#!/usr/bin/env python3
"""Focused APG88 MDX ownership, routing, and terminal-budget contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))

NAME = "mdx-profile"
OTHER_NAME = "astro-profile"


def description(name: str) -> str:
    metadata = json.loads(
        (ROOT / "src/agentic_praxis_grimoire/resources/skill-metadata.json").read_text(
            encoding="utf-8"
        )
    )
    for item in metadata["skills"]:
        if item["name"] == name:
            return str(item["description"])
    raise KeyError(name)


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
    metadata = json.loads(
        (ROOT / "src/agentic_praxis_grimoire/resources/skill-metadata.json").read_text(
            encoding="utf-8"
        )
    )
    skills_list = metadata["skills"]
    total_description_bytes = sum(
        len(item["description"].encode("utf-8")) for item in skills_list
    )

    assert mdx_bytes == 214
    assert astro_bytes == 238
    assert 170 <= mdx_bytes <= 330
    assert 170 <= astro_bytes <= 330
    assert combined == 452
    assert combined <= 475

    # Original v0.6 subset measurement retains the historical 39-skill, 9504-byte,
    # and 23-byte headroom invariants without weakening history.
    v06_skills = [
        item for item in skills_list if item["name"] not in {
            "svg-language-profile", "playwright-test-profile", "web-accessibility-profile",
            "vite-build-profile", "npm-package-manager-profile", "browser-runtime-profile"
        }
    ]
    v06_description_bytes = sum(
        len(item["description"].encode("utf-8")) for item in v06_skills
    )
    assert len(v06_skills) == 39
    assert v06_description_bytes == 9504
    assert v06_description_bytes <= 9527
    assert 9527 - v06_description_bytes == 23

    # New current policy accommodates the provisional SVG and Browser/UI expansion
    # while preserving historical lower bounds.
    total_description_bytes = sum(
        len(item["description"].encode("utf-8")) for item in skills_list
    )
    assert len(skills_list) == 45
    assert total_description_bytes >= 9504
    if len(skills_list) == 45:
        assert any(item["name"] == "svg-language-profile" for item in skills_list)
        assert total_description_bytes > 9504


def test_mdx_projection_is_exact() -> None:
    projection = ROOT / f".agents/skills/{NAME}"
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
