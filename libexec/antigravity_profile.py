from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import threading
import time
from typing import Any, BinaryIO, Callable, Sequence

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from antigravity_terminal_evidence import (
    EvidenceWriteError,
    OversizedRecord,
    OversizedRecordCapture,
    StderrCapture,
    utc_now,
    write_terminal_evidence,
)


PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
# Antigravity's documented print mode takes the prompt as an argv value rather
# than from stdin. Keep well below macOS ARG_MAX after accounting for the
# inherited environment and the launcher's fixed arguments.
MAX_PROMPT_BYTES = 256 * 1024
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
FENCE_NONCE_BYTES = 16  # 128 bits -> 32 hex characters
# `agy --print` applies a hidden 5m0s deadline and (through 1.1.17) exposes no
# value that disables it, so a healthy long agentic stage dies on elapsed time
# alone. This ceiling is a compatibility floor for that upstream requirement,
# not a phase deadline: it is set far past any plausible single stage so that
# hitting it means the provider hung, never that the work took too long.
ANTIGRAVITY_PRINT_TIMEOUT = "24h"
VERSION_PROBE_TIMEOUT_SECONDS = 0.5
MAX_VERSION_OUTPUT_BYTES = 4096

# The provider wrapper owns this private, inherited pipe only when launched by
# the exact managed provider path. Its payload is a closed token vocabulary;
# nested AGY receives a sanitized environment and never inherits the writer FD.
ACTIVITY_PIPE_ENV = "AGENT_CENTRAL_ANTIGRAVITY_ACTIVITY_FD"
ACTIVITY_MAX_TOKEN_BYTES = 64
ACTIVITY_STDOUT_TOKEN = b"O\n"
ACTIVITY_STDERR_TOKEN = b"E\n"
ACTIVITY_PROTOCOL_TOKEN = b"P\n"
ACTIVITY_WAITING_TOKEN = b"W\n"
ACTIVITY_PGID_PATTERN = re.compile(rb"^G:[1-9][0-9]*:[1-9][0-9]*\n$")

# Lifecycle supervision bounds (seconds). Monkeypatchable in tests.
POST_RESULT_GRACE_SECONDS = 5.0
POST_RESULT_KILL_GRACE_SECONDS = 2.0
STREAM_DRAIN_GRACE_SECONDS = 2.0
PROCESS_GROUP_POLL_SECONDS = 0.02
PROCESS_GROUP_STATUS_TIMEOUT_SECONDS = 0.25
MAX_RECORD_BYTES = 16 * 1024 * 1024
MAX_DIAGNOSTIC_BYTES = 4 * 1024

PROCESS_GROUP_CLEANUP_SCHEMA = "antigravity-process-group-cleanup-v1"
CLEANUP_FAILURE_DIAGNOSTIC = (
    "antigravity-profile: process-group cleanup unproven"
)
CLEANUP_SIGNAL_STATUSES = frozenset(
    {"sent", "absent", "permission_denied", "error", "not_attempted"}
)

ALLOWED_SUCCESS_STATUSES = frozenset({"success", "completed", "ok"})
ALLOWED_ERROR_STATUSES = frozenset(
    {"error", "canceled", "interrupted", "invalid", "failed", "failure"}
)
NON_TERMINAL_STATUSES = frozenset(
    {"running", "waiting", "in_progress", "pending", "active"}
)

# Liveness classification for parsed protocol events. Emitting `P` for *every*
# parsed JSON object let generic wrapper chatter refresh the silence clock
# forever, which made the advisory evidence useless. Only these named events are
# credited as work advancing; everything else -- keepalives and any event this
# wrapper does not recognize -- is reported as non-progress `W`. Defaulting to
# non-progress is the safe direction: the cost is at most an extra advisory
# notice, never a termination, because silence no longer kills anything.
PROGRESS_EVENT_NAMES = frozenset(
    {
        "step_update",
        "agent_response",
        "content_block_delta",
        "text",
        "message",
        "assistant",
        "result",
    }
)
WAITING_EVENT_NAMES = frozenset({"ping", "keepalive", "heartbeat", "status"})


def _classify_protocol_event(event: dict[str, Any]) -> str:
    """Classify one parsed protocol event as "progress" or "waiting"."""
    name = event.get("type") or event.get("event")
    if not isinstance(name, str):
        return "waiting"
    if name in WAITING_EVENT_NAMES:
        return "waiting"
    for field in ("status", "subtype"):
        value = event.get(field)
        # Statuses arrive in mixed case (`SUCCESS`, `running`); the rest of this
        # wrapper compares them lowercased, so this must too.
        if isinstance(value, str) and value.lower() in NON_TERMINAL_STATUSES:
            # A `waiting`/`pending`/`running` status proves nothing advanced.
            return "waiting"
    return "progress" if name in PROGRESS_EVENT_NAMES else "waiting"


class ProfileError(RuntimeError):
    pass


class ActivityPipeWriter:
    """Write only bounded, source-defined liveness tokens to the wrapper pipe."""

    def __init__(self, fd: int) -> None:
        self._fd = fd
        self._lock = threading.Lock()
        self._closed = False

    @classmethod
    def from_environment(cls) -> "ActivityPipeWriter | None":
        value = os.environ.get(ACTIVITY_PIPE_ENV)
        if value is None:
            return None
        fd = -1
        try:
            fd = int(value, 10)
            info = os.fstat(fd)
            if fd <= 2 or not stat.S_ISFIFO(info.st_mode):
                raise ValueError("activity descriptor is not a private pipe")
            # Explicitly clear inheritance before starting either AGY process;
            # close_fds=True is an additional subprocess boundary, not the only
            # proof that the writer cannot reach the nested provider.
            os.set_inheritable(fd, False)
        except (OSError, ValueError):
            try:
                os.close(fd)
            except OSError:
                pass
            return None
        return cls(fd)

    def emit(self, token: bytes) -> None:
        if not (
            token in {
                ACTIVITY_STDOUT_TOKEN,
                ACTIVITY_STDERR_TOKEN,
                ACTIVITY_PROTOCOL_TOKEN,
                ACTIVITY_WAITING_TOKEN,
            }
            or ACTIVITY_PGID_PATTERN.fullmatch(token)
        ):
            return
        if len(token) > ACTIVITY_MAX_TOKEN_BYTES:
            return
        with self._lock:
            if self._closed:
                return
            try:
                offset = 0
                while offset < len(token):
                    offset += os.write(self._fd, token[offset:])
            except (BrokenPipeError, OSError, ValueError):
                self._closed = True

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            try:
                os.close(self._fd)
            except OSError:
                pass


@dataclass(frozen=True)
class Profile:
    model: str


@dataclass(frozen=True)
class TerminalResult:
    raw_status: str | None
    status: str
    response: str
    error: str
    is_error: bool
    is_incomplete: bool
    status_source: str | None
    response_source: str | None
    error_source: str | None


