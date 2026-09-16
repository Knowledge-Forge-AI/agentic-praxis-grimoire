"""Bounded deterministic dynamic router and static preset resolver.

Evaluates capability eligibility (fails closed), reviewer independence,
and bounded operational observations before provider launch.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Mapping, Sequence

from .capabilities import EndpointCapabilities, load_capabilities
from .roster import RosterSnapshot, load_roster
from .semantic_roles import (
    ActorBinding,
    ROLE_PLANNER,
    ROLE_PLAN_REVIEWER,
    ROLE_PRODUCER,
    ROLE_REVISER,
    ROLE_WORK_REVIEWER,
)


class RoutingResolutionError(RuntimeError):
    """Raised when no capability-eligible or independent route can be selected."""


class NoRouteAvailableError(RoutingResolutionError):
    """Specific error when all potential routes fail eligibility or operational criteria."""


@dataclass(frozen=True)
class OperationalObservation:
    observation_id: str
    producer: str
    observation_type: str  # "availability", "authentication", "cooldown", "quota"
    provider: str
    profile: str | None = None
    timestamp: float = 0.0
    expires_at: float | None = None
    state_value: str = "available"  # "available", "unavailable", "usable", "unusable", "healthy", "constrained", "exhausted", "active_cooldown", "cooldown", "unknown"
    detail: Mapping[str, Any] | None = None
    digest: str | None = None

    def __post_init__(self) -> None:
        if self.digest is None:
            import hashlib
            import json
            payload = {
                "detail": dict(self.detail) if self.detail else None,
                "expires_at": float(self.expires_at) if self.expires_at is not None else None,
                "observation_id": self.observation_id,
                "observation_type": self.observation_type,
                "producer": self.producer,
                "profile": self.profile,
                "provider": self.provider,
                "state_value": self.state_value,
                "timestamp": float(self.timestamp),
            }
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            object.__setattr__(self, "digest", hashlib.sha256(raw).hexdigest())

    @property
    def is_active(self) -> bool:
        if self.expires_at is None:
            return True
        return time.time() < self.expires_at

    def is_active_at(self, ref_now: float | None = None) -> bool:
        if self.expires_at is None:
            return True
        check_time = time.time() if ref_now is None else float(ref_now)
        return check_time < self.expires_at


@dataclass(frozen=True)
class ResolvedActorRoute:
    binding_id: str
    provider: str
    profile: str
    endpoint_alias: str
    capabilities: frozenset[str]
    selection_rationale: str
    roles: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    policy_snapshot: Mapping[str, Any] | None = None
    rejections: Mapping[str, str] | None = None

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "binding_id": self.binding_id,
            "provider": self.provider,
            "profile": self.profile,
            "endpoint_alias": self.endpoint_alias,
            "capabilities": sorted(self.capabilities),
            "selection_rationale": self.selection_rationale,
            "roles": list(self.roles),
            "observation_ids": list(self.observation_ids),
        }
        if self.rejections is not None:
            d["rejections"] = dict(self.rejections)
        return d


def _phase_affinity(phase_type: str, provider: str, profile: str) -> int:
    score = 0
    if phase_type == "implementation_testing":
        if "implementation" in profile:
            score += 20
        if provider == "codex":
            score += 10
        elif provider == "antigravity":
            score += 8
    elif phase_type == "architecture_docs":
        if "architecture" in profile or "docs" in profile:
            score += 20
        if provider == "claude":
            score += 10
        elif provider == "codex":
            score += 8
    elif phase_type == "sysadmin":
        if "sysadmin" in profile:
            score += 20
        if provider == "claude":
            score += 10
        elif provider == "codex":
            score += 8
    return score


def _role_affinity(binding: ActorBinding, endpoint: EndpointCapabilities) -> int:
    score = 0
    is_review_turn = any(r in (ROLE_PLAN_REVIEWER, ROLE_WORK_REVIEWER) for r in binding.roles)
    is_producer_turn = any(r in (ROLE_PRODUCER, ROLE_REVISER) for r in binding.roles)

    if is_review_turn:
        if endpoint.is_read_only:
            score += 15
        if "review" in endpoint.endpoint_alias:
            score += 15
    elif is_producer_turn:
        if endpoint.is_mutating:
            score += 15
        if "primary" in endpoint.endpoint_alias or "testing" in endpoint.endpoint_alias:
            score += 10
    return score


def resolve_dynamic_route(
    binding: ActorBinding,
    phase_type: str,
    *,
    capabilities_catalog: Mapping[str, EndpointCapabilities],
    operational_observations: Sequence[OperationalObservation] = (),
    prior_resolutions: Mapping[str, ResolvedActorRoute] | None = None,
    now: float | None = None,
) -> ResolvedActorRoute:
    """Resolve an actor binding turn dynamically with fail-closed capability checking."""
    prior = prior_resolutions or {}
    candidates: list[EndpointCapabilities] = list(capabilities_catalog.values())

    # 1. Capability Eligibility (Fails Closed)
    capable: list[EndpointCapabilities] = []
    rejections: dict[str, str] = {}
    for ep in candidates:
        if not ep.satisfies(
            binding.required_capabilities,
            requires_mutating=binding.is_mutating,
        ):
            rejections[ep.endpoint_alias] = (
                f"missing required capabilities {sorted(binding.required_capabilities - ep.capabilities)} "
                f"or posture conflict (ep: {ep.posture}, binding mutating: {binding.is_mutating})"
            )
            continue
        capable.append(ep)

    if not capable:
        raise NoRouteAvailableError(
            f"no capability-eligible routes for binding {binding.binding_id!r} "
            f"with required {sorted(binding.required_capabilities)}. Rejections: {rejections}"
        )

    active_observations = [obs for obs in operational_observations if obs.is_active_at(now)]
    used_obs_ids: list[str] = []

    # 2. Hard Unusable / Unavailable Exclusions
    usable: list[EndpointCapabilities] = []
    for ep in capable:
        excluded = False
        for obs in active_observations:
            applies = (obs.provider == ep.provider) and (obs.profile is None or obs.profile == ep.profile)
            if not applies:
                continue
            used_obs_ids.append(obs.observation_id)
            if obs.observation_type == "availability" and obs.state_value == "unavailable":
                rejections[ep.endpoint_alias] = f"marked unavailable by observation {obs.observation_id}"
                excluded = True
                break
            if obs.observation_type == "authentication" and obs.state_value == "unusable":
                rejections[ep.endpoint_alias] = f"authentication marked unusable by observation {obs.observation_id}"
                excluded = True
                break
        if not excluded:
            usable.append(ep)

    if not usable:
        raise NoRouteAvailableError(
            f"no available or usable routes for binding {binding.binding_id!r}. Rejections: {rejections}"
        )

    # 3. Explicit Exhausted Quota Exclusion
    quota_eligible: list[EndpointCapabilities] = []
    for ep in usable:
        excluded = False
        for obs in active_observations:
            applies = (obs.provider == ep.provider) and (obs.profile is None or obs.profile == ep.profile)
            if not applies:
                continue
            used_obs_ids.append(obs.observation_id)
            if obs.observation_type == "quota" and obs.state_value == "exhausted":
                rejections[ep.endpoint_alias] = f"quota exhausted per observation {obs.observation_id}"
                excluded = True
                break
            # unknown quota is admitted per ADR 0060/0064 §4 without speculative blocking
        if not excluded:
            quota_eligible.append(ep)

    if not quota_eligible:
        raise NoRouteAvailableError(
            f"no unexhausted quota routes for binding {binding.binding_id!r}. Rejections: {rejections}"
        )

    # 4. Active Typed Cooldown Exclusion
    non_cooldown: list[EndpointCapabilities] = []
    for ep in quota_eligible:
        excluded = False
        for obs in active_observations:
            applies = (obs.provider == ep.provider) and (obs.profile is None or obs.profile == ep.profile)
            if not applies:
                continue
            used_obs_ids.append(obs.observation_id)
            if obs.observation_type == "cooldown" and obs.state_value in ("cooldown", "active_cooldown"):
                rejections[ep.endpoint_alias] = f"in active failure cooldown until {obs.expires_at}"
                excluded = True
                break
        if not excluded:
            non_cooldown.append(ep)

    if not non_cooldown:
        raise NoRouteAvailableError(
            f"no operational routes available for binding {binding.binding_id!r}. Rejections: {rejections}"
        )

    # 5. Reviewer Independence Invariants
    independent: list[EndpointCapabilities] = []
    planner_provider: str | None = None
    producer_provider: str | None = None

    for prior_route in prior.values():
        prior_roles = getattr(prior_route, "roles", ())
        if not prior_roles and isinstance(prior_route, dict):
            prior_roles = prior_route.get("roles", ())
        prior_binding_id = getattr(prior_route, "binding_id", "")
        if isinstance(prior_route, dict):
            prior_binding_id = prior_route.get("binding_id", "")
        prior_provider = getattr(prior_route, "provider", None)
        if isinstance(prior_route, dict):
            prior_provider = prior_route.get("provider")

        if ROLE_PLANNER in prior_roles or prior_binding_id == "binding_plan":
            planner_provider = prior_provider
        if ROLE_PRODUCER in prior_roles or prior_binding_id == "binding_work":
            producer_provider = prior_provider

    is_plan_review = ROLE_PLAN_REVIEWER in binding.roles
    is_work_review = ROLE_WORK_REVIEWER in binding.roles

    for ep in non_cooldown:
        if is_plan_review and planner_provider is not None:
            if ep.provider == planner_provider:
                rejections[ep.endpoint_alias] = f"violates plan reviewer independence (planner: {planner_provider})"
                continue
        if is_work_review and producer_provider is not None:
            if ep.provider == producer_provider:
                rejections[ep.endpoint_alias] = f"violates work reviewer independence (producer: {producer_provider})"
                continue
        independent.append(ep)

    if not independent:
        raise NoRouteAvailableError(
            f"no independent review routes for binding {binding.binding_id!r}. Rejections: {rejections}"
        )

    # 6. Deterministic Ranking & Lexical Tie-Breaking
    scored: list[tuple[int, str, str, str, EndpointCapabilities]] = []
    for ep in independent:
        score = _phase_affinity(phase_type, ep.provider, ep.profile) + _role_affinity(binding, ep)
        avail_obs_found = False
        for obs in active_observations:
            applies = (obs.provider == ep.provider) and (obs.profile is None or obs.profile == ep.profile)
            if not applies:
                continue
            if obs.observation_type == "availability":
                avail_obs_found = True
                if obs.state_value == "available":
                    score += 10
                elif obs.state_value == "unknown":
                    score -= 5
            elif obs.observation_type == "quota":
                if obs.state_value == "healthy":
                    score += 5
                elif obs.state_value == "constrained":
                    score -= 10
        if not avail_obs_found and active_observations:
            score -= 10
        # Lexical tie-breaker tuple: (-score, provider, profile, alias)
        scored.append((-score, ep.provider, ep.profile, ep.endpoint_alias, ep))

    scored.sort()
    winner = scored[0][4]
    rationale = f"selected with score {-scored[0][0]} for {binding.binding_id} ({phase_type})"

    return ResolvedActorRoute(
        binding_id=binding.binding_id,
        provider=winner.provider,
        profile=winner.profile,
        endpoint_alias=winner.endpoint_alias,
        capabilities=winner.capabilities,
        selection_rationale=rationale,
        roles=tuple(binding.roles),
        observation_ids=tuple(sorted(set(used_obs_ids))),
        policy_snapshot={"phase_type": phase_type, "roles": list(binding.roles)},
        rejections=dict(rejections) if rejections else None,
    )


def resolve_static_preset_route(
    binding: ActorBinding,
    phase_type: str,
    execution_mode: str,
    roster: RosterSnapshot | None = None,
    root: Path | None = None,
) -> ResolvedActorRoute:
    """Resolve a binding turn deterministically from the V1 static route tables."""
    repo_root = root or Path.cwd()
    snap = roster or load_roster(repo_root)
    # Map standard binding to V1 routing slot
    slot_map = {
        "binding_plan": "plan",
        "binding_plan_review": "plan_review",
        "binding_work": "work",
        "binding_work_review": "final_review",
        "binding_closeout": "closeout",
    }
    slot = slot_map.get(binding.binding_id)
    if slot is None:
        raise RoutingResolutionError(
            f"unsupported binding {binding.binding_id!r} for static preset route in mode {execution_mode!r}"
        )
    key = (phase_type, execution_mode)
    if key not in snap.routes:
        raise RoutingResolutionError(f"unknown static route key: {key}")
    route_table = snap.routes[key]
    alias = route_table.get(slot)
    if not alias or alias not in snap.endpoints:
        raise RoutingResolutionError(f"no endpoint alias for slot {slot!r} in static mode {execution_mode!r}")
    endpoint = snap.endpoints[alias]
    capabilities = load_capabilities(repo_root)
    ep_caps = capabilities.get(alias)
    if ep_caps is None:
        raise RoutingResolutionError(f"endpoint {alias!r} lacks capability declaration in capabilities catalog")
    caps = ep_caps.capabilities

    return ResolvedActorRoute(
        binding_id=binding.binding_id,
        provider=endpoint.provider,
        profile=endpoint.profile,
        endpoint_alias=alias,
        capabilities=caps,
        selection_rationale=f"static preset from route table for mode {execution_mode!r}",
        roles=tuple(binding.roles),
        observation_ids=(),
        policy_snapshot={"execution_mode": execution_mode, "slot": slot},
    )
