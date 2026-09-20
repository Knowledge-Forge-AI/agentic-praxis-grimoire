"""APG166ZA-OBSERVABILITY-RUNS1 run discovery/listing over real temporary run layouts.

Fixtures are real directory trees shaped like the maintained V1 outbox, the
historical project-level layout, V2 canonical runs and V2 projection symlinks.
Listing must be bounded, read-only, human/JSON consistent and never claim health.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_phase import observations
from agent_phase import observations_discovery as discovery
from agent_phase import observations_list as listing
from test_agent_phase_context import isolated_provider_version_probes  # noqa: F401 (autouse)
from test_agent_phase_disposition_flow import repository  # noqa: F401 (fixture)
from test_agent_phase_observations import _home, _v1_dispatch, _v2

ROOT = Path(__file__).resolve().parents[3]
V2_PROJECTED = "apgr-run-v2-implementation_testing-20260105T000000Z-0123abcd"
V2_OPEN = "apgr-run-v2-review-20260110T000000Z-89abcdef"


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value))


def plan(prefix: str, *, requested="adaptive", effective="adaptive", reason="qualified_projection",
         planned=True, supported=True) -> dict:
    record = {"schema": "apg.invocation-context/v1", "binding_id": prefix.split("-", 1)[1],
              "attempt_id": f"att-{prefix}", "attempt_number": 1, "requested_mode": requested,
              "effective_mode": effective, "reason": reason, "planned": planned,
              "controlled_total": {"bytes": 4200, "boundary": "canonical argv JSON plus runner stdin"},
              "attempted_request": {"facts": [{"kind": "language", "value": "python"}]}}
    if supported is not None:
        record["route_support"] = {"supported": supported, "code": None if supported else "provider_not_in_pilot"}
    return record


def meta(stage: str, started: str, ended: str, profile: str) -> dict:
    return {"stage": stage, "provider": "claude", "profile": profile, "exit_code": 0,
            "started_at": started, "ended_at": ended}


def event(prefix: str, run_id: str, recorded: str) -> dict:
    return {"schema": observations.SCHEMA, "dispatcher": "v1", "run_id": run_id, "binding_id": prefix.split("-", 1)[1],
            "attempt_id": f"att-{prefix}", "attempt_number": 1, "route": {"provider": "claude", "profile": "opus-high"},
            "build": {"apgr_version": "0.13.0", "controller_commit": "a" * 40},
            "outcome": {"status": "runner_returned", "exit_code": 0}, "recorded_at": recorded}


def v1_state(root: Path, project: str, phase: str, leaf: str, **fields) -> dict:
    state = {"run_id": f"{project}/{phase}/{leaf}", "project": project, "phase_id": phase,
             "run_layout": {"kind": "project-phase-dispatch", "leaf": leaf},
             "run_directory": str(root / project / phase / leaf), "cwd": str(root),
             "phase_type": "implementation_testing", "execution_mode": "claude_only", "lifecycle": "standard",
             "finalization_policy": "checkpoint", "outcome": None, "semantic_outcome": None,
             "finalization_outcome": "not_attempted", "complete": False, "blocking_reason": None,
             "manager_disposition_required": False, "dry_run": False,
             "expected_stages": ["plan", "work"], "stages_invoked": [], "stages_completed": [],
             "controller_generation": {"commit": "a" * 40, "tree": "b" * 40, "controller_id": "c" * 64,
                                       "manifest_sha256": "d" * 64, "safety_established": True,
                                       "reason": "controller_generation", "controller_root": str(root)}}
    state.update(fields)
    return state


@pytest.fixture
def layout(tmp_path: Path) -> dict:
    outbox, home, elsewhere = tmp_path / "outbox", tmp_path / "home", tmp_path / "elsewhere"
    runs = home / "state" / "runs"
    phase_a = outbox / "demo" / "PHASE-A"
    # Completed adaptive V1 run with a fallback attempt, a worker quota result and an observation failure.
    done = phase_a / "PHASE-A-dispatch--20260101T000000000001Z"
    run_id = f"demo/PHASE-A/{done.name}"
    write(done / "state.json", v1_state(outbox, "demo", "PHASE-A", done.name, outcome="completed",
                                        semantic_outcome="accepted", complete=True,
                                        stages_invoked=["plan", "work"], stages_completed=["plan", "work"],
                                        observation_failures=[{"prefix": "02-work", "diagnostic": "OSError"}]))
    write(done / "resolved.json", {"roster": {"generation": 8}})
    write(done / "01-plan.context-plan.json", plan("01-plan"))
    write(done / "01-plan.meta.json", meta("plan", "2026-01-01T00:00:01Z", "2026-01-01T00:05:00Z", "opus-high-plan"))
    write(done / f"01-plan{observations.EVENT_SUFFIX}", event("01-plan", run_id, "2026-01-01T00:05:01Z"))
    write(done / "02-work.context-plan.json", plan("02-work", effective="static",
                                                   reason="route_unsupported:provider_not_in_pilot,optional_plan_failed",
                                                   supported=False))
    write(done / "02-work.meta.json", meta("work", "2026-01-01T00:06:00Z", "2026-01-01T00:30:00Z", "opus-high"))
    write(done / "workers" / "parent-1" / "jobs" / "job-1" / "job-1.result.json",
          {"status": "failed", "worker_kind": "luna", "quota": {"classification": "explicit_quota_exhaustion"}})
    # In-progress run: no terminal outcome, one stage invoked.
    write(phase_a / "PHASE-A-dispatch--20260102T000000000000Z" / "state.json",
          v1_state(outbox, "demo", "PHASE-A", "PHASE-A-dispatch--20260102T000000000000Z", stages_invoked=["plan"]))
    # Interrupted before state.json: one meta record only.
    write(phase_a / "PHASE-A-dispatch--20260103T000000000000Z" / "01-plan.meta.json",
          meta("plan", "2026-01-03T00:00:01Z", "2026-01-03T00:00:02Z", "opus-high-plan"))
    # Malformed state.json.
    write(phase_a / "PHASE-A-dispatch--20260104T000000000000Z" / "state.json", "{not json")
    # Verified V2 projection (symlink + locator + archive link) of a failed canonical run.
    write(runs / V2_PROJECTED / "result.json", {"schema": "agent-phase-result-v2", "run_id": V2_PROJECTED,
                                                "project": "demo", "phase_id": "PHASE-A", "status": "failed",
                                                "semantic_status": "failed", "finalization_status": "failed",
                                                "phase_type": "implementation_testing", "execution_mode": "gemini_sub",
                                                "lifecycle": "standard", "run_directory": str(runs / V2_PROJECTED)})
    projected = phase_a / "PHASE-A-dispatch--20260105T000000000000Z"
    os.symlink(runs / V2_PROJECTED, projected)
    write(phase_a / f"{projected.name}.locator.json", {"run_id": V2_PROJECTED})
    os.symlink(runs / V2_PROJECTED, phase_a / f"{projected.name}.zip")
    # A symlinked leaf pointing outside the APGR home, and a FIFO named like a leaf.
    (elsewhere / "fake-run").mkdir(parents=True)
    write(elsewhere / "fake-run" / "state.json", {"outcome": "completed"})
    os.symlink(elsewhere / "fake-run", phase_a / "PHASE-A-dispatch--20260106T000000000000Z")
    os.mkfifo(phase_a / "PHASE-A-dispatch--20260107T000000000000Z")
    (phase_a / "launch-abc").mkdir()
    write(phase_a / "launch.lock", "")
    # Blocked, observation-disabled run with a PILOT1-shaped plan (no inputs, no route support, no event).
    blocked = outbox / "demo" / "PHASE-B" / "PHASE-B-dispatch--20251201T000000000000Z"
    write(blocked / "state.json", v1_state(outbox, "demo", "PHASE-B", blocked.name, outcome="blocked",
                                           blocking_reason="review_blocked", stages_invoked=["plan"]))
    write(blocked / "01-plan.context-plan.json", plan("01-plan", effective="static",
                                                      reason="selective_projection_unqualified", supported=None))
    write(blocked / "01-plan.meta.json", meta("plan", "2025-12-01T00:00:01Z", "2025-12-01T00:01:00Z", "opus-high-plan"))
    # Historical project-level layout and a symlinked phase directory.
    write(outbox / "demo" / "PHASE-OLD--20250101T000000000000Z" / "state.json",
          {"run_id": "demo/PHASE-OLD--20250101T000000000000Z", "project": "demo", "phase_id": "PHASE-OLD",
           "outcome": "completed"})
    os.symlink(outbox / "demo" / "PHASE-B", outbox / "demo" / "linked-phase")
    # Another project with the newest run, a symlinked project and a stray file.
    write(outbox / "other" / "X" / "X-dispatch--20260201T000000000000Z" / "state.json",
          v1_state(outbox, "other", "X", "X-dispatch--20260201T000000000000Z", outcome="completed"))
    os.symlink(outbox / "demo", outbox / "linked-project")
    write(outbox / "README.txt", "not a project")
    # Canonical V2 runs: one in flight (no result.json) and one with a caller-supplied id.
    write(runs / V2_OPEN / "request.json", {"schema": "x"})
    write(runs / "custom-run-id" / "request.json", {"schema": "x"})
    write(runs / f"{V2_PROJECTED}.zip", "archive")
    return {"outbox": outbox, "home": home, "runs": runs, "done": done, "tmp": tmp_path}


def by_leaf(value: dict) -> dict:
    return {row["leaf"]: row for row in value["runs"]}


# ------------------------------------------------------------------ shared readers (U1)


def test_worker_reader_skips_symlinked_parent_and_job_directories(layout: dict) -> None:
    done, tmp = layout["done"], layout["tmp"]
    write(tmp / "outside" / "jobs" / "job-x" / "job-x.result.json", {"status": "completed", "worker_kind": "gemini"})
    os.symlink(tmp / "outside", done / "workers" / "parent-linked")
    os.symlink(tmp / "outside" / "jobs" / "job-x", done / "workers" / "parent-1" / "jobs" / "job-linked")
    rows = observations.collect_run(done)["workers"]
    assert [(w["parent_id"], w["job_id"]) for w in rows] == [("parent-1", "job-1")]


def test_worker_parent_bound_is_reported(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    write(layout["done"] / "workers" / "parent-2" / "jobs" / "job-2" / "job-2.result.json", {"status": "completed"})
    monkeypatch.setattr(observations, "MAX_WORKER_PARENTS", 1)
    run = observations.collect_run(layout["done"])
    assert len(run["workers"]) <= 1 and any("worker parent limit reached" in w for w in run["warnings"])


def test_collect_run_defaults_are_unchanged_and_attempts_are_bounded(layout: dict) -> None:
    done = layout["done"]
    assert observations.collect_run(done) == observations.collect_run(done, reader=None, max_attempts=None)
    limited = observations.collect_run(done, max_attempts=1)
    assert len(limited["attempts"]) == 1 and any("attempt limit reached" in w for w in limited["warnings"])
    seen = []
    def reader(path, limit, warnings, label):
        seen.append(path.name)
        return observations._read_json(path, limit, warnings, label)
    assert observations.collect_run(done, reader=reader) == observations.collect_run(done)
    assert "state.json" in seen and "job-1.result.json" in seen


def test_select_runs_orders_v2_runs_by_embedded_timestamp(tmp_path: Path) -> None:
    runs = tmp_path / "home" / "state" / "runs"
    older = runs / "apgr-run-v2-review-20260101T000000Z-00000000"
    newer = runs / "apgr-run-v2-implementation_testing-20260201T000000Z-11111111"
    older.mkdir(parents=True)
    newer.mkdir()
    assert observations.select_runs(apgr_home=tmp_path / "home", v2_home=True, latest=1) == [newer]


def test_feedback_reader_refuses_symlinks_and_oversized_lines(tmp_path: Path) -> None:
    real = tmp_path / "real.jsonl"
    observations.append_feedback(real, run_id="r", label="helpful", source="agent")
    link = tmp_path / "link.jsonl"
    os.symlink(real, link)
    warnings: list[str] = []
    assert observations.read_feedback(link, None, warnings) == [] and "not a regular file" in warnings[0]
    real.write_bytes(real.read_bytes() + b"x" * (observations.MAX_FEEDBACK_LINE_BYTES + 10) + b"\n")
    warnings = []
    assert len(observations.read_feedback(real, None, warnings)) == 1
    assert any("line limit" in w for w in warnings)


# ------------------------------------------------------------------ discovery and listing (U2)


def test_project_listing_is_newest_first_with_explicit_state(layout: dict) -> None:
    value = listing.list_runs(outbox_root=layout["outbox"], project="demo", apgr_home=layout["home"])
    assert value["schema"] == listing.SCHEMA
    leaves = [row["leaf"] for row in value["runs"]]
    assert leaves == ["PHASE-A-dispatch--20260106T000000000000Z", "PHASE-A-dispatch--20260105T000000000000Z",
                      "PHASE-A-dispatch--20260104T000000000000Z", "PHASE-A-dispatch--20260103T000000000000Z",
                      "PHASE-A-dispatch--20260102T000000000000Z", "PHASE-A-dispatch--20260101T000000000001Z",
                      "PHASE-B-dispatch--20251201T000000000000Z", "PHASE-OLD--20250101T000000000000Z"]
    rows = by_leaf(value)
    done = rows["PHASE-A-dispatch--20260101T000000000001Z"]
    assert done["state"]["runtime"] == "terminal_recorded" and done["state"]["outcome"] == "completed"
    assert done["dispatcher"] == "v1" and done["source"] == "outbox_leaf" and done["run_id_source"] == "records"
    running = rows["PHASE-A-dispatch--20260102T000000000000Z"]["state"]
    assert running["runtime"] == "no_terminal_record" and "not a health claim" in running["note"]
    assert running["stages"]["last_invoked"] == "plan"
    no_state = rows["PHASE-A-dispatch--20260103T000000000000Z"]
    assert no_state["state"]["runtime"] == "no_terminal_record"
    assert no_state["telemetry"]["missing"] == ["state.json", "resolved.json"] and no_state["run_id_source"] == "layout"
    assert no_state["times"]["last_attempt_at"] == "2026-01-03T00:00:02Z"
    malformed = rows["PHASE-A-dispatch--20260104T000000000000Z"]
    assert malformed["state"]["runtime"] == "records_unavailable" and malformed["telemetry"]["records"] == "partial"
    projected = rows["PHASE-A-dispatch--20260105T000000000000Z"]
    assert projected["source"] == "v2_projection" and projected["dispatcher"] == "v2"
    assert projected["state"]["runtime"] == "terminal_recorded" and projected["state"]["outcome"] == "failed"
    assert projected["run_id"] == V2_PROJECTED and projected["execution_mode"] == "gemini_sub"
    outside = rows["PHASE-A-dispatch--20260106T000000000000Z"]
    assert outside["telemetry"]["records"] == "not_read" and outside["explain"] is None
    assert outside["telemetry"]["records_reason"] == "symlink_target_outside_apgr_home_runs"
    assert outside["state"]["runtime"] == "records_unavailable" and outside["state"]["outcome"] is None
    blocked = rows["PHASE-B-dispatch--20251201T000000000000Z"]
    assert blocked["state"]["outcome"] == "blocked" and blocked["state"]["blocking_reason"] == "review_blocked"
    assert blocked["attempts"]["with_event"] == 0 and blocked["telemetry"]["attempts_without_event"] == 1
    assert blocked["context"]["delivery"] == {"static_with_shadow_plan": 1}
    historical = rows["PHASE-OLD--20250101T000000000000Z"]
    assert historical["source"] == "historical_leaf" and historical["phase_id"] == "PHASE-OLD"
    assert historical["state"]["outcome"] == "completed"
    assert historical["explain"]["argv"][-4:] == ["--project", "demo", "--leaf", historical["leaf"]]
    skipped = value["discovery"]["skipped"]
    # linked-phase (symlink), the FIFO (special); zip/locator/launch entries are ordinary non-leaves.
    assert skipped["symlink"] == 1 and skipped["special"] == 1 and skipped["non_leaf"] == 4
    assert value["discovery"]["order_complete"] is True and value["discovery"]["truncated"] is False


def test_row_context_worker_generation_time_and_feedback_fields(layout: dict) -> None:
    home = layout["home"]
    feedback = observations.storage_root(home) / "feedback.jsonl"
    run_id = f"demo/PHASE-A/{layout['done'].name}"
    observations.append_feedback(feedback, run_id=run_id, label="helpful", source="agent")
    observations.append_feedback(feedback, run_id=run_id, label="missing", source="operator")
    observations.append_feedback(feedback, run_id="elsewhere", label="missing", source="operator")
    value = listing.list_runs(outbox_root=layout["outbox"], project="demo", phase="PHASE-A", apgr_home=home)
    row = by_leaf(value)[layout["done"].name]
    assert row["attempts"] == {"count": 2, "with_event": 1, "status": {"runner_returned": 2}, "failures": 0,
                               "routes": {"claude/opus-high": 2}}
    assert row["context"] == {"requested_modes": {"adaptive": 2}, "effective_modes": {"adaptive": 1, "static": 1},
                              "delivery": {"adaptive": 1, "static_with_shadow_plan": 1},
                              "route_support": {"supported": 1, "unsupported:provider_not_in_pilot": 1},
                              "fallback_reasons": {"optional_plan_failed": 1, "route_unsupported:provider_not_in_pilot": 1},
                              "acquisition_events": 0}
    assert row["workers"] == {"jobs": 1, "by_kind_status": {"luna:failed": 1}, "quota": {"explicit_quota_exhaustion": 1}}
    generation = row["generation"]
    assert generation["controller_commit"] == "a" * 40 and generation["roster_generation"] == 8
    assert generation["apgr_versions"] == ["0.13.0"] and generation["manifest_sha256"] == "d" * 64
    assert row["times"]["started_at"] == "2026-01-01T00:00:00.000001Z"
    assert row["times"]["last_attempt_at"] == "2026-01-01T00:30:00Z" and row["times"]["terminal_at"] is None
    assert row["telemetry"]["observation_failures"] == 1 and row["telemetry"]["records"] == "read"
    assert row["feedback"] == {"count": 2, "labels": {"helpful": 1, "missing": 1}}
    assert row["explain"]["argv"] == ["apgr", "dispatcher", "observations", "explain", "--project", "demo",
                                      "--phase", "PHASE-A", "--leaf", layout["done"].name]
    no_feedback = listing.list_runs(outbox_root=layout["outbox"], project="demo", apgr_home=home, feedback=False)
    assert all(r["feedback"] is None for r in no_feedback["runs"])


def test_filters_all_projects_and_latest(layout: dict) -> None:
    everything = listing.list_runs(outbox_root=layout["outbox"], apgr_home=layout["home"], latest=2)
    assert [r["leaf"] for r in everything["runs"]] == ["X-dispatch--20260201T000000000000Z",
                                                       "PHASE-A-dispatch--20260106T000000000000Z"]
    assert everything["query"]["all_projects"] is True and everything["discovery"]["listed"] == 2
    assert everything["discovery"]["skipped"]["symlink"] == 2  # linked-project and linked-phase
    phase_b = listing.list_runs(outbox_root=layout["outbox"], phase="PHASE-B", apgr_home=layout["home"])
    assert [r["leaf"] for r in phase_b["runs"]] == ["PHASE-B-dispatch--20251201T000000000000Z"]
    assert listing.list_runs(outbox_root=layout["outbox"], project="absent", apgr_home=layout["home"])["runs"] == []
    linked = listing.list_runs(outbox_root=layout["outbox"], project="linked-project", apgr_home=layout["home"])
    assert linked["runs"] == [] and linked["discovery"]["skipped"]["symlink"] == 1
    with pytest.raises(observations.ObservationError):
        listing.list_runs(outbox_root=layout["outbox"], project="demo", latest=0)


def test_v2_canonical_runs_merge_with_projections_and_order_by_time(layout: dict) -> None:
    home = layout["home"]
    os.utime(layout["runs"] / "custom-run-id", (1_700_000_000, 1_700_000_000))
    only_v2 = listing.list_runs(apgr_home=home, v2=True)
    rows = by_leaf(only_v2)
    assert [r["leaf"] for r in only_v2["runs"]] == [V2_OPEN, V2_PROJECTED, "custom-run-id"]
    assert rows["custom-run-id"]["times"]["started_at_source"] == "filesystem_mtime"
    open_run = rows[V2_OPEN]["state"]
    assert open_run["runtime"] == "no_terminal_record" and "dispatcher.sqlite3" in open_run["note"]
    assert rows[V2_OPEN]["telemetry"]["missing"] == ["result.json"]
    assert rows[V2_OPEN]["explain"]["argv"][-3:] == ["--v2", "--leaf", V2_OPEN]
    assert only_v2["query"]["outbox_root"] is None
    merged = listing.list_runs(outbox_root=layout["outbox"], project="demo", phase="PHASE-A", apgr_home=home, v2=True)
    sources = [r["source"] for r in merged["runs"] if r["run_id"] == V2_PROJECTED]
    assert sources == ["v2_projection"]
    assert merged["discovery"]["v2_unattributed_excluded"] == 2
    assert V2_OPEN not in by_leaf(merged)


def test_v2_filter_budget_nanosecond_leaves_and_duplicate_projections(layout: dict) -> None:
    home, phase_a = layout["home"], layout["outbox"] / "demo" / "PHASE-A"
    starved = listing.list_runs(apgr_home=home, v2=True, project="demo", max_read_bytes=1)
    assert starved["discovery"]["v2_unread_excluded"] == 1 and starved["discovery"]["v2_unattributed_excluded"] == 2
    assert any("read budget was exhausted" in w for w in starved["warnings"])
    # A 9-digit fraction orders by time rather than falling to the bottom.
    (phase_a / "PHASE-A-dispatch--20260108T000000123456789Z").mkdir()
    # A second, newer verified projection of the same canonical run replaces the older row.
    newer = phase_a / "PHASE-A-dispatch--20260109T000000000000Z"
    os.symlink(layout["runs"] / V2_PROJECTED, newer)
    write(phase_a / f"{newer.name}.locator.json", {"run_id": V2_PROJECTED})
    value = listing.list_runs(outbox_root=layout["outbox"], project="demo", apgr_home=home, v2=True, latest=3)
    leaves = [row["leaf"] for row in value["runs"]]
    assert leaves[:2] == [newer.name, "PHASE-A-dispatch--20260108T000000123456789Z"]
    assert [r["leaf"] for r in value["runs"] if r["run_id"] == V2_PROJECTED] == [newer.name]


def test_other_apgr_home_projection_gets_a_distinct_reason(layout: dict, tmp_path: Path) -> None:
    other = tmp_path / "other-home" / "state" / "runs" / "apgr-run-v2-x-20260301T000000Z-aaaaaaaa"
    other.mkdir(parents=True)
    phase_a = layout["outbox"] / "demo" / "PHASE-A"
    os.symlink(other, phase_a / "PHASE-A-dispatch--20260301T000000000000Z")
    write(phase_a / "PHASE-A-dispatch--20260301T000000000000Z.locator.json", {"run_id": other.name})
    os.symlink(layout["runs"] / V2_PROJECTED, phase_a / "PHASE-A-dispatch--20260302T000000000000Z")
    row = by_leaf(listing.list_runs(outbox_root=layout["outbox"], project="demo", apgr_home=layout["home"]))
    assert row["PHASE-A-dispatch--20260301T000000000000Z"]["telemetry"]["records_reason"] == \
        "symlink_target_other_apgr_home_runs"
    assert row["PHASE-A-dispatch--20260302T000000000000Z"]["telemetry"]["records_reason"] == \
        "symlink_leaf_without_locator"


def test_discovery_bounds_mark_results_incomplete(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(discovery, "MAX_DISCOVERY_ENTRIES", 5)
    value = listing.list_runs(outbox_root=layout["outbox"], apgr_home=layout["home"])
    assert value["discovery"]["truncated"] is True and value["discovery"]["order_complete"] is False
    assert any("not guaranteed newest" in w for w in value["warnings"])
    assert "rows are not guaranteed to be the newest" in listing.render_list(value)
    monkeypatch.setattr(discovery, "MAX_DISCOVERY_ENTRIES", 50_000)
    monkeypatch.setattr(discovery, "MAX_PROJECTS", 1)
    assert listing.list_runs(outbox_root=layout["outbox"], apgr_home=layout["home"])["discovery"]["truncated"] is True


def test_unreadable_run_records_do_not_break_the_listing(layout: dict) -> None:
    locked = layout["done"] / "workers" / "locked"
    locked.mkdir()
    locked.chmod(0)
    try:
        value = listing.list_runs(outbox_root=layout["outbox"], project="demo", apgr_home=layout["home"])
    finally:
        locked.chmod(0o700)
    row = by_leaf(value)[layout["done"].name]
    assert row["telemetry"]["records"] == "not_read"
    assert row["telemetry"]["records_reason"] == "run records unreadable (PermissionError)"
    assert row["state"]["runtime"] == "records_unavailable" and row["run_id_source"] == "layout"
    assert len(value["runs"]) == 8 and str(layout["tmp"]) not in json.dumps(value)


def test_aggregate_read_budget_leaves_identity_rows(layout: dict) -> None:
    value = listing.list_runs(outbox_root=layout["outbox"], project="demo", apgr_home=layout["home"],
                              max_read_bytes=1500)
    records = [row["telemetry"]["records"] for row in value["runs"]]
    assert "budget_exhausted" in records
    exhausted = next(row for row in value["runs"] if row["telemetry"]["records"] == "budget_exhausted")
    assert exhausted["state"]["runtime"] == "records_unavailable" and exhausted["leaf"] and exhausted["run_id"]
    assert any("aggregate read budget exhausted" in w for row in value["runs"] for w in row["telemetry"]["warnings"])


def _flatten(value, prefix=""):
    if isinstance(value, dict):
        if value and all(type(v) is int for v in value.values()):
            yield from (f"{k}={v}" for k, v in value.items())
        for key, item in value.items():
            yield from _flatten(item, f"{prefix}.{key}")
    elif isinstance(value, list):
        for item in value:
            yield from _flatten(item, prefix)
    elif isinstance(value, (str, int)) and not isinstance(value, bool):
        yield str(value)


def test_human_output_is_rendered_from_the_json_value_without_io(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    value = listing.list_runs(outbox_root=layout["outbox"], project="demo", apgr_home=layout["home"], v2=True,
                              explicit_outbox=True, explicit_home=True)
    def refuse(*args, **kwargs):
        raise AssertionError("render_list must not perform I/O")
    for owner, name in ((os, "scandir"), (Path, "read_bytes"), (Path, "lstat"), (Path, "stat"), (Path, "open")):
        monkeypatch.setattr(owner, name, refuse)
    text = listing.render_list(value)
    monkeypatch.undo()
    for row in value["runs"]:
        missing = [token for token in _flatten(row) if token not in text]
        assert missing == [], (row["leaf"], missing)
    assert "<OUTBOX_ROOT>" in text and "<APGR_HOME>" in text
    assert listing.render_list(listing.list_runs(apgr_home=layout["tmp"] / "empty", v2=True)).count("no runs found") == 1


def test_json_is_path_free_and_never_claims_health(layout: dict) -> None:
    value = listing.list_runs(outbox_root=layout["outbox"], apgr_home=layout["home"], v2=True, latest=50)
    serialized = json.dumps(value)
    assert str(layout["tmp"]) not in serialized
    text = listing.render_list(value)
    for rendered in (serialized.lower(), text.lower()):
        assert "healthy" not in rendered and '"ok"' not in rendered


def _snapshot(*roots: Path) -> list[tuple]:
    rows = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            info = path.lstat()
            rows.append((str(path), info.st_mode, info.st_size, info.st_mtime_ns))
    return rows


def test_listing_is_read_only_and_starts_no_process(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    before = _snapshot(layout["outbox"], layout["home"])
    def refuse(*args, **kwargs):
        raise AssertionError("listing must not start a process")
    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)
    listing.list_runs(outbox_root=layout["outbox"], apgr_home=layout["home"], v2=True)
    assert _snapshot(layout["outbox"], layout["home"]) == before
    assert not observations.storage_root(layout["home"]).exists()


def test_symlinked_state_runs_is_refused_by_list_and_explain(layout: dict, tmp_path: Path) -> None:
    linked_home = tmp_path / "linked-home"
    (linked_home / "state").mkdir(parents=True)
    os.symlink(layout["runs"], linked_home / "state" / "runs")
    value = listing.list_runs(outbox_root=layout["outbox"], project="demo", phase="PHASE-A",
                              apgr_home=linked_home, v2=True)
    assert any("state/runs is a symlink" in w for w in value["warnings"])
    assert V2_OPEN not in by_leaf(value)
    projected = by_leaf(value)["PHASE-A-dispatch--20260105T000000000000Z"]
    assert projected["source"] == "symlink_leaf" and projected["telemetry"]["records"] == "not_read"
    for argv in (["--v2", "--leaf", V2_OPEN],
                 ["--project", "demo", "--phase", "PHASE-A", "--leaf", "PHASE-A-dispatch--20260105T000000000000Z",
                  "--outbox-root", str(layout["outbox"])]):
        assert run_cli("explain", *argv, "--apgr-home", str(linked_home)).returncode == 2, argv


# ------------------------------------------------------------------ command routes (U3)


def run_cli(*args, cwd=None):
    return subprocess.run([sys.executable, str(ROOT / "libexec/agent_phase/cli.py"), "observations", *args],
                          capture_output=True, text=True, timeout=60, cwd=cwd)


def test_cli_list_json_text_errors_and_explain_handoff(layout: dict) -> None:
    outbox, home = str(layout["outbox"]), str(layout["home"])
    listed = run_cli("list", "--project", "demo", "--outbox-root", outbox, "--apgr-home", home, "--json")
    assert listed.returncode == 0, listed.stderr
    value = json.loads(listed.stdout)
    assert value["schema"] == listing.SCHEMA and value["query"]["outbox_root"] == "explicit"
    text = run_cli("list", "--project", "demo", "--outbox-root", outbox, "--apgr-home", home)
    assert text.returncode == 0 and "state: no_terminal_record" in text.stdout and "state: terminal_recorded" in text.stdout
    row = by_leaf(value)[layout["done"].name]
    argv = [{"<OUTBOX_ROOT>": outbox, "<APGR_HOME>": home}.get(a, a) for a in row["explain"]["argv"][3:]]
    explained = run_cli(*argv, "--json")
    assert explained.returncode == 0, explained.stderr
    assert json.loads(explained.stdout)["run"]["run_id"] == row["run_id"]
    v2_row = next(r for r in json.loads(run_cli("list", "--v2", "--apgr-home", home, "--json").stdout)["runs"]
                  if r["leaf"] == V2_OPEN)
    v2_argv = [{"<APGR_HOME>": home}.get(a, a) for a in v2_row["explain"]["argv"][3:]]
    assert run_cli(*v2_argv, "--json").returncode == 0
    projected = by_leaf(value)["PHASE-A-dispatch--20260105T000000000000Z"]
    projected_argv = [{"<OUTBOX_ROOT>": outbox, "<APGR_HOME>": home}.get(a, a) for a in projected["explain"]["argv"][3:]]
    (layout["runs"] / V2_PROJECTED / "acquisitions").mkdir()  # read at the verified target, not via the symlink
    projected_explained = json.loads(run_cli(*projected_argv, "--json").stdout)
    assert projected_explained["run"]["run_id"] == V2_PROJECTED
    assert not [w for w in projected_explained["warnings"] if w.startswith("acquisitions")]
    empty = run_cli("list", "--project", "absent", "--outbox-root", outbox, "--apgr-home", home)
    assert empty.returncode == 0 and "no runs found" in empty.stdout
    for bad in (["list"], ["list", "--project", "demo", "--all-projects"], ["list", "--project", "../x"],
                ["list", "--project", "demo", "--latest", "0"], ["list", "--v2", "--outbox-root", outbox],
                ["list", "--project", "demo", "--outbox-root", str(layout["done"] / "state.json")],
                ["explain", "--leaf", layout["done"].name], ["explain", str(layout["done"]), "--leaf", "x"],
                ["explain", "--project", "demo", "--phase", "PHASE-A", "--leaf", "not-a-leaf", "--outbox-root", outbox],
                ["explain", "--project", "demo", "--phase", "PHASE-A", "--leaf", "../escape", "--outbox-root", outbox],
                ["explain", "--project", "demo", "--phase", "PHASE-A", "--leaf", "PHASE-A-dispatch--20260106T000000000000Z",
                 "--outbox-root", outbox],
                ["explain", "--project", "demo", "--phase", "linked-phase", "--leaf",
                 "PHASE-B-dispatch--20251201T000000000000Z", "--outbox-root", outbox]):
        result = run_cli(*bad, "--apgr-home", home)
        assert result.returncode == 2, (bad, result.stdout, result.stderr)


def test_wrapper_and_top_level_routes_list(layout: dict, tmp_path: Path) -> None:
    wrapper = subprocess.run([str(ROOT / "bin/agent-phase-observations"), "list", "--project", "demo",
                              "--outbox-root", str(layout["outbox"]), "--apgr-home", str(layout["home"]), "--json"],
                             capture_output=True, text=True, timeout=60)
    assert wrapper.returncode == 0, wrapper.stderr
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "HOME": str(tmp_path / "user-home")}
    relative = os.path.relpath(layout["outbox"], tmp_path)
    top = subprocess.run([sys.executable, "-m", "agentic_praxis_grimoire", "--project-root", str(ROOT),
                          "--apgr-home", str(layout["home"]), "--outbox-root", relative,
                          "dispatcher", "observations", "list", "--project=demo", "--json"],
                         capture_output=True, text=True, env=env, cwd=tmp_path, timeout=60)
    if top.returncode != 0 and "No module named" in top.stderr:
        pytest.skip("top-level package entry point unavailable in this interpreter")
    assert top.returncode == 0, top.stderr
    value = json.loads(top.stdout)
    assert value["query"]["outbox_root"] == "explicit" and value["runs"] == json.loads(wrapper.stdout)["runs"]
    # A global outbox root without a project scope is surfaced as a usage error, not dropped.
    unscoped = subprocess.run([sys.executable, "-m", "agentic_praxis_grimoire", "--project-root", str(ROOT),
                               "--apgr-home", str(layout["home"]), "--outbox-root", relative,
                               "dispatcher", "observations", "list", "--v2", "--json"],
                              capture_output=True, text=True, env=env, cwd=tmp_path, timeout=60)
    assert unscoped.returncode == 2 and "--outbox-root requires" in unscoped.stderr, unscoped.stderr


# ------------------------------------------------------------------ maintained dispatch writers


def test_real_v1_and_v2_dispatch_records_are_listed(repository: Path, tmp_path: Path) -> None:
    state, runner, run_dir = _v1_dispatch(repository, tmp_path / "v1", _home(tmp_path / "v1"))
    value = listing.list_runs(outbox_root=run_dir.parents[2], project=run_dir.parents[1].name,
                              apgr_home=tmp_path / "v1" / "apgr-home")
    (row,) = value["runs"]
    assert row["run_id"] == state["run_id"] and row["state"]["runtime"] == "terminal_recorded"
    assert row["state"]["outcome"] == state["outcome"] == "completed"
    assert row["attempts"]["count"] == row["attempts"]["with_event"] == len(runner.calls) == 5
    assert row["state"]["stages"]["completed"] == state["stages_completed"]
    assert row["context"]["requested_modes"] == {"static": 5} and row["telemetry"]["missing"] == []
    assert row["generation"]["apgr_versions"] and row["times"]["last_attempt_at"]
    result, _, canonical, home = _v2(tmp_path / "v2")
    value = listing.list_runs(outbox_root=tmp_path / "v2" / "outbox", project=result["project"], apgr_home=home, v2=True)
    rows = [r for r in value["runs"] if r["run_id"] == canonical.name]
    assert len(rows) == 1 and rows[0]["state"]["runtime"] == "terminal_recorded"
    assert rows[0]["state"]["outcome"] == result["status"] == "completed"
    assert rows[0]["attempts"]["count"] == 5 and rows[0]["dispatcher"] == "v2"
