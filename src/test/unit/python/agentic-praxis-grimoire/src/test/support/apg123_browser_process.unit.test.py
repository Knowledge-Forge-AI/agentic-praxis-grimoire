"""Owned browser child cleanup contracts, independent of browser prerequisites."""

import os
import io
import importlib
import json
from contextlib import contextmanager
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))
process_owner = importlib.import_module("apg123_browser_process")
harness = importlib.import_module("apg123_browser_ui")


READINESS_TIMEOUT = 30
FIXTURE_CODE = r"""
import json, os, select, signal, subprocess, sys
lease, ready, lifetime, group = map(int, sys.argv[1:5])
mode, delay, announce = sys.argv[5], float(sys.argv[6]), sys.argv[7] == 'True'
ack_delay, ack, sentinel, registration_eof = (
    float(sys.argv[8]), sys.argv[9] == 'True', sys.argv[10] == 'True', sys.argv[11] == 'True')
if sentinel:
    # Ignored TERM survives exec, including the sentinel's interpreter startup.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    subprocess.Popen([sys.executable, '-c',
        'import select,sys; select.select([int(sys.argv[1])],[],[])', str(lease)],
        pass_fds=(lease, group), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
child = subprocess.Popen([sys.executable, '-c',
    'import select,sys; select.select([int(sys.argv[1])],[],[])', str(lease)],
    pass_fds=(lease, lifetime), start_new_session=mode == 'detached')
# Only the descendant holds lifetime. The ready fd is never passed to it.
os.close(lifetime)
if select.select([lease], [], [], ack_delay)[0]:
    sys.exit(0)
if not ack:
    select.select([lease], [], [])
    sys.exit(0)
os.write(ready, b'{"descendant_created":true}\n')
if select.select([lease], [], [], delay)[0]:
    sys.exit(0)
label = {'live': 'owned', 'exited': 'failed child', 'detached': 'detached'}[mode]
print(label + ' stdout', flush=True)
print(label + ' stderr', file=sys.stderr, flush=True)
if announce:
    os.write(ready, (json.dumps({'descendant_pid': child.pid}) + '\n').encode())
if announce or registration_eof:
    os.close(ready)
if not announce or mode == 'live':
    select.select([lease], [], [])
else:
    sys.exit(7 if mode == 'exited' else 9)
"""


def _ready_payload(fd, timeout, phase):
    deadline, data = time.monotonic() + timeout, b''
    while b'\n' not in data:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise TimeoutError('fixture ' + phase + ' deadline')
        chunk = os.read(fd, 1)
        if not chunk:
            raise TimeoutError('fixture EOF before ' + phase)
        data += chunk
        if len(data) > 4096:
            raise ValueError('oversized fixture readiness')
    return json.loads(data)


def _signal_guard(pgid, group_fd, state, delegate):
    def guarded(target, sig):
        owned = target == pgid and not select.select([group_fd], [], [], 0)[0]
        state.setdefault('group_signals', []).append({'signal': sig, 'owned': owned})
        if not owned:
            raise ProcessLookupError('fixture group ownership refused')
        delegate(target, sig)
    return guarded


