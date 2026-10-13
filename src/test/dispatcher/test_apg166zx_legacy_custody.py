"""Provider-free legacy custody contracts using disposable synthetic evidence."""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
from types import SimpleNamespace

import pytest
from agent_phase import canary_budget as owner


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh(s, monkeypatch):
    canary_sha = write_json(s["canary_path"], s["canary"])
    s["authority"]["historical_canary"]["sha256"] = canary_sha
    authority_sha = write_json(s["authority_path"], s["authority"])
    monkeypatch.setattr(owner, "PINNED_CANARY_SHA256", canary_sha)
    monkeypatch.setattr(owner, "PINNED_AUTHORITY_SHA256", authority_sha)
    s["approval"].update(reviewed_authority_sha256=authority_sha, canary_sha256=canary_sha,
                         original_attempt_sha256=owner.canonical_attempt_sha256(s["entry"]))
    approval_sha = write_json(s["approval_path"], s["approval"])
    s["evidence"].update(authority_sha256=authority_sha, approval_sha256=approval_sha)
    s["budget"]._write(s["data"])


@pytest.fixture
def legacy(tmp_path, monkeypatch):
    reservation = {"attempt": 1, "pid": 101, "pgid": 102, "process_start_identity": "fixture-start",
                       "created_at": 1.0, "cause": "initial_run"}
    cleanup = dict.fromkeys(("cleanup_proven", "outer_group_absent", "nested_groups_absent",
                            "verified_absence", "reaped", "wrapper_reaped", "parent_reaped"), True)
    cleanup.update(failure_reasons=[], outer_group_status="absent", nested_groups_registered=1,
                   nested_group_status={"202": "absent"},
                   termination={"reason": "normal_completion", "outer_pgid": 201, "nested_pgids": [202]})
    reason = "parent registration unavailable (ValueError)"
    capability = {"available": False, "allowed": False, "reason": reason, "native_worker": {"enabled": False}}
    group_cleanup = {"cleanup_complete": True, "group_absent": True}
    canary = {"schema": "apgr.worker-canary/v1", "case": "gemini-sonnet", "phase": owner.SONNET_PHASE,
                  "status": "partial", "cleanup_proven": False, "stage_ok": True,
                  "candidate_source_identity": "a" * 64, "bundle": {"manifest_sha256": "b" * 64},
                  "parent_id": "fixture-parent--work--1", "budget_reservation": reservation,
                  "parent_cleanup": cleanup, "admission": {}, "worker_results": [], "native_admission": [],
                  "native_sonnet_count": None, "capacity_receipt": dict.fromkeys(("max_gemini", "max_luna", "max_sonnet", "borrowing")),
                  "stage_meta": {"stage": "work", "exit_code": 0, "cleanup": cleanup, "worker_capability": capability,
                                  "worker_disposition": {"status": "unavailable", "reason": reason},
                                  "antigravity_evidence": {"validation": "validated", "provider_status": "success", "transport_success": True,
                                                           "process_group_cleanup": group_cleanup, "version_probe_cleanup": group_cleanup}}}
    entry = dict(reservation, status="partial", updated_at=2.0, cleanup_proven=False,
                 details={"receipt": "archive/gemini-sonnet/canary.json", "source_identity": "a" * 64,
                              "bundle_sha256": "b" * 64, "parent_cleanup": cleanup, "worker_drain": None})
    authority = {"schema": owner.LEGACY_AUTHORITY_SCHEMA, "phase": "APG166ZX",
                     "decision": "authorize_implementation_and_provider_free_testing_only", "case": "gemini-sonnet",
                     "historical_campaign_phase": owner.SONNET_PHASE, "attempt": 1, "classification": owner.LEGACY_CLASSIFICATION,
                     "historical_canary": {"filename": "APG166ZS-GEMINI-CANARY.json", "candidate_source_identity": "a" * 64,
                                            "bundle_sha256": "b" * 64, "parent_id": canary["parent_id"]},
                     "budget_evidence": {"attempt_record_cleanup_proven": False, "attempt_status": "partial",
                                          "zv_packet_sha256": "c" * 64, "budget_actions_sha256": "d" * 64},
                     "verified_historical_facts": dict(owner.LEGACY_EXPECTED_FACTS),
                     "real_budget_application_authorized_now": False, "forbidden": list(owner.LEGACY_FORBIDDEN_ACTIONS)}
    approval = {"schema": owner.LEGACY_APPROVAL_SCHEMA, "decision": "authorize_legacy_cleanup_application",
                    "case": "gemini-sonnet", "attempt": 1, "historical_campaign_phase": owner.SONNET_PHASE,
                    "classification": owner.LEGACY_CLASSIFICATION}
    budget = owner.CanaryBudget(home=tmp_path / "home", phase=owner.SONNET_PHASE)
    budget.path.parent.mkdir(parents=True)
    s = {"budget": budget, "entry": entry, "canary": canary, "authority": authority, "approval": approval,
             "data": {"schema": owner.SCHEMA, "phase": owner.SONNET_PHASE, "cases": {"gemini-sonnet": {"attempts": [entry]}}},
             "canary_path": tmp_path / "canary.json", "authority_path": tmp_path / "authority.json",
             "approval_path": tmp_path / "approval.json"}
    s["evidence"] = {k: s[k] for k in ("canary_path", "authority_path", "approval_path")}
    refresh(s, monkeypatch)
    return s


