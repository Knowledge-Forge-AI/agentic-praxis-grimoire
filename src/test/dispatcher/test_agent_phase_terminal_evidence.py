"""Terminal lifecycle evidence regressions for stage metadata attribution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_phase.dispatch import DispatchError

from test_agent_phase_dispatch import FakeRunner
from test_agent_phase_disposition_flow import DispositionFakeRunner, PHASE_ID, REQUEST, make_dispatcher, repository as _repository

repository = _repository


def _only_run(run_root: Path) -> Path:
    runs = list(run_root.rglob("state.json"))
    assert len(runs) == 1
    return runs[0].parent


def test_preexisting_metadata_is_unattributed_to_the_first_stage(
    repository: Path, tmp_path: Path
) -> None:
    metadata = repository / ".serena" / "preexisting.json"
    metadata.parent.mkdir()
    metadata.write_text("created before dispatch\n", encoding="utf-8")

    state = make_dispatcher(
        repository, tmp_path, FakeRunner()
    ).dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")

    plan_deltas = state["stage_delta_ledger"]["stages"]["plan"]["deltas"]
    assert not any(
        delta["path"] == ".serena/preexisting.json" for delta in plan_deltas
    )


def test_resumed_stage_uses_current_metadata_baseline(
    repository: Path, tmp_path: Path
) -> None:
    metadata = repository / ".serena" / "resume.json"

    source_root = tmp_path / "source"
    with pytest.raises(DispatchError):
        make_dispatcher(
            repository,
            source_root,
            FakeRunner(exit_codes={2: 1}),
        ).dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    source = _only_run(source_root / "runs")

    # This file appears after the failed attempt closes and is therefore
    # pre-existing at the resumed attempt's entry boundary.
    metadata.parent.mkdir()
    metadata.write_text("created between attempts\n", encoding="utf-8")

    def mutate_resumed_stage(_cwd: Path, _prompt: bytes) -> None:
        metadata.write_text("modified by resumed provider\n", encoding="utf-8")

    resumed = make_dispatcher(
        repository,
        tmp_path / "resumed",
        DispositionFakeRunner(hooks={0: mutate_resumed_stage}),
    ).resume(
        PHASE_ID,
        REQUEST,
        source,
        finalization_policy="checkpoint",
    )

    work_deltas = resumed["stage_delta_ledger"]["stages"]["work"]["deltas"]
    metadata_deltas = [
        delta for delta in work_deltas if delta["path"] == ".serena/resume.json"
    ]
    assert [delta["status"] for delta in metadata_deltas] == ["modified"]
    assert not any(
        ".serena/resume.json" in observation.get("paths", [])
        for observation in resumed.get("interstage_observations", [])
    )

    result = json.loads(
        Path(resumed["run_directory"], "result.json").read_text(encoding="utf-8")
    )
    assert resumed["resumed"] is True
    assert result["stage_delta_ledger"]["stages"]["work"][
        "classification_status_counts"
    ]["operational_metadata"]["modified"] == 1
