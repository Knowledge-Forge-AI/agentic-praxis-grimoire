"""Exact recovery of one successful Antigravity response lost to capture policy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import antigravity_evidence as evidence_module
from . import candidate as candidate_module
from . import finalization as finalization_module
from . import gitstate as gitstate_module
from . import result_repair as result_repair_module
from . import resume as resume_module
from . import resume_validation as validation_module
from .provider import MAX_STAGE_OUTPUT_BYTES
from .routing import PROVIDER_ANTIGRAVITY, RoutingError, antigravity_intelligence


SCHEMA = "agent-phase-antigravity-output-recovery-v1"
ARTIFACT = "01-produce.recovered-complete.stdout.md"
RECORD = "antigravity-output-recovery.json"
BLOCKER = "PROVIDER_OUTPUT_LIMIT"
CODE = "ANTIGRAVITY_OUTPUT_RECOVERY_INELIGIBLE"


def _reject(detail: str) -> None:
    raise validation_module.ResumeError(CODE, detail)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_bytes(value: bytes) -> str:
    """Return a stable digest for recovery records and prompt decisions."""
    return _sha256_bytes(value)


def _stage_route(resolved: dict[str, Any], stage: str) -> dict[str, Any]:
    stages = resolved.get("stages")
    if not isinstance(stages, dict):
        _reject("source resolved stage inventory is not an object")
    route = stages.get(stage)
    if not isinstance(route, dict):
        _reject(f"source route is unavailable for {stage}")
    return route


def _validate_resolved_identity(
    state: dict[str, Any], resolved: dict[str, Any], lifecycle: Any
) -> None:
    expected = {
        "expected_stages": list(lifecycle.stage_names),
        "expected_provider_invocations": lifecycle.expected_provider_invocations,
        "expected_review_count": lifecycle.expected_review_count,
        "terminal_result_stage": lifecycle.terminal_result_stage,
    }
    for key, value in expected.items():
        if state.get(key) != value or resolved.get(key) != value:
            _reject(f"source {key} disagrees with the lifecycle contract")
    if (
        resolved.get("checkpoints") != list(lifecycle.checkpoints)
        or resolved.get("checkpoint_count") != lifecycle.expected_review_count
        or resolved.get("provider_invocations")
        != lifecycle.expected_provider_invocations
        or resolved.get("finalization_policy")
        != state.get("finalization_policy")
        or resolved.get("provider_local_workers_count_as_invocations") is not False
        or resolved.get("provider_local_workers_count_as_reviews") is not False
    ):
        _reject("source resolved lifecycle accounting is inconsistent")
    stages = resolved.get("stages")
    if not isinstance(stages, dict) or set(stages) != set(lifecycle.stage_names):
        _reject("source resolved stage inventory disagrees with the lifecycle")


def qualify(
    dispatcher: Any,
    phase_id: str,
    request: Any,
    source_path: Path,
    requested_from_stage: str,
    root: Path,
    project: str,
) -> resume_module.ResumePlan | None:
    """Validate a narrow output-limit source and recover its exact response."""
    source, state, result, resolved, source_entry, completed = (
        validation_module.load_core(
            source_path, phase_id, request, root, project
        )
    )
    blocker = state.get("blocking_reason")
    if not isinstance(blocker, dict) or blocker.get("code") != BLOCKER:
        return None
    for key in (
        "blocking_reason",
        "complete",
        "outcome",
        "expected_stages",
        "expected_provider_invocations",
        "expected_review_count",
        "terminal_result_stage",
        "stages_invoked",
        "stage_transports_completed",
        "stages_completed",
        "failure_candidate",
        "phase_delta",
        "phase_owned_paths",
        "manager_disposition_required",
        "provider_evidence",
        "archive",
    ):
        if result.get(key) != state.get(key):
            raise validation_module.ResumeError(
                "RESUME_ARTIFACT_MISMATCH",
                f"source result and state disagree on {key}",
            )
    lifecycle = resume_module.get_lifecycle(str(state.get("lifecycle", "")))
    if lifecycle.name != "work-reviewed":
        _reject("only work-reviewed Antigravity producer recovery is supported")
    source_schema = resume_module._resolved_schema(resolved)
    if source_schema not in (resume_module.RESOLVED_V5, resume_module.RESOLVED_V6):
        _reject("output recovery requires resolved V5 or V6 roster provenance")
    _validate_resolved_identity(state, resolved, lifecycle)
    aliases = lifecycle.valid_resume_aliases
    if (
        requested_from_stage != "auto"
        and (
            requested_from_stage not in aliases
            or aliases[requested_from_stage] != "work_review"
        )
    ):
        _reject("recovery must continue exactly from work_review")
    produce = lifecycle.stages[0]
    if (
        completed
        or produce.name != "produce"
        or not produce.is_mutating
        or state.get("stages_invoked") != [produce.name]
        or state.get("stage_transports_completed") not in ([], None)
    ):
        _reject("source stage accounting is not one failed nonterminal producer")

    try:
        archive = result_repair_module._verify_source_archive(source)
        source_manifest = result_repair_module._source_manifest(source)
    except (
        OSError,
        finalization_module.FinalizationError,
        validation_module.ResumeError,
    ) as error:
        _reject(f"source run and sibling archive do not cross-verify: {error}")
    try:
        result_repair_module._require_source_state(source, state, archive)
    except validation_module.ResumeError as error:
        _reject(f"source archive record does not bind the verified sibling ZIP: {error.detail}")
    prefix = produce.prefix
    meta_path = source / f"{prefix}.meta.json"
    try:
        meta_bytes = meta_path.read_bytes()
        meta = validation_module.load_json(source, f"{prefix}.meta.json")
        prompt = (source / f"{prefix}.prompt.md").read_bytes()
        captured = (source / f"{prefix}.stdout.md").read_bytes()
    except (OSError, validation_module.ResumeError) as error:
        _reject(f"producer stage artifacts are unavailable: {error}")
    if (
        meta.get("stage") != produce.name
        or meta.get("role") != produce.role
        or meta.get("provider") != PROVIDER_ANTIGRAVITY
        or meta.get("exit_code") != 0
        or meta.get("truncated") is not True
        or meta.get("prompt_bytes") != len(prompt)
        or meta.get("prompt_sha256") != _sha256_bytes(prompt)
        or meta.get("stdout_bytes") != len(captured)
        or meta.get("stdout_sha256") != _sha256_bytes(captured)
    ):
        _reject("producer meta does not bind the truncated successful transport")

    route = _stage_route(resolved, produce.name)
    profile = meta.get("profile")
    posture = route.get("process_posture")
    intelligence = route.get("intelligence")
    if (
        not isinstance(profile, str)
        or not isinstance(posture, dict)
        or not isinstance(intelligence, dict)
        or route.get("provider") != PROVIDER_ANTIGRAVITY
        or route.get("profile") != profile
        or route.get("role") != produce.role
        or route.get("artifact_prefix") != produce.prefix
        or route.get("candidate_binding_key") != produce.candidate_key
        or route.get("candidate_mutation") is not True
        or route.get("process_read_only") is not False
        or posture.get("mode") != "mutation-capable"
    ):
        _reject("producer route and stage meta disagree")
    try:
        model = antigravity_intelligence(dispatcher.root, profile)["model"]
    except RoutingError as error:
        _reject(f"producer profile intelligence is unavailable: {error}")
    if intelligence.get("model") != model:
        _reject("producer route intelligence disagrees with its profile")
    try:
        validated = evidence_module.validate(
            source, prefix, profile, model, False, 0
        )
    except evidence_module.EvidenceError as error:
        _reject(f"Antigravity evidence is invalid: {error}")
    if meta.get("antigravity_evidence") != validated:
        _reject("stage meta does not exactly bind validated Antigravity evidence")
    if (
        validated.get("wrapper_exit_code") != 0
        or validated.get("child_exit_code") != 0
        or validated.get("provider_status") != "success"
        or validated.get("transport_success") is not True
        or validated.get("completion_fence_observed") is not True
        or validated.get("terminal_record_kind") != "exact_raw_event"
        or validated.get("response_source") != "result.response"
    ):
        _reject("terminal evidence does not prove exact successful response recovery")
    raw_record = validated.get("raw")
    if not isinstance(raw_record, dict):
        _reject("exact raw terminal evidence is unavailable")
    raw_path = source / str(raw_record.get("relative_path", ""))
    try:
        raw_event = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        _reject(f"raw terminal event is unreadable: {error}")
    nested = raw_event.get("result") if isinstance(raw_event, dict) else None
    if not isinstance(nested, dict) or not isinstance(nested.get("response"), str):
        _reject("response is not the authenticated nested result.response field")
    try:
        response = nested["response"].encode("utf-8")
    except UnicodeEncodeError as error:
        _reject(f"complete response is not valid UTF-8: {error}")
    if (
        not response
        or len(response) > MAX_STAGE_OUTPUT_BYTES
        or validated.get("provider_raw_status") != nested.get("status")
        or not response.startswith(captured)
    ):
        _reject("complete response is oversized, non-success, or not prefix-bound")

    failure = state.get("failure_candidate")
    if (
        not isinstance(failure, dict)
        or failure.get("stage") != produce.name
        or not isinstance(failure.get("tree"), str)
        or not isinstance(failure.get("head"), str)
        or failure.get("head") != source_entry.head
        or not isinstance(failure.get("paths"), list)
        or not failure["paths"]
        or any(not isinstance(path, str) for path in failure["paths"])
        or len(set(failure["paths"])) != len(failure["paths"])
    ):
        _reject("source failure candidate identity is unavailable")
    try:
        mechanical_paths = {
            change.path
            for change in gitstate_module.phase_delta(
                root, source_entry.tree, failure["tree"]
            )
        }
        if mechanical_paths != set(failure["paths"]):
            _reject("failure candidate path inventory is not the exact tree delta")
        from . import adoption
        adoption.guard_boundary(state, root, failure["tree"])
        manifest = gitstate_module.candidate_manifest(
            root,
            source_entry.tree,
            failure["tree"],
            paths=sorted(set(failure["paths"]) | adoption.paths(state)),
        )
        current_entry = gitstate_module.capture_entry(root)
        if current_entry.branch != source_entry.branch:
            _reject("live candidate is not on the source branch")
        if not gitstate_module.is_ancestor(
            root, source_entry.head, current_entry.head
        ):
            _reject("source entry HEAD is not an ancestor of the live boundary")
        conflicts = gitstate_module.candidate_manifest_conflicts(
            root, current_entry.tree, manifest
        )
    except (candidate_module.CandidateError, gitstate_module.GitStateError) as error:
        raise validation_module.ResumeError(
            getattr(error, "code", CODE), str(error)
        ) from error
    if conflicts:
        raise validation_module.ResumeError(
            "RESUME_CANDIDATE_CONFLICT",
            "live candidate differs from recovered paths: " + ", ".join(conflicts),
        )
    current_candidate = candidate_module.tree_identity(root)
    boundary, skew = resume_module._boundary_facts(
        source_entry,
        current_entry,
        str(failure["tree"]),
        manifest,
        root,
    )
    source_hashes = {
        name: validation_module.sha256(source / name)
        for name in ("state.json", "result.json", "request.json", "resolved.json")
    }
    response_record = {
        "schema": SCHEMA,
        "source_run_id": state["run_id"],
        "stage": produce.name,
        "provider": PROVIDER_ANTIGRAVITY,
        "profile": profile,
        "model": model,
        "blocking_code": BLOCKER,
        "wrapper_exit_code": 0,
        "child_exit_code": 0,
        "normalized_status": "success",
        "transport_success": True,
        "completion_fence_observed": True,
        "terminal_record_kind": "exact_raw_event",
        "response_source": "result.response",
        "response_bytes": len(response),
        "response_sha256": _sha256_bytes(response),
        "captured_prefix_bytes": len(captured),
        "captured_prefix_sha256": _sha256_bytes(captured),
        "captured_stdout_is_exact_prefix": True,
        "global_stage_output_limit_bytes": MAX_STAGE_OUTPUT_BYTES,
        "candidate_tree": failure["tree"],
        "failure_head": failure["head"],
        "live_candidate_tree": current_candidate["tree"],
        "candidate_manifest": manifest,
        "prompt_artifact": {
            "basename": f"{prefix}.prompt.md",
            "bytes": len(prompt),
            "sha256": _sha256_bytes(prompt),
        },
        "captured_stdout_artifact": {
            "basename": f"{prefix}.stdout.md",
            "bytes": len(captured),
            "sha256": _sha256_bytes(captured),
        },
        "stage_meta_artifact": {
            "basename": meta_path.name,
            "bytes": len(meta_bytes),
            "sha256": _sha256_bytes(meta_bytes),
        },
        "evidence_summary_artifact": validated["summary"],
        "evidence_raw_artifact": validated["raw"],
        "source_directory_file_count": source_manifest["file_count"],
        "source_directory_files": source_manifest["files"],
        "source_archive": archive,
        "recovered_artifact": ARTIFACT,
        "semantic_completion": "recovered",
        "transport_completion": "recovered",
        "provider_invocation_performed": False,
    }
    return resume_module.ResumePlan(
        source=source,
        source_state=state,
        source_result=result,
        source_resolved=resolved,
        source_entry=source_entry,
        requested_from_stage=requested_from_stage,
        from_stage="work_review",
        reason={
            "safe_stage": "work_review",
            "blocking_reason": blocker,
            "recovery": SCHEMA,
        },
        inherited_stages=(produce.name,),
        invalidated_stages=(),
        inherited_checkpoints=(),
        inherited_artifacts=resume_module.artifact_records(
            source, (produce.name,), lifecycle
        ),
        closeout_result=None,
        failed_stage_context=None,
        current_entry=current_entry,
        current_head=current_entry.head,
        current_tree=current_entry.tree,
        candidate_manifest=manifest,
        boundary_facts=boundary,
        evidence_boundary_skew=skew,
        source_hashes=source_hashes,
        source_archive=archive,
        lifecycle=lifecycle,
        roster_compatibility="inherited_prefix_current_suffix",
        effective_stage_routes={},
        route_transition=None,
        recovered_outputs={produce.name: response},
        output_recovery=response_record,
        recovered_candidate=current_candidate,
    )


def verify_remaining_route(
    plan: resume_module.ResumePlan, current_resolved: dict[str, Any]
) -> None:
    if plan.output_recovery is None:
        return
    from .route_provenance import validate_current_resolution
    remaining = tuple(plan.lifecycle.stage_names[1:])
    validate_current_resolution(current_resolved, plan.lifecycle, remaining)


def verify_live_candidate(plan: resume_module.ResumePlan, root: Path) -> None:
    if plan.output_recovery is None:
        return
    try:
        current = gitstate_module.capture_entry(root)
        if not gitstate_module.is_ancestor(
            root, plan.source_entry.head, current.head
        ):
            _reject("source entry HEAD is no longer an ancestor")
        conflicts = gitstate_module.candidate_manifest_conflicts(
            root, current.tree, plan.candidate_manifest
        )
    except (
        candidate_module.CandidateError,
        gitstate_module.GitStateError,
    ) as error:
        code = (
            "RESUME_STAGED_CHANGES"
            if getattr(error, "code", "") == "ENTRY_STAGED_CHANGES"
            else getattr(error, "code", CODE)
        )
        raise validation_module.ResumeError(code, str(error)) from error
    if current.branch != plan.source_entry.branch:
        _reject("live candidate changed branches before reviewer invocation")
    if conflicts:
        raise validation_module.ResumeError(
            "RESUME_CANDIDATE_CONFLICT",
            "live candidate drifted before reviewer invocation: "
            + ", ".join(conflicts),
        )


def materialize(plan: resume_module.ResumePlan, directory: Any) -> None:
    if plan.output_recovery is None:
        return
    verify_source_unchanged(plan)
    response = plan.recovered_outputs["produce"]
    directory.write_bytes(ARTIFACT, response)
    record = {
        **plan.output_recovery,
        "recovered_artifact_sha256": _sha256_bytes(response),
        "recovered_artifact_bytes": len(response),
    }
    directory.write_json(RECORD, record)
    plan.output_recovery.update(record)


def verify_source_unchanged(plan: resume_module.ResumePlan) -> None:
    if plan.output_recovery is None:
        return
    try:
        observed = result_repair_module._source_manifest(plan.source)
    except (
        OSError,
        finalization_module.FinalizationError,
        validation_module.ResumeError,
    ) as error:
        raise validation_module.ResumeError(
            "RESUME_ARTIFACT_MISMATCH",
            f"source run or sibling archive became unreadable: {error}",
        ) from error
    if (
        observed["files"] != plan.output_recovery["source_directory_files"]
        or observed["archive_sha256"]
        != plan.output_recovery["source_archive"]["sha256"]
    ):
        raise validation_module.ResumeError(
            "RESUME_ARTIFACT_MISMATCH",
            "source run or sibling archive changed during output recovery",
        )
