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
from pathlib import Path
import stat
import sys
from typing import Any

import pytest

from apgr_workers.claude_external import (
    CANONICAL_SONNET_EFFORT,
    CANONICAL_SONNET_MODEL,
    CANONICAL_SONNET_PROFILE,
    ClaudeExternalError,
    build_claude_argv,
    build_claude_exec_argv,
    classify_explicit_quota,
    classify_quota_evidence,
    load_sonnet_profile,
    parse_claude_events,
    scrub_leaf_environment,
)
from apgr_workers.model_observation import claude_session
from apgr_workers.supervisor import build_leaf_prompt


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


def test_sonnet_profile_exact_provenance():
    profile = load_sonnet_profile(ROOT)
    assert profile.name == CANONICAL_SONNET_PROFILE
    assert profile.model == CANONICAL_SONNET_MODEL
    assert profile.effort == CANONICAL_SONNET_EFFORT
    assert profile.source_sha256
    assert profile.projection_matches_selected is True

    evidence = profile.evidence()
    assert evidence["profile"] == "sonnet-worker"
    assert evidence["model"] == "claude-sonnet-5-5"
    assert evidence["effort"] == "high"
    assert "source" in evidence
    assert "source_sha256" in evidence


def test_sonnet_profile_rejection_of_non_canonical():
    with pytest.raises(ClaudeExternalError, match="requires profile 'sonnet-worker'"):
        load_sonnet_profile(ROOT, profile="other-worker")

    with pytest.raises(ClaudeExternalError):
        load_sonnet_profile(ROOT, profile="../unsafe")


def test_build_claude_argv_readonly(tmp_path):
    profile = load_sonnet_profile(ROOT)
    argv = build_claude_argv(profile, tmp_path, "read_only")

    assert argv[0] == "claude"
    assert "--print" in argv
    assert "--output-format" in argv
    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert "--model" in argv
    assert argv[argv.index("--model") + 1] == "claude-sonnet-5-5"
    assert "--effort" in argv
    assert argv[argv.index("--effort") + 1] == "high"
    assert "--restricted" in argv
    assert "--setting-sources" in argv
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert "--mcp-config" in argv
    assert argv[argv.index("--mcp-config") + 1] == '{"mcpServers":{}}'
    assert "--strict-mcp-config" in argv
    assert "--disallowed-tools" in argv
    assert argv[argv.index("--disallowed-tools") + 1] == "Agent,Task"
    assert "--no-chrome" in argv
    assert "--disable-slash-commands" in argv

    # Read-only specific flags
    assert "--permission-mode" in argv
    assert argv[argv.index("--permission-mode") + 1] == "plan"
    assert "--tools" in argv
    tools = argv[argv.index("--tools") + 1].split(",")
    assert set(tools) == {"Read", "Glob", "Grep"}
    assert "Write" not in tools
    assert "Edit" not in tools
    assert "Agent" not in tools
    assert "Task" not in tools


def test_build_claude_argv_mutation_capable(tmp_path):
    profile = load_sonnet_profile(ROOT)
    argv = build_claude_argv(profile, tmp_path, "mutation_capable", mutation_scope=["src/test.py"])

    assert "--permission-mode" in argv
    assert argv[argv.index("--permission-mode") + 1] == "acceptEdits"
    assert "--tools" in argv
    tools = argv[argv.index("--tools") + 1].split(",")
    assert set(tools) == {"Read", "Glob", "Grep", "Write", "Edit"}
    assert "Agent" not in tools
    assert "Task" not in tools

    # Alias check
    alias_argv = build_claude_exec_argv(profile, tmp_path, "mutation_capable", mutation_scope=["src/test.py"])
    assert alias_argv == argv


