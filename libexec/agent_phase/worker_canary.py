"""Bounded nonce canaries through the dispatcher's actual stage launch path."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shlex
import subprocess
import sys
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import antigravity_evidence as antigravity_evidence_module
from . import provider
from .bundle import BundleError as BundleError, load_bundle as load_bundle
from .canary_budget import (
    DEFAULT_PHASE,
    SONNET_CASES,
    SONNET_PHASE,
    CanaryBudget,
    CanaryBudgetError,
    classify_cleanup,
    cleanup_inputs,
)
from .canary_native_evidence import (
    _native_call_coverage as _native_call_coverage,
    antigravity_parent_nonce_returned as antigravity_parent_nonce_returned,
    correlate_native_children as correlate_native_children,
    extract_stream_init as extract_stream_init,
    native_nonce_returns as native_nonce_returns,
    native_reuse_ready as native_reuse_ready,
    native_tool_observations as native_tool_observations,
    normalize_native_model_observation as normalize_native_model_observation,
    parent_nonce_returned as parent_nonce_returned,
)
from .canary_qualification import (
    ANTIGRAVITY_CHECK_KEYS as ANTIGRAVITY_CHECK_KEYS,
    CASE_ROUTES as CASE_ROUTES,
    CASES as CASES,
    PARENT_LAUNCH_FIELDS as PARENT_LAUNCH_FIELDS,
    _launch_bound_parent_identity as _launch_bound_parent_identity,
    qualify as qualify,
)
from .dispatch import Dispatcher
from .envelope import RenderedPrompt
from .roster import Endpoint
from .routing import antigravity_intelligence
from .run import RunDirectory, stage_parent_id
from .runtime_identity import runtime_identity
from .worker_capability import resolve_worker_capability
from .worker_evidence import events, native_admissions, parent_observation

DISALLOWED_PREFIXES = (
    "AGENT_CENTRAL_",
    "APGR_AUTHORITY_",
    "APGR_DISPATCH_",
    "APGR_WORKER_",
    "APGR_PARENT_",
    "APGR_ROLE_",
    "APGR_STAGE_",
    "APGR_TASK_",
    "AGENT_WORKER_",
)

DISALLOWED_EXACT = {
    "APG166S_BOOTSTRAP_REQUIRED_WORKERS",
    "CODEX_THREAD_ID",
    "CODEX_SESSION_ID",
    "CODEX_CI",
    "APGR_MODEL_AUTHORITY",
    "APGR_TARGET_PROJECT_START",
    "PARENT_ID",
    "WORKER_ID",
    "STAGE_ID",
    "TASK_AUTHORITY",
    "MUTATION_SCOPE",
}


def clean_environment(apgr_home: Path | None = None) -> dict[str, str]:
    """Inherit authentication and remove the enumerated orchestration context."""
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        if any(key.startswith(prefix) for prefix in DISALLOWED_PREFIXES):
            continue
        if key in DISALLOWED_EXACT:
            continue
        env[key] = value

    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if apgr_home is not None:
        env["APGR_HOME"] = str(Path(apgr_home).resolve())
    return env


def _runner(actual: list):
    def run(argv, prompt, cwd, max_output, on_output=None):
        args = list(argv)
        if "exec" in args:
            args = args[:-1] + ["--json", "--skip-git-repo-check"] + args[-1:]
        elif "--evidence-prefix" not in args:
            args += ["--output-format", "stream-json", "--verbose"]
        actual.append(args)
        return provider.run(
            args,
            prompt,
            cwd,
            max_output,
            on_output,
            liveness_policy=provider.LivenessPolicy(outer_ceiling_seconds=1200),
        )
    return run


def _worker_interface(family: str, kind: str, cap: dict) -> str:
    """Select the per-kind transport, distinct from a parent's native facility."""
    allowed = cap.get("allowed_worker_kinds")
    if not isinstance(allowed, list) or kind not in {"gemini", "luna", "sonnet"}:
        raise ValueError("unsupported parent worker interface")
    worker = cap.get(kind + "_worker") or {}
    transport = worker.get("transport")
    if kind == "gemini" and transport is None and worker.get("provider") == "antigravity":
        transport = "antigravity"
    expected = {"gemini": "antigravity", "luna": "codex_external", "sonnet": "claude_external"}
    if family == "codex":
        expected["luna"] = "codex_native"
    elif family == "claude":
        expected["sonnet"] = "claude_native"
    elif family != "antigravity":
        raise ValueError("unsupported parent worker interface")
    if transport != expected[kind]:
        raise ValueError("unsupported parent worker interface")
    if transport in {"codex_native", "claude_native"}:
        if kind in allowed or cap.get("interface") != ("native" if family == "codex" else "stdio-mcp"):
            raise ValueError("unsupported parent worker interface")
        return "native"
    if kind not in allowed:
        raise ValueError("unsupported parent worker interface")
    if family == "antigravity" and cap.get("interface") == "cli":
        return "cli"
    if family == "claude" and cap.get("interface") == "stdio-mcp":
        return "stdio-mcp"
    if family == "codex" and cap.get("interface") == "native" and (
            cap.get("parent_family") == "codex_parent" and cap.get("policy_selection") == "triple_pool_4x4x4"):
        return "stdio-mcp"
    raise ValueError("unsupported parent worker interface")


