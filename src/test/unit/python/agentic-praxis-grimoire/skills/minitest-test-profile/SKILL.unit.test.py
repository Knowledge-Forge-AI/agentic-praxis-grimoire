#!/usr/bin/env python3
"""Focused APG32 Minitest-profile contract tests."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
SKILL_NAME = "minitest-test-profile"


class APG32MinitestProfileContractTests(unittest.TestCase):
    @staticmethod
    def skill_text() -> str:
        return (
            REPOSITORY_ROOT / "skills" / SKILL_NAME / "SKILL.md"
        ).read_text()

    @staticmethod
    def capability_map() -> dict[str, dict[str, str]]:
        path = (
            REPOSITORY_ROOT
            / "skills"
            / "agentic-praxis-grimoire-workflow"
            / "references"
            / "capability-map.json"
        )
        return {
            entry["name"]: entry
            for entry in json.loads(path.read_text())["capabilities"]
        }

    @staticmethod
    def frontmatter_description(text: str) -> str:
        lines = text.splitlines()
        if not lines or lines[0] != "---":
            raise AssertionError("skill frontmatter is missing")
        for line in lines[1:]:
            if line == "---":
                break
            if line.startswith("description: "):
                return line.removeprefix("description: ")
        raise AssertionError("skill description is missing")

    def test_trigger_non_triggers_and_route_are_explicit(self) -> None:
        text = self.skill_text()
        normalized = " ".join(text.split())
        expected_description = (
            "Use when Minitest-specific judgment is material to test or spec "
            "organization, assertions, lifecycle, mocks, stubs, fixture "
            "alternatives, isolation, parallelism, filtering, runners, "
            "plugins, reporters, subprocess, filesystem, or database test "
            "boundaries, or warning and crisis thresholds beyond repository "
            "policy."
        )
        self.assertEqual(
            self.frontmatter_description(text),
            expected_description,
        )

        route = self.capability_map()[SKILL_NAME]
        self.assertEqual(route["capability_class"], "Minitest test profile")
        self.assertEqual(
            route["trigger"],
            expected_description.removeprefix("Use when "),
        )

        for phrase in (
            "ordinary Ruby implementation with no material Minitest behavior",
            "RSpec-specific work when no Minitest boundary is involved",
            "choosing Minitest, a plugin, a Ruby version, a Minitest version",
            "project-owned unit, integration, coverage, CI, or test-command policy",
            "framework selection",
            "harness-neutral subprocess, filesystem, or database integration",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_profile_has_required_structure_and_thresholds(self) -> None:
        text = self.skill_text()
        for heading in (
            "# Minitest Test Profile",
            "## Core principle",
            "## Do not use",
            "## Procedure",
            "## Project-owned parameters",
            "## Evidence and completion",
            "## Stop or escalate",
            "## Common mistakes",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, text)

        for row in (
            "| Physical lines per test owner | `<= 200` | `201–350` | `351–600` | `>= 601` |",
            "| Test methods or spec examples per owner | `<= 12` | `13–24` | `25–40` | `>= 41` |",
            "| Effective setup, teardown, or lifecycle-extension hooks per owner | `<= 2` | `3–4` | `5–6` | `>= 7` |",
            "| Helper modules mixed into one test owner | `0` | `1` | `2` | `>= 3` |",
            "| Mock or stub boundaries in one test | `<= 2` | `3–5` | `6–9` | `>= 10` |",
            "| Shared mutable resource domains per test owner | `0` | `1` | `2–3` | `>= 4` |",
            "| Parallel-worker shared writable domains per test owner | `0` | `1, isolated` | `2–3, isolated` | `>= 4`, or any unisolated collision |",
            "| Custom test-owner inheritance depth | `0–1` | `2` | `3` | `>= 4` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
            "| Generated or parameterized cases from one definition family | `<= 20` | `21–100` | `101–500` | `>= 501` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)

    def test_profile_implements_versioned_minitest_semantics_and_stops(
        self,
    ) -> None:
        text = self.skill_text()
        normalized = " ".join(text.split())
        for phrase in (
            "Minitest 6.0.6",
            "Ruby 4.0.6",
            "`minitest-mock` 5.27.0",
            "removed `minitest/mock.rb`",
            "unfiltered zero-test run can return success",
            "`test_`",
            "`describe`",
            "`it`",
            "`parallelize_me!`",
            "reported seed",
            "include or exclude",
            "`Minitest.autorun`",
            "opt-in plugin loading",
            "expectations are verified",
            "restoration",
            "mocks do not support multithreading",
            "mocked or stubbed boundary is represented as integrated",
            "fixture alternatives",
            "`implementing-with-test-discipline` retains real-versus-fake selection",
            "`ruby-language-profile` retains Ruby process lifecycle",
            "repository policy retains filesystem and database isolation",
            "protected data",
            "support is unverified",
            "destructive or consequential external state",
            "Three materially coupled Yellow signals",
            "Two materially coupled Orange signals",
            "One Red signal remains Red",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_all_thirty_six_frozen_scenarios_are_present(self) -> None:
        fixture_path = (
            REPOSITORY_ROOT
            / "src"
            / "test"
            / "fixtures"
            / "apg32-minitest-scenario-families.json"
        )
        families = json.loads(fixture_path.read_text())["minitest"]
        identifiers = [family["id"] for family in families]
        self.assertEqual(
            identifiers,
            [f"APG32-MINITEST-{index:02d}" for index in range(1, 37)],
        )
        for family in families:
            with self.subTest(identifier=family["id"]):
                self.assertEqual(
                    set(family),
                    {"id", "scenario", "expected"},
                )
                self.assertTrue(family["scenario"].strip())
                self.assertTrue(family["expected"].strip())

    def test_removal_is_candidate_independent_and_atomic(self) -> None:
        normalized = " ".join(self.skill_text().split())
        for phrase in (
            "Removal is candidate-independent",
            "public scenario fixture",
            "recompute all surviving",
            "Derive counts from the resulting live inventories",
            "raw APG32 commit revert is not valid rollback",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_projection_targets_the_canonical_leaf(self) -> None:
        projection = REPOSITORY_ROOT / ".agents" / "skills" / SKILL_NAME
        self.assertTrue(projection.is_symlink())
        self.assertEqual(
            projection.readlink(),
            Path("../../skills/minitest-test-profile"),
        )


if __name__ == "__main__":
    unittest.main()
