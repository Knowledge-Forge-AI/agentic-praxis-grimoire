"""Regression tests for entry-candidate adoption boundary (strict vs retained validation)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from copy import deepcopy
from pathlib import Path

import pytest
from agent_phase import adoption, candidate, entry_adoption
from agent_phase.dispatch import Dispatcher, DispatchError
from agent_phase.entry_adoption import EntryAdoptionError
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest
from test_agent_phase_resume import PHASE, ROOT, git, repository, review

__all__ = ["repository"]


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
        "commit_message": (
            {"subject": subject or "Adopted candidate commit", "body": ""} if subject else None
        ),
    })
    return f"<<<AGENT-PHASE-RESULT {marker}>>>\n{payload}\n<<<END-AGENT-PHASE-RESULT {marker}>>>\n".encode()


class EntryBoundaryRunner:
    def __init__(
        self,
        repository: Path,
        *,
        adopted_paths: list[str],
        unadopted_paths: list[str] | None = None,
        work_mutates: bool = False,
        work_mutate_file: str | None = None,
        work_mutate_content: str = "work stage modification\n",
        terminal_mutates: bool = False,
        terminal_mutate_file: str | None = None,
        terminal_mutate_content: str = "terminal stage modification\n",
        review_mutates: bool = False,
        review_mutate_file: str | None = None,
        unauthorized_commit: bool = False,
        claim_unadopted: bool = False,
        mutate_unadopted: bool = False,
        subject: str | None = "Closeout candidate commit",
    ) -> None:
        self.repository = repository
        self.adopted_paths = adopted_paths
        self.unadopted_paths = unadopted_paths or []
        self.work_mutates = work_mutates
        self.work_mutate_file = work_mutate_file
        self.work_mutate_content = work_mutate_content
        self.terminal_mutates = terminal_mutates
        self.terminal_mutate_file = terminal_mutate_file
        self.terminal_mutate_content = terminal_mutate_content
        self.review_mutates = review_mutates
        self.review_mutate_file = review_mutate_file
        self.unauthorized_commit = unauthorized_commit
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

        if is_review:
            if self.review_mutates and self.review_mutate_file:
                target = self.repository / self.review_mutate_file
                target.write_text("reviewer illegal mutation\n")
            stdout = review(prompt, "reviewed_with_no_findings")
            return Result(
                exit_code=0,
                stdout=stdout,
                stderr=b"",
                truncated=False,
                started=started,
                ended=started,
            )

        if is_closeout:
            if self.terminal_mutates and self.terminal_mutate_file:
                target = self.repository / self.terminal_mutate_file
                target.write_text(self.terminal_mutate_content)
            dispositions = [
                {"path": p, "disposition": "phase_owned"} for p in self.adopted_paths
            ]
            if self.claim_unadopted and self.unadopted_paths:
                dispositions.append(
                    {"path": self.unadopted_paths[0], "disposition": "phase_owned"}
                )
            stdout = closeout_with_dispositions(
                prompt, dispositions=dispositions, subject=self.subject
            )
            return Result(
                exit_code=0,
                stdout=stdout,
                stderr=b"",
                truncated=False,
                started=started,
                ended=started,
            )

        if index == 2:  # work stage in standard lifecycle
            if self.work_mutates and self.work_mutate_file:
                target = self.repository / self.work_mutate_file
                target.write_text(self.work_mutate_content)
            if self.mutate_unadopted and self.unadopted_paths:
                target = self.repository / self.unadopted_paths[0]
                target.write_text("tampered unadopted dirt\n")
            if self.unauthorized_commit:
                (self.repository / "rogue.txt").write_text("rogue commit\n")
                subprocess.run(
                    ["git", "add", "rogue.txt"], cwd=self.repository, check=True
                )
                subprocess.run(
                    ["git", "commit", "-m", "unauthorized commit"],
                    cwd=self.repository,
                    check=True,
                )
            stdout = json.dumps({
                "outcome": "completed",
                "body": "work stage output",
            }).encode()
            return Result(
                exit_code=0,
                stdout=stdout,
                stderr=b"",
                truncated=False,
                started=started,
                ended=started,
            )

        stdout = f"output {index}".encode()
        return Result(
            exit_code=0,
            stdout=stdout,
            stderr=b"",
            truncated=False,
            started=started,
            ended=started,
        )


def test_receipt_creation_and_strict_entry_validation_succeeds(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("initial candidate\n")
    req_file = write_request_file(tmp_path)

    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="reviewed pre-existing candidate"
    )
    assert receipt["schema"] == "agent-phase-entry-adoption-v1"
    assert receipt["source_kind"] == "entry_worktree"
    assert receipt["adopted_paths"] == ["candidate.txt"]

    validated = entry_adoption.validate_entry(
        repository, receipt, request_path=req_file
    )
    assert validated["sha256"] == receipt["sha256"]

    strict_val = entry_adoption.validate_strict_entry(
        repository, receipt, request_path=req_file
    )
    assert strict_val["sha256"] == receipt["sha256"]

    strict_no_args = entry_adoption.validate_entry(repository, receipt)
    assert strict_no_args["sha256"] == receipt["sha256"]


def test_adopted_bytes_drift_before_dispatch_fails(repository: Path, tmp_path: Path):
    (repository / "candidate.txt").write_text("original candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    (repository / "candidate.txt").write_text("tampered bytes before dispatch\n")

    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_strict_entry(repository, receipt, request_path=req_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"

    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_entry(repository, receipt)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=EntryBoundaryRunner(repository, adopted_paths=["candidate.txt"]),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"


def test_strict_entry_validation_bindings_and_exactness(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("original candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    orig_access = os.access
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            os, "access",
            lambda p, m, *a, **k: True if m == os.X_OK and Path(p) == target else orig_access(p, m, *a, **k),
        )
        with pytest.raises(EntryAdoptionError) as exc_info:
            entry_adoption.validate_strict_entry(repository, receipt, request_path=req_file)
        assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"
        with pytest.raises(EntryAdoptionError) as exc_info:
            entry_adoption.validate_entry(repository, receipt)
        assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"

    target.write_text("changed bytes\n")
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_strict_entry(repository, receipt, request_path=req_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_entry(repository, receipt)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"
    target.write_text("original candidate\n")

    target.unlink()
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_strict_entry(repository, receipt, request_path=req_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_PATH_MISSING"
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_entry(repository, receipt)
    assert exc_info.value.code == "ENTRY_ADOPTION_PATH_MISSING"
    target.write_text("original candidate\n")

    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_strict_entry(repository, receipt, phase_id="wrong_phase_id")
    assert exc_info.value.code == "ENTRY_ADOPTION_INVALID"

    wrong_req = PhaseRequest("implementation_testing", "codex_only", "Different prompt")
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_strict_entry(repository, receipt, request=wrong_req)
    assert exc_info.value.code == "ENTRY_ADOPTION_INVALID"


def test_retained_validation_accepts_adopted_content_revision(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("original candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    entry_adoption.validate_strict_entry(repository, receipt, request_path=req_file)

    target.write_text("legitimate work stage modification\n")

    validated = entry_adoption.validate_retained_entry(repository, receipt)
    assert validated["sha256"] == receipt["sha256"]

    # Strict validate_entry without arguments MUST fail on live drift
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_entry(repository, receipt)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"


def test_retained_validation_accepts_adopted_mode_revision(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("original candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    assert receipt["path_metadata"]["candidate.txt"]["mode"] == "100644"

    orig_access = os.access
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            os, "access",
            lambda p, m, *a, **k: True if m == os.X_OK and Path(p) == target else orig_access(p, m, *a, **k),
        )
        validated = entry_adoption.validate_retained_entry(repository, receipt)
        assert validated["sha256"] == receipt["sha256"]
        with pytest.raises(EntryAdoptionError) as exc_info:
            entry_adoption.validate_entry(repository, receipt)
        assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"


def test_retained_validation_accepts_adopted_deletion_and_type_change_unit(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("original candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    # Deletion: validate_retained_entry does not require live file existence
    target.unlink()
    validated = entry_adoption.validate_retained_entry(repository, receipt)
    assert validated["sha256"] == receipt["sha256"]

    # But strict entry validation catches missing path
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_strict_entry(repository, receipt, request_path=req_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_PATH_MISSING"

    # Also validate_entry without arguments catches missing path
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_entry(repository, receipt)
    assert exc_info.value.code == "ENTRY_ADOPTION_PATH_MISSING"

    # Type change: file replaced with symlink
    target.symlink_to("dummy_target.txt")
    validated_symlink = entry_adoption.validate_retained_entry(repository, receipt)
    assert validated_symlink["sha256"] == receipt["sha256"]

    # But strict entry validation catches drift
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_strict_entry(repository, receipt, request_path=req_file)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"

    # Also validate_entry without arguments catches drift
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_entry(repository, receipt)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"


def test_retained_validation_does_not_mutate_receipt_or_checksum(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("original candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )
    original_copy = deepcopy(receipt)
    original_sha = receipt["sha256"]

    target.write_text("mutated by provider\n")
    entry_adoption.validate_retained_entry(repository, receipt)

    assert receipt == original_copy
    assert receipt["sha256"] == original_sha
    assert receipt["path_metadata"] == original_copy["path_metadata"]
    assert receipt["candidate_tree"] == original_copy["candidate_tree"]


def test_retained_validation_rejects_receipt_tamper(repository: Path, tmp_path: Path):
    (repository / "candidate.txt").write_text("original candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    bad_sha = deepcopy(receipt)
    bad_sha["sha256"] = "0" * 64
    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(repository, bad_sha)
    assert exc.value.code == "ENTRY_ADOPTION_INVALID"

    bad_schema = deepcopy(receipt)
    bad_schema["schema"] = "invalid-schema-v2"
    bad_schema["sha256"] = entry_adoption.digest(
        {k: v for k, v in bad_schema.items() if k != "sha256"}
    )
    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(repository, bad_schema)
    assert exc.value.code == "ENTRY_ADOPTION_INVALID"

    bad_kind = deepcopy(receipt)
    bad_kind["source_kind"] = "invalid_kind"
    bad_kind["sha256"] = entry_adoption.digest(
        {k: v for k, v in bad_kind.items() if k != "sha256"}
    )
    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(repository, bad_kind)
    assert exc.value.code == "ENTRY_ADOPTION_INVALID"

    missing_field = deepcopy(receipt)
    del missing_field["reason"]
    missing_field["sha256"] = entry_adoption.digest(missing_field)
    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(repository, missing_field)
    assert exc.value.code == "ENTRY_ADOPTION_INVALID"


def test_retained_validation_rejects_repository_identity_mismatch(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    bad_repo = deepcopy(receipt)
    bad_repo["repository"]["inode"] = 999999999
    bad_repo["sha256"] = entry_adoption.digest(
        {k: v for k, v in bad_repo.items() if k != "sha256"}
    )
    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(repository, bad_repo)
    assert exc.value.code == "ENTRY_ADOPTION_INVALID"

    other_repo = tmp_path / "other"
    other_repo.mkdir()
    git(other_repo, "init", "-q")
    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(other_repo, receipt)
    assert exc.value.code == "ENTRY_ADOPTION_INVALID"


def test_retained_validation_rejects_branch_head_or_base_tree_movement(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    git(repository, "checkout", "-b", "other-branch")
    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(repository, receipt)
    assert exc.value.code == "ENTRY_ADOPTION_INVALID"
    git(repository, "checkout", receipt["branch"])

    (repository / "committed.txt").write_text("new commit\n")
    git(repository, "add", "committed.txt")
    git(repository, "commit", "-m", "rogue commit")
    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(repository, receipt)
    assert exc.value.code == "ENTRY_ADOPTION_INVALID"


def test_retained_validation_rejects_staged_changes_and_index_movement(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    (repository / "staged.txt").write_text("staged file\n")
    git(repository, "add", "staged.txt")

    with pytest.raises(EntryAdoptionError) as exc:
        entry_adoption.validate_retained_entry(repository, receipt)
    assert exc.value.code == "ENTRY_STAGED_CHANGES"


def test_full_lifecycle_work_stage_modifies_adopted_path_checkpoint(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("initial candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        work_mutates=True,
        work_mutate_file="candidate.txt",
        work_mutate_content="modified by work stage\n",
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
        finalization_policy="checkpoint",
    )
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert "candidate.txt" in state["phase_owned_paths"]
    assert state["checkpoint_candidate"] is not None


def test_full_lifecycle_work_stage_modifies_adopted_path_publish(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("initial candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        work_mutates=True,
        work_mutate_file="candidate.txt",
        work_mutate_content="published modification by work\n",
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
    assert state["push"]["status"] == "succeeded"


def test_full_lifecycle_terminal_stage_modifies_adopted_path(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("initial candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        terminal_mutates=True,
        terminal_mutate_file="candidate.txt",
        terminal_mutate_content="modified by terminal closeout stage\n",
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
        finalization_policy="checkpoint",
    )
    assert state["complete"] is True
    assert state["outcome"] == "completed"


def test_full_lifecycle_reviewer_mutating_adopted_path_blocked(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("initial candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        review_mutates=True,
        review_mutate_file="candidate.txt",
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
        d.dispatch(
            PHASE,
            REQUEST,
            entry_adoption=receipt_file,
            finalization_policy="checkpoint",
        )
    assert exc_info.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"


def test_full_lifecycle_unadopted_dirty_path_mutation_blocks(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("initial candidate\n")
    (repository / "unadopted_dirt.txt").write_text("untouched dirt\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        unadopted_paths=["unadopted_dirt.txt"],
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
        d.dispatch(
            PHASE,
            REQUEST,
            entry_adoption=receipt_file,
            finalization_policy="checkpoint",
        )
    assert exc_info.value.code == "ADOPTION_INVALID"


def test_full_lifecycle_unauthorized_git_commit_blocks(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("initial candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        unauthorized_commit=True,
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

    with pytest.raises(EntryAdoptionError) as exc_info:
        d.dispatch(
            PHASE,
            REQUEST,
            entry_adoption=receipt_file,
            finalization_policy="checkpoint",
        )
    assert exc_info.value.code == "ENTRY_ADOPTION_INVALID"
    assert "differs from adoption" in str(exc_info.value)


def test_full_lifecycle_adopted_path_deletion_routes_to_ownership_challenge(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("initial candidate\n")
    subprocess.run(["git", "add", "candidate.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-m", "add candidate"], cwd=repository, check=True)
    target.write_text("candidate dirty at entry\n")

    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    class DeletingRunner:
        def __init__(self, repo: Path):
            self.repo = repo
            self.calls: list[bytes] = []

        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            idx = len(self.calls)
            self.calls.append(prompt)
            started = time.time()
            if b"<<<AGENT-REVIEW-RESULT " in prompt:
                stdout = review(prompt, "reviewed_with_no_findings")
                return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)
            if b"<<<AGENT-PHASE-RESULT " in prompt:
                stdout = closeout_with_dispositions(prompt, dispositions=[{"path": "candidate.txt", "disposition": "phase_owned"}])
                return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)
            if idx == 2:  # Work stage: deletes candidate.txt
                (self.repo / "candidate.txt").unlink()
                stdout = json.dumps({"outcome": "completed", "body": "deleted candidate"}).encode()
                return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)
            return Result(exit_code=0, stdout=f"out {idx}".encode(), stderr=b"", truncated=False, started=started, ended=started)

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=DeletingRunner(repository),
    )
    res = d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file, finalization_policy="checkpoint")
    assert res["completion_kind"] == "candidate_requires_manager_disposition"
    assert res["finalization"]["outcome"] == "blocked"
    assert res["finalization"]["code"] == "OWNERSHIP_CHALLENGE_OPEN"
    assert "candidate.txt" in res["unclaimed_deletion_paths"]


def test_full_lifecycle_adopted_path_type_change_routes_to_ownership_type_check(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("initial candidate\n")
    subprocess.run(["git", "add", "candidate.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-m", "add candidate"], cwd=repository, check=True)
    target.write_text("candidate dirty at entry\n")

    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    class TypeChangeRunner:
        def __init__(self, repo: Path):
            self.repo = repo
            self.calls: list[bytes] = []

        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            idx = len(self.calls)
            self.calls.append(prompt)
            started = time.time()
            if b"<<<AGENT-REVIEW-RESULT " in prompt:
                stdout = review(prompt, "reviewed_with_no_findings")
                return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)
            if b"<<<AGENT-PHASE-RESULT " in prompt:
                stdout = closeout_with_dispositions(prompt, dispositions=[{"path": "candidate.txt", "disposition": "phase_owned"}])
                return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)
            if idx == 2:  # Work stage: replace with symlink
                (self.repo / "candidate.txt").unlink()
                (self.repo / "candidate.txt").symlink_to("base.txt")
                stdout = json.dumps({"outcome": "completed", "body": "type changed"}).encode()
                return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)
            return Result(exit_code=0, stdout=f"out {idx}".encode(), stderr=b"", truncated=False, started=started, ended=started)

    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=TypeChangeRunner(repository),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, entry_adoption=receipt_file, finalization_policy="checkpoint")
    assert exc_info.value.code == "OWNERSHIP_TYPE_CHANGE_UNSUPPORTED"


def test_final_candidate_includes_latest_adopted_bytes(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("original candidate bytes\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        work_mutates=True,
        work_mutate_file="candidate.txt",
        work_mutate_content="latest candidate bytes revision\n",
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

    branch = git(repository, "branch", "--show-current").strip()
    remote = tmp_path / "remote.git"
    remote_head = git(remote, "rev-parse", branch)
    content = git(remote, "show", f"{remote_head}:candidate.txt")
    assert content.strip() == "latest candidate bytes revision"


def test_retained_receipt_in_run_evidence_remains_original_snapshot(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("original candidate bytes\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        work_mutates=True,
        work_mutate_file="candidate.txt",
        work_mutate_content="modified candidate bytes\n",
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
        finalization_policy="checkpoint",
    )
    assert state["complete"] is True

    retained_in_state = state["entry_adoption"]
    assert retained_in_state["sha256"] == receipt["sha256"]
    assert (
        retained_in_state["path_metadata"]["candidate.txt"]["content_sha256"]
        == receipt["path_metadata"]["candidate.txt"]["content_sha256"]
    )
    assert retained_in_state["candidate_tree"] == receipt["candidate_tree"]

    run_dir = Path(state["run_directory"])
    on_disk = json.loads((run_dir / "entry-adoption.json").read_text(encoding="utf-8"))
    assert on_disk["sha256"] == receipt["sha256"]
    assert on_disk["candidate_tree"] == receipt["candidate_tree"]


def test_checkpoint_reconstruction_after_adopted_path_revised(
    repository: Path, tmp_path: Path
):
    (repository / "candidate.txt").write_text("original candidate bytes\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        work_mutates=True,
        work_mutate_file="candidate.txt",
        work_mutate_content="checkpoint revised content\n",
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
        finalization_policy="checkpoint",
    )
    assert state["complete"] is True
    checkpoint_cand = state["checkpoint_candidate"]
    assert checkpoint_cand is not None
    assert checkpoint_cand["reconstruction"]["verified"] is True
    current_tree = candidate.tree_identity(repository)
    assert checkpoint_cand["reconstruction"]["reconstructed_tree"] == current_tree["tree"]


def test_custody1_ordinary_non_mutating_cases(repository: Path, tmp_path: Path):
    (repository / "candidate.txt").write_text("non-mutating candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        work_mutates=False,
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


def test_run_layout_v2_structure_preserved(repository: Path, tmp_path: Path):
    (repository / "candidate.txt").write_text("v2 layout candidate\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="adoption"
    )
    receipt_file = tmp_path / "adoption.json"
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    runner = EntryBoundaryRunner(
        repository,
        adopted_paths=["candidate.txt"],
        work_mutates=True,
        work_mutate_file="candidate.txt",
        work_mutate_content="v2 mutated\n",
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
        finalization_policy="checkpoint",
    )
    assert state["complete"] is True

    run_dir = Path(state["run_directory"])
    assert (run_dir / "state.json").exists()
    assert (run_dir / "request.json").exists()
    assert (run_dir / "resolved.json").exists()
    assert (run_dir / "entry-evidence.json").exists()
    assert (run_dir / "entry-adoption.json").exists()


def test_validate_entry_strict_default_even_without_request_binding(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("unmodified candidate content\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    # 1. Calling validate_entry with NO request/phase arguments succeeds on unmodified candidate
    validated = entry_adoption.validate_entry(repository, receipt)
    assert validated["sha256"] == receipt["sha256"]

    # 2. Mutate adopted worktree file
    target.write_text("mutated candidate bytes after adoption\n")

    # 3. Calling validate_entry with NO request/phase arguments MUST fail with ENTRY_ADOPTION_DRIFT
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_entry(repository, receipt)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"

    # 4. Calling validate_retained_entry accepts legitimate evolution while verifying integrity
    retained = entry_adoption.validate_retained_entry(repository, receipt)
    assert retained["sha256"] == receipt["sha256"]


def test_validate_entry_rejects_strict_parameter_and_no_aliases():
    # Verify strict=False escape hatch is not supported (fail-closed)
    import inspect
    sig = inspect.signature(entry_adoption.validate_entry)
    assert "strict" not in sig.parameters

    # Verify bootstrap aliases are removed
    assert not hasattr(entry_adoption, "validate_strict")
    assert not hasattr(entry_adoption, "validate_retained")


def test_adoption_guard_boundary_uses_retained_validation_on_evolved_candidate(
    repository: Path, tmp_path: Path
):
    target = repository / "candidate.txt"
    target.write_text("initial candidate content\n")
    req_file = write_request_file(tmp_path)
    receipt = entry_adoption.create(
        req_file, repository, ["candidate.txt"], reason="valid"
    )

    # Mutate adopted file (simulating work-stage evolution)
    target.write_text("evolved work stage content\n")

    # validate_entry would fail here:
    with pytest.raises(EntryAdoptionError) as exc_info:
        entry_adoption.validate_entry(repository, receipt)
    assert exc_info.value.code == "ENTRY_ADOPTION_DRIFT"

    # But adoption.guard_boundary explicitly calls validate_retained_entry, so it succeeds
    state = {
        "entry_adoption": receipt,
        "entry_dirt_identities": {},
    }
    raw_tree = candidate.tree_identity(repository)["tree"]
    # guard_boundary must not raise ENTRY_ADOPTION_DRIFT
    adoption.guard_boundary(state, repository, raw_tree, ())