def _bounded_diagnostic_text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("message")
    if value is None:
        return ""
    if not isinstance(value, str):
        return ""

    encoded = value.encode("utf-8")
    if len(encoded) <= MAX_DIAGNOSTIC_BYTES:
        return value

    suffix = "...[truncated]"
    prefix_bytes = encoded[: MAX_DIAGNOSTIC_BYTES - len(suffix.encode("utf-8"))]
    return prefix_bytes.decode("utf-8", errors="ignore") + suffix


def generate_fence_nonce() -> str:
    """Generate a high-entropy cryptographically random nonce (128 bits)."""
    import secrets

    return secrets.token_hex(FENCE_NONCE_BYTES)


def format_completion_fence(nonce: str) -> str:
    """Format the exact completion-fence line for a given nonce."""
    return f"<<<AGENT-CENTRAL-COMPLETE {nonce}>>>"


def format_transport_instructions(nonce: str) -> str:
    """Format launcher-owned transport completion instructions appended to prompt."""
    fence = format_completion_fence(nonce)
    return (
        "\n\n---\n"
        "# Agent-Central Transport Instructions\n"
        "1. Run every required local build, test, or validation command in the foreground. Do NOT launch a local command in the background and then keep waiting for it indefinitely, and do NOT emit heartbeat or no-op output to keep the turn alive.\n"
        "2. A required local foreground command MAY run longer than fifteen minutes, and MAY produce no output while it runs. Let it finish. Do not abandon, background, or truncate it merely because it is slow or quiet, and do not wrap it in a short timeout.\n"
        "3. Complete or terminate every local child process you started before beginning your final response.\n"
        "4. Polling a hosted CI job or any other externally hosted job is different from running a local test, and is the only case that is time-bounded. State the finite polling interval before you begin polling, and poll only for that interval. If that evidence is still pending when your bound is reached, do not keep waiting: return an accurate terminal `blocked` result — or the explicitly permitted \"pending externally\" completion when the task contract allows one — naming the immutable run or job identifier and the recovery action.\n"
        "5. Never fabricate or assume a passing validation result merely to reach a terminal state. An honest blocked or failed result is required instead.\n"
        "6. Do not begin the final response until no further tool calls are required.\n"
        "7. Make NO tool calls after beginning the final response, and especially make NO tool calls after the completion fence.\n"
        "8. When your final response is completely finished, emit exactly this completion-fence line as the very last line of your response:\n"
        f"{fence}\n"
        "9. The transport will terminate immediately once this completion fence is received.\n"
    )


def build_prompt(caller_prompt: str, nonce: str) -> str:
    """Append transport instructions with invocation-unique fence nonce to caller prompt."""
    return caller_prompt + format_transport_instructions(nonce)


def load_profile(root: Path, name: str) -> Profile:
    if not PROFILE_NAME_PATTERN.fullmatch(name):
        raise ProfileError(f"invalid profile name: {name}")
    path = root / "profiles" / f"{name}.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileError(f"unusable Antigravity profile {path}: {error}") from error
    if not isinstance(document, dict) or set(document) != {"model"}:
        raise ProfileError("Antigravity profiles must contain exactly the model field")
    model = document["model"]
    if not isinstance(model, str) or not PROFILE_NAME_PATTERN.fullmatch(model):
        raise ProfileError(f"invalid Antigravity model slug in {path}")
    return Profile(model=model)


def decode_prompt(data: bytes) -> str:
    if len(data) > MAX_PROMPT_BYTES:
        raise ProfileError(
            f"prompt exceeds the Antigravity launcher bound of {MAX_PROMPT_BYTES} bytes"
        )
    try:
        prompt = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProfileError("prompt is not valid UTF-8") from error
    if "\0" in prompt:
        raise ProfileError("prompt contains an argv-incompatible NUL byte")
    return prompt


def build_agy_argv(
    profile: Profile, prompt: str, reviewer: bool = False
) -> list[str]:
    argv = [
        "agy",
        "-p",
        prompt,
        "--model",
        profile.model,
        "--output-format",
        "stream-json",
        "--print-timeout",
        ANTIGRAVITY_PRINT_TIMEOUT,
    ]
    if reviewer:
        argv.extend(["--mode", "plan"])

    # Current operator policy: every headless AGY invocation auto-approves tools.
    argv.append("--dangerously-skip-permissions")
    return argv


def _parse_agy_version_output(stdout: bytes) -> str | None:
    """Return a bounded, human-readable version line or no version."""
    if len(stdout) > MAX_VERSION_OUTPUT_BYTES:
        return None
    try:
        text = stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None
    lines = text.strip().splitlines()
    if not lines:
        return None
    value = lines[0]
    if not re.fullmatch(r"[A-Za-z0-9 ._+()/:-]{1,256}", value):
        return None
    if not any(character.isdigit() for character in value):
        return None
    return value


def _cleanup_record_without_group(reason: str) -> dict[str, Any]:
    """Represent a source-owned process group that was never started."""
    return {
        "schema": PROCESS_GROUP_CLEANUP_SCHEMA,
        "reason": reason,
        "attempted": False,
        "term_status": "not_attempted",
        "kill_status": "not_attempted",
        "group_absent": True,
        "group_state": "absent",
        "parent_reaped": True,
        "stdout_reader_joined": True,
        "stderr_reader_joined": True,
        "readers_joined": True,
        "cleanup_complete": True,
        "failure_class": None,
    }


def _source_process_group(process: subprocess.Popen[bytes]) -> int | None:
    """Return the launch-owned session/group id only when identity is proven."""
    try:
        pgid = os.getpgid(process.pid)
        session = os.getsid(process.pid)
    except (OSError, ValueError):
        return None
    if pgid != process.pid or session != process.pid:
        return None
    return pgid


