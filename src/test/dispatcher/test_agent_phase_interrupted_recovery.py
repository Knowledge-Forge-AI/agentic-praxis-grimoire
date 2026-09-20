"""First-class recovery of a run whose dispatcher vanished before its result."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent_phase import cli as cli_module
from agent_phase import interrupted_recovery
from agent_phase.dispatch import DispatchError
from agent_phase.resume_validation import ResumeError, phase_id_for_resume
from interrupted_run_fixtures import (
    PHASE_ID,
    REQUEST,
    DispositionFakeRunner,
    add_worker_custody,
    interrupted_source,
    make_dispatcher,
    read_state,
    record_dead_controller,
    tree_bytes,
    write_state,
)
from test_agent_phase_disposition_flow import repository as _repository

repository = _repository


def modify(cwd: Path) -> None:
    (cwd / "README.md").write_text("# Interrupted phase edit\n")
    (cwd / "phase-new.txt").write_text("interrupted phase bytes\n")


def test_missing_result_with_closed_prefix_recovers_without_semantic_claims(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    before = read_state(source)
    assert before["stages_completed"] == ["plan", "plan_review"]
    assert before["stages_invoked"] == ["plan", "plan_review", "work"]

    record = interrupted_recovery.ensure(source)

    state = read_state(source)
    result = json.loads((source / "result.json").read_text())
    assert record == state["interrupted_recovery"]
    assert record["interrupted_stage"] == "work"
    assert record["semantic_completion_claimed"] is False
    for view in (state, result):
        assert view["complete"] is False
        assert view["outcome"] is None and view["semantic_outcome"] is None
        assert view["finalization_outcome"] == "not_attempted"
        assert view["blocking_reason"]["code"] == "RUN_INTERRUPTED_BEFORE_RESULT"
    assert state["stages_completed"] == before["stages_completed"]
    assert (source / "interrupted-recovery.source-state.json").read_bytes() == json.dumps(
        before, sort_keys=True, indent=2, ensure_ascii=False).encode() + b"\n"
    receipt = json.loads((source / "interrupted-recovery.json").read_text())
    assert receipt["interrupted_stage_artifacts"]
    assert all(item["name"].startswith("03-work.") for item in receipt["interrupted_stage_artifacts"])
    assert not (source / "03-work.meta.json").exists()


def test_recovery_is_idempotent_and_rolls_forward_from_each_write_point(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    pristine = tree_bytes(source)
    interrupted_recovery.ensure(source)
    recovered = tree_bytes(source)
    assert interrupted_recovery.ensure(source) is None
    assert tree_bytes(source) == recovered

    names = ("interrupted-recovery.json", "interrupted-recovery.source-state.json",
             "result.json", "result.md", "state.json")
    for written in range(1, len(names)):
        for name in names:
            path = source / name
            if name == "state.json":
                path.write_bytes(pristine[name])
            elif names.index(name) >= written and path.exists():
                path.unlink()
        interrupted_recovery.ensure(source)
        assert tree_bytes(source) == recovered, written


def test_receipt_for_other_bytes_refuses_roll_forward(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    interrupted_recovery.ensure(source)
    pristine = (source / "interrupted-recovery.source-state.json").read_bytes()
    for name in ("result.json", "result.md", "interrupted-recovery.source-state.json"):
        (source / name).unlink()
    state = json.loads(pristine)
    state["phase_type"] = "architecture_docs"
    write_state(source, state)

    with pytest.raises(ResumeError) as caught:
        interrupted_recovery.ensure(source)
    assert caught.value.code == "RESUME_RECOVERY_REFUSED"


@pytest.mark.parametrize(
    "damage",
    ["missing_meta", "stdout_changed", "invoked_gap", "archive", "blocking", "complete",
     "failure_candidate", "extra_invoked"],
)
def test_missing_result_with_inconsistent_prefix_refuses_and_preserves_source(
    repository, tmp_path, damage
):
    source = interrupted_source(repository, tmp_path, modify)
    state = read_state(source)
    if damage == "missing_meta":
        (source / "02-plan-review.meta.json").unlink()
    elif damage == "stdout_changed":
        (source / "01-plan.stdout.md").write_text("rewritten plan\n")
    elif damage == "invoked_gap":
        state["stages_invoked"] = ["plan", "plan_review", "final_review"]
    elif damage == "archive":
        (source.parent / f"{source.name}.zip").write_bytes(b"archive")
    elif damage == "blocking":
        state["blocking_reason"] = {"code": "PROVIDER_TIMEOUT", "detail": "recorded"}
    elif damage == "complete":
        state["complete"] = True
    elif damage == "failure_candidate":
        state["failure_candidate"] = {"stage": "work", "tree": "f" * 40}
    else:
        state["stages_invoked"] = ["plan", "plan_review", "work", "final_review"]
    if damage in ("invoked_gap", "blocking", "complete", "failure_candidate", "extra_invoked"):
        write_state(source, state)
    before = tree_bytes(source)

    with pytest.raises(ResumeError) as caught:
        interrupted_recovery.ensure(source)
    with pytest.raises(DispatchError):
        make_dispatcher(repository, tmp_path / "refused", DispositionFakeRunner()).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")

    assert caught.value.code in ("RESUME_RECOVERY_REFUSED", "RESUME_ARTIFACT_MISMATCH")
    assert tree_bytes(source) == before
    assert not list((tmp_path / "refused").rglob("state.json"))


def test_dry_run_qualifies_without_writing(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    ledger = add_worker_custody(source, {"job-1": {"status": "completed", "cleanup_proven": True}})
    before = tree_bytes(source)

    preview = make_dispatcher(repository, tmp_path / "dry", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, dry_run=True, finalization_policy="checkpoint")

    assert preview["outcome"] == "dry_run"
    assert preview["interrupted_recovery"]["status"] == "qualified_not_materialized"
    assert preview["interrupted_recovery"]["interrupted_stage"] == "work"
    assert tree_bytes(source) == before
    assert json.loads(ledger.read_text())["status"] == "active"
    assert not (tmp_path / "dry").exists()


@pytest.fixture
def no_signals(monkeypatch):
    def guarded(real):
        def probe_only(target, signal_number):
            if signal_number != 0:
                raise AssertionError("recovery must never signal a worker")
            return real(target, 0)
        return probe_only

    monkeypatch.setattr(os, "kill", guarded(os.kill))
    monkeypatch.setattr(os, "killpg", guarded(os.killpg))


def test_stale_parent_with_settled_children_is_reconciled_idempotently(repository, tmp_path, no_signals):
    source = interrupted_source(repository, tmp_path, modify)
    ledger = add_worker_custody(source, {
        "job-1": {"status": "completed", "cleanup_proven": True},
        "job-2": {"status": "failed", "cleanup_proven": True},
    })

    interrupted_recovery.ensure(source)
    closed = ledger.read_bytes()
    interrupted_recovery.ensure(source)

    data = json.loads(closed)
    receipt = json.loads((source / "interrupted-recovery.json").read_text())
    assert data["status"] == "closed"
    assert data["settled_reconciliation"]["prior_status"] == "active"
    assert receipt["worker_custody"]["parents"] == [{
        "parent_id": data["parent_id"], "status": "closed",
        "settled_reconciliation": data["settled_reconciliation"],
        "gemini_jobs": {"job-1": "completed", "job-2": "failed"},
    }]
    assert ledger.read_bytes() == closed
    state = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, dry_run=True, finalization_policy="checkpoint")
    assert state["worker_cleanup_reconciled"]["cleanup_proven"] is True


@pytest.mark.parametrize(
    ("jobs", "natives"),
    [
        ({"job-1": {"status": "running", "cleanup_proven": False}}, {}),
        ({"job-1": {"status": "orphaned", "cleanup_proven": False}}, {}),
        ({"job-1": {"status": "completed", "cleanup_proven": False}}, {}),
        ({}, {"agent-1": {"status": "active"}}),
    ],
    ids=["running", "orphaned", "unproven", "native-active"],
)
def test_active_or_uncertain_child_refuses_without_touching_custody(
    repository, tmp_path, no_signals, jobs, natives
):
    source = interrupted_source(repository, tmp_path, modify)
    add_worker_custody(source, jobs, natives=natives)
    before = tree_bytes(source)

    with pytest.raises(ResumeError) as caught:
        interrupted_recovery.ensure(source)
    with pytest.raises(DispatchError) as dispatched:
        make_dispatcher(repository, tmp_path / "refused", DispositionFakeRunner()).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")

    assert caught.value.code == dispatched.value.code == "WORKER_CLEANUP_FAILED"
    assert tree_bytes(source) == before


def test_interrupted_source_identity_uses_semantic_request(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    retained = json.loads((source / "request.json").read_text())
    ascii_copy = tmp_path / "ascii-request.json"
    ascii_copy.write_text(json.dumps(retained, indent=1))
    assert ascii_copy.read_bytes() != (source / "request.json").read_bytes()

    assert phase_id_for_resume(source, ascii_copy) == PHASE_ID
    assert not (source / "result.json").exists()
    retained["prompt"] += " Also something else."
    ascii_copy.write_text(json.dumps(retained))
    with pytest.raises(ResumeError) as caught:
        phase_id_for_resume(source, ascii_copy)
    assert caught.value.code == "RESUME_REQUEST_MISMATCH"


def test_resume_of_interrupted_resumed_attempt_recovers(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    from interrupted_run_fixtures import only_run
    import shutil

    snapshot = tmp_path / "second-kill-point"

    def lose(cwd, _prompt):
        (cwd / "second.txt").write_text("second interrupted bytes\n")
        shutil.copytree(only_run(tmp_path / "second" / "runs"), snapshot)
        raise RuntimeError("lost again")

    with pytest.raises((DispatchError, RuntimeError)):
        make_dispatcher(repository, tmp_path / "second", DispositionFakeRunner(hooks={0: lose})).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    second = only_run(tmp_path / "second" / "runs")
    for sibling in second.parent.iterdir():
        if sibling != second:
            sibling.unlink()
    shutil.rmtree(second)
    shutil.copytree(snapshot, second)
    record_dead_controller(second)

    record = interrupted_recovery.ensure(second)
    assert read_state(second)["resumed"] is True
    assert record["interrupted_stage"] == "work"
    assert record["completed_stages"] == ["plan", "plan_review"]


def test_cli_resume_recovers_byte_different_request(repository, tmp_path, monkeypatch, capsys):
    source = interrupted_source(repository, tmp_path, modify)
    supplied = tmp_path / "launch-copy.json"
    supplied.write_text(json.dumps(json.loads((source / "request.json").read_text())))
    runner = DispositionFakeRunner()

    def factory(*_args, **kwargs):
        return make_dispatcher(repository, tmp_path / "cli", runner,
                               review_mutation_policy=kwargs.get("review_mutation_policy", "block"))

    monkeypatch.setattr(cli_module, "Dispatcher", factory)
    monkeypatch.chdir(repository)
    assert cli_module.dispatch_main([
        str(supplied), "--resume", str(source), "--finalization", "checkpoint", "--quiet",
    ]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["resume"]["source_interrupted_recovery"]["interrupted_stage"] == "work"
    assert state["resume"]["request_identity"]["comparison"] == "semantic_v1"
    assert len(runner.calls) == 3
    assert read_state(source)["interrupted_recovery"]["semantic_completion_claimed"] is False


@pytest.mark.parametrize("dry_run", [True, False])
def test_mismatched_request_refuses_before_any_recovery_write(repository, tmp_path, dry_run):
    from agent_phase.request import PhaseRequest

    source = interrupted_source(repository, tmp_path, modify)
    ledger = add_worker_custody(source, {"job-1": {"status": "completed", "cleanup_proven": True}})
    before = tree_bytes(source)
    different = PhaseRequest(REQUEST.phase_type, REQUEST.execution_mode, REQUEST.prompt + " And more.")

    for phase_id, request in ((PHASE_ID, different), ("OTHER-PHASE", REQUEST)):
        with pytest.raises(DispatchError) as caught:
            make_dispatcher(repository, tmp_path / "mismatch", DispositionFakeRunner()).resume(
                phase_id, request, source, dry_run=dry_run, finalization_policy="checkpoint")
        assert caught.value.code == "RESUME_REQUEST_MISMATCH"

    assert tree_bytes(source) == before
    assert json.loads(ledger.read_text())["status"] == "active"


def _live_controller() -> dict:
    from controller_generation_process import process_identity

    return {"pid": os.getpid(), "process_identity": process_identity(os.getpid())}


@pytest.mark.parametrize("generation", ["live", "absent", "identity-missing"])
def test_live_or_unproven_source_controller_refuses_before_any_write(
    repository, tmp_path, no_signals, generation
):
    source = interrupted_source(repository, tmp_path, modify)
    ledger = add_worker_custody(source, {"job-1": {"status": "completed", "cleanup_proven": True}})
    state = read_state(source)
    if generation == "live":
        state["controller_generation"] = _live_controller()
    elif generation == "absent":
        state.pop("controller_generation")
    else:
        state["controller_generation"].pop("process_identity")
    write_state(source, state)
    before = tree_bytes(source)

    with pytest.raises(ResumeError) as caught:
        interrupted_recovery.ensure(source)
    assert caught.value.code == "RESUME_RECOVERY_REFUSED"
    for dry_run in (True, False):
        with pytest.raises(DispatchError) as dispatched:
            make_dispatcher(repository, tmp_path / f"live-{dry_run}", DispositionFakeRunner()).resume(
                PHASE_ID, REQUEST, source, dry_run=dry_run, finalization_policy="checkpoint")
        assert dispatched.value.code == "RESUME_RECOVERY_REFUSED"
    assert tree_bytes(source) == before
    assert json.loads(ledger.read_text())["status"] == "active"


def test_live_interrupted_stage_provider_group_refuses(repository, tmp_path, no_signals):
    import subprocess
    import sys

    source = interrupted_source(repository, tmp_path, modify)
    launch = source / "03-work.context-launcher-deliveries.json"
    provider = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"],
                                stdin=subprocess.PIPE, start_new_session=True)
    try:
        launch.write_text(json.dumps({"launch_facts": {
            "pid": provider.pid, "process_group": provider.pid}}))
        before = tree_bytes(source)
        with pytest.raises(ResumeError) as caught:
            interrupted_recovery.ensure(source)
        assert caught.value.code == "RESUME_RECOVERY_REFUSED"
        assert "provider process group" in caught.value.detail
        assert tree_bytes(source) == before
    finally:
        provider.communicate(b"")

    assert interrupted_recovery.ensure(source)["interrupted_stage"] == "work"


def test_foreign_checkout_refuses_before_any_recovery_write(repository, tmp_path):
    import subprocess

    source = interrupted_source(repository, tmp_path, modify)
    foreign = tmp_path / "foreign"
    subprocess.run(["git", "clone", "-q", str(repository), str(foreign)], check=True)
    before = tree_bytes(source)

    for dry_run in (True, False):
        with pytest.raises(DispatchError) as caught:
            make_dispatcher(foreign, tmp_path / f"foreign-{dry_run}", DispositionFakeRunner()).resume(
                PHASE_ID, REQUEST, source, dry_run=dry_run, finalization_policy="checkpoint")
        assert caught.value.code == "RESUME_PROJECT_MISMATCH"
    assert tree_bytes(source) == before
