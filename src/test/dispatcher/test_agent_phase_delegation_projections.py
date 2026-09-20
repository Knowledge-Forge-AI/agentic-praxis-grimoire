"""Review-slot edits propagate through lifecycle projections, not other slots."""

from pathlib import Path

import pytest

from agent_phase.lifecycle import LIFECYCLE_NAMES, get_lifecycle
from agent_phase.request import PhaseRequest
from agent_phase.routing import resolve
from agent_phase_roster_fixtures import build_synthetic_roster, write_roster_sources


@pytest.mark.parametrize(
    "phase,slot",
    [("architecture_docs", "final_review"), ("sysadmin", "plan_review")],
)
def test_review_slot_change_preserves_projected_terminal_authority(
    tmp_path: Path, phase: str, slot: str
) -> None:
    fixture = build_synthetic_roster(tmp_path)
    request = PhaseRequest(phase, "gemini_sub", "bounded task")
    before = {
        name: resolve(request, fixture.root, name, "commit-local")
        for name in LIFECYCLE_NAMES
    }
    routes = {key: dict(value) for key, value in fixture.routes.items()}
    replacement = "fixture-claude-primary"
    assert routes[(phase, "gemini_sub")][slot] != replacement
    routes[(phase, "gemini_sub")][slot] = replacement
    write_roster_sources(
        fixture.root, fixture.endpoints, routes, generation=fixture.generation + 1
    )

    for name in LIFECYCLE_NAMES:
        after = resolve(request, fixture.root, name, "commit-local")
        lifecycle = get_lifecycle(name)
        assert after["roster"]["generation"] == fixture.generation + 1
        assert after["finalization_policy"] == "commit-local"
        assert after["expected_provider_invocations"] == len(lifecycle.stages)
        assert after["expected_review_count"] == len(lifecycle.checkpoints)
        for stage in lifecycle.stages:
            actual = after["stages"][stage.name]
            if stage.routing_slot == slot:
                assert actual["endpoint_alias"] == replacement
                assert actual["profile"] == "implementation-primary"
                assert actual["process_read_only"] is True
                assert actual["candidate_mutation"] is False
            else:
                assert actual == before[name]["stages"][stage.name]
        terminal = after["stages"][lifecycle.terminal_result_stage]
        assert terminal["candidate_mutation"] is True
        assert terminal["process_read_only"] is False
        if name != "standard":
            assert terminal["routing_source_slot"] == "work"
            assert terminal["endpoint_alias"] == routes[(phase, "gemini_sub")]["work"]
