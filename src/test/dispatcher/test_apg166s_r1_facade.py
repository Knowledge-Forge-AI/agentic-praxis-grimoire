"""Source projection and narrow worker facade contracts (provider-free)."""
from pathlib import Path
import json
import os
import subprocess
import tomllib

from agent_phase.runtime_models import source_defaults
from apgr_workers import policy
from apgr_workers.ledger import ParentLedger
from apgr_workers.facade_context import WorkerFacadeContext, MCP_TOOL_NAMES

ROOT = Path(__file__).resolve().parents[3]


def test_default_luna_projections_match_inventory():
    catalog = tomllib.loads((ROOT / "common/dispatcher/models.toml").read_text())
    selected = catalog["providers"]["codex"]["luna-worker"]
    worker = tomllib.loads((ROOT / "codex/profiles/luna-worker.config.toml").read_text())
    native = tomllib.loads((ROOT / "codex/config.d/170-subagents.toml").read_text())
    assert worker["model"] == selected["model"]
    assert worker["model_reasoning_effort"] == selected["effort"]
    assert native["agents"]["default_subagent_model"] == selected["model"]
    assert native["agents"]["default_subagent_reasoning_effort"] == selected["effort"]


def test_real_facade_lists_closed_tools_with_fake_scratch_context(tmp_path):
    with source_defaults():
        cap = policy.resolve_worker_capability(ROOT, "claude", "opus-high-review", "gemini_sub")
    cap.update(interface="stdio-mcp", source_root=str(ROOT), lifecycle_generation="test-handshake")
    state = tmp_path / "state"
    ledger = ParentLedger("fake-handshake", state)
    ledger.initialize_parent("claude_opus", workspace=tmp_path, task_authority="read_only", worker_capability=cap)
    context = WorkerFacadeContext("fake-handshake", state, ROOT, tmp_path, "claude_opus", "read_only", "test-handshake", cap["gemini_worker"]["profile"])
    environment = {key: value for key, value in os.environ.items() if not key.startswith(("AGENT_CENTRAL_", "APGR_"))}
    environment.update(context.environment())
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    requests = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}}, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}]
    result = subprocess.run([str(ROOT / "bin/agent-worker-mcp")], cwd=tmp_path, env=environment, input="".join(json.dumps(item) + "\n" for item in requests), capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    tools = replies[1]["result"]["tools"]
    assert {tool["name"] for tool in tools} == {name.removeprefix("mcp__agent_worker__") for name in MCP_TOOL_NAMES}
    assert all(tool["inputSchema"]["type"] == "object" for tool in tools)
    submit = next(tool for tool in tools if tool["name"] == "submit")
    assert {"task", "worker_kind", "task_authority"} <= set(submit["inputSchema"]["properties"])
    assert not json.loads(ledger.data_path.read_text())["gemini_jobs"]
