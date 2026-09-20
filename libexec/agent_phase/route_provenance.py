"""Truthful route provenance and transition audit records for dispatcher runs."""

from __future__ import annotations

from typing import Any
from .lifecycle import LifecycleSpec
from .resume_validation import ResumeError


RESOLVED_V4 = "agent-phase-resolved-v4"
RESOLVED_V5 = "agent-phase-resolved-v5"
RESOLVED_V6 = "agent-phase-resolved-v6"
RESOLVED_V7 = "agent-phase-resolved-v7"
SUPPORTED_RESOLVED_SCHEMAS = (RESOLVED_V4, RESOLVED_V5, RESOLVED_V6)

ROUTE_TRANSITION_POLICY = "inherited_prefix_current_suffix"
ROSTER_COMPATIBILITY_INHERITED = "inherited_prefix_current_suffix"
ROSTER_COMPATIBILITY_FINALIZATION = "finalization_only_no_current_roster"

BOUNDED_ROUTE_FIELDS = (
    "endpoint_alias",
    "provider",
    "profile",
    "role",
    "routing_source_slot",
    "candidate_mutation",
    "process_read_only",
    "process_posture",
    "artifact_prefix",
    "review_checkpoint",
    "candidate_binding_key",
    "intelligence",
)


def validate_resolved_schema(schema: Any) -> str:
    """Validate that a resolved schema string is one of the supported versions."""
    if not isinstance(schema, str) or schema not in SUPPORTED_RESOLVED_SCHEMAS:
        raise ResumeError(
            "RESUME_RESOLVED_SCHEMA_UNSUPPORTED",
            f"unsupported source resolved schema: {schema!r}",
        )
    return schema


def validate_current_resolution(
    current_resolved: dict[str, Any],
    lifecycle: LifecycleSpec,
    performed_stages: tuple[str, ...],
) -> None:
    """Validate that current_resolved satisfies lifecycle semantics for all performed stages."""
    stages = current_resolved.get("stages")
    if not isinstance(stages, dict):
        raise ResumeError(
            "RESUME_CURRENT_ROUTE_INVALID",
            "current resolved document lacks stages table",
        )
    for stage_name in performed_stages:
        if stage_name not in stages:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route evidence is missing for stage {stage_name}",
            )
        route_info = stages[stage_name]
        if not isinstance(route_info, dict):
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route evidence for {stage_name} is not an object",
            )
        spec = lifecycle.stage(stage_name)
        if route_info.get("routing_source_slot") != spec.routing_slot:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route routing_source_slot mismatch for {stage_name}: "
                f"expected {spec.routing_slot}, got {route_info.get('routing_source_slot')}",
            )
        if route_info.get("role") != spec.role:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route role mismatch for {stage_name}: "
                f"expected {spec.role}, got {route_info.get('role')}",
            )
        if route_info.get("candidate_mutation") != spec.is_mutating:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route candidate_mutation mismatch for {stage_name}: "
                f"expected {spec.is_mutating}, got {route_info.get('candidate_mutation')}",
            )
        if route_info.get("artifact_prefix") != spec.prefix:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route artifact_prefix mismatch for {stage_name}: "
                f"expected {spec.prefix}, got {route_info.get('artifact_prefix')}",
            )
        if route_info.get("review_checkpoint") != spec.checkpoint:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route review_checkpoint mismatch for {stage_name}: "
                f"expected {spec.checkpoint}, got {route_info.get('review_checkpoint')}",
            )
        if route_info.get("candidate_binding_key") != spec.candidate_key:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route candidate_binding_key mismatch for {stage_name}: "
                f"expected {spec.candidate_key}, got {route_info.get('candidate_binding_key')}",
            )
        if spec.role == "reviewer":
            if not route_info.get("process_read_only"):
                raise ResumeError(
                    "RESUME_CURRENT_ROUTE_INVALID",
                    f"current route for reviewer stage {stage_name} must enforce read-only process",
                )
            posture = route_info.get("process_posture")
            if not isinstance(posture, dict) or not posture.get("enforced"):
                raise ResumeError(
                    "RESUME_CURRENT_ROUTE_INVALID",
                    f"current route for reviewer stage {stage_name} cannot enforce read-only posture",
                )
        if route_info.get("process_read_only") != spec.process_read_only:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route process_read_only mismatch for {stage_name}: "
                f"expected {spec.process_read_only}, got {route_info.get('process_read_only')}",
            )
        posture = route_info.get("process_posture")
        if not isinstance(posture, dict) or bool(posture.get("enforced")) != spec.process_read_only:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                f"current route process_posture enforcement mismatch for {stage_name}",
            )
        if stage_name == lifecycle.terminal_result_stage:
            if current_resolved.get("terminal_result_stage") != lifecycle.terminal_result_stage:
                raise ResumeError(
                    "RESUME_CURRENT_ROUTE_INVALID",
                    f"terminal_result_stage mismatch: expected {lifecycle.terminal_result_stage}, "
                    f"got {current_resolved.get('terminal_result_stage')}",
                )


