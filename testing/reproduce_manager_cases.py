#!/usr/bin/env python3
"""Reproduction test harness for the 14 manager qualification cases.

Covers:
- 9 historical defect reproductions (C1–C5)
- 5 passing controls verifying contract integrity
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

# Ensure libexec is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
LIBEXEC_DIR = REPO_ROOT / "libexec"
if str(LIBEXEC_DIR) not in sys.path:
    sys.path.insert(0, str(LIBEXEC_DIR))

from agent_phase.config_routing import ReviewMutationPolicy
from agent_phase.finalization import FinalizationError, finalize_repository
from agent_phase.gitstate import capture_entry
from agent_phase.persistence import (
    PersistenceError,
    SCHEMA_VERSION,
    _is_v5_shape,
    check_dispatcher_db_compatibility,
    get_review_mutation_observations,
    migrate_schema_v5,
    open_dispatcher_db,
    record_review_mutation_observation,
    record_review_mutation_policy_provenance,
    record_run,
)
from agent_phase.result import CommitMessage, StageResult
from agent_phase.review_drift import (
    ACTION_BLOCKED,
    ACTION_WARNED,
    ReviewObservation,
    apply_review_mutation_policy,
    derive_final_candidate_freshness,
)


def _create_legacy_v3_db(db_path: Path) -> sqlite3.Connection:
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
                detail TEXT,
                mutated_paths TEXT NOT NULL,
                worktree_paths TEXT NOT NULL,
                expected_tree TEXT NOT NULL,
                observed_tree TEXT NOT NULL,
                expected_index TEXT NOT NULL,
                observed_index TEXT NOT NULL,
                expected_head TEXT NOT NULL,
                observed_head TEXT NOT NULL,
                observed_at TEXT NOT NULL,
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
                resolved_mode TEXT NOT NULL,
                precedence_rank INTEGER NOT NULL,
                is_winner INTEGER NOT NULL,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (run_id, source_type, precedence_rank),
                FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            "INSERT INTO runs VALUES ('run-001', 'apgr', 'APG160', 3, 'req-v2', 'dig-1', '1.0', 'active', 'sub', '2026-09-20T12:00:00Z', 'completed')"
        )
    return conn


def run_case_1(tmp_dir: Path) -> None:
    """Case 1: Orphan observations quarantined without synthesizing stub runs (C1)."""
    db_path = tmp_dir / "case1.sqlite3"
    conn = _create_legacy_v3_db(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """INSERT INTO review_mutation_observations VALUES (
                'orphan-run-999', 'work_review', 'warn', 'block', 'block',
                'none', 0, 0, 0, 0, NULL, '[]', '[]',
                'tree1', 'tree1', 'idx1', 'idx1', 'head1', 'head1',
                '2026-09-20T14:00:00Z'
            )"""
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")

        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)

        # Verify NO stub run synthesized
        stub = conn.execute("SELECT run_id FROM runs WHERE run_id = 'orphan-run-999'").fetchone()
        assert stub is None, "Stub run must not be synthesized for orphan observations"

        # Verify orphan quarantined
        q_row = conn.execute(
            "SELECT run_id, quarantine_reason FROM legacy_quarantine_review_mutation_observations WHERE run_id = 'orphan-run-999'"
        ).fetchone()
        assert q_row is not None, "Orphan observation must be quarantined"
        assert q_row[1] == "orphaned_record_missing_parent_run"

        # Verify foreign keys check passes
        violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(violations) == 0, f"Foreign key violations found: {violations}"
    finally:
        conn.close()


def run_case_2(tmp_dir: Path) -> None:
    """Case 2: Orphan policies quarantined without failing foreign_key_check (C1)."""
    db_path = tmp_dir / "case2.sqlite3"
    conn = _create_legacy_v3_db(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute(
            """INSERT INTO review_mutation_policies VALUES (
                'orphan-pol-888', 'config_file', '/etc/policy.toml', 'dig888',
                'warn', 'block', 'block', 'warn', 1, 1, '2026-09-20T14:00:00Z'
            )"""
        )
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON;")

        migrate_schema_v5(conn)
        check_dispatcher_db_compatibility(conn)

        # Verify NO stub run synthesized
        stub = conn.execute("SELECT run_id FROM runs WHERE run_id = 'orphan-pol-888'").fetchone()
        assert stub is None, "Stub run must not be synthesized for orphan policies"

        # Verify orphan policy quarantined
        q_row = conn.execute(
            "SELECT run_id, quarantine_reason FROM legacy_quarantine_review_mutation_policies WHERE run_id = 'orphan-pol-888'"
        ).fetchone()
        assert q_row is not None, "Orphan policy must be quarantined"
        assert q_row[1] == "orphaned_record_missing_parent_run"

        # Verify foreign keys check passes
        violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        assert len(violations) == 0, f"Foreign key violations found: {violations}"
    finally:
        conn.close()


def run_case_3(tmp_dir: Path) -> None:
    """Case 3: Custom index prefix and UNIQUE constraint preservation (C1)."""
    db_path = tmp_dir / "case3.sqlite3"
    conn = _create_legacy_v3_db(db_path)
    try:
        conn.execute("CREATE UNIQUE INDEX idx_review_mutation_obs_custom_unique ON review_mutation_observations(run_id, stage);")
        conn.commit()

        migrate_schema_v5(conn)

        idx = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'index' AND name = 'idx_review_mutation_obs_custom_unique'"
        ).fetchone()
        assert idx is not None, "Custom index with prefix idx_review_mutation_obs_ must be preserved"
        assert "UNIQUE" in idx[1].upper(), "UNIQUE constraint must not be silently weakened"
    finally:
        conn.close()


def run_case_4(tmp_dir: Path) -> None:
    """Case 4: Custom triggers preserved across table migration (C1)."""
    db_path = tmp_dir / "case4.sqlite3"
    conn = _create_legacy_v3_db(db_path)
    try:
        conn.execute("CREATE TRIGGER trg_test_obs AFTER INSERT ON review_mutation_observations BEGIN SELECT 1; END;")
        conn.execute("CREATE TRIGGER trg_test_pol AFTER INSERT ON review_mutation_policies BEGIN SELECT 1; END;")
        conn.commit()

        migrate_schema_v5(conn)

        trg_obs = conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger' AND name = 'trg_test_obs'").fetchone()
        trg_pol = conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger' AND name = 'trg_test_pol'").fetchone()
        assert trg_obs is not None, "Observation trigger must be preserved"
        assert trg_pol is not None, "Policy trigger must be preserved"
    finally:
        conn.close()


def run_case_5(tmp_dir: Path) -> None:
    """Case 5: Isolation level reset does not commit caller's active uncommitted transaction (C1)."""
    db_path = tmp_dir / "case5.sqlite3"
    conn = _create_legacy_v3_db(db_path)
    try:
        conn.isolation_level = ""
        conn.execute("UPDATE runs SET project = 'caller-uncommitted' WHERE run_id = 'run-001';")
        migrate_schema_v5(conn)
        conn.rollback()

        proj = conn.execute("SELECT project FROM runs WHERE run_id = 'run-001';").fetchone()[0]
        assert proj == "apgr", "Caller uncommitted write must roll back cleanly"
    finally:
        conn.close()


