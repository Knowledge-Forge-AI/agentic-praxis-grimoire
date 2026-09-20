"""Repository-detached formatting repair for Request V2 terminal closeout responses."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Callable

from . import (
    candidate,
    finalization as finalization_module,
    gitstate as gitstate_module,
    provider as provider_module,
    result as result_module,
    result_repair as result_repair_module,
)
from .display import Display
from .dynamic_router import ResolvedActorRoute
from .persistence import record_artifact, record_invocation_attempt, utc_now_iso
from .semantic_roles import ActorBinding


def is_v2_repair_eligible(exc: BaseException, stdout_bytes: bytes, nonce: str) -> bool:
    """Verify that a terminal failure is strictly eligible for formatting repair."""
    if not isinstance(exc, result_module.ResultError):
        return False
    if exc.code in (
        "PATH_DISPOSITION_INVALID",
        "OWNERSHIP_CHALLENGE_INVALID",
        "OWNERSHIP_PROVIDER_RESOLUTION_INVALID",
    ):
        return False
    if not (exc.code.startswith("RESULT_") or exc.code.startswith("COMMIT_")):
        return False
    if result_repair_module._terminal_has_structured_authority(stdout_bytes, nonce):
        return False
    return True


def record_repair_attempt(
    conn: sqlite3.Connection,
    run_id: str,
    binding_id: str,
    attempt_number: int,
    predecessor_attempt_id: str,
    provider: str,
    profile: str,
    endpoint_alias: str,
    status: str,
    exit_code: int,
    started_at: str,
) -> None:
    """Record auxiliary formatting repair attempt into persistence."""
    record_invocation_attempt(
        conn,
        attempt_id=f"att-{run_id}-{binding_id}-repair-1",
        run_id=run_id,
        binding_id=binding_id,
        attempt_number=attempt_number,
        predecessor_attempt_id=predecessor_attempt_id,
        provider=provider,
        profile=profile,
        endpoint_alias=endpoint_alias,
        status=status,
        exit_code=exit_code,
        started_at=started_at,
        completed_at=utc_now_iso(),
        route_resolution_id=None,
        attempt_kind="auxiliary",
    )


def execute_v2_result_repair(
    *,
    conn: sqlite3.Connection,
    run_id: str,
    run_dir: Path,
    repository_root: Path,
    work_tree: Path,
    binding: ActorBinding,
    route: ResolvedActorRoute,
    endpoint: Any,
    stdout_bytes: bytes,
    stderr_bytes: bytes,
    exit_code: int,
    initial_head: str,
    tree_after: str,
    runner: Callable[..., Any],
    display: Display | None,
    original_error: result_module.ResultError,
    attempt_id: str,
    curr_attempt_number: int,
) -> tuple[result_module.StageResult, dict[str, Any]]:
    """Execute a single-shot repository-detached formatting repair invocation."""
    tree_pre = candidate.tree_identity(work_tree)["tree"]
    index_pre = gitstate_module.index_identity(work_tree)
    if tree_pre != tree_after:
        raise finalization_module.FinalizationError(
            "RESULT_REPAIR_CANDIDATE_MUTATED",
            "candidate tree changed before auxiliary repair invocation",
        )

    repair_nonce = result_module.new_nonce()
    rendered = result_repair_module._formatting_prompt("closeout", stdout_bytes, repair_nonce)

    with tempfile.TemporaryDirectory(prefix="agent-phase-result-repair-") as scratch:
        repair_cwd = Path(scratch).resolve()
        before_inv = result_repair_module._inventory(repair_cwd)
        is_inside_repo = result_repair_module._inside_repository_checkout(repair_cwd)
        if is_inside_repo or before_inv["entry_count"] != 0:
            cwd_payload = {
                "schema": result_repair_module.INVENTORY_SCHEMA,
                "working_directory": os.fspath(repair_cwd),
                "repository_checkout_present": is_inside_repo,
                "before": before_inv,
                "after": before_inv,
                "cleanup": "temporary_directory_context_exit",
            }
            cwd_bytes = (json.dumps(cwd_payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
            (run_dir / "result-repair-cwd.json").write_bytes(cwd_bytes)
            record_artifact(
                conn,
                artifact_id=f"art-{run_id}-result-repair-cwd",
                run_id=run_id,
                artifact_name="result-repair-cwd.json",
                relative_path="result-repair-cwd.json",
                size_bytes=len(cwd_bytes),
                sha256=hashlib.sha256(cwd_bytes).hexdigest(),
                content_type="application/json",
            )
            raise finalization_module.FinalizationError(
                "RESULT_REPAIR_WORKDIR_UNSAFE",
                "auxiliary provider working directory is not empty and repository-detached",
            )

        repair_start_iso = utc_now_iso()
        repair_stdout = b""
        repair_stderr = b""
        repair_exit_code = 0

        import inspect
        sig = inspect.signature(runner)
        if len(sig.parameters) >= 3 and ("binding" in sig.parameters or "run_id" in sig.parameters):
            runner_kwargs: dict[str, Any] = {
                "run_id": run_id,
                "binding": binding,
                "route": route,
                "run_dir": run_dir,
            }
            if "prompt_bytes" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                runner_kwargs["prompt_bytes"] = rendered.data
            if "nonce" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                runner_kwargs["nonce"] = repair_nonce
            if "cwd" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                runner_kwargs["cwd"] = repair_cwd
            if "read_only" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                runner_kwargs["read_only"] = True
            if "is_repair" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                runner_kwargs["is_repair"] = True
            if "invocation_kind" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                runner_kwargs["invocation_kind"] = "auxiliary_result_repair"

            try:
                res_val = runner(**runner_kwargs)
            except BaseException as run_err:
                record_repair_attempt(
                    conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                    getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                    getattr(route, "endpoint_alias", "default"), "failed", 1, repair_start_iso,
                )
                raise run_err

            if isinstance(res_val, provider_module.Result):
                repair_stdout = res_val.stdout
                repair_stderr = res_val.stderr
                repair_exit_code = res_val.exit_code
            elif isinstance(res_val, tuple) and len(res_val) >= 3:
                repair_exit_code, repair_stdout, repair_stderr = res_val[:3]
                if isinstance(repair_stdout, str):
                    repair_stdout = repair_stdout.encode("utf-8")
                if isinstance(repair_stderr, str):
                    repair_stderr = repair_stderr.encode("utf-8")
            elif isinstance(res_val, (bytes, str)):
                repair_stdout = res_val if isinstance(res_val, bytes) else res_val.encode("utf-8")
                repair_exit_code = 0
            else:
                record_repair_attempt(
                    conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                    getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                    getattr(route, "endpoint_alias", "default"), "failed", 1, repair_start_iso,
                )
                type_name = "None" if res_val is None else type(res_val).__name__
                raise finalization_module.FinalizationError(
                    "RESULT_REPAIR_TRANSPORT_INVALID",
                    f"auxiliary repair runner returned unsupported result: {type_name}",
                )
        else:
            repair_argv = (
                provider_module.build_argv(
                    endpoint,
                    "reviewer",
                    repository_root,
                    read_only=True,
                )
                if endpoint is not None
                else ["mock-provider", getattr(route, "endpoint_alias", "default")]
            )
            notice_kwargs: dict[str, Any] = {}
            if runner is provider_module.run and display is not None and hasattr(display, "stage_notice"):
                notice_kwargs["on_notice"] = display.stage_notice
            try:
                res = runner(
                    repair_argv,
                    rendered.data,
                    repair_cwd,
                    provider_module.MAX_STAGE_OUTPUT_BYTES,
                    display.stage_output if (display and hasattr(display, "stage_output")) else None,
                    **notice_kwargs,
                )
                repair_stdout = res.stdout
                repair_stderr = res.stderr
                repair_exit_code = res.exit_code
            except BaseException as run_err:
                record_repair_attempt(
                    conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                    getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                    getattr(route, "endpoint_alias", "default"), "failed", 1, repair_start_iso,
                )
                raise run_err

        after_inv = result_repair_module._inventory(repair_cwd)
        cwd_payload = {
            "schema": result_repair_module.INVENTORY_SCHEMA,
            "working_directory": os.fspath(repair_cwd),
            "repository_checkout_present": is_inside_repo,
            "before": before_inv,
            "after": after_inv,
            "cleanup": "temporary_directory_context_exit",
        }
        cwd_bytes = (json.dumps(cwd_payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (run_dir / "result-repair-cwd.json").write_bytes(cwd_bytes)
        record_artifact(
            conn,
            artifact_id=f"art-{run_id}-result-repair-cwd",
            run_id=run_id,
            artifact_name="result-repair-cwd.json",
            relative_path="result-repair-cwd.json",
            size_bytes=len(cwd_bytes),
            sha256=hashlib.sha256(cwd_bytes).hexdigest(),
            content_type="application/json",
        )

        if after_inv["entry_count"] != 0:
            record_repair_attempt(
                conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                getattr(route, "endpoint_alias", "default"), "failed", repair_exit_code, repair_start_iso,
            )
            raise finalization_module.FinalizationError(
                "RESULT_REPAIR_SIDE_EFFECT",
                "auxiliary provider created an unexpected working-directory node",
            )

        tree_post = candidate.tree_identity(work_tree)["tree"]
        index_post = gitstate_module.index_identity(work_tree)
        if tree_post != tree_pre:
            record_repair_attempt(
                conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                getattr(route, "endpoint_alias", "default"), "failed", repair_exit_code, repair_start_iso,
            )
            raise finalization_module.FinalizationError(
                "RESULT_REPAIR_CANDIDATE_MUTATED",
                "auxiliary result repair changed the candidate tree",
            )
        if index_post != index_pre:
            record_repair_attempt(
                conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                getattr(route, "endpoint_alias", "default"), "failed", repair_exit_code, repair_start_iso,
            )
            raise finalization_module.FinalizationError(
                "RESULT_REPAIR_INDEX_MUTATED",
                "auxiliary result repair changed the real index",
            )

        if repair_exit_code != 0:
            record_repair_attempt(
                conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                getattr(route, "endpoint_alias", "default"), "failed", repair_exit_code, repair_start_iso,
            )
            raise finalization_module.FinalizationError(
                "RESULT_REPAIR_TRANSPORT_INVALID",
                f"auxiliary repair provider exited with code {repair_exit_code}",
            )

        try:
            parsed = result_module.parse(repair_stdout, "closeout", repair_nonce)
        except result_module.ResultError as parse_err:
            record_repair_attempt(
                conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                getattr(route, "endpoint_alias", "default"), "failed", repair_exit_code, repair_start_iso,
            )
            raise parse_err

        if parsed.ownership_resolutions:
            record_repair_attempt(
                conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                getattr(route, "endpoint_alias", "default"), "failed", repair_exit_code, repair_start_iso,
            )
            raise finalization_module.FinalizationError(
                "OWNERSHIP_CHALLENGE_INVALID",
                "formatting repair cannot resolve ownership challenges",
            )
        if parsed.path_dispositions:
            record_repair_attempt(
                conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                getattr(route, "endpoint_alias", "default"), "failed", repair_exit_code, repair_start_iso,
            )
            raise finalization_module.FinalizationError(
                "PATH_DISPOSITION_INVALID",
                "formatting repair cannot introduce path ownership",
            )
        if not parsed.completed:
            record_repair_attempt(
                conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
                getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
                getattr(route, "endpoint_alias", "default"), "failed", repair_exit_code, repair_start_iso,
            )
            raise finalization_module.FinalizationError(
                "RESULT_REPAIR_FAILED",
                f"auxiliary repair returned non-completed outcome: {parsed.outcome}",
            )

        record_repair_attempt(
            conn, run_id, binding.binding_id, curr_attempt_number + 1, attempt_id,
            getattr(route, "provider", "unknown"), getattr(route, "profile", "unknown"),
            getattr(route, "endpoint_alias", "default"), "completed", 0, repair_start_iso,
        )

        repair_evidence = {
            "operation": result_repair_module.OPERATION,
            "one_shot": True,
            "semantic_work_replayed": False,
            "source_attempt_id": attempt_id,
            "source_binding_id": binding.binding_id,
            "source_provider": getattr(route, "provider", "unknown"),
            "source_profile": getattr(route, "profile", "unknown"),
            "source_endpoint": getattr(route, "endpoint_alias", "default"),
            "source_result_blocker": original_error.code,
            "source_stdout_sha256": hashlib.sha256(stdout_bytes).hexdigest(),
            "source_stdout_bytes": len(stdout_bytes),
            "repair_invocation_count": 1,
            "repair_provider": getattr(route, "provider", "unknown"),
            "repair_profile": getattr(route, "profile", "unknown"),
            "fresh_nonce_digest": hashlib.sha256(repair_nonce.encode("utf-8")).hexdigest(),
            "isolated_working_directory": os.fspath(repair_cwd),
            "repair_transport_status": "succeeded",
            "strict_parse_outcome": parsed.outcome,
            "final_semantic_result": parsed.outcome,
            "candidate_tree_before": tree_pre,
            "candidate_tree_after": tree_post,
            "candidate_tree_identical": tree_pre == tree_post,
            "no_side_effect_truth": True,
        }
        rep_bytes = (json.dumps(repair_evidence, indent=2, sort_keys=True) + "\n").encode("utf-8")
        (run_dir / "result-repair.json").write_bytes(rep_bytes)
        record_artifact(
            conn,
            artifact_id=f"art-{run_id}-result-repair",
            run_id=run_id,
            artifact_name="result-repair.json",
            relative_path="result-repair.json",
            size_bytes=len(rep_bytes),
            sha256=hashlib.sha256(rep_bytes).hexdigest(),
            content_type="application/json",
        )

        c_bytes = (json.dumps(parsed.as_dict(), indent=2, sort_keys=True) + "\n").encode("utf-8")
        (run_dir / "closeout.result.json").write_bytes(c_bytes)
        record_artifact(
            conn,
            artifact_id=f"art-{run_id}-closeout-result",
            run_id=run_id,
            artifact_name="closeout.result.json",
            relative_path="closeout.result.json",
            size_bytes=len(c_bytes),
            sha256=hashlib.sha256(c_bytes).hexdigest(),
            content_type="application/json",
        )

        return parsed, repair_evidence
