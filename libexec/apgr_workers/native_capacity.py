"""APG166ZO triple-pool worker capacity and native Sonnet lifecycle management.

Authority and lifecycle invariants:
1. Triple-pool policy 'triple_pool_4x4x4' schema v2 governs independent
   4-slot pools for Gemini, Luna, and Sonnet without capacity borrowing.
2. Existing dual_pool_4x4 and codex_astra historical runs remain inspect,
   settle, and drain readable, but refuse fresh admission with a pinned-controller
   diagnostic. Historical runs never claim Sonnet capacity.
3. Native Sonnet capacity (reserve, activate, close, rollback) is restricted to
   Claude parents ('claude_opus', 'claude_fable') and the 'apgr-sonnet-leaf'
   agent type, enforced atomically under the parent ledger lock at cap 4.
4. Codex Luna occupancy remains native runtime-owned at 4.
5. Per-call model override is forbidden; background subagents are disallowed.
6. Interrupted native children retain their slot until observed parent-exit drain;
   explicit closure forbids double release.
7. Sufficient correlated terminal evidence and closure share one transaction;
   legacy split-transaction recovery preserves the original terminal evidence.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

TRIPLE_POOL = "triple_pool_4x4x4"
DUAL_POOL = "dual_pool_4x4"
SCHEMA_V1 = "agent-worker-ledger-v1"
SCHEMA_V2 = "agent-worker-ledger-v2"
SUPPORTED_SCHEMAS = frozenset({SCHEMA_V1, SCHEMA_V2})

SONNET_MODEL = "claude-sonnet-5-5"
SONNET_EFFORT = "high"
SONNET_AGENT_TYPE = "apgr-sonnet-leaf"
MAX_POOL_CAPACITY = 4
MAX_AGGREGATE_CAPACITY = 12

CLAUDE_PARENT_FAMILIES = frozenset({"claude_opus", "claude_fable"})
CODEX_PARENT_FAMILIES = frozenset({"codex_parent"})
ALL_PARENT_FAMILIES = frozenset({
    "codex_parent", "codex_astra", "claude_opus", "claude_fable", "gemini_flash",
})
EXTERNAL_WORKER_KINDS = frozenset({"gemini", "luna", "sonnet"})
PINNED_CONTROLLER_DIAGNOSTIC = (
    "fresh worker admission requires triple_pool_4x4x4; "
    "resume historical runs under their pinned generation"
)


class LedgerError(RuntimeError):
    """Base error for capacity ledger operations."""


class CapacityExceededError(LedgerError):
    """Requested worker exceeds per-parent capacity."""


class PinnedControllerError(CapacityExceededError):
    """Historical dual_pool_4x4 or codex_astra ledgers require a pinned controller."""


def _get_selection(data: Mapping[str, Any]) -> str | None:
    return (
        data.get("policy_selection")
        or (data.get("policy") or {}).get("policy_selection")
        or (data.get("worker_capability") or {}).get("policy_selection")
    )


def is_triple_pool(data: Mapping[str, Any]) -> bool:
    return _get_selection(data) == TRIPLE_POOL


def is_historical_ledger(data: Mapping[str, Any]) -> bool:
    return data.get("parent_family") == "codex_astra" or _get_selection(data) == DUAL_POOL


def validate_native_admission_request(tool_input: Mapping[str, Any]) -> tuple[bool, str]:
    atype = tool_input.get("agent_type") or tool_input.get("subagent_type") or tool_input.get("type")
    if atype != SONNET_AGENT_TYPE:
        return False, f"invalid_agent_type: native Sonnet requires {SONNET_AGENT_TYPE}, got {atype!r}"
    model = tool_input.get("model")
    if "model" in tool_input or "effort" in tool_input:
        return False, f"per_call_model_override_disallowed: cannot override model to {model!r}"
    if tool_input.get("background") or tool_input.get("run_in_background"):
        return False, "background_disallowed: native leaf workers cannot run in background"
    return True, "valid"


@dataclass(frozen=True, slots=True)
class NativeHookContract:
    policy_selection: str = TRIPLE_POOL
    schema_version: str = SCHEMA_V2
    sonnet_agent_type: str = SONNET_AGENT_TYPE
    sonnet_model: str = SONNET_MODEL
    sonnet_effort: str = SONNET_EFFORT
    max_concurrency: int = MAX_POOL_CAPACITY
    background_allowed: bool = False
    per_call_model_override_allowed: bool = False

    def validate_request(self, tool_input: Mapping[str, Any]) -> tuple[bool, str]:
        return validate_native_admission_request(tool_input)


def init_triple_pool_policy_snapshot(policy_snapshot: dict[str, Any], max_luna: int | None, max_sonnet: int | None) -> None:
    policy_snapshot.update({
        "policy_selection": TRIPLE_POOL, "max_luna": max_luna or MAX_POOL_CAPACITY,
        "max_sonnet": max_sonnet or MAX_POOL_CAPACITY, "borrowing": False,
    })


def init_triple_pool_data(data: dict[str, Any], parent_family: str, allowed: list[str] | None) -> None:
    default_allowed = (
        ["gemini", "sonnet"] if parent_family == "codex_parent"
        else ["gemini", "luna"] if parent_family in CLAUDE_PARENT_FAMILIES
        else ["gemini", "luna", "sonnet"]
    )
    data["policy_selection"] = TRIPLE_POOL
    data["allowed_worker_kinds"] = list(default_allowed if allowed is None else allowed)
    data["pool_state"] = {"gemini": {"paused": False}, "luna": {"paused": False}, "sonnet": {"paused": False}}
    data["native_occupancy"] = {
        "status": "unknown", "count": None,
        "owner": "codex_runtime" if parent_family == "codex_parent" else "ledger" if parent_family in CLAUDE_PARENT_FAMILIES else "none",
    }


def check_triple_pool_capacity(
    worker_kind: str, g_count: int, max_gemini: int, jobs: Mapping[str, Any],
    policy: Mapping[str, Any], active_count_fn: Callable[[Mapping[str, Any], str], int],
) -> None:
    if worker_kind == "gemini" and g_count >= max_gemini:
        raise CapacityExceededError(f"Gemini capacity limit reached: {g_count}/{max_gemini} active")
    for kind in ("luna", "sonnet"):
        if worker_kind == kind:
            max_c = policy.get(f"max_{kind}", MAX_POOL_CAPACITY)
            c = active_count_fn(jobs, kind)
            if c >= max_c:
                raise CapacityExceededError(f"{kind.title()} capacity limit reached: {c}/{max_c} active")


def build_triple_pool_status(
    data: Mapping[str, Any], status: dict[str, Any], l_count: int, active_states: frozenset[str],
    active_count_fn: Callable[[Mapping[str, Any], str], int],
    job_kind_fn: Callable[[Mapping[str, Any]], str], copy_fn: Callable[[Any], Any],
) -> dict[str, Any]:
    jobs = data.get("gemini_jobs") or {}
    ext_g, ext_l, ext_s = active_count_fn(jobs, "gemini"), active_count_fn(jobs, "luna"), active_count_fn(jobs, "sonnet")
    pools = copy_fn(data.get("pool_state") or {})
    family = data.get("parent_family")
    is_claude = family in CLAUDE_PARENT_FAMILIES
    nat_count = l_count if is_claude else None
    nat_adm = "ledger" if is_claude else "codex_runtime" if family == "codex_parent" else "none"
    nat_occ = copy_fn(data.get("native_occupancy")) or {
        "status": "active" if (nat_count or 0) > 0 else "idle", "count": nat_count, "owner": nat_adm,
    }
    agg = ext_g + ext_l + ext_s + (nat_count or 0)
    status.update({
        "policy_selection": TRIPLE_POOL,
        "allowed_worker_kinds": copy_fn(data.get("allowed_worker_kinds") or []),
        "gemini_count": ext_g, "gemini_remaining": max(0, 4 - ext_g),
        "luna_count": ext_l, "luna_remaining": max(0, 4 - ext_l),
        "sonnet_count": ext_s + (nat_count or 0), "sonnet_remaining": max(0, 4 - ext_s - (nat_count or 0)),
        "external_gemini_count": ext_g, "external_luna_count": ext_l, "external_sonnet_count": ext_s,
        "external_counts": {"gemini": ext_g, "luna": ext_l, "sonnet": ext_s},
        "external_remaining": {"gemini": max(0, 4 - ext_g), "luna": max(0, 4 - ext_l), "sonnet": max(0, 4 - ext_s)},
        "max_luna": 4, "max_sonnet": 4,
        "native_count": nat_count, "native_admission": nat_adm, "native_occupancy": nat_occ,
        "aggregate_count": agg, "aggregate_remaining": max(0, 12 - agg), "aggregate_admission": "informational",
        "pool_state": pools,
        "paused_pools": [k for k in ("gemini", "luna", "sonnet") if isinstance(pools.get(k), Mapping) and pools[k].get("paused") is True],
        "active_external_jobs": [j.get("job_id") for j in jobs.values() if isinstance(j, dict) and j.get("status") in active_states],
        "active_gemini_jobs": [j.get("job_id") for j in jobs.values() if isinstance(j, dict) and j.get("status") in active_states and job_kind_fn(j) == "gemini"],
        "active_luna_jobs": [j.get("job_id") for j in jobs.values() if isinstance(j, dict) and j.get("status") in active_states and job_kind_fn(j) == "luna"],
        "active_sonnet_jobs": [j.get("job_id") for j in jobs.values() if isinstance(j, dict) and j.get("status") in active_states and job_kind_fn(j) == "sonnet"],
    })
    return status


def reserve_native_sonnet(
    data: dict[str, Any], agent_id: str, agent_type: str, active_states: frozenset[str],
) -> tuple[bool, str]:
    parent_family = data.get("parent_family")
    if parent_family not in CLAUDE_PARENT_FAMILIES:
        return False, f"native_sonnet_only_for_claude: parent family {parent_family!r} cannot host native Sonnet"
    if agent_type != SONNET_AGENT_TYPE:
        return False, f"invalid_agent_type: native Sonnet requires {SONNET_AGENT_TYPE}, got {agent_type!r}"
    pool_state = data.get("pool_state") or {}
    sonnet_pool = pool_state.get("sonnet")
    if isinstance(sonnet_pool, Mapping) and sonnet_pool.get("paused") is True:
        cause = sonnet_pool.get("cause") or "sonnet pool paused"
        return False, f"sonnet worker pool is paused: {cause}"

    agents = data.setdefault("native_agents", {})
    existing = agents.get(agent_id)
    if isinstance(existing, dict) and existing.get("status") == "closed":
        return False, "native_agent_closed"
    if isinstance(existing, dict) and existing.get("status") in active_states:
        return True, "already_admitted"
    active_count = sum(1 for a in agents.values() if isinstance(a, dict) and a.get("status") in active_states)
    if active_count >= MAX_POOL_CAPACITY:
        return False, f"Sonnet capacity limit reached: {active_count}/{MAX_POOL_CAPACITY} active"
    now = time.time()
    agents[agent_id] = {"agent_id": agent_id, "agent_type": SONNET_AGENT_TYPE, "status": "reserved", "created_at": now, "updated_at": now}
    return True, "admitted"


def activate_native_sonnet(data: dict[str, Any], agent_id: str, agent_type: str) -> tuple[bool, str]:
    agents = data.setdefault("native_agents", {})
    existing = agents.get(agent_id)
    if isinstance(existing, dict):
        if existing.get("status") == "reserved":
            existing["status"] = "active"
            existing["updated_at"] = time.time()
            return True, "activated"
        return (True, "already_active") if existing.get("status") == "active" else (False, "native_agent_closed")
    events = data.setdefault("unmatched_native_events", [])
    events.append({"agent_id": agent_id, "agent_type": agent_type, "observed_at": time.time()})
    del events[:-64]
    return False, "unmatched_start_event"


def rollback_native_sonnet(data: dict[str, Any], agent_id: str) -> bool:
    agents = data.get("native_agents", {})
    existing = agents.get(agent_id)
    if isinstance(existing, dict) and existing.get("status") == "reserved":
        del agents[agent_id]
        return True
    return False


def close_native_sonnet(data: dict[str, Any], agent_id: str, active_states: frozenset[str]) -> bool:
    agents = data.get("native_agents", {})
    existing = agents.get(agent_id)
    if isinstance(existing, dict) and existing.get("status") in active_states:
        existing["status"] = "closed"
        existing["updated_at"] = time.time()
        return True
    return False


def drain_active_native_agents(data: dict[str, Any], active_states: frozenset[str], parent_exit_observed: bool = False) -> tuple[list[str], bool]:
    drained_ids, uncertain = [], False
    for agent_id, agent in sorted((data.get("native_agents") or {}).items()):
        if isinstance(agent, dict) and agent.get("status") in active_states:
            agent["status"] = "closed" if parent_exit_observed else "uncertain"
            agent["drain_closed"] = parent_exit_observed
            agent["parent_exit_observed"] = parent_exit_observed
            agent["updated_at"] = time.time()
            drained_ids.append(str(agent_id))
            uncertain = not parent_exit_observed
    return drained_ids, uncertain


def reserve_native_agent_slot(
    data: dict[str, Any], agent_id: str, agent_type: str, active_states: frozenset[str],
) -> tuple[bool, str]:
    if not isinstance(agent_id, str) or not agent_id:
        return False, "invalid_native_agent_id"
    if not isinstance(agent_type, str) or not agent_type:
        return False, "invalid_native_agent_type"
    if not data or data.get("status") != "active":
        return True, "inert_outside_registered_parent"
    if is_historical_ledger(data):
        raise PinnedControllerError(PINNED_CONTROLLER_DIAGNOSTIC)
    family = data.get("parent_family")
    if is_triple_pool(data):
        if family in CLAUDE_PARENT_FAMILIES:
            return reserve_native_sonnet(data, agent_id, agent_type, active_states)
        if family in CODEX_PARENT_FAMILIES:
            if agent_type == SONNET_AGENT_TYPE:
                return False, "Codex Sonnet workers require external Claude transport"
            return True, "native_admission_owned_by_codex_runtime"
        return True, f"inert_non_native_parent_{family}"
    return False, "native admission requires a current three-pool capability"


def activate_native_agent_slot(data: dict[str, Any], agent_id: str, agent_type: str) -> tuple[bool, str]:
    if not data or data.get("status") != "active":
        return False, "inert_outside_registered_parent"
    family = data.get("parent_family")
    if is_triple_pool(data):
        if family in CLAUDE_PARENT_FAMILIES:
            return activate_native_sonnet(data, agent_id, agent_type)
        if family in CODEX_PARENT_FAMILIES:
            return True, "native_admission_owned_by_codex_runtime"
        return False, f"inert_non_native_parent_{family}"
    return False, "native activation requires a current three-pool capability"


def rollback_native_agent_slot(data: dict[str, Any], agent_id: str) -> bool:
    return rollback_native_sonnet(data, agent_id)


def close_native_agent_slot(data: dict[str, Any], agent_id: str, active_states: frozenset[str]) -> bool:
    family = data.get("parent_family")
    if is_triple_pool(data):
        return close_native_sonnet(data, agent_id, active_states) if family in CLAUDE_PARENT_FAMILIES else False
    if family == "codex_astra" and _get_selection(data) == DUAL_POOL:
        return False
    agents = data.get("native_agents", {})
    existing = agents.get(agent_id)
    if isinstance(existing, dict) and existing.get("status") in active_states:
        existing["status"] = "closed"
        existing["updated_at"] = time.time()
        return True
    return False


def sufficient_native_terminal(record: Mapping[str, Any]) -> bool:
    return record.get("cleanup_proven") is True and (
        record.get("terminal_result"), record.get("terminal_evidence")
    ) in {
        ("completed", "foreground_tool_return"),
        ("failed", "foreground_tool_return"),
        ("failed", "legacy_not_started"),
    }


def settle_native_sonnet(
    data: dict[str, Any], agent_id: str, evidence: Mapping[str, Any],
    active_states: frozenset[str], recovery: Mapping[str, Any] | None = None,
) -> str:
    """Mutate the caller's locked transaction; never persist or acquire a lock.

    A failed close raises so the caller cannot persist terminal-but-occupied
    state. A correlated repeat can recover sufficient legacy evidence without
    overwriting its result, cleanup proof or model qualification.
    """
    record = (data.get("native_agents") or {}).get(agent_id)
    if not isinstance(record, dict) or record.get("status") not in active_states:
        return "ignored"
    if record.get("agent_id") != agent_id or record.get("agent_type") != SONNET_AGENT_TYPE:
        return "retained"
    if record.get("terminal_result"):
        if recovery is None or not sufficient_native_terminal(record):
            return "retained"
        record.setdefault("settlement", "recovered_split_transaction")
        record.setdefault("settlement_recovery", dict(recovery))
        outcome = "recovered"
    else:
        if not sufficient_native_terminal(evidence):
            raise ValueError("native settlement requires sufficient terminal evidence")
        record.update(evidence)
        record["settlement"] = "atomic_foreground_terminal"
        outcome = "settled"
    if not close_native_agent_slot(data, agent_id, active_states):
        raise LedgerError("native terminal settlement could not close its reservation")
    return outcome


def validate_triple_capability(cap, family):
    """Reject missing, cross-provider or enlarged authority before ledger registration."""
    limits = cap.get("limits") or {}
    if any(type(limits.get("max_" + kind)) is not int or limits["max_" + kind] != 4
           for kind in ("gemini", "luna", "sonnet")) or limits.get("max_aggregate") != 12:
        raise ValueError("triple_pool_4x4x4 requires exactly four slots per pool and aggregate 12")
    if any(cap.get(key) is not expected for key, expected in
           (("borrowing", False), ("leaf_only", True), ("parent_authority", True))):
        raise ValueError("triple capability requires no borrowing, leaf-only and parent authority")
    expected = {"codex_parent": {"gemini", "sonnet"}, "claude_opus": {"gemini", "luna"},
                "claude_fable": {"gemini", "luna"}, "gemini_flash": {"gemini", "luna", "sonnet"}}[family]
    allowed = cap.get("allowed_worker_kinds")
    if not isinstance(allowed, list) or len(set(allowed)) != len(allowed) or not set(allowed) <= expected:
        raise ValueError("triple capability exposes the wrong native/foreign worker kinds")
    transports = ("codex_native", "claude_external") if family == "codex_parent" else (
        "codex_external", "claude_native" if family in CLAUDE_PARENT_FAMILIES else "claude_external")
    for kind, transport in zip(("luna", "sonnet"), transports):
        worker = cap.get(kind + "_worker") or {}
        if worker.get("transport") != transport or worker.get("maximum_concurrency") != 4:
            raise ValueError(f"invalid {kind} transport or capacity")
    if (cap["sonnet_worker"].get("model"), cap["sonnet_worker"].get("effort")) != (SONNET_MODEL, SONNET_EFFORT):
        raise ValueError("Sonnet must be claude-sonnet-5-5/high")
