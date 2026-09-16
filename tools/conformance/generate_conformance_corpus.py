#!/usr/bin/env python3
"""Deterministic generator and drift verifier for cross-language conformance corpus.

Python runtime is the authoritative oracle for APGR v0.12 semantics.
Generates canonical JSON vectors consumed identically by Go and Python test suites.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if str(Path(__file__).resolve().parents[2] / "libexec") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "libexec"))

from agent_phase.dynamic_router import (
    EndpointCapabilities,
    NoRouteAvailableError,
    OperationalObservation,
    resolve_dynamic_route,
)
from agent_phase.probes import compute_observation_digest
from agent_phase.semantic_roles import (
    CANONICAL_RESPONSIBILITIES,
    ROLE_MUTATING,
    ROLE_READ_ONLY,
    ROLE_REQUIRED_CAPABILITIES,
    create_default_binding_policy,
    create_unmerged_binding_policy,
)

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT / "testing" / "fixtures" / "conformance"


def generate_request_v2_vectors() -> dict[str, Any]:
    valid = [
        {
            "id": "valid_minimal",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "Implement public Go packages",
            },
        },
        {
            "id": "valid_architecture_docs",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "architecture_docs",
                "prompt": "Write ADR 0066 specification",
            },
        },
        {
            "id": "valid_sysadmin",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "sysadmin",
                "prompt": "Provision development environment",
            },
        },
        {
            "id": "valid_multiline_prompt",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "Line 1\nLine 2\n\nLine 4 with special chars: <>&'\"`",
            },
        },
        {
            "id": "valid_unicode_prompt",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "Unicode test: 魔法 🧙‍♂️ ✨ 🚀 — invariant check",
            },
        },
    ]

    invalid = [
        {
            "id": "invalid_wrong_schema",
            "payload": {
                "schema": "agent-phase-request-v1",
                "phase_type": "implementation_testing",
                "prompt": "Test prompt",
            },
            "expected_error": "request schema must be agent-phase-request-v2",
        },
        {
            "id": "invalid_unknown_schema",
            "payload": {
                "schema": "unknown-schema-v2",
                "phase_type": "implementation_testing",
                "prompt": "Test prompt",
            },
            "expected_error": "request schema must be agent-phase-request-v2",
        },
        {
            "id": "invalid_wrong_phase_type",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "invalid_phase",
                "prompt": "Test prompt",
            },
            "expected_error": "unsupported phase_type: invalid_phase",
        },
        {
            "id": "invalid_empty_prompt",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "",
            },
            "expected_error": "prompt must be non-empty",
        },
        {
            "id": "invalid_whitespace_prompt",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "   \n\t  ",
            },
            "expected_error": "prompt must be non-empty",
        },
        {
            "id": "invalid_extra_execution_mode",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "Test prompt",
                "execution_mode": "normal",
            },
            "expected_error": "unsupported request key for agent-phase-request-v2: execution_mode",
        },
        {
            "id": "invalid_extra_constraints",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "Test prompt",
                "constraints": ["no_network"],
            },
            "expected_error": "unsupported request key for agent-phase-request-v2: constraints",
        },
        {
            "id": "invalid_extra_provider",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "Test prompt",
                "provider": "codex",
            },
            "expected_error": "unsupported request key for agent-phase-request-v2: provider",
        },
        {
            "id": "invalid_extra_unknown_key",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
                "prompt": "Test prompt",
                "extra_key": "unexpected",
            },
            "expected_error": "unsupported request key for agent-phase-request-v2: extra_key",
        },
        {
            "id": "invalid_missing_prompt",
            "payload": {
                "schema": "agent-phase-request-v2",
                "phase_type": "implementation_testing",
            },
            "expected_error": "request keys must be exactly ['phase_type', 'prompt', 'schema']",
        },
        {
            "id": "invalid_missing_phase_type",
            "payload": {
                "schema": "agent-phase-request-v2",
                "prompt": "Test prompt",
            },
            "expected_error": "request keys must be exactly ['phase_type', 'prompt', 'schema']",
        },
        {
            "id": "invalid_missing_schema",
            "payload": {
                "phase_type": "implementation_testing",
                "prompt": "Test prompt",
            },
            "expected_error": "request keys must be exactly ['phase_type', 'prompt', 'schema']",
        },
    ]

    return {
        "schema": "apgr-conformance-request-v2-v1",
        "valid_vectors": valid,
        "invalid_vectors": invalid,
    }


def generate_semantic_roles_vectors() -> dict[str, Any]:
    roles = []
    for role in CANONICAL_RESPONSIBILITIES:
        roles.append(
            {
                "name": role,
                "is_mutating": ROLE_MUTATING[role],
                "is_read_only": ROLE_READ_ONLY[role],
                "required_capabilities": sorted(ROLE_REQUIRED_CAPABILITIES[role]),
            }
        )

    default_policy = create_default_binding_policy()
    unmerged_policy = create_unmerged_binding_policy()

    return {
        "schema": "apgr-conformance-semantic-roles-v1",
        "roles": roles,
        "topologies": {
            "default_standard": [
                {
                    "binding_id": b.binding_id,
                    "roles": list(b.roles),
                    "policy_name": b.policy_name,
                    "is_mutating": b.is_mutating,
                    "process_read_only": b.process_read_only,
                    "required_capabilities": sorted(b.required_capabilities),
                }
                for b in default_policy.bindings
            ],
            "unmerged_discrete": [
                {
                    "binding_id": b.binding_id,
                    "roles": list(b.roles),
                    "policy_name": b.policy_name,
                    "is_mutating": b.is_mutating,
                    "process_read_only": b.process_read_only,
                    "required_capabilities": sorted(b.required_capabilities),
                }
                for b in unmerged_policy.bindings
            ],
        },
    }


def generate_observation_digest_vectors() -> dict[str, Any]:
    cases = [
        {
            "observation_id": "obs-avail-codex-1000",
            "producer": "apgr_operational_probe",
            "observation_type": "availability",
            "provider": "codex",
            "profile": None,
            "timestamp": 1726500000.0,
            "expires_at": 1726500060.0,
            "state_value": "available",
            "detail": {"path": "/usr/local/bin/codex", "version": "0.1.0"},
        },
        {
            "observation_id": "obs-avail-claude-2000",
            "producer": "apgr_operational_probe",
            "observation_type": "availability",
            "provider": "claude",
            "profile": "claude_review",
            "timestamp": 1726500100.5,
            "expires_at": 1726500160.5,
            "state_value": "unavailable",
            "detail": {"reason": "executable_not_found"},
        },
        {
            "observation_id": "obs-auth-antigravity-3000",
            "producer": "apgr_auth_check",
            "observation_type": "authentication",
            "provider": "antigravity",
            "profile": "gemini_flash",
            "timestamp": 1726500200.0,
            "expires_at": None,
            "state_value": "unusable",
            "detail": {"error_code": 401, "message": "unauthenticated"},
        },
        {
            "observation_id": "obs-quota-codex-4000",
            "producer": "apgr_quota_monitor",
            "observation_type": "quota",
            "provider": "codex",
            "profile": None,
            "timestamp": 1726500300.0,
            "expires_at": 1726500900.0,
            "state_value": "exhausted",
            "detail": None,
        },
        {
            "observation_id": "obs-quota-claude-5000",
            "producer": "apgr_quota_monitor",
            "observation_type": "quota",
            "provider": "claude",
            "profile": "claude_sonnet",
            "timestamp": 1726500400.0,
            "expires_at": 1726501000.0,
            "state_value": "healthy",
            "detail": {"remaining_tokens": 500000},
        },
        {
            "observation_id": "obs-cooldown-antigravity-6000",
            "producer": "apgr_cooldown_tracker",
            "observation_type": "cooldown",
            "provider": "antigravity",
            "profile": None,
            "timestamp": 1726500500.0,
            "expires_at": 1726500800.0,
            "state_value": "active_cooldown",
            "detail": {"failure_count": 3, "last_failure": "rate_limit"},
        },
    ]

    vectors = []
    for c in cases:
        digest = compute_observation_digest(
            observation_id=c["observation_id"],
            producer=c["producer"],
            observation_type=c["observation_type"],
            provider=c["provider"],
            state_value=c["state_value"],
            profile=c["profile"],
            timestamp=c["timestamp"],
            expires_at=c["expires_at"],
            detail=c["detail"],
        )
        entry = dict(c)
        entry["expected_digest"] = digest
        vectors.append(entry)

    return {
        "schema": "apgr-conformance-observation-digest-v1",
        "vectors": vectors,
    }


def generate_dynamic_routing_scenarios() -> dict[str, Any]:
    catalog: dict[str, EndpointCapabilities] = {
        "codex-primary": EndpointCapabilities(
            endpoint_alias="codex-primary",
            provider="codex",
            profile="codex_implementation",
            capabilities=frozenset({"read", "mutation", "execution", "reasoning", "structured_output"}),
            posture="mutating",
        ),
        "codex-review": EndpointCapabilities(
            endpoint_alias="codex-review",
            provider="codex",
            profile="codex_review",
            capabilities=frozenset({"read", "reasoning", "structured_output"}),
            posture="read_only",
        ),
        "claude-primary": EndpointCapabilities(
            endpoint_alias="claude-primary",
            provider="claude",
            profile="claude_architecture",
            capabilities=frozenset({"read", "mutation", "execution", "reasoning", "structured_output"}),
            posture="mutating",
        ),
        "claude-review": EndpointCapabilities(
            endpoint_alias="claude-review",
            provider="claude",
            profile="claude_review",
            capabilities=frozenset({"read", "reasoning", "structured_output"}),
            posture="read_only",
        ),
        "antigravity-primary": EndpointCapabilities(
            endpoint_alias="antigravity-primary",
            provider="antigravity",
            profile="antigravity_implementation",
            capabilities=frozenset({"read", "mutation", "execution", "reasoning", "subagent_workers"}),
            posture="mutating",
        ),
        "antigravity-review": EndpointCapabilities(
            endpoint_alias="antigravity-review",
            provider="antigravity",
            profile="antigravity_review",
            capabilities=frozenset({"read", "reasoning"}),
            posture="read_only",
        ),
    }

    catalog_dict = {
        k: {
            "endpoint_alias": ep.endpoint_alias,
            "provider": ep.provider,
            "profile": ep.profile,
            "capabilities": sorted(ep.capabilities),
            "posture": ep.posture,
        }
        for k, ep in sorted(catalog.items())
    }

    policy = create_default_binding_policy()
    bindings = {b.binding_id: b for b in policy.bindings}

    scenarios = []
    phase_types = ["implementation_testing", "architecture_docs", "sysadmin"]
    simulated_now = 1726500000.0

    # 1. Baseline no-observation routing across all phase types and bindings
    for pt in phase_types:
        for b_id, binding in sorted(bindings.items()):
            try:
                res = resolve_dynamic_route(
                    binding,
                    pt,
                    capabilities_catalog=catalog,
                    operational_observations=(),
                    prior_resolutions={},
                )
                scenarios.append(
                    {
                        "id": f"baseline_{pt}_{b_id}",
                        "description": f"Baseline routing for {b_id} in {pt}",
                        "phase_type": pt,
                        "binding_id": b_id,
                        "required_capabilities": sorted(binding.required_capabilities),
                        "is_mutating": binding.is_mutating,
                        "observations": [],
                        "prior_resolutions": {},
                        "now": simulated_now,
                        "expected_winner": res.endpoint_alias,
                        "expected_provider": res.provider,
                        "expected_profile": res.profile,
                        "expected_rationale": res.selection_rationale,
                    }
                )
            except NoRouteAvailableError as e:
                scenarios.append(
                    {
                        "id": f"baseline_{pt}_{b_id}",
                        "description": f"Baseline routing error for {b_id} in {pt}",
                        "phase_type": pt,
                        "binding_id": b_id,
                        "required_capabilities": sorted(binding.required_capabilities),
                        "is_mutating": binding.is_mutating,
                        "observations": [],
                        "prior_resolutions": {},
                        "now": simulated_now,
                        "expected_error": "no_route",
                        "error_message": str(e),
                    }
                )

    # 2. Hard unavailable exclusion (expires_at=None is unconditionally active)
    obs_unavail = OperationalObservation(
        observation_id="obs-codex-unavail",
        producer="probe",
        observation_type="availability",
        provider="codex",
        profile=None,
        timestamp=simulated_now,
        expires_at=None,
        state_value="unavailable",
    )
    res_unavail = resolve_dynamic_route(
        bindings["binding_work"],
        "implementation_testing",
        capabilities_catalog=catalog,
        operational_observations=[obs_unavail],
        prior_resolutions={},
    )
    scenarios.append(
        {
            "id": "codex_unavailable_fallback_to_antigravity",
            "description": "Codex marked unavailable, implementation falls back to antigravity",
            "phase_type": "implementation_testing",
            "binding_id": "binding_work",
            "required_capabilities": sorted(bindings["binding_work"].required_capabilities),
            "is_mutating": bindings["binding_work"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_unavail.observation_id,
                    "producer": obs_unavail.producer,
                    "observation_type": obs_unavail.observation_type,
                    "provider": obs_unavail.provider,
                    "profile": obs_unavail.profile,
                    "timestamp": obs_unavail.timestamp,
                    "expires_at": obs_unavail.expires_at,
                    "state_value": obs_unavail.state_value,
                }
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_unavail.endpoint_alias,
            "expected_provider": res_unavail.provider,
            "expected_profile": res_unavail.profile,
            "expected_rationale": res_unavail.selection_rationale,
        }
    )

    # 3. Plan Reviewer independence
    prior_plan = {
        "binding_plan": {
            "binding_id": "binding_plan",
            "provider": "codex",
            "profile": "codex_implementation",
            "endpoint_alias": "codex-primary",
            "roles": ["Planner"],
        }
    }
    res_indep = resolve_dynamic_route(
        bindings["binding_plan_review"],
        "architecture_docs",
        capabilities_catalog=catalog,
        operational_observations=(),
        prior_resolutions=prior_plan,
    )
    scenarios.append(
        {
            "id": "plan_reviewer_independence_excludes_codex",
            "description": "Planner was Codex, Plan Reviewer must not choose Codex",
            "phase_type": "architecture_docs",
            "binding_id": "binding_plan_review",
            "required_capabilities": sorted(bindings["binding_plan_review"].required_capabilities),
            "is_mutating": bindings["binding_plan_review"].is_mutating,
            "observations": [],
            "prior_resolutions": prior_plan,
            "now": simulated_now,
            "expected_winner": res_indep.endpoint_alias,
            "expected_provider": res_indep.provider,
            "expected_profile": res_indep.profile,
            "expected_rationale": res_indep.selection_rationale,
        }
    )

    # 4. Work Reviewer independence
    prior_work = {
        "binding_work": {
            "binding_id": "binding_work",
            "provider": "claude",
            "profile": "claude_architecture",
            "endpoint_alias": "claude-primary",
            "roles": ["Producer"],
        }
    }
    res_work_indep = resolve_dynamic_route(
        bindings["binding_work_review"],
        "architecture_docs",
        capabilities_catalog=catalog,
        operational_observations=(),
        prior_resolutions=prior_work,
    )
    scenarios.append(
        {
            "id": "work_reviewer_independence_excludes_claude",
            "description": "Producer was Claude, Work Reviewer must not choose Claude",
            "phase_type": "architecture_docs",
            "binding_id": "binding_work_review",
            "required_capabilities": sorted(bindings["binding_work_review"].required_capabilities),
            "is_mutating": bindings["binding_work_review"].is_mutating,
            "observations": [],
            "prior_resolutions": prior_work,
            "now": simulated_now,
            "expected_winner": res_work_indep.endpoint_alias,
            "expected_provider": res_work_indep.provider,
            "expected_profile": res_work_indep.profile,
            "expected_rationale": res_work_indep.selection_rationale,
        }
    )

    # 5. Quota exhausted exclusion
    obs_quota = OperationalObservation(
        observation_id="obs-claude-quota-exhausted",
        producer="quota",
        observation_type="quota",
        provider="claude",
        profile=None,
        timestamp=simulated_now,
        expires_at=None,
        state_value="exhausted",
    )
    res_quota = resolve_dynamic_route(
        bindings["binding_plan"],
        "architecture_docs",
        capabilities_catalog=catalog,
        operational_observations=[obs_quota],
        prior_resolutions={},
    )
    scenarios.append(
        {
            "id": "claude_quota_exhausted_fallback",
            "description": "Claude quota exhausted, falls back to codex or antigravity",
            "phase_type": "architecture_docs",
            "binding_id": "binding_plan",
            "required_capabilities": sorted(bindings["binding_plan"].required_capabilities),
            "is_mutating": bindings["binding_plan"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_quota.observation_id,
                    "producer": obs_quota.producer,
                    "observation_type": obs_quota.observation_type,
                    "provider": obs_quota.provider,
                    "profile": obs_quota.profile,
                    "timestamp": obs_quota.timestamp,
                    "expires_at": obs_quota.expires_at,
                    "state_value": obs_quota.state_value,
                }
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_quota.endpoint_alias,
            "expected_provider": res_quota.provider,
            "expected_profile": res_quota.profile,
            "expected_rationale": res_quota.selection_rationale,
        }
    )

    # 6. Active failure cooldown exclusion
    obs_cooldown = OperationalObservation(
        observation_id="obs-antigravity-cooldown",
        producer="cooldown",
        observation_type="cooldown",
        provider="antigravity",
        profile=None,
        timestamp=simulated_now,
        expires_at=None,
        state_value="active_cooldown",
    )
    res_cooldown = resolve_dynamic_route(
        bindings["binding_work"],
        "sysadmin",
        capabilities_catalog=catalog,
        operational_observations=[obs_cooldown],
        prior_resolutions={},
    )
    scenarios.append(
        {
            "id": "antigravity_active_cooldown_fallback",
            "description": "Antigravity in active cooldown, fallback to alternative",
            "phase_type": "sysadmin",
            "binding_id": "binding_work",
            "required_capabilities": sorted(bindings["binding_work"].required_capabilities),
            "is_mutating": bindings["binding_work"].is_mutating,
            "observations": [
                {
                    "observation_id": obs_cooldown.observation_id,
                    "producer": obs_cooldown.producer,
                    "observation_type": obs_cooldown.observation_type,
                    "provider": obs_cooldown.provider,
                    "profile": obs_cooldown.profile,
                    "timestamp": obs_cooldown.timestamp,
                    "expires_at": obs_cooldown.expires_at,
                    "state_value": obs_cooldown.state_value,
                }
            ],
            "prior_resolutions": {},
            "now": simulated_now,
            "expected_winner": res_cooldown.endpoint_alias,
            "expected_provider": res_cooldown.provider,
            "expected_profile": res_cooldown.profile,
            "expected_rationale": res_cooldown.selection_rationale,
        }
    )

    # 7. Complete exhaustion -> NoRouteAvailableError
    all_unavail = [
        OperationalObservation(
            observation_id=f"obs-{p}-unavail",
            producer="probe",
            observation_type="availability",
            provider=p,
            timestamp=simulated_now,
            expires_at=None,
            state_value="unavailable",
        )
        for p in ("codex", "claude", "antigravity")
    ]
    try:
        resolve_dynamic_route(
            bindings["binding_work"],
            "implementation_testing",
            capabilities_catalog=catalog,
            operational_observations=all_unavail,
            prior_resolutions={},
        )
        raise AssertionError("Expected NoRouteAvailableError")
    except NoRouteAvailableError as e:
        scenarios.append(
            {
                "id": "all_providers_unavailable_fails_closed",
                "description": "All providers unavailable raises NoRouteAvailableError",
                "phase_type": "implementation_testing",
                "binding_id": "binding_work",
                "required_capabilities": sorted(bindings["binding_work"].required_capabilities),
                "is_mutating": bindings["binding_work"].is_mutating,
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
                    for o in all_unavail
                ],
                "prior_resolutions": {},
                "now": simulated_now,
                "expected_error": "no_route",
                "error_message": str(e),
            }
        )

    try:
        from tools.conformance.feedback_scenarios import generate_feedback_scenarios
    except ImportError:
        from feedback_scenarios import generate_feedback_scenarios
    scenarios.extend(generate_feedback_scenarios(bindings, catalog, simulated_now))

    return {
        "schema": "apgr-conformance-dynamic-routing-v1",
        "catalog": catalog_dict,
        "scenarios": scenarios,
    }


def generate_evidence_review_vectors() -> dict[str, Any]:
    return {
        "schema": "apgr-conformance-evidence-review-v1",
        "severities": ["blocking", "substantive", "advisory"],
        "categories": [
            "correctness",
            "contract_violation",
            "security",
            "scope",
            "evidence",
            "clarity",
        ],
        "review_outcomes": [
            "reviewed_with_no_findings",
            "reviewed_with_findings",
            "unreviewable",
        ],
        "disposition_actions": ["accept", "amend", "reject", "defer"],
        "disposition_bases": [
            "accepted_authority",
            "canonical_evidence",
            "scope_owner",
            "none",
        ],
        "sample_finding": {
            "finding_id": "F-001",
            "severity": "blocking",
            "category": "contract_violation",
            "summary": "Request V2 must reject execution_mode",
            "file_path": "phase/request.go",
            "line_start": 42,
            "line_end": 45,
        },
        "sample_disposition": {
            "finding_id": "F-001",
            "action": "amend",
            "basis": "accepted_authority",
            "rationale": "Corrected per ADR 0066 specification",
        },
        "sample_receipt": {
            "receipt_id": "rcpt-run-001",
            "run_id": "run-20260917-001",
            "phase_id": "APG150",
            "completed_at": "2026-09-17T00:00:00Z",
            "terminal_status": "completed",
            "archive_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
    }


def generate_candidate_artifact_vectors() -> dict[str, Any]:
    return {
        "schema": "apgr-conformance-candidate-artifact-v1",
        "sample_candidate": {
            "candidate_id": "cand-001-generation-1",
            "generation": 1,
            "producer_role": "Producer",
            "producer_attempt_id": "att-001",
            "predecessor_id": None,
            "commit": "4885f5f290fe6adc0d763cc8a284ac1179be5c90",
            "tree_digest": "0ec1c98f51e3b6419e4ab0f3d25fa120aaffb1f8",
            "expected_base": "388f53e1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7",
        },
        "sample_artifact": {
            "artifact_id": "art-plan-001",
            "run_id": "run-001",
            "phase_id": "APG150",
            "relative_path": "docs/architecture/plan.md",
            "media_type": "text/markdown; charset=utf-8",
            "byte_size": 2048,
            "sha256": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        },
        "invalid_relative_paths": [
            "../outside.txt",
            "/absolute/path.txt",
            "foo/../../escape.txt",
            "",
            ".",
        ],
    }


def generate_provider_conformance_vectors() -> dict[str, Any]:
    matrix_path = ROOT / "docs" / "architecture" / "provider-conformance-matrix.json"
    data = json.loads(matrix_path.read_text(encoding="utf-8"))
    return {
        "schema": "apgr-conformance-provider-matrix-v1",
        "generated_at": data.get("generated_at"),
        "providers": data.get("providers"),
        "row_count": len(data.get("rows", [])),
        "rows": data.get("rows", []),
    }


def generate_all_corpora() -> dict[str, str]:
    generators = {
        "request_v2_vectors.json": generate_request_v2_vectors,
        "semantic_roles_vectors.json": generate_semantic_roles_vectors,
        "observation_digest_vectors.json": generate_observation_digest_vectors,
        "dynamic_routing_scenarios.json": generate_dynamic_routing_scenarios,
        "evidence_review_vectors.json": generate_evidence_review_vectors,
        "candidate_artifact_vectors.json": generate_candidate_artifact_vectors,
        "provider_conformance_vectors.json": generate_provider_conformance_vectors,
    }
    result = {}
    for filename, fn in generators.items():
        data = fn()
        text = json.dumps(data, indent=2, sort_keys=True) + "\n"
        result[filename] = text
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-language conformance corpus generator & drift checker")
    parser.add_argument("--check", action="store_true", help="Verify fixtures match generated corpus without writing")
    parser.add_argument("--generate", action="store_true", help="Generate/overwrite fixtures")
    args = parser.parse_args(argv)

    corpora = generate_all_corpora()

    if args.check:
        drifted = []
        for filename, expected_text in corpora.items():
            path = FIXTURES_DIR / filename
            if not path.is_file():
                drifted.append(f"{filename} (missing)")
                continue
            actual_text = path.read_text(encoding="utf-8")
            if actual_text != expected_text:
                drifted.append(f"{filename} (content drifted)")

        if drifted:
            print("FAIL: Cross-language conformance corpus drift detected in:", file=sys.stderr)
            for item in drifted:
                print(f"  - {item}", file=sys.stderr)
            print("Run 'python3 tools/conformance/generate_conformance_corpus.py --generate' to sync.", file=sys.stderr)
            return 1
        print("PASS: Cross-language conformance corpus matches Python runtime oracle.")
        return 0

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    for filename, text in corpora.items():
        (FIXTURES_DIR / filename).write_text(text, encoding="utf-8")
        print(f"Wrote {FIXTURES_DIR / filename}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
