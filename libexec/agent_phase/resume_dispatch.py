"""Provider suffix execution for a validated resume plan."""

from __future__ import annotations

from dataclasses import dataclass, replace
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from . import route_provenance

from . import archive as archive_module
from . import antigravity_output_recovery as output_recovery_module
from . import candidate as candidate_module
from . import capacity as capacity_module
from . import envelope as envelope_module
from . import finalization as finalization_module
from . import failure_boundary as failure_boundary_module
from . import gitstate as gitstate_module
from . import lifecycle_dispatch as lifecycle_dispatch_module
from . import prompt_policy as prompt_policy_module
from . import provider as provider_module
from . import result as result_module
from . import result_artifacts as result_artifacts_module
from . import result_repair as result_repair_module
from . import review_result as review_result_module
from . import resume as resume_module
from .result_repair import qualify as qualify_result_repair
from .result_repair import start as start_result_repair
from . import run as run_module
from .publication import record as push_record
from .routing import Endpoint, load_validated_roster, resolve, route
from . import stage_delta as stage_delta_module
from .transport import PromptLimitError

def _inert_result_markers(text: str) -> str:
    """Neutralize retained dispatcher fences before forwarding failed output."""
    return text.replace(
        "<<<AGENT-PHASE-RESULT", "[inert phase-result marker"
    ).replace(
        "<<<END-AGENT-PHASE-RESULT", "[inert end phase-result marker"
    )

def _initial_state(dispatcher: Any, directory: Any, project: str, phase_id: str,
                   request: Any, plan: resume_module.ResumePlan, dry_run: bool):
    from .worker_recovery import verify_pending_cleanup, verify_retained_cleanup

    try:
        verify_retained_cleanup(plan.source, plan.source_state)
        worker_cleanup_reconciled = verify_pending_cleanup(plan.source, plan.source_state)
    except ValueError as error:
        raise resume_module.ResumeError("WORKER_CLEANUP_FAILED", str(error)) from error
    inherited_stages = list(plan.inherited_stages)
    inherited_checkpoints = list(plan.inherited_checkpoints)
    inherited_invoked = plan.source_state.get("stages_invoked")
    if not isinstance(inherited_invoked, list):
        inherited_invoked = inherited_stages.copy()
    inherited_transports = plan.source_state.get("stage_transports_completed")
    if not isinstance(inherited_transports, list):
        inherited_transports = inherited_stages.copy()
    terminal = plan.lifecycle.terminal_result_stage
    terminal_validated = bool(
        plan.source_state.get("terminal_result_validated")
        or (terminal in inherited_stages and plan.closeout_result is not None)
    )
    state = {
        "run_layout": dict(directory.run_layout),
        "source_controller_generation": plan.source_state.get("controller_generation"),
        "worker_cleanup_reconciled": worker_cleanup_reconciled,
        "run_id": directory.run_id, "project": project, "phase_id": phase_id,
        "run_directory": str(directory.path), "dry_run": dry_run, "resumed": True,
        "phase_type": request.phase_type, "execution_mode": request.execution_mode,
        "lifecycle": plan.lifecycle.name,
        "finalization_policy": dispatcher.finalization_policy,
        "expected_stages": list(plan.lifecycle.stage_names),
        "expected_provider_invocations": plan.lifecycle.expected_provider_invocations,
        "expected_review_count": plan.lifecycle.expected_review_count,
        "terminal_result_stage": plan.lifecycle.terminal_result_stage,
        "cwd": str(dispatcher.cwd),
        "checkpoints_completed": inherited_checkpoints.copy(),
        "effective_checkpoints": inherited_checkpoints.copy(),
        "stage_accounting_schema": result_artifacts_module.STAGE_ACCOUNTING_SCHEMA,
        "stages_invoked": inherited_invoked.copy(),
        "stage_transports_completed": inherited_transports.copy(),
        "terminal_result_validated": terminal_validated,
        "stages_completed": inherited_stages.copy(),
        "effective_stages": {stage: "inherited" for stage in inherited_stages},
        "effective_stage_routes": dict(plan.effective_stage_routes),
        "route_transition": plan.route_transition,
        "entry": plan.current_entry.as_dict(), "final_head": plan.current_head,
        "phase_delta": [],
        "commit": plan.source_state.get("commit") if plan.from_stage == "finalize" else None,
        "push": push_record(), "archive_path": str(directory.archive_path),
        "archive": archive_module.record(directory.archive_path),
        "prompt_policy": {
            "policy_version": prompt_policy_module.POLICY_VERSION,
            "sanitized": False, "total_removal_count": 0,
            "evidence_artifact": "prompt-policy.json",
        },
        "provider_outcomes": {},
        "review_recoveries": {
            stage: recovery for stage, recovery in plan.source_state.get("review_recoveries", {}).items()
            if stage in inherited_stages
        },
        "auxiliary_provider_invocations_inherited": sum(
            1 for stage in inherited_stages
            if (plan.source / f"{plan.lifecycle.prefixes[stage]}.recovery.json").is_file()
        ),
        "review_outcomes": dict(plan.source_state.get("review_outcomes", {})),
        "final_review": plan.source_state.get(
            "final_review",
            (plan.source_state.get("review_outcomes", {}) or {}).get("final_review")
            if isinstance(plan.source_state.get("review_outcomes", {}), dict)
            else None,
        ),
        "review_artifacts": list(
            plan.source_state.get("review_artifacts", [])
            if isinstance(plan.source_state.get("review_artifacts", []), list)
            else []
        ),
        "review_artifact_names": list(
            plan.source_state.get("review_artifact_names", [])
            if isinstance(plan.source_state.get("review_artifact_names", []), list)
            else []
        ),
        "review_artifact_outcomes": dict(
            plan.source_state.get("review_artifact_outcomes", {})
            if isinstance(plan.source_state.get("review_artifact_outcomes", {}), dict)
            else {}
        ),
        "provider_invocations_inherited": len(inherited_stages),
        "provider_invocations_performed": 0,
        "manager_disposition_required": False,
        "proposed_commit_message": plan.source_state.get("proposed_commit_message"),
        "terminal_candidate": plan.source_state.get("terminal_candidate"),
        "candidate_manifest": plan.candidate_manifest,
        "path_ownership": plan.source_state.get("path_ownership"),
        "ownership_challenges": deepcopy(plan.source_state.get("ownership_challenges")),
        "adoption": plan.source_state.get("adoption"),
        "inherited_candidate_manifest": plan.candidate_manifest,
        "phase_owned_paths": sorted(plan.candidate_manifest["paths"]),
        "resume_boundary": plan.boundary_facts,
        "evidence_boundary_skew": plan.evidence_boundary_skew,
        "review_boundaries": {},
        **{
            stage.candidate_key: plan.source_state.get(stage.candidate_key)
            for stage in plan.lifecycle.stages
            if stage.candidate_key is not None
        },
        "plan_candidate": plan.source_state.get("plan_candidate"),
        "proposal_binding": plan.source_state.get(
            "proposal_binding", plan.source_state.get("plan_candidate")
        ),
        "plan_proposal_binding": plan.source_state.get(
            "plan_proposal_binding", plan.source_state.get("plan_candidate")
        ),
        "producer_binding": plan.source_state.get(
            "producer_binding",
            plan.source_state.get(
                "work_product_binding",
                plan.source_state.get(
                    "produced_candidate",
                    plan.source_state.get(
                        "pre_final_candidate",
                        plan.source_state.get("produce_close_candidate"),
                    ),
                ),
            ),
        ),
        "work_product_binding": plan.source_state.get(
            "work_product_binding",
            plan.source_state.get(
                "producer_binding",
                plan.source_state.get(
                    "produced_candidate",
                    plan.source_state.get(
                        "pre_final_candidate",
                        plan.source_state.get("produce_close_candidate"),
                    ),
                ),
            ),
        ),
        "revisor_input": plan.source_state.get("revisor_input"),
        "authorized_revisor_revisions": plan.source_state.get(
            "authorized_revisor_revisions"
        ),
        "revisor_revisions": plan.source_state.get("revisor_revisions"),
        "revisor_binding": plan.source_state.get(
            "revisor_binding",
            plan.source_state.get(
                "revisor_candidate",
                plan.source_state.get(
                    "revise_close_candidate",
                    plan.source_state.get(
                        "closeout_candidate",
                        plan.source_state.get("produce_close_candidate"),
                    ),
                ),
            ),
        ),
        "post_revisor_review": plan.source_state.get(
            "post_revisor_review",
            {
                "performed": False,
                "automatic": False,
                "reason": "selected lifecycle has no post-revisor independent review",
            },
        ),
        "outcome": None,
        "semantic_outcome": plan.source_state.get("semantic_outcome") if plan.from_stage == "finalize" else None,
        "finalization_attempted": False,
        "finalization_outcome": "not_attempted",
        "blocking_reason": None,
        "complete": False,
        "shadow": dispatcher._shadow_state(),
    }
    if isinstance(plan.source_state.get("stage_delta_ledger"), dict):
        state["stage_delta_ledger"] = plan.source_state["stage_delta_ledger"]
    elif isinstance(plan.source_state.get("stage_delta_record"), dict):
        state["stage_delta_ledger"] = plan.source_state["stage_delta_record"]
    else:
        state["stage_delta_ledger"] = {
            "schema": stage_delta_module.STAGE_DELTA_SCHEMA,
            "deltas": [],
            "stages": {},
        }
    state["_previous_operational_metadata"] = stage_delta_module.scan_operational_metadata(dispatcher.cwd)
    state["index_normalizations"] = list(plan.source_state.get("index_normalizations", []))
    if plan.output_recovery is not None:
        recovered_stage = plan.lifecycle.stage_names[0]
        state["stages_invoked"] = [recovered_stage]
        state["stage_transports_completed"] = [recovered_stage]
        state["stages_completed"] = [recovered_stage]
        state["effective_stages"] = {recovered_stage: "recovered"}
        state["stage_transport_outcomes"] = {
            recovered_stage: {
                "stage": recovered_stage,
                "status": "recovered",
                "provider_invocation_performed": False,
            }
        }
        state["produced_candidate"] = plan.recovered_candidate
        state["antigravity_output_recovery"] = plan.output_recovery
        state["source_artifacts_verified"] = True
        state["source_archive_verified"] = True
    return state


