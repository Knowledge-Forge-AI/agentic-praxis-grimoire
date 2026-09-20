from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import time
from typing import Callable

import pytest

from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest
from agent_phase import result as result_module


ROOT = Path(__file__).resolve().parents[3]
PHASE = "RESUME1"
REQUEST = PhaseRequest("implementation_testing", "codex_only", "Implement the change.")


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "base.txt").write_text("base\n")
    git(root, "add", "base.txt")
    git(root, "commit", "-q", "-m", "initial")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-q", "--set-upstream", "origin", "HEAD")
    return root


def closeout(
    prompt: bytes, *, duplicate: bool = False,
    subject: str | None = "Resume phase",
) -> bytes:
    nonce = re.search(rb"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
    assert nonce is not None
    marker = nonce.group(1).decode()
    payload = json.dumps({
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "done",
        "commit_message": (
            None if subject is None else {"subject": subject, "body": ""}
        ),
    })
    block = (
        f"<<<AGENT-PHASE-RESULT {marker}>>>\n{payload}\n"
        f"<<<END-AGENT-PHASE-RESULT {marker}>>>\n"
    ).encode()
    return block + block if duplicate else block


def review(prompt: bytes, outcome: str = "reviewed_with_no_findings") -> bytes:
    nonce = re.search(rb"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", prompt)
    stage = re.search(rb"^stage: ([a-z_]+)$", prompt, re.MULTILINE)
    assert nonce is not None and stage is not None
    token = nonce.group(1).decode()
    payload = json.dumps({
        "version": 1,
        "stage": stage.group(1).decode(),
        "outcome": outcome,
        "body": "subject is unreviewable" if outcome == "unreviewable" else "no findings",
    })
    return (
        f"<<<AGENT-REVIEW-RESULT {token}>>>\n{payload}\n"
        f"<<<END-AGENT-REVIEW-RESULT {token}>>>\n"
    ).encode()


class Runner:
    def __init__(
        self,
        *,
        fail_at: int | None = None,
        duplicate: bool = False,
        mutate_at: int | None = None,
        subject: str | None = "Resume phase",
        review_outcome: str = "reviewed_with_no_findings",
    ) -> None:
        self.calls: list[bytes] = []
        self.fail_at = fail_at
        self.duplicate = duplicate
        self.mutate_at = mutate_at
        self.subject = subject
        self.review_outcome = review_outcome

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        index = len(self.calls)
        self.calls.append(prompt)
        if self.mutate_at == index:
            (cwd / "phase.txt").write_text(f"stage {index}\n")
        started = time.time()
        is_closeout = b"<<<AGENT-PHASE-RESULT " in prompt
        is_review = b"<<<AGENT-REVIEW-RESULT " in prompt
        if is_closeout:
            stdout = closeout(
                prompt, duplicate=self.duplicate, subject=self.subject
            )
        elif is_review:
            stdout = review(prompt, self.review_outcome)
        else:
            stdout = f"output {index}".encode()
        return Result(
            exit_code=1 if self.fail_at == index else 0,
            stdout=stdout,
            stderr=b"failed" if self.fail_at == index else b"",
            truncated=False,
            started=started,
            ended=started,
        )


class InlineRepairRunner:
    """Return one malformed terminal result and one canonical formatter result."""

    def __init__(self) -> None:
        self.calls: list[bytes] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        self.calls.append(prompt)
        started = time.time()
        if prompt.startswith(b"Formatting-only terminal result repair."):
            nonce = re.search(rb"Terminal nonce: ([0-9a-f]{32})", prompt)
            stage = re.search(rb"terminal_stage: ([a-z_]+)", prompt)
            assert nonce is not None and stage is not None
            token = nonce.group(1).decode()
            name = stage.group(1).decode()
            payload = json.dumps({
                "version": 1,
                "stage": name,
                "outcome": "completed",
                "body": "repaired",
                "commit_message": {"subject": "Resume phase", "body": ""},
            })
            stdout = (
                f"<<<AGENT-PHASE-RESULT {token}>>>\n{payload}\n"
                f"<<<END-AGENT-PHASE-RESULT {token}>>>\n"
            ).encode()
        else:
            stdout = b"Completed work, but omitted the required result fence."
        return Result(0, stdout, b"", False, started, started)


def dispatcher(repository: Path, run_root: Path, runner: Callable) -> Dispatcher:
    return Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )


def only_run(run_root: Path) -> Path:
    runs = list(run_root.rglob("state.json"))
    assert len(runs) == 1
    return runs[0].parent


