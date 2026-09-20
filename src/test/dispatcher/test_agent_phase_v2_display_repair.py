"""Deterministic regression tests for Request V2 live-display contract and pre-launch reconciliation.

Validates APGR V0120-E-REPAIR1 requirements:
1. Default five-binding V2 policy reaches runner without TypeError with Display enabled.
2. Unmerged 8-binding policy displays correct indices and stage_count.
3. Merged role label is deterministic and contains bound semantic responsibilities.
4. Display remains observational (disabled or broken stream does not alter dispatcher truth).
5. Deliberate exception at display/pre-launch boundary marks run failed.
6. Persisted attempt is not left 'running' on pre-launch failure (marked 'failed_pre_launch', exit_code None).
7. Semantic responsibilities are not left 'running' (active marked 'failed_pre_launch', remaining 'pending').
8. No provider-launch receipt or candidate is fabricated.
9. Route-resolution provenance is retained.
10. KeyboardInterrupt at pre-launch boundary leaves attempt terminalized, not 'running'.
"""

from __future__ import annotations

import io
from typing import TextIO, cast
import json
from pathlib import Path
import subprocess
from typing import Any
import pytest

from agent_phase import result as result_module
from agent_phase.display import Display
from agent_phase.persistence import (
    get_attempt_route_resolution,
    get_candidates,
    get_completion_receipts,
    get_invocation_attempts,
    get_semantic_responsibilities,
    open_dispatcher_db,
    resolve_dispatcher_db_path,
)
from agent_phase.request import parse_request_v2
from agent_phase.semantic_roles import (
    create_default_binding_policy,
    create_unmerged_binding_policy,
)
from agent_phase.v2_dispatch import V2DispatchError, dispatch_v2


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    (path / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)
    remote = path.parent / "remote.git"
    if not remote.exists():
        subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(path), "push", "-q", "--set-upstream", "origin", "HEAD"], check=True)
    return path


def _make_v2_request_bytes(
    phase_type: str = "implementation_testing",
    prompt: str = "Implement display repair",
) -> bytes:
    payload = {
        "schema": "agent-phase-request-v2",
        "phase_type": phase_type,
        "prompt": prompt,
    }
    return json.dumps(payload).encode("utf-8")


def _make_closeout_output(
    nonce: str,
    outcome: str = "completed",
    body: str = "Closeout complete.",
    commit_message: dict[str, str] | None = None,
) -> bytes:
    begin, end = result_module.markers(nonce)
    msg = commit_message or {
        "subject": "Implement requested changes",
        "body": "Add implementation files and updates.",
    }
    payload = {
        "version": 1,
        "stage": "closeout",
        "outcome": outcome,
        "body": body,
        "commit_message": msg,
    }
    return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")


