"""Provider-free regressions for repaired canary functional observations."""
from __future__ import annotations

import json
from pathlib import Path
import shlex

import pytest

from agent_phase import worker_canary as canary
from test_apg166s_r1_canary import _valid_claude_sonnet_native_record


SESSION = "11111111-2222-4333-8444-555555555555"
CHILD = "abcdef1234567890"


def stream(*, tool="Agent", call="agent-tool-use-1", scoped=True, background=False,
           error=False, child=CHILD, sessions=False):
    rows = [
        {"type": "system", "subtype": "init", "session_id": SESSION,
         "tools": ["Read", "Task"]},
        {"type": "assistant", "session_id": SESSION, "message": {"content": [
            {"type": "tool_use", "id": call, "name": tool,
             "input": {"subagent_type": "apgr-sonnet-leaf:apgr-sonnet-leaf" if scoped else "other",
                       "run_in_background": background}}]}},
        {"type": "user", "session_id": SESSION if not sessions else "other-session",
         "message": {"content": [{"type": "tool_result", "tool_use_id": call,
                                    "is_error": error, "content": "nonce-secret-token"}]},
         "tool_use_result": {"agentId": child, "status": "completed",
                             "agentType": "apgr-sonnet-leaf:apgr-sonnet-leaf",
                             "resolvedModel": "claude-sonnet-5-5",
                             "usage": {"output_tokens_details": {"thinking_tokens": 0}}}},
    ]
    return b"\n".join(json.dumps(row).encode() for row in rows)


def test_zs_task_init_actual_agent_partial_allows_functional_reuse(tmp_path):
    raw = stream()
    record = _valid_claude_sonnet_native_record()
    record["native_admission"][0]["model_observation"]["effective_effort"] = None
    record["native_admission"][0]["model_observation"]["configured_effort"] = "high"
    record["stream_init"] = canary.extract_stream_init(raw)
    correlated = canary.correlate_native_children(
        raw, {"agent-tool-use-1": record["native_admission"][0]}, record["parent_id"],
        record["nonce"], record["worker"]["requested"], metadata_home=tmp_path,
    )
    record.update(native_admission=correlated["children"], native_unmatched=correlated["unmatched"],
                  native_call_coverage=correlated["coverage"])
    result = canary.qualify(record)
    assert record["stream_init"]["agent_tool_names_observed"] == ["Task"]
    assert result["dimensions"]["native_tool_invoked"] is True
    assert result["status"] == "partial"
    assert result["functional"]["admissions"] == 1
    assert result["functional"]["remaining_occupancy"] == 0
    assert result["functional"]["effort"] == "unknown"
    assert canary.native_reuse_ready(result)


@pytest.mark.parametrize("changes", [
    {"tool": "Read"}, {"call": "unmatched"}, {"scoped": False},
    {"background": True}, {"error": True}, {"child": None}, {"sessions": True},
])
def test_unmatched_or_invalid_child_cannot_qualify(changes, tmp_path):
    record = _valid_claude_sonnet_native_record()
    result = canary.correlate_native_children(
        stream(**changes), {"agent-tool-use-1": record["native_admission"][0]},
        record["parent_id"], record["nonce"], record["worker"]["requested"], metadata_home=tmp_path,
    )
    assert not result["children"][0]["tool_correlation"]["matched"]
    record["native_admission"] = result["children"]
    assert not canary.qualify(record)["dimensions"]["native_tool_invoked"]


def test_prose_never_counts_as_tool_invocation(tmp_path):
    raw = json.dumps({"type": "assistant", "session_id": SESSION,
                      "message": {"content": [{"type": "text", "text": "Agent Task"}]}}).encode()
    assert not canary.native_tool_observations(raw)["invocations"]
    assert canary.extract_stream_init(raw) is None
    assert not canary.native_nonce_returns(raw, "Agent")


