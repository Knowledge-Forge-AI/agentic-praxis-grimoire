"""Detached supervisor process executing an admitted Gemini worker job.

Supervises antigravity-profile as a leaf job, captures structured results,
ensures process-group cleanup, and updates the capacity ledger.
"""

from __future__ import annotations

import argparse
import inspect
import json
import hashlib
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .adapter import validate_mutation_scope
from .leaf_assignment import build_leaf_prompt as build_leaf_prompt, get_changed_paths as get_changed_paths
from .claude_external import (
    build_claude_argv,
    classify_quota_evidence as claude_classify_quota,
    load_sonnet_profile,
    parse_claude_events as parse_claude_events,
)
from .codex_external import (
    build_codex_exec_argv,
    classify_quota_evidence,
    load_luna_profile,
    parse_codex_events as parse_codex_events,
)
from .ledger import AuthorityViolationError, LedgerError, ParentLedger
from agent_phase.provider import ACTIVITY_PIPE_ENV, _drain_activity

RESULT_SCHEMA = "agent-worker-result-v1"
TERM_TO_KILL_GRACE_SECONDS = 2.0
KILL_REAP_GRACE_SECONDS = 2.0
STREAM_DRAIN_GRACE_SECONDS = 1.0
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_cleanup_attestation(evidence_prefix: Path) -> tuple[bool, str | None]:
    """Read the Antigravity wrapper's bounded process-cleanup evidence."""
    summary_path = evidence_prefix.with_name(
        f"{evidence_prefix.name}.antigravity-terminal-result.json"
    )
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False, None
    if not isinstance(summary, Mapping):
        return False, str(summary_path)
    process_cleanup = summary.get("process_group_cleanup")
    version_cleanup = summary.get("version_probe_cleanup")
    proven = (
        isinstance(process_cleanup, Mapping)
        and process_cleanup.get("cleanup_complete") is True
        and isinstance(version_cleanup, Mapping)
        and version_cleanup.get("cleanup_complete") is True
    )
    return bool(proven), str(summary_path)


def _provider_pgid(child_proc: Any) -> int | None:
    """Read a provider process group without assuming a real ``Popen`` object."""
    pid = getattr(child_proc, "pid", None)
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        return os.getpgid(pid)
    except (OSError, ProcessLookupError):
        return None


def _signal_provider(
    child_proc: Any,
    signum: int,
    provider_pgid: int | None = None,
) -> bool:
    """Signal the owned provider group, falling back to its process object."""
    sent = False
    # Both transports use ``start_new_session``.  Never signal the supervisor's
    # own group when a test double or a failed handoff reports its PID instead.
    if provider_pgid is not None and provider_pgid != os.getpgrp():
        try:
            os.killpg(provider_pgid, signum)
            sent = True
        except (OSError, ProcessLookupError):
            pass
    if sent:
        return True
    try:
        if signum == signal.SIGTERM:
            child_proc.terminate()
        else:
            child_proc.kill()
        return True
    except (AttributeError, OSError, ProcessLookupError):
        return False


