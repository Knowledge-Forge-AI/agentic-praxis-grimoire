#!/usr/bin/env python3
"""Unit tests for the APG skill-library lexical subset."""

from __future__ import annotations

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
            "## APG v0.1 catalog\n\n"
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


if __name__ == "__main__":
    unittest.main()
