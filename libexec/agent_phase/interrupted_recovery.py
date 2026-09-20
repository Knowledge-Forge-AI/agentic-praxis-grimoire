"""Mechanical recovery for a run whose process vanished before its result.

A dispatcher killed during a stage leaves ``state.json`` and the closed stage
prefix but never writes the aggregate ``result.json``. Recovery materializes
that missing aggregate through the maintained result owner, records that it
did so, and claims nothing about the interrupted stage: the run stays
incomplete with no semantic outcome. Every write is atomic and deterministic,
and a retry after a crash at any write point rolls forward to the same bytes.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from . import gitstate as gitstate_module
from . import run as run_module
from .lifecycle import LIFECYCLE_STANDARD, LifecycleSpec, get_lifecycle
from .request import RequestError, parse_request
from .resume_validation import (
    ResumeError,
    completed_prefix,
    entry,
    load_json,
    require_same_request,
    require_source,
    sha256,
    validate_bindings,
)

SCHEMA = "agent-phase-interrupted-recovery-v1"
RECEIPT = "interrupted-recovery.json"
SOURCE_STATE_COPY = "interrupted-recovery.source-state.json"
BLOCKING_CODE = "RUN_INTERRUPTED_BEFORE_RESULT"
RECORD_FIELDS = frozenset({
    "schema", "receipt", "receipt_sha256", "source_state_copy",
    "source_state_sha256", "result_sha256", "completed_stages",
    "interrupted_stage", "semantic_completion_claimed",
})
# Recovery may add its record, a mechanical blocker and the result owner's
# normalized views. It may never change the retained lifecycle facts.
PRESERVED_KEYS = (
    "run_id", "run_layout", "run_directory", "project", "phase_id", "phase_type",
    "execution_mode", "lifecycle", "finalization_policy", "entry",
    "controller_generation", "complete", "outcome", "semantic_outcome", "commit",
    "finalization_attempted", "stages_completed", "stages_invoked",
    "checkpoints_completed", "review_outcomes", "review_recoveries",
    "terminal_result_validated", "worker_cleanup_pending", "failure_candidate",
    "candidate_manifest", "path_ownership", "ownership_challenges", "adoption", "entry_adoption", "entry_dirt_identities",
    "provider_launch_contract", "provider_launches",
)


def _refuse(detail: str) -> None:
    raise ResumeError("RESUME_RECOVERY_REFUSED", detail)


def _mismatch(detail: str) -> None:
    raise ResumeError("RESUME_ARTIFACT_MISMATCH", f"interrupted recovery: {detail}")


def _encode(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


class _SourceDirectory:
    """The result owner's directory surface without controller re-stamping."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def write_bytes(self, name: str, data: bytes) -> Path:
        target = self.path / name
        temporary = self.path / f".{name}.recovery.tmp"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return target

    def write_text(self, name: str, text: str) -> Path:
        return self.write_bytes(name, text.encode("utf-8"))

    def write_json(self, name: str, payload: Any) -> Path:
        return self.write_bytes(name, _encode(payload))


def _regular_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        _mismatch(f"{path.name} is not an exact regular file")
    return path.read_bytes()


def _pre_state(source: Path) -> tuple[dict[str, Any], bytes]:
    """Return the retained pre-recovery state, bound to any existing receipt."""
    copy_path = source / SOURCE_STATE_COPY
    raw = _regular_bytes(copy_path if copy_path.exists() else source / "state.json")
    receipt_path = source / RECEIPT
    if receipt_path.exists():
        receipt = _json_object(_regular_bytes(receipt_path), RECEIPT)
        if receipt.get("source_state_sha256") != _sha(raw):
            _refuse("existing recovery receipt does not bind the retained source state")
    return _json_object(raw, "retained source state"), raw


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeError, json.JSONDecodeError):
        value = None
    if not isinstance(value, dict):
        _mismatch(f"{label} is not a JSON object")
    return value


