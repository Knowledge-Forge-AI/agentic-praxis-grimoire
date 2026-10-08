"""Optional per-attempt operational observations and a provider-free summary.

One small immutable event is written beside each V1 or V2 provider attempt.
It records identity, route, build, outcome and a reference to the existing
context-plan record; it never copies argv, prompts, settings, transcripts or
environment values. Collection is an optional enhancement: every writer
failure is reduced to a bounded type-name diagnostic and never changes
dispatch. Interrupts are not swallowed.

The reader summarizes selected run directories from existing native records
(state, meta, context plan/deliveries, acquisition events and worker results)
plus these events. It never starts a provider, planner, Go bridge or server.
The optional SQLite index and feedback file are separate, rebuildable local
analytics under ``<APGR_HOME>/state/observations/``; they are never
``dispatcher.sqlite3`` and never execution authority.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from typing import Any, Iterable, Mapping

SCHEMA = "apg.dispatch-observation/v1"
SUMMARY_SCHEMA = "apg.dispatch-observation-summary/v1"
FEEDBACK_SCHEMA = "apg.dispatch-feedback/v1"
INDEX_USER_VERSION = 1
MAX_EVENT_BYTES = 64 * 1024
# V2 already owns "{attempt}.observation.json" for review-drift evidence.
EVENT_SUFFIX = ".dispatch-observation.json"
MAX_RECORD_BYTES = 16 * 1024 * 1024
MAX_WORKER_RESULTS = 256
MAX_WORKER_RESULT_BYTES = 1024 * 1024
MAX_WORKER_PARENTS = 256
MAX_FEEDBACK_LINE_BYTES = 16 * 1024
MAX_RUNS = 200
MAX_WARNINGS = 200
ENVIRONMENT_OPT_OUT = "APGR_DISPATCH_OBSERVATIONS"
FEEDBACK_LABELS = ("helpful", "missing", "misleading")
FEEDBACK_SOURCES = ("operator", "agent", "reviewer")
MAX_NOTE_CHARACTERS = 512
UNAVAILABLE = "unavailable"
_DISABLED_VALUES = {"0", "off", "false", "no", "disabled"}
_LEAF = re.compile(r".+-dispatch--(\d{8}T\d{6}\d*Z)\Z")
V2_RUN = re.compile(r"apgr-run-v2-.+-(\d{8}T\d{6}Z)-[0-9a-f]{8}\Z")


class ObservationError(RuntimeError):
    """A bounded analytics-side error; never raised on the dispatch path."""


# --------------------------------------------------------------------------
# Collection (dispatch path)


def enabled(settings: Mapping[str, Any] | None,
            environment: Mapping[str, str] | None = None) -> bool:
    """Default on; the environment or ``dispatcher.observations.enabled`` opt out."""
    values = os.environ if environment is None else environment
    raw = values.get(ENVIRONMENT_OPT_OUT)
    if raw is not None and raw.strip().lower() in _DISABLED_VALUES:
        return False
    return not (isinstance(settings, Mapping) and settings.get("enabled") is False)


def configured(*, project_root=None, start=None, apgr_home=None) -> bool:
    """Read the opt-out for invocations that do not prepare context.

    A configuration that cannot be read disables only this optional feature;
    essential configuration errors are reported by their normal owners.
    """
    try:
        from .context_config import capture_context_config
        capture = capture_context_config(project_root=project_root, start=start, apgr_home=apgr_home)
    except Exception:
        return False
    return enabled(capture.get("observations"))


def _event_id(run_id: str, prefix: str) -> str:
    return hashlib.sha256("\0".join((SCHEMA, run_id, prefix)).encode("utf-8")).hexdigest()


def _outcome(prepared: Mapping[str, Any], error: BaseException | None) -> dict[str, Any]:
    started, finished = prepared.get("runner_started_monotonic"), prepared.get("runner_finished_monotonic")
    duration = (round(finished - started, 3)
                if isinstance(started, float) and isinstance(finished, float) else None)
    runner_error = prepared.get("runner_error_type")
    if not prepared.get("invoked"):
        status = "not_started"
    elif runner_error is None and prepared.get("runner_returned"):
        status = "runner_returned"
    else:
        status = {
            "ProviderStartFailed": "start_failed",
            "ProviderLivenessExpired": "liveness_expired",
            "ProviderCleanupFailed": "cleanup_failed",
            "ProviderInterrupted": "interrupted",
            "KeyboardInterrupt": "interrupted",
        }.get(runner_error or "", "failed")
    return {"status": status, "exit_code": prepared.get("runner_exit_code"),
            "runner_error_type": runner_error,
            "dispatch_error_type": type(error).__name__ if error is not None else None,
            "duration_seconds": duration,
            "duration_source": "runner_monotonic" if duration is not None else None}


def _context(prepared: Mapping[str, Any]) -> dict[str, Any] | None:
    record = prepared.get("record")
    if isinstance(record, Mapping):
        support = record.get("route_support")
        support = support if isinstance(support, Mapping) else {}
        return {"requested_mode": record.get("requested_mode"),
                "effective_mode": record.get("effective_mode"),
                "reason": record.get("reason"), "planned": record.get("planned"),
                "plan": prepared.get("reference"),
                # Additive (APG166Z-CONTEXT1): ordinary route classification.
                "route_supported": support.get("supported") if support else None,
                "route_code": support.get("code") or support.get("preflight") if support else None,
                "acquisition_attached": isinstance(record.get("acquisition"), Mapping)
                and record.get("effective_mode") == "adaptive",
                # Additive (APG166ZB): prepared instruction projection status only;
                # launcher application is read by explain from launcher deliveries.
                "instruction_projection_prepared_status": (record.get("instruction_projection") or {}).get("status")
                if isinstance(record.get("instruction_projection"), Mapping) else None}
    if prepared.get("reason"):
        # Optional plan persistence failed; the diagnostic sibling remains the evidence.
        return {"requested_mode": prepared.get("requested_mode"),
                "effective_mode": prepared.get("effective_mode"),
                "reason": prepared.get("reason"), "planned": None, "plan": None}
    return None


def build_event(*, dispatcher: str, run_id: str, prefix: str, binding_id: str,
                attempt_id: str, attempt_number: int | None, invocation_kind: str,
                predecessor_attempt_id: str | None, worker_parent_id: str | None,
                task: Mapping[str, Any], route: Mapping[str, Any], build: Mapping[str, Any],
                prepared: Mapping[str, Any], error: BaseException | None,
                artifacts: Mapping[str, str]) -> dict[str, Any]:
    context = _context(prepared)
    return {
        "schema": SCHEMA, "event_id": _event_id(run_id, prefix), "dispatcher": dispatcher,
        "run_id": run_id, "binding_id": binding_id, "attempt_id": attempt_id,
        "attempt_number": attempt_number, "artifact_prefix": prefix,
        "invocation_kind": invocation_kind, "predecessor_attempt_id": predecessor_attempt_id,
        "worker_parent_id": worker_parent_id, "task": dict(task), "route": dict(route),
        # Separately reported provider metadata is not available at this seam.
        "provider_reported": None, "build": dict(build),
        "outcome": _outcome(prepared, error),
        "context": context,
        "context_unavailable_reason": None if context else "context_not_prepared_for_invocation",
        "artifacts": dict(artifacts), "self_report": None, "recorded_by": "dispatcher",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def write_event(run_dir: Path, prefix: str, event: Mapping[str, Any]) -> str:
    """Exclusive-create one event; an existing identical attempt is not a failure."""
    raw = (json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    if len(raw) > MAX_EVENT_BYTES:
        raise ValueError("observation event exceeds bound")
    root = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            fd = os.open(f"{prefix}{EVENT_SUFFIX}",
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
        except FileExistsError:
            return "exists"
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
        return "written"
    finally:
        os.close(root)


def record_attempt(run_dir: Path, prefix: str, *, active: bool, error: BaseException | None,
                   **fields: Any) -> dict[str, Any]:
    """Non-blocking dispatch hook. Returns a bounded disposition, never raises Exception."""
    if not active:
        return {"status": "disabled"}
    try:
        return {"status": write_event(Path(run_dir), prefix,
                                      build_event(prefix=prefix, error=error, **fields))}
    except Exception as failure:  # optional analytics only
        return {"status": "failed", "diagnostic": type(failure).__name__}


def build_identity(state_generation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """APGR version plus controller commit/tree when already known; never probes Git."""
    version = None
    try:
        path = Path(__file__).resolve().parents[2] / "src/agentic_praxis_grimoire/VERSION"
        if path.is_file() and path.stat().st_size < 64:
            version = path.read_text(encoding="utf-8").strip() or None
    except OSError:
        version = None
    generation = state_generation
    if generation is None:
        try:
            import controller_generation
            generation = controller_generation.provenance()
        except Exception:
            generation = None
    generation = generation if isinstance(generation, Mapping) else {}
    return {"apgr_version": version, "controller_commit": generation.get("commit"),
            "controller_tree": generation.get("tree"),
            "controller_safety_established": generation.get("safety_established"),
            "controller_source": generation.get("reason") or (
                "controller_generation" if generation.get("generation_root") else None),
            # Worktree dirt is not measured on the dispatch path.
            "source_dirty": None}


# --------------------------------------------------------------------------
# Reading (analytics path; never on the dispatch path)


def _read_json(path: Path, limit: int, warnings: list[str], label: str) -> Any:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        _warn(warnings, f"{label}: {type(error).__name__}")
        return None
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        _warn(warnings, f"{label}: not a bounded regular file")
        return None
    try:
        return json.loads(path.read_bytes())
    except (OSError, ValueError) as error:
        _warn(warnings, f"{label}: {type(error).__name__}")
        return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _integer(value: Any) -> int | None:
    return value if type(value) is int else None


def _number(value: Any) -> int | float | None:
    return value if type(value) in (int, float) else None


def _warn(warnings: list[str], message: str) -> None:
    if len(warnings) < MAX_WARNINGS:
        warnings.append(message)
    elif len(warnings) == MAX_WARNINGS:
        warnings.append("further warnings omitted")


def _prefixes(names: Iterable[str]) -> list[str]:
    found = set()
    for name in names:
        for suffix in (EVENT_SUFFIX, ".context-plan.json", ".context-failure.json", ".meta.json"):
            if name.endswith(suffix) and not name.startswith("."):
                found.add(name[: -len(suffix)])
    return sorted(found)


def _delivered_components(deliveries: Any) -> tuple[int | None, list[str], str | None]:
    if not isinstance(deliveries, Mapping):
        return None, [], None
    total, skills = 0, []
    seen = False
    for event in _list(deliveries.get("events")):
        if not isinstance(event, Mapping) or event.get("phase") != "initial":
            continue
        if type(event.get("controlled_bytes")) is int:
            total += event["controlled_bytes"]
            seen = True
        for component in _list(event.get("components")):
            if isinstance(component, Mapping) and component.get("kind") == "selected-skill-source-view":
                skills.append(str(component.get("id")))
    return (total if seen else None), skills, _text(deliveries.get("boundary"))


def _real_dirs(path: Path, limit: int, warnings: list[str], label: str) -> list[Path]:
    """Sorted real (non-symlink) child directories among at most ``limit`` scanned entries."""
    names: list[str] = []
    try:
        with os.scandir(path) as entries:
            for number, entry in enumerate(entries):
                if number >= limit:
                    _warn(warnings, f"{label} limit reached; remaining entries omitted")
                    break
                if entry.is_dir(follow_symlinks=False):
                    names.append(entry.name)
    except OSError as error:
        _warn(warnings, f"{label}: {type(error).__name__}")
    return [path / name for name in sorted(names)]


def _worker_rows(run_dir: Path, warnings: list[str], reader=_read_json) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    workers = run_dir / "workers"
    if not workers.is_dir() or workers.is_symlink():
        return rows
    count = 0
    for parent in _real_dirs(workers, MAX_WORKER_PARENTS, warnings, "worker parent"):
        jobs = parent / "jobs"
        if not jobs.is_dir() or jobs.is_symlink():
            continue
        for job in _real_dirs(jobs, MAX_WORKER_RESULTS + 1, warnings, "worker job"):
            result = job / f"{job.name}.result.json"
            count += 1
            if count > MAX_WORKER_RESULTS:
                _warn(warnings, "worker result limit reached; remaining jobs omitted")
                return rows
            value = reader(result, MAX_WORKER_RESULT_BYTES, warnings, f"worker {job.name}")
            if value is not None and not isinstance(value, Mapping):
                _warn(warnings, f"worker {job.name}: result is not an object")
                value = None
            if value is None:
                rows.append({"parent_id": parent.name, "job_id": job.name, "status": UNAVAILABLE,
                             "worker_kind": None, "task_outcome": None, "requested_model": None,
                             "effective_model": None, "effective_model_source": None, "quota": None})
                continue
            effective = _mapping(_mapping(value.get("model_evidence")).get("effective"))
            quota = value.get("quota")
            rows.append({"parent_id": _text(value.get("parent_id")) or parent.name,
                         "job_id": _text(value.get("job_id")) or job.name,
                         "status": _text(value.get("status")), "worker_kind": _text(value.get("worker_kind")),
                         "task_outcome": _text(value.get("task_outcome")),
                         "requested_model": _text(value.get("requested_model")),
                         "effective_model": _text(value.get("effective_model")),
                         "effective_model_source": _text(effective.get("source")),
                         # The worker's own classification; "not exhausted" is not a quota event.
                         "quota": _text(quota.get("classification") or ("exhausted" if quota.get("exhausted") is True else None)
                                        or quota.get("status")) if isinstance(quota, Mapping)
                         else _text(quota)})
    return rows


def _acquisition_rows(run_dir: Path, run_id: str, warnings: list[str]) -> list[dict[str, Any]]:
    if not (run_dir / "acquisitions").is_dir():
        return []
    try:
        from .acquisition_records import records
        diagnostics: list[dict[str, Any]] = []
        rows = records(run_dir, run_id, diagnostics=diagnostics)
    except (OSError, ValueError) as error:
        _warn(warnings, f"acquisitions: {type(error).__name__}")
        return []
    if diagnostics:
        _warn(warnings, f"acquisitions: {len(diagnostics)} malformed event(s) skipped")
    result = []
    for row in rows:
        event = _mapping(row.get("event") if isinstance(row, Mapping) else None)
        requested = event.get("requested")
        result.append({"attempt_id": _text(event.get("attempt_id")), "binding_id": _text(event.get("binding_id")),
                       "kind": _text(event.get("kind")), "phase": _text(event.get("phase")),
                       "controlled_bytes": _integer(event.get("controlled_bytes")),
                       "requested": requested if isinstance(requested, (str, list, Mapping)) else None,
                       "repeat": event.get("is_repeat_delivery") is True,
                       # Additive: separates prelaunch preparation and handshakes.
                       "channel": _text(event.get("channel")), "operation": _text(event.get("diagnostic"))})
    return result


def collect_run(run_dir: Path, *, reader=None, max_attempts: int | None = None) -> dict[str, Any]:
    """Normalize one run into path-free rows; ``reader`` (``_read_json`` signature) may budget reads."""
    run_dir = Path(run_dir)
    warnings: list[str] = []
    read = reader or _read_json
    state = read(run_dir / "state.json", MAX_RECORD_BYTES, warnings, "state.json")
    state = state if isinstance(state, Mapping) else {}
    try:
        names = [entry.name for entry in os.scandir(run_dir)]
    except OSError as error:
        raise ObservationError(f"run directory is not readable: {type(error).__name__}") from error
    routes = state.get("effective_stage_routes") if isinstance(state.get("effective_stage_routes"), Mapping) else {}
    attempts = []
    run_id = state.get("run_id")
    prefixes = _prefixes(names)
    if max_attempts is not None and len(prefixes) > max_attempts:
        _warn(warnings, f"attempt limit reached; {len(prefixes) - max_attempts} attempt(s) omitted")
        prefixes = prefixes[:max_attempts]
    for prefix in prefixes:
        event = read(run_dir / f"{prefix}{EVENT_SUFFIX}", MAX_EVENT_BYTES, warnings, f"{prefix} observation")
        if event is not None and (not isinstance(event, Mapping) or event.get("schema") != SCHEMA):
            _warn(warnings, f"{prefix} observation: unsupported schema")
            event = None
        plan = read(run_dir / f"{prefix}.context-plan.json", MAX_RECORD_BYTES, warnings, f"{prefix} context plan")
        plan = plan if isinstance(plan, Mapping) else None
        failure = read(run_dir / f"{prefix}.context-failure.json", MAX_EVENT_BYTES, warnings, f"{prefix} context failure")
        deliveries = read(run_dir / f"{prefix}.context-deliveries.json", MAX_RECORD_BYTES, warnings, f"{prefix} deliveries")
        meta = read(run_dir / f"{prefix}.meta.json", MAX_RECORD_BYTES, warnings, f"{prefix} meta")
        meta = meta if isinstance(meta, Mapping) else {}
        failure = _mapping(failure)
        ev, pl = _mapping(event), _mapping(plan)
        run_id = _text(run_id) or _text(ev.get("run_id")) or _text(pl.get("run_id"))
        binding = _text(ev.get("binding_id")) or _text(pl.get("binding_id")) or _text(meta.get("stage"))
        route_record = _mapping(routes.get(binding)) if binding is not None else {}
        intelligence = _mapping(route_record.get("intelligence"))
        event_route = _mapping(ev.get("route"))
        outcome = _mapping(ev.get("outcome"))
        build = _mapping(ev.get("build"))
        # Exactly one byte view per attempt: prefer the plan's argv+stdin total;
        # delivery events (stdin only) are a fallback, never added to it.
        delivered_bytes, delivered_skills, delivered_boundary = _delivered_components(deliveries)
        initial_bytes, boundary, bytes_source = None, None, None
        controlled = _mapping(pl.get("controlled_total"))
        if _integer(controlled.get("bytes")) is not None:
            initial_bytes = controlled["bytes"]
            boundary = _text(controlled.get("boundary"))
            bytes_source = "context-plan controlled_total"
        elif delivered_bytes is not None:
            initial_bytes, boundary, bytes_source = delivered_bytes, delivered_boundary, "context-deliveries"
        prospective = _mapping(pl.get("prospective_plan"))
        planned_skills = [str(s.get("qualified_id")) for s in _list(prospective.get("selected_snapshots"))
                          if isinstance(s, Mapping) and s.get("qualified_id")]
        request = _mapping(pl.get("attempted_request"))
        context = _mapping(ev.get("context"))
        support = _mapping(pl.get("route_support"))
        status = _text(outcome.get("status"))
        if status is None and meta:
            status = ("liveness_expired" if meta.get("liveness_expired") else "cleanup_failed" if meta.get("cleanup_failed")
                      else "interrupted" if meta.get("interrupted") else "runner_returned")
        stderr_name = next((n for n in (f"{prefix}.stderr.log", f"{prefix}.stderr.txt") if n in names), None)
        generation = _mapping(state.get("controller_generation"))
        attempts.append({
            "prefix": prefix, "binding_id": binding,
            "attempt_id": _text(ev.get("attempt_id")) or _text(pl.get("attempt_id")),
            "attempt_number": _integer(ev.get("attempt_number")) or _integer(pl.get("attempt_number")),
            "invocation_kind": _text(ev.get("invocation_kind")) or _text(meta.get("invocation_kind")) or ("semantic" if meta else None),
            "predecessor_attempt_id": _text(ev.get("predecessor_attempt_id")),
            "event": event is not None, "dispatcher": _text(ev.get("dispatcher")),
            "provider": _text(event_route.get("provider")) or _text(meta.get("provider")) or _text(route_record.get("provider")),
            "profile": _text(event_route.get("profile")) or _text(meta.get("profile")) or _text(route_record.get("profile")),
            "requested_model": _text(event_route.get("requested_model")) or _text(intelligence.get("model")),
            "requested_effort": _text(event_route.get("requested_effort")) or _text(intelligence.get("effort")),
            "build_commit": _text(build.get("controller_commit")) or _text(generation.get("commit")),
            "apgr_version": _text(build.get("apgr_version")),
            "status": status,
            "exit_code": _integer(outcome["exit_code"]) if "exit_code" in outcome else _integer(meta.get("exit_code")),
            "dispatch_error_type": _text(outcome.get("dispatch_error_type")),
            "duration_seconds": _number(outcome["duration_seconds"]) if "duration_seconds" in outcome
            else _number(meta.get("duration_seconds")),
            "requested_mode": _text(pl.get("requested_mode")) or _text(context.get("requested_mode")) or _text(failure.get("requested_mode")),
            "effective_mode": _text(pl.get("effective_mode")) or _text(context.get("effective_mode")) or _text(failure.get("effective_mode")),
            "reason": _text(pl.get("reason")) or _text(context.get("reason")) or _text(failure.get("reason")),
            "planned": pl.get("planned") if isinstance(pl.get("planned"), bool) else None,
            "route_support": (("supported" if support.get("supported") is True else
                               "unsupported:" + _value(_text(support.get("code")))) if support else None),
            "facts": [f"{f.get('kind')}={f.get('value')}" for f in _list(request.get("facts")) if isinstance(f, Mapping)],
            "planned_skills": planned_skills, "delivered_skills": delivered_skills,
            "content_identity": _text(pl.get("content_identity")),
            "initial_bytes": _integer(initial_bytes),
            "initial_bytes_boundary": boundary, "initial_bytes_source": bytes_source,
            "stderr_available": stderr_name is not None,
        })
    run_id = run_id or run_dir.name
    dispatchers = {a["dispatcher"] for a in attempts if a["dispatcher"]}
    # The resolved leaf distinguishes a V2 projection symlink from nothing:
    # both name the same canonical directory and therefore the same row.
    leaf = run_dir.resolve().name
    return {"run_id": run_id, "leaf": leaf, "run_key": f"{run_id}|{leaf}",
            "dispatcher": "v1" if state.get("run_layout") else (dispatchers.pop() if len(dispatchers) == 1 else UNAVAILABLE),
            "phase_type": _text(state.get("phase_type")), "execution_mode": _text(state.get("execution_mode")),
            "project": _text(state.get("project")),
            "attempts": attempts, "acquisitions": _acquisition_rows(run_dir, run_id, warnings),
            "workers": _worker_rows(run_dir, warnings, read), "warnings": warnings}


def _leaf_order(path: Path) -> str:
    match = _LEAF.fullmatch(path.name)
    return match[1] if match else path.name


def _v2_order(path: Path) -> tuple[str, str]:  # the phase type precedes the timestamp
    match = V2_RUN.fullmatch(path.name)
    return (match[1] if match else "", path.name)


def select_runs(*, run_dirs: Iterable[Path] = (), outbox_root: Path | None = None,
                project: str | None = None, phase: str | None = None,
                apgr_home: Path | None = None, v2_home: bool = False,
                latest: int = 20) -> list[Path]:
    """Bounded explicit selection; scans only the known run-leaf depth."""
    if not 1 <= latest <= MAX_RUNS:
        raise ObservationError(f"--latest must be between 1 and {MAX_RUNS}")
    selected: list[Path] = []
    for path in run_dirs:
        path = Path(path)
        if not path.is_dir():
            raise ObservationError(f"not a run directory: {path.name}")
        selected.append(path)
    if outbox_root is not None:
        if not project:
            raise ObservationError("--outbox-root requires --project")
        project_dir = Path(outbox_root) / project
        phases = [project_dir / phase] if phase else (sorted(p for p in project_dir.iterdir() if p.is_dir()) if project_dir.is_dir() else [])
        leaves = []
        for phase_dir in phases:
            if not phase_dir.is_dir():
                continue
            leaves.extend(p for p in phase_dir.iterdir() if _LEAF.fullmatch(p.name) and p.is_dir())
        selected.extend(sorted(leaves, key=_leaf_order, reverse=True)[:latest])
    if v2_home:
        if apgr_home is None:
            raise ObservationError("V2 selection requires an APGR home")
        runs = Path(apgr_home) / "state" / "runs"
        if runs.is_dir():
            v2 = [p for p in runs.iterdir() if p.is_dir() and not p.is_symlink()]
            selected.extend(sorted(v2, key=_v2_order, reverse=True)[:latest])
    unique: dict[Path, Path] = {}
    for path in selected:
        unique.setdefault(path.resolve(), path)
    if len(unique) > MAX_RUNS:
        raise ObservationError(f"selection exceeds {MAX_RUNS} runs")
    return list(unique.values())


def _stats(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "sum": None, "min": None, "median": None, "max": None}
    ordered = sorted(values)
    middle = len(ordered) // 2
    median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return {"n": len(ordered), "sum": sum(ordered), "min": ordered[0], "median": median, "max": ordered[-1]}


def _value(value: Any) -> str:
    return UNAVAILABLE if value is None or value == "" else str(value)


def summarize(runs: list[Mapping[str, Any]], feedback: list[Mapping[str, Any]] = ()) -> dict[str, Any]:
    attempts = [dict(a, run_id=r["run_id"]) for r in runs for a in r["attempts"]]
    total = len(attempts)
    warnings = [f"{r['leaf']}: {w}" for r in runs for w in r.get("warnings", [])]
    without_event = [a for a in attempts if not a["event"]]
    if without_event:
        warnings.append(f"{len(without_event)}/{total} attempts have no observation event; "
                        "fields were reconstructed from native records where present")
    for field in ("requested_mode", "provider", "status", "build_commit", "initial_bytes"):
        missing = sum(1 for a in attempts if a.get(field) is None)
        if missing:
            warnings.append(f"{field} unavailable for {missing}/{total} attempts")
    modes = Counter(f"{_value(a['requested_mode'])} -> {_value(a['effective_mode'])}" for a in attempts)
    reasons: Counter[str] = Counter()
    for a in attempts:
        for reason in (a.get("reason") or UNAVAILABLE).split(","):
            reasons[reason.strip() or UNAVAILABLE] += 1
    planned = Counter(s for a in attempts for s in a["planned_skills"])
    delivered = Counter(s for a in attempts for s in a["delivered_skills"])
    facts = Counter(f for a in attempts for f in a["facts"])
    boundaries = Counter(f"{_value(a['initial_bytes_source'])}: {_value(a['initial_bytes_boundary'])}"
                         for a in attempts if a["initial_bytes"] is not None)
    acquisitions = [dict(row, run_id=r["run_id"]) for r in runs for row in r["acquisitions"]]
    late = [row["controlled_bytes"] for row in acquisitions
            if row.get("phase") == "late" and row.get("controlled_bytes") is not None
            and row["kind"] in ("channel_delivered", "response_delivered", "recovery_read_observed")]
    misses = Counter(_value(row.get("requested")) for row in acquisitions if row["kind"] in ("search_miss", "rejected"))
    statuses = Counter(_value(a["status"]) for a in attempts)
    failures = Counter(
        f"{_value(a['binding_id'])} | {_value(a['provider'])} | {_value((a['build_commit'] or '')[:12] or None)} | {_value(a['status'])}"
        # Unknown status (legacy or in-flight) is a coverage gap, not a failure.
        for a in attempts
        if (a["status"] is not None and a["status"] != "runner_returned")
        or a["exit_code"] not in (0, None) or a.get("dispatch_error_type"))
    workers = [w for r in runs for w in r["workers"]]
    feedback_rows = list(feedback)
    return {
        "schema": SUMMARY_SCHEMA,
        "selection": {"runs": len(runs), "attempts": total,
                      "dispatchers": dict(Counter(_value(r["dispatcher"]) for r in runs)),
                      "attempts_with_event": total - len(without_event)},
        "context": {"requested_to_effective": dict(modes), "reasons": dict(reasons),
                    "delivery": dict(Counter(
                        "adaptive" if a.get("effective_mode") == "adaptive" else
                        ("static_with_shadow_plan" if a.get("planned") else "static_fallback")
                        if a.get("requested_mode") == "adaptive" else _value(a.get("requested_mode"))
                        for a in attempts)),
                    "route_support": dict(Counter(_value(a.get("route_support")) for a in attempts)),
                    "planned_attempts": sum(1 for a in attempts if a["planned"]),
                    "planner_facts": dict(facts),
                    "denominator": total},
        "skills": {"planned_not_delivered_note": "planned skills are prospective; only attempts whose effective mode "
                                                 "is adaptive (supported route) placed selected skills on the runner transport",
                   "planned": dict(planned), "delivered": dict(delivered),
                   "content_identities": len({a["content_identity"] for a in attempts if a["content_identity"]})},
        "bytes": {"initial_by_boundary": {
                      boundary: _stats([a["initial_bytes"] for a in attempts if a["initial_bytes"] is not None
                                        and f"{_value(a['initial_bytes_source'])}: {_value(a['initial_bytes_boundary'])}" == boundary])
                      for boundary in boundaries},
                  "initial_attempts_without_bytes": sum(1 for a in attempts if a["initial_bytes"] is None),
                  "late": _stats(late),
                  "note": "one byte view per attempt; overlapping views are not added"},
        "acquisition": {"events": len(acquisitions), "kinds": dict(Counter(_value(r["kind"]) for r in acquisitions)),
                        "misses": dict(misses), "repeat_deliveries": sum(1 for r in acquisitions if r["repeat"])},
        "outcomes": {"status": dict(statuses), "failures_by_stage_provider_build_status": dict(failures),
                     "stderr_available": sum(1 for a in attempts if a["stderr_available"])},
        "routes": dict(Counter(f"{_value(a['provider'])}/{_value(a['profile'])} model={_value(a['requested_model'])} effort={_value(a['requested_effort'])}"
                               for a in attempts)),
        "workers": {"jobs": len(workers),
                    "by_kind_status": dict(Counter(f"{_value(w['worker_kind'])}:{_value(w['status'])}" for w in workers)),
                    "task_outcomes": dict(Counter(_value(w["task_outcome"]) for w in workers)),
                    "model_requested_vs_effective": dict(Counter(
                        f"{_value(w['requested_model'])} -> {_value(w['effective_model'])} (source={_value(w['effective_model_source'])})"
                        for w in workers)),
                    "quota": dict(Counter(_value(w["quota"]) for w in workers if w["quota"] is not None))},
        "feedback": {"rows": len(feedback_rows),
                     "by_label_source": dict(Counter(f"{f['label']} ({f['source']})" for f in feedback_rows)),
                     "by_skill": dict(Counter(f"{f.get('skill') or UNAVAILABLE}: {f['label']}" for f in feedback_rows)),
                     "note": "feedback is attributed by source and is not machine observation"},
        "warnings": warnings,
        "claims": "raw counts only; no savings, benefit or maturity score is computed",
    }


def render_text(summary: Mapping[str, Any]) -> str:
    lines = ["APGR dispatch observations (" + summary["claims"] + ")"]

    def section(title: str, mapping: Mapping[str, Any], denominator: int | None = None) -> None:
        lines.append("")
        lines.append(title)
        if not mapping:
            lines.append("  (none)")
        for key, value in sorted(mapping.items(), key=lambda item: (-item[1] if isinstance(item[1], int) else 0, str(item[0]))):
            lines.append(f"  {key}: {value}" + (f"/{denominator}" if denominator else ""))

    s = summary["selection"]
    lines.append(f"runs={s['runs']} attempts={s['attempts']} attempts_with_event={s['attempts_with_event']} dispatchers={s['dispatchers']}")
    section("Requested -> effective context mode", summary["context"]["requested_to_effective"], summary["context"]["denominator"])
    section("Context reasons / fallback", summary["context"]["reasons"], summary["context"]["denominator"])
    section("Context delivery (adaptive = selected skills on runner transport)",
            summary["context"].get("delivery", {}), summary["context"]["denominator"])
    section("Ordinary route support", summary["context"].get("route_support", {}), summary["context"]["denominator"])
    section("Planner facts supplied", summary["context"]["planner_facts"])
    section("Skills planned (prospective)", summary["skills"]["planned"])
    section("Skills delivered", summary["skills"]["delivered"])
    lines.append("")
    lines.append("Controlled initial bytes (per measured boundary; views are never summed)")
    for boundary, stats in sorted(summary["bytes"]["initial_by_boundary"].items()):
        lines.append(f"  [{boundary}] " + ", ".join(f"{k}={_value(v)}" for k, v in stats.items()))
    lines.append(f"  attempts without a byte record: {summary['bytes']['initial_attempts_without_bytes']}")
    lines.append("Controlled late bytes (acquisition deliveries): "
                 + ", ".join(f"{k}={_value(v)}" for k, v in summary["bytes"]["late"].items()))
    section("Acquisition event kinds", summary["acquisition"]["kinds"])
    section("Acquisition misses (requested id)", summary["acquisition"]["misses"])
    section("Attempt status", summary["outcomes"]["status"], summary["selection"]["attempts"])
    section("Failures (stage | provider | build | status)", summary["outcomes"]["failures_by_stage_provider_build_status"])
    section("Routes (requested)", summary["routes"])
    section("Worker jobs (kind:status)", summary["workers"]["by_kind_status"])
    section("Worker model requested -> effective", summary["workers"]["model_requested_vs_effective"])
    section("Worker quota observations", summary["workers"]["quota"])
    section("Feedback (label/source; attributed, not machine-observed)", summary["feedback"]["by_label_source"])
    section("Feedback by skill", summary["feedback"]["by_skill"])
    lines.append("")
    lines.append("Coverage and missing-data warnings")
    lines.extend(f"  - {w}" for w in summary["warnings"]) if summary["warnings"] else lines.append("  (none)")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Optional analytics storage


def storage_root(apgr_home: Path) -> Path:
    return Path(apgr_home) / "state" / "observations"


def append_feedback(path: Path, *, run_id: str, label: str, source: str,
                    attempt_id: str | None = None, skill: str | None = None,
                    note: str | None = None) -> dict[str, Any]:
    if label not in FEEDBACK_LABELS:
        raise ObservationError(f"label must be one of {', '.join(FEEDBACK_LABELS)}")
    if source not in FEEDBACK_SOURCES:
        raise ObservationError(f"source must be one of {', '.join(FEEDBACK_SOURCES)}")
    if not run_id:
        raise ObservationError("run id is required")
    if note is not None and len(note) > MAX_NOTE_CHARACTERS:
        raise ObservationError(f"note exceeds {MAX_NOTE_CHARACTERS} characters")
    record = {"schema": FEEDBACK_SCHEMA,
              "feedback_id": hashlib.sha256(os.urandom(16)).hexdigest()[:32],
              "run_id": run_id, "attempt_id": attempt_id, "label": label, "skill": skill,
              "source": source, "note": note,
              "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    from .scanner import append_row
    append_row(Path(path), record)
    return record


def read_feedback(path: Path, run_ids: set[str] | None, warnings: list[str]) -> list[dict[str, Any]]:
    path = Path(path)
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            _warn(warnings, "feedback: not a regular file")
            return []
    except OSError:
        return []
    rows = []
    try:
        with path.open("rb") as stream:
            for number, line in enumerate(iter(lambda: stream.readline(MAX_FEEDBACK_LINE_BYTES + 1), b""), 1):
                if number > 100_000 or len(line) > MAX_FEEDBACK_LINE_BYTES:
                    _warn(warnings, f"feedback: row or {MAX_FEEDBACK_LINE_BYTES}-byte line limit reached at line {number}")
                    break
                try:
                    row = json.loads(line)
                    if row.get("schema") != FEEDBACK_SCHEMA or row.get("label") not in FEEDBACK_LABELS \
                            or row.get("source") not in FEEDBACK_SOURCES:
                        raise ValueError("unsupported feedback row")
                except (ValueError, AttributeError):
                    _warn(warnings, f"feedback line {number}: malformed row skipped")
                    continue
                if run_ids is None or row.get("run_id") in run_ids:
                    rows.append(row)
    except OSError as error:
        _warn(warnings, f"feedback: {type(error).__name__}")
    return rows


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(os.fspath(path), timeout=2.0)
    connection.execute("PRAGMA busy_timeout = 2000")
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if version == 0 and not tables:
        connection.execute("CREATE TABLE runs (run_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, row_sha256 TEXT NOT NULL, row_json TEXT NOT NULL, imported_at TEXT NOT NULL)")
        connection.execute(f"PRAGMA user_version = {INDEX_USER_VERSION}")
        return
    if version != INDEX_USER_VERSION or "runs" not in tables:
        raise ObservationError("observation index is incompatible; rerun with --rebuild")


def import_runs(index_path: Path, runs: list[Mapping[str, Any]], *, rebuild: bool = False) -> dict[str, int]:
    """Idempotent keyed import; rebuild writes a fresh file and replaces atomically."""
    index_path = Path(index_path)
    index_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = index_path.with_name(f".{index_path.name}.rebuild-{os.getpid()}") if rebuild else index_path
    if rebuild and target.exists():
        target.unlink()
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    try:
        connection = _connect(target)
        try:
            with connection:
                _ensure_schema(connection)
                for run in runs:
                    raw = json.dumps(run, sort_keys=True, ensure_ascii=False)
                    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                    previous = connection.execute("SELECT row_sha256 FROM runs WHERE run_key = ?", (run["run_key"],)).fetchone()
                    if previous is not None and previous[0] == digest:
                        counts["unchanged"] += 1
                        continue
                    connection.execute(
                        "INSERT INTO runs (run_key, run_id, row_sha256, row_json, imported_at) VALUES (?, ?, ?, ?, ?) "
                        "ON CONFLICT(run_key) DO UPDATE SET row_sha256=excluded.row_sha256, row_json=excluded.row_json, imported_at=excluded.imported_at",
                        (run["run_key"], run["run_id"], digest, raw, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
                    counts["updated" if previous is not None else "inserted"] += 1
        finally:
            connection.close()
        os.chmod(target, 0o600)
        if rebuild:
            os.replace(target, index_path)
    except sqlite3.Error as error:
        if rebuild:
            try:
                target.unlink()
            except OSError:
                pass
        raise ObservationError(f"observation index unavailable: {type(error).__name__}: {error}") from error
    return counts


def runs_from_index(index_path: Path, run_ids: set[str] | None = None) -> list[dict[str, Any]]:
    if not Path(index_path).is_file():
        raise ObservationError("observation index does not exist; run the index command first")
    try:
        connection = _connect(Path(index_path))
        try:
            _ensure_schema(connection)
            rows = connection.execute("SELECT run_id, row_json FROM runs ORDER BY run_key").fetchall()
        finally:
            connection.close()
    except sqlite3.Error as error:
        raise ObservationError(f"observation index unavailable: {type(error).__name__}: {error}") from error
    return [json.loads(raw) for run_id, raw in rows if run_ids is None or run_id in run_ids]