def _record_failure(dispatcher: Any, directory: Any, state: dict[str, Any],
                    plan: resume_module.ResumePlan, root: Any, error: BaseException) -> None:
    state["complete"] = False
    state["outcome"] = "blocked"
    if state.get("semantic_outcome") is None:
        state["semantic_outcome"] = "blocked"
    if state.get("finalization_outcome") is None or state.get("finalization_outcome") == "not_attempted":
        if state.get("finalization_attempted"):
            state["finalization_outcome"] = "blocked"
        else:
            state["finalization_outcome"] = "not_attempted"
    state["blocking_reason"] = {
        "code": getattr(error, "code", type(error).__name__),
        "detail": getattr(error, "detail", str(error)),
    }
    dispatcher._update_invocation_accounting(state)
    if "resume" in state:
        state["resume"]["provider_invocations_performed"] = state.get(
            "provider_invocations_performed", 0
        )
        state["resume"]["auxiliary_provider_invocations_performed"] = state.get(
            "auxiliary_provider_invocations_performed", 0
        )
        directory.write_json("resume.json", state["resume"])
    try:
        failure_boundary_module.capture_mutating_boundary(
            dispatcher, state, plan.current_entry, plan.lifecycle
        )
    except failure_boundary_module.FailureBoundaryError as capture_error:
        state["failure_candidate_capture"] = {
            "status": "failed",
            "code": capture_error.code,
            "detail": capture_error.detail,
        }
        if capture_error.code == "ENTRY_DIRT_OVERLAP":
            if state.get("blocking_reason") is None:
                state["blocking_reason"] = {
                    "code": capture_error.code,
                    "detail": capture_error.detail,
                }
    try:
        dispatcher._finalize(directory, state)
    except (archive_module.ArchiveError, OSError):
        dispatcher.display.finished(state, directory.path)