def run_case_6(tmp_dir: Path) -> None:
    """Case 6: Nullable policy columns tolerate sources without review settings (C1)."""
    db_path = tmp_dir / "case6.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        record_run(
            conn,
            run_id="run-null-policy",
            project="apgr",
            request_schema="agent-phase-request-v2",
            request_digest="dig-np",
            lifecycle="standard",
            execution_mode="dynamic",
        )
        item = {
            "source_type": "config_file",
            "source_path": "/path/to/other.toml",
            "content_digest": "dig-other",
            "worktree_policy": None,
            "index_policy": None,
            "head_policy": None,
            "resolved_mode": None,
            "precedence_rank": 1,
            "is_winner": True,
        }
        record_review_mutation_policy_provenance(conn, run_id="run-null-policy", provenance_chain=[item])

        row = conn.execute("SELECT worktree_policy, index_policy, head_policy FROM review_mutation_policies WHERE run_id = 'run-null-policy'").fetchone()
        assert tuple(row) == (None, None, None), "Nullable policy fields must persist NULL without constraint failure"
    finally:
        conn.close()


def run_case_7(tmp_dir: Path) -> None:
    """Case 7: Same-attempt warn -> clean recheck does NOT certify freshness (C2)."""
    candidate_hash = "cand-hash-777"
    state = {}
    obs_warned = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=True,
        worktree_drift=True,
        index_drift=False,
        head_drift=False,
        expected_tree=candidate_hash,
        observed_tree="cand-dirty-000",
        attempt_id="att-attempt-1",
    )
    apply_review_mutation_policy(obs_warned, state=state, raise_on_block=False)

    # Recheck same attempt with clean tree
    obs_clean = ReviewObservation(
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
        attempt_id="att-attempt-1",
    )
    apply_review_mutation_policy(obs_clean, state=state, raise_on_block=False)

    # Must NOT certify freshness
    fresh = derive_final_candidate_freshness(
        work_review_observation=state["review_mutation_observations"]["work_review"],
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=True,
    )
    assert fresh is False, "Same-attempt clean recheck must not erase prior drift"


