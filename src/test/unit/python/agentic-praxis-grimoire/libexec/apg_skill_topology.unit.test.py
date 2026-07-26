#!/usr/bin/env python3
"""Focused direct/nested topology and router-map unit contracts."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_skill_library_check as checker  # noqa: E402
from apg_skill_library_check import check_library, render_text  # noqa: E402


def apg30_skill_text(name: str) -> str:
    sections = "".join(
        f"\n## {heading}\n\nEvidence for {heading.lower()}.\n"
        for heading in checker.REQUIRED_H2S
    )
    return (
        "---\n"
        f"name: {name}\n"
        f"description: Use when {name} is required.\n"
        "---\n\n"
        f"# {name}\n"
        f"{sections}"
    )


def write_apg30_library(
    root: Path,
    canonical_paths: dict[str, str],
    *,
    catalog_paths: dict[str, str] | None = None,
    projection_targets: dict[str, str] | None = None,
) -> None:
    skills = root / "skills"
    projections = root / ".agents" / "skills"
    skills.mkdir(parents=True)
    projections.mkdir(parents=True)
    catalog_paths = catalog_paths or canonical_paths
    projection_targets = projection_targets or {
        name: f"../../skills/{relative}"
        for name, relative in canonical_paths.items()
    }
    rows = "\n".join(
        f"| [`{name}`]({catalog_paths[name]}/SKILL.md) | "
        f"Trigger for {name} | `provisional` |"
        for name in sorted(catalog_paths)
    )
    (skills / "README.md").write_text(
        "# APG Skill Library\n\n"
        "## Current development catalog\n\n"
        "| Skill | Trigger boundary | Maturity |\n"
        "| --- | --- | --- |\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    for name, relative in canonical_paths.items():
        leaf = skills / relative
        leaf.mkdir(parents=True)
        (leaf / "SKILL.md").write_text(
            apg30_skill_text(name),
            encoding="utf-8",
        )
        (projections / name).symlink_to(
            projection_targets[name],
            target_is_directory=True,
        )


def write_capability_map(
    leaf: Path,
    router_name: str,
    capability_names: tuple[str, ...],
) -> None:
    references = leaf / "references"
    references.mkdir(exist_ok=True)
    capabilities = [
        {
            "capability_class": f"{name} capability",
            "name": name,
            "trigger": f"{name} selection is required.",
        }
        for name in sorted(capability_names)
    ]
    (references / "capability-map.json").write_text(
        json.dumps(
            {
                "capabilities": capabilities,
                "router_name": router_name,
                "schema_version": 1,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


class APGSkillTopologyTests(unittest.TestCase):
    def test_direct_and_nested_leaf_classes_preserve_catalog_support_and_flat_links(
        self,
    ) -> None:
        paths = {
            "direct-skill": "direct-skill",
            "manager-skill": "chatgpt/manager-skill",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_apg30_library(root, paths)
            references = root / "skills/chatgpt/manager-skill/references"
            references.mkdir()
            (references / "evidence.md").write_text(
                "# Nested support\n",
                encoding="utf-8",
            )
            result = check_library(root)
            nested_link = root / ".agents/skills/manager-skill"
            self.assertEqual(
                nested_link.readlink().as_posix(),
                "../../skills/chatgpt/manager-skill",
            )
            self.assertEqual(
                (nested_link / "references/evidence.md").read_text(
                    encoding="utf-8"
                ),
                "# Nested support\n",
            )
        self.assertTrue(result.passed, render_text(result))
        self.assertEqual(
            (
                result.canonical_skills,
                result.catalog_rows,
                result.projections,
            ),
            (2, 2, 2),
        )

    def test_namespace_depth_duplicate_catalog_and_projection_failures_are_bounded(
        self,
    ) -> None:
        valid = {
            "direct-skill": "direct-skill",
            "manager-skill": "chatgpt/manager-skill",
        }
        cases = (
            ("namespace-skill", "APG036"),
            ("deeper-nesting", "APG037"),
            ("duplicate-name", "APG013"),
            ("stale-catalog", "APG026"),
            ("stale-projection", "APG032"),
            ("escaping-projection", "APG032"),
        )
        for label, expected_code in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                paths = dict(valid)
                catalog = dict(valid)
                projections = {
                    name: f"../../skills/{relative}"
                    for name, relative in valid.items()
                }
                if label == "duplicate-name":
                    paths = {
                        "direct-skill": "direct-skill",
                        "manager-skill": "manager-skill",
                        "manager-skill-copy": "chatgpt/manager-skill-copy",
                    }
                    catalog = dict(paths)
                    projections = {
                        name: f"../../skills/{relative}"
                        for name, relative in paths.items()
                    }
                if label == "stale-catalog":
                    catalog["manager-skill"] = "manager-skill"
                if label == "stale-projection":
                    projections["manager-skill"] = "../../skills/manager-skill"
                if label == "escaping-projection":
                    projections["manager-skill"] = "../../../outside"
                write_apg30_library(
                    root,
                    paths,
                    catalog_paths=catalog,
                    projection_targets=projections,
                )
                if label == "namespace-skill":
                    (root / "skills/chatgpt/SKILL.md").write_text(
                        apg30_skill_text("chatgpt"),
                        encoding="utf-8",
                    )
                if label == "deeper-nesting":
                    nested = root / "skills/chatgpt/group/deeper-skill"
                    nested.mkdir(parents=True)
                    (nested / "SKILL.md").write_text(
                        apg30_skill_text("deeper-skill"),
                        encoding="utf-8",
                    )
                if label == "duplicate-name":
                    duplicate = (
                        root / "skills/chatgpt/manager-skill-copy/SKILL.md"
                    )
                    duplicate.write_text(
                        apg30_skill_text("manager-skill"),
                        encoding="utf-8",
                    )
                result = check_library(root)
                self.assertIn(
                    expected_code,
                    {item.code for item in result.diagnostics},
                    render_text(result),
                )

    def test_namespace_and_router_malformed_shapes_report_owned_diagnostics(
        self,
    ) -> None:
        router = "agentic-praxis-grimoire-workflow"
        paths = {
            router: router,
            "ordinary-skill": "ordinary-skill",
            "manager-skill": "chatgpt/manager-skill",
        }
        cases = (
            "namespace-entry",
            "namespace-symlink",
            "missing-map",
            "malformed-map",
            "malformed-capability",
        )
        for label in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                write_apg30_library(root, paths)
                namespace = root / "skills/chatgpt"
                router_leaf = root / "skills" / router
                if label == "namespace-entry":
                    (namespace / "unexpected.txt").write_text(
                        "unsupported\n",
                        encoding="utf-8",
                    )
                elif label == "namespace-symlink":
                    (namespace / "linked-skill").symlink_to(
                        root / "skills/ordinary-skill",
                        target_is_directory=True,
                    )
                elif label == "malformed-map":
                    references = router_leaf / "references"
                    references.mkdir()
                    (references / "capability-map.json").write_text(
                        "{\n",
                        encoding="utf-8",
                    )
                elif label == "malformed-capability":
                    write_capability_map(
                        router_leaf,
                        router,
                        ("manager-skill", "ordinary-skill"),
                    )
                    map_path = router_leaf / "references/capability-map.json"
                    value = json.loads(map_path.read_text(encoding="utf-8"))
                    del value["capabilities"][0]["trigger"]
                    map_path.write_text(
                        json.dumps(value, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                result = check_library(root)
                expected = (
                    "APG036"
                    if label == "namespace-entry"
                    else "APG004"
                    if label == "namespace-symlink"
                    else "APG038"
                )
                self.assertIn(
                    expected,
                    {item.code for item in result.diagnostics},
                    render_text(result),
                )

    def test_general_and_chatgpt_router_maps_have_disjoint_checked_ownership(
        self,
    ) -> None:
        paths = {
            "agentic-praxis-grimoire-workflow": (
                "agentic-praxis-grimoire-workflow"
            ),
            "ordinary-skill": "ordinary-skill",
            "chatgpt-manager-workflow": "chatgpt/chatgpt-manager-workflow",
            "manager-skill": "chatgpt/manager-skill",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_apg30_library(root, paths)
            write_capability_map(
                root / "skills/agentic-praxis-grimoire-workflow",
                "agentic-praxis-grimoire-workflow",
                ("chatgpt-manager-workflow", "ordinary-skill"),
            )
            write_capability_map(
                root / "skills/chatgpt/chatgpt-manager-workflow",
                "chatgpt-manager-workflow",
                ("manager-skill",),
            )
            result = check_library(root)
            self.assertTrue(result.passed, render_text(result))

            write_capability_map(
                root / "skills/chatgpt/chatgpt-manager-workflow",
                "chatgpt-manager-workflow",
                ("chatgpt-manager-workflow", "ordinary-skill"),
            )
            invalid = check_library(root)
        self.assertIn(
            "APG038",
            {item.code for item in invalid.diagnostics},
            render_text(invalid),
        )

    def test_nested_manager_leaf_requires_chatgpt_subrouter(self) -> None:
        router = "agentic-praxis-grimoire-workflow"
        paths = {
            router: router,
            "manager-skill": "chatgpt/manager-skill",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_apg30_library(root, paths)
            write_capability_map(
                root / "skills" / router,
                router,
                ("manager-skill",),
            )
            result = check_library(root)
        self.assertIn(
            "APG038",
            {item.code for item in result.diagnostics},
            render_text(result),
        )

    def test_general_router_cannot_move_under_chatgpt_and_form_a_cycle(
        self,
    ) -> None:
        paths = {
            "agentic-praxis-grimoire-workflow": (
                "chatgpt/agentic-praxis-grimoire-workflow"
            ),
            "chatgpt-manager-workflow": "chatgpt/chatgpt-manager-workflow",
            "manager-skill": "chatgpt/manager-skill",
            "ordinary-skill": "ordinary-skill",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_apg30_library(root, paths)
            write_capability_map(
                root / "skills/chatgpt/agentic-praxis-grimoire-workflow",
                "agentic-praxis-grimoire-workflow",
                ("chatgpt-manager-workflow", "ordinary-skill"),
            )
            write_capability_map(
                root / "skills/chatgpt/chatgpt-manager-workflow",
                "chatgpt-manager-workflow",
                (
                    "agentic-praxis-grimoire-workflow",
                    "manager-skill",
                ),
            )
            result = check_library(root)
        self.assertIn(
            "APG038",
            {item.code for item in result.diagnostics},
            render_text(result),
        )

if __name__ == "__main__":
    unittest.main()
