#!/usr/bin/env python3
"""Focused unit tests for APG user-skill state and source identities."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from src.test.apg_test_support import repository_root
from src.test.apg_user_skills_cases import APGUserSkillsCaseMixin
from unittest import mock


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_user_skills as user_skills  # noqa: E402


class APGUserSkillsUnitTests(APGUserSkillsCaseMixin, unittest.TestCase):
    def test_default_roots_follow_home_and_xdg(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            original = os.environ.copy()
            try:
                os.environ["HOME"] = str(Path(temporary) / "home")
                os.environ["XDG_STATE_HOME"] = str(Path(temporary) / "state")
                self.assertEqual(user_skills.default_skills_root(), Path(temporary) / "home" / ".agents" / "skills")
                self.assertEqual(user_skills.state_root(), Path(temporary) / "state" / "agentic-praxis-grimoire")
            finally:
                os.environ.clear()
                os.environ.update(original)

    def test_relative_skills_root_is_rejected(self) -> None:
        with self.assertRaises(user_skills.ToolError):
            user_skills.absolute_root("relative")

    def test_unique_json_object_rejects_duplicate_keys(self) -> None:
        with self.assertRaises(ValueError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=user_skills.unique_object)

    def test_restart_reminder_is_bounded_and_explicit(self) -> None:
        self.assertIn("normally detects", user_skills.RESTART_REMINDER)
        self.assertIn("fully restart Codex", user_skills.RESTART_REMINDER)

    def test_git_environment_removes_inherited_repository_configuration(self) -> None:
        with mock.patch.dict(
            user_skills.os.environ,
            {
                "GIT_DIR": "unsafe",
                "GIT_CONFIG_KEY_0": "unsafe",
                "GIT_CONFIG_VALUE_0": "unsafe",
                "KEEP": "yes",
            },
            clear=True,
        ):
            value = user_skills.git_environment()
        self.assertNotIn("GIT_DIR", value)
        self.assertNotIn("GIT_CONFIG_KEY_0", value)
        self.assertEqual(value["KEEP"], "yes")

    def test_frontmatter_name_accepts_exact_owner_and_rejects_malformed_forms(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "example-skill"
            leaf.mkdir()
            skill = leaf / "SKILL.md"
            skill.write_text("---\nname: example-skill\n---\n", encoding="utf-8")
            self.assertEqual(user_skills.frontmatter_name(skill), "example-skill")
            for content in (
                "name: example-skill\n",
                "---\nname: example-skill\n",
                "---\nname: other\n---\n",
                "---\nname: example-skill\nname: example-skill\n---\n",
            ):
                skill.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(user_skills.ToolError):
                    user_skills.frontmatter_name(skill)

    def test_policy_skill_names_rejects_missing_unsorted_and_malformed_arrays(self) -> None:
        valid = {
            "required_skills": ["skills/example/SKILL.md"],
            "required_projections": [".agents/skills/example"],
        }
        cases = (
            {},
            {**valid, "required_skills": []},
            {**valid, "required_skills": ["skills/z/SKILL.md", "skills/a/SKILL.md"]},
            {**valid, "required_skills": ["skills/INVALID/SKILL.md"]},
            {**valid, "required_projections": [1]},
        )
        for value in cases:
            with self.subTest(value=value), self.assertRaises(user_skills.ToolError):
                user_skills.policy_skill_names(value)

    def test_home_and_xdg_state_roots_fail_closed(self) -> None:
        for environment, message in (
            ({}, "HOME"),
            ({"HOME": "relative"}, "HOME"),
            ({"HOME": "/home", "XDG_STATE_HOME": "relative"}, "XDG_STATE_HOME"),
        ):
            with self.subTest(environment=environment):
                with mock.patch.dict(user_skills.os.environ, environment, clear=True):
                    with self.assertRaisesRegex(user_skills.ToolError, message):
                        user_skills.state_root()
        with mock.patch.dict(user_skills.os.environ, {}, clear=True):
            with self.assertRaisesRegex(user_skills.ToolError, "HOME"):
                user_skills.default_skills_root()

    def test_path_overlap_covers_equal_parent_child_and_disjoint_cases(self) -> None:
        root = Path("/root")
        child = root / "child"
        self.assertTrue(user_skills.paths_overlap(root, root))
        self.assertTrue(user_skills.paths_overlap(root, child))
        self.assertTrue(user_skills.paths_overlap(child, root))
        self.assertFalse(user_skills.paths_overlap(root, Path("/other")))

    def test_parse_source_and_container_reject_type_digest_and_metadata_failures(self) -> None:
        source = self.identity().as_dict()
        for mutation in (
            {**source, "commit": 1},
            {**source, "skill_hashes": []},
            {**source, "skill_hashes": {"valid-name": "bad"}},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(user_skills.ToolError):
                user_skills.parse_source(mutation)
        valid = {"device": 1, "inode": 2, "mode": 0o755, "owner": 3, "path": "/root"}
        self.assertEqual(user_skills.parse_container(valid).path, "/root")
        for mutation in (
            {},
            {**valid, "path": "relative"},
            {**valid, "device": True},
            {**valid, "inode": -1},
        ):
            with self.subTest(mutation=mutation), self.assertRaises(user_skills.ToolError):
                user_skills.parse_container(mutation)

    def test_read_state_rejects_storage_schema_and_ownership_failures(self) -> None:
        base = json.loads(user_skills.serialize_state(self.state()))
        cases: list[dict[str, object]] = []
        value = dict(base)
        value["schema_version"] = True
        cases.append(value)
        value = dict(base)
        value["skills_root"] = "relative"
        cases.append(value)
        value = dict(base)
        value["skills_root"] = "/user/../user/.agents/skills"
        cases.append(value)
        value = dict(base)
        value["managed_skills"] = []
        cases.append(value)
        value = dict(base)
        value["created_containers"] = "invalid"
        cases.append(value)
        value = dict(base)
        value["created_containers"] = list(reversed(value["created_containers"]))
        cases.append(value)
        value = dict(base)
        value["created_containers"] = [
            {"device": 1, "inode": 2, "mode": 0o755, "owner": 3, "path": "/outside"}
        ]
        cases.append(value)

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            self.assertIsNone(user_skills.read_state(path))
            for value in cases:
                path.write_text(json.dumps(value), encoding="utf-8")
                path.chmod(0o600)
                with self.subTest(value=value), self.assertRaises(user_skills.ToolError):
                    user_skills.read_state(path)
            path.write_text("{", encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaisesRegex(user_skills.ToolError, "malformed"):
                user_skills.read_state(path)
            path.write_text("", encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaisesRegex(user_skills.ToolError, "empty or oversized"):
                user_skills.read_state(path)
            path.write_text("{}", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaisesRegex(user_skills.ToolError, "unsafe type"):
                user_skills.read_state(path)

    def test_exact_links_accepts_exact_links_and_rejects_missing_or_nonlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "source"
            links = base / "links"
            links.mkdir()
            source = self.identity(str(source_root), names=("example",))
            leaf = source_root / "skills" / "example"
            leaf.mkdir(parents=True)
            link = links / "example"
            link.symlink_to(leaf)
            user_skills.exact_links(links, source)
            link.unlink()
            with self.assertRaisesRegex(user_skills.ToolError, "missing"):
                user_skills.exact_links(links, source)
            link.write_text("conflict", encoding="utf-8")
            with self.assertRaisesRegex(user_skills.ToolError, "not a symbolic link"):
                user_skills.exact_links(links, source)

    def test_physical_location_and_mutation_root_reject_source_and_git_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            missing = base / "future" / "skills"
            self.assertEqual(user_skills.physical_location(missing), missing)
            source = self.identity(str(base / "source"))
            (base / "source").mkdir()
            with self.assertRaisesRegex(user_skills.ToolError, "disjoint"):
                user_skills.reject_mutation_root(base / "source" / "skills", source)
            result = mock.Mock(returncode=0, stdout=(str(base) + "\n").encode())
            with mock.patch.object(user_skills, "run_git", return_value=result):
                with self.assertRaisesRegex(user_skills.ToolError, "Git worktree"):
                    user_skills.reject_mutation_root(base / "managed")

    def test_state_directory_and_lock_contexts_enforce_private_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            home.mkdir()
            with mock.patch.dict(user_skills.os.environ, {"HOME": str(home)}, clear=True):
                directory = user_skills.ensure_state_directory()
                self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                with user_skills.state_lock() as (state_path, lock_path):
                    self.assertEqual(state_path.parent, directory)
                    state_path.write_bytes(user_skills.serialize_state(self.state()))
                    state_path.chmod(0o600)
                    self.assertTrue(lock_path.exists())
                with user_skills.read_only_state_lock() as (state_path, lock_path):
                    self.assertTrue(state_path.exists() and lock_path.exists())

    def test_atomic_state_source_match_and_container_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state_path = base / "state.json"
            state = self.state()
            user_skills.atomic_state_write(state_path, state)
            self.assertEqual(user_skills.read_state(state_path), state)
            with mock.patch.object(user_skills, "verify_source", return_value=state.current_source):
                self.assertEqual(user_skills.source_matches(state.current_source), state.current_source)
            with mock.patch.object(user_skills, "verify_source", return_value=self.identity("/other")):
                with self.assertRaisesRegex(user_skills.ToolError, "identity has changed"):
                    user_skills.source_matches(state.current_source)

            root = base / "one" / "two"
            created = user_skills.create_containers(root)
            self.assertEqual([Path(item.path).name for item in created], ["one", "two"])
            self.assertTrue(root.is_dir())

    def test_link_creation_adoption_and_preflight_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "source"
            root = base / "links"
            root.mkdir()
            source = self.identity(str(source_root), names=("example",))
            (source_root / "skills" / "example").mkdir(parents=True)
            user_skills.preflight_absent(root, source.skill_names)
            user_skills.create_links(root, source)
            user_skills.verify_adoptable(root, source)
            with self.assertRaisesRegex(user_skills.ToolError, "conflicting"):
                user_skills.preflight_absent(root, source.skill_names)
            (root / "example").unlink()
            (root / "example").write_text("not a link")
            with self.assertRaisesRegex(user_skills.ToolError, "symbolic link"):
                user_skills.verify_adoptable(root, source)

    def test_repository_duplicate_detection_and_source_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scope = root / ".agents" / "skills" / "example"
            scope.mkdir(parents=True)
            (scope / "SKILL.md").write_text("---\nname: example\n---\n")
            result = mock.Mock(returncode=0, stdout=(str(root) + "\n").encode())
            with mock.patch.object(user_skills, "run_git", return_value=result):
                self.assertEqual(user_skills.repository_duplicates(str(root), ("example",)), ("example",))
            self.assertEqual(user_skills.repository_duplicates(None, ("example",)), ())
            identity = self.identity(names=("example",))
            self.assertEqual(user_skills.render_source(identity, "text"), "example\n")
            self.assertEqual(json.loads(user_skills.render_source(identity, "json"))["skills"], ["example"])

    def test_install_adopt_check_and_update_orchestration_contracts(self) -> None:
        source = self.identity()
        root = Path("/user/.agents/skills")
        state_path = Path("/state.json")
        installed = self.state()
        with (
            mock.patch.object(user_skills, "read_state", return_value=installed),
            mock.patch.object(user_skills, "source_matches"),
            mock.patch.object(user_skills, "exact_links"),
        ):
            self.assertIn("already installed", user_skills.do_install(source, root, state_path))
            self.assertIn("already adopted", user_skills.do_adopt(source, root, state_path))
            rendered = user_skills.do_check(root, state_path, None, "json")
            self.assertEqual(json.loads(rendered)["status"], "pass")

        next_source = user_skills.SourceIdentity(
            "/next",
            "0.3.0",
            "v0.3.0",
            "d" * 40,
            "e" * 40,
            source.skill_hashes,
        )
        with (
            mock.patch.object(user_skills, "read_state", return_value=installed),
            mock.patch.object(user_skills, "source_matches"),
            mock.patch.object(user_skills, "replace_links") as replace,
            mock.patch.object(user_skills, "atomic_state_write") as write,
        ):
            self.assertIn("updated", user_skills.do_update(next_source, root, state_path))
            replace.assert_called_once()
            write.assert_called_once()

    def test_parser_and_main_route_success_and_bounded_tool_errors(self) -> None:
        identity = self.identity(names=("example",))
        with mock.patch.object(user_skills, "verify_source", return_value=identity):
            stdout = tempfile.TemporaryFile(mode="w+")
            with mock.patch.object(sys, "stdout", stdout):
                self.assertEqual(
                    user_skills.main(["list", "--source", "/source", "--format", "json"]),
                    0,
                )
        with mock.patch.object(user_skills, "verify_source", side_effect=user_skills.ToolError("bad source")):
            self.assertEqual(user_skills.main(["list", "--source", "/source"]), 1)

    def test_rollback_uses_recorded_source_and_writes_reversible_state(self) -> None:
        current = self.identity("/current")
        previous = user_skills.SourceIdentity(
            "/previous", "0.1.0", "v0.1.0", "d" * 40, "e" * 40, current.skill_hashes
        )
        state = user_skills.State(
            "/user/.agents/skills", current, previous, current.skill_names, ()
        )
        with (
            mock.patch.object(user_skills, "read_state", return_value=state),
            mock.patch.object(user_skills, "source_matches", side_effect=lambda source: source),
            mock.patch.object(user_skills, "replace_links") as replace,
            mock.patch.object(user_skills, "atomic_state_write") as write,
        ):
            self.assertIn(
                "rolled back",
                user_skills.do_rollback(None, Path(state.skills_root), Path("/state")),
            )
        replace.assert_called_once_with(Path(state.skills_root), current, previous)
        self.assertEqual(write.call_args.args[1].previous_source, current)

    def test_uninstall_success_removes_only_state_owned_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "source"
            root = base / "skills"
            root.mkdir()
            source = self.identity(str(source_root), names=("example",))
            leaf = source_root / "skills" / "example"
            leaf.mkdir(parents=True)
            (root / "example").symlink_to(leaf)
            state_path = base / "state.json"
            state_path.write_text("owned")
            state = user_skills.State(str(root), source, None, source.skill_names, ())
            with (
                mock.patch.object(user_skills, "read_state", return_value=state),
                mock.patch.object(user_skills, "source_matches"),
                mock.patch.object(user_skills, "exact_links"),
            ):
                self.assertIn("uninstalled 1", user_skills.do_uninstall(root, state_path))
            self.assertFalse(state_path.exists())
            self.assertFalse((root / "example").exists())

    def test_update_and_rollback_reject_missing_or_ambiguous_history(self) -> None:
        with mock.patch.object(user_skills, "read_state", return_value=None):
            with self.assertRaisesRegex(user_skills.ToolError, "install or adopt"):
                user_skills.do_update(self.identity(), Path("/root"), Path("/state"))
            with self.assertRaisesRegex(user_skills.ToolError, "no previous"):
                user_skills.do_rollback(None, Path("/root"), Path("/state"))

    def test_verified_public_source_returns_exact_committed_skill_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            committed: dict[str, bytes] = {}
            for name in user_skills.SKILLS:
                leaf = root / "skills" / name
                leaf.mkdir(parents=True)
                content = f"---\nname: {name}\n---\n".encode()
                (leaf / "SKILL.md").write_bytes(content)
                committed[name] = content

            def git(_root: Path, arguments: list[str], **kwargs: object) -> mock.Mock:
                del kwargs
                if arguments == ["rev-parse", "--show-toplevel"]:
                    return mock.Mock(returncode=0, stdout=(str(root) + "\n").encode())
                if arguments[0] in {"status", "ls-files"}:
                    return mock.Mock(returncode=0, stdout=b"")
                if arguments[0] == "show":
                    name = arguments[1].split("/", 1)[1].removesuffix("/SKILL.md")
                    return mock.Mock(returncode=0, stdout=committed[name])
                raise AssertionError(arguments)

            lineage = (
                user_skills.public_release.ReleaseIdentity(
                    "0.1.0",
                    "v0.1.0",
                    user_skills.PUBLIC_V01_COMMIT,
                    user_skills.PUBLIC_V01_TREE,
                ),
            )
            valid_library = mock.Mock(passed=True, diagnostics=())
            with (
                mock.patch.object(user_skills, "run_git", side_effect=git),
                mock.patch.object(
                    user_skills,
                    "text_git",
                    side_effect=(user_skills.PUBLIC_V01_COMMIT, user_skills.PUBLIC_V01_TREE),
                ),
                mock.patch.object(
                    user_skills.public_release,
                    "resolve_repository",
                    return_value=mock.Mock(),
                ),
                mock.patch.object(
                    user_skills.public_release,
                    "verify_public_release_lineage",
                    return_value=lineage,
                ),
                mock.patch.object(user_skills, "check_library", return_value=valid_library),
            ):
                identity = user_skills.verify_source(root)
        self.assertEqual(identity.commit, user_skills.PUBLIC_V01_COMMIT)
        self.assertEqual(identity.skill_names, user_skills.SKILLS)
        self.assertTrue(all(len(digest) == 64 for _name, digest in identity.skill_hashes))


if __name__ == "__main__":
    unittest.main()
