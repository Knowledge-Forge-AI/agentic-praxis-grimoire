#!/usr/bin/env python3
"""Mutation and navigation controls for the APG75 TypeScript candidate."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_typescript_candidate_contract import (  # noqa: E402
    ContractError,
    candidate_guard_failures,
    load_scenario_fixture,
    validate_candidate,
    validate_project_compiler_case,
    validate_scenario_fixture,
)


SCENARIO_PATH = ROOT / "src/test/fixtures/apg75-typescript-language-profile-scenarios.json"
FIXTURE = load_scenario_fixture(SCENARIO_PATH)
LEAF = (ROOT / "skills/typescript-language-profile/SKILL.md").read_text(encoding="utf-8")
SPECIFICATION = (ROOT / "docs/specs/typescript-language-profile.md").read_text(encoding="utf-8")
COVERAGE = (
    ROOT / "docs/specs/typescript-language-profile-scenario-coverage.md"
).read_text(encoding="utf-8")


def test_current_candidate_and_complete_oracle_projection_are_valid() -> None:
    validate_candidate(LEAF, SPECIFICATION, COVERAGE, expected_lifecycle="integrated")
    assert len(FIXTURE["rows"]) == 39
    assert candidate_guard_failures(
        LEAF, SPECIFICATION, expected_lifecycle="integrated"
    ) == []


def test_reusable_profile_consumes_project_selected_compiler_policy() -> None:
    profile = " ".join((LEAF + "\n" + SPECIFICATION).split()).lower()
    for marker in (
        "exact project-selected compiler role and version",
        "TypeScript 5.x, 6.x, 7.x, or another exact supported line",
        "does not choose a destination generation",
        "does not label an older compiler a migration baseline",
        "compiler migration routes to project-design and compiler-configuration owners",
    ):
        assert marker.lower() in profile
    assert "any older compiler in a live target is migration baseline evidence, never the destination" not in profile
    assert "TypeScript 7 is the intended primary compiler generation" not in profile

    target = next(row for row in FIXTURE["rows"] if row["id"] == "APG75-TARGET-001")
    assert "TS7 destination" in " ".join(target["present_evidence"])
    assert "migration baseline" in target["owned_conclusion"]


@pytest.mark.parametrize(
    "case",
    [
        {
            "compiler_version": "5.9.3",
            "expected_analysis_version": "5.9.3",
            "migration_verdict": None,
            "project_policy": "5.9.3 is the current selected line",
            "question": "TypeScript-specific static semantics",
            "role": "exact current CLI checker",
        },
        {
            "compiler_version": "6.0.3",
            "expected_analysis_version": "6.0.3",
            "migration_verdict": None,
            "project_policy": "TypeScript 6 is the current primary compiler",
            "question": "static behavior under exact options",
            "role": "exact current CLI checker",
        },
    ],
)
def test_exact_supported_project_compilers_do_not_imply_migration(
    case: dict[str, object],
) -> None:
    validate_project_compiler_case(case)
    profile = " ".join((LEAF + "\n" + SPECIFICATION).split()).lower()
    assert "does not choose a destination generation" in profile
    assert "does not label an older compiler a migration baseline" in profile

    wrong_version = deepcopy(case)
    wrong_version["expected_analysis_version"] = "7.0.2"
    with pytest.raises(ContractError, match="exact project compiler"):
        validate_project_compiler_case(wrong_version)

    automatic_migration = deepcopy(case)
    automatic_migration["migration_verdict"] = "migrate-to-7"
    with pytest.raises(ContractError, match="migration verdict"):
        validate_project_compiler_case(automatic_migration)


def test_selection_and_response_vocabularies_are_exact_and_disjoint() -> None:
    assert FIXTURE["vocabulary"]["responses"] == [
        "proceed-routine",
        "inspect-before-judgment",
        "bounded-local-decision",
        "stop-and-escalate",
    ]
    assert not (
        set(FIXTURE["vocabulary"]["selections"])
        & set(FIXTURE["vocabulary"]["responses"])
    )
    compatibility = next(
        row for row in FIXTURE["rows"] if row["id"] == "APG74-FX-010"
    )
    assert compatibility["typescript_selection"] == "non-trigger"
    assert compatibility["response"] == "proceed-routine"
    assert compatibility["routes_or_obligations"] == ["host-owner", "package-owner"]
    routed_stop = next(
        row for row in FIXTURE["rows"] if row["id"] == "APG75-TARGET-001"
    )
    assert routed_stop["typescript_selection"] == "route-to-owner"
    assert routed_stop["response"] == "stop-and-escalate"


def test_response_axis_mutations_fail_closed() -> None:
    response_as_selection = deepcopy(FIXTURE)
    row = next(
        item for item in response_as_selection["rows"] if item["id"] == "APG74-FX-010"
    )
    row["response"] = "route-to-owner"
    with pytest.raises(ContractError, match="unknown response"):
        validate_scenario_fixture(response_as_selection)

    fifth_response = deepcopy(FIXTURE)
    fifth_response["vocabulary"]["responses"].append("route-to-owner")
    with pytest.raises(ContractError, match="vocabulary"):
        validate_scenario_fixture(fifth_response)


def test_scenario_024_is_project_neutral_while_target_intent_remains_specific() -> None:
    scenario = next(row for row in FIXTURE["rows"] if row["id"] == "APG74-TS-024")
    assert scenario["fact_summary"] == (
        "project-selected primary compiler role plus conditional compatibility role"
    )
    assert "TS7 remains destination" not in scenario["owned_conclusion"]
    target = next(row for row in FIXTURE["rows"] if row["id"] == "APG75-TARGET-001")
    assert "TS7 destination" in " ".join(target["present_evidence"])


def test_scenario_fixture_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}\n', encoding="utf-8")
    with pytest.raises(ContractError, match="duplicate JSON key"):
        load_scenario_fixture(path)


@pytest.mark.parametrize("case_id", ["APG74-TS-020", "APG74-TS-021", "APG74-FX-006", "APG74-FX-008"])
def test_embedded_owner_cannot_be_replaced_by_typescript(case_id: str) -> None:
    mutated = deepcopy(FIXTURE)
    row = next(row for row in mutated["rows"] if row["id"] == case_id)
    row["typescript_selection"] = "selected"
    with pytest.raises(ContractError, match="preserve its non-TypeScript whole-file owner"):
        validate_scenario_fixture(mutated)


def test_unknown_evidence_cannot_become_an_invented_role() -> None:
    mutated = deepcopy(FIXTURE)
    row = next(row for row in mutated["rows"] if row["id"] == "APG74-TS-014")
    row["required_roles"] = ["cli-checker"]
    with pytest.raises(ContractError, match="unknown role case invents"):
        validate_scenario_fixture(mutated)


def test_present_evidence_cannot_satisfy_required_evidence_by_copy() -> None:
    mutated = deepcopy(FIXTURE)
    row = mutated["rows"][0]
    row["required_evidence"] = [row["present_evidence"][0]]
    with pytest.raises(ContractError, match="copies present evidence"):
        validate_scenario_fixture(mutated)


def test_option_fact_requires_an_explicit_value() -> None:
    mutated = deepcopy(FIXTURE)
    mutated["rows"][0]["required_option_facts"] = ["strict"]
    with pytest.raises(ContractError, match="option name without a value"):
        validate_scenario_fixture(mutated)


def test_unknown_role_case_must_stop_or_route() -> None:
    mutated = deepcopy(FIXTURE)
    row = next(row for row in mutated["rows"] if row["id"] == "APG74-TS-014")
    row["response"] = "proceed-routine"
    row["routes_or_obligations"] = []
    with pytest.raises(ContractError, match="must stop on unknown evidence"):
        validate_scenario_fixture(mutated)


def test_target_scenario_preserves_migration_truth() -> None:
    row = next(row for row in FIXTURE["rows"] if row["id"] == "APG75-TARGET-001")
    assert row["whole_file_owner"] == "per-artifact"
    assert row["response"] == "stop-and-escalate"
    assert "host-owner" in row["routes_or_obligations"]
    assert "package-owner" in row["routes_or_obligations"]
    assert "current embedded role excludes TS7" in row["owned_conclusion"]
    assert "runtime completion" in row["nonowned_conclusion"]


@pytest.mark.parametrize(
    "route",
    [
        "project-configuration",
        "package-owner",
        "host-owner",
        "declaration-provenance-owner",
        "runtime-owner",
    ],
)
def test_target_scenario_rejects_each_dropped_route(route: str) -> None:
    mutated = deepcopy(FIXTURE)
    row = next(row for row in mutated["rows"] if row["id"] == "APG75-TARGET-001")
    row["routes_or_obligations"].remove(route)
    with pytest.raises(ContractError, match="route set is incomplete"):
        validate_scenario_fixture(mutated)


@pytest.mark.parametrize(
    ("field", "replacement", "diagnostic"),
    [
        ("present_evidence", ["exact live object"], "present evidence"),
        ("required_evidence", ["declaration-emitter invocation"], "required evidence"),
        ("forbid", ["package presence proves role"], "negative controls"),
        ("required_roles", [], "embedded role"),
    ],
)
def test_target_scenario_rejects_incomplete_evidence_controls(
    field: str, replacement: list[str], diagnostic: str
) -> None:
    mutated = deepcopy(FIXTURE)
    row = next(row for row in mutated["rows"] if row["id"] == "APG75-TARGET-001")
    row[field] = replacement
    with pytest.raises(ContractError, match=diagnostic):
        validate_scenario_fixture(mutated)


@pytest.mark.parametrize("marker", ["current TS7 use", "runtime completion", "direct CLI role"])
def test_target_scenario_rejects_lost_nonowned_completion(marker: str) -> None:
    mutated = deepcopy(FIXTURE)
    row = next(row for row in mutated["rows"] if row["id"] == "APG75-TARGET-001")
    row["nonowned_conclusion"] = row["nonowned_conclusion"].replace(marker, "removed")
    with pytest.raises(ContractError, match="non-owned conclusion loses"):
        validate_scenario_fixture(mutated)


@pytest.mark.parametrize(
    ("old_marker", "diagnostic"),
    [
        ("small ordered set of routes or obligations", "ordered obligations"),
        ("no universal \"first matching signature\" shortcut", "overload specialization"),
        ("creates a compatibility/migration route", "migration route"),
    ],
)
def test_round_one_candidate_guard_mutations_fail(old_marker: str, diagnostic: str) -> None:
    combined = LEAF + "\n" + SPECIFICATION
    assert old_marker in " ".join(combined.split())
    expression = r"\s+".join(re.escape(part) for part in old_marker.split())
    mutated_leaf = re.sub(expression, "removed round-one correction", LEAF)
    mutated_spec = re.sub(expression, "removed round-one correction", SPECIFICATION)
    assert diagnostic in candidate_guard_failures(mutated_leaf, mutated_spec)


def test_old_singular_owner_claim_is_rejected() -> None:
    with pytest.raises(ContractError, match="singular receiving owner"):
        validate_candidate(
            LEAF + "\nUse one exact receiving owner.",
            SPECIFICATION,
            COVERAGE,
        )


def test_false_integration_marker_is_rejected_in_proposed_round() -> None:
    with pytest.raises(ContractError, match="false integration marker"):
        validate_candidate(
            LEAF + "\nStatus: provisionally-integrated\n",
            SPECIFICATION,
            COVERAGE,
        )


@pytest.mark.parametrize(
    ("mutated_leaf", "mutated_specification", "diagnostic"),
    [
        (
            LEAF.replace("Collapsing `.mts` and `.cts` into one source kind", "Collapsing source kinds"),
            SPECIFICATION,
            "source-kind distinction",
        ),
        (
            LEAF.replace("never hand-edited", "directly edited"),
            SPECIFICATION.replace("hand-edited", "directly edited"),
            "generated declaration edit refusal",
        ),
        (
            LEAF.replace("static success offered as runtime proof", "static success"),
            re.sub(
                r"Static\s+success\s+offered\s+as\s+runtime\s+proof",
                "Static success",
                SPECIFICATION,
            ),
            "static runtime refusal",
        ),
        (LEAF + "\nUse a 600 line band.\n", SPECIFICATION, "numeric structural band"),
        (
            LEAF + "\nAutomatic JavaScript migration is required.\n",
            SPECIFICATION,
            "automatic migration",
        ),
        (
            LEAF + "\nTypeScript 7 is the intended primary compiler generation.\n",
            SPECIFICATION,
            "universal TypeScript 7 destination",
        ),
        (
            LEAF + "\nAny older compiler in a live target is migration baseline evidence, never the destination.\n",
            SPECIFICATION,
            "universal older-compiler migration baseline",
        ),
        (
            LEAF + "\nAutomatic compiler migration is recommended.\n",
            SPECIFICATION,
            "automatic migration",
        ),
        (
            LEAF.replace("exact project-selected compiler role and version", "compiler"),
            SPECIFICATION.replace("exact project-selected compiler role and version", "compiler"),
            "project compiler authority",
        ),
    ],
)
def test_required_candidate_mutations_fail(
    mutated_leaf: str, mutated_specification: str, diagnostic: str
) -> None:
    with pytest.raises(ContractError, match=diagnostic):
        validate_candidate(
            mutated_leaf,
            mutated_specification,
            COVERAGE,
            expected_lifecycle="integrated",
        )


@pytest.mark.parametrize(
    "mutated",
    [
        COVERAGE.replace("ADR 0043: Accepted with amendment", "ADR 0043: Proposed"),
        COVERAGE + "\nAPG75: pending independent review.\n",
        COVERAGE.replace(
            "Current lifecycle: provisionally integrated after APG75 and APG75A",
            "Current lifecycle: APG75 pending independent review",
        ),
    ],
)
def test_coverage_lifecycle_mutations_fail(mutated: str) -> None:
    with pytest.raises(ContractError, match="coverage lifecycle"):
        validate_candidate(
            LEAF, SPECIFICATION, mutated, expected_lifecycle="integrated"
        )


@pytest.mark.parametrize(
    ("contradiction", "diagnostic"),
    [
        ("Use a 500 line structural band.", "numeric structural band"),
        ("Automatically perform JavaScript migration.", "automatic migration"),
        ("Generated declarations may be hand-edited.", "edit contradiction"),
        ("Static success proves runtime completion.", "runtime contradiction"),
        ("Collapse .mts and .cts into one source kind.", "source-kind contradiction"),
        ("Treat `.mts` and `.cts` as the same source kind.", "source-kind contradiction"),
    ],
)
def test_contradictory_permissions_fail_even_when_refusals_remain(
    contradiction: str, diagnostic: str
) -> None:
    with pytest.raises(ContractError, match=diagnostic):
        validate_candidate(LEAF + "\n" + contradiction, SPECIFICATION, COVERAGE)
