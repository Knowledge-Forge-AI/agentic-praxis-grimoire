"""APG166E-CORR2 objective source-evidence review-oracle contracts."""
from __future__ import annotations

import copy

import pytest

from testing.h_eval import oracles, response_contract


_VALID_EVIDENCE = {
    "scenario-03": {
        "README.md": [{
            "source_path": "README.md",
            "span": {"start": 3, "end": 3},
            "snippet": "See the [architecture document](docs/missing.md).",
        }],
        "docs/architecture.md": [{
            "source_path": "docs/architecture.md",
            "span": {"start": 1, "end": 2},
            "snippet": (
                "## Architecture overview\n"
                "The service reads configuration at startup and serves requests from a shared worker pool."
            ),
        }],
    },
    "scenario-11": {
        "pkg/api/client.go": [{
            "source_path": "pkg/api/client.go",
            "span": {"start": 7, "end": 7},
            "snippet": "    return nil, nil",
        }],
    },
    "scenario-12": {
        "pkg/service/service.go": [{
            "source_path": "pkg/service/service.go",
            "span": {"start": 6, "end": 6},
            "snippet": 'func (Service) Name() string { return "fixture" }',
        }],
    },
    "scenario-14": {
        "pkg/data/models.go": [{
            "source_path": "pkg/data/models.go",
            "span": {"start": 5, "end": 6},
            "snippet": "    ID   int\n    Name string",
        }],
    },
}


def _response(scenario_id: str, *, categories: dict[str, str] | None = None) -> dict[str, object]:
    categories = categories or {}
    findings = []
    for path in sorted(oracles._REVIEW_REQUIRED_PATHS[scenario_id]):
        findings.append({
            "path": path,
            "category": categories.get(path, "observation"),
            "summary": f"Finding summary for {path}; wording is descriptive.",
            "evidence": copy.deepcopy(_VALID_EVIDENCE[scenario_id][path]),
        })
    return {
        "schema": "apg.h-evaluation-response/v1",
        "scenario_id": scenario_id,
        "summary": "The source facts were checked.",
        "findings": findings,
        "limitations": [],
    }


@pytest.mark.parametrize("scenario_id", sorted(_VALID_EVIDENCE))
def test_correct_objective_facts_accept_arbitrary_summary_and_category(scenario_id: str) -> None:
    paths = sorted(oracles._REVIEW_REQUIRED_PATHS[scenario_id])
    categories = {
        path: category
        for path, category in zip(
            paths,
            ("documentation-link", "layout-note", "api-contract", "constant-observation", "field-types"),
        )
    }
    accepted, facts = oracles._review_check(
        scenario_id, {"review_response": _response(scenario_id, categories=categories)}, {}
    )
    assert accepted is True, facts
    assert all(item["matches"] is True for item in facts["semantic_facts"])


def test_objective_claims_are_independent_of_factual_prose() -> None:
    response = _response("scenario-03", categories={
        "README.md": "arbitrary-label",
        "docs/architecture.md": "another-label",
    })
    response["findings"][0]["summary"] = "A completely different explanation."
    response["findings"][0]["evidence"] = copy.deepcopy(_VALID_EVIDENCE["scenario-03"]["README.md"])
    accepted, facts = oracles._review_check("scenario-03", {"review_response": response}, {})
    assert accepted is True, facts


_WRONG_EVIDENCE = {
    ("scenario-03", "README.md"): {
        **_VALID_EVIDENCE["scenario-03"]["README.md"][0],
        "link_target": "docs/present.md",
    },
    ("scenario-03", "docs/architecture.md"): {
        **_VALID_EVIDENCE["scenario-03"]["docs/architecture.md"][0],
        "snippet": "## Architecture overview\n\nThe service reads configuration at startup and serves requests from a shared worker pool.",
    },
    ("scenario-11", "pkg/api/client.go"): {
        **_VALID_EVIDENCE["scenario-11"]["pkg/api/client.go"][0],
        "return_expression": "return []byte{}, nil",
    },
    ("scenario-12", "pkg/service/service.go"): {
        **_VALID_EVIDENCE["scenario-12"]["pkg/service/service.go"][0],
        "return_expression": 'return "computed"',
    },
    ("scenario-14", "pkg/data/models.go"): {
        **_VALID_EVIDENCE["scenario-14"]["pkg/data/models.go"][0],
        "declaration": {"ID": "string", "Name": "int"},
    },
}


@pytest.mark.parametrize("scenario_id,path", sorted(_WRONG_EVIDENCE))
def test_correct_path_with_forged_or_wrong_objective_evidence_is_rejected(
    scenario_id: str, path: str
) -> None:
    response = _response(scenario_id, categories={item: "unrelated-label" for item in _VALID_EVIDENCE[scenario_id]})
    finding = next(item for item in response["findings"] if item["path"] == path)
    finding["summary"] = "The prose is irrelevant to this rejection."
    finding["evidence"] = [_WRONG_EVIDENCE[(scenario_id, path)]]
    accepted, facts = oracles._review_check(scenario_id, {"review_response": response}, {})
    assert accepted is False, facts
    assert any(item["matches"] is False for item in facts["semantic_facts"])


