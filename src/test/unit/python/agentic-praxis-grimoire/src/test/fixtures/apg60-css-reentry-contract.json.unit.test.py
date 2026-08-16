#!/usr/bin/env python3
"""Mutation and closed-schema tests for the APG60 CSS contract fixture."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_css_candidate_contract import (  # noqa: E402
    ContractError,
    assert_case_expected,
    canonical_contract_bytes,
    evaluate_case,
    load_contract,
    validate_contract,
)


CONTRACT_PATH = ROOT / "src/test/fixtures/apg60-css-reentry-contract.json"
CONTRACT = load_contract(CONTRACT_PATH, ROOT)
CASES = CONTRACT["cases"]


def test_apg60a_schema_revision_and_supersession_are_closed() -> None:
    assert CONTRACT["schema_version"] == 2
    assert CONTRACT["contract_revision"] == "APG60A"
    assert CONTRACT["supersedes_contract_sha256"] == (
        "d0847c10577ed59336693093dbaf422ac9944a4ab1631833ebf328680c283858"
    )
    for field, replacement in (
        ("schema_version", 1),
        ("contract_revision", "APG60"),
        ("supersedes_contract_sha256", "0" * 64),
    ):
        changed = deepcopy(CONTRACT)
        changed[field] = replacement
        with pytest.raises(ContractError, match="schema|candidate"):
            validate_contract(changed)


def test_artifact_exception_grant_source_is_required_and_closed() -> None:
    case_index = next(
        index
        for index, case in enumerate(CASES)
        if case["id"] == "APG60-CSS-024"
    )
    for source in (None, "incidental-convention"):
        changed = deepcopy(CONTRACT)
        changed["cases"][case_index]["exception_grant_source"] = source
        with pytest.raises(ContractError, match="grant source"):
            validate_contract(changed)
    changed = deepcopy(CONTRACT)
    changed["cases"][0]["exception_grant_source"] = "repository-policy"
    with pytest.raises(ContractError, match="not applicable"):
        validate_contract(changed)


def test_closed_schema_unknown_keys_and_canonical_bytes() -> None:
    assert CONTRACT_PATH.read_bytes() == canonical_contract_bytes(CONTRACT)
    mutations = (
        ((), "extra"),
        (("policy",), "extra"),
        (("counting",), "extra"),
        (("cases", 0), "extra"),
        (("cases", 0, "input"), "extra"),
        (("cases", 0, "expected"), "extra"),
    )
    for path, key in mutations:
        value = deepcopy(CONTRACT)
        target = value
        for component in path:
            target = target[component]
        target[key] = True
        with pytest.raises(ContractError, match="unknown|schema"):
            validate_contract(value)


def test_structured_fields_not_control_labels_drive_behavior() -> None:
    mutations = (
        ("APG60-CSS-009", lambda case: case["input"].update(parts=["commit-1-20"])),
        (
            "APG60-CSS-010",
            lambda case: case["input"].update(
                parts=["tool-call-1", "tool-call-2"]
            ),
        ),
        (
            "APG60-CSS-010",
            lambda case: case["input"].update(
                parts=["conversation-turn-1", "conversation-turn-2"]
            ),
        ),
        ("APG60-CSS-010", lambda case: case.update(semantic_facts=[])),
        ("APG60-CSS-020", lambda case: case.update(authority="general-default")),
        ("APG60-CSS-027", lambda case: case.update(established_requirements=[])),
        (
            "APG60-CSS-032",
            lambda case: case.update(semantic_facts=["documented-root-token"]),
        ),
        (
            "APG60-CSS-052",
            lambda case: case.update(authority="missing-red-exception"),
        ),
        (
            "APG60-CSS-057",
            lambda case: case.update(semantic_facts=["rejected-state"]),
        ),
    )
    by_id = {case["id"]: case for case in CASES}
    for case_id, mutate in mutations:
        changed = deepcopy(by_id[case_id])
        mutate(changed)
        with pytest.raises(
            ContractError, match="expected result|baseline-reset-attempt"
        ):
            assert_case_expected(changed)


def test_control_labels_do_not_drive_structured_behavior() -> None:
    for case in CASES:
        changed = deepcopy(case)
        changed["input"]["control"] = "deliberately-misleading-label"
        assert evaluate_case(changed) == case["expected"]


def test_contract_loader_rejects_symlinked_fixture_ancestor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    external = tmp_path / "external-fixtures"
    external.mkdir()
    (external / CONTRACT_PATH.name).write_bytes(CONTRACT_PATH.read_bytes())
    fixtures = root / "src/test/fixtures"
    fixtures.parent.mkdir(parents=True)
    fixtures.symlink_to(external, target_is_directory=True)

    with pytest.raises(ContractError, match="direct|ancestor"):
        load_contract(fixtures / CONTRACT_PATH.name, root)
