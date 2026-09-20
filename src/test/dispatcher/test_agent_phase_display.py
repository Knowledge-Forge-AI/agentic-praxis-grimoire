"""The live display is an observer.

Everything here asserts one of two things: that an operator watching a run can
actually see it happen, or that what they see cannot change what the run did.
The second is the important one — a progress bar that can alter dispatcher truth
is worse than no progress bar.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import threading
import time

import pytest

from agent_phase import display as display_module
from agent_phase import provider as provider_module
from agent_phase.display import Display
from agent_phase.request import PhaseRequest
from agent_phase.routing import Endpoint, resolve

from test_agent_phase_dispatch import (
    FakeRunner, PHASE_ID, make_dispatcher, repository,
)


__all__ = ["repository"]

ROOT = Path(__file__).resolve().parents[3]
REQUEST = PhaseRequest("implementation_testing", "normal", "task")


class RecordingStream:
    """Stands in for stderr. Writes arrive from the display's writer thread."""

    def __init__(self) -> None:
        self.chunks: list[str] = []
        self.lock = threading.Lock()

    def write(self, text: str) -> int:
        with self.lock:
            self.chunks.append(text)
        return len(text)

    def flush(self) -> None:
        return None

    @property
    def text(self) -> str:
        with self.lock:
            return "".join(self.chunks)


class BrokenStream:
    def write(self, text: str) -> int:
        raise BrokenPipeError("downstream went away")

    def flush(self) -> None:
        raise BrokenPipeError("downstream went away")


def watched(repository: Path, tmp_path: Path, runner: FakeRunner, stream=None):
    stream = stream if stream is not None else RecordingStream()
    display = Display(stream, enabled=True)
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    dispatcher.display = display
    return dispatcher, display, stream


def writing(repo: Path, path: str, text: str):
    def hook(index: int) -> None:
        if index == 2:
            (repo / path).write_text(text)
    return hook


# -- what the operator sees --------------------------------------------------


