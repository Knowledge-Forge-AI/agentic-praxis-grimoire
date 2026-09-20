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
import sqlite3
import time
from typing import Any

from .v2_repair import execute_v2_result_repair, is_v2_repair_eligible
from . import (
    candidate,
    plan_material,
    provider as provider_module,
    result as result_module,
    review_result,
)
from .capabilities import EndpointCapabilities
from .config_routing import RETAINED_STATIC_MODES
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
    record_route_resolution,
    update_invocation_attempt,
    update_semantic_responsibility,
    utc_now_iso,
)
from .request import PhaseRequestV2
from .roster import load_roster
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




def execute_v2_turns(
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
    snap = load_roster(repository_root)
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
                    )
                else:
                    route = resolve_dynamic_route(
                        binding,
                        request.phase_type,
                        capabilities_catalog=caps_catalog,
                        operational_observations=operational_observations,
                        prior_resolutions=prior_resolutions,
                        now=now,
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
            attempt_terminalized = False
            t_elapsed = 0.0

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
                    )
                else:
                    prompt_bytes = request.prompt.encode("utf-8")

                # 4. Enforce read-only process posture
                is_read_only = binding.process_read_only
                ident_before = candidate.tree_identity(work_tree)
                tree_before = str(ident_before.get("tree", initial_tree))

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
                        read_only=is_read_only,
                    )
                    if endpoint is not None
                    else ["mock-provider", route.endpoint_alias]
                )

                import inspect
                sig = inspect.signature(runner)
                if len(sig.parameters) >= 3 and ("binding" in sig.parameters or "run_id" in sig.parameters):
                    runner_kwargs: dict[str, Any] = {"run_id": run_id, "binding": binding, "route": route, "run_dir": run_dir}
                    if "prompt_bytes" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                        runner_kwargs["prompt_bytes"] = prompt_bytes
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
                    res_val = runner(**runner_kwargs)
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
                    res = runner(
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

                # 6. Capture worktree post-run
                ident_after = candidate.tree_identity(work_tree)
                tree_after = str(ident_after.get("tree", tree_before))

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

                # Check mutation during read-only stage
                if is_read_only and tree_after != tree_before:
                    attempt_terminalized = True
                    update_invocation_attempt(
                        conn,
                        attempt_id=attempt_id,
                        status="failed",
                        exit_code=exit_code or 1,
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
                    if display is not None:
                        _safe_display_call(display.stage_failed, binding.binding_id, "read-only turn mutated worktree")
                    raise V2TurnError(
                        f"read-only turn {binding.binding_id} mutated worktree: before {tree_before} != after {tree_after}"
                    )

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

    final_tree = str(candidate.tree_identity(work_tree).get("tree", initial_tree))

    return {
        "final_tree": final_tree,
        "prior_resolutions": prior_resolutions,
        "closeout_stage_result": closeout_stage_result,
        "result_repair": result_repair_evidence,
    }
