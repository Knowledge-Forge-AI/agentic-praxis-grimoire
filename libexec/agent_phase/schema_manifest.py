"""Generate and inspect the normalized SQLite schema manifest for APGR."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
from typing import Any

try:
    from .persistence import SCHEMA_VERSION, migrate_schema
except (ImportError, ValueError):
    from agent_phase.persistence import SCHEMA_VERSION, migrate_schema

SCHEMA_MANIFEST_IDENTIFIER = "dispatcher-sqlite-schema-v5"


def generate_schema_manifest(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Generate normalized schema manifest for SQLite schema v5."""
    close_after = False
    if conn is None:
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON;")
        migrate_schema(conn)
        close_after = True

    try:
        tables_query = (
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name;"
        )
        tables = [r[0] for r in conn.execute(tables_query).fetchall()]

        tables_manifest: dict[str, Any] = {}
        for tbl in tables:
            # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
            cols: list[dict[str, Any]] = []
            for c in conn.execute(f"PRAGMA table_info({tbl});").fetchall():
                cols.append({
                    "cid": c[0],
                    "name": c[1],
                    "type": c[2],
                    "notnull": bool(c[3]),
                    "default_value": c[4],
                    "pk": c[5],
                })

            # PRAGMA foreign_key_list: id, seq, table, from, to, on_update, on_delete, match
            fks: list[dict[str, Any]] = []
            fk_rows = conn.execute(f"PRAGMA foreign_key_list({tbl});").fetchall()
            for f in sorted(fk_rows, key=lambda x: (x[0], x[1])):
                fks.append({
                    "id": f[0],
                    "seq": f[1],
                    "to_table": f[2],
                    "from_column": f[3],
                    "to_column": f[4],
                    "on_update": f[5],
                    "on_delete": f[6],
                    "match": f[7],
                })

            # PRAGMA index_list: seq, name, unique, origin, partial
            indexes: list[dict[str, Any]] = []
            idx_rows = conn.execute(f"PRAGMA index_list({tbl});").fetchall()
            for idx in sorted(idx_rows, key=lambda x: x[1]):
                idx_name = idx[1]
                unique = bool(idx[2])
                origin = idx[3] if len(idx) > 3 else ""
                partial = bool(idx[4]) if len(idx) > 4 else False
                idx_cols = [
                    ic[2]
                    for ic in conn.execute(f"PRAGMA index_info({idx_name});").fetchall()
                ]
                indexes.append({
                    "name": idx_name,
                    "unique": unique,
                    "origin": origin,
                    "partial": partial,
                    "columns": idx_cols,
                })

            tables_manifest[tbl] = {
                "columns": cols,
                "foreign_keys": fks,
                "indexes": indexes,
            }

        return {
            "schema": SCHEMA_MANIFEST_IDENTIFIER,
            "version": SCHEMA_VERSION,
            "tables": tables_manifest,
        }
    finally:
        if close_after:
            conn.close()


def manifest_path(repo_root: Path | None = None) -> Path:
    """Return canonical path to docs/architecture/dispatcher-sqlite-schema-v5.json."""
    root = (
        repo_root
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    return root / "docs" / "architecture" / f"{SCHEMA_MANIFEST_IDENTIFIER}.json"


def write_manifest(target_path: Path | None = None) -> Path:
    """Generate and write the schema manifest to disk."""
    path = target_path or manifest_path()
    manifest = generate_schema_manifest()
    raw = json.dumps(manifest, indent=2) + "\n"
    path.write_text(raw, encoding="utf-8")
    return path


if __name__ == "__main__":
    out = write_manifest()
    print(f"Wrote schema manifest to {out}")