def test_build_claude_argv_rejections(tmp_path):
    profile = load_sonnet_profile(ROOT)
    # Mutation capable without mutation scope
    with pytest.raises(ClaudeExternalError, match="require an explicit mutation_scope"):
        build_claude_argv(profile, tmp_path, "mutation_capable", mutation_scope=None)

    with pytest.raises(ClaudeExternalError, match="require an explicit mutation_scope"):
        build_claude_argv(profile, tmp_path, "mutation_capable", mutation_scope=[])

    # Invalid task authority
    with pytest.raises(ClaudeExternalError, match="task authority must be"):
        build_claude_argv(profile, tmp_path, "invalid_authority")


def test_scrub_leaf_environment_auth_preservation():
    env = {
        "APGR_PARENT_ID": "parent-123",
        "APGR_WORKER_PARENT_TOKEN": "secret-tok",
        "APGR_WORKER_STATE_DIR": "/tmp/state",
        "APGR_WORKER_FACADE": "1",
        "APGR_WORKER_SOURCE_ROOT": "/tmp/src",
        "APGR_WORKER_WORKSPACE": "/tmp/ws",
        "APGR_WORKER_PARENT_FAMILY": "gemini_flash",
        "APGR_WORKER_TASK_AUTHORITY": "read_only",
        "APGR_WORKER_LIFECYCLE_GENERATION": "gen-1",
        "APGR_WORKER_PROFILE": "sonnet-worker",
        "CODEX_THREAD_ID": "th-1",
        "CODEX_SESSION_ID": "sess-1",
        "CLAUDE_CODE_SESSION_ID": "claude-sess-1",
        "AGENT_CENTRAL_TASK": "do-something",
        # Provider auth to preserve:
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "CLAUDE_CONFIG_DIR": "/custom/claude",
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/user",
    }
    scrubbed = scrub_leaf_environment(env)
    assert scrubbed["APGR_WORKER_LEAF"] == "1"
    assert "APGR_PARENT_ID" not in scrubbed
    assert "APGR_WORKER_FACADE" not in scrubbed
    assert "CODEX_THREAD_ID" not in scrubbed
    assert "CLAUDE_CODE_SESSION_ID" not in scrubbed
    assert "AGENT_CENTRAL_TASK" not in scrubbed
    # Preserved auth and path:
    assert scrubbed["ANTHROPIC_API_KEY"] == "sk-ant-test"
    assert scrubbed["CLAUDE_CONFIG_DIR"] == "/custom/claude"
    assert scrubbed["PATH"] == "/usr/bin:/bin"


def test_parse_claude_events_stream():
    events_raw = "\n".join([
        json.dumps({"type": "system", "session_id": "00000000-0000-0000-0000-000000000001", "model": "claude-sonnet-5-5", "effort": "high"}),
        json.dumps({"type": "content_block_delta", "delta": {"text": "Hello "}}),
        json.dumps({"type": "content_block_delta", "delta": {"text": "World"}}),
        json.dumps({"type": "result", "result": "Hello World"}),
    ])
    parsed = parse_claude_events(events_raw)
    assert parsed["response"] == "Hello World"
    assert parsed["terminal_result"] and not parsed["provider_error"]
    assert parsed["effective_model"] == "claude-sonnet-5-5"
    assert parsed["effective_effort"] == "high"
    assert parsed["quota"]["exhausted"] is False
    assert parsed["provider_identifiers"]["session_id"] == "00000000-0000-0000-0000-000000000001"


def test_parse_claude_events_honest_observation_no_consensus():
    # If events report multiple conflicting models, effective_model must be None
    events_raw = "\n".join([
        json.dumps({"type": "system", "model": "claude-sonnet-5-5", "effort": "high"}),
        json.dumps({"type": "model_info", "model": "claude-haiku", "effort": "low"}),
        json.dumps({"type": "result", "result": "done"}),
    ])
    parsed = parse_claude_events(events_raw)
    assert parsed["effective_model"] is None
    assert parsed["effective_effort"] is None
    assert "claude-sonnet-5-5" in parsed["observed_models"]
    assert "claude-haiku" in parsed["observed_models"]


