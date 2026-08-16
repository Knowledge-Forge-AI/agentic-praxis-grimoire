#!/usr/bin/env python3
"""Mutation checks for the maintained CSS profile contract."""

from copy import deepcopy
from pathlib import Path
import re
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_css_profile_candidate_contract import (  # noqa: E402
    ContractError,
    cascade_rank,
    current_color,
    custom_property_consequence,
    load_scenario_fixture,
    logical_inline_start,
    media_query_branch,
    nesting_specificity,
    pseudo_box_generated,
    selector_list_forgiving,
    selector_specificity,
    shorthand_longhands,
    supports_declaration_result,
    validate_candidate,
    validate_scenario_fixture,
)


LEAF = (ROOT / "skills/css-language-profile/SKILL.md").read_text(encoding="utf-8")
SPEC = (ROOT / "docs/specs/css-language-profile.md").read_text(encoding="utf-8")
COVERAGE = (ROOT / "docs/specs/css-language-profile-scenario-coverage.md").read_text(encoding="utf-8")
SCENARIOS = load_scenario_fixture(ROOT / "src/test/fixtures/apg77-css-language-profile-scenarios.json")


@pytest.mark.parametrize(
    ("needle", "replacement"),
    [
        ("proceed-routine", "route-to-owner"),
        ("normative module is selected by the construct and claim", "project picks CSS levels"),
        ("style attribute contains CSS declarations", "style attribute is non-CSS"),
        ("recognized SVG presentation attribute", "SVG attributes are non-CSS"),
        ("read-only CSS semantic decision", "edit permission required before reading"),
        ("does not grant edit permission", "grants edit permission"),
        ("winner within an explicitly bounded declaration set", "global winner"),
    ],
)
def test_candidate_semantic_mutations_fail(needle: str, replacement: str) -> None:
    pattern = re.compile(r"\s+".join(map(re.escape, needle.split())), re.IGNORECASE)
    assert pattern.search(LEAF + SPEC)
    with pytest.raises(ContractError):
        validate_candidate(
            pattern.sub(replacement, LEAF),
            pattern.sub(replacement, SPEC),
            COVERAGE,
        )


def test_scenario_schema_and_evidence_mutations_fail() -> None:
    fifth = deepcopy(SCENARIOS)
    fifth["vocabulary"]["responses"].append("route-to-owner")
    with pytest.raises(ContractError):
        validate_scenario_fixture(fifth)

    overlap = deepcopy(SCENARIOS)
    overlap["rows"][0]["required"] = [overlap["rows"][0]["present"][0]]
    with pytest.raises(ContractError):
        validate_scenario_fixture(overlap)

    media = deepcopy(SCENARIOS)
    media["rows"][15]["conclusion"] = "unknown media feature evaluates false"
    with pytest.raises(ContractError):
        validate_scenario_fixture(media)


@pytest.mark.parametrize(
    "injection",
    [
        " 300 line threshold",
        " record-growth-state",
        " sixty-row exact action map",
        " automatically convert CSS to Sass",
    ],
)
def test_forbidden_policy_mutations_fail(injection: str) -> None:
    with pytest.raises(ContractError):
        validate_candidate(LEAF + injection, SPEC, COVERAGE)


def test_selector_forgiveness_and_specificity_are_computed_independently() -> None:
    assert selector_list_forgiving("is")
    assert selector_list_forgiving("where")
    assert not selector_list_forgiving("not")
    assert not selector_list_forgiving("has")
    assert not selector_list_forgiving(None)
    assert selector_specificity(".menu a") == (0, 1, 1)
    assert selector_specificity(":is(.menu, #menu-primary) a") == (1, 0, 1)
    assert selector_specificity(":where(.menu, #menu-primary) a") == (0, 0, 1)
    assert selector_specificity("a:not(.menu, #menu-primary)") == (1, 0, 1)


