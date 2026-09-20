"""Regression tests for worker termination classification and cleanup safety (Cases 47-53)."""

from __future__ import annotations

import json
from pathlib import Path
import time
from unittest.mock import patch

import pytest

from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase import gitstate
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest
pytest.importorskip("agent_workers", reason="agent_workers subsystem retained in Agent-Central")
from agent_workers.ledger import ParentLedger
from test_agent_phase_resume import ROOT, PHASE, git, repository as _repository, review, closeout

repository = _repository


REQUEST = PhaseRequest("implementation_testing", "gemini_sub", "Worker recovery test.")


class WorkerDeathRunner:
    def __init__(
        self,
        *,
        fail_at_work: bool = True,
        work_stdout: bytes = b"",
        work_exit_code: int = 137,
        mutate_in_work: bool = False,
    ):
        self.fail_at_work = fail_at_work
        self.work_stdout = work_stdout
        self.work_exit_code = work_exit_code
        self.mutate_in_work = mutate_in_work
        self.calls: list[bytes] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        self.calls.append(prompt)
        started = time.time()
        if b"<<<AGENT-REVIEW-RESULT " in prompt:
            stdout = review(prompt, "reviewed_with_no_findings")
            return Result(0, stdout, b"", False, started, started)
        elif b"<<<AGENT-PHASE-RESULT " in prompt:
            stdout = closeout(prompt, subject="Closeout commit")
            return Result(0, stdout, b"", False, started, started)
        elif len(self.calls) == 1:
            # Plan stage
            return Result(0, b"Initial plan\n", b"", False, started, started)
        else:
            # Work stage
            if self.mutate_in_work:
                (cwd / "candidate.txt").write_text("candidate created before crash\n")
            if self.fail_at_work:
                return Result(
                    self.work_exit_code,
                    self.work_stdout,
                    b"Worker process killed\n",
                    False,
                    started,
                    started,
                )
            return Result(0, b"Work completed\n", b"", False, started, started)


def test_worker_death_before_result_with_uncertain_cleanup(repository: Path, tmp_path: Path):
    # Case 47: Worker dies with uncertain_cleanup=True before result or candidate emission.
    # Terminal classification: WORKER_TERMINATED_BEFORE_RESULT, resume_safety: fresh_run_required.
    entry = gitstate.capture_entry(repository)
    run_root = tmp_path / "runs"
    runner = WorkerDeathRunner(fail_at_work=True, work_stdout=b"", work_exit_code=137)
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    drain_calls = []

    def fake_drain_and_close(self, timeout_seconds=15.0):
        drain_calls.append(self.parent_id)
        if "work" in self.parent_id:
            return {
                "uncertain_cleanup": True,
                "status": "stopping",
                "orphaned_pids": [12345, 12346],
            }
        return {"uncertain_cleanup": False, "status": "closed", "orphaned_pids": []}

    with patch.object(ParentLedger, "drain_and_close", fake_drain_and_close):
        with pytest.raises(DispatchError) as exc_info:
            d.dispatch(PHASE, REQUEST)

    assert exc_info.value.code == "WORKER_TERMINATED_BEFORE_RESULT"
    assert "uncertain cleanup requires fresh run" in str(exc_info.value)

    # Inspect the run directory
    run_dirs = [p.parent for p in run_root.rglob("state.json")]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    state_path = run_dir / "state.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert state["complete"] is False
    assert state["outcome"] == "blocked"
    assert state["resume_safety"] == "fresh_run_required"
    assert state["blocking_reason"]["code"] == "WORKER_TERMINATED_BEFORE_RESULT"
    assert state["worker_cleanup"] == {
        "certainty": "uncertain",
        "known_survivors": [12345, 12346],
        "candidate_emitted": False,
        "result_emitted": False,
    }

    # Inspect work stage metadata
    work_meta_path = run_dir / "03-work.meta.json"
    assert work_meta_path.exists()
    work_meta = json.loads(work_meta_path.read_text(encoding="utf-8"))
    assert work_meta["resume_safety"] == "fresh_run_required"
    assert work_meta["worker_cleanup"]["certainty"] == "uncertain"
    assert work_meta["worker_cleanup"]["known_survivors"] == [12345, 12346]
    assert work_meta["worker_cleanup"]["candidate_emitted"] is False
    assert work_meta["worker_cleanup"]["result_emitted"] is False

    # Repository must be untouched
    current_entry = gitstate.capture_entry(repository)
    assert current_entry.head == entry.head
    assert current_entry.tree == entry.tree
    assert not gitstate.dirty_paths(repository)


