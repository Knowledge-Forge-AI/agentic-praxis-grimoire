#!/usr/bin/env python3
"""Focused direct/nested topology and router-map unit contracts."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

import pytest

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


_ORACLE_LIFECYCLE = re.compile(r"Lifecycle: `([a-z][a-z0-9-]*)`\.")
_ORACLE_ADR = re.compile(
    r"Lifecycle ADR: `(not-applicable|Proposed|Accepted with amendment)`\."
)


def _oracle_profile_paths(root: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for skills_root in (root / "skills", root / "skills" / "chatgpt"):
        for leaf in skills_root.iterdir():
            skill = leaf / "SKILL.md"
            if not leaf.is_dir() or not skill.is_file():
                continue
            names = re.findall(
                r"(?m)^name: ([a-z0-9]+(?:-[a-z0-9]+)*)$",
                skill.read_text(encoding="utf-8"),
            )
            if len(names) == 1 and names[0].endswith("-profile"):
                paths[names[0]] = leaf.relative_to(root)
    return {name: paths[name] for name in sorted(paths)}


def _oracle_catalog(root: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    pattern = re.compile(
        r"\| \[`([^`]+)`\]\([^)]*\) \| .* \| "
        r"`(stable|provisional)` \|"
    )
    for line in (root / "skills" / "README.md").read_text(
        encoding="utf-8"
    ).splitlines():
        match = pattern.fullmatch(line)
        if match is not None:
            rows[match.group(1)] = match.group(2)
    return rows


def _oracle_owner(path: Path) -> tuple[str, str] | None:
    lines = path.read_text(encoding="utf-8").splitlines()
    lifecycle = [line for line in lines if line.startswith("Lifecycle:")]
    adr_status = [line for line in lines if line.startswith("Lifecycle ADR:")]
    if not lifecycle and not adr_status:
        return None
    if len(lifecycle) != 1 or len(adr_status) != 1:
        raise ValueError("oracle lifecycle owner fields are incomplete or duplicated")
    lifecycle_match = _ORACLE_LIFECYCLE.fullmatch(lifecycle[0])
    adr_match = _ORACLE_ADR.fullmatch(adr_status[0])
    if lifecycle_match is None or adr_match is None:
        raise ValueError("oracle lifecycle owner fields are not exact and anchored")
    return lifecycle_match.group(1), adr_match.group(1)


def _oracle_lifecycle_rows(
    root: Path,
) -> tuple[checker.apg_skill_topology.ProfileLifecycleRow, ...]:
    profile_paths = _oracle_profile_paths(root)
    catalog_profiles = {
        name for name in _oracle_catalog(root) if name.endswith("-profile")
    }
    projection_profiles = {
        path.name
        for path in (root / ".agents" / "skills").iterdir()
        if path.name.endswith("-profile")
    }
    if catalog_profiles != projection_profiles:
        raise ValueError("independent integration owners disagree")
    rows = []
    for name, relative in profile_paths.items():
        owner_values = []
        for path in (
            root / relative / "SKILL.md",
            root / "docs" / "specs" / f"{name}.md",
        ):
            if path.is_file() and (value := _oracle_owner(path)) is not None:
                owner_values.append((*value, path.relative_to(root).as_posix()))
        if owner_values and len({value[:2] for value in owner_values}) != 1:
            raise ValueError(f"independent lifecycle owners disagree for {name}")
        lifecycle, adr_status = owner_values[0][:2] if owner_values else (
            "not-applicable",
            "not-applicable",
        )
        rows.append(
            checker.apg_skill_topology.ProfileLifecycleRow(
                name,
                lifecycle,
                adr_status,
                "integrated" if name in catalog_profiles else "unintegrated",
                tuple(sorted(value[2] for value in owner_values)),
            )
        )
    return tuple(rows)


def _production_lifecycle_rows(root: Path):
    canonical = checker.apg_skill_topology.canonical_skill_paths(
        root, root / "skills"
    )
    catalog = checker.parse_catalog((root / "skills" / "README.md").read_text())
    integrated = tuple(
        sorted(row.name for row in catalog.rows if row.name.endswith("-profile"))
    )
    return checker.apg_skill_topology.observe_profile_lifecycle_rows(
        root, canonical, integrated
    )


def _require_independent_rows(observed_reader, authority_reader):
    if observed_reader is authority_reader:
        raise ValueError("observation and authority readers are not independent")
    observed = tuple(observed_reader())
    authority = tuple(authority_reader())
    if observed != authority:
        raise ValueError("production lifecycle rows disagree with independent owners")
    return observed


class APG81HCompleteLifecycleTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = list(_oracle_lifecycle_rows(REPOSITORY_ROOT))
        self.names = tuple(row.profile for row in self.rows)
        self.node = next(
            row for row in self.rows if row.profile == "nodejs-runtime-profile"
        )

    def test_complete_map_is_canonical_derived_and_binds_node_repair(self) -> None:
        complete = checker.apg_skill_topology.complete_profile_lifecycle_rows(
            self.names, self.rows, required_node_row=self.node
        )
        self.assertEqual(len(complete), len(self.names))
        self.assertIn(self.node.text(), complete)

    def test_complete_map_rejects_domain_and_no_owner_mutations(self) -> None:
        ordinary_index = next(
            index for index, row in enumerate(self.rows) if not row.lifecycle_owners
        )
        wrong = list(self.rows)
        ordinary = wrong[ordinary_index]
        wrong[ordinary_index] = checker.apg_skill_topology.ProfileLifecycleRow(
            ordinary.profile,
            "retained-provisional",
            "not-applicable",
            ordinary.integration,
        )
        unknown = checker.apg_skill_topology.ProfileLifecycleRow(
            "unknown-language-profile",
            "not-applicable",
            "not-applicable",
            "integrated",
        )
        mutations = (
            [row for row in self.rows if row.profile != self.node.profile],
            self.rows[1:],
            self.rows + [unknown],
            self.rows + [self.rows[0]],
            wrong,
        )
        for rows in mutations:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                checker.apg_skill_topology.complete_profile_lifecycle_rows(
                    self.names, rows, required_node_row=self.node
                )


def test_apg81h_current_repository_complete_profile_lifecycle_observation() -> None:
    observed = _require_independent_rows(
        lambda: _production_lifecycle_rows(REPOSITORY_ROOT),
        lambda: _oracle_lifecycle_rows(REPOSITORY_ROOT),
    )
    profile_names = tuple(_oracle_profile_paths(REPOSITORY_ROOT))
    assert len(profile_names) == 22
    assert len(observed) == len(profile_names)
    explicit = {row.profile for row in observed if row.lifecycle_owners}
    assert explicit == {
        "css-language-profile",
        "javascript-language-profile",
        "markdown-language-profile",
        "nodejs-runtime-profile",
        "typescript-language-profile",
    }
    no_owner = [row for row in observed if not row.lifecycle_owners]
    assert len(no_owner) == 17
    assert all(
        row.lifecycle == row.adr_status == "not-applicable" for row in no_owner
    )
    node = next(row for row in observed if row.profile == "nodejs-runtime-profile")
    assert node == checker.apg_skill_topology.ProfileLifecycleRow(
        "nodejs-runtime-profile",
        "provisionally-integrated",
        "Accepted with amendment",
        "integrated",
        (
            "docs/specs/nodejs-runtime-profile.md",
            "skills/nodejs-runtime-profile/SKILL.md",
        ),
    )


def test_apg81h_independence_mutations(tmp_path: Path) -> None:
    production = list(_production_lifecycle_rows(REPOSITORY_ROOT))
    authority = list(_oracle_lifecycle_rows(REPOSITORY_ROOT))
    ordinary_index = next(
        index for index, row in enumerate(production) if not row.lifecycle_owners
    )
    wrong_production = list(production)
    row = wrong_production[ordinary_index]
    wrong_production[ordinary_index] = checker.apg_skill_topology.ProfileLifecycleRow(
        row.profile, "retained-provisional", "not-applicable", row.integration
    )
    with pytest.raises(ValueError, match="disagree"):
        _require_independent_rows(lambda: wrong_production, lambda: authority)

    altered_owner = tmp_path / "altered-owner.md"
    altered_owner.write_text(
        "Lifecycle: `provisionally-integrated`.\n"
        "Lifecycle ADR: `Accepted with amendment`.\n",
        encoding="utf-8",
    )
    lifecycle, adr_status = _oracle_owner(altered_owner)
    explicit_index = next(
        index
        for index, candidate in enumerate(authority)
        if candidate.profile == "javascript-language-profile"
    )
    altered_authority = list(authority)
    explicit = altered_authority[explicit_index]
    altered_authority[explicit_index] = checker.apg_skill_topology.ProfileLifecycleRow(
        explicit.profile,
        lifecycle,
        adr_status,
        explicit.integration,
        explicit.lifecycle_owners,
    )
    with pytest.raises(ValueError, match="disagree"):
        _require_independent_rows(lambda: production, lambda: altered_authority)

    producer = lambda: production
    with pytest.raises(ValueError, match="not independent"):
        _require_independent_rows(producer, producer)


def test_apg81h_owner_agreement_and_exact_matching(tmp_path: Path) -> None:
    leaf = tmp_path / "skills" / "nodejs-runtime-profile"
    spec = tmp_path / "docs" / "specs" / "nodejs-runtime-profile.md"
    leaf.mkdir(parents=True)
    spec.parent.mkdir(parents=True)
    (leaf / "SKILL.md").write_text(
        "Lifecycle: `provisionally-integrated`.\n"
        "Lifecycle ADR: `Accepted with amendment`.\n",
        encoding="utf-8",
    )
    spec.write_text(
        "Lifecycle: `provisionally-integrated-with-known-debt`.\n"
        "Lifecycle ADR: `Accepted with amendment`.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="owners disagree"):
        checker.apg_skill_topology.observe_profile_lifecycle_rows(
            tmp_path,
            {"nodejs-runtime-profile": Path("skills/nodejs-runtime-profile")},
            (),
        )
    assert _oracle_owner(spec) == (
        "provisionally-integrated-with-known-debt",
        "Accepted with amendment",
    )

    malformed = tmp_path / "malformed-prefix.md"
    malformed.write_text(
        "Lifecycle: `provisionally-integrated-with-known-debt-extra`.\n"
        "Lifecycle ADR: `Accepted with amendment`.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown lifecycle value"):
        checker.apg_skill_topology._exact_lifecycle_owner(malformed)


def test_apg81h_maturity_changes_do_not_create_lifecycle(tmp_path: Path) -> None:
    row = next(
        row for row in _oracle_lifecycle_rows(REPOSITORY_ROOT)
        if not row.lifecycle_owners
    )
    original = _oracle_catalog(REPOSITORY_ROOT)
    maturity = original[row.profile]
    changed_maturity = "provisional" if maturity == "stable" else "stable"
    catalog = (REPOSITORY_ROOT / "skills" / "README.md").read_text(
        encoding="utf-8"
    )
    old_fragment = f"[`{row.profile}`]"
    matching_line = next(
        line for line in catalog.splitlines() if old_fragment in line
    )
    changed_line = matching_line.replace(
        f"`{maturity}`", f"`{changed_maturity}`"
    )
    test_root = tmp_path
    (test_root / "skills").mkdir()
    (test_root / "skills" / "README.md").write_text(
        changed_line + "\n", encoding="utf-8"
    )
    assert _oracle_catalog(test_root)[row.profile] == changed_maturity
    assert row.lifecycle == "not-applicable"


@pytest.mark.parametrize("case", range(50))
def test_apg81h_exact_transition_case(case: int) -> None:
    surfaces = tuple(sorted(checker.apg_skill_topology.EXACT_TRANSITION_SURFACES))
    baseline = {surface: (f"{surface}-before",) for surface in surfaces}
    if case == 0:
        assert (
            checker.apg_skill_topology.exact_topology_transition(
                baseline, baseline, {}
            )
            == baseline
        )
        return
    if case == 1:
        observed = dict(baseline)
        observed["profile_lifecycle"] = ("profile_lifecycle-after",)
        assert checker.apg_skill_topology.exact_topology_transition(
            baseline,
            observed,
            {
                "profile_lifecycle": (
                    ("profile_lifecycle-before",),
                    ("profile_lifecycle-after",),
                )
            },
        )["profile_lifecycle"] == ("profile_lifecycle-after",)
        return

    surface = surfaces[(case - 2) // 4]
    mutation = (case - 2) % 4
    observed = dict(baseline)
    delta = {surface: ((f"{surface}-before",), (f"{surface}-after",))}
    if mutation == 0:
        observed[surface] = ()
    elif mutation == 1:
        observed[surface] = (f"{surface}-after", f"{surface}-unknown")
    elif mutation == 2:
        observed[surface] = (f"{surface}-after", f"{surface}-after")
    else:
        observed[surface] = (f"{surface}-drift",)
    with pytest.raises(ValueError):
        checker.apg_skill_topology.exact_topology_transition(
            baseline, observed, delta
        )


if __name__ == "__main__":
    unittest.main()
