#!/usr/bin/env python3
"""Focused APG88 Astro ownership and routing contract."""

from __future__ import annotations

import json
from pathlib import Path

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
NAME = "astro-profile"


def test_astro_leaf_owns_only_framework_project_and_execution_semantics() -> None:
    text = (ROOT / f"skills/{NAME}/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for phrase in (
        ".astro",
        "frontmatter/template",
        "islands",
        "client directives",
        "server-versus-client",
        "content collections",
        "file-based routing",
        "integration configuration",
        "react-component-profile",
        "jsx-language-profile",
        "mdx-profile",
        "typescript-language-profile",
        "nodejs-runtime-profile",
        "Vite",
        "Starlight",
        "styling",
        "accessibility",
        "deployment",
    ):
        assert phrase.lower() in normalized.lower()
    assert "where code runs" in normalized


def test_astro_boundary_fixture_is_exact_and_ordered() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg88-profile-boundary-scenarios.json").read_text()
    )
    rows = document["astro"]
    assert [row["id"] for row in rows] == [f"APG88-ASTRO-{index:02d}" for index in range(1, 10)]
    assert [row["owner"] for row in rows] == [
        "astro-profile",
        "astro-profile",
        "astro-profile",
        "react-component-profile",
        "mdx-profile",
        "jsx-language-profile",
        "typescript-language-profile",
        "nodejs-runtime-profile",
        "project-owner",
    ]
    assert "/" + "Users" + "/" not in json.dumps(rows)


def test_apg89_web_composition_preserves_astro_placement() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-03"]["owner"] == NAME


def test_astro_projection_is_exact() -> None:
    projection = ROOT / f".agents/skills/{NAME}"
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
