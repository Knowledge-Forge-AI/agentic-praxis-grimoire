"""Lifecycle-aware prompt capacity planning before provider one is spent."""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from . import envelope as envelope_module
from . import result as result_module
from . import review_result as review_result_module
from .lifecycle import (
    LIFECYCLE_PLAN_REVIEWED,
    LIFECYCLE_SOLO,
    LIFECYCLE_STANDARD,
    LIFECYCLE_WORK_REVIEWED,
)
from .provider import MAX_STAGE_OUTPUT_BYTES
from .routing import Endpoint, PROVIDER_ANTIGRAVITY
from .transport import PromptLimitError, ensure_prompt_fits


def _omission_note(
    source_stage: str, artifact_basename: str, artifact_bytes: bytes
) -> bytes:
    if (
        not artifact_basename
        or artifact_basename in {".", ".."}
        or "/" in artifact_basename
        or "\\" in artifact_basename
        or "\x00" in artifact_basename
    ):
        raise PromptLimitError("optional prior-material artifact is not a safe basename")
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    return (
        "Dispatcher prompt-capacity decision: one non-authoritative prior "
        "artifact was omitted as a whole.\n"
        f"source_stage: {source_stage}\n"
        f"artifact_basename: {artifact_basename}\n"
        f"exact_bytes: {len(artifact_bytes)}\n"
        f"sha256: {digest}\n"
        "No prefix or summary was substituted. Inspect the bound/current "
        "Git-tree candidate for the authoritative work.\n"
    ).encode("utf-8")


def fit_optional_narrative(
    stage: str,
    endpoint: Endpoint,
    render: Callable[[str | bytes], Any],
    narrative: str | bytes,
    *,
    source_stage: str,
    artifact_basename: str,
    artifact_bytes: bytes,
    mandatory_sources: tuple[str, ...] = (),
) -> tuple[Any, dict[str, Any]]:
    """Render one actual prompt, omitting only a whole optional narrative."""
    full = render(narrative)
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    record: dict[str, Any] = {
        "stage": stage,
        "source_stage": source_stage,
        "artifact_basename": artifact_basename,
        "classification": "non_authoritative_prior_narrative",
        "artifact_bytes": len(artifact_bytes),
        "artifact_sha256": digest,
        "full_prompt_bytes": len(full.data),
        "optional_source": source_stage,
        "mandatory_sources": list(mandatory_sources),
        "omitted_sources": [],
        "preserved_sources": list(mandatory_sources),
        "omission_scope": "whole_optional_artifact_only",
    }
    try:
        ensure_prompt_fits(stage, endpoint, full)
    except PromptLimitError:
        note = _omission_note(source_stage, artifact_basename, artifact_bytes)
        reduced = render(note)
        ensure_prompt_fits(stage, endpoint, reduced)
        record.update({
            "decision": "omitted_whole",
            "final_prompt_bytes": len(reduced.data),
            "prefix_or_summary_substituted": False,
            "mandatory_material_preserved": True,
            "omitted_sources": [source_stage],
        })
        return reduced, record
    record.update({
        "decision": "included_exact",
        "final_prompt_bytes": len(full.data),
        "prefix_or_summary_substituted": False,
        "mandatory_material_preserved": True,
    })
    return full, record


def _tree_binding() -> dict[str, Any]:
    return {"kind": "git_tree", "head": "0" * 40, "tree": "0" * 40}


def _plan_binding() -> dict[str, Any]:
    return {
        "kind": "plan_bytes", "sha256": "0" * 64,
        "bytes": MAX_STAGE_OUTPUT_BYTES,
    }


def _bound(
    stage: str,
    endpoint: Endpoint,
    render: Callable[[], Any],
    sources: tuple[str, ...],
    output_limits: dict[str, int],
    optional_sources: tuple[str, ...] = (),
) -> dict[str, Any]:
    rendered = render()
    return {
        "endpoint_provider": endpoint.provider,
        "static_prompt_bytes": len(rendered.data),
        "mechanically_bounded": endpoint.provider == PROVIDER_ANTIGRAVITY,
        "sources": list(sources),
        "mandatory_sources": list(sources),
        "optional_sources": list(optional_sources),
        "omission_scope": "whole_optional_artifact_only" if optional_sources else "none",
        "mandatory_material_preserved": True,
        "prompt_fit_decision": (
            "checked_at_actual_stage_prompt_construction"
            if sources
            else "checked_before_current_stage_invocation"
        ),
        "current_stage_output_limit_authority": False,
    }


