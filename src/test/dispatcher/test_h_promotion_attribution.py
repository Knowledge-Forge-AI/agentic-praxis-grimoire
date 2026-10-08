"""Promotion preregistration keeps attribution independent of prompt compliance."""

import json
import shutil
from pathlib import Path

import pytest

from testing.h_eval import preregistration as owner


ROOT = Path(__file__).resolve().parents[3]


def _copy_promotion_tree(tmp_path: Path) -> Path:
    root = tmp_path / "promotion-source"
    root.mkdir()
    for relative in (
        "testing/h_eval/promotion-preregistration.json",
        "docs/governance/skill-maturity-ledger.json",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    shutil.copytree(
        ROOT / "docs/evaluations/apg166/promotions",
        root / "docs/evaluations/apg166/promotions",
    )
    value = json.loads((root / "testing/h_eval/promotion-preregistration.json").read_bytes())
    for row in value["skills"]:
        source = ROOT / row["source_path"]
        destination = root / row["source_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        for case in row["cases"]:
            route_source = case["route"]["model_source"]
            source = ROOT / route_source
            destination = root / route_source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    return root


def _write_inventory(root: Path, value: dict) -> None:
    path = root / "testing/h_eval/promotion-preregistration.json"
    path.write_text(json.dumps(value, indent=2) + "\n")


def test_cases_freeze_undictated_attribution_and_semantic_non_use() -> None:
    value = owner.verify_promotions(ROOT)
    cases = [case for row in value["skills"] for case in row["cases"]]
    assert len(cases) == 25
    assert sum(case["kind"] == "positive" for case in cases) == 15
    assert sum(case["kind"] == "non-trigger" for case in cases) == 10
    for case in cases:
        rubric = case["attribution_rubric"]
        assert rubric["material_decision_required"] is True
        assert rubric["decision_not_dictated_by"] == ["prompt", "oracle"]
        assert rubric["exact_guidance_link_required"] == (case["kind"] == "positive")
        assert rubric["resulting_work_link_required"] is True
        assert rubric["insufficient_evidence"] == [
            "skill delivery", "native Read", "skill acquisition", "prompt compliance"
        ]
        if case["kind"] == "positive":
            assert rubric["mode"] == "positive_use"
            assert "not dictated by the prompt or oracle" in " ".join(case["required_evidence"])
        else:
            assert rubric["mode"] == "semantic_non_use"
            assert rubric["neighboring_domain_non_use_required"] is True
            assert rubric["semantic_non_use_link_required"] is True
            assert "semantic non-use decision" in " ".join(case["required_evidence"]).lower()


def test_checklist_leading_positive_prompt_is_rejected_after_digest_update(tmp_path: Path) -> None:
    root = _copy_promotion_tree(tmp_path)
    path = root / "testing/h_eval/promotion-preregistration.json"
    value = json.loads(path.read_bytes())
    case = value["skills"][0]["cases"][0]
    case["prompt"] += " Use subtests and cleanup."
    case["case_sha256"] = owner.case_identity(case)
    case["oracle"]["case_sha256"] = case["case_sha256"]
    _write_inventory(root, value)

    with pytest.raises(ValueError, match="checklist-leading prompt"):
        owner.verify_promotions(root)


def test_attribution_rubric_cannot_be_removed_after_digest_update(tmp_path: Path) -> None:
    root = _copy_promotion_tree(tmp_path)
    path = root / "testing/h_eval/promotion-preregistration.json"
    value = json.loads(path.read_bytes())
    case = value["skills"][0]["cases"][0]
    del case["attribution_rubric"]["resulting_work_link_required"]
    case["case_sha256"] = owner.case_identity(case)
    case["oracle"]["case_sha256"] = case["case_sha256"]
    _write_inventory(root, value)

    with pytest.raises(ValueError, match="attribution rubric changed"):
        owner.verify_promotions(root)
