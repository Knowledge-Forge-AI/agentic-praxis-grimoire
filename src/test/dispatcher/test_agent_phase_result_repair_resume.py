from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from agent_phase import candidate as candidate_module
from agent_phase import gitstate as gitstate_module
from agent_phase import result_repair as result_repair_module
from agent_phase.dispatch import DispatchError
from agent_phase.resume_validation import ResumeError
from test_agent_phase_result_repair import OrdinaryResumeRunner, RepairRunner, make_source, repair, repository as _repository, _repack_source_zip

repository = _repository


def file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_historical_v3_terminal_transport_accounting_remains_repairable(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    state_path = source / "state.json"
    result_path = source / "result.json"
    state = json.loads(state_path.read_text())
    result = json.loads(result_path.read_text())
    stages = state["expected_stages"]
    for key in (
        "stage_accounting_schema",
        "stages_invoked",
        "stage_transports_completed",
        "terminal_result_validated",
    ):
        state.pop(key, None)
        result.pop(key, None)
    state["stages_completed"] = stages
    result["stages_completed"] = stages
    result["schema"] = "agent-phase-result-v3"
    for record in (state, result):
        record["archive"]["status"] = "succeeded"
        record["archive"]["succeeded"] = True
        record["archive"].pop("receipt_path", None)
    state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    (source.parent / f"{source.name}.zip.receipt.json").unlink()
    _repack_source_zip(source)

    repaired = repair(repository, tmp_path, source, RepairRunner())

    assert repaired["complete"] is True
    assert repaired["result_repair"]["source_accounting_compatibility"] == (
        "historical-v3-terminal-transport-as-completed"
    )
    assert repaired["semantic_provider_invocations_inherited"] == 5
    assert repaired["stages_completed"] == stages


def test_auto_selects_detached_repair_without_live_snapshot_checks(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_source(repository, tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()

    def forbidden(*args, **kwargs):
        raise AssertionError("auto result repair inspected live Git")

    monkeypatch.setattr(candidate_module, "require_worktree", forbidden)
    monkeypatch.setattr(gitstate_module, "repository_root", forbidden)
    monkeypatch.setattr(gitstate_module, "capture_entry", forbidden)

    state = repair(
        plain, tmp_path, source, RepairRunner(), from_stage="auto"
    )

    assert state["resume"]["effective_from_stage"] == "result-repair"
    assert state["completion_kind"] == "detached_result_repair_checkpoint"


@pytest.mark.parametrize("archive_available", [True, False])
def test_auto_declines_repair_only_requirements_and_uses_ordinary_resume(
    repository: Path, tmp_path: Path, archive_available: bool
) -> None:
    source = make_source(
        repository,
        tmp_path,
        finalization_policy="publish",
    )
    archive = source.parent / f"{source.name}.zip"
    if not archive_available:
        archive.unlink()
    runner = OrdinaryResumeRunner()

    state = repair(
        repository,
        tmp_path,
        source,
        runner,
        from_stage="auto",
        finalization_policy=None,
    )

    assert state["resume"]["effective_from_stage"] == "closeout"
    assert state["completion_kind"] == "finalized_empty_delta"
    assert len(runner.calls) == 1
    assert runner.calls[0]["cwd"] == repository


def test_auto_declines_repair_only_cross_record_failure(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_source(repository, tmp_path)
    runner = OrdinaryResumeRunner()

    def repair_only_failure(*args: object, **kwargs: object) -> None:
        raise ResumeError("RESUME_ARTIFACT_MISMATCH", "repair-only cross-record drift")

    monkeypatch.setattr(
        result_repair_module,
        "_source_evidence_consistent",
        repair_only_failure,
    )

    state = repair(
        repository,
        tmp_path,
        source,
        runner,
        from_stage="auto",
        finalization_policy=None,
    )

    assert state["resume"]["effective_from_stage"] == "closeout"
    assert state["completion_kind"] == "checkpoint_ready"
    assert len(runner.calls) == 1


def test_detached_repair_dry_run_qualifies_without_provider_or_archive(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    runner = RepairRunner()

    state = repair(repository, tmp_path, source, runner, dry_run=True)

    assert state["outcome"] == "dry_run"
    assert state["repository_binding"] == "none"
    assert state["source_artifacts_verified"] is True
    assert state["auxiliary_provider_invocations_performed"] == 0
    assert runner.calls == []
    assert not Path(state["archive_path"]).exists()


def test_checkpoint_records_detached_truth_and_no_repository_claim(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)

    state = repair(repository, tmp_path, source, RepairRunner())
    run = Path(state["run_directory"])
    checkpoint = json.loads((run / "result-repair-checkpoint.json").read_text())
    result = json.loads((run / "result.json").read_text())

    expected = {
        "schema": "agent-phase-result-repair-checkpoint-v1",
        "completion_kind": "detached_result_repair_checkpoint",
        "repository_binding": "none",
        "repository_state_validated": False,
        "repository_mutation_attempted": False,
        "manager_disposition_required": True,
    }
    assert checkpoint == expected
    assert result["schema"] == "agent-phase-result-v4"
    assert result["entry"] is None
    assert result["entry_head"] is None
    assert result["final_head"] is None
    assert result["phase_delta"] == []
    assert result["commit"] is None
    assert result["push"]["status"] == "not_attempted_by_policy"
    assert result["repository_finalized"] is False
    assert result["repository_binding"] == "none"


def test_invocation_accounting_separates_semantic_and_auxiliary_turns(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)

    state = repair(repository, tmp_path, source, RepairRunner())

    assert state["semantic_provider_invocations_inherited"] == 5
    assert state["semantic_provider_invocations_performed"] == 0
    assert state["provider_invocations_inherited"] == 5
    assert state["provider_invocations_performed"] == 0
    assert state["auxiliary_provider_invocations"] == 1
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["provider_invocations_effective"] == 5
    assert state["total_effective_provider_turns"] == 6
    assert state["effective_stages"] == {
        "plan": "inherited",
        "plan_review": "inherited",
        "work": "inherited",
        "final_review": "inherited",
        "closeout": "validated_by_result_repair",
    }
    assert state["effective_checkpoints"] == ["post_planning", "pre_final"]


def test_source_directory_and_zip_remain_byte_identical(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    archive = source.parent / f"{source.name}.zip"
    before_files = file_hashes(source)
    before_archive = hashlib.sha256(archive.read_bytes()).hexdigest()

    state = repair(repository, tmp_path, source, RepairRunner())

    assert file_hashes(source) == before_files
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == before_archive
    assert state["source_artifacts_verified"] is True
    assert state["source_archive_verified"] is True


def test_resumed_archive_is_standalone_and_attaches_repaired_result(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)

    state = repair(repository, tmp_path, source, RepairRunner())

    with zipfile.ZipFile(state["archive_path"]) as archive:
        leaf = Path(state["run_directory"]).name
        names = set(archive.namelist())
        assert f"{leaf}/resume.json" in names
        assert f"{leaf}/inherited/source-state.json" in names
        assert f"{leaf}/05-closeout.stdout.md" in names
        assert f"{leaf}/result-repair.result.json" in names
        repaired = json.loads(archive.read(f"{leaf}/result-repair.result.json"))
    assert repaired["stage"] == "closeout"
    assert repaired["outcome"] == "completed"


def test_auxiliary_route_reuses_source_terminal_provider_profile_and_intelligence(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    source_resolved = json.loads((source / "resolved.json").read_text())
    runner = RepairRunner()

    state = repair(repository, tmp_path, source, runner)
    run = Path(state["run_directory"])
    meta = json.loads((run / "result-repair.meta.json").read_text())
    terminal = source_resolved["stages"]["closeout"]

    assert len(runner.calls) == 1
    assert meta["provider"] == terminal["provider"] == "antigravity"
    assert meta["profile"] == terminal["profile"]
    assert state["result_repair"]["source_terminal_intelligence"] == terminal["intelligence"]
    assert meta["antigravity_evidence"]["validation"] == "validated"


def test_source_drift_during_auxiliary_turn_fails_closed(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)

    class DriftingRunner(RepairRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            result = super().__call__(argv, prompt, cwd, max_output, on_output)
            (source / "state.json").write_bytes(
                (source / "state.json").read_bytes() + b"\n"
            )
            return result

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, DriftingRunner())

    assert caught.value.code == "RESULT_REPAIR_SOURCE_DRIFT"


def test_result_repair_is_one_shot_per_attempt(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    runner = RepairRunner(mode="malformed")

    with pytest.raises(DispatchError):
        repair(repository, tmp_path, source, runner)

    assert len(runner.calls) == 1
