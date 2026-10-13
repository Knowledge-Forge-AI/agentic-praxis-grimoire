"""Adversarial provider-free cleanup classification and exact-attempt correction."""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
from types import SimpleNamespace

import pytest

from agent_phase import canary_budget as owner


@pytest.fixture(autouse=True)
def process_identity(monkeypatch):
    real = owner.subprocess.run
    def run(argv, *args, **kwargs):
        if argv[0] == "ps":
            return SimpleNamespace(returncode=0, stdout="fixture-start", stderr="")
        return real(argv, *args, **kwargs)
    monkeypatch.setattr(owner.subprocess, "run", run)


def fixture(tmp_path, *, drained=False):
    budget = owner.CanaryBudget(home=tmp_path / "home", phase=owner.SONNET_PHASE)
    reservation = budget.reserve("gemini-sonnet", cause="original")
    run = tmp_path / "run"
    run.mkdir()
    parent = "dispatch-fixture--work--1"
    record = {"schema": "apgr.worker-canary/v1", "case": "gemini-sonnet", "phase": owner.SONNET_PHASE,
              "status": "blocked", "budget_reservation": reservation,
              "candidate_source_identity": "a" * 64, "bundle": {"manifest_sha256": "b" * 64},
              "parent_id": parent, "provider_invocations": 0, "actual_argv": [],
              "error_code": "worker_unavailable", "admission": {}, "native_admission": [], "worker_results": []}
    registration = {"schema": owner.STAGE_REGISTRATION_SCHEMA, "parent_id": parent,
                    "run_id": "fixture-run", "stage": "work", "prefix": "01-work", "index": 1,
                    "lifecycle_generation": "fixture-run:work:1", "complete": True,
                    "registration_status": "refused_before_register", "register_entered": False,
                    "provider_entered": False, "custody_status": "not_acquired", "process_state": "not_started"}
    (run / "01-work.registration.json").write_text(json.dumps(registration))
    if drained:
        cleanup = {k: True for k in ("cleanup_proven", "outer_group_absent", "nested_groups_absent", "verified_absence", "reaped")}
        cleanup["failure_reasons"] = []
        drain = {"status": "closed", "uncertain_cleanup": False, "parent_id": parent}
        record.update(parent_cleanup=cleanup, provider_invocations=1, actual_argv=[["fixture-provider"]],
                      stage_meta={"cleanup": cleanup, "worker_drain": drain})
        (run / "01-work.meta.json").write_text(json.dumps(record["stage_meta"]))
        (run / "01-work.worker-drain.json").write_text(json.dumps(drain))
        ledger = run / "workers" / parent / "ledger.json"
        ledger.parent.mkdir(parents=True)
        ledger.write_text(json.dumps({"status": "closed", "parent_id": parent}))
    record["classification_inputs"] = owner.cleanup_inputs(record, run)
    receipt = tmp_path / "canary.json"
    receipt.write_text(json.dumps(record))
    details = {"receipt": str(receipt), "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
               "case": record["case"], "phase": record["phase"], "source_identity": record["candidate_source_identity"],
               "bundle_sha256": record["bundle"]["manifest_sha256"], "parent_cleanup": record.get("parent_cleanup"),
               "worker_drain": record.get("stage_meta", {}).get("worker_drain"),
               "classification_inputs": record["classification_inputs"]}
    budget.record_disposition(record["case"], 1, status="blocked", cleanup_proven=False, details=details)
    entry = json.loads(budget.path.read_bytes())["cases"][record["case"]]["attempts"][0]
    return budget, run, record, receipt, entry


@pytest.mark.parametrize("drained,classification", [(False, "proven_no_child_before_provider"), (True, "proven_drained")])
def test_cleanup_requires_complete_bound_affirmative_records(tmp_path, drained, classification):
    _, run, record, _, _ = fixture(tmp_path, drained=drained)
    before = copy.deepcopy(record)
    result = owner.classify_cleanup(record, run)
    assert result["cleanup_proven"]
    assert result["classification"] == classification
    assert record == before


@pytest.mark.parametrize("mutation", ["registered", "maybe_committed", "provider_entered", "custody_acquired", "incomplete", "wrong_parent", "missing_counter", "caller_boolean", "missing_artifact", "altered_artifact"])
def test_no_child_refuses_uncertainty_or_caller_assertions(tmp_path, mutation):
    _, run, record, _, _ = fixture(tmp_path)
    path = run / "01-work.registration.json"
    registration = json.loads(path.read_bytes())
    changes = {"registered": {"registration_status": "registered"}, "maybe_committed": {"register_entered": True},
               "provider_entered": {"provider_entered": True}, "custody_acquired": {"custody_status": "acquired"},
               "incomplete": {"complete": False}, "wrong_parent": {"parent_id": "other"}}
    if mutation in changes:
        registration.update(changes[mutation])
        path.write_text(json.dumps(registration))
        record["classification_inputs"] = owner.cleanup_inputs(record, run)
    elif mutation == "missing_counter":
        record.pop("provider_invocations")
        record["classification_inputs"].pop("provider_invocations")
    elif mutation == "caller_boolean":
        record = {"cleanup_proven": True}
    elif mutation == "missing_artifact":
        path.unlink()
    else:
        path.write_text("{}")
    assert not owner.classify_cleanup(record, run)["cleanup_proven"]


