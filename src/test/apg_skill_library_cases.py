#!/usr/bin/env python3
"""Unit tests for the APG skill-library lexical subset."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from src.test.apg_test_support import repository_root


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
)


class CompleteCheckerBoundaryTests(unittest.TestCase):
    def test_minimal_valid_library_passes_complete_checker_contract(self) -> None:
        name = "debugging-systematically"
        trigger = (
            "Behavior is failing, inconsistent, flaky, unexplained, or has multiple plausible causes"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "skills" / name
            leaf.mkdir(parents=True)
            source = REPOSITORY_ROOT / "skills" / name / "SKILL.md"
            (leaf / "SKILL.md").write_bytes(source.read_bytes())
            (root / "skills" / "README.md").write_text(
                "# APG Skill Library\n\n## Current development catalog\n\n"
                "| Skill | Trigger boundary | Maturity |\n| --- | --- | --- |\n"
                f"| [`{name}`]({name}/SKILL.md) | {trigger} | `stable` |\n"
            )
            projection_root = root / ".agents" / "skills"
            projection_root.mkdir(parents=True)
            (projection_root / name).symlink_to(
                Path("../../skills") / name,
                target_is_directory=True,
            )
            result = check_library(root)
        self.assertTrue(result.passed, render_text(result))
        self.assertEqual((result.canonical_skills, result.catalog_rows, result.projections), (1, 1, 1))

    def test_missing_library_aggregates_owned_diagnostics_and_renders_both_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = check_library(root)
        self.assertFalse(result.passed)
        self.assertEqual(result.canonical_skills, 0)
        self.assertEqual(result.catalog_rows, 0)
        self.assertEqual(result.projections, 0)
        self.assertIn("APG001", {item.code for item in result.diagnostics})
        rendered = json.loads(render_json(result))
        self.assertEqual(rendered["status"], "fail")
        self.assertEqual(rendered["summary"]["canonical_skills"], 0)
        self.assertIn("FAIL APG skill library", render_text(result))

    def test_malformed_tree_reports_leaf_catalog_and_projection_contracts_together(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skills = root / "skills"
            skills.mkdir()
            (skills / "unexpected.txt").write_text("unexpected")
            leaf = skills / "example-skill"
            leaf.mkdir()
            (leaf / "SKILL.md").write_text(
                "---\nname: wrong-name\ndescription: test\n---\n# Wrong\n"
            )
            (skills / "README.md").write_text(
                "# Skill Library\n\n| Skill | Capability class | Trigger |\n"
                "| --- | --- | --- |\n| [missing](missing/SKILL.md) | class | trigger |\n"
            )
            projections = root / ".agents" / "skills"
            projections.mkdir(parents=True)
            (projections / "unexpected").mkdir()
            result = check_library(root)
        codes = {item.code for item in result.diagnostics}
        self.assertFalse(result.passed)
        self.assertGreaterEqual(result.canonical_skills, 1)
        self.assertTrue({"APG003", "APG011"}.intersection(codes))
        self.assertGreater(len(codes), 3)

    def test_checker_reports_missing_leaf_file_and_projection_root_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "skills" / "example-skill"
            leaf.mkdir(parents=True)
            (root / "skills" / "README.md").write_text(
                "# APG Skill Library\n\n## Current development catalog\n\n"
                "| Skill | Trigger boundary | Maturity |\n| --- | --- | --- |\n"
                "| [`example-skill`](example-skill/SKILL.md) | trigger | `stable` |\n"
            )
            (root / ".agents").write_text("unsafe")
            result = check_library(root)
        codes = {item.code for item in result.diagnostics}
        self.assertIn("APG005", codes)
        self.assertIn("APG029", codes)

    def test_checker_reports_duplicate_declarations_and_wrong_projection_shapes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skills = root / "skills"
            skills.mkdir()
            for leaf_name in ("first", "second"):
                leaf = skills / leaf_name
                leaf.mkdir()
                (leaf / "SKILL.md").write_text(
                    "---\nname: shared\ndescription: trigger\n---\n"
                    "# Shared\n\n## Core principle\ntext\n\n## Do not use\ntext\n"
                    "\n## Procedure\ntext\n\n## Project-owned parameters\ntext\n"
                    "\n## Evidence and completion\ntext\n\n## Stop or escalate\ntext\n"
                    "\n## Common mistakes\ntext\n"
                )
            (skills / "README.md").write_text(
                "# APG Skill Library\n\n## Current development catalog\n\n"
                "| Skill | Trigger boundary | Maturity |\n| --- | --- | --- |\n"
                "| [`first`](first/SKILL.md) | trigger | `invalid` |\n"
                "| [`first`](first/SKILL.md) | trigger | `stable` |\n"
            )
            projection = root / ".agents" / "skills"
            projection.mkdir(parents=True)
            (projection / "first").write_text("not a link")
            result = check_library(root)
        codes = {item.code for item in result.diagnostics}
        self.assertIn("APG013", codes)
        self.assertGreater(len(codes), 5)

    def test_catalog_parser_reports_malformed_rows_duplicates_and_trailing_content(self) -> None:
        text = (
            "## Current development catalog\n\n"
            "| Skill | Trigger boundary | Maturity |\n| --- | --- | --- |\n"
            "| malformed | row |\n"
            "| [`one`](one/SKILL.md) | trigger | `stable` |\n"
            "| [`one`](one/SKILL.md) | trigger | `stable` |\n\n"
            "trailing content\n"
        )
        parsed = parse_catalog(text)
        self.assertGreater(len(parsed.malformed_lines), 0)
        self.assertEqual(len(parsed.rows), 2)

    def test_leaf_checker_aggregates_frontmatter_heading_and_link_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "skills" / "Invalid_Name"
            leaf.mkdir(parents=True)
            (leaf / "SKILL.md").write_text(
                "---\nname: Invalid_Name\nname: duplicate\n"
                "description: not trigger oriented\ninvalid key: value\n---\n"
                "# First\n# Second\n\n[missing](missing.md)\n[escape](../../outside.md)\n"
            )
            diagnostics: list[Diagnostic] = []
            declared: list[tuple[str, str]] = []
            checker._check_leaf(root, leaf, diagnostics, declared)
        codes = {item.code for item in diagnostics}
        self.assertTrue({"APG009", "APG014", "APG015", "APG016", "APG021"}.issubset(codes))

    def test_leaf_checker_validates_every_optional_support_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "skills" / "example"
            leaf.mkdir(parents=True)
            (leaf / "SKILL.md").write_text(
                "---\nname: example\ndescription: Use when testing.\n---\n# Example\n"
                + "".join(f"\n## {heading}\ntext\n" for heading in checker.REQUIRED_H2S)
                + "\n[anchor](#section) [external](https://example.test) [valid](local.md)\n"
            )
            (leaf / "local.md").write_text("local")
            (leaf / "unexpected.txt").write_text("unexpected")
            (leaf / "scripts").mkdir()
            assets = leaf / "assets"
            assets.mkdir()
            (assets / "local.md").write_text("[missing](missing.md)\n")
            (assets / "internal.md").symlink_to("local.md")
            outside = root / "outside.md"
            outside.write_text("outside")
            (assets / "escape").symlink_to(outside)
            agents = leaf / "agents"
            agents.mkdir()
            (agents / "data.bin").write_bytes(b"\xff")
            references_target = leaf / "references-target"
            references_target.mkdir()
            (leaf / "references").symlink_to(references_target, target_is_directory=True)
            diagnostics: list[Diagnostic] = []
            declared: list[tuple[str, str]] = []
            checker._check_leaf(root, leaf, diagnostics, declared)
        codes = {item.code for item in diagnostics}
        self.assertTrue({"APG017", "APG018", "APG019", "APG020", "APG021"}.issubset(codes))

    def test_checker_helper_alternatives_cover_empty_metadata_catalog_and_escaping_links(self) -> None:
        parsed = parse_frontmatter(b"body only\n")
        self.assertIsNone(parsed.line_for("missing"))
        self.assertEqual(checker.markdown_body("body only", parsed), "")
        self.assertFalse(parse_catalog("## Current development catalog\n").header_valid)
        self.assertFalse(
            parse_catalog(
                "## Current development catalog\n\n| wrong | header |\n| --- | --- | --- |\n"
            ).header_valid
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "skills" / "example"
            leaf.mkdir(parents=True)
            outside = root / "outside.md"
            outside.write_text("outside")
            markdown = leaf / "SKILL.md"
            markdown.write_text("[escape](../../outside.md)\n")
            diagnostics: list[Diagnostic] = []
            checker._check_local_links(leaf, markdown, markdown.read_text(), root, diagnostics)
            self.assertIn("escapes", diagnostics[0].message)

            projection_root = root / ".agents" / "skills"
            projection_root.mkdir(parents=True)
            wrong = root / "wrong"
            wrong.mkdir()
            (projection_root / "example").symlink_to(wrong, target_is_directory=True)
            diagnostics.clear()
            checker._check_projection(root, {"example": leaf}, diagnostics)
            codes = {item.code for item in diagnostics}
            self.assertTrue({"APG032", "APG033"}.issubset(codes))

    def test_checker_defensive_content_paths_report_invalid_utf8_and_scalar_forms(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "skills" / "Bad_Name"
            leaf.mkdir(parents=True)
            skill = leaf / "SKILL.md"
            diagnostics: list[Diagnostic] = []
            declared: list[tuple[str, str]] = []
            malformed = b"\xef\xbb\xbf---\nname: Bad_Name\ndescription: \"quoted\"\n"
            checker._check_frontmatter_and_body(
                leaf,
                skill,
                "skills/Bad_Name/SKILL.md",
                malformed,
                malformed.decode("utf-8"),
                diagnostics,
                declared,
            )
            skill.write_bytes(b"\xff")
            checker._check_leaf(root, leaf, diagnostics, declared)
            readme = root / "skills" / "README.md"
            readme.write_bytes(b"\xff")
            checker._check_catalog(root, readme, {"Bad_Name"}, diagnostics)
            codes = {item.code for item in diagnostics}
            self.assertTrue({"APG007", "APG008", "APG010", "APG006"}.issubset(codes))

            rendered = render_text(
                CheckResult(
                    (Diagnostic("APG999", "path", "invariant", "message", "action", 2, None),),
                    0,
                    0,
                    0,
                )
            )
            self.assertIn("path:2 APG999", rendered)

    def test_checker_remaining_support_projection_and_symlink_alternatives_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "skills" / "example"
            leaf.mkdir(parents=True)
            skill = leaf / "SKILL.md"
            skill.write_text(
                "---\nname: example\ndescription: Use when testing.\n---\n# Example\n"
                + "".join(f"\n## {heading}\ntext\n" for heading in checker.REQUIRED_H2S)
            )
            assets = leaf / "assets"
            assets.mkdir()
            (assets / "target.bin").write_bytes(b"data")
            (assets / "internal").symlink_to("target.bin")
            (assets / "invalid.md").write_bytes(b"\xff")
            (assets / "invalid-link.md").symlink_to("invalid.md")
            diagnostics: list[Diagnostic] = []
            checker._check_leaf(root, leaf, diagnostics, [])
            self.assertIn("APG006", {item.code for item in diagnostics})

            projection = root / ".agents" / "skills"
            projection.mkdir(parents=True)
            skill.unlink()
            (projection / "example").symlink_to(
                Path("../../skills/example"), target_is_directory=True
            )
            diagnostics.clear()
            checker._check_projection(root, {"example": leaf}, diagnostics)
            self.assertIn("APG034", {item.code for item in diagnostics})

            external = root / "external"
            external.mkdir()
            (root / "skills" / "linked").symlink_to(external, target_is_directory=True)
            result = check_library(root)
            self.assertIn("APG004", {item.code for item in result.diagnostics})

    def test_checker_reports_empty_catalog_trigger_and_duplicate_name_nonmatches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skills = root / "skills"
            skills.mkdir()
            for directory, declared_name in (("first", "shared"), ("second", "shared"), ("third", "other")):
                leaf = skills / directory
                leaf.mkdir()
                (leaf / "SKILL.md").write_text(
                    f"---\nname: {declared_name}\ndescription: Use when testing.\n---\n# Test\n"
                )
            (skills / "README.md").write_text(
                "## Current development catalog\n\n"
                "| Skill | Trigger boundary | Maturity |\n| --- | --- | --- |\n"
                "| [`first`](first/SKILL.md) |  | `stable` |\n"
            )
            diagnostics: list[Diagnostic] = []
            checker._check_catalog(root, skills / "README.md", {"first", "second", "third"}, diagnostics)
            self.assertIn("APG027", {item.code for item in diagnostics})
            result = check_library(root)
            self.assertGreaterEqual(sum(item.code == "APG013" for item in result.diagnostics), 2)

    def test_text_rendering_uses_singular_diagnostic_and_precise_location(self) -> None:
        diagnostic = Diagnostic(
            "APG999",
            "skills/example/SKILL.md",
            "test-invariant",
            "message",
            "action",
            4,
            2,
        )
        result = CheckResult((diagnostic,), 1, 0, 0)
        rendered = render_text(result)
        self.assertIn("skills/example/SKILL.md:4:2", rendered)
        self.assertIn("1 diagnostic,", rendered)

    def test_main_returns_pass_and_failure_status_from_checker(self) -> None:
        passing = CheckResult((), 1, 1, 1)
        failing = CheckResult(
            (Diagnostic("APG999", "path", "invariant", "message", "action"),),
            0,
            0,
            0,
        )
        with mock.patch.object(checker, "check_library", return_value=passing):
            self.assertEqual(main(["--root", ".", "--format", "json"]), 0)
        with mock.patch.object(checker, "check_library", return_value=failing):
            self.assertEqual(main(["--root", ".", "--format", "text"]), 1)

if __name__ == "__main__":
    unittest.main()