def start(
    dispatcher: Any,
    phase_id: str,
    request: Any,
    source: Any,
    from_stage: str,
    *,
    lifecycle: str | None,
    finalization_policy: str | None,
    dry_run: bool,
    result_repair_commit_subject: str | None = None,
    result_repair_commit_body_file: Path | None = None,
) -> dict[str, Any]:
    """Preflight, create, and finish one standalone resumed attempt."""
    authority_requested = (
        result_repair_commit_subject is not None
        or result_repair_commit_body_file is not None
    )
    if authority_requested and (
        from_stage != result_repair_module.OPERATION
        or finalization_policy
        not in (
            result_repair_module.FINALIZATION_COMMIT_LOCAL,
            result_repair_module.FINALIZATION_PUBLISH,
        )
    ):
        raise resume_module.ResumeError(
            "RESULT_REPAIR_COMMIT_AUTHORITY_SCOPE",
            "operator commit-message authority requires explicit result-repair and an explicit commit-local or publish finalization",
        )
    commit_authority = result_repair_module.authority_module.load(
        result_repair_commit_subject,
        result_repair_commit_body_file,
    )
    repair_plan = qualify_result_repair(
        dispatcher,
        phase_id,
        request,
        source,
        from_stage,
        lifecycle,
        finalization_policy,
        commit_authority,
    )
    if repair_plan is not None:
        return start_result_repair(
            dispatcher,
            phase_id,
            request,
            repair_plan,
            dry_run=dry_run,
        )
    candidate_module.require_worktree(dispatcher.cwd)
    root = gitstate_module.repository_root(dispatcher.cwd)
    project = run_module.project_name(root)
    run_module.safe_component(phase_id, "phase id")
    plan = output_recovery_module.qualify(
        dispatcher,
        phase_id,
        request,
        source,
        from_stage,
        root,
        project,
    )
    if plan is None:
        plan = resume_module.preflight(
            source, from_stage, phase_id, request, root, project, None,
            expected_lifecycle=lifecycle,
            check_route=False,
        )
    source_policy = str(plan.source_state.get("finalization_policy", "publish"))
    target_policy = finalization_policy or source_policy
    if plan.from_stage == "finalize":
        finalization_module.validate_transition(source_policy, target_policy)
    dispatcher.lifecycle = plan.lifecycle
    dispatcher.finalization_policy = target_policy
    roster = (
        None
        if plan.from_stage == "finalize"
        else load_validated_roster(dispatcher.root)
    )
    current_resolved = (
        None
        if roster is None
        else resolve(
            request,
            dispatcher.root,
            plan.lifecycle.name,
            target_policy,
            roster=roster,
        )
    )
    if current_resolved is not None and plan.output_recovery is not None:
        output_recovery_module.verify_remaining_route(plan, current_resolved)
        remaining = tuple(plan.lifecycle.stage_names[1:])
        effective_routes = route_provenance.compose_effective_stage_routes(
            plan.source_resolved,
            current_resolved,
            plan.lifecycle,
            plan.inherited_stages,
            remaining,
            plan.source_state["run_id"],
        )
        route_transition = route_provenance.build_route_transition(
            plan.source_resolved,
            current_resolved,
            plan.lifecycle,
            plan.inherited_stages,
            remaining,
        )
        plan = replace(
            plan,
            effective_stage_routes=effective_routes,
            route_transition=route_transition,
        )
    elif current_resolved is not None:
        plan = resume_module.preflight(
            source,
            from_stage,
            phase_id,
            request,
            root,
            project,
            current_resolved,
            expected_lifecycle=plan.lifecycle.name,
        )
    dispatcher.invocations = []
    dispatcher.provider_evidence = [
        record
        for record in plan.source_state.get("provider_evidence", [])
        if record.get("stage") in plan.inherited_stages
    ]
    dispatcher.telemetry_failures = []
    dispatcher.scan_rows = []
    dispatcher.prompt_policy_segments = []
    dispatcher._active_stage = None
    endpoints = (
        {}
        if roster is None
        else route(
            request, plan.lifecycle, root=dispatcher.root, roster=roster
        )
    )
    directory = run_module.RunDirectory(dispatcher.run_root, project, phase_id)
    effective_routes = {
        k: {**v, "route_selecting_run_id": directory.run_id} if v.get("source") == "current" else dict(v)
        for k, v in plan.effective_stage_routes.items()
    }
    plan = replace(plan, effective_stage_routes=effective_routes)
    resolved = {
        **(plan.source_resolved if current_resolved is None else current_resolved),
        "schema": route_provenance.RESOLVED_V6,
        "finalization_policy": target_policy,
        "effective_stage_routes": effective_routes,
        "route_transition": plan.route_transition,
    }
    dispatcher.display.run_started(
        project, phase_id, request.phase_type, request.execution_mode,
        endpoints, dry_run=dry_run,
        lifecycle=plan.lifecycle.name,
        finalization_policy=target_policy,
        review_count=plan.lifecycle.expected_review_count,
    )
    state = _initial_state(
        dispatcher, directory, project, phase_id, request, plan, dry_run
    )
    dispatcher._adoption = state.get("adoption")
    if dispatcher._adoption is not None:
        directory.write_json("adoption.json", dispatcher._adoption)
    dispatcher._bind_stage_accounting(state, directory, entry=plan.current_entry)
    try:
        dispatcher.display.artifacts(directory.path)
        directory.write_json("request.json", request.as_dict())
        directory.write_json("resolved.json", resolved)
        directory.write_json("entry-evidence.json", {
            **plan.current_entry.as_dict(), "dirty": plan.current_entry.dirty,
        })
        copied = resume_module.copy_inherited(plan, directory.path)
        output_recovery_module.materialize(plan, directory)
        state["resume"] = resume_module.provenance(plan, copied)
        if plan.output_recovery is not None:
            state["antigravity_output_recovery"] = plan.output_recovery
        directory.write_json("resume.json", state["resume"])
        directory.write_json("state.json", state)
        if dry_run:
            if plan.from_stage == "finalize":
                state["terminal_prompt_preflight"] = {
                    "status": "not_applicable",
                    "reason": "finalize-only resume invokes zero providers",
                    "placeholders_persisted": False,
                }
            else:
                task_prompt = dispatcher._sanitize(
                    directory, state, "request.prompt", request.prompt
                )
                try:
                    capacity, dispatcher.stage_output_limits = (
                        capacity_module.preflight_lifecycle_capacity(
                            dispatcher,
                            request,
                            directory.run_id,
                            task_prompt,
                            endpoints,
                        )
                    )
                except PromptLimitError as error:
                    from .dispatch import DispatchError
                    raise DispatchError(
                        str(error), "PROVIDER_PROMPT_LIMIT"
                    ) from error
                state["terminal_prompt_preflight"] = capacity
            state["outcome"] = "dry_run"
            state["archive"] = {
                "attempted": False, "path": str(directory.archive_path),
                "status": "not-attempted", "succeeded": False, "failure": None,
            }
            directory.write_json("state.json", state)
            dispatcher.display.finished(state, directory.path)
            return state
        result = execute(dispatcher, request, directory, state, plan, endpoints)
        archive_error = dispatcher._finalize(directory, result)
        if archive_error is not None:
            result["_finalized"] = True
            raise archive_error
        return result
    except BaseException as error:
        if state.pop("_finalized", False):
            raise
        _record_failure(dispatcher, directory, state, plan, root, error)
        raise


def _source_stdout(plan: resume_module.ResumePlan, stage: str) -> bytes:
    if stage in plan.recovered_outputs:
        return plan.recovered_outputs[stage]
    raw = (plan.source / f"{plan.lifecycle.prefixes[stage]}.stdout.md").read_bytes()
    if stage == envelope_module.STAGE_PLAN:
        binding = plan.source_state.get("plan_candidate")
        if (
            isinstance(binding, dict)
            and binding.get("schema") == "agent-phase-plan-material-v1"
        ):
            try:
                from . import plan_material as plan_material_module

                return plan_material_module.verify(plan.source, binding)
            except (OSError, candidate_module.CandidateError) as error:
                raise finalization_module.FinalizationError(
                    "RESUME_ARTIFACT_MISMATCH",
                    f"plan material artifact disagrees: {error}",
                ) from error
    return raw


def _source_review_body(plan: resume_module.ResumePlan, stage: str) -> bytes:
    path = plan.source / f"{plan.lifecycle.prefixes[stage]}.result.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    return str(value["body"]).encode("utf-8")


def _review_binding(
    context: _Execution,
    stage: str,
    binding: dict[str, Any],
) -> dict[str, Any]:
    """Expose scoped ownership evidence to a reviewer without changing meta binding."""
    context.state.setdefault("review_boundaries", {})[stage] = {
        "schema": "agent-phase-review-boundary-v1",
        "candidate": binding,
        "candidate_binding": binding,
        "candidate_manifest": context.state.get("candidate_manifest"),
        "resume_boundary": context.state.get("resume_boundary"),
    }
    return {
        **binding,
        "candidate_binding": binding,
        "candidate_manifest": context.state.get("candidate_manifest"),
        "resume_boundary": context.state.get("resume_boundary"),
    }


def _verify_recovery_boundary(context: _Execution) -> None:
    if context.plan.output_recovery is None:
        return
    output_recovery_module.verify_source_unchanged(context.plan)
    output_recovery_module.verify_live_candidate(
        context.plan, context.dispatcher.cwd
    )


@dataclass
class _Execution:
    dispatcher: Any
    request: Any
    directory: Any
    state: dict[str, Any]
    plan: resume_module.ResumePlan
    endpoints: dict[str, Endpoint]
    task_prompt: str
    performed: set[str]

    def done(self, stage: str) -> None:
        if stage not in self.state["stages_completed"]:
            self.state["stages_completed"].append(stage)
        self.state["effective_stages"][stage] = "performed"
        self.dispatcher._update_invocation_accounting(self.state)
        for key in (
            "provider_invocations_performed",
            "semantic_provider_invocations_performed",
            "auxiliary_provider_invocations",
            "auxiliary_provider_invocations_performed",
            "provider_invocations_effective",
            "total_effective_provider_turns",
        ):
            self.state["resume"][key] = self.state[key]
        self.state["shadow"] = self.dispatcher._shadow_state()
        self.directory.write_json("resume.json", self.state["resume"])
        self.directory.write_json("state.json", self.state)


def _plan_output(context: _Execution) -> bytes:
    stage = context.plan.lifecycle.stage(envelope_module.STAGE_PLAN)
    if envelope_module.STAGE_PLAN not in context.performed:
        context.state["plan_candidate"] = context.plan.source_state.get("plan_candidate")
        return _source_stdout(context.plan, envelope_module.STAGE_PLAN)
    read_only_tree = candidate_module.tree_identity(context.dispatcher.cwd)
    rendered = context.dispatcher.plan_prompt(
        context.request, context.directory.run_id, context.task_prompt
    )
    result, _ = context.dispatcher._stage(
        context.directory, 1, stage.name, stage.prefix, stage.role,
        context.endpoints[envelope_module.STAGE_PLAN], rendered, None,
        read_only=stage.process_read_only,
    )
    lifecycle_dispatch_module.require_unchanged(
        context.dispatcher,
        context.state,
        read_only_tree,
        stage.name,
        context.plan.current_entry.index_identity,
    )
    endpoint = context.endpoints[envelope_module.STAGE_PLAN]
    material = lifecycle_dispatch_module.materialize_plan(
        context.directory,
        result.stdout,
        endpoint.provider,
        endpoint.profile,
    )
    context.state["plan_candidate"] = material.binding
    context.done(envelope_module.STAGE_PLAN)
    return material.data


