#!/usr/bin/env python3
"""Repository-bound APG77D integration and rollback contract for CSS."""

from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(ROOT / "libexec"))
sys.path.insert(0, str(SUPPORT))

import apg_project_skills_core as project_skills  # noqa: E402
import apg_public_release as public_release  # noqa: E402
from apg_candidate_surface_contract import derive_skill_surface_counts  # noqa: E402
from apg_candidate_narrative_state_contract import marker  # noqa: E402
from apg_css_evidence_retention_contract import (  # noqa: E402
    validate_current_contract,
)
from apg_css_profile_candidate_contract import (  # noqa: E402
    load_scenario_fixture,
    validate_candidate,
)
from apg_css_profile_fixture_contract import (  # noqa: E402
    load_known_debt,
    load_manifest,
    validate_css_known_debt,
    validate_fixture_readme,
)


CANDIDATE = "css-language-profile"
LEAF = ROOT / "skills" / CANDIDATE / "SKILL.md"
SPECIFICATION = ROOT / "docs/specs/css-language-profile.md"
COVERAGE = ROOT / "docs/specs/css-language-profile-scenario-coverage.md"
SCENARIOS = ROOT / "src/test/fixtures/apg77-css-language-profile-scenarios.json"
FIXTURE = ROOT / "src/test/fixtures/apg76-css-target-first"
MANIFEST = FIXTURE / "fixture-manifest.json"
KNOWN_DEBT = ROOT / "docs/governance/language-profile-known-debt.json"
REMOVAL_PLAN = ROOT / "src/test/fixtures/apg60-css-removal-plan.json"
ADR = ROOT / "docs/adr/2026/08/0044-css-language-profile-candidate-and-target-first-harness.md"
EVALUATION = ROOT / "docs/evaluations/apg77d-css-known-debt-and-provisional-integration.md"
EXIT = ROOT / "docs/status/2026/08/08/00115-apg77d-css-known-debt-and-provisional-integration-exit.md"
ROLLBACK_BASE_SUBJECT = "APG75A: Close TypeScript scope and lifecycle"
UNIT_TESTS = {
    "src/test/unit/python/agentic-praxis-grimoire/skills/css-language-profile/SKILL.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_evidence_retention_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_profile_candidate_contract.unit.test.py",
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_css_profile_fixture_contract.unit.test.py",
}
PRIVATE_EVIDENCE_UNIT_TEST = (
    "src/test/unit/python/agentic-praxis-grimoire/src/test/support/"
    "apg_css_evidence_retention_contract.unit.test.py"
)
LEGACY_INTEGRATION = (
    "src/test/int/python/agentic-praxis-grimoire/src/test/support/"
    "apg_css_candidate_contract.int.test.py"
)
INTEGRATION_TEST = Path(__file__).resolve().relative_to(ROOT).as_posix()