def invoke(s, *, apply=False, case="gemini-sonnet", attempt=1, **overrides):
    return s["budget"].reconcile_legacy_attempt_cleanup(case, attempt, **{**s["evidence"], **overrides}, apply=apply)


@pytest.mark.parametrize("with_approval", [True, False])
def test_legacy_evaluate_wrapper_is_read_only(legacy, monkeypatch, with_approval):
    s, budget = legacy, legacy["budget"]
    evidence = dict(s["evidence"])
    if not with_approval:
        evidence.update(approval_path=None, approval_sha256=None)
    before = budget.path.read_bytes()

    def refuse_write(*args, **kwargs):
        pytest.fail("evaluation attempted a budget write or lock")

    monkeypatch.setattr(budget, "_write", refuse_write)
    monkeypatch.setattr(owner.fcntl, "flock", refuse_write)
    result = budget.evaluate_legacy_attempt_cleanup("gemini-sonnet", 1, **evidence)
    assert result["status"] == "eligible"
    assert budget.path.read_bytes() == before
    assert not budget.lock_path.exists()


@pytest.mark.parametrize("apply", [True, False, 1, None])
def test_legacy_evaluate_wrapper_rejects_explicit_apply(legacy, apply):
    s, budget = legacy, legacy["budget"]
    before = budget.path.read_bytes()
    with pytest.raises(owner.CanaryBudgetError, match="^legacy evaluation is read-only; apply is not accepted$"):
        budget.evaluate_legacy_attempt_cleanup("gemini-sonnet", 1, **s["evidence"], apply=apply)
    assert budget.path.read_bytes() == before
    assert not budget.lock_path.exists()
    assert json.loads(before)["cases"]["gemini-sonnet"]["attempts"][0]["cleanup_proven"] is False


def test_legacy_evaluate_wrapper_rejects_apply_before_delegation(legacy, monkeypatch):
    budget = legacy["budget"]
    before = budget.path.read_bytes()

    def refuse_delegation(*args, **kwargs):
        pytest.fail("explicit apply reached reconciliation")

    monkeypatch.setattr(budget, "reconcile_legacy_attempt_cleanup", refuse_delegation)
    with pytest.raises(owner.CanaryBudgetError, match="^legacy evaluation is read-only; apply is not accepted$"):
        budget.evaluate_legacy_attempt_cleanup("gemini-sonnet", 1, apply=True)
    assert budget.path.read_bytes() == before
    assert not budget.lock_path.exists()