def test_worker_death_after_result_emitted_with_uncertain_cleanup(repository: Path, tmp_path: Path):
    # Case 48: Worker emitted result before dying, but uncertain_cleanup=True.
    # Must NOT classify as WORKER_TERMINATED_BEFORE_RESULT; classifies as WORKER_CLEANUP_FAILED.
    run_root = tmp_path / "runs"
    runner = WorkerDeathRunner(
        fail_at_work=False,
        work_stdout=b"Completed stage work successfully.\n",
        work_exit_code=0,
    )
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    def fake_drain_and_close(self, timeout_seconds=15.0):
        if "work" in self.parent_id:
            return {
                "uncertain_cleanup": True,
                "status": "stopping",
                "orphaned_pids": [12345],
            }
        return {"uncertain_cleanup": False, "status": "closed", "orphaned_pids": []}

    with patch.object(ParentLedger, "drain_and_close", fake_drain_and_close):
        with pytest.raises(DispatchError) as exc_info:
            d.dispatch(PHASE, REQUEST)

    assert exc_info.value.code == "WORKER_CLEANUP_FAILED"
    assert exc_info.value.code != "WORKER_TERMINATED_BEFORE_RESULT"


def test_worker_death_after_candidate_emitted_with_uncertain_cleanup(repository: Path, tmp_path: Path):
    # Case 49: Worker wrote candidate changes before dying with uncertain_cleanup=True.
    # Must NOT classify as WORKER_TERMINATED_BEFORE_RESULT; classifies as WORKER_CLEANUP_FAILED.
    run_root = tmp_path / "runs"
    runner = WorkerDeathRunner(
        fail_at_work=True,
        work_stdout=b"",
        work_exit_code=137,
        mutate_in_work=True,
    )
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    def fake_drain_and_close(self, timeout_seconds=15.0):
        if "work" in self.parent_id:
            return {
                "uncertain_cleanup": True,
                "status": "stopping",
                "orphaned_pids": [12345],
            }
        return {"uncertain_cleanup": False, "status": "closed", "orphaned_pids": []}

    with patch.object(ParentLedger, "drain_and_close", fake_drain_and_close):
        with pytest.raises(DispatchError) as exc_info:
            d.dispatch(PHASE, REQUEST)

    assert exc_info.value.code == "WORKER_CLEANUP_FAILED"
    assert exc_info.value.code != "WORKER_TERMINATED_BEFORE_RESULT"


def test_worker_failure_clean_cleanup_raises_process_failed(repository: Path, tmp_path: Path):
    # Case 50: Worker fails with non-zero exit code, but uncertain_cleanup is False.
    # Standard failure path (PROCESS_FAILED), not uncertain cleanup.
    run_root = tmp_path / "runs"
    runner = WorkerDeathRunner(
        fail_at_work=True,
        work_stdout=b"",
        work_exit_code=1,
    )
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    def fake_drain_and_close(self, timeout_seconds=15.0):
        return {"uncertain_cleanup": False, "status": "closed", "orphaned_pids": []}

    with patch.object(ParentLedger, "drain_and_close", fake_drain_and_close):
        with pytest.raises(DispatchError) as exc_info:
            d.dispatch(PHASE, REQUEST)

    assert exc_info.value.code in ("PROCESS_FAILED", "PROVIDER_TRANSPORT_FAILED")
    assert exc_info.value.code not in ("WORKER_TERMINATED_BEFORE_RESULT", "WORKER_CLEANUP_FAILED")


def test_resume_refused_on_fresh_run_required(repository: Path, tmp_path: Path):
    # Case 51: Attempting to resume a run where worker died with WORKER_TERMINATED_BEFORE_RESULT.
    # Must refuse resume because fresh_run_required.
    run_root = tmp_path / "runs"
    runner = WorkerDeathRunner(fail_at_work=True, work_stdout=b"", work_exit_code=137)
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    def fake_drain_and_close(self, timeout_seconds=15.0):
        if "work" in self.parent_id:
            return {
                "uncertain_cleanup": True,
                "status": "stopping",
                "orphaned_pids": [12345],
            }
        return {"uncertain_cleanup": False, "status": "closed", "orphaned_pids": []}

    with patch.object(ParentLedger, "drain_and_close", fake_drain_and_close):
        with pytest.raises(DispatchError):
            d.dispatch(PHASE, REQUEST)

    run_dirs = [p.parent for p in run_root.rglob("state.json")]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    # Attempt resume
    with pytest.raises(DispatchError) as exc_info:
        d.resume(PHASE, REQUEST, run_dir)

    assert exc_info.value.code == "WORKER_TERMINATED_BEFORE_RESULT"


