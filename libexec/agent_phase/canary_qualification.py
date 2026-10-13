"""Qualification and parent identity rules for worker canary evidence."""
from __future__ import annotations

from typing import Any

from .canary_budget import SONNET_CASES
from .canary_native_evidence import (
    _native_call_coverage,
    normalize_native_model_observation,
)
from .run import stage_parent_id

CASES = {
    "claude-gemini": ("claude", "opus-high-review", "gemini"),
    "claude-luna": ("claude", "opus-high-review", "luna"),
    "codex-gemini": ("codex", "implementation-testing", "gemini"),
    "codex-luna": ("codex", "implementation-testing", "luna"),
    "claude-sonnet-native": ("claude", "opus-high-review", "sonnet"),
    "claude-sonnet-native-reuse": ("claude", "opus-high-review", "sonnet"),
    "codex-sonnet": ("codex", "implementation-testing", "sonnet"),
    "gemini-sonnet": ("antigravity", "gemini-3.8-flash-high", "sonnet"),
}

CASE_ROUTES = {
    case: ("implementation_testing", "gemini_flash_sub" if family == "antigravity" else "gemini_sub",
           "plan_review" if family == "claude" else "work")
    for case, (family, _profile, _kind) in CASES.items()
}

ANTIGRAVITY_CHECK_KEYS = frozenset({
    "route_source_owned", "roster_selection", "profile_model_match", "stage_identity",
    "launch_argv", "run_binding", "terminal_revalidated", "terminal_success",
})

PARENT_LAUNCH_FIELDS = (
    "stage", "role", "provider", "profile", "argv", "exit_code",
    "worker_capability", "antigravity_evidence",
)


