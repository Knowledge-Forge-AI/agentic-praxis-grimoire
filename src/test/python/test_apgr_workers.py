"""Comprehensive unit and integration tests for apgr_workers runtime.

Validates standalone APGR-owned worker modules, candidate-absolute entrypoints,
APGR_* environment variable handling with legacy fallbacks, 4+4 dual pool capacity
governance (no borrowing), provider-free supervisor scrubbing, inspection, MCP facade,
and policy loading across both TOML and JSON formats.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure libexec is on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIBEXEC = _REPO_ROOT / "libexec"
if str(_LIBEXEC) not in sys.path:
    sys.path.insert(0, str(_LIBEXEC))

import apgr_workers
import apgr_workers.adapter as adapter
import apgr_workers.claude_parent as claude_parent
import apgr_workers.cli as cli
import apgr_workers.codex_external as codex_external
import apgr_workers.facade_context as facade_context
import apgr_workers.gemini_parent as gemini_parent
import apgr_workers.inspection as inspection
import apgr_workers.ledger as ledger
import apgr_workers.mcp as mcp
import apgr_workers.native_launch as native_launch
import apgr_workers.parent_custody as parent_custody
import apgr_workers.policy as policy
import apgr_workers.supervisor as supervisor


@pytest.fixture(autouse=True)
def clean_leaf_environment(monkeypatch):
    """Isolate fixture parents and policy from the invoking dispatch context."""
    for name in (
        "APGR_WORKER_LEAF", "APGR_WORKER_FACADE", "APGR_PARENT_ID",
        "APGR_WORKER_STATE_DIR", "APGR_DISPATCH_WORKERS",
        "APGR_DISPATCH_WORKERS_SHA256", "APGR_DISPATCH_MODELS",
        "APGR_DISPATCH_MODELS_SHA256",
    ):
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# 1. Module imports and standalone independence
# ---------------------------------------------------------------------------


def test_apgr_workers_standalone_modules():
    """Verify that all 14 apgr_workers modules import cleanly with no Agent-Central dependency."""
    modules = [
        apgr_workers,
        adapter,
        claude_parent,
        cli,
        codex_external,
        facade_context,
        gemini_parent,
        inspection,
        ledger,
        mcp,
        native_launch,
        parent_custody,
        policy,
        supervisor,
    ]
    for mod in modules:
        assert mod is not None
        assert mod.__name__.startswith("apgr_workers")

    # Verify inspection does NOT depend on compact_export
    assert "compact_export" not in sys.modules
    assert hasattr(inspection, "read_regular")
    assert callable(inspection.read_regular)


# ---------------------------------------------------------------------------
# 2. Entrypoint integrity and candidate-absoluteness
# ---------------------------------------------------------------------------


def test_entrypoints_executable():
    """Verify that bin/agent-worker and bin/agent-worker-mcp exist and are executable."""
    ep_worker = _REPO_ROOT / "bin" / "agent-worker"
    ep_mcp = _REPO_ROOT / "bin" / "agent-worker-mcp"

    assert ep_worker.is_file()
    assert ep_mcp.is_file()
    assert os.access(ep_worker, os.X_OK)
    assert os.access(ep_mcp, os.X_OK)


def test_agent_worker_cli_help():
    """Verify bin/agent-worker runs --help and prints usage."""
    ep_worker = _REPO_ROOT / "bin" / "agent-worker"
    res = subprocess.run(
        [sys.executable, str(ep_worker), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert res.returncode == 0
    assert "usage: agent-worker" in res.stdout
    assert "{parent,job,native}" in res.stdout


def test_agent_worker_mcp_unconfigured_exit():
    """Verify bin/agent-worker-mcp exits 2 with FacadeContextError when launched outside Claude."""
    ep_mcp = _REPO_ROOT / "bin" / "agent-worker-mcp"
    res = subprocess.run(
        [sys.executable, str(ep_mcp)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert res.returncode == 2
    assert "agent-worker-mcp: unavailable (FacadeContextError)" in res.stderr


def test_candidate_absolute_symlink_execution(tmp_path):
    """Verify candidate-absolute path resolution: a symlink outside the repo runs correctly."""
    external_bin = tmp_path / "agent-worker-link"
    ep_worker = _REPO_ROOT / "bin" / "agent-worker"
    os.symlink(ep_worker, external_bin)

    res = subprocess.run(
        [sys.executable, str(external_bin), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert res.returncode == 0
    assert "usage: agent-worker" in res.stdout


# ---------------------------------------------------------------------------
# 3. Policy loading (both TOML and JSON) and capability resolution
# ---------------------------------------------------------------------------


def test_policy_loading_toml(tmp_path):
    """Verify load_worker_policy parses TOML format policy files."""
    policy_toml = tmp_path / "workers.toml"
    content = """schema = "agent-worker-policy-v1"

[limits]
max_gemini_workers_per_parent = 4
max_aggregate_workers_per_astra_parent = 8

[gemini_worker]
provider = "antigravity"
profile = "gemini-3.8-flash-high"

[selections.dual_pool_4x4]
max_gemini = 4
max_luna = 4
borrowing = false

