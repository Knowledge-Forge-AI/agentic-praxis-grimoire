#!/usr/bin/env python3
"""Source and numeric polarity controls for APG66B Markdown."""

from __future__ import annotations

import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_markdown_candidate_contract import (  # noqa: E402
    parse_clauses,
    targeted_guard_failures,
)
from apg_markdown_polarity_guard_contract import (  # noqa: E402
    MACHINE_SOURCE_GUARDS,
    SOURCE_DIRECT_NEGATIONS,
    source_guard_passes,
)


CLAUSES = parse_clauses(
    (ROOT / "skills/markdown-language-profile/SKILL.md").read_text(encoding="utf-8"),
    (ROOT / "docs/specs/markdown-language-profile.md").read_text(encoding="utf-8"),
)


@pytest.mark.parametrize(
    "scenario", tuple(MACHINE_SOURCE_GUARDS), ids=tuple(MACHINE_SOURCE_GUARDS)
)
def test_each_source_guard_rejects_marker_negation_and_reverse_ownership(
    scenario: str,
) -> None:
    marker = MACHINE_SOURCE_GUARDS[scenario]
    assert not source_guard_passes(scenario, f"{marker} is not required")
    assert not source_guard_passes(scenario, f"evidence is not owned by {marker}")


@pytest.mark.parametrize(
    ("scenario", "statement"),
    (
        ("APG63-MD-013", "profile owns fence. The profile does not own the fence."),
        ("APG63-MD-030", "project input is not an evidentiary source."),
        ("APG63-MD-032", "project-policy is not the source owner."),
        ("APG63-MD-034", "project-policy does not require repository evidence."),
        ("APG63-MD-034", "repository evidence is not required."),
    ),
)
def test_reproduced_source_negations_fail(scenario: str, statement: str) -> None:
    assert not source_guard_passes(scenario, statement)


@pytest.mark.parametrize(
    "scenario", tuple(SOURCE_DIRECT_NEGATIONS), ids=tuple(SOURCE_DIRECT_NEGATIONS)
)
def test_each_source_guard_rejects_natural_direct_negations(scenario: str) -> None:
    marker = MACHINE_SOURCE_GUARDS[scenario]
    for contradiction in SOURCE_DIRECT_NEGATIONS[scenario]:
        assert not source_guard_passes(
            scenario, f"{marker}. However, {contradiction}."
        )


def test_unrelated_source_negative_does_not_false_fail_fence_source() -> None:
    assert source_guard_passes(
        "APG63-MD-013",
        "profile owns fence. Repository evidence is not required elsewhere.",
    )


@pytest.mark.parametrize(
    "scenario", tuple(MACHINE_SOURCE_GUARDS), ids=tuple(MACHINE_SOURCE_GUARDS)
)
def test_each_source_guard_accepts_positive_and_rejects_near_miss(
    scenario: str,
) -> None:
    marker = MACHINE_SOURCE_GUARDS[scenario]
    assert source_guard_passes(scenario, f"({marker}).")
    assert not source_guard_passes(scenario, f"{marker}-extra")


@pytest.mark.parametrize(
    "statement",
    (
        "A 500-line document is not automatically high risk.",
        "This example records 500 lines as descriptive inspection evidence only.",
        "500 lines is descriptive and triggers no signal.",
        "500 lines authorizes no split.",
        "500 lines is insufficient to classify the document.",
        "500 lines may prompt inspection.",
        "No 500-line threshold exists.",
        "500 lines is not a threshold.",
        "A document with 500 lines does not select a response by count.",
        "500 lines is descriptive, but the parser configuration triggers a warning.",
        "500 lines is descriptive; the parser triggers a warning.",
        "500 lines is descriptive while repository tooling triggers a warning.",
        "500 lines is descriptive, but reviewers select Orange for semantic risk.",
        "500 lines is descriptive; CI triggers a warning.",
        "500 lines is descriptive while authors split the document for navigability.",
        "500 lines is descriptive but reviewers deliberately select Orange.",
        "500 lines is descriptive but reviewers may deliberately select Orange.",
        "500 lines is descriptive but reviewers continue selecting Orange.",
        "500 lines is descriptive but reviewers shall select Orange.",
        "500 lines is descriptive but reviewers keep selecting Orange.",
        "500 lines is descriptive but reviewers proceed to authorize a split.",
        "500 lines is descriptive but reviewers keep on selecting Orange.",
        "500 lines is descriptive but reviewers remain fully authorized to split.",
        "500 lines is descriptive but reviewers proceed routinely to authorize a split.",
        "500 lines is descriptive but reviewers continue routinely to authorize a split.",
        "500 lines does not trigger a signal and does not split the document.",
        "`500 lines` is descriptive inspection evidence only.",
        "In a table cell, 500 lines does not fire a signal or select a response.",
    ),
)
def test_descriptive_and_negative_counts_are_allowed(statement: str) -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-STRUCTURAL-POLICY"] += f"\n{statement}"
    assert "no-numeric-bands" not in targeted_guard_failures(clauses)


def test_unrelated_scenario_count_is_not_numeric_line_policy() -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-STRUCTURAL-POLICY"] += (
        "\nThe 34 scenarios require human review."
    )
    assert "no-numeric-bands" not in targeted_guard_failures(clauses)


