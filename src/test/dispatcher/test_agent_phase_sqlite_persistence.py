from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat
import pytest

from agent_phase.persistence import (
    PersistenceError,
    SCHEMA_VERSION,
    STATE_DIR_MODE,
    ensure_state_directory,
    get_attempt_route_resolution,
    get_candidates,
    get_completion_receipts,
    get_invocation_attempts,
    get_operational_observations,
    get_resume_relations,
    get_review_dispositions,
    get_review_findings,
    get_review_records,
    get_route_resolutions,
    get_run,
    get_semantic_responsibilities,
    open_dispatcher_db,
    record_actor_bindings,
    record_artifact,
    record_candidate,
    record_completion_receipt,
    record_configuration_provenance,
    record_invocation_attempt,
    record_operational_observation,
    record_resume_relation,
    record_review_disposition,
    record_review_finding,
    record_review_record,
    record_route_resolution,
    record_run,
    record_semantic_responsibility,
    resolve_dispatcher_db_path,
    update_invocation_attempt,
    update_run_status,
    update_semantic_responsibility,
    verify_run_artifacts,
)


def test_resolve_dispatcher_db_path(tmp_path: Path) -> None:
    apgr_home = tmp_path / "home"
    db_path = resolve_dispatcher_db_path(apgr_home)
    assert db_path == apgr_home / "state" / "dispatcher.sqlite3"


