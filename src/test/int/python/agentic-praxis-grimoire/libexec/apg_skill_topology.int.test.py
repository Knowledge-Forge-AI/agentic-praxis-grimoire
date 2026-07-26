#!/usr/bin/env python3
"""Direct/nested topology transitions through the user-skills boundary."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock


USER_TEST = Path(__file__).with_name("apg_user_skills.int.test.py")
SPEC = importlib.util.spec_from_file_location("apg_user_skills_topology_base", USER_TEST)
assert SPEC is not None and SPEC.loader is not None
USER_CASES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(USER_CASES)

user_skills = USER_CASES.user_skills


class APGSkillTopologyIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = USER_CASES.APGUserSkillVariableSetTests(methodName="runTest")
        self.base.setUp()
        self.fixture = self.base.fixture
        self.v03 = self.base.v03

    def tearDown(self) -> None:
        self.base.tearDown()

    def assert_success(self, result: object) -> None:
        self.fixture.assert_success(result)

    def make_v04_nested_release(
        self,
        *,
        extra_skills: tuple[str, ...] = (),
    ) -> Path:
        path = self.fixture.root / "public-v0.4.0"
        shutil.copytree(self.v03, path, symlinks=True)
        policy_path = path / "release" / "public-surface.json"
        policy = json.loads(policy_path.read_text())
        current_surface = user_skills.public_release.audited_policy_surfaces(
            "0.4.0"
        )[0]
        for key, values in current_surface.items():
            policy[key] = list(values)
        policy_path.write_text(
            json.dumps(policy, indent=2, sort_keys=True) + "\n"
        )

        skill_paths = user_skills.policy_skill_paths(policy)
        manager_name = "composing-approved-roadmap-assignments"
        old_manager = path / "skills" / manager_name
        nested_manager = path / skill_paths[manager_name]
        nested_manager.parent.mkdir(parents=True, exist_ok=True)
        old_manager.rename(nested_manager)
        actual_skill_paths = dict(
            sorted(
                {
                    **skill_paths,
                    **{
                        name: Path("skills") / name
                        for name in extra_skills
                    },
                }.items()
            )
        )
        sections = "\n\n".join(
            f"## {heading}\n\nFixture for {heading.lower()}."
            for heading in USER_CASES.EXISTING.REQUIRED_H2S
        )
        for name, relative in actual_skill_paths.items():
            leaf = path / relative
            leaf.mkdir(parents=True, exist_ok=True)
            skill_file = leaf / "SKILL.md"
            if not skill_file.exists():
                skill_file.write_text(
                    f"---\nname: {name}\n"
                    f"description: Use when v0.4 {name} applies.\n---\n\n"
                    f"# {name}\n\n{sections}\n"
                )

        rows = "\n".join(
            f"| [`{name}`]({relative.relative_to('skills').as_posix()}/SKILL.md) "
            f"| Use when v0.4 {name} applies | `provisional` |"
            for name, relative in actual_skill_paths.items()
        )
        (path / "skills" / "README.md").write_text(
            "# APG Skill Library\n\n## Current development catalog\n\n"
            "| Skill | Trigger boundary | Maturity |\n"
            "| --- | --- | --- |\n"
            f"{rows}\n"
        )
        for name, relative in actual_skill_paths.items():
            projection = path / ".agents" / "skills" / name
            projection.unlink(missing_ok=True)
            projection.symlink_to(
                Path("../..") / relative,
                target_is_directory=True,
            )

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
        general_name = "agentic-praxis-grimoire-workflow"
        subrouter_name = "chatgpt-manager-workflow"
        write_maps = (
            (
                path
                / skill_paths[general_name]
                / "references"
                / "capability-map.json",
                general_name,
                tuple(
                    name
                    for name in actual_skill_paths
                    if name not in {general_name, manager_name}
                ),
            ),
            (
                path
                / skill_paths[subrouter_name]
                / "references"
                / "capability-map.json",
                subrouter_name,
                (manager_name,),
            ),
        )
        for map_path, router_name, capability_names in write_maps:
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
                            for name in capability_names
                        ],
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        self.fixture.git(path, "add", "-A")
        self.fixture.git(path, "commit", "-q", "-m", "Release v0.4.0")
        self.fixture.git(path, "tag", "-a", "v0.4.0", "-m", "Release v0.4.0")
        return path

    def test_nested_source_links_transition_to_and_from_historical_direct_paths(
        self,
    ) -> None:
        name = "composing-approved-roadmap-assignments"
        with tempfile.TemporaryDirectory(
            prefix="apg-user-nested-transition-"
        ) as raw:
            root = Path(raw)
            historical_root = root / "historical"
            current_root = root / "current"
            links = root / "links"
            historical_leaf = historical_root / "skills" / name
            current_leaf = current_root / "skills/chatgpt" / name
            historical_leaf.mkdir(parents=True)
            current_leaf.mkdir(parents=True)
            links.mkdir()
            (links / name).symlink_to(
                historical_leaf,
                target_is_directory=True,
            )
            historical = user_skills.SourceIdentity(
                str(historical_root),
                "0.3.0",
                "v0.3.0",
                "a" * 40,
                "b" * 40,
                ((name, "c" * 64),),
            )
            current = user_skills.SourceIdentity(
                str(current_root),
                "0.4.0",
                "v0.4.0",
                "d" * 40,
                "e" * 40,
                ((name, "f" * 64),),
            )
            policy = {
                "required_skills": [f"skills/chatgpt/{name}/SKILL.md"],
                "required_projections": [f".agents/skills/{name}"],
            }
            with mock.patch.object(
                user_skills.public_release,
                "load_policy",
                return_value=policy,
            ):
                user_skills.replace_links(links, historical, current)
                self.assertTrue(
                    (links / name).resolve().samefile(current_leaf)
                )
                self.assertEqual(os.readlink(links / name), str(current_leaf))
                user_skills.replace_links(links, current, historical)
                self.assertTrue(
                    (links / name).resolve().samefile(historical_leaf)
                )

    def test_command_state_transitions_between_direct_and_nested_sources(
        self,
    ) -> None:
        nested = self.make_v04_nested_release()
        manager_name = "composing-approved-roadmap-assignments"
        self.assert_success(self.fixture.invoke("install", source=self.v03))

        self.assert_success(self.fixture.invoke("update", source=nested))
        updated = self.fixture.state()
        self.assertEqual(updated["schema_version"], 1)
        self.assertEqual(updated["current_source"]["version"], "0.4.0")
        self.assertEqual(updated["previous_source"]["version"], "0.3.0")
        self.assertEqual(
            os.readlink(self.fixture.skills_root / manager_name),
            str(
                Path(updated["current_source"]["path"])
                / "skills/chatgpt"
                / manager_name
            ),
        )

        self.assert_success(self.fixture.invoke("rollback"))
        rolled_back = self.fixture.state()
        self.assertEqual(rolled_back["schema_version"], 1)
        self.assertEqual(rolled_back["current_source"]["version"], "0.3.0")
        self.assertEqual(rolled_back["previous_source"]["version"], "0.4.0")
        self.assertEqual(
            os.readlink(self.fixture.skills_root / manager_name),
            str(
                Path(rolled_back["current_source"]["path"])
                / "skills"
                / manager_name
            ),
        )
        self.assert_success(self.fixture.invoke("check"))

        self.assert_success(self.fixture.invoke("uninstall"))
        self.assert_success(self.fixture.invoke("install", source=nested))
        installed = self.fixture.state()
        self.assertEqual(installed["schema_version"], 1)
        self.assertEqual(installed["current_source"]["version"], "0.4.0")
        self.assertIsNone(installed["previous_source"])
        self.assertEqual(
            os.readlink(self.fixture.skills_root / manager_name),
            str(
                Path(installed["current_source"]["path"])
                / "skills/chatgpt"
                / manager_name
            ),
        )
        self.assert_success(self.fixture.invoke("check"))

    def test_checker_valid_unlisted_canonical_skill_is_rejected(self) -> None:
        source = self.make_v04_nested_release(
            extra_skills=("unlisted-skill",),
        )
        result = self.fixture.invoke("list", source=source)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "canonical skill set disagrees with its public release policy",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
