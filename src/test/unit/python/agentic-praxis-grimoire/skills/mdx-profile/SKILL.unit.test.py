#!/usr/bin/env python3
"""Focused APG88 MDX ownership, routing, and terminal-budget contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))

from agentic_praxis_grimoire import skills  # noqa: E402


NAME = "mdx-profile"
OTHER_NAME = "astro-profile"


def description(name: str) -> str:
    blob = (ROOT / f"skills/{name}/SKILL.md").read_bytes()
    return skills.parse_skill_metadata(f"skills/{name}/SKILL.md", blob).description


def test_mdx_leaf_owns_only_the_document_component_seam() -> None:
    text = (ROOT / f"skills/{NAME}/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for phrase in (
        "Markdown-to-JSX",
        "imports and exports",
        "expressions",
        "component provider",
        "compile-time",
        "runtime",
        "markdown-language-profile",
        "jsx-language-profile",
        "react-component-profile",
        "typescript-language-profile",
        "javascript-language-profile",
        "astro-profile",
    ):
        assert phrase.lower() in normalized.lower()
    assert "removing every JSX" in normalized


def test_mdx_boundary_fixture_is_exact_and_ordered() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg88-profile-boundary-scenarios.json").read_text()
    )
    rows = document["mdx"]
    assert [row["id"] for row in rows] == [f"APG88-MDX-{index:02d}" for index in range(1, 9)]
    assert [row["owner"] for row in rows] == [
        "mdx-profile",
        "mdx-profile",
        "markdown-language-profile",
        "jsx-language-profile",
        "react-component-profile",
        "typescript-language-profile",
        "javascript-language-profile",
        "astro-profile",
    ]
    assert "/" + "Users" + "/" not in json.dumps(rows)


def test_apg89_web_composition_preserves_the_mdx_seam() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-02"]["owner"] == NAME


def test_apg88_terminal_description_and_topology_budget_is_exact() -> None:
    mdx_bytes = len(description(NAME).encode("utf-8"))
    astro_bytes = len(description(OTHER_NAME).encode("utf-8"))
    combined = mdx_bytes + astro_bytes
    report = skills.context_footprint_report(
        blobs={
            path.relative_to(ROOT).as_posix(): path.read_bytes()
            for path in sorted((ROOT / "skills").glob("**/SKILL.md"))
        }
    )

    assert mdx_bytes == 214
    assert astro_bytes == 238
    assert 170 <= mdx_bytes <= 330
    assert 170 <= astro_bytes <= 330
    assert combined == 452
    assert combined <= 475
    assert report["skill_count"] == 39
    assert report["discoverable_skill_count"] == 39
    assert report["malformed"] == []
    assert report["total_description_bytes"] == 9504
    assert report["total_description_bytes"] <= 9527
    assert 9527 - report["total_description_bytes"] == 23


def test_mdx_projection_is_exact() -> None:
    projection = ROOT / f".agents/skills/{NAME}"
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
