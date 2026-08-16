#!/usr/bin/env python3
"""Maintained unit contract for the CSS language profile."""

from pathlib import Path
import sys

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_css_profile_candidate_contract import (  # noqa: E402
    load_scenario_fixture,
    validate_candidate,
)


LEAF = ROOT / "skills/css-language-profile/SKILL.md"
SPEC = ROOT / "docs/specs/css-language-profile.md"
COVERAGE = ROOT / "docs/specs/css-language-profile-scenario-coverage.md"
SCENARIOS = ROOT / "src/test/fixtures/apg77-css-language-profile-scenarios.json"


def test_candidate_and_candidate_independent_oracle_are_coherent() -> None:
    validate_candidate(
        LEAF.read_text(encoding="utf-8"),
        SPEC.read_text(encoding="utf-8"),
        COVERAGE.read_text(encoding="utf-8"),
    )
    fixture = load_scenario_fixture(SCENARIOS)
    assert len(fixture["rows"]) == 45


def test_oracle_has_exact_semantic_fixture_and_target_families() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    ids = [row["id"] for row in fixture["rows"]]
    assert len([item for item in ids if item.startswith("APG77-CSS-")]) == 24
    assert len([item for item in ids if item.startswith("APG77-FX-")]) == 14
    assert len([item for item in ids if item.startswith("APG77-TARGET-")]) == 7
