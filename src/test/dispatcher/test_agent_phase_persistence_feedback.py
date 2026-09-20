"""Unit tests for SQLite persistence feedback, digest stability, and schema v2 relations."""

from __future__ import annotations

from pathlib import Path
import sqlite3
import time
import pytest

from agent_phase.persistence import (
    PersistenceError,
    SCHEMA_VERSION,
    open_dispatcher_db,
    record_actor_bindings,
    record_invocation_attempt,
    record_operational_observation,
    record_run,
    record_semantic_responsibility,
    update_semantic_responsibility,
    get_semantic_responsibilities,
)
from agent_phase.persistence_feedback import (
    get_active_operational_observations,
    get_invocation_observation_relations,
    record_invocation_observation_relation,
)
from agent_phase.probes import compute_observation_digest
from agent_phase.semantic_roles import SEMANTIC_RESPONSIBILITY_STATUSES


def _setup_db(tmp_path: Path) -> sqlite3.Connection:
    db_file = tmp_path / "test_dispatcher.sqlite3"
    return open_dispatcher_db(db_file)


def test_schema_migration_v2_creates_tables(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    assert SCHEMA_VERSION >= 2

    cur = conn.execute("SELECT MAX(version) FROM schema_migrations;")
    assert cur.fetchone()[0] == 2

    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='invocation_observation_relations';"
    )
    assert cur.fetchone() is not None


