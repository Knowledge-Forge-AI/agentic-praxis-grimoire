#!/usr/bin/env python3
"""Focused APG38 go-cmp v0.7.0 profile contract."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
NAME = "go-cmp-test-profile"


class APG38GoCmpProfileContractTests(unittest.TestCase):
    def test_fixture_is_complete_ordered_and_public_safe(self) -> None:
        document = json.loads(
            (
                ROOT / "src/test/fixtures/apg37-go-cmp-scenario-families.json"
            ).read_text()
        )
        rows = document["go_cmp"]
        self.assertEqual(
            [row["id"] for row in rows],
            [f"APG37-CMP-{index:02d}" for index in range(1, 31)],
        )
        self.assertEqual(len(document["apg38_outcome_corrections"]), 6)
        for row in rows:
            self.assertEqual(set(row), {"id", "scenario", "expected"})
            self.assertNotIn("/" + "Users" + "/", json.dumps(row))

    def test_corrected_exact_version_contract_is_truthful(self) -> None:
        text = (ROOT / f"skills/{NAME}/SKILL.md").read_text()
        normalized = " ".join(text.split())
        for phrase in (
            "v0.7.0",
            "negative or NaN",
            "exact identity",
            "standard matching relation",
            "boolean comparison",
            "value-rendering",
            "filtering alone does not redact",
            "subject under test",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), normalized.lower())
        self.assertNotIn(
            "must be filtered, ignored, or transformed before comparison",
            normalized,
        )

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

    def test_apg89_go_composition_preserves_go_cmp_comparison(self) -> None:
        document = json.loads(
            (ROOT / "src/test/fixtures/apg89-profile-composition-scenarios.json").read_text()
        )
        rows = {row["id"]: row for row in document["go"]}
        self.assertEqual(rows["APG89-GO-04"]["owner"], NAME)


if __name__ == "__main__":
    unittest.main()
