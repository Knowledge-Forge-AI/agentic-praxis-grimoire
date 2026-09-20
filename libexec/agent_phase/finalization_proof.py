"""Exact-run recovery proofs; no provider, publication or worktree writes."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

from . import archive_verify, gitstate, outcomes, path_disposition, resume
from .lifecycle import get_lifecycle
from .request import load_request
from .resume_validation import ResumeError, load_core


class RecoveryError(RuntimeError):
    def __init__(self, code: str, detail: str, repair_class: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.repair_class = code, detail, repair_class


def refuse(code: str, detail: str, category: str | None = None) -> None:
    raise RecoveryError(code, detail, category or outcomes.classify_failure(code))


def overlaps(path: str, other: str) -> bool:
    return path == other or path.startswith(other + "/") or other.startswith(path + "/")


@dataclass
class Proof:
    source: Path
    state: dict[str, Any]
    entry: gitstate.EntryState
    current: gitstate.EntryState
    terminal: Any
    manifest: dict[str, Any]
    source_manifest: dict[str, Any]
    action: str
    extras: list[str]
    ownership_resolutions: list[dict[str, Any]] = field(default_factory=list)
    ownership_resolution_paths: list[Path] = field(default_factory=list)


def require_standard_environment() -> None:
    """Reject redirected repository/index/object authority before any Git read."""
    keys = ("GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_NAMESPACE",
            "GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE")
    if any(key in os.environ for key in keys):
        refuse("RECOVERY_ENVIRONMENT_INVALID", "redirected Git authority is not supported")


def _repository_guard(root: Path) -> None:
    require_standard_environment()
    fsmonitor = gitstate._run(root, ["config", "--get", "core.fsmonitor"])
    if fsmonitor.returncode not in (0, 1):
        refuse("RECOVERY_HOOK_POLICY", "Git monitor configuration cannot be read")
    if fsmonitor.returncode == 0 and fsmonitor.stdout.strip().lower() not in (b"false", b"0", b"no", b"off"):
        refuse("RECOVERY_HOOK_POLICY", "recovery cannot execute a configured filesystem monitor")
    # Replacement/graft/shallow graphs cannot establish immutable ancestry.
    if any(os.environ.get(key) for key in ("GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE")):
        refuse("RECOVERY_GRAPH_INVALID", "alternate graph interpretation is not supported")
    if gitstate._text(root, ["for-each-ref", "--format=%(refname)", "refs/replace/"],
                      "RECOVERY_GRAPH_INVALID"):
        refuse("RECOVERY_GRAPH_INVALID", "replacement objects are not supported")
    for name in ("shallow", "info/grafts"):
        path = Path(gitstate._text(root, ["rev-parse", "--git-path", name],
                                  "RECOVERY_GRAPH_INVALID"))
        if not path.is_absolute():
            path = root / path
        if path.exists():
            refuse("RECOVERY_GRAPH_INVALID", "incomplete or rewritten ancestry is not supported")
    lock = Path(gitstate._text(root, ["rev-parse", "--git-path", "index.lock"], "RECOVERY_INDEX_LOCKED"))
    if not lock.is_absolute():
        lock = root / lock
    if lock.exists():
        refuse("RECOVERY_INDEX_LOCKED", "real index has an active lock")


def _ownership(
    state: dict[str, Any],
    entry: gitstate.EntryState,
    terminal: Any,
    retained_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from . import adoption
    if state.get("adoption"):
        adoption.validate_retained(entry.root, state["adoption"])
    raw = (state.get("raw_terminal_candidate") or state.get("terminal_candidate") or {}).get("tree")
    if not isinstance(raw, str):
        refuse("CANDIDATE_MANIFEST_INVALID", "sealed terminal tree is required")
    # ``retained_state`` is the immutable archived state.  ``state`` may have
    # exact manager resolution events applied to it, which can legitimately
    # expand the publication manifest by the named challenge paths.
    original = deepcopy(retained_state if retained_state is not None else state)
    from . import ownership_challenge
    try:
        ownership_challenge.validate(entry.root, state)
    except (TypeError, KeyError, ValueError, RuntimeError) as error:
        refuse("OWNERSHIP_CHALLENGE_INVALID", str(error), "requires_manager_ownership")
    publication, excluded, ambiguous = path_disposition.apply(
        state, entry, raw, terminal.path_dispositions
    )
    grants = ownership_challenge.decisions(state)
    manager_owned = {
        path for path, decision in grants.items() if decision == "phase_owned"
    }
    manager_excluded = {
        path for path, decision in grants.items() if decision == "exclude_unrelated"
    }
    remaining_overlap = set(state.get("entry_dirt_overlap") or []) - manager_owned
    if ambiguous or remaining_overlap:
        refuse("MANAGER_DISPOSITION_REQUIRED", "tracked deletion or entry ownership overlap is unresolved",
               "requires_manager_ownership")
    base = state["path_ownership"]["entry_tree"]
    observed = {c.path for c in gitstate.phase_delta(entry.root, base, raw)}
    owned = (observed | adoption.paths(state) | {item["path"] for item in state["path_dispositions"]
                         if item["disposition"] == "phase_owned"}) - excluded
    if any(overlaps(p, dirty) for p in owned for dirty in entry.dirty):
        # Exact resumed provenance may already include phase dirt at entry.
        inherited = (set((original.get("resume") or {}).get("candidate_manifest", {}).get("paths", {}))
                     | adoption.paths(state) | manager_owned)
        if any(overlaps(p, dirty) and p not in inherited for p in owned for dirty in entry.dirty):
            refuse("ENTRY_DIRT_OVERLAP", "phase ownership overlaps entry dirt", "requires_manager_ownership")
    manifest = gitstate.candidate_manifest(entry.root, base, publication, paths=sorted(owned))
    recorded = original.get("candidate_manifest")
    recorded_paths = set(recorded.get("paths", {})) if isinstance(recorded, dict) else set()
    expanded = set(manifest.get("paths", {})) - recorded_paths
    if expanded - manager_owned:
        refuse("CANDIDATE_MANIFEST_INVALID", "candidate ownership expanded outside manager resolutions")
    if (recorded_paths & set(manifest.get("paths", {}))
            and isinstance(recorded, dict)
            and any(recorded["paths"][path] != manifest["paths"][path]
                    for path in recorded_paths & set(manifest.get("paths", {})))):
        refuse("CANDIDATE_MANIFEST_INVALID", "retained candidate objects changed")
    if original.get("path_ownership") is not None:
        same_paths = (
            isinstance(recorded, dict)
            and recorded.get("paths") == manifest.get("paths")
        )
        allowed_exclusion_tree_change = bool(manager_excluded) and same_paths
        if (not expanded
                and (original.get("phase_owned_paths") != sorted(owned)
                     or (recorded != manifest and not allowed_exclusion_tree_change))):
            refuse("CANDIDATE_MANIFEST_INVALID", "sealed ownership set differs from retained candidate")
        # Re-run the normal inherited-manifest proof over the resolved copy.
        # Its exact recorded manifest is replaced only by the newly computed
        # candidate, so the resolver cannot smuggle in an unrelated path.
        inherited = deepcopy(state)
        inherited["candidate_manifest"] = manifest
        inherited["phase_owned_paths"] = sorted(owned)
        try:
            resume._inherited_candidate_manifest(
                Path(), inherited, get_lifecycle(state["lifecycle"]), "finalize", entry
            )
        except ResumeError as error:
            refuse(error.code, error.detail, "requires_manager_ownership")
    elif (original.get("blocking_reason") or {}).get("code") == "PATH_DISPOSITION_INVALID":
        if (not state.get("path_disposition_noops") or publication != raw
                or (not expanded and (recorded != manifest
                    or original.get("phase_owned_paths") != sorted(owned)))):
            refuse("PATH_DISPOSITION_INVALID", "no closed metadata no-op repair proof", "requires_manager_ownership")
    else:
        refuse("CANDIDATE_MANIFEST_INVALID", "recovery requires sealed ownership evidence")
    state["candidate_manifest"] = manifest
    state["phase_owned_paths"] = sorted(owned)
    state["final_tree"] = publication
    return manifest


def require_no_execution_hooks(root: Path) -> None:
    """Refuse executable hooks instead of bypassing repository hook policy."""
    configured = gitstate._run(root, ["config", "--path", "--get", "core.hooksPath"])
    if configured.returncode not in (0, 1):
        refuse("RECOVERY_HOOK_POLICY", "Git hook configuration cannot be read")
    hook_path = configured.stdout.decode().strip() if configured.returncode == 0 else gitstate._text(
        root, ["rev-parse", "--git-path", "hooks"], "RECOVERY_HOOK_POLICY")
    hooks = Path(hook_path)
    if not hooks.is_absolute():
        hooks = root / hooks
    for name in ("pre-commit", "prepare-commit-msg", "commit-msg", "post-commit", "pre-push",
                 "reference-transaction", "post-index-change", "post-rewrite", "push-to-checkout"):
        if os.access(hooks / name, os.X_OK) and (hooks / name).is_file():
            refuse("RECOVERY_HOOK_POLICY", "provider-free recovery cannot execute repository hooks")


def _materialized(root: Path, entry: gitstate.EntryState, current: gitstate.EntryState,
                  state: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    if not gitstate.is_ancestor(root, entry.head, current.head):
        refuse("RECOVERY_ANCESTRY_MISMATCH", "source entry is not an ancestor of current HEAD")
    if gitstate.candidate_manifest_conflicts(root, current.head, manifest):
        refuse("RECOVERY_CANDIDATE_CONFLICT", "current HEAD differs on candidate-owned objects")
    excluded = state["excluded_paths"]
    ownership = state["path_ownership"]
    exclusions = gitstate.candidate_manifest(root, ownership["entry_tree"],
                                            ownership["entry_tree"], paths=excluded)
    if gitstate.candidate_manifest_conflicts(root, current.head, exclusions):
        refuse("RECOVERY_EXCLUSION_CONFLICT", "current HEAD contradicts retained excluded objects")
    extras = sorted(c.path for c in gitstate.phase_delta(root, entry.head, current.head)
                    if c.path not in manifest["paths"])
    if any(overlaps(p, extra) for p in manifest["paths"] for extra in extras):
        refuse("RECOVERY_CANDIDATE_CONFLICT", "additional objects overlap owned paths")
    return extras


def inspect(
    source: Path,
    root: Path,
    ownership_resolutions: list[Path] | tuple[Path, ...] | None = None,
    ownership_resolution: Path | None = None,
) -> Proof:
    if ownership_resolution is not None:
        if ownership_resolutions:
            refuse("OWNERSHIP_RESOLUTION_INVALID", "singular and repeated resolution inputs cannot be combined",
                   "requires_manager_ownership")
        ownership_resolutions = [ownership_resolution]
    _repository_guard(root)
    source = source.resolve(strict=True)
    request = load_request(source / "request.json")
    from .resume_validation import load_json
    identity = load_json(source, "state.json")
    source, original, result, resolved, entry, completed = load_core(
        source, identity.get("phase_id"), request, root, identity.get("project")
    )
    archive_verify.verify_source_archive(source)
    source_manifest = archive_verify.source_manifest(source)
    lifecycle = get_lifecycle(original["lifecycle"])
    terminal = resume._terminal_result(source, original, completed, lifecycle)
    if terminal is None or not terminal.completed or completed != lifecycle.stage_names:
        refuse("PROVIDER_OUTCOME_INVALID", "source semantic lifecycle is not completed",
               "requires_semantic_revision")
    _repository_guard(root)
    current = gitstate.capture_entry(root)
    if current.branch == "HEAD" or current.branch != entry.branch:
        refuse("RESUME_BRANCH_MISMATCH", "current branch differs from the source branch")
    if current.head == entry.head and current.index_identity != entry.index_identity:
        refuse("FINALIZATION_INDEX_MUTATED", "index differs from source entry")
    if current.index_identity != gitstate.index_identity_for_tree(root, current.head):
        refuse("FINALIZATION_INDEX_MUTATED", "real index is not exactly current HEAD")
    state = deepcopy(original)
    retained_state = deepcopy(original)
    # Manager receipts are applied only to this recovery copy.  The archived
    # source state and its original terminal bytes remain immutable evidence.
    resolutions: list[dict[str, Any]] = []
    state["_ownership_recovery"] = True
    if ownership_resolutions:
        from . import ownership_cli

        try:
            resolutions = ownership_cli.apply_receipts(
                root, source, state, source_manifest, ownership_resolutions
            )
        except ownership_cli.OwnershipResolutionError as error:
            refuse(error.code, error.detail, "requires_manager_ownership")
    manifest = _ownership(state, entry, terminal, retained_state=retained_state)
    blocker = (original.get("blocking_reason") or {}).get("code")
    allowed_attention = {"uncommitted_phase_paths"}
    if blocker == "PATH_DISPOSITION_INVALID" and state.get("path_disposition_noops"):
        allowed_attention.add("path_ownership_invalid")
    from . import ownership_challenge
    resolved_paths = set(ownership_challenge.decisions(state))
    challenge_states = ownership_challenge.statuses(state)
    retained_challenge_states = ownership_challenge.statuses(retained_state)
    retained_open_ids = {
        challenge_id for challenge_id, status in retained_challenge_states.items()
        if status == "open"
    }
    resolved_retained_open = bool(retained_open_ids) and all(
        challenge_states.get(challenge_id)
        in ("resolved_by_provider", "resolved_by_manager")
        for challenge_id in retained_open_ids
    )
    resolved_reasons = {
        record.get("reason")
        for record in (state.get("ownership_challenges") or {}).get("records", [])
        if (record.get("path") in resolved_paths
                and challenge_states.get(record.get("challenge_id"))
                in ("resolved_by_provider", "resolved_by_manager"))
    }
    if "path_ownership_required" in original.get("manager_attention_reasons", []) \
            and (("unclaimed_tracked_deletion" in resolved_reasons)
                 or resolved_retained_open):
        allowed_attention.add("path_ownership_required")
    if "entry_dirt_overlap" in original.get("manager_attention_reasons", []) \
            and "entry_dirt_overlap" in resolved_reasons \
            and not (set(original.get("entry_dirt_overlap") or [])
                     - {path for path, decision in ownership_challenge.decisions(state).items()
                        if decision == "phase_owned"}):
        allowed_attention.add("entry_dirt_overlap")
    if set(original.get("manager_attention_reasons", [])) - allowed_attention:
        refuse("MANAGER_DISPOSITION_REQUIRED", "source retains unresolved manager attention",
               "requires_manager_ownership")
    resolved_blocker = blocker == "OWNERSHIP_CHALLENGE_OPEN" and not ownership_challenge.open_records(state)
    if (blocker and blocker not in ("PATH_DISPOSITION_INVALID", "OWNERSHIP_CHALLENGE_OPEN")
            and not original.get("finalization_attempted")):
        refuse(blocker, "source blocker predates Git finalization")
    if current.head != entry.head:
        extras = _materialized(root, entry, current, state, manifest)
        action = "verify_existing" if (original.get("commit") or {}).get("sha") == current.head else "recognize_materialization"
    else:
        if blocker not in (None, "PATH_DISPOSITION_INVALID") and not resolved_blocker:
            refuse(blocker, "source failure is outside the mechanical repair allowlist")
        if gitstate.candidate_manifest_conflicts(root, current.tree, manifest):
            refuse("RECOVERY_CANDIDATE_CONFLICT", "worktree differs on sealed candidate paths")
        excluded_raw = gitstate.candidate_manifest(root, entry.tree,
            state["path_ownership"]["raw_tree"], paths=state["excluded_paths"])
        if gitstate.candidate_manifest_conflicts(root, current.tree, excluded_raw):
            refuse("RECOVERY_EXCLUSION_CONFLICT", "retained excluded observations changed")
        action, extras = "finalize", []
        if not manifest["paths"] and original.get("repository_finalized"):
            action = "verify_existing"
    return Proof(
        source, state, entry, current, terminal, manifest, source_manifest,
        action, extras, resolutions,
        [Path(path) for path in (ownership_resolutions or ())],
    )


def revalidate(proof: Proof) -> None:
    if archive_verify.source_manifest(proof.source) != proof.source_manifest:
        refuse("RECOVERY_SOURCE_CHANGED", "historical source changed during recovery")
    _repository_guard(proof.current.root)
    current = gitstate.capture_entry(proof.current.root)
    if current != proof.current:
        refuse("RECOVERY_BOUNDARY_CHANGED", "repository boundary changed during recovery")
    if proof.ownership_resolution_paths:
        from . import ownership_cli

        try:
            for path, expected in zip(
                proof.ownership_resolution_paths, proof.ownership_resolutions
            ):
                actual = ownership_cli.validate_for_source(
                    path, proof.current.root, proof.source, proof.state,
                    proof.source_manifest,
                )
                if actual != expected:
                    refuse(
                        "RECOVERY_RESOLUTION_CHANGED",
                        "ownership resolution changed during recovery",
                        "requires_manager_ownership",
                    )
        except ownership_cli.OwnershipResolutionError as error:
            refuse(error.code, error.detail, "requires_manager_ownership")