def _interrupted_shape(source: Path, state: dict[str, Any]) -> None:
    if state.get("complete") is not False:
        _refuse("source is not an incomplete run")
    for key in ("outcome", "semantic_outcome", "blocking_reason", "commit",
                "failure_candidate", "failure_candidate_capture", "interrupted_recovery"):
        if state.get(key) is not None:
            _refuse(f"source already records {key}; it did not stop before its result")
    if state.get("finalization_attempted") or state.get("finalization_outcome") not in (None, "not_attempted"):
        _refuse("source attempted finalization")
    if state.get("resume_safety") == "fresh_run_required":
        _refuse("source requires a fresh run")
    if (source.parent / f"{source.name}.zip").exists():
        _refuse("source already has an archive; it was finalized")


def _stage_facts(
    source: Path, state: dict[str, Any], completed: tuple[str, ...], lifecycle: LifecycleSpec
) -> tuple[str | None, list[dict[str, str]]]:
    invoked = state.get("stages_invoked")
    names = lifecycle.stage_names
    if len(completed) >= len(names):
        _refuse("a complete semantic lifecycle cannot be interrupted before its result")
    if not isinstance(invoked, list) or invoked not in (list(completed), [*completed, names[len(completed)]]):
        _refuse("invoked stages are not the closed prefix plus at most the next stage")
    if len(invoked) == len(completed):
        return None, []
    stage = invoked[-1]
    prefix = lifecycle.prefixes[stage] + "."
    partial = [
        {"name": path.name, "sha256": sha256(path)}
        for path in sorted(source.iterdir())
        if path.name.startswith(prefix) and path.is_file() and not path.is_symlink()
    ]
    return stage, partial


def _pid_gone(pid: int, identity: str | None) -> bool:
    """True only when the recorded process incarnation provably ended."""
    from controller_generation_process import identity_supersedes, process_identity

    observed = process_identity(pid)
    if observed is not None:
        return identity is not None and identity_supersedes(pid, identity, observed)
    try:
        os.kill(pid, 0)  # Existence probe only; signal 0 is never delivered.
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


def _require_source_processes_ended(
    source: Path, state: dict[str, Any], stage: str | None, lifecycle: LifecycleSpec,
    resolved: dict[str, Any],
) -> dict[str, Any] | None:
    """A result-less source is recoverable only once its writers are gone.

    The recorded controller must be provably dead or superseded; without that
    identity nothing distinguishes an interruption from a live run. Every
    parent provider attempt must then be proven by its durable launch evidence
    never to have started, or to have ended; a source that predates that
    evidence and was mid-stage cannot be proven and refuses. Optional context
    launcher facts may add a refusal but never permit recovery. Proof uses
    existence probes only and never signals anything.
    """
    from . import provider_launch
    from .route_provenance import stage_effective_route

    generation = state.get("controller_generation")
    pid = generation.get("pid") if isinstance(generation, dict) else None
    identity = generation.get("process_identity") if isinstance(generation, dict) else None
    if type(pid) is not int or pid <= 0 or not isinstance(identity, str) or not identity:
        _refuse("source controller process identity is not recorded; cannot prove it ended")
    if not _pid_gone(pid, identity):
        _refuse(f"source controller process {pid} may still be running")
    try:
        proof = provider_launch.recovery_proof(
            source, state, stage, lifecycle=lifecycle,
            routes=lambda name: stage_effective_route(resolved, name),
        )
    except provider_launch.LaunchEvidenceError as error:
        raise ResumeError(error.code, error.detail) from error
    if stage is None:
        return proof
    launch = source / f"{lifecycle.prefixes[stage]}.context-launcher-deliveries.json"
    if not launch.exists():
        return proof
    facts = _json_object(_regular_bytes(launch), launch.name).get("launch_facts")
    if facts is None:
        return proof
    if not isinstance(facts, dict):
        _refuse("interrupted stage launch facts are invalid")
    group, provider = facts.get("process_group"), facts.get("pid")
    if type(group) is int and group > 0:
        try:
            os.killpg(group, 0)  # Existence probe only.
        except ProcessLookupError:
            return proof
        except OSError:
            pass
        _refuse(f"interrupted stage provider process group {group} may still be running")
    if type(provider) is not int or provider <= 0 or not _pid_gone(provider, None):
        _refuse("interrupted stage provider process cannot be proven ended")
    return proof


