"""APG166V-H-COMPLETE1 external decision/grant admission for live H arms.

Only local fake executables run.  Refusals are asserted before any arm
directory, ledger record or provider start exists.
"""
from __future__ import annotations

import json
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from testing.h_eval import assembly, execution, execution_evidence, granted_execution, live_admission
from h_live_fixtures import (ROOT, Authority, _write_private, fake_provider, report_group_writable,
                             sealed_runtime, starts)

UNIT = "scenario-01/static"


@pytest.fixture
def world(tmp_path, monkeypatch):
    provider, counter = fake_provider(tmp_path / "fixture")
    runtime = sealed_runtime(provider, tmp_path / "home")
    return {"authority": Authority(tmp_path, monkeypatch, runtime), "runtime": runtime,
            "provider": provider, "counter": counter, "tmp": tmp_path}


def _live_arm(world, authorization, name="arm", scenario_id="scenario-01", mode="static"):
    return execution.construct_arm(
        arm_dir=world["tmp"] / name, source_root=ROOT, scenario_id=scenario_id, mode=mode,
        execution="live", runtime_inputs=world["runtime"], live_authorization=authorization,
    )


@pytest.mark.parametrize("authorization", [
    None, {}, {"authorized": True}, True,
    {"decision_path": "/absent/d.json", "grant_path": "/absent/g.json", "authorized": True},
])
def test_live_arm_refused_without_external_records(world, authorization):
    with pytest.raises(ValueError, match="admission unavailable"):
        _live_arm(world, authorization)
    assert not (world["tmp"] / "arm").exists()
    assert starts(world["counter"]) == 0


def test_feature_flag_is_not_a_live_grant(world, monkeypatch):
    monkeypatch.setattr(execution, "LIVE_ADMISSION_AVAILABLE", True)
    with pytest.raises(ValueError, match="admission unavailable"):
        _live_arm(world, {"authorized": True})
    assert execution.LIVE_ADMISSION_AVAILABLE is True  # patched only; source default stays False
    assert not (world["tmp"] / "arm").exists()


def _defect(authority: Authority, kind: str):
    if kind == "decision-digest":
        value = dict(authority.decision, decision_id="tampered")
        authority.write_decision(value)
        return authority.grant([UNIT])
    if kind == "grant-digest":
        return authority.grant([UNIT], redigest=False, grant_sha256="0" * 64)
    if kind == "stale-source":
        value = authority.decision_record(source={**authority.facts, "source_identity": "1" * 64})
        authority.decision = value
        authority.write_decision(value)
        return authority.grant([UNIT])
    if kind == "route":
        routes = dict(authority.decision["routes"])
        routes[UNIT] = "2" * 64
        authority.decision = authority.decision_record(routes=routes)
        authority.write_decision(authority.decision)
        return authority.grant([UNIT])
    if kind == "runtime":
        authority.decision = authority.decision_record(runtime={
            "live_runtime_manifest_sha256": "3" * 64,
            "transaction_directory": authority.transaction})
        authority.write_decision(authority.decision)
        return authority.grant([UNIT])
    if kind == "custody-inside-source":
        authority.decision = authority.decision_record(custody_root=str(ROOT))
        authority.write_decision(authority.decision)
        return authority.grant([UNIT])
    if kind == "expired":
        stamp = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return authority.grant([UNIT], valid_until=stamp)
    if kind == "template":
        templates = live_admission.template()
        authority.write_decision(templates["manager-decision"])
        return authority.grant([UNIT])
    if kind == "group-writable":
        authorization = authority.grant([UNIT])
        authority.report_group_writable(authorization["decision_path"])
        return authorization
    if kind == "evidence-bytes":
        Path(authority.evidence["host_mechanical_result"]["path"]).write_text("{}\n")
        return authority.grant([UNIT])
    if kind == "readiness-drift":
        authority.readiness_value = {**authority.readiness_value, "source_identity": "4" * 64}
        return authority.grant([UNIT])
    raise AssertionError(kind)


