#!/usr/bin/env python3
"""Lexical safety controls for the JavaScript profile leaf."""

from __future__ import annotations

import json

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
LEAF = (ROOT / "skills/javascript-language-profile/SKILL.md").read_text(encoding="utf-8")


def test_leaf_separates_language_host_and_evidence_axes() -> None:
    lowered = LEAF.lower()
    assert "parse goal" in lowered
    assert "host context" in lowered
    assert "goal evidence state" in lowered
    assert "host-wrapper" not in lowered
    assert "ecmascript job queue" not in lowered


def test_leaf_stops_absent_receivers_and_partial_coverage() -> None:
    lowered = LEAF.lower()
    assert "absent receiver" in lowered
    assert "stop-and-escalate" in lowered
    for marker in ("proxy", "reflect", "sharedarraybuffer", "ecma-402", "regular expression"):
        assert marker in lowered


def test_selection_and_checked_status_do_not_transfer_whole_file_ownership() -> None:
    lowered = " ".join(LEAF.lower().split())
    assert "`selected` means this profile answers the exact ecmascript decision" in lowered
    assert "it does not say who owns the file" in lowered
    assert "embedded-route` is reserved for a javascript region nested inside a different host file" in lowered
    assert "does not acquire its whole-file owner from checked status" in lowered
    assert "configuration module may remain `project-configuration-owner`" in lowered
    assert "checker selection and invocation evidence" in lowered
    assert "configuration, loader, build, or deployment decision" in lowered


def test_apg89_web_composition_preserves_ecmascript_semantics() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-07"]["owner"] == "javascript-language-profile"
