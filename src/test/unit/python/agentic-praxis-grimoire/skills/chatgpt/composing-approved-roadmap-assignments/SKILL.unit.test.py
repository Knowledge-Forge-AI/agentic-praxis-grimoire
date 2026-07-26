#!/usr/bin/env python3
"""Focused roadmap-assignment skill contract test."""

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)


def test_roadmap_assignment_compression_never_assumes_broad_tests() -> None:
    path = (
        REPOSITORY_ROOT
        / "skills/chatgpt/composing-approved-roadmap-assignments/SKILL.md"
    )
    text = path.read_text()
    normalized = " ".join(text.split())
    assert "reference them once" in normalized
    assert (
        "omit default commit, status or exit, ADR, docs-only, scoped-test, "
        "and report procedure"
    ) in normalized
    assert "Do not assume combined, full, smoke, readiness, or release suites" in text
    assert (
        "Name an expanded gate only when the approved phase supplies it or a "
        "material risk or checkpoint justifies it, and preserve that "
        "justification in the assignment"
    ) in normalized
    assert "authority, acceptance, stop, and successor boundaries" in text
