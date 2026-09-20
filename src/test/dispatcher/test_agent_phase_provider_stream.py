"""Provider execution with source-owned liveness, streaming, and interruption.

A real composition phase was killed at closeout with `exit=143, timed_out=True`
after the one-hour stage deadline elapsed. The dispatcher-owned phase deadline
is gone, and so is the hard silence bound that once killed a healthy quiet stage.
These tests hold the line that a silent provider is warned about but never
terminated, that the bounds which remain (the absolute outer ceiling, a hard
stdout cap, a soft stderr capture cap, and operator interruption) still work,
and that mirroring output to an observer cannot corrupt captured bytes.

These run genuine subprocesses. Fakes cannot demonstrate that a process was
allowed to finish or that a process group was torn down.
"""

from __future__ import annotations

import inspect
from typing import Any, cast
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest

from agent_phase import provider as provider_module
from agent_phase.provider import (
    LivenessPolicy,
    ProviderInterrupted,
    ProviderLivenessExpired,
    Result,
)

def script(body: str, tmp_path: Path, name: str = "fake_provider.py") -> list[str]:
    path = tmp_path / name
    path.write_text(body)
    return [sys.executable, str(path)]


# -- dispatcher phase deadline is gone --------------------------------------


def test_provider_api_exposes_no_wall_clock() -> None:
    assert not hasattr(provider_module, "DEFAULT_STAGE_TIMEOUT_SECONDS")
    parameters = inspect.signature(provider_module.run).parameters
    # The contract is that no wall clock can be handed in, not that the
    # signature is frozen; an unrelated future parameter is not a regression.
    assert not [name for name in parameters if "timeout" in name or "deadline" in name]
    assert list(parameters)[:3] == ["argv", "prompt", "cwd"]


def test_result_has_no_timed_out_field() -> None:
    assert "timed_out" not in Result._fields
    assert Result._fields == (
        "exit_code",
        "stdout",
        "stderr",
        "truncated",
        "started",
        "ended",
        "stderr_truncated",
    )
    compatible = Result(0, b"", b"", False, 0.0, 1.0)
    assert len(compatible) == 7
    assert tuple(compatible) == (0, b"", b"", False, 0.0, 1.0, False)
    assert compatible.ok is True
    assert compatible.stderr_truncated is False
    assert compatible.cleanup is None
    enriched = Result(
        0,
        b"",
        b"",
        False,
        0.0,
        1.0,
        cleanup={"cleanup_proven": True},
    )
    assert enriched.cleanup == {"cleanup_proven": True}
    replaced = enriched._replace(stdout=b"replacement")
    assert replaced.cleanup == enriched.cleanup
    assert tuple(replaced) == (0, b"replacement", b"", False, 0.0, 1.0, False)
    assert Result(0, b"", b"", True, 0.0, 1.0).ok is False
    assert Result(1, b"", b"", False, 0.0, 1.0).ok is False


def test_liveness_policy_is_immutable_and_silence_is_only_advisory() -> None:
    generic = provider_module.DEFAULT_LIVENESS_POLICY
    override = LivenessPolicy(0.25, 1.0)

    assert isinstance(generic, LivenessPolicy)
    # Production has no hard silence bound at all.
    assert generic.inactivity_seconds is None
    assert generic.inactivity is None
    # Silence is observed, not enforced.
    assert generic.advisory_silence_seconds == 900
    assert generic.advisory_interval_seconds == 900
    # The absolute outer safety ceiling is unchanged and still enforced.
    assert generic.outer_ceiling_seconds == 90_000

    assert inspect.signature(provider_module.run).parameters[
        "liveness_policy"
    ].default is None
    assert provider_module._effective_liveness_policy(None) is generic
    assert provider_module._effective_liveness_policy(override) is override
    # The positional spelling still means (inactivity, outer ceiling), so an
    # explicitly injected finite hard bound remains available.
    assert override.inactivity_seconds == 0.25
    assert override.outer_ceiling_seconds == 1.0

    with pytest.raises(AttributeError):
        setattr(generic, "inactivity_seconds", 1)
    with pytest.raises(TypeError):
        LivenessPolicy(advisory_interval_seconds=cast(Any, None))
    with pytest.raises(ValueError):
        LivenessPolicy(advisory_silence_seconds=0)
    with pytest.raises(TypeError):
        LivenessPolicy(inactivity_seconds=cast(Any, True))


def test_silent_provider_expires_distinctly_and_is_reaped(
    tmp_path: Path,
) -> None:
    argv = script(
        "import time\n"
        "time.sleep(30)\n",
        tmp_path,
    )
    started = time.monotonic()

    with pytest.raises(ProviderLivenessExpired) as raised:
        provider_module.run(
            argv,
            b"",
            tmp_path,
            liveness_policy=LivenessPolicy(0.15, 2.0),
        )

    expired = raised.value
    assert time.monotonic() - started < 3.0
    assert not isinstance(expired, ProviderInterrupted)
    assert expired.reason == "inactivity"
    assert expired.policy == LivenessPolicy(0.15, 2.0)
    assert expired.elapsed_seconds >= expired.silent_seconds >= 0.15
    assert expired.last_activity_stream is None
    assert expired.termination["reason"] == "inactivity"
    assert expired.cleanup["wrapper_reaped"] is True
    assert expired.cleanup["readers_joined"] is True
    assert expired.stdout == b""
    assert expired.stderr == b""


def test_outer_ceiling_is_distinct_from_inactivity(
    tmp_path: Path,
) -> None:
    argv = script(
        "import sys, time\n"
        "while True:\n"
        "    sys.stdout.write('progress\\n')\n"
        "    sys.stdout.flush()\n"
        "    time.sleep(0.02)\n",
        tmp_path,
    )

    with pytest.raises(ProviderLivenessExpired) as raised:
        provider_module.run(
            argv,
            b"",
            tmp_path,
            liveness_policy=LivenessPolicy(0.15, 0.35),
        )

    expired = raised.value
    assert expired.reason == "outer_ceiling"
    assert expired.elapsed_seconds >= 0.35
    assert expired.silent_seconds < 0.15
    assert b"progress" in expired.stdout