def _process_group_state(pgid: int) -> str:
    """Return ``absent``, ``present``, or an uncertainty status for a PGID.

    ``killpg(..., 0)`` alone reports zombie-only groups as present and cannot
    distinguish an inaccessible group from a live one.  Use a bounded ``ps``
    read to inspect the member states, treating zombie-only membership as
    quiescent while retaining permission and parser failures as unproven.
    """
    probe_status = "present"
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return "absent"
    except PermissionError:
        # Darwin can report EPERM briefly for a just-reaped, now-empty process
        # group. Resolve membership below before treating that as a custody
        # failure or attempting to signal a potentially reused numeric PGID.
        probe_status = "permission_denied"
    except (OSError, ValueError):
        return "error"

    try:
        listing = subprocess.run(
            ["/bin/ps", "-axo", "pid=,pgid=,stat="],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=PROCESS_GROUP_STATUS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if listing.returncode != 0:
        return "unknown"

    matching_row = False
    for line in listing.stdout.splitlines():
        try:
            fields = line.decode("ascii").split()
            if len(fields) < 3:
                continue
            row_pid = int(fields[0], 10)
            row_pgid = int(fields[1], 10)
        except (UnicodeDecodeError, ValueError):
            continue
        if row_pgid != pgid:
            continue
        matching_row = True
        if fields[2].startswith("Z"):
            continue
        try:
            if os.getsid(row_pid) == pgid:
                return probe_status
        except ProcessLookupError:
            continue
        except (OSError, ValueError):
            return "unknown"
        return "unknown"
    if matching_row:
        # Zombie-only membership cannot execute, mutate, or retain provider
        # streams. The direct parent is reaped separately below.
        return "absent"

    # The group can disappear between killpg(0) and the ps snapshot. Require a
    # second kernel observation before calling that race an absence; otherwise
    # retain uncertainty and never authorize a signal from it.
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return "absent"
    except PermissionError:
        return "permission_denied"
    except (OSError, ValueError):
        return "error"
    return "unknown"


def _wait_for_process_group_absence(pgid: int, timeout: float) -> str:
    deadline = time.monotonic() + max(timeout, 0.0)
    state = _process_group_state(pgid)
    while state != "absent" and time.monotonic() < deadline:
        time.sleep(min(PROCESS_GROUP_POLL_SECONDS, max(0.0, deadline - time.monotonic())))
        state = _process_group_state(pgid)
    return state


def _signal_process_group(pgid: int, signum: int) -> str:
    try:
        os.killpg(pgid, signum)
    except ProcessLookupError:
        return "absent"
    except PermissionError:
        return "permission_denied"
    except (OSError, ValueError):
        return "error"
    return "sent"


def _reap_process(process: subprocess.Popen[bytes], timeout: float) -> bool:
    if process.poll() is not None:
        return True
    try:
        process.wait(timeout=max(timeout, 0.0))
    except subprocess.TimeoutExpired:
        return False
    except (OSError, ValueError):
        return process.poll() is not None
    return process.poll() is not None


def _join_owned_reader(
    thread: threading.Thread, source: BinaryIO, timeout: float
) -> bool:
    thread.join(timeout=max(timeout, 0.0))
    if thread.is_alive():
        try:
            source.close()
        except OSError:
            pass
        thread.join(timeout=max(timeout, 0.0))
    return not thread.is_alive()


def _finalize_process_group(
    process: subprocess.Popen[bytes],
    pgid: int | None,
    *,
    reason: str,
    term_grace: float,
    kill_grace: float,
    readers: Sequence[tuple[str, threading.Thread, BinaryIO]] = (),
) -> dict[str, Any]:
    """Boundedly terminate one source-owned group and attest its aftermath."""
    record: dict[str, Any] = {
        "schema": PROCESS_GROUP_CLEANUP_SCHEMA,
        "reason": reason,
        "attempted": True,
        "term_status": "not_attempted",
        "kill_status": "not_attempted",
        "group_absent": False,
        "group_state": "unknown",
        "parent_reaped": False,
        "stdout_reader_joined": True,
        "stderr_reader_joined": True,
        "readers_joined": True,
        "cleanup_complete": False,
        "failure_class": None,
    }

    if pgid is None:
        record["failure_class"] = "group_identity_unverified"
    else:
        state = _process_group_state(pgid)
        if state == "absent":
            record["term_status"] = "absent"
            record["kill_status"] = "not_attempted"
        elif state == "present":
            record["term_status"] = _signal_process_group(pgid, signal.SIGTERM)
            state = _wait_for_process_group_absence(pgid, term_grace)
            if state == "absent":
                record["kill_status"] = "not_attempted"
            elif state == "present":
                record["kill_status"] = _signal_process_group(pgid, signal.SIGKILL)
                state = _wait_for_process_group_absence(pgid, kill_grace)
        else:
            record["term_status"] = "not_attempted"
            record["failure_class"] = "group_identity_unverified"
        record["group_state"] = state
        record["group_absent"] = state == "absent"

    record["parent_reaped"] = _reap_process(process, kill_grace)
    reader_states: dict[str, bool] = {}
    for name, thread, source in readers:
        reader_states[name] = _join_owned_reader(thread, source, kill_grace)
    if "stdout" in reader_states:
        record["stdout_reader_joined"] = reader_states["stdout"]
    if "stderr" in reader_states:
        record["stderr_reader_joined"] = reader_states["stderr"]
    record["readers_joined"] = all(reader_states.values())

    if record["failure_class"] is None:
        term_status = record["term_status"]
        kill_status = record["kill_status"]
        if not record["group_absent"]:
            if term_status in {"permission_denied", "error"}:
                record["failure_class"] = f"term_{term_status}"
            elif kill_status in {"permission_denied", "error"}:
                record["failure_class"] = f"kill_{kill_status}"
            else:
                record["failure_class"] = (
                    "group_state_unknown"
                    if record["group_state"] == "unknown"
                    else "group_remaining"
                )
        elif not record["parent_reaped"]:
            record["failure_class"] = "parent_not_reaped"
        elif not record["readers_joined"]:
            record["failure_class"] = "reader_join_timeout"

    record["cleanup_complete"] = (
        record["group_absent"]
        and record["parent_reaped"]
        and record["readers_joined"]
        and record["failure_class"] is None
    )
    return record


def agy_cli_version(
    executable: str,
    *,
    cancelled: Callable[[], bool] | None = None,
    env: dict[str, str] | None = None,
    cleanup_result: list[dict[str, Any]] | None = None,
) -> str | None:
    """Probe optional version metadata without delaying provider availability.

    The probe is a direct, bounded subprocess in its own process group.  Any
    launch, output, timeout, or exit failure simply suppresses metadata.
    """
    probe_process: subprocess.Popen[bytes] | None = None
    probe_group_pgid: int | None = None
    reader: threading.Thread | None = None
    captured = bytearray()
    overflow = False

    def drain_stdout() -> None:
        nonlocal overflow
        assert probe_process is not None and probe_process.stdout is not None
        try:
            while chunk := probe_process.stdout.read(65536):
                remaining = MAX_VERSION_OUTPUT_BYTES + 1 - len(captured)
                if remaining > 0:
                    captured.extend(chunk[:remaining])
                if len(captured) > MAX_VERSION_OUTPUT_BYTES or len(chunk) > remaining:
                    overflow = True
        except OSError:
            overflow = True
        finally:
            try:
                probe_process.stdout.close()
            except OSError:
                pass

    try:
        probe_process = subprocess.Popen(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
            start_new_session=True,
            env=env,
        )
        probe_group_pgid = _source_process_group(probe_process)
        reader = threading.Thread(
            target=drain_stdout,
            name="antigravity-version-stdout",
            daemon=True,
        )
        reader.start()
        deadline = time.monotonic() + VERSION_PROBE_TIMEOUT_SECONDS
        while probe_process.poll() is None:
            if cancelled is not None and cancelled():
                raise InterruptedError("wrapper signal received")
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.01)
        reader.join(timeout=VERSION_PROBE_TIMEOUT_SECONDS)
        if reader.is_alive() or overflow or probe_process.returncode != 0:
            return None
        return _parse_agy_version_output(bytes(captured))
    except OSError:
        return None
    finally:
        if probe_process is None:
            probe_cleanup = _cleanup_record_without_group(
                "version-probe-process-group-not-started"
            )
        else:
            assert probe_process.stdout is not None
            probe_readers: tuple[tuple[str, threading.Thread, BinaryIO], ...] = (
                ()
                if reader is None
                else (("stdout", reader, probe_process.stdout),)
            )
            probe_cleanup = _finalize_process_group(
                probe_process,
                probe_group_pgid,
                reason="version-probe-cleanup",
                term_grace=VERSION_PROBE_TIMEOUT_SECONDS,
                kill_grace=VERSION_PROBE_TIMEOUT_SECONDS,
                readers=probe_readers,
            )
        if cleanup_result is not None:
            cleanup_result.append(probe_cleanup)


