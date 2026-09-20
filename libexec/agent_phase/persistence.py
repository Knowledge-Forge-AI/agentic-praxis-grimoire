"""Lightweight embedded SQLite persistence for the single-phase dispatcher.

Maintains relational run records, actor bindings, pre-launch route selections,
candidates, review findings, and artifact digests. Large streams and transcripts
remain run-owned files on disk. No daemon, no lease server.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import stat
from typing import Any, Mapping, Sequence

from .persistence_feedback import PersistenceError, get_active_operational_observations as get_active_operational_observations, get_invocation_observation_relations as get_invocation_observation_relations, get_operational_observations as get_operational_observations, record_invocation_observation_relation as record_invocation_observation_relation, record_operational_observation as record_operational_observation, record_operational_observation_idempotent as record_operational_observation_idempotent, row_to_operational_observation as row_to_operational_observation, utc_now_iso
from .config_routing import resolve_global_home
from .semantic_roles import SEMANTIC_RESPONSIBILITY_STATUSES

SCHEMA_VERSION = 5
STATE_DIR_MODE = 0o700

REQUIRED_OBSERVATION_COLUMNS: tuple[str, ...] = (
    "run_id", "stage", "sequence", "worktree_policy", "index_policy", "head_policy",
    "action_taken", "subject_drift_observed", "worktree_drift", "index_drift", "head_drift",
    "diagnostic_code", "worktree_paths_json", "index_paths_json", "expected_tree", "observed_tree",
    "expected_index", "observed_index", "expected_head", "observed_head", "recorded_at",
    "attempt_id", "binding_id", "attempt_number", "role", "subject_kind",
    "limitations_json", "policy_generation", "raw_stdout_artifact", "raw_stderr_artifact",
    "candidate_observation_unavailable", "index_observation_unavailable", "head_observation_unavailable",
)




def resolve_dispatcher_db_path(
    apgr_home: Path | str | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Resolve <APGR_HOME>/state/dispatcher.sqlite3."""
    home = Path(apgr_home) if apgr_home is not None else resolve_global_home(environment=environment)
    return home / "state" / "dispatcher.sqlite3"


def ensure_state_directory(path: Path) -> None:
    """Ensure parent state/ directory exists with restricted permissions (0o700)."""
    parent = path.parent
    if not parent.exists():
        parent.mkdir(parents=True, mode=STATE_DIR_MODE)
    try:
        current_mode = stat.S_IMODE(parent.stat().st_mode)
        if current_mode != STATE_DIR_MODE:
            parent.chmod(STATE_DIR_MODE)
    except OSError:
        pass


