#!/usr/bin/env python3
"""Integration tests for bin/apg-check-skill-library."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
COMMAND = REPOSITORY_ROOT / "bin" / "apg-check-skill-library"
REQUIRED_H2S = (
    "Core principle",
    "Do not use",
    "Procedure",
    "Project-owned parameters",
    "Evidence and completion",
    "Stop or escalate",
    "Common mistakes",
)


def skill_text(name: str) -> str:
    sections = "\n\n".join(
        f"## {heading}\n\nEvidence for {heading.lower()}." for heading in REQUIRED_H2S
    )
    return (
        "---\n"
        f"name: {name}\n"
        f"description: Use when {name} is required.\n"
        "---\n\n"
        f"# {name}\n\n"
        f"{sections}\n"
    )


def catalog_text(names: tuple[str, ...]) -> str:
    rows = "\n".join(
        f"| [`{name}`]({name}/SKILL.md) | Trigger for {name} | `provisional` |"
        for name in names
    )
    return (
        "# APG Skill Library\n\n"
        "## APG v0.1 catalog\n\n"
        "| Skill | Trigger boundary | Maturity |\n"
        "| --- | --- | --- |\n"
        f"{rows}\n"
    )


class APGCheckSkillLibraryTests(unittest.TestCase):
    """Exercise the real command against generated APG-shaped trees."""

    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="apg-check-test-")
        self.base = Path(self.temporary.name)
        self.root = self.base / "library"
        self.names = ("alpha-skill", "beta-skill")
        self.create_valid_library(self.root, self.names)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_valid_library(
        self, root: Path, names: tuple[str, ...]
    ) -> None:
        skills = root / "skills"
        projection = root / ".agents" / "skills"
        skills.mkdir(parents=True)
        projection.mkdir(parents=True)
        (skills / "README.md").write_text(catalog_text(names), encoding="utf-8")
        for name in names:
            leaf = skills / name
            leaf.mkdir()
            (leaf / "SKILL.md").write_text(skill_text(name), encoding="utf-8")
            (projection / name).symlink_to(
                Path("../../skills") / name, target_is_directory=True
            )

    def run_checker(
        self,
        root: Path | None = None,
        *arguments: str,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [str(COMMAND)]
        if root is not None:
            command.extend(["--root", str(root)])
        command.extend(arguments)
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(cwd or self.base),
            env=os.environ.copy(),
        )

    def result_codes(self, root: Path | None = None) -> set[str]:
        result = self.run_checker(root or self.root, "--format", "json")
        self.assertEqual(result.returncode, 1, result)
        payload = json.loads(result.stdout)
        return {item["code"] for item in payload["diagnostics"]}

    def replace_skill(self, name: str, old: str, new: str) -> None:
        path = self.root / "skills" / name / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def tree_fingerprint(self, root: Path) -> tuple[tuple[object, ...], ...]:
        records: list[tuple[object, ...]] = []
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            relative = path.relative_to(root).as_posix()
            metadata = path.lstat()
            mode = stat.S_IMODE(metadata.st_mode)
            if path.is_symlink():
                records.append((relative, "link", mode, os.readlink(path)))
            elif path.is_dir():
                records.append((relative, "dir", mode))
            elif path.is_file():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                records.append((relative, "file", mode, digest))
            else:
                records.append((relative, "special", mode))
        return tuple(records)

    def test_current_development_repository_passes(self) -> None:
        result = self.run_checker(REPOSITORY_ROOT)
        self.assertEqual(result.returncode, 0, result)
        self.assertIn("PASS APG skill library", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_default_root_is_the_command_repository(self) -> None:
        result = self.run_checker(None)
        self.assertEqual(result.returncode, 0, result)
        self.assertIn(
            "19 canonical skills, 19 catalog rows, 19 projections", result.stdout
        )

    def test_public_v010_library_passes_when_supplied(self) -> None:
        value = os.environ.get("APG11_PUBLIC_V01_ROOT")
        if value is None:
            self.skipTest("APG11_PUBLIC_V01_ROOT is phase dogfood evidence")
        result = self.run_checker(Path(value))
        self.assertEqual(result.returncode, 0, result)

    def test_text_output_success(self) -> None:
        result = self.run_checker(self.root)
        self.assertEqual(
            result.stdout,
            "PASS APG skill library: 2 canonical skills, 2 catalog rows, "
            "2 projections\n",
        )

    def test_json_output_is_deterministic(self) -> None:
        first = self.run_checker(self.root, "--format", "json")
        second = self.run_checker(self.root, "--format", "json")
        self.assertEqual(first.returncode, 0, first)
        self.assertEqual(first.stdout, second.stdout)
        payload = json.loads(first.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "pass")
        self.assertNotIn(str(self.root), first.stdout)

    def test_missing_skills_readme(self) -> None:
        (self.root / "skills" / "README.md").unlink()
        self.assertIn("APG002", self.result_codes())

    def test_missing_canonical_skill_file(self) -> None:
        (self.root / "skills" / "alpha-skill" / "SKILL.md").unlink()
        self.assertIn("APG005", self.result_codes())

    def test_canonical_skill_directory_symlink(self) -> None:
        leaf = self.root / "skills" / "alpha-skill"
        moved = self.root / "alpha-real"
        leaf.rename(moved)
        leaf.symlink_to(moved, target_is_directory=True)
        self.assertIn("APG004", self.result_codes())

    def test_unterminated_frontmatter(self) -> None:
        path = self.root / "skills" / "alpha-skill" / "SKILL.md"
        path.write_text("---\nname: alpha-skill\n", encoding="utf-8")
        self.assertIn("APG008", self.result_codes())

    def test_frontmatter_must_begin_at_byte_one(self) -> None:
        path = self.root / "skills" / "alpha-skill" / "SKILL.md"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        self.assertIn("APG007", self.result_codes())

    def test_optional_frontmatter_is_not_scanned_as_markdown(self) -> None:
        self.replace_skill(
            "alpha-skill",
            "description: Use when alpha-skill is required.\n",
            "description: Use when alpha-skill is required.\n"
            "# optional YAML comment\n"
            "example: '[escape](../beta-skill/SKILL.md)'\n",
        )
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 0, result)

    def test_frontmatter_fence_like_text_does_not_hide_markdown_body(self) -> None:
        self.replace_skill(
            "alpha-skill",
            "description: Use when alpha-skill is required.\n",
            "description: Use when alpha-skill is required.\n"
            "example: |\n"
            "  ```\n",
        )
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 0, result)

    def test_missing_required_name(self) -> None:
        self.replace_skill("alpha-skill", "name: alpha-skill\n", "")
        self.assertIn("APG009", self.result_codes())

    def test_missing_required_description(self) -> None:
        self.replace_skill(
            "alpha-skill", "description: Use when alpha-skill is required.\n", ""
        )
        self.assertIn("APG009", self.result_codes())

    def test_duplicate_required_frontmatter_key(self) -> None:
        self.replace_skill(
            "alpha-skill",
            "name: alpha-skill\n",
            "name: alpha-skill\nname: alpha-skill\n",
        )
        self.assertIn("APG009", self.result_codes())

    def test_ambiguous_top_level_required_key_is_bounded_noncompliance(self) -> None:
        self.replace_skill(
            "alpha-skill",
            "name: alpha-skill\n",
            'name: alpha-skill\n"name": other-skill\n',
        )
        text_result = self.run_checker(self.root)
        first_json = self.run_checker(self.root, "--format", "json")
        second_json = self.run_checker(self.root, "--format", "json")
        self.assertEqual(text_result.returncode, 1, text_result)
        self.assertEqual(first_json.returncode, 1, first_json)
        self.assertEqual(first_json.stdout, second_json.stdout)
        self.assertEqual(text_result.stderr, "")
        self.assertEqual(first_json.stderr, "")
        self.assertIn("APG035", text_result.stdout)
        self.assertIn(
            "APG035",
            {item["code"] for item in json.loads(first_json.stdout)["diagnostics"]},
        )
        self.assertNotIn(str(self.root), text_result.stdout)
        self.assertNotIn(str(self.root), first_json.stdout)

    def test_required_frontmatter_scalar_subset(self) -> None:
        self.replace_skill(
            "alpha-skill", "name: alpha-skill", 'name: "alpha-skill"'
        )
        self.assertIn("APG010", self.result_codes())

    def test_name_directory_mismatch(self) -> None:
        self.replace_skill("alpha-skill", "name: alpha-skill", "name: other-skill")
        self.assertIn("APG012", self.result_codes())

    def test_duplicate_skill_name(self) -> None:
        self.replace_skill("beta-skill", "name: beta-skill", "name: alpha-skill")
        self.assertIn("APG013", self.result_codes())

    def test_invalid_skill_name_grammar(self) -> None:
        self.replace_skill("alpha-skill", "name: alpha-skill", "name: Alpha")
        self.assertIn("APG011", self.result_codes())

    def test_description_must_be_trigger_oriented(self) -> None:
        self.replace_skill(
            "alpha-skill",
            "description: Use when alpha-skill is required.",
            "description: Alpha is useful.",
        )
        self.assertIn("APG014", self.result_codes())

    def test_description_length_boundary(self) -> None:
        accepted = "Use when " + ("a" * (1024 - len("Use when ")))
        self.replace_skill(
            "alpha-skill",
            "description: Use when alpha-skill is required.",
            f"description: {accepted}",
        )
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 0, result)

        rejected_root = self.base / "description-too-long"
        self.create_valid_library(rejected_root, self.names)
        path = rejected_root / "skills" / "alpha-skill" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        rejected = accepted + "a"
        path.write_text(
            text.replace(
                "description: Use when alpha-skill is required.",
                f"description: {rejected}",
                1,
            ),
            encoding="utf-8",
        )
        self.assertIn("APG014", self.result_codes(rejected_root))

    def test_semantically_poor_but_mechanically_valid_prose_passes(self) -> None:
        path = self.root / "skills" / "alpha-skill" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(
                "description: Use when alpha-skill is required.",
                "description: Use when anything happens.",
            ).replace("Evidence for core principle.", "Do whatever seems useful."),
            encoding="utf-8",
        )
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 0, result)

    def test_missing_required_section(self) -> None:
        self.replace_skill("alpha-skill", "## Procedure", "## Different")
        self.assertIn("APG016", self.result_codes())

    def test_duplicate_required_section(self) -> None:
        path = self.root / "skills" / "alpha-skill" / "SKILL.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n## Procedure\n\nAgain.\n",
            encoding="utf-8",
        )
        self.assertIn("APG016", self.result_codes())

    def test_fenced_required_section_does_not_count(self) -> None:
        self.replace_skill(
            "alpha-skill", "## Procedure", "```markdown\n## Procedure\n```"
        )
        self.assertIn("APG016", self.result_codes())

    def test_fence_like_content_does_not_expose_required_section(self) -> None:
        self.replace_skill(
            "alpha-skill",
            "## Procedure",
            "```markdown\n```python\n## Procedure\n```\n```",
        )
        self.assertIn("APG016", self.result_codes())

    def test_empty_optional_support_directory(self) -> None:
        (self.root / "skills" / "alpha-skill" / "references").mkdir()
        self.assertIn("APG019", self.result_codes())

    def test_agents_metadata_directory_is_accepted(self) -> None:
        agents = self.root / "skills" / "alpha-skill" / "agents"
        agents.mkdir()
        (agents / "openai.yaml").write_text("interface: test\n", encoding="utf-8")
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 0, result)

    def test_unsupported_skill_top_level_entry(self) -> None:
        (self.root / "skills" / "alpha-skill" / "notes.txt").write_text("x")
        self.assertIn("APG017", self.result_codes())

    def test_nested_support_symlink_must_remain_contained(self) -> None:
        support = self.root / "skills" / "alpha-skill" / "references"
        support.mkdir()
        (support / "escape").symlink_to(self.root / "skills" / "beta-skill")
        self.assertIn("APG020", self.result_codes())

    def test_contained_markdown_symlink_still_checks_local_links(self) -> None:
        support = self.root / "skills" / "alpha-skill" / "references"
        support.mkdir()
        (support / "payload.txt").write_text(
            "[escape](../../beta-skill/SKILL.md)\n", encoding="utf-8"
        )
        (support / "guide.md").symlink_to("payload.txt")
        self.assertIn("APG021", self.result_codes())

    def test_escaping_skill_local_link(self) -> None:
        path = self.root / "skills" / "alpha-skill" / "SKILL.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n[escape](../beta-skill/SKILL.md)\n",
            encoding="utf-8",
        )
        self.assertIn("APG021", self.result_codes())

    def test_missing_skill_local_link(self) -> None:
        path = self.root / "skills" / "alpha-skill" / "SKILL.md"
        path.write_text(
            path.read_text(encoding="utf-8") + "\n[missing](references/no.md)\n",
            encoding="utf-8",
        )
        self.assertIn("APG021", self.result_codes())

    def test_valid_skill_local_link_and_fragment(self) -> None:
        support = self.root / "skills" / "alpha-skill" / "references"
        support.mkdir()
        (support / "guide.md").write_text("# Guide\n", encoding="utf-8")
        path = self.root / "skills" / "alpha-skill" / "SKILL.md"
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n[guide](references/guide.md#section)\n",
            encoding="utf-8",
        )
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 0, result)

    def test_missing_catalog_row(self) -> None:
        readme = self.root / "skills" / "README.md"
        line = (
            "| [`beta-skill`](beta-skill/SKILL.md) | Trigger for beta-skill | "
            "`provisional` |\n"
        )
        readme.write_text(readme.read_text().replace(line, ""), encoding="utf-8")
        self.assertIn("APG025", self.result_codes())

    def test_duplicate_catalog_row(self) -> None:
        readme = self.root / "skills" / "README.md"
        row = (
            "| [`alpha-skill`](alpha-skill/SKILL.md) | Trigger for alpha-skill | "
            "`provisional` |\n"
        )
        readme.write_text(readme.read_text() + row, encoding="utf-8")
        self.assertIn("APG024", self.result_codes())

    def test_unknown_catalog_skill(self) -> None:
        readme = self.root / "skills" / "README.md"
        text = readme.read_text(encoding="utf-8")
        text += (
            "| [`unknown-skill`](unknown-skill/SKILL.md) | Unknown | "
            "`provisional` |\n"
        )
        readme.write_text(text, encoding="utf-8")
        self.assertIn("APG025", self.result_codes())

    def test_invalid_maturity_vocabulary(self) -> None:
        readme = self.root / "skills" / "README.md"
        readme.write_text(
            readme.read_text().replace("`provisional`", "`production`", 1),
            encoding="utf-8",
        )
        self.assertIn("APG028", self.result_codes())

    def test_catalog_link_mismatch(self) -> None:
        readme = self.root / "skills" / "README.md"
        readme.write_text(
            readme.read_text().replace(
                "alpha-skill/SKILL.md", "beta-skill/SKILL.md", 1
            ),
            encoding="utf-8",
        )
        self.assertIn("APG026", self.result_codes())

    def test_catalog_rejects_an_extra_raw_column(self) -> None:
        readme = self.root / "skills" / "README.md"
        readme.write_text(
            readme.read_text().replace(
                "Trigger for alpha-skill | `provisional`",
                "Trigger for alpha-skill | Extra | `provisional`",
                1,
            ),
            encoding="utf-8",
        )
        self.assertIn("APG023", self.result_codes())

    def test_missing_checked_in_projection_root(self) -> None:
        for path in (self.root / ".agents" / "skills").iterdir():
            path.unlink()
        (self.root / ".agents" / "skills").rmdir()
        self.assertIn("APG029", self.result_codes())

    def test_projection_is_not_a_symlink(self) -> None:
        link = self.root / ".agents" / "skills" / "alpha-skill"
        link.unlink()
        link.mkdir()
        self.assertIn("APG031", self.result_codes())

    def test_projection_has_wrong_raw_target(self) -> None:
        link = self.root / ".agents" / "skills" / "alpha-skill"
        link.unlink()
        link.symlink_to(Path("../../skills/beta-skill"), target_is_directory=True)
        self.assertIn("APG032", self.result_codes())

    def test_projection_is_broken(self) -> None:
        link = self.root / ".agents" / "skills" / "alpha-skill"
        link.unlink()
        link.symlink_to(Path("../../skills/missing-skill"), target_is_directory=True)
        codes = self.result_codes()
        self.assertTrue({"APG032", "APG033"}.issubset(codes))

    def test_projection_escapes_repository(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text(skill_text("alpha-skill"))
        link = self.root / ".agents" / "skills" / "alpha-skill"
        link.unlink()
        link.symlink_to(outside, target_is_directory=True)
        self.assertIn("APG033", self.result_codes())

    def test_extra_projection_entry(self) -> None:
        extra = self.root / ".agents" / "skills" / "extra-skill"
        extra.symlink_to(Path("../../skills/alpha-skill"), target_is_directory=True)
        self.assertIn("APG030", self.result_codes())

    def test_root_path_containing_spaces(self) -> None:
        spaced = self.base / "root with spaces"
        self.create_valid_library(spaced, self.names)
        result = self.run_checker(spaced)
        self.assertEqual(result.returncode, 0, result)

    def test_usage_error_returns_two(self) -> None:
        result = self.run_checker(None, "--unknown-option")
        self.assertEqual(result.returncode, 2, result)
        self.assertEqual(result.stdout, "")

    def test_invalid_installed_command_layout_returns_two(self) -> None:
        installed = self.base / "invalid-install" / "bin"
        installed.mkdir(parents=True)
        command = installed / "apg-check-skill-library"
        shutil.copy2(COMMAND, command)
        command.chmod(0o755)
        result = subprocess.run(
            [str(command)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.base),
            env=os.environ.copy(),
        )
        self.assertEqual(result.returncode, 2, result)
        self.assertEqual(result.stdout, "")
        self.assertIn("installed APG command layout is invalid", result.stderr)

    def test_missing_installed_helper_returns_two_without_traceback(self) -> None:
        installed_root = self.base / "missing-helper"
        installed = installed_root / "bin"
        installed.mkdir(parents=True)
        (installed_root / "libexec").mkdir()
        command = installed / "apg-check-skill-library"
        shutil.copy2(COMMAND, command)
        command.chmod(0o755)
        result = subprocess.run(
            [str(command)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(self.base),
            env=os.environ.copy(),
        )
        self.assertEqual(result.returncode, 2, result)
        self.assertEqual(result.stdout, "")
        self.assertIn("installed APG command layout is invalid", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_noncompliance_returns_one(self) -> None:
        (self.root / "skills" / "README.md").unlink()
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 1, result)

    def test_command_does_not_mutate_checked_tree_or_command_repository(self) -> None:
        before_target = self.tree_fingerprint(self.root)
        before_command = self.tree_fingerprint(REPOSITORY_ROOT)
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 0, result)
        self.assertEqual(self.tree_fingerprint(self.root), before_target)
        self.assertEqual(self.tree_fingerprint(REPOSITORY_ROOT), before_command)

    def test_invalid_utf8_is_bounded_noncompliance(self) -> None:
        path = self.root / "skills" / "alpha-skill" / "SKILL.md"
        path.write_bytes(b"\xff\xfe")
        result = self.run_checker(self.root, "--format", "json")
        self.assertEqual(result.returncode, 1, result)
        self.assertIn("APG006", {d["code"] for d in json.loads(result.stdout)["diagnostics"]})
        self.assertEqual(result.stderr, "")

    def test_extra_skills_root_file_is_rejected(self) -> None:
        (self.root / "skills" / "notes.txt").write_text("unexpected\n")
        self.assertIn("APG003", self.result_codes())

    def test_text_diagnostic_paths_escape_control_characters(self) -> None:
        unexpected = self.root / "skills" / "bad\nname"
        unexpected.write_text("unexpected\n", encoding="utf-8")
        result = self.run_checker(self.root)
        self.assertEqual(result.returncode, 1, result)
        self.assertIn(r"skills/bad\nname", result.stdout)
        self.assertNotIn("skills/bad\nname", result.stdout)

    def test_symlinked_agents_ancestor_is_rejected(self) -> None:
        skills_projection = self.root / ".agents" / "skills"
        for entry in skills_projection.iterdir():
            entry.unlink()
        skills_projection.rmdir()
        (self.root / ".agents").rmdir()
        real_agents = self.root / "real-agents"
        self.create_projection_only(real_agents)
        (self.root / ".agents").symlink_to(real_agents, target_is_directory=True)
        self.assertIn("APG029", self.result_codes())

    def create_projection_only(self, agents: Path) -> None:
        projection = agents / "skills"
        projection.mkdir(parents=True)
        for name in self.names:
            (projection / name).symlink_to(
                Path("../../skills") / name, target_is_directory=True
            )

    def test_diagnostics_are_sorted_and_include_safe_actions(self) -> None:
        (self.root / "skills" / "README.md").unlink()
        (self.root / "skills" / "alpha-skill" / "SKILL.md").unlink()
        result = self.run_checker(self.root, "--format", "json")
        payload = json.loads(result.stdout)
        diagnostics = payload["diagnostics"]
        keys = [
            (item["path"], item["line"] or 0, item["code"])
            for item in diagnostics
        ]
        self.assertEqual(keys, sorted(keys))
        self.assertTrue(all(item["action"] for item in diagnostics))
        self.assertNotIn(str(self.root), result.stdout)


if __name__ == "__main__":
    unittest.main()