def test_slow_stdout_progress_prevents_inactivity_expiry(
    tmp_path: Path,
) -> None:
    argv = script(
        "import sys, time\n"
        "for index in range(5):\n"
        "    sys.stdout.write(f'progress {index}\\n')\n"
        "    sys.stdout.flush()\n"
        "    time.sleep(0.05)\n",
        tmp_path,
    )

    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        liveness_policy=LivenessPolicy(0.15, 2.0),
    )

    assert result.ok is True
    assert result.stdout.count(b"progress") == 5


def test_stderr_activity_prevents_inactivity_expiry(
    tmp_path: Path,
) -> None:
    argv = script(
        "import sys, time\n"
        "for index in range(5):\n"
        "    sys.stderr.write(f'diagnostic {index}\\n')\n"
        "    sys.stderr.flush()\n"
        "    time.sleep(0.05)\n"
        "sys.stdout.write('finished\\n')\n"
        "sys.stdout.flush()\n",
        tmp_path,
    )

    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        liveness_policy=LivenessPolicy(0.15, 2.0),
    )

    assert result.ok is True
    assert result.stdout == b"finished\n"
    assert result.stderr.count(b"diagnostic") == 5


def test_partial_bytes_are_carried_by_liveness_expiry(
    tmp_path: Path,
) -> None:
    argv = script(
        "import sys, time\n"
        "sys.stdout.buffer.write(b'partial bytes')\n"
        "sys.stdout.buffer.flush()\n"
        "sys.stderr.buffer.write(b'partial diagnostic')\n"
        "sys.stderr.buffer.flush()\n"
        "time.sleep(30)\n",
        tmp_path,
    )

    with pytest.raises(ProviderLivenessExpired) as raised:
        provider_module.run(
            argv,
            b"",
            tmp_path,
            liveness_policy=LivenessPolicy(0.15, 2.0),
        )

    expired = raised.value
    assert expired.stdout == b"partial bytes"
    assert expired.stderr == b"partial diagnostic"
    assert expired.truncated is False
    assert expired.stderr_truncated is False


def _assert_pid_disappears(pid: int) -> None:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.02)
    pytest.fail(f"process {pid} survived provider cleanup")


def test_normal_parent_exit_cleans_term_ignoring_generic_descendant(
    tmp_path: Path,
) -> None:
    pid_file = tmp_path / "generic-descendant.pid"
    ignore_term = (
        "import os, signal, time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"Path({str(pid_file)!r}).write_text(str(os.getpid())); "
        "time.sleep(30)"
    )
    argv = script(
        "import subprocess, sys, time\n"
        f"child = subprocess.Popen([sys.executable, '-c', {ignore_term!r}])\n"
        "deadline = time.monotonic() + 5\n"
        f"while not __import__('pathlib').Path({str(pid_file)!r}).exists() and time.monotonic() < deadline: time.sleep(0.01)\n"
        f"if not __import__('pathlib').Path({str(pid_file)!r}).exists(): raise SystemExit('descendant not ready')\n"
        "print('parent complete', flush=True)\n",
        tmp_path,
    )

    result = provider_module.run(argv, b"", tmp_path)

    assert result.ok is True
    assert result.stdout == b"parent complete\n"
    assert result.cleanup is not None
    assert result.cleanup["cleanup_proven"] is True
    assert result.cleanup["parent_reaped"] is True
    assert result.cleanup["outer_group_absent"] is True
    assert result.cleanup["readers_joined"] is True
    assert result.cleanup["writer_joined"] is True
    assert any(
        item["pgid"] == result.cleanup["termination"]["outer_pgid"]
        and item["status"] == "sent"
        for item in result.cleanup["termination"]["kill"]
    )
    assert pid_file.exists()
    _assert_pid_disappears(int(pid_file.read_text()))