def cli_worker_commands(entrypoint: Path, task_file: Path, kind: str) -> list[list[str]]:
    return [
        [str(entrypoint), "job", "launch", "--worker-kind", kind, "--key", "nonce-canary",
         "--task-file", str(task_file), "--task-authority", "read_only",
         "--acceptance-criteria", "return fixture contents"],
        [str(entrypoint), "job", "wait", "--job-id", "<job-id>", "--timeout", "30"],
        [str(entrypoint), "job", "outcome", "--job-id", "<job-id>", "--outcome", "accepted",
         "--evidence", "completed leaf returned fixture contents; cleanup proven"],
    ]


def _prompt(
    fixture: Path,
    family: str,
    kind: str,
    worker_choice: dict | None = None,
    case: str | None = None,
    *,
    interface: str | None = None,
    worker_entrypoint: Path | None = None,
) -> str:
    """Generate prompt integrating selected worker choices without hardcoding Luna models/efforts."""
    choice = worker_choice or {}
    model = choice.get("model")
    effort = choice.get("effort")
    if not model or not effort:
        raise ValueError("selected worker model and effort required")

    expected_interface = ("cli" if family == "antigravity" else "native"
        if (family, kind) in {("codex", "luna"), ("claude", "sonnet")} else "stdio-mcp")
    if family not in {"codex", "claude", "antigravity"} or kind not in {"luna", "gemini", "sonnet"} or (
        interface is not None and interface != expected_interface):
        raise ValueError("unsupported parent worker interface")
    if family == "antigravity":
        if worker_entrypoint is None:
            raise ValueError("CLI worker interface requires source-owned entrypoint")
        operation = ("Use the inherited CLI facade and inherited parent identity. "
            + "; then ".join(shlex.join(command) for command in cli_worker_commands(
                worker_entrypoint, fixture.parent / "leaf-task.md", kind))
            + ". Replace <job-id> with the admitted identifier; record accepted only after terminal completion "
              "and proven cleanup, otherwise record the observed partial/failed outcome with evidence. "
              "Do not initialize a parent or supply parent/state overrides. Do not directly launch foreign providers. "
            + f"The selected leaf is {model} with {effort} effort. No fallback or recursive workers.")
    elif family == "codex" and kind == "luna":
        operation = (
            f"Use the native spawn_agent tool with model {model} and {effort} effort. "
            "Use one leaf only, no further delegation. Wait for its terminal result."
        )
    elif family == "claude" and kind == "sonnet":
        if case == "claude-sonnet-native-reuse":
            operation = (
                "Use the native Agent tool with subagent_type apgr-sonnet-leaf:apgr-sonnet-leaf and run_in_background=false. "
                "Do not override model or effort. Delegate 5 sequential foreground leaf tasks one after another, "
                "waiting for each terminal result before launching the next. No further delegation."
            )
        else:
            operation = (
                "Use the native Agent tool with subagent_type apgr-sonnet-leaf:apgr-sonnet-leaf and run_in_background=false. "
                "Do not override model or effort. Use one leaf only, no further delegation. Wait for its terminal result."
            )
    else:
        operation = (
            f"Use the agent_worker server submit tool with worker_kind={kind}, task_authority=read_only, "
            "key=nonce-canary and acceptance_criteria=return fixture contents. "
            "Use bounded waits; obtain its result and record outcome. Do not initialize a parent."
        )

    intro = (
        "This is a worker-facility nonce canary. Delegate 5 sequential read-only leaf tasks. "
        if case == "claude-sonnet-native-reuse"
        else "This is a worker-facility nonce canary. Delegate exactly one read-only leaf task. "
    )
    return (
        intro
        + "Do not read the fixture yourself. Do not modify files, run tests, build, use Git, "
        "or launch any other worker. "
        + operation
        + "\nLeaf task: read only "
        + str(fixture)
        + " and return its exact contents. The leaf must not delegate. "
        "Return the leaf result verbatim and the terminal worker identifier. "
        "If the required facility is unavailable report unavailable and stop; do not substitute."
    )


