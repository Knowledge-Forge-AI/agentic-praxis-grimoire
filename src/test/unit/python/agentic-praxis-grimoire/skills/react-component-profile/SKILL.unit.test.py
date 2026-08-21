#!/usr/bin/env python3
"""Focused APG87 React ownership and routing contract."""

from __future__ import annotations

import json
from pathlib import Path

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
NAME = "react-component-profile"


def test_react_leaf_owns_host_independent_component_semantics() -> None:
    text = (ROOT / f"skills/{NAME}/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for phrase in (
        "component composition",
        "prop contracts",
        "render",
        "re-render",
        "state",
        "Effect",
        "Rules of Hooks",
        "context",
        "memoization",
        "error boundaries",
        "component testing",
        "jsx-language-profile",
        "typescript-language-profile",
        "javascript-language-profile",
        "vitest-test-profile",
        "implementing-with-test-discipline",
        "mdx-profile",
        "astro-profile",
    ):
        assert phrase.lower() in normalized.lower()
    assert "rendered by any host" in normalized


def test_react_boundary_fixture_is_exact_and_ordered() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg87-profile-boundary-scenarios.json").read_text()
    )
    rows = document["react"]
    assert [row["id"] for row in rows] == [f"APG87-REACT-{index:02d}" for index in range(1, 11)]
    assert [row["owner"] for row in rows] == [
        "react-component-profile",
        "react-component-profile",
        "react-component-profile",
        "react-component-profile",
        "jsx-language-profile",
        "typescript-language-profile",
        "vitest-test-profile",
        "implementing-with-test-discipline",
        "astro-profile",
        "mdx-profile",
    ]
    assert "/" + "Users" + "/" not in json.dumps(rows)


def test_apg89_web_composition_preserves_react_component_semantics() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-04"]["owner"] == NAME


def test_react_projection_is_exact() -> None:
    projection = ROOT / f".agents/skills/{NAME}"
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
