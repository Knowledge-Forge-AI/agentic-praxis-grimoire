"""No-provider lifecycle resolution and first-prompt rendering."""

from __future__ import annotations

from typing import Any

from . import archive as archive_module
from . import candidate as candidate_module
from . import capacity as capacity_module
from . import envelope as envelope_module
from . import gitstate as gitstate_module
from . import prompt_policy as prompt_policy_module
from . import result as result_module
from . import run as run_module
from .lifecycle import (
    FINALIZATION_PUBLISH,
    LIFECYCLE_STANDARD,
    get_lifecycle,
    validate_finalization,
)
from .routing import load_validated_roster, resolve, route
from .transport import PromptLimitError, ensure_prompt_fits


def run(
    dispatcher: Any,
    phase_id: str,
    request: Any,
    lifecycle: str = LIFECYCLE_STANDARD,
    finalization_policy: str = FINALIZATION_PUBLISH,
) -> dict[str, Any]:
    from .dispatch import DispatchError

    dispatcher.lifecycle = get_lifecycle(lifecycle)
    dispatcher.finalization_policy = validate_finalization(finalization_policy)
    dispatcher.invocations = []
    dispatcher.telemetry_failures = []
    dispatcher.scan_rows = []
    dispatcher.prompt_policy_segments = []
    candidate_module.require_worktree(dispatcher.cwd)
    project = run_module.project_name(gitstate_module.repository_root(dispatcher.cwd))
    run_module.safe_component(phase_id, "phase id")
    roster = load_validated_roster(dispatcher.root)
    resolved = resolve(
        request, dispatcher.root, dispatcher.lifecycle.name,
        dispatcher.finalization_policy,
        roster=roster,
    )
    endpoints = route(
        request, dispatcher.lifecycle, root=dispatcher.root, roster=roster
    )
    dispatcher.display.run_started(
        project, phase_id, request.phase_type, request.execution_mode,
        endpoints, dry_run=True, lifecycle=dispatcher.lifecycle.name,
        finalization_policy=dispatcher.finalization_policy,
        review_count=dispatcher.lifecycle.expected_review_count,
    )
    directory = run_module.RunDirectory(dispatcher.run_root, project, phase_id)
    state = {
        "run_layout": dict(directory.run_layout),
        "run_id": directory.run_id,
        "project": project,
        "phase_id": phase_id,
        "run_directory": str(directory.path),
        "dry_run": True,
        "phase_type": request.phase_type,
        "execution_mode": request.execution_mode,
        "lifecycle": dispatcher.lifecycle.name,
        "finalization_policy": dispatcher.finalization_policy,
        "expected_stages": list(dispatcher.lifecycle.stage_names),
        "expected_provider_invocations": (
            dispatcher.lifecycle.expected_provider_invocations
        ),
        "expected_review_count": dispatcher.lifecycle.expected_review_count,
        "terminal_result_stage": dispatcher.lifecycle.terminal_result_stage,
        "cwd": str(dispatcher.cwd),
        "provider_invocations": 0,
        "stages_rendered": [dispatcher.lifecycle.stages[0].name],
        "stages_not_rendered": list(dispatcher.lifecycle.stage_names[1:]),
        "stages_not_rendered_reason": (
            "Later lifecycle stages may embed output of the stages before them. "
            "Those outputs do not exist until a real run produces them, so their "
            "prompts cannot be rendered here and no placeholder is written."
        ),
        "shadow": dispatcher._shadow_state(),
        "archive_path": str(directory.archive_path),
        "archive": archive_module.record(directory.archive_path),
        "effective_stage_routes": resolved.get("effective_stage_routes"),
        "route_transition": resolved.get("route_transition"),
        "prompt_policy": {
            "policy_version": prompt_policy_module.POLICY_VERSION,
            "sanitized": False,
            "total_removal_count": 0,
            "evidence_artifact": "prompt-policy.json",
        },
    }
    try:
        dispatcher.display.artifacts(directory.path)
        directory.write_json("request.json", request.as_dict())
        directory.write_json("resolved.json", resolved)
        directory.write_json("state.json", state)
        task_prompt = dispatcher._sanitize(
            directory, state, "request.prompt", request.prompt
        )
        first = dispatcher.lifecycle.stages[0]
        nonce = "0" * 32
        preflight_begin, preflight_end = result_module.markers(nonce)
        if first.name == "plan":
            first_prompt = dispatcher.plan_prompt(
                request, directory.run_id, task_prompt
            )
        elif first.name == "solo":
            first_prompt = dispatcher.continuation_prompt(
                first.name, request, directory.run_id,
                envelope_module.SOLO_ENVELOPE, [], include_task_prompt=True,
                contract=dispatcher._terminal_contract(
                    first.name, preflight_begin, preflight_end
                ),
                task_prompt=task_prompt,
            )
        else:
            first_prompt = dispatcher.continuation_prompt(
                first.name, request, directory.run_id,
                envelope_module.WORK_REVIEWED_PRODUCE_ENVELOPE, [],
                include_task_prompt=True, task_prompt=task_prompt,
            )
        try:
            capacity, dispatcher.stage_output_limits = (
                capacity_module.preflight_lifecycle_capacity(
                    dispatcher, request, directory.run_id, task_prompt, endpoints
                )
            )
            state["terminal_prompt_preflight"] = capacity
            ensure_prompt_fits(first.name, endpoints[first.name], first_prompt)
        except PromptLimitError as error:
            raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
        directory.write_bytes(f"{first.prefix}.prompt.md", first_prompt.data)
        dispatcher._scan(directory, first.prefix, first.name, first_prompt)
    except BaseException as error:
        state["dry_run_error"] = {
            "code": getattr(error, "code", type(error).__name__),
            "detail": str(error),
        }
        try:
            dispatcher._finalize(directory, state, write_result=False)
        except (archive_module.ArchiveError, OSError):
            dispatcher.display.finished(state, directory.path)
        raise
    archive_error = dispatcher._finalize(directory, state, write_result=False)
    if archive_error is not None:
        raise DispatchError(str(archive_error), archive_error.code)
    return state
