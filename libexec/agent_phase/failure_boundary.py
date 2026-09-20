"""Mechanical candidate accounting at an incomplete mutating-stage boundary."""

from __future__ import annotations

from typing import Any

from . import candidate as candidate_module
from . import gitstate as gitstate_module
from . import adoption


def _publication_boundary(state: dict[str, Any], entry: Any, raw: str, carried: set[str]) -> tuple[str, list[str]]:
    """Failure capture retains observations without granting deletion authority."""
    from . import path_disposition
    try:
        adoption.guard_boundary(state, entry.root, raw)
    except adoption.AdoptionError as error:
        raise FailureBoundaryError(error.code, error.detail) from error
    base = (state.get("resume") or {}).get("source_entry_tree", entry.tree)
    observed = gitstate_module.phase_delta(entry.root, base, raw)
    state["mechanical_phase_delta"] = [change._asdict() for change in observed]
    state["raw_terminal_candidate"] = {"kind": "git_tree", "tree": raw}
    if state.get("path_ownership") is not None:
        publication, excluded, ambiguous = path_disposition.apply(state, entry, raw, ())
    else:
        publication, excluded = raw, set()
        ambiguous = [change.path for change in observed if change.status == "D"]
    state["unclaimed_deletion_paths"] = ambiguous[:path_disposition.MAX_ENTRIES]
    try:
        adoption.guard_owned(state, carried - excluded - set(ambiguous))
    except adoption.AdoptionError as error:
        raise FailureBoundaryError(error.code, error.detail) from error
    return publication, sorted(carried - excluded - set(ambiguous))


class FailureBoundaryError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def record_manager_attention(
    state: dict[str, Any],
    *,
    reason: str,
    detail: str | None = None,
    paths: list[str] | None = None,
    candidate_tree: str | None = None,
) -> None:
    """Add a manager attention reason monotonically."""
    state["manager_disposition_required"] = True
    reasons = state.setdefault("manager_attention_reasons", [])
    if not isinstance(reasons, list):
        reasons = []
        state["manager_attention_reasons"] = reasons
    if reason not in reasons:
        reasons.append(reason)

    records = state.setdefault("manager_attention_records", [])
    if not isinstance(records, list):
        records = []
        state["manager_attention_records"] = records
    if not any(isinstance(r, dict) and r.get("reason") == reason for r in records):
        entry_item = {"reason": reason, "detail": detail or reason}
        if paths is not None:
            entry_item["paths"] = list(paths)
        if candidate_tree is not None:
            entry_item["candidate_tree"] = candidate_tree
        records.append(entry_item)

    if not isinstance(state.get("manager_disposition"), dict):
        state["manager_disposition"] = {
            "required": True,
            "reason": reason,
            "paths": list(paths or []),
            "candidate_tree": candidate_tree,
            "automatic_publication": "not_attempted",
            "reasons": reasons,
            "records": records,
        }
    else:
        disp = state["manager_disposition"]
        disp["required"] = True
        disp["reasons"] = reasons
        disp["records"] = records
        if not disp.get("reason"):
            disp["reason"] = reason
        if paths and not disp.get("paths"):
            disp["paths"] = list(paths)


