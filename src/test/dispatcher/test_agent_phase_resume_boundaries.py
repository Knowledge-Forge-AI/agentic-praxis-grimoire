from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import zipfile

import pytest

from agent_phase.dispatch import DispatchError
from agent_phase import finalization as finalization_module
from agent_phase import plan_material as plan_material_module
from agent_phase import resume as resume_module
from agent_phase import resume_validation as resume_validation_module
from agent_phase import resume_dispatch as resume_dispatch_module
from agent_phase.lifecycle import get_lifecycle
from test_agent_phase_resume import PHASE, REQUEST, Runner, dispatcher, duplicate_source, failed_source, git, only_run, repository as _repository

repository = _repository


@pytest.mark.parametrize(
    ("lifecycle", "completed_stage"),
    [("solo", "solo"), ("work-reviewed", "produce")],
)
def test_non_plan_lifecycle_rejects_escaped_plan_material_binding(
    tmp_path: Path, lifecycle: str, completed_stage: str
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    binding = plan_material_module.bind(b"canonical plan\n", "codex", "fixture")
    binding["relative_path"] = "../operator-private.md"
    candidate_key = "solo_candidate" if lifecycle == "solo" else "produced_candidate"

    with pytest.raises(resume_validation_module.ResumeError) as caught:
        resume_validation_module.validate_bindings(
            source,
            {
                "lifecycle": lifecycle,
                "plan_candidate": binding,
                candidate_key: {"tree": "f" * 40},
            },
            (completed_stage,),
        )

    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"


def test_artifact_records_rejects_escaped_provider_evidence_name(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (tmp_path / "operator-private.json").write_text("private\n")
    (source / "state.json").write_text("{}\n")
    for suffix in ("prompt.md", "stdout.md", "stderr.log"):
        (source / f"01-plan.{suffix}").write_text(f"{suffix}\n")
    (source / "01-plan.meta.json").write_text(
        json.dumps(
            {
                "provider": "codex",
                "antigravity_evidence": {
                    "validation": "validated",
                    "summary": {"relative_path": "../operator-private.json"},
                    "raw": None,
                },
            }
        )
    )

    with pytest.raises(resume_validation_module.ResumeError) as caught:
        resume_module.artifact_records(
            source, ("plan",), get_lifecycle("standard")
        )

    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"


@pytest.mark.parametrize("field", ["provider", "profile"])
def test_plan_binding_route_identity_must_match_plan_stage_metadata(
    repository: Path, tmp_path: Path, field: str
) -> None:
    source = failed_source(repository, tmp_path, 1)
    state = json.loads((source / "state.json").read_text(encoding="utf-8"))
    state["plan_candidate"][field] = "drifted-route-identity"

    with pytest.raises(resume_validation_module.ResumeError) as caught:
        resume_validation_module.validate_bindings(source, state, ("plan",))

    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"


def test_resume_final_review_requires_exact_pre_final_tree(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 3, mutate_at=2)
    runner = Runner()

    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "final-review"
    )

    assert len(runner.calls) == 2
    assert state["effective_stages"]["work"] == "inherited"
    assert state["effective_stages"]["final_review"] == "performed"


def test_resume_allows_unrelated_commit_and_worktree_dirt_and_commits_at_current_parent(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 0)
    old_entry_head = git(repository, "rev-parse", "HEAD")
    (repository / "concurrent.txt").write_text("concurrent commit\n")
    git(repository, "add", "concurrent.txt")
    git(repository, "commit", "-q", "-m", "unrelated concurrent commit")
    current_parent = git(repository, "rev-parse", "HEAD")
    assert current_parent != old_entry_head
    (repository / "operator-notes.txt").write_text("leave me alone\n")

    state = dispatcher(
        repository, tmp_path / "resumed", Runner(mutate_at=2)
    ).resume(PHASE, REQUEST, source, "plan")

    assert state["commit"] is not None
    assert git(repository, "rev-parse", "HEAD^") == current_parent
    assert (repository / "operator-notes.txt").read_text() == "leave me alone\n"
    assert git(repository, "status", "--short") == "?? operator-notes.txt"
    assert state["resume"]["evidence_boundary_skew"] is True


def test_resume_rejects_conflicting_inherited_candidate_path_before_provider(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 3, mutate_at=2)
    (repository / "phase.txt").write_text("conflicting concurrent bytes\n")
    runner = Runner()

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "conflict", runner).resume(
            PHASE, REQUEST, source, "final-review"
        )

    assert caught.value.code == "RESUME_CANDIDATE_CONFLICT"
    assert runner.calls == []
    assert not (tmp_path / "conflict").exists()