def test_legacy_evaluate_wrapper_readback_does_not_write(legacy, monkeypatch):
    s, budget = legacy, legacy["budget"]
    assert invoke(s, apply=True)["status"] == "reconciled"
    before = budget.path.read_bytes()

    def refuse_write(*args, **kwargs):
        pytest.fail("readback attempted a budget write or lock")

    monkeypatch.setattr(budget, "_write", refuse_write)
    monkeypatch.setattr(owner.fcntl, "flock", refuse_write)
    assert budget.evaluate_legacy_attempt_cleanup("gemini-sonnet", 1, **s["evidence"])["status"] == "already_reconciled"
    assert budget.path.read_bytes() == before


def test_shipped_permit_is_pinned_and_caller_cannot_override():
    assert owner.LEGACY_SOURCE_PERMIT == (owner.SONNET_PHASE, "gemini-sonnet", 1)
    assert owner.PINNED_CANARY_SHA256 == "8565bcbb8b7b0d7c70edfeee8e6d11617e045b89380e92efa8ba7aad9e2f0c2a"
    assert owner.PINNED_AUTHORITY_SHA256 == "efb61da9401ed67f10ff76bcbd5beaeac5c11b51950017b866b90b3b26e3ebca"
    assert "permit" not in inspect.signature(owner.evaluate_legacy_cleanup_reconciliation).parameters
    assert "permit" not in inspect.signature(owner.CanaryBudget.reconcile_legacy_attempt_cleanup).parameters


def test_evaluate_apply_readback_preserve_history_and_retry_rules(legacy, monkeypatch):
    s, budget = legacy, legacy["budget"]
    original = copy.deepcopy(s["entry"])
    before = budget.path.read_bytes()
    assert invoke(s, approval_path=None, approval_sha256=None)["status"] == "eligible"
    assert budget.path.read_bytes() == before and not budget.lock_path.exists()
    with pytest.raises(owner.PredecessorCleanupError):
        budget.reserve("gemini-sonnet", cause="repair")
    assert invoke(s, apply=True)["status"] == "reconciled"
    actual = json.loads(budget.path.read_bytes())["cases"]["gemini-sonnet"]["attempts"][0]
    audit = actual.pop("cleanup_reconciliation")
    assert actual == {**original, "cleanup_proven": True}
    assert audit["original_cleanup_proven"] is False
    assert audit["original_attempt_sha256"] == owner.canonical_attempt_sha256(original)
    assert audit["recomputed_historical_facts"] == owner.LEGACY_EXPECTED_FACTS
    assert not {"receipt_sha256", "classification_inputs", "worker_drain"} & audit.keys()
    assert not owner.evaluate_cleanup_reconciliation(actual, s["canary_path"], case="gemini-sonnet", phase=owner.SONNET_PHASE)["ok"]
    accepted = budget.path.read_bytes()
    assert invoke(s, apply=True)["status"] == "already_reconciled"
    assert invoke(s)["status"] == "already_reconciled" and budget.path.read_bytes() == accepted
    with pytest.raises(owner.UnchangedCauseError):
        budget.reserve("gemini-sonnet", cause="initial_run")
    monkeypatch.setattr(owner.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="fixture-start"))
    assert budget.reserve("gemini-sonnet", cause="repair")["attempt"] == 2
    after_two = budget.path.read_bytes()
    with pytest.raises(owner.CanaryBudgetError):
        invoke(s)
    assert budget.path.read_bytes() == after_two
    budget.record_disposition("gemini-sonnet", 2, status="partial", cleanup_proven=True)
    with pytest.raises(owner.BudgetExhaustedError):
        budget.reserve("gemini-sonnet", cause="third")


DELETE = object()