def record_mutating_failure(
    state: dict[str, Any],
    entry: Any,
    stage_name: str,
    after_tree: dict[str, Any] | None = None,
    after_index: dict[str, Any] | None = None,
) -> None:
    """Record mutating failure boundary from StageBoundary close."""
    if entry is None:
        return
    try:
        candidate_tree = str((after_tree or {}).get("tree") or candidate_module.tree_identity(entry.root)["tree"])
        boundary_delta = gitstate_module.phase_delta(entry.root, entry.tree, candidate_tree)
        carried = set(state.get("phase_owned_paths", [])) | adoption.paths(state)
        manifest = state.get("candidate_manifest")
        if isinstance(manifest, dict):
            gitstate_module.validate_candidate_manifest(manifest)
            carried.update(manifest["paths"])
        overlap = ({change.path for change in boundary_delta} & set(entry.dirty)) - adoption.paths(state)
        if state.get("resumed"):
            overlap -= carried
        if overlap:
            overlap_paths = sorted(overlap)
            state["entry_dirt_overlap"] = overlap_paths
            record_manager_attention(
                state,
                reason="entry_dirt_overlap",
                detail=f"phase and operator bytes overlap: {overlap_paths}",
                paths=overlap_paths,
                candidate_tree=candidate_tree,
            )
            carried.update(c.path for c in boundary_delta if c.path not in overlap)
        else:
            carried.update(c.path for c in boundary_delta)
        publication_tree, owned = _publication_boundary(state, entry, candidate_tree, carried)
        if state.get("unclaimed_deletion_paths"):
            record_manager_attention(state, reason="path_ownership_required",
                                     paths=state["unclaimed_deletion_paths"], candidate_tree=candidate_tree)
        carried = set(owned)
        head_delta = gitstate_module.phase_delta(entry.root, entry.head, publication_tree)
        phase_delta = [c for c in head_delta if c.path in carried]
        owned = sorted(carried)
        base_tree = entry.tree
        resume = state.get("resume")
        if isinstance(resume, dict) and isinstance(resume.get("source_entry_tree"), str):
            base_tree = resume["source_entry_tree"]
        if state.get("path_ownership"):
            base_tree = state["path_ownership"]["entry_tree"]
        closed_manifest = gitstate_module.candidate_manifest(entry.root, base_tree, publication_tree, paths=owned)
        current_head = gitstate_module.current_head(entry.root)
        uncommitted = [c for c in gitstate_module.phase_delta(entry.root, current_head, candidate_tree) if c.path in carried]
        state["phase_delta"] = [{"status": c.status, "path": c.path} for c in phase_delta]
        state["phase_owned_paths"] = owned
        state["candidate_manifest"] = closed_manifest
        state["candidate_manifest_derivation"] = "mechanical_failure_boundary"
        state["failure_candidate"] = {
            "stage": stage_name,
            "head": current_head,
            "tree": candidate_tree,
            "paths": [c.path for c in phase_delta],
            "candidate_paths": sorted(c.path for c in boundary_delta),
        }
        if uncommitted:
            record_manager_attention(
                state,
                reason="uncommitted_phase_paths",
                detail=f"uncommitted phase-owned paths remain: {[c.path for c in uncommitted]}",
                paths=[c.path for c in uncommitted],
                candidate_tree=candidate_tree,
            )
        state["manager_disposition_required"] = bool(
            state.get("manager_disposition_required") or uncommitted
        )
    except Exception as error:
        state["failure_candidate_capture"] = {
            "status": "failed",
            "code": getattr(error, "code", type(error).__name__),
            "detail": str(error),
        }


def _failed_stage(state: dict[str, Any], lifecycle: Any) -> Any | None:
    if lifecycle is None:
        return None
    for name in reversed(state.get("stages_invoked", [])):
        if name not in lifecycle.stage_names:
            continue
        return lifecycle.stage(name)
    return None


