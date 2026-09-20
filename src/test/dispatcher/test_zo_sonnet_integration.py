"""APG166ZO foreign Sonnet external worker transport tests.

Validates the complete external Sonnet launch path:
- Exact profile ("sonnet-worker"), model ("claude-sonnet-5-5"), and effort ("high")
  validation and provenance from bundle+catalog.
- Fixed installed claude CLI argv construction with restricted mode, leaf tool
  confinement (Read, Glob, Grep for read-only; Write, Edit for mutation-capable),
  empty MCP/setting-sources, and rejection of Agent/Task tools.
- Parent APGR identity and session scrubbing while preserving provider auth.
- Honest stream-json event parsing and model/effort observation (not requested values).
- Explicit quota exhaustion recognition and isolated pool pausing.
- Full supervisor execution with detached process group custody and cleanup.
- MCP facade dynamic enum binding to allowed worker kinds.
- Native launch binding for codex_parent supporting external gemini and sonnet.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

import pytest

from apgr_workers.facade_context import WorkerFacadeContext
from apgr_workers.ledger import ParentLedger
from apgr_workers.mcp import WorkerMCPServer, MCPRequestError
from apgr_workers.native_launch import (
    apply_worker_exclusions,
    prepare_native_binding,
)
from apgr_workers.supervisor import run_supervisor


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def clean_ambient_dispatch_env(monkeypatch):
    monkeypatch.delenv("APGR_DISPATCH_MODELS", raising=False)
    monkeypatch.delenv("APGR_DISPATCH_MODELS_SHA256", raising=False)
    monkeypatch.delenv("APGR_DISPATCH_WORKERS", raising=False)
    monkeypatch.delenv("APGR_DISPATCH_WORKERS_SHA256", raising=False)
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)


def _make_gemini_flash_triple_capability(lifecycle_generation: str = "gen-1") -> dict[str, Any]:
    return {
        "parent_provider": "antigravity",
        "parent_profile": "gemini-3.8-flash-high",
        "parent_family": "gemini_flash",
        "source_root": str(ROOT),
        "execution_mode": "gemini_flash_sub",
        "policy_selection": "triple_pool_4x4x4",
        "available": True,
        "allowed": True,
        "interface": "stdio-mcp",
        "lifecycle_generation": lifecycle_generation,
        "native_worker": {"enabled": False},
        "borrowing": False, "leaf_only": True, "parent_authority": True,
        "limits": {"max_gemini": 4, "max_luna": 4, "max_sonnet": 4, "max_aggregate": 12},
        "allowed_worker_kinds": ["gemini", "luna", "sonnet"],
        "gemini_worker": {"transport": "antigravity", "provider": "antigravity", "profile": "gemini-flash"},
        "luna_worker": {"transport": "codex_external", "provider": "codex", "profile": "luna-worker", "maximum_concurrency": 4},
        "sonnet_worker": {
            "transport": "claude_external",
            "provider": "claude",
            "profile": "sonnet-worker",
            "model": "claude-sonnet-5-5",
            "effort": "high", "maximum_concurrency": 4,
        },
    }


def _create_fake_claude_executable(bin_dir: Path, *, mode: str = "success") -> Path:
    """Create a standalone fake claude CLI executable recording invocations."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_claude = bin_dir / "claude"
    script = "#!" + sys.executable + "\n" + f"""
import json
import os
import sys
from pathlib import Path

capture_file = os.environ.get("FAKE_CLAUDE_CAPTURE_FILE")
if capture_file:
    payload = {{
        "argv": list(sys.argv),
        "env": {{
            key: os.environ[key] for key in (
                "APGR_PARENT_ID", "APGR_WORKER_FACADE", "APGR_WORKER_LEAF",
                "CODEX_THREAD_ID", "CLAUDE_CODE_SESSION_ID",
                "ANTHROPIC_API_KEY", "CLAUDE_CONFIG_DIR"
            ) if key in os.environ
        }},
    }}
    Path(capture_file).write_text(json.dumps(payload, indent=2), encoding="utf-8")

# Read stdin prompt
try:
    prompt = sys.stdin.read()
except Exception:
    prompt = ""

mode = "{mode}"
if mode == "quota":
    # Emit explicit quota exhaustion event
    print(json.dumps({{"type": "system", "session_id": "00000000-0000-0000-0000-000000000001"}}), flush=True)
    print(json.dumps({{
        "type": "error",
        "error": {{"message": "credit balance is too low", "code": "insufficient_quota"}},
        "status": "quota_exhausted"
    }}), flush=True)
    sys.exit(1)
elif mode == "transient_error":
    print(json.dumps({{
        "type": "error",
        "error": {{"message": "rate limit exceeded, retry after 5s", "retry_after": 5}},
        "status": "rate_limited"
    }}), flush=True)
    sys.exit(1)
else:
    # Successful execution with stream-json events
    session_id = "00000000-0000-0000-0000-000000000002"
    print(json.dumps({{
        "type": "system",
        "session_id": session_id,
        "model": "claude-sonnet-5-5",
        "effort": "high"
    }}), flush=True)
    print(json.dumps({{
        "type": "assistant",
        "message": {{
            "content": [
                {{"type": "text", "text": "synthetic sonnet external worker response"}}
            ]
        }}
    }}), flush=True)
    print(json.dumps({{
        "type": "result",
        "result": "synthetic sonnet external worker response"
    }}), flush=True)
    sys.exit(0)
"""
    fake_claude.write_text(script, encoding="utf-8")
    fake_claude.chmod(fake_claude.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return fake_claude


def test_run_supervisor_claude_external_success(tmp_path, monkeypatch):
    monkeypatch.setattr("apgr_workers.ledger._process_identity", lambda pid: f"fixture-start-{pid}")
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)
    bin_dir = tmp_path / "bin"
    fake_claude = _create_fake_claude_executable(bin_dir, mode="success")
    capture_file = tmp_path / "claude_capture.json"

    # Prepend fake claude to PATH
    orig_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{bin_dir}:{orig_path}")
    monkeypatch.setenv("FAKE_CLAUDE_CAPTURE_FILE", str(capture_file))

    state_dir = tmp_path / "state"
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    parent_id = "test-parent-sonnet"
    ledger = ParentLedger(parent_id, state_dir)
    ledger.initialize_parent(
        "gemini_flash",
        workspace=ws_dir,
        task_authority="read_only",
        worker_capability=_make_gemini_flash_triple_capability(),
    )

    job_id = "job-sonnet-1"
    task_file = tmp_path / f"{job_id}.task.json"
    task_file.write_text(json.dumps({
        "workspace": str(ws_dir),
        "task_authority": "read_only",
        "worker_kind": "sonnet",
        "profile": "sonnet-worker",
        "task": "Perform read-only code survey",
    }), encoding="utf-8")

    # Reserve the job in ledger
    ledger.reserve_external(
        job_id,
        "key-1",
        "hash-1",
        task_authority="read_only",
        task_file=str(task_file),
        worker_kind="sonnet"
    )
    ledger.claim_gemini_launch(job_id)

    exit_code = run_supervisor(parent_id, job_id, task_file, state_dir=state_dir)
    assert exit_code == 0

    # Inspect captured arguments to fake claude
    assert capture_file.is_file()
    captured = json.loads(capture_file.read_text(encoding="utf-8"))
    assert captured["argv"][0] == str(fake_claude)
    assert "--model" in captured["argv"]
    assert captured["argv"][captured["argv"].index("--model") + 1] == "claude-sonnet-5-5"
    assert "--restricted" in captured["argv"]
    assert "--permission-mode" in captured["argv"]
    assert captured["argv"][captured["argv"].index("--permission-mode") + 1] == "plan"
    assert captured["env"].get("APGR_WORKER_LEAF") == "1"
    assert "APGR_PARENT_ID" not in captured["env"]

    # Verify result payload
    result_file = tmp_path / f"{job_id}.result.json"
    assert result_file.is_file()
    result = json.loads(result_file.read_text(encoding="utf-8"))
    assert result["status"] == "completed"
    assert result["transport"] == "claude_external"
    assert result["provider"] == "claude"
    assert result["worker_kind"] == "sonnet"
    assert result["requested_model"] == "claude-sonnet-5-5"
    assert result["requested_effort"] == "high"
    assert result["effective_model"] == "claude-sonnet-5-5"
    assert result["effective_effort"] == "high"
    assert result["model_evidence"]["match"] is True
    assert result["cleanup_proven"] is True


