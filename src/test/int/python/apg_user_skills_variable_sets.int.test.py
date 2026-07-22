#!/usr/bin/env python3
"""Variable public-source set transitions for apg-user-skills."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import unittest


EXISTING_TEST = Path(__file__).with_name("apg_user_skills.int.test.py")
SPEC = importlib.util.spec_from_file_location("apg_user_skills_existing", EXISTING_TEST)
assert SPEC is not None and SPEC.loader is not None
EXISTING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXISTING)

V03_ADDITIONS = (
    "agentic-praxis-grimoire-workflow",
    "bash-language-profile",
    "bats-test-profile",
    "composing-approved-roadmap-assignments",
    "go-language-profile",
    "nix-language-profile",
    "postgresql-database-profile",
    "python-language-profile",
    "ruby-language-profile",
    "sqlite-database-profile",
    "synthesizing-repository-guidance",
    "zsh-language-profile",
    "zunit-test-profile",
)
V03_SKILLS = tuple(sorted((*EXISTING.SKILLS, *V03_ADDITIONS)))


class APGUserSkillVariableSetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = EXISTING.APGUserSkillsTests(methodName="runTest")
        self.fixture.setUp()
        self.v03 = self.make_v03_release()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def make_v03_release(self) -> Path:
        path = self.fixture.root / "public-v0.3.0"
        shutil.copytree(self.fixture.second, path, symlinks=True)
        sections = "\n\n".join(
            f"## {heading}\n\nFixture for {heading.lower()}."
            for heading in EXISTING.REQUIRED_H2S
        )
        for name in V03_ADDITIONS:
            leaf = path / "skills" / name
            leaf.mkdir(parents=True, exist_ok=True)
            (leaf / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Use when v0.3 {name} applies.\n---\n\n"
                f"# {name}\n\n{sections}\n"
            )
            projection = path / ".agents" / "skills" / name
            if not os.path.lexists(projection):
                projection.symlink_to(f"../../skills/{name}", target_is_directory=True)
        rows = "\n".join(
            f"| [`{name}`]({name}/SKILL.md) | Use when v0.3 {name} applies | `provisional` |"
            for name in V03_SKILLS
        )
        (path / "skills" / "README.md").write_text(
            "# APG Skill Library\n\n## Current development catalog\n\n"
            "| Skill | Trigger boundary | Maturity |\n"
            "| --- | --- | --- |\n"
            f"{rows}\n"
        )
        policy_path = path / "release" / "public-surface.json"
        policy = json.loads(policy_path.read_text())
        for key, values in EXISTING.public_release.audited_policy_surfaces("0.3.0")[0].items():
            policy[key] = list(values)
        policy["required_skills"] = [f"skills/{name}/SKILL.md" for name in V03_SKILLS]
        policy["required_projections"] = [f".agents/skills/{name}" for name in V03_SKILLS]
        policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n")
        for key in (
            "critical_files",
            "required_helpers",
            "required_licensing_files",
            "required_test_entrypoints",
            "required_wrappers",
        ):
            for public_path in policy[key]:
                target = path / public_path
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("# Fixture public owner\n")
        self.fixture.git(path, "add", "-A")
        self.fixture.git(path, "commit", "-q", "-m", "Release v0.3.0")
        self.fixture.git(path, "tag", "-a", "v0.3.0", "-m", "Release v0.3.0")
        return path

    def assert_success(self, result: object) -> None:
        self.fixture.assert_success(result)

    def test_list_and_atomic_six_to_nineteen_to_six_transition(self) -> None:
        listed = self.fixture.invoke("list", "--format", "json", source=self.v03)
        self.assert_success(listed)
        self.assertEqual(tuple(json.loads(listed.stdout)["skills"]), V03_SKILLS)
        self.assert_success(self.fixture.invoke("install", source=self.fixture.second))
        unrelated = self.fixture.skills_root / "unrelated-skill"
        unrelated.mkdir()
        self.assert_success(self.fixture.invoke("update", source=self.v03))
        self.assertEqual(self.fixture.state()["managed_skills"], list(V03_SKILLS))
        for name in V03_SKILLS:
            self.assertEqual(
                (self.fixture.skills_root / name).resolve(),
                (self.v03 / "skills" / name).resolve(),
            )
        self.assert_success(self.fixture.invoke("rollback"))
        self.assertEqual(self.fixture.state()["managed_skills"], list(EXISTING.SKILLS))
        for name in EXISTING.SKILLS:
            self.assertEqual(
                (self.fixture.skills_root / name).resolve(),
                (self.fixture.second / "skills" / name).resolve(),
            )
        for name in V03_ADDITIONS:
            self.assertFalse(os.path.lexists(self.fixture.skills_root / name))
        self.assertTrue(unrelated.is_dir())
        self.assert_success(self.fixture.invoke("update", source=self.v03))
        self.assert_success(self.fixture.invoke("uninstall"))
        for name in V03_SKILLS:
            self.assertFalse(os.path.lexists(self.fixture.skills_root / name))
        self.assertTrue(unrelated.is_dir())

    def test_added_name_conflict_refuses_without_link_or_state_drift(self) -> None:
        self.assert_success(self.fixture.invoke("install", source=self.fixture.second))
        conflict = self.fixture.skills_root / V03_ADDITIONS[0]
        conflict.write_text("preserve\n")
        before_state = self.fixture.state_path.read_bytes()
        before_links = {
            name: os.readlink(self.fixture.skills_root / name)
            for name in EXISTING.SKILLS
        }
        result = self.fixture.invoke("update", source=self.v03)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.fixture.state_path.read_bytes(), before_state)
        self.assertEqual(
            {
                name: os.readlink(self.fixture.skills_root / name)
                for name in EXISTING.SKILLS
            },
            before_links,
        )
        self.assertEqual(conflict.read_text(), "preserve\n")

    def test_policy_catalog_projection_disagreement_is_rejected(self) -> None:
        source = self.fixture.root / "public-v0.4.0-mismatch"
        shutil.copytree(self.v03, source, symlinks=True)
        policy_path = source / "release" / "public-surface.json"
        policy = json.loads(policy_path.read_text())
        policy["required_projections"] = policy["required_projections"][:-1]
        policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n")
        self.fixture.git(source, "add", "-A")
        self.fixture.git(source, "commit", "-q", "-m", "Release v0.4.0")
        self.fixture.git(source, "tag", "-a", "v0.4.0", "-m", "Release v0.4.0")
        result = self.fixture.invoke("list", source=source)
        self.assertEqual(result.returncode, 1)
        self.assertIn("policy", result.stderr.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