def test_normal_managed_exit_cleans_ready_registered_nested_group(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ready = tmp_path / "managed-descendant.ready.json"
    wrapper = script(
        "import os, subprocess, sys, time\n"
        f"ready = {str(ready)!r}\n"
        "child_code = (\n"
        "    'import json,os,signal,time; from pathlib import Path; '\n"
        "    'signal.signal(signal.SIGTERM, signal.SIG_IGN); '\n"
        "    f'p=Path({ready!r}); t=p.with_name(p.name+\".tmp\"); '\n"
        "    't.write_text(json.dumps({\"ready\":True,\"pid\":os.getpid(),\"pgid\":os.getpgrp()})); '\n"
        "    'os.replace(t,p); time.sleep(30)'\n"
        ")\n"
        "child = subprocess.Popen([sys.executable, '-c', child_code], start_new_session=True)\n"
        "deadline = time.monotonic() + 5\n"
        "while not __import__('pathlib').Path(ready).exists() and time.monotonic() < deadline: time.sleep(0.01)\n"
        "if not __import__('pathlib').Path(ready).exists(): raise SystemExit('nested group not ready')\n"
        "fd = int(os.environ['AGENT_CENTRAL_ANTIGRAVITY_ACTIVITY_FD'])\n"
        "os.write(fd, f'G:{child.pid}:{child.pid}\\n'.encode('ascii'))\n"
        "print('managed complete', flush=True)\n",
        tmp_path,
        "managed_wrapper.py",
    )
    monkeypatch.setattr(
        provider_module, "_is_managed_antigravity_launcher", lambda _argv, _cwd: True
    )
    nested_pgid: int | None = None
    try:
        result = provider_module.run(wrapper, b"", tmp_path)
        marker = json.loads(ready.read_text(encoding="utf-8"))
        assert marker["ready"] is True
        nested_pgid = marker["pgid"]
        assert result.ok is True
        assert result.stdout == b"managed complete\n"
        assert result.cleanup is not None
        assert result.cleanup["cleanup_proven"] is True
        assert result.cleanup["nested_groups_registered"] == 1
        assert result.cleanup["nested_groups_absent"] is True
        assert any(
            item["pgid"] == nested_pgid and item["status"] == "sent"
            for item in result.cleanup["termination"]["kill"]
        )
        _assert_pid_disappears(marker["pid"])
    finally:
        if nested_pgid is not None:
            try:
                os.killpg(nested_pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def test_cleanup_failure_is_non_success_with_exact_partial_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Keep the real process boundary, but make the final existence proof
    # honestly unavailable. The bounded grace is shortened only for this
    # adverse-path test; the source-owned production constant remains long.
    monkeypatch.setattr(provider_module, "KILL_GRACE_SECONDS", 0.02)
    monkeypatch.setattr(
        provider_module, "_group_probe", lambda _pgid: "permission_denied"
    )
    argv = script(
        "import sys\n"
        "sys.stdout.write('partial output')\n"
        "sys.stdout.flush()\n",
        tmp_path,
    )

    with pytest.raises(provider_module.ProviderCleanupFailed) as raised:
        provider_module.run(argv, b"", tmp_path)

    failed = raised.value
    assert failed.stdout == b"partial output"
    assert failed.stderr == b""
    assert failed.truncated is False
    assert failed.stderr_truncated is False
    assert failed.cleanup["cleanup_proven"] is False
    assert failed.cleanup["verified_absence"] is False
    assert "process_group_absence_unverified" in failed.cleanup["failure_reasons"]


def test_post_cap_stderr_activity_is_counted_before_discard(
    tmp_path: Path,
) -> None:
    argv = script(
        "import sys, time\n"
        "for _ in range(20):\n"
        "    sys.stderr.buffer.write(b'eeee')\n"
        "    sys.stderr.buffer.flush()\n"
        "    time.sleep(0.03)\n"
        "time.sleep(30)\n",
        tmp_path,
    )
    started = time.monotonic()

    with pytest.raises(ProviderLivenessExpired) as raised:
        provider_module.run(
            argv,
            b"",
            tmp_path,
            max_output=8,
            liveness_policy=LivenessPolicy(0.12, 2.0),
        )

    expired = raised.value
    elapsed = time.monotonic() - started
    # If discarded stderr reads did not count, this would expire around 0.12s;
    # the provider remains live through the 20 post-cap writes first.
    assert elapsed >= 0.45
    assert expired.stderr == b"e" * 8
    assert expired.stderr_truncated is True
    assert expired.cleanup["activity_reads"] >= 20


def _managed_antigravity_argv() -> list[str]:
    root = Path(__file__).resolve().parents[3]
    return [str(root / "bin/antigravity-profile"), "gemini-3.7-flash-medium", "-p"]


def _fake_agy(tmp_path: Path, body: str) -> Path:
    executable = tmp_path / "agy"
    executable.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    executable.chmod(0o755)
    return executable


def test_managed_antigravity_protocol_activity_keeps_outer_provider_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recognized progress events refresh liveness; keepalives are not progress.

    `heartbeat` events used to be credited as activity, which let generic wrapper
    chatter postpone expiry indefinitely. Only `agent_response` counts here, and
    it is emitted often enough to hold an explicitly injected finite hard bound.
    """
    _fake_agy(
        tmp_path,
        "import json, sys, time\n"
        "for _ in range(8):\n"
        "    print(json.dumps({'type': 'heartbeat'}), flush=True)\n"
        "    print(json.dumps({'type': 'agent_response', 'text_delta': ''}), flush=True)\n"
        "    time.sleep(0.05)\n"
        "print(json.dumps({'type': 'result', 'status': 'SUCCESS', 'result': 'done'}), flush=True)\n",
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    result = provider_module.run(
        _managed_antigravity_argv(),
        b"outer prompt",
        Path(__file__).resolve().parents[3],
        liveness_policy=LivenessPolicy(0.6, 2.0),
    )

    assert result.ok is True
    assert result.stdout == b"done\n"


def test_managed_antigravity_expiry_reaps_registered_nested_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid_file = tmp_path / "descendant.pid"
    _fake_agy(
        tmp_path,
        "import os, signal, subprocess, sys, time\n"
        f"child = subprocess.Popen([sys.executable, '-c', {('import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)')!r}])\n"
        f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
        "print('{\"type\": \"heartbeat\"}', flush=True)\n"
        "time.sleep(30)\n",
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    with pytest.raises(ProviderLivenessExpired) as raised:
        provider_module.run(
            _managed_antigravity_argv(),
            b"outer prompt",
            Path(__file__).resolve().parents[3],
            liveness_policy=LivenessPolicy(0.6, 2.5),
        )

    expired = raised.value
    assert expired.cleanup["nested_groups_registered"] >= 1
    assert expired.cleanup["nested_groups_targeted"] >= 1
    assert expired.termination["term"]
    if pid_file.exists():
        descendant_pid = int(pid_file.read_text())
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                os.kill(descendant_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.02)
        else:
            pytest.fail("registered nested descendant survived liveness cleanup")


def test_cleanup_includes_registration_arriving_during_wrapper_term_grace(
    tmp_path: Path,
) -> None:
    ignore_term = script(
        "import signal,time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "time.sleep(30)\n",
        tmp_path,
        "ignore_term.py",
    )
    wrapper = subprocess.Popen(ignore_term, start_new_session=True)
    nested = subprocess.Popen(ignore_term, start_new_session=True)
    registrations: dict[int, int] = {}
    lock = threading.Lock()

    def register_late() -> None:
        time.sleep(0.04)
        with lock:
            registrations[nested.pid] = nested.pid

    reader = threading.Thread(target=register_late, daemon=True)
    reader.start()
    termination, cleanup = provider_module._cleanup_process_groups(
        wrapper,
        registrations,
        registration_lock=lock,
        activity_thread=reader,
        term_grace=0.12,
        kill_grace=0.12,
        reason="test_late_registration",
    )
    nested.wait(timeout=2.0)

    assert wrapper.poll() is not None
    assert nested.returncode == -signal.SIGKILL
    assert termination["nested_pgids"] == [nested.pid]
    assert cleanup["nested_groups_registered"] == 1
    assert any(
        item["pgid"] == nested.pid and item["status"] in {"sent", "absent"}
        for item in termination["kill"]
    )


def test_managed_antigravity_writer_fd_is_not_inherited_by_agy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "activity-env-visible"
    _fake_agy(
        tmp_path,
        "import os, sys, json\n"
        f"if os.environ.get('AGENT_CENTRAL_ANTIGRAVITY_ACTIVITY_FD'): open({str(marker)!r}, 'w').write('leaked')\n"
        "print(json.dumps({'type': 'result', 'status': 'SUCCESS', 'result': 'safe'}), flush=True)\n",
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    result = provider_module.run(
        _managed_antigravity_argv(),
        b"outer prompt",
        Path(__file__).resolve().parents[3],
        liveness_policy=LivenessPolicy(0.6, 2.0),
    )

    assert result.stdout == b"safe\n"
    assert not marker.exists()


def test_a_slow_provider_is_allowed_to_finish(tmp_path: Path) -> None:
    """The old deadline was the only thing that could have stopped this."""
    argv = script(
        "import sys, time\n"
        "time.sleep(1.5)\n"
        "sys.stdout.write('finished after sleeping\\n')\n",
        tmp_path,
    )
    result = provider_module.run(argv, b"", tmp_path)

    assert result.exit_code == 0
    assert result.ok is True
    assert result.stdout == b"finished after sleeping\n"
    assert result.ended - result.started >= 1.5


def test_output_overflow_still_terminates_and_reports_truncation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The output cap keeps its own contract, and it is not a timeout."""
    argv = script(
        "import sys\n"
        "while True:\n"
        "    sys.stdout.write('x' * 4096)\n"
        "    sys.stdout.flush()\n",
        tmp_path,
    )
    processes: list[subprocess.Popen] = []
    real_popen = provider_module.subprocess.Popen

    def watched_popen(*arguments, **keywords):
        process = real_popen(*arguments, **keywords)
        processes.append(process)
        return process

    monkeypatch.setattr(provider_module.subprocess, "Popen", watched_popen)
    result = provider_module.run(argv, b"", tmp_path, max_output=64 * 1024)

    assert result.truncated is True
    assert result.ok is False
    assert len(result.stdout) <= 64 * 1024
    assert processes, "no provider process was launched"
    assert processes[0].poll() is not None


def test_stdout_overflow_wins_a_simultaneous_liveness_race(
    tmp_path: Path,
) -> None:
    argv = script(
        "import sys, time\n"
        "sys.stdout.buffer.write(b'x' * 4096)\n"
        "sys.stdout.buffer.flush()\n"
        "time.sleep(30)\n",
        tmp_path,
    )

    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        max_output=64,
        liveness_policy=LivenessPolicy(0.01, 0.2),
    )

    assert result.truncated is True
    assert result.ok is False
    assert len(result.stdout) == 64


def test_stderr_overflow_is_drained_before_final_stdout(tmp_path: Path) -> None:
    """Diagnostic overflow must not fill the pipe and strand final output."""
    cap = 8 * 1024
    stderr_bytes = cap + 1024 * 1024
    argv = script(
        "import sys, time\n"
        f"sys.stderr.buffer.write(b'e' * {stderr_bytes})\n"
        "sys.stderr.buffer.flush()\n"
        "time.sleep(0.25)\n"
        "sys.stdout.buffer.write(b'final stdout\\n')\n",
        tmp_path,
    )
    mirrored: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        max_output=cap,
        on_output=lambda stream, chunk: mirrored[stream].append(chunk),
    )

    assert result.exit_code == 0
    assert result.stdout == b"final stdout\n"
    assert result.stderr == b"e" * cap
    assert b"".join(mirrored["stdout"]) == result.stdout
    assert b"".join(mirrored["stderr"]) == result.stderr
    assert result.stderr_truncated is True
    assert result.truncated is False
    assert result.ok is True


