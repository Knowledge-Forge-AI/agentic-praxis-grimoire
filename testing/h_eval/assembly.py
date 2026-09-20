"""Immutable arm assembly and frozen APG166 aggregate formulas.

Assembly retains every scenario and both arm outcomes. It never drops a failed
or unavailable arm to improve a cohort. The existing evaluate.aggregate
function remains the sole owner of savings, quality, recovery, and contingency
formulas; this module only translates arm receipts into its frozen input shape.
"""
from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import execution
from .evaluate import BOUNDARY, SCHEMA, encoded, load
from .evaluate import aggregate as frozen_aggregate
from .preregistration import verify_bindings

ASSEMBLY_SCHEMA = "apg.h-assembly/v1"
AGGREGATE_SCHEMA = "apg.h-aggregate/v1"
MODES = ("static", "adaptive")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unavailable(reason: str) -> dict[str, Any]:
    return {"source": "unavailable", "value": None, "reason": reason}


def _observed(value: Any, *, source: str = "measured") -> dict[str, Any]:
    return {"source": source, "value": value}


def _load_result(value: Any) -> dict[str, Any]:
    if isinstance(value, (str, Path)):
        arm_dir = Path(value)
        result = execution.read_arm_result(arm_dir)
        result["_arm_dir"] = str(arm_dir)
        return result
    if isinstance(value, Mapping) and isinstance(value.get("arm_dir"), (str, Path)):
        arm_dir = Path(value["arm_dir"])
        result = execution.read_arm_result(arm_dir)
        result["_arm_dir"] = str(arm_dir)
        return result
    raise ValueError("arm result must be an integrity-checked retained directory")


def _receipt_facts(row: Mapping[str, Any], mode: str, result: Mapping[str, Any]) -> dict[str, Any]:
    """Read the execution-owned bundle and reject copied/self-described facts."""
    from .execution_evidence import validate_retained_bundle

    arm_dir = result.get("_arm_dir")
    if not isinstance(arm_dir, str):
        raise ValueError("complete arm must identify its retained directory")
    receipt = validate_retained_bundle(arm_dir, result, scenario=row, mode=mode)
    route = receipt["route"]
    frozen = row["routes"][mode]
    binding = frozen["role_binding"]
    if (
        route.get("provider") != frozen.get("provider")
        or route.get("profile") != frozen.get("profile")
        or route.get("model") != frozen.get("model")
        or route.get("binding_id") != binding.get("binding_id")
        or route.get("roles") != binding.get("roles")
        or route.get("source_sha256") != frozen.get("source_sha256")
    ):
        raise ValueError("arm route receipt is not the frozen route")
    if result.get("route") != route:
        raise ValueError("arm result route differs from retained route")
    eligibility = receipt.get("qualification_eligibility")
    if (not isinstance(eligibility, Mapping)
            or eligibility.get("schema") != "apg.h-qualification-eligibility/v1"
            or eligibility.get("status") != "eligible"):
        reasons = eligibility.get("reasons", []) if isinstance(eligibility, Mapping) else []
        raise ValueError(f"arm qualification eligibility rejected: {reasons}")
    if result.get("provider_import") != receipt["provider_import"]:
        raise ValueError("arm result importer differs from retained importer")
    if result.get("provider_terminal") != receipt["provider_terminal"]:
        raise ValueError("arm result terminal differs from retained terminal")
    if result.get("coverage") != receipt["transport"].get("coverage"):
        raise ValueError("arm result coverage differs from retained transport")
    activity = receipt["activity"]
    if result.get("provider_invocations") != activity.get("provider_invocations"):
        raise ValueError("arm result invocation count differs from activity receipt")
    if result.get("retries", 0) != activity.get("retries") or result.get("restarts", 0) != activity.get("restarts"):
        raise ValueError("arm result retry/restart facts differ from activity receipt")
    authority = receipt.get("authority")
    if not isinstance(authority, Mapping) or authority.get("permitted") is not activity.get("permitted"):
        raise ValueError("arm result authority differs from retained authority receipt")
    oracle_file = Path(arm_dir) / "task-oracle.json"
    if not oracle_file.is_file() or result.get("task_oracle") != load(oracle_file):
        raise ValueError("arm task oracle is not retained immutably")
    construction = result.get("construction")
    if not isinstance(construction, Mapping) or construction.get("schema") != execution.CONSTRUCTION_SCHEMA:
        raise ValueError("repository-owned arm construction is missing")
    if construction.get("source") != receipt["identity"].get("source_binding"):
        raise ValueError("source identity is not retained by the arm bundle")
    if construction.get("subject_factory") != receipt["identity"].get("subject_factory"):
        raise ValueError("subject factory identity is not retained by the arm bundle")
    if construction.get("task_contract") != receipt["identity"].get("task_contract"):
        raise ValueError("task contract identity is not retained by the arm bundle")
    if construction.get("oracle") != receipt["identity"].get("oracle_owner"):
        raise ValueError("oracle owner identity is not retained by the arm bundle")
    runtime = receipt["runtime"]
    revalidation = runtime.get("revalidation")
    if not isinstance(revalidation, Mapping) or revalidation.get("post_run") != "valid":
        raise ValueError("post-run runtime revalidation is absent")
    if result.get("runtime_revalidation") != revalidation:
        raise ValueError("arm runtime revalidation differs from retained runtime receipt")
    return receipt


