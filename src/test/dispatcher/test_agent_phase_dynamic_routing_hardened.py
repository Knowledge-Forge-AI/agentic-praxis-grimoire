"""Qualification tests for hardened dynamic routing and operational observation precedence."""

from __future__ import annotations

import time
import pytest

from agent_phase.capabilities import EndpointCapabilities
from agent_phase.dynamic_router import (
    NoRouteAvailableError,
    OperationalObservation,
    ResolvedActorRoute,
    RoutingResolutionError,
    resolve_dynamic_route,
    resolve_static_preset_route,
)
from agent_phase.semantic_roles import (
    ROLE_PLAN_REVIEWER,
    ROLE_PLANNER,
    ROLE_PRODUCER,
    ActorBinding,
)


def make_ep(
    alias: str,
    provider: str,
    profile: str,
    caps: set[str],
    posture: str = "mutating",
) -> EndpointCapabilities:
    return EndpointCapabilities(
        endpoint_alias=alias,
        provider=provider,
        profile=profile,
        capabilities=frozenset(caps),
        posture=posture,
    )


def test_precedence_stage1_capability_fails_closed() -> None:
    catalog = {
        "ep-1": make_ep("ep-1", "codex", "model-a", {"read"}),
    }
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    with pytest.raises(NoRouteAvailableError, match="no capability-eligible routes"):
        resolve_dynamic_route(binding, "implementation_testing", capabilities_catalog=catalog)


def test_precedence_stage2_hard_unavailable_and_unusable() -> None:
    catalog = {
        "ep-1": make_ep("ep-1", "codex", "model-a", {"read", "mutation", "execution"}),
        "ep-2": make_ep("ep-2", "claude", "model-b", {"read", "mutation", "execution"}),
    }
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    obs_unavail = OperationalObservation(
        observation_id="obs-1",
        producer="probe",
        observation_type="availability",
        provider="codex",
        state_value="unavailable",
    )
    route = resolve_dynamic_route(
        binding, "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_unavail],
    )
    assert route.provider == "claude"


def test_precedence_stage2_authentication_unusable() -> None:
    catalog = {
        "ep-1": make_ep("ep-1", "codex", "model-a", {"read", "mutation", "execution"}),
        "ep-2": make_ep("ep-2", "claude", "model-b", {"read", "mutation", "execution"}),
    }
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    obs_auth = OperationalObservation(
        observation_id="obs-auth",
        producer="probe",
        observation_type="authentication",
        provider="codex",
        state_value="unusable",
    )
    route = resolve_dynamic_route(
        binding, "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_auth],
    )
    assert route.provider == "claude"


def test_precedence_stage3_quota_exhausted_excludes_but_unknown_admits() -> None:
    catalog = {
        "ep-1": make_ep("ep-1", "codex", "model-a", {"read", "mutation", "execution"}),
        "ep-2": make_ep("ep-2", "claude", "model-b", {"read", "mutation", "execution"}),
    }
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    obs_exhausted = OperationalObservation(
        observation_id="obs-quota-1",
        producer="probe",
        observation_type="quota",
        provider="codex",
        state_value="exhausted",
    )
    obs_unknown = OperationalObservation(
        observation_id="obs-quota-2",
        producer="probe",
        observation_type="quota",
        provider="claude",
        state_value="unknown",
    )
    route = resolve_dynamic_route(
        binding, "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_exhausted, obs_unknown],
    )
    # Claude is admitted fail-open under unknown quota; Codex is excluded
    assert route.provider == "claude"


def test_precedence_stage4_active_cooldown_excludes() -> None:
    now = time.time()
    catalog = {
        "ep-1": make_ep("ep-1", "codex", "model-a", {"read", "mutation", "execution"}),
        "ep-2": make_ep("ep-2", "claude", "model-b", {"read", "mutation", "execution"}),
    }
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    obs_cool = OperationalObservation(
        observation_id="obs-cool-1",
        producer="probe",
        observation_type="cooldown",
        provider="codex",
        state_value="active_cooldown",
        expires_at=now + 300,
    )
    route = resolve_dynamic_route(
        binding, "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_cool],
    )
    assert route.provider == "claude"


def test_precedence_stage5_reviewer_independence() -> None:
    catalog = {
        "ep-codex": make_ep("ep-codex", "codex", "model-a", {"read", "reasoning"}, posture="read_only"),
        "ep-claude": make_ep("ep-claude", "claude", "model-b", {"read", "reasoning"}, posture="read_only"),
    }
    prior = {
        "binding_plan": ResolvedActorRoute(
            binding_id="binding_plan",
            provider="codex",
            profile="model-a",
            endpoint_alias="ep-codex",
            capabilities=frozenset({"read", "reasoning"}),
            selection_rationale="planner",
            roles=(ROLE_PLANNER,),
        )
    }
    binding = ActorBinding.create("binding_plan_review", (ROLE_PLAN_REVIEWER,))
    route = resolve_dynamic_route(
        binding, "implementation_testing",
        capabilities_catalog=catalog,
        prior_resolutions=prior,
    )
    assert route.provider != "codex"
    assert route.provider == "claude"


def test_precedence_stage6_ranking_scoring_bonuses() -> None:
    catalog = {
        "ep-1": make_ep("ep-1", "codex", "generic-a", {"read", "mutation", "execution"}),
        "ep-2": make_ep("ep-2", "codex", "generic-b", {"read", "mutation", "execution"}),
    }
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))
    obs_healthy = OperationalObservation(
        observation_id="obs-healthy",
        producer="probe",
        observation_type="quota",
        provider="codex",
        profile="generic-a",
        state_value="healthy",
    )
    route = resolve_dynamic_route(
        binding, "sysadmin",
        capabilities_catalog=catalog,
        operational_observations=[obs_healthy],
    )
    assert route.endpoint_alias == "ep-1"


def test_static_preset_refuses_unmerged_binding() -> None:
    unmerged_binding = ActorBinding.create("binding_planner", (ROLE_PLANNER,))
    with pytest.raises(RoutingResolutionError, match="unsupported binding"):
        resolve_static_preset_route(unmerged_binding, "implementation_testing", "normal")
