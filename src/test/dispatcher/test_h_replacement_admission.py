"""APG166W-H-RECOVERY1 Decision B: one explicit replacement of a proven no-start failure.

A consumed unit whose attempt failed before any provider invocation may be
replaced at most once, only through a separate manager replacement
authorization bound by a ``apg.h-live-grant/v2``.  Every record here is
disposable fixture authority in a temporary custody root (``h_live_fixtures``);
the provider is a local counting fake.  The real ``admit``/``consume``/
``construct_arm``/``run_granted_pair``/``accounting``/``assembly`` owners run
unpatched; only mechanical-evidence recomputation uses the existing fixture
seam and, where stated, the calibration inventory is narrowed.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from testing.h_eval import assembly, evaluate, execution, granted_execution, live_admission
from testing.h_eval.runtime_manifest import manifest_digest
from h_live_fixtures import ROOT, Authority, _write_private, fake_provider, sealed_runtime, starts

STATIC, ADAPTIVE = "scenario-01/static", "scenario-01/adaptive"
AdmissionError = live_admission.AdmissionError


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stamp(delta: timedelta) -> str:
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


def _world(tmp_path, monkeypatch, **provider_options):
    provider, counter = fake_provider(tmp_path / "fixture", **provider_options)
    home = tmp_path / "home"
    runtime = sealed_runtime(provider, home)
    skills = home / ".agents" / "skills"
    skills.mkdir(parents=True)
    return {"authority": Authority(tmp_path, monkeypatch, runtime), "runtime": runtime,
            "counter": counter, "tmp": tmp_path, "skills": skills}


@pytest.fixture
def world(tmp_path, monkeypatch):
    return _world(tmp_path, monkeypatch)


def _live_arm(world, authorization, name, scenario_id="scenario-01", mode="static"):
    return execution.construct_arm(
        arm_dir=world["tmp"] / name, source_root=ROOT, scenario_id=scenario_id, mode=mode,
        execution="live", runtime_inputs=world["runtime"], live_authorization=authorization,
    )


def _oracle_double(monkeypatch):
    from testing.h_eval import oracles

    def evaluate_(subject, returned, scenario):
        return {"schema": "apg.h-task-oracle/v1", "oracle": scenario["expected_outcome"]["quality_oracle"],
                "status": "fail", "evidence": [{"kind": "test-double", "sha256": "0" * 64, "bytes": 0}]}

    monkeypatch.setattr(oracles, "oracle_for", lambda scenario: evaluate_)


def _failed_predecessor(world, name="arm-1", units=(STATIC, ADAPTIVE)):
    """Decision 1 consumes STATIC; a FIFO refuses observation before the provider."""
    fifo = world["skills"] / "pipe"
    os.mkfifo(fifo)
    authorization = world["authority"].grant(list(units), name="grant-1.json")
    result = _live_arm(world, authorization, name)
    fifo.unlink()
    assert result["status"] == "incomplete" and result["provider_invocations"] == 0
    assert result["failure_detail"]["step"] == "observation_begin"
    assert starts(world["counter"]) == 0
    return authorization


def _decision_two(world) -> None:
    authority = world["authority"]
    authority.decision = authority.decision_record(decision_id="decision-2")
    authority.decision_path = authority.write_decision(authority.decision, "decision-2.json")


def _ref(path: Path) -> dict:
    return {"path": str(path), "sha256": _sha(path)}


def _authorize(world, *, arm="arm-1", unit=STATIC, name="replacement.json", mutate=None,
               manager_evidence=None) -> dict:
    authority = world["authority"]
    custody, arm_dir = authority.custody, world["tmp"] / arm
    result = json.loads((arm_dir / "result.json").read_text())
    old_decision = json.loads((custody / "decision.json").read_text())
    old_grant = json.loads((custody / "grant-1.json").read_text())
    ledger = live_admission._ledger_path(custody, STATIC)
    record = {
        "schema": live_admission.REPLACEMENT_SCHEMA, "replacement_id": name, "unit_id": unit,
        "custody_root": str(custody),
        "predecessor": {
            "decision_id": old_decision["decision_id"], "decision_sha256": old_decision["decision_sha256"],
            "decision_record": _ref(custody / "decision.json"),
            "grant_id": old_grant["grant_id"], "grant_sha256": old_grant["grant_sha256"],
            "grant_record": _ref(custody / "grant-1.json"), "ledger": _ref(ledger),
            "source_identity": json.loads(ledger.read_text())["source_identity"],
            "arm_dir": str(arm_dir), "result_sha256": _sha(arm_dir / "result.json"),
            "integrity_sha256": _sha(arm_dir / "integrity.json"),
        },
        "disposition": {"kind": live_admission.NO_START, "provider_invocations": 0,
                        "failure": result["failure"],
                        "failure_step": (result.get("failure_detail") or {}).get("step"),
                        "manager_evidence": manager_evidence},
        "successor": {"decision_sha256": authority.decision["decision_sha256"],
                      "source_identity": authority.facts["source_identity"],
                      "runtime_manifest_sha256": manifest_digest(world["runtime"])},
        "max_replacements": 1, "retries": 0, "replay_prohibited": True,
        "issued_at": _stamp(timedelta(minutes=-1)), "valid_until": _stamp(timedelta(hours=1)),
    }
    if mutate is not None:
        mutate(record)
    record["authorization_sha256"] = live_admission.self_digest(record, "authorization_sha256")
    return _write_private(custody / name, record)


def _grant_v2(world, units, replacements, *, name="grant-2.json", calibration_attempts=None, **changes):
    return world["authority"].grant(
        list(units), name=name, schema=live_admission.GRANT_SCHEMA_V2, replacements=replacements,
        calibration_attempts=calibration_attempts, **changes)


def _snapshot(*roots: Path) -> dict:
    found = {}
    for root in roots:
        for path in [root] if root.is_file() else sorted(root.rglob("*")):
            info = path.lstat()
            found[str(path)] = (stat.S_IMODE(info.st_mode),
                                path.read_bytes() if stat.S_ISREG(info.st_mode) else None)
    return found


def _history(world, arm="arm-1") -> dict:
    custody = world["authority"].custody
    return _snapshot(custody / "decision.json", custody / "grant-1.json",
                     live_admission._ledger_path(custody, STATIC), world["tmp"] / arm)


def _refused(world, authorization, match, unit=STATIC):
    before = _history(world)
    count = starts(world["counter"])
    with pytest.raises(AdmissionError, match=match):
        live_admission.admit(ROOT, authorization, unit, runtime_inputs=world["runtime"])
    assert not (world["authority"].custody / live_admission.REPLACEMENT_LEDGER).exists()
    assert _history(world) == before and starts(world["counter"]) == count


def _reseal(arm_dir: Path, change) -> None:
    """Author a retained result variant with a recomputed integrity inventory."""
    result = json.loads((arm_dir / "result.json").read_text())
    change(result)
    (arm_dir / "result.json").unlink()
    execution._write_json(arm_dir / "result.json", result)
    (arm_dir / "integrity.json").unlink()
    execution._persist_integrity(arm_dir)


# --- legacy behavior -----------------------------------------------------------


def test_new_decision_with_v1_grant_still_cannot_replay(world):
    _failed_predecessor(world)
    _decision_two(world)
    _refused(world, world["authority"].grant([STATIC], name="grant-2.json"), "another grant")
    _refused(world, _grant_v2(world, [STATIC], {}), "another grant")


# --- one explicitly authorized replacement --------------------------------


def test_one_replacement_counts_one_start_and_preserves_history(world, monkeypatch):
    first = _failed_predecessor(world)
    predecessor_receipt = execution.read_arm_result(world["tmp"] / "arm-1")["live_admission"]
    history = _history(world)
    _decision_two(world)
    authorization = _grant_v2(world, [STATIC], {STATIC: _authorize(world)})
    _oracle_double(monkeypatch)
    result = _live_arm(world, authorization, "arm-2")
    assert result["status"] == "complete", result.get("failure_detail")
    assert starts(world["counter"]) == 1 and result["provider_invocations"] == 1
    receipt = result["live_admission"]
    assert receipt["schema"] == live_admission.REPLACEMENT_RECEIPT_SCHEMA
    assert receipt["attempt"] == "replacement-1" and receipt["replacement_id"] == "replacement.json"
    assert Path(receipt["ledger_path"]).parent.name == live_admission.REPLACEMENT_LEDGER
    assert live_admission.verify_receipt(receipt, unit=STATIC)["schema"] == (
        live_admission.REPLACEMENT_CONSUMPTION_SCHEMA)
    assert _history(world) == history  # every original byte and mode is preserved
    readback = execution.read_arm_result(world["tmp"] / "arm-2")
    assert readback["qualification_eligibility"]["status"] == "eligible"
    # Accounting separates the historical attempt, the reservation and starts.
    report = live_admission.accounting(ROOT, authorization, arm_receipts={STATIC: receipt},
                                       arm_results={STATIC: readback})
    row = report["units"][0]
    assert row["attempt"] == "replacement-1" and row["status"] == "retained"
    assert row["predecessor"]["status"] == "historical-consumed-incomplete"
    assert row["predecessor"]["selected"] is False
    assert row["predecessor"]["grant_sha256"] == json.loads(
        Path(first["grant_path"]).read_text())["grant_sha256"]
    assert report["historical_attempts"] == 1 and report["replacement_reservations"] == 1
    assert report["provider_invocations"] == {"observed": 1, "zero": 0, "positive": 1, "unobserved": 0}
    assert report["provider_starts_by_accounting"] == 0
    old = live_admission.accounting(ROOT, authorization, arm_receipts={STATIC: predecessor_receipt})
    assert old["units"][0]["status"] == "consumed-missing-result"
    # The predecessor's own decision still accounts for its consumed attempt.
    history_report = live_admission.accounting(ROOT, first)
    assert history_report["missing_results"] == [STATIC] and history_report["unconsumed"] == [ADAPTIVE]
    # Assembly readback through the admission block after the replacement.
    monkeypatch.setattr(live_admission, "all_units", lambda root: [STATIC])
    block = assembly._admission_block(ROOT, assembly.assemble_raw(ROOT, [world["tmp"] / "arm-2"]),
                                      authorization)
    assert block["scenario_units"] == 1
    assert block["decision_sha256"] == world["authority"].decision["decision_sha256"]
    # Replay of the replacement is refused before any arm exists.
    with pytest.raises(ValueError, match="replacement already used"):
        _live_arm(world, authorization, "arm-3")
    assert not (world["tmp"] / "arm-3").exists() and starts(world["counter"]) == 1


def test_second_replacement_with_new_id_and_grant_is_refused(world, monkeypatch):
    _failed_predecessor(world)
    _decision_two(world)
    _oracle_double(monkeypatch)
    _live_arm(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world)}), "arm-2")
    assert starts(world["counter"]) == 1
    again = _grant_v2(world, [STATIC], {STATIC: _authorize(world, name="replacement-b.json")},
                      name="grant-3.json")
    with pytest.raises(AdmissionError, match="another grant"):
        live_admission.admit(ROOT, again, STATIC, runtime_inputs=world["runtime"])
    assert starts(world["counter"]) == 1


def test_concurrent_duplicate_consumption_is_refused(world):
    _failed_predecessor(world)
    history = _history(world)
    _decision_two(world)
    authorization = _grant_v2(world, [STATIC], {STATIC: _authorize(world)})
    first = live_admission.admit(ROOT, authorization, STATIC, runtime_inputs=world["runtime"])
    second = live_admission.admit(ROOT, authorization, STATIC, runtime_inputs=world["runtime"])
    receipt = live_admission.consume(first)
    with pytest.raises(AdmissionError, match="replacement already used"):
        live_admission.consume(second)
    assert live_admission.verify_receipt(receipt, unit=STATIC)
    assert sorted(p.name for p in (world["authority"].custody / "h-replacement-consumed").iterdir()) == [
        "scenario-01--static.json"]
    assert _history(world) == history and starts(world["counter"]) == 0


# --- invalid, absent or confused authority --------------------------------


def _set(path, value):
    def change(record):
        target = record
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    return change


@pytest.mark.parametrize("case,match", [
    ("missing-file", "replacement authorization is unavailable"),
    ("grant-digest", "digest differs from the grant"),
    # A template or a drifted ledger binding cannot even justify listing the
    # consumed unit: refused by the unconsumed-unit guard before eligibility.
    ("template", "already consumed under another grant"),
    ("self-digest", "authorization digest mismatch"),
    ("stale", "authorization is stale"),
    ("group-writable", "private operator-owned record"),
    ("unit-mismatch", "does not name this unit"),
    ("two-replacements", "exactly one start"),
    ("retry", "exactly one start"),
    ("successor-old-decision", "successor differs"),
    ("successor-source", "successor differs"),
    ("successor-runtime", "successor differs"),
    ("disposition-positive", "not a pre-provider no-start"),
    ("ledger-lineage", "already consumed under another grant"),
    ("ledger-noncanonical", "canonical predecessor ledger"),
    ("grant-lineage", "predecessor grant bytes differ"),
    ("decision-lineage", "predecessor decision identity differs"),
    ("result-lineage", "arm evidence differs"),
    ("arm-lineage", "missing or tampered"),
    ("failure-step", "not a proven pre-provider step"),
])
def test_invalid_successor_authority_is_refused(world, case, match):
    _failed_predecessor(world)
    _decision_two(world)
    custody = world["authority"].custody
    mutations = {
        "unit-mismatch": _set(["unit_id"], ADAPTIVE),
        "two-replacements": _set(["max_replacements"], 2),
        "retry": _set(["retries"], 1),
        "stale": _set(["valid_until"], _stamp(timedelta(minutes=-1))),
        "successor-old-decision": _set(["successor", "decision_sha256"],
                                       json.loads((custody / "decision.json").read_text())["decision_sha256"]),
        "successor-source": _set(["successor", "source_identity"], "1" * 64),
        "successor-runtime": _set(["successor", "runtime_manifest_sha256"], "2" * 64),
        "disposition-positive": _set(["disposition", "provider_invocations"], 1),
        "ledger-lineage": _set(["predecessor", "ledger", "sha256"], "3" * 64),
        "grant-lineage": _set(["predecessor", "grant_record", "sha256"], "4" * 64),
        "decision-lineage": _set(["predecessor", "decision_sha256"], "5" * 64),
        "result-lineage": _set(["predecessor", "result_sha256"], "6" * 64),
        "arm-lineage": _set(["predecessor", "arm_dir"], str(world["tmp"] / "no-such-arm")),
        "failure-step": _set(["disposition", "failure_step"], "provider_stdin"),
    }
    if case == "ledger-noncanonical":
        copy = custody / "copied-ledger.json"
        copy.write_bytes(live_admission._ledger_path(custody, STATIC).read_bytes())
        copy.chmod(0o600)
        mutations[case] = _set(["predecessor", "ledger"], _ref(copy))
    reference = _authorize(world, mutate=mutations.get(case))
    if case == "missing-file":
        reference = {"path": str(custody / "absent.json"), "sha256": "7" * 64}
    elif case == "grant-digest":
        reference = {**reference, "sha256": "8" * 64}
    elif case == "template":
        reference = _write_private(custody / "template.json",
                                   live_admission.replacement_template()["replacement-authorization"])
    elif case == "self-digest":
        record = json.loads(Path(reference["path"]).read_text())
        reference = _write_private(custody / "replacement.json", {**record, "authorization_sha256": "9" * 64})
    elif case == "group-writable":
        world["authority"].report_group_writable(reference["path"])
    _refused(world, _grant_v2(world, [STATIC], {STATIC: reference}), match)


def test_grant_shape_and_start_ceiling_stay_enforced_for_v2(world):
    _failed_predecessor(world)
    _decision_two(world)
    reference = _authorize(world)
    for units, replacements, changes, match in (
        ([ADAPTIVE], {STATIC: reference}, {}, "replacement must name a granted scenario unit"),
        ([STATIC], {STATIC: reference}, {"start_ceiling": 2}, "start ceiling"),
        ([STATIC], {STATIC: reference}, {"retries": 1}, "no replay and no retry"),
        ([STATIC], {STATIC: reference}, {"calibration_attempts": {}}, "only by an acceptance grant"),
        ([STATIC], {STATIC: {"path": "relative", "sha256": "0" * 64}}, {}, "one record"),
    ):
        with pytest.raises(AdmissionError, match=match):
            live_admission.admit(ROOT, _grant_v2(world, units, replacements, **changes), units[0],
                                 runtime_inputs=world["runtime"])
    template = live_admission.replacement_template()["live-grant-v2"]
    assert template["template"].startswith("TEMPLATE-NOT-AUTHORITY")
    assert not (world["authority"].custody / live_admission.REPLACEMENT_LEDGER).exists()


def test_old_decision_and_other_unit_confusion_is_refused(world):
    _failed_predecessor(world)
    # Still under decision 1: a predecessor can never be replaced by its own decision.
    same = _grant_v2(world, [STATIC], {STATIC: _authorize(world)}, name="grant-same.json")
    _refused(world, same, "earlier decision")
    _decision_two(world)
    other = _grant_v2(world, ["scenario-02/static"], {"scenario-02/static": _authorize(world)})
    _refused(world, other, "predecessor ledger is absent", unit="scenario-02/static")
    renamed = _grant_v2(world, ["scenario-02/static"],
                        {"scenario-02/static": _authorize(world, unit="scenario-02/static")},
                        name="grant-renamed.json")
    _refused(world, renamed, "predecessor ledger is absent", unit="scenario-02/static")


# --- start status must be proven zero -------------------------------------


def test_positive_start_predecessor_is_refused(tmp_path, monkeypatch):
    world = _world(tmp_path, monkeypatch, exit_code=3)
    result = _live_arm(world, world["authority"].grant([STATIC], name="grant-1.json"), "arm-1")
    assert result["provider_invocations"] == 1 and starts(world["counter"]) == 1
    _decision_two(world)
    _refused(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world)}), "positive or unknown")


def test_unknown_start_predecessor_is_refused(world, monkeypatch):
    with monkeypatch.context() as patch:
        def unavailable(_environment):
            raise ValueError("fixture provider runner unavailable")
        patch.setattr(execution, "_bound_provider_runner", unavailable)
        result = _live_arm(world, world["authority"].grant([STATIC], name="grant-1.json"), "arm-1")
    # The counter precedes provider_environment: 1 is not a proven start and
    # is never guessed to be a no-start.
    assert result["failure_detail"]["step"] == "provider_environment"
    assert result["provider_invocations"] == 1 and starts(world["counter"]) == 0
    assert (world["tmp"] / "arm-1/run/provider.stdin").is_file()
    _decision_two(world)
    _refused(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world)}), "positive or unknown")
    # A resealed result that merely asserts zero still carries provider stdin.
    arm = world["tmp"] / "arm-1"

    def claim_zero(value):
        value.update(provider_invocations=0)
        value.pop("prepared")
        value["failure_detail"]["step"] = "observation_begin"

    _reseal(arm, claim_zero)
    _refused(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world, name="r-zero.json")},
                              name="grant-zero.json"), "provider transport artifacts")
    _reseal(arm, lambda value: value.pop("provider_invocations"))
    _refused(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world, name="r-missing.json")},
                              name="grant-missing.json"), "positive or unknown")


def test_retained_provider_return_predecessor_is_refused(tmp_path, monkeypatch):
    """APG166W-H-POSTRUN1: earlier stream retention only adds refusal grounds."""
    world = _world(tmp_path, monkeypatch, exit_code=1, stdout=False, stderr=b"fixture diagnostic\n")
    result = _live_arm(world, world["authority"].grant([STATIC], name="grant-1.json"), "arm-1")
    arm = world["tmp"] / "arm-1"
    assert result["provider_invocations"] == 1 and starts(world["counter"]) == 1
    assert result["postrun_checks"]["provider_return"]["status"] == "retained"
    assert (arm / "run/provider.stderr").read_bytes() == b"fixture diagnostic\n"
    _decision_two(world)
    _refused(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world)}), "positive or unknown")

    def claim_zero(value):
        value.update(provider_invocations=0)
        for field in ("prepared", "provider_terminal"):
            value.pop(field)
        value["failure_detail"]["step"] = "observation_begin"

    _reseal(arm, claim_zero)
    _refused(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world, name="r-zero.json")},
                              name="grant-zero.json"), "provider transport artifacts")
    assert starts(world["counter"]) == 1


def test_tampered_or_completed_predecessor_is_refused(world):
    _failed_predecessor(world)
    _decision_two(world)
    arm = world["tmp"] / "arm-1"
    authorization = _grant_v2(world, [STATIC], {STATIC: _authorize(world)})
    subject = arm / "subject" / "main.go"
    subject.chmod(0o600)
    subject.write_text(subject.read_text() + "// tampered\n")
    with pytest.raises(AdmissionError, match="missing or tampered"):
        live_admission.admit(ROOT, authorization, STATIC, runtime_inputs=world["runtime"])
    _reseal(arm, lambda value: value.update(status="complete"))
    _refused(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world, name="r-complete.json")},
                              name="grant-complete.json"), "not an incomplete attempt")


def test_legacy_predecessor_without_failure_detail_needs_manager_evidence(world, monkeypatch):
    _failed_predecessor(world)
    _decision_two(world)
    _reseal(world["tmp"] / "arm-1", lambda value: value.pop("failure_detail"))
    _refused(world, _grant_v2(world, [STATIC], {STATIC: _authorize(world)}), "exact manager evidence")
    guessed = _authorize(world, name="r-guess.json",
                         mutate=_set(["disposition", "failure_step"], "observation_begin"))
    _refused(world, _grant_v2(world, [STATIC], {STATIC: guessed}, name="grant-guess.json"),
             "exact manager evidence")
    evidence = world["tmp"] / "manager-evidence.md"
    evidence.write_text("manager disposition: exact retained pre-provider evidence\n")
    wrong = _authorize(world, name="r-wrong.json", manager_evidence={**_ref(evidence), "sha256": "0" * 64})
    _refused(world, _grant_v2(world, [STATIC], {STATIC: wrong}, name="grant-wrong.json"), "digest mismatch")
    bound = _authorize(world, name="r-bound.json", manager_evidence=_ref(evidence))
    authorization = _grant_v2(world, [STATIC], {STATIC: bound}, name="grant-bound.json")
    _oracle_double(monkeypatch)
    result = _live_arm(world, authorization, "arm-2")
    assert result["status"] == "complete" and starts(world["counter"]) == 1


# --- pair stop and calibration-to-acceptance ------------------------------


def test_failing_replacement_static_stops_the_pair(world):
    _failed_predecessor(world)
    history = _history(world)
    _decision_two(world)
    authorization = _grant_v2(world, [STATIC, ADAPTIVE], {STATIC: _authorize(world)})
    os.mkfifo(world["skills"] / "pipe")
    record = granted_execution.run_granted_pair(
        pair_dir=world["tmp"] / "pair-2", source_root=ROOT, scenario_id="scenario-01",
        live_authorization=authorization, runtime_inputs=world["runtime"],
    )
    assert set(record["arms"]) == {"static"} and "did not complete" in record["stopped"]
    assert record["arms"]["static"]["live_admission"]["attempt"] == "replacement-1"
    assert not (world["tmp"] / "pair-2/adaptive").exists() and starts(world["counter"]) == 0
    report = live_admission.accounting(ROOT, authorization)
    assert report["unconsumed"] == [ADAPTIVE] and report["replacement_reservations"] == 1
    assert _history(world) == history
    (world["skills"] / "pipe").unlink()
    again = _grant_v2(world, [STATIC], {STATIC: _authorize(world, name="r-again.json")}, name="grant-3.json")
    with pytest.raises(AdmissionError):
        live_admission.admit(ROOT, again, STATIC, runtime_inputs=world["runtime"])


def test_replacement_pair_completes_with_one_start_per_arm(world, monkeypatch):
    _failed_predecessor(world)
    _decision_two(world)
    authorization = _grant_v2(world, [STATIC, ADAPTIVE], {STATIC: _authorize(world)})
    _oracle_double(monkeypatch)
    record = granted_execution.run_granted_pair(
        pair_dir=world["tmp"] / "pair-2", source_root=ROOT, scenario_id="scenario-01",
        live_authorization=authorization, runtime_inputs=world["runtime"],
    )
    assert record["stopped"] is None and record["same_source"] is True, record
    assert starts(world["counter"]) == 2
    assert record["arms"]["static"]["live_admission"]["attempt"] == "replacement-1"
    assert record["arms"]["adaptive"]["live_admission"]["schema"] == live_admission.RECEIPT_SCHEMA


def _evaluation(world) -> dict:
    binary = world["tmp"] / "evaluation-binary"
    binary.write_bytes(b"fixture evaluation binary\n")
    seal = world["tmp"] / "evaluation-seal.json"
    seal.write_text(json.dumps(evaluate.make_seal(ROOT, binary)))
    return {"evaluation_seal": _ref(seal), "evaluation_binary": _ref(binary)}


def test_acceptance_uses_only_selected_current_decision_attempts(world, monkeypatch):
    full = live_admission.all_units(ROOT)
    # Narrow only the calibration set to Scenario 01; the unit inventory stays real.
    monkeypatch.setattr(live_admission, "CALIBRATION", ("scenario-01",))
    monkeypatch.setattr(live_admission, "all_units", lambda root: list(full))
    acceptance = "scenario-06/static"
    _failed_predecessor(world)
    _decision_two(world)
    evaluation = _evaluation(world)

    def accept(name, attempts):
        return _grant_v2(world, [acceptance], {}, name=name, calibration_attempts=attempts, **evaluation)

    def admit(authorization):
        return live_admission.admit(ROOT, authorization, acceptance, runtime_inputs=world["runtime"])

    predecessor = {"arm_dir": str(world["tmp"] / "arm-1"), "result_sha256": _sha(world["tmp"] / "arm-1/result.json")}
    # Only the old decision's failed canonical attempt exists: refused.
    with pytest.raises(AdmissionError, match="consumed first"):
        admit(accept("accept-a.json", {STATIC: predecessor, ADAPTIVE: predecessor}))
    # Replacement static fails again (incomplete); adaptive completes separately.
    authorization = _grant_v2(world, [STATIC, ADAPTIVE], {STATIC: _authorize(world)})
    os.mkfifo(world["skills"] / "pipe")
    _live_arm(world, authorization, "arm-2")
    (world["skills"] / "pipe").unlink()
    _oracle_double(monkeypatch)
    _live_arm(world, authorization, "arm-adaptive", mode="adaptive")
    adaptive = {"arm_dir": str(world["tmp"] / "arm-adaptive"),
                "result_sha256": _sha(world["tmp"] / "arm-adaptive/result.json")}
    incomplete = {"arm_dir": str(world["tmp"] / "arm-2"), "result_sha256": _sha(world["tmp"] / "arm-2/result.json")}
    with pytest.raises(AdmissionError, match="not a complete current attempt"):
        admit(accept("accept-b.json", {STATIC: incomplete, ADAPTIVE: adaptive}))
    with pytest.raises(AdmissionError):
        admit(accept("accept-c.json", {STATIC: predecessor, ADAPTIVE: adaptive}))
    # A legacy v1 acceptance grant never selects a replacement.
    legacy = world["authority"].grant([acceptance], name="accept-v1.json", **evaluation)
    with pytest.raises(AdmissionError, match="consumed first"):
        admit(legacy)
    assert starts(world["counter"]) == 1


def test_acceptance_admits_after_complete_selected_replacement(world, monkeypatch):
    full = live_admission.all_units(ROOT)
    monkeypatch.setattr(live_admission, "CALIBRATION", ("scenario-01",))
    monkeypatch.setattr(live_admission, "all_units", lambda root: list(full))
    _failed_predecessor(world)
    _decision_two(world)
    evaluation = _evaluation(world)
    authorization = _grant_v2(world, [STATIC, ADAPTIVE], {STATIC: _authorize(world)})
    _oracle_double(monkeypatch)
    record = granted_execution.run_granted_pair(
        pair_dir=world["tmp"] / "pair-2", source_root=ROOT, scenario_id="scenario-01",
        live_authorization=authorization, runtime_inputs=world["runtime"],
    )
    assert record["stopped"] is None and starts(world["counter"]) == 2
    attempts = {unit: {"arm_dir": str(world["tmp"] / "pair-2" / unit.split("/")[1]),
                       "result_sha256": _sha(world["tmp"] / "pair-2" / unit.split("/")[1] / "result.json")}
                for unit in (STATIC, ADAPTIVE)}
    grant = _grant_v2(world, ["scenario-06/static"], {}, name="accept.json",
                      calibration_attempts=attempts, **evaluation)
    state = live_admission.admit(ROOT, grant, "scenario-06/static", runtime_inputs=world["runtime"])
    assert state["unit_id"] == "scenario-06/static" and state["replacement"] is None
    # Pointing the static selection at the failed predecessor refuses.
    stale = {**attempts, STATIC: {"arm_dir": str(world["tmp"] / "arm-1"),
                                  "result_sha256": _sha(world["tmp"] / "arm-1/result.json")}}
    with pytest.raises(AdmissionError, match="not a complete current attempt"):
        live_admission.admit(ROOT, _grant_v2(world, ["scenario-06/static"], {}, name="accept-stale.json",
                                             calibration_attempts=stale, **evaluation),
                             "scenario-06/static", runtime_inputs=world["runtime"])
    assert starts(world["counter"]) == 2