def change(s, path, value):
    parts = path.split(".")
    target = s
    for part in parts[:-1]:
        target = target[part]
    if value is DELETE:
        target.pop(parts[-1])
    else:
        target[parts[-1]] = value


# Fixture hashes are rebound so a hash refusal cannot mask a semantic gap.
REFUSALS = [
    ("entry.details.source_identity", "other"), ("entry.details.bundle_sha256", "other"),
    ("canary.parent_id", "other"), ("entry.pid", 999), ("entry.pgid", 999),
    ("entry.created_at", 3.0), ("entry.status", "completed"), ("entry.attempt", True),
    ("canary.parent_cleanup.cleanup_proven", False), ("canary.parent_cleanup.verified_absence", DELETE),
    ("canary.parent_cleanup.nested_group_status", {"202": "present"}),
    ("canary.parent_cleanup.failure_reasons", ["uncertain"]),
    ("canary.parent_cleanup.termination.nested_pgids", [303]),
    ("canary.stage_ok", False), ("canary.stage_meta.exit_code", 1),
    ("canary.stage_meta.antigravity_evidence.process_group_cleanup.group_absent", False),
    ("canary.admission", {"child": 1}), ("canary.worker_results", [{"child": 1}]),
    ("canary.native_admission", [{"child": 1}]), ("canary.native_sonnet_count", 1),
    ("canary.capacity_receipt.max_sonnet", 4), ("canary.capacity_receipt.borrowing", DELETE),
    ("canary.stage_meta.worker_capability.native_worker.enabled", True),
    ("canary.stage_meta.worker_capability.reason", "registration timing unknown"),
    ("canary.stage_meta.worker_capability.allowed", True),
    ("canary.stage_meta.worker_disposition.reason", "different"),
    ("canary.stage_meta.worker_drain", None), ("canary.classification_inputs", {}),
    ("entry.details.receipt_sha256", "e" * 64), ("entry.details.classification_inputs", {}),
    ("authority.schema", "wrong"), ("authority.phase", "wrong"),
    ("authority.historical_canary.filename", "wrong"), ("authority.forbidden", []),
    ("authority.real_budget_application_authorized_now", True),
    ("authority.verified_historical_facts.worker_admissions", False),
    ("approval.reviewed_authority_sha256", "wrong"), ("approval.classification", "wrong"),
    ("approval.original_attempt_sha256", "wrong"),
]


@pytest.mark.parametrize("path,value", REFUSALS, ids=[p for p, _ in REFUSALS])
def test_semantic_refusal_never_mutates_budget(legacy, monkeypatch, path, value):
    s = legacy
    change(s, path, value)
    changed_approval = copy.deepcopy(s["approval"])
    refresh(s, monkeypatch)
    if path.startswith("approval."):
        s["evidence"]["approval_sha256"] = write_json(s["approval_path"], changed_approval)
    before = s["budget"].path.read_bytes()
    with pytest.raises(owner.CanaryBudgetError):
        invoke(s, apply=True)
    assert s["budget"].path.read_bytes() == before and not s["budget"].lock_path.exists()


@pytest.mark.parametrize("field", ["canary_path", "authority_path", "approval_path"])
@pytest.mark.parametrize("damage", ["hash", "missing", "malformed", "symlink"])
def test_file_evidence_refusal_preserves_budget(legacy, field, damage):
    s, path = legacy, legacy[field]
    if damage == "hash":
        path.write_bytes(path.read_bytes() + b" ")
    elif damage == "missing":
        path.unlink()
    elif damage == "malformed":
        path.write_text("{")
    else:
        retained = path.with_suffix(".retained")
        path.rename(retained)
        path.symlink_to(retained)
    before = s["budget"].path.read_bytes()
    with pytest.raises(owner.CanaryBudgetError):
        invoke(s, apply=True)
    assert s["budget"].path.read_bytes() == before


