"""Retained entry adoption through interrupted dispatch and maintained resume."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from agent_phase import adoption, cli as cli_module, entry_adoption, gitstate
from agent_phase.dispatch import DispatchError
from interrupted_run_fixtures import (
    PHASE_ID, REQUEST, DispositionFakeRunner, add_worker_custody,
    interrupted_source, make_dispatcher, only_run, read_state, record_dead_controller, write_state,
)
from test_agent_phase_disposition_flow import git, repository as _repository

repository = _repository


def adopted_source(repository: Path, tmp_path: Path, *, mutate=lambda _cwd: None,
                   at=2, before=None, operator_dirt=False):
    (repository / "README.md").write_text("# Adopted entry\n")
    (repository / "adopted.txt").write_text("adopted object\n")
    if operator_dirt:
        (repository / "operator.txt").write_text("unadopted operator bytes\n")
    request = tmp_path / "entry-request.json"
    request.write_text(json.dumps(REQUEST.as_dict()))
    record = entry_adoption.create(request, repository, ["README.md", "adopted.txt"],
                                  reason="Resume regression", phase_id=PHASE_ID)
    receipt = tmp_path / "entry-receipt.json"
    receipt.write_text(json.dumps(record))
    source = interrupted_source(repository, tmp_path, mutate, at=at, before=before,
                                entry_adoption=receipt)
    return source, record


def test_interrupted_entry_adoption_reproves_original_manifest(repository, tmp_path):
    source, record = adopted_source(repository, tmp_path)
    before = read_state(source)
    assert before["entry"]["tree"] == record["candidate_tree"]
    assert record["base_tree"] != before["entry"]["tree"]
    assert before["stages_completed"] == ["plan", "plan_review"]
    assert before["stages_invoked"] == ["plan", "plan_review", "work"]
    ledger = add_worker_custody(source, {"job-1": {"status": "completed", "cleanup_proven": True}})
    runner = DispositionFakeRunner()
    try:
        result = make_dispatcher(repository, tmp_path / "resumed", runner).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    finally:
        assert (source / "interrupted-recovery.json").is_file()
        assert read_state(source)["interrupted_recovery"]["interrupted_stage"] == "work"
        assert json.loads(ledger.read_text())["status"] == "closed"
    assert result["complete"] is True
    assert result["entry_adoption"] == record
    assert result["candidate_manifest"] == record["candidate_manifest"]
    assert set(record["adopted_paths"]) <= set(result["phase_owned_paths"])


def test_entry_with_unadopted_dirt_finalizes_without_owning_it(repository, tmp_path):
    source, record = adopted_source(repository, tmp_path, operator_dirt=True)
    assert read_state(source)["entry"]["tree"] != record["candidate_tree"]
    result = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert result["complete"]
    assert read_state(Path(result["run_directory"]))["entry_dirt_identities"] == read_state(source)["entry_dirt_identities"]
    assert result["candidate_manifest"] == record["candidate_manifest"]
    assert result["resume_boundary"]["unrelated_paths"] == ["operator.txt"]
    assert result["resume_boundary"]["skew"] is True
    assert result.get("review_binding_invalidations", {}) == {}
    assert "operator.txt" not in result["phase_owned_paths"]
    assert (repository / "operator.txt").read_text() == "unadopted operator bytes\n"


def test_entry_plus_later_delta_preserves_base_and_updated_objects(repository, tmp_path):
    def work(cwd, _prompt):
        (cwd / "README.md").write_text("# Later adopted edit\n")
        (cwd / "later.txt").write_text("later work\n")
    source, record = adopted_source(repository, tmp_path, at=3, before={2: work})
    result = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    manifest = result["candidate_manifest"]
    assert result["complete"]
    assert manifest["entry_tree"] == record["base_tree"]
    assert set(manifest["paths"]) == set(record["adopted_paths"]) | {"later.txt"}
    assert manifest["paths"]["README.md"] != record["candidate_manifest"]["paths"]["README.md"]


def test_resumed_provider_cannot_change_unadopted_identity(repository, tmp_path):
    source, _ = adopted_source(repository, tmp_path, operator_dirt=True)
    runner = DispositionFakeRunner(hooks={0: lambda cwd, _prompt: (
        cwd / "operator.txt").write_text("provider replaced operator bytes\n")})
    with pytest.raises(adoption.AdoptionError, match="unadopted or excluded entry objects changed"):
        make_dispatcher(repository, tmp_path / "refused", runner).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    state = read_state(only_run(tmp_path / "refused/runs"))
    assert "operator.txt" not in state["phase_owned_paths"]


def test_chained_resume_carries_prior_work_and_later_delta(repository, tmp_path):
    snapshot = tmp_path / "second-kill-point"
    def work(cwd, _prompt):
        (cwd / "first-work.txt").write_text("first closed work\n")
    source, record = adopted_source(repository, tmp_path, at=3, before={2: work})
    def lose(_cwd, _prompt):
        shutil.copytree(only_run(tmp_path / "second/runs"), snapshot)
        raise RuntimeError("lost during closeout")
    with pytest.raises((DispatchError, RuntimeError)):
        make_dispatcher(repository, tmp_path / "second", DispositionFakeRunner(
            hooks={1: lose})).resume(PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    second = only_run(tmp_path / "second/runs")
    for sibling in second.parent.iterdir():
        if sibling != second:
            sibling.unlink()
    shutil.rmtree(second)
    shutil.copytree(snapshot, second)
    record_dead_controller(second)
    assert read_state(second)["entry"]["tree"] != record["candidate_tree"]
    def later(cwd, _prompt):
        (cwd / "second-work.txt").write_text("later closed work\n")
    result = make_dispatcher(repository, tmp_path / "third", DispositionFakeRunner(
        hooks={0: later})).resume(PHASE_ID, REQUEST, second, finalization_policy="checkpoint")
    assert result["complete"]
    assert result["candidate_manifest"]["entry_tree"] == record["base_tree"]
    assert set(result["candidate_manifest"]["paths"]) == set(record["adopted_paths"]) | {
        "first-work.txt", "second-work.txt"}
    final = make_dispatcher(repository, tmp_path / "fourth", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, Path(result["run_directory"]), "finalize", finalization_policy="checkpoint")
    assert final["complete"] and final["candidate_manifest"] == result["candidate_manifest"]


def test_interrupted_extra_path_remains_manager_residue(repository, tmp_path):
    source, record = adopted_source(repository, tmp_path, mutate=lambda cwd: (
        cwd / "residue.txt").write_text("interrupted bytes\n"))
    result = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert result["resume_boundary"]["interrupted_residue_paths"] == ["residue.txt"]
    assert result["manager_disposition_required"]
    assert "residue.txt" not in result["phase_owned_paths"]
    assert "residue.txt" not in result.get("mechanical_phase_owned_paths", [])
    assert any(item["reason"] == "interrupted_stage_residue"
               for item in result["ownership_challenges"]["records"])
    assert set(result["candidate_manifest"]["paths"]) == set(record["adopted_paths"])


def test_interrupted_adopted_object_edit_refuses_before_provider(repository, tmp_path):
    source, _ = adopted_source(repository, tmp_path, mutate=lambda cwd: (
        cwd / "adopted.txt").write_text("interrupted replacement\n"))
    runner = DispositionFakeRunner()
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path / "refused", runner).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert caught.value.code == "RESUME_CANDIDATE_CONFLICT" and runner.calls == []


@pytest.mark.parametrize("damage", ["checksum", "base", "blob", "missing_tree", "missing_blob",
                                   "retained", "baseline", "identity", "phase", "request", "both"])
def test_entry_authority_corruption_refuses(repository, tmp_path, damage):
    source, record = adopted_source(repository, tmp_path)
    state = read_state(source)
    if damage in {"checksum", "base", "blob", "missing_tree", "missing_blob", "phase", "request"}:
        if damage == "checksum":
            record["reason"] = "unsealed replacement"
        elif damage == "base":
            record["base_tree"] = record["candidate_tree"]
        elif damage == "blob":
            record["path_metadata"]["adopted.txt"]["blob_sha"] = git(
                repository, "rev-parse", "HEAD:README.md")
        elif damage == "missing_tree":
            record["candidate_tree"] = "f" * 40
        elif damage == "missing_blob":
            record["path_metadata"]["adopted.txt"]["blob_sha"] = "f" * 40
        elif damage == "phase":
            record["phase_id"] = "OTHER-PHASE"
        else:
            record["request_sha256"] = "f" * 64
        if damage != "checksum":
            record.pop("sha256")
            record["sha256"] = adoption.digest(record)
        state["entry_adoption"] = record
        (source / "entry-adoption.json").write_text(json.dumps(record))
    elif damage == "retained":
        (source / "entry-adoption.json").write_text("{}")
    elif damage == "baseline":
        state["candidate_baseline"]["manifest"] = {}
    elif damage == "identity":
        state["adopted_candidate_identity"] = {}
    else:
        state["adoption"] = {}
    write_state(source, state)
    runner = DispositionFakeRunner()
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path / "refused", runner).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"
    assert runner.calls == []


@pytest.mark.parametrize("damage", ["base", "extra", "missing", "object", "residue"])
def test_recorded_manifest_disagreement_refuses(repository, tmp_path, damage):
    source, _ = adopted_source(repository, tmp_path, mutate=lambda cwd: (
        cwd / "residue.txt").write_text("interrupted bytes\n"))
    state = read_state(source)
    manifest = state["candidate_manifest"]
    if damage == "base":
        manifest["entry_tree"] = manifest["candidate_tree"]
    elif damage == "missing":
        manifest["paths"].pop("adopted.txt")
    elif damage == "object":
        manifest["paths"]["adopted.txt"] = manifest["paths"]["README.md"]
    else:
        path = "residue.txt" if damage == "residue" else "extra.txt"
        manifest["paths"][path] = manifest["paths"]["adopted.txt"]
    write_state(source, state)
    runner = DispositionFakeRunner()
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path / "refused", runner).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH" and runner.calls == []


def test_unadopted_operator_delta_cannot_expand_ownership(repository, tmp_path):
    source, _ = adopted_source(repository, tmp_path, operator_dirt=True, at=3, before={
        2: lambda cwd, _prompt: (cwd / "operator.txt").write_text("smuggled delta\n")})
    runner = DispositionFakeRunner()
    with pytest.raises(DispatchError):
        make_dispatcher(repository, tmp_path / "refused", runner).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert runner.calls == []


def test_entry_adoption_head_skew_and_finalize_after_commit_refuse(repository, tmp_path):
    source, _ = adopted_source(repository, tmp_path)
    result = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    git(repository, "add", "README.md", "adopted.txt")
    git(repository, "commit", "-qm", "local materialization")
    for index, run in enumerate((source, Path(result["run_directory"]))):
        runner = DispositionFakeRunner()
        with pytest.raises(DispatchError) as caught:
            make_dispatcher(repository, tmp_path / f"refused-{index}", runner).resume(
                PHASE_ID, REQUEST, run, finalization_policy="checkpoint")
        assert caught.value.code == "RESUME_ARTIFACT_MISMATCH" and runner.calls == []


def test_cli_entry_adoption_resume(repository, tmp_path, monkeypatch, capsys):
    source, record = adopted_source(repository, tmp_path)
    runner = DispositionFakeRunner()
    monkeypatch.setattr(cli_module, "Dispatcher", lambda *_args, **_kwargs:
                        make_dispatcher(repository, tmp_path / "cli", runner))
    monkeypatch.chdir(repository)
    assert cli_module.dispatch_main([str(source / "request.json"), "--resume", str(source),
                                    "--finalization", "checkpoint", "--quiet"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["candidate_manifest"] == record["candidate_manifest"]
    assert result["entry_adoption"] == record and len(runner.calls) == 3


def test_no_adoption_interrupted_resume_keeps_entry_base(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, lambda _cwd: None)
    entry = read_state(source)["entry"]["tree"]
    result = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert result["complete"]
    assert result["candidate_manifest"] == gitstate.candidate_manifest(repository, entry, entry)
    assert not adoption.paths(result)


def test_entry_adoption_mechanical_failure_reproves_base(repository, tmp_path):
    _interrupted, record = adopted_source(repository, tmp_path)
    def fail(cwd, _prompt):
        (cwd / "failure-work.txt").write_text("surviving failed work\n")
        raise RuntimeError("failed mutating stage")
    with pytest.raises((DispatchError, RuntimeError)):
        make_dispatcher(repository, tmp_path / "failure", DispositionFakeRunner(
            hooks={2: fail})).dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint",
                                    entry_adoption=tmp_path / "entry-receipt.json")
    source = only_run(tmp_path / "failure/runs")
    failed = read_state(source)
    assert failed["failure_candidate"]["stage"] == "work"
    assert failed["candidate_manifest"]["entry_tree"] == record["base_tree"]
    result = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert result["complete"]
    assert result["candidate_manifest"]["entry_tree"] == record["base_tree"]
    assert set(result["candidate_manifest"]["paths"]) == set(record["adopted_paths"]) | {"failure-work.txt"}


def test_output_recovery_entry_adoption_preserves_base_and_operator_dirt(repository, tmp_path):
    import test_agent_phase_output_recovery as output
    from agent_phase.dispatch import Dispatcher
    (repository / "adopted.txt").write_text("adopted entry\n")
    (repository / "operator.txt").write_text("unchanged operator\n")
    request = tmp_path / "output-request.json"
    request.write_text(json.dumps(output.REQUEST.as_dict()))
    record = entry_adoption.create(request, repository, ["adopted.txt"],
                                  reason="Output recovery regression", phase_id=output.PHASE)
    receipt = tmp_path / "output-entry.json"
    receipt.write_text(json.dumps(record))
    response = output.response_bytes(13227)
    runner = output.SourceRunner(repository, ["produced.txt"], response)
    with pytest.raises(DispatchError) as caught:
        Dispatcher(output.ROOT, repository, run_root=tmp_path / "output-source",
                   runner=runner, resolve_scanner=False).dispatch(output.PHASE, output.REQUEST,
            lifecycle="work-reviewed", finalization_policy="checkpoint", entry_adoption=receipt)
    assert caught.value.code == "PROVIDER_OUTPUT_LIMIT"
    source = next((tmp_path / "output-source").rglob("state.json")).parent
    assert read_state(source)["candidate_manifest"]["entry_tree"] == record["base_tree"]
    result = Dispatcher(output.ROOT, repository, run_root=tmp_path / "output-resumed",
        runner=output.RecoveryRunner(repository, response, "produced.txt"), resolve_scanner=False).resume(
            output.PHASE, output.REQUEST, source, lifecycle="work-reviewed", finalization_policy="checkpoint")
    assert result["complete"]
    assert result["candidate_manifest"]["entry_tree"] == record["base_tree"]
    assert set(result["candidate_manifest"]["paths"]) == {"adopted.txt", "produced.txt"}
    assert (repository / "operator.txt").read_text() == "unchanged operator\n"
