"""Worker launch adapter and conservative native lifecycle handlers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

from .ledger import (
    AuthorityViolationError,
    LedgerError,
    ParentLedger,
    ParentNotFoundError,
    provider_group_present,
    provider_group_identity_matches,
    supervisor_identity_matches,
    supervisor_is_bound,
)

ENV_PARENT_ID = "APGR_PARENT_ID"
ENV_STATE_DIR = "APGR_WORKER_STATE_DIR"
_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_TERMINAL_JOB_STATES = frozenset({"completed", "failed", "cancelled", "orphaned"})
_PROVIDER_TERM_GRACE_SECONDS = 0.5
_PROVIDER_KILL_GRACE_SECONDS = 0.5


def get_active_parent_id(explicit_parent_id: str | None = None) -> str | None:
    """Resolve a stable parent ID from an explicit argument or environment."""
    inherited = os.environ.get(ENV_PARENT_ID)
    if explicit_parent_id and inherited and explicit_parent_id != inherited:
        raise AuthorityViolationError(
            "explicit parent ID differs from inherited parent context"
        )
    if explicit_parent_id:
        return explicit_parent_id
    return inherited


def validate_inherited_context(
    parent_id: str | None,
    state_dir: Path | None,
) -> Path | None:
    """Reject adapter calls that split an inherited parent or state ledger."""
    get_active_parent_id(parent_id)
    inherited_state = os.environ.get(ENV_STATE_DIR)
    inherited_path = (
        Path(inherited_state).expanduser().resolve() if inherited_state else None
    )
    explicit_path = (
        Path(state_dir).expanduser().resolve() if state_dir is not None else None
    )
    if (
        inherited_path is not None
        and explicit_path is not None
        and explicit_path != inherited_path
    ):
        raise AuthorityViolationError(
            "explicit worker state directory differs from inherited parent context"
        )
    return explicit_path or inherited_path


def validate_mutation_scope(scope: list[str]) -> list[str]:
    """Keep mutation scope bounded, workspace-relative, and metadata-free."""
    if len(scope) > 64:
        raise AuthorityViolationError("mutation_scope contains too many paths")
    validated: list[str] = []
    for item in scope:
        if not isinstance(item, str) or not item.strip():
            raise AuthorityViolationError(
                "mutation_scope must contain non-empty path strings"
            )
        value = item.strip()
        if len(value) > 512:
            raise AuthorityViolationError("mutation_scope path is too long")
        path = Path(value)
        windows_path = PureWindowsPath(value)
        if path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
            raise AuthorityViolationError(
                "mutation_scope paths must be workspace-relative"
            )
        if ".." in path.parts or ".." in windows_path.parts:
            raise AuthorityViolationError(
                "mutation_scope paths cannot traverse a parent directory"
            )
        if ".git" in path.parts or ".git" in windows_path.parts:
            raise AuthorityViolationError("mutation_scope cannot include .git paths")
        validated.append(value)
    return validated


def _atomic_json_write(path: Path, value: Mapping[str, Any]) -> None:
    """Write one private task file without exposing a partial JSON payload."""
    temp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temp.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.chmod(temp, 0o600)
    temp.replace(path)
    os.chmod(path, 0o600)


def _reap_launch_process(process: subprocess.Popen[Any]) -> None:
    """Reap a launcher-owned supervisor after a rejected handoff."""
    try:
        process.wait(timeout=15.0)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.terminate()
    except OSError:
        pass
    try:
        process.wait(timeout=5.0)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.kill()
    except OSError:
        pass
    # The Popen owner performs the final wait.  Observation helpers must not
    # steal this status from the owner.
    process.wait()


def _start_background_reaper(
    process: subprocess.Popen[Any], ledger: ParentLedger, job_id: str
) -> None:
    """Keep launcher ownership of a detached supervisor's wait and handoff."""
    if not callable(getattr(process, "wait", None)):
        return

    def reap() -> None:
        try:
            process.wait()
            # A supervisor can fail before it reaches self-bind, including
            # before the launcher records its PID.  Once this Popen owner has
            # reaped a recorded, unbound process, settle only that same PID;
            # a bound record remains under the supervisor's result/attestation
            # path.
            ledger.settle_gemini_launch_exit(job_id, process.pid)
        except (OSError, ValueError, LedgerError):
            # The launcher has no stronger cleanup operation after an owner
            # wait failure; the ledger remains conservative until evidence.
            pass

    threading.Thread(
        target=reap,
        name=f"agent-worker-reap-{getattr(process, 'pid', 'unknown')}",
        daemon=True,
    ).start()


