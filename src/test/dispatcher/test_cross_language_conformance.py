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


def test_conformance_review_mutation_policy() -> None:
    from agent_phase.config_routing import (
        DEFAULT_REVIEW_MUTATION_GIT,
        DEFAULT_REVIEW_MUTATION_WORKTREE,
        SUPPORTED_POLICY_GENERATION,
        SUPPORTED_WORKTREE_POLICIES,
        ReviewMutationPolicy,
    )
    from agent_phase.review_drift import (
        ACTION_ALLOWED,
        ACTION_BLOCKED,
        ACTION_NONE,
        ACTION_WARNED,
        READ_ONLY_STAGE_MUTATED_CANDIDATE,
        READ_ONLY_STAGE_MUTATED_HEAD,
        READ_ONLY_STAGE_MUTATED_INDEX,
        ReviewObservation,
        apply_review_mutation_policy,
    )

    path = FIXTURES_DIR / "review_mutation_vectors.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    assert sorted(SUPPORTED_WORKTREE_POLICIES) == sorted(data["worktree_policies"])
    assert [DEFAULT_REVIEW_MUTATION_GIT] == data["git_policies"]
    assert sorted([ACTION_BLOCKED, ACTION_WARNED, ACTION_ALLOWED, ACTION_NONE]) == sorted(data["actions_taken"])
    assert sorted([
        READ_ONLY_STAGE_MUTATED_CANDIDATE,
        READ_ONLY_STAGE_MUTATED_INDEX,
        READ_ONLY_STAGE_MUTATED_HEAD,
    ]) == sorted(data["diagnostic_codes"])

    sample_p = data["sample_policy"]
    p = ReviewMutationPolicy(
        worktree=sample_p["worktree"],
        index=sample_p["index"],
        head=sample_p["head"],
        generation=sample_p["generation"],
    )
    assert p.worktree == DEFAULT_REVIEW_MUTATION_WORKTREE
    assert p.generation == SUPPORTED_POLICY_GENERATION

    for item in data["valid_observations"]:
        raw_obs = item["observation"]
        pol = ReviewMutationPolicy(
            worktree=raw_obs["policy"]["worktree"],
            index=raw_obs["policy"]["index"],
            head=raw_obs["policy"]["head"],
            generation=raw_obs["policy"]["generation"],
        )
        obs = ReviewObservation(
            stage=raw_obs["stage"],
            policy=pol,
            subject_drift_observed=raw_obs["subject_drift_observed"],
            worktree_drift=raw_obs["worktree_drift"],
            index_drift=raw_obs["index_drift"],
            head_drift=raw_obs["head_drift"],
            worktree_paths=raw_obs.get("worktree_paths", []),
            index_paths=raw_obs.get("index_paths", []),
            expected_index=raw_obs.get("expected_index"),
            observed_index=raw_obs.get("observed_index"),
            expected_head=raw_obs.get("expected_head", ""),
            observed_head=raw_obs.get("observed_head", ""),
            candidate_observation_unavailable=raw_obs.get("candidate_observation_unavailable", False),
            index_observation_unavailable=raw_obs.get("index_observation_unavailable", False),
            head_observation_unavailable=raw_obs.get("head_observation_unavailable", False),
            observation_limitations=raw_obs.get("observation_limitations", raw_obs.get("limitations", [])),
            role=raw_obs.get("role"),
            subject_kind=raw_obs.get("subject_kind"),
            sequence=raw_obs.get("sequence", 0),
            attempt_id=raw_obs.get("attempt_id"),
            binding_id=raw_obs.get("binding_id"),
            attempt_number=raw_obs.get("attempt_number"),
            paths_complete=raw_obs.get("paths_complete", True),
        )
        evaluated = apply_review_mutation_policy(obs, pol, raise_on_block=False)
        assert evaluated.action_taken == raw_obs["action_taken"], f"Failed for {item['name']}"
        expected_diag = raw_obs.get("diagnostic_code", "")
        assert evaluated.diagnostic_code == expected_diag, f"Diagnostic mismatch for {item['name']}"

