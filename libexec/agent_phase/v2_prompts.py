"""Prompt synthesis templates and renderers for Request V2 turns."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from . import result as result_module
from .envelope import TERMINAL_RESULT_CONTRACT
from .review_result import contract as review_contract


def render_plan_prompt(task_prompt: str) -> bytes:
    """Render prompt for Turn 1 (Planner)."""
    text = (
        f"# Planning Phase\n\n"
        f"You are the Planner for this task.\n\n"
        f"## Task Requirements\n"
        f"{task_prompt.strip()}\n\n"
        f"## Instructions\n"
        f"Produce a comprehensive implementation plan detailing architecture, "
        f"components, step-by-step changes, and verification strategy.\n"
    )
    return text.encode("utf-8")


def render_plan_review_prompt(
    task_prompt: str,
    plan_material_text: str,
    nonce: str,
) -> bytes:
    """Render prompt for Turn 2 (Plan Reviewer)."""
    contract_text = review_contract("plan_review", nonce)
    text = (
        f"# Independent Plan Review\n\n"
        f"You are the independent Plan Reviewer. Evaluate the proposed plan against the task scope.\n\n"
        f"## Original Task Scope\n"
        f"{task_prompt.strip()}\n\n"
        f"## Proposed Plan Material\n"
        f"{plan_material_text.strip()}\n\n"
        f"{contract_text}\n"
    )
    return text.encode("utf-8")


def render_work_prompt(
    task_prompt: str,
    plan_material_text: str,
    plan_review_outcome: str,
    plan_findings: Sequence[Mapping[str, Any]],
    plan_disposition: str,
    baseline_tree: str | None = None,
) -> bytes:
    """Render prompt for Turn 3 (Plan Review Disposition + Producer)."""
    findings_summary = (
        f"Plan review outcome: {plan_review_outcome}\n"
        f"Disposition: {plan_disposition}\n"
    )
    if plan_findings:
        findings_summary += "Findings to incorporate:\n"
        for f in plan_findings:
            findings_summary += f"- [{f.get('severity', 'advisory')}] {f.get('title', '')}: {f.get('detail', '')}\n"

    baseline_info = f"Baseline git tree: `{baseline_tree}`\n" if baseline_tree else ""

    text = (
        f"# Work / Implementation Phase\n\n"
        f"You are the Producer. Implement the requested changes adhering to the plan and review disposition.\n\n"
        f"## Original Task Scope\n"
        f"{task_prompt.strip()}\n\n"
        f"## Approved / Amended Plan Material\n"
        f"{plan_material_text.strip()}\n\n"
        f"## Plan Review Findings & Disposition\n"
        f"{findings_summary}\n"
        f"{baseline_info}\n"
        f"## Instructions\n"
        f"Implement the solution completely within repository instructions. Run verification and report stdout.\n"
    )
    return text.encode("utf-8")


def render_work_review_prompt(
    task_prompt: str,
    candidate_tree: str,
    candidate_delta: Sequence[str],
    work_stdout: str,
    nonce: str,
) -> bytes:
    """Render prompt for Turn 4 (Work Reviewer)."""
    contract_text = review_contract("final_review", nonce)
    delta_text = "\n".join(f"- {p}" for p in candidate_delta) if candidate_delta else "No file delta observed."

    text = (
        f"# Independent Work Review\n\n"
        f"You are the independent Work Reviewer. Evaluate the producer candidate against the task scope.\n\n"
        f"## Original Task Scope\n"
        f"{task_prompt.strip()}\n\n"
        f"## Pre-Final Candidate Git Tree\n"
        f"Tree SHA: `{candidate_tree}`\n\n"
        f"### Changed Paths\n"
        f"{delta_text}\n\n"
        f"## Producer Narrative & Output\n"
        f"{work_stdout.strip()}\n\n"
        f"{contract_text}\n"
    )
    return text.encode("utf-8")


def render_closeout_prompt(
    task_prompt: str,
    candidate_tree: str,
    work_review_outcome: str,
    work_findings: Sequence[Mapping[str, Any]],
    work_disposition: str,
    nonce: str,
) -> bytes:
    """Render prompt for Turn 5 (Work Review Disposition + Reviser + Closeout Agent)."""
    findings_summary = (
        f"Work review outcome: {work_review_outcome}\n"
        f"Disposition: {work_disposition}\n"
    )
    if work_findings:
        findings_summary += "Findings to address/close:\n"
        for f in work_findings:
            findings_summary += f"- [{f.get('severity', 'advisory')}] {f.get('title', '')}: {f.get('detail', '')}\n"

    begin, end = result_module.markers(nonce)
    contract_text = TERMINAL_RESULT_CONTRACT.format(begin=begin, end=end, stage="closeout")

    text = (
        f"# Closeout and Finalization Phase\n\n"
        f"You are the Closeout Agent. Verify terminal completion, review disposition, and final qualification.\n\n"
        f"## Original Task Scope\n"
        f"{task_prompt.strip()}\n\n"
        f"## Current Candidate Tree\n"
        f"`{candidate_tree}`\n\n"
        f"## Work Review Findings & Disposition\n"
        f"{findings_summary}\n\n"
        f"## Instructions\n"
        f"Perform any required revisions, finalize documentation/receipts, and verify terminal criteria.\n\n"
        f"{contract_text}\n"
    )
    return text.encode("utf-8")

