"""Tests for FINALREC1 additive semantic vs Git finalization truth."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from agent_phase import archive as archive_module
from agent_phase import publication as publication_module
from agent_phase.dispatch import DispatchError
from agent_phase.outcomes import (
    REPAIRABLE_MECHANICAL,
    REQUIRES_MANAGER_OWNERSHIP,
    REQUIRES_REPOSITORY_RESOLUTION,
    REQUIRES_SEMANTIC_REVISION,
    classify_failure,
)
from agent_phase.request import PhaseRequest
from agent_phase.resume_validation import ResumeError, load_core

from test_agent_phase_dispatch import (
    PHASE_ID,
    FakeRunner,
    git,
    make_dispatcher,
    repository,
)

__all__ = ["repository"]

REQUEST = PhaseRequest("implementation_testing", "codex_only", "Implement it.")


def _read_run_artifacts(run_directory: Path | str) -> tuple[dict, dict, str]:
    run_dir = Path(run_directory)
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    result_md = (run_dir / "result.md").read_text(encoding="utf-8")
    return state, result, result_md


def _work_mutator(repo: Path):
    def on_stage(index: int) -> None:
        if index == 2:  # work stage
            (repo / "file.txt").write_text("mutation from work stage\n")
    return on_stage


def _latest_run_dir(tmp_path: Path) -> Path:
    state_files = list((tmp_path / "runs").rglob("state.json"))
    assert state_files, "no state.json found"
    return sorted(state_files, key=lambda p: p.stat().st_mtime)[-1].parent


# --- Requirement H1: Success ---


def test_h1_success_additive_truth(repository: Path, tmp_path: Path) -> None:
    """Requirement H1: on success, semantic_outcome and finalization_outcome are completed."""
    runner = FakeRunner(on_stage=_work_mutator(repository))
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="publish")

    assert state["outcome"] == "completed"
    assert state["complete"] is True
    assert state["semantic_outcome"] == "completed"
    assert state["finalization_outcome"] == "completed"
    assert state["finalization"]["outcome"] == "completed"
    assert state["commit"] is not None
    assert isinstance(state["commit"].get("sha"), str)

    saved_state, saved_result, saved_md = _read_run_artifacts(state["run_directory"])
    assert saved_state["semantic_outcome"] == "completed"
    assert saved_state["finalization_outcome"] == "completed"
    assert saved_result["semantic_outcome"] == "completed"
    assert saved_result["finalization_outcome"] == "completed"
    assert saved_result["outcome"] == "completed"
    assert saved_result["complete"] is True

    # Human report shows split
    assert "- outcome: **completed**" in saved_md
    assert "- semantic outcome: **completed**" in saved_md
    assert "- finalization: **completed**" in saved_md


# --- Requirement H2: Provider Blocker ---


def test_h2_provider_blocker_additive_truth(repository: Path, tmp_path: Path) -> None:
    """Requirement H2: when provider reports blocked, finalization is not_attempted."""
    runner = FakeRunner(closeout_outcome="blocked")
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    with pytest.raises(DispatchError) as exc_info:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert "PROVIDER_OUTCOME_BLOCKED" in str(exc_info.value)
    run_dir = _latest_run_dir(tmp_path)
    saved_state, saved_result, saved_md = _read_run_artifacts(run_dir)

    assert saved_state["outcome"] == "blocked"
    assert saved_state["complete"] is False
    assert saved_state["semantic_outcome"] == "blocked"
    assert saved_state["finalization_outcome"] == "not_attempted"
    assert saved_state["finalization"]["outcome"] == "not_attempted"
    assert saved_state["finalization_attempted"] is False
    assert saved_state["commit"] is None

    assert saved_result["outcome"] == "blocked"
    assert saved_result["complete"] is False
    assert saved_result["semantic_outcome"] == "blocked"
    assert saved_result["finalization_outcome"] == "not_attempted"
    assert saved_result["finalization"]["outcome"] == "not_attempted"

    assert "- outcome: **blocked**" in saved_md
    assert "- semantic outcome: **blocked**" in saved_md
    assert "- finalization: **not_attempted**" in saved_md


# --- Requirement H3: Git Blocker ---


def test_h3_git_blocker_additive_truth(repository: Path, tmp_path: Path) -> None:
    """Requirement H3: terminal outcome validated, but Git finalization blocked (e.g. branch mismatch)."""
    def switch_branch_before_closeout(stage_index: int) -> None:
        if stage_index == 2:
            (repository / "file.txt").write_text("mutation from work stage\n")
        elif stage_index == 4:
            # Switch branch right before closeout stage
            git(repository, "checkout", "-b", "tampered-branch")

    runner = FakeRunner(on_stage=switch_branch_before_closeout)
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    with pytest.raises(DispatchError) as exc_info:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert "GIT_AUTHORITY_BRANCH_MISMATCH" in str(exc_info.value)
    run_dir = _latest_run_dir(tmp_path)
    saved_state, saved_result, saved_md = _read_run_artifacts(run_dir)

    # Semantic truth was captured at terminal parse and retained!
    assert saved_state["semantic_outcome"] == "completed"
    assert saved_state["finalization_outcome"] == "blocked"
    assert saved_state["finalization"]["outcome"] == "blocked"
    assert saved_state["outcome"] == "blocked"
    assert saved_state["complete"] is False
    assert saved_state["commit"] is None

    assert saved_result["semantic_outcome"] == "completed"
    assert saved_result["finalization_outcome"] == "blocked"
    assert saved_result["outcome"] == "blocked"
    assert saved_result["complete"] is False

    assert "- outcome: **blocked**" in saved_md
    assert "- semantic outcome: **completed**" in saved_md
    assert "- finalization: **blocked**" in saved_md


# --- Requirement H4: Commit Success / Push Failure ---


def test_h4_commit_success_push_failure_additive_truth(repository: Path, tmp_path: Path) -> None:
    """Requirement H4: commit succeeds locally, push fails; local commit is preserved."""
    runner = FakeRunner(on_stage=_work_mutator(repository))
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    # Mock publish to raise PublicationError
    def failing_publish(*args, **kwargs):
        raise publication_module.PublicationError(
            "GIT_PUSH_FAILED",
            "mock push failure",
            {
                "attempted": True,
                "status": "failed",
                "failure": {"code": "GIT_PUSH_FAILED", "detail": "mock push failure"},
            },
        )

    with patch("agent_phase.finalization.publish", side_effect=failing_publish):
        with pytest.raises(DispatchError) as exc_info:
            dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="publish")

    assert "GIT_PUSH_FAILED" in str(exc_info.value)
    run_dir = _latest_run_dir(tmp_path)
    saved_state, saved_result, saved_md = _read_run_artifacts(run_dir)

    # Semantic outcome retained
    assert saved_state["semantic_outcome"] == "completed"
    # Finalization is blocked because push failed
    assert saved_state["finalization_outcome"] == "blocked"
    assert saved_state["finalization"]["outcome"] == "blocked"
    # Local commit success is preserved separately from push failure!
    assert saved_state["commit"] is not None
    assert isinstance(saved_state["commit"]["sha"], str)
    assert saved_state["push"]["status"] == "failed"
    assert saved_state["finalization"]["local_commit"]["outcome"] == "completed"
    # Compatibility outcome is conservative
    assert saved_state["outcome"] == "blocked"
    assert saved_state["complete"] is False

    assert saved_result["semantic_outcome"] == "completed"
    assert saved_result["finalization_outcome"] == "blocked"
    assert saved_result["commit"] is not None
    assert saved_result["outcome"] == "blocked"
    assert saved_result["complete"] is False


# --- Requirement H5: Archive Failure ---


def test_h5_archive_failure_additive_truth(repository: Path, tmp_path: Path) -> None:
    """Requirement H5: provider and git succeed, archive fails; conservative compatibility outcome."""
    runner = FakeRunner(on_stage=_work_mutator(repository))
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    def failing_archive_create(*args, **kwargs):
        raise archive_module.ArchiveError("RUN_ARCHIVE_FAILED", "simulated disk failure")

    with patch("agent_phase.archive.create", side_effect=failing_archive_create):
        with pytest.raises(DispatchError) as exc_info:
            dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="commit-local")

    assert "RUN_ARCHIVE_FAILED" in str(exc_info.value)
    run_dir = _latest_run_dir(tmp_path)
    saved_state, saved_result, saved_md = _read_run_artifacts(run_dir)

    # Semantic and finalization truth retained
    assert saved_state["semantic_outcome"] == "completed"
    assert saved_state["finalization_outcome"] == "completed"
    assert saved_state["commit"] is not None
    # Existing compatibility result is preserved; archive delivery is orthogonal.
    assert saved_state["outcome"] == "completed"
    assert saved_state["complete"] is True
    assert saved_result["semantic_outcome"] == "completed"
    assert saved_result["finalization_outcome"] == "completed"
    assert saved_state["archive"]["failure"]["code"] == "RUN_ARCHIVE_FAILED"


# --- Requirement H18: Optional Additive Fields in resume_validation.load_core ---


def test_h18_optional_additive_fields_load_core(repository: Path, tmp_path: Path) -> None:
    """Requirement H18: load_core validates additive fields, allowing historical absent without inventing completion."""
    runner = FakeRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    run_dir = Path(state["run_directory"])

    # Modern run with matching fields loads successfully
    src, loaded_state, loaded_result, _, _, _ = load_core(
        run_dir, PHASE_ID, REQUEST, repository, state["project"]
    )
    assert loaded_state["semantic_outcome"] == "completed"
    assert loaded_state["finalization_outcome"] == "completed"

    # Historical run: absent from both state.json and result.json
    state_file = run_dir / "state.json"
    result_file = run_dir / "result.json"
    s_data = json.loads(state_file.read_text(encoding="utf-8"))
    r_data = json.loads(result_file.read_text(encoding="utf-8"))

    s_hist = {k: v for k, v in s_data.items() if k not in ("semantic_outcome", "finalization_outcome", "finalization")}
    r_hist = {k: v for k, v in r_data.items() if k not in ("semantic_outcome", "finalization_outcome", "finalization")}
    state_file.write_text(json.dumps(s_hist), encoding="utf-8")
    result_file.write_text(json.dumps(r_hist), encoding="utf-8")

    src, loaded_state, loaded_result, _, _, _ = load_core(
        run_dir, PHASE_ID, REQUEST, repository, state["project"]
    )
    assert "semantic_outcome" not in loaded_state
    assert "finalization_outcome" not in loaded_state

    # Disagreement on semantic_outcome raises ResumeError
    s_bad = dict(s_hist, semantic_outcome="completed")
    r_bad = dict(r_hist, semantic_outcome="blocked")
    state_file.write_text(json.dumps(s_bad), encoding="utf-8")
    result_file.write_text(json.dumps(r_bad), encoding="utf-8")

    with pytest.raises(ResumeError) as exc_info:
        load_core(run_dir, PHASE_ID, REQUEST, repository, state["project"])
    assert "RESUME_ARTIFACT_MISMATCH" in str(exc_info.value)

    # Disagreement where one is absent raises ResumeError
    s_bad = dict(s_hist, semantic_outcome="completed")
    r_bad = dict(r_hist)
    state_file.write_text(json.dumps(s_bad), encoding="utf-8")
    result_file.write_text(json.dumps(r_bad), encoding="utf-8")

    with pytest.raises(ResumeError) as exc_info:
        load_core(run_dir, PHASE_ID, REQUEST, repository, state["project"])
    assert "RESUME_ARTIFACT_MISMATCH" in str(exc_info.value)

    # Invalid finalization outcome value raises ResumeError
    s_bad = dict(s_hist, semantic_outcome="completed", finalization_outcome="invalid_status")
    r_bad = dict(r_hist, semantic_outcome="completed", finalization_outcome="invalid_status")
    state_file.write_text(json.dumps(s_bad), encoding="utf-8")
    result_file.write_text(json.dumps(r_bad), encoding="utf-8")

    with pytest.raises(ResumeError) as exc_info:
        load_core(run_dir, PHASE_ID, REQUEST, repository, state["project"])
    assert "RESUME_ARTIFACT_MISMATCH" in str(exc_info.value)


# --- Requirement H19: Human and JSON result artifacts show split ---


def test_h19_result_artifacts_show_split(repository: Path, tmp_path: Path) -> None:
    """Requirement H19: Human and JSON result artifacts show split."""
    runner = FakeRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    run_dir = Path(state["run_directory"])

    _, result_json, result_md = _read_run_artifacts(run_dir)

    assert "semantic_outcome" in result_json
    assert "finalization_outcome" in result_json
    assert "finalization" in result_json
    assert "outcome" in result_json
    assert result_json["semantic_outcome"] == "completed"
    assert result_json["finalization_outcome"] == "completed"
    assert result_json["finalization"]["outcome"] == "completed"

    # Human Markdown artifact contains the split lines
    assert "- outcome: **completed**" in result_md
    assert "- semantic outcome: **completed**" in result_md
    assert "- finalization: **completed**" in result_md


# --- Classification Tests ---


@pytest.mark.parametrize("code,category", [
    ("PATH_DISPOSITION_INVALID", REQUIRES_MANAGER_OWNERSHIP),
    ("ENTRY_DIRT_OVERLAP", REQUIRES_MANAGER_OWNERSHIP),
    ("GIT_AUTHORITY_BRANCH_MISMATCH", REQUIRES_REPOSITORY_RESOLUTION),
    ("PROVIDER_OUTCOME_BLOCKED", REQUIRES_SEMANTIC_REVISION),
    ("METADATA_NORMALIZATION_VERIFIED", REPAIRABLE_MECHANICAL),
    ("CANDIDATE_MATERIALIZATION_VERIFIED", REPAIRABLE_MECHANICAL),
    ("RANDOM_SYSTEM_ERROR", REQUIRES_REPOSITORY_RESOLUTION),
])
def test_classifier_categories(code, category):
    assert classify_failure(code, {}) == category


def test_metadata_observations_alone_never_grant_repair():
    for state in (
        {"path_disposition_noops": [{"path": ".serena/cache"}]},
        {"stage_delta_ledger": {"retained_metadata_observations": [{"stage": "work"}]}},
        {"manager_disposition_required": True},
    ):
        assert classify_failure("PATH_DISPOSITION_INVALID", state) == REQUIRES_MANAGER_OWNERSHIP
    assert classify_failure("repairable_mechanical", {}) == REQUIRES_REPOSITORY_RESOLUTION
