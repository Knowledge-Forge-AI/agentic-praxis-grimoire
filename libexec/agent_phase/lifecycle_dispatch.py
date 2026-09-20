"""Execution helpers for non-standard lifecycle specifications."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from . import candidate as candidate_module
from . import capacity as capacity_module
from . import envelope as envelope_module
from . import finalization as finalization_module
from . import gitstate as gitstate_module
from . import provider as provider_module
from . import plan_material as plan_material_module
from . import result as result_module
from . import result_repair as result_repair_module
from . import review_result as review_result_module
from . import stage_delta as stage_delta_module
from .transport import PromptLimitError, ensure_prompt_fits


REVIEW_ARTIFACT_SCHEMA = "agent-phase-review-artifact-v1"
REVISOR_REVISION_SCHEMA = "agent-phase-revisor-revision-v1"
PRODUCER_EVIDENCE_SCHEMA = "agent-phase-producer-evidence-v1"

_CLOSER_DISPOSITIONS = frozenset(
    {"accept", "amend", "reject", "defer", "supersede"}
)
_CLOSER_REPORT_LABEL = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?(disposition|rationale|qualification[ \t]+evidence|unresolved[ \t]+concerns)[ \t]*:[ \t]*(.*)$",
    re.IGNORECASE,
)


def terminal_narrative_fields(body: str) -> dict[str, str | None]:
    """Extract only explicitly labelled closer report fields.

    Terminal results intentionally retain a free-form narrative for backward
    compatibility.  A field is populated only when the provider uses one of
    the canonical labels, so normal prose or the terminal outcome can never be
    mistaken for a disposition, qualification claim, or absence of concerns.
    Label values may continue on subsequent lines until another canonical
    label begins.  Unknown labels remain part of the narrative and are not
    interpreted.
    """
    fields: dict[str, str | None] = {
        "closer_disposition": None,
        "closer_rationale": None,
        "qualification_evidence": None,
        "unresolved_concerns": None,
    }
    matches: list[tuple[str, str, int, int]] = []
    lines = body.splitlines(keepends=True)
    offset = 0
    for line in lines:
        match = _CLOSER_REPORT_LABEL.match(line.rstrip("\r\n"))
        if match is not None:
            label = re.sub(r"[ \t]+", " ", match.group(1).lower())
            matches.append((label, match.group(2), offset, offset + len(line)))
        offset += len(line)
    for index, (label, first_value, _start, end) in enumerate(matches):
        next_start = matches[index + 1][2] if index + 1 < len(matches) else len(body)
        value = body[end:next_start]
        first_value = first_value.strip()
        if first_value:
            value = first_value + ("\n" + value if value else "")
        value = value.strip()
        if label == "disposition":
            normalized = value.casefold()
            if normalized in _CLOSER_DISPOSITIONS:
                fields["closer_disposition"] = normalized
        elif label == "rationale":
            fields["closer_rationale"] = value or None
        elif label == "qualification evidence":
            fields["qualification_evidence"] = value or None
        elif label == "unresolved concerns":
            fields["unresolved_concerns"] = value or None
    return fields


def record_terminal_narrative(state: dict[str, Any], body: str) -> None:
    """Retain terminal prose and its explicitly labelled disposition fields."""
    state["closer_narrative"] = body
    state.update(terminal_narrative_fields(body))


def _binding_text(binding: dict[str, Any]) -> str:
    """Render dispatcher-owned binding metadata without provider prose."""
    return json.dumps(binding, sort_keys=True, separators=(",", ":"))


def _review_artifact(
    stage: Any, parsed: review_result_module.ReviewResult
) -> dict[str, Any]:
    body = parsed.body.encode("utf-8")
    return {
        "schema": REVIEW_ARTIFACT_SCHEMA,
        "name": f"{stage.prefix}.result.json",
        "stage": stage.name,
        "checkpoint": stage.checkpoint,
        "outcome": parsed.outcome,
        "independent": True,
        "body_bytes": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest(),
    }


def record_review_artifact(
    state: dict[str, Any], stage: Any, parsed: review_result_module.ReviewResult
) -> dict[str, Any]:
    """Retain a neutral, named record while preserving review_outcomes."""
    artifact = _review_artifact(stage, parsed)
    artifacts = state.setdefault("review_artifacts", [])
    if not isinstance(artifacts, list):
        artifacts = []
        state["review_artifacts"] = artifacts
    artifacts[:] = [
        item for item in artifacts
        if isinstance(item, dict) and item.get("name") != artifact["name"]
    ]
    artifacts.append(artifact)
    state["review_artifact_names"] = [item["name"] for item in artifacts]
    state["review_artifact_outcomes"] = {
        item["stage"]: item["outcome"]
        for item in artifacts
        if isinstance(item.get("stage"), str)
        and isinstance(item.get("outcome"), str)
    }
    return artifact


def record_producer_evidence(
    state: dict[str, Any],
    stage: str,
    output: bytes,
    forwarded_to: str,
    *,
    optional: bool = True,
    artifact_name: str | None = None,
) -> dict[str, Any]:
    """Record the producer artifact that was forwarded to a dispositioner."""
    evidence = {
        "schema": PRODUCER_EVIDENCE_SCHEMA,
        "stage": stage,
        "artifact_name": artifact_name if artifact_name is not None else f"{stage}.stdout.md",
        "bytes": len(output),
        "sha256": hashlib.sha256(output).hexdigest(),
        "forwarded_to": forwarded_to,
        "optional": optional,
    }
    state["producer_evidence"] = evidence
    return evidence


def record_revisor_revision(
    dispatcher: Any,
    state: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    stage: Any,
    review_stage: str,
) -> dict[str, Any]:
    """Record the exact terminal revision and its post-review boundary."""
    paths = candidate_module.tree_delta(
        dispatcher.cwd, str(before["tree"]), str(after["tree"])
    )
    revision = {
        "schema": REVISOR_REVISION_SCHEMA,
        "stage": stage.name,
        "review_stage": review_stage,
        "before": before,
        "after": after,
        "paths": paths,
        "authorized": bool(stage.is_mutating),
        "terminal_bytes_verified": bool(state.get("terminal_bytes_verified")),
        "independent_review_after_revision": False,
    }
    state["post_revisor_review"] = {
        "performed": False,
        "automatic": False,
        "reason": "selected lifecycle has no post-revisor independent review",
    }
    if not paths:
        state.pop("authorized_revisor_revisions", None)
        state.pop("revisor_revisions", None)
        return revision
    state["authorized_revisor_revisions"] = revision
    # Neutral alias retained alongside the explicit role-oriented field.
    state["revisor_revisions"] = revision
    return revision


def terminal_contract(stage: str, begin: str, end: str) -> str:
    return envelope_module.terminal_result_contract(stage).format(
        begin=begin, end=end
    )


def bind_plan(
    data: bytes,
    provider: str | None = None,
    profile: str | None = None,
    directory: Any | None = None,
) -> dict[str, object]:
    from .dispatch import DispatchError

    try:
        if provider is not None or profile is not None:
            if provider is None or profile is None:
                raise DispatchError(
                    "plan provider and profile must be supplied together",
                    "PLAN_ARTIFACT_INVALID",
                )
            material = plan_material_module.materialize(data, provider, profile)
            if directory is not None:
                plan_material_module.write(directory, material)
            return material.binding
        return candidate_module.plan_identity(data)
    except (
        candidate_module.PlanArtifactError,
        plan_material_module.PlanMaterialError,
    ) as error:
        raise DispatchError(str(error), error.code) from error


def materialize_plan(
    directory: Any,
    data: bytes,
    provider: str,
    profile: str,
) -> plan_material_module.PlanMaterial:
    """Bind and archive one canonical plan before an independent review."""

    try:
        material = plan_material_module.materialize(data, provider, profile)
        plan_material_module.write(directory, material)
        return material
    except plan_material_module.PlanMaterialError as error:
        from .dispatch import DispatchError

        raise DispatchError(str(error), error.code) from error


def require_unchanged(
    dispatcher: Any,
    state: dict[str, Any],
    before: dict[str, Any],
    stage: str,
    expected_index: dict[str, Any],
    candidate_code: str = "READ_ONLY_STAGE_MUTATED_CANDIDATE",
    strict: bool = False,
) -> None:
    from .dispatch import DispatchError

    entry = state.get("entry")
    if not strict:
        if entry is not None:
            stage_delta_module.normalize_index_if_needed(
                dispatcher.cwd, expected_index, state, stage_name=stage
            )
        # Recompute both identities after normalization.  A staged untracked
        # metadata path must not be folded into the candidate tree that is
        # captured for this boundary.
        after = candidate_module.tree_identity(dispatcher.cwd)
        observed_index = gitstate_module.index_identity(dispatcher.cwd)
        # Compatibility fallback: normal _stage execution already closed StageBoundary.
        stage_delta_module.capture_stage_boundary(
            dispatcher.cwd,
            state,
            stage=stage,
            before_tree=before["tree"],
            after_tree=after["tree"],
            before_index=expected_index,
            after_index=observed_index,
            entry=entry,
        )
        return

    after = candidate_module.tree_identity(dispatcher.cwd)
    observed_index = gitstate_module.index_identity(dispatcher.cwd)
    tree_changed = after["tree"] != before["tree"]
    index_changed = observed_index != expected_index
    if not tree_changed and not index_changed:
        return

    paths = (
        candidate_module.tree_delta(
            dispatcher.cwd, str(before["tree"]), str(after["tree"])
        )
        if tree_changed else []
    )
    state[f"{stage}_mutation"] = {
        "expected_tree": before["tree"],
        "observed_tree": after["tree"],
        "paths": paths,
        "expected_index": expected_index,
        "observed_index": observed_index,
    }
    if index_changed:
        code = "READ_ONLY_STAGE_MUTATED_INDEX"
        detail = f"read-only stage {stage} mutated the real index"
    else:
        code = candidate_code
        detail = f"read-only stage {stage} mutated the worktree: {paths}"
    state["blocking_reason"] = {
        "code": code,
        "detail": detail,
    }
    state["outcome"] = "blocked"
    raise DispatchError(f"{code}: {detail}", code)


def complete_review(
    dispatcher: Any,
    directory: Any,
    state: dict[str, Any],
    stage: Any,
    result: provider_module.Result,
    nonce: str,
    *,
    resumed: bool = False,
) -> review_result_module.ReviewResult:
    from . import review_binding

    # Close the post-transport/parser seam against the original review binding.
    binding = state.get("immutable_review_bindings", {}).get(stage.name)
    if binding is not None:
        stage_delta_module.normalize_index_if_needed(
            dispatcher.cwd, binding["index"], state, stage_name=stage.name,
        )
    review_binding.verify(dispatcher.cwd, state, stage.name)

    try:
        parsed = review_result_module.parse(result.stdout, stage.name, nonce)
    except review_result_module.ReviewResultError as error:
        from .review_recovery import retry_review

        parsed = retry_review(dispatcher, directory, state, stage, nonce, error)
    review_binding.verify(dispatcher.cwd, state, stage.name)
    directory.write_json(f"{stage.prefix}.result.json", parsed.as_dict())
    state.setdefault("review_outcomes", {})[stage.name] = parsed.outcome
    record_review_artifact(state, stage, parsed)
    # The plan and standard work candidates use legacy stage keys. Populate
    # neutral role aliases at the point their exact read-only binding is
    # available, without changing those legacy keys.
    if stage.name == envelope_module.STAGE_PLAN_REVIEW:
        proposal = state.get("plan_candidate")
        if isinstance(proposal, dict):
            state["proposal_binding"] = proposal
            state["plan_proposal_binding"] = proposal
    elif stage.name == envelope_module.STAGE_FINAL_REVIEW:
        product = state.get("pre_final_candidate")
        if isinstance(product, dict):
            state["producer_binding"] = product
            state["work_product_binding"] = product
        state["final_review"] = parsed.outcome
    if not parsed.reviewable:
        state.setdefault("review_advisories", []).append(
            f"{stage.name} reported the bound subject unreviewable: {parsed.body[:2000]}"
        )
    checkpoint = str(stage.checkpoint)
    state["checkpoints_completed"].append(checkpoint)
    if resumed:
        state["effective_checkpoints"].append(checkpoint)
    dispatcher.display.checkpoint(checkpoint)
    return parsed


def complete_terminal(
    dispatcher: Any,
    directory: Any,
    state: dict[str, Any],
    entry: Any,
    stage: Any,
    result: provider_module.Result,
    nonce: str,
    endpoint: Any | None = None,
) -> dict[str, Any]:
    from .dispatch import DispatchError

    # Successful terminal-only lifecycles still expose stable additive review
    # containers; review-bearing lifecycles already populated them upstream.
    state.setdefault("review_artifacts", [])
    state.setdefault("review_artifact_names", [])
    state.setdefault("review_artifact_outcomes", {})
    state.setdefault(
        "post_revisor_review",
        {
            "performed": False,
            "automatic": False,
            "reason": "selected lifecycle has no post-revisor independent review",
        },
    )

    def block(code: str, detail: str) -> DispatchError:
        state["blocking_reason"] = {"code": code, "detail": detail}
        state["outcome"] = "blocked"
        state["complete"] = False
        if state.get("semantic_outcome") is None:
            state["semantic_outcome"] = "blocked"
        if not state.get("finalization_attempted"):
            state.setdefault("finalization_outcome", "not_attempted")
        return DispatchError(f"{code}: {detail}", code)

    # Capture the terminal candidate, ownership delta, and transport facts
    # before parsing. A malformed result must never erase the candidate bytes
    # that preceded it, even when the outer failure path writes artifacts.
    if endpoint is None:
        endpoint = getattr(dispatcher, "_terminal_endpoint", None)
    if endpoint is not None:
        try:
            verified = result_repair_module._candidate_boundary(
                dispatcher, state, entry, stage
            )
            state["terminal_transport"] = result_repair_module._transport_record(
                stage.name, endpoint, result
            )
            state["terminal_bytes_verified"] = verified
            for key in ("authorized_revisor_revisions", "revisor_revisions"):
                revision = state.get(key)
                if isinstance(revision, dict):
                    revision["terminal_bytes_verified"] = verified
        except (candidate_module.CandidateError, gitstate_module.GitStateError) as error:
            state["terminal_bytes_verified"] = False
            for key in ("authorized_revisor_revisions", "revisor_revisions"):
                revision = state.get(key)
                if isinstance(revision, dict):
                    revision["terminal_bytes_verified"] = False
            state["terminal_boundary_capture"] = {
                "status": "failed",
                "code": getattr(error, "code", type(error).__name__),
                "detail": str(error),
            }
    state["finalization_attempted"] = False
    state.setdefault("finalization_outcome", "not_attempted")
    state["effective_stages"] = {
        name: "performed" for name in state.get("stages_completed", [])
    }
    state["effective_checkpoints"] = list(state.get("checkpoints_completed", []))
    state["effective_review_count"] = len(state["effective_checkpoints"])
    dispatcher._update_invocation_accounting(state)
    directory.write_json("state.json", state)
    try:
        parsed = result_module.parse(result.stdout, stage.name, nonce)
    except result_module.ResultError as error:
        if endpoint is None or not result.ok:
            raise block(error.code, error.detail)
        state.setdefault("result_repair", {})["source_result_blocker"] = error.code
        try:
            parsed = result_repair_module.repair_terminal_result(
                dispatcher,
                directory,
                state,
                entry,
                stage,
                endpoint,
                result,
                nonce,
            )
        except finalization_module.FinalizationError as repair_error:
            raise block(repair_error.code, repair_error.detail)
    state["terminal_result_validated"] = True
    state["semantic_outcome"] = parsed.outcome
    directory.write_json(f"{stage.prefix}.result.json", parsed.as_dict())
    state["terminal_fence_copies"] = parsed.fence_copies
    if stage.name == envelope_module.STAGE_CLOSEOUT:
        state["closeout_fence_copies"] = parsed.fence_copies
    state["provider_outcomes"] = {stage.name: parsed.outcome}
    state["proposed_commit_message"] = (
        None if parsed.commit_message is None else {
            "subject": parsed.commit_message.subject,
            "body": parsed.commit_message.body,
        }
    )
    record_terminal_narrative(state, parsed.body)
    if not parsed.completed:
        raise block(
            f"PROVIDER_OUTCOME_{parsed.outcome.upper()}",
            f"{stage.name} reported {parsed.outcome} despite exit "
            f"{result.exit_code}: {parsed.body.strip()[:2000]}",
        )
    if stage.name not in state["stages_completed"]:
        state["stages_completed"].append(stage.name)
    state["effective_stages"] = {
        name: "performed" for name in dispatcher.lifecycle.stage_names
    }
    state["effective_checkpoints"] = list(state["checkpoints_completed"])
    state["effective_review_count"] = len(state["effective_checkpoints"])
    # Auxiliary formatting is evidence-accounted but is not a semantic stage.
    # Recompute the split after a successful repair instead of making the
    # lifecycle appear to contain a sixth provider stage.
    dispatcher._update_invocation_accounting(state)
    state["finalization_attempted"] = True
    directory.write_json("state.json", state)
    try:
        finalization_module.finalize_repository(
            state,
            entry,
            parsed,
            dispatcher.display,
            resumed=False,
            directory=directory,
        )
    except finalization_module.FinalizationError as error:
        raise block(error.code, error.detail)
    state["outcome"] = "completed"
    state["complete"] = True
    archive_error = dispatcher._finalize(directory, state)
    if archive_error is not None:
        state["_finalized"] = True
        raise DispatchError(str(archive_error), archive_error.code)
    return state


def run_solo(
    dispatcher: Any, request: Any, directory: Any, state: dict[str, Any],
    entry: Any, endpoints: dict[str, Any], checkpoint: Any, done: Any,
) -> dict[str, Any]:
    from .dispatch import DispatchError

    del checkpoint
    stage = dispatcher.lifecycle.stage("solo")
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
        raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
    nonce = result_module.new_nonce()
    begin, end = result_module.markers(nonce)
    rendered = dispatcher.continuation_prompt(
        stage.name, request, directory.run_id, envelope_module.SOLO_ENVELOPE, [],
        include_task_prompt=True,
        contract=terminal_contract(stage.name, begin, end),
        task_prompt=task_prompt,
    )
    try:
        ensure_prompt_fits(stage.name, endpoints[stage.name], rendered)
    except PromptLimitError as error:
        raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
    terminal, _ = dispatcher._stage(
        directory, 1, stage.name, stage.prefix, stage.role,
        endpoints[stage.name], rendered, None,
        read_only=stage.process_read_only,
    )
    stage_delta_module.normalize_index_if_needed(
        dispatcher.cwd, entry.index_identity, state, stage_name=stage.name
    )
    candidate = candidate_module.tree_identity(dispatcher.cwd)
    # Compatibility fallback: normal _stage execution already closed StageBoundary.
    stage_delta_module.capture_stage_boundary(
        dispatcher.cwd,
        state,
        stage=stage.name,
        before_tree=entry.tree,
        after_tree=candidate["tree"],
        entry=entry,
    )
    state["solo_candidate"] = candidate
    state["producer_binding"] = candidate
    state["terminal_candidate"] = candidate
    return complete_terminal(
        dispatcher, directory, state, entry, stage, terminal, nonce,
        endpoint=endpoints[stage.name],
    )


def run_plan_reviewed(
    dispatcher: Any, request: Any, directory: Any, state: dict[str, Any],
    entry: Any, endpoints: dict[str, Any], checkpoint: Any, done: Any,
) -> dict[str, Any]:
    plan_stage, review_stage, terminal_stage = dispatcher.lifecycle.stages
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
    candidate_module.tree_identity(dispatcher.cwd)
    plan_prompt = dispatcher.plan_prompt(request, directory.run_id, task_prompt)
    plan_result, _ = dispatcher._stage(
        directory, 1, plan_stage.name, plan_stage.prefix, plan_stage.role,
        endpoints[plan_stage.name], plan_prompt, None,
        read_only=plan_stage.process_read_only,
    )
    stage_delta_module.normalize_index_if_needed(
        dispatcher.cwd, entry.index_identity, state, stage_name=plan_stage.name
    )
    post_plan_tree = candidate_module.tree_identity(dispatcher.cwd)
    # Compatibility fallback: normal _stage execution already closed StageBoundary.
    stage_delta_module.capture_stage_boundary(
        dispatcher.cwd,
        state,
        stage=plan_stage.name,
        before_tree=entry.tree,
        after_tree=post_plan_tree["tree"],
        entry=entry,
    )
    plan_endpoint = endpoints[plan_stage.name]
    plan_material = materialize_plan(
        directory, plan_result.stdout, plan_endpoint.provider, plan_endpoint.profile
    )
    plan_binding = plan_material.binding
    state["plan_candidate"] = plan_binding
    state["proposal_binding"] = plan_binding
    state["plan_proposal_binding"] = plan_binding
    done(plan_stage.name)

    review_nonce = review_result_module.new_nonce()
    review_prompt = dispatcher.review_prompt(
        review_stage.name, request, directory.run_id, plan_binding,
        plan_material.data,
        task_prompt,
        review_result_module.contract(review_stage.name, review_nonce),
    )
    review_result, _ = dispatcher._stage(
        directory, 2, review_stage.name, review_stage.prefix, review_stage.role,
        endpoints[review_stage.name], review_prompt, plan_binding,
        read_only=review_stage.process_read_only,
    )
    stage_delta_module.normalize_index_if_needed(
        dispatcher.cwd, entry.index_identity, state, stage_name=review_stage.name
    )
    post_review_tree = candidate_module.tree_identity(dispatcher.cwd)
    # Compatibility fallback: normal _stage execution already closed StageBoundary.
    stage_delta_module.capture_stage_boundary(
        dispatcher.cwd,
        state,
        stage=review_stage.name,
        before_tree=post_plan_tree["tree"],
        after_tree=post_review_tree["tree"],
        entry=entry,
    )
    parsed_review = complete_review(
        dispatcher, directory, state, review_stage, review_result, review_nonce
    )
    done(review_stage.name)

    nonce = result_module.new_nonce()
    begin, end = result_module.markers(nonce)
    forwarded_review = dispatcher._sanitize(
        directory, state, "plan_review.stdout.forwarded_to_produce_close",
        parsed_review.body,
    )
    stage_delta_summary = stage_delta_module.format_stage_deltas_summary(state)
    terminal_prompt = dispatcher.continuation_prompt(
        terminal_stage.name, request, directory.run_id,
        envelope_module.PLAN_REVIEWED_PRODUCE_CLOSE_ENVELOPE,
        [
            (
                "Plan proposal binding (dispatcher-owned exact bytes)",
                _binding_text(plan_binding),
            ),
            (
                "Planner proposal — exact bound bytes, to be dispositioned",
                plan_material.data,
            ),
            ("Independent plan review findings", forwarded_review),
            ("Stage deltas and change ledger", stage_delta_summary),
        ],
        include_task_prompt=True,
        contract=terminal_contract(terminal_stage.name, begin, end),
        task_prompt=task_prompt,
    )
    terminal_result, _ = dispatcher._stage(
        directory, 3, terminal_stage.name, terminal_stage.prefix,
        terminal_stage.role, endpoints[terminal_stage.name], terminal_prompt,
        None, read_only=terminal_stage.process_read_only,
    )
    stage_delta_module.normalize_index_if_needed(
        dispatcher.cwd, entry.index_identity, state, stage_name=terminal_stage.name
    )
    candidate = candidate_module.tree_identity(dispatcher.cwd)
    # Compatibility fallback: normal _stage execution already closed StageBoundary.
    stage_delta_module.capture_stage_boundary(
        dispatcher.cwd,
        state,
        stage=terminal_stage.name,
        before_tree=post_review_tree["tree"],
        after_tree=candidate["tree"],
        entry=entry,
    )
    state["produce_close_candidate"] = candidate
    state["producer_binding"] = candidate
    state["work_product_binding"] = candidate
    state["terminal_candidate"] = candidate
    state["final_candidate_reviewed"] = False
    return complete_terminal(
        dispatcher, directory, state, entry, terminal_stage, terminal_result, nonce,
        endpoint=endpoints[terminal_stage.name],
    )


def run_work_reviewed(
    dispatcher: Any, request: Any, directory: Any, state: dict[str, Any],
    entry: Any, endpoints: dict[str, Any], checkpoint: Any, done: Any,
) -> dict[str, Any]:
    from .dispatch import DispatchError

    produce_stage, review_stage, terminal_stage = dispatcher.lifecycle.stages
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
        raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
    produce_prompt = dispatcher.continuation_prompt(
        produce_stage.name, request, directory.run_id,
        envelope_module.WORK_REVIEWED_PRODUCE_ENVELOPE, [],
        include_task_prompt=True, task_prompt=task_prompt,
    )
    produce_result, _ = dispatcher._stage(
        directory, 1, produce_stage.name, produce_stage.prefix,
        produce_stage.role, endpoints[produce_stage.name], produce_prompt,
        None, read_only=produce_stage.process_read_only,
    )
    record_producer_evidence(
        state,
        produce_stage.name,
        produce_result.stdout,
        terminal_stage.name,
        artifact_name=f"{produce_stage.prefix}.stdout.md",
    )
    stage_delta_module.normalize_index_if_needed(
        dispatcher.cwd, entry.index_identity, state, stage_name=produce_stage.name
    )
    produced = candidate_module.tree_identity(dispatcher.cwd)
    # Compatibility fallback: normal _stage execution already closed StageBoundary.
    stage_delta_module.capture_stage_boundary(
        dispatcher.cwd,
        state,
        stage=produce_stage.name,
        before_tree=entry.tree,
        after_tree=produced["tree"],
        entry=entry,
    )
    state["produced_candidate"] = produced
    state["producer_binding"] = produced
    state["work_product_binding"] = produced
    done(produce_stage.name)

    review_nonce = review_result_module.new_nonce()
    review_prompt, prompt_decision = capacity_module.fit_optional_narrative(
        review_stage.name,
        endpoints[review_stage.name],
        lambda material: dispatcher.review_prompt(
            review_stage.name, request, directory.run_id, produced, material,
            task_prompt,
            review_result_module.contract(review_stage.name, review_nonce),
        ),
        produce_result.stdout,
        source_stage=produce_stage.name,
        artifact_basename=f"{produce_stage.prefix}.stdout.md",
        artifact_bytes=produce_result.stdout,
        mandatory_sources=("original_scope", "producer_binding", "work_review_contract"),
    )
    state.setdefault("prompt_capacity_decisions", []).append(prompt_decision)
    review_result, _ = dispatcher._stage(
        directory, 2, review_stage.name, review_stage.prefix, review_stage.role,
        endpoints[review_stage.name], review_prompt, produced,
        read_only=review_stage.process_read_only,
    )
    stage_delta_module.normalize_index_if_needed(
        dispatcher.cwd, entry.index_identity, state, stage_name=review_stage.name
    )
    post_review_tree = candidate_module.tree_identity(dispatcher.cwd)
    # Compatibility fallback: normal _stage execution already closed StageBoundary.
    stage_delta_module.capture_stage_boundary(
        dispatcher.cwd,
        state,
        stage=review_stage.name,
        before_tree=produced["tree"],
        after_tree=post_review_tree["tree"],
        entry=entry,
    )
    parsed_review = complete_review(
        dispatcher, directory, state, review_stage, review_result, review_nonce
    )
    done(review_stage.name)

    current_product = candidate_module.tree_identity(dispatcher.cwd)
    state["revisor_input"] = {
        "original_scope": {
            "kind": "task_prompt",
            "bytes": len(task_prompt.encode("utf-8")),
            "sha256": hashlib.sha256(task_prompt.encode("utf-8")).hexdigest(),
        },
        "producer_binding": produced,
        "current_worktree_product": current_product,
        "producer_narrative": {
            "optional": True,
            "stage": produce_stage.name,
            "artifact_basename": f"{produce_stage.prefix}.stdout.md",
        },
        "work_review": {
            "artifact_name": f"{review_stage.prefix}.result.json",
            "outcome": parsed_review.outcome,
        },
    }
    nonce = result_module.new_nonce()
    begin, end = result_module.markers(nonce)
    forwarded_produce = dispatcher._sanitize(
        directory, state, "produce.stdout.forwarded_to_revise_close",
        produce_result.stdout.decode("utf-8", "replace"),
    )
    forwarded_review = dispatcher._sanitize(
        directory, state, "work_review.stdout.forwarded_to_revise_close",
        parsed_review.body,
    )
    stage_delta_summary = stage_delta_module.format_stage_deltas_summary(state)
    terminal_prompt, prompt_decision = capacity_module.fit_optional_narrative(
        terminal_stage.name,
        endpoints[terminal_stage.name],
        lambda material: dispatcher.continuation_prompt(
            terminal_stage.name, request, directory.run_id,
            envelope_module.WORK_REVIEWED_REVISE_CLOSE_ENVELOPE,
            [
                (
                    "Producer binding (dispatcher-owned exact product)",
                    _binding_text(produced),
                ),
                (
                    "Current worktree product (dispatcher-owned exact binding)",
                    _binding_text(current_product),
                ),
                ("Producer narrative (optional whole artifact)", material),
                ("Independent work review findings", forwarded_review),
                ("Stage deltas and change ledger", stage_delta_summary),
            ],
            include_task_prompt=True,
            contract=terminal_contract(terminal_stage.name, begin, end),
            task_prompt=task_prompt,
        ),
        forwarded_produce,
        source_stage=produce_stage.name,
        artifact_basename=f"{produce_stage.prefix}.stdout.md",
        artifact_bytes=produce_result.stdout,
        mandatory_sources=(
            "original_scope",
            "producer_binding",
            "current_worktree_product",
            "work_review_findings",
            "terminal_result_contract",
        ),
    )
    state.setdefault("prompt_capacity_decisions", []).append(prompt_decision)
    closer_entry_candidate = post_review_tree
    state["closer_entry_candidate"] = closer_entry_candidate
    state["revisor_entry_candidate"] = closer_entry_candidate
    terminal_result, _ = dispatcher._stage(
        directory, 3, terminal_stage.name, terminal_stage.prefix,
        terminal_stage.role, endpoints[terminal_stage.name], terminal_prompt,
        produced, read_only=terminal_stage.process_read_only,
    )
    stage_delta_module.normalize_index_if_needed(
        dispatcher.cwd, entry.index_identity, state, stage_name=terminal_stage.name
    )
    final_candidate = candidate_module.tree_identity(dispatcher.cwd)
    # Compatibility fallback: normal _stage execution already closed StageBoundary.
    stage_delta_module.capture_stage_boundary(
        dispatcher.cwd,
        state,
        stage=terminal_stage.name,
        before_tree=post_review_tree["tree"],
        after_tree=final_candidate["tree"],
        entry=entry,
    )
    state["revise_close_candidate"] = final_candidate
    state["revisor_binding"] = final_candidate
    state["terminal_candidate"] = final_candidate
    closer_mutated = final_candidate["tree"] != post_review_tree["tree"]
    adversary_mutated = post_review_tree["tree"] != produced["tree"]
    state["post_review_revision_delta"] = {
        "changed": closer_mutated,
        "paths": candidate_module.tree_delta(
            dispatcher.cwd, str(post_review_tree["tree"]), str(final_candidate["tree"])
        ),
        "note": (
            "These paths changed during terminal revise_close stage and did not receive "
            "an independent review."
        ),
    }
    state["cumulative_post_review_delta"] = {
        "changed": final_candidate["tree"] != produced["tree"],
        "paths": candidate_module.tree_delta(
            dispatcher.cwd, str(produced["tree"]), str(final_candidate["tree"])
        ),
        "note": (
            "These paths changed after post_work review and did not receive "
            "a second independent review."
        ),
    }
    record_revisor_revision(
        dispatcher,
        state,
        post_review_tree,
        final_candidate,
        terminal_stage,
        review_stage.name,
    )
    state["final_candidate_reviewed"] = (
        (not adversary_mutated)
        and (not closer_mutated)
        and (final_candidate["tree"] == produced["tree"])
    )
    return complete_terminal(
        dispatcher, directory, state, entry, terminal_stage, terminal_result, nonce,
        endpoint=endpoints[terminal_stage.name],
    )
