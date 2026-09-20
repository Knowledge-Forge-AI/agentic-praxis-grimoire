"""Qualification test suite for APG160B review-stage mutation and persistence upgrade repair.

Verifies the 11 core repair requirements:
1. Unmigrated v3 database compatibility check failure
2. Real host snapshot migration preserving legacy rows with attempt_id=NULL and limitations
3. Prelaunch database shape validation against corrupted/downgraded schemas
4. Concurrent MAX(sequence) race prevention under BEGIN IMMEDIATE
5. Replay idempotency vs conflicting row persistence errors
6. Observation immutability across retry turns without sticky drift overwriting
7. Immediate raw stdout/stderr artifact writing on failed/blocked turns
8. V2 resume_from_run_id prelaunch rejection with PreLaunchFailureError
9. Attribution-free review-window mutation notice rendering
10. Closed policy file root key rejection
11. Final candidate freshness 4-way tree hash match and strict negative criteria
12. CLI inspectable policy probe (--inspect-policy)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import pytest

from agent_phase.cli import resolve_main
from agent_phase.config_routing import (
    ConfigError,
    ReviewMutationPolicy,
    load_policy_file,
    resolve_review_mutation_policy,
)
from agent_phase.persistence import (
    PersistenceError,
    SCHEMA_VERSION,
    _is_v4_shape,
    _is_v5_shape,
    check_dispatcher_db_compatibility,
    get_review_mutation_observations,
    migrate_schema,
    migrate_schema_v4,
    migrate_schema_v5,
    open_dispatcher_db,
    record_review_mutation_observation,
    record_review_mutation_policy_provenance,
    record_run,
)
from agent_phase.review_drift import (
    ReviewObservation,
    apply_review_mutation_policy,
    derive_final_candidate_freshness,
)
from agent_phase.v2_dispatch import (
    PreLaunchFailureError,
    dispatch_v2,
)
from agent_phase.v2_prompts import (
    format_review_window_mutation_notice,
    render_work_prompt,
    render_closeout_prompt,
)
from agent_phase.request import PhaseRequestV2, parse_request_v2
from agent_phase.v2_turns import execute_v2_turns
from agent_phase.semantic_roles import create_default_binding_policy
from agent_phase.capabilities import EndpointCapabilities
from agent_phase.persistence import record_actor_bindings, record_semantic_responsibility

_HOST_SNAPSHOT_ENV = os.environ.get("APGR_HOST_SNAPSHOT_PATH")
HOST_SNAPSHOT_PATH = Path(_HOST_SNAPSHOT_ENV) if _HOST_SNAPSHOT_ENV else None


def _create_legacy_v3_db(db_path: Path, populate: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.isolation_level = None
    with conn:
        conn.execute(
            """CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )"""
        )
        conn.execute("INSERT INTO schema_migrations VALUES (1, '2026-09-16T12:00:00Z')")
        conn.execute("INSERT INTO schema_migrations VALUES (2, '2026-09-17T12:00:00Z')")
        conn.execute("INSERT INTO schema_migrations VALUES (3, '2026-09-20T12:00:00Z')")
        conn.execute(
            """CREATE TABLE runs (
                run_id TEXT PRIMARY KEY, project TEXT NOT NULL, phase_id TEXT,
                schema_version INTEGER NOT NULL, request_schema TEXT NOT NULL,
                request_digest TEXT NOT NULL, workflow_version TEXT NOT NULL,
                lifecycle TEXT NOT NULL, execution_mode TEXT NOT NULL,
                created_at TEXT NOT NULL, status TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE review_mutation_observations (
                run_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                worktree_policy TEXT NOT NULL,
                index_policy TEXT NOT NULL,
                head_policy TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                subject_drift_observed INTEGER NOT NULL,
                worktree_drift INTEGER NOT NULL,
                index_drift INTEGER NOT NULL,
                head_drift INTEGER NOT NULL,
                diagnostic_code TEXT,
                worktree_paths_json TEXT,
                index_paths_json TEXT,
                expected_tree TEXT,
                observed_tree TEXT,
                expected_index TEXT,
                observed_index TEXT,
                expected_head TEXT,
                observed_head TEXT,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (run_id, stage),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE review_mutation_policies (
                run_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_path TEXT,
                content_digest TEXT,
                worktree_policy TEXT NOT NULL,
                index_policy TEXT NOT NULL,
                head_policy TEXT NOT NULL,
                policy_generation INTEGER NOT NULL,
                is_winner INTEGER NOT NULL DEFAULT 0,
                precedence_rank INTEGER NOT NULL DEFAULT 0,
                resolved_at TEXT NOT NULL,
                PRIMARY KEY (run_id, source_type),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )"""
        )
        if populate:
            conn.execute(
                """INSERT INTO runs VALUES (
                    'run-v3-001', 'apgr', 'APG159', 1, 'v2', 'digest1', '1.0',
                    'standard', 'dynamic', '2026-09-20T12:00:00Z', 'completed'
                )"""
            )
            conn.execute(
                """INSERT INTO runs VALUES (
                    'run-v3-002', 'apgr', 'APG160', 1, 'v2', 'digest2', '1.0',
                    'standard', 'dynamic', '2026-09-20T13:00:00Z', 'completed'
                )"""
            )
            conn.execute(
                """INSERT INTO review_mutation_observations VALUES (
                    'run-v3-001', 'plan_review', 'warn', 'block', 'block',
                    'none', 0, 0, 0, 0, NULL, '[]', '[]',
                    'tree1', 'tree1', 'idx1', 'idx1', 'head1', 'head1',
                    '2026-09-20T14:00:00Z'
                )"""
            )
            conn.execute(
                """INSERT INTO review_mutation_observations VALUES (
                    'run-v3-001', 'work_review', 'warn', 'block', 'block',
                    'warned', 1, 1, 0, 0, 'READ_ONLY_STAGE_MUTATED_CANDIDATE', '[\"notes.md\"]', '[]',
                    'tree1', 'tree2', 'idx1', 'idx1', 'head1', 'head1',
                    '2026-09-20T14:05:00Z'
                )"""
            )
            conn.execute(
                """INSERT INTO review_mutation_observations VALUES (
                    'run-v3-002', 'work_review', 'block', 'block', 'block',
                    'blocked', 1, 0, 1, 0, 'READ_ONLY_STAGE_MUTATED_INDEX', '[]', '[\"staged.txt\"]',
                    'tree1', 'tree1', 'idx1', 'idx2', 'head1', 'head1',
                    '2026-09-20T14:10:00Z'
                )"""
            )
    return conn


def test_unmigrated_v3_db_compatibility_check_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_v3.sqlite3"
    conn = _create_legacy_v3_db(db_path)
    try:
        with pytest.raises(PersistenceError, match="incompatible dispatcher database"):
            check_dispatcher_db_compatibility(conn)
    finally:
        conn.close()


def test_real_host_snapshot_migration_preserves_legacy_rows(tmp_path: Path) -> None:
    if HOST_SNAPSHOT_PATH is None or not HOST_SNAPSHOT_PATH.exists():
        pytest.skip(f"Host snapshot not configured or not found via APGR_HOST_SNAPSHOT_PATH")

    # Every test must operate on its own disposable copy of that snapshot
    disposable_copy = tmp_path / "dispatcher.snapshot.sqlite3"
    shutil.copy2(HOST_SNAPSHOT_PATH, disposable_copy)

    conn = sqlite3.connect(disposable_copy)
    try:
        # Populate disposable copy with a legacy row if empty, so preservation is genuinely executed
        cur = conn.cursor()
        has_obs = cur.execute("SELECT count(*) FROM review_mutation_observations").fetchone()[0]
        if has_obs == 0:
            cur.execute(
                "INSERT OR IGNORE INTO runs (run_id, project, schema_version, request_schema, request_digest, workflow_version, lifecycle, execution_mode, created_at, status) "
                "VALUES ('run-snap-test', 'apgr', 1, 'agent-phase-request-v2', 'dig-snap', '1.0', 'standard', 'dynamic', '2026-09-20T00:00:00Z', 'completed')"
            )
            cur.execute(
                "INSERT INTO review_mutation_observations (run_id, stage, worktree_policy, index_policy, head_policy, action_taken, subject_drift_observed, worktree_drift, index_drift, head_drift, worktree_paths_json, index_paths_json, expected_tree, observed_tree, expected_head, observed_head, recorded_at) "
                "VALUES ('run-snap-test', 'plan_review', 'warn', 'block', 'block', 'none', 0, 0, 0, 0, '[]', '[]', 't1', 't1', 'h1', 'h1', '2026-09-20T00:00:00Z')"
            )

        # Step 1: Verify host snapshot fails compatibility check prior to migration
        with pytest.raises(PersistenceError, match="incompatible dispatcher database"):
            check_dispatcher_db_compatibility(conn)

        # Step 2: Perform migration v5
        migrate_schema_v5(conn)

        # Step 3: Verify compatibility check passes post-migration
        check_dispatcher_db_compatibility(conn)
        assert _is_v5_shape(conn) is True

        # Step 4: Verify schema_migrations contains version 5
        versions = [row[0] for row in cur.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
        assert 5 in versions

        # Step 5: Verify table schema: has 33 columns and 3-column primary key
        columns = [row[1] for row in cur.execute("PRAGMA table_info(review_mutation_observations)").fetchall()]
        assert len(columns) == 33
        assert "attempt_id" in columns
        assert "sequence" in columns
        assert "limitations_json" in columns
        assert "policy_generation" in columns

        # Step 6: Verify legacy rows are preserved with attempt_id IS NULL and legacy limitation
        rows = cur.execute(
            "SELECT run_id, stage, sequence, attempt_id, limitations_json FROM review_mutation_observations"
        ).fetchall()
        assert len(rows) > 0
        for run_id, stage, seq, attempt_id, limitations_json in rows:
            assert seq >= 0
            assert attempt_id is None
            assert limitations_json is not None
            lims = json.loads(limitations_json)
            assert any(lim.get("kind") == "legacy_migrated_record" for lim in lims)
    finally:
        conn.close()


def test_prelaunch_shape_validation_detects_corrupted_or_downgraded_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "corrupted.sqlite3"
    conn = sqlite3.connect(db_path)
    try:
        # DB claims version 5 in schema_migrations but review_mutation_observations is missing columns
        conn.execute(
            """CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )"""
        )
        conn.execute("INSERT INTO schema_migrations VALUES (5, '2026-09-21T00:00:00Z')")
        conn.execute(
            """CREATE TABLE review_mutation_observations (
                run_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                PRIMARY KEY (run_id, stage)
            )"""
        )
        with pytest.raises(PersistenceError, match="incompatible dispatcher database"):
            check_dispatcher_db_compatibility(conn)
    finally:
        conn.close()


def test_concurrent_max_sequence_race_prevention_under_transaction(tmp_path: Path) -> None:
    db_path = tmp_path / "test_seq.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        record_run(
            conn,
            run_id="run-seq",
            project="apgr",
            request_schema="agent-phase-request-v2",
            request_digest="dig-seq",
            lifecycle="default_v012",
            execution_mode="dynamic",
        )
        # Record observations sequentially for same run_id and stage
        obs1 = ReviewObservation(
            stage="work_review",
            policy=ReviewMutationPolicy(worktree="warn"),
            subject_drift_observed=False,
            worktree_drift=False,
            index_drift=False,
            head_drift=False,
            attempt_id="att-1",
        )
        record_review_mutation_observation(conn, run_id="run-seq", stage="work_review", observation=obs1)

        obs2 = ReviewObservation(
            stage="work_review",
            policy=ReviewMutationPolicy(worktree="warn"),
            subject_drift_observed=False,
            worktree_drift=False,
            index_drift=False,
            head_drift=False,
            attempt_id="att-2",
        )
        record_review_mutation_observation(conn, run_id="run-seq", stage="work_review", observation=obs2)

        cur = conn.cursor()
        rows = cur.execute(
            "SELECT sequence, attempt_id FROM review_mutation_observations WHERE run_id = 'run-seq' ORDER BY sequence"
        ).fetchall()
        assert len(rows) == 2
        assert tuple(rows[0]) == (0, "att-1")
        assert tuple(rows[1]) == (1, "att-2")
    finally:
        conn.close()


def test_replay_idempotency_and_conflicting_row_errors(tmp_path: Path) -> None:
    db_path = tmp_path / "test_idempotent.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        record_run(
            conn,
            run_id="run-idem",
            project="apgr",
            request_schema="agent-phase-request-v2",
            request_digest="dig-idem",
            lifecycle="default_v012",
            execution_mode="dynamic",
        )
        obs = ReviewObservation(
            stage="work_review",
            policy=ReviewMutationPolicy(worktree="warn"),
            subject_drift_observed=False,
            worktree_drift=False,
            index_drift=False,
            head_drift=False,
            attempt_id="att-100",
            sequence=1,
            action_taken="none",
        )
        # First record with explicit sequence
        record_review_mutation_observation(conn, run_id="run-idem", stage="work_review", observation=obs, sequence=1)

        # Idempotent replay of exact same record
        record_review_mutation_observation(conn, run_id="run-idem", stage="work_review", observation=obs, sequence=1)

        # Conflicting attempt_id for same sequence
        obs_conflict = ReviewObservation(
            stage="work_review",
            policy=ReviewMutationPolicy(worktree="warn"),
            subject_drift_observed=False,
            worktree_drift=False,
            index_drift=False,
            head_drift=False,
            attempt_id="att-CONFLICT",
            sequence=1,
            action_taken="none",
        )
        with pytest.raises(PersistenceError, match="conflict recording review mutation observation"):
            record_review_mutation_observation(conn, run_id="run-idem", stage="work_review", observation=obs_conflict, sequence=1)
    finally:
        conn.close()


def test_observation_immutability_across_retry_turns() -> None:
    # Turn 1: warning drift observed
    obs1 = ReviewObservation(
        stage="work_review",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=True,
        worktree_drift=True,
        index_drift=False,
        head_drift=False,
        worktree_paths=["modified.txt"],
        attempt_id="turn-1",
    )
    apply_review_mutation_policy(obs1)
    assert obs1.action_taken == "warned"

    # Turn 2: clean retry turn
    obs2 = ReviewObservation(
        stage="work_review",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        attempt_id="turn-2",
    )
    apply_review_mutation_policy(obs2)
    assert obs2.action_taken == "none"

    # Turn 1 observation remains immutable and is not overwritten or cleared
    assert obs1.action_taken == "warned"
    assert obs1.worktree_drift is True


def test_v2_dispatch_prelaunch_rejects_resume_from_run_id(tmp_path: Path) -> None:
    req_json = {
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "test prompt",
    }
    raw = json.dumps(req_json).encode("utf-8")
    req = parse_request_v2(raw)

    with pytest.raises(PreLaunchFailureError, match="suffix-resume is not implemented"):
        dispatch_v2(
            tmp_path,
            tmp_path,
            req,
            raw,
            resume_from_run_id="prior-run-id-12345",
        )


def test_attribution_free_review_window_mutation_notices() -> None:
    notice = format_review_window_mutation_notice(["dir/file1.py", "file2.txt"])
    assert "dir/file1.py" in notice
    assert "file2.txt" in notice
    # Verify notice is attribution-free: no blaming of reviewer, dirt, or author
    for forbidden in ["reviewer", "blame", "author", "dirt", "fault"]:
        assert forbidden not in notice.lower()

    # Empty paths returns empty string
    assert format_review_window_mutation_notice([]) == ""


def test_closed_policy_file_root_key_rejection(tmp_path: Path) -> None:
    policy_file = tmp_path / "extra_keys_policy.toml"
    policy_file.write_text(
        """schema = 1
generation = 7
extra_unauthorized_key = "forbidden"

[review_mutation]
worktree = "warn"
index = "block"
head = "block"
"""
    )
    with pytest.raises(ConfigError, match="unsupported key in policy file"):
        load_policy_file(policy_file)


def test_final_candidate_freshness_truthful_requirements() -> None:
    candidate_hash = "abc123tree"
    head_hash = "head123hash"
    index_id = {"kind": "git_ls_files_stage_v1", "sha256": "idx123hash"}
    clean_obs = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
        action_taken="none",
    )

    # Positive: all 4 hashes match, verified receipt, work review role
    res = derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=clean_obs,
        has_verified_receipt=True,
    )
    assert res is True

    # Negative 1: work_review_candidate_tree != terminal_candidate_tree
    res = derive_final_candidate_freshness(
        work_review_candidate_tree="different_tree",
        terminal_candidate_tree=candidate_hash,
        work_review_observation=clean_obs,
        has_verified_receipt=True,
    )
    assert res is False

    # Negative 2: terminal_candidate_tree != obs.expected_tree
    obs_diff_exp = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree="other_expected",
        observed_tree=candidate_hash,
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
        action_taken="none",
    )
    res = derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_diff_exp,
        has_verified_receipt=True,
    )
    assert res is False

    # Negative 3: obs.expected_tree != obs.observed_tree
    obs_diff_obs = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=True,
        worktree_drift=True,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree="other_observed",
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
        action_taken="warned",
    )
    res = derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_diff_obs,
        has_verified_receipt=True,
    )
    assert res is False

    # Negative 4: role is plan_reviewer
    obs_plan_role = ReviewObservation(
        stage="work_review",
        role="plan_reviewer",
        subject_kind="plan",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
        action_taken="none",
    )
    res = derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_plan_role,
        has_verified_receipt=True,
    )
    assert res is False

    # Negative 5: has_verified_receipt=False
    res = derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=clean_obs,
        has_verified_receipt=False,
    )
    assert res is False

    # Negative 6: candidate_observation_unavailable
    obs_unavail = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        candidate_observation_unavailable=True,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
        action_taken="blocked",
    )
    res = derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_unavail,
        has_verified_receipt=True,
    )
    assert res is False

    # Negative 7: limitations non-empty
    obs_lims = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
        observation_limitations=[{"kind": "partial_read", "detail": "test"}],
        action_taken="none",
    )
    res = derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_lims,
        has_verified_receipt=True,
    )
    assert res is False

    # Negative 8: allow-mode drift
    obs_allow_drift = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="allow"),
        subject_drift_observed=True,
        worktree_drift=True,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree="drifted_tree",
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
        action_taken="allowed",
    )
    res = derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_allow_drift,
        has_verified_receipt=True,
    )
    assert res is False

    # Negative 9 (D1): Missing HEAD evidence (ReviewObservation)
    obs_missing_head = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_index=index_id,
        observed_index=index_id,
        action_taken="none",
    )
    assert derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_missing_head,
        has_verified_receipt=True,
    ) is False

    # Negative 10 (D1): Missing index evidence (ReviewObservation)
    obs_missing_index = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head=head_hash,
        observed_head=head_hash,
        action_taken="none",
    )
    assert derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_missing_index,
        has_verified_receipt=True,
    ) is False

    # Negative 11 (D1): Mapping missing index evidence
    mapping_missing_idx = {
        "stage": "work_review",
        "role": "work_reviewer",
        "subject_kind": "work",
        "expected_tree": candidate_hash,
        "observed_tree": candidate_hash,
        "expected_head": head_hash,
        "observed_head": head_hash,
        "subject_drift_observed": False,
        "worktree_drift": False,
        "index_drift": False,
        "head_drift": False,
    }
    assert derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=mapping_missing_idx,
        has_verified_receipt=True,
    ) is False

    # Negative 12 (D1): Mapping missing HEAD evidence
    mapping_missing_head = {
        "stage": "work_review",
        "role": "work_reviewer",
        "subject_kind": "work",
        "expected_tree": candidate_hash,
        "observed_tree": candidate_hash,
        "expected_index": index_id,
        "observed_index": index_id,
        "subject_drift_observed": False,
        "worktree_drift": False,
        "index_drift": False,
        "head_drift": False,
    }
    assert derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=mapping_missing_head,
        has_verified_receipt=True,
    ) is False

    # Positive 2 (D1): Explicit index-absence value is evidence
    obs_explicit_absent_index = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index={"present": False, "sha256": None},
        observed_index={"present": False, "sha256": None},
        action_taken="none",
    )
    assert derive_final_candidate_freshness(
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        work_review_observation=obs_explicit_absent_index,
        has_verified_receipt=True,
    ) is True


def test_cli_inspect_policy_probe(capsys: pytest.CaptureFixture[str]) -> None:
    # 1. Default inspect policy probe without request file
    code = resolve_main(["--inspect-policy"])
    assert code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert "policy" in res
    assert "winner" in res
    assert "provenance_chain" in res
    assert res["policy"]["worktree"] in ("block", "warn", "allow")

    # 2. Inspect policy with explicit override
    code = resolve_main(["--inspect-policy", "--review-mutation-worktree", "allow"])
    assert code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["policy"]["worktree"] == "allow"
    assert res["winner"]["resolved_mode"] == "allow"

    # 3. Missing request without --inspect-policy exits with code 2
    with pytest.raises(SystemExit) as exc_info:
        resolve_main([])
    assert exc_info.value.code == 2


def test_cli_inspect_policy_with_operator_bundle_generation_42(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    op_home = tmp_path / "operator_home"
    disp = op_home / "dispatcher"
    disp.mkdir(parents=True)

    gen = 42
    for name in ("routes.toml", "endpoints.toml", "capabilities.toml", "policy.toml"):
        src = repo_root / "common" / "dispatcher" / name
        content = src.read_text(encoding="utf-8")
        import re
        content = re.sub(r"generation = \d+", f"generation = {gen}", content)
        if name == "policy.toml":
            content = re.sub(r'worktree = "[^"]+"', 'worktree = "warn"', content)
        (disp / name).write_text(content, encoding="utf-8")

    code = resolve_main(["--inspect-policy", "--apgr-home", str(op_home)])
    assert code == 0
    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["policy"]["generation"] == 42
    assert res["policy"]["worktree"] == "warn"
    assert res["winner"]["source_type"] == "operator_default"


def test_v1_dispatcher_programmatic_home_scoping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from agent_phase.dispatch import Dispatcher
    from agent_phase.request import PhaseRequest

    repo_root = Path(__file__).resolve().parents[3]
    home_x = tmp_path / "home_x"
    home_y = tmp_path / "home_y"
    home_x.mkdir()
    home_y.mkdir()

    # Ambient APGR_HOME is home_y
    monkeypatch.setenv("APGR_HOME", str(home_y))

    # Set up generation 42 bundle in home_x
    disp_x = home_x / "dispatcher"
    disp_x.mkdir(parents=True)
    gen = 42
    for name in ("routes.toml", "endpoints.toml", "capabilities.toml", "policy.toml"):
        src = repo_root / "common" / "dispatcher" / name
        content = src.read_text(encoding="utf-8")
        import re
        content = re.sub(r"generation = \d+", f"generation = {gen}", content)
        if name == "policy.toml":
            content = re.sub(r'worktree = "[^"]+"', 'worktree = "warn"', content)
        (disp_x / name).write_text(content, encoding="utf-8")

    dispatcher = Dispatcher(
        root=repo_root,
        cwd=repo_root,
        apgr_home=home_x,
    )

    # Dispatcher resolves policy from home_x (gen 42, warn)
    assert dispatcher.review_mutation_policy.generation == 42
    assert dispatcher.review_mutation_policy.worktree == "warn"

    # Verify dry_run execution scopes APGR_HOME to home_x and restores home_y
    req = PhaseRequest(phase_type="implementation_testing", execution_mode="normal", prompt="test")
    res = dispatcher.dry_run("test_phase", req)
    assert res["dry_run"] is True
    assert os.environ.get("APGR_HOME") == str(home_y)


def test_synthetic_populated_legacy_v3_migration_preserves_exact_field_bytes(tmp_path: Path) -> None:
    db_path = tmp_path / "synthetic_v3.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=True)
    try:
        # Pre-migration assertions
        with pytest.raises(PersistenceError, match="incompatible dispatcher database"):
            check_dispatcher_db_compatibility(conn)

        migrate_schema_v4(conn)

        check_dispatcher_db_compatibility(conn)
        assert _is_v4_shape(conn) is True

        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT run_id, stage, sequence, worktree_policy, index_policy, head_policy,
                   action_taken, subject_drift_observed, worktree_drift, index_drift, head_drift,
                   diagnostic_code, worktree_paths_json, index_paths_json,
                   expected_tree, observed_tree, expected_index, observed_index,
                   expected_head, observed_head, attempt_id, limitations_json,
                   policy_generation, candidate_observation_unavailable,
                   index_observation_unavailable, head_observation_unavailable
            FROM review_mutation_observations
            ORDER BY run_id, sequence
            """
        ).fetchall()

        assert len(rows) == 3

        # Row 0: run-v3-001, plan_review
        r0 = rows[0]
        assert r0[0] == "run-v3-001"
        assert r0[1] == "plan_review"
        assert r0[2] == 0  # sequence
        assert r0[3] == "warn"
        assert r0[4] == "block"
        assert r0[5] == "block"
        assert r0[6] == "none"
        assert r0[7] == 0
        assert r0[8] == 0
        assert r0[9] == 0
        assert r0[10] == 0
        assert r0[11] is None  # diagnostic_code
        assert r0[12] == "[]"
        assert r0[13] == "[]"
        assert r0[14] == "tree1"
        assert r0[15] == "tree1"
        assert r0[16] == "idx1"
        assert r0[17] == "idx1"
        assert r0[18] == "head1"
        assert r0[19] == "head1"
        assert r0[20] is None  # attempt_id
        lims0 = json.loads(r0[21])
        assert any(lim.get("kind") == "legacy_migrated_record" for lim in lims0)
        assert r0[22] == 7  # policy_generation
        assert r0[23] == 0  # candidate_observation_unavailable
        assert r0[24] == 0  # index_observation_unavailable
        assert r0[25] == 0  # head_observation_unavailable

        # Row 1: run-v3-001, work_review
        r1 = rows[1]
        assert r1[0] == "run-v3-001"
        assert r1[1] == "work_review"
        assert r1[2] == 0  # sequence (single row in run_id, stage partition)
        assert r1[6] == "warned"
        assert r1[7] == 1  # subject_drift_observed
        assert r1[8] == 1  # worktree_drift
        assert r1[11] == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
        assert json.loads(r1[12]) == ["notes.md"]
        assert r1[14] == "tree1"
        assert r1[15] == "tree2"
        assert r1[20] is None

        # Row 2: run-v3-002, work_review
        r2 = rows[2]
        assert r2[0] == "run-v3-002"
        assert r2[1] == "work_review"
        assert r2[2] == 0  # sequence
        assert r2[6] == "blocked"
        assert r2[7] == 1
        assert r2[9] == 1  # index_drift
        assert r2[11] == "READ_ONLY_STAGE_MUTATED_INDEX"
        assert json.loads(r2[13]) == ["staged.txt"]
        assert r2[20] is None
    finally:
        conn.close()


