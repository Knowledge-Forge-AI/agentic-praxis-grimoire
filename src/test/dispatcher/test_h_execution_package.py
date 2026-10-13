"""Focused APG166D F9 execution-package evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from testing.h_eval import assembly, dry_run, execution, importers
from testing.h_eval.evaluate import load
from h_regression_fixtures import current_source


ROOT = Path(__file__).resolve().parents[3]


def test_unqualified_live_owner_cannot_invoke_even_with_ready_claim(tmp_path, current_source):
    scenario, route = _scenario_and_route(current_source)
    route = {**route, "execution": "live"}
    with pytest.raises(ValueError, match="admission unavailable"):
        execution.run_one_arm(
            arm_dir=tmp_path / "arm", source_root=current_source, scenario=scenario,
            mode="static", route=route, seal={"prerequisites_ready": True},
            live_authorization={"authorized": True},
            runner=lambda *a, **k: pytest.fail("live provider invoked"),
        )
    assert not (tmp_path / "arm").exists()


def test_aggregate_rejects_empty_cohort_and_in_memory_receipts(tmp_path):
    with pytest.raises(ValueError, match="incomplete"):
        assembly.aggregate_complete(ROOT, {"rows": []})
    with pytest.raises(ValueError, match="integrity"):
        assembly._load_result({"status": "complete"})
    with pytest.raises(ValueError, match="unavailable"):
        assembly.write_aggregate(tmp_path / "aggregate.json", {"h_gate_established": True})
    assert not (tmp_path / "aggregate.json").exists()


def _scenario_and_route(root, number: int = 1):
    scenario_path = next((root / "testing/fixtures/context-eval").glob(f"scenario-{number:02d}-*.json"))
    scenario = load(scenario_path)
    bindings = load(root / "testing/h_eval/scenario-bindings.json")
    row = next(item for item in bindings["scenarios"] if item["scenario_id"] == scenario["scenario_id"])
    return scenario, row["routes"]["static"]


def _provider(tmp_path: Path) -> tuple[Path, Path]:
    counter = tmp_path / "provider-count"
    script = tmp_path / "provider"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "from pathlib import Path\n"
        "import sys\n"
        f"counter = Path({str(counter)!r})\n"
        "counter.write_text(str(int(counter.read_text() or '0') + 1) if counter.exists() else '1')\n"
        "sys.stdin.buffer.read()\n"
        "print(json.dumps({'schema': 'apg.instrumented-provider/v1', 'result': 'done', "
        "'producer_revisions': [], 'missing_guidance_findings': [], "
        "'restart_required_incidents': [], 'model_observed': None}))\n"
    )
    script.chmod(0o700)
    return script, counter


def _oracle(scenario):
    return {
        "schema": "apg.h-task-oracle/v1",
        "oracle": scenario["expected_outcome"]["quality_oracle"],
        "status": "pass",
        "evidence": [{"kind": "fixture", "sha256": "0" * 64, "bytes": 0}],
    }


def test_provider_importers_retain_raw_identity_without_semantic_claims():
    route = {
        "provider": "claude",
        "profile": "normal-final-review",
        "model": "claude-opus-5",
        "binding_id": "binding-reviewer-01",
        "roles": ["Work Review"],
        "execution": "instrumented",
    }
    raw = b'{"type":"result","session_id":"s-1","model":"observed-model","result":"done"}\n'
    imported = importers.import_claude(raw, route, terminal={"exit_code": 0})
    assert imported["raw"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert imported["result"]["kind"] == "text"
    assert imported["session"] == {"session_id": "s-1"}
    assert imported["model_observed"] is None
    assert imported["producer_revisions"] is None
    assert imported["terminal"]["exit_code"] == 0


def test_provider_importers_do_not_promote_task_json_to_runtime_identity():
    route = {
        "provider": "claude",
        "profile": "normal-final-review",
        "model": "claude-opus-5",
        "binding_id": "binding-reviewer-01",
        "roles": ["Work Review"],
        "execution": "instrumented",
    }
    imported = importers.import_claude(
        b'{"model":"answer text","session_id":"answer-id","result":"answer"}\n',
        route,
    )
    assert imported["parse_status"] == "malformed"
    assert imported["observed_model"] is None
    assert imported["session"] is None


@pytest.mark.parametrize("answer", [
    {"answer": "legitimate JSON"},
    {"type": "result", "schema": "apg.instrumented-provider/v1", "model": "spoof",
     "session_id": "spoof", "status": "spoof", "producer_revisions": [],
     "missing_guidance_findings": [], "restart_required_incidents": [], "model_observed": True},
])
def test_claude_stream_keeps_json_answers_opaque(answer):
    route = {"provider": "claude", "execution": "live"}
    answer_text = json.dumps(answer)
    raw = (json.dumps({"type": "system", "subtype": "init", "model": "actual", "session_id": "actual"}) + "\n"
           + json.dumps({"type": "result", "subtype": "success", "session_id": "actual", "result": answer_text}) + "\n").encode()
    imported = importers.import_claude(raw, route, terminal={"exit_code": 0})
    assert imported["parse_status"] == "structured"
    assert imported["observed_model"] == "actual"
    assert imported["session"] == {"session_id": "actual"}
    assert imported["provider_terminal_status"] == "success"
    assert imported["producer_revisions"] is imported["model_observed"] is None
    assert imported["result"]["sha256"] == hashlib.sha256(answer_text.encode()).hexdigest()
    assert imported["raw"]["sha256"] == hashlib.sha256(raw).hexdigest()


def test_live_import_refuses_instrumented_envelope():
    value = importers.import_claude(
        b'{"schema":"apg.instrumented-provider/v1","result":"fake","model_observed":true}',
        {"provider": "claude", "execution": "live"},
    )
    assert value["parse_status"] == "malformed"
    assert value["model_observed"] is value["session"] is None


def test_one_arm_is_single_use_and_readback_is_provider_free(tmp_path, current_source):
    scenario, route = _scenario_and_route(current_source)
    executable, counter = _provider(tmp_path)
    result = execution.run_one_arm(
        arm_dir=tmp_path / "arm",
        source_root=current_source,
        scenario=scenario,
        mode="static",
        route=route,
        subject_files={"main.go": b"package main\n"},
        oracle=lambda subject, returned, value: _oracle(value),
        executable_paths={"codex_executable": str(executable)},
    )
    assert result["status"] == "complete"
    assert result["provider_invocations"] == 1
    assert result["coverage"] == "complete"
    assert counter.read_text() == "1"
    retained = execution.read_arm_result(tmp_path / "arm")
    assert retained["status"] == "complete"
    assert counter.read_text() == "1"
    with pytest.raises(ValueError, match="admission"):
        execution.run_one_arm(
            arm_dir=tmp_path / "arm",
            source_root=current_source,
            scenario=scenario,
            mode="static",
            route=route,
            subject_files={"main.go": b"package main\n"},
            oracle=lambda subject, returned, value: _oracle(value),
            executable_paths={"codex_executable": str(executable)},
        )
    assert counter.read_text() == "1"


def test_assembly_preserves_all_incomplete_arms_and_rejects_aggregate(tmp_path, current_source):
    raw = assembly.assemble_raw(current_source)
    assert len(raw["rows"]) == 15
    assert all(set(row["arms"]) == {"static", "adaptive"} for row in raw["rows"])
    with pytest.raises(ValueError, match="incomplete"):
        assembly.aggregate_complete(current_source, raw)


def test_provider_free_dry_run_builds_two_arms_for_all_frozen_scenarios(tmp_path, monkeypatch, current_source):
    monkeypatch.setattr(dry_run, "_scenario_special", lambda root, scenario, route, destination:
                        {"selective_projection": {"status": "incomplete"}} if scenario["scenario_id"] == "scenario-15" else {})
    class Subjects:
        def materialize_subject(self, scenario, destination, mode):
            files = {}
            for name in scenario.get("repository_evidence", {}).get("files", []):
                files[name] = f"{scenario['scenario_id']}:{mode}:{name}\n"
            project = (scenario.get("catalog_sources") or {}).get("project")
            if project:
                files[project["canonical_path"]] = project["synthetic_body"]
            config = (scenario.get("repository_evidence", {}).get("configuration_facts") or {}).get("project_config")
            if config is not None:
                files[".apgr/config.toml"] = config
            return {"files": files or {"README.md": f"{scenario['scenario_id']}:{mode}\n"}}

    class Oracles:
        def oracle_for(self, scenario):
            return object()

        def exercise_oracle(self, root, scenario, oracle):
            return {"good": True, "bad": True}

    result = dry_run.dry_run_all(
        current_source,
        tmp_path / "dry",
        subject_factory=Subjects(),
        oracle_owner=Oracles(),
    )
    assert result["scenario_count"] == 15
    # The dry-run must retain all records while refusing a false complete claim
    # when no operator-owned v2 runtime manifest has been supplied.
    assert result["complete_records"] == 0
    assert result["provider_invocations"] == 0
    assert result["all_subjects_complete"] is True
    assert result["aggregate_written"] is False
    for row in result["records"]:
        assert row["provider_invocations"] == 0
        assert set(row["subjects"]) == {"static", "adaptive"}
        assert set(row["context_plans"]).issubset({"static", "adaptive"})
        assert row["runtime"]["status"] == "unavailable"
        assert row["initial_trees_equal"] is False
        assert "static/adaptive initial subjects differ or are unavailable" in row["blockers"]
        assert all(item["unchanged"] for item in row["subject_authority"].values())
    assert "selective_projection plumbing incomplete" in result["records"][-1]["blockers"]


def test_current_source_route_drift_is_still_rejected(current_source):
    from testing.h_eval.preregistration import verify_bindings
    verify_bindings(current_source)
    path = current_source / "common/dispatcher/routes.toml"
    path.write_bytes(path.read_bytes() + b"\n# drift\n")
    with pytest.raises(ValueError, match="route source changed"):
        verify_bindings(current_source)
