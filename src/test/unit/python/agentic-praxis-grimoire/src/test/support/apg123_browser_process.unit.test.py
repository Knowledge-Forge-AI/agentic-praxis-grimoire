"""Owned browser child cleanup contracts, independent of browser prerequisites."""

import ast
import os
import io
import importlib
import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path
import select
import signal
import stat
import subprocess
import sys
import threading
import time

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))
process_owner = importlib.import_module("apg123_browser_process")
harness = importlib.import_module("apg123_browser_ui")


READINESS_TIMEOUT = 30
HARNESS_DEADLINE_MARKER = {"source": "harness", "phase": "harness deadline", "engine": None,
                           "scenario": None, "boundary": "signal"}
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
        timed_out = failure.startswith("timeout")
        assert "PW10" in evidence["progress_tail"][-2 if timed_out else -1]
        if timed_out:
            assert json.loads(evidence["progress_tail"][-1]) == HARNESS_DEADLINE_MARKER
        else:
            assert "harness deadline" not in "".join(evidence["progress_tail"])
        assert evidence["scheduling"] == {"wait_seconds": evidence["scheduling"]["wait_seconds"],
                                          "budget_seconds": 180, "selected_cases": 3,
                                          "terminated_by_harness_deadline": timed_out}
        assert evidence["scheduling"]["wait_seconds"] >= 0
        assert evidence["cleanup"]["child_reaped"]
        assert caught.value.retained_path.name.startswith("browser-run-")
        assert str(scratch) not in json.dumps(json.loads(caught.value.retained_path.read_text()))
        if failure.startswith("timeout"):
            assert caught.value.original_class == "TimeoutExpired"
            assert evidence["process_error"]["class"] == "TimeoutExpired"
        if failure == "timeout_receipt":
            assert evidence["error_class"] == "AssertionError"
            assert evidence["failed_scenarios"][0]["scenario_id"] == "PW10"


@pytest.mark.parametrize("cases,pw10,expected", [
    (72, 3, 858), (39, 3, 726), (42, 0, 198), (33, 0, 180),
    (1, 0, 180), (38, 3, 722), (114, 3, 1026)])
def test_harness_timeout_budget_includes_pw10_per_browser(cases, pw10, expected):
    assert process_owner.harness_timeout_seconds(cases, pw10) == expected


@pytest.mark.parametrize("cases", [True, False, 0, -1, 115, 3.0, "3", None])
def test_harness_timeout_budget_refuses_invalid_case_count(cases):
    with pytest.raises(ValueError, match="case_count"):
        process_owner.harness_timeout_seconds(cases, 0)


@pytest.mark.parametrize("pw10", [True, -1, 4, 1.0, "1", None])
def test_harness_timeout_budget_refuses_invalid_pw10_browser_count(pw10):
    with pytest.raises(ValueError, match="pw10_browsers"):
        process_owner.harness_timeout_seconds(3, pw10)


INT_ROOT = "src/test/int/python/agentic-praxis-grimoire/"
CALLERS = (
    ("skills/playwright-test-profile/SKILL.int.test.py", "test_playwright_and_svg_real_browser_lanes", False),
    ("skills/web-accessibility-profile/SKILL.int.test.py", "test_web_accessibility_real_browser_lanes", False),
    ("src/test/support/apg123_browser_ui.int.test.py", "test_browser_runtime_scenarios_matrix_distinct_verification", True),
    ("src/test/support/apg123_browser_ui.int.test.py", "test_apg123_scenarios_matrix_distinct_verification", True),
)


class _BudgetObserved(Exception):
    pass


