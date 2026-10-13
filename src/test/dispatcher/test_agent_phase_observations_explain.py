"""APG166Z-CONTEXT1 context explanation: bounded, index-free, human/JSON agreement."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_phase import observations
from agent_phase import observations_explain as explain

ROOT = Path(__file__).resolve().parents[3]


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value) if not isinstance(value, str) else value)


def plan_record(prefix, *, requested="adaptive", effective="adaptive", reason="qualified_projection", supported=True,
                acquisition=True, inputs=True, planned=True):
    record = {"schema": "apg.invocation-context/v1", "run_id": "run-1", "binding_id": prefix.split("-", 1)[1],
              "attempt_id": f"att-{prefix}", "attempt_number": 1, "requested_mode": requested,
              "effective_mode": effective, "reason": reason, "planned": planned,
              "controlled_total": {"bytes": 4200, "boundary": "canonical argv JSON plus runner stdin"},
              "attempted_request": {"facts": [{"kind": "work_class", "value": "implementation_testing"}]},
              "prospective_plan": {"mandatory_cost": {"bytes": 1000, "characters": 1000},
                                   "payload_cost": {"bytes": 4000, "characters": 4000},
                                   "unknown_facts": [{"kind": "language", "value": "rust"}],
                                   "decisions": [
                                       {"requested_id": "apgr:pytest-test-profile", "selected_id": "apgr:pytest-test-profile",
                                        "status": "selected", "reason": "structured_fact:test_framework:pytest",
                                        "whole_source": {"bytes": 3000}},
                                       {"requested_id": "apgr:vagrantfile-profile", "selected_id": "apgr:vagrantfile-profile",
                                        "status": "deferred", "reason": "required_closure_exceeds_budget"},
                                       {"requested_id": "project:house", "selected_id": "project:house",
                                        "status": "unavailable", "reason": "skill not found"},
                                       {"requested_id": "apgr:bats-test-profile", "selected_id": "apgr:bats-test-profile",
                                        "status": "deferred", "reason": "applicability_unknown_no_positive_fact"}]}}
    if supported is not None:
        record["route_support"] = {"schema": "apg.context-route/v1", "seam": "claude-profile", "supported": supported,
                                   "code": None if supported else "provider_not_in_pilot", "provider": "claude",
                                   "profile": "opus-high-review", "preflight": "available" if supported else None}
    if inputs:
        record["inputs"] = {"schema": "apg.context-inputs/v1", "postures": ["work"],
                            "facts": [{"kind": "test_framework", "value": "pytest", "source": "manifest:pyproject.toml",
                                       "status": "supplied"},
                                      {"kind": "language", "value": "go", "source": "manifest:go.mod", "status": "conflicting"}],
                            "requests": [{"id": "apgr:vagrantfile-profile", "source": "project", "required": False,
                                          "stages": ["work"], "applies": True}],
                            "manifest": {"enabled": True, "files": [{"file": "pyproject.toml", "status": "read"}]}}
    if acquisition:
        record["acquisition"] = {"allowed_ids": ["apgr:vagrantfile-profile", "apgr:bats-test-profile"],
                                 "recovery": [{"id": "apgr:vagrantfile-profile", "path": "acquisitions/skills/x/SKILL.md",
                                               "bytes": 28338}], "status": "prelaunch_available"}
    return record


@pytest.fixture
def run_dir(tmp_path):
    run = tmp_path / "PHASE-dispatch--20260929T120000000000Z"
    run.mkdir()
    write(run / "state.json", {"run_id": "run-1", "run_layout": {"schema": "x"}, "project": "demo",
                               "phase_type": "implementation_testing", "execution_mode": "claude_only", "outcome": "completed"})
    write(run / "01-work.context-plan.json", plan_record("01-work"))
    write(run / "01-work.context-transport.json", {"status": "runner_returned", "exit_code": 0})
    write(run / "01-work.context-deliveries.json", {"coverage": "complete", "boundary": "runner", "events": [
        {"channel": "prompt", "controlled_bytes": 4100, "phase": "initial"},
        {"channel": "mcp_configuration", "controlled_bytes": 300, "phase": "initial"}]})
    write(run / "02-final-review.context-plan.json", plan_record(
        "02-final-review", effective="static", reason="route_unsupported:provider_not_in_pilot", supported=False,
        acquisition=False))
    return run


def test_supported_and_fallback_attempts_are_distinguished(run_dir):
    value = explain.explain_run(run_dir)
    assert value["schema"] == explain.SCHEMA and value["run"]["runtime_state"]["terminal_outcome"] == "completed"
    first, second = value["attempts"]
    assert first["delivery"] == "adaptive" and first["route"]["supported"] is True
    assert second["delivery"] == "static_with_shadow_plan"
    assert second["delivery_note"] == "planned only; selected skills NOT delivered"
    assert second["route"]["code"] == "provider_not_in_pilot" and second["hints"]
    skills = first["skills"]
    assert [s["id"] for s in skills["selected"]] == ["apgr:pytest-test-profile"]
    assert [s["id"] for s in skills["deferred"]] == ["apgr:vagrantfile-profile"]
    assert [s["id"] for s in skills["unavailable"]] == ["project:house"]
    assert skills["not_applicable_count"] == 1 and skills["acquirable_count"] == 2
    assert skills["unknown_facts"] == ["language=rust"]
    assert first["planned"]["payload"]["bytes"] == 4000 and first["runner_transport"]["bytes"] == 4200
    assert first["transmitted"]["runner"]["bytes_by_channel"] == {"prompt": 4100, "mcp_configuration": 300}
    assert first["transmitted"]["launcher"] is None and first["provider_reported_usage"] == "unavailable"
    statuses = {(f["kind"], f["value"]): f["status"] for f in first["inputs"]["facts"]}
    assert statuses[("language", "go")] == "conflicting" and ("work_class", "implementation_testing") in statuses


def test_human_output_is_rendered_from_the_json_value(run_dir):
    value = explain.explain_run(run_dir)
    text = explain.render_explanation(value)
    for attempt in value["attempts"]:
        assert attempt["prefix"] in text and attempt["reason"] in text and attempt["delivery"].upper() in text
        for group in ("selected", "deferred", "unavailable"):
            for row in attempt["skills"][group]:
                assert row["id"] in text and row["reason"] in text
        planned = attempt["planned"]
        assert f"payload {planned['payload']['bytes']} bytes" in text
    assert "NOT delivered" in text and "provider-reported usage: unavailable" in text
    assert "runner_returned is process return, not task success" in text


def test_older_partial_and_malformed_records(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    # PILOT1-shaped: no inputs, no route support, no acquisition, no terminal outcome.
    old = plan_record("01-work", effective="static", reason="selective_projection_unqualified", supported=None,
                      acquisition=False, inputs=False)
    write(run / "state.json", {"run_id": "run-1", "run_layout": {}, "outcome": None})
    write(run / "01-work.context-plan.json", old)
    write(run / "02-review.meta.json", {"stage": "review", "provider": "claude"})
    write(run / "03-work.context-plan.json", "{not json")
    write(run / "04-work.context-plan.json", {"schema": "something-else"})
    (run / "05-work.context-plan.json").mkdir()
    value = explain.explain_run(run)
    by = {a["prefix"]: a for a in value["attempts"]}
    assert by["01-work"]["inputs"]["recorded"] is False and by["01-work"]["route"] == {"recorded": False}
    assert by["01-work"]["delivery"] == "static_with_shadow_plan"
    assert by["02-review"]["delivery"] == "unknown" and by["02-review"]["transmitted"]["runner"] is None
    assert value["run"]["runtime_state"]["terminal_outcome"] is None
    assert "not a health claim" in value["run"]["runtime_state"]["note"]
    warnings = "\n".join(value["warnings"])
    assert "03-work context plan" in warnings and "unsupported schema" in warnings and "05-work" in warnings
    explain.render_explanation(value)


def test_bounded_reads_and_attempt_limit(run_dir, monkeypatch):
    value = explain.explain_run(run_dir, max_total_bytes=200)
    assert any("aggregate read budget" in w for w in value["warnings"])
    monkeypatch.setattr(explain, "MAX_ATTEMPTS", 1)
    value = explain.explain_run(run_dir)
    assert len(value["attempts"]) == 1 and any("attempt limit" in w for w in value["warnings"])


def test_filters_and_feedback_survive_index_rebuild(run_dir, tmp_path):
    home = tmp_path / "home"
    feedback = observations.storage_root(home) / "feedback.jsonl"
    observations.append_feedback(feedback, run_id="run-1", attempt_id="att-01-work", label="helpful",
                                 source="agent", skill="apgr:pytest-test-profile", note="used")
    observations.append_feedback(feedback, run_id="run-1", label="missing", source="operator")
    index = observations.storage_root(home) / "index.sqlite3"
    observations.import_runs(index, [observations.collect_run(run_dir)], rebuild=True)
    observations.import_runs(index, [observations.collect_run(run_dir)], rebuild=True)
    value = explain.explain_run(run_dir, stage="work")
    explain.attach_feedback(value, observations.read_feedback(feedback, {"run-1"}, []))
    (attempt,) = value["attempts"]
    assert attempt["feedback"][0]["label"] == "helpful" and value["run_feedback"][0]["label"] == "missing"
    assert "feedback (agent): helpful" in explain.render_explanation(value)
    assert explain.explain_run(run_dir, attempt="02")["attempts"][0]["binding_id"] == "final-review"


def run_cli(*args, env=None):
    return subprocess.run([sys.executable, str(ROOT / "libexec/agent_phase/cli.py"), "observations", "explain", *args],
                          capture_output=True, text=True, env={**os.environ, **(env or {})}, timeout=60)


def test_cli_json_and_selectors(run_dir, tmp_path):
    outbox = tmp_path / "outbox"
    leaf = outbox / "demo" / "PHASE" / run_dir.name
    leaf.parent.mkdir(parents=True)
    run_dir.rename(leaf)
    home = tmp_path / "home"
    direct = run_cli(str(leaf), "--json", "--apgr-home", str(home))
    assert direct.returncode == 0, direct.stderr
    value = json.loads(direct.stdout)
    assert value["attempts"][0]["delivery"] == "adaptive"
    selected = run_cli("--project", "demo", "--outbox-root", str(outbox), "--apgr-home", str(home))
    assert selected.returncode == 0 and "Attempt 01-work" in selected.stdout
    wrapper = subprocess.run([str(ROOT / "bin/agent-phase-observations"), "explain", str(leaf), "--no-feedback", "--json"],
                             capture_output=True, text=True, timeout=60)
    assert wrapper.returncode == 0 and json.loads(wrapper.stdout)["run"]["run_id"] == "run-1"
    assert run_cli("--apgr-home", str(home)).returncode == 2
    assert run_cli(str(leaf), "--phase", "PHASE").returncode == 2
    empty = run_cli("--v2", "--apgr-home", str(home))
    assert empty.returncode == 2 and "no run found" in empty.stderr


def test_apgr_top_level_forwards_explain(run_dir, tmp_path):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run([sys.executable, "-m", "agentic_praxis_grimoire", "--apgr-home", str(tmp_path / "home"),
                             "dispatcher", "observations", "explain", str(run_dir), "--json"],
                            capture_output=True, text=True, env=env, cwd=ROOT, timeout=60)
    if result.returncode != 0 and "No module named" in result.stderr:
        pytest.skip("top-level package entry point unavailable in this interpreter")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["schema"] == explain.SCHEMA


def test_summarize_reports_delivery_and_route_support(run_dir):
    summary = observations.summarize([observations.collect_run(run_dir)])
    assert summary["context"]["delivery"] == {"adaptive": 1, "static_with_shadow_plan": 1}
    assert summary["context"]["route_support"] == {"supported": 1, "unsupported:provider_not_in_pilot": 1}
    assert "only attempts whose effective mode is adaptive" in summary["skills"]["planned_not_delivered_note"]
    assert "Context delivery" in observations.render_text(summary)


def test_ignored_task_inputs_are_explained(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    record = plan_record("01-work", requested="static", effective="static", reason="static_requested",
                         supported=None, acquisition=False, inputs=False, planned=False)
    record["task_inputs_ignored"] = {"reason": "static_mode", "facts": ["language=go"], "skills": ["apgr:x-profile"]}
    write(run / "state.json", {"run_id": "run-1", "run_layout": {}, "outcome": "completed"})
    write(run / "01-work.context-plan.json", record)
    value = explain.explain_run(run)
    assert value["attempts"][0]["task_inputs_ignored"] == record["task_inputs_ignored"]
    assert "task inputs ignored (static_mode): language=go, apgr:x-profile" in explain.render_explanation(value)


def instruction_view(status="projected", reason=None):
    view = {"schema": "apg.claude-instruction-projection/v1", "status": status, "reason": reason, "diagnostic": None}
    if status in ("projected", "not_used_static_fallback"):
        view.update(
            selection={"classes": ["review_verification"], "capabilities": {"ambient_tools": False},
                       "selected": ["preamble", "role-split"], "omitted": ["repomap"]},
            fragments=[{"id": "preamble", "selected": True, "stages": ["planning"], "requires": [], "why": "p", "bytes": 10},
                       {"id": "role-split", "selected": True, "stages": ["planning"], "requires": [], "why": "r", "bytes": 20},
                       {"id": "repomap", "selected": False, "stages": ["review_verification"],
                        "requires": ["ambient_tools"], "why": "ambient MCP", "bytes": 400}],
            source={"path": "/x/claude/CLAUDE.md", "bytes": 11781, "sha256": "a" * 64},
            manifest={"path": "/x/claude/instruction-fragments-v1.json", "bytes": 900, "sha256": "b" * 64},
            projection={"path": "/run/01.instruction-projection.md", "bytes": 11381, "sha256": "c" * 64,
                        "projection_id": "d" * 64},
            comparison={"boundary": "APGR tracked Claude standing-instruction source (claude/CLAUDE.md body)",
                        "static_bytes": 11781, "projected_bytes": 11381, "delta_bytes": 400, "delta_percent": 3.4},
            measurement="prospective")
    return view


@pytest.mark.parametrize("case", ["projected_observed", "projected_not_applied", "projected_no_launcher",
                                  "static_fallback", "disabled", "not_used", "not_applicable", "static", "older"])
def test_instruction_projection_explained_in_json_and_human_views(tmp_path, case):
    run = tmp_path / "run"
    run.mkdir()
    write(run / "state.json", {"run_id": "run-1", "run_layout": {}, "outcome": "completed"})
    record = plan_record("01-review")
    if case == "static":
        record.update(requested_mode="static", effective_mode="static", reason="static_requested")
    elif case == "older":
        pass
    elif case == "static_fallback":
        record["instruction_projection"] = instruction_view("static_fallback", "instruction_source_changed")
    elif case == "disabled":
        record["instruction_projection"] = instruction_view("disabled", "instructions_static_configured")
    elif case == "not_used":
        record["instruction_projection"] = instruction_view("not_used_static_fallback")
    elif case == "not_applicable":
        record["instruction_projection"] = instruction_view("not_applicable", "attempt_not_adaptive")
    else:
        record["instruction_projection"] = instruction_view()
    write(run / "01-review.context-plan.json", record)
    if case in ("projected_observed", "projected_not_applied"):
        applied = case == "projected_observed"
        write(run / "01-review.context-launcher-deliveries.json", {
            "coverage": "complete", "boundary": "native", "events": (
                [{"channel": "instructions", "controlled_bytes": 11900}] if applied else []),
            "instruction_projection": {"applied": applied, "reason": None if applied else "source_guidance_inactive",
                                       "witnessed": applied, "instructions_argument_bytes": 11900 if applied else 0,
                                       "static_counterfactual_instructions_bytes": 12300 if applied else None,
                                       "measurement": "observed_at_launcher_boundary" if applied
                                       else "prospective_only:source_guidance_inactive"}})
    value = explain.explain_run(run)
    (attempt,) = value["attempts"]
    instructions = attempt["instructions"]
    expected_mode = {"projected_observed": "projected", "projected_not_applied": "projected",
                     "projected_no_launcher": "projected", "not_used": "not_used_static_fallback",
                     "older": "unknown"}.get(case, case)
    assert instructions["mode"] == expected_mode
    text = explain.render_explanation(value)
    assert f"instructions: {expected_mode.upper()}" in text
    assert "not tokens, not total provider context" in text and "not tokens" in " ".join(value["notes"])
    basis = {"projected_observed": "transmitted_projection", "projected_no_launcher": "prospective_projection",
             "projected_not_applied": "not_transmitted", "not_used": "not_transmitted"}.get(case)
    assert instructions["delta_basis"] == basis
    if basis in ("transmitted_projection", "prospective_projection"):
        kind = "transmitted" if basis == "transmitted_projection" else "prospective"
        assert instructions["delta_bytes"] == 400 and instructions["delta_percent"] == 3.4
        assert f"static 11781 -> projected 11381 (delta 400, 3.4%; {kind})" in text
    else:
        # No delta for an attempt that sent no projection.
        assert instructions["delta_bytes"] is None and instructions["delta_percent"] is None
        assert instructions["projected_bytes"] is None and "-> projected" not in text
    if basis == "not_transmitted":
        assert instructions["prepared_projection_bytes"] == 11381 and instructions["static_bytes"] == 11781
        assert "a 11381-byte projection was prepared but not transmitted; no delta" in text
    if expected_mode == "projected":
        assert instructions["classes"] == ["review_verification"]
        assert instructions["omitted"] == [{"id": "repomap", "because": "requires ambient_tools", "why": "ambient MCP",
                                            "bytes": 400}]
        assert "instruction omitted: repomap" in text
        assert instructions["digests"]["projection"] == "c" * 64 and "c" * 64 in text
    measurement = {"projected_observed": "observed_at_launcher_boundary",
                   "projected_not_applied": "prospective_only:source_guidance_inactive",
                   "projected_no_launcher": "prospective_only:no_launcher_record"}.get(case, "unknown")
    assert instructions["measurement"] == measurement and f"instruction measurement: {measurement}" in text
    if case == "projected_observed":
        assert instructions["observed_instructions_bytes"] == 11900 and "static counterfactual 12300 bytes" in text
    if case == "projected_not_applied":
        assert instructions["applied"] is False and "consumed but not applied (source_guidance_inactive)" in text
    if case == "older":
        assert instructions["reason"] == "not_recorded" and instructions["static_bytes"] is None
    if case in ("static_fallback", "disabled", "not_applicable"):
        assert f"reason: {instructions['reason']}" in text
    assert json.loads(json.dumps(value)) == value
