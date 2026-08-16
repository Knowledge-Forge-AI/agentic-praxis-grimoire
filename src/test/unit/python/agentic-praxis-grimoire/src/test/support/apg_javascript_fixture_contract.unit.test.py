#!/usr/bin/env python3
"""Fail-closed controls for the APG79 JavaScript fixture contract."""

from __future__ import annotations

from copy import deepcopy
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_javascript_candidate_contract import (  # noqa: E402
    ContractError,
    load_scenario_fixture,
)
from apg_javascript_fixture_contract import (  # noqa: E402
    load_manifest,
    validate_fixture_projection,
    validate_manifest,
)


MANIFEST = ROOT / "src/test/fixtures/apg78-javascript-core/fixture-manifest.json"
SCENARIOS = ROOT / "src/test/fixtures/apg79-javascript-language-profile-scenarios.json"


def test_corrected_fixture_manifest_is_valid() -> None:
    value = load_manifest(MANIFEST)
    assert len(value["cases"]) == 14


def test_host_wrapper_cannot_become_a_parse_goal() -> None:
    value = load_manifest(MANIFEST)
    mutated = deepcopy(value)
    mutated["cases"][10]["artifacts"][0]["parse_goal"] = "host-wrapper"
    with pytest.raises(ContractError, match="invalid parse goal"):
        validate_manifest(mutated)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("host_context", "function-body", "invalid host context"),
        ("language_contexts", ["runtime-wrapper"], "invalid language context"),
        ("goal_state", "assumed", "invalid goal state"),
        ("strictness_state", "probably-strict", "invalid strictness state"),
        ("javascript_selection", "selected-by-default", "invalid JavaScript selection"),
        ("host_role_state", "present", "invalid host role state"),
        ("qualification_engine_state", "passed", "invalid qualification-engine state"),
        ("artifact_class", "bogus-class", "invalid artifact class"),
        ("whole_file_owner", "bogus-owner", "invalid whole-file owner"),
        ("goal_evidence_owner", "bogus-owner", "invalid goal-evidence owner"),
    ),
)
def test_consequence_bearing_artifact_fields_are_closed(
    field: str, value: object, message: str
) -> None:
    manifest = load_manifest(MANIFEST)
    mutated = deepcopy(manifest)
    mutated["cases"][0]["artifacts"][0][field] = value
    with pytest.raises(ContractError, match=message):
        validate_manifest(mutated)


def test_routes_require_an_exact_owner_and_decision_scope() -> None:
    manifest = load_manifest(MANIFEST)
    mutated = deepcopy(manifest)
    mutated["cases"][7]["routes_or_obligations"] = ["check runtime"]
    with pytest.raises(ContractError, match="exact owner and decision scope"):
        validate_manifest(mutated)


def test_manifest_and_case_schemas_are_closed() -> None:
    manifest = load_manifest(MANIFEST)
    top = deepcopy(manifest)
    top["unexpected"] = True
    with pytest.raises(ContractError, match="schema version 4"):
        validate_manifest(top)
    case = deepcopy(manifest)
    case["cases"][0]["unexpected"] = True
    with pytest.raises(ContractError, match="case schema"):
        validate_manifest(case)


def test_artifact_paths_are_exact_and_unique() -> None:
    manifest = load_manifest(MANIFEST)
    missing = deepcopy(manifest)
    missing["cases"][0]["artifacts"][0]["path"] = "missing/not-real.mjs"
    with pytest.raises(ContractError, match="artifact paths"):
        validate_manifest(missing)
    duplicate = deepcopy(manifest)
    duplicate["cases"][1]["artifacts"][0]["path"] = duplicate["cases"][0]["artifacts"][0]["path"]
    with pytest.raises(ContractError, match="artifact paths"):
        validate_manifest(duplicate)


def test_module_artifact_must_be_strict() -> None:
    manifest = load_manifest(MANIFEST)
    mutated = deepcopy(manifest)
    mutated["cases"][0]["artifacts"][0]["strictness_state"] = "non-strict"
    with pytest.raises(ContractError, match="Module artifact is not strict"):
        validate_manifest(mutated)


