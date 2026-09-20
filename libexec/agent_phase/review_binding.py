"""Attribution-free immutability fence for independent review checkpoints."""

from __future__ import annotations

from collections.abc import Mapping

from . import candidate, gitstate, lifecycle


def is_review(state, stage):
    spec = lifecycle.get_lifecycle(state.get("lifecycle", "standard"))
    return stage in spec.stage_names and spec.stage(stage).checkpoint is not None


def bind(root, state, stage, subject, *, attempt_id=None, binding_id=None, attempt_number=None):
    """Keep immutable plan/subject identity separate from repository identity."""
    spec = None
    try:
        spec = lifecycle.get_lifecycle(state.get("lifecycle", "standard")).stage(stage)
    except Exception:
        pass
    role = None
    subject_kind = None
    if spec:
        if spec.checkpoint in ("pre_final", "post_work"):
            role = "work_reviewer"
            subject_kind = "work"
        elif spec.checkpoint == "post_planning":
            role = "plan_reviewer"
            subject_kind = "plan"
        else:
            role = spec.role
            subject_kind = subject.get("kind") if isinstance(subject, Mapping) else None

    if attempt_id is None:
        run_id = state.get("run_id") or state.get("active_run_id") or state.get("route_selecting_run_id") or "run"
        att_num = attempt_number or state.get("attempt_number") or 1
        attempt_id = f"att-{run_id}-{stage}-{att_num}"
    if binding_id is None:
        binding_id = stage
    if attempt_number is None:
        attempt_number = 1

    record = {
        "subject": subject,
        "repository": candidate.tree_identity(root),
        "index": gitstate.index_identity(root),
        "role": role,
        "subject_kind": subject_kind,
        "attempt_id": attempt_id,
        "binding_id": binding_id,
        "attempt_number": attempt_number,
    }
    state.setdefault("immutable_review_bindings", {})[stage] = record
    # Resume validates scoped candidate ownership and may allow unrelated HEAD
    # or dirt changes. Its review prompt carries that separate current boundary.
    if not state.get("resumed") and subject and subject.get("kind") == "git_tree":
        record["repository"] = {key: subject[key] for key in ("kind", "head", "tree")}
        verify(root, state, stage, attempt_id=attempt_id, binding_id=binding_id, attempt_number=attempt_number)
    return record


def require_resolved_resume(root, state, current_tree):
    """Do not reclassify observed review drift as unrelated operator dirt."""
    from .resume_validation import ResumeError

    for record in state.get("review_binding_invalidations", {}).values():
        if not record.get("paths_complete", True) and current_tree != record["expected_tree"]:
            raise ResumeError(
                "RESUME_CANDIDATE_CONFLICT",
                "invalidated review has incomplete path evidence; restore the full "
                "pre-review repository tree before exact resume",
            )
        protected = set(record["paths"]) | set(record["index_paths"])
        try:
            changed = set(candidate.tree_delta(root, record["expected_tree"], current_tree))
        except candidate.CandidateError as error:
            raise ResumeError("RESUME_ARTIFACT_MISMATCH", str(error)) from error
        unresolved = sorted(protected & changed)
        if unresolved:
            raise ResumeError(
                "RESUME_CANDIDATE_CONFLICT",
                "invalidated review paths require manager resolution before exact resume: "
                + ", ".join(unresolved),
            )


def _observe_candidate(root):
    try:
        return candidate.tree_identity(root)
    except candidate.CandidateError:
        return {"tree": "", "observation_unavailable": True}


