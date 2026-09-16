"""Focused regression coverage for the injected_observations bootstrap NameError.

Proves the 7 mandatory bootstrap contract points:
1. Request V2 dispatch works when no injected observations are supplied.
2. Request V2 dispatch works when injected observations ARE supplied.
3. Retry snapshot refresh retains the original injected observations.
4. No function references an unbound `injected_observations` local.
5. Dispatch -> V2 turns / retry helper call signatures agree.
6. The regression fails against the broken preserved snapshot shape and passes against corrected.
7. A premature V2 failure creates canonical failure evidence and operator-facing outbox projection.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
import sqlite3
import subprocess
import time
from typing import Any

import pytest

from agent_phase.dynamic_router import OperationalObservation
from agent_phase.persistence import (
    get_operational_observations,
    open_dispatcher_db,
)
from agent_phase.probes import collect_operational_observations
from agent_phase.request import parse_request_v2
from agent_phase.v2_dispatch import dispatch_v2
from agent_phase.v2_turns import execute_v2_turns


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _init_worktree(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    (path / "file.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "file.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "init"], check=True)
    return path


def test_1_dispatch_v2_works_without_injected_observations(tmp_path: Path) -> None:
    """1. Request V2 dispatch works when no injected observations are supplied."""
    root = _repo_root()
    work = _init_worktree(tmp_path / "work")
    apgr_home = tmp_path / "home"
    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test dispatch without injected observations",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    res = dispatch_v2(
        root,
        work,
        req,
        raw_req,
        execution_mode="dynamic",
        apgr_home=apgr_home,
        dry_run=True,
    )
    assert res["status"] in ("dry_run", "completed", "clean")
    assert res["schema"] == "agent-phase-result-v2"


def test_2_dispatch_v2_works_with_injected_observations(tmp_path: Path) -> None:
    """2. Request V2 dispatch works when injected observations ARE supplied."""
    root = _repo_root()
    work = _init_worktree(tmp_path / "work")
    apgr_home = tmp_path / "home"
    now = time.time()
    obs = OperationalObservation(
        observation_id="obs-injected-test-001",
        producer="operator_injected",
        observation_type="quota",
        provider="codex",
        profile=None,
        timestamp=now,
        expires_at=now + 3600.0,
        state_value="exhausted",
    )
    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test dispatch with injected observations",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    res = dispatch_v2(
        root,
        work,
        req,
        raw_req,
        execution_mode="dynamic",
        apgr_home=apgr_home,
        injected_observations=[obs],
        dry_run=True,
    )
    assert res["status"] in ("dry_run", "completed", "clean")

    # Verify persisted in SQLite
    db_path = apgr_home / "state" / "dispatcher.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    persisted = get_operational_observations(conn)
    obs_ids = [r["observation_id"] for r in persisted]
    assert "obs-injected-test-001" in obs_ids
    conn.close()


def test_3_retry_snapshot_refresh_retains_injected_observations(tmp_path: Path) -> None:
    """3. Retry snapshot refresh retains the original injected observations."""
    apgr_home = tmp_path / "home"
    db_path = apgr_home / "state" / "dispatcher.sqlite3"
    conn = open_dispatcher_db(db_path)

    now = time.time()
    original_injected = [
        OperationalObservation(
            observation_id="obs-operator-retained-001",
            producer="operator",
            observation_type="probe",
            provider="codex",
            profile=None,
            timestamp=now,
            expires_at=now + 7200.0,
            state_value="active",
        )
    ]

    # First collection
    initial_snapshot = collect_operational_observations(
        conn=conn,
        now=now,
        injected=original_injected,
    )
    assert any(o.observation_id == "obs-operator-retained-001" for o in initial_snapshot)

    # Simulate dynamic retry snapshot refresh
    refreshed_snapshot = collect_operational_observations(
        conn=conn,
        now=now + 10.0,
        injected=original_injected,
    )
    assert any(o.observation_id == "obs-operator-retained-001" for o in refreshed_snapshot)

    # End-to-end execute_v2_turns test: verify injected observations survive retry boundary
    from agent_phase.capabilities import EndpointCapabilities
    from agent_phase.persistence import (
        get_attempt_route_resolution,
        record_actor_bindings,
        record_run,
        record_semantic_responsibility,
    )
    from agent_phase.semantic_roles import create_default_binding_policy

    root = _repo_root()
    work = _init_worktree(tmp_path / "work_retry")
    run_dir = apgr_home / "state" / "runs" / "test-run-retry-retention"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id = "run-test-retry-retention"

    record_run(
        conn,
        run_id=run_id,
        project="apgr",
        phase_id="APG150B",
        schema_version=2,
        request_schema="agent-phase-request-v2",
        request_digest="dig-retry-test",
        workflow_version="2.0",
        lifecycle="active",
        execution_mode="dynamic",
        run_directory=str(run_dir),
    )

    full_policy = create_default_binding_policy()
    single_policy = type(full_policy)(name=full_policy.name, bindings=(full_policy.bindings[0],))
    bindings_data = [
        {
            "binding_id": b.binding_id,
            "policy_name": single_policy.name,
            "roles": list(b.roles),
            "required_capabilities": list(b.required_capabilities),
            "process_read_only": b.process_read_only,
            "is_mutating": b.is_mutating,
        }
        for b in single_policy.bindings
    ]
    record_actor_bindings(conn, run_id, bindings_data)
    for b in single_policy.bindings:
        for r in b.roles:
            record_semantic_responsibility(
                conn,
                id=f"sem-{run_id}-{r}",
                run_id=run_id,
                responsibility_name=r,
                binding_id=b.binding_id,
                status="pending",
            )

    caps = {
        "codex-primary": EndpointCapabilities(
            endpoint_alias="codex-primary",
            provider="codex",
            profile="primary",
            capabilities=frozenset(["code_generation", "read_only", "mutation", "read", "execution", "reasoning"]),
            posture="full",
        ),
        "agy-primary": EndpointCapabilities(
            endpoint_alias="agy-primary",
            provider="antigravity",
            profile="primary",
            capabilities=frozenset(["code_generation", "read_only", "mutation", "read", "execution", "reasoning"]),
            posture="full",
        ),
    }

    class MockRes:
        def __init__(self, exit_code: int, stdout: bytes, stderr: bytes):
            self.exit_code = exit_code
            self.stdout = stdout
            self.stderr = stderr

    attempt_count = [0]

    def mock_runner(*args: Any, **kwargs: Any) -> Any:
        attempt_count[0] += 1
        if attempt_count[0] == 1:
            return MockRes(1, b"", b"ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at Sep 19th, 2026 8:20 AM.")
        return MockRes(0, b"Plan material produced.\n", b"")

    req = parse_request_v2(json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test retry snapshot retention",
    }).encode("utf-8"))

    # Supply operator observation directly via injected_observations (testing invariant across reroute)
    execute_v2_turns(
        conn,
        run_id,
        run_dir,
        root,
        work,
        req,
        execution_mode="dynamic",
        binding_policy=single_policy,
        caps_catalog=caps,
        operational_observations=(),
        runner=mock_runner,
        display=None,
        dry_run=False,
        lifecycle_spec=type("Spec", (), {"name": "default_v012"})(),
        finalization_policy="checkpoint",
        injected_observations=original_injected,
    )

    res2 = get_attempt_route_resolution(conn, run_id, "binding_plan", 2)
    assert res2 is not None
    obs_ids = json.loads(res2["observation_ids_json"])
    assert "obs-operator-retained-001" in obs_ids
    conn.close()


def test_4_no_function_references_unbound_injected_observations() -> None:
    """4. No function references an unbound `injected_observations` local.

    Uses lexical scope analysis (excluding nested function/class bodies) to verify
    that any load of injected_observations is resolved by its own parameters or local stores.
    """
    libexec_dir = Path(__file__).resolve().parents[3] / "libexec" / "agent_phase"
    py_files = list(libexec_dir.glob("*.py"))
    assert py_files, "Found no python files in libexec/agent_phase"

    for py_path in py_files:
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Collect parameter names
                param_names = {arg.arg for arg in node.args.args}
                param_names.update(arg.arg for arg in getattr(node.args, "kwonlyargs", []))
                param_names.update(arg.arg for arg in getattr(node.args, "posonlyargs", []))
                if node.args.vararg:
                    param_names.add(node.args.vararg.arg)
                if node.args.kwarg:
                    param_names.add(node.args.kwarg.arg)

                # Collect assigned local names in this exact function scope (do not enter nested defs)
                assigned_names: set[str] = set()
                loaded_names: list[ast.Name] = []

                def _walk_local_scope(cur: ast.AST) -> None:
                    for child in ast.iter_child_nodes(cur):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                            continue
                        if isinstance(child, ast.Name):
                            if isinstance(child.ctx, ast.Store):
                                assigned_names.add(child.id)
                            elif isinstance(child.ctx, ast.Load) and child.id == "injected_observations":
                                loaded_names.append(child)
                        _walk_local_scope(child)

                _walk_local_scope(node)

                if loaded_names:
                    is_defined = (
                        "injected_observations" in param_names
                        or "injected_observations" in assigned_names
                    )
                    assert is_defined, (
                        f"In {py_path.name}:{node.name} at line {loaded_names[0].lineno}: "
                        f"reference to 'injected_observations' is not in parameters or assigned locals!"
                    )


def test_5_dispatch_and_turns_call_signatures_agree() -> None:
    """5. Dispatch -> V2 turns / retry helper call signatures agree."""
    dispatch_sig = inspect.signature(dispatch_v2)
    turns_sig = inspect.signature(execute_v2_turns)
    probes_sig = inspect.signature(collect_operational_observations)

    assert "injected_observations" in dispatch_sig.parameters
    assert "injected_observations" in turns_sig.parameters
    assert "injected" in probes_sig.parameters

    assert dispatch_sig.parameters["injected_observations"].default is None
    assert turns_sig.parameters["injected_observations"].default == ()


HISTORICAL_BROKEN_DISPATCH_V2_SNIPPET = """
def dispatch_v2(
    *,
    conn,
    project,
    phase_id,
    request,
    execution_mode,
    policy,
    caps_catalog,
    runner,
    display=None,
    dry_run=False,
    spec=None,
    valid_finalization_policy="checkpoint",
    attempt_number=1,
    now=None,
    operational_observations=(),
):
    # Historical broken snapshot shape: injected_observations is loaded but unbound
    return execute_v2_turns(
        conn,
        "run_id",
        None,
        None,
        None,
        request,
        execution_mode,
        policy,
        caps_catalog,
        (),
        runner,
        display,
        dry_run,
        spec,
        valid_finalization_policy,
        attempt_number=attempt_number,
        injected_observations=injected_observations,
        now=now,
    )
