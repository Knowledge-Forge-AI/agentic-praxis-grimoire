#!/usr/bin/env python3
"""Retained-provisional integration contract for the TypeScript profile."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(ROOT / "libexec"))
sys.path.insert(0, str(SUPPORT))

import apg_project_skills_core as project_skills  # noqa: E402
import apg_public_release as public_release  # noqa: E402
import apg_test  # noqa: E402
from apg_typescript_candidate_contract import (  # noqa: E402
    load_scenario_fixture,
    validate_candidate,
)
from apg_typescript_fixture_contract import (  # noqa: E402
    load_manifest,
    validate_compiler_version,
    validate_fixture_readme,
    validate_fixture_projection,
)


CANDIDATE = "typescript-language-profile"
LEAF = ROOT / "skills" / CANDIDATE / "SKILL.md"
SPECIFICATION = ROOT / "docs/specs/typescript-language-profile.md"
COVERAGE = ROOT / "docs/specs/typescript-language-profile-scenario-coverage.md"
SCENARIOS = ROOT / "src/test/fixtures/apg75-typescript-language-profile-scenarios.json"
FIXTURE = ROOT / "src/test/fixtures/apg74-typescript-intended-state"
MANIFEST = FIXTURE / "fixture-manifest.json"
UNIT_TESTS = {
    "src/test/unit/python/agentic-praxis-grimoire/skills/typescript-language-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_typescript_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_typescript_fixture_contract.unit.test.py",
}
INTEGRATION_TEST = Path(__file__).resolve().relative_to(ROOT).as_posix()


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _catalog_rows() -> list[str]:
    return [
        line
        for line in (ROOT / "skills/README.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("| [`")
    ]


def test_integrated_candidate_fixture_and_exact_compiler_are_coherent() -> None:
    validate_candidate(
        LEAF.read_text(encoding="utf-8"),
        SPECIFICATION.read_text(encoding="utf-8"),
        COVERAGE.read_text(encoding="utf-8"),
        expected_lifecycle="integrated",
    )
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)
    validate_fixture_projection(manifest, scenarios)
    assert len(scenarios["rows"]) == 39
    assert len(manifest["cases"]) == 14
    assert validate_compiler_version(FIXTURE) == "Version 7.0.2"


def test_catalog_projection_maturity_routes_and_project_set_are_exact() -> None:
    rows = _catalog_rows()
    candidate_rows = [row for row in rows if f"[`{CANDIDATE}`]" in row]
    assert len(rows) == 39
    assert len(candidate_rows) == 1
    assert candidate_rows[0].endswith("| `provisional` |")
    assert sum(row.endswith("| `stable` |") for row in rows) == 14
    assert sum(row.endswith("| `provisional` |") for row in rows) == 25
    projection = ROOT / ".agents/skills" / CANDIDATE
    assert projection.is_symlink()
    assert os.readlink(projection) == "../../skills/typescript-language-profile"
    assert projection.resolve() == LEAF.parent.resolve()

    general = _json(
        ROOT / "skills/agentic-praxis-grimoire-workflow/references/capability-map.json"
    )["capabilities"]
    local = _json(
        ROOT / "skills/chatgpt/chatgpt-manager-workflow/references/capability-map.json"
    )["capabilities"]
    entries = [entry for entry in general if entry["name"] == CANDIDATE]
    assert len(general) == 37
    assert len(local) == 1
    assert len(general) + len(local) == 38
    assert len(entries) == 1
    assert "TypeScript-specific static semantics" in entries[0]["trigger"]
    assert CANDIDATE in project_skills.EXPECTED_SKILLS
    assert len(project_skills.EXPECTED_SKILLS) == 39


def test_release_inventory_and_historical_boundary_own_exact_surfaces() -> None:
    skill = "skills/typescript-language-profile/SKILL.md"
    projection = ".agents/skills/typescript-language-profile"
    fixture_files = {
        path.relative_to(ROOT).as_posix()
        for path in FIXTURE.rglob("*")
        if path.is_file()
    }
    critical = fixture_files | {
        SPECIFICATION.relative_to(ROOT).as_posix(),
        COVERAGE.relative_to(ROOT).as_posix(),
        SCENARIOS.relative_to(ROOT).as_posix(),
        "src/test/support/apg_typescript_candidate_contract.py",
        "src/test/support/apg_typescript_fixture_contract.py",
    }
    tests = UNIT_TESTS | {INTEGRATION_TEST}
    assert skill in public_release.AUDITED_SKILLS
    assert projection in public_release.AUDITED_PROJECTIONS
    assert critical <= set(public_release.AUDITED_CRITICAL)
    assert tests <= set(public_release.AUDITED_TESTS)
    policy = _json(ROOT / "release/public-surface.json")
    assert skill in policy["required_skills"]
    assert projection in policy["required_projections"]
    assert critical <= set(policy["critical_files"])
    assert tests <= set(policy["required_test_entrypoints"])
    inventory = _json(ROOT / "testing/apg-test-inventory.json")
    inventory_paths = {entry["path"] for entry in inventory["tests"]}
    assert tests <= inventory_paths

    historical = public_release.audited_policy_surfaces("0.4.0")[0]
    current = public_release.audited_policy_surfaces("0.6.0")[0]
    assert public_release.APG75A_V05_CRITICAL <= set(current["critical_files"])
    historical_owners = set().union(
        *(set(historical[key]) for key in (
            "critical_files", "required_helpers", "required_licensing_files",
            "required_projections", "required_skills", "required_test_entrypoints",
            "required_wrappers",
        ))
    )
    for owners in (
        public_release.APG75_V05_SKILLS,
        public_release.APG75_V05_PROJECTIONS,
        public_release.APG75_V05_TESTS,
        public_release.APG75_V05_CRITICAL,
        public_release.APG75A_V05_CRITICAL,
    ):
        assert not owners & historical_owners
    historical_tests = set(historical["required_test_entrypoints"])
    assert not historical_tests & apg_test.TYPESCRIPT_COMPILER_TEST_PATHS
    rollback_inventory = apg_test.Inventory(
        {},
        {},
        {path: ("historical-owner", "unit") for path in historical_tests},
    )
    assert not apg_test.requires_typescript_compiler(rollback_inventory)
    assert apg_test.requires_typescript_compiler(apg_test.load_inventory(ROOT))


def test_adr_and_current_lifecycle_are_exclusive() -> None:
    adr = (
        ROOT
        / "docs/adr/2026/08/0043-typescript-language-profile-candidate-and-intended-state-harness.md"
    ).read_text(encoding="utf-8")
    assert "Accepted with amendment (APG75)" in adr
    assert "Proposed (APG74)" not in adr
    assert LEAF.is_file()
    assert (ROOT / ".agents/skills" / CANDIDATE).is_symlink()
    assert any(f"[`{CANDIDATE}`]" in row for row in _catalog_rows())


def test_current_lifecycle_surfaces_agree() -> None:
    coverage = COVERAGE.read_text(encoding="utf-8")
    fixture_readme = (FIXTURE / "README.md").read_text(encoding="utf-8")
    manifest = _json(MANIFEST)
    validate_fixture_readme(fixture_readme)
    assert "Accepted with amendment" in coverage
    assert "provisionally integrated after APG75 and APG75A" in coverage
    assert "current maintained fixture owner" in fixture_readme
    assert "provisionally integrated" in fixture_readme
    assert "branch-only" not in fixture_readme
    assert manifest["current_phase"] == "APG75A"
    assert manifest["lifecycle"] == "provisionally-integrated"
