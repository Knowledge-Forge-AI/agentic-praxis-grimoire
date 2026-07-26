#!/usr/bin/env python3
"""Variable public-source set transitions for apg-user-skills."""

from __future__ import annotations

from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest


EXISTING_TEST = Path(__file__).parent.parent / "bin" / "apg-user-skills.int.test.py"
SPEC = importlib.util.spec_from_file_location("apg_user_skills_existing", EXISTING_TEST)
assert SPEC is not None and SPEC.loader is not None
EXISTING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXISTING)

import apg_user_skills as user_skills

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


@contextmanager
def temporary_environment(**values: str | None):
    original = {name: os.environ.get(name) for name in values}
    try:
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in original.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def valid_source_value(root: Path) -> dict[str, object]:
    return {
        "commit": "a" * 40,
        "path": str(root),
        "skill_hashes": {"example-skill": "b" * 64},
        "tag": "v0.4.0",
        "tree": "c" * 40,
        "version": "0.4.0",
    }


class APGUserSkillBoundaryTests(unittest.TestCase):
    """Exercise user-state and mutation-root contracts on real paths."""

    def test_environment_roots_require_absolute_values(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-user-root-") as raw:
            root = Path(raw).resolve()
            with temporary_environment(HOME=str(root), XDG_STATE_HOME=None):
                self.assertEqual(
                    user_skills.state_root(),
                    root / ".local/state/agentic-praxis-grimoire",
                )
                self.assertEqual(
                    user_skills.default_skills_root(), root / ".agents/skills"
                )
                self.assertEqual(
                    user_skills.absolute_root(None), root / ".agents/skills"
                )
            with temporary_environment(HOME=str(root), XDG_STATE_HOME=str(root / "state")):
                self.assertEqual(
                    user_skills.state_root(), root / "state/agentic-praxis-grimoire"
                )
            for home, state, call in (
                (None, None, user_skills.state_root),
                ("relative", None, user_skills.default_skills_root),
                (str(root), "relative", user_skills.state_root),
            ):
                with self.subTest(home=home, state=state, call=call.__name__):
                    with temporary_environment(HOME=home, XDG_STATE_HOME=state):
                        with self.assertRaises(user_skills.ToolError):
                            call()
            with self.assertRaisesRegex(user_skills.ToolError, "skills root must be absolute"):
                user_skills.absolute_root("relative")

    def test_git_environment_and_real_frontmatter_files_fail_closed(self) -> None:
        with temporary_environment(
            GIT_DIR="foreign",
            GIT_CONFIG_KEY_0="credential.helper",
            GIT_CONFIG_VALUE_0="foreign",
        ):
            environment = user_skills.git_environment()
        self.assertNotIn("GIT_DIR", environment)
        self.assertNotIn("GIT_CONFIG_KEY_0", environment)
        self.assertEqual(environment["GIT_OPTIONAL_LOCKS"], "0")

        with tempfile.TemporaryDirectory(prefix="apg-user-frontmatter-") as raw:
            leaf = Path(raw) / "example-skill"
            leaf.mkdir()
            skill_file = leaf / "SKILL.md"
            for content, message in (
                (b"", "frontmatter is malformed"),
                (b"---\nname: example-skill\n", "unterminated"),
                (b"---\nname: other-skill\n---\n", "mismatched"),
                (b"\xff", "unreadable"),
            ):
                skill_file.write_bytes(content)
                with self.subTest(message=message):
                    with self.assertRaisesRegex(user_skills.ToolError, message):
                        user_skills.frontmatter_name(skill_file)
            skill_file.write_text(
                "---\nname: example-skill\n---\n",
                encoding="utf-8",
            )
            self.assertEqual(user_skills.frontmatter_name(skill_file), "example-skill")

    def test_path_overlap_and_physical_location_cover_missing_components(self) -> None:
        self.assertTrue(user_skills.paths_overlap(Path("/a"), Path("/a")))
        self.assertTrue(user_skills.paths_overlap(Path("/a"), Path("/a/b")))
        self.assertTrue(user_skills.paths_overlap(Path("/a/b"), Path("/a")))
        self.assertFalse(user_skills.paths_overlap(Path("/a"), Path("/b")))
        with tempfile.TemporaryDirectory(prefix="apg-user-physical-") as raw:
            root = Path(raw).resolve()
            self.assertEqual(
                user_skills.physical_location(root / "missing" / "leaf"),
                root / "missing" / "leaf",
            )
            broken = root / "broken"
            broken.symlink_to(root / "absent", target_is_directory=True)
            with self.assertRaisesRegex(user_skills.ToolError, "cannot be resolved"):
                user_skills.physical_location(broken / "leaf")

    def test_mutation_root_rejects_source_overlap_and_git_worktrees(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-user-mutation-") as raw:
            root = Path(raw).resolve()
            source_root = root / "source"
            source_root.mkdir()
            source = user_skills.SourceIdentity(
                str(source_root), "0.4.0", "v0.4.0", "a" * 40, "b" * 40,
                (("example-skill", "c" * 64),),
            )
            with self.assertRaisesRegex(user_skills.ToolError, "disjoint"):
                user_skills.reject_mutation_root(source_root / "skills", source)
            repository = root / "repository"
            repository.mkdir()
            result = user_skills.run_git(repository, ["init", "-q", "-b", "main"])
            self.assertEqual(result.returncode, 0)
            with self.assertRaisesRegex(user_skills.ToolError, "Git worktree"):
                user_skills.reject_mutation_root(repository / "skills")
            user_skills.reject_mutation_root(root / "independent" / "skills", source)

    def test_existing_ancestor_validation_rejects_files_and_symlinks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-user-ancestor-") as raw:
            root = Path(raw).resolve()
            user_skills.verify_existing_ancestors(root / "missing" / "leaf")
            plain = root / "plain"
            plain.write_text("file\n")
            with self.assertRaisesRegex(user_skills.ToolError, "non-directory ancestor"):
                user_skills.verify_existing_ancestors(plain / "leaf")
            target = root / "target"
            target.mkdir()
            link = root / "link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(user_skills.ToolError, "symlinked"):
                user_skills.verify_existing_ancestors(link / "leaf")
            broken = root / "broken"
            broken.symlink_to(root / "absent", target_is_directory=True)
            with self.assertRaisesRegex(user_skills.ToolError, "broken symlink"):
                user_skills.verify_existing_ancestors(broken / "leaf")

    def test_source_and_container_state_parsers_reject_invalid_shapes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-user-state-") as raw:
            root = Path(raw).resolve()
            source = valid_source_value(root)
            parsed = user_skills.parse_source(source)
            self.assertEqual(parsed.skill_names, ("example-skill",))
            source_cases = []
            malformed = dict(source)
            malformed["extra"] = True
            source_cases.append(malformed)
            malformed = dict(source)
            malformed["commit"] = 1
            source_cases.append(malformed)
            malformed = dict(source)
            malformed["skill_hashes"] = {}
            source_cases.append(malformed)
            malformed = dict(source)
            malformed["skill_hashes"] = {"Bad Name": "b" * 64}
            source_cases.append(malformed)
            malformed = dict(source)
            malformed["skill_hashes"] = {"example-skill": "short"}
            source_cases.append(malformed)
            for value in source_cases:
                with self.subTest(value=value):
                    with self.assertRaisesRegex(user_skills.ToolError, "source"):
                        user_skills.parse_source(value)

            container = {
                "device": 1,
                "inode": 2,
                "mode": stat.S_IFDIR | 0o700,
                "owner": os.getuid(),
                "path": str(root),
            }
            self.assertEqual(user_skills.parse_container(container).path, str(root))
            container_cases = []
            malformed_container = dict(container)
            malformed_container["extra"] = 1
            container_cases.append(malformed_container)
            malformed_container = dict(container)
            malformed_container["path"] = "relative"
            container_cases.append(malformed_container)
            malformed_container = dict(container)
            malformed_container["inode"] = -1
            container_cases.append(malformed_container)
            malformed_container = dict(container)
            malformed_container["owner"] = True
            container_cases.append(malformed_container)
            for value in container_cases:
                with self.subTest(value=value):
                    with self.assertRaisesRegex(user_skills.ToolError, "created-container"):
                        user_skills.parse_container(value)

    def test_read_state_accepts_canonical_state_and_rejects_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-user-read-state-") as raw:
            root = Path(raw).resolve()
            state_path = root / "state.json"
            value = {
                "created_containers": [],
                "current_source": valid_source_value(root),
                "managed_skills": ["example-skill"],
                "previous_source": None,
                "schema_version": 1,
                "skills_root": str(root / "skills"),
            }
            self.assertIsNone(user_skills.read_state(state_path))
            state_path.write_text(json.dumps(value), encoding="utf-8")
            state_path.chmod(0o600)
            self.assertEqual(user_skills.read_state(state_path).managed_skills, ("example-skill",))

            cases: list[tuple[dict[str, object], str]] = []
            malformed = dict(value)
            malformed["extra"] = True
            cases.append((malformed, "schema"))
            malformed = dict(value)
            malformed["schema_version"] = True
            cases.append((malformed, "schema version"))
            malformed = dict(value)
            malformed["skills_root"] = "relative"
            cases.append((malformed, "skills root"))
            malformed = dict(value)
            malformed["skills_root"] = str(root / "skills/../skills")
            cases.append((malformed, "not canonical"))
            malformed = dict(value)
            malformed["managed_skills"] = []
            cases.append((malformed, "managed skill"))
            malformed = dict(value)
            malformed["created_containers"] = {}
            cases.append((malformed, "ownership"))
            for content, message in cases:
                with self.subTest(message=message):
                    state_path.write_text(json.dumps(content), encoding="utf-8")
                    with self.assertRaisesRegex(user_skills.ToolError, message):
                        user_skills.read_state(state_path)

            state_path.write_text("{}", encoding="utf-8")
            state_path.chmod(0o644)
            with self.assertRaisesRegex(user_skills.ToolError, "unsafe type"):
                user_skills.read_state(state_path)
            state_path.chmod(0o600)
            state_path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(user_skills.ToolError, "empty or oversized"):
                user_skills.read_state(state_path)
            state_path.write_text('{"duplicate":1,"duplicate":2}', encoding="utf-8")
            with self.assertRaisesRegex(user_skills.ToolError, "malformed"):
                user_skills.read_state(state_path)

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
        router_name = "agentic-praxis-grimoire-workflow"
        map_path = (
            path
            / "skills"
            / router_name
            / "references"
            / "capability-map.json"
        )
        map_path.parent.mkdir(parents=True, exist_ok=True)
        map_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "router_name": router_name,
                    "capabilities": [
                        {
                            "name": name,
                            "capability_class": f"fixture {name}",
                            "trigger": f"Use when fixture {name} applies.",
                        }
                        for name in V03_SKILLS
                        if name != router_name
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
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
