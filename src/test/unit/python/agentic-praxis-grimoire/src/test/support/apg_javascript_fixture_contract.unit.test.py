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
    validate_commonjs_seam_invariant,
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


class DummyObservation:
    def __init__(
        self,
        return_code: int = 0,
        stdout_empty: bool = True,
        stderr_empty: bool = True,
        result: object = None,
        output_contract_id: str = "commonjs-boundary-syntax",
    ) -> None:
        self.output_contract_id = output_contract_id
        self.return_code = return_code
        self.stdout_empty = stdout_empty
        self.stderr_empty = stderr_empty
        self.result = result


@pytest.mark.parametrize(
    ("case_id", "case_index", "art_index", "field", "mutated_value", "error_match"),
    (
        # FX-011 (src/commonjs-boundary.cjs) artifact mutations
        ("APG78-FX-011", 10, 0, "whole_file_owner", "javascript-language-profile", "CommonJS whole-file owner is incorrect"),
        ("APG78-FX-011", 10, 0, "host_context", "standalone", "CommonJS host context must be commonjs-wrapper"),
        ("APG78-FX-011", 10, 0, "language_contexts", ["expression-region", "module-body"], "CommonJS language context must be expression-region"),
        ("APG78-FX-011", 10, 0, "parse_goal", "module", "parse goal"),
        ("APG78-FX-011", 10, 0, "goal_state", "known", "goal state"),
        ("APG78-FX-011", 10, 0, "host_role_state", "known", "CommonJS host role state must be unresolved"),
        ("APG78-FX-011", 10, 0, "goal_evidence_owner", "project-configuration-owner", "CommonJS goal evidence owner must be node-runtime-owner"),
        ("APG78-FX-011", 10, 0, "strictness_state", "strict", "CommonJS strictness state is incorrect"),
        ("APG78-FX-011", 10, 0, "qualification_engine_state", "observed-exact-engine", "CommonJS qualification engine state must be observed-syntax-only"),
        ("APG78-FX-011", 10, 0, "artifact_class", "handwritten-mjs", "CommonJS artifact class must be handwritten-cjs"),
        # FX-014 adapter (src/cli-node-adapter-boundary.cjs) artifact mutations
        ("APG78-FX-014", 13, 1, "whole_file_owner", "javascript-language-profile", "CLI CommonJS adapter whole-file owner is incorrect"),
        ("APG78-FX-014", 13, 1, "host_context", "standalone", "CLI CommonJS adapter host context must be commonjs-wrapper"),
        ("APG78-FX-014", 13, 1, "language_contexts", ["global-code"], "CLI CommonJS adapter language context must be expression-region"),
        ("APG78-FX-014", 13, 1, "parse_goal", "module", "parse goal"),
        ("APG78-FX-014", 13, 1, "goal_state", "known", "goal state"),
        ("APG78-FX-014", 13, 1, "host_role_state", "known", "CLI CommonJS adapter host role state must be unresolved"),
        ("APG78-FX-014", 13, 1, "goal_evidence_owner", "project-configuration-owner", "CLI CommonJS adapter goal evidence owner must be node-runtime-owner"),
        ("APG78-FX-014", 13, 1, "strictness_state", "strict", "CLI CommonJS adapter strictness state is incorrect"),
        ("APG78-FX-014", 13, 1, "qualification_engine_state", "observed-exact-engine", "CLI CommonJS adapter qualification engine state must be observed-syntax-only"),
        ("APG78-FX-014", 13, 1, "artifact_class", "handwritten-mjs", "CLI CommonJS adapter artifact class must be handwritten-cjs"),
    ),
)
def test_commonjs_seam_invariant_rejects_artifact_dimensions_in_manifest(
    case_id: str,
    case_index: int,
    art_index: int,
    field: str,
    mutated_value: object,
    error_match: str,
) -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(manifest)
    mutated["cases"][case_index]["artifacts"][art_index][field] = mutated_value
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(mutated, scenarios)
    with pytest.raises(ContractError):
        validate_manifest(mutated)


@pytest.mark.parametrize(
    ("case_index", "field", "mutated_value", "error_match"),
    (
        (10, "completion_state", "owned-complete", "CommonJS completion state must be stopped-required-evidence"),
        (10, "source_binding_id", "source::APG78-FX-001", "CommonJS source binding is not exact"),
        (10, "required_evidence", [], "CommonJS required evidence cannot be empty without Node owner"),
        (10, "routes_or_obligations", ["module-loader-owner::establish CommonJS resolution and loading"], "CommonJS must retain node-runtime-owner route"),
        (13, "completion_state", "owned-complete", "CLI CommonJS adapter completion state must be stopped-required-evidence"),
        (13, "source_binding_id", "source::APG78-FX-001", "CLI CommonJS adapter source binding is not exact"),
        (13, "required_evidence", [], "CLI CommonJS adapter required evidence cannot be empty without Node owner"),
        (13, "routes_or_obligations", ["module-loader-owner::resolve"], "CLI CommonJS adapter must retain node-runtime-owner route"),
    ),
)
def test_commonjs_seam_invariant_rejects_case_dimensions_in_manifest(
    case_index: int,
    field: str,
    mutated_value: object,
    error_match: str,
) -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(manifest)
    mutated["cases"][case_index][field] = mutated_value
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(mutated, scenarios)
    with pytest.raises(ContractError):
        validate_manifest(mutated)


