"""Bounded run listing over existing dispatch records (``observations list``).

``observations_discovery`` finds run leaves by name. ``list_runs`` reads each selected run through ``observations.collect_run``
under one aggregate byte budget and returns one versioned dict;
``render_list`` formats that dict only. Nothing here starts a provider,
planner, Go bridge or server, reads ``dispatcher.sqlite3``, or writes,
retries, resumes, cancels or cleans anything.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from . import observations as obs
from . import observations_discovery as discovery
from . import observations_explain as explain
from .observations_discovery import discover_runs

SCHEMA = "apg.dispatch-run-list/v1"
DEFAULT_LATEST = 20
MAX_LIST_READ_BYTES = 128 * 1024 * 1024
MAX_ATTEMPTS = explain.MAX_ATTEMPTS
RUNTIME_NOTES = {
    "terminal_recorded": "terminal outcome recorded by the dispatcher",
    "no_terminal_record": "no terminal record: running, interrupted or crashed; not a health claim",
    "records_unavailable": "run records could not be read; runtime state unknown",
}
V2_DATABASE_NOTE = "a V2 terminal status may be recorded only in dispatcher.sqlite3, which list does not read"
NOTES = [
    "Recorded state only: no live process, provider or dispatcher database is consulted; nothing is a health claim.",
    "Telemetry coverage is independent of runtime state.",
    "Use the explain command shown for a run for per-attempt context detail.",
]


class _Reader:
    """``collect_run``-compatible reader over one aggregate budget; keeps records it already parsed."""

    def __init__(self, total: int) -> None:
        self.budget = explain.ReadBudget(total, [])
        self.start(None)

    def start(self, run_dir: Path | None) -> None:
        self.run_dir, self.state, self.times = run_dir, None, []

    def __call__(self, path: Path, limit: int, warnings: list[str], label: str) -> Any:
        self.budget.warnings = warnings
        value = self.budget.read(path, limit, label)
        if isinstance(value, Mapping):
            if path.name == "state.json" and path.parent == self.run_dir:
                self.state = value
            elif path.name.endswith(".meta.json"):
                self.times += [value.get("started_at"), value.get("ended_at")]
            elif path.name.endswith(obs.EVENT_SUFFIX):
                self.times.append(value.get("recorded_at"))
        return value


def _filter_v2(candidates: list[dict[str, Any]], reader: _Reader, project: str | None,
               phase: str | None, warnings: list[str]) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Apply --project/--phase to canonical V2 runs by their recorded ``result.json``."""
    excluded: Counter[str] = Counter({"unattributed": 0, "unread": 0})
    if project is None and phase is None:
        return candidates, excluded
    kept = []
    for candidate in candidates:
        if candidate["source"] != "v2_canonical":
            kept.append(candidate)
            continue
        if reader.budget.exhausted:
            excluded["unread"] += 1
            continue
        result = obs._mapping(reader(candidate["path"] / "result.json", obs.MAX_RECORD_BYTES, warnings,
                                     f"{candidate['leaf']} result.json"))
        candidate["result"] = result or None
        if not result:
            excluded["unread" if reader.budget.exhausted else "unattributed"] += 1
        elif (project is None or result.get("project") == project) and (phase is None or result.get("phase_id") == phase):
            kept.append(candidate)
    if excluded["unread"]:
        obs._warn(warnings, f"{excluded['unread']} canonical V2 run(s) could not be attributed to the filter "
                            "because the read budget was exhausted; they are excluded, not absent")
    return kept, excluded


def _counts(values) -> dict[str, int]:
    return dict(sorted(Counter(obs._value(v) for v in values).items()))