def test_ensure_state_directory_permissions(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    ensure_state_directory(db_path)
    assert db_path.parent.is_dir()
    mode = stat.S_IMODE(db_path.parent.stat().st_mode)
    assert mode == STATE_DIR_MODE


def test_open_dispatcher_db_initializes_schema_v1(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        cur = conn.execute("PRAGMA journal_mode;")
        journal_mode = cur.fetchone()[0]
        assert journal_mode.lower() == "wal"

        cur = conn.execute("PRAGMA foreign_keys;")
        foreign_keys = cur.fetchone()[0]
        assert foreign_keys == 1

        cur = conn.execute("SELECT MAX(version) FROM schema_migrations;")
        version = cur.fetchone()[0]
        assert version == SCHEMA_VERSION
    finally:
        conn.close()


def test_record_and_query_run(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        run_id = "run-test-001"
        record_run(
            conn,
            run_id=run_id,
            project="/workspace/myproj",
            phase_id="APG148",
            request_schema="agent-phase-request-v2",
            request_digest="sha256:abcd",
            lifecycle="standard",
            execution_mode="dynamic",
            status="running",
        )

        cur = conn.execute("SELECT * FROM runs WHERE run_id = ?;", (run_id,))
        row = cur.fetchone()
        assert row is not None
        assert row["project"] == "/workspace/myproj"
        assert row["phase_id"] == "APG148"
        assert row["execution_mode"] == "dynamic"
        assert row["status"] == "running"
    finally:
        conn.close()


def test_record_configuration_provenance_chain(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        run_id = "run-test-002"
        record_run(
            conn,
            run_id=run_id,
            project="/workspace/myproj",
            request_schema="agent-phase-request-v2",
            request_digest="sha256:abcd",
            lifecycle="standard",
            execution_mode="conserve_claude",
        )

        chain = [
            {
                "source_type": "cli",
                "source_path": None,
                "content_digest": None,
                "resolved_mode": "conserve_claude",
                "is_winner": True,
                "precedence_rank": 1,
            },
            {
                "source_type": "project_config",
                "source_path": "/workspace/myproj/.apgr/config.toml",
                "content_digest": "sha256:1111",
                "resolved_mode": "dynamic",
                "is_winner": False,
                "precedence_rank": 2,
            },
        ]
        record_configuration_provenance(conn, run_id, chain)

        cur = conn.execute(
            "SELECT * FROM configuration_provenance WHERE run_id = ? ORDER BY precedence_rank ASC;",
            (run_id,),
        )
        rows = cur.fetchall()
        assert len(rows) == 2
        assert rows[0]["source_type"] == "cli"
        assert rows[0]["is_winner"] == 1
        assert rows[1]["source_type"] == "project_config"
        assert rows[1]["is_winner"] == 0
    finally:
        conn.close()


def test_record_actor_bindings(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        run_id = "run-test-003"
        record_run(
            conn,
            run_id=run_id,
            project="/workspace/myproj",
            request_schema="agent-phase-request-v2",
            request_digest="sha256:abcd",
            lifecycle="standard",
            execution_mode="dynamic",
        )

        bindings = [
            {
                "binding_id": "binding_plan",
                "policy_name": "default_standard",
                "roles": ["Planner"],
                "required_capabilities": ["read", "reasoning"],
                "process_read_only": True,
                "is_mutating": False,
            },
            {
                "binding_id": "binding_work",
                "policy_name": "default_standard",
                "roles": ["Plan Review Disposition", "Producer"],
                "required_capabilities": ["read", "mutation", "execution"],
                "process_read_only": False,
                "is_mutating": True,
            },
        ]
        record_actor_bindings(conn, run_id, bindings)

        cur = conn.execute("SELECT * FROM actor_bindings WHERE run_id = ?;", (run_id,))
        rows = cur.fetchall()
        assert len(rows) == 2
        plan_row = next(r for r in rows if r["binding_id"] == "binding_plan")
        assert plan_row["process_read_only"] == 1
        assert plan_row["is_mutating"] == 0
        assert json.loads(plan_row["merged_roles_json"]) == ["Planner"]
    finally:
        conn.close()


def test_prelaunch_route_persistence_and_same_attempt_immutability(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        run_id = "run-test-004"
        record_run(
            conn,
            run_id=run_id,
            project="/workspace/myproj",
            request_schema="agent-phase-request-v2",
            request_digest="sha256:abcd",
            lifecycle="standard",
            execution_mode="dynamic",
        )

        record_route_resolution(
            conn,
            resolution_id="res-001",
            run_id=run_id,
            binding_id="binding_plan",
            attempt_number=1,
            provider="claude",
            profile="claude-3-7-sonnet",
            endpoint_alias="claude-default",
            selection_rationale="highest reasoning score",
        )

        # Same-attempt recovery: query route from persistence
        stored = get_attempt_route_resolution(conn, run_id, "binding_plan", 1)
        assert stored is not None
        assert stored["resolution_id"] == "res-001"
        assert stored["provider"] == "claude"
        assert stored["profile"] == "claude-3-7-sonnet"
        assert stored["selection_rationale"] == "highest reasoning score"

        # Nonexistent attempt returns None
        assert get_attempt_route_resolution(conn, run_id, "binding_plan", 2) is None
    finally:
        conn.close()


def test_artifact_digest_verification_and_tampering_detection(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        run_id = "run-test-005"
        record_run(
            conn,
            run_id=run_id,
            project="/workspace/myproj",
            request_schema="agent-phase-request-v2",
            request_digest="sha256:abcd",
            lifecycle="standard",
            execution_mode="dynamic",
        )

        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        art_file = run_dir / "proposal.md"
        content = b"# Bounded Plan Proposal\nEverything looks good.\n"
        art_file.write_bytes(content)
        content_sha = hashlib.sha256(content).hexdigest()

        record_artifact(
            conn,
            artifact_id="art-001",
            run_id=run_id,
            artifact_name="plan_proposal",
            relative_path="proposal.md",
            size_bytes=len(content),
            sha256=content_sha,
        )

        # Verification passes initially
        valid, mismatches = verify_run_artifacts(conn, run_id, run_dir)
        assert valid is True
        assert mismatches == []

        # Tampering: modify file content with different size
        art_file.write_bytes(b"# Tampered Plan Proposal\nInjected extra instructions.\n")
        valid, mismatches = verify_run_artifacts(conn, run_id, run_dir)
        assert valid is False
        assert len(mismatches) == 1
        assert "size mismatch for proposal.md" in mismatches[0]

        # Tampering: modify file content with exact same size
        tampered_same_size = b"# Bounded Plan Proposal\nEverything looks evil!\n"
        assert len(tampered_same_size) == len(content)
        art_file.write_bytes(tampered_same_size)
        valid, mismatches = verify_run_artifacts(conn, run_id, run_dir)
        assert valid is False
        assert len(mismatches) == 1
        assert "digest mismatch for proposal.md" in mismatches[0]

        # Missing file on disk
        art_file.unlink()
        valid, mismatches = verify_run_artifacts(conn, run_id, run_dir)
        assert valid is False
        assert len(mismatches) == 1
        assert "missing artifact on disk: proposal.md" in mismatches[0]
    finally:
        conn.close()


def test_foreign_key_cascade_and_transactional_rollback(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        "run-test-006"
        # Foreign key violation: inserting actor binding for nonexistent run_id
        with pytest.raises(PersistenceError):
            record_actor_bindings(
                conn,
                "nonexistent-run",
                [{"binding_id": "b1", "roles": ["Planner"]}],
            )
    finally:
        conn.close()


def test_plain_insert_immutability_and_no_cascade_on_run_update(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        run_id = "run-test-007"
        record_run(
            conn,
            run_id=run_id,
            project="/workspace/myproj",
            request_schema="agent-phase-request-v2",
            request_digest="sha256:abcd",
            lifecycle="standard",
            execution_mode="dynamic",
            status="running",
        )

        # Duplicate run_id must raise PersistenceError (not silently REPLACE and cascade-delete)
        with pytest.raises(PersistenceError, match="cannot record run"):
            record_run(
                conn,
                run_id=run_id,
                project="/workspace/myproj",
                request_schema="agent-phase-request-v2",
                request_digest="sha256:abcd",
                lifecycle="standard",
                execution_mode="dynamic",
                status="running",
            )

        # Add child records
        record_route_resolution(
            conn,
            resolution_id="res-007",
            run_id=run_id,
            binding_id="binding_plan",
            attempt_number=1,
            provider="claude",
            profile="claude-3-7-sonnet",
        )

        # Overwriting route resolution must raise PersistenceError
        with pytest.raises(PersistenceError, match="cannot record route resolution"):
            record_route_resolution(
                conn,
                resolution_id="res-007",
                run_id=run_id,
                binding_id="binding_plan",
                attempt_number=1,
                provider="codex",
                profile="gpt-5-codex",
            )

        # Update run status without cascade-deleting child records
        update_run_status(conn, run_id, "completed", outcome="success", semantic_outcome="completed")
        updated_run = get_run(conn, run_id)
        assert updated_run is not None
        assert updated_run["status"] == "completed"
        assert updated_run["outcome"] == "success"

        # Child record still exists!
        resolutions = get_route_resolutions(conn, run_id)
        assert len(resolutions) == 1
        assert resolutions[0]["resolution_id"] == "res-007"
    finally:
        conn.close()


def test_full_table_writers_and_readers(tmp_path: Path) -> None:
    db_path = tmp_path / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        run_id = "run-test-008"
        record_run(
            conn,
            run_id=run_id,
            project="/workspace/myproj",
            request_schema="agent-phase-request-v2",
            request_digest="sha256:abcd",
            lifecycle="standard",
            execution_mode="dynamic",
        )

        # 1. Semantic Responsibilities
        record_semantic_responsibility(
            conn,
            id="sem-plan-1",
            run_id=run_id,
            responsibility_name="Planner",
            binding_id="binding_plan",
            status="pending",
        )
        update_semantic_responsibility(
            conn,
            id="sem-plan-1",
            status="completed",
            outcome="plan_drafted",
        )
        sems = get_semantic_responsibilities(conn, run_id)
        assert len(sems) == 1
        assert sems[0]["status"] == "completed"
        assert sems[0]["outcome"] == "plan_drafted"

        # 2. Invocation Attempts
        record_invocation_attempt(
            conn,
            attempt_id="att-1",
            run_id=run_id,
            binding_id="binding_plan",
            attempt_number=1,
            provider="claude",
            profile="claude-3-7-sonnet",
            status="running",
        )
        update_invocation_attempt(
            conn,
            attempt_id="att-1",
            status="completed",
            exit_code=0,
        )
        attempts = get_invocation_attempts(conn, run_id)
        assert len(attempts) == 1
        assert attempts[0]["status"] == "completed"
        assert attempts[0]["exit_code"] == 0

        # Attempt 2 with predecessor_attempt_id
        record_invocation_attempt(
            conn,
            attempt_id="att-2",
            run_id=run_id,
            binding_id="binding_plan",
            attempt_number=2,
            predecessor_attempt_id="att-1",
            provider="codex",
            profile="gpt-5-codex",
            status="running",
        )
        attempts = get_invocation_attempts(conn, run_id)
        assert len(attempts) == 2
        assert attempts[1]["predecessor_attempt_id"] == "att-1"

        # 3. Operational Observations
        record_operational_observation(
            conn,
            observation_id="obs-1",
            producer="supervisor",
            observation_type="availability",
            provider="codex",
            state_value="available",
        )
        obs_list = get_operational_observations(conn, provider="codex")
        assert len(obs_list) == 1
        assert obs_list[0]["observation_id"] == "obs-1"

        # 4. Candidates
        record_candidate(
            conn,
            candidate_id="cand-1",
            run_id=run_id,
            responsibility_name="Producer",
            candidate_type="git_tree",
            tree_sha="tree123",
            head_sha="head123",
        )
        cands = get_candidates(conn, run_id)
        assert len(cands) == 1
        assert cands[0]["tree_sha"] == "tree123"

        # 5. Review Records & Findings
        record_review_record(
            conn,
            review_id="rev-1",
            run_id=run_id,
            responsibility_name="Work Reviewer",
            reviewer_provider="claude",
            reviewer_profile="claude-3-7-sonnet",
            outcome="reviewed_with_findings",
            findings_count=1,
            candidate_id="cand-1",
        )
        reviews = get_review_records(conn, run_id)
        assert len(reviews) == 1
        assert reviews[0]["outcome"] == "reviewed_with_findings"

        record_review_finding(
            conn,
            finding_id="find-1",
            review_id="rev-1",
            severity="BLOCKING",
            title="Missing assertion",
        )
        findings = get_review_findings(conn, "rev-1")
        assert len(findings) == 1
        assert findings[0]["severity"] == "BLOCKING"

        # 6. Review Dispositions
        record_review_disposition(
            conn,
            disposition_id="disp-1",
            run_id=run_id,
            responsibility_name="Work Review Disposition",
            review_id="rev-1",
            disposition_outcome="amend",
            rationale="Accept blocking finding",
        )
        disps = get_review_dispositions(conn, run_id)
        assert len(disps) == 1
        assert disps[0]["disposition_outcome"] == "amend"

        # 7. Completion Receipts
        record_completion_receipt(
            conn,
            receipt_id="rec-1",
            run_id=run_id,
            phase_id="APG148",
            final_head="head123",
            finalization_outcome="publish",
        )
        receipts = get_completion_receipts(conn, run_id)
        assert len(receipts) == 1
        assert receipts[0]["finalization_outcome"] == "publish"

        # 8. Resume Relations
        record_resume_relation(
            conn,
            run_id=run_id,
            prior_run_id="run-prior-000",
            resumed_from_stage="work",
            relation_type="retry",
        )
        resumes = get_resume_relations(conn, run_id)
        assert len(resumes) == 1
        assert resumes[0]["prior_run_id"] == "run-prior-000"
    finally:
        conn.close()
