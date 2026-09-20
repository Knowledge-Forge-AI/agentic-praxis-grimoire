"""Execution-owned receipt retention and symmetric evaluation task bytes.

The arm result is only an index into this receipt bundle.  The bundle keeps
the source, subject factory, route, contract, runtime and terminal evidence
that a later owner needs to re-read without trusting a caller supplied arm
dictionary.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from agent_phase.acquisition_records import delivery_entries, records

from . import response_contract

REVIEW_SCENARIOS = frozenset({"scenario-03", "scenario-11", "scenario-12", "scenario-14"})
TASK_CONTRACT_SCHEMA = "apg.h-task-contract/v1"
SOURCE_BINDING_SCHEMA = "apg.h-source-binding/v1"
SUBJECT_FACTORY_SCHEMA = "apg.h-subject-factory-identity/v1"
ORACLE_OWNER_SCHEMA = "apg.h-oracle-owner/v1"
ARM_EVIDENCE_SCHEMA = "apg.h-arm-evidence/v1"
NOT_APPLICABLE_SCHEMA = "apg.h-not-applicable/v1"
RECOVERY_RECEIPT_SCHEMA = "apg.h-recovery-receipt/v1"
RECOVERY_QUALIFICATION_SCHEMA = "apg.h-recovery-qualification/v1"
SETTINGS_OBSERVATION_SCHEMA = "apg.h-settings-observation/v1"
DISCOVERY_OBSERVATION_SCHEMA = "apg.h-discovery-observation/v1"
DISCOVERY_ABSENT_OBSERVATION_SCHEMA = "apg.h-discovery-observation/v2"
DISCOVERY_ABSENCE_SCHEMA = "apg.h-discovery-absence/v1"
DISCOVERY_OBSERVATION_SCHEMAS = frozenset({DISCOVERY_OBSERVATION_SCHEMA, DISCOVERY_ABSENT_OBSERVATION_SCHEMA})
AUTHORITY_SCHEMA = "apg.h-authority-receipt/v1"
QUALIFICATION_ELIGIBILITY_SCHEMA = "apg.h-qualification-eligibility/v1"
EXACT_RECOVERY_SCHEMA = "apg.h-exact-recovery/v1"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def task_prompt(scenario):
    task = scenario["task_input"]["instruction"].encode()
    return task + response_bytes(scenario)


def response_bytes(scenario):
    if scenario["scenario_id"] in REVIEW_SCENARIOS:
        return ("\n\nEvaluation scenario: " + scenario["scenario_id"] + "\n"
                + response_contract.instructions()).encode()
    return b""


def contract_identity(scenario):
    raw = response_bytes(scenario)
    return {"schema": "apg.h-evaluation-contract-identity/v1", "bytes": len(raw),
            "sha256": _sha256(raw), "required": bool(raw)}


def task_contract(scenario, *, source_binding: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Bind the exact frozen task bytes and evaluation response contract."""
    prompt = task_prompt(scenario)
    contract = contract_identity(scenario)
    result: dict[str, Any] = {
        "schema": TASK_CONTRACT_SCHEMA,
        "owner": "h-execution-package",
        "scenario_id": scenario.get("scenario_id"),
        "prompt": {"bytes": len(prompt), "sha256": _sha256(prompt)},
        "response_contract": contract,
    }
    if source_binding is not None:
        result["source_binding"] = deepcopy(dict(source_binding))
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"arm evidence JSON is unavailable: {path.name}") from exc


def _not_applicable(kind: str) -> dict[str, Any]:
    """Return an explicit absence receipt instead of silently dropping a seam."""
    return {"schema": NOT_APPLICABLE_SCHEMA, "kind": kind, "status": "not_applicable"}


def _optional_receipt(value: Any, *, schema: str, kind: str) -> dict[str, Any]:
    if value is None:
        return _not_applicable(kind)
    if not isinstance(value, Mapping):
        raise ValueError(f"{kind} receipt is malformed")
    result = deepcopy(dict(value))
    if result.get("schema") not in {schema, RECOVERY_QUALIFICATION_SCHEMA, NOT_APPLICABLE_SCHEMA}:
        raise ValueError(f"{kind} receipt schema is invalid")
    if not isinstance(result.get("status"), str) or not result["status"]:
        raise ValueError(f"{kind} receipt status is absent")
    return result


def observation_state(value: Any, *, field: str) -> dict[str, Any]:
    """Retain provider revision/restart observations without inventing facts."""
    if value is None:
        return {
            "schema": "apg.h-observation-state/v1",
            "status": "not_observed",
            "value": None,
            "source": "provider-terminal",
            "field": field,
            "reason": f"provider did not emit {field}",
        }
    if not isinstance(value, list):
        raise ValueError(f"{field} observation must be a list or absent")
    return {
        "schema": "apg.h-observation-state/v1",
        "status": "observed",
        "value": deepcopy(value),
        "source": "provider-terminal",
        "field": field,
    }