def _antigravity_launch_receipt(record: dict, root: Path, directory: RunDirectory, bundle, roster) -> dict:
    """Bind roster identity to the executed launch; never claim effective telemetry.

    Effort is a roster lookup on the launched profile. The launcher's profile file
    supplies model only. Its validated v6 terminal record supplies transport proof.
    """
    receipt: dict[str, Any] = {
        "schema": "apgr.canary-parent-identity/v1", "basis": "launch_bound_match",
        "runtime_effective_observation": False, "effort_observed": False,
        "effort_basis": "roster_lookup_on_launched_profile",
        "checks": dict.fromkeys(ANTIGRAVITY_CHECK_KEYS, False), "status": "unknown",
    }
    try:
        case = record["case"]
        family, profile, _kind = CASES[case]
        phase_type, mode, slot = CASE_ROUTES[case]
        expected_endpoint = {"provider": family, "profile": profile}
        resolved = roster.route_endpoints(phase_type, mode)[slot]
        resolved_endpoint = {"provider": resolved.provider, "profile": resolved.profile}
        selected = bundle.select_model(family, profile).as_dict()
        identity = {key: selected[key] for key in ("provider", "profile", "model", "effort")}
        parent = record["parent"]
        route = record["route_provenance"]
        meta = record.get("stage_meta") or {}
        stage_cap = meta.get("worker_capability") or {}
        registered = record.get("registered_parent_capability") or {}
        profile_model = antigravity_intelligence(root, profile)["model"]
        expected_argv = [os.fspath(root / provider.ANTIGRAVITY_LAUNCHER), profile,
                         "-p", "--reviewer", "--evidence-prefix", os.fspath(directory.path / "01-work")]
        checks = receipt["checks"]
        checks["route_source_owned"] = bool(
            family == "antigravity"
            and (route.get("phase_type"), route.get("execution_mode"), route.get("endpoint_slot")) == CASE_ROUTES[case]
            and route.get("endpoint") == expected_endpoint
            and route.get("resolved_endpoint") == resolved_endpoint == expected_endpoint
            and route.get("roster") == roster.provenance()
            and route.get("lifecycle") == "standard")
        checks["roster_selection"] = bool(
            all(isinstance(identity[key], str) and identity[key] for key in identity)
            and all(parent.get(key) == value for key, value in identity.items())
            and all(stage_cap.get("parent_" + key) == value for key, value in identity.items())
            and all(registered.get("parent_" + key) == value for key, value in identity.items()))
        checks["profile_model_match"] = profile_model == identity["model"]
        checks["stage_identity"] = bool(
            (meta.get("stage"), meta.get("role"), meta.get("provider"), meta.get("profile")) == ("work", "worker", family, profile)
            and (route.get("executed_stage"), route.get("executed_role")) == ("work", "worker")
            and parent.get("stage") == registered.get("parent_stage") == "work"
            and stage_cap.get("execution_mode") == registered.get("execution_mode") == mode)
        checks["launch_argv"] = bool(type(record.get("provider_invocations")) is int
            and record["provider_invocations"] == 1 and record.get("actual_argv") == [expected_argv]
            and meta.get("argv") == expected_argv)
        checks["run_binding"] = bool(
            record.get("parent_id") == stage_parent_id(directory.run_id, "work", 1)
            and record.get("run_id") == registered.get("parent_run_id") == directory.run_id
            and record.get("run_directory") == os.fspath(directory.path))
        receipt.update(parent=identity, profile_model=profile_model, route=deepcopy(route),
            parent_id=record.get("parent_id"), run_id=directory.run_id, run_directory=os.fspath(directory.path),
            stage_nonce=record.get("nonce"),
            launch=deepcopy({key: meta.get(key) for key in PARENT_LAUNCH_FIELDS}),
            registration=deepcopy(registered),
            candidate_source_identity=record.get("candidate_source_identity"),
            controller_identity=record.get("controller_identity"),
            bundle_sha256=record["bundle"]["manifest_sha256"])
        # Missing metadata never supplies a default successful wrapper exit.
        if type(meta.get("exit_code")) is not int:
            return receipt
        validated = antigravity_evidence_module.validate(directory.path, "01-work", profile, profile_model, True, meta["exit_code"])
        checks["terminal_revalidated"] = validated == meta.get("antigravity_evidence")
        checks["terminal_success"] = bool(
            validated.get("validation") == "validated" and validated.get("provider_status") == "success"
            and validated.get("transport_success") is True and validated.get("completion_fence_observed") is True
            and validated.get("terminal_record_kind") == "exact_raw_event" and validated.get("response_source") == "result.response"
            and validated.get("wrapper_exit_code") == meta["exit_code"] == 0 and validated.get("child_started") is True
            and (validated.get("process_group_cleanup") or {}).get("cleanup_complete") is True
            and (validated.get("version_probe_cleanup") or {}).get("cleanup_complete") is True
            # The digest-checked response must echo this run's fresh challenge,
            # preventing a prior successful terminal record from being replayed.
            and isinstance(record.get("nonce"), str) and bool(record["nonce"])
            and antigravity_parent_nonce_returned(directory.path, meta, record["nonce"]))
        # After a successful completion fence the wrapper may terminate the child;
        # child_exit_code is deliberately not promoted to a transport failure.
        receipt["status"] = "launch_bound_match" if all(value is True for value in checks.values()) else "mismatch"
    except (OSError, RuntimeError, ValueError, TypeError, LookupError, AttributeError) as error:
        receipt["diagnostic"] = type(error).__name__
    return receipt


