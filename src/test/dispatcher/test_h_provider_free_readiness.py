"""The provider-free checkpoint cannot inherit live or review authority."""
import copy

import pytest

from testing.h_eval import provider_free_readiness as readiness
from testing.h_eval.dry_run import dry_run_all


def _complete():
    return {
        "complete_records": 15, "provider_invocations": 0,
        "runtime_transaction": {"status": "valid"},
        "records": [{
            "scenario_id": f"scenario-{n:02d}", "status": "complete",
            "initial_trees_equal": True,
            "subject_authority": {mode: {"unchanged": True} for mode in ("static", "adaptive")},
            "oracle": {"fixture_exercise": {"status": "complete"}},
            "importer": {"status": "complete"},
            "special": {name: {"status": "complete"}
                        for name in readiness.SPECIALS.get(f"scenario-{n:02d}", set())},
        } for n in range(1, 16)],
    }


def test_transaction_requires_each_independent_boundary():
    original = _complete()
    assert readiness._dry_run_complete(original)
    for family in ("oracle", "importer", "subject", "special", "runtime", "invocation"):
        value = copy.deepcopy(original)
        row = value["records"][0]
        if family == "oracle":
            row["oracle"]["fixture_exercise"]["status"] = "incomplete"
        elif family == "importer":
            row["importer"]["status"] = "resolved"
        elif family == "subject":
            row["subject_authority"]["adaptive"]["unchanged"] = False
        elif family == "special":
            row["special"]["recovery"] = {"status": "incomplete"}
        elif family == "runtime":
            value["runtime_transaction"]["status"] = "expired"
        else:
            value["provider_invocations"] = 1
        assert not readiness._dry_run_complete(value), family

    for scenario in readiness.SPECIALS:
        value = copy.deepcopy(original)
        next(row for row in value["records"] if row["scenario_id"] == scenario)["special"] = {}
        assert not readiness._dry_run_complete(value)


def test_qualified_transaction_refuses_caller_oracle_claims(tmp_path):
    with pytest.raises(ValueError, match="repository-owned"):
        dry_run_all(tmp_path, tmp_path / "result", runtime_manifest={"schema": "fake"},
                    oracle_owner=lambda: {"good": True, "bad": True})
    assert not (tmp_path / "result").exists()


@pytest.mark.parametrize("review", [
    {}, "a" * 64, {"evidence_sha256": "a" * 64},
    {"overall_source_disposition": "accept", "provider_free_package_disposition": "accept",
     "promotion_preregistration_by_skill": {skill: "accept" for skill in readiness.SKILLS},
     "promotion_preregistration_disposition": "accept", "evidence_sha256": "b" * 64},
])
def test_source_refuses_every_caller_review_before_reading_evidence(tmp_path, review):
    with pytest.raises(ValueError, match="custody belongs to dispatcher/manager"):
        readiness.make_package_seal(tmp_path, tmp_path / "absent", independent_review=review)


def test_mechanical_candidate_cannot_self_accept(tmp_path, monkeypatch):
    inventory = tmp_path / "testing/h_eval/promotion-preregistration.json"
    inventory.parent.mkdir(parents=True)
    inventory.write_text("{}")
    directory = tmp_path / "evidence"; directory.mkdir()
    (directory / "dry-run.json").write_text("{}")
    result = _complete()
    result["source_identity"] = readiness.source_identity({})
    monkeypatch.setattr(readiness, "read_dry_run", lambda _: result)
    monkeypatch.setattr(readiness, "make_seal", lambda _: {"files": {}})
    monkeypatch.setattr(readiness, "_promotion_fixtures_complete", lambda *_: True)
    sealed = readiness.make_package_seal(tmp_path, directory)
    assert sealed["provider_free_mechanical_candidate"] is True
    assert sealed["provider_free_package_ready"] is False
    assert sealed["manager_review_required"] is True
    assert sealed["promotion_preregistration_acceptance"] == "pending-independent-review"
    assert sealed["checkpoint"] != readiness.TOKEN


def test_promotion_receipt_counts_cannot_replace_exact_coverage(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from testing.h_eval import preregistration, promotion_oracles
    root = Path(__file__).resolve().parents[3]
    value = json.loads((root / "testing/h_eval/promotion-preregistration.json").read_bytes())
    monkeypatch.setattr(preregistration, "verify_promotions", lambda _: value)
    inventory = preregistration.expected_oracle_inventory(value)
    from test_h_starting_evidence import durable_starting
    with monkeypatch.context() as context:
        observed, _ = durable_starting(tmp_path, context)
    pytest_starts = {r['case_id']: r for r in observed['starting_subjects']}
    receipts, starts = [], []
    for binding in inventory:
        for status in ("pass", "fail"):
            receipt = {key: binding[key] for key in ("case_id", "oracle_id", "hidden_oracle_sha256")}
            receipt.update(fixture=status, status=status,
                           qualification_scope="structural-only; semantic-non-use-not-evaluated")
            if binding["kind"] == "positive" and binding["fixture_kind"] == "command":
                receipt["model_evaluation"] = {"status": status, "model_authored_tests": {
                    "status": status, "good": {"status": "pass"}, "bad": {"status": "fail"}}}
            receipts.append(receipt)
        if binding["kind"] == "positive":
            starts.append(pytest_starts.get(binding["case_id"],
                {"case_id": binding["case_id"], "status": "fail", "starting_failure_required": True}))
    result = {"runtime_transaction": {"manifest_sha256": "a" * 64}, "promotion_oracle_fixtures": {
        "complete_qualification": True, "qualification_mode": "complete",
        "source_sha256": promotion_oracles.source_sha256(root), "cases": len(inventory),
        "fixture_pairs": len(inventory), "receipts": receipts, "starting_subjects": starts,
        "starting_subject_count": len(starts), "runtime_transaction": {
            "before_revalidated": True, "after_revalidated": True,
            "manifest_sha256": "a" * 64, "after_manifest_sha256": "a" * 64}}}
    assert readiness._promotion_fixtures_complete(result, root)
    for mutation in ("duplicate", "oracle", "authored", "starting", "semantic-claim", "source"):
        candidate = copy.deepcopy(result)
        evidence = candidate["promotion_oracle_fixtures"]
        if mutation == "duplicate":
            evidence["receipts"][1] = copy.deepcopy(evidence["receipts"][0])
        elif mutation == "oracle":
            evidence["receipts"][0]["hidden_oracle_sha256"] = "0" * 64
        elif mutation == "authored":
            row = next(r for r in evidence["receipts"] if r["case_id"].startswith("go-test-profile/positive/") and r["fixture"] == "pass")
            row["model_evaluation"]["model_authored_tests"]["bad"]["status"] = "pass"
        elif mutation == "starting":
            evidence["starting_subjects"][0]["status"] = "pass"
        elif mutation == "semantic-claim":
            row = next(r for r in evidence["receipts"] if "/non-trigger/" in r["case_id"])
            row["qualification_scope"] = "semantic-non-use-proven"
        else:
            evidence["source_sha256"] = "0" * 64
        assert not readiness._promotion_fixtures_complete(candidate, root), mutation
