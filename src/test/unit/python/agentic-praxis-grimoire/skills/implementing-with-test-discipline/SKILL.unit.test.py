#!/usr/bin/env python3
"""Focused APG29 implementation-skill contract test."""

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)


def test_implementation_skill_owns_bounded_coverage_remediation() -> None:
    path = REPOSITORY_ROOT / "skills/implementing-with-test-discipline/SKILL.md"
    text = " ".join(path.read_text().split())
    for phrase in (
        "Distinguish a behavior or test failure from a coverage-only failure",
        "exact per-file statement and branch counts",
        "current-task behavior",
        "adjacent behavior",
        "same maintained module",
        "package and subpackages",
        "parent package",
        "no useful observable contract remains",
        "Do not add tests only to execute lines",
        "Do not broaden to combined, full, smoke, readiness, or release suites",
    ):
        assert phrase in text
