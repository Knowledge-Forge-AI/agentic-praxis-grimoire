#!/usr/bin/env python3
"""Lexical and routing controls for the Node.js runtime profile leaf."""

from __future__ import annotations

import json

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
LEAF = (ROOT / "skills/nodejs-runtime-profile/SKILL.md").read_text(encoding="utf-8")


def test_leaf_requires_an_established_exact_node_execution_role() -> None:
    lowered = " ".join(LEAF.lower().split())
    for phrase in (
        "exact runtime version",
        "platform",
        "architecture",
        "flags",
        "package scope",
        "loader identity",
        "whole-file owner",
    ):
        assert phrase in lowered


def test_leaf_keeps_language_package_manager_and_security_nonowners_closed() -> None:
    for exact_nonowner in (
        "- ECMAScript language semantics: scope, coercion, ordinary object semantics,",
        "- TypeScript: parsing, checking, inference, declaration emit, compiler options,",
        "- package managers: npm, pnpm, Yarn, or Bun installation, registry selection,",
        "- network and security: DNS correctness, HTTP application correctness, TLS",
        "  deployment exposure;",
    ):
        assert exact_nonowner in LEAF


def test_leaf_preserves_exact_stop_and_evidence_boundaries() -> None:
    lowered = LEAF.lower()
    assert "stop or escalate" in lowered
    assert "unresolved runtime role" in lowered
    assert "exact runtime" in lowered
    assert "evidence and completion" in lowered


def test_leaf_declares_the_integrated_lifecycle_independently() -> None:
    assert "Lifecycle: `provisionally-integrated`." in LEAF
    assert "Lifecycle ADR: `Accepted with amendment`." in LEAF


def test_apg89_web_composition_preserves_node_runtime_ownership() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-08"]["owner"] == "nodejs-runtime-profile"