@contextmanager
def owned_fixture(mode, *, delay=0, announce=True, ack_delay=0, ack=True,
                  sentinel=True, registration_eof=False, creation_timeout=READINESS_TIMEOUT,
                  registration_timeout=READINESS_TIMEOUT, state=None):
    """Lease EOF releases even an unregistered detached fixture descendant."""
    state = {} if state is None else state
    lease_r, lease_w = os.pipe()
    ready_r, ready_w = os.pipe()
    lifetime_r, lifetime_w = os.pipe()
    group_r, group_w = os.pipe()
    proc, primary = None, None
    patch = pytest.MonkeyPatch()
    state['group_signals'] = []
    try:
        proc = subprocess.Popen(
            [sys.executable, '-c', FIXTURE_CODE, str(lease_r), str(ready_w),
             str(lifetime_w), str(group_w), mode, str(delay), str(announce),
             str(ack_delay), str(ack), str(sentinel), str(registration_eof)],
            pass_fds=(lease_r, ready_w, lifetime_w, group_w), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, start_new_session=True)
        state['proc'] = proc
        state['lifetime_fd'] = lifetime_r
        patch.setattr(os, 'killpg', _signal_guard(proc.pid, group_r, state, os.killpg))
        os.close(lease_r)
        os.close(ready_w)
        os.close(lifetime_w)
        os.close(group_w)
        lease_r = ready_w = lifetime_w = group_w = None
        state['ready_started'] = time.monotonic()
        created = _ready_payload(ready_r, creation_timeout, 'creation acknowledgement')
        if created != {'descendant_created': True}:
            raise ValueError('missing fixture creation acknowledgement')
        state['descendant_created'] = True
        state['creation_acknowledged'] = time.monotonic()
        state['registration_started'] = time.monotonic()
        try:
            payload = _ready_payload(ready_r, registration_timeout, 'registration')
        except TimeoutError:
            state['registration_failed'] = time.monotonic()
            raise
        pid = payload['descendant_pid']
        if type(pid) is not int or pid <= 0:
            raise ValueError('invalid fixture descendant registration')
        state['descendant_pid'] = pid
        state['ready_completed'] = time.monotonic()
        if mode != 'live':
            # The same-group sentinel pins PGID even after wait/poll/communicate reap.
            proc.wait(timeout=READINESS_TIMEOUT)
        yield proc
    except BaseException as error:
        primary = error
        raise
    finally:
        errors = []
        if proc is not None:
            # Keep the lease open through every group signal, including setup failure.
            if proc.returncode is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError as error:
                    errors.append(str(error))
        os.close(lease_w)
        if proc is not None:
            try:
                proc.wait(timeout=2)
                # Production may have closed its pipes; lifetime remains independent.
                if not proc.stdout.closed and not proc.stderr.closed:
                    proc.communicate(timeout=2)
            except (OSError, subprocess.TimeoutExpired) as error:
                errors.append(str(error))
            finally:
                proc.stdout.close()
                proc.stderr.close()
            if select.select([lifetime_r], [], [], READINESS_TIMEOUT)[0] and os.read(lifetime_r, 1) == b'':
                state['descendants_released'] = True
            else:
                errors.append('fixture descendant did not release its lease/lifetime')
            state['child_reaped'] = proc.returncode is not None
            if select.select([group_r], [], [], READINESS_TIMEOUT)[0] and os.read(group_r, 1) == b'':
                state['group_released'] = True
            else:
                errors.append('fixture group did not release its ownership pipe')
            if sentinel and any(not row['owned'] for row in state['group_signals']):
                errors.append('fixture group ownership refused')
        patch.undo()
        for fd in (lease_r, ready_r, ready_w, lifetime_r, lifetime_w, group_r, group_w):
            if fd is not None:
                os.close(fd)
        state['cleanup_errors'] = errors
        if errors:
            if primary is not None:
                primary.add_note('fixture cleanup: ' + '; '.join(errors))
            else:
                pytest.fail('; '.join(errors))


@pytest.mark.parametrize('delay', [0, 1.0])
def test_timeout_reaps_owned_group_and_keeps_output(delay):
    state = {}
    with owned_fixture('live', delay=delay, state=state) as proc:
        _assert_live_timeout(proc)
    assert state['ready_completed'] - state['ready_started'] >= delay
    _assert_released(state)
    assert state['group_signals'] == [{'signal': signal.SIGTERM, 'owned': True}]


def _assert_live_timeout(proc):
    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        process_owner.communicate_owned(proc, timeout=0.2, grace=0.2)
    assert time.monotonic() - start < 3
    assert "owned stdout" in caught.value.output
    assert "owned stderr" in caught.value.stderr
    assert proc.returncode is not None
    assert caught.value.cleanup["child_reaped"]
    cleanup = caught.value.cleanup
    assert cleanup["child_returncode_at_exception"] is None
    assert cleanup["communication_started_monotonic"] <= cleanup["exception_observed_monotonic"] <= cleanup["cleanup_completed_monotonic"]