@pytest.mark.parametrize("model,effort,status", [
    ("claude-sonnet-5-5", "high", "unknown"),
    ("claude-sonnet-5-5", "low", "unknown"),
    ("claude-opus-5-5", "high", "conflict"),
])
def test_bound_child_metadata_merges_without_requested_fallback(tmp_path, model, effort, status):
    path = tmp_path / "projects" / "fixture" / SESSION / "subagents" / f"agent-{CHILD}.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"sessionId": SESSION, "agentId": CHILD, "isSidechain": True,
                               "type": "assistant", "message": {"model": model, "content": "private nonce"},
                               "effort": effort}) + "\n")
    record = _valid_claude_sonnet_native_record()
    record["native_admission"][0]["model_observation"]["effective_effort"] = None
    child = canary.correlate_native_children(stream(), {"agent-tool-use-1": record["native_admission"][0]},
        record["parent_id"], record["nonce"], record["worker"]["requested"], metadata_home=tmp_path)["children"][0]
    assert child["model_status" if status == "conflict" else "effort_status"] == status
    assert "private nonce" not in json.dumps(child["child_observation"])


@pytest.mark.parametrize("family,kind,interface", [
    ("antigravity", "sonnet", "cli"), ("claude", "sonnet", "native"),
    ("claude", "gemini", "stdio-mcp"), ("claude", "luna", "stdio-mcp"),
    ("codex", "gemini", "stdio-mcp"), ("codex", "sonnet", "stdio-mcp"),
    ("codex", "luna", "native"),
])
def test_prompt_uses_parent_interface(tmp_path, monkeypatch, family, kind, interface):
    prompt = canary._prompt(tmp_path / "nonce.txt", family, kind,
                            {"model": "fixture-model", "effort": "high"},
                            interface=interface, worker_entrypoint=tmp_path / "agent-worker")
    if family == "antigravity":
        from apgr_workers import cli
        for name in ("cmd_job_launch", "cmd_job_wait", "cmd_job_outcome"):
            monkeypatch.setattr(cli, name, lambda args: 0)
        commands = canary.cli_worker_commands(tmp_path / "agent-worker", tmp_path / "leaf-task.md", kind)
        for command in commands:
            assert cli.main(command[1:]) == 0
            assert shlex.join(command) in prompt
        assert "submit tool" not in prompt
        assert "parent init" not in prompt
    elif interface == "stdio-mcp":
        assert "agent_worker server submit tool" in prompt
    else:
        assert "native" in prompt


def test_unknown_interface_is_refused(tmp_path):
    with pytest.raises(ValueError, match="interface"):
        canary._prompt(tmp_path / "nonce.txt", "antigravity", "sonnet",
                        {"model": "fixture", "effort": "high"}, interface="stdio-mcp")


def test_effective_stage_unavailable_is_blocked():
    record = _valid_claude_sonnet_native_record()
    record["stage_meta"]["worker_capability"] = {"allowed": False}
    assert canary.qualify(record)["status"] == "blocked"


def test_uncertain_maintained_cleanup_cannot_qualify_from_summary_booleans():
    record = _valid_claude_sonnet_native_record()
    record["cleanup_classification"] = {"classification": "uncertain", "cleanup_proven": False}
    result = canary.qualify(record)
    assert result["passed"] is False
    assert result["dimensions"]["proven_cleanup"] is False


@pytest.mark.parametrize("mutation", [None, "digest", "validation"])
def test_antigravity_nonce_requires_bound_validated_raw(tmp_path, mutation):
    import hashlib
    raw = json.dumps({"result": {"response": "fixture-nonce"}}).encode()
    (tmp_path / "01-work.antigravity-terminal-result.raw.json").write_bytes(raw)
    evidence = {"validation": "validated", "raw": {"sha256": hashlib.sha256(raw).hexdigest()}}
    if mutation == "digest":
        evidence["raw"]["sha256"] = "a" * 64
    if mutation == "validation":
        evidence["validation"] = "invalid"
    assert canary.antigravity_parent_nonce_returned(tmp_path, {"antigravity_evidence": evidence}, "fixture-nonce") is (mutation is None)


