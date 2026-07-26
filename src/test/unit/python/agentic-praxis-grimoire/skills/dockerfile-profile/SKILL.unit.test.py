#!/usr/bin/env python3
"""Focused APG33 Dockerfile-profile contract tests."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
SKILL_NAME = "dockerfile-profile"


class APG33DockerfileProfileContractTests(unittest.TestCase):
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
            "Use when Dockerfile-specific judgment is material to parser "
            "directives, build stages, instruction forms, variable scope, "
            "build context, copies, mounts, cache behavior, file ownership, "
            "runtime metadata, platform behavior, or warning and crisis "
            "thresholds beyond repository policy."
        )
        self.assertEqual(
            self.frontmatter_description(text),
            expected_description,
        )

        route = self.capability_map()[SKILL_NAME]
        self.assertEqual(route["capability_class"], "Dockerfile profile")
        self.assertEqual(
            route["trigger"],
            expected_description.removeprefix("Use when "),
        )

        for phrase in (
            "ordinary application code with no material Dockerfile behavior",
            "Compose-only, Kubernetes-only, or orchestrator-only work",
            "generic shell review with no Dockerfile-specific boundary",
            "choosing Docker, a base image, tag, digest, registry, frontend",
            "exact build, scan, push, run, sign, publish, or deployment command",
            "does not grant authority to perform a Docker operation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)

    def test_profile_has_required_structure_and_thresholds(self) -> None:
        text = self.skill_text()
        for heading in (
            "# Dockerfile Profile",
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
            "| Physical lines per Dockerfile | `<= 150` | `151–300` | `301–500` | `>= 501` |",
            "| Logical Dockerfile instructions | `<= 20` | `21–40` | `41–70` | `>= 71` |",
            "| Build stages | `1–3` | `4–6` | `7–10` | `>= 11` |",
            "| Commands in one shell-form `RUN` | `<= 5` | `6–10` | `11–20` | `>= 21` |",
            "| Distinct `ARG` and `ENV` names | `<= 6` | `7–12` | `13–20` | `>= 21` |",
            "| Distinct `COPY` and `ADD` source domains | `0–2` | `3–4` | `5–7` | `>= 8` |",
            "| Bind, cache, tmpfs, secret, or SSH mount families | `0–1` | `2–3` | `4–6` | `>= 7` |",
            "| Instructions executing as root after the last explicit user transition | `0–2` | `3–5` | `6–10` | `>= 11` |",
            "| Platform-conditional behavior families | `0–1` | `2–3` | `4–6` | `>= 7` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)

    def test_profile_implements_versioned_dockerfile_semantics_and_stops(
        self,
    ) -> None:
        text = self.skill_text()
        normalized = " ".join(text.split())
        for phrase in (
            "Dockerfile frontend 1.25.0",
            "BuildKit 0.31.2",
            "OCI Image Spec 1.1.1",
            "`docker/dockerfile:1` is mutable",
            "ordinary comment, empty line, or instruction",
            "global `ARG`",
            "redeclared inside a stage",
            "`FROM` starts a stage",
            "`COPY --from`",
            "shell form",
            "exec form",
            "`SHELL` changes later shell-form",
            "Linux and Windows",
            "build context",
            "Dockerfile-specific ignore file takes precedence",
            "final matching rule wins",
            "Local-context source paths in `COPY` and `ADD` cannot escape the context root",
            "Dockerfile and applicable ignore file remain builder inputs",
            "Remote `ADD`, named contexts, images, and `COPY --from` stages",
            "remote `ADD`",
            "`RUN --mount`",
            "secret mount does not prove",
            "secret value does not participate in the cache key",
            "ordinary `RUN` cache",
            "`ARG` and `ENV` are not protected-value transports",
            "`WORKDIR`",
            "`USER`",
            "`EXPOSE`",
            "`VOLUME`",
            "`STOPSIGNAL`",
            "`HEALTHCHECK`",
            "`ONBUILD`",
            "`ENTRYPOINT`",
            "`CMD`",
            "Build checks can report warnings while the build still succeeds",
            "Source review cannot prove that an image builds",
            "protected data",
            "support is unverified",
            "destructive or consequential external state",
            "`bash-language-profile`",
            "Three materially coupled Yellow signals",
            "Two materially coupled Orange signals",
            "One Red signal remains Red",
            "one cohesive responsibility family, not four",
            "Four independently released target images",
            "Measure each reachable stage separately and use the maximum",
            "final transition does not erase the build-stage count",
            "Unknown base-user or target reachability remains Orange",
            "Removal is candidate-independent",
            "public scenario fixture",
            "recompute all surviving",
            "Derive counts from the resulting live inventories",
            "raw APG33 commit revert is not valid rollback",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized)
        for stale in (
            "expect 23 current leaves",
            "general-router cardinality returns to 21",
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, normalized)

    def test_all_forty_frozen_scenarios_are_present(self) -> None:
        fixture_path = (
            REPOSITORY_ROOT
            / "src"
            / "test"
            / "fixtures"
            / "apg33-dockerfile-scenario-families.json"
        )
        families = json.loads(fixture_path.read_text())["dockerfile"]
        identifiers = [family["id"] for family in families]
        self.assertEqual(
            identifiers,
            [f"APG33-DOCKERFILE-{index:02d}" for index in range(1, 41)],
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
            Path("../../skills/dockerfile-profile"),
        )


if __name__ == "__main__":
    unittest.main()