def _provider_custody(job: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return persisted provider custody, with a legacy result fallback."""
    custody = {
        key: job.get(key)
        for key in ("provider_pid", "provider_pgid", "provider_identity")
        if job.get(key) is not None
    }
    if isinstance(custody.get("provider_pgid"), int):
        return custody
    result = job.get("result")
    observation = result.get("cleanup_observation") if isinstance(result, Mapping) else None
    if not isinstance(observation, Mapping):
        return None
    pgid = observation.get("provider_pgid")
    if not isinstance(pgid, int) or pgid <= 0:
        return None
    legacy = {"provider_pgid": pgid}
    for key in ("provider_pid", "provider_identity"):
        value = observation.get(key)
        if value is not None:
            legacy[key] = value
    return legacy


def _settle_provider_cleanup(
    ledger: ParentLedger,
    job: Mapping[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Clean an exact, recorded provider group after explicit control.

    A supervisor that has already exited cannot be signalled through its old
    PID.  This path therefore uses provider custody persisted before Popen
    work began.  Missing groups are settled observation-only; a present group
    requires the original provider leader identity before any signal is sent.
    """
    # Gemini's wrapper can own a separately sessioned AGY/tool group. A late
    # observation of the wrapper group alone cannot establish that cleanup.
    # Keep its existing supervisor/attestation path and retain uncertainty if
    # that owner is gone; never manufacture a free Gemini slot here.
    if job.get("worker_kind", "gemini") != "luna":
        return dict(job)
    job_id = job.get("job_id")
    if not isinstance(job_id, str) or not job_id:
        return dict(job)
    custody = _provider_custody(job)
    if custody is None:
        return dict(job)
    pgid = custody.get("provider_pgid")
    if not isinstance(pgid, int) or pgid <= 0 or pgid == os.getpgrp():
        return dict(job)
    initial_present = provider_group_present(pgid)
    receipt: dict[str, Any] = {
        "source": "explicit_provider_cleanup",
        "explicit_control": True,
        "provider_pid": custody.get("provider_pid"),
        "provider_pgid": pgid,
        "provider_identity": custody.get("provider_identity"),
        "identity_validated": False,
        "initial_group_present": initial_present,
        "term_sent": False,
        "kill_sent": False,
        "final_group_present": initial_present,
        "cleanup_proven": False,
        "cleanup_status": "unknown",
        "observed_at": time.time(),
    }
    if not initial_present:
        # A stale numeric PGID is never signalled.  Absence is a fresh proof
        # that the recorded provider group no longer occupies a slot.
        receipt["cleanup_proven"] = True
        receipt["cleanup_status"] = "proven"
        try:
            return ledger.settle_provider_cleanup(job_id, receipt)
        except (LedgerError, KeyError, ValueError):
            return dict(job)

    if not provider_group_identity_matches(job):
        receipt["identity_ambiguous"] = True
        receipt["final_group_present"] = True
        try:
            return ledger.settle_provider_cleanup(job_id, receipt)
        except (LedgerError, KeyError, ValueError):
            return dict(job)

    receipt["identity_validated"] = True
    try:
        os.killpg(pgid, signal.SIGTERM)
        receipt["term_sent"] = True
    except (OSError, ProcessLookupError, PermissionError):
        pass

    bounded_timeout = max(0.0, min(float(timeout_seconds), 120.0))
    deadline = time.monotonic() + min(
        bounded_timeout, _PROVIDER_TERM_GRACE_SECONDS
    )
    while provider_group_present(pgid) and time.monotonic() < deadline:
        time.sleep(0.02)

    if provider_group_present(pgid) and bounded_timeout > _PROVIDER_TERM_GRACE_SECONDS:
        try:
            # The group was identity-validated while its leader was live and
            # remains present, so its PGID cannot have been recycled here.
            os.killpg(pgid, signal.SIGKILL)
            receipt["kill_sent"] = True
        except (OSError, ProcessLookupError, PermissionError):
            pass
        deadline = time.monotonic() + min(
            bounded_timeout - _PROVIDER_TERM_GRACE_SECONDS,
            _PROVIDER_KILL_GRACE_SECONDS,
        )
        while provider_group_present(pgid) and time.monotonic() < deadline:
            time.sleep(0.02)

    final_present = provider_group_present(pgid)
    receipt["final_group_present"] = final_present
    receipt["cleanup_proven"] = final_present is False
    receipt["cleanup_status"] = "proven" if final_present is False else "unknown"
    try:
        return ledger.settle_provider_cleanup(job_id, receipt)
    except (LedgerError, KeyError, ValueError):
        return dict(job)


def _parse_hook_input(raw_input: str | Mapping[str, Any]) -> dict[str, Any] | None:
    if isinstance(raw_input, str):
        try:
            value = json.loads(raw_input)
        except (TypeError, json.JSONDecodeError):
            return None
    else:
        value = raw_input
    return dict(value) if isinstance(value, Mapping) else None


def _hook_value(payload: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in payload and payload[name] is not None:
            return payload[name]
    return None


def launch_worker_job(
    parent_id: str,
    task: str,
    idempotency_key: str | None = None,
    task_authority: str | None = None,
    mutation_scope: list[str] | None = None,
    acceptance_criteria: str | None = None,
    profile: str | None = None,
    output_dir: Path | None = None,
    state_dir: Path | None = None,
    worker_kind: str = "gemini",
    task_id: str | None = None,
    previous_job_id: str | None = None,
    recovery_decision: str | None = None,
    recovery_reason: str | None = None,
) -> dict[str, Any]:
    """Admit and launch one detached Gemini job.

    The reservation and launch claim are separate atomic ledger operations. A
    second shell call with the same key sees the first claim and never starts
    another supervisor.
    """
    state_dir = validate_inherited_context(parent_id, state_dir)
    if os.environ.get("APGR_WORKER_LEAF") == "1":
        raise AuthorityViolationError("leaf workers cannot launch additional workers")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be a non-empty string")
    ledger = ParentLedger(parent_id, state_dir)
    parent = ledger.get_status()
    if not parent.get("registered"):
        raise ParentNotFoundError(f"parent context {parent_id} is not registered")

    family = parent.get("parent_family")
    if family == "codex_parent" and parent.get("worker_allowed") is not True:
        raise AuthorityViolationError(
            "Gemini delegation is unavailable for this Codex parent until native "
            "admission is qualified"
        )

    effective_authority = task_authority or parent.get("task_authority")
    if effective_authority not in {"read_only", "mutation_capable"}:
        raise AuthorityViolationError("task authority must be read_only or mutation_capable")
    if parent.get("task_authority") == "read_only" and effective_authority != "read_only":
        raise AuthorityViolationError("cannot launch a mutating worker from a read-only parent")

    if mutation_scope is not None and not isinstance(mutation_scope, list):
        raise AuthorityViolationError("mutation_scope must be a list of paths")
    scope = validate_mutation_scope(list(mutation_scope or []))
    if effective_authority == "mutation_capable" and not scope:
        raise AuthorityViolationError(
            "mutation-capable workers require an explicit mutation_scope"
        )
    if acceptance_criteria is not None and not isinstance(acceptance_criteria, str):
        raise ValueError("acceptance_criteria must be text")

    capability = parent.get("worker_capability") or {}
    if family == "codex_parent" and capability.get("policy_selection") == "triple_pool_4x4x4":
        binding = capability.get("native_launch_binding") or {}
        if binding.get("status") != "bound" or binding.get("cap") != 4 or binding.get("source") != "fresh_source_launcher":
            raise AuthorityViolationError("Codex Gemini requires a fresh source launch with a bound native cap")
    if worker_kind not in {"gemini", "luna", "sonnet"}:
        raise AuthorityViolationError("worker kind must be gemini, luna or sonnet")
    if worker_kind not in capability.get("allowed_worker_kinds", ["gemini"]):
        raise AuthorityViolationError("worker kind is excluded by this parent policy")
    if family == "codex_parent" and worker_kind == "luna":
        raise AuthorityViolationError("Codex Luna workers must use its native runtime pool")
    configured_profile = (parent.get("policy") or {}).get(f"{worker_kind}_profile")
    if isinstance(capability, Mapping):
        gemini_config = capability.get(f"{worker_kind}_worker")
        if isinstance(gemini_config, Mapping):
                configured_profile = gemini_config.get("profile", configured_profile)
    if not configured_profile:
        raise AuthorityViolationError("parent has no frozen Gemini profile; use a new parent lifetime")
    effective_profile = profile or configured_profile
    if not isinstance(effective_profile, str) or not _KEY_RE.fullmatch(effective_profile):
        raise ValueError("profile is invalid")
    if configured_profile is not None and effective_profile != configured_profile:
        raise AuthorityViolationError(
            f"worker profile {effective_profile!r} differs from frozen profile "
            f"{configured_profile!r}"
        )

    key = idempotency_key or f"job-{uuid.uuid4().hex[:12]}"
    if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
        raise ValueError("idempotency_key must contain only safe identifier characters")
    job_id = f"worker-{key}"
    workspace = str(parent.get("workspace") or Path.cwd())
    if task_id is None:
        if previous_job_id is not None:
            previous = ledger.get_job(previous_job_id)
            task_id = previous.get("task_id") or f"legacy-{previous_job_id}"
        else:
            try:
                existing = ledger.get_job(job_id)
            except KeyError:
                identity = json.dumps({"task": task, "workspace": workspace,
                                       "authority": effective_authority, "scope": scope,
                                       "acceptance": acceptance_criteria or ""}, sort_keys=True)
                task_id = "task-" + hashlib.sha256(identity.encode()).hexdigest()[:32]
            else:
                # An old idempotent replay keeps its original payload dialect.
                task_id = existing.get("task_id")
    base_output = Path(output_dir) if output_dir is not None else ledger.base_dir / "jobs"
    base_output = base_output.expanduser().resolve()
    job_dir = base_output / job_id
    task_file = job_dir / "task.json"

    task_payload: dict[str, Any] = {
        "parent_id": parent_id,
        "job_id": job_id,
        "task": task,
        "task_authority": effective_authority,
        "mutation_scope": scope,
        "acceptance_criteria": acceptance_criteria or "",
        "profile": effective_profile,
        "workspace": workspace,
        "output_dir": str(job_dir),
    }
    if worker_kind != "gemini" or capability.get("policy_selection"):
        task_payload["worker_kind"] = worker_kind
    if task_id is not None or previous_job_id is not None:
        task_payload.update(task_id=task_id, previous_job_id=previous_job_id,
                            recovery_decision=recovery_decision, recovery_reason=recovery_reason)
    payload_raw = json.dumps(task_payload, sort_keys=True, separators=(",", ":")).encode()
    payload_hash = hashlib.sha256(payload_raw).hexdigest()
    reservation = ledger.reserve_gemini(
        job_id=job_id,
        idempotency_key=key,
        payload_hash=payload_hash,
        task_authority=effective_authority,
        task_file=str(task_file),
        mutation_scope=scope,
        worker_kind=worker_kind,
        task_id=task_id,
        previous_job_id=previous_job_id,
        recovery_decision=recovery_decision,
        recovery_reason=recovery_reason,
    )
    if reservation.get("status") in {
        "running", "launched", "starting", "stopping", "orphaned",
        "completed", "failed", "cancelled",
    }:
        return reservation

    claimed, state = ledger.claim_gemini_launch(job_id)
    if not claimed:
        return state

    try:
        # The destination is created only after the atomic capacity reservation
        # and launch claim, so denied model-selected keys do not leave folders.
        job_dir.mkdir(parents=True, exist_ok=True)
        _atomic_json_write(task_file, task_payload)
        if not ledger.set_gemini_task_file(job_id, str(task_file)):
            ledger.update_gemini_status(job_id, "cancelled", cleanup_proven=True)
            return ledger.get_job(job_id)
        root = Path(__file__).resolve().parents[2]
        supervisor_stdout = (job_dir / "supervisor.stdout.log").open("ab")
        supervisor_stderr = (job_dir / "supervisor.stderr.log").open("ab")
        try:
            command = [
                sys.executable,
                "-m",
                "apgr_workers.supervisor",
                "--parent-id",
                parent_id,
                "--job-id",
                job_id,
                "--task-file",
                str(task_file),
                "--state-dir",
                str(Path(state_dir).expanduser().resolve())
                if state_dir is not None
                else str(ledger.base_dir.parent),
            ]
            child_env = os.environ.copy()
            for key in list(child_env.keys()):
                if key.startswith("AGENT_CENTRAL"):
                    child_env.pop(key, None)
            child_env["PYTHONPATH"] = str((root / "libexec").resolve())
            # The supervisor is an internal manager; the provider subprocess it
            # creates performs the leaf environment scrub.
            process = subprocess.Popen(
                command,
                cwd=str(root),
                env=child_env,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=supervisor_stdout,
                stderr=supervisor_stderr,
                close_fds=True,
            )
        finally:
            supervisor_stdout.close()
            supervisor_stderr.close()
    except (OSError, ValueError) as error:
        ledger.fail_gemini_launch(job_id, f"supervisor_launch_failed: {error}")
        return ledger.get_job(job_id)

    # ``start_new_session`` makes the supervisor PID its own PGID.  Record the
    # handoff while the launcher still owns the Popen object; this is not a
    # running admission and cannot be signalled until the supervisor self-binds.
    try:
        try:
            supervisor_pgid = os.getpgid(process.pid)
        except OSError:
            supervisor_pgid = process.pid
        handed_off = ledger.record_gemini_launch(job_id, process.pid, supervisor_pgid)
    except BaseException:  # noqa: BLE001 - interruption must not abandon the child
        _reap_launch_process(process)
        raise
    if not handed_off:
        _reap_launch_process(process)
        try:
            current = ledger.get_job(job_id)
        except KeyError:
            return {"job_id": job_id, "status": "failed", "error": "launch handoff rejected"}
        if (
            current.get("status") in {"starting", "stopping", "launched"}
            and current.get("supervisor_pid") is None
        ):
            ledger.update_gemini_status(
                job_id,
                "cancelled" if current.get("status") == "stopping" else "failed",
                error="launch handoff rejected",
                cleanup_proven=True,
            )
    else:
        _start_background_reaper(process, ledger, job_id)
    return ledger.get_job(job_id)


def wait_worker_job(
    parent_id: str,
    job_id: str,
    timeout_seconds: float | None = None,
    poll_interval: float = 0.1,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Wait for terminal worker evidence without reading a partial file."""
    state_dir = validate_inherited_context(parent_id, state_dir)
    ledger = ParentLedger(parent_id, state_dir)
    import math
    timeout_seconds = 30.0 if timeout_seconds is None else float(timeout_seconds)
    if not math.isfinite(timeout_seconds) or not 0 <= timeout_seconds <= 120:
        raise ValueError("wait timeout must be finite and between 0 and 120 seconds")
    deadline = time.monotonic() + timeout_seconds
    while True:
        job = ledger.get_job(job_id)
        status = job.get("status")
        if status in _TERMINAL_JOB_STATES:
            result = job.get("result")
            if isinstance(result, dict):
                return result
            return {"job_id": job_id, "status": status, "error": job.get("error")}
        if deadline is not None and time.monotonic() >= deadline:
            return {**job, "timed_out": True, "observation": "running_or_cleanup_pending",
                    "decision_required": True}
        time.sleep(max(0.0, poll_interval))


def cancel_worker_job(
    parent_id: str,
    job_id: str,
    state_dir: Path | None = None,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Request cancellation and release capacity only after cleanup proof."""
    state_dir = validate_inherited_context(parent_id, state_dir)
    ledger = ParentLedger(parent_id, state_dir)
    job = ledger.begin_gemini_stop(job_id)
    if job.get("status") in {"completed", "failed", "cancelled"}:
        # Never signal a PID retained in terminal evidence: it may have been
        # recycled by an unrelated process after this job finished.
        return job.get("result") or job
    if job.get("status") == "orphaned":
        # A supervisor may have exited after returning a provider result while
        # its independent provider group was still present.  The explicit
        # cancel/abandon call is the only path allowed to reconcile that group.
        return _settle_provider_cleanup(ledger, job, timeout_seconds)
    pid = job.get("supervisor_pid")
    if not isinstance(pid, int) or pid <= 0:
        # A reserved job has no launch owner and can be cancelled safely.  A
        # claimed launch remains stopping until its owner acknowledges whether
        # Popen happened; an old snapshot cannot release that slot.
        if job.get("launch_claimed") is True:
            return _settle_provider_cleanup(ledger, job, timeout_seconds)
        ledger.update_gemini_status(job_id, "cancelled", cleanup_proven=True)
        return ledger.get_job(job_id)
    if not supervisor_is_bound(job):
        # The launcher still owns this process.  Let its supervisor install the
        # handler and refuse the bind; signalling this window could invoke the
        # default SIGTERM action and lose cleanup custody.
        return job
    if not supervisor_identity_matches(job):
        ledger.update_gemini_status(
            job_id, "orphaned", error="supervisor_identity_unproven", cleanup_proven=False
        )
        return ledger.get_job(job_id)
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass

    deadline = time.monotonic() + max(timeout_seconds, 0.0)
    while True:
        current = ledger.get_job(job_id)
        if current.get("status") in {"completed", "failed", "cancelled"}:
            return current.get("result") or current
        if current.get("status") == "orphaned":
            return _settle_provider_cleanup(ledger, current, timeout_seconds)
        if time.monotonic() >= deadline:
            current["error"] = current.get("error") or "cancellation_pending_cleanup"
            return current
        time.sleep(0.05)


# Native Codex hook handlers.  They are inert unless a dispatcher parent is
# registered.  SubagentStop intentionally does not release capacity because a
# stopped native thread may be resumed.


def handle_native_pre_tool(
    raw_input: str | Mapping[str, Any],
    parent_id: str | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Reserve native capacity at the supported pre-tool admission point."""
    pid = get_active_parent_id(parent_id)
    payload = _parse_hook_input(raw_input)
    if not pid or payload is None:
        return {"continue": True}
    state_dir = validate_inherited_context(pid, state_dir)
    tool_name = _hook_value(payload, "tool_name", "toolName")
    if tool_name not in ("spawn_agent", "Agent"):
        return {"continue": True}
    tool_input = _hook_value(payload, "tool_input", "toolInput") or {}
    if not isinstance(tool_input, Mapping):
        tool_input = {}
    subagent_type = _hook_value(tool_input, "subagent_type", "agent_type", "subagentType") or "luna"
    reservation_id = _hook_value(payload, "tool_use_id", "toolUseId", "id")
    if reservation_id is None:
        reservation_id = _hook_value(tool_input, "tool_use_id", "toolUseId", "id")
    if not isinstance(reservation_id, str) or not reservation_id:
        # Without an event identity there is no safe way to bind a later start
        # event.  Preserve ordinary tool behavior and report the limitation.
        return {"continue": True, "workerAdmission": "identity_unavailable"}
    admitted, reason = ParentLedger(state_dir=state_dir, parent_id=pid).reserve_native(
        reservation_id, str(subagent_type)
    )
    if not admitted:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }


def handle_native_post_tool(
    raw_input: str | Mapping[str, Any],
    parent_id: str | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Rollback a native reservation only when the spawn tool reports failure."""
    pid = get_active_parent_id(parent_id)
    payload = _parse_hook_input(raw_input)
    if not pid or payload is None:
        return {"continue": True}
    state_dir = validate_inherited_context(pid, state_dir)
    tool_name = _hook_value(payload, "tool_name", "toolName")
    if tool_name not in ("spawn_agent", "Agent"):
        return {"continue": True}
    reservation_id = _hook_value(payload, "tool_use_id", "toolUseId", "id")
    if reservation_id is None:
        tool_input = _hook_value(payload, "tool_input", "toolInput")
        if isinstance(tool_input, Mapping):
            reservation_id = _hook_value(tool_input, "tool_use_id", "toolUseId", "id")
    error = _hook_value(payload, "error", "is_error", "isError")
    if reservation_id and error:
        ParentLedger(pid, state_dir).rollback_native(str(reservation_id))
    return {"continue": True}


def handle_native_subagent_start(
    raw_input: str | Mapping[str, Any],
    parent_id: str | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Activate only a reservation with the exact same native event ID."""
    pid = get_active_parent_id(parent_id)
    payload = _parse_hook_input(raw_input)
    if not pid or payload is None:
        return {"continue": True}
    state_dir = validate_inherited_context(pid, state_dir)
    agent_id = _hook_value(payload, "agent_id", "subagentId", "subagent_id", "agentId")
    if not isinstance(agent_id, str) or not agent_id:
        return {"continue": True, "workerAdmission": "identity_unavailable"}
    agent_type = _hook_value(payload, "agent_type", "subagentType", "subagent_type") or "luna"
    ParentLedger(pid, state_dir).activate_native(agent_id, str(agent_type))
    return {"continue": True}


def handle_native_subagent_stop(
    raw_input: str | Mapping[str, Any],
    parent_id: str | None = None,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Observe a stop event while retaining capacity for possible wakeup."""
    return {"continue": True}


def close_native_agent(
    parent_id: str, agent_id: str, state_dir: Path | None = None
) -> dict[str, Any]:
    """Explicitly close a verified native thread and release its slot."""
    state_dir = validate_inherited_context(parent_id, state_dir)
    ledger = ParentLedger(parent_id, state_dir)
    closed = ledger.close_native(agent_id)
    runtime_owned = ledger.get_status().get("policy_selection") == "triple_pool_4x4x4"
    return {
        "agent_id": agent_id,
        "closed": closed,
        "status": "closed" if closed else "not_closed",
        "admission_owner": "codex_runtime" if runtime_owned else "legacy_ledger",
    }
