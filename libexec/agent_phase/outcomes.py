"""Additive terminal truth and closed dispatcher-owned failure categories."""

from __future__ import annotations

from typing import Any

REPAIRABLE_MECHANICAL = "repairable_mechanical"
REQUIRES_MANAGER_OWNERSHIP = "requires_manager_ownership"
REQUIRES_SEMANTIC_REVISION = "requires_semantic_revision"
REQUIRES_REPOSITORY_RESOLUTION = "requires_repository_resolution"
FAILURE_CLASSIFICATIONS = frozenset({REPAIRABLE_MECHANICAL, REQUIRES_MANAGER_OWNERSHIP,
    REQUIRES_SEMANTIC_REVISION, REQUIRES_REPOSITORY_RESOLUTION})
FINALIZATION_COMPLETED = "completed"
FINALIZATION_BLOCKED = "blocked"
FINALIZATION_NOT_ATTEMPTED = "not_attempted"
FINALIZATION_REUSED = "reused"
FINALIZATION_MATERIALIZED = "materialized"
FINALIZATION_OUTCOMES = frozenset({"completed", "blocked", "not_attempted", "reused", "materialized"})

# Only dispatcher-issued codes, never provider narrative or category strings.
_MANAGER = frozenset({"OWNERSHIP_CHALLENGE_OPEN", "ENTRY_DIRT_OVERLAP", "MANAGER_DISPOSITION_REQUIRED",
    "PATH_DISPOSITION_INVALID", "PATH_OWNERSHIP_REQUIRED", "PATH_OWNERSHIP_INVALID"})
_SEMANTIC = frozenset({"OWNERSHIP_PROVIDER_RESOLUTION_INVALID", "PROVIDER_OUTCOME_INVALID", "PROVIDER_OUTCOME_BLOCKED",
    "PROVIDER_OUTCOME_FAILED", "COMMIT_MESSAGE_MISSING", "INVOCATION_COUNT", "REVIEW_COUNT",
    "PROVIDER_PROMPT_LIMIT", "PROVIDER_TIMEOUT", "TERMINAL_RESULT_INVALID"})
_MECHANICAL = frozenset({"METADATA_NORMALIZATION_VERIFIED", "CANDIDATE_MATERIALIZATION_VERIFIED",
    "RECORDED_FINALIZATION_VERIFIED"})


def classify_failure(code: str, state: dict[str, Any] | None = None) -> str:
    """Unknown errors are never repairable; retained observations alone prove nothing.

    Recovery issues verified codes only after rechecking immutable objects and
    the full ownership set. This label is descriptive, not admission.
    """
    if code in _MECHANICAL:
        return REPAIRABLE_MECHANICAL
    if code in _MANAGER:
        return REQUIRES_MANAGER_OWNERSHIP
    if code in _SEMANTIC:
        return REQUIRES_SEMANTIC_REVISION
    return REQUIRES_REPOSITORY_RESOLUTION


def finish(state: dict[str, Any]) -> None:
    """Freeze semantic/Git truth before archive delivery; don't upgrade old sources."""
    if "semantic_outcome" not in state and "finalization_outcome" not in state:
        return
    outcome = state.get("finalization_outcome", "not_attempted")
    blocking = state.get("blocking_reason") or {}
    if not blocking and outcome == "blocked":
        blocking = (state.get("push") or {}).get("failure") or {}
    code = blocking.get("code") if outcome in ("blocked", "not_attempted") else None
    commit = state.get("commit") or {}
    local = "not_attempted"
    if commit.get("sha"):
        local = "reused" if state.get("commit_reused") else (
            "completed" if state.get("commit_verified") else "created")
    state["finalization"] = {
        "outcome": outcome, "code": code,
        "repair_class": classify_failure(code, state) if code else None,
        "local_commit": {"outcome": local, "sha": commit.get("sha")},
        "publication_status": (state.get("push") or {}).get("status", "not_attempted"),
    }
    if outcome == "not_attempted" and state.get("semantic_outcome") in ("blocked", "failed"):
        state["finalization"]["repair_class"] = REQUIRES_SEMANTIC_REVISION


def validate(state: dict[str, Any], result: dict[str, Any]) -> None:
    """Validate optional additive shape and its relationship to retained facts."""
    from .result import OUTCOMES
    for key in ("semantic_outcome", "finalization_outcome", "finalization"):
        if (key in state) != (key in result) or state.get(key) != result.get(key):
            raise ValueError(f"source result and state disagree on {key}")
    semantic = state.get("semantic_outcome")
    if semantic is not None and (not isinstance(semantic, str) or semantic not in OUTCOMES):
        raise ValueError("invalid semantic outcome")
    value = state.get("finalization_outcome")
    if value is not None and (not isinstance(value, str) or value not in FINALIZATION_OUTCOMES):
        raise ValueError("invalid finalization outcome")
    record = state.get("finalization")
    if record is not None:
        expected = dict(state)
        finish(expected)
        if not isinstance(record, dict) or record != expected.get("finalization"):
            raise ValueError("finalization record disagrees with retained Git facts")
        if record["outcome"] != value:
            raise ValueError("finalization aliases disagree")
    if value in ("completed", "reused", "materialized") and semantic != "completed":
        raise ValueError("Git success lacks completed semantic truth")
    if value == "not_attempted" and state.get("finalization_attempted"):
        raise ValueError("not-attempted outcome contradicts finalization attempt")
    if value in ("completed", "reused") and state.get("completion_kind") not in {
        "checkpoint_ready", "finalized_empty_delta", "committed_local", "published",
    }:
        raise ValueError("finalization success contradicts completion evidence")
    if value == "reused" and not state.get("commit_reused"):
        raise ValueError("reused finalization lacks reuse evidence")
    if value == "materialized":
        raise ValueError("materialization is a separate receipt, not historical run finalization")


def validate_terminal(state: dict[str, Any], parsed: Any) -> None:
    semantic = state.get("semantic_outcome")
    if not state.get("terminal_result_validated"):
        if semantic == "completed":
            raise ValueError("semantic completion lacks original terminal validation")
        # A newer parser may accept historically rejected output. That is
        # completion evidence for a NEW exact resume, not rewritten source truth.
        return
    if semantic == "completed" and (parsed is None or not parsed.completed):
        raise ValueError("semantic completion disagrees with retained terminal result")
    if parsed is not None and semantic is not None and semantic != parsed.outcome:
        raise ValueError("semantic outcome disagrees with retained terminal result")
