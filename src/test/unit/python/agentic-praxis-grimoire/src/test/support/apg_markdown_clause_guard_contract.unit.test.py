#!/usr/bin/env python3
"""Clause-polarity state controls for APG66C Markdown evidence."""

from __future__ import annotations

import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_markdown_clause_guard_contract import (  # noqa: E402
    ABSENT,
    CONFLICTED,
    NEGATIVE,
    POSITIVE,
    TARGETED_GUARD_MARKERS,
    combined_guard_state,
    guard_state,
    local_guard_observations,
    unconditional_rollback_state,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("navigation-failure applies.", POSITIVE),
        ("navigation-failure does not apply.", NEGATIVE),
        (
            "navigation-failure applies. navigation-failure does not apply.",
            CONFLICTED,
        ),
        ("navigation-failure-extra applies.", ABSENT),
        (
            "navigation-failure applies. another-signal does not apply.",
            POSITIVE,
        ),
        ("Do not claim navigation-failure.", NEGATIVE),
        (
            "The following rejected phrase must not be used: navigation-failure.",
            NEGATIVE,
        ),
        ("It is false that navigation-failure.", NEGATIVE),
        ("Hypothetically, navigation-failure; reject that claim.", NEGATIVE),
        ("The phrase navigation-failure is rejected.", NEGATIVE),
        (
            "This hypothetical is explicitly denied: navigation-failure.",
            NEGATIVE,
        ),
        (
            "The hypothetical claim navigation-failure is explicitly disclaimed.",
            NEGATIVE,
        ),
        ('The rejected quotation is: "navigation-failure."', NEGATIVE),
        ("Suppose navigation-failure applies.", NEGATIVE),
        ('"navigation-failure."', NEGATIVE),
        ("‘navigation-failure.’", NEGATIVE),
        ("“navigation-failure.”", NEGATIVE),
        ("«navigation-failure.»", NEGATIVE),
        ("Assume navigation-failure applies.", NEGATIVE),
        ("If navigation-failure applies, then continue.", NEGATIVE),
        ("Were navigation-failure applicable, it would matter.", NEGATIVE),
        ("Consider whether navigation-failure applies.", NEGATIVE),
    ),
)
def test_guard_state_matrix(text: str, expected: str) -> None:
    assert guard_state(text, "navigation-failure") == expected


def test_combined_guard_state_requires_every_positive_marker() -> None:
    markers = ("primary owner", "embedded-route", "proceed-routine")
    assert combined_guard_state("; ".join(markers), markers) == POSITIVE
    assert combined_guard_state("primary owner; embedded-route", markers) == ABSENT
    assert (
        combined_guard_state(
            "; ".join(markers) + ". Do not claim embedded-route.", markers
        )
        == CONFLICTED
    )


def test_negated_owner_and_axes_are_not_observed_tokens() -> None:
    result = local_guard_observations(
        {"structural_signals": (), "semantic_signals": ()},
        "Do not claim markdown-language-profile, selected, or proceed-routine.",
    )
    assert result["owners"] == set()
    assert result["axes"] == set()
    assert result["guard_states"]["owner:markdown-language-profile"] == NEGATIVE
    assert result["guard_states"]["axis:selected"] == NEGATIVE
    assert result["guard_states"]["axis:proceed-routine"] == NEGATIVE


@pytest.mark.parametrize(
    "rule",
    (
        "Rollback is always required.",
        "Rollback applies unconditionally.",
        "Rollback is mandatory.",
        "Every change requires rollback.",
        "All changes require rollback.",
        "Each change must include rollback.",
        "Each decision must have a rollback.",
        "Rollback is required for every change.",
    ),
)
def test_unconditional_rollback_positive_forms(rule: str) -> None:
    assert unconditional_rollback_state(rule) == POSITIVE


@pytest.mark.parametrize(
    "rule",
    (
        "Rollback is not required.",
        "No rollback is required.",
        "Not every change requires rollback.",
        "Rollback applies only where material.",
    ),
)
def test_unconditional_rollback_negative_forms(rule: str) -> None:
    assert unconditional_rollback_state(rule) == NEGATIVE


def test_unconditional_rollback_conflict_and_absence() -> None:
    assert (
        unconditional_rollback_state(
            "Rollback is not required. Every change requires rollback."
        )
        == CONFLICTED
    )
    assert unconditional_rollback_state("Record the observed behavior.") == ABSENT


@pytest.mark.parametrize("guard", tuple(TARGETED_GUARD_MARKERS))
def test_each_targeted_marker_has_closed_larger_token_boundaries(guard: str) -> None:
    _, requirement = TARGETED_GUARD_MARKERS[guard]
    markers = (requirement,) if isinstance(requirement, str) else requirement
    for marker in markers:
        assert guard_state(f"{marker}-extra", marker) == ABSENT


@pytest.mark.parametrize("guard", tuple(TARGETED_GUARD_MARKERS))
@pytest.mark.parametrize(
    "template",
    (
        'The rejected quotation is: "{marker}."',
        "Suppose {marker}.",
        '"{marker}."',
        "‘{marker}.’",
        "“{marker}.”",
        "«{marker}.»",
        "Assume {marker}.",
        "If {marker}, then continue.",
        "Were {marker} true, it would matter.",
        "Consider whether {marker}.",
    ),
)
def test_each_targeted_marker_rejects_quoted_and_hypothetical_positive_forms(
    guard: str, template: str
) -> None:
    _, requirement = TARGETED_GUARD_MARKERS[guard]
    markers = (requirement,) if isinstance(requirement, str) else requirement
    for marker in markers:
        assert guard_state(template.format(marker=marker), marker) == NEGATIVE
