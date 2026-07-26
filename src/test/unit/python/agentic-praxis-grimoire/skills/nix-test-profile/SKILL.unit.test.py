#!/usr/bin/env python3
"""Focused APG40 Nix test-profile contract."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
NAME = "nix-test-profile"
FIXTURE = "src/test/fixtures/apg39-nix-test-scenario-families.json"


class APG40NixTestProfileContractTests(unittest.TestCase):
    def test_fixture_is_complete_ordered_and_public_safe(self) -> None:
        document = json.loads((ROOT / FIXTURE).read_text())
        rows = document["nix_test"]
        self.assertEqual(
            [row["id"] for row in rows],
            [f"APG39-NIX-TEST-{index:02d}" for index in range(1, 41)],
        )
        self.assertEqual(document["source_phase"], "APG39")
        self.assertEqual(
            [row["id"] for row in document["apg40_outcome_corrections"]],
            [
                "APG39-NIX-TEST-05",
                "APG39-NIX-TEST-06",
                "APG39-NIX-TEST-07",
                "APG39-NIX-TEST-08",
                "APG39-NIX-TEST-09",
                "APG39-NIX-TEST-20",
                "APG39-NIX-TEST-31",
                "APG39-NIX-TEST-36",
            ],
        )
        for row in rows:
            self.assertEqual(set(row), {"id", "scenario", "expected"})
            rendered = json.dumps(row)
            self.assertNotIn("/" + "Users" + "/", rendered)
            self.assertNotIn("442d" + "27af", rendered)

    def test_claim_relative_source_bounded_contract_is_truthful(self) -> None:
        text = (ROOT / f"skills/{NAME}/SKILL.md").read_text()
        normalized = " ".join(text.split()).lower()
        for phrase in (
            "begin from the claim, not from a ladder of surfaces",
            "enabled on linux and on freebsd",
            "effective client and daemon configuration",
            "recognized does not imply uniformly checked",
            "can execute the host platform",
            "install-check phase can also silently run no tests",
            "sandbox-fallback",
            "physical size, node count, matrix size, and expense alone",
            "source review is not execution authority",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), normalized)
        self.assertNotIn("enabled on linux and disabled on every other", normalized)

    def test_atomic_integration_surfaces_exist(self) -> None:
        projection = ROOT / f".agents/skills/{NAME}"
        self.assertTrue(projection.is_symlink())
        self.assertEqual(projection.readlink(), Path(f"../../skills/{NAME}"))

        capability = json.loads(
            (
                ROOT
                / "skills/agentic-praxis-grimoire-workflow/references/"
                "capability-map.json"
            ).read_text()
        )
        self.assertIn(NAME, {row["name"] for row in capability["capabilities"]})

        policy = json.loads((ROOT / "release/public-surface.json").read_text())
        self.assertIn(f"skills/{NAME}/SKILL.md", policy["required_skills"])
        self.assertIn(f".agents/skills/{NAME}", policy["required_projections"])
        self.assertIn(FIXTURE, policy["critical_files"])

        inventory = json.loads(
            (ROOT / "testing/apg-test-inventory.json").read_text()
        )
        self.assertIn(
            f"skills/{NAME}/SKILL.md",
            {row["owner"] for row in inventory["tests"]},
        )


if __name__ == "__main__":
    unittest.main()