"""


def test_6_broken_snapshot_shape_demonstrates_name_error_and_fix_succeeds() -> None:
    """6. The regression fails against the broken preserved snapshot shape and passes against corrected."""
    # 1. Hermetic AST and runtime analysis of the historical broken snapshot fixture
    broken_tree = ast.parse(HISTORICAL_BROKEN_DISPATCH_V2_SNIPPET)
    broken_dispatch = next(
        n for n in ast.walk(broken_tree)
        if isinstance(n, ast.FunctionDef) and n.name == "dispatch_v2"
    )
    broken_params = {arg.arg for arg in broken_dispatch.args.args}
    broken_params.update(arg.arg for arg in getattr(broken_dispatch.args, "kwonlyargs", []))
    broken_stores = {
        n.id for n in ast.walk(broken_dispatch)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
    }
    broken_loads = {
        n.id for n in ast.walk(broken_dispatch)
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    }

    # In the broken snapshot: injected_observations is loaded (passed to execute_v2_turns)
    # but is NEITHER a parameter NOR an assigned local variable, producing NameError at runtime!
    assert "injected_observations" in broken_loads, "Broken snapshot should load injected_observations"
    assert "injected_observations" not in broken_params, "Broken snapshot omitted injected_observations parameter"
    assert "injected_observations" not in broken_stores, "Broken snapshot did not assign injected_observations"

    # Runtime demonstration: executing a callable with the broken AST structure raises NameError
    compiled = compile(broken_tree, filename="<broken_dispatch_v2>", mode="exec")
    ns: dict[str, Any] = {
        "execute_v2_turns": lambda **kwargs: kwargs,
        "conn": None,
    }
    exec(compiled, ns)
    with pytest.raises(NameError, match="name 'injected_observations' is not defined"):
        ns["dispatch_v2"](
            conn=None, project="p", phase_id="APG150B", request=None,
            execution_mode="dynamic", policy=None, caps_catalog={}, runner=None,
        )

    # 2. Analyze the current corrected shipped implementation
    current_source = (_repo_root() / "libexec" / "agent_phase" / "v2_dispatch.py").read_text(encoding="utf-8")
    current_tree = ast.parse(current_source)
    current_dispatch = next(
        n for n in ast.walk(current_tree)
        if isinstance(n, ast.FunctionDef) and n.name == "dispatch_v2"
    )
    current_params = {arg.arg for arg in current_dispatch.args.args}
    current_params.update(arg.arg for arg in getattr(current_dispatch.args, "kwonlyargs", []))

    # In corrected implementation: injected_observations IS properly declared as a parameter
    assert "injected_observations" in current_params, "Corrected implementation must declare injected_observations parameter"


def test_7_premature_v2_failure_preserves_canonical_evidence_and_outbox(tmp_path: Path) -> None:
    """7. A premature V2 failure still creates the expected canonical failure evidence and outbox projection."""
    root = _repo_root()
    work = _init_worktree(tmp_path / "work")
    apgr_home = tmp_path / "home"
    outbox_root = tmp_path / "outbox"

    def failing_runner(*args: Any, **kwargs: Any) -> Any:
        class DummyProc:
            exit_code = 1
            returncode = 1
            stdout = b""
            stderr = b"fatal startup error: missing binary"
        return DummyProc()

    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test premature failure outbox",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    with pytest.raises(Exception):
        dispatch_v2(
            root,
            work,
            req,
            raw_req,
            execution_mode="gemini_opus",  # static mode -> no reroute
            apgr_home=apgr_home,
            outbox_root=outbox_root,
            runner=failing_runner,
            dry_run=False,
        )

    # Verify canonical evidence in state directory
    runs_dir = apgr_home / "state" / "runs"
    assert runs_dir.is_dir()
    run_subdirs = [p for p in runs_dir.iterdir() if p.is_dir()]
    assert len(run_subdirs) == 1
    run_dir = run_subdirs[0]
    assert (run_dir / "result.json").is_file()
    archive_files = [p for p in runs_dir.iterdir() if p.suffix == ".zip"]
    assert len(archive_files) == 1

    # Verify canonical run record in DB
    db_path = apgr_home / "state" / "dispatcher.sqlite3"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM runs;")
    rows = cur.fetchall()
    assert len(rows) == 1
    run_row = rows[0]
    assert run_row["status"] == "failed"
    conn.close()

    # Verify outbox projection exists and reports failed
    assert outbox_root.is_dir()
    loc_files = list(outbox_root.glob("**/*.locator.json"))
    assert len(loc_files) >= 1
    loc_data = json.loads(loc_files[0].read_text(encoding="utf-8"))
    assert loc_data["semantic_status"] == "failed"

    dispatch_symlink = loc_files[0].parent / loc_files[0].name.replace(".locator.json", "")
    assert dispatch_symlink.is_symlink()
    result_path = dispatch_symlink / "result.json"
    assert result_path.is_file()
    result_data = json.loads(result_path.read_text(encoding="utf-8"))
    assert result_data["status"] == "failed"
