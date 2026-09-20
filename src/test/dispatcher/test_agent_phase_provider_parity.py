"""Qualification tests for provider conformance, adapter parity, and operational contracts."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

from agent_phase.provider import (
    DEFAULT_ADVISORY_INTERVAL_SECONDS,
    DEFAULT_ADVISORY_SILENCE_SECONDS,
    DEFAULT_OUTER_CEILING_SECONDS,
    LivenessPolicy,
    build_argv,
)
from agent_phase.routing import (
    Endpoint,
    PROVIDER_ANTIGRAVITY,
    PROVIDER_CLAUDE,
    PROVIDER_CODEX,
)


def test_conformance_matrix_json_and_truthful_claims() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    matrix_path = repo_root / "docs" / "architecture" / "provider-conformance-matrix.json"
    assert matrix_path.exists(), f"Missing {matrix_path}"

    with open(matrix_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("schema") == "apgr-provider-conformance-matrix-v1"
    assert data.get("providers") == ["codex", "claude", "antigravity"]
    rows = data.get("rows", [])
    assert len(rows) == 22, f"Expected 22 conformance rows, got {len(rows)}"

    row_map = {r["id"]: r for r in rows}
    assert len(row_map) == 22

    # Verify key truthful claims per ADR 0064 and ADR 0065
    # 1. Structured output CLI flag is false across all providers (uses nonce decoding)
    struct_out = row_map["adapter_structured_output"]["support"]
    assert struct_out["codex"]["supported"] is False
    assert struct_out["claude"]["supported"] is False
    assert struct_out["antigravity"]["supported"] is False

    # 2. Tokenless auth & quota probes are false across all providers (truthfully unknown)
    auth_probe = row_map["tokenless_auth_probe"]["support"]
    assert auth_probe["codex"]["supported"] is False
    assert auth_probe["claude"]["supported"] is False
    assert auth_probe["antigravity"]["supported"] is False

    quota_probe = row_map["tokenless_quota_probe"]["support"]
    assert quota_probe["codex"]["supported"] is False
    assert quota_probe["claude"]["supported"] is False
    assert quota_probe["antigravity"]["supported"] is False

    # 3. Activity pipe is unique to Antigravity
    act_pipe = row_map["activity_pipe_telemetry"]["support"]
    assert act_pipe["antigravity"]["supported"] is True
    assert act_pipe["codex"]["supported"] is False
    assert act_pipe["claude"]["supported"] is False

    # 4. Reviewer role qualification: all three first-class providers are qualified
    rev_qual = row_map["reviewer_role_qualification"]["support"]
    assert rev_qual["claude"]["supported"] is True
    assert rev_qual["antigravity"]["supported"] is True
    assert rev_qual["codex"]["supported"] is True

    # 5. Cross-check with capabilities.toml
    cap_path = repo_root / "common" / "dispatcher" / "capabilities.toml"
    with open(cap_path, "rb") as cf:
        cap_data = tomllib.load(cf)
    endpoints = cap_data.get("endpoints", {})
    codex_reviewers = [ep for ep in endpoints.values() if ep.get("provider") == "codex" and ep.get("posture") == "read_only"]
    assert len(codex_reviewers) >= 1, "Codex must have at least one read_only reviewer endpoint in capabilities.toml"


def test_antigravity_reviewer_endpoint_registration() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    endpoints_path = repo_root / "common" / "dispatcher" / "endpoints.toml"
    capabilities_path = repo_root / "common" / "dispatcher" / "capabilities.toml"

    with open(endpoints_path, "rb") as f:
        endpoints_data = tomllib.load(f)
    with open(capabilities_path, "rb") as f:
        capabilities_data = tomllib.load(f)

    assert endpoints_data.get("generation") == 7
    ep_entry = endpoints_data.get("endpoints", {}).get("antigravity-claude-opus-review")
    assert ep_entry is not None, "antigravity-claude-opus-review missing from endpoints.toml"
    assert ep_entry.get("provider") == "antigravity"
    assert ep_entry.get("profile") == "claude-opus-4-6-thinking-review"

    cap_entry = capabilities_data.get("endpoints", {}).get("antigravity-claude-opus-review")
    assert cap_entry is not None, "antigravity-claude-opus-review missing from capabilities.toml"
    assert cap_entry.get("posture") == "read_only"
    assert "read" in cap_entry.get("capabilities", [])
    assert "reasoning" in cap_entry.get("capabilities", [])


def test_provider_read_only_posture_argv(tmp_path: Path) -> None:
    # 1. Claude
    ep_claude = Endpoint(PROVIDER_CLAUDE, "test-profile")
    argv_claude = build_argv(ep_claude, "reviewer", tmp_path, claude_launcher="/bin/claude")
    assert "--read-only" in argv_claude

    argv_claude_mut = build_argv(ep_claude, "producer", tmp_path, claude_launcher="/bin/claude", read_only=False)
    assert "--read-only" not in argv_claude_mut

    # 2. Codex
    ep_codex = Endpoint(PROVIDER_CODEX, "test-profile")
    argv_codex = build_argv(ep_codex, "reviewer", tmp_path, codex_executable="/bin/codex", pin_profile=False)
    assert "-s" in argv_codex
    assert argv_codex[argv_codex.index("-s") + 1] == "read-only"

    argv_codex_mut = build_argv(ep_codex, "producer", tmp_path, codex_executable="/bin/codex", pin_profile=False, read_only=False)
    assert "-s" not in argv_codex_mut

    # 3. Antigravity
    ep_antigravity = Endpoint(PROVIDER_ANTIGRAVITY, "test-profile")
    argv_antigravity = build_argv(ep_antigravity, "reviewer", tmp_path, antigravity_launcher="/bin/antigravity")
    assert "--reviewer" in argv_antigravity

    argv_antigravity_mut = build_argv(ep_antigravity, "producer", tmp_path, antigravity_launcher="/bin/antigravity", read_only=False)
    assert "--reviewer" not in argv_antigravity_mut


def test_liveness_policy_defaults() -> None:
    assert DEFAULT_OUTER_CEILING_SECONDS == 90_000.0
    assert DEFAULT_ADVISORY_SILENCE_SECONDS == 900.0
    assert DEFAULT_ADVISORY_INTERVAL_SECONDS == 900.0

    policy = LivenessPolicy()
    assert policy.outer_ceiling == 90_000.0
    assert policy.advisory_silence_seconds == 900.0
    assert policy.advisory_interval_seconds == 900.0
    assert policy.inactivity is None  # Production never terminates on quiet background commands
