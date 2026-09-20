"""Multi-turn semantic execution loop and turn orchestrator for Request V2.

Actor Binding Stage Labels:
For Display observer integration, each turn's stage label is given by
`binding.binding_id` (e.g. 'binding_plan', 'binding_plan_review',
'binding_work', 'binding_work_review', 'binding_closeout' in the default
5-turn topology, and 'binding_<role_name>' in the unmerged 8-turn topology).
This stable identifier represents the active actor binding boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
import json
from pathlib import Path
import os
import sqlite3
import sys
import time
from typing import Any

from .v2_repair import execute_v2_result_repair, is_v2_repair_eligible
from . import (
    candidate,
    gitstate as gitstate_module,
    plan_material,
    provider as provider_module,
    result as result_module,
    review_drift as review_drift_module,
    review_result,
)
from .capabilities import EndpointCapabilities
from .config_routing import RETAINED_STATIC_MODES, ReviewMutationPolicy
from .display import Display
from .dynamic_router import (
    OperationalObservation,
    ResolvedActorRoute,
    resolve_dynamic_route,
    resolve_static_preset_route,
)
from .v2_reroute import handle_turn_failure, orchestrate_dynamic_retry
from .persistence import (
    get_attempt_route_resolution,
    get_invocation_attempts,
    record_artifact,
    record_candidate,
    record_completion_receipt,
    record_invocation_attempt,
    record_review_mutation_observation,
    record_route_resolution,
    update_invocation_attempt,
    update_semantic_responsibility,
    utc_now_iso,
)
from .request import PhaseRequestV2
from .roster import RosterSnapshot, load_roster
from .worker_capability import resolve_worker_capability
from .semantic_roles import (
    ROLE_CLOSEOUT_AGENT,
    ROLE_PLAN_REVIEW_DISPOSITION,
    ROLE_PLAN_REVIEWER,
    ROLE_PLANNER,
    ROLE_PRODUCER,
    ROLE_REVISER,
    ROLE_WORK_REVIEW_DISPOSITION,
    ROLE_WORK_REVIEWER,
    ActorBindingPolicy,
)
from .v2_prompts import (
    render_closeout_prompt,
    render_plan_prompt,
    render_plan_review_prompt,
    render_work_prompt,
    render_work_review_prompt,
)
from .v2_records import (
    save_disposition,
    save_plan_candidate,
    save_review,
)


class V2TurnError(RuntimeError):
    """Raised when a Request V2 turn fails."""


class PreLaunchFailureError(V2TurnError):
    """Raised when an error occurs before substantive provider process launch."""


class PreSubstantiveFailureError(V2TurnError):
    """Pre-substantive failure permitting dynamic reroute on retry."""


class StartupFailureError(PreSubstantiveFailureError):
    """Provider exited before substantive work or stdout was produced."""


class SubstantiveFailureError(V2TurnError):
    """Failure after substantive work, provider output, or mutation occurred."""


def _safe_display_call(func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Invoke a display observer method safely; observer failures must not mask execution errors."""
    try:
        func(*args, **kwargs)
    except Exception:
        pass


