from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_phase import result_repair as result_repair_module
from agent_phase import resume_dispatch as resume_dispatch_module
from agent_phase.dispatch import DispatchError
from test_agent_phase_result_repair import (
    PHASE as REPAIR_PHASE,
    REQUEST as REPAIR_REQUEST,
    RepairRunner,
    _repack_source_zip,
    make_source,
    repair,
)
from test_agent_phase_resume import PHASE, REQUEST, Runner, dispatcher, duplicate_source, failed_source, repository as _repository

repository = _repository


def _rewrite_resolved(source: Path, transform) -> None:
    path = source / "resolved.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    transform(value)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _rewrite_repair_resolved(source: Path, transform) -> None:
    _rewrite_resolved(source, transform)
    _repack_source_zip(source)


def test_resume_uses_one_roster_snapshot_for_resolution_and_execution(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = failed_source(repository, tmp_path, 2)
    loaded = []
    resolved_with = []
    routed_with = []
    routed = []
    real_load = resume_dispatch_module.load_validated_roster
    real_resolve = resume_dispatch_module.resolve
    real_route = resume_dispatch_module.route

    def counted_load(root: Path):
        snapshot = real_load(root)
        loaded.append(snapshot)
        return snapshot

    def recorded_resolve(*args, roster=None, **kwargs):
        resolved_with.append(roster)
        return real_resolve(*args, roster=roster, **kwargs)

    def recorded_route(*args, roster=None, **kwargs):
        routed_with.append(roster)
        endpoints = real_route(*args, roster=roster, **kwargs)
        routed.append(endpoints)
        return endpoints

    monkeypatch.setattr(resume_dispatch_module, "load_validated_roster", counted_load)
    monkeypatch.setattr(resume_dispatch_module, "resolve", recorded_resolve)
    monkeypatch.setattr(resume_dispatch_module, "route", recorded_route)

    state = dispatcher(repository, tmp_path / "resumed", Runner()).resume(
        PHASE, REQUEST, source, "work", dry_run=True
    )
    resolved = json.loads(
        Path(state["run_directory"]).joinpath("resolved.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(loaded) == 1
    assert resolved_with == loaded
    assert routed_with == loaded
    assert routed[0]["work"].provider == resolved["stages"]["work"]["provider"]
    assert routed[0]["work"].profile == resolved["stages"]["work"]["profile"]


def test_v5_finalization_only_resume_loads_no_current_roster(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = duplicate_source(repository, tmp_path, monkeypatch)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("finalization-only V5 resume loaded a current roster")

    monkeypatch.setattr(resume_dispatch_module, "load_validated_roster", forbidden)
    state = dispatcher(repository, tmp_path / "resumed", Runner()).resume(
        PHASE, REQUEST, source, "finalize", dry_run=True
    )

    assert state["provider_invocations_performed"] == 0
    assert state["resume"]["roster_compatibility"] == "finalization_only_no_current_roster"


def test_unknown_schema_finalization_only_resume_fails_before_roster_load(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = duplicate_source(repository, tmp_path, monkeypatch)
    _rewrite_resolved(
        source,
        lambda value: value.__setitem__("schema", "agent-phase-resolved-v99"),
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unsupported schema reached current roster loading")

    monkeypatch.setattr(resume_dispatch_module, "load_validated_roster", forbidden)
    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path / "resumed", Runner()).resume(
            PHASE, REQUEST, source, "finalize", dry_run=True
        )

    assert caught.value.code == "RESUME_RESOLVED_SCHEMA_UNSUPPORTED"


def test_result_repair_uses_one_roster_snapshot_for_resolution_and_endpoint(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = make_source(repository, tmp_path)
    loaded = []
    resolved_with = []
    routed_with = []
    real_load = result_repair_module.load_validated_roster
    real_resolve = result_repair_module.resolve
    real_route = result_repair_module.route

    def counted_load(root: Path):
        snapshot = real_load(root)
        loaded.append(snapshot)
        return snapshot

    def recorded_resolve(*args, roster=None, **kwargs):
        resolved_with.append(roster)
        return real_resolve(*args, roster=roster, **kwargs)

    def recorded_route(*args, roster=None, **kwargs):
        routed_with.append(roster)
        return real_route(*args, roster=roster, **kwargs)

    monkeypatch.setattr(result_repair_module, "load_validated_roster", counted_load)
    monkeypatch.setattr(result_repair_module, "resolve", recorded_resolve)
    monkeypatch.setattr(result_repair_module, "route", recorded_route)

    state = repair(repository, tmp_path, source, RepairRunner(), dry_run=True)

    assert state["phase_id"] == REPAIR_PHASE
    assert state["phase_type"] == REPAIR_REQUEST.phase_type
    assert len(loaded) == 1
    assert resolved_with == loaded
    assert routed_with == loaded


def test_result_repair_v5_accepts_roster_generation_advance_and_routes_auxiliary_from_current(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    _rewrite_repair_resolved(
        source,
        lambda value: value["roster"].__setitem__(
            "generation", value["roster"]["generation"] + 1
        ),
    )
    runner = RepairRunner()

    state = repair(repository, tmp_path, source, runner, dry_run=True)

    assert state["outcome"] == "dry_run"
    assert state["resume"]["roster_compatibility"] == "inherited_prefix_current_suffix"
    assert state["route_transition"]["auxiliary_route"] is not None
    assert runner.calls == []


def test_result_repair_v4_allows_exact_terminal_stage_equality(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)

    def downgrade(value: dict[str, object]) -> None:
        value["schema"] = "agent-phase-resolved-v4"
        value.pop("roster", None)
        for stage in value["stages"].values():
            stage.pop("endpoint_alias", None)

    _rewrite_repair_resolved(source, downgrade)

    state = repair(repository, tmp_path, source, RepairRunner(), dry_run=True)

    assert state["outcome"] == "dry_run"


def test_result_repair_unknown_resolved_schema_fails_closed(
    repository: Path, tmp_path: Path
) -> None:
    source = make_source(repository, tmp_path)
    _rewrite_repair_resolved(
        source,
        lambda value: value.__setitem__("schema", "agent-phase-resolved-v99"),
    )
    runner = RepairRunner()

    with pytest.raises(DispatchError) as caught:
        repair(repository, tmp_path, source, runner, dry_run=True)

    assert caught.value.code == "RESUME_RESOLVED_SCHEMA_UNSUPPORTED"
    assert runner.calls == []