def _observed_budget_inputs(monkeypatch, relative, function, takes_config):
    """Run the real caller function through the real harness up to its budget computation."""
    path = ROOT / INT_ROOT / relative
    spec = importlib.util.spec_from_file_location("apg_int_caller_" + function, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = harness.BrowserHarnessConfig(ROOT, ROOT, Path(sys.executable), "fake", ROOT, "fake", ROOT)
    monkeypatch.setattr(module, "observe_browser_harness_config", lambda root: config)
    seen = []

    def record(case_count, pw10_browsers=0):
        seen.append((case_count, pw10_browsers))
        raise _BudgetObserved

    monkeypatch.setattr(harness, "harness_timeout_seconds", record)
    with pytest.raises(_BudgetObserved):
        getattr(module, function)(*([config] if takes_config else []))
    assert len(seen) == 1
    return seen[0]


def test_integration_callers_budgets_and_exact_186_without_skips(monkeypatch):
    observed = {}
    for relative, function, takes_config in CALLERS:
        observed[INT_ROOT + relative + "::" + function] = _observed_budget_inputs(
            monkeypatch, relative, function, takes_config)
        monkeypatch.undo()
    # The sum of cases actually requested by the four callers is the deferred set.
    assert sorted(case for case, _ in observed.values()) == [33, 39, 42, 72]
    assert sum(case for case, _ in observed.values()) == 186
    budgets = {node: process_owner.harness_timeout_seconds(*inputs) for node, inputs in observed.items()}
    assert sorted(budgets.values()) == [180, 198, 726, 858]
    assert sum(budgets.values()) == 1962
    # Each run also pays at most TERM and KILL grace; the serialized total stays inside the slot bound.
    assert sum(budgets.values()) + 2 * 5 * len(budgets) < process_owner.SLOT_TIMEOUT_SECONDS == 2100

    monkeypatch.syspath_prepend(str(ROOT / "libexec"))
    release = importlib.import_module("apg_public_release")
    assert set(observed) == set(release.LOCAL_BROWSER_DEFERRAL_NODES) and len(observed) == 4
    discovered = set()
    for path in (ROOT / INT_ROOT).rglob("*.int.test.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                if any(isinstance(call, ast.Call) and
                       getattr(call.func, "id", getattr(call.func, "attr", None)) == "execute_browser_harness"
                       for call in ast.walk(node)):
                    discovered.add(path.relative_to(ROOT).as_posix() + "::" + node.name)
    assert discovered == set(observed)
    for relative, function, _ in CALLERS:
        tree = ast.parse((ROOT / INT_ROOT / relative).read_text(encoding="utf-8"))
        definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function]
        assert len(definitions) == 1
        names = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        names |= {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        assert not names & {"skip", "skipif", "xfail", "importorskip"}, relative


def _slot_root(tmp_path):
    root = tmp_path.resolve() / "slot-root"
    root.mkdir(mode=0o700)
    return root


def _open_fds():
    return len(os.listdir("/dev/fd"))


def test_slot_is_exclusive_times_out_and_releases(tmp_path):
    root = _slot_root(tmp_path)
    first = process_owner.BrowserSlot(root)
    assert first.acquire() >= 0
    lock = root / process_owner.SLOT_LOCK_NAME
    assert stat.S_IMODE(lock.stat().st_mode) == 0o600 and lock.stat().st_nlink == 1
    assert not os.get_inheritable(first.fd)
    second = process_owner.BrowserSlot(root, timeout=0.2, poll=0.02)
    with pytest.raises(process_owner.BrowserSlotError) as caught:
        second.acquire()
    assert caught.value.timed_out and caught.value.wait_seconds >= 0.2 and second.fd is None
    first.release()
    first.release()
    assert second.acquire() >= 0
    second.release()


def test_slot_waiter_proceeds_when_holder_releases(tmp_path):
    root = _slot_root(tmp_path)
    holder = process_owner.BrowserSlot(root)
    holder.acquire()
    timer = threading.Timer(0.2, holder.release)
    timer.start()
    waiter = process_owner.BrowserSlot(root, timeout=10, poll=0.02)
    try:
        assert waiter.acquire() >= 0.1
    finally:
        timer.join()
        waiter.release()


def test_slot_wait_is_bounded_by_the_2100_second_default(tmp_path):
    root = _slot_root(tmp_path)
    holder = process_owner.BrowserSlot(root)
    holder.acquire()
    now, sleeps = [0.0], []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    waiter = process_owner.BrowserSlot(root, clock=lambda: now[0], sleep=sleep)
    assert waiter.timeout == 2100
    try:
        with pytest.raises(process_owner.BrowserSlotError, match="2100s") as caught:
            waiter.acquire()
    finally:
        holder.release()
    assert caught.value.timed_out and caught.value.wait_seconds == 2100
    assert max(sleeps) <= process_owner.SLOT_POLL_SECONDS and sum(sleeps) == 2100


@pytest.mark.parametrize("kind", ["symlink", "fifo", "hardlink", "group_writable", "directory", "root_symlink"])
def test_slot_refuses_unsafe_lock_path_without_leaking_descriptors(tmp_path, kind):
    root = _slot_root(tmp_path)
    lock = root / process_owner.SLOT_LOCK_NAME
    target = tmp_path / "target"
    if kind == "symlink":
        target.write_text("untouched")
        lock.symlink_to(target)
    elif kind == "fifo":
        os.mkfifo(lock, 0o600)
    elif kind == "hardlink":
        target.write_text("untouched")
        target.chmod(0o600)
        os.link(target, lock)
    elif kind == "group_writable":
        lock.touch()
        lock.chmod(0o660)
    elif kind == "directory":
        lock.mkdir()
    else:
        root = tmp_path / "root-link"
        root.symlink_to(tmp_path / "slot-root")
    before = _open_fds()
    slot = process_owner.BrowserSlot(root, timeout=0)
    with pytest.raises(process_owner.BrowserSlotError) as caught:
        slot.acquire()
    assert not caught.value.timed_out and slot.fd is None
    assert _open_fds() == before
    if kind in ("symlink", "hardlink"):
        assert target.read_text() == "untouched"


def test_slot_refuses_lock_replaced_while_waiting(tmp_path):
    root = _slot_root(tmp_path)
    holder = process_owner.BrowserSlot(root)
    holder.acquire()
    lock = root / process_owner.SLOT_LOCK_NAME
    replaced = []

    def sleep(seconds):
        # The waiter's open descriptor pins the displaced inode, so it cannot be reused for the new file.
        if not replaced:
            replaced.append(True)
            holder.release()
            lock.unlink()
            lock.write_text("")
            lock.chmod(0o600)

    waiter = process_owner.BrowserSlot(root, timeout=5, poll=0.01, sleep=sleep)
    before = _open_fds()
    with pytest.raises(process_owner.BrowserSlotError, match="replaced") as caught:
        waiter.acquire()
    # The holder was deliberately released by sleep; only its descriptor left.
    assert not caught.value.timed_out and waiter.fd is None and _open_fds() == before - 1


class _DeadlineChild:
    pid = 123456789
    returncode = None
    stdout = None
    stderr = None

    def __init__(self, *errors):
        self.errors = list(errors)

    def communicate(self, timeout):
        if self.errors:
            raise self.errors.pop(0)
        self.returncode = -15
        return "o", "e"


def test_on_deadline_runs_once_before_group_signal_for_timeout_only(monkeypatch):
    events = []
    monkeypatch.setattr(process_owner.os, "killpg", lambda pid, sig: events.append(sig))
    timeout = subprocess.TimeoutExpired("fake", 1, output="o", stderr="e")
    # A grace-period timeout is not the harness deadline; SIGKILL follows without a second callback.
    child = _DeadlineChild(timeout, subprocess.TimeoutExpired("fake", 1))
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        process_owner.communicate_owned(child, timeout=1, grace=0.01,
                                        on_deadline=lambda: events.append("deadline"))
    assert caught.value is timeout
    assert events == ["deadline", signal.SIGTERM, signal.SIGKILL]


@pytest.mark.parametrize("primary", [OSError("read failed"), KeyboardInterrupt()])
def test_on_deadline_is_skipped_for_non_timeout_failures(primary, monkeypatch):
    events = []
    monkeypatch.setattr(process_owner.os, "killpg", lambda pid, sig: events.append(sig))
    with pytest.raises(type(primary)):
        process_owner.communicate_owned(_DeadlineChild(primary), timeout=1, grace=0.01,
                                        on_deadline=lambda: events.append("deadline"))
    assert events == [signal.SIGTERM]


@pytest.mark.parametrize("secondary", [RuntimeError("marker failed"), KeyboardInterrupt()])
def test_on_deadline_failure_never_replaces_primary_or_skips_cleanup(secondary, monkeypatch):
    events = []
    monkeypatch.setattr(process_owner.os, "killpg", lambda pid, sig: events.append(sig))
    primary = subprocess.TimeoutExpired("fake", 1, output="o", stderr="e")

    def broken():
        raise secondary

    child = _DeadlineChild(primary)
    with pytest.raises(subprocess.TimeoutExpired) as caught:
        process_owner.communicate_owned(child, timeout=1, grace=0.01, on_deadline=broken)
    assert caught.value is primary
    assert events == [signal.SIGTERM] and child.returncode == -15
    assert primary.cleanup["errors"] == ["on_deadline:" + type(secondary).__name__]
    assert primary.cleanup["child_reaped"]


def test_progress_marker_appends_in_order_and_repairs_partial_line(tmp_path):
    progress = tmp_path / "progress.jsonl"
    process_owner.append_progress_marker(progress, {"n": 1})
    with progress.open("a") as stream:
        stream.write('{"partial"')
    process_owner.append_progress_marker(progress, {"n": 2})
    lines = progress.read_text().splitlines()
    assert [json.loads(line) for line in (lines[0], lines[2])] == [{"n": 1}, {"n": 2}]
    assert lines[1] == '{"partial"'
    assert stat.S_IMODE(progress.stat().st_mode) == 0o600


def test_progress_marker_refuses_symlink_and_nonregular_targets(tmp_path):
    target = tmp_path / "target"
    target.write_text("untouched")
    linked = tmp_path / "linked.jsonl"
    linked.symlink_to(target)
    with pytest.raises(OSError):
        process_owner.append_progress_marker(linked, {"n": 1})
    assert target.read_text() == "untouched"
    hardlink = tmp_path / "hardlink.jsonl"
    os.link(target, hardlink)
    with pytest.raises(OSError):
        process_owner.append_progress_marker(hardlink, {"n": 1})
    assert target.read_text() == "untouched"
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    before = _open_fds()
    with pytest.raises(OSError):
        process_owner.append_progress_marker(fifo, {"n": 1})
    assert _open_fds() == before


class _ScheduledChild:
    """Fake Popen that reports whether the shared slot is held at each observation."""
    pid = 123456789
    returncode = None
    observed = None
    scratch = None
    fail = None

    def __init__(self, *args, **kwargs):
        self.calls = 0
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        self.observed["spawn"] = _slot_held(self.scratch)
        (kwargs["cwd"] / "receipt.json").write_text("{}")

    def communicate(self, timeout=None):
        self.calls += 1
        if self.calls == 1:
            self.observed["timeout"] = timeout
            self.observed["communicate"] = _slot_held(self.scratch)
            if self.fail is not None:
                raise self.fail
            self.returncode = 0
            return "", ""
        self.returncode = -15
        return "", ""


def _slot_held(scratch):
    probe = process_owner.BrowserSlot(scratch, timeout=0)
    try:
        probe.acquire()
    except process_owner.BrowserSlotError as err:
        return err.timed_out
    probe.release()
    return False


def _scheduled_harness(tmp_path, monkeypatch, fail=None):
    scratch = tmp_path.resolve() / "owned"
    scratch.mkdir(mode=0o700)
    observed = {}
    child = type("ScheduledChild", (_ScheduledChild,), {"observed": observed, "scratch": scratch, "fail": fail})
    monkeypatch.setattr(harness.subprocess, "Popen", child)
    monkeypatch.setattr(process_owner.os, "killpg", lambda pid, sig: None)
    monkeypatch.setattr(harness, "validate_receipt",
                        lambda *args, **kwargs: harness.BrowserHarnessReceipt(raw={}))
    config = harness.BrowserHarnessConfig(ROOT, scratch, Path(sys.executable), "fake", scratch, "fake", scratch)
    return scratch, config, observed


FIXTURES = ROOT / "src/test/fixtures/apg123-browser-ui"


def test_harness_holds_slot_across_spawn_and_communicate_with_budget(tmp_path, monkeypatch):
    scratch, config, observed = _scheduled_harness(tmp_path, monkeypatch)
    receipt = harness.execute_browser_harness(config, FIXTURES, scenario_filter=("PW10",))
    # PW10 on three browsers: max(180, 30 + 4 * 3) + 3 * 180.
    assert observed == {"spawn": True, "timeout": 720, "communicate": True}
    assert receipt.scheduling == {"wait_seconds": receipt.scheduling["wait_seconds"], "budget_seconds": 720,
                                  "selected_cases": 3, "terminated_by_harness_deadline": False}
    assert receipt.scheduling["wait_seconds"] >= 0
    assert not _slot_held(scratch)


@pytest.mark.parametrize("failure", [OSError("read failed"), KeyboardInterrupt()])
def test_harness_releases_slot_after_communication_failure(tmp_path, monkeypatch, failure):
    scratch, config, observed = _scheduled_harness(tmp_path, monkeypatch, fail=failure)
    expected = type(failure) if isinstance(failure, KeyboardInterrupt) else harness.BrowserHarnessExecutionError
    with pytest.raises(expected):
        harness.execute_browser_harness(config, FIXTURES, scenario_filter=("PW01",))
    assert observed["communicate"] is True and observed["timeout"] == 180
    assert not _slot_held(scratch)


@pytest.mark.parametrize("held", ["busy", "symlink"])
def test_harness_slot_failure_retains_scheduling_and_never_spawns(tmp_path, monkeypatch, held):
    scratch, config, observed = _scheduled_harness(tmp_path, monkeypatch)
    monkeypatch.setattr(harness.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("spawned without slot"))
    monkeypatch.setattr(harness, "BrowserSlot", lambda root: process_owner.BrowserSlot(root, timeout=0.2, poll=0.02))
    holder = process_owner.BrowserSlot(scratch)
    if held == "busy":
        holder.acquire()
    else:
        (tmp_path / "target").write_text("untouched")
        (scratch / process_owner.SLOT_LOCK_NAME).symlink_to(tmp_path / "target")
    try:
        with pytest.raises(harness.BrowserHarnessExecutionError) as caught:
            harness.execute_browser_harness(config, FIXTURES, scenario_filter=("PW01",))
    finally:
        holder.release()
    evidence = caught.value.failure_evidence
    assert caught.value.original_class == "BrowserSlotError"
    assert evidence["process_error"]["class"] == "BrowserSlotError"
    assert evidence["scheduling"]["budget_seconds"] == 180 and evidence["scheduling"]["selected_cases"] == 3
    assert evidence["scheduling"]["terminated_by_harness_deadline"] is False
    assert (evidence["scheduling"]["wait_seconds"] >= 0.2) == (held == "busy")
    assert json.loads(caught.value.retained_path.read_text())["scheduling"] == evidence["scheduling"]
    assert not [p for p in scratch.iterdir() if p.name.startswith("run-")]


@pytest.mark.parametrize("browsers", [(), ("chromium",) * 39])
def test_execute_refuses_case_count_outside_budget_before_any_side_effect(tmp_path: Path, browsers: tuple) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700)
    config = harness.BrowserHarnessConfig(ROOT, scratch, Path(sys.executable), "fake", scratch, "fake", scratch)
    with pytest.raises(harness.BrowserHarnessExecutionError, match="case budget refused"):
        harness.execute_browser_harness(config, FIXTURES, browsers=browsers)
    assert list(scratch.iterdir()) == []


