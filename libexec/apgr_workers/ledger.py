"""Process-safe capacity ledger for per-parent worker scheduling.

The ledger is deliberately local and small.  A parent context owns one state
directory, and every state transition takes the same advisory file lock.  The
lock is held only while reading, validating, and atomically replacing the JSON
state; model execution and process waits happen outside it.

Fresh triple-pool admission independently caps Gemini, Luna and Sonnet at four.
Codex native Luna occupancy belongs to the Codex runtime; Claude native Sonnet
uses atomic ledger reservations. The aggregate view is informational.
Historical two-pool ledgers remain readable and require their pinned controller
for new admission. Orphaned external records and uncertain native reservations
retain capacity until cleanup or parent exit is proven.
"""

from __future__ import annotations

import contextlib
import copy
import fcntl
import hashlib
import json
import os
import posixpath
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Iterator, Mapping

from .policy import (
    DEFAULT_MAX_AGGREGATE_ASTRA,
    DEFAULT_MAX_GEMINI,
    DUAL_POOL,
    PARENT_FAMILIES,
    TASK_AUTHORITIES,
    WorkerPolicyError,
    load_worker_policy,
)
from .native_capacity import (
    EXTERNAL_WORKER_KINDS,
    PINNED_CONTROLLER_DIAGNOSTIC,
    CapacityExceededError,
    LedgerError,
    PinnedControllerError,
    SCHEMA_V2,
    TRIPLE_POOL,
    activate_native_agent_slot,
    build_triple_pool_status,
    check_triple_pool_capacity,
    close_native_agent_slot,
    drain_active_native_agents,
    init_triple_pool_data,
    init_triple_pool_policy_snapshot,
    is_historical_ledger,
    is_triple_pool,
    reserve_native_agent_slot,
    rollback_native_agent_slot,
)

SCHEMA_NAME = "agent-worker-ledger-v1"

# ``orphaned`` remains active until cleanup evidence is supplied.  In
# particular, a dead supervisor PID is not sufficient to release a slot.
ACTIVE_GEMINI_STATES = frozenset(
    {"reserved", "starting", "launched", "running", "stopping", "orphaned"}
)
TERMINAL_GEMINI_STATES = frozenset({"completed", "failed", "cancelled"})
ACTIVE_NATIVE_STATES = frozenset({"reserved", "active", "uncertain"})
TERMINAL_NATIVE_STATES = frozenset({"closed"})
GEMINI_STATES = ACTIVE_GEMINI_STATES | TERMINAL_GEMINI_STATES
NATIVE_STATES = ACTIVE_NATIVE_STATES | TERMINAL_NATIVE_STATES
_SAFE_PARENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
RECOVERY_DECISIONS = frozenset({"adopt", "amend", "reject", "continue"})
TASK_OUTCOMES = frozenset({"unknown", "partial", "accepted", "rejected", "failed", "cancelled"})


class PoolPausedError(CapacityExceededError):
    """The selected external worker pool is paused for this parent."""


class IdempotencyConflictError(LedgerError):
    """Same idempotency key reused with a different task payload."""


class ParentNotFoundError(LedgerError):
    """Parent context not found or no longer active."""


class ParentContextConflictError(LedgerError):
    """A stable parent identity was reused with different context."""


class AuthorityViolationError(LedgerError):
    """Child requested permissions exceeding the parent's task authority."""


class RecoveryConflictError(LedgerError):
    """A replacement task violated the cleanup or lineage recovery fence."""


def _process_identity(pid: int) -> str | None:
    """Bind a PID to its observed start time and group before signalling it."""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart=", "-o", "pgid="],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            timeout=2, check=False,
        )
        value = result.stdout.strip()
        return value if result.returncode == 0 and value and len(value) <= 200 else None
    except Exception:
        return None


def supervisor_identity_matches(job: Mapping[str, Any]) -> bool:
    pid = job.get("supervisor_pid")
    identity = job.get("supervisor_identity")
    return (
        isinstance(pid, int) and pid > 0 and isinstance(identity, str)
        and bool(identity) and _process_identity(pid) == identity
    )


def provider_identity_matches(job: Mapping[str, Any]) -> bool:
    """Validate the recorded provider leader before signalling its group.

    A provider group is a separate session from the supervisor.  The
    supervisor can therefore disappear while the provider (or one of its
    descendants) remains alive.  Only a still-live provider leader with the
    original start-time/group identity may authorize a group signal.  A group
    that is already absent is handled as a separate, observation-only case by
    the adapter.
    """
    pid = job.get("provider_pid")
    pgid = job.get("provider_pgid")
    identity = job.get("provider_identity")
    if (
        not _valid_positive_int(pid)
        or not _valid_positive_int(pgid)
        or not isinstance(identity, str)
        or not identity
    ):
        return False
    try:
        if os.getpgid(pid) != pgid:
            return False
    except (OSError, ProcessLookupError):
        return False
    return _process_identity(pid) == identity


def provider_group_identity_matches(job: Mapping[str, Any]) -> bool:
    """Validate a recorded group even after its leader has exited.

    ``start_new_session`` makes the provider PID the PGID.  Once that leader
    has exited, the group can still contain a child, but the numeric PGID
    cannot be recycled while that child remains in the group.  A live leader
    with a changed identity is treated as ambiguous and is never signalled.
    """
    if provider_identity_matches(job):
        return True
    pid = job.get("provider_pid")
    pgid = job.get("provider_pgid")
    if not (_valid_positive_int(pid) and _valid_positive_int(pgid) and pid == pgid):
        return False
    if _pid_is_alive(pid):
        # The leader is live but its identity did not match the launch record.
        return False
    return _process_group_is_present(pgid)


def supervisor_is_bound(job: Mapping[str, Any]) -> bool:
    """Return whether a supervisor completed its own launch handoff.

    Older ledgers have no explicit marker. Their ``running`` state is the
    legacy equivalent; new launcher handoffs use ``launched`` with an explicit
    false marker until the supervisor installs its signal handler and binds.
    """
    marker = job.get("supervisor_bound")
    if marker is not None:
        return marker is True
    return job.get("status") == "running"


def get_default_state_dir() -> Path:
    """Return the persistent worker state directory outside the repository."""
    override = os.environ.get("APGR_WORKER_STATE_DIR")
    if override:
        path = Path(override).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    home_env = os.environ.get("APGR_HOME")
    if home_env:
        resolved_home = Path(home_env).expanduser().resolve()
    else:
        resolved_home = (Path.home() / ".apgr").resolve()

    base = resolved_home / "state" / "workers"
    # Changing state roots after an I/O failure would hide live reservations.
    # Decline optional admission instead of silently creating an empty ledger.
    base.mkdir(parents=True, exist_ok=True)
    return base


def sanitize_parent_id(parent_id: str) -> str:
    """Derive a collision-resistant directory name from a parent identity."""
    if not isinstance(parent_id, str) or not parent_id:
        raise ValueError("parent_id must be a non-empty string")
    clean = re.sub(r"[^A-Za-z0-9_.-]", "_", parent_id)
    if clean != parent_id or len(clean) > 128:
        digest = hashlib.sha256(parent_id.encode("utf-8")).hexdigest()[:16]
        clean = clean[:100] + "_" + digest
    return clean or "root"


@dataclass
class GeminiJob:
    """Typed view of a persisted Gemini job."""

    job_id: str
    idempotency_key: str
    payload_hash: str
    status: str
    task_authority: str
    created_at: float
    updated_at: float
    supervisor_pid: int | None = None
    supervisor_pgid: int | None = None
    supervisor_identity: str | None = None
    supervisor_bound: bool = False
    launch_claimed: bool = False
    provider_pid: int | None = None
    provider_pgid: int | None = None
    provider_identity: str | None = None
    task_file: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    cleanup_proven: bool = False
    worker_kind: str = "gemini"
    task_id: str | None = None
    previous_job_id: str | None = None
    recovery_decision: str | None = None
    recovery_reason: str | None = None


@dataclass
class NativeAgent:
    """Typed view of a persisted native worker reservation."""

    agent_id: str
    agent_type: str
    status: str
    created_at: float
    updated_at: float


def _copy(value: Any) -> Any:
    """Copy JSON-shaped values without exposing mutable ledger state."""
    return copy.deepcopy(value)


def _valid_positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _cleanup_proven(job: Mapping[str, Any]) -> bool:
    if job.get("cleanup_proven") is True:
        return True
    result = job.get("result")
    return isinstance(result, Mapping) and result.get("cleanup_proven") is True


def _job_worker_kind(job: Mapping[str, Any]) -> str:
    """Read a job kind while treating pre-dual ledgers as Gemini jobs."""
    kind = job.get("worker_kind", "gemini")
    return kind if kind in EXTERNAL_WORKER_KINDS else "gemini"


def _policy_selection(data: Mapping[str, Any]) -> str | None:
    """Return the immutable selection recorded at parent registration."""
    selection = data.get("policy_selection")
    if isinstance(selection, str) and selection:
        return selection
    policy = data.get("policy")
    if isinstance(policy, Mapping):
        selection = policy.get("policy_selection")
        if isinstance(selection, str) and selection:
            return selection
    capability = data.get("worker_capability")
    if isinstance(capability, Mapping):
        selection = capability.get("policy_selection")
        if isinstance(selection, str) and selection:
            return selection
    return None


def _is_dual_pool(data: Mapping[str, Any]) -> bool:
    return _policy_selection(data) == DUAL_POOL