def _launch_bound_parent_identity(record: dict) -> bool:
    """Fail closed for a missing receipt or disagreement with its executed records."""
    try:
        case = record["case"]
        family, profile, _kind = CASES[case]
        phase_type, mode, slot = CASE_ROUTES[case]
        receipt = record["parent_identity"]
        checks = receipt["checks"]
        route = record["route_provenance"]
        parent = record["parent"]
        meta = record["stage_meta"]
        registered = record["registered_parent_capability"]
        expected_endpoint = {"provider": family, "profile": profile}
        return bool(
            family == parent.get("provider") == "antigravity" and parent.get("profile") == profile
            and receipt.get("schema") == "apgr.canary-parent-identity/v1"
            and receipt.get("basis") == receipt.get("status") == "launch_bound_match"
            and receipt.get("runtime_effective_observation") is False and receipt.get("effort_observed") is False
            and receipt.get("effort_basis") == "roster_lookup_on_launched_profile"
            and isinstance(checks, dict) and set(checks) == ANTIGRAVITY_CHECK_KEYS and all(value is True for value in checks.values())
            and receipt.get("parent") == {key: parent[key] for key in ("provider", "profile", "model", "effort")}
            and receipt.get("profile_model") == parent.get("model")
            and receipt.get("route") == route
            and (route.get("phase_type"), route.get("execution_mode"), route.get("endpoint_slot")) == (phase_type, mode, slot)
            and route.get("endpoint") == route.get("resolved_endpoint") == expected_endpoint
            and receipt.get("launch") == {key: meta.get(key) for key in PARENT_LAUNCH_FIELDS}
            and receipt.get("registration") == registered
            and all(registered.get("parent_" + key) == meta["worker_capability"].get("parent_" + key) == parent[key]
                    for key in ("provider", "profile", "model", "effort"))
            and registered.get("parent_run_id") == record["run_id"]
            and registered.get("parent_stage") == meta.get("stage") == parent.get("stage") == "work"
            and registered.get("execution_mode") == meta["worker_capability"].get("execution_mode") == mode
            and type(record.get("provider_invocations")) is int and record["provider_invocations"] == 1
            and record.get("actual_argv") == [meta.get("argv")]
            and receipt.get("parent_id") == record["parent_id"] == stage_parent_id(record["run_id"], "work", 1)
            and receipt.get("run_id") == record["run_id"] and receipt.get("run_directory") == record["run_directory"]
            and receipt.get("stage_nonce") == record.get("nonce") and bool(record.get("nonce"))
            and all(record.get(key) and receipt.get(key) == record[key] for key in ("candidate_source_identity", "controller_identity"))
            and receipt.get("bundle_sha256") == record["bundle"]["manifest_sha256"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def qualify(record: dict) -> dict[str, Any]:
    """Require complete, child-bound observation; missing evidence never passes."""
    parent = record.get("parent") or {}
    observed = record.get("parent_observed") or {}
    spec = record.get("worker") or {}
    requested = spec.get("requested") or {}
    cap = record.get("capability") or {}
    case = record.get("case", "")

    case_family = CASES.get(case, (None,))[0]
    is_antigravity = (case_family == "antigravity")

    is_codex_native = (case == "codex-luna")
    is_claude_native = (case in {"claude-sonnet-native", "claude-sonnet-native-reuse"})
    is_native = is_codex_native or is_claude_native
    is_reuse = (case == "claude-sonnet-native-reuse")

    candidates = record.get("native_admission" if is_native else "worker_results") or []
    expected_count = 5 if is_reuse else 1
    child = candidates[0] if len(candidates) == expected_count else {}
    nonce = record.get("nonce")
    parent_id = record.get("parent_id")
    parent_threads = [item.get("thread_id") for item in observed.get("session_observations", [])]

    if is_codex_native:
        sessions = child.get("session_observations") or []
        child_session = sessions[0] if len(sessions) == 1 else child.get("child_observation") or {}
        binding = bool(
            child_session.get("thread_id")
            and child_session.get("parent_thread_id") in parent_threads
            and child_session.get("parent_thread_id") is not None
            and child_session.get("source") == "codex_session_turn_context"
        )
        worker_nonce = bool(nonce and child_session.get("nonce_returned") is True)
        terminal = child_session.get("terminal_status") == "completed"
        cleanup = terminal and child_session.get("active") is False
        transport = "codex_native" if binding else None
        admission = len(candidates) == 1 and child.get("status") in {"admitted", "completed"} and binding
        kind = "luna" if binding else None
        effective_model = child.get("effective_model")
        effective_effort = child.get("effective_effort")
    elif is_claude_native:
        binding = bool(
            len(candidates) == expected_count
            and all(
                c.get("agent_id")
                and c.get("agent_type") == "apgr-sonnet-leaf"
                and c.get("parent_id") == parent_id
                for c in candidates
            )
        )
        worker_nonce = bool(
            nonce
            and candidates
            and all(c.get("nonce_returned") is True or (nonce in c.get("response", "")) for c in candidates)
        )
        terminal = bool(
            candidates
            and all(c.get("terminal_result") == "completed" and c.get("status") == "closed" for c in candidates)
        )
        cleanup = bool(
            candidates
            and all(c.get("cleanup_proven") is True for c in candidates)
        )
        transport = "claude_native" if binding else None
        admission = bool(
            len(candidates) == expected_count
            and all(c.get("status") in {"closed", "completed", "admitted"} for c in candidates)
            and binding
        )
        kind = "sonnet" if binding else None
        effective_model = child.get("effective_model")
        effective_effort = child.get("effective_effort")
    else:
        jobs = record.get("admission") or {}
        binding = bool(parent_id and child.get("parent_id") == parent_id and child.get("job_id") in jobs)
        worker_nonce = bool(nonce and nonce in child.get("response", ""))
        terminal = child.get("status") == "completed"
        cleanup = child.get("cleanup_proven") is True
        transport = child.get("transport")
        admission = len(jobs) == 1 and binding
        kind = child.get("worker_kind")
        effective_model = child.get("effective_model")
        effective_effort = child.get("effective_effort")

    expected_model = requested.get("model")
    expected_effort = requested.get("effort")

    if is_native and candidates:
        for c in candidates:
            obs = c.get("model_observation") or {
                "effective_model": c.get("effective_model"),
                "effective_effort": c.get("effective_effort"),
            }
            norm_obs = normalize_native_model_observation(obs, expected_model, expected_effort)
            c["model_observation"] = norm_obs
            c["effective_model"] = norm_obs["effective_model"]
            c["effective_effort"] = norm_obs["effective_effort"]
            c["model_status"] = norm_obs["model_status"]
            c["effort_status"] = norm_obs["effort_status"]
        if child:
            effective_model = child.get("effective_model")
            effective_effort = child.get("effective_effort")

    if is_codex_native:
        expected_transport = "codex_native"
    elif is_claude_native:
        expected_transport = "claude_native"
    elif spec.get("kind") == "sonnet":
        expected_transport = "claude_external"
    elif spec.get("kind") == "luna":
        expected_transport = "codex_external"
    else:
        expected_transport = "antigravity"

    limits = cap.get("limits") or {}
    capacity = record.get("capacity_receipt") or {}
    drain = (record.get("stage_meta") or {}).get("worker_drain") or {}
    parent_cleanup = record.get("parent_cleanup") or {}
    cleanup_classification = record.get("cleanup_classification")

    is_sonnet = (spec.get("kind") == "sonnet" or case in SONNET_CASES)
    sonnet_cap_ok = True
    if is_sonnet or limits.get("max_sonnet") is not None or capacity.get("max_sonnet") is not None:
        sonnet_cap_ok = (limits.get("max_sonnet") == 4 and capacity.get("max_sonnet") == 4)

    admission_capacity = bool(
        admission
        and limits.get("max_gemini") == 4
        and limits.get("max_luna") == 4
        and sonnet_cap_ok
        and cap.get("borrowing") is False
        and capacity.get("max_gemini") == 4
        and capacity.get("max_luna") == 4
        and capacity.get("borrowing") is False
    )

    worker_match = bool(
        kind == spec.get("kind")
        and expected_model
        and expected_effort
        and effective_model == expected_model
        and effective_effort == expected_effort
    )
    if is_claude_native and candidates:
        all_matched = all(
            c.get("effective_model") == expected_model
            and c.get("effective_effort") == expected_effort
            and c.get("model_status") == "observed_match"
            and c.get("effort_status") == "observed_match"
            for c in candidates
        )
        worker_match = worker_match and all_matched

    sequential_non_overlap = True
    if is_reuse:
        intervals = [(c.get("created_at"), c.get("updated_at")) for c in candidates]
        sequential_non_overlap = (len(candidates) == 5 and len({c.get("agent_id") for c in candidates}) == 5
            and all(type(start) in (int, float) and type(end) in (int, float) and 0 < start <= end
                    for start, end in intervals))
        if sequential_non_overlap:
            intervals.sort()
            sequential_non_overlap = all(intervals[i][1] <= intervals[i + 1][0] for i in range(4))

    native_tool_invoked = not is_claude_native or bool(len(candidates) == expected_count and all(
        (c.get("tool_correlation") or {}).get("matched") is True
        and (c.get("tool_correlation") or {}).get("tool_use_id") == c.get("agent_id")
        and (c.get("tool_correlation") or {}).get("parent_session_id")
        and (c.get("tool_correlation") or {}).get("provider_agent_id") for c in candidates))
    call_coverage = _native_call_coverage(record, candidates, expected_count) if is_claude_native else None
    stage_cap = (record.get("stage_meta") or {}).get("worker_capability")

    launch_bound_valid = _launch_bound_parent_identity(record) if is_antigravity else False

    dims = {
        "source_bundle_stable": record.get("candidate_unchanged") is True and record.get("bundle_unchanged") is True,
        "source_controller_bound": not is_sonnet or bool(record.get("candidate_source_identity")
            and record.get("controller_identity") == record["candidate_source_identity"]
            and record.get("controller_unchanged") is True),
        "parent_model_effort": (
            launch_bound_valid
            if is_antigravity
            else bool(
                observed.get("model") and observed.get("model") == parent.get("model")
                and observed.get("effort") and observed.get("effort") == parent.get("effort")
                and observed.get("provider") == parent.get("provider")
            )
        ),
        "worker_kind_model_effort": worker_match,
        "transport": transport == expected_transport,
        "admission_capacity": admission_capacity,
        "parent_child_binding": binding,
        "nonce_worker_and_parent": bool(nonce and record.get("nonce_returned") is True and worker_nonce),
        "terminal": record.get("stage_ok") is True and terminal,
        "proven_cleanup": parent_cleanup.get("cleanup_proven") is True and cleanup
            and drain.get("uncertain_cleanup") is False and drain.get("status") == "closed"
            and (cleanup_classification is None or cleanup_classification.get("cleanup_proven") is True),
        "capability_allowed": cap.get("allowed") is True and (stage_cap is None or stage_cap.get("allowed") is True),
        "no_execution_error": not record.get("error_type") and not record.get("authentication_failed"),
        "native_tool_invoked": native_tool_invoked,
        "native_call_coverage": not is_claude_native or call_coverage == "complete",
        "sequential_non_overlap": sequential_non_overlap,
        "native_pool_settled": not is_claude_native or record.get("native_sonnet_count") == 0,
    }
    reasons = [name for name, passed in dims.items() if not passed]
    unknowns = [
        name for name, value in (
            ("parent_model_unknown", observed.get("model")),
            ("parent_effort_unknown", observed.get("effort")),
            ("worker_model_unknown", effective_model),
            ("worker_effort_unknown", effective_effort),
        ) if value is None
    ]
    if is_antigravity:
        unknowns = [name for name in unknowns if not name.startswith("parent_")]
        unknowns += ["parent_runtime_effective_model_unobserved", "parent_runtime_effective_effort_unobserved"]
    if is_claude_native and call_coverage == "unknown":
        unknowns.append("native_call_coverage_unknown")
    status = "passed" if not reasons else "partial"
    if not dims["source_bundle_stable"]:
        status = "invalidated"
    elif not dims["no_execution_error"] or not dims["capability_allowed"]:
        status = "blocked"
    qualification = {"passed": status == "passed", "status": status, "reasons": reasons,
        "dimensions": dims, "diagnostics": {"reasons": reasons, "failed_dimensions": reasons, "unknowns": unknowns}}
    if is_antigravity:
        qualification["diagnostics"]["parent_identity_basis"] = "launch_bound_match" if launch_bound_valid else None
    if is_claude_native:
        def aggregate_status(field):
            values = {c.get(field, "unknown") for c in candidates}
            return next((value for value in ("conflict", "mismatch", "unknown") if value in values),
                        "observed_match" if values else "unknown")
        init = record.get("stream_init") or {}
        qualification["functional"] = {
            "tool_advertised": init.get("agent_tool_present") is True,
            "raw_names": init.get("agent_tool_names_observed", []),
            "tool_used": native_tool_invoked, "child_admitted": len(candidates), "admissions": len(candidates),
            "terminal_result": "completed" if terminal else "unknown",
            "nonce_returned": dims["nonce_worker_and_parent"],
            "remaining_occupancy": record.get("native_sonnet_count"),
            "cleanup_proven": dims["proven_cleanup"],
            "call_coverage": call_coverage,
            "unmatched_calls": record.get("native_unmatched") if isinstance(record.get("native_unmatched"), list) else None,
            "model": aggregate_status("model_status"), "effort": aggregate_status("effort_status"),
        }
    return qualification
