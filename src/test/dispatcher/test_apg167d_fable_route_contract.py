"""v0.13 effective alias and specialist closeout contracts; launches nothing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_phase.bundle import load_bundle
from agent_phase.capabilities import load_capabilities
from agent_phase.config_routing import SUPPORTED_EXECUTION_MODES
from agent_phase.dynamic_router import OperationalObservation, resolve_dynamic_route
from agent_phase.lifecycle import LIFECYCLE_NAMES, get_lifecycle
from agent_phase.provider import build_argv
from agent_phase.request import EXECUTION_MODES, PHASE_TYPES, PhaseRequest, parse_request
from agent_phase.roster import Endpoint
from agent_phase.routing import load_validated_roster, resolve
from agent_phase.runtime_models import captured, parent_family_for_endpoint, selection
from agent_phase.semantic_roles import create_default_binding_policy
from claude_model_catalog import load_catalog
from claude_vc_profile import PROFILE_CONTRACTS, resolve_profile

ROOT = Path(__file__).resolve().parents[3]
FABLE = "fable-architecture-docs-primary"
OPUS_ARCHITECTURE_ALIASES = (
    "claude-architecture-docs-primary", "claude-only-architecture-docs-primary",
)
REVIEW_IDENTITIES = {
    "implementation_testing": (
        ("claude-normal-final-review", "normal-final-review", "primary", "primary"),
        ("claude-normal-plan-review", "normal-plan-review", "review", "review"),
    ),
    "architecture_docs": (
        ("claude-normal-final-review", "normal-final-review", "primary", "primary"),
        ("claude-normal-plan-review", "normal-plan-review", "review", "review"),
    ),
    "sysadmin": (
        ("claude-sysadmin-opus-review", "sysadmin-opus-review", "primary", "primary"),
        ("claude-normal-sysadmin-plan-review", "normal-sysadmin-plan-review", "review", "review"),
    ),
}


@pytest.fixture
def isolated_context(tmp_path, monkeypatch):
    apgr_home = tmp_path / "apgr"
    monkeypatch.setenv("APGR_HOME", str(apgr_home))
    bundle = load_bundle(apgr_home=apgr_home, repo_root=ROOT)
    assert bundle.manifest["authority"] == "source_default"
    return bundle, load_validated_roster(ROOT, apgr_home=apgr_home)


@pytest.mark.parametrize("phase", PHASE_TYPES)
def test_gemini_fable_and_gemini_opus_remain_separately_accepted(isolated_context, phase):
    bundle, roster = isolated_context
    with captured(bundle):
        for mode in ("gemini_fable", "gemini_opus"):
            assert mode in EXECUTION_MODES
            assert mode in SUPPORTED_EXECUTION_MODES
            request = parse_request(json.dumps({
                "schema": "agent-phase-request-v1", "phase_type": phase,
                "execution_mode": mode, "prompt": "compatibility contract",
            }).encode())
            assert (request.phase_type, request.execution_mode) == (phase, mode)
            assert (phase, mode) in roster.routes
            assert resolve(request, ROOT, roster=roster)["execution_mode"] == mode


def stage_identity(stage, bundle):
    inventory = selection(ROOT, stage["provider"], stage["profile"], bundle=bundle)
    return (stage["endpoint_alias"], stage["profile"],
            stage["intelligence"].get("model_role"), inventory.get("role"))


def stage_launch_transport(stage):
    argv = build_argv(Endpoint(stage["provider"], stage["profile"]), stage["role"],
                      ROOT, read_only=stage["process_read_only"], pin_profile=False)
    # These compatibility modes have Claude/Antigravity launchers only. Permit
    # exactly the profile operand to differ, retaining executable and flags.
    assert stage["provider"] in {"claude", "antigravity"}
    assert argv[1] == stage["profile"]
    return (argv[0], "<profile>", *argv[2:])


def assert_profile_launch_equivalent(opus, fable):
    profiles = [resolve_profile(ROOT, stage["profile"]) for stage in (opus, fable)]
    contracts = [PROFILE_CONTRACTS[stage["profile"]] for stage in (opus, fable)]
    assert profiles[0].minimum_version == profiles[1].minimum_version
    assert profiles[0].adaptive_thinking == profiles[1].adaptive_thinking
    assert contracts[0]._replace(model_role="<role>") == contracts[1]._replace(model_role="<role>")
    assert ({k:v for k,v in profiles[0].source_profile.items() if k != "modelRole"}
            == {k:v for k,v in profiles[1].source_profile.items() if k != "modelRole"})


def assert_stage_launch_equivalent(opus, fable, bundle):
    for field in ("provider", "process_read_only", "process_posture", "role",
                  "routing_source_slot", "candidate_mutation", "artifact_prefix",
                  "review_checkpoint", "candidate_binding_key", "worker_capability"):
        assert opus.get(field) == fable.get(field), field
    assert ({k:v for k,v in opus["intelligence"].items() if k != "model_role"}
            == {k:v for k,v in fable["intelligence"].items() if k != "model_role"})
    assert stage_launch_transport(opus) == stage_launch_transport(fable)
    # Name worker transport explicitly in addition to whole-capability equality.
    for kind in ("gemini_worker", "luna_worker", "sonnet_worker", "native_worker"):
        assert ((opus.get("worker_capability") or {}).get(kind, {}).get("transport")
                == (fable.get("worker_capability") or {}).get(kind, {}).get("transport"))
    if opus["provider"] == "claude":
        assert_profile_launch_equivalent(opus, fable)
    for stage in (opus, fable):
        assert "fable" not in stage["intelligence"]["model"].lower()
        assert parent_family_for_endpoint(ROOT, stage["provider"], stage["profile"],
                                          bundle=bundle) != "claude_fable"


@pytest.mark.parametrize("phase", PHASE_TYPES)
@pytest.mark.parametrize("lifecycle", LIFECYCLE_NAMES)
def test_gemini_fable_is_effective_alias_of_gemini_opus(isolated_context, phase, lifecycle):
    bundle, roster = isolated_context
    with captured(bundle):
        opus, fable = [resolve(PhaseRequest(phase, mode, "contract"), ROOT, lifecycle,
                              "checkpoint", roster=roster)
                       for mode in ("gemini_opus", "gemini_fable")]
        spec = get_lifecycle(lifecycle)
        assert tuple(opus["stages"]) == tuple(fable["stages"]) == spec.stage_names
        for field in ("checkpoints", "checkpoint_count", "expected_review_count",
                      "provider_invocations", "terminal_result_stage"):
            assert opus[field] == fable[field]
        differences = {}
        for name in spec.stage_names:
            stages = opus["stages"][name], fable["stages"][name]
            assert_stage_launch_equivalent(*stages, bundle)
            identities = tuple(stage_identity(stage, bundle) for stage in stages)
            if identities[0] != identities[1]:
                differences[name] = identities
        expected = {"plan_review": REVIEW_IDENTITIES[phase]} if "plan_review" in spec.stage_names else {}
        assert differences == expected


def assert_fable_specialist(stage):
    assert stage["provider"] == "claude"
    assert stage["endpoint_alias"] == stage["profile"] == FABLE
    assert stage["intelligence"]["model"] == "claude-fable-5-1"
    assert stage["intelligence"]["effort"] == "high"
    assert stage["intelligence"]["model_role"] == "review"
    profile = resolve_profile(ROOT, FABLE)
    assert profile.minimum_version == "2.1.250"
    assert profile.model_role == "review"
    assert profile.source_profile["permissionMode"] == "acceptEdits"
    assert profile.source_profile["additionalDirectories"] == ["scratch"]
    assert PROFILE_CONTRACTS[FABLE].isolated_settings is False


def test_fable_route_exceptions_are_exactly_two_and_other_claude_parents_are_opus(isolated_context):
    bundle, roster = isolated_context
    observed = set()
    with captured(bundle):
        for phase, mode in roster.routes:
            if mode == "dynamic":
                continue
            for lifecycle in LIFECYCLE_NAMES:
                stages = resolve(PhaseRequest(phase, mode, "contract"), ROOT,
                                 lifecycle, "checkpoint", roster=roster)["stages"]
                for stage in stages.values():
                    if stage["profile"] == FABLE or "fable" in stage["intelligence"]["model"].lower():
                        observed.add((phase, mode, stage["routing_source_slot"]))
                        assert_fable_specialist(stage)
                    elif stage["provider"] == "claude":
                        assert stage["intelligence"]["model"] == "claude-opus-5-5"
                        assert resolve_profile(ROOT, stage["profile"]).minimum_version is None
        assert observed == {("architecture_docs", "normal", "closeout"),
                            ("architecture_docs", "gemini_flash_sub", "closeout")}


@pytest.mark.parametrize("mode", ("normal", "gemini_flash_sub"))
def test_architecture_docs_fable_closeout_identity(isolated_context, mode):
    bundle, roster = isolated_context
    with captured(bundle):
        stage = resolve(PhaseRequest("architecture_docs", mode, "contract"), ROOT,
                        finalization_policy="checkpoint", roster=roster)["stages"]["closeout"]
        assert_fable_specialist(stage)
        catalog = load_catalog(ROOT)
        assert catalog.models["fable-current"].id == "claude-fable-5-1"
        assert catalog.models["fable-current"].minimum_claude_code_version == "2.1.250"
        for role in ("primary", "review", "opus"):
            assert catalog.roles[role] == "opus-5-5"
            assert bundle.models_catalog["roles"]["claude"][role] == "claude-opus-5-5"


@pytest.mark.parametrize("phase", PHASE_TYPES)
def test_dynamic_default_never_selects_fable(isolated_context, phase):
    bundle, roster = isolated_context
    catalog = load_capabilities(ROOT, roster=roster)
    for binding in create_default_binding_policy().bindings:
        route = resolve_dynamic_route(binding, phase, capabilities_catalog=catalog,
            now=100.0, execution_mode="dynamic", worker_qualifier=lambda _ep: True,
            root=ROOT, bundle=bundle)
        assert route.profile != FABLE
        assert "fable" not in selection(ROOT, route.provider, route.profile, bundle=bundle)["model"].lower()


@pytest.mark.parametrize("mechanism", ("exclusion", "score-only"))
def test_dynamic_fable_selection_follows_observation_ranking(isolated_context, mechanism):
    bundle, roster = isolated_context
    catalog = load_capabilities(ROOT, roster=roster)
    binding = create_default_binding_policy().get_binding("binding_work")
    profiles = ("architecture-docs-primary", "claude-only-architecture-docs-primary") if mechanism == "exclusion" else (FABLE,)
    observations = [OperationalObservation("observation-"+profile, "contract", "availability",
        "claude", profile, timestamp=100.0,
        state_value="unavailable" if mechanism == "exclusion" else "available")
        for profile in profiles]
    route = resolve_dynamic_route(binding, "architecture_docs", capabilities_catalog=catalog,
        operational_observations=observations, now=100.0, execution_mode="dynamic",
        worker_qualifier=lambda _ep: True, root=ROOT, bundle=bundle)
    assert route.provider == "claude"
    assert route.profile == route.endpoint_alias == FABLE
    assert selection(ROOT, route.provider, route.profile, bundle=bundle)["model"] == "claude-fable-5-1"
    for alias in OPUS_ARCHITECTURE_ALIASES:
        assert (alias in (route.rejections or {})) is (mechanism == "exclusion")