def _seal_receipt(path: Path, record: dict[str, Any]) -> tuple[bytes, str]:
    """Atomically seal canary record to path and return bytes and sha256."""
    content = (json.dumps(record, indent=2) + "\n").encode()
    tmp_path = path.with_name(f"{path.name}.tmp.{secrets.token_hex(8)}")
    tmp_path.write_bytes(content)
    tmp_path.replace(path)
    return content, hashlib.sha256(content).hexdigest()


def run_case(
    root: Path,
    home: Path,
    output: Path,
    case: str,
    *,
    cause: str | None = None,
    runner: Callable | None = None,
    phase: str | None = None,
) -> dict:
    """Each exclusive case directory is one attempt; callers cannot replay it."""
    root = Path(root).resolve()
    home = Path(home).resolve()
    output = Path(output).resolve()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)

    source = runtime_identity(root)
    controller_root = Path(__file__).resolve().parents[2]
    controller_identity = runtime_identity(controller_root)
    workspace = output / "workspace"
    workspace.mkdir(mode=0o700)
    nonce = secrets.token_hex(24)
    fixture = workspace / "nonce.txt"
    fixture.write_text(nonce + "\n")
    family, profile, kind = CASES[case]

    effective_phase = phase or (SONNET_PHASE if case in SONNET_CASES else DEFAULT_PHASE)

    sys.path.insert(0, str(root))
    from testing.h_eval.d1_qualification import assert_structural_non_holdout

    directory = RunDirectory(output / "runs", "worker-canary", effective_phase)
    actual: list[list[str]] = []
    provider_invocations = 0
    delegate_runner = runner or _runner(actual)
    def effective_runner(argv, prompt, cwd, max_output, on_output=None):
        nonlocal provider_invocations
        provider_invocations += 1
        if runner is not None:
            actual.append(list(argv))
        return delegate_runner(argv, prompt, cwd, max_output, on_output)

    try:
        dispatcher = Dispatcher(root, workspace, run_root=output / "runs", apgr_home=home,
                                runner=effective_runner, resolve_scanner=False)
        bundle = dispatcher.roster.bundle
        requested = bundle.select_model(family, profile).as_dict()
        phase_type, mode, slot = CASE_ROUTES[case]
        resolved_endpoints = dispatcher.roster.route_endpoints(phase_type, mode)
        resolved_endpoint = resolved_endpoints[slot]
        if resolved_endpoint != Endpoint(family, profile):
            raise ValueError("canary endpoint does not match validated route")
        if family == "antigravity":
            profile_model = antigravity_intelligence(root, profile)["model"]
            if profile_model != requested.get("model"):
                raise ValueError("profile-file model does not match roster")
        from .runtime_models import captured
        with captured(bundle):
            cap = resolve_worker_capability(root, family, profile, mode)
        if not cap or not cap.get("allowed"):
            raise ValueError("worker_unavailable: " + str((cap or {}).get("reason")))
        worker_choice = cap.get(kind + "_worker") or {}
        interface = _worker_interface(family, kind, cap)
        prompt = _prompt(fixture, family, kind, worker_choice=worker_choice, case=case,
                         interface=interface, worker_entrypoint=root / "bin/agent-worker")
        (workspace / "leaf-task.md").write_text(
            f"Read only {fixture} and return its exact contents. Do not delegate, modify files, run tests, builds or Git.\n")
        assert_structural_non_holdout(prompt, root)
    except (OSError, RuntimeError, ValueError, TypeError, LookupError, AttributeError, CanaryBudgetError) as error:
        record = {"schema": "apgr.worker-canary/v1", "phase": effective_phase, "case": case,
                  "candidate_source_identity": source, "status": "blocked", "reservation": None,
                  "budget_reservation": None, "preflight_refusal": True,
                  "error_type": type(error).__name__, "diagnostic": str(error),
                  "provider_invocations": provider_invocations, "actual_argv": actual,
                  "cleanup_proven": False}
        _seal_receipt(output / "canary.json", record)
        return record

    # Preflight refuses without spending an attempt. Stage failures remain audited.
    budget = CanaryBudget(phase=effective_phase)
    try:
        reservation = budget.reserve(case, cause=cause)
    except CanaryBudgetError as error:
        record = {"schema": "apgr.worker-canary/v1", "phase": effective_phase, "case": case,
                  "candidate_source_identity": source, "candidate_unchanged": True,
                  "status": "blocked", "error_type": type(error).__name__, "diagnostic": str(error),
                  "budget_reservation": None, "cleanup_proven": False}
        _seal_receipt(output / "canary.json", record)
        return record

    record: dict[str, Any] = {
        "schema": "apgr.worker-canary/v1",
        "phase": effective_phase,
        "case": case,
        "nonce": nonce,
        "candidate_source_identity": source,
        "controller_identity": controller_identity,
        "bundle": bundle.provenance(),
        "parent": {**requested, "stage": "work", "authority": "read_only"},
        "worker": {
            "kind": kind,
            "authority": "read_only",
            "recursive": False,
            "requested": worker_choice,
        },
        "entrypoints": {
            name: str(root / "bin" / name)
            for name in ("agent-worker", "agent-worker-mcp")
        },
        "capability": cap,
        "worker_interface": interface,
        "route_provenance": {"phase_type": phase_type, "execution_mode": mode, "endpoint_slot": slot,
            "endpoint": {"provider": family, "profile": profile},
            "resolved_endpoint": {"provider": resolved_endpoint.provider, "profile": resolved_endpoint.profile}, "roster": dispatcher.roster.provenance(),
            "lifecycle": dispatcher.lifecycle.name, "executed_stage": "work", "executed_role": "worker",
            "original_requirement": cap.get("requirement"),
            "qualification_requirement": "required" if case in SONNET_CASES else cap.get("requirement")},
        "budget_reservation": reservation,
        "parent_id": stage_parent_id(directory.run_id, "work", 1),
        "run_id": directory.run_id, "run_directory": os.fspath(directory.path),
        "environment_names": sorted(os.environ),
        "runtime_owner": "product",
        "bootstrap_runtime_used": False,
        "status": "started",
        "attempt_limit": 2,
    }
    _seal_receipt(output / "canary.json", record)

    def _seal_unexpected_blocked(error: BaseException) -> None:
        record.update(
            status="blocked",
            error_type=type(error).__name__,
            diagnostic=str(error),
            cleanup_proven=False,
        )
        _receipt_bytes, receipt_sha256 = _seal_receipt(output / "canary.json", record)
        details: dict[str, Any] = {
            "receipt": str(output / "canary.json"),
            "source_identity": source,
            "receipt_sha256": receipt_sha256,
            "case": case,
            "phase": effective_phase,
            "error_type": type(error).__name__,
            "diagnostic": str(error),
        }
        if "classification_inputs" in record:
            details["classification_inputs"] = record["classification_inputs"]
        if "bundle" in record and isinstance(record["bundle"], dict) and "manifest_sha256" in record["bundle"]:
            details["bundle_sha256"] = record["bundle"]["manifest_sha256"]
        if record.get("parent_cleanup") is not None:
            details["parent_cleanup"] = record["parent_cleanup"]
        if record.get("stage_meta", {}).get("worker_drain") is not None:
            details["worker_drain"] = record["stage_meta"]["worker_drain"]
        budget.record_disposition(
            case,
            reservation["attempt"],
            status="blocked",
            cleanup_proven=False,
            details=details,
        )

    try:
        try:
            result, meta = dispatcher._stage(
                directory,
                1,
                "work",
                "01-work",
                "worker",
                Endpoint(family, profile),
                RenderedPrompt(prompt.encode(), [{"kind": "task_prompt", "start": 0, "end": len(prompt.encode())}]),
                None,
                read_only=True,
                worker_capability={**cap, "requirement": "required"} if case in SONNET_CASES else cap,
            )

            from apgr_workers.ledger import ParentLedger
            ledger = ParentLedger(stage_parent_id(directory.run_id, "work", 1), directory.path / "workers")
            state = json.loads(ledger.data_path.read_text()) if ledger.data_path.is_file() else {}
            jobs = state.get("gemini_jobs", {})
            observed = []
            for path in (directory.path / "workers").rglob("*.result.json"):
                observed.append(json.loads(path.read_text()))

            if case in {"claude-sonnet-native", "claude-sonnet-native-reuse"}:
                correlated = correlate_native_children(result.stdout, state.get("native_agents") or {},
                    record["parent_id"], nonce, worker_choice)
                native = correlated["children"]
                record["native_unmatched"] = correlated["unmatched"]
                record["native_call_coverage"] = correlated["coverage"]
            else:
                native = native_admissions(result.stdout, expected_nonce=nonce)

            record.update(
                authentication_failed=any(
                    event.get("type") == "assistant"
                    and event.get("error") == "authentication_failed"
                    for event in events(result.stdout)
                ),
                parent_observed=parent_observation(result.stdout),
                stream_init=extract_stream_init(result.stdout),
                stage_meta=meta,
                actual_argv=actual,
                admission=jobs,
                capacity_receipt={key: state.get("policy", {}).get(key) for key in ("max_gemini", "max_luna", "max_sonnet", "borrowing")},
                registered_parent_capability=state.get("worker_capability"),
                native_admission=native,
                native_sonnet_count=ledger.get_status().get("sonnet_count"),
                worker_results=observed,
                parent_cleanup=result.cleanup,
                nonce_returned=(antigravity_parent_nonce_returned(directory.path, meta, nonce)
                    if family == "antigravity" else parent_nonce_returned(result.stdout, nonce)),
                stage_ok=result.ok,
            )
            cleanup = bool(result.cleanup and result.cleanup.get("cleanup_proven"))
            cleanup &= meta.get("worker_drain", {}).get("uncertain_cleanup") is False
            record["cleanup_proven"] = cleanup
        except (OSError, RuntimeError, ValueError, TypeError, LookupError, AttributeError, subprocess.SubprocessError) as error:
            record.update(
                status="blocked",
                error_type=type(error).__name__,
                error_code=getattr(error, "code", None),
                diagnostic=str(error),
                actual_argv=actual,
                cleanup_proven=False,
            )
            if error.__cause__ is not None:
                record["underlying_exception"] = {
                    "type": type(error.__cause__).__name__,
                    "detail": str(error.__cause__).replace("\n", " ").strip()[:240],
                }
            meta_path = directory.path / "01-work.meta.json"
            if meta_path.is_file():
                meta = json.loads(meta_path.read_text())
                raw_path = directory.path / "01-work.stdout.md"
                raw = raw_path.read_bytes() if raw_path.is_file() else b""
                record.update(
                    stage_meta=meta,
                    parent_observed=parent_observation(raw),
                    stream_init=extract_stream_init(raw),
                    native_admission=(
                        [] if case in {"claude-sonnet-native", "claude-sonnet-native-reuse"}
                        else native_admissions(raw, expected_nonce=nonce)
                    ),
                    parent_cleanup=meta.get("cleanup"),
                    cleanup_proven=bool(
                        meta.get("cleanup", {}).get("cleanup_proven")
                        and meta.get("worker_drain", {}).get("uncertain_cleanup") is False
                    ),
                )
                record["authentication_failed"] = any(
                    event.get("type") == "assistant"
                    and event.get("error") == "authentication_failed"
                    for event in events(raw)
                )
                errors = [
                    event.get("result")
                    for event in events(raw)
                    if event.get("type") == "result" and event.get("is_error")
                ]
                if errors:
                    record["provider_diagnostic"] = errors
            record["worker_results"] = [
                json.loads(path.read_text())
                for path in (directory.path / "workers").rglob("*.result.json")
            ]
            record["worker_disposition"] = "unavailable"

        # Verify source stability and qualify evidence
        record["provider_invocations"] = provider_invocations
        record["actual_argv"] = actual
        record["classification_inputs"] = cleanup_inputs(record, directory.path)
        record["cleanup_classification"] = classify_cleanup(record, directory.path)
        record["cleanup_proven"] = record["cleanup_classification"]["cleanup_proven"]
        effective_cap = record.get("stage_meta", {}).get("worker_capability") or {}
        evidence = record.get("stage_meta", {}).get("antigravity_evidence") or {}
        record["outcome_layers"] = {
            "provider": {"status": evidence.get("provider_status"), "transport_success": evidence.get("transport_success"),
                         "exit_code": record.get("stage_meta", {}).get("exit_code")},
            "facility": {"allowed": effective_cap.get("allowed"), "reason": effective_cap.get("reason"),
                         "interface": effective_cap.get("interface"),
                         "disposition": record.get("stage_meta", {}).get("worker_disposition")},
            "child": {"admissions": len(record.get("admission") or {}) + len(record.get("native_admission") or []),
                      "statuses": [item.get("status") for item in record.get("worker_results", [])]},
        }
        record["candidate_unchanged"] = (source == runtime_identity(root))
        record["controller_unchanged"] = (controller_identity == runtime_identity(controller_root))
        try:
            after_bundle = load_bundle(repo_root=root, apgr_home=home, required=True)
            record["bundle_unchanged"] = after_bundle.provenance()["manifest_sha256"] == record["bundle"]["manifest_sha256"]
        except (BundleError, OSError, ValueError, TypeError, LookupError, RuntimeError):
            record["bundle_unchanged"] = False
        if CASES.get(case, (None,))[0] == "antigravity":
            record["parent_identity"] = _antigravity_launch_receipt(record, root, directory, bundle, dispatcher.roster)
        q_result = qualify(record)
        record["qualification"] = q_result
        record["status"] = q_result["status"]
        if not q_result["passed"] and not record.get("diagnostic"):
            record["diagnostic"] = "; ".join(q_result["reasons"])

        # Seal the original receipt and classification inputs before binding disposition.
        receipt_bytes, receipt_sha256 = _seal_receipt(output / "canary.json", record)
        budget.record_disposition(
            case,
            reservation["attempt"],
            status=record["status"],
            cleanup_proven=record.get("cleanup_proven", False),
            details={"receipt": str(output / "canary.json"), "source_identity": source,
                     "receipt_sha256": receipt_sha256,
                     "case": case, "phase": effective_phase,
                     "classification_inputs": record["classification_inputs"],
                     "bundle_sha256": record["bundle"]["manifest_sha256"],
                     "parent_cleanup": record.get("parent_cleanup"),
                     "worker_drain": record.get("stage_meta", {}).get("worker_drain")},
        )
    except Exception as error:
        _seal_unexpected_blocked(error)
        raise

    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    parser.add_argument("--apgr-home", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--cause", default=None, help="Remediation cause for attempt 2")
    parser.add_argument("--phase", default=None, help="Optional budget phase override")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    clean = clean_environment(args.apgr_home)
    os.environ.clear()
    os.environ.update(clean)

    freeze = json.loads(args.freeze.read_text())
    selected = load_bundle(repo_root=root, apgr_home=args.apgr_home.resolve(), required=True)
    if freeze.get("runtime_identity") != runtime_identity(root) or freeze.get("bundle_sha256") != selected.provenance()["manifest_sha256"]:
        raise ValueError("canary freeze mismatch before budget reservation")

    record = run_case(
        root,
        args.apgr_home.resolve(),
        args.output.resolve(),
        args.case,
        cause=args.cause,
        phase=args.phase,
    )
    print(
        json.dumps(
            {
                "case": args.case,
                "status": record["status"],
                "cleanup_proven": record.get("cleanup_proven"),
            }
        )
    )
    return 0 if record["status"] == "passed" else 1