def test_worker_death_preserves_prior_completed_stage_artifacts(repository: Path, tmp_path: Path):
    # Case 52: Prior stages (plan, plan_review) succeed; worker dies in stage 3 (work).
    # Prior stage artifacts and evidence are preserved in run directory.
    run_root = tmp_path / "runs"
    runner = WorkerDeathRunner(fail_at_work=True, work_stdout=b"", work_exit_code=137)
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    def fake_drain_and_close(self, timeout_seconds=15.0):
        if "work" in self.parent_id:
            return {
                "uncertain_cleanup": True,
                "status": "stopping",
                "orphaned_pids": [12345],
            }
        return {"uncertain_cleanup": False, "status": "closed", "orphaned_pids": []}

    with patch.object(ParentLedger, "drain_and_close", fake_drain_and_close):
        with pytest.raises(DispatchError):
            d.dispatch(PHASE, REQUEST)

    run_dirs = [p.parent for p in run_root.rglob("state.json")]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    # Plan stage artifacts exist
    assert (run_dir / "01-plan.stdout.md").exists()
    assert (run_dir / "01-plan.meta.json").exists()
    # Plan review stage artifacts exist
    assert (run_dir / "02-plan-review.stdout.md").exists()
    assert (run_dir / "02-plan-review.meta.json").exists()


def test_worker_death_custody_boundary_closed_cleanly(repository: Path, tmp_path: Path):
    # Case 53: Worker dies with uncertain cleanup; custody boundary is closed with ok=False,
    # leaving repository index and worktree completely clean.
    entry = gitstate.capture_entry(repository)
    run_root = tmp_path / "runs"
    runner = WorkerDeathRunner(fail_at_work=True, work_stdout=b"", work_exit_code=137)
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    def fake_drain_and_close(self, timeout_seconds=15.0):
        if "work" in self.parent_id:
            return {
                "uncertain_cleanup": True,
                "status": "stopping",
                "orphaned_pids": [12345],
            }
        return {"uncertain_cleanup": False, "status": "closed", "orphaned_pids": []}

    with patch.object(ParentLedger, "drain_and_close", fake_drain_and_close):
        with pytest.raises(DispatchError) as exc_info:
            d.dispatch(PHASE, REQUEST)

    assert exc_info.value.code == "WORKER_TERMINATED_BEFORE_RESULT"

    # Verify no uncommitted index changes or unstaged dirt
    res = git(repository, "status", "--porcelain")
    assert res == "", f"repository must be clean after failure: {res}"
    assert gitstate.current_head(repository) == entry.head


def test_worker_failure_with_retained_candidate_remains_resumable(repository: Path, tmp_path: Path):
    # Case 53: Worker failure with retained candidate changes does not require fresh run and remains resumable
    run_root = tmp_path / "runs"
    runner = WorkerDeathRunner(
        fail_at_work=True,
        work_stdout=b"",
        work_exit_code=137,
        mutate_in_work=True,
    )
    d = Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )

    def fake_drain_and_close(self, timeout_seconds=15.0):
        if "work" in self.parent_id:
            return {
                "uncertain_cleanup": True,
                "status": "stopping",
                "orphaned_pids": [12345],
            }
        return {"uncertain_cleanup": False, "status": "closed", "orphaned_pids": []}

    with patch.object(ParentLedger, "drain_and_close", fake_drain_and_close):
        with pytest.raises(DispatchError) as exc_info:
            d.dispatch(PHASE, REQUEST)

    assert exc_info.value.code == "WORKER_CLEANUP_FAILED"
    run_dirs = [p.parent for p in run_root.rglob("state.json")]
    assert len(run_dirs) == 1
    state = json.loads((run_dirs[0] / "state.json").read_text(encoding="utf-8"))
    assert state.get("resume_safety") != "fresh_run_required"