@pytest.mark.parametrize("kind", [
    "decision-digest", "grant-digest", "stale-source", "route", "runtime", "custody-inside-source",
    "expired", "template", "group-writable", "evidence-bytes", "readiness-drift",
])
def test_invalid_or_stale_authority_refused_before_arm(world, kind):
    authorization = _defect(world["authority"], kind)
    match = "manager decision must be a private operator-owned record" if kind == "group-writable" else None
    with pytest.raises(ValueError, match=match):
        _live_arm(world, authorization)
    assert not (world["tmp"] / "arm").exists()
    assert not (world["authority"].custody / live_admission.LEDGER).exists()
    assert starts(world["counter"]) == 0


@pytest.mark.parametrize("units,changes,message", [
    (["scenario-15/static"], {}, "unknown"),
    (["scenario-01/sideways"], {}, "unknown"),
    ([UNIT, UNIT], {}, "duplicated"),
    ([UNIT], {"start_ceiling": 54}, "ceiling"),
    ([UNIT], {"max_starts_per_unit": 2}, "one start"),
    ([UNIT], {"retries": 1}, "one start"),
    (["scenario-06/static"], {}, "separately sealed evaluation"),
])
def test_grant_shape_refusals(world, units, changes, message):
    authorization = world["authority"].grant(units, **changes)
    with pytest.raises(live_admission.AdmissionError, match=message):
        live_admission.admit(ROOT, authorization, units[0] if "15" not in units[0] else UNIT,
                             runtime_inputs=world["runtime"])


def test_acceptance_requires_consumed_calibration_first(world):
    evidence = world["tmp"] / "evaluation"
    evidence.mkdir()
    for name in ("seal.json", "binary"):
        (evidence / name).write_text("{}\n")
    import hashlib
    ref = {name: {"path": str(evidence / name),
                  "sha256": hashlib.sha256((evidence / name).read_bytes()).hexdigest()}
           for name in ("seal.json", "binary")}
    authorization = world["authority"].grant(["scenario-06/static"], evaluation_seal=ref["seal.json"],
                                             evaluation_binary=ref["binary"])
    with pytest.raises(live_admission.AdmissionError, match="calibration unit consumed first"):
        live_admission.admit(ROOT, authorization, "scenario-06/static", runtime_inputs=world["runtime"])


def test_unit_is_single_use_across_grants(world):
    authority = world["authority"]
    first = authority.grant([UNIT, "scenario-01/adaptive"], name="grant-a.json")
    admission = live_admission.admit(ROOT, first, UNIT, runtime_inputs=world["runtime"])
    receipt = live_admission.consume(admission)
    assert live_admission.verify_receipt(receipt, unit=UNIT)["status"] == "consumed-before-context"
    with pytest.raises(live_admission.AdmissionError, match="already consumed"):
        live_admission.admit(ROOT, first, UNIT, runtime_inputs=world["runtime"])
    with pytest.raises(live_admission.AdmissionError, match="already consumed"):
        live_admission.consume(admission)
    second = authority.grant([UNIT], name="grant-b.json")
    with pytest.raises(live_admission.AdmissionError, match="another grant"):
        live_admission.admit(ROOT, second, UNIT, runtime_inputs=world["runtime"])
    accounting = live_admission.accounting(ROOT, first)
    assert accounting["missing_results"] == [UNIT]
    assert accounting["unconsumed"] == ["scenario-01/adaptive"]
    assert accounting["provider_starts_by_accounting"] == 0


def test_forged_receipt_is_rejected(world):
    admission = live_admission.admit(ROOT, world["authority"].grant([UNIT]), UNIT,
                                     runtime_inputs=world["runtime"])
    receipt = live_admission.consume(admission)
    for field, value in (("ledger_sha256", "5" * 64), ("unit_id", "scenario-02/static"),
                         ("grant_sha256", "6" * 64)):
        with pytest.raises(live_admission.AdmissionError):
            live_admission.verify_receipt({**receipt, field: value}, unit=receipt["unit_id"])
    Path(receipt["ledger_path"]).chmod(0o600)
    Path(receipt["ledger_path"]).write_text("{}\n")
    with pytest.raises(live_admission.AdmissionError, match="changed"):
        live_admission.verify_receipt(receipt)


