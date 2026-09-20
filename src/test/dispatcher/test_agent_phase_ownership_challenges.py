"""OWNCHALLENGE1 regressions over disposable real Git repositories."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from agent_phase import candidate, gitstate, ownership_challenge, result
from agent_phase.dispatch import DispatchError
from test_agent_phase_disposition_flow import REQUEST, git, make_dispatcher, repository as _repository
from test_agent_phase_lifecycle_dispatch import (
    REQUEST as WORK_REVIEWED_REQUEST,
    LifecycleRunner,
    dispatcher as lifecycle_dispatcher,
)
from test_agent_phase_path_dispositions import OwnershipRunner, track

repository = _repository


def _state(tmp_path: Path) -> dict:
    states = list((tmp_path / "runs").rglob("state.json"))
    assert len(states) == 1
    return json.loads(states[0].read_text(encoding="utf-8"))


def _challenge_id(prompt: bytes) -> str:
    ids = re.findall(rb'"challenge_id"\s*:\s*"(ownch1-[0-9a-f]{64})"', prompt)
    assert len(ids) == 1
    return ids[0].decode("ascii")


@pytest.mark.parametrize("kind", ["addition", "modification"])
def test_clean_product_changes_are_mechanically_owned(
    repository: Path, tmp_path: Path, kind: str
) -> None:
    path = "product.txt" if kind == "addition" else "README.md"

    def produce(cwd: Path, _prompt: bytes) -> None:
        (cwd / path).write_text("phase product\n", encoding="utf-8")

    state = make_dispatcher(repository, tmp_path, OwnershipRunner(hooks={2: produce})).dispatch(
        "OWNCHALLENGE-CLEAN", REQUEST, finalization_policy="commit-local"
    )

    assert state["ownership_challenges"]["records"] == []
    assert state["phase_owned_paths"] == [path]
    assert state["commit"]
    assert git(repository, "show", f"HEAD:{path}") == "phase product"


def test_untracked_operational_metadata_does_not_create_challenge(
    repository: Path, tmp_path: Path
) -> None:
    head = git(repository, "rev-parse", "HEAD")

    def produce(cwd: Path, _prompt: bytes) -> None:
        metadata = cwd / ".serena" / "cache.json"
        metadata.parent.mkdir()
        metadata.write_text("metadata\n", encoding="utf-8")

    state = make_dispatcher(repository, tmp_path, OwnershipRunner(hooks={2: produce})).dispatch(
        "OWNCHALLENGE-METADATA", REQUEST, finalization_policy="commit-local"
    )

    assert state["ownership_challenges"]["records"] == []
    assert state["phase_owned_paths"] == []
    assert state["commit"] is None
    assert state["completion_kind"] == "finalized_empty_delta"
    assert git(repository, "rev-parse", "HEAD") == head
    assert (repository / ".serena" / "cache.json").is_file()


def test_tracked_metadata_looking_product_change_is_mechanically_owned(
    repository: Path, tmp_path: Path
) -> None:
    path = repository / ".serena" / "tracked.json"
    path.parent.mkdir()
    path.write_text("before\n", encoding="utf-8")
    git(repository, "add", "--", ".serena/tracked.json")
    git(repository, "commit", "-qm", "Track metadata-looking product")

    def produce(_cwd: Path, _prompt: bytes) -> None:
        path.write_text("after\n", encoding="utf-8")

    state = make_dispatcher(repository, tmp_path, OwnershipRunner(hooks={2: produce})).dispatch(
        "OWNCHALLENGE-TRACKED-METADATA", REQUEST, finalization_policy="commit-local"
    )

    assert state["ownership_challenges"]["records"] == []
    assert ".serena/tracked.json" in state["phase_owned_paths"]
    assert git(repository, "show", "HEAD:.serena/tracked.json") == "after"


def test_producer_deletion_challenge_is_shown_and_resolved_by_id(
    repository: Path, tmp_path: Path
) -> None:
    target = track(repository, "deleted.txt", symlink=False)

    def produce(cwd: Path, _prompt: bytes) -> None:
        target.unlink()
        (cwd / "product.txt").write_text("accepted\n", encoding="utf-8")

    runner = OwnershipRunner(
        hooks={2: produce}, challenge_decision="phase_owned"
    )
    state = make_dispatcher(repository, tmp_path, runner).dispatch(
        "OWNCHALLENGE-PRODUCER-DELETE", REQUEST, finalization_policy="commit-local"
    )

    record = state["ownership_challenges"]["records"][0]
    challenge_id = record["challenge_id"]
    terminal_prompt = runner.calls[-1]["prompt"]
    assert b"Dispatcher-owned ownership challenges" in terminal_prompt
    assert challenge_id.encode("ascii") in terminal_prompt
    assert record["boundary"] == "post_producer"
    assert record["reason"] == "unclaimed_tracked_deletion"
    events = state["ownership_challenges"]["events"]
    assert {event["kind"] for event in events} == {"shown", "resolved_by_provider"}
    assert any(
        event["kind"] == "resolved_by_provider"
        and event["challenge_id"] == challenge_id
        and event["decision"] == "phase_owned"
        and event["stage"] == "closeout"
        for event in events
    )
    assert state["phase_owned_paths"] == ["deleted.txt", "product.txt"]
    assert state["commit"]
    assert git(repository, "ls-tree", "HEAD", "--", "deleted.txt") == ""
    assert state["semantic_provider_invocations_performed"] == 5


def test_forged_provider_challenge_id_fails_closed_without_commit(
    repository: Path, tmp_path: Path
) -> None:
    target = track(repository, "deleted.txt", symlink=False)
    before = git(repository, "rev-parse", "HEAD")

    def produce(_cwd: Path, _prompt: bytes) -> None:
        target.unlink()

    runner = OwnershipRunner(
        hooks={2: produce},
        ownership_resolutions=lambda _prompt: [
            {"challenge_id": "ownch1-" + "0" * 64, "decision": "phase_owned"}
        ],
    )
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(
            "OWNCHALLENGE-FORGED-ID", REQUEST, finalization_policy="commit-local"
        )

    assert caught.value.code == "OWNERSHIP_PROVIDER_RESOLUTION_INVALID"
    state = _state(tmp_path)
    assert len(runner.calls) == 5
    assert state["finalization"]["repair_class"] == "requires_semantic_revision"
    assert not any(
        event["kind"] == "resolved_by_provider"
        for event in state["ownership_challenges"]["events"]
    )
    assert git(repository, "rev-parse", "HEAD") == before


def test_provider_resolution_becomes_stale_after_terminal_candidate_drift(
    repository: Path, tmp_path: Path
) -> None:
    target = track(repository, "deleted.txt", symlink=False)
    before = git(repository, "rev-parse", "HEAD")

    def produce(_cwd: Path, _prompt: bytes) -> None:
        target.unlink()

    def restore_at_terminal(_cwd: Path, _prompt: bytes) -> None:
        target.write_text("terminal replacement\n", encoding="utf-8")

    def resolve_shown(prompt: bytes) -> list[dict[str, str]]:
        return [{"challenge_id": _challenge_id(prompt), "decision": "phase_owned"}]

    runner = OwnershipRunner(
        hooks={2: produce, 4: restore_at_terminal},
        ownership_resolutions=resolve_shown,
    )
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(
            "OWNCHALLENGE-STALE-ID", REQUEST, finalization_policy="commit-local"
        )

    assert caught.value.code == "OWNERSHIP_PROVIDER_RESOLUTION_INVALID"
    state = _state(tmp_path)
    assert len(runner.calls) == 5
    assert any(
        event["kind"] == "superseded"
        for event in state["ownership_challenges"]["events"]
    )
    assert not any(
        event["kind"] == "resolved_by_provider"
        for event in state["ownership_challenges"]["events"]
    )
    assert git(repository, "rev-parse", "HEAD") == before


def test_terminal_introduced_deletion_creates_post_terminal_manager_challenge(
    repository: Path, tmp_path: Path
) -> None:
    target = track(repository, "terminal-deleted.txt", symlink=False)
    before = git(repository, "rev-parse", "HEAD")

    def mutate(stage: str, cwd: Path) -> None:
        if stage == "produce":
            (cwd / "product.txt").write_text("produced\n", encoding="utf-8")
        elif stage == "revise_close":
            target.unlink()

    runner = LifecycleRunner(mutate=mutate)
    state = lifecycle_dispatcher(repository, tmp_path, runner).dispatch(
        "OWNCHALLENGE-TERMINAL-DELETE",
        WORK_REVIEWED_REQUEST,
        lifecycle="work-reviewed",
        finalization_policy="commit-local",
    )

    records = state["ownership_challenges"]["records"]
    assert len(records) == 1
    assert records[0]["boundary"] == "post_terminal"
    assert records[0]["path"] == "terminal-deleted.txt"
    assert records[0]["reason"] == "unclaimed_tracked_deletion"
    assert not any(
        event["kind"] == "resolved_by_provider"
        for event in state["ownership_challenges"]["events"]
    )
    assert state["semantic_outcome"] == "completed"
    assert state["finalization_outcome"] == "blocked"
    assert state["finalization"]["repair_class"] == "requires_manager_ownership"
    assert state["commit"] is None
    assert len(runner.calls) == 3
    assert state["semantic_provider_invocations_performed"] == 3
    assert git(repository, "rev-parse", "HEAD") == before
    result_data = json.loads(
        Path(state["run_directory"], "result.json").read_text(encoding="utf-8")
    )
    assert result_data["semantic_outcome"] == "completed"
    assert result_data["finalization"]["repair_class"] == "requires_manager_ownership"


def test_actual_post_terminal_challenge_id_cannot_be_provider_resolved(
    repository: Path,
) -> None:
    target = track(repository, "terminal-known.txt", symlink=False)
    entry = gitstate.capture_entry(repository)
    target.unlink()
    raw = candidate.tree_identity(repository)["tree"]
    state = {
        "run_id": "OWNCHALLENGE-POST-TERMINAL-KNOWN",
        "project": "agent-central-test",
        "phase_id": "OWNCHALLENGE-POST-TERMINAL-KNOWN",
        "lifecycle": "work-reviewed",
        "controller_generation": "test-generation",
    }
    ownership_challenge.observe(
        repository, state, entry, raw, "revise_close", "post_terminal"
    )
    challenge_id = state["ownership_challenges"]["records"][0]["challenge_id"]

    with pytest.raises(result.ResultError, match="OWNERSHIP_PROVIDER_RESOLUTION_INVALID"):
        ownership_challenge.resolve_provider(
            repository,
            state,
            "revise_close",
            raw,
            [{"challenge_id": challenge_id, "decision": "phase_owned"}],
        )

    assert not any(
        event["kind"] == "resolved_by_provider"
        for event in state["ownership_challenges"]["events"]
    )


def test_reintroduced_identical_deletion_gets_new_id_even_at_same_timestamp(repository, monkeypatch):
    from datetime import datetime, timezone
    class FrozenClock:
        @staticmethod
        def now(zone):
            return datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(ownership_challenge, 'datetime', FrozenClock)
    target = track(repository, 'reintroduced.txt', symlink=False)
    entry = gitstate.capture_entry(repository)
    state = {'run_id': 'repeat', 'project': 'fixture', 'phase_id': 'repeat', 'lifecycle': 'standard'}
    target.unlink()
    raw = candidate.tree_identity(repository)['tree']
    ownership_challenge.observe(repository, state, entry, raw, 'work', 'post_producer')
    first = ownership_challenge.open_records(state)[0]['challenge_id']
    target.write_text('entry bytes\n')
    ownership_challenge.observe(repository, state, entry, entry.tree, 'work', 'post_producer')
    assert ownership_challenge.statuses(state)[first] == 'superseded'
    assert not ownership_challenge.decisions(state)
    target.unlink()
    ownership_challenge.observe(repository, state, entry, raw, 'work', 'post_producer')
    second = ownership_challenge.open_records(state)[0]['challenge_id']
    assert first != second
    assert [r['observation_sequence'] for r in state['ownership_challenges']['records']] == [0, 1]


def test_read_only_review_cannot_present_or_resolve_challenge(
    repository: Path,
) -> None:
    target = track(repository, "review-owned.txt", symlink=False)
    entry = gitstate.capture_entry(repository)
    target.unlink()
    raw = candidate.tree_identity(repository)["tree"]
    state = {
        "run_id": "OWNCHALLENGE-REVIEW",
        "project": "agent-central-test",
        "phase_id": "OWNCHALLENGE-REVIEW",
        "lifecycle": "standard",
        "controller_generation": "test-generation",
    }
    ownership_challenge.observe(
        repository, state, entry, raw, "work", "post_producer"
    )
    challenge_id = state["ownership_challenges"]["records"][0]["challenge_id"]

    # A review cannot create a presentation event, even through the prompt API.
    with pytest.raises(result.ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        ownership_challenge.prompt(repository, state, "final_review")
    assert state['ownership_challenges']['events'] == []
    with pytest.raises(result.ResultError, match="OWNERSHIP_PROVIDER_RESOLUTION_INVALID"):
        ownership_challenge.resolve_provider(
            repository,
            state,
            "final_review",
            raw,
            [{"challenge_id": challenge_id, "decision": "phase_owned"}],
        )
    assert not any(
        event["kind"] == "resolved_by_provider"
        for event in state["ownership_challenges"]["events"]
    )


def test_challenge_ledger_tamper_and_duplicate_resolution_fail_closed(
    repository: Path, tmp_path: Path
) -> None:
    target = track(repository, "tamper.txt", symlink=False)

    def produce(_cwd: Path, _prompt: bytes) -> None:
        target.unlink()

    state = make_dispatcher(
        repository, tmp_path, OwnershipRunner(hooks={2: produce})
    ).dispatch("OWNCHALLENGE-TAMPER", REQUEST, finalization_policy="commit-local")
    challenge_id = state["ownership_challenges"]["records"][0]["challenge_id"]

    tampered = deepcopy(state)
    tampered["ownership_challenges"]["records"][0]["path"] = "other.txt"
    with pytest.raises(result.ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        ownership_challenge.validate(repository, tampered)

    duplicate = [
        {"challenge_id": challenge_id, "decision": "phase_owned"},
        {"challenge_id": challenge_id, "decision": "phase_owned"},
    ]
    with pytest.raises(result.ResultError, match="OWNERSHIP_PROVIDER_RESOLUTION_INVALID"):
        ownership_challenge.validate_resolutions(duplicate)


def test_entry_dirt_overlap_is_an_exact_phase_owned_challenge(
    repository: Path, tmp_path: Path
) -> None:
    path = repository / "README.md"
    path.write_text("operator bytes\n", encoding="utf-8")

    def produce(_cwd: Path, _prompt: bytes) -> None:
        path.write_text("phase bytes\n", encoding="utf-8")

    runner = OwnershipRunner(hooks={2: produce}, challenge_decision="phase_owned")
    state = make_dispatcher(repository, tmp_path, runner).dispatch(
        "OWNCHALLENGE-ENTRY-DIRT", REQUEST, finalization_policy="commit-local"
    )

    record = state["ownership_challenges"]["records"][0]
    assert record["reason"] == "entry_dirt_overlap"
    assert record["entry_object"] != record["base_object"]
    assert record["current_object"] != record["entry_object"]
    assert state["ownership_challenges"]["events"] == []
    assert record["challenge_id"].encode() not in runner.calls[-1]["prompt"]
    assert state["finalization"]["repair_class"] == "requires_manager_ownership"
    assert state["commit"] is None
    assert git(repository, "show", "HEAD:README.md") != "phase bytes"
    assert path.read_text() == "phase bytes\n"
    with pytest.raises(result.ResultError, match="OWNERSHIP_PROVIDER_RESOLUTION_INVALID"):
        ownership_challenge.resolve_provider(repository, state, "closeout", record["raw_tree"],
            [{"challenge_id": record["challenge_id"], "decision": "phase_owned"}])
    # Even a forged presentation event cannot turn operator dirt into model authority.
    forged = deepcopy(state)
    forged["ownership_challenges"]["events"].append(
        {"challenge_id": record["challenge_id"], "kind": "shown", "stage": "closeout"})
    with pytest.raises(result.ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        ownership_challenge.validate(repository, forged)


def test_entry_dirt_overlap_without_exact_resolution_does_not_commit(
    repository: Path, tmp_path: Path
) -> None:
    path = repository / "README.md"
    path.write_text("operator bytes\n", encoding="utf-8")
    before = git(repository, "rev-parse", "HEAD")

    def produce(_cwd: Path, _prompt: bytes) -> None:
        path.write_text("phase bytes\n", encoding="utf-8")

    state = make_dispatcher(repository, tmp_path, OwnershipRunner(hooks={2: produce})).dispatch(
        "OWNCHALLENGE-ENTRY-DIRT-BLOCKED", REQUEST, finalization_policy="commit-local"
    )

    assert state["ownership_challenges"]["records"][0]["reason"] == "entry_dirt_overlap"
    assert state["finalization"]["repair_class"] == "requires_manager_ownership"
    assert state["commit"] is None
    assert git(repository, "rev-parse", "HEAD") == before
    challenge_id = state["ownership_challenges"]["records"][0]["challenge_id"]
    ownership_challenge.resolve_manager(
        repository, state, challenge_id, "phase_owned", "a" * 64
    )
    assert ownership_challenge.decisions(state) == {"README.md": "phase_owned"}


def test_entry_dirt_overlap_rejects_exclude_unrelated_resolution(
    repository: Path, tmp_path: Path
) -> None:
    path = repository / "README.md"
    path.write_text("operator bytes\n", encoding="utf-8")
    before = git(repository, "rev-parse", "HEAD")

    def produce(_cwd: Path, _prompt: bytes) -> None:
        path.write_text("phase bytes\n", encoding="utf-8")

    runner = OwnershipRunner(hooks={2: produce})
    state = make_dispatcher(repository, tmp_path, runner).dispatch(
        "OWNCHALLENGE-ENTRY-EXCLUDE", REQUEST, finalization_policy="commit-local")
    record = state["ownership_challenges"]["records"][0]
    with pytest.raises(result.ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        ownership_challenge.resolve_manager(repository, state, record["challenge_id"],
                                            "exclude_unrelated", "a" * 64)
    assert git(repository, "rev-parse", "HEAD") == before


def test_challenge_drift_supersedes_old_id_and_base_return_grants_no_ownership(
    repository: Path,
) -> None:
    path = track(repository, "drift.txt", symlink=False)
    entry = gitstate.capture_entry(repository)
    state = {
        "run_id": "OWNCHALLENGE-DRIFT",
        "project": "agent-central-test",
        "phase_id": "OWNCHALLENGE-DRIFT",
        "lifecycle": "standard",
        "controller_generation": "test-generation",
    }

    path.unlink()
    deleted_tree = candidate.tree_identity(repository)["tree"]
    ownership_challenge.observe(repository, state, entry, deleted_tree, "work", "post_producer")
    first_id = state["ownership_challenges"]["records"][0]["challenge_id"]

    path.write_text("entry bytes\n", encoding="utf-8")
    base_tree = candidate.tree_identity(repository)["tree"]
    assert base_tree == entry.tree
    ownership_challenge.observe(repository, state, entry, base_tree, "work", "post_terminal")
    assert state["mechanical_phase_owned_paths"] == []
    assert state["ownership_challenges"]["records"][0]["challenge_id"] == first_id
    assert state["ownership_challenges"]["events"][-1]["kind"] == "superseded"
    assert ownership_challenge.decisions(state) == {}

    path.unlink()
    deleted_again_tree = candidate.tree_identity(repository)["tree"]
    ownership_challenge.observe(
        repository, state, entry, deleted_again_tree, "work", "post_producer"
    )
    records = state["ownership_challenges"]["records"]
    assert len(records) == 2
    assert records[1]["challenge_id"] != first_id
    assert ownership_challenge.open_records(state)[0]["challenge_id"] == records[1]["challenge_id"]


@pytest.mark.parametrize("start_symlink,end_symlink", [(False, True), (True, False)])
def test_file_symlink_type_transitions_fail_closed(
    repository: Path, tmp_path: Path, start_symlink: bool, end_symlink: bool
) -> None:
    target = track(repository, "type-transition", symlink=start_symlink)
    before = git(repository, "rev-parse", "HEAD")

    def produce(_cwd: Path, _prompt: bytes) -> None:
        target.unlink()
        if end_symlink:
            target.symlink_to(".agents/skills")
        else:
            target.write_text("regular replacement\n", encoding="utf-8")

    runner = OwnershipRunner(hooks={2: produce})
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(
            "OWNCHALLENGE-TYPE", REQUEST, finalization_policy="commit-local"
        )

    assert caught.value.code == "OWNERSHIP_TYPE_CHANGE_UNSUPPORTED"
    assert git(repository, "rev-parse", "HEAD") == before


def test_executable_mode_change_is_classified_and_owned(
    repository: Path, tmp_path: Path
) -> None:
    target = track(repository, "mode-change", symlink=False)

    def produce(_cwd: Path, _prompt: bytes) -> None:
        target.chmod(0o755)

    state = make_dispatcher(repository, tmp_path, OwnershipRunner(hooks={2: produce})).dispatch(
        "OWNCHALLENGE-MODE", REQUEST, finalization_policy="commit-local"
    )

    assert state["ownership_challenges"]["records"] == []
    assert state["ownership_type_transitions"] == [
        {
            "path": "mode-change",
            "classification": "executable_mode_only",
            "before_mode": "100644",
            "after_mode": "100755",
        }
    ]
    assert state["commit"]
    assert git(repository, "ls-tree", "HEAD", "--", "mode-change").startswith("100755 ")


def test_regular_file_content_and_mode_change_is_ordinary_product_ownership(
    repository: Path, tmp_path: Path
) -> None:
    target = track(repository, "mode-and-content", symlink=False)

    def produce(_cwd: Path, _prompt: bytes) -> None:
        target.write_text("changed content\n", encoding="utf-8")
        target.chmod(0o755)

    state = make_dispatcher(repository, tmp_path, OwnershipRunner(hooks={2: produce})).dispatch(
        "OWNCHALLENGE-MODE-CONTENT", REQUEST, finalization_policy="commit-local"
    )

    assert state["ownership_challenges"]["records"] == []
    assert state["ownership_type_transitions"] == [{
        "path": "mode-and-content",
        "classification": "regular_file_mode_and_content",
        "before_mode": "100644",
        "after_mode": "100755",
    }]
    assert state["commit"]
    assert git(repository, "show", "HEAD:mode-and-content") == "changed content"
    assert git(repository, "ls-tree", "HEAD", "--", "mode-and-content").startswith("100755 ")


def test_symlink_ancestor_validation_remains_fail_closed(
    repository: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (repository / "alias").symlink_to(outside, target_is_directory=True)

    with pytest.raises(result.ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        ownership_challenge.validate_path(repository, "alias/escaped.txt")


def test_carried_deletion_requires_inherited_absence_evidence(
    repository: Path,
) -> None:
    path = track(repository, "carried.txt", symlink=False)
    entry = gitstate.capture_entry(repository)
    path.unlink()
    deleted_tree = candidate.tree_identity(repository)["tree"]
    present_manifest = gitstate.candidate_manifest(
        repository, entry.tree, entry.tree, paths=["carried.txt"]
    )
    absent_manifest = gitstate.candidate_manifest(
        repository, entry.tree, deleted_tree, paths=["carried.txt"]
    )

    present_state = {
        "run_id": "OWNCHALLENGE-CARRIED-PRESENT",
        "project": "agent-central-test",
        "phase_id": "OWNCHALLENGE-CARRIED-PRESENT",
        "lifecycle": "standard",
        "controller_generation": "test-generation",
        "adoption": {
            "adopted_paths": ["carried.txt"],
            "candidate_manifest": present_manifest,
        },
    }
    ownership_challenge.observe(
        repository, present_state, entry, deleted_tree, "work", "post_producer"
    )
    assert present_state["ownership_challenges"]["records"][0]["reason"] == (
        "unclaimed_tracked_deletion"
    )

    absent_state = {
        "run_id": "OWNCHALLENGE-CARRIED-ABSENT",
        "project": "agent-central-test",
        "phase_id": "OWNCHALLENGE-CARRIED-ABSENT",
        "lifecycle": "standard",
        "controller_generation": "test-generation",
        "adoption": {
            "adopted_paths": ["carried.txt"],
            "candidate_manifest": absent_manifest,
        },
    }
    ownership_challenge.observe(
        repository, absent_state, entry, deleted_tree, "work", "post_producer"
    )
    assert absent_state["ownership_challenges"]["records"] == []
    assert absent_state["mechanical_phase_owned_paths"] == ["carried.txt"]