def _plan_review_output(context: _Execution, plan_stdout: bytes) -> bytes:
    stage = context.plan.lifecycle.stage(envelope_module.STAGE_PLAN_REVIEW)
    if envelope_module.STAGE_PLAN_REVIEW not in context.performed:
        return _source_review_body(context.plan, envelope_module.STAGE_PLAN_REVIEW)
    binding = context.state["plan_candidate"]
    read_only_tree = candidate_module.tree_identity(context.dispatcher.cwd)
    nonce = review_result_module.new_nonce()
    review_binding = _review_binding(context, stage.name, binding)
    rendered = context.dispatcher.review_prompt(
        envelope_module.STAGE_PLAN_REVIEW, context.request, context.directory.run_id,
        review_binding, plan_stdout,
        context.task_prompt,
        review_result_module.contract(stage.name, nonce),
    )
    result, _ = context.dispatcher._stage(
        context.directory, 2, stage.name, stage.prefix,
        stage.role, context.endpoints[envelope_module.STAGE_PLAN_REVIEW],
        rendered, binding,
        read_only=stage.process_read_only,
    )
    lifecycle_dispatch_module.require_unchanged(
        context.dispatcher,
        context.state,
        read_only_tree,
        stage.name,
        context.plan.current_entry.index_identity,
    )
    parsed = lifecycle_dispatch_module.complete_review(
        context.dispatcher, context.directory, context.state, stage, result,
        nonce, resumed=True,
    )
    context.done(envelope_module.STAGE_PLAN_REVIEW)
    return parsed.body.encode("utf-8")


def _work_output(context: _Execution, plan_stdout: bytes, review_stdout: bytes) -> bytes:
    stage = context.plan.lifecycle.stage(envelope_module.STAGE_WORK)
    if envelope_module.STAGE_WORK not in context.performed:
        context.state["pre_final_candidate"] = context.plan.source_state.get(
            "pre_final_candidate"
        )
        context.state["producer_binding"] = context.state["pre_final_candidate"]
        context.state["work_product_binding"] = context.state["pre_final_candidate"]
        context.state["producer_candidate"] = context.state["pre_final_candidate"]
        return _source_stdout(context.plan, envelope_module.STAGE_WORK)
    forwarded_review = context.dispatcher._sanitize(
        context.directory, context.state, "plan_review.stdout.forwarded_to_work",
        review_stdout.decode("utf-8", "replace"),
    )
    materials = [
        (
            "Plan proposal binding (dispatcher-owned exact bytes)",
            lifecycle_dispatch_module._binding_text(
                context.state["plan_candidate"]
            ),
        ),
        (
            "Planner proposal — exact bound bytes, to be dispositioned",
            plan_stdout,
        ),
        ("Independent plan review findings", forwarded_review),
        ("Prior stage-delta summary (dispatcher-owned evidence)",
         stage_delta_module.format_stage_deltas_summary(context.state)),
    ]
    failure_candidate = context.plan.source_state.get("failure_candidate") or {}
    failed_work = context.plan.source / f"{stage.prefix}.stdout.md"
    if failure_candidate.get("stage") == "work" and failed_work.is_file():
        interrupted = context.dispatcher._sanitize(
            context.directory, context.state, "failed_work.stdout.context",
            failed_work.read_text(encoding="utf-8", errors="replace"),
        )
        materials.append((
            "Prior interrupted work output (non-authoritative context)", interrupted
        ))
    rendered = context.dispatcher.continuation_prompt(
        envelope_module.STAGE_WORK, context.request, context.directory.run_id,
        envelope_module.WORK_ENVELOPE, materials, include_task_prompt=True,
        task_prompt=context.task_prompt,
    )
    result, _ = context.dispatcher._stage(
        context.directory, 3, stage.name, stage.prefix, stage.role,
        context.endpoints[envelope_module.STAGE_WORK], rendered, None,
        read_only=stage.process_read_only,
    )
    context.state["pre_final_candidate"] = candidate_module.tree_identity(
        context.dispatcher.cwd
    )
    context.state["producer_binding"] = context.state["pre_final_candidate"]
    context.state["work_product_binding"] = context.state["pre_final_candidate"]
    context.state["producer_candidate"] = context.state["pre_final_candidate"]
    context.done(envelope_module.STAGE_WORK)
    return result.stdout


def _final_review_output(context: _Execution, work_stdout: bytes) -> bytes:
    stage = context.plan.lifecycle.stage(envelope_module.STAGE_FINAL_REVIEW)
    if envelope_module.STAGE_FINAL_REVIEW not in context.performed:
        return _source_review_body(context.plan, envelope_module.STAGE_FINAL_REVIEW)
    pre_final = context.state["pre_final_candidate"]
    nonce = review_result_module.new_nonce()
    review_binding = _review_binding(context, stage.name, pre_final)
    rendered, prompt_decision = capacity_module.fit_optional_narrative(
        stage.name,
        context.endpoints[stage.name],
        lambda material: context.dispatcher.review_prompt(
            envelope_module.STAGE_FINAL_REVIEW,
            context.request,
            context.directory.run_id,
            review_binding,
            material,
            context.task_prompt,
            review_result_module.contract(stage.name, nonce),
        ),
        work_stdout,
        source_stage=envelope_module.STAGE_WORK,
        artifact_basename=(
            f"{context.plan.lifecycle.prefixes[envelope_module.STAGE_WORK]}.stdout.md"
        ),
        artifact_bytes=work_stdout,
        mandatory_sources=("original_scope", "candidate_binding", "review_contract"),
    )
    context.state.setdefault("prompt_capacity_decisions", []).append(
        prompt_decision
    )
    result, _ = context.dispatcher._stage(
        context.directory, 4, stage.name, stage.prefix,
        stage.role, context.endpoints[envelope_module.STAGE_FINAL_REVIEW],
        rendered, pre_final, read_only=stage.process_read_only,
    )
    lifecycle_dispatch_module.require_unchanged(
        context.dispatcher,
        context.state,
        pre_final,
        stage.name,
        context.plan.current_entry.index_identity,
        "REVIEW_MUTATED_CANDIDATE",
    )
    parsed = lifecycle_dispatch_module.complete_review(
        context.dispatcher, context.directory, context.state, stage, result,
        nonce, resumed=True,
    )
    context.done(envelope_module.STAGE_FINAL_REVIEW)
    return parsed.body.encode("utf-8")


