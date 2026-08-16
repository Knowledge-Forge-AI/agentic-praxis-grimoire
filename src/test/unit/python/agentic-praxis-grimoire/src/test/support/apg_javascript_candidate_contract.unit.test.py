#!/usr/bin/env python3
"""Mutation controls for the APG79 JavaScript candidate contract."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_javascript_candidate_contract import (  # noqa: E402
    ContractError,
    javascript_process_invocation_violations,
    load_test262_source_role,
    load_scenario_fixture,
    validate_candidate,
    validate_javascript_process_invocation_owners,
    validate_scenario_fixture,
    validate_test262_source_role,
)


SCENARIOS = ROOT / "src/test/fixtures/apg79-javascript-language-profile-scenarios.json"
TEST262_SOURCE_ROLE = ROOT / "private/evaluations/apg79d/test262-source-role.json"
PRIVATE_SOURCE_ROLE = pytest.mark.skipif(
    not TEST262_SOURCE_ROLE.is_file(),
    reason="publication-excluded Test262 source-role evidence is absent",
)


@PRIVATE_SOURCE_ROLE
def test_test262_source_role_is_closed_and_non_blocking_for_head_drift() -> None:
    source_role = load_test262_source_role(TEST262_SOURCE_ROLE)
    assert validate_test262_source_role(source_role) == {
        "corpus_use": False,
        "head_drift": "freshness-only-non-blocking",
        "normative": False,
        "rights": "unchanged",
    }

    advanced = deepcopy(source_role)
    advanced["fresh_head_observation"]["commit"] = "1" * 40
    advanced["fresh_head_observation"]["relation_to_historical_review_pin"] = (
        "advanced-from-historical-review-pin"
    )
    advanced["fresh_head_tree"] = "2" * 40
    assert validate_test262_source_role(advanced)["head_drift"] == (
        "freshness-only-non-blocking"
    )


@PRIVATE_SOURCE_ROLE
def test_test262_source_role_refuses_duplicate_and_noncanonical_json(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
    with pytest.raises(ContractError, match="duplicate JSON key"):
        load_test262_source_role(duplicate)

    noncanonical = tmp_path / "noncanonical.json"
    noncanonical.write_text(TEST262_SOURCE_ROLE.read_text().replace(":", ": ", 1))
    with pytest.raises(ContractError, match="not canonical"):
        load_test262_source_role(noncanonical)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("replace-historical-pin", "historical review pin"),
        ("omit-fresh-head", "schema"),
        ("promote-false-identity", "historical false identity"),
        ("omit-license-blob", "schema"),
        ("wrong-license-blob", "license blob"),
        ("normative", "normative authority"),
        ("semantic-oracle", "semantic oracle"),
        ("compatibility-oracle", "compatibility oracle"),
        ("implementation-authority", "implementation authority"),
        ("corpus-read", "corpus use"),
        ("corpus-copied", "corpus use"),
        ("corpus-executed", "corpus use"),
        ("corpus-vendored", "corpus use"),
        ("head-equality", "head equality"),
        ("head-drift-semantic", "refresh condition"),
        ("rights-harmless", "blocking change classes"),
        ("historical-report-rewritten", "historical false identity disposition"),
        ("raw-test-path", "schema"),
    ),
)
@PRIVATE_SOURCE_ROLE
def test_test262_source_role_mutations_fail_closed(mutation: str, message: str) -> None:
    source_role = load_test262_source_role(TEST262_SOURCE_ROLE)
    mutated = deepcopy(source_role)
    if mutation == "replace-historical-pin":
        mutated["fresh_head_observation"]["commit"] = "1" * 40
        mutated["historical_review_pin"] = mutated["fresh_head_observation"]["commit"]
    elif mutation == "omit-fresh-head":
        del mutated["fresh_head_observation"]
    elif mutation == "promote-false-identity":
        mutated["current_authority"] = mutated["historical_false_identity"]
    elif mutation == "omit-license-blob":
        del mutated["license_blob"]
    elif mutation == "wrong-license-blob":
        mutated["license_blob"] = "0" * 40
    elif mutation == "normative":
        mutated["normative_authority"] = True
    elif mutation == "semantic-oracle":
        mutated["semantic_oracle"] = True
    elif mutation == "compatibility-oracle":
        mutated["compatibility_oracle"] = True
    elif mutation == "implementation-authority":
        mutated["implementation_authority"] = True
    elif mutation == "corpus-read":
        mutated["corpus_read"] = True
    elif mutation == "corpus-copied":
        mutated["corpus_copied"] = True
    elif mutation == "corpus-executed":
        mutated["corpus_executed"] = True
    elif mutation == "corpus-vendored":
        mutated["corpus_vendored"] = True
    elif mutation == "head-equality":
        mutated["head_equality_required"] = True
    elif mutation == "head-drift-semantic":
        mutated["refresh_condition"] = "main-head drift is a semantic change"
    elif mutation == "rights-harmless":
        mutated["blocking_change_classes"] = ["corpus-use-change"]
    elif mutation == "historical-report-rewritten":
        mutated["historical_false_identity_disposition"] = "historical report rewritten"
    elif mutation == "raw-test-path":
        mutated["test_path"] = "test/language/example.js"
    with pytest.raises(ContractError, match=message):
        validate_test262_source_role(mutated)


def test_corrected_candidate_and_independent_scenarios_are_valid() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    validate_candidate(
        (ROOT / "skills/javascript-language-profile/SKILL.md").read_text(encoding="utf-8"),
        (ROOT / "docs/specs/javascript-language-profile.md").read_text(encoding="utf-8"),
        (ROOT / "docs/specs/javascript-language-profile-scenario-coverage.md").read_text(encoding="utf-8"),
        integrated=True,
    )
    assert len(fixture["rows"]) == 41


def test_selection_response_and_goal_axes_fail_closed() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    response = deepcopy(fixture)
    response["rows"][0]["response"] = "route-to-owner"
    with pytest.raises(ContractError, match="unknown response"):
        validate_scenario_fixture(response)
    goal = deepcopy(fixture)
    goal["rows"][0]["parse_goal"] = "host-wrapper"
    with pytest.raises(ContractError, match="invalid parse goal"):
        validate_scenario_fixture(goal)


def test_duplicate_json_keys_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}\n', encoding="utf-8")
    with pytest.raises(ContractError, match="duplicate JSON key"):
        load_scenario_fixture(path)


def test_present_evidence_cannot_copy_required_evidence() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    mutated["rows"][0]["required_evidence"] = [mutated["rows"][0]["present_evidence"][0]]
    with pytest.raises(ContractError, match="copies present evidence"):
        validate_scenario_fixture(mutated)


def test_absent_receiver_cannot_claim_completion() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    row = next(item for item in mutated["rows"] if item["id"] == "APG78-JS-023")
    row["response"] = "proceed-routine"
    with pytest.raises(ContractError, match="completion state|absent receivers"):
        validate_scenario_fixture(mutated)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("host_context", "function-body", "invalid host context"),
        ("language_contexts", ["runtime-wrapper"], "invalid language context"),
        ("goal_state", "assumed", "invalid goal state"),
        ("strictness", "probably-strict", "invalid strictness state"),
        ("javascript_selection", "selected-by-default", "unknown selection"),
        ("host_role_state", "present", "invalid host role state"),
        ("qualification_engine_state", "passed", "invalid qualification state"),
        ("artifact_class", "bogus-class", "invalid artifact class"),
        ("whole_file_owner", "bogus-owner", "invalid whole-file owner"),
    ),
)
def test_consequence_bearing_scenario_fields_are_closed(
    field: str, value: object, message: str
) -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    mutated["rows"][0][field] = value
    with pytest.raises(ContractError, match=message):
        validate_scenario_fixture(mutated)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("artifact_class", "module-control"),
        ("whole_file_owner", "javascript-language-profile"),
        ("parse_goal", "module"),
        ("host_context", "standalone"),
        ("language_contexts", ["module-body"]),
        ("goal_state", "known"),
        ("strictness", "strict"),
        ("javascript_selection", "selected"),
        ("host_role_state", "known"),
        ("qualification_engine_state", "not-required"),
        ("response", "bounded-local-decision"),
    ),
)
def test_aggregate_variant_cannot_invent_a_shared_state(field: str, value: object) -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    row = next(item for item in mutated["rows"] if item["id"] == "APG78-JS-005")
    row[field] = value
    with pytest.raises(ContractError, match="invents a shared state"):
        validate_scenario_fixture(mutated)


def test_route_requires_an_exact_owner_and_decision_scope() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    mutated["rows"][0]["routes_or_obligations"] = ["inspect runtime"]
    with pytest.raises(ContractError, match="exact owner and decision scope"):
        validate_scenario_fixture(mutated)


def test_astro_intended_module_cannot_become_observed_parse_goal() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    target = next(item for item in mutated["rows"] if item["id"] == "APG79-TARGET-002")
    target["parse_goal"] = "module"
    target["goal_state"] = "known"
    target["strictness"] = "strict"
    with pytest.raises(ContractError, match="promotes intended processing"):
        validate_scenario_fixture(mutated)


def test_checked_target_owner_is_exact() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    target = next(item for item in fixture["rows"] if item["id"] == "APG79-TARGET-001")
    assert target["whole_file_owner"] == "project-configuration-owner"
    assert target["javascript_selection"] == "selected"
    mutated = deepcopy(fixture)
    changed = next(item for item in mutated["rows"] if item["id"] == "APG79-TARGET-001")
    changed["javascript_selection"] = "embedded-route"
    with pytest.raises(ContractError, match="owner, region selection"):
        validate_scenario_fixture(mutated)


def test_embedded_route_is_reserved_for_nested_host_regions() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    rows = {row["id"]: row for row in fixture["rows"]}
    assert rows["APG78-FX-011"]["javascript_selection"] == "selected"
    cli = next(
        variant
        for variant in rows["APG78-FX-014"]["variants"]
        if variant["label"] == "commonjs-node-adapter"
    )
    assert cli["javascript_selection"] == "selected"
    targets = {row["id"]: row for row in fixture["rows"][-3:]}
    assert targets["APG79-TARGET-001"]["javascript_selection"] == "selected"
    assert targets["APG79-TARGET-002"]["javascript_selection"] == "embedded-route"
    assert targets["APG79-TARGET-003"]["javascript_selection"] == "embedded-route"
    assert targets["APG79-TARGET-002"]["whole_file_owner"] == "astro-host-owner"
    assert targets["APG79-TARGET-003"]["whole_file_owner"] == "astro-host-owner"
    for row_id, vector_label in (("APG78-FX-011", None), ("APG78-FX-014", "commonjs-node-adapter")):
        mutated = deepcopy(fixture)
        row = next(item for item in mutated["rows"] if item["id"] == row_id)
        vector = (
            row
            if vector_label is None
            else next(item for item in row["variants"] if item["label"] == vector_label)
        )
        vector["javascript_selection"] = "embedded-route"
        with pytest.raises(ContractError, match="decision-scoped JavaScript Selection"):
            validate_scenario_fixture(mutated)


def test_authority_source_lifecycle_provenance_and_completion_are_closed() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    authority = deepcopy(fixture)
    authority["rows"][0]["authority_ids"] = ["ecma262-es2026", "invented-authority"]
    with pytest.raises(ContractError, match="authority IDs"):
        validate_scenario_fixture(authority)
    source = deepcopy(fixture)
    source["rows"][0]["source_binding_id"], source["rows"][1]["source_binding_id"] = (
        source["rows"][1]["source_binding_id"], source["rows"][0]["source_binding_id"]
    )
    with pytest.raises(ContractError, match="source binding"):
        validate_scenario_fixture(source)
    lifecycle = deepcopy(fixture)
    lifecycle["rows"][0]["lifecycle_state"] = "repair-required-after-apg79b"
    with pytest.raises(ContractError, match="lifecycle state"):
        validate_scenario_fixture(lifecycle)
    provenance = deepcopy(fixture)
    provenance["rows"][-1]["edit_permission"] = "apg-maintainer-editable"
    with pytest.raises(ContractError, match="edit permission"):
        validate_scenario_fixture(provenance)
    completion = deepcopy(fixture)
    completion["rows"][22]["completion_state"] = "owned-complete"
    with pytest.raises(ContractError, match="completion state"):
        validate_scenario_fixture(completion)


def test_owned_and_nonowned_conclusion_ids_cannot_be_invented_or_swapped() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    invented = deepcopy(fixture)
    invented["rows"][0]["owned_conclusion_id"] = "owned::invented"
    with pytest.raises(ContractError, match="owned conclusion ID"):
        validate_scenario_fixture(invented)
    swapped = deepcopy(fixture)
    swapped["rows"][0]["owned_conclusion_id"], swapped["rows"][1]["owned_conclusion_id"] = (
        swapped["rows"][1]["owned_conclusion_id"], swapped["rows"][0]["owned_conclusion_id"]
    )
    with pytest.raises(ContractError, match="owned conclusion ID"):
        validate_scenario_fixture(swapped)


def test_exact_variant_set_cannot_be_duplicated() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    row = next(item for item in mutated["rows"] if item["id"] == "APG78-JS-005")
    row["variants"] = [deepcopy(row["variants"][0]) for _ in range(3)]
    with pytest.raises(ContractError, match="loses an exact variant"):
        validate_scenario_fixture(mutated)


def test_module_vector_must_be_strict() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    mutated["rows"][0]["strictness"] = "non-strict"
    with pytest.raises(ContractError, match="Module vector is not strict"):
        validate_scenario_fixture(mutated)


def test_target_commitment_is_exact() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    mutated["rows"][-1]["target_binding_commitment"] = "0" * 64
    with pytest.raises(ContractError, match="not bound to exact retained evidence"):
        validate_scenario_fixture(mutated)


@pytest.mark.parametrize("row_id", ["APG78-JS-001", "APG78-FX-001"])
def test_target_binding_commitment_is_forbidden_on_non_target_rows(row_id: str) -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    mutated = deepcopy(fixture)
    next(row for row in mutated["rows"] if row["id"] == row_id)[
        "target_binding_commitment"
    ] = "0" * 64
    with pytest.raises(ContractError, match="row class"):
        validate_scenario_fixture(mutated)


def test_target_rows_require_distinct_exact_commitments() -> None:
    fixture = load_scenario_fixture(SCENARIOS)
    missing = deepcopy(fixture)
    del missing["rows"][-1]["target_binding_commitment"]
    with pytest.raises(ContractError, match="row class"):
        validate_scenario_fixture(missing)
    copied = deepcopy(fixture)
    copied["rows"][-1]["target_binding_commitment"] = copied["rows"][-2][
        "target_binding_commitment"
    ]
    with pytest.raises(ContractError, match="exact retained evidence"):
        validate_scenario_fixture(copied)


def test_semantic_helpers_cannot_bypass_the_bound_invocation_owner() -> None:
    validate_javascript_process_invocation_owners(ROOT)


@pytest.mark.parametrize(
    "source",
    [
        "import subprocess as sp\nsp.run(['node'])\n",
        "from subprocess import run as execute\nexecute(['node'])\n",
        "from subprocess import Popen\nPopen(['node'])\n",
        "import subprocess\nalias = subprocess.run\nalias(['node'])\n",
        "import subprocess as sp\nalias = sp.run\nalias(['node'])\n",
        "import subprocess\nsubprocess.call(['node'])\n",
        "import subprocess\nsubprocess.check_call(['node'])\n",
        "import subprocess\nsubprocess.check_output(['node'])\n",
        "import os\nos.system('node')\n",
        "import os\nos.popen('node')\n",
        "import os\nos.spawnv(0, 'node', ['node'])\n",
        "import asyncio\nasyncio.create_subprocess_exec('node')\n",
        "import asyncio\nasyncio.create_subprocess_shell('node')\n",
        "import multiprocessing\nmultiprocessing.Process(target=print).start()\n",
        "__import__('subprocess').run(['node'])\n",
        "import subprocess\ngetattr(subprocess, 'run')(['node'])\n",
    ],
)
def test_named_process_alias_and_alternate_forms_are_rejected(source: str) -> None:
    assert javascript_process_invocation_violations(source)


def test_harmless_run_word_is_not_a_process_bypass() -> None:
    assert javascript_process_invocation_violations("run = 'ordinary word'\n") == ()