def stage_effective_route(
    resolved: dict[str, Any],
    stage_name: str,
) -> dict[str, Any] | None:
    """Retrieve the effective route dictionary for stage_name from resolved document."""
    schema = resolved.get("schema")
    if schema == RESOLVED_V6 and "effective_stage_routes" in resolved:
        ledger = resolved.get("effective_stage_routes")
        if isinstance(ledger, dict) and stage_name in ledger:
            return ledger[stage_name]
    stages = resolved.get("stages")
    if isinstance(stages, dict):
        return stages.get(stage_name)
    return None


def get_stage_effective_route(
    source_resolved: dict[str, Any],
    stage_name: str,
    lifecycle: LifecycleSpec,
    source_run_id: str | None = None,
) -> dict[str, Any]:
    """Extract an inherited effective route record for stage_name from source_resolved."""
    schema = source_resolved.get("schema", RESOLVED_V5)
    validate_resolved_schema(schema)

    if schema == RESOLVED_V6 and "effective_stage_routes" in source_resolved:
        ledger = source_resolved["effective_stage_routes"]
        if isinstance(ledger, dict) and stage_name in ledger:
            entry = dict(ledger[stage_name])
            entry["source"] = "inherited"
            if entry.get("route_selecting_run_id") is None and source_run_id is not None:
                entry["route_selecting_run_id"] = source_run_id
            return entry

    stages = source_resolved.get("stages")
    if not isinstance(stages, dict) or stage_name not in stages:
        raise ResumeError(
            "RESUME_ARTIFACT_MISMATCH",
            f"source resolved stages evidence missing for stage {stage_name}",
        )
    stage_info = stages[stage_name]
    if not isinstance(stage_info, dict):
        raise ResumeError(
            "RESUME_ARTIFACT_MISMATCH",
            f"source resolved stage {stage_name} is not an object",
        )
    spec = lifecycle.stage(stage_name)
    roster_prov = (
        {"status": "not_recorded"}
        if schema == RESOLVED_V4
        else source_resolved.get("roster")
    )
    return {
        "stage": stage_name,
        "source": "inherited",
        "route_selecting_run_id": source_run_id,
        "source_schema": schema,
        "roster": roster_prov,
        "endpoint_alias": stage_info.get("endpoint_alias"),
        "provider": stage_info.get("provider"),
        "profile": stage_info.get("profile"),
        "intelligence": stage_info.get("intelligence", {}),
        "process_read_only": stage_info.get("process_read_only", spec.process_read_only),
        "process_posture": stage_info.get("process_posture", {}),
        "role": stage_info.get("role", spec.role),
        "routing_source_slot": stage_info.get("routing_source_slot", spec.routing_slot),
        "candidate_mutation": stage_info.get("candidate_mutation", spec.is_mutating),
        "artifact_prefix": stage_info.get("artifact_prefix", spec.prefix),
        "review_checkpoint": stage_info.get("review_checkpoint", spec.checkpoint),
        "candidate_binding_key": stage_info.get("candidate_binding_key", spec.candidate_key),
    }