def test_record_and_query_invocation_observation_relation(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    run_id = "run-feedback-1"
    record_run(
        conn,
        run_id=run_id,
        project="apgr",
        request_schema="agent-phase-request-v2",
        request_digest="dig-123",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    binding_id = "binding_plan"
    record_actor_bindings(
        conn,
        run_id=run_id,
        bindings=[{
            "binding_id": binding_id,
            "policy_name": "default",
            "roles": ["planner"],
            "required_capabilities": ["code_generation"],
            "process_read_only": True,
            "is_mutating": False,
        }],
    )
    attempt_id = f"att-{run_id}-{binding_id}-1"
    record_invocation_attempt(
        conn,
        attempt_id=attempt_id,
        run_id=run_id,
        binding_id=binding_id,
        attempt_number=1,
        provider="codex",
        profile="primary",
        status="failed",
    )

    obs_id = "obs-result-quota_exhausted-codex-att-1"
    now = time.time()
    detail = {"attempt_id": attempt_id, "reason": "quota"}
    digest = compute_observation_digest(
        obs_id, "feedback", "quota", "codex", "exhausted",
        timestamp=now, expires_at=now + 3600.0, detail=detail,
    )
    record_operational_observation(
        conn,
        observation_id=obs_id,
        producer="feedback",
        observation_type="quota",
        provider="codex",
        timestamp=now,
        expires_at=now + 3600.0,
        state_value="exhausted",
        digest=digest,
        detail=detail,
    )

    record_invocation_observation_relation(
        conn,
        attempt_id=attempt_id,
        observation_id=obs_id,
        relation_type="produced_by",
    )

    relations = get_invocation_observation_relations(conn, attempt_id=attempt_id)
    assert len(relations) == 1
    assert relations[0]["attempt_id"] == attempt_id
    assert relations[0]["observation_id"] == obs_id
    assert relations[0]["relation_type"] == "produced_by"

    by_obs = get_invocation_observation_relations(conn, observation_id=obs_id)
    assert len(by_obs) == 1
    assert by_obs[0]["attempt_id"] == attempt_id


def test_get_active_operational_observations_respects_expiry(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    ref_now = 1700000000.0

    record_operational_observation(
        conn,
        observation_id="obs-active-1",
        producer="probe",
        observation_type="quota",
        provider="codex",
        timestamp=ref_now - 100.0,
        expires_at=ref_now + 500.0,
        state_value="exhausted",
    )

    record_operational_observation(
        conn,
        observation_id="obs-expired-1",
        producer="feedback",
        observation_type="quota",
        provider="claude",
        timestamp=ref_now - 1000.0,
        expires_at=ref_now - 10.0,
        state_value="exhausted",
    )

    record_operational_observation(
        conn,
        observation_id="obs-permanent-1",
        producer="probe",
        observation_type="availability",
        provider="antigravity",
        timestamp=ref_now - 50.0,
        expires_at=None,
        state_value="available",
    )

    active = get_active_operational_observations(conn, now=ref_now)
    active_ids = [r["observation_id"] for r in active]
    assert "obs-active-1" in active_ids
    assert "obs-permanent-1" in active_ids
    assert "obs-expired-1" not in active_ids

    cur = conn.execute("SELECT COUNT(*) FROM operational_observations;")
    assert cur.fetchone()[0] == 3


def test_idempotent_observation_write_and_digest_stability_verification(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    obs_id = "obs-test-stability-1"
    digest_a = "digest_aaa_111"
    digest_b = "digest_bbb_222"

    record_operational_observation(
        conn,
        observation_id=obs_id,
        producer="feedback",
        observation_type="quota",
        provider="codex",
        state_value="exhausted",
        digest=digest_a,
    )

    record_operational_observation(
        conn,
        observation_id=obs_id,
        producer="feedback",
        observation_type="quota",
        provider="codex",
        state_value="exhausted",
        digest=digest_a,
    )

    with pytest.raises(PersistenceError, match="conflicting observation reuse"):
        record_operational_observation(
            conn,
            observation_id=obs_id,
            producer="feedback",
            observation_type="quota",
            provider="codex",
            state_value="exhausted",
            digest=digest_b,
        )


def test_idempotent_relation_recording_on_crash_replay(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    run_id = "run-feedback-replay"
    record_run(
        conn,
        run_id=run_id,
        project="apgr",
        request_schema="agent-phase-request-v2",
        request_digest="dig-123",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    record_actor_bindings(
        conn,
        run_id=run_id,
        bindings=[{
            "binding_id": "binding_work",
            "policy_name": "default",
            "roles": ["producer"],
            "required_capabilities": ["code_generation"],
            "process_read_only": False,
            "is_mutating": True,
        }],
    )
    attempt_id = f"att-{run_id}-binding_work-1"
    record_invocation_attempt(
        conn,
        attempt_id=attempt_id,
        run_id=run_id,
        binding_id="binding_work",
        attempt_number=1,
        provider="codex",
        profile="primary",
        status="failed",
    )
    obs_id = "obs-replay-1"
    record_operational_observation(
        conn,
        observation_id=obs_id,
        producer="feedback",
        observation_type="quota",
        provider="codex",
        state_value="exhausted",
    )

    record_invocation_observation_relation(conn, attempt_id=attempt_id, observation_id=obs_id)
    assert len(get_invocation_observation_relations(conn, attempt_id=attempt_id)) == 1

    record_invocation_observation_relation(conn, attempt_id=attempt_id, observation_id=obs_id)
    assert len(get_invocation_observation_relations(conn, attempt_id=attempt_id)) == 1


def test_semantic_responsibility_status_vocabulary_enforcement(tmp_path: Path) -> None:
    conn = _setup_db(tmp_path)
    run_id = "run-vocab-1"
    record_run(
        conn,
        run_id=run_id,
        project="apgr",
        request_schema="agent-phase-request-v2",
        request_digest="dig-123",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )

    for status in SEMANTIC_RESPONSIBILITY_STATUSES:
        sem_id = f"sem-{run_id}-{status}"
        record_semantic_responsibility(
            conn,
            id=sem_id,
            run_id=run_id,
            responsibility_name="Planner",
            binding_id="binding_plan",
            status=status,
        )
        update_semantic_responsibility(conn, id=sem_id, status=status)

    sems = get_semantic_responsibilities(conn, run_id)
    assert len(sems) == len(SEMANTIC_RESPONSIBILITY_STATUSES)

    with pytest.raises(PersistenceError, match="invalid semantic responsibility status"):
        record_semantic_responsibility(
            conn,
            id=f"sem-{run_id}-invalid",
            run_id=run_id,
            responsibility_name="Planner",
            binding_id="binding_plan",
            status="invented_status",
        )

    with pytest.raises(PersistenceError, match="invalid semantic responsibility status"):
        update_semantic_responsibility(
            conn,
            id=f"sem-{run_id}-pending",
            status="bogus_status",
        )