def test_commonjs_seam_invariant_rejects_scenario_mutations() -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)

    # 1. FX-011 row response mutation
    mut = deepcopy(scenarios)
    row11 = next(r for r in mut["rows"] if r["id"] == "APG78-FX-011")
    row11["response"] = "bounded-local-decision"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(manifest, mut)

    # 2. FX-011 row whole_file_owner mutation
    mut = deepcopy(scenarios)
    row11 = next(r for r in mut["rows"] if r["id"] == "APG78-FX-011")
    row11["whole_file_owner"] = "javascript-language-profile"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(manifest, mut)

    # 3. FX-011 row completion_state mutation
    mut = deepcopy(scenarios)
    row11 = next(r for r in mut["rows"] if r["id"] == "APG78-FX-011")
    row11["completion_state"] = "owned-complete"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(manifest, mut)

    # 4. FX-011 row routes_or_obligations missing node-runtime-owner
    mut = deepcopy(scenarios)
    row11 = next(r for r in mut["rows"] if r["id"] == "APG78-FX-011")
    row11["routes_or_obligations"] = ["module-loader-owner::establish exact resolution and loading decision"]
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(manifest, mut)

    # 5. FX-014 adapter variant response mutation
    mut = deepcopy(scenarios)
    row14 = next(r for r in mut["rows"] if r["id"] == "APG78-FX-014")
    adapter_var = next(v for v in row14["variants"] if v["label"] == "commonjs-node-adapter")
    adapter_var["response"] = "proceed-routine"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(manifest, mut)

    # 6. FX-014 adapter variant whole_file_owner mutation
    mut = deepcopy(scenarios)
    row14 = next(r for r in mut["rows"] if r["id"] == "APG78-FX-014")
    adapter_var = next(v for v in row14["variants"] if v["label"] == "commonjs-node-adapter")
    adapter_var["whole_file_owner"] = "javascript-language-profile"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(manifest, mut)

    # 7. FX-014 row completion_state mutation
    mut = deepcopy(scenarios)
    row14 = next(r for r in mut["rows"] if r["id"] == "APG78-FX-014")
    row14["completion_state"] = "owned-complete"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(manifest, mut)


def test_commonjs_seam_invariant_rejects_coordinated_cross_surface_mutation() -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)

    # Coordinated mutation 1: whole_file_owner changed in both manifest and scenarios for FX-014 adapter
    mut_man = deepcopy(manifest)
    mut_scen = deepcopy(scenarios)
    mut_man["cases"][13]["artifacts"][1]["whole_file_owner"] = "javascript-language-profile"
    row14 = next(r for r in mut_scen["rows"] if r["id"] == "APG78-FX-014")
    adapter_var = next(v for v in row14["variants"] if v["label"] == "commonjs-node-adapter")
    adapter_var["whole_file_owner"] = "javascript-language-profile"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_fixture_projection(mut_man, mut_scen)

    # Coordinated mutation 2: host_context changed in both manifest and scenarios for FX-011
    mut_man2 = deepcopy(manifest)
    mut_scen2 = deepcopy(scenarios)
    mut_man2["cases"][10]["artifacts"][0]["host_context"] = "standalone"
    row11 = next(r for r in mut_scen2["rows"] if r["id"] == "APG78-FX-011")
    row11["host_context"] = "standalone"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_fixture_projection(mut_man2, mut_scen2)


def test_commonjs_seam_invariant_preserves_cli_effect_free_core() -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)

    # Manifest CLI core altered: whole_file_owner
    mut_man = deepcopy(manifest)
    mut_man["cases"][13]["artifacts"][0]["whole_file_owner"] = "node-commonjs-owner"
    with pytest.raises(ContractError, match="CLI effect-free core owner or boundary was altered"):
        validate_manifest(mut_man)

    # Manifest CLI core altered: parse_goal
    mut_man2 = deepcopy(manifest)
    mut_man2["cases"][13]["artifacts"][0]["parse_goal"] = "script"
    with pytest.raises(ContractError, match="CLI effect-free core owner or boundary was altered"):
        validate_manifest(mut_man2)

    # Scenario CLI core variant altered: response
    mut_scen = deepcopy(scenarios)
    row14 = next(r for r in mut_scen["rows"] if r["id"] == "APG78-FX-014")
    core_var = next(v for v in row14["variants"] if v["label"] == "effect-free-module-core")
    core_var["response"] = "stop-and-escalate"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(manifest, mut_scen)


