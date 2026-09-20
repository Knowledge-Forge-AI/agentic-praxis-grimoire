"""Regression tests for entry-candidate adoption (Cases 29-46)."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import time

import pytest

from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase import adoption
from agent_phase import entry_adoption
from agent_phase.entry_adoption import EntryAdoptionError
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest
from test_agent_phase_resume import ROOT, PHASE, git, repository as _repository, review

repository = _repository


REQUEST = PhaseRequest("implementation_testing", "codex_only", "Adopt entry candidate.")


def write_request_file(path: Path) -> Path:
    req_path = path / f"{PHASE}.json"
    req_path.write_text(json.dumps(REQUEST.as_dict()), encoding="utf-8")
    return req_path


def closeout_with_dispositions(
    prompt: bytes,
    *,
    dispositions: list[dict[str, str]],
    subject: str | None = "Closeout commit",
) -> bytes:
    nonce = re.search(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
    assert nonce is not None
    marker = nonce.group(1).decode()
    payload = json.dumps({
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "done",
        "path_dispositions": dispositions,
        "commit_message": {"subject": subject or "Adopted candidate commit", "body": ""} if subject else None,
    })
    return (
        f"<<<AGENT-PHASE-RESULT {marker}>>>\n{payload}\n"
        f"<<<END-AGENT-PHASE-RESULT {marker}>>>\n"
    ).encode()


class EntryAdoptionRunner:
    def __init__(
        self,
        repository: Path,
        *,
        adopted_paths: list[str],
        unadopted_paths: list[str] | None = None,
        work_mutates: bool = False,
        work_mutate_file: str | None = None,
        claim_unadopted: bool = False,
        mutate_unadopted: bool = False,
        subject: str | None = "Closeout candidate commit",
    ) -> None:
        self.repository = repository
        self.adopted_paths = adopted_paths
        self.unadopted_paths = unadopted_paths or []
        self.work_mutates = work_mutates
        self.work_mutate_file = work_mutate_file
        self.claim_unadopted = claim_unadopted
        self.mutate_unadopted = mutate_unadopted
        self.subject = subject
        self.calls: list[bytes] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        index = len(self.calls)
        self.calls.append(prompt)
        started = time.time()
        is_closeout = b"<<<AGENT-PHASE-RESULT " in prompt
        is_review = b"<<<AGENT-REVIEW-RESULT " in prompt

        if index == 2:  # work stage
            if self.work_mutates and self.work_mutate_file:
                target = self.repository / self.work_mutate_file
                target.write_text("work stage modification\n")
            if self.mutate_unadopted and self.unadopted_paths:
                target = self.repository / self.unadopted_paths[0]
                target.write_text("tampered unadopted dirt\n")
            stdout = json.dumps({
                "outcome": "completed",
                "body": "reviewed and verified pre-existing candidate",
            }).encode()
            return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)

        if is_closeout:
            dispositions = [{"path": p, "disposition": "phase_owned"} for p in self.adopted_paths]
            if self.claim_unadopted and self.unadopted_paths:
                dispositions.append({"path": self.unadopted_paths[0], "disposition": "phase_owned"})
            stdout = closeout_with_dispositions(prompt, dispositions=dispositions, subject=self.subject)
            return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)

        if is_review:
            stdout = review(prompt, "reviewed_with_no_findings")
            return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)

        stdout = f"output {index}".encode()
        return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)


# ==============================================================================
# Positive Cases: Creation, CLI, Dispatch, Finalization, Dirt Preservation
# ==============================================================================

def test_entry_adoption_creation_positive(repository: Path, tmp_path: Path):
    # Case 29: Receipt creation produces schema, synthetic candidate tree, and manifest
    candidate_file = repository / "candidate.txt"
    candidate_file.write_text("candidate modifications\n")
    req_file = write_request_file(tmp_path)

    receipt = entry_adoption.create(
        req_file,
        repository,
        ["candidate.txt"],
        reason="pre-existing reviewed candidate",
    )

    assert receipt["schema"] == "agent-phase-entry-adoption-v1"
    assert receipt["source_kind"] == "entry_worktree"
    assert receipt["adopted_paths"] == ["candidate.txt"]
    assert "candidate_tree" in receipt
    assert "candidate_manifest" in receipt
    assert "candidate.txt" in receipt["candidate_manifest"]["paths"]
    assert receipt["unadopted_dirty_paths"] == []

    validated = entry_adoption.validate_entry(repository, receipt, request_path=req_file)
    assert validated["schema"] == receipt["schema"]


def test_entry_adoption_cli_adopt_entry(repository: Path, tmp_path: Path):
    # Case 30: CLI subcommand agent-phase-adopt-entry
    candidate_file = repository / "candidate.txt"
    candidate_file.write_text("candidate modifications\n")
    req_file = write_request_file(tmp_path)
    receipt_file = tmp_path / "adoption.json"

    res = subprocess.run(
        [
            str(ROOT / "bin/agent-phase-adopt-entry"),
            "--request",
            str(req_file),
            "--path",
            "candidate.txt",
            "--reason",
            "operator reviewed candidate",
            "--output",
            str(receipt_file),
        ],
        cwd=repository,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    assert receipt_file.exists()
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert data["schema"] == "agent-phase-entry-adoption-v1"
    assert data["adopted_paths"] == ["candidate.txt"]


def test_entry_adoption_work_stage_review_publish_no_path_disposition_invalid(
    repository: Path, tmp_path: Path
):
    # Cases 31, 32: Candidate adopted, work stage reviews without mutating, closer phase_owned,
    # publishes cleanly without PATH_DISPOSITION_INVALID, unadopted dirt excluded.
    candidate_file = repository / "candidate.txt"
    candidate_file.write_text("pre-existing candidate content\n")

    unadopted_file = repository / "unrelated_dirt.txt"
    unadopted_file.write_text("unrelated operator dirt\n")

    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file,
        repository,
        ["candidate.txt"],
        reason="operator adoption",
    )
    assert receipt["unadopted_dirty_paths"] == ["unrelated_dirt.txt"]
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryAdoptionRunner(
        repository,
        adopted_paths=["candidate.txt"],
        unadopted_paths=["unrelated_dirt.txt"],
    )
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    state = d.dispatch(
        PHASE,
        REQUEST,
        entry_adoption=receipt_file,
        finalization_policy="publish",
    )

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert "candidate.txt" in state["phase_owned_paths"]
    assert "unrelated_dirt.txt" not in state["phase_owned_paths"]
    assert state["push"]["status"] == "succeeded"

    # Verify unadopted dirt remained untouched in worktree
    assert unadopted_file.read_text() == "unrelated operator dirt\n"

    # Verify published commit contains candidate.txt but NOT unrelated_dirt.txt
    branch = git(repository, "branch", "--show-current").strip()
    remote = tmp_path / "remote.git"
    remote_head = git(remote, "rev-parse", branch)
    tree = git(remote, "rev-parse", f"{remote_head}^{{tree}}")
    ls = git(remote, "ls-tree", "-r", "--name-only", tree)
    assert "candidate.txt" in ls.splitlines()
    assert "unrelated_dirt.txt" not in ls.splitlines()


def test_entry_adoption_multiple_paths(repository: Path, tmp_path: Path):
    # Case 33: Multiple adopted paths
    (repository / "f1.txt").write_text("file 1\n")
    (repository / "f2.txt").write_text("file 2\n")

    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file,
        repository,
        ["f1.txt", "f2.txt"],
        reason="adoption of two files",
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    runner = EntryAdoptionRunner(
        repository,
        adopted_paths=["f1.txt", "f2.txt"],
    )
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )
    state = d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file, finalization_policy="publish")
    assert state["complete"] is True
    assert set(state["phase_owned_paths"]) == {"f1.txt", "f2.txt"}


def test_entry_adoption_checkpoint_policy(repository: Path, tmp_path: Path):
    # Case 34: Checkpoint policy preserves candidate
    (repository / "candidate.txt").write_text("candidate text\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="test checkpoint"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    runner = EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"])
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )
    state = d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file, finalization_policy="checkpoint")
    assert state["checkpoint_candidate"] is not None
    assert state["push"]["status"] == "not_attempted_by_policy"


def test_entry_adoption_commit_local_policy(repository: Path, tmp_path: Path):
    # Case 35: Commit-local policy creates local commit without push
    (repository / "candidate.txt").write_text("candidate text\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="test commit local"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    runner = EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"])
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )
    state = d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file, finalization_policy="commit-local")
    assert state["complete"] is True
    assert state["commit"] is not None
    assert state["push"]["status"] == "not_attempted_by_policy"


def test_entry_adoption_dry_run_validation(repository: Path, tmp_path: Path):
    # Case 36: Dry-run validates entry adoption receipt
    (repository / "candidate.txt").write_text("candidate text\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="dry run test"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    runner = EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"])
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )
    preview = d.dry_run(PHASE, REQUEST, entry_adoption=receipt_file)
    assert preview["entry_adoption"]["schema"] == "agent-phase-entry-adoption-v1"
    assert preview["entry_adoption"]["adopted_paths"] == ["candidate.txt"]


# ==============================================================================
# Mutual Exclusivity and Negative Cases
# ==============================================================================

def test_entry_adoption_and_continue_from_mutually_exclusive(repository: Path, tmp_path: Path):
    # Case 37: --continue-from and --entry-adoption mutually exclusive
    write_request_file(tmp_path)
    dummy_continue = tmp_path / "continue_run"
    dummy_adoption = tmp_path / "adoption.json"
    dummy_adoption.write_text("{}")

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=[]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(
            PHASE,
            REQUEST,
            continue_from=dummy_continue,
            entry_adoption=dummy_adoption,
        )
    assert exc_info.value.code == "MUTUALLY_EXCLUSIVE_OPTIONS"


def test_entry_adoption_and_native_git_authority_mutually_exclusive(repository: Path, tmp_path: Path):
    # Case 38: --native-git-authority and --entry-adoption mutually exclusive
    write_request_file(tmp_path)
    dummy_auth = tmp_path / "native.json"
    dummy_auth.write_text("{}")
    dummy_adoption = tmp_path / "adoption.json"
    dummy_adoption.write_text("{}")

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=[]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(
            PHASE,
            REQUEST,
            native_git_authority=dummy_auth,
            entry_adoption=dummy_adoption,
        )
    assert exc_info.value.code == "MUTUALLY_EXCLUSIVE_OPTIONS"


def test_staged_changes_rejected_at_receipt_creation(repository: Path, tmp_path: Path):
    # Case 39: Pre-existing staged changes rejected at receipt creation
    (repository / "staged.txt").write_text("staged content\n")
    git(repository, "add", "staged.txt")
    req_file = write_request_file(tmp_path)

    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.create(
            req_file,
            repository,
            ["staged.txt"],
            reason="trying to adopt staged",
        )
    assert exc_info.value.code == "ENTRY_STAGED_CHANGES"


def test_staged_changes_rejected_at_dispatch_entry(repository: Path, tmp_path: Path):
    # Case 40: Worktree clean when receipt made, but staged before dispatch starts
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    # Stage a file after receipt creation
    (repository / "new_staged.txt").write_text("staged after\n")
    git(repository, "add", "new_staged.txt")

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_STAGED_CHANGES"


def test_worktree_drift_rejected(repository: Path, tmp_path: Path):
    # Case 41: Worktree file modified after receipt creation
    (repository / "candidate.txt").write_text("original candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    # Tamper with file
    (repository / "candidate.txt").write_text("drifted candidate bytes\n")

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"


def test_adopted_path_missing_rejected(repository: Path, tmp_path: Path):
    # Case 42: Adopted path deleted before dispatch starts
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    (repository / "candidate.txt").unlink()

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_PATH_MISSING"


def test_modified_unadopted_dirt_refused(repository: Path, tmp_path: Path):
    # Case 43: Unadopted dirt modified during lifecycle is refused
    (repository / "candidate.txt").write_text("candidate\n")
    (repository / "dirt.txt").write_text("clean dirt\n")

    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    # Runner tampers with dirt.txt during work stage
    runner = EntryAdoptionRunner(
        repository,
        adopted_paths=["candidate.txt"],
        unadopted_paths=["dirt.txt"],
        mutate_unadopted=True,
    )
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )
    with pytest.raises(adoption.AdoptionError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ADOPTION_INVALID"


def test_provider_claims_unadopted_dirt_refused(repository: Path, tmp_path: Path):
    # Case 44: Closer tries to claim unadopted dirt as phase_owned
    (repository / "candidate.txt").write_text("candidate\n")
    (repository / "dirt.txt").write_text("clean dirt\n")

    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    runner = EntryAdoptionRunner(
        repository,
        adopted_paths=["candidate.txt"],
        unadopted_paths=["dirt.txt"],
        claim_unadopted=True,
    )
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "PATH_DISPOSITION_INVALID"


def test_tree_or_head_mismatch_refused(repository: Path, tmp_path: Path):
    # Case 45: Head advanced after receipt creation
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    # Advance HEAD
    (repository / "other.txt").write_text("other\n")
    git(repository, "add", "other.txt")
    git(repository, "commit", "-m", "advance HEAD")

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_INVALID"


def test_branch_mismatch_refused(repository: Path, tmp_path: Path):
    # Case 46: Switched branch after receipt creation
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    git(repository, "checkout", "-b", "other-branch")

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_INVALID"


def test_entry_adoption_cross_repo_or_request_refused(repository: Path, tmp_path: Path):
    # Case 39: Cross-repo or cross-request entry adoption receipt is rejected
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"

    # Cross-request
    other_req = PhaseRequest("implementation_testing", "codex_only", "Different request.")
    other_req_file = tmp_path / "other_req.json"
    other_req_file.write_text(json.dumps(other_req.as_dict()))
    other_receipt = entry_adoption.create(
        other_req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file.write_text(json.dumps(other_receipt))
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_INVALID"

    # Cross-repo
    other_repo = tmp_path / "other_repo"
    other_repo.mkdir()
    git(other_repo, "init", "-b", "main")
    git(other_repo, "commit", "--allow-empty", "-m", "init")
    (other_repo / "candidate.txt").write_text("candidate\n")
    repo_receipt = entry_adoption.create(
        req_file, other_repo, ["candidate.txt"], reason="valid"
    )
    receipt_file.write_text(json.dumps(repo_receipt))
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_INVALID"


def test_entry_adoption_receipt_tamper_refused(repository: Path, tmp_path: Path):
    # Case 41: Tampered entry receipt fails closed
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    tampered = dict(receipt)
    tampered["candidate_tree"] = "0" * 40
    receipt_file = tmp_path / "tampered.json"
    receipt_file.write_text(json.dumps(tampered))

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_INVALID"


def test_entry_adoption_cannot_replay_as_continue_from(repository: Path, tmp_path: Path):
    # Case 45: Entry adoption receipt cannot be passed to --continue-from
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt))

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryAdoptionRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(adoption.AdoptionError) as exc_info:
        d.dispatch(PHASE, REQUEST, continue_from=receipt_file)
    assert exc_info.value.code == "ADOPTION_INVALID"
