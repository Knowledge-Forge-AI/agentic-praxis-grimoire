#!/usr/bin/env python3
"""Focused APG29 and APG89 implementation-skill contract tests."""

import json

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


def test_apg89_composition_has_exact_narrow_owners_and_no_stack_owner() -> None:
    document = json.loads(
        (
            REPOSITORY_ROOT
            / "src/test/fixtures/apg89-profile-composition-scenarios.json"
        ).read_text()
    )
    constraints = document["constraints"]
    assert constraints == {
        "selection": "explicit-only",
        "mandatory_chain": False,
        "aggregate_owner": None,
        "v0_6_profiles": [
            "astro-profile",
            "gomock-test-profile",
            "jsx-language-profile",
            "mdx-profile",
            "react-component-profile",
            "vitest-test-profile",
        ],
    }
    rows = document["web"] + document["go"]
    assert [row["id"] for row in rows] == [
        *(f"APG89-WEB-{index:02d}" for index in range(1, 11)),
        *(f"APG89-GO-{index:02d}" for index in range(1, 6)),
    ]
    assert len({row["id"] for row in rows}) == len(rows)
    assert all(row["owner"] and "stack" not in row["owner"] for row in rows)
    strategy_ids = {"APG89-WEB-10", "APG89-GO-05"}
    strategy_owners = [row["owner"] for row in rows if row["id"] in strategy_ids]
    assert strategy_owners == [
        "implementing-with-test-discipline",
        "implementing-with-test-discipline",
    ]
    assert "/" + "Users" + "/" not in json.dumps(document)