def test_resume_does_not_inherit_failed_review_attempt_as_complete(
    repository: Path, tmp_path: Path
) -> None:
    source_runner = Runner(fail_at=1)
    source_dispatcher = dispatcher(repository, tmp_path / "source", source_runner)
    with pytest.raises(DispatchError):
        source_dispatcher.dispatch(
            PHASE,
            REQUEST,
            finalization_policy="checkpoint",
        )
    source = only_run(tmp_path / "source")

    resumed = dispatcher(
        repository, tmp_path / "resumed", Runner()
    ).resume(
        PHASE,
        REQUEST,
        source,
        dry_run=True,
        finalization_policy="checkpoint",
    )

    assert resumed["resume"]["inherited_stages"] == ["plan"]
    assert resumed["resume"]["effective_from_stage"] == "plan_review"
    assert resumed["effective_checkpoints"] == []


def test_resume_inherits_completed_unreviewable_review(
    repository: Path, tmp_path: Path
) -> None:
    source_runner = Runner(fail_at=2, review_outcome="unreviewable")
    source_dispatcher = dispatcher(repository, tmp_path / "source", source_runner)
    with pytest.raises(DispatchError):
        source_dispatcher.dispatch(
            PHASE,
            REQUEST,
            finalization_policy="checkpoint",
        )
    source = only_run(tmp_path / "source")

    resumed = dispatcher(
        repository, tmp_path / "resumed", Runner()
    ).resume(
        PHASE,
        REQUEST,
        source,
        dry_run=True,
        finalization_policy="checkpoint",
    )

    assert resumed["resume"]["inherited_stages"] == ["plan", "plan_review"]
    assert resumed["resume"]["effective_from_stage"] == "work"
    assert resumed["effective_checkpoints"] == ["post_planning"]


def failed_source(
    repository: Path, tmp_path: Path, fail_at: int, *, mutate_at: int | None = None
) -> Path:
    run_root = tmp_path / f"source-{fail_at}"
    with pytest.raises(DispatchError):
        dispatcher(
            repository, run_root, Runner(fail_at=fail_at, mutate_at=mutate_at)
        ).dispatch(PHASE, REQUEST)
    return only_run(run_root)


def test_standard_resume_inline_repair_does_not_inflate_semantic_count(
    repository: Path, tmp_path: Path
) -> None:
    source_root = tmp_path / "source-inline-repair"
    with pytest.raises(DispatchError):
        dispatcher(repository, source_root, Runner(fail_at=4)).dispatch(
            PHASE, REQUEST, finalization_policy="checkpoint"
        )
    runner = InlineRepairRunner()

    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE,
        REQUEST,
        only_run(source_root),
        "closeout",
        finalization_policy="checkpoint",
    )

    assert len(runner.calls) == 2
    assert state["provider_invocations_inherited"] == 4
    assert state["provider_invocations_performed"] == 1
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["provider_invocations_effective"] == 5
    assert state["terminal_result_validated"] is True


def duplicate_source(
    repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    mutate: bool = True,
    subject: str | None = "Resume phase",
) -> Path:
    run_root = tmp_path / "source-duplicate"
    real_parse = result_module.parse

    def old_parser(data: bytes, stage: str, nonce: str):
        if data.count(result_module.markers(nonce)[0].encode()) > 1:
            raise result_module.ResultError("RESULT_DUPLICATE_FENCE", "old parser")
        return real_parse(data, stage, nonce)

    with monkeypatch.context() as context:
        context.setattr(result_module, "parse", old_parser)
        with pytest.raises(DispatchError) as caught:
            dispatcher(
                repository,
                run_root,
                Runner(duplicate=True, mutate_at=4 if mutate else None, subject=subject),
            ).dispatch(PHASE, REQUEST)
    assert caught.value.code == "RESULT_DUPLICATE_FENCE"
    return only_run(run_root)


@pytest.mark.parametrize(
    ("fail_at", "expected"),
    [(0, "plan"), (1, "plan_review")],
)
def test_auto_selects_first_unsatisfied_stage(
    repository: Path, tmp_path: Path, fail_at: int, expected: str
) -> None:
    source = failed_source(repository, tmp_path, fail_at)
    runner = Runner(fail_at=0)

    with pytest.raises(DispatchError):
        dispatcher(repository, tmp_path / "resumed", runner).resume(
            PHASE, REQUEST, source, "auto"
        )

    state = json.loads(only_run(tmp_path / "resumed").joinpath("state.json").read_text())
    assert state["resume"]["effective_from_stage"] == expected


