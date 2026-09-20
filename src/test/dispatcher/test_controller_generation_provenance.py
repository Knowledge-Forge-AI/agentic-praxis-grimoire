"""Generation attribution survives real run/archive/resume/adoption boundaries."""
import json
import subprocess
from pathlib import Path

import controller_generation as generation
from agent_phase import finalization_recovery
from test_agent_phase_adoption import sealed, receipt, continue_phase, repository as _repository
from test_agent_phase_disposition_flow import make_dispatcher, PHASE_ID, REQUEST
from test_agent_phase_path_dispositions import OwnershipRunner

repository = _repository


def observation(label):
    return {"schema": "controller-generation-v1", "commit": label * 40,
            "tree": label * 40, "safety_established": False,
            "reason": "source_development_worktree", "generation_root": None}


def test_resume_and_recovery_preserve_source_generation(repository, tmp_path, monkeypatch):
    first, second = observation("a"), observation("b")
    monkeypatch.setattr(generation, "_development", first)
    source = sealed(repository, tmp_path)
    original = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    before = json.loads((source / "state.json").read_text())["controller_generation"]
    monkeypatch.setattr(generation, "_development", second)
    runner = OwnershipRunner()
    resumed = make_dispatcher(repository, tmp_path / "resumed", runner).resume(
        PHASE_ID, REQUEST, source, "finalize", finalization_policy="checkpoint")
    assert resumed["source_controller_generation"] == before
    assert resumed["controller_generation"]["commit"] == second["commit"]
    assert runner.calls == []
    recovered = finalization_recovery.recover(source, repository, dry_run=True)
    assert recovered["source_controller_generation"] == before
    assert recovered["controller_generation"]["commit"] == second["commit"]
    assert recovered["provider_invocations"] == 0
    assert original == {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}


def test_continue_adopts_source_generation_without_relabelling_it(repository, tmp_path, monkeypatch):
    monkeypatch.setattr(generation, "_development", observation("a"))
    source = sealed(repository, tmp_path)
    before = json.loads((source / "state.json").read_text())["controller_generation"]
    monkeypatch.setattr(generation, "_development", observation("b"))
    path, record = receipt(repository, tmp_path, source)
    assert record["source_controller_generation"] == before
    state = continue_phase(repository, tmp_path, path, policy="checkpoint")
    assert state["adoption"]["source_controller_generation"] == before
    assert state["controller_generation"]["commit"] == "b" * 40
    result = json.loads((Path(state["run_directory"]) / "result.json").read_text())
    assert result["controller_generation"] == state["controller_generation"]


def test_actual_ownership_command_activates_pinned_generation(repository, tmp_path, monkeypatch):
    from test_controller_generation_real_cli import candidate
    from test_agent_phase_ownership_receipt_boundaries import source_with_challenges
    monkeypatch.setattr(generation, "_development", observation("a"))
    source, state = source_with_challenges(repository, tmp_path)
    controller = tmp_path / "controller"
    candidate(controller)
    monkeypatch.setenv("AGENT_CENTRAL_GENERATION_STORE", str(tmp_path / "store"))
    monkeypatch.setenv("AGENT_CENTRAL_ACTIVE_ROOT", str(controller))
    monkeypatch.delenv(generation.LEASE_ENV, raising=False)
    output = tmp_path / "manager-resolution.json"
    process = subprocess.run([
        str(controller / "bin/agent-phase-ownership"), "resolve", "--run", str(source),
        "--challenge", state["ownership_challenges"]["records"][0]["challenge_id"],
        "--decision", "phase_owned", "--reason", "exact generation fixture",
        "--output", str(output),
    ], cwd=repository, capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stderr
    record = json.loads(output.read_text())
    assert record["source_controller_generation"] == state["controller_generation"]
    assert record["controller_generation"]["safety_established"] is True
    expected = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=controller, text=True).strip()
    assert record["controller_generation"]["commit"] == expected
    assert record["manager_authority"]["controller_generation"] == record["controller_generation"]
    assert record["provider_invocations"] == record["product_test_invocations"] == 0