def test_failure_evidence_retains_sanitized_scheduling(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700)
    config = harness.BrowserHarnessConfig(ROOT, scratch, Path(sys.executable), "fake", scratch, "fake", scratch)
    scheduling = {"wait_seconds": 1.5, "budget_seconds": 858, "selected_cases": 72,
                  "terminated_by_harness_deadline": True}
    evidence, retained = harness.retain_failure_evidence(
        config, "run-scheduling", scratch / "absent.json", -1, "", "", "failed", scheduling=scheduling)
    assert evidence["scheduling"] == scheduling
    assert json.loads(retained.read_text(encoding="utf-8"))["scheduling"] == scheduling
    absent, retained = harness.retain_failure_evidence(config, "run-no-scheduling", scratch / "absent.json", -1, "", "", "failed")
    assert absent["scheduling"] is None


@pytest.mark.parametrize("name,value", [
    ("timeout", float("nan")), ("timeout", float("inf")), ("timeout", -1),
    ("timeout", True), ("timeout", 2101), ("poll", 0), ("poll", float("nan")),
    ("poll", True), ("poll", 0.26), ("poll", "1")])
def test_slot_refuses_unbounded_or_invalid_wait_parameters(tmp_path, name, value):
    with pytest.raises(ValueError, match=name):
        process_owner.BrowserSlot(tmp_path, **{name: value})
    assert not (tmp_path / process_owner.SLOT_LOCK_NAME).exists()


