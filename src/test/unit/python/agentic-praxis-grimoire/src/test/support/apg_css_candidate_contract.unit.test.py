#!/usr/bin/env python3
"""Unit contracts for the frozen APG60 CSS pre-authoring oracle."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_css_candidate_contract import (  # noqa: E402
    ACTION_VOCABULARY,
    ContractError,
    assert_case_expected,
    canonical_contract_bytes,
    classify_growth,
    count_nonblank_css,
    evaluate_case,
    governing_growth,
    load_contract,
    validate_collected_case_ids,
    validate_contract,
)


CONTRACT_PATH = ROOT / "src/test/fixtures/apg60-css-reentry-contract.json"
PHRASE_PATH = ROOT / "src/test/fixtures/apg60-css-phrase-only-control.md"
CONTRACT = load_contract(CONTRACT_PATH, ROOT)
CASES = CONTRACT["cases"]


def _growth_case(
    operation: str,
    projected_count: int,
    actual_count: int,
) -> dict[str, object]:
    case = deepcopy(CASES[4])
    case.update(
        {
            "actual_count": actual_count,
            "authority": "general-default",
            "baseline_count": projected_count,
            "current_count": projected_count,
            "exception_grant_source": None,
            "family": "growth-transition",
            "operation": operation,
            "projected_count": projected_count,
            "semantic_facts": [],
        }
    )
    case["input"] = {
        "control": "projection-overrun-matrix",
        "parts": ["bounded-change"],
        "responsibility": "bounded-change",
    }
    return case


def test_exact_ids_families_operations_and_source_labels() -> None:
    assert [case["id"] for case in CASES] == [
        f"APG60-CSS-{number:03d}" for number in range(1, 61)
    ]
    assert Counter(case["family"] for case in CASES) == {
        "growth-transition": 8,
        "task-aggregation": 10,
        "authority": 8,
        "semantic-owner": 10,
        "one-count-exclusions": 12,
        "legacy-exception": 6,
        "lifecycle-removal": 6,
    }
    assert {case["operation"] for case in CASES} == {
        "smallest-safe-correction",
        "material-new-behavior",
        "decomposition-or-removal",
        "non-growing-documentation",
    }
    assert "rejected evidence" in CONTRACT["status"]
    assert "not active guidance" in CONTRACT["status"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_all_sixty_cases_match_exact_frozen_behavior(case: dict[str, object]) -> None:
    assert evaluate_case(case) == case["expected"]
    assert_case_expected(case)


def test_numeric_edges_highest_state_and_projection_overrun() -> None:
    assert [classify_growth(value) for value in (299, 300, 599, 600, 899, 900)] == [
        "Green",
        "Yellow",
        "Yellow",
        "Orange",
        "Orange",
        "Red",
    ]
    assert governing_growth(600, 600, 595, 595) == ("Orange", "current")
    assert governing_growth(299, 299, 300, None) == ("Yellow", "projected")
    overrun = next(case for case in CASES if case["id"] == "APG60-CSS-008")
    assert evaluate_case(overrun)["required_actions"] == [
        "record-growth-state",
        "rollback",
        "stop-and-reauthorize",
    ]


@pytest.mark.parametrize(
    ("operation", "projected_count", "actual_count", "expected_forbidden"),
    (
        ("material-new-behavior", 899, 901, {"unplanned-material-growth"}),
        (
            "smallest-safe-correction",
            899,
            901,
            {"feature-as-correction", "unplanned-material-growth"},
        ),
        (
            "decomposition-or-removal",
            700,
            905,
            {"unplanned-material-growth"},
        ),
        (
            "non-growing-documentation",
            299,
            300,
            {"feature-as-correction", "unplanned-material-growth"},
        ),
        (
            "smallest-safe-correction",
            310,
            320,
            {"feature-as-correction", "unplanned-material-growth"},
        ),
    ),
)
def test_projection_overrun_stops_before_every_operation_specific_success(
    operation: str,
    projected_count: int,
    actual_count: int,
    expected_forbidden: set[str],
) -> None:
    result = evaluate_case(_growth_case(operation, projected_count, actual_count))
    assert result["permitted"] is False
    assert result["required_actions"] == [
        "record-growth-state",
        "rollback",
        "stop-and-reauthorize",
    ]
    assert set(result["forbidden_actions"]) == expected_forbidden
    assert result["rollback"] is True


@pytest.mark.parametrize(("projected_count", "actual_count"), ((310, 310), (310, 309)))
def test_equal_or_below_projection_is_not_an_overrun(
    projected_count: int, actual_count: int
) -> None:
    result = evaluate_case(
        _growth_case("material-new-behavior", projected_count, actual_count)
    )
    assert "stop-and-reauthorize" not in result["required_actions"]
    assert result["permitted"] is True


def test_artifact_exception_inherits_repository_or_human_grant_source() -> None:
    original = deepcopy(next(case for case in CASES if case["id"] == "APG60-CSS-024"))
    for grant_source in ("repository-policy", "human-instruction"):
        case = deepcopy(original)
        case["exception_grant_source"] = grant_source
        result = evaluate_case(case)
        assert result["selected_owner"] == grant_source
        assert result["permitted"] is True


@pytest.mark.parametrize("grant_source", (None, "incidental-convention"))
def test_artifact_exception_missing_or_unsupported_grant_source_fails_closed(
    grant_source: str | None,
) -> None:
    case = deepcopy(next(case for case in CASES if case["id"] == "APG60-CSS-024"))
    case["exception_grant_source"] = grant_source
    result = evaluate_case(case)
    assert result["permitted"] is False
    assert result["selected_owner"] != "artifact-exception"


def test_artifact_exception_scope_overrun_rolls_back_under_real_owner() -> None:
    case = deepcopy(next(case for case in CASES if case["id"] == "APG60-CSS-024"))
    case["exception_grant_source"] = "repository-policy"
    case["actual_count"] = case["projected_count"] + 1
    result = evaluate_case(case)
    assert result["selected_owner"] == "repository-policy"
    assert result["permitted"] is False
    assert result["rollback"] is True
    assert "exception-scope-overrun" in result["forbidden_actions"]
    assert "stop-and-reauthorize" in result["required_actions"]


def test_artifact_exception_never_becomes_an_authority_owner() -> None:
    assert all(
        evaluate_case(case)["selected_owner"] != "artifact-exception"
        for case in CASES
    )


def test_incidental_convention_cannot_grant_an_artifact_exception() -> None:
    case = deepcopy(next(case for case in CASES if case["id"] == "APG60-CSS-024"))
    case["authority"] = "incidental-weaker"
    case["exception_grant_source"] = "repository-policy"
    assert evaluate_case(case)["permitted"] is False


def test_repository_and_human_exception_sources_are_not_interchangeable() -> None:
    case = deepcopy(next(case for case in CASES if case["id"] == "APG60-CSS-024"))
    case["exception_grant_source"] = "repository-policy"
    assert evaluate_case(case)["selected_owner"] == "repository-policy"
    case["exception_grant_source"] = "human-instruction"
    case["actual_count"] = case["projected_count"] + 1
    result = evaluate_case(case)
    assert result["selected_owner"] == "human-instruction"
    assert result["permitted"] is False


def test_task_aggregation_controls_are_complete_and_behavioral() -> None:
    controls = {
        case["input"]["control"]
        for case in CASES
        if case["family"] == "task-aggregation"
    }
    assert {
        "multi-commit-one-feature",
        "baseline-reset-attempt",
        "feature-as-correction",
        "formatting-uncertainty",
        "generated-embedded-indirection",
        "cross-file-one-responsibility",
    } <= controls
    for case in CASES[8:18]:
        assert set(evaluate_case(case)["required_actions"]) or not case["expected"]["permitted"]


def test_authority_accessibility_and_custom_property_boundaries() -> None:
    by_id = {case["id"]: evaluate_case(case) for case in CASES}
    assert by_id["APG60-CSS-025"]["selected_owner"] == "repository-policy"
    assert not by_id["APG60-CSS-025"]["permitted"]
    assert "invent-accessibility-requirement" in by_id["APG60-CSS-028"]["forbidden_actions"]
    assert by_id["APG60-CSS-028"]["semantic_level"] != "Red"
    assert by_id["APG60-CSS-029"]["semantic_level"] == "Red"
    assert by_id["APG60-CSS-031"]["semantic_level"] == "Green"
    assert by_id["APG60-CSS-032"]["semantic_level"] == "Orange"
    assert by_id["APG60-CSS-033"]["selected_owner"] == "project-policy"


def test_one_count_and_every_exclusion_class() -> None:
    by_id = {case["id"]: evaluate_case(case) for case in CASES}
    assert by_id["APG60-CSS-037"]["growth_level"] == "Green"
    assert by_id["APG60-CSS-038"]["growth_level"] == "Green"
    for case_id in ("APG60-CSS-039", "APG60-CSS-040"):
        assert by_id[case_id]["growth_level"] == "NotApplicable"
        assert "additive-embedded-count" in by_id[case_id]["forbidden_actions"]
    exclusions = {
        item
        for case in CASES[40:48]
        for item in case["exclusions"]
    }
    assert exclusions == set(CONTRACT["counting"]["excluded"])
    assert all(evaluate_case(case)["growth_level"] == "Excluded" for case in CASES[40:48])


def test_counting_handles_bom_newlines_comments_and_final_segment() -> None:
    value = b"\xef\xbb\xbf/* comment */\r\n  \rbody{}\nlast"
    assert count_nonblank_css(value) == 3
    with pytest.raises(ContractError, match="UTF-8"):
        count_nonblank_css(b"\xff")


def test_phrase_only_text_cannot_satisfy_wrong_structured_result() -> None:
    text = PHRASE_PATH.read_text(encoding="utf-8")
    assert all(action in text for action in ACTION_VOCABULARY)
    wrong = deepcopy(CASES[2])
    wrong["expected"] = deepcopy(CASES[0]["expected"])
    with pytest.raises(ContractError, match="expected result"):
        assert_case_expected(wrong)


def test_partial_m2_collection_is_rejected(tmp_path: Path) -> None:
    partial = deepcopy(CONTRACT)
    partial["cases"] = [
        case for case in partial["cases"] if case["id"] != "APG60-CSS-009"
    ]
    disposable = tmp_path / "partial-contract.json"
    disposable.write_text(json.dumps(partial), encoding="utf-8")
    collected = [
        case["id"]
        for case in json.loads(disposable.read_text(encoding="utf-8"))["cases"]
    ]
    with pytest.raises(ContractError, match="collection"):
        validate_collected_case_ids(CONTRACT, collected)


def test_results_are_sorted_unique_and_deterministic() -> None:
    first = [evaluate_case(case) for case in CASES]
    second = [evaluate_case(case) for case in CASES]
    assert first == second
    for result in first:
        for field in ("required_actions", "forbidden_actions"):
            assert result[field] == sorted(set(result[field]))
