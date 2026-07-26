#!/usr/bin/env python3
"""Focused APG29 planning-skill contract test."""

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)


def test_planning_skill_scopes_tests_and_bounds_coverage_escalation() -> None:
    path = REPOSITORY_ROOT / "skills/planning-repository-work/SKILL.md"
    text = " ".join(path.read_text().split())
    for phrase in (
        "scoped unit evidence",
        "changed-boundary integration evidence",
        "Do not schedule combined, full, smoke, readiness, or release suites",
        "state the specific justification",
        "bounded coverage-remediation escalation",
        "unit replacement seams",
        "integration real boundaries",
        "readiness and release suites at their authorized checkpoints",
    ):
        assert phrase in text
