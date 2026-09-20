"""Private terminal-evidence serialization for the Antigravity wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import time
from typing import Any, Sequence


MAX_DIAGNOSTIC_BYTES = 4 * 1024
MAX_TERMINAL_RESULT_BYTES = 16 * 1024 * 1024
MAX_EVIDENCE_SUMMARY_BYTES = 1024 * 1024
MAX_STDERR_TAIL_BYTES = 16 * 1024
# Version 6 is the first direct-launch schema that attests process-group
# custody. Historical v2-v5 artifacts remain reader-compatible in the
# dispatcher validator; new writers use this explicit discriminator.
EVIDENCE_SCHEMA = "antigravity-terminal-evidence-v6"
EVIDENCE_VERSION = 6
PROCESS_GROUP_CLEANUP_SCHEMA = "antigravity-process-group-cleanup-v1"
REASON_KEYS = (
    "error", "message", "reason", "cancel_reason", "cancellation_reason",
    "finish_reason", "termination_reason", "code", "error_code",
)
REASON_PRIORITY = (
    "error", "message", "reason", "cancel_reason", "cancellation_reason",
    "finish_reason", "termination_reason", "error_code", "code",
)
IDENTIFIER_KEYS = (
    "conversation_id", "request_id", "session_id", "operation_id",
    "run_id", "turn_id",
)


class EvidenceWriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class OversizedRecord:
    utf8_bytes: int
    sha256: str
    terminal_event: bool
    classification: str | None


@dataclass
class OversizedRecordCapture:
    digest: Any
    prefix_limit: int
    total_bytes: int = 0
    prefix: bytes = b""

    @classmethod
    def create(cls, prefix_limit: int = 64 * 1024) -> "OversizedRecordCapture":
        return cls(hashlib.sha256(), prefix_limit)

    def feed(self, chunk: bytes) -> None:
        self.digest.update(chunk)
        self.total_bytes += len(chunk)
        remaining = self.prefix_limit - len(self.prefix)
        if remaining > 0:
            self.prefix += chunk[:remaining]

    def finish(self) -> OversizedRecord:
        terminal = bool(re.match(
            rb'^\s*\{\s*"(?:type|event)"\s*:\s*"result"\s*[,}]',
            self.prefix,
        ))
        return OversizedRecord(
            self.total_bytes,
            self.digest.hexdigest(),
            terminal,
            "terminal_result" if terminal else None,
        )


@dataclass
class StderrCapture:
    digest: Any
    total_bytes: int = 0
    tail: bytes = b""

    @classmethod
    def create(cls) -> "StderrCapture":
        return cls(hashlib.sha256())

    def feed(self, chunk: bytes) -> None:
        self.digest.update(chunk)
        self.total_bytes += len(chunk)
        self.tail = (self.tail + chunk)[-MAX_STDERR_TAIL_BYTES:]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text_evidence(value: Any, source: str | None = None) -> dict[str, Any]:
    if not isinstance(value, str):
        value = ""
    encoded = value.encode("utf-8")
    bounded = encoded[:MAX_DIAGNOSTIC_BYTES]
    return {
        "text": bounded.decode("utf-8", errors="ignore"),
        "utf8_bytes": len(encoded),
        "sha256": _sha256(encoded),
        "truncated": len(encoded) > len(bounded),
        "source": source,
    }


def _atomic_private_write(path: Path, data: bytes, maximum: int) -> None:
    if len(data) > maximum:
        raise EvidenceWriteError(
            f"evidence artifact exceeds {maximum} bytes: {path.name}"
        )
    path.parent.mkdir(mode=0o700, parents=False, exist_ok=True)
    if path.exists() or path.is_symlink():
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise EvidenceWriteError(f"unsafe evidence target: {path}")
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp"
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        info = os.lstat(temporary)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
            raise EvidenceWriteError(f"unsafe evidence temporary file: {temporary}")
        os.replace(temporary, path)
        final = os.lstat(path)
        if not stat.S_ISREG(final.st_mode) or stat.S_IMODE(final.st_mode) != 0o600:
            raise EvidenceWriteError(f"unsafe evidence artifact: {path}")
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            temporary.unlink()
        except OSError:
            pass


def _selected_value(event: dict[str, Any], key: str) -> tuple[Any, str | None]:
    result = event.get("result")
    containers: list[tuple[str, dict[str, Any]]] = []
    if isinstance(result, dict):
        containers.append(("result", result))
    containers.append(("event", event))
    for name, container in containers:
        value = container.get(key)
        if isinstance(value, str):
            return value, f"{name}.{key}"
        if key == "error" and isinstance(value, dict):
            for nested_key in ("message", "reason", "code", "error_code"):
                nested = value.get(nested_key)
                if isinstance(nested, str):
                    return nested, f"{name}.error.{nested_key}"
    for name, container in containers:
        error = container.get("error")
        if isinstance(error, dict) and isinstance(error.get(key), str):
            return error[key], f"{name}.error.{key}"
    return None, None


def _closed_terminal_fields(raw: bytes | None) -> dict[str, Any]:
    event: dict[str, Any] = {}
    if raw is not None:
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            decoded = None
        if isinstance(decoded, dict):
            event = decoded
    nested = event.get("result")
    payload: dict[str, Any] = nested if isinstance(nested, dict) else event
    fields: dict[str, Any] = {
        "subtype": payload.get("subtype") if isinstance(payload.get("subtype"), str) else None,
        "reason_fields": {},
        "identifier_fields": {},
        "preferred_reason": None,
    }
    for key in REASON_KEYS:
        value, source = _selected_value(event, key)
        fields["reason_fields"][key] = _text_evidence(value, source)
    for key in IDENTIFIER_KEYS:
        value, source = _selected_value(event, key)
        fields["identifier_fields"][key] = _text_evidence(value, source)
    for key in REASON_PRIORITY:
        evidence = fields["reason_fields"][key]
        if evidence["text"]:
            fields["preferred_reason"] = {
                "field": key,
                "source": evidence["source"],
                "text": evidence["text"],
            }
            break
    return fields


_CLEANUP_FIELDS = (
    "schema",
    "reason",
    "attempted",
    "term_status",
    "kill_status",
    "group_absent",
    "group_state",
    "parent_reaped",
    "stdout_reader_joined",
    "stderr_reader_joined",
    "readers_joined",
    "cleanup_complete",
    "failure_class",
)


def _default_cleanup_record(
    *, child_started: bool, reason: str, failure_class: str | None = None
) -> dict[str, Any]:
    """Return an explicit, conservative cleanup record for legacy callers."""
    no_group = not child_started
    return {
        "schema": PROCESS_GROUP_CLEANUP_SCHEMA,
        "reason": reason,
        "attempted": child_started,
        "term_status": "not_attempted",
        "kill_status": "not_attempted",
        "group_absent": no_group,
        "group_state": "absent" if no_group else "unknown",
        "parent_reaped": no_group,
        "stdout_reader_joined": no_group,
        "stderr_reader_joined": no_group,
        "readers_joined": no_group,
        "cleanup_complete": no_group,
        "failure_class": failure_class or (
            None if no_group else "cleanup_not_attested"
        ),
    }


def _closed_cleanup_record(
    value: dict[str, Any] | None,
    *,
    child_started: bool,
    reason: str,
) -> dict[str, Any]:
    """Copy only the bounded cleanup vocabulary into durable evidence."""
    default = _default_cleanup_record(
        child_started=child_started,
        reason=reason,
    )
    if not isinstance(value, dict):
        return default
    return {key: value.get(key, default[key]) for key in _CLEANUP_FIELDS}


def write_terminal_evidence(
    prefix: Path,
    *,
    profile: str,
    model: str,
    reviewer: bool,
    command: Sequence[str],
    observer: Any | None,
    stderr_capture: StderrCapture,
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    child_started: bool,
    child_exit_code: int | None,
    wrapper_exit_code: int,
    received_signals: list[int],
    signal_events: list[dict[str, Any]],
    child_exit_monotonic: float | None,
    protocol_error: str | None = None,
    agy_version: str | None = None,
    process_group_cleanup: dict[str, Any] | None = None,
    version_probe_cleanup: dict[str, Any] | None = None,
) -> None:
    raw = None if observer is None else observer.raw_terminal_result
    oversized = (
        None if observer is None else getattr(observer, "oversized_terminal_result", None)
    )
    raw_path = prefix.with_name(
        f"{prefix.name}.antigravity-terminal-result.raw.json"
    )
    summary_path = prefix.with_name(
        f"{prefix.name}.antigravity-terminal-result.json"
    )
    if raw is not None:
        _atomic_private_write(raw_path, raw, MAX_TERMINAL_RESULT_BYTES)

    terminal = None if observer is None else observer.terminal_result
    response = "" if terminal is None else terminal.response
    response_bytes = response.encode("utf-8")
    terminal_time = None if observer is None else observer.terminal_result_monotonic
    fence_time = None if observer is None else observer.completion_fence_monotonic
    terminal_sequence = (
        None if observer is None else getattr(observer, "terminal_result_sequence", None)
    )
    fence_sequence = (
        None if observer is None else getattr(observer, "completion_fence_sequence", None)
    )
    protocol_sequence = (
        None if observer is None else getattr(observer, "protocol_error_sequence", None)
    )
    first_wrapper_signal = signal_events[0]["monotonic"] if signal_events else None
    last_action = signal_events[-1]["action"] if signal_events else "none"
    if oversized is not None:
        record_kind = "oversized_digest_only"
    elif raw is not None and terminal is None:
        record_kind = "malformed_event"
    elif raw is not None:
        record_kind = "exact_raw_event"
    else:
        record_kind = "no_terminal_event"
    observed_bytes = (
        oversized.utf8_bytes if oversized is not None else (0 if raw is None else len(raw))
    )
    observed_sha256 = (
        oversized.sha256 if oversized is not None else (None if raw is None else _sha256(raw))
    )
    protocol_outcome = {
        "exact_raw_event": "exact_terminal_event_retained",
        "oversized_digest_only": (
            "terminal_status_unavailable_fail_closed"
            if oversized is not None and oversized.terminal_event
            else "terminal_classification_unavailable_fail_closed"
        ),
        "malformed_event": "malformed_terminal_event",
        "no_terminal_event": "no_terminal_event",
    }[record_kind]
    summary: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA, "version": EVIDENCE_VERSION,
        "profile": profile, "model": model, "reviewer": reviewer,
        "plan_mode": reviewer,
        "agy_executable": command[0] if command else "agy",
        "agy_cli_version": agy_version,
        "process_group_cleanup": _closed_cleanup_record(
            process_group_cleanup,
            child_started=child_started,
            reason="main-process-group",
        ),
        "version_probe_cleanup": _closed_cleanup_record(
            version_probe_cleanup,
            child_started=False,
            reason="version-probe-process-group",
        ),
        "started_at": started_at, "ended_at": ended_at,
        "duration_seconds": round(duration_seconds, 6),
        "child_started": child_started, "child_exit_code": child_exit_code,
        "wrapper_exit_code": wrapper_exit_code,
        "locally_observed_signal": (
            None if not received_signals else signal.Signals(received_signals[0]).name
        ),
        "completion_fence_observed": bool(
            observer is not None and observer.completed_by_fence
        ),
        "provider_record_observed": raw is not None or oversized is not None,
        "terminal_result_observed": (
            raw is not None
            or (oversized is not None and oversized.terminal_event)
        ),
        "terminal_record_kind": record_kind,
        "protocol_evidence_outcome": protocol_outcome,
        "oversized_record_classification": (
            None if oversized is None else oversized.classification
        ),
        "raw_status": None if terminal is None else terminal.raw_status,
        "normalized_status": None if terminal is None else terminal.status,
        "status_source": None if terminal is None else terminal.status_source,
        "is_error": None if terminal is None else terminal.is_error,
        "is_incomplete": None if terminal is None else terminal.is_incomplete,
        "response_present": terminal is not None and bool(response),
        "response_utf8_bytes": len(response_bytes),
        "response_sha256": _sha256(response_bytes),
        "response_source": None if terminal is None else terminal.response_source,
        "error_source": None if terminal is None else terminal.error_source,
        "raw_result_artifact": raw_path.name if raw is not None else None,
        "raw_result_absent_reason": (
            None if raw is not None else (
                "terminal record exceeds raw artifact limit"
                if oversized is not None
                else "no terminal result event received"
            )
        ),
        "raw_result_bytes": observed_bytes,
        "raw_result_sha256": observed_sha256,
        "child_stderr_sha256": stderr_capture.digest.hexdigest(),
        "child_stderr_bytes": stderr_capture.total_bytes,
        "child_stderr_tail": stderr_capture.tail.decode("utf-8", errors="replace"),
        "stderr_truncated": stderr_capture.total_bytes > len(stderr_capture.tail),
        "wrapper_termination_action": last_action,
        "wrapper_signaled_child_after_result": any(
            terminal_time is not None and item["monotonic"] >= terminal_time
            for item in signal_events
        ),
        "result_observed_before_wrapper_signal": (
            terminal_time is not None
            and (first_wrapper_signal is None or terminal_time <= first_wrapper_signal)
        ),
        "wrapper_signal_preceded_result": (
            terminal_time is not None and first_wrapper_signal is not None
            and first_wrapper_signal < terminal_time
        ),
        "terminal_result_monotonic": terminal_time,
        "terminal_result_sequence": terminal_sequence,
        "completion_fence_monotonic": fence_time,
        "completion_fence_sequence": fence_sequence,
        "protocol_error_sequence": protocol_sequence,
        "terminal_result_after_completion_fence": (
            terminal_sequence is not None
            and fence_sequence is not None
            and terminal_sequence > fence_sequence
        ),
        "protocol_error_after_completion_fence": (
            protocol_sequence is not None
            and fence_sequence is not None
            and protocol_sequence > fence_sequence
        ),
        "transport_success": bool(
            observer is not None
            and getattr(observer, "transport_success", wrapper_exit_code == 0)
        ),
        "wrapper_signal_events": signal_events,
        "natural_child_exit_monotonic": (
            child_exit_monotonic
            if child_exit_monotonic is not None and (
                first_wrapper_signal is None
                or child_exit_monotonic <= first_wrapper_signal
            ) else None
        ),
        "child_exit_monotonic": child_exit_monotonic,
        "child_exited_naturally": (
            child_exit_monotonic is not None and (
                first_wrapper_signal is None
                or child_exit_monotonic <= first_wrapper_signal
            )
        ),
        "protocol_error": (
            protocol_error or (None if observer is None else observer.protocol_error)
        ),
    }
    summary.update(_closed_terminal_fields(raw))
    encoded = (json.dumps(summary, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    _atomic_private_write(summary_path, encoded, MAX_EVIDENCE_SUMMARY_BYTES)