def run_case_8(tmp_dir: Path) -> None:
    """Case 8: Missing positive HEAD/index drift observation rejected for freshness (C2)."""
    candidate_hash = "cand-hash-888"
    obs_incomplete = {
        "stage": "work_review",
        "role": "work_reviewer",
        "subject_kind": "work",
        "expected_tree": candidate_hash,
        "observed_tree": candidate_hash,
        # Missing head_drift, index_drift, worktree_drift
    }
    fresh = derive_final_candidate_freshness(
        work_review_observation=obs_incomplete,
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=True,
    )
    assert fresh is False, "Candidate freshness must reject observations lacking positive git inspection"


def run_case_9(tmp_dir: Path) -> None:
    """Case 9: SQLite observation indexing failure records sql_indexing_failure limitation (C3)."""
    attempt_id = "att-fail-idx"
    eval_obs = ReviewObservation(
        stage="work_review",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree="tree-fresh",
        observed_tree="tree-fresh",
        attempt_id=attempt_id,
    )
    eval_obs.observation_limitations.append({
        "kind": "sql_indexing_failure",
        "detail": "database is locked",
    })

    # Freshness must reject on sql_indexing_failure limitation
    fresh = derive_final_candidate_freshness(
        work_review_observation=eval_obs,
        work_review_candidate_tree="tree-fresh",
        terminal_candidate_tree="tree-fresh",
        has_verified_receipt=True,
    )
    assert fresh is False, "Candidate freshness must reject when sql_indexing_failure limitation is present"


def run_case_10(tmp_dir: Path) -> None:
    """Case 10: [Control] Independent new attempt can restore clean candidate freshness (C2)."""
    candidate_hash = "cand-fresh-1010"
    state = {}
    # Attempt 1 had drift
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
        observed_tree="cand-dirty",
        expected_head="head-0",
        observed_head="head-0",
        expected_index="idx-0",
        observed_index="idx-0",
        attempt_id="att-1",
    )
    apply_review_mutation_policy(obs1, state=state, raise_on_block=False)

    # Attempt 2 is a new independent attempt with clean tree
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
        expected_head="head-0",
        observed_head="head-0",
        expected_index="idx-0",
        observed_index="idx-0",
        attempt_id="att-2",
    )
    apply_review_mutation_policy(obs2, state=state, raise_on_block=False)

    fresh = derive_final_candidate_freshness(
        work_review_observation=state["review_mutation_observations"]["work_review"],
        work_review_candidate_tree=candidate_hash,
        terminal_candidate_tree=candidate_hash,
        has_verified_receipt=True,
    )
    assert fresh is True, "Independent clean attempt must restore candidate freshness"


def run_case_11(tmp_dir: Path) -> None:
    """Case 11: [Control] Real authority violation strictly fails closed (C2)."""
    obs = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="block"),
        subject_drift_observed=True,
        worktree_drift=True,
        index_drift=False,
        head_drift=False,
        expected_tree="tree-a",
        observed_tree="tree-b",
    )
    obs_res = apply_review_mutation_policy(obs, policy=ReviewMutationPolicy(worktree="block"), raise_on_block=False)
    assert obs_res.action_taken == ACTION_BLOCKED, "Policy violation must result in ACTION_BLOCKED"


def run_case_12(tmp_dir: Path) -> None:
    """Case 12: [Control] Exit-nonzero turn fails closed regardless of indexing (C3)."""
    obs = ReviewObservation(
        stage="work_review",
        role="work_reviewer",
        subject_kind="work",
        policy=ReviewMutationPolicy(worktree="warn"),
        subject_drift_observed=False,
        worktree_drift=False,
        index_drift=False,
        head_drift=False,
        expected_tree="tree-c",
        observed_tree="tree-c",
    )
    fresh = derive_final_candidate_freshness(
        work_review_observation=obs,
        work_review_candidate_tree="tree-c",
        terminal_candidate_tree="tree-c",
        has_verified_receipt=False,  # Unreviewable or failed turn receipt
    )
    assert fresh is False, "Unreviewed/failed turn must not certify candidate freshness"


