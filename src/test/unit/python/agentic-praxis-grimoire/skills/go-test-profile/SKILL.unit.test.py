#!/usr/bin/env python3
"""Focused APG38 native Go test-profile contract."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
NAME = "go-test-profile"


class APG38GoTestProfileContractTests(unittest.TestCase):
    def test_fixture_is_complete_ordered_and_public_safe(self) -> None:
        path = ROOT / "src/test/fixtures/apg37-go-test-scenario-families.json"
        document = json.loads(path.read_text())
        rows = document["go_test"]
        self.assertEqual(
            [row["id"] for row in rows],
            [f"APG37-GO-TEST-{index:02d}" for index in range(1, 37)],
        )
        self.assertEqual(len(document["apg38_outcome_corrections"]), 7)
        for row in rows:
            self.assertEqual(set(row), {"id", "scenario", "expected"})
            self.assertNotIn("/" + "Users" + "/", json.dumps(row))

    def test_corrected_native_contract_is_truthful(self) -> None:
        text = (ROOT / f"skills/{NAME}/SKILL.md").read_text()
        normalized = " ".join(text.split())
        for phrase in (
            "required result",
            "resource-owning goroutine",
            "fuzz cache",
            "only when writable",
            "retained test artifact",
            "package-wide",
            "subject under test",
            "selected toolchain and project support floor",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), normalized.lower())
        for prohibited in (
            "lowers that file's language version",
            "A failing input is written into the fuzz test's seed corpus",
            "Cleanup that can leave a process, port, file, or external object behind is Red",
        ):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, normalized)

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
        self.assertIn(
            "src/test/fixtures/apg37-go-test-scenario-families.json",
            policy["critical_files"],
        )


if __name__ == "__main__":
    unittest.main()
