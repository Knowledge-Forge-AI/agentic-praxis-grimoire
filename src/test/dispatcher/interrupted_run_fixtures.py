"""Synthetic runs whose dispatcher process vanished during one stage.

A real kill cannot write anything after the provider call starts, so the fault
seam snapshots the run directory at the exact point the provider is running
and restores it after the in-process dispatcher unwinds. The restored bytes are
what a SIGKILL at that instant leaves: every atomic pre-stage write, no stage
metadata, no aggregate result and no archive. The worktree keeps whatever the
dying stage wrote.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable

import pytest

from controller_generation_process import process_identity
from agent_phase.dispatch import DispatchError
from agent_phase.run import stage_parent_id
from test_agent_phase_disposition_flow import (
    PHASE_ID,
    REQUEST,
    DispositionFakeRunner,
    make_dispatcher,
)


class _ProcessLost(RuntimeError):
    """Raised only after the kill-point snapshot has been taken."""


def only_run(run_root: Path) -> Path:
    runs = [path.parent for path in run_root.rglob("state.json") if path.parent.name != "inherited"]
    assert len(runs) == 1, runs
    return runs[0]


def interrupted_source(
    repository: Path,
    tmp_path: Path,
    mutate: Callable[[Path], None],
    *,
    at: int = 2,
    name: str = "source",
    before: dict[int, Callable[[Path, bytes], None]] | None = None,
    entry_adoption: Path | None = None,
) -> Path:
    """Dispatch until provider call ``at``, let it mutate, then lose the process."""
    run_root = tmp_path / name
    snapshot = tmp_path / f"{name}-kill-point"

    def lose_process(cwd: Path, _prompt: bytes) -> None:
        mutate(cwd)
        shutil.copytree(only_run(run_root / "runs"), snapshot, symlinks=True)
        raise _ProcessLost("dispatcher process lost")

    runner = DispositionFakeRunner(hooks={**(before or {}), at: lose_process})
    with pytest.raises((DispatchError, _ProcessLost)):
        make_dispatcher(repository, run_root, runner).dispatch(
            PHASE_ID, REQUEST, finalization_policy="checkpoint", entry_adoption=entry_adoption
        )
    source = only_run(run_root / "runs")
    for sibling in source.parent.iterdir():
        if sibling != source:
            sibling.unlink()
    shutil.rmtree(source)
    shutil.copytree(snapshot, source, symlinks=True)
    shutil.rmtree(snapshot)
    assert not (source / "result.json").exists()
    record_dead_controller(source)
    return source


def dead_controller_generation() -> dict:
    """A development controller record whose process has exited and been reaped.

    The in-process fake dispatcher records no controller generation, while a
    real CLI dispatcher always does; a killed one leaves its dead identity.
    """
    child = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"],
                             stdin=subprocess.PIPE)
    identity = process_identity(child.pid)
    child.communicate(b"")
    assert identity is not None
    return {"schema": "controller-generation-v1", "commit": None, "tree": None,
            "controller_root": None, "generation_root": None, "safety_established": False,
            "reason": "source_development_worktree", "pid": child.pid,
            "process_identity": identity, "created_at": 0.0}


def record_dead_controller(source: Path, generation: dict | None = None) -> None:
    state = read_state(source)
    state["controller_generation"] = generation or dead_controller_generation()
    write_state(source, state)


def read_state(source: Path) -> dict:
    return json.loads((source / "state.json").read_text(encoding="utf-8"))


def write_state(source: Path, state: dict) -> None:
    (source / "state.json").write_text(
        json.dumps(state, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def add_worker_custody(source: Path, jobs: dict, *, status: str = "active", natives=None) -> Path:
    """Retain the crash shape: an armed drain receipt and an unclosed parent."""
    from apgr_workers.ledger import SCHEMA_NAME, sanitize_parent_id

    state = read_state(source)
    parent = stage_parent_id(state["run_id"], "work", 3)
    (source / "03-work.worker-drain.json").write_text(json.dumps(
        {"parent_id": parent, "status": "armed", "uncertain_cleanup": True}, indent=2, sort_keys=True
    ) + "\n")
    ledger_path = source / "workers" / sanitize_parent_id(parent) / "ledger.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(json.dumps({
        "schema": SCHEMA_NAME, "parent_id": parent, "status": status,
        "gemini_jobs": jobs, "native_agents": natives or {},
    }, indent=2, sort_keys=True) + "\n")
    state["worker_cleanup_pending"] = {"artifact": "03-work.worker-drain.json", "status": "incomplete"}
    write_state(source, state)
    return ledger_path


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


__all__ = [
    "PHASE_ID", "REQUEST", "DispositionFakeRunner", "add_worker_custody",
    "dead_controller_generation", "interrupted_source", "make_dispatcher", "only_run",
    "read_state", "record_dead_controller", "tree_bytes", "write_state",
]