def _validate_observation_state(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema") != "apg.h-observation-state/v1":
        raise ValueError(f"{field} observation state is invalid")
    if value.get("field") != field or value.get("source") != "provider-terminal":
        raise ValueError(f"{field} observation provenance is invalid")
    status = value.get("status")
    if status == "not_observed":
        if value.get("value") is not None or not isinstance(value.get("reason"), str) or not value["reason"]:
            raise ValueError(f"{field} not-observed state is incomplete")
    elif status == "observed":
        if not isinstance(value.get("value"), list):
            raise ValueError(f"{field} observed state is incomplete")
    else:
        raise ValueError(f"{field} observation status is invalid")
    return dict(value)


def _live_admission_reason(
    receipt: Any,
    source: Any,
    source_seal: Mapping[str, Any],
    route: Any,
) -> str | None:
    """Return why a live admission receipt cannot replace readiness, if it cannot."""
    if receipt is None:
        return "source readiness prerequisites are not accepted"
    from . import live_admission
    from .readiness import source_identity
    try:
        if not isinstance(source, Mapping) or not isinstance(route, Mapping) or route.get("execution") != "live":
            raise ValueError("receipt is not bound to a live source route")
        unit = live_admission.scenario_unit(source.get("scenario_id"), source.get("mode"))
        live_admission.verify_receipt(receipt, unit=unit)
        files = source_seal.get("files")
        if not isinstance(files, Mapping) or receipt["source_identity"] != source_identity(dict(files)):
            raise ValueError("receipt source identity differs from the retained source inventory")
        if receipt["route_sha256"] != source.get("route_sha256"):
            raise ValueError("receipt route differs from the retained source route")
    except (OSError, KeyError, TypeError, ValueError) as error:
        return f"live admission receipt invalid: {error}"
    return None


def qualification_eligibility(
    bundle: Mapping[str, Any],
    *,
    require_live: bool = True,
) -> dict[str, Any]:
    """Derive package eligibility only from retained source identities.

    Instrumented arms remain useful unit seams, but their caller-owned or
    test-only identities cannot qualify the provider package.  This decision
    intentionally ignores copied completion/coverage/authority claims.
    """
    reasons: list[str] = []
    identity = bundle.get("identity") if isinstance(bundle.get("identity"), Mapping) else bundle
    source = bundle.get("source_binding") or identity.get("source_binding")
    subject_factory = bundle.get("subject_factory") or identity.get("subject_factory")
    oracle_owner = bundle.get("oracle_owner") or identity.get("oracle_owner")
    task = bundle.get("task_contract") or identity.get("task_contract")
    source_seal = bundle.get("source_seal")
    runtime = bundle.get("runtime")
    route = bundle.get("route")

    def digest(value: Any) -> bool:
        return (isinstance(value, str) and len(value) == 64
                and all(char in "0123456789abcdef" for char in value))

    if (not isinstance(source, Mapping) or source.get("schema") != SOURCE_BINDING_SCHEMA
            or source.get("owner") != "testing.h_eval.preregistration"
            or source.get("status") in {"legacy-direct-arm", "test-only", "caller-supplied"}):
        reasons.append("source binding is not repository-owned")
    if (not isinstance(source, Mapping)
            or not isinstance(source.get("scenario_id"), str)
            or not isinstance(source.get("mode"), str)
            or source.get("bindings_path") != "testing/h_eval/scenario-bindings.json"
            or not isinstance(source.get("scenario_path"), str)
            or not digest(source.get("bindings_sha256"))
            or not digest(source.get("scenario_sha256"))
            or not digest(source.get("route_sha256"))
            or not isinstance(source.get("source_sha256"), Mapping)
            or not source.get("source_sha256")
            or any(not isinstance(key, str) or not digest(value)
                   for key, value in source.get("source_sha256", {}).items())
            or not isinstance(source.get("identity_sources"), list)
            or not source.get("identity_sources")
            or any(not isinstance(value, str) for value in source.get("identity_sources", []))):
        reasons.append("source binding digest identity is incomplete")
    if (not isinstance(subject_factory, Mapping)
            or subject_factory.get("schema") != SUBJECT_FACTORY_SCHEMA
            or subject_factory.get("owner") != "testing.h_eval.subjects"
            or subject_factory.get("status") in {"test-only", "caller-supplied-instrumented-fixture"}):
        reasons.append("subject factory is not repository-owned")
    if (not isinstance(oracle_owner, Mapping)
            or oracle_owner.get("schema") != ORACLE_OWNER_SCHEMA
            or oracle_owner.get("owner") != "testing.h_eval.oracles"
            or oracle_owner.get("status") in {"test-only", "instrumented-fixture", "caller-supplied-instrumented-fixture"}):
        reasons.append("oracle owner is not repository-owned")
    if (not isinstance(task, Mapping) or task.get("schema") != TASK_CONTRACT_SCHEMA
            or not isinstance(source, Mapping)
            or task.get("source_binding") != source
            or task.get("scenario_id") != source.get("scenario_id")):
        reasons.append("task contract identity is unavailable")

    seal_schema = source_seal.get("schema") if isinstance(source_seal, Mapping) else None
    if (not isinstance(source_seal, Mapping)
            or not isinstance(seal_schema, str)
            or not (seal_schema.startswith("apg.h-readiness-seal/") or seal_schema.startswith("apg.h-source-seal/"))
            or source_seal.get("status") == "not_applicable"):
        reasons.append("source readiness seal is unavailable or not applicable")
    elif type(source_seal.get("prerequisites_ready")) is not bool:
        reasons.append("source readiness state is not explicit")
    elif require_live and source_seal.get("prerequisites_ready") is not True:
        # The readiness seal stays explicitly not-ready.  A live arm is instead
        # admitted by an external decision/grant whose consumption receipt
        # binds this arm's unit, route and retained source inventory.
        reason = _live_admission_reason(bundle.get("live_admission"), source, source_seal, route)
        if reason is not None:
            reasons.append(reason)

    runtime_schema = runtime.get("schema") if isinstance(runtime, Mapping) else None
    revalidation = runtime.get("revalidation") if isinstance(runtime, Mapping) else None
    runtime_valid = False
    if isinstance(runtime, Mapping) and runtime_schema == "apg.h-runtime-inputs/v2":
        # A copied observation/status mapping cannot qualify a package arm.
        # Verify the complete v2 manifest after removing only the separate
        # post-run observation retained alongside it.
        try:
            from . import runtime_manifest
            manifest = dict(runtime)
            manifest.pop("revalidation", None)
            runtime_manifest.verify_complete(manifest, probe_versions=False)
            runtime_valid = (
                isinstance(revalidation, Mapping)
                and revalidation.get("schema") == "apg.h-runtime-observation/v1"
                and revalidation.get("status") == "valid"
                and revalidation.get("post_run") == "valid"
                and revalidation.get("test_only") is not True
                and isinstance(revalidation.get("transaction"), Mapping)
                and revalidation["transaction"].get("schema") == "apg.h-runtime-transaction/v1"
                and revalidation["transaction"].get("revalidate") == "valid"
                and revalidation["transaction"].get("manifest_sha256") == runtime_manifest.manifest_digest(manifest)
            )
        except (OSError, TypeError, ValueError):
            runtime_valid = False
    if not runtime_valid:
        reasons.append("runtime identity is unavailable or test-only")

    if not isinstance(route, Mapping):
        reasons.append("route identity is unavailable")
    elif require_live and route.get("execution") != "live":
        reasons.append("instrumented execution is test-only")
    if isinstance(bundle.get("result"), Mapping):
        # These are caller-facing claims.  They never make an ineligible bundle
        # eligible, and explicit injection markers are retained as a reason.
        result = bundle["result"]
        for field in ("coverage", "authority", "task_oracle"):
            value = result.get(field)
            if isinstance(value, str) and value.startswith("injected"):
                reasons.append(f"caller-injected {field} claim")

    return {
        "schema": QUALIFICATION_ELIGIBILITY_SCHEMA,
        "status": "eligible" if not reasons else "ineligible",
        "require_live": require_live,
        "reasons": sorted(set(reasons)),
        "source_owner": source.get("owner") if isinstance(source, Mapping) else None,
        "subject_factory_owner": subject_factory.get("owner") if isinstance(subject_factory, Mapping) else None,
        "oracle_owner": oracle_owner.get("owner") if isinstance(oracle_owner, Mapping) else None,
        "runtime_schema": runtime_schema,
        "route_execution": route.get("execution") if isinstance(route, Mapping) else None,
    }


def derive_exact_recovery(
    scenario: Mapping[str, Any],
    *,
    result: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """Derive exact recovery from retained authority and witnessed events.

    Native Read coverage by itself is insufficient.  A positive result needs a
    live route, a bound scope/session, an authorized path plus bytes/digest,
    one retained late delivery event, unchanged authority, and no replay.
    """
    evidence: dict[str, Any] = {
        "schema": EXACT_RECOVERY_SCHEMA,
        "status": "not_observed",
        "value": False,
        "source": "retained-evidence",
        "reason": "exact recovery evidence is incomplete",
    }
    if (scenario.get("cohorts") or {}).get("exact_recovery") is not True:
        evidence["reason"] = "scenario does not require exact recovery"
        return False, evidence
    route = receipt.get("route")
    if not isinstance(route, Mapping) or route.get("execution") != "live":
        evidence["reason"] = "exact recovery requires a live route"
        return False, evidence
    activity = receipt.get("activity")
    context = receipt.get("context")
    authority = receipt.get("authority")
    terminal = receipt.get("provider_terminal")
    if not all(isinstance(value, Mapping) for value in (activity, context, authority, terminal)):
        evidence["reason"] = "retained authority/activity/transport evidence is incomplete"
        return False, evidence
    scope = {key: context.get(key) for key in ("run_id", "binding_id", "attempt_id")}
    if any(not isinstance(value, str) or not value for value in scope.values()):
        evidence["reason"] = "recovery attempt scope is absent"
        return False, evidence
    if (activity.get("attempts") != ["one"] or activity.get("retries") != 0
            or activity.get("restarts") != 0 or result.get("replay_authorized") is not False
            or context.get("replay_authorized") is True
            or authority.get("replay_authorized") is not False):
        evidence["reason"] = "recovery attempt is replayed or not single-use"
        return False, evidence
    if (terminal.get("exit_code") != 0 or terminal.get("truncated") is True
            or terminal.get("stderr_truncated") is True):
        evidence["reason"] = "provider terminal did not complete"
        return False, evidence
    if (authority.get("permitted") is not True or authority.get("unchanged") is not True
            or authority.get("directories_unchanged") is not True or authority.get("git_unchanged") is not True):
        evidence["reason"] = "post-run authority is not unchanged"
        return False, evidence

    def digest(value: Any) -> bool:
        return (isinstance(value, str) and len(value) == 64
                and all(char in "0123456789abcdef" for char in value))

    native = activity.get("native_reads")
    if (not isinstance(native, Mapping)
            or native.get("schema") != "apg.claude-native-reads/v1"
            or native.get("coverage") != "complete"
            or native.get("scope") != scope
            or not isinstance(native.get("session_id"), str)
            or not native.get("session_id")
            or not isinstance(native.get("reads"), list)
            or not isinstance(native.get("events"), list)
            or not isinstance(native.get("terminal"), Mapping)
            or native["terminal"].get("type") != "result"
            or native["terminal"].get("subtype") != "success"
            or (native["terminal"].get("session_id") is not None
                and native["terminal"].get("session_id") != native.get("session_id"))
            or not isinstance(native.get("raw_stream"), Mapping)
            or type(native["raw_stream"].get("bytes")) is not int
            or native["raw_stream"].get("bytes") < 0
            or not digest(native["raw_stream"].get("sha256"))):
        evidence["reason"] = "native recovery scope/session/result evidence is incomplete"
        return False, evidence

    recovery_authority = native.get("recovery_authority")
    prelaunch = recovery_authority.get("prelaunch") if isinstance(recovery_authority, Mapping) else None
    postrun = recovery_authority.get("postrun") if isinstance(recovery_authority, Mapping) else None
    if (not isinstance(recovery_authority, Mapping)
            or recovery_authority.get("schema") != "apg.h-recovery-authority/v1"
            or recovery_authority.get("scope") != scope
            or recovery_authority.get("session_id") != native.get("session_id")
            or not isinstance(prelaunch, Mapping)
            or prelaunch.get("status") != "captured"
            or not isinstance(prelaunch.get("entries"), list)
            or not isinstance(postrun, Mapping)
            or postrun.get("status") != "verified"
            or not isinstance(postrun.get("entries"), list)):
        evidence["reason"] = "prelaunch recovery authority/readback is incomplete"
        return False, evidence

    def entry_valid(entry: Any) -> bool:
        return (isinstance(entry, Mapping)
                and isinstance(entry.get("id"), str) and bool(entry["id"])
                and isinstance(entry.get("path"), str) and bool(entry["path"])
                and not entry["path"].startswith("/")
                and "\\" not in entry["path"]
                and all(part not in {"", ".", ".."} for part in entry["path"].split("/"))
                and type(entry.get("bytes")) is int and entry["bytes"] > 0
                and digest(entry.get("sha256"))
                and (entry.get("content_identity") in (None, entry.get("sha256"))))

    prelaunch_entries = prelaunch["entries"]
    postrun_entries = postrun["entries"]
    if (any(not entry_valid(entry) for entry in prelaunch_entries)
            or any(not entry_valid(entry) for entry in postrun_entries)):
        evidence["reason"] = "prelaunch recovery authority entry is malformed"
        return False, evidence
    canonical_entries = lambda entries: sorted(
        json.dumps(dict(entry), sort_keys=True, separators=(",", ":"))
        for entry in entries
    )
    if canonical_entries(prelaunch_entries) != canonical_entries(postrun_entries):
        evidence["reason"] = "post-run recovery authority differs from prelaunch mapping"
        return False, evidence
    acquisitions = receipt.get("acquisitions", [])
    if not isinstance(acquisitions, list):
        evidence["reason"] = "retained acquisition evidence is malformed"
        return False, evidence
    if (any(not isinstance(row, Mapping) or not isinstance(row.get("event"), Mapping)
            for row in acquisitions)):
        evidence["reason"] = "retained acquisition event is malformed"
        return False, evidence

    if (any(not isinstance(row, Mapping) for row in native["reads"])
            or any(not isinstance(event, Mapping) for event in native["events"])):
        evidence["reason"] = "native recovery observation entry is malformed"
        return False, evidence
    read_ids = [row.get("id") for row in native["reads"]]
    if (any(not isinstance(value, str) or not value for value in read_ids)
            or len(set(read_ids)) != len(read_ids)):
        evidence["reason"] = "native Read IDs are duplicated or incomplete"
        return False, evidence
    reads_by_id = {row["id"]: row for row in native["reads"]}
    native_events = list(native["events"])
    event_ids = [event.get("event_id") for event in native_events]
    if (any(not isinstance(value, str) or not value for value in event_ids)
            or len(set(event_ids)) != len(event_ids)):
        evidence["reason"] = "native recovery event IDs are duplicated or incomplete"
        return False, evidence
    recovery_tool_ids = [event.get("tool_use_id") for event in native_events
                         if event.get("channel") == "recovery_read"]
    if (any(not isinstance(value, str) or not value for value in recovery_tool_ids)
            or len(set(recovery_tool_ids)) != len(recovery_tool_ids)):
        evidence["reason"] = "native recovery tool-use IDs are duplicated or incomplete"
        return False, evidence
    rows = list(acquisitions)
    existing_event_ids = {
        row.get("event", {}).get("event_id")
        for row in rows if isinstance(row, Mapping) and isinstance(row.get("event"), Mapping)
    }
    rows.extend(
        {"event": event} for event in native_events
        if event.get("event_id") not in existing_event_ids
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        event = row.get("event") if isinstance(row, Mapping) else None
        if not isinstance(event, Mapping) or event.get("phase") != "late":
            continue
        if event.get("channel") != "recovery_read":
            continue
        if any(event.get(key) != value for key, value in scope.items()):
            evidence["reason"] = "recovery delivery scope differs from attempt scope"
            return False, evidence
        entry = event.get("recovery_entry")
        if (not entry_valid(entry)
                or dict(entry) not in prelaunch_entries
                or dict(entry) not in postrun["entries"]
                or event.get("provenance") != entry.get("path")
                or event.get("controlled_bytes") != entry.get("bytes")
                or event.get("payload_sha256") != entry.get("sha256")
                or not isinstance(event.get("event_id"), str)
                or not digest(event.get("event_id"))
                or event.get("kind") != "recovery_read_observed"
                or event.get("raw_stream_sha256") != native.get("raw_stream", {}).get("sha256")
                or not isinstance(event.get("tool_use_id"), str)
                or event.get("event_id") != _sha256(
                    json.dumps([scope, native["raw_stream"]["sha256"], event["tool_use_id"]], sort_keys=True).encode()
                )):
            evidence["reason"] = "recovery delivery lacks source-owned authority binding"
            return False, evidence
        read_id = event.get("tool_use_id")
        read = reads_by_id.get(read_id)
        read_result = read.get("result") if isinstance(read, Mapping) else None
        structured = read_result.get("structured_file") if isinstance(read_result, Mapping) else None
        raw_identity = read_result.get("raw_identity") if isinstance(read_result, Mapping) else None
        if (not isinstance(read, Mapping) or not isinstance(read.get("input"), Mapping)
                or read["input"].get("file_path") != event.get("requested_path")
                or not isinstance(read_result, Mapping)
                or read_result.get("authorized_recovery") != dict(entry)
                or not isinstance(structured, Mapping)
                or structured.get("filePath") != event.get("requested_path")
                or not isinstance(structured.get("content"), str)
                or type(structured.get("startLine")) is not int
                or type(structured.get("numLines")) is not int
                or type(structured.get("totalLines")) is not int
                or structured.get("startLine") != 1
                or structured.get("numLines") != structured.get("totalLines")
                or len(structured["content"].encode()) != entry["bytes"]
                or _sha256(structured["content"].encode()) != entry["sha256"]
                or not isinstance(raw_identity, Mapping)
                or raw_identity.get("bytes") != entry["bytes"]
                or raw_identity.get("sha256") != entry["sha256"]):
            evidence["reason"] = "recovery Read result shape is unsupported or unbound"
            return False, evidence
        candidates.append(dict(event))
    if not candidates:
        evidence["reason"] = "no retained authorized recovery delivery event"
        return False, evidence
    evidence.update(status="observed", value=True,
                    event_ids=[event["event_id"] for event in candidates], scope=scope,
                    session_id=native["session_id"], authority_entries=prelaunch_entries)
    return True, evidence


def _observation_identity(value: Any, name: str) -> dict[str, Any]:
    """Validate the private path/device/inode/byte identity vocabulary."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} identity is absent")
    required = ("path", "device", "inode", "mode", "bytes", "sha256")
    if any(key not in value for key in required):
        raise ValueError(f"{name} identity is incomplete")
    if (not isinstance(value["path"], str) or not value["path"].startswith("/")
            or type(value["device"]) is not int or type(value["inode"]) is not int
            or type(value["mode"]) is not int or type(value["bytes"]) is not int
            or value["bytes"] < 0 or not isinstance(value["sha256"], str)
            or len(value["sha256"]) != 64):
        raise ValueError(f"{name} identity is malformed")
    return dict(value)


def _typed_observation(value: Any, *, schema: str, kind: str) -> dict[str, Any]:
    """Validate a source-owned typed observation without accepting booleans."""
    if not isinstance(value, Mapping) or value.get("schema") != schema:
        raise ValueError(f"{kind} observation schema is invalid")
    result = dict(value)
    _observation_identity(result.get("before"), f"{kind} before")
    _observation_identity(result.get("after"), f"{kind} after")
    before_inputs = result.get("inputs_before")
    after_inputs = result.get("inputs_after")
    if before_inputs is not None or after_inputs is not None:
        if not isinstance(before_inputs, list) or not isinstance(after_inputs, list):
            raise ValueError(f"{kind} input identities are malformed")
        if len(before_inputs) != len(after_inputs) or not before_inputs:
            raise ValueError(f"{kind} input identities are incomplete")
        for index, item in enumerate(before_inputs):
            _observation_identity(item, f"{kind} before input {index}")
            _observation_identity(after_inputs[index], f"{kind} after input {index}")
        if before_inputs[0] != result["before"] or after_inputs[0] != result["after"]:
            raise ValueError(f"{kind} primary identity is not source-bound")
    return result


def _absence_component(value: Any, expected_path: Path) -> None:
    if not isinstance(value, Mapping) or value.get("path") != str(expected_path):
        raise ValueError("discovery absence component path is not lexical")
    base = {"path", "kind", "device", "inode", "mode"}
    if any(type(value.get(key)) is not int for key in ("device", "inode", "mode")):
        raise ValueError("discovery absence component identity is malformed")
    if value.get("kind") == "directory":
        if set(value) != base or not stat.S_ISDIR(value["mode"]):
            raise ValueError("discovery absence directory component is malformed")
    elif value.get("kind") == "symlink":
        target = value.get("target")
        if (set(value) != base | {"link_text", "target"} or not stat.S_ISLNK(value["mode"])
                or not isinstance(value["link_text"], str) or not value["link_text"]
                or not isinstance(target, Mapping) or set(target) != {"device", "inode", "mode"}
                or any(type(target[key]) is not int for key in target)
                or not stat.S_ISDIR(target["mode"])):
            raise ValueError("discovery absence link component is malformed")
    else:
        raise ValueError("discovery absence component kind is invalid")


def _absence_record(value: Any, name: str) -> dict[str, Any]:
    """Validate an explicit absent-root record; it is never a content inventory."""
    fields = {"schema", "kind", "lexical_root", "missing", "existing_prefix", "components", "sha256"}
    if (not isinstance(value, Mapping) or set(value) != fields
            or value["schema"] != DISCOVERY_ABSENCE_SCHEMA or value["kind"] != "absent"):
        raise ValueError(f"{name} absence record is malformed")
    from .execution import discovery_absence_digest
    if not isinstance(value["sha256"], str) or discovery_absence_digest(value) != value["sha256"]:
        raise ValueError(f"{name} absence record digest mismatch")
    root, missing, prefix, components = (value["lexical_root"], value["missing"],
                                         value["existing_prefix"], value["components"])
    if (not isinstance(root, str) or not root.startswith("/") or not isinstance(prefix, str)
            or not isinstance(missing, list) or not missing
            or any(not isinstance(item, str) for item in missing) or missing[-1] != root
            or not isinstance(components, list) or not components):
        raise ValueError(f"{name} absence record is incomplete")
    expected = Path("/")
    for index, component in enumerate(components):
        if index:
            leaf = Path(str(component.get("path", ""))).name if isinstance(component, Mapping) else ""
            if not leaf:
                raise ValueError(f"{name} absence component path is not lexical")
            expected = expected / leaf
        _absence_component(component, expected)
    if str(expected) != prefix:
        raise ValueError(f"{name} absence record prefix is not its last component")
    parent = Path(prefix)
    for item in missing:
        if Path(item).parent != parent or Path(item) == parent:
            raise ValueError(f"{name} absence record missing path is not lexical")
        parent = Path(item)
    return dict(value)


def discovery_scope(receipt: Any) -> str:
    """Classify a validated discovery receipt without relabelling history.

    A legacy v1 receipt whose ``global_path`` differs from its candidate was a
    full inventory of an existing ancestor; it stays that, never an absence.
    """
    value = _discovery_observation(receipt)
    if value["schema"] == DISCOVERY_ABSENT_OBSERVATION_SCHEMA:
        return "absent-root"
    if value.get("global_path") is not None and value.get("global_path") != value.get("global_candidate"):
        return "legacy-ancestor-inventory"
    return "existing-root"


def _discovery_observation(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping) and value.get("schema") == DISCOVERY_ABSENT_OBSERVATION_SCHEMA:
        return _absent_discovery_observation(value)
    if not isinstance(value, Mapping) or value.get("schema") != DISCOVERY_OBSERVATION_SCHEMA:
        raise ValueError("discovery observation schema is invalid")
    if "global_scope" in value:
        raise ValueError("v1 discovery observation cannot claim an absence scope")
    result = dict(value)
    if result.get("scoped_to_run") is not True:
        raise ValueError("discovery observation scope is incomplete")
    _observation_identity(result.get("run_root"), "discovery run root")
    _observation_identity(result.get("global_before"), "discovery global before")
    _observation_identity(result.get("global_after"), "discovery global after")
    if result.get("run_root_after") is not None:
        _observation_identity(result.get("run_root_after"), "discovery run root after")
    absent = result.get("global_absent", [])
    if not isinstance(absent, list) or any(not isinstance(path, str) or not path.startswith("/") for path in absent):
        raise ValueError("discovery absence assertions are malformed")
    return result


def _absent_discovery_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the v2 absent-root receipt; the run root keeps v1 checks."""
    fields = {"schema", "global_scope", "run_root", "global_before", "global_after", "scoped_to_run",
              "run_root_after", "global_path", "global_candidate", "global_absent"}
    result = dict(value)
    if set(result) != fields or result["global_scope"] != "absent-root":
        raise ValueError("absent-root discovery observation is incomplete")
    if result["scoped_to_run"] is not True:
        raise ValueError("discovery observation scope is incomplete")
    _observation_identity(result["run_root"], "discovery run root")
    _observation_identity(result["run_root_after"], "discovery run root after")
    before = _absence_record(result["global_before"], "discovery global before")
    after = _absence_record(result["global_after"], "discovery global after")
    if not (before["lexical_root"] == result["global_candidate"] == result["global_path"]):
        raise ValueError("absent-root discovery observation is not the named root")
    if result["global_absent"] != before["missing"]:
        raise ValueError("discovery absence assertions differ from the absence record")
    if before != after:
        raise ValueError("absent-root discovery observation changed during arm")
    return result


def _receipt_file_identity(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError(f"arm evidence receipt is unavailable: {path.name}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"arm evidence receipt is not a regular file: {path.name}")
    if stat.S_IMODE(info.st_mode) & 0o007:
        raise ValueError(f"arm evidence receipt is not private: {path.name}")
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": _sha256(data)}


def _replace_json(path: Path, value: Mapping[str, Any]) -> None:
    """Replace one owned receipt while preserving private mode and durability."""
    if path.resolve() != path or path.is_symlink() or not path.is_file():
        raise ValueError(f"owned receipt is unavailable: {path.name}")
    temporary = path.with_name(f".{path.name}.update")
    if temporary.exists() or temporary.is_symlink():
        raise ValueError(f"owned receipt update path is occupied: {path.name}")
    data = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(temporary.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        child = os.open(temporary.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                        dir_fd=descriptor)
        try:
            with os.fdopen(child, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            os.fsync(descriptor)
        except BaseException:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            raise
    finally:
        os.close(descriptor)


def _command_receipt(arm_dir: Path) -> dict[str, Any]:
    command_root = arm_dir / "oracle-command"
    if command_root.is_symlink():
        raise ValueError("oracle command receipt root is not physical")
    if not command_root.exists():
        return _not_applicable("oracle_command_receipt")
    if command_root.resolve() != command_root or not command_root.is_dir():
        raise ValueError("oracle command receipt root is not physical")
    names = ("command.json", "stdout", "stderr")
    if {entry.name for entry in command_root.iterdir()} != set(names):
        raise ValueError("oracle command receipt inventory is incomplete")
    identities = {name: _receipt_file_identity(command_root / name) for name in names}
    command = _load_json(command_root / "command.json")
    if not isinstance(command, Mapping) or command.get("schema") != "apg.h-oracle-command/v1":
        raise ValueError("oracle command receipt schema is invalid")
    if command.get("stdout") != identities["stdout"] or command.get("stderr") != identities["stderr"]:
        raise ValueError("oracle command receipt stream identity differs")
    if command.get("truncated") is not False or not isinstance(command.get("exit_code"), int):
        raise ValueError("oracle command receipt terminal identity is incomplete")
    return {
        "schema": "apg.h-oracle-command-receipt/v1",
        "status": "complete",
        "root": "oracle-command",
        "files": identities,
        "command": dict(command),
    }


def finalize_oracle_receipt(
    arm_dir: str | Path,
    *,
    claimed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind command-runner files into the activity and identity receipts.

    Command oracles create their retained files after the initial arm receipt
    is opened because they need its ``receipt_root``.  This close step derives
    the command identity from those files and updates the two owning receipts;
    a caller-supplied claim is accepted only when it exactly matches.
    """
    arm_dir = Path(arm_dir)
    root = arm_dir / "oracle-input"
    activity_path = root / "activity.json"
    identity_path = root / "identity.json"
    activity = _load_json(activity_path)
    if not isinstance(activity, Mapping):
        raise ValueError("execution activity receipt is malformed")
    observed = _command_receipt(arm_dir)
    if claimed is not None and dict(claimed) != observed:
        raise ValueError("oracle command claim differs from retained files")
    updated_activity = {**dict(activity), "oracle_command_receipt": observed}
    _replace_json(activity_path, updated_activity)
    identity = _load_json(identity_path)
    if not isinstance(identity, Mapping) or not isinstance(identity.get("files"), Mapping):
        raise ValueError("execution receipt identity is malformed")
    updated_identity = {**dict(identity), "files": {
        **dict(identity["files"]),
        "activity.json": _receipt_file_identity(activity_path),
    }}
    _replace_json(identity_path, updated_identity)
    identity_bytes = (json.dumps(updated_identity, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    return {"receipt": observed, "identity_sha256": _sha256(identity_bytes)}


def validate_retained_bundle(
    arm_dir: str | Path,
    result: Mapping[str, Any],
    *,
    scenario: Mapping[str, Any] | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Validate source-owned receipts and return measured facts for assembly.

    Every value returned to assembly is loaded from the fixed receipt files and
    checked against the immutable identity manifest.  The arm result may point
    at this bundle, but it cannot replace any of its facts.
    """
    from .execution import snapshot_dirs, snapshot_tree

    arm_dir = Path(arm_dir)
    if arm_dir.resolve() != arm_dir or not arm_dir.is_dir():
        raise ValueError("arm evidence directory must be physical")
    root = arm_dir / "oracle-input"
    identity = _load_json(root / "identity.json")
    if not isinstance(identity, Mapping) or identity.get("schema") != ARM_EVIDENCE_SCHEMA:
        raise ValueError("execution receipt identity is invalid")
    if identity.get("owner") != "h-execution-package":
        raise ValueError("execution receipt owner identity is absent")
    expected_scenario = scenario.get("scenario_id") if isinstance(scenario, Mapping) else result.get("scenario_id")
    if identity.get("scenario_id") != expected_scenario:
        raise ValueError("execution receipt scenario identity mismatch")
    expected_mode = mode or result.get("mode")
    if identity.get("mode") != expected_mode:
        raise ValueError("execution receipt mode identity mismatch")
    subject = arm_dir / "subject"
    subject_identity = identity.get("subject")
    if not isinstance(subject_identity, Mapping) or subject_identity.get("path") != str(subject):
        raise ValueError("execution receipt subject identity mismatch")
    names = (
        "subject-before.json", "subject-after.json", "git-before.json", "git-after.json",
        "provider-import.json", "provider-terminal.json", "context-plan.json", "transport.json",
        "source-seal.json", "route.json", "activity.json", "authority.json", "acquisition-receipts.jsonl",
        "runtime.json", "review-response.json", "provider.stdout", "provider.stderr",
    )
    files = identity.get("files")
    if not isinstance(files, Mapping) or set(files) != set(names):
        raise ValueError("execution receipt file inventory is incomplete")
    raw: dict[str, bytes] = {}
    for name in names:
        path = root / name
        data = path.read_bytes()
        observed = _receipt_file_identity(path)
        declared = files.get(name)
        if (not isinstance(declared, Mapping)
                or declared.get("bytes") != observed["bytes"]
                or declared.get("sha256") != observed["sha256"]):
            raise ValueError(f"execution receipt file identity mismatch: {name}")
        raw[name] = data

    parsed: dict[str, Any] = {}
    for name in names:
        if name.endswith(".json"):
            parsed[name] = _load_json(root / name)
    acquisitions = []
    for line in raw["acquisition-receipts.jsonl"].splitlines():
        if line.strip():
            try:
                item = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("acquisition receipt stream is malformed") from exc
            if not isinstance(item, Mapping):
                raise ValueError("acquisition receipt is not an object")
            acquisitions.append(dict(item))

    actual_subject = snapshot_tree(subject)
    actual_dirs = snapshot_dirs(subject)
    before_record = parsed["subject-before.json"]
    after_record = parsed["subject-after.json"]
    before = before_record.get("files") if isinstance(before_record, Mapping) and "files" in before_record else before_record
    after = after_record.get("files") if isinstance(after_record, Mapping) and "files" in after_record else after_record
    before_dirs = before_record.get("directories", {}) if isinstance(before_record, Mapping) else {}
    after_dirs = after_record.get("directories", {}) if isinstance(after_record, Mapping) else {}
    if (not isinstance(before, Mapping) or not isinstance(after, Mapping)
            or not isinstance(before_dirs, Mapping) or not isinstance(after_dirs, Mapping)
            or dict(after) != actual_subject or dict(after_dirs) != actual_dirs):
        raise ValueError("subject receipt does not bind the retained subject")
    if (result.get("subject_before") != dict(before)
            or result.get("subject_directories_before", {}) != dict(before_dirs)):
        raise ValueError("arm result before authority differs from retained subject receipt")
    provider_import = parsed["provider-import.json"]
    provider_terminal = parsed["provider-terminal.json"]
    route = parsed["route.json"]
    context = parsed["context-plan.json"]
    transport = parsed["transport.json"]
    source_seal = parsed["source-seal.json"]
    activity = parsed["activity.json"]
    authority = parsed["authority.json"]
    runtime = parsed["runtime.json"]
    review = parsed["review-response.json"]
    for name, value in (("provider import", provider_import), ("provider terminal", provider_terminal),
                        ("route", route), ("context plan", context), ("transport", transport),
                        ("source seal", source_seal), ("activity", activity), ("authority", authority),
                        ("runtime", runtime), ("review response", review)):
        if not isinstance(value, Mapping):
            raise ValueError(f"{name} receipt is malformed")
    if (authority.get("schema") != AUTHORITY_SCHEMA
            or authority.get("before") != dict(before)
            or authority.get("after") != dict(after)
            or authority.get("before_directories") != dict(before_dirs)
            or authority.get("after_directories") != dict(after_dirs)
            or not isinstance(authority.get("permitted"), bool)
            or not isinstance(authority.get("read_only"), bool)
            or authority.get("replay_authorized") is not False):
        raise ValueError("authority receipt does not bind retained subject evidence")
    if result.get("authority") != dict(authority):
        raise ValueError("arm result authority differs from retained authority receipt")
    if provider_import.get("schema") != "apg.h-provider-import/v1":
        raise ValueError("provider import receipt schema is invalid")
    stdout_identity = {"bytes": len(raw["provider.stdout"]), "sha256": _sha256(raw["provider.stdout"])}
    stderr_identity = {"bytes": len(raw["provider.stderr"]), "sha256": _sha256(raw["provider.stderr"])}
    if provider_import.get("raw") != stdout_identity:
        raise ValueError("provider import does not bind retained stdout")
    if provider_terminal.get("stdout") != stdout_identity or provider_terminal.get("stderr") != stderr_identity:
        raise ValueError("provider terminal does not bind retained streams")
    if not isinstance(provider_terminal.get("exit_code"), int):
        raise ValueError("provider terminal exit identity is absent")
    if (transport.get("coverage") != "complete"
            or not isinstance(transport.get("events"), list)
            or any(not isinstance(event, Mapping) for event in transport["events"])):
        raise ValueError("delivery receipt is incomplete")
    if context.get("schema") not in {"apg.h-context-plan/v1", "apg.context-plan/v1", "apg.invocation-context/v1"}:
        raise ValueError("context plan receipt schema is invalid")
    plan_reference = transport.get("plan")
    if (not isinstance(plan_reference, Mapping)
            or plan_reference.get("bytes") != len(raw["context-plan.json"])
            or plan_reference.get("sha256") != _sha256(raw["context-plan.json"])):
        raise ValueError("transport plan does not bind exact retained context bytes")
    transport_events = list(transport["events"])
    if any(not isinstance(row.get("event"), Mapping) for row in acquisitions):
        raise ValueError("retained acquisition event is malformed")
    transport_events.extend(
        row["event"] for row in acquisitions
        if isinstance(row.get("event"), Mapping)
    )
    if source_seal.get("schema") not in {"apg.h-readiness-seal/v1", "apg.h-source-seal/v1", "apg.h-not-applicable/v1"}:
        raise ValueError("source seal receipt schema is invalid")
    if runtime.get("schema") not in {"apg.h-runtime-inputs/v2", "apg.h-runtime-observation/v1", "apg.h-not-applicable/v1"}:
        raise ValueError("runtime receipt schema is invalid")
    bound_source = activity.get("source_binding")
    if isinstance(scenario, Mapping) and isinstance(scenario.get("routes"), Mapping):
        expected_route = scenario["routes"].get(expected_mode)
        if not isinstance(expected_route, Mapping) or not isinstance(bound_source, Mapping):
            raise ValueError("source binding is not retained")
        expected_route_sha = _sha256(
            (json.dumps(dict(expected_route), sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
        )
        if (bound_source.get("scenario_id") != expected_scenario
                or bound_source.get("mode") != expected_mode
                or bound_source.get("scenario_path") != scenario.get("scenario_path")
                or bound_source.get("scenario_sha256") != scenario.get("scenario_sha256")
                or bound_source.get("route_sha256") != expected_route_sha
                or bound_source.get("source_sha256") != expected_route.get("source_sha256")
                or bound_source.get("identity_sources") != expected_route.get("identity_sources")
                or bound_source.get("bindings_path") != "testing/h_eval/scenario-bindings.json"):
            raise ValueError("source binding digest identity differs from preregistration")
    for key in ("attempts", "retries", "restarts", "provider_invocations", "revision_observation", "restart_observation"):
        if key not in activity:
            raise ValueError(f"activity receipt lacks {key}")
    _validate_observation_state(activity["revision_observation"], field="producer_revisions")
    _validate_observation_state(activity["restart_observation"], field="restart_required_incidents")
    for key in ("instruction_delivery", "settings_receipt", "discovery_receipt",
                "settings_identity", "discovery_identity", "native_reads",
                "recovery_receipt", "oracle_command_receipt"):
        if key not in activity:
            raise ValueError(f"activity receipt lacks {key}")
    native_activity = activity["native_reads"]
    if not isinstance(native_activity, Mapping):
        raise ValueError("native Read observation is malformed")
    if native_activity.get("schema") == "apg.claude-native-reads/v1":
        if (native_activity.get("coverage") != "complete"
                or not isinstance(native_activity.get("raw_stream"), Mapping)
                or not isinstance(native_activity.get("scope"), Mapping)
                or set(native_activity["scope"]) != {"run_id", "binding_id", "attempt_id"}
                or any(not isinstance(value, str) or not value for value in native_activity["scope"].values())
                or not isinstance(native_activity.get("session_id"), str)
                or not native_activity.get("session_id")
                or not isinstance(native_activity.get("reads"), list)
                or not isinstance(native_activity.get("events"), list)
                or any(not isinstance(read, Mapping) for read in native_activity["reads"])
                or any(not isinstance(event, Mapping) for event in native_activity["events"])
                or not isinstance(native_activity.get("terminal"), Mapping)):
            raise ValueError("native Read observation is incomplete")
        if native_activity["raw_stream"] != stdout_identity:
            raise ValueError("native Read stream does not bind retained provider stdout")
        terminal_session = native_activity["terminal"].get("session_id")
        if (terminal_session is not None
                and terminal_session != native_activity.get("session_id")):
            raise ValueError("native Read terminal session differs from retained session")
    elif native_activity.get("schema") != NOT_APPLICABLE_SCHEMA:
        raise ValueError("native Read observation schema is invalid")
    if native_activity.get("schema") == "apg.claude-native-reads/v1":
        transport_events.extend(
            event for event in native_activity["events"]
            if isinstance(event, Mapping)
        )
    try:
        observed_delivery = delivery_entries(
            transport_events,
            run_id=context["run_id"],
            binding_id=context["binding_id"],
            attempt_id=context["attempt_id"],
        )
        if observed_delivery.get("coverage") != "complete":
            raise ValueError("retained delivery events are incomplete")
        from .evaluate import delivered_totals
        observed_deliveries = observed_delivery["deliveries"]
        observed_initial, observed_cumulative = delivered_totals(observed_deliveries)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("retained delivery evidence cannot be derived") from error
    if (result.get("deliveries") != observed_deliveries
            or result.get("initial") != observed_initial
            or result.get("cumulative") != observed_cumulative
            or result.get("coverage") != transport.get("coverage")):
        raise ValueError("arm result delivery claims differ from retained events")
    settings_receipt = activity["settings_receipt"]
    discovery_receipt = activity["discovery_receipt"]
    if settings_receipt.get("schema") == SETTINGS_OBSERVATION_SCHEMA:
        _typed_observation(settings_receipt, schema=SETTINGS_OBSERVATION_SCHEMA, kind="settings")
    elif settings_receipt.get("schema") != NOT_APPLICABLE_SCHEMA:
        raise ValueError("settings observation receipt schema is invalid")
    if discovery_receipt.get("schema") in DISCOVERY_OBSERVATION_SCHEMAS:
        _discovery_observation(discovery_receipt)
    elif discovery_receipt.get("schema") != NOT_APPLICABLE_SCHEMA:
        raise ValueError("discovery observation receipt schema is invalid")
    if activity["settings_identity"] != settings_receipt or activity["discovery_identity"] != discovery_receipt:
        raise ValueError("historical observation aliases differ from typed receipts")
    recovery = activity["recovery_receipt"]
    if not isinstance(recovery, Mapping):
        raise ValueError("recovery receipt is malformed")
    if recovery.get("schema") not in {
        RECOVERY_RECEIPT_SCHEMA, RECOVERY_QUALIFICATION_SCHEMA, NOT_APPLICABLE_SCHEMA,
    }:
        raise ValueError("recovery receipt schema is invalid")
    if (recovery.get("schema") in {RECOVERY_RECEIPT_SCHEMA, RECOVERY_QUALIFICATION_SCHEMA}
            and recovery.get("status") not in {"complete", "incomplete", "rejected"}):
        raise ValueError("recovery receipt status is invalid")
    if recovery.get("schema") == RECOVERY_QUALIFICATION_SCHEMA and (
            recovery.get("status") != "complete"
            or recovery.get("provider_free") is not True
            or recovery.get("provider_invocations") != 0
            or recovery.get("model_invocations") != 0
            or not isinstance(recovery.get("prelaunch_authority"), Mapping)
            or not isinstance(recovery.get("postrun_readback"), Mapping)
            or recovery["postrun_readback"].get("status") != "valid"
            or recovery.get("subtree", {}).get("unchanged") is not True
            or recovery.get("stream_readback", {}).get("status") != "valid"
            or not isinstance(recovery.get("stream_custody"), list)):
            raise ValueError("provider-free recovery qualification is incomplete")
    if recovery.get("schema") == RECOVERY_RECEIPT_SCHEMA:
        native = recovery.get("native_reads")
        if recovery.get("status") == "complete" and (
                not isinstance(native, Mapping)
                or native.get("schema") != "apg.claude-native-reads/v1"
                or native.get("coverage") != "complete"
                or not isinstance(native.get("raw_stream"), Mapping)
                or not isinstance(native.get("scope"), Mapping)
                or not isinstance(native.get("session_id"), str)
                or not native.get("session_id")
                or not isinstance(native.get("reads"), list)
                or not isinstance(native.get("events"), list)
                or not isinstance(native.get("terminal"), Mapping)
                or type(native.get("read_count")) is not int):
            raise ValueError("native recovery receipt is incomplete")
    command_receipt = activity["oracle_command_receipt"]
    observed_command = _command_receipt(arm_dir)
    if command_receipt != observed_command:
        raise ValueError("oracle command receipt is not retained from its files")
    task_oracle = _load_json(arm_dir / "task-oracle.json")
    if result.get("task_oracle") != task_oracle:
        raise ValueError("arm task oracle is not retained from its file")
    if (result.get("provider_import") != provider_import
            or result.get("provider_terminal") != provider_terminal
            or result.get("route") != route
            or result.get("provider_invocations") != activity.get("provider_invocations")
            or result.get("retries", 0) != activity.get("retries")
            or result.get("restarts", 0) != activity.get("restarts")):
        raise ValueError("arm result claims differ from retained execution receipts")
    if ("revalidation" in runtime
            and result.get("runtime_revalidation") != runtime.get("revalidation")):
        raise ValueError("arm runtime revalidation is not retained from its receipt")
    scenario_id = expected_scenario
    acquisition_required = scenario_id in {"scenario-10", "scenario-11", "scenario-14"}
    if acquisition_required and not acquisitions:
        raise ValueError("required acquisition receipt is absent")
    if scenario_id == "scenario-12" and (
            recovery.get("schema") == NOT_APPLICABLE_SCHEMA
            or recovery.get("status") != "complete"):
        raise ValueError("Scenario 12 recovery receipt is incomplete")
    if activity.get("attempts") != ["one"] or activity.get("retries") != 0 or activity.get("restarts") != 0:
        raise ValueError("arm retry/restart evidence is not single-use")
    owner = result.get("evidence_owner")
    identity_bytes = (json.dumps(identity, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    if not isinstance(owner, Mapping) or owner.get("path") != "oracle-input/identity.json" or owner.get("sha256") != _sha256(identity_bytes):
        raise ValueError("arm result does not bind execution-owned evidence")
    for key in ("native_reads", "recovery_receipt", "settings_receipt",
                "discovery_receipt", "settings_identity", "discovery_identity",
                "oracle_command_receipt"):
        if result.get(key) is not None and result.get(key) != activity.get(key):
            raise ValueError(f"arm result {key} differs from activity receipt")
    admission_path = arm_dir / "admission.json"
    admission_record = _load_json(admission_path) if admission_path.is_file() and not admission_path.is_symlink() else {}
    eligibility = qualification_eligibility({
        "live_admission": admission_record.get("live_admission") if isinstance(admission_record, Mapping) else None,
        "identity": identity,
        "source_binding": activity.get("source_binding"),
        "subject_factory": activity.get("subject_factory"),
        "oracle_owner": activity.get("oracle_owner"),
        "task_contract": activity.get("task_contract"),
        "source_seal": source_seal,
        "runtime": runtime,
        "route": route,
        "result": result,
    })
    bound_scenario = scenario or {
        "scenario_id": expected_scenario,
        "cohorts": identity.get("cohorts", {}),
    }
    exact_recovery, exact_recovery_evidence = derive_exact_recovery(
        bound_scenario, result=result,
        receipt={
            "route": route, "activity": activity, "context": context,
            "authority": authority, "provider_terminal": provider_terminal,
            "acquisitions": acquisitions,
        },
    )
    return {
        "identity": dict(identity),
        "before": dict(before),
        "after": dict(after),
        "before_dirs": dict(before_dirs),
        "after_dirs": dict(after_dirs),
        "provider_import": dict(provider_import),
        "provider_terminal": dict(provider_terminal),
        "route": dict(route),
        "context": dict(context),
        "transport": dict(transport),
        "source_seal": dict(source_seal),
        "activity": dict(activity),
        "authority": dict(authority),
        "runtime": dict(runtime),
        "review": dict(review),
        "instruction_delivery": deepcopy(activity["instruction_delivery"]),
        "settings_receipt": deepcopy(activity["settings_receipt"]),
        "discovery_receipt": deepcopy(activity["discovery_receipt"]),
        "settings_identity": deepcopy(activity["settings_identity"]),
        "discovery_identity": deepcopy(activity["discovery_identity"]),
        "native_reads": deepcopy(activity["native_reads"]),
        "recovery_receipt": deepcopy(activity["recovery_receipt"]),
        "oracle_command_receipt": deepcopy(activity["oracle_command_receipt"]),
        "acquisitions": acquisitions,
        "qualification_eligibility": eligibility,
        "live_admission": deepcopy(admission_record.get("live_admission")) if isinstance(admission_record, Mapping) else None,
        "exact_recovery": exact_recovery,
        "exact_recovery_evidence": exact_recovery_evidence,
        "stream_identities": {"stdout": stdout_identity, "stderr": stderr_identity},
    }


def retain(
    arm_dir,
    scenario,
    prepared,
    result,
    *,
    source_root,
    source_seal,
    runtime,
    source_binding: Mapping[str, Any] | None = None,
    subject_factory: Mapping[str, Any] | None = None,
    oracle_owner: Mapping[str, Any] | None = None,
    task_contract_value: Mapping[str, Any] | None = None,
    runtime_revalidation: Mapping[str, Any] | None = None,
    recovery_receipt: Mapping[str, Any] | None = None,
):
    """Copy facts observed by run_one_arm into a fixed immutable oracle input."""
    from .execution import _write_bytes, _write_json, snapshot_dirs, snapshot_tree
    from .readiness import make_seal
    arm_dir = Path(arm_dir)
    run, subject, destination = arm_dir / "run", arm_dir / "subject", arm_dir / "oracle-input"
    destination.mkdir(mode=0o700)
    diagnostics = []
    acquisitions = records(run, result["mode"], diagnostics=diagnostics)
    if diagnostics:
        raise ValueError("acquisition receipt custody incomplete")
    _write_bytes(destination / "acquisition-receipts.jsonl", b"".join(
        json.dumps(item, sort_keys=True).encode() + b"\n" for item in acquisitions))
    for name in ("provider.stdout", "provider.stderr"):
        _write_bytes(destination / name, (run / name).read_bytes())
    imported = result["provider_import"]
    bound_source = deepcopy(dict(source_binding or {
        "schema": SOURCE_BINDING_SCHEMA,
        "owner": "h-execution-package",
        "status": "legacy-direct-arm",
    }))
    bound_subject = deepcopy(dict(subject_factory or {
        "schema": SUBJECT_FACTORY_SCHEMA,
        "owner": "caller-supplied-instrumented-fixture",
        "status": "test-only",
    }))
    bound_oracle = deepcopy(dict(oracle_owner or {
        "schema": ORACLE_OWNER_SCHEMA,
        "owner": "caller-supplied-instrumented-fixture",
        "status": "test-only",
    }))
    bound_contract = deepcopy(dict(task_contract_value or task_contract(scenario, source_binding=bound_source)))
    bound_source_seal = deepcopy(dict(source_seal or make_seal(source_root)))
    if source_binding is not None:
        bound_source_seal["source_binding"] = bound_source
    bound_runtime = deepcopy(dict(runtime or {
        "schema": "apg.h-runtime-observation/v1",
        "status": "unavailable",
        "test_only": True,
    }))
    if runtime_revalidation is not None:
        bound_runtime["revalidation"] = deepcopy(dict(runtime_revalidation))
    bound_recovery = _optional_receipt(
        recovery_receipt if recovery_receipt is not None else result.get("recovery_receipt"),
        schema=RECOVERY_RECEIPT_SCHEMA,
        kind="recovery",
    )
    context_record = prepared["record"]
    context_path = prepared.get("path")
    if not isinstance(context_path, Path):
        context_path = Path(context_path) if isinstance(context_path, str) else None
    if (context_path is None or context_path.resolve() != context_path
            or context_path.is_symlink() or not context_path.is_file()):
        raise ValueError("native context plan path is not retained")
    context_raw = context_path.read_bytes()
    reference = prepared.get("reference")
    if (not isinstance(reference, Mapping)
            or reference.get("bytes") != len(context_raw)
            or reference.get("sha256") != _sha256(context_raw)):
        raise ValueError("native context plan bytes differ from its reference")
    instruction_delivery = context_record.get("instruction_delivery")
    if instruction_delivery is None:
        instruction_delivery = context_record.get("instruction_plan")
    if instruction_delivery is None:
        instruction_delivery = _not_applicable("instruction_delivery")
    settings_receipt = result.get("settings_receipt")
    if settings_receipt is None:
        settings_receipt = _not_applicable("settings_receipt")
    elif isinstance(settings_receipt, Mapping) and settings_receipt.get("schema") == SETTINGS_OBSERVATION_SCHEMA:
        settings_receipt = _typed_observation(
            settings_receipt, schema=SETTINGS_OBSERVATION_SCHEMA, kind="settings",
        )
    else:
        settings_receipt = _not_applicable("settings_receipt")
    discovery_receipt = result.get("discovery_receipt")
    if discovery_receipt is None:
        discovery_receipt = _not_applicable("discovery_receipt")
    elif isinstance(discovery_receipt, Mapping) and discovery_receipt.get("schema") in DISCOVERY_OBSERVATION_SCHEMAS:
        discovery_receipt = _discovery_observation(discovery_receipt)
    else:
        discovery_receipt = _not_applicable("discovery_receipt")
    # Keep historical names as exact aliases, never as an independently
    # caller-supplied claim.
    settings_identity = deepcopy(settings_receipt)
    discovery_identity = deepcopy(discovery_receipt)
    native_reads = result.get("native_reads")
    if native_reads is None:
        native_reads = _not_applicable("native_reads")
    oracle_command = result.get("oracle_command_receipt")
    if oracle_command is None:
        oracle_command = _not_applicable("oracle_command_receipt")
    for value, kind in (
        (instruction_delivery, "instruction delivery"),
        (settings_receipt, "settings receipt"),
        (discovery_receipt, "discovery receipt"),
        (native_reads, "native reads"),
        (oracle_command, "oracle command"),
    ):
        if not isinstance(value, Mapping):
            raise ValueError(f"{kind} receipt is malformed")
    activity = {
        "schema": "apg.h-execution-activity/v1",
        "attempts": ["one"],
        "retries": result.get("retries", 0),
        "restarts": result.get("restarts", 0),
        "provider_invocations": result["provider_invocations"],
        "revision_observation": observation_state(
            imported.get("producer_revisions"), field="producer_revisions",
        ),
        "restart_observation": observation_state(
            imported.get("restart_required_incidents"), field="restart_required_incidents",
        ),
        "missing_guidance_observation": imported.get("missing_guidance_findings"),
        "permitted": result["authority"]["permitted"],
        "source_binding": bound_source,
        "subject_factory": bound_subject,
        "oracle_owner": bound_oracle,
        "task_contract": bound_contract,
        "instruction_delivery": deepcopy(dict(instruction_delivery)),
        "settings_receipt": deepcopy(dict(settings_receipt)),
        "discovery_receipt": deepcopy(dict(discovery_receipt)),
        "settings_identity": deepcopy(dict(settings_identity)),
        "discovery_identity": deepcopy(dict(discovery_identity)),
        "native_reads": deepcopy(dict(native_reads)),
        "recovery_receipt": bound_recovery,
        "oracle_command_receipt": deepcopy(dict(oracle_command)),
    }
    authority_record = {
        "schema": AUTHORITY_SCHEMA,
        "read_only": result["authority"]["read_only"],
        "permitted": result["authority"]["permitted"],
        "unchanged": result["authority"]["unchanged"],
        "changed_paths": list(result["authority"].get("changed_paths", [])),
        "changed_directories": list(result["authority"].get("changed_directories", [])),
        "directories_unchanged": result["authority"].get("directories_unchanged"),
        "git_unchanged": result["authority"].get("git_unchanged"),
        "before": result["subject_before"],
        "after": snapshot_tree(subject),
        "before_directories": result.get("subject_directories_before", {}),
        "after_directories": snapshot_dirs(subject),
        "git_before": result["git_authority_before"],
        "git_after": result["authority"].get("git_after"),
        "replay_authorized": result.get("replay_authorized", False),
    }
    result["authority"] = authority_record
    receipt_values = {
        "subject-before.json": {
            "files": result["subject_before"],
            "directories": result.get("subject_directories_before", {}),
        },
        "subject-after.json": {
            "files": snapshot_tree(subject),
            "directories": snapshot_dirs(subject),
        },
        "git-before.json": result["git_authority_before"],
        "git-after.json": result["authority"]["git_after"],
        "provider-import.json": imported,
        "provider-terminal.json": result["provider_terminal"],
        # Preserve the exact bytes written by context_adapter.  Re-encoding
        # the parsed record changes whitespace and can invalidate the native
        # transport reference digest.
        "context-plan.json": None,
        "transport.json": json.loads((run / "attempt.context-deliveries.json").read_bytes()),
        "source-seal.json": bound_source_seal,
        "route.json": result["route"],
        "activity.json": activity,
        "authority.json": authority_record,
        "runtime.json": bound_runtime,
        "review-response.json": imported.get("review_response") or {"schema": "apg.h-not-applicable/v1"},
    }
    for name, value in receipt_values.items():
        if name == "context-plan.json":
            _write_bytes(destination / name, context_raw)
        else:
            _write_json(destination / name, value)
    files = snapshot_tree(destination)
    _write_json(destination / "identity.json", {
        "schema": ARM_EVIDENCE_SCHEMA, "owner": "h-execution-package",
        "scenario_id": scenario["scenario_id"], "mode": result["mode"],
        "cohorts": deepcopy(dict(result.get("source_cohorts", scenario.get("cohorts", {})))),
        "subject": {"path": str(subject)}, "files": files,
        "source_binding": bound_source,
        "subject_factory": bound_subject,
        "task_contract": bound_contract,
        "oracle_owner": bound_oracle,
    })
    _write_json(arm_dir / "task-contract.json", {
        "scenario": scenario,
        "prompt_sha256": _sha256(task_prompt(scenario)),
        "response_contract": contract_identity(scenario),
        "contract": bound_contract,
    })
    return destination


__all__ = [
    "REVIEW_SCENARIOS",
    "AUTHORITY_SCHEMA",
    "EXACT_RECOVERY_SCHEMA",
    "QUALIFICATION_ELIGIBILITY_SCHEMA",
    "contract_identity",
    "derive_exact_recovery",
    "finalize_oracle_receipt",
    "observation_state",
    "qualification_eligibility",
    "response_bytes",
    "retain",
    "task_contract",
    "task_prompt",
    "validate_retained_bundle",
]