def test_resume_legacy_source_derives_closed_candidate_manifest(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 3, mutate_at=2)
    source_state = json.loads((source / "state.json").read_text())
    source_result = json.loads((source / "result.json").read_text())
    source_state.pop("candidate_manifest", None)
    source_result.pop("candidate_manifest", None)
    (source / "state.json").write_text(
        json.dumps(source_state, indent=2, sort_keys=True) + "\n"
    )
    (source / "result.json").write_text(
        json.dumps(source_result, indent=2, sort_keys=True) + "\n"
    )
    assert "candidate_manifest" not in source_state

    state = dispatcher(repository, tmp_path / "derived", Runner()).resume(
        PHASE, REQUEST, source, "final-review", dry_run=True
    )

    manifest = state["candidate_manifest"]
    assert manifest["schema"] == "agent-phase-candidate-manifest-v1"
    assert manifest["entry_tree"] == source_state["entry"]["tree"]
    assert manifest["paths"]["phase.txt"]["present"] is True
    assert manifest["paths"]["phase.txt"]["type"] == "file"
    assert manifest["paths"]["phase.txt"]["size_bytes"] == len(b"stage 2\n")


@pytest.mark.parametrize(
    "marker",
    ["MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG"],
)
def test_resume_rejects_active_git_operation_before_provider(
    repository: Path, tmp_path: Path, marker: str
) -> None:
    source = failed_source(repository, tmp_path, 0)
    git_dir = Path(git(repository, "rev-parse", "--absolute-git-dir"))
    operation = git_dir / marker
    operation.write_text("f" * 40 if marker.endswith("HEAD") else "active\n")
    runner = Runner()

    try:
        with pytest.raises(DispatchError) as caught:
            dispatcher(repository, tmp_path / f"active-{marker}", runner).resume(
                PHASE, REQUEST, source
            )
        assert caught.value.code == "ENTRY_ACTIVE_GIT_OPERATION"
        assert runner.calls == []
    finally:
        operation.unlink()


def test_resume_closeout_from_exact_pre_final_tree_invokes_one_provider(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 4, mutate_at=2)
    runner = Runner()

    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "closeout"
    )

    assert len(runner.calls) == 1
    assert state["provider_invocations_inherited"] == 4
    assert state["provider_invocations_performed"] == 1


def test_closeout_result_failure_can_replay_from_recorded_mutated_tree(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = duplicate_source(repository, tmp_path, monkeypatch)
    runner = Runner()

    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "closeout"
    )

    assert len(runner.calls) == 1
    prompt = runner.calls[0].decode()
    assert "Prior failed closeout attempt (non-authoritative context)" in prompt
    assert state["resume"]["closeout_replayed"] is True


def test_work_failure_records_and_reuses_exact_surviving_candidate(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 2, mutate_at=2)
    source_state = json.loads((source / "state.json").read_text())
    runner = Runner(mutate_at=0)

    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "auto"
    )

    assert source_state["failure_candidate"]["stage"] == "work"
    assert source_state["failure_candidate"]["tree"] == state["resume"]["resume_start_tree"]
    assert len(runner.calls) == 3


def test_explicit_earlier_work_replay_invalidates_entire_source_suffix(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 4, mutate_at=2)
    (repository / "phase.txt").unlink()
    runner = Runner(mutate_at=0)

    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "work"
    )

    assert state["resume"]["invalidated_stages"] == ["work", "final_review"]
    assert state["effective_stages"]["final_review"] == "performed"
    assert state["effective_checkpoints"] == ["post_planning", "pre_final"]
    assert len(runner.calls) == 3


