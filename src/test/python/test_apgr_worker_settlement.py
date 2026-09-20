"""Settled-parent reconciliation never touches a child and refuses uncertainty."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from apgr_workers import ledger, settlement


PARENT = "dispatch-fixture--work--3"


def write_ledger(state_dir: Path, *, status: str = "active", jobs=None, natives=None) -> Path:
    path = state_dir / ledger.sanitize_parent_id(PARENT) / "ledger.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "schema": ledger.SCHEMA_NAME,
        "parent_id": PARENT,
        "status": status,
        "gemini_jobs": jobs if jobs is not None else {
            "job-1": {"job_id": "job-1", "status": "completed", "cleanup_proven": True,
                      "supervisor_pid": 999_999, "supervisor_pgid": 999_999},
            "job-2": {"job_id": "job-2", "status": "cancelled", "cleanup_proven": True},
        },
        "native_agents": natives if natives is not None else {},
    }, indent=2, sort_keys=True) + "\n")
    return path


@pytest.fixture
def no_signals(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("settlement must never signal a process")

    monkeypatch.setattr(os, "kill", forbidden)
    monkeypatch.setattr(os, "killpg", forbidden)


def test_settled_active_parent_closes_once_and_is_idempotent(tmp_path, no_signals):
    path = write_ledger(tmp_path)
    parent = ledger.ParentLedger(PARENT, tmp_path)

    first = settlement.close_settled(parent, "interrupted dispatcher")
    closed_bytes = path.read_bytes()
    second = settlement.close_settled(parent, "interrupted dispatcher")

    data = json.loads(closed_bytes)
    assert first["reconciled"] is True and second["reconciled"] is False
    assert data["status"] == "closed"
    assert data["settled_reconciliation"] == {
        "schema": settlement.RECORD_SCHEMA,
        "prior_status": "active",
        "reason": "interrupted dispatcher",
        "gemini_jobs": {"job-1": "completed", "job-2": "cancelled"},
        "native_agents": {},
        "signals_sent": 0,
    }
    assert second["settled_reconciliation"] == data["settled_reconciliation"]
    assert path.read_bytes() == closed_bytes
    assert data["gemini_jobs"]["job-1"]["status"] == "completed"


@pytest.mark.parametrize(
    ("jobs", "natives", "status"),
    [
        ({"job-1": {"status": "running", "cleanup_proven": False, "supervisor_pid": 999_999}}, {}, "active"),
        ({"job-1": {"status": "orphaned", "cleanup_proven": False}}, {}, "active"),
        ({"job-1": {"status": "completed", "cleanup_proven": False,
                    "result": {"cleanup_proven": True}}}, {}, "active"),
        ({"job-1": {"status": "reserved"}}, {}, "draining"),
        ({}, {"agent-1": {"status": "active"}}, "active"),
        ({}, {}, "initializing"),
    ],
    ids=["running", "orphaned", "unproven-flag", "reserved", "native-active", "unknown-parent"],
)
def test_uncertain_parent_refuses_without_writing(tmp_path, no_signals, jobs, natives, status):
    path = write_ledger(tmp_path, status=status, jobs=jobs, natives=natives)
    before = path.read_bytes()

    with pytest.raises(ledger.RecoveryConflictError, match="not settled"):
        settlement.close_settled(ledger.ParentLedger(PARENT, tmp_path), "interrupted dispatcher")

    assert path.read_bytes() == before


def test_foreign_ledger_identity_refuses(tmp_path, no_signals):
    path = write_ledger(tmp_path)
    data = json.loads(path.read_text())
    data["parent_id"] = "someone-else"
    path.write_text(json.dumps(data))

    with pytest.raises(ledger.LedgerError, match="identity"):
        settlement.close_settled(ledger.ParentLedger(PARENT, tmp_path), "interrupted dispatcher")
