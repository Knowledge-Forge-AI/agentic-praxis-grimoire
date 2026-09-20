"""Dispatcher-owned Git finalization for normal and resumed lifecycles."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NoReturn

from . import candidate as candidate_module
from . import checkpoint as checkpoint_module
from .failure_boundary import record_manager_attention
from . import gitstate as gitstate_module
from . import stage_delta as stage_delta_module
from . import path_disposition as ownership_module
from .lifecycle import (
    FINALIZATION_CHECKPOINT,
    FINALIZATION_COMMIT_LOCAL,
    FINALIZATION_PUBLISH,
    get_lifecycle,
    validate_finalization,
)
from .publication import PublicationError, publish, publish_or_reuse, record
from .result import ResultError, StageResult


class FinalizationError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _safe_commit(
    root: Path,
    paths: list[str],
    message: str,
    expected_branch: str | None = None,
) -> str:
    commit_fn = gitstate_module.commit
    if expected_branch is None:
        return commit_fn(root, paths, message)
    try:
        import inspect
        sig = inspect.signature(commit_fn)
        accepts_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD or p.name == "expected_branch"
            for p in sig.parameters.values()
        )
    except Exception:
        accepts_kw = True
    if accepts_kw:
        return commit_fn(root, paths, message, expected_branch=expected_branch)
    return commit_fn(root, paths, message)


def _fail(code: str, detail: str) -> NoReturn:
    raise FinalizationError(code, detail)


def validate_transition(source: str, target: str) -> None:
    """Allow only the documented monotonic finalization transitions."""
    try:
        validate_finalization(source)
        validate_finalization(target)
    except ValueError as error:
        _fail("FINALIZATION_POLICY_INVALID", str(error))
    rank = {
        FINALIZATION_CHECKPOINT: 0,
        FINALIZATION_COMMIT_LOCAL: 1,
        FINALIZATION_PUBLISH: 2,
    }
    if rank[target] < rank[source]:
        _fail(
            "FINALIZATION_TRANSITION_INVALID",
            f"cannot downgrade finalization from {source} to {target}",
        )


def _lifecycle(state: dict[str, Any]) -> None:
    try:
        specification = get_lifecycle(str(state.get("lifecycle", "standard")))
    except ValueError as error:
        _fail("LIFECYCLE_INVALID", str(error))
    effective = state.get("effective_stages")
    if not isinstance(effective, dict) or tuple(effective) != specification.stage_names:
        _fail(
            "INVOCATION_COUNT",
            f"effective lifecycle must contain {list(specification.stage_names)} exactly once",
        )
    checkpoints = state.get("effective_checkpoints")
    if not isinstance(checkpoints, list) or checkpoints != list(specification.checkpoints):
        _fail(
            "REVIEW_COUNT",
            f"effective lifecycle must contain {list(specification.checkpoints)} exactly once",
        )
    inherited = int(state.get("provider_invocations_inherited", 0))
    performed = int(state.get("provider_invocations_performed", 0))
    if inherited + performed != specification.expected_provider_invocations:
        _fail(
            "INVOCATION_COUNT",
            f"effective lifecycle has {inherited} inherited and {performed} performed invocations",
        )
    state["provider_invocations_effective"] = inherited + performed
    state["effective_review_count"] = len(checkpoints)


def _phase_delta(
    state: dict[str, Any], entry: gitstate_module.EntryState, final_tree: str
) -> list[gitstate_module.Change]:
    from . import adoption
    adoption.guard_boundary(state, entry.root, final_tree)
    carried: set[str] = adoption.paths(state)
    manifest = state.get("candidate_manifest")
    if manifest is not None:
        try:
            gitstate_module.validate_candidate_manifest(manifest)
        except gitstate_module.GitStateError as error:
            _fail("CANDIDATE_MANIFEST_INVALID", error.detail)
        carried.update(manifest["paths"])
    recorded_paths = state.get("phase_owned_paths", [])
    if recorded_paths is not None:
        if not isinstance(recorded_paths, list) or any(
            not isinstance(path, str) for path in recorded_paths
        ):
            _fail("CANDIDATE_MANIFEST_INVALID", "phase-owned path evidence is invalid")
        carried.update(recorded_paths)
    try:
        boundary_delta = gitstate_module.phase_delta(entry.root, entry.tree, final_tree)
    except gitstate_module.GitStateError as error:
        _fail(error.code, error.detail)
    if ((state.get("resume") or {}).get("finalization_replayed") is True
            and any(change.path not in carried for change in boundary_delta)):
        _fail("RESUME_CANDIDATE_CONFLICT", "finalize-only boundary acquired unowned paths")
    # A fresh dispatch records a mechanical boundary before terminal parsing,
    # but those paths are not ownership proof yet: any path already dirty at
    # entry must still be rejected as an overlap. Resumed attempts carry a
    # validated manifest, so inherited phase paths are intentionally excluded
    # from that check.
    dirty_paths = {change.path for change in boundary_delta} & set(entry.dirty)
    dirty_paths -= adoption.paths(state)
    if state.get("resumed"):
        dirty_paths -= carried
    overlap = sorted(dirty_paths)
    if overlap:
        # The terminal dispositioner owns this ambiguity. Preserve the complete
        # candidate and surface the overlap to the manager instead of discarding
        # a successfully completed lifecycle merely because exact-path
        # publication cannot separate two authors of the same path.
        state["entry_dirt_overlap"] = overlap
        state["manager_disposition_required"] = True
        state["manager_disposition"] = {
            "required": True,
            "reason": "entry_dirt_overlap",
            "paths": overlap,
            "candidate_tree": final_tree,
            "automatic_publication": "not_attempted",
        }
    carried.update(change.path for change in boundary_delta)
    adoption.guard_owned(state, carried)
    try:
        # The commit delta is relative to the current boundary's HEAD. This
        # includes inherited phase paths that were already present as
        # unstaged candidate bytes when the resumed attempt began, while
        # excluding unrelated operator dirt that was also present there.
        head_delta = gitstate_module.phase_delta(entry.root, entry.head, final_tree)
    except gitstate_module.GitStateError as error:
        _fail(error.code, error.detail)
    delta = [change for change in head_delta if change.path in carried]
    state["phase_owned_paths"] = sorted(carried)
    state["boundary_phase_delta"] = [
        {"status": change.status, "path": change.path}
        for change in boundary_delta
    ]
    state["phase_delta"] = [
        {"status": change.status, "path": change.path} for change in delta
    ]
    state["phase_owned_paths_finalized"] = True
    return delta


def _candidate_manifest(
    state: dict[str, Any], entry: gitstate_module.EntryState, final_tree: str
) -> None:
    """Seal phase-owned candidate identities for later review and resume."""
    owned = state.get("phase_owned_paths", [])
    if not isinstance(owned, list) or any(not isinstance(path, str) for path in owned):
        _fail("CANDIDATE_MANIFEST_INVALID", "phase-owned path evidence is invalid")
    resume = state.get("resume")
    base_tree = entry.tree
    if isinstance(resume, dict) and isinstance(resume.get("source_entry_tree"), str):
        base_tree = resume["source_entry_tree"]
    if state.get("path_ownership"):
        base_tree = state["path_ownership"]["entry_tree"]
    try:
        state["candidate_manifest"] = gitstate_module.candidate_manifest(
            entry.root, base_tree, final_tree, paths=owned
        )
    except gitstate_module.GitStateError as error:
        _fail("CANDIDATE_MANIFEST_INVALID", error.detail)


def _preserve_candidate_for_manager(
    state: dict[str, Any],
    current_head: str,
    final_tree: str,
    overlap: list[str],
) -> None:
    """Record a complete candidate when exact publication needs a manager."""
    state["manager_disposition_required"] = True
    state["manager_disposition"] = {
        "required": True,
        "reason": "entry_dirt_overlap",
        "paths": list(overlap),
        "candidate_tree": final_tree,
        "automatic_publication": "not_attempted",
    }
    state["repository_mutation_attempted"] = False
    state["repository_finalized"] = False
    state["completion_kind"] = "candidate_requires_manager_disposition"
    state["finalization_outcome"] = "blocked"
    state["commit"] = None
    state["final_head"] = current_head
    state["push"] = {
        **record(None),
        "status": "not_attempted_manager_disposition",
        "failure": {
            "code": "ENTRY_DIRT_OVERLAP",
            "detail": (
                "phase and operator bytes overlap; exact-path publication "
                f"requires manager disposition for {list(overlap)}"
            ),
        },
    }


def _is_finalize_replay(state: dict[str, Any], resumed: bool) -> bool:
    resume = state.get("resume")
    return (
        resumed
        and isinstance(resume, dict)
        and resume.get("finalization_replayed") is True
    )


def _reuse_completed_commit(
    state: dict[str, Any],
    entry: gitstate_module.EntryState,
    final_tree: str,
    parsed: StageResult,
) -> str:
    """Revalidate the recorded commit when finalize-only resume is idempotent."""
    record = state.get("commit")
    resume = state.get("resume")
    manifest = state.get("candidate_manifest")
    if (
        not isinstance(record, dict)
        or not isinstance(record.get("sha"), str)
        or not isinstance(resume, dict)
        or not isinstance(resume.get("source_entry_head"), str)
        or not isinstance(manifest, dict)
    ):
        _fail(
            "RESUME_COMMIT_MISMATCH",
            "completed resume lacks recorded commit provenance",
        )
    head = gitstate_module.current_head(entry.root)
    if head != record["sha"]:
        _fail("RESUME_COMMIT_MISMATCH", "current HEAD differs from recorded phase commit")
    try:
        gitstate_module.verify_recorded_commit(
            entry.root,
            resume["source_entry_head"],
            head,
            final_tree,
            list(manifest["paths"]),
        )
        gitstate_module.verify_untouched(entry.root, entry)
        actual_message = gitstate_module.commit_message(entry.root, head)
    except gitstate_module.GitStateError as error:
        _fail("RESUME_COMMIT_MISMATCH", error.detail)
    expected_message = parsed.commit_message.render() if parsed.commit_message else ""
    if actual_message != expected_message:
        _fail("RESUME_COMMIT_MISMATCH", "recorded phase commit message differs from closeout")
    state["commit_reused"] = True
    state["commit_verified"] = True
    return head


def _verify_existing_commit(
    state: dict[str, Any],
    entry: gitstate_module.EntryState,
    delta: list[gitstate_module.Change],
    final_tree: str,
    parsed: StageResult,
) -> str:
    record = state.get("commit")
    if not isinstance(record, dict) or not isinstance(record.get("sha"), str):
        _fail("RESUME_COMMIT_MISMATCH", "current HEAD advanced without a recorded phase commit")
    head = gitstate_module.current_head(entry.root)
    if head != record["sha"]:
        _fail("RESUME_COMMIT_MISMATCH", "current HEAD differs from recorded phase commit")
    try:
        gitstate_module.verify_commit(entry.root, entry, delta, final_tree, head)
        actual_message = gitstate_module.commit_message(entry.root, head)
    except gitstate_module.GitStateError as error:
        _fail("RESUME_COMMIT_MISMATCH", error.detail)
    expected_message = parsed.commit_message.render() if parsed.commit_message else ""
    if actual_message != expected_message:
        _fail("RESUME_COMMIT_MISMATCH", "recorded phase commit message differs from closeout")
    state["commit_reused"] = True
    state["commit_verified"] = True
    return head


def finalize_repository(
    state: dict[str, Any],
    entry: gitstate_module.EntryState,
    parsed: StageResult,
    display: Any,
    *,
    resumed: bool,
    directory: Any | None = None,
    expected_index: dict[str, Any] | None = None,
) -> None:
    """Validate lifecycle/candidate truth, then apply operator Git policy."""
    state["finalization_attempted"] = True
    state["finalization_outcome"] = "blocked"
    if not parsed.completed:
        _fail("PROVIDER_OUTCOME_INVALID", "closeout result is not completed")
    _lifecycle(state)
    try:
        policy = validate_finalization(
            str(state.get("finalization_policy", FINALIZATION_PUBLISH))
        )
    except ValueError as error:
        _fail("FINALIZATION_POLICY_INVALID", str(error))
    try:
        observed_index = gitstate_module.index_identity(entry.root)
    except gitstate_module.GitStateError as error:
        _fail(error.code, error.detail)
    if expected_index is None:
        native_transition = state.get("native_git_transition")
        native_accepted = (
            isinstance(native_transition, dict)
            and native_transition.get("status") == "accepted"
        )
        if native_accepted and native_transition.get("commit_tree"):
            expected_index = gitstate_module.index_identity_for_tree(
                entry.root, native_transition["commit_tree"]
            )
        else:
            expected_index = entry.index_identity
    state["pre_finalization_index"] = {
        "expected": expected_index,
        "observed": observed_index,
        "unchanged": observed_index == expected_index,
    }
    if observed_index != expected_index:
        code = (
            "CHECKPOINT_INDEX_MUTATED"
            if policy == FINALIZATION_CHECKPOINT
            else "FINALIZATION_INDEX_MUTATED"
        )
        _fail(code, "real index differs from the dispatcher entry boundary")
    final = candidate_module.tree_identity(entry.root)
    final_tree = str(final["tree"])
    finalize_replay = _is_finalize_replay(state, resumed)
    terminal_candidate = state.get("terminal_candidate") or state.get(
        "closeout_candidate"
    )
    expected = str((terminal_candidate or {}).get("tree", final_tree))
    if not finalize_replay and final_tree != expected:
        _fail("RESUME_TREE_MISMATCH", "worktree differs from recorded terminal candidate")
    if finalize_replay:
        manifest = state.get("candidate_manifest")
        if not isinstance(manifest, dict):
            _fail("CANDIDATE_MANIFEST_INVALID", "finalize-only resume lacks candidate manifest")
        try:
            conflicts = gitstate_module.candidate_manifest_conflicts(
                entry.root, final_tree, manifest
            )
        except gitstate_module.GitStateError as error:
            _fail("CANDIDATE_MANIFEST_INVALID", error.detail)
        if conflicts:
            _fail(
                "RESUME_CANDIDATE_CONFLICT",
                "final candidate differs from inherited phase paths: "
                + ", ".join(conflicts),
            )
    state["final_tree"] = final_tree
    from . import ownership_challenge as challenges
    try:
        legacy_exact_replay = finalize_replay and state.get('ownership_challenges') is None
        if not state.get('_ownership_recovery') and not legacy_exact_replay:
            challenges.observe(entry.root, state, entry, final_tree, parsed.stage, 'post_terminal')
            # Exact resume reuses already validated provider events; it cannot
            # reinterpret the original response against a newly minted ID.
            if not finalize_replay:
                challenges.resolve_provider(entry.root, state, parsed.stage, final_tree,
                                             parsed.ownership_resolutions)
        else:
            challenges.validate(entry.root, state)
    except ResultError as error:
        _fail(error.code, error.detail)
    delta = _phase_delta(state, entry, final_tree)
    grants = {path for path, decision in challenges.decisions(state).items() if decision == 'phase_owned'}
    if state.get('entry_dirt_overlap'):
        state['entry_dirt_overlap'] = sorted(set(state['entry_dirt_overlap']) - grants)
        if not state['entry_dirt_overlap']:
            state['manager_disposition_required'] = False
            state.pop('manager_disposition', None)
    try:
        final_tree, excluded, ambiguous = ownership_module.apply(
            state, entry, final_tree, parsed.path_dispositions
        )
    except (ResultError, candidate_module.CandidateError, gitstate_module.GitStateError) as error:
        record_manager_attention(
            state, reason="path_ownership_invalid", detail=str(error),
            candidate_tree=final_tree,
        )
        _fail("PATH_DISPOSITION_INVALID", str(error))
    if ambiguous:
        record_manager_attention(
            state, reason="path_ownership_required",
            detail="exact ownership challenges require ID-based resolution",
            paths=ambiguous[:ownership_module.MAX_ENTRIES], candidate_tree=final_tree,
        )
    state["phase_owned_paths"] = sorted(
        (set(state["phase_owned_paths"]) | {
            item["path"] for item in state["path_dispositions"]
            if item["disposition"] == "phase_owned"
        }) - excluded - set(ambiguous)
    )
    delta = [change for change in gitstate_module.phase_delta(entry.root, entry.head, final_tree)
             if change.path in state["phase_owned_paths"]]
    state["phase_delta"] = [change._asdict() for change in delta]
    state["final_tree"] = final_tree
    stage_delta_module.finalize_stage_deltas(
        state, [change.path for change in delta]
    )
    _candidate_manifest(state, entry, final_tree)
    display.git_delta([change.path for change in delta])
    current_head = gitstate_module.current_head(entry.root)
    curr_branch = gitstate_module.current_branch(entry.root)
    state["git_authority_branch"] = {
        "entry_branch": entry.branch,
        "current_branch": curr_branch,
        "matches": curr_branch == entry.branch,
    }
    if curr_branch != entry.branch:
        stage_delta_module.finalize_stage_deltas(state, [])
        state["git_authority_branch_mismatch"] = {
            "entry_branch": entry.branch,
            "current_branch": curr_branch,
        }
        record_manager_attention(
            state, reason="git_authority_branch_mismatch",
            detail=f"branch changed from {entry.branch!r} to {curr_branch!r}",
            paths=[change.path for change in delta], candidate_tree=final_tree,
        )
        state["manager_disposition"].update({
            "entry_branch": entry.branch, "current_branch": curr_branch,
        })
        state["repository_mutation_attempted"] = False
        state["repository_finalized"] = False
        state["completion_kind"] = "candidate_requires_manager_disposition"
        state["commit"] = None
        state["final_head"] = current_head
        state["push"] = {
            **record(None),
            "status": "not_attempted_branch_mismatch",
            "failure": {
                "code": "GIT_AUTHORITY_BRANCH_MISMATCH",
                "detail": (
                    f"repository branch changed from {entry.branch!r} to {curr_branch!r}; "
                    "candidate is preserved for manager disposition"
                ),
            },
        }
        _fail(
            "GIT_AUTHORITY_BRANCH_MISMATCH",
            f"repository branch changed from {entry.branch!r} to {curr_branch!r}; "
            "candidate is preserved for manager disposition",
        )

    # Git operation markers are an unsafe preservation boundary. The candidate
    # and manifest are already closed above, so the outer failure path can
    # archive the exact bytes while preventing an automatic commit or push.
    try:
        active_operations = gitstate_module.active_git_operations(entry.root)
    except gitstate_module.GitStateError as error:
        _fail(error.code, error.detail)
    if active_operations:
        stage_delta_module.finalize_stage_deltas(state, [])
        state["active_git_operations"] = list(active_operations)
        record_manager_attention(
            state, reason="active_git_operation",
            detail="active Git operations: " + ", ".join(active_operations),
            paths=[change.path for change in delta], candidate_tree=final_tree,
        )
        state["repository_mutation_attempted"] = False
        state["repository_finalized"] = False
        state["completion_kind"] = "candidate_preserved_blocked"
        state["commit"] = None
        state["final_head"] = current_head
        state["push"] = {
            **record(None),
            "status": "not_attempted_active_git_operation",
            "failure": {
                "code": "ENTRY_ACTIVE_GIT_OPERATION",
                "detail": (
                    "repository has active Git operation state: "
                    + ", ".join(active_operations)
                ),
            },
        }
        _fail(
            "ENTRY_ACTIVE_GIT_OPERATION",
            "repository has active Git operation state: "
            + ", ".join(active_operations),
        )

    if challenges.open_records(state):
        if directory is not None:
            try:
                challenges.capture_candidate(directory, entry, state, str(final['tree']))
            except (checkpoint_module.CheckpointError, ResultError, OSError) as error:
                _fail('OWNERSHIP_EVIDENCE_CAPTURE_FAILED', str(error))
        state['repository_mutation_attempted'] = False
        state['repository_finalized'] = False
        state['completion_kind'] = 'candidate_requires_manager_disposition'
        state['commit'] = None
        state['final_head'] = current_head
        state['push'] = {**record(None), 'status': 'not_attempted_manager_ownership',
                         'failure': {'code': 'OWNERSHIP_CHALLENGE_OPEN',
                                     'detail': 'exact challenge resolution required; entry dirt is not automatically restored'}}
        return

    if policy == FINALIZATION_CHECKPOINT:
        native_transition = state.get("native_git_transition")
        native_accepted = (
            isinstance(native_transition, dict)
            and native_transition.get("status") == "accepted"
            and current_head == native_transition.get("commit")
        )
        if current_head != entry.head and not native_accepted:
            _fail("RESUME_COMMIT_MISMATCH", "checkpoint unexpectedly advanced HEAD")
        if directory is None:
            _fail("CHECKPOINT_EVIDENCE_FAILED", "checkpoint artifact directory is unavailable")
        try:
            checkpoint_candidate = checkpoint_module.create(
                directory, entry, final_tree, delta, observed_index,
                raw_terminal_tree=str(final["tree"]),
            )
        except (checkpoint_module.CheckpointError, OSError) as error:
            _fail("CHECKPOINT_EVIDENCE_FAILED", str(error))
        state["checkpoint_candidate"] = checkpoint_candidate
        state["commit"] = (
            {"sha": current_head, "subject": gitstate_module.commit_subject(entry.root, current_head)}
            if native_accepted
            else None
        )
        state["final_head"] = current_head
        state["push"] = {
            **record(None),
            "status": "not_attempted_by_policy",
        }
        state["manager_disposition_required"] = True
        state["repository_finalized"] = False
        state["completion_kind"] = "checkpoint_ready"
        state["finalization_outcome"] = "completed"
        return

    overlap = state.get("entry_dirt_overlap")
    if isinstance(overlap, list) and overlap:
        stage_delta_module.finalize_stage_deltas(state, [])
        _preserve_candidate_for_manager(state, current_head, final_tree, overlap)
        return

    if state.get("manager_disposition_required"):
        stage_delta_module.finalize_stage_deltas(state, [])
        reasons = state.get("manager_attention_reasons", [])
        primary_reason = reasons[0] if reasons else "manager_attention_required"
        state["repository_mutation_attempted"] = False
        state["repository_finalized"] = False
        state["completion_kind"] = "candidate_requires_manager_disposition"
        state["commit"] = None
        state["final_head"] = current_head
        state["push"] = {
            **record(None),
            "status": f"not_attempted_{primary_reason}",
            "failure": {
                "code": "MANAGER_DISPOSITION_REQUIRED",
                "detail": f"manager disposition required: {reasons}",
            },
        }
        return

    # Exclusions are deliberate local observations. Bind their current bytes
    # for post-commit preservation without changing the entry authority record.
    if excluded:
        excluded_manifest = gitstate_module.candidate_manifest(
            entry.root, entry.tree, final_tree, paths=excluded
        )
        if gitstate_module.candidate_manifest_conflicts(entry.root, current_head, excluded_manifest):
            record_manager_attention(
                state, reason="path_ownership_invalid",
                detail="excluded publication objects differ from current HEAD",
                paths=sorted(excluded)[:ownership_module.MAX_ENTRIES],
                candidate_tree=final_tree,
            )
            _fail("PATH_DISPOSITION_INVALID", "excluded publication objects differ from current HEAD")
        preserved = dict(entry.dirty)
        for path in excluded:
            preserved.setdefault(path, gitstate_module._identity(entry.root, path))
        entry = entry._replace(dirty=preserved)

    recorded_commit = state.get("commit")
    reused = False
    if (
        finalize_replay
        and isinstance(recorded_commit, dict)
        and recorded_commit.get("sha") == current_head
    ):
        head = _reuse_completed_commit(state, entry, final_tree, parsed)
        state["final_head"] = head
        reused = True
    elif not delta:
        if current_head != entry.head:
            _fail("RESUME_COMMIT_MISMATCH", "empty phase delta unexpectedly advanced HEAD")
        try:
            gitstate_module.verify_untouched(entry.root, entry)
        except gitstate_module.GitStateError as error:
            _fail(error.code, error.detail)
        state["commit"] = None
        state["final_head"] = entry.head
        state["push"] = {
            **record(None),
            "status": "not_attempted_by_policy" if policy == FINALIZATION_COMMIT_LOCAL
            else "not_attempted",
        }
        if not state.get("manager_disposition_required"):
            state["manager_disposition_required"] = False
            state["repository_finalized"] = True
            state["completion_kind"] = "finalized_empty_delta"
            state["finalization_outcome"] = "completed"
        else:
            state["repository_finalized"] = False
            state["completion_kind"] = "candidate_requires_manager_disposition"
            state["finalization_outcome"] = "blocked"
        return

    if not reused:
        native_transition = state.get("native_git_transition")
        native_accepted = (
            isinstance(native_transition, dict)
            and native_transition.get("status") == "accepted"
            and current_head == native_transition.get("commit")
        )

        if native_accepted and final_tree == native_transition.get("commit_tree"):
            head = current_head
            state["final_head"] = head
            state["commit"] = {
                "sha": head,
                "subject": gitstate_module.commit_subject(entry.root, head),
            }
            state["commit_reused"] = True
            state["commit_verified"] = True
            state["real_index_identity_final"] = gitstate_module.index_identity(entry.root)
            if parsed.commit_message is not None:
                state["commit_message_superseded_by_native_commit"] = True
            reused = True
        elif native_accepted:
            message = parsed.commit_message
            if message is None:
                _fail(
                    "COMMIT_MESSAGE_MISSING",
                    f"closeout changed {len(delta)} path(s) but proposed no commit message",
                )
            follow_up_changes = [
                c for c in gitstate_module.phase_delta(entry.root, native_transition["commit_tree"], final_tree)
                if c.path in state["phase_owned_paths"]
            ]
            display.git_committing(message.subject)
            try:
                head = _safe_commit(
                    entry.root,
                    [change.path for change in follow_up_changes],
                    message.render(),
                    expected_branch=entry.branch,
                )
                state["final_head"] = head
                state["commit"] = {"sha": head, "subject": message.subject}
                state["native_follow_up_commit"] = head
                gitstate_module.verify_commit(
                    entry.root, entry, delta, final_tree, head,
                    expected_parent=native_transition["commit"],
                )
                state["commit_verified"] = True
                state["commit_reused"] = False
                state["real_index_identity_final"] = gitstate_module.index_identity(entry.root)
            except gitstate_module.GitStateError as error:
                _fail(error.code, error.detail)
            display.git_committed(head)
            reused = False
        elif current_head == entry.head:
            message = parsed.commit_message
            if message is None:
                _fail(
                    "COMMIT_MESSAGE_MISSING",
                    f"closeout changed {len(delta)} path(s) but proposed no commit message",
                )
            display.git_committing(message.subject)
            try:
                head = _safe_commit(
                    entry.root,
                    [change.path for change in delta],
                    message.render(),
                    expected_branch=entry.branch,
                )
                state["final_head"] = head
                state["commit"] = {"sha": head, "subject": message.subject}
                gitstate_module.verify_commit(entry.root, entry, delta, final_tree, head)
                state["commit_verified"] = True
                state["commit_reused"] = False
                state["real_index_identity_final"] = gitstate_module.index_identity(entry.root)
            except gitstate_module.GitStateError as error:
                _fail(error.code, error.detail)
            display.git_committed(head)
            reused = False
        else:
            head = _verify_existing_commit(state, entry, delta, final_tree, parsed)
            state["final_head"] = head
            reused = True

    if policy == FINALIZATION_COMMIT_LOCAL:
        state["push"] = {
            **record(head),
            "status": "not_attempted_by_policy",
        }
        if not state.get("manager_disposition_required"):
            state["manager_disposition_required"] = False
            state["repository_finalized"] = True
            state["completion_kind"] = "committed_local"
            state["finalization_outcome"] = "reused" if reused else "completed"
        else:
            state["repository_finalized"] = False
            state["completion_kind"] = "candidate_requires_manager_disposition"
            state["finalization_outcome"] = "blocked"
        return

    try:
        publication_entry_head = entry.head
        resume_record = state.get("resume")
        if (
            resumed
            and reused
            and isinstance(resume_record, dict)
            and isinstance(resume_record.get("source_entry_head"), str)
        ):
            # A finalize-only replay starts at the already-created phase
            # commit. Publication accounting must exclude that phase commit
            # and count only ancestors that predated it.
            publication_entry_head = resume_record["source_entry_head"]
        state["push"] = (
            publish_or_reuse(
                entry.root,
                publication_entry_head,
                head,
                display,
                expected_branch=entry.branch,
            )
            if resumed and reused
            else publish(
                entry.root,
                publication_entry_head,
                head,
                display,
                expected_branch=entry.branch,
            )
        )
    except PublicationError as error:
        state["push"] = error.record
        state["finalization_outcome"] = "blocked"
        _fail(error.code, error.detail)
    if not state.get("manager_disposition_required"):
        state["manager_disposition_required"] = False
        state["repository_finalized"] = True
        state["completion_kind"] = "published"
        state["finalization_outcome"] = (
            "reused" if (resumed and reused) else "completed"
        )
    else:
        state["repository_finalized"] = False
        state["completion_kind"] = "candidate_requires_manager_disposition"
        state["finalization_outcome"] = "blocked"