def _nonempty_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def _normalize_mutation_scope(scope: Any) -> list[str]:
    """Validate and canonicalize a bounded relative mutation path list."""
    if scope is None:
        return []
    if not isinstance(scope, (list, tuple)):
        raise ValueError("mutation_scope must be a list of paths")
    if len(scope) > 64:
        raise ValueError("mutation_scope contains too many paths")
    normalized: list[str] = []
    for item in scope:
        _nonempty_text(item, "mutation_scope item")
        value = item.strip().replace("\\", "/")
        if len(value) > 512:
            raise ValueError("mutation_scope path is too long")
        parts = tuple(part for part in value.split("/") if part)
        windows_path = PureWindowsPath(value)
        if (
            value.startswith("/")
            or windows_path.is_absolute()
            or bool(windows_path.drive)
            or ".." in parts
            or ".git" in parts
        ):
            raise ValueError("mutation_scope paths must be relative")
        value = posixpath.normpath(value)
        if value in {"", "."} or value == ".." or value.startswith("../"):
            raise ValueError("mutation_scope path escapes the workspace")
        if value not in normalized:
            normalized.append(value)
    return normalized


def _scopes_overlap(first: str, second: str) -> bool:
    return (
        first == second
        or first.startswith(second.rstrip("/") + "/")
        or second.startswith(first.rstrip("/") + "/")
    )


def _pool_state(data: dict[str, Any], kind: str, *, create: bool = False) -> dict[str, Any] | None:
    pools = data.get("pool_state")
    if not isinstance(pools, dict):
        if not create:
            return None
        pools = {}
        data["pool_state"] = pools
    current = pools.get(kind)
    if not isinstance(current, dict):
        if not create:
            return None
        current = {"paused": False}
        pools[kind] = current
    return current


def apply_pool_pause(
    data: dict[str, Any], kind: str, cause: str, evidence: Any, parent_id: str
) -> dict[str, Any]:
    """Apply a validated pause inside the caller's existing ledger transaction."""
    if not data or data.get("status") not in {"active", "draining"}:
        raise ParentNotFoundError(
            f"parent {parent_id} is not registered"
        )
    native_sonnet = (kind == "sonnet" and is_triple_pool(data)
        and data.get("parent_family") in {"claude_opus", "claude_fable"}
        and (data.get("worker_capability") or {}).get("sonnet_worker", {}).get("transport") == "claude_native"
        and "sonnet" not in (data.get("worker_capability") or {}).get("excluded_worker_kinds", []))
    if not native_sonnet:
        _validate_worker_kind(data, kind)
    pool = _pool_state(data, kind, create=True)
    assert pool is not None
    if pool.get("paused") is True:
        existing_cause = pool.get("cause")
        if existing_cause == cause and pool.get("evidence") == evidence:
            return _copy(pool)
        raise RecoveryConflictError(
            f"{kind} worker pool is already paused for another cause"
        )
    now = time.time()
    pool.update(
        {
            "paused": True,
            "cause": cause,
            "evidence": _copy(evidence),
            "paused_at": now,
        }
    )
    return _copy(pool)


def _active_external_count(jobs: Mapping[str, Any], kind: str) -> int:
    return sum(
        1
        for job in jobs.values()
        if isinstance(job, Mapping)
        and job.get("status") in ACTIVE_GEMINI_STATES
        and _job_worker_kind(job) == kind
    )