def _closeout_result(
    context: _Execution, work_stdout: bytes, final_review_stdout: bytes
) -> result_module.StageResult:
    stage = context.plan.lifecycle.stage(envelope_module.STAGE_CLOSEOUT)
    if envelope_module.STAGE_CLOSEOUT not in context.performed:
        parsed = context.plan.closeout_result
        if parsed is None:
            raise finalization_module.FinalizationError(
                "RESUME_ARTIFACT_MISMATCH", "finalize has no valid completed closeout result"
            )
        context.state["closeout_candidate"] = context.plan.source_state.get(
            "closeout_candidate"
        )
        return parsed
    nonce = result_module.new_nonce()
    begin, end = result_module.markers(nonce)
    findings = context.dispatcher._sanitize(
        context.directory, context.state, "final_review.stdout.forwarded_to_closeout",
        final_review_stdout.decode("utf-8", "replace"),
    )
    if context.plan.failed_stage_context is not None:
        failed = context.dispatcher._sanitize(
            context.directory, context.state, "failed_closeout.stdout.context",
            _inert_result_markers(
                context.plan.failed_stage_context.decode("utf-8", "replace")
            ),
        )
        findings += (
            "\n\n## Prior failed closeout attempt (non-authoritative context)\n\n"
            "The current exact worktree may already contain its corrections. "
            "Inspect and preserve correct bytes; do not trust its result claim.\n\n" + failed
        )
    binding = candidate_module.tree_identity(context.dispatcher.cwd)
    pre_final = context.state.get("pre_final_candidate")
    if not isinstance(pre_final, dict):
        raise finalization_module.FinalizationError(
            "RESUME_ARTIFACT_MISMATCH", "pre-final candidate is unavailable"
        )
    context.state["revisor_input"] = {
        "original_scope": {
            "kind": "task_prompt",
            "bytes": len(context.task_prompt.encode("utf-8")),
            "sha256": hashlib.sha256(
                context.task_prompt.encode("utf-8")
            ).hexdigest(),
        },
        "producer_binding": pre_final,
        "current_worktree_product": binding,
        "producer_narrative": {
            "optional": True,
            "stage": envelope_module.STAGE_WORK,
            "artifact_basename": (
                f"{context.plan.lifecycle.prefixes[envelope_module.STAGE_WORK]}.stdout.md"
            ),
        },
        "work_review": {
            "artifact_name": (
                f"{context.plan.lifecycle.prefixes[envelope_module.STAGE_FINAL_REVIEW]}"
                ".result.json"
            ),
            "stage": envelope_module.STAGE_FINAL_REVIEW,
            "semantic_role": "work_review",
            "outcome": context.state.get("review_outcomes", {}).get(
                envelope_module.STAGE_FINAL_REVIEW
            ),
        },
    }
    forwarded_work = context.dispatcher._sanitize(
        context.directory,
        context.state,
        "work.stdout.forwarded_to_closeout",
        work_stdout.decode("utf-8", "replace"),
    )
    prior_stage_deltas = stage_delta_module.format_stage_deltas_summary(context.state)
    rendered, prompt_decision = capacity_module.fit_optional_narrative(
        stage.name,
        context.endpoints[envelope_module.STAGE_CLOSEOUT],
        lambda material: context.dispatcher.closeout_prompt(
            context.request,
            context.directory.run_id,
            context.task_prompt,
            pre_final,
            binding,
            material,
            findings,
            begin,
            end,
            stage_delta_summary=prior_stage_deltas,
        ),
        forwarded_work,
        source_stage=envelope_module.STAGE_WORK,
        artifact_basename=(
            f"{context.plan.lifecycle.prefixes[envelope_module.STAGE_WORK]}.stdout.md"
        ),
        artifact_bytes=work_stdout,
        mandatory_sources=(
            "original_scope",
            "producer_binding",
            "current_worktree_product",
            "work_review_findings",
            "terminal_result_contract",
            "stage_delta_summary",
        ),
    )
    context.state.setdefault("prompt_capacity_decisions", []).append(
        prompt_decision
    )
    closer_entry_candidate = candidate_module.tree_identity(context.dispatcher.cwd)
    context.state["closer_entry_candidate"] = closer_entry_candidate
    context.state["revisor_entry_candidate"] = closer_entry_candidate
    result, _ = context.dispatcher._stage(
        context.directory, 5, stage.name, stage.prefix, stage.role,
        context.endpoints[envelope_module.STAGE_CLOSEOUT], rendered, binding,
        read_only=stage.process_read_only,
    )
    closeout_candidate = candidate_module.tree_identity(context.dispatcher.cwd)
    context.state["closeout_candidate"] = closeout_candidate
    context.state["revisor_binding"] = closeout_candidate
    context.state["revisor_candidate"] = closeout_candidate
    closer_mutated = closeout_candidate["tree"] != closer_entry_candidate["tree"]
    adversary_mutated = closer_entry_candidate["tree"] != pre_final["tree"]
    context.state["closeout_delta"] = {
        "changed": closer_mutated,
        "paths": candidate_module.tree_delta(
            context.dispatcher.cwd, str(closer_entry_candidate["tree"]),
            str(closeout_candidate["tree"]),
        ),
        "note": "Paths changed during the closeout stage.",
    }
    context.state["cumulative_closeout_delta"] = {
        "changed": closeout_candidate["tree"] != pre_final["tree"],
        "paths": candidate_module.tree_delta(
            context.dispatcher.cwd, str(pre_final["tree"]),
            str(closeout_candidate["tree"]),
        ),
        "note": "Paths changed after the effective pre_final review.",
    }
    lifecycle_dispatch_module.record_revisor_revision(
        context.dispatcher,
        context.state,
        closer_entry_candidate,
        closeout_candidate,
        stage,
        envelope_module.STAGE_FINAL_REVIEW,
    )
    context.state["final_candidate_reviewed"] = (
        (not adversary_mutated)
        and (not closer_mutated)
        and (closeout_candidate["tree"] == pre_final["tree"])
    )
    try:
        verified = result_repair_module._candidate_boundary(
            context.dispatcher, context.state, context.plan.current_entry, stage
        )
        context.state["terminal_bytes_verified"] = verified
        for key in ("authorized_revisor_revisions", "revisor_revisions"):
            revision = context.state.get(key)
            if isinstance(revision, dict):
                revision["terminal_bytes_verified"] = verified
        context.state["terminal_transport"] = result_repair_module._transport_record(
            stage.name,
            context.endpoints[envelope_module.STAGE_CLOSEOUT],
            result,
        )
    except (candidate_module.CandidateError, gitstate_module.GitStateError) as error:
        context.state["terminal_bytes_verified"] = False
        for key in ("authorized_revisor_revisions", "revisor_revisions"):
            revision = context.state.get(key)
            if isinstance(revision, dict):
                revision["terminal_bytes_verified"] = False
        raise finalization_module.FinalizationError(
            getattr(error, "code", "TERMINAL_BOUNDARY_CAPTURE_FAILED"), str(error)
        ) from error
    context.state["finalization_attempted"] = False
    context.dispatcher._update_invocation_accounting(context.state)
    context.directory.write_json("state.json", context.state)
    try:
        parsed = result_module.parse(
            result.stdout, envelope_module.STAGE_CLOSEOUT, nonce
        )
    except result_module.ResultError as error:
        if not result.ok:
            raise finalization_module.FinalizationError(error.code, error.detail) from error
        context.state.setdefault("result_repair", {})[
            "source_result_blocker"
        ] = error.code
        try:
            parsed = result_repair_module.repair_terminal_result(
                context.dispatcher,
                context.directory,
                context.state,
                context.plan.current_entry,
                stage,
                context.endpoints[envelope_module.STAGE_CLOSEOUT],
                result,
                nonce,
            )
        except finalization_module.FinalizationError as repair_error:
            raise repair_error from error
    context.state["terminal_result_validated"] = True
    if parsed.completed:
        context.done(envelope_module.STAGE_CLOSEOUT)
    return parsed


def _lightweight_context(
    dispatcher: Any,
    request: Any,
    directory: Any,
    state: dict[str, Any],
    plan: resume_module.ResumePlan,
    endpoints: dict[str, Endpoint],
) -> _Execution:
    task_prompt = dispatcher._sanitize(
        directory, state, "request.prompt", request.prompt
    )
    try:
        capacity, dispatcher.stage_output_limits = (
            capacity_module.preflight_lifecycle_capacity(
                dispatcher, request, directory.run_id, task_prompt, endpoints
            )
        )
        state["terminal_prompt_preflight"] = capacity
    except PromptLimitError as error:
        from .dispatch import DispatchError
        raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
    return _Execution(
        dispatcher, request, directory, state, plan, endpoints, task_prompt,
        set(plan.performed_stages),
    )