def test_resume_work_inherits_one_review_and_performs_remaining_three_stages(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 2)
    runner = Runner(mutate_at=0)

    state = dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE, REQUEST, source, "work"
    )

    assert len(runner.calls) == 3
    assert state["provider_invocations_inherited"] == 2
    assert state["provider_invocations_performed"] == 3
    assert state["effective_checkpoints"] == ["post_planning", "pre_final"]
    assert state["effective_stages"]["work"] == "performed"
    assert state["proposal_binding"] == state["plan_candidate"]
    assert state["plan_proposal_binding"] == state["plan_candidate"]
    assert b"Plan proposal binding (dispatcher-owned exact bytes)" in runner.calls[0]
    assert b"Planner proposal \xe2\x80\x94 exact bound bytes, to be dispositioned" in runner.calls[0]
    assert b"authoritative exact material" not in runner.calls[0]
    assert state["review_artifact_outcomes"] == {
        "plan_review": "reviewed_with_no_findings",
        "final_review": "reviewed_with_no_findings",
    }


def test_resumed_mutating_closeout_verifies_authorized_terminal_revision(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 4)

    state = dispatcher(
        repository, tmp_path / "resumed", Runner(mutate_at=0)
    ).resume(PHASE, REQUEST, source, "closeout")

    assert state["complete"] is True
    assert state["terminal_result_validated"] is True
    assert state["terminal_bytes_verified"] is True
    assert state["authorized_revisor_revisions"]["paths"] == ["phase.txt"]
    assert state["authorized_revisor_revisions"]["terminal_bytes_verified"] is True


def test_explicit_later_than_safe_stage_is_rejected_before_new_run(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 1)

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "resumed", Runner()).resume(
            PHASE, REQUEST, source, "work"
        )

    assert caught.value.code == "RESUME_STAGE_UNSATISFIED"
    assert not (tmp_path / "resumed").exists()


def test_request_mismatch_is_rejected(repository: Path, tmp_path: Path) -> None:
    source = failed_source(repository, tmp_path, 0)
    changed = PhaseRequest(REQUEST.phase_type, REQUEST.execution_mode, "changed scope")

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "resumed", Runner()).resume(
            PHASE, changed, source
        )

    assert caught.value.code == "RESUME_REQUEST_MISMATCH"


def test_unrelated_worktree_drift_is_allowed(repository: Path, tmp_path: Path) -> None:
    source = failed_source(repository, tmp_path, 0)
    (repository / "drift.txt").write_text("drift\n")

    state = dispatcher(repository, tmp_path / "resumed", Runner()).resume(
        PHASE, REQUEST, source
    )

    assert state["commit"] is None
    assert (repository / "drift.txt").read_text() == "drift\n"
    assert state["resume"]["evidence_boundary_skew"] is True


def test_finalize_duplicate_fence_invokes_zero_providers_and_publishes_once(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = duplicate_source(repository, tmp_path, monkeypatch)
    source_hashes = {path.name: path.read_bytes() for path in source.iterdir() if path.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("finalize invoked a provider")

    state = dispatcher(repository, tmp_path / "resumed", forbidden).resume(
        PHASE, REQUEST, source, "finalize"
    )

    assert state["complete"] is True
    assert state["provider_invocations_performed"] == 0
    assert state["provider_invocations_inherited"] == 5
    assert state["closeout_fence_copies"] == 2
    assert git(repository, "rev-parse", "HEAD") == state["commit"]["sha"]
    branch = git(repository, "branch", "--show-current")
    remote_head = git(
        repository, "ls-remote", "origin", f"refs/heads/{branch}"
    ).split()[0]
    assert remote_head == state["commit"]["sha"]
    assert Path(state["archive_path"]).is_file()
    assert all((source / name).read_bytes() == data for name, data in source_hashes.items())


def test_finalize_empty_delta_creates_no_commit_or_push(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = duplicate_source(
        repository, tmp_path, monkeypatch, mutate=False, subject=None
    )
    entry_head = git(repository, "rev-parse", "HEAD")

    state = dispatcher(repository, tmp_path / "resumed", lambda *args: None).resume(
        PHASE, REQUEST, source, "finalize"
    )

    assert state["commit"] is None
    assert state["push"]["attempted"] is False
    assert git(repository, "rev-parse", "HEAD") == entry_head


def test_resumed_dry_run_performs_full_preflight_without_archive_or_provider(
    repository: Path, tmp_path: Path
) -> None:
    source = failed_source(repository, tmp_path, 0)

    state = dispatcher(
        repository, tmp_path / "resumed", lambda *args: pytest.fail("provider called")
    ).resume(PHASE, REQUEST, source, dry_run=True)

    assert state["outcome"] == "dry_run"
    assert state["archive"]["attempted"] is False
    assert not Path(state["archive_path"]).exists()