def _require_repository(source: Path, state: dict[str, Any], cwd: Path) -> None:
    """Bind recovery to the source checkout before any recovery write."""
    from . import candidate as candidate_module

    try:
        candidate_module.require_worktree(cwd)
        root = gitstate_module.repository_root(cwd)
    except (candidate_module.CandidateError, gitstate_module.GitStateError) as error:
        raise ResumeError("RESUME_PROJECT_MISMATCH", f"no source repository here: {error}") from error
    if state.get("project") != run_module.project_name(root):
        raise ResumeError("RESUME_PROJECT_MISMATCH", "source project differs")
    if entry(source, state, detached=True).root.resolve() != root.resolve():
        raise ResumeError("RESUME_PROJECT_MISMATCH", "source repository root differs")


def qualify(source_path: Path) -> dict[str, Any]:
    """Read-only proof that a result-less source is a recoverable interruption."""
    from . import resume as resume_module
    from .worker_recovery import verify_retained_cleanup

    source = require_source(source_path)
    state, raw = _pre_state(source)
    run_module.validate_run_topology(source, state, None, error_fn=ResumeError)
    _interrupted_shape(source, state)
    request_raw = _regular_bytes(source / "request.json")
    try:
        request = parse_request(request_raw)
    except RequestError as error:
        raise ResumeError("RESUME_SOURCE_INVALID", f"retained request is invalid: {error}") from error
    resolved = load_json(source, "resolved.json")
    try:
        lifecycle = get_lifecycle(str(state.get("lifecycle", LIFECYCLE_STANDARD)))
    except ValueError as error:
        raise ResumeError("RESUME_SOURCE_INVALID", str(error)) from error
    if (
        (state.get("phase_type"), state.get("execution_mode"))
        != (request.phase_type, request.execution_mode)
        or resolved.get("phase_type") != request.phase_type
        or resolved.get("execution_mode") != request.execution_mode
        or resolved.get("lifecycle", LIFECYCLE_STANDARD) != lifecycle.name
    ):
        _refuse("source request, state and route identity disagree")
    entry(source, state, detached=True)
    completed = completed_prefix(state, resolved, source)
    validate_bindings(source, state, completed)
    stage, partial = _stage_facts(source, state, completed, lifecycle)
    launch_proof = _require_source_processes_ended(source, state, stage, lifecycle, resolved)
    try:
        verify_retained_cleanup(source, state, settled_ok=True)
    except ValueError as error:
        raise ResumeError("WORKER_CLEANUP_FAILED", str(error)) from error
    evidence = source / "entry-evidence.json"
    return {
        "source": source,
        "state": state,
        "source_state_bytes": raw,
        "lifecycle": lifecycle,
        "completed_stages": list(completed),
        "interrupted_stage": stage,
        "interrupted_stage_mutating": bool(stage and lifecycle.stage(stage).is_mutating),
        "interrupted_stage_artifacts": partial,
        "provider_launch": launch_proof,
        "completed_artifacts": list(resume_module.artifact_records(source, completed, lifecycle)),
        "request_sha256": sha256(source / "request.json"),
        "resolved_sha256": sha256(source / "resolved.json"),
        "entry_evidence_sha256": sha256(evidence) if evidence.is_file() else None,
    }


