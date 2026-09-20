"""Validated, immutable evidence for same-phase dispatcher resume."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Protocol

from . import candidate as candidate_module
from . import gitstate as gitstate_module
from . import plan_material as plan_material_module
from . import result as result_module
from .lifecycle import LIFECYCLE_STANDARD, LifecycleSpec, get_lifecycle
from .request import PhaseRequest
from .resume_validation import ResumeError, load_core, sha256


from .route_provenance import (
    RESOLVED_V5 as RESOLVED_V5,
    RESOLVED_V6 as RESOLVED_V6,
    RESOLVED_V4,
    ROSTER_COMPATIBILITY_FINALIZATION,
    ROSTER_COMPATIBILITY_INHERITED,
    build_route_transition,
    compose_effective_stage_routes,
    validate_current_resolution,
    validate_resolved_schema,
)


SCHEMA = "agent-phase-resume-v1"
_STANDARD = get_lifecycle(LIFECYCLE_STANDARD)
STAGES = _STANDARD.stage_names
PREFIXES = _STANDARD.prefixes
CHECKPOINTS = _STANDARD.checkpoint_by_stage
CLI_STAGES = _STANDARD.valid_resume_aliases
@dataclass(frozen=True)
class ResumePlan:
    source: Path
    source_state: dict[str, Any]
    source_result: dict[str, Any]
    source_resolved: dict[str, Any]
    source_entry: gitstate_module.EntryState
    requested_from_stage: str
    from_stage: str
    reason: dict[str, Any]
    inherited_stages: tuple[str, ...]
    invalidated_stages: tuple[str, ...]
    inherited_checkpoints: tuple[str, ...]
    inherited_artifacts: tuple[dict[str, Any], ...]
    closeout_result: result_module.StageResult | None
    failed_stage_context: bytes | None
    current_entry: gitstate_module.EntryState
    current_head: str
    current_tree: str
    candidate_manifest: dict[str, Any]
    boundary_facts: dict[str, Any]
    evidence_boundary_skew: bool
    source_hashes: dict[str, str]
    source_archive: dict[str, Any] | None
    lifecycle: LifecycleSpec
    roster_compatibility: str
    effective_stage_routes: dict[str, Any] = field(default_factory=dict)
    route_transition: dict[str, Any] | None = None
    recovered_outputs: dict[str, bytes] = field(default_factory=dict)
    output_recovery: dict[str, Any] | None = None
    recovered_candidate: dict[str, Any] | None = None

    @property
    def performed_stages(self) -> tuple[str, ...]:
        if self.from_stage == "finalize":
            return ()
        stages = self.lifecycle.stage_names
        return stages[stages.index(self.from_stage):]


class InheritedPlan(Protocol):
    source: Path
    source_state: dict[str, Any]
    inherited_artifacts: tuple[dict[str, Any], ...]


def _terminal_result(
    source: Path,
    state: dict[str, Any],
    completed: tuple[str, ...],
    lifecycle: LifecycleSpec,
) -> result_module.StageResult | None:
    terminal = lifecycle.terminal_result_stage
    transported = state.get("stage_transports_completed")
    transport_completed = (
        isinstance(transported, list) and terminal in transported
    )
    if terminal not in completed and not transport_completed:
        return None
    prefix = lifecycle.prefixes[terminal]
    prompt = (source / f"{prefix}.prompt.md").read_text(encoding="utf-8")
    nonces = re.findall(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
    if len(set(nonces)) != 1:
        raise ResumeError("RESUME_ARTIFACT_MISMATCH", "terminal prompt nonce is ambiguous")
    try:
        return result_module.parse(
            (source / f"{prefix}.stdout.md").read_bytes(), terminal, nonces[0]
        )
    except result_module.ResultError:
        return None


def _safe_stage(
    completed: tuple[str, ...], parsed: result_module.StageResult | None,
    lifecycle: LifecycleSpec,
) -> str:
    stages = lifecycle.stage_names
    if (
        parsed is not None
        and parsed.completed
        and completed == stages[:-1]
    ):
        # A corrected-accounting source may have returned a successful
        # terminal transport whose result only became strictly parseable after
        # a parser correction.  Parsing it here is the semantic validation;
        # finalization may therefore inherit the now-complete terminal stage
        # without another provider invocation.
        return "finalize"
    if len(completed) < len(stages):
        return stages[len(completed)]
    return (
        "finalize"
        if parsed is not None and parsed.completed
        else lifecycle.terminal_result_stage
    )


def artifact_records(
    source: Path, inherited: tuple[str, ...], lifecycle: LifecycleSpec
) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for stage in inherited:
        prefix = lifecycle.prefixes[stage]
        for suffix in ("prompt.md", "stdout.md", "stderr.log", "meta.json"):
            name = f"{prefix}.{suffix}"
            path = source / name
            records.append({"stage": stage, "name": name, "sha256": sha256(path)})
        if stage == lifecycle.stage_names[0]:
            binding = None
            try:
                binding = json.loads((source / "state.json").read_text(
                    encoding="utf-8"
                )).get("plan_candidate")
            except (OSError, UnicodeError, json.JSONDecodeError):
                binding = None
            if (
                isinstance(binding, dict)
                and binding.get("schema") == "agent-phase-plan-material-v1"
                and binding.get("relative_path")
                == plan_material_module.CANONICAL_PATH
            ):
                name = plan_material_module.CANONICAL_PATH
                path = source / name
                if path.is_file():
                    records.append({
                        "stage": stage, "name": name, "sha256": sha256(path)
                    })
        drain_path = source / f"{prefix}.worker-drain.json"
        if drain_path.is_file():
            records.append({"stage": stage, "name": drain_path.name, "sha256": sha256(drain_path)})
        meta = json.loads((source / f"{prefix}.meta.json").read_text(encoding="utf-8"))
        evidence = meta.get("antigravity_evidence")
        if isinstance(evidence, dict) and evidence.get("validation") == "validated":
            names = [evidence["summary"]["relative_path"]]
            if evidence.get("raw") is not None:
                names.append(evidence["raw"]["relative_path"])
            for name in names:
                if (
                    not isinstance(name, str)
                    or not name
                    or name in {".", ".."}
                    or Path(name).name != name
                    or "\x00" in name
                ):
                    raise ResumeError(
                        "RESUME_ARTIFACT_MISMATCH",
                        "inherited provider evidence path is not a safe basename",
                    )
                path = source / name
                records.append({"stage": stage, "name": name, "sha256": sha256(path)})
        result_path = source / f"{prefix}.result.json"
        if result_path.is_file() and lifecycle.stage(stage).role == "reviewer":
            from .review_recovery import validate_recovery

            records.extend(validate_recovery(source, lifecycle.stage(stage), json.loads(result_path.read_bytes())))
        if result_path.is_file():
            records.append({
                "stage": stage, "name": result_path.name, "sha256": sha256(result_path)
            })
    return tuple(records)


def _resolved_schema(resolved: dict[str, Any]) -> str:
    schema = resolved.get("schema")
    return validate_resolved_schema(schema)


def _candidate_tree_for_inherited_prefix(
    state: dict[str, Any],
    lifecycle: LifecycleSpec,
    chosen: str,
    source_entry: gitstate_module.EntryState,
) -> str:
    """Find the last candidate actually inherited by the chosen suffix."""
    if chosen == "finalize":
        terminal = state.get("terminal_candidate")
        if isinstance(terminal, dict) and isinstance(terminal.get("tree"), str):
            return terminal["tree"]
        terminal_spec = lifecycle.stage(lifecycle.terminal_result_stage)
        candidate = state.get(terminal_spec.candidate_key or "")
        if isinstance(candidate, dict) and isinstance(candidate.get("tree"), str):
            return candidate["tree"]

    # A mutating stage can fail after writing candidate bytes but before it is
    # added to the completed semantic prefix.  Resuming that exact failed
    # stage inherits the recorded surviving candidate and therefore must bind
    # its paths before the new provider is allowed to run.
    failure = state.get("failure_candidate")
    if (
        isinstance(failure, dict)
        and failure.get("stage") == chosen
        and isinstance(failure.get("tree"), str)
    ):
        return failure["tree"]

    chosen_index = lifecycle.stage_names.index(chosen)
    for stage in reversed(lifecycle.stages[:chosen_index]):
        if stage.candidate_key is None:
            continue
        candidate = state.get(stage.candidate_key)
        if isinstance(candidate, dict) and isinstance(candidate.get("tree"), str):
            return candidate["tree"]
    return source_entry.tree


def _inherited_candidate_manifest(
    source: Path,
    state: dict[str, Any],
    lifecycle: LifecycleSpec,
    chosen: str,
    source_entry: gitstate_module.EntryState,
) -> tuple[dict[str, Any], str]:
    """Load or derive the closed manifest for the prefix being inherited."""
    candidate_tree = _candidate_tree_for_inherited_prefix(
        state, lifecycle, chosen, source_entry
    )
    try:
        recorded = state.get("candidate_manifest")
        from . import ownership_challenge
        try:
            ownership_challenge.validate(source_entry.root, state)
        except ValueError as error:
            raise ResumeError('RESUME_ARTIFACT_MISMATCH', str(error)) from error
        if chosen == 'finalize' and ownership_challenge.open_records(state):
            raise ResumeError('OWNERSHIP_CHALLENGE_OPEN', 'open challenges require the exact manager-resolution lane')
        ownership = state.get("path_ownership")
        if ownership is not None:
            from .path_disposition import normalize, validate_evidence
            from .result import ResultError
            try:
                validate_evidence(source_entry.root, ownership, state)
                if ownership["raw_tree"] != (state.get("raw_terminal_candidate") or {}).get("tree") or ownership["publication_tree"] != (state.get("publication_candidate") or {}).get("tree"):
                    raise ResumeError("RESUME_ARTIFACT_MISMATCH", "ownership candidate identities disagree")
                if state.get("path_dispositions") != ownership["dispositions"]:
                    raise ResumeError("RESUME_ARTIFACT_MISMATCH", "ownership dispositions disagree")
                if state.get("path_disposition_noops", []) != ownership.get("path_disposition_noops", []):
                    raise ResumeError("RESUME_ARTIFACT_MISMATCH", "metadata no-op dispositions disagree")
                candidate_tree = normalize(
                    source_entry.root, ownership["entry_tree"], candidate_tree,
                    ownership["dispositions"],
                )
            except (ResultError, candidate_module.CandidateError) as error:
                raise ResumeError("RESUME_ARTIFACT_MISMATCH", str(error)) from error
        explicit_paths = None
        if state.get("adoption"):
            from . import adoption
            # Replaying an earlier prefix still carries explicitly adopted
            # starting objects, even when unchanged relative to this entry.
            explicit_paths = sorted(adoption.paths(state) | {
                c.path for c in gitstate_module.phase_delta(
                    source_entry.root, source_entry.tree, candidate_tree)})
        if isinstance(recorded, dict) and state.get("candidate_manifest_derivation") == "mechanical_failure_boundary" and recorded.get("candidate_tree") == candidate_tree:
            gitstate_module.validate_candidate_manifest(recorded)
            explicit_paths = recorded["paths"]
        if ownership is not None and isinstance(recorded, dict) and recorded.get("candidate_tree") == candidate_tree:
            explicit_paths = recorded["paths"]
            if set(explicit_paths) & {item['path'] for item in ownership['dispositions'] if item['disposition'] != 'phase_owned'}:
                raise ResumeError("RESUME_ARTIFACT_MISMATCH", "excluded path appears in publication manifest")
        manifest = gitstate_module.candidate_manifest(
            source_entry.root, (ownership or {}).get("entry_tree", source_entry.tree),
            candidate_tree, paths=explicit_paths,
        )
        if isinstance(recorded, dict):
            # A completed source may have a manifest for its terminal
            # candidate. It is authoritative only when this resume inherits
            # that same candidate; an earlier replay derives its own prefix
            # manifest from the recorded Git trees.
            if recorded.get("candidate_tree") == candidate_tree:
                gitstate_module.validate_candidate_manifest(recorded)
                if recorded != manifest:
                    raise ResumeError(
                        "RESUME_ARTIFACT_MISMATCH",
                        "recorded candidate manifest disagrees with Git trees",
                    )
                manifest = recorded
        return manifest, candidate_tree
    except gitstate_module.GitStateError as error:
        raise ResumeError(
            "RESUME_ARTIFACT_MISMATCH",
            f"candidate manifest is unavailable: {error.detail}",
        ) from error


def _boundary_facts(
    source_entry: gitstate_module.EntryState,
    current_entry: gitstate_module.EntryState,
    candidate_tree: str,
    manifest: dict[str, Any],
    root: Path,
) -> tuple[dict[str, Any], bool]:
    """Describe allowed resume skew without making it an identity gate."""
    candidate_paths = sorted(manifest["paths"])
    try:
        unrelated = [
            change.path
            for change in gitstate_module.phase_delta(root, candidate_tree, current_entry.tree)
            if change.path not in candidate_paths
        ]
    except gitstate_module.GitStateError as error:
        raise ResumeError(
            "RESUME_ARTIFACT_MISMATCH",
            f"cannot classify resume boundary changes: {error.detail}",
        ) from error
    skew = (
        source_entry.head != current_entry.head
        or source_entry.tree != current_entry.tree
        or bool(unrelated)
    )
    facts = {
        "schema": "agent-phase-resume-boundary-v1",
        "source_entry_head": source_entry.head,
        "source_entry_tree": source_entry.tree,
        "current_boundary_head": current_entry.head,
        "current_boundary_tree": current_entry.tree,
        "inherited_candidate_tree": candidate_tree,
        "candidate_paths": candidate_paths,
        "unrelated_paths": sorted(set(unrelated)),
        "skew": skew,
    }
    return facts, skew


def preflight(
    source_path: Path,
    requested_from_stage: str,
    phase_id: str,
    request: PhaseRequest,
    root: Path,
    project: str,
    current_resolved: dict[str, Any] | None,
    *,
    expected_lifecycle: str | None = None,
    check_route: bool = True,
) -> ResumePlan:
    source, state, result, resolved, source_entry, completed = load_core(
        source_path, phase_id, request, root, project
    )
    if state.get("worker_cleanup_pending"):
        from .worker_recovery import verify_pending_cleanup

        try:
            verify_pending_cleanup(source, state)
        except ValueError as error:
            raise ResumeError("WORKER_CLEANUP_FAILED", str(error)) from error
    source_schema = _resolved_schema(resolved)
    lifecycle = get_lifecycle(str(state.get("lifecycle", LIFECYCLE_STANDARD)))
    if expected_lifecycle is not None and expected_lifecycle != lifecycle.name:
        raise ResumeError(
            "RESUME_LIFECYCLE_MISMATCH",
            f"requested lifecycle {expected_lifecycle} differs from {lifecycle.name}",
        )
    aliases = lifecycle.valid_resume_aliases
    if requested_from_stage not in aliases:
        raise ResumeError(
            "RESUME_STAGE_UNSATISFIED",
            f"unknown resume stage for {lifecycle.name}: {requested_from_stage}",
        )
    parsed_closeout = _terminal_result(source, state, completed, lifecycle)
    safe = _safe_stage(completed, parsed_closeout, lifecycle)
    chosen = safe if requested_from_stage == "auto" else aliases[requested_from_stage]
    order = (*lifecycle.stage_names, "finalize")
    if order.index(chosen) > order.index(safe):
        raise ResumeError(
            "RESUME_STAGE_UNSATISFIED", f"{chosen} is later than validated safe stage {safe}"
        )
    inherited = tuple(lifecycle.stage_names[: order.index(chosen)])
    invalidated = tuple(stage for stage in completed if stage not in inherited)
    checkpoint_by_stage = lifecycle.checkpoint_by_stage
    inherited_checkpoints = tuple(
        checkpoint_by_stage[s] for s in inherited if s in checkpoint_by_stage
    )
    inherited_manifest, inherited_candidate_tree = _inherited_candidate_manifest(
        source, state, lifecycle, chosen, source_entry
    )
    if source_schema == RESOLVED_V4 and "roster" in resolved:
        raise ResumeError(
            "RESUME_RESOLVED_SCHEMA_UNSUPPORTED",
            "resolved V4 source unexpectedly records roster provenance",
        )
    roster_compatibility = (
        ROSTER_COMPATIBILITY_FINALIZATION
        if chosen == "finalize"
        else ROSTER_COMPATIBILITY_INHERITED
    )
    if chosen != "finalize" and check_route:
        if current_resolved is None:
            raise ResumeError(
                "RESUME_CURRENT_ROUTE_INVALID",
                "current route evidence is unavailable",
            )
        remaining_stages = lifecycle.stage_names[
            lifecycle.stage_names.index(chosen):
        ]
        validate_current_resolution(
            current_resolved, lifecycle, remaining_stages
        )
    try:
        current_entry = gitstate_module.capture_entry(root)
    except gitstate_module.GitStateError as error:
        if error.code == "ENTRY_STAGED_CHANGES":
            raise ResumeError(
                "RESUME_STAGED_CHANGES",
                "resume requires an unstaged index",
            ) from error
        raise ResumeError(error.code, error.detail) from error
    current_head = current_entry.head
    current_tree = current_entry.tree
    from . import review_binding
    review_binding.require_resolved_resume(root, state, current_tree)
    ownership = state.get("path_ownership")
    if ownership is not None:
        excluded = [item["path"] for item in ownership["dispositions"] if item["disposition"] != "phase_owned"]
        raw_manifest = gitstate_module.candidate_manifest(
            root, ownership["entry_tree"], ownership["raw_tree"], paths=excluded,
        )
        if gitstate_module.candidate_manifest_conflicts(root, current_tree, raw_manifest):
            raise ResumeError("RESUME_CANDIDATE_CONFLICT", "inherited excluded observation changed")
    if current_entry.branch != source_entry.branch:
        raise ResumeError(
            "RESUME_BRANCH_MISMATCH",
            f"current branch {current_entry.branch} is not source branch {source_entry.branch}",
        )
    try:
        conflicts = gitstate_module.candidate_manifest_conflicts(
            root, current_tree, inherited_manifest
        )
    except gitstate_module.GitStateError as error:
        raise ResumeError(
            "RESUME_ARTIFACT_MISMATCH",
            f"candidate manifest cannot be checked: {error.detail}",
        ) from error
    if conflicts:
        raise ResumeError(
            "RESUME_CANDIDATE_CONFLICT",
            "current boundary differs from inherited candidate paths: "
            + ", ".join(conflicts),
        )
    if (chosen == "finalize" and inherited_manifest["paths"]
            and current_head != source_entry.head
            and (state.get("commit") or {}).get("sha") != current_head
            and not gitstate_module.candidate_manifest_conflicts(root, current_head, inherited_manifest)):
        raise ResumeError(
            "RESUME_MATERIALIZATION_PROOF_REQUIRED",
            "candidate objects already occur at a different HEAD; use agent-phase-finalize --run "
            "for a new materialization receipt, not implicit finalize-only equivalence",
        )
    boundary, skew = _boundary_facts(
        source_entry, current_entry, inherited_candidate_tree,
        inherited_manifest, root,
    )
    context_marker = None
    failure = state.get("failure_candidate")
    if (
        isinstance(failure, dict)
        and failure.get("stage") == chosen
        and failure.get("tree") == current_tree
        and chosen == lifecycle.terminal_result_stage
    ):
        context_marker = b"failure-context"
    blocker = state.get("blocking_reason") or {}
    if (
        chosen == lifecycle.terminal_result_stage
        and isinstance(state.get("terminal_candidate"), dict)
        and state["terminal_candidate"].get("tree") == current_tree
        and (
            str(blocker.get("code", "")).startswith("RESULT_")
            or str(blocker.get("code", "")).startswith("COMMIT_")
        )
    ):
        context_marker = b"failure-context"
    context = None
    if context_marker is not None:
        terminal_prefix = lifecycle.prefixes[lifecycle.terminal_result_stage]
        context = (source / f"{terminal_prefix}.stdout.md").read_bytes()
    core_names = ("state.json", "result.json", "request.json", "resolved.json")
    source_hashes = {name: sha256(source / name) for name in core_names}
    archive = source.parent / f"{source.name}.zip"
    archive_record = (
        {"path": os.fspath(archive), "sha256": sha256(archive)} if archive.is_file() else None
    )
    blocker = state.get("blocking_reason")
    reason = {
        "safe_stage": safe,
        "blocking_reason": blocker,
        "auto": requested_from_stage == "auto",
    }
    if chosen == "finalize":
        effective_stage_routes = compose_effective_stage_routes(
            resolved, None, lifecycle, inherited, (), state["run_id"]
        )
        route_transition = build_route_transition(
            resolved, None, lifecycle, inherited, (), is_finalization_only=True
        )
    elif check_route and current_resolved is not None:
        remaining_stages = lifecycle.stage_names[
            lifecycle.stage_names.index(chosen):
        ]
        effective_stage_routes = compose_effective_stage_routes(
            resolved, current_resolved, lifecycle, inherited, remaining_stages, state["run_id"]
        )
        route_transition = build_route_transition(
            resolved, current_resolved, lifecycle, inherited, remaining_stages
        )
    else:
        effective_stage_routes = compose_effective_stage_routes(
            resolved, current_resolved, lifecycle, inherited, (), state["run_id"]
        )
        for stage_name in lifecycle.stage_names[len(inherited):]:
            if stage_name in effective_stage_routes:
                effective_stage_routes[stage_name]["source"] = "unexecuted"
        route_transition = None
    return ResumePlan(
        source=source, source_state=state, source_result=result,
        source_resolved=resolved, source_entry=source_entry,
        requested_from_stage=requested_from_stage, from_stage=chosen, reason=reason,
        inherited_stages=inherited, invalidated_stages=invalidated,
        inherited_checkpoints=inherited_checkpoints,
        inherited_artifacts=artifact_records(source, inherited, lifecycle),
        closeout_result=parsed_closeout, failed_stage_context=context,
        current_entry=current_entry,
        current_head=current_head, current_tree=current_tree,
        candidate_manifest=inherited_manifest,
        boundary_facts=boundary,
        evidence_boundary_skew=skew,
        source_hashes=source_hashes, source_archive=archive_record,
        lifecycle=lifecycle, roster_compatibility=roster_compatibility,
        effective_stage_routes=effective_stage_routes,
        route_transition=route_transition,
    )


def copy_inherited(plan: InheritedPlan, target: Path) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for record in plan.inherited_artifacts:
        source = plan.source / record["name"]
        destination = target / record["name"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if record["name"].endswith(
            (".antigravity-terminal-result.json", ".antigravity-terminal-result.raw.json")
        ):
            destination.chmod(0o600)
        destination_hash = sha256(destination)
        if destination_hash != record["sha256"]:
            raise ResumeError("RESUME_ARTIFACT_MISMATCH", f"copy drifted: {record['name']}")
        copied.append({**record, "source_run_id": plan.source_state["run_id"],
                       "destination_sha256": destination_hash})
    inherited = target / "inherited"
    inherited.mkdir(mode=0o700)
    for source_name, destination_name in (
        ("state.json", "source-state.json"),
        ("result.json", "source-result.json"),
        ("request.json", "source-request.json"),
        ("resolved.json", "source-resolved.json"),
    ):
        shutil.copyfile(plan.source / source_name, inherited / destination_name)
    return copied


def provenance(plan: ResumePlan, copied: list[dict[str, Any]]) -> dict[str, Any]:
    from .resume_validation import require_source

    excluded: list[dict[str, str]] = []
    require_source(plan.source, excluded)
    failure = plan.source_state.get("failure_candidate")
    record = {
        "schema": SCHEMA,
        "source_run_id": plan.source_state["run_id"],
        "source": {"kind": "directory", "path": os.fspath(plan.source),
                   "archive": plan.source_archive},
        "source_hashes": plan.source_hashes,
        "excluded_source_paths": excluded,
        "requested_from_stage": plan.requested_from_stage,
        "effective_from_stage": plan.from_stage,
        "reason": plan.reason,
        "inherited_stages": list(plan.inherited_stages),
        "invalidated_stages": list(plan.invalidated_stages),
        "inherited_checkpoints": list(plan.inherited_checkpoints),
        "provider_invocations_inherited": len(plan.inherited_stages),
        "provider_invocations_performed": 0,
        "source_entry_head": plan.source_entry.head,
        "source_entry_tree": plan.source_entry.tree,
        "resume_start_head": plan.current_head,
        "resume_start_tree": plan.current_tree,
        "candidate_manifest": plan.candidate_manifest,
        "adoption": plan.source_state.get("adoption"),
        "resume_boundary": plan.boundary_facts,
        "evidence_boundary_skew": plan.evidence_boundary_skew,
        "failure_candidate": failure,
        "terminal_replayed": plan.from_stage == plan.lifecycle.terminal_result_stage,
        "closeout_replayed": plan.from_stage == "closeout",
        "lifecycle": plan.lifecycle.name,
        "finalization_replayed": plan.from_stage == "finalize",
        "roster_compatibility": plan.roster_compatibility,
        "effective_stage_routes": plan.effective_stage_routes,
        "route_transition": plan.route_transition,
        "inherited_artifacts": copied,
    }
    if plan.output_recovery is not None:
        record["antigravity_output_recovery"] = plan.output_recovery
    return record