[selections.dual_pool_4x4.luna_worker]
provider = "codex"
profile = "luna-worker"
"""
    policy_toml.write_text(content, encoding="utf-8")

    data, source, digest = policy.load_worker_policy(tmp_path, policy_toml)
    assert data["schema"] == "agent-worker-policy-v1"
    assert data["limits"]["max_gemini_workers_per_parent"] == 4
    assert data["limits"]["max_aggregate_workers_per_astra_parent"] == 8
    assert data["gemini_worker"]["profile"] == "gemini-3.8-flash-high"
    assert data["selections"]["dual_pool_4x4"]["max_gemini"] == 4
    assert data["selections"]["dual_pool_4x4"]["max_luna"] == 4
    assert data["selections"]["dual_pool_4x4"]["borrowing"] is False
    assert len(digest) == 64


def test_policy_loading_json(tmp_path):
    """Verify load_worker_policy parses JSON format policy files."""
    policy_json = tmp_path / "policy.json"
    doc = {
        "schema": "agent-worker-policy-v1",
        "limits": {
            "max_gemini_workers_per_parent": 4,
            "max_aggregate_workers_per_astra_parent": 8,
        },
        "gemini_worker": {
            "provider": "antigravity",
            "profile": "gemini-3.8-flash-high",
        },
        "selections": {
            "dual_pool_4x4": {
                "max_gemini": 4,
                "max_luna": 4,
                "borrowing": False,
                "luna_worker": {
                    "provider": "codex",
                    "profile": "luna-worker",
                },
            }
        },
    }
    policy_json.write_text(json.dumps(doc), encoding="utf-8")

    data, source, digest = policy.load_worker_policy(tmp_path, policy_json)
    assert data["schema"] == "agent-worker-policy-v1"
    assert data["limits"]["max_gemini_workers_per_parent"] == 4
    assert data["limits"]["max_aggregate_workers_per_astra_parent"] == 8
    assert data["gemini_worker"]["provider"] == "antigravity"


def test_selected_capability_triple_pool_4x4x4(tmp_path):
    """Verify selected_capability resolves triple_pool_4x4x4 with 4 Gemini and 4 Luna slots."""
    doc, _, _ = policy.load_worker_policy(_REPO_ROOT)
    cap = policy.selected_capability(
        _REPO_ROOT,
        "gemini_flash",
        doc,
        "mock/policy.toml",
        "mockdigest",
        "triple_pool_4x4x4",
    )
    assert cap["mode"] == "shared-local-worker"
    assert cap["parent_family"] == "gemini_flash"
    assert cap["policy_selection"] == "triple_pool_4x4x4"
    assert cap["borrowing"] is False
    assert cap["allowed_worker_kinds"] == ["gemini", "luna", "sonnet"]
    assert cap["limits"]["max_gemini"] == 4
    assert cap["limits"]["max_luna"] == 4
    assert cap["limits"]["max_aggregate"] == 12
    assert cap["luna_worker"]["model"] == "gpt-6-luna"
    assert cap["luna_worker"]["effort"] == "max"
    assert cap["luna_worker"]["transport"] == "codex_external"


# ---------------------------------------------------------------------------
# 4. Ledger capacity and 4+4 no-borrowing governance
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_policy_file(tmp_path):
    pol_file = tmp_path / "test_policy.toml"
    content = (_REPO_ROOT / "common/dispatcher/workers.toml").read_text()
    pol_file.write_text(content, encoding="utf-8")
    return pol_file


def test_ledger_initialization_and_status(tmp_path, mock_policy_file):
    """Verify ParentLedger initializes and correctly tracks status."""
    state_dir = tmp_path / "workers_state"
    parent_id = "test-parent-001"
    pleg = ledger.ParentLedger(parent_id, state_dir)

    capability = policy.resolve_worker_capability(
        _REPO_ROOT,
        "antigravity",
        "gemini-3.8-flash-high",
        "gemini_flash_sub",
        custom_policy_path=mock_policy_file,
    )
    assert capability is not None

    pleg.initialize_parent(
        "gemini_flash",
        workspace=_REPO_ROOT,
        task_authority="mutation_capable",
        worker_capability=capability,
        policy_path=mock_policy_file,
    )

    status = pleg.get_status()
    assert status["registered"] is True
    assert status["status"] == "active"
    assert status["parent_family"] == "gemini_flash"
    assert status["task_authority"] == "mutation_capable"
    assert status["max_gemini"] == 4
    assert status["max_luna"] == 4
    assert status["external_counts"] == {"gemini": 0, "luna": 0, "sonnet": 0}


def test_ledger_4x4_capacity_ceiling_and_no_borrowing(tmp_path, mock_policy_file):
    """Verify independent 4 Gemini and 4 Luna capacity pools with strict ceilings and no borrowing."""
    state_dir = tmp_path / "workers_state"
    parent_id = "test-parent-pool"
    pleg = ledger.ParentLedger(parent_id, state_dir)

    capability = policy.resolve_worker_capability(
        _REPO_ROOT,
        "antigravity",
        "gemini-3.8-flash-high",
        "gemini_flash_sub",
        custom_policy_path=mock_policy_file,
    )
    assert capability is not None

    pleg.initialize_parent(
        "gemini_flash",
        workspace=_REPO_ROOT,
        task_authority="mutation_capable",
        worker_capability=capability,
        policy_path=mock_policy_file,
    )

    # 1. Admit 4 Gemini jobs - all 4 must succeed
    gemini_jobs = []
    for i in range(4):
        job = pleg.reserve_gemini(
            f"gemini-job-{i}",
            idempotency_key=f"gem-key-{i}",
            payload_hash=f"hash-{i}",
            task_authority="read_only",
            worker_kind="gemini",
        )
        assert job["status"] == "reserved"
        gemini_jobs.append(job)

    status = pleg.get_status()
    assert status["external_counts"]["gemini"] == 4
    assert status["external_counts"]["luna"] == 0

    # 2. 5th Gemini job must raise CapacityExceededError
    with pytest.raises(ledger.CapacityExceededError):
        pleg.reserve_gemini(
            "gemini-job-5",
            idempotency_key="gem-key-5",
            payload_hash="hash-5",
            task_authority="read_only",
            worker_kind="gemini",
        )

    # 3. Admit 4 Luna jobs - all 4 must succeed (independent pool)
    luna_jobs = []
    for i in range(4):
        job = pleg.reserve_gemini(
            f"luna-job-{i}",
            idempotency_key=f"luna-key-{i}",
            payload_hash=f"luna-hash-{i}",
            task_authority="read_only",
            worker_kind="luna",
        )
        assert job["status"] == "reserved"
        luna_jobs.append(job)

    status = pleg.get_status()
    assert status["external_counts"]["gemini"] == 4
    assert status["external_counts"]["luna"] == 4

    # 4. 5th Luna job must raise CapacityExceededError (no borrowing from Gemini)
    with pytest.raises(ledger.CapacityExceededError):
        pleg.reserve_gemini(
            "luna-job-5",
            idempotency_key="luna-key-5",
            payload_hash="luna-hash-5",
            task_authority="read_only",
            worker_kind="luna",
        )

    # 5. Completing a Gemini job frees exactly 1 Gemini slot, does NOT affect Luna
    first_job_id = gemini_jobs[0]["job_id"]
    pleg.update_gemini_status(first_job_id, "completed", cleanup_proven=True)

    status = pleg.get_status()
    assert status["external_counts"]["gemini"] == 3
    assert status["external_counts"]["luna"] == 4

    # 6. Now a new Gemini slot can be admitted
    replacement = pleg.reserve_gemini(
        "gemini-job-replacement",
        idempotency_key="gem-key-rep",
        payload_hash="hash-rep",
        task_authority="read_only",
        worker_kind="gemini",
    )
    assert replacement["status"] == "reserved"
    assert pleg.get_status()["external_counts"]["gemini"] == 4


# ---------------------------------------------------------------------------
# 5. Environment variable handling (APGR_* primary, legacy AGENT_CENTRAL ignored)
# ---------------------------------------------------------------------------


def test_get_active_parent_id_precedence(monkeypatch):
    """Verify get_active_parent_id uses APGR_PARENT_ID and ignores AGENT_CENTRAL_PARENT_ID."""
    monkeypatch.delenv("APGR_PARENT_ID", raising=False)
    monkeypatch.delenv("AGENT_CENTRAL_PARENT_ID", raising=False)

    assert adapter.get_active_parent_id() is None

    # Legacy environment variable is ignored
    monkeypatch.setenv("AGENT_CENTRAL_PARENT_ID", "legacy-id")
    assert adapter.get_active_parent_id() is None

    # Primary APGR takes precedence
    monkeypatch.setenv("APGR_PARENT_ID", "primary-apgr-id")
    assert adapter.get_active_parent_id() == "primary-apgr-id"

    # Explicit matches
    assert adapter.get_active_parent_id("primary-apgr-id") == "primary-apgr-id"

    # Explicit conflict raises AuthorityViolationError
    with pytest.raises(adapter.AuthorityViolationError):
        adapter.get_active_parent_id("conflicting-id")


def test_leaf_worker_launch_prohibition(monkeypatch, tmp_path, mock_policy_file):
    """Verify that APGR_WORKER_LEAF blocks worker registration and launches, while AGENT_CENTRAL_WORKER_LEAF is ignored."""
    state_dir = tmp_path / "leaf_test_state"
    parent_id = "parent-for-leaf-test"
    pleg = ledger.ParentLedger(parent_id, state_dir)

    capability = policy.resolve_worker_capability(
        _REPO_ROOT,
        "antigravity",
        "gemini-3.8-flash-high",
        "gemini_flash_sub",
        custom_policy_path=mock_policy_file,
    )

    # Legacy flag is ignored: initializing parent succeeds
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)
    monkeypatch.setenv("AGENT_CENTRAL_WORKER_LEAF", "1")
    pleg.initialize_parent(
        "gemini_flash",
        workspace=_REPO_ROOT,
        task_authority="mutation_capable",
        worker_capability=capability,
        policy_path=mock_policy_file,
    )
    assert pleg.get_status()["registered"] is True

    # APGR_WORKER_LEAF blocks registration
    monkeypatch.setenv("APGR_WORKER_LEAF", "1")
    other_ledger = ledger.ParentLedger("other-parent", state_dir)
    with pytest.raises(ledger.AuthorityViolationError, match="leaf workers cannot register root parents"):
        other_ledger.initialize_parent(
            "gemini_flash",
            workspace=_REPO_ROOT,
            task_authority="mutation_capable",
            worker_capability=capability,
            policy_path=mock_policy_file,
        )

    # APGR_WORKER_LEAF blocks launching jobs
    with pytest.raises(adapter.AuthorityViolationError, match="leaf workers cannot launch additional workers"):
        adapter.launch_worker_job(parent_id, "task", state_dir=state_dir)


# ---------------------------------------------------------------------------
# 6. Supervisor environment scrubbing and prompt generation
# ---------------------------------------------------------------------------


def test_supervisor_build_leaf_prompt():
    """Verify build_leaf_prompt produces expected isolated non-recursive worker instructions."""
    prompt_gemini = supervisor.build_leaf_prompt(
        task="Do scoped task A",
        task_authority="read_only",
        mutation_scope=None,
        acceptance_criteria="Return clean analysis",
        worker_kind="gemini",
    )
    assert "# Gemini Worker Leaf Job" in prompt_gemini
    assert "You are an isolated Gemini leaf worker" in prompt_gemini
    assert "You must NOT attempt to register as a root agent" in prompt_gemini
    assert "Do not create further workers, spawn subagents" in prompt_gemini
    assert "Task Authority: READ_ONLY" in prompt_gemini
    assert "## Acceptance Criteria" in prompt_gemini
    assert "Return clean analysis" in prompt_gemini

    prompt_luna = supervisor.build_leaf_prompt(
        task="Do scoped task B",
        task_authority="mutation_capable",
        mutation_scope=["libexec/apgr_workers"],
        acceptance_criteria="All tests pass",
        worker_kind="luna",
    )
    assert "# Codex Luna Worker Leaf Job" in prompt_luna
    assert "You are an isolated Codex Luna leaf worker" in prompt_luna
    assert "Task Authority: MUTATION_CAPABLE" in prompt_luna
    assert "MUTATION SCOPE: You are permitted to modify only these paths: libexec/apgr_workers" in prompt_luna


# ---------------------------------------------------------------------------
# 7. Facade Context and MCP Configuration
# ---------------------------------------------------------------------------


def test_facade_context_environment(monkeypatch):
    """Verify WorkerFacadeContext exports APGR_* and snapshot variables with no AGENT_CENTRAL_* export."""
    state_dir = Path("/tmp/state")
    source_root = Path("/tmp/source")
    workspace = Path("/tmp/workspace")

    monkeypatch.setenv("APGR_DISPATCH_MODELS", "/path/to/models.toml")
    monkeypatch.setenv("APGR_DISPATCH_MODELS_SHA256", "sha-models")
    monkeypatch.setenv("APGR_DISPATCH_WORKERS", "/path/to/workers.toml")
    monkeypatch.setenv("APGR_DISPATCH_WORKERS_SHA256", "sha-workers")

    ctx = facade_context.WorkerFacadeContext(
        parent_id="parent-ctx-test",
        state_dir=state_dir,
        source_root=source_root,
        workspace=workspace,
        parent_family="gemini_flash",
        task_authority="mutation_capable",
        lifecycle_generation="gen-123",
        profile="gemini-3.8-flash-high",
    )

    env = ctx.environment()
    assert env["APGR_PARENT_ID"] == "parent-ctx-test"
    assert env["APGR_WORKER_STATE_DIR"] == str(state_dir)
    assert env["APGR_WORKER_SOURCE_ROOT"] == str(source_root)
    assert env["APGR_WORKER_WORKSPACE"] == str(workspace)
    assert env["APGR_WORKER_PARENT_FAMILY"] == "gemini_flash"
    assert env["APGR_WORKER_TASK_AUTHORITY"] == "mutation_capable"
    assert env["APGR_WORKER_LIFECYCLE_GENERATION"] == "gen-123"
    assert env["APGR_WORKER_PROFILE"] == "gemini-3.8-flash-high"
    assert env["APGR_DISPATCH_MODELS"] == "/path/to/models.toml"
    assert env["APGR_DISPATCH_MODELS_SHA256"] == "sha-models"
    assert env["APGR_DISPATCH_WORKERS"] == "/path/to/workers.toml"
    assert env["APGR_DISPATCH_WORKERS_SHA256"] == "sha-workers"

    # Legacy variables must NOT be exported
    for key in env:
        assert not key.startswith("AGENT_CENTRAL"), f"Unexpected legacy key in env: {key}"


def test_facade_context_mcp_tools():
    """Verify mcp_tool_names returns all required worker tools."""
    ctx = facade_context.WorkerFacadeContext(
        parent_id="parent-ctx-tools",
        state_dir=Path("/tmp/state"),
        source_root=_REPO_ROOT,
        workspace=_REPO_ROOT,
        parent_family="claude_opus",
        task_authority="read_only",
        lifecycle_generation="gen-tools",
        profile="gemini-3.8-flash-high",
    )

    names = ctx.mcp_tool_names()
    assert "mcp__agent_worker__submit" in names
    assert "mcp__agent_worker__status" in names
    assert "mcp__agent_worker__result" in names
    assert "mcp__agent_worker__wait" in names
    assert "mcp__agent_worker__outcome" in names
    assert "mcp__agent_worker__pause_pool" in names
    assert "mcp__agent_worker__abandon" in names
    assert "mcp__agent_worker__cancel" in names


# ---------------------------------------------------------------------------
# 8. Inspection and read_regular
# ---------------------------------------------------------------------------


def test_inspection_read_regular(tmp_path):
    """Verify self-contained read_regular in inspection.py safely reads regular files within limits."""
    test_file = tmp_path / "sample.txt"
    test_file.write_bytes(b"hello world")

    dir_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        data = inspection.read_regular(dir_fd, "sample.txt", limit=100)
        assert data == b"hello world"

        # Exceeding limit raises OverflowError
        with pytest.raises(OverflowError):
            inspection.read_regular(dir_fd, "sample.txt", limit=5)

        # Non-regular file (directory) raises ValueError
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        with pytest.raises(ValueError):
            inspection.read_regular(dir_fd, "sub", limit=100)
    finally:
        os.close(dir_fd)


def test_observed_process():
    """Verify observed_process detects alive and dead process PIDs."""
    # Current process is alive
    res_alive = inspection.observed_process(os.getpid())
    assert res_alive == "pid_present_identity_not_verified"

    # PID 9999999 is absent
    res_dead = inspection.observed_process(9999999)
    assert res_dead == "pid_absent_cleanup_not_proven"

    # Non-int or non-positive PID
    assert inspection.observed_process(0) == "unknown"
    assert inspection.observed_process(-1) == "unknown"
    assert inspection.observed_process(None) == "unknown"


# ---------------------------------------------------------------------------
# 9. Mutation Scope and CLI Integration Tests
# ---------------------------------------------------------------------------


def test_validate_mutation_scope():
    """Verify validate_mutation_scope enforces boundary rules on permitted paths."""
    assert adapter.validate_mutation_scope([]) == []
    assert adapter.validate_mutation_scope(["src/lib", "docs/spec.md"]) == ["src/lib", "docs/spec.md"]

    # Traversal rejected
    with pytest.raises(adapter.AuthorityViolationError, match="cannot traverse a parent directory"):
        adapter.validate_mutation_scope(["../outside"])

    # Absolute path rejected
    with pytest.raises(adapter.AuthorityViolationError, match="must be workspace-relative"):
        adapter.validate_mutation_scope(["/etc/passwd"])


def test_cli_parent_status_subprocess(tmp_path):
    """Verify bin/agent-worker parent status runs via subprocess and outputs JSON."""
    ep_worker = _REPO_ROOT / "bin" / "agent-worker"
    env = os.environ.copy()
    env["APGR_PARENT_ID"] = "cli-test-parent"
    env["APGR_WORKER_STATE_DIR"] = str(tmp_path)
    env.pop("APGR_WORKER_LEAF", None)
    env.pop("AGENT_CENTRAL_WORKER_LEAF", None)

    res = subprocess.run(
        [sys.executable, str(ep_worker), "parent", "status", "--parent-id", "cli-test-parent", "--state-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["parent_id"] == "cli-test-parent"
    assert data["registered"] is False
    assert data["max_gemini"] == 4


def test_codex_external_event_parsing():
    """Verify parse_codex_events parses JSONL stream into clean observation record."""
    raw = (
        '{"type": "item.output_text.delta", "text": "Beginning task..."}\n'
        '{"type": "model_info", "model": "gpt-6-luna", "reasoning_effort": "max"}\n'
        '{"type": "item.completed", "item": {"type": "agent_message", "text": "Task finished successfully."}}\n'
    )
    parsed = codex_external.parse_codex_events(raw)
    assert "Beginning task..." in parsed["response"]
    assert "Task finished successfully." in parsed["response"]
    assert parsed["effective_model"] == "gpt-6-luna"
    assert parsed["effective_effort"] == "max"
    assert parsed["observed_models"] == ["gpt-6-luna"]
    assert parsed["observed_efforts"] == ["max"]
    assert parsed["malformed_event_lines"] == 0


# ---------------------------------------------------------------------------
# 10. Default state directory resolution and legacy env scrubbing
# ---------------------------------------------------------------------------


def test_default_state_dir_apgr_home_resolution(tmp_path, monkeypatch):
    """Verify get_default_state_dir uses APGR_HOME/state/workers and ignores AGENT_CENTRAL."""
    monkeypatch.delenv("APGR_HOME", raising=False)
    monkeypatch.delenv("APGR_WORKER_STATE_DIR", raising=False)
    monkeypatch.delenv("AGENT_CENTRAL_WORKER_STATE_DIR", raising=False)

    # 1. Unset environment defaults to ~/.apgr/state/workers (never ~/.cache)
    default_dir = ledger.get_default_state_dir()
    expected_default = (Path.home() / ".apgr" / "state" / "workers").resolve()
    assert default_dir == expected_default
    assert ".cache" not in str(default_dir)

    # 2. Legacy AGENT_CENTRAL_WORKER_STATE_DIR is strictly ignored
    monkeypatch.setenv("AGENT_CENTRAL_WORKER_STATE_DIR", str(tmp_path / "legacy_state"))
    assert ledger.get_default_state_dir() == expected_default

    # 3. APGR_HOME resolves to <APGR_HOME>/state/workers
    custom_home = tmp_path / "custom_apgr"
    monkeypatch.setenv("APGR_HOME", str(custom_home))
    resolved_home = ledger.get_default_state_dir()
    assert resolved_home == (custom_home / "state" / "workers").resolve()

    # 4. APGR_WORKER_STATE_DIR overrides APGR_HOME
    custom_override = tmp_path / "override_workers"
    monkeypatch.setenv("APGR_WORKER_STATE_DIR", str(custom_override))
    assert ledger.get_default_state_dir() == custom_override.resolve()


def test_child_env_scrubbing_and_no_pythonpath_donor(tmp_path, monkeypatch):
    """Verify supervisor launch scrubs AGENT_CENTRAL_* and avoids donor PYTHONPATH inheritance."""
    state_dir = tmp_path / "workers_state"
    launch_dir = tmp_path / "launch"
    launch_dir.mkdir()
    parent_id = "parent-env-scrub"
    pleg = ledger.ParentLedger(parent_id, state_dir)

    capability = policy.resolve_worker_capability(
        _REPO_ROOT,
        "antigravity",
        "gemini-3.8-flash-high",
        "gemini_flash_sub",
    )
    pleg.initialize_parent(
        "gemini_flash",
        workspace=_REPO_ROOT,
        task_authority="mutation_capable",
        worker_capability=capability,
    )

    from agent_phase.runtime_models import current_bundle, launch_capture
    bundle = current_bundle(_REPO_ROOT)

    with launch_capture(bundle, launch_dir):
        # Set up dirty environment with AGENT_CENTRAL variables and a donor PYTHONPATH
        monkeypatch.setenv("AGENT_CENTRAL_JOB_ID", "legacy-job-999")
        monkeypatch.setenv("AGENT_CENTRAL_MANAGED_PARENT", "legacy-parent")
        monkeypatch.setenv("AGENT_CENTRAL_WORKER_LEAF", "1")
        monkeypatch.setenv("PYTHONPATH", "/donor/library/path:/another/donor/path")

        captured_env: dict[str, str] = {}

        class MockPopen:
            def __init__(self, cmd, cwd, env, **kwargs):
                captured_env.update(env)
                self.pid = os.getpid()

            def wait(self, timeout=None):
                return 0

            def poll(self):
                return 0

            def kill(self):
                pass

            def terminate(self):
                pass

        monkeypatch.setattr(subprocess, "Popen", MockPopen)

        # Launch worker job through adapter
        adapter.launch_worker_job(
            parent_id=parent_id,
            task="Scoped leaf test task",
            task_authority="read_only",
            state_dir=state_dir,
        )

        # Verify AGENT_CENTRAL_* scrubbed
        for key in captured_env:
            assert not key.startswith("AGENT_CENTRAL"), f"Unscrubbed legacy key: {key}"

        # Verify no PYTHONPATH donor inheritance - only candidate libexec allowed
        expected_pythonpath = str((_REPO_ROOT / "libexec").resolve())
        assert captured_env["PYTHONPATH"] == expected_pythonpath
        assert "/donor/library/path" not in captured_env["PYTHONPATH"]

        # Verify snapshot variables preserved
        assert "APGR_DISPATCH_MODELS" in captured_env
        assert "APGR_DISPATCH_MODELS_SHA256" in captured_env
        assert "APGR_DISPATCH_WORKERS" in captured_env
        assert "APGR_DISPATCH_WORKERS_SHA256" in captured_env


def test_native_launch_binding_env_scrubbing(tmp_path, monkeypatch):
    """Verify native_launch.prepare_native_binding scrubs AGENT_CENTRAL and preserves snapshot vars."""
    state_dir = tmp_path / "workers_state"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    launch_dir = tmp_path / "launch"
    launch_dir.mkdir()

    from agent_phase.runtime_models import current_bundle, launch_capture
    bundle = current_bundle(_REPO_ROOT)

    with launch_capture(bundle, launch_dir):
        monkeypatch.setenv("AGENT_CENTRAL_ACTIVE", "true")
        monkeypatch.setenv("AGENT_CENTRAL_TOKEN", "secret-token")

        binding = native_launch.prepare_native_binding(
            _REPO_ROOT,
            parent_id="native-parent-01",
            parent_profile="implementation-testing",
            workspace=workspace,
            state_dir=state_dir,
            task_authority="read_only",
        )

        overrides = binding.config_overrides()
        assert "mcp_servers.agent_worker.required=true" in overrides
        for tool in binding.allowlisted_tools:
            assert f'mcp_servers.agent_worker.tools.{tool.removeprefix("mcp__agent_worker__")}.approval_mode="approve"' in overrides
        assert not any(value.startswith("approval_policy=") for value in overrides)
        env = binding.facade_environment()
        assert env["APGR_PARENT_ID"] == "native-parent-01"
        assert "APGR_DISPATCH_MODELS" in env
        assert "APGR_DISPATCH_MODELS_SHA256" in env
        assert "APGR_DISPATCH_WORKERS" in env
        assert "APGR_DISPATCH_WORKERS_SHA256" in env
        for key in env:
            assert not key.startswith("AGENT_CENTRAL"), f"Unscrubbed legacy key in native binding: {key}"


# ---------------------------------------------------------------------------
# 11. Canonical candidate standalone policy and bundle loading
# ---------------------------------------------------------------------------


def test_canonical_candidate_standalone_policy(tmp_path, monkeypatch):
    monkeypatch.setenv("APGR_HOME", str(tmp_path / "isolated-home"))
    """Verify load_worker_policy default resolves common/dispatcher/workers.toml via bundle."""
    data, source, sha256 = policy.load_worker_policy(_REPO_ROOT)
    assert data["schema"] == "agent-worker-policy-v2"
    assert data["limits"]["max_gemini_workers_per_parent"] == 4
    assert data["limits"]["max_aggregate_workers_per_codex_parent"] == 12
    assert data["gemini_worker"]["provider"] == "antigravity"
    assert data["gemini_worker"]["profile"] == "gemini-3.8-flash-high"
    assert data["selections"]["triple_pool_4x4x4"]["max_gemini"] == 4
    assert data["selections"]["triple_pool_4x4x4"]["max_luna"] == 4
    assert data["selections"]["triple_pool_4x4x4"]["borrowing"] is False
    assert source == "common/dispatcher/workers.toml"
    assert len(sha256) == 64

    # Verify capability resolution using canonical bundle
    cap_gemini = policy.resolve_worker_capability(
        _REPO_ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub"
    )
    assert cap_gemini is not None
    assert cap_gemini["mode"] == "shared-local-worker"
    assert cap_gemini["parent_family"] == "gemini_flash"
    assert cap_gemini["limits"]["max_gemini"] == 4
    assert cap_gemini["limits"]["max_aggregate"] == 12

    cap_codex = policy.selected_capability(
        _REPO_ROOT, "codex_parent", data, source, sha256, "triple_pool_4x4x4"
    )
    assert cap_codex is not None
    assert cap_codex["parent_family"] == "codex_parent"
    assert cap_codex["limits"]["max_gemini"] == 4
    assert cap_codex["limits"]["max_luna"] == 4
    assert cap_codex["limits"]["max_aggregate"] == 12


# ---------------------------------------------------------------------------
# 12. Operator snapshot effective args and tamper/symlink refusal
# ---------------------------------------------------------------------------


def test_operator_snapshot_effective_args_and_validation(tmp_path, monkeypatch):
    """Verify APGR_DISPATCH_WORKERS no-follow read, digest validation, and refusal cases."""
    snapshot_file = tmp_path / "launch-workers.toml"
    content = b"""schema = "agent-worker-policy-v1"

