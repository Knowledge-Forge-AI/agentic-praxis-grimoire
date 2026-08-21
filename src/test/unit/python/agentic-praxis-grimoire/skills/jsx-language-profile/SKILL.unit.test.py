#!/usr/bin/env python3
"""Focused APG87 JSX ownership, routing, and budget contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))

from agentic_praxis_grimoire import skills  # noqa: E402


NAME = "jsx-language-profile"
OTHER_NAME = "react-component-profile"


def description(name: str) -> str:
    blob = (ROOT / f"skills/{name}/SKILL.md").read_bytes()
    return skills.parse_skill_metadata(f"skills/{name}/SKILL.md", blob).description


def test_jsx_leaf_owns_only_library_independent_syntax_and_transform() -> None:
    text = (ROOT / f"skills/{NAME}/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for phrase in (
        "element, attribute, and child grammar",
        "expression containers",
        "fragments",
        "spread",
        "escaping",
        "jsxImportSource",
        "automatic",
        "classic",
        ".jsx",
        ".tsx",
        "react-component-profile",
        "typescript-language-profile",
        "javascript-language-profile",
        "nodejs-runtime-profile",
        "mdx-profile",
        "astro-profile",
    ):
        assert phrase.lower() in normalized.lower()
    assert "question answerable without naming a component library" in normalized


def test_jsx_boundary_fixture_is_exact_and_routes_are_installed() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg87-profile-boundary-scenarios.json").read_text()
    )
    rows = document["jsx"]
    assert [row["id"] for row in rows] == [f"APG87-JSX-{index:02d}" for index in range(1, 9)]
    assert [row["owner"] for row in rows] == [
        "jsx-language-profile",
        "jsx-language-profile",
        "typescript-language-profile",
        "javascript-language-profile",
        "react-component-profile",
        "nodejs-runtime-profile",
        "mdx-profile",
        "astro-profile",
    ]
    for owner in ("mdx-profile", "astro-profile"):
        assert (ROOT / f"skills/{owner}/SKILL.md").is_file()
        assert (ROOT / f".agents/skills/{owner}").is_symlink()
    assert "/" + "Users" + "/" not in json.dumps(rows)


def test_apg89_web_composition_preserves_jsx_transform_semantics() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-05"]["owner"] == NAME


def test_apg87_description_pair_stays_byte_stable_in_apg88() -> None:
    jsx_bytes = len(description(NAME).encode("utf-8"))
    react_bytes = len(description(OTHER_NAME).encode("utf-8"))
    combined = jsx_bytes + react_bytes
    report = skills.context_footprint_report(
        blobs={
            path.relative_to(ROOT).as_posix(): path.read_bytes()
            for path in sorted((ROOT / "skills").glob("**/SKILL.md"))
        }
    )

    assert 170 <= jsx_bytes <= 330
    assert 170 <= react_bytes <= 330
    assert combined == 516
    assert 340 <= combined <= 651
    assert report["skill_count"] == 39
    assert report["discoverable_skill_count"] == 39
    assert report["malformed"] == []
    assert report["total_description_bytes"] == 9504
    assert report["total_description_bytes"] <= 9527
    assert report["total_description_bytes"] - 7967 == 1537
    assert 9527 - report["total_description_bytes"] == 23


def test_jsx_projection_is_exact() -> None:
    projection = ROOT / f".agents/skills/{NAME}"
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