def _finish_resumed_stage(context: _Execution, stage_name: str) -> None:
    context.done(stage_name)
    checkpoint = context.plan.lifecycle.stage(stage_name).checkpoint
    if checkpoint is not None:
        context.state["checkpoints_completed"].append(checkpoint)
        context.state["effective_checkpoints"].append(checkpoint)
        context.dispatcher.display.checkpoint(checkpoint)


def _resume_solo(
    context: _Execution,
) -> tuple[provider_module.Result, str, Any]:
    terminal = context.plan.lifecycle.stage(
        context.plan.lifecycle.terminal_result_stage
    )
    nonce = result_module.new_nonce()
    begin, end = result_module.markers(nonce)
    prior = []
    if context.plan.failed_stage_context is not None:
        # A failed terminal response is context only. Keep its bounded prose,
        # but neutralize result-fence spellings so a provider cannot mistake a
        # historical nonce for the newly dispatched terminal contract.
        failed_context = _inert_result_markers(
            context.plan.failed_stage_context.decode("utf-8", "replace")
        )
        prior.append((
            "Prior failed solo attempt (non-authoritative context)",
            context.dispatcher._sanitize(
                context.directory, context.state, "failed_solo.stdout.context",
                failed_context,
            ),
        ))
    rendered = context.dispatcher.continuation_prompt(
            terminal.name, context.request, context.directory.run_id,
            envelope_module.SOLO_ENVELOPE, prior,
            include_task_prompt=True,
            contract=context.dispatcher._terminal_contract(
                terminal.name, begin, end
            ),
            task_prompt=context.task_prompt,
        )
    terminal_result, _ = context.dispatcher._stage(
            context.directory, 1, terminal.name, terminal.prefix, terminal.role,
            context.endpoints[terminal.name], rendered, None,
            read_only=terminal.process_read_only,
        )
    candidate = candidate_module.tree_identity(context.dispatcher.cwd)
    context.state["solo_candidate"] = candidate
    context.state["producer_binding"] = candidate
    context.state["terminal_candidate"] = candidate
    return terminal_result, nonce, terminal


def _resume_plan_reviewed(
    context: _Execution,
) -> tuple[provider_module.Result, str, Any]:
    plan_stage, review_stage, terminal = context.plan.lifecycle.stages
    if plan_stage.name in context.performed:
        read_only_tree = candidate_module.tree_identity(context.dispatcher.cwd)
        rendered = context.dispatcher.plan_prompt(
            context.request, context.directory.run_id, context.task_prompt
        )
        result, _ = context.dispatcher._stage(
                context.directory, 1, plan_stage.name, plan_stage.prefix,
                plan_stage.role, context.endpoints[plan_stage.name], rendered, None,
                read_only=plan_stage.process_read_only,
            )
        lifecycle_dispatch_module.require_unchanged(
                context.dispatcher, context.state, read_only_tree, plan_stage.name,
                context.plan.current_entry.index_identity,
            )
        endpoint = context.endpoints[plan_stage.name]
        material = lifecycle_dispatch_module.materialize_plan(
            context.directory,
            result.stdout,
            endpoint.provider,
            endpoint.profile,
        )
        plan_stdout = material.data
        context.state["plan_candidate"] = material.binding
        context.state["proposal_binding"] = material.binding
        context.state["plan_proposal_binding"] = material.binding
        _finish_resumed_stage(context, plan_stage.name)
    else:
        plan_stdout = _source_stdout(context.plan, plan_stage.name)
        context.state["proposal_binding"] = context.state.get(
            "proposal_binding", context.state.get("plan_candidate")
        )
        context.state["plan_proposal_binding"] = context.state.get(
            "plan_proposal_binding", context.state.get("plan_candidate")
        )
    if review_stage.name in context.performed:
        read_only_tree = candidate_module.tree_identity(context.dispatcher.cwd)
        nonce = review_result_module.new_nonce()
        review_binding = _review_binding(
            context, review_stage.name, context.state["plan_candidate"]
        )
        rendered = context.dispatcher.review_prompt(
                review_stage.name, context.request, context.directory.run_id,
                review_binding,
                plan_stdout,
                context.task_prompt,
                review_result_module.contract(review_stage.name, nonce),
            )
        result, _ = context.dispatcher._stage(
                context.directory, 2, review_stage.name, review_stage.prefix,
                review_stage.role, context.endpoints[review_stage.name], rendered,
                context.state["plan_candidate"],
                read_only=review_stage.process_read_only,
            )
        lifecycle_dispatch_module.require_unchanged(
                context.dispatcher, context.state, read_only_tree, review_stage.name,
                context.plan.current_entry.index_identity,
            )
        parsed = lifecycle_dispatch_module.complete_review(
            context.dispatcher, context.directory, context.state, review_stage,
            result, nonce, resumed=True,
        )
        review_stdout = parsed.body.encode("utf-8")
        context.done(review_stage.name)
    else:
        review_stdout = _source_review_body(context.plan, review_stage.name)
    nonce = result_module.new_nonce()
    begin, end = result_module.markers(nonce)
    rendered = context.dispatcher.continuation_prompt(
            terminal.name, context.request, context.directory.run_id,
            envelope_module.PLAN_REVIEWED_PRODUCE_CLOSE_ENVELOPE,
            [
                (
                    "Plan proposal binding (dispatcher-owned exact bytes)",
                    lifecycle_dispatch_module._binding_text(
                        context.state["plan_candidate"]
                    ),
                ),
                (
                    "Planner proposal — exact bound bytes, to be dispositioned",
                    plan_stdout,
                ),
                ("Independent plan review findings",
                 review_stdout.decode("utf-8", "replace")),
            ],
            include_task_prompt=True,
            contract=context.dispatcher._terminal_contract(terminal.name, begin, end),
            task_prompt=context.task_prompt,
        )
    terminal_result, _ = context.dispatcher._stage(
            context.directory, 3, terminal.name, terminal.prefix, terminal.role,
            context.endpoints[terminal.name], rendered, None,
            read_only=terminal.process_read_only,
        )
    candidate = candidate_module.tree_identity(context.dispatcher.cwd)
    context.state["produce_close_candidate"] = candidate
    context.state["producer_binding"] = candidate
    context.state["work_product_binding"] = candidate
    context.state["terminal_candidate"] = candidate
    context.state["final_candidate_reviewed"] = False
    return terminal_result, nonce, terminal