[limits]
max_gemini_workers_per_parent = 4
max_aggregate_workers_per_astra_parent = 8

[gemini_worker]
provider = "antigravity"
profile = "gemini-3.8-flash-high"

[selections.dual_pool_4x4]
max_gemini = 4
max_luna = 4
borrowing = false

[selections.dual_pool_4x4.luna_worker]
provider = "codex"
profile = "luna-worker"
"""
    snapshot_file.write_bytes(content)
    valid_digest = hashlib.sha256(content).hexdigest()

    # 1. Valid snapshot and matching digest
    monkeypatch.setenv("APGR_DISPATCH_WORKERS", str(snapshot_file))
    monkeypatch.setenv("APGR_DISPATCH_WORKERS_SHA256", valid_digest)
    data, src, digest = policy.load_worker_policy(_REPO_ROOT)
    assert data["schema"] == "agent-worker-policy-v1"
    assert digest == valid_digest

    # 2. Tampered / mismatched digest raises WorkerPolicyError
    monkeypatch.setenv("APGR_DISPATCH_WORKERS_SHA256", "0" * 64)
    with pytest.raises(policy.WorkerPolicyError, match="digest mismatch"):
        policy.load_worker_policy(_REPO_ROOT)

    # 3. Missing APGR_DISPATCH_WORKERS_SHA256 raises WorkerPolicyError
    monkeypatch.delenv("APGR_DISPATCH_WORKERS_SHA256")
    with pytest.raises(policy.WorkerPolicyError, match="APGR_DISPATCH_WORKERS_SHA256 required"):
        policy.load_worker_policy(_REPO_ROOT)

    # 4. Non-absolute APGR_DISPATCH_WORKERS path raises WorkerPolicyError
    monkeypatch.setenv("APGR_DISPATCH_WORKERS", "relative/launch-workers.toml")
    monkeypatch.setenv("APGR_DISPATCH_WORKERS_SHA256", valid_digest)
    with pytest.raises(policy.WorkerPolicyError, match="must be an absolute path"):
        policy.load_worker_policy(_REPO_ROOT)

    # 5. Symlink snapshot refused (O_NOFOLLOW)
    symlink_file = tmp_path / "symlink-workers.toml"
    os.symlink(snapshot_file, symlink_file)
    monkeypatch.setenv("APGR_DISPATCH_WORKERS", str(symlink_file))
    monkeypatch.setenv("APGR_DISPATCH_WORKERS_SHA256", valid_digest)
    with pytest.raises(policy.WorkerPolicyError, match="cannot read captured workers policy"):
        policy.load_worker_policy(_REPO_ROOT)


# ---------------------------------------------------------------------------
# 13. Runtime models selection and mandatory invariants
# ---------------------------------------------------------------------------


def test_model_selection_and_mandatory_invariants():
    """Verify mandatory invariants: gpt-6-luna/max, gpt-6.1-sol/xhigh, cap 4."""
    # 1. Luna worker profile: mandatory gpt-6-luna and max effort, posture agents.enabled=false
    luna = codex_external.load_luna_profile(_REPO_ROOT)
    assert luna.name == "luna-worker"
    assert luna.model == "gpt-6-luna"
    assert luna.effort == "max"
    assert luna.agents_enabled is False

    with pytest.raises(codex_external.CodexExternalError, match="requires profile 'luna-worker'"):
        codex_external.load_luna_profile(_REPO_ROOT, profile="other-worker")

    # 2. Codex parent profile: mandatory gpt-6.1-sol with xhigh effort
    model, effort, rel_path, sha256 = native_launch._load_parent_profile(
        _REPO_ROOT, "implementation-testing"
    )
    assert model == "gpt-6.1-sol"
    assert effort == "xhigh"
    assert len(sha256) == 64

    # 3. Native worker source: mandatory gpt-6-luna/max and native capacity 4
    native_source = native_launch.load_native_worker_source(_REPO_ROOT)
    assert native_source.model == "gpt-6-luna"
    assert native_source.effort == "max"
    assert native_source.source_max_concurrent_threads == 4

    # 4. identify_parent_family: standard route resolution
    assert policy.identify_parent_family(_REPO_ROOT, "antigravity", "gemini-3.8-flash-high") == "gemini_flash"
    assert policy.identify_parent_family(_REPO_ROOT, "codex", "implementation-testing") == "codex_parent"
    assert policy.identify_parent_family(_REPO_ROOT, "codex", "luna-worker") is None
    assert policy.identify_parent_family(_REPO_ROOT, "antigravity", "unknown-profile") is None


# ---------------------------------------------------------------------------
# 14. Read-only authority refusal across ledger, adapter, and MCP
# ---------------------------------------------------------------------------


def test_read_only_authority_refusal(tmp_path, mock_policy_file):
    """Verify read-only parent refuses mutation-capable jobs across ledger, adapter, and MCP."""
    state_dir = tmp_path / "workers_state"
    parent_id = "parent-ro-test"
    pleg = ledger.ParentLedger(parent_id, state_dir)

    capability = policy.resolve_worker_capability(
        _REPO_ROOT,
        "antigravity",
        "gemini-3.8-flash-high",
        "gemini_flash_sub",
        custom_policy_path=mock_policy_file,
    )

    # 1. Initialize parent with task_authority="read_only"
    pleg.initialize_parent(
        "gemini_flash",
        workspace=_REPO_ROOT,
        task_authority="read_only",
        worker_capability=capability,
        policy_path=mock_policy_file,
    )

    # 2. Ledger refuses mutation-capable reservation under read-only parent
    with pytest.raises(ledger.AuthorityViolationError, match="read-only parent cannot launch mutation-capable worker"):
        pleg.reserve_gemini(
            "job-mutation-denied",
            idempotency_key="key-denied",
            payload_hash="hash-denied",
            task_authority="mutation_capable",
            mutation_scope=["libexec"],
        )

    # Read-only reservation succeeds
    ro_job = pleg.reserve_gemini(
        "job-ro-allowed",
        idempotency_key="key-ro",
        payload_hash="hash-ro",
        task_authority="read_only",
    )
    assert ro_job["status"] == "reserved"

    # 3. Read-only task cannot define a mutation scope
    with pytest.raises(ledger.AuthorityViolationError, match="read-only worker cannot claim a mutation scope"):
        pleg.reserve_gemini(
            "job-ro-with-scope",
            idempotency_key="key-ro-scope",
            payload_hash="hash-ro-scope",
            task_authority="read_only",
            mutation_scope=["libexec"],
        )

    # 4. Adapter launch_worker_job refuses mutation-capable launch under read-only parent
    with pytest.raises(adapter.AuthorityViolationError, match="cannot launch a mutating worker from a read-only parent"):
        adapter.launch_worker_job(
            parent_id=parent_id,
            task="Attempted mutation",
            task_authority="mutation_capable",
            state_dir=state_dir,
        )

    # 5. MCP submit refuses mutation_capable request on read_only context
    claude_id = "parent-claude-ro"
    data, src, sha = policy.load_worker_policy(_REPO_ROOT)
    capability_claude = policy.selected_capability(
        _REPO_ROOT, "claude_opus", data, src, sha, "triple_pool_4x4x4"
    )
    capability_claude["interface"] = "stdio-mcp"
    capability_claude["source_root"] = str(_REPO_ROOT)
    capability_claude["lifecycle_generation"] = "gen-ro"
    pleg_claude = ledger.ParentLedger(claude_id, state_dir)
    pleg_claude.initialize_parent(
        "claude_opus",
        workspace=_REPO_ROOT,
        task_authority="read_only",
        worker_capability=capability_claude,
    )
    ctx = facade_context.WorkerFacadeContext(
        parent_id=claude_id,
        state_dir=state_dir,
        source_root=_REPO_ROOT,
        workspace=_REPO_ROOT,
        parent_family="claude_opus",
        task_authority="read_only",
        lifecycle_generation="gen-ro",
        profile="gemini-3.8-flash-high",
    )
    server = mcp.WorkerMCPServer(ctx)
    with pytest.raises(mcp.MCPRequestError, match="a read-only parent cannot submit a mutating task"):
        server._submit({
            "task": "Attempt mutation via MCP",
            "task_authority": "mutation_capable",
        })
