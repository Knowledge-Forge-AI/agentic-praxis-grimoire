#!/usr/bin/env python3
"""APG38 Go component owner-graph and no-stack contract."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
GO_COMPONENTS = (
    "go-test-profile",
    "go-cmp-test-profile",
    "gomock-test-profile",
)


class APG38GoComponentOwnerGraphTests(unittest.TestCase):
    def test_components_are_flat_direct_routes(self) -> None:
        document = json.loads(
            (
                ROOT
                / "skills/agentic-praxis-grimoire-workflow/references/"
                "capability-map.json"
            ).read_text()
        )
        names = [row["name"] for row in document["capabilities"]]
        for name in GO_COMPONENTS:
            self.assertEqual(names.count(name), 1)
        self.assertNotIn("go-testing-stack", names)

    def test_non_retained_artifacts_and_projections_do_not_exist(self) -> None:
        for relative in (
            "skills/go-testing-stack",
            ".agents/skills/go-testing-stack",
            "docs/specs/go-testing-stack.md",
            "src/test/fixtures/apg37-go-testing-stack-scenario-families.json",
            "skills/matryer-is-test-profile",
            ".agents/skills/matryer-is-test-profile",
            "docs/specs/matryer-is-test-profile.md",
            "src/test/fixtures/apg37-matryer-is-scenario-families.json",
            "src/test/fixtures/apg39-matryer-is-scenario-families.json",
            "src/test/unit/python/agentic-praxis-grimoire/skills/"
            "matryer-is-test-profile/SKILL.unit.test.py",
        ):
            with self.subTest(relative=relative):
                self.assertFalse((ROOT / relative).exists())

    def test_owner_graph_is_direct_optional_and_removable(self) -> None:
        spec = (
            ROOT / "docs/specs/go-testing-component-profiles.md"
        ).read_text()
        normalized = " ".join(spec.split())
        for phrase in (
            "triggered directly",
            "does not require entering",
            "already selected",
            "candidate-independent",
            "repair surviving cross-references",
            "project-owned fallback",
            "No composition owner",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)
        self.assertNotIn(
            "leaves the others fully functional and requires no graph repair",
            normalized,
        )

    def test_surviving_references_have_project_owned_fallbacks(self) -> None:
        expectations = {
            "go-test-profile": "project-owned assertion policy",
            "go-cmp-test-profile": "project-owned assertion policy",
            "gomock-test-profile": "project-owned policy",
        }
        for name, phrase in expectations.items():
            with self.subTest(name=name):
                text = " ".join(
                    (ROOT / f"skills/{name}/SKILL.md").read_text().split()
                )
                self.assertIn(phrase, text)
                self.assertNotIn("must invoke", text)

    def test_adr_disposition_matches_two_owner_graph(self) -> None:
        accepted = (
            ROOT
            / "docs/adr/2026/07/"
            "0026-go-testing-component-profiles-without-a-stack-owner.md"
        ).read_text()
        rejected = (
            ROOT
            / "docs/adr/2026/07/"
            "0027-version-bounded-matryer-is-go-test-component.md"
        ).read_text()
        self.assertIn("- Status: Accepted", accepted)
        self.assertIn("- Status: Rejected", rejected)
        self.assertIn("ADR 0026 remains Accepted and controlling", rejected)


if __name__ == "__main__":
    unittest.main()