def test_run_header_names_the_project_phase_and_routing(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher, display, stream = watched(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()
    text = stream.text

    assert repository.name in text
    assert PHASE_ID in text
    assert "implementation_testing" in text
    assert "normal" in text
    resolved = resolve(REQUEST, ROOT)
    for stage, endpoint in resolved["stages"].items():
        assert (
            f"  {stage + ':':<16}{endpoint['provider']} {endpoint['profile']}"
            in text
        )
    assert state["run_directory"] in text


def test_auxiliary_result_repair_has_distinct_one_turn_display() -> None:
    stream = RecordingStream()
    display = Display(stream, enabled=True)
    endpoint = Endpoint("antigravity", "gemini-3.7-flash-high")
    display.run_started(
        "project",
        "phase",
        "implementation_testing",
        "conserve_claude",
        {"result_repair": endpoint},
        lifecycle="standard",
        finalization_policy="publish",
        review_count=2,
        operation="result-repair auxiliary formatter (1 turn; semantic stages inherited)",
    )
    display.stage_started(
        1, "result_repair", "auxiliary_formatter", endpoint, stage_count=1
    )
    display.close()

    assert "operation:      result-repair auxiliary formatter" in stream.text
    assert "[1/1] result_repair" in stream.text
    assert "[1/5] result_repair" not in stream.text


def test_banner_request_resolved_route_and_invocations_share_one_mode_snapshot(
    repository: Path, tmp_path: Path
) -> None:
    request = PhaseRequest(
        "implementation_testing", "conserve_claude", "bounded task"
    )
    runner = FakeRunner()
    dispatcher, display, stream = watched(repository, tmp_path, runner)

    state = dispatcher.dispatch(PHASE_ID, request)
    display.close()
    run = Path(state["run_directory"])
    resolved = json.loads((run / "resolved.json").read_text())

    assert "execution mode: conserve_claude" in stream.text
    assert "execution mode: normal" not in stream.text
    assert json.loads((run / "request.json").read_text())["execution_mode"] == (
        "conserve_claude"
    )
    assert resolved["execution_mode"] == "conserve_claude"

    prefixes = {
        "plan": "01-plan",
        "plan_review": "02-plan-review",
        "work": "03-work",
        "final_review": "04-final-review",
        "closeout": "05-closeout",
    }
    for stage, prefix in prefixes.items():
        route = resolved["stages"][stage]
        meta = json.loads((run / f"{prefix}.meta.json").read_text())
        prompt = (run / f"{prefix}.prompt.md").read_text()
        assert meta["provider"] == route["provider"]
        assert meta["profile"] == route["profile"]
        assert "execution_mode: conserve_claude" in prompt
        assert f"{route['provider']} {route['profile']}" in stream.text


def test_every_stage_transition_is_numbered_out_of_five(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher, display, stream = watched(repository, tmp_path, FakeRunner())
    dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()
    text = stream.text

    for index, stage in enumerate(
        ["plan", "plan_review", "work", "final_review", "closeout"], start=1
    ):
        assert f"[{index}/5] {stage}" in text, stage
        assert f"[{stage}] complete" in text


def test_stage_lines_carry_role_provider_and_profile(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher, display, stream = watched(repository, tmp_path, FakeRunner())
    dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()
    text = stream.text

    for record in dispatcher.invocations:
        assert f"{record['role']} {record['provider']} {record['profile']}" in text


def test_checkpoints_and_outcome_are_reported(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher, display, stream = watched(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()
    text = stream.text

    assert "checkpoint complete: post_planning" in text
    assert "checkpoint complete: pre_final" in text
    assert "outcome: completed" in text
    assert "result.json" in text
    assert f"archive (succeeded): {state['archive_path']}" in text


def test_scanner_status_is_reported_without_implying_enforcement(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher, display, stream = watched(repository, tmp_path, FakeRunner())
    dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()

    assert "shadow only, never blocks a run" in stream.text


def test_git_closeout_progress_is_visible(repository: Path, tmp_path: Path) -> None:
    runner = FakeRunner(on_stage=writing(repository, "new.txt", "phase\n"))
    dispatcher, display, stream = watched(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()
    text = stream.text

    assert "phase delta is 1 path(s)" in text
    assert "new.txt" in text
    assert "committing — Apply phase changes" in text
    assert f"committed {state['commit']['sha']}" in text
    assert "push: starting normal push to origin refs/heads/" in text
    assert "push: no pre-existing unpushed ancestor commits" in text
    assert "push: succeeded" in text
    assert f"-> {state['commit']['sha']}" in text


def test_a_clean_run_says_there_was_no_delta(repository: Path, tmp_path: Path) -> None:
    dispatcher, display, stream = watched(repository, tmp_path, FakeRunner())
    dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()

    assert "no phase delta; nothing to commit" in stream.text


def test_a_blocked_run_shows_the_blocking_reason(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(closeout_outcome="blocked")
    dispatcher, display, stream = watched(repository, tmp_path, runner)
    with pytest.raises(Exception):
        dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()
    text = stream.text

    assert "outcome: blocked" in text
    assert "PROVIDER_OUTCOME_BLOCKED" in text


def test_provider_output_is_shown_with_stage_and_source_labels(
    repository: Path, tmp_path: Path
) -> None:
    display = Display(RecordingStream(), enabled=True)
    display.stage_started(3, "work", "primary", type("E", (), {
        "provider": "codex", "profile": "implementation-primary"})())
    display.stage_output("stdout", b"first line\nsecond ")
    display.stage_output("stderr", b"a warning\n")
    display.stage_output("stdout", b"line\n")
    display.stage_finished("work", 0, 1.25)
    display.close()
    text = display.stream.text if display.stream else ""

    assert "3/5 work out| first line" in text
    assert "3/5 work out| second line" in text
    assert "3/5 work err| a warning" in text
    assert "[work] complete — exit 0 in 1.2s" in text


def test_stderr_beyond_the_capture_cap_is_not_displayed(tmp_path: Path) -> None:
    stream = RecordingStream()
    display = Display(stream, enabled=True)
    display.stage_started(3, "work", "primary", type("E", (), {
        "provider": "codex", "profile": "implementation-primary"})())
    child = tmp_path / "stderr_overflow.py"
    child.write_text(
        "import sys\n"
        "sys.stderr.write('early sentinel\\n')\n"
        "sys.stderr.write('x' * 1024 + '\\npost-cap sentinel\\n')\n"
        "sys.stderr.flush()\n"
        "sys.stdout.write('finished\\n')\n"
    )

    result = provider_module.run(
        [sys.executable, str(child)],
        b"",
        tmp_path,
        max_output=64,
        on_output=display.stage_output,
    )
    display.stage_finished("work", result.exit_code, result.ended - result.started)
    display.close()

    assert result.stdout == b"finished\n"
    assert result.stderr_truncated is True
    assert "early sentinel" in stream.text
    assert "post-cap sentinel" not in stream.text
    assert display.dropped == 0


def test_a_trailing_partial_line_is_still_shown(repository: Path, tmp_path: Path) -> None:
    """Providers do not always end their last line."""
    stream = RecordingStream()
    display = Display(stream, enabled=True)
    display.stage_started(1, "plan", "primary", type("E", (), {
        "provider": "codex", "profile": "p"})())
    display.stage_output("stdout", b"no trailing newline")
    display.stage_finished("plan", 0, 0.5)
    display.close()

    assert "1/5 plan out| no trailing newline" in stream.text


# -- the display cannot change the run ---------------------------------------


def test_display_does_not_alter_artifacts_or_outcome(
    repository: Path, tmp_path: Path
) -> None:
    quiet_runner = FakeRunner()
    quiet = make_dispatcher(repository, tmp_path / "quiet", quiet_runner)
    quiet_state = quiet.dispatch(PHASE_ID, REQUEST)

    loud_runner = FakeRunner()
    loud, display, _ = watched(repository, tmp_path / "loud", loud_runner)
    loud_state = loud.dispatch(PHASE_ID, REQUEST)
    display.close()

    assert loud_state["complete"] == quiet_state["complete"] is True
    def normalize_invocations(records):
        normalized = []
        for record in records:
            copied = {**record, "argv": list(record["argv"])}
            if "--evidence-prefix" in copied["argv"]:
                index = copied["argv"].index("--evidence-prefix")
                copied["argv"][index + 1] = "<evidence-prefix>"
            normalized.append(copied)
        return normalized

    assert normalize_invocations(loud.invocations) == normalize_invocations(
        quiet.invocations
    )
    # Same prompt bytes once the two runs' own identities are normalised: the
    # display never reaches model context.
    def normalize(prompt: bytes, state: dict) -> bytes:
        return re.sub(
            rb"[0-9a-f]{32}", b"<nonce>",
            prompt.replace(state["run_id"].encode("utf-8"), b"<run-id>"),
        )

    for index, call in enumerate(loud_runner.calls):
        assert normalize(call["prompt"], loud_state) == normalize(
            quiet_runner.calls[index]["prompt"], quiet_state
        )

    for prefix in ["01-plan", "03-work", "05-closeout"]:
        loud_bytes = (Path(loud_state["run_directory"]) / f"{prefix}.stdout.md").read_bytes()
        quiet_bytes = (Path(quiet_state["run_directory"]) / f"{prefix}.stdout.md").read_bytes()
        # Closeout output carries the run's own result nonce, which differs by
        # construction; everything else must match byte for byte.
        assert re.sub(rb"[0-9a-f]{32}", b"<nonce>", loud_bytes) == re.sub(
            rb"[0-9a-f]{32}", b"<nonce>", quiet_bytes
        )
        if prefix == "05-closeout":
            continue
        loud_meta = json.loads(
            (Path(loud_state["run_directory"]) / f"{prefix}.meta.json").read_text()
        )
        quiet_meta = json.loads(
            (Path(quiet_state["run_directory"]) / f"{prefix}.meta.json").read_text()
        )
        assert loud_meta["stdout_sha256"] == quiet_meta["stdout_sha256"]
        assert loud_meta["stdout_bytes"] == quiet_meta["stdout_bytes"]


def test_a_broken_display_stream_cannot_fail_the_run(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher, display, _ = watched(
        repository, tmp_path, FakeRunner(), stream=BrokenStream()
    )
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()

    assert state["complete"] is True
    assert state["blocking_reason"] is None


def test_a_full_display_queue_drops_lines_rather_than_blocking(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stalled terminal consumer must cost display lines, never progress.

    With no stage wall clock left, a display write that blocked a provider
    reader thread would fill the provider's pipe and deadlock the phase. The
    consumer here really does block, which is the only way to fill the queue.
    """
    monkeypatch.setattr(display_module, "QUEUE_SIZE", 4)
    released = threading.Event()

    class BlockingStream(RecordingStream):
        def write(self, text: str) -> int:
            released.wait(30)
            return super().write(text)

    display = Display(BlockingStream(), enabled=True)
    started = time.time()
    for index in range(200):
        display.stage_output("stdout", f"line {index}\n".encode("utf-8"))
    elapsed = time.time() - started

    # The caller is a provider reader thread; it must not have waited on the
    # blocked terminal, and the lines it could not enqueue must be accounted for.
    assert elapsed < 5.0, elapsed
    assert display.dropped > 0
    released.set()
    display.close()


def test_an_advisory_stall_notice_reads_as_a_warning_not_a_termination(
    repository: Path, tmp_path: Path
) -> None:
    """The operator must be told the provider is quiet *and* that it still lives.

    A notice that reads like a kill would train the operator to interrupt a
    healthy quiet test -- exactly the false positive this policy withdrew.
    """
    stream = RecordingStream()
    display = Display(stream, enabled=True)
    display.stage_notice(
        {
            "elapsed_seconds": 1801.4,
            "silent_seconds": 900.6,
            "last_activity_kind": "stderr",
        }
    )
    display.close()

    line = next(
        line for line in stream.text.splitlines() if "warn|" in line
    )
    assert "provider quiet for 901s" in line
    assert "elapsed 1801s" in line
    assert "last activity stderr" in line
    assert "still running, not terminated" in line
    # An advisory local observation must never masquerade as provider bytes.
    assert "out|" not in line and "err|" not in line


def test_a_notice_with_no_recognized_activity_yet_still_renders(
    repository: Path, tmp_path: Path
) -> None:
    stream = RecordingStream()
    display = Display(stream, enabled=True)
    display.stage_notice(
        {"elapsed_seconds": 900.0, "silent_seconds": 900.0, "last_activity_kind": None}
    )
    display.close()

    assert "last activity none" in stream.text


def test_the_production_runner_is_wired_to_the_advisory_notice_sink(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The notice path must actually reach the operator in production.

    `test_dispatcher_never_selects_a_liveness_policy` proves injected fakes keep
    the five-argument contract. This proves the other half: when the runner *is*
    the real provider entry point, it receives `on_notice`, and calling it puts
    an advisory warning on the operator's terminal without touching the result.
    """
    captured: list[object] = []
    inner = FakeRunner()

    def production_run(argv, prompt, cwd, max_output, on_output=None, *, on_notice=None):
        captured.append(on_notice)
        return inner(argv, prompt, cwd, max_output, on_output)

    monkeypatch.setattr(provider_module, "run", production_run)
    stream = RecordingStream()
    display = Display(stream, enabled=True)
    dispatcher = make_dispatcher(repository, tmp_path, provider_module.run)
    dispatcher.display = display

    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["complete"] is True
    assert captured and all(sink is not None for sink in captured)
    # Every stage gets the sink, and it is the display's own renderer.
    assert all(sink == display.stage_notice for sink in captured)

    captured[0](
        {
            "elapsed_seconds": 1000.0,
            "silent_seconds": 900.0,
            "last_activity_kind": "protocol",
        }
    )
    display.close()
    assert "still running, not terminated" in stream.text
    # The observer stayed an observer.
    assert state["complete"] is True


def test_a_disabled_display_writes_nothing(repository: Path, tmp_path: Path) -> None:
    stream = RecordingStream()
    display = Display(stream, enabled=False)
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    dispatcher.display = display
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()

    assert stream.text == ""
    assert state["complete"] is True


def test_display_does_not_print_the_inherited_environment(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGENT_PHASE_FAKE_SECRET", "s3cret-value-not-for-display")
    dispatcher, display, stream = watched(repository, tmp_path, FakeRunner())
    dispatcher.dispatch(PHASE_ID, REQUEST)
    display.close()

    assert "s3cret-value-not-for-display" not in stream.text
    assert "AGENT_PHASE_FAKE_SECRET" not in stream.text


def test_provider_escape_sequences_cannot_drive_the_operators_terminal(
    repository: Path, tmp_path: Path
) -> None:
    """Mirroring provider bytes must not hand a model the terminal itself."""
    hostile = b"\x1b]52;c;cGF5bG9hZA==\x07\x1b[2Jclear\x1b]0;retitled\x07\n"
    dispatcher, display, stream = watched(
        repository, tmp_path, FakeRunner(on_stage=None)
    )
    dispatcher.display.stage_started(3, "work", "primary", Endpoint("codex", "p"))
    dispatcher.display.stage_output("stdout", hostile)
    display.close()

    assert "\x1b" not in stream.text
    assert "\x07" not in stream.text
    # The text itself still reaches the operator; only the control bytes go.
    assert "clear" in stream.text and "retitled" in stream.text


# -- CLI contract ------------------------------------------------------------


class StubDispatcher:
    """Records how the CLI wired the display; runs no providers."""

    last: dict = {}

    def __init__(self, root, cwd, display=None, **keywords) -> None:
        # Captured at construction: the CLI closes the display on the way out,
        # which necessarily disables it.
        StubDispatcher.last = {"display": display, "enabled": display.enabled}

    def dispatch(self, phase_id, request, lifecycle="standard", finalization="publish"):
        StubDispatcher.last["phase_id"] = phase_id
        StubDispatcher.last["lifecycle"] = lifecycle
        StubDispatcher.last["finalization"] = finalization
        return {"run_id": f"proj/{phase_id}--stamp", "complete": True}

    def dry_run(self, phase_id, request, lifecycle="standard", finalization="publish"):
        return self.dispatch(phase_id, request, lifecycle, finalization)


def write_request(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "agent-phase-request-v1",
                "phase_type": "implementation_testing",
                "execution_mode": "normal",
                "prompt": "task",
            }
        )
    )
    return path


def test_cli_derives_the_phase_id_from_the_request_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import agent_phase.cli as cli

    monkeypatch.setattr(cli, "Dispatcher", StubDispatcher)
    request = write_request(tmp_path / "MY-PHASE-NAME.request.json")
    assert cli.dispatch_main([str(request)]) == 0

    assert StubDispatcher.last["phase_id"] == "MY-PHASE-NAME"
    assert StubDispatcher.last["lifecycle"] == "standard"
    assert StubDispatcher.last["finalization"] == "publish"


def test_cli_emits_machine_readable_json_on_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import agent_phase.cli as cli

    monkeypatch.setattr(cli, "Dispatcher", StubDispatcher)
    request = write_request(tmp_path / "PHASE.request.json")
    cli.dispatch_main([str(request)])
    captured = capsys.readouterr()

    assert json.loads(captured.out)["complete"] is True


def test_quiet_suppresses_the_display_without_changing_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import agent_phase.cli as cli

    monkeypatch.setattr(cli, "Dispatcher", StubDispatcher)
    request = write_request(tmp_path / "PHASE.request.json")

    cli.dispatch_main([str(request)])
    loud_display = StubDispatcher.last["enabled"]
    loud_output = capsys.readouterr()

    cli.dispatch_main([str(request), "--quiet"])
    quiet_output = capsys.readouterr()

    assert loud_display is True
    assert StubDispatcher.last["enabled"] is False
    assert quiet_output.err == ""
    # Same machine-readable result either way.
    assert json.loads(quiet_output.out) == json.loads(loud_output.out)
    assert json.loads(quiet_output.out)["complete"] is True


def test_cli_refuses_an_unsafe_request_filename_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A refusal is a typed exit 2, not a traceback."""
    import agent_phase.cli as cli

    monkeypatch.setattr(cli, "Dispatcher", StubDispatcher)
    request = write_request(tmp_path / ".request.json")

    with pytest.raises(SystemExit) as exit_info:
        cli.dispatch_main([str(request)])
    captured = capsys.readouterr()

    assert exit_info.value.code == 2
    assert "agent-phase-dispatch:" in captured.err
    assert "safe path component" in captured.err
