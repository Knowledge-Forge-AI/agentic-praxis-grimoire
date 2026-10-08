"""Command-line interface for the shared agent-worker facility."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .adapter import (
    cancel_worker_job,
    close_native_agent,
    get_active_parent_id,
    handle_native_post_tool,
    handle_native_pre_tool,
    handle_native_subagent_start,
    handle_native_subagent_stop,
    launch_worker_job,
    wait_worker_job,
    validate_inherited_context,
)
from .ledger import AuthorityViolationError, ParentLedger
from .policy import TRIPLE_POOL, load_worker_policy, selected_capability


def parent_capability(parent_id: str, family: str, policy_path: Path | None,
                      policy_selection: str | None = None,
                      excluded_worker_kinds: list[str] | None = None) -> dict[str, Any]:
    """Freeze source and lifetime context for direct provider launchers."""
    root = Path(__file__).resolve().parents[2]
    policy, source, digest = load_worker_policy(root, policy_path)
    policy_selection = policy_selection or (TRIPLE_POOL if policy.get("schema") == "agent-worker-policy-v2" else None)
    if policy_selection:
        capability = {**selected_capability(root, family, policy, source, digest, policy_selection),
                "source_root": str(root), "lifecycle_generation": parent_id,
                "interface": "stdio-mcp", "policy_source": str((root / source).resolve())}
        excluded = set(excluded_worker_kinds or [])
        if not excluded.issubset({"gemini", "luna", "sonnet"}):
            raise ValueError("invalid excluded worker kind")
        capability["allowed_worker_kinds"] = [kind for kind in capability["allowed_worker_kinds"] if kind not in excluded]
        capability["excluded_worker_kinds"] = sorted(excluded)
        if family in {"codex_parent"} and "luna" in excluded:
            if isinstance(capability.get("native_worker"), dict):
                capability["native_worker"]["enabled"] = False
        return capability
    if excluded_worker_kinds:
        raise ValueError("worker exclusions require an explicit policy selection on a fresh lifetime")
    gemini_max = policy["limits"]["max_gemini_workers_per_parent"]
    aggregate_max = (
        policy["limits"]["max_aggregate_workers_per_codex_parent"]
        if family == "codex_parent" else gemini_max
    )
    return {
        "available": True,
        "allowed": family != "codex_parent",
        "parent_family": family,
        "source_root": str(root),
        "lifecycle_generation": parent_id,
        "interface": "stdio-mcp",
        "policy_source": str((root / source).resolve()),
        "policy_sha256": digest,
        "limits": {"max_gemini": gemini_max, "max_aggregate": aggregate_max},
        "gemini_worker": policy["gemini_worker"],
    }


def require_parent_id(explicit_id: str | None) -> str:
    pid = get_active_parent_id(explicit_id)
    if not pid:
        print("error: parent ID must be specified via --parent-id or APGR_PARENT_ID env var", file=sys.stderr)
        sys.exit(2)
    return pid


def cmd_parent_init(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    ledger = ParentLedger(pid, args.state_dir)
    existing = ledger.get_status()
    frozen = existing.get("worker_capability") or {}
    if existing.get("status") and (
        args.worker_policy and frozen.get("policy_selection") != args.worker_policy
        or args.exclude_worker_kind and sorted(args.exclude_worker_kind) != frozen.get("excluded_worker_kinds", [])
    ):
        raise ValueError("existing parent retains its frozen policy; handle its work before a fresh lifetime")
    capability = (
        None if existing.get("status")
        else parent_capability(pid, args.parent_family, args.policy_path, args.worker_policy, args.exclude_worker_kind)
    )
    custom_limits = {}
    if args.max_gemini is not None:
        custom_limits["max_gemini"] = args.max_gemini
    if args.max_aggregate is not None:
        custom_limits["max_aggregate"] = args.max_aggregate

    res = ledger.initialize_parent(
        parent_family=args.parent_family,
        workspace=args.workspace or os.getcwd(),
        task_authority=args.task_authority,
        policy_path=Path(capability["policy_source"]) if capability else args.policy_path,
        worker_capability=capability,
        custom_limits=custom_limits or None,
    )
    print(json.dumps(res, indent=2))
    return 0


def cmd_parent_status(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    ledger = ParentLedger(pid, args.state_dir)
    res = ledger.get_status()
    print(json.dumps(res, indent=2))
    return 0


def cmd_parent_inspect(args: argparse.Namespace) -> int:
    from .inspection import human, inspect_parent
    view = inspect_parent(get_active_parent_id(args.parent_id), args.state_dir, job_id=args.job_id)
    print(json.dumps(view, indent=2) if args.json else human(view))
    return 0


def cmd_parent_drain(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    ledger = ParentLedger(pid, args.state_dir)
    res = ledger.drain_and_close(timeout_seconds=args.timeout)
    print(json.dumps(res, indent=2))
    return 1 if res.get("uncertain_cleanup") else 0


def cmd_parent_pool(args: argparse.Namespace) -> int:
    ledger = ParentLedger(require_parent_id(args.parent_id), args.state_dir)
    result = (ledger.pause_pool(args.worker_kind, args.reason, args.evidence)
              if args.action == "pause-pool" else ledger.resume_pool(args.worker_kind, args.evidence))
    print(json.dumps(result, indent=2))
    return 0


def cmd_job_launch(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    task_text = args.task
    if args.task_file:
        task_text = Path(args.task_file).read_text(encoding="utf-8")
    if not task_text:
        print("error: either --task or --task-file must be provided", file=sys.stderr)
        return 2

    scopes = args.mutation_scope.split(",") if args.mutation_scope else None
    try:
        res = launch_worker_job(
            parent_id=pid,
            task=task_text,
            idempotency_key=args.key,
            task_authority=args.task_authority,
            mutation_scope=scopes,
            acceptance_criteria=args.acceptance_criteria,
            profile=args.profile,
            output_dir=args.output_dir,
            state_dir=args.state_dir,
            worker_kind=args.worker_kind,
            task_id=args.task_id,
            previous_job_id=args.previous_job_id,
            recovery_decision=args.recovery_decision,
            recovery_reason=args.recovery_reason,
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") in {"reserved", "starting", "launched", "running"} else 1
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def cmd_job_status(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    ledger = ParentLedger(pid, args.state_dir)
    try:
        job = ledger.get_job(args.job_id)
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(job, indent=2))
    return 0


def cmd_job_wait(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    try:
        res = wait_worker_job(
            parent_id=pid,
            job_id=args.job_id,
            timeout_seconds=args.timeout,
            state_dir=args.state_dir,
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "completed" or res.get("timed_out") else 1
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def cmd_job_cancel(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    try:
        if getattr(args, "reason", None):
            ParentLedger(pid, args.state_dir).record_abandonment(args.job_id, args.reason)
        res = cancel_worker_job(pid, args.job_id, state_dir=args.state_dir)
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") in {"cancelled", "completed", "failed"} else 1
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def cmd_job_list(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    ledger = ParentLedger(pid, args.state_dir)
    try:
        data = ledger._read_data()
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    jobs = list((data.get("gemini_jobs") or {}).values())
    print(json.dumps(jobs, indent=2))
    return 0


def cmd_job_outcome(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    try:
        if not args.evidence.strip():
            raise ValueError("outcome evidence must not be empty")
        result = ParentLedger(pid, args.state_dir).record_task_outcome(
            args.job_id, args.outcome, args.evidence
        )
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def cmd_native_hook(hook_fn, args: argparse.Namespace) -> int:
    pid = get_active_parent_id(args.parent_id)
    capability_digest = getattr(args, "capability_digest", None)
    if capability_digest and pid:
        state_dir = getattr(args, "state_dir", None)
        ledger = ParentLedger(pid, state_dir)
        status = ledger.get_status()
        cap = status.get("worker_capability") or {}
        expected = (
            cap.get("capability_digest")
            or cap.get("policy_sha256")
            or status.get("policy_sha256")
            or (status.get("policy") or {}).get("policy_sha256")
        )
        if expected and capability_digest != expected:
            print(f"error: capability digest mismatch: expected {expected}, got {capability_digest}", file=sys.stderr)
            return 2
    try:
        raw_in = sys.stdin.read()
    except Exception:
        raw_in = "{}"
    res = hook_fn(
        raw_in,
        parent_id=args.parent_id,
        state_dir=getattr(args, "state_dir", None),
    )
    print(json.dumps(res))
    return 0


def cmd_native_close(args: argparse.Namespace) -> int:
    pid = require_parent_id(args.parent_id)
    res = close_native_agent(pid, args.agent_id, state_dir=args.state_dir)
    print(json.dumps(res, indent=2))
    return 0 if res.get("closed") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-worker", description="Shared local agent worker facility.")
    parser.add_argument("--state-dir", type=Path, help="Override worker state directory.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # parent group
    parent_parser = subparsers.add_parser("parent")
    parent_subs = parent_parser.add_subparsers(dest="action", required=True)

    init_p = parent_subs.add_parser("init")
    init_p.add_argument("--parent-id")
    init_p.add_argument("--parent-family", required=True, choices=["codex_parent", "claude_opus", "claude_fable", "gemini_flash"])
    init_p.add_argument("--workspace")
    init_p.add_argument("--task-authority", default="mutation_capable", choices=["mutation_capable", "read_only"])
    init_p.add_argument("--policy-path", type=Path)
    init_p.add_argument("--worker-policy", choices=[TRIPLE_POOL])
    init_p.add_argument("--exclude-worker-kind", action="append", choices=["gemini", "luna", "sonnet"], default=[])
    init_p.add_argument("--max-gemini", type=int)
    init_p.add_argument("--max-aggregate", type=int)
    init_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    init_p.set_defaults(func=cmd_parent_init)

    status_p = parent_subs.add_parser("status")
    status_p.add_argument("--parent-id")
    status_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    status_p.set_defaults(func=cmd_parent_status)

    inspect_p = parent_subs.add_parser("inspect", help="immutable capability/recovery view; no reconciliation")
    inspect_p.add_argument("--parent-id")
    inspect_p.add_argument("--job-id")
    inspect_p.add_argument("--json", action="store_true")
    inspect_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    inspect_p.set_defaults(func=cmd_parent_inspect)

    drain_p = parent_subs.add_parser("drain")
    drain_p.add_argument("--parent-id")
    drain_p.add_argument("--timeout", type=float, default=15.0)
    drain_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    drain_p.set_defaults(func=cmd_parent_drain)

    close_p = parent_subs.add_parser("close")
    close_p.add_argument("--parent-id")
    close_p.add_argument("--timeout", type=float, default=15.0)
    close_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    close_p.set_defaults(func=cmd_parent_drain)

    for action in ("pause-pool", "resume-pool"):
        pool_p = parent_subs.add_parser(action)
        pool_p.add_argument("--parent-id")
        pool_p.add_argument("--worker-kind", required=True, choices=["gemini", "luna", "sonnet"])
        pool_p.add_argument("--evidence", required=True)
        if action == "pause-pool":
            pool_p.add_argument("--reason", required=True)
        pool_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
        pool_p.set_defaults(func=cmd_parent_pool)

    # job group
    job_parser = subparsers.add_parser("job")
    job_subs = job_parser.add_subparsers(dest="action", required=True)

    launch_p = job_subs.add_parser("launch")
    launch_p.add_argument("--task")
    launch_p.add_argument("--task-file", type=Path)
    launch_p.add_argument("--parent-id")
    launch_p.add_argument("--key")
    launch_p.add_argument("--task-authority", choices=["mutation_capable", "read_only"])
    launch_p.add_argument("--mutation-scope")
    launch_p.add_argument("--acceptance-criteria")
    launch_p.add_argument("--profile")
    launch_p.add_argument("--worker-kind", choices=["gemini", "luna", "sonnet"], default="gemini")
    launch_p.add_argument("--task-id")
    launch_p.add_argument("--previous-job-id")
    launch_p.add_argument("--recovery-decision", choices=["adopt", "amend", "reject", "continue"])
    launch_p.add_argument("--recovery-reason")
    launch_p.add_argument("--output-dir", type=Path)
    launch_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    launch_p.set_defaults(func=cmd_job_launch)

    status_j = job_subs.add_parser("status")
    status_j.add_argument("--job-id", required=True)
    status_j.add_argument("--parent-id")
    status_j.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    status_j.set_defaults(func=cmd_job_status)

    wait_j = job_subs.add_parser("wait")
    wait_j.add_argument("--job-id", required=True)
    wait_j.add_argument("--parent-id")
    wait_j.add_argument("--timeout", type=float)
    wait_j.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    wait_j.set_defaults(func=cmd_job_wait)

    cancel_j = job_subs.add_parser("cancel")
    cancel_j.add_argument("--job-id", required=True)
    cancel_j.add_argument("--parent-id")
    cancel_j.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    cancel_j.set_defaults(func=cmd_job_cancel)

    abandon_j = job_subs.add_parser("abandon")
    abandon_j.add_argument("--job-id", required=True)
    abandon_j.add_argument("--parent-id")
    abandon_j.add_argument("--reason", required=True)
    abandon_j.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    abandon_j.set_defaults(func=cmd_job_cancel)

    outcome_j = job_subs.add_parser("outcome")
    outcome_j.add_argument("--parent-id")
    outcome_j.add_argument("--job-id", required=True)
    outcome_j.add_argument("--outcome", required=True,
                           choices=("partial", "accepted", "rejected", "failed", "cancelled"))
    outcome_j.add_argument("--evidence", required=True)
    outcome_j.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    outcome_j.set_defaults(func=cmd_job_outcome)

    list_j = job_subs.add_parser("list")
    list_j.add_argument("--parent-id")
    list_j.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    list_j.set_defaults(func=cmd_job_list)

    # native hook group
    nat_parser = subparsers.add_parser("native")
    nat_subs = nat_parser.add_subparsers(dest="action", required=True)

    pre_tool_p = nat_subs.add_parser("pre-tool")
    pre_tool_p.add_argument("--parent-id")
    pre_tool_p.add_argument("--capability-digest")
    pre_tool_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    pre_tool_p.set_defaults(func=lambda a: cmd_native_hook(handle_native_pre_tool, a))

    post_tool_p = nat_subs.add_parser("post-tool")
    post_tool_p.add_argument("--parent-id")
    post_tool_p.add_argument("--capability-digest")
    post_tool_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    post_tool_p.set_defaults(func=lambda a: cmd_native_hook(handle_native_post_tool, a))

    start_p = nat_subs.add_parser("subagent-start")
    start_p.add_argument("--parent-id")
    start_p.add_argument("--capability-digest")
    start_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    start_p.set_defaults(func=lambda a: cmd_native_hook(handle_native_subagent_start, a))

    stop_p = nat_subs.add_parser("subagent-stop")
    stop_p.add_argument("--parent-id")
    stop_p.add_argument("--capability-digest")
    stop_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    stop_p.set_defaults(func=lambda a: cmd_native_hook(handle_native_subagent_stop, a))

    close_nat_p = nat_subs.add_parser("close")
    close_nat_p.add_argument("--agent-id", required=True)
    close_nat_p.add_argument("--parent-id")
    close_nat_p.add_argument("--state-dir", type=Path, default=argparse.SUPPRESS)
    close_nat_p.set_defaults(func=cmd_native_close)

    parsed = parser.parse_args(argv)
    try:
        parsed.state_dir = validate_inherited_context(parsed.parent_id, parsed.state_dir)
    except AuthorityViolationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return parsed.func(parsed)


if __name__ == "__main__":
    raise SystemExit(main())
