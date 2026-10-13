"""Bounded per-run context explanation: one query dict for human and JSON output.

``explain_run`` reads only fixed sibling records of one run directory (state or
result, per-attempt context plan/transport/deliveries/failure, observation
events and acquisition events) under per-file and aggregate byte limits. It
never needs the optional index and never starts a provider, planner, Go bridge
or server. ``render_explanation`` formats the returned dict only; nothing
parses display text.

The explanation keeps four evidence classes apart: the planner's prospective
plan, the transport the adapter prepared for the runner, transmissions the
runner/launcher observed, and provider/agent/operator reports. None of them
proves model use, token counts or cost.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
from typing import Any, Mapping

from . import observations as obs

SCHEMA = "apg.dispatch-context-explanation/v1"
MAX_ATTEMPTS = 256
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_DIAGNOSTIC_REFERENCES = 32
DELIVERY_NOTES = {
    "adaptive": "selected skills were placed on the runner transport (see transmission coverage)",
    "static_with_shadow_plan": "planned only; selected skills NOT delivered",
    "static_fallback": "adaptive requested; static transport used without a plan",
    "static": "static requested; nothing selected",
    "unknown": "context records not available for this attempt",
}
HINTS = {
    "acquisition_binary_unavailable": "set APGR_GO_BINARY to a built apgr binary (a source-only checkout has no persistent MCP executable)",
    "required_skills_unsatisfied": "a matched fact makes its owning skill required and a required skill did not fit the budget; "
                                   "raise max_initial_context_bytes, declare narrower facts, or set manifest_facts = false",
    "mandatory_overflow": "the mandatory prompt alone exceeds the configured budget",
    "transport_overhead_overflow": "argv plus the planned payload and notices exceeded the budget",
    "optional_plan_failed": "the optional planner or projection failed before launch; see the diagnostic type",
}
NOTES = [
    "Planned bytes are the planner's prospective view; runner-transport bytes are what the adapter handed to the runner; "
    "observed transmissions are process-boundary records. None of these proves model use.",
    "Provider-reported usage is not collected at this seam; no token or cost figure is inferred.",
    "runner_returned means the provider process returned, not that the task succeeded.",
    "In adaptive attempts the delivered stdin is the planned payload recorded in the context-plan file; "
    "the <prefix>.prompt.md file keeps the static rendered prompt.",
    "Instruction byte deltas count APGR-owned standing-instruction bytes at the labelled boundary only; "
    "they are not tokens and not a reduction of total provider context.",
]
INSTRUCTION_MODES = ("projected", "static", "static_fallback", "disabled", "not_applicable", "not_used_static_fallback")


class ReadBudget:
    def __init__(self, total: int, warnings: list[str]) -> None:
        self.remaining = total
        self.warnings = warnings
        self.exhausted = False

    def read(self, path: Path, limit: int, label: str) -> Any:
        try:
            info = path.lstat()
        except FileNotFoundError:
            return None
        except OSError as error:
            obs._warn(self.warnings, f"{label}: {type(error).__name__}")
            return None
        if stat.S_ISREG(info.st_mode) and info.st_size > self.remaining:
            if not self.exhausted:
                obs._warn(self.warnings, "aggregate read budget exhausted; later records not read")
            self.exhausted = True
            return None
        value = obs._read_json(path, limit, self.warnings, label)
        if stat.S_ISREG(info.st_mode):
            self.remaining -= min(info.st_size, limit)
        return value


def _cost(value: Any) -> dict[str, Any] | None:
    value = obs._mapping(value)
    if not value:
        return None
    return {"bytes": obs._integer(value.get("bytes")), "characters": obs._integer(value.get("characters"))}


def delivery_label(plan: Mapping[str, Any]) -> str:
    requested, effective = plan.get("requested_mode"), plan.get("effective_mode")
    if effective == "adaptive":
        return "adaptive"
    if requested == "adaptive":
        return "static_with_shadow_plan" if plan.get("planned") is True else "static_fallback"
    if requested == "static":
        return "static"
    return "unknown"


def _skills(plan: Mapping[str, Any]) -> dict[str, Any]:
    prospective = obs._mapping(plan.get("prospective_plan"))
    selected, deferred, unavailable, not_considered, incompatible = [], [], [], 0, 0
    for decision in obs._list(prospective.get("decisions")):
        decision = obs._mapping(decision)
        row = {"id": obs._text(decision.get("selected_id")) or obs._text(decision.get("requested_id")),
               "requested_id": obs._text(decision.get("requested_id")),
               "reason": obs._text(decision.get("reason")), "required": decision.get("required") is True,
               "bytes": obs._integer(obs._mapping(decision.get("whole_source")).get("bytes"))}
        status = decision.get("status")
        if status == "selected":
            selected.append(row)
        elif status == "unavailable" and "incompatible with consumer" in (row["reason"] or "") and not row["required"] \
                and row["reason"] and decision.get("requested_id") == decision.get("selected_id"):
            incompatible += 1
        elif status == "unavailable":
            unavailable.append(row)
        elif status == "deferred" and row["reason"] == "applicability_unknown_no_positive_fact":
            not_considered += 1
        elif status == "deferred":
            deferred.append(row)
    acquisition = obs._mapping(plan.get("acquisition"))
    return {"selected": selected, "deferred": deferred, "unavailable": unavailable,
            "not_applicable_count": not_considered, "consumer_incompatible_count": incompatible,
            "unknown_facts": [f"{f.get('kind')}={f.get('value')}" for f in obs._list(prospective.get("unknown_facts"))
                              if isinstance(f, Mapping)],
            "acquirable_count": len(obs._list(acquisition.get("allowed_ids"))) if acquisition else 0,
            "acquisition_status": obs._text(acquisition.get("status")) if acquisition else None,
            "recovery_files": [{"id": obs._text(r.get("id")), "path": obs._text(r.get("path")),
                                "bytes": obs._integer(r.get("bytes"))}
                               for r in obs._list(acquisition.get("recovery")) if isinstance(r, Mapping)]}


def _inputs(plan: Mapping[str, Any]) -> dict[str, Any]:
    inputs = obs._mapping(plan.get("inputs"))
    request = obs._mapping(plan.get("attempted_request"))
    if not inputs:
        # Older (PILOT1-shaped) records carry only the facts sent to the planner.
        facts = [{"kind": obs._text(f.get("kind")), "value": obs._text(f.get("value")), "source": "dispatcher",
                  "status": "supplied"} for f in obs._list(request.get("facts")) if isinstance(f, Mapping)]
        return {"recorded": False, "facts": facts, "requests": [], "manifest": None, "task_source": None}
    facts = [{"kind": obs._text(f.get("kind")), "value": obs._text(f.get("value")),
              "source": obs._text(f.get("source")), "status": obs._text(f.get("status"))}
             for f in obs._list(inputs.get("facts")) if isinstance(f, Mapping)]
    facts.extend({"kind": obs._text(f.get("kind")), "value": obs._text(f.get("value")), "source": "dispatcher",
                  "status": "supplied"} for f in obs._list(request.get("facts"))
                 if isinstance(f, Mapping) and f.get("kind") == "work_class")
    manifest = obs._mapping(inputs.get("manifest"))
    return {"recorded": True, "postures": [p for p in obs._list(inputs.get("postures")) if isinstance(p, str)],
            "facts": facts,
            "requests": [{"id": obs._text(r.get("id")), "source": obs._text(r.get("source")),
                          "required": r.get("required") is True, "applies": r.get("applies") is True,
                          "stages": [s for s in obs._list(r.get("stages")) if isinstance(s, str)]}
                         for r in obs._list(inputs.get("requests")) if isinstance(r, Mapping)],
            "manifest": {"enabled": manifest.get("enabled") is True,
                         "files": [{"file": obs._text(f.get("file")), "status": obs._text(f.get("status")),
                                    "reason": obs._text(f.get("reason"))}
                                   for f in obs._list(manifest.get("files")) if isinstance(f, Mapping)]},
            "task_source": obs._text(inputs.get("task_source"))}


def _ignored(value: Any) -> dict[str, Any] | None:
    ignored = obs._mapping(value)
    if not ignored:
        return None
    return {"reason": obs._text(ignored.get("reason")),
            "facts": [f for f in obs._list(ignored.get("facts")) if isinstance(f, str)],
            "skills": [s for s in obs._list(ignored.get("skills")) if isinstance(s, str)]}


def _transmissions(record: Any) -> dict[str, Any] | None:
    if not isinstance(record, Mapping):
        return None
    channels: dict[str, int] = {}
    for event in obs._list(record.get("events")):
        if isinstance(event, Mapping) and type(event.get("controlled_bytes")) is int:
            channel = str(event.get("channel"))
            channels[channel] = channels.get(channel, 0) + event["controlled_bytes"]
    return {"coverage": obs._text(record.get("coverage")), "boundary": obs._text(record.get("boundary")),
            "bytes_by_channel": channels, "diagnostics": [str(d) for d in obs._list(record.get("diagnostics"))][:8]}


def _late(rows: list[Mapping[str, Any]], attempt_id: str | None) -> dict[str, Any]:
    scoped = [r for r in rows if attempt_id and r.get("attempt_id") == attempt_id]
    preparation = [r for r in scoped if r.get("channel") == "preparation"]
    handshakes = [r for r in scoped if r.get("channel") != "preparation" and r.get("operation") == "initialize"]
    requests = [r for r in scoped if r not in preparation and r not in handshakes]
    kinds: dict[str, int] = {}
    for row in requests:
        kinds[str(row.get("kind"))] = kinds.get(str(row.get("kind")), 0) + 1
    late_bytes = sum(r.get("controlled_bytes") or 0 for r in requests if r.get("phase") == "late")
    return {"events": len(scoped), "preparation_events": len(preparation), "handshake_events": len(handshakes),
            "request_kinds": dict(sorted(kinds.items())), "late_controlled_bytes": late_bytes,
            "misses": kinds.get("search_miss", 0), "rejections": kinds.get("rejected", 0),
            "boundary": "APGR acquisition channel records; prelaunch preparation and MCP initialize "
                        "handshakes (including APGR's own probes) are counted separately; not provider consumption"}


def _instruction_bytes(record: Any) -> int | None:
    if not isinstance(record, Mapping):
        return None
    sizes = [e["controlled_bytes"] for e in obs._list(record.get("events"))
             if isinstance(e, Mapping) and e.get("channel") == "instructions" and type(e.get("controlled_bytes")) is int]
    return sum(sizes) if sizes else None


def _omitted(view: Mapping[str, Any], classes: list[str]) -> list[dict[str, Any]]:
    rows = []
    for row in obs._list(view.get("fragments")):
        if not isinstance(row, Mapping) or row.get("selected") is not False:
            continue
        stages = [s for s in obs._list(row.get("stages")) if isinstance(s, str)]
        because = ("not declared for " + "+".join(classes) if not set(stages) & set(classes)
                   else "requires " + ",".join(str(r) for r in obs._list(row.get("requires"))))
        rows.append({"id": obs._text(row.get("id")), "because": because, "why": obs._text(row.get("why")),
                     "bytes": obs._integer(row.get("bytes"))})
    return rows


def _instructions(plan: Mapping[str, Any], launcher: Any) -> dict[str, Any]:
    """APGR-owned standing-instruction projection facts; explicit unknowns, no inference."""
    view = obs._mapping(plan.get("instruction_projection"))
    launch = obs._mapping(obs._mapping(launcher).get("instruction_projection")) if isinstance(launcher, Mapping) else {}
    status = obs._text(view.get("status"))
    if view:
        mode = status if status in INSTRUCTION_MODES else "unknown"
    elif plan.get("requested_mode") == "static":
        mode = "static"
    else:
        mode = "unknown"
    selection, comparison = obs._mapping(view.get("selection")), obs._mapping(view.get("comparison"))
    classes = [c for c in obs._list(selection.get("classes")) if isinstance(c, str)]
    observed = _instruction_bytes(launcher)
    if mode == "projected":
        measurement = (obs._text(launch.get("measurement")) or "unknown") if launch else "prospective_only:no_launcher_record"
    else:
        measurement = "observed_at_launcher_boundary" if observed is not None else "unknown"
    digest = lambda key: obs._text(obs._mapping(view.get(key)).get("sha256"))
    applied = launch.get("applied") if isinstance(launch.get("applied"), bool) else None
    prepared = obs._integer(comparison.get("projected_bytes"))
    # A delta describes what a projection sent (or, without a launcher record,
    # would send). Fallback and consumed-but-unapplied attempts sent none.
    if prepared is None:
        basis = None
    elif mode == "projected" and applied is True:
        basis = "transmitted_projection"
    elif mode == "projected" and applied is None:
        basis = "prospective_projection"
    else:
        basis = "not_transmitted"
    delta = basis in ("transmitted_projection", "prospective_projection")
    percent = comparison.get("delta_percent")
    return {"mode": mode, "reason": obs._text(view.get("reason")) or (None if view else
                                                                       "static_requested" if mode == "static" else "not_recorded"),
            "diagnostic": obs._text(view.get("diagnostic")), "schema": obs._text(view.get("schema")),
            "classes": classes, "capabilities": dict(obs._mapping(selection.get("capabilities"))),
            "selected": [s for s in obs._list(selection.get("selected")) if isinstance(s, str)],
            "omitted": _omitted(view, classes),
            "boundary": obs._text(comparison.get("boundary")),
            "static_bytes": obs._integer(comparison.get("static_bytes")),
            "prepared_projection_bytes": prepared,
            "delta_basis": basis,
            "projected_bytes": prepared if delta else None,
            "delta_bytes": obs._integer(comparison.get("delta_bytes")) if delta else None,
            "delta_percent": percent if delta and isinstance(percent, (int, float)) else None,
            "digests": {"source": digest("source"), "manifest": digest("manifest"), "projection": digest("projection"),
                        "projection_id": obs._text(obs._mapping(view.get("projection")).get("projection_id"))},
            "measurement": measurement,
            "applied": applied,
            "not_applied_reason": obs._text(launch.get("reason")),
            "observed_instructions_bytes": observed,
            "static_counterfactual_instructions_bytes": obs._integer(launch.get("static_counterfactual_instructions_bytes")),
            "note": "APGR-owned instruction bytes only; not tokens, not total provider context"}


def _references(names: list[str], run_dir: Path, prefix: str) -> list[dict[str, Any]]:
    refs = []
    for name in sorted(n for n in names if n.startswith(prefix + ".")):
        if len(refs) >= MAX_DIAGNOSTIC_REFERENCES:
            break
        try:
            info = (run_dir / name).lstat()
        except OSError:
            continue
        if stat.S_ISREG(info.st_mode):
            refs.append({"name": name, "bytes": info.st_size})
    return refs


def explain_run(run_dir: Path, *, attempt: str | None = None, stage: str | None = None,
                feedback_rows: list[Mapping[str, Any]] | None = None,
                max_total_bytes: int = MAX_TOTAL_BYTES) -> dict[str, Any]:
    run_dir = Path(run_dir)
    warnings: list[str] = []
    budget = ReadBudget(max_total_bytes, warnings)
    try:
        names = [entry.name for entry in os.scandir(run_dir)]
    except OSError as error:
        raise obs.ObservationError(f"run directory is not readable: {type(error).__name__}") from error
    state = obs._mapping(budget.read(run_dir / "state.json", obs.MAX_RECORD_BYTES, "state.json"))
    result = obs._mapping(budget.read(run_dir / "result.json", obs.MAX_RECORD_BYTES, "result.json"))
    routes = obs._mapping(state.get("effective_stage_routes"))
    run_id = obs._text(state.get("run_id")) or obs._text(result.get("run_id"))
    prefixes = obs._prefixes(names)
    if len(prefixes) > MAX_ATTEMPTS:
        obs._warn(warnings, f"attempt limit reached; {len(prefixes) - MAX_ATTEMPTS} attempt(s) omitted")
        prefixes = prefixes[:MAX_ATTEMPTS]
    attempts = []
    events = []
    for prefix in prefixes:
        event = budget.read(run_dir / f"{prefix}{obs.EVENT_SUFFIX}", obs.MAX_EVENT_BYTES, f"{prefix} observation")
        if event is not None and (not isinstance(event, Mapping) or event.get("schema") != obs.SCHEMA):
            obs._warn(warnings, f"{prefix} observation: unsupported schema")
            event = None
        plan = budget.read(run_dir / f"{prefix}.context-plan.json", obs.MAX_RECORD_BYTES, f"{prefix} context plan")
        if plan is not None and (not isinstance(plan, Mapping) or plan.get("schema") != "apg.invocation-context/v1"):
            obs._warn(warnings, f"{prefix} context plan: unsupported schema")
            plan = None
        failure = obs._mapping(budget.read(run_dir / f"{prefix}.context-failure.json", obs.MAX_EVENT_BYTES,
                                           f"{prefix} context failure"))
        transport = obs._mapping(budget.read(run_dir / f"{prefix}.context-transport.json", obs.MAX_EVENT_BYTES,
                                             f"{prefix} context transport"))
        deliveries = budget.read(run_dir / f"{prefix}.context-deliveries.json", obs.MAX_RECORD_BYTES, f"{prefix} deliveries")
        launcher = budget.read(run_dir / f"{prefix}.context-launcher-deliveries.json", obs.MAX_RECORD_BYTES,
                               f"{prefix} launcher deliveries")
        meta = obs._mapping(budget.read(run_dir / f"{prefix}.meta.json", obs.MAX_RECORD_BYTES, f"{prefix} meta"))
        ev, pl = obs._mapping(event), obs._mapping(plan)
        binding = obs._text(ev.get("binding_id")) or obs._text(pl.get("binding_id")) or obs._text(meta.get("stage"))
        attempt_id = obs._text(ev.get("attempt_id")) or obs._text(pl.get("attempt_id")) or obs._text(failure.get("attempt_id"))
        if stage is not None and binding != stage:
            continue
        if attempt is not None and not (prefix.startswith(attempt) or attempt_id == attempt):
            continue
        run_id = run_id or obs._text(ev.get("run_id")) or obs._text(pl.get("run_id"))
        route = obs._mapping(ev.get("route"))
        route_record = obs._mapping(routes.get(binding)) if binding else {}
        support = obs._mapping(pl.get("route_support"))
        outcome = obs._mapping(ev.get("outcome"))
        prospective = obs._mapping(pl.get("prospective_plan"))
        source = pl or failure
        label = delivery_label(source) if source else "unknown"
        reason = obs._text(pl.get("reason")) or obs._text(failure.get("reason"))
        hints = [HINTS[r] for r in (reason or "").split(",") if r in HINTS]
        if reason and reason.startswith("route_unsupported:"):
            hints.append("this route keeps static transport in the pilot; see CAPABILITY and the context-planning guide")
        entry = {
            "prefix": prefix, "binding_id": binding, "attempt_id": attempt_id,
            "attempt_number": obs._integer(ev.get("attempt_number")) or obs._integer(pl.get("attempt_number")),
            "invocation_kind": obs._text(ev.get("invocation_kind")) or obs._text(meta.get("invocation_kind")),
            "provider": obs._text(route.get("provider")) or obs._text(meta.get("provider")) or obs._text(route_record.get("provider"))
            or obs._text(support.get("provider")),
            "profile": obs._text(route.get("profile")) or obs._text(meta.get("profile")) or obs._text(route_record.get("profile"))
            or obs._text(support.get("profile")),
            "route": ({"recorded": True, "seam": obs._text(support.get("seam")), "supported": support.get("supported") is True,
                       "code": obs._text(support.get("code")), "preflight": obs._text(support.get("preflight"))}
                      if support else {"recorded": False}),
            "requested_mode": obs._text(source.get("requested_mode")) if source else None,
            "effective_mode": obs._text(source.get("effective_mode")) if source else None,
            "reason": reason, "diagnostic": obs._text(pl.get("diagnostic")) or obs._text(failure.get("diagnostic")),
            "delivery": label, "delivery_note": DELIVERY_NOTES[label], "hints": hints,
            "inputs": _inputs(pl) if pl else None,
            "task_inputs_ignored": _ignored(pl.get("task_inputs_ignored")) if pl else None,
            "skills": _skills(pl) if pl else None,
            "instructions": _instructions(pl, launcher),
            "planned": {"mandatory": _cost(prospective.get("mandatory_cost")),
                        "payload": _cost(prospective.get("payload_cost")),
                        "stdin_budget_after_argv": obs._mapping(pl.get("stdin_budget_after_argv")) or None,
                        "boundary": "planner prospective view (mandatory prompt plus selected skill block)"}
            if prospective else None,
            "runner_transport": ({"bytes": obs._integer(obs._mapping(pl.get("controlled_total")).get("bytes")),
                                  "boundary": obs._text(obs._mapping(pl.get("controlled_total")).get("boundary"))}
                                 if pl.get("controlled_total") else None),
            "transmitted": {"runner": _transmissions(deliveries), "launcher": _transmissions(launcher)},
            "late": None,
            "provider_reported_usage": "unavailable",
            "outcome": {"status": obs._text(outcome.get("status")) or obs._text(transport.get("status")),
                        "exit_code": obs._integer(outcome.get("exit_code")) if outcome else obs._integer(transport.get("exit_code")),
                        "note": "runner_returned is process return, not task success"},
            "diagnostic_references": _references(names, run_dir, prefix),
            "feedback": [],
        }
        if not pl and not failure:
            obs._warn(warnings, f"{prefix}: no context record (older run, static-only invocation or not yet prepared)")
        events.append(entry)
    acquisitions = obs._acquisition_rows(run_dir, run_id or "", warnings) if run_id else []
    for entry in events:
        entry["late"] = _late(acquisitions, entry["attempt_id"])
    attempts = events
    terminal = obs._text(state.get("outcome")) if state else obs._text(result.get("status"))
    runtime = {"terminal_outcome": terminal,
               "note": ("terminal outcome recorded by the dispatcher" if terminal else
                        "no terminal outcome recorded: running, interrupted or crashed (not a health claim)")}
    telemetry = {"attempts": len(attempts),
                 "with_observation_event": sum(1 for p in prefixes if (run_dir / f"{p}{obs.EVENT_SUFFIX}").is_file()),
                 "with_context_plan": sum(1 for a in attempts if a["inputs"] is not None),
                 "with_runner_transmissions": sum(1 for a in attempts if a["transmitted"]["runner"]),
                 "note": "telemetry completeness is independent of runtime state"}
    value = {"schema": SCHEMA, "run": {"run_id": run_id or run_dir.name, "leaf": run_dir.resolve().name,
                                       "dispatcher": "v1" if state.get("run_layout") else ("v2" if result or not state else None),
                                       "project": obs._text(state.get("project")),
                                       "phase_type": obs._text(state.get("phase_type")),
                                       "execution_mode": obs._text(state.get("execution_mode")),
                                       "runtime_state": runtime, "telemetry": telemetry},
            "filters": {"attempt": attempt, "stage": stage},
            "attempts": attempts, "run_feedback": [], "notes": list(NOTES), "warnings": warnings,
            "feedback_note": "feedback is attributed by source (operator, agent, reviewer); it is not machine observation"}
    if feedback_rows:
        attach_feedback(value, feedback_rows)
    return value


def attach_feedback(value: dict[str, Any], rows: list[Mapping[str, Any]]) -> None:
    """Attach separately retained feedback rows for this run (never from the index)."""
    run_id = value["run"]["run_id"]
    rows = [dict(r) for r in rows if r.get("run_id") == run_id]
    for entry in value["attempts"]:
        entry["feedback"] = [r for r in rows if r.get("attempt_id") and r.get("attempt_id") == entry["attempt_id"]]
    value["run_feedback"] = [r for r in rows if not r.get("attempt_id")]


def _bytes(cost: Any) -> str:
    if not isinstance(cost, Mapping) or cost.get("bytes") is None:
        return "not recorded"
    return f"{cost['bytes']} bytes"


def _render_instructions(value: Mapping[str, Any]) -> list[str]:
    head = f"  instructions: {value['mode'].upper()}"
    if value["mode"] == "projected":
        capabilities = ", ".join(f"{k}={str(v).lower()}" for k, v in sorted(value["capabilities"].items()))
        head += f" for {'+'.join(value['classes'])} ({capabilities}); {len(value['selected'])} fragment(s) selected"
    else:
        head += f" - reason: {value['reason']}" + (f" [{value['diagnostic']}]" if value["diagnostic"] else "")
    lines = [head]
    if value["delta_bytes"] is not None:
        kind = "prospective" if value["delta_basis"] == "prospective_projection" else "transmitted"
        lines.append(f"  instruction bytes ({value['boundary']}): static {value['static_bytes']} -> projected "
                     f"{value['projected_bytes']} (delta {value['delta_bytes']}, {value['delta_percent']}%; {kind})")
    elif value["prepared_projection_bytes"] is not None:
        lines.append(f"  instruction bytes ({value['boundary']}): static {value['static_bytes']}; a "
                     f"{value['prepared_projection_bytes']}-byte projection was prepared but not transmitted; no delta")
    for row in value["omitted"]:
        lines.append(f"  instruction omitted: {row['id']} ({row['because']}; {row['bytes']} bytes) - {row['why']}")
    observed = value["observed_instructions_bytes"]
    line = f"  instruction measurement: {value['measurement']}; observed instructions argument " + (
        f"{observed} bytes" if observed is not None else "not recorded")
    if value["applied"] is False:
        line += f"; consumed but not applied ({value['not_applied_reason']})"
    if value["static_counterfactual_instructions_bytes"] is not None:
        line += f"; static counterfactual {value['static_counterfactual_instructions_bytes']} bytes (not transmitted)"
    lines.append(line)
    digests = value["digests"]
    if digests["source"]:
        lines.append(f"  instruction digests: source {digests['source']} manifest {digests['manifest']} "
                     f"projection {digests['projection']} id {digests['projection_id']}")
    lines.append(f"  instruction note: {value['note']}")
    return lines


def render_explanation(value: Mapping[str, Any]) -> str:
    """Human view built only from the explain_run dict."""
    run = value["run"]
    lines = [f"Run {run['run_id']} ({run.get('dispatcher') or 'dispatcher unknown'})",
             f"  project: {run.get('project') or 'not recorded'}  phase type: {run.get('phase_type') or 'not recorded'}"
             f"  execution mode: {run.get('execution_mode') or 'not recorded'}",
             f"  runtime: {run['runtime_state']['terminal_outcome'] or 'none'} - {run['runtime_state']['note']}",
             "  telemetry: {attempts} attempt(s); {with_observation_event} observation event(s); "
             "{with_context_plan} context plan(s); {with_runner_transmissions} transmission record(s) "
             "- {note}".format(**run["telemetry"])]
    for entry in value["attempts"]:
        lines.append("")
        lines.append(f"Attempt {entry['prefix']}  binding={entry['binding_id']}  id={entry['attempt_id']}")
        lines.append(f"  provider/profile: {entry['provider'] or 'not recorded'} / {entry['profile'] or 'not recorded'}")
        route = entry["route"]
        if route.get("recorded"):
            state = "supported" if route["supported"] else f"unsupported ({route['code']})"
            lines.append(f"  route: {route['seam']} {state}; preflight: {route['preflight'] or 'not run'}")
        else:
            lines.append("  route: not recorded (static request or older run)")
        lines.append(f"  mode: requested {entry['requested_mode']} -> effective {entry['effective_mode']}; "
                     f"reason: {entry['reason']}" + (f" [{entry['diagnostic']}]" if entry["diagnostic"] else ""))
        lines.append(f"  delivery: {entry['delivery'].upper()} - {entry['delivery_note']}")
        for hint in entry["hints"]:
            lines.append(f"  hint: {hint}")
        ignored = entry["task_inputs_ignored"]
        if ignored is not None:
            lines.append(f"  task inputs ignored ({ignored['reason']}): "
                         + ", ".join(ignored["facts"] + ignored["skills"]))
        inputs = entry["inputs"]
        if inputs is not None:
            if not inputs["recorded"]:
                lines.append("  inputs: structured inputs not recorded (older record); planner facts only")
            for fact in inputs["facts"]:
                lines.append(f"  fact: {fact['kind']}={fact['value']}  source={fact['source']}  status={fact['status']}")
            for request in inputs["requests"]:
                lines.append(f"  request: {request['id']}  source={request['source']}  required={request['required']}"
                             f"  applies={request['applies']}")
            manifest = inputs.get("manifest")
            if manifest:
                for row in manifest["files"]:
                    lines.append(f"  manifest: {row['file']} {row['status']}" + (f" ({row['reason']})" if row["reason"] else ""))
        skills = entry["skills"]
        if skills is not None:
            for row in skills["selected"]:
                lines.append(f"  selected: {row['id']} ({row['reason']}; {row['bytes']} bytes)")
            for row in skills["deferred"]:
                lines.append(f"  deferred: {row['id']} ({row['reason']})")
            for row in skills["unavailable"]:
                lines.append(f"  unavailable: {row['id']} ({row['reason']})")
            for fact in skills["unknown_facts"]:
                lines.append(f"  unknown fact (no owning skill): {fact}")
            lines.append(f"  not selected without a positive fact: {skills['not_applicable_count']}; "
                         f"consumer-incompatible: {skills['consumer_incompatible_count']}; "
                         f"acquirable later: {skills['acquirable_count']}"
                         + (f" (acquisition {skills['acquisition_status']})" if skills["acquisition_status"] else ""))
            for row in skills["recovery_files"]:
                lines.append(f"  recovery copy: {row['id']} -> {row['path']} ({row['bytes']} bytes)")
        lines.extend(_render_instructions(entry["instructions"]))
        planned = entry["planned"]
        if planned:
            lines.append(f"  planned (prospective): mandatory {_bytes(planned['mandatory'])}; payload {_bytes(planned['payload'])}")
        transport = entry["runner_transport"]
        lines.append("  runner transport (prepared): " + (f"{transport['bytes']} bytes - {transport['boundary']}"
                                                         if transport else "not recorded"))
        for name in ("runner", "launcher"):
            record = entry["transmitted"][name]
            if record is None:
                lines.append(f"  transmitted ({name}): not recorded")
            else:
                channels = ", ".join(f"{k} {v}" for k, v in sorted(record["bytes_by_channel"].items())) or "none"
                lines.append(f"  transmitted ({name}): coverage {record['coverage']}; bytes by channel: {channels}")
        late = entry["late"]
        kinds = ", ".join(f"{k} {v}" for k, v in late["request_kinds"].items()) or "none"
        lines.append(f"  late acquisition: requests {kinds}; {late['late_controlled_bytes']} late controlled bytes; "
                     f"misses {late['misses']}; rejections {late['rejections']} "
                     f"(plus {late['preparation_events']} preparation and {late['handshake_events']} handshake record(s))")
        lines.append(f"  provider-reported usage: {entry['provider_reported_usage']}")
        outcome = entry["outcome"]
        lines.append(f"  outcome: {outcome['status'] or 'not recorded'} (exit {outcome['exit_code']}) - {outcome['note']}")
        for row in entry["feedback"]:
            lines.append(f"  feedback ({row.get('source')}): {row.get('label')}"
                         + (f" skill={row['skill']}" if row.get("skill") else "") + (f" - {row['note']}" if row.get("note") else ""))
        if entry["diagnostic_references"]:
            lines.append("  records: " + ", ".join(f"{r['name']} ({r['bytes']} bytes)" for r in entry["diagnostic_references"]))
    for row in value["run_feedback"]:
        lines.append(f"Run feedback ({row.get('source')}): {row.get('label')}" + (f" - {row['note']}" if row.get("note") else ""))
    lines.append("")
    lines.extend(f"Note: {note}" for note in value["notes"])
    lines.extend(f"Warning: {warning}" for warning in value["warnings"])
    return "\n".join(lines) + "\n"
