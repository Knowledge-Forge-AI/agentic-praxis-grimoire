from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agent_phase.lifecycle import LIFECYCLE_NAMES, get_lifecycle
from agent_phase.request import EXECUTION_MODES, PHASE_TYPES, PhaseRequest
from agent_phase.roster import ENDPOINTS_SOURCE, ROUTES_SOURCE, Endpoint, load_roster
from agent_phase.routing import (
    CHECKPOINTS,
    CHECKPOINT_COUNT,
    PROVIDER_INVOCATIONS,
    RESOLVED_SCHEMA,
    RoutingError,
    describe,
    load_validated_roster,
    resolve,
    route,
)
from agent_phase_roster_fixtures import (
    SYNTHETIC_ENDPOINTS,
    SYNTHETIC_INTELLIGENCE,
    SyntheticRoster,
    build_synthetic_roster,
    replace_once,
    write_roster_sources,
)


ROOT = Path(__file__).resolve().parents[3]
COMBINATIONS = tuple(
    (phase_type, execution_mode)
    for phase_type in PHASE_TYPES
    for execution_mode in EXECUTION_MODES
)


def request_for(key: tuple[str, str]) -> PhaseRequest:
    return PhaseRequest(key[0], key[1], "bounded fixture task")


def expected_intelligence(
    fixture: SyntheticRoster,
    execution_mode: str,
    endpoint: Endpoint,
) -> dict[str, object]:
    expected = dict(SYNTHETIC_INTELLIGENCE[(endpoint.provider, endpoint.profile)])
    if execution_mode == "conserve_claude" and endpoint.provider == "codex":
        source = fixture.root / "codex/config.d/170-subagents.toml"
        expected["workers"] = {
            "mode": "provider-local",
            "enabled": True,
            "model": "gpt-5.6-luna",
            "reasoning_effort": "max",
            "maximum_concurrency": 10,
            "source_path": "codex/config.d/170-subagents.toml",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    return expected


def assert_synthetic_roster_contract(fixture: SyntheticRoster) -> None:
    snapshot = load_validated_roster(fixture.root)
    assert set(snapshot.routes) == set(COMBINATIONS)
    assert snapshot.generation == fixture.generation
    for key in COMBINATIONS:
        for lifecycle_name in LIFECYCLE_NAMES:
            specification = get_lifecycle(lifecycle_name)
            resolved = resolve(
                request_for(key),
                fixture.root,
                lifecycle_name,
                "checkpoint",
                roster=snapshot,
            )
            assert tuple(resolved["stages"]) == specification.stage_names
            for stage in specification.stages:
                expected_alias = fixture.routes[key][stage.routing_slot]
                expected_endpoint = fixture.endpoints[expected_alias]
                actual = resolved["stages"][stage.name]
                assert actual["endpoint_alias"] == expected_alias
                assert (actual["provider"], actual["profile"]) == expected_endpoint
                assert actual["role"] == stage.role
                assert actual["routing_source_slot"] == stage.routing_slot
                assert actual["candidate_mutation"] is stage.is_mutating
                assert actual["process_read_only"] is stage.process_read_only
                assert actual["intelligence"] == expected_intelligence(
                    fixture, key[1], expected_endpoint
                )
                if stage.process_read_only:
                    assert actual["process_posture"]["enforced"] is True
                else:
                    assert actual["process_posture"] == {
                        "enforced": False,
                        "mode": "mutation-capable",
                    }


def test_canonical_roster_smoke_is_data_driven() -> None:
    snapshot = load_validated_roster(ROOT)
    assert set(snapshot.routes) == set(COMBINATIONS)
    for key in COMBINATIONS:
        aliases = snapshot.route_aliases(*key)
        first = resolve(request_for(key), ROOT, roster=snapshot)
        second = resolve(request_for(key), ROOT, roster=snapshot)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
        assert first["schema"] == RESOLVED_SCHEMA == "agent-phase-resolved-v6"
        assert first["roster"] == snapshot.provenance()
        assert "primary" not in first
        assert "reviewer" not in first
        specification = get_lifecycle("standard")
        for stage in specification.stages:
            actual = first["stages"][stage.name]
            alias = aliases[stage.routing_slot]
            endpoint = snapshot.endpoints[alias]
            assert actual["endpoint_alias"] == alias
            assert (actual["provider"], actual["profile"]) == endpoint
            assert actual["role"] == stage.role


def test_canonical_provenance_is_byte_exact_without_generation_coupling() -> None:
    snapshot = load_roster(ROOT)
    assert snapshot.provenance() == {
        "schema": "agent-phase-roster-provenance-v1",
        "generation": snapshot.generation,
        "sources": {
            "endpoints": {
                "path": ENDPOINTS_SOURCE.as_posix(),
                "sha256": hashlib.sha256(
                    (ROOT / ENDPOINTS_SOURCE).read_bytes()
                ).hexdigest(),
            },
            "routes": {
                "path": ROUTES_SOURCE.as_posix(),
                "sha256": hashlib.sha256(
                    (ROOT / ROUTES_SOURCE).read_bytes()
                ).hexdigest(),
            },
        },
    }


@pytest.mark.parametrize("variant", ["mixed", "permuted"])
def test_materially_different_synthetic_lineups_share_invariant_machinery(
    tmp_path: Path, variant: str
) -> None:
    fixture = build_synthetic_roster(tmp_path / variant, variant=variant)
    assert_synthetic_roster_contract(fixture)


def test_resolved_and_executed_routes_share_one_captured_snapshot(
    tmp_path: Path,
) -> None:
    fixture = build_synthetic_roster(tmp_path)
    request = PhaseRequest("implementation_testing", "normal", "x")
    snapshot = load_validated_roster(fixture.root)
    resolved = resolve(request, fixture.root, roster=snapshot)
    changed_routes = {key: dict(value) for key, value in fixture.routes.items()}
    changed_routes[("implementation_testing", "normal")]["work"] = (
        "fixture-gemini-gold"
    )
    write_roster_sources(
        fixture.root,
        SYNTHETIC_ENDPOINTS,
        changed_routes,
        generation=fixture.generation + 1,
    )

    endpoints = route(request, root=fixture.root, roster=snapshot)

    assert snapshot.generation == resolved["roster"]["generation"]
    assert endpoints["work"].provider == resolved["stages"]["work"]["provider"]
    assert endpoints["work"].profile == resolved["stages"]["work"]["profile"]


def test_lifecycle_and_invocation_counts_remain_lifecycle_owned(
    tmp_path: Path,
) -> None:
    fixture = build_synthetic_roster(tmp_path)
    for key in COMBINATIONS:
        resolved = resolve(request_for(key), fixture.root)
        assert resolved["checkpoints"] == ["post_planning", "pre_final"]
        assert resolved["checkpoint_count"] == 2
        assert resolved["provider_invocations"] == 5
    assert CHECKPOINTS == ("post_planning", "pre_final")
    assert CHECKPOINT_COUNT == 2
    assert PROVIDER_INVOCATIONS == 5


def test_resolved_exposes_only_verified_process_posture(tmp_path: Path) -> None:
    fixture = build_synthetic_roster(tmp_path)
    for key in COMBINATIONS:
        resolved = resolve(request_for(key), fixture.root)
        assert "plugin" not in json.dumps(resolved).lower()
        for endpoint in resolved["stages"].values():
            intelligence = endpoint["intelligence"]
            assert "default_subagent_model" not in intelligence
            assert "default_subagent_reasoning_effort" not in intelligence
            assert endpoint["process_read_only"] is endpoint["process_posture"][
                "enforced"
            ]


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("enabled = true", "enabled = false", "disabled"),
        (
            'default_subagent_model = "gpt-5.6-luna"',
            'default_subagent_model = "gpt-5.6-sol"',
            "model",
        ),
        (
            'default_subagent_reasoning_effort = "max"',
            'default_subagent_reasoning_effort = "high"',
            "reasoning",
        ),
        (
            "max_concurrent_threads_per_session = 10",
            "max_concurrent_threads_per_session = 9",
            "concurrency",
        ),
    ],
)
def test_conserve_resolution_fails_closed_for_wrong_worker_contract(
    tmp_path: Path, old: str, new: str, message: str
) -> None:
    fixture = build_synthetic_roster(tmp_path)
    source = fixture.root / "codex/config.d/170-subagents.toml"
    source.write_text(
        replace_once(source.read_text(encoding="utf-8"), old, new),
        encoding="utf-8",
    )

    with pytest.raises(RoutingError, match=message):
        resolve(
            PhaseRequest("implementation_testing", "conserve_claude", "x"),
            fixture.root,
        )