def test_harness_spawn_failure_retains_evidence_and_releases_slot(tmp_path, monkeypatch):
    scratch, config, _ = _scheduled_harness(tmp_path, monkeypatch)
    def fail_spawn(*args, **kwargs):
        assert _slot_held(scratch)
        raise OSError("spawn failed")
    monkeypatch.setattr(harness.subprocess, "Popen", fail_spawn)
    with pytest.raises(harness.BrowserHarnessExecutionError) as caught:
        harness.execute_browser_harness(config, FIXTURES, scenario_filter=("PW01",))
    assert caught.value.failure_evidence["process_error"]["class"] == "OSError"
    assert caught.value.failure_evidence["scheduling"]["budget_seconds"] == 180
    assert not _slot_held(scratch)


def test_deadline_marker_precedes_actual_child_sigterm(tmp_path):
    progress = tmp_path / "progress.jsonl"
    code = """import os, signal, sys, time
from pathlib import Path
p = Path(sys.argv[1])
def terminate(signum, frame):
    with p.open('a') as stream: stream.write('SIGTERM\\n')
    sys.exit(7)
signal.signal(signal.SIGTERM, terminate)
print('READY', flush=True)
time.sleep(60)
"""
    proc = subprocess.Popen([sys.executable, "-c", code, str(progress)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    try:
        assert select.select([proc.stdout], [], [], 5)[0], "child readiness deadline"
        assert proc.stdout.readline().strip() == "READY"
        with pytest.raises(subprocess.TimeoutExpired) as caught:
            process_owner.communicate_owned(proc, timeout=0.05, grace=2,
                on_deadline=lambda: process_owner.append_progress_marker(progress, HARNESS_DEADLINE_MARKER))
        lines = progress.read_text().splitlines()
        assert json.loads(lines[0]) == HARNESS_DEADLINE_MARKER and lines[1:] == ["SIGTERM"]
        assert proc.returncode == 7 and caught.value.cleanup["child_reaped"]
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=2)