def _state_fields(source: str, state: Mapping[str, Any], result: Mapping[str, Any],
                  present: dict[str, bool], records: str) -> dict[str, Any]:
    v2 = source in ("v2_canonical", "v2_projection")
    record, name = (result, "result.json") if v2 else (state, "state.json")
    outcome = obs._text(record.get("status" if v2 else "outcome"))
    if records in ("not_read", "budget_exhausted") or (not record and present.get(name)):
        runtime = "records_unavailable"
    else:
        runtime = "terminal_recorded" if outcome else "no_terminal_record"
    note = RUNTIME_NOTES[runtime] + (f"; {V2_DATABASE_NOTE}" if v2 and runtime == "no_terminal_record" else "")
    stages = None
    if state.get("expected_stages") is not None or state.get("stages_invoked") is not None:
        invoked = [s for s in obs._list(state.get("stages_invoked")) if isinstance(s, str)]
        stages = {"expected": [s for s in obs._list(state.get("expected_stages")) if isinstance(s, str)],
                  "invoked": invoked, "completed": [s for s in obs._list(state.get("stages_completed")) if isinstance(s, str)],
                  "last_invoked": invoked[-1] if invoked else None}
    flag = (lambda key: record.get(key) if isinstance(record.get(key), bool) else None)
    return {"runtime": runtime, "note": note, "outcome": outcome,
            "semantic_outcome": obs._text(record.get("semantic_status" if v2 else "semantic_outcome")),
            "finalization_outcome": obs._text(record.get("finalization_status" if v2 else "finalization_outcome")),
            "complete": flag("complete"), "blocking_reason": obs._text(record.get("blocking_reason")),
            "manager_disposition_required": flag("manager_disposition_required"), "dry_run": flag("dry_run"),
            "stages": stages}