# -- streaming ---------------------------------------------------------------


def test_output_is_mirrored_before_the_process_exits(tmp_path: Path) -> None:
    argv = script(
        "import sys, time\n"
        "sys.stdout.write('early\\n')\n"
        "sys.stdout.flush()\n"
        "time.sleep(4)\n"
        "sys.stdout.write('late\\n')\n",
        tmp_path,
    )
    seen: list[tuple[float, str, bytes]] = []
    result = provider_module.run(
        argv, b"", tmp_path,
        on_output=lambda stream, chunk: seen.append((time.time(), stream, chunk)),
    )

    assert seen, "no output was mirrored"
    first_at, first_stream, first_chunk = seen[0]
    assert first_stream == "stdout"
    assert b"early" in first_chunk
    # Printing captured bytes after the process exits would put this at the end.
    # The margin is wide so a loaded machine cannot make a passing run look like
    # a failing one; the defect this catches is a ~4s gap, not a ~0.1s one.
    assert first_at < result.ended - 3.0
    assert result.stdout == b"early\nlate\n"


def test_both_streams_are_labelled(tmp_path: Path) -> None:
    argv = script(
        "import sys\n"
        "sys.stderr.write('to stderr\\n')\n"
        "sys.stderr.flush()\n"
        "sys.stdout.write('to stdout\\n')\n",
        tmp_path,
    )
    seen: dict[str, bytes] = {}

    def record(stream: str, chunk: bytes) -> None:
        seen[stream] = seen.get(stream, b"") + chunk

    result = provider_module.run(argv, b"", tmp_path, on_output=record)

    assert seen["stdout"] == result.stdout == b"to stdout\n"
    assert seen["stderr"] == result.stderr == b"to stderr\n"


