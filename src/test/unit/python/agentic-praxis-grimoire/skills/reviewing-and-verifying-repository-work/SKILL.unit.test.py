#!/usr/bin/env python3
"""Focused APG29 review-skill contract test."""

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)


def test_review_skill_checks_useful_tests_honest_coverage_and_reports() -> None:
    path = (
        REPOSITORY_ROOT
        / "skills/reviewing-and-verifying-repository-work/SKILL.md"
    )
    text = " ".join(path.read_text().split())
    for phrase in (
        "useful observable behavior",
        "exact coverage arithmetic",
        "complete maintained-source inventory",
        "exclusions have an explicit owner and rationale",
        "unit replacements do not erase the subject behavior",
        "integration claims exercise the real boundary they name",
        "A deliberately mocked unsafe external service remains a unit or "
        "bounded-adapter claim",
        "worker and subprocess completeness when material",
        "Broader test gates require a recorded justification",
        "deliberately unrun comprehensive suites",
        "Git-diff evidence for a dirty stopped result",
        "associated operational evidence",
    ):
        assert phrase in text
