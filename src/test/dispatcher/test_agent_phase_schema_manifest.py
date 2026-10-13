"""Drift and validation tests for SQLite schema v5 manifest."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from agent_phase.persistence import SCHEMA_VERSION, migrate_schema
from agent_phase.schema_manifest import (
    SCHEMA_MANIFEST_IDENTIFIER,
    generate_schema_manifest,
    manifest_path,
)


def test_schema_manifest_matches_disk() -> None:
    """Ensure in-memory generated schema manifest matches committed JSON manifest."""
    path = manifest_path()
    assert path.is_file(), f"manifest file not found at {path}"

    disk_data = json.loads(path.read_text(encoding="utf-8"))
    generated = generate_schema_manifest()

    assert generated["schema"] == SCHEMA_MANIFEST_IDENTIFIER
    assert generated["version"] == SCHEMA_VERSION
    assert generated["version"] == 5

    assert generated == disk_data, "Drift detected between generated manifest and committed JSON!"


def test_schema_manifest_covers_all_tables() -> None:
    """Ensure manifest contains all expected tables and columns."""
    manifest = generate_schema_manifest()
    tables = manifest["tables"]

    expected_tables = {
        "runs",
        "actor_bindings",
        "semantic_responsibilities",
        "invocation_attempts",
        "route_resolutions",
        "operational_observations",
        "invocation_observation_relations",
        "candidates",
        "review_records",
        "review_findings",
        "review_dispositions",
        "artifacts",
        "completion_receipts",
        "resume_relations",
        "configuration_provenance",
        "schema_migrations",
        "review_mutation_observations",
        "review_mutation_policies",
        "legacy_quarantine_review_mutation_observations",
        "legacy_quarantine_review_mutation_policies",
    }

    assert expected_tables.issubset(set(tables.keys()))

    # Verify runs table shape
    runs = tables["runs"]
    run_cols = {c["name"]: c for c in runs["columns"]}
    assert run_cols["run_id"]["pk"] == 1
    assert run_cols["project"]["notnull"] is True

    # Verify review_mutation_policies nullable policies in v5
    pol = tables["review_mutation_policies"]
    pol_cols = {c["name"]: c for c in pol["columns"]}
    assert pol_cols["worktree_policy"]["notnull"] is False
    assert pol_cols["index_policy"]["notnull"] is False
    assert pol_cols["head_policy"]["notnull"] is False
    assert pol_cols["resolved_mode"]["notnull"] is False
    assert pol_cols["policy_generation"]["notnull"] is True

    # Verify quarantine tables exist and have quarantine columns
    for qtbl in ("legacy_quarantine_review_mutation_observations", "legacy_quarantine_review_mutation_policies"):
        qcols = {c["name"]: c for c in tables[qtbl]["columns"]}
        assert "quarantined_at" in qcols
        assert "quarantine_reason" in qcols
        assert qcols["quarantined_at"]["notnull"] is True