def _provider_group_present(provider_pgid: int | None) -> bool | None:
    """Return group liveness, preserving unknown when no group identity exists."""
    if provider_pgid is None or provider_pgid <= 0:
        return None
    if provider_pgid == os.getpgrp():
        return None
    try:
        os.killpg(provider_pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    except OSError:
        return False
    return True


def _provider_poll(child_proc: Any) -> int | None:
    """Poll a real process or a minimal provider test double."""
    try:
        return child_proc.poll()
    except (AttributeError, OSError):
        value = getattr(child_proc, "returncode", None)
        return value if isinstance(value, int) else None


def terminate_and_reap_child(
    child_proc: subprocess.Popen[Any],
    provider_pgid: int | None = None,
    nested_groups: Mapping[int, int] | None = None,
    nested_lock: threading.Lock | None = None,
    activity_thread: threading.Thread | None = None,
    activity_read_fd: int | None = None,
) -> dict[str, Any]:
    """TERM then finitely KILL an explicitly cancelled provider group.

    This helper is only an execution-side stop path.  It has no inactivity
    timeout and is never used to infer a stalled provider during ordinary
    execution.  The returned fields let the caller distinguish an observed
    wait result from cleanup that is still unknown.  The activity reader owns
    ``activity_read_fd`` after its thread starts; this helper deliberately does
    not close that descriptor because a later open could reuse its number.
    """
    if provider_pgid is None:
        provider_pgid = _provider_pgid(child_proc)
    def snapshot_nested() -> dict[int, int]:
        if nested_lock is None:
            return dict(nested_groups or {})
        with nested_lock:
            return dict(nested_groups or {})

    def signal_nested(groups: Mapping[int, int], signum: int) -> list[int]:
        sent: list[int] = []
        for pgid in groups:
            try:
                if pgid != os.getpgrp():
                    os.killpg(pgid, signum)
                    sent.append(pgid)
            except (OSError, ProcessLookupError):
                pass
        return sent

    term_sent = _signal_provider(child_proc, signal.SIGTERM, provider_pgid)
    nested_snapshot = snapshot_nested()
    nested_term_sent = signal_nested(nested_snapshot, signal.SIGTERM)
    wait_completed = False
    kill_sent = False
    nested_kill_sent: list[int] = []
    try:
        child_proc.wait(timeout=TERM_TO_KILL_GRACE_SECONDS)
        wait_completed = True
    except subprocess.TimeoutExpired:
        kill_sent = _signal_provider(child_proc, signal.SIGKILL, provider_pgid)
        nested_snapshot = snapshot_nested()
        nested_kill_sent = signal_nested(nested_snapshot, signal.SIGKILL)
        try:
            child_proc.wait(timeout=KILL_REAP_GRACE_SECONDS)
            wait_completed = True
        except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
            pass
    except (AttributeError, OSError, ProcessLookupError):
        pass
    if activity_thread is not None and activity_thread.is_alive():
        # Allow tokens written during the TERM/wait window to register their
        # exact nested process groups before taking the final KILL snapshot.
        activity_thread.join(timeout=0.1)
    late_groups = snapshot_nested()
    if late_groups != nested_snapshot:
        nested_snapshot = late_groups
        if wait_completed:
            nested_term_sent.extend(
                pgid for pgid in signal_nested(nested_snapshot, signal.SIGTERM)
                if pgid not in nested_term_sent
            )
        if not kill_sent:
            still_present = [
                pgid for pgid in nested_snapshot
                if _provider_group_present(pgid) is True
            ]
            if still_present:
                nested_kill_sent.extend(
                    pgid for pgid in signal_nested(
                        {pgid: nested_snapshot[pgid] for pgid in still_present},
                        signal.SIGKILL,
                    )
                    if pgid not in nested_kill_sent
                )
    if wait_completed and not nested_kill_sent:
        lingering_groups = {
            pgid: nested_snapshot[pgid]
            for pgid in nested_snapshot
            if _provider_group_present(pgid) is True
        }
        nested_kill_sent = signal_nested(lingering_groups, signal.SIGKILL)
    kill_sent = kill_sent or bool(nested_kill_sent)
    if activity_thread is not None:
        activity_thread.join(timeout=KILL_REAP_GRACE_SECONDS)
    nested_present = {
        str(pgid): _provider_group_present(pgid) for pgid in nested_snapshot
    }
    return {
        "term_sent": term_sent,
        "kill_sent": kill_sent,
        "wait_completed": wait_completed,
        "group_present": _provider_group_present(provider_pgid),
        "nested_groups": nested_snapshot,
        "nested_term_sent": nested_term_sent,
        "nested_kill_sent": nested_kill_sent,
        "nested_group_present": nested_present,
        "activity_reader_joined": activity_thread is None or not activity_thread.is_alive(),
    }


def _ledger_method(ledger: ParentLedger, worker_kind: str, operation: str) -> Any:
    """Select the generic or provider-specific ledger operation.

    Existing Gemini ledgers expose ``*_gemini`` methods.  The fixed dual-pool
    ledger may expose generic ``*_worker`` or ``*_luna`` methods; accepting all
    three keeps old journals readable while the parent-owned ledger evolves.
    """
    names_by_operation = {
        "bind_supervisor": [
            "bind_worker_supervisor",
            f"bind_{worker_kind}_supervisor",
        ],
        "settle_supervisor_rejection": [
            "settle_worker_supervisor_rejection",
            f"settle_{worker_kind}_supervisor_rejection",
        ],
        "record_provider_custody": [
            "record_provider_custody",
            f"record_{worker_kind}_provider_custody",
        ],
        "update_status": [
            "update_worker_status",
            f"update_{worker_kind}_status",
        ],
        "pause_pool": ["pause_pool"],
    }
    names = names_by_operation.get(operation, [operation])
    if worker_kind == "gemini":
        names.extend(
            {
                "bind_supervisor": ["bind_gemini_supervisor"],
                "settle_supervisor_rejection": ["settle_gemini_supervisor_rejection"],
                "update_status": ["update_gemini_status"],
            }.get(operation, [])
        )
    for name in dict.fromkeys(names):
        method = getattr(ledger, name, None)
        if callable(method):
            return method
    return None


def _call_ledger(
    ledger: ParentLedger,
    worker_kind: str,
    operation: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Call a worker ledger operation while preserving old method signatures."""
    method = _ledger_method(ledger, worker_kind, operation)
    if method is None:
        raise AttributeError(f"ledger has no {operation} operation for {worker_kind}")
    try:
        signature = inspect.signature(method)
        accepts_kind = "worker_kind" in signature.parameters or any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
    except (TypeError, ValueError):
        accepts_kind = False
    call_kwargs = dict(kwargs)
    if accepts_kind:
        call_kwargs.setdefault("worker_kind", worker_kind)
    return method(*args, **call_kwargs)


class _IncrementalCapture:
    """Persist every stream byte while bounding result memory."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.file = path.open("wb")
        os.chmod(path, 0o600)
        self.data = bytearray()
        self.total_bytes = 0
        self.truncated = False

    def append(self, chunk: bytes | str) -> None:
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8", errors="replace")
        if not isinstance(chunk, bytes):
            chunk = bytes(chunk)
        self.total_bytes += len(chunk)
        self.file.write(chunk)
        self.file.flush()
        if len(self.data) < MAX_RESPONSE_BYTES:
            remaining = MAX_RESPONSE_BYTES - len(self.data)
            self.data.extend(chunk[:remaining])
            if len(chunk) > remaining:
                self.truncated = True
        else:
            self.truncated = True

    def close(self) -> None:
        try:
            self.file.flush()
        finally:
            self.file.close()


def _reader_thread(
    stream: Any,
    capture: _IncrementalCapture,
    errors: list[str],
) -> None:
    """Read one provider pipe incrementally until EOF or a close error."""
    try:
        read = getattr(stream, "read1", None)
        if not callable(read):
            read = stream.read
        while True:
            chunk = read(65536)
            if not chunk:
                return
            capture.append(chunk)
    except (AttributeError, OSError, TypeError, ValueError) as error:
        errors.append(str(error))


def _close_stream(stream: Any) -> None:
    try:
        if stream is not None:
            if isinstance(stream, int):
                os.close(stream)
            else:
                stream.close()
    except (AttributeError, OSError, ValueError):
        pass


def _run_provider_process(
    child_proc: Any,
    prompt: str,
    cancelled: list[bool],
    stdout_capture: _IncrementalCapture,
    stderr_capture: _IncrementalCapture,
    nested_groups: dict[int, int] | None = None,
    nested_lock: threading.Lock | None = None,
    activity_thread: threading.Thread | None = None,
    activity_read_fd: int | None = None,
) -> dict[str, Any]:
    """Run a provider with incremental readers and bounded cancellation cleanup.

    Activity-reader descriptor ownership stays with the reader thread.  The
    supervisor closes only a setup descriptor for which no reader was started.
    """
    provider_pgid = _provider_pgid(child_proc)
    stdout_stream = getattr(child_proc, "stdout", None)
    stderr_stream = getattr(child_proc, "stderr", None)
    stdin_stream = getattr(child_proc, "stdin", None)
    reader_errors: list[str] = []
    readers: list[threading.Thread] = []
    communication: dict[str, Any] = {}

    if stdout_stream is not None or stderr_stream is not None:
        for stream, capture in (
            (stdout_stream, stdout_capture),
            (stderr_stream, stderr_capture),
        ):
            if stream is None:
                continue
            reader = threading.Thread(
                target=_reader_thread,
                args=(stream, capture, reader_errors),
                name="agent-worker-provider-reader",
                daemon=True,
            )
            reader.start()
            readers.append(reader)
        if stdin_stream is not None:
            try:
                payload = prompt.encode("utf-8")
                try:
                    stdin_stream.write(payload)
                except TypeError:
                    stdin_stream.write(prompt)
                stdin_stream.flush()
            except (BrokenPipeError, OSError, ValueError) as error:
                reader_errors.append(f"stdin: {error}")
            finally:
                _close_stream(stdin_stream)
        while True:
            try:
                returncode = child_proc.poll()
            except (AttributeError, OSError):
                returncode = None
            if cancelled[0] or returncode is not None:
                break
            # This is a polling interval only; provider silence does not stop
            # the job.  A parent cancellation is the sole stop trigger.
            time.sleep(0.02)
        cleanup = (
            terminate_and_reap_child(
                child_proc,
                provider_pgid,
                nested_groups,
                nested_lock,
                activity_thread,
                activity_read_fd,
            )
            if cancelled[0]
            else {"term_sent": False, "kill_sent": False, "wait_completed": True,
                  "group_present": _provider_group_present(provider_pgid)}
        )
        if activity_thread is not None:
            activity_thread.join(timeout=STREAM_DRAIN_GRACE_SECONDS)
        for reader in readers:
            reader.join(timeout=STREAM_DRAIN_GRACE_SECONDS)
        if any(reader.is_alive() for reader in readers):
            # Closing the parent's descriptors unblocks inherited-pipe cases;
            # output already persisted remains valid partial evidence.
            _close_stream(stdout_stream)
            _close_stream(stderr_stream)
            for reader in readers:
                reader.join(timeout=0.1)
            cleanup["stream_drain_complete"] = False
        else:
            cleanup["stream_drain_complete"] = True
        try:
            returncode = child_proc.returncode
        except AttributeError:
            returncode = child_proc.poll()
        cleanup["returncode"] = returncode
        cleanup["provider_pid"] = getattr(child_proc, "pid", None)
        cleanup["provider_pgid"] = provider_pgid
        cleanup["reader_errors"] = reader_errors
        if nested_lock is None:
            nested_snapshot = dict(nested_groups or {})
        else:
            with nested_lock:
                nested_snapshot = dict(nested_groups or {})
        cleanup["nested_groups"] = nested_snapshot
        cleanup["nested_group_present"] = {
            str(pgid): _provider_group_present(pgid) for pgid in nested_snapshot
        }
        cleanup["activity_reader_joined"] = (
            activity_thread is None or not activity_thread.is_alive()
        )
        return cleanup

    # Small process doubles in the historical tests do not expose pipes.  Keep
    # that compatibility path bounded by a helper thread so a broken
    # ``communicate`` implementation cannot pin the supervisor forever.
    def communicate() -> None:
        try:
            value = child_proc.communicate(input=prompt.encode("utf-8"))
            communication["value"] = value
        except Exception as error:  # noqa: BLE001 - provider boundary evidence
            communication["error"] = error

    worker = threading.Thread(target=communicate, name="agent-worker-communicate", daemon=True)
    worker.start()
    while worker.is_alive():
        if cancelled[0]:
            break
        time.sleep(0.02)
    try:
        process_still_running = child_proc.poll() is None
    except (AttributeError, OSError):
        process_still_running = False
    cleanup_needed = (
        cancelled[0]
        or worker.is_alive()
        or (communication.get("error") is not None and process_still_running)
    )
    cleanup = (
        terminate_and_reap_child(
            child_proc,
            provider_pgid,
            nested_groups,
            nested_lock,
            activity_thread,
            activity_read_fd,
        )
        if cleanup_needed
        else {"term_sent": False, "kill_sent": False, "wait_completed": True,
              "group_present": _provider_group_present(provider_pgid)}
    )
    worker.join(timeout=0.1)
    value = communication.get("value")
    if isinstance(value, tuple):
        if len(value) > 0 and value[0]:
            stdout_capture.append(value[0])
        if len(value) > 1 and value[1]:
            stderr_capture.append(value[1])
    if communication.get("error") is not None:
        cleanup["error"] = str(communication["error"])
    try:
        cleanup["returncode"] = child_proc.returncode
    except AttributeError:
        cleanup["returncode"] = child_proc.poll()
    cleanup["provider_pid"] = getattr(child_proc, "pid", None)
    cleanup["provider_pgid"] = provider_pgid
    cleanup["reader_errors"] = reader_errors
    if nested_lock is None:
        nested_snapshot = dict(nested_groups or {})
    else:
        with nested_lock:
            nested_snapshot = dict(nested_groups or {})
    cleanup["nested_groups"] = nested_snapshot
    cleanup.setdefault(
        "nested_group_present",
        {str(pgid): _provider_group_present(pgid) for pgid in nested_snapshot},
    )
    cleanup["activity_reader_joined"] = (
        activity_thread is None or not activity_thread.is_alive()
    )
    cleanup["stream_drain_complete"] = not worker.is_alive()
    return cleanup


def run_supervisor(
    parent_id: str,
    job_id: str,
    task_file: Path,
    state_dir: Path | None = None,
) -> int:
    ledger = ParentLedger(parent_id, state_dir)
    supervisor_pid = os.getpid()
    supervisor_pgid = os.getpgrp()
    worker_kind = "gemini"

    def settle_prebind_failure(error: str) -> int:
        """Settle only this recorded, still-unbound supervisor owner."""
        try:
            _call_ledger(
                ledger,
                worker_kind,
                "settle_supervisor_rejection",
                job_id,
                supervisor_pid,
                error=error,
            )
        except AttributeError:
            # Preserve conservative custody when a malformed handoff targets
            # a legacy journal without the provider-specific operation.
            pass
        return 1

    # Load and validate the explicit handoff.  User task text remains data;
    # only the selected fixed provider launcher receives it through stdin.
    try:
        raw_task = json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as error:
        return settle_prebind_failure(f"cannot read task file: {error}")
    if not isinstance(raw_task, Mapping):
        return settle_prebind_failure("task file must contain an object")

    try:
        workspace_value = raw_task.get("workspace", ".")
        task_authority = raw_task.get("task_authority", "read_only")
        worker_kind = raw_task.get("worker_kind", "gemini")
        mutation_scope = raw_task.get("mutation_scope") or []
        if isinstance(mutation_scope, list):
            mutation_scope = validate_mutation_scope(mutation_scope)
        acceptance_criteria = raw_task.get("acceptance_criteria") or ""
        profile = raw_task.get("profile")
        if not isinstance(profile, str) or not profile.strip():
            raise AuthorityViolationError("missing worker profile in task handoff")
        task_text = raw_task.get("task", "")
        if (
            not isinstance(workspace_value, (str, Path))
            or not str(workspace_value)
            or worker_kind not in {"gemini", "luna", "sonnet"}
            or task_authority not in {"read_only", "mutation_capable"}
            or not isinstance(mutation_scope, list)
            or task_authority == "mutation_capable" and not mutation_scope
            or not isinstance(acceptance_criteria, str)
            or not isinstance(profile, str)
            or not isinstance(task_text, str)
            or not task_text.strip()
        ):
            raise AuthorityViolationError("invalid worker task handoff")

        workspace = Path(workspace_value).expanduser().resolve()
        output_dir = Path(raw_task.get("output_dir", task_file.parent)).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        source_root = Path(__file__).resolve().parents[2]
        from agent_phase.runtime_models import selection
        provider_name = (
            "codex" if worker_kind == "luna"
            else "claude" if worker_kind == "sonnet"
            else "antigravity"
        )
        requested_selection = selection(source_root, provider_name, profile)
        luna_profile = (
            load_luna_profile(source_root, profile) if worker_kind == "luna" else None
        )
        sonnet_profile = (
            load_sonnet_profile(source_root, profile) if worker_kind == "sonnet" else None
        )
    except Exception as error:
        return settle_prebind_failure(str(error))
    stdout_path = output_dir / f"{job_id}.stdout.md"
    stderr_path = output_dir / f"{job_id}.stderr.log"
    result_path = output_dir / f"{job_id}.result.json"

    # Install the stop handler before self-admission.  The launcher records a
    # separate ``launched`` handoff and cancellation never signals that window.
    # Once this handler is live, a bind is the point at which TERM can safely
    # reach the supervisor and its provider wrapper.
    child_proc: subprocess.Popen[bytes] | None = None
    cancelled = [False]
    provider_pgid_box: list[int | None] = [None]

    def sigterm_handler(signum: int, frame: Any) -> None:
        del signum, frame
        cancelled[0] = True
        child = child_proc
        if child is not None and _provider_poll(child) is None:
            _signal_provider(child, signal.SIGTERM, provider_pgid_box[0])

    previous_handler = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, sigterm_handler)

    if not _call_ledger(
        ledger,
        worker_kind,
        "bind_supervisor",
        job_id,
        supervisor_pid,
        supervisor_pgid,
    ):
        # Cancellation, parent drain, or another supervisor may have won the
        # bind race.  Only this process's recorded unbound handoff may settle
        # the job; a loser must leave the live owner's record untouched.
        signal.signal(signal.SIGTERM, previous_handler)
        _call_ledger(
            ledger,
            worker_kind,
            "settle_supervisor_rejection",
            job_id,
            supervisor_pid,
            error="parent closed before supervisor bind",
        )
        return 1

    # The supervisor is an internal manager.  The provider receives a scrubbed
    # environment and owns its own process group.  Authentication remains in
    # the inherited Codex home; parent facade and session identity do not.
    child_env = os.environ.copy()
    for key in (
        "APGR_PARENT_ID",
        "APGR_WORKER_PARENT_TOKEN",
        "APGR_WORKER_STATE_DIR",
        "APGR_WORKER_FACADE",
        "APGR_WORKER_SOURCE_ROOT",
        "APGR_WORKER_WORKSPACE",
        "APGR_WORKER_PARENT_FAMILY",
        "APGR_WORKER_TASK_AUTHORITY",
        "APGR_WORKER_LIFECYCLE_GENERATION",
        "APGR_WORKER_PROFILE",
        "CODEX_THREAD_ID",
        "CODEX_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
    ):
        child_env.pop(key, None)
    for key in list(child_env.keys()):
        if key.startswith("AGENT_CENTRAL"):
            child_env.pop(key, None)
    child_env["APGR_WORKER_LEAF"] = "1"
    if worker_kind == "sonnet":
        from .claude_external import scrub_leaf_environment
        child_env = scrub_leaf_environment(child_env)
    activity_read_fd: int | None = None
    activity_write_fd: int | None = None
    activity_thread: threading.Thread | None = None
    nested_groups: dict[int, int] = {}
    nested_lock = threading.Lock()
    activity_setup_error: str | None = None
    activity: dict[str, Any] = {
        "last": time.monotonic(),
        "stream": None,
        "reads": 0,
        "bytes": 0,
        "kinds": {
            "stdout": 0,
            "stderr": 0,
            "nested.stdout": 0,
            "nested.stderr": 0,
            "nested.protocol": 0,
        },
        "non_progress": {
            "nested.pgid": 0,
            "waiting": 0,
            "unknown": 0,
            "oversized": 0,
            "partial": 0,
            "discarded": 0,
        },
    }
    if worker_kind == "gemini":
        try:
            activity_read_fd, activity_write_fd = os.pipe()
            child_env[ACTIVITY_PIPE_ENV] = str(activity_write_fd)
        except OSError as error:
            activity_setup_error = f"activity pipe setup: {error}"

    root = Path(__file__).resolve().parents[2]
    evidence_prefix: Path | None = None
    if worker_kind == "luna":
        assert luna_profile is not None
        argv = build_codex_exec_argv(luna_profile, workspace, task_authority)
    elif worker_kind == "sonnet":
        assert sonnet_profile is not None
        argv = build_claude_argv(
            sonnet_profile,
            workspace,
            task_authority,
            mutation_scope=mutation_scope if task_authority == "mutation_capable" else None,
        )
    else:
        launcher = root / "bin/antigravity-profile"
        if not launcher.exists() or not os.access(launcher, os.X_OK):
            launcher_cmd = [sys.executable, str(root / "libexec/antigravity_profile.py")]
        else:
            launcher_cmd = [str(launcher)]
        argv = [*launcher_cmd, profile, "-p"]
        if task_authority == "read_only":
            argv.append("--reviewer")
        evidence_prefix = output_dir / f"{job_id}.antigravity"
        argv.extend(["--evidence-prefix", str(evidence_prefix)])

    prompt_text = build_leaf_prompt(
        task=task_text,
        task_authority=task_authority,
        mutation_scope=mutation_scope,
        acceptance_criteria=acceptance_criteria,
        worker_kind=worker_kind,
    )
    started_at = utc_now_iso()
    started_mono = time.monotonic()
    error_message: str | None = None
    child_started = False
    stdout_capture = _IncrementalCapture(stdout_path)
    stderr_capture = _IncrementalCapture(stderr_path)
    execution: dict[str, Any] = {
        "returncode": None,
        "wait_completed": False,
        "group_present": None,
        "stream_drain_complete": False,
        "reader_errors": [],
    }
    provider_custody_error: str | None = None
    try:
        # A stop may have arrived immediately after bind.  Check before
        # Popen, then check again after Popen so a signal in that narrow window
        # terminates the owned wrapper before it can continue provider work.
        if not cancelled[0]:
            if activity_setup_error is not None:
                raise OSError(activity_setup_error)
            child_proc = subprocess.Popen(
                argv,
                cwd=workspace,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=child_env,
                close_fds=True,
                start_new_session=True,
                pass_fds=(activity_write_fd,) if activity_write_fd is not None else (),
            )
            child_started = True
            _close_stream(activity_write_fd)
            activity_write_fd = None
            provider_pgid_box[0] = _provider_pgid(child_proc)
            child_pid = getattr(child_proc, "pid", None)
            if isinstance(child_pid, int) and child_pid > 0:
                try:
                    custody = _call_ledger(
                        ledger,
                        worker_kind,
                        "record_provider_custody",
                        job_id,
                        child_pid,
                        provider_pgid_box[0],
                        supervisor_pid=supervisor_pid,
                    )
                    if custody is False:
                        provider_custody_error = "provider custody was not persisted"
                except (AttributeError, LedgerError, OSError, ValueError) as error:
                    # Retain provider output while refusing to claim cleanup
                    # proof when the independent group identity was not
                    # persisted.  The ledger remains occupied for recovery.
                    provider_custody_error = str(error)
            if activity_read_fd is not None and isinstance(child_pid, int):
                # The activity reader owns this descriptor and closes it in
                # ``_drain_activity``.  Clear the supervisor's handle after a
                # successful start so cleanup paths cannot close the same
                # numeric descriptor again after the reader (or an unrelated
                # later open) has reused it.
                activity_thread = threading.Thread(
                    target=_drain_activity,
                    args=(
                        activity_read_fd,
                        child_pid,
                        nested_lock,
                        activity,
                        nested_groups,
                    ),
                    name="agent-worker-antigravity-activity",
                    daemon=True,
                )
                activity_thread.start()
                activity_read_fd = None
        if cancelled[0] and _provider_poll(child_proc) is None:
            _signal_provider(child_proc, signal.SIGTERM, provider_pgid_box[0])
        execution = _run_provider_process(
            child_proc,
            prompt_text,
            cancelled,
            stdout_capture,
            stderr_capture,
            nested_groups,
            nested_lock,
            activity_thread,
            activity_read_fd,
        )
        if provider_custody_error is not None:
            execution["provider_custody_error"] = provider_custody_error
    except Exception as error:
        error_message = f"execution failed: {error}"
        if child_started and child_proc is not None:
            execution = terminate_and_reap_child(
                child_proc,
                provider_pgid_box[0],
                nested_groups,
                nested_lock,
                activity_thread,
                activity_read_fd,
            )
            if provider_custody_error is not None:
                execution["provider_custody_error"] = provider_custody_error
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        _close_stream(activity_write_fd)
        if activity_thread is None:
            # No reader successfully took ownership.  The supervisor retains
            # the setup descriptor only for this pre-reader failure path.
            _close_stream(activity_read_fd)
        stdout_capture.close()
        stderr_capture.close()

    ended_at = utc_now_iso()
    duration = time.monotonic() - started_mono
    stdout_data = bytes(stdout_capture.data)
    stderr_data = bytes(stderr_capture.data)
    exit_code = execution.get("returncode")
    if not isinstance(exit_code, int):
        exit_code = _provider_poll(child_proc) if child_proc is not None else 1
    cleanup_evidence: str | None = None
    if not child_started:
        cleanup_proven = True
    elif worker_kind == "gemini" and evidence_prefix is not None:
        cleanup_proven, cleanup_evidence = read_cleanup_attestation(evidence_prefix)
        nested_presence = execution.get("nested_group_present") or {}
        nested_clear = all(value is False for value in nested_presence.values())
        cleanup_proven = (
            cleanup_proven
            and execution.get("wait_completed") is True
            and execution.get("activity_reader_joined") is not False
            and nested_clear
        )
    else:
        cleanup_proven = (
            execution.get("wait_completed") is True
            and execution.get("stream_drain_complete") is True
            and execution.get("group_present") is False
        )
    provider_identifiers: dict[str, Any] = {}
    gemini_terminal_event: dict[str, Any] | None = None
    summary: dict[str, Any] = {}
    if cleanup_evidence:
        try:
            summary = json.loads(Path(cleanup_evidence).read_text(encoding="utf-8"))
            if not isinstance(summary, dict):
                summary = {}
            identifiers = summary.get("identifier_fields", {})
            for key in ("conversation_id", "session_id"):
                record = identifiers.get(key)
                if isinstance(record, dict) and isinstance(record.get("text"), str):
                    provider_identifiers[key] = record
            raw_artifact = summary.get("raw_result_artifact")
            if raw_artifact:
                raw_path = Path(cleanup_evidence).parent / raw_artifact
                if raw_path.is_file():
                    try:
                        raw_bytes = raw_path.read_bytes()
                        if hashlib.sha256(raw_bytes).hexdigest() != summary.get("raw_result_sha256"):
                            raise ValueError("terminal artifact digest mismatch")
                        raw_data = json.loads(raw_bytes)
                        if isinstance(raw_data, dict):
                            gemini_terminal_event = raw_data
                    except (OSError, UnicodeDecodeError, ValueError):
                        pass
        except (OSError, ValueError, AttributeError):
            pass
    from .model_observation import external_events
    codex_events = external_events("luna", stdout_data) if worker_kind == "luna" else {}
    claude_events = external_events("sonnet", stdout_data) if worker_kind == "sonnet" else {}
    provider_identifiers.update((codex_events or claude_events).get("provider_identifiers") or {})

    gemini_model: str | None = None
    gemini_effort: str | None = None
    if worker_kind == "gemini" and gemini_terminal_event is not None:
        res = gemini_terminal_event.get("result")
        payload = res if isinstance(res, dict) else gemini_terminal_event
        if isinstance(payload.get("model"), str) and payload["model"].strip():
            gemini_model = payload["model"].strip()
        effort = payload.get("effort", payload.get("reasoning_effort"))
        if isinstance(effort, str) and effort.strip():
            gemini_effort = effort.strip()

    requested_model = requested_selection.get("model")
    requested_effort = requested_selection.get("effort")
    if worker_kind == "luna":
        effective_model = codex_events.get("effective_model") if codex_events else None
        effective_effort = codex_events.get("effective_effort") if codex_events else None
    elif worker_kind == "sonnet":
        effective_model = claude_events.get("effective_model") if claude_events else None
        effective_effort = claude_events.get("effective_effort") if claude_events else None
    elif worker_kind == "gemini":
        effective_model = gemini_model
        effective_effort = gemini_effort
    else:
        effective_model = None
        effective_effort = None
    model_mismatch = bool(
        requested_model and effective_model and requested_model != effective_model
    )
    effort_mismatch = bool(
        requested_effort and effective_effort and requested_effort != effective_effort
    )
    sonnet_protocol_failure = worker_kind == "sonnet" and (not claude_events.get("terminal_result") or claude_events.get("provider_error")
        or len(claude_events.get("observed_models", [])) > 1
        or len(claude_events.get("observed_efforts", [])) > 1)
    if sonnet_protocol_failure:
        error_message = error_message or "Sonnet provider result missing, failed, or conflicting"
    if model_mismatch or effort_mismatch:
        detail = "model" if model_mismatch else "reasoning effort"
        error_message = error_message or f"provider selected unexpected {detail}"
    reader_errors = execution.get("reader_errors") or []
    if reader_errors and not error_message:
        error_message = "provider stream read failed: " + "; ".join(map(str, reader_errors))
    if execution.get("error") is not None and not error_message:
        error_message = f"execution failed: {execution['error']}"
    if worker_kind == "gemini":
        with nested_lock:
            execution["activity"] = {
                "enabled": activity_setup_error is None,
                "reads": activity["reads"],
                "bytes": activity["bytes"],
                "last_stream": activity["stream"],
                "kinds": dict(activity["kinds"]),
                "non_progress": dict(activity["non_progress"]),
                "nested_groups": dict(nested_groups),
                "setup_error": activity_setup_error,
            }
    if not child_started:
        provider_terminal_status = "not_started"
    elif exit_code is None:
        provider_terminal_status = "unknown"
    elif cancelled[0] and execution.get("kill_sent"):
        provider_terminal_status = "killed"
    elif cancelled[0]:
        provider_terminal_status = "terminated"
    elif exit_code == 0:
        provider_terminal_status = "exited_success"
    else:
        provider_terminal_status = "exited_error"
    # Provider failure or cancellation cannot classify the useful work left
    # behind any more than exit zero can establish semantic acceptance.
    # The parent's separate ledger disposition owns that decision.
    task_outcome = "unknown"
    status = (
        "cancelled"
        if cancelled[0]
        else "completed"
        if exit_code == 0 and cleanup_proven and not (model_mismatch or effort_mismatch or sonnet_protocol_failure)
        else "failed"
    )
    if exit_code != 0 and not error_message:
        error_message = f"process exited with code {exit_code}"
    if exit_code == 0 and not cleanup_proven:
        error_message = error_message or "provider cleanup evidence unavailable"
    cleanup_status = "proven" if cleanup_proven else "uncertain" if child_started else "not_started"
    response = (
        codex_events.get("response", "")
        if worker_kind == "luna"
        else claude_events.get("response", "")
        if worker_kind == "sonnet"
        else stdout_data.decode("utf-8", errors="replace")
    )
    if not isinstance(response, str) or not response:
        response = stdout_data.decode("utf-8", errors="replace")
    quota_evidence = (
        (
            claude_classify_quota(
                stdout_data,
                stderr=stderr_data,
                exit_code=exit_code,
            )
            if worker_kind == "sonnet"
            else classify_quota_evidence(
                stdout_data,
                stderr=stderr_data,
                exit_code=exit_code,
            )
        )
        if child_started
        else {
            "exhausted": False,
            "classification": None,
            "source": None,
            "confidence": "unknown",
            "provider_status": None,
        }
    )
    quota_exhausted = bool(quota_evidence["exhausted"])
    quota_pause_error: str | None = None
    if quota_exhausted:
        pause = _ledger_method(ledger, worker_kind, "pause_pool")
        if pause is not None:
            evidence = {
                "job_id": job_id,
                "worker_kind": worker_kind,
                "transport": (
                    "claude_external" if worker_kind == "sonnet"
                    else "codex_external" if worker_kind == "luna"
                    else "antigravity"
                ),
                "classification": "explicit_quota_exhaustion",
                "source": quota_evidence.get("source"),
                "confidence": quota_evidence.get("confidence", "unknown"),
                "provider_status": quota_evidence.get("provider_status"),
            }
            try:
                pause(worker_kind, "explicit_quota_exhaustion", evidence)
            except Exception as error:  # noqa: BLE001 - retain provider result
                quota_pause_error = str(error)
    if quota_pause_error and not error_message:
        error_message = f"quota pause recording failed: {quota_pause_error}"
    profile_evidence = (
        luna_profile.evidence() if luna_profile is not None
        else sonnet_profile.evidence() if sonnet_profile is not None
        else requested_selection
    )
    provider_custody: dict[str, Any] = {
        "provider_pid": execution.get("provider_pid"),
        "provider_pgid": execution.get("provider_pgid"),
        "persisted": False,
    }
    try:
        job_snapshot = ledger.get_job(job_id)
        for key in ("provider_pid", "provider_pgid", "provider_identity", "provider_custody_status"):
            if key in job_snapshot:
                provider_custody[key] = job_snapshot[key]
        provider_custody["persisted"] = (
            isinstance(job_snapshot.get("provider_pid"), int)
            and isinstance(job_snapshot.get("provider_pgid"), int)
            and isinstance(job_snapshot.get("provider_identity"), str)
        )
    except (KeyError, LedgerError, OSError, ValueError):
        pass
    if provider_custody_error is not None:
        provider_custody["error"] = provider_custody_error
    changed_files = get_changed_paths(workspace) if task_authority == "mutation_capable" else None
    terminal_layers = {}
    if worker_kind == "gemini":
        from .model_observation import gemini_terminal_layers
        terminal_layers = gemini_terminal_layers(summary, provider_terminal_status)

    result_payload: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "parent_id": parent_id,
        "job_id": job_id,
        "status": status,
        "exit_code": exit_code,
        "response": response,
        "raw_response_bytes": stdout_capture.total_bytes,
        "raw_stderr_bytes": stderr_capture.total_bytes,
        "response_truncated": stdout_capture.truncated,
        "task_outcome": task_outcome,
        "provider_terminal_status": provider_terminal_status,
        # The legacy status names the supervised wrapper. These additive
        # Gemini-only fields preserve the distinct raw provider terminal layer.
        **terminal_layers,
        "cleanup_status": cleanup_status,
        "transport": (
            "claude_external" if worker_kind == "sonnet"
            else "codex_external" if worker_kind == "luna"
            else "antigravity"
        ),
        "provider": (
            "claude" if worker_kind == "sonnet"
            else "codex" if worker_kind == "luna"
            else "antigravity"
        ),
        "worker_kind": worker_kind,
        "requested_model": requested_model,
        "effective_model": effective_model,
        "requested_effort": requested_effort,
        "effective_effort": effective_effort,
        "model_evidence": {
            "requested": profile_evidence,
            "effective": {
                "model": effective_model,
                "effort": effective_effort,
                "source": (
                    (claude_events.get("session_model_observation", {}).get("source") or "provider_structured_events")
                    if worker_kind == "sonnet" and effective_model
                    else (codex_events.get("session_model_observation", {}).get("source") or "provider_structured_events")
                    if worker_kind == "luna" and effective_model
                    else "provider_terminal_metadata"
                    if worker_kind == "gemini" and effective_model
                    else "not_observed"
                ),
            },
            "match": None
            if effective_model is None or effective_effort is None
            else not (model_mismatch or effort_mismatch),
        },
        "provider_event_evidence": (
            {
                "malformed_event_lines": claude_events.get("malformed_event_lines", 0),
                "observed_models": claude_events.get("observed_models", []),
                "observed_efforts": claude_events.get("observed_efforts", []),
                "session_model_observation": claude_events.get("session_model_observation"),
                "quota": quota_evidence,
            }
            if worker_kind == "sonnet"
            else {
                "malformed_event_lines": codex_events.get("malformed_event_lines", 0),
                "observed_models": codex_events.get("observed_models", []),
                "observed_efforts": codex_events.get("observed_efforts", []),
                "session_model_observation": codex_events.get("session_model_observation"),
                "quota": quota_evidence,
            }
            if worker_kind == "luna"
            else None
        ),
        "changed_files": changed_files,
        "changed_files_scope": "workspace_status_not_job_attribution",
        "tests": {"verification": "not_independently_observed", "source": "response"},
        "provider_identifiers": provider_identifiers,
        "provider_custody": provider_custody,
        "error": error_message,
        "cleanup_proven": cleanup_proven,
        "cleanup_observation": execution,
        "quota": {
            "exhausted": bool(quota_exhausted),
            "classification": "explicit_quota_exhaustion"
            if quota_exhausted
            else None,
            "source": quota_evidence.get("source"),
            "confidence": quota_evidence.get("confidence", "unknown"),
            "provider_status": quota_evidence.get("provider_status"),
            "pool_paused": bool(quota_exhausted and quota_pause_error is None),
        },
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(duration, 3),
        "artifacts": {
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "task": str(task_file),
            "evidence_prefix": str(evidence_prefix) if evidence_prefix else None,
            "cleanup_evidence": cleanup_evidence,
        },
    }
    result_path.write_text(
        json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.chmod(result_path, 0o600)
    _call_ledger(
        ledger,
        worker_kind,
        "update_status",
        job_id,
        status,
        result=result_payload,
        error=error_message,
        cleanup_proven=cleanup_proven,
    )
    return 0 if status == "completed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detached supervisor for a single Gemini worker job.")
    parser.add_argument("--parent-id", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--task-file", required=True, type=Path)
    parser.add_argument("--state-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    return run_supervisor(
        parent_id=args.parent_id,
        job_id=args.job_id,
        task_file=args.task_file,
        state_dir=args.state_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
