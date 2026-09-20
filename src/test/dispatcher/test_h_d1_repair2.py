"""Focused APG166T-REPAIR2 evaluator and contract verification.

Tests independently exercise real production helpers and call sites:
- d1_auth: builtin plugin provenance and agent inventory subsets.
- d1_response: response extraction supporting bare JSON and one fenced JSON
  block in final type=result only; duplicate keys rejected; no earlier assistant
  fallback.
- d1_qualification: observed surface diagnostics (startup_inventory,
  terminal_subagent_stats) and subagent/nested envelope detection.
- d1_failure: comprehensive failure_reasons aggregation with required oracle
  and preservation flags.
- Real run_live_d1 fake production transport and readback with sanitized
  LIVE2-like synthetic streams (labeled test fixtures; zero external providers
  or private input dependencies).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from testing.h_eval import (
    d1_auth,
    d1_failure,
    d1_qualification as d1,
    d1_response,
    importers,
)

from test_h_d1_repair1 import installed

ROOT = Path(__file__).resolve().parents[3]

# SANITIZED TEST FIXTURE: Generated synthetic provider event stream modeling LIVE2
# execution without private custody, tokens, or external network dependencies.
SANITIZED_FIXTURE_PATH = "/sanitized/probe/d1_probe_target.txt"
SANITIZED_FIXTURE_BYTES = (
    b"D1-PROBE-NONCE: 8f4e2b1c6a0d3e5f7b9a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f\n"
    b"Sanitized test fixture content for unit evaluation.\n"
)
SANITIZED_NONCE = "8f4e2b1c6a0d3e5f7b9a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f"


def _jsonl(*events: dict[str, Any]) -> bytes:
    """Format events as UTF-8 encoded JSON Lines."""
    return b"".join(json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n" for event in events)


def _sanitized_live2_stream(
    *,
    probe_path: str = SANITIZED_FIXTURE_PATH,
    probe_content: bytes = SANITIZED_FIXTURE_BYTES,
    nonce: str = SANITIZED_NONCE,
    agents: list[str] | None = None,
    plugins: list[dict[str, str]] | None = None,
    tools: list[str] | None = None,
    mcp_servers: list[dict[str, Any]] | None = None,
    model: str = "claude-opus-5",
    permission_mode: str = "plan",
    cli_version: str = d1.D1_CLAUDE_CLI_VERSION,
    subagent_stats: dict[str, Any] | None = None,
    parent_tool_use_id: str | None = None,
    response_mode: str = "fenced",
    multiple_terminals: bool = False,
) -> bytes:
    """Generate a sanitized synthetic stream modeling the LIVE2 sequence."""
    if agents is None:
        agents = ["claude", "Explore", "general-purpose", "Plan"]
    if plugins is None:
        plugins = [
            {"name": "agents-md", "path": "builtin", "source": "agents-md@builtin"},
            {"name": "telemetry", "path": "builtin", "source": "telemetry@builtin"},
        ]
    if tools is None:
        tools = ["Read"]
    if mcp_servers is None:
        mcp_servers = []
    if subagent_stats is None:
        subagent_stats = {"spawned": 0, "max_depth": 0}

    init_event = {
        "type": "system",
        "subtype": "init",
        "session_id": "sanitized-live2-session",
        "tools": tools,
        "mcp_servers": mcp_servers,
        "model": model,
        "permissionMode": permission_mode,
        "claude_code_version": cli_version,
        "agents": agents,
        "skills": [],
        "plugins": plugins,
    }

    content_str = probe_content.decode("utf-8", "replace")
    assistant_read = {
        "type": "assistant",
        "session_id": "sanitized-live2-session",
        "parent_tool_use_id": parent_tool_use_id,
        "message": {
            "model": model,
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_sanitized_read_01",
                    "name": "Read",
                    "input": {"file_path": probe_path},
                    "caller": {"type": "direct"},
                }
            ],
        },
    }

    user_read_result = {
        "type": "user",
        "session_id": "sanitized-live2-session",
        "parent_tool_use_id": parent_tool_use_id,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_sanitized_read_01",
                    "content": f"1\t{content_str}",
                }
            ],
        },
        "tool_use_result": {
            "type": "text",
            "file": {
                "filePath": probe_path,
                "content": content_str,
                "numLines": len(probe_content.splitlines()),
                "startLine": 1,
                "totalLines": len(probe_content.splitlines()),
            },
        },
    }

    fenced_response = (
        "Read completed via native Read tool.\n\n```json\n"
        + json.dumps({
            "schema": "apg.d1-response/v1",
            "probe_id": "APG166D-PROBE-D1",
            "nonce": nonce,
            "summary": "Verified native Read of probe fixture file.",
        })
        + "\n```\n\nDetails: probe verified successfully."
    )
    bare_response = json.dumps({
        "schema": "apg.d1-response/v1",
        "probe_id": "APG166D-PROBE-D1",
        "nonce": nonce,
        "summary": "Verified native Read of probe fixture file.",
    })

    if response_mode == "fenced":
        result_text = fenced_response
    elif response_mode == "bare":
        result_text = bare_response
    else:
        raise ValueError("unsupported synthetic response mode")

    events = [init_event, assistant_read, user_read_result]

    terminal_event = {
        "type": "result",
        "subtype": "success",
        "session_id": "sanitized-live2-session",
        "is_error": False,
        "subagent_stats": subagent_stats,
        "result": result_text,
    }
    events.append(terminal_event)

    if multiple_terminals:
        events.append({
            "type": "result",
            "subtype": "success",
            "session_id": "sanitized-live2-session",
            "is_error": False,
            "subagent_stats": subagent_stats,
            "result": result_text,
        })

    return _jsonl(*events)


# -----------------------------------------------------------------------------
# Part 1: Real run_live_d1 fake production transport and readback tests
# -----------------------------------------------------------------------------

def test_live2_fake_production_transport_qualified_with_builtin_plugins_and_fenced_response(installed):
    """LIVE2-like execution with 4 builtin agents, 2 builtin plugins, and fenced JSON qualifies."""
    _, _, configure = installed

    def transform_live2(script: str) -> str:
        s = script.replace(
            '"tools": tools, "mcp_servers": mcps',
            '"tools": tools, "mcp_servers": mcps, '
            '"agents": ["claude", "Explore", "general-purpose", "Plan"], "skills": [], '
            '"plugins": [{"name": "agents-md", "path": "builtin", "source": "agents-md@builtin"}, '
            '{"name": "telemetry", "path": "builtin", "source": "telemetry@builtin"}]',
        )
        return s.replace(
            '"result": json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", "nonce": ans_nonce, "summary": "Read ok"})',
            '"subagent_stats": {"spawned": 0, "max_depth": 0}, '
            '"result": "Read completed via native Read tool.\\n\\n```json\\n" + '
            'json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", '
            '"nonce": ans_nonce, "summary": "Verified native Read of probe fixture file."}) + '
            '"\\n```\\n\\nDetails: native Read completed."',
        )

    evidence, authority = configure(transform=transform_live2)
    record = d1.run_live_d1(ROOT, evidence, authority)

    assert record["d1_status"] == "qualified"
    assert record["post_provider"]["failure_reasons"] == []
    assert record["post_provider"]["oracle"]["status"] == "pass"

    surface = record["surface_contract"]
    assert surface["valid"] is True
    assert surface["startup_inventory"]["agents"] == ["claude", "Explore", "general-purpose", "Plan"]
    assert surface["startup_inventory"]["skills"] == []
    assert len(surface["startup_inventory"]["plugins"]) == 2
    assert surface["terminal_subagent_stats"] == [{"spawned": 0, "max_depth": 0}]

    readback = d1.readback_d1_record(evidence, ROOT)
    assert readback["d1_status"] == "qualified"


def test_live2_fake_production_transport_bare_json_response_qualified(installed):
    """Bare JSON in final type=result is supported and qualifies under REPAIR2."""
    _, _, configure = installed

    def transform_bare(script: str) -> str:
        s = script.replace(
            '"tools": tools, "mcp_servers": mcps',
            '"tools": tools, "mcp_servers": mcps, '
            '"agents": ["claude", "Explore", "general-purpose", "Plan"], "skills": [], '
            '"plugins": [{"name": "agents-md", "path": "builtin", "source": "agents-md@builtin"}]',
        )
        return s.replace(
            '"result": json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", "nonce": ans_nonce, "summary": "Read ok"})',
            '"subagent_stats": {"spawned": 0, "max_depth": 0}, '
            '"result": json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", '
            '"nonce": ans_nonce, "summary": "Verified native Read of probe fixture file."})',
        )

    evidence, authority = configure(transform=transform_bare)
    record = d1.run_live_d1(ROOT, evidence, authority)

    assert record["d1_status"] == "qualified"
    assert record["post_provider"]["failure_reasons"] == []
    assert record["post_provider"]["oracle"]["status"] == "pass"
    readback = d1.readback_d1_record(evidence, ROOT)
    assert readback["d1_status"] == "qualified"


def test_live2_fake_production_transport_combined_surface_and_oracle_fail(installed):
    """Combined surface failure (custom agent + invalid plugin) and oracle failure (nonce mismatch)."""
    _, _, configure = installed

    def transform_combined(script: str) -> str:
        s = script.replace(
            '"tools": tools, "mcp_servers": mcps',
            '"tools": tools, "mcp_servers": mcps, '
            '"agents": ["claude", "custom-unauthorized-agent"], "skills": [], '
            '"plugins": [{"name": "unauthorized", "path": "/opt/custom", "source": "custom"}]',
        )
        return s.replace(
            '"result": json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", "nonce": ans_nonce, "summary": "Read ok"})',
            '"subagent_stats": {"spawned": 0, "max_depth": 0}, '
            '"result": "```json\\n" + '
            'json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", '
            '"nonce": "0000000000000000000000000000000000000000000000000000000000000000", '
            '"summary": "Wrong nonce"}) + "\\n```"',
        )

    evidence, authority = configure(transform=transform_combined)
    record = d1.run_live_d1(ROOT, evidence, authority)

    assert record["d1_status"] == "failed"
    failures = record["post_provider"]["failure_reasons"]
    assert "PLUGINS_NOT_BUILTIN" in failures
    assert "AGENTS_MISMATCH" in failures
    assert "ORACLE_FAILED:nonce mismatch" in failures

    # Readback confirms the failed record with all failure diagnostics
    readback = d1.readback_d1_record(evidence, ROOT, allow_failed=True)
    assert readback["d1_status"] == "failed"
    assert readback["post_provider"]["failure_reasons"] == failures
    with pytest.raises(d1.D1ReadbackError):
        d1.readback_d1_record(evidence, ROOT)
    # Removing only the oracle explanation must fail recomputation, even with
    # the surface failures still retained and the record digest rebound.
    record["post_provider"]["failure_reasons"].remove("ORACLE_FAILED:nonce mismatch")
    record["record_digest"] = d1.compute_record_digest(record)
    path = evidence / "d1-record.json"
    path.chmod(0o600)
    path.write_text(json.dumps(record))
    with pytest.raises(d1.D1ReadbackError, match="provider failure disposition mismatch"):
        d1.readback_d1_record(evidence, ROOT, allow_failed=True)


def test_live2_fake_production_transport_subagents_observed_fails(installed):
    """Subagent stats with spawned > 0 fails surface inspection with SUBAGENTS_OBSERVED."""
    _, _, configure = installed

    def transform_subagents(script: str) -> str:
        s = script.replace(
            '"tools": tools, "mcp_servers": mcps',
            '"tools": tools, "mcp_servers": mcps, '
            '"agents": ["claude", "Explore", "general-purpose", "Plan"], "skills": [], "plugins": []',
        )
        return s.replace(
            '"result": json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", "nonce": ans_nonce, "summary": "Read ok"})',
            '"subagent_stats": {"spawned": 2, "max_depth": 1}, '
            '"result": json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", '
            '"nonce": ans_nonce, "summary": "Read ok"})',
        )

    evidence, authority = configure(transform=transform_subagents)
    record = d1.run_live_d1(ROOT, evidence, authority)

    assert record["d1_status"] == "failed"
    assert "SUBAGENTS_OBSERVED" in record["surface_contract"]["failure_codes"]
    assert "SUBAGENTS_OBSERVED" in record["post_provider"]["failure_reasons"]


def test_live2_fake_production_transport_nested_envelope_fails(installed):
    """Events with parent_tool_use_id set fail surface inspection with SUBAGENTS_OBSERVED."""
    _, _, configure = installed

    def transform_nested(script: str) -> str:
        s = script.replace(
            '"type": "assistant", "session_id": "d1-s"',
            '"type": "assistant", "session_id": "d1-s", "parent_tool_use_id": "toolu_nested_delegation_01"',
        )
        return s.replace(
            '"result": json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", "nonce": ans_nonce, "summary": "Read ok"})',
            '"subagent_stats": {"spawned": 0, "max_depth": 0}, '
            '"result": json.dumps({"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", '
            '"nonce": ans_nonce, "summary": "Read ok"})',
        )

    evidence, authority = configure(transform=transform_nested)
    record = d1.run_live_d1(ROOT, evidence, authority)

    assert record["d1_status"] == "failed"
    assert "SUBAGENTS_OBSERVED" in record["surface_contract"]["failure_codes"]
    assert "SUBAGENTS_OBSERVED" in record["post_provider"]["failure_reasons"]


def test_live2_fake_production_transport_no_native_read_fails(installed):
    """Skipping native Read produces NO_NATIVE_READ and ORACLE_FAILED:no_native_read_observed."""
    _, _, configure = installed
    evidence, authority = configure("no_read")
    record = d1.run_live_d1(ROOT, evidence, authority)

    assert record["d1_status"] == "failed"
    assert "NO_NATIVE_READ" in record["post_provider"]["failure_reasons"]
    assert "ORACLE_FAILED:no_native_read_observed" in record["post_provider"]["failure_reasons"]


# -----------------------------------------------------------------------------
# Part 2: Unit matrix - d1_auth builtin plugins and agents provenance
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "plugins,expected",
    [
        ([], True),
        ([{"name": "telemetry", "path": "builtin", "source": "telemetry@builtin"}], True),
        (
            [
                {"name": "agents-md", "path": "builtin", "source": "agents-md@builtin"},
                {"name": "telemetry", "path": "builtin", "source": "telemetry@builtin"},
            ],
            True,
        ),
        # Not a list
        (None, False),
        ({}, False),
        ("builtin", False),
        # Items not dicts
        (["telemetry"], False),
        ([123], False),
        # Missing keys
        ([{"name": "telemetry", "path": "builtin"}], False),
        ([{"path": "builtin", "source": "telemetry@builtin"}], False),
        # Extra keys
        ([{"name": "telemetry", "path": "builtin", "source": "telemetry@builtin", "version": "1.0"}], False),
        # Invalid path
        ([{"name": "telemetry", "path": "custom", "source": "telemetry@builtin"}], False),
        ([{"name": "telemetry", "path": "/usr/local/plugins", "source": "telemetry@builtin"}], False),
        # Invalid source
        ([{"name": "telemetry", "path": "builtin", "source": "telemetry@custom"}], False),
        ([{"name": "telemetry", "path": "builtin", "source": "other"}], False),
        # Invalid names
        ([{"name": "", "path": "builtin", "source": "@builtin"}], False),
        ([{"name": " telemetry ", "path": "builtin", "source": " telemetry @builtin"}], False),
        ([{"name": "a@b", "path": "builtin", "source": "a@b@builtin"}], False),
        ([{"name": "a/b", "path": "builtin", "source": "a/b@builtin"}], False),
        ([{"name": "a\\b", "path": "builtin", "source": "a\\b@builtin"}], False),
        ([{"name": "a\0b", "path": "builtin", "source": "a\0b@builtin"}], False),
        # Duplicate names
        (
            [
                {"name": "telemetry", "path": "builtin", "source": "telemetry@builtin"},
                {"name": "telemetry", "path": "builtin", "source": "telemetry@builtin"},
            ],
            False,
        ),
    ],
)
def test_builtin_plugins_provenance_matrix(plugins, expected):
    """_builtin_plugins strictly checks provenance keys, values, and uniqueness."""
    assert d1_auth._builtin_plugins(plugins) is expected


@pytest.mark.parametrize(
    "agents,expected_failure",
    [
        # Valid subsets of the five builtin agents
        (["claude", "Explore", "general-purpose", "Plan", "statusline-setup"], None),
        (["claude", "Explore", "general-purpose", "Plan"], None),  # Observed LIVE2 subset
        (["claude", "Plan"], None),
        (["claude"], None),
        ([], None),
        # Invalid: duplicates
        (["claude", "claude"], "AGENTS_MISMATCH"),
        (["claude", "Explore", "claude"], "AGENTS_MISMATCH"),
        # Invalid: unknown agent names
        (["claude", "custom-agent"], "AGENTS_MISMATCH"),
        (["unauthorized"], "AGENTS_MISMATCH"),
        # Invalid: non-list or non-string elements
        ("claude", "AGENTS_MISMATCH"),
        (["claude", 123], "AGENTS_MISMATCH"),
    ],
)
def test_agents_inventory_subset_matrix(agents, expected_failure):
    """surface_failures enforces that agents is a unique subset of BUILTIN_AGENTS."""
    init = {"agents": agents}
    failures = d1_auth.surface_failures(init, {})
    if expected_failure is None:
        assert "AGENTS_MISMATCH" not in failures
    else:
        assert expected_failure in failures


def test_surface_failures_skills_and_plugins():
    """Skills non-empty and non-builtin plugins are rejected by surface_failures."""
    assert d1_auth.surface_failures({"skills": ["my-skill"]}, {}) == ["SKILLS_NON_EMPTY"]
    assert d1_auth.surface_failures(
        {"plugins": [{"name": "bad", "path": "custom", "source": "bad"}]},
        {},
    ) == ["PLUGINS_NOT_BUILTIN"]


# -----------------------------------------------------------------------------
# Part 3: Unit matrix - d1_response response parsing
# -----------------------------------------------------------------------------

def test_response_from_text_bare_json():
    """response_from_text parses valid bare JSON and rejects invalid shapes."""
    val, err = d1_response.response_from_text('{"schema": "apg.d1-response/v1", "nonce": "abc"}')
    assert err is None
    assert val == {"schema": "apg.d1-response/v1", "nonce": "abc"}

    # Non-dict JSON values
    assert d1_response.response_from_text("[1, 2, 3]")[1] == "non-JSON response"
    assert d1_response.response_from_text('"hello"')[1] == "non-JSON response"
    assert d1_response.response_from_text("42")[1] == "non-JSON response"

    # Duplicate keys rejected
    assert d1_response.response_from_text('{"a": 1, "a": 2}')[1] == "duplicate JSON key"

    # Size limit
    huge = '{"a": "' + ("x" * (d1_response.MAX_D1_RESPONSE_CHARS + 1)) + '"}'
    assert d1_response.response_from_text(huge)[1] == "response too large"


def test_response_from_text_fenced_json():
    """response_from_text parses a single fenced JSON block surrounded by prose."""
    text = (
        "Here is the execution result:\n\n"
        "```json\n"
        '{\n  "schema": "apg.d1-response/v1",\n  "probe_id": "APG166D-PROBE-D1",\n  "nonce": "test-nonce"\n}\n'
        "```\n\n"
        "Details: Read succeeded."
    )
    val, err = d1_response.response_from_text(text)
    assert err is None
    assert val["schema"] == "apg.d1-response/v1"
    assert val["nonce"] == "test-nonce"

    # Multiple fenced blocks rejected as ambiguous
    multi = "```json\n{\"a\": 1}\n```\n```json\n{\"b\": 2}\n```"
    assert d1_response.response_from_text(multi)[1] == "ambiguous response: multiple fenced blocks"

    # Unterminated fence
    unterminated = "```json\n{\"a\": 1}\n"
    assert d1_response.response_from_text(unterminated)[1] == "unterminated response fence"

    # Non-json fence language
    wrong_lang = "```python\n{\"a\": 1}\n```"
    assert d1_response.response_from_text(wrong_lang)[1] == "non-JSON response"

    # Malformed JSON in fence
    malformed = "```json\n{invalid json}\n```"
    assert d1_response.response_from_text(malformed)[1] == "malformed fenced JSON"

    # Duplicate keys in fence
    dup = '```json\n{"k": 1, "k": 2}\n```'
    assert d1_response.response_from_text(dup)[1] == "duplicate JSON key"

    # Fenced non-dict
    non_dict = '```json\n["not", "dict"]\n```'
    assert d1_response.response_from_text(non_dict)[1] == "malformed fenced JSON"


def test_response_candidate_stream_handling():
    """response_candidate enforces stream boundaries and rejects assistant fallbacks."""
    # Successful stream with final type=result holding fenced JSON
    raw = _sanitized_live2_stream(response_mode="fenced")
    cand, err = d1_response.response_candidate(raw)
    assert err is None
    assert cand["nonce"] == SANITIZED_NONCE

    # Successful stream with bare JSON in result
    raw_bare = _sanitized_live2_stream(response_mode="bare")
    cand_bare, err_bare = d1_response.response_candidate(raw_bare)
    assert err_bare is None
    assert cand_bare["nonce"] == SANITIZED_NONCE

    # Standalone bare JSON bytes (not JSON Lines)
    standalone = json.dumps({"schema": "apg.d1-response/v1", "nonce": "abc"}).encode()
    cand_std, err_std = d1_response.response_candidate(standalone)
    assert err_std is None
    assert cand_std["nonce"] == "abc"

    # Earlier assistant fallback rejected: assistant had json, but terminal result has plain prose
    fallback_stream = _jsonl(
        {"type": "system", "subtype": "init"},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": '{"schema": "apg.d1-response/v1", "nonce": "early"}'}]}},
        {"type": "result", "subtype": "success", "result": "Operation completed without structured result."},
    )
    cand_fb, err_fb = d1_response.response_candidate(fallback_stream)
    assert cand_fb is None
    assert err_fb == "non-JSON response"

    # Multiple terminal candidates rejected
    multi_raw = _sanitized_live2_stream(multiple_terminals=True)
    cand_multi, err_multi = d1_response.response_candidate(multi_raw)
    assert cand_multi is None
    assert err_multi == "ambiguous response: multiple terminal candidates"

    # Terminal event is not the last event
    trailing_stream = _jsonl(
        {"type": "system", "subtype": "init"},
        {"type": "result", "subtype": "success", "result": '{"schema": "apg.d1-response/v1"}'},
        {"type": "system", "subtype": "metrics", "data": {}},
    )
    cand_trail, err_trail = d1_response.response_candidate(trailing_stream)
    assert cand_trail is None
    assert err_trail == "non-JSON response"

    # Malformed stream line
    malformed_stream = b'{"type": "system"}\nnot-json\n'
    cand_mal, err_mal = d1_response.response_candidate(malformed_stream)
    assert cand_mal is None
    assert err_mal == "malformed response stream"


def test_response_candidate_mapping_inputs():
    """response_candidate correctly handles in-memory mapping inputs."""
    # Explicit review_response
    cand, err = d1_response.response_candidate({"review_response": {"schema": "apg.d1-response/v1", "nonce": "n1"}})
    assert err is None and cand["nonce"] == "n1"

    # Explicit d1_response
    cand, err = d1_response.response_candidate({"d1_response": {"schema": "apg.d1-response/v1", "nonce": "n2"}})
    assert err is None and cand["nonce"] == "n2"

    # Result with nested value
    cand, err = d1_response.response_candidate({"result": {"value": '```json\n{"schema": "apg.d1-response/v1", "nonce": "n3"}\n```'}})
    assert err is None and cand["nonce"] == "n3"


# -----------------------------------------------------------------------------
# Part 4: Unit matrix - d1_qualification inspect and evaluate
# -----------------------------------------------------------------------------

def test_inspect_observed_surface_diagnostics_and_subagents():
    """inspect_observed_surface records inventory diagnostics and detects subagent delegation."""
    route = {"model": "claude-opus-5"}
    contract = {
        "profile": d1.ALLOWED_PROFILE,
        "roles": [d1.ALLOWED_ROLE],
        "binding_id": d1.ALLOWED_BINDING_ID,
        "permission_mode": d1.ALLOWED_PERMISSION_MODE,
        "argv": ["claude"],
        "roots": {"run_dir": "/tmp/run"},
        "settings_sources": {"home_settings": {"path": "/tmp/home/.claude/settings.json"}},
    }

    # Clean stream
    clean_stream = _sanitized_live2_stream()
    surface = d1.inspect_observed_surface(clean_stream, route, contract, expected_argv=["claude"])
    assert surface["valid"] is True
    assert surface["failure_codes"] == []
    assert surface["startup_inventory"]["agents"] == ["claude", "Explore", "general-purpose", "Plan"]
    assert surface["terminal_subagent_stats"] == [{"spawned": 0, "max_depth": 0}]

    # Subagents spawned > 0
    spawned_stream = _sanitized_live2_stream(subagent_stats={"spawned": 1, "max_depth": 0})
    surf_spawned = d1.inspect_observed_surface(spawned_stream, route, contract)
    assert "SUBAGENTS_OBSERVED" in surf_spawned["failure_codes"]

    # Subagents max_depth > 0
    depth_stream = _sanitized_live2_stream(subagent_stats={"spawned": 0, "max_depth": 2})
    surf_depth = d1.inspect_observed_surface(depth_stream, route, contract)
    assert "SUBAGENTS_OBSERVED" in surf_depth["failure_codes"]

    # Nested envelope (parent_tool_use_id present)
    nested_stream = _sanitized_live2_stream(parent_tool_use_id="toolu_parent_01")
    surf_nested = d1.inspect_observed_surface(nested_stream, route, contract)
    assert "SUBAGENTS_OBSERVED" in surf_nested["failure_codes"]

    # Malformed subagent stats
    invalid_stats_stream = _sanitized_live2_stream(subagent_stats={"spawned": -1, "max_depth": 0})
    surf_invalid = d1.inspect_observed_surface(invalid_stats_stream, route, contract)
    assert "SUBAGENT_STATS_INVALID" in surf_invalid["failure_codes"]

    # Forbidden tools observed
    bad_tools_stream = _sanitized_live2_stream(tools=["Read", "Bash"])
    surf_tools = d1.inspect_observed_surface(bad_tools_stream, route, contract)
    assert "FORBIDDEN_TOOLS_OBSERVED" in surf_tools["failure_codes"]

    # Required tools absent
    no_tools_stream = _sanitized_live2_stream(tools=[])
    surf_no_tools = d1.inspect_observed_surface(no_tools_stream, route, contract)
    assert "READ_TOOL_MISSING" in surf_no_tools["failure_codes"]

    # Non-empty MCP servers
    mcp_stream = _sanitized_live2_stream(mcp_servers=[{"name": "unauthorized-server"}])
    surf_mcp = d1.inspect_observed_surface(mcp_stream, route, contract)
    assert "MCP_SERVERS_NON_EMPTY" in surf_mcp["failure_codes"]


def test_evaluate_d1_response_oracle_checks():
    """evaluate_d1_response independently verifies observation, path, digest, and response."""
    read_obs = {
        "reads": [
            {
                "file_path": SANITIZED_FIXTURE_PATH,
                "sha256": hashlib.sha256(SANITIZED_FIXTURE_BYTES).hexdigest(),
                "content": SANITIZED_FIXTURE_BYTES.decode(),
            }
        ]
    }

    # Pass case
    valid_text = (
        "```json\n"
        + json.dumps({
            "schema": "apg.d1-response/v1",
            "probe_id": "APG166D-PROBE-D1",
            "nonce": SANITIZED_NONCE,
            "summary": "Read verified.",
        })
        + "\n```"
    )
    res = d1.evaluate_d1_response(
        valid_text,
        SANITIZED_NONCE,
        observation=read_obs,
        fixture_bytes=SANITIZED_FIXTURE_BYTES,
        fixture_path=Path(SANITIZED_FIXTURE_PATH),
    )
    assert res["status"] == "pass"
    assert res["observed_nonce"] == SANITIZED_NONCE

    # Missing observation
    assert d1.evaluate_d1_response(valid_text, SANITIZED_NONCE, observation=None)["reason"] == "native_read_observation_missing"

    # Empty reads
    assert d1.evaluate_d1_response(valid_text, SANITIZED_NONCE, observation={"reads": []})["reason"] == "no_native_read_observed"

    # Fixture path mismatch
    assert d1.evaluate_d1_response(
        valid_text,
        SANITIZED_NONCE,
        observation=read_obs,
        fixture_path=Path("/different/path.txt"),
    )["reason"] == "fixture_path_not_observed_in_reads"

    # Fixture bytes mismatch
    assert d1.evaluate_d1_response(
        valid_text,
        SANITIZED_NONCE,
        observation=read_obs,
        fixture_bytes=b"completely different fixture bytes",
    )["reason"] == "observed_content_digest_mismatch"

    # Schema mismatch
    schema_bad = '{"schema": "wrong.schema/v1", "probe_id": "APG166D-PROBE-D1", "nonce": "' + SANITIZED_NONCE + '"}'
    assert d1.evaluate_d1_response(schema_bad, SANITIZED_NONCE, observation=read_obs)["reason"] == "schema mismatch"

    # Probe ID mismatch
    probe_bad = '{"schema": "apg.d1-response/v1", "probe_id": "WRONG-PROBE", "nonce": "' + SANITIZED_NONCE + '"}'
    assert d1.evaluate_d1_response(probe_bad, SANITIZED_NONCE, observation=read_obs)["reason"] == "probe_id mismatch"

    # Nonce mismatch
    nonce_bad = '{"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", "nonce": "wrong-nonce"}'
    res_nonce = d1.evaluate_d1_response(nonce_bad, SANITIZED_NONCE, observation=read_obs)
    assert res_nonce["status"] == "fail"
    assert res_nonce["reason"] == "nonce mismatch"
    assert res_nonce["observed_nonce"] == "wrong-nonce"


# -----------------------------------------------------------------------------
# Part 5: Unit matrix - d1_failure.failure_reasons aggregation
# -----------------------------------------------------------------------------

def test_failure_reasons_full_aggregation():
    """failure_reasons aggregates provider, exit, surface, oracle, and drift reasons."""
    clean_imported = {"provider_outcome": "success"}
    clean_terminal = {"exit_code": 0}
    clean_capture = {"status": "complete"}
    clean_surface = {"valid": True, "failure_codes": []}
    clean_reads = [{"id": "read1"}]
    clean_oracle = {"status": "pass"}
    clean_native = {"schema": "apg.d1-native-launch-custody/v1"}

    # Clean pass -> empty reasons
    assert d1_failure.failure_reasons(
        clean_imported, clean_terminal, clean_capture, clean_surface, clean_reads,
        clean_oracle, native_launch=clean_native, git_preserved=True, settings_preserved=True,
    ) == []

    # Oracle failure included
    fail_oracle = {"status": "fail", "reason": "nonce mismatch"}
    assert d1_failure.failure_reasons(
        clean_imported, clean_terminal, clean_capture, clean_surface, clean_reads,
        fail_oracle, native_launch=clean_native, git_preserved=True, settings_preserved=True,
    ) == ["ORACLE_FAILED:nonce mismatch"]

    # Native launch custody missing
    assert d1_failure.failure_reasons(
        clean_imported, clean_terminal, clean_capture, clean_surface, clean_reads,
        clean_oracle, native_launch=None, git_preserved=True, settings_preserved=True,
    ) == ["NATIVE_LAUNCH_CUSTODY_MISSING"]

    # Git and settings drift
    assert d1_failure.failure_reasons(
        clean_imported, clean_terminal, clean_capture, clean_surface, clean_reads,
        clean_oracle, native_launch=clean_native, git_preserved=False, settings_preserved=False,
    ) == ["GIT_DRIFT", "SETTINGS_DRIFT"]

    # Provider error with auth failed
    auth_err_imp = {
        "provider_outcome": "error",
        "provider_error": {"assistant_errors": ["authentication_failed"]},
    }
    assert "PROVIDER_ERROR:authentication_failed" in d1_failure.failure_reasons(
        auth_err_imp, clean_terminal, clean_capture, clean_surface, clean_reads,
        clean_oracle, native_launch=clean_native, git_preserved=True, settings_preserved=True,
    )

    # Combined multiple failure reasons deterministically ordered
    bad_surface = {"valid": False, "failure_codes": ["AGENTS_MISMATCH", "PLUGINS_NOT_BUILTIN"]}
    combined_failures = d1_failure.failure_reasons(
        {"provider_outcome": "error"},
        {"exit_code": 1},
        {"status": "incomplete"},
        bad_surface,
        [],
        {"status": "fail", "reason": "non-JSON response"},
        native_launch=None,
        git_preserved=False,
        settings_preserved=False,
    )
    expected_order = [
        "PROVIDER_ERROR",
        "NONZERO_EXIT:1",
        "AGENTS_MISMATCH",
        "PLUGINS_NOT_BUILTIN",
        "NO_NATIVE_READ",
        "CAPTURE_INCOMPLETE",
        "ORACLE_FAILED:non-JSON response",
        "NATIVE_LAUNCH_CUSTODY_MISSING",
        "GIT_DRIFT",
        "SETTINGS_DRIFT",
    ]
    assert combined_failures == expected_order


# -----------------------------------------------------------------------------
# Part 6: Generic importer regression stability
# -----------------------------------------------------------------------------

def test_generic_claude_importer_unchanged():
    """Generic Work Review importer parses Claude CLI streams without schema drift."""
    route = {"provider": "claude", "execution": "live"}
    raw = _sanitized_live2_stream(response_mode="fenced")
    imported = importers.import_claude(raw, route, terminal={"exit_code": 0})

    assert imported["provider_outcome"] == "success"
    assert imported["provider_terminal_status"] == "success"
    assert imported["provider_error"] == {
        "api_error_status": None,
        "assistant_errors": [],
        "is_error": False,
        "terminal_reason": None,
    }

    assert imported["review_response"] is None
    assert imported["review_response_status"] == "malformed"


@pytest.mark.parametrize("field,reason", [
    ("schema", "schema mismatch"), ("probe_id", "probe_id mismatch"), ("nonce", "nonce mismatch"),
])
def test_fenced_final_still_requires_exact_response_fields(field, reason):
    events = [json.loads(line) for line in _sanitized_live2_stream().splitlines()]
    value = {"schema": d1.RESPONSE_SCHEMA, "probe_id": d1.PROBE_ID, "nonce": SANITIZED_NONCE}
    value[field] = "wrong"
    events[-1]["result"] = "Prose\n```json\n" + json.dumps(value) + "\n```\nEnd."
    result = d1.evaluate_d1_response(_jsonl(*events), SANITIZED_NONCE, observation={"reads": [{}]})
    assert result["reason"] == reason


@pytest.mark.parametrize("conflicting", [False, True])
def test_two_complete_fenced_responses_are_ambiguous(conflicting):
    payload = {"schema": d1.RESPONSE_SCHEMA, "probe_id": d1.PROBE_ID, "nonce": SANITIZED_NONCE}
    first = "```json\n" + json.dumps(payload) + "\n```"
    if conflicting:
        payload["nonce"] = "wrong"
    second = "```json\n" + json.dumps(payload) + "\n```"
    result = d1.evaluate_d1_response(first + "\n" + second, SANITIZED_NONCE, observation={"reads": [{}]})
    assert result["reason"] == "ambiguous response: multiple fenced blocks"


def test_stream_envelope_duplicates_and_unrelated_result_keys():
    duplicate = b'{"type":"result","result":"{}","result":"{}"}\n'
    assert d1_response.response_candidate(duplicate) == (None, "duplicate JSON key")
    raw = _sanitized_live2_stream()
    # An unrelated event's result key is not a terminal response candidate.
    raw = _jsonl({"type": "system", "result": "diagnostic"}) + raw
    assert d1_response.response_candidate(raw)[1] is None
    assert d1_response.response_candidate(raw[:-8])[1] == "malformed response stream"


def test_read_only_advertisement_does_not_hide_actual_other_tool_call():
    events = [json.loads(line) for line in _sanitized_live2_stream().splitlines()]
    events.insert(-1, {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "synthetic-agent", "name": "Agent", "input": {}}
    ]}})
    surface = d1.inspect_observed_surface(_jsonl(*events), {"model": "claude-opus-5"})
    assert surface["tools"] == ["Read"]
    assert surface["failure_codes"] == ["FORBIDDEN_TOOL_CALL_OBSERVED"]


@pytest.mark.parametrize("scenario,code", [
    ("extra_tool", "FORBIDDEN_TOOLS_OBSERVED"), ("no_read_tool", "READ_TOOL_MISSING"),
    ("non_empty_mcp", "MCP_SERVERS_NON_EMPTY"), ("permission_mismatch", "PERMISSION_MODE_MISMATCH"),
])
def test_builtin_inventory_does_not_hide_other_contract_failures(installed, scenario, code):
    _, _, configure = installed
    def builtins(script):
        marker = '"tools": tools, "mcp_servers": mcps'
        assert script.count(marker) == 2
        return script.replace(marker, marker + ', "agents": ["claude", "Explore", "general-purpose", "Plan"], '
            '"plugins": [{"name": "agents-md", "path": "builtin", "source": "agents-md@builtin"}]')
    evidence, authority = configure(scenario, transform=builtins)
    record = d1.run_live_d1(ROOT, evidence, authority)
    assert record["d1_status"] == "failed"
    assert code in record["post_provider"]["failure_reasons"]
    if scenario == "non_empty_mcp":
        readback = d1.readback_d1_record(evidence, ROOT, allow_failed=True)
        assert readback["post_provider"]["failure_reasons"] == record["post_provider"]["failure_reasons"]
    else:
        # Existing observer qualification refuses tool/permission drift during
        # execution; readback reconstructs Reads and reports the count mismatch.
        # This nearby failed-inspection limitation is outside REPAIR2.
        with pytest.raises(d1.D1ReadbackError, match="native reads count recomputation mismatch"):
            d1.readback_d1_record(evidence, ROOT, allow_failed=True)


@pytest.mark.parametrize("updates,expected", [
    ({}, []),
    ({"oracle_result": {"status": "fail", "reason": "non-JSON response"}}, ["ORACLE_FAILED:non-JSON response"]),
    ({"native_launch": None}, ["NATIVE_LAUNCH_CUSTODY_MISSING"]),
    ({"post_git": {}}, ["GIT_DRIFT"]),
    ({"post_settings": {"sha256": "different"}}, ["SETTINGS_DRIFT"]),
    ({"imported": {"provider_outcome": "error"}}, ["PROVIDER_ERROR"]),
    ({"imported": {}}, ["PROVIDER_OUTCOME_UNVERIFIED"]),
    ({"observation": {"reads": []}}, ["NO_NATIVE_READ"]),
    ({"surface_contract": {"valid": False}}, ["SURFACE_UNVERIFIED"]),
    ({"surface_contract": {"valid": False, "failure_codes": ["AGENTS_MISMATCH"]}}, ["AGENTS_MISMATCH"]),
    ({"stream_receipt": {}}, ["CAPTURE_INCOMPLETE"]),
    ({"terminal": {"exit_code": 7}}, ["NONZERO_EXIT:7", "CAPTURE_INCOMPLETE"]),
    ({"terminal": {"exit_code": 0, "truncated": True}}, ["CAPTURE_INCOMPLETE"]),
])
def test_real_record_decision_and_failure_explanations_agree(updates, expected):
    arguments = dict(
        authority={"attempt_id": "synthetic-decision"}, descriptor={}, descriptor_sha256="d",
        source_identity_str="synthetic", route={},
        pre_evidence={"git": {"head": "h"}, "settings": {"sha256": "s"}},
        terminal={"exit_code": 0}, stdout=b"", stderr=b"", raw_stream=b"",
        stream_receipt={"schema": "apg.claude-stream-completion/v2", "process_status": 0,
            "raw_stream": {"bytes": 0, "sha256": d1._sha256(b"")}, "durable": True,
            "stream_enabled_before_start": True},
        observation={"reads": [{}]}, delivery_data={}, imported={"provider_outcome": "success"},
        oracle_result={"status": "pass"}, post_git={"head": "h"}, post_settings={"sha256": "s"},
        post_runtime={}, surface_contract={"valid": True, "failure_codes": []},
        execution_kind=d1.FAKE_TRANSPORT_KIND, native_launch={},
    )
    arguments.update(updates)
    record = d1.derive_d1_record(**arguments)
    assert record["post_provider"]["failure_reasons"] == expected
    assert record["provider_free_seam_qualified"] is (not expected)
