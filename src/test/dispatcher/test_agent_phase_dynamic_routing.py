from __future__ import annotations

from pathlib import Path
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
    ActorBinding,
    ROLE_CLOSEOUT_AGENT,
    ROLE_PLAN_REVIEWER,
    ROLE_PLANNER,
    ROLE_PRODUCER,
    ROLE_WORK_REVIEWER,
)


def make_mock_endpoint(
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


def test_capability_eligibility_fails_closed() -> None:
    catalog = {
        "ep-read-only": make_mock_endpoint(
            "ep-read-only", "claude", "claude-3-7-sonnet", {"read", "reasoning"}, posture="read_only"
        ),
    }

    # Binding requires mutation and execution (Producer)
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))

    with pytest.raises(NoRouteAvailableError, match="no capability-eligible routes"):
        resolve_dynamic_route(
            binding,
            "implementation_testing",
            capabilities_catalog=catalog,
        )


def test_reviewer_independence_plan_review() -> None:
    catalog = {
        "claude-ep": make_mock_endpoint(
            "claude-ep", "claude", "claude-3-7-sonnet", {"read", "reasoning"}, posture="read_only"
        ),
        "codex-ep": make_mock_endpoint(
            "codex-ep", "codex", "gpt-5-codex", {"read", "reasoning"}, posture="read_only"
        ),
    }

    # Planner route was already chosen with Claude
    prior = {
        "binding_plan": ResolvedActorRoute(
            binding_id="binding_plan",
            provider="claude",
            profile="claude-3-7-sonnet",
            endpoint_alias="claude-ep",
            capabilities=frozenset({"read", "reasoning"}),
            selection_rationale="test",
        )
    }

    # Plan reviewer MUST NOT be Claude
    binding = ActorBinding.create("binding_plan_review", (ROLE_PLAN_REVIEWER,))
    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        prior_resolutions=prior,
    )
    assert route.provider == "codex"
    assert route.endpoint_alias == "codex-ep"


def test_reviewer_independence_work_review() -> None:
    catalog = {
        "claude-ep": make_mock_endpoint(
            "claude-ep", "claude", "claude-3-7-sonnet", {"read", "reasoning"}, posture="read_only"
        ),
        "codex-ep": make_mock_endpoint(
            "codex-ep", "codex", "gpt-5-codex", {"read", "reasoning"}, posture="read_only"
        ),
    }

    # Producer was Codex
    prior = {
        "binding_work": ResolvedActorRoute(
            binding_id="binding_work",
            provider="codex",
            profile="gpt-5-codex",
            endpoint_alias="codex-ep",
            capabilities=frozenset({"read", "mutation", "execution"}),
            selection_rationale="test",
        )
    }

    # Work Reviewer MUST NOT be Codex
    binding = ActorBinding.create("binding_work_review", (ROLE_WORK_REVIEWER,))
    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        prior_resolutions=prior,
    )
    assert route.provider == "claude"
    assert route.endpoint_alias == "claude-ep"


def test_operational_observations_filter_unavailable_and_cooldown() -> None:
    catalog = {
        "codex-1": make_mock_endpoint(
            "codex-1", "codex", "gpt-5-codex", {"read", "mutation", "execution"}
        ),
        "codex-2": make_mock_endpoint(
            "codex-2", "codex", "gpt-5-codex-fast", {"read", "mutation", "execution"}
        ),
    }

    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))

    # Observation marking codex-1 in active cooldown
    now = time.time()
    obs_cooldown = OperationalObservation(
        observation_id="obs-cool-1",
        producer="supervisor",
        observation_type="cooldown",
        provider="codex",
        profile="gpt-5-codex",
        timestamp=now,
        expires_at=now + 300,
        state_value="cooldown",
    )

    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_cooldown],
    )
    # Must pick codex-2 since codex-1 is in cooldown
    assert route.endpoint_alias == "codex-2"
    assert "obs-cool-1" in route.observation_ids


def test_unknown_quota_admitted_without_speculative_blocking() -> None:
    catalog = {
        "codex-1": make_mock_endpoint(
            "codex-1", "codex", "gpt-5-codex", {"read", "mutation", "execution"}
        ),
    }

    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))

    # Observation with unknown quota
    obs_unknown = OperationalObservation(
        observation_id="obs-quota-unknown",
        producer="quota_monitor",
        observation_type="quota",
        provider="codex",
        state_value="unknown",
    )

    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_unknown],
    )
    # Must succeed and not block
    assert route.endpoint_alias == "codex-1"