def test_admitted_live_arm_invokes_once_and_is_readable(world):
    authorization = world["authority"].grant([UNIT])
    result = _live_arm(world, authorization)
    assert starts(world["counter"]) == 1
    assert result["provider_invocations"] == 1
    assert result["route"]["execution"] == "live"
    receipt = result["live_admission"]
    assert live_admission.verify_receipt(receipt, unit=UNIT)["grant_sha256"] == receipt["grant_sha256"]
    admission_record = json.loads((world["tmp"] / "arm/admission.json").read_text())
    assert admission_record["live_admission"] == receipt
    readback = execution.read_arm_result(world["tmp"] / "arm")
    assert readback["live_admission"] == receipt
    # The real scenario oracle needs the host toolchain; with fake commands it
    # fails and that consumed failure must still be retained and readable.
    assert readback["status"] == "incomplete"
    with pytest.raises(ValueError, match="already consumed"):
        _live_arm(world, authorization, name="replay")
    assert not (world["tmp"] / "replay").exists()
    assert starts(world["counter"]) == 1
    accounting = live_admission.accounting(ROOT, authorization, arm_receipts={UNIT: readback["live_admission"]})
    assert accounting["retained"] == 1 and accounting["missing_results"] == []


def _oracle_double(monkeypatch):
    """Deterministic oracle double: oracle execution belongs to the host transaction."""
    from testing.h_eval import oracles

    def evaluate(subject, returned, scenario):
        return {"schema": "apg.h-task-oracle/v1", "oracle": scenario["expected_outcome"]["quality_oracle"],
                "status": "fail", "evidence": [{"kind": "test-double", "sha256": "0" * 64, "bytes": 0}]}

    monkeypatch.setattr(oracles, "oracle_for", lambda scenario: evaluate)


def test_granted_arm_is_eligible_and_assembles_with_receipt(world, monkeypatch):
    _oracle_double(monkeypatch)
    authorization = world["authority"].grant([UNIT])
    result = _live_arm(world, authorization)
    assert result["status"] == "complete", result.get("failure")
    readback = execution.read_arm_result(world["tmp"] / "arm")
    assert readback["qualification_eligibility"]["status"] == "eligible", readback["qualification_eligibility"]
    from testing.h_eval.preregistration import verify_bindings
    row = next(r for r in verify_bindings(ROOT)["scenarios"] if r["scenario_id"] == "scenario-01")
    arm = assembly._receipt_arm(row, "static", {**readback, "_arm_dir": str(world["tmp"] / "arm")})
    assert arm["coverage"]["source"] == "measured"
    assert arm["task_outcome"] == {"source": "measured", "value": "fail"}
    assert arm["live_admission"] == readback["live_admission"]
    assert arm["route"]["model_route"]["source"] == "measured"
    raw = assembly.assemble_raw(ROOT, [world["tmp"] / "arm"])
    missing = assembly._incomplete_arms(raw)
    assert "scenario-01/static" not in missing and missing[0] == "scenario-01/adaptive"
    assert len(missing) == 27
    # Narrow the derived inventory so one real granted arm exercises accounting.
    monkeypatch.setattr(live_admission, "all_units", lambda root: [UNIT])
    block = assembly._admission_block(ROOT, raw, authorization)
    assert block["scenario_units"] == 1
    assert block["decision_sha256"] == world["authority"].decision["decision_sha256"]
    with pytest.raises(ValueError, match="grant accounting is incomplete"):
        assembly._admission_block(ROOT, assembly.assemble_raw(ROOT), authorization)