def test_mirroring_does_not_change_captured_bytes(tmp_path: Path) -> None:
    argv = script(
        "import sys\n"
        "for index in range(200):\n"
        "    sys.stdout.write(f'line {index}\\n')\n"
        "    sys.stderr.write(f'err {index}\\n')\n",
        tmp_path,
    )
    silent = provider_module.run(argv, b"", tmp_path)
    watched = provider_module.run(
        argv, b"", tmp_path, on_output=lambda stream, chunk: None
    )

    assert watched.stdout == silent.stdout
    assert watched.stderr == silent.stderr
    assert watched.exit_code == silent.exit_code


def test_a_raising_observer_cannot_truncate_the_evidence(tmp_path: Path) -> None:
    """The guard is in the reader thread, not in the observer's own wrapping."""
    argv = script(
        "import sys\n"
        "for index in range(500):\n"
        "    sys.stdout.write(f'line {index}\\n')\n",
        tmp_path,
    )
    silent = provider_module.run(argv, b"", tmp_path)

    def hostile(stream: str, chunk: bytes) -> None:
        raise MemoryError("observer exploded")

    watched = provider_module.run(argv, b"", tmp_path, on_output=hostile)

    assert watched.stdout == silent.stdout
    assert watched.truncated is False
    assert watched.ok is True


def test_the_observer_never_sees_bytes_the_artifact_lacks(tmp_path: Path) -> None:
    """Display is a mirror of the record, never a fuller version of it."""
    argv = script(
        "import sys\n"
        "for index in range(400):\n"
        "    sys.stdout.write('y' * 512 + '\\n')\n"
        "    sys.stdout.flush()\n",
        tmp_path,
    )
    mirrored: list[bytes] = []
    result = provider_module.run(
        argv, b"", tmp_path, max_output=8 * 1024,
        on_output=lambda stream, chunk: mirrored.append(chunk),
    )

    assert b"".join(mirrored) == result.stdout
    assert len(result.stdout) <= 8 * 1024


# -- operator interruption ---------------------------------------------------


def test_interruption_terminates_the_provider_and_keeps_partial_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    argv = script(
        "import sys, time\n"
        "sys.stderr.buffer.write(b'e' * (8 * 1024 + 1024 * 1024))\n"
        "sys.stderr.buffer.flush()\n"
        "sys.stdout.write('started\\n')\n"
        "sys.stdout.flush()\n"
        "time.sleep(120)\n",
        tmp_path,
    )
    processes: list[subprocess.Popen] = []
    real_popen = provider_module.subprocess.Popen

    def watched_popen(*arguments, **keywords):
        process = real_popen(*arguments, **keywords)
        processes.append(process)
        return process

    monkeypatch.setattr(provider_module.subprocess, "Popen", watched_popen)

    # Stands in for the operator's Ctrl-C landing in the dispatcher's wait loop.
    # It fires exactly once: `time` is shared with `subprocess`'s own wait loop,
    # and an interrupt that repeated would land inside the teardown it triggers.
    real_sleep = provider_module.time.sleep
    fired: list[bool] = []
    seen: list[bytes] = []

    def interrupt(seconds: float) -> None:
        # Interrupt a stage that has already produced output, which is the case
        # worth covering: the operator gives up on a long-running provider.
        if seen and not fired:
            fired.append(True)
            raise KeyboardInterrupt
        real_sleep(seconds)

    monkeypatch.setattr(provider_module.time, "sleep", interrupt)

    started = time.time()
    with pytest.raises(ProviderInterrupted) as raised:
        provider_module.run(
            argv,
            b"",
            tmp_path,
            max_output=8 * 1024,
            on_output=lambda stream, chunk: seen.append(chunk)
            if stream == "stdout" else None,
        )

    assert time.time() - started < 30, "did not return promptly"
    assert processes, "no provider process was launched"
    # `_terminate` signals the process *group* and reaps it, so an interrupted
    # run cannot leave the provider running after the dispatcher exits.
    assert processes[0].poll() is not None
    assert b"started" in raised.value.stdout
    assert len(raised.value.stderr) == 8 * 1024
    assert raised.value.truncated is False
    assert raised.value.stderr_truncated is True


def test_interruption_is_not_a_transport_failure_type() -> None:
    """`ProviderInterrupted` must not be swallowed by ordinary error handling."""
    assert issubclass(ProviderInterrupted, BaseException)
    assert not issubclass(ProviderInterrupted, Exception)

# -- meaningful-activity accounting and the managed inactivity bound ---------


def _load_antigravity_launcher():
    import importlib.util

    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "antigravity_profile_for_liveness_test",
        root / "libexec/antigravity_profile.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: the module defines frozen dataclasses, and
    # `dataclasses` resolves annotations through `sys.modules[cls.__module__]`.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_no_production_hard_silence_bound_is_reintroduced() -> None:
    """Silence must not be a kill signal for any provider, managed or not.

    On 2026-09-04 a healthy Claude work stage that had already modified nineteen
    tracked paths was killed at silent=900.006s with stdout_bytes=0 while running
    a legitimate quiet foreground command. No per-provider hard silence bound may
    come back, and the upstream 24h print timeout stays an upstream limit rather
    than something this watchdog races.
    """
    launcher = _load_antigravity_launcher()
    upstream = launcher.ANTIGRAVITY_PRINT_TIMEOUT
    assert upstream.endswith("h")
    assert float(upstream[:-1]) * 3600.0 == 86_400.0

    for retired in (
        "ANTIGRAVITY_LIVENESS_POLICY",
        "ANTIGRAVITY_INACTIVITY_SECONDS",
        "ANTIGRAVITY_OUTER_CEILING_SECONDS",
        "DEFAULT_INACTIVITY_SECONDS",
    ):
        assert not hasattr(provider_module, retired), (
            f"{retired} encodes the disproven hard-silence premise"
        )

    # The managed launcher gets exactly the same advisory policy as anything else.
    assert (
        provider_module._effective_liveness_policy(None)
        is provider_module.DEFAULT_LIVENESS_POLICY
    )
    assert provider_module.DEFAULT_LIVENESS_POLICY.inactivity_seconds is None