def _resume_work_reviewed(
    context: _Execution,
) -> tuple[provider_module.Result, str, Any]:
    produce, review_stage, terminal = context.plan.lifecycle.stages
    if produce.name in context.performed:
        rendered = context.dispatcher.continuation_prompt(
                produce.name, context.request, context.directory.run_id,
                envelope_module.WORK_REVIEWED_PRODUCE_ENVELOPE, [],
                include_task_prompt=True, task_prompt=context.task_prompt,
            )
        result, _ = context.dispatcher._stage(
                context.directory, 1, produce.name, produce.prefix, produce.role,
                context.endpoints[produce.name], rendered, None,
                read_only=produce.process_read_only,
            )
        produce_stdout = result.stdout
        context.state["produced_candidate"] = candidate_module.tree_identity(
                context.dispatcher.cwd
            )
        context.state["producer_binding"] = context.state["produced_candidate"]
        context.state["work_product_binding"] = context.state["produced_candidate"]
        _finish_resumed_stage(context, produce.name)
    else:
        produce_stdout = _source_stdout(context.plan, produce.name)
    produced = context.state["produced_candidate"]
    context.state["producer_binding"] = context.state.get(
        "producer_binding", produced
    )
    context.state["work_product_binding"] = context.state.get(
        "work_product_binding", produced
    )
    if review_stage.name in context.performed:
        nonce = review_result_module.new_nonce()
        review_binding = _review_binding(context, review_stage.name, produced)
        def render_review(material):
            return context.dispatcher.review_prompt(
                review_stage.name, context.request, context.directory.run_id,
                review_binding, material, context.task_prompt,
                review_result_module.contract(review_stage.name, nonce),
            )
        if context.plan.output_recovery is not None:
            rendered = render_review(produce_stdout)
            prompt_decision = {
                "stage": review_stage.name,
                "source_stage": produce.name,
                "artifact_basename": output_recovery_module.ARTIFACT,
                "classification": "mandatory_exact_recovered_producer_material",
                "artifact_bytes": len(produce_stdout),
                "artifact_sha256": output_recovery_module.sha256_bytes(
                    produce_stdout
                ),
                "decision": "included_exact",
                "final_prompt_bytes": len(rendered.data),
                "prefix_or_summary_substituted": False,
                "mandatory_sources": [
                    "original_scope", "producer_binding", "work_review_contract"
                ],
                "optional_sources": [],
                "omitted_sources": [],
                "preserved_sources": [
                    "original_scope", "producer_binding", "work_review_contract"
                ],
                "omission_scope": "none",
                "mandatory_material_preserved": True,
            }
        else:
            rendered, prompt_decision = capacity_module.fit_optional_narrative(
                review_stage.name,
                context.endpoints[review_stage.name],
                render_review,
                produce_stdout,
                source_stage=produce.name,
                artifact_basename=f"{produce.prefix}.stdout.md",
                artifact_bytes=produce_stdout,
                mandatory_sources=(
                    "original_scope", "producer_binding", "work_review_contract"
                ),
            )
        context.state.setdefault("prompt_capacity_decisions", []).append(
            prompt_decision
        )
        result, _ = context.dispatcher._stage(
                context.directory, 2, review_stage.name, review_stage.prefix,
                review_stage.role, context.endpoints[review_stage.name], rendered,
                produced, read_only=review_stage.process_read_only,
                on_provider_invoke=lambda: _verify_recovery_boundary(context),
            )
        lifecycle_dispatch_module.require_unchanged(
            context.dispatcher,
            context.state,
            produced,
            review_stage.name,
            context.plan.current_entry.index_identity,
            "REVIEW_MUTATED_CANDIDATE",
        )
        parsed = lifecycle_dispatch_module.complete_review(
            context.dispatcher, context.directory, context.state, review_stage,
            result, nonce, resumed=True,
        )
        review_stdout = parsed.body.encode("utf-8")
        context.done(review_stage.name)
    else:
        review_stdout = _source_review_body(context.plan, review_stage.name)
    current_product = candidate_module.tree_identity(context.dispatcher.cwd)
    context.state["revisor_input"] = {
        "original_scope": {
            "kind": "task_prompt",
            "bytes": len(context.task_prompt.encode("utf-8")),
            "sha256": hashlib.sha256(
                context.task_prompt.encode("utf-8")
            ).hexdigest(),
        },
        "producer_binding": produced,
        "current_worktree_product": current_product,
        "producer_narrative": {
            "optional": True,
            "stage": produce.name,
            "artifact_basename": (
                output_recovery_module.ARTIFACT
                if context.plan.output_recovery is not None
                else f"{produce.prefix}.stdout.md"
            ),
        },
        "work_review": {
            "artifact_name": f"{review_stage.prefix}.result.json",
            "outcome": context.state.get("review_outcomes", {}).get(
                review_stage.name
            ),
        },
    }
    nonce = result_module.new_nonce()
    begin, end = result_module.markers(nonce)
    terminal_producer_material = context.dispatcher._sanitize(
        context.directory,
        context.state,
        "produce.stdout.forwarded_to_revise_close",
        produce_stdout.decode("utf-8", "replace"),
    )
    rendered, prompt_decision = capacity_module.fit_optional_narrative(
        terminal.name,
        context.endpoints[terminal.name],
        lambda material: context.dispatcher.continuation_prompt(
            terminal.name, context.request, context.directory.run_id,
            envelope_module.WORK_REVIEWED_REVISE_CLOSE_ENVELOPE,
            [
                (
                    "Producer binding (dispatcher-owned exact product)",
                    lifecycle_dispatch_module._binding_text(produced),
                ),
                (
                    "Current worktree product (dispatcher-owned exact binding)",
                    lifecycle_dispatch_module._binding_text(current_product),
                ),
                ("Producer narrative (optional whole artifact)", material),
                (
                    "Independent work review findings",
                    review_stdout.decode("utf-8", "replace"),
                ),
            ],
            include_task_prompt=True,
            contract=context.dispatcher._terminal_contract(
                terminal.name, begin, end
            ),
            task_prompt=context.task_prompt,
        ),
        terminal_producer_material,
        source_stage=produce.name,
        artifact_basename=(
            output_recovery_module.ARTIFACT
            if context.plan.output_recovery is not None
            else f"{produce.prefix}.stdout.md"
        ),
        artifact_bytes=produce_stdout,
        mandatory_sources=(
            "original_scope",
            "producer_binding",
            "current_worktree_product",
            "work_review_findings",
            "terminal_result_contract",
        ),
    )
    context.state.setdefault("prompt_capacity_decisions", []).append(
        prompt_decision
    )
    closer_entry_candidate = candidate_module.tree_identity(context.dispatcher.cwd)
    context.state["closer_entry_candidate"] = closer_entry_candidate
    context.state["revisor_entry_candidate"] = closer_entry_candidate
    terminal_result, _ = context.dispatcher._stage(
            context.directory, 3, terminal.name, terminal.prefix, terminal.role,
            context.endpoints[terminal.name], rendered, produced,
            read_only=terminal.process_read_only,
            on_provider_invoke=lambda: _verify_recovery_boundary(context),
        )
    candidate = candidate_module.tree_identity(context.dispatcher.cwd)
    context.state["revise_close_candidate"] = candidate
    context.state["revisor_binding"] = candidate
    context.state["terminal_candidate"] = candidate
    closer_mutated = candidate["tree"] != closer_entry_candidate["tree"]
    adversary_mutated = closer_entry_candidate["tree"] != produced["tree"]
    context.state["post_review_revision_delta"] = {
            "changed": closer_mutated,
            "paths": candidate_module.tree_delta(
                context.dispatcher.cwd,
                str(closer_entry_candidate["tree"]), str(candidate["tree"])
            ),
            "note": "Paths changed during terminal revise_close stage without a second review.",
        }
    context.state["cumulative_post_review_delta"] = {
            "changed": candidate["tree"] != produced["tree"],
            "paths": candidate_module.tree_delta(
                context.dispatcher.cwd,
                str(produced["tree"]), str(candidate["tree"])
            ),
            "note": "Paths changed after post_work review without a second review.",
        }
    lifecycle_dispatch_module.record_revisor_revision(
        context.dispatcher,
        context.state,
        closer_entry_candidate,
        candidate,
        terminal,
        review_stage.name,
    )
    context.state["final_candidate_reviewed"] = (
        (not adversary_mutated)
        and (not closer_mutated)
        and (candidate["tree"] == produced["tree"])
    )
    return terminal_result, nonce, terminal