def _receipt(facts: dict[str, Any], workers: list[dict[str, Any]]) -> dict[str, Any]:
    state = facts["state"]
    return {
        "schema": SCHEMA,
        "source_run_id": state["run_id"],
        "source_state_sha256": _sha(facts["source_state_bytes"]),
        "request_sha256": facts["request_sha256"],
        "resolved_sha256": facts["resolved_sha256"],
        "entry_evidence_sha256": facts["entry_evidence_sha256"],
        "lifecycle": facts["lifecycle"].name,
        "completed_stages": facts["completed_stages"],
        "completed_artifacts": facts["completed_artifacts"],
        "interrupted_stage": facts["interrupted_stage"],
        "interrupted_stage_mutating": facts["interrupted_stage_mutating"],
        "interrupted_stage_artifacts": facts["interrupted_stage_artifacts"],
        "worker_custody": {"pending": state.get("worker_cleanup_pending"), "parents": workers},
        # Only contract-bearing sources carry the proof, so a ZE-era receipt
        # still rolls forward to identical bytes.
        **({"provider_launch": facts["provider_launch"]} if facts["provider_launch"] is not None else {}),
        "recovered_outcome": {
            "complete": False, "outcome": None, "semantic_outcome": None,
            "finalization_outcome": "not_attempted", "blocking_code": BLOCKING_CODE,
        },
        "semantic_completion_claimed": False,
    }


def _needs_recovery(source: Path, state: dict[str, Any]) -> bool:
    if state.get("interrupted_recovery") is not None:
        verify(source, state)
        return False
    return (source / RECEIPT).exists() or not (source / "result.json").exists()


def prepare(
    source_path: Path, phase_id: str, request: Any, *, dry_run: bool, cwd: Path
) -> dict[str, Any] | None:
    """Resume hook: recover, or preview recovery without writing on dry-run.

    The caller's identity and checkout are proven before any write, so a
    mismatched request or foreign checkout can neither preview nor
    materialize another task's recovery.
    """
    source = require_source(source_path)
    if not _needs_recovery(source, load_json(source, "state.json")):
        return None
    state, _raw = _pre_state(source)
    require_same_request(source, request)
    if state.get("phase_id") != phase_id:
        raise ResumeError("RESUME_REQUEST_MISMATCH", "semantic phase identity differs")
    _require_repository(source, state, cwd)
    if not dry_run:
        ensure(source)
        return None
    facts = qualify(source)
    return {
        "outcome": "dry_run", "dry_run": True, "complete": False,
        "source": str(source),
        "interrupted_recovery": {
            "status": "qualified_not_materialized",
            "completed_stages": facts["completed_stages"],
            "interrupted_stage": facts["interrupted_stage"],
            "worker_cleanup_pending": facts["state"].get("worker_cleanup_pending"),
            "detail": "a non-dry-run resume materializes the missing aggregate result",
        },
    }


def ensure(source_path: Path) -> dict[str, Any] | None:
    """Materialize the missing aggregate result exactly once, idempotently."""
    from . import outcomes
    from . import result_artifacts
    from .worker_recovery import reconcile_settled_parents

    source = require_source(source_path)
    if not _needs_recovery(source, load_json(source, "state.json")):
        return None
    facts = qualify(source)
    try:
        workers = reconcile_settled_parents(
            source, facts["state"], "dispatcher process ended before draining; interrupted-run recovery"
        )
    except ValueError as error:
        raise ResumeError("WORKER_CLEANUP_FAILED", str(error)) from error
    receipt_bytes = _encode(_receipt(facts, workers))
    directory = _SourceDirectory(source)
    for name, data in ((RECEIPT, receipt_bytes), (SOURCE_STATE_COPY, facts["source_state_bytes"])):
        existing = source / name
        if existing.exists():
            if _regular_bytes(existing) != data:
                _refuse(f"existing {name} disagrees with the deterministic recovery")
        else:
            directory.write_bytes(name, data)
    recovered = copy.deepcopy(facts["state"])
    recovered["blocking_reason"] = {
        "code": BLOCKING_CODE,
        "detail": "dispatcher process ended during a stage before writing its aggregate result",
    }
    recovered["finalization_outcome"] = "not_attempted"
    record = {
        "schema": SCHEMA, "receipt": RECEIPT, "receipt_sha256": _sha(receipt_bytes),
        "source_state_copy": SOURCE_STATE_COPY,
        "source_state_sha256": _sha(facts["source_state_bytes"]),
        "result_sha256": None,
        "completed_stages": facts["completed_stages"],
        "interrupted_stage": facts["interrupted_stage"],
        "semantic_completion_claimed": False,
    }
    recovered["interrupted_recovery"] = record
    outcomes.finish(recovered)
    result_artifacts.write(directory, recovered, [])
    record["result_sha256"] = sha256(source / "result.json")
    directory.write_json("state.json", recovered)
    verify(source, recovered)
    return record