def test_route_drift_for_remaining_stage_is_routed_from_current_roster(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = failed_source(repository, tmp_path, 2)
    real_resolve = resume_dispatch_module.resolve

    def drifted(
        request, root, lifecycle="standard", finalization_policy="publish", *, roster=None
    ):
        value = real_resolve(
            request, root, lifecycle, finalization_policy, roster=roster
        )
        value["stages"]["work"]["profile"] = "drifted-profile"
        return value

    monkeypatch.setattr(resume_dispatch_module, "resolve", drifted)
    state = dispatcher(repository, tmp_path / "resumed", Runner()).resume(
        PHASE, REQUEST, source, "work", dry_run=True
    )
    assert state["outcome"] == "dry_run"
    assert state["effective_stage_routes"]["work"]["profile"] == "drifted-profile"
    assert state["route_transition"]["route_differences"]["work"]["differences"]["profile"] == {
        "source": "implementation-testing",
        "current": "drifted-profile",
    }


def test_current_route_semantic_lifecycle_mismatch_is_rejected_pre_provider(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = failed_source(repository, tmp_path, 2)
    real_resolve = resume_dispatch_module.resolve

    def invalid_role(
        request, root, lifecycle="standard", finalization_policy="publish", *, roster=None
    ):
        value = real_resolve(
            request, root, lifecycle, finalization_policy, roster=roster
        )
        value["stages"]["work"]["role"] = "wrong-role"
        return value

    monkeypatch.setattr(resume_dispatch_module, "resolve", invalid_role)
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "resumed", Runner()).resume(
            PHASE, REQUEST, source, "work"
        )
    assert caught.value.code == "RESUME_CURRENT_ROUTE_INVALID"


def test_roster_digest_drift_is_accepted_and_records_roster_changed(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = failed_source(repository, tmp_path, 2)
    real_resolve = resume_dispatch_module.resolve

    def drifted(
        request, root, lifecycle="standard", finalization_policy="publish", *, roster=None
    ):
        value = real_resolve(
            request, root, lifecycle, finalization_policy, roster=roster
        )
        value["roster"]["sources"]["routes"]["sha256"] = "0" * 64
        return value

    monkeypatch.setattr(resume_dispatch_module, "resolve", drifted)
    state = dispatcher(repository, tmp_path / "resumed", Runner()).resume(
        PHASE, REQUEST, source, "work", dry_run=True
    )
    assert state["outcome"] == "dry_run"
    assert state["route_transition"]["roster_changed"] is True


def _rewrite_source_resolved(source: Path, transform) -> None:
    path = source / "resolved.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    transform(value)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _downgrade_source_to_v4(source: Path) -> None:
    def downgrade(value: dict[str, object]) -> None:
        value["schema"] = "agent-phase-resolved-v4"
        value.pop("roster", None)
        for stage in value["stages"].values():
            stage.pop("endpoint_alias", None)

    _rewrite_source_resolved(source, downgrade)


def test_v5_roster_generation_drift_is_accepted_and_records_roster_changed(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = failed_source(repository, tmp_path, 2)
    real_resolve = resume_dispatch_module.resolve

    def drifted(
        request, root, lifecycle="standard", finalization_policy="publish", *, roster=None
    ):
        value = real_resolve(
            request, root, lifecycle, finalization_policy, roster=roster
        )
        value["roster"]["generation"] += 1
        return value

    monkeypatch.setattr(resume_dispatch_module, "resolve", drifted)
    runner = Runner()
    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "work", dry_run=True
    )
    assert state["outcome"] == "dry_run"
    assert state["route_transition"]["roster_changed"] is True


def test_v4_resume_allows_exact_remaining_stage_equality(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 2)
    _downgrade_source_to_v4(source)

    state = dispatcher(repository, tmp_path / "resumed", Runner()).resume(
        PHASE, REQUEST, source, "work", dry_run=True
    )

    assert state["resume"]["roster_compatibility"] == "inherited_prefix_current_suffix"


def test_v4_resume_routes_remaining_stages_from_current_roster(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 2)
    _downgrade_source_to_v4(source)
    _rewrite_source_resolved(
        source,
        lambda value: value["stages"]["work"].__setitem__(
            "profile", "historical-drift"
        ),
    )
    runner = Runner()
    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "work", dry_run=True
    )
    assert state["outcome"] == "dry_run"
    assert state["resume"]["roster_compatibility"] == "inherited_prefix_current_suffix"
    assert state["effective_stage_routes"]["plan"]["source"] == "inherited"
    assert state["effective_stage_routes"]["work"]["source"] == "current"


def test_unknown_resolved_schema_is_rejected_with_stable_error(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 2)
    _rewrite_source_resolved(
        source,
        lambda value: value.__setitem__("schema", "agent-phase-resolved-v99"),
    )
    runner = Runner()

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "resumed", runner).resume(
            PHASE, REQUEST, source, "work"
        )

    assert caught.value.code == "RESUME_RESOLVED_SCHEMA_UNSUPPORTED"
    assert runner.calls == []