@pytest.mark.parametrize('delay', [0, 1.0])
def test_failed_child_with_same_group_pipe_descendant_is_bounded(delay):
    state = {}
    with owned_fixture('exited', delay=delay, state=state) as proc:
        start = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired) as caught:
            process_owner.communicate_owned(proc, timeout=0.2, grace=0.2)
        assert time.monotonic() - start < 3
        assert proc.returncode == 7
        assert caught.value.cleanup['child_returncode_at_exception'] == 7
        assert 'failed child stdout' in caught.value.output
        assert 'failed child stderr' in caught.value.stderr
    _assert_released(state)
    assert state['group_signals'] == [{'signal': signal.SIGTERM, 'owned': True}]


@pytest.mark.parametrize('delay', [0, 1.0])
def test_detached_pipe_holder_not_signalled_and_pipe_wait_bounded(delay):
    state = {}
    with owned_fixture('detached', delay=delay, state=state) as proc:
        start = time.monotonic()
        with pytest.raises(subprocess.TimeoutExpired) as caught:
            process_owner.communicate_owned(proc, timeout=0.2, grace=0.1)
        assert time.monotonic() - start < 3
        assert "detached stdout" in caught.value.output
        assert "detached stderr" in caught.value.stderr
        assert caught.value.cleanup["pipe_retained_after_group_kill"]
        assert proc.returncode == 9
        os.kill(state['descendant_pid'], 0)
        assert not select.select([state['lifetime_fd']], [], [], 0)[0]
        assert proc.stdout.closed and proc.stderr.closed
    _assert_released(state)
    assert state['group_signals'] == [
        {'signal': signal.SIGTERM, 'owned': True}, {'signal': signal.SIGKILL, 'owned': True}]


@pytest.mark.parametrize('ack_delay', [0, 1.0])
def test_readiness_failure_releases_unregistered_detached_child(ack_delay):
    state = {}
    with pytest.raises(TimeoutError, match='fixture registration deadline'):
        with owned_fixture('detached', ack_delay=ack_delay, announce=False,
                           registration_timeout=0.3, state=state):
            pytest.fail('fixture without registration cannot be ready')
    assert 'descendant_pid' not in state
    assert state['descendant_created']
    assert state['creation_acknowledged'] - state['ready_started'] >= ack_delay
    assert state['registration_started'] >= state['creation_acknowledged']
    assert state['registration_failed'] - state['registration_started'] >= 0.3
    _assert_released(state)
    assert state['group_signals'] == [{'signal': signal.SIGKILL, 'owned': True}]


def _assert_released(state):
    assert state['child_reaped'] and state['descendants_released'] and state['group_released']
    assert not state['cleanup_errors']


def test_missing_creation_ack_has_its_own_bounded_budget():
    state = {}
    with pytest.raises(TimeoutError, match='fixture creation acknowledgement deadline'):
        with owned_fixture('detached', ack=False, creation_timeout=0.5, state=state):
            pytest.fail('fixture without acknowledgement cannot be ready')
    assert 'descendant_created' not in state and 'registration_started' not in state
    assert 'descendant_pid' not in state
    _assert_released(state)


def test_registration_eof_is_distinct_from_deadline():
    state = {}
    with pytest.raises(TimeoutError, match='fixture EOF before registration'):
        with owned_fixture('detached', announce=False, registration_eof=True, state=state):
            pytest.fail('EOF cannot register a descendant')
    assert state['descendant_created'] and 'descendant_pid' not in state
    _assert_released(state)


def test_unpinned_group_signals_are_refused():
    state = {}
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        with owned_fixture('detached', sentinel=False, state=state) as proc:
            process_owner.communicate_owned(proc, timeout=0.2, grace=0.1)
    assert state['group_signals'] == [
        {'signal': signal.SIGTERM, 'owned': False}, {'signal': signal.SIGKILL, 'owned': False}]
    assert caught.value.cleanup['pipe_retained_after_group_kill']
    assert state['proc'].returncode == 9
    _assert_released(state)