def test_bounded_author_cascade_computes_layer_and_element_attached_order() -> None:
    normal_first = cascade_rank(
        important=False, element_attached=False, layer_index=0,
        specificity=(0, 1, 0), order=1,
    )
    normal_unlayered = cascade_rank(
        important=False, element_attached=False, layer_index=None,
        specificity=(0, 0, 1), order=0,
    )
    important_first = cascade_rank(
        important=True, element_attached=False, layer_index=0,
        specificity=(0, 0, 1), order=0,
    )
    important_later = cascade_rank(
        important=True, element_attached=False, layer_index=1,
        specificity=(1, 0, 0), order=9,
    )
    attached = cascade_rank(
        important=False, element_attached=True, layer_index=None,
        specificity=(0, 0, 0), order=0,
    )
    sheet = cascade_rank(
        important=False, element_attached=False, layer_index=None,
        specificity=(99, 0, 0), order=99,
    )
    assert normal_unlayered > normal_first
    assert important_first > important_later
    assert attached > sheet


def test_media_query_branches_and_supports_boundary_are_distinct() -> None:
    assert media_query_branch("unknown-feature") == "unknown-does-not-match"
    assert media_query_branch("unknown-feature", negated=True) == "unknown-does-not-match"
    assert media_query_branch("unknown-value") == "unknown-does-not-match"
    assert media_query_branch("grammar-invalid") == "not-all-does-not-match"
    assert media_query_branch("unknown-media-type") == "does-not-match"
    assert media_query_branch("unknown-media-type", negated=True) == "matches"
    assert media_query_branch("known") == "environment-required"
    assert supports_declaration_result(accepted_and_usable=True) == (
        "implementation-support-not-render"
    )


def test_custom_property_and_shorthand_consequences_are_computed() -> None:
    assert custom_property_consequence("missing-with-fallback") == "fallback"
    assert custom_property_consequence("empty") == "substitute-empty-then-validate"
    assert custom_property_consequence("cycle") == "initial"
    assert custom_property_consequence("cycle", target_inherits=True) == "inherited"
    assert custom_property_consequence("cycle", registered_syntax="<color>") == (
        "registered-initial-or-inherited"
    )
    result = shorthand_longhands(
        {"padding-top": "3px", "padding-inline-start": "12px"},
        {"padding-right": "8px", "padding-bottom": "8px", "padding-left": "8px"},
        ("padding-top", "padding-right", "padding-bottom", "padding-left"),
        "8px",
    )
    assert result["padding-top"] == "8px"
    assert result["padding-inline-start"] == "12px"


def test_nesting_logical_current_color_and_pseudo_boundaries_are_computed() -> None:
    assert nesting_specificity([".nav", "#primary"], ".link") == (1, 1, 0)
    assert logical_inline_start(
        writing_mode="horizontal-tb", direction="ltr", text_orientation="mixed"
    ) == "left"
    assert logical_inline_start(
        writing_mode="horizontal-tb", direction="rtl", text_orientation="mixed"
    ) == "right"
    assert current_color("#1f4f8f") == "#1f4f8f"
    assert pseudo_box_generated(content='"label"', replaced=False, displayed=True)
    assert not pseudo_box_generated(content="normal", replaced=False, displayed=True)
    assert not pseudo_box_generated(content='"label"', replaced=True, displayed=True)
    assert not pseudo_box_generated(content='"label"', replaced=False, displayed=False)


def test_every_scenario_consequence_and_route_owner_is_mutation_closed() -> None:
    for index, row in enumerate(SCENARIOS["rows"]):
        mutated = deepcopy(SCENARIOS)
        mutated["rows"][index]["conclusion"] = "unrelated nonempty text"
        with pytest.raises(ContractError):
            validate_scenario_fixture(mutated)

    route = deepcopy(SCENARIOS)
    route["rows"][1]["routes"] = ["DOM and browser owner"]
    with pytest.raises(ContractError, match="unknown route owner"):
        validate_scenario_fixture(route)