def test_commonjs_seam_invariant_observations_and_node_availability() -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)

    valid_obs = {
        "commonjs-boundary-syntax": DummyObservation(return_code=0, stdout_empty=True, stderr_empty=True),
        "cli-commonjs-adapter-syntax": DummyObservation(output_contract_id="cli-commonjs-adapter-syntax", return_code=0, stdout_empty=True, stderr_empty=True),
    }
    # Valid baseline passes
    validate_commonjs_seam_invariant(manifest, scenarios, valid_obs)

    # Observation return_code != 0 rejected
    bad_rc = {
        "commonjs-boundary-syntax": DummyObservation(return_code=1, stdout_empty=True, stderr_empty=True),
        "cli-commonjs-adapter-syntax": DummyObservation(output_contract_id="cli-commonjs-adapter-syntax", return_code=0, stdout_empty=True, stderr_empty=True),
    }
    with pytest.raises(ContractError, match="return code must be 0"):
        validate_commonjs_seam_invariant(manifest, scenarios, bad_rc)

    # Observation non-empty stdout rejected
    bad_stdout = {
        "commonjs-boundary-syntax": DummyObservation(return_code=0, stdout_empty=False, stderr_empty=True),
        "cli-commonjs-adapter-syntax": DummyObservation(output_contract_id="cli-commonjs-adapter-syntax", return_code=0, stdout_empty=True, stderr_empty=True),
    }
    with pytest.raises(ContractError, match="must be syntax-only with empty streams"):
        validate_commonjs_seam_invariant(manifest, scenarios, bad_stdout)

    # Observation runtime execution result rejected
    bad_result = {
        "commonjs-boundary-syntax": DummyObservation(return_code=0, stdout_empty=True, stderr_empty=True, result={"executed": True}),
        "cli-commonjs-adapter-syntax": DummyObservation(output_contract_id="cli-commonjs-adapter-syntax", return_code=0, stdout_empty=True, stderr_empty=True),
    }
    with pytest.raises(ContractError, match="without runtime execution"):
        validate_commonjs_seam_invariant(manifest, scenarios, bad_result)

    # Node availability does NOT satisfy missing artifact facts
    mut_man = deepcopy(manifest)
    mut_man["cases"][10]["required_evidence"] = []
    with pytest.raises(ContractError, match="required_evidence mismatch"):
        validate_commonjs_seam_invariant(mut_man, scenarios, valid_obs)

    mut_man2 = deepcopy(manifest)
    mut_man2["cases"][13]["completion_state"] = "owned-complete"
    with pytest.raises(ContractError, match="CommonJS"):
        validate_commonjs_seam_invariant(mut_man2, scenarios, valid_obs)



@pytest.mark.parametrize("case_index", (10, 13))
@pytest.mark.parametrize("field", ("present_evidence", "required_evidence", "routes_or_obligations"))
@pytest.mark.parametrize("surface", ("manifest", "scenario", "both"))
def test_commonjs_exact_evidence_and_route_values(case_index, field, surface) -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)
    case = manifest["cases"][case_index]
    row = next(row for row in scenarios["rows"] if row["id"] == case["id"])
    # Remains nonempty and retains the Node owner prefix: only the value changes.
    for target in ([case] if surface == "manifest" else [row] if surface == "scenario" else [case, row]):
        target[field] = [target[field][0] + " changed decision"]
    with pytest.raises(ContractError, match=field):
        validate_commonjs_seam_invariant(manifest, scenarios)


@pytest.mark.parametrize("case_index,art_index", ((10, 0), (13, 1)))
@pytest.mark.parametrize("field,value", (("content_sha256", "0" * 64), ("scenario_variant", "other")))
def test_commonjs_exact_source_and_variant_identity(case_index, art_index, field, value) -> None:
    manifest = load_manifest(MANIFEST)
    scenarios = load_scenario_fixture(SCENARIOS)
    manifest["cases"][case_index]["artifacts"][art_index][field] = value
    with pytest.raises(ContractError, match="artifact vector"):
        validate_commonjs_seam_invariant(manifest, scenarios)


def test_commonjs_node_owner_is_bound_to_integrated_scenarios() -> None:
    from apg_javascript_fixture_contract import validate_commonjs_node_owner
    from apg_nodejs_candidate_contract import load_scenarios
    scenarios = load_scenarios(ROOT / "src/test/fixtures/apg81-nodejs-runtime-profile-scenarios.json")
    validate_commonjs_node_owner(scenarios)
    for owner_id in ("APG80-NODE-004", "APG80-NODE-006", "APG80-NODE-008"):
        mutated = deepcopy(scenarios)
        next(row for row in mutated["rows"] if row["id"] == owner_id)["whole_file_owner"] = "javascript-language-profile"
        with pytest.raises(ValueError):
            validate_commonjs_node_owner(mutated)