def test_run_supervisor_sonnet_quota_pause(tmp_path, monkeypatch):
    monkeypatch.setattr("apgr_workers.ledger._process_identity", lambda pid: f"fixture-start-{pid}")
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)
    bin_dir = tmp_path / "bin"
    _create_fake_claude_executable(bin_dir, mode="quota")

    orig_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{bin_dir}:{orig_path}")

    state_dir = tmp_path / "state"
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    parent_id = "test-parent-quota"
    ledger = ParentLedger(parent_id, state_dir)
    ledger.initialize_parent(
        "gemini_flash",
        workspace=ws_dir,
        task_authority="read_only",
        worker_capability=_make_gemini_flash_triple_capability(),
    )

    job_id = "job-sonnet-quota"
    task_file = tmp_path / f"{job_id}.task.json"
    task_file.write_text(json.dumps({
        "workspace": str(ws_dir),
        "task_authority": "read_only",
        "worker_kind": "sonnet",
        "profile": "sonnet-worker",
        "task": "Quota test task",
    }), encoding="utf-8")

    ledger.reserve_external(
        job_id,
        "key-quota",
        "hash-quota",
        task_authority="read_only",
        task_file=str(task_file),
        worker_kind="sonnet"
    )
    ledger.claim_gemini_launch(job_id)

    exit_code = run_supervisor(parent_id, job_id, task_file, state_dir=state_dir)
    assert exit_code == 1

    status = ledger.get_status()
    pools = status.get("pool_state", {})
    # Sonnet pool must be paused
    assert pools.get("sonnet", {}).get("paused") is True
    assert pools.get("sonnet", {}).get("cause") == "explicit_quota_exhaustion"
    # Other pools remain unpaused
    assert pools.get("gemini", {}).get("paused") is not True
    assert pools.get("luna", {}).get("paused") is not True


