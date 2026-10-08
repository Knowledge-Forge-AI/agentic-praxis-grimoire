"""APG166X optional operational observations on the native V1/V2 paths.

Counting fake runners stand in for providers; every dispatch uses a temporary
HOME and APGR home. Observations must never change dispatch, and the summary
must never start a provider or planner.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import pytest

from agent_phase import context_adapter as adapter
from agent_phase import observations
from agent_phase import observations_cli
from agent_phase.config_routing import ConfigError, load_config_file
from test_agent_phase_context import isolated_provider_version_probes  # noqa: F401 (autouse)
from test_agent_phase_disposition_flow import (  # noqa: F401 (fixture)
    PHASE_ID,
    REQUEST,
    DispositionFakeRunner,
    make_dispatcher,
    repository,
)

ROOT = Path(__file__).resolve().parents[3]
PLANNED = {"effective_mode": "static",
           "reasons": ["selective_projection_unqualified", "independent_recovery_unqualified"],
           "selected_snapshots": [{"qualified_id": "apgr:planning-repository-work"}],
           "catalog_fingerprint": "f" * 64, "rule_version": "fixture", "content_identity": "c" * 64}


def _home(tmp_path: Path, config: str | None = None) -> Path:
    home = tmp_path / "apgr-home"
    home.mkdir(parents=True, exist_ok=True)
    if config is not None:
        (home / "config.toml").write_text(config)
    return home


def _v1_dispatch(repository: Path, tmp_path: Path, home: Path, runner=None):
    runner = runner or DispositionFakeRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner, apgr_home=home)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    return state, runner, Path(state["run_directory"])


def _events(run_dir: Path) -> list[dict]:
    return [json.loads(p.read_bytes()) for p in sorted(run_dir.glob("*.dispatch-observation.json"))]


# --------------------------------------------------------------------------- V1


def test_v1_dispatch_emits_one_event_per_invoked_attempt(repository: Path, tmp_path: Path) -> None:
    state, runner, run_dir = _v1_dispatch(repository, tmp_path, _home(tmp_path))
    assert state["outcome"] == "completed"
    events = _events(run_dir)
    assert len(events) == len(runner.calls) == 5
    assert {e["binding_id"] for e in events} == {"plan", "plan_review", "work", "final_review", "closeout"}
    for event in events:
        assert event["schema"] == observations.SCHEMA and event["dispatcher"] == "v1"
        assert event["outcome"]["status"] == "runner_returned" and event["outcome"]["exit_code"] == 0
        assert event["outcome"]["duration_seconds"] is not None
        assert event["context"]["requested_mode"] == "static" and event["context"]["plan"]["sha256"]
        assert event["route"]["provider"] in {"codex", "claude", "antigravity"}
        assert event["route"]["source"] == "effective_stage_routes" and event["route"]["requested_model"]
        assert event["build"]["apgr_version"] and event["provider_reported"] is None
        assert event["self_report"] is None
        serialized = json.dumps(event)
        # Metadata and references only: no argv, prompt text or absolute paths.
        assert "argv" not in event and str(tmp_path) not in serialized
        assert (run_dir / event["artifacts"]["meta"]).is_file()
    assert "observation_failures" not in json.loads((run_dir / "state.json").read_bytes())


def test_v1_opt_out_by_config_and_environment_changes_no_provider_input(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    enabled_state, enabled_runner, enabled_dir = _v1_dispatch(repository, tmp_path / "on", _home(tmp_path / "on"))
    home = _home(tmp_path / "off", "[dispatcher.observations]\nenabled = false\n")
    disabled_state, disabled_runner, disabled_dir = _v1_dispatch(repository, tmp_path / "off", home)
    assert _events(enabled_dir) and _events(disabled_dir) == []
    assert disabled_state["outcome"] == enabled_state["outcome"] == "completed"
    # Provider argv and permissions are unchanged apart from run-specific paths.
    def shape(calls, run_dir):
        return [[a.replace(str(run_dir), "<run>") for a in call["argv"] if "dispatch--" not in a] for call in calls]
    assert shape(disabled_runner.calls, disabled_dir) == shape(enabled_runner.calls, enabled_dir)
    monkeypatch.setenv(observations.ENVIRONMENT_OPT_OUT, "off")
    _, _, env_dir = _v1_dispatch(repository, tmp_path / "env", _home(tmp_path / "env"))
    assert _events(env_dir) == []


def test_v1_writer_failure_is_bounded_and_does_not_change_result(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unwritable(*args, **kwargs):
        raise PermissionError(f"denied {tmp_path}/private/path")
    monkeypatch.setattr(observations, "write_event", unwritable)
    state, runner, run_dir = _v1_dispatch(repository, tmp_path, _home(tmp_path))
    assert state["outcome"] == "completed" and len(runner.calls) == 5
    persisted = json.loads((run_dir / "state.json").read_bytes())
    assert persisted["observation_failures"] == [
        {"prefix": p, "diagnostic": "PermissionError"}
        for p in ("01-plan", "02-plan-review", "03-work", "04-final-review", "05-closeout")]
    assert "private/path" not in json.dumps(persisted)
    assert persisted["shadow"] == state["shadow"]


def test_v1_hook_exception_cannot_escape_before_worker_drain(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(observations, "record_attempt", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bug")))
    state, runner, _ = _v1_dispatch(repository, tmp_path, _home(tmp_path))
    assert state["outcome"] == "completed" and len(runner.calls) == 5



def test_v1_interrupt_in_observation_write_cannot_skip_worker_drain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agent_phase import worker_custody
    order = []
    original = worker_custody.WorkerCustody.drain
    def drain(self):
        order.append("drain")
        return original(self)
    def interrupt(*args, **kwargs):
        order.append("observation")
        raise KeyboardInterrupt
    monkeypatch.setattr(worker_custody.WorkerCustody, "drain", drain)
    monkeypatch.setattr(observations, "record_attempt", interrupt)
    monkeypatch.delenv("APGR_WORKERS_REQUIRED", raising=False)
    _, error = _single_stage(tmp_path, monkeypatch, lambda *a: None)
    assert isinstance(error, KeyboardInterrupt), "interrupts must propagate"
    assert order == ["drain", "observation"]
    assert "APGR_WORKERS_REQUIRED" not in os.environ

def _single_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, runner, *, config: str = "",
                  on_provider_invoke=None):
    from agent_phase.dispatch import Dispatcher
    from agent_phase.envelope import SEGMENT_TASK_PROMPT, Segment, render
    from agent_phase.routing import Endpoint
    from agent_phase.run import RunDirectory
    from test_agent_phase_v2_full_execution import _init_repo
    target = _init_repo(tmp_path / "target")
    home = _home(tmp_path, config + "[integrations.rtk]\nenabled=false\n")
    dispatcher = Dispatcher(ROOT, target, project_root=target, apgr_home=home, run_root=tmp_path / "runs",
                            runner=runner, resolve_scanner=False, codex_executable="/fake/codex",
                            claude_launcher="/fake/claude", antigravity_launcher="/fake/antigravity")
    directory = RunDirectory(tmp_path / "runs", "observations", "single")
    kwargs = {"on_provider_invoke": on_provider_invoke} if on_provider_invoke else {}
    error = None
    try:
        dispatcher._stage(directory, 1, "work_review", "01-work_review", "reviewer",
                          Endpoint("codex", "implementation-testing-review"),
                          render([Segment(SEGMENT_TASK_PROMPT, "exact task")]), None,
                          read_only=True, worker_capability={"allowed": False}, **kwargs)
    except BaseException as caught:  # noqa: BLE001 - classification under test
        error = caught
    return directory.path, error


def test_start_failure_interrupt_and_not_started_are_classified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase import provider
    def start_fails(argv, prompt, cwd, limit, output):
        return provider.run([str(tmp_path / "missing-provider")], prompt, cwd, limit, output)
    run_dir, error = _single_stage(tmp_path / "start", monkeypatch, start_fails)
    assert isinstance(error, provider.ProviderStartFailed)
    assert _events(run_dir)[0]["outcome"]["status"] == "start_failed"

    def interrupted(*args):
        raise KeyboardInterrupt
    run_dir, error = _single_stage(tmp_path / "interrupt", monkeypatch, interrupted)
    assert isinstance(error, KeyboardInterrupt), "interrupts must propagate"
    assert _events(run_dir)[0]["outcome"]["status"] == "interrupted"

    calls = []
    def counting(*args):
        calls.append(args)
        raise AssertionError("must not start")
    def reject():
        raise RuntimeError("boundary rejected")
    run_dir, error = _single_stage(tmp_path / "boundary", monkeypatch, counting, on_provider_invoke=reject)
    assert isinstance(error, RuntimeError) and calls == []
    event = _events(run_dir)[0]
    assert event["outcome"]["status"] == "not_started"
    assert event["outcome"]["dispatch_error_type"] == "RuntimeError"


def test_adaptive_opt_in_is_shadow_planning_with_static_transport(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase.provider import Result
    seen = []
    def runner(argv, prompt, cwd, limit, output):
        seen.append((list(argv), prompt))
        return Result(0, b"ok", b"", False, time.time(), time.time())
    monkeypatch.setattr(adapter, "native_plan", lambda request, capture: dict(PLANNED))
    run_dir, error = _single_stage(tmp_path / "adaptive", monkeypatch, runner,
                                   config='[dispatcher.context]\nmode="adaptive"\n')
    assert error is None and len(seen) == 1
    plan = json.loads((run_dir / "01-work_review.context-plan.json").read_bytes())
    assert plan["transport"]["argv"] == seen[0][0] and plan["effective_mode"] == "static"
    assert b"exact task" in seen[0][1]
    event = _events(run_dir)[0]
    assert event["context"]["requested_mode"] == "adaptive" and event["context"]["planned"] is True
    summary = observations.summarize([observations.collect_run(run_dir)])
    assert summary["context"]["requested_to_effective"] == {"adaptive -> static": 1}
    # APG166Z-CONTEXT1: a Codex route is outside the ordinary Claude pilot; the
    # headline reason names the route while the planner's own reasons stay in
    # the retained prospective plan. Transport remains static (shadow plan).
    assert summary["context"]["reasons"] == {"route_unsupported:provider_not_in_pilot": 1}
    assert plan["prospective_plan"]["reasons"] == ["selective_projection_unqualified", "independent_recovery_unqualified"]
    assert summary["context"]["delivery"] == {"static_with_shadow_plan": 1}
    assert summary["skills"]["planned"] == {"apgr:planning-repository-work": 1}
    assert summary["skills"]["delivered"] == {}
    assert summary["context"]["planner_facts"] == {"work_class=review_verification": 1}

    monkeypatch.setattr(adapter, "native_plan", lambda *a: (_ for _ in ()).throw(ImportError("absent")))
    run_dir, error = _single_stage(tmp_path / "failed", monkeypatch, runner,
                                   config='[dispatcher.context]\nmode="adaptive"\n')
    assert error is None and _events(run_dir)[0]["context"]["reason"] == "optional_plan_failed"


def test_adaptive_opt_in_with_native_planner_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase.provider import Result
    from test_agent_phase_context import built_context_binary
    monkeypatch.setenv("APGR_GO_BINARY", str(built_context_binary(ROOT)))
    seen = []
    def runner(argv, prompt, cwd, limit, output):
        seen.append(prompt)
        return Result(0, b"ok", b"", False, time.time(), time.time())
    run_dir, error = _single_stage(tmp_path, monkeypatch, runner, config='[dispatcher.context]\nmode="adaptive"\n')
    assert error is None and len(seen) == 1
    summary = observations.summarize([observations.collect_run(run_dir)])
    assert summary["context"]["requested_to_effective"] == {"adaptive -> static": 1}
    assert summary["context"]["reasons"].get("route_unsupported:provider_not_in_pilot") == 1
    assert summary["skills"]["planned"] and summary["skills"]["delivered"] == {}
    assert _events(run_dir)[0]["context"]["planned"] is True


# --------------------------------------------------------------------------- V2


def _v2(tmp_path: Path, config: str | None = None):
    from agent_phase.request import parse_request_v2
    from agent_phase.v2_dispatch import dispatch_v2
    from test_agent_phase_v2_full_execution import _init_repo, _make_closeout_output, _make_v2_request_bytes, _repo_root
    repo = _init_repo(tmp_path / "repo")
    home = _home(tmp_path, config)
    calls = []
    def runner(*, run_id, binding, route, run_dir, prompt_bytes, argv, nonce):
        calls.append((binding.binding_id, list(argv)))
        if binding.binding_id == "binding_closeout":
            return _make_closeout_output(nonce)
        return None
    raw = _make_v2_request_bytes()
    result = dispatch_v2(_repo_root(), repo, parse_request_v2(raw), raw, execution_mode="gemini_sub",
                         apgr_home=home, outbox_root=tmp_path / "outbox", runner=runner)
    runs = [p for p in (home / "state" / "runs").iterdir() if p.is_dir()]
    assert len(runs) == 1
    return result, calls, runs[0], home


def test_v2_dispatch_emits_events_and_summary(tmp_path: Path) -> None:
    result, calls, run_dir, home = _v2(tmp_path)
    assert result["status"] == "completed"
    events = _events(run_dir)
    assert len(events) == len(calls) == 5
    assert all(e["dispatcher"] == "v2" and e["outcome"]["status"] == "runner_returned" for e in events)
    assert all(e["artifact_prefix"] == e["attempt_id"] and e["attempt_number"] == 1 for e in events)
    assert all(e["predecessor_attempt_id"] is None for e in events)
    assert "dispatcher.sqlite3" not in json.dumps(events)
    # The pre-existing V2 review-drift evidence file keeps its own name and bytes.
    drift = sorted(run_dir.glob("*-binding_work_review-1.observation.json"))
    assert drift and json.loads(drift[0].read_bytes()).get("schema") != observations.SCHEMA
    summary = observations.summarize([observations.collect_run(run_dir)])
    assert summary["selection"]["attempts"] == 5 and summary["selection"]["attempts_with_event"] == 5
    assert summary["selection"]["dispatchers"] == {"v2": 1}
    # V2 route metadata carries no model/effort at this seam; reported as unavailable.
    assert any("model=unavailable" in key for key in summary["routes"])


def test_v2_opt_out_and_writer_failure_do_not_change_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                              capfd: pytest.CaptureFixture[str]) -> None:
    disabled, disabled_calls, run_dir, _ = _v2(tmp_path / "off", "[dispatcher.observations]\nenabled = false\n")
    assert disabled["status"] == "completed" and _events(run_dir) == []
    monkeypatch.setattr(observations, "write_event", lambda *a, **k: (_ for _ in ()).throw(OSError("full")))
    failed, failed_calls, run_dir, _ = _v2(tmp_path / "fail")
    assert failed["status"] == "completed" and _events(run_dir) == []
    assert len(failed_calls) == len(disabled_calls) == 5
    assert "optional observation not recorded (OSError)" in capfd.readouterr().err


# ------------------------------------------------------------- summary/index


def _fixture_runs(repository: Path, tmp_path: Path) -> tuple[Path, Path]:
    _, _, run_dir = _v1_dispatch(repository, tmp_path, _home(tmp_path))
    jobs = run_dir / "workers" / "parent-fixture" / "jobs" / "job-1"
    jobs.mkdir(parents=True)
    (jobs / "job-1.result.json").write_text(json.dumps({
        "schema": "agent-worker-result-v1", "parent_id": "parent-fixture", "job_id": "job-1",
        "status": "failed", "worker_kind": "luna", "task_outcome": "unknown",
        "requested_model": "fixture-model", "effective_model": None,
        "model_evidence": {"effective": {"source": "provider_terminal_metadata"}},
        "quota": {"classification": "explicit_quota_exhaustion", "exhausted": True}}))
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    for path in run_dir.iterdir():
        if path.is_file() and not path.name.endswith(".dispatch-observation.json"):
            (legacy / path.name).write_bytes(path.read_bytes())
    (legacy / "03-work.dispatch-observation.json").write_text("{not json")
    return run_dir, legacy


def test_summary_reports_missing_data_and_isolates_malformed_events(repository: Path, tmp_path: Path) -> None:
    run_dir, legacy = _fixture_runs(repository, tmp_path)
    runs = [observations.collect_run(run_dir), observations.collect_run(legacy)]
    summary = observations.summarize(runs)
    assert summary["selection"]["attempts"] == 10 and summary["selection"]["attempts_with_event"] == 5
    assert any("5/10 attempts have no observation event" in w for w in summary["warnings"])
    assert any("03-work observation: JSONDecodeError" in w for w in summary["warnings"])
    assert summary["outcomes"]["status"] == {"runner_returned": 10}
    assert summary["workers"]["by_kind_status"] == {"luna:failed": 1}
    assert summary["workers"]["model_requested_vs_effective"] == {
        "fixture-model -> unavailable (source=provider_terminal_metadata)": 1}
    assert summary["workers"]["quota"] == {"explicit_quota_exhaustion": 1}
    boundary = "context-plan controlled_total: canonical argv JSON plus runner stdin"
    assert list(summary["bytes"]["initial_by_boundary"]) == [boundary]
    assert summary["bytes"]["initial_by_boundary"][boundary]["n"] == 10
    assert summary["acquisition"]["events"] == 0 and summary["bytes"]["late"]["sum"] is None
    text = observations.render_text(summary)
    assert "Controlled late bytes (acquisition deliveries): n=0, sum=unavailable" in text
    assert "savings" not in text.replace("no savings", "")


def test_cli_summarize_feedback_and_index_are_provider_free_and_idempotent(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir, legacy = _fixture_runs(repository, tmp_path)
    from agent_phase import provider
    monkeypatch.setattr(provider, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("provider")))
    monkeypatch.setattr(adapter, "native_plan", lambda *a: (_ for _ in ()).throw(AssertionError("planner")))
    home = tmp_path / "analytics-home"
    run_id = json.loads((run_dir / "state.json").read_bytes())["run_id"]

    assert observations_cli.main(["feedback", "--apgr-home", str(home), "--run-id", run_id,
                                  "--label", "helpful", "--source", "agent", "--skill", "apgr:x"]) == 0
    assert observations_cli.main(["feedback", "--apgr-home", str(home), "--run-id", run_id,
                                  "--label", "missing", "--source", "operator"]) == 0
    with pytest.raises(SystemExit):
        observations_cli.main(["feedback", "--apgr-home", str(home), "--run-id", run_id,
                               "--label", "great", "--source", "operator"])
    feedback_file = home / "state/observations/feedback.jsonl"
    assert oct(feedback_file.stat().st_mode & 0o777) == "0o600"
    assert not list(run_dir.glob("*feedback*"))
    capsys.readouterr()

    assert observations_cli.main(["summarize", "--apgr-home", str(home), "--json", str(run_dir)]) == 0
    direct = json.loads(capsys.readouterr().out)
    assert direct["feedback"]["by_label_source"] == {"helpful (agent)": 1, "missing (operator)": 1}

    index = home / "state/observations/index.sqlite3"
    args = ["index", "--apgr-home", str(home), str(run_dir), str(legacy)]
    assert observations_cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["inserted"] == 2  # same run id, distinct directories
    assert observations_cli.main(args) == 0
    assert json.loads(capsys.readouterr().out)["unchanged"] == 2
    with sqlite3.connect(index) as connection:
        assert connection.execute("SELECT count(*) FROM runs").fetchone()[0] == 2
    assert observations_cli.main(["summarize", "--apgr-home", str(home), "--json", "--from-index"]) == 0
    from_index = json.loads(capsys.readouterr().out)
    assert from_index["selection"]["runs"] == 2 and from_index["selection"]["attempts"] == 10
    # Feedback rows are joined by run id; the duplicated run id does not double them.
    assert from_index["feedback"] == direct["feedback"]



def test_structurally_malformed_records_are_bounded_warnings(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    run_dir, _ = _fixture_runs(repository, tmp_path)
    event_path = run_dir / "03-work.dispatch-observation.json"
    event = json.loads(event_path.read_bytes())
    event.update(route=["not", "a", "mapping"], outcome="broken", context=7, build={"controller_commit": 42},
                 binding_id={"nested": True}, attempt_number="1")
    event_path.write_text(json.dumps(event))
    (run_dir / "workers" / "parent-fixture" / "jobs" / "job-1" / "job-1.result.json").write_text("[1, 2]")
    row = observations.collect_run(run_dir)
    work = next(a for a in row["attempts"] if a["prefix"] == "03-work")
    assert work["build_commit"] is None or isinstance(work["build_commit"], str)
    # Wrong-typed event fields are dropped; the plan's typed values remain the fallback.
    assert work["attempt_number"] == 1 and work["binding_id"] == "work"
    assert isinstance(work["provider"], str)
    assert row["workers"][0]["status"] == observations.UNAVAILABLE
    assert any("result is not an object" in w for w in row["warnings"])
    observations.render_text(observations.summarize([row]))
    home = tmp_path / "analytics-home"
    assert observations_cli.main(["summarize", "--apgr-home", str(home), "--no-feedback", str(run_dir)]) == 0

    capsys.readouterr()
    def explode(path):
        raise TypeError("unexpected shape")
    monkeypatch.setattr(observations, "collect_run", explode)
    assert observations_cli.main(["summarize", "--apgr-home", str(home), "--json", str(run_dir)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["selection"]["runs"] == 0
    assert any("malformed run records skipped (TypeError)" in w for w in summary["warnings"])


def test_retry_links_predecessor_and_index_selection_is_explicit(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    from agent_phase.dispatch import Dispatcher
    from agent_phase.run import RunDirectory
    from agent_phase.routing import Endpoint
    captured = {}
    def record(*args, **kwargs):
        captured.update(kwargs)
        return {"status": "recorded"}
    dispatcher = Dispatcher.__new__(Dispatcher)
    dispatcher._stage_accounting_state = {}
    dispatcher._review_attempt_context = {"index": 4}
    monkeypatch.setattr(observations, "record_attempt", record)
    directory = RunDirectory(tmp_path / "runs", "observations", "retry")
    dispatcher._record_observation(directory, "07-final-review", "final_review", 7,
                                   Endpoint("codex", "implementation-testing-review"),
                                   "auxiliary_review_retry", None, {}, True, None)
    assert captured["attempt_number"] == 2
    assert captured["predecessor_attempt_id"] == f"att-{directory.run_id}-final_review-4"

    run_dir, legacy = _fixture_runs(repository, tmp_path / "idx")
    home = tmp_path / "analytics-home"
    assert observations_cli.main(["index", "--apgr-home", str(home), str(run_dir)]) == 0
    capsys.readouterr()
    run_id = json.loads((run_dir / "state.json").read_bytes())["run_id"]
    assert observations_cli.main(["summarize", "--apgr-home", str(home), "--json", "--from-index",
                                  "--run-id", "absent-run"]) == 0
    assert json.loads(capsys.readouterr().out)["selection"]["runs"] == 0
    assert observations_cli.main(["summarize", "--apgr-home", str(home), "--json", "--from-index",
                                  "--run-id", run_id]) == 0
    assert json.loads(capsys.readouterr().out)["selection"]["runs"] == 1
    for bad in (["--from-index", str(run_dir)], ["--run-id", run_id, str(run_dir)]):
        with pytest.raises(SystemExit) as exited:
            observations_cli.main(["summarize", "--apgr-home", str(home), *bad])
        assert exited.value.code == 2

def test_index_lock_corruption_and_incompatibility_are_isolated(repository: Path, tmp_path: Path,
                                                                capsys: pytest.CaptureFixture[str]) -> None:
    run_dir, _ = _fixture_runs(repository, tmp_path)
    home = tmp_path / "analytics-home"
    index = home / "state/observations/index.sqlite3"
    assert observations_cli.main(["index", "--apgr-home", str(home), str(run_dir)]) == 0
    holder = sqlite3.connect(index)
    holder.execute("BEGIN EXCLUSIVE")
    started = time.monotonic()
    try:
        (run_dir / "state.json").write_bytes((run_dir / "state.json").read_bytes() + b" ")
        assert observations_cli.main(["index", "--apgr-home", str(home), str(run_dir)]) == 1
    finally:
        holder.rollback()
        holder.close()
    assert time.monotonic() - started < 10
    assert "observation index unavailable" in capsys.readouterr().err
    with sqlite3.connect(index) as connection:
        connection.execute("PRAGMA user_version = 99")
    assert observations_cli.main(["index", "--apgr-home", str(home), str(run_dir)]) == 1
    assert "--rebuild" in capsys.readouterr().err
    assert observations_cli.main(["index", "--apgr-home", str(home), "--rebuild", str(run_dir)]) == 0
    index.write_bytes(b"not a database" * 100)
    assert observations_cli.main(["index", "--apgr-home", str(home), str(run_dir)]) == 1
    # A broken optional index never affects the file-based summary.
    capsys.readouterr()
    assert observations_cli.main(["summarize", "--apgr-home", str(home), str(run_dir)]) == 0


def test_outbox_selection_is_bounded_to_run_leaves(repository: Path, tmp_path: Path) -> None:
    _, _, run_dir = _v1_dispatch(repository, tmp_path, _home(tmp_path))
    outbox = tmp_path / "runs"
    project = run_dir.parent.parent.name
    (run_dir.parent / "not-a-run").mkdir()
    selected = observations.select_runs(outbox_root=outbox, project=project, latest=5)
    assert selected == [run_dir]
    with pytest.raises(observations.ObservationError):
        observations.select_runs(outbox_root=outbox, project=project, latest=0)
    with pytest.raises(observations.ObservationError):
        observations.select_runs(outbox_root=outbox, latest=5)


def test_apgr_cli_routes_dispatcher_observations(repository: Path, tmp_path: Path) -> None:
    _, _, run_dir = _v1_dispatch(repository, tmp_path, _home(tmp_path))
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HOME": str(tmp_path / "home")}
    completed = subprocess.run(
        [sys.executable, "-m", "agentic_praxis_grimoire", "--apgr-home", str(tmp_path / "analytics"),
         "dispatcher", "observations", "summarize", "--json", str(run_dir)],
        cwd=ROOT, env=environment, capture_output=True, timeout=60)
    assert completed.returncode == 0, completed.stderr.decode()
    assert json.loads(completed.stdout)["selection"]["attempts"] == 5


@pytest.mark.parametrize("value", ["enabled = 1", 'enabled = "false"', "other = true"])
def test_observation_config_is_closed_in_both_owners(tmp_path: Path, value: str) -> None:
    from agentic_praxis_grimoire.config import ConfigError as PublicError, load_config
    path = tmp_path / "config.toml"
    path.write_text("[dispatcher.observations]\n" + value + "\n")
    with pytest.raises(ConfigError):
        load_config_file(path)
    with pytest.raises(PublicError):
        load_config(path)
    path.write_text("[dispatcher.observations]\nenabled = false\n")
    load_config_file(path)
    assert load_config(path)["dispatcher"]["observations"] == {"enabled": False}