def _json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _catalog_rows(root: Path = ROOT) -> list[str]:
    return [
        line
        for line in (root / "skills/README.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("| [`")
    ]


def _routes(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    general = _json(
        root / "skills/agentic-praxis-grimoire-workflow/references/capability-map.json"
    )["capabilities"]
    local = _json(
        root / "skills/chatgpt/chatgpt-manager-workflow/references/capability-map.json"
    )["capabilities"]
    return general, local


def _rollback_base_revision() -> str:
    history = subprocess.run(
        ["git", "log", "--all", "--format=%H%x00%s"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    matches = [
        line.split("\x00", 1)[0]
        for line in history
        if line.split("\x00", 1)[1] == ROLLBACK_BASE_SUBJECT
    ]
    assert len(matches) == 1
    return matches[0]


def test_candidate_fixture_debt_and_repository_lifecycle_agree() -> None:
    validate_candidate(
        LEAF.read_text(encoding="utf-8"),
        SPECIFICATION.read_text(encoding="utf-8"),
        COVERAGE.read_text(encoding="utf-8"),
    )
    assert len(load_scenario_fixture(SCENARIOS)["rows"]) == 45
    manifest = load_manifest(MANIFEST)
    validate_fixture_readme((FIXTURE / "README.md").read_text(encoding="utf-8"), integrated=True)
    assert len(manifest["cases"]) == 14
    assert manifest["lifecycle"]["state"] == "provisionally-integrated-with-known-debt"
    assert manifest["authority"]["human_integration_phase"] == "APG77D"
    assert validate_css_known_debt(load_known_debt(KNOWN_DEBT)) == {
        "debts": 5,
        "low": 1,
        "medium": 4,
    }
    assert validate_current_contract(ROOT)["current_machine_bytes"] == 161893
    for text in (
        LEAF.read_text(encoding="utf-8"),
        SPECIFICATION.read_text(encoding="utf-8"),
        COVERAGE.read_text(encoding="utf-8"),
        ADR.read_text(encoding="utf-8"),
    ):
        assert "provisionally-integrated-with-known-debt" in text
    assert "Accepted with amendment (APG77D)" in ADR.read_text(encoding="utf-8")
    assert "0044" in (ROOT / "docs/adr/README.md").read_text(encoding="utf-8")
    narrative_owners = [
        owner
        for owner in _json(REMOVAL_PLAN)["owners"]
        if owner["surface_class"] == "current-narrative-owner"
    ]
    assert {owner["path"] for owner in narrative_owners} == {
        "AGENTS.md",
        "README.md",
        "docs/adr/README.md",
        "docs/project-model.md",
        "docs/project-skill-projection.md",
        "docs/provenance.md",
        "docs/public-release-process.md",
        "docs/roadmap.md",
        "docs/skill-authoring-and-maintenance.md",
        "docs/status/README.md",
        "docs/v0-5-roadmap.md",
    }
    for owner in narrative_owners:
        text = (ROOT / owner["path"]).read_text(encoding="utf-8")
        expected = marker(CANDIDATE, "retained-provisional")
        assert text.count(expected) == 1
        assert text.count(f"<!-- APG-CANDIDATE-STATE: {CANDIDATE} ") == 1


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
    assert os.readlink(projection) == "../../skills/css-language-profile"
    assert projection.resolve() == LEAF.parent.resolve()
    general, local = _routes(ROOT)
    entries = [entry for entry in general if entry["name"] == CANDIDATE]
    assert len(general) == 37
    assert len(local) == 1
    assert len(general) + len(local) == 38
    assert len(entries) == 1
    assert "CSS-specific static semantics" in entries[0]["trigger"]
    assert CANDIDATE in project_skills.EXPECTED_SKILLS
    assert len(project_skills.EXPECTED_SKILLS) == 39


def test_release_inventory_and_historical_exclusions_are_exact() -> None:
    skill = "skills/css-language-profile/SKILL.md"
    projection = ".agents/skills/css-language-profile"
    fixture_files = {
        path.relative_to(ROOT).as_posix()
        for path in FIXTURE.rglob("*")
        if path.is_file()
    }
    critical = fixture_files | {
        ADR.relative_to(ROOT).as_posix(),
        EVALUATION.relative_to(ROOT).as_posix(),
        EXIT.relative_to(ROOT).as_posix(),
        SPECIFICATION.relative_to(ROOT).as_posix(),
        COVERAGE.relative_to(ROOT).as_posix(),
        SCENARIOS.relative_to(ROOT).as_posix(),
        KNOWN_DEBT.relative_to(ROOT).as_posix(),
        "docs/governance/language-profile-known-debt.md",
        "src/test/support/apg_css_candidate_contract.py",
        "src/test/support/apg_css_profile_candidate_contract.py",
        "src/test/support/apg_css_profile_fixture_contract.py",
    }
    all_tests = UNIT_TESTS | {INTEGRATION_TEST, LEGACY_INTEGRATION}
    release_tests = all_tests - {
        PRIVATE_EVIDENCE_UNIT_TEST,
        INTEGRATION_TEST,
        LEGACY_INTEGRATION,
    }
    assert skill in public_release.AUDITED_SKILLS
    assert projection in public_release.AUDITED_PROJECTIONS
    assert critical <= set(public_release.AUDITED_CRITICAL)
    assert release_tests <= set(public_release.AUDITED_TESTS)
    policy = _json(ROOT / "release/public-surface.json")
    assert skill in policy["required_skills"]
    assert projection in policy["required_projections"]
    assert critical <= set(policy["critical_files"])
    assert release_tests <= set(policy["required_test_entrypoints"])
    inventory = _json(ROOT / "testing/apg-test-inventory.json")
    inventory_paths = {entry["path"] for entry in inventory["tests"]}
    assert all_tests <= inventory_paths
    historical = public_release.audited_policy_surfaces("0.4.0")[0]
    current = public_release.audited_policy_surfaces("0.6.0")[0]
    assert public_release.APG77D_V05_CRITICAL <= set(current["critical_files"])
    historical_owners = set().union(*(
        set(historical[key])
        for key in (
            "critical_files", "required_helpers", "required_licensing_files",
            "required_projections", "required_skills", "required_test_entrypoints",
            "required_wrappers",
        )
    ))
    for owners in (
        public_release.APG77D_V05_SKILLS,
        public_release.APG77D_V05_PROJECTIONS,
        public_release.APG77D_V05_TESTS,
        public_release.APG77D_V05_CRITICAL,
    ):
        assert not owners & historical_owners


def test_disposable_rollback_reconstructs_preintegration_owners(tmp_path: Path) -> None:
    before = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout
    archive = subprocess.run(
        ["git", "archive", "--format=tar", _rollback_base_revision()], cwd=ROOT, check=True,
        capture_output=True,
    ).stdout
    rollback = tmp_path / "rollback"
    rollback.mkdir()
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as stream:
        stream.extractall(rollback, filter="data")
    for source in (ADR, EVALUATION, EXIT):
        target = rollback / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    assert derive_skill_surface_counts(rollback) == (30, 30, 30)
    rows = _catalog_rows(rollback)
    assert sum(row.endswith("| `stable` |") for row in rows) == 14
    assert sum(row.endswith("| `provisional` |") for row in rows) == 16
    general, local = _routes(rollback)
    assert len(general) == 28 and len(local) == 1
    assert CANDIDATE not in {entry["name"] for entry in general}
    assert not (rollback / "skills/css-language-profile").exists()
    assert not (rollback / ".agents/skills/css-language-profile").exists()
    assert not (rollback / "docs/governance/language-profile-known-debt.json").exists()
    assert (rollback / ADR.relative_to(ROOT)).is_file()
    assert (rollback / EVALUATION.relative_to(ROOT)).is_file()
    assert (rollback / EXIT.relative_to(ROOT)).is_file()
    after = subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout
    assert after == before
