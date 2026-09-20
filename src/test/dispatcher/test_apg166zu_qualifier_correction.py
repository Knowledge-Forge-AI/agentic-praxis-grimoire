"""Provider-free APG166ZU regressions across actual routes and qualification."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import time

import pytest

from agent_phase import worker_canary as canary
from agent_phase.canary_budget import CanaryBudget, DEFAULT_PHASE, SONNET_PHASE
from agent_phase.dispatch import Dispatcher
from agent_phase.provider import Result
from apgr_workers.claude_native import SCOPED_AGENT_NAME
from apgr_workers.ledger import ParentLedger
from apgr_workers.model_observation import claude_native_child_session
from test_apg166s_r1_canary import (
    _valid_claude_sonnet_native_record,
    _valid_claude_sonnet_native_reuse_record,
)
from test_apg166zt_native_metadata import (
    CHILD_AGENT, PARENT_SESSION, child_record, create_parent_transcript,
    create_subagent_transcript,
)
import test_apg166zt_qualifier_repair as qualifier_repair
from test_apg166zt_qualifier_repair import stream

canary_stage_environment = qualifier_repair.canary_stage_environment

ROOT = Path(__file__).resolve().parents[3]
INTERFACES = {
    "claude-gemini": "stdio-mcp", "claude-luna": "stdio-mcp",
    "codex-gemini": "stdio-mcp", "codex-luna": "native",
    "claude-sonnet-native": "native", "claude-sonnet-native-reuse": "native",
    "codex-sonnet": "stdio-mcp", "gemini-sonnet": "cli",
}


def isolated_budgets(tmp_path, monkeypatch, order):
    budgets = {}
    def factory(*, phase):
        budget = CanaryBudget(home=tmp_path / "isolated-budget", phase=phase)
        reserve = budget.reserve
        def reserved(case, **kwargs):
            order.append("reserve")
            return reserve(case, **kwargs)
        monkeypatch.setattr(budget, "reserve", reserved)
        budgets[phase] = budget
        return budget
    monkeypatch.setattr(canary, "CanaryBudget", factory)
    return budgets


def observe_preflight(monkeypatch, order):
    resolve = canary.resolve_worker_capability
    def observed(*args, **kwargs):
        value = resolve(*args, **kwargs)
        order.append("preflight")
        return value
    monkeypatch.setattr(canary, "resolve_worker_capability", observed)


@pytest.mark.parametrize("case", sorted(INTERFACES))
def test_all_source_routes_reach_stage_with_worker_interface(
    tmp_path, monkeypatch, canary_stage_environment, case,
):
    assert set(canary.CASES) == set(canary.CASE_ROUTES) == set(INTERFACES)
    home, _ = canary_stage_environment
    order, seen = [], {}
    budgets = isolated_budgets(tmp_path, monkeypatch, order)
    observe_preflight(monkeypatch, order)
    def stage(self, directory, index, name, prefix, role, endpoint, rendered, resume, **kwargs):
        order.append("stage")
        seen.update(endpoint=endpoint, prompt=rendered.data.decode(), cap=kwargs["worker_capability"])
        raise RuntimeError("injected stage boundary; no provider")
    monkeypatch.setattr(Dispatcher, "_stage", stage)
    record = canary.run_case(ROOT, home, tmp_path / "case", case,
                            runner=lambda *a, **k: pytest.fail("stage double launched provider"))
    assert order == ["preflight", "reserve", "stage"]
    assert record["worker_interface"] == INTERFACES[case]
    family, profile, kind = canary.CASES[case]
    assert (seen["endpoint"].provider, seen["endpoint"].profile) == (family, profile)
    if INTERFACES[case] == "stdio-mcp":
        assert "agent_worker server submit tool" in seen["prompt"]
        assert f"worker_kind={kind}" in seen["prompt"]
    elif family == "codex":
        assert "spawn_agent" in seen["prompt"]
    elif family == "claude":
        assert SCOPED_AGENT_NAME in seen["prompt"]
    else:
        assert "job launch --worker-kind sonnet" in seen["prompt"]
        assert "job wait" in seen["prompt"] and "job outcome" in seen["prompt"]
    phase = SONNET_PHASE if case in canary.SONNET_CASES else DEFAULT_PHASE
    assert budgets[phase].get_case(case)["attempts"][0]["attempt"] == 1
    assert record["provider_invocations"] == 0


@pytest.mark.parametrize("case", ["codex-gemini", "codex-sonnet"])
def test_codex_external_real_stage_registers_and_uses_mcp(
    tmp_path, monkeypatch, canary_stage_environment, case,
):
    home, _ = canary_stage_environment
    order, seen = [], {}
    budgets = isolated_budgets(tmp_path, monkeypatch, order)
    observe_preflight(monkeypatch, order)
    def runner(argv, prompt, cwd, maximum, on_output=None):
        order.append("runner")
        ledger = ParentLedger(os.environ["APGR_PARENT_ID"], Path(os.environ["APGR_WORKER_STATE_DIR"]))
        seen.update(argv=argv, prompt=prompt.decode(), cap=ledger.get_status()["worker_capability"])
        now = time.time()
        cleanup = {k: True for k in ("cleanup_proven", "outer_group_absent", "nested_groups_absent",
                                    "verified_absence", "reaped")}
        cleanup["failure_reasons"] = []
        return Result(0, b"injected provider result; no child", b"", False, now, now, cleanup=cleanup)
    record = canary.run_case(ROOT, home, tmp_path / "case", case, runner=runner)
    assert order == ["preflight", "reserve", "runner"], record.get("diagnostic")
    assert record["worker_interface"] == "stdio-mcp"
    assert record["provider_invocations"] == 1 and record["status"] != "passed"
    assert "agent_worker server submit tool" in seen["prompt"]
    assert f"worker_kind={canary.CASES[case][2]}" in seen["prompt"]
    assert any("mcp_servers.agent_worker" in arg for arg in seen["argv"])
    assert any("submit" in arg and "status" in arg and "result" in arg for arg in seen["argv"])
    assert seen["cap"]["parent_family"] == "codex_parent"
    assert seen["cap"]["allowed_worker_kinds"] == ["gemini", "sonnet"]
    assert seen["cap"]["sonnet_worker"]["transport"] == "claude_external"
    phase = SONNET_PHASE if case in canary.SONNET_CASES else DEFAULT_PHASE
    assert budgets[phase].get_case(case)["attempts"][0]["status"] == record["status"]


@pytest.mark.parametrize("case,mutation", [
    ("codex-sonnet", "native-sonnet"), ("codex-luna", "external-luna"),
    ("codex-luna", "allowed-luna"), ("codex-gemini", "missing-gemini"),
    ("codex-sonnet", "wrong-policy"), ("codex-sonnet", "wrong-parent"),
    ("claude-gemini", "wrong-interface"), ("claude-sonnet-native", "external-sonnet"),
    ("gemini-sonnet", "wrong-interface"), ("codex-sonnet", "route-slot"),
    ("codex-sonnet", "unknown-family"),
])
def test_inconsistent_route_refuses_before_budget_or_provider(
    tmp_path, monkeypatch, canary_stage_environment, case, mutation,
):
    home, _ = canary_stage_environment
    order = []
    budgets = isolated_budgets(tmp_path, monkeypatch, order)
    resolve = canary.resolve_worker_capability
    def tamper(*args, **kwargs):
        cap = deepcopy(resolve(*args, **kwargs))
        if mutation == "native-sonnet":
            cap["sonnet_worker"]["transport"] = "claude_native"
        elif mutation == "external-luna":
            cap["luna_worker"]["transport"] = "codex_external"
        elif mutation == "allowed-luna":
            cap["allowed_worker_kinds"].append("luna")
        elif mutation == "missing-gemini":
            cap["allowed_worker_kinds"].remove("gemini")
        elif mutation == "wrong-policy":
            cap["policy_selection"] = "two_pool_4x4"
        elif mutation == "wrong-parent":
            cap["parent_family"] = "claude_parent"
        elif mutation == "wrong-interface":
            cap["interface"] = "native"
        elif mutation == "external-sonnet":
            cap["sonnet_worker"]["transport"] = "claude_external"
        return cap
    monkeypatch.setattr(canary, "resolve_worker_capability", tamper)
    if mutation == "route-slot":
        monkeypatch.setitem(canary.CASE_ROUTES, case, ("implementation_testing", "gemini_sub", "plan_review"))
    elif mutation == "unknown-family":
        monkeypatch.setitem(canary.CASES, case, ("unsupported", "implementation-testing", "sonnet"))
    record = canary.run_case(ROOT, home, tmp_path / "case", case,
                            runner=lambda *a, **k: pytest.fail("refused route launched provider"))
    assert record.get("preflight_refusal") is True
    assert record["provider_invocations"] == 0 and record["reservation"] is None
    assert not budgets and not order


def correlated_record(tmp_path, *, tool="Agent", count=1, mutation=None):
    record = (_valid_claude_sonnet_native_record() if count == 1
              else _valid_claude_sonnet_native_reuse_record())
    agents = {c["agent_id"]: deepcopy(c) for c in record["native_admission"]}
    rows = [json.loads(line) for line in stream(tool=tool).splitlines()][:1]
    for index, (call, agent) in enumerate(agents.items()):
        child = f"abcdef12345678{index:02x}"
        rows.extend(json.loads(line) for line in stream(tool=tool, call=call, child=child).splitlines()[1:])
    if mutation in {"unscoped", "extra-scoped", "tool-only"}:
        extra = [json.loads(line) for line in stream(tool=tool, call="extra", scoped=mutation != "unscoped").splitlines()][1:]
        rows.extend(extra[:1] if mutation == "tool-only" else extra)
    elif mutation == "ledger-only":
        agents["ledger-only"] = {**deepcopy(next(iter(agents.values()))), "agent_id": "ledger-only"}
    elif mutation == "result-only":
        rows.extend([json.loads(line) for line in stream(tool=tool, call="extra").splitlines()][2:])
    elif mutation == "duplicate-use":
        rows.append(deepcopy(rows[1]))
    elif mutation == "duplicate-result":
        rows.append(deepcopy(rows[2]))
    elif mutation == "conflicting-result":
        other = deepcopy(rows[2])
        other["tool_use_result"]["agentId"] = "fedcba1234567890"
        rows.append(other)
    elif mutation == "duplicate-provider":
        rows[4]["tool_use_result"]["agentId"] = rows[2]["tool_use_result"]["agentId"]
    elif mutation == "malformed-use":
        rows.append({"type": "assistant", "session_id": PARENT_SESSION, "message": {"content": [
            {"type": "tool_use", "name": tool, "id": "malformed", "input": "invalid"}]}})
    elif mutation == "malformed-id":
        rows[1]["message"]["content"][0]["id"] = 3
    elif mutation == "malformed-result":
        rows.append({"type": "user", "session_id": PARENT_SESSION,
                     "message": {"content": [{"type": "tool_result", "tool_use_id": None}]}})
    elif mutation == "invalid-message":
        rows.append({"type": "assistant", "session_id": PARENT_SESSION, "message": []})
    elif mutation == "no-session":
        for row in rows:
            row.pop("session_id", None)
    elif mutation == "multiple-sessions":
        rows[-1]["session_id"] = "other"
    raw = b"\n".join(json.dumps(row).encode() for row in rows)
    if mutation == "invalid-json":
        raw += b"\n{invalid stream line"
    correlated = canary.correlate_native_children(raw, agents, record["parent_id"],
                                                record["nonce"], record["worker"]["requested"], metadata_home=tmp_path)
    record["native_admission"] = correlated["children"]
    record["native_unmatched"] = correlated["unmatched"]
    record["native_call_coverage"] = correlated.get("coverage")
    return record, correlated


@pytest.mark.parametrize("tool", ["Agent", "Task"])
@pytest.mark.parametrize("count", [1, 5])
def test_complete_native_calls_keep_unknown_effort_and_settled_capacity(tmp_path, tool, count):
    record, correlated = correlated_record(tmp_path, tool=tool, count=count)
    q = canary.qualify(record)
    assert correlated["coverage"]["status"] == "complete"
    assert q["dimensions"]["native_call_coverage"] is True
    assert q["functional"]["call_coverage"] == "complete"
    assert q["status"] == "partial" and "worker_effort_unknown" in q["diagnostics"]["unknowns"]
    assert q["functional"]["terminal_result"] == "completed"
    assert q["functional"]["cleanup_proven"] and q["functional"]["remaining_occupancy"] == 0
    assert canary.native_reuse_ready(q) is (count == 1)


@pytest.mark.parametrize("tool", ["Agent", "Task"])
@pytest.mark.parametrize("mutation", [
    "unscoped", "extra-scoped", "ledger-only", "tool-only", "result-only",
    "duplicate-use", "duplicate-result", "conflicting-result", "malformed-use",
    "malformed-id", "malformed-result", "invalid-message", "invalid-json", "no-session", "multiple-sessions",
])
def test_incomplete_native_call_contract_never_authorizes_reuse(tmp_path, tool, mutation):
    record, correlated = correlated_record(tmp_path, tool=tool, mutation=mutation)
    q = canary.qualify(record)
    assert not q["passed"] and not canary.native_reuse_ready(q)
    assert correlated["coverage"]["status"] in {"unknown", "violated"}
    assert q["dimensions"]["native_call_coverage"] is False
    assert q["functional"]["terminal_result"] == "completed"
    assert q["functional"]["cleanup_proven"] and q["functional"]["remaining_occupancy"] == 0


@pytest.mark.parametrize("tool", ["Agent", "Task"])
@pytest.mark.parametrize("mutation", ["unscoped", "extra-scoped", "duplicate-provider"])
def test_five_child_reuse_rejects_extra_or_conflicting_calls(tmp_path, tool, mutation):
    record, _ = correlated_record(tmp_path, tool=tool, count=5, mutation=mutation)
    q = canary.qualify(record)
    assert q["functional"]["call_coverage"] == "violated"
    assert not q["dimensions"]["native_call_coverage"] and not canary.native_reuse_ready(q)
    assert q["functional"]["terminal_result"] == "completed" and q["functional"]["cleanup_proven"]


@pytest.mark.parametrize("mutation", ["missing", "schema", "missing-field", "bad-type", "disagree", "duplicate-ids", "other-attempt"])
def test_missing_or_malformed_coverage_is_unknown(tmp_path, mutation):
    record, _ = correlated_record(tmp_path)
    if mutation == "missing":
        record.pop("native_call_coverage")
    elif mutation == "schema":
        record["native_call_coverage"]["schema"] = "unsupported"
    elif mutation == "missing-field":
        record["native_call_coverage"].pop("tool_only")
    elif mutation == "bad-type":
        record["native_call_coverage"]["unmatched"] = None
    elif mutation == "disagree":
        record["native_unmatched"] = ["extra"]
    elif mutation == "other-attempt":
        record["native_call_coverage"]["parent_id"] = "other-attempt"
    else:
        record["native_call_coverage"]["matched_ids"] *= 2
    q = canary.qualify(record)
    assert q["functional"]["call_coverage"] == "unknown"
    assert "native_call_coverage_unknown" in q["diagnostics"]["unknowns"]
    assert not q["passed"] and not canary.native_reuse_ready(q)


@pytest.mark.parametrize("parent_effort,child_effort,raw_effort", [
    ("low", "high", "high"), ("high", "low", "low"),
    ("max", "high", "max"), ("high", "low", "high"), ("high", "high", "high"),
])
@pytest.mark.parametrize("source", ["subagent", "sidechain", "both"])
def test_effort_observation_never_proves_child_meaning(tmp_path, parent_effort, child_effort, raw_effort, source):
    parent = {"sessionId": PARENT_SESSION, "isSidechain": False, "type": "assistant",
              "message": {"model": "claude-opus-5-5"}, "effort": parent_effort}
    child = child_record(effort=raw_effort, perTurnEffort=raw_effort)
    create_parent_transcript(tmp_path, [parent] + ([child] if source != "subagent" else []))
    if source != "sidechain":
        create_subagent_transcript(tmp_path, [child])
    observation = claude_native_child_session(PARENT_SESSION, CHILD_AGENT, home=tmp_path)
    assert observation["effective_effort"] is None and observation["observed_efforts"] == [raw_effort]
    assert observation["effort_semantics"] == "unestablished"
    record = _valid_claude_sonnet_native_record()
    record["worker"]["requested"]["effort"] = child_effort
    record["parent"]["effort"] = record["parent_observed"]["effort"] = parent_effort
    # The preserved hook adapter also observes an ambiguous terminal effort.
    record["native_admission"][0]["model_observation"]["effective_effort"] = parent_effort
    result = canary.correlate_native_children(stream(), {"agent-tool-use-1": record["native_admission"][0]},
        record["parent_id"], record["nonce"], record["worker"]["requested"], metadata_home=tmp_path)
    record.update(native_admission=result["children"], native_unmatched=result["unmatched"],
                  native_call_coverage=result["coverage"])
    raw_observation = deepcopy(result["children"][0]["child_observation"])
    hook_observation = deepcopy(result["children"][0]["hook_observation"])
    q = canary.qualify(record)
    assert q["status"] == "partial" and q["functional"]["effort"] == "unknown"
    assert "worker_effort_unknown" in q["diagnostics"]["unknowns"] and canary.native_reuse_ready(q)
    assert record["native_admission"][0]["child_observation"] == raw_observation
    assert record["native_admission"][0]["hook_observation"] == hook_observation
    assert hook_observation["effective_effort"] == parent_effort


@pytest.mark.parametrize("model", ["claude-opus-5-5", None])
def test_supported_model_mismatch_or_missing_is_not_effort_proof(tmp_path, model):
    # Full reader-to-correlation path uses this fixture's distinct provider id.
    create_subagent_transcript(tmp_path, [child_record(agentId="abcdef1234567800", message={"model": model})]).rename(
        tmp_path / "projects/test-project" / PARENT_SESSION / "subagents/agent-abcdef1234567800.jsonl")
    record, _ = correlated_record(tmp_path)
    q = canary.qualify(record)
    assert q["functional"]["effort"] == "unknown"
    if model:
        assert q["functional"]["model"] == "conflict" and not canary.native_reuse_ready(q)


@pytest.mark.parametrize("effort,status,ready", [("high", None, True), ("low", None, False), (None, "conflict", False)])
def test_effective_observation_controls_remain_distinct(tmp_path, effort, status, ready):
    record, _ = correlated_record(tmp_path)
    obs = record["native_admission"][0]["model_observation"]
    obs["effective_effort"] = effort
    if status:
        obs["effort_status"] = status
    q = canary.qualify(record)
    assert q["passed"] is (effort == "high")
    assert canary.native_reuse_ready(q) is ready


@pytest.mark.parametrize("models,status", [([], "unknown"), (["claude-opus-5-5"], "mismatch"),
                                          (["claude-sonnet-5-5", "claude-opus-5-5"], "conflict")])
def test_native_model_evidence_keeps_missing_mismatch_and_conflict(tmp_path, models, status):
    record = _valid_claude_sonnet_native_record()
    agent = record["native_admission"][0]
    agent["model_observation"]["effective_model"] = None
    rows = [json.loads(line) for line in stream().splitlines()]
    rows[-1]["tool_use_result"]["resolvedModel"] = None
    create_subagent_transcript(tmp_path, [child_record(message={"model": model})
                                        for model in (models or [None])])
    c = canary.correlate_native_children(b"\n".join(json.dumps(row).encode() for row in rows),
        {agent["agent_id"]: agent}, record["parent_id"], record["nonce"],
        record["worker"]["requested"], metadata_home=tmp_path)
    record.update(native_admission=c["children"], native_unmatched=c["unmatched"], native_call_coverage=c["coverage"])
    q = canary.qualify(record)
    assert q["functional"]["model"] == status and q["functional"]["effort"] == "unknown"
    assert not canary.native_reuse_ready(q)
    assert q["functional"]["terminal_result"] == "completed" and q["functional"]["cleanup_proven"]


def test_multiple_raw_efforts_are_uncertain_rather_than_effective_conflict(tmp_path):
    create_subagent_transcript(tmp_path, [child_record(effort="high", perTurnEffort="low")])
    record = _valid_claude_sonnet_native_record()
    c = canary.correlate_native_children(stream(), {"agent-tool-use-1": record["native_admission"][0]},
        record["parent_id"], record["nonce"], record["worker"]["requested"], metadata_home=tmp_path)
    record.update(native_admission=c["children"], native_unmatched=c["unmatched"], native_call_coverage=c["coverage"])
    before = deepcopy(c["children"][0]["child_observation"])
    q = canary.qualify(record)
    assert q["functional"]["effort"] == "unknown" and canary.native_reuse_ready(q)
    assert before["observed_efforts"] == ["high", "low"]
    assert before["effort_observation_status"] == "multiple_values"
    assert record["native_admission"][0]["child_observation"] == before


class CustomUnexpectedStageError(Exception):
    pass


class CustomUnexpectedReloadError(Exception):
    pass


def test_unexpected_stage_exception_seals_receipt_and_budget_disposition_then_raises(
    tmp_path, monkeypatch, canary_stage_environment,
):
    case = "claude-gemini"
    home, _ = canary_stage_environment
    order = []
    budgets = isolated_budgets(tmp_path, monkeypatch, order)
    observe_preflight(monkeypatch, order)

    def stage_error(*args, **kwargs):
        order.append("stage")
        raise CustomUnexpectedStageError("simulated unexpected stage crash")

    monkeypatch.setattr(Dispatcher, "_stage", stage_error)
    case_dir = tmp_path / "case"

    with pytest.raises(CustomUnexpectedStageError) as exc_info:
        canary.run_case(ROOT, home, case_dir, case,
                        runner=lambda *a, **k: pytest.fail("unexpected stage launched provider"))

    assert "simulated unexpected stage crash" in str(exc_info.value)
    assert order == ["preflight", "reserve", "stage"]

    receipt_path = case_dir / "canary.json"
    assert receipt_path.is_file()
    receipt_bytes = receipt_path.read_bytes()
    receipt_data = json.loads(receipt_bytes.decode())
    assert receipt_data["status"] == "blocked"
    assert receipt_data["error_type"] == "CustomUnexpectedStageError"
    assert receipt_data["cleanup_proven"] is False
    assert "simulated unexpected stage crash" in receipt_data["diagnostic"]

    attempt = budgets[DEFAULT_PHASE].get_case(case)["attempts"][0]
    assert attempt["attempt"] == 1
    assert attempt["status"] == "blocked"
    assert attempt["cleanup_proven"] is False
    assert attempt["details"]["receipt"] == str(receipt_path)
    assert attempt["details"]["receipt_sha256"] == hashlib.sha256(receipt_bytes).hexdigest()
    assert attempt["details"]["error_type"] == "CustomUnexpectedStageError"


def test_unexpected_reload_exception_seals_receipt_and_budget_disposition_then_raises(
    tmp_path, monkeypatch, canary_stage_environment,
):
    case = "claude-gemini"
    home, _ = canary_stage_environment
    order = []
    budgets = isolated_budgets(tmp_path, monkeypatch, order)
    observe_preflight(monkeypatch, order)

    now = time.time()
    cleanup = {k: True for k in ("cleanup_proven", "outer_group_absent", "nested_groups_absent",
                                "verified_absence", "reaped")}
    cleanup["failure_reasons"] = []

    def mock_stage(*args, **kwargs):
        order.append("stage")
        return Result(0, b"", b"", True, now, now, cleanup=cleanup), {"worker_drain": {"uncertain_cleanup": False}}

    def mock_load_bundle(*args, **kwargs):
        order.append("load_bundle")
        raise CustomUnexpectedReloadError("simulated unexpected reload crash")

    monkeypatch.setattr(Dispatcher, "_stage", mock_stage)
    monkeypatch.setattr(canary, "load_bundle", mock_load_bundle)
    case_dir = tmp_path / "case"

    with pytest.raises(CustomUnexpectedReloadError) as exc_info:
        canary.run_case(ROOT, home, case_dir, case,
                        runner=lambda *a, **k: pytest.fail("unexpected reload launched provider"))

    assert "simulated unexpected reload crash" in str(exc_info.value)
    assert order == ["preflight", "reserve", "stage", "load_bundle"]

    receipt_path = case_dir / "canary.json"
    assert receipt_path.is_file()
    receipt_bytes = receipt_path.read_bytes()
    receipt_data = json.loads(receipt_bytes.decode())
    assert receipt_data["status"] == "blocked"
    assert receipt_data["error_type"] == "CustomUnexpectedReloadError"
    assert receipt_data["cleanup_proven"] is False
    assert "simulated unexpected reload crash" in receipt_data["diagnostic"]

    attempt = budgets[DEFAULT_PHASE].get_case(case)["attempts"][0]
    assert attempt["attempt"] == 1
    assert attempt["status"] == "blocked"
    assert attempt["cleanup_proven"] is False
    assert attempt["details"]["receipt"] == str(receipt_path)
    assert attempt["details"]["receipt_sha256"] == hashlib.sha256(receipt_bytes).hexdigest()
    assert attempt["details"]["error_type"] == "CustomUnexpectedReloadError"
