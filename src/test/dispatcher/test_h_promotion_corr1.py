"""Focused APG166E-CORR1 promotion-oracle regression checks."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import pytest

from testing.h_eval import preregistration as owner
from testing.h_eval import promotion_fixture_specs as fixtures
from testing.h_eval import promotion_oracles


ROOT = Path(__file__).resolve().parents[3]


def _executables() -> dict[str, str]:
    go = shutil.which("go")
    if go is None:
        pytest.skip("Go runtime is unavailable")
    return {"go": go, "python3": sys.executable}


def _value() -> dict:
    return json.loads((ROOT / "testing/h_eval/promotion-preregistration.json").read_bytes())


def _case(case_id: str) -> dict:
    return next(case for row in _value()["skills"] for case in row["cases"]
                if case["case_id"] == case_id)


def test_registry_requires_exact_preregistration_metadata() -> None:
    value = _value()
    expected = owner.expected_oracle_inventory(value)
    promotion_oracles.validate_registry(expected)
    with pytest.raises(promotion_oracles.PromotionOracleError, match="case digest"):
        promotion_oracles.validate_registry(promotion_oracles.registry_inventory())
    with pytest.raises(promotion_oracles.PromotionOracleError, match="preregistration inventory"):
        promotion_oracles.validate_registry([row["case_id"] for row in expected])
    for field, match in (
        ("skill_id", "skill mismatch"),
        ("kind", "kind mismatch"),
        ("oracle_id", "oracle identity mismatch"),
        ("hidden_oracle_sha256", "oracle identity mismatch"),
        ("fixture_contract", "fixture contract mismatch"),
    ):
        mutated = [dict(row) for row in expected]
        mutated[0][field] = "mutated"
        with pytest.raises(promotion_oracles.PromotionOracleError, match=match):
            promotion_oracles.validate_registry(mutated)
    duplicate = [*expected, dict(expected[0])]
    with pytest.raises(promotion_oracles.PromotionOracleError, match="duplicate"):
        promotion_oracles.validate_registry(duplicate)
    missing = expected[1:]
    with pytest.raises(promotion_oracles.PromotionOracleError, match="missing"):
        promotion_oracles.validate_registry(missing)
    extra = [*expected, {**expected[0], "case_id": "extra/case"}]
    with pytest.raises(promotion_oracles.PromotionOracleError, match="extra"):
        promotion_oracles.validate_registry(extra)


def test_source_digest_binds_execution_owner_and_fixture_registry() -> None:
    value = _value()
    assert value["phase"] == "APG166E"
    assert value["oracle_source"]["paths"] == [
        promotion_oracles.SOURCE_PATH,
        promotion_oracles.FIXTURE_SOURCE_PATH,
        "testing/h_eval/hidden_execution.py",
        "testing/h_eval/lifecycle_hidden.py",
        "testing/h_eval/authored_execution.py",
        "testing/h_eval/starting_evidence.py",
    ]
    assert value["oracle_source"]["sha256"] == promotion_oracles.source_sha256()
    assert owner.verify_promotions(ROOT)["oracle_source"] == value["oracle_source"]


def test_later_subject_uses_same_hidden_oracle_for_good_bad_and_starting() -> None:
    executables = _executables()
    case_id = "go-language-profile/positive/cancellation"
    case = _case(case_id)
    starting = promotion_oracles.evaluate_model_output(case_id, case["subject_files"], executables)
    good = promotion_oracles.evaluate_model_output(case_id, fixtures.ORACLES[case_id].good_files, executables)
    bad = promotion_oracles.evaluate_model_output(case_id, fixtures.ORACLES[case_id].bad_files, executables)
    assert starting["status"] == "fail"
    assert good["status"] == "pass"
    assert bad["status"] == "fail"
    assert good["hidden_oracle"]["oracle_id"] == bad["hidden_oracle"]["oracle_id"]
    assert good["hidden_oracle"]["hidden_oracle_sha256"] == bad["hidden_oracle"]["hidden_oracle_sha256"]


@pytest.mark.parametrize("case_id", [
    "go-test-profile/positive/lifecycle",
    "pytest-test-profile/positive/collection",
    "pytest-test-profile/positive/fixture-lifecycle",
])
def test_authored_tests_must_pass_good_and_detect_bad(case_id: str) -> None:
    result = promotion_oracles.evaluate_model_output(
        case_id, fixtures.ORACLES[case_id].good_files, _executables()
    )
    assert result["status"] == "pass"
    authored = result["model_authored_tests"]
    assert authored["status"] == "pass"
    assert authored["good"]["status"] == "pass"
    assert authored["bad"]["status"] == "fail"
    assert authored["vacuous"] is False


def test_vacuous_authored_tests_are_rejected() -> None:
    case_id = "go-test-profile/positive/lifecycle"
    subject = {
        "go.mod": fixtures.ORACLES[case_id].good_files["go.mod"],
        "parse.go": fixtures.ORACLES[case_id].good_files["parse.go"],
        "parse_test.go": "package parsing\nimport \"testing\"\nfunc TestNoop(t *testing.T) {}\n",
    }
    result = promotion_oracles.evaluate_model_output(case_id, subject, _executables())
    assert result["status"] == "fail"
    assert result["model_authored_tests"]["vacuous"] is True


def test_markdown_variants_are_semantic_and_nontriggers_are_structural_only() -> None:
    nested = {
        "README.md": "1. Prepare\n    * first item\n    + second item\n\n    ~~~~sh\n    echo ready\n    ~~~~\n\n2. Finish\n"
    }
    assert fixtures.source_check(fixtures.ORACLES["markdown-language-profile/positive/nested-blocks"], nested)
    literals = {"README.md": "# Examples\n\n~~~~markdown\n```python\nprint(\"literal\")\n```\n~~~~\n"}
    assert fixtures.source_check(fixtures.ORACLES["markdown-language-profile/positive/code-literals"], literals)
    value = _value()
    for row in value["skills"]:
        for case in row["cases"]:
            if case["kind"] == "non-trigger":
                contract = case["non_trigger_contract"]
                assert contract["provider_free_claim"] == "structure-only"
                assert contract["external_correctness_oracle"]["task_result_required"] is True
                assert set(contract["required_evidence"]) == {
                    "selection/delivery/acquisition/read traces",
                    "actual task result",
                    "absence of material target-skill guidance use",
                    "reviewer disposition of semantic non-use",
                }


def test_directory_oracle_binds_unchanged_retained_result(tmp_path: Path) -> None:
    case_id = "markdown-language-profile/positive/links"
    root = tmp_path / "subject"
    root.mkdir(mode=0o700)
    for name, content in fixtures.ORACLES[case_id].good_files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        target.chmod(0o600)
    result = promotion_oracles.evaluate_subject_directory(case_id, root, {})
    assert result["status"] == "pass"
    assert result["subject_readback_unchanged"] is True
    assert result["subject_inventory_before"] == result["subject_inventory_after"]


@pytest.mark.parametrize("fence", ["~~~", "~~~~~", "````", "`````"])
@pytest.mark.parametrize("info", ["", "markdown", "text"])
def test_literal_fences_preserve_the_visible_example(fence, info):
    spec = fixtures.ORACLES["markdown-language-profile/positive/code-literals"]
    text = '# Examples\n\n' + fence + info + '\n```python\nprint("literal")\n```\n' + fence + '\n'
    assert fixtures.source_check(spec, {"README.md": text})
    assert not fixtures.source_check(spec, {"README.md": text.replace('print("literal")', 'print("different")')})


@pytest.mark.parametrize("indent", ["   ", "    "])
@pytest.mark.parametrize("blank", ["", "\n"])
def test_nested_blocks_accept_layout_variants_and_preserve_wording(indent, blank):
    spec = fixtures.ORACLES["markdown-language-profile/positive/nested-blocks"]
    text = ("1. Prepare\n" + indent + "* first item\n" + indent + "+ second item\n" + blank
            + indent + "~~~sh\n" + indent + "echo ready\n" + indent + "~~~\n" + blank + "2. Finish\n")
    assert fixtures.source_check(spec, {"README.md": text})
    assert not fixtures.source_check(spec, {"README.md": text.replace("second item", "unrelated")})
    assert not fixtures.source_check(spec, {"README.md": text.replace(indent, "")})


@pytest.mark.parametrize("policy", ["timeout=0", "timeout=0.05", "timeout=5"])
def test_sqlite_writer_accepts_defensible_contention_policies(policy):
    case_id = "sqlite-database-profile/positive/writer-wal"
    subject = {"exercise.py": "import sqlite3\ndef open_database(path):\n    return sqlite3.connect(path, " + policy + ")\n"}
    assert promotion_oracles.evaluate_model_output(case_id, subject, {"python3": sys.executable})["status"] == "pass"


def test_sqlite_writer_rejects_connections_that_do_not_share_the_store():
    subject = {"exercise.py": "import sqlite3\ncount=0\ndef open_database(path):\n    global count\n    count+=1\n    return sqlite3.connect(path if count==1 else ':memory:', timeout=0)\n"}
    assert promotion_oracles.evaluate_model_output("sqlite-database-profile/positive/writer-wal", subject, {"python3": sys.executable})["status"] == "fail"
