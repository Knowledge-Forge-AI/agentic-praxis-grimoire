"""Strict source-run structure and artifact validation for resume."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from . import candidate as candidate_module
from . import antigravity_evidence as antigravity_evidence_module
from . import gitstate as gitstate_module
from . import review_result as review_result_module
from . import run as run_module
from .runtime_exclusion import disposable_runtime
from .lifecycle import LIFECYCLE_STANDARD, get_lifecycle
from .request import PhaseRequest


_STANDARD = get_lifecycle(LIFECYCLE_STANDARD)
STAGES = _STANDARD.stage_names
PREFIXES = _STANDARD.prefixes
CHECKPOINTS = _STANDARD.checkpoint_by_stage


class ResumeError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(source: Path, name: str) -> dict[str, Any]:
    path = source / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ResumeError(
            "RESUME_SOURCE_INVALID", f"cannot read source {name}: {error}"
        ) from error
    if not isinstance(value, dict):
        raise ResumeError("RESUME_SOURCE_INVALID", f"source {name} is not an object")
    return value


def require_source(path: Path, excluded: list[dict[str, str]] | None = None) -> Path:
    if path.is_symlink():
        raise ResumeError("RESUME_SOURCE_INVALID", "source run must not be a symlink")
    try:
        source = path.resolve(strict=True)
    except OSError as error:
        raise ResumeError("RESUME_SOURCE_INVALID", f"source run is unreadable: {error}") from error
    if not source.is_dir() or source.is_symlink():
        raise ResumeError("RESUME_SOURCE_INVALID", "source run must be an exact directory")
    def walk(descriptor: int, relative: Path) -> None:
        with os.scandir(descriptor) as entries:
            for entry in entries:
                child = relative / entry.name
                reason = disposable_runtime(child)
                if reason:
                    if excluded is not None:
                        excluded.append({"path": child.as_posix(), "reason": reason})
                    continue
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    nested = os.open(entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                     dir_fd=descriptor)
                    try:
                        walk(nested, child)
                    finally:
                        os.close(nested)
                elif not stat.S_ISREG(info.st_mode):
                    raise ResumeError(
                        "RESUME_SOURCE_INVALID", f"source run contains unsupported node: {child}"
                    )

    try:
        descriptor = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            walk(descriptor, Path())
        finally:
            os.close(descriptor)
    except OSError as error:
        raise ResumeError("RESUME_SOURCE_INVALID", "cannot traverse source run without following links") from error
    return source


def phase_id_for_resume(source_path: Path, request_path: Path) -> str:
    """Derive resume identity from a structurally validated closed source run."""
    source = require_source(source_path)
    state = load_json(source, "state.json")
    result = load_json(source, "result.json")
    run_module.validate_run_topology(
        source, state, result, error_fn=ResumeError
    )
    phase_id = str(state["phase_id"])
    try:
        supplied = request_path.read_bytes()
        retained = (source / "request.json").read_bytes()
    except OSError as error:
        raise ResumeError(
            "RESUME_SOURCE_INVALID", f"cannot read retained request bytes: {error}"
        ) from error
    if supplied != retained:
        raise ResumeError(
            "RESUME_REQUEST_MISMATCH",
            "supplied request bytes differ from source request.json",
        )
    return phase_id


def entry(
    source: Path,
    state: dict[str, Any],
    *,
    detached: bool = False,
) -> gitstate_module.EntryState:
    raw = state.get("entry")
    if not isinstance(raw, dict):
        raise ResumeError("RESUME_SOURCE_INVALID", "source state has no entry evidence")
    dirty_names = raw.get("dirty", [])
    dirty: dict[str, dict[str, Any]] = {}
    if (source / "entry-evidence.json").exists():
        evidence = load_json(source, "entry-evidence.json")
        if evidence.get("head") != raw.get("head") or evidence.get("tree") != raw.get("tree"):
            raise ResumeError("RESUME_ARTIFACT_MISMATCH", "entry evidence disagrees with state")
        candidate = evidence.get("dirty")
        if not isinstance(candidate, dict):
            raise ResumeError("RESUME_ARTIFACT_MISMATCH", "entry dirty evidence is invalid")
        dirty = candidate
    elif dirty_names:
        raise ResumeError(
            "RESUME_ARTIFACT_MISMATCH",
            "source predates resumable entry-dirt identity evidence",
        )
    if sorted(dirty) != sorted(dirty_names):
        raise ResumeError("RESUME_ARTIFACT_MISMATCH", "entry dirty paths disagree")
    try:
        root = Path(raw["root"])
        if not root.is_absolute():
            raise ValueError("source entry root is not absolute")
        if not detached:
            root = root.resolve()
        head = str(raw["head"])
        # Pre-R1 entries refused staged changes too. Deriving their missing
        # semantic index identity from the durable entry HEAD preserves safe
        # checkpoint finalization without trusting the current real index.
        index = (
            dict(raw["index"])
            if "index" in raw
            else (
                _missing_detached_index()
                if detached
                else gitstate_module.index_identity_for_tree(root, head)
            )
        )
        return gitstate_module.EntryState(
            root=root, head=head, branch=str(raw["branch"]),
            tree=str(raw["tree"]), dirty=dirty, index_identity=index,
        )
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise ResumeError("RESUME_SOURCE_INVALID", f"invalid source entry: {error}") from error


def _missing_detached_index() -> dict[str, Any]:
    return {
        "kind": "not_recorded_historical_source_provenance",
        "repository_state_validated": False,
    }


def completed_prefix(
    state: dict[str, Any], resolved: dict[str, Any], source: Path
) -> tuple[str, ...]:
    try:
        lifecycle = get_lifecycle(str(state.get("lifecycle", LIFECYCLE_STANDARD)))
    except ValueError as error:
        raise ResumeError("RESUME_SOURCE_INVALID", str(error)) from error
    raw = state.get("stages_completed")
    if not isinstance(raw, list) or raw != list(lifecycle.stage_names[: len(raw)]):
        raise ResumeError(
            "RESUME_SOURCE_INVALID", "completed stages are not one contiguous semantic prefix"
        )
    review_outcomes: dict[str, str] = {}
    for stage in raw:
        prefix = lifecycle.prefixes[stage]
        for suffix in ("prompt.md", "stdout.md", "stderr.log", "meta.json"):
            if not (source / f"{prefix}.{suffix}").is_file():
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH", f"missing stage artifact: {prefix}.{suffix}"
                )
        from .route_provenance import stage_effective_route

        meta = load_json(source, f"{prefix}.meta.json")
        route = stage_effective_route(resolved, stage)
        if (
            meta.get("stage") != stage
            or meta.get("exit_code") != 0
            or meta.get("stdout_sha256") != sha256(source / f"{prefix}.stdout.md")
            or meta.get("prompt_sha256") != sha256(source / f"{prefix}.prompt.md")
            or not isinstance(route, dict)
            or any(meta.get(key) != route.get(key) for key in ("role", "provider", "profile"))
        ):
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH", f"stage metadata does not bind {prefix}"
            )
        if meta.get("provider") == "antigravity":
            try:
                evidence = antigravity_evidence_module.validate(
                    source,
                    prefix,
                    str(meta.get("profile")),
                    str((route.get("intelligence") or {}).get("model")),
                    bool(route.get("process_read_only")),
                    0,
                )
            except antigravity_evidence_module.EvidenceError as error:
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH",
                    f"invalid inherited Antigravity evidence for {prefix}: {error}",
                ) from error
            if meta.get("antigravity_evidence") != evidence:
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH",
                    f"Antigravity evidence metadata does not bind {prefix}",
                )
        elif meta.get("antigravity_evidence") is not None:
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH",
                f"non-Antigravity stage carries Antigravity evidence: {prefix}",
            )
        if lifecycle.stage(stage).role == "reviewer":
            artifact = load_json(source, f"{prefix}.result.json")
            nonce = artifact.get("nonce")
            if not isinstance(nonce, str):
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH",
                    f"review result nonce is missing for {prefix}",
                )
            try:
                parsed = review_result_module.parse(
                    (source / f"{prefix}.stdout.md").read_bytes(), stage, nonce
                )
            except review_result_module.ReviewResultError as error:
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH",
                    f"review result does not bind {prefix}: {error}",
                ) from error
            if parsed.as_dict() != artifact:
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH",
                    f"review result is incomplete or disagrees for {prefix}",
                )
            from .review_recovery import validate_recovery

            try:
                validate_recovery(source, lifecycle.stage(stage), artifact)
                recovery_path = source / f"{prefix}.recovery.json"
                if recovery_path.exists() and state.get("review_recoveries", {}).get(stage) != load_json(source, recovery_path.name):
                    raise ValueError("state and review recovery record disagree")
            except (OSError, ValueError, KeyError, TypeError) as error:
                raise ResumeError("RESUME_ARTIFACT_MISMATCH", f"invalid review recovery: {stage}") from error
            review_outcomes[stage] = parsed.outcome
    checkpoint_by_stage = lifecycle.checkpoint_by_stage
    expected = [
        checkpoint_by_stage[stage] for stage in raw if stage in checkpoint_by_stage
    ]
    if state.get("checkpoints_completed") != expected:
        raise ResumeError(
            "RESUME_ARTIFACT_MISMATCH", "checkpoint evidence disagrees with completed stages"
        )
    recorded_reviews = state.get("review_outcomes", {})
    if not isinstance(recorded_reviews, dict) or any(
        recorded_reviews.get(stage) != outcome
        for stage, outcome in review_outcomes.items()
    ):
        raise ResumeError(
            "RESUME_ARTIFACT_MISMATCH", "review outcome evidence disagrees"
        )
    for stage, outcome in recorded_reviews.items():
        if stage in review_outcomes:
            continue
        try:
            specification = lifecycle.stage(stage)
        except ValueError as error:
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH", "unknown attempted review outcome"
            ) from error
        if specification.role != "reviewer" or outcome != "unreviewable":
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH", "noncompleted review outcome is invalid"
            )
        artifact = load_json(source, f"{specification.prefix}.result.json")
        nonce = artifact.get("nonce")
        try:
            parsed = review_result_module.parse(
                (source / f"{specification.prefix}.stdout.md").read_bytes(),
                stage,
                str(nonce),
            )
        except (OSError, review_result_module.ReviewResultError) as error:
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH", "unreviewable attempt evidence is invalid"
            ) from error
        if parsed.as_dict() != artifact or parsed.outcome != "unreviewable":
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH", "unreviewable attempt evidence disagrees"
            )
    return tuple(raw)


def validate_bindings(
    source: Path, state: dict[str, Any], completed: tuple[str, ...]
) -> None:
    lifecycle = get_lifecycle(str(state.get("lifecycle", LIFECYCLE_STANDARD)))
    binding = state.get("plan_candidate")
    if (
        isinstance(binding, dict)
        and binding.get("schema") == "agent-phase-plan-material-v1"
    ):
        try:
            from . import plan_material as plan_material_module

            plan_material_module.verify(source, binding)
        except (OSError, candidate_module.CandidateError) as error:
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH",
                f"plan material artifact disagrees: {error}",
            ) from error
    if "plan" in completed:
        plan_prefix = lifecycle.prefixes["plan"]
        if (
            isinstance(binding, dict)
            and binding.get("schema") == "agent-phase-plan-material-v1"
        ):
            plan_meta = load_json(source, f"{plan_prefix}.meta.json")
            if any(
                binding.get(field) != plan_meta.get(field)
                for field in ("provider", "profile")
            ):
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH",
                    "plan material provider or profile disagrees with stage metadata",
                )
        else:
            actual = candidate_module.plan_identity(
                (source / f"{plan_prefix}.stdout.md").read_bytes()
            )
            if binding != actual:
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH", "plan candidate digest disagrees"
                )
    prior_tree_candidate: str | None = None
    for stage in lifecycle.stages:
        if stage.name not in completed:
            break
        if stage.role == "reviewer":
            candidate_name = (
                "plan_candidate" if stage.name == "plan_review"
                else prior_tree_candidate
            )
            meta = load_json(source, f"{stage.prefix}.meta.json")
            if candidate_name is None or meta.get("candidate") != state.get(candidate_name):
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH",
                    f"{stage.name} candidate binding disagrees",
                )
        if stage.candidate_key is not None:
            candidate = state.get(stage.candidate_key)
            if not isinstance(candidate, dict) or not candidate.get("tree"):
                raise ResumeError(
                    "RESUME_ARTIFACT_MISMATCH",
                    f"{stage.candidate_key} is missing",
                )
            prior_tree_candidate = stage.candidate_key


def load_core(
    source_path: Path,
    phase_id: str,
    request: PhaseRequest,
    root: Path | None,
    project: str | None,
) -> tuple[
    Path, dict[str, Any], dict[str, Any], dict[str, Any],
    gitstate_module.EntryState, tuple[str, ...],
]:
    """Load and cross-bind the source run's durable core evidence."""
    source = require_source(source_path)
    request_json = load_json(source, "request.json")
    state = load_json(source, "state.json")
    result = load_json(source, "result.json")
    resolved = load_json(source, "resolved.json")
    if request_json != request.as_dict():
        raise ResumeError("RESUME_REQUEST_MISMATCH", "request differs from source request.json")
    if (
        state.get("phase_id") != phase_id
        or state.get("phase_type") != request.phase_type
        or state.get("execution_mode") != request.execution_mode
    ):
        raise ResumeError("RESUME_REQUEST_MISMATCH", "semantic phase identity differs")
    lifecycle_name = str(state.get("lifecycle", LIFECYCLE_STANDARD))
    try:
        lifecycle = get_lifecycle(lifecycle_name)
    except ValueError as error:
        raise ResumeError("RESUME_SOURCE_INVALID", str(error)) from error
    detached = root is None and project is None
    if (root is None) != (project is None):
        raise ResumeError(
            "RESUME_SOURCE_INVALID",
            "repository root and project must both be supplied or both omitted",
        )
    source_project = state.get("project")
    if not isinstance(source_project, str):
        raise ResumeError("RESUME_SOURCE_INVALID", "source project is invalid")
    if project is not None and source_project != project:
        raise ResumeError("RESUME_PROJECT_MISMATCH", "source project differs")
    run_module.validate_run_topology(
        source, state, result, error_fn=ResumeError
    )
    for key in (
        "run_layout", "run_id", "project", "phase_id", "phase_type", "execution_mode",
        "lifecycle", "finalization_policy",
        "entry", "final_head", "phase_delta", "commit", "blocking_reason",
        "path_ownership", "path_dispositions", "path_disposition_noops", "excluded_paths",
        "ownership_challenges", "mechanical_phase_owned_paths", "ownership_type_transitions",
        "ownership_candidate_evidence",
        "ownership_challenge_states",
        "raw_terminal_candidate", "publication_candidate", "mechanical_phase_delta", "adoption",
    ):
        default = [] if key in {"path_dispositions", "path_disposition_noops", "excluded_paths"} else None
        if result.get(key, default) != state.get(key, default):
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH", f"source result and state disagree on {key}"
            )
    from . import ownership_challenge
    if state.get('ownership_challenges') is not None:
        if state.get('ownership_challenge_states') != ownership_challenge.statuses(state):
            raise ResumeError('RESUME_ARTIFACT_MISMATCH', 'challenge state view disagrees with immutable events')
    from . import outcomes
    try:
        outcomes.validate(state, result)
    except ValueError as error:
        raise ResumeError("RESUME_ARTIFACT_MISMATCH", str(error)) from error
    if (
        resolved.get("phase_type") != request.phase_type
        or resolved.get("execution_mode") != request.execution_mode
        or resolved.get("lifecycle", LIFECYCLE_STANDARD) != lifecycle.name
    ):
        raise ResumeError("RESUME_ARTIFACT_MISMATCH", "resolved route identity disagrees")
    source_entry = entry(source, state, detached=detached)
    if state.get("adoption") is not None:
        from . import adoption
        try:
            if load_json(source, "adoption.json") != state["adoption"]:
                raise adoption.AdoptionError("archived adoption differs from state")
            adoption.validate_state(state, request, source_entry)
            if root is not None:
                adoption.validate_retained(root, state["adoption"])
        except (ValueError, RuntimeError, KeyError) as error:
            raise ResumeError("RESUME_ARTIFACT_MISMATCH", str(error)) from error
    if state.get("path_disposition_noops") and result.get("stage_delta_ledger") != state.get("stage_delta_ledger"):
        raise ResumeError("RESUME_ARTIFACT_MISMATCH", "metadata no-op observation ledgers disagree")
    if root is not None and source_entry.root != root.resolve():
        raise ResumeError("RESUME_PROJECT_MISMATCH", "source repository root differs")
    recorded_manifest = state.get("candidate_manifest")
    if recorded_manifest is not None:
        try:
            gitstate_module.validate_candidate_manifest(recorded_manifest)
        except gitstate_module.GitStateError as error:
            raise ResumeError(
                "RESUME_ARTIFACT_MISMATCH",
                f"source candidate manifest is invalid: {error.detail}",
            ) from error
    if state.get("resume_safety") == "fresh_run_required" or (
        isinstance(state.get("blocking_reason"), dict)
        and state["blocking_reason"].get("code") == "WORKER_TERMINATED_BEFORE_RESULT"
    ):
        raise ResumeError(
            "WORKER_TERMINATED_BEFORE_RESULT",
            "source run terminated before result with uncertain cleanup; fresh run required",
        )

    from .worker_recovery import verify_retained_cleanup

    try:
        verify_retained_cleanup(source, state)
    except ValueError as error:
        raise ResumeError("WORKER_CLEANUP_FAILED", str(error)) from error
    completed = completed_prefix(state, resolved, source)
    validate_bindings(source, state, completed)
    from .resume import _terminal_result
    try:
        outcomes.validate_terminal(state, _terminal_result(source, state, completed, lifecycle))
    except ValueError as error:
        raise ResumeError("RESUME_ARTIFACT_MISMATCH", str(error)) from error
    return source, state, result, resolved, source_entry, completed
