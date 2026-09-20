"""Tests for AGENTCENTRAL-RESUME-ROSTER1: Route Resumed Suffixes from Current TOML Roster."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pytest

from agent_phase import resume as resume_module
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.request import PhaseRequest
from agent_phase.route_provenance import (
    BOUNDED_ROUTE_FIELDS,
    RESOLVED_V4,
    RESOLVED_V6,
    ROSTER_COMPATIBILITY_FINALIZATION,
    ROSTER_COMPATIBILITY_INHERITED,
)
from agent_phase.routing import RoutingError
from agent_phase_roster_fixtures import (
    SYNTHETIC_ENDPOINTS,
    build_synthetic_roster,
    synthetic_routes,
    write_roster_sources,
)
from test_agent_phase_resume import PHASE as SOURCE_PHASE, REQUEST as SOURCE_REQUEST, Runner, duplicate_source, only_run, repository as _repository
from test_agent_phase_output_recovery import (
    PHASE as RECOVERY_PHASE,
    REQUEST as RECOVERY_REQUEST,
    RecoveryRunner,
    digest_tree,
    make_source as make_recovery_source,
)

repository = _repository


PHASE = "ROSTER-TRANSITION-1"
REQUEST = PhaseRequest("implementation_testing", "normal", "Implement the change.")


def default_routes() -> dict[tuple[str, str], dict[str, str]]:
    routes = synthetic_routes("mixed")
    routes[(REQUEST.phase_type, REQUEST.execution_mode)] = {
        "plan": "fixture-codex-primary",
        "plan_review": "fixture-codex-review",
        "work": "fixture-codex-primary",
        "final_review": "fixture-codex-review",
        "closeout": "fixture-codex-primary",
    }
    return routes


def make_dispatcher(
    repository: Path, run_root: Path, runner: Any, *, root: Path
) -> Dispatcher:
    return Dispatcher(
        root=root,
        cwd=repository,
        run_root=run_root,
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )


def make_failed_source(
    roster_root: Path,
    repository: Path,
    run_root: Path,
    fail_at: int,
    *,
    mutate_at: int | None = None,
    lifecycle: str = "standard",
) -> Path:
    runner = Runner(fail_at=fail_at, mutate_at=mutate_at)
    disp = make_dispatcher(repository, run_root, runner, root=roster_root)
    with pytest.raises(DispatchError):
        disp.dispatch(PHASE, REQUEST, lifecycle=lifecycle)
    return only_run(run_root)


def test_preflight_without_current_roster_labels_suffix_unexecuted(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster")
    write_roster_sources(
        roster_fixture.root,
        SYNTHETIC_ENDPOINTS,
        default_routes(),
        generation=41,
    )
    source = make_failed_source(
        roster_fixture.root,
        repository,
        tmp_path / "source",
        fail_at=1,
    )

    plan = resume_module.preflight(
        source,
        "auto",
        PHASE,
        REQUEST,
        repository,
        repository.name,
        None,
        check_route=False,
    )

    assert plan.effective_stage_routes["plan"]["source"] == "inherited"
    assert all(
        plan.effective_stage_routes[stage]["source"] == "unexecuted"
        for stage in plan.lifecycle.stage_names[1:]
    )


# Scenario 1: V5/V6 generation and suffix-route changes
def test_source_generation_and_suffix_route_change_advances_suffix_and_preserves_prefix(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster_v1")
    roster_root = roster_fixture.root
    routes_v1 = default_routes()
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v1, generation=41)

    source = make_failed_source(roster_root, repository, tmp_path / "source", fail_at=2)
    source_resolved = json.loads((source / "resolved.json").read_text())
    source_state = json.loads((source / "state.json").read_text())
    assert source_resolved["schema"] == RESOLVED_V6
    assert source_resolved["roster"]["generation"] == 41

    routes_v2 = default_routes()
    # Change work route for normal to fixture-claude-primary
    routes_v2[(REQUEST.phase_type, REQUEST.execution_mode)]["work"] = "fixture-claude-primary"
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v2, generation=42)

    runner = Runner()
    resumed = make_dispatcher(
        repository, tmp_path / "resumed", runner, root=roster_root
    ).resume(
        PHASE, REQUEST, source, from_stage="auto", finalization_policy="checkpoint"
    )

    assert resumed["outcome"] == "completed"
    assert resumed["resume"]["inherited_stages"] == ["plan", "plan_review"]
    effective_routes = resumed["effective_stage_routes"]

    assert effective_routes["plan"]["source"] == "inherited"
    assert effective_routes["plan"]["route_selecting_run_id"] == source_state["run_id"]
    assert effective_routes["plan"]["roster"]["generation"] == 41

    assert effective_routes["work"]["source"] == "current"
    assert effective_routes["work"]["route_selecting_run_id"] == resumed["run_id"]
    assert effective_routes["work"]["roster"]["generation"] == 42
    assert effective_routes["work"]["provider"] == "claude"
    assert effective_routes["work"]["profile"] == "implementation-primary"

    transition = resumed["route_transition"]
    assert transition["roster_changed"] is True
    assert transition["source_roster"]["generation"] == 41
    assert transition["current_roster"]["generation"] == 42
    assert "work" in transition["route_differences"]
    assert transition["route_differences"]["work"]["status"] == "changed_and_executed"


# Scenario 2: Unrelated roster edit allowed and recorded
def test_unrelated_roster_edit_allowed_and_provenance_recorded(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster")
    roster_root = roster_fixture.root
    routes_v1 = default_routes()
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v1, generation=41)

    source = make_failed_source(roster_root, repository, tmp_path / "source", fail_at=2)

    routes_v2 = default_routes()
    # Change plan route (already completed/inherited)
    routes_v2[(REQUEST.phase_type, REQUEST.execution_mode)]["plan"] = "fixture-claude-primary"
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v2, generation=42)

    runner = Runner()
    resumed = make_dispatcher(
        repository, tmp_path / "resumed", runner, root=roster_root
    ).resume(PHASE, REQUEST, source, from_stage="work", finalization_policy="checkpoint")

    assert resumed["outcome"] == "completed"
    assert resumed["route_transition"]["roster_changed"] is True
    assert resumed["route_transition"]["route_differences"]["plan"]["status"] == "changed_but_not_executed"
    assert "work" not in resumed["route_transition"]["route_differences"]


# Scenario 3: Replayed stage uses current roster while still-inherited prefix keeps historical
def test_replayed_stage_uses_current_roster_and_inherited_keeps_historical(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster")
    roster_root = roster_fixture.root
    routes_v1 = default_routes()
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v1, generation=41)

    source = make_failed_source(
        roster_root, repository, tmp_path / "source", fail_at=3, mutate_at=2
    )
    source_state = json.loads((source / "state.json").read_text())

    routes_v2 = default_routes()
    routes_v2[(REQUEST.phase_type, REQUEST.execution_mode)]["work"] = "fixture-claude-primary"
    routes_v2[(REQUEST.phase_type, REQUEST.execution_mode)]["final_review"] = "fixture-claude-review"
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v2, generation=42)

    runner = Runner()
    resumed = make_dispatcher(
        repository, tmp_path / "resumed", runner, root=roster_root
    ).resume(PHASE, REQUEST, source, from_stage="work", finalization_policy="checkpoint")

    assert resumed["outcome"] == "completed"
    assert resumed["resume"]["inherited_stages"] == ["plan", "plan_review"]
    effective = resumed["effective_stage_routes"]
    assert effective["plan"]["source"] == "inherited"
    assert effective["plan"]["route_selecting_run_id"] == source_state["run_id"]
    assert effective["work"]["source"] == "current"
    assert effective["work"]["provider"] == "claude"
    assert effective["work"]["route_selecting_run_id"] == resumed["run_id"]


# Scenario 4: Chained resumes across three roster generations
def test_chained_resumes_three_generations_preserve_provenance_ledger(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster")
    roster_root = roster_fixture.root
    routes_v1 = default_routes()
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v1, generation=41)

    # Gen 41: Run 1 fails at stage 2 (work)
    run1_dir = make_failed_source(roster_root, repository, tmp_path / "run1", fail_at=2)
    run1_state = json.loads((run1_dir / "state.json").read_text())
    run1_id = run1_state["run_id"]

    # Gen 42: advance roster and resume; Run 2 mutates at 0 (work) and fails at 1 (final_review)
    routes_v2 = default_routes()
    routes_v2[(REQUEST.phase_type, REQUEST.execution_mode)]["work"] = "fixture-claude-primary"
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v2, generation=42)

    runner2 = Runner(fail_at=1, mutate_at=0)
    with pytest.raises(DispatchError):
        make_dispatcher(
            repository, tmp_path / "run2", runner2, root=roster_root
        ).resume(PHASE, REQUEST, run1_dir, from_stage="work")
    run2_dir = only_run(tmp_path / "run2")
    run2_state = json.loads((run2_dir / "state.json").read_text())
    run2_id = run2_state["run_id"]

    # Gen 43: advance roster again, changing closeout; Run 3 completes from final_review
    routes_v3 = default_routes()
    routes_v3[(REQUEST.phase_type, REQUEST.execution_mode)]["work"] = "fixture-claude-primary"
    routes_v3[(REQUEST.phase_type, REQUEST.execution_mode)]["closeout"] = "fixture-claude-primary"
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v3, generation=43)

    runner3 = Runner()
    run3 = make_dispatcher(
        repository, tmp_path / "run3", runner3, root=roster_root
    ).resume(PHASE, REQUEST, run2_dir, from_stage="auto", finalization_policy="checkpoint")

    assert run3["outcome"] == "completed"
    effective = run3["effective_stage_routes"]
    # plan from Run 1 (Gen 41)
    assert effective["plan"]["source"] == "inherited"
    assert effective["plan"]["route_selecting_run_id"] == run1_id
    assert effective["plan"]["roster"]["generation"] == 41

    # work from Run 2 (Gen 42)
    assert effective["work"]["source"] == "inherited"
    assert effective["work"]["route_selecting_run_id"] == run2_id
    assert effective["work"]["roster"]["generation"] == 42
    assert effective["work"]["provider"] == "claude"

    # closeout from Run 3 (Gen 43)
    assert effective["closeout"]["source"] == "current"
    assert effective["closeout"]["route_selecting_run_id"] == run3["run_id"]
    assert effective["closeout"]["roster"]["generation"] == 43
    assert effective["closeout"]["endpoint_alias"] == "fixture-claude-primary"


# Scenario 5: Current route validation remains fail-closed pre-provider
def test_current_route_validation_fails_closed_before_provider(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster")
    roster_root = roster_fixture.root
    routes_v1 = default_routes()
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v1, generation=41)

    source = make_failed_source(roster_root, repository, tmp_path / "source", fail_at=2)

    # Subcase A: Malformed TOML syntax
    (roster_root / "common/dispatcher/endpoints.toml").write_text("invalid = [toml")
    runner = Runner()
    with pytest.raises((DispatchError, RoutingError)):
        make_dispatcher(repository, tmp_path / "rA", runner, root=roster_root).resume(
            PHASE, REQUEST, source, from_stage="work"
        )
    assert runner.calls == []

    # Subcase B: Generation mismatch
    build_synthetic_roster(tmp_path / "roster_b")
    roster_root_b = tmp_path / "roster_b/repository"
    write_roster_sources(roster_root_b, SYNTHETIC_ENDPOINTS, default_routes(), generation=41)
    (roster_root_b / "common/dispatcher/endpoints.toml").write_text(
        (roster_root_b / "common/dispatcher/endpoints.toml").read_text().replace("generation = 41", "generation = 42")
    )
    runner = Runner()
    with pytest.raises((DispatchError, RoutingError)):
        make_dispatcher(repository, tmp_path / "rB", runner, root=roster_root_b).resume(
            PHASE, REQUEST, source, from_stage="work"
        )
    assert runner.calls == []

    # Subcase C: Reviewer stage lacks read-only posture in current resolution
    build_synthetic_roster(tmp_path / "roster_c")
    roster_root_c = tmp_path / "roster_c/repository"
    write_roster_sources(roster_root_c, SYNTHETIC_ENDPOINTS, default_routes(), generation=41)
    runner = Runner()
    import agent_phase.resume_dispatch as rdm
    real_resolve = rdm.resolve

    def non_read_only(req, root, lifecycle="standard", finalization_policy="publish", *, roster=None):
        val = real_resolve(req, root, lifecycle, finalization_policy, roster=roster)
        val["stages"]["final_review"]["process_read_only"] = False
        return val

    monkey = pytest.MonkeyPatch()
    monkey.setattr(rdm, "resolve", non_read_only)
    try:
        with pytest.raises(DispatchError) as caught:
            make_dispatcher(repository, tmp_path / "rC", runner, root=roster_root_c).resume(
                PHASE, REQUEST, source, from_stage="work"
            )
        assert caught.value.code == "RESUME_CURRENT_ROUTE_INVALID"
        assert runner.calls == []
    finally:
        monkey.undo()


# Scenario 6: Finalization-only resume loads no current roster and tolerates broken TOML
def test_finalization_only_resume_loads_no_current_roster_even_if_toml_invalid(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = duplicate_source(repository, tmp_path, monkeypatch)

    # Sabotage repository current roster
    roster_root = tmp_path / "broken_roster"
    roster_root.mkdir()
    (roster_root / "common/dispatcher").mkdir(parents=True)
    (roster_root / "common/dispatcher/endpoints.toml").write_text("INVALID BROKEN SYNTAX")

    finalize_runner = Runner()
    resumed = make_dispatcher(
        repository, tmp_path / "resumed", finalize_runner, root=roster_root
    ).resume(SOURCE_PHASE, SOURCE_REQUEST, source, from_stage="finalize", dry_run=True)

    assert finalize_runner.calls == []
    assert resumed["outcome"] == "dry_run"
    assert resumed["provider_invocations_performed"] == 0
    assert resumed["resume"]["roster_compatibility"] == ROSTER_COMPATIBILITY_FINALIZATION
    assert resumed["effective_stage_routes"]["plan"]["source"] == "inherited"


# Scenario 7: Historical V4 source resumed under new current V6 route
def test_v4_historical_source_resumed_with_current_v6_suffix(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster")
    roster_root = roster_fixture.root
    routes_v1 = default_routes()
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v1, generation=41)

    source = make_failed_source(roster_root, repository, tmp_path / "source", fail_at=2)

    # Downgrade source resolved.json to V4
    resolved_path = source / "resolved.json"
    v4_resolved = json.loads(resolved_path.read_text())
    v4_resolved["schema"] = RESOLVED_V4
    v4_resolved.pop("roster", None)
    v4_resolved.pop("effective_stage_routes", None)
    v4_resolved.pop("route_transition", None)
    for st in v4_resolved["stages"].values():
        st.pop("endpoint_alias", None)
    resolved_path.write_text(json.dumps(v4_resolved, indent=2, sort_keys=True) + "\n")

    # Advance roster to Gen 42
    routes_v2 = default_routes()
    routes_v2[(REQUEST.phase_type, REQUEST.execution_mode)]["work"] = "fixture-claude-primary"
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v2, generation=42)

    runner = Runner()
    resumed = make_dispatcher(
        repository, tmp_path / "resumed", runner, root=roster_root
    ).resume(PHASE, REQUEST, source, from_stage="work", finalization_policy="checkpoint")

    assert resumed["outcome"] == "completed"
    assert resumed["resume"]["roster_compatibility"] == ROSTER_COMPATIBILITY_INHERITED
    assert resumed["effective_stage_routes"]["plan"]["source"] == "inherited"
    assert resumed["effective_stage_routes"]["plan"]["source_schema"] == RESOLVED_V4
    assert resumed["effective_stage_routes"]["plan"]["roster"] == {"status": "not_recorded"}
    assert resumed["effective_stage_routes"]["work"]["source"] == "current"
    assert resumed["effective_stage_routes"]["work"]["source_schema"] == RESOLVED_V6
    assert resumed["effective_stage_routes"]["work"]["roster"]["generation"] == 42


# Scenario 8: Antigravity output recovery accepts changed suffix route and preserves producer
def test_antigravity_output_recovery_accepts_changed_suffix_route(
    repository: Path, tmp_path: Path
) -> None:
    source, response, fixture = make_recovery_source(repository, tmp_path)
    before_tree = digest_tree(source)

    runner = RecoveryRunner(repository, response, fixture["candidate_paths"][0])
    resumed = Dispatcher(
        Path(__file__).resolve().parents[3],
        repository,
        run_root=tmp_path / "recovered",
        runner=runner,
        resolve_scanner=False,
    ).resume(
        RECOVERY_PHASE,
        RECOVERY_REQUEST,
        source,
        from_stage="auto",
        lifecycle="work-reviewed",
        finalization_policy="publish",
    )
    assert resumed["outcome"] == "completed"
    assert resumed["resume"]["roster_compatibility"] == ROSTER_COMPATIBILITY_INHERITED
    assert resumed["effective_stage_routes"]["produce"]["source"] == "inherited"
    assert resumed["effective_stage_routes"]["work_review"]["source"] == "current"
    assert digest_tree(source) == before_tree


# Scenario 9: Same-attempt snapshot invariance
def test_same_attempt_single_snapshot_invariance(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster")
    roster_root = roster_fixture.root
    routes_v1 = default_routes()
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v1, generation=41)

    source = make_failed_source(roster_root, repository, tmp_path / "source", fail_at=2)

    disk_mutated = [False]
    class MutatingRunner(Runner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            if not disk_mutated[0]:
                routes_mutated = default_routes()
                routes_mutated[(REQUEST.phase_type, REQUEST.execution_mode)]["final_review"] = "fixture-claude-primary"
                write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_mutated, generation=99)
                disk_mutated[0] = True
            return super().__call__(argv, prompt, cwd, max_output, on_output)

    runner = MutatingRunner()
    resumed = make_dispatcher(
        repository, tmp_path / "resumed", runner, root=roster_root
    ).resume(PHASE, REQUEST, source, from_stage="work", finalization_policy="checkpoint")

    # In this attempt, generation was 41 and final_review was NOT changed to generation 99
    assert resumed["effective_stage_routes"]["final_review"]["roster"]["generation"] == 41

    # In a subsequent attempt, the new generation 99 is observed
    from agent_phase.routing import load_validated_roster
    snapshot = load_validated_roster(roster_root)
    assert snapshot.generation == 99


# Scenario 10: Transition evidence is deterministic, bounded, and agreement across artifacts
def test_route_transition_bounded_and_consistent_across_all_artifacts(
    repository: Path, tmp_path: Path
) -> None:
    roster_fixture = build_synthetic_roster(tmp_path / "roster")
    roster_root = roster_fixture.root
    routes_v1 = default_routes()
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v1, generation=41)

    source = make_failed_source(roster_root, repository, tmp_path / "source", fail_at=2)

    routes_v2 = default_routes()
    routes_v2[(REQUEST.phase_type, REQUEST.execution_mode)]["work"] = "fixture-claude-primary"
    write_roster_sources(roster_root, SYNTHETIC_ENDPOINTS, routes_v2, generation=42)

    runner = Runner()
    resumed = make_dispatcher(
        repository, tmp_path / "resumed", runner, root=roster_root
    ).resume(PHASE, REQUEST, source, from_stage="work", finalization_policy="checkpoint")

    run_dir = Path(resumed["run_directory"])
    resolved_json = json.loads((run_dir / "resolved.json").read_text())
    state_json = json.loads((run_dir / "state.json").read_text())
    resume_json = json.loads((run_dir / "resume.json").read_text())
    result_json = json.loads((run_dir / "result.json").read_text())

    # All files must have identical effective_stage_routes and route_transition
    assert resolved_json["effective_stage_routes"] == state_json["effective_stage_routes"]
    assert state_json["effective_stage_routes"] == resume_json["effective_stage_routes"]
    assert resume_json["effective_stage_routes"] == result_json["effective_stage_routes"]

    assert resolved_json["route_transition"] == state_json["route_transition"]
    assert state_json["route_transition"] == resume_json["route_transition"]
    assert resume_json["route_transition"] == result_json["route_transition"]

    transition_str = json.dumps(resolved_json["route_transition"])
    user_path_marker = "/" + "Users" + "/"
    assert user_path_marker.split("/") == ["", "Users", ""]
    assert user_path_marker in str(Path("/") / "Users" / "fixture")
    for forbidden in ("password", "secret", "bearer", "api_key", user_path_marker, "/private/"):
        assert forbidden not in transition_str

    diffs = resolved_json["route_transition"]["route_differences"]["work"]["differences"]
    for field_name in diffs:
        assert field_name in BOUNDED_ROUTE_FIELDS