def open_dispatcher_db(
    db_path: Path | str,
    *,
    busy_timeout_ms: int = 5000,
) -> sqlite3.Connection:
    """Open or initialize the embedded SQLite database with WAL and foreign keys."""
    path = Path(db_path)
    ensure_state_directory(path)
    try:
        conn = sqlite3.connect(str(path), timeout=busy_timeout_ms / 1000.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(f"PRAGMA busy_timeout = {busy_timeout_ms};")
        migrate_schema(conn)
        check_dispatcher_db_compatibility(conn)
        return conn
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as error:
        raise PersistenceError(f"could not open dispatcher database at {path}: {error}") from error


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Apply version 1 schema migrations in an explicit transaction."""
    if conn.in_transaction:
        raise PersistenceError(
            "active caller transaction detected; migrate_schema refuses execution while a transaction is active"
        )
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations';")
    if cur.fetchone():
        cur = conn.execute("SELECT MAX(version) FROM schema_migrations;")
        row = cur.fetchone()
        current_version = row[0] if row and row[0] is not None else 0
        if current_version > SCHEMA_VERSION:
            raise PersistenceError(
                f"incompatible dispatcher database: schema version {current_version} is newer than "
                f"supported version {SCHEMA_VERSION}; refusing execution"
            )
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                """
            )
            cur = conn.execute("SELECT MAX(version) FROM schema_migrations;")
            row = cur.fetchone()
            current_version = row[0] if row and row[0] is not None else 0

            if current_version > SCHEMA_VERSION:
                raise PersistenceError(
                    f"incompatible dispatcher database: schema version {current_version} is newer than "
                    f"supported version {SCHEMA_VERSION}; refusing execution"
                )

            if current_version < 1:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id TEXT PRIMARY KEY, project TEXT NOT NULL, phase_id TEXT,
                        schema_version INTEGER NOT NULL, request_schema TEXT NOT NULL,
                        request_digest TEXT NOT NULL, workflow_version TEXT NOT NULL,
                        lifecycle TEXT NOT NULL, execution_mode TEXT NOT NULL,
                        created_at TEXT NOT NULL, status TEXT NOT NULL, outcome TEXT,
                        semantic_outcome TEXT, finalization_policy TEXT,
                        finalization_outcome TEXT, run_directory TEXT,
                        archive_path TEXT, archive_sha256 TEXT
                    );
                    CREATE TABLE IF NOT EXISTS configuration_provenance (
                        run_id TEXT NOT NULL, source_type TEXT NOT NULL, source_path TEXT,
                        content_digest TEXT, resolved_mode TEXT NOT NULL,
                        is_winner INTEGER NOT NULL DEFAULT 0, precedence_rank INTEGER NOT NULL DEFAULT 0,
                        resolved_at TEXT NOT NULL,
                        PRIMARY KEY (run_id, source_type),
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS actor_bindings (
                        run_id TEXT NOT NULL, binding_id TEXT NOT NULL, policy_name TEXT NOT NULL,
                        merged_roles_json TEXT NOT NULL, required_capabilities_json TEXT NOT NULL,
                        process_read_only INTEGER NOT NULL, is_mutating INTEGER NOT NULL,
                        PRIMARY KEY (run_id, binding_id),
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS semantic_responsibilities (
                        id TEXT PRIMARY KEY, run_id TEXT NOT NULL, responsibility_name TEXT NOT NULL,
                        binding_id TEXT NOT NULL, status TEXT NOT NULL, started_at TEXT,
                        completed_at TEXT, outcome TEXT, candidate_id TEXT,
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS invocation_attempts (
                        attempt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, binding_id TEXT NOT NULL,
                        attempt_number INTEGER NOT NULL, predecessor_attempt_id TEXT,
                        provider TEXT NOT NULL, profile TEXT NOT NULL, endpoint_alias TEXT,
                        status TEXT NOT NULL, exit_code INTEGER, started_at TEXT NOT NULL,
                        completed_at TEXT, route_resolution_id TEXT,
                        attempt_kind TEXT NOT NULL DEFAULT 'semantic',
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS route_resolutions (
                        resolution_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, binding_id TEXT NOT NULL,
                        attempt_number INTEGER NOT NULL, provider TEXT NOT NULL, profile TEXT NOT NULL,
                        endpoint_alias TEXT, intelligence_json TEXT, policy_snapshot_json TEXT,
                        observation_ids_json TEXT, selection_rationale TEXT, resolved_at TEXT NOT NULL,
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS operational_observations (
                        observation_id TEXT PRIMARY KEY, producer TEXT NOT NULL,
                        observation_type TEXT NOT NULL, provider TEXT NOT NULL, profile TEXT,
                        timestamp REAL NOT NULL, expires_at REAL, digest TEXT,
                        state_value TEXT NOT NULL, detail_json TEXT
                    );
                    CREATE TABLE IF NOT EXISTS candidates (
                        candidate_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                        responsibility_name TEXT NOT NULL, candidate_type TEXT NOT NULL,
                        tree_sha TEXT, head_sha TEXT, manifest_json TEXT, created_at TEXT NOT NULL,
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS review_records (
                        review_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                        responsibility_name TEXT NOT NULL, candidate_id TEXT,
                        reviewer_provider TEXT NOT NULL, reviewer_profile TEXT NOT NULL,
                        outcome TEXT NOT NULL, findings_count INTEGER NOT NULL DEFAULT 0,
                        raw_artifact_id TEXT, created_at TEXT NOT NULL,
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS review_findings (
                        finding_id TEXT PRIMARY KEY, review_id TEXT NOT NULL, severity TEXT NOT NULL,
                        title TEXT NOT NULL, detail TEXT, disposition_status TEXT, disposition_rationale TEXT,
                        FOREIGN KEY (review_id) REFERENCES review_records(review_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS review_dispositions (
                        disposition_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                        responsibility_name TEXT NOT NULL, review_id TEXT NOT NULL,
                        disposition_outcome TEXT NOT NULL, rationale TEXT, created_at TEXT NOT NULL,
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS artifacts (
                        artifact_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                        artifact_name TEXT NOT NULL, relative_path TEXT NOT NULL,
                        size_bytes INTEGER NOT NULL, sha256 TEXT NOT NULL,
                        content_type TEXT, created_at TEXT NOT NULL,
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS completion_receipts (
                        receipt_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, phase_id TEXT,
                        final_head TEXT, finalization_policy TEXT, finalization_outcome TEXT,
                        commit_sha TEXT, push_status TEXT, receipt_json TEXT, completed_at TEXT NOT NULL,
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    CREATE TABLE IF NOT EXISTS resume_relations (
                        run_id TEXT NOT NULL, prior_run_id TEXT NOT NULL,
                        resumed_from_stage TEXT NOT NULL, relation_type TEXT NOT NULL,
                        PRIMARY KEY (run_id, prior_run_id),
                        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                    );
                    """
                )
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                    (1, utc_now_iso()),
                )

            if current_version < 2:
                from .persistence_feedback import migrate_schema_v2
                migrate_schema_v2(conn)

            if current_version < 3:
                migrate_schema_v3(conn)

            cur = conn.execute("PRAGMA table_info(invocation_attempts);")
            cols = [r[1] for r in cur.fetchall()]
            if cols and "attempt_kind" not in cols:
                conn.execute(
                    "ALTER TABLE invocation_attempts ADD COLUMN attempt_kind TEXT NOT NULL DEFAULT 'semantic';"
                )

            migrate_schema_v4(conn)
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as error:
        raise PersistenceError(f"migration failed: {error}") from error


def migrate_schema_v3(conn: sqlite3.Connection) -> None:
    """Apply schema version 3 migration: review_mutation_observations and review_mutation_policies."""
    try:
        with conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS review_mutation_observations (
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
                    PRIMARY KEY (run_id, stage, sequence),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS review_mutation_policies (
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
                );
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                (3, utc_now_iso()),
            )
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as error:
        raise PersistenceError(f"migration to schema v3 failed: {error}") from error


def check_dispatcher_db_compatibility(conn: sqlite3.Connection) -> None:
    """Prelaunch compatibility check: inspect schema version and actual table shape."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations';")
    if not cur.fetchone():
        return
    cur = conn.execute("SELECT MAX(version) FROM schema_migrations;")
    row = cur.fetchone()
    max_ver = row[0] if row and row[0] is not None else 0
    if max_ver > SCHEMA_VERSION:
        raise PersistenceError(
            f"incompatible dispatcher database: schema version {max_ver} is newer than "
            f"supported version {SCHEMA_VERSION}; refusing execution"
        )
    if max_ver >= 5:
        for qtbl in ("legacy_quarantine_review_mutation_observations", "legacy_quarantine_review_mutation_policies"):
            qcur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (qtbl,))
            if not qcur.fetchone():
                raise PersistenceError(
                    f"incompatible dispatcher database: quarantine table {qtbl} is missing in schema v5"
                )
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_policies';")
        if not cur.fetchone():
            raise PersistenceError(
                "incompatible dispatcher database: required table review_mutation_policies is missing in schema v5"
            )
        cur = conn.execute("PRAGMA table_info(review_mutation_policies);")
        pol_cols = {r[1]: r for r in cur.fetchall()}
        required_pol_cols = (
            "run_id", "source_type", "source_path", "content_digest",
            "worktree_policy", "index_policy", "head_policy", "resolved_mode",
            "policy_generation", "is_winner", "precedence_rank", "resolved_at",
        )
        missing_pol = [c for c in required_pol_cols if c not in pol_cols]
        if missing_pol:
            raise PersistenceError(
                f"incompatible dispatcher database: review_mutation_policies missing columns: {missing_pol}"
            )
        pol_pk = [r[1] for r in sorted(pol_cols.values(), key=lambda x: x[5]) if r[5] > 0]
        if pol_pk != ["run_id", "source_type"]:
            raise PersistenceError(
                f"incompatible dispatcher database: review_mutation_policies has primary key {pol_pk}, "
                f"expected ['run_id', 'source_type']"
            )
        for nullable_col in ("worktree_policy", "index_policy", "head_policy"):
            if nullable_col in pol_cols and pol_cols[nullable_col][3] != 0:
                raise PersistenceError(
                    f"incompatible dispatcher database: review_mutation_policies.{nullable_col} must be nullable in schema v5"
                )
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_observations';")
        if not cur.fetchone():
            raise PersistenceError(
                "incompatible dispatcher database: required table review_mutation_observations is missing in schema v5"
            )

    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_observations';")
    if cur.fetchone():
        cur = conn.execute("PRAGMA table_info(review_mutation_observations);")
        cols = {r[1]: r for r in cur.fetchall()}
        missing = [c for c in REQUIRED_OBSERVATION_COLUMNS if c not in cols]
        if missing:
            raise PersistenceError(
                f"incompatible dispatcher database: review_mutation_observations missing columns: {missing}"
            )
        pk_cols = [r[1] for r in sorted(cols.values(), key=lambda x: x[5]) if r[5] > 0]
        if pk_cols != ["run_id", "stage", "sequence"]:
            raise PersistenceError(
                f"incompatible dispatcher database: review_mutation_observations has primary key {pk_cols}, "
                f"expected ['run_id', 'stage', 'sequence']"
            )
        for notnull_col in (
            "run_id", "stage", "sequence", "worktree_policy", "index_policy", "head_policy",
            "action_taken", "subject_drift_observed", "worktree_drift", "index_drift", "head_drift",
            "recorded_at",
        ):
            if notnull_col in cols and cols[notnull_col][3] == 0:
                raise PersistenceError(
                    f"incompatible dispatcher database: review_mutation_observations.{notnull_col} must be NOT NULL in schema v5"
                )


def _is_v4_shape(conn: sqlite3.Connection) -> bool:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_observations';")
    if not cur.fetchone():
        return False
    cur = conn.execute("PRAGMA table_info(review_mutation_observations);")
    cols = {r[1]: r for r in cur.fetchall()}
    if not set(REQUIRED_OBSERVATION_COLUMNS).issubset(cols.keys()):
        return False
    pk_cols = [r[1] for r in sorted(cols.values(), key=lambda x: x[5]) if r[5] > 0]
    if pk_cols != ["run_id", "stage", "sequence"]:
        return False
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_policies';")
    if not cur.fetchone():
        return False
    cur = conn.execute("PRAGMA table_info(review_mutation_policies);")
    pol_cols = {r[1]: r for r in cur.fetchall()}
    if "resolved_mode" not in pol_cols:
        return False
    if "worktree_policy" in pol_cols and pol_cols["worktree_policy"][3] != 0:
        return False
    return True


def _is_v5_shape(conn: sqlite3.Connection) -> bool:
    if not _is_v4_shape(conn):
        return False
    for qtbl in ("legacy_quarantine_review_mutation_observations", "legacy_quarantine_review_mutation_policies"):
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (qtbl,))
        if not cur.fetchone():
            return False
    return True


def migrate_schema_v5(conn: sqlite3.Connection) -> None:
    """Apply schema version 5 migration: immutable attempt identity, quarantine for orphans, nullable policies, and v5 evolution."""
    if _is_v5_shape(conn):
        for ver in (4, 5):
            cur = conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?;", (ver,))
            if not cur.fetchone():
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                    (ver, utc_now_iso()),
                )
        return

    pre_fk_violations = set(tuple(r) for r in conn.execute("PRAGMA foreign_key_check;").fetchall())

    in_tx = conn.in_transaction
    savepoint_name = "_migrate_v5_sp"
    if in_tx or conn.isolation_level is not None:
        conn.execute(f"SAVEPOINT {savepoint_name};")
    else:
        conn.execute("BEGIN IMMEDIATE;")

    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_observations';")
        if cur.fetchone():
            cur = conn.execute("PRAGMA index_list(review_mutation_observations);")
            for idx_row in cur.fetchall():
                origin = idx_row[3] if len(idx_row) > 3 else ("u" if idx_row[1].startswith("sqlite_autoindex_") and idx_row[2] == 1 else "c")
                if origin == "u":
                    raise PersistenceError(
                        f"unsupported augmented schema on review_mutation_observations: "
                        f"table-declared UNIQUE constraint {idx_row[1]} detected; refusing destructive migration"
                    )

        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_policies';")
        if cur.fetchone():
            cur = conn.execute("PRAGMA index_list(review_mutation_policies);")
            for idx_row in cur.fetchall():
                origin = idx_row[3] if len(idx_row) > 3 else ("u" if idx_row[1].startswith("sqlite_autoindex_") and idx_row[2] == 1 else "c")
                if origin == "u":
                    raise PersistenceError(
                        f"unsupported augmented schema on review_mutation_policies: "
                        f"table-declared UNIQUE constraint {idx_row[1]} detected; refusing destructive migration"
                    )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS legacy_quarantine_review_mutation_observations (
                run_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                sequence INTEGER NOT NULL DEFAULT 0,
                worktree_policy TEXT,
                index_policy TEXT,
                head_policy TEXT,
                action_taken TEXT,
                subject_drift_observed INTEGER,
                worktree_drift INTEGER,
                index_drift INTEGER,
                head_drift INTEGER,
                diagnostic_code TEXT,
                worktree_paths_json TEXT,
                index_paths_json TEXT,
                expected_tree TEXT,
                observed_tree TEXT,
                expected_index TEXT,
                observed_index TEXT,
                expected_head TEXT,
                observed_head TEXT,
                recorded_at TEXT,
                attempt_id TEXT,
                binding_id TEXT,
                attempt_number INTEGER,
                role TEXT,
                subject_kind TEXT,
                limitations_json TEXT,
                policy_generation INTEGER,
                raw_stdout_artifact TEXT,
                raw_stderr_artifact TEXT,
                candidate_observation_unavailable INTEGER DEFAULT 0,
                index_observation_unavailable INTEGER DEFAULT 0,
                head_observation_unavailable INTEGER DEFAULT 0,
                quarantined_at TEXT NOT NULL,
                quarantine_reason TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS legacy_quarantine_review_mutation_policies (
                run_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_path TEXT,
                content_digest TEXT,
                worktree_policy TEXT,
                index_policy TEXT,
                head_policy TEXT,
                resolved_mode TEXT,
                policy_generation INTEGER,
                is_winner INTEGER,
                precedence_rank INTEGER,
                resolved_at TEXT,
                quarantined_at TEXT NOT NULL,
                quarantine_reason TEXT NOT NULL
            );
            """
        )

        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_observations';")
        has_old_obs_table = cur.fetchone() is not None
        old_indexes: list[tuple[str, str]] = []
        old_triggers: list[tuple[str, str]] = []

        now_iso = utc_now_iso()

        if has_old_obs_table:
            cur = conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='review_mutation_observations' AND sql IS NOT NULL;"
            )
            old_indexes = [(r[0], r[1]) for r in cur.fetchall()]

            cur = conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='review_mutation_observations' AND sql IS NOT NULL;"
            )
            old_triggers = [(r[0], r[1]) for r in cur.fetchall()]

            cur = conn.execute("PRAGMA table_info(review_mutation_observations);")
            existing_cols = {r[1] for r in cur.fetchall()}
            recorded_at_col = "recorded_at" if "recorded_at" in existing_cols else ("observed_at" if "observed_at" in existing_cols else "''")
            diag_code_col = "diagnostic_code" if "diagnostic_code" in existing_cols else ("detail" if "detail" in existing_cols else "NULL")
            wt_paths_col = "worktree_paths_json" if "worktree_paths_json" in existing_cols else ("worktree_paths" if "worktree_paths" in existing_cols else "'[]'")
            idx_paths_col = "index_paths_json" if "index_paths_json" in existing_cols else "'[]'"
            seq_col = "sequence" if "sequence" in existing_cols else f"(ROW_NUMBER() OVER (PARTITION BY run_id, stage ORDER BY {recorded_at_col} ASC) - 1)"
            att_id_col = "attempt_id" if "attempt_id" in existing_cols else "NULL"
            bind_id_col = "binding_id" if "binding_id" in existing_cols else "NULL"
            att_num_col = "attempt_number" if "attempt_number" in existing_cols else "NULL"
            role_col = "role" if "role" in existing_cols else "NULL"
            subj_kind_col = "subject_kind" if "subject_kind" in existing_cols else "NULL"
            limits_col = "limitations_json" if "limitations_json" in existing_cols else "'[{\"kind\": \"legacy_migrated_record\", \"detail\": \"migrated from pre-v4 schema without attempt identity\"}]'"
            gen_col = "policy_generation" if "policy_generation" in existing_cols else "7"
            raw_stdout_col = "raw_stdout_artifact" if "raw_stdout_artifact" in existing_cols else "NULL"
            raw_stderr_col = "raw_stderr_artifact" if "raw_stderr_artifact" in existing_cols else "NULL"
            cand_unavail_col = "candidate_observation_unavailable" if "candidate_observation_unavailable" in existing_cols else "0"
            idx_unavail_col = "index_observation_unavailable" if "index_observation_unavailable" in existing_cols else "0"
            head_unavail_col = "head_observation_unavailable" if "head_observation_unavailable" in existing_cols else "0"

            conn.execute(
                f"""
                INSERT INTO legacy_quarantine_review_mutation_observations (
                    run_id, stage, sequence, worktree_policy, index_policy, head_policy,
                    action_taken, subject_drift_observed, worktree_drift, index_drift, head_drift,
                    diagnostic_code, worktree_paths_json, index_paths_json,
                    expected_tree, observed_tree, expected_index, observed_index,
                    expected_head, observed_head, recorded_at,
                    attempt_id, binding_id, attempt_number, role, subject_kind,
                    limitations_json, policy_generation, raw_stdout_artifact, raw_stderr_artifact,
                    candidate_observation_unavailable, index_observation_unavailable, head_observation_unavailable,
                    quarantined_at, quarantine_reason
                )
                SELECT
                    run_id, stage, {seq_col}, worktree_policy, index_policy, head_policy,
                    action_taken, subject_drift_observed, worktree_drift, index_drift, head_drift,
                    {diag_code_col}, {wt_paths_col}, {idx_paths_col},
                    expected_tree, observed_tree, expected_index, observed_index,
                    expected_head, observed_head, {recorded_at_col},
                    {att_id_col}, {bind_id_col}, {att_num_col}, {role_col}, {subj_kind_col},
                    {limits_col}, {gen_col}, {raw_stdout_col}, {raw_stderr_col},
                    {cand_unavail_col}, {idx_unavail_col}, {head_unavail_col},
                    ?, 'orphaned_record_missing_parent_run'
                FROM review_mutation_observations
                WHERE run_id NOT IN (SELECT run_id FROM runs);
                """,
                (now_iso,),
            )

            conn.execute("DROP TABLE IF EXISTS _review_mutation_observations_v4_new;")
            conn.execute(
                """
                CREATE TABLE _review_mutation_observations_v4_new (
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
                );
                """
            )

            conn.execute(
                f"""
                INSERT INTO _review_mutation_observations_v4_new (
                    run_id, stage, sequence, worktree_policy, index_policy, head_policy,
                    action_taken, subject_drift_observed, worktree_drift, index_drift, head_drift,
                    diagnostic_code, worktree_paths_json, index_paths_json,
                    expected_tree, observed_tree, expected_index, observed_index,
                    expected_head, observed_head, recorded_at,
                    attempt_id, binding_id, attempt_number, role, subject_kind,
                    limitations_json, policy_generation, raw_stdout_artifact, raw_stderr_artifact,
                    candidate_observation_unavailable, index_observation_unavailable, head_observation_unavailable
                )
                SELECT
                    run_id, stage, {seq_col}, worktree_policy, index_policy, head_policy,
                    action_taken, subject_drift_observed, worktree_drift, index_drift, head_drift,
                    {diag_code_col}, {wt_paths_col}, {idx_paths_col},
                    expected_tree, observed_tree, expected_index, observed_index,
                    expected_head, observed_head, {recorded_at_col},
                    {att_id_col}, {bind_id_col}, {att_num_col}, {role_col}, {subj_kind_col},
                    {limits_col}, {gen_col}, {raw_stdout_col}, {raw_stderr_col},
                    {cand_unavail_col}, {idx_unavail_col}, {head_unavail_col}
                FROM review_mutation_observations
                WHERE run_id IN (SELECT run_id FROM runs);
                """
            )
            conn.execute("DROP TABLE review_mutation_observations;")
            conn.execute("ALTER TABLE _review_mutation_observations_v4_new RENAME TO review_mutation_observations;")

            standard_index_sqls = {
                "idx_review_mutation_obs_run": "CREATE INDEX IF NOT EXISTS idx_review_mutation_obs_run ON review_mutation_observations(run_id);",
                "idx_review_mutation_obs_attempt": "CREATE INDEX IF NOT EXISTS idx_review_mutation_obs_attempt ON review_mutation_observations(run_id, stage, attempt_id);",
            }
            recreated_indexes: set[str] = set()
            for idx_name, idx_sql in old_indexes:
                if idx_sql and idx_name not in recreated_indexes:
                    try:
                        conn.execute(idx_sql)
                        recreated_indexes.add(idx_name)
                    except Exception as err:
                        raise PersistenceError(f"failed to preserve index {idx_name}: {err}") from err

            for name, sql in standard_index_sqls.items():
                if name not in recreated_indexes:
                    conn.execute(sql)
                    recreated_indexes.add(name)

            for trig_name, trig_sql in old_triggers:
                if trig_sql:
                    try:
                        conn.execute(trig_sql)
                    except Exception as err:
                        raise PersistenceError(f"failed to preserve trigger {trig_name}: {err}") from err
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_mutation_observations (
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
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_review_mutation_obs_run ON review_mutation_observations(run_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_review_mutation_obs_attempt ON review_mutation_observations(run_id, stage, attempt_id);"
            )

        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='review_mutation_policies';")
        has_old_pol_table = cur.fetchone() is not None
        old_pol_indexes: list[tuple[str, str]] = []
        old_pol_triggers: list[tuple[str, str]] = []

        if has_old_pol_table:
            cur = conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='review_mutation_policies' AND sql IS NOT NULL;"
            )
            old_pol_indexes = [(r[0], r[1]) for r in cur.fetchall()]

            cur = conn.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name='review_mutation_policies' AND sql IS NOT NULL;"
            )
            old_pol_triggers = [(r[0], r[1]) for r in cur.fetchall()]

            cur = conn.execute("PRAGMA table_info(review_mutation_policies);")
            existing_pol_cols = {r[1] for r in cur.fetchall()}
            res_mode_col = "resolved_mode" if "resolved_mode" in existing_pol_cols else "NULL"
            pol_gen_col = "policy_generation" if "policy_generation" in existing_pol_cols else "7"
            resolved_at_col = "resolved_at" if "resolved_at" in existing_pol_cols else ("recorded_at" if "recorded_at" in existing_pol_cols else "''")

            conn.execute(
                f"""
                INSERT INTO legacy_quarantine_review_mutation_policies (
                    run_id, source_type, source_path, content_digest,
                    worktree_policy, index_policy, head_policy, resolved_mode,
                    policy_generation, is_winner, precedence_rank, resolved_at,
                    quarantined_at, quarantine_reason
                )
                SELECT
                    run_id, source_type, source_path, content_digest,
                    worktree_policy, index_policy, head_policy, {res_mode_col},
                    {pol_gen_col}, is_winner, precedence_rank, {resolved_at_col},
                    ?, 'orphaned_record_missing_parent_run'
                FROM review_mutation_policies
                WHERE run_id NOT IN (SELECT run_id FROM runs);
                """,
                (now_iso,),
            )

            conn.execute("DROP TABLE IF EXISTS _review_mutation_policies_v4_new;")
            conn.execute(
                """
                CREATE TABLE _review_mutation_policies_v4_new (
                    run_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_path TEXT,
                    content_digest TEXT,
                    worktree_policy TEXT,
                    index_policy TEXT,
                    head_policy TEXT,
                    resolved_mode TEXT,
                    policy_generation INTEGER NOT NULL DEFAULT 7,
                    is_winner INTEGER NOT NULL DEFAULT 0,
                    precedence_rank INTEGER NOT NULL DEFAULT 0,
                    resolved_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, source_type),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                f"""
                INSERT INTO _review_mutation_policies_v4_new (
                    run_id, source_type, source_path, content_digest,
                    worktree_policy, index_policy, head_policy, resolved_mode,
                    policy_generation, is_winner, precedence_rank, resolved_at
                )
                SELECT
                    run_id, source_type, source_path, content_digest,
                    worktree_policy, index_policy, head_policy, {res_mode_col},
                    {pol_gen_col}, is_winner, precedence_rank, {resolved_at_col}
                FROM review_mutation_policies
                WHERE run_id IN (SELECT run_id FROM runs);
                """
            )
            conn.execute("DROP TABLE review_mutation_policies;")
            conn.execute("ALTER TABLE _review_mutation_policies_v4_new RENAME TO review_mutation_policies;")

            for idx_name, idx_sql in old_pol_indexes:
                if idx_sql:
                    try:
                        conn.execute(idx_sql)
                    except Exception as err:
                        raise PersistenceError(f"failed to preserve policy index {idx_name}: {err}") from err

            for trig_name, trig_sql in old_pol_triggers:
                if trig_sql:
                    try:
                        conn.execute(trig_sql)
                    except Exception as err:
                        raise PersistenceError(f"failed to preserve policy trigger {trig_name}: {err}") from err
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_mutation_policies (
                    run_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_path TEXT,
                    content_digest TEXT,
                    worktree_policy TEXT,
                    index_policy TEXT,
                    head_policy TEXT,
                    resolved_mode TEXT,
                    policy_generation INTEGER NOT NULL DEFAULT 7,
                    is_winner INTEGER NOT NULL DEFAULT 0,
                    precedence_rank INTEGER NOT NULL DEFAULT 0,
                    resolved_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, source_type),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
                """
            )

        obs_fk = conn.execute("PRAGMA foreign_key_check(review_mutation_observations);").fetchall()
        if obs_fk:
            raise PersistenceError(f"foreign key check failed on review_mutation_observations: {obs_fk}")
        pol_fk = conn.execute("PRAGMA foreign_key_check(review_mutation_policies);").fetchall()
        if pol_fk:
            raise PersistenceError(f"foreign key check failed on review_mutation_policies: {pol_fk}")

        post_fk_violations = set(tuple(r) for r in conn.execute("PRAGMA foreign_key_check;").fetchall())
        new_violations = post_fk_violations - pre_fk_violations
        if new_violations:
            raise PersistenceError(f"migration introduced new foreign key violations: {new_violations}")

        for ver in (4, 5):
            cur = conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?;", (ver,))
            if not cur.fetchone():
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                    (ver, utc_now_iso()),
                )

        if in_tx or conn.isolation_level is not None:
            conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
        else:
            conn.execute("COMMIT;")
    except Exception as error:
        if in_tx or conn.isolation_level is not None:
            try:
                conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
            except Exception:
                pass
        else:
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass
        raise PersistenceError(f"migration to schema v5 failed: {error}") from error


def migrate_schema_v4(conn: sqlite3.Connection) -> None:
    """Apply schema version 4/5 migration."""
    migrate_schema_v5(conn)


def record_run(

    conn: sqlite3.Connection,
    *,
    run_id: str,
    project: str,
    phase_id: str | None = None,
    schema_version: int = 1,
    request_schema: str,
    request_digest: str,
    workflow_version: str = "v0.12",
    lifecycle: str,
    execution_mode: str,
    status: str = "running",
    created_at: str | None = None,
    run_directory: str | None = None,
) -> None:
    created = created_at or utc_now_iso()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, project, phase_id, schema_version, request_schema,
                    request_digest, workflow_version, lifecycle, execution_mode,
                    created_at, status, run_directory
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    run_id,
                    project,
                    phase_id,
                    schema_version,
                    request_schema,
                    request_digest,
                    workflow_version,
                    lifecycle,
                    execution_mode,
                    created,
                    status,
                    run_directory,
                ),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record run {run_id}: {error}") from error


def update_run_status(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    *,
    outcome: str | None = None,
    semantic_outcome: str | None = None,
    finalization_outcome: str | None = None,
    archive_path: str | None = None,
    archive_sha256: str | None = None,
) -> None:
    try:
        with conn:
            conn.execute(
                """
                UPDATE runs SET
                    status = ?,
                    outcome = COALESCE(?, outcome),
                    semantic_outcome = COALESCE(?, semantic_outcome),
                    finalization_outcome = COALESCE(?, finalization_outcome),
                    archive_path = COALESCE(?, archive_path),
                    archive_sha256 = COALESCE(?, archive_sha256)
                WHERE run_id = ?;
                """,
                (status, outcome, semantic_outcome, finalization_outcome, archive_path, archive_sha256, run_id),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot update run status for {run_id}: {error}") from error


def get_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    try:
        cur = conn.execute("SELECT * FROM runs WHERE run_id = ?;", (run_id,))
        row = cur.fetchone()
        return dict(row) if row is not None else None
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query run {run_id}: {error}") from error


def record_configuration_provenance(
    conn: sqlite3.Connection,
    run_id: str,
    provenance_chain: Sequence[Mapping[str, Any]],
) -> None:
    try:
        with conn:
            for item in provenance_chain:
                conn.execute(
                    """
                    INSERT INTO configuration_provenance (
                        run_id, source_type, source_path, content_digest,
                        resolved_mode, is_winner, precedence_rank, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        run_id,
                        item["source_type"],
                        item.get("source_path"),
                        item.get("content_digest"),
                        item["resolved_mode"],
                        1 if item.get("is_winner") else 0,
                        item.get("precedence_rank", 0),
                        utc_now_iso(),
                    ),
                )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record configuration provenance for run {run_id}: {error}") from error


def get_configuration_provenance(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[dict[str, Any]]:
    try:
        cur = conn.execute(
            "SELECT * FROM configuration_provenance WHERE run_id = ? ORDER BY precedence_rank ASC;",
            (run_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query configuration provenance for run {run_id}: {error}") from error


def record_review_mutation_policy_provenance(
    conn: sqlite3.Connection,
    run_id: str,
    provenance_chain: Sequence[Mapping[str, Any]],
    worktree_policy: str = "warn",
    index_policy: str = "block",
    head_policy: str = "block",
    policy_generation: int = 7,
) -> None:
    in_tx = getattr(conn, "in_transaction", False)
    savepoint_name = "_rec_pol_sp"
    if in_tx:
        conn.execute(f"SAVEPOINT {savepoint_name};")
    else:
        prev_iso = conn.isolation_level
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE;")
    try:
        for item in provenance_chain:
            mode = item.get("resolved_mode") if isinstance(item, Mapping) else getattr(item, "resolved_mode", None)
            if mode == "":
                mode = None
            if mode is not None:
                wt = (item.get("worktree_policy") or item.get("resolved_worktree") or mode) if isinstance(item, Mapping) else (getattr(item, "worktree_policy", None) or getattr(item, "resolved_worktree", None) or mode)
                idx = (item.get("index_policy") or item.get("resolved_index") or "block") if isinstance(item, Mapping) else (getattr(item, "index_policy", None) or getattr(item, "resolved_index", None) or "block")
                hd = (item.get("head_policy") or item.get("resolved_head") or "block") if isinstance(item, Mapping) else (getattr(item, "head_policy", None) or getattr(item, "resolved_head", None) or "block")
            else:
                wt = (item.get("worktree_policy") or item.get("resolved_worktree") or None) if isinstance(item, Mapping) else (getattr(item, "worktree_policy", None) or getattr(item, "resolved_worktree", None) or None)
                idx = (item.get("index_policy") or item.get("resolved_index") or None) if isinstance(item, Mapping) else (getattr(item, "index_policy", None) or getattr(item, "resolved_index", None) or None)
                hd = (item.get("head_policy") or item.get("resolved_head") or None) if isinstance(item, Mapping) else (getattr(item, "head_policy", None) or getattr(item, "resolved_head", None) or None)
            gen = item.get("policy_generation", policy_generation) if isinstance(item, Mapping) else getattr(item, "policy_generation", policy_generation)
            src_type = item["source_type"] if isinstance(item, Mapping) else getattr(item, "source_type")
            src_path = item.get("source_path") if isinstance(item, Mapping) else getattr(item, "source_path", None)
            digest = item.get("content_digest") if isinstance(item, Mapping) else getattr(item, "content_digest", None)
            is_win = 1 if (item.get("is_winner") if isinstance(item, Mapping) else getattr(item, "is_winner", False)) else 0
            rank = item.get("precedence_rank", 0) if isinstance(item, Mapping) else getattr(item, "precedence_rank", 0)

            cur = conn.execute(
                "SELECT * FROM review_mutation_policies WHERE run_id = ? AND source_type = ?;",
                (run_id, src_type),
            )
            existing = cur.fetchone()
            if existing:
                existing_dict = dict(existing)
                if (
                    existing_dict.get("source_path") == src_path
                    and existing_dict.get("content_digest") == digest
                    and existing_dict.get("worktree_policy") == wt
                    and existing_dict.get("index_policy") == idx
                    and existing_dict.get("head_policy") == hd
                    and existing_dict.get("resolved_mode") == mode
                    and existing_dict.get("policy_generation") == gen
                    and existing_dict.get("is_winner") == is_win
                    and existing_dict.get("precedence_rank") == rank
                ):
                    continue
                else:
                    if in_tx:
                        conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                        conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
                    else:
                        conn.execute("ROLLBACK;")
                    raise PersistenceError(
                        f"conflict recording review mutation policy provenance for run {run_id}, source {src_type}"
                    )

            conn.execute(
                """
                INSERT INTO review_mutation_policies (
                    run_id, source_type, source_path, content_digest,
                    worktree_policy, index_policy, head_policy, resolved_mode, policy_generation,
                    is_winner, precedence_rank, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    run_id,
                    src_type,
                    src_path,
                    digest,
                    wt,
                    idx,
                    hd,
                    mode,
                    gen,
                    is_win,
                    rank,
                    utc_now_iso(),
                ),
            )
        if in_tx:
            conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
        else:
            conn.execute("COMMIT;")
    except Exception as error:
        try:
            if in_tx:
                conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
            else:
                conn.execute("ROLLBACK;")
        except Exception:
            pass
        if isinstance(error, PersistenceError):
            raise
        raise PersistenceError(f"cannot record review mutation policy for run {run_id}: {error}") from error
    finally:
        if not in_tx:
            conn.isolation_level = prev_iso


def get_review_mutation_policies(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[dict[str, Any]]:
    try:
        cur = conn.execute(
            "SELECT * FROM review_mutation_policies WHERE run_id = ? ORDER BY precedence_rank ASC;",
            (run_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query review mutation policies for run {run_id}: {error}") from error


def record_review_mutation_observation(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    stage: str,
    observation: Mapping[str, Any] | None = None,
    observation_dict: Mapping[str, Any] | None = None,
    recorded_at: str | None = None,
    sequence: int | None = None,
) -> None:
    recorded = recorded_at or utc_now_iso()
    obs_raw = observation if observation is not None else (observation_dict or {})
    if hasattr(obs_raw, "as_dict"):
        obs_map = obs_raw.as_dict()
    elif isinstance(obs_raw, Mapping):
        obs_map = dict(obs_raw)
    else:
        obs_map = {}
    policy = obs_map.get("policy", {})
    wt_pol = policy.get("worktree", "warn") if isinstance(policy, Mapping) else getattr(policy, "worktree", "warn")
    idx_pol = policy.get("index", "block") if isinstance(policy, Mapping) else getattr(policy, "index", "block")
    hd_pol = policy.get("head", "block") if isinstance(policy, Mapping) else getattr(policy, "head", "block")
    action_taken = obs_map.get("action_taken", "none")
    diag_code = obs_map.get("diagnostic_code")
    worktree_paths = obs_map.get("worktree_paths", [])
    index_paths = obs_map.get("index_paths", [])
    wt_paths_json = json.dumps(worktree_paths)
    idx_paths_json = json.dumps(index_paths)
    exp_tree = obs_map.get("expected_tree")
    obs_tree = obs_map.get("observed_tree")
    exp_idx = obs_map.get("expected_index")
    obs_idx = obs_map.get("observed_index")
    exp_idx_str = json.dumps(exp_idx) if isinstance(exp_idx, (dict, list)) else (str(exp_idx) if exp_idx else None)
    obs_idx_str = json.dumps(obs_idx) if isinstance(obs_idx, (dict, list)) else (str(obs_idx) if obs_idx else None)
    exp_hd = obs_map.get("expected_head")
    obs_hd = obs_map.get("observed_head")

    attempt_id = obs_map.get("attempt_id")
    binding_id = obs_map.get("binding_id")
    attempt_number = obs_map.get("attempt_number")
    role = obs_map.get("role")
    subject_kind = obs_map.get("subject_kind")
    limitations = obs_map.get("limitations")
    if limitations is None:
        limitations = obs_map.get("observation_limitations")
    limitations_json = json.dumps(limitations) if limitations is not None else None
    policy_gen = obs_map.get("policy_generation", 7)
    raw_stdout = obs_map.get("raw_stdout_artifact")
    raw_stderr = obs_map.get("raw_stderr_artifact")

    subj_drift = 1 if obs_map.get("subject_drift_observed") else 0
    wt_drift = 1 if obs_map.get("worktree_drift") else 0
    idx_drift = 1 if obs_map.get("index_drift") else 0
    hd_drift = 1 if obs_map.get("head_drift") else 0
    cand_unavail = 1 if obs_map.get("candidate_observation_unavailable") else 0
    idx_unavail = 1 if obs_map.get("index_observation_unavailable") else 0
    hd_unavail = 1 if obs_map.get("head_observation_unavailable") else 0

    in_tx = getattr(conn, "in_transaction", False)
    savepoint_name = "_rec_obs_sp"
    if in_tx:
        conn.execute(f"SAVEPOINT {savepoint_name};")
    else:
        prev_iso = conn.isolation_level
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE;")
    try:
        if sequence is None:
            attempt_id_val = obs_map.get("attempt_id")
            if attempt_id_val:
                cur = conn.execute(
                    "SELECT sequence FROM review_mutation_observations WHERE run_id = ? AND stage = ? AND attempt_id = ?;",
                    (run_id, stage, attempt_id_val),
                )
                row = cur.fetchone()
                if row is not None:
                    seq = row[0]
                else:
                    cur = conn.execute(
                        "SELECT COALESCE(MAX(sequence), -1) + 1 FROM review_mutation_observations WHERE run_id = ? AND stage = ?;",
                        (run_id, stage),
                    )
                    row = cur.fetchone()
                    seq = row[0] if row else 0
            else:
                cur = conn.execute(
                    "SELECT COALESCE(MAX(sequence), -1) + 1 FROM review_mutation_observations WHERE run_id = ? AND stage = ?;",
                    (run_id, stage),
                )
                row = cur.fetchone()
                seq = row[0] if row else 0
        else:
            seq = sequence

        cur = conn.execute(
            "SELECT * FROM review_mutation_observations WHERE run_id = ? AND stage = ? AND sequence = ?;",
            (run_id, stage, seq),
        )
        existing = cur.fetchone()
        if existing:
            existing_dict = dict(existing)
            matches = (
                existing_dict.get("worktree_policy") == wt_pol
                and existing_dict.get("index_policy") == idx_pol
                and existing_dict.get("head_policy") == hd_pol
                and (existing_dict.get("action_taken") or "none") == action_taken
                and bool(existing_dict.get("subject_drift_observed")) == bool(subj_drift)
                and bool(existing_dict.get("worktree_drift")) == bool(wt_drift)
                and bool(existing_dict.get("index_drift")) == bool(idx_drift)
                and bool(existing_dict.get("head_drift")) == bool(hd_drift)
                and existing_dict.get("diagnostic_code") == diag_code
                and json.loads(existing_dict.get("worktree_paths_json") or "[]") == worktree_paths
                and json.loads(existing_dict.get("index_paths_json") or "[]") == index_paths
                and existing_dict.get("expected_tree") == exp_tree
                and existing_dict.get("observed_tree") == obs_tree
                and existing_dict.get("expected_index") == exp_idx_str
                and existing_dict.get("observed_index") == obs_idx_str
                and existing_dict.get("expected_head") == exp_hd
                and existing_dict.get("observed_head") == obs_hd
                and existing_dict.get("attempt_id") == attempt_id
                and existing_dict.get("binding_id") == binding_id
                and existing_dict.get("attempt_number") == attempt_number
                and existing_dict.get("role") == role
                and existing_dict.get("subject_kind") == subject_kind
                and json.loads(existing_dict.get("limitations_json") or "[]") == (limitations or [])
                and existing_dict.get("policy_generation") == policy_gen
                and existing_dict.get("raw_stdout_artifact") == raw_stdout
                and existing_dict.get("raw_stderr_artifact") == raw_stderr
                and bool(existing_dict.get("candidate_observation_unavailable")) == bool(cand_unavail)
                and bool(existing_dict.get("index_observation_unavailable")) == bool(idx_unavail)
                and bool(existing_dict.get("head_observation_unavailable")) == bool(hd_unavail)
            )
            if matches:
                if in_tx:
                    conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
                else:
                    conn.execute("COMMIT;")
                return
            else:
                if in_tx:
                    conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                    conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
                else:
                    conn.execute("ROLLBACK;")
                raise PersistenceError(
                    f"conflict recording review mutation observation for run {run_id}, stage {stage}, sequence {seq}"
                )

        conn.execute(
            """
            INSERT INTO review_mutation_observations (
                run_id, stage, sequence, worktree_policy, index_policy, head_policy,
                action_taken, subject_drift_observed, worktree_drift, index_drift, head_drift,
                diagnostic_code, worktree_paths_json, index_paths_json,
                expected_tree, observed_tree, expected_index, observed_index,
                expected_head, observed_head, recorded_at,
                attempt_id, binding_id, attempt_number, role, subject_kind,
                limitations_json, policy_generation, raw_stdout_artifact, raw_stderr_artifact,
                candidate_observation_unavailable, index_observation_unavailable, head_observation_unavailable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                run_id,
                stage,
                seq,
                wt_pol,
                idx_pol,
                hd_pol,
                action_taken,
                subj_drift,
                wt_drift,
                idx_drift,
                hd_drift,
                diag_code,
                wt_paths_json,
                idx_paths_json,
                exp_tree,
                obs_tree,
                exp_idx_str,
                obs_idx_str,
                exp_hd,
                obs_hd,
                recorded,
                attempt_id,
                binding_id,
                attempt_number,
                role,
                subject_kind,
                limitations_json,
                policy_gen,
                raw_stdout,
                raw_stderr,
                cand_unavail,
                idx_unavail,
                hd_unavail,
            ),
        )
        if in_tx:
            conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
        else:
            conn.execute("COMMIT;")
    except Exception as error:
        try:
            if in_tx:
                conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name};")
                conn.execute(f"RELEASE SAVEPOINT {savepoint_name};")
            else:
                conn.execute("ROLLBACK;")
        except Exception:
            pass
        if isinstance(error, PersistenceError):
            raise
        raise PersistenceError(
            f"cannot record review mutation observation for run {run_id} stage {stage}: {error}"
        ) from error
    finally:
        if not in_tx:
            conn.isolation_level = prev_iso


def get_review_mutation_observations(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[dict[str, Any]]:
    try:
        cur = conn.execute(
            "SELECT * FROM review_mutation_observations WHERE run_id = ? ORDER BY sequence ASC, recorded_at ASC;",
            (run_id,),
        )
        rows = [dict(row) for row in cur.fetchall()]
        for r in rows:
            limitations_val = json.loads(r.get("limitations_json") or "[]")
            r["worktree_paths"] = json.loads(r.get("worktree_paths_json") or "[]")
            r["index_paths"] = json.loads(r.get("index_paths_json") or "[]")
            r["limitations"] = limitations_val
            r["observation_limitations"] = limitations_val
            r["subject_drift_observed"] = bool(r.get("subject_drift_observed"))
            r["worktree_drift"] = bool(r.get("worktree_drift"))
            r["index_drift"] = bool(r.get("index_drift"))
            r["head_drift"] = bool(r.get("head_drift"))
            r["candidate_observation_unavailable"] = bool(r.get("candidate_observation_unavailable"))
            r["index_observation_unavailable"] = bool(r.get("index_observation_unavailable"))
            r["head_observation_unavailable"] = bool(r.get("head_observation_unavailable"))
        return rows
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query review mutation observations for run {run_id}: {error}") from error


def record_actor_bindings(

    conn: sqlite3.Connection,
    run_id: str,
    bindings: Sequence[Mapping[str, Any]],
) -> None:
    try:
        with conn:
            for binding in bindings:
                conn.execute(
                    """
                    INSERT INTO actor_bindings (
                        run_id, binding_id, policy_name, merged_roles_json,
                        required_capabilities_json, process_read_only, is_mutating
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        run_id,
                        binding["binding_id"],
                        binding.get("policy_name", "default_standard"),
                        json.dumps(binding.get("roles", [])),
                        json.dumps(binding.get("required_capabilities", [])),
                        1 if binding.get("process_read_only") else 0,
                        1 if binding.get("is_mutating") else 0,
                    ),
                )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record actor bindings for run {run_id}: {error}") from error


def get_actor_bindings(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[dict[str, Any]]:
    try:
        cur = conn.execute(
            "SELECT * FROM actor_bindings WHERE run_id = ? ORDER BY binding_id;",
            (run_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query actor bindings for run {run_id}: {error}") from error


def record_semantic_responsibility(
    conn: sqlite3.Connection,
    *,
    id: str,
    run_id: str,
    responsibility_name: str,
    binding_id: str,
    status: str = "pending",
    started_at: str | None = None,
    completed_at: str | None = None,
    outcome: str | None = None,
    candidate_id: str | None = None,
) -> None:
    if status not in SEMANTIC_RESPONSIBILITY_STATUSES:
        raise PersistenceError(f"invalid semantic responsibility status {status!r}; expected one of {SEMANTIC_RESPONSIBILITY_STATUSES}")
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO semantic_responsibilities (
                    id, run_id, responsibility_name, binding_id,
                    status, started_at, completed_at, outcome, candidate_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (id, run_id, responsibility_name, binding_id, status, started_at, completed_at, outcome, candidate_id),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record semantic responsibility {id} for run {run_id}: {error}") from error


def update_semantic_responsibility(
    conn: sqlite3.Connection,
    *,
    id: str,
    status: str,
    outcome: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
    candidate_id: str | None = None,
) -> None:
    if status not in SEMANTIC_RESPONSIBILITY_STATUSES:
        raise PersistenceError(f"invalid semantic responsibility status {status!r}; expected one of {SEMANTIC_RESPONSIBILITY_STATUSES}")
    try:
        with conn:
            conn.execute(
                """
                UPDATE semantic_responsibilities SET
                    status = ?,
                    outcome = COALESCE(?, outcome),
                    started_at = COALESCE(?, started_at),
                    completed_at = COALESCE(?, completed_at),
                    candidate_id = COALESCE(?, candidate_id)
                WHERE id = ?;
                """,
                (status, outcome, started_at, completed_at, candidate_id, id),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot update semantic responsibility {id}: {error}") from error


def get_semantic_responsibilities(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[dict[str, Any]]:
    try:
        cur = conn.execute(
            "SELECT * FROM semantic_responsibilities WHERE run_id = ? ORDER BY id;",
            (run_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query semantic responsibilities for run {run_id}: {error}") from error


def record_invocation_attempt(
    conn: sqlite3.Connection,
    *,
    attempt_id: str,
    run_id: str,
    binding_id: str,
    attempt_number: int,
    provider: str,
    profile: str,
    status: str = "running",
    started_at: str | None = None,
    completed_at: str | None = None,
    predecessor_attempt_id: str | None = None,
    endpoint_alias: str | None = None,
    exit_code: int | None = None,
    route_resolution_id: str | None = None,
    attempt_kind: str = "semantic",
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO invocation_attempts (
                    attempt_id, run_id, binding_id, attempt_number,
                    predecessor_attempt_id, provider, profile, endpoint_alias,
                    status, exit_code, started_at, completed_at, route_resolution_id,
                    attempt_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    attempt_id,
                    run_id,
                    binding_id,
                    attempt_number,
                    predecessor_attempt_id,
                    provider,
                    profile,
                    endpoint_alias,
                    status,
                    exit_code,
                    started_at or utc_now_iso(),
                    completed_at,
                    route_resolution_id,
                    attempt_kind,
                ),
            )
    except sqlite3.OperationalError as error:
        if "no column named attempt_kind" in str(error):
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO invocation_attempts (
                            attempt_id, run_id, binding_id, attempt_number,
                            predecessor_attempt_id, provider, profile, endpoint_alias,
                            status, exit_code, started_at, completed_at, route_resolution_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            attempt_id,
                            run_id,
                            binding_id,
                            attempt_number,
                            predecessor_attempt_id,
                            provider,
                            profile,
                            endpoint_alias,
                            status,
                            exit_code,
                            started_at or utc_now_iso(),
                            completed_at,
                            route_resolution_id,
                        ),
                    )
            except sqlite3.Error as inner_error:
                raise PersistenceError(f"cannot record invocation attempt {attempt_id} for run {run_id}: {inner_error}") from inner_error
        else:
            raise PersistenceError(f"cannot record invocation attempt {attempt_id} for run {run_id}: {error}") from error
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record invocation attempt {attempt_id} for run {run_id}: {error}") from error


def update_invocation_attempt(
    conn: sqlite3.Connection,
    *,
    attempt_id: str,
    status: str,
    exit_code: int | None = None,
    completed_at: str | None = None,
) -> None:
    try:
        with conn:
            conn.execute(
                """
                UPDATE invocation_attempts SET
                    status = ?,
                    exit_code = COALESCE(?, exit_code),
                    completed_at = COALESCE(?, completed_at)
                WHERE attempt_id = ?;
                """,
                (status, exit_code, completed_at, attempt_id),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot update invocation attempt {attempt_id}: {error}") from error


def get_invocation_attempts(
    conn: sqlite3.Connection,
    run_id: str,
    binding_id: str | None = None,
) -> list[dict[str, Any]]:
    try:
        if binding_id is not None:
            cur = conn.execute(
                "SELECT * FROM invocation_attempts WHERE run_id = ? AND binding_id = ? ORDER BY attempt_number ASC;",
                (run_id, binding_id),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM invocation_attempts WHERE run_id = ? ORDER BY attempt_number ASC;",
                (run_id,),
            )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query invocation attempts for run {run_id}: {error}") from error


def record_route_resolution(
    conn: sqlite3.Connection,
    *,
    resolution_id: str,
    run_id: str,
    binding_id: str,
    attempt_number: int,
    provider: str,
    profile: str,
    endpoint_alias: str | None = None,
    intelligence: Mapping[str, Any] | None = None,
    policy_snapshot: Mapping[str, Any] | None = None,
    observation_ids: Sequence[str] | None = None,
    selection_rationale: str = "",
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO route_resolutions (
                    resolution_id, run_id, binding_id, attempt_number,
                    provider, profile, endpoint_alias, intelligence_json,
                    policy_snapshot_json, observation_ids_json,
                    selection_rationale, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    resolution_id,
                    run_id,
                    binding_id,
                    attempt_number,
                    provider,
                    profile,
                    endpoint_alias,
                    json.dumps(intelligence or {}),
                    json.dumps(policy_snapshot or {}),
                    json.dumps(list(observation_ids or [])),
                    selection_rationale,
                    utc_now_iso(),
                ),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record route resolution for run {run_id}: {error}") from error


def get_attempt_route_resolution(
    conn: sqlite3.Connection,
    run_id: str,
    binding_id: str,
    attempt_number: int,
) -> dict[str, Any] | None:
    try:
        cur = conn.execute(
            """
            SELECT * FROM route_resolutions
            WHERE run_id = ? AND binding_id = ? AND attempt_number = ?;
            """,
            (run_id, binding_id, attempt_number),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return dict(row)
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query attempt route for run {run_id}: {error}") from error


def get_route_resolutions(
    conn: sqlite3.Connection,
    run_id: str,
) -> list[dict[str, Any]]:
    try:
        cur = conn.execute(
            "SELECT * FROM route_resolutions WHERE run_id = ? ORDER BY attempt_number ASC;",
            (run_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query route resolutions for run {run_id}: {error}") from error


def record_candidate(
    conn: sqlite3.Connection,
    *,
    candidate_id: str,
    run_id: str,
    responsibility_name: str,
    candidate_type: str,
    tree_sha: str | None = None,
    head_sha: str | None = None,
    manifest: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO candidates (
                    candidate_id, run_id, responsibility_name, candidate_type,
                    tree_sha, head_sha, manifest_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    candidate_id,
                    run_id,
                    responsibility_name,
                    candidate_type,
                    tree_sha,
                    head_sha,
                    json.dumps(manifest) if manifest else None,
                    created_at or utc_now_iso(),
                ),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record candidate {candidate_id} for {run_id}: {error}") from error


def get_candidates(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    try:
        cur = conn.execute("SELECT * FROM candidates WHERE run_id = ? ORDER BY created_at ASC;", (run_id,))
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query candidates for {run_id}: {error}") from error


def record_review_record(
    conn: sqlite3.Connection,
    *,
    review_id: str,
    run_id: str,
    responsibility_name: str,
    reviewer_provider: str,
    reviewer_profile: str,
    outcome: str,
    findings_count: int = 0,
    candidate_id: str | None = None,
    raw_artifact_id: str | None = None,
    created_at: str | None = None,
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO review_records (
                    review_id, run_id, responsibility_name, candidate_id,
                    reviewer_provider, reviewer_profile, outcome, findings_count,
                    raw_artifact_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    review_id,
                    run_id,
                    responsibility_name,
                    candidate_id,
                    reviewer_provider,
                    reviewer_profile,
                    outcome,
                    findings_count,
                    raw_artifact_id,
                    created_at or utc_now_iso(),
                ),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record review {review_id} for {run_id}: {error}") from error


def get_review_records(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    try:
        cur = conn.execute("SELECT * FROM review_records WHERE run_id = ? ORDER BY created_at ASC;", (run_id,))
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query reviews for {run_id}: {error}") from error


def record_review_finding(
    conn: sqlite3.Connection,
    *,
    finding_id: str,
    review_id: str,
    severity: str,
    title: str,
    detail: str | None = None,
    disposition_status: str | None = None,
    disposition_rationale: str | None = None,
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO review_findings (
                    finding_id, review_id, severity, title, detail,
                    disposition_status, disposition_rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (finding_id, review_id, severity, title, detail, disposition_status, disposition_rationale),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record review finding {finding_id}: {error}") from error


def get_review_findings(conn: sqlite3.Connection, review_id: str) -> list[dict[str, Any]]:
    try:
        cur = conn.execute("SELECT * FROM review_findings WHERE review_id = ?;", (review_id,))
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query review findings for {review_id}: {error}") from error


def record_review_disposition(
    conn: sqlite3.Connection,
    *,
    disposition_id: str,
    run_id: str,
    responsibility_name: str,
    review_id: str,
    disposition_outcome: str,
    rationale: str | None = None,
    created_at: str | None = None,
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO review_dispositions (
                    disposition_id, run_id, responsibility_name, review_id,
                    disposition_outcome, rationale, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (disposition_id, run_id, responsibility_name, review_id, disposition_outcome, rationale, created_at or utc_now_iso()),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record review disposition {disposition_id} for {run_id}: {error}") from error


def get_review_dispositions(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    try:
        cur = conn.execute("SELECT * FROM review_dispositions WHERE run_id = ? ORDER BY created_at ASC;", (run_id,))
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query review dispositions for {run_id}: {error}") from error


def record_artifact(
    conn: sqlite3.Connection,
    *,
    artifact_id: str,
    run_id: str,
    artifact_name: str,
    relative_path: str,
    size_bytes: int,
    sha256: str,
    content_type: str = "text/plain",
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, run_id, artifact_name, relative_path,
                    size_bytes, sha256, content_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    artifact_id,
                    run_id,
                    artifact_name,
                    relative_path,
                    size_bytes,
                    sha256,
                    content_type,
                    utc_now_iso(),
                ),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record artifact {artifact_id} for run {run_id}: {error}") from error


def get_artifacts(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    try:
        cur = conn.execute("SELECT * FROM artifacts WHERE run_id = ? ORDER BY artifact_id;", (run_id,))
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query artifacts for {run_id}: {error}") from error


def record_completion_receipt(
    conn: sqlite3.Connection,
    *,
    receipt_id: str,
    run_id: str,
    phase_id: str | None = None,
    final_head: str | None = None,
    finalization_policy: str | None = None,
    finalization_outcome: str | None = None,
    commit_sha: str | None = None,
    push_status: str | None = None,
    receipt: Mapping[str, Any] | None = None,
    completed_at: str | None = None,
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO completion_receipts (
                    receipt_id, run_id, phase_id, final_head,
                    finalization_policy, finalization_outcome,
                    commit_sha, push_status, receipt_json, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    receipt_id,
                    run_id,
                    phase_id,
                    final_head,
                    finalization_policy,
                    finalization_outcome,
                    commit_sha,
                    push_status,
                    json.dumps(receipt) if receipt else None,
                    completed_at or utc_now_iso(),
                ),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record completion receipt {receipt_id} for {run_id}: {error}") from error


def get_completion_receipts(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    try:
        cur = conn.execute("SELECT * FROM completion_receipts WHERE run_id = ?;", (run_id,))
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query completion receipts for {run_id}: {error}") from error


def record_resume_relation(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    prior_run_id: str,
    resumed_from_stage: str,
    relation_type: str = "retry",
) -> None:
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO resume_relations (
                    run_id, prior_run_id, resumed_from_stage, relation_type
                ) VALUES (?, ?, ?, ?);
                """,
                (run_id, prior_run_id, resumed_from_stage, relation_type),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record resume relation {run_id} -> {prior_run_id}: {error}") from error


def get_resume_relations(conn: sqlite3.Connection, run_id: str) -> list[dict[str, Any]]:
    try:
        cur = conn.execute("SELECT * FROM resume_relations WHERE run_id = ?;", (run_id,))
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query resume relations for {run_id}: {error}") from error


def verify_run_artifacts(
    conn: sqlite3.Connection,
    run_id: str,
    run_directory: Path | str,
) -> tuple[bool, list[str]]:
    """Verify that on-disk files match stored digests and sizes."""
    run_dir = Path(run_directory)
    mismatches: list[str] = []
    try:
        cur = conn.execute("SELECT * FROM artifacts WHERE run_id = ?;", (run_id,))
        rows = cur.fetchall()
        for row in rows:
            rel = row["relative_path"]
            stored_sha = row["sha256"]
            stored_size = row["size_bytes"]
            target = run_dir / rel
            if not target.is_file():
                mismatches.append(f"missing artifact on disk: {rel}")
                continue
            data = target.read_bytes()
            if len(data) != stored_size:
                mismatches.append(f"size mismatch for {rel}: expected {stored_size}, got {len(data)}")
                continue
            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != stored_sha:
                mismatches.append(f"digest mismatch for {rel}: expected {stored_sha}, got {actual_sha}")
        return len(mismatches) == 0, mismatches
    except (OSError, sqlite3.Error) as error:
        raise PersistenceError(f"artifact verification failed for {run_id}: {error}") from error