def capture_mutating_boundary(
    dispatcher: Any,
    state: dict[str, Any],
    entry: Any,
    lifecycle: Any,
    stage_name: str | None = None,
    *,
    record_failure: bool = True,
) -> bool:
    """Close candidate truth for one incomplete semantic stage."""
    if state.get("review_binding_invalidations"):
        # Observed concurrent drift is not producer ownership or adoption authority.
        return False
    if state.get("worker_cleanup_pending"):
        raise FailureBoundaryError(
            "WORKER_CLEANUP_FAILED",
            "final candidate capture withheld while owned worker cleanup is incomplete",
        )
    stage = (
        lifecycle.stage(stage_name)
        if (lifecycle is not None and stage_name in lifecycle.stage_names)
        else _failed_stage(state, lifecycle)
    )
    if stage is None:
        st_name = stage_name or (state.get("stages_invoked") or ["work"])[-1]
    else:
        st_name = stage.name
    try:
        candidate = candidate_module.tree_identity(entry.root)
        candidate_tree = str(candidate["tree"])
        boundary_delta = gitstate_module.phase_delta(
            entry.root, entry.tree, candidate_tree
        )
        carried = set(state.get("phase_owned_paths", [])) | adoption.paths(state)
        manifest = state.get("candidate_manifest")
        if isinstance(manifest, dict):
            gitstate_module.validate_candidate_manifest(manifest)
            carried.update(manifest["paths"])
        overlap = ({change.path for change in boundary_delta} & set(entry.dirty)) - adoption.paths(state)
        if state.get("resumed"):
            overlap -= carried
        if overlap:
            overlap_paths = sorted(overlap)
            state["entry_dirt_overlap"] = overlap_paths
            record_manager_attention(
                state,
                reason="entry_dirt_overlap",
                detail=f"phase and operator bytes overlap: {overlap_paths}",
                paths=overlap_paths,
                candidate_tree=candidate_tree,
            )
            carried.update(
                change.path
                for change in boundary_delta
                if change.path not in overlap
            )
        else:
            carried.update(change.path for change in boundary_delta)
        publication_tree, owned = _publication_boundary(state, entry, candidate_tree, carried)
        carried = set(owned)
        head_delta = gitstate_module.phase_delta(
            entry.root, entry.head, publication_tree
        )
        phase_delta = [change for change in head_delta if change.path in carried]
        owned = sorted(carried)
        base_tree = entry.tree
        resume = state.get("resume")
        if isinstance(resume, dict) and isinstance(
            resume.get("source_entry_tree"), str
        ):
            base_tree = resume["source_entry_tree"]
        if state.get("path_ownership"):
            base_tree = state["path_ownership"]["entry_tree"]
        closed_manifest = gitstate_module.candidate_manifest(
            entry.root, base_tree, publication_tree, paths=owned
        )
        current_head = gitstate_module.current_head(entry.root)
        uncommitted = [
            change
            for change in gitstate_module.phase_delta(
                entry.root, current_head, candidate_tree
            )
            if change.path in carried
        ]
    except FailureBoundaryError:
        raise
    except (candidate_module.CandidateError, gitstate_module.GitStateError) as error:
        raise FailureBoundaryError(
            getattr(error, "code", type(error).__name__), str(error)
        ) from error

    active_stage = getattr(dispatcher, "_active_stage", None)
    transport_stage = (
        active_stage
        if (lifecycle is not None and active_stage in lifecycle.stage_names)
        else st_name
    )
    transport = state.get("stage_transport_outcomes", {}).get(transport_stage)
    state["phase_delta"] = [
        {"status": change.status, "path": change.path}
        for change in phase_delta
    ]
    state["phase_owned_paths"] = owned
    state["candidate_manifest"] = closed_manifest
    state["candidate_manifest_derivation"] = "mechanical_failure_boundary"
    if record_failure:
        if state.get("unclaimed_deletion_paths"):
            record_manager_attention(state, reason="path_ownership_required",
                                     paths=state["unclaimed_deletion_paths"], candidate_tree=candidate_tree)
        state["failure_candidate"] = {
            "stage": st_name,
            "head": current_head,
            "tree": candidate_tree,
            "paths": [change.path for change in phase_delta],
            # Keep the complete candidate path set available even when an
            # overlap is excluded from phase ownership for safe resume.
            "candidate_paths": sorted(change.path for change in boundary_delta),
        }
        if uncommitted:
            record_manager_attention(
                state,
                reason="uncommitted_phase_paths",
                detail=f"uncommitted phase-owned paths remain: {[c.path for c in uncommitted]}",
                paths=[c.path for c in uncommitted],
                candidate_tree=candidate_tree,
            )
        state["manager_disposition_required"] = bool(
            state.get("manager_disposition_required") or uncommitted
        )
        state["failure_stage_transport"] = (
            transport
            if isinstance(transport, dict)
            else {
                "stage": st_name,
                "status": "semantic_failure_after_transport",
            }
        )
    return True
