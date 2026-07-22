#!/usr/bin/env python3
"""Unit tests for the APG skill-library lexical subset."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from apg_skill_library_check import (  # noqa: E402
    inline_links,
    parse_catalog,
    parse_frontmatter,
    valid_skill_name,
    visible_lines,
)


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
        catalog = parse_catalog(
            (REPOSITORY_ROOT / "skills" / "README.md").read_text()
        )
        catalog_names = {row.name for row in catalog.rows}
        routable_names = catalog_names - {router_name}

        map_path = (
            REPOSITORY_ROOT
            / "skills"
            / router_name
            / "references"
            / "capability-map.json"
        )
        capability_map = json.loads(map_path.read_text())

        self.assertEqual(
            set(capability_map),
            {"schema_version", "router_name", "capabilities"},
        )
        self.assertEqual(capability_map["schema_version"], 1)
        self.assertEqual(capability_map["router_name"], router_name)

        capabilities = capability_map["capabilities"]
        self.assertEqual(
            capabilities,
            sorted(capabilities, key=lambda entry: entry["name"]),
        )
        self.assertEqual(
            {entry["name"] for entry in capabilities}, routable_names
        )
        self.assertEqual(len(capabilities), len(routable_names))
        for entry in capabilities:
            with self.subTest(name=entry["name"]):
                self.assertEqual(
                    set(entry), {"name", "capability_class", "trigger"}
                )
                self.assertNotEqual(entry["name"], router_name)
                self.assertTrue(entry["capability_class"].strip())
                self.assertTrue(entry["trigger"].strip())

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
            / "agentic-praxis-grimoire-workflow"
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

if __name__ == "__main__":
    unittest.main()
