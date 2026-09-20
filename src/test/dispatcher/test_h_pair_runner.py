"""Paired runner mechanism qualification; synthetic tasks and non-model actors."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import os

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from testing.h_eval.paired import run_pair, read_pair, import_oracle
from agent_phase.provider import LivenessPolicy
from test_agent_phase_acquisition import binary


def imported(data, route):
    value = json.loads(data)
    assert value.pop("schema") == "apg.instrumented-provider/v1"
    assert value.pop("model") == route["model"]
    return value


def oracle(subject, result, scenario):
    raw = (subject / "source.txt").read_bytes()
    return {"schema": "apg.h-task-oracle/v1", "oracle": scenario["expected_outcome"]["quality_oracle"],
            "status": "pass" if raw == b"unchanged\n" else "fail",
            "evidence": [{"kind": "instrumented-subject", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}]}


class Projection:
    def qualification(self):
        return {"selective_projection": True, "independent_recovery": True, "evidence": "instrumented mechanism only"}
    def project(self, plan, argv, prompt):
        return argv, plan["payload"].encode()


def planner(request, capture):
    return {"effective_mode": "adaptive", "reasons": [], "payload": request["mandatory"][0]["text"]}


def inputs(tmp_path, operation="success"):
    executable = tmp_path / "instrumented"
    executable.write_text("#!" + sys.executable + "\n" + (ROOT / "testing/h_eval/instrumented_provider.py").read_text().split("\n", 1)[1])
    executable.chmod(0o700)
    route = {"provider": "codex", "profile": "fixture", "model": "instrumented-model",
             "binding_id": "review", "roles": ["Work Review"], "execution": "instrumented"}
    scenario = {"scenario_id": "mechanism-only", "task_input": {"task_authority": "read_only"},
                "expected_outcome": {"quality_oracle": {"assertions": "instrumented subject unchanged"}}}
    return dict(pair_dir=tmp_path / "pair", source_root=ROOT, scenario=scenario,
                routes={"static": dict(route), "adaptive": dict(route)},
                subject_files={"source.txt": b"unchanged\n"}, prompt=json.dumps({"operation": operation}).encode(),
                executable_paths={"codex_executable": str(executable)}, oracle=oracle,
                result_importer=imported, projection=Projection(), planner=planner,
                liveness_policy=LivenessPolicy(outer_ceiling_seconds=2, advisory_silence_seconds=None))


def test_pair_uses_real_launch_seam_isolation_and_archive_resume(tmp_path):
    config = inputs(tmp_path)
    value = run_pair(**config)
    assert value["evidence_kind"] == "runner_qualification" and value["h_gate_established"] is False
    assert value["arms"]["static"]["route"] == value["arms"]["adaptive"]["route"]
    for mode in ("static", "adaptive"):
        arm = value["arms"][mode]
        assert arm["effective_mode"] == mode and arm["model_observed"] is None
        assert arm["authority"]["unchanged"] and arm["task_oracle"]["status"] == "pass"
        assert len(arm["deliveries"]) == 2  # exact task stdin + source doctrine argv
    static = config["pair_dir"] / "static/subject/source.txt"
    adaptive = config["pair_dir"] / "adaptive/subject/source.txt"
    assert static.stat().st_ino != adaptive.stat().st_ino
    assert read_pair(config["pair_dir"]) == value
    archive = shutil.make_archive(str(tmp_path / "transport"), "zip", config["pair_dir"])
    restored = tmp_path / "restored"
    shutil.unpack_archive(archive, restored)
    assert read_pair(restored) == value
    with pytest.raises(FileExistsError):
        run_pair(**config)
    (restored / "static/run/attempt.context-deliveries.json").unlink()
    with pytest.raises(ValueError, match="changed or lost"):
        read_pair(restored)


def test_route_mismatch_rejected_before_launch(tmp_path):
    config = inputs(tmp_path)
    config["routes"]["adaptive"]["model"] = "other"
    with pytest.raises(ValueError, match="route"):
        run_pair(**config)
    assert not config["pair_dir"].exists()


@pytest.mark.parametrize("operation", ["timeout", "nonzero", "malformed", "side-effect"])
def test_provider_failure_preserved_without_replay(tmp_path, operation):
    config = inputs(tmp_path, operation)
    with pytest.raises(ValueError, match="never blindly replay"):
        run_pair(**config)
    result = json.loads((config["pair_dir"] / "static/run/terminal.json").read_bytes())
    assert result["status"] == "incomplete" and result["retries"] == 0
    assert not (config["pair_dir"] / "adaptive").exists()
    with pytest.raises(FileExistsError):
        run_pair(**config)
    if operation == "side-effect":
        assert result["authority"]["unchanged"] is False
        assert (config["pair_dir"] / "static/subject/side-effect.txt").read_text() == "one invocation\n"


def test_missing_observation_fails_closed(tmp_path, monkeypatch):
    from agent_phase.transmission import Transport
    monkeypatch.setattr(Transport, "wrote_stdin", lambda *a: None)
    config = inputs(tmp_path)
    with pytest.raises(ValueError, match="pair incomplete"):
        run_pair(**config)
    assert not (config["pair_dir"] / "pair.json").exists()


def test_exact_task_oracle_shape_and_authority(tmp_path):
    config = inputs(tmp_path)
    config["oracle"] = lambda *a: {"status": "pass"}
    with pytest.raises(ValueError, match="pair incomplete"):
        run_pair(**config)
    with pytest.raises(ValueError, match="oracle"):
        import_oracle({"schema": "apg.h-task-oracle/v1", "oracle": {}, "status": "pass", "evidence": []}, {})


@pytest.mark.parametrize("operation", ["acquire", "recover"])
def test_pair_real_acquisition_and_witnessed_recovery(binary, tmp_path, monkeypatch, operation):
    from agent_phase.acquisition_launch import AcquisitionLaunch
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(str(ROOT / p) for p in ("libexec", "src")))
    config = inputs(tmp_path, operation)
    projection = Projection()
    projection.acquisition = AcquisitionLaunch(binary=binary, catalog={"schema_version": "apg.skill-catalog/v1"},
        candidates=["apgr:go-test-profile"], seam="codex-native", native_read_authorized=True)
    config["projection"] = projection
    config["liveness_policy"] = LivenessPolicy(outer_ceiling_seconds=10, advisory_silence_seconds=None)
    result = run_pair(**config)
    arm = result["arms"]["adaptive"]
    assert arm["late_acquisitions"]
    if operation == "recover":
        assert len(arm["exact_recovery"]) == 1
    else:
        assert any(d["channel"] == "mcp" for d in arm["late_acquisitions"])
    assert read_pair(config["pair_dir"]) == result


def test_readiness_inventory_recomputes_and_rejects_changed_owner():
    from testing.h_eval.readiness import make_seal, verify_seal
    seal = make_seal(ROOT)
    verify_seal(ROOT, seal)
    assert len([p for p in seal["files"] if p.startswith("testing/fixtures/context-eval/scenario-")]) == 15
    assert seal["h_gate_established"] is False
    seal["files"]["libexec/agent_phase/transmission.py"] = "0" * 64
    with pytest.raises(ValueError, match="readiness inputs changed"):
        verify_seal(ROOT, seal)


def test_oracle_cannot_hide_readonly_mutation(tmp_path):
    config = inputs(tmp_path)
    def mutate(subject, returned, scenario):
        value = oracle(subject, returned, scenario)
        (subject / "source.txt").write_text("unauthorized oracle mutation")
        return value
    config["oracle"] = mutate
    with pytest.raises(ValueError, match="pair incomplete"):
        run_pair(**config)


def test_explicit_static_context_is_measured_without_claiming_benefit(tmp_path):
    config = inputs(tmp_path)
    config["static_context"] = b"\nInstrumented static skill context.\n"
    value = run_pair(**config)
    assert value["arms"]["static"]["initial"] - value["arms"]["adaptive"]["initial"] == len(config["static_context"])
    assert value["evidence_kind"] == "runner_qualification"
    assert value["h_gate_established"] is False


def test_provider_cannot_redirect_output_retention_through_symlink(tmp_path):
    config = inputs(tmp_path, "evidence-symlink")
    with pytest.raises(ValueError, match="pair incomplete"):
        run_pair(**config)
    assert (config["pair_dir"] / "static/subject/source.txt").read_bytes() == b"unchanged\n"


def test_binary_and_large_subjects_survive_pair_archive(tmp_path):
    config = inputs(tmp_path)
    config["subject_files"]["schema/db.sqlite"] = b"SQLite format 3\x00\xff\xfe"
    config["subject_files"]["build/output.bin"] = b"\xff" * ((16 << 20) + 1)
    value = run_pair(**config)
    assert read_pair(config["pair_dir"]) == value
    assert all(arm["authority"]["unchanged"] for arm in value["arms"].values())


def test_prelaunch_snapshot_failure_retains_terminal_fence(tmp_path, monkeypatch):
    from testing.h_eval import paired
    config = inputs(tmp_path)
    def fail(root):
        raise ValueError("snapshot unavailable")
    monkeypatch.setattr(paired, "_snapshot", fail)
    with pytest.raises(ValueError, match="snapshot unavailable"):
        run_pair(**config)
    terminal = json.loads((config["pair_dir"] / "terminal.json").read_bytes())
    assert terminal["status"] == "incomplete"
    assert terminal["replay_authorized"] is False
    assert not (config["pair_dir"] / "static/run/started.json").exists()
    with pytest.raises(FileExistsError):
        run_pair(**config)


def test_live_recovery_cannot_claim_complete_native_read_coverage():
    from testing.h_eval.paired import require_recovery_coverage
    prepared = {"record": {"acquisition": {"recovery": [{"path": "recovery.json"}]}}}
    with pytest.raises(ValueError, match="native recovery"):
        require_recovery_coverage("live", prepared)
    require_recovery_coverage("instrumented", prepared)
    require_recovery_coverage("live", {"record": {}})


def test_interrupt_preserves_interrupt_and_terminal_evidence(tmp_path, monkeypatch):
    from testing.h_eval import paired
    config = inputs(tmp_path)
    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt()
    monkeypatch.setattr(paired.context_adapter, "invoke", interrupt)
    with pytest.raises(KeyboardInterrupt):
        run_pair(**config)
    terminal = json.loads((config["pair_dir"] / "static/run/terminal.json").read_bytes())
    assert terminal["failure"] == "KeyboardInterrupt" and terminal["replay_authorized"] is False


def test_live_requires_real_catalog_capture_before_admission(tmp_path):
    config = inputs(tmp_path)
    for route in config["routes"].values():
        route["execution"] = "live"
    with pytest.raises(ValueError, match="catalog capture"):
        run_pair(**config)
    assert not config["pair_dir"].exists()


def test_runtime_settings_manifest_rejects_drift_and_unbound_handoff(tmp_path):
    from testing.h_eval.paired import verify_runtime_inputs
    settings = tmp_path / "settings.json"
    settings.write_bytes(b"{}\n")
    identity = {"bytes": 3, "sha256": hashlib.sha256(b"{}\n").hexdigest()}
    manifest = {str(settings): identity}
    event = {"provenance": "provider-settings-reference", "reference": str(settings),
             "controlled_bytes": 3, "payload_sha256": identity["sha256"]}
    verify_runtime_inputs(manifest, [event])
    with pytest.raises(ValueError, match="not bound"):
        verify_runtime_inputs({}, [event])
    settings.write_bytes(b"{ }\n")
    with pytest.raises(ValueError, match="changed"):
        verify_runtime_inputs(manifest)


def test_pair_preserves_caller_catalog_capture(tmp_path):
    config = inputs(tmp_path)
    capture = {"settings": {"max_initial_context_bytes": 100000}, "provenance": [],
               "overrides": [{"fixture": "capture-only"}], "apgr_home": str(tmp_path / "catalog")}
    seen = []
    def capturing_planner(request, supplied):
        seen.append(supplied)
        return planner(request, supplied)
    config.update(capture=capture, planner=capturing_planner)
    run_pair(**config)
    assert seen[0]["overrides"] == capture["overrides"]
    assert seen[0]["apgr_home"] == capture["apgr_home"]
    assert "mode" not in capture["settings"]
