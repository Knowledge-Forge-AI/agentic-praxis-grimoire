#!/usr/bin/env python3
"""Focused APG26 candidate-skill contract tests."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)


class APG26CandidateSkillContractTests(unittest.TestCase):
    @staticmethod
    def skill_text(name: str) -> str:
        return (REPOSITORY_ROOT / "skills" / name / "SKILL.md").read_text()

    @staticmethod
    def capability_map() -> dict[str, dict[str, str]]:
        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "agentic-praxis-grimoire-workflow"
            / "references"
            / "capability-map.json"
        )
        return {
            entry["name"]: entry
            for entry in json.loads(map_path.read_text())["capabilities"]
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

    def test_pytest_trigger_and_non_triggers_are_explicit(self) -> None:
        text = self.skill_text("pytest-test-profile")
        normalized = " ".join(text.split())
        capabilities = self.capability_map()
        self.assertEqual(
            self.frontmatter_description(text),
            "Use when pytest-specific judgment is material to discovery, "
            "collection, assertions, fixtures, parametrization, mocks, "
            "isolation, xdist, coverage, or warning and crisis thresholds "
            "beyond repository policy.",
        )
        self.assertEqual(
            capabilities["pytest-test-profile"]["trigger"],
            "pytest-specific judgment is material to discovery, collection, "
            "assertions, fixtures, parametrization, mocks, isolation, xdist, "
            "coverage, or warning and crisis thresholds beyond repository "
            "policy.",
        )
        self.assertIn(
            "ordinary Python implementation with no material pytest behavior",
            normalized,
        )
        self.assertIn(
            "`unittest` or another test harness when no pytest boundary is involved",
            normalized,
        )

    def test_conversion_trigger_and_non_triggers_are_explicit(self) -> None:
        text = self.skill_text("converting-bash-scripts-to-python")
        normalized = " ".join(text.split())
        capabilities = self.capability_map()
        self.assertEqual(
            self.frontmatter_description(text),
            "Use when an existing Bash executable or script family needs a "
            "bounded conversion to Python that preserves or deliberately "
            "migrates its observable contract.",
        )
        self.assertEqual(
            capabilities["converting-bash-scripts-to-python"]["trigger"],
            "An existing Bash executable or script family needs a bounded "
            "conversion to Python that preserves or deliberately migrates "
            "its observable contract.",
        )
        self.assertIn(
            "a trivial new Python script with no existing Bash contract;",
            normalized,
        )
        self.assertIn(
            "a Bash script that remains the clearest, safest, and "
            "best-supported implementation for the required task and "
            "platforms;",
            normalized,
        )

    def test_pytest_profile_has_frozen_ownership_thresholds_and_stops(
        self,
    ) -> None:
        text = self.skill_text("pytest-test-profile")
        for heading in (
            "# Pytest Test Profile",
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
            "| Test-file physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |",
            "| Tests per file | `<= 12` | `13–24` | `25–40` | `>= 41` |",
            "| Fixture definitions per file or local `conftest.py` owner | `<= 5` | `6–10` | `11–18` | `>= 19` |",
            "| Maximum fixture dependency depth | `<= 2` | `3` | `4–5` | `>= 6` |",
            "| Collected tests reached by one autouse fixture | `<= 10` | `11–30` | `31–100` | `>= 101` |",
            "| Generated cases for one parametrized test definition | `<= 20` | `21–100` | `101–500` | `>= 501` |",
            "| Mock or monkeypatch boundaries in one test | `<= 2` | `3–5` | `6–9` | `>= 10` |",
            "| Shared mutable resource domains per test owner | `0` | `1` | `2–3` | `>= 4` |",
            "| Worker-shared writable resource domains per test owner | `0` | `1, isolated` | `2–3, isolated` | `>= 4` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        for phrase in (
            "mocked behavior is represented as integrated",
            "xdist collision can corrupt or cross-contaminate results",
            "required assertion can false-pass",
            "protected data leaks",
            "unsupported plugin or runtime behavior is represented as verified",
            "crisis-level test-owner growth",
            "Three materially coupled Yellow signals",
            "Two materially coupled Orange signals",
            "One Red signal remains Red",
            "pytest 9.1.1",
            "pytest-xdist 3.8.0",
            "pytest-cov 7.1.0",
            "coverage.py 7.15.2",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_conversion_skill_preserves_full_migration_contract_and_stops(
        self,
    ) -> None:
        text = self.skill_text("converting-bash-scripts-to-python")
        for heading in (
            "# Converting Bash Scripts to Python",
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
        for phrase in (
            "authority and migration goal",
            "current interpreter and platform support",
            "CLI arguments and help",
            "stdin, stdout, and stderr",
            "file modes, ownership, and links",
            "atomicity and locking",
            "signals, interruption, and cleanup",
            "subprocess argument vectors",
            "characterization tests",
            "shell wrapper retention or removal",
            "compatibility rollout",
            "documentation and release projection",
            "current behavior is not sufficiently characterized",
            "exact CLI or report compatibility cannot be established",
            "Git semantics are approximated rather than verified",
            "option tokens fixed or drawn from a trusted allowlist",
            "end-of-options marker",
            "does not by itself prevent argument or option injection",
            "shell, argument, or option injection",
            "rollback or restoration is missing",
            "unrelated rewrite is required to claim completion",
            "GitPython 3.1.54",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_apg26_routes_are_explicit_and_keep_existing_owners(self) -> None:
        capabilities = self.capability_map()
        self.assertEqual(
            capabilities["pytest-test-profile"]["capability_class"],
            "pytest test profile",
        )
        self.assertEqual(
            capabilities["converting-bash-scripts-to-python"][
                "capability_class"
            ],
            "Bash-to-Python conversion",
        )

    def test_frozen_records_cover_all_sixty_scenario_families(self) -> None:
        families = json.loads((
            REPOSITORY_ROOT
            / "src"
            / "test"
            / "fixtures"
            / "apg26-scenario-families.json"
        ).read_text())
        for profile, prefix in (
            ("pytest", "APG26-PYTEST"),
            ("conversion", "APG26-CONVERT"),
        ):
            for index in range(1, 31):
                with self.subTest(profile=profile, index=index):
                    self.assertIn(
                        f"{prefix}-{index:02d}",
                        families[profile],
                    )


if __name__ == "__main__":
    unittest.main()
