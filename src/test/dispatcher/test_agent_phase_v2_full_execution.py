"""Comprehensive qualification test suite for full Request V2 multi-turn execution.

Exercises:
- Complete V2 five-turn happy path with all 8 semantic responsibilities.
- SQLite persistence of actor bindings, attempts, candidates, reviews, dispositions, artifacts, and completion receipts.
- Unmerged 8-turn execution topology.
- Plan amend path with review findings and disposition.
- Work revision path with Reviser candidate creation.
- Plan rejection path blocking subsequent mutating turn.
- Read-only turn mutation detection.
- Non-zero provider exit code failure handling.
- Capability union across merged turns.
- Resume relation recording.
- Same-attempt route pinning.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any
import zipfile
import pytest

from agent_phase import result as result_module, review_result
from agent_phase.persistence import (
    get_attempt_route_resolution,
    get_candidates,
    get_completion_receipts,
    get_invocation_attempts,
    get_resume_relations,
    get_review_dispositions,
    get_review_records,
    get_semantic_responsibilities,
    open_dispatcher_db,
    resolve_dispatcher_db_path,
)
from agent_phase.provider import Result
from agent_phase.request import parse_request_v2
from agent_phase.semantic_roles import (
    CANONICAL_RESPONSIBILITIES,
    ROLE_PLAN_REVIEW_DISPOSITION,
    ROLE_PRODUCER,
    ActorBinding,
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
    prompt: str = "Implement operational parity hardening",
) -> bytes:
    payload = {
        "schema": "agent-phase-request-v2",
        "phase_type": phase_type,
        "prompt": prompt,
    }
    return json.dumps(payload).encode("utf-8")


def _make_review_output(nonce: str, stage: str, outcome: str, body: str) -> bytes:
    begin, end = review_result.markers(nonce)
    payload = {"version": 1, "stage": stage, "outcome": outcome, "body": body}
    return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")


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


def test_v2_full_five_turn_happy_path(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    turns_executed: list[str] = []

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        turns_executed.append(binding.binding_id)
        if binding.binding_id == "binding_work":
            (repo / "work_output.txt").write_text("work complete\n", encoding="utf-8")
        elif binding.binding_id == "binding_closeout" and nonce:
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
        runner=mock_runner,
    )

    assert res["status"] == "completed"
    assert "archive_path" in res
    assert Path(res["archive_path"]).exists()
    assert zipfile.is_zipfile(res["archive_path"])

    assert turns_executed == [
        "binding_plan",
        "binding_plan_review",
        "binding_work",
        "binding_work_review",
        "binding_closeout",
    ]

    conn = open_dispatcher_db(db_path)
    # Verify all 5 invocation attempts completed
    attempts = get_invocation_attempts(conn, res["run_id"])
    assert len(attempts) == 5
    assert all(a["status"] == "completed" for a in attempts)

    # Verify all 8 semantic responsibilities completed
    responsibilities = get_semantic_responsibilities(conn, res["run_id"])
    assert len(responsibilities) == 8
    assert all(r["status"] == "completed" for r in responsibilities)
    resp_names = {r["responsibility_name"] for r in responsibilities}
    assert resp_names == set(CANONICAL_RESPONSIBILITIES)

    # Verify candidates recorded
    candidates = get_candidates(conn, res["run_id"])
    assert len(candidates) >= 2  # plan candidate and work candidate

    # Verify reviews and dispositions
    reviews = get_review_records(conn, res["run_id"])
    assert len(reviews) == 2  # plan review and work review
    assert all(r["outcome"] == "reviewed_with_no_findings" for r in reviews)

    dispositions = get_review_dispositions(conn, res["run_id"])
    assert len(dispositions) == 2  # plan disposition and work disposition
    assert all(d["disposition_outcome"] == "accept" for d in dispositions)

    # Verify completion receipt
    receipts = get_completion_receipts(conn, res["run_id"])
    assert len(receipts) == 1
    assert receipts[0]["finalization_outcome"] == "completed"

    conn.close()


def test_v2_plan_amend_path(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    def amend_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        if binding.binding_id == "binding_plan_review" and nonce:
            body = "- F1: Plan should clarify database recovery\n- F2: Plan should include SQLite lock verification"
            return _make_review_output(nonce, "plan_review", "reviewed_with_findings", body)
        if binding.binding_id == "binding_work":
            (repo / "amended_output.txt").write_text("amended implementation\n", encoding="utf-8")
        if binding.binding_id == "binding_closeout" and nonce:
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
        runner=amend_runner,
    )
    assert res["status"] == "completed"

    conn = open_dispatcher_db(db_path)
    reviews = get_review_records(conn, res["run_id"])
    plan_rev = next(r for r in reviews if r["responsibility_name"] == "plan_reviewer")
    assert plan_rev["outcome"] == "reviewed_with_findings"
    assert plan_rev["findings_count"] == 2

    # Verify findings recorded in review_findings table
    cur = conn.cursor()
    cur.execute("SELECT * FROM review_findings WHERE review_id = ?", (plan_rev["review_id"],))
    findings = cur.fetchall()
    assert len(findings) == 2

    # Verify disposition was recorded as 'amend'
    dispositions = get_review_dispositions(conn, res["run_id"])
    plan_disp = next(d for d in dispositions if d["responsibility_name"] == "plan_review_disposition")
    assert plan_disp["disposition_outcome"] == "amend"
    conn.close()


def test_v2_work_revision_path(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    def revision_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        if binding.binding_id == "binding_work":
            (repo / "feature.txt").write_text("initial producer code\n", encoding="utf-8")
        elif binding.binding_id == "binding_work_review" and nonce:
            body = "- F1: Needs documentation for new feature\n- F2: Needs test assertion"
            return _make_review_output(nonce, "final_review", "reviewed_with_findings", body)
        elif binding.binding_id == "binding_closeout":
            # Reviser applies changes in closeout turn
            (repo / "feature.txt").write_text("revised code with docs and tests\n", encoding="utf-8")
            if nonce:
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
        runner=revision_runner,
    )
    assert res["status"] == "completed"

    conn = open_dispatcher_db(db_path)
    reviews = get_review_records(conn, res["run_id"])
    work_rev = next(r for r in reviews if r["responsibility_name"] == "work_reviewer")
    assert work_rev["outcome"] == "reviewed_with_findings"
    assert work_rev["findings_count"] == 2

    dispositions = get_review_dispositions(conn, res["run_id"])
    work_disp = next(d for d in dispositions if d["responsibility_name"] == "work_review_disposition")
    assert work_disp["disposition_outcome"] == "amend"

    # Verify reviser candidate was created and persisted
    candidates = get_candidates(conn, res["run_id"])
    reviser_cands = [c for c in candidates if c["responsibility_name"] == "reviser"]
    assert len(reviser_cands) == 1
    assert reviser_cands[0]["candidate_id"] == f"cand-{res['run_id']}-revision"
    conn.close()


def test_v2_plan_rejection_blocks_mutating_work(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    def rejecting_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        if binding.binding_id == "binding_plan_review" and nonce:
            return _make_review_output(nonce, "plan_review", "unreviewable", "Plan is structurally empty or nonsensical")
        return None

    with pytest.raises(V2DispatchError, match="Plan review rejected proposed plan"):
        dispatch_v2(
            root,
            repo,
            req,
            raw,
            execution_mode="dynamic",
            apgr_home=home,
            runner=rejecting_runner,
        )

    conn = open_dispatcher_db(db_path)
    # Verify Producer attempt was marked failed and no producer candidate was created
    cur = conn.cursor()
    cur.execute("SELECT attempt_id, binding_id, status FROM invocation_attempts")
    attempts = cur.fetchall()
    work_attempts = [a for a in attempts if a[1] == "binding_work"]
    assert len(work_attempts) == 1 and work_attempts[0][2] == "failed"
    cur.execute("SELECT * FROM candidates WHERE responsibility_name = 'producer'")
    assert cur.fetchall() == []
    conn.close()


def test_v2_readonly_mutation_fails(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"

    def mutating_reviewer(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> None:
        if binding.binding_id == "binding_plan_review":
            (repo / "illegal_mutation.txt").write_text("mutated during read only!\n", encoding="utf-8")

    with pytest.raises(V2DispatchError, match="mutated worktree"):
        dispatch_v2(
            root,
            repo,
            req,
            raw,
            execution_mode="dynamic",
            apgr_home=home,
            runner=mutating_reviewer,
        )


def test_v2_provider_exit_code_failure_handling(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    def failing_runner(argv: list[str], prompt: bytes, cwd: Path, max_output: int, on_output=None) -> Result:
        return Result(
            exit_code=127,
            stdout=b"",
            stderr=b"executable not found\n",
            truncated=False,
            started=0.0,
            ended=0.0,
        )

    with pytest.raises(V2DispatchError, match="failed before substantive output"):
        dispatch_v2(
            root,
            repo,
            req,
            raw,
            execution_mode="dynamic",
            apgr_home=home,
            runner=failing_runner,
        )

    conn = open_dispatcher_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status, exit_code FROM invocation_attempts")
    rows = cur.fetchall()
    assert len(rows) >= 1
    assert rows[0][0] == "failed"
    assert rows[0][1] == 127
    conn.close()


def test_v2_unmerged_discrete_eight_turns(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    unmerged_policy = create_unmerged_binding_policy()
    turns_executed: list[str] = []

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        turns_executed.append(binding.binding_id)
        if "producer" in binding.binding_id:
            (repo / "file.txt").write_text("producer output\n", encoding="utf-8")
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
        runner=mock_runner,
        binding_policy=unmerged_policy,
    )

    assert res["status"] == "completed"
    assert len(turns_executed) == 8

    conn = open_dispatcher_db(db_path)
    attempts = get_invocation_attempts(conn, res["run_id"])
    assert len(attempts) == 8
    assert all(a["status"] == "completed" for a in attempts)
    conn.close()


def test_v2_merged_responsibility_capability_union() -> None:
    binding = ActorBinding.create("binding_work", (ROLE_PLAN_REVIEW_DISPOSITION, ROLE_PRODUCER))
    assert binding.is_mutating is True
    assert binding.process_read_only is False
    assert "mutation" in binding.required_capabilities
    assert "read" in binding.required_capabilities
    assert "execution" in binding.required_capabilities


def test_v2_resume_relations_recorded(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    prior_run_id = "prior-run-12345"

    res = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
        resume_from_run_id=prior_run_id,
        dry_run=True,
    )

    conn = open_dispatcher_db(db_path)
    resume_rels = get_resume_relations(conn, res["run_id"])
    conn.close()

    assert len(resume_rels) == 1
    assert resume_rels[0]["prior_run_id"] == prior_run_id
    assert resume_rels[0]["relation_type"] == "retry"


def test_v2_same_attempt_route_pinning(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    # Initial staged run
    res1 = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
    )
    initial_route = res1["selected_route"]

    conn = open_dispatcher_db(db_path)
    persisted = get_attempt_route_resolution(conn, res1["run_id"], "binding_plan", 1)
    conn.close()

    assert persisted is not None
    assert persisted["endpoint_alias"] == initial_route["endpoint_alias"]
    assert persisted["provider"] == initial_route["provider"]