def test_live_eligibility_requires_verified_admission_not_seal_flag(world):
    authorization = world["authority"].grant([UNIT])
    _live_arm(world, authorization)
    arm = world["tmp"] / "arm"
    result = json.loads((arm / "result.json").read_text())
    retained = json.loads((arm / "oracle-input/source-seal.json").read_text())
    assert retained["prerequisites_ready"] is False
    source = json.loads((arm / "oracle-input/activity.json").read_text())["source_binding"]
    route = json.loads((arm / "oracle-input/route.json").read_text())
    reason = execution_evidence._live_admission_reason
    assert reason(result["live_admission"], source, retained, route) is None
    assert reason(None, source, retained, route) == "source readiness prerequisites are not accepted"
    forged = {**result["live_admission"], "route_sha256": "7" * 64}
    assert reason(forged, source, retained, route).startswith("live admission receipt invalid")
    assert reason(result["live_admission"], source, retained,
                  {**route, "execution": "instrumented"}).startswith("live admission receipt invalid")


def test_consumed_provider_failure_is_retained_and_readable(tmp_path, monkeypatch):
    provider, counter = fake_provider(tmp_path / "fixture", exit_code=3)
    runtime = sealed_runtime(provider, tmp_path / "home")
    authority = Authority(tmp_path, monkeypatch, runtime)
    world = {"tmp": tmp_path, "runtime": runtime}
    authorization = authority.grant([UNIT])
    result = _live_arm(world, authorization)
    assert starts(counter) == 1
    assert result["status"] == "incomplete" and result["failure"] == "ValueError"
    assert result["provider_invocations"] == 1
    readback = execution.read_arm_result(tmp_path / "arm")
    assert readback["status"] == "incomplete"
    assert live_admission.verify_receipt(readback["live_admission"], unit=UNIT)
    assembled = assembly._receipt_arm({"frozen_oracle": {}, "routes": {"static": {}}, "scenario_id": "scenario-01"},
                                      "static", {**readback, "_arm_dir": str(tmp_path / "arm")})
    assert assembled["coverage"]["source"] == "unavailable"


def test_pair_stops_before_adaptive_after_static_failure(tmp_path, monkeypatch):
    provider, counter = fake_provider(tmp_path / "fixture", exit_code=4)
    runtime = sealed_runtime(provider, tmp_path / "home")
    authority = Authority(tmp_path, monkeypatch, runtime)
    authorization = authority.grant(["scenario-01/static", "scenario-01/adaptive"])
    record = granted_execution.run_granted_pair(
        pair_dir=tmp_path / "pair", source_root=ROOT, scenario_id="scenario-01",
        live_authorization=authorization, runtime_inputs=runtime,
    )
    assert starts(counter) == 1
    assert set(record["arms"]) == {"static"}
    assert "did not complete" in record["stopped"]
    assert not (tmp_path / "pair/adaptive").exists()
    accounting = live_admission.accounting(ROOT, authorization)
    assert accounting["unconsumed"] == ["scenario-01/adaptive"]
    assert json.loads((tmp_path / "pair/pair.json").read_text())["retries"] == 0


def test_pair_refused_without_grant_starts_nothing(world):
    record = granted_execution.run_granted_pair(
        pair_dir=world["tmp"] / "pair", source_root=ROOT, scenario_id="scenario-01",
        live_authorization={"authorized": True}, runtime_inputs=world["runtime"],
    )
    assert record["arms"]["static"]["status"] == "refused"
    assert "adaptive" not in record["arms"]
    assert starts(world["counter"]) == 0


def _raw(sources):
    rows = []
    for number in range(1, 16):
        sid = f"scenario-{number:02d}"
        arms = {}
        for mode in ("static", "adaptive"):
            source = sources(sid)
            measured = {"source": source, "value": 1 if source == "measured" else None}
            arms[mode] = {"coverage": measured, "task_outcome": measured, "authority": measured,
                          "route": {"execution": "live", "model_route": {"source": source}}}
            if source == "measured":
                arms[mode]["live_admission"] = {"unit_id": f"{sid}/{mode}"}
        rows.append({"scenario_id": sid, "arms": arms})
    return rows