def _fresh_activity() -> dict:
    return {
        "last": 0.0,
        "stream": None,
        "reads": 0,
        "bytes": 0,
        "kinds": {
            "stdout": 0,
            "stderr": 0,
            "nested.stdout": 0,
            "nested.stderr": 0,
            "nested.protocol": 0,
        },
        "non_progress": {
            "nested.pgid": 0,
            "waiting": 0,
            "unknown": 0,
            "oversized": 0,
            "partial": 0,
            "discarded": 0,
        },
    }


def _drain_tokens(payload: bytes, wrapper_pid: int = 1) -> tuple[dict, dict]:
    """Run the real activity reader over an exact byte payload."""
    read_fd, write_fd = os.pipe()
    activity = _fresh_activity()
    nested: dict[int, int] = {}
    lock = threading.Lock()
    thread = threading.Thread(
        target=provider_module._drain_activity,
        args=(read_fd, wrapper_pid, lock, activity, nested),
        daemon=True,
    )
    thread.start()
    os.write(write_fd, payload)
    os.close(write_fd)
    thread.join(timeout=5.0)
    assert not thread.is_alive()
    return activity, nested


def test_non_progress_activity_tokens_do_not_postpone_inactivity() -> None:
    """Unknown, malformed, oversized, and partial reads are noise, not progress."""
    oversized = b"X" * (provider_module.ACTIVITY_MAX_TOKEN_BYTES + 4) + b"\n"
    payload = (
        b"\n"                         # empty line: unknown token
        b"Q\n"                        # unknown single-character token
        b"O extra\n"                  # near-miss of a real progress token
        b"G:notanumber:7\n"           # malformed registration
        b"G:0:0\n"                    # invalid PIDs
        + oversized                   # oversized token
        + b"G:999999999:999999999\n"  # well-formed but unresolvable group
        + b"partial-without-newline"  # unterminated remainder at EOF
    )

    activity, nested = _drain_tokens(payload)

    assert activity["last"] == 0.0, "no non-progress read may refresh liveness"
    assert activity["stream"] is None
    assert activity["reads"] == 0
    assert activity["bytes"] == 0
    assert activity["kinds"] == _fresh_activity()["kinds"]
    assert nested == {}
    non_progress = activity["non_progress"]
    assert non_progress["oversized"] == 1
    assert non_progress["unknown"] == 6
    assert non_progress["partial"] == 1
    assert non_progress["nested.pgid"] == 0


def test_waiting_tokens_are_counted_but_never_refresh_meaningful_activity() -> None:
    """Generic `waiting`/keepalive chatter must not postpone the advisory clock."""
    activity, nested = _drain_tokens(b"W\nW\nW\n")

    assert activity["last"] == 0.0
    assert activity["reads"] == 0
    assert activity["stream"] is None
    assert activity["non_progress"]["waiting"] == 3
    # Counted under its own class, not lumped in with unknown noise.
    assert activity["non_progress"]["unknown"] == 0
    assert nested == {}


def test_recognized_progress_tokens_do_refresh_meaningful_activity() -> None:
    activity, _ = _drain_tokens(b"O\nE\nP\n")

    assert activity["last"] > 0.0
    assert activity["reads"] == 3
    assert activity["kinds"]["nested.stdout"] == 1
    assert activity["kinds"]["nested.stderr"] == 1
    assert activity["kinds"]["nested.protocol"] == 1
    assert activity["non_progress"] == _fresh_activity()["non_progress"]


def test_custody_only_registration_is_kept_for_teardown_but_is_not_progress() -> None:
    """A valid nested group is still captured, yet registration alone is silence."""
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    try:
        token = f"G:{child.pid}:{child.pid}\n".encode("ascii")
        activity, nested = _drain_tokens(token, wrapper_pid=os.getpid())

        # Custody is recorded, so teardown can still reach the group.
        assert nested == {child.pid: child.pid}
        # Liveness is not: a wrapper that only registers groups is stalled.
        assert activity["last"] == 0.0
        assert activity["reads"] == 0
        assert activity["stream"] is None
        assert activity["non_progress"]["nested.pgid"] == 1
    finally:
        child.kill()
        child.wait(timeout=5.0)


def test_late_valid_registration_is_still_captured_without_being_progress() -> None:
    """Item 4: a registration arriving after real progress adds custody only."""
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    try:
        read_fd, write_fd = os.pipe()
        activity = _fresh_activity()
        nested: dict[int, int] = {}
        lock = threading.Lock()
        thread = threading.Thread(
            target=provider_module._drain_activity,
            args=(read_fd, os.getpid(), lock, activity, nested),
            daemon=True,
        )
        thread.start()
        os.write(write_fd, b"O\n")
        deadline = time.monotonic() + 5.0
        while activity["last"] == 0.0 and time.monotonic() < deadline:
            time.sleep(0.01)
        with lock:
            after_progress = activity["last"]
        assert after_progress > 0.0

        time.sleep(0.05)
        os.write(write_fd, f"G:{child.pid}:{child.pid}\n".encode("ascii"))
        os.close(write_fd)
        thread.join(timeout=5.0)
        assert not thread.is_alive()

        assert nested == {child.pid: child.pid}
        # The later registration did not move liveness forward.
        assert activity["last"] == after_progress
        assert activity["reads"] == 1
        assert activity["kinds"]["nested.stdout"] == 1
        assert activity["non_progress"]["nested.pgid"] == 1
    finally:
        child.kill()
        child.wait(timeout=5.0)


def test_recognized_nested_tokens_are_the_only_pipe_progress() -> None:
    """Item 2 (protocol half): O/E/P are progress; anything else is not."""
    activity, nested = _drain_tokens(b"O\nE\nP\nO\nZ\n")

    assert activity["last"] > 0.0
    assert activity["stream"] == "nested.stdout"
    assert activity["reads"] == 4
    assert activity["bytes"] == 8
    assert activity["kinds"]["nested.stdout"] == 2
    assert activity["kinds"]["nested.stderr"] == 1
    assert activity["kinds"]["nested.protocol"] == 1
    assert activity["non_progress"]["unknown"] == 1
    assert nested == {}


