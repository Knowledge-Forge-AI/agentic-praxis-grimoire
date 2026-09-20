"""Unit tests for probe collection precedence, dominance, and expiration filtering."""

from __future__ import annotations

from pathlib import Path
import pytest

from agent_phase.capabilities import EndpointCapabilities
from agent_phase.dynamic_router import (
    NoRouteAvailableError,
    OperationalObservation,
    resolve_dynamic_route,
)
from agent_phase.persistence import (
    open_dispatcher_db,
    record_operational_observation,
    record_run,
)
from agent_phase.probes import (
    collect_operational_observations,
)
from agent_phase.semantic_roles import ActorBinding, ROLE_PRODUCER


def _make_endpoint(alias: str, provider: str, profile: str) -> EndpointCapabilities:
    return EndpointCapabilities(
        endpoint_alias=alias,
        provider=provider,
        profile=profile,
        capabilities=frozenset({"read", "mutation", "execution", "reasoning"}),
        posture="mutating",
    )


def test_injected_observation_overrides_probes() -> None:
    """Injected observation suppresses probe generation for the same provider and type."""
    injected_obs = OperationalObservation(
        observation_id="inj-quota-codex-1",
        producer="operator_manual",
        observation_type="quota",
        provider="codex",
        timestamp=1000.0,
        expires_at=2000.0,
        state_value="exhausted",
        detail={"source": "operator"},
    )

    observations = collect_operational_observations(
        conn=None,
        now=1500.0,
        providers=("codex",),
        injected=(injected_obs,),
    )

    codex_quota = [obs for obs in observations if obs.provider == "codex" and obs.observation_type == "quota"]
    assert len(codex_quota) == 1
    assert codex_quota[0].observation_id == "inj-quota-codex-1"
    assert codex_quota[0].state_value == "exhausted"
    assert codex_quota[0].producer == "operator_manual"
    assert codex_quota[0].digest is not None


def test_injected_observation_precedence_over_durable(tmp_path: Path) -> None:
    """Injected observations appear ahead of durable observations and preserve operator authority."""
    conn = open_dispatcher_db(tmp_path / "test.db")
    run_id = "run-test-1"
    record_run(
        conn,
        run_id=run_id,
        project="test",
        request_schema="agent-phase-request-v2",
        request_digest="dig1",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    # Durable observation says healthy
    record_operational_observation(
        conn,
        observation_id="durable-quota-codex",
        producer="telemetry",
        observation_type="quota",
        provider="codex",
        state_value="healthy",
        timestamp=1000.0,
        expires_at=2000.0,
        digest="orig_digest",
    )

    # Injected observation says exhausted
    injected_obs = OperationalObservation(
        observation_id="inj-quota-codex",
        producer="operator_override",
        observation_type="quota",
        provider="codex",
        timestamp=1100.0,
        expires_at=2500.0,
        state_value="exhausted",
    )

    observations = collect_operational_observations(
        conn=conn,
        now=1500.0,
        providers=("codex",),
        injected=(injected_obs,),
    )

    obs_ids = [o.observation_id for o in observations]
    assert "inj-quota-codex" in obs_ids
    inj = next(o for o in observations if o.observation_id == "inj-quota-codex")
    assert inj.state_value == "exhausted"


def test_active_exhausted_dominates_unknown() -> None:
    """Active quota exhaustion eliminates endpoint, while unknown state is admitted fail-open."""
    catalog = {
        "codex-ep": _make_endpoint("codex-ep", "codex", "gpt-5-codex"),
        "claude-ep": _make_endpoint("claude-ep", "claude", "claude-3-7-sonnet"),
    }
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))

    # Without exhaustion, codex is preferred for implementation_testing
    route1 = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=(),
        now=1000.0,
    )
    assert route1.provider == "codex"

    # With unknown quota, still admitted
    obs_unknown = OperationalObservation(
        observation_id="obs-unknown",
        producer="probe",
        observation_type="quota",
        provider="codex",
        state_value="unknown",
        timestamp=1000.0,
        expires_at=2000.0,
    )
    route2 = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=(obs_unknown,),
        now=1500.0,
    )
    assert route2.provider == "codex"

    # With active exhausted quota, codex is excluded and fallback is selected
    obs_exhausted = OperationalObservation(
        observation_id="obs-exhausted",
        producer="probe",
        observation_type="quota",
        provider="codex",
        state_value="exhausted",
        timestamp=1000.0,
        expires_at=2000.0,
    )
    route3 = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=(obs_exhausted,),
        now=1500.0,
    )
    assert route3.provider == "claude"


def test_observation_expiration_filtering() -> None:
    """Expired observation is ignored by is_active_at and resolve_dynamic_route."""
    catalog = {
        "codex-ep": _make_endpoint("codex-ep", "codex", "gpt-5-codex"),
    }
    binding = ActorBinding.create("binding_work", (ROLE_PRODUCER,))

    obs_exhausted = OperationalObservation(
        observation_id="obs-exhausted",
        producer="probe",
        observation_type="quota",
        provider="codex",
        state_value="exhausted",
        timestamp=1000.0,
        expires_at=2000.0,
    )

    assert obs_exhausted.is_active_at(1500.0) is True
    assert obs_exhausted.is_active_at(2500.0) is False

    # When active (now=1500), resolution fails closed with NoRouteAvailableError
    with pytest.raises(NoRouteAvailableError, match="no unexhausted quota routes"):
        resolve_dynamic_route(
            binding,
            "implementation_testing",
            capabilities_catalog=catalog,
            operational_observations=(obs_exhausted,),
            now=1500.0,
        )

    # When expired (now=2500), observation is ignored and route succeeds
    route = resolve_dynamic_route(
        binding,
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=(obs_exhausted,),
        now=2500.0,
    )
    assert route.provider == "codex"


def test_durable_observation_expiration_in_collector(tmp_path: Path) -> None:
    """collect_operational_observations filters expired durable observations using now."""
    conn = open_dispatcher_db(tmp_path / "test.db")
    run_id = "run-test-exp"
    record_run(
        conn,
        run_id=run_id,
        project="test",
        request_schema="agent-phase-request-v2",
        request_digest="dig1",
        lifecycle="default_v012",
        execution_mode="dynamic",
    )
    # Expired observation: timestamp=1000, expires_at=2000
    record_operational_observation(
        conn,
        observation_id="durable-expired",
        producer="test",
        observation_type="quota",
        provider="codex",
        state_value="exhausted",
        timestamp=1000.0,
        expires_at=2000.0,
        digest="d1",
    )
    # Active observation: timestamp=1000, expires_at=3000
    record_operational_observation(
        conn,
        observation_id="durable-active",
        producer="test",
        observation_type="cooldown",
        provider="codex",
        state_value="active_cooldown",
        timestamp=1000.0,
        expires_at=3000.0,
        digest="d2",
    )

    observations = collect_operational_observations(
        conn=conn,
        now=2500.0,
        providers=("codex",),
    )
    obs_ids = [o.observation_id for o in observations]
    assert "durable-expired" not in obs_ids
    assert "durable-active" in obs_ids


def test_probe_timestamps_and_expiry_honor_supplied_now() -> None:
    """MED-7: Tokenless probes must stamp timestamp=ref_now and expires_at=ref_now + 60.0."""
    scenario_now = 1234567.0
    observations = collect_operational_observations(
        conn=None,
        now=scenario_now,
        providers=("codex", "claude", "antigravity"),
    )
    assert len(observations) > 0
    for obs in observations:
        assert obs.timestamp == scenario_now
        assert obs.expires_at == scenario_now + 60.0
