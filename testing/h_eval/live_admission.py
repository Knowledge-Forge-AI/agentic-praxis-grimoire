"""External manager decision and grant admission for live H units.

This module is the only owner that can admit a live H scenario arm or a
promotion case.  Authority comes from two external records under an operator
custody root: a manager decision that binds the accepted source, route,
runtime, preregistration, readiness, package, host-mechanical and D1 evidence,
and a grant that names at most one start for each derived unit.  Source-owned
flags, booleans and feature constants never grant execution.

Consumption is unit-scoped across every grant under one custody root.  A unit
is consumed by an exclusive ledger record before any context, subject or
provider work begins, so a failed start can never be replayed under a fresh
grant or an alternate identity.

A single explicitly authorized replacement of a proven pre-provider failure
is the only exception.  A ``apg.h-live-grant/v2`` names a separate manager
replacement authorization that binds the exact predecessor decision, grant,
canonical ledger and integrity-checked failed result.  The original ledger and
result are never touched; the replacement is consumed by an additional record
under ``h-replacement-consumed`` in the same custody root, keyed by unit, so a
unit can be replaced at most once and a replacement is never replaced.

The checks are proportionate local record and ownership checks under the
accepted operator context.  They are not signatures: a process running as the
same operator can author both records.  That limitation is recorded, not
hidden.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DECISION_SCHEMA = "apg.h-manager-decision/v1"
GRANT_SCHEMA = "apg.h-live-grant/v1"
GRANT_SCHEMA_V2 = "apg.h-live-grant/v2"
CONSUMPTION_SCHEMA = "apg.h-live-consumption/v1"
RECEIPT_SCHEMA = "apg.h-live-admission/v1"
REPLACEMENT_SCHEMA = "apg.h-live-replacement-authorization/v1"
REPLACEMENT_CONSUMPTION_SCHEMA = "apg.h-live-replacement-consumption/v1"
REPLACEMENT_RECEIPT_SCHEMA = "apg.h-live-admission/v2"
ACCOUNTING_SCHEMA = "apg.h-live-accounting/v2"
UNAVAILABLE = "live arm admission unavailable: external manager decision and grant required"
DISPOSITION = "authorize-live-grant"
COHORT_DECISION = "eligible-subset-01-14-and-25-cases"
SCENARIO15 = "contingent/unavailable"
CALIBRATION = tuple(f"scenario-{n:02d}" for n in range(1, 6))
ACCEPTANCE = tuple(f"scenario-{n:02d}" for n in range(6, 15))
MODES = ("static", "adaptive")
MAX_START_CEILING = 53
LEDGER = "h-consumed"
REPLACEMENT_LEDGER = "h-replacement-consumed"
REPLACEMENT_ATTEMPT = "replacement-1"
NO_START = "pre-provider-no-start"
# Arm steps entered strictly before ``provider_stdin``; ``provider_stdin`` is
# conservatively excluded because the invocation counter follows it.
PRE_PROVIDER_STEPS = frozenset({
    "runtime_transaction", "source_context", "provider_argv", "context_prepare",
    "observation_begin", "native_read_prepare",
})
_PROVIDER_FILES = ("run/provider.stdin", "run/provider.stdout", "run/provider.stderr")
_PROVIDER_RESULT_FIELDS = ("prepared", "provider_terminal", "provider_import", "task_oracle")
_UNIT = re.compile(r"^(scenario-(0[1-9]|1[0-4])/(static|adaptive)|promotion/[a-z0-9-]+/(positive|non-trigger)/[a-z0-9-]+)$")
_HOST_RESULT_CHECKS = {
    "scenario_records": 15, "equal_initial_trees": 15, "unchanged_subject_pairs": 15,
    "promotion_fixture_pairs": 25, "provider_invocations": 0, "sentinels": 0,
    "package_seal_valid": True, "readback_valid": True,
}
_EVIDENCE = ("readiness_seal", "package_seal", "host_mechanical_result", "d1_decision",
             "installed_home_comparison")
_DECISION_FIELDS = {
    "schema", "decision_id", "disposition", "cohort_decision", "scenario15", "issued_at",
    "custody_root", "source", "routes", "runtime", "evidence", "native_read_qualification",
    "decision_sha256",
}
_GRANT_FIELDS = {
    "schema", "grant_id", "decision_sha256", "custody_root", "units", "start_ceiling",
    "max_starts_per_unit", "replay_prohibited", "retries", "valid_until",
    "evaluation_seal", "evaluation_binary", "grant_sha256",
}
_GRANT_V2_FIELDS = _GRANT_FIELDS | {"replacements", "calibration_attempts"}
_REPLACEMENT_FIELDS = {
    "schema", "replacement_id", "unit_id", "custody_root", "predecessor", "disposition",
    "successor", "max_replacements", "retries", "replay_prohibited", "issued_at",
    "valid_until", "authorization_sha256",
}
_PREDECESSOR_FIELDS = {
    "decision_id", "decision_sha256", "decision_record", "grant_id", "grant_sha256",
    "grant_record", "ledger", "source_identity", "arm_dir", "result_sha256", "integrity_sha256",
}
_DISPOSITION_FIELDS = {"kind", "provider_invocations", "failure", "failure_step", "manager_evidence"}
_SUCCESSOR_FIELDS = {"decision_sha256", "source_identity", "runtime_manifest_sha256"}


class AdmissionError(ValueError):
    """A live unit is not admitted; no provider may start."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hex(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def self_digest(record: Mapping[str, Any], field: str) -> str:
    """Digest a record without its own digest field."""
    return _sha256(_canonical({k: v for k, v in record.items() if k != field}))


def scenario_unit(scenario_id: str, mode: str) -> str:
    unit = f"{scenario_id}/{mode}"
    if not _UNIT.match(unit) or not unit.startswith("scenario-"):
        raise AdmissionError(f"unknown live scenario unit: {unit}")
    return unit


def promotion_unit(case_id: str) -> str:
    unit = f"promotion/{case_id}"
    if not _UNIT.match(unit):
        raise AdmissionError(f"unknown promotion unit: {unit}")
    return unit


def _encoded_unit(unit: str) -> str:
    if not _UNIT.match(unit):
        raise AdmissionError(f"unknown live unit: {unit}")
    return unit.replace("/", "--") + ".json"


def _promotion_cases(root: Path) -> list[dict[str, Any]]:
    from .preregistration import verify_promotions
    return [case for skill in verify_promotions(root)["skills"] for case in skill["cases"]]


def all_units(root: str | Path) -> list[str]:
    """Return every derivable unit in execution order; Scenario 15 is absent."""
    root = Path(root)
    units = [scenario_unit(sid, mode) for sid in (*CALIBRATION, *ACCEPTANCE) for mode in MODES]
    units.extend(promotion_unit(case["case_id"]) for case in _promotion_cases(root))
    if len(units) != MAX_START_CEILING or len(set(units)) != len(units):
        raise AdmissionError("derived live unit inventory is not the prospective 28+25 set")
    return units