def test_buffer_overflow_noise_is_discarded_without_crediting_progress() -> None:
    payload = b"z" * (provider_module.ACTIVITY_MAX_BUFFER_BYTES + 4096)

    activity, _ = _drain_tokens(payload)

    assert activity["last"] == 0.0
    assert activity["reads"] == 0
    assert activity["non_progress"]["discarded"] >= 1


def test_progress_then_silence_expires_with_typed_activity_evidence(
    tmp_path: Path,
) -> None:
    """Item 1: real progress, then meaningful silence, then a bounded teardown."""
    argv = script(
        "import sys, time\n"
        "for _ in range(4):\n"
        "    sys.stdout.write('progress\\n')\n"
        "    sys.stdout.flush()\n"
        "    sys.stderr.write('diagnostic\\n')\n"
        "    sys.stderr.flush()\n"
        "    time.sleep(0.05)\n"
        "time.sleep(30)\n",
        tmp_path,
    )
    started = time.monotonic()

    with pytest.raises(ProviderLivenessExpired) as raised:
        provider_module.run(
            argv,
            b"",
            tmp_path,
            liveness_policy=LivenessPolicy(0.3, 8.0),
        )

    expired = raised.value
    # The recognized progress genuinely held the turn open past one interval.
    assert time.monotonic() - started >= 0.3
    assert expired.reason == "inactivity"
    assert expired.expiry_reason == "inactivity"
    assert expired.policy.inactivity_seconds == 0.3
    assert expired.silent_seconds >= 0.3
    # Bounded typed evidence is retained, with no raw activity payload.
    assert expired.last_activity_kind in {"stdout", "stderr"}
    assert expired.last_activity_age_seconds == expired.silent_seconds
    assert set(expired.activity_counts) == {"progress", "non_progress"}
    assert expired.activity_counts["progress"]["stdout"] >= 1
    assert expired.activity_counts["progress"]["stderr"] >= 1
    assert all(
        isinstance(value, int)
        for group in expired.activity_counts.values()
        for value in group.values()
    )
    assert expired.activity_facts["activity_counts"] == expired.activity_counts
    # Partial output survives the teardown as evidence.
    assert b"progress" in expired.stdout
    assert b"diagnostic" in expired.stderr
    assert expired.termination["reason"] == "inactivity"
    assert expired.termination["term"]


def test_periodic_progress_survives_several_inactivity_intervals(
    tmp_path: Path,
) -> None:
    """Item 2: periodic stdout/stderr keeps a turn alive and completes normally."""
    argv = script(
        "import sys, time\n"
        "for index in range(12):\n"
        "    sys.stdout.write(f'progress {index}\\n')\n"
        "    sys.stdout.flush()\n"
        "    sys.stderr.write('working\\n')\n"
        "    sys.stderr.flush()\n"
        "    time.sleep(0.06)\n",
        tmp_path,
    )
    started = time.monotonic()

    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        liveness_policy=LivenessPolicy(0.25, 20.0),
    )

    # Total runtime covers the inactivity interval several times over.
    assert time.monotonic() - started >= 0.72
    assert result.ok is True
    assert result.stdout.count(b"progress") == 12
    counts = result.cleanup["activity_counts"]
    assert counts["progress"]["stdout"] >= 1
    assert counts["progress"]["stderr"] >= 1
    assert counts["non_progress"] == {
        "nested.pgid": 0,
        "waiting": 0,
        "unknown": 0,
        "oversized": 0,
        "partial": 0,
        "discarded": 0,
    }
    assert result.cleanup["last_activity_kind"] in {"stdout", "stderr"}
    assert result.cleanup["last_activity_age_seconds"] >= 0.0
    assert result.cleanup["activity_reads"] >= 1
    # Meaningful output kept resetting the advisory clock, so nothing was warned.
    assert result.cleanup["stall_warnings"]["count"] == 0


# -- silence is advisory, never a production kill signal ---------------------


def _advisory_policy(
    silence: float = 0.1, interval: float = 0.1, ceiling: float = 30.0
) -> LivenessPolicy:
    """A production-shaped policy: no hard silence bound, only advisory notices."""
    return LivenessPolicy(
        inactivity_seconds=None,
        outer_ceiling_seconds=ceiling,
        advisory_silence_seconds=silence,
        advisory_interval_seconds=interval,
    )


def test_silent_generic_provider_is_warned_about_but_not_terminated(
    tmp_path: Path,
) -> None:
    """The exact 2026-09-04 false positive: quiet, then a clean success."""
    argv = script("import time\ntime.sleep(0.9)\nprint('done')\n", tmp_path)
    notices: list[dict] = []

    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        liveness_policy=_advisory_policy(),
        on_notice=notices.append,
    )

    assert result.ok is True
    assert result.exit_code == 0
    assert result.stdout == b"done\n"
    # It went quiet for many advisory intervals and was still allowed to finish.
    assert notices, "a silent provider must still be observable"
    assert result.cleanup["stall_warnings"]["count"] == len(notices)
    assert result.cleanup["termination"]["reason"] != "inactivity"


def test_silent_managed_antigravity_is_warned_about_but_not_terminated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_agy(
        tmp_path,
        "import json, time\n"
        "time.sleep(0.9)\n"
        "print(json.dumps({'type': 'result', 'status': 'SUCCESS', 'result': 'done'}), flush=True)\n",
    )
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    notices: list[dict] = []
    started = time.monotonic()

    # Not raising is the assertion: managed Antigravity used to be the provider
    # with the shortest leash, and a silent managed turn must now survive.
    result = provider_module.run(
        _managed_antigravity_argv(),
        b"outer prompt",
        Path(__file__).resolve().parents[3],
        liveness_policy=_advisory_policy(),
        on_notice=notices.append,
    )

    # It stayed silent across many advisory intervals and still ran to its own
    # exit rather than being cut short at the threshold.
    assert time.monotonic() - started >= 0.9
    assert result.cleanup["termination"]["reason"] != "inactivity"
    assert notices
    assert result.cleanup["stall_warnings"]["count"] == len(notices)
    # End-to-end managed wrapper success is covered by the dedicated managed-exit
    # and nested-group tests; this one owns the advisory-silence contract.