def test_aggregation_names_missing_arms_and_keeps_scenario15_unavailable():
    measured_14 = _raw(lambda sid: "unavailable" if sid == "scenario-15" else "measured")
    assert assembly._incomplete_arms({"rows": measured_14, "scenario15": "contingent/unavailable"}) == []
    assert assembly._incomplete_arms({"rows": measured_14, "scenario15": "qualified"}) == [
        "scenario-15/static", "scenario-15/adaptive"]
    all_measured = _raw(lambda sid: "measured")
    assert assembly._incomplete_arms({"rows": all_measured, "scenario15": "contingent/unavailable"}) == [
        "scenario-15/static (measured while contingent)", "scenario-15/adaptive (measured while contingent)"]
    one_missing = _raw(lambda sid: "unavailable" if sid in ("scenario-07", "scenario-15") else "measured")
    assert assembly._incomplete_arms({"rows": one_missing, "scenario15": "contingent/unavailable"}) == [
        "scenario-07/static", "scenario-07/adaptive"]
    unadmitted = _raw(lambda sid: "unavailable" if sid == "scenario-15" else "measured")
    del unadmitted[0]["arms"]["static"]["live_admission"]
    assert assembly._incomplete_arms({"rows": unadmitted, "scenario15": "contingent/unavailable"}) == [
        "scenario-01/static"]


def test_aggregate_and_publication_refuse_without_grant(tmp_path):
    raw = assembly.assemble_raw(ROOT)
    with pytest.raises(ValueError, match="incomplete"):
        assembly.aggregate_complete(ROOT, raw)
    measured = {"rows": _raw(lambda sid: "unavailable" if sid == "scenario-15" else "measured"),
                "scenario15": "contingent/unavailable"}
    with pytest.raises(ValueError, match="external manager decision and grant required"):
        assembly.aggregate_complete(ROOT, measured)
    with pytest.raises(ValueError, match="unavailable"):
        assembly.write_aggregate(tmp_path / "aggregate.json", {"h_gate_established": False})
    with pytest.raises(ValueError, match="H gate"):
        assembly.write_aggregate(tmp_path / "aggregate.json", {"h_gate_established": True},
                                 root=ROOT, live_authorization={}, raw=measured)
    assert not (tmp_path / "aggregate.json").exists()


def test_source_default_live_admission_stays_closed():
    from testing.h_eval import d1_qualification
    assert execution.LIVE_ADMISSION_AVAILABLE is False
    assert d1_qualification.LIVE_ADMISSION_AVAILABLE is False
    templates = live_admission.template()
    assert set(templates) == {"manager-decision", "live-grant"}
    assert all("template" in value for value in templates.values())
    assert len(live_admission.all_units(ROOT)) == live_admission.MAX_START_CEILING == 53
    assert not any(unit.startswith("scenario-15") for unit in live_admission.all_units(ROOT))


@pytest.mark.parametrize("reader", ["custody-record", "ledger"])
def test_group_writable_record_refused_without_group_write_on_disk(tmp_path, monkeypatch, reader):
    custody = tmp_path / "custody"
    custody.mkdir(mode=0o700)
    schema = live_admission.CONSUMPTION_SCHEMA
    path = Path(_write_private(custody / "record.json", {"schema": schema})["path"])
    if reader == "custody-record":
        def read():
            return live_admission._custody_record(str(path), custody, "manager decision")[0]
        refusal = "manager decision must be a private operator-owned record"
    else:
        def read():
            return live_admission._read_ledger(path)
        refusal = "consumption ledger record is not a private regular file"
    assert read()["schema"] == schema
    report_group_writable(monkeypatch, path)
    with pytest.raises(live_admission.AdmissionError, match=refusal):
        read()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