def _attempt_fields(run: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    attempts = run["attempts"]
    failures = sum(1 for a in attempts if (a["status"] is not None and a["status"] != "runner_returned")
                   or a["exit_code"] not in (0, None) or a.get("dispatch_error_type"))
    fallback: Counter[str] = Counter()
    for a in attempts:
        if a.get("requested_mode") == "adaptive" and a.get("effective_mode") != "adaptive":
            for reason in (a.get("reason") or obs.UNAVAILABLE).split(","):
                fallback[reason.strip() or obs.UNAVAILABLE] += 1
    return ({"count": len(attempts), "with_event": sum(1 for a in attempts if a["event"]),
             "status": _counts(a["status"] for a in attempts), "failures": failures,
             "routes": _counts(f"{obs._value(a['provider'])}/{obs._value(a['profile'])}" for a in attempts)},
            {"requested_modes": _counts(a["requested_mode"] for a in attempts),
             "effective_modes": _counts(a["effective_mode"] for a in attempts),
             "delivery": _counts(explain.delivery_label(a) for a in attempts),
             "route_support": _counts(a["route_support"] for a in attempts),
             "fallback_reasons": dict(sorted(fallback.items())),
             "acquisition_events": len(run["acquisitions"])})


def _generation(run: Mapping[str, Any], state: Mapping[str, Any], resolved: Mapping[str, Any]) -> dict[str, Any]:
    generation = obs._mapping(state.get("controller_generation"))
    roster = obs._mapping(resolved.get("roster")).get("generation")
    return {"controller_commit": obs._text(generation.get("commit")), "controller_tree": obs._text(generation.get("tree")),
            "controller_id": obs._text(generation.get("controller_id")),
            "manifest_sha256": obs._text(generation.get("manifest_sha256")),
            "controller_source": obs._text(generation.get("reason")),
            "safety_established": generation.get("safety_established") if isinstance(generation.get("safety_established"), bool) else None,
            "roster_generation": roster if type(roster) in (int, str) else None,
            "apgr_versions": sorted({a["apgr_version"] for a in run["attempts"] if a["apgr_version"]}),
            "attempt_build_commits": sorted({a["build_commit"] for a in run["attempts"] if a["build_commit"]})}


def _moment(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def _times(candidate: Mapping[str, Any], recorded: list[Any], modified: datetime | None) -> dict[str, Any]:
    moments = [m for m in map(_moment, recorded) if m is not None]
    return {"started_at": discovery.iso(candidate["started"]), "started_at_source": candidate["started_source"],
            "last_attempt_at": discovery.iso(max(moments)) if moments else None,
            "last_attempt_at_source": "attempt meta started_at/ended_at and event recorded_at" if moments else None,
            "record_modified_at": discovery.iso(modified), "record_modified_at_source": "filesystem_mtime" if modified else None,
            "terminal_at": None, "terminal_at_note": "not recorded by the dispatcher"}


def _explain(candidate: Mapping[str, Any], explicit_outbox: bool, explicit_home: bool) -> dict[str, Any] | None:
    source = candidate["source"]
    if source == "symlink_leaf":
        return None
    argv = ["apgr", "dispatcher", "observations", "explain"]
    if source == "v2_canonical":
        argv += ["--v2", "--leaf", candidate["leaf"]]
    else:
        argv += ["--project", candidate["project"]]
        argv += ["--phase", candidate["phase_id"]] if source != "historical_leaf" else []
        argv += ["--leaf", candidate["leaf"]]
    placeholders = []
    if explicit_outbox and source != "v2_canonical":
        argv += ["--outbox-root", "<OUTBOX_ROOT>"]
        placeholders.append("<OUTBOX_ROOT>")
    if explicit_home:
        argv += ["--apgr-home", "<APGR_HOME>"]
        placeholders.append("<APGR_HOME>")
    return {"argv": argv, "placeholders": placeholders}


def _identity(candidate: Mapping[str, Any], run_id: str | None) -> dict[str, Any]:
    source, project, phase, leaf = candidate["source"], candidate["project"], candidate["phase_id"], candidate["leaf"]
    layout_id = (leaf if source == "v2_canonical" else f"{project}/{leaf}" if source == "historical_leaf"
                 else f"{project}/{phase}/{leaf}")
    return {"run_id": run_id or layout_id, "run_id_source": "records" if run_id else "layout",
            "leaf": leaf, "project": project, "phase_id": phase, "source": source,
            "location": {"root": candidate["root"], "relative": candidate["relative"]},
            "dispatcher": {"outbox_leaf": "v1", "historical_leaf": "v1", "v2_projection": "v2",
                           "v2_canonical": "v2"}.get(source)}


def _present(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except OSError:
        return False


def _empty(reason: str | None, records: str) -> dict[str, Any]:
    return {"run": None, "state": {}, "result": {}, "resolved": {}, "record": {}, "records": records,
            "records_reason": reason, "warnings": [], "missing": [], "present": {}, "times": [],
            "modified": None, "workers": False}


def _read(candidate: dict[str, Any], reader: _Reader) -> dict[str, Any]:
    """Read one run's records under the shared budget; the only per-run I/O."""
    path = candidate["path"]
    v2 = candidate["source"] in ("v2_canonical", "v2_projection")
    exhausted = reader.budget.exhausted
    reader.start(path)
    warnings: list[str] = []
    run = obs.collect_run(path, reader=reader, max_attempts=MAX_ATTEMPTS)
    state, times = obs._mapping(reader.state), list(reader.times)
    if v2:
        result = candidate["result"] if candidate["result"] is not None else \
            reader(path / "result.json", obs.MAX_RECORD_BYTES, warnings, "result.json")
        record, resolved, expected = obs._mapping(result), {}, ("result.json",)
    else:
        record, expected = state, ("state.json", "resolved.json")
        resolved = obs._mapping(reader(path / "resolved.json", obs.MAX_RECORD_BYTES, warnings, "resolved.json"))
    found = {"state.json": state, "result.json": record if v2 else {}, "resolved.json": resolved}
    missing = [name for name in expected if not found[name]]
    warnings = run["warnings"] + warnings
    records = "partial" if warnings or missing or reader.budget.exhausted != exhausted else "read"
    primary = expected[0]
    return {"run": run, "state": state, "result": record if v2 else {}, "resolved": resolved, "record": record,
            "records": records, "records_reason": None, "warnings": warnings, "missing": missing,
            "present": {primary: _present(path / primary)}, "times": times,
            "modified": discovery.mtime(path / primary) if _present(path / primary) else None,
            "workers": (path / "workers").is_dir() and not (path / "workers").is_symlink()}


def _row(candidate: dict[str, Any], reader: _Reader, explicit_outbox: bool, explicit_home: bool,
         warnings: list[str]) -> dict[str, Any]:
    if candidate["source"] == "symlink_leaf":
        data = _empty(candidate["records_reason"], "not_read")
    elif reader.budget.exhausted:
        data = _empty("aggregate read budget exhausted before this run", "budget_exhausted")
    else:
        try:
            data = _read(candidate, reader)
        except (obs.ObservationError, OSError, TypeError, AttributeError, ValueError, KeyError) as error:
            data = _empty(f"run records unreadable ({type(error).__name__})", "not_read")
            obs._warn(warnings, f"{candidate['leaf']}: {data['records_reason']}")
    run, record = data["run"], data["record"]
    identity = _identity(candidate, obs._text(record.get("run_id")))
    identity["project"] = identity["project"] or obs._text(record.get("project"))
    identity["phase_id"] = identity["phase_id"] or obs._text(record.get("phase_id"))
    attempts, context = _attempt_fields(run) if run else (None, None)
    workers = run["workers"] if run else []
    return {**identity,
            "phase_type": obs._text(record.get("phase_type")), "execution_mode": obs._text(record.get("execution_mode")),
            "lifecycle": obs._text(record.get("lifecycle")), "finalization_policy": obs._text(record.get("finalization_policy")),
            "generation": _generation(run, data["state"], data["resolved"]) if run else None,
            "times": _times(candidate, data["times"], data["modified"]),
            "state": _state_fields(candidate["source"], data["state"], data["result"], data["present"], data["records"]),
            "attempts": attempts, "context": context,
            "workers": {"jobs": len(workers),
                        "by_kind_status": _counts(f"{obs._value(w['worker_kind'])}:{obs._value(w['status'])}" for w in workers),
                        "quota": _counts(w["quota"] for w in workers if w["quota"] is not None)} if data["workers"] else None,
            "telemetry": {"records": data["records"], "records_reason": data["records_reason"],
                          "attempts_without_event": attempts["count"] - attempts["with_event"] if attempts else None,
                          "observation_failures": len(obs._list(data["state"].get("observation_failures"))),
                          "warning_count": len(data["warnings"]), "warnings": data["warnings"], "missing": data["missing"]},
            "feedback": None, "explain": _explain(candidate, explicit_outbox, explicit_home)}


def list_runs(*, outbox_root: Path | None = None, project: str | None = None, phase: str | None = None,
              apgr_home: Path | None = None, v2: bool = False, latest: int = DEFAULT_LATEST,
              feedback: bool = True, explicit_outbox: bool = False, explicit_home: bool = False,
              max_read_bytes: int = MAX_LIST_READ_BYTES) -> dict[str, Any]:
    """One normalized query result; ``outbox_root`` with ``project=None`` lists all projects."""
    if not 1 <= latest <= obs.MAX_RUNS:
        raise obs.ObservationError(f"--latest must be between 1 and {obs.MAX_RUNS}")
    candidates, scan = discover_runs(outbox_root=outbox_root, project=project, phase=phase, apgr_home=apgr_home, v2=v2)
    warnings = scan.warnings
    reader = _Reader(max_read_bytes)
    newest = (lambda c: (c["started"] or discovery.OLDEST, c["leaf"]))
    # De-duplicate before filtering: outbox rows (including a verified projection) win over the
    # canonical V2 run they name, newest first, so a projected canonical run is never read twice.
    preferred = sorted(sorted(candidates, key=newest, reverse=True), key=lambda c: c["source"] == "v2_canonical")
    unique: dict[Path, dict[str, Any]] = {}
    for candidate in preferred:
        key = candidate["path"].resolve() if candidate["source"] != "symlink_leaf" else candidate["path"]
        unique.setdefault(key, candidate)
    kept, excluded = _filter_v2(list(unique.values()), reader, project, phase, warnings)
    ordered = sorted(kept, key=newest, reverse=True)
    rows = [_row(c, reader, explicit_outbox, explicit_home, warnings) for c in ordered[:latest]]
    if feedback and apgr_home is not None:
        rows_by_id = {row["run_id"]: row for row in rows}
        found = obs.read_feedback(obs.storage_root(Path(apgr_home)) / "feedback.jsonl", set(rows_by_id), warnings)
        for row in rows:
            labels = [f["label"] for f in found if f.get("run_id") == row["run_id"]]
            row["feedback"] = {"count": len(labels), "labels": _counts(labels)}
    return {"schema": SCHEMA,
            "query": {"outbox_root": ("explicit" if explicit_outbox else "configured") if outbox_root is not None else None,
                      "project": project, "all_projects": outbox_root is not None and project is None,
                      "phase": phase, "v2": v2, "latest": latest, "feedback": feedback},
            "discovery": {"discovered": len(unique), "matched": len(kept), "listed": len(rows),
                          "entries_scanned": scan.entries, "skipped": dict(sorted(scan.skipped.items())),
                          "v2_unattributed_excluded": excluded["unattributed"],
                          "v2_unread_excluded": excluded["unread"],
                          "truncated": scan.truncated, "order_complete": not scan.truncated,
                          "bounds": {"projects": discovery.MAX_PROJECTS, "phase_dirs": discovery.MAX_PHASE_DIRS,
                                     "entries": discovery.MAX_DISCOVERY_ENTRIES, "read_bytes": max_read_bytes,
                                     "attempts_per_run": MAX_ATTEMPTS}},
            "runs": rows, "notes": list(NOTES), "warnings": warnings}


def _pairs(mapping: Mapping[str, Any] | None) -> str:
    return ", ".join(f"{key}={value}" for key, value in mapping.items()) if mapping else "none"


def _shown(value: Any) -> str:
    return "not recorded" if value is None else str(value)


def _render_state(row: Mapping[str, Any]) -> list[str]:
    state, times = row["state"], row["times"]
    lines = [f"  started: {_shown(times['started_at'])} ({_shown(times['started_at_source'])}); "
             f"last attempt: {_shown(times['last_attempt_at'])} ({_shown(times['last_attempt_at_source'])}); "
             f"record modified: {_shown(times['record_modified_at'])} ({_shown(times['record_modified_at_source'])}); "
             f"terminal time: {times['terminal_at_note']}",
             f"  state: {state['runtime']} - {state['note']}",
             f"  outcome={_shown(state['outcome'])} semantic={_shown(state['semantic_outcome'])} "
             f"finalization={_shown(state['finalization_outcome'])} complete={_shown(state['complete'])} "
             f"blocking_reason={_shown(state['blocking_reason'])} "
             f"manager_disposition_required={_shown(state['manager_disposition_required'])} dry_run={_shown(state['dry_run'])}"]
    stages = state["stages"]
    if stages is not None:
        lines.append(f"  stages: invoked {len(stages['invoked'])}/{len(stages['expected'])} "
                     f"[{', '.join(stages['invoked'])}]; completed {len(stages['completed'])}/{len(stages['expected'])} "
                     f"[{', '.join(stages['completed'])}]; expected [{', '.join(stages['expected'])}]; "
                     f"last invoked: {_shown(stages['last_invoked'])}")
    return lines


def _render_records(row: Mapping[str, Any]) -> list[str]:
    attempts, context, generation = row["attempts"], row["context"], row["generation"]
    lines = []
    if attempts is not None:
        lines.append(f"  attempts: {attempts['count']} ({attempts['with_event']} with observation event); "
                     f"status: {_pairs(attempts['status'])}; failures: {attempts['failures']}; routes: {_pairs(attempts['routes'])}")
        lines.append(f"  context: requested {_pairs(context['requested_modes'])}; effective {_pairs(context['effective_modes'])}; "
                     f"delivery {_pairs(context['delivery'])}; route support {_pairs(context['route_support'])}; "
                     f"fallback reasons {_pairs(context['fallback_reasons'])}; acquisition events: {context['acquisition_events']}")
    workers = row["workers"]
    lines.append("  workers: no worker records" if workers is None else
                 f"  workers: {workers['jobs']} job(s); kind:status {_pairs(workers['by_kind_status'])}; "
                 f"quota {_pairs(workers['quota'])}")
    if generation is not None:
        lines.append(f"  build: controller commit {_shown(generation['controller_commit'])} tree {_shown(generation['controller_tree'])} "
                     f"id {_shown(generation['controller_id'])} manifest {_shown(generation['manifest_sha256'])} "
                     f"source {_shown(generation['controller_source'])} safety_established {_shown(generation['safety_established'])}; "
                     f"roster generation {_shown(generation['roster_generation'])}; "
                     f"apgr versions [{', '.join(generation['apgr_versions'])}]; "
                     f"attempt build commits [{', '.join(generation['attempt_build_commits'])}]")
    return lines


def _render_row(row: Mapping[str, Any]) -> list[str]:
    telemetry, feedback, handoff = row["telemetry"], row["feedback"], row["explain"]
    lines = [f"{row['leaf']}  [{row['dispatcher'] or 'dispatcher unknown'} {row['source']}]",
             f"  run: {row['run_id']} (id from {row['run_id_source']}); "
             f"location: {row['location']['root']}:{row['location']['relative']}",
             f"  project/phase: {_shown(row['project'])} / {_shown(row['phase_id'])}; phase type: {_shown(row['phase_type'])}; "
             f"execution: {_shown(row['execution_mode'])}; lifecycle: {_shown(row['lifecycle'])}; "
             f"finalization policy: {_shown(row['finalization_policy'])}"]
    lines += _render_state(row) + _render_records(row)
    lines.append(f"  telemetry: records {telemetry['records']}"
                 + (f" ({telemetry['records_reason']})" if telemetry["records_reason"] else "")
                 + f"; attempts without event: {_shown(telemetry['attempts_without_event'])}; "
                 f"observation failures: {telemetry['observation_failures']}; warnings: {telemetry['warning_count']}; "
                 f"missing: [{', '.join(telemetry['missing'])}]")
    lines += [f"    warning: {warning}" for warning in telemetry["warnings"]]
    lines.append("  feedback: not read" if feedback is None else
                 f"  feedback: {feedback['count']} ({_pairs(feedback['labels'])}; attributed, not machine-observed)")
    lines.append("  explain: not available (records not read)" if handoff is None else
                 f"  explain: {' '.join(handoff['argv'])}"
                 + (f"  (replace {', '.join(handoff['placeholders'])})" if handoff["placeholders"] else ""))
    return lines


def render_list(value: Mapping[str, Any]) -> str:
    """Human view built only from the ``list_runs`` dict; it performs no I/O."""
    query, found = value["query"], value["discovery"]
    lines = ["APGR runs (newest first; recorded state only, not live health)",
             f"query: project={query['project'] or ('all' if query['all_projects'] else 'none')} "
             f"phase={query['phase'] or 'any'} v2={query['v2']} latest={query['latest']} "
             f"outbox root={query['outbox_root'] or 'not scanned'} feedback={query['feedback']}",
             f"discovery: {found['listed']} listed of {found['matched']} matching ({found['discovered']} discovered); "
             f"{found['entries_scanned']} entries scanned; skipped {_pairs(found['skipped'])}; V2 runs excluded by "
             f"the filter: {found['v2_unattributed_excluded']} without a recorded project/phase, "
             f"{found['v2_unread_excluded']} unread (budget)",
             f"bounds: {_pairs(found['bounds'])}; truncated={found['truncated']} order_complete={found['order_complete']}"
             + ("" if found["order_complete"] else " (rows are not guaranteed to be the newest)")]
    if not value["runs"]:
        lines += ["", "no runs found"]
    for row in value["runs"]:
        lines += [""] + _render_row(row)
    lines.append("")
    lines += [f"Note: {note}" for note in value["notes"]]
    lines += [f"Warning: {warning}" for warning in value["warnings"]]
    return "\n".join(lines) + "\n"
