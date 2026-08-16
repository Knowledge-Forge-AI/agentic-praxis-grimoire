#!/usr/bin/env python3
"""Exact-token and rollback proof-boundary controls for APG66B Markdown."""

from __future__ import annotations

import json
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_markdown_candidate_contract import (  # noqa: E402
    parse_clauses,
    parse_coverage,
    scenario_support,
)
from apg_markdown_token_guard_contract import (  # noqa: E402
    exact_tokens,
    observed_rollback_classes,
    observed_semantic_signals,
    pending_resolution_is_contradicted,
)
from apg_markdown_vocabulary_contract import (  # noqa: E402
    ACCEPTED_ROUTE_TOKENS,
    ACCEPTED_VOCABULARY,
)


FIXTURE = json.loads(
    (ROOT / "src/test/fixtures/apg66-markdown-language-profile-scenarios.json")
    .read_text(encoding="utf-8")
)
ROWS = {row["id"]: row for row in FIXTURE["rows"]}
CLAUSES = parse_clauses(
    (ROOT / "skills/markdown-language-profile/SKILL.md").read_text(encoding="utf-8"),
    (ROOT / "docs/specs/markdown-language-profile.md").read_text(encoding="utf-8"),
)
COVERAGE = parse_coverage(
    (ROOT / "docs/specs/markdown-language-profile-scenario-coverage.md")
    .read_text(encoding="utf-8")
)


def _mapped_mutation(scenario: str, old: str, new: str) -> dict[str, str]:
    clauses = dict(CLAUSES)
    for clause_id in COVERAGE[scenario]:
        clauses[clause_id] = clauses[clause_id].replace(old, new)
    return clauses


@pytest.mark.parametrize("scenario", ("APG63-MD-032", "APG63-MD-034"))
def test_contradiction_rollbacks_remain_human_distinctions(scenario: str) -> None:
    result = scenario_support(ROWS[scenario], COVERAGE, CLAUSES)
    assert ROWS[scenario]["rollback_class"] not in result["rollback_classes"]
    assert "rollback_class" in result["human_review_required"]


def test_pending_resolution_contradiction_is_rejected_locally() -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-SEMANTIC-RISK"] += (
        "\nContent rollback may precede authoritative resolution."
    )
    result = scenario_support(ROWS["APG63-MD-034"], COVERAGE, clauses)
    assert "rollback:pending-resolution-contradiction" in result["missing"]


@pytest.mark.parametrize(
    "statement",
    (
        "xcontent rollback may precede authoritative resolution",
        "content rollback may precede authoritative resolution-ish",
        "non-content rollback may precede authoritative resolution",
        "content_rollback may precede authoritative resolution",
    ),
)
def test_pending_resolution_contradiction_rejects_larger_near_misses(
    statement: str,
) -> None:
    assert not pending_resolution_is_contradicted(statement)


@pytest.mark.parametrize(
    ("scenario", "old", "new", "result_field"),
    (
        ("APG63-MD-013", "markdown-language-profile", "not-markdown-language-profile", "owners"),
        ("APG63-MD-002", "selected", "non-selected", "axes"),
        ("APG63-MD-002", "proceed-routine", "non-proceed-routine", "axes"),
        ("APG63-MD-013", "embedded-language-owner", "embedded-language-ownerish", "owners"),
        ("APG63-MD-033", "navigation-failure", "navigation-failure-extra", "structural_signals"),
    ),
)
def test_larger_hyphenated_tokens_do_not_count_as_closed_tokens(
    scenario: str, old: str, new: str, result_field: str
) -> None:
    result = scenario_support(
        ROWS[scenario], COVERAGE, _mapped_mutation(scenario, old, new)
    )
    assert old not in result[result_field]


@pytest.mark.parametrize(
    ("token", "near_miss"),
    (
        ("normative-contradiction", "x-normative-contradiction"),
        ("selected", "selected-state"),
        ("stop-and-escalate", "stop-and-escalate-ish"),
        ("navigation-failure", "navigation-failure-extra"),
    ),
)
def test_closed_token_primitive_rejects_larger_near_miss(
    token: str, near_miss: str
) -> None:
    assert exact_tokens(near_miss, (token,)) == set()


@pytest.mark.parametrize(
    ("observer", "token", "exact", "near_miss"),
    (
        (observed_semantic_signals, "extension-unsupported", "unsupported construct", "xunsupported constructish"),
        (observed_rollback_classes, "record-predecision-behavior", "pre-decision behavior is recorded", "xpre-decision behavior is recordedish"),
        (observed_rollback_classes, "preserve-navigation-move-map", "preserve navigation and move map", "preserve navigation-failure and move map-extra"),
    ),
)
def test_phrase_aliases_use_the_same_exact_boundary(
    observer: object, token: str, exact: str, near_miss: str
) -> None:
    assert token in observer(exact)
    assert token not in observer(near_miss)


TOKEN_FAMILIES = {**ACCEPTED_VOCABULARY, "routes": ACCEPTED_ROUTE_TOKENS}


@pytest.mark.parametrize(
    ("family", "token"),
    tuple(
        (family, token)
        for family, tokens in TOKEN_FAMILIES.items()
        for token in tokens
    ),
    ids=lambda value: value,
)
def test_every_closed_token_uses_ascii_identifier_boundaries(
    family: str, token: str
) -> None:
    del family
    assert exact_tokens(token, (token,)) == {token}
    assert exact_tokens(f"(`{token}`),", (token,)) == {token}
    for near_miss in (
        f"x{token}", f"{token}x", f"x-{token}", f"{token}-x",
        f"x_{token}", f"{token}_x",
    ):
        assert exact_tokens(near_miss, (token,)) == set()
