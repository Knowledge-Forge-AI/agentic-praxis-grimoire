"""APG166E source-owned promotion preregistration qualification."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import pytest

from testing.h_eval import preregistration as owner, promotion_oracles


ROOT = Path(__file__).resolve().parents[3]
SKILLS = {
    "go-language-profile", "go-test-profile", "pytest-test-profile",
    "markdown-language-profile", "sqlite-database-profile",
}


def _executables() -> dict[str, str]:
    go = shutil.which("go")
    if go is None:
        pytest.fail("provider-free promotion oracle qualification requires Go")
    return {"go": go, "python3": shutil.which("python3") or sys.executable}


def _copy_tree(tmp_path: Path) -> Path:
    root = tmp_path / "promotion-source"
    root.mkdir()
    for prefix in (
        "testing/h_eval", "docs/governance", "docs/evaluations/apg166/promotions",
        "codex/profiles", "claude/profiles", "antigravity/profiles",
    ):
        shutil.copytree(ROOT / prefix, root / prefix, ignore=shutil.ignore_patterns("__pycache__"))
    value = json.loads((root / "testing/h_eval/promotion-preregistration.json").read_bytes())
    for row in value["skills"]:
        source = ROOT / row["source_path"]
        destination = root / row["source_path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        for case in row["cases"]:
            source = ROOT / case["route"]["model_source"]
            destination = root / case["route"]["model_source"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    return root


def _write_inventory(root: Path, value: dict) -> None:
    (root / "testing/h_eval/promotion-preregistration.json").write_text(
        json.dumps(value, indent=2) + "\n", encoding="utf-8"
    )


def _case(value: dict, case_id: str) -> dict:
    return next(case for row in value["skills"] for case in row["cases"] if case["case_id"] == case_id)


def test_exact_five_skill_inventory_and_pending_review_contract() -> None:
    value = owner.verify_promotions(ROOT)
    assert {row["skill_id"] for row in value["skills"]} == SKILLS
    cases = [case for row in value["skills"] for case in row["cases"]]
    assert len(cases) == 25
    assert sum(case["kind"] == "positive" for case in cases) == 15
    assert sum(case["kind"] == "non-trigger" for case in cases) == 10
    assert value["independent_review"]["status"] == "pending"
    assert value["independent_review"]["overall_inventory_disposition"] == "pending"
    assert set(value["independent_review"]["per_skill_disposition"]) == SKILLS
    assert value["oracle_source"]["sha256"] == promotion_oracles.source_sha256()
    assert all(case["oracle"]["assertion_owner"] == "source-owned" for case in cases)


def test_all_source_owned_good_bad_fixture_pairs_qualify_without_provider() -> None:
    result = owner.qualify_promotion_oracles(ROOT, _executables())
    assert result["schema"] == "apg.h-promotion-oracle/v1"
    assert result["qualification_mode"] == "diagnostic"
    assert result["complete_qualification"] is False
    assert result["cases"] == 25
    assert result["fixture_pairs"] == 25
    assert len(result["receipts"]) == 50
    assert {receipt["fixture"] for receipt in result["receipts"]} == {"pass", "fail"}
    assert all(receipt["network"] == "configured_offline_not_os_enforced"
               for receipt in result["receipts"] if "network" in receipt)
    assert all(Path(receipt["command"][0]).name not in {"claude", "codex", "antigravity", "gemini"}
               for receipt in result["receipts"] if "command" in receipt)


def test_complete_qualification_rejects_explicit_path_mapping(tmp_path: Path) -> None:
    with pytest.raises(promotion_oracles.PromotionOracleError, match="complete sealed runtime manifest"):
        promotion_oracles.qualify_all(_executables(), tmp_path / "fixtures")


def test_hidden_oracle_fact_cannot_be_moved_into_model_visible_subject(tmp_path: Path) -> None:
    root = _copy_tree(tmp_path)
    path = root / "testing/h_eval/promotion-preregistration.json"
    value = json.loads(path.read_bytes())
    case = _case(value, "markdown-language-profile/positive/links")
    case["subject_files"]["README.md"] = promotion_oracles.spec_for(case["case_id"]).hidden_facts[0]
    case["case_sha256"] = owner.case_identity(case)
    case["oracle"]["case_sha256"] = case["case_sha256"]
    _write_inventory(root, value)
    with pytest.raises(ValueError, match="hidden fact"):
        owner.verify_promotions(root)


def test_unbound_xdist_and_model_authored_oracle_are_rejected(tmp_path: Path) -> None:
    root = _copy_tree(tmp_path)
    path = root / "testing/h_eval/promotion-preregistration.json"
    value = json.loads(path.read_bytes())
    case = _case(value, "pytest-test-profile/positive/worker-isolation")
    case["subject_files"]["pytest.ini"] = "[pytest]\naddopts = -n 2\n"
    case["case_sha256"] = owner.case_identity(case)
    case["oracle"]["case_sha256"] = case["case_sha256"]
    _write_inventory(root, value)
    with pytest.raises(ValueError, match="unbound xdist"):
        owner.verify_promotions(root)

    value = json.loads(path.read_bytes())
    case = _case(value, "go-test-profile/positive/false-pass")
    case["oracle"]["assertion_owner"] = "model-authored"
    case["case_sha256"] = owner.case_identity(case)
    case["oracle"]["case_sha256"] = case["case_sha256"]
    _write_inventory(root, value)
    with pytest.raises(ValueError, match="oracle binding"):
        owner.verify_promotions(root)


def test_review_cannot_self_accept_exact_inventory(tmp_path: Path) -> None:
    root = _copy_tree(tmp_path)
    path = root / "testing/h_eval/promotion-preregistration.json"
    value = json.loads(path.read_bytes())
    value["independent_review"]["status"] = "accept"
    _write_inventory(root, value)
    with pytest.raises(ValueError, match="independent review contract"):
        owner.verify_promotions(root)


@pytest.mark.parametrize("mutation", ["subject", "case-digest", "oracle-case-digest"])
def test_stale_case_identity_is_rejected(tmp_path, mutation):
    root = _copy_tree(tmp_path)
    value = json.loads((root / "testing/h_eval/promotion-preregistration.json").read_bytes())
    case = value["skills"][0]["cases"][0]
    if mutation == "subject":
        name = next(iter(case["subject_files"]))
        case["subject_files"][name] += "\nchanged subject\n"
    elif mutation == "case-digest":
        case["case_sha256"] = "0" * 64
    else:
        case["oracle"]["case_sha256"] = "0" * 64
    _write_inventory(root, value)
    with pytest.raises(ValueError, match="case identity|oracle binding"):
        owner.verify_promotions(root)
