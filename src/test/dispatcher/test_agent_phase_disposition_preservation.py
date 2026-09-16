from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable

import pytest

from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.gitstate import GitStateError
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest


ROOT = Path(__file__).resolve().parents[3]
PHASE_ID = "DISPOSITION-PRESERVATION"
REQUEST = PhaseRequest(
    "implementation_testing", "normal", "Preserve a dispositioned candidate."
)


def git(cwd: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=cwd, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("# Initial Repo\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-q", "-m", "initial commit")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-q", "--set-upstream", "origin", "HEAD")
    return root


def _write_fake_evidence(argv: list[str], exit_code: int) -> None:
    if "--evidence-prefix" not in argv:
        return
    prefix = Path(argv[argv.index("--evidence-prefix") + 1])
    empty = {
        "text": "",
        "utf8_bytes": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "truncated": False,
        "source": None,
    }
    path = prefix.with_name(f"{prefix.name}.antigravity-terminal-result.json")
    path.write_text(
        json.dumps(
            {
                "schema": "antigravity-terminal-evidence-v2",
                "version": 2,
                "profile": argv[1],
                "model": argv[1],
                "reviewer": "--reviewer" in argv,
                "plan_mode": "--reviewer" in argv,
                "wrapper_exit_code": exit_code,
                "provider_record_observed": False,
                "terminal_result_observed": False,
                "terminal_record_kind": "no_terminal_event",
                "protocol_evidence_outcome": "no_terminal_event",
                "oversized_record_classification": None,
                "completion_fence_observed": exit_code == 0,
                "raw_result_artifact": None,
                "raw_result_absent_reason": "focused test runner",
                "raw_result_bytes": 0,
                "raw_result_sha256": None,
                "normalized_status": "success" if exit_code == 0 else "error",
                "raw_status": None,
                "child_started": True,
                "child_exit_code": exit_code,
                "protocol_error": None,
                "reason_fields": {key: dict(empty) for key in (
                    "error", "message", "reason", "cancel_reason",
                    "cancellation_reason", "finish_reason", "termination_reason",
                    "code", "error_code",
                )},
                "identifier_fields": {key: dict(empty) for key in (
                    "conversation_id", "request_id", "session_id", "operation_id",
                    "run_id", "turn_id",
                )},
                "preferred_reason": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _phase_result(prompt: bytes) -> bytes:
    match = re.search(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
    assert match is not None
    nonce = match.group(1).decode("ascii")
    payload = {
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "The terminal candidate is dispositioned.",
        "commit_message": {
            "subject": "AGENTCENTRAL-DISPOSITION-FLOW1: Preserve candidate",
            "body": "",
        },
    }
    return (
        f"<<<AGENT-PHASE-RESULT {nonce}>>>\n"
        f"{json.dumps(payload)}\n"
        f"<<<END-AGENT-PHASE-RESULT {nonce}>>>\n"
    ).encode("utf-8")


def _review_result(prompt: bytes, stage: str) -> bytes:
    match = re.search(rb"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", prompt)
    assert match is not None
    nonce = match.group(1).decode("ascii")
    payload = {
        "version": 1,
        "stage": stage,
        "outcome": "reviewed_with_findings",
        "body": "Advisory findings are forwarded to the dispositioner.",
    }
    return (
        f"<<<AGENT-REVIEW-RESULT {nonce}>>>\n{json.dumps(payload)}\n"
        f"<<<END-AGENT-REVIEW-RESULT {nonce}>>>\n"
    ).encode("utf-8")


class Runner:
    def __init__(self, hook: Callable[[int, Path, bytes], None] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.hook = hook

    def __call__(
        self,
        argv: list[str],
        prompt: bytes,
        cwd: Path,
        max_output: int,
        on_output: Any = None,
    ) -> Result:
        del max_output, on_output
        index = len(self.calls)
        self.calls.append({"argv": argv, "prompt": prompt, "cwd": cwd})
        if self.hook is not None:
            self.hook(index, cwd, prompt)
        stage_match = re.search(rb"^stage: ([a-z_]+)$", prompt, re.MULTILINE)
        stage = stage_match.group(1).decode("ascii") if stage_match else ""
        if b"<<<AGENT-PHASE-RESULT " in prompt:
            stdout = _phase_result(prompt)
        elif b"<<<AGENT-REVIEW-RESULT " in prompt:
            stdout = _review_result(prompt, stage)
        elif stage == "plan":
            stdout = b"Plan: preserve candidate bytes."
        elif stage == "work":
            stdout = b"Produced: preserve candidate bytes."
        else:
            stdout = f"{stage or 'stage'} evidence".encode("utf-8")
        started = time.time()
        _write_fake_evidence(argv, 0)
        return Result(0, stdout, b"", False, started, started)


def make_dispatcher(repository: Path, tmp_path: Path, runner: Runner) -> Dispatcher:
    return Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        claude_launcher="/fake/claude-profile",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )


def _run_directory(tmp_path: Path) -> Path:
    directories = [
        path.parent for path in (tmp_path / "runs").rglob("state.json")
    ]
    assert len(directories) == 1
    return directories[0]


def test_nonoverlap_operator_dirt_commits_only_phase_product(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "README.md").write_text("operator edit\n", encoding="utf-8")

    def hook(index: int, cwd: Path, prompt: bytes) -> None:
        if index == 2:
            (cwd / "phase.txt").write_text("phase product\n", encoding="utf-8")

    state = make_dispatcher(repository, tmp_path, Runner(hook)).dispatch(
        PHASE_ID, REQUEST
    )

    assert state["complete"] is True
    assert state["repository_finalized"] is True
    assert state["completion_kind"] == "published"
    assert state["phase_delta"] == [{"status": "A", "path": "phase.txt"}]
    committed = git(
        repository,
        "diff-tree",
        "-r",
        "--name-only",
        "--no-commit-id",
        "HEAD^",
        "HEAD",
    ).splitlines()
    assert committed == ["phase.txt"]
    assert (repository / "README.md").read_text(encoding="utf-8") == "operator edit\n"


def test_overlap_completes_candidate_and_requires_manager_disposition(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "README.md").write_text("operator edit\n", encoding="utf-8")

    def hook(index: int, cwd: Path, prompt: bytes) -> None:
        if index == 2:
            (cwd / "README.md").write_text("phase edit\n", encoding="utf-8")
            (cwd / "phase.txt").write_text("phase product\n", encoding="utf-8")

    before = git(repository, "rev-parse", "HEAD")
    state = make_dispatcher(repository, tmp_path, Runner(hook)).dispatch(
        PHASE_ID, REQUEST
    )

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["manager_disposition_required"] is True
    assert state["manager_disposition"]["reason"] == "entry_dirt_overlap"
    assert state["manager_disposition"]["paths"] == ["README.md"]
    assert state["repository_finalized"] is False
    assert state["completion_kind"] == "candidate_requires_manager_disposition"
    assert state["commit"] is None
    assert state["push"]["status"] == "not_attempted_manager_ownership"
    assert git(repository, "rev-parse", "HEAD") == before
    assert (repository / "README.md").read_text(encoding="utf-8") == "phase edit\n"
    assert (repository / "phase.txt").read_text(encoding="utf-8") == "phase product\n"
    assert sorted(state["candidate_manifest"]["paths"]) == ["phase.txt"]
    challenge = state['ownership_challenges']['records'][0]
    assert challenge['path'] == 'README.md'
    assert challenge['reason'] == 'entry_dirt_overlap'
    assert state['ownership_candidate_evidence']['raw']['reconstruction_verified']


def test_active_git_operation_preserves_candidate_and_blocks_finalization(
    repository: Path, tmp_path: Path
) -> None:
    def hook(index: int, cwd: Path, prompt: bytes) -> None:
        if index == 4:
            (cwd / "phase.txt").write_text("phase product\n", encoding="utf-8")
            (cwd / ".git" / "MERGE_HEAD").write_text("0" * 40 + "\n", encoding="ascii")

    before = git(repository, "rev-parse", "HEAD")
    try:
        with pytest.raises((DispatchError, GitStateError)) as raised:
            make_dispatcher(repository, tmp_path, Runner(hook)).dispatch(
                PHASE_ID, REQUEST
            )
        assert raised.value.code == "ENTRY_ACTIVE_GIT_OPERATION"
        directory = _run_directory(tmp_path)
        state = json.loads((directory / "state.json").read_text(encoding="utf-8"))
        result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
        assert state["complete"] is False
        assert state["blocking_reason"]["code"] == "ENTRY_ACTIVE_GIT_OPERATION"
        assert "MERGE_HEAD" in state["blocking_reason"]["detail"]
        assert state["failure_candidate"]["tree"]
        assert "phase.txt" in state["failure_candidate"]["candidate_paths"]
        assert result["failure_candidate"]["tree"] == state["failure_candidate"]["tree"]
        assert git(repository, "rev-parse", "HEAD") == before
        assert (repository / "phase.txt").read_text(encoding="utf-8") == "phase product\n"
    finally:
        marker = repository / ".git" / "MERGE_HEAD"
        if marker.exists():
            marker.unlink()
