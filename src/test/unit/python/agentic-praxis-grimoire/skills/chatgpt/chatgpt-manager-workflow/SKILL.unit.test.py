#!/usr/bin/env python3
"""Focused ChatGPT-manager workflow routing contracts."""

from __future__ import annotations

import json

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
SKILL_ROOT = REPOSITORY_ROOT / "skills/chatgpt/chatgpt-manager-workflow"


def test_subrouter_owns_only_chatgpt_manager_capability_selection() -> None:
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    normalized_lower = normalized.lower()
    for phrase in (
        "select only among ChatGPT top-level-manager capabilities",
        "smallest sufficient",
        "select no skill",
        "Direct explicit selection",
        "Ordinary Codex",
        "no mandatory router chain",
    ):
        assert phrase.lower() in normalized_lower
    for prohibited_authority in (
        "approve or revise a roadmap",
        "compose the assignment",
        "dispatch an agent",
        "execute work",
        "review or accept a result",
        "continue automatically",
    ):
        assert prohibited_authority.lower() in normalized_lower


def test_subrouter_map_has_one_local_leaf_and_no_cross_domain_edge() -> None:
    capability_map = json.loads(
        (SKILL_ROOT / "references/capability-map.json").read_text(
            encoding="utf-8"
        )
    )
    assert capability_map["schema_version"] == 1
    assert capability_map["router_name"] == "chatgpt-manager-workflow"
    assert [
        entry["name"] for entry in capability_map["capabilities"]
    ] == ["composing-approved-roadmap-assignments"]


def test_general_router_has_one_subrouter_edge_and_no_manager_leaf_edge() -> None:
    capability_map = json.loads(
        (
            REPOSITORY_ROOT
            / "skills/agentic-praxis-grimoire-workflow/references/capability-map.json"
        ).read_text(encoding="utf-8")
    )
    names = [entry["name"] for entry in capability_map["capabilities"]]
    assert len(names) == 31
    assert "css-language-profile" in names
    assert "javascript-language-profile" in names
    assert "markdown-language-profile" in names
    assert "nodejs-runtime-profile" in names
    assert "typescript-language-profile" in names
    assert names.count("chatgpt-manager-workflow") == 1
    assert "composing-approved-roadmap-assignments" not in names