def _arm_route(row: Mapping[str, Any], mode: str, result: Mapping[str, Any] | None) -> dict[str, Any]:
    route = dict(row["routes"][mode])
    route.pop("requested_mode", None)
    route["requested_context_mode"] = mode
    route["execution"] = (result or {}).get("route", {}).get("execution", "instrumented")
    imported = (result or {}).get("provider_import", {})
    observed_model = imported.get("observed_model") if isinstance(imported, Mapping) else None
    observed_session = imported.get("session") if isinstance(imported, Mapping) else None
    if route["execution"] == "live" and isinstance(observed_model, str) and observed_model:
        model_route = {
            "source": "measured",
            "value": {"provider": imported.get("provider"), "model": observed_model,
                      "session": observed_session},
        }
    else:
        model_route = {"source": "unavailable", "value": None,
                       "reason": "provider runtime identity was not observed"}
    route["model_route"] = model_route
    return route


def _empty_arm(row: Mapping[str, Any], mode: str, reason: str) -> dict[str, Any]:
    route = _arm_route(row, mode, None)
    return {
        "route": route,
        "initial": _unavailable(reason),
        "cumulative": _unavailable(reason),
        "deliveries": [],
        "coverage": _unavailable(reason),
        "task_outcome": _unavailable(reason),
        "quality_oracle": row["frozen_oracle"],
        "retries": _unavailable(reason),
        "producer_revisions": _unavailable(reason),
        "missing_guidance_findings": _unavailable(reason),
        "restart_required_incidents": _unavailable(reason),
        "authority": _unavailable(reason),
        "exact_recovery": _unavailable(reason),
        "late_acquisitions": _unavailable(reason),
        "provider_native_bytes": _unavailable(reason),
        "tokens": _unavailable(reason),
    }


def _receipt_arm(row: Mapping[str, Any], mode: str, result: Mapping[str, Any]) -> dict[str, Any]:
    reason = result.get("failure", "arm result incomplete")
    if result.get("status") != "complete":
        return _empty_arm(row, mode, reason)
    try:
        receipt = _receipt_facts(row, mode, result)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return _empty_arm(row, mode, f"retained arm evidence invalid: {error}")
    route = _arm_route(row, mode, result)
    deliveries = result.get("deliveries")
    initial = result.get("initial")
    cumulative = result.get("cumulative")
    coverage = result.get("coverage")
    if not isinstance(deliveries, list) or type(initial) is not int or type(cumulative) is not int or coverage != "complete":
        return _empty_arm(row, mode, "complete receipt lacks transmission evidence")
    imported = receipt["provider_import"]
    observed = imported.get("observed") if isinstance(imported, Mapping) else {}
    oracle = result.get("task_oracle")
    authority = result.get("authority")
    if (
        not isinstance(oracle, Mapping)
        or oracle.get("status") not in ("pass", "fail")
        or not isinstance(authority, Mapping)
        or authority.get("permitted") is not True
    ):
        return _empty_arm(row, mode, "complete receipt lacks oracle or authority evidence")
    admission = receipt.get("live_admission")
    if route.get("execution") == "live" and not isinstance(admission, Mapping):
        return _empty_arm(row, mode, "live arm lacks a verified admission receipt")
    exact_recovery = receipt.get("exact_recovery")
    arm = {
        "route": route,
        "initial": _observed(initial),
        "cumulative": _observed(cumulative),
        "deliveries": deliveries,
        "coverage": _observed(coverage),
        "task_outcome": _observed(oracle.get("status")),
        "quality_oracle": row["frozen_oracle"],
        "retries": _observed(result.get("retries", 0)),
        "producer_revisions": _observed(observed["producer_revisions"]) if isinstance(observed, Mapping) and observed.get("producer_revisions") is not None else _unavailable("provider did not emit producer revisions"),
        "missing_guidance_findings": _observed(observed["missing_guidance_findings"]) if isinstance(observed, Mapping) and observed.get("missing_guidance_findings") is not None else _unavailable("provider did not emit guidance findings"),
        "restart_required_incidents": _observed(observed["restart_required_incidents"]) if isinstance(observed, Mapping) and observed.get("restart_required_incidents") is not None else _unavailable("provider did not emit restart incidents"),
        "authority": _observed("preserved"),
        "exact_recovery": _observed(exact_recovery) if isinstance(exact_recovery, bool) else _unavailable("exact recovery was not observed"),
        "late_acquisitions": _observed(receipt.get("acquisitions", [])),
        "provider_native_bytes": _observed((result.get("provider_terminal") or {}).get("stdout", {}).get("bytes", 0)),
        "tokens": _unavailable("provider token counter unavailable"),
    }
    if "selective_discovery" in result:
        arm["selective_discovery"] = result["selective_discovery"]
    if isinstance(admission, Mapping):
        arm["live_admission"] = dict(admission)
    return arm