@pytest.mark.parametrize(
    "statement",
    (
        "A 500-line threshold applies.",
        "At 500 lines classify Orange.",
        "500 lines triggers bounded-local-decision.",
        "At 500 lines split the document.",
        "300–599 is Yellow.",
        "300-599 lines are Orange.",
        "A 500 line band selects stop-and-escalate.",
        "A 500 lines threshold authorizes a split.",
        "No 500-line threshold exists, but at 600 lines classify Orange.",
        "500 lines does not classify Green; 600 lines classifies Orange.",
        "500 lines does not classify Green and 600 lines classifies Orange.",
        "500 lines is not a threshold and a 600-line threshold applies.",
        "A threshold applies at 500 lines.",
        "Yellow is 300-599 lines.",
        "500 lines does not select a response and at 600 lines select stop-and-escalate.",
        "500 lines does not fire a signal while 600 lines triggers bounded-local-decision.",
        "(`500 lines` selects Orange) in a table cell.",
        "500 lines does not classify a document but triggers Orange.",
        "500 lines is descriptive inspection evidence and selects bounded-local-decision.",
        "A 500-line document is not automatically high risk while authorizing a split.",
        "500 lines does not fire a signal; therefore select Orange.",
        "A 500-line count may prompt inspection and then requires a split.",
        "500 lines may prompt inspection and split the document.",
        "500 lines is descriptive; it triggers Orange.",
        "500–700 lines are descriptive but select Yellow.",
        "500 lines is descriptive: select Orange.",
        "500 lines is descriptive, therefore select Orange.",
        "500 lines is descriptive and then select Orange.",
        "500 lines is descriptive but often triggers Orange.",
        "500 lines is descriptive and perhaps selects Orange.",
        "500 lines is descriptive and may select Orange.",
        "500 lines is descriptive and must trigger Orange.",
        "500 lines is descriptive and can authorize a split.",
        "500 lines is descriptive and is selecting Orange.",
        "500 lines is descriptive and has triggered Orange.",
        "500 lines is descriptive and seems to select Orange.",
        "500 lines is descriptive and appears to trigger Orange.",
        "500 lines is descriptive and continues to authorize a split.",
        "500 lines is descriptive and begins selecting Orange.",
        "500 lines is descriptive and starts triggering Orange.",
        "500 lines is descriptive and shall select Orange.",
        "500 lines is descriptive and ought to select Orange.",
        "500 lines is descriptive and needs to trigger Orange.",
        "500 lines is descriptive and keeps selecting Orange.",
        "500 lines is descriptive and remains authorized to split the document.",
        "500 lines is descriptive and stops selecting Orange.",
        "500 lines is descriptive and finishes triggering Orange.",
        "500 lines is descriptive and proceeds to authorize a split.",
        "500 lines is descriptive and keeps on selecting Orange.",
        "500 lines is descriptive and remains fully authorized to split the document.",
        "500 lines is descriptive and proceeds routinely to authorize a split.",
        "500 lines is descriptive and continues routinely to authorize a split.",
        "500 lines triggers Orange but does not classify the document.",
        "500 lines triggers Orange and remains descriptive evidence.",
        "(`500 lines` may prompt inspection and then requires a split).",
    ),
)
def test_normative_numeric_policy_is_rejected(statement: str) -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-STRUCTURAL-POLICY"] += f"\n{statement}"
    assert "no-numeric-bands" in targeted_guard_failures(clauses)


@pytest.mark.parametrize(
    "scenario", tuple(MACHINE_SOURCE_GUARDS), ids=tuple(MACHINE_SOURCE_GUARDS)
)
@pytest.mark.parametrize(
    "contradiction",
    (
        "Evidence from {marker} must not be used.",
        "No evidence from {marker} may be considered.",
        "Evidence from {marker} is irrelevant.",
        "Evidence from {marker} is invalid evidence.",
        "Evidence from {marker} must be ignored.",
        "Do not claim {marker}.",
        "The following rejected phrase must not be used: {marker}.",
        'The rejected quotation is: "{marker}."',
        "Suppose {marker}.",
        '"{marker}."',
        "‘{marker}.’",
        "“{marker}.”",
        "«{marker}.»",
        "Assume {marker}.",
        "If {marker}, then continue.",
        "Were {marker} true, it would be relevant.",
        "Consider whether {marker}.",
        "It is false that {marker}.",
        "Hypothetically, {marker}; reject that claim.",
        "The phrase {marker} is rejected.",
        "This hypothetical is explicitly denied: {marker}.",
        "The hypothetical claim {marker} is explicitly disclaimed.",
    ),
)
def test_each_source_guard_rejects_bounded_direct_contradictions(
    scenario: str, contradiction: str
) -> None:
    marker = MACHINE_SOURCE_GUARDS[scenario]
    statement = f"{marker}. {contradiction.format(marker=marker)}"
    assert not source_guard_passes(scenario, statement)


@pytest.mark.parametrize(
    ("scenario", "statement"),
    (
        (
            "APG63-MD-034",
            "project-policy. Repository evidence must not be used.",
        ),
        (
            "APG63-MD-034",
            "project-policy. No repository evidence may be considered.",
        ),
        ("APG63-MD-033", "navigation provides no evidence."),
        (
            "APG63-MD-030",
            "project input is irrelevant to the decision.",
        ),
        (
            "APG63-MD-031",
            "bounded reviewer judgment is invalid evidence.",
        ),
        (
            "APG63-MD-020",
            "parser-established boundary must be ignored.",
        ),
    ),
)
def test_reproduced_source_contradiction_variants_fail(
    scenario: str, statement: str
) -> None:
    assert not source_guard_passes(scenario, statement)