def extract_findings_from_body(body: str) -> list[dict[str, Any]]:
    """Extract structured finding list from unstructured reviewer body."""
    findings: list[dict[str, Any]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ")) or (len(line) > 2 and line[0].isdigit() and line[1] in (".", ")")):
            text = line.lstrip("-*0123456789.) ").strip()
            if text:
                findings.append({"severity": "advisory", "title": text[:60], "detail": text})
        elif line.startswith(("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "Finding")):
            findings.append({"severity": "advisory", "title": line[:60], "detail": line})
    if not findings and body.strip():
        findings.append({"severity": "advisory", "title": body.strip()[:60], "detail": body.strip()})
    return findings




def _execute_v2_turns(
    conn: sqlite3.Connection,
    run_id: str,
    run_dir: Path,
    repository_root: Path,
    work_tree: Path,
    request: PhaseRequestV2,
    execution_mode: str,
    binding_policy: ActorBindingPolicy,
    caps_catalog: Mapping[str, EndpointCapabilities],
    operational_observations: Sequence[OperationalObservation],
    runner: Callable[..., Any] | None,
    display: Display | None,
    dry_run: bool,
    lifecycle_spec: Any,
    finalization_policy: str,
    attempt_number: int = 1,
    injected_observations: Sequence[OperationalObservation] = (),
    now: float | None = None,
    review_mutation_policy: ReviewMutationPolicy | Mapping[str, Any] | None = None,
    *,
    roster: RosterSnapshot | None = None,
    apgr_home: Path | str | None = None,
    rtk_resolution: Any = None,
) -> dict[str, Any]:
    """Execute all actor bindings in the binding policy sequentially.

    Stage Labels:
    For Display observer integration, each turn's stage label is given by
    `binding.binding_id` (e.g. 'binding_plan', 'binding_plan_review',
    'binding_work', 'binding_work_review', 'binding_closeout' in the default
    5-turn topology, and 'binding_<role_name>' in the unmerged 8-turn topology).
    This stable identifier represents the active actor binding boundary.
    """
    candidate.require_worktree(work_tree)
    initial_ident = candidate.tree_identity(work_tree)
    initial_tree = str(initial_ident.get("tree", ""))
    initial_head = str(initial_ident.get("head", ""))

    effective_injected = tuple(injected_observations)
    snap = roster if roster is not None else load_roster(repository_root, apgr_home=apgr_home)
    prior_resolutions: dict[str, ResolvedActorRoute] = {}

    plan_material_text = ""
    plan_review_outcome = "reviewed_with_no_findings"
    plan_findings: list[dict[str, Any]] = []
    plan_disposition = "accept"
    plan_review_id = ""

    producer_candidate_tree = ""
    work_stdout = ""
    candidate_delta: list[str] = []
    work_review_outcome = "reviewed_with_no_findings"
    work_findings: list[dict[str, Any]] = []
    work_disposition = "accept"
    work_review_id = ""
    closeout_stage_result: result_module.StageResult | None = None
    repair_attempted: bool = False
    result_repair_evidence: dict[str, Any] | None = None

    review_mutation_observations: dict[str, Any] = {}
    subject_drift_observed = False
    surviving_review_paths: set[str] = set()
    work_review_candidate_tree = ""
    work_review_obs: Any = None
    work_review_receipt_valid = False
    closer_entry_tree = ""
    closer_terminal_tree = ""

    stage_count = len(binding_policy.bindings)
    for index, binding in enumerate(binding_policy.bindings, start=1):
        # 1. Derive attempt number and verified predecessor lineage (semantic attempts only)
        all_attempts = get_invocation_attempts(conn, run_id, binding_id=binding.binding_id)
        prior_attempts = [
            a for a in all_attempts
            if a.get("attempt_kind", "semantic") != "auxiliary"
            and not (a["attempt_id"].endswith("-repair-1") or "-repair-" in a["attempt_id"])
        ]
        if prior_attempts:
            curr_attempt_number = len(prior_attempts) + 1
            predecessor_id: str | None = prior_attempts[-1]["attempt_id"]
        elif attempt_number > 1:
            curr_attempt_number = attempt_number
            cand_pred = f"att-{run_id}-{binding.binding_id}-{attempt_number - 1}"
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM invocation_attempts WHERE attempt_id = ?", (cand_pred,))
            predecessor_id = cand_pred if cur.fetchone() else None
        else:
            curr_attempt_number = 1
            predecessor_id = None

        while True:

            # 2. Check for existing route resolution (Recovery Immutability)
            existing = get_attempt_route_resolution(conn, run_id, binding.binding_id, curr_attempt_number)
            if existing is not None:
                route = ResolvedActorRoute(
                    binding_id=existing["binding_id"],
                    provider=existing["provider"],
                    profile=existing["profile"],
                    endpoint_alias=existing.get("endpoint_alias") or "",
                    capabilities=frozenset(),
                    selection_rationale=existing.get("selection_rationale") or "reused from persistence",
                    roles=tuple(binding.roles),
                )
                resolution_id = existing["resolution_id"]
            else:
                if execution_mode in RETAINED_STATIC_MODES:
                    route = resolve_static_preset_route(
                        binding,
                        request.phase_type,
                        execution_mode,
                        roster=snap,
                        root=repository_root,
                        capabilities=caps_catalog,
                        apgr_home=apgr_home,
                    )
                else:
                    if not caps_catalog:
                        raise PreLaunchFailureError(
                            "dynamic execution mode requires a usable capabilities catalog, but capabilities are missing or empty"
                        )
                    route = resolve_dynamic_route(
                        binding,
                        request.phase_type,
                        capabilities_catalog=caps_catalog,
                        operational_observations=operational_observations,
                        prior_resolutions=prior_resolutions,
                        now=now,
                        execution_mode=execution_mode,
                        root=repository_root, bundle=snap.bundle,
                    )

                resolution_id = f"res-{run_id}-{binding.binding_id}-attempt-{curr_attempt_number}"
                if not dry_run:
                    record_route_resolution(
                        conn,
                        resolution_id=resolution_id,
                        run_id=run_id,
                        binding_id=binding.binding_id,
                        attempt_number=curr_attempt_number,
                        provider=route.provider,
                        profile=route.profile,
                        endpoint_alias=route.endpoint_alias,
                        intelligence={"provider": route.provider, "profile": route.profile},
                        policy_snapshot=route.policy_snapshot,
                        observation_ids=route.observation_ids,
                        selection_rationale=route.selection_rationale,
                    )

            prior_resolutions[binding.binding_id] = route

            if dry_run:
                break

            # Record attempt if not already staged
            attempt_id = f"att-{run_id}-{binding.binding_id}-{curr_attempt_number}"
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM invocation_attempts WHERE attempt_id = ?", (attempt_id,))
            if not cur.fetchone():
                record_invocation_attempt(
                    conn,
                    attempt_id=attempt_id,
                    run_id=run_id,
                    binding_id=binding.binding_id,
                    attempt_number=curr_attempt_number,
                    provider=route.provider,
                    profile=route.profile,
                    endpoint_alias=route.endpoint_alias,
                    status="staged",
                    predecessor_attempt_id=predecessor_id,
                    route_resolution_id=resolution_id,
                )

            if runner is None:
                break

            runner_launched = False
            context_prepared = {"reference": None}
            attempt_terminalized = False
            t_elapsed = 0.0
            observation_active: bool | None = None
            observation_worker_parent: str | None = None
            # The reroute path advances both values before continuing.
            attempt_predecessor_id = predecessor_id
            attempt_number_at_start = curr_attempt_number

            try:
                # Invariant 14 check
                persisted_route = get_attempt_route_resolution(conn, run_id, binding.binding_id, curr_attempt_number)
                if persisted_route is None:
                    raise V2TurnError("invariant violation: route was not persisted before launch")

                if display is not None:
                    display.stage_started(
                        index,
                        binding.binding_id,
                        ", ".join(binding.roles),
                        route,
                        stage_count=stage_count,
                    )

                # 3. Synthesize prompt
                nonce = review_result.new_nonce()
                is_plan = ROLE_PLANNER in binding.roles
                is_plan_rev = ROLE_PLAN_REVIEWER in binding.roles
                is_prod = ROLE_PRODUCER in binding.roles
                is_work_rev = ROLE_WORK_REVIEWER in binding.roles
                is_closeout = ROLE_CLOSEOUT_AGENT in binding.roles or ROLE_REVISER in binding.roles

                if is_plan:
                    prompt_bytes = render_plan_prompt(request.prompt)
                elif is_plan_rev:
                    prompt_bytes = render_plan_review_prompt(request.prompt, plan_material_text, nonce)
                elif is_prod:
                    prompt_bytes = render_work_prompt(
                        request.prompt, plan_material_text, plan_review_outcome,
                        plan_findings, plan_disposition, baseline_tree=initial_tree,
                        review_window_mutations=sorted(surviving_review_paths),
                    )
                elif is_work_rev:
                    prompt_bytes = render_work_review_prompt(
                        request.prompt, producer_candidate_tree or initial_tree,
                        candidate_delta, work_stdout, nonce,
                    )
                elif is_closeout:
                    prompt_bytes = render_closeout_prompt(
                        request.prompt, producer_candidate_tree or initial_tree,
                        work_review_outcome, work_findings, work_disposition,
                        nonce=nonce,
                        review_window_mutations=sorted(surviving_review_paths),
                    )
                else:
                    prompt_bytes = request.prompt.encode("utf-8")

                # 4. Enforce read-only process posture
                is_read_only = binding.process_read_only
                ident_before = candidate.tree_identity(work_tree)
                tree_before = str(ident_before.get("tree", initial_tree))
                index_before = gitstate_module.index_identity(work_tree)
                head_before = gitstate_module.current_head(work_tree)
                if is_closeout and not closer_entry_tree:
                    closer_entry_tree = tree_before

                # 5. Execute runner
                stdout_bytes = b""
                stderr_bytes = b""
                exit_code = 0

                endpoint = snap.endpoints.get(route.endpoint_alias)
                argv = (
                    provider_module.build_argv(
                        endpoint,
                        "reviewer" if is_read_only else "primary",
                        repository_root,
                        read_only=is_read_only, pin_profile=False,
                    )
                    if endpoint is not None
                    else ["mock-provider", route.endpoint_alias]
                )
                worker_capability = (
                    resolve_worker_capability(
                        repository_root, endpoint.provider, endpoint.profile, execution_mode
                    )
                    if endpoint is not None
                    else None
                )
                task_authority = "read_only" if is_read_only else "mutation_capable"
                if worker_capability is not None and worker_capability.get("allowed"):
                    worker_capability = {**worker_capability, "task_authority": task_authority}

                from .worker_capability import MANDATORY_WORKER_MODES
                is_mandatory = (
                    execution_mode in MANDATORY_WORKER_MODES
                    or execution_mode == "dynamic"
                    or (worker_capability and worker_capability.get("requirement") == "required")
                    or "subagent_workers" in binding.required_capabilities
                )
                if is_mandatory:
                    if worker_capability is None or not worker_capability.get("allowed"):
                        reason = (
                            worker_capability.get("reason", "worker_unavailable")
                            if worker_capability
                            else "worker_unavailable"
                        )
                        if not reason.startswith("worker_unavailable"):
                            reason = f"worker_unavailable: {reason}"
                        raise PreLaunchFailureError(reason)

                has_workers = bool(worker_capability and worker_capability.get("allowed"))
                instruction_records = []
                if endpoint is not None and endpoint.provider == "codex":
                    from agent_source_guidance import codex_guidance_overrides
                    overrides = codex_guidance_overrides(
                        repository_root, workers=has_workers, rtk=rtk_resolution,
                        instruction_records=instruction_records,
                    )
                    additions = []
                    for override in overrides:
                        if override not in argv:
                            additions.extend(("-c", override))
                    if additions and not has_workers:
                        argv = argv[:-1] + additions + argv[-1:]
                    if has_workers:
                        from . import envelope as envelope_module
                        worker_env_text = envelope_module.worker_envelope(
                            worker_capability, str(repository_root / "bin/agent-worker")
                        )
                        if worker_env_text:
                            prompt_bytes = (worker_env_text + "\n\n").encode("utf-8") + prompt_bytes
                elif endpoint is not None and endpoint.provider == "antigravity":
                    from agent_source_guidance import source_guidance
                    ag_source = source_guidance(
                        repository_root / "antigravity",
                        [],
                        workers=has_workers,
                        instruction_file="GEMINI.md",
                        rtk=rtk_resolution,
                        provider="antigravity",
                    )
                    ag_guidance, _ = ag_source
                    instruction_records.extend(ag_source.instruction_components)
                    from . import envelope as envelope_module
                    worker_env_text = (
                        envelope_module.worker_envelope(worker_capability, str(repository_root / "bin/agent-worker"))
                        if has_workers
                        else ""
                    )
                    combined_guidance = (ag_guidance + "\n\n" + worker_env_text).strip()
                    if combined_guidance:
                        prompt_bytes = (combined_guidance + "\n\n").encode("utf-8") + prompt_bytes
                elif endpoint is not None and endpoint.provider == "claude" and has_workers:
                    from . import envelope as envelope_module
                    worker_env_text = envelope_module.worker_envelope(
                        worker_capability, str(repository_root / "bin/agent-worker")
                    )
                    if worker_env_text:
                        prompt_bytes = (worker_env_text + "\n\n").encode("utf-8") + prompt_bytes

                from .worker_launch import bound_workers
                parent_id = f"parent-{run_id}-{binding.binding_id}-{curr_attempt_number}"
                with bound_workers(
                    repository_root, run_dir, work_tree, parent_id, endpoint,
                    task_authority, worker_capability, argv, attempt_id, rtk=rtk_resolution,
                ) as worker_session:
                    argv = worker_session["argv"]
                    if worker_capability and worker_capability.get("allowed"):
                        observation_worker_parent = parent_id
                    from .context_config import capture_context_config
                    from . import context_adapter
                    context_capture = capture_context_config(project_root=work_tree, apgr_home=apgr_home)
                    from . import observations as observations_module
                    observation_active = observations_module.enabled(context_capture.get("observations"))
                    from . import context_route
                    route_argv = list(argv)
                    argv, prompt_bytes, context_prepared = context_adapter.prepare(
                        capture=context_capture, run_dir=run_dir, prefix=attempt_id,
                        run_id=run_id, binding_id=binding.binding_id, attempt_id=attempt_id,
                        attempt_number=curr_attempt_number,
                        roles=list(binding.roles), consumer=endpoint.provider if endpoint else "go_library",
                        argv=argv, prompt=prompt_bytes, instruction_records=instruction_records,
                        postures=sorted({*(["plan"] if is_plan else []),
                                         *(["review"] if is_plan_rev or is_work_rev else []),
                                         *(["work"] if is_prod or is_closeout else [])}) or ["work"],
                        work_tree=work_tree,
                        route=lambda: context_route.ordinary_projection(
                            provider=endpoint.provider if endpoint else None,
                            profile=endpoint.profile if endpoint else None,
                            argv=route_argv, prefix=attempt_id,
                            classes=[c for c, active in (("planning", is_plan),
                                                         ("review_verification", is_plan_rev or is_work_rev),
                                                         ("implementation", is_prod), ("closeout", is_closeout))
                                     if active] or ["implementation"]),
                        facts=[{"kind": "work_class", "value": value} for value in sorted({
                            *( ["planning"] if is_plan else [] ),
                            *( ["review_verification"] if is_plan_rev or is_work_rev else [] ),
                            *( [request.phase_type] if is_prod or is_closeout else [] ),
                        })],
                    )
                    context_adapter.index_reference(context_prepared, conn, run_id, attempt_id)
                    import inspect
                    sig = inspect.signature(runner)
                    if len(sig.parameters) >= 3 and ("binding" in sig.parameters or "run_id" in sig.parameters):
                        runner_kwargs: dict[str, Any] = {"run_id": run_id, "binding": binding, "route": route, "run_dir": run_dir}
                        if "prompt_bytes" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                            runner_kwargs["prompt_bytes"] = prompt_bytes
                        if "argv" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                            runner_kwargs["argv"] = list(argv)
                        if "nonce" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                            runner_kwargs["nonce"] = nonce
                        update_invocation_attempt(conn, attempt_id=attempt_id, status="running")
                        for role in binding.roles:
                            update_semantic_responsibility(
                                conn,
                                id=f"sem-{run_id}-{role}",
                                status="running",
                                started_at=utc_now_iso(),
                            )
                        runner_launched = True
                        t_start = time.time()
                        res_val = context_adapter.invoke(context_prepared, runner, **runner_kwargs)
                        t_elapsed = time.time() - t_start
                        if isinstance(res_val, provider_module.Result):
                            stdout_bytes = res_val.stdout
                            stderr_bytes = res_val.stderr
                            exit_code = res_val.exit_code
                        elif isinstance(res_val, tuple) and len(res_val) >= 3:
                            exit_code, stdout_bytes, stderr_bytes = res_val[:3]
                        elif isinstance(res_val, (bytes, str)):
                            stdout_bytes = res_val if isinstance(res_val, bytes) else res_val.encode("utf-8")
                        elif res_val is None and (is_plan_rev or is_work_rev):
                            stage = "plan_review" if is_plan_rev else "final_review"
                            begin, end = review_result.markers(nonce)
                            stdout_bytes = f"{begin}\n{{\"version\": 1, \"stage\": \"{stage}\", \"outcome\": \"reviewed_with_no_findings\", \"body\": \"Approved.\"}}\n{end}\n".encode("utf-8")
                    else:
                        notice_kwargs: dict[str, Any] = {}
                        if runner is provider_module.run and display is not None:
                            notice_kwargs["on_notice"] = display.stage_notice
                        update_invocation_attempt(conn, attempt_id=attempt_id, status="running")
                        for role in binding.roles:
                            update_semantic_responsibility(
                                conn,
                                id=f"sem-{run_id}-{role}",
                                status="running",
                                started_at=utc_now_iso(),
                            )
                        runner_launched = True
                        t_start = time.time()
                        res = context_adapter.invoke(
                            context_prepared, runner,
                            argv,
                            prompt_bytes,
                            work_tree,
                            provider_module.MAX_STAGE_OUTPUT_BYTES,
                            display.stage_output if display else None,
                            **notice_kwargs,
                        )
                        t_elapsed = time.time() - t_start
                        stdout_bytes = res.stdout
                        stderr_bytes = res.stderr
                        exit_code = res.exit_code
                    worker_session["stdout"] = stdout_bytes
                # 6. Capture worktree post-run
                # Persist raw stdout/stderr for the turn immediately to ensure raw reviewer stdout
                # is preserved even if policy evaluation blocks or parsing fails.
                stdout_file = run_dir / f"{attempt_id}.stdout.md"
                stdout_file.write_bytes(stdout_bytes)
                stderr_file = run_dir / f"{attempt_id}.stderr.txt"
                stderr_file.write_bytes(stderr_bytes)
                (run_dir / f"{binding.binding_id}.stdout.md").write_bytes(stdout_bytes)
                if is_plan_rev:
                    (run_dir / "plan_review.stdout.md").write_bytes(stdout_bytes)
                    record_artifact(
                        conn,
                        artifact_id=f"art-{run_id}-plan-review-stdout",
                        run_id=run_id,
                        artifact_name="plan_review.stdout.md",
                        relative_path="plan_review.stdout.md",
                        size_bytes=len(stdout_bytes),
                        sha256=hashlib.sha256(stdout_bytes).hexdigest(),
                        content_type="text/markdown",
                    )
                elif is_work_rev:
                    (run_dir / "work_review.stdout.md").write_bytes(stdout_bytes)
                    (run_dir / "final_review.stdout.md").write_bytes(stdout_bytes)
                    record_artifact(
                        conn,
                        artifact_id=f"art-{run_id}-work-review-stdout",
                        run_id=run_id,
                        artifact_name="work_review.stdout.md",
                        relative_path="work_review.stdout.md",
                        size_bytes=len(stdout_bytes),
                        sha256=hashlib.sha256(stdout_bytes).hexdigest(),
                        content_type="text/markdown",
                    )

                # 6. Capture worktree post-run with graceful degradation
                tree_after = tree_before
                index_after = None
                head_after = None
                candidate_unavail = False
                index_unavail = False
                head_unavail = False

                try:
                    ident_after = candidate.tree_identity(work_tree)
                    tree_after = str(ident_after.get("tree", tree_before))
                except Exception:
                    candidate_unavail = True

                try:
                    index_after = gitstate_module.index_identity(work_tree)
                except Exception:
                    index_unavail = True

                try:
                    head_after = gitstate_module.current_head(work_tree)
                except Exception:
                    head_unavail = True

                # Check mutation during read-only stage before checking exit code
                eval_obs = None
                if is_read_only:
                    role_str = "work_reviewer" if is_work_rev else ("plan_reviewer" if is_plan_rev else (binding.roles[0] if binding.roles else None))
                    subject_kind_str = "work" if is_work_rev else ("plan" if is_plan_rev else None)
                    obs = review_drift_module.observe_review_drift(
                        work_tree,
                        stage=binding.binding_id,
                        before={
                            "tree": tree_before,
                            "index": index_before,
                            "head": head_before,
                        },
                        after={"tree": tree_after, "observation_unavailable": candidate_unavail},
                        expected_index=index_before,
                        observed_index=index_after,
                        expected_head=head_before,
                        observed_head=head_after,
                        policy=review_mutation_policy,
                        role=role_str,
                        subject_kind=subject_kind_str,
                        sequence=curr_attempt_number - 1,
                        attempt_id=attempt_id,
                        binding_id=binding.binding_id,
                        attempt_number=curr_attempt_number,
                        raw_stdout_artifact=f"{attempt_id}.stdout.md",
                        raw_stderr_artifact=f"{attempt_id}.stderr.txt",
                    )
                    if head_unavail:
                        obs.head_observation_unavailable = True
                        if not any(lim.get("kind") == "head_observation_unavailable" for lim in obs.observation_limitations):
                            obs.observation_limitations.append({"kind": "head_observation_unavailable"})
                    if index_unavail:
                        obs.index_observation_unavailable = True
                        if not any(lim.get("kind") == "index_observation_unavailable" for lim in obs.observation_limitations):
                            obs.observation_limitations.append({"kind": "index_observation_unavailable"})

                    turn_state = {
                        "review_mutation_observations": review_mutation_observations,
                        "review_window_mutation_paths": list(surviving_review_paths),
                    }
                    eval_obs = review_drift_module.apply_review_mutation_policy(
                        obs,
                        policy=review_mutation_policy,
                        state=turn_state,
                        raise_on_block=False,
                    )
                    review_mutation_observations[binding.binding_id] = eval_obs.as_dict()
                    if turn_state.get("review_window_mutation_paths"):
                        surviving_review_paths.update(turn_state["review_window_mutation_paths"])

                    # Write file-backed observation before SQL write
                    obs_file = run_dir / f"{attempt_id}.observation.json"
                    try:
                        obs_file.write_text(json.dumps(eval_obs.as_dict(), indent=2), encoding="utf-8")
                    except Exception:
                        pass

                    sql_indexing_error: Exception | None = None
                    try:
                        record_review_mutation_observation(
                            conn,
                            run_id=run_id,
                            stage=binding.binding_id,
                            sequence=eval_obs.sequence,
                            observation_dict=eval_obs.as_dict(),
                        )
                    except Exception as sql_err:
                        sql_indexing_error = sql_err
                        indexing_failure_file = run_dir / f"{attempt_id}.observation_indexing_failure.json"
                        try:
                            indexing_failure_file.write_text(
                                json.dumps({
                                    "error": str(sql_err),
                                    "attempt_id": attempt_id,
                                    "stage": binding.binding_id,
                                    "observation": eval_obs.as_dict(),
                                }, indent=2),
                                encoding="utf-8",
                            )
                        except Exception:
                            pass
                        eval_obs.observation_limitations.append({
                            "kind": "sql_indexing_failure",
                            "detail": str(sql_err),
                        })
                        review_mutation_observations[binding.binding_id] = eval_obs.as_dict()
                        try:
                            obs_file.write_text(json.dumps(eval_obs.as_dict(), indent=2), encoding="utf-8")
                        except Exception:
                            pass

                    if eval_obs.subject_drift_observed:
                        subject_drift_observed = True
                    if eval_obs.worktree_paths:
                        surviving_review_paths.update(eval_obs.worktree_paths)

                    if eval_obs.action_taken == review_drift_module.ACTION_BLOCKED:
                        attempt_terminalized = True
                        update_invocation_attempt(
                            conn,
                            attempt_id=attempt_id,
                            status="failed",
                            exit_code=exit_code,
                            completed_at=utc_now_iso(),
                        )
                        for b_role in binding.roles:
                            update_semantic_responsibility(
                                conn,
                                id=f"sem-{run_id}-{b_role}",
                                status="failed",
                                completed_at=utc_now_iso(),
                                outcome="failed",
                            )
                        if display is not None:
                            _safe_display_call(display.stage_failed, binding.binding_id, eval_obs.detail)
                        raise V2TurnError(
                            f"read-only turn {binding.binding_id} mutated worktree; violated review mutation policy: {eval_obs.detail}"
                        )
                    elif eval_obs.action_taken == review_drift_module.ACTION_WARNED:
                        if display is not None:
                            _safe_display_call(
                                getattr(display, "stage_notice", None) or getattr(display, "note", None),
                                binding.binding_id,
                                eval_obs.detail,
                            )
                    if sql_indexing_error is not None and exit_code == 0:
                        obs_file_ok = False
                        try:
                            obs_file_ok = obs_file.is_file() and obs_file.stat().st_size > 0
                        except Exception:
                            obs_file_ok = False
                        if not obs_file_ok:
                            attempt_terminalized = True
                            update_invocation_attempt(
                                conn,
                                attempt_id=attempt_id,
                                status="failed",
                                exit_code=exit_code,
                                completed_at=utc_now_iso(),
                            )
                            raise V2TurnError(
                                f"observation sinks completely failed for {binding.binding_id}: {sql_indexing_error}"
                            )
                        if display is not None:
                            _safe_display_call(
                                getattr(display, "stage_notice", None) or getattr(display, "note", None),
                                binding.binding_id,
                                f"observation SQL indexing nonfatal failure: {sql_indexing_error}",
                            )

                # Check exit code per Finding F2 ordering
                if exit_code != 0:
                    attempt_terminalized = True
                    if display is not None:
                        _safe_display_call(display.stage_failed, binding.binding_id, f"exit {exit_code}")
                    disposition = handle_turn_failure(
                        conn,
                        run_id=run_id,
                        run_dir=run_dir,
                        binding=binding,
                        attempt_id=attempt_id,
                        attempt_number=curr_attempt_number,
                        provider=route.provider,
                        profile=route.profile,
                        endpoint_alias=route.endpoint_alias,
                        exit_code=exit_code,
                        stdout_bytes=stdout_bytes,
                        stderr_bytes=stderr_bytes,
                        tree_before=tree_before,
                        tree_after=tree_after,
                        now=now,
                    )
                    rerouted, next_route, next_att_num = orchestrate_dynamic_retry(
                        conn,
                        run_id=run_id,
                        run_dir=run_dir,
                        phase_type=request.phase_type,
                        execution_mode=execution_mode,
                        binding=binding,
                        current_attempt_number=curr_attempt_number,
                        current_attempt_id=attempt_id,
                        caps_catalog=caps_catalog,
                        injected_observations=effective_injected,
                        prior_resolutions=prior_resolutions,
                        disposition=disposition,
                        now=now,
                        root=repository_root,
                        bundle=snap.bundle,
                    )
                    if rerouted and next_route is not None:
                        predecessor_id = attempt_id
                        curr_attempt_number = next_att_num
                        continue
                    else:
                        for role in binding.roles:
                            update_semantic_responsibility(
                                conn,
                                id=f"sem-{run_id}-{role}",
                                status="failed",
                                completed_at=utc_now_iso(),
                                outcome="failed",
                            )
                        err_msg = disposition.sanitized_error or f"exit code {exit_code}"
                        if disposition.substantive:
                            raise SubstantiveFailureError(f"Turn {binding.binding_id} failed substantively: {err_msg}")
                        raise StartupFailureError(f"Turn {binding.binding_id} failed before substantive output: {err_msg}")

                # 7. Post-turn artifact & record processing
                if is_plan:
                    plan_file = run_dir / "plan-material.md"
                    if not plan_file.exists():
                        try:
                            mat = plan_material.materialize(stdout_bytes, route.provider, route.profile, _home=run_dir.parent.parent)
                            plan_material_text = mat.data.decode("utf-8", errors="replace")
                        except Exception:
                            plan_material_text = stdout_bytes.decode("utf-8", errors="replace") or "Plan draft."
                        plan_file.write_text(plan_material_text, encoding="utf-8")
                    else:
                        plan_material_text = plan_file.read_text(encoding="utf-8")

                    p_digest = hashlib.sha256(plan_material_text.encode("utf-8")).hexdigest()
                    record_artifact(
                        conn,
                        artifact_id=f"art-{run_id}-plan-material",
                        run_id=run_id,
                        artifact_name="plan-material.md",
                        relative_path="plan-material.md",
                        size_bytes=len(plan_material_text.encode("utf-8")),
                        sha256=p_digest,
                        content_type="text/markdown",
                    )
                    save_plan_candidate(
                        conn, run_id, "plan-material.md", p_digest,
                        len(plan_material_text.encode("utf-8")), route.provider, route.profile,
                    )

                if is_plan_rev:
                    try:
                        parsed_rev = review_result.parse(stdout_bytes, "plan_review", nonce)
                    except Exception as exc:
                        raise V2TurnError(f"Plan review stage failed to parse review result: {exc}") from exc

                    plan_review_outcome = parsed_rev.outcome
                    body = parsed_rev.body
                    if plan_review_outcome == "reviewed_with_findings":
                        plan_findings = extract_findings_from_body(body)
                        plan_disposition = "amend"
                    elif plan_review_outcome == "unreviewable":
                        plan_findings = extract_findings_from_body(body)
                        plan_disposition = "reject"
                    else:
                        plan_findings = []
                        plan_disposition = "accept"

                    plan_review_id = save_review(
                        conn,
                        run_id,
                        "plan_reviewer",
                        "plan_review",
                        route.provider,
                        route.profile,
                        plan_review_outcome,
                        body,
                        findings=plan_findings,
                    )
                    rev_bytes = json.dumps({"outcome": plan_review_outcome, "body": body}).encode("utf-8")
                    record_artifact(
                        conn,
                        artifact_id=f"art-{run_id}-plan-review",
                        run_id=run_id,
                        artifact_name="plan_review.result.json",
                        relative_path="plan_review.result.json",
                        size_bytes=len(rev_bytes),
                        sha256=hashlib.sha256(rev_bytes).hexdigest(),
                        content_type="application/json",
                    )

                if ROLE_PLAN_REVIEW_DISPOSITION in binding.roles and plan_review_id:
                    rationale = f"Plan review outcome {plan_review_outcome} dispositioned as {plan_disposition}."
                    save_disposition(conn, run_id, "plan_review_disposition", plan_review_id, plan_disposition, rationale)
                    if plan_disposition == "reject":
                        attempt_terminalized = True
                        update_invocation_attempt(conn, attempt_id=attempt_id, status="failed", completed_at=utc_now_iso())
                        for role in binding.roles:
                            update_semantic_responsibility(conn, id=f"sem-{run_id}-{role}", status="failed", completed_at=utc_now_iso(), outcome="failed")
                        if display is not None:
                            _safe_display_call(display.stage_failed, binding.binding_id, "plan review rejected proposed plan")
                        raise V2TurnError(f"Plan review rejected proposed plan ({plan_review_outcome}): cannot proceed to implementation")

                if is_prod:
                    producer_candidate_tree = tree_after
                    try:
                        candidate_delta = candidate.tree_delta(work_tree, initial_tree, producer_candidate_tree)
                    except Exception:
                        candidate_delta = []
                    work_stdout = stdout_bytes.decode("utf-8", errors="replace")
                    cand_id = f"cand-{run_id}-work"
                    record_candidate(
                        conn,
                        candidate_id=cand_id,
                        run_id=run_id,
                        responsibility_name="producer",
                        candidate_type="git_tree",
                        tree_sha=producer_candidate_tree,
                        head_sha=initial_head,
                    )
                    w_file = run_dir / "work.stdout.md"
                    w_file.write_text(work_stdout, encoding="utf-8")
                    record_artifact(
                        conn,
                        artifact_id=f"art-{run_id}-work-stdout",
                        run_id=run_id,
                        artifact_name="work.stdout.md",
                        relative_path="work.stdout.md",
                        size_bytes=len(work_stdout.encode("utf-8")),
                        sha256=hashlib.sha256(work_stdout.encode("utf-8")).hexdigest(),
                        content_type="text/markdown",
                    )

                if is_work_rev:
                    try:
                        parsed_rev = review_result.parse(stdout_bytes, "final_review", nonce)
                    except Exception as exc:
                        raise V2TurnError(f"Work review stage failed to parse review result: {exc}") from exc

                    work_review_outcome = parsed_rev.outcome
                    body = parsed_rev.body
                    if work_review_outcome == "reviewed_with_findings":
                        work_findings = extract_findings_from_body(body)
                        work_disposition = "amend"
                    elif work_review_outcome == "unreviewable":
                        work_findings = extract_findings_from_body(body)
                        work_disposition = "reject"
                    else:
                        work_findings = []
                        work_disposition = "accept"

                    work_review_id = save_review(
                        conn,
                        run_id,
                        "work_reviewer",
                        "final_review",
                        route.provider,
                        route.profile,
                        work_review_outcome,
                        body,
                        findings=work_findings,
                        candidate_id=f"cand-{run_id}-work",
                    )
                    w_rev_bytes = json.dumps({"outcome": work_review_outcome, "body": body}).encode("utf-8")
                    record_artifact(
                        conn,
                        artifact_id=f"art-{run_id}-work-review",
                        run_id=run_id,
                        artifact_name="final_review.result.json",
                        relative_path="final_review.result.json",
                        size_bytes=len(w_rev_bytes),
                        sha256=hashlib.sha256(w_rev_bytes).hexdigest(),
                        content_type="application/json",
                    )
                    work_review_candidate_tree = producer_candidate_tree or tree_before
                    work_review_obs = eval_obs
                    work_review_receipt_valid = work_review_outcome not in ("unreviewable", "")

                if ROLE_WORK_REVIEW_DISPOSITION in binding.roles and work_review_id:
                    rationale = f"Work review outcome {work_review_outcome} dispositioned as {work_disposition}."
                    save_disposition(conn, run_id, "work_review_disposition", work_review_id, work_disposition, rationale)

                if ROLE_REVISER in binding.roles:
                    if work_disposition == "amend" or (tree_after != producer_candidate_tree and bool(producer_candidate_tree)):
                        record_candidate(
                            conn,
                            candidate_id=f"cand-{run_id}-revision",
                            run_id=run_id,
                            responsibility_name="reviser",
                            candidate_type="git_tree",
                            tree_sha=tree_after,
                            head_sha=initial_head,
                        )

                if ROLE_CLOSEOUT_AGENT in binding.roles:
                    try:
                        parsed_closeout = result_module.parse(stdout_bytes, "closeout", nonce)
                    except Exception as exc:
                        if not repair_attempted and is_v2_repair_eligible(exc, stdout_bytes, nonce):
                            repair_attempted = True
                            if display is not None:
                                _safe_display_call(display.stage_notice, "result_repair", "Attempting formatting-only result repair")
                            try:
                                parsed_closeout, result_repair_evidence = execute_v2_result_repair(
                                    conn=conn,
                                    run_id=run_id,
                                    run_dir=run_dir,
                                    repository_root=repository_root,
                                    work_tree=work_tree,
                                    binding=binding,
                                    route=route,
                                    endpoint=endpoint,
                                    stdout_bytes=stdout_bytes,
                                    stderr_bytes=stderr_bytes,
                                    exit_code=exit_code,
                                    initial_head=initial_head,
                                    tree_after=tree_after,
                                    runner=runner,
                                    display=display,
                                    original_error=exc if isinstance(exc, result_module.ResultError) else result_module.ResultError("RESULT_INVALID", str(exc)),
                                    attempt_id=attempt_id,
                                    curr_attempt_number=curr_attempt_number,
                                )
                            except Exception as repair_exc:
                                attempt_terminalized = True
                                update_invocation_attempt(
                                    conn, attempt_id=attempt_id, status="failed", exit_code=exit_code, completed_at=utc_now_iso()
                                )
                                for role in binding.roles:
                                    update_semantic_responsibility(
                                        conn, id=f"sem-{run_id}-{role}", status="failed", completed_at=utc_now_iso(), outcome="failed"
                                    )
                                if display is not None:
                                    _safe_display_call(display.stage_failed, binding.binding_id, f"closeout result repair failed: {repair_exc}")
                                raise V2TurnError(f"Closeout stage failed to parse terminal result: {repair_exc}") from repair_exc
                        else:
                            attempt_terminalized = True
                            update_invocation_attempt(conn, attempt_id=attempt_id, status="failed", exit_code=exit_code, completed_at=utc_now_iso())
                            for role in binding.roles:
                                update_semantic_responsibility(conn, id=f"sem-{run_id}-{role}", status="failed", completed_at=utc_now_iso(), outcome="failed")
                            if display is not None:
                                _safe_display_call(display.stage_failed, binding.binding_id, f"closeout result contract failed: {exc}")
                            raise V2TurnError(f"Closeout stage failed to parse terminal result: {exc}") from exc

                    if not parsed_closeout.completed:
                        attempt_terminalized = True
                        update_invocation_attempt(conn, attempt_id=attempt_id, status="failed", exit_code=exit_code, completed_at=utc_now_iso())
                        for role in binding.roles:
                            update_semantic_responsibility(conn, id=f"sem-{run_id}-{role}", status="failed", completed_at=utc_now_iso(), outcome="failed")
                        if display is not None:
                            _safe_display_call(display.stage_failed, binding.binding_id, f"closeout outcome is not completed: {parsed_closeout.outcome}")
                        raise V2TurnError(f"Closeout outcome is not completed: {parsed_closeout.outcome}")

                    closeout_stage_result = parsed_closeout
                    closer_terminal_tree = tree_after
                    final_outcome = "rejected" if work_disposition == "reject" else "completed"
                    receipt_id = f"rcpt-{run_id}-closeout"
                    record_completion_receipt(
                        conn,
                        receipt_id=receipt_id,
                        run_id=run_id,
                        final_head=initial_head,
                        finalization_policy=finalization_policy,
                        finalization_outcome=final_outcome,
                        receipt={"status": final_outcome, "final_tree": tree_after},
                    )
                    if work_disposition == "reject":
                        attempt_terminalized = True
                        update_invocation_attempt(conn, attempt_id=attempt_id, status="failed", exit_code=exit_code, completed_at=utc_now_iso())
                        for role in binding.roles:
                            update_semantic_responsibility(conn, id=f"sem-{run_id}-{role}", status="failed", completed_at=utc_now_iso(), outcome="failed")
                        if display is not None:
                            _safe_display_call(display.stage_failed, binding.binding_id, "work review rejected candidate")
                        raise V2TurnError(f"Work review rejected candidate ({work_review_outcome}): closeout failed")

                # 8. Complete attempt and semantic responsibilities
                update_invocation_attempt(
                    conn,
                    attempt_id=attempt_id,
                    status="completed",
                    exit_code=exit_code,
                    completed_at=utc_now_iso(),
                )

                for role in binding.roles:
                    update_semantic_responsibility(
                        conn,
                        id=f"sem-{run_id}-{role}",
                        status="completed",
                        completed_at=utc_now_iso(),
                        outcome="completed",
                    )
                attempt_terminalized = True
                if display is not None:
                    _safe_display_call(display.stage_finished, binding.binding_id, exit_code, t_elapsed)
                break
            except BaseException as exc:
                if context_prepared.get("reference") and not context_prepared.get("invoked"):
                    from . import context_adapter
                    context_adapter.observe(context_prepared, status="not_started")
                had_prior_terminalization = attempt_terminalized
                if not attempt_terminalized:
                    attempt_terminalized = True
                    if not runner_launched:
                        update_invocation_attempt(
                            conn,
                            attempt_id=attempt_id,
                            status="failed_pre_launch",
                            completed_at=utc_now_iso(),
                        )
                        for role in binding.roles:
                            update_semantic_responsibility(
                                conn,
                                id=f"sem-{run_id}-{role}",
                                status="failed",
                                completed_at=utc_now_iso(),
                                outcome="failed_pre_launch",
                            )
                    else:
                        update_invocation_attempt(
                            conn,
                            attempt_id=attempt_id,
                            status="failed",
                            exit_code=exit_code,
                            completed_at=utc_now_iso(),
                        )
                        for role in binding.roles:
                            update_semantic_responsibility(
                                conn,
                                id=f"sem-{run_id}-{role}",
                                status="failed",
                                completed_at=utc_now_iso(),
                                outcome="failed",
                            )
                if display is not None and not had_prior_terminalization:
                    _safe_display_call(display.stage_failed, binding.binding_id, str(exc))
                if not runner_launched and isinstance(exc, Exception):
                    if isinstance(exc, PreLaunchFailureError):
                        raise
                    raise PreLaunchFailureError(f"Turn {binding.binding_id} failed before provider launch: {exc}") from exc
                if isinstance(exc, V2TurnError):
                    raise
                raise
            finally:
                _record_v2_observation(
                    run_dir, run_id, binding, attempt_id, attempt_number_at_start,
                    attempt_predecessor_id, route, request, execution_mode, work_tree, apgr_home,
                    context_prepared, observation_active, sys.exc_info()[1],
                    observation_worker_parent,
                )

    final_tree = str(candidate.tree_identity(work_tree).get("tree", initial_tree))
    closer_mutated = bool(closer_entry_tree and closer_terminal_tree and closer_entry_tree != closer_terminal_tree)
    final_candidate_reviewed = review_drift_module.derive_final_candidate_freshness(
        work_review_observation=work_review_obs,
        work_review_candidate_tree=work_review_candidate_tree,
        terminal_candidate_tree=final_tree,
        has_verified_receipt=work_review_receipt_valid,
        closer_mutated=closer_mutated,
    )

    return {
        "final_tree": final_tree,
        "prior_resolutions": prior_resolutions,
        "closeout_stage_result": closeout_stage_result,
        "result_repair": result_repair_evidence,
        "review_mutation_observations": review_mutation_observations,
        "subject_drift_observed": subject_drift_observed,
        "final_candidate_reviewed": final_candidate_reviewed,
        "surviving_review_paths": sorted(surviving_review_paths),
    }


def _record_v2_observation(run_dir, run_id, binding, attempt_id, attempt_number,
                           predecessor_id, route, request, execution_mode, work_tree,
                           apgr_home, prepared, active, error,
                           worker_parent_id=None) -> None:
    """Optional attempt observation; a failure is a bounded notice only."""
    try:
        from . import observations as observations_module
        if active is None:
            active = observations_module.configured(project_root=work_tree, apgr_home=apgr_home)
        disposition = observations_module.record_attempt(
            run_dir, attempt_id, active=active, error=error, dispatcher="v2",
            run_id=run_id, binding_id=binding.binding_id, attempt_id=attempt_id,
            attempt_number=attempt_number,
            invocation_kind="semantic", predecessor_attempt_id=predecessor_id,
            # Only a parent actually registered by bound_workers, as in V1.
            worker_parent_id=worker_parent_id,
            task={"project": None, "phase_type": request.phase_type,
                  "execution_mode": execution_mode, "category": None},
            route={"provider": route.provider, "profile": route.profile,
                   "endpoint_alias": route.endpoint_alias, "requested_model": None,
                   "requested_effort": None, "source": None},
            build=observations_module.build_identity(None), prepared=prepared,
            artifacts={"stdout": f"{attempt_id}.stdout.md", "stderr": f"{attempt_id}.stderr.txt"},
        )
        diagnostic = disposition.get("diagnostic") if disposition["status"] == "failed" else None
    except Exception as failure:
        diagnostic = type(failure).__name__
    if diagnostic is not None:
        try:
            sys.stderr.write(f"apgr: optional observation not recorded ({diagnostic})\n")
        except Exception:
            pass


from functools import wraps
@wraps(_execute_v2_turns)
def execute_v2_turns(*args, **kwargs):
    """Pin one bundle across the V2 launch path and its child processes."""
    import inspect
    from .runtime_models import launch_capture
    bound = inspect.signature(_execute_v2_turns).bind(*args, **kwargs)
    bound.apply_defaults()
    values = bound.arguments
    snap = values["roster"] or load_roster(values["repository_root"], apgr_home=values["apgr_home"])
    values["roster"] = snap
    with launch_capture(snap.bundle, values["run_dir"]):
        return _execute_v2_turns(*bound.args, **bound.kwargs)