def _extract_agent_response_delta(event: dict[str, Any]) -> str | None:
    """Extract authenticated agent-response text delta from agy 1.1.19 event.

    Strictly requires event == 'step_update' and step_update.step_type == 'agent_response',
    or top-level agent_response event. Tool calls, tool results, thoughts, diagnostics,
    and metadata are excluded.
    """
    if event.get("event") == "step_update" or event.get("type") == "step_update":
        step_update = event.get("step_update")
        if isinstance(step_update, dict) and step_update.get("step_type") == "agent_response":
            delta = step_update.get("text_delta")
            if isinstance(delta, str):
                return delta
    elif event.get("type") == "agent_response" or event.get("event") == "agent_response":
        delta = event.get("text_delta") or event.get("text")
        if isinstance(delta, str):
            return delta
    return None


def _extract_streaming_text(event: dict[str, Any]) -> str | None:
    """Extract non-agent streaming text for live stderr rendering in legacy formats."""
    event_type = event.get("type") or event.get("event")
    if event_type == "content_block_delta":
        delta = event.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("text"), str):
            return delta["text"]
    elif event_type == "text" and isinstance(event.get("text"), str):
        return event["text"]
    elif event_type == "message":
        content = event.get("content")
        if isinstance(content, str):
            return content
    elif event_type == "assistant":
        msg = event.get("message")
        if isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = [
                    p["text"]
                    for p in content
                    if isinstance(p, dict)
                    and p.get("type") == "text"
                    and isinstance(p.get("text"), str)
                ]
                if texts:
                    return "".join(texts)
    return None


def _selected_field(
    event: dict[str, Any], payload: dict[str, Any], key: str
) -> tuple[Any, str | None]:
    if key in payload:
        source = "result" if payload is not event else "event"
        return payload[key], f"{source}.{key}"
    if key in event:
        return event[key], f"event.{key}"
    return None, None


def _error_text_and_source(value: Any, source: str | None) -> tuple[str, str | None]:
    if value is None:
        return "", None
    if isinstance(value, str):
        return _bounded_diagnostic_text(value), source
    if isinstance(value, dict):
        for key in ("message", "reason", "code", "error_code"):
            nested = value.get(key)
            if isinstance(nested, str):
                return _bounded_diagnostic_text(nested), f"{source}.{key}"
        return "", source
    raise ValueError("malformed result: error must be a string or object")