def test_migration_rollback_on_injected_error(tmp_path: Path) -> None:
    db_path = tmp_path / "rollback_test.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=True)
    try:
        # Save pre-state
        pre_versions = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        assert [v[0] for v in pre_versions] == [1, 2, 3]

        # Insert an orphan observation that will require inserting a stub run
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """INSERT INTO review_mutation_observations VALUES (
                'run-orphan-fail', 'work_review', 'warn', 'block', 'block',
                'none', 0, 0, 0, 0, NULL, '[]', '[]',
                'tree1', 'tree1', 'idx1', 'idx1', 'head1', 'head1',
                '2026-09-20T14:00:00Z'
            )"""
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")

        # Create trigger to abort on schema_migrations insert
        conn.execute("CREATE TRIGGER fail_migrations BEFORE INSERT ON schema_migrations BEGIN SELECT RAISE(ABORT, 'injected disk failure'); END;")
        conn.commit()

        with pytest.raises(PersistenceError, match="migration to schema v5 failed"):
            migrate_schema_v5(conn)

        # Verify rollback: schema version remains 3, original table remains intact
        post_versions = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
        assert [v[0] for v in post_versions] == [1, 2, 3]
        rows = conn.execute("SELECT count(*) FROM review_mutation_observations").fetchone()[0]
        assert rows == 4

        # Drop trigger and verify migration now succeeds cleanly
        conn.execute("DROP TRIGGER fail_migrations;")
        conn.commit()
        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)
        assert _is_v5_shape(conn) is True
    finally:
        conn.close()


