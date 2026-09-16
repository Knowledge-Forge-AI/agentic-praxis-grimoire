"""Dispatcher-owned push state around mechanically fixed Git operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import gitstate as gitstate_module


class PublicationError(RuntimeError):
    def __init__(self, code: str, detail: str, record: dict[str, Any]) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.record = record


def record(phase_commit: str | None = None) -> dict[str, Any]:
    return {
        "attempted": False,
        "status": "not_attempted",
        "remote": None,
        "remote_ref": None,
        "upstream_branch": None,
        "pre_push_remote_head": None,
        "preexisting_unpushed_commit_count": None,
        "phase_commit": phase_commit,
        "push_command_succeeded": None,
        "succeeded": False,
        "post_push_remote_head": None,
        "failure": None,
    }


def _push_target(root: Path, expected_branch: str | None = None) -> Any:
    target_fn = gitstate_module.push_target
    if expected_branch is None:
        return target_fn(root)
    try:
        import inspect
        sig = inspect.signature(target_fn)
        accepts_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD or p.name == "expected_branch"
            for p in sig.parameters.values()
        )
    except Exception:
        accepts_kw = True
    if accepts_kw:
        return target_fn(root, expected_branch=expected_branch)
    return target_fn(root)


def publish(
    root: Path,
    entry_head: str,
    phase_commit: str,
    display: Any,
    *,
    expected_branch: str | None = None,
) -> dict[str, Any]:
    """Publish one verified phase commit or raise with the full push record."""
    result = record(phase_commit)
    try:
        target = _push_target(root, expected_branch=expected_branch)
        result.update(
            remote=target.remote,
            remote_ref=target.remote_ref,
            upstream_branch=target.upstream_branch,
        )
        pre_head = gitstate_module.remote_head(root, target)
        result["pre_push_remote_head"] = pre_head
        count = gitstate_module.preexisting_unpushed_count(root, pre_head, entry_head)
        result["preexisting_unpushed_commit_count"] = count
        result["attempted"] = True
        result["status"] = "attempting"
        display.push_starting(target.remote, target.remote_ref, count)
        post_head = gitstate_module.push_verified(root, target, phase_commit)
        result["post_push_remote_head"] = post_head
        result["push_command_succeeded"] = True
        result["succeeded"] = True
        result["status"] = "succeeded"
        display.push_finished(True, target.remote, target.remote_ref, post_head)
        return result
    except gitstate_module.GitPushError as error:
        result["post_push_remote_head"] = error.post_push_remote_head
        result["push_command_succeeded"] = error.command_succeeded
        result["failure"] = {"code": error.code, "detail": error.detail}
        result["status"] = "failed"
    except gitstate_module.GitStateError as error:
        result["failure"] = {"code": error.code, "detail": error.detail}
        result["status"] = "failed"

    failure = result["failure"]
    display.push_finished(
        False,
        result.get("remote") or "unresolved",
        result.get("remote_ref") or "unresolved",
        result.get("post_push_remote_head"),
    )
    raise PublicationError(failure["code"], failure["detail"], result)


def publish_or_reuse(
    root: Path,
    entry_head: str,
    phase_commit: str,
    display: Any,
    *,
    expected_branch: str | None = None,
) -> dict[str, Any]:
    """Resolve uncertain resumed publication state before issuing any push."""
    result = record(phase_commit)
    try:
        target = _push_target(root, expected_branch=expected_branch)
        remote_head = gitstate_module.remote_head(root, target)
        result.update(
            remote=target.remote,
            remote_ref=target.remote_ref,
            upstream_branch=target.upstream_branch,
            pre_push_remote_head=remote_head,
        )
        if remote_head == phase_commit:
            result.update(
                attempted=False,
                status="succeeded",
                succeeded=True,
                post_push_remote_head=remote_head,
                push_command_succeeded=None,
                already_published=True,
            )
            display.push_finished(True, target.remote, target.remote_ref, remote_head)
            return result
        # This proves the remote still belongs to the normal safe publication
        # topology before publish() performs its own fresh pre-push readback.
        gitstate_module.preexisting_unpushed_count(root, remote_head, entry_head)
    except gitstate_module.GitStateError as error:
        result["failure"] = {
            "code": "RESUME_PUSH_STATE_MISMATCH", "detail": error.detail,
        }
        result["status"] = "failed"
        raise PublicationError(
            "RESUME_PUSH_STATE_MISMATCH", error.detail, result
        ) from error
    return publish(
        root,
        entry_head,
        phase_commit,
        display,
        expected_branch=expected_branch,
    )