def _finish_lightweight(
    context: _Execution,
    terminal_result: provider_module.Result,
    nonce: str,
    terminal: Any,
) -> dict[str, Any]:
    try:
        verified = result_repair_module._candidate_boundary(
            context.dispatcher, context.state, context.plan.current_entry, terminal
        )
        context.state["terminal_transport"] = result_repair_module._transport_record(
            terminal.name, context.endpoints[terminal.name], terminal_result
        )
        context.state["terminal_bytes_verified"] = verified
        for key in ("authorized_revisor_revisions", "revisor_revisions"):
            revision = context.state.get(key)
            if isinstance(revision, dict):
                revision["terminal_bytes_verified"] = verified
    except (candidate_module.CandidateError, gitstate_module.GitStateError) as error:
        context.state["terminal_bytes_verified"] = False
        for key in ("authorized_revisor_revisions", "revisor_revisions"):
            revision = context.state.get(key)
            if isinstance(revision, dict):
                revision["terminal_bytes_verified"] = False
        raise finalization_module.FinalizationError(
            getattr(error, "code", "TERMINAL_BOUNDARY_CAPTURE_FAILED"), str(error)
        ) from error
    context.state["finalization_attempted"] = False
    context.dispatcher._update_invocation_accounting(context.state)
    context.directory.write_json("state.json", context.state)
    try:
        parsed = result_module.parse(terminal_result.stdout, terminal.name, nonce)
    except result_module.ResultError as error:
        if not terminal_result.ok:
            raise finalization_module.FinalizationError(error.code, error.detail) from error
        context.state.setdefault("result_repair", {})[
            "source_result_blocker"
        ] = error.code
        try:
            parsed = result_repair_module.repair_terminal_result(
                context.dispatcher,
                context.directory,
                context.state,
                context.plan.current_entry,
                terminal,
                context.endpoints[terminal.name],
                terminal_result,
                nonce,
            )
        except finalization_module.FinalizationError as repair_error:
            raise repair_error from error
    context.directory.write_json(f"{terminal.prefix}.result.json", parsed.as_dict())
    lifecycle_dispatch_module.record_terminal_narrative(
        context.state, parsed.body
    )
    context.state["terminal_fence_copies"] = parsed.fence_copies
    context.state["provider_outcomes"] = {terminal.name: parsed.outcome}
    context.state["semantic_outcome"] = parsed.outcome
    context.state["proposed_commit_message"] = (
        None if parsed.commit_message is None else {
            "subject": parsed.commit_message.subject,
            "body": parsed.commit_message.body,
        }
    )
    if not parsed.completed:
        raise finalization_module.FinalizationError(
            f"PROVIDER_OUTCOME_{parsed.outcome.upper()}",
            f"{terminal.name} reported {parsed.outcome}: {parsed.body.strip()[:2000]}",
        )
    context.state["terminal_result_validated"] = True
    context.state["semantic_outcome"] = parsed.outcome
    context.done(terminal.name)
    context.state["effective_review_count"] = len(
        context.state["effective_checkpoints"]
    )
    context.state["finalization_attempted"] = True
    context.directory.write_json("state.json", context.state)
    output_recovery_module.verify_source_unchanged(context.plan)
    finalization_module.finalize_repository(
        context.state,
        context.plan.current_entry,
        parsed,
        context.dispatcher.display,
        resumed=True,
        directory=context.directory,
    )
    context.state["outcome"] = "completed"
    context.state["complete"] = True
    return context.state


def _execute_lightweight(
    dispatcher: Any,
    request: Any,
    directory: Any,
    state: dict[str, Any],
    plan: resume_module.ResumePlan,
    endpoints: dict[str, Endpoint],
) -> dict[str, Any]:
    """Execute a lifecycle-declared lightweight suffix."""
    context = _lightweight_context(
        dispatcher, request, directory, state, plan, endpoints
    )
    runners = {
        "solo": _resume_solo,
        "plan-reviewed": _resume_plan_reviewed,
        "work-reviewed": _resume_work_reviewed,
    }
    try:
        terminal_result, nonce, terminal = runners[plan.lifecycle.name](context)
    except KeyError as error:
        raise finalization_module.FinalizationError(
            "LIFECYCLE_INVALID", f"unsupported lifecycle {plan.lifecycle.name}"
        ) from error
    return _finish_lightweight(context, terminal_result, nonce, terminal)


def _finalize_only(
    dispatcher: Any,
    directory: Any,
    state: dict[str, Any],
    plan: resume_module.ResumePlan,
) -> dict[str, Any]:
    parsed = plan.closeout_result
    if parsed is None or not parsed.completed:
        raise finalization_module.FinalizationError(
            "RESUME_ARTIFACT_MISMATCH",
            "finalize has no valid completed terminal result",
        )
    state["provider_outcomes"] = {parsed.stage: parsed.outcome}
    state["semantic_outcome"] = parsed.outcome
    state["terminal_fence_copies"] = parsed.fence_copies
    if parsed.stage == "closeout":
        state["closeout_fence_copies"] = parsed.fence_copies
    lifecycle_dispatch_module.record_terminal_narrative(state, parsed.body)
    state["provider_invocations_performed"] = 0
    state["effective_review_count"] = len(state["effective_checkpoints"])
    finalization_module.finalize_repository(
        state,
        plan.current_entry,
        parsed,
        dispatcher.display,
        resumed=True,
        directory=directory,
        expected_index=plan.current_entry.index_identity,
    )
    state["outcome"] = "completed"
    state["complete"] = True
    return state


def execute(
    dispatcher: Any,
    request: Any,
    directory: Any,
    state: dict[str, Any],
    plan: resume_module.ResumePlan,
    endpoints: dict[str, Endpoint],
) -> dict[str, Any]:
    """Execute exactly the invalidated suffix, then finalize once."""
    if plan.from_stage == "finalize":
        return _finalize_only(dispatcher, directory, state, plan)
    if plan.lifecycle.name != "standard":
        return _execute_lightweight(
            dispatcher, request, directory, state, plan, endpoints
        )
    task_prompt = dispatcher._sanitize(directory, state, "request.prompt", request.prompt)
    try:
        capacity, dispatcher.stage_output_limits = (
            capacity_module.preflight_lifecycle_capacity(
                dispatcher, request, directory.run_id, task_prompt, endpoints
            )
        )
        state["terminal_prompt_preflight"] = capacity
    except PromptLimitError as error:
        from .dispatch import DispatchError
        raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
    context = _Execution(
        dispatcher, request, directory, state, plan, endpoints, task_prompt,
        set(plan.performed_stages),
    )
    plan_stdout = _plan_output(context)
    plan_review_stdout = _plan_review_output(context, plan_stdout)

    work_stdout = _work_output(context, plan_stdout, plan_review_stdout)

    final_review_stdout = _final_review_output(context, work_stdout)

    parsed = _closeout_result(context, work_stdout, final_review_stdout)

    terminal_prefix = plan.lifecycle.prefixes[plan.lifecycle.terminal_result_stage]
    directory.write_json(f"{terminal_prefix}.result.json", parsed.as_dict())
    lifecycle_dispatch_module.record_terminal_narrative(state, parsed.body)
    state["closeout_fence_copies"] = parsed.fence_copies
    state["terminal_fence_copies"] = parsed.fence_copies
    state["terminal_candidate"] = state.get("closeout_candidate")
    state["proposed_commit_message"] = (
        None if parsed.commit_message is None else {
            "subject": parsed.commit_message.subject,
            "body": parsed.commit_message.body,
        }
    )
    state["provider_outcomes"] = {envelope_module.STAGE_CLOSEOUT: parsed.outcome}
    state["semantic_outcome"] = parsed.outcome
    if not parsed.completed:
        raise finalization_module.FinalizationError(
            f"PROVIDER_OUTCOME_{parsed.outcome.upper()}",
            f"closeout reported {parsed.outcome}: {parsed.body.strip()[:2000]}",
        )
    finalization_module.finalize_repository(
        state,
        plan.current_entry,
        parsed,
        dispatcher.display,
        resumed=True,
        directory=directory,
    )
    state["outcome"] = "completed"
    state["complete"] = True
    return state