@pytest.fixture
def canary_stage_environment(tmp_path, monkeypatch):
    import os
    import sys
    from agent_phase.canary_budget import CanaryBudget, SONNET_PHASE
    from test_apg166s_r1_home_path import _home_bundle
    from types import SimpleNamespace
    from agent_phase import canary_budget
    for key in list(os.environ):
        if key.startswith(canary.DISALLOWED_PREFIXES) or key in canary.DISALLOWED_EXACT:
            monkeypatch.delenv(key, raising=False)
    binaries = tmp_path / "fake-bin"
    binaries.mkdir()
    for name in ("agy", "claude", "codex"):
        path = binaries / name
        path.write_text(f"#!{sys.executable}\nprint('{name} 99.0')\n")
        path.chmod(0o755)
    monkeypatch.setenv("PATH", str(binaries) + os.pathsep + os.environ["PATH"])
    real_run = canary_budget.subprocess.run
    def run(argv, *args, **kwargs):
        if argv[0] == "ps":
            return SimpleNamespace(returncode=0, stdout="fixture-start", stderr="")
        return real_run(argv, *args, **kwargs)
    monkeypatch.setattr(canary_budget.subprocess, "run", run)
    home = _home_bundle(tmp_path)
    budget = CanaryBudget(home=tmp_path / "budget-home", phase=SONNET_PHASE)
    monkeypatch.setattr(canary, "CanaryBudget", lambda **kw: budget)
    return home, budget


def test_run_case_real_stage_registers_validated_gemini_provenance(tmp_path, monkeypatch, canary_stage_environment):
    import os
    import time
    from agent_phase.provider import Result
    from apgr_workers.ledger import ParentLedger
    from test_agent_phase_antigravity import write_fake_evidence
    home, budget = canary_stage_environment
    seen = {}
    def runner(argv, prompt, cwd, maximum, on_output=None):
        write_fake_evidence(argv, 0)
        ledger = ParentLedger(os.environ["APGR_PARENT_ID"], Path(os.environ["APGR_WORKER_STATE_DIR"]))
        seen.update(ledger.get_status())
        cleanup = {k: True for k in ("cleanup_proven", "outer_group_absent", "nested_groups_absent", "verified_absence", "reaped")}
        cleanup["failure_reasons"] = []
        now = time.time()
        return Result(0, b"facility fixture; no Sonnet admission", b"", False, now, now, cleanup=cleanup)
    record = canary.run_case(Path(__file__).resolve().parents[3], home, tmp_path / "case", "gemini-sonnet", runner=runner)
    cap = seen["worker_capability"]
    assert cap["execution_mode"] == "gemini_flash_sub"
    assert cap["parent_provider"] == "antigravity"
    assert cap["parent_family"] == "gemini_flash"
    assert cap["native_worker"] == {"enabled": False}
    assert cap["sonnet_worker"]["transport"] == "claude_external"
    assert cap["parent_stage"] == "work" and cap["parent_run_id"]
    assert record["route_provenance"]["original_requirement"] == "optional"
    assert record["route_provenance"]["qualification_requirement"] == "required"
    assert record["provider_invocations"] == 1
    assert record["cleanup_classification"]["classification"] == "proven_drained"
    assert record["status"] == "partial"
    assert record["outcome_layers"]["child"]["admissions"] == 0
    assert not record["parent_observed"].get("model")
    entry = budget.get_case("gemini-sonnet")["attempts"][0]
    assert entry["details"]["classification_inputs"] == record["classification_inputs"]


@pytest.mark.parametrize("possibly_committed", [False, True])
def test_run_case_preprovider_refusal_vs_uncertain_registration(tmp_path, monkeypatch, canary_stage_environment, possibly_committed):
    from apgr_workers.ledger import ParentLedger
    home, budget = canary_stage_environment
    if possibly_committed:
        def refuse(*args, **kwargs):
            raise ValueError("fixture registration might have committed")
        monkeypatch.setattr(ParentLedger, "register", refuse)
    else:
        resolve = canary.resolve_worker_capability
        def tamper(*args, **kwargs):
            cap = resolve(*args, **kwargs)
            cap["source_root"] = "mismatched-source"
            return cap
        monkeypatch.setattr(canary, "resolve_worker_capability", tamper)
    record = canary.run_case(Path(__file__).resolve().parents[3], home, tmp_path / "case", "gemini-sonnet",
                             runner=lambda *a, **k: pytest.fail("provider started despite required refusal"))
    assert record["status"] == "blocked"
    assert record["provider_invocations"] == 0
    assert "ValueError" in record["diagnostic"]
    assert record["cleanup_proven"] is (not possibly_committed)
    assert budget.get_case("gemini-sonnet")["attempts"][0]["cleanup_proven"] is (not possibly_committed)
