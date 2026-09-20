"""Conformance test scenarios for provider feedback, durable exhaustion, and dynamic routing."""

from __future__ import annotations

from typing import Any, Mapping

from agent_phase.capabilities import EndpointCapabilities
from agent_phase.dynamic_router import (
    NoRouteAvailableError,
    OperationalObservation,
    resolve_dynamic_route,
)
from agent_phase.semantic_roles import ActorBinding


def generate_feedback_scenarios(
    bindings: Mapping[str, ActorBinding],
    catalog: Mapping[str, EndpointCapabilities],
    simulated_now: float,
) -> list[dict[str, Any]]:
    """Generate dynamic routing scenarios proving provider feedback and durable exhaustion semantics."""
    scenarios: list[dict[str, Any]] = []

    # 1. Active provider-wide quota exhausted excludes every profile in that provider
    obs_codex_exhausted = OperationalObservation(
        observation_id="obs-codex-quota-exhausted-feedback",
        producer="feedback",
        observation_type="quota",
        provider="codex",
        profile=None,
        timestamp=simulated_now,
        expires_at=simulated_now + 3600.0,
        state_value="exhausted",
    )
    res_codex_exhausted = resolve_dynamic_route(
        bindings["binding_plan"],
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_codex_exhausted],
        prior_resolutions={},
        now=simulated_now,
    )
    assert res_codex_exhausted.provider != "codex"
    scenarios.append(
        {
            "id": "active_exhausted_quota_excludes_all_profiles_of_provider",
            "description": "Active provider-wide quota exhausted excludes every profile in that provider",
            "phase_type": "implementation_testing",
            "binding_id": "binding_plan",
            "required_capabilities": sorted(bindings["binding_plan"].required_capabilities),
            "is_mutating": bindings["binding_plan"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_codex_exhausted.observation_id,
                    "producer": obs_codex_exhausted.producer,
                    "observation_type": obs_codex_exhausted.observation_type,
                    "provider": obs_codex_exhausted.provider,
                    "profile": obs_codex_exhausted.profile,
                    "timestamp": obs_codex_exhausted.timestamp,
                    "expires_at": obs_codex_exhausted.expires_at,
                    "state_value": obs_codex_exhausted.state_value,
                }
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_codex_exhausted.endpoint_alias,
            "expected_provider": res_codex_exhausted.provider,
            "expected_profile": res_codex_exhausted.profile,
            "expected_rationale": res_codex_exhausted.selection_rationale,
        }
    )

    # 2. Tokenless unknown does not erase active exhausted observation
    obs_codex_unknown = OperationalObservation(
        observation_id="obs-codex-quota-unknown-probe",
        producer="probe",
        observation_type="quota",
        provider="codex",
        profile=None,
        timestamp=simulated_now,
        expires_at=None,
        state_value="unknown",
    )
    res_unknown_coexist = resolve_dynamic_route(
        bindings["binding_plan"],
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_codex_exhausted, obs_codex_unknown],
        prior_resolutions={},
        now=simulated_now,
    )
    assert res_unknown_coexist.provider != "codex"
    scenarios.append(
        {
            "id": "tokenless_unknown_does_not_erase_exhausted",
            "description": "Tokenless unknown quota probe does not erase stronger active exhausted observation",
            "phase_type": "implementation_testing",
            "binding_id": "binding_plan",
            "required_capabilities": sorted(bindings["binding_plan"].required_capabilities),
            "is_mutating": bindings["binding_plan"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_codex_exhausted.observation_id,
                    "producer": obs_codex_exhausted.producer,
                    "observation_type": obs_codex_exhausted.observation_type,
                    "provider": obs_codex_exhausted.provider,
                    "profile": obs_codex_exhausted.profile,
                    "timestamp": obs_codex_exhausted.timestamp,
                    "expires_at": obs_codex_exhausted.expires_at,
                    "state_value": obs_codex_exhausted.state_value,
                },
                {
                    "observation_id": obs_codex_unknown.observation_id,
                    "producer": obs_codex_unknown.producer,
                    "observation_type": obs_codex_unknown.observation_type,
                    "provider": obs_codex_unknown.provider,
                    "profile": obs_codex_unknown.profile,
                    "timestamp": obs_codex_unknown.timestamp,
                    "expires_at": obs_codex_unknown.expires_at,
                    "state_value": obs_codex_unknown.state_value,
                },
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_unknown_coexist.endpoint_alias,
            "expected_provider": res_unknown_coexist.provider,
            "expected_profile": res_unknown_coexist.profile,
            "expected_rationale": res_unknown_coexist.selection_rationale,
        }
    )

    # 3. Expired quota exhaustion readmits provider
    obs_codex_expired = OperationalObservation(
        observation_id="obs-codex-quota-expired",
        producer="feedback",
        observation_type="quota",
        provider="codex",
        profile=None,
        timestamp=simulated_now - 3600.0,
        expires_at=simulated_now - 100.0,
        state_value="exhausted",
    )
    res_readmitted = resolve_dynamic_route(
        bindings["binding_plan"],
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_codex_expired],
        prior_resolutions={},
        now=simulated_now,
    )
    assert res_readmitted.provider == "codex"
    scenarios.append(
        {
            "id": "expired_quota_exhaustion_readmits_codex",
            "description": "Expired quota exhaustion observation no longer excludes; codex readmitted",
            "phase_type": "implementation_testing",
            "binding_id": "binding_plan",
            "required_capabilities": sorted(bindings["binding_plan"].required_capabilities),
            "is_mutating": bindings["binding_plan"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_codex_expired.observation_id,
                    "producer": obs_codex_expired.producer,
                    "observation_type": obs_codex_expired.observation_type,
                    "provider": obs_codex_expired.provider,
                    "profile": obs_codex_expired.profile,
                    "timestamp": obs_codex_expired.timestamp,
                    "expires_at": obs_codex_expired.expires_at,
                    "state_value": obs_codex_expired.state_value,
                }
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_readmitted.endpoint_alias,
            "expected_provider": res_readmitted.provider,
            "expected_profile": res_readmitted.profile,
            "expected_rationale": res_readmitted.selection_rationale,
        }
    )

    # 4. All providers quota exhausted fails closed with no_route
    all_exhausted = [
        OperationalObservation(
            observation_id=f"obs-{p}-exhausted",
            producer="feedback",
            observation_type="quota",
            provider=p,
            timestamp=simulated_now,
            expires_at=None,
            state_value="exhausted",
        )
        for p in ("codex", "claude", "antigravity")
    ]
    try:
        resolve_dynamic_route(
            bindings["binding_plan"],
            "implementation_testing",
            capabilities_catalog=catalog,
            operational_observations=all_exhausted,
            prior_resolutions={},
            now=simulated_now,
        )
        raise AssertionError("Expected NoRouteAvailableError")
    except NoRouteAvailableError:
        scenarios.append(
            {
                "id": "all_providers_quota_exhausted_fails_closed",
                "description": "All providers quota exhausted raises NoRouteAvailableError",
                "phase_type": "implementation_testing",
                "binding_id": "binding_plan",
                "required_capabilities": sorted(bindings["binding_plan"].required_capabilities),
                "is_mutating": bindings["binding_plan"].is_mutating,
                "observations": [
                    {
                        "observation_id": o.observation_id,
                        "producer": o.producer,
                        "observation_type": o.observation_type,
                        "provider": o.provider,
                        "profile": o.profile,
                        "timestamp": o.timestamp,
                        "expires_at": o.expires_at,
                        "state_value": o.state_value,
                    }
                    for o in all_exhausted
                ],
                "prior_resolutions": {},
                "now": simulated_now,
                "expected_winner": "",
                "expected_provider": "",
                "expected_profile": "",
                "expected_rationale": "",
                "expected_error": "no_route",
            }
        )

    # 5. Profile-specific quota exhaustion excludes only matching profile
    obs_profile_codex_review = OperationalObservation(
        observation_id="obs-codex-review-quota-exhausted",
        producer="feedback",
        observation_type="quota",
        provider="codex",
        profile="codex_review",
        timestamp=simulated_now,
        expires_at=simulated_now + 3600.0,
        state_value="exhausted",
    )
    # 5a. For read-only binding_plan, codex-review is excluded, claude-review wins
    res_plan_profile_excl = resolve_dynamic_route(
        bindings["binding_plan"],
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_profile_codex_review],
        prior_resolutions={},
        now=simulated_now,
    )
    assert res_plan_profile_excl.endpoint_alias != "codex-review"
    scenarios.append(
        {
            "id": "profile_specific_quota_exhaustion_excludes_matching_profile",
            "description": "Profile-specific quota exhaustion excludes matching profile from route selection",
            "phase_type": "implementation_testing",
            "binding_id": "binding_plan",
            "required_capabilities": sorted(bindings["binding_plan"].required_capabilities),
            "is_mutating": bindings["binding_plan"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_profile_codex_review.observation_id,
                    "producer": obs_profile_codex_review.producer,
                    "observation_type": obs_profile_codex_review.observation_type,
                    "provider": obs_profile_codex_review.provider,
                    "profile": obs_profile_codex_review.profile,
                    "timestamp": obs_profile_codex_review.timestamp,
                    "expires_at": obs_profile_codex_review.expires_at,
                    "state_value": obs_profile_codex_review.state_value,
                }
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_plan_profile_excl.endpoint_alias,
            "expected_provider": res_plan_profile_excl.provider,
            "expected_profile": res_plan_profile_excl.profile,
            "expected_rationale": res_plan_profile_excl.selection_rationale,
        }
    )

    # 5b. For mutating binding_work, codex_implementation is NOT excluded by codex_review exhaustion
    res_work_profile_admit = resolve_dynamic_route(
        bindings["binding_work"],
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_profile_codex_review],
        prior_resolutions={},
        now=simulated_now,
    )
    assert res_work_profile_admit.provider == "codex"
    assert res_work_profile_admit.profile == "codex_implementation"
    scenarios.append(
        {
            "id": "profile_specific_quota_exhaustion_admits_other_profile_of_same_provider",
            "description": "Profile-specific quota exhaustion on review profile does not exclude implementation profile",
            "phase_type": "implementation_testing",
            "binding_id": "binding_work",
            "required_capabilities": sorted(bindings["binding_work"].required_capabilities),
            "is_mutating": bindings["binding_work"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_profile_codex_review.observation_id,
                    "producer": obs_profile_codex_review.producer,
                    "observation_type": obs_profile_codex_review.observation_type,
                    "provider": obs_profile_codex_review.provider,
                    "profile": obs_profile_codex_review.profile,
                    "timestamp": obs_profile_codex_review.timestamp,
                    "expires_at": obs_profile_codex_review.expires_at,
                    "state_value": obs_profile_codex_review.state_value,
                }
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_work_profile_admit.endpoint_alias,
            "expected_provider": res_work_profile_admit.provider,
            "expected_profile": res_work_profile_admit.profile,
            "expected_rationale": res_work_profile_admit.selection_rationale,
        }
    )

    # 6. Deterministic next route selection
    # When codex is exhausted on binding_work, verify deterministic fallback to antigravity-primary
    res_work_codex_excl = resolve_dynamic_route(
        bindings["binding_work"],
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_codex_exhausted],
        prior_resolutions={},
        now=simulated_now,
    )
    assert res_work_codex_excl.endpoint_alias == "antigravity-primary"
    scenarios.append(
        {
            "id": "deterministic_next_route_selection_on_exhaustion",
            "description": "Deterministic next route selection falls back to antigravity-primary on codex exhaustion",
            "phase_type": "implementation_testing",
            "binding_id": "binding_work",
            "required_capabilities": sorted(bindings["binding_work"].required_capabilities),
            "is_mutating": bindings["binding_work"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_codex_exhausted.observation_id,
                    "producer": obs_codex_exhausted.producer,
                    "observation_type": obs_codex_exhausted.observation_type,
                    "provider": obs_codex_exhausted.provider,
                    "profile": obs_codex_exhausted.profile,
                    "timestamp": obs_codex_exhausted.timestamp,
                    "expires_at": obs_codex_exhausted.expires_at,
                    "state_value": obs_codex_exhausted.state_value,
                }
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_work_codex_excl.endpoint_alias,
            "expected_provider": res_work_codex_excl.provider,
            "expected_profile": res_work_codex_excl.profile,
            "expected_rationale": res_work_codex_excl.selection_rationale,
        }
    )

    return scenarios