@pytest.mark.parametrize("replacement", [None, "[agents\nenabled = true\n"])
def test_conserve_resolution_fails_closed_for_missing_or_malformed_worker_source(
    tmp_path: Path, replacement: str | None
) -> None:
    fixture = build_synthetic_roster(tmp_path)
    source = fixture.root / "codex/config.d/170-subagents.toml"
    if replacement is None:
        source.unlink()
    else:
        source.write_text(replacement, encoding="utf-8")

    with pytest.raises(RoutingError, match="worker source"):
        resolve(PhaseRequest("sysadmin", "conserve_claude", "x"), fixture.root)


def test_unknown_provider_is_rejected_explicitly() -> None:
    with pytest.raises(RoutingError, match="unknown provider"):
        describe(ROOT, "primary", Endpoint("not-a-provider", "fixture"))


def test_resolution_fails_closed_when_a_profile_source_is_missing(
    tmp_path: Path,
) -> None:
    fixture = build_synthetic_roster(tmp_path)
    (fixture.root / "codex/profiles/fixture-codex-review.config.toml").unlink()
    with pytest.raises(RoutingError, match="unusable Codex profile source"):
        resolve(PhaseRequest("sysadmin", "codex_only", "x"), fixture.root)


def test_resolution_refuses_unavailable_claude_read_only_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import claude_vc_profile

    fixture = build_synthetic_roster(tmp_path)

    def unavailable(root: Path, profile: str) -> dict[str, object]:
        raise claude_vc_profile.ProfileError(
            f"read-only posture unavailable for {profile}"
        )

    monkeypatch.setattr(claude_vc_profile, "read_only_contract", unavailable)
    with pytest.raises(RoutingError, match="read-only posture unavailable"):
        resolve(
            PhaseRequest("implementation_testing", "claude_only", "task"),
            fixture.root,
            "plan-reviewed",
            "checkpoint",
        )


