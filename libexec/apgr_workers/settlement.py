"""Close a stale parent whose retained children are already settled.

A dispatcher that loses its process before ``drain_and_close`` leaves an
``active`` parent even when every child already reached a terminal state with
proven cleanup.  Reconciliation here is bookkeeping only: it never signals,
cancels, reaps or rewrites a child, and it refuses every uncertain ledger.
"""

from __future__ import annotations

import fcntl
import os
from typing import Any, Mapping

from .ledger import (
    TERMINAL_GEMINI_STATES,
    TERMINAL_NATIVE_STATES,
    LedgerError,
    ParentLedger,
    RecoveryConflictError,
)

RECORD_SCHEMA = "agent-worker-settled-reconciliation-v1"
RECONCILABLE_PARENT_STATES = frozenset({"active", "draining"})


def settlement_problems(data: Mapping[str, Any]) -> list[str]:
    """Return why a parent cannot be closed without touching a child."""
    problems: list[str] = []
    status = data.get("status")
    if status != "closed" and status not in RECONCILABLE_PARENT_STATES:
        problems.append(f"parent status {status!r} is not reconcilable")
    jobs = data.get("gemini_jobs")
    natives = data.get("native_agents")
    if not isinstance(jobs, dict) or not isinstance(natives, dict):
        return [*problems, "worker ledger is incomplete"]
    for job_id, job in sorted(jobs.items()):
        if (
            not isinstance(job, dict)
            or job.get("status") not in TERMINAL_GEMINI_STATES
            or job.get("cleanup_proven") is not True
        ):
            problems.append(f"job {job_id} is not terminal with proven cleanup")
    for agent_id, agent in sorted(natives.items()):
        if not isinstance(agent, dict) or agent.get("status") not in TERMINAL_NATIVE_STATES:
            problems.append(f"native agent {agent_id} is not closed")
    return problems


def close_settled(ledger: ParentLedger, reason: str) -> dict[str, Any]:
    """Idempotently close a settled parent; refuse without writing otherwise."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("settled reconciliation requires a reason")
    lock_fd = os.open(os.fspath(ledger.lock_path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        # Deliberately bypass ``_locked``: its stale-process reaping may change
        # an active child, and an unchanged closed ledger must stay byte-exact.
        data = ledger._read_data()
        if not data or data.get("parent_id") != ledger.parent_id:
            raise LedgerError("worker ledger parent identity mismatch")
        if data.get("status") == "closed":
            return {
                "parent_id": ledger.parent_id,
                "status": "closed",
                "reconciled": False,
                "settled_reconciliation": data.get("settled_reconciliation"),
            }
        problems = settlement_problems(data)
        if problems:
            raise RecoveryConflictError(
                "worker parent is not settled: " + "; ".join(problems)
            )
        record = {
            "schema": RECORD_SCHEMA,
            "prior_status": data["status"],
            "reason": reason,
            "gemini_jobs": {
                str(job_id): job["status"]
                for job_id, job in sorted(data["gemini_jobs"].items())
            },
            "native_agents": {
                str(agent_id): agent["status"]
                for agent_id, agent in sorted(data["native_agents"].items())
            },
            "signals_sent": 0,
        }
        data["status"] = "closed"
        data["settled_reconciliation"] = record
        ledger._write_data(data)
        return {
            "parent_id": ledger.parent_id,
            "status": "closed",
            "reconciled": True,
            "settled_reconciliation": record,
        }
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(lock_fd)
