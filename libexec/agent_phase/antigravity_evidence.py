"""Closed validation for dispatcher-owned Antigravity terminal evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any


SCHEMA = "antigravity-terminal-evidence-v3"
COMPATIBLE_SCHEMAS = {
    "antigravity-terminal-evidence-v2": 2,
    SCHEMA: 3,
    "antigravity-terminal-evidence-v4": 4,
    "antigravity-terminal-evidence-v5": 5,
    "antigravity-terminal-evidence-v6": 6,
}
SUMMARY_SUFFIX = "antigravity-terminal-result.json"
RAW_SUFFIX = "antigravity-terminal-result.raw.json"
MAX_SUMMARY_BYTES = 1024 * 1024
MAX_RAW_BYTES = 16 * 1024 * 1024
MAX_FIELD_BYTES = 4 * 1024
REASON_KEYS = {
    "error", "message", "reason", "cancel_reason", "cancellation_reason",
    "finish_reason", "termination_reason", "code", "error_code",
}
IDENTIFIER_KEYS = {
    "conversation_id", "request_id", "session_id", "operation_id", "run_id",
    "turn_id",
}
RECORD_KINDS = {
    "no_terminal_event", "exact_raw_event", "oversized_digest_only",
    "malformed_event",
}
FIELD_SOURCE_PATTERN = re.compile(
    r"^(?:result|event)(?:\.error)?\."
    r"(?:error|message|reason|cancel_reason|cancellation_reason|finish_reason|"
    r"termination_reason|code|error_code|conversation_id|request_id|session_id|"
    r"operation_id|run_id|turn_id)$"
)
STATUS_SOURCES = {"result.status", "event.status", "result.subtype", "event.subtype"}
RESPONSE_SOURCES = {
    "result.response", "event.response", "result.result", "event.result",
    "result.text", "event.text", "result.content", "event.content",
}
ERROR_SOURCES = {
    "result.error", "event.error", "result.message", "event.message",
    "result.error.message", "event.error.message", "result.error.reason",
    "event.error.reason", "result.error.code", "event.error.code",
    "result.error.error_code", "event.error.error_code",
}
LEASE_FAILURE_CLASSES = {
    "lease_holder_unavailable", "lease_acquisition_timeout", "lease_contention",
    "lease_handshake_invalid", "lease_control_pipe_invalid",
    "lease_holder_exited", "lease_protocol_violation", "lease_release_failed",
}
LEASE_FIELDS = {
    "contract", "acquired", "acquisition_duration_seconds", "failure_class",
    "holder_exit_code", "control_channel_closed", "holder_reaped",
    "agy_launched_after_acquisition",
}
LEASE_CONTRACT = "agent-security-antigravity-launch-lease-v1"
V2_LEASE_FIELDS = {
    "contract",
    "acquisition_validated",
    "registration_validated",
    "gate_released",
    "provider_group_quiescent",
    "control_channel_closed",
    "holder_reaped",
    "holder_exit_class",
    "failure_phase",
    "failure_class",
}
V2_LEASE_CONTRACT = "agent-security-antigravity-launch-lease-v2"
LEASE_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
CLEANUP_SCHEMA = "antigravity-process-group-cleanup-v1"
CLEANUP_STATUSES = {
    "sent", "absent", "permission_denied", "error", "not_attempted",
}
CLEANUP_STATES = {"absent", "present", "unknown", "permission_denied", "error"}
CLEANUP_FAILURE_CLASSES = {
    "cleanup_not_attested",
    "group_identity_unverified",
    "term_permission_denied",
    "term_error",
    "kill_permission_denied",
    "kill_error",
    "group_remaining",
    "group_state_unknown",
    "parent_not_reaped",
    "reader_join_timeout",
    "cleanup_exception",
    "version_probe_thread_not_joined",
    "version_probe_exception",
}
CLEANUP_FIELDS = {
    "schema", "reason", "attempted", "term_status", "kill_status",
    "group_absent", "group_state", "parent_reaped",
    "stdout_reader_joined", "stderr_reader_joined", "readers_joined",
    "cleanup_complete", "failure_class",
}
CLEANUP_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")


class EvidenceError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_private_regular(path: Path, root: Path, maximum: int) -> bytes:
    try:
        if path.parent.resolve() != root.resolve():
            raise EvidenceError(f"evidence path escapes run directory: {path.name}")
        info = os.lstat(path)
    except OSError as error:
        raise EvidenceError(f"missing evidence artifact {path.name}: {error}") from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise EvidenceError(f"evidence artifact is not a regular file: {path.name}")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise EvidenceError(f"evidence artifact is not mode 0600: {path.name}")
    if info.st_size > maximum:
        raise EvidenceError(f"evidence artifact exceeds bound: {path.name}")
    data = path.read_bytes()
    if len(data) != info.st_size:
        raise EvidenceError(f"evidence artifact size changed while reading: {path.name}")
    return data


def _validate_text_evidence(value: Any, label: str) -> None:
    required = {"text", "utf8_bytes", "sha256", "truncated", "source"}
    if not isinstance(value, dict) or set(value) != required:
        raise EvidenceError(f"invalid bounded field schema: {label}")
    text = value["text"]
    count = value["utf8_bytes"]
    digest = value["sha256"]
    truncated = value["truncated"]
    source = value["source"]
    if (
        not isinstance(text, str)
        or type(count) is not int
        or count < 0
        or not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        or type(truncated) is not bool
        or (source is not None and not isinstance(source, str))
        or (isinstance(source, str) and FIELD_SOURCE_PATTERN.fullmatch(source) is None)
    ):
        raise EvidenceError(f"invalid bounded field values: {label}")
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_FIELD_BYTES or count < len(encoded):
        raise EvidenceError(f"bounded field exceeds limits: {label}")
    if truncated:
        if count <= len(encoded):
            raise EvidenceError(f"bounded field truncation mismatch: {label}")
    elif count != len(encoded) or digest != _sha256(encoded):
        raise EvidenceError(f"bounded field digest mismatch: {label}")


def _validate_legacy_v1_lease(
    lease_summary: Any, summary: dict[str, Any], wrapper_exit_code: int,
    name: str,
) -> None:
    """Validate the V1 lease shape retained by version-4 evidence only."""
    if not isinstance(lease_summary, dict) or set(lease_summary) != LEASE_FIELDS:
        raise EvidenceError(f"invalid provider launch lease schema in {name}")
    duration = lease_summary.get("acquisition_duration_seconds")
    holder_exit = lease_summary.get("holder_exit_code")
    failure_class = lease_summary.get("failure_class")
    acquired = lease_summary.get("acquired")
    control_closed = lease_summary.get("control_channel_closed")
    holder_reaped = lease_summary.get("holder_reaped")
    launched = lease_summary.get("agy_launched_after_acquisition")
    if (
        lease_summary.get("contract") != LEASE_CONTRACT
        or type(acquired) is not bool
        or not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or duration < 0
        or (holder_exit is not None and type(holder_exit) is not int)
        or (failure_class is not None and failure_class not in LEASE_FAILURE_CLASSES)
        or type(control_closed) is not bool
        or type(holder_reaped) is not bool
        or type(launched) is not bool
        or (launched and not acquired)
        or (summary.get("child_started") is True and not launched)
        or (holder_reaped and holder_exit is None)
    ):
        raise EvidenceError(f"invalid provider launch lease values in {name}")
    if (
        acquired
        and failure_class is None
        and (not control_closed or not holder_reaped)
    ):
        raise EvidenceError(f"incomplete provider launch lease cleanup in {name}")
    if wrapper_exit_code == 0 and (
        failure_class is not None
        or not acquired
        or not launched
        or holder_exit != 0
    ):
        raise EvidenceError(f"wrapper success lacks completed launch lease in {name}")


def _validate_lease_token(value: Any, label: str) -> None:
    if value is None:
        return
    if not isinstance(value, str) or LEASE_TOKEN_PATTERN.fullmatch(value) is None:
        raise EvidenceError(f"invalid bounded launch-lease class: {label}")
    try:
        encoded_length = len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise EvidenceError(f"invalid bounded launch-lease class: {label}") from error
    if encoded_length > 128:
        raise EvidenceError(f"invalid bounded launch-lease class: {label}")


def _validated_protocol_error(value: Any, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise EvidenceError(f"invalid bounded protocol error in {name}")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise EvidenceError(f"invalid bounded protocol error in {name}") from error
    if len(encoded) > 1024 or any(ord(char) < 0x20 and char not in "\t\r\n" for char in value):
        raise EvidenceError(f"invalid bounded protocol error in {name}")
    return value


def _validate_v2_lease(
    lease_summary: Any, summary: dict[str, Any], wrapper_exit_code: int,
    name: str,
) -> None:
    """Validate the V2 lifecycle shape emitted by current terminal evidence."""
    if not isinstance(lease_summary, dict) or set(lease_summary) != V2_LEASE_FIELDS:
        raise EvidenceError(f"invalid provider launch lease schema in {name}")
    if lease_summary.get("contract") != V2_LEASE_CONTRACT:
        raise EvidenceError(f"invalid provider launch lease contract in {name}")

    boolean_fields = (
        "acquisition_validated",
        "registration_validated",
        "gate_released",
        "provider_group_quiescent",
        "control_channel_closed",
        "holder_reaped",
    )
    if any(type(lease_summary.get(field)) is not bool for field in boolean_fields):
        raise EvidenceError(f"invalid provider launch lease values in {name}")

    for field in ("holder_exit_class", "failure_phase", "failure_class"):
        _validate_lease_token(lease_summary.get(field), field)

    acquired = lease_summary["acquisition_validated"]
    registered = lease_summary["registration_validated"]
    gate_released = lease_summary["gate_released"]
    holder_reaped = lease_summary["holder_reaped"]
    failure_phase = lease_summary["failure_phase"]
    failure_class = lease_summary["failure_class"]
    if registered and not acquired:
        raise EvidenceError(f"provider registration lacks validated acquisition in {name}")
    if gate_released and not registered:
        raise EvidenceError(f"provider gate released without validated registration in {name}")
    if summary.get("child_started") is True and not (acquired and registered and gate_released):
        raise EvidenceError(f"provider launch lacks completed gate lifecycle in {name}")
    if holder_reaped and lease_summary["holder_exit_class"] is None:
        raise EvidenceError(f"reaped holder lacks bounded exit class in {name}")
    if wrapper_exit_code == 0 and (
        not all(lease_summary[field] for field in boolean_fields)
        or lease_summary["holder_exit_class"] != "clean"
        or failure_phase is not None
        or failure_class is not None
    ):
        raise EvidenceError(f"wrapper success lacks completed V2 launch lease in {name}")


def _validate_cleanup_record(
    value: Any,
    name: str,
    wrapper_exit_code: int,
    *,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != CLEANUP_FIELDS:
        raise EvidenceError(f"invalid {label} cleanup schema in {name}")
    reason = value.get("reason")
    if (
        not isinstance(reason, str)
        or not reason
        or CLEANUP_TOKEN_PATTERN.fullmatch(reason) is None
    ):
        raise EvidenceError(f"invalid {label} cleanup reason in {name}")
    if any(
        type(value.get(field)) is not bool
        for field in (
            "attempted",
            "group_absent",
            "parent_reaped",
            "stdout_reader_joined",
            "stderr_reader_joined",
            "readers_joined",
            "cleanup_complete",
        )
    ):
        raise EvidenceError(f"invalid {label} cleanup booleans in {name}")
    if value.get("schema") != CLEANUP_SCHEMA:
        raise EvidenceError(f"invalid {label} cleanup contract in {name}")
    if (
        value.get("term_status") not in CLEANUP_STATUSES
        or value.get("kill_status") not in CLEANUP_STATUSES
        or value.get("group_state") not in CLEANUP_STATES
    ):
        raise EvidenceError(f"invalid {label} cleanup status in {name}")
    failure_class = value.get("failure_class")
    if failure_class is not None:
        if (
            not isinstance(failure_class, str)
            or CLEANUP_TOKEN_PATTERN.fullmatch(failure_class) is None
            or failure_class not in CLEANUP_FAILURE_CLASSES
        ):
            raise EvidenceError(f"invalid {label} cleanup failure class in {name}")
    if value["group_absent"] != (value["group_state"] == "absent"):
        raise EvidenceError(f"{label} cleanup absence mismatch in {name}")
    if value["readers_joined"] != (
        value["stdout_reader_joined"] and value["stderr_reader_joined"]
    ):
        raise EvidenceError(f"{label} cleanup reader mismatch in {name}")
    if value["cleanup_complete"] and (
        not value["group_absent"]
        or not value["parent_reaped"]
        or not value["readers_joined"]
        or failure_class is not None
    ):
        raise EvidenceError(f"incomplete {label} cleanup marked complete in {name}")
    if not value["cleanup_complete"] and failure_class is None:
        raise EvidenceError(f"unclassified {label} cleanup failure in {name}")
    if wrapper_exit_code == 0 and not value["cleanup_complete"]:
        raise EvidenceError(f"wrapper success lacks completed {label} cleanup in {name}")
    return value


def validate(
    run_directory: Path,
    prefix: str,
    profile: str,
    model: str,
    reviewer: bool,
    wrapper_exit_code: int,
) -> dict[str, Any]:
    summary_path = run_directory / f"{prefix}.{SUMMARY_SUFFIX}"
    summary_bytes = _read_private_regular(
        summary_path, run_directory, MAX_SUMMARY_BYTES
    )
    try:
        summary = json.loads(summary_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceError(f"malformed evidence summary {summary_path.name}: {error}") from error
    if not isinstance(summary, dict) or summary.get("schema") not in COMPATIBLE_SCHEMAS:
        raise EvidenceError(f"unknown evidence schema in {summary_path.name}")
    version = COMPATIBLE_SCHEMAS[summary["schema"]]
    if (
        summary.get("version") != version
        or summary.get("profile") != profile
        or summary.get("model") != model
        or summary.get("reviewer") is not reviewer
        or summary.get("plan_mode") is not reviewer
    ):
        raise EvidenceError(f"evidence identity mismatch in {summary_path.name}")
    if summary.get("wrapper_exit_code") != wrapper_exit_code:
        raise EvidenceError(f"wrapper exit mismatch in {summary_path.name}")

    reason_fields = summary.get("reason_fields")
    identifier_fields = summary.get("identifier_fields")
    if not isinstance(reason_fields, dict) or set(reason_fields) != REASON_KEYS:
        raise EvidenceError(f"invalid reason field inventory in {summary_path.name}")
    if not isinstance(identifier_fields, dict) or set(identifier_fields) != IDENTIFIER_KEYS:
        raise EvidenceError(f"invalid identifier field inventory in {summary_path.name}")
    for key, value in {**reason_fields, **identifier_fields}.items():
        _validate_text_evidence(value, key)

    kind = summary.get("terminal_record_kind")
    if kind not in RECORD_KINDS:
        raise EvidenceError(f"invalid terminal record kind in {summary_path.name}")
    expected_protocol = {
        "exact_raw_event": "exact_terminal_event_retained",
        "oversized_digest_only": (
            "terminal_status_unavailable_fail_closed"
            if summary.get("oversized_record_classification") == "terminal_result"
            else "terminal_classification_unavailable_fail_closed"
        ),
        "malformed_event": "malformed_terminal_event",
        "no_terminal_event": "no_terminal_event",
    }[kind]
    if summary.get("protocol_evidence_outcome") != expected_protocol:
        raise EvidenceError(f"protocol evidence outcome mismatch in {summary_path.name}")
    raw_record: dict[str, Any] | None = None
    provider_record_observed = kind != "no_terminal_event"
    terminal_observed = kind in {"exact_raw_event", "malformed_event"} or (
        kind == "oversized_digest_only"
        and summary.get("oversized_record_classification") == "terminal_result"
    )
    if summary.get("provider_record_observed") is not provider_record_observed:
        raise EvidenceError(f"provider record observation mismatch in {summary_path.name}")
    if summary.get("terminal_result_observed") is not terminal_observed:
        raise EvidenceError(f"terminal observation mismatch in {summary_path.name}")
    raw_name = summary.get("raw_result_artifact")
    if kind in {"exact_raw_event", "malformed_event"}:
        expected_name = f"{prefix}.{RAW_SUFFIX}"
        if raw_name != expected_name:
            raise EvidenceError(f"raw evidence path mismatch in {summary_path.name}")
        raw_path = run_directory / expected_name
        raw_bytes = _read_private_regular(raw_path, run_directory, MAX_RAW_BYTES)
        if (
            summary.get("raw_result_bytes") != len(raw_bytes)
            or summary.get("raw_result_sha256") != _sha256(raw_bytes)
        ):
            raise EvidenceError(f"raw evidence digest mismatch in {summary_path.name}")
        raw_record = {
            "relative_path": raw_path.name,
            "sha256": _sha256(raw_bytes),
            "size": len(raw_bytes),
        }
    else:
        if raw_name is not None or not summary.get("raw_result_absent_reason"):
            raise EvidenceError(f"raw evidence absence is ambiguous in {summary_path.name}")
        unexpected = run_directory / f"{prefix}.{RAW_SUFFIX}"
        if unexpected.exists() or unexpected.is_symlink():
            raise EvidenceError(f"unexpected raw evidence artifact: {unexpected.name}")
        if kind == "oversized_digest_only":
            if (
                type(summary.get("raw_result_bytes")) is not int
                or summary["raw_result_bytes"] <= MAX_RAW_BYTES
                or not isinstance(summary.get("raw_result_sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", summary["raw_result_sha256"]) is None
                or summary.get("normalized_status") is not None
                or not summary.get("protocol_error")
                or summary.get("oversized_record_classification") not in {
                    None, "terminal_result"
                }
            ):
                raise EvidenceError(f"invalid oversized evidence in {summary_path.name}")
        elif summary.get("raw_result_bytes") != 0 or summary.get("raw_result_sha256") is not None:
            raise EvidenceError(f"invalid absent raw evidence in {summary_path.name}")

    preferred = summary.get("preferred_reason")
    if preferred is not None:
        if (
            not isinstance(preferred, dict)
            or set(preferred) != {"field", "source", "text"}
            or preferred.get("field") not in REASON_KEYS
            or preferred.get("text") != reason_fields[preferred["field"]]["text"]
            or preferred.get("source") != reason_fields[preferred["field"]]["source"]
        ):
            raise EvidenceError(f"invalid preferred reason in {summary_path.name}")

    lease_summary = None
    if version == 4:
        lease_summary = summary.get("provider_launch_lease")
        _validate_legacy_v1_lease(
            lease_summary, summary, wrapper_exit_code, summary_path.name
        )
    elif version == 5:
        lease_summary = summary.get("provider_launch_lease")
        _validate_v2_lease(
            lease_summary, summary, wrapper_exit_code, summary_path.name
        )

    process_group_cleanup = None
    version_probe_cleanup = None
    if version == 6:
        process_group_cleanup = _validate_cleanup_record(
            summary.get("process_group_cleanup"),
            summary_path.name,
            wrapper_exit_code,
            label="process-group",
        )
        version_probe_cleanup = _validate_cleanup_record(
            summary.get("version_probe_cleanup"),
            summary_path.name,
            wrapper_exit_code,
            label="version-probe",
        )

    terminal_after_fence = False
    if version >= 3:
        status_source = summary.get("status_source")
        response_source = summary.get("response_source")
        error_source = summary.get("error_source")
        if status_source is not None and status_source not in STATUS_SOURCES:
            raise EvidenceError(f"invalid status source in {summary_path.name}")
        if response_source is not None and response_source not in RESPONSE_SOURCES:
            raise EvidenceError(f"invalid response source in {summary_path.name}")
        if error_source is not None and error_source not in ERROR_SOURCES:
            raise EvidenceError(f"invalid error source in {summary_path.name}")
        terminal_sequence = summary.get("terminal_result_sequence")
        fence_sequence = summary.get("completion_fence_sequence")
        protocol_sequence = summary.get("protocol_error_sequence")
        for label, value in (
            ("terminal", terminal_sequence),
            ("fence", fence_sequence),
            ("protocol", protocol_sequence),
        ):
            if value is not None and (type(value) is not int or value <= 0):
                raise EvidenceError(
                    f"invalid {label} event sequence in {summary_path.name}"
                )
        if terminal_observed and kind != "oversized_digest_only" and terminal_sequence is None:
            raise EvidenceError(f"missing terminal sequence in {summary_path.name}")
        if summary.get("completion_fence_observed") is True and fence_sequence is None:
            raise EvidenceError(f"missing fence sequence in {summary_path.name}")
        terminal_after_fence = (
            terminal_sequence is not None
            and fence_sequence is not None
            and terminal_sequence > fence_sequence
        )
        protocol_after_fence = (
            protocol_sequence is not None
            and fence_sequence is not None
            and protocol_sequence > fence_sequence
        )
        if summary.get("terminal_result_after_completion_fence") is not terminal_after_fence:
            raise EvidenceError(f"terminal/fence ordering mismatch in {summary_path.name}")
        if summary.get("protocol_error_after_completion_fence") is not protocol_after_fence:
            raise EvidenceError(f"protocol/fence ordering mismatch in {summary_path.name}")
        expected_transport = False
        if fence_sequence is not None:
            expected_transport = not (
                (protocol_sequence is not None and protocol_sequence <= fence_sequence)
                or (
                    summary.get("is_error") is True
                    and terminal_sequence is not None
                    and terminal_sequence <= fence_sequence
                )
            )
        elif kind == "exact_raw_event":
            expected_transport = (
                summary.get("is_error") is False and protocol_sequence is None
            )
        if summary.get("transport_success") is not expected_transport:
            raise EvidenceError(f"transport-success relationship mismatch in {summary_path.name}")
        if wrapper_exit_code == 0 and not expected_transport:
            raise EvidenceError(f"wrapper success lacks transport completion in {summary_path.name}")
        if kind == "exact_raw_event" and raw_record is not None:
            try:
                raw_event = json.loads(raw_bytes.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise EvidenceError(
                    f"exact raw event is malformed in {summary_path.name}: {error}"
                ) from error
            if not isinstance(raw_event, dict):
                raise EvidenceError(f"exact raw event is not an object in {summary_path.name}")
            nested = raw_event.get("result")
            payload = nested if isinstance(nested, dict) else raw_event
            status_value = payload.get("status")
            status_path = "result.status" if payload is not raw_event else "event.status"
            if status_value is None:
                status_value = payload.get("subtype")
                status_path = "result.subtype" if payload is not raw_event else "event.subtype"
            if isinstance(status_value, str):
                if (
                    summary.get("raw_status") != status_value
                    or summary.get("normalized_status") != status_value.lower()
                    or status_source != status_path
                ):
                    raise EvidenceError(f"raw status evidence mismatch in {summary_path.name}")
            response_value = payload.get("response")
            response_path = "result.response" if payload is not raw_event else "event.response"
            if isinstance(response_value, str):
                encoded_response = response_value.encode("utf-8")
                if (
                    response_source != response_path
                    or summary.get("response_present") is not bool(response_value)
                    or summary.get("response_utf8_bytes") != len(encoded_response)
                    or summary.get("response_sha256") != _sha256(encoded_response)
                ):
                    raise EvidenceError(f"raw response evidence mismatch in {summary_path.name}")
            if "error" in payload:
                error_value = payload["error"]
                error_path = "result.error" if payload is not raw_event else "event.error"
                if isinstance(error_value, str):
                    error_bytes = error_value.encode("utf-8")
                    error_field = reason_fields["error"]
                    if (
                        error_source != error_path
                        or error_field.get("source") != error_path
                        or error_field.get("utf8_bytes") != len(error_bytes)
                        or error_field.get("sha256") != _sha256(error_bytes)
                    ):
                        raise EvidenceError(f"raw error evidence mismatch in {summary_path.name}")
            for identifier in IDENTIFIER_KEYS:
                identifier_value = payload.get(identifier)
                if not isinstance(identifier_value, str):
                    continue
                identifier_path = (
                    f"result.{identifier}" if payload is not raw_event
                    else f"event.{identifier}"
                )
                identifier_bytes = identifier_value.encode("utf-8")
                identifier_field = identifier_fields[identifier]
                if (
                    identifier_field.get("source") != identifier_path
                    or identifier_field.get("utf8_bytes") != len(identifier_bytes)
                    or identifier_field.get("sha256") != _sha256(identifier_bytes)
                ):
                    raise EvidenceError(
                        f"raw identifier evidence mismatch in {summary_path.name}"
                    )

    protocol_error = _validated_protocol_error(
        summary.get("protocol_error"), summary_path.name
    )
    validated = {
        "validation": "validated",
        "summary": {
            "relative_path": summary_path.name,
            "sha256": _sha256(summary_bytes),
            "size": len(summary_bytes),
        },
        "raw": raw_record,
        "raw_absent_reason": summary.get("raw_result_absent_reason"),
        "provider_status": summary.get("normalized_status"),
        "provider_raw_status": summary.get("raw_status"),
        "provider_reason_available": preferred is not None,
        "provider_reason_field": None if preferred is None else preferred["source"],
        "provider_reason": None if preferred is None else preferred["text"],
        "terminal_record_kind": kind,
        "protocol_evidence_outcome": summary.get("protocol_evidence_outcome"),
        "observed_result_bytes": summary.get("raw_result_bytes"),
        "observed_result_sha256": summary.get("raw_result_sha256"),
        "provider_record_observed": provider_record_observed,
        "terminal_result_observed": terminal_observed,
        "completion_fence_observed": summary.get("completion_fence_observed") is True,
        "child_started": summary.get("child_started") is True,
        "child_exit_code": summary.get("child_exit_code"),
        "wrapper_exit_code": summary.get("wrapper_exit_code"),
        "protocol_error": protocol_error,
    }
    if version >= 3:
        validated.update({
            "terminal_result_after_completion_fence": terminal_after_fence,
            "transport_success": summary.get("transport_success"),
            "status_source": summary.get("status_source"),
            "response_source": summary.get("response_source"),
            "error_source": summary.get("error_source"),
        })
    if version in {4, 5}:
        validated["provider_launch_lease"] = lease_summary
    if version == 6:
        validated["process_group_cleanup"] = process_group_cleanup
        validated["version_probe_cleanup"] = version_probe_cleanup
    return validated