def test_resolution_does_not_touch_the_filesystem_state() -> None:
    before = sorted(path.name for path in ROOT.iterdir())
    resolve(PhaseRequest("sysadmin", "normal", "x"), ROOT)
    assert sorted(path.name for path in ROOT.iterdir()) == before


def test_claude_intelligence_resolves_roles_and_catalog() -> None:
    from agent_phase.routing import claude_intelligence

    primary = claude_intelligence(ROOT, "implementation-primary")
    assert primary["model_role"] == "primary"
    assert primary["model"] == "claude-opus-5"
    assert primary["effort"] == "medium"
    assert primary["catalog"]["schema"] == "agent-central-claude-model-catalog-v1"
    assert primary["catalog"]["relativePath"] == "claude/model-catalog-v1.json"
    assert primary["catalog"]["bytes"] > 0
    assert len(primary["catalog"]["sha256"]) == 64

    review = claude_intelligence(ROOT, "implementation-review")
    assert review["model_role"] == "review"
    assert review["model"] == "claude-fable-5-1"
    assert review["effort"] == "medium"
    assert review["catalog"]["schema"] == "agent-central-claude-model-catalog-v1"


@pytest.mark.parametrize("mode", ["gemini_opus", "gemini_fable"])
@pytest.mark.parametrize("phase_type", ["implementation_testing", "architecture_docs", "sysadmin"])
def test_gemini_opus_and_gemini_fable_canonical_acceptance(mode: str, phase_type: str) -> None:
    request = PhaseRequest(phase_type, mode, "task")
    resolved = resolve(request, ROOT)
    stages = resolved["stages"]

    # Exactly 0 Codex parent stages
    assert all(stage["provider"] != "codex" for stage in stages.values())

    # Provider sequence: antigravity, claude, antigravity, claude, antigravity
    provider_sequence = [
        stages[name]["provider"]
        for name in ["plan", "plan_review", "work", "final_review", "closeout"]
    ]
    assert provider_sequence == ["antigravity", "claude", "antigravity", "claude", "antigravity"]

    # Plan, work, closeout are Gemini 3.8-Flash High
    for slot in ["plan", "work", "closeout"]:
        assert stages[slot]["profile"] == "gemini-3.8-flash-high"
        assert stages[slot]["intelligence"]["model"] == "gemini-3.8-flash-high"
        assert "worker_capability" not in stages[slot]

    # Review slots
    if mode == "gemini_opus":
        assert stages["plan_review"]["intelligence"]["model"] == "claude-opus-5"
        assert stages["plan_review"]["intelligence"]["effort"] == "high"
        assert stages["final_review"]["intelligence"]["model"] == "claude-opus-5"
        assert stages["final_review"]["intelligence"]["effort"] == "high"
    else:  # gemini_fable
        assert stages["plan_review"]["intelligence"]["model"] == "claude-fable-5-1"
        assert stages["plan_review"]["intelligence"]["effort"] == "high"
        assert stages["final_review"]["intelligence"]["model"] == "claude-opus-5"
        assert stages["final_review"]["intelligence"]["effort"] == "high"

    # Claude review stages have worker capability attached (allowed when agent_workers is present)
    for slot in ["plan_review", "final_review"]:
        worker_cap = stages[slot].get("worker_capability")
        assert worker_cap is not None
        try:
            __import__("agent_workers.policy")
            has_workers = True
        except ImportError:
            has_workers = False
        if has_workers:
            assert worker_cap["allowed"] is True
            assert worker_cap["limits"]["max_gemini"] == 4
        else:
            assert worker_cap["allowed"] is False

    # Lifecycle projections
    for lifecycle_name in ["standard", "solo", "plan-reviewed", "work-reviewed"]:
        spec = get_lifecycle(lifecycle_name)
        proj = resolve(request, ROOT, lifecycle_name)
        assert tuple(proj["stages"]) == spec.stage_names
        for stage in spec.stages:
            assert proj["stages"][stage.name]["provider"] in {"antigravity", "claude"}
