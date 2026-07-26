#!/usr/bin/env python3
"""Focused APG34 Vagrantfile-profile contract tests."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
SKILL_NAME = "vagrantfile-profile"


class APG34VagrantfileProfileContractTests(unittest.TestCase):
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
            "Use when Vagrantfile-specific judgment is material to "
            "configuration versions and loading, machines, boxes, provider "
            "blocks, networks, synced folders, provisioners, triggers, "
            "Vagrant state, host-dependent behavior, or warning and crisis "
            "thresholds beyond repository policy."
        )
        self.assertEqual(
            self.frontmatter_description(text),
            expected_description,
        )

        route = self.capability_map()[SKILL_NAME]
        self.assertEqual(route["capability_class"], "Vagrantfile profile")
        self.assertEqual(
            route["trigger"],
            expected_description.removeprefix("Use when "),
        )

        for phrase in (
            "ordinary Ruby code with no material Vagrant behavior",
            "Terraform-only, Packer-only, or Docker-only work",
            "provider or hypervisor administration outside a Vagrantfile",
            "choosing Vagrant, a provider, box, plugin, host platform",
            "exact Vagrant or lifecycle command",
            "does not grant authority to perform a Vagrant or provider operation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_profile_has_required_structure_and_thresholds(self) -> None:
        text = self.skill_text()
        for heading in (
            "# Vagrantfile Profile",
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
            "| Physical lines per Vagrantfile owner | `<= 200` | `201–350` | `351–500` | `>= 501` |",
            "| Concrete machine definitions | `1–4` | `5–8` | `9–16` | `>= 17` |",
            "| Concrete machine-provider block applications | `0–2` | `3–4` | `5–7` | `>= 8` |",
            "| Concrete machine-network declarations | `0–3` | `4–8` | `9–16` | `>= 17` |",
            "| Concrete machine-synced-folder declarations | `0–2` | `3–5` | `6–10` | `>= 11` |",
            "| Concrete provisioner and trigger effect families | `0–3` | `4–7` | `8–12` | `>= 13` |",
            "| Host or platform conditional branches | `0–1` | `2–3` | `4–6` | `>= 7` |",
            "| Plugin and external dependency families | `0–1` | `2–3` | `4–6` | `>= 7` |",
            "| Shared mutable host or VM state domains | `0` | `1` | `2–3` | `>= 4` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)

    def test_profile_implements_versioned_vagrantfile_semantics_and_stops(
        self,
    ) -> None:
        text = self.skill_text()
        normalized = " ".join(text.split())
        for phrase in (
            "Vagrant 2.4.9",
            "`2.4.10.dev`",
            "Business Source License 1.1",
            "configuration number is not the Vagrant product version",
            "configuration versions 1 and 2",
            "`Vagrant.configure` stores",
            "does not evaluate a Vagrantfile",
            "Ruby `>= 3.0` and `< 3.5`",
            "box, home, project, multi-machine, and provider-specific",
            "`VAGRANT_CWD`",
            "`VAGRANT_HOME`",
            "`VAGRANT_DOTFILE_PATH`",
            "`.vagrant` is generated",
            "`Vagrant.has_plugin?`",
            "`Vagrant.require_plugin`",
            "deprecated and has no effect",
            "unavailable provider",
            "capability evidence",
            "latest available version satisfying `>= 0`",
            "checksum does not prove",
            "For most providers, forwarded ports bind all host interfaces by default",
            "auto-correction changes the host port",
            "static address remains project-owned",
            "Public-network meaning varies by provider",
            "exact host path",
            "absolute guest path",
            "default `/vagrant`",
            "Vagrant does not enforce idempotency",
            "Triggers run in definition order",
            "host or guest",
            "`ruby-language-profile`",
            "`bash-language-profile`",
            "Static review cannot prove",
            "protected data",
            "ports, addresses, machine names, or state identities can collide",
            "Untrusted input reaches Ruby, shell, host-command, or guest-command interpretation",
            "Three materially coupled Yellow signals",
            "Two materially coupled Orange signals",
            "One Red signal remains Red",
            "only when no named machine definitions exist",
            "Otherwise count each statically bounded named",
            "one root declaration applied to four machines counts four",
            "one cohesive responsibility family",
            "Removal is candidate-independent",
            "public scenario fixture",
            "recompute all surviving",
            "Derive counts from the resulting live inventories",
            "Public and active v0.3.0 remain 19/19/19",
            "No Vagrant lifecycle or provider operation is authorized",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)
        for stale in (
            "expect 24 current leaves",
            "general-router cardinality returns to 22",
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, normalized)

    def test_all_forty_frozen_scenarios_are_present(self) -> None:
        fixture_path = (
            REPOSITORY_ROOT
            / "src"
            / "test"
            / "fixtures"
            / "apg34-vagrantfile-scenario-families.json"
        )
        families = json.loads(fixture_path.read_text())["vagrantfile"]
        identifiers = [family["id"] for family in families]
        self.assertEqual(
            identifiers,
            [f"APG34-VAGRANTFILE-{index:02d}" for index in range(1, 41)],
        )
        for family in families:
            with self.subTest(identifier=family["id"]):
                self.assertEqual(
                    set(family),
                    {"id", "scenario", "expected"},
                )
                self.assertTrue(family["scenario"].strip())
                self.assertTrue(family["expected"].strip())

    def test_projection_targets_the_canonical_leaf(self) -> None:
        projection = REPOSITORY_ROOT / ".agents" / "skills" / SKILL_NAME
        self.assertTrue(projection.is_symlink())
        self.assertEqual(
            projection.readlink(),
            Path("../../skills/vagrantfile-profile"),
        )


if __name__ == "__main__":
    unittest.main()