def build_fresh_effective_routes(
    resolved: dict[str, Any],
    lifecycle: LifecycleSpec,
    run_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Build fresh effective stage route ledger for newly resolved run."""
    stages = resolved.get("stages", {})
    roster_prov = resolved.get("roster")
    ledger: dict[str, dict[str, Any]] = {}
    for stage in lifecycle.stages:
        stage_info = stages.get(stage.name, {})
        ledger[stage.name] = {
            "stage": stage.name,
            "source": "current",
            "route_selecting_run_id": run_id,
            "source_schema": RESOLVED_V6,
            "roster": roster_prov,
            "endpoint_alias": stage_info.get("endpoint_alias"),
            "provider": stage_info.get("provider"),
            "profile": stage_info.get("profile"),
            "intelligence": stage_info.get("intelligence", {}),
            "process_read_only": stage_info.get("process_read_only", stage.process_read_only),
            "process_posture": stage_info.get("process_posture", {}),
            "role": stage_info.get("role", stage.role),
            "routing_source_slot": stage_info.get("routing_source_slot", stage.routing_slot),
            "candidate_mutation": stage_info.get("candidate_mutation", stage.is_mutating),
            "artifact_prefix": stage_info.get("artifact_prefix", stage.prefix),
            "review_checkpoint": stage_info.get("review_checkpoint", stage.checkpoint),
            "candidate_binding_key": stage_info.get("candidate_binding_key", stage.candidate_key),
        }
    return ledger


def compose_effective_stage_routes(
    source_resolved: dict[str, Any],
    current_resolved: dict[str, Any] | None,
    lifecycle: LifecycleSpec,
    inherited_stages: tuple[str, ...],
    performed_stages: tuple[str, ...],
    source_run_id: str,
    current_run_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Compose canonical effective stage ledger from inherited prefix and current suffix."""
    ledger: dict[str, dict[str, Any]] = {}
    for stage in lifecycle.stages:
        stage_name = stage.name
        if stage_name in inherited_stages:
            ledger[stage_name] = get_stage_effective_route(
                source_resolved, stage_name, lifecycle, source_run_id
            )
        elif stage_name in performed_stages:
            if current_resolved is None:
                raise ResumeError(
                    "RESUME_CURRENT_ROUTE_INVALID",
                    "current route evidence is unavailable for performed stages",
                )
            stage_info = (current_resolved.get("stages") or {}).get(stage_name, {})
            ledger[stage_name] = {
                "stage": stage_name,
                "source": "current",
                "route_selecting_run_id": current_run_id,
                "source_schema": RESOLVED_V6,
                "roster": current_resolved.get("roster"),
                "endpoint_alias": stage_info.get("endpoint_alias"),
                "provider": stage_info.get("provider"),
                "profile": stage_info.get("profile"),
                "intelligence": stage_info.get("intelligence", {}),
                "process_read_only": stage_info.get("process_read_only", stage.process_read_only),
                "process_posture": stage_info.get("process_posture", {}),
                "role": stage_info.get("role", stage.role),
                "routing_source_slot": stage_info.get("routing_source_slot", stage.routing_slot),
                "candidate_mutation": stage_info.get("candidate_mutation", stage.is_mutating),
                "artifact_prefix": stage_info.get("artifact_prefix", stage.prefix),
                "review_checkpoint": stage_info.get("review_checkpoint", stage.checkpoint),
                "candidate_binding_key": stage_info.get("candidate_binding_key", stage.candidate_key),
            }
        else:
            source_stages = source_resolved.get("stages")
            if isinstance(source_stages, dict) and stage_name in source_stages:
                ledger[stage_name] = get_stage_effective_route(
                    source_resolved, stage_name, lifecycle, source_run_id
                )
            elif current_resolved is not None:
                stage_info = (current_resolved.get("stages") or {}).get(stage_name, {})
                ledger[stage_name] = {
                    "stage": stage_name,
                    "source": "unexecuted",
                    "route_selecting_run_id": current_run_id,
                    "source_schema": RESOLVED_V6,
                    "roster": current_resolved.get("roster"),
                    "endpoint_alias": stage_info.get("endpoint_alias"),
                    "provider": stage_info.get("provider"),
                    "profile": stage_info.get("profile"),
                    "intelligence": stage_info.get("intelligence", {}),
                    "process_read_only": stage_info.get("process_read_only", stage.process_read_only),
                    "process_posture": stage_info.get("process_posture", {}),
                    "role": stage_info.get("role", stage.role),
                    "routing_source_slot": stage_info.get("routing_source_slot", stage.routing_slot),
                    "candidate_mutation": stage_info.get("candidate_mutation", stage.is_mutating),
                    "artifact_prefix": stage_info.get("artifact_prefix", stage.prefix),
                    "review_checkpoint": stage_info.get("review_checkpoint", stage.checkpoint),
                    "candidate_binding_key": stage_info.get("candidate_binding_key", stage.candidate_key),
                }
    return ledger


def summarize_route(route_info: dict[str, Any] | None) -> dict[str, Any] | None:
    """Produce deterministic bounded summary of a stage route without sensitive data."""
    if not isinstance(route_info, dict):
        return None
    summary: dict[str, Any] = {
        "endpoint_alias": route_info.get("endpoint_alias"),
        "provider": route_info.get("provider"),
        "profile": route_info.get("profile"),
        "role": route_info.get("role"),
        "routing_source_slot": route_info.get("routing_source_slot"),
        "candidate_mutation": route_info.get("candidate_mutation"),
        "process_read_only": route_info.get("process_read_only"),
        "artifact_prefix": route_info.get("artifact_prefix"),
        "review_checkpoint": route_info.get("review_checkpoint"),
        "candidate_binding_key": route_info.get("candidate_binding_key"),
    }
    intelligence = route_info.get("intelligence")
    if isinstance(intelligence, dict):
        summary["intelligence"] = {
            k: v for k, v in sorted(intelligence.items())
            if k in (
                "model",
                "effort",
                "role",
                "mode",
                "enabled",
                "maximum_concurrency",
                "model_role",
                "catalog",
            )
        }
    return summary


def compute_route_differences(
    source_stage: dict[str, Any] | None,
    current_stage: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute bounded deterministic differences between source and current route."""
    if source_stage is None or current_stage is None:
        return {}
    differences: dict[str, Any] = {}
    for key in BOUNDED_ROUTE_FIELDS:
        source_val = source_stage.get(key)
        current_val = current_stage.get(key)
        if source_val != current_val:
            differences[key] = {
                "source": source_val,
                "current": current_val,
            }
    return differences


def build_route_transition(
    source_resolved: dict[str, Any],
    current_resolved: dict[str, Any] | None,
    lifecycle: LifecycleSpec,
    inherited_stages: tuple[str, ...],
    performed_stages: tuple[str, ...],
    is_finalization_only: bool = False,
    auxiliary_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic, bounded route transition evidence for a resumed run."""
    source_schema = source_resolved.get("schema", RESOLVED_V5)
    source_roster = (
        {"status": "not_recorded"}
        if source_schema == RESOLVED_V4
        else source_resolved.get("roster")
    )
    current_roster = None if current_resolved is None else current_resolved.get("roster")

    if is_finalization_only or current_resolved is None:
        policy = ROSTER_COMPATIBILITY_FINALIZATION
        roster_changed = None
    elif source_schema == RESOLVED_V4:
        policy = ROUTE_TRANSITION_POLICY
        roster_changed = None
    else:
        policy = ROUTE_TRANSITION_POLICY
        roster_changed = source_roster != current_roster

    stage_sources: dict[str, str] = {}
    for stage_name in lifecycle.stage_names:
        if stage_name in inherited_stages:
            stage_sources[stage_name] = "inherited"
        elif stage_name in performed_stages:
            stage_sources[stage_name] = "current"
        else:
            stage_sources[stage_name] = "unexecuted"

    route_summaries: dict[str, Any] = {}
    route_differences: dict[str, Any] = {}
    for stage_name in lifecycle.stage_names:
        src_stage = (source_resolved.get("stages") or {}).get(stage_name)
        cur_stage = (current_resolved.get("stages") or {}).get(stage_name) if current_resolved else None
        is_inherited = stage_name in inherited_stages
        is_performed = stage_name in performed_stages
        route_summaries[stage_name] = {
            "source": summarize_route(src_stage),
            "current": summarize_route(cur_stage),
            "execution": (
                "inherited_historical_retained"
                if is_inherited
                else ("performed_from_current_roster" if is_performed else "not_executed")
            ),
        }
        diff = compute_route_differences(src_stage, cur_stage)
        if diff:
            route_differences[stage_name] = {
                "differences": diff,
                "status": "changed_but_not_executed" if is_inherited else "changed_and_executed",
            }

    transition: dict[str, Any] = {
        "policy": policy,
        "source_schema": source_schema,
        "source_roster": source_roster,
        "current_roster": current_roster,
        "roster_changed": roster_changed,
        "inherited_stages": list(inherited_stages),
        "performed_stages": list(performed_stages),
        "stage_sources": stage_sources,
        "route_summaries": route_summaries,
        "route_differences": route_differences,
    }
    if source_schema == RESOLVED_V4:
        transition["roster_change_reason"] = "source_v4_lacks_roster_provenance"
    if auxiliary_route is not None:
        transition["auxiliary_route"] = summarize_route(auxiliary_route)
    return transition
