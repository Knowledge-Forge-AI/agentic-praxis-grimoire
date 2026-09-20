"""Persistence feedback and schema v2 support for provider failure observations.

Provides schema version 2 migrations (invocation_observation_relations table),
atomic idempotent observation recording with SHA-256 conflict detection,
and active operational observation queries.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
import sqlite3
import time
from typing import Any

from .dynamic_router import OperationalObservation


class PersistenceError(RuntimeError):
    """Raised when SQLite operations fail or encounter lock contention."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def migrate_schema_v2(conn: sqlite3.Connection) -> None:
    """Apply schema version 2 migration: invocation_observation_relations."""
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS invocation_observation_relations (
                    attempt_id TEXT NOT NULL,
                    observation_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (attempt_id, observation_id),
                    FOREIGN KEY (attempt_id) REFERENCES invocation_attempts(attempt_id) ON DELETE CASCADE,
                    FOREIGN KEY (observation_id) REFERENCES operational_observations(observation_id) ON DELETE CASCADE
                );
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                (2, utc_now_iso()),
            )
    except (sqlite3.OperationalError, sqlite3.DatabaseError) as error:
        raise PersistenceError(f"migration to schema v2 failed: {error}") from error


def record_operational_observation_idempotent(
    conn: sqlite3.Connection,
    *,
    observation_id: str,
    producer: str,
    observation_type: str,
    provider: str,
    state_value: str,
    profile: str | None = None,
    timestamp: float | None = None,
    expires_at: float | None = None,
    digest: str | None = None,
    detail: Mapping[str, Any] | None = None,
) -> None:
    """Record operational observation idempotently with atomic digest stability verification."""
    try:
        with conn:
            cur = conn.execute(
                "SELECT digest, state_value, expires_at FROM operational_observations WHERE observation_id = ?;",
                (observation_id,),
            )
            row = cur.fetchone()
            if row is not None:
                existing_digest = row[0]
                existing_state = row[1]
                if digest is not None and existing_digest is not None and existing_digest != digest:
                    raise PersistenceError(
                        f"conflicting observation reuse for {observation_id}: existing digest {existing_digest} != new digest {digest}"
                    )
                if state_value != existing_state:
                    raise PersistenceError(
                        f"conflicting observation state reuse for {observation_id}: existing {existing_state} != new {state_value}"
                    )
                return

            conn.execute(
                """
                INSERT INTO operational_observations (
                    observation_id, producer, observation_type, provider,
                    profile, timestamp, expires_at, digest, state_value, detail_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    observation_id,
                    producer,
                    observation_type,
                    provider,
                    profile,
                    timestamp if timestamp is not None else time.time(),
                    expires_at,
                    digest,
                    state_value,
                    json.dumps(detail) if detail is not None else None,
                ),
            )
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot record operational observation {observation_id}: {error}") from error


record_operational_observation = record_operational_observation_idempotent


def get_operational_observations(
    conn: sqlite3.Connection,
    *,
    provider: str | None = None,
) -> list[dict[str, Any]]:
    """Query operational observations, optionally filtered by provider."""
    try:
        if provider is not None:
            cur = conn.execute(
                "SELECT * FROM operational_observations WHERE provider = ? ORDER BY timestamp DESC;",
                (provider,),
            )
        else:
            cur = conn.execute("SELECT * FROM operational_observations ORDER BY timestamp DESC;")
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query operational observations: {error}") from error


def record_invocation_observation_relation(
    conn: sqlite3.Connection,
    *,
    attempt_id: str,
    observation_id: str,
    relation_type: str = "produced_by",
    created_at: str | None = None,
) -> None:
    """Record relation between an invocation attempt and an operational observation."""
    created = created_at or utc_now_iso()
    try:
        with conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO invocation_observation_relations (
                    attempt_id, observation_id, relation_type, created_at
                ) VALUES (?, ?, ?, ?);
                """,
                (attempt_id, observation_id, relation_type, created),
            )
    except sqlite3.Error as error:
        raise PersistenceError(
            f"cannot record invocation observation relation ({attempt_id}, {observation_id}): {error}"
        ) from error


def get_invocation_observation_relations(
    conn: sqlite3.Connection,
    *,
    attempt_id: str | None = None,
    observation_id: str | None = None,
) -> list[dict[str, Any]]:
    """Query invocation-observation relations with optional filtering."""
    try:
        if attempt_id is not None and observation_id is not None:
            cur = conn.execute(
                "SELECT * FROM invocation_observation_relations WHERE attempt_id = ? AND observation_id = ?;",
                (attempt_id, observation_id),
            )
        elif attempt_id is not None:
            cur = conn.execute(
                "SELECT * FROM invocation_observation_relations WHERE attempt_id = ? ORDER BY created_at ASC;",
                (attempt_id,),
            )
        elif observation_id is not None:
            cur = conn.execute(
                "SELECT * FROM invocation_observation_relations WHERE observation_id = ? ORDER BY created_at ASC;",
                (observation_id,),
            )
        else:
            cur = conn.execute("SELECT * FROM invocation_observation_relations ORDER BY created_at ASC;")
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query invocation observation relations: {error}") from error


def get_active_operational_observations(
    conn: sqlite3.Connection,
    *,
    now: float | None = None,
) -> list[dict[str, Any]]:
    """Query active operational observations at the given timestamp."""
    ref_now = time.time() if now is None else float(now)
    try:
        cur = conn.execute(
            """
            SELECT * FROM operational_observations
            WHERE expires_at IS NULL OR expires_at > ?
            ORDER BY timestamp ASC, observation_id ASC;
            """,
            (ref_now,),
        )
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error as error:
        raise PersistenceError(f"cannot query active operational observations at {ref_now}: {error}") from error


def row_to_operational_observation(row: Mapping[str, Any] | sqlite3.Row) -> OperationalObservation:
    """Convert a database row from operational_observations to OperationalObservation."""
    r = dict(row)
    detail_raw = r.get("detail_json")
    detail = json.loads(detail_raw) if detail_raw else None
    return OperationalObservation(
        observation_id=str(r["observation_id"]),
        producer=str(r["producer"]),
        observation_type=str(r["observation_type"]),
        provider=str(r["provider"]),
        profile=r.get("profile"),
        timestamp=float(r["timestamp"]),
        expires_at=float(r["expires_at"]) if r.get("expires_at") is not None else None,
        state_value=str(r["state_value"]),
        digest=r.get("digest"),
        detail=detail,
    )
