#!/usr/bin/env python3
"""Unit evidence for the maintained APG81 Node candidate contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_nodejs_candidate_contract import (  # noqa: E402
    ContractError,
    load_scenarios,
    validate_candidate,
    validate_review_sequence,
    validate_rollback_lifecycle,
    validate_scenarios,
)


SCENARIOS = ROOT / "src/test/fixtures/apg81-nodejs-runtime-profile-scenarios.json"


def _candidate() -> tuple[str, str, str]:
    return (
        (ROOT / "skills/nodejs-runtime-profile/SKILL.md").read_text(encoding="utf-8"),
        (ROOT / "docs/specs/nodejs-runtime-profile.md").read_text(encoding="utf-8"),
        (ROOT / "docs/specs/nodejs-runtime-profile-scenario-coverage.md").read_text(encoding="utf-8"),
    )


def test_current_candidate_and_scenarios_are_closed() -> None:
    validate_candidate(*_candidate())
    value = load_scenarios(SCENARIOS)
    assert len(value["rows"]) == 24
    assert len(value["receivers"]) == 12
    adr = (ROOT / "docs/adr/2026/08/0046-nodejs-runtime-and-cli-stack-candidate-and-target-first-harness.md").read_text(encoding="utf-8")
    assert "Rollback is history preserving" in adr
    assert "Removing those paths removes it" not in adr


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["authority"]["target_pins"][0].update(commit="0" * 40),
        lambda value: value["authority"]["target_pins"][1].update(tree="0" * 40),
        lambda value: value["authority"]["target_pins"][1].update(repository_role="website"),
        lambda value: value["authority"]["target_pins"][1].update(tracked_leaf_entries=71),
        lambda value: value["authority"]["runtime_roles"][0].update(executable_sha256="0" * 64),
        lambda value: value["authority"]["runtime_roles"][0].update(platform="linux"),
        lambda value: value["authority"]["runtime_roles"][1].update(architecture="x64"),
        lambda value: value["authority"]["runtime_roles"].pop(),
        lambda value: value["receivers"][0].update(availability="present"),
        lambda value: value["receivers"][0].update(scope="unrelated scope"),
        lambda value: value["receivers"][0].update(required_evidence="unrelated evidence"),
        lambda value: value["rows"][6].update(completion_state="owned-complete"),
        lambda value: value["rows"][7].update(whole_file_owner="javascript-language-profile"),
        lambda value: value["rows"][2].update(selection="route-to-owner"),
        lambda value: value["rows"][2].update(response="stop-and-escalate"),
    ],
)
def test_scenario_mutations_are_rejected(mutation) -> None:
    value = deepcopy(load_scenarios(SCENARIOS))
    mutation(value)
    with pytest.raises(ContractError, match="exact authority projection"):
        validate_scenarios(value)


def test_rejected_candidate_claims_are_detected() -> None:
    leaf, specification, coverage = _candidate()
    with pytest.raises(ContractError, match="omits corrected contract"):
        validate_candidate(leaf, specification.replace("69 recursive tracked leaf", "71 tracked"), coverage)
    with pytest.raises(ContractError, match="retains rejected contract"):
        validate_candidate(leaf, specification + "\nRemoving those paths removes the candidate.\n", coverage)
    with pytest.raises(ContractError, match="scenario-to-clause projection"):
        validate_candidate(leaf, specification, coverage.replace("`NODE-ESM`", "`NODE-NOT-A-CLAUSE`", 1))
    with pytest.raises(ContractError, match="exact leaf marker set"):
        validate_candidate(
            leaf.replace("APG-CLAUSE: NODE-ESM", "APG-CLAUSE: NODE-NOT-A-CLAUSE", 1),
            specification,
            coverage,
        )
    moved = coverage.replace(
        "| `APG80-NODE-003` | `.mjs` Node ESM mapping | `NODE-MODULE-MAPPING` |",
        "| `APG80-NODE-003` | `.mjs` Node ESM mapping | `NODE-MODULE-MAPPING`, `NODE-COMMONJS` |",
    ).replace(
        "| `APG80-NODE-004` | `.cjs` Node CommonJS mapping | `NODE-MODULE-MAPPING`, `NODE-COMMONJS` |",
        "| `APG80-NODE-004` | `.cjs` Node CommonJS mapping | `NODE-MODULE-MAPPING` |",
    )
    with pytest.raises(ContractError, match="scenario-to-clause projection"):
        validate_candidate(leaf, specification, moved)


def _rollback() -> dict[str, object]:
    lifecycle = "accepted-integration-rolled-back"
    return {
        "adr_file_status": "Accepted with amendment",
        "adr_index_status": "Accepted with amendment",
        "candidate_lifecycle": {
            "fixture_manifest": lifecycle,
            "leaf": lifecycle,
            "scenario_authority": lifecycle,
            "specification": lifecycle,
        },
        "candidate_present": True,
        "counts": {
            "canonical": 33,
            "catalog": 32,
            "chatgpt_local_routes": 1,
            "checked_routes": 31,
            "general_routes": 30,
            "projections": 32,
            "provisional": 18,
            "stable": 14,
        },
        "historical_proposed_provenance_present": True,
        "integration_owners": {
            "capability_route": False,
            "catalog": False,
            "current_development_release": False,
            "maintained_integration_test": False,
            "maturity": False,
            "project_selection": False,
            "projection": False,
            "test_inventory": False,
        },
        "schema_version": 1,
    }


def test_post_acceptance_rollback_lifecycle_is_closed() -> None:
    validate_rollback_lifecycle(_rollback())


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(adr_file_status="Proposed"),
        lambda value: value.update(candidate_present=False),
        lambda value: value["candidate_lifecycle"].update(fixture_manifest="authored-proposed-unintegrated"),
        lambda value: value["integration_owners"].update(catalog=True),
    ],
)
def test_post_acceptance_rollback_mutations_are_rejected(mutation) -> None:
    value = deepcopy(_rollback())
    mutation(value)
    with pytest.raises(ContractError):
        validate_rollback_lifecycle(value)


@pytest.mark.parametrize("invalid_version", [True, 1.0])
def test_post_acceptance_rollback_rejects_non_integer_schema_versions(invalid_version) -> None:
    value = _rollback()
    value["schema_version"] = invalid_version
    with pytest.raises(ContractError):
        validate_rollback_lifecycle(value)


@pytest.mark.parametrize("invalid_count", [True, 1.0])
def test_post_acceptance_rollback_rejects_non_integer_counts(invalid_count) -> None:
    value = _rollback()
    value["counts"]["chatgpt_local_routes"] = invalid_count
    with pytest.raises(ContractError):
        validate_rollback_lifecycle(value)


def test_staged_review_sequence_has_no_self_attesting_tree() -> None:
    digest = "a" * 64
    validate_review_sequence({
        "commit_message_review_claim": False,
        "external_review_identity": None,
        "external_review_state": "not-run",
        "repository_review_state": "review-target-frozen",
        "schema_version": 1,
        "staged_identity": digest,
    })
    validate_review_sequence({
        "commit_message_review_claim": True,
        "external_review_identity": digest,
        "external_review_state": "zero-findings",
        "repository_review_state": "review-target-frozen",
        "schema_version": 1,
        "staged_identity": digest,
    })


@pytest.mark.parametrize(
    "value",
    [
        {
            "commit_message_review_claim": True,
            "external_review_identity": None,
            "external_review_state": "pending",
            "repository_review_state": "review-target-frozen",
            "schema_version": 1,
            "staged_identity": "a" * 64,
        },
        {
            "commit_message_review_claim": True,
            "external_review_identity": "b" * 64,
            "external_review_state": "zero-findings",
            "repository_review_state": "review-target-frozen",
            "schema_version": 1,
            "staged_identity": "a" * 64,
        },
    ],
)
def test_staged_review_sequence_rejects_pending_claims_and_tree_drift(value) -> None:
    with pytest.raises(ContractError):
        validate_review_sequence(value)


@pytest.mark.parametrize("invalid_version", [True, 1.0])
def test_staged_review_sequence_rejects_non_integer_schema_versions(invalid_version) -> None:
    with pytest.raises(ContractError):
        validate_review_sequence({
            "commit_message_review_claim": False,
            "external_review_identity": None,
            "external_review_state": "not-run",
            "repository_review_state": "review-target-frozen",
            "schema_version": invalid_version,
            "staged_identity": "a" * 64,
        })


def test_staged_review_sequence_rejects_pending_repository_state() -> None:
    with pytest.raises(ContractError):
        validate_review_sequence({
            "commit_message_review_claim": False,
            "external_review_identity": None,
            "external_review_state": "not-run",
            "repository_review_state": "pending",
            "schema_version": 1,
            "staged_identity": "a" * 64,
        })
