#!/usr/bin/env python3
"""Failing-first APG66 Markdown candidate contract tests."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_markdown_candidate_contract import (  # noqa: E402
    REGISTER_BLOB_OID,
    orange_requires_unqualified_rollback,
    load_fixture,
    parse_clauses,
    parse_coverage,
    parse_frontmatter,
    parse_signal_table,
    scenario_support,
    targeted_guard_failures,
    validate_navigation,
)


FIXTURE_PATH = ROOT / "src/test/fixtures/apg66-markdown-language-profile-scenarios.json"
LEAF_PATH = ROOT / "skills/markdown-language-profile/SKILL.md"
SPEC_PATH = ROOT / "docs/specs/markdown-language-profile.md"
COVERAGE_PATH = ROOT / "docs/specs/markdown-language-profile-scenario-coverage.md"
FIXTURE = load_fixture(FIXTURE_PATH)
ROWS = {row["id"]: row for row in FIXTURE["rows"]}
SCENARIO_IDS = tuple(ROWS)


@pytest.fixture(scope="module")
def candidate() -> dict[str, object]:
    leaf = LEAF_PATH.read_text(encoding="utf-8")
    specification = SPEC_PATH.read_text(encoding="utf-8")
    coverage_text = COVERAGE_PATH.read_text(encoding="utf-8")
    return {
        "leaf": leaf,
        "specification": specification,
        "coverage_text": coverage_text,
        "clauses": parse_clauses(leaf, specification),
        "coverage": parse_coverage(coverage_text),
    }


def test_fixture_is_public_safe_and_bound_to_accepted_apg64() -> None:
    assert FIXTURE["authority"] == {
        "source_phase": "APG64",
        "register_blob_oid": REGISTER_BLOB_OID,
        "semantic_rows": 34,
        "process_rows": 0,
    }
    encoded = json.dumps(FIXTURE, sort_keys=True)
    assert "/" "Users/" not in encoded
    assert "/private/" not in encoded
    assert "APG63-MD-035" not in encoded
    assert "APG63-MD-036" not in encoded
    assert not ({"In", "Invariant", "Forbid"} & set(FIXTURE["rows"][0]))


def test_apg89_web_composition_preserves_pure_markdown_ownership() -> None:
    document = json.loads(
        (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
    )
    rows = {row["id"]: row for row in document["web"]}
    assert rows["APG89-WEB-01"]["owner"] == "markdown-language-profile"


def test_candidate_identity_and_canonical_frontmatter(candidate: dict[str, object]) -> None:
    frontmatter = parse_frontmatter(candidate["leaf"])
    assert frontmatter == {
        "name": "markdown-language-profile",
        "description": (
            "Use when a material decision depends on the repository's actual "
            "Markdown parser or selected-dialect document semantics, or on "
            "qualitative Markdown document-structure policy."
        ),
    }
    assert "[Markdown Language Profile](../../docs/specs/markdown-language-profile.md)" in candidate["leaf"]


def test_clause_and_coverage_navigation_is_closed(candidate: dict[str, object]) -> None:
    clauses = candidate["clauses"]
    coverage = candidate["coverage"]
    assert len(clauses) == 24
    assert set(coverage) == set(SCENARIO_IDS)
    assert not {"APG63-MD-035", "APG63-MD-036"} & set(coverage)
    referenced = [clause for mapped in coverage.values() for clause in mapped]
    assert set(referenced) == set(clauses)
    assert not (set(referenced) - set(clauses))
    validate_navigation(FIXTURE["rows"], coverage, clauses)


def test_effective_grammar_is_an_ordered_noncomposite_hierarchy(
    candidate: dict[str, object],
) -> None:
    grammar = candidate["clauses"]["MARKDOWN-EFFECTIVE-GRAMMAR"]
    ordered = [
        " ".join(match.group(2).split())
        for match in re.finditer(r"(?m)^(\d+)\. (.+(?:\n   .+)*)", grammar)
    ]
    assert len(ordered) == 4
    assert "actual repository renderer or parser" in ordered[0]
    assert "CommonMark 0.31.2" in ordered[1]
    assert "GFM 0.29" in ordered[2]
    assert "implementation-specific behavior" in ordered[3]
    normalized = " ".join(grammar.split())
    assert "never presented as one formally specified composite dialect" in normalized
    assert "never promises cross-context compatibility" in normalized


def test_all_structural_signals_have_structured_controls(
    candidate: dict[str, object],
) -> None:
    table = parse_signal_table(candidate["clauses"]["MARKDOWN-STRUCTURAL-SIGNALS"])
    assert set(table) == set(FIXTURE["vocabulary"]["structural_signals"])
    for signal, contract in table.items():
        assert contract["evidence_class"], signal
        assert contract["observable_and_scope"], signal
        assert contract["responses"], signal
        assert contract["false_positive_control"], signal
    assert table["deep-or-inconsistent-heading-hierarchy"]["responses"] == "inspect-before-judgment"
    assert table["multiple-independent-audiences"]["routes"] == "project-design"
    assert table["policy-evasion"]["routes"] == "project-policy"


def test_generated_legacy_and_exception_rules_are_bounded(
    candidate: dict[str, object],
) -> None:
    generated = " ".join(candidate["clauses"]["MARKDOWN-GENERATED"].split())
    legacy = " ".join(candidate["clauses"]["MARKDOWN-LEGACY-EXCEPTION"].split())
    assert "Generator-owned output is never hand-refactored" in generated
    assert "regeneration as the rollback path" in generated
    assert "only when change provenance evidences an attempt to avoid review" in generated
    assert "smallest safe correction" in legacy
    assert "Legacy length does not create a crisis by itself" in legacy
    exception_fields = {"authority", "scope", "reason", "validation", "rollback", "non-precedential"}
    assert all(field in legacy for field in exception_fields)


def test_no_numeric_bands_or_process_obligations_leak_into_candidate(
    candidate: dict[str, object],
) -> None:
    combined = candidate["leaf"] + "\n" + candidate["specification"]
    assert not re.search(r"(?i)\b(?:300|600|900)\s*(?:lines?|band|threshold)", combined)
    assert not re.search(r"(?i)\bpercentile(?:s)?\b", combined)
    assert "APG63-MD-035" not in candidate["coverage"]
    assert "APG63-MD-036" not in candidate["coverage"]
    assert "MARKDOWN-CORRECTED-STATE" not in candidate["clauses"]


@pytest.mark.parametrize("scenario_id", SCENARIO_IDS, ids=SCENARIO_IDS)
def test_all_semantic_scenarios_have_mechanical_navigation(
    candidate: dict[str, object], scenario_id: str,
) -> None:
    replay = scenario_support(
        ROWS[scenario_id], candidate["coverage"], candidate["clauses"]
    )
    assert "expected_consequence" not in replay
    assert replay["missing"] == [], (
        f"{scenario_id} mapped clauses do not satisfy mechanical navigation: {replay}"
    )


def test_targeted_candidate_guards_are_complete(candidate: dict[str, object]) -> None:
    assert targeted_guard_failures(candidate["clauses"]) == []


def test_orange_does_not_invent_rollback_for_navigation_only_decision(
    candidate: dict[str, object],
) -> None:
    row = ROWS["APG63-MD-033"]
    assert row["response"] == "bounded-local-decision"
    assert row["rollback_class"] == "none"
    assert not orange_requires_unqualified_rollback(
        candidate["clauses"]["MARKDOWN-VALIDATION"]
    )
