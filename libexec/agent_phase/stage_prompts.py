"""Prompt assembly shared by dispatcher stages; bound overrides stay on the dispatcher."""

from __future__ import annotations

import json
from typing import Any, Sequence

from . import adoption as adoption_module, envelope as envelope_module
from .request import PhaseRequest


def _header(dispatcher, stage: str, request: PhaseRequest, run_id: str) -> str:
    return envelope_module.stage_header(
        stage,
        run_id,
        request.phase_type,
        request.execution_mode,
        dispatcher.lifecycle.name,
        dispatcher.lifecycle.checkpoints,
        dispatcher.finalization_policy,
    ) + adoption_module.prompt_context(getattr(dispatcher, "_adoption", None))


def plan_prompt(
    dispatcher, request: PhaseRequest, run_id: str, task_prompt: str | None = None
) -> envelope_module.RenderedPrompt:
    return envelope_module.render(
        [
            envelope_module.Segment(
                envelope_module.SEGMENT_ENVELOPE,
                dispatcher._header(envelope_module.STAGE_PLAN, request, run_id)
                + "\n"
                + envelope_module.PLAN_ENVELOPE
                + "\n\n"
                + envelope_module.PROVIDER_NOTE
                + "\n\n"
                + envelope_module.TASK_PROMPT_HEADER,
            ),
            envelope_module.Segment(
                envelope_module.SEGMENT_TASK_PROMPT,
                request.prompt if task_prompt is None else task_prompt,
            ),
        ]
    )


def review_prompt(
    dispatcher,
    stage: str,
    request: PhaseRequest,
    run_id: str,
    binding: dict[str, Any],
    material: str | bytes,
    task_prompt: str,
    review_contract: str,
) -> envelope_module.RenderedPrompt:
    task_header = (
        dispatcher._header(stage, request, run_id)
        + "\n"
        + envelope_module.REVIEWER_ENVELOPE
        + "\n\n"
        + review_contract
        + "\n\n"
        + envelope_module.GIT_IDENTITY_POLICY
        + "\n\n"
        + envelope_module.TASK_PROMPT_HEADER
    )
    material_header = (
        "Candidate binding:\n"
        + "\n".join(f"  {key}: {value}" for key, value in sorted(binding.items()))
        + "\n\n"
        + envelope_module.REVIEWER_INDEPENDENCE
        + "\n\n"
        + envelope_module.PRIOR_MATERIAL_HEADER
    )
    return envelope_module.render(
        [
            envelope_module.Segment(
                envelope_module.SEGMENT_ENVELOPE, task_header
            ),
            envelope_module.Segment(
                envelope_module.SEGMENT_TASK_PROMPT, task_prompt
            ),
            envelope_module.Segment(
                envelope_module.SEGMENT_ENVELOPE, material_header
            ),
            envelope_module.Segment(
                envelope_module.SEGMENT_PRIOR_MATERIAL, material
            ),
        ]
    )


def continuation_prompt(
    dispatcher,
    stage: str,
    request: PhaseRequest,
    run_id: str,
    directive: str,
    prior: list[tuple[str, str | bytes]],
    include_task_prompt: bool,
    contract: str | None = None,
    task_prompt: str | None = None,
) -> envelope_module.RenderedPrompt:
    header = (
        dispatcher._header(stage, request, run_id)
        + "\n"
        + directive
        + "\n\n"
        + envelope_module.PROVIDER_NOTE
    )
    segments = [envelope_module.Segment(envelope_module.SEGMENT_ENVELOPE, header)]
    if include_task_prompt:
        segments.append(
            envelope_module.Segment(
                envelope_module.SEGMENT_ENVELOPE,
                "\n" + envelope_module.TASK_PROMPT_HEADER,
            )
        )
        segments.append(
            envelope_module.Segment(
                envelope_module.SEGMENT_TASK_PROMPT,
                request.prompt if task_prompt is None else task_prompt,
            )
        )
    segments.append(
        envelope_module.Segment(
            envelope_module.SEGMENT_ENVELOPE,
            "\n" + envelope_module.PRIOR_MATERIAL_HEADER,
        )
    )
    for title, body in prior:
        if isinstance(body, bytes):
            payload: str | bytes = (
                f"\n## {title}\n\n".encode("utf-8") + body
            )
        else:
            payload = f"\n## {title}\n\n{body}"
        segments.append(
            envelope_module.Segment(
                envelope_module.SEGMENT_PRIOR_MATERIAL,
                payload,
            )
        )
    if contract is not None:
        # Keep the nonce-bound contract at the absolute prompt end. Do not
        # place any task, prior material, or contextual headers after this
        # segment: the provider's exact ending must be unambiguous.
        segments.append(
            envelope_module.Segment(
                envelope_module.SEGMENT_ENVELOPE,
                "\n" + envelope_module.TERMINAL_CONTRACT_PRECEDER
                + "\n" + contract,
            )
        )
    return envelope_module.render(segments)


def closeout_prompt(
    dispatcher,
    request: PhaseRequest,
    run_id: str,
    task_prompt: str,
    producer_binding: dict[str, Any],
    current_product: dict[str, Any],
    producer_narrative: str | bytes,
    findings: str,
    begin: str,
    end: str,
    *,
    stage_delta_summary: str | None = None,
    qualification_evidence: str | None = None,
    review_window_mutations: Sequence[str] | str | None = None,
) -> envelope_module.RenderedPrompt:
    prior_segments: list[tuple[str, str | bytes]] = [
        (
            "Producer candidate binding (dispatcher-owned exact identity)",
            json.dumps(producer_binding, sort_keys=True, separators=(",", ":")),
        ),
        (
            "Current exact worktree product (dispatcher-owned binding)",
            json.dumps(current_product, sort_keys=True, separators=(",", ":")),
        ),
        ("Producer summary/output (optional whole artifact)", producer_narrative),
        ("Independent work-review findings", findings),
    ]
    if stage_delta_summary:
        prior_segments.append(
            ("Prior stage-delta summary (dispatcher-owned evidence)", stage_delta_summary)
        )
    if qualification_evidence:
        prior_segments.append(
            ("Qualification evidence available in the run", qualification_evidence)
        )
    if review_window_mutations:
        from .v2_prompts import format_review_window_mutation_notice
        notice_text = (
            review_window_mutations
            if isinstance(review_window_mutations, str)
            else format_review_window_mutation_notice(review_window_mutations)
        )
        if notice_text.strip():
            prior_segments.append(
                ("Review-window mutation notice (dispatcher-owned evidence)", notice_text.strip())
            )
    return dispatcher.continuation_prompt(
        envelope_module.STAGE_CLOSEOUT,
        request,
        run_id,
        envelope_module.CLOSEOUT_ENVELOPE,
        prior_segments,
        include_task_prompt=True,
        contract=envelope_module.CLOSEOUT_RESULT_CONTRACT.format(
            begin=begin, end=end
        ),
        task_prompt=task_prompt,
    )