def _input_results(arm_results: Any) -> dict[tuple[str, str], Any]:
    if arm_results is None:
        return {}
    if isinstance(arm_results, Mapping):
        output: dict[tuple[str, str], Any] = {}
        for key, value in arm_results.items():
            if isinstance(key, tuple) and len(key) == 2:
                output[(str(key[0]), str(key[1]))] = value
            elif isinstance(value, Mapping) and set(value).intersection(MODES):
                for mode in MODES:
                    if mode in value:
                        output[(str(key), mode)] = value[mode]
            elif isinstance(value, Mapping) and value.get("scenario_id") and value.get("mode") in MODES:
                output[(str(value["scenario_id"]), str(value["mode"]))] = value
        return output
    output = {}
    for value in arm_results:
        result = _load_result(value)
        if result.get("scenario_id") and result.get("mode") in MODES:
            output[(str(result["scenario_id"]), str(result["mode"]))] = value
    return output


def assemble_raw(root: str | Path, arm_results: Any = None, *, scenario15: str = "contingent/unavailable") -> dict[str, Any]:
    """Assemble all fifteen rows, preserving explicit incomplete arms."""
    root = Path(root)
    bindings = verify_bindings(root)
    if scenario15 not in ("qualified", "contingent/unavailable"):
        raise ValueError("invalid Scenario 15 disposition")
    supplied = _input_results(arm_results)
    rows = []
    calibration = {f"scenario-{n:02}" for n in range(1, 6)}
    for row in bindings["scenarios"]:
        arms: dict[str, Any] = {}
        for mode in MODES:
            key = (row["scenario_id"], mode)
            arms[mode] = (
                _empty_arm(row, mode, "arm result unavailable")
                if key not in supplied
                else _receipt_arm(row, mode, _load_result(supplied[key]))
            )
        rows.append({
            "scenario_id": row["scenario_id"],
            "subset": "calibration" if row["scenario_id"] in calibration else "acceptance",
            "synthetic_inputs": bool(row["cohorts"].get("synthetic")),
            "synthetic_materialization": None,
            "arms": arms,
            "mechanism": {
                "source": "APG166E-one-arm-assembly",
                "complete": all(arms[mode]["coverage"].get("source") == "measured" for mode in MODES),
            },
        })
    return {
        "schema_version": SCHEMA,
        "seal_sha256": _sha((root / "testing/h_eval/scenario-bindings.json").read_bytes()),
        "boundary": BOUNDARY,
        "scenario15": scenario15,
        "rows": rows,
    }


def _measured_live(arm: Mapping[str, Any]) -> bool:
    return (arm.get("coverage", {}).get("source") == "measured"
            and arm.get("task_outcome", {}).get("source") == "measured"
            and arm.get("authority", {}).get("source") == "measured"
            and arm.get("route", {}).get("execution") == "live"
            and arm.get("route", {}).get("model_route", {}).get("source") == "measured"
            and isinstance(arm.get("live_admission"), Mapping))