def test_classify_quota_evidence_explicit_and_transient():
    # Explicit exhaustion in event
    quota_raw = json.dumps({
        "type": "error",
        "error": {"message": "You've hit your usage limit. Check your plan.", "code": "insufficient_quota"}
    })
    evidence = classify_quota_evidence(quota_raw)
    assert evidence["exhausted"] is True
    assert evidence["classification"] == "explicit_quota_exhaustion"
    assert evidence["confidence"] in ("explicit_provider", "explicit_provider_code")

    # Transient error should NOT be classified as quota exhaustion
    transient_raw = json.dumps({
        "type": "error",
        "error": {"message": "rate limit exceeded, retry after 10 seconds", "retry_after": 10}
    })
    evidence = classify_quota_evidence(transient_raw)
    assert evidence["exhausted"] is False
    assert evidence["classification"] is None

    # Failed stderr fallback
    stderr_quota = b"claude code: You've hit your usage limit.\n"
    evidence_stderr = classify_quota_evidence("", stderr=stderr_quota, exit_code=1)
    assert evidence_stderr["exhausted"] is True
    assert evidence_stderr["source"] == "failed_stderr"

    # Compatibility helper
    assert classify_explicit_quota(quota_raw) == "explicit_quota_exhaustion"
    assert classify_explicit_quota(transient_raw) is None


def test_claude_session_discovery(tmp_path):
    home = tmp_path / "claude_home"
    session_id = "11111111-2222-3333-4444-555555555555"
    project_dir = home / "projects" / "my_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    session_file = project_dir / f"{session_id}.jsonl"

    session_content = "\n".join([
        json.dumps({
            "type": "assistant",
            "sessionId": session_id,
            "message": {"model": "claude-sonnet-5-5"},
            "effort": "high"
        }),
    ]) + "\n"
    session_file.write_text(session_content, encoding="utf-8")

    obs = claude_session(session_id, home=home)
    assert obs["effective_model"] == "claude-sonnet-5-5"
    assert obs["effective_effort"] == "high"
    assert obs["limitation"] is None

    # Fallback to home/sessions
    session_id_2 = "22222222-3333-4444-5555-666666666666"
    sessions_dir = home / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file_2 = sessions_dir / f"{session_id_2}.jsonl"
    session_content_2 = "\n".join([
        json.dumps({
            "type": "assistant",
            "sessionId": session_id_2,
            "message": {"model": "claude-sonnet-5-5"},
            "perTurnEffort": "high"
        }),
    ]) + "\n"
    session_file_2.write_text(session_content_2, encoding="utf-8")

    obs2 = claude_session(session_id_2, home=home)
    assert obs2["effective_model"] == "claude-sonnet-5-5"
    assert obs2["effective_effort"] == "high"

    # Invalid session UUID
    assert claude_session("not-a-uuid", home=home)["limitation"] == "invalid_session_id"


def test_build_leaf_prompt_label():
    prompt_sonnet = build_leaf_prompt("task instructions", "read_only", worker_kind="sonnet")
    assert "# Claude Sonnet Worker Leaf Job" in prompt_sonnet
    assert "You are an isolated Claude Sonnet leaf worker" in prompt_sonnet
    assert "READ-ONLY RESTRICTION" in prompt_sonnet

    prompt_luna = build_leaf_prompt("task instructions", "read_only", worker_kind="luna")
    assert "# Codex Luna Worker Leaf Job" in prompt_luna

    prompt_gemini = build_leaf_prompt("task instructions", "read_only", worker_kind="gemini")
    assert "# Gemini Worker Leaf Job" in prompt_gemini



def test_assistant_tool_input_is_not_provider_model_evidence():
    events = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "input": {"model": "claude-sonnet-5-5", "effort": "high"}}]}},
        {"type": "result", "result": "done"},
    ]
    parsed = parse_claude_events("\n".join(map(json.dumps, events)))
    assert parsed["effective_model"] is None
    assert parsed["effective_effort"] is None
    assert parsed["response"] == "done"
