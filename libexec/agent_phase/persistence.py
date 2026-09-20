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

SCHEMA_VERSION = 2
STATE_DIR_MODE = 0o700



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
        return conn
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as error:
        raise PersistenceError(f"could not open dispatcher database at {path}: {error}") from error


def migrate_schema(conn: sqlite3.Connection) -> None:
    """Apply version 1 schema migrations in an explicit transaction."""
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

            cur = conn.execute("PRAGMA table_info(invocation_attempts);")
            cols = [r[1] for r in cur.fetchall()]
            if cols and "attempt_kind" not in cols:
                conn.execute(
                    "ALTER TABLE invocation_attempts ADD COLUMN attempt_kind TEXT NOT NULL DEFAULT 'semantic';"
                )
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as error:
        raise PersistenceError(f"migration failed: {error}") from error


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