def test_migration_reopen_and_idempotent_upgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "idempotent_upgrade.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=True)
    try:
        # First migration
        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)
        assert _is_v5_shape(conn) is True

        # Second migration call must be a clean idempotent no-op
        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)

        # Third migration call
        migrate_schema_v5(conn)

        # Verify exactly one version 5 in schema_migrations
        v5_count = conn.execute("SELECT count(*) FROM schema_migrations WHERE version = 5").fetchone()[0]
        assert v5_count == 1

        # Verify observations count did not duplicate
        obs_count = conn.execute("SELECT count(*) FROM review_mutation_observations").fetchone()[0]
        assert obs_count == 3
    finally:
        conn.close()


def test_fresh_db_and_v2_db_migration(tmp_path: Path) -> None:
    # 1. Fresh DB
    fresh_path = tmp_path / "fresh.sqlite3"
    conn_fresh = open_dispatcher_db(fresh_path)
    try:
        assert _is_v5_shape(conn_fresh) is True
        versions = [r[0] for r in conn_fresh.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
        assert versions == [1, 2, 3, 4, 5]
    finally:
        conn_fresh.close()

    # 2. Legacy v2 DB (versions 1 and 2 only)
    v2_path = tmp_path / "legacy_v2.sqlite3"
    conn_v2 = sqlite3.connect(v2_path)
    try:
        conn_v2.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        conn_v2.execute("INSERT INTO schema_migrations VALUES (1, '2026-09-16T12:00:00Z')")
        conn_v2.execute("INSERT INTO schema_migrations VALUES (2, '2026-09-17T12:00:00Z')")
        conn_v2.execute(
            """CREATE TABLE runs (
                run_id TEXT PRIMARY KEY, project TEXT NOT NULL, phase_id TEXT,
                schema_version INTEGER NOT NULL, request_schema TEXT NOT NULL,
                request_digest TEXT NOT NULL, workflow_version TEXT NOT NULL,
                lifecycle TEXT NOT NULL, execution_mode TEXT NOT NULL,
                created_at TEXT NOT NULL, status TEXT NOT NULL
            )"""
        )
        conn_v2.commit()
    finally:
        conn_v2.close()

    # open_dispatcher_db migrates v2 -> v3 -> v4 -> v5
    conn_upgraded = open_dispatcher_db(v2_path)
    try:
        assert _is_v5_shape(conn_upgraded) is True
        versions = [r[0] for r in conn_upgraded.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
        assert versions == [1, 2, 3, 4, 5]
    finally:
        conn_upgraded.close()


def test_partial_interrupted_migration_recovery(tmp_path: Path) -> None:
    db_path = tmp_path / "interrupted.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=True)
    try:
        # Simulate leftover temporary table from an interrupted run
        conn.execute("CREATE TABLE _review_mutation_observations_v4_new (dummy_col TEXT);")
        conn.commit()

        # Migration should clean up the temporary table and succeed
        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)
        assert _is_v5_shape(conn) is True

        # Verify temporary table is gone
        leftover = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = '_review_mutation_observations_v4_new'"
        ).fetchone()
        assert leftover is None

        # Verify rows preserved
        count = conn.execute("SELECT count(*) FROM review_mutation_observations").fetchone()[0]
        assert count == 3
    finally:
        conn.close()