def test_v4_resolved_source_with_roster_fails_closed(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 2)
    _downgrade_source_to_v4(source)
    _rewrite_source_resolved(
        source,
        lambda value: value.__setitem__("roster", {"schema": "bogus"}),
    )
    runner = Runner()

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "resumed", runner).resume(
            PHASE, REQUEST, source, "work"
        )
    assert caught.value.code == "RESUME_RESOLVED_SCHEMA_UNSUPPORTED"


def test_v4_finalization_only_resume_loads_no_current_roster(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = duplicate_source(repository, tmp_path, monkeypatch)
    _downgrade_source_to_v4(source)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("finalization-only V4 resume loaded a current roster")

    monkeypatch.setattr(resume_dispatch_module, "load_validated_roster", forbidden)
    state = dispatcher(repository, tmp_path / "resumed", Runner()).resume(
        PHASE, REQUEST, source, "finalize"
    )

    assert state["provider_invocations_performed"] == 0
    assert state["resume"]["roster_compatibility"] == "finalization_only_no_current_roster"


def test_standalone_archive_contains_inherited_artifacts_and_hash_provenance(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = duplicate_source(repository, tmp_path, monkeypatch)

    state = dispatcher(repository, tmp_path / "resumed", lambda *args: None).resume(
        PHASE, REQUEST, source, "finalize"
    )

    with zipfile.ZipFile(state["archive_path"]) as archive:
        names = set(archive.namelist())
        leaf = Path(state["run_directory"]).name
        assert f"{leaf}/resume.json" in names
        assert f"{leaf}/inherited/source-state.json" in names
        assert f"{leaf}/01-plan.stdout.md" in names
        resume = json.loads(archive.read(f"{leaf}/resume.json"))
    assert len(resume["inherited_artifacts"]) >= 20
    assert all(
        item["sha256"] == item["destination_sha256"]
        for item in resume["inherited_artifacts"]
    )


def test_finalize_preserves_preexisting_dirty_state_without_a_commit(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (repository / "base.txt").write_text("operator dirt\n")
    source = duplicate_source(
        repository, tmp_path, monkeypatch, mutate=False, subject=None
    )

    state = dispatcher(repository, tmp_path / "resumed", lambda *args: None).resume(
        PHASE, REQUEST, source, "finalize"
    )

    assert state["commit"] is None
    assert (repository / "base.txt").read_text() == "operator dirt\n"
    assert git(repository, "status", "--short") == "M base.txt"


def test_finalize_reuses_existing_exact_commit_and_remote_state(
    repository: Path, tmp_path: Path
) -> None:
    source_root = tmp_path / "source-complete"
    original = dispatcher(repository, source_root, Runner(mutate_at=4)).dispatch(
        PHASE, REQUEST
    )
    source = Path(original["run_directory"])
    commit_count = int(git(repository, "rev-list", "--count", "HEAD"))

    state = dispatcher(repository, tmp_path / "resumed", lambda *args: None).resume(
        PHASE, REQUEST, source, "finalize"
    )

    assert state["commit"]["sha"] == original["commit"]["sha"]
    assert state["commit_reused"] is True
    assert state["push"]["already_published"] is True
    assert state["push"]["attempted"] is False
    assert int(git(repository, "rev-list", "--count", "HEAD")) == commit_count


def test_finalize_resumed_publication_supplies_entry_branch(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_root = tmp_path / "source-complete"
    original = dispatcher(repository, source_root, Runner(mutate_at=4)).dispatch(
        PHASE, REQUEST
    )
    source = Path(original["run_directory"])
    entry_branch = git(repository, "branch", "--show-current")

    captured_kws: list[dict[str, Any]] = []
    real_reuse = finalization_module.publish_or_reuse

    def spy_reuse(*args: Any, **kwargs: Any) -> dict[str, Any]:
        captured_kws.append(kwargs)
        return real_reuse(*args, **kwargs)

    monkeypatch.setattr(finalization_module, "publish_or_reuse", spy_reuse)

    state = dispatcher(repository, tmp_path / "resumed", lambda *args: None).resume(
        PHASE, REQUEST, source, "finalize"
    )

    assert state["push"]["already_published"] is True
    assert len(captured_kws) == 1
    assert captured_kws[0].get("expected_branch") == entry_branch



def test_unrelated_head_drift_is_allowed_and_artifact_drift_is_typed(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 0)
    (repository / "unrelated.txt").write_text("new\n")
    git(repository, "add", "unrelated.txt")
    git(repository, "commit", "-q", "-m", "unrelated")
    unrelated_head = git(repository, "rev-parse", "HEAD")

    state = dispatcher(repository, tmp_path / "head-resume", Runner()).resume(
        PHASE, REQUEST, source
    )
    assert state["commit"] is None
    assert state["resume"]["evidence_boundary_skew"] is True
    assert git(repository, "rev-parse", "HEAD") == unrelated_head

    git(repository, "reset", "-q", "--hard", "HEAD^")
    source = failed_source(repository, tmp_path, 1)
    (source / "01-plan.stdout.md").write_text("tampered")
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "artifact-resume", Runner()).resume(
            PHASE, REQUEST, source
        )
    assert caught.value.code == "RESUME_ARTIFACT_MISMATCH"


def test_resume_rejects_staged_index_before_provider(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 0)
    (repository / "base.txt").write_text("staged operator change\n")
    git(repository, "add", "base.txt")
    (repository / "base.txt").write_text("base\n")
    runner = Runner()

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "staged-resume", runner).resume(
            PHASE, REQUEST, source
        )

    assert caught.value.code == "RESUME_STAGED_CHANGES"
    assert runner.calls == []
    assert not (tmp_path / "staged-resume").exists()


def test_resume_rejects_same_commit_on_another_branch_before_provider(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 0)
    git(repository, "switch", "-q", "-c", "other-branch")
    runner = Runner()

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "branch-resume", runner).resume(
            PHASE, REQUEST, source
        )

    assert caught.value.code == "RESUME_BRANCH_MISMATCH"
    assert runner.calls == []
    assert not (tmp_path / "branch-resume").exists()


def test_dotted_source_run_records_exact_sibling_archive(
    repository: Path, tmp_path: Path
) -> None:
    dotted_phase = "APG90.self-contained"
    source_root = tmp_path / "dotted-source"
    with pytest.raises(DispatchError):
        dispatcher(repository, source_root, Runner(fail_at=0)).dispatch(
            dotted_phase, REQUEST
        )
    source = only_run(source_root)
    archive = source.parent / f"{source.name}.zip"
    assert archive.is_file()

    state = dispatcher(repository, tmp_path / "dotted-resume", Runner()).resume(
        dotted_phase, REQUEST, source, dry_run=True
    )

    source_archive = state["resume"]["source"]["archive"]
    assert source_archive["path"] == str(archive)
    assert len(source_archive["sha256"]) == 64
