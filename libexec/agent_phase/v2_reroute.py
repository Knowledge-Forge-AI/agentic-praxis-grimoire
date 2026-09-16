"""Dynamic turn rerouting, failure disposition, and retry engine for Request V2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any

from .capabilities import EndpointCapabilities
from .config_routing import RETAINED_STATIC_MODES
from .dynamic_router import (
    NoRouteAvailableError,
    OperationalObservation,
    ResolvedActorRoute,
    resolve_dynamic_route,
)
from .failure_classifier import (
    ProviderFailureClassification,
    classify_provider_result,
    is_recognized_codex_quota_banner_only,
)
from .persistence import (
    record_artifact,
    record_invocation_attempt,
    record_route_resolution,
    update_invocation_attempt,
    update_semantic_responsibility,
    utc_now_iso,
)
from .persistence_feedback import (
    record_invocation_observation_relation,
    record_operational_observation_idempotent,
)
from .probes import collect_operational_observations
from .semantic_roles import ActorBinding

SCHEMA_PROVIDER_FAILURE = "apgr-provider-failure-v1"
SCHEMA_ROUTE_DECISION = "apgr-route-decision-v1"

PROVIDER_FAILURE_V1_REQUIRED_KEYS = frozenset({
    "attempt_id",
    "attempt_number",
    "binding_id",
    "confidence",
    "detail",
    "endpoint_alias",
    "error_message",
    "exit_code",
    "failure_category",
    "failure_id",
    "match_basis",
    "observation_digests",
    "observation_expirations",
    "observation_ids",
    "observed_at",
    "profile",
    "provider",
    "reset_hint",
    "reset_timestamp",
    "retryable",
    "run_id",
    "schema",
    "stderr_sha256",
    "stdout_sha256",
    "substantive",
    "timezone_assumption",
})

ROUTE_DECISION_V1_REQUIRED_KEYS = frozenset({
    "attempt_number",
    "binding_id",
    "decision_id",
    "decision_timestamp",
    "observation_ids",
    "outcome",
    "predecessor_attempt_id",
    "rejections",
    "run_id",
    "schema",
    "selected_endpoint_alias",
    "selected_profile",
    "selected_provider",
    "selection_rationale",
})


def validate_provider_failure_payload(payload: Mapping[str, Any]) -> None:
    """Validate closed schema for apgr-provider-failure-v1 (Scope K)."""
    if payload.get("schema") != SCHEMA_PROVIDER_FAILURE:
        raise ValueError(
            f"Invalid schema: {payload.get('schema')!r}, expected {SCHEMA_PROVIDER_FAILURE!r}"
        )
    actual_keys = set(payload.keys())
    if actual_keys != PROVIDER_FAILURE_V1_REQUIRED_KEYS:
        missing = PROVIDER_FAILURE_V1_REQUIRED_KEYS - actual_keys
        extra = actual_keys - PROVIDER_FAILURE_V1_REQUIRED_KEYS
        raise ValueError(
            f"Closed schema violation for {SCHEMA_PROVIDER_FAILURE}: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if not isinstance(payload["observation_ids"], list):
        raise ValueError("observation_ids must be a list")
    if not isinstance(payload["observation_digests"], dict):
        raise ValueError("observation_digests must be a dict")
    if not isinstance(payload["observation_expirations"], dict):
        raise ValueError("observation_expirations must be a dict")
    if not isinstance(payload["substantive"], bool):
        raise ValueError("substantive must be a boolean")
    if not isinstance(payload["retryable"], bool):
        raise ValueError("retryable must be a boolean")


def validate_route_decision_payload(payload: Mapping[str, Any]) -> None:
    """Validate closed schema for apgr-route-decision-v1 (Scope K)."""
    if payload.get("schema") != SCHEMA_ROUTE_DECISION:
        raise ValueError(
            f"Invalid schema: {payload.get('schema')!r}, expected {SCHEMA_ROUTE_DECISION!r}"
        )
    actual_keys = set(payload.keys())
    if actual_keys != ROUTE_DECISION_V1_REQUIRED_KEYS:
        missing = ROUTE_DECISION_V1_REQUIRED_KEYS - actual_keys
        extra = actual_keys - ROUTE_DECISION_V1_REQUIRED_KEYS
        raise ValueError(
            f"Closed schema violation for {SCHEMA_ROUTE_DECISION}: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if not isinstance(payload["observation_ids"], list):
        raise ValueError("observation_ids must be a list")
    if not isinstance(payload["rejections"], dict):
        raise ValueError("rejections must be a dict")


@dataclass(frozen=True)
class TurnFailureDisposition:
    """Immutable summary of a turn execution failure and its routing implications."""
    category: str
    confidence: str
    substantive: bool
    retryable: bool
    observation_ids: tuple[str, ...]
    sanitized_error: str
    reset_timestamp: float | None
    artifact_path: str
    classification: ProviderFailureClassification


def is_substantive_failure(tree_before: str, tree_after: str, stdout: bytes) -> bool:
    """Determine if turn failure is substantive vs pre-substantive."""
    if tree_after != tree_before:
        return True
    if not stdout or not stdout.strip():
        return False
    if is_recognized_codex_quota_banner_only(stdout):
        return False
    return True


def record_provider_failure_artifact(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    run_dir: Path,
    binding: ActorBinding,
    attempt_id: str,
    attempt_number: int,
    provider: str,
    profile: str,
    endpoint_alias: str,
    exit_code: int,
    classification: ProviderFailureClassification,
    substantive: bool,
    retryable: bool,
    now: float | None = None,
) -> str:
    """Persist apgr-provider-failure-v1 artifact to run directory and SQLite."""
    ref_now = time.time() if now is None else float(now)
    active_obs = classification.observations_to_persist if (not substantive) else ()
    obs_ids = [o.observation_id for o in active_obs]
    obs_digests = {o.observation_id: o.digest for o in active_obs}
    obs_expirations = {
        o.observation_id: o.expires_at for o in active_obs if o.expires_at is not None
    }
    artifact_filename = f"provider-failure-{attempt_id}.json"
    artifact_path = run_dir / artifact_filename
    payload = {
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "binding_id": binding.binding_id,
        "confidence": classification.confidence,
        "detail": {
            "exit_code": exit_code,
            "match_basis": classification.match_basis,
            "reset_hint": classification.reset_hint,
            "stderr_sha256": classification.stderr_sha256,
            "stdout_sha256": classification.stdout_sha256,
            "timezone_assumption": classification.timezone_assumption,
        },
        "endpoint_alias": endpoint_alias,
        "error_message": classification.sanitized_evidence_excerpt,
        "exit_code": exit_code,
        "failure_category": classification.category,
        "failure_id": f"fail-{attempt_id}",
        "match_basis": classification.match_basis,
        "observation_digests": obs_digests,
        "observation_expirations": obs_expirations,
        "observation_ids": obs_ids,
        "observed_at": ref_now,
        "profile": profile,
        "provider": provider,
        "reset_hint": classification.reset_hint,
        "reset_timestamp": classification.parsed_reset_timestamp,
        "retryable": retryable,
        "run_id": run_id,
        "schema": SCHEMA_PROVIDER_FAILURE,
        "stderr_sha256": classification.stderr_sha256,
        "stdout_sha256": classification.stdout_sha256,
        "substantive": substantive,
        "timezone_assumption": classification.timezone_assumption,
    }
    validate_provider_failure_payload(payload)
    raw = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    artifact_path.write_bytes(raw)
    record_artifact(
        conn, artifact_id=f"art-fail-{attempt_id}", run_id=run_id,
        artifact_name=f"provider-failure-{attempt_id}", relative_path=artifact_filename,
        size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), content_type="application/json",
    )
    return str(artifact_path)


def record_route_decision_artifact(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    run_dir: Path,
    binding_id: str,
    attempt_number: int,
    predecessor_attempt_id: str | None,
    route: ResolvedActorRoute | None,
    rejections: Mapping[str, str] | None = None,
    outcome: str = "rerouted",
    now: float | None = None,
) -> str:
    """Persist apgr-route-decision-v1 artifact to run directory and SQLite."""
    ref_now = time.time() if now is None else float(now)
    artifact_filename = f"route-decision-{binding_id}-attempt-{attempt_number}.json"
    artifact_path = run_dir / artifact_filename
    payload = {
        "attempt_number": attempt_number,
        "binding_id": binding_id,
        "decision_id": f"dec-{binding_id}-attempt-{attempt_number}",
        "decision_timestamp": ref_now,
        "observation_ids": list(route.observation_ids) if route else [],
        "outcome": outcome,
        "predecessor_attempt_id": predecessor_attempt_id,
        "rejections": dict(rejections) if rejections else (dict(route.rejections) if route and route.rejections else {}),
        "run_id": run_id,
        "schema": SCHEMA_ROUTE_DECISION,
        "selected_endpoint_alias": route.endpoint_alias if route else None,
        "selected_profile": route.profile if route else None,
        "selected_provider": route.provider if route else None,
        "selection_rationale": route.selection_rationale if route else "no route selected",
    }
    validate_route_decision_payload(payload)
    raw = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    artifact_path.write_bytes(raw)
    record_artifact(
        conn, artifact_id=f"art-dec-{binding_id}-att-{attempt_number}", run_id=run_id,
        artifact_name=f"route-decision-{binding_id}-attempt-{attempt_number}",
        relative_path=artifact_filename, size_bytes=len(raw),
        sha256=hashlib.sha256(raw).hexdigest(), content_type="application/json",
    )
    return str(artifact_path)


def handle_turn_failure(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    run_dir: Path,
    binding: ActorBinding,
    attempt_id: str,
    attempt_number: int,
    provider: str,
    profile: str,
    endpoint_alias: str,
    exit_code: int,
    stdout_bytes: bytes,
    stderr_bytes: bytes,
    tree_before: str,
    tree_after: str,
    now: float | None = None,
) -> TurnFailureDisposition:
    """Process non-zero turn exit per Finding F2 ordering."""
    ref_now = time.time() if now is None else float(now)
    substantive = is_substantive_failure(tree_before, tree_after, stdout_bytes)
    classification = classify_provider_result(
        provider=provider,
        profile=profile,
        exit_code=exit_code,
        stdout=stdout_bytes,
        stderr=stderr_bytes,
        attempt_id=attempt_id,
        now=ref_now,
    )
    retryable = (not substantive) and classification.is_pre_substantive_reroutable

    persisted_obs_ids: list[str] = []
    # Scope B / HIGH-1: Only persist observations if the failure was NOT substantive.
    # Substantive agent prose or worktree changes cannot forge provider-wide quota exclusions.
    if not substantive:
        for obs in classification.observations_to_persist:
            record_operational_observation_idempotent(
                conn, observation_id=obs.observation_id, producer=obs.producer,
                observation_type=obs.observation_type, provider=obs.provider, profile=obs.profile,
                timestamp=obs.timestamp, expires_at=obs.expires_at, state_value=obs.state_value,
                detail=obs.detail, digest=obs.digest,
            )
            record_invocation_observation_relation(
                conn, attempt_id=attempt_id, observation_id=obs.observation_id,
                relation_type="produced_by",
            )
            persisted_obs_ids.append(obs.observation_id)

    art_path = record_provider_failure_artifact(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        binding=binding,
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        provider=provider,
        profile=profile,
        endpoint_alias=endpoint_alias,
        exit_code=exit_code,
        classification=classification,
        substantive=substantive,
        retryable=retryable,
        now=ref_now,
    )

    update_invocation_attempt(
        conn,
        attempt_id=attempt_id,
        status="failed",
        exit_code=exit_code,
        completed_at=utc_now_iso(),
    )

    return TurnFailureDisposition(
        category=classification.category,
        confidence=classification.confidence,
        substantive=substantive,
        retryable=retryable,
        observation_ids=tuple(persisted_obs_ids),
        sanitized_error=classification.sanitized_evidence_excerpt,
        reset_timestamp=classification.parsed_reset_timestamp,
        artifact_path=art_path,
        classification=classification,
    )


def orchestrate_dynamic_retry(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    run_dir: Path,
    phase_type: str,
    execution_mode: str,
    binding: ActorBinding,
    current_attempt_number: int,
    current_attempt_id: str,
    caps_catalog: Mapping[str, EndpointCapabilities],
    injected_observations: Sequence[OperationalObservation],
    prior_resolutions: Mapping[str, ResolvedActorRoute],
    disposition: TurnFailureDisposition,
    now: float | None = None,
) -> tuple[bool, ResolvedActorRoute | None, int]:
    """Orchestrate dynamic retry turn following F2/F14/F15 rules."""
    ref_now = time.time() if now is None else float(now)
    if execution_mode != "dynamic" or execution_mode in RETAINED_STATIC_MODES:
        return False, None, current_attempt_number

    if not disposition.retryable:
        record_route_decision_artifact(
            conn,
            run_id=run_id,
            run_dir=run_dir,
            binding_id=binding.binding_id,
            attempt_number=current_attempt_number + 1,
            predecessor_attempt_id=current_attempt_id,
            route=None,
            outcome="non_retryable",
            now=ref_now,
        )
        return False, None, current_attempt_number

    # Finding F14: Retry ceiling M = min(3, |routes|)
    capable_candidates = [
        ep for ep in caps_catalog.values()
        if ep.satisfies(binding.required_capabilities, requires_mutating=binding.is_mutating)
    ]
    m_bound = min(3, max(1, len(capable_candidates)))
    if current_attempt_number >= m_bound:
        for role in binding.roles:
            update_semantic_responsibility(
                conn,
                id=f"sem-{run_id}-{role}",
                status="failed",
            )
        record_route_decision_artifact(
            conn,
            run_id=run_id,
            run_dir=run_dir,
            binding_id=binding.binding_id,
            attempt_number=current_attempt_number + 1,
            predecessor_attempt_id=current_attempt_id,
            route=None,
            outcome="max_retries_exceeded",
            now=ref_now,
        )
        return False, None, current_attempt_number

    next_attempt = current_attempt_number + 1

    # Finding F2: Responsibility set to retry_pending BEFORE launching attempt N+1
    for role in binding.roles:
        update_semantic_responsibility(
            conn,
            id=f"sem-{run_id}-{role}",
            status="retry_pending",
        )

    # Finding F4/F5: Fresh observations using original injected_observations
    fresh_observations = collect_operational_observations(
        conn=conn,
        now=ref_now,
        providers=("codex", "claude", "antigravity"),
        injected=injected_observations,
    )

    try:
        next_route = resolve_dynamic_route(
            binding,
            phase_type,
            capabilities_catalog=caps_catalog,
            operational_observations=fresh_observations,
            prior_resolutions=prior_resolutions,
            now=ref_now,
        )
    except NoRouteAvailableError:
        for role in binding.roles:
            update_semantic_responsibility(
                conn,
                id=f"sem-{run_id}-{role}",
                status="failed",
            )
        record_route_decision_artifact(
            conn,
            run_id=run_id,
            run_dir=run_dir,
            binding_id=binding.binding_id,
            attempt_number=next_attempt,
            predecessor_attempt_id=current_attempt_id,
            route=None,
            outcome="exhausted",
            now=ref_now,
        )
        return False, None, current_attempt_number

    record_route_decision_artifact(
        conn,
        run_id=run_id,
        run_dir=run_dir,
        binding_id=binding.binding_id,
        attempt_number=next_attempt,
        predecessor_attempt_id=current_attempt_id,
        route=next_route,
        rejections=next_route.rejections,
        outcome="rerouted",
        now=ref_now,
    )

    next_res_id = f"res-{run_id}-{binding.binding_id}-attempt-{next_attempt}"
    record_route_resolution(
        conn, resolution_id=next_res_id, run_id=run_id, binding_id=binding.binding_id,
        attempt_number=next_attempt, provider=next_route.provider, profile=next_route.profile,
        endpoint_alias=next_route.endpoint_alias, intelligence={"provider": next_route.provider, "profile": next_route.profile},
        policy_snapshot=next_route.policy_snapshot, observation_ids=next_route.observation_ids,
        selection_rationale=next_route.selection_rationale,
    )
    next_attempt_id = f"att-{run_id}-{binding.binding_id}-{next_attempt}"
    record_invocation_attempt(
        conn, attempt_id=next_attempt_id, run_id=run_id, binding_id=binding.binding_id,
        attempt_number=next_attempt, provider=next_route.provider, profile=next_route.profile,
        endpoint_alias=next_route.endpoint_alias, status="staged",
        predecessor_attempt_id=current_attempt_id, route_resolution_id=next_res_id,
    )

    return True, next_route, next_attempt