def _job_snapshot(job: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compatibility snapshot with additive lifecycle metadata."""
    snapshot = _copy(dict(job))
    snapshot.setdefault("worker_kind", "gemini")
    snapshot.setdefault("task_outcome", "unknown")
    snapshot.setdefault("provider_status", snapshot.get("status"))
    snapshot.setdefault(
        "cleanup_status", "proven" if _cleanup_proven(snapshot) else "unknown"
    )
    return snapshot


def _validate_worker_kind(data: Mapping[str, Any], worker_kind: str) -> None:
    if worker_kind not in EXTERNAL_WORKER_KINDS:
        raise ValueError("worker_kind must be gemini, luna, or sonnet")
    if not _is_dual_pool(data) and not is_triple_pool(data):
        if worker_kind in ("luna", "sonnet"):
            raise AuthorityViolationError(
                f"external {worker_kind} workers require dual_pool_4x4 or triple_pool_4x4x4"
            )
        return
    if data.get("worker_allowed") is not True:
        raise AuthorityViolationError(
            "the frozen optional worker capability is unavailable for this parent"
        )
    allowed = data.get("allowed_worker_kinds")
    if not isinstance(allowed, list):
        capability = data.get("worker_capability")
        allowed = capability.get("allowed_worker_kinds") if isinstance(capability, Mapping) else None
    if worker_kind not in (allowed if isinstance(allowed, list) else []):
        raise AuthorityViolationError(
            f"worker kind {worker_kind!r} is not allowed for this parent"
        )


def _validate_dual_capability(
    parent_family: str,
    limits: Mapping[str, Any],
    allowed_worker_kinds: Any,
    luna_worker: Any,
    borrowing: Any,
) -> tuple[int, list[str]]:
    """Validate the small capability contract before freezing a dual parent."""
    max_luna = limits.get("max_luna", limits.get("max_luna_workers_per_parent"))
    max_aggregate = limits.get(
        "max_aggregate_workers_per_astra_parent", limits.get("max_aggregate")
    )
    if max_luna != 4 or max_aggregate != 8:
        raise WorkerPolicyError(
            "dual_pool_4x4 requires four Luna slots and an informational aggregate of eight"
        )
    if borrowing is None:
        borrowing = False
    if borrowing is not False:
        raise WorkerPolicyError("dual_pool_4x4 does not permit pool borrowing")
    if not isinstance(allowed_worker_kinds, list):
        raise WorkerPolicyError("dual_pool_4x4 must declare allowed worker kinds")
    if any(not isinstance(kind, str) for kind in allowed_worker_kinds):
        raise WorkerPolicyError("dual_pool_4x4 allowed worker kinds must be strings")
    if len(set(allowed_worker_kinds)) != len(allowed_worker_kinds):
        raise WorkerPolicyError("dual_pool_4x4 allowed worker kinds must be unique")
    valid_kinds = {"gemini"} if parent_family == "codex_astra" else EXTERNAL_WORKER_KINDS
    if any(kind not in valid_kinds for kind in allowed_worker_kinds):
        raise WorkerPolicyError(
            "dual_pool_4x4 allowed worker kinds contain an unsupported provider"
        )
    # Provider exclusions are frozen as an allowlisted subset.  Preserve a
    # stable order in readback while keeping both independent ceilings in the
    # parent policy even when one pool is unavailable.
    expected = [
        kind for kind in ("gemini", "luna") if kind in allowed_worker_kinds
    ]
    if not isinstance(luna_worker, Mapping) or luna_worker.get("profile") != "luna-worker":
        raise WorkerPolicyError("dual_pool_4x4 must freeze the luna-worker profile")
    return max_luna, expected


def _recovery_lineage(
    jobs: Mapping[str, Any],
    *,
    job_id: str,
    task_id: str | None,
    previous_job_id: str | None,
    recovery_decision: str | None,
    recovery_reason: str | None,
) -> tuple[str | None, int, dict[str, Any] | None]:
    """Validate one optional successor and return its frozen lineage fields."""
    if previous_job_id is None:
        if recovery_decision is not None or recovery_reason is not None:
            raise RecoveryConflictError(
                "recovery decision and reason require previous_job_id"
            )
        if task_id is not None and any(
            isinstance(job, Mapping) and job.get("task_id") == task_id
            for job in jobs.values()
        ):
            raise RecoveryConflictError("existing task requires a linked recovery attempt, not a new key")
        return task_id, 1, None

    previous = jobs.get(previous_job_id)
    if not isinstance(previous, Mapping):
        raise RecoveryConflictError(f"previous job {previous_job_id!r} was not found")
    if previous_job_id == job_id:
        raise RecoveryConflictError("a job cannot be its own recovery successor")
    if previous.get("status") not in TERMINAL_GEMINI_STATES or not _cleanup_proven(previous):
        raise RecoveryConflictError(
            "previous job must be terminal with proven cleanup before a successor"
        )
    if recovery_decision not in RECOVERY_DECISIONS:
        raise RecoveryConflictError(
            "successor requires adopt, amend, reject, or continue recovery decision"
        )
    _nonempty_text(recovery_reason, "recovery_reason")
    effective_task_id = task_id or previous.get("task_id")
    if not isinstance(effective_task_id, str) or not effective_task_id:
        raise RecoveryConflictError("successor requires a task_id matching its lineage")
    previous_task_id = previous.get("task_id")
    if previous_task_id is not None and previous_task_id != effective_task_id:
        raise RecoveryConflictError("successor task_id does not match previous task lineage")
    previous_attempt = previous.get("attempt", previous.get("attempt_number", 1))
    if type(previous_attempt) is not int or previous_attempt < 1:
        raise RecoveryConflictError("previous job has invalid attempt lineage")
    attempt = previous_attempt + 1
    if attempt > 2:
        raise RecoveryConflictError("task lineage permits at most two delegated attempts")
    lineage_id = previous.get("lineage_id") or effective_task_id
    lineage = [job for job in jobs.values() if isinstance(job, Mapping) and (
        job.get("lineage_id") == lineage_id or job.get("task_id") == effective_task_id
    )]
    if len(lineage) >= 2:
        raise RecoveryConflictError("task lineage already used its two delegated attempts")
    recovery = {
        "decision": recovery_decision,
        "reason": recovery_reason,
        "previous_job_id": previous_job_id,
        "previous_status": previous.get("status"),
        "previous_task_outcome": previous.get("task_outcome", "unknown"),
        "previous_cleanup_status": previous.get(
            "cleanup_status", "proven" if _cleanup_proven(previous) else "unknown"
        ),
        "previous_error": previous.get("error"),
        "previous_result": _copy(previous.get("result")),
    }
    return effective_task_id, attempt, {"lineage_id": lineage_id, **recovery}


def _pid_is_alive(pid: int) -> bool:
    """Return true unless the kernel proves that ``pid`` is gone."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    # Observation does not own the child's wait status. Its Popen owner must
    # reap it; an unreaped child conservatively remains live for accounting.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _process_group_is_present(pgid: int | None) -> bool:
    """Return true unless the kernel proves that a process group is absent."""
    if not isinstance(pgid, int) or pgid <= 0:
        return False
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def provider_group_present(pgid: int | None) -> bool:
    """Observe a provider group without changing its state."""
    return _process_group_is_present(pgid)


class ParentLedger:
    """Process-safe ledger for one stable top-level parent context."""

    def __init__(self, parent_id: str, state_dir: Path | None = None) -> None:
        if not isinstance(parent_id, str) or not parent_id:
            raise ValueError("parent_id must be a non-empty string")
        self.parent_id = parent_id
        root = Path(state_dir) if state_dir is not None else get_default_state_dir()
        self.base_dir = root.expanduser().resolve() / sanitize_parent_id(parent_id)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.base_dir / "ledger.lock"
        self.data_path = self.base_dir / "ledger.json"
        self._recently_reaped: list[str] = []
        self._recently_orphaned: list[str] = []

    @contextlib.contextmanager
    def _locked(self) -> Iterator[dict[str, Any]]:
        """Read, lock, and atomically persist one ledger transaction."""
        lock_fd = os.open(os.fspath(self.lock_path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            os.fchmod(lock_fd, 0o600)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            data = self._read_data()
            self._recently_reaped = []
            self._recently_orphaned = []
            self._reap_stale_processes(data)
            yield data
            self._write_data(data)
        finally:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(lock_fd)

    def _read_data(self) -> dict[str, Any]:
        if not self.data_path.exists():
            return {}
        try:
            raw = self.data_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            # Never turn corrupted state into an empty ledger: that would reset
            # counters while an old child may still be executing.
            raise LedgerError(f"worker ledger is unreadable: {self.data_path}") from error
        if not isinstance(data, dict):
            raise LedgerError(f"worker ledger is not an object: {self.data_path}")
        if data.get("schema") not in (None, SCHEMA_NAME, SCHEMA_V2):
            raise LedgerError(f"unsupported worker ledger schema: {data.get('schema')!r}")
        if is_triple_pool(data) and data.get("schema") != SCHEMA_V2:
            raise LedgerError("three-pool authority requires ledger schema v2")
        if data.get("schema") == SCHEMA_V2 and not is_triple_pool(data):
            raise LedgerError("ledger schema v2 cannot carry historical two-pool authority")
        return data

    def _write_data(self, data: dict[str, Any]) -> None:
        if not data:
            return
        data["updated_at"] = time.time()
        tmp_path = self.data_path.with_name(
            f"{self.data_path.name}.tmp.{os.getpid()}"
        )
        try:
            tmp_path.write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            os.chmod(tmp_path, 0o600)
            tmp_path.replace(self.data_path)
            os.chmod(self.data_path, 0o600)
        except OSError as error:
            raise LedgerError(f"cannot write worker ledger: {self.data_path}") from error

    def _reap_stale_processes(self, data: dict[str, Any]) -> list[str]:
        """Reap only jobs with proven cleanup; retain uncertain jobs active."""
        jobs = data.get("gemini_jobs")
        if not isinstance(jobs, dict):
            return []
        now = time.time()
        for job_id, job in jobs.items():
            if not isinstance(job, dict) or job.get("status") not in ACTIVE_GEMINI_STATES:
                continue
            pid = job.get("supervisor_pid")
            if not isinstance(pid, int) or pid <= 0:
                # A reservation or launch claim may still be between the
                # atomic claim and Popen.  Do not expire it by elapsed time.
                continue
            if _pid_is_alive(pid):
                continue

            pgid_present = _process_group_is_present(job.get("supervisor_pgid"))
            if pgid_present or not _cleanup_proven(job):
                job["status"] = "orphaned"
                job["cleanup_proven"] = False
                job["error"] = (
                    "supervisor_process_terminated_cleanup_unproven"
                    if not pgid_present
                    else "supervisor_process_terminated_group_present"
                )
                job["provider_status"] = "unknown"
                job["cleanup_status"] = "unknown"
                job["updated_at"] = now
                self._recently_orphaned.append(str(job_id))
                continue

            job["status"] = "failed"
            job["error"] = job.get("error") or "supervisor_process_terminated"
            job["cleanup_proven"] = True
            job["provider_status"] = "failed"
            job["cleanup_status"] = "proven"
            job["updated_at"] = now
            self._recently_reaped.append(str(job_id))
        return list(self._recently_reaped)

    def _existing_parent(self) -> dict[str, Any] | None:
        """Return a snapshot of an existing context under a lock."""
        with self._locked() as data:
            if not data:
                return None
            if data.get("parent_id") not in (None, self.parent_id):
                raise LedgerError("worker ledger parent identity mismatch")
            return _copy(data)

    @staticmethod
    def _validate_parent_context(
        existing: Mapping[str, Any],
        parent_family: str,
        workspace: Path,
        task_authority: str,
    ) -> None:
        """Reject reuse of an identity for a different parent context."""
        if existing.get("parent_family") != parent_family:
            raise ParentContextConflictError(
                f"parent already belongs to {existing.get('parent_family')}"
            )
        if existing.get("workspace") != str(workspace):
            raise ParentContextConflictError(
                f"parent already uses workspace {existing.get('workspace')}"
            )
        if existing.get("task_authority") != task_authority:
            raise ParentContextConflictError(
                f"parent already uses task authority {existing.get('task_authority')}"
            )

    def initialize_parent(
        self,
        parent_family: str,
        *,
        workspace: str | Path = "/tmp",
        task_authority: str = "mutation_capable",
        policy_path: Path | None = None,
        worker_capability: Mapping[str, Any] | None = None,
        custom_limits: Mapping[str, int] | None = None,
    ) -> dict[str, Any]:
        """Register one stable parent and freeze its policy/capability.

        Registration is idempotent for the same parent context.  A repeated
        shell call returns the existing snapshot and never reloads policy or
        resets reservations.
        """
        if os.environ.get("APGR_WORKER_LEAF") == "1":
            raise AuthorityViolationError("leaf workers cannot register root parents")
        if parent_family not in PARENT_FAMILIES:
            raise ValueError(
                f"parent_family must be one of {sorted(PARENT_FAMILIES)}"
            )
        if task_authority not in TASK_AUTHORITIES:
            raise ValueError(
                f"task_authority must be one of {sorted(TASK_AUTHORITIES)}"
            )
        if not isinstance(workspace, (str, Path)) or not str(workspace):
            raise ValueError("workspace must be a non-empty path")
        root = Path(workspace).expanduser().resolve()

        existing = self._existing_parent()
        if existing is not None:
            self._validate_parent_context(existing, parent_family, root, task_authority)
            return existing

        if parent_family == "gemini_flash":
            from .gemini_parent import validate_registration
            validate_registration(worker_capability)

        # Policy is read before the commit, but the resulting source/digest is
        # stored in the context and never re-read for this parent lifetime.
        policy_source = "defaults"
        policy_sha256 = ""
        max_gemini = DEFAULT_MAX_GEMINI
        max_aggregate = DEFAULT_MAX_GEMINI
        max_luna: int | None = None
        policy_selection: str | None = None
        allowed_worker_kinds: list[str] | None = None
        borrowing: bool | None = None
        gemini_profile = None
        if worker_capability is not None:
            if not isinstance(worker_capability, Mapping):
                raise ValueError("worker_capability must be a mapping")
            cap_family = worker_capability.get("parent_family")
            if cap_family is not None and cap_family != parent_family:
                raise ParentContextConflictError(
                    "worker capability parent family does not match registration"
                )
            limits = worker_capability.get("limits")
            if not isinstance(limits, Mapping):
                raise ValueError("worker capability must contain limits")
            max_gemini = limits.get(
                "max_gemini_workers_per_parent", limits.get("max_gemini")
            )
            max_aggregate = limits.get(
                "max_aggregate_workers_per_codex_parent",
                limits.get("max_aggregate"),
            )
            if not _valid_positive_int(max_gemini) or not _valid_positive_int(max_aggregate):
                raise ValueError("worker capability limits must be positive integers")
            policy_source = str(worker_capability.get("policy_source", "capability"))
            policy_sha256 = str(worker_capability.get("policy_sha256", ""))
            gemini_worker = worker_capability.get("gemini_worker")
            gemini_profile = (
                gemini_worker.get("profile")
                if isinstance(gemini_worker, Mapping)
                else None
            )
            policy_selection = worker_capability.get("policy_selection")
            if policy_selection is not None:
                if policy_selection == TRIPLE_POOL:
                    from .native_capacity import validate_triple_capability
                    validate_triple_capability(worker_capability, parent_family)
                    max_luna = 4
                    max_sonnet = 4
                    allowed_worker_kinds = worker_capability.get("allowed_worker_kinds")
                    borrowing = False
                elif policy_selection == DUAL_POOL:
                    raise WorkerPolicyError("historical two-pool authority requires its pinned controller generation")
                else:
                    raise WorkerPolicyError(
                        f"unknown optional worker policy selection {policy_selection!r}"
                    )
            if policy_path is not None and policy_sha256:
                _, checked_source, checked_sha256 = load_worker_policy(
                    root, policy_path
                )
                if checked_sha256 != policy_sha256:
                    raise WorkerPolicyError(
                        "worker policy changed after capability resolution"
                    )
                if policy_source not in {"capability", checked_source}:
                    advertised_path = (root / policy_source).resolve()
                    checked_path = (root / checked_source).resolve()
                    if advertised_path != checked_path:
                        raise WorkerPolicyError(
                            "worker policy source differs from capability provenance"
                        )
        else:
            policy_data, policy_source, policy_sha256 = load_worker_policy(
                root, policy_path
            )
            max_gemini = policy_data["limits"]["max_gemini_workers_per_parent"]
            gemini_profile = policy_data["gemini_worker"]["profile"]
            if parent_family == "codex_parent":
                raise WorkerPolicyError("Codex parents require a bound current three-pool capability")
            max_aggregate = max_gemini


        if not isinstance(gemini_profile, str) or not gemini_profile:
            raise WorkerPolicyError("worker policy must freeze a Gemini profile")
        max_sonnet = 4 if policy_selection == TRIPLE_POOL else None
        if policy_selection == TRIPLE_POOL:
            max_luna = 4
        if custom_limits is not None:
            accepted_limit_keys = {"max_gemini", "max_aggregate"}
            if policy_selection in (DUAL_POOL, TRIPLE_POOL):
                accepted_limit_keys.add("max_luna")
            if policy_selection == TRIPLE_POOL:
                accepted_limit_keys.add("max_sonnet")
            for key in custom_limits:
                if key not in accepted_limit_keys:
                    raise ValueError(f"unknown worker limit {key!r}")
                if not _valid_positive_int(custom_limits[key]):
                    raise ValueError(f"worker limit {key!r} must be a positive integer")
            if "max_gemini" in custom_limits:
                if custom_limits["max_gemini"] > max_gemini:
                    raise ValueError("test limits may only reduce the Gemini budget")
                max_gemini = custom_limits["max_gemini"]
            if "max_aggregate" in custom_limits:
                if custom_limits["max_aggregate"] > max_aggregate:
                    raise ValueError("test limits may only reduce the aggregate budget")
                max_aggregate = custom_limits["max_aggregate"]
            if "max_luna" in custom_limits:
                if max_luna is None or custom_limits["max_luna"] > max_luna:
                    raise ValueError("test limits may only reduce the Luna budget")
                max_luna = custom_limits["max_luna"]
            if "max_sonnet" in custom_limits:
                if max_sonnet is None or custom_limits["max_sonnet"] > max_sonnet:
                    raise ValueError("test limits may only reduce the Sonnet budget")
                max_sonnet = custom_limits["max_sonnet"]
        if not _valid_positive_int(max_gemini) or not _valid_positive_int(max_aggregate):
            raise ValueError("worker limits must be positive integers")
        if policy_selection in (DUAL_POOL, TRIPLE_POOL) and not _valid_positive_int(max_luna):
            raise ValueError("Luna limit must be a positive integer")
        if policy_selection == TRIPLE_POOL and not _valid_positive_int(max_sonnet):
            raise ValueError("Sonnet limit must be a positive integer")
        capability_snapshot = (
            _copy(dict(worker_capability)) if worker_capability is not None else None
        )
        worker_allowed = (
            bool(worker_capability.get("allowed", True))
            if worker_capability is not None
            else True
        )

        with self._locked() as data:
            # Another process may have won registration while policy was read.
            if data:
                self._validate_parent_context(data, parent_family, root, task_authority)
                return _copy(data)
            now = time.time()
            policy_snapshot = {
                "policy_source": policy_source,
                "policy_sha256": policy_sha256,
                "max_gemini": max_gemini,
                "max_aggregate": max_aggregate,
                "gemini_profile": gemini_profile,
            }
            if policy_selection == TRIPLE_POOL:
                init_triple_pool_policy_snapshot(policy_snapshot, max_luna, max_sonnet)
            elif policy_selection == DUAL_POOL:
                policy_snapshot.update(
                    {
                        "policy_selection": policy_selection,
                        "max_luna": max_luna,
                        "borrowing": borrowing,
                    }
                )
            data.update(
                {
                    "schema": SCHEMA_V2 if policy_selection == TRIPLE_POOL else SCHEMA_NAME,
                    "parent_id": self.parent_id,
                    "parent_family": parent_family,
                    "workspace": str(root),
                    "task_authority": task_authority,
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                    "worker_allowed": worker_allowed,
                    "policy": policy_snapshot,
                    "worker_capability": capability_snapshot,
                    "gemini_jobs": {},
                    "native_agents": {},
                    "unmatched_native_events": [],
                }
            )
            if policy_selection == TRIPLE_POOL:
                init_triple_pool_data(data, parent_family, allowed_worker_kinds)
            return _copy(data)

    # Stable public spelling used by the CLI and dispatcher.
    register = initialize_parent

    def reap_stale_processes(self) -> list[str]:
        """Reconcile dead supervisors and return slots safely released."""
        with self._locked():
            return list(self._recently_reaped)

    def get_job(self, job_id: str) -> dict[str, Any]:
        """Return one job snapshot after conservative stale reconciliation."""
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                raise KeyError(f"job {job_id} not found under parent {self.parent_id}")
            return _job_snapshot(job)

    def get_status(self) -> dict[str, Any]:
        """Read current capacity without exposing mutable ledger structures."""
        with self._locked() as data:
            if not data:
                return {
                    "parent_id": self.parent_id,
                    "registered": False,
                    "gemini_count": 0,
                    "native_count": 0,
                    "max_gemini": DEFAULT_MAX_GEMINI,
                    "max_aggregate": DEFAULT_MAX_AGGREGATE_ASTRA,
                }

            policy = data.get("policy") or {}
            max_gemini = policy.get("max_gemini", DEFAULT_MAX_GEMINI)
            max_aggregate = policy.get("max_aggregate", DEFAULT_MAX_AGGREGATE_ASTRA)
            jobs = data.get("gemini_jobs") or {}
            natives = data.get("native_agents") or {}
            active_gemini = [
                j for j in jobs.values()
                if isinstance(j, dict) and j.get("status") in ACTIVE_GEMINI_STATES
            ]
            active_native = [
                a for a in natives.values()
                if isinstance(a, dict) and a.get("status") in ACTIVE_NATIVE_STATES
            ]
            g_count = len(active_gemini)
            l_count = len(active_native)
            status = {
                "parent_id": self.parent_id,
                "registered": data.get("status") == "active",
                "status": data.get("status"),
                "parent_family": data.get("parent_family"),
                "task_authority": data.get("task_authority"),
                "workspace": data.get("workspace"),
                "worker_allowed": data.get("worker_allowed", False),
                "worker_capability": _copy(data.get("worker_capability")),
                "policy": _copy(policy),
                "gemini_count": g_count,
                "native_count": l_count,
                "aggregate_count": g_count + l_count,
                "max_gemini": max_gemini,
                "max_aggregate": max_aggregate,
                "gemini_remaining": max(0, max_gemini - g_count),
                "aggregate_remaining": max(0, max_aggregate - (g_count + l_count)),
                "active_gemini_jobs": [j.get("job_id") for j in active_gemini],
                "active_native_agents": [a.get("agent_id") for a in active_native],
                "unmatched_native_event_count": len(data.get("unmatched_native_events") or []),
            }
            if is_triple_pool(data):
                return build_triple_pool_status(
                    data, status, l_count, ACTIVE_GEMINI_STATES,
                    _active_external_count, _job_worker_kind, _copy,
                )

            if not _is_dual_pool(data):
                return status

            jobs = data.get("gemini_jobs") or {}
            external_gemini = _active_external_count(jobs, "gemini")
            external_luna = _active_external_count(jobs, "luna")
            limits = {
                "gemini": max_gemini,
                "luna": policy.get("max_luna", 4),
            }
            pools = _copy(data.get("pool_state") or {})
            native = _copy(data.get("native_occupancy"))
            if not isinstance(native, dict):
                native = {
                    "status": "unknown",
                    "count": None,
                    "owner": "codex_runtime"
                    if data.get("parent_family") == "codex_astra"
                    else "none",
                }
            status.update(
                {
                    "policy_selection": DUAL_POOL,
                    "allowed_worker_kinds": _copy(data.get("allowed_worker_kinds") or []),
                    # Keep the historical keys meaningful for a dual context:
                    # ``gemini_count`` is Gemini-only, while the separate
                    # external counts make the independent pools explicit.
                    "gemini_count": external_gemini,
                    "gemini_remaining": max(0, limits["gemini"] - external_gemini),
                    "luna_count": external_luna,
                    "luna_remaining": max(0, limits["luna"] - external_luna),
                    "external_gemini_count": external_gemini,
                    "external_luna_count": external_luna,
                    "external_counts": {
                        "gemini": external_gemini,
                        "luna": external_luna,
                    },
                    "external_remaining": {
                        "gemini": max(0, limits["gemini"] - external_gemini),
                        "luna": max(0, limits["luna"] - external_luna),
                    },
                    "max_luna": limits["luna"],
                    "native_count": None,
                    "native_open_count": native.get("count"),
                    "native_open_count_status": native.get("status", "unknown"),
                    "native_occupancy": native,
                    "aggregate_count": external_gemini + external_luna,
                    "aggregate_remaining": max(
                        0, max_aggregate - (external_gemini + external_luna)
                    ),
                    "aggregate_admission": "informational",
                    "native_admission": "codex_runtime"
                    if data.get("parent_family") == "codex_astra"
                    else "none",
                    "pool_state": pools,
                    "paused_pools": [
                        kind
                        for kind in EXTERNAL_WORKER_KINDS
                        if isinstance(pools.get(kind), Mapping)
                        and pools[kind].get("paused") is True
                    ],
                    "active_external_jobs": [
                        j.get("job_id")
                        for j in jobs.values()
                        if isinstance(j, dict)
                        and j.get("status") in ACTIVE_GEMINI_STATES
                    ],
                    "active_gemini_jobs": [
                        j.get("job_id")
                        for j in jobs.values()
                        if isinstance(j, dict)
                        and j.get("status") in ACTIVE_GEMINI_STATES
                        and _job_worker_kind(j) == "gemini"
                    ],
                    "active_luna_jobs": [
                        j.get("job_id")
                        for j in jobs.values()
                        if isinstance(j, dict)
                        and j.get("status") in ACTIVE_GEMINI_STATES
                        and _job_worker_kind(j) == "luna"
                    ],
                }
            )
            return status

    def reserve_gemini(
        self,
        job_id: str,
        idempotency_key: str,
        payload_hash: str,
        task_authority: str = "read_only",
        task_file: str | None = None,
        *,
        worker_kind: str = "gemini",
        task_id: str | None = None,
        previous_job_id: str | None = None,
        recovery_decision: str | None = None,
        recovery_reason: str | None = None,
        mutation_scope: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """Atomically admit and reserve one external worker job.

        ``gemini_jobs`` is retained as the persisted collection name for
        compatibility.  A legacy entry without ``worker_kind`` is Gemini;
        selected dual-pool parents count Gemini and Luna independently.
        """
        if not isinstance(job_id, str) or not job_id:
            raise ValueError("job_id must be a non-empty string")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise ValueError("idempotency_key must be a non-empty string")
        if task_authority not in TASK_AUTHORITIES:
            raise ValueError("task_authority must be read_only or mutation_capable")
        if task_id is not None:
            _nonempty_text(task_id, "task_id")
        if previous_job_id is not None:
            _nonempty_text(previous_job_id, "previous_job_id")
        normalized_scope = _normalize_mutation_scope(mutation_scope)
        if task_authority == "read_only" and normalized_scope:
            raise AuthorityViolationError(
                "read-only worker cannot claim a mutation scope"
            )
        with self._locked() as data:
            if not data or data.get("status") != "active":
                raise ParentNotFoundError(
                    f"parent {self.parent_id} is not registered or active"
                )
            _validate_worker_kind(data, worker_kind)
            parent_authority = data.get("task_authority", "read_only")
            if parent_authority == "read_only" and task_authority != "read_only":
                raise AuthorityViolationError(
                    "read-only parent cannot launch mutation-capable worker"
                )

            jobs = data.setdefault("gemini_jobs", {})
            for existing_id, existing in jobs.items():
                if not isinstance(existing, dict):
                    continue
                if existing.get("idempotency_key") == idempotency_key:
                    if (
                        existing.get("payload_hash") != payload_hash
                        or _job_worker_kind(existing) != worker_kind
                        or existing.get("task_id") != task_id
                        or existing.get("previous_job_id") != previous_job_id
                        or "mutation_scope" in existing and _normalize_mutation_scope(existing.get("mutation_scope")) != normalized_scope
                    ):
                        raise IdempotencyConflictError(
                            f"idempotency key {idempotency_key} reused with differing task content"
                        )
                    return _job_snapshot(existing)
                if existing_id == job_id:
                    if (
                        existing.get("payload_hash") != payload_hash
                        or _job_worker_kind(existing) != worker_kind
                        or "mutation_scope" in existing and _normalize_mutation_scope(existing.get("mutation_scope")) != normalized_scope
                    ):
                        raise IdempotencyConflictError(f"job ID {job_id} already exists")
                    return _job_snapshot(existing)

            effective_task_id, attempt, recovery = _recovery_lineage(
                jobs,
                job_id=job_id,
                task_id=task_id,
                previous_job_id=previous_job_id,
                recovery_decision=recovery_decision,
                recovery_reason=recovery_reason,
            )
            if task_authority == "mutation_capable" and normalized_scope:
                for existing in [*jobs.values(), *(data.get("native_agents") or {}).values()]:
                    if not isinstance(existing, Mapping):
                        continue
                    if existing.get("status") not in ACTIVE_GEMINI_STATES | ACTIVE_NATIVE_STATES:
                        continue
                    if existing.get("task_authority") != "mutation_capable":
                        continue
                    for current_scope in _normalize_mutation_scope(
                        existing.get("mutation_scope")
                    ):
                        if any(
                            _scopes_overlap(current_scope, requested_scope)
                            for requested_scope in normalized_scope
                        ):
                            raise AuthorityViolationError(
                                "mutation scope overlaps an active worker scope"
                            )
            if is_historical_ledger(data):
                raise PinnedControllerError(PINNED_CONTROLLER_DIAGNOSTIC)

            pool = _pool_state(data, worker_kind)
            if isinstance(pool, Mapping) and pool.get("paused") is True:
                cause = pool.get("cause") or "parent paused this pool"
                raise PoolPausedError(
                    f"{worker_kind} worker pool is paused: {cause}"
                )

            policy = data.get("policy") or {}
            max_gemini = policy.get("max_gemini", DEFAULT_MAX_GEMINI)
            max_aggregate = policy.get("max_aggregate", DEFAULT_MAX_AGGREGATE_ASTRA)
            g_count = _active_external_count(jobs, "gemini")
            natives = data.get("native_agents") or {}
            l_count = sum(
                1 for a in natives.values()
                if isinstance(a, dict) and a.get("status") in ACTIVE_NATIVE_STATES
            )
            if is_triple_pool(data):
                check_triple_pool_capacity(
                    worker_kind, g_count, max_gemini, jobs, policy, _active_external_count
                )
            elif _is_dual_pool(data):
                if worker_kind == "gemini":
                    if g_count >= max_gemini:
                        raise CapacityExceededError(
                            f"Gemini capacity limit reached: {g_count}/{max_gemini} active"
                        )
                else:
                    max_luna = policy.get("max_luna", 4)
                    luna_count = _active_external_count(jobs, "luna")
                    if luna_count >= max_luna:
                        raise CapacityExceededError(
                            f"Luna capacity limit reached: {luna_count}/{max_luna} active"
                        )
            else:
                if g_count >= max_gemini:
                    raise CapacityExceededError(
                        f"Gemini capacity limit reached: {g_count}/{max_gemini} active"
                    )
                if data.get("parent_family") == "codex_astra" and g_count + l_count >= max_aggregate:
                    raise CapacityExceededError(
                        f"Aggregate capacity limit reached: G={g_count} + L={l_count} = "
                        f"{g_count + l_count}/{max_aggregate} active"
                    )

            now = time.time()
            job = {
                "job_id": job_id,
                "idempotency_key": idempotency_key,
                "payload_hash": payload_hash,
                "status": "reserved",
                "task_authority": task_authority,
                "created_at": now,
                "updated_at": now,
                "supervisor_pid": None,
                "supervisor_pgid": None,
                "supervisor_identity": None,
                "supervisor_bound": False,
                "launch_claimed": False,
                "provider_pid": None,
                "provider_pgid": None,
                "provider_identity": None,
                "task_file": task_file,
                "mutation_scope": normalized_scope,
                "result": None,
                "error": None,
                "cleanup_proven": False,
                "worker_kind": worker_kind,
                "task_id": effective_task_id,
                "previous_job_id": previous_job_id,
                "attempt": attempt,
                "attempt_number": attempt,
                "lineage_id": (
                    recovery.get("lineage_id")
                    if isinstance(recovery, Mapping)
                    else effective_task_id or job_id
                ),
                "recovery_decision": recovery_decision,
                "recovery_reason": recovery_reason,
                "recovery": recovery,
                "provider_status": "reserved",
                "task_outcome": "unknown",
                "task_outcome_evidence": None,
                "cleanup_status": "unknown",
                "abandonment": None,
            }
            if data.get("parent_family") == "gemini_flash":
                from .gemini_parent import worker_provenance
                job["worker_provenance"] = worker_provenance(data["worker_capability"], worker_kind)
            jobs[job_id] = job
            return _job_snapshot(job)

    def reserve_external(
        self,
        job_id: str,
        idempotency_key: str,
        payload_hash: str,
        task_authority: str = "read_only",
        task_file: str | None = None,
        *,
        worker_kind: str = "gemini",
        task_id: str | None = None,
        previous_job_id: str | None = None,
        recovery_decision: str | None = None,
        recovery_reason: str | None = None,
        mutation_scope: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """Alias for callers that need to name the external pool explicitly."""
        return self.reserve_gemini(
            job_id,
            idempotency_key,
            payload_hash,
            task_authority,
            task_file,
            worker_kind=worker_kind,
            task_id=task_id,
            previous_job_id=previous_job_id,
            recovery_decision=recovery_decision,
            recovery_reason=recovery_reason,
            mutation_scope=mutation_scope,
        )

    reserve_worker = reserve_external

    def pause_pool(
        self, kind: str, cause: str, evidence: Any
    ) -> dict[str, Any]:
        """Pause new reservations for one external pool until resumed.

        Existing reservations remain occupied and are never terminated by this
        bookkeeping operation.  A caller must provide an observable cause and
        evidence; the ledger does not infer quota exhaustion from a stall.
        """
        _nonempty_text(cause, "cause")
        if kind not in EXTERNAL_WORKER_KINDS:
            raise ValueError("pool kind must be gemini, luna, or sonnet")
        if evidence is None or evidence == "":
            raise ValueError("evidence is required to pause a pool")
        with self._locked() as data:
            return apply_pool_pause(data, kind, cause, evidence, self.parent_id)

    def resume_pool(self, kind: str, evidence: Any) -> dict[str, Any]:
        """Resume a paused external pool only with fresh operator evidence."""
        if kind not in EXTERNAL_WORKER_KINDS:
            raise ValueError("pool kind must be gemini, luna, or sonnet")
        if evidence is None or evidence == "":
            raise ValueError("evidence is required to resume a pool")
        with self._locked() as data:
            if not data or data.get("status") not in {"active", "draining"}:
                raise ParentNotFoundError(
                    f"parent {self.parent_id} is not registered"
                )
            _validate_worker_kind(data, kind)
            pool = _pool_state(data, kind, create=True)
            assert pool is not None
            if pool.get("paused") is not True:
                raise RecoveryConflictError(f"{kind} worker pool is not paused")
            now = time.time()
            pool.update(
                {
                    "paused": False,
                    "resume_evidence": _copy(evidence),
                    "resumed_at": now,
                }
            )
            return _copy(pool)

    # Keep both spellings available to provider-specific callers.
    unpause_pool = resume_pool

    def record_abandonment(self, job_id: str, reason: str) -> dict[str, Any]:
        """Record the parent's abandonment decision before any signal is sent.

        This does not signal a process or claim that cleanup completed.  The
        provider status, task outcome, and cleanup status remain separate so a
        useful partial result cannot be mistaken for a successful completion.
        """
        _nonempty_text(reason, "reason")
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                raise KeyError(f"job {job_id} not found")
            existing = job.get("abandonment")
            if isinstance(existing, Mapping):
                if existing.get("reason") != reason:
                    raise RecoveryConflictError(
                        "job abandonment was already recorded with another reason"
                    )
                return _job_snapshot(job)
            now = time.time()
            observed_status = job.get("status")
            cleanup_proven = _cleanup_proven(job)
            cleanup_status = job.get("cleanup_status")
            if cleanup_status not in {"proven", "unknown", "pending"}:
                cleanup_status = None
            if cleanup_status is None:
                cleanup_status = "proven" if cleanup_proven else "unknown"
            if observed_status in {"reserved", "starting", "launched", "running"}:
                job["status"] = "stopping"
                job["provider_status"] = observed_status
                cleanup_status = "pending"
            job["abandonment"] = {
                "decision": "abandon",
                "reason": reason,
                "decided_at": now,
                "observed_status": observed_status,
                "provider_status": job.get("provider_status", observed_status),
                "task_outcome": job.get("task_outcome", "unknown"),
                "cleanup_status": cleanup_status,
                "cleanup_proven": cleanup_proven,
                "custody": {
                    "supervisor_pid": job.get("supervisor_pid"),
                    "supervisor_pgid": job.get("supervisor_pgid"),
                    "supervisor_identity": job.get("supervisor_identity"),
                    "supervisor_bound": job.get("supervisor_bound"),
                    "launch_claimed": job.get("launch_claimed"),
                },
            }
            job["cancellation_decision"] = "abandon"
            job["cancellation_reason"] = reason
            job["cleanup_status"] = cleanup_status
            job["updated_at"] = now
            return _job_snapshot(job)

    def record_task_outcome(
        self, job_id: str, outcome: str, evidence: Any = None
    ) -> dict[str, Any]:
        """Persist semantic task outcome independently of provider status."""
        if outcome not in TASK_OUTCOMES:
            raise ValueError(
                "task outcome must be unknown, partial, accepted, rejected, failed, or cancelled"
            )
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                raise KeyError(f"job {job_id} not found")
            current = job.get("task_outcome", "unknown")
            if current not in {"unknown", outcome}:
                raise RecoveryConflictError(
                    f"task outcome already recorded as {current!r}"
                )
            job["task_outcome"] = outcome
            if evidence is not None:
                job["task_outcome_evidence"] = _copy(evidence)
            job["updated_at"] = time.time()
            return _job_snapshot(job)

    def claim_gemini_launch(self, job_id: str) -> tuple[bool, dict[str, Any]]:
        """Atomically claim the right to Popen a reserved job exactly once."""
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                raise KeyError(f"job {job_id} not found")
            if job.get("status") == "reserved":
                job["status"] = "starting"
                job["launch_claimed"] = True
                job["provider_status"] = "starting"
                job["updated_at"] = time.time()
                return True, _job_snapshot(job)
            return False, _job_snapshot(job)

    def record_gemini_launch(
        self,
        job_id: str,
        supervisor_pid: int,
        supervisor_pgid: int | None = None,
    ) -> bool:
        """Record launcher custody without admitting provider execution.

        The launcher owns the returned ``Popen`` object and therefore the
        obligation to reap it.  ``launched`` is deliberately distinct from
        ``running``: cancellation and drain may not signal this process until
        the supervisor has installed its handler and self-bound.
        """
        if not isinstance(supervisor_pid, int) or supervisor_pid <= 0:
            raise ValueError("supervisor_pid must be positive")
        if supervisor_pgid is None:
            supervisor_pgid = supervisor_pid
        if not isinstance(supervisor_pgid, int) or supervisor_pgid <= 0:
            raise ValueError("supervisor_pgid must be positive")
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                return False
            if job.get("status") in TERMINAL_GEMINI_STATES | {"orphaned", "stopping"}:
                return False
            if data.get("status") != "active":
                return False
            old_pid = job.get("supervisor_pid")
            if old_pid is not None:
                if old_pid != supervisor_pid:
                    return False
                old_pgid = job.get("supervisor_pgid")
                if old_pgid is not None and old_pgid != supervisor_pgid:
                    return False
                identity = job.get("supervisor_identity")
                return (
                    isinstance(identity, str)
                    and bool(identity)
                    and _process_identity(supervisor_pid) == identity
                )
            if job.get("status") != "starting" or job.get("launch_claimed") is not True:
                return False
            identity = _process_identity(supervisor_pid)
            if not isinstance(identity, str) or not identity:
                return False
            job["status"] = "launched"
            job["supervisor_pid"] = supervisor_pid
            job["supervisor_pgid"] = supervisor_pgid
            job["supervisor_identity"] = identity
            job["supervisor_bound"] = False
            job["provider_status"] = "launched"
            job["updated_at"] = time.time()
            return True

    def bind_gemini_supervisor(
        self,
        job_id: str,
        supervisor_pid: int,
        supervisor_pgid: int | None = None,
    ) -> bool:
        """Self-bind a supervisor after its stop handler is ready.

        A stopping job is monotonic: a late bind cannot turn it back into a
        running job.  The explicit bound marker lets cancellation distinguish
        a launcher-owned handoff from a supervisor ready to receive TERM.
        """
        if not isinstance(supervisor_pid, int) or supervisor_pid <= 0:
            raise ValueError("supervisor_pid must be positive")
        if supervisor_pgid is None:
            supervisor_pgid = supervisor_pid
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                return False
            if job.get("status") in TERMINAL_GEMINI_STATES | {"orphaned", "stopping"}:
                return False
            if data.get("status") != "active":
                return False
            old_pid = job.get("supervisor_pid")
            if old_pid is not None and old_pid != supervisor_pid:
                return False
            if job.get("launch_claimed") is not True:
                return False
            if old_pid is None:
                if job.get("status") != "starting":
                    return False
                identity = _process_identity(supervisor_pid)
                if not isinstance(identity, str) or not identity:
                    return False
                job["supervisor_pid"] = supervisor_pid
                job["supervisor_pgid"] = supervisor_pgid
                job["supervisor_identity"] = identity
            else:
                if job.get("status") not in {"launched", "running"}:
                    return False
                old_pgid = job.get("supervisor_pgid")
                if old_pgid is not None and old_pgid != supervisor_pgid:
                    return False
                identity = job.get("supervisor_identity")
                if (
                    not isinstance(identity, str)
                    or not identity
                    or _process_identity(supervisor_pid) != identity
                ):
                    return False
                if job.get("supervisor_bound") is True:
                    # Duplicate callbacks are idempotent and never rewrite
                    # the original owner identity or process group.
                    return True
            job["status"] = "running"
            job["supervisor_bound"] = True
            job["provider_status"] = "running"
            job["updated_at"] = time.time()
            return True

    def record_provider_custody(
        self,
        job_id: str,
        provider_pid: int,
        provider_pgid: int | None = None,
        *,
        supervisor_pid: int | None = None,
    ) -> dict[str, Any] | bool:
        """Persist a provider leader and process-group identity immediately.

        External providers run in a new session, so the supervisor's PID and
        PGID cannot identify the provider after the supervisor exits.  The
        provider leader is observed while it is live and its start-time/PGID
        identity is retained for a later, explicitly authorized cleanup.
        """
        if not _valid_positive_int(provider_pid):
            raise ValueError("provider_pid must be positive")
        if provider_pgid is not None and not _valid_positive_int(provider_pgid):
            raise ValueError("provider_pgid must be positive")
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                return False
            if job.get("status") not in ACTIVE_GEMINI_STATES:
                return False
            if supervisor_pid is not None:
                if job.get("supervisor_pid") != supervisor_pid:
                    return False
                if not supervisor_is_bound(job) or not supervisor_identity_matches(job):
                    return False
            try:
                current_pgid = os.getpgid(provider_pid)
            except (OSError, ProcessLookupError):
                return False
            if provider_pgid is None:
                provider_pgid = current_pgid
            if provider_pgid != current_pgid:
                return False
            identity = _process_identity(provider_pid)
            if not isinstance(identity, str) or not identity:
                return False
            old_pid = job.get("provider_pid")
            old_pgid = job.get("provider_pgid")
            old_identity = job.get("provider_identity")
            if old_pid is not None or old_pgid is not None or old_identity is not None:
                return _job_snapshot(job) if (
                    old_pid == provider_pid
                    and old_pgid == provider_pgid
                    and old_identity == identity
                ) else False
            job["provider_pid"] = provider_pid
            job["provider_pgid"] = provider_pgid
            job["provider_identity"] = identity
            job["provider_custody_status"] = "bound"
            job["updated_at"] = time.time()
            return _job_snapshot(job)

    def settle_provider_cleanup(
        self,
        job_id: str,
        receipt: Mapping[str, Any],
        *,
        provider_pgid: int | None = None,
    ) -> dict[str, Any]:
        """Record an explicit late provider cleanup observation.

        The adapter performs signals and bounded observation outside the ledger
        lock.  This method validates the recorded group identity, preserves
        the pre-reconciliation result, and releases capacity only when the
        receipt proves the exact provider group is absent.  A receipt with an
        ambiguous identity remains orphaned and occupied.
        """
        if not isinstance(receipt, Mapping):
            raise ValueError("provider cleanup receipt must be an object")
        receipt_copy = _copy(dict(receipt))
        if receipt_copy.get("explicit_control") is not True:
            raise RecoveryConflictError(
                "provider cleanup requires an explicit cancellation or abandonment"
            )
        receipt_pgid = receipt_copy.get("provider_pgid")
        if provider_pgid is None:
            provider_pgid = receipt_pgid
        if not _valid_positive_int(provider_pgid):
            raise ValueError("provider cleanup receipt requires a positive provider_pgid")
        if receipt_pgid is not None and receipt_pgid != provider_pgid:
            raise RecoveryConflictError("provider cleanup group identity changed")

        proven = receipt_copy.get("cleanup_proven") is True
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                raise KeyError(f"job {job_id} not found")
            recorded_pgid = job.get("provider_pgid")
            if recorded_pgid is None:
                result = job.get("result")
                observation = result.get("cleanup_observation") if isinstance(result, Mapping) else None
                if isinstance(observation, Mapping):
                    recorded_pgid = observation.get("provider_pgid")
            if recorded_pgid != provider_pgid:
                raise RecoveryConflictError("provider cleanup does not match recorded provider group")
            if job.get("provider_pgid") is None:
                # Preserve the old result's group observation for a legacy
                # journal, but do not invent a provider PID or identity.
                job["provider_pgid"] = provider_pgid

            receipts = job.setdefault("provider_cleanup_receipts", [])
            if not isinstance(receipts, list):
                receipts = []
                job["provider_cleanup_receipts"] = receipts
            receipts.append(receipt_copy)
            del receipts[:-8]
            job["provider_cleanup"] = receipt_copy
            if not proven:
                if job.get("status") in ACTIVE_GEMINI_STATES:
                    job["status"] = "orphaned"
                job["cleanup_proven"] = False
                job["cleanup_status"] = "unknown"
                job["provider_custody_status"] = "uncertain"
                job["updated_at"] = time.time()
                return _job_snapshot(job)

            original = job.get("result")
            if isinstance(original, Mapping):
                if "original_result" not in job:
                    job["original_result"] = _copy(original)
                reconciled = _copy(dict(original))
                reconciled["status"] = "cancelled"
                reconciled["cleanup_proven"] = True
                reconciled["cleanup_status"] = "proven"
                reconciled["cleanup_reconciliation"] = receipt_copy
                job["result"] = reconciled
            job["status"] = "cancelled"
            job["cleanup_proven"] = True
            job["cleanup_status"] = "proven"
            job["provider_custody_status"] = "released"
            job["updated_at"] = time.time()
            return _job_snapshot(job)

    def settle_gemini_supervisor_rejection(
        self,
        job_id: str,
        supervisor_pid: int,
        *,
        error: str = "parent closed before supervisor bind",
    ) -> bool:
        """Terminalize only the same unbound owner that failed before bind.

        A second supervisor may observe a rejected bind after another process
        owns the job.  Its PID cannot settle or release that owner's record.
        The same recorded owner may settle an unbound handoff because it has
        not admitted provider execution.  A stopping owner becomes cancelled;
        an otherwise active owner becomes failed.  The operation is kept under
        the ledger lock so an old snapshot cannot release a newer owner.

        Callers must invoke this only before any provider process has been
        spawned for this job; the method cannot verify that and records
        cleanup_proven on that basis.
        """
        if not isinstance(supervisor_pid, int) or supervisor_pid <= 0:
            raise ValueError("supervisor_pid must be positive")
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                return False
            if job.get("status") not in {"launched", "stopping", "orphaned"}:
                return False
            if job.get("supervisor_pid") != supervisor_pid:
                return False
            if job.get("supervisor_bound") is not False:
                return False
            if job.get("launch_claimed") is not True:
                return False
            identity = job.get("supervisor_identity")
            if (
                not isinstance(identity, str)
                or not identity
                or _process_identity(supervisor_pid) != identity
            ):
                return False
            job["status"] = (
                "cancelled" if job.get("status") == "stopping" else "failed"
            )
            job["error"] = error
            job["cleanup_proven"] = True
            job["provider_status"] = job["status"]
            job["cleanup_status"] = "proven"
            job["updated_at"] = time.time()
            return True

    def settle_gemini_launch_exit(
        self,
        job_id: str,
        supervisor_pid: int,
        *,
        error: str = "supervisor exited before bind",
    ) -> bool:
        """Settle an owned unbound supervisor after its launcher reaps it.

        The launcher owns the ``Popen`` wait status.  Once that owner has
        reaped a supervisor whose recorded PID is still unbound, no provider
        could have been admitted through this job.  A bound record is left
        alone for its supervisor's cleanup attestation path.  If the process
        exited before its PID was recorded, the launcher's no-PID failure path
        settles the reservation separately.
        """
        if not isinstance(supervisor_pid, int) or supervisor_pid <= 0:
            raise ValueError("supervisor_pid must be positive")
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                return False
            if job.get("status") in TERMINAL_GEMINI_STATES:
                return True
            if job.get("supervisor_pid") != supervisor_pid:
                return False
            if job.get("supervisor_bound") is True:
                return False
            if job.get("status") not in {"launched", "stopping", "orphaned"}:
                return False
            # ``_locked`` performs stale-PID observation before entering this
            # method.  A dead, unbound supervisor may therefore already be
            # marked orphaned; the launcher wait is the stronger owner proof,
            # but a surviving process group still requires custody.
            if job.get("status") == "orphaned" and _process_group_is_present(
                job.get("supervisor_pgid")
            ):
                return False
            job["status"] = "cancelled" if job.get("status") == "stopping" else "failed"
            job["error"] = error
            job["cleanup_proven"] = True
            job["provider_status"] = job["status"]
            job["cleanup_status"] = "proven"
            job["updated_at"] = time.time()
            return True

    def set_gemini_task_file(self, job_id: str, task_file: str) -> bool:
        """Persist the task path after an atomic launch claim."""
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict) or job.get("status") not in ACTIVE_GEMINI_STATES:
                return False
            job["task_file"] = task_file
            job["updated_at"] = time.time()
            return True

    def begin_gemini_stop(self, job_id: str) -> dict[str, Any]:
        """Mark a job stopping without releasing its capacity."""
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                raise KeyError(f"job {job_id} not found")
            if job.get("status") in {"reserved", "starting", "launched", "running"}:
                job["status"] = "stopping"
                job["provider_status"] = "stopping"
                if job.get("abandonment") is not None:
                    job["cancellation_decision"] = "abandon"
                job["updated_at"] = time.time()
            return _job_snapshot(job)

    def update_gemini_status(
        self,
        job_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        *,
        cleanup_proven: bool | None = None,
        task_outcome: str | None = None,
        task_outcome_evidence: Any = None,
    ) -> bool:
        """Apply an idempotent job state update with cleanup gating."""
        if status not in GEMINI_STATES:
            raise ValueError(f"unknown Gemini job status {status!r}")
        result_outcome = (
            result.get("task_outcome")
            if isinstance(result, Mapping)
            else None
        )
        if task_outcome is None and result_outcome in TASK_OUTCOMES:
            # Provider ``success`` is intentionally not in TASK_OUTCOMES:
            # exit zero is provider evidence, not semantic acceptance.
            task_outcome = result_outcome
        if task_outcome is not None and task_outcome not in TASK_OUTCOMES:
            raise ValueError(
                "task outcome must be unknown, partial, accepted, rejected, failed, or cancelled"
            )
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                return False
            current = job.get("status")
            if current in TERMINAL_GEMINI_STATES:
                if task_outcome is not None and job.get("task_outcome", "unknown") == "unknown":
                    job["task_outcome"] = task_outcome
                    if task_outcome_evidence is not None:
                        job["task_outcome_evidence"] = _copy(task_outcome_evidence)
                    job["updated_at"] = time.time()
                return True
            requested_status = status
            proven = bool(cleanup_proven)
            if result is not None and result.get("cleanup_proven") is True:
                proven = True
            # A stop request owns the terminal disposition.  A provider result
            # or stale lifecycle event arriving afterward must not resurrect
            # the job as running/completed.
            if current == "stopping" and status not in {"cancelled", "orphaned"}:
                status = "cancelled" if proven else "orphaned"
            if status in TERMINAL_GEMINI_STATES and not proven:
                status = "orphaned"
            job["status"] = status
            if result is not None:
                result_copy = _copy(result)
                if status in {"cancelled", "orphaned"}:
                    result_copy["status"] = status
                if status == "orphaned":
                    result_copy["error"] = error or result_copy.get("error") or "worker_cleanup_unproven"
                job["result"] = result_copy
            if error is not None:
                job["error"] = error
            job["cleanup_proven"] = proven
            provider_status = (
                result.get("provider_terminal_status")
                if isinstance(result, Mapping)
                else None
            )
            job["provider_status"] = (
                provider_status
                if isinstance(provider_status, str) and provider_status
                else requested_status
            )
            result_cleanup_status = (
                result.get("cleanup_status")
                if isinstance(result, Mapping)
                else None
            )
            job["cleanup_status"] = (
                result_cleanup_status
                if isinstance(result_cleanup_status, str) and result_cleanup_status
                else "proven" if proven else "unknown"
            )
            if task_outcome is not None and job.get("task_outcome", "unknown") == "unknown":
                job["task_outcome"] = task_outcome
                if task_outcome_evidence is not None:
                    job["task_outcome_evidence"] = _copy(task_outcome_evidence)
            job["updated_at"] = time.time()
            return True

    def fail_gemini_launch(self, job_id: str, error: str) -> bool:
        """Terminalize a pre-Popen launch failure and safely free its slot."""
        with self._locked() as data:
            job = (data.get("gemini_jobs") or {}).get(job_id)
            if not isinstance(job, dict):
                return False
            if job.get("supervisor_pid") is not None:
                return False
            if job.get("status") in TERMINAL_GEMINI_STATES:
                return True
            job["status"] = "cancelled" if job.get("status") == "stopping" else "failed"
            job["error"] = error
            job["cleanup_proven"] = True
            job["provider_status"] = job["status"]
            job["cleanup_status"] = "proven"
            job["updated_at"] = time.time()
            return True

    def reserve_native(self, agent_id: str, agent_type: str = "luna", *,
                       task_authority: str = "read_only", mutation_scope=None) -> tuple[bool, str]:
        """Atomically reserve one native slot under the parent ledger lock."""
        scope = _normalize_mutation_scope(mutation_scope)
        if task_authority not in TASK_AUTHORITIES or (task_authority == "read_only" and scope):
            raise AuthorityViolationError("invalid native task authority or read-only mutation scope")
        if task_authority == "mutation_capable" and not scope:
            raise AuthorityViolationError("native writer requires mutation scope")
        with self._locked() as data:
            if data.get("task_authority") == "read_only" and task_authority != "read_only":
                raise AuthorityViolationError("read-only parent cannot launch a native writer")
            agents = data.get("native_agents") or {}
            existing = agents.get(agent_id)
            if existing and (existing.get("task_authority", "read_only") != task_authority
                             or _normalize_mutation_scope(existing.get("mutation_scope")) != scope):
                raise IdempotencyConflictError("native identity reused with different authority or scope")
            for current in [*(data.get("gemini_jobs") or {}).values(), *agents.values()]:
                if not isinstance(current, Mapping) or current.get("agent_id") == agent_id:
                    continue
                if current.get("status") not in ACTIVE_GEMINI_STATES | ACTIVE_NATIVE_STATES:
                    continue
                if any(_scopes_overlap(a, b) for a in scope
                       for b in _normalize_mutation_scope(current.get("mutation_scope"))):
                    raise AuthorityViolationError("mutation scope overlaps an active worker scope")
            admitted, reason = reserve_native_agent_slot(data, agent_id, agent_type, ACTIVE_NATIVE_STATES)
            record = (data.get("native_agents") or {}).get(agent_id)
            if admitted and record:
                record.update(task_authority=task_authority, mutation_scope=scope)
            return admitted, reason

    def activate_native(self, agent_id: str, agent_type: str = "luna") -> tuple[bool, str]:
        """Bind a native start event only to an existing reservation."""
        with self._locked() as data:
            return activate_native_agent_slot(data, agent_id, agent_type)

    def rollback_native(self, agent_id: str) -> bool:
        """Remove a reservation after a proven native launch failure."""
        with self._locked() as data:
            return rollback_native_agent_slot(data, agent_id)

    def close_native(self, agent_id: str) -> bool:
        """Release native capacity only on explicit verified thread closure."""
        with self._locked() as data:
            return close_native_agent_slot(data, agent_id, ACTIVE_NATIVE_STATES)

    def reserve_native_agent(self, agent_id: str, agent_type: str = "luna") -> dict[str, Any]:
        """Reserve a native agent and raise on a capacity denial."""
        admitted, reason = self.reserve_native(agent_id, agent_type)
        if not admitted:
            raise CapacityExceededError(reason)
        status = "runtime_owned" if reason == "native_admission_owned_by_codex_runtime" else "reserved"
        return {
            "status": status,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "admission_owner": "codex_runtime" if status == "runtime_owned" else "ledger",
        }

    def drain_and_close(self, timeout_seconds: float = 15.0, *, parent_exit_observed: bool = False) -> dict[str, Any]:
        """Drain owned workers and close the parent after cleanup accounting.

        The supervisor receives TERM first so its provider adapter can perform
        nested process-group cleanup.  A process-group kill is an escalation
        only; if the provider evidence is absent the job remains orphaned and
        the summary reports uncertain cleanup.
        """
        timeout_seconds = max(float(timeout_seconds), 0.0)
        cancelled_jobs: list[str] = []
        with self._locked() as data:
            if not data:
                return {
                    "parent_id": self.parent_id,
                    "status": "closed",
                    "cancelled_jobs": [],
                    "uncertain_cleanup": False,
                }
            data["status"] = "draining"
            jobs = data.get("gemini_jobs") or {}
            active_jobs = []
            for job in jobs.values():
                if isinstance(job, dict) and job.get("status") in ACTIVE_GEMINI_STATES:
                    if (
                        job.get("status") in {"reserved", "stopping"}
                        and job.get("supervisor_pid") is None
                        and job.get("launch_claimed") is not True
                    ):
                        # No launcher claimed this reservation, so there is no
                        # Popen owner or provider process to drain.
                        job["status"] = "cancelled"
                        job["cleanup_proven"] = True
                        job["provider_status"] = "cancelled"
                        job["cleanup_status"] = "proven"
                        job["updated_at"] = time.time()
                        cancelled_jobs.append(str(job.get("job_id")))
                        continue
                    if job.get("status") in {"reserved", "starting", "launched", "running"}:
                        job["status"] = "stopping"
                        job["updated_at"] = time.time()
                    active_jobs.append(_copy(job))

        def current(job_id: str) -> dict[str, Any] | None:
            try:
                return self.get_job(job_id)
            except KeyError:
                return None
            except LedgerError:
                return None

        # Forward TERM to the supervisor itself.  The supervisor owns the
        # provider wrapper and will then invoke the Antigravity nested-group
        # cleanup contract.
        for job in active_jobs:
            pid = job.get("supervisor_pid")
            if (
                supervisor_is_bound(job)
                and isinstance(pid, int)
                and pid > 0
                and supervisor_identity_matches(job)
            ):
                try:
                    os.kill(pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            pending = []
            for job in active_jobs:
                snapshot = current(job["job_id"])
                if snapshot is None:
                    continue
                if snapshot.get("status") in TERMINAL_GEMINI_STATES and _cleanup_proven(snapshot):
                    continue
                pending.append(snapshot)
            if not pending:
                break
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))

        # Escalate only the outer supervisor group after the graceful window.
        # Nested provider groups may be outside that group; absent evidence is
        # therefore kept uncertain rather than declared clean.
        for job in active_jobs:
            snapshot = current(job["job_id"])
            if snapshot is None:
                continue
            if snapshot.get("status") in TERMINAL_GEMINI_STATES and _cleanup_proven(snapshot):
                continue
            pgid = snapshot.get("supervisor_pgid") or job.get("supervisor_pgid")
            if (
                supervisor_is_bound(snapshot)
                and isinstance(pgid, int)
                and pgid > 0
                and supervisor_identity_matches(snapshot)
            ):
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass

        # Give the result writer a short chance after escalation, then freeze
        # the parent.  Never mark an unproven job terminal just to clear a slot.
        final_deadline = time.monotonic() + min(1.0, timeout_seconds)
        while time.monotonic() < final_deadline:
            if all(
                (snap := current(job["job_id"])) is None
                or (
                    snap.get("status") in TERMINAL_GEMINI_STATES
                    and _cleanup_proven(snap)
                )
                for job in active_jobs
            ):
                break
            time.sleep(min(0.05, max(0.0, final_deadline - time.monotonic())))

        uncertain_cleanup = False
        with self._locked() as data:
            for job in (data.get("gemini_jobs") or {}).values():
                if not isinstance(job, dict) or job.get("status") not in ACTIVE_GEMINI_STATES:
                    continue
                if (
                    job.get("status") in {"reserved", "stopping"}
                    and job.get("supervisor_pid") is None
                    and job.get("launch_claimed") is not True
                ):
                    # No launch owner claimed Popen; no child can execute.
                    job["status"] = "cancelled"
                    job["cleanup_proven"] = True
                    job["provider_status"] = "cancelled"
                    job["cleanup_status"] = "proven"
                    job["updated_at"] = time.time()
                    cancelled_jobs.append(str(job.get("job_id")))
                else:
                    # A claimed launch with no settled handoff remains in
                    # custody.  Do not guess that Popen never happened.
                    job["status"] = "orphaned"
                    job["cleanup_proven"] = False
                    job["error"] = job.get("error") or "worker_cleanup_unproven"
                    job["provider_status"] = job.get("provider_status") or "unknown"
                    job["cleanup_status"] = "unknown"
                    job["updated_at"] = time.time()
                    uncertain_cleanup = True
            if is_triple_pool(data):
                _, native_uncertain = drain_active_native_agents(data, ACTIVE_NATIVE_STATES, parent_exit_observed)
                if native_uncertain:
                    uncertain_cleanup = True
            else:
                native_pending = any(
                    isinstance(agent, dict) and agent.get("status") in ACTIVE_NATIVE_STATES
                    for agent in (data.get("native_agents") or {}).values()
                )
                if native_pending:
                    uncertain_cleanup = True
            data["status"] = "closed"

        return {
            "parent_id": self.parent_id,
            "status": "closed",
            "cancelled_jobs": cancelled_jobs,
            "uncertain_cleanup": uncertain_cleanup,
        }

    # The shared supervisor uses provider-neutral names when it handles a
    # Luna leaf.  Dispatch through the provider-specific method at call time
    # so legacy Gemini monkey-patches and journals retain their old surface.
    def bind_worker_supervisor(
        self,
        job_id: str,
        supervisor_pid: int,
        supervisor_pgid: int | None = None,
        *,
        worker_kind: str = "gemini",
    ) -> bool:
        method = getattr(self, f"bind_{worker_kind}_supervisor", None)
        if not callable(method):
            method = self.bind_gemini_supervisor
        return method(job_id, supervisor_pid, supervisor_pgid)

    def settle_worker_supervisor_rejection(
        self,
        job_id: str,
        supervisor_pid: int,
        *,
        error: str = "parent closed before supervisor bind",
        worker_kind: str = "gemini",
    ) -> bool:
        method = getattr(self, f"settle_{worker_kind}_supervisor_rejection", None)
        if not callable(method):
            method = self.settle_gemini_supervisor_rejection
        return method(job_id, supervisor_pid, error=error)

    def update_worker_status(
        self,
        job_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        *,
        cleanup_proven: bool | None = None,
        task_outcome: str | None = None,
        task_outcome_evidence: Any = None,
        worker_kind: str = "gemini",
    ) -> bool:
        method = getattr(self, f"update_{worker_kind}_status", None)
        if not callable(method):
            method = self.update_gemini_status
        return method(
            job_id,
            status,
            result=result,
            error=error,
            cleanup_proven=cleanup_proven,
            task_outcome=task_outcome,
            task_outcome_evidence=task_outcome_evidence,
        )
