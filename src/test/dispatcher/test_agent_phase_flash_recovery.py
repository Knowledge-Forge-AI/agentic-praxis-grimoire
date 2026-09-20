"""Flash mode retains normal route and controller custody across recovery."""
import json
from pathlib import Path

import controller_generation as generation
from agent_phase import adoption, finalization_recovery
from agent_phase.request import PhaseRequest
from test_agent_phase_disposition_flow import make_dispatcher, repository as _repository
from test_agent_phase_path_dispositions import OwnershipRunner
from test_controller_generation_provenance import observation


import pytest

repository = _repository

@pytest.mark.parametrize("mode", ["gemini_flash_sub", "gemini_flash_opus_sub"])
def test_flash_resume_adoption_and_finalization_provenance(repository, tmp_path, monkeypatch, mode):
    request = PhaseRequest("implementation_testing", mode, "Bounded Flash task")
    monkeypatch.setattr(generation, "_development", observation("a"))
    runner = OwnershipRunner(hooks={
        2: lambda cwd, prompt: (cwd / "flash.txt").write_text("candidate\n"),
    })
    state = make_dispatcher(repository, tmp_path / f"source-{mode}", runner).dispatch(
        f"FLASH-RECOVERY-{mode}", request, finalization_policy="checkpoint")
    source = Path(state["run_directory"])
    original = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    resolved = json.loads((source / "resolved.json").read_text())
    assert state["execution_mode"] == resolved["execution_mode"] == request.execution_mode
    assert resolved["effective_stage_routes"]["work"]["provider"] == "antigravity"

    monkeypatch.setattr(generation, "_development", observation("b"))
    resume_runner = OwnershipRunner()
    resumed = make_dispatcher(repository, tmp_path / f"resumed-{mode}", resume_runner).resume(
        f"FLASH-RECOVERY-{mode}", request, source, "finalize", finalization_policy="checkpoint")
    assert resumed["execution_mode"] == request.execution_mode
    assert resumed["source_controller_generation"] == state["controller_generation"]
    assert resume_runner.calls == []
    resumed_resolved = json.loads((Path(resumed["run_directory"]) / "resolved.json").read_text())
    for stage, route in resolved["effective_stage_routes"].items():
        inherited = resumed_resolved["effective_stage_routes"][stage]
        assert inherited == {**route, "source": "inherited", "route_selecting_run_id": state["run_id"]}

    recovery = finalization_recovery.recover(source, repository)
    assert recovery["source_controller_generation"] == state["controller_generation"]
    assert recovery["provider_invocations"] == 0
    recovered_state = json.loads((Path(recovery["receipt_path"]).parent / "finalization-state.json").read_text())
    assert recovered_state["execution_mode"] == request.execution_mode
    assert recovered_state["effective_stage_routes"] == state["effective_stage_routes"]
    assert recovered_state["source_controller_generation"] == state["controller_generation"]

    continuation = PhaseRequest("implementation_testing", request.execution_mode, "Continue Flash work")
    record = adoption.create(source, repository, f"FLASH-CONTINUE-{mode}", continuation,
                             reason="Accept exact Flash candidate")
    receipt = tmp_path / f"adoption-{mode}.json"
    receipt.write_bytes(adoption.encoded(record))
    continued = make_dispatcher(repository, tmp_path / f"continued-{mode}", OwnershipRunner()).dispatch(
        f"FLASH-CONTINUE-{mode}", continuation, finalization_policy="checkpoint", continue_from=receipt)
    assert continued["execution_mode"] == request.execution_mode
    assert continued["adoption"]["source_controller_generation"] == state["controller_generation"]
    assert continued["provider_invocations_inherited"] == 0
    continued_resolved = json.loads((Path(continued["run_directory"]) / "resolved.json").read_text())
    for stage, route in resolved["effective_stage_routes"].items():
        current = continued_resolved["effective_stage_routes"][stage]
        assert current == route
        assert continued["effective_stage_routes"][stage]["route_selecting_run_id"] == continued["run_id"]
    result = json.loads((Path(continued["run_directory"]) / "result.json").read_text())
    assert result["execution_mode"] == request.execution_mode
    assert result["controller_generation"] == continued["controller_generation"]
    assert original == {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
