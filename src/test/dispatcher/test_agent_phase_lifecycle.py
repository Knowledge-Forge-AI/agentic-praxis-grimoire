from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_phase import cli as cli_module
from agent_phase.lifecycle import (
    FINALIZATION_POLICIES,
    LIFECYCLE_NAMES,
    LifecycleError,
    get_lifecycle,
)
from agent_phase.request import EXECUTION_MODES, PHASE_TYPES, PhaseRequest
from agent_phase.routing import resolve, route


ROOT = Path(__file__).resolve().parents[3]

EXPECTED = {
    "standard": {
        "stages": ("plan", "plan_review", "work", "final_review", "closeout"),
        "slots": ("plan", "plan_review", "work", "final_review", "closeout"),
        "prefixes": (
            "01-plan", "02-plan-review", "03-work", "04-final-review", "05-closeout",
        ),
        "checkpoints": ("post_planning", "pre_final"),
        "terminal": "closeout",
        "invocations": 5,
    },
    "solo": {
        "stages": ("solo",),
        "slots": ("work",),
        "prefixes": ("01-solo",),
        "checkpoints": (),
        "terminal": "solo",
        "invocations": 1,
    },
    "plan-reviewed": {
        "stages": ("plan", "plan_review", "produce_close"),
        "slots": ("plan", "plan_review", "work"),
        "prefixes": ("01-plan", "02-plan-review", "03-produce-close"),
        "checkpoints": ("post_planning",),
        "terminal": "produce_close",
        "invocations": 3,
    },
    "work-reviewed": {
        "stages": ("produce", "work_review", "revise_close"),
        "slots": ("work", "final_review", "work"),
        "prefixes": ("01-produce", "02-work-review", "03-revise-close"),
        "checkpoints": ("post_work",),
        "terminal": "revise_close",
        "invocations": 3,
    },
}


def request(phase_type: str = "implementation_testing", mode: str = "normal"):
    return PhaseRequest(phase_type, mode, "bounded task")


def test_registry_is_closed_and_exact() -> None:
    assert LIFECYCLE_NAMES == tuple(EXPECTED)
    assert FINALIZATION_POLICIES == ("publish", "commit-local", "checkpoint")
    with pytest.raises(LifecycleError, match="unknown lifecycle"):
        get_lifecycle("reviewed")


@pytest.mark.parametrize("name", EXPECTED)
def test_registry_owns_stage_graph_and_counts(name: str) -> None:
    expected = EXPECTED[name]
    lifecycle = get_lifecycle(name)
    assert lifecycle.stage_names == expected["stages"]
    assert tuple(stage.routing_slot for stage in lifecycle.stages) == expected["slots"]
    assert tuple(stage.prefix for stage in lifecycle.stages) == expected["prefixes"]
    assert lifecycle.checkpoints == expected["checkpoints"]
    assert lifecycle.terminal_result_stage == expected["terminal"]
    assert lifecycle.expected_provider_invocations == expected["invocations"]
    assert lifecycle.expected_review_count == len(expected["checkpoints"])


@pytest.mark.parametrize("name", EXPECTED)
@pytest.mark.parametrize("phase_type", PHASE_TYPES)
@pytest.mark.parametrize("mode", EXECUTION_MODES)
def test_every_request_combination_resolves_for_every_lifecycle(
    name: str, phase_type: str, mode: str
) -> None:
    resolved = resolve(request(phase_type, mode), ROOT, name, "checkpoint")
    expected = EXPECTED[name]
    assert resolved["schema"] == "agent-phase-resolved-v6"
    assert resolved["lifecycle"] == name
    assert resolved["finalization_policy"] == "checkpoint"
    assert tuple(resolved["stages"]) == expected["stages"]
    assert resolved["expected_stages"] == list(expected["stages"])
    assert resolved["provider_invocations"] == expected["invocations"]
    assert resolved["expected_provider_invocations"] == expected["invocations"]
    assert resolved["checkpoint_count"] == len(expected["checkpoints"])
    assert resolved["expected_review_count"] == len(expected["checkpoints"])
    assert resolved["terminal_result_stage"] == expected["terminal"]
    for stage, source_slot in zip(expected["stages"], expected["slots"], strict=True):
        assert resolved["stages"][stage]["routing_source_slot"] == source_slot


def test_lightweight_routes_are_projections_of_standard_route() -> None:
    standard = route(request())
    for lifecycle_name, expected in EXPECTED.items():
        projected = route(request(), lifecycle_name)
        for stage, source_slot in zip(
            expected["stages"], expected["slots"], strict=True
        ):
            assert projected[stage] == standard[source_slot]


def test_lightweight_projections_are_exact() -> None:
    for phase_type in PHASE_TYPES:
        for mode in EXECUTION_MODES:
            request_value = request(phase_type, mode)
            standard = route(request_value)
            for lifecycle_name in ("solo", "plan-reviewed", "work-reviewed"):
                specification = get_lifecycle(lifecycle_name)
                projected = route(request_value, lifecycle_name)
                for stage in specification.stages:
                    assert projected[stage.name] == standard[stage.routing_slot]


def test_standard_plan_is_process_read_only_for_every_route() -> None:
    for phase_type in PHASE_TYPES:
        for mode in EXECUTION_MODES:
            resolved = resolve(request(phase_type, mode), ROOT)
            assert resolved["stages"]["plan"]["process_read_only"] is True


def test_resolve_cli_accepts_operator_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    request_path = tmp_path / "PHASE.request.json"
    request_path.write_text(json.dumps({
        "schema": "agent-phase-request-v1",
        "phase_type": "implementation_testing",
        "execution_mode": "codex_only",
        "prompt": "task prose cannot choose lifecycle",
    }))
    monkeypatch.setattr(cli_module, "repository_root", lambda: ROOT)

    assert cli_module.resolve_main([
        str(request_path),
        "--lifecycle", "work-reviewed",
        "--finalization", "commit-local",
    ]) == 0

    resolved = json.loads(capsys.readouterr().out)
    assert resolved["lifecycle"] == "work-reviewed"
    assert resolved["finalization_policy"] == "commit-local"
    assert resolved["expected_stages"] == ["produce", "work_review", "revise_close"]
