"""Immutable, bounded observation of existing worker custody; never reconciliation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import stat

from .ledger import ACTIVE_GEMINI_STATES, get_default_state_dir, sanitize_parent_id
from .native_capacity import CLAUDE_PARENT_FAMILIES, is_triple_pool


def _signature(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_regular(directory: int, name: str, limit: int) -> bytes:
    """Read at most limit+1 bytes and bind identity to the still-named input."""
    before = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("not_regular")
    if not before.st_mode & 0o444:
        raise PermissionError("unreadable")
    if before.st_size > limit:
        raise OverflowError("size_limit")
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    with os.fdopen(fd, "rb") as stream:
        if _signature(before) != _signature(os.fstat(stream.fileno())):
            raise RuntimeError("changed_input")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    named = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if len(data) > limit or _signature(before) != _signature(after) or _signature(after) != _signature(named):
        raise RuntimeError("changed_or_growing_input")
    return data



MAX_RECORD = 4_000_000
RECORDS = ("ledger.json", "native-launch.json")


def snapshot(base, records=RECORDS):
    """Read two matching bounded passes, otherwise explicitly incomplete."""
    if not base.exists():
        return {}, ["no_retained_context"]
    try:
        fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        return {}, ["context_unreadable"]
    try:
        passes = []
        for _ in range(2):
            values = {}
            for name in records:
                try:
                    values[name] = read_regular(fd, name, MAX_RECORD)
                except FileNotFoundError:
                    values[name] = None
            passes.append(values)
        if passes[0] != passes[1]:
            return {}, ["concurrent_snapshot_incomplete"]
        parsed = {name: json.loads(raw) for name, raw in passes[0].items() if raw is not None}
        if any(not isinstance(value, dict) for value in parsed.values()):
            return {}, ["optional_record_corrupt"]
        return parsed, []
    except (OSError, ValueError, RuntimeError, OverflowError):
        return {}, ["optional_record_unreadable_corrupt_or_changed"]
    finally:
        os.close(fd)


def observed_process(pid):
    if type(pid) is not int or pid <= 0:
        return "unknown"
    try:
        os.kill(pid, 0)
        return "pid_present_identity_not_verified"
    except ProcessLookupError:
        return "pid_absent_cleanup_not_proven"
    except OSError:
        return "unknown"


def text(value):
    return value[:512] if isinstance(value, str) else None


def job_view(job):
    cleanup = job.get("cleanup_status")
    known = cleanup == "proven"
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    return {"job_id": text(job.get("job_id")), "task_id": text(job.get("task_id")),
            "worker_kind": job.get("worker_kind", "gemini"),
            "semantic_disposition": job.get("task_outcome", "unknown"),
            "provider_outcome": job.get("provider_status", "unknown"),
            "persisted_status": job.get("status", "unknown"),
            "abandonment_decided": isinstance(job.get("abandonment"), dict),
            "cleanup_status": cleanup or "unknown",
            "occupied": job.get("status") in ACTIVE_GEMINI_STATES,
            "attempt_count": job.get("attempt", job.get("attempt_number", 1)),
            "partial_work": {"output_dir": text(job.get("output_dir")),
                             "result_path": text(result.get("result_path"))},
            "observed_process": observed_process(job.get("supervisor_pid")),
            "suggested_action": ("inspect retained partial work before explicit adoption or replacement" if known
                                 else "retain custody and occupied capacity; inspect/drain explicitly before overlapping work; disjoint/direct work can continue")}


def revision(root):
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=2)
        value = result.stdout.strip()
        return value if result.returncode == 0 and len(value) == 40 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _inspect_parent(parent_id=None, state_dir=None, *, root=None, job_id=None):
    root = root or Path(__file__).resolve().parents[2]
    view = {"schema": "agent-worker-inspection-v1", "read_only": True,
            "source_revision": revision(root), "parent_id": parent_id,
            "native_occupancy": None, "account_capacity": "not_observed",
            "limitations": [], "pools": {}, "jobs": []}
    if not parent_id:
        return {**view, "status": "no_context", "reason": "No worker context selected; direct parent work remains available."}
    base = Path(state_dir or get_default_state_dir()) / sanitize_parent_id(parent_id)
    records, limitations = snapshot(base)
    if not records and (not limitations or limitations == ["no_retained_context"]):
        return {**view, "status": "no_context",
                "reason": "No retained worker context for this parent; direct parent work remains available."}
    data = records.get("ledger.json", {})
    launch = records.get("native-launch.json", {})
    cap = data.get("worker_capability") or {}
    policy = data.get("policy") or {}
    if not isinstance(cap, dict) or not isinstance(policy, dict) or not isinstance(data.get("gemini_jobs", {}), dict):
        return {**view, "status": "incomplete", "limitations": ["optional_record_corrupt"]}
    if (not isinstance(data.get("pool_state", {}), dict)
            or not isinstance(cap.get("allowed_worker_kinds", []), list)
            or not isinstance(cap.get("excluded_worker_kinds", []), list)):
        return {**view, "status": "incomplete", "limitations": ["optional_record_corrupt"]}
    jobs = [job_view(job) for job in data.get("gemini_jobs", {}).values() if isinstance(job, dict)]
    pool_kinds = [("gemini", "agy"), ("luna", "codex")]
    if is_triple_pool(data):
        pool_kinds.append(("sonnet", "claude"))
    for kind, executable in pool_kinds:
        if kind == "gemini":
            external = True
        elif kind == "luna":
            external = data.get("parent_family") not in ("codex_astra", "codex_parent")
        elif kind == "sonnet":
            external = data.get("parent_family") not in CLAUDE_PARENT_FAMILIES
        else:
            external = True
        allowed = kind in cap.get("allowed_worker_kinds", ["gemini"])
        pool = (data.get("pool_state") or {}).get(kind) or {}
        available = shutil.which(executable) is not None
        view["pools"][kind] = {"external": external, "configured_limit": policy.get("max_" + kind),
            "enabled": allowed and data.get("worker_allowed") is True if external else None,
            "excluded": kind in cap.get("excluded_worker_kinds", []),
            "paused": pool.get("paused") if isinstance(pool, dict) else None,
            "occupied_persisted": sum(job["occupied"] for job in jobs if job["worker_kind"] == kind) if external else None,
            "executable_available": available if external else None,
            "unavailable_reason": None if available or not external else "provider executable absent; no login or inference attempted"}
    if not launch:
        limitations.append("launch_binding_not_recorded")
    native = cap.get("native_launch_binding") or launch.get("native_launch_binding") or {}
    view.update({"status": "observed" if data and not limitations else "incomplete",
                 "limitations": limitations, "parent_family": data.get("parent_family"),
                 "authority": data.get("task_authority"), "workspace": text(data.get("workspace")),
                 "persisted_status": data.get("status"), "policy_selection": cap.get("policy_selection", "legacy"),
                 "policy_sha256": text(cap.get("policy_sha256")),
                 "policy_source": text(cap.get("policy_source")),
                 "launch_bound_native_ceiling": native.get("cap") if isinstance(native, dict) else None,
                 "guidance": {"source": "common/skills/agent-worker/SKILL.md", "mechanism": "launcher advertisement and source file read", "launch_record_present": bool(launch)},
                 "jobs": [job for job in jobs if job_id is None or job["job_id"] == job_id]})
    if job_id and not view["jobs"]:
        view["limitations"].append("requested_job_absent")
    return view


def inspect_parent(parent_id=None, state_dir=None, *, root=None, job_id=None):
    try:
        return _inspect_parent(parent_id, state_dir, root=root, job_id=job_id)
    except (TypeError, ValueError, AttributeError, OSError):
        return {"schema": "agent-worker-inspection-v1", "read_only": True,
                "status": "incomplete", "parent_id": parent_id,
                "limitations": ["optional_record_corrupt_or_unavailable"],
                "native_occupancy": None, "pools": {}, "jobs": []}


def human(view):
    # JSON escaping bounds terminal control characters even in persisted identifiers.
    def safe(value):
        return json.dumps(value, ensure_ascii=True)
    lines = [f"Worker inspection: {view['status']} (read only)",
             f"Parent {safe(view.get('parent_id'))}; authority {safe(view.get('authority'))}",
             f"Policy {safe(view.get('policy_selection'))}; native ceiling {safe(view.get('launch_bound_native_ceiling'))}; native occupancy unknown"]
    for kind, pool in view["pools"].items():
        lines.append(f"{kind}: " + safe(pool))
    for job in view["jobs"]:
        lines.append("Task: " + safe(job))
    lines.append(view.get("reason") or "Suggestions never change custody or capacity. Direct/disjoint work remains available.")
    if view["limitations"]:
        lines.append("Limitations: " + safe(view["limitations"]))
    return "\n".join(lines)