def test_signal_guard_requires_matching_group_and_live_holder():
    read_fd, write_fd = os.pipe()
    calls, state = [], {}
    try:
        guarded = _signal_guard(123, read_fd, state, lambda *args: calls.append(args))
        guarded(123, signal.SIGTERM)
        with pytest.raises(ProcessLookupError, match='ownership refused'):
            guarded(124, signal.SIGKILL)
        os.close(write_fd)
        write_fd = None
        with pytest.raises(ProcessLookupError, match='ownership refused'):
            guarded(123, signal.SIGKILL)
        assert calls == [(123, signal.SIGTERM)]
        assert [row['owned'] for row in state['group_signals']] == [True, False, False]
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)


def test_assertion_failure_still_releases_fixture_processes():
    state = {}
    with pytest.raises(AssertionError, match='deliberate assertion'):
        with owned_fixture('detached', state=state):
            raise AssertionError('deliberate assertion')
    _assert_released(state)


def test_fixture_cleanup_diagnostic_preserves_primary_assertion(monkeypatch):
    state = {}
    primary = AssertionError('deliberate primary assertion')
    with pytest.raises(AssertionError) as caught:
        with owned_fixture('detached', state=state) as proc:
            def failed_wait(*, timeout):
                raise OSError('deliberate cleanup diagnostic')
            monkeypatch.setattr(proc, 'wait', failed_wait)
            raise primary
    assert caught.value is primary
    assert any('deliberate cleanup diagnostic' in note for note in primary.__notes__)
    assert state['child_reaped'] and state['descendants_released'] and state['group_released']


