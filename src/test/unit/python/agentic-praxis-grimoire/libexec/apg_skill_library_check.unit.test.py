#!/usr/bin/env python3
"""Unit tests for the APG skill-library lexical subset."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

from src.test.apg_test_support import repository_root
from src.test.apg_skill_library_cases import CompleteCheckerBoundaryTests


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_skill_library_check as checker  # noqa: E402
from apg_skill_library_check import (  # noqa: E402
    CheckResult,
    Diagnostic,
    check_library,
    inline_links,
    main,
    parse_catalog,
    parse_frontmatter,
    render_json,
    render_text,
    valid_skill_name,
    visible_lines,
)


class EmbeddedCorpusConvergenceTests(unittest.TestCase):
    @mock.patch("apg_skill_library_check.subprocess.run")
    def test_go_embedded_corpus_verification_is_silent_exact_argv(self, run: mock.Mock) -> None:
        run.return_value = mock.Mock(returncode=0, stdout=b"", stderr=b"")
        self.assertIsNone(checker._embedded_corpus_failure(REPOSITORY_ROOT))
        arguments = run.call_args.args[0]
        self.assertEqual(arguments[:3], [sys.executable, "-m", "agentic_praxis_grimoire"])
        self.assertEqual(arguments[-3:], ["verify-corpus", "--repository", str(REPOSITORY_ROOT)])
        self.assertFalse(run.call_args.kwargs["shell"])

    @mock.patch("apg_skill_library_check.subprocess.run")
    def test_go_embedded_corpus_verification_fails_closed(self, run: mock.Mock) -> None:
        run.return_value = mock.Mock(returncode=1, stdout=b"", stderr=b"bounded")
        self.assertEqual(
            checker._embedded_corpus_failure(REPOSITORY_ROOT),
            "Go embedded-corpus verification disagrees with repository truth",
        )

    @mock.patch("apg_skill_library_check._embedded_corpus_failure")
    @mock.patch("apg_skill_library_check.check_library")
    def test_main_runs_embedded_corpus_gate_whenever_passed(
        self, check_mock: mock.Mock, corpus_mock: mock.Mock
    ) -> None:
        check_mock.return_value = CheckResult((), 40, 40, 40)
        corpus_mock.return_value = "disagrees"
        exit_code = main(["--root", str(REPOSITORY_ROOT), "--format", "json"])
        self.assertEqual(exit_code, 1)
        corpus_mock.assert_called_once_with(REPOSITORY_ROOT)

    @mock.patch("apg_skill_library_check._embedded_corpus_failure")
    @mock.patch("apg_skill_library_check.check_library")
    def test_main_skips_corpus_gate_when_check_already_failed(
        self, check_mock: mock.Mock, corpus_mock: mock.Mock
    ) -> None:
        diag = Diagnostic("APG001", "skills", "inv", "msg", "act")
        check_mock.return_value = CheckResult((diag,), 39, 39, 39)
        exit_code = main(["--root", str(REPOSITORY_ROOT), "--format", "json"])
        self.assertEqual(exit_code, 1)
        corpus_mock.assert_not_called()


class SkillNameTests(unittest.TestCase):
    def test_accepts_boundary_lengths_and_internal_hyphens(self) -> None:
        self.assertTrue(valid_skill_name("a"))
        self.assertTrue(valid_skill_name("a" * 64))
        self.assertTrue(valid_skill_name("alpha-2"))

    def test_rejects_invalid_grammar(self) -> None:
        for value in (
            "",
            "a" * 65,
            "Alpha",
            "alpha_beta",
            "-alpha",
            "alpha-",
            "alpha--beta",
            "alphá",
        ):
            with self.subTest(value=value):
                self.assertFalse(valid_skill_name(value))


class FrontmatterTests(unittest.TestCase):
    def test_parses_required_plain_scalars_and_ignores_optional_yaml(self) -> None:
        result = parse_frontmatter(
            b"---\nname: alpha-skill\ndescription: Use when alpha applies.\n"
            b"metadata:\n  owner: project\n---\n# Alpha\n"
        )
        self.assertTrue(result.starts_at_byte_one)
        self.assertTrue(result.terminated)
        self.assertEqual(result.values("name"), ("alpha-skill",))
        self.assertEqual(
            result.values("description"), ("Use when alpha applies.",)
        )
        self.assertEqual(result.invalid_required, ())

    def test_records_duplicate_required_keys(self) -> None:
        result = parse_frontmatter(
            b"---\nname: alpha-skill\nname: beta-skill\n"
            b"description: Use when needed.\n---\n"
        )
        self.assertEqual(result.values("name"), ("alpha-skill", "beta-skill"))

    def test_rejects_ambiguous_top_level_required_key_forms(self) -> None:
        templates = (
            '"{key}": shadowed',
            "'{key}': shadowed",
            "{key} : shadowed",
            "{key}\t: shadowed",
            "? {key}",
        )
        for key in ("name", "description"):
            for template in templates:
                line = template.format(key=key)
                with self.subTest(key=key, line=line):
                    result = parse_frontmatter(
                        (
                            "---\n"
                            "name: alpha-skill\n"
                            "description: Use when alpha applies.\n"
                            f"{line}\n"
                            "---\n"
                        ).encode()
                    )
                    self.assertEqual(len(result.values(key)), 1)
                    self.assertEqual(
                        getattr(result, "invalid_top_level_keys", ()), (4,)
                    )

    def test_accepts_plain_top_level_keys_and_ignores_nested_keys(self) -> None:
        result = parse_frontmatter(
            b"---\n"
            b"name: alpha-skill\n"
            b"description: Use when alpha applies.\n"
            b"metadata:\n"
            b"  name: nested-name\n"
            b"  description : nested description\n"
            b"items:\n"
            b"- one\n"
            b"- name: sequence-entry\n"
            b"flow-sequence:\n"
            b"[one, two]\n"
            b"flow-mapping:\n"
            b"{name: nested-name}\n"
            b"# optional comment\n"
            b"\n"
            b"---\n"
        )
        self.assertEqual(result.values("name"), ("alpha-skill",))
        self.assertEqual(
            result.values("description"), ("Use when alpha applies.",)
        )
        self.assertEqual(getattr(result, "invalid_top_level_keys", ()), ())

    def test_rejects_unsupported_optional_top_level_key_form(self) -> None:
        for line in (
            b"metadata : value",
            b"[metadata]: value",
            b"{metadata}: value",
        ):
            with self.subTest(line=line):
                result = parse_frontmatter(
                    b"---\n"
                    b"name: alpha-skill\n"
                    b"description: Use when alpha applies.\n"
                    + line
                    + b"\n---\n"
                )
                self.assertEqual(
                    getattr(result, "invalid_top_level_keys", ()), (4,)
                )

    def test_rejects_quoted_commented_and_multiline_required_values(self) -> None:
        for field in (
            b'name: "alpha-skill"',
            b"name: 'alpha-skill'",
            b"name: alpha-skill # comment",
            b"description: |",
            b"description: >",
        ):
            with self.subTest(field=field):
                result = parse_frontmatter(b"---\n" + field + b"\n---\n")
                self.assertTrue(result.invalid_required)

    def test_reports_unterminated_and_non_byte_one_frontmatter(self) -> None:
        unterminated = parse_frontmatter(b"---\nname: alpha-skill\n")
        shifted = parse_frontmatter(b"\xef\xbb\xbf---\n---\n")
        self.assertFalse(unterminated.terminated)
        self.assertFalse(shifted.starts_at_byte_one)


class TestV06ContextBudget(unittest.TestCase):
    @staticmethod
    def diagnostics_for(name: str, description_bytes: int) -> list[Diagnostic]:
        prefix = "Use when "
        description = prefix + ("x" * (description_bytes - len(prefix)))
        data = (
            f"---\nname: {name}\ndescription: {description}\n---\n"
            "# Profile\n"
            + "".join(
                f"\n## {heading}\nEvidence.\n" for heading in checker.REQUIRED_H2S
            )
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path(name),
            Path(name) / "SKILL.md",
            f"skills/{name}/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
        )
        return diagnostics

    def test_v06_description_band_is_utf8_byte_exact(self) -> None:
        for byte_count, should_pass in ((169, False), (170, True), (250, True), (330, True), (331, False)):
            with self.subTest(byte_count=byte_count):
                codes = {
                    item.code
                    for item in self.diagnostics_for(
                        "gomock-test-profile", byte_count
                    )
                }
                self.assertEqual("APG039" not in codes, should_pass)

        prefix = "Use when "
        multibyte = prefix + ("é" * 80) + "x"
        self.assertEqual(len(multibyte.encode("utf-8")), 170)
        data = (
            "---\nname: gomock-test-profile\n"
            f"description: {multibyte}\n---\n# Profile\n"
            + "".join(
                f"\n## {heading}\nEvidence.\n" for heading in checker.REQUIRED_H2S
            )
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("gomock-test-profile"),
            Path("gomock-test-profile/SKILL.md"),
            "skills/gomock-test-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
        )
        self.assertNotIn("APG039", {item.code for item in diagnostics})

    def test_band_is_scoped_to_the_frozen_v06_names(self) -> None:
        self.assertNotIn(
            "APG039",
            {
                item.code
                for item in self.diagnostics_for(
                    "javascript-language-profile", 417
                )
            },
        )

    def test_aggregate_gate_uses_the_canonical_context_report_owner(self) -> None:
        cases = (
            (
                "topology-agnostic-valid",
                {
                    "skill_count": 7,
                    "discoverable_skill_count": 7,
                    "total_description_bytes": 9527,
                    "malformed": [],
                },
                False,
            ),
            (
                "over-ceiling",
                {
                    "skill_count": 7,
                    "discoverable_skill_count": 7,
                    "total_description_bytes": 9528,
                    "malformed": [],
                },
                True,
            ),
            (
                "discoverability-mismatch",
                {
                    "skill_count": 7,
                    "discoverable_skill_count": 6,
                    "total_description_bytes": 9527,
                    "malformed": [],
                },
                True,
            ),
            (
                "malformed",
                {
                    "skill_count": 7,
                    "discoverable_skill_count": 7,
                    "total_description_bytes": 9527,
                    "malformed": [
                        {"path": "skills/bad/SKILL.md", "error": "bad"}
                    ],
                },
                True,
            ),
        )
        for label, report, should_fail in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "skills" / "gomock-test-profile").mkdir(parents=True)
                with mock.patch.object(
                    checker, "context_footprint_report", return_value=report
                ) as context_report:
                    result = check_library(root)
                context_report.assert_called_once_with(blobs={})
                self.assertEqual(
                    "APG040" in {item.code for item in result.diagnostics},
                    should_fail,
                )


class MarkdownLexicalTests(unittest.TestCase):
    def test_fenced_content_is_not_structural(self) -> None:
        text = (
            "# Visible\n"
            "```markdown\n## Hidden\n[hidden](missing.md)\n```\n"
            "## Visible\n"
            "~~~\n## Also hidden\n~~~\n"
        )
        visible = [line for _, line in visible_lines(text)]
        self.assertEqual(visible, ["# Visible", "## Visible"])

    def test_fence_closers_require_same_long_enough_bare_marker(self) -> None:
        cases = {
            "ordinary-backtick": (
                "```markdown\n## Hidden\n```\n## Visible\n",
                ["## Visible"],
            ),
            "ordinary-tilde": (
                "~~~text\n## Hidden\n~~~\n## Visible\n",
                ["## Visible"],
            ),
            "longer-closer": (
                "```\n## Hidden\n`````\n## Visible\n",
                ["## Visible"],
            ),
            "trailing-language-content": (
                "```markdown\n```python\n## Hidden\n```\n## Still hidden\n```\n",
                ["## Still hidden"],
            ),
            "shorter-marker": (
                "````\n```\n## Hidden\n````\n## Visible\n",
                ["## Visible"],
            ),
            "different-marker": (
                "```\n~~~\n## Hidden\n```\n## Visible\n",
                ["## Visible"],
            ),
            "unterminated": ("```\n## Hidden\n", []),
        }
        for label, (text, expected) in cases.items():
            with self.subTest(label=label):
                self.assertEqual(
                    [line for _, line in visible_lines(text)], expected
                )

    def test_recognizes_links_images_angle_destinations_and_fragments(self) -> None:
        text = (
            "[plain](references/a.md) "
            "![image](<assets/a file.png>) "
            "[fragment](references/a.md#part)"
        )
        self.assertEqual(
            [token.destination for token in inline_links(text)],
            ["references/a.md", "assets/a file.png", "references/a.md#part"],
        )

    def test_ignores_escaped_openers_reference_links_and_fenced_links(self) -> None:
        text = (
            r"\[escaped](missing.md) [reference][id]" + "\n"
            "```\n[fenced](missing.md)\n```\n"
        )
        self.assertEqual(inline_links(text), ())


class CatalogLexicalTests(unittest.TestCase):
    def test_parses_only_the_exact_catalog_contract(self) -> None:
        text = (
            "## Other\n\n| Skill | Trigger boundary | Maturity |\n"
            "| --- | --- | --- |\n| ignored | ignored | `stable` |\n\n"
            "## Current development catalog\n\n"
            "| Skill | Trigger boundary | Maturity |\n"
            "| --- | --- | --- |\n"
            "| [`alpha-skill`](alpha-skill/SKILL.md) | Alpha | `provisional` |\n"
        )
        result = parse_catalog(text)
        self.assertEqual(result.heading_count, 1)
        self.assertTrue(result.header_valid)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].name, "alpha-skill")
        self.assertEqual(result.rows[0].target, "alpha-skill/SKILL.md")

    def test_ignores_fenced_catalog_heading(self) -> None:
        text = "```\n## APG v0.1 catalog\n```\n"
        result = parse_catalog(text)
        self.assertEqual(result.heading_count, 0)

    def test_accepts_legacy_public_catalog_heading(self) -> None:
        text = (
            "## APG v0.1 catalog\n\n"
            "| Skill | Trigger boundary | Maturity |\n"
            "| --- | --- | --- |\n"
            "| [`alpha-skill`](alpha-skill/SKILL.md) | Alpha | `stable` |\n"
        )
        result = parse_catalog(text)
        self.assertEqual(result.heading_count, 1)
        self.assertTrue(result.header_valid)
        self.assertEqual([row.name for row in result.rows], ["alpha-skill"])


class WorkflowRouterCapabilityMapTests(unittest.TestCase):
    def test_map_covers_each_routable_catalog_skill_exactly_once(self) -> None:
        router_name = "agentic-praxis-grimoire-workflow"
        subrouter_name = "chatgpt-manager-workflow"
        catalog = parse_catalog(
            (REPOSITORY_ROOT / "skills" / "README.md").read_text()
        )
        catalog_names = {row.name for row in catalog.rows}
        routable_names = catalog_names - {router_name}

        general_map_path = (
            REPOSITORY_ROOT
            / "skills"
            / router_name
            / "references"
            / "capability-map.json"
        )
        subrouter_map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "chatgpt"
            / subrouter_name
            / "references"
            / "capability-map.json"
        )
        capability_maps = (
            json.loads(general_map_path.read_text()),
            json.loads(subrouter_map_path.read_text()),
        )

        routed_names: list[str] = []
        for capability_map, expected_router in zip(
            capability_maps,
            (router_name, subrouter_name),
            strict=True,
        ):
            self.assertEqual(
                set(capability_map),
                {"schema_version", "router_name", "capabilities"},
            )
            self.assertEqual(capability_map["schema_version"], 1)
            self.assertEqual(capability_map["router_name"], expected_router)

            capabilities = capability_map["capabilities"]
            self.assertEqual(
                capabilities,
                sorted(capabilities, key=lambda entry: entry["name"]),
            )
            for entry in capabilities:
                with self.subTest(router=expected_router, name=entry["name"]):
                    self.assertEqual(
                        set(entry), {"name", "capability_class", "trigger"}
                    )
                    self.assertNotEqual(entry["name"], expected_router)
                    self.assertTrue(entry["capability_class"].strip())
                    self.assertTrue(entry["trigger"].strip())
                    routed_names.append(entry["name"])

        self.assertEqual(set(routed_names), routable_names)
        self.assertEqual(len(routed_names), len(routable_names))

    def test_mixed_guidance_route_is_advertised(self) -> None:
        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "agentic-praxis-grimoire-workflow"
            / "references"
            / "capability-map.json"
        )
        capabilities = json.loads(map_path.read_text())["capabilities"]
        synthesis = next(
            entry
            for entry in capabilities
            if entry["name"] == "synthesizing-repository-guidance"
        )

        self.assertEqual(
            synthesis["capability_class"], "repository guidance synthesis"
        )
        self.assertIn("mixed-scope", synthesis["trigger"])
        self.assertIn("before rewrite", synthesis["trigger"])

    def test_python_language_profile_route_is_advertised(self) -> None:
        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "agentic-praxis-grimoire-workflow"
            / "references"
            / "capability-map.json"
        )
        capabilities = json.loads(map_path.read_text())["capabilities"]
        python_profile = next(
            entry
            for entry in capabilities
            if entry["name"] == "python-language-profile"
        )

        self.assertEqual(
            python_profile["capability_class"], "Python language profile"
        )
        self.assertIn("Python-specific judgment", python_profile["trigger"])

    def test_shell_language_and_test_profile_routes_are_advertised(self) -> None:
        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "agentic-praxis-grimoire-workflow"
            / "references"
            / "capability-map.json"
        )
        capabilities = {
            entry["name"]: entry
            for entry in json.loads(map_path.read_text())["capabilities"]
        }

        expected = {
            "bash-language-profile": (
                "Bash language profile",
                "Bash-specific judgment",
            ),
            "bats-test-profile": (
                "Bats test profile",
                "Bats-specific test judgment",
            ),
            "zsh-language-profile": (
                "Zsh language profile",
                "Zsh-specific judgment",
            ),
            "zunit-test-profile": (
                "ZUnit test profile",
                "ZUnit-specific judgment",
            ),
        }
        for name, (capability_class, trigger) in expected.items():
            with self.subTest(name=name):
                self.assertEqual(
                    capabilities[name]["capability_class"], capability_class
                )
                self.assertIn(trigger, capabilities[name]["trigger"])

    def test_go_and_ruby_language_profile_routes_are_advertised(self) -> None:
        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "agentic-praxis-grimoire-workflow"
            / "references"
            / "capability-map.json"
        )
        capabilities = {
            entry["name"]: entry
            for entry in json.loads(map_path.read_text())["capabilities"]
        }

        expected = {
            "go-language-profile": (
                "Go language profile",
                "Go-specific judgment",
            ),
            "ruby-language-profile": (
                "Ruby language profile",
                "Ruby-specific judgment",
            ),
        }
        for name, (capability_class, trigger) in expected.items():
            with self.subTest(name=name):
                self.assertEqual(
                    capabilities[name]["capability_class"], capability_class
                )
                self.assertIn(trigger, capabilities[name]["trigger"])

    def test_postgresql_and_sqlite_profile_routes_are_advertised(self) -> None:
        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "agentic-praxis-grimoire-workflow"
            / "references"
            / "capability-map.json"
        )
        capabilities = {
            entry["name"]: entry
            for entry in json.loads(map_path.read_text())["capabilities"]
        }

        expected = {
            "postgresql-database-profile": (
                "PostgreSQL database profile",
                "PostgreSQL-specific judgment",
            ),
            "sqlite-database-profile": (
                "SQLite database profile",
                "SQLite-specific judgment",
            ),
        }
        for name, (capability_class, trigger) in expected.items():
            with self.subTest(name=name):
                self.assertIn(name, capabilities)
                self.assertEqual(capabilities[name]["capability_class"], capability_class)
                self.assertIn(trigger, capabilities[name]["trigger"])

    def test_nix_language_profile_route_is_advertised(self) -> None:
        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "agentic-praxis-grimoire-workflow"
            / "references"
            / "capability-map.json"
        )
        capabilities = {
            entry["name"]: entry
            for entry in json.loads(map_path.read_text())["capabilities"]
        }
        nix_profile = capabilities["nix-language-profile"]
        self.assertEqual(
            nix_profile["capability_class"], "Nix language profile"
        )
        self.assertIn("Nix-specific judgment", nix_profile["trigger"])

    def test_approved_roadmap_manager_assignment_route_is_advertised(
        self,
    ) -> None:
        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / "chatgpt"
            / "chatgpt-manager-workflow"
            / "references"
            / "capability-map.json"
        )
        capabilities = {
            entry["name"]: entry
            for entry in json.loads(map_path.read_text())["capabilities"]
        }
        manager_assignment = capabilities[
            "composing-approved-roadmap-assignments"
        ]
        self.assertEqual(
            manager_assignment["capability_class"],
            "approved-roadmap manager-assignment composition",
        )
        self.assertIn("human-approved roadmap phase", manager_assignment["trigger"])
        self.assertIn("reviewable top-level", manager_assignment["trigger"])


class ApprovedRoadmapManagerAssignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_path = (
            REPOSITORY_ROOT
            / "skills"
            / "chatgpt"
            / "composing-approved-roadmap-assignments"
            / "SKILL.md"
        )
        cls.skill_text = cls.skill_path.read_text()

    def test_required_structure_and_trigger_are_present(self) -> None:
        frontmatter = parse_frontmatter(self.skill_path.read_bytes())
        self.assertEqual(
            frontmatter.values("name"),
            ("composing-approved-roadmap-assignments",),
        )
        description = frontmatter.values("description")[0]
        self.assertIn("human-approved roadmap phase", description)
        self.assertIn("reviewable top-level", description)

        for heading in (
            "# Composing Approved Roadmap Assignments",
            "## Core principle",
            "## Do not use",
            "## Procedure",
            "## Project-owned parameters",
            "## Evidence and completion",
            "## Stop or escalate",
            "## Common mistakes",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.skill_text)

    def test_authority_nontrigger_and_handoff_boundaries_are_explicit(
        self,
    ) -> None:
        for phrase in (
            "Translate approved authority; do not create authority.",
            "one approved phase by default",
            "explicitly approved bounded phase sequence",
            "planning-repository-work",
            "composing-bounded-worker-assignments",
            "reviewing-and-verifying-repository-work",
            "precommit",
            "postcommit",
            "no-successor",
            "Do not execute, dispatch, accept, or continue",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill_text)

    def test_fault_stops_and_project_owned_parameters_are_explicit(self) -> None:
        for phrase in (
            "semantic phase IDs",
            "source and write scopes",
            "private and public treatment",
            "unexpected repository state",
            "future commit hash",
            "publication authority",
            "application-smoke timing",
            "acceptance authority",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill_text)

    def test_structured_project_defaults_compress_repeated_procedure(self) -> None:
        for phrase in (
            "load the repository's structured-project defaults",
            "omit default commit, status or exit, ADR, docs-only, scoped-test, and report procedure",
            "deviations and material phase-specific requirements",
            "release, destructive, or otherwise high-risk",
            "authority, acceptance, stop, and successor boundaries",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.skill_text)


class PythonLanguageProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = (
            REPOSITORY_ROOT
            / "skills"
            / "python-language-profile"
            / "SKILL.md"
        ).read_text()

    def test_required_structure_and_warning_levels_are_present(self) -> None:
        for heading in (
            "# Python Language Profile",
            "## Core principle",
            "## Do not use",
            "## Procedure",
            "## Project-owned parameters",
            "## Evidence and completion",
            "## Stop or escalate",
            "## Common mistakes",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.skill_text)

        for level in (
            "Green — routine",
            "Yellow — caution",
            "Orange — warning",
            "Red — crisis / stop",
        ):
            with self.subTest(level=level):
                self.assertIn(level, self.skill_text)

    def test_structural_threshold_contract_is_complete(self) -> None:
        for metric in (
            "Module size",
            "Function or method size",
            "Cyclomatic complexity",
            "Branches",
            "Nesting depth",
            "Arguments",
            "Locals",
            "Responsibility count",
        ):
            with self.subTest(metric=metric):
                self.assertIn(f"| {metric} |", self.skill_text)

        for crisis in (
            "`>= 1,001`",
            "`>= 51`",
            "`>= 21`",
            "`>= 13`",
            "`>= 6`",
            "`>= 10`",
            "`>= 16`",
            "`>= 4`",
        ):
            with self.subTest(crisis=crisis):
                self.assertIn(crisis, self.skill_text)

    def test_process_domain_pairing_and_red_semantics_are_explicit(self) -> None:
        self.assertIn(
            "implementing-with-test-discipline", self.skill_text
        )
        self.assertIn(
            "reviewing-and-verifying-repository-work", self.skill_text
        )
        self.assertIn("untrusted input reaches `eval`", self.skill_text)
        self.assertIn("untrusted input reaches `exec`", self.skill_text)
        self.assertIn("unsafe untrusted deserialization", self.skill_text)


class ShellProfileContractTests(unittest.TestCase):
    REQUIRED_HEADINGS = (
        "## Core principle",
        "## Do not use",
        "## Procedure",
        "## Project-owned parameters",
        "## Evidence and completion",
        "## Stop or escalate",
        "## Common mistakes",
    )
    LEVELS = (
        "Green — routine",
        "Yellow — caution",
        "Orange — warning",
        "Red — crisis / stop",
    )

    def profile_text(self, name: str) -> str:
        return (
            REPOSITORY_ROOT / "skills" / name / "SKILL.md"
        ).read_text()

    def assert_common_contract(self, text: str) -> None:
        for heading in self.REQUIRED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, text)
        for level in self.LEVELS:
            with self.subTest(level=level):
                self.assertIn(level, text)
        self.assertIn("classify", text.lower())
        self.assertIn("smallest safe fix", text)
        self.assertIn("accepted bounded exception", text)

    def test_bash_profile_has_complete_thresholds_pairing_and_stops(self) -> None:
        text = self.profile_text("bash-language-profile")
        self.assert_common_contract(text)
        for row in (
            "| Script physical lines | `<= 150` | `151–300` | `301–500` | `>= 501` |",
            "| Function/top-level command count | `<= 15` | `16–25` | `26–40` | `>= 41` |",
            "| Decision paths | `<= 4` | `5–7` | `8–12` | `>= 13` |",
            "| Nesting depth | `<= 2` | `3` | `4` | `>= 5` |",
            "| Fixed positional parameters | `<= 4` | `5–6` | `7–9` | `>= 10` |",
            "| Mutable globals/cross-function state | `0–1` | `2–3` | `4–6` | `>= 7` |",
            "| Pipeline/process graph breadth | `0–2` | `3–4` | `5–7` | `>= 8` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        self.assertIn("Three materially coupled Yellow signals", text)
        self.assertIn("Two materially coupled Orange signals", text)
        self.assertIn("One Red signal remains Red", text)
        self.assertIn("implementing-with-test-discipline", text)
        self.assertIn("reviewing-and-verifying-repository-work", text)
        self.assertIn("untrusted or uncontrolled data reaches `eval`", text)
        self.assertIn("destructive command target", text)
        self.assertIn("Bats", text)

    def test_bats_profile_has_complete_thresholds_pairing_and_stops(self) -> None:
        text = self.profile_text("bats-test-profile")
        self.assert_common_contract(text)
        for row in (
            "| Test-file physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |",
            "| Test count | `<= 12` | `13–24` | `25–40` | `>= 41` |",
            "| Maximum test-body commands | `<= 15` | `16–25` | `26–50` | `>= 51` |",
            "| Maximum setup/teardown/bootstrap commands | `<= 12` | `13–20` | `21–35` | `>= 36` |",
            "| Maximum helper commands | `<= 20` | `21–35` | `36–50` | `>= 51` |",
            "| Shared fixture/global-state owners | `0–1` | `2–3` | `4–5` | `>= 6` |",
            "| Maximum concurrent background child groups | `0` | `1, fully owned` | `2–3, fully owned` | `>= 4, or any unowned/leaking child` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        self.assertIn("Three materially coupled Yellow signals", text)
        self.assertIn("Two materially coupled Orange signals", text)
        self.assertIn("One Red signal remains Red", text)
        self.assertIn("lower a line-count-only response by at most one level", text)
        self.assertIn("`run producer | consumer` outside", text)
        self.assertIn("assert the selected or expected", text)
        self.assertIn("status explicitly", text)
        self.assertIn("bash-language-profile", text)
        self.assertIn("file descriptor 3", text)
        self.assertIn("materially required status", text)
        self.assertIn("order-dependent", text)
        self.assertIn("runner-recognized tests", text)
        self.assertIn("supported comment function forms", text)
        self.assertIn("Do not evaluate a Bats file merely to count tests", text)

    def test_zsh_profile_has_complete_thresholds_pairing_and_stops(self) -> None:
        text = self.profile_text("zsh-language-profile")
        self.assert_common_contract(text)
        for row in (
            "| Script physical lines | `<= 200` | `201–300` | `301–500` | `>= 501` |",
            "| Commands in one function or top-level region | `<= 15` | `16–25` | `26–40` | `>= 41` |",
            "| Decision points | `<= 3` | `4–6` | `7–10` | `>= 11` |",
            "| Maximum control/subshell nesting | `<= 2` | `3` | `4–5` | `>= 6` |",
            "| Positional parameters | `<= 3` | `4–5` | `6–9` | `>= 10` |",
            "| Distinct option mutations in one scope | `<= 2` | `3–5` | `6–9` | `>= 10` |",
            "| Mutable global/cross-function parameters | `<= 2` | `3–5` | `6–9` | `>= 10` |",
            "| Autoload/module/hook/ZLE/completion breadth | `<= 2` | `3–5` | `6–10` | `>= 11` |",
            "| External process/pipeline families | `<= 2` | `3–5` | `6–9` | `>= 10` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        self.assertIn("Three materially coupled Yellow signals", text)
        self.assertIn("Two materially coupled Orange signals", text)
        self.assertIn("One Red signal remains Red", text)
        self.assertIn("implementing-with-test-discipline", text)
        self.assertIn("reviewing-and-verifying-repository-work", text)
        self.assertIn("untrusted dynamic source", text)
        self.assertIn("destructive glob", text)
        self.assertIn("ZUnit", text)

    def test_zunit_profile_has_version_matrix_thresholds_pairing_and_stops(self) -> None:
        text = self.profile_text("zunit-test-profile")
        self.assert_common_contract(text)
        for row in (
            "| Test-file physical lines | `<= 150` | `151–300` | `301–500` | `>= 501` |",
            "| Tests per file | `<= 8` | `9–15` | `16–24` | `>= 25` |",
            "| Commands in one test body | `<= 12` | `13–20` | `21–35` | `>= 36` |",
            "| Setup/teardown/bootstrap span | `<= 25` | `26–50` | `51–80` | `>= 81` |",
            "| Helper function span | `<= 20` | `21–35` | `36–50` | `>= 51` |",
            "| Mutable shared fixture/state domains | `<= 3` | `4–6` | `7–10` | `>= 11` |",
            "| Cleanup-owned children/jobs | `<= 1` | `2–3` | `4–5` | `>= 6` |",
            "| Independent responsibilities | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        self.assertIn("ZUnit v0.8.2 with Zsh 5.9.2", text)
        self.assertIn("Zsh 5.3.1", text)
        self.assertIn("unsupported", text)
        self.assertIn("No version range", text)
        self.assertIn("runner-recognized `@test`", text)
        self.assertIn("assertion-free", text)
        self.assertIn("order-dependent", text)
        self.assertIn("untrusted input reaches dynamic shell evaluation", text)
        self.assertIn("zsh-language-profile", text)
        self.assertIn("implementing-with-test-discipline", text)
        self.assertIn("reviewing-and-verifying-repository-work", text)

class GoAndRubyProfileContractTests(unittest.TestCase):
    REQUIRED_HEADINGS = ShellProfileContractTests.REQUIRED_HEADINGS
    LEVELS = ShellProfileContractTests.LEVELS

    def profile_text(self, name: str) -> str:
        return (REPOSITORY_ROOT / "skills" / name / "SKILL.md").read_text()

    def assert_common_contract(self, text: str) -> None:
        for heading in self.REQUIRED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, text)
        for level in self.LEVELS:
            with self.subTest(level=level):
                self.assertIn(level, text)
        self.assertIn("Three materially coupled Yellow signals", text)
        self.assertIn("Two materially coupled Orange signals", text)
        self.assertIn("One Red signal remains Red", text)
        self.assertIn("smallest safe fix", text)
        self.assertIn("accepted bounded exception", text)
        self.assertIn("implementing-with-test-discipline", text)
        self.assertIn("reviewing-and-verifying-repository-work", text)

    def test_go_profile_has_corrected_measurements_sinks_and_semantics(self) -> None:
        text = self.profile_text("go-language-profile")
        self.assert_common_contract(text)
        for row in (
            "| File physical lines | `<= 400` | `401–700` | `701–1,000` | `>= 1,001` |",
            "| Function or method statements | `<= 20` | `21–35` | `36–50` | `>= 51` |",
            "| Cyclomatic complexity | `1–5` | `6–10` | `11–20` | `>= 21` |",
            "| Branch or decision count | `<= 5` | `6–9` | `10–16` | `>= 17` |",
            "| Maximum control nesting | `<= 2` | `3` | `4–5` | `>= 6` |",
            "| Parameters | `<= 4` | `5–6` | `7–9` | `>= 10` |",
            "| Local bindings | `<= 10` | `11–15` | `16–20` | `>= 21` |",
            "| Exported API breadth per package | `<= 15` | `16–30` | `31–50` | `>= 51` |",
            "| Independent concurrency ownership breadth | `<= 2` | `3–4` | `5–7` | `>= 8` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        for phrase in (
            "grouped `const`",
            "grouped `var`",
            "type aliases",
            "promoted fields and methods",
            "unexported methods do not count",
            "every switch, type-switch, and select",
            "maximum count across supported build configurations",
            "nested function literals",
            "type-switch",
            "closure-capture subtotal",
            "panic or recover output",
            "metrics and labels",
            "trace attributes",
            "subprocess environment",
            "database or query text",
            "crash, core, profile, or debug output",
            "protected data",
            "Go website prose",
            "Go source distribution",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn("goroutine can outlive", text)
        self.assertIn("ambiguous channel", text)
        self.assertIn("known or credible data race", text)
        self.assertIn("`unsafe` or cgo", text)
        self.assertIn("untrusted input reaches shell interpretation", text)

    def test_ruby_profile_has_corrected_dynamic_state_lifecycle_and_compatibility(self) -> None:
        text = self.profile_text("ruby-language-profile")
        self.assert_common_contract(text)
        for row in (
            "| File physical lines | `<= 250` | `251–400` | `401–600` | `>= 601` |",
            "| Method physical span | `<= 15` | `16–25` | `26–40` | `>= 41` |",
            "| Cyclomatic complexity | `1–5` | `6–10` | `11–15` | `>= 16` |",
            "| Explicit decisions | `<= 4` | `5–8` | `9–12` | `>= 13` |",
            "| Control nesting depth | `<= 2` | `3` | `4–5` | `>= 6` |",
            "| Declared parameters | `<= 3` | `4–5` | `6–8` | `>= 9` |",
            "| Unique local bindings | `<= 8` | `9–12` | `13–16` | `>= 17` |",
            "| Direct public API breadth per owner | `<= 8` | `9–15` | `16–24` | `>= 25` |",
            "| Dynamic-dispatch/metaprogramming families per owner | `0` | `1` | `2` | `>= 3` |",
            "| Callback/hook/lifecycle families per owner | `0–1` | `2–3` | `4–5` | `>= 6` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        for phrase in (
            "ordinary public dispatch",
            "does not count as a dynamic family",
            "`public_send`",
            "`send`",
            "`method_missing`",
            "`respond_to_missing?`",
            "generated methods",
            "runtime class or module mutation",
            "dynamic constant lookup",
            "`autoload`",
            "runtime evaluation",
            "globals and class variables",
            "mutable constants",
            "singleton state",
            "registries and memoization",
            "process-global configuration",
            "test-visible shared state",
            "thread, fiber, or ractor",
            "shutdown and cancellation",
            "queue or port ownership",
            "fiber scheduler",
            "ractor shareability",
            "keyword arguments",
            "block and yield contracts",
            "serialization formats",
            "consumer inventory",
            "Ruby distribution",
            "RubyGems and Bundler source",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn("Untrusted evaluation", text)
        self.assertIn("unsafe or tamperable", text)
        self.assertIn("unresolved compatibility break", text)


class NixAndRelationalProfileContractTests(unittest.TestCase):
    REQUIRED_HEADINGS = ShellProfileContractTests.REQUIRED_HEADINGS
    LEVELS = ShellProfileContractTests.LEVELS

    def profile_text(self, name: str) -> str:
        return (REPOSITORY_ROOT / "skills" / name / "SKILL.md").read_text()

    def assert_common_contract(self, text: str) -> None:
        for heading in self.REQUIRED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(heading, text)
        for level in self.LEVELS:
            with self.subTest(level=level):
                self.assertIn(level, text)
        for phrase in (
            "Three materially coupled Yellow signals",
            "Two materially coupled Orange signals",
            "One Red signal remains Red",
            "smallest safe fix",
            "accepted bounded exception",
            "implementing-with-test-discipline",
            "reviewing-and-verifying-repository-work",
            "does not grant",
            "provisional",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_nix_profile_separates_structural_and_semantic_merge_risk(self) -> None:
        text = self.profile_text("nix-language-profile")
        self.assert_common_contract(text)
        for row in (
            "| File physical lines | `<= 200` | `201–350` | `351–500` | `>= 501` |",
            "| Function formals | `<= 6` | `7–12` | `13–20` | `>= 21` |",
            "| Direct `let` bindings | `<= 8` | `9–16` | `17–28` | `>= 29` |",
            "| Direct attribute-set breadth | `<= 12` | `13–24` | `25–40` | `>= 41` |",
            "| Attribute-definition depth | `<= 3` | `4` | `5–6` | `>= 7` |",
            "| Direct imports | `<= 5` | `6–10` | `11–18` | `>= 19` |",
            "| Module option leaf paths | `<= 8` | `9–16` | `17–28` | `>= 29` |",
            "| Merge/override mechanism families | `<= 1` | `2` | `3` | `>= 4` |",
            "| Direct derivation attributes | `<= 15` | `16–25` | `26–40` | `>= 41` |",
            "| Direct flake inputs | `<= 6` | `7–12` | `13–20` | `>= 21` |",
            "| Direct derivation input dependencies | `<= 10` | `11–20` | `21–35` | `>= 36` |",
            "| Direct outputs | `<= 2` | `3–4` | `5–7` | `>= 8` |",
            "| Embedded shell physical lines | `<= 20` | `21–40` | `41–80` | `>= 81` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        for phrase in (
            "A structurally Green merge-family count cannot downgrade",
            "Closed computed-name merge",
            "Open or insufficiently bounded",
            "Recursive, repeated-layer, fixed-point, overlay, or module-priority",
            "invariant-bypassing priority override",
            "mapAttrs",
            "listToAttrs",
            "mergeAttrsList",
            "mkForce",
            "No response level grants Nix evaluation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_postgresql_profile_has_frozen_thresholds_and_stops(self) -> None:
        text = self.profile_text("postgresql-database-profile")
        self.assert_common_contract(text)
        for row in (
            "| SQL or migration physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |",
            "| Top-level statements per migration direction | `<= 8` | `9–20` | `21–40` | `>= 41` |",
            "| Distinct relation owners touched | `<= 2` | `3–5` | `6–10` | `>= 11` |",
            "| Columns, indexes, or constraints changed | `<= 6` | `7–15` | `16–30` | `>= 31` |",
            "| Join edges in one query | `<= 3` | `4–6` | `7–10` | `>= 11` |",
            "| Maximum CTE/subquery depth | `<= 2` | `3` | `4–5` | `>= 6` |",
            "| PL/pgSQL routine-body physical span | `<= 40` | `41–80` | `81–140` | `>= 141` |",
            "| PL/pgSQL explicit decisions | `<= 5` | `6–10` | `11–16` | `>= 17` |",
            "| PL/pgSQL cyclomatic complexity | `1–6` | `7–12` | `13–20` | `>= 21` |",
            "| Owned trigger, policy, function, or procedure families | `<= 2` | `3–5` | `6–10` | `>= 11` |",
            "| Lock/transaction boundary families | `<= 1` | `2` | `3–4` | `>= 5` |",
            "| Data-movement/backfill families | `0` | `1` | `2` | `>= 3` |",
            "| Independent responsibility families | `1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        for phrase in (
            "untrusted input reaches generated SQL interpretation",
            "unresolved lock or table-rewrite risk",
            "RLS",
            "`SECURITY DEFINER`",
            "`search_path`",
            "tested restore",
            "forward correction",
            "live database access",
            "Count a physical line once when body payload shares it",
            "The 140-line boundary is Orange and the 141-line boundary is Red",
            "both decision measures as unresolved",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn(
            "A consequential change that relies on restoration as its recovery boundary requires",
            text,
        )
        self.assertNotIn(
            "Consequential change requires a successful version-compatible restore",
            text,
        )

    def test_sqlite_profile_has_frozen_thresholds_and_stops(self) -> None:
        text = self.profile_text("sqlite-database-profile")
        self.assert_common_contract(text)
        for row in (
            "| SQL or migration physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |",
            "| Top-level statements per migration direction | `<= 8` | `9–16` | `17–30` | `>= 31` |",
            "| Distinct tables, indexes, triggers, or views touched | `<= 3` | `4–7` | `8–12` | `>= 13` |",
            "| Join edges in one statement | `<= 2` | `3–5` | `6–8` | `>= 9` |",
            "| Maximum CTE/subquery depth | `<= 1` | `2` | `3–4` | `>= 5` |",
            "| Ordered schema-rebuild steps | `0` | `1–5` | `6–12` | `>= 13` |",
            "| State-mutating PRAGMA families | `0` | `1–2` | `3–4` | `>= 5` |",
            "| Transaction/attached-database families | `0–1` | `2` | `3` | `>= 4` |",
            "| Trigger definitions affecting one owner | `0–1` | `2–3` | `4–6` | `>= 7` |",
            "| Top-level body actions in one trigger | `0–3` | `4–6` | `7–10` | `>= 11` |",
            "| Independent data-copy/backfill families | `0` | `1` | `2–3` | `>= 4` |",
            "| Independent responsibility families | `0–1` | `2` | `3` | `>= 4` |",
        ):
            with self.subTest(row=row):
                self.assertIn(row, text)
        for phrase in (
            "untrusted input reaches SQL grammar",
            "WAL is proposed on a network filesystem",
            "foreign-key enforcement is assumed",
            "unsafe rename-old-first",
            "`synchronous=OFF`",
            "untested backup",
            "destructive file replacement",
            "live database access",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_domain_profiles_pair_without_replacing_process_owner(self) -> None:
        router = self.profile_text("agentic-praxis-grimoire-workflow")
        self.assertIn(
            "Add a separately applicable current domain profile only when",
            router,
        )
        for name, domain in (
            ("nix-language-profile", "Nix"),
            ("postgresql-database-profile", "PostgreSQL"),
            ("sqlite-database-profile", "SQLite"),
        ):
            with self.subTest(name=name):
                text = self.profile_text(name)
                normalized = " ".join(text.split())
                self.assertIn("implementing-with-test-discipline", text)
                self.assertIn("reviewing-and-verifying-repository-work", text)
                self.assertIn(
                    f"This profile supplies {domain} judgment without silently invoking either",
                    normalized,
                )
                self.assertIn("a comment, typo", text)


class DiscoveryPolicyParityTests(unittest.TestCase):
    def test_python_discovery_policy_constants_match_specification(self) -> None:
        self.assertEqual(checker.DISCOVERY_POLICY_VERSION_V010, "v0.10")
        self.assertEqual(
            checker.DISCOVERY_POLICY_VERSION_V010_BROWSER_UI, "v0.10-browser-ui"
        )
        self.assertEqual(
            checker.DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN, "v0.10-toolchain"
        )
        self.assertEqual(
            checker.DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME, "v0.10-browser-runtime"
        )
        self.assertEqual(checker.DISCOVERY_POLICY_VERSION, "v0.10-browser-runtime")
        self.assertEqual(checker.HISTORICAL_SKILL_COUNT, 39)
        self.assertEqual(checker.HISTORICAL_DESCRIPTION_BYTES, 9504)
        self.assertEqual(checker.HISTORICAL_DESCRIPTION_CHARACTERS, 9492)
        self.assertEqual(checker.HISTORICAL_GLOBAL_DESCRIPTION_LIMIT, 9527)
        self.assertEqual(checker.V010_MAX_RESERVATION_DESCRIPTION_BYTES, 330)
        self.assertEqual(checker.V010_CURRENT_SVG_ADMISSION_CEILING, 9857)
        self.assertEqual(checker.V010_BROWSER_UI_ADMISSION_CEILING, 10517)
        self.assertEqual(checker.V010_CURRENT_BROWSER_UI_ADMISSION_CEILING, 10517)
        self.assertEqual(checker.V010_TOOLCHAIN_ADMISSION_CEILING, 11177)
        self.assertEqual(checker.V010_CURRENT_TOOLCHAIN_ADMISSION_CEILING, 11177)
        self.assertEqual(checker.V010_BROWSER_RUNTIME_ADMISSION_CEILING, 11507)
        self.assertEqual(checker.V010_CURRENT_BROWSER_RUNTIME_ADMISSION_CEILING, 11507)
        self.assertEqual(checker.V010_OVERALL_FUTURE_CEILING, 11507)
        self.assertEqual(checker.V010_MAX_SVG_FILE_BYTES, 20480)
        self.assertEqual(checker.V010_CURRENT_ADMITTED_CANDIDATE, "svg-language-profile")
        self.assertEqual(checker.V010_ADMITTED_SKILL_COUNT, 40)
        self.assertEqual(checker.V010_BROWSER_UI_ADMITTED_SKILL_COUNT, 42)
        self.assertEqual(checker.V010_TOOLCHAIN_ADMITTED_SKILL_COUNT, 44)
        self.assertEqual(checker.V010_BROWSER_RUNTIME_ADMITTED_SKILL_COUNT, 45)
        self.assertEqual(
            checker.V010_ELIGIBLE_CANDIDATES,
            frozenset(
                {
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                    "browser-runtime-profile",
                    "npm-package-manager-profile",
                    "vite-build-profile",
                }
            ),
        )
        self.assertEqual(
            checker.V010_BROWSER_UI_ADMITTED_CANDIDATES,
            frozenset(
                {
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                }
            ),
        )
        self.assertEqual(
            checker.V010_TOOLCHAIN_ADMITTED_CANDIDATES,
            frozenset(
                {
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                    "vite-build-profile",
                    "npm-package-manager-profile",
                }
            ),
        )
        self.assertEqual(
            checker.V010_BROWSER_RUNTIME_ADMITTED_CANDIDATES,
            frozenset(
                {
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                    "vite-build-profile",
                    "npm-package-manager-profile",
                    "browser-runtime-profile",
                }
            ),
        )
        self.assertEqual(
            len(checker.FROZEN_SVG_SKILL_DESCRIPTION.encode("utf-8")), 241
        )
        self.assertTrue(
            checker.FROZEN_SVG_SKILL_DESCRIPTION.startswith("Use when ")
        )
        self.assertEqual(
            len(checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION.encode("utf-8")), 266
        )
        self.assertTrue(
            checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION.startswith("Use when ")
        )
        self.assertEqual(
            len(checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION.encode("utf-8")), 262
        )
        self.assertTrue(
            checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION.startswith("Use when ")
        )
        self.assertEqual(
            len(checker.FROZEN_VITE_SKILL_DESCRIPTION.encode("utf-8")), 223
        )
        self.assertTrue(
            checker.FROZEN_VITE_SKILL_DESCRIPTION.startswith("Use when ")
        )
        self.assertEqual(
            len(checker.FROZEN_NPM_SKILL_DESCRIPTION.encode("utf-8")), 323
        )
        self.assertTrue(
            checker.FROZEN_NPM_SKILL_DESCRIPTION.startswith("Use when ")
        )
        self.assertEqual(
            checker.FROZEN_ORIGINAL_39_DIGEST,
            "f9255d38eadff7b2bfc5ab13cd1722b8d98ac1ea974d8220475ff7067a1e8cc7",
        )
        self.assertEqual(len(checker.ORIGINAL_39_SKILL_DESCRIPTIONS), 39)
        self.assertEqual(
            checker.compute_original_39_digest(checker.ORIGINAL_39_SKILL_DESCRIPTIONS),
            checker.FROZEN_ORIGINAL_39_DIGEST,
        )

    def test_parity_with_go_discovery_policy_source(self) -> None:
        go_source_path = REPOSITORY_ROOT / "skills" / "discovery_policy.go"
        self.assertTrue(go_source_path.is_file())
        go_code = go_source_path.read_text(encoding="utf-8")

        def extract_str(name: str) -> str:
            match = re.search(rf'\b{name}\s*=\s*(?:"([^"]+)"|([A-Za-z0-9_]+))', go_code)
            self.assertIsNotNone(match, f"Missing constant string {name}")
            assert match is not None
            if match.group(1):
                return match.group(1)
            return extract_str(match.group(2))

        def extract_int(name: str) -> int:
            match = re.search(rf"\b{name}\s*=\s*(?:(?:int64\()?(\d+)\)?|([A-Za-z0-9_]+))", go_code)
            self.assertIsNotNone(match, f"Missing constant int {name}")
            assert match is not None
            if match.group(1):
                return int(match.group(1))
            return extract_int(match.group(2))

        self.assertEqual(
            extract_str("DiscoveryPolicyVersionV010"), checker.DISCOVERY_POLICY_VERSION_V010
        )
        self.assertEqual(
            extract_str("DiscoveryPolicyVersionV010BrowserUI"),
            checker.DISCOVERY_POLICY_VERSION_V010_BROWSER_UI,
        )
        self.assertEqual(
            extract_str("DiscoveryPolicyVersionV010Toolchain"),
            checker.DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN,
        )
        self.assertEqual(
            extract_str("DiscoveryPolicyVersionV010BrowserRuntime"),
            checker.DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME,
        )
        self.assertEqual(
            extract_str("DiscoveryPolicyVersion"), checker.DISCOVERY_POLICY_VERSION
        )
        self.assertEqual(
            extract_int("HistoricalSkillCount"), checker.HISTORICAL_SKILL_COUNT
        )
        self.assertEqual(
            extract_int("HistoricalDescriptionBytes"),
            checker.HISTORICAL_DESCRIPTION_BYTES,
        )
        self.assertEqual(
            extract_int("HistoricalDescriptionCharacters"),
            checker.HISTORICAL_DESCRIPTION_CHARACTERS,
        )
        self.assertEqual(
            extract_int("V010MaxReservationDescriptionBytes"),
            checker.V010_MAX_RESERVATION_DESCRIPTION_BYTES,
        )
        self.assertEqual(
            extract_int("V010CurrentSVGAdmissionCeiling"),
            checker.V010_CURRENT_SVG_ADMISSION_CEILING,
        )
        self.assertEqual(
            extract_int("V010BrowserUIAdmissionCeiling"),
            checker.V010_BROWSER_UI_ADMISSION_CEILING,
        )
        self.assertEqual(
            extract_int("V010CurrentBrowserUIAdmissionCeiling"),
            checker.V010_CURRENT_BROWSER_UI_ADMISSION_CEILING,
        )
        self.assertEqual(
            extract_int("V010ToolchainAdmissionCeiling"),
            checker.V010_TOOLCHAIN_ADMISSION_CEILING,
        )
        self.assertEqual(
            extract_int("V010CurrentToolchainAdmissionCeiling"),
            checker.V010_CURRENT_TOOLCHAIN_ADMISSION_CEILING,
        )
        self.assertEqual(
            extract_int("V010BrowserRuntimeAdmissionCeiling"),
            checker.V010_BROWSER_RUNTIME_ADMISSION_CEILING,
        )
        self.assertEqual(
            extract_int("V010CurrentBrowserRuntimeAdmissionCeiling"),
            checker.V010_CURRENT_BROWSER_RUNTIME_ADMISSION_CEILING,
        )
        self.assertEqual(
            extract_int("V010OverallFutureCeiling"),
            checker.V010_OVERALL_FUTURE_CEILING,
        )
        self.assertEqual(
            extract_int("V010MaxSVGFileBytes"), checker.V010_MAX_SVG_FILE_BYTES
        )
        self.assertEqual(
            extract_str("V010CurrentAdmittedCandidate"),
            checker.V010_CURRENT_ADMITTED_CANDIDATE,
        )
        self.assertEqual(
            extract_int("V010AdmittedSkillCount"),
            checker.V010_ADMITTED_SKILL_COUNT,
        )
        self.assertEqual(
            extract_int("V010BrowserUIAdmittedSkillCount"),
            checker.V010_BROWSER_UI_ADMITTED_SKILL_COUNT,
        )
        self.assertEqual(
            extract_int("V010ToolchainAdmittedSkillCount"),
            checker.V010_TOOLCHAIN_ADMITTED_SKILL_COUNT,
        )
        self.assertEqual(
            extract_int("V010BrowserRuntimeAdmittedSkillCount"),
            checker.V010_BROWSER_RUNTIME_ADMITTED_SKILL_COUNT,
        )
        self.assertEqual(
            extract_str("FrozenSVGSkillDescription"),
            checker.FROZEN_SVG_SKILL_DESCRIPTION,
        )
        self.assertEqual(
            extract_str("FrozenPlaywrightSkillDescription"),
            checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION,
        )
        self.assertEqual(
            extract_str("FrozenWebAccessibilitySkillDescription"),
            checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION,
        )
        self.assertEqual(
            extract_str("FrozenViteSkillDescription"),
            checker.FROZEN_VITE_SKILL_DESCRIPTION,
        )
        self.assertEqual(
            extract_str("FrozenNPMSkillDescription"),
            checker.FROZEN_NPM_SKILL_DESCRIPTION,
        )
        self.assertEqual(
            extract_str("FrozenOriginal39Digest"),
            checker.FROZEN_ORIGINAL_39_DIGEST,
        )

        cand_match = re.search(
            r"V010EligibleCandidates\s*=\s*\[\]string\{([^}]+)\}", go_code
        )
        self.assertIsNotNone(cand_match, "Missing V010EligibleCandidates in Go source")
        assert cand_match is not None
        extracted_candidates = re.findall(r'"([^"]+)"', cand_match.group(1))
        self.assertEqual(
            frozenset(extracted_candidates), checker.V010_ELIGIBLE_CANDIDATES
        )
        self.assertEqual(
            len(extracted_candidates), len(checker.V010_ELIGIBLE_CANDIDATES)
        )

        admitted_match = re.search(
            r"V010BrowserUIAdmittedCandidates\s*=\s*\[\]string\{([^}]+)\}", go_code
        )
        self.assertIsNotNone(
            admitted_match, "Missing V010BrowserUIAdmittedCandidates in Go source"
        )
        assert admitted_match is not None
        extracted_admitted = re.findall(r'"([^"]+)"', admitted_match.group(1))
        self.assertEqual(
            frozenset(extracted_admitted), checker.V010_BROWSER_UI_ADMITTED_CANDIDATES
        )
        self.assertEqual(
            len(extracted_admitted), len(checker.V010_BROWSER_UI_ADMITTED_CANDIDATES)
        )

        toolchain_admitted_match = re.search(
            r"V010ToolchainAdmittedCandidates\s*=\s*\[\]string\{([^}]+)\}", go_code
        )
        self.assertIsNotNone(
            toolchain_admitted_match, "Missing V010ToolchainAdmittedCandidates in Go source"
        )
        assert toolchain_admitted_match is not None
        extracted_toolchain_admitted = re.findall(r'"([^"]+)"', toolchain_admitted_match.group(1))
        self.assertEqual(
            frozenset(extracted_toolchain_admitted), checker.V010_TOOLCHAIN_ADMITTED_CANDIDATES
        )
        self.assertEqual(
            len(extracted_toolchain_admitted), len(checker.V010_TOOLCHAIN_ADMITTED_CANDIDATES)
        )

        browser_runtime_admitted_match = re.search(
            r"V010BrowserRuntimeAdmittedCandidates\s*=\s*\[\]string\{([^}]+)\}", go_code
        )
        self.assertIsNotNone(
            browser_runtime_admitted_match, "Missing V010BrowserRuntimeAdmittedCandidates in Go source"
        )
        assert browser_runtime_admitted_match is not None
        extracted_browser_runtime_admitted = re.findall(r'"([^"]+)"', browser_runtime_admitted_match.group(1))
        self.assertEqual(
            frozenset(extracted_browser_runtime_admitted), checker.V010_BROWSER_RUNTIME_ADMITTED_CANDIDATES
        )
        self.assertEqual(
            len(extracted_browser_runtime_admitted), len(checker.V010_BROWSER_RUNTIME_ADMITTED_CANDIDATES)
        )

        desc_match = re.search(
            r"Original39SkillDescriptions\s*=\s*map\[string\]string\{([^}]+)\n\}",
            go_code,
        )
        self.assertIsNotNone(
            desc_match, "Missing Original39SkillDescriptions in Go source"
        )
        assert desc_match is not None
        entries = re.findall(
            r'"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', desc_match.group(1)
        )
        extracted_descriptions = {k: json.loads(f'"{v}"') for k, v in entries}
        self.assertEqual(
            extracted_descriptions, checker.ORIGINAL_39_SKILL_DESCRIPTIONS
        )
        self.assertEqual(len(extracted_descriptions), checker.HISTORICAL_SKILL_COUNT)
        self.assertEqual(
            checker.compute_original_39_digest(extracted_descriptions),
            checker.FROZEN_ORIGINAL_39_DIGEST,
        )


class DiscoveryPolicyBoundaryTests(unittest.TestCase):
    @staticmethod
    def baseline_skills() -> list[dict[str, object]]:
        return [
            {
                "name": name,
                "description": desc,
                "bytes": len(desc.encode("utf-8")),
                "characters": len(desc),
                "blob_bytes": 1000,
            }
            for name, desc in sorted(checker.ORIGINAL_39_SKILL_DESCRIPTIONS.items())
        ]

    def test_exact_boundaries(self) -> None:
        baseline = self.baseline_skills()
        self.assertEqual(checker.validate_discovery_policy("v0.10", baseline), [])

        desc330 = "Use when SVG syntax is needed " + ("x" * (330 - len("Use when SVG syntax is needed ")))
        self.assertEqual(len(desc330.encode("utf-8")), 330)
        skills40 = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": desc330,
                "bytes": 330,
                "characters": len(desc330),
                "blob_bytes": 20480,
            }
        ]
        self.assertEqual(checker.validate_discovery_policy("v0.10", skills40), [])

    def test_one_over_boundaries(self) -> None:
        desc331 = "Use when SVG syntax is needed " + ("x" * (331 - len("Use when SVG syntax is needed ")))
        skills_over_desc = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": desc331,
                "bytes": 331,
                "characters": len(desc331),
                "blob_bytes": 1000,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", skills_over_desc)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        desc300 = "Use when SVG syntax is needed " + ("x" * (300 - len("Use when SVG syntax is needed ")))
        skills_over_file = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": desc300,
                "bytes": 300,
                "characters": len(desc300),
                "blob_bytes": 20481,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", skills_over_file)
        self.assertTrue(any("exceeds SVG file limit of 20480" in f for f in failures))

        skills41 = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": desc300,
                "bytes": 300,
                "characters": len(desc300),
                "blob_bytes": 1000,
            },
            {
                "name": "playwright-test-profile",
                "description": "Use when Playwright applies.",
                "bytes": len("Use when Playwright applies.".encode("utf-8")),
                "characters": len("Use when Playwright applies."),
                "blob_bytes": 1000,
            },
        ]
        failures = checker.validate_discovery_policy("v0.10", skills41)
        self.assertTrue(any("expected 39 or 40 leaves" in f for f in failures))

        skills38 = self.baseline_skills()[:38]
        failures = checker.validate_discovery_policy("v0.10", skills38)
        self.assertTrue(any("expected 39 or 40 leaves" in f for f in failures))

    def test_multibyte_enforcement(self) -> None:
        multibyte330 = "Use when " + ("é" * 160) + "x"
        self.assertEqual(len(multibyte330.encode("utf-8")), 330)
        self.assertEqual(len(multibyte330), 170)
        skills_multibyte = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": multibyte330,
                "bytes": 330,
                "characters": 170,
                "blob_bytes": 1000,
            }
        ]
        self.assertEqual(checker.validate_discovery_policy("v0.10", skills_multibyte), [])

        multibyte331 = "Use when " + ("é" * 160) + "xx"
        self.assertEqual(len(multibyte331.encode("utf-8")), 331)
        skills_multibyte_over = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": multibyte331,
                "bytes": 331,
                "characters": 171,
                "blob_bytes": 1000,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", skills_multibyte_over)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        tampered = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": multibyte330,
                "bytes": 170,
                "characters": 170,
                "blob_bytes": 1000,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", tampered)
        self.assertTrue(any("description bytes mismatch" in f for f in failures))

    def test_malformed_metadata(self) -> None:
        bad_name = self.baseline_skills()
        bad_name[0]["name"] = ""
        failures = checker.validate_discovery_policy("v0.10", bad_name)
        self.assertTrue(any("empty name or description" in f for f in failures))

        bad_desc = self.baseline_skills()
        bad_desc[0]["description"] = ""
        failures = checker.validate_discovery_policy("v0.10", bad_desc)
        self.assertTrue(any("empty name or description" in f for f in failures))

        bad_prefix = self.baseline_skills()
        bad_prefix[0]["description"] = "Invalid prefix for description."
        bad_prefix[0]["bytes"] = len(bad_prefix[0]["description"].encode("utf-8"))
        failures = checker.validate_discovery_policy("v0.10", bad_prefix)
        self.assertTrue(any("must begin with 'Use when '" in f for f in failures))

    def test_missing_skills(self) -> None:
        imposter39 = self.baseline_skills()
        imposter39[0] = {
            "name": "svg-language-profile",
            "description": "Use when SVG applies.",
            "bytes": len("Use when SVG applies.".encode("utf-8")),
            "characters": len("Use when SVG applies."),
            "blob_bytes": 1000,
        }
        failures = checker.validate_discovery_policy("v0.10", imposter39)
        self.assertTrue(any("missing original 39 skill" in f for f in failures))

        missing_orig40 = self.baseline_skills()[:38] + [
            {
                "name": "svg-language-profile",
                "description": "Use when SVG applies.",
                "bytes": len("Use when SVG applies.".encode("utf-8")),
                "characters": len("Use when SVG applies."),
                "blob_bytes": 1000,
            },
            {
                "name": "playwright-test-profile",
                "description": "Use when Playwright applies.",
                "bytes": len("Use when Playwright applies.".encode("utf-8")),
                "characters": len("Use when Playwright applies."),
                "blob_bytes": 1000,
            },
        ]
        failures = checker.validate_discovery_policy("v0.10", missing_orig40)
        self.assertTrue(any("expected exactly 1 admitted candidate skill" in f for f in failures))

    def test_duplicate_skills(self) -> None:
        dupes = self.baseline_skills()
        dupes[1] = dict(dupes[0])
        failures = checker.validate_discovery_policy("v0.10", dupes)
        self.assertTrue(any("duplicate skill ID" in f for f in failures))

    def test_reservation_theft(self) -> None:
        theft = self.baseline_skills()
        for item in theft:
            if item["name"] == "agentic-praxis-grimoire-workflow":
                item["description"] = "Use when APG routing applies."
                item["bytes"] = len(item["description"].encode("utf-8"))
                item["characters"] = len(item["description"])
                break
        failures = checker.validate_discovery_policy("v0.10", theft)
        self.assertTrue(any("reservation theft" in f for f in failures))

        playwright40 = self.baseline_skills() + [
            {
                "name": "playwright-test-profile",
                "description": "Use when Playwright applies.",
                "bytes": len("Use when Playwright applies.".encode("utf-8")),
                "characters": len("Use when Playwright applies."),
                "blob_bytes": 1000,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", playwright40)
        self.assertTrue(any("not authorized for admission" in f for f in failures))

        unregistered40 = self.baseline_skills() + [
            {
                "name": "custom-domain-profile",
                "description": "Use when custom domain applies.",
                "bytes": len("Use when custom domain applies.".encode("utf-8")),
                "characters": len("Use when custom domain applies."),
                "blob_bytes": 1000,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", unregistered40)
        self.assertTrue(any("not authorized for admission" in f for f in failures))

        desc335 = "Use when SVG syntax applies " + ("x" * (335 - len("Use when SVG syntax applies ")))
        theft_over = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": desc335,
                "bytes": 335,
                "characters": len(desc335),
                "blob_bytes": 1000,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", theft_over)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

    def test_unknown_policy(self) -> None:
        baseline = self.baseline_skills()
        for unknown in ("v0.9", "v0.11", "v1.0", "unknown", ""):
            with self.subTest(unknown=unknown):
                failures = checker.validate_discovery_policy(unknown, baseline)
                self.assertTrue(any("unknown discovery policy" in f for f in failures))

    def test_measurement_boundaries_and_malformed(self) -> None:
        # Candidate body bytes must be positive and non-missing
        missing_blob = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": "Use when SVG syntax applies.",
                "bytes": len("Use when SVG syntax applies.".encode("utf-8")),
                "characters": len("Use when SVG syntax applies."),
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", missing_blob)
        self.assertTrue(any("missing required body bytes measurement" in f for f in failures))

        zero_blob = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": "Use when SVG syntax applies.",
                "bytes": len("Use when SVG syntax applies.".encode("utf-8")),
                "characters": len("Use when SVG syntax applies."),
                "blob_bytes": 0,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", zero_blob)
        self.assertTrue(any("must be positive" in f for f in failures))

        neg_blob = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": "Use when SVG syntax applies.",
                "bytes": len("Use when SVG syntax applies.".encode("utf-8")),
                "characters": len("Use when SVG syntax applies."),
                "blob_bytes": -10,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", neg_blob)
        self.assertTrue(any("must be positive" in f for f in failures))

        non_int_blob = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": "Use when SVG syntax applies.",
                "bytes": len("Use when SVG syntax applies.".encode("utf-8")),
                "characters": len("Use when SVG syntax applies."),
                "blob_bytes": "not-an-int",
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", non_int_blob)
        self.assertTrue(any("malformed body bytes" in f for f in failures))

        # Candidate non-positive description bytes
        zero_desc_bytes = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": "Use when SVG syntax applies.",
                "bytes": 0,
                "characters": len("Use when SVG syntax applies."),
                "blob_bytes": 1000,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", zero_desc_bytes)
        self.assertTrue(any("must be positive" in f for f in failures))

        # Candidate mismatched description bytes
        mismatch_desc_bytes = self.baseline_skills() + [
            {
                "name": "svg-language-profile",
                "description": "Use when SVG syntax applies.",
                "bytes": 50,
                "characters": len("Use when SVG syntax applies."),
                "blob_bytes": 1000,
            }
        ]
        failures = checker.validate_discovery_policy("v0.10", mismatch_desc_bytes)
        self.assertTrue(any("description bytes mismatch" in f for f in failures))

        # Baseline body bytes negative
        baseline_neg_body = self.baseline_skills()
        baseline_neg_body[0]["blob_bytes"] = -5
        failures = checker.validate_discovery_policy("v0.10", baseline_neg_body)
        self.assertTrue(any("must be positive" in f for f in failures))

        # Baseline body bytes malformed
        baseline_bad_body = self.baseline_skills()
        baseline_bad_body[0]["blob_bytes"] = "invalid"
        failures = checker.validate_discovery_policy("v0.10", baseline_bad_body)
        self.assertTrue(any("malformed body bytes" in f for f in failures))

        # Character count mismatch
        char_mismatch = self.baseline_skills()
        char_mismatch[0]["characters"] = 99999
        failures = checker.validate_discovery_policy("v0.10", char_mismatch)
        self.assertTrue(any("characters mismatch" in f for f in failures))


class DiscoveryPolicyBrowserUIBoundaryTests(unittest.TestCase):
    @staticmethod
    def baseline_skills_42() -> list[dict[str, object]]:
        orig = [
            {
                "name": name,
                "description": desc,
                "bytes": len(desc.encode("utf-8")),
                "characters": len(desc),
                "blob_bytes": 1000,
            }
            for name, desc in sorted(checker.ORIGINAL_39_SKILL_DESCRIPTIONS.items())
        ]
        candidates = [
            {
                "name": "svg-language-profile",
                "description": checker.FROZEN_SVG_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_SVG_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_SVG_SKILL_DESCRIPTION),
                "blob_bytes": 20480,
            },
            {
                "name": "playwright-test-profile",
                "description": "Use when Playwright end-to-end browser tests, fixtures, locators, tracing, network mocking, or page interactions are evaluated.",
                "bytes": len("Use when Playwright end-to-end browser tests, fixtures, locators, tracing, network mocking, or page interactions are evaluated.".encode("utf-8")),
                "characters": len("Use when Playwright end-to-end browser tests, fixtures, locators, tracing, network mocking, or page interactions are evaluated."),
                "blob_bytes": 35000,
            },
            {
                "name": "web-accessibility-profile",
                "description": "Use when accessibility auditing, ARIA attributes, semantic landmarks, focus management, screen-reader semantics, or WCAG compliance are evaluated.",
                "bytes": len("Use when accessibility auditing, ARIA attributes, semantic landmarks, focus management, screen-reader semantics, or WCAG compliance are evaluated.".encode("utf-8")),
                "characters": len("Use when accessibility auditing, ARIA attributes, semantic landmarks, focus management, screen-reader semantics, or WCAG compliance are evaluated."),
                "blob_bytes": 40000,
            },
        ]
        return orig + candidates

    def test_exact_boundaries(self) -> None:
        baseline42 = self.baseline_skills_42()
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-ui", baseline42), [])

        # SVG at exact 20480 bytes passes
        exact_svg = self.baseline_skills_42()
        for s in exact_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20480
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-ui", exact_svg), [])

        # Playwright at exact 330 description bytes passes
        exact_pw = self.baseline_skills_42()
        desc330_pw = "Use when Playwright applies " + ("x" * (330 - len("Use when Playwright applies ")))
        for s in exact_pw:
            if s["name"] == "playwright-test-profile":
                s["description"] = desc330_pw
                s["bytes"] = 330
                s["characters"] = len(desc330_pw)
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-ui", exact_pw), [])

        # Web-a11y at exact 330 description bytes passes
        exact_a11y = self.baseline_skills_42()
        desc330_a11y = "Use when web accessibility applies " + ("x" * (330 - len("Use when web accessibility applies ")))
        for s in exact_a11y:
            if s["name"] == "web-accessibility-profile":
                s["description"] = desc330_a11y
                s["bytes"] = 330
                s["characters"] = len(desc330_a11y)
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-ui", exact_a11y), [])

    def test_one_over_boundaries(self) -> None:
        # 1. 331 bytes on Playwright fails
        over_pw = self.baseline_skills_42()
        desc331_pw = "Use when Playwright applies " + ("x" * (331 - len("Use when Playwright applies ")))
        for s in over_pw:
            if s["name"] == "playwright-test-profile":
                s["description"] = desc331_pw
                s["bytes"] = 331
                s["characters"] = len(desc331_pw)
        failures = checker.validate_discovery_policy("v0.10-browser-ui", over_pw)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        # 2. 331 bytes on Web-a11y fails
        over_a11y = self.baseline_skills_42()
        desc331_a11y = "Use when web accessibility applies " + ("x" * (331 - len("Use when web accessibility applies ")))
        for s in over_a11y:
            if s["name"] == "web-accessibility-profile":
                s["description"] = desc331_a11y
                s["bytes"] = 331
                s["characters"] = len(desc331_a11y)
        failures = checker.validate_discovery_policy("v0.10-browser-ui", over_a11y)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        # 3. SVG file size > 20480 fails
        over_svg = self.baseline_skills_42()
        for s in over_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20481
        failures = checker.validate_discovery_policy("v0.10-browser-ui", over_svg)
        self.assertTrue(any("exceeds SVG file limit of 20480" in f for f in failures))

        # 4. Count 41 fails
        skills41 = self.baseline_skills_42()[:41]
        failures = checker.validate_discovery_policy("v0.10-browser-ui", skills41)
        self.assertTrue(any("expected 42 leaves" in f for f in failures))

        # 5. Count 43 fails
        extra = {
            "name": "browser-runtime-profile",
            "description": "Use when browser runtime applies.",
            "bytes": len("Use when browser runtime applies.".encode("utf-8")),
            "characters": len("Use when browser runtime applies."),
            "blob_bytes": 1000,
        }
        skills43 = self.baseline_skills_42() + [extra]
        failures = checker.validate_discovery_policy("v0.10-browser-ui", skills43)
        self.assertTrue(any("expected 42 leaves" in f for f in failures))

        # 6. Count 40 fails
        skills40 = self.baseline_skills_42()[:40]
        failures = checker.validate_discovery_policy("v0.10-browser-ui", skills40)
        self.assertTrue(any("expected 42 leaves" in f for f in failures))

        # 7. Count 39 fails
        skills39 = [s for s in self.baseline_skills_42() if s["name"] in checker.ORIGINAL_39_SKILL_DESCRIPTIONS]
        failures = checker.validate_discovery_policy("v0.10-browser-ui", skills39)
        self.assertTrue(any("expected 42 leaves" in f for f in failures))

    def test_multibyte_enforcement(self) -> None:
        multibyte330 = "Use when " + ("é" * 160) + "x"
        self.assertEqual(len(multibyte330.encode("utf-8")), 330)
        self.assertEqual(len(multibyte330), 170)
        skills_mb = self.baseline_skills_42()
        for s in skills_mb:
            if s["name"] == "playwright-test-profile":
                s["description"] = multibyte330
                s["bytes"] = 330
                s["characters"] = 170
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-ui", skills_mb), [])

        multibyte331 = "Use when " + ("é" * 160) + "xx"
        self.assertEqual(len(multibyte331.encode("utf-8")), 331)
        skills_mb_over = self.baseline_skills_42()
        for s in skills_mb_over:
            if s["name"] == "playwright-test-profile":
                s["description"] = multibyte331
                s["bytes"] = 331
                s["characters"] = 171
        failures = checker.validate_discovery_policy("v0.10-browser-ui", skills_mb_over)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        tampered = self.baseline_skills_42()
        for s in tampered:
            if s["name"] == "playwright-test-profile":
                s["description"] = multibyte330
                s["bytes"] = 170
                s["characters"] = 170
        failures = checker.validate_discovery_policy("v0.10-browser-ui", tampered)
        self.assertTrue(any("description bytes mismatch" in f for f in failures))

    def test_set_equality_and_substitution(self) -> None:
        # Substituting with future candidates
        for sub_name in ("browser-runtime-profile", "npm-package-manager-profile", "vite-build-profile", "unregistered-profile"):
            with self.subTest(sub_name=sub_name):
                sub_skills = self.baseline_skills_42()
                for s in sub_skills:
                    if s["name"] == "web-accessibility-profile":
                        s["name"] = sub_name
                        s["description"] = f"Use when {sub_name} applies."
                        s["bytes"] = len(s["description"].encode("utf-8"))
                        s["characters"] = len(s["description"])
                failures = checker.validate_discovery_policy("v0.10-browser-ui", sub_skills)
                self.assertTrue(any("not authorized for admission" in f for f in failures))

        # Duplicate candidate ID
        dupe_cand = self.baseline_skills_42()
        for i, s in enumerate(dupe_cand):
            if s["name"] == "web-accessibility-profile":
                dupe_cand[i] = dict(dupe_cand[i-1])
        failures = checker.validate_discovery_policy("v0.10-browser-ui", dupe_cand)
        self.assertTrue(any("duplicate skill ID" in f for f in failures))

        # Duplicate original ID
        dupe_orig = self.baseline_skills_42()
        dupe_orig[1] = dict(dupe_orig[0])
        failures = checker.validate_discovery_policy("v0.10-browser-ui", dupe_orig)
        self.assertTrue(any("duplicate skill ID" in f for f in failures))

    def test_frozen_descriptions(self) -> None:
        # Mutating original 39 fails
        theft_orig = self.baseline_skills_42()
        for s in theft_orig:
            if s["name"] == "agentic-praxis-grimoire-workflow":
                s["description"] = "Use when APG routing is needed."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-browser-ui", theft_orig)
        self.assertTrue(any("reservation theft" in f for f in failures))

        # Mutating SVG description fails
        theft_svg = self.baseline_skills_42()
        for s in theft_svg:
            if s["name"] == "svg-language-profile":
                s["description"] = "Use when SVG authoring applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-browser-ui", theft_svg)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

    def test_body_ceiling_exemption_and_svg_limit(self) -> None:
        # Non-SVG candidate with large body bytes (> 20480) passes
        large_bodies = self.baseline_skills_42()
        for s in large_bodies:
            if s["name"] == "playwright-test-profile":
                s["blob_bytes"] = 50000
            elif s["name"] == "web-accessibility-profile":
                s["blob_bytes"] = 60000
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-ui", large_bodies), [])

        # SVG body bytes > 20480 fails
        over_svg = self.baseline_skills_42()
        for s in over_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20481
        failures = checker.validate_discovery_policy("v0.10-browser-ui", over_svg)
        self.assertTrue(any("exceeds SVG file limit of 20480" in f for f in failures))

        # Missing body bytes on Playwright fails
        missing_body = self.baseline_skills_42()
        for s in missing_body:
            if s["name"] == "playwright-test-profile":
                del s["blob_bytes"]
        failures = checker.validate_discovery_policy("v0.10-browser-ui", missing_body)
        self.assertTrue(any("missing required body bytes measurement" in f for f in failures))

    def test_malformed_metadata(self) -> None:
        # Empty name
        bad_name = self.baseline_skills_42()
        for s in bad_name:
            if s["name"] == "playwright-test-profile":
                s["name"] = ""
        failures = checker.validate_discovery_policy("v0.10-browser-ui", bad_name)
        self.assertTrue(any("empty name or description" in f for f in failures))

        # Empty description
        bad_desc = self.baseline_skills_42()
        for s in bad_desc:
            if s["name"] == "playwright-test-profile":
                s["description"] = ""
        failures = checker.validate_discovery_policy("v0.10-browser-ui", bad_desc)
        self.assertTrue(any("empty name or description" in f for f in failures))

        # Missing "Use when " prefix
        bad_prefix = self.baseline_skills_42()
        for s in bad_prefix:
            if s["name"] == "playwright-test-profile":
                s["description"] = "Invalid prefix description."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
        failures = checker.validate_discovery_policy("v0.10-browser-ui", bad_prefix)
        self.assertTrue(any("must begin with 'Use when '" in f for f in failures))

    def test_total_ceiling(self) -> None:
        skills = self.baseline_skills_42()
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-ui", skills), [])
        self.assertEqual(checker.V010_BROWSER_UI_ADMISSION_CEILING, 10517)
        self.assertEqual(checker.V010_CURRENT_BROWSER_UI_ADMISSION_CEILING, 10517)
        self.assertEqual(checker.V010_OVERALL_FUTURE_CEILING, 11507)


class DiscoveryPolicyToolchainBoundaryTests(unittest.TestCase):
    @staticmethod
    def baseline_skills_44() -> list[dict[str, object]]:
        orig = [
            {
                "name": name,
                "description": desc,
                "bytes": len(desc.encode("utf-8")),
                "characters": len(desc),
                "blob_bytes": 1000,
            }
            for name, desc in sorted(checker.ORIGINAL_39_SKILL_DESCRIPTIONS.items())
        ]
        candidates = [
            {
                "name": "svg-language-profile",
                "description": checker.FROZEN_SVG_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_SVG_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_SVG_SKILL_DESCRIPTION),
                "blob_bytes": 20480,
            },
            {
                "name": "playwright-test-profile",
                "description": checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION),
                "blob_bytes": 35000,
            },
            {
                "name": "web-accessibility-profile",
                "description": checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION),
                "blob_bytes": 40000,
            },
            {
                "name": "vite-build-profile",
                "description": "Use when Vite build configuration, bundling, plugins, dev server, or asset processing are evaluated.",
                "bytes": len("Use when Vite build configuration, bundling, plugins, dev server, or asset processing are evaluated.".encode("utf-8")),
                "characters": len("Use when Vite build configuration, bundling, plugins, dev server, or asset processing are evaluated."),
                "blob_bytes": 30000,
            },
            {
                "name": "npm-package-manager-profile",
                "description": "Use when npm package management, dependencies, workspaces, scripts, or publishing workflows are evaluated.",
                "bytes": len("Use when npm package management, dependencies, workspaces, scripts, or publishing workflows are evaluated.".encode("utf-8")),
                "characters": len("Use when npm package management, dependencies, workspaces, scripts, or publishing workflows are evaluated."),
                "blob_bytes": 32000,
            },
        ]
        return orig + candidates

    def test_exact_boundaries(self) -> None:
        baseline44 = self.baseline_skills_44()
        self.assertEqual(checker.validate_discovery_policy("v0.10-toolchain", baseline44), [])

        # SVG at exact 20480 bytes passes
        exact_svg = self.baseline_skills_44()
        for s in exact_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20480
        self.assertEqual(checker.validate_discovery_policy("v0.10-toolchain", exact_svg), [])

        # vite-build-profile at exact 330 description bytes passes
        exact_vite = self.baseline_skills_44()
        desc330_vite = "Use when Vite applies " + ("x" * (330 - len("Use when Vite applies ")))
        for s in exact_vite:
            if s["name"] == "vite-build-profile":
                s["description"] = desc330_vite
                s["bytes"] = 330
                s["characters"] = len(desc330_vite)
        self.assertEqual(checker.validate_discovery_policy("v0.10-toolchain", exact_vite), [])

        # npm-package-manager-profile at exact 330 description bytes passes
        exact_npm = self.baseline_skills_44()
        desc330_npm = "Use when npm applies " + ("x" * (330 - len("Use when npm applies ")))
        for s in exact_npm:
            if s["name"] == "npm-package-manager-profile":
                s["description"] = desc330_npm
                s["bytes"] = 330
                s["characters"] = len(desc330_npm)
        self.assertEqual(checker.validate_discovery_policy("v0.10-toolchain", exact_npm), [])

    def test_one_over_boundaries(self) -> None:
        # 1. 331 bytes on vite-build-profile fails
        over_vite = self.baseline_skills_44()
        desc331_vite = "Use when Vite applies " + ("x" * (331 - len("Use when Vite applies ")))
        for s in over_vite:
            if s["name"] == "vite-build-profile":
                s["description"] = desc331_vite
                s["bytes"] = 331
                s["characters"] = len(desc331_vite)
        failures = checker.validate_discovery_policy("v0.10-toolchain", over_vite)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        # 2. 331 bytes on npm-package-manager-profile fails
        over_npm = self.baseline_skills_44()
        desc331_npm = "Use when npm applies " + ("x" * (331 - len("Use when npm applies ")))
        for s in over_npm:
            if s["name"] == "npm-package-manager-profile":
                s["description"] = desc331_npm
                s["bytes"] = 331
                s["characters"] = len(desc331_npm)
        failures = checker.validate_discovery_policy("v0.10-toolchain", over_npm)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        # 3. SVG file size > 20480 fails
        over_svg = self.baseline_skills_44()
        for s in over_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20481
        failures = checker.validate_discovery_policy("v0.10-toolchain", over_svg)
        self.assertTrue(any("exceeds SVG file limit of 20480" in f for f in failures))

        # 4. Count 43 fails
        skills43 = self.baseline_skills_44()[:43]
        failures = checker.validate_discovery_policy("v0.10-toolchain", skills43)
        self.assertTrue(any("expected 44 leaves" in f for f in failures))

        # 5. Count 45 fails
        extra = {
            "name": "browser-runtime-profile",
            "description": "Use when browser runtime applies.",
            "bytes": len("Use when browser runtime applies.".encode("utf-8")),
            "characters": len("Use when browser runtime applies."),
            "blob_bytes": 1000,
        }
        skills45 = self.baseline_skills_44() + [extra]
        failures = checker.validate_discovery_policy("v0.10-toolchain", skills45)
        self.assertTrue(any("expected 44 leaves" in f for f in failures))

        # 6. Count 42 fails
        skills42 = self.baseline_skills_44()[:42]
        failures = checker.validate_discovery_policy("v0.10-toolchain", skills42)
        self.assertTrue(any("expected 44 leaves" in f for f in failures))

        # 7. Count 40 fails
        skills40 = self.baseline_skills_44()[:40]
        failures = checker.validate_discovery_policy("v0.10-toolchain", skills40)
        self.assertTrue(any("expected 44 leaves" in f for f in failures))

        # 8. Count 39 fails
        skills39 = [s for s in self.baseline_skills_44() if s["name"] in checker.ORIGINAL_39_SKILL_DESCRIPTIONS]
        failures = checker.validate_discovery_policy("v0.10-toolchain", skills39)
        self.assertTrue(any("expected 44 leaves" in f for f in failures))

    def test_multibyte_enforcement(self) -> None:
        multibyte330 = "Use when " + ("é" * 160) + "x"
        self.assertEqual(len(multibyte330.encode("utf-8")), 330)
        self.assertEqual(len(multibyte330), 170)
        skills_mb = self.baseline_skills_44()
        for s in skills_mb:
            if s["name"] == "vite-build-profile":
                s["description"] = multibyte330
                s["bytes"] = 330
                s["characters"] = 170
        self.assertEqual(checker.validate_discovery_policy("v0.10-toolchain", skills_mb), [])

        multibyte331 = "Use when " + ("é" * 160) + "xx"
        self.assertEqual(len(multibyte331.encode("utf-8")), 331)
        skills_mb_over = self.baseline_skills_44()
        for s in skills_mb_over:
            if s["name"] == "vite-build-profile":
                s["description"] = multibyte331
                s["bytes"] = 331
                s["characters"] = 171
        failures = checker.validate_discovery_policy("v0.10-toolchain", skills_mb_over)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        tampered = self.baseline_skills_44()
        for s in tampered:
            if s["name"] == "vite-build-profile":
                s["description"] = multibyte330
                s["bytes"] = 170
                s["characters"] = 170
        failures = checker.validate_discovery_policy("v0.10-toolchain", tampered)
        self.assertTrue(any("description bytes mismatch" in f for f in failures))

    def test_set_equality_and_substitution(self) -> None:
        # Substituting with unauthorized candidate
        for sub_name in ("browser-runtime-profile", "unregistered-profile"):
            with self.subTest(sub_name=sub_name):
                sub_skills = self.baseline_skills_44()
                for s in sub_skills:
                    if s["name"] == "npm-package-manager-profile":
                        s["name"] = sub_name
                        s["description"] = f"Use when {sub_name} applies."
                        s["bytes"] = len(s["description"].encode("utf-8"))
                        s["characters"] = len(s["description"])
                failures = checker.validate_discovery_policy("v0.10-toolchain", sub_skills)
                self.assertTrue(any("not authorized for admission" in f for f in failures))

        # Duplicate candidate ID
        dupe_cand = self.baseline_skills_44()
        for i, s in enumerate(dupe_cand):
            if s["name"] == "npm-package-manager-profile":
                dupe_cand[i] = dict(dupe_cand[i-1])
        failures = checker.validate_discovery_policy("v0.10-toolchain", dupe_cand)
        self.assertTrue(any("duplicate skill ID" in f for f in failures))

        # Duplicate original ID
        dupe_orig = self.baseline_skills_44()
        dupe_orig[1] = dict(dupe_orig[0])
        failures = checker.validate_discovery_policy("v0.10-toolchain", dupe_orig)
        self.assertTrue(any("duplicate skill ID" in f for f in failures))

    def test_frozen_descriptions(self) -> None:
        # Mutating original 39 fails
        theft_orig = self.baseline_skills_44()
        for s in theft_orig:
            if s["name"] == "agentic-praxis-grimoire-workflow":
                s["description"] = "Use when APG routing is needed."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-toolchain", theft_orig)
        self.assertTrue(any("reservation theft" in f for f in failures))

        # Mutating SVG description fails
        theft_svg = self.baseline_skills_44()
        for s in theft_svg:
            if s["name"] == "svg-language-profile":
                s["description"] = "Use when SVG authoring applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-toolchain", theft_svg)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

        # Mutating Playwright description fails
        theft_pw = self.baseline_skills_44()
        for s in theft_pw:
            if s["name"] == "playwright-test-profile":
                s["description"] = "Use when Playwright applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-toolchain", theft_pw)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

        # Mutating Web Accessibility description fails
        theft_a11y = self.baseline_skills_44()
        for s in theft_a11y:
            if s["name"] == "web-accessibility-profile":
                s["description"] = "Use when accessibility applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-toolchain", theft_a11y)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

    def test_body_ceiling_exemption_and_svg_limit(self) -> None:
        # Non-SVG candidate with large body bytes (> 20480) passes
        large_bodies = self.baseline_skills_44()
        for s in large_bodies:
            if s["name"] in ("playwright-test-profile", "web-accessibility-profile", "vite-build-profile", "npm-package-manager-profile"):
                s["blob_bytes"] = 50000
        self.assertEqual(checker.validate_discovery_policy("v0.10-toolchain", large_bodies), [])

        # SVG body bytes > 20480 fails
        over_svg = self.baseline_skills_44()
        for s in over_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20481
        failures = checker.validate_discovery_policy("v0.10-toolchain", over_svg)
        self.assertTrue(any("exceeds SVG file limit of 20480" in f for f in failures))

        # Missing body bytes on vite-build-profile fails
        missing_body = self.baseline_skills_44()
        for s in missing_body:
            if s["name"] == "vite-build-profile":
                del s["blob_bytes"]
        failures = checker.validate_discovery_policy("v0.10-toolchain", missing_body)
        self.assertTrue(any("missing required body bytes measurement" in f for f in failures))

    def test_malformed_metadata(self) -> None:
        # Empty name
        bad_name = self.baseline_skills_44()
        for s in bad_name:
            if s["name"] == "vite-build-profile":
                s["name"] = ""
        failures = checker.validate_discovery_policy("v0.10-toolchain", bad_name)
        self.assertTrue(any("empty name or description" in f for f in failures))

        # Empty description
        bad_desc = self.baseline_skills_44()
        for s in bad_desc:
            if s["name"] == "vite-build-profile":
                s["description"] = ""
        failures = checker.validate_discovery_policy("v0.10-toolchain", bad_desc)
        self.assertTrue(any("empty name or description" in f for f in failures))

        # Missing "Use when " prefix
        bad_prefix = self.baseline_skills_44()
        for s in bad_prefix:
            if s["name"] == "vite-build-profile":
                s["description"] = "Invalid prefix description."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
        failures = checker.validate_discovery_policy("v0.10-toolchain", bad_prefix)
        self.assertTrue(any("must begin with 'Use when '" in f for f in failures))

    def test_total_ceiling(self) -> None:
        skills = self.baseline_skills_44()
        self.assertEqual(checker.validate_discovery_policy("v0.10-toolchain", skills), [])
        self.assertEqual(checker.V010_TOOLCHAIN_ADMISSION_CEILING, 11177)
        self.assertEqual(checker.V010_CURRENT_TOOLCHAIN_ADMISSION_CEILING, 11177)
        self.assertEqual(checker.V010_OVERALL_FUTURE_CEILING, 11507)


class DiscoveryPolicyBrowserRuntimeBoundaryTests(unittest.TestCase):
    @staticmethod
    def baseline_skills_45() -> list[dict[str, object]]:
        orig = [
            {
                "name": name,
                "description": desc,
                "bytes": len(desc.encode("utf-8")),
                "characters": len(desc),
                "blob_bytes": 1000,
            }
            for name, desc in sorted(checker.ORIGINAL_39_SKILL_DESCRIPTIONS.items())
        ]
        candidates = [
            {
                "name": "svg-language-profile",
                "description": checker.FROZEN_SVG_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_SVG_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_SVG_SKILL_DESCRIPTION),
                "blob_bytes": 20480,
            },
            {
                "name": "playwright-test-profile",
                "description": checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION),
                "blob_bytes": 35000,
            },
            {
                "name": "web-accessibility-profile",
                "description": checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION),
                "blob_bytes": 40000,
            },
            {
                "name": "vite-build-profile",
                "description": checker.FROZEN_VITE_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_VITE_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_VITE_SKILL_DESCRIPTION),
                "blob_bytes": 30000,
            },
            {
                "name": "npm-package-manager-profile",
                "description": checker.FROZEN_NPM_SKILL_DESCRIPTION,
                "bytes": len(checker.FROZEN_NPM_SKILL_DESCRIPTION.encode("utf-8")),
                "characters": len(checker.FROZEN_NPM_SKILL_DESCRIPTION),
                "blob_bytes": 32000,
            },
            {
                "name": "browser-runtime-profile",
                "description": "Use when web decisions depend on browser host behavior — Window, Document, DOM mutation, event phases, tasks, microtasks, timers, rAF, MutationObserver, URL, History, Fetch, CORS, cookies, WebStorage, IndexedDB, custom elements, Shadow DOM, geometry, workers, or object URLs — for an established browser execution role.",
                "bytes": 323,
                "characters": 319,
                "blob_bytes": 20085,
            },
        ]
        return orig + candidates

    def test_exact_boundaries(self) -> None:
        baseline45 = self.baseline_skills_45()
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-runtime", baseline45), [])

        # SVG at exact 20480 bytes passes
        exact_svg = self.baseline_skills_45()
        for s in exact_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20480
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-runtime", exact_svg), [])

        # browser-runtime-profile at exact 330 description bytes passes
        exact_br = self.baseline_skills_45()
        desc330_br = "Use when browser runtime applies " + ("x" * (330 - len("Use when browser runtime applies ")))
        for s in exact_br:
            if s["name"] == "browser-runtime-profile":
                s["description"] = desc330_br
                s["bytes"] = 330
                s["characters"] = len(desc330_br)
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-runtime", exact_br), [])

    def test_one_over_boundaries(self) -> None:
        # 1. 331 bytes on browser-runtime-profile fails
        over_br = self.baseline_skills_45()
        desc331_br = "Use when browser runtime applies " + ("x" * (331 - len("Use when browser runtime applies ")))
        for s in over_br:
            if s["name"] == "browser-runtime-profile":
                s["description"] = desc331_br
                s["bytes"] = 331
                s["characters"] = len(desc331_br)
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", over_br)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        # 2. SVG file size > 20480 fails
        over_svg = self.baseline_skills_45()
        for s in over_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20481
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", over_svg)
        self.assertTrue(any("exceeds SVG file limit of 20480" in f for f in failures))

        # 3. Count 44 fails
        skills44 = self.baseline_skills_45()[:44]
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", skills44)
        self.assertTrue(any("expected 45 leaves" in f for f in failures))

        # 4. Count 46 fails
        extra = {
            "name": "extra-test-profile",
            "description": "Use when extra profile applies.",
            "bytes": len("Use when extra profile applies.".encode("utf-8")),
            "characters": len("Use when extra profile applies."),
            "blob_bytes": 1000,
        }
        skills46 = self.baseline_skills_45() + [extra]
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", skills46)
        self.assertTrue(any("expected 45 leaves" in f for f in failures))

        # 5. Count 42 fails
        skills42 = self.baseline_skills_45()[:42]
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", skills42)
        self.assertTrue(any("expected 45 leaves" in f for f in failures))

        # 6. Count 40 fails
        skills40 = self.baseline_skills_45()[:40]
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", skills40)
        self.assertTrue(any("expected 45 leaves" in f for f in failures))

        # 7. Count 39 fails
        skills39 = [s for s in self.baseline_skills_45() if s["name"] in checker.ORIGINAL_39_SKILL_DESCRIPTIONS]
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", skills39)
        self.assertTrue(any("expected 45 leaves" in f for f in failures))

    def test_multibyte_enforcement(self) -> None:
        multibyte330 = "Use when " + ("é" * 160) + "x"
        self.assertEqual(len(multibyte330.encode("utf-8")), 330)
        self.assertEqual(len(multibyte330), 170)
        skills_mb = self.baseline_skills_45()
        for s in skills_mb:
            if s["name"] == "browser-runtime-profile":
                s["description"] = multibyte330
                s["bytes"] = 330
                s["characters"] = 170
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-runtime", skills_mb), [])

        multibyte331 = "Use when " + ("é" * 160) + "xx"
        self.assertEqual(len(multibyte331.encode("utf-8")), 331)
        skills_mb_over = self.baseline_skills_45()
        for s in skills_mb_over:
            if s["name"] == "browser-runtime-profile":
                s["description"] = multibyte331
                s["bytes"] = 331
                s["characters"] = 171
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", skills_mb_over)
        self.assertTrue(any("exceeds reservation ceiling of 330" in f for f in failures))

        tampered = self.baseline_skills_45()
        for s in tampered:
            if s["name"] == "browser-runtime-profile":
                s["description"] = multibyte330
                s["bytes"] = 170
                s["characters"] = 170
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", tampered)
        self.assertTrue(any("description bytes mismatch" in f for f in failures))

    def test_set_equality_and_substitution(self) -> None:
        # Substituting with unauthorized candidate
        for sub_name in ("unknown-runtime-profile", "unregistered-profile"):
            with self.subTest(sub_name=sub_name):
                sub_skills = self.baseline_skills_45()
                for s in sub_skills:
                    if s["name"] == "browser-runtime-profile":
                        s["name"] = sub_name
                        s["description"] = f"Use when {sub_name} applies."
                        s["bytes"] = len(s["description"].encode("utf-8"))
                        s["characters"] = len(s["description"])
                failures = checker.validate_discovery_policy("v0.10-browser-runtime", sub_skills)
                self.assertTrue(any("not authorized for admission" in f for f in failures))

        # Duplicate candidate ID
        dupe_cand = self.baseline_skills_45()
        for i, s in enumerate(dupe_cand):
            if s["name"] == "browser-runtime-profile":
                dupe_cand[i] = dict(dupe_cand[i-1])
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", dupe_cand)
        self.assertTrue(any("duplicate skill ID" in f for f in failures))

        # Duplicate original ID
        dupe_orig = self.baseline_skills_45()
        dupe_orig[1] = dict(dupe_orig[0])
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", dupe_orig)
        self.assertTrue(any("duplicate skill ID" in f for f in failures))

    def test_frozen_descriptions(self) -> None:
        # Mutating original 39 fails
        theft_orig = self.baseline_skills_45()
        for s in theft_orig:
            if s["name"] == "agentic-praxis-grimoire-workflow":
                s["description"] = "Use when APG routing is needed."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", theft_orig)
        self.assertTrue(any("reservation theft" in f for f in failures))

        # Mutating SVG description fails
        theft_svg = self.baseline_skills_45()
        for s in theft_svg:
            if s["name"] == "svg-language-profile":
                s["description"] = "Use when SVG authoring applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", theft_svg)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

        # Mutating Playwright description fails
        theft_pw = self.baseline_skills_45()
        for s in theft_pw:
            if s["name"] == "playwright-test-profile":
                s["description"] = "Use when Playwright applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", theft_pw)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

        # Mutating Web Accessibility description fails
        theft_a11y = self.baseline_skills_45()
        for s in theft_a11y:
            if s["name"] == "web-accessibility-profile":
                s["description"] = "Use when accessibility applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", theft_a11y)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

        # Mutating Vite description fails
        theft_vite = self.baseline_skills_45()
        for s in theft_vite:
            if s["name"] == "vite-build-profile":
                s["description"] = "Use when Vite applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", theft_vite)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

        # Mutating NPM description fails
        theft_npm = self.baseline_skills_45()
        for s in theft_npm:
            if s["name"] == "npm-package-manager-profile":
                s["description"] = "Use when npm applies."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
                break
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", theft_npm)
        self.assertTrue(any("reservation theft" in f or "mutated" in f for f in failures))

    def test_body_ceiling_exemption_and_svg_limit(self) -> None:
        # Non-SVG candidate with large body bytes (> 20480) passes
        large_bodies = self.baseline_skills_45()
        for s in large_bodies:
            if s["name"] in ("playwright-test-profile", "web-accessibility-profile", "vite-build-profile", "npm-package-manager-profile", "browser-runtime-profile"):
                s["blob_bytes"] = 50000
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-runtime", large_bodies), [])

        # SVG body bytes > 20480 fails
        over_svg = self.baseline_skills_45()
        for s in over_svg:
            if s["name"] == "svg-language-profile":
                s["blob_bytes"] = 20481
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", over_svg)
        self.assertTrue(any("exceeds SVG file limit of 20480" in f for f in failures))

        # Missing body bytes on browser-runtime-profile fails
        missing_body = self.baseline_skills_45()
        for s in missing_body:
            if s["name"] == "browser-runtime-profile":
                del s["blob_bytes"]
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", missing_body)
        self.assertTrue(any("missing required body bytes measurement" in f for f in failures))

    def test_malformed_metadata(self) -> None:
        # Empty name
        bad_name = self.baseline_skills_45()
        for s in bad_name:
            if s["name"] == "browser-runtime-profile":
                s["name"] = ""
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", bad_name)
        self.assertTrue(any("empty name or description" in f for f in failures))

        # Empty description
        bad_desc = self.baseline_skills_45()
        for s in bad_desc:
            if s["name"] == "browser-runtime-profile":
                s["description"] = ""
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", bad_desc)
        self.assertTrue(any("empty name or description" in f for f in failures))

        # Missing "Use when " prefix
        bad_prefix = self.baseline_skills_45()
        for s in bad_prefix:
            if s["name"] == "browser-runtime-profile":
                s["description"] = "Invalid prefix description."
                s["bytes"] = len(s["description"].encode("utf-8"))
                s["characters"] = len(s["description"])
        failures = checker.validate_discovery_policy("v0.10-browser-runtime", bad_prefix)
        self.assertTrue(any("must begin with 'Use when '" in f for f in failures))

    def test_total_ceiling(self) -> None:
        skills = self.baseline_skills_45()
        self.assertEqual(checker.validate_discovery_policy("v0.10-browser-runtime", skills), [])
        self.assertEqual(checker.V010_BROWSER_RUNTIME_ADMISSION_CEILING, 11507)
        self.assertEqual(checker.V010_CURRENT_BROWSER_RUNTIME_ADMISSION_CEILING, 11507)
        self.assertEqual(checker.V010_OVERALL_FUTURE_CEILING, 11507)


class TestV010CheckerIntegration(unittest.TestCase):
    def test_reservation_diagnostic_apg042(self) -> None:
        desc331 = "Use when SVG syntax applies " + ("x" * (331 - len("Use when SVG syntax applies ")))
        data = (
            f"---\nname: svg-language-profile\ndescription: {desc331}\n---\n"
            "# Profile\n"
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("svg-language-profile"),
            Path("svg-language-profile/SKILL.md"),
            "skills/svg-language-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
        )
        codes = {d.code for d in diagnostics}
        self.assertIn("APG042", codes)

    def test_svg_file_size_diagnostic_apg043(self) -> None:
        desc = "Use when SVG syntax applies to coordinates, path semantics, or transforms."
        body_padding = "<!-- " + ("p" * 21000) + " -->\n"
        data = (
            f"---\nname: svg-language-profile\ndescription: {desc}\n---\n"
            "# Profile\n"
            + body_padding
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        self.assertGreater(len(data), 20480)
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("svg-language-profile"),
            Path("svg-language-profile/SKILL.md"),
            "skills/svg-language-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
        )
        codes = {d.code for d in diagnostics}
        self.assertIn("APG043", codes)

    def test_original_39_freeze_diagnostic_apg044(self) -> None:
        desc_mutated = "Use when an operator or manager needs to choose among APG skills."
        data = (
            f"---\nname: agentic-praxis-grimoire-workflow\ndescription: {desc_mutated}\n---\n"
            "# Profile\n"
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("agentic-praxis-grimoire-workflow"),
            Path("agentic-praxis-grimoire-workflow/SKILL.md"),
            "skills/agentic-praxis-grimoire-workflow/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
        )
        codes = {d.code for d in diagnostics}
        self.assertIn("APG044", codes)

    def test_discovery_policy_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            root = Path(temp_dir_str)
            self.assertEqual(checker._resolve_discovery_policy(root), (None, None))
            self.assertEqual(checker._resolve_discovery_policy(root, "v0.10"), ("v0.10", None))
            self.assertIsNotNone(checker._resolve_discovery_policy(root, " ")[1])
            owner = root / "skills/discovery_policy.go"
            owner.parent.mkdir()
            owner.write_text("package skills")
            self.assertIn("missing", checker._resolve_discovery_policy(root)[1])
            selector = root / checker.DISCOVERY_POLICY_SELECTOR
            selector.parent.mkdir()
            for invalid in ('{}', '{broken', '[]', '{"schema_version":true,"policy":"v0.10"}',
                            '{"schema_version":1,"policy":"v0.10","policy":"v0.10"}',
                            '{"schema_version":1,"policy":null}',
                            '{"schema_version":1,"policy":"v0.10","extra":0}'):
                selector.write_text(invalid)
                self.assertIsNotNone(checker._resolve_discovery_policy(root)[1], invalid)
            selector.write_text('{"schema_version":1,"policy":"v0.10"}')
            self.assertEqual(checker._resolve_discovery_policy(root), ("v0.10", None))
            selector.write_text('{"schema_version":1,"policy":"v0.10-toolchain"}')
            self.assertEqual(checker._resolve_discovery_policy(root), ("v0.10-toolchain", None))
            self.assertIsNotNone(checker._resolve_discovery_policy(root, "v99")[1])
            selector.unlink()
            selector.symlink_to(owner)
            self.assertIsNotNone(checker._resolve_discovery_policy(root)[1])

    def test_check_library_fail_closed_on_policy_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            # Create minimal skills directory
            skills_dir = temp_dir / "skills"
            skills_dir.mkdir(parents=True)
            catalog = temp_dir / "skills" / "README.md"
            catalog.write_text(
                "# Skills\n| Name | Description |\n| --- | --- |\n",
                encoding="utf-8",
            )

            # Unknown explicit policy fails closed with APG048
            res = checker.check_library(temp_dir, policy="v99.99")
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG048", codes)

            # Malformed selector file fails closed with APG048
            sel_file = temp_dir / "testing" / "apg-discovery-policy.json"
            sel_file.parent.mkdir(parents=True, exist_ok=True)
            sel_file.write_text("{broken", encoding="utf-8")
            res2 = checker.check_library(temp_dir)
            codes2 = {d.code for d in res2.diagnostics}
            self.assertIn("APG048", codes2)

    def test_browser_ui_svg_freeze_diagnostic_apg044(self) -> None:
        desc_mutated = "Use when SVG authoring applies."
        data = (
            f"---\nname: svg-language-profile\ndescription: {desc_mutated}\n---\n"
            "# Profile\n"
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("svg-language-profile"),
            Path("svg-language-profile/SKILL.md"),
            "skills/svg-language-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
            policy="v0.10-browser-ui",
        )
        codes = {d.code for d in diagnostics}
        self.assertIn("APG044", codes)

    def test_browser_ui_non_svg_file_size_exemption(self) -> None:
        desc = "Use when Playwright applies."
        body_padding = "<!-- " + ("p" * 25000) + " -->\n"
        data = (
            f"---\nname: playwright-test-profile\ndescription: {desc}\n---\n"
            "# Profile\n"
            + body_padding
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        self.assertGreater(len(data), 20480)
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("playwright-test-profile"),
            Path("playwright-test-profile/SKILL.md"),
            "skills/playwright-test-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
            policy="v0.10-browser-ui",
        )
        codes = {d.code for d in diagnostics}
        self.assertNotIn("APG043", codes)

    def test_toolchain_playwright_freeze_diagnostic_apg044(self) -> None:
        desc_mutated = "Use when Playwright applies."
        data = (
            f"---\nname: playwright-test-profile\ndescription: {desc_mutated}\n---\n"
            "# Profile\n"
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("playwright-test-profile"),
            Path("playwright-test-profile/SKILL.md"),
            "skills/playwright-test-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
            policy="v0.10-toolchain",
        )
        codes = {d.code for d in diagnostics}
        self.assertIn("APG044", codes)

    def test_toolchain_web_accessibility_freeze_diagnostic_apg044(self) -> None:
        desc_mutated = "Use when accessibility applies."
        data = (
            f"---\nname: web-accessibility-profile\ndescription: {desc_mutated}\n---\n"
            "# Profile\n"
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("web-accessibility-profile"),
            Path("web-accessibility-profile/SKILL.md"),
            "skills/web-accessibility-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
            policy="v0.10-toolchain",
        )
        codes = {d.code for d in diagnostics}
        self.assertIn("APG044", codes)

    def test_toolchain_non_svg_file_size_exemption(self) -> None:
        desc = "Use when Vite applies."
        body_padding = "<!-- " + ("p" * 25000) + " -->\n"
        data = (
            f"---\nname: vite-build-profile\ndescription: {desc}\n---\n"
            "# Profile\n"
            + body_padding
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        self.assertGreater(len(data), 20480)
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("vite-build-profile"),
            Path("vite-build-profile/SKILL.md"),
            "skills/vite-build-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
            policy="v0.10-toolchain",
        )
        codes = {d.code for d in diagnostics}
        self.assertNotIn("APG043", codes)

    def test_browser_runtime_vite_freeze_diagnostic_apg044(self) -> None:
        desc_mutated = "Use when Vite applies."
        data = (
            f"---\nname: vite-build-profile\ndescription: {desc_mutated}\n---\n"
            "# Profile\n"
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("vite-build-profile"),
            Path("vite-build-profile/SKILL.md"),
            "skills/vite-build-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
            policy="v0.10-browser-runtime",
        )
        codes = {d.code for d in diagnostics}
        self.assertIn("APG044", codes)

    def test_browser_runtime_npm_freeze_diagnostic_apg044(self) -> None:
        desc_mutated = "Use when npm applies."
        data = (
            f"---\nname: npm-package-manager-profile\ndescription: {desc_mutated}\n---\n"
            "# Profile\n"
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("npm-package-manager-profile"),
            Path("npm-package-manager-profile/SKILL.md"),
            "skills/npm-package-manager-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
            policy="v0.10-browser-runtime",
        )
        codes = {d.code for d in diagnostics}
        self.assertIn("APG044", codes)

    def test_browser_runtime_non_svg_file_size_exemption(self) -> None:
        desc = "Use when browser runtime applies."
        body_padding = "<!-- " + ("p" * 25000) + " -->\n"
        data = (
            f"---\nname: browser-runtime-profile\ndescription: {desc}\n---\n"
            "# Profile\n"
            + body_padding
            + "".join(f"\n## {h}\nEvidence.\n" for h in checker.REQUIRED_H2S)
        ).encode("utf-8")
        self.assertGreater(len(data), 20480)
        diagnostics: list[Diagnostic] = []
        checker._check_frontmatter_and_body(
            Path("browser-runtime-profile"),
            Path("browser-runtime-profile/SKILL.md"),
            "skills/browser-runtime-profile/SKILL.md",
            data,
            data.decode("utf-8"),
            diagnostics,
            [],
            policy="v0.10-browser-runtime",
        )
        codes = {d.code for d in diagnostics}
        self.assertNotIn("APG043", codes)