class StreamObserver:
    """Parse structured stream-json output incrementally and track terminal completion."""

    def __init__(
        self,
        fence_nonce: str | None = None,
        on_text: Callable[[str], None] | None = None,
        max_record_bytes: int | None = None,
        max_response_bytes: int | None = None,
        on_protocol: Callable[[str], None] | None = None,
    ) -> None:
        self.fence_nonce = fence_nonce
        self.on_text = on_text
        self.on_protocol = on_protocol
        self.max_record_bytes = (
            max_record_bytes if max_record_bytes is not None else MAX_RECORD_BYTES
        )
        self.max_response_bytes = (
            max_response_bytes if max_response_bytes is not None else MAX_RESPONSE_BYTES
        )
        self._lock = threading.Lock()
        self.terminal_result: TerminalResult | None = None
        self._result_event_seen = False
        self.raw_terminal_result: bytes | None = None
        self.oversized_terminal_result: OversizedRecord | None = None
        self.terminal_result_monotonic: float | None = None
        self.terminal_result_sequence: int | None = None
        self.fenced_response: str | None = None
        self.completed_by_fence: bool = False
        self.completion_fence_monotonic: float | None = None
        self.completion_fence_sequence: int | None = None
        self.protocol_error: str | None = None
        self.protocol_error_monotonic: float | None = None
        self.protocol_error_sequence: int | None = None
        self._event_sequence = 0
        self._buffer = bytearray()
        self._oversized_capture: OversizedRecordCapture | None = None
        self._response_buffer = ""
        self._streamed_offset = 0

    @property
    def has_terminal_result(self) -> bool:
        with self._lock:
            return (
                self.completed_by_fence
                or self.terminal_result is not None
                or self.oversized_terminal_result is not None
                or self.protocol_error is not None
            )

    @property
    def has_completion(self) -> bool:
        with self._lock:
            return (
                self.completed_by_fence
                or self.terminal_result is not None
                or self.oversized_terminal_result is not None
                or self.protocol_error is not None
            )

    @property
    def transport_success(self) -> bool:
        """Whether provider evidence supports wrapper transport success.

        A completion fence wins over later provider evidence, but never over a
        provider failure or protocol error that was observed first.
        """
        with self._lock:
            if self.completed_by_fence:
                fence = self.completion_fence_sequence
                if fence is None:
                    return False
                if (
                    self.protocol_error_sequence is not None
                    and self.protocol_error_sequence <= fence
                ):
                    return False
                if (
                    self.terminal_result is not None
                    and self.terminal_result.is_error
                    and self.terminal_result_sequence is not None
                    and self.terminal_result_sequence <= fence
                ):
                    return False
                return True
            return (
                self.protocol_error is None
                and self.terminal_result is not None
                and not self.terminal_result.is_error
            )

    def _set_protocol_error(self, detail: str, sequence: int) -> None:
        if self.protocol_error is None:
            self.protocol_error = detail
            self.protocol_error_monotonic = time.monotonic()
            self.protocol_error_sequence = sequence

    def feed(self, chunk: bytes) -> None:
        offset = 0
        while offset < len(chunk):
            newline = chunk.find(b"\n", offset)
            end = len(chunk) if newline < 0 else newline
            segment = chunk[offset:end]
            if self._oversized_capture is not None:
                self._feed_oversized(segment)
            elif len(self._buffer) + len(segment) > self.max_record_bytes:
                self._start_oversized(segment)
            else:
                self._buffer.extend(segment)
            if newline < 0:
                return
            if self._oversized_capture is not None:
                self._finish_oversized()
            else:
                line = bytes(self._buffer)
                self._buffer.clear()
                self._process_line(line)
            offset = newline + 1

    def finish(self) -> None:
        if self._oversized_capture is not None:
            self._finish_oversized()
        if self._buffer.strip():
            line = bytes(self._buffer)
            self._buffer.clear()
            self._process_line(line)
        with self._lock:
            if not self.completed_by_fence and self.on_text:
                unstreamed = self._response_buffer[self._streamed_offset :]
                if unstreamed:
                    self._streamed_offset += len(unstreamed)
                    try:
                        self.on_text(unstreamed)
                    except Exception:
                        pass

    def _start_oversized(self, segment: bytes) -> None:
        self._oversized_capture = OversizedRecordCapture.create()
        if self._buffer:
            self._feed_oversized(bytes(self._buffer))
            self._buffer.clear()
        self._feed_oversized(segment)

    def _feed_oversized(self, segment: bytes) -> None:
        assert self._oversized_capture is not None
        self._oversized_capture.feed(segment)

    def _finish_oversized(self) -> None:
        assert self._oversized_capture is not None
        record = self._oversized_capture.finish()
        with self._lock:
            self._event_sequence += 1
            sequence = self._event_sequence
            if self.oversized_terminal_result is None:
                self.oversized_terminal_result = record
                if record.terminal_event:
                    self.terminal_result_monotonic = time.monotonic()
                    self.terminal_result_sequence = sequence
                    self._set_protocol_error(
                        "oversized terminal result observed; exact status unavailable "
                        "from bounded prefix",
                        sequence,
                    )
                else:
                    self._set_protocol_error(
                        "oversized provider record observed; terminal classification "
                        "unavailable from bounded prefix",
                        sequence,
                    )
        self._oversized_capture = None

    def _process_line(self, raw_line: bytes) -> None:
        with self._lock:
            self._event_sequence += 1
            sequence = self._event_sequence
        if len(raw_line) > self.max_record_bytes:
            with self._lock:
                self._set_protocol_error(
                    "provider output line exceeds maximum record size", sequence
                )
            return
        line = raw_line.strip()
        if not line:
            return
        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError as error:
            with self._lock:
                self._set_protocol_error(
                    f"malformed UTF-8 in provider output: {error}", sequence
                )
            return

        try:
            event = json.loads(text)
        except json.JSONDecodeError as error:
            with self._lock:
                self._set_protocol_error(
                    f"malformed JSON from provider: {error}", sequence
                )
            return

        if not isinstance(event, dict):
            with self._lock:
                self._set_protocol_error(
                    "malformed JSON from provider: event must be a JSON object",
                    sequence,
                )
            return

        if self.on_protocol is not None:
            try:
                self.on_protocol(_classify_protocol_event(event))
            except BaseException:
                pass

        event_name = event.get("type") or event.get("event")
        if event_name == "result":
            with self._lock:
                if self.raw_terminal_result is None:
                    self.raw_terminal_result = raw_line
                    self.terminal_result_monotonic = time.monotonic()
                    self.terminal_result_sequence = sequence
            self._handle_result_event(event, sequence)
            return

        agent_delta = _extract_agent_response_delta(event)
        if agent_delta is not None:
            self._handle_agent_response_delta(agent_delta, sequence)
        elif self.on_text:
            legacy_text = _extract_streaming_text(event)
            if legacy_text:
                self.on_text(legacy_text)

    def _handle_agent_response_delta(self, delta: str, sequence: int) -> None:
        with self._lock:
            if self.completed_by_fence:
                return

            self._response_buffer += delta
            if len(self._response_buffer.encode("utf-8")) > self.max_response_bytes:
                self._set_protocol_error(
                    f"agent response exceeds maximum response size of {self.max_response_bytes} bytes",
                    sequence,
                )
                return

            if self.fence_nonce is not None:
                fence_marker = format_completion_fence(self.fence_nonce)
                fence_regex = re.compile(
                    r"(?:\r?\n|^)[ \t]*"
                    + re.escape(fence_marker)
                    + r"[ \t]*(?:\r?\n|$)"
                )
                match = fence_regex.search(self._response_buffer)
                if match:
                    self.completed_by_fence = True
                    self.completion_fence_monotonic = time.monotonic()
                    self.completion_fence_sequence = sequence
                    self.fenced_response = self._response_buffer[: match.start()]
                    if self.on_text and match.start() > self._streamed_offset:
                        unstreamed = self._response_buffer[
                            self._streamed_offset : match.start()
                        ]
                        self._streamed_offset = match.start()
                        try:
                            self.on_text(unstreamed)
                        except Exception:
                            pass
                    return

            if self.on_text:
                unstreamed = self._response_buffer[self._streamed_offset :]
                holdback = 0
                if self.fence_nonce is not None:
                    fence_marker = format_completion_fence(self.fence_nonce)
                    candidate_idx = max(unstreamed.rfind("\n"), 0)
                    candidate_line = unstreamed[candidate_idx:].lstrip("\n \t")
                    if candidate_line and fence_marker.startswith(candidate_line):
                        holdback = len(unstreamed) - candidate_idx
                    elif not candidate_line and unstreamed.endswith("\n"):
                        holdback = 1

                to_stream = unstreamed[:-holdback] if holdback > 0 else unstreamed
                if to_stream:
                    self._streamed_offset += len(to_stream)
                    try:
                        self.on_text(to_stream)
                    except Exception:
                        pass

    def _handle_result_event(self, event: dict[str, Any], sequence: int) -> None:
        with self._lock:
            if self._result_event_seen:
                self._set_protocol_error(
                    "duplicate terminal result received from provider", sequence
                )
                return
            self._result_event_seen = True

            payload: dict[str, Any]
            if isinstance(event.get("result"), dict):
                payload = event["result"]
            else:
                payload = event

            status, status_source = _selected_field(event, payload, "status")
            subtype, subtype_source = _selected_field(event, payload, "subtype")
            is_error, _ = _selected_field(event, payload, "is_error")

            status_str = status.lower() if isinstance(status, str) else None
            subtype_str = subtype.lower() if isinstance(subtype, str) else None

            if status is not None and not isinstance(status, str):
                self._set_protocol_error(
                    "malformed result: status must be a string", sequence
                )
                return
            if subtype is not None and not isinstance(subtype, str):
                self._set_protocol_error(
                    "malformed result: subtype must be a string", sequence
                )
                return
            if is_error is not None and not isinstance(is_error, bool):
                self._set_protocol_error(
                    "malformed result: is_error must be a boolean", sequence
                )
                return

            all_allowed = (
                ALLOWED_SUCCESS_STATUSES
                | ALLOWED_ERROR_STATUSES
                | NON_TERMINAL_STATUSES
            )
            if status_str is not None and status_str not in all_allowed:
                self._set_protocol_error(
                    "provider reported unknown status in result: "
                    f"{_bounded_diagnostic_text(status)}",
                    sequence,
                )
                return
            if subtype_str is not None and subtype_str not in all_allowed:
                self._set_protocol_error(
                    "provider reported unknown subtype in result: "
                    f"{_bounded_diagnostic_text(subtype)}",
                    sequence,
                )
                return

            is_incomplete = (
                status_str in NON_TERMINAL_STATUSES
                or subtype_str in NON_TERMINAL_STATUSES
            )

            is_err: bool
            if is_incomplete or is_error is True:
                is_err = True
            elif status_str in ALLOWED_ERROR_STATUSES or subtype_str in ALLOWED_ERROR_STATUSES:
                is_err = True
            elif status_str in ALLOWED_SUCCESS_STATUSES or subtype_str in ALLOWED_SUCCESS_STATUSES or is_error is False:
                is_err = False
            elif "error" in payload or "error" in event:
                is_err = True
            elif (
                "response" in payload
                or "result" in event
                or "text" in payload
                or "content" in payload
            ):
                is_err = False
            else:
                self._set_protocol_error(
                    "ambiguous protocol: result event lacks status, is_error, result, or error",
                    sequence,
                )
                return

            response_text: str | None = None
            response_source: str | None = None
            malformed_response: str | None = None
            response_value, selected_response_source = _selected_field(
                event, payload, "response"
            )
            if selected_response_source is not None:
                if not isinstance(response_value, str):
                    self._set_protocol_error(
                        "malformed result: response must be a string", sequence
                    )
                    return
                response_text = response_value
                response_source = selected_response_source
            elif isinstance(event.get("result"), str):
                response_text = event["result"]
                response_source = "event.result"
            elif isinstance(payload.get("result"), str):
                response_text = payload["result"]
                response_source = (
                    "result.result" if payload is not event else "event.result"
                )
            elif isinstance(payload.get("text"), str):
                response_text = payload["text"]
                response_source = "result.text" if payload is not event else "event.text"
            elif "content" in payload:
                content_val = payload["content"]
                if isinstance(content_val, str):
                    response_text = content_val
                    response_source = (
                        "result.content" if payload is not event else "event.content"
                    )
                elif isinstance(content_val, list):
                    parts: list[str] = []
                    for part in content_val:
                        if (
                            isinstance(part, dict)
                            and part.get("type") == "text"
                            and isinstance(part.get("text"), str)
                        ):
                            parts.append(part["text"])
                        elif isinstance(part, str):
                            parts.append(part)
                        else:
                            malformed_response = "malformed result: invalid content item"
                            break
                    if malformed_response is None:
                        response_text = "".join(parts)
                        response_source = (
                            "result.content" if payload is not event else "event.content"
                        )
                else:
                    malformed_response = (
                        "malformed result: content must be string or list"
                    )

            if not is_err:
                if malformed_response is not None:
                    self._set_protocol_error(malformed_response, sequence)
                    return
                if response_text is None:
                    self._set_protocol_error(
                        "malformed result: missing result text payload in success result",
                        sequence,
                    )
                    return

            error_value, error_source = _selected_field(event, payload, "error")
            if error_value is None:
                error_value, error_source = _selected_field(
                    event, payload, "message"
                )
            try:
                error_text, error_source = _error_text_and_source(
                    error_value, error_source
                )
            except ValueError as error:
                self._set_protocol_error(str(error), sequence)
                return

            raw_status = status if isinstance(status, str) else subtype
            raw_status_source = status_source if isinstance(status, str) else subtype_source
            normalized_status = (
                status_str
                or subtype_str
                or ("error" if is_err else "success")
            )

            self.terminal_result = TerminalResult(
                raw_status=raw_status,
                status=normalized_status,
                response=response_text or "",
                error=error_text,
                is_error=is_err,
                is_incomplete=is_incomplete,
                status_source=raw_status_source,
                response_source=response_source,
                error_source=error_source,
            )