@pytest.mark.parametrize("primary", [OSError("read failed"), KeyboardInterrupt()])
def test_communication_exception_cleanup_preserves_primary(primary, monkeypatch):
    signals = []
    monkeypatch.setattr(process_owner.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    class Child:
        pid = 123456789
        returncode = None
        stdout = None
        stderr = None

        def __init__(self):
            self.calls = 0

        def communicate(self, timeout):
            self.calls += 1
            if self.calls == 1:
                raise primary
            self.returncode = -15
            return "partial stdout", "partial stderr"

    proc = Child()
    with pytest.raises(type(primary)) as caught:
        process_owner.communicate_owned(proc, timeout=1, grace=0.1)
    assert caught.value is primary
    assert caught.value.output == "partial stdout"
    assert caught.value.stderr == "partial stderr"
    assert caught.value.cleanup["child_reaped"]
    assert signals == [(proc.pid, signal.SIGTERM)]


def test_failed_drain_closes_pipes_and_reaps_without_replacing_primary(monkeypatch):
    primary = OSError("primary read failure")
    signals = []
    monkeypatch.setattr(process_owner.os, "killpg", lambda pid, sig: signals.append((pid, sig)))

    class Child:
        pid = 123456789
        returncode = None
        stdout, stderr = io.StringIO(), io.StringIO()

        def communicate(self, timeout):
            raise primary

        def wait(self, timeout):
            self.returncode = -9

    child = Child()
    with pytest.raises(OSError) as caught:
        process_owner.communicate_owned(child, timeout=1, grace=0.01)
    assert caught.value is primary
    assert child.stdout.closed and child.stderr.closed
    assert primary.cleanup["child_reaped"]
    assert primary.cleanup["errors"] == ["OSError", "OSError"]
    assert signals == [(child.pid, signal.SIGTERM), (child.pid, signal.SIGKILL)]


def test_progress_tail_is_bounded_and_refuses_symlink(tmp_path):
    progress = tmp_path / "progress.jsonl"
    progress.write_text("\n".join(str(i) for i in range(100)))
    assert process_owner.progress_tail(progress, lines=3) == ["97", "98", "99"]
    linked = tmp_path / "linked.jsonl"
    linked.symlink_to(progress)
    assert process_owner.progress_tail(linked) == []
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    assert process_owner.progress_tail(fifo) == []


@pytest.mark.parametrize("failure", ["timeout", "timeout_receipt", "error", "interrupt", "tail_receipt"])
def test_harness_failure_keeps_terminal_output_progress_and_reaps(tmp_path, monkeypatch, failure):
    scratch = tmp_path.resolve() / "owned"
    scratch.mkdir(mode=0o700)
    primary = (subprocess.TimeoutExpired("fake", 180, output="before timeout", stderr="before stderr")
               if failure.startswith("timeout") else OSError("primary read failure") if failure in ("error", "tail_receipt")
               else KeyboardInterrupt())

    class Child:
        pid = 123456789
        returncode = None

        def __init__(self, *args, **kwargs):
            self.calls = 0
            self.stdout, self.stderr = io.StringIO(), io.StringIO()
            (kwargs["cwd"] / "progress.jsonl").write_text(
                '{"phase":"scenario_start","engine":"webkit","scenario":"PW10","monotonic_ms":2}\n')
            if failure in ("timeout_receipt", "tail_receipt"):
                (kwargs["cwd"] / "receipt.json").write_text(json.dumps({"scenarios": [{
                    "scenario_id": "PW10", "browser": "webkit", "status": "failed",
                    "error_details": {"class": "AssertionError", "message": "primary scenario failure"},
                }]}))

        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                raise primary
            if timeout is None:
                raise AssertionError("unbounded pipe wait")
            self.returncode = -15
            if failure == "tail_receipt":
                return ("stdout head\n" + "x" * 6000 + "\nstdout terminal PW10 webkit",
                        "stderr head\n" + "y" * 6000 + '\nRunner fatal error: {"class":"FatalError","message":"terminal webkit PW10 ' +
                        str(scratch) + ' bearer sensitive-token"}')
            return "terminal stdout", "terminal stderr"

    child = None

    def spawn(*args, **kwargs):
        nonlocal child
        child = Child(*args, **kwargs)
        return child

    monkeypatch.setattr(harness.subprocess, "Popen", spawn)
    signals = []
    monkeypatch.setattr(process_owner.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    config = harness.BrowserHarnessConfig(ROOT, scratch, Path(sys.executable), "fake", scratch, "fake", scratch)
    expected = KeyboardInterrupt if failure == "interrupt" else harness.BrowserHarnessExecutionError
    with pytest.raises(expected) as caught:
        harness.execute_browser_harness(config, ROOT / "src/test/fixtures/apg123-browser-ui", scenario_filter=("PW01",))
    assert child.returncode is not None, "failed child must be reaped"
    assert signals == [(child.pid, signal.SIGTERM)]
    if failure != "interrupt":
        evidence = caught.value.failure_evidence
        if failure == "tail_receipt":
            assert "Runner fatal error:" in evidence["stderr"]
            assert "terminal webkit PW10" in evidence["stderr"]
            assert "stdout terminal PW10 webkit" in evidence["stdout"]
            assert evidence["stdout"].startswith("stdout head")
            assert evidence["stderr"].startswith("stderr head")
            assert "[truncated]" in evidence["stderr"]
            assert str(scratch) not in evidence["stderr"]
            assert "sensitive-token" not in evidence["stderr"]
            assert evidence["error_class"] == "AssertionError"
        else:
            assert evidence["stdout"] == "terminal stdout"
            assert evidence["stderr"] == "terminal stderr"
        assert "PW10" in evidence["progress_tail"][-1]
        assert evidence["cleanup"]["child_reaped"]
        assert caught.value.retained_path.name.startswith("browser-run-")
        assert str(scratch) not in json.dumps(json.loads(caught.value.retained_path.read_text()))
        if failure.startswith("timeout"):
            assert caught.value.original_class == "TimeoutExpired"
            assert evidence["process_error"]["class"] == "TimeoutExpired"
        if failure == "timeout_receipt":
            assert evidence["error_class"] == "AssertionError"
            assert evidence["failed_scenarios"][0]["scenario_id"] == "PW10"