def _enrich_evidence(root, state, evidence):
    """Retain the invalidation even if optional path diagnostics are unavailable."""
    limitations = evidence["observation_limitations"]
    if evidence["candidate_observation_unavailable"]:
        limitations.append({"kind": "candidate_observation_unavailable"})
    else:
        try:
            evidence["paths"] = candidate.tree_delta(
                root, evidence["expected_tree"], evidence["observed_tree"]
            )
            evidence["paths_complete"] = True
        except candidate.CandidateError:
            limitations.append({"kind": "product_paths_unavailable"})
    if evidence["expected_index"] != evidence["observed_index"]:
        from .stage_delta import inspect_index_changes
        observation = {}
        evidence["index_paths"] = sorted({
            item["path"] for item in inspect_index_changes(root, observation=observation)
        })
        if observation.get("observation_limitations"):
            limitations.extend(observation["observation_limitations"])
            evidence["paths_complete"] = False
    normalizations = state.get("index_normalizations", [])
    latest = next((item for item in reversed(normalizations)
                   if item["stage"] == evidence["stage"]), {})
    evidence["index_normalization_reason"] = latest.get("reason")


def verify(
    root,
    state,
    stage,
    after=None,
    observed_index=None,
    transport=None,
    policy=None,
    attempt_id=None,
    binding_id=None,
    attempt_number=None,
):
    """Observe review drift and evaluate review mutation policy."""
    from . import review_drift

    binding = state.get("immutable_review_bindings", {}).get(stage)
    if binding is None:
        return None

    if policy is None:
        policy = state.get("review_mutation_policy", "block")

    eff_attempt_id = attempt_id if attempt_id is not None else binding.get("attempt_id")
    if eff_attempt_id is None:
        run_id = state.get("run_id") or state.get("active_run_id") or state.get("route_selecting_run_id") or "run"
        eff_attempt_id = f"att-{run_id}-{stage}-1"
    eff_binding_id = binding_id if binding_id is not None else (binding.get("binding_id") or stage)
    eff_attempt_num = attempt_number if attempt_number is not None else (binding.get("attempt_number") or 1)

    obs = review_drift.observe_review_drift(
        root,
        stage=stage,
        before=binding,
        after=after,
        expected_index=binding.get("index"),
        observed_index=observed_index,
        transport=transport,
        policy=policy,
        state=state,
        role=binding.get("role"),
        subject_kind=binding.get("subject_kind"),
        attempt_id=eff_attempt_id,
        binding_id=eff_binding_id,
        attempt_number=eff_attempt_num,
    )

    evaluated = review_drift.apply_review_mutation_policy(
        obs,
        policy=policy,
        state=state,
        raise_on_block=False,
    )

    if not obs.subject_drift_observed and evaluated.action_taken != "blocked":
        return evaluated

    evidence = obs.as_dict()
    evidence["candidate_binding"] = binding.get("subject")
    evidence["subject_binding"] = binding.get("subject")
    evidence["paths"] = obs.worktree_paths
    evidence["code"] = obs.diagnostic_code
    if "transport" not in evidence or evidence["transport"] is None:
        evidence["transport"] = transport or (state.get("stage_transport_outcomes", {}).get(stage) if state else None)

    normalizations = state.get("index_normalizations", [])
    latest = next((item for item in reversed(normalizations)
                   if item.get("stage") == stage), {})
    if latest.get("reason"):
        evidence["index_normalization_reason"] = latest.get("reason")

    state[f"{stage}_mutation"] = evidence

    if evaluated.action_taken == "blocked":
        state.setdefault("review_binding_invalidations", {})[stage] = evidence
        from .dispatch import DispatchError
        from .failure_boundary import record_manager_attention
        detail = evaluated.detail or f"mutation observed during read-only stage {stage}; review binding invalidated"
        state["blocking_reason"] = {"code": evaluated.diagnostic_code, "detail": detail}
        state["outcome"] = "blocked"
        _enrich_evidence(root, state, evidence)
        record_manager_attention(
            state,
            reason="review_binding_invalidated",
            detail=detail + "; repository/candidate resolution and fresh review required",
            paths=sorted(set(evidence["paths"] + evidence["index_paths"])),
            candidate_tree=evidence.get("observed_tree"),
        )
        raise DispatchError(detail, evaluated.diagnostic_code)

    return evaluated

