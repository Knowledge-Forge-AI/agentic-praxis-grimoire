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
topology = user_skills.apg_skill_topology


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

    def write_capability_map(
        self, path: Path, router: str, names: tuple[str, ...]
    ) -> None:
        capabilities = [
            {"capability_class": "leaf", "name": name, "trigger": "use"}
            for name in names
        ]
        value = {"capabilities": capabilities, "router_name": router, "schema_version": 1}
        path.write_text(json.dumps(value), encoding="utf-8")

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

    def test_lifecycle_files_and_exact_transition_contract(self) -> None:
        root = self.fixture.root / "lifecycle-contract"
        paths = {
            "alpha-profile": Path("skills/alpha-profile"),
            "nodejs-runtime-profile": Path("skills/nodejs-runtime-profile"),
        }
        for relative in paths.values():
            leaf = root / relative / "SKILL.md"
            leaf.parent.mkdir(parents=True)
            leaf.write_text("# profile\n", encoding="utf-8")
        spec = root / "docs/specs/nodejs-runtime-profile.md"
        spec.parent.mkdir(parents=True)
        exact = (
            "Lifecycle: `provisionally-integrated`.\n"
            "Lifecycle ADR: `Accepted with amendment`.\n"
        )
        node_leaf = root / paths["nodejs-runtime-profile"] / "SKILL.md"
        node_leaf.write_text(exact, encoding="utf-8")
        spec.write_text(exact, encoding="utf-8")
        rows = topology.observe_profile_lifecycle_rows(
            root, paths, ("nodejs-runtime-profile",)
        )
        node = rows[1]
        self.assertEqual(
            topology.complete_profile_lifecycle_rows(
                tuple(paths), rows, required_node_row=node
            ),
            tuple(row.text() for row in rows),
        )
        self.assertEqual(rows[0].lifecycle, "not-applicable")
        for integrated in (
            ("nodejs-runtime-profile", "nodejs-runtime-profile"),
            ("unknown-profile",),
        ):
            with self.subTest(integrated=integrated), self.assertRaisesRegex(
                ValueError, "duplicated or unknown"
            ):
                topology.observe_profile_lifecycle_rows(root, paths, integrated)
        malformed = (
            "Lifecycle: `repair-required`.\n",
            "Lifecycle: `repair-required`.\nLifecycle: `repair-required`.\n"
            "Lifecycle ADR: `Proposed`.\n",
            "Lifecycle: `repair-required`. suffix\nLifecycle ADR: `Proposed`.\n",
            "Lifecycle: `repair-required`.\nLifecycle ADR: `Proposed`. suffix\n",
            "Lifecycle: `unknown-state`.\nLifecycle ADR: `Proposed`.\n",
        )
        for content in malformed:
            node_leaf.write_text(content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaises(ValueError):
                topology.observe_profile_lifecycle_rows(root, paths, ())
        node_leaf.write_text(exact, encoding="utf-8")
        spec.write_text(
            exact.replace("provisionally-integrated", "repair-required"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "owners disagree"):
            topology.observe_profile_lifecycle_rows(root, paths, ())
        spec.write_text(exact, encoding="utf-8")
        row_type = topology.ProfileLifecycleRow
        owner = node.lifecycle_owners
        malformed_rows = (
            row_type("", node.lifecycle, node.adr_status, node.integration, owner),
            row_type(node.profile, "", node.adr_status, node.integration, owner),
            row_type(node.profile, node.lifecycle, "", node.integration, owner),
            row_type(node.profile, node.lifecycle, node.adr_status, "", owner),
            row_type(node.profile, "unknown", node.adr_status, node.integration, owner),
            row_type(node.profile, node.lifecycle, "Rejected", node.integration, owner),
            row_type(node.profile, node.lifecycle, node.adr_status, "unknown", owner),
            row_type(node.profile, node.lifecycle, node.adr_status, node.integration, owner * 2),
            row_type(node.profile, "not-applicable", "Proposed", "unintegrated"),
            row_type(node.profile, node.lifecycle, "not-applicable", node.integration, owner),
            row_type(node.profile, node.lifecycle, node.adr_status, node.integration),
            row_type(node.profile, "not-applicable", "not-applicable", "unintegrated", owner),
            row_type(node.profile, node.lifecycle, node.adr_status, node.integration, ("bad|owner",)),
        )
        for row in malformed_rows:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "malformed"):
                topology.complete_profile_lifecycle_rows(
                    tuple(paths), (rows[0], row), required_node_row=node
                )
        for names in (("nodejs-runtime-profile", "alpha-profile"), (), ("alpha",)):
            with self.subTest(names=names), self.assertRaises(ValueError):
                topology.complete_profile_lifecycle_rows(
                    names, rows, required_node_row=node
                )
        duplicate_profile = row_type(
            rows[0].profile, "not-applicable", "not-applicable", "integrated"
        )
        for changed in ((rows[0], rows[0]), (rows[0], duplicate_profile), (rows[0],)):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                topology.complete_profile_lifecycle_rows(
                    tuple(paths), changed, required_node_row=node
                )
        wrong_required_node = row_type(
            node.profile, "repair-required", "Proposed", "unintegrated", owner
        )
        with self.assertRaisesRegex(ValueError, "current owner"):
            topology.complete_profile_lifecycle_rows(
                tuple(paths), rows, required_node_row=wrong_required_node
            )

    def test_exact_topology_transition_contract(self) -> None:
        surfaces = topology.EXACT_TRANSITION_SURFACES
        baseline = {surface: () for surface in surfaces}
        self.assertEqual(
            topology.exact_topology_transition(baseline, baseline, {}), baseline
        )
        malformed_transitions = (
            ({}, baseline, {}),
            (baseline, {}, {}),
            (baseline, baseline, {"unknown": ((), ())}),
            ({**baseline, "catalog": ("b", "a")}, baseline, {}),
            (baseline, {**baseline, "catalog": ("b", "a")}, {}),
            ({**baseline, "catalog": ("a",)}, baseline, {"catalog": (("a", "a"), ())}),
            (baseline, baseline, {"catalog": ((), ("b", "a"))}),
            ({**baseline, "catalog": ("a",)}, baseline, {"catalog": (("a",), ("a",))}),
            (baseline, baseline, {"catalog": (("missing",), ())}),
            (baseline, {**baseline, "catalog": ("unexpected",)}, {}),
        )
        for before, after, delta in malformed_transitions:
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                topology.exact_topology_transition(before, after, delta)

    def test_release_policy_discovery_and_router_file_boundaries(self) -> None:
        repository = USER_CASES.EXISTING.REPOSITORY_ROOT
        policy = json.loads((repository / "release/public-surface.json").read_text())
        paths = topology.policy_skill_paths(policy)
        canonical = topology.canonical_skill_paths(repository, repository / "skills")
        expected = dict(canonical)
        rollback = "nodejs-runtime-profile" not in paths
        if rollback:
            rows = topology.observe_profile_lifecycle_rows(
                repository,
                canonical,
                tuple(name for name in paths if name.endswith("-profile")),
            )
            node = next(
                row for row in rows if row.profile == "nodejs-runtime-profile"
            )
            self.assertEqual(
                (node.lifecycle, node.adr_status, node.integration),
                (
                    "accepted-integration-rolled-back",
                    "Accepted with amendment",
                    "unintegrated",
                ),
            )
            expected.pop("nodejs-runtime-profile")
        self.assertEqual(tuple(paths), tuple(expected))
        current = {name: repository / path for name, path in canonical.items()}
        issues: list[str] = []
        topology.check_router_maps(
            repository,
            current,
            lambda name: bool(name),
            lambda code, *_details: issues.append(code),
        )
        self.assertEqual(issues, ["APG038"] if rollback else [])
        malformed_policies = (
            {**policy, "required_skills": []},
            {**policy, "required_skills": ["invalid"]},
            {**policy, "required_projections": ["invalid"]},
            {
                **policy,
                "required_skills": ["skills/alpha/SKILL.md"],
                "required_projections": [".agents/skills/beta"],
            },
        )
        for malformed in malformed_policies:
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                topology.policy_skill_paths(malformed)
        root = self.fixture.root / "router-contract"
        skills = root / "skills"
        general = skills / topology.GENERAL_ROUTER_NAME
        general.mkdir(parents=True)
        capability_path = general / topology.CAPABILITY_MAP_PATH
        capability_path.parent.mkdir(parents=True)
        self.write_capability_map(
            capability_path, topology.GENERAL_ROUTER_NAME, ("alpha-skill",)
        )
        canonical = {
            topology.GENERAL_ROUTER_NAME: general,
            "alpha-skill": skills / "alpha-skill",
        }
        for observed in ({}, canonical):
            local_issues: list[str] = []
            topology.check_router_maps(
                root,
                observed,
                lambda name: bool(name),
                lambda code, *_details: local_issues.append(code),
            )
            self.assertEqual(local_issues, [])
        capability_path.unlink()
        missing: list[str] = []
        topology.check_router_maps(
            root, canonical, lambda name: bool(name),
            lambda code, *_details: missing.append(code),
        )
        self.assertEqual(missing, ["APG038"])
        capability_path.write_text("not-json", encoding="utf-8")
        invalid: list[str] = []
        topology.check_router_maps(
            root, canonical, lambda name: bool(name),
            lambda code, *_details: invalid.append(code),
        )
        self.assertEqual(invalid, ["APG038"])
        self.write_capability_map(
            capability_path, topology.GENERAL_ROUTER_NAME, ("wrong-skill",)
        )
        mismatched: list[str] = []
        topology.check_router_maps(
            root, canonical, lambda name: bool(name),
            lambda code, *_details: mismatched.append(code),
        )
        self.assertEqual(mismatched, ["APG038"])

    def test_canonical_discovery_file_rejections(self) -> None:
        root = self.fixture.root / "canonical-file-contract"
        frontmatter = root / "frontmatter/alpha-skill/SKILL.md"
        frontmatter.parent.mkdir(parents=True)
        for content in ("not-frontmatter\n", "---\nname: other-skill\n---\n"):
            frontmatter.write_text(content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaises(ValueError):
                topology.frontmatter_name(frontmatter)
        shape_root = self.fixture.root / "canonical-shape"
        shape_skills = shape_root / "skills"
        shape_skills.mkdir(parents=True)
        (shape_skills / "corpus.go").write_text("package skills\n")
        (shape_skills / "unexpected.txt").write_text("unexpected\n")
        direct_target = shape_root / "direct-target"
        direct_target.mkdir()
        (shape_skills / "linked-skill").symlink_to(
            direct_target, target_is_directory=True
        )
        namespace = shape_skills / "chatgpt"
        namespace.mkdir()
        (namespace / "SKILL.md").write_text("namespace\n")
        (namespace / "unexpected.txt").write_text("unexpected\n")
        nested_target = shape_root / "nested-target"
        nested_target.mkdir()
        (namespace / "linked-skill").symlink_to(
            nested_target, target_is_directory=True
        )
        (namespace / "deep-owner/child").mkdir(parents=True)
        shape_issues: list[str] = []
        topology.discover_canonical_leaves(
            shape_root,
            shape_skills,
            lambda code, *_details: shape_issues.append(code),
        )
        self.assertEqual(
            set(shape_issues), {"APG003", "APG004", "APG036", "APG037"}
        )
        with self.assertRaisesRegex(ValueError, "topology is invalid"):
            topology.canonical_skill_paths(shape_root, shape_skills)

    def test_router_map_file_rejections(self) -> None:
        root = self.fixture.root / "router-rejections"
        skills = root / "skills"
        general = skills / topology.GENERAL_ROUTER_NAME
        capability_path = general / topology.CAPABILITY_MAP_PATH
        capability_path.parent.mkdir(parents=True)
        canonical = {
            topology.GENERAL_ROUTER_NAME: general,
            "alpha-skill": skills / "alpha-skill",
        }
        self.write_capability_map(
            capability_path, topology.GENERAL_ROUTER_NAME, ("alpha-skill",)
        )
        wrong_general: list[str] = []
        topology.check_router_maps(
            root,
            {topology.GENERAL_ROUTER_NAME: root / "wrong-general"},
            lambda name: bool(name),
            lambda code, *_details: wrong_general.append(code),
        )
        self.assertEqual(wrong_general, ["APG038"])
        self.write_capability_map(
            capability_path, topology.GENERAL_ROUTER_NAME, ("nested-skill",)
        )
        nested_without_router: list[str] = []
        topology.check_router_maps(
            root,
            {
                topology.GENERAL_ROUTER_NAME: general,
                "nested-skill": skills / "chatgpt/nested-skill",
            },
            lambda name: bool(name),
            lambda code, *_details: nested_without_router.append(code),
        )
        self.assertEqual(nested_without_router, ["APG038"])
        capability_path.write_text(
            json.dumps(
                {
                    "capabilities": [{}],
                    "router_name": topology.GENERAL_ROUTER_NAME,
                    "schema_version": 1,
                }
            ),
            encoding="utf-8",
        )
        invalid_entry: list[str] = []
        topology.check_router_maps(
            root, canonical, lambda name: bool(name),
            lambda code, *_details: invalid_entry.append(code),
        )
        self.assertEqual(invalid_entry, ["APG038"])
        self.write_capability_map(
            capability_path,
            topology.GENERAL_ROUTER_NAME,
            (topology.CHATGPT_ROUTER_NAME,),
        )
        chatgpt = skills / "chatgpt" / topology.CHATGPT_ROUTER_NAME
        final_invalid: list[str] = []
        topology.check_router_maps(
            root,
            {topology.GENERAL_ROUTER_NAME: general, topology.CHATGPT_ROUTER_NAME: chatgpt},
            lambda name: bool(name),
            lambda code, *_details: final_invalid.append(code),
        )
        self.assertEqual(final_invalid, ["APG038", "APG038"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