def unit_route_sha256(root: str | Path, unit: str) -> str:
    """Digest the frozen route that a unit must execute."""
    root = Path(root)
    if unit.startswith("scenario-"):
        from .execution import _frozen_inputs, _encoded
        scenario_id, mode = unit.split("/")
        _scenario, _row, route, _source = _frozen_inputs(root, scenario_id, mode)
        route = {k: v for k, v in route.items() if k not in ("scenario_id", "source_identity")}
        return _sha256(_encoded(route))
    case_id = unit.split("/", 1)[1]
    case = next((item for item in _promotion_cases(root) if item["case_id"] == case_id), None)
    if case is None:
        raise AdmissionError(f"promotion case is not preregistered: {case_id}")
    return _sha256(_canonical({"case_id": case_id, "case_sha256": case["case_sha256"],
                               "route": case["route"]}))


def route_map(root: str | Path) -> dict[str, str]:
    return {unit: unit_route_sha256(root, unit) for unit in all_units(root)}


def source_facts(root: str | Path) -> dict[str, str]:
    """Recompute the source identities a decision must bind."""
    from .preregistration import verify_bindings, verify_promotions
    from .readiness import make_seal, source_identity, verify_d1_carry_forward
    root = Path(root)
    verify_bindings(root)
    verify_promotions(root)
    verify_d1_carry_forward(root)

    def file_digest(relative: str) -> str:
        return _sha256((root / relative).read_bytes())

    return {
        "source_identity": source_identity(make_seal(root)["files"]),
        "scenario_bindings_sha256": file_digest("testing/h_eval/scenario-bindings.json"),
        "promotion_preregistration_sha256": file_digest("testing/h_eval/promotion-preregistration.json"),
        "subject_manifest_sha256": file_digest("testing/fixtures/context-eval/subjects/manifest.json"),
        "d1_carry_forward_sha256": file_digest("testing/h_eval/d1-carry-forward.json"),
    }


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AdmissionError(f"{field} must be an explicit UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise AdmissionError(f"{field} is not a timestamp") from error
    return parsed


def _outside(path: Path, source_root: Path) -> bool:
    return not (path == source_root or path.is_relative_to(source_root) or source_root.is_relative_to(path))


def _custody_root(value: Any, source_root: Path) -> Path:
    if not isinstance(value, str) or not value.startswith("/"):
        raise AdmissionError("custody root must be an absolute path")
    path = Path(value)
    try:
        info = path.lstat()
    except OSError as error:
        raise AdmissionError("custody root is unavailable") from error
    if (path.resolve() != path or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o022):
        raise AdmissionError("custody root must be a private operator-owned directory")
    if not _outside(path, source_root):
        raise AdmissionError("custody root must be outside the source tree")
    return path


def _custody_record(value: Any, custody: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if not isinstance(value, str) or not value.startswith("/"):
        raise AdmissionError(f"{label} path must be absolute")
    path = Path(value)
    try:
        info = path.lstat()
    except OSError as error:
        raise AdmissionError(f"{label} is unavailable") from error
    if (path.resolve() != path or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o022 or not path.is_relative_to(custody)):
        raise AdmissionError(f"{label} must be a private operator-owned record under custody")
    data = path.read_bytes()
    try:
        from .evaluate import load
        record = load(path)
    except ValueError as error:
        raise AdmissionError(f"{label} is not strict JSON") from error
    if not isinstance(record, dict):
        raise AdmissionError(f"{label} must be an object")
    return record, data


def _evidence_file(reference: Any, label: str, source_root: Path) -> tuple[Path, bytes]:
    if not isinstance(reference, Mapping) or set(reference) != {"path", "sha256"}:
        raise AdmissionError(f"{label} evidence reference is incomplete")
    path = Path(str(reference["path"]))
    if not path.is_absolute() or path.resolve() != path or path.is_symlink() or not path.is_file():
        raise AdmissionError(f"{label} evidence is unavailable")
    if not _outside(path, source_root):
        raise AdmissionError(f"{label} evidence must be outside the source tree")
    data = path.read_bytes()
    if not _hex(reference["sha256"]) or _sha256(data) != reference["sha256"]:
        raise AdmissionError(f"{label} evidence digest mismatch")
    return path, data


def _authorization_paths(authorization: Any) -> tuple[str, str]:
    """Accept only external record paths; flags and booleans never authorize."""
    if (not isinstance(authorization, Mapping)
            or set(authorization) != {"decision_path", "grant_path"}
            or not all(isinstance(authorization[k], str) and authorization[k] for k in authorization)):
        raise AdmissionError(UNAVAILABLE)
    return authorization["decision_path"], authorization["grant_path"]


def check_shape(authorization: Any) -> None:
    """Cheap pre-check used before any other live construction work."""
    _authorization_paths(authorization)


def _validate_decision(decision: Mapping[str, Any], source_root: Path) -> None:
    if decision.get("template") is not None or set(decision) != _DECISION_FIELDS:
        raise AdmissionError("manager decision fields are not the accepted schema")
    if (decision["schema"] != DECISION_SCHEMA or decision["disposition"] != DISPOSITION
            or decision["cohort_decision"] != COHORT_DECISION or decision["scenario15"] != SCENARIO15
            or not isinstance(decision["decision_id"], str) or not decision["decision_id"]):
        raise AdmissionError("manager decision does not authorize the eligible live subset")
    if not _hex(decision["decision_sha256"]) or self_digest(decision, "decision_sha256") != decision["decision_sha256"]:
        raise AdmissionError("manager decision digest mismatch")
    if _timestamp(decision["issued_at"], "decision issued_at") > datetime.now(timezone.utc):
        raise AdmissionError("manager decision is not yet issued")
    runtime = decision["runtime"]
    if (not isinstance(runtime, Mapping)
            or set(runtime) != {"live_runtime_manifest_sha256", "transaction_directory"}
            or not _hex(runtime["live_runtime_manifest_sha256"])
            or not isinstance(runtime["transaction_directory"], str)
            or not runtime["transaction_directory"].startswith("/")):
        raise AdmissionError("manager decision runtime binding is incomplete")
    evidence = decision["evidence"]
    if not isinstance(evidence, Mapping) or set(evidence) != {*_EVIDENCE, "skill_approvals"}:
        raise AdmissionError("manager decision evidence inventory is incomplete")
    from .evaluate import PRIMARY
    approvals = evidence["skill_approvals"]
    if not isinstance(approvals, Mapping) or set(approvals) != set(PRIMARY):
        raise AdmissionError("manager decision must bind all five skill approvals")
    qualification = decision["native_read_qualification"]
    if qualification is not None:
        from .readiness import _qualification
        _qualification(qualification)


def _reference(value: Any) -> bool:
    return (isinstance(value, Mapping) and set(value) == {"path", "sha256"}
            and isinstance(value["path"], str) and value["path"].startswith("/") and _hex(value["sha256"]))


def _calibration_units() -> list[str]:
    return [scenario_unit(sid, mode) for sid in CALIBRATION for mode in MODES]


def _validate_grant_v2(grant: Mapping[str, Any], units: Sequence[str], acceptance: bool) -> None:
    """Additive v2 fields: explicit replacements and selected calibration attempts."""
    replacements = grant["replacements"]
    if not isinstance(replacements, Mapping):
        raise AdmissionError("live grant replacements are malformed")
    for unit, reference in replacements.items():
        if unit not in units or not unit.startswith("scenario-") or not _reference(reference):
            raise AdmissionError("live grant replacement must name a granted scenario unit and one record")
    attempts = grant["calibration_attempts"]
    if not acceptance:
        if attempts is not None:
            raise AdmissionError("calibration attempts are bound only by an acceptance grant")
        return
    if not isinstance(attempts, Mapping) or set(attempts) != set(_calibration_units()):
        raise AdmissionError("acceptance grant must select one attempt for every calibration unit")
    for attempt in attempts.values():
        if (not isinstance(attempt, Mapping) or set(attempt) != {"arm_dir", "result_sha256"}
                or not isinstance(attempt["arm_dir"], str) or not attempt["arm_dir"].startswith("/")
                or not _hex(attempt["result_sha256"])):
            raise AdmissionError("selected calibration attempt reference is incomplete")


def _validate_grant(grant: Mapping[str, Any], decision: Mapping[str, Any], known: Sequence[str]) -> None:
    fields = _GRANT_V2_FIELDS if grant.get("schema") == GRANT_SCHEMA_V2 else _GRANT_FIELDS
    if grant.get("template") is not None or set(grant) != fields:
        raise AdmissionError("live grant fields are not the accepted schema")
    if (grant["schema"] not in (GRANT_SCHEMA, GRANT_SCHEMA_V2)
            or not isinstance(grant["grant_id"], str) or not grant["grant_id"]):
        raise AdmissionError("live grant schema is invalid")
    if not _hex(grant["grant_sha256"]) or self_digest(grant, "grant_sha256") != grant["grant_sha256"]:
        raise AdmissionError("live grant digest mismatch")
    if grant["decision_sha256"] != decision["decision_sha256"]:
        raise AdmissionError("live grant does not bind this manager decision")
    if grant["custody_root"] != decision["custody_root"]:
        raise AdmissionError("live grant custody root differs from the decision")
    units = grant["units"]
    if (not isinstance(units, list) or not units or len(units) != len(set(units))
            or any(unit not in known for unit in units)):
        raise AdmissionError("live grant units are unknown, duplicated or include Scenario 15")
    if (type(grant["start_ceiling"]) is not int or grant["start_ceiling"] != len(units)
            or grant["start_ceiling"] > MAX_START_CEILING):
        raise AdmissionError("live grant start ceiling must equal its units and stay within 53")
    if grant["max_starts_per_unit"] != 1 or grant["replay_prohibited"] is not True or grant["retries"] != 0:
        raise AdmissionError("live grant must allow one start per unit, no replay and no retry")
    if datetime.now(timezone.utc) >= _timestamp(grant["valid_until"], "grant valid_until"):
        raise AdmissionError("live grant is stale")
    acceptance = any(unit.split("/")[0] in ACCEPTANCE for unit in units)
    for field in ("evaluation_seal", "evaluation_binary"):
        if acceptance and grant[field] is None:
            raise AdmissionError("acceptance units require a separately sealed evaluation")
        if grant[field] is not None and (not isinstance(grant[field], Mapping)
                                         or set(grant[field]) != {"path", "sha256"}):
            raise AdmissionError(f"live grant {field} reference is incomplete")
    if grant["schema"] == GRANT_SCHEMA_V2:
        _validate_grant_v2(grant, units, acceptance)


def _ledger_path(custody: Path, unit: str) -> Path:
    return custody / LEDGER / _encoded_unit(unit)


def _replacement_ledger_path(custody: Path, unit: str) -> Path:
    return custody / REPLACEMENT_LEDGER / _encoded_unit(unit)


def _present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _read_ledger(path: Path, schema: str = CONSUMPTION_SCHEMA) -> dict[str, Any]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise AdmissionError("consumption ledger record is not a private regular file")
    from .evaluate import load
    record = load(path)
    if not isinstance(record, dict) or record.get("schema") != schema:
        raise AdmissionError("consumption ledger record is invalid")
    return record


def _verify_mechanical(decision: Mapping[str, Any], source_root: Path, facts: Mapping[str, str]) -> dict[str, Any]:
    """Recompute accepted preparation evidence and compare it with custody bytes."""
    from . import readiness
    evidence = decision["evidence"]
    transaction = decision["runtime"]["transaction_directory"]
    _path, readiness_bytes = _evidence_file(evidence["readiness_seal"], "readiness seal", source_root)
    _path, package_bytes = _evidence_file(evidence["package_seal"], "package seal", source_root)
    _path, host_bytes = _evidence_file(evidence["host_mechanical_result"], "host mechanical result", source_root)
    for label in ("d1_decision", "installed_home_comparison"):
        _evidence_file(evidence[label], label.replace("_", " "), source_root)
    for skill_id, reference in evidence["skill_approvals"].items():
        _evidence_file(reference, f"{skill_id} approval", source_root)
    try:
        retained_readiness = json.loads(readiness_bytes)
        retained_package = json.loads(package_bytes)
        host = json.loads(host_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AdmissionError("mechanical evidence is not JSON") from error
    current = readiness.make_ready1_seal(source_root, {"transaction_directory": transaction})
    if retained_readiness != current:
        raise AdmissionError("readiness seal evidence differs from recomputed current state")
    package = current.get("mechanical_package")
    if not isinstance(package, Mapping) or retained_package != package:
        raise AdmissionError("package seal evidence differs from recomputed current state")
    if package.get("provider_free_mechanical_candidate") is not True:
        raise AdmissionError("provider-free mechanical package is not a passing candidate")
    if current.get("source_identity") != facts["source_identity"] or package.get("source_identity") != facts["source_identity"]:
        raise AdmissionError("mechanical evidence source identity is stale")
    checks = host.get("checks") if isinstance(host, Mapping) else None
    if (not isinstance(host, Mapping) or host.get("schema") != "apg166v-h-mechanical-host/v1"
            or host.get("status") != "passed" or host.get("live_provider_starts") != 0
            or host.get("source_unchanged") is not True
            or not isinstance(checks, Mapping)
            or any(checks.get(key) != value for key, value in _HOST_RESULT_CHECKS.items())
            or host.get("transaction_directory") != transaction
            or (host.get("source") or {}).get("source_identity") != facts["source_identity"]):
        raise AdmissionError("host mechanical result is not a passing current provider-free transaction")
    return current


def load_authorization(root: str | Path, authorization: Any) -> dict[str, Any]:
    """Load and structurally verify the decision and grant; performs no consumption."""
    source_root = Path(root)
    decision_path, grant_path = _authorization_paths(authorization)
    probe = Path(decision_path)
    try:
        preliminary = json.loads(probe.read_bytes()) if probe.is_file() and not probe.is_symlink() else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        preliminary = None
    if not isinstance(preliminary, Mapping):
        raise AdmissionError("manager decision is unavailable")
    custody = _custody_root(preliminary.get("custody_root"), source_root)
    decision, _ = _custody_record(decision_path, custody, "manager decision")
    grant, _ = _custody_record(grant_path, custody, "live grant")
    _validate_decision(decision, source_root)
    known = all_units(source_root)
    _validate_grant(grant, decision, known)
    return {"decision": decision, "grant": grant, "custody_root": custody, "known_units": known}


def _replacements(grant: Mapping[str, Any]) -> Mapping[str, Any]:
    return (grant.get("replacements") or {}) if grant.get("schema") == GRANT_SCHEMA_V2 else {}


def _replacement_record(custody: Path, grant: Mapping[str, Any], unit: str) -> tuple[dict[str, Any], str]:
    """Load the grant-bound replacement authorization bytes for one unit."""
    reference = _replacements(grant)[unit]
    record, data = _custody_record(reference["path"], custody, "replacement authorization")
    if _sha256(data) != reference["sha256"]:
        raise AdmissionError("replacement authorization digest differs from the grant")
    return record, reference["sha256"]


def _require_unconsumed(custody: Path, grant: Mapping[str, Any], unit: str) -> None:
    replacements = _replacements(grant)
    for listed in grant["units"]:
        path = _ledger_path(custody, listed)
        if path.exists() or path.is_symlink():
            record = _read_ledger(path)
            if record.get("grant_sha256") != grant["grant_sha256"]:
                if listed not in replacements:
                    raise AdmissionError("live grant lists a unit already consumed under another grant")
                # Only the exact historical ledger the replacement binds may
                # already exist for a declared replacement unit.
                authorization, _digest = _replacement_record(custody, grant, listed)
                predecessor = authorization.get("predecessor")
                ledger = predecessor.get("ledger") if isinstance(predecessor, Mapping) else None
                if not isinstance(ledger, Mapping) or _sha256(path.read_bytes()) != ledger.get("sha256"):
                    raise AdmissionError("live grant lists a unit already consumed under another grant")
        replaced = _replacement_ledger_path(custody, listed)
        if _present(replaced):
            record = _read_ledger(replaced, REPLACEMENT_CONSUMPTION_SCHEMA)
            if record.get("grant_sha256") != grant["grant_sha256"]:
                raise AdmissionError("live grant lists a unit already consumed under another grant")
    target = _ledger_path(custody, unit)
    if unit in replacements:
        if not _present(target):
            raise AdmissionError("replacement predecessor ledger is absent")
        if _present(_replacement_ledger_path(custody, unit)):
            raise AdmissionError("live unit replacement already used; replay refused")
        return
    if target.exists() or target.is_symlink():
        raise AdmissionError("live unit already consumed; replay refused")


def _custody_bound_record(reference: Any, custody: Path, label: str,
                          digest_field: str, expected_digest: Any) -> dict[str, Any]:
    """Read a bound historical custody record and check its bytes and self-digest."""
    if not _reference(reference):
        raise AdmissionError(f"{label} reference is incomplete")
    record, data = _custody_record(reference["path"], custody, label)
    if _sha256(data) != reference["sha256"]:
        raise AdmissionError(f"{label} bytes differ from the replacement binding")
    if (record.get(digest_field) != expected_digest or not _hex(record.get(digest_field))
            or self_digest(record, digest_field) != record[digest_field]):
        raise AdmissionError(f"{label} identity differs from the replacement binding")
    return record


def _verify_no_start(arm_dir: Path, unit: str, predecessor: Mapping[str, Any],
                     disposition: Mapping[str, Any], ledger_path: Path, source_root: Path) -> None:
    """Establish a proven pre-provider failure from integrity-checked evidence only.

    Integrity is verified without re-running git or re-verifying the retained
    runtime manifest against today's host.  A missing, non-integer or positive
    invocation counter, any provider artifact, a terminal or completed result
    and any replacement predecessor all refuse.
    """
    from . import execution
    if not arm_dir.is_absolute() or arm_dir.resolve() != arm_dir or not _outside(arm_dir, source_root):
        raise AdmissionError("predecessor arm must be a physical directory outside the source tree")
    try:
        result, integrity = execution._verified_arm_record(arm_dir)
        result_bytes = (arm_dir / "result.json").read_bytes()
        integrity_bytes = (arm_dir / "integrity.json").read_bytes()
        admission_record = json.loads((arm_dir / "admission.json").read_bytes())
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise AdmissionError("predecessor arm evidence is missing or tampered") from error
    if (_sha256(result_bytes) != predecessor["result_sha256"]
            or _sha256(integrity_bytes) != predecessor["integrity_sha256"]):
        raise AdmissionError("predecessor arm evidence differs from the replacement binding")
    scenario_id, mode = unit.split("/")
    if (not isinstance(result, Mapping) or result.get("scenario_id") != scenario_id
            or result.get("mode") != mode or result.get("status") != "incomplete"):
        raise AdmissionError("predecessor is not an incomplete attempt of this unit")
    files = integrity.get("files")
    invocations = result.get("provider_invocations")
    if type(invocations) is not int or invocations != 0:
        raise AdmissionError("predecessor provider start is positive or unknown")
    if any(field in result for field in _PROVIDER_RESULT_FIELDS):
        raise AdmissionError("predecessor reached provider preparation or completion")
    if not isinstance(files, Mapping) or any(name in files for name in _PROVIDER_FILES):
        raise AdmissionError("predecessor retained provider transport artifacts")
    receipt = result.get("live_admission")
    if (not isinstance(receipt, Mapping) or receipt.get("schema") != RECEIPT_SCHEMA
            or receipt.get("unit_id") != unit or receipt.get("ledger_path") != str(ledger_path)
            or receipt.get("ledger_sha256") != predecessor["ledger"]["sha256"]
            or receipt.get("decision_sha256") != predecessor["decision_sha256"]
            or receipt.get("grant_sha256") != predecessor["grant_sha256"]
            or not isinstance(admission_record, Mapping)
            or admission_record.get("live_admission") != receipt):
        raise AdmissionError("predecessor admission receipt differs from its canonical ledger")
    if result.get("failure") != disposition["failure"] or not isinstance(disposition["failure"], str):
        raise AdmissionError("predecessor failure differs from the replacement disposition")
    detail = result.get("failure_detail")
    if detail is not None:
        step = detail.get("step") if isinstance(detail, Mapping) else None
        if (step not in PRE_PROVIDER_STEPS or step != disposition["failure_step"]
                or disposition["manager_evidence"] is not None):
            raise AdmissionError("predecessor failure step is not a proven pre-provider step")
    else:
        # Legacy result without failure_detail: bind the manager's exact
        # evidence instead of inventing a historical step.
        if disposition["failure_step"] is not None or disposition["manager_evidence"] is None:
            raise AdmissionError("legacy predecessor requires exact manager evidence and no invented step")
        _evidence_file(disposition["manager_evidence"], "replacement manager", source_root)


def _verify_replacement(source_root: Path, custody: Path, decision: Mapping[str, Any],
                        grant: Mapping[str, Any], unit: str, facts: Mapping[str, str],
                        runtime_digest: str) -> dict[str, Any]:
    """Admit one explicitly authorized replacement of a proven no-start failure."""
    record, authorization_digest = _replacement_record(custody, grant, unit)
    if record.get("template") is not None or set(record) != _REPLACEMENT_FIELDS:
        raise AdmissionError("replacement authorization fields are not the accepted schema")
    if (record["schema"] != REPLACEMENT_SCHEMA or not isinstance(record["replacement_id"], str)
            or not record["replacement_id"] or record["unit_id"] != unit
            or record["custody_root"] != str(custody)):
        raise AdmissionError("replacement authorization does not name this unit and custody")
    if (not _hex(record["authorization_sha256"])
            or self_digest(record, "authorization_sha256") != record["authorization_sha256"]):
        raise AdmissionError("replacement authorization digest mismatch")
    if (record["max_replacements"] != 1 or record["retries"] != 0
            or record["replay_prohibited"] is not True):
        raise AdmissionError("replacement authorization must allow exactly one start and no retry")
    now = datetime.now(timezone.utc)
    if _timestamp(record["issued_at"], "replacement issued_at") > now:
        raise AdmissionError("replacement authorization is not yet issued")
    if now >= _timestamp(record["valid_until"], "replacement valid_until"):
        raise AdmissionError("replacement authorization is stale")
    successor, predecessor, disposition = record["successor"], record["predecessor"], record["disposition"]
    if (not isinstance(successor, Mapping) or set(successor) != _SUCCESSOR_FIELDS
            or not isinstance(predecessor, Mapping) or set(predecessor) != _PREDECESSOR_FIELDS
            or not isinstance(disposition, Mapping) or set(disposition) != _DISPOSITION_FIELDS):
        raise AdmissionError("replacement authorization lineage is incomplete")
    if dict(successor) != {"decision_sha256": decision["decision_sha256"],
                           "source_identity": facts["source_identity"],
                           "runtime_manifest_sha256": runtime_digest}:
        raise AdmissionError("replacement successor differs from the current decision, source or runtime")
    if predecessor["decision_sha256"] == decision["decision_sha256"]:
        raise AdmissionError("replacement predecessor must be under an earlier decision")
    if (disposition["kind"] != NO_START or type(disposition["provider_invocations"]) is not int
            or disposition["provider_invocations"] != 0):
        raise AdmissionError("replacement disposition is not a pre-provider no-start")
    old_decision = _custody_bound_record(predecessor["decision_record"], custody, "predecessor decision",
                                         "decision_sha256", predecessor["decision_sha256"])
    old_grant = _custody_bound_record(predecessor["grant_record"], custody, "predecessor grant",
                                      "grant_sha256", predecessor["grant_sha256"])
    if (old_decision.get("decision_id") != predecessor["decision_id"]
            or old_grant.get("grant_id") != predecessor["grant_id"]
            or old_grant.get("decision_sha256") != predecessor["decision_sha256"]
            or old_grant.get("custody_root") != str(custody)
            or unit not in (old_grant.get("units") or [])
            or unit in _replacements(old_grant)):
        raise AdmissionError("predecessor grant does not bind this unit under the predecessor decision")
    ledger_path = _ledger_path(custody, unit)
    ledger = predecessor["ledger"]
    if not _reference(ledger) or ledger["path"] != str(ledger_path):
        raise AdmissionError("replacement must bind the canonical predecessor ledger")
    try:
        ledger_bytes = ledger_path.read_bytes()
        ledger_record = _read_ledger(ledger_path)
    except OSError as error:
        raise AdmissionError("replacement predecessor ledger is absent") from error
    if (_sha256(ledger_bytes) != ledger["sha256"]
            or ledger_record.get("status") != "consumed-before-context"
            or any(ledger_record.get(key) != predecessor[key] for key in (
                "decision_id", "decision_sha256", "grant_id", "grant_sha256", "source_identity"))
            or ledger_record.get("unit_id") != unit):
        raise AdmissionError("predecessor ledger differs from the replacement binding")
    if not isinstance(predecessor["arm_dir"], str) or not _hex(predecessor["result_sha256"]) \
            or not _hex(predecessor["integrity_sha256"]):
        raise AdmissionError("predecessor arm binding is incomplete")
    _verify_no_start(Path(predecessor["arm_dir"]), unit, predecessor, disposition, ledger_path, source_root)
    if _present(_replacement_ledger_path(custody, unit)):
        raise AdmissionError("live unit replacement already used; replay refused")
    return {
        "replacement_id": record["replacement_id"],
        "authorization_sha256": authorization_digest,
        "predecessor_ledger_path": str(ledger_path),
        "predecessor_ledger_sha256": ledger["sha256"],
    }


def _selected_calibration(custody: Path, decision_sha256: str, unit: str) -> tuple[Path, dict[str, Any]] | None:
    """Select the current decision's attempt: a replacement, else a canonical ledger."""
    replaced = _replacement_ledger_path(custody, unit)
    if _present(replaced):
        record = _read_ledger(replaced, REPLACEMENT_CONSUMPTION_SCHEMA)
        if record.get("decision_sha256") == decision_sha256:
            return replaced, record
    canonical = _ledger_path(custody, unit)
    if _present(canonical):
        record = _read_ledger(canonical)
        if record.get("decision_sha256") == decision_sha256:
            return canonical, record
    return None


def _verify_calibration_attempts(source_root: Path, custody: Path, decision: Mapping[str, Any],
                                 grant: Mapping[str, Any], facts: Mapping[str, str]) -> None:
    """Resolve the explicitly selected current-source attempt of every calibration unit."""
    from . import execution
    for unit in _calibration_units():
        if grant["schema"] != GRANT_SCHEMA_V2:
            # Legacy v1 check, unchanged: the canonical ledger under this
            # decision.  A replaced unit can only be selected explicitly (v2).
            path = _ledger_path(custody, unit)
            if not path.exists() or _read_ledger(path).get("decision_sha256") != decision["decision_sha256"]:
                raise AdmissionError("acceptance requires every calibration unit consumed first")
            continue
        selected = _selected_calibration(custody, decision["decision_sha256"], unit)
        if selected is None:
            raise AdmissionError("acceptance requires every calibration unit consumed first")
        attempt = grant["calibration_attempts"][unit]
        arm_dir = Path(attempt["arm_dir"])
        if arm_dir.resolve() != arm_dir or not _outside(arm_dir, source_root):
            raise AdmissionError("selected calibration attempt must be outside the source tree")
        try:
            result_bytes = (arm_dir / "result.json").read_bytes()
            result = execution.read_arm_result(arm_dir)
        except (OSError, TypeError, ValueError) as error:
            raise AdmissionError("selected calibration attempt is unreadable") from error
        if _sha256(result_bytes) != attempt["result_sha256"] or result.get("status") != "complete":
            raise AdmissionError("selected calibration attempt is not a complete current attempt")
        receipt = result.get("live_admission")
        try:
            verify_receipt(receipt, unit=unit)
        except (OSError, ValueError) as error:
            raise AdmissionError("selected calibration attempt receipt is invalid") from error
        if (receipt["ledger_path"] != str(selected[0])
                or receipt["decision_sha256"] != decision["decision_sha256"]
                or receipt["source_identity"] != facts["source_identity"]):
            raise AdmissionError("selected calibration attempt is not the current decision's attempt")


def admit(
    root: str | Path,
    authorization: Any,
    unit: str,
    *,
    runtime_inputs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate one unit against external authority without consuming it."""
    source_root = Path(root)
    loaded = load_authorization(source_root, authorization)
    decision, grant, custody = loaded["decision"], loaded["grant"], loaded["custody_root"]
    if unit not in grant["units"]:
        raise AdmissionError("live unit is not named by the grant")
    _require_unconsumed(custody, grant, unit)
    facts = source_facts(source_root)
    if decision["source"] != facts:
        raise AdmissionError("manager decision source identity is stale or mismatched")
    routes = decision["routes"]
    if not isinstance(routes, Mapping) or dict(routes) != route_map(source_root):
        raise AdmissionError("manager decision route digests differ from frozen routes")
    if runtime_inputs is None:
        raise AdmissionError("sealed live runtime inputs are required")
    from . import runtime_manifest
    runtime_manifest.verify(runtime_inputs, probe_versions=False)
    runtime_digest = runtime_manifest.manifest_digest(runtime_inputs)
    if runtime_digest != decision["runtime"]["live_runtime_manifest_sha256"]:
        raise AdmissionError("live runtime manifest differs from the manager decision")
    replacement = None
    if unit in _replacements(grant):
        replacement = _verify_replacement(source_root, custody, decision, grant, unit, facts, runtime_digest)
    scenario_id = unit.split("/")[0]
    if scenario_id in ACCEPTANCE:
        # Only this decision's selected attempts count; an older decision's
        # failed attempt or a bare replacement reservation never does.
        _verify_calibration_attempts(source_root, custody, decision, grant, facts)
        from .evaluate import load, verify_seal
        seal_path, _ = _evidence_file(grant["evaluation_seal"], "evaluation seal", source_root)
        binary_path, _ = _evidence_file(grant["evaluation_binary"], "evaluation binary", source_root)
        try:
            verify_seal(source_root, binary_path, load(seal_path))
        except (KeyError, TypeError, ValueError) as error:
            raise AdmissionError("acceptance evaluation seal is not current") from error
    _verify_mechanical(decision, source_root, facts)
    return {
        "schema": "apg.h-live-admission-state/v1",
        "unit_id": unit,
        "custody_root": str(custody),
        "decision_id": decision["decision_id"],
        "decision_sha256": decision["decision_sha256"],
        "grant_id": grant["grant_id"],
        "grant_sha256": grant["grant_sha256"],
        "source_identity": facts["source_identity"],
        "source": dict(facts),
        "route_sha256": routes[unit],
        "runtime_manifest_sha256": runtime_digest,
        "native_read_qualification": deepcopy(decision["native_read_qualification"]),
        "replacement": replacement,
    }


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> bytes:
    data = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    parent = path.parent
    fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        child = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(child, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(fd)
    finally:
        os.close(fd)
    return data


def _private_ledger_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise AdmissionError("consumption ledger directory is not private")


def consume(admission: Mapping[str, Any]) -> dict[str, Any]:
    """Consume one admitted unit before context work; never reversible.

    A replacement admission writes an additional record under
    ``h-replacement-consumed``; the canonical ledger is never touched.
    """
    if not isinstance(admission, Mapping) or admission.get("schema") != "apg.h-live-admission-state/v1":
        raise AdmissionError("consumption requires an admitted unit")
    custody = Path(admission["custody_root"])
    replacement = admission.get("replacement")
    record = {
        "schema": CONSUMPTION_SCHEMA,
        "unit_id": admission["unit_id"],
        "status": "consumed-before-context",
        "decision_id": admission["decision_id"],
        "decision_sha256": admission["decision_sha256"],
        "grant_id": admission["grant_id"],
        "grant_sha256": admission["grant_sha256"],
        "source_identity": admission["source_identity"],
        "route_sha256": admission["route_sha256"],
        "runtime_manifest_sha256": admission["runtime_manifest_sha256"],
        "consumed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "replay_authorized": False,
    }
    if replacement is None:
        _private_ledger_directory(custody / LEDGER)
        path = _ledger_path(custody, admission["unit_id"])
        refusal = "live unit already consumed; replay refused"
    else:
        predecessor = Path(replacement["predecessor_ledger_path"])
        if (predecessor != _ledger_path(custody, admission["unit_id"])
                or _sha256(predecessor.read_bytes()) != replacement["predecessor_ledger_sha256"]):
            raise AdmissionError("replacement predecessor ledger changed before consumption")
        _private_ledger_directory(custody / REPLACEMENT_LEDGER)
        path = _replacement_ledger_path(custody, admission["unit_id"])
        refusal = "live unit replacement already used; replay refused"
        record.update({
            "schema": REPLACEMENT_CONSUMPTION_SCHEMA,
            "attempt": REPLACEMENT_ATTEMPT,
            "replacement_id": replacement["replacement_id"],
            "replacement_authorization_sha256": replacement["authorization_sha256"],
            "predecessor_ledger_sha256": replacement["predecessor_ledger_sha256"],
        })
    try:
        data = _write_exclusive(path, record)
    except FileExistsError as error:
        raise AdmissionError(refusal) from error
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "unit_id": admission["unit_id"],
        "ledger_path": str(path),
        "ledger_sha256": _sha256(data),
        "decision_sha256": admission["decision_sha256"],
        "grant_sha256": admission["grant_sha256"],
        "source_identity": admission["source_identity"],
        "route_sha256": admission["route_sha256"],
        "runtime_manifest_sha256": admission["runtime_manifest_sha256"],
    }
    if replacement is not None:
        receipt.update({
            "schema": REPLACEMENT_RECEIPT_SCHEMA,
            "attempt": REPLACEMENT_ATTEMPT,
            "replacement_id": replacement["replacement_id"],
            "replacement_authorization_sha256": replacement["authorization_sha256"],
            "predecessor_ledger_sha256": replacement["predecessor_ledger_sha256"],
        })
    return receipt


_RECEIPT_FIELDS = {"schema", "unit_id", "ledger_path", "ledger_sha256", "decision_sha256",
                   "grant_sha256", "source_identity", "route_sha256", "runtime_manifest_sha256"}
_REPLACEMENT_RECEIPT_FIELDS = _RECEIPT_FIELDS | {
    "attempt", "replacement_id", "replacement_authorization_sha256", "predecessor_ledger_sha256"}


def verify_receipt(receipt: Any, *, unit: str | None = None) -> dict[str, Any]:
    """Re-read the custody ledger that a retained receipt claims.

    A v1 receipt names a canonical ``h-consumed`` record.  A v2 receipt names
    a replacement record and additionally re-hashes its preserved predecessor.
    """
    replacement = isinstance(receipt, Mapping) and receipt.get("schema") == REPLACEMENT_RECEIPT_SCHEMA
    fields = _REPLACEMENT_RECEIPT_FIELDS if replacement else _RECEIPT_FIELDS
    if (not isinstance(receipt, Mapping) or set(receipt) != fields
            or receipt["schema"] not in (RECEIPT_SCHEMA, REPLACEMENT_RECEIPT_SCHEMA)):
        raise AdmissionError("live admission receipt is incomplete")
    if unit is not None and receipt["unit_id"] != unit:
        raise AdmissionError("live admission receipt names another unit")
    path = Path(receipt["ledger_path"])
    if (path.name != _encoded_unit(receipt["unit_id"])
            or path.parent.name != (REPLACEMENT_LEDGER if replacement else LEDGER)):
        raise AdmissionError("live admission receipt ledger path is not canonical")
    if path.resolve() != path or path.is_symlink() or not path.is_file():
        raise AdmissionError("live admission ledger record is unavailable")
    if _sha256(path.read_bytes()) != receipt["ledger_sha256"]:
        raise AdmissionError("live admission ledger record changed")
    record = _read_ledger(path, REPLACEMENT_CONSUMPTION_SCHEMA if replacement else CONSUMPTION_SCHEMA)
    keys = ["unit_id", "decision_sha256", "grant_sha256", "source_identity",
            "route_sha256", "runtime_manifest_sha256"]
    if replacement:
        keys += ["attempt", "replacement_id", "replacement_authorization_sha256",
                 "predecessor_ledger_sha256"]
    for key in keys:
        if record.get(key) != receipt[key]:
            raise AdmissionError("live admission receipt differs from its ledger record")
    if replacement:
        predecessor = path.parent.parent / LEDGER / path.name
        if (not predecessor.is_file() or predecessor.is_symlink()
                or _sha256(predecessor.read_bytes()) != receipt["predecessor_ledger_sha256"]):
            raise AdmissionError("replacement predecessor ledger changed or lost")
    return record


def verify_current(admission: Mapping[str, Any], root: str | Path,
                   runtime_inputs: Mapping[str, Any]) -> None:
    """Post-run check that source, bindings and runtime did not drift."""
    from . import runtime_manifest
    if source_facts(root) != admission["source"]:
        raise AdmissionError("source changed during a live unit")
    if unit_route_sha256(root, admission["unit_id"]) != admission["route_sha256"]:
        raise AdmissionError("frozen route changed during a live unit")
    if runtime_manifest.manifest_digest(runtime_inputs) != admission["runtime_manifest_sha256"]:
        raise AdmissionError("runtime manifest changed during a live unit")


def normalize_authorizations(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and value:
        return list(value)
    raise AdmissionError(UNAVAILABLE)


def _invocation_status(result: Any) -> str:
    value = result.get("provider_invocations") if isinstance(result, Mapping) else None
    if type(value) is not int or value < 0:
        return "unobserved"
    return "zero" if value == 0 else "positive"


def accounting(root: str | Path, authorizations: Any, *,
               arm_receipts: Mapping[str, Mapping[str, Any] | None] | None = None,
               arm_results: Mapping[str, Mapping[str, Any] | None] | None = None) -> dict[str, Any]:
    """Provider-free grant accounting; never starts, retries or deletes anything.

    A replacement row reports its preserved predecessor as historical and
    unselected.  Consumption records are reservations, never provider tasks;
    invocation status comes only from supplied, already-read arm results.
    """
    loaded = [load_authorization(root, item) for item in normalize_authorizations(authorizations)]
    decisions = {item["decision"]["decision_sha256"] for item in loaded}
    if len(decisions) != 1:
        raise AdmissionError("accounting requires grants under one manager decision")
    arm_receipts = dict(arm_receipts or {})
    arm_results = dict(arm_results or {})
    granted: dict[str, Mapping[str, Any]] = {}
    for item in loaded:
        for unit in item["grant"]["units"]:
            if unit in granted:
                raise AdmissionError("one unit is named by more than one grant")
            granted[unit] = item["grant"]
    custody = loaded[0]["custody_root"]
    rows = []
    for unit, grant in granted.items():
        grant_sha = grant["grant_sha256"]
        replacement = unit in _replacements(grant)
        predecessor = None
        if replacement:
            path = _replacement_ledger_path(custody, unit)
            consumed = _present(path)
            record = _read_ledger(path, REPLACEMENT_CONSUMPTION_SCHEMA) if consumed else None
            canonical = _ledger_path(custody, unit)
            old = _read_ledger(canonical) if _present(canonical) else None
            predecessor = {
                "ledger_sha256": _sha256(canonical.read_bytes()) if old is not None else None,
                "decision_sha256": (old or {}).get("decision_sha256"),
                "grant_sha256": (old or {}).get("grant_sha256"),
                "status": "historical-consumed-incomplete" if old is not None else "absent",
                "selected": False,
            }
        else:
            path = _ledger_path(custody, unit)
            consumed = path.exists()
            record = _read_ledger(path) if consumed else None
        receipt = arm_receipts.get(unit)
        retained = False
        if receipt is not None:
            try:
                retained = verify_receipt(receipt, unit=unit).get("grant_sha256") == grant_sha
            except (OSError, ValueError):
                retained = False
        rows.append({
            "unit_id": unit,
            "grant_sha256": grant_sha,
            "attempt": REPLACEMENT_ATTEMPT if replacement else "canonical",
            "consumed": consumed,
            "consumed_under_grant": bool(record and record.get("grant_sha256") == grant_sha),
            "result_retained": retained,
            "provider_invocation": _invocation_status(arm_results.get(unit)),
            "predecessor": predecessor,
            "status": ("unconsumed" if not consumed
                       else "retained" if retained else "consumed-missing-result"),
        })
    invocations = {"zero": 0, "positive": 0, "unobserved": 0}
    for row in rows:
        if row["consumed"]:
            invocations[row["provider_invocation"]] += 1
    return {
        "schema": ACCOUNTING_SCHEMA,
        "decision_sha256": decisions.pop(),
        "granted": len(rows),
        "consumed": sum(row["consumed"] for row in rows),
        "retained": sum(row["result_retained"] for row in rows),
        "missing_results": [row["unit_id"] for row in rows if row["status"] == "consumed-missing-result"],
        "unconsumed": [row["unit_id"] for row in rows if row["status"] == "unconsumed"],
        # Preserved earlier attempts replaced under this decision; never selected.
        "historical_attempts": sum(row["predecessor"] is not None
                                   and row["predecessor"]["status"] == "historical-consumed-incomplete"
                                   for row in rows),
        "replacement_reservations": sum(row["attempt"] == REPLACEMENT_ATTEMPT and row["consumed"]
                                        for row in rows),
        # Consumed units by observed provider invocation; reservations are not tasks.
        "provider_invocations": {"observed": invocations["zero"] + invocations["positive"], **invocations},
        "units": rows,
        "provider_starts_by_accounting": 0,
    }


def template() -> dict[str, dict[str, Any]]:
    """Return deliberately invalid, non-authorizing decision and grant shapes."""
    note = "NON-AUTHORIZING TEMPLATE: an external manager must author, digest and place real records"
    return {
        "manager-decision": {
            "template": note,
            "schema": DECISION_SCHEMA,
            "decision_id": "<manager-assigned>",
            "disposition": "<authorize-live-grant only by external manager>",
            "cohort_decision": COHORT_DECISION,
            "scenario15": SCENARIO15,
            "issued_at": "<UTC timestamp ending in Z>",
            "custody_root": "<absolute private operator custody directory outside source>",
            "source": {key: "<recomputed by live_admission.source_facts>" for key in (
                "source_identity", "scenario_bindings_sha256", "promotion_preregistration_sha256",
                "subject_manifest_sha256", "d1_carry_forward_sha256")},
            "routes": "<live_admission.route_map(root): 53 unit route digests>",
            "runtime": {"live_runtime_manifest_sha256": "<sealed live runtime manifest digest>",
                        "transaction_directory": "<retained host mechanical transaction directory>"},
            "evidence": {**{key: {"path": "<absolute>", "sha256": "<sha256>"} for key in _EVIDENCE},
                         "skill_approvals": "<one {path, sha256} per primary skill>"},
            "native_read_qualification": None,
            "decision_sha256": "<live_admission.self_digest(record, 'decision_sha256')>",
        },
        "live-grant": {
            "template": note,
            "schema": GRANT_SCHEMA,
            "grant_id": "<manager-assigned>",
            "decision_sha256": "<decision digest>",
            "custody_root": "<same as decision>",
            "units": "<subset of live_admission.all_units(root); never scenario-15>",
            "start_ceiling": "<exactly len(units), at most 53>",
            "max_starts_per_unit": 1,
            "replay_prohibited": True,
            "retries": 0,
            "valid_until": "<UTC timestamp ending in Z>",
            "evaluation_seal": "<{path, sha256} required for any acceptance unit>",
            "evaluation_binary": "<{path, sha256} required for any acceptance unit>",
            "grant_sha256": "<live_admission.self_digest(record, 'grant_sha256')>",
        },
    }


def replacement_template() -> dict[str, dict[str, Any]]:
    """Return deliberately invalid, non-authorizing replacement and v2 grant shapes."""
    note = ("TEMPLATE-NOT-AUTHORITY: an external manager must review the exact predecessor "
            "evidence, then author, digest and place real records")
    return {
        "replacement-authorization": {
            "template": note,
            "schema": REPLACEMENT_SCHEMA,
            "replacement_id": "<manager-assigned>",
            "unit_id": "<the one canonical scenario unit being replaced>",
            "custody_root": "<the same campaign custody root>",
            "predecessor": {
                "decision_id": "<predecessor decision_id>",
                "decision_sha256": "<predecessor decision digest>",
                "decision_record": {"path": "<absolute custody path>", "sha256": "<file bytes digest>"},
                "grant_id": "<predecessor grant_id>",
                "grant_sha256": "<predecessor grant digest>",
                "grant_record": {"path": "<absolute custody path>", "sha256": "<file bytes digest>"},
                "ledger": {"path": "<custody>/h-consumed/<unit>.json", "sha256": "<file bytes digest>"},
                "source_identity": "<predecessor ledger source_identity>",
                "arm_dir": "<absolute predecessor arm directory>",
                "result_sha256": "<result.json bytes digest>",
                "integrity_sha256": "<integrity.json bytes digest>",
            },
            "disposition": {
                "kind": NO_START,
                "provider_invocations": 0,
                "failure": "<predecessor result failure>",
                "failure_step": "<failure_detail step, or null for a legacy result>",
                "manager_evidence": "<{path, sha256} required exactly when failure_detail is absent>",
            },
            "successor": {"decision_sha256": "<current decision digest>",
                          "source_identity": "<live_admission.source_facts source_identity>",
                          "runtime_manifest_sha256": "<current sealed runtime manifest digest>"},
            "max_replacements": 1,
            "retries": 0,
            "replay_prohibited": True,
            "issued_at": "<UTC timestamp ending in Z>",
            "valid_until": "<UTC timestamp ending in Z>",
            "authorization_sha256": "<live_admission.self_digest(record, 'authorization_sha256')>",
        },
        "live-grant-v2": {
            **template()["live-grant"],
            "template": note,
            "schema": GRANT_SCHEMA_V2,
            "replacements": "<{unit: {path, sha256}} for explicitly authorized replacement units only>",
            "calibration_attempts": "<null, or for an acceptance grant {calibration unit: {arm_dir, result_sha256}}>",
        },
    }


__all__ = [
    "ACCOUNTING_SCHEMA", "AdmissionError", "CONSUMPTION_SCHEMA", "DECISION_SCHEMA",
    "GRANT_SCHEMA", "GRANT_SCHEMA_V2", "MAX_START_CEILING", "PRE_PROVIDER_STEPS", "RECEIPT_SCHEMA",
    "REPLACEMENT_CONSUMPTION_SCHEMA", "REPLACEMENT_LEDGER", "REPLACEMENT_RECEIPT_SCHEMA",
    "REPLACEMENT_SCHEMA", "UNAVAILABLE", "accounting",
    "admit", "all_units", "check_shape", "consume", "load_authorization",
    "normalize_authorizations", "promotion_unit", "replacement_template", "route_map", "scenario_unit",
    "self_digest",
    "source_facts", "template", "unit_route_sha256", "verify_current", "verify_receipt",
]
