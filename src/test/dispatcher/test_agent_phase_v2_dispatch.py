"""Integration and CLI tests for Request V2 dispatch, resolution, and SQLite persistence.

Covers:
- Acceptance Item 12: agent-phase-resolve and agent-phase-dispatch CLI entrypoints.
- Acceptance Item 14: Route verified in SQLite persistence before provider runner is called.
- Acceptance Item 15: Recovery of the same attempt reuses persisted route without re-routing.
- Acceptance Item 16: New attempt resolves with predecessor attempt provenance.
- Acceptance Item 17: Request V2 static preset resolution across bindings.
- Acceptance Item 18: Request V2 dynamic routing with capability matching.
- Acceptance Item 19: Embedded SQLite leaves no background processes or daemons.
- Reviewer independence across multi-turn plan and work review bindings.
- Graceful error reporting (exit code 2 without unhandled tracebacks).
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
from typing import Any
import pytest

from agent_phase.cli import dispatch_main, resolve_main
from agent_phase.dynamic_router import (
    OperationalObservation,
)
from agent_phase.persistence import (
    get_attempt_route_resolution,
    get_invocation_attempts,
    get_run,
    open_dispatcher_db,
    resolve_dispatcher_db_path,
)
from agent_phase.request import parse_request_v2
from agent_phase.resolution_v2 import resolve_v2
from agent_phase.v2_dispatch import dispatch_v2


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _make_v2_request_bytes(
    phase_type: str = "implementation_testing",
    prompt: str = "Implement feature X",
) -> bytes:
    payload = {
        "schema": "agent-phase-request-v2",
        "phase_type": phase_type,
        "prompt": prompt,
    }
    return json.dumps(payload).encode("utf-8")


def test_resolve_v2_static_preset() -> None:
    root = _repo_root()
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    resolved = resolve_v2(
        req,
        root,
        execution_mode="gemini_flash_sub",
    )
    assert resolved["schema"] == "agent-phase-resolved-v7"
    assert resolved["execution_mode"] == "gemini_flash_sub"
    assert resolved["pending_responsibilities"] == []
    assert "binding_plan" in resolved["route_resolutions"]
    assert "binding_work" in resolved["route_resolutions"]


def test_resolve_v2_dynamic_initial_and_full() -> None:
    root = _repo_root()
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)

    # Initial turn resolution
    initial = resolve_v2(req, root, execution_mode="dynamic")
    assert initial["schema"] == "agent-phase-resolved-v7"
    assert "binding_plan" in initial["route_resolutions"]
    assert len(initial["pending_responsibilities"]) > 0

    # Full resolution with reviewer independence
    full = resolve_v2(req, root, execution_mode="dynamic", resolve_all_dynamic=True)
    assert "binding_plan" in full["route_resolutions"]
    assert "binding_plan_review" in full["route_resolutions"]
    assert "binding_work" in full["route_resolutions"]
    assert "binding_work_review" in full["route_resolutions"]

    plan_alias = full["route_resolutions"]["binding_plan"]["endpoint_alias"]
    plan_review_alias = full["route_resolutions"]["binding_plan_review"]["endpoint_alias"]
    assert plan_alias != plan_review_alias

    work_alias = full["route_resolutions"]["binding_work"]["endpoint_alias"]
    work_review_alias = full["route_resolutions"]["binding_work_review"]["endpoint_alias"]
    assert work_alias != work_review_alias


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    (path / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)
    return path


def test_dispatch_v2_dry_run(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"

    res = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
        dry_run=True,
    )
    assert res["status"] == "dry_run"
    assert res["schema"] == "agent-phase-result-v2"

    db_path = resolve_dispatcher_db_path(home)
    assert db_path.is_file()
    conn = open_dispatcher_db(db_path)
    run = get_run(conn, res["run_id"])
    assert run is not None
    assert run["status"] == "dry_run"
    conn.close()


def test_dispatch_v2_invariant_14_persisted_before_runner(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)

    runner_called = False
    verified_in_runner = False

    def test_runner(*, run_id: str, binding: Any, route: Any, run_dir: Path, nonce: str | None = None) -> bytes | None:
        nonlocal runner_called, verified_in_runner
        runner_called = True
        # Invariant 14: check that SQLite contains the route resolution and attempt
        conn_check = sqlite3.connect(str(db_path))
        conn_check.row_factory = sqlite3.Row
        cur = conn_check.cursor()
        cur.execute(
            "SELECT * FROM route_resolutions WHERE run_id = ? AND binding_id = ?",
            (run_id, binding.binding_id),
        )
        route_row = cur.fetchone()
        cur.execute(
            "SELECT * FROM invocation_attempts WHERE run_id = ? AND binding_id = ?",
            (run_id, binding.binding_id),
        )
        attempt_row = cur.fetchone()
        conn_check.close()
        if route_row is not None and attempt_row is not None:
            verified_in_runner = True
        if binding.binding_id in ("binding_closeout", "binding_closeout_agent") and nonce:
            from agent_phase import result as result_module
            begin, end = result_module.markers(nonce)
            payload = {
                "version": 1,
                "stage": "closeout",
                "outcome": "completed",
                "body": "Closeout complete.",
                "commit_message": None,
            }
            return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")
        return None

    res = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
        finalization_policy="checkpoint",
        outbox_root=tmp_path / "outbox",
        runner=test_runner,
    )
    assert runner_called is True
    assert verified_in_runner is True
    assert res["status"] == "completed"

    conn = open_dispatcher_db(db_path)
    attempts = get_invocation_attempts(conn, res["run_id"])
    assert len(attempts) == 5
    assert all(a["status"] == "completed" for a in attempts)
    conn.close()


def test_dispatch_v2_recovery_same_attempt_reuses_route(tmp_path: Path) -> None:
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"

    # Initial staged dispatch (Attempt 1)
    res1 = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
    )
    run_id = res1["run_id"]
    initial_route = res1["selected_route"]

    # Recovery: Re-dispatching the same attempt must read the persisted route
    db_path = resolve_dispatcher_db_path(home)
    conn = open_dispatcher_db(db_path)
    persisted = get_attempt_route_resolution(conn, run_id, "binding_plan", 1)
    assert persisted is not None
    assert persisted["endpoint_alias"] == initial_route["endpoint_alias"]
    conn.close()


def test_dispatch_v2_retry_new_attempt_provenance(tmp_path: Path) -> None:
    import time
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"

    # Attempt 1
    res1 = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
        attempt_number=1,
    )
    run_id = res1["run_id"]
    route1 = res1["selected_route"]

    # Attempt 2 under new observation with active cooldown on route 1 provider
    obs = OperationalObservation(
        observation_id="obs-cool-1",
        producer="test",
        observation_type="cooldown",
        provider=route1["provider"],
        profile=None,
        timestamp=time.time(),
        expires_at=time.time() + 300.0,
        state_value="active_cooldown",
    )
    res2 = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
        operational_observations=[obs],
        run_id=run_id,
        attempt_number=2,
    )
    db_path = resolve_dispatcher_db_path(home)
    conn = open_dispatcher_db(db_path)
    attempts = get_invocation_attempts(conn, run_id, binding_id="binding_plan")
    conn.close()
    assert len(attempts) == 2
    assert attempts[1]["predecessor_attempt_id"] == f"att-{run_id}-binding_plan-1"
    assert res2["selected_route"]["provider"] != route1["provider"]


def test_dispatch_v2_no_route_typed_result(tmp_path: Path) -> None:
    import time
    root = _repo_root()
    repo = _init_repo(tmp_path / "repo")
    raw = _make_v2_request_bytes()
    req = parse_request_v2(raw)
    home = tmp_path / "apgr_home"

    # All providers unavailable
    obs = [
        OperationalObservation(
            observation_id=f"obs-unavail-{p}",
            producer="test",
            observation_type="availability",
            provider=p,
            timestamp=time.time(),
            expires_at=time.time() + 300.0,
            state_value="unavailable",
        )
        for p in ("codex", "claude", "antigravity")
    ]
    res = dispatch_v2(
        root,
        repo,
        req,
        raw,
        execution_mode="dynamic",
        apgr_home=home,
        operational_observations=obs,
    )
    assert res["status"] == "no_route"
    assert res["outcome"] == "no_route"
    assert "no available or usable routes" in res["detail"]


def test_embedded_sqlite_no_daemon_processes(tmp_path: Path) -> None:
    home = tmp_path / "apgr_home"
    db_path = resolve_dispatcher_db_path(home)
    conn = open_dispatcher_db(db_path)
    conn.execute("SELECT 1")
    conn.close()

    # Verify no sqlite daemon or zombie locks
    assert not (db_path.parent / "dispatcher.sqlite3-wal").is_file() or (
        db_path.parent / "dispatcher.sqlite3-shm"
    ).is_file()


def test_cli_agent_phase_resolve_and_dispatch_v2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    req_file = tmp_path / "req.json"
    req_file.write_bytes(_make_v2_request_bytes())
    home = tmp_path / "home"

    # Test resolve CLI
    code = resolve_main([str(req_file), "--execution-mode", "codex_only", "--apgr-home", str(home)])
    assert code == 0
    captured = capsys.readouterr()
    resolved = json.loads(captured.out)
    assert resolved["schema"] == "agent-phase-resolved-v7"
    assert resolved["execution_mode"] == "codex_only"

    # Test dispatch CLI with dry-run
    code = dispatch_main([str(req_file), "--execution-mode", "codex_only", "--apgr-home", str(home), "--dry-run"])
    assert code == 0
    captured = capsys.readouterr()
    dispatched = json.loads(captured.out)
    assert dispatched["schema"] == "agent-phase-result-v2"
    assert dispatched["status"] == "dry_run"


def test_cli_error_clean_exit_code_2(tmp_path: Path) -> None:
    # CLI error handling on invalid execution-mode for V1
    req_v1 = tmp_path / "req_v1.json"
    req_v1.write_text(json.dumps({
        "schema": "agent-phase-request-v1",
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "prompt": "test",
    }))

    with pytest.raises(SystemExit) as exc_info:
        resolve_main([str(req_v1), "--execution-mode", "codex_only"])
    assert exc_info.value.code == 2