def test_a_quiet_local_foreground_test_outlasts_the_former_hard_bound(
    tmp_path: Path,
) -> None:
    """A legitimate quiet foreground command must survive past the old boundary.

    The former production bound was one silence interval. Here the fake test
    stays silent for many multiples of the advisory threshold, exactly as a real
    quiet suite or Nix evaluation would, and still reports success.
    """
    argv = script(
        "import time\ntime.sleep(1.0)\nprint('42 passed')\n",
        tmp_path,
    )
    notices: list[dict] = []
    started = time.monotonic()

    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        liveness_policy=_advisory_policy(silence=0.1, interval=0.1),
        on_notice=notices.append,
    )

    silent_span = time.monotonic() - started
    assert silent_span >= 1.0
    # Far beyond the point where the old policy would have killed it.
    assert silent_span > 5 * 0.1
    assert result.ok is True
    assert result.stdout == b"42 passed\n"


def test_advisory_notices_are_rate_limited_and_bounded(tmp_path: Path) -> None:
    argv = script("import time\ntime.sleep(1.2)\n", tmp_path)
    notices: list[dict] = []

    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        # POLL_SECONDS is 0.05, so a 0.3s interval must throttle hard.
        liveness_policy=_advisory_policy(silence=0.2, interval=0.3),
        on_notice=notices.append,
    )

    assert result.ok is True
    warnings = result.cleanup["stall_warnings"]
    # Rate-limited: nowhere near one notice per 0.05s poll.
    assert 1 <= warnings["count"] <= 6
    assert warnings["count"] == len(notices)
    assert warnings["threshold_seconds"] == 0.2
    assert warnings["interval_seconds"] == 0.3
    assert warnings["first_at"] is not None and warnings["last_at"] is not None
    # Bounded storage regardless of how long the stage stays quiet.
    assert len(warnings["notices"]) <= provider_module.STALL_WARNING_RECORD_LIMIT
    first = warnings["notices"][0]
    assert first["sequence"] == 1
    assert first["silent_seconds"] >= 0.2
    assert first["elapsed_seconds"] >= first["silent_seconds"]
    assert "last_activity_kind" in first
    assert first["at"].endswith("Z")
    # Advisory evidence changed nothing about the outcome.
    assert result.exit_code == 0


def test_stored_notices_are_capped_while_the_count_stays_truthful() -> None:
    policy = _advisory_policy(silence=0.01, interval=0.01)
    warnings = provider_module._new_stall_warnings(policy)
    limit = provider_module.STALL_WARNING_RECORD_LIMIT

    for index in range(limit + 25):
        provider_module._record_stall_warning(
            warnings,
            elapsed_seconds=float(index),
            silent_seconds=float(index),
            last_activity_kind=None,
            threshold_seconds=0.01,
            on_notice=None,
        )

    assert warnings["count"] == limit + 25
    assert len(warnings["notices"]) == limit
    assert warnings["notices"][-1]["sequence"] == limit


def test_a_raising_notice_observer_cannot_fail_the_stage(tmp_path: Path) -> None:
    argv = script("import time\ntime.sleep(0.5)\nprint('ok')\n", tmp_path)

    def explode(_notice: dict) -> None:
        raise RuntimeError("observer failure must stay advisory")

    result = provider_module.run(
        argv,
        b"",
        tmp_path,
        liveness_policy=_advisory_policy(),
        on_notice=explode,
    )

    assert result.ok is True
    assert result.stdout == b"ok\n"
    assert result.cleanup["stall_warnings"]["count"] >= 1


def test_meaningful_output_resets_the_advisory_silence_schedule(
    tmp_path: Path,
) -> None:
    chatty = script(
        "import sys, time\n"
        "for _ in range(20):\n"
        "    sys.stdout.write('tick\\n')\n"
        "    sys.stdout.flush()\n"
        "    time.sleep(0.02)\n",
        tmp_path,
    )
    notices: list[dict] = []

    result = provider_module.run(
        chatty,
        b"",
        tmp_path,
        liveness_policy=_advisory_policy(silence=0.25, interval=0.25),
        on_notice=notices.append,
    )

    assert result.ok is True
    assert result.stdout.count(b"tick") == 20
    # Output kept arriving well inside the threshold, so silence never matured.
    assert notices == []
    assert result.cleanup["stall_warnings"]["count"] == 0


def test_an_explicitly_injected_finite_hard_bound_still_expires(
    tmp_path: Path,
) -> None:
    """Requirement 8: the typed evidence path survives for accepted policies."""
    argv = script("import time\ntime.sleep(30)\n", tmp_path)

    with pytest.raises(ProviderLivenessExpired) as raised:
        provider_module.run(
            argv,
            b"",
            tmp_path,
            liveness_policy=LivenessPolicy(
                inactivity_seconds=0.2,
                outer_ceiling_seconds=20.0,
                advisory_silence_seconds=0.05,
                advisory_interval_seconds=0.05,
            ),
        )

    expired = raised.value
    assert expired.reason == "inactivity"
    assert expired.policy.inactivity_seconds == 0.2
    assert expired.elapsed_seconds >= expired.silent_seconds >= 0.2
    assert expired.termination["reason"] == "inactivity"
    # Advisory evidence is preserved alongside the typed expiry.
    assert expired.cleanup["stall_warnings"]["count"] >= 1
    assert expired.activity_counts["non_progress"]["unknown"] == 0
