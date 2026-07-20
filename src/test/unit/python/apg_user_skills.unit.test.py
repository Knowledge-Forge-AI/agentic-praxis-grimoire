#!/usr/bin/env python3
"""Focused unit tests for APG user-skill state and source identities."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_user_skills as user_skills  # noqa: E402


class APGUserSkillsUnitTests(unittest.TestCase):
    def identity(self, path: str = "/public") -> user_skills.SourceIdentity:
        return user_skills.SourceIdentity(
            path,
            "0.2.0",
            "v0.2.0",
            "a" * 40,
            "b" * 40,
            tuple((name, "c" * 64) for name in user_skills.SKILLS),
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

    def test_parse_source_rejects_wrong_skill_hash_set(self) -> None:
        value = self.identity().as_dict()
        value["skill_hashes"] = {user_skills.SKILLS[0]: "c" * 64}
        with self.assertRaises(user_skills.ToolError):
            user_skills.parse_source(value)

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
