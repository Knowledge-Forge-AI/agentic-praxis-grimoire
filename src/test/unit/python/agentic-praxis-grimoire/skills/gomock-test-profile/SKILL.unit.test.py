#!/usr/bin/env python3
"""Focused APG86 GoMock ownership and integration contract."""

from __future__ import annotations

import json
from pathlib import Path

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
NAME = "gomock-test-profile"


def test_gomock_leaf_owns_only_the_mock_component() -> None:
    text = (ROOT / f"skills/{NAME}/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for phrase in (
        "v0.6.0",
        "source, package, and archive",
        "generated",
        "Controller",
        "expectation",
        "call counts",
        "ordering",
        "matcher",
        "go-test-profile",
        "go-cmp-test-profile",
        "go-language-profile",
        "already selected",
    ):
        assert phrase.lower() in normalized.lower()


def test_gomock_finish_guidance_distinguishes_cleanup_reporters() -> None:
    text = (ROOT / f"skills/{NAME}/SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    assert "cleanup path silently tolerates a later duplicate `Finish`" in normalized
    assert "without cleanup support, a repeated `Finish` is a hard failure" in normalized
    assert "because `Finish` is not idempotent" not in normalized


def test_gomock_boundary_fixture_is_exact_and_ordered() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg86-profile-boundary-scenarios.json").read_text()
    )
    rows = document["gomock"]
    assert [row["id"] for row in rows] == [f"APG86-GOMOCK-{index:02d}" for index in range(1, 9)]
    assert [row["owner"] for row in rows[:4]] == [
        "gomock-test-profile",
        "go-test-profile",
        "go-cmp-test-profile",
        "go-language-profile",
    ]
    assert "/" + "Users" + "/" not in json.dumps(rows)


def test_apg89_go_composition_preserves_gomock_mechanics() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["go"]}
    assert rows["APG89-GO-03"]["owner"] == NAME


def test_gomock_projection_is_exact() -> None:
    projection = ROOT / f".agents/skills/{NAME}"
    assert projection.is_symlink()
    assert projection.readlink() == Path(f"../../skills/{NAME}")
