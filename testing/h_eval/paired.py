"""Repository-owned pair execution interface; APG166A uses instrumented actors.

Route selection, selective projection and native read authority belong to the
caller. This module never qualifies a provider or chooses an adaptive default.
Existing attempts are inspectable, never automatically replayed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from agent_phase import context_adapter, provider
from agent_phase.acquisition_records import delivery_entries, records
from agent_phase.transmission import direct_bytes

from .evaluate import delivered_totals, encoded, load

SCHEMA = "apg.h-pair-mechanism/v1"


def _write(path, value):
    _write_bytes(path, encoded(value))


def _write_bytes(path, data):
    if path.parent.resolve() != path.parent:
        raise ValueError("unsafe pair artifact parent")
    root = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(root)
    finally:
        os.close(root)


def _snapshot(root):
    result = {}
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("subject symlink refused")
        if path.is_dir():
            continue
        data = direct_bytes(path, utf8=False, max_bytes=128 << 20)
        total += len(data)
        if len(result) >= 20000 or total > 128 << 20:
            raise ValueError("subject snapshot exceeds bound")
        result[str(path.relative_to(root))] = hashlib.sha256(data).hexdigest()
    return result


def import_oracle(value, expected):
    """Exact external task-oracle receipt shape; provider self-report is separate."""
    if (not isinstance(value, dict) or set(value) != {"schema", "oracle", "status", "evidence"}
            or value["schema"] != "apg.h-task-oracle/v1" or value["oracle"] != expected
            or value["status"] not in ("pass", "fail", "unavailable")
            or not isinstance(value["evidence"], list) or not value["evidence"]):
        raise ValueError("invalid task oracle receipt")
    for evidence in value["evidence"]:
        if (not isinstance(evidence, dict) or set(evidence) != {"kind", "sha256", "bytes"}
                or not isinstance(evidence["kind"], str) or not evidence["kind"]
                or type(evidence["bytes"]) is not int or evidence["bytes"] < 0
                or not isinstance(evidence["sha256"], str) or len(evidence["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in evidence["sha256"])):
            raise ValueError("invalid task oracle evidence")
    return value


def validate_routes(routes):
    if set(routes) != {"static", "adaptive"}:
        raise ValueError("both routes required")
    fields = {"provider", "profile", "model", "binding_id", "roles", "execution"}
    if any(set(route) != fields for route in routes.values()) or routes["static"] != routes["adaptive"]:
        raise ValueError("paired route identity mismatch")
    route = routes["static"]
    if route["execution"] not in ("instrumented", "live") or not all(route[k] for k in fields):
        raise ValueError("incomplete route identity")
    return route


def verify_runtime_inputs(manifest, events=()):
    """Bind operator-owned controlled files separately from public source seal.

    The caller must freeze this manifest before opening the live holdout.
    Materialization alone never creates a delivery.
    """
    if not isinstance(manifest, dict):
        raise ValueError("pre-live runtime input manifest required")
    for name, expected in manifest.items():
        data = direct_bytes(name)
        if expected != {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}:
            raise ValueError("runtime input changed")
    for event in events:
        if event.get("provenance") == "provider-settings-reference":
            if manifest.get(event["reference"]) != {"bytes": event["controlled_bytes"], "sha256": event["payload_sha256"]}:
                raise ValueError("provider settings not bound to pre-live runtime inputs")


def require_recovery_coverage(execution, prepared, observation=None):
    """Only complete Claude stream proof can replace the live recovery block."""
    recovery = (prepared.get("record") or {}).get("acquisition", {}).get("recovery")
    if execution != "live" or not recovery:
        return
    if (not prepared.get("claude_read_stream") or not observation
            or observation.get("coverage") != "complete"
            or observation.get("schema") != "apg.claude-native-reads/v1"
            or observation.get("scope") != {k: prepared["record"][k] for k in ("run_id", "binding_id", "attempt_id")}
            or not isinstance(observation.get("events"), list)):
        raise ValueError("native recovery coverage unavailable; live arm incomplete")


def run_pair(*, pair_dir, source_root, scenario, routes, subject_files, prompt,
             executable_paths, oracle, result_importer, projection=None, planner=None,
             liveness_policy=None, seal=None, static_context=b"", capture=None, runtime_inputs=None):
    """Invoke each arm once through the actual APGR builder, adapter and runner.

    No retry is implicit, including on interruption, timeout, malformed output,
    failed oracle or missing traces. The caller must supply an independently
    authorized route; APG166A callers select instrumented executables only.
    """
    route = validate_routes(routes)
    if route["execution"] == "live" and (not isinstance(capture, dict)
            or not {"settings", "provenance", "overrides", "apgr_home"} <= capture.keys()):
        raise ValueError("explicit catalog capture required for live evaluation")
    if route["execution"] == "live":
        verify_runtime_inputs(runtime_inputs)
    if not isinstance(prompt, bytes) or not isinstance(static_context, bytes):
        raise ValueError("exact task and static context bytes required")
    prompt.decode("utf-8")
    static_context.decode("utf-8")
    pair_dir, source_root = Path(pair_dir), Path(source_root)
    if pair_dir.resolve() != pair_dir or source_root.resolve() != source_root:
        raise ValueError("physical pair and source roots required")
    from .readiness import verify_seal
    if route["execution"] == "live" and seal is None:
        raise ValueError("accepted readiness seal required before live invocation")
    if seal is not None:
        verify_seal(source_root, seal)
    if route["execution"] == "live":
        if seal.get("prerequisites_ready") is not True:
            raise ValueError("live prerequisites are blocked")
        if route["provider"] == "claude" and any(route[k] != seal.get("qualification", {}).get(k) for k in ("profile", "model")):
            raise ValueError("Claude route differs from qualified native Read binding")
    if not subject_files or len(subject_files) > 20000:
        raise ValueError("bounded clean subject required")
    for name, data in subject_files.items():
        path = Path(name)
        if path.is_absolute() or any(p in ("", ".", "..") for p in name.split("/")) or "\\" in name or not isinstance(data, bytes):
            raise ValueError("unsafe subject input")
    if sum(map(len, subject_files.values())) > 128 << 20:
        raise ValueError("subject exceeds archive budget")
    pair_dir.mkdir(mode=0o700, exist_ok=False)  # durable admission fence, including crashes
    try:
        admission = {"schema": SCHEMA, "scenario_id": scenario["scenario_id"], "routes": routes,
                     "scenario_sha256": hashlib.sha256(encoded(scenario)).hexdigest(),
                     "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
                     "static_context_sha256": hashlib.sha256(static_context).hexdigest(),
                     "runtime_inputs": runtime_inputs, "catalog_capture": capture, "replay_authorized": False}
        _write(pair_dir / "admission.json", admission)
        arms = {}
        for mode in ("static", "adaptive"):
            if route["execution"] == "live":
                verify_runtime_inputs(runtime_inputs)
            if seal is not None:
                verify_seal(source_root, seal)
            arm = pair_dir / mode; arm.mkdir(mode=0o700)
            subject = arm / "subject"; subject.mkdir(mode=0o700)
            run = arm / "run"; run.mkdir(mode=0o700)
            for name, data in subject_files.items():
                path = subject / name; path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                _write_bytes(path, data)
            before = _snapshot(subject)
            read_only = scenario["task_input"]["task_authority"] == "read_only"
            endpoint = provider.Endpoint(route["provider"], route["profile"])
            argv = provider.build_argv(endpoint, "reviewer" if read_only else "producer", source_root,
                                       read_only=read_only, pin_profile=route["execution"] == "live", **executable_paths)
            # Same construction owner as V1/V2 for explicitly injected Codex doctrine.
            if route["provider"] == "codex":
                from agent_source_guidance import codex_guidance_overrides
                additions = [part for value in codex_guidance_overrides(source_root, workers=False) for part in ("-c", value)]
                argv[-1:-1] = additions
            argv, payload, prepared = context_adapter.prepare(
                capture={**(capture or {"provenance": [], "overrides": [], "apgr_home": str(run)}),
                         "settings": {**(capture or {}).get("settings", {}), "mode": mode},
                         "project_root": str(subject)},
                run_dir=run, prefix="attempt", run_id=mode, binding_id=route["binding_id"], attempt_id="one",
                roles=route["roles"], consumer=route["provider"], argv=argv,
                prompt=prompt + static_context if mode == "static" else prompt,
                projection=projection, planner=planner)
            prepared["evaluation_transport"] = True
            native_reads = None
            if route["execution"] == "live" and route["provider"] == "claude":
                from . import claude_reads
                argv = claude_reads.prepare(prepared, argv, qualification=seal["qualification"])
            result = {"route": route, "requested_mode": mode, "effective_mode": prepared.get("record", {}).get("effective_mode"),
                      "status": "incomplete", "retries": 0, "producer_revisions": [],
                      "missing_guidance_findings": None, "restart_required_incidents": None,
                      "model_observed": None, "replay_authorized": False}
            _write(run / "started.json", {"attempt_id": "one", "replay_authorized": False})
            _write_bytes(run / "provider.stdin", payload)
            try:
                returned = context_adapter.invoke(prepared, provider.run, argv, payload, subject,
                                                  liveness_policy=liveness_policy)
                _write_bytes(run / "provider.stdout", returned.stdout)
                _write_bytes(run / "provider.stderr", returned.stderr)
                result["provider_terminal"] = {"exit_code": returned.exit_code}
                if returned.exit_code:
                    raise ValueError("provider nonzero")
                import_bytes = returned.stdout
                if prepared.get("claude_read_stream"):
                    native_reads = claude_reads.collect(prepared, returned)
                    result["native_reads"] = {"schema": native_reads["schema"],
                                              "raw_stream": native_reads["raw_stream"],
                                              "read_count": len(native_reads["reads"])}
                    import_bytes = native_reads["terminal"]["result"].encode("utf-8")
                imported = result_importer(import_bytes, route)
                if not isinstance(imported, dict) or set(imported) != {"producer_revisions", "missing_guidance_findings", "restart_required_incidents", "model_observed"}:
                    raise ValueError("invalid provider result import")
                if any(not isinstance(imported[k], list) for k in ("producer_revisions", "missing_guidance_findings", "restart_required_incidents")):
                    raise ValueError("invalid provider finding/revision collections")
                if route["execution"] == "instrumented" and imported["model_observed"] is not None:
                    raise ValueError("instrumented actors cannot establish model observation")
                result.update(imported)
                trace = load(run / "attempt.context-deliveries.json")
                diagnostics = []
                late = records(run, mode, diagnostics=diagnostics)
                observed = delivery_entries([*trace["events"], *(r["event"] for r in late),
                                             *(native_reads or {}).get("events", [])],
                    run_id=mode, binding_id=route["binding_id"], attempt_id="one")
                if trace["coverage"] != "complete" or observed["coverage"] != "complete" or diagnostics:
                    raise ValueError("incomplete transmission coverage")
                if route["execution"] == "live":
                    verify_runtime_inputs(runtime_inputs, trace["events"])
                require_recovery_coverage(route["execution"], prepared, native_reads)
                result["deliveries"] = observed["deliveries"]
                result["initial"], result["cumulative"] = delivered_totals(result["deliveries"])
                result["authority"] = {"read_only": read_only, "unchanged": before == _snapshot(subject)}
                if read_only and not result["authority"]["unchanged"]:
                    raise ValueError("read-only subject changed")
                result["task_oracle"] = import_oracle(oracle(subject, returned, scenario), scenario["expected_outcome"]["quality_oracle"])
                after_oracle = _snapshot(subject)
                changed = sorted(name for name in before.keys() | after_oracle.keys() if before.get(name) != after_oracle.get(name))
                allowed = set(scenario["task_input"].get("mutation_scope", []))
                result["authority"].update(changed_paths=changed, permitted=not changed if read_only else set(changed) <= allowed)
                if not result["authority"]["permitted"]:
                    raise ValueError("subject authority changed outside permitted scope")
                result["late_acquisitions"] = [r for r in observed["deliveries"] if r["phase"] == "late"]
                result["exact_recovery"] = [r for r in result["late_acquisitions"] if r["channel"] == "recovery_read"]
                result["status"] = "mechanism_observed" if route["execution"] == "instrumented" else "live_observed"
            except (Exception, KeyboardInterrupt, provider.ProviderLivenessExpired, provider.ProviderInterrupted) as error:
                result["failure"] = type(error).__name__
                try:
                    result["authority"] = {"read_only": read_only, "unchanged": before == _snapshot(subject)}
                except (OSError, ValueError):
                    result["authority"] = {"read_only": read_only, "unchanged": None}
                if hasattr(error, "stdout"):
                    _write_bytes(run / "provider.stdout", error.stdout)
                    _write_bytes(run / "provider.stderr", error.stderr)
                    result["provider_terminal"] = {"failure": type(error).__name__, "cleanup": error.cleanup}
                _write(run / "terminal.json", result)
                if isinstance(error, KeyboardInterrupt):
                    raise
                raise ValueError("pair incomplete; inspect retained attempt, never blindly replay") from error
            _write(run / "terminal.json", result)
            arms[mode] = result
        if seal is not None:
            verify_seal(source_root, seal)
        value = {"schema": SCHEMA, "scenario_id": scenario["scenario_id"], "arms": arms,
                 "evidence_kind": "runner_qualification" if route["execution"] == "instrumented" else "live_pair",
                 "h_gate_established": False, "scenario15": "contingent/unavailable"}
        value["artifacts"] = _snapshot(pair_dir)
        _write(pair_dir / "pair.json", value)
        return value
    except BaseException as error:
        # Admission is already durable: preparation failures need a terminal
        # record too. Never remove the fence or replay a possibly started arm.
        _write(pair_dir / "terminal.json", {"schema": SCHEMA, "status": "incomplete",
                                            "failure": type(error).__name__, "replay_authorized": False})
        raise



def read_pair(pair_dir):
    """Archive/resume verification only. This path cannot launch a provider."""
    pair_dir = Path(pair_dir)
    value = load(pair_dir / "pair.json")
    actual = _snapshot(pair_dir)
    actual.pop("pair.json", None)
    if actual != value["artifacts"]:
        raise ValueError("pair evidence changed or lost")
    for mode, arm in value["arms"].items():
        if delivered_totals(arm["deliveries"]) != (arm["initial"], arm["cumulative"]):
            raise ValueError("retained transmission totals differ")
    return value
