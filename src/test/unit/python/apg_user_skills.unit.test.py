#!/usr/bin/env python3
"""Focused unit tests for APG user-skill state and source identities."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_user_skills as user_skills  # noqa: E402


class APGUserSkillsUnitTests(unittest.TestCase):
    def identity(
        self,
        path: str = "/public",
        names: tuple[str, ...] = user_skills.SKILLS,
    ) -> user_skills.SourceIdentity:
        return user_skills.SourceIdentity(
            path,
            "0.2.0",
            "v0.2.0",
            "a" * 40,
            "b" * 40,
            tuple((name, "c" * 64) for name in names),
        )

    def state(self) -> user_skills.State:
        return user_skills.State(
            "/user/.agents/skills",
            self.identity(),
            None,
            user_skills.SKILLS,
            (
                user_skills.ContainerIdentity("/user/.agents", 1, 2, 3, 0o755),
                user_skills.ContainerIdentity("/user/.agents/skills", 1, 4, 3, 0o755),
            ),
        )

    def test_source_identity_serializes_canonical_fields(self) -> None:
        value = self.identity().as_dict()
        self.assertEqual(set(value), user_skills.SOURCE_KEYS)
        self.assertEqual(tuple(value["skill_hashes"]), user_skills.SKILLS)

    def test_state_serialization_is_sorted_newline_terminated_json(self) -> None:
        content = user_skills.serialize_state(self.state())
        self.assertTrue(content.endswith(b"\n"))
        value = json.loads(content)
        self.assertEqual(value["schema_version"], 1)
        self.assertEqual(value["managed_skills"], list(user_skills.SKILLS))

    def test_parse_source_rejects_unknown_and_missing_keys(self) -> None:
        value = self.identity().as_dict()
        for mutation in ({**value, "extra": True}, {key: member for key, member in value.items() if key != "tree"}):
            with self.assertRaises(user_skills.ToolError):
                user_skills.parse_source(mutation)

    def test_parse_source_accepts_source_specific_skill_hash_sets(self) -> None:
        value = self.identity().as_dict()
        value["skill_hashes"] = {
            **value["skill_hashes"],
            "additional-profile": "d" * 64,
        }
        parsed = user_skills.parse_source(value)
        self.assertEqual(
            tuple(name for name, _digest in parsed.skill_hashes),
            tuple(sorted(value["skill_hashes"])),
        )

    def test_parse_source_rejects_empty_or_invalid_skill_hash_sets(self) -> None:
        for hashes in ({}, {"Invalid Name": "c" * 64}):
            with self.subTest(hashes=hashes):
                value = self.identity().as_dict()
                value["skill_hashes"] = hashes
                with self.assertRaises(user_skills.ToolError):
                    user_skills.parse_source(value)

    def test_schema_v1_state_accepts_a_source_specific_managed_set(self) -> None:
        names = tuple(sorted((*user_skills.SKILLS, "additional-profile")))
        state = user_skills.State(
            "/user/.agents/skills",
            self.identity(names=names),
            self.identity("/previous", user_skills.SKILLS),
            names,
            (),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.json"
            path.write_bytes(user_skills.serialize_state(state))
            path.chmod(0o600)
            parsed = user_skills.read_state(path)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.managed_skills, names)
        self.assertEqual(parsed.previous_source.skill_names, user_skills.SKILLS)

    def test_policy_skill_and_projection_sets_must_agree(self) -> None:
        names = tuple(sorted((*user_skills.SKILLS, "additional-profile")))
        policy = {
            "required_skills": [f"skills/{name}/SKILL.md" for name in names],
            "required_projections": [f".agents/skills/{name}" for name in names],
        }
        self.assertEqual(user_skills.policy_skill_names(policy), names)
        policy["required_projections"].pop()
        with self.assertRaises(user_skills.ToolError):
            user_skills.policy_skill_names(policy)

    def test_variable_link_transition_restores_old_set_after_failure(self) -> None:
        old_names = user_skills.SKILLS
        new_names = tuple(sorted((*old_names, "additional-profile")))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            old_root = base / "old"
            new_root = base / "new"
            links = base / "links"
            links.mkdir()
            for source, names in ((old_root, old_names), (new_root, new_names)):
                for name in names:
                    (source / "skills" / name).mkdir(parents=True)
            for name in old_names:
                (links / name).symlink_to(old_root / "skills" / name)
            old = self.identity(str(old_root), old_names)
            new = self.identity(str(new_root), new_names)
            real_replace = user_skills.os.replace
            calls = 0

            def fail_once(source: Path, target: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("injected transition failure")
                real_replace(source, target)

            with mock.patch.object(user_skills.os, "replace", side_effect=fail_once):
                with self.assertRaises(user_skills.ToolError):
                    user_skills.replace_links(links, old, new)
            for name in old_names:
                self.assertEqual(
                    (links / name).resolve(),
                    (old_root / "skills" / name).resolve(),
                )
            self.assertFalse((links / "additional-profile").exists())

    def test_removal_transition_restores_old_set_after_failure(self) -> None:
        old_names = tuple(sorted((*user_skills.SKILLS, "additional-profile", "other-profile")))
        new_names = user_skills.SKILLS
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            old_root = base / "old"
            new_root = base / "new"
            links = base / "links"
            links.mkdir()
            for source, names in ((old_root, old_names), (new_root, new_names)):
                for name in names:
                    (source / "skills" / name).mkdir(parents=True)
            for name in old_names:
                (links / name).symlink_to(old_root / "skills" / name)
            old = self.identity(str(old_root), old_names)
            new = self.identity(str(new_root), new_names)
            real_unlink = Path.unlink
            failed = False

            def fail_once(path: Path, *args: object, **kwargs: object) -> None:
                nonlocal failed
                if path == links / "other-profile" and not failed:
                    failed = True
                    raise OSError("injected removal failure")
                real_unlink(path, *args, **kwargs)

            with mock.patch.object(Path, "unlink", autospec=True, side_effect=fail_once):
                with self.assertRaises(user_skills.ToolError):
                    user_skills.replace_links(links, old, new)
            for name in old_names:
                self.assertEqual(
                    (links / name).resolve(),
                    (old_root / "skills" / name).resolve(),
                )

    def test_uninstall_restores_links_when_state_deletion_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source_root = base / "source"
            links = base / "links"
            links.mkdir()
            source = self.identity(str(source_root))
            for name in source.skill_names:
                leaf = source_root / "skills" / name
                leaf.mkdir(parents=True)
                (links / name).symlink_to(leaf)
            state_path = base / "state.json"
            state_path.write_text("preserve state\n")
            state = user_skills.State(str(links), source, None, source.skill_names, ())
            real_unlink = Path.unlink

            def fail_state(path: Path, *args: object, **kwargs: object) -> None:
                if path == state_path:
                    raise OSError("injected state deletion failure")
                real_unlink(path, *args, **kwargs)

            with (
                mock.patch.object(user_skills, "read_state", return_value=state),
                mock.patch.object(user_skills, "source_matches"),
                mock.patch.object(Path, "unlink", autospec=True, side_effect=fail_state),
            ):
                with self.assertRaises(user_skills.ToolError):
                    user_skills.do_uninstall(links, state_path)
            self.assertTrue(state_path.exists())
            for name in source.skill_names:
                self.assertEqual(
                    (links / name).resolve(),
                    (source_root / "skills" / name).resolve(),
                )

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


if __name__ == "__main__":
    unittest.main()