def terminate_process_group(process: subprocess.Popen[bytes], signum: int) -> bool:
    return _signal_process_group(process.pid, signum) == "sent"


def process_group_exists(process: subprocess.Popen[bytes]) -> bool:
    return _process_group_state(process.pid) != "absent"


def drain_stream(
    source: BinaryIO,
    target: BinaryIO,
    capture: StderrCapture | None = None,
    activity: ActivityPipeWriter | None = None,
) -> None:
    try:
        while chunk := source.read(65536):
            if activity is not None:
                activity.emit(ACTIVITY_STDERR_TOKEN)
            if capture is not None:
                capture.feed(chunk)
            target.write(chunk)
            target.flush()
    except Exception:
        pass
    finally:
        try:
            source.close()
        except Exception:
            pass


def process_stdout(
    source: BinaryIO,
    observer: StreamObserver,
    activity: ActivityPipeWriter | None = None,
) -> None:
    try:
        while chunk := source.read(65536):
            if activity is not None:
                activity.emit(ACTIVITY_STDOUT_TOKEN)
            observer.feed(chunk)
    except Exception as error:
        with observer._lock:
            observer._event_sequence += 1
            observer._set_protocol_error(
                f"error reading provider stdout: {error}", observer._event_sequence
            )
    finally:
        observer.finish()
        try:
            source.close()
        except Exception:
            pass