def test_deterministic_ranking_and_tie_breaking() -> None:
    # Multiple identical endpoints must sort lexically by endpoint_alias
    catalog = {
        "z-endpoint": make_mock_endpoint(
            "z-endpoint", "codex", "gpt-5", {"read", "reasoning"}, posture="read_only"
        ),
        "a-endpoint": make_mock_endpoint(
            "a-endpoint", "codex", "gpt-5", {"read", "reasoning"}, posture="read_only"
        ),
    }

    binding = ActorBinding.create("binding_plan", (ROLE_PLANNER,))
    r1 = resolve_dynamic_route(binding, "implementation_testing", capabilities_catalog=catalog)
    r2 = resolve_dynamic_route(binding, "implementation_testing", capabilities_catalog=catalog)

    assert r1.endpoint_alias == "a-endpoint"
    assert r2.endpoint_alias == "a-endpoint"
    assert r1 == r2


def test_reviewer_independence_no_prefix_collision() -> None:
    catalog = {
        "claude-ep": make_mock_endpoint(
            "claude-ep", "claude", "claude-3-7-sonnet", {"read", "reasoning"}, posture="read_only"
        ),
        "codex-ep": make_mock_endpoint(
            "codex-ep", "codex", "gpt-5-codex", {"read", "reasoning"}, posture="read_only"
        ),
        "antigravity-ep": make_mock_endpoint(
            "antigravity-ep", "antigravity", "gemini-3.8-flash-high", {"read", "reasoning"}, posture="read_only"
        ),
    }

    # Simulate full prior history where both planner and plan_reviewer, producer and work_reviewer exist
    prior = {
        "binding_plan": ResolvedActorRoute(
            binding_id="binding_plan",
            provider="codex",
            profile="gpt-5-codex",
            endpoint_alias="codex-ep",
            capabilities=frozenset({"read", "reasoning"}),
            selection_rationale="plan",
            roles=(ROLE_PLANNER,),
        ),
        "binding_plan_review": ResolvedActorRoute(
            binding_id="binding_plan_review",
            provider="claude",
            profile="claude-3-7-sonnet",
            endpoint_alias="claude-ep",
            capabilities=frozenset({"read", "reasoning"}),
            selection_rationale="plan_review",
            roles=(ROLE_PLAN_REVIEWER,),
        ),
        "binding_work": ResolvedActorRoute(
            binding_id="binding_work",
            provider="antigravity",
            profile="gemini-3.8-flash-high",
            endpoint_alias="antigravity-ep",
            capabilities=frozenset({"read", "mutation", "execution"}),
            selection_rationale="work",
            roles=(ROLE_PRODUCER,),
        ),
    }

    # Work review must NOT be antigravity (producer). Should pick claude or codex, definitely not antigravity.
    binding = ActorBinding.create("binding_work_review", (ROLE_WORK_REVIEWER,))
    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        prior_resolutions=prior,
    )
    assert route.provider != "antigravity"
    assert route.provider in ("claude", "codex")


def test_planner_posture_allows_mutating_capable_endpoint() -> None:
    catalog = {
        "codex-arch": make_mock_endpoint(
            "codex-arch", "codex", "codex-architecture-docs-primary",
            {"read", "mutation", "execution", "reasoning", "structured_output"},
            posture="mutating",
        ),
    }
    binding = ActorBinding.create("binding_plan", (ROLE_PLANNER,))
    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
    )
    assert route.endpoint_alias == "codex-arch"
    assert route.provider == "codex"


def test_static_presets_equivalence_all_ten_retained_modes() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    retained_modes = (
        "normal",
        "gemini_sub",
        "gemini_flash_sub",
        "gemini_flash_opus_sub",
        "conserve_claude",
        "claude_only",
        "codex_only",
        "gemini_only",
        "gemini_opus",
        "gemini_fable",
    )
    bindings = (
        ActorBinding.create("binding_plan", (ROLE_PLANNER,)),
        ActorBinding.create("binding_plan_review", (ROLE_PLAN_REVIEWER,)),
        ActorBinding.create("binding_work", (ROLE_PRODUCER,)),
        ActorBinding.create("binding_work_review", (ROLE_WORK_REVIEWER,)),
        ActorBinding.create("binding_closeout", (ROLE_CLOSEOUT_AGENT,)),
    )
    for mode in retained_modes:
        for binding in bindings:
            route = resolve_static_preset_route(
                binding,
                "implementation_testing",
                mode,
                root=repo_root,
            )
            assert route.binding_id == binding.binding_id
            assert route.provider in ("codex", "claude", "antigravity", "fable")
            assert len(route.endpoint_alias) > 0
            assert len(route.capabilities) > 0

    with pytest.raises(RoutingResolutionError, match="unknown static route key"):
        resolve_static_preset_route(
            bindings[0],
            "nonexistent_phase",
            "codex_only",
            root=repo_root,
        )