class RecordingStream(io.StringIO):
    """In-memory stream capturing emitted lines for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.recorded_lines: list[str] = []

    def write(self, s: str) -> int:
        for line in s.splitlines():
            if line.strip():
                self.recorded_lines.append(line)
        return super().write(s)


class BrokenStream:
    """Stream that raises OSError on write to simulate broken terminal stderr."""

    def write(self, s: str) -> int:
        raise OSError("Simulated broken pipe")

    def flush(self) -> None:
        pass


def test_default_five_binding_with_display_reaches_runner(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"

    stream = RecordingStream()
    display = Display(stream, enabled=True)
    turns_executed: list[str] = []

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        turns_executed.append(binding.binding_id)
        if binding.binding_id == "binding_work":
            (repo / "file.txt").write_text("modified\n", encoding="utf-8")
        elif binding.binding_id in ("binding_closeout", "binding_closeout_agent") and nonce:
            return _make_closeout_output(nonce)
        return None

    res = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
        outbox_root=tmp_path / "outbox",
        display=display,
        runner=mock_runner,
    )
    display.close()

    assert res["status"] == "completed"
    assert len(turns_executed) == 5

    output = "\n".join(stream.recorded_lines)
    assert "[1/5] binding_plan — Planner " in output
    assert "[2/5] binding_plan_review — Plan Reviewer " in output
    assert "[3/5] binding_work — Plan Review Disposition, Producer " in output
    assert "[4/5] binding_work_review — Work Reviewer " in output
    assert "[5/5] binding_closeout — Work Review Disposition, Reviser, Closeout Agent " in output
    assert "[binding_plan] complete — exit 0 in " in output
    assert "[binding_closeout] complete — exit 0 in " in output


def test_unmerged_eight_binding_display_counts(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"

    stream = RecordingStream()
    display = Display(stream, enabled=True)
    turns_executed: list[str] = []

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        turns_executed.append(binding.binding_id)
        if "producer" in binding.binding_id:
            (repo / "file.txt").write_text("modified\n", encoding="utf-8")
        elif binding.binding_id in ("binding_closeout", "binding_closeout_agent") and nonce:
            return _make_closeout_output(nonce)
        return None

    res = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        binding_policy=create_unmerged_binding_policy(),
        apgr_home=home,
        outbox_root=tmp_path / "outbox",
        display=display,
        runner=mock_runner,
    )
    display.close()

    assert res["status"] == "completed"
    assert len(turns_executed) == 8

    output = "\n".join(stream.recorded_lines)
    for i in range(1, 9):
        assert f"[{i}/8]" in output


def test_merged_role_label_determinism() -> None:
    policy = create_default_binding_policy()
    work_binding = next(b for b in policy.bindings if b.binding_id == "binding_work")
    closeout_binding = next(b for b in policy.bindings if b.binding_id == "binding_closeout")

    # Assert exact deterministic rendering repeatedly
    for _ in range(10):
        work_label = ", ".join(work_binding.roles)
        closeout_label = ", ".join(closeout_binding.roles)
        assert work_label == "Plan Review Disposition, Producer"
        assert closeout_label == "Work Review Disposition, Reviser, Closeout Agent"


def test_display_observational_invariance(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        if binding.binding_id == "binding_work":
            (repo / "file.txt").write_text("updated\n", encoding="utf-8")
        elif binding.binding_id in ("binding_closeout", "binding_closeout_agent") and nonce:
            return _make_closeout_output(nonce)
        return None

    # 1. display=None
    home1 = tmp_path / "home1"
    res1 = dispatch_v2(root, repo, req, raw, execution_mode="dynamic", apgr_home=home1, outbox_root=tmp_path / "outbox1", display=None, runner=mock_runner)
    assert res1["status"] == "completed"

    # 2. Disabled display
    home2 = tmp_path / "home2"
    disp2 = Display(None, enabled=False)
    res2 = dispatch_v2(root, repo, req, raw, execution_mode="dynamic", apgr_home=home2, outbox_root=tmp_path / "outbox2", display=disp2, runner=mock_runner)
    disp2.close()
    assert res2["status"] == "completed"

    # 3. Broken stream (raises OSError)
    home3 = tmp_path / "home3"
    disp3 = Display(cast(TextIO, BrokenStream()), enabled=True)
    res3 = dispatch_v2(root, repo, req, raw, execution_mode="dynamic", apgr_home=home3, outbox_root=tmp_path / "outbox3", display=disp3, runner=mock_runner)
    disp3.close()
    assert res3["status"] == "completed"


class CrashingDisplay(Display):
    def stage_started(self, index: int, stage: str, role: str, endpoint: Any, stage_count: int = 5) -> None:
        raise RuntimeError("deliberate pre-launch display crash")


def test_prelaunch_display_exception_reconciliation(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    runner_called: list[str] = []

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> None:
        runner_called.append(binding.binding_id)

    crashing_display = CrashingDisplay(None, enabled=True)

    with pytest.raises(V2DispatchError, match="Turn execution failed:.*deliberate pre-launch display crash"):
        dispatch_v2(
            root,
            repo,
            req,
            raw,
            execution_mode="dynamic",
            apgr_home=home,
            display=crashing_display,
            runner=mock_runner,
        )

    # Invariant checks
    assert runner_called == [], "Provider runner must never be called on pre-launch failure"

    conn = open_dispatcher_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT run_id, status, outcome, semantic_outcome FROM runs;")
    runs = cur.fetchall()
    assert len(runs) == 1
    run_id, r_status, r_outcome, r_sem_outcome = runs[0]
    assert r_status == "failed"
    assert r_outcome == "failed_pre_launch"
    assert r_sem_outcome == "failed_pre_launch"

    # Persisted attempt is not left 'running'
    attempts = get_invocation_attempts(conn, run_id)
    assert len(attempts) == 1
    att = attempts[0]
    assert att["status"] == "failed_pre_launch"
    assert att["exit_code"] is None
    assert att["completed_at"] is not None

    # Semantic responsibilities are not left 'running'
    responsibilities = get_semantic_responsibilities(conn, run_id)
    assert len(responsibilities) == 8
    for r in responsibilities:
        if r["responsibility_name"] == "Planner":
            assert r["status"] == "failed"
            assert r["outcome"] == "failed_pre_launch"
            assert r["completed_at"] is not None
        else:
            assert r["status"] == "pending"
            assert r["completed_at"] is None

    # No provider-launch receipt or result fabricated
    assert get_completion_receipts(conn, run_id) == []
    assert get_candidates(conn, run_id) == []

    # Route resolution provenance retained
    persisted_route = get_attempt_route_resolution(conn, run_id, "binding_plan", 1)
    assert persisted_route is not None
    assert persisted_route["provider"] != ""
    assert persisted_route["profile"] != ""
    conn.close()


class InterruptDisplay(Display):
    def stage_started(self, index: int, stage: str, role: str, endpoint: Any, stage_count: int = 5) -> None:
        raise KeyboardInterrupt("Simulated operator interrupt")


def test_keyboard_interrupt_reconciles_attempt(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> None:
        pass

    interrupt_display = InterruptDisplay(None, enabled=True)

    with pytest.raises(KeyboardInterrupt):
        dispatch_v2(
            root,
            repo,
            req,
            raw,
            execution_mode="dynamic",
            apgr_home=home,
            display=interrupt_display,
            runner=mock_runner,
        )

    conn = open_dispatcher_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT run_id, status, outcome, semantic_outcome FROM runs;")
    row = cur.fetchone()
    assert row is not None
    run_id, r_status, r_outcome, r_sem_outcome = row
    assert r_status == "failed"
    assert r_outcome == "operator_interrupted"
    assert r_sem_outcome == "operator_interrupted"

    attempts = get_invocation_attempts(conn, run_id)
    assert len(attempts) == 1
    assert attempts[0]["status"] == "failed_pre_launch"
    assert attempts[0]["exit_code"] is None
    assert attempts[0]["completed_at"] is not None
    conn.close()


def test_invariant_14_prelaunch_failure_reconciles_run_and_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    monkeypatch.setattr("agent_phase.v2_turns.get_attempt_route_resolution", lambda *args, **kwargs: None)

    with pytest.raises(V2DispatchError, match="Turn execution failed:.*invariant violation: route was not persisted before launch"):
        dispatch_v2(root, repo, req, raw, execution_mode="dynamic", apgr_home=home, runner=lambda **kw: None)

    conn = open_dispatcher_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT run_id, status, outcome, semantic_outcome FROM runs;")
    run_id, r_status, r_outcome, r_sem_outcome = cur.fetchone()
    assert r_status == "failed"
    assert r_outcome == "failed_pre_launch"
    assert r_sem_outcome == "failed_pre_launch"

    attempts = get_invocation_attempts(conn, run_id)
    assert len(attempts) == 1
    assert attempts[0]["status"] == "failed_pre_launch"
    assert attempts[0]["exit_code"] is None
    conn.close()


def test_staged_mode_preserves_truthful_pending_statuses(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    res = dispatch_v2(root, repo, req, raw, execution_mode="dynamic", apgr_home=home, runner=None)
    assert res["status"] == "staged_pre_launch"

    conn = open_dispatcher_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT run_id, status FROM runs;")
    run_id, r_status = cur.fetchone()
    assert r_status == "staged"

    attempts = get_invocation_attempts(conn, run_id)
    assert len(attempts) == 5
    for att in attempts:
        assert att["status"] == "staged"
        assert att["completed_at"] is None

    responsibilities = get_semantic_responsibilities(conn, run_id)
    assert len(responsibilities) == 8
    for r in responsibilities:
        assert r["status"] == "pending"
        assert r["completed_at"] is None
    conn.close()