def run_supervised(
    command: Sequence[str],
    fence_nonce: str | None = None,
    post_result_grace: float | None = None,
    post_result_kill_grace: float | None = None,
    drain_grace: float | None = None,
    evidence_prefix: Path | None = None,
    profile_name: str = "",
    model: str = "",
    reviewer: bool = False,
) -> int:
    evidence_started_at = utc_now()
    evidence_started_monotonic = time.monotonic()
    evidence_agy_version: str | None = None
    if post_result_grace is None:
        post_result_grace = POST_RESULT_GRACE_SECONDS
    if post_result_kill_grace is None:
        post_result_kill_grace = POST_RESULT_KILL_GRACE_SECONDS
    if drain_grace is None:
        drain_grace = STREAM_DRAIN_GRACE_SECONDS

    activity = ActivityPipeWriter.from_environment()
    # Never expose the provider-to-wrapper descriptor to AGY, including through
    # the advisory version probe. The wrapper keeps the writer itself while
    # both nested subprocesses receive this sanitized environment.
    nested_environment = os.environ.copy()
    nested_environment.pop(ACTIVITY_PIPE_ENV, None)

    def on_stream_text(text: str) -> None:
        try:
            sys.stderr.write(text)
            sys.stderr.flush()
        except Exception:
            pass

    observer = StreamObserver(
        fence_nonce=fence_nonce,
        on_text=on_stream_text,
        on_protocol=(
            None
            if activity is None
            else lambda kind: activity.emit(
                ACTIVITY_PROTOCOL_TOKEN
                if kind == "progress"
                else ACTIVITY_WAITING_TOKEN
            )
        ),
    )
    stderr_capture = StderrCapture.create()

    received_signals: list[int] = []
    signal_events: list[dict[str, Any]] = []
    child_ref: list[subprocess.Popen[bytes] | None] = [None]
    previous_handlers: dict[int, Any] = {}
    process: subprocess.Popen[bytes] | None = None
    process_group_pgid: int | None = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    version_thread: threading.Thread | None = None
    version_cleanup_holder: list[dict[str, Any]] = []
    process_group_cleanup: dict[str, Any] | None = None

    def handle_signal(signum: int, _frame: Any) -> None:
        received_signals.append(signum)
        if child_ref[0] is not None:
            if terminate_process_group(child_ref[0], signum):
                signal_events.append({
                    "action": signal.Signals(signum).name,
                    "reason": "local-wrapper-signal",
                    "monotonic": time.monotonic(),
                })

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, handle_signal)

    returncode: int | None = None
    child_started = False
    child_exit_monotonic: float | None = None

    def write_evidence(
        wrapper_exit_code: int,
        *,
        current_observer: StreamObserver | None,
        protocol_error: str | None = None,
    ) -> None:
        if evidence_prefix is None:
            return
        write_terminal_evidence(
            evidence_prefix,
            profile=profile_name,
            model=model,
            reviewer=reviewer,
            command=command,
            observer=current_observer,
            stderr_capture=stderr_capture,
            started_at=evidence_started_at,
            ended_at=utc_now(),
            duration_seconds=time.monotonic() - evidence_started_monotonic,
            child_started=child_started,
            child_exit_code=returncode,
            wrapper_exit_code=wrapper_exit_code,
            received_signals=received_signals,
            signal_events=signal_events,
            child_exit_monotonic=child_exit_monotonic,
            protocol_error=protocol_error,
            agy_version=evidence_agy_version,
            process_group_cleanup=process_group_cleanup,
            version_probe_cleanup=(
                version_cleanup_holder[-1] if version_cleanup_holder else None
            ),
        )

    def signal_child(signum: int, reason: str) -> None:
        child = child_ref[0]
        if child is not None and terminate_process_group(child, signum):
            signal_events.append({
                "action": signal.Signals(signum).name,
                "reason": reason,
                "monotonic": time.monotonic(),
            })

    try:
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                start_new_session=True,
                env=nested_environment,
            )
        except OSError as error:
            write_evidence(
                2,
                current_observer=None,
                protocol_error=f"cannot start Antigravity CLI: {error}",
            )
            raise ProfileError(f"cannot start Antigravity CLI: {error}") from error

        child_ref[0] = process
        child_started = True
        process_group_pgid = _source_process_group(process)

        if activity is not None:
            try:
                nested_pgid = os.getpgid(process.pid)
                if nested_pgid == process.pid and os.getsid(process.pid) == process.pid:
                    activity.emit(
                        f"G:{process.pid}:{nested_pgid}\n".encode("ascii")
                    )
            except OSError:
                pass

        for signum in received_signals:
            signal_child(signum, "signal-received-before-child-started")

        assert process.stdout is not None
        assert process.stderr is not None

        stdout_thread = threading.Thread(
            target=process_stdout,
            args=(process.stdout, observer, activity),
            name="antigravity-stdout",
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=drain_stream,
            args=(process.stderr, sys.stderr.buffer, stderr_capture, activity),
            name="antigravity-stderr",
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        # Version metadata is advisory.  The supervised provider is already
        # running and supervision continues concurrently, so an absent,
        # failing, noisy, or slow probe cannot delay completion handling.
        def probe_version() -> None:
            nonlocal evidence_agy_version
            try:
                evidence_agy_version = agy_cli_version(
                    command[0] if command else "agy",
                    cancelled=lambda: bool(received_signals),
                    env=nested_environment,
                    cleanup_result=version_cleanup_holder,
                )
            except InterruptedError:
                evidence_agy_version = None
            except BaseException:
                evidence_agy_version = None
                if not version_cleanup_holder:
                    version_cleanup_holder.append({
                        **_cleanup_record_without_group("version-probe-exception"),
                        "attempted": True,
                        "group_absent": False,
                        "group_state": "unknown",
                        "cleanup_complete": False,
                        "failure_class": "version_probe_exception",
                    })

        version_thread = threading.Thread(
            target=probe_version,
            name="antigravity-version-probe",
            daemon=True,
        )
        version_thread.start()

        local_signal_deadline: float | None = None
        local_signal_term_forwarded = False
        while returncode is None:
            try:
                returncode = process.wait(timeout=0.05)
                child_exit_monotonic = time.monotonic()
                break
            except subprocess.TimeoutExpired:
                pass

            if received_signals:
                now = time.monotonic()
                if local_signal_deadline is None:
                    local_signal_deadline = now + post_result_grace
                elif len(received_signals) > 1:
                    # Repeated operator interruption accelerates bounded
                    # teardown but retains the first signal's classification.
                    local_signal_deadline = min(local_signal_deadline, now)
                if now >= local_signal_deadline:
                    if (
                        received_signals[0] != signal.SIGTERM
                        and not local_signal_term_forwarded
                    ):
                        signal_child(signal.SIGTERM, "local-wrapper-signal-term")
                        local_signal_term_forwarded = True
                        local_signal_deadline = now + post_result_kill_grace
                        continue
                    signal_child(signal.SIGKILL, "local-wrapper-signal-kill")
                    try:
                        returncode = process.wait(timeout=post_result_kill_grace)
                        child_exit_monotonic = time.monotonic()
                    except subprocess.TimeoutExpired:
                        returncode = -signal.SIGKILL
                    break
                continue

            if observer.has_completion:
                if observer.completed_by_fence:
                    signal_child(signal.SIGTERM, "completion-fence-observed")
                    term_deadline = time.monotonic() + post_result_grace
                    while time.monotonic() < term_deadline:
                        try:
                            returncode = process.wait(timeout=0.05)
                            child_exit_monotonic = time.monotonic()
                            break
                        except subprocess.TimeoutExpired:
                            pass
                    if returncode is None:
                        signal_child(signal.SIGKILL, "completion-fence-grace-expired")
                        try:
                            returncode = process.wait(timeout=post_result_kill_grace)
                            child_exit_monotonic = time.monotonic()
                        except subprocess.TimeoutExpired:
                            returncode = -signal.SIGKILL
                    break
                else:
                    deadline = time.monotonic() + post_result_grace
                    while time.monotonic() < deadline:
                        try:
                            returncode = process.wait(timeout=0.05)
                            child_exit_monotonic = time.monotonic()
                            break
                        except subprocess.TimeoutExpired:
                            pass
                    if returncode is not None:
                        break

                    signal_child(signal.SIGTERM, "terminal-result-grace-expired")
                    term_deadline = time.monotonic() + post_result_kill_grace
                    while time.monotonic() < term_deadline:
                        try:
                            returncode = process.wait(timeout=0.05)
                            child_exit_monotonic = time.monotonic()
                            break
                        except subprocess.TimeoutExpired:
                            pass
                    if returncode is not None:
                        break

                    signal_child(signal.SIGKILL, "terminal-result-kill-grace-expired")
                    try:
                        returncode = process.wait(timeout=post_result_kill_grace)
                        child_exit_monotonic = time.monotonic()
                    except subprocess.TimeoutExpired:
                        returncode = -signal.SIGKILL
                    break

    finally:
        if process is not None and child_started:
            try:
                process_group_cleanup = _finalize_process_group(
                    process,
                    process_group_pgid,
                    reason=(
                        "operator-interruption"
                        if received_signals
                        else "stream-drain-cleanup"
                    ),
                    term_grace=post_result_grace,
                    kill_grace=post_result_kill_grace,
                    readers=tuple(
                        reader
                        for reader in (
                            ("stdout", stdout_thread, process.stdout),
                            ("stderr", stderr_thread, process.stderr),
                        )
                        if reader[1] is not None and reader[2] is not None
                    ),
                )
            except BaseException:
                # Cleanup is a fail-closed boundary. Preserve the original
                # exception while retaining a bounded diagnostic record.
                process_group_cleanup = {
                    **_cleanup_record_without_group("cleanup-exception"),
                    "attempted": True,
                    "group_absent": False,
                    "group_state": "unknown",
                    "parent_reaped": process.poll() is not None,
                    "stdout_reader_joined": False,
                    "stderr_reader_joined": False,
                    "readers_joined": False,
                    "cleanup_complete": False,
                    "failure_class": "cleanup_exception",
                }
        if version_thread is not None:
            version_thread.join(
                timeout=(
                    VERSION_PROBE_TIMEOUT_SECONDS * 4
                    + PROCESS_GROUP_STATUS_TIMEOUT_SECONDS
                    + 0.2
                )
            )
            if version_thread.is_alive() and not version_cleanup_holder:
                version_cleanup_holder.append({
                    **_cleanup_record_without_group("version-probe-thread-not-joined"),
                    "attempted": True,
                    "group_absent": False,
                    "group_state": "unknown",
                    "cleanup_complete": False,
                    "failure_class": "version_probe_thread_not_joined",
                })
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        if activity is not None:
            activity.close()

    successful_output: str | None = None
    if received_signals:
        signum = received_signals[0]
        wrapper_exit = 128 + signum
    elif observer.completed_by_fence and observer.transport_success:
        successful_output = observer.fenced_response or ""
        wrapper_exit = 0
    elif observer.protocol_error is not None:
        print(f"antigravity-profile: {observer.protocol_error}", file=sys.stderr)
        wrapper_exit = 1
    elif observer.terminal_result is None:
        print(
            "antigravity-profile: provider exited without terminal result",
            file=sys.stderr,
        )
        wrapper_exit = 1 if returncode == 0 else (returncode if returncode is not None else 1)
    elif observer.terminal_result.is_error:
        status_label = _bounded_diagnostic_text(
            observer.terminal_result.raw_status
            or observer.terminal_result.status.upper()
        )
        if observer.terminal_result.is_incomplete:
            print(
                "antigravity-profile: provider reported recognized "
                f"incomplete/non-terminal status: {status_label}",
                file=sys.stderr,
            )
        else:
            print(
                f"antigravity-profile: provider ended with status {status_label}",
                file=sys.stderr,
            )
        if observer.terminal_result.error:
            print(
                "antigravity-profile: provider error: "
                f"{observer.terminal_result.error}",
                file=sys.stderr,
            )
        elif (
            observer.terminal_result.raw_status is None
            and observer.terminal_result.response
        ):
            print(observer.terminal_result.response, file=sys.stderr)
        wrapper_exit = 1
    else:
        successful_output = observer.terminal_result.response
        wrapper_exit = 0

    main_cleanup_complete = (
        process_group_cleanup is None
        or process_group_cleanup.get("cleanup_complete") is True
    )
    probe_cleanup_complete = all(
        cleanup.get("cleanup_complete") is True
        for cleanup in version_cleanup_holder
    )
    cleanup_proven = main_cleanup_complete and probe_cleanup_complete
    if not cleanup_proven:
        print(CLEANUP_FAILURE_DIAGNOSTIC, file=sys.stderr)
        if wrapper_exit == 0:
            wrapper_exit = 1
            successful_output = None

    write_evidence(wrapper_exit, current_observer=observer)
    if successful_output is not None:
        sys.stdout.write(successful_output)
        if not successful_output.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    return wrapper_exit


def main(
    argv: list[str] | None = None,
    fence_nonce: str | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description="Run one Antigravity headless prompt with a versioned profile.",
    )
    parser.add_argument("profile")
    parser.add_argument("-p", "--print", action="store_true", required=True)
    parser.add_argument(
        "--reviewer",
        action="store_true",
        help="run in read-only plan mode for reviewer invocations",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print constructed argv as JSON without resolving or starting agy",
    )
    parser.add_argument(
        "--evidence-prefix",
        help="wrapper-only private terminal-evidence prefix",
    )
    arguments = parser.parse_args(argv)
    antigravity_root = Path(__file__).resolve().parents[1] / "antigravity"
    evidence_prefix: Path | None = None
    if arguments.evidence_prefix is not None:
        evidence_prefix = Path(arguments.evidence_prefix)
        if not evidence_prefix.is_absolute() or not evidence_prefix.parent.is_dir():
            parser.error("evidence prefix must be absolute with an existing parent")
        if evidence_prefix.name in {"", ".", ".."}:
            parser.error("invalid evidence prefix")
    try:
        profile = load_profile(antigravity_root, arguments.profile)
        caller_prompt = decode_prompt(sys.stdin.buffer.read(MAX_PROMPT_BYTES + 1))
        nonce = fence_nonce if fence_nonce is not None else generate_fence_nonce()
        full_prompt = build_prompt(caller_prompt, nonce)
        command = build_agy_argv(profile, full_prompt, reviewer=arguments.reviewer)
        if arguments.dry_run:
            print(json.dumps(command, ensure_ascii=False))
            return 0
        return run_supervised(
            command,
            fence_nonce=nonce,
            evidence_prefix=evidence_prefix,
            profile_name=arguments.profile,
            model=profile.model,
            reviewer=arguments.reviewer,
        )
    except (ProfileError, EvidenceWriteError) as error:
        if evidence_prefix is not None:
            summary_path = evidence_prefix.with_name(
                f"{evidence_prefix.name}.antigravity-terminal-result.json"
            )
            if not summary_path.exists():
                capture = StderrCapture.create()
                write_terminal_evidence(
                    evidence_prefix,
                    profile=arguments.profile,
                    model="",
                    reviewer=arguments.reviewer,
                    command=["agy"],
                    observer=None,
                    stderr_capture=capture,
                    started_at=utc_now(),
                    ended_at=utc_now(),
                    duration_seconds=0.0,
                    child_started=False,
                    child_exit_code=None,
                    wrapper_exit_code=2,
                    received_signals=[],
                    signal_events=[],
                    child_exit_monotonic=None,
                    protocol_error=str(error),
                )
        parser.error(str(error))
    except OSError as error:
        parser.error(f"cannot start Antigravity CLI: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