@pytest.mark.parametrize("case,attempt,phase", [("codex-sonnet", 1, owner.SONNET_PHASE),
                                             ("gemini-sonnet", 2, owner.SONNET_PHASE),
                                             ("gemini-sonnet", 1, owner.DEFAULT_PHASE)])
def test_wrong_campaign_case_attempt_refused(legacy, case, attempt, phase):
    s = legacy
    before = s["budget"].path.read_bytes()
    s["budget"].phase = phase
    with pytest.raises(owner.CanaryBudgetError):
        invoke(s, apply=True, case=case, attempt=attempt)
    assert s["budget"].path.read_bytes() == before


@pytest.mark.parametrize("damage", ["attempt2", "case_disposition", "missing_budget", "approval_missing", "duplicate_json"])
def test_later_state_or_missing_authority_refused(legacy, damage):
    s, budget = legacy, legacy["budget"]
    kwargs = {}
    if damage == "attempt2":
        s["data"]["cases"]["gemini-sonnet"]["attempts"].append({"attempt": 2, "status": "partial"})
        budget._write(s["data"])
    elif damage == "case_disposition":
        s["data"]["cases"]["gemini-sonnet"]["disposition"] = "contradictory"
        budget._write(s["data"])
    elif damage == "missing_budget":
        budget.path.unlink()
    elif damage == "approval_missing":
        kwargs = {"approval_path": None, "approval_sha256": None}
    else:
        budget.path.write_text('{"schema":"ignored",' + budget.path.read_text()[1:])
    before = budget.path.read_bytes() if budget.path.exists() else None
    with pytest.raises(owner.CanaryBudgetError):
        invoke(s, apply=True, **kwargs)
    assert (budget.path.read_bytes() if budget.path.exists() else None) == before
    assert not budget.lock_path.exists()


@pytest.mark.parametrize("field", ["classification", "authority_sha256", "canary_sha256", "approval_sha256",
                                 "original_attempt_sha256", "recomputed_historical_facts", "original_cleanup_proven"])
def test_contradictory_second_classification_refused(legacy, field):
    s = legacy
    invoke(s, apply=True)
    data = json.loads(s["budget"].path.read_bytes())
    data["cases"]["gemini-sonnet"]["attempts"][0]["cleanup_reconciliation"][field] = "contradiction"
    s["budget"]._write(data)
    before = s["budget"].path.read_bytes()
    with pytest.raises(owner.CanaryBudgetError):
        invoke(s, apply=True)
    assert s["budget"].path.read_bytes() == before


def test_budget_race_is_not_overwritten(legacy, monkeypatch):
    s, real = legacy, owner.fcntl.flock
    concurrent = s["budget"].path.read_bytes() + b" "
    def race(fd, operation):
        if operation == owner.fcntl.LOCK_EX:
            s["budget"].path.write_bytes(concurrent)
        return real(fd, operation)
    monkeypatch.setattr(owner.fcntl, "flock", race)
    with pytest.raises(owner.CanaryBudgetError, match="budget changed"):
        invoke(s, apply=True)
    assert s["budget"].path.read_bytes() == concurrent


def test_cli_requires_explicit_home_and_separate_application_approval(legacy, capsys):
    s = legacy
    with pytest.raises(SystemExit) as missing:
        owner.main(["legacy-reconcile"])
    assert missing.value.code == 2
    args = ["legacy-reconcile", "--home", str(s["budget"].path.parents[5]),
            "--canary", str(s["canary_path"]), "--authority", str(s["authority_path"]),
            "--authority-sha256", s["evidence"]["authority_sha256"]]
    before = s["budget"].path.read_bytes()
    assert owner.main(args) == 0
    assert owner.main([*args, "--apply"]) == 2
    assert s["budget"].path.read_bytes() == before
    assert owner.main([*args, "--apply", "--approval", str(s["approval_path"]),
                       "--approval-sha256", s["evidence"]["approval_sha256"]]) == 0
    assert '"status": "reconciled"' in capsys.readouterr().out
