#!/usr/bin/env python3
"""Unit contracts for the extracted APG60C lifecycle schema."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_surface_contract import (  # noqa: E402
    SurfaceContractError,
    load_removal_plan,
)


PLAN_PATH = ROOT / "src/test/fixtures/apg60-css-removal-plan.json"
PLAN = load_removal_plan(PLAN_PATH, root=ROOT)


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        (
            "actual_lifecycle",
            "integrated_count",
            29,
            "actual lifecycle",
        ),
        (
            "narrative_state",
            "human_review",
            "not-required",
            "narrative-state",
        ),
        (
            "python_source_binding",
            "collection",
            "mutable",
            "source-binding",
        ),
        (
            "python_source_binding",
            "runtime_value_authority",
            "runtime-finality",
            "source-binding",
        ),
        (
            "python_source_binding",
            "proof_scope",
            "unproven calls fail closed",
            "source-binding",
        ),
        (
            "python_source_binding",
            "arbitrary_caller_mutation_scope",
            "prevented",
            "source-binding",
        ),
    ],
)
def test_extracted_schema_rejects_contract_drift(
    section: str,
    key: str,
    value: object,
    message: str,
) -> None:
    plan = deepcopy(PLAN)
    plan["closure_contracts"][section][key] = value
    with pytest.raises(SurfaceContractError, match=message):
        load_removal_plan(PLAN_PATH, value=plan)


def test_extracted_schema_accepts_the_canonical_plan() -> None:
    assert load_removal_plan(PLAN_PATH, root=ROOT) == PLAN


def test_history_authority_cannot_be_substituted() -> None:
    plan = deepcopy(PLAN)
    plan["closure_contracts"]["actual_lifecycle"]["authoring_history"] = [
        "APG60D"
    ]
    with pytest.raises(SurfaceContractError, match="contract-exact"):
        load_removal_plan(PLAN_PATH, value=plan)


def test_phase_history_manifest_is_apg60i_exact() -> None:
    lifecycle = PLAN["closure_contracts"]["actual_lifecycle"]
    assert lifecycle["foundation_history"][-1] == "APG60I"
    assert lifecycle["phase_history_manifest"] == (
        "src/test/fixtures/apg60i-css-phase-history.json"
    )