def _incomplete_arms(raw: Mapping[str, Any]) -> list[str]:
    """Name every arm that prevents aggregation under the Scenario 15 disposition.

    A contingent Scenario 15 must remain explicitly unavailable; it is never
    measured, dropped or replaced.  A qualified disposition still requires all
    fifteen rows to be measured live.
    """
    rows = raw.get("rows")
    expected = {f"scenario-{n:02d}" for n in range(1, 16)}
    if (not isinstance(rows, list) or len(rows) != 15
            or {row.get("scenario_id") for row in rows} != expected
            or any(set(row.get("arms", {})) != set(MODES) for row in rows)):
        return ["complete fifteen-row assembly"]
    contingent = raw.get("scenario15") == "contingent/unavailable"
    missing = []
    for row in rows:
        for mode in MODES:
            arm = row["arms"][mode]
            name = f"{row['scenario_id']}/{mode}"
            if row["scenario_id"] == "scenario-15" and contingent:
                if arm.get("coverage", {}).get("source") != "unavailable":
                    missing.append(f"{name} (measured while contingent)")
            elif not _measured_live(arm):
                missing.append(name)
    return missing


def _all_arms_complete(raw: Mapping[str, Any]) -> bool:
    return not _incomplete_arms(raw)


def _admission_block(root: str | Path, raw: Mapping[str, Any], live_authorization: Any) -> dict[str, Any]:
    from . import live_admission
    if live_authorization is None:
        raise ValueError("live aggregate admission unavailable: external manager decision and grant required")
    receipts = {}
    for row in raw["rows"]:
        for mode in MODES:
            admission = row["arms"][mode].get("live_admission")
            if isinstance(admission, Mapping):
                receipts[live_admission.scenario_unit(row["scenario_id"], mode)] = admission
    accounting = live_admission.accounting(root, live_authorization, arm_receipts=receipts)
    scenario_units = [unit for unit in live_admission.all_units(root) if unit.startswith("scenario-")]
    granted = {row["unit_id"]: row for row in accounting["units"]}
    incomplete = [unit for unit in scenario_units
                  if granted.get(unit, {}).get("status") != "retained"]
    if incomplete:
        raise ValueError(f"grant accounting is incomplete for aggregation: {incomplete}")
    if set(receipts) != set(scenario_units):
        raise ValueError("measured arms are not exactly the granted scenario units")
    return {
        "decision_sha256": accounting["decision_sha256"],
        "grant_sha256": sorted({granted[unit]["grant_sha256"] for unit in scenario_units}),
        "accounting_sha256": _sha(encoded(accounting)),
        "scenario_units": len(scenario_units),
    }


def aggregate_complete(root: str | Path, raw: Mapping[str, Any], *,
                       live_authorization: Any = None) -> dict[str, Any]:
    """Apply frozen formulas only to granted, retained and readable arm receipts."""
    missing = _incomplete_arms(raw)
    if missing:
        raise ValueError(f"cannot aggregate incomplete arm results: {missing}")
    admission = _admission_block(root, raw, live_authorization)
    metrics = load(Path(root) / "testing/fixtures/context-eval/context-eval-metrics-and-oracles.json")
    value = frozen_aggregate(dict(raw), metrics)
    value["h_gate_established"] = False
    value["qualified_promotions"] = 0
    value["scenario15"] = raw["scenario15"]
    value["admission"] = admission
    return value


def write_aggregate(path: str | Path, value: Mapping[str, Any], *,
                    root: str | Path | None = None, live_authorization: Any = None,
                    raw: Mapping[str, Any] | None = None) -> None:
    """Publish only an aggregate whose admission block re-verifies now."""
    if root is None or live_authorization is None or raw is None:
        raise ValueError("aggregate publication unavailable without re-verified grant admission")
    if value.get("h_gate_established") is not False or value.get("qualified_promotions") != 0:
        raise ValueError("aggregate cannot establish H gate or promotions")
    if value.get("admission") != _admission_block(root, raw, live_authorization):
        raise ValueError("aggregate admission block differs from current grant accounting")
    if value.get("raw_sha256") != _sha(encoded(dict(raw))):
        raise ValueError("aggregate does not bind the supplied raw assembly")
    path = Path(path)
    if path.parent.resolve() != path.parent or path.exists() or path.is_symlink():
        raise ValueError("aggregate destination must be a new physical path")
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        child = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(child, "wb") as stream:
            stream.write(encoded(dict(value)))
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(fd)
    finally:
        os.close(fd)


def read_aggregate(path: str | Path) -> dict[str, Any]:
    value = load(Path(path))
    if value.get("schema_version") != AGGREGATE_SCHEMA:
        raise ValueError("unsupported aggregate receipt")
    if value.get("h_gate_established") is not False:
        raise ValueError("aggregate cannot establish H gate")
    return value


__all__ = [
    "AGGREGATE_SCHEMA",
    "ASSEMBLY_SCHEMA",
    "aggregate_complete",
    "assemble_raw",
    "read_aggregate",
    "write_aggregate",
]
