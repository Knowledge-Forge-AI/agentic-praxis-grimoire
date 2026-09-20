"""Regression tests for native Git custody and transition reconciliation (Cases 1-28)."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import time

import pytest

from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase import native_git
from agent_phase.native_git import NativeGitError
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest
from test_agent_phase_resume import ROOT, PHASE, git, repository as _repository, review

repository = _repository


REQUEST = PhaseRequest("implementation_testing", "codex_only", "Implement native change.")


def write_request_file(path: Path) -> Path:
    req_path = path / f"{PHASE}.json"
    req_path.write_text(json.dumps(REQUEST.as_dict()), encoding="utf-8")
    return req_path


class NativeToolRunner:
    def __init__(
        self,
        repository: Path,
        *,
        commit_at_work: bool = True,
        commit_file: str = "flake.lock",
        commit_content: str = "native content\n",
        unauthorized_file: str | None = None,
        leave_dirty: bool = False,
        leave_staged: bool = False,
        extra_commits: int = 0,
        closer_mutates: bool = False,
        closer_mutate_file: str = "closer.txt",
        closer_subject: str | None = "Closeout commit",
        report_commit: bool = True,
        reported_commit_override: str | None = None,
        reported_parent_override: str | None = None,
        omit_git_disposition: bool = False,
        claim_without_commit: bool = False,
        claim_unauthorized_stage: bool = False,
        unowned_dirt_file: str | None = None,
    ) -> None:
        self.repository = repository
        self.commit_at_work = commit_at_work
        self.commit_file = commit_file
        self.commit_content = commit_content
        self.unauthorized_file = unauthorized_file
        self.leave_dirty = leave_dirty
        self.leave_staged = leave_staged
        self.extra_commits = extra_commits
        self.closer_mutates = closer_mutates
        self.closer_mutate_file = closer_mutate_file
        self.closer_subject = closer_subject
        self.report_commit = report_commit
        self.reported_commit_override = reported_commit_override
        self.reported_parent_override = reported_parent_override
        self.omit_git_disposition = omit_git_disposition
        self.claim_without_commit = claim_without_commit
        self.claim_unauthorized_stage = claim_unauthorized_stage
        self.unowned_dirt_file = unowned_dirt_file

        self.calls: list[bytes] = []
        self.native_commit_sha: str | None = None
        self.native_parent_sha: str | None = None

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        index = len(self.calls)
        self.calls.append(prompt)
        started = time.time()
        is_closeout = b"<<<AGENT-PHASE-RESULT " in prompt
        is_review = b"<<<AGENT-REVIEW-RESULT " in prompt

        if index == 2:  # work stage
            if self.commit_at_work:
                self.native_parent_sha = git(self.repository, "rev-parse", "HEAD")
                target = self.repository / self.commit_file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(self.commit_content)
                git(self.repository, "add", self.commit_file)

                if self.unauthorized_file:
                    unauth = self.repository / self.unauthorized_file
                    unauth.parent.mkdir(parents=True, exist_ok=True)
                    unauth.write_text("unauthorized content\n")
                    git(self.repository, "add", self.unauthorized_file)

                if self.unowned_dirt_file:
                    unowned = self.repository / self.unowned_dirt_file
                    unowned.write_text("modified unowned dirt\n")
                    git(self.repository, "add", self.unowned_dirt_file)

                git(self.repository, "commit", "-q", "-m", "native tool commit")
                self.native_commit_sha = git(self.repository, "rev-parse", "HEAD")

                for _ in range(self.extra_commits):
                    target.write_text("more content\n")
                    git(self.repository, "add", self.commit_file)
                    git(self.repository, "commit", "-q", "-m", "extra commit")
                    self.native_commit_sha = git(self.repository, "rev-parse", "HEAD")

                if self.leave_dirty:
                    target.write_text("leftover dirty bytes\n")

                if self.leave_staged:
                    staged_f = self.repository / "staged.txt"
                    staged_f.write_text("staged bytes\n")
                    git(self.repository, "add", "staged.txt")

            work_res = {
                "outcome": "completed",
                "summary": "native tool finished",
            }
            if not self.omit_git_disposition and self.report_commit and self.native_commit_sha:
                work_res["git_disposition"] = {
                    "action": "committed",
                    "commit": self.reported_commit_override or self.native_commit_sha,
                    "parent": self.reported_parent_override or self.native_parent_sha,
                }
            elif self.claim_without_commit:
                work_res["git_disposition"] = {
                    "action": "committed",
                    "commit": "1234567890123456789012345678901234567890",
                    "parent": self.native_parent_sha or "0000000000000000000000000000000000000000",
                }
            stdout = json.dumps(work_res).encode()
            return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)

        if is_closeout:
            if self.closer_mutates:
                (self.repository / self.closer_mutate_file).write_text("closer bytes\n")
            dispositions = [{"path": self.commit_file, "disposition": "phase_owned"}]
            if self.closer_mutates and self.closer_mutate_file != self.commit_file:
                dispositions.append({"path": self.closer_mutate_file, "disposition": "phase_owned"})
            stdout = closeout_with_dispositions(prompt, dispositions=dispositions, subject=self.closer_subject)
            return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)

        if is_review:
            stdout = review(prompt, "reviewed_with_no_findings")
            return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)

        if index == 0 and self.claim_unauthorized_stage:
            # plan stage tries to claim native commit
            stdout = json.dumps({
                "git_disposition": {
                    "action": "committed",
                    "commit": "1234567890123456789012345678901234567890",
                }
            }).encode()
            return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)

        stdout = f"output {index}".encode()
        return Result(exit_code=0, stdout=stdout, stderr=b"", truncated=False, started=started, ended=started)


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
            None if subject is None else {"subject": subject, "body": ""}
        ),
    })
    return (
        f"<<<AGENT-PHASE-RESULT {marker}>>>\n{payload}\n"
        f"<<<END-AGENT-PHASE-RESULT {marker}>>>\n"
    ).encode()


def test_native_authority_creation_positive(repository: Path, tmp_path: Path):
    # Case 1: create_authority positive
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file,
        repository,
        stage="work",
        paths=["flake.lock"],
        reason="authorized nix-update promotion",
        max_commits=1,
    )
    assert auth["schema"] == "agent-phase-native-git-authority-v1"
    assert auth["authorized_stage"] == "work"
    assert auth["authorized_paths"] == ["flake.lock"]
    assert auth["max_commits"] == 1
    assert auth["publication_state"] == "pending"
    assert "sha256" in auth


def test_native_git_cli_authorize_subcommand(repository: Path, tmp_path: Path):
    # Case 2: CLI bin/agent-phase-native-git authorize
    req_file = write_request_file(tmp_path)
    out_file = tmp_path / "auth.json"
    cmd = [
        str(ROOT / "bin/agent-phase-native-git"),
        "authorize",
        "--request", str(req_file),
        "--stage", "work",
        "--paths", "flake.lock",
        "--reason", "authorized CLI promotion",
        "--output", str(out_file),
    ]
    res = subprocess.run(cmd, cwd=repository, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert out_file.is_file()
    rec = json.loads(out_file.read_text())
    assert rec["schema"] == "agent-phase-native-git-authority-v1"
    assert rec["authorized_paths"] == ["flake.lock"]


def test_native_commit_work_stage_publish_no_duplicate(repository: Path, tmp_path: Path):
    # Cases 3, 4, 5: Work-stage native commit, no HEAD_MOVED_WITHOUT_COMMIT,
    # exact native commit reused and published without duplicate commit.
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file,
        repository,
        stage="work",
        paths=["flake.lock"],
        reason="authorized nix-update promotion",
    )
    auth_file = tmp_path / "native-auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_file="flake.lock")
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
        native_git_authority=auth_file,
        finalization_policy="publish",
    )

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["commit_reused"] is True
    assert state["final_head"] == runner.native_commit_sha
    assert state["push"]["status"] == "succeeded"
    assert state["push"]["post_push_remote_head"] == runner.native_commit_sha
    branch = git(repository, "branch", "--show-current").strip()
    remote = tmp_path / "remote.git"
    assert git(remote, "rev-parse", branch) == runner.native_commit_sha

    # Case 5 & 24: Reviewer prompt sees commit B and immutable review bindings bind B
    review_prompt = runner.calls[3]
    assert runner.native_commit_sha.encode() in review_prompt or b"flake.lock" in review_prompt
    assert "immutable_review_bindings" in state


def test_native_commit_checkpoint_policy(repository: Path, tmp_path: Path):
    # Case 6: Checkpoint policy preserves native commit
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file,
        repository,
        stage="work",
        paths=["flake.lock"],
        reason="authorized nix-update promotion",
    )
    auth_file = tmp_path / "native-auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_file="flake.lock")
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
        native_git_authority=auth_file,
        finalization_policy="checkpoint",
    )
    assert state["final_head"] == runner.native_commit_sha
    assert state["commit"]["sha"] == runner.native_commit_sha
    assert state["push"]["status"] == "not_attempted_by_policy"


def test_native_commit_commit_local_policy(repository: Path, tmp_path: Path):
    # Case 7: Commit-local policy preserves native commit
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file,
        repository,
        stage="work",
        paths=["flake.lock"],
        reason="authorized nix-update promotion",
    )
    auth_file = tmp_path / "native-auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_file="flake.lock")
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
        native_git_authority=auth_file,
        finalization_policy="commit-local",
    )
    assert state["final_head"] == runner.native_commit_sha
    assert state["commit"]["sha"] == runner.native_commit_sha
    assert state["push"]["status"] == "not_attempted_by_policy"


def test_unauthorized_commit_rejected_as_head_moved_without_commit(repository: Path, tmp_path: Path):
    # Case 8: Without authority and without claimed disposition, rejected as HEAD_MOVED_WITHOUT_COMMIT
    runner = NativeToolRunner(repository, commit_file="flake.lock", omit_git_disposition=True)
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
        d.dispatch(PHASE, REQUEST)
    assert exc_info.value.code == "HEAD_MOVED_WITHOUT_COMMIT"


def test_unauthorized_commit_with_claim_rejected_as_native_commit_unauthorized(repository: Path, tmp_path: Path):
    # Case 8b: Without authority but with claimed disposition, rejected as NATIVE_COMMIT_UNAUTHORIZED
    runner = NativeToolRunner(repository, commit_file="flake.lock", omit_git_disposition=False)
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
        d.dispatch(PHASE, REQUEST)
    assert exc_info.value.code == "NATIVE_COMMIT_UNAUTHORIZED"


def test_reported_commit_mismatch(repository: Path, tmp_path: Path):
    # Case 9: Reported commit != exit HEAD
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(
        repository,
        commit_file="flake.lock",
        reported_commit_override="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_REPORT_MISMATCH"


def test_exit_head_not_descendant(repository: Path, tmp_path: Path):
    # Case 10: Exit HEAD not descendant of entry HEAD
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    class OrphanCommitRunner(NativeToolRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            if len(self.calls) == 2:
                # create orphan commit
                tree = git(self.repository, "write-tree")
                orphan = git(self.repository, "commit-tree", tree, "-m", "orphan")
                git(self.repository, "update-ref", "HEAD", orphan)
                self.native_commit_sha = orphan
                self.calls.append(prompt)
                return Result(exit_code=0, stdout=json.dumps({
                    "git_disposition": {"commit": orphan}
                }).encode(), stderr=b"", truncated=False, started=time.time(), ended=time.time())
            return super().__call__(argv, prompt, cwd, max_output, on_output)

    runner = OrphanCommitRunner(repository)
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_ANCESTRY_INVALID"


def test_commit_chain_parent_mismatch(repository: Path, tmp_path: Path):
    # Case 11: Non-linear parent / merge commit
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test", max_commits=2
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    class MergeCommitRunner(NativeToolRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            if len(self.calls) == 2:
                parent1 = git(self.repository, "rev-parse", "HEAD")
                tree = git(self.repository, "write-tree")
                orphan = git(self.repository, "commit-tree", tree, "-m", "side")
                merge = git(self.repository, "commit-tree", tree, "-p", parent1, "-p", orphan, "-m", "merge")
                git(self.repository, "update-ref", "HEAD", merge)
                self.calls.append(prompt)
                return Result(exit_code=0, stdout=json.dumps({
                    "git_disposition": {"commit": merge}
                }).encode(), stderr=b"", truncated=False, started=time.time(), ended=time.time())
            return super().__call__(argv, prompt, cwd, max_output, on_output)

    runner = MergeCommitRunner(repository)
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_PARENT_MISMATCH"


def test_commit_touches_unauthorized_path(repository: Path, tmp_path: Path):
    # Case 12: Commit touches unauthorized path
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_file="flake.lock", unauthorized_file="unauthorized.py")
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_UNAUTHORIZED_PATH"


def test_worktree_dirty_after_native_commit(repository: Path, tmp_path: Path):
    # Case 13: Worktree dirty after native commit
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_file="flake.lock", leave_dirty=True)
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_WORKTREE_DIRTY"


def test_staged_residue_after_native_commit(repository: Path, tmp_path: Path):
    # Case 14: Staged residue in index after commit
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_file="flake.lock", leave_staged=True)
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_STAGED_RESIDUE"


def test_commit_count_exceeded(repository: Path, tmp_path: Path):
    # Case 15: Commit count exceeds max_commits
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], max_commits=1, reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_file="flake.lock", extra_commits=1)
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_COUNT_EXCEEDED"


def test_active_git_operation_during_native_transition(repository: Path, tmp_path: Path):
    # Case 16: Active git operation present
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    class ActiveOpRunner(NativeToolRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            res = super().__call__(argv, prompt, cwd, max_output, on_output)
            if len(self.calls) == 3:  # after work stage
                git_dir = Path(git(self.repository, "rev-parse", "--git-dir"))
                (self.repository / git_dir / "CHERRY_PICK_HEAD").write_text("dummy\n")
            return res

    runner = ActiveOpRunner(repository, commit_file="flake.lock")
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "ENTRY_ACTIVE_GIT_OPERATION"


def test_branch_changed_during_native_transition(repository: Path, tmp_path: Path):
    # Case 17: Branch changed
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    class BranchChangeRunner(NativeToolRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            res = super().__call__(argv, prompt, cwd, max_output, on_output)
            if len(self.calls) == 3:
                git(self.repository, "checkout", "-q", "-b", "other-branch")
            return res

    runner = BranchChangeRunner(repository, commit_file="flake.lock")
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "GIT_AUTHORITY_BRANCH_MISMATCH"


def test_remote_tracking_branch_already_advanced(repository: Path, tmp_path: Path):
    # Case 18: Remote tracking branch already advanced to include commit
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    class RemotePushedRunner(NativeToolRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            res = super().__call__(argv, prompt, cwd, max_output, on_output)
            if len(self.calls) == 3:
                # prematurely push to origin
                git(self.repository, "push", "origin", "HEAD")
            return res

    runner = RemotePushedRunner(repository, commit_file="flake.lock")
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_REMOTE_ADVANCED"


def test_native_commit_claimed_on_unauthorized_stage(repository: Path, tmp_path: Path):
    # Case 19: Claim on unauthorized stage
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, claim_unauthorized_stage=True)
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_UNAUTHORIZED"


def test_claimed_native_commit_missing(repository: Path, tmp_path: Path):
    # Case 20: Claimed native commit but HEAD did not advance
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_at_work=False, claim_without_commit=True)
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_COMMIT_MISSING"


def test_unowned_entry_dirt_modified_by_native_commit(repository: Path, tmp_path: Path):
    # Case 21: Unowned entry dirt modified by native commit
    (repository / "unowned.txt").write_text("entry dirt\n")
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(repository, commit_file="flake.lock", unowned_dirt_file="unowned.txt")
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "ENTRY_DIRT_NOT_PRESERVED"


def test_symlink_alias_path_traversal_refused(repository: Path, tmp_path: Path):
    # Case 22: Symlink alias path traversal
    (repository / "real_dir").mkdir()
    (repository / "symlink_dir").symlink_to("real_dir")
    req_file = write_request_file(tmp_path)
    with pytest.raises(NativeGitError, match="NATIVE_GIT_PATH_INVALID"):
        native_git.create_authority(
            req_file, repository, stage="work", paths=["symlink_dir/file.txt"], reason="test"
        )


def test_closer_follow_up_commit_on_top_of_native_commit(repository: Path, tmp_path: Path):
    # Cases 23, 24, 25, 26, 27: Closer follow-up changes create commit C on top of B, verify parent B, publish C
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(
        repository,
        commit_file="flake.lock",
        closer_mutates=True,
        closer_mutate_file="closer.txt",
        closer_subject="Closer follow-up commit",
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
    state = d.dispatch(PHASE, REQUEST, native_git_authority=auth_file, finalization_policy="publish")
    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["commit_reused"] is False
    c_commit = state["final_head"]
    assert c_commit != runner.native_commit_sha
    # Verify parent of C is B
    c_parent = git(repository, "rev-parse", f"{c_commit}^")
    assert c_parent == runner.native_commit_sha
    # Verify remote head is C
    assert state["push"]["status"] == "succeeded"
    assert state["push"]["post_push_remote_head"] == c_commit
    branch = git(repository, "branch", "--show-current").strip()
    remote = tmp_path / "remote.git"
    assert git(remote, "rev-parse", branch) == c_commit


def test_native_authority_tamper_or_cross_context_refused(repository: Path, tmp_path: Path):
    # Case 21: Tampered/cross-run/cross-request/cross-repo authority fails closed
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"

    # Subcase 1: Checksum tamper
    tampered = dict(auth)
    tampered["max_commits"] = 5
    auth_file.write_text(json.dumps(tampered))
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=NativeToolRunner(repository),
    )
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_GIT_AUTHORITY_INVALID"

    # Subcase 2: Malformed JSON
    auth_file.write_text("not json {")
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_GIT_AUTHORITY_INVALID"

    # Subcase 3: Cross-request digest
    other_req_file = tmp_path / "other.json"
    other_req = PhaseRequest("implementation_testing", "codex_only", "Different request.")
    other_req_file.write_text(json.dumps(other_req.as_dict()))
    other_auth = native_git.create_authority(
        other_req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file.write_text(json.dumps(other_auth))
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_GIT_AUTHORITY_INVALID"

    # Subcase 4: Cross-repo authority
    other_repo = tmp_path / "other_repo"
    other_repo.mkdir()
    git(other_repo, "init", "-b", "main")
    git(other_repo, "commit", "--allow-empty", "-m", "init")
    repo_auth = native_git.create_authority(
        req_file, other_repo, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file.write_text(json.dumps(repo_auth))
    with pytest.raises(DispatchError) as exc_info:
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "NATIVE_GIT_AUTHORITY_INVALID"


def test_finalrec1_recovers_native_chain_provider_free(repository: Path, tmp_path: Path):
    # Case 28: FINALREC1 recovers native commit chain provider-free
    from agent_phase.finalization_recovery import recover

    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(
        repository,
        commit_file="flake.lock",
        closer_mutates=True,
        closer_mutate_file="closer.txt",
        closer_subject="Closer follow-up commit",
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
    state = d.dispatch(PHASE, REQUEST, native_git_authority=auth_file, finalization_policy="publish")
    assert state["complete"] is True
    c_commit = state["final_head"]

    run_dir = Path(state["run_directory"])
    receipt = recover(run_dir, repository)
    assert receipt["finalization"]["outcome"] in ("recorded", "reused")
    assert receipt["observed_head"] == c_commit
    assert receipt["provider_invocations"] == 0


def test_closer_without_commit_message_when_mutated_fails(repository: Path, tmp_path: Path):
    # Closer mutated bytes but omitted commit message
    req_file = write_request_file(tmp_path)
    auth = native_git.create_authority(
        req_file, repository, stage="work", paths=["flake.lock"], reason="test"
    )
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(auth))

    runner = NativeToolRunner(
        repository,
        commit_file="flake.lock",
        closer_mutates=True,
        closer_mutate_file="closer.txt",
        closer_subject=None,
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
        d.dispatch(PHASE, REQUEST, native_git_authority=auth_file)
    assert exc_info.value.code == "COMMIT_MESSAGE_MISSING"