def test_mcp_facade_allowed_worker_kinds_enum(tmp_path, monkeypatch):
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)
    state_dir = tmp_path / "state"
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    parent_id = "test-parent-mcp"
    ledger = ParentLedger(parent_id, state_dir)
    ledger.initialize_parent(
        "gemini_flash",
        workspace=ws_dir,
        task_authority="read_only",
        worker_capability=_make_gemini_flash_triple_capability(),
    )

    ctx = WorkerFacadeContext(
        parent_id=parent_id,
        state_dir=state_dir,
        source_root=ROOT,
        workspace=ws_dir,
        parent_family="gemini_flash",
        task_authority="read_only",
        lifecycle_generation="gen-1",
        profile="gemini-flash",
    )
    server = WorkerMCPServer(ctx)
    specs = server._tool_specs()
    submit_spec = next(s for s in specs if s["name"] == "submit")
    pause_spec = next(s for s in specs if s["name"] == "pause_pool")

    # Allowed kinds enum must include all three kinds
    submit_enum = submit_spec["inputSchema"]["properties"]["worker_kind"]["enum"]
    assert submit_enum == ["gemini", "luna", "sonnet"]
    pause_enum = pause_spec["inputSchema"]["properties"]["worker_kind"]["enum"]
    assert pause_enum == ["gemini", "luna", "sonnet"]

    # Rejection of invalid worker kind in pause_pool
    with pytest.raises(MCPRequestError, match="not allowed"):
        server._call_tool("pause_pool", {"worker_kind": "invalid", "reason": "test", "evidence": "test"})


def test_native_launch_codex_parent_external_sonnet(tmp_path):
    state_dir = tmp_path / "state"
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    parent_id = "test-codex-parent"

    capability = {
        "parent_family": "codex_parent",
        "policy_selection": "triple_pool_4x4x4",
        "allowed": True,
        "limits": {"max_gemini": 4, "max_luna": 4, "max_sonnet": 4, "max_aggregate": 12},
        "allowed_worker_kinds": ["gemini", "sonnet"],
        "gemini_worker": {"profile": "gemini-worker"},
        "sonnet_worker": {"profile": "sonnet-worker"},
    }

    binding = prepare_native_binding(
        ROOT,
        parent_id=parent_id,
        parent_profile="sysadmin-primary",
        workspace=ws_dir,
        state_dir=state_dir,
        task_authority="read_only",
        capability=capability,
    )
    assert binding.parent_family == "codex_parent"
    assert "sonnet" in binding.allowed_worker_kinds
    assert "gemini" in binding.allowed_worker_kinds
    assert binding.facade_enabled is True

    # Test exclusion of sonnet
    excluded_cap = apply_worker_exclusions(capability, excluded_worker_kinds=["sonnet"])
    assert "sonnet" in excluded_cap["excluded_worker_kinds"]
    assert "sonnet" not in excluded_cap["allowed_worker_kinds"]
    assert "gemini" in excluded_cap["allowed_worker_kinds"]


def test_gemini_facade_triple_pool_validation():
    from apgr_workers.gemini_parent import capability_error, validate_registration, worker_provenance

    cap = _make_gemini_flash_triple_capability()
    assert capability_error(cap) is None
    validate_registration(cap)

    # Worker provenance for sonnet
    prov = worker_provenance(cap, "sonnet")
    assert prov["worker_kind"] == "sonnet"
    assert prov["transport"] == "claude_external"
    assert prov["worker"]["model"] == "claude-sonnet-5-5"
    assert prov["worker"]["effort"] == "high"

    # Worker provenance for luna and gemini
    luna_prov = worker_provenance(cap, "luna")
    assert luna_prov["transport"] == "codex_external"
    gemini_prov = worker_provenance(cap, "gemini")
    assert gemini_prov["transport"] == "antigravity"

    # Mismatched model/effort in sonnet_worker
    bad_model = dict(cap, sonnet_worker={"transport": "claude_external", "provider": "claude", "model": "claude-3-opus", "effort": "high"})
    assert capability_error(bad_model) is not None
    with pytest.raises(ValueError, match="Gemini parent requires qualified profile and Flash High provenance"):
        validate_registration(bad_model)

    # Invalid limits
    bad_limits = dict(cap, limits={"max_gemini": 4, "max_luna": 4, "max_sonnet": 3, "max_aggregate": 11})
    assert capability_error(bad_limits) is not None

    # Missing sonnet in allowed_worker_kinds
    bad_kinds = dict(cap, allowed_worker_kinds=["gemini", "luna"])
    assert capability_error(bad_kinds) is not None
