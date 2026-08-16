#!/usr/bin/env python3
"""Focused APG42 public release contract."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
EVALUATION = (
    ROOT
    / "docs/evaluations/apg42-v0-4-release-publication-and-active-deployment.md"
)
EXIT = (
    ROOT
    / "docs/status/2026/07/26/"
    "00062-apg42-v0-4-release-publication-and-active-deployment-exit.md"
)
TEST_PATH = Path(__file__).resolve().relative_to(ROOT).as_posix()


class APG42PublicReleaseContractTests(unittest.TestCase):
    def test_release_record_closes_the_exact_skill_scope(self) -> None:
        text = EVALUATION.read_text()
        for phrase in (
            "28 canonical skills",
            "28 catalog rows",
            "28 projections",
            "14 stable",
            "14 provisional",
            "26 general routes",
            "one ChatGPT-local direct route",
            "no mandatory chain",
            "ADR 0025 remains Rejected",
            "ADR 0026 remains Accepted",
            "ADR 0027 remains Rejected",
            "`matryer-is-test-profile` remains absent",
            "`go-testing-stack` remains absent",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_release_record_groups_limitations_without_overclaim(self) -> None:
        text = EVALUATION.read_text()
        for heading in (
            "## Current-host verified",
            "## Source/fixture-reviewed provisional domains",
            "## Not claimed",
        ):
            with self.subTest(heading=heading):
                self.assertEqual(text.count(heading), 1)
        for phrase in (
            "universal cross-platform compatibility",
            "target-repository compatibility",
            "automatic invocation or precedence",
            "Docker, Vagrant, Nix, or database runtime success",
            "No maturity promotion",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_exit_requires_postcommit_operational_acceptance(self) -> None:
        text = EXIT.read_text()
        for phrase in (
            "Complete — v0.4.0 published and active public-backed source "
            "deployed with provisional limitations",
            "associated operational report",
            "public push",
            "fresh public checkout",
            "active fast-forward",
            "aggregate preservation",
            "development parity",
            "No phase after APG42 is authorized",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_notice_retains_the_canonical_project_identity(self) -> None:
        notice = ROOT / "NOTICE"
        text = notice.read_text()
        payload = notice.read_bytes()
        git_blob = hashlib.sha1(
            f"blob {len(payload)}\0".encode() + payload
        ).hexdigest()
        self.assertEqual(git_blob, "d622b081f4cf109501d03bbfebd1224a3ecbcf33")
        self.assertIn("# Agentic Praxis Grimoire Notice", text)
        self.assertIn("Agentic Praxis Grimoire contributors", text)
        self.assertNotIn("Joint Agentic " + "Command Aegis", text)

    def test_release_policy_and_inventory_own_this_contract(self) -> None:
        policy = json.loads((ROOT / "release/public-surface.json").read_text())
        inventory = json.loads((ROOT / "testing/apg-test-inventory.json").read_text())
        evaluation = EVALUATION.relative_to(ROOT).as_posix()
        exit_record = EXIT.relative_to(ROOT).as_posix()

        self.assertEqual(len(policy["required_skills"]), 33)
        self.assertEqual(len(policy["required_projections"]), 33)
        self.assertIn(evaluation, policy["critical_files"])
        self.assertIn(exit_record, policy["critical_files"])
        self.assertIn(TEST_PATH, policy["required_test_entrypoints"])
        self.assertIn(
            {"owner": evaluation, "path": TEST_PATH, "suite": "unit"},
            inventory["tests"],
        )


if __name__ == "__main__":
    unittest.main()
