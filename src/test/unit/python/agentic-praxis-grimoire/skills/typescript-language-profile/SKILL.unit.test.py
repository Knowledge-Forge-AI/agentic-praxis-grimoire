#!/usr/bin/env python3
"""Unit checks for the APG75 TypeScript profile leaf."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_typescript_candidate_contract import parse_clauses, parse_frontmatter  # noqa: E402


LEAF = (ROOT / "skills/typescript-language-profile/SKILL.md").read_text(encoding="utf-8")
SPECIFICATION = (ROOT / "docs/specs/typescript-language-profile.md").read_text(encoding="utf-8")


def test_leaf_identity_and_clause_ownership_are_closed() -> None:
    frontmatter = parse_frontmatter(LEAF)
    assert frontmatter["name"] == "typescript-language-profile"
    clauses = parse_clauses(LEAF, SPECIFICATION)
    assert len(clauses) == 24
    assert len(clauses) == len(set(clauses))


def test_leaf_keeps_adjacent_owners_and_runtime_proof_outside_scope() -> None:
    normalized = " ".join((LEAF + "\n" + SPECIFICATION).split())
    assert "checked JavaScript use `embedded-route`" in normalized
    assert "runtime behavior" in normalized
    assert "static success offered as runtime proof" in normalized


def test_leaf_uses_qualitative_structure_policy_only() -> None:
    normalized = " ".join(LEAF.split()).lower()
    assert "numeric bands are forbidden" in normalized
    assert "300 lines" not in normalized
    assert "600 lines" not in normalized
    assert "900 lines" not in normalized


def test_apg89_web_composition_preserves_typescript_checking() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-06"]["owner"] == "typescript-language-profile"