def verify(source: Path, state: dict[str, Any]) -> None:
    """Bind a recovered source to its receipt, pre-state copy and result."""
    record = state.get("interrupted_recovery")
    if record is None:
        _mismatch("recovery receipt exists without a recorded recovery")
    if not isinstance(record, dict) or set(record) != RECORD_FIELDS or record.get("schema") != SCHEMA:
        _mismatch("recovery record is invalid")
    receipt_bytes = _regular_bytes(source / RECEIPT)
    pre_bytes = _regular_bytes(source / SOURCE_STATE_COPY)
    receipt = _json_object(receipt_bytes, RECEIPT)
    if (
        record["receipt"] != RECEIPT or record["source_state_copy"] != SOURCE_STATE_COPY
        or record["receipt_sha256"] != _sha(receipt_bytes)
        or receipt.get("schema") != SCHEMA
        or receipt.get("source_run_id") != state.get("run_id")
        or record["source_state_sha256"] != _sha(pre_bytes)
        or receipt.get("source_state_sha256") != record["source_state_sha256"]
        or record["result_sha256"] != sha256(source / "result.json")
        or record["completed_stages"] != receipt.get("completed_stages")
        or record["interrupted_stage"] != receipt.get("interrupted_stage")
        or record["semantic_completion_claimed"] is not False
    ):
        _mismatch("receipt, retained pre-state, result and state disagree")
    pre = _json_object(pre_bytes, SOURCE_STATE_COPY)
    if any(pre.get(key) != state.get(key) for key in PRESERVED_KEYS):
        _mismatch("recovery changed a retained lifecycle fact")
    if (state.get("blocking_reason") or {}).get("code") != BLOCKING_CODE:
        _mismatch("recovered blocker is not the mechanical interruption fact")


def residue_facts(
    state: dict[str, Any],
    lifecycle: LifecycleSpec,
    source_entry: gitstate_module.EntryState,
    current_entry: gitstate_module.EntryState,
    candidate_tree: str,
    manifest: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Name dirty paths that a killed mutating stage may have written.

    They changed after the source entry and after the inherited candidate,
    are dirty at the resumed entry, and are not inherited candidate paths.
    Provenance between the dead stage and an operator is unknowable, so these
    are never owned automatically; ownership challenges govern them.
    """
    record = state.get("interrupted_recovery")
    if not isinstance(record, dict):
        return {}
    stage = record.get("interrupted_stage")
    facts: dict[str, Any] = {
        "interrupted_stage": stage,
        "interrupted_residue_paths": [],
        "source_entry_dirty_paths": sorted(source_entry.dirty),
    }
    if stage is None or not lifecycle.stage(stage).is_mutating:
        return facts
    try:
        after_candidate = {c.path for c in gitstate_module.phase_delta(root, candidate_tree, current_entry.tree)}
        after_source = {c.path for c in gitstate_module.phase_delta(root, source_entry.tree, current_entry.tree)}
    except gitstate_module.GitStateError as error:
        raise ResumeError("RESUME_ARTIFACT_MISMATCH", f"cannot classify interruption residue: {error.detail}") from error
    residue = sorted((after_candidate & after_source & set(current_entry.dirty)) - set(manifest["paths"]))
    from .ownership_challenge import MAX_RECORDS

    if len(residue) > MAX_RECORDS:
        _refuse(f"interruption residue exceeds {MAX_RECORDS} challengeable paths")
    facts["interrupted_residue_paths"] = residue
    return facts