def preflight_lifecycle_capacity(
    dispatcher: Any,
    request: Any,
    run_id: str,
    task_prompt: str,
    endpoints: dict[str, Endpoint],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Record static prompt evidence without constraining stage output capture."""
    nonce = "0" * 32
    begin, end = result_module.markers(nonce)
    lifecycle = dispatcher.lifecycle.name
    output_limits: dict[str, int] = {}
    stages: dict[str, Any] = {}

    if lifecycle == LIFECYCLE_STANDARD:
        stages["final_review"] = _bound(
            "final_review", endpoints["final_review"],
            lambda: dispatcher.review_prompt(
                "final_review", request, run_id, _tree_binding(), "", task_prompt,
                review_result_module.contract("final_review", nonce),
            ),
            ("original_scope", "candidate_binding", "review_contract"),
            output_limits, ("work_narrative",),
        )
        stages["closeout"] = _bound(
            "closeout", endpoints["closeout"],
            lambda: dispatcher.closeout_prompt(
                request,
                run_id,
                task_prompt,
                _tree_binding(),
                _tree_binding(),
                "",
                "",
                begin,
                end,
                stage_delta_summary="",
                qualification_evidence="",
            ),
            (
                "original_scope",
                "producer_binding",
                "current_worktree_product",
                "work_review_findings",
                "terminal_result_contract",
            ),
            output_limits,
            ("producer_narrative",),
        )
    elif lifecycle == LIFECYCLE_SOLO:
        stages["solo"] = _bound(
            "solo", endpoints["solo"],
            lambda: dispatcher.continuation_prompt(
                "solo", request, run_id, envelope_module.SOLO_ENVELOPE, [],
                include_task_prompt=True,
                contract=dispatcher._terminal_contract("solo", begin, end),
                task_prompt=task_prompt,
            ),
            (), output_limits,
        )
    elif lifecycle == LIFECYCLE_PLAN_REVIEWED:
        stages["plan_review"] = _bound(
            "plan_review", endpoints["plan_review"],
            lambda: dispatcher.review_prompt(
                "plan_review", request, run_id, _plan_binding(), "", task_prompt,
                review_result_module.contract("plan_review", nonce),
            ),
            ("original_scope", "proposal_binding", "review_contract"),
            output_limits,
        )
        stages["produce_close"] = _bound(
            "produce_close", endpoints["produce_close"],
            lambda: dispatcher.continuation_prompt(
                "produce_close", request, run_id,
                envelope_module.PLAN_REVIEWED_PRODUCE_CLOSE_ENVELOPE,
                [
                    ("Plan proposal binding (dispatcher-owned exact bytes)", ""),
                    (
                        "Planner proposal — exact bound bytes, to be dispositioned",
                        "",
                    ),
                    ("Independent plan review findings", ""),
                    ("Stage deltas and change ledger", ""),
                ],
                include_task_prompt=True,
                contract=dispatcher._terminal_contract("produce_close", begin, end),
                task_prompt=task_prompt,
            ),
            (
                "original_scope",
                "proposal_binding",
                "plan_review_findings",
                "terminal_result_contract",
            ),
            output_limits,
        )
    elif lifecycle == LIFECYCLE_WORK_REVIEWED:
        stages["work_review"] = _bound(
            "work_review", endpoints["work_review"],
            lambda: dispatcher.review_prompt(
                "work_review", request, run_id, _tree_binding(), "", task_prompt,
                review_result_module.contract("work_review", nonce),
            ),
            (
                "original_scope",
                "producer_binding",
                "work_review_contract",
            ),
            output_limits,
        )
        stages["revise_close"] = _bound(
            "revise_close", endpoints["revise_close"],
            lambda: dispatcher.continuation_prompt(
                "revise_close", request, run_id,
                envelope_module.WORK_REVIEWED_REVISE_CLOSE_ENVELOPE,
                [
                    ("Producer binding (dispatcher-owned exact product)", ""),
                    ("Current worktree product (dispatcher-owned exact binding)", ""),
                    ("Producer narrative (optional whole artifact)", ""),
                    ("Independent work review findings", ""),
                    ("Stage deltas and change ledger", ""),
                ],
                include_task_prompt=True,
                contract=dispatcher._terminal_contract("revise_close", begin, end),
                task_prompt=task_prompt,
            ),
            (
                "original_scope",
                "producer_binding",
                "current_worktree_product",
                "work_review_findings",
                "terminal_result_contract",
            ),
            output_limits,
            ("producer_narrative",),
        )
    else:
        raise PromptLimitError(f"unsupported lifecycle capacity preflight: {lifecycle}")

    return ({
        "status": "completed",
        "lifecycle": lifecycle,
        "method": "static-envelope-evidence-plus-actual-prompt-fit",
        "stages": stages,
        "output_limits": output_limits,
        "placeholders_persisted": False,
    }, output_limits)
