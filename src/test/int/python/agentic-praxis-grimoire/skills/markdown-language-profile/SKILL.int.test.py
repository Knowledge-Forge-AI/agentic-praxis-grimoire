#!/usr/bin/env python3
"""Retained-provisional integration contract for the Markdown profile."""

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
from apg_markdown_candidate_contract import (  # noqa: E402
    load_fixture,
    parse_clauses,
    parse_coverage,
    scenario_support,
    targeted_guard_failures,
    validate_navigation,
)
from apg_markdown_register_contract import (  # noqa: E402
    verify_fixture_projection,
)


CANDIDATE = "markdown-language-profile"
LEAF = ROOT / "skills" / CANDIDATE / "SKILL.md"
SPECIFICATION = ROOT / "docs/specs/markdown-language-profile.md"
COVERAGE = ROOT / "docs/specs/markdown-language-profile-scenario-coverage.md"
FIXTURE = ROOT / "src/test/fixtures/apg66-markdown-language-profile-scenarios.json"
REGISTER_SOURCE = ROOT / "src/test/fixtures/apg64-markdown-scenario-register.md"
UNIT_TEST = (
    ROOT
    / "src/test/unit/python/agentic-praxis-grimoire/skills"
    / CANDIDATE
    / "SKILL.unit.test.py"
)
INTEGRATION_TEST = Path(__file__).resolve()


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _catalog_rows() -> list[str]:
    return [
        line
        for line in (ROOT / "skills/README.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("| [`")
    ]


def test_register_binding_navigation_and_targeted_guards_hold_in_integrated_tree() -> None:
    fixture = load_fixture(FIXTURE)
    clauses = parse_clauses(
        LEAF.read_text(encoding="utf-8"),
        SPECIFICATION.read_text(encoding="utf-8"),
    )
    coverage = parse_coverage(COVERAGE.read_text(encoding="utf-8"))
    register_data = REGISTER_SOURCE.read_bytes()
    assert verify_fixture_projection(register_data, fixture) is None
    validate_navigation(fixture["rows"], coverage, clauses)
    results = [scenario_support(row, coverage, clauses) for row in fixture["rows"]]
    assert len(results) == 34
    assert all(result["missing"] == [] for result in results)
    assert all("expected_consequence" not in result for result in results)
    assert targeted_guard_failures(clauses) == []


def test_catalog_projection_and_maturity_are_exact() -> None:
    rows = _catalog_rows()
    candidate_rows = [row for row in rows if f"[`{CANDIDATE}`]" in row]
    assert len(rows) == 33
    assert len(candidate_rows) == 1
    assert candidate_rows[0].endswith("| `provisional` |")
    assert sum(row.endswith("| `stable` |") for row in rows) == 14
    assert sum(row.endswith("| `provisional` |") for row in rows) == 19
    projection = ROOT / ".agents/skills" / CANDIDATE
    assert projection.is_symlink()
    assert os.readlink(projection) == "../../skills/markdown-language-profile"
    assert projection.resolve() == LEAF.parent.resolve()


def test_router_project_and_checked_edges_are_exact() -> None:
    general = _json(
        ROOT
        / "skills/agentic-praxis-grimoire-workflow/references/capability-map.json"
    )["capabilities"]
    local = _json(
        ROOT / "skills/chatgpt/chatgpt-manager-workflow/references/capability-map.json"
    )["capabilities"]
    candidate_entries = [entry for entry in general if entry["name"] == CANDIDATE]
    assert len(general) == 31
    assert len(local) == 1
    assert len(general) + len(local) == 32
    assert len(candidate_entries) == 1
    assert "actual Markdown parser" in candidate_entries[0]["trigger"]
    assert CANDIDATE in project_skills.EXPECTED_SKILLS
    assert len(project_skills.EXPECTED_SKILLS) == 33
    conceptual = {
        "accessibility-owner", "data-language-owner", "embedded-language-owner",
        "host-owner", "html-owner", "mdx-owner", "parser-tool-owner",
        "project-design", "project-policy", "repository-policy",
    }
    assert not conceptual & {entry["name"] for entry in general}


def test_release_and_inventory_own_every_current_surface() -> None:
    skill = "skills/markdown-language-profile/SKILL.md"
    projection = ".agents/skills/markdown-language-profile"
    unit = UNIT_TEST.relative_to(ROOT).as_posix()
    integration = INTEGRATION_TEST.relative_to(ROOT).as_posix()
    critical = {
        SPECIFICATION.relative_to(ROOT).as_posix(),
        COVERAGE.relative_to(ROOT).as_posix(),
        FIXTURE.relative_to(ROOT).as_posix(),
        REGISTER_SOURCE.relative_to(ROOT).as_posix(),
        "src/test/support/apg_markdown_candidate_contract.py",
        "src/test/support/apg_markdown_clause_guard_contract.py",
        "src/test/support/apg_markdown_polarity_guard_contract.py",
        "src/test/support/apg_markdown_register_contract.py",
        "src/test/support/apg_markdown_token_guard_contract.py",
        "src/test/support/apg_markdown_vocabulary_contract.py",
    }
    assert skill in public_release.AUDITED_SKILLS
    assert projection in public_release.AUDITED_PROJECTIONS
    assert critical <= set(public_release.AUDITED_CRITICAL)
    assert {unit, integration} <= set(public_release.AUDITED_TESTS)
    register_unit = (
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/"
        "apg_markdown_register_contract.unit.test.py"
    )
    assert register_unit in public_release.AUDITED_TESTS
    guard_units = {
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/"
        "apg_markdown_clause_guard_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/"
        "apg_markdown_polarity_guard_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/"
        "apg_markdown_token_guard_contract.unit.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/"
        "apg_markdown_vocabulary_contract.unit.test.py",
    }
    assert guard_units <= set(public_release.AUDITED_TESTS)
    policy = _json(ROOT / "release/public-surface.json")
    assert skill in policy["required_skills"]
    assert projection in policy["required_projections"]
    assert critical <= set(policy["critical_files"])
    assert {unit, integration} <= set(policy["required_test_entrypoints"])
    assert register_unit in policy["required_test_entrypoints"]
    assert guard_units <= set(policy["required_test_entrypoints"])
    inventory = _json(ROOT / "testing/apg-test-inventory.json")
    tests = {(entry["owner"], entry["path"], entry["suite"]) for entry in inventory["tests"]}
    assert (skill, unit, "unit") in tests
    assert (skill, integration, "integration") in tests
    assert (
        "src/test/support/apg_markdown_candidate_contract.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/"
        "apg_markdown_candidate_contract.unit.test.py",
        "unit",
    ) in tests
    assert (
        "src/test/support/apg_markdown_register_contract.py",
        register_unit,
        "unit",
    ) in tests
    guard_owners = {
        guard_unit: "src/test/support/" + guard_unit.rsplit("/", 1)[-1].replace(
            ".unit.test.py", ".py"
        )
        for guard_unit in guard_units
    }
    for guard_unit, guard_owner in guard_owners.items():
        assert (guard_owner, guard_unit, "unit") in tests


def test_retained_state_is_exclusive_and_v04_is_immutable() -> None:
    adr = (ROOT / "docs/adr/2026/07/0038-markdown-language-profile-candidate.md").read_text(
        encoding="utf-8"
    )
    retained = (
        "- Status: Accepted with amendment" in adr
        and LEAF.is_file()
        and (ROOT / ".agents/skills" / CANDIDATE).is_symlink()
        and any(f"[`{CANDIDATE}`]" in row for row in _catalog_rows())
    )
    authored_proposed_unintegrated = (
        "- Status: Proposed" in adr
        and not (ROOT / ".agents/skills" / CANDIDATE).exists()
        and not any(f"[`{CANDIDATE}`]" in row for row in _catalog_rows())
    )
    rejected_preserved = (
        "- Status: Rejected" in adr
        and not LEAF.exists()
        and not (ROOT / ".agents/skills" / CANDIDATE).exists()
    )
    assert retained
    assert not authored_proposed_unintegrated
    assert not rejected_preserved
    historical = public_release.audited_policy_surfaces("0.4.0")[0]
    historical_owners = set().union(*(
        set(historical[key])
        for key in (
            "critical_files", "required_helpers", "required_licensing_files",
            "required_projections", "required_skills",
            "required_test_entrypoints", "required_wrappers",
        )
    ))
    for owners in (
        public_release.APG66_V05_SKILLS,
        public_release.APG66_V05_PROJECTIONS,
        public_release.APG66_V05_TESTS,
        public_release.APG66_V05_CRITICAL,
        public_release.APG66A_V05_TESTS,
        public_release.APG66A_V05_CRITICAL,
        public_release.APG66B_V05_TESTS,
        public_release.APG66B_V05_CRITICAL,
        public_release.APG66C_V05_TESTS,
        public_release.APG66C_V05_CRITICAL,
    ):
        assert not owners & historical_owners
