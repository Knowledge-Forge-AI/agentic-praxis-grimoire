"""Routing and lifecycle regressions for the Gemini Flash parent mode."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest

from agent_phase.lifecycle import LIFECYCLE_NAMES, get_lifecycle
from agent_phase.request import EXECUTION_MODES, PHASE_TYPES, PhaseRequest, parse_request
from agent_phase.roster import STANDARD_SLOTS, Endpoint, load_roster
from agent_phase.routing import resolve, route

from test_agent_phase_dispatch import FakeRunner, make_dispatcher, repository as _repository

repository = _repository


ROOT = Path(__file__).resolve().parents[3]
FLASH_MODE = "gemini_flash_sub"
ASTRA_MODEL = "gpt-6-astra"
ASTRA_EFFORT = "medium"
FLASH_ENDPOINT = Endpoint("antigravity", "gemini-3.8-flash-high")

EXPECTED_GEMINI_SUB = {
    "implementation_testing": {
        "plan": "codex-architecture-docs-primary",
        "plan_review": "claude-normal-plan-review",
        "work": "codex-implementation-testing",
        "final_review": "claude-normal-final-review",
        "closeout": "codex-implementation-testing",
    },
    "architecture_docs": {
        "plan": "codex-architecture-docs-primary",
        "plan_review": "claude-normal-plan-review",
        "work": "codex-architecture-docs-primary",
        "final_review": "claude-normal-final-review",
        "closeout": "fable-architecture-docs-primary",
    },
    "sysadmin": {
        "plan": "codex-architecture-docs-primary",
        "plan_review": "claude-sysadmin-opus-review",
        "work": "codex-sysadmin-primary",
        "final_review": "claude-sysadmin-opus-review",
        "closeout": "codex-implementation-testing",
    },
}


def _request(phase_type: str, mode: str = FLASH_MODE) -> PhaseRequest:
    return PhaseRequest(phase_type, mode, "bounded Gemini Flash routing task")


def _is_astra_medium(root: Path, endpoint: Endpoint) -> bool:
    """Identify Astra from the provider-owned profile bytes, never an alias."""
    if endpoint.provider != "codex":
        return False
    path = root / "codex/profiles" / f"{endpoint.profile}.config.toml"
    try:
        profile = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    return (
        profile.get("model") == ASTRA_MODEL
        and profile.get("model_reasoning_effort") == ASTRA_EFFORT
    )


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
def test_strict_request_parser_accepts_gemini_flash_sub(phase_type: str) -> None:
    payload = {
        "schema": "agent-phase-request-v1",
        "phase_type": phase_type,
        "execution_mode": FLASH_MODE,
        "prompt": "bounded task",
    }

    request = parse_request(json.dumps(payload).encode("utf-8"))

    assert request == PhaseRequest(phase_type, FLASH_MODE, "bounded task")
    assert request.as_dict() == payload
    assert FLASH_MODE in EXECUTION_MODES


def test_gemini_sub_routes_are_unchanged() -> None:
    roster = load_roster(ROOT)

    for phase_type in PHASE_TYPES:
        assert dict(roster.route_aliases(phase_type, "gemini_sub")) == (
            EXPECTED_GEMINI_SUB[phase_type]
        )


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
def test_flash_route_is_an_actual_profile_based_gemini_sub_transform(
    phase_type: str,
) -> None:
    roster = load_roster(ROOT)
    source = roster.route_aliases(phase_type, "gemini_sub")
    transformed = roster.route_aliases(phase_type, FLASH_MODE)

    for slot in STANDARD_SLOTS:
        source_endpoint = roster.endpoints[source[slot]]
        target_endpoint = roster.endpoints[transformed[slot]]
        if _is_astra_medium(ROOT, source_endpoint):
            assert target_endpoint == FLASH_ENDPOINT
        else:
            assert target_endpoint == source_endpoint
            assert transformed[slot] == source[slot]

    # The architecture closeout is a Claude Fable stage and must stay exactly
    # where gemini_sub puts it, despite the substituted parent stages.
    if phase_type == "architecture_docs":
        assert transformed["closeout"] == source["closeout"]
    assert roster.generation == 7


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
@pytest.mark.parametrize("lifecycle", LIFECYCLE_NAMES)
def test_flash_resolve_and_route_preserve_lifecycle_projection(
    phase_type: str, lifecycle: str
) -> None:
    roster = load_roster(ROOT)
    specification = get_lifecycle(lifecycle)
    resolved = resolve(_request(phase_type), ROOT, lifecycle, "checkpoint")
    projected = route(_request(phase_type), lifecycle, root=ROOT, roster=roster)

    assert resolved["phase_type"] == phase_type
    assert resolved["execution_mode"] == FLASH_MODE
    assert resolved["lifecycle"] == lifecycle
    for stage in specification.stages:
        source_alias = roster.route_aliases(phase_type, FLASH_MODE)[stage.routing_slot]
        expected_endpoint = roster.endpoints[source_alias]
        actual_endpoint = projected[stage.name]
        assert actual_endpoint == expected_endpoint
        stage_record = resolved["stages"][stage.name]
        assert stage_record["endpoint_alias"] == source_alias
        assert (stage_record["provider"], stage_record["profile"]) == expected_endpoint
        effective = resolved["effective_stage_routes"][stage.name]
        assert (effective["provider"], effective["profile"]) == expected_endpoint

    # Substituted stages carry the provider-owned Gemini model readback.
    standard = resolve(_request(phase_type), ROOT, "standard", "checkpoint")
    for slot in STANDARD_SLOTS:
        source_endpoint = roster.endpoints[
            roster.route_aliases(phase_type, "gemini_sub")[slot]
        ]
        if _is_astra_medium(ROOT, source_endpoint):
            assert standard["stages"][slot]["provider"] == "antigravity"
            assert standard["stages"][slot]["profile"] == FLASH_ENDPOINT.profile
            assert standard["stages"][slot]["intelligence"]["model"] == (
                "gemini-3.8-flash-high"
            )


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
@pytest.mark.parametrize("lifecycle", LIFECYCLE_NAMES)
def test_flash_dry_run_records_mode_without_provider_invocation(
    repository: Path,
    tmp_path: Path,
    phase_type: str,
    lifecycle: str,
) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    phase_id = f"FLASH-{phase_type}-{lifecycle}"

    state = dispatcher.dry_run(
        phase_id,
        _request(phase_type),
        lifecycle,
        "checkpoint",
    )

    assert state["dry_run"] is True
    assert state["execution_mode"] == FLASH_MODE
    assert state["phase_type"] == phase_type
    assert state["lifecycle"] == lifecycle
    assert state["provider_invocations"] == 0
    run_directory = Path(state["run_directory"])
    resolved = json.loads((run_directory / "resolved.json").read_text())
    assert resolved["execution_mode"] == FLASH_MODE
    assert resolved["roster"]["generation"] == 7
    first_prefix = get_lifecycle(lifecycle).stages[0].prefix
    assert (run_directory / f"{first_prefix}.prompt.md").is_file()


FLASH_OPUS_MODE = "gemini_flash_opus_sub"

EXPECTED_FLASH_OPUS = {
    "implementation_testing": {
        "plan": "antigravity-gemini-high",
        "plan_review": "claude-normal-final-review",
        "work": "antigravity-gemini-high",
        "final_review": "claude-normal-final-review",
        "closeout": "antigravity-gemini-high",
    },
    "architecture_docs": {
        "plan": "antigravity-gemini-high",
        "plan_review": "claude-normal-final-review",
        "work": "antigravity-gemini-high",
        "final_review": "claude-normal-final-review",
        "closeout": "claude-architecture-docs-primary",
    },
    "sysadmin": {
        "plan": "antigravity-gemini-high",
        "plan_review": "claude-sysadmin-opus-review",
        "work": "antigravity-gemini-high",
        "final_review": "claude-sysadmin-opus-review",
        "closeout": "antigravity-gemini-high",
    },
}


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
def test_strict_request_parser_accepts_gemini_flash_opus_sub(phase_type: str) -> None:
    payload = {
        "schema": "agent-phase-request-v1",
        "phase_type": phase_type,
        "execution_mode": FLASH_OPUS_MODE,
        "prompt": "bounded flash opus task",
    }

    request = parse_request(json.dumps(payload).encode("utf-8"))

    assert request == PhaseRequest(phase_type, FLASH_OPUS_MODE, "bounded flash opus task")
    assert request.as_dict() == payload
    assert FLASH_OPUS_MODE in EXECUTION_MODES


def test_gemini_flash_opus_expected_routes() -> None:
    roster = load_roster(ROOT)

    for phase_type in PHASE_TYPES:
        assert dict(roster.route_aliases(phase_type, FLASH_OPUS_MODE)) == (
            EXPECTED_FLASH_OPUS[phase_type]
        )


def test_sysadmin_route_is_identical_to_gemini_flash_sub() -> None:
    roster = load_roster(ROOT)
    flash_routes = dict(roster.route_aliases("sysadmin", FLASH_MODE))
    opus_routes = dict(roster.route_aliases("sysadmin", FLASH_OPUS_MODE))
    assert opus_routes == flash_routes


def test_route_and_endpoint_generations_agree() -> None:
    roster = load_roster(ROOT)
    endpoints_doc = tomllib.loads(roster.endpoints_source.raw.decode("utf-8"))
    routes_doc = tomllib.loads(roster.routes_source.raw.decode("utf-8"))
    assert roster.generation == 7
    assert endpoints_doc["generation"] == routes_doc["generation"] == 7


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
def test_gemini_flash_sub_and_gemini_flash_opus_sub_route_transformation_invariant(
    phase_type: str,
) -> None:
    roster = load_roster(ROOT)
    flash_routes = roster.route_aliases(phase_type, FLASH_MODE)
    opus_routes = roster.route_aliases(phase_type, FLASH_OPUS_MODE)

    for slot in STANDARD_SLOTS:
        flash_alias = flash_routes[slot]
        flash_endpoint = roster.endpoints[flash_alias]
        opus_alias = opus_routes[slot]
        opus_endpoint = roster.endpoints[opus_alias]

        # 1. Resolve endpoint & determine actual provider/profile/model role from tracked source
        is_fable = False
        is_mutation_capable = False
        if flash_endpoint.provider == "claude":
            profile_path = ROOT / "claude/profiles" / f"{flash_endpoint.profile}.json"
            profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
            model_role = profile_data.get("modelRole")
            if model_role == "review":
                is_fable = True
            is_mutation_capable = profile_data.get("permissionMode") == "acceptEdits"

        # 2. Non-Fable slots must retain the exact same endpoint alias
        if not is_fable:
            assert opus_alias == flash_alias, (
                f"Non-Fable slot {phase_type}.{slot} changed alias: "
                f"{flash_alias} -> {opus_alias}"
            )
            assert opus_endpoint == flash_endpoint
        else:
            # 3. Fable slots must map to role-compatible Opus endpoints:
            if is_mutation_capable:
                # Mutation-capable architecture closeout Fable -> mutation-capable Opus architecture primary
                assert opus_alias == "claude-architecture-docs-primary"
                assert opus_endpoint == Endpoint("claude", "architecture-docs-primary")
            elif slot == "plan_review":
                # Read-only plan-review Fable -> role-compatible Opus review endpoint
                assert opus_alias == "claude-normal-final-review"
                assert opus_endpoint == Endpoint("claude", "normal-final-review")
            else:
                pytest.fail(
                    f"Unhandled gemini_flash_sub Claude Fable slot without explicit Opus mapping: "
                    f"{phase_type}.{slot} ({flash_alias})"
                )

        # 4. In the new mode, no effective slot may resolve to Claude Fable
        if opus_endpoint.provider == "claude":
            opus_profile_path = ROOT / "claude/profiles" / f"{opus_endpoint.profile}.json"
            opus_data = json.loads(opus_profile_path.read_text(encoding="utf-8"))
            assert opus_data.get("modelRole") != "review", (
                f"gemini_flash_opus_sub has effective Fable slot: {phase_type}.{slot}"
            )
            assert opus_data.get("modelRole") == "primary"


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
def test_resolver_intelligence_reports_opus_for_replaced_slots(phase_type: str) -> None:
    standard = resolve(_request(phase_type, FLASH_OPUS_MODE), ROOT, "standard", "checkpoint")
    replaced_slots = []
    if phase_type in ("implementation_testing", "architecture_docs"):
        replaced_slots.append("plan_review")
    if phase_type == "architecture_docs":
        replaced_slots.append("closeout")

    for slot in replaced_slots:
        stage = standard["stages"][slot]
        assert stage["provider"] == "claude"
        assert stage["intelligence"]["model"] == "claude-opus-5"
        assert stage["intelligence"]["model_role"] == "primary"

    if phase_type == "architecture_docs":
        assert standard["stages"]["closeout"]["candidate_mutation"] is True
        assert standard["stages"]["closeout"]["process_read_only"] is False


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
@pytest.mark.parametrize("lifecycle", LIFECYCLE_NAMES)
def test_flash_opus_resolve_and_route_preserve_lifecycle_projection(
    phase_type: str, lifecycle: str
) -> None:
    roster = load_roster(ROOT)
    specification = get_lifecycle(lifecycle)
    resolved = resolve(_request(phase_type, FLASH_OPUS_MODE), ROOT, lifecycle, "checkpoint")
    projected = route(_request(phase_type, FLASH_OPUS_MODE), lifecycle, root=ROOT, roster=roster)

    assert resolved["phase_type"] == phase_type
    assert resolved["execution_mode"] == FLASH_OPUS_MODE
    assert resolved["lifecycle"] == lifecycle
    for stage in specification.stages:
        source_alias = roster.route_aliases(phase_type, FLASH_OPUS_MODE)[stage.routing_slot]
        expected_endpoint = roster.endpoints[source_alias]
        actual_endpoint = projected[stage.name]
        assert actual_endpoint == expected_endpoint
        stage_record = resolved["stages"][stage.name]
        assert stage_record["endpoint_alias"] == source_alias
        assert (stage_record["provider"], stage_record["profile"]) == expected_endpoint
        effective = resolved["effective_stage_routes"][stage.name]
        assert (effective["provider"], effective["profile"]) == expected_endpoint


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
@pytest.mark.parametrize("lifecycle", LIFECYCLE_NAMES)
def test_flash_opus_dry_run_records_mode_without_provider_invocation(
    repository: Path,
    tmp_path: Path,
    phase_type: str,
    lifecycle: str,
) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    phase_id = f"FLASH-OPUS-{phase_type}-{lifecycle}"

    state = dispatcher.dry_run(
        phase_id,
        _request(phase_type, FLASH_OPUS_MODE),
        lifecycle,
        "checkpoint",
    )

    assert state["dry_run"] is True
    assert state["execution_mode"] == FLASH_OPUS_MODE
    assert state["phase_type"] == phase_type
    assert state["lifecycle"] == lifecycle
    assert state["provider_invocations"] == 0
    run_directory = Path(state["run_directory"])
    resolved = json.loads((run_directory / "resolved.json").read_text())
    assert resolved["execution_mode"] == FLASH_OPUS_MODE
    assert resolved["roster"]["generation"] == 7
    first_prefix = get_lifecycle(lifecycle).stages[0].prefix
    assert (run_directory / f"{first_prefix}.prompt.md").is_file()