@pytest.mark.parametrize(
    "scenario_id,evidence",
    [
        ("scenario-03", ["prose evidence cannot prove a source fact"]),
        ("scenario-03", [{"source_path": "README.md", "snippet": "forged"}]),
        ("scenario-11", [{
            "source_path": "pkg/api/client.go",
            "span": {"start": 7, "end": 7},
            "snippet": "    return nil, nil",
            "return_expression": "return nil, nil",
            "unexpected": "field",
        }]),
    ],
)
def test_malformed_or_legacy_evidence_fails_closed(scenario_id: str, evidence: list[object]) -> None:
    response = _response(scenario_id)
    response["findings"][0]["evidence"] = evidence
    if any(isinstance(item, dict) for item in evidence):
        with pytest.raises(oracles._Incomplete, match="malformed"):
            oracles._review_check(scenario_id, {"review_response": response}, {})
        return
    accepted, facts = oracles._review_check(scenario_id, {"review_response": response}, {})
    assert accepted is False, facts


def test_forged_extra_evidence_is_rejected_even_with_one_valid_item() -> None:
    response = _response("scenario-11")
    evidence = response["findings"][0]["evidence"]
    evidence.append({
        "source_path": "pkg/api/client.go",
        "span": {"start": 7, "end": 7},
        "snippet": "    return nil, nil",
        "return_expression": "return []byte{}, nil",
    })
    accepted, facts = oracles._review_check("scenario-11", {"review_response": response}, {})
    assert accepted is False, facts
    assert facts["semantic_facts"] == [{"path": "pkg/api/client.go", "matches": False}]


def test_forged_non_required_finding_cannot_be_ignored() -> None:
    response = _response("scenario-03")
    response["findings"].append({
        "path": "docs/missing.md",
        "category": "additional-observation",
        "summary": "Additional source observation.",
        "evidence": [{
            "source_path": "README.md",
            "span": {"start": 3, "end": 3},
            "snippet": "forged source bytes",
        }],
    })
    accepted, facts = oracles._review_check("scenario-03", {"review_response": response}, {})
    assert accepted is False, facts
    assert any(item == {"path": "docs/missing.md", "matches": False}
               for item in facts["generic_evidence"])


def test_valid_extra_finding_is_accepted_after_generic_source_binding() -> None:
    response = _response("scenario-03")
    response["findings"].append({
        "path": "README.md",
        "category": "additional-observation",
        "summary": "Additional source observation.",
        "evidence": copy.deepcopy(_VALID_EVIDENCE["scenario-03"]["README.md"]),
    })
    accepted, facts = oracles._review_check("scenario-03", {"review_response": response}, {})
    assert accepted is True, facts
    assert all(item["matches"] is True for item in facts["generic_evidence"])


def test_extra_declaration_evidence_binds_each_type_to_its_source_line() -> None:
    response = _response("scenario-14")
    response["findings"].append({
        "path": "pkg/data/models.go",
        "category": "additional-observation",
        "summary": "Additional source observation.",
        "evidence": [{
            **copy.deepcopy(_VALID_EVIDENCE["scenario-14"]["pkg/data/models.go"][0]),
            "declaration": {"ID": "string", "Name": "int"},
        }],
    })
    accepted, facts = oracles._review_check("scenario-14", {"review_response": response}, {})
    assert accepted is False, facts
    assert any(item == {"path": "pkg/data/models.go", "matches": False}
               for item in facts["generic_evidence"])


def test_duplicate_wrong_findings_cannot_manufacture_acceptance() -> None:
    response = _response("scenario-11")
    wrong = copy.deepcopy(response["findings"][0])
    wrong["category"] = "second-label"
    wrong["evidence"][0]["return_expression"] = "return []byte{}, nil"
    response["findings"][0] = wrong
    duplicate = copy.deepcopy(wrong)
    duplicate["category"] = "third-label"
    response["findings"].append(duplicate)
    accepted, facts = oracles._review_check("scenario-11", {"review_response": response}, {})
    assert accepted is False, facts
    assert facts["semantic_facts"] == [{"path": "pkg/api/client.go", "matches": False}]


def test_response_instructions_describe_objective_shape_without_frozen_answers() -> None:
    instructions = response_contract.instructions()
    assert "source_path" in instructions
    assert "source snippet" in instructions
    assert "Category is a descriptive label" in instructions
    assert "docs/missing.md" not in instructions
    assert "README.md" not in instructions