def run_case_13(tmp_dir: Path) -> None:
    """Case 13: [Control] Contextual closeout requires valid commit message under commit-local (C4)."""
    repo_dir = tmp_dir / "case13_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True, capture_output=True)
    (repo_dir / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True, capture_output=True)

    entry = capture_entry(repo_dir)

    # Modify file
    (repo_dir / "file.txt").write_text("modified\n", encoding="utf-8")

    # Bare closeout without commit message
    parsed_bare = StageResult(
        version=1,
        stage="revise_close",
        outcome="completed",
        body="closeout completed",
        commit_message=None,
    )
    state = {
        "lifecycle": "work-reviewed",
        "finalization_policy": "commit-local",
        "phase_owned_paths": ["file.txt"],
        "path_dispositions": [],
        "ownership_resolutions": [],
        "effective_stages": {"produce": {}, "work_review": {}, "revise_close": {}},
        "effective_checkpoints": ["post_work"],
        "provider_invocations_performed": 3,
        "provider_invocations_inherited": 0,
    }

    class DummyDisplay:
        def git_committing(self, *args): pass
        def git_committed(self, *args): pass
        def git_delta(self, *args): pass
        def __getattr__(self, name): return lambda *args, **kwargs: None

    try:
        finalize_repository(state, entry, parsed_bare, DummyDisplay(), resumed=False)
        assert False, "Bare stage result without commit message must raise FinalizationError"
    except FinalizationError as err:
        assert err.code == "COMMIT_MESSAGE_MISSING", f"Expected COMMIT_MESSAGE_MISSING, got {err.code}"

    # Complete closeout with commit message
    parsed_complete = StageResult(
        version=1,
        stage="revise_close",
        outcome="completed",
        body="closeout completed",
        commit_message=CommitMessage(
            subject="APG160C: test commit",
            body="Scope:\n- s\n\nResult:\n- r\n\nVerification:\n- v\n\nNot run:\n- n",
        ),
    )
    state_complete = {
        "lifecycle": "work-reviewed",
        "finalization_policy": "commit-local",
        "phase_owned_paths": ["file.txt"],
        "path_dispositions": [],
        "ownership_resolutions": [],
        "effective_stages": {"produce": {}, "work_review": {}, "revise_close": {}},
        "effective_checkpoints": ["post_work"],
        "provider_invocations_performed": 3,
        "provider_invocations_inherited": 0,
    }
    finalize_repository(state_complete, entry, parsed_complete, DummyDisplay(), resumed=False)
    assert state_complete.get("final_head") is not None
    assert state_complete.get("repository_finalized") is True
    assert state_complete.get("push", {}).get("status") == "not_attempted_by_policy"


def run_case_14(tmp_dir: Path) -> None:
    """Case 14: [Control] Limitations field bidirectional roundtrip through persistence (C2)."""
    db_path = tmp_dir / "case14.sqlite3"
    conn = open_dispatcher_db(db_path)
    try:
        record_run(
            conn,
            run_id="run-c14",
            project="apgr",
            request_schema="agent-phase-request-v2",
            request_digest="dig-c14",
            lifecycle="standard",
            execution_mode="dynamic",
        )
        obs_dict = {
            "policy": {"worktree": "warn", "index": "block", "head": "block"},
            "attempt_id": "att-c14-1",
            "action_taken": "none",
            "observation_limitations": [{"kind": "custom_limitation", "detail": "fidelity check"}],
        }
        record_review_mutation_observation(
            conn,
            run_id="run-c14",
            stage="work_review",
            sequence=0,
            observation_dict=obs_dict,
        )

        rows = get_review_mutation_observations(conn, "run-c14")
        assert len(rows) == 1
        assert rows[0]["limitations"] == [{"kind": "custom_limitation", "detail": "fidelity check"}]
        assert rows[0]["observation_limitations"] == [{"kind": "custom_limitation", "detail": "fidelity check"}]
    finally:
        conn.close()


CASES = [
    ("Case 1: Orphan observations quarantined without stub runs (C1)", run_case_1),
    ("Case 2: Orphan policies quarantined without failing foreign_key_check (C1)", run_case_2),
    ("Case 3: Custom index prefix and UNIQUE constraint preservation (C1)", run_case_3),
    ("Case 4: Custom triggers preserved across table migration (C1)", run_case_4),
    ("Case 5: Isolation level reset preserves caller's uncommitted transaction (C1)", run_case_5),
    ("Case 6: Nullable policy columns tolerate missing review settings (C1)", run_case_6),
    ("Case 7: Same-attempt warn -> clean recheck does NOT certify freshness (C2)", run_case_7),
    ("Case 8: Missing positive HEAD/index drift observation rejected for freshness (C2)", run_case_8),
    ("Case 9: SQLite observation indexing failure records sql_indexing_failure limitation (C3)", run_case_9),
    ("Case 10: [Control] Independent new attempt can restore clean candidate freshness (C2)", run_case_10),
    ("Case 11: [Control] Real authority violation strictly fails closed (C2)", run_case_11),
    ("Case 12: [Control] Exit-nonzero turn fails closed regardless of indexing (C3)", run_case_12),
    ("Case 13: [Control] Contextual closeout requires valid commit message under commit-local (C4)", run_case_13),
    ("Case 14: [Control] Limitations field bidirectional roundtrip through persistence (C2)", run_case_14),
]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="reproduce_cases_") as tmp_str:
        tmp_dir = Path(tmp_str)
        passed = 0
        failed = 0
        for name, fn in CASES:
            try:
                fn(tmp_dir)
                print(f"  PASS: {name}")
                passed += 1
            except Exception as e:
                import traceback
                print(f"  FAIL: {name} - {e}")
                traceback.print_exc()
                failed += 1

        print(f"\nSummary: {passed}/{len(CASES)} passed, {failed} failed.")
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