@pytest.mark.parametrize("flag", ["cleanup_proven", "outer_group_absent", "nested_groups_absent", "verified_absence", "reaped"])
def test_drain_requires_each_process_proof(tmp_path, flag):
    _, run, record, _, _ = fixture(tmp_path, drained=True)
    record["parent_cleanup"].pop(flag)
    (run / "01-work.meta.json").write_text(json.dumps(record["stage_meta"]))
    record["classification_inputs"] = owner.cleanup_inputs(record, run)
    assert not owner.classify_cleanup(record, run)["cleanup_proven"]


def test_legacy_provider_invoked_no_drain_is_uncertain(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    result = owner.classify_cleanup({"provider_invocations": 1, "actual_argv": [["provider"]],
                                    "parent_cleanup": {"cleanup_proven": True}}, run)
    assert not result["cleanup_proven"]
    assert "affirmative_no_admission_record" in result["missing"]


def test_reconciliation_preserves_history_and_retry_rules(tmp_path):
    budget, _, _, receipt, original = fixture(tmp_path)
    result = budget.reconcile_attempt_cleanup("gemini-sonnet", 1, receipt_path=receipt)
    audit = result.pop("cleanup_reconciliation")
    assert result == {**original, "cleanup_proven": True}
    assert audit["original_cleanup_proven"] is False
    assert audit["original_status"] == "blocked"
    with pytest.raises(owner.UnchangedCauseError):
        budget.reserve("gemini-sonnet", cause="original")
    assert budget.reserve("gemini-sonnet", cause="reviewed repair")["attempt"] == 2
    budget.record_disposition("gemini-sonnet", 2, status="partial", cleanup_proven=True)
    with pytest.raises(owner.BudgetExhaustedError):
        budget.reserve("gemini-sonnet", cause="third")
    assert "cleanup_proven" not in inspect.signature(budget.reconcile_attempt_cleanup).parameters


@pytest.mark.parametrize("mutation", ["receipt_path", "receipt_digest", "attempt", "phase", "case", "parent", "drain", "source", "bundle", "inputs", "inflight", "already", "artifact", "missing_receipt", "symlink"])
def test_reconciliation_refusal_preserves_exact_budget_bytes(tmp_path, mutation):
    budget, run, record, receipt, entry = fixture(tmp_path)
    data = json.loads(budget.path.read_bytes())
    target = data["cases"]["gemini-sonnet"]["attempts"][0]
    if mutation == "receipt_path":
        other = tmp_path / "other.json"
        other.write_bytes(receipt.read_bytes())
        receipt = other
    elif mutation == "receipt_digest":
        target["details"]["receipt_sha256"] = "c" * 64
    elif mutation == "attempt":
        record["budget_reservation"]["pid"] += 1
    elif mutation == "phase":
        record["phase"] = "other"
    elif mutation == "case":
        record["case"] = "codex-sonnet"
    elif mutation == "parent":
        record["parent_cleanup"] = {"cleanup_proven": True}
    elif mutation == "drain":
        record["stage_meta"] = {"worker_drain": {"status": "closed"}}
    elif mutation == "source":
        record["candidate_source_identity"] = "c" * 64
    elif mutation == "bundle":
        record["bundle"]["manifest_sha256"] = "c" * 64
    elif mutation == "inputs":
        target["details"].pop("classification_inputs")
    elif mutation == "inflight":
        target["status"] = "in_flight"
    elif mutation == "already":
        target["cleanup_reconciliation"] = {"operation": "previous"}
    elif mutation == "artifact":
        (run / "01-work.registration.json").write_text("{}")
    elif mutation == "missing_receipt":
        receipt.unlink()
    elif mutation == "symlink":
        actual = tmp_path / "actual.json"
        actual.write_bytes(receipt.read_bytes())
        receipt.unlink()
        receipt.symlink_to(actual)
    if mutation in {"attempt", "phase", "case", "parent", "drain", "source", "bundle"}:
        receipt.write_text(json.dumps(record))
        target["details"]["receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    budget.path.write_text(json.dumps(data))
    before = budget.path.read_bytes()
    with pytest.raises(owner.CanaryBudgetError):
        budget.reconcile_attempt_cleanup("gemini-sonnet", 1, receipt_path=receipt)
    assert budget.path.read_bytes() == before


def test_reconciliation_budget_race_refuses_without_its_own_write(tmp_path, monkeypatch):
    budget, _, _, receipt, _ = fixture(tmp_path)
    real = owner.evaluate_cleanup_reconciliation
    changed = None
    def racing(*args, **kwargs):
        nonlocal changed
        result = real(*args, **kwargs)
        changed = budget.path.read_bytes() + b" "
        budget.path.write_bytes(changed)
        return result
    monkeypatch.setattr(owner, "evaluate_cleanup_reconciliation", racing)
    with pytest.raises(owner.CanaryBudgetError, match="budget changed"):
        budget.reconcile_attempt_cleanup("gemini-sonnet", 1, receipt_path=receipt)
    assert budget.path.read_bytes() == changed