def test_incompatible_future_schema_refuses_destructive_fallback(tmp_path: Path) -> None:
    db_path = tmp_path / "future_schema.sqlite3"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        conn.execute("INSERT INTO schema_migrations VALUES (6, '2026-09-22T00:00:00Z')")
        conn.commit()

        with pytest.raises(PersistenceError, match="newer than supported version"):
            open_dispatcher_db(db_path)
    finally:
        conn.close()


def test_already_v4_to_v5_upgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "already_v4.sqlite3"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        for v in (1, 2, 3, 4):
            conn.execute(f"INSERT INTO schema_migrations VALUES ({v}, '2026-09-20T12:00:00Z')")
        conn.execute(
            """CREATE TABLE runs (
                run_id TEXT PRIMARY KEY, project TEXT NOT NULL, phase_id TEXT,
                schema_version INTEGER NOT NULL, request_schema TEXT NOT NULL,
                request_digest TEXT NOT NULL, workflow_version TEXT NOT NULL,
                lifecycle TEXT NOT NULL, execution_mode TEXT NOT NULL,
                created_at TEXT NOT NULL, status TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE review_mutation_observations (
                run_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                worktree_policy TEXT NOT NULL,
                index_policy TEXT NOT NULL,
                head_policy TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                subject_drift_observed INTEGER NOT NULL,
                worktree_drift INTEGER NOT NULL,
                index_drift INTEGER NOT NULL,
                head_drift INTEGER NOT NULL,
                diagnostic_code TEXT,
                worktree_paths_json TEXT,
                index_paths_json TEXT,
                expected_tree TEXT,
                observed_tree TEXT,
                expected_index TEXT,
                observed_index TEXT,
                expected_head TEXT,
                observed_head TEXT,
                recorded_at TEXT NOT NULL,
                attempt_id TEXT,
                binding_id TEXT,
                attempt_number INTEGER,
                role TEXT,
                subject_kind TEXT,
                limitations_json TEXT,
                policy_generation INTEGER NOT NULL DEFAULT 7,
                raw_stdout_artifact TEXT,
                raw_stderr_artifact TEXT,
                candidate_observation_unavailable INTEGER NOT NULL DEFAULT 0,
                index_observation_unavailable INTEGER NOT NULL DEFAULT 0,
                head_observation_unavailable INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (run_id, stage, sequence),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            """CREATE TABLE review_mutation_policies (
                run_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_path TEXT,
                content_digest TEXT,
                worktree_policy TEXT NOT NULL,
                index_policy TEXT NOT NULL,
                head_policy TEXT NOT NULL,
                resolved_mode TEXT,
                policy_generation INTEGER NOT NULL DEFAULT 7,
                is_winner INTEGER NOT NULL DEFAULT 0,
                precedence_rank INTEGER NOT NULL DEFAULT 0,
                resolved_at TEXT NOT NULL,
                PRIMARY KEY (run_id, source_type),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )"""
        )
        conn.commit()

        # Migrate already-v4 to v5
        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)
        assert _is_v5_shape(conn) is True

        versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()]
        assert versions == [1, 2, 3, 4, 5]
    finally:
        conn.close()


def test_foreign_key_integrity_and_orphan_observation_preservation(tmp_path: Path) -> None:
    db_path = tmp_path / "orphan_test.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=False)
    try:
        # Disable FKs to insert an orphan observation whose run_id does not exist in `runs`
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """INSERT INTO review_mutation_observations VALUES (
                'run-orphan-999', 'work_review', 'warn', 'block', 'block',
                'none', 0, 0, 0, 0, NULL, '[]', '[]',
                'tree1', 'tree1', 'idx1', 'idx1', 'head1', 'head1',
                '2026-09-20T14:00:00Z'
            )"""
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")

        # Migrate to v5
        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)

        # Verify NO stub run was synthesized in `runs`
        stub_run = conn.execute("SELECT run_id, project, status FROM runs WHERE run_id = 'run-orphan-999'").fetchone()
        assert stub_run is None

        # Verify foreign keys check passes without any violations
        fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(fk_violations) == 0

        # Verify orphan observation was preserved in quarantine table
        q_obs = conn.execute(
            "SELECT run_id, stage, quarantine_reason FROM legacy_quarantine_review_mutation_observations WHERE run_id = 'run-orphan-999'"
        ).fetchone()
        assert q_obs is not None
        assert q_obs[0] == "run-orphan-999"
        assert q_obs[2] == "orphaned_record_missing_parent_run"
    finally:
        conn.close()


def test_foreign_key_integrity_and_orphan_policy_preservation(tmp_path: Path) -> None:
    db_path = tmp_path / "orphan_policy_test.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=False)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """INSERT INTO review_mutation_policies VALUES (
                'run-orphan-pol-888', 'config_file', '/path/to/pol.toml', 'dig888',
                'warn', 'block', 'block', 'warn', 1, 1, '2026-09-20T14:00:00Z'
            )"""
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")

        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)

        stub_run = conn.execute("SELECT run_id FROM runs WHERE run_id = 'run-orphan-pol-888'").fetchone()
        assert stub_run is None

        fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(fk_violations) == 0

        q_pol = conn.execute(
            "SELECT run_id, quarantine_reason FROM legacy_quarantine_review_mutation_policies WHERE run_id = 'run-orphan-pol-888'"
        ).fetchone()
        assert q_pol is not None
        assert q_pol[0] == "run-orphan-pol-888"
        assert q_pol[1] == "orphaned_record_missing_parent_run"
    finally:
        conn.close()


def test_pre_existing_indexes_preserved(tmp_path: Path) -> None:
    db_path = tmp_path / "indexes_test.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=True)
    try:
        # Create a custom legacy index and an index with prefix idx_review_mutation_obs_ and UNIQUE
        conn.execute("CREATE INDEX idx_custom_legacy ON review_mutation_observations(diagnostic_code);")
        conn.execute("CREATE UNIQUE INDEX idx_review_mutation_obs_custom_unique ON review_mutation_observations(run_id, stage);")
        conn.execute("CREATE TRIGGER trg_test_obs AFTER INSERT ON review_mutation_observations BEGIN SELECT 1; END;")
        conn.execute("CREATE TRIGGER trg_test_pol AFTER INSERT ON review_mutation_policies BEGIN SELECT 1; END;")
        conn.commit()

        migrate_schema_v5(conn)

        # Verify custom index was recreated
        cur = conn.cursor()
        indexes = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()]
        assert "idx_custom_legacy" in indexes
        assert "idx_review_mutation_obs_custom_unique" in indexes
        assert "idx_review_mutation_obs_run" in indexes
        assert "idx_review_mutation_obs_attempt" in indexes

        unique_sql = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'idx_review_mutation_obs_custom_unique'"
        ).fetchone()[0]
        assert "UNIQUE" in unique_sql.upper()

        triggers = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'").fetchall()]
        assert "trg_test_obs" in triggers
        assert "trg_test_pol" in triggers
    finally:
        conn.close()


def test_concurrent_competing_writers_max_sequence(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    db_path = tmp_path / "concurrent_writers.sqlite3"
    init_conn = open_dispatcher_db(db_path)
    try:
        record_run(
            init_conn,
            run_id="run-concurrent",
            project="apgr",
            request_schema="agent-phase-request-v2",
            request_digest="dig-conc",
            lifecycle="default_v012",
            execution_mode="dynamic",
        )
    finally:
        init_conn.close()

    num_writers = 8

    def write_obs(idx: int) -> int:
        thread_conn = open_dispatcher_db(db_path, busy_timeout_ms=15000)
        try:
            obs = ReviewObservation(
                stage="work_review",
                policy=ReviewMutationPolicy(worktree="warn"),
                subject_drift_observed=False,
                worktree_drift=False,
                index_drift=False,
                head_drift=False,
                attempt_id=f"concurrent-att-{idx}",
            )
            record_review_mutation_observation(
                thread_conn,
                run_id="run-concurrent",
                stage="work_review",
                observation=obs,
            )
            return idx
        finally:
            thread_conn.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(write_obs, i) for i in range(num_writers)]
        results = [f.result() for f in futures]
    assert len(results) == num_writers

    verify_conn = open_dispatcher_db(db_path)
    try:
        rows = verify_conn.execute(
            "SELECT sequence, attempt_id FROM review_mutation_observations WHERE run_id = 'run-concurrent' ORDER BY sequence"
        ).fetchall()
        assert len(rows) == num_writers
        sequences = [r[0] for r in rows]
        assert sequences == list(range(num_writers))
    finally:
        verify_conn.close()


def test_prompt_delivery_into_work_and_closeout_prompts() -> None:
    # 1. render_work_prompt with mutation notice
    mutated_paths = ["src/core/dispatch.py", "docs/specs/v2.md"]
    work_prompt = render_work_prompt(
        task_prompt="Implement task A",
        plan_material_text="Plan step 1\nStep 2",
        plan_review_outcome="reviewed_clean",
        plan_findings=[],
        plan_disposition="accept",
        baseline_tree="tree-base-123",
        review_window_mutations=mutated_paths,
    ).decode("utf-8")

    assert "### Review-Window Mutation Notice (Dispatcher-Observed)" in work_prompt
    assert "src/core/dispatch.py" in work_prompt
    assert "docs/specs/v2.md" in work_prompt
    assert "These paths are tracked by the dispatcher" in work_prompt
    # Ensure attribution-free
    for forbidden in ["reviewer", "blame", "author", "dirt", "fault"]:
        assert forbidden not in work_prompt.lower()

    # 2. render_closeout_prompt with mutation notice
    closeout_prompt = render_closeout_prompt(
        task_prompt="Verify task A",
        candidate_tree="tree-cand-456",
        work_review_outcome="reviewed_clean",
        work_findings=[],
        work_disposition="accept",
        nonce="nonce-closeout-789",
        review_window_mutations=mutated_paths,
    ).decode("utf-8")

    assert "### Review-Window Mutation Notice (Dispatcher-Observed)" in closeout_prompt
    assert "src/core/dispatch.py" in closeout_prompt
    assert "docs/specs/v2.md" in closeout_prompt
    assert "tree-cand-456" in closeout_prompt
    for forbidden in ["reviewer", "blame", "author", "dirt", "fault"]:
        assert forbidden not in closeout_prompt.lower()


def test_policy_provenance_per_source_resolved_mode_and_idempotency(tmp_path: Path) -> None:
    db_path = tmp_path / "policy_prov.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        record_run(
            conn,
            run_id="run-prov",
            project="apgr",
            request_schema="agent-phase-request-v2",
            request_digest="dig-prov",
            lifecycle="default_v012",
            execution_mode="dynamic",
        )

        item_defaults = {
            "source_type": "defaults",
            "worktree_policy": "warn",
            "index_policy": "block",
            "head_policy": "block",
            "resolved_mode": "warn",
            "precedence_rank": 1,
            "is_winner": False,
        }

        # Record defaults provenance
        record_review_mutation_policy_provenance(
            conn,
            run_id="run-prov",
            provenance_chain=[item_defaults],
        )

        # Idempotent re-record of exact same defaults provenance
        record_review_mutation_policy_provenance(
            conn,
            run_id="run-prov",
            provenance_chain=[item_defaults],
        )

        # Conflicting re-record of defaults provenance raises PersistenceError
        conflict_item = dict(item_defaults)
        conflict_item["worktree_policy"] = "block"
        conflict_item["resolved_mode"] = "block"
        with pytest.raises(PersistenceError, match="conflict recording review mutation policy provenance"):
            record_review_mutation_policy_provenance(
                conn,
                run_id="run-prov",
                provenance_chain=[conflict_item],
            )

        # Record config file provenance
        item_config = {
            "source_type": "config_file",
            "source_path": "/path/to/policy.toml",
            "content_digest": "abc123digest",
            "worktree_policy": "allow",
            "index_policy": "warn",
            "head_policy": "block",
            "resolved_mode": "allow",
            "precedence_rank": 2,
            "is_winner": True,
        }
        record_review_mutation_policy_provenance(
            conn,
            run_id="run-prov",
            provenance_chain=[item_config],
        )

        rows = conn.execute(
            "SELECT source_type, worktree_policy, is_winner FROM review_mutation_policies WHERE run_id = 'run-prov' ORDER BY precedence_rank"
        ).fetchall()
        assert len(rows) == 2
        assert tuple(rows[0]) == ("defaults", "warn", 0)
        assert tuple(rows[1]) == ("config_file", "allow", 1)
    finally:
        conn.close()


def test_observation_sql_indexing_failure_preserves_transport_and_raw_files(tmp_path: Path) -> None:
    from agent_phase.capabilities import EndpointCapabilities
    from agent_phase.persistence import (
        open_dispatcher_db,
        record_actor_bindings,
        record_run,
        record_semantic_responsibility,
    )
    from agent_phase.semantic_roles import ActorBinding, ActorBindingPolicy, ROLE_WORK_REVIEWER

    repo_root = Path(__file__).resolve().parents[3]
    work_tree = tmp_path / "work_tree"
    work_tree.mkdir(parents=True, exist_ok=True)
    import subprocess
    subprocess.run(["git", "init", "-b", "main"], cwd=work_tree, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=work_tree, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work_tree, check=True, capture_output=True)
    (work_tree / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=work_tree, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=work_tree, check=True, capture_output=True)

    run_dir = tmp_path / "run_failure_test"
    run_dir.mkdir(parents=True, exist_ok=True)
    db_path = run_dir / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)
    run_id = "run-sql-fail-001"
    record_run(
        conn,
        run_id=run_id,
        project="apgr",
        phase_id="APG160C",
        schema_version=5,
        request_schema="agent-phase-request-v2",
        request_digest="dig-sql-fail",
        workflow_version="2.0",
        lifecycle="active",
        execution_mode="dynamic",
        run_directory=str(run_dir),
    )

    ro_binding = ActorBinding.create("work_review", (ROLE_WORK_REVIEWER,), policy_name="test-policy")
    binding_policy = ActorBindingPolicy(name="test-policy", bindings=(ro_binding,))
    record_actor_bindings(conn, run_id, [
        {
            "binding_id": ro_binding.binding_id,
            "policy_name": binding_policy.name,
            "roles": list(ro_binding.roles),
            "required_capabilities": list(ro_binding.required_capabilities),
            "process_read_only": ro_binding.process_read_only,
            "is_mutating": ro_binding.is_mutating,
        }
    ])
    record_semantic_responsibility(
        conn,
        id=f"sem-{run_id}-{ROLE_WORK_REVIEWER}",
        run_id=run_id,
        responsibility_name=ROLE_WORK_REVIEWER,
        binding_id=ro_binding.binding_id,
        status="pending",
    )

    caps = {
        "test-ep": EndpointCapabilities(
            endpoint_alias="test-ep",
            provider="mock",
            profile="primary",
            capabilities=frozenset(["read_only", "read", "reasoning"]),
            posture="full",
        ),
    }

    def mock_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None, **kwargs: Any) -> Any:
        return None

    conn.execute(
        "CREATE TRIGGER fail_obs_insert BEFORE INSERT ON review_mutation_observations "
        "BEGIN SELECT RAISE(ABORT, 'injected sqlite indexing error'); END;"
    )

    req = parse_request_v2(json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test SQL indexing failure",
    }).encode("utf-8"))

    turn_res = execute_v2_turns(
        conn,
        run_id,
        run_dir,
        repo_root,
        work_tree,
        req,
        execution_mode="dynamic",
        binding_policy=binding_policy,
        caps_catalog=caps,
        operational_observations=(),
        runner=mock_runner,
        display=None,
        dry_run=False,
        lifecycle_spec=type("Spec", (), {"name": "default_v012"})(),
        finalization_policy="commit-local",
    )

    assert turn_res is not None
    obs_mem = turn_res["review_mutation_observations"].get("work_review")
    assert obs_mem is not None
    assert any(lim.get("kind") == "sql_indexing_failure" for lim in obs_mem.get("observation_limitations", []))

    attempt_id = f"att-{run_id}-work_review-1"
    obs_file = run_dir / f"{attempt_id}.observation.json"
    assert obs_file.exists()
    obs_file_data = json.loads(obs_file.read_text(encoding="utf-8"))
    assert any(lim.get("kind") == "sql_indexing_failure" for lim in obs_file_data.get("observation_limitations", []))

    fail_file = run_dir / f"{attempt_id}.observation_indexing_failure.json"
    assert fail_file.exists()
    fail_data = json.loads(fail_file.read_text(encoding="utf-8"))
    assert "injected sqlite indexing error" in fail_data.get("error", "")
    conn.close()


def test_v2_unreviewable_receipt_disqualifies_freshness() -> None:
    candidate_hash = "cand-fresh-123"
    head_hash = "head-fresh-123"
    index_id = {"kind": "git_ls_files_stage_v1", "sha256": "idx-fresh-123"}
    obs = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head=head_hash,
        observed_head=head_hash,
        expected_index=index_id,
        observed_index=index_id,
        action_taken="none",
    )

    # 1. Unreviewable outcome: receipt is invalid (has_verified_receipt=False)
    work_review_outcome = "unreviewable"
    work_review_receipt_valid = work_review_outcome not in ("unreviewable", "")
    assert work_review_receipt_valid is False

    fresh = derive_final_candidate_freshness(
        work_review_observation=obs,
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=work_review_receipt_valid,
    )
    assert fresh is False

    # 2. Empty outcome: receipt is invalid
    work_review_outcome = ""
    work_review_receipt_valid = work_review_outcome not in ("unreviewable", "")
    assert work_review_receipt_valid is False

    fresh = derive_final_candidate_freshness(
        work_review_observation=obs,
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=work_review_receipt_valid,
    )
    assert fresh is False

    # 3. Reviewed clean outcome: receipt is valid
    work_review_outcome = "reviewed_clean"
    work_review_receipt_valid = work_review_outcome not in ("unreviewable", "")
    assert work_review_receipt_valid is True

    fresh = derive_final_candidate_freshness(
        work_review_observation=obs,
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=work_review_receipt_valid,
    )
    assert fresh is True


def test_migration_does_not_commit_unrelated_pending_caller_update(tmp_path: Path) -> None:
    # 1. Lower helper (migrate_schema_v4) preserves caller transaction via savepoint
    db_path = tmp_path / "caller_tx.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=True)
    try:
        conn.isolation_level = ""
        conn.execute("UPDATE runs SET project = 'not-committed-by-caller' WHERE run_id = 'run-v3-001';")
        migrate_schema_v4(conn)
        conn.rollback()
        # Verify caller's update was rolled back, proving migrate_schema_v4 did not commit it
        proj = conn.execute("SELECT project FROM runs WHERE run_id = 'run-v3-001';").fetchone()[0]
        assert proj == "apgr"
    finally:
        conn.close()

    # 2. Public migrate_schema explicitly refuses active caller transaction before any writes
    db_path2 = tmp_path / "caller_tx_public.sqlite3"
    conn2 = _create_legacy_v3_db(db_path2, populate=True)
    try:
        conn2.isolation_level = ""
        conn2.execute("UPDATE runs SET project = 'active-uncommitted' WHERE run_id = 'run-v3-001';")
        with pytest.raises(PersistenceError, match="active caller transaction detected"):
            migrate_schema(conn2)
        conn2.rollback()
        # Verify caller's update was preserved and safely rolled back by the caller
        proj2 = conn2.execute("SELECT project FROM runs WHERE run_id = 'run-v3-001';").fetchone()[0]
        assert proj2 == "apgr"
    finally:
        conn2.close()

    # 3. Ordinary open_dispatcher_db on an idle connection succeeds normally
    db_path3 = tmp_path / "idle_open.sqlite3"
    conn3 = open_dispatcher_db(db_path3)
    try:
        cur = conn3.execute("SELECT MAX(version) FROM schema_migrations;")
        assert cur.fetchone()[0] == 5
    finally:
        conn3.close()


def test_writer_preserves_observer_limitations(tmp_path: Path) -> None:
    db_path = tmp_path / "limits_test.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        record_run(
            conn,
            run_id="run-limits",
            project="apgr",
            request_schema="agent-phase-request-v2",
            request_digest="dig-lim",
            lifecycle="default_v012",
            execution_mode="dynamic",
        )
        obs_dict = {
            "policy": {"worktree": "warn", "index": "block", "head": "block"},
            "attempt_id": "att-lim-1",
            "action_taken": "none",
            "observation_limitations": [{"kind": "missing-history", "detail": "history truncated"}],
        }
        record_review_mutation_observation(
            conn,
            run_id="run-limits",
            stage="work_review",
            sequence=0,
            observation_dict=obs_dict,
        )
        # Query back and verify limitations
        rows = get_review_mutation_observations(conn, "run-limits")
        assert len(rows) == 1
        r = rows[0]
        assert r["attempt_id"] == "att-lim-1"
        assert r["limitations"] == [{"kind": "missing-history", "detail": "history truncated"}]
        assert r["observation_limitations"] == [{"kind": "missing-history", "detail": "history truncated"}]
    finally:
        conn.close()


def test_same_attempt_vs_new_attempt_drift_and_freshness() -> None:
    candidate_hash = "cand-fresh-456"
    state = {}

    # Attempt 1: drift observed
    obs1 = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=True,
        worktree_drift=True,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree="cand-dirty-999",
        expected_head="head-456",
        observed_head="head-456",
        expected_index="index-456",
        observed_index="index-456",
        attempt_id="attempt-1",
    )
    apply_review_mutation_policy(obs1, state=state, raise_on_block=False)

    # Attempt 1 recheck: clean recheck must not erase attempt 1 drift
    obs1_recheck = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head="head-456",
        observed_head="head-456",
        expected_index="index-456",
        observed_index="index-456",
        attempt_id="attempt-1",
    )
    apply_review_mutation_policy(obs1_recheck, state=state, raise_on_block=False)
    assert derive_final_candidate_freshness(
        work_review_observation=state["review_mutation_observations"]["work_review"],
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=True,
    ) is False

    # Attempt 2: new independent attempt starts fresh and can restore freshness
    obs2 = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree=candidate_hash,
        expected_head="head-456",
        observed_head="head-456",
        expected_index="index-456",
        observed_index="index-456",
        attempt_id="attempt-2",
    )
    apply_review_mutation_policy(obs2, state=state, raise_on_block=False)
    assert derive_final_candidate_freshness(
        work_review_observation=state["review_mutation_observations"]["work_review"],
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=True,
    ) is True


def test_v1_review_binding_same_attempt_recheck_retains_drift(tmp_path: Path) -> None:
    from agent_phase import candidate, gitstate, review_binding
    import subprocess
    work_tree = tmp_path / "repo"
    work_tree.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=work_tree, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=work_tree, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work_tree, check=True, capture_output=True)
    (work_tree / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=work_tree, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=work_tree, check=True, capture_output=True)

    state = {
        "run_id": "run-v1-test",
        "lifecycle": "standard",
        "review_mutation_policy": {"worktree": "warn", "index": "block", "head": "block"},
    }
    subject = {
        "kind": "git_tree",
        "head": gitstate.current_head(work_tree),
        "tree": candidate.tree_identity(work_tree)["tree"],
    }

    review_binding.bind(work_tree, state, "work_review", subject, attempt_id="attempt-1")

    (work_tree / "dirty.txt").write_text("drift\n", encoding="utf-8")
    obs1 = review_binding.verify(work_tree, state, "work_review", attempt_id="attempt-1")
    assert obs1.worktree_drift is True
    assert state["review_mutation_observations"]["work_review"]["worktree_drift"] is True

    (work_tree / "dirty.txt").unlink()
    obs2 = review_binding.verify(work_tree, state, "work_review", attempt_id="attempt-1")
    assert state["review_mutation_observations"]["work_review"]["worktree_drift"] is True
    assert derive_final_candidate_freshness(
        work_review_observation=state["review_mutation_observations"]["work_review"],
        work_review_candidate_tree=subject["tree"],
        terminal_candidate_tree=subject["tree"],
        has_verified_receipt=True,
    ) is False


def test_freshness_denies_missing_git_observations() -> None:
    # A dictionary without evaluated git drift fields must be rejected
    candidate_hash = "cand-fresh-789"
    obs_dict = {
        "stage": "work_review",
        "role": "work_reviewer",
        "subject_kind": "work",
        "expected_tree": candidate_hash,
        "observed_tree": candidate_hash,
    }
    assert derive_final_candidate_freshness(
        work_review_observation=obs_dict,
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=True,
    ) is False


def test_commit_local_finalization_failure_publication_status(tmp_path: Path) -> None:
    import subprocess
    from agent_phase import result as result_module

    repo_root = Path(__file__).resolve().parents[3]

    # Sub-case 1: Bare closeout without commit message fails with COMMIT_MESSAGE_MISSING
    repo_dir_1 = tmp_path / "repo1"
    repo_dir_1.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir_1, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir_1, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir_1, check=True, capture_output=True)
    (repo_dir_1 / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo_dir_1, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir_1, check=True, capture_output=True)

    outbox_1 = tmp_path / "outbox1"
    outbox_1.mkdir(parents=True, exist_ok=True)
    home_1 = tmp_path / "home1"
    home_1.mkdir(parents=True, exist_ok=True)

    req_json = {
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test commit-local failure",
    }
    raw = json.dumps(req_json).encode("utf-8")
    req = parse_request_v2(raw)

    def runner_bare(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        if binding.binding_id == "binding_work":
            (repo_dir_1 / "work.txt").write_text("work\n", encoding="utf-8")
            return b"Work done\n"
        elif binding.binding_id == "binding_closeout" and nonce:
            begin, end = result_module.markers(nonce)
            payload = {"version": 1, "stage": "closeout", "outcome": "completed", "body": "Bare closeout"}
            return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")
        return None

    res_1 = dispatch_v2(
        repo_root,
        repo_dir_1,
        req,
        raw,
        apgr_home=home_1,
        outbox_root=outbox_1,
        finalization_policy="commit-local",
        lifecycle="standard",
        dry_run=False,
        runner=runner_bare,
    )
    assert res_1["status"] == "failed"
    assert res_1["finalization_error"]["code"] == "COMMIT_MESSAGE_MISSING"
    assert res_1["publication_status"] == "not_attempted"

    # Sub-case 2: Complete closeout with commit message completes with publication_status="not_attempted" and verified commit
    repo_dir_2 = tmp_path / "repo2"
    repo_dir_2.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir_2, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir_2, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir_2, check=True, capture_output=True)
    (repo_dir_2 / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo_dir_2, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir_2, check=True, capture_output=True)

    outbox_2 = tmp_path / "outbox2"
    outbox_2.mkdir(parents=True, exist_ok=True)
    home_2 = tmp_path / "home2"
    home_2.mkdir(parents=True, exist_ok=True)

    def runner_complete(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        if binding.binding_id == "binding_work":
            (repo_dir_2 / "work.txt").write_text("work\n", encoding="utf-8")
            return b"Work done\n"
        elif binding.binding_id == "binding_closeout" and nonce:
            begin, end = result_module.markers(nonce)
            payload = {
                "version": 1,
                "stage": "closeout",
                "outcome": "completed",
                "body": "Complete closeout",
                "commit_message": {
                    "subject": "phase APG160C test commit",
                    "body": "phase APG160C test commit details",
                },
            }
            return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")
        return None

    res_2 = dispatch_v2(
        repo_root,
        repo_dir_2,
        req,
        raw,
        apgr_home=home_2,
        outbox_root=outbox_2,
        finalization_policy="commit-local",
        lifecycle="standard",
        dry_run=False,
        runner=runner_complete,
    )
    assert res_2["status"] == "completed"
    assert res_2["publication_status"] == "not_attempted"
    log = subprocess.run(
        ["git", "-C", str(repo_dir_2), "log", "-1", "--pretty=%s"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert log.stdout.strip() == "phase APG160C test commit"


def test_migration_v5_custom_unique_index_recreated_once(tmp_path: Path) -> None:
    db_path = tmp_path / "custom_unique.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=False)
    try:
        conn.execute("INSERT INTO runs VALUES ('r1', 'apgr', 'APG160', 1, 'v2', 'digest1', '1.0', 'standard', 'dynamic', '2026-09-20T12:00:00Z', 'completed');")
        conn.execute("INSERT INTO review_mutation_observations VALUES ('r1', 'work_review', 'warn', 'block', 'block', 'none', 0, 0, 0, 0, NULL, '[]', '[]', 'tree1', 'tree1', 'idx1', 'idx1', 'head1', 'head1', '2026-09-20T14:00:00Z');")
        conn.execute("CREATE UNIQUE INDEX idx_review_mutation_obs_run ON review_mutation_observations(run_id);")
        migrate_schema_v5(conn)
        idx_list = conn.execute("PRAGMA index_list(review_mutation_observations);").fetchall()
        run_idxs = [r for r in idx_list if r[1] == "idx_review_mutation_obs_run"]
        assert len(run_idxs) == 1
        assert run_idxs[0][2] == 1  # UNIQUE
    finally:
        conn.close()


def test_migration_v5_table_declared_unique_refused_before_destructive_work(tmp_path: Path) -> None:
    db_path = tmp_path / "table_unique.sqlite3"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT);")
        conn.execute("INSERT INTO schema_migrations VALUES (3, '2026-09-20T12:00:00Z');")
        conn.execute("""CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, project TEXT NOT NULL, phase_id TEXT,
            schema_version INTEGER NOT NULL, request_schema TEXT NOT NULL,
            request_digest TEXT NOT NULL, workflow_version TEXT NOT NULL,
            lifecycle TEXT NOT NULL, execution_mode TEXT NOT NULL,
            created_at TEXT NOT NULL, status TEXT NOT NULL
        );""")
        conn.execute("INSERT INTO runs VALUES ('r1', 'p', 'APG160', 3, 's', 'd', '1', 'std', 'sub', 'now', 'completed');")
        conn.execute("""CREATE TABLE review_mutation_observations (
            run_id TEXT NOT NULL, stage TEXT NOT NULL, worktree_policy TEXT NOT NULL, index_policy TEXT NOT NULL, head_policy TEXT NOT NULL,
            action_taken TEXT NOT NULL, subject_drift_observed INT NOT NULL, worktree_drift INT NOT NULL, index_drift INT NOT NULL, head_drift INT NOT NULL,
            expected_tree TEXT, observed_tree TEXT, expected_index TEXT, observed_index TEXT, expected_head TEXT, observed_head TEXT, recorded_at TEXT NOT NULL,
            PRIMARY KEY (run_id, stage), UNIQUE(recorded_at)
        );""")
        conn.execute("INSERT INTO review_mutation_observations VALUES ('r1', 's1', 'w', 'i', 'h', 'a', 0, 0, 0, 0, 't', 't', 'i', 'i', 'h', 'h', '2026-09-20T12:00:00Z');")
        conn.commit()

        with pytest.raises(PersistenceError, match="unsupported augmented schema on review_mutation_observations"):
            migrate_schema_v5(conn)

        idx_list = conn.execute("PRAGMA index_list(review_mutation_observations);").fetchall()
        assert any(r[3] == "u" for r in idx_list)
        count = conn.execute("SELECT count(*) FROM review_mutation_observations;").fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_migration_v5_missing_observation_table_separated_executes(tmp_path: Path) -> None:
    db_path = tmp_path / "missing_obs.sqlite3"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT);")
        conn.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY);")
        conn.commit()

        migrate_schema_v5(conn)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_observations';")
        assert cur.fetchone() is not None
        idx_list = conn.execute("PRAGMA index_list(review_mutation_observations);").fetchall()
        idx_names = {r[1] for r in idx_list}
        assert "idx_review_mutation_obs_run" in idx_names
        assert "idx_review_mutation_obs_attempt" in idx_names
    finally:
        conn.close()


def test_check_dispatcher_db_compatibility_v5_shape(tmp_path: Path) -> None:
    db_path = tmp_path / "v5_shape.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        check_dispatcher_db_compatibility(conn)

        conn.execute("DROP TABLE review_mutation_policies;")
        with pytest.raises(PersistenceError, match="required table review_mutation_policies is missing"):
            check_dispatcher_db_compatibility(conn)
    finally:
        conn.close()


def test_migration_v5_custom_index_semantics_retained(tmp_path: Path) -> None:
    db_path = tmp_path / "custom_semantics.sqlite3"
    conn = _create_legacy_v3_db(db_path, populate=False)
    try:
        conn.execute("INSERT INTO runs VALUES ('r1', 'apgr', 'APG160', 1, 'v2', 'digest1', '1.0', 'standard', 'dynamic', '2026-09-20T12:00:00Z', 'completed');")
        conn.execute("INSERT INTO review_mutation_observations VALUES ('r1', 'work_review', 'warn', 'block', 'block', 'none', 0, 0, 0, 0, NULL, '[]', '[]', 'tree1', 'tree1', 'idx1', 'idx1', 'head1', 'head1', '2026-09-20T14:00:00Z');")
        conn.execute("CREATE INDEX idx_review_mutation_obs_run ON review_mutation_observations(run_id, stage);")
        migrate_schema_v5(conn)
        sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_review_mutation_obs_run';").fetchone()[0]
        assert "run_id, stage" in sql
    finally:
        conn.close()


def test_future_schema_version_refused_untouched(tmp_path: Path) -> None:
    db_path = tmp_path / "future_ver.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (999, '2099-01-01T00:00:00Z');")
        conn.commit()

        with pytest.raises(PersistenceError, match="is newer than supported version"):
            check_dispatcher_db_compatibility(conn)

        with pytest.raises(PersistenceError, match="is newer than supported version"):
            migrate_schema(conn)

        max_ver = conn.execute("SELECT MAX(version) FROM schema_migrations;").fetchone()[0]
        assert max_ver == 999
    finally:
        conn.close()
