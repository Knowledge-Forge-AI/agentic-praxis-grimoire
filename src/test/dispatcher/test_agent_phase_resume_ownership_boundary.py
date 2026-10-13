"""Ownership after a resumed entry must use one boundary per observation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_phase import ownership_challenge, ownership_cli
from agent_phase.dispatch import DispatchError
from agent_phase.finalization_recovery import recover
from interrupted_run_fixtures import (
    PHASE_ID,
    REQUEST,
    DispositionFakeRunner,
    interrupted_source,
    make_dispatcher,
)
from test_agent_phase_disposition_flow import git, repository as _repository

repository = _repository
RESIDUE = ownership_challenge.RESIDUE


def commit_files(root: Path, **files: str) -> None:
    for name, text in files.items():
        (root / name).write_text(text)
    git(root, "add", "--", *files)
    git(root, "commit", "-qm", "Track fixture files")


def zd_interruption(cwd: Path) -> None:
    """The observed ZD shape: tracked edits and new untracked files."""
    (cwd / "tracked.txt").write_text("interrupted tracked edit\n")
    (cwd / "untouched-tracked.txt").write_text("interrupted edit left alone\n")
    (cwd / "new-untracked.txt").write_text("interrupted new file left alone\n")
    (cwd / "new-untracked-2.txt").write_text("interrupted new file\n")


def resumed_work(cwd: Path, _prompt: bytes) -> None:
    (cwd / "resumed-new.txt").write_text("resumed attempt product\n")
    (cwd / "tracked.txt").write_text("resumed attempt finished tracked edit\n")
    (cwd / "new-untracked-2.txt").write_text("resumed attempt finished new file\n")


@pytest.fixture
def zd_repository(repository: Path) -> Path:
    commit_files(repository, **{
        "tracked.txt": "entry tracked\n",
        "untouched-tracked.txt": "entry untouched\n",
        "operator-tracked.txt": "entry operator\n",
    })
    # Real operator dirt that predates the original dispatch.
    (repository / "operator-tracked.txt").write_text("operator edit before dispatch\n")
    (repository / "operator-notes.txt").write_text("operator notes before dispatch\n")
    return repository


def resume_zd(repository: Path, tmp_path: Path, runner=None) -> tuple[Path, dict, DispositionFakeRunner]:
    source = interrupted_source(repository, tmp_path, zd_interruption)
    runner = runner or DispositionFakeRunner(hooks={0: resumed_work})
    state = make_dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    return source, state, runner


def records_by_path(state: dict) -> dict[str, dict]:
    ledger = state.get("ownership_challenges") or {"records": []}
    active = ownership_challenge.statuses(state)
    return {r["path"]: r for r in ledger["records"] if active[r["challenge_id"]] == "open"}


def test_zd_pattern_produces_valid_residue_challenges_not_invalid_overlap(zd_repository, tmp_path):
    repository = zd_repository
    _source, state, runner = resume_zd(repository, tmp_path)

    assert (state.get("blocking_reason") or {}).get("code") != "OWNERSHIP_CHALLENGE_INVALID"
    assert state["semantic_outcome"] == "completed"
    assert state["completion_kind"] == "candidate_requires_manager_disposition"
    assert state["push"]["failure"]["code"] == "OWNERSHIP_CHALLENGE_OPEN"
    ownership_challenge.validate(repository, state)
    records = records_by_path(state)
    residue = {"tracked.txt", "untouched-tracked.txt", "new-untracked.txt", "new-untracked-2.txt"}
    assert set(records) == residue
    assert state["resume"]["resume_boundary"]["interrupted_residue_paths"] == sorted(residue)
    for path, record in records.items():
        context = record["ownership_context"]["resume"]
        assert record["reason"] == RESIDUE
        assert record["allowed_decisions"] == ["phase_owned", "exclude_unrelated"]
        assert record["entry_tree"] == state["resume"]["source_entry_tree"]
        assert record["base_head"] == state["resume"]["source_entry_head"]
        assert context["resume_entry_tree"] == state["entry"]["tree"]
        assert context["resume_entry_object"] != record["entry_object"]
        assert context["source_entry_dirty"] is False
    # The exact observed defect: a pre-interruption untracked file is absent at
    # the source entry yet present at the resumed entry.
    untracked = records["new-untracked-2.txt"]
    assert untracked["entry_object"]["present"] is False
    assert untracked["ownership_context"]["resume"]["resume_entry_object"]["present"] is True
    assert untracked["current_object"] != untracked["ownership_context"]["resume"]["resume_entry_object"]
    # Residue is manager-only: never shown to, or resolvable by, a provider.
    shown = {e["challenge_id"] for e in state["ownership_challenges"]["events"] if e["kind"] == "shown"}
    assert not shown & {r["challenge_id"] for r in records.values()}
    closeout_prompt = runner.calls[-1]["prompt"]
    assert not any(r["challenge_id"].encode() in closeout_prompt for r in records.values())
    # Operator dirt that predates the original dispatch stays operator dirt.
    assert "resumed-new.txt" in state["phase_owned_paths"]
    for path in ("operator-tracked.txt", "operator-notes.txt", *residue):
        assert path not in state["phase_owned_paths"]
        assert path not in state["mechanical_phase_owned_paths"]
    assert "operator-tracked.txt" not in records and "operator-notes.txt" not in records
    assert not state.get("entry_dirt_overlap")


def test_zd_manager_lane_finalizes_exact_resolved_boundary(zd_repository, tmp_path):
    repository = zd_repository
    _source, state, _runner = resume_zd(repository, tmp_path)
    resumed = Path(state["run_directory"])
    decisions = {
        "tracked.txt": "phase_owned",
        "new-untracked-2.txt": "phase_owned",
        "untouched-tracked.txt": "exclude_unrelated",
        "new-untracked.txt": "exclude_unrelated",
    }
    receipts = []
    outside = tmp_path / "receipts"
    outside.mkdir()
    for path, record in sorted(records_by_path(state).items()):
        receipt = ownership_cli.create(
            resumed, repository, record["challenge_id"], decisions[path], f"Manager decides {path}")
        output = outside / f"{path}.json"
        ownership_cli._write_create_only(output, receipt)
        receipts.append(output)

    receipt = recover(resumed, repository, policy="commit-local",
                      authorize_policy_upgrade=True, ownership_resolutions=receipts)

    assert receipt["finalization"]["outcome"] == "completed"
    committed = set(git(repository, "show", "--name-only", "--format=", "HEAD").splitlines())
    assert committed == {"resumed-new.txt", "tracked.txt", "new-untracked-2.txt"}
    assert git(repository, "show", "HEAD:untouched-tracked.txt") == "entry untouched"
    assert git(repository, "show", "HEAD:operator-tracked.txt") == "entry operator"
    assert (repository / "untouched-tracked.txt").read_text() == "interrupted edit left alone\n"
    assert (repository / "new-untracked.txt").read_text() == "interrupted new file left alone\n"
    assert (repository / "operator-tracked.txt").read_text() == "operator edit before dispatch\n"
    assert (repository / "operator-notes.txt").read_text() == "operator notes before dispatch\n"
    status = {line.strip() for line in git(repository, "status", "--porcelain").splitlines()}
    assert status == {
        "M untouched-tracked.txt", "M operator-tracked.txt",
        "?? new-untracked.txt", "?? operator-notes.txt",
    }


def test_open_residue_blocks_manager_lane_without_receipts(zd_repository, tmp_path):
    repository = zd_repository
    _source, state, _runner = resume_zd(repository, tmp_path)
    head = git(repository, "rev-parse", "HEAD")

    from agent_phase.finalization_proof import RecoveryError

    with pytest.raises(RecoveryError):
        recover(Path(state["run_directory"]), repository, policy="commit-local",
                authorize_policy_upgrade=True, ownership_resolutions=[])
    assert git(repository, "rev-parse", "HEAD") == head


def test_operator_edit_to_interrupted_path_is_challenged_not_claimed(zd_repository, tmp_path):
    repository = zd_repository
    source = interrupted_source(repository, tmp_path, zd_interruption)
    (repository / "untouched-tracked.txt").write_text("operator changed it during the outage\n")

    state = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner(
        hooks={0: resumed_work})).resume(PHASE_ID, REQUEST, source, finalization_policy="checkpoint")

    record = records_by_path(state)["untouched-tracked.txt"]
    assert record["reason"] == RESIDUE
    assert record["ownership_context"]["resume"]["resume_entry_object"] == record["current_object"]
    assert "untouched-tracked.txt" not in state["phase_owned_paths"]
    assert (repository / "untouched-tracked.txt").read_text() == "operator changed it during the outage\n"


def closed_work(cwd: Path, _prompt: bytes) -> None:
    (cwd / "phase.txt").write_text("closed work candidate\n")


def test_operator_edit_to_closed_candidate_path_refuses_before_provider(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, lambda cwd: None, at=3,
                                before={2: closed_work})
    (repository / "phase.txt").write_text("operator edit during outage\n")
    runner = DispositionFakeRunner()

    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path / "conflict", runner).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")

    assert caught.value.code == "RESUME_CANDIDATE_CONFLICT"
    assert runner.calls == []
    assert (repository / "phase.txt").read_text() == "operator edit during outage\n"


def test_interrupted_read_only_stage_has_no_residue(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, lambda cwd: None, at=3,
                                before={2: closed_work})
    (repository / "operator-late.txt").write_text("operator dirt during a review outage\n")
    runner = DispositionFakeRunner()

    state = make_dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")

    assert len(runner.calls) == 2
    boundary = state["resume"]["resume_boundary"]
    assert boundary["interrupted_stage"] == "final_review"
    assert boundary["interrupted_residue_paths"] == []
    assert "operator-late.txt" in boundary["unrelated_paths"]
    assert "operator-late.txt" not in records_by_path(state)
    assert "operator-late.txt" not in state["phase_owned_paths"]
    assert state["completion_kind"] == "checkpoint_ready"
    assert "phase.txt" in state["phase_owned_paths"]


def test_interrupted_phase_modification_resumes_to_resolvable_challenge(repository, tmp_path):
    def edit(cwd: Path) -> None:
        (cwd / "README.md").write_text("# interrupted phase edit\n")

    source = interrupted_source(repository, tmp_path, edit)
    state = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner()).resume(
        PHASE_ID, REQUEST, source, finalization_policy="checkpoint")

    record = records_by_path(state)["README.md"]
    assert record["reason"] == RESIDUE and record["status"] == "M"
    receipt = ownership_cli.create(Path(state["run_directory"]), repository,
                                   record["challenge_id"], "phase_owned", "phase wrote it")
    assert receipt["decision"] == "phase_owned"


def test_ordinary_resume_overlap_uses_resumed_entry_boundary(repository, tmp_path):
    """Dirt that appeared after a failed source and is then touched is valid."""
    source_runner = DispositionFakeRunner(hooks={4: lambda cwd, prompt: (_ for _ in ()).throw(
        RuntimeError("closeout transport failed"))})
    with pytest.raises((DispatchError, RuntimeError)):
        make_dispatcher(repository, tmp_path / "source", source_runner).dispatch(
            PHASE_ID, REQUEST, finalization_policy="checkpoint")
    from interrupted_run_fixtures import only_run

    source = only_run(tmp_path / "source" / "runs")
    assert (source / "result.json").exists()
    (repository / "late-operator.txt").write_text("operator bytes after the failed source\n")

    def touch(cwd: Path, _prompt: bytes) -> None:
        (cwd / "late-operator.txt").write_text("closeout overwrote operator bytes\n")

    state = make_dispatcher(repository, tmp_path / "resumed", DispositionFakeRunner(
        hooks={0: touch})).resume(PHASE_ID, REQUEST, source, "closeout",
                                  finalization_policy="checkpoint")

    assert (state.get("blocking_reason") or {}).get("code") != "OWNERSHIP_CHALLENGE_INVALID"
    record = records_by_path(state)["late-operator.txt"]
    assert record["reason"] == "entry_dirt_overlap"
    assert record["entry_tree"] == state["entry"]["tree"]
    assert record["base_head"] == state["entry"]["head"]
    assert record["entry_object"] != record["base_object"]
    assert "resume" not in record["ownership_context"]
    ownership_challenge.validate(repository, state)


def test_residue_record_validation_rejects_cross_boundary_evidence(zd_repository, tmp_path):
    repository = zd_repository
    _source, state, _runner = resume_zd(repository, tmp_path)
    record = dict(records_by_path(state)["new-untracked.txt"])
    context = json.loads(json.dumps(record["ownership_context"]))
    context["resume"]["resume_entry_object"] = record["entry_object"]
    forged = {**record, "ownership_context": context}
    forged["challenge_id"] = "ownch1-" + ownership_challenge.digest(
        {k: v for k, v in forged.items() if k != "challenge_id"})

    from agent_phase.result import ResultError

    with pytest.raises(ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        ownership_challenge.validate_record(repository, forged)
    stripped = {**record, "ownership_context": {k: v for k, v in record["ownership_context"].items()
                                                if k != "resume"}}
    stripped["challenge_id"] = "ownch1-" + ownership_challenge.digest(
        {k: v for k, v in stripped.items() if k != "challenge_id"})
    with pytest.raises(ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        ownership_challenge.validate_record(repository, stripped)
