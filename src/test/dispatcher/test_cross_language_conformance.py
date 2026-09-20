"""Cross-language equivalence test suite between APGR Python runtime and Go contracts.

Consumes the canonical golden fixtures in testing/fixtures/conformance/ and asserts
that the Python runtime oracle behavior matches the golden vectors consumed by Go.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent_phase.dynamic_router import (
    EndpointCapabilities,
    NoRouteAvailableError,
    OperationalObservation,
    resolve_dynamic_route,
)
from agent_phase.probes import compute_observation_digest
from agent_phase.request import (
    RequestError,
    SCHEMA_V2,
    parse_request_v2,
)
from agent_phase.semantic_roles import (
    CANONICAL_RESPONSIBILITIES,
    ROLE_MUTATING,
    ROLE_READ_ONLY,
    ROLE_REQUIRED_CAPABILITIES,
    create_default_binding_policy,
)

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "testing" / "fixtures" / "conformance"


def test_conformance_request_v2() -> None:
    path = FIXTURES_DIR / "request_v2_vectors.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    for vec in data["valid_vectors"]:
        raw = json.dumps(vec["payload"]).encode("utf-8")
        req = parse_request_v2(raw)
        assert req.schema == SCHEMA_V2
        assert req.phase_type == vec["payload"]["phase_type"]
        assert req.prompt == vec["payload"]["prompt"]

    for vec in data["invalid_vectors"]:
        raw = json.dumps(vec["payload"]).encode("utf-8")
        with pytest.raises(RequestError):
            parse_request_v2(raw)


def test_conformance_semantic_roles() -> None:
    path = FIXTURES_DIR / "semantic_roles_vectors.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert len(data["roles"]) == 8
    for r in data["roles"]:
        name = r["name"]
        assert name in CANONICAL_RESPONSIBILITIES
        assert ROLE_MUTATING[name] == r["is_mutating"]
        assert ROLE_READ_ONLY[name] == r["is_read_only"]
        assert sorted(ROLE_REQUIRED_CAPABILITIES[name]) == r["required_capabilities"]

    default_policy = create_default_binding_policy()
    assert len(default_policy.bindings) == 5
    for b, exp in zip(default_policy.bindings, data["topologies"]["default_standard"]):
        assert b.binding_id == exp["binding_id"]
        assert list(b.roles) == exp["roles"]
        assert b.is_mutating == exp["is_mutating"]
        assert b.process_read_only == exp["process_read_only"]
        assert sorted(b.required_capabilities) == exp["required_capabilities"]


def test_conformance_observation_digest() -> None:
    path = FIXTURES_DIR / "observation_digest_vectors.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    for vec in data["vectors"]:
        digest = compute_observation_digest(
            observation_id=vec["observation_id"],
            producer=vec["producer"],
            observation_type=vec["observation_type"],
            provider=vec["provider"],
            state_value=vec["state_value"],
            profile=vec["profile"],
            timestamp=vec["timestamp"],
            expires_at=vec["expires_at"],
            detail=vec["detail"],
        )
        assert digest == vec["expected_digest"]


def test_conformance_dynamic_routing() -> None:
    path = FIXTURES_DIR / "dynamic_routing_scenarios.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    catalog = {
        k: EndpointCapabilities(
            endpoint_alias=v["endpoint_alias"],
            provider=v["provider"],
            profile=v["profile"],
            capabilities=frozenset(v["capabilities"]),
            posture=v["posture"],
        )
        for k, v in data["catalog"].items()
    }

    policy = create_default_binding_policy()
    bindings = {b.binding_id: b for b in policy.bindings}

    for sc in data["scenarios"]:
        obs = [
            OperationalObservation(
                observation_id=o["observation_id"],
                producer=o["producer"],
                observation_type=o["observation_type"],
                provider=o["provider"],
                profile=o.get("profile"),
                timestamp=o["timestamp"],
                expires_at=o.get("expires_at"),
                state_value=o["state_value"],
            )
            for o in sc["observations"]
        ]

        binding = bindings[sc["binding_id"]]

        if sc.get("expected_error") == "no_route":
            with pytest.raises(NoRouteAvailableError):
                resolve_dynamic_route(
                    binding,
                    sc["phase_type"],
                    capabilities_catalog=catalog,
                    operational_observations=obs,
                    prior_resolutions=sc.get("prior_resolutions", {}),
                    now=sc.get("now"),
                )
        else:
            route = resolve_dynamic_route(
                binding,
                sc["phase_type"],
                capabilities_catalog=catalog,
                operational_observations=obs,
                prior_resolutions=sc.get("prior_resolutions", {}),
                now=sc.get("now"),
            )
            assert route.endpoint_alias == sc["expected_winner"]
            assert route.provider == sc["expected_provider"]
            assert route.profile == sc["expected_profile"]


def test_conformance_provider_matrix() -> None:
    path = FIXTURES_DIR / "provider_conformance_vectors.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["row_count"] == 22
    assert len(data["rows"]) == 22
    for row in data["rows"]:
        assert len(row["support"]) == 3
        assert "codex" in row["support"]
        assert "claude" in row["support"]
        assert "antigravity" in row["support"]
