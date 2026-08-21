#!/usr/bin/env python3
"""Focused APG86 Vitest ownership and integration contract."""

from __future__ import annotations

import json
from pathlib import Path

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
NAME = "vitest-test-profile"


def test_vitest_leaf_owns_runner_mechanics_without_adjacent_semantics() -> None:
    text = (ROOT / f"skills/{NAME}/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for phrase in (
        "Vitest 4.1",
        "configuration",
        "projects",
        "environment",
        "assertion",
        "module mocking",
        "fake timers",
        "isolation",
        "snapshot",
        "coverage provider",
        "javascript-language-profile",
        "typescript-language-profile",
        "nodejs-runtime-profile",
        "react-component-profile",
        "implementing-with-test-discipline",
    ):
        assert phrase.lower() in normalized.lower()


def test_vitest_boundary_fixture_is_exact_and_ordered() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg86-profile-boundary-scenarios.json").read_text()
    )
    rows = document["vitest"]
    assert [row["id"] for row in rows] == [f"APG86-VITEST-{index:02d}" for index in range(1, 9)]
    assert [row["owner"] for row in rows[:5]] == [
        "vitest-test-profile",
        "javascript-language-profile",
        "typescript-language-profile",
        "implementing-with-test-discipline",
        "react-component-profile",
    ]
    assert "/" + "Users" + "/" not in json.dumps(rows)


def test_apg89_web_composition_preserves_vitest_runner_mechanics() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-09"]["owner"] == NAME


def test_vitest_projection_is_exact() -> None:
    projection = ROOT / f".agents/skills/{NAME}"
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