def test_case_evidence_is_disjoint() -> None:
    manifest = load_manifest(MANIFEST)
    mutated = deepcopy(manifest)
    mutated["cases"][0]["required_evidence"] = [mutated["cases"][0]["present_evidence"][0]]
    with pytest.raises(ContractError, match="copies present evidence"):
        validate_manifest(mutated)


def test_manifest_vector_must_project_exactly_to_scenario_variant() -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(manifest)
    case = next(item for item in mutated["cases"] if item["id"] == "APG78-FX-009")
    case["artifacts"][0]["host_role_state"] = "unresolved"
    with pytest.raises(ContractError, match="diverges at host_role_state"):
        validate_fixture_projection(mutated, scenarios)


def test_commonjs_cannot_become_javascript_whole_file_owned() -> None:
    value = load_manifest(MANIFEST)
    assert value["cases"][10]["artifacts"][0]["javascript_selection"] == "selected"
    assert value["cases"][13]["artifacts"][1]["javascript_selection"] == "selected"
    mutated = deepcopy(value)
    mutated["cases"][10]["artifacts"][0]["whole_file_owner"] = "javascript-language-profile"
    with pytest.raises(ContractError, match="CommonJS whole-file owner"):
        validate_manifest(mutated)
    for case_index, artifact_index in ((10, 0), (13, 1)):
        changed = deepcopy(value)
        changed["cases"][case_index]["artifacts"][artifact_index][
            "javascript_selection"
        ] = "embedded-route"
        with pytest.raises(ContractError, match="decision-scoped JavaScript Selection"):
            validate_manifest(changed)


def test_authoring_smoke_cannot_become_universal_engine_evidence() -> None:
    value = load_manifest(MANIFEST)
    mutated = deepcopy(value)
    mutated["cases"][0]["artifacts"][0]["qualification_engine_state"] = "known"
    with pytest.raises(ContractError, match="qualification-engine state"):
        validate_manifest(mutated)


def test_checked_directive_cannot_become_checker_invocation() -> None:
    value = load_manifest(MANIFEST)
    mutated = deepcopy(value)
    mutated["cases"][12]["typescript_checker_state"] = "invoked"
    with pytest.raises(ContractError, match="checker invocation"):
        validate_manifest(mutated)


def test_manifest_authority_source_lifecycle_provenance_and_conclusions_are_closed() -> None:
    value = load_manifest(MANIFEST)
    authority = deepcopy(value)
    authority["authority"]["normative_authority_ids"] = ["invented-authority"]
    with pytest.raises(ContractError, match="fixture authority"):
        validate_manifest(authority)
    source = deepcopy(value)
    source["cases"][0]["source_binding_id"], source["cases"][1]["source_binding_id"] = (
        source["cases"][1]["source_binding_id"], source["cases"][0]["source_binding_id"]
    )
    with pytest.raises(ContractError, match="source binding"):
        validate_manifest(source)
    lifecycle = deepcopy(value)
    del lifecycle["lifecycle"]["authored_by_phase_id"]
    with pytest.raises(ContractError, match="lifecycle"):
        validate_manifest(lifecycle)
    provenance = deepcopy(value)
    provenance["fixture"]["edit_permission"] = "read-only-no-copy-no-edit"
    with pytest.raises(ContractError, match="provenance or edit permission"):
        validate_manifest(provenance)
    conclusion = deepcopy(value)
    conclusion["cases"][0]["nonowned_conclusion_id"] = "nonowned::invented"
    with pytest.raises(ContractError, match="nonowned conclusion ID"):
        validate_manifest(conclusion)


def test_artifact_content_bindings_are_exact() -> None:
    value = load_manifest(MANIFEST)
    mutated = deepcopy(value)
    mutated["cases"][0]["artifacts"][0]["content_sha256"] = "0" * 64
    with pytest.raises(ContractError, match="content binding changed"):
        validate_manifest(mutated, fixture_root=MANIFEST.parent)
