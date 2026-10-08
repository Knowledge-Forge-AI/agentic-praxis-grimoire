"""Pure native tool evidence and observation helpers for worker canaries."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from apgr_workers.claude_native import (
    SCOPED_AGENT_NAME,
    TOOL_ALIAS_MODEL,
    canonical_tool_name,
)

from .worker_evidence import events


def extract_stream_init(raw: bytes) -> dict[str, Any] | None:
    """Extract stream init Agent and version observations narrowly without archiving whole private sessions."""
    from .worker_evidence import events
    for event in events(raw):
        if event.get("type") == "system" and (
            event.get("subtype") == "init"
            or event.get("event") == "init"
            or "tools" in event
        ):
            tools = event.get("tools")
            version = event.get("claude_code_version") or event.get("version")
            return {
                "agent_tool_present": bool(isinstance(tools, list) and any(
                    canonical_tool_name(t) == "Agent" for t in tools if isinstance(t, str))),
                "agent_tool_names_observed": [t for t in tools if isinstance(t, str)
                    and canonical_tool_name(t) == "Agent"] if isinstance(tools, list) else [],
                "tool_alias_model": TOOL_ALIAS_MODEL,
                "claude_code_version": str(version) if version else None,
                "model": event.get("model"),
                "tools": sorted(str(t) for t in tools) if isinstance(tools, list) else [],
            }
    return None


def normalize_native_model_observation(
    obs: dict[str, Any] | None,
    expected_model: str | None,
    expected_effort: str | None,
) -> dict[str, Any]:
    """Retain effective_model/effective_effort and add model_status/effort_status."""
    obs_dict = dict(obs) if isinstance(obs, dict) else {}
    eff_model = obs_dict.get("effective_model")
    eff_effort = obs_dict.get("effective_effort")

    if obs_dict.get("model_status") == "conflict":
        eff_model = None
        model_status = "conflict"
    elif eff_model is None:
        model_status = "unknown"
    elif expected_model and eff_model == expected_model:
        model_status = "observed_match"
    else:
        model_status = "mismatch"

    if obs_dict.get("effort_status") == "conflict":
        eff_effort = None
        effort_status = "conflict"
    elif eff_effort is None:
        effort_status = "unknown"
    elif expected_effort and eff_effort == expected_effort:
        effort_status = "observed_match"
    else:
        effort_status = "mismatch"

    obs_dict["effective_model"] = eff_model
    obs_dict["effective_effort"] = eff_effort
    obs_dict["model_status"] = model_status
    obs_dict["effort_status"] = effort_status
    return obs_dict


def native_tool_observations(raw: bytes, *, nonce: str | None = None) -> dict[str, Any]:
    """Observe only structured, uniquely paired native invocation/result records."""
    sessions, uses, results, native_results = set(), {}, {}, set()
    malformed = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            if not isinstance(json.loads(line), dict):
                malformed += 1
        except (ValueError, UnicodeDecodeError):
            malformed += 1
    for event in events(raw):
        if "session_id" in event:
            if isinstance(event["session_id"], str) and event["session_id"]:
                sessions.add(event["session_id"])
            else:
                malformed += 1
        message = event.get("message")
        if message is not None and not isinstance(message, dict):
            malformed += 1
        content = message.get("content", []) if isinstance(message, dict) else []
        if not isinstance(content, list):
            malformed += 1
            continue
        result_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"]
        for block in content:
            if not isinstance(block, dict):
                malformed += 1
                continue
            name = block.get("name")
            if block.get("type") == "tool_use" and isinstance(name, str) and canonical_tool_name(name) == "Agent":
                args = block.get("input")
                if not isinstance(args, dict) or not isinstance(block.get("id"), str) or not block["id"]:
                    malformed += 1
                    continue
                uses.setdefault(block["id"], []).append({
                    "raw_tool_name": name, "canonical_tool_name": "Agent",
                    "subagent_type": args.get("subagent_type"),
                    "run_in_background": args.get("run_in_background"),
                })
            elif block.get("type") == "tool_result" and isinstance(block.get("tool_use_id"), str):
                terminal = event.get("tool_use_result") if len(result_blocks) == 1 else None
                if not isinstance(terminal, dict):
                    terminal = block.get("tool_use_result")
                terminal = terminal if isinstance(terminal, dict) else {}
                if terminal.get("agentId") or terminal.get("agentType"):
                    native_results.add(block["tool_use_id"])
                results.setdefault(block["tool_use_id"], []).append({
                    "is_error": block.get("is_error") is True,
                    "provider_agent_id": terminal.get("agentId"),
                    "provider_agent_type": terminal.get("agentType"),
                    "status": terminal.get("status"), "resolved_model": terminal.get("resolvedModel"),
                    "nonce_returned": bool(nonce and nonce in json.dumps(block.get("content", ""))),
                })
            elif block.get("type") == "tool_result":
                malformed += 1
    invocations = {}
    for tool_id, records in uses.items():
        paired = results.get(tool_id, [])
        invocations[tool_id] = {
            **records[0], **(paired[0] if len(paired) == 1 else {}),
            "unique": len(records) == 1 and len(paired) == 1,
            "tool_use_id": tool_id,
        }
    native_ids = set(uses) | native_results
    return {"parent_session_id": next(iter(sessions)) if len(sessions) == 1 else None,
            "invocations": invocations, "result_ids": sorted(native_ids & set(results)),
            "native_ids": sorted(native_ids), "malformed_invocations": malformed,
            "duplicate_ids": sorted(k for k in native_ids
                if len(uses.get(k, [])) > 1 or len(results.get(k, [])) > 1),
            "conflicting_provider_ids": sorted(k for k in native_ids if len({
                r["provider_agent_id"] for r in results.get(k, [])
                if isinstance(r.get("provider_agent_id"), str)}) > 1)}


def correlate_native_children(raw: bytes, agents: dict, parent_id: str, nonce: str,
                              choice: dict, *, metadata_home: Path | None = None) -> dict:
    """Bind ledger admission, tool-use id, provider child id and supported metadata."""
    from apgr_workers.model_observation import claude_native_child_session
    observations = native_tool_observations(raw, nonce=nonce)
    children, matched_ids = [], set()
    for tool_id, agent in sorted(agents.items()):
        invocation = observations["invocations"].get(tool_id, {})
        binding = {key: invocation.get(key) for key in (
            "tool_use_id", "provider_agent_id", "raw_tool_name", "provider_agent_type")}
        binding["parent_session_id"] = observations["parent_session_id"]
        matched = bool(binding["parent_session_id"] and invocation.get("unique")
            and invocation.get("subagent_type") == SCOPED_AGENT_NAME
            and invocation.get("run_in_background") is False
            and invocation.get("is_error") is False and invocation.get("status") == "completed"
            and isinstance(binding["provider_agent_id"], str) and binding["provider_agent_id"]
            and invocation.get("provider_agent_type") == SCOPED_AGENT_NAME
            and agent.get("agent_id", tool_id) == tool_id
            and agent.get("agent_type") == "apgr-sonnet-leaf")
        child_obs = claude_native_child_session(binding["parent_session_id"], binding["provider_agent_id"],
            home=metadata_home) if matched else {"effective_model": None, "effective_effort": None,
                                               "limitation": "native_child_not_correlated"}
        hook = agent.get("model_observation") or {}
        models = {v for v in (invocation.get("resolved_model"), hook.get("effective_model"),
                              child_obs.get("effective_model")) if isinstance(v, str)} if matched else set()
        # Neither terminal effort nor sidechain session fields establish effective
        # child effort. Preserve the original hook observation without promotion.
        obs = {"effective_model": next(iter(models)) if len(models) == 1 else None,
               "effective_effort": None, "effort_semantics": "unestablished",
               "source": "correlated_native_child_metadata"}
        if len(models) > 1 or len(child_obs.get("observed_models", [])) > 1:
            obs["model_status"] = "conflict"
        obs = normalize_native_model_observation(obs, choice.get("model"), choice.get("effort"))
        returned = matched and invocation.get("nonce_returned") is True
        children.append({**agent, **obs, "model_observation": obs, "parent_id": parent_id,
            "agent_id": tool_id, "transport": "claude_native", "nonce_returned": returned,
            "tool_correlation": {**binding, "matched": matched},
            "child_observation": {**binding, **child_obs}, "hook_observation": dict(hook)})
        if matched:
            matched_ids.add(tool_id)
    provider_ids = [c["tool_correlation"]["provider_agent_id"] for c in children
                    if c["tool_correlation"]["matched"]]
    conflicts = sorted(p for p in set(provider_ids) if provider_ids.count(p) > 1)
    if conflicts:
        for child in children:
            child["tool_correlation"]["matched"] = False
        matched_ids.clear()
    ledger_ids, invocation_ids = set(agents), set(observations["invocations"])
    native_ids = set(observations["native_ids"])
    unmatched = sorted((ledger_ids | native_ids) - matched_ids)
    coverage = {
        "schema": "apgr.native-call-coverage/v1",
        "parent_id": parent_id,
        "parent_session_id": observations["parent_session_id"],
        "parent_session_bound": bool(observations["parent_session_id"]),
        "ledger_ids": sorted(ledger_ids), "invocation_ids": sorted(invocation_ids),
        "result_ids": observations["result_ids"], "matched_ids": sorted(matched_ids),
        "ledger_only": sorted(ledger_ids - invocation_ids),
        "tool_only": sorted(native_ids - ledger_ids),
        "duplicate_ids": observations["duplicate_ids"],
        "malformed_invocations": observations["malformed_invocations"],
        "conflicting_provider_ids": sorted(set(conflicts) | set(observations["conflicting_provider_ids"])),
        "unmatched": unmatched,
    }
    coverage["status"] = ("unknown" if not coverage["parent_session_bound"] or coverage["malformed_invocations"]
        else "violated" if unmatched or coverage["duplicate_ids"] or coverage["conflicting_provider_ids"]
        else "complete")
    return {"children": children, "unmatched": unmatched, "coverage": coverage}


def parent_nonce_returned(raw: bytes, nonce: str) -> bool:
    from .worker_evidence import events
    for event in events(raw):
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "agent_message" and nonce in str(item.get("text", "")):
            return True
        if event.get("type") == "result" and event.get("is_error") is False and nonce in str(event.get("result", "")):
            return True
        if event.get("type") == "assistant":
            msg = event.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str) and nonce in content:
                    return True
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and nonce in str(block.get("text", "")):
                            return True
            if nonce in str(event.get("text", "")):
                return True
    return False


def native_nonce_returns(raw: bytes, nonce: str) -> dict[str, bool]:
    """Correlate child tool results, never infer a child return from parent prose."""
    observed = native_tool_observations(raw, nonce=nonce)
    return {tool_id: bool(observed["parent_session_id"] and item.get("unique")
        and item.get("subagent_type") == SCOPED_AGENT_NAME
        and item.get("run_in_background") is False and item.get("is_error") is False
        and item.get("provider_agent_id") and item.get("status") == "completed"
        and item.get("nonce_returned") is True)
        for tool_id, item in observed["invocations"].items()}


def antigravity_parent_nonce_returned(run_dir: Path, meta: dict, nonce: str) -> bool:
    evidence = meta.get("antigravity_evidence") or {}
    if evidence.get("validation") != "validated":
        return False
    path = run_dir / "01-work.antigravity-terminal-result.raw.json"
    try:
        if path.is_symlink():
            return False
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != (evidence.get("raw") or {}).get("sha256"):
            return False
        response = (json.loads(raw).get("result") or {}).get("response")
        return isinstance(response, str) and nonce in response
    except (OSError, ValueError, AttributeError):
        return False


def _native_call_coverage(record: dict, candidates: list, expected_count: int) -> str:
    """Validate the complete correlation receipt; absent evidence is unknown."""
    coverage = record.get("native_call_coverage")
    if not isinstance(coverage, dict) or coverage.get("schema") != "apgr.native-call-coverage/v1":
        return "unknown"
    if not record.get("parent_id") or coverage.get("parent_id") != record["parent_id"]:
        return "unknown"
    fields = ("ledger_ids", "invocation_ids", "result_ids", "matched_ids", "ledger_only",
              "tool_only", "duplicate_ids", "conflicting_provider_ids", "unmatched")
    for field in fields:
        values = coverage.get(field)
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
            return "unknown"
        if values != sorted(set(values)):
            return "unknown"
    if type(coverage.get("malformed_invocations")) is not int or coverage["malformed_invocations"] < 0:
        return "unknown"
    if type(coverage.get("parent_session_bound")) is not bool:
        return "unknown"
    if record.get("native_unmatched") != coverage["unmatched"]:
        return "unknown"
    if not coverage["parent_session_bound"] or coverage["malformed_invocations"]:
        return "unknown"
    session = coverage.get("parent_session_id")
    if not isinstance(session, str) or not session:
        return "unknown"
    if coverage.get("status") not in {"complete", "violated"}:
        return "unknown"
    ledger, invocations, results, matched = (set(coverage[k]) for k in fields[:4])
    ids = [c.get("agent_id") for c in candidates]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        return "violated"
    if ledger != set(ids) or set(coverage["ledger_only"]) != ledger - invocations:
        return "unknown"
    if any(coverage[k] for k in ("unmatched", "ledger_only", "tool_only", "duplicate_ids", "conflicting_provider_ids")):
        return "violated"
    if not (ledger == invocations == results == matched) or len(matched) != expected_count:
        return "violated"
    bindings = [c.get("tool_correlation") or {} for c in candidates]
    provider_ids = [b.get("provider_agent_id") for b in bindings]
    if any(b.get("matched") is not True or b.get("tool_use_id") != c.get("agent_id")
           or b.get("parent_session_id") != session for b, c in zip(bindings, candidates)):
        return "violated"
    if any(not isinstance(p, str) or not p for p in provider_ids) or len(set(provider_ids)) != len(provider_ids):
        return "violated"
    return "complete" if coverage["status"] == "complete" else "unknown"


def native_reuse_ready(qualification: dict) -> bool:
    functional, dims = qualification.get("functional", {}), qualification.get("dimensions", {})
    return bool(functional.get("tool_used") and functional.get("child_admitted") == 1
        and functional.get("terminal_result") == "completed" and functional.get("nonce_returned")
        and functional.get("remaining_occupancy") == 0 and functional.get("cleanup_proven")
        and functional.get("model") == "observed_match"
        and functional.get("call_coverage") == "complete" and dims.get("native_call_coverage") is True
        and functional.get("effort") in {"observed_match", "unknown"}
        and all(dims.get(name) for name in ("source_bundle_stable", "source_controller_bound", "no_execution_error")))
