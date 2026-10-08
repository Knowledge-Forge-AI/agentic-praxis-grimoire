"""Per-attempt optional planning and immutable observations at the runner seam.

Default static is independent of the Go bridge, catalog, source roots and workers.
Only this optional preparation boundary catches planning failures. Provider and
configuration failures retain their original semantics.
"""
from __future__ import annotations

import hashlib
import json
from contextvars import ContextVar
from pathlib import Path
from typing import Protocol

MAX_PLAN_BYTES = 16 * 1024 * 1024
ACTIVE_TRANSPORT = ContextVar("apgr_transport", default=None)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def measured(data):
    try:
        characters = len(data.decode("utf-8"))
    except UnicodeDecodeError:
        characters = None
    return {"bytes": len(data), "characters": characters, "sha256": hashlib.sha256(data).hexdigest()}


class ProjectionAdapter(Protocol):
    """Caller-owned qualified seam; F supplies no live implementation."""
    def qualification(self) -> dict: ...
    def project(self, plan: dict, argv: list[str], prompt: bytes) -> tuple[list[str], bytes]: ...


def _write_new(path, value):
    raw = canonical(value)
    if len(raw) > MAX_PLAN_BYTES:
        raise ValueError("context artifact exceeds bound")
    with path.open("xb") as stream:
        stream.write(raw)
    return {"schema": "apg.context-reference/v1", "path": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def native_plan(request, capture):
    # Import only in the elected adaptive branch. Missing binary/package is an
    # optional planning failure, never a static startup prerequisite.
    import importlib.util
    import sys
    # Bind the maintained sibling explicitly; never borrow an ambient package
    # and never alter sys.path in a native/frozen controller.
    source = Path(__file__).resolve().parents[2] / "src/agentic_praxis_grimoire/go_bridge.py"
    name = "_apgr_context_bridge_" + hashlib.sha256(str(source).encode()).hexdigest()
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError("maintained Go bridge unavailable")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    run_capture = module.run_capture
    args = ["skills", "plan", "--stdin", "--apgr-home", capture["apgr_home"]]
    if capture["project_root"]:
        args.extend(["--project-root", capture["project_root"]])
    result = run_capture(args, repository_root=None, input_bytes=canonical(request))
    if result.returncode:
        raise ValueError("native context planner failed")
    if len(result.stdout) > MAX_PLAN_BYTES:
        raise ValueError("native context plan exceeds bound")
    return json.loads(result.stdout)


def _planning_request(record, capture, consumer, argv, prompt, facts, qualification, requests=()):
    settings = capture["settings"]
    run_id, binding_id, attempt_id, roles = (record[k] for k in ("run_id", "binding_id", "attempt_id", "roles"))
    request = {"schema_version": "apg.context-plan/v1", "run_id": run_id,
               "binding_id": binding_id, "attempt_id": attempt_id, "roles": list(roles),
               "consumer": consumer if consumer in ("claude", "codex", "chatgpt") else "go_library",
               "requested_mode": "adaptive", "catalog": {"schema_version": "apg.skill-catalog/v1", "overrides": capture["overrides"]},
               "facts": list(facts), "requests": list(requests), "mandatory": [{"id": "runner-stdin", "kind": "task-and-role-envelope", "text": prompt.decode("utf-8"), "source_sha256": hashlib.sha256(prompt).hexdigest()}],
               "budget": {k: settings[k] for k in ("max_initial_context_bytes", "max_initial_context_characters") if k in settings},
               "qualification": qualification}
    # Reserve the exact serializable argv overhead before packing stdin.
    # These are disjoint transport portions, not two views of one body.
    argv_cost = measured(canonical(argv))
    for key, dimension in (("max_initial_context_bytes", "bytes"), ("max_initial_context_characters", "characters")):
        if key in request["budget"]:
            request["budget"][key] = max(0, request["budget"][key] - argv_cost[dimension])
    record["stdin_budget_after_argv"] = dict(request["budget"])
    return request


def _record_transport(record, argv, prompt):
    argv_cost, stdin_cost = measured(canonical(argv)), measured(prompt)
    record["transport"] = {"argv": argv, "argv_json": argv_cost, "stdin": stdin_cost,
                           "native_discovery_count": None,
                           "delivered_body_count": None}
    record["controlled_total"] = {"bytes": argv_cost["bytes"] + stdin_cost["bytes"],
                                  "characters": (argv_cost["characters"] + stdin_cost["characters"]
                                                 if stdin_cost["characters"] is not None else None),
                                  "boundary": "canonical argv JSON plus runner stdin"}


def _transport_overflow(settings, cost):
    return any(settings.get(key) is not None and (cost[dimension] is None or cost[dimension] > settings[key])
               for key, dimension in (("max_initial_context_bytes", "bytes"),
                                      ("max_initial_context_characters", "characters")))


def _fallback_reason(error, default):
    """Typed prelaunch fallbacks keep a stable reason; anything else is generic."""
    reason = getattr(error, "fallback_reason", None)
    return reason if isinstance(reason, str) and reason else default


def _mark_unused_acquisition(record):
    if isinstance(record.get("acquisition"), dict):
        record["acquisition"]["status"] = "not_used_static_fallback"
    view = record.get("instruction_projection")
    if isinstance(view, dict) and view.get("status") == "projected":
        view["status"] = "not_used_static_fallback"


INSTRUCTION_SCHEMA = "apg.claude-instruction-projection/v1"
INSTRUCTION_OPTION = "--apgr-instruction-projection"


def _prepare_instructions(record, projection, run_dir, prefix, argv, settings):
    """Optional standing-instruction projection; its failure never changes the skill plan."""
    inputs = getattr(projection, "instructions", None)
    if inputs is None:
        return argv
    if settings.get("instructions", "projected") == "static":
        record["instruction_projection"] = {"schema": INSTRUCTION_SCHEMA, "status": "disabled",
                                            "reason": "instructions_static_configured", "diagnostic": None}
        return argv
    try:
        handoff, record["instruction_projection"] = inputs.prepare(record, run_dir, prefix)
    except Exception as error:
        code = getattr(error, "code", None)
        record["instruction_projection"] = {"schema": INSTRUCTION_SCHEMA, "status": "static_fallback",
                                            "reason": code if isinstance(code, str) and code else "instruction_projection_failed",
                                            "diagnostic": f"{type(error).__name__}: {error}"[:300]}
        return argv
    return [*argv, INSTRUCTION_OPTION, str(handoff)]


def _drop_instructions(record, argv):
    """Release only the instruction projection when its option alone overflows."""
    view = record.get("instruction_projection")
    if not (isinstance(view, dict) and view.get("status") == "projected" and INSTRUCTION_OPTION in argv):
        return argv
    index = argv.index(INSTRUCTION_OPTION)
    view.update(status="static_fallback", reason="transport_overhead_overflow")
    return [*argv[:index], *argv[index + 2:]]


def prepare(*, capture, run_dir, prefix, run_id, binding_id, attempt_id, roles,
            consumer, argv, prompt, planner=None, projection=None, facts=(), instruction_records=(), attempt_number=1,
            postures=None, work_tree=None, route=None):
    """Prepare one attempt. ``route`` and ``postures`` are consulted only when adaptive.

    ``route`` is a zero-argument callable returning ``(projection | None, support)``
    for the shared ordinary seam; ``postures`` enables structured config, task and
    manifest inputs (``context_inputs``). Static never evaluates either.
    """
    settings = capture["settings"]
    record = {"schema": "apg.invocation-context/v1", "run_id": run_id,
              "binding_id": binding_id, "attempt_id": attempt_id, "attempt_number": attempt_number, "roles": sorted(set(roles)),
              "requested_mode": settings["mode"], "effective_mode": "static",
              "reason": "static_requested", "configuration": capture["provenance"],
              "planned": False, "materialized": False, "model_observed": None,
              "provider_native_overhead": None, "tokens": None, "catalog_fingerprint": None,
              "rule_version": None, "content_identity": None}
    prospective = None
    attempted_request = None
    elected_argv, elected_prompt = list(argv), prompt
    if settings["mode"] == "adaptive":
        try:
            support = None
            if route is not None and projection is None:
                projection, support = route()
                record["route_support"] = support
            requests = []
            planner_facts = list(facts)
            if postures is not None:
                from .context_inputs import resolve
                extra, requests, record["inputs"] = resolve(capture, postures=postures, work_tree=work_tree)
                planner_facts.extend(extra)
            qualification = projection.qualification() if projection else {
                "selective_projection": False, "independent_recovery": False, "evidence": ""}
            request = _planning_request(record, capture, consumer, argv, prompt, planner_facts, qualification, requests)
            attempted_request = request
            prospective = (planner or native_plan)(request, capture)
            record["planned"] = True
            for key in ("catalog_fingerprint", "rule_version", "content_identity"):
                record[key] = prospective.get(key)
            record["reason"] = ",".join(prospective["reasons"]) or "qualified_projection"
            if prospective["effective_mode"] == "adaptive" and projection is None:
                record["reason"] = "projection_adapter_unavailable"
            if support is not None and not support.get("supported"):
                record["reason"] = "route_unsupported:" + str(support.get("code"))
            elif support is not None and support.get("preflight") not in (None, "available"):
                record["reason"] = str(support["preflight"])
            if prospective["effective_mode"] == "adaptive" and projection is not None:
                if not (qualification.get("selective_projection") is True
                        and qualification.get("independent_recovery") is True
                        and qualification.get("evidence")):
                    raise ValueError("projection and recovery must both be qualified")
                elected_argv, elected_prompt = projection.project(prospective, list(argv), prompt)
                # Permissions and mandatory payload may not be changed by projection.
                if elected_argv != argv or not elected_prompt.startswith(prompt):
                    raise ValueError("projection changed static transport authority")
                if elected_prompt.decode("utf-8") != prospective["payload"]:
                    raise ValueError("projection differs from planned payload")
                record["effective_mode"] = "adaptive"
                elected_argv = _prepare_instructions(record, projection, run_dir, prefix, elected_argv, settings)
                acquisition = getattr(projection, "acquisition", None)
                if acquisition is not None:
                    elected_argv, record["acquisition"] = acquisition.prepare(record, run_dir, elected_argv)
                    if hasattr(acquisition, "notice"):
                        recovery_notice = acquisition.notice(record)
                    else:
                        recovery_notice = "\nAPGR late acquisition recovery: if MCP fails, preserve this attempt and use the already-authorized native read tool on these exact run snapshots. Do not replay the turn or gain shell authority.\n"
                        recovery_notice += "\n".join(str(Path(run_dir) / row["path"]) for row in record["acquisition"]["recovery"]) + "\n"
                    elected_prompt += recovery_notice.encode("utf-8")
        except Exception as error:
            elected_argv, elected_prompt = list(argv), prompt
            _mark_unused_acquisition(record)
            record.update(effective_mode="static", reason=_fallback_reason(error, "optional_plan_failed"),
                          diagnostic=type(error).__name__)
    elif postures is not None:
        # Static never plans; make ignored dispatch-command inputs visible instead of silent.
        from .context_inputs import TASK_INPUTS
        task = TASK_INPUTS.get()
        if task:
            record["task_inputs_ignored"] = {
                "reason": "static_mode",
                "facts": [f"{kind}={value}" for kind, value in task.get("facts", [])],
                "skills": [r["id"] for r in task.get("skills", [])]}
    # Capture the actual adapter-controlled transport. Native discovery and
    # downstream launcher additions are outside this measured boundary.
    _record_transport(record, elected_argv, elected_prompt)
    if record["effective_mode"] == "adaptive" and _transport_overflow(settings, record["controlled_total"]):
        elected_argv = _drop_instructions(record, elected_argv)
        _record_transport(record, elected_argv, elected_prompt)
    if record["effective_mode"] == "adaptive" and _transport_overflow(settings, record["controlled_total"]):
        _mark_unused_acquisition(record)
        record.update(effective_mode="static", reason="transport_overhead_overflow")
        elected_argv, elected_prompt = list(argv), prompt
        _record_transport(record, elected_argv, elected_prompt)
    record["instruction_plan"] = {"schema": "apg.instruction-plan/v1", "components": list(instruction_records), "runner_stdin": measured(elected_prompt), "model_observed": None}
    record["attempted_request"] = attempted_request
    record["prospective_plan"] = prospective
    if settings["mode"] == "adaptive" and "instruction_projection" not in record:
        record["instruction_projection"] = {
            "schema": INSTRUCTION_SCHEMA, "status": "not_applicable", "diagnostic": None,
            "reason": "attempt_not_adaptive" if record["effective_mode"] != "adaptive" else "route_without_instruction_projection"}
    if record["effective_mode"] == "adaptive" and record.get("acquisition"):
        try:
            projection.acquisition.finalize(record)
        except Exception as error:
            # Includes subprocess timeouts from the final probe: never fail the stage.
            _mark_unused_acquisition(record)
            record.update(effective_mode="static", reason=_fallback_reason(error, "acquisition_config_failed"),
                          diagnostic=type(error).__name__)
            elected_argv, elected_prompt = list(argv), prompt
            _record_transport(record, elected_argv, elected_prompt)
            record["instruction_plan"]["runner_stdin"] = measured(elected_prompt)
    path = Path(run_dir) / f"{prefix}.context-plan.json"
    try:
        reference = _write_new(path, record)
    except (OSError, ValueError) as error:
        # A failed optional write does not replace essential run evidence rules.
        diagnostic = {"schema": "apg.context-diagnostic/v1", "attempt_id": attempt_id,
                      "requested_mode": settings["mode"], "effective_mode": "static",
                      "reason": "plan_persistence_failed", "diagnostic": type(error).__name__}
        try:
            _write_new(path.with_name(f"{prefix}.context-failure.json"), diagnostic)
        except (OSError, ValueError):
            pass
        return list(argv), prompt, {"record": None, "reference": None, **diagnostic}
    return elected_argv, elected_prompt, {"record": record, "reference": reference, "path": path}


def observe(prepared, *, status, exit_code=None):
    if not prepared.get("reference"):
        return None
    observation = {"schema": "apg.context-transport/v1", "plan": prepared["reference"],
                   "attempt_id": prepared["record"]["attempt_id"], "status": status,
                   "exit_code": exit_code, "transport_delivered": False if status in ("start_failed", "not_started") else None, "model_observed": None,
                   "reason": "runner completion does not attest provider consumption"}
    try:
        return _write_new(prepared["path"].with_name(prepared["path"].name.replace(".context-plan.json", ".context-transport.json")), observation)
    except (OSError, ValueError):
        return None


def invoke(prepared, runner, *args, **kwargs):
    """Observe the real runner once; never replay or swallow its exceptions."""
    from .provider import ProviderStartFailed
    from .transmission import Transport
    import time
    transport = Transport(prepared) if prepared.get("reference") else None
    token = ACTIVE_TRANSPORT.set(transport)
    prepared["invoked"] = True
    # In-memory runner timing/outcome for the optional attempt observation.
    prepared["runner_started_monotonic"] = time.monotonic()
    try:
        result = runner(*args, **kwargs)
    except BaseException as error:
        prepared["runner_error_type"] = type(error).__name__
        observe(prepared, status="start_failed" if isinstance(error, ProviderStartFailed) else "partial_or_unknown")
        raise
    finally:
        prepared["runner_finished_monotonic"] = time.monotonic()
        ACTIVE_TRANSPORT.reset(token)
        if transport is not None:
            transport.finish()
        if prepared.get("acquisition_index_conn") is not None and prepared.get("path"):
            from .acquisition_records import observe_index
            observe_index(prepared["acquisition_index_conn"], prepared["path"].parent, prepared["record"]["run_id"])
    code = getattr(result, "exit_code", None)
    if code is None and isinstance(result, tuple) and result:
        code = result[0]
    prepared["runner_returned"] = True
    prepared["runner_exit_code"] = code if type(code) is int else None
    observe(prepared, status="runner_returned", exit_code=code)
    return result


def index_reference(prepared, conn, run_id, attempt_id):
    reference = prepared.get("reference")
    if not reference:
        return
    if prepared.get("record", {}).get("requested_mode") == "adaptive":
        prepared["acquisition_index_conn"] = conn
    try:
        from .persistence import record_artifact
        record_artifact(conn, artifact_id=attempt_id+":context-plan", run_id=run_id,
                        artifact_name="context-plan", relative_path=reference["path"],
                        size_bytes=reference["bytes"], sha256=reference["sha256"],
                        content_type="application/json")
    except Exception as error:
        try:
            _write_new(prepared["path"].with_suffix(".index-failure.json"),
                       {"schema": "apg.context-index-diagnostic/v1", "plan": reference,
                        "diagnostic": type(error).__name__})
        except (OSError, ValueError):
            pass


def retained_records(source, prefix, stage):
    """Read only fixed historical siblings; never resolve today's catalog."""
    import stat
    state_path = Path(source) / "state.json"
    state = json.loads(state_path.read_bytes()) if state_path.is_file() else {}
    references = {r["path"]: r for r in state.get("context_plans", [])}
    records = []
    for attempt_prefix in (prefix, prefix + ".review-retry"):
        for suffix in ("context-plan.json", "context-transport.json", "context-deliveries.json", "context-launcher-deliveries.json", "context-failure.json", "context-plan.index-failure.json"):
            path = Path(source) / f"{attempt_prefix}.{suffix}"
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_PLAN_BYTES:
                raise ValueError("invalid retained context artifact")
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            reference = references.get(path.name)
            if reference is not None and (reference.get("sha256") != digest or reference.get("bytes") != len(data)):
                raise ValueError("retained context reference differs from artifact")
            records.append({"stage": stage, "name": path.name, "sha256": digest})
    if state.get("run_id") and (Path(source) / "acquisitions").exists():
        from .acquisition_records import records as acquisition_records
        diagnostics = []
        try:
            acquisition_rows = acquisition_records(source, state["run_id"], diagnostics=diagnostics)
        except (OSError, ValueError) as error:
            acquisition_rows = []
            diagnostics.append({"path": "acquisitions", "diagnostic": type(error).__name__})
        if diagnostics:
            import warnings
            warnings.warn("optional acquisition records unavailable: " + str(len(diagnostics)), RuntimeWarning)
        for row in acquisition_rows:
            if row["event"]["binding_id"] == stage:
                records.append({"stage": stage, "name": row["path"], "sha256": row["sha256"]})
    return records
