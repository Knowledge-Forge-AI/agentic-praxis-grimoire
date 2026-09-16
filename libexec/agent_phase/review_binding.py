"""Attribution-free immutability fence for independent review checkpoints."""

from __future__ import annotations

from . import candidate, gitstate, lifecycle


def is_review(state, stage):
    spec = lifecycle.get_lifecycle(state.get("lifecycle", "standard"))
    return stage in spec.stage_names and spec.stage(stage).checkpoint is not None


def bind(root, state, stage, subject):
    """Keep immutable plan/subject identity separate from repository identity."""
    record = {
        "subject": subject,
        "repository": candidate.tree_identity(root),
        "index": gitstate.index_identity(root),
    }
    state.setdefault("immutable_review_bindings", {})[stage] = record
    # Resume validates scoped candidate ownership and may allow unrelated HEAD
    # or dirt changes. Its review prompt carries that separate current boundary.
    if not state.get("resumed") and subject and subject.get("kind") == "git_tree":
        record["repository"] = {key: subject[key] for key in ("kind", "head", "tree")}
        verify(root, state, stage)
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


def verify(root, state, stage, after=None, observed_index=None, transport=None):
    """Invalidate before parsing or accepting review bytes; never restore product."""
    from .dispatch import DispatchError
    from .failure_boundary import record_manager_attention

    binding = state.get("immutable_review_bindings", {}).get(stage)
    if binding is None:
        return
    after = after if after is not None else _observe_candidate(root)
    observed_index = observed_index if observed_index is not None else gitstate.index_identity(root)
    before = binding["repository"]
    if after == before and observed_index == binding["index"]:
        return
    index_changed = observed_index != binding["index"]
    code = "READ_ONLY_STAGE_MUTATED_INDEX" if index_changed else "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    detail = f"mutation observed during read-only stage {stage}; review binding invalidated"
    evidence = {
        "stage": stage, "candidate_binding": binding["subject"],
        "subject_binding": binding["subject"],
        "expected_head": before.get("head"), "observed_head": after.get("head"),
        "expected_tree": before["tree"], "observed_tree": after.get("tree"),
        "paths": [], "index_paths": [], "paths_complete": False,
        "candidate_observation_unavailable": bool(after.get("observation_unavailable") or not after.get("tree")),
        "observation_limitations": [],
        "expected_index": binding["index"], "observed_index": observed_index,
        "transport": transport or state.get("stage_transport_outcomes", {}).get(stage),
        "code": code, "detail": detail,
    }
    state[f"{stage}_mutation"] = evidence
    state.setdefault("review_binding_invalidations", {})[stage] = evidence
    state["blocking_reason"] = {"code": code, "detail": detail}
    state["outcome"] = "blocked"
    _enrich_evidence(root, state, evidence)
    record_manager_attention(
        state, reason="review_binding_invalidated", detail=detail + "; repository/candidate resolution and fresh review required",
        paths=sorted(set(evidence["paths"] + evidence["index_paths"])), candidate_tree=after.get("tree"),
    )
    raise DispatchError(detail, code)
