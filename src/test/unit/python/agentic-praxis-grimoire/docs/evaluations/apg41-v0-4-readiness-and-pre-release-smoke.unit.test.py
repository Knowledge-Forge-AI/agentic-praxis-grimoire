#!/usr/bin/env python3
"""Focused APG41 provisional-readiness contract."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
FIXTURE = ROOT / "src/test/fixtures/apg41-provisional-readiness-cases.json"
EVALUATION = (
    ROOT / "docs/evaluations/apg41-v0-4-readiness-and-pre-release-smoke.md"
)
PROVISIONAL = (
    "chatgpt-manager-workflow",
    "composing-approved-roadmap-assignments",
    "converting-bash-scripts-to-python",
    "dockerfile-profile",
    "go-cmp-test-profile",
    "go-language-profile",
    "go-test-profile",
    "minitest-test-profile",
    "nix-test-profile",
    "postgresql-database-profile",
    "pytest-test-profile",
    "ruby-language-profile",
    "sqlite-database-profile",
    "vagrantfile-profile",
)
REQUIRED_CASE_FIELDS = {
    "adverse_or_stop",
    "evidence_class",
    "known_limitations",
    "name",
    "non_trigger",
    "owner_boundary",
    "project_owned_input",
    "readiness_disposition",
    "removal_or_rollback",
    "trigger",
}


class APG41ProvisionalReadinessContractTests(unittest.TestCase):
    def test_fixture_covers_each_provisional_row_once(self) -> None:
        document = json.loads(FIXTURE.read_text())
        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["source_phase"], "APG41")
        rows = document["provisional_readiness"]
        self.assertEqual(tuple(row["name"] for row in rows), PROVISIONAL)
        for row in rows:
            with self.subTest(name=row["name"]):
                self.assertEqual(set(row), REQUIRED_CASE_FIELDS)
                self.assertTrue(all(str(value).strip() for value in row.values()))
                self.assertIn(
                    row["readiness_disposition"],
                    {
                        "ready-provisional",
                        "ready-provisional-with-limitation",
                        "defer-before-release",
                        "release-blocking-defect",
                    },
                )
                self.assertNotIn("/" + "Users" + "/", json.dumps(row))

    def test_public_evaluation_records_exact_release_scope(self) -> None:
        text = EVALUATION.read_text()
        for name in PROVISIONAL:
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", text)
        for phrase in (
            "28 canonical skills",
            "14 stable",
            "14 provisional",
            "ADR 0025",
            "ADR 0026",
            "ADR 0027",
            "`matryer-is-test-profile`",
            "`go-testing-stack`",
            "no mandatory chain",
            "ready-for-publication-with-provisional-limitations",
            "No publication or active deployment",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_release_and_test_inventories_own_the_contract(self) -> None:
        policy = json.loads((ROOT / "release/public-surface.json").read_text())
        inventory = json.loads((ROOT / "testing/apg-test-inventory.json").read_text())
        fixture = FIXTURE.relative_to(ROOT).as_posix()
        test = Path(__file__).resolve().relative_to(ROOT).as_posix()
        self.assertIn(fixture, policy["critical_files"])
        self.assertIn(test, policy["required_test_entrypoints"])
        self.assertIn(
            {
                "owner": EVALUATION.relative_to(ROOT).as_posix(),
                "path": test,
                "suite": "unit",
            },
            inventory["tests"],
        )


if __name__ == "__main__":
    unittest.main()
