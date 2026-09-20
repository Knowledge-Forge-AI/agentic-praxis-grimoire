#!/usr/bin/env python3
"""Launch Claude with a version-controlled operating profile."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
from typing import Any, BinaryIO, Callable, NamedTuple, NoReturn, Sequence

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from claude_live_renderer import (
    LivePresentation,
    write_all,
)
from claude_profile_directories import (
    HOST_DIRECTORY_TOKENS as HOST_DIRECTORIES,
    SCRATCH_DIRECTORY_TOKENS as SCRATCH_DIRECTORIES,
    ProfileError, resolve_profile_directories,
)


PRIMARY_ROLE = "primary"
REVIEW_ROLE = "review"
# The host role is a scope, not a policy fork: it runs the one canonical CLI
# policy with ambient user/project/local sources excluded, so the engineering
# role's deny rules cannot merge back in and make the role unusable.
CANONICAL_SETTINGS_FILE = "settings.json"
ISOLATED_SETTING_SOURCES = ""
READ_ONLY_TOOLS = ("Read", "Glob", "Grep", "WebFetch", "WebSearch")
READ_ONLY_WRAPPER_FLAG = "--read-only"
WORKER_FACADE_MARKER = "AGENT_CENTRAL_WORKER_FACADE"
WORKER_FACADE_SYSTEM_PROMPT = (
    "Use the fixed Agent-Central worker MCP tools when a bounded delegation is "
    "useful. A read-only worker task is authorized read-only inspection; the "
    "facade's ledger and outbox writes are launcher-owned orchestration "
    "bookkeeping and do not grant product mutation. No plan-file workflow is "
    "needed for a read-only worker task. Stay within the current permission mode "
    "and explicitly exposed tools. Bounded waits return control for a decision; "
    "do not poll indefinitely. Use outcome with evidence to record task disposition; "
    "this never proves cleanup. Select only an allowed worker kind. On a stalled "
    "or erroring task, use abandon with a reason, retain partial work, and wait "
    "for proven cleanup before a replacement writer. A replacement must adopt "
    "the observed partial state and acceptance criteria, not blindly replay. "
    "Explicit quota exhaustion pauses that pool; do not retry or probe resets. "
    "Finish directly or use another allowed pool at its unchanged cap."
)


class ProfileContract(NamedTuple):
    model_role: str
    effort: str
    permission_mode: str | None = None
    additional_directories: list[str] | None = None
    isolated_settings: bool = False

    def expected_keys(self) -> frozenset[str]:
        keys = {"modelRole", "effort"}
        if self.permission_mode is not None:
            keys.add("permissionMode")
        if self.additional_directories is not None:
            keys.add("additionalDirectories")
        return frozenset(keys)


PROFILE_CONTRACTS = {
    "implementation-primary": ProfileContract(PRIMARY_ROLE, "medium"),
    "implementation-review": ProfileContract(REVIEW_ROLE, "medium", "plan"),
    "architecture-docs-primary": ProfileContract(
        PRIMARY_ROLE, "high", "acceptEdits", SCRATCH_DIRECTORIES
    ),
    "fable-architecture-docs-primary": ProfileContract(
        REVIEW_ROLE, "high", "acceptEdits", SCRATCH_DIRECTORIES
    ),
    "architecture-docs-review": ProfileContract(REVIEW_ROLE, "high", "plan"),
    # NORMAL implementation/docs review profiles are stage-specific and
    # deliberately repo-scoped. They accept no edits.
    "normal-plan-review": ProfileContract(REVIEW_ROLE, "high", "plan"),
    "normal-final-review": ProfileContract(PRIMARY_ROLE, "high", "plan"),
    # NORMAL sysadmin reviews preserve host-read scope and isolated settings.
    "normal-sysadmin-plan-review": ProfileContract(
        REVIEW_ROLE,
        "high",
        permission_mode="plan",
        additional_directories=HOST_DIRECTORIES,
        isolated_settings=True,
    ),
    "sysadmin-primary": ProfileContract(
        PRIMARY_ROLE,
        "high",
        "acceptEdits",
        HOST_DIRECTORIES,
        isolated_settings=True,
    ),
    # A reviewer reads the host; it does not need edits accepted on its behalf.
    "sysadmin-review": ProfileContract(
        REVIEW_ROLE,
        "high",
        permission_mode="plan",
        additional_directories=HOST_DIRECTORIES,
        isolated_settings=True,
    ),
    "sysadmin-opus-review": ProfileContract(
        PRIMARY_ROLE,
        "high",
        permission_mode="plan",
        additional_directories=HOST_DIRECTORIES,
        isolated_settings=True,
    ),
}
SUPPORTED_PROFILES = frozenset(PROFILE_CONTRACTS)
# A result ends substantive work only when nothing else is outstanding; anything
# after such a result is teardown. These bounds apply only then, never to
# productive work.
POST_RESULT_GRACE_SECONDS = 10.0
POST_RESULT_KILL_GRACE_SECONDS = 3.0
STREAM_DRAIN_GRACE_SECONDS = 3.0
# A result emitted while background tasks run is only a turn result: Claude
# resumes once the tasks report in. Resuming means a fresh inference request, so
# this bound must be far looser than the MCP-teardown bound above.
BACKGROUND_RESULT_RESUME_GRACE_SECONDS = 60.0
# Claude's result event carries the whole final response, so this bound must sit
# far above any reachable transcript: dropping the record would silently restore
# the unbounded wait this observer exists to prevent.
MAX_RESULT_RECORD_BYTES = 16 * 1024 * 1024
_EXIT_POLL_SECONDS = 0.05

# No candidate for completion: Claude owns the session and must not be bounded.
PHASE_RUNNING = "running"
# A result arrived with nothing outstanding; ordinary teardown bounding applies.
PHASE_TERMINAL = "terminal"
# A turn result's background tasks all reported in; Claude should resume soon.
PHASE_SETTLING = "settling"

# Every status Claude Code emits for background work that will never run again.
# A status outside this set leaves the task active, because inventing task
# completion is what lets the wrapper invent session completion. The accepted
# cost: a task that never reports an allowlisted status holds the session open
# indefinitely. That is deliberate -- an operator can interrupt a session that
# waits too long, but cannot recover one that was killed while still working.
# Widen this set rather than loosening the rule if Claude Code adds a status.
TERMINAL_TASK_STATUSES = frozenset(
    {
        "completed",
        "killed",
        "stopped",
        "failed",
        "error",
        "cancelled",
        "canceled",
        "timed_out",
        "timeout",
    }
)
# Event types that can only be produced by Claude doing more work. Task
# lifecycle events are deliberately excluded: they report on work already
# accounted for and must drive the settle timer instead of resetting it.
CONTINUATION_EVENT_TYPES = frozenset({"assistant", "user"})


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_profile(root: Path, name: str) -> dict[str, Any]:
    if name == "doctor":
        raise ProfileError("reserved profile name: doctor")
    if name not in SUPPORTED_PROFILES:
        raise ProfileError(f"unsupported profile: {name}")
    path = root / "profiles" / f"{name}.json"
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
        )
    except (OSError, json.JSONDecodeError) as error:
        raise ProfileError(f"invalid profile {name}: {error}") from error
    if not isinstance(value, dict):
        raise ProfileError(f"profile must be an object: {name}")
    contract = PROFILE_CONTRACTS[name]
    expected_keys = contract.expected_keys()
    if set(value) != expected_keys:
        raise ProfileError(
            f"profile keys must be exactly {sorted(expected_keys)}: {name}"
        )
    if value["modelRole"] != contract.model_role:
        raise ProfileError(f"profile modelRole must be {contract.model_role}: {name}")
    if value["effort"] != contract.effort:
        raise ProfileError(f"invalid profile effort: {name}")
    if (
        contract.permission_mode is not None
        and value["permissionMode"] != contract.permission_mode
    ):
        raise ProfileError(f"invalid profile permission mode: {name}")
    if (
        contract.additional_directories is not None
        and value["additionalDirectories"] != contract.additional_directories
    ):
        raise ProfileError(f"invalid profile additional directories: {name}")
    return value


class ResolvedProfile(NamedTuple):
    profile_name: str
    model_role: str
    resolved_model_id: str
    minimum_version: str | None
    adaptive_thinking: bool
    catalog_provenance: dict[str, Any]
    source_profile: dict[str, Any]


def resolve_profile(root: Path, name: str) -> ResolvedProfile:
    source_profile = load_profile(root, name)
    contract = PROFILE_CONTRACTS[name]
    from claude_model_catalog import load_catalog, resolve_role

    try:
        catalog = load_catalog(root)
        role_info = resolve_role(catalog, contract.model_role)
    except Exception as error:
        raise ProfileError(
            f"failed to resolve model role for {name}: {error}"
        ) from error
    return ResolvedProfile(
        profile_name=name,
        model_role=contract.model_role,
        resolved_model_id=role_info["resolved_model_id"],
        minimum_version=role_info["minimum_claude_code_version"],
        adaptive_thinking=role_info["adaptive_thinking"],
        catalog_provenance=role_info["catalog"],
        source_profile=source_profile,
    )


def canonical_settings_path(root: Path) -> Path:
    from controller_generation import operator_root
    root = operator_root(root.parent) / root.name
    path = root / CANONICAL_SETTINGS_FILE
    if not path.is_file() or path.is_symlink():
        raise ProfileError(
            f"canonical settings payload must be a regular non-symlink file: {path}"
        )
    return path


def reject_resume_flags(arguments: Sequence[str]) -> None:
    prohibited = {"--resume", "-r", "--continue", "-c", "--teleport"}
    prohibited_prefixes = ("--resume=", "-r=", "--continue=", "-c=", "--teleport=")
    for argument in arguments:
        if argument == "--":
            return
        if argument in prohibited or argument.startswith(prohibited_prefixes):
            raise ProfileError(f"resume/continue flag cannot be used: {argument}")


def reject_profile_overrides(
    profile_name: str, arguments: Sequence[str]
) -> None:
    contract = PROFILE_CONTRACTS[profile_name]
    # This is a denylist: a future CLI alias or short form for any of these
    # options would pass through unprotected. Re-check it against
    # `claude --help` whenever the CLI is upgraded.
    protected = {
        "--model",
        "--effort",
        "--dangerously-skip-permissions",
        "--allow-dangerously-skip-permissions",
        "--tool-choice",
        "--thinking",
        "--thinking-budget",
        "--thinking-mode",
    }
    valued = {
        "--model",
        "--effort",
        "--tool-choice",
        "--thinking",
        "--thinking-budget",
        "--thinking-mode",
    }
    if contract.permission_mode is not None:
        valued.add("--permission-mode")
    if contract.additional_directories is not None:
        valued.add("--add-dir")
    if contract.isolated_settings:
        valued.update(("--settings", "--setting-sources", "--managed-settings"))
    protected |= valued
    protected_prefixes = tuple(f"{flag}=" for flag in valued)
    for argument in arguments:
        if argument == "--":
            return
        if argument in protected or argument.startswith(protected_prefixes):
            raise ProfileError(f"profile flag cannot be overridden: {argument}")


def _load_worker_facade(
    root: Path,
    profile_name: str,
    *,
    read_only: bool,
    no_tools: bool,
) -> Any | None:
    """Load an optional active-parent facade without blocking Claude startup."""
    if no_tools or os.environ.get(WORKER_FACADE_MARKER) != "1":
        return None
    expected_family = (
        "claude_opus"
        if PROFILE_CONTRACTS[profile_name].model_role == PRIMARY_ROLE
        else "claude_fable"
    )
    expected_authority = "read_only" if read_only else "mutation_capable"
    try:
        from agent_workers.facade_context import load_launcher_context

        # ``bin/claude-profile`` resolves profiles from the ``claude/``
        # projection, while the dispatcher freezes capability provenance at
        # the repository root.  Synthetic launcher roots used by tests may
        # carry their own executable, so prefer the projection when it does.
        source_root = root
        if not (root / "bin" / "agent-worker-mcp").is_file():
            parent_entrypoint = root.parent / "bin" / "agent-worker-mcp"
            if parent_entrypoint.is_file():
                source_root = root.parent
        context = load_launcher_context(
            source_root,
            expected_parent_family=expected_family,
            expected_task_authority=expected_authority,
        )
        # Check the source-owned executable before constructing Claude's argv;
        # an absent or damaged optional facade must keep ordinary launch alive.
        context.config()
        return context
    except Exception as error:
        # The worker path is an enhancement.  An absent, damaged, stale, or
        # mismatched facade must leave ordinary Claude execution available.
        print(
            f"claude-profile: worker facade unavailable ({type(error).__name__})",
            file=sys.stderr,
        )
        return None


def read_only_contract(
    root: Path,
    profile_name: str,
    *,
    no_tools: bool = False,
    worker_facade: Any | None = None,
    headless: bool = False,
) -> dict[str, Any]:
    """Validate and describe the launcher-owned read-only overlay."""
    profile = load_profile(root, profile_name)
    if not READ_ONLY_TOOLS or any(tool in {"Bash", "Write", "Edit"} for tool in READ_ONLY_TOOLS):
        raise ProfileError("read-only tool contract is not enforceable")
    tools = [] if no_tools else list(READ_ONLY_TOOLS)
    if worker_facade is not None and not no_tools:
        tools.extend(worker_facade_tool_names(worker_facade))
    contract: dict[str, Any] = {
        "enforced": True,
        "permission_mode": (
            "default" if headless and worker_facade is not None and not no_tools else "plan"
        ),
        "profile_permission_mode": profile.get("permissionMode"),
        "headless_worker_permission_mode": "default",
        "permission_mode_selection": "default only for headless with validated worker facade; otherwise plan",
        "task_authority": "read_only",
        "tools": tools,
        "setting_sources": ISOLATED_SETTING_SOURCES,
        "slash_commands": False,
        "chrome": False,
        # Routing asks for this contract before a parent ledger exists.  The
        # launcher still emits a strict-empty config for ordinary no-worker
        # runs, while an active validated parent receives the fixed facade.
        "mcp": (
            "stdio"
            if worker_facade is not None and not no_tools
            else "strict-launcher-owned-conditional"
        ),
    }
    if worker_facade is not None and not no_tools:
        from agent_workers.facade_context import WorkerFacadeContext

        if isinstance(worker_facade, WorkerFacadeContext):
            contract["facade_evidence"] = {
                "serena": worker_facade.serena_evidence(),
            }
    return contract


def worker_facade_tool_names(_worker_facade: Any) -> list[str]:
    """Return the fixed MCP tool names exposed by a validated facade."""
    from agent_workers.facade_context import MCP_TOOL_NAMES, WorkerFacadeContext

    if isinstance(_worker_facade, WorkerFacadeContext):
        return list(_worker_facade.mcp_tool_names())
    return list(MCP_TOOL_NAMES)


def extract_wrapper_flags(
    arguments: Sequence[str],
) -> tuple[list[str], bool, bool]:
    cleaned: list[str] = []
    read_only = False
    no_tools = False
    for index, argument in enumerate(arguments):
        if argument == "--":
            cleaned.extend(arguments[index:])
            break
        if argument == READ_ONLY_WRAPPER_FLAG:
            if read_only:
                raise ProfileError("--read-only may be supplied only once")
            read_only = True
        elif argument == "--no-tools":
            if no_tools:
                raise ProfileError("--no-tools may be supplied only once")
            no_tools = True
        else:
            cleaned.append(argument)
    return cleaned, read_only, no_tools


def extract_read_only(arguments: Sequence[str]) -> tuple[list[str], bool]:
    cleaned, read_only, _no_tools = extract_wrapper_flags(arguments)
    return cleaned, read_only


def reject_read_only_overrides(arguments: Sequence[str]) -> None:
    valued = {
        "--permission-mode", "--tools", "--allowedTools", "--allowed-tools",
        "--disallowedTools", "--disallowed-tools", "--setting-sources",
        "--mcp-config", "--agent", "--agents", "--plugin-dir", "--plugin-url",
        "--append-system-prompt", "--append-system-prompt-file",
    }
    protected = valued | {
        "--chrome", "--dangerously-skip-permissions",
        "--allow-dangerously-skip-permissions",
    }
    prefixes = tuple(f"{flag}=" for flag in valued)
    for argument in arguments:
        if argument == "--":
            return
        if argument in protected or argument.startswith(prefixes):
            raise ProfileError(f"read-only flag cannot be overridden: {argument}")


def reject_worker_facade_overrides(arguments: Sequence[str]) -> None:
    """Keep launcher-owned facade identity and guidance single-valued."""
    for argument in arguments:
        if argument == "--":
            return
        if argument in ("--append-system-prompt", "--append-system-prompt-file") or argument.startswith(
            ("--append-system-prompt=", "--append-system-prompt-file=")
        ):
            raise ProfileError(
                "worker facade system prompt cannot be overridden: "
                f"{argument}"
            )
        if argument == "--mcp-config" or argument.startswith("--mcp-config="):
            raise ProfileError("worker facade MCP configuration cannot be overridden")
        if (
            argument in ("--allowed-tools", "--allowedTools")
            or argument.startswith(("--allowed-tools=", "--allowedTools="))
        ):
            raise ProfileError("worker facade allowed tools cannot be overridden")


def parse_wrapper_arguments(
    arguments: Sequence[str],
) -> tuple[list[str], Path | None, str, Path | None]:
    claude_arguments: list[str] = []
    live_log: Path | None = None
    live_display = "auto"
    live_display_seen = False
    require_artifact: Path | None = None
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            claude_arguments.extend(arguments[index:])
            break
        if argument == "--live-log":
            if live_log is not None:
                raise ProfileError("--live-log may be supplied only once")
            index += 1
            if index >= len(arguments) or arguments[index].startswith("-"):
                raise ProfileError("--live-log requires a value")
            live_log = Path(arguments[index])
        elif argument.startswith("--live-log="):
            raise ProfileError("--live-log requires a separate path value")
        elif argument == "--live-display":
            if live_display_seen:
                raise ProfileError("--live-display may be supplied only once")
            live_display_seen = True
            index += 1
            if index >= len(arguments) or arguments[index].startswith("-"):
                raise ProfileError("--live-display requires a value")
            live_display = arguments[index]
            if live_display not in {"auto", "human", "raw"}:
                raise ProfileError("--live-display must be auto, human, or raw")
        elif argument.startswith("--live-display="):
            raise ProfileError("--live-display requires a separate value")
        elif argument == "--require-artifact":
            if require_artifact is not None:
                raise ProfileError("--require-artifact may be supplied only once")
            index += 1
            if index >= len(arguments) or arguments[index].startswith("-"):
                raise ProfileError("--require-artifact requires a value")
            require_artifact = Path(arguments[index])
        elif argument.startswith("--require-artifact="):
            raise ProfileError("--require-artifact requires a separate path value")
        else:
            claude_arguments.append(argument)
        index += 1

    if live_log is None:
        if live_display_seen:
            raise ProfileError("--live-display requires --live-log")
        if require_artifact is not None:
            raise ProfileError("--require-artifact requires --live-log")
        return claude_arguments, None, live_display, None

    option_arguments = claude_arguments
    if "--" in option_arguments:
        option_arguments = option_arguments[: option_arguments.index("--")]
    if not any(
        argument in {"--print", "-p"} or argument.startswith("--print=")
        for argument in option_arguments
    ):
        raise ProfileError("--live-log requires --print or -p")
    if any(
        argument == "--output-format" or argument.startswith("--output-format=")
        for argument in option_arguments
    ):
        raise ProfileError("--output-format cannot be supplied with --live-log")

    live_arguments: list[str] = []
    if "--verbose" not in option_arguments:
        live_arguments.append("--verbose")
    live_arguments.extend(("--output-format", "stream-json"))
    live_arguments.extend(claude_arguments)
    return live_arguments, live_log, live_display, require_artifact


def select_live_display(requested: str, stdout: Any) -> str:
    if requested == "auto":
        return "human" if stdout.isatty() else "raw"
    return requested


def open_private_log(path: Path) -> BinaryIO:
    try:
        previous_umask = os.umask(0o077)
        try:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        finally:
            os.umask(previous_umask)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        flags |= getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise OSError("destination is not a regular file")
            os.fchmod(descriptor, 0o600)
            return os.fdopen(descriptor, "wb", buffering=0)
        except BaseException:
            os.close(descriptor)
            raise
    except OSError as error:
        raise ProfileError(f"cannot maintain live log {path}: {error}") from error


class TerminalResultObserver:
    """Track session completion directly in the authoritative stream.

    A `result` event is only a candidate for completion. Claude emits one at the
    end of every turn, including a turn that parked work in a background task and
    will resume when that task reports in. Treating the first result as terminal
    kills live sessions, so a result counts only when no background task is
    outstanding, and any later work withdraws it again.

    Presentation may be disabled or may fail; teardown bounding must not.
    """

    def __init__(
        self,
        max_record_bytes: int = MAX_RESULT_RECORD_BYTES,
        notify: Callable[[str], None] | None = None,
    ) -> None:
        self.max_record_bytes = max_record_bytes
        self._buffer = bytearray()
        self._discarding_oversized = False
        self._notify = notify
        self._lock = threading.Lock()
        self._phase = PHASE_RUNNING
        self._generation = 0
        self._error = False
        self._active_tasks: set[str] = set()
        self._provisional = False
        self._warned_untracked_task = False

    @property
    def seen(self) -> bool:
        with self._lock:
            return self._phase == PHASE_TERMINAL

    @property
    def is_error(self) -> bool:
        with self._lock:
            return self._error

    @property
    def active_tasks(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._active_tasks)

    def phase(self) -> tuple[str, int]:
        """Read phase and generation together so a waiter cannot act on a torn pair."""
        with self._lock:
            return self._phase, self._generation

    def _announce(self, message: str) -> None:
        if self._notify is not None:
            self._notify(message)

    def _enter(self, phase: str) -> None:
        """Caller holds the lock. Generation moves so waiters abandon stale bounds."""
        self._phase = phase
        self._generation += 1

    def feed(self, chunk: bytes) -> None:
        remaining = chunk
        while remaining:
            newline = remaining.find(b"\n")
            if self._discarding_oversized:
                if newline < 0:
                    return
                self._discarding_oversized = False
                remaining = remaining[newline + 1 :]
                continue
            if newline < 0:
                if len(self._buffer) + len(remaining) > self.max_record_bytes:
                    self._buffer.clear()
                    self._discarding_oversized = True
                else:
                    self._buffer.extend(remaining)
                return
            fragment = remaining[:newline]
            if len(self._buffer) + len(fragment) > self.max_record_bytes:
                self._buffer.clear()
            else:
                self._buffer.extend(fragment)
                self._inspect_buffered_record()
            remaining = remaining[newline + 1 :]

    def _inspect_buffered_record(self) -> None:
        record = bytes(self._buffer)
        self._buffer.clear()
        if not record.strip():
            return
        try:
            event = json.loads(record.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        if event_type == "result":
            self._observe_result(event)
        elif event_type == "system":
            subtype = event.get("subtype")
            if subtype == "task_started":
                self._observe_task_started(event)
            elif subtype in ("task_updated", "task_notification"):
                self._observe_task_status(event)
            elif subtype == "init":
                self._observe_continuation()
        elif event_type in CONTINUATION_EVENT_TYPES:
            self._observe_continuation()

    def _observe_result(self, event: dict[str, Any]) -> None:
        is_error = event.get("is_error") is True or event.get("subtype") != "success"
        with self._lock:
            self._error = is_error
            outstanding = len(self._active_tasks)
            if not outstanding:
                self._provisional = False
                self._enter(PHASE_TERMINAL)
                return
            # A turn result, not a session result: Claude is waiting on its own
            # background work and will resume once that work reports in.
            self._provisional = True
            self._enter(PHASE_RUNNING)
        plural = "" if outstanding == 1 else "s"
        self._announce(
            f"result received with {outstanding} background task{plural} still "
            "active; waiting for continuation"
        )

    @staticmethod
    def _task_identity(event: dict[str, Any]) -> str | None:
        task_id = event.get("task_id")
        if isinstance(task_id, str) and task_id:
            return task_id
        return None

    @staticmethod
    def _task_status(event: dict[str, Any]) -> str | None:
        status = event.get("status")
        if not isinstance(status, str):
            patch = event.get("patch")
            status = patch.get("status") if isinstance(patch, dict) else None
        return status.lower() if isinstance(status, str) else None

    def _observe_task_started(self, event: dict[str, Any]) -> None:
        task_id = self._task_identity(event)
        if task_id is None:
            # An untrackable task cannot hold a result provisional, so the next
            # result would look terminal and the session could be killed mid-run.
            # Say so rather than failing this open in silence.
            with self._lock:
                first = not self._warned_untracked_task
                self._warned_untracked_task = True
            if first:
                self._announce(
                    "background task started without a task id; it cannot be "
                    "tracked and will not hold a result provisional"
                )
            return
        with self._lock:
            self._active_tasks.add(task_id)
        self._observe_continuation()

    def _observe_task_status(self, event: dict[str, Any]) -> None:
        task_id = self._task_identity(event)
        status = self._task_status(event)
        if task_id is None or status not in TERMINAL_TASK_STATUSES:
            return
        with self._lock:
            if task_id not in self._active_tasks:
                # Already retired, or never ours. Either way nothing else may be
                # retired in its place.
                return
            self._active_tasks.discard(task_id)
            if self._active_tasks or not self._provisional:
                return
            if self._phase != PHASE_RUNNING:
                return
            self._enter(PHASE_SETTLING)
        self._announce(
            "background tasks completed after provisional result; waiting for "
            "Claude continuation"
        )

    def _observe_continuation(self) -> None:
        with self._lock:
            if self._phase == PHASE_RUNNING and not self._provisional:
                return
            previous = self._phase
            was_provisional = self._provisional
            self._provisional = False
            self._enter(PHASE_RUNNING)
        if previous == PHASE_TERMINAL:
            self._announce(
                "Claude continued after its result; that result is no longer "
                "final and a fresh result is required"
            )
        elif was_provisional or previous == PHASE_SETTLING:
            self._announce(
                "Claude continued after provisional result; final result still "
                "pending"
            )


def terminate_process_group(process: subprocess.Popen[bytes], signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


def mirror_stream(
    source: BinaryIO,
    terminal: BinaryIO,
    durable: BinaryIO,
    process: subprocess.Popen[bytes],
    failures: list[tuple[str, Exception]],
    channel: str,
) -> None:
    try:
        while chunk := source.read(65536):
            write_all(durable, chunk)
            write_all(terminal, chunk)
            terminal.flush()
    except Exception as error:
        failures.append((channel, error))
        terminate_process_group(process, signal.SIGTERM)


def mirror_stdout(
    source: BinaryIO,
    terminal: BinaryIO,
    warning_stream: BinaryIO,
    durable: BinaryIO,
    process: subprocess.Popen[bytes],
    failures: list[tuple[str, Exception]],
    display: str,
    profile_name: str,
    observer: TerminalResultObserver,
) -> None:
    presentation = LivePresentation(
        display, profile_name, terminal, warning_stream
    )
    try:
        while chunk := source.read(65536):
            write_all(durable, chunk)
            observer.feed(chunk)
            presentation.feed(chunk)
        presentation.finish()
    except Exception as error:
        failures.append(("stdout", error))
        terminate_process_group(process, signal.SIGTERM)


def await_completion(
    process: subprocess.Popen[bytes],
    observer: TerminalResultObserver,
    warn: Callable[[str], None],
    grace: float,
    kill_grace: float,
    settle_grace: float,
) -> tuple[int, bool]:
    """Wait for Claude, bounding only the states in which it owes nothing more."""
    while True:
        phase, generation = observer.phase()
        if phase == PHASE_RUNNING:
            try:
                return process.wait(timeout=_EXIT_POLL_SECONDS), False
            except subprocess.TimeoutExpired:
                continue
        limit = grace if phase == PHASE_TERMINAL else settle_grace
        deadline = time.monotonic() + limit
        superseded = False
        while time.monotonic() < deadline:
            try:
                return process.wait(timeout=_EXIT_POLL_SECONDS), False
            except subprocess.TimeoutExpired:
                pass
            if observer.phase()[1] != generation:
                superseded = True
                break
        if superseded:
            continue
        if phase == PHASE_TERMINAL:
            warn(
                "terminal result received; terminated lingering Claude/MCP "
                f"process group after {limit:g}s grace"
            )
        else:
            warn(
                "background tasks completed but Claude never resumed after its "
                "provisional result; terminated lingering Claude/MCP process "
                f"group after {limit:g}s grace"
            )
        for signum in (signal.SIGTERM, signal.SIGKILL):
            terminate_process_group(process, signum)
            try:
                return process.wait(timeout=kill_grace), True
            except subprocess.TimeoutExpired:
                continue
        return -signal.SIGKILL, True


def describe_missing_artifact(path: Path) -> str | None:
    """Report why a declared response artifact does not satisfy its contract."""
    try:
        info = os.stat(path)
    except OSError as error:
        return f"required response artifact is unusable: {path}: {error}"
    if not stat.S_ISREG(info.st_mode):
        return f"required response artifact is not a regular file: {path}"
    if info.st_size == 0:
        return f"required response artifact is empty: {path}"
    return None


def run_live(
    executable: str,
    argv: Sequence[str],
    environment: dict[str, str],
    log_path: Path,
    display: str,
    profile_name: str,
    require_artifact: Path | None = None,
) -> int:
    stdout_log = open_private_log(log_path)
    try:
        stderr_log = open_private_log(Path(f"{log_path}.stderr.log"))
    except BaseException:
        stdout_log.close()
        raise

    child: list[subprocess.Popen[bytes] | None] = [None]
    received_signals: list[int] = []
    previous_handlers: dict[int, Any] = {}

    def warn(message: str) -> None:
        payload = f"claude-profile: {message}\n".encode("utf-8")
        for stream in (sys.stderr.buffer, stderr_log):
            try:
                write_all(stream, payload)
                stream.flush()
            except (OSError, ValueError):
                pass

    observer = TerminalResultObserver(notify=warn)

    def forward_signal(signum: int, _frame: Any) -> None:
        received_signals.append(signum)
        if child[0] is not None:
            terminate_process_group(child[0], signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, forward_signal)

    failures: list[tuple[str, Exception]] = []
    lingering = False
    artifact_problem: str | None = None
    try:
        try:
            process = subprocess.Popen(
                argv,
                executable=executable,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                start_new_session=True,
            )
        except OSError as error:
            raise ProfileError(f"cannot launch claude: {error}") from error
        child[0] = process
        for signum in received_signals:
            terminate_process_group(process, signum)
        assert process.stdout is not None
        assert process.stderr is not None
        threads = [
            threading.Thread(
                target=mirror_stdout,
                args=(
                    process.stdout,
                    sys.stdout.buffer,
                    sys.stderr.buffer,
                    stdout_log,
                    process,
                    failures,
                    display,
                    profile_name,
                    observer,
                ),
                name="claude-profile-stdout",
                daemon=True,
            ),
            threading.Thread(
                target=mirror_stream,
                args=(process.stderr, sys.stderr.buffer, stderr_log, process, failures, "stderr"),
                name="claude-profile-stderr",
                daemon=True,
            ),
        ]
        for thread in threads:
            thread.start()
        returncode, forced_cleanup = await_completion(
            process,
            observer,
            warn,
            POST_RESULT_GRACE_SECONDS,
            POST_RESULT_KILL_GRACE_SECONDS,
            BACKGROUND_RESULT_RESUME_GRACE_SECONDS,
        )
        terminate_process_group(process, signal.SIGTERM)
        # A descendant that left the process group keeps the inherited pipe write
        # end open, so draining must be bounded too or the wait simply moves here.
        for thread in threads:
            thread.join(timeout=STREAM_DRAIN_GRACE_SECONDS)
        lingering = any(thread.is_alive() for thread in threads)
        if lingering:
            warn(
                "live log readers still blocked by an escaped descendant; "
                "raw logs remain authoritative"
            )
        for channel, durable in (("stdout", stdout_log), ("stderr", stderr_log)):
            try:
                durable.flush()
                os.fsync(durable.fileno())
            except OSError as error:
                failures.append((channel, error))
        # An operator signal already decided this run; a report the operator
        # interrupted is not a broken artifact contract.
        if require_artifact is not None and not received_signals:
            artifact_problem = describe_missing_artifact(require_artifact)
            if artifact_problem is not None:
                warn(artifact_problem)
    finally:
        for signum, previous_handler in previous_handlers.items():
            signal.signal(signum, previous_handler)
        if not lingering:
            stdout_log.close()
            stderr_log.close()

    status = 128 - returncode if returncode < 0 else returncode
    if forced_cleanup and not received_signals:
        status = 1 if observer.is_error else 0
    if artifact_problem is not None:
        status = status or 1
    if failures:
        channels = ", ".join(channel for channel, _error in failures)
        print(
            f"claude-profile: live logging failed for {channels}",
            file=sys.stderr,
            flush=True,
        )
        return status or 1
    return status


def launch(
    root: Path, profile_name: str, arguments: Sequence[str]
) -> int | NoReturn:
    reject_resume_flags(arguments)
    resolved = resolve_profile(root, profile_name)
    arguments, wrapper_read_only, no_tools = extract_wrapper_flags(arguments)
    read_only = (
        wrapper_read_only
        or PROFILE_CONTRACTS[profile_name].permission_mode == "plan"
    )
    if no_tools and not read_only:
        raise ProfileError("--no-tools requires an effective read-only profile")
    reject_profile_overrides(profile_name, arguments)
    worker_facade = _load_worker_facade(
        root,
        profile_name,
        read_only=read_only,
        no_tools=no_tools,
    )
    if worker_facade is not None and not no_tools:
        reject_worker_facade_overrides(arguments)
    options = list(arguments)
    if "--" in options:
        options = options[:options.index("--")]
    headless = any(arg in {"--print", "-p"} or arg.startswith("--print=") for arg in options)
    if read_only:
        overlay = read_only_contract(
            root,
            profile_name,
            no_tools=no_tools,
            worker_facade=worker_facade,
            headless=headless,
        )
        reject_read_only_overrides(arguments)
    claude_arguments, live_log, requested_display, require_artifact = (
        parse_wrapper_arguments(arguments)
    )
    executable = shutil.which("claude")
    if executable is None:
        raise ProfileError("claude executable not found")

    if resolved.minimum_version is not None:
        from claude_model_catalog import is_version_compatible, probe_claude_version

        observed_version, probe_status = probe_claude_version(executable)
        if probe_status != "available" or observed_version is None:
            raise ProfileError(
                f"profile {profile_name} requires Claude Code >= {resolved.minimum_version}, "
                "but Claude Code executable version is unavailable"
            )
        if not is_version_compatible(observed_version, resolved.minimum_version):
            raise ProfileError(
                f"profile {profile_name} requires Claude Code >= {resolved.minimum_version}, "
                f"but observed version is {observed_version}"
            )

    environment = os.environ.copy()
    environment.pop("CLAUDE_CODE_EFFORT_LEVEL", None)
    environment.pop("CLAUDE_EFFORT", None)
    if os.environ.get(WORKER_FACADE_MARKER) == "1":
        # The MCP child receives a complete fixed context in its config env.
        # Keep descriptive fields out of Claude's ambient environment.  A
        # writable parent also uses the same inherited ID/state for CLI calls;
        # read-only parents have no shell path and therefore keep all context
        # fields private to the facade.
        environment.pop(WORKER_FACADE_MARKER, None)
        for key in (
            "AGENT_CENTRAL_WORKER_SOURCE_ROOT",
            "AGENT_CENTRAL_WORKER_WORKSPACE",
            "AGENT_CENTRAL_WORKER_PARENT_FAMILY",
            "AGENT_CENTRAL_WORKER_TASK_AUTHORITY",
            "AGENT_CENTRAL_WORKER_LIFECYCLE_GENERATION",
            "AGENT_CENTRAL_WORKER_PROFILE",
        ):
            environment.pop(key, None)
        if read_only:
            for key in ("AGENT_CENTRAL_PARENT_ID", "AGENT_CENTRAL_WORKER_STATE_DIR"):
                environment.pop(key, None)
    argv = [
        executable,
        "--model",
        resolved.resolved_model_id,
        "--effort",
        resolved.source_profile["effort"],
    ]
    contract = PROFILE_CONTRACTS[profile_name]
    source_prompt, source_reads = "", []
    readback: dict[str, Any] | None = None
    # Reuse the already-selected overlay names for exposure, grants and evidence.
    # Optional inspection-server discovery must not be repeated for each field.
    facade_tools = (
        overlay["tools"][len(READ_ONLY_TOOLS):] if read_only
        else worker_facade_tool_names(worker_facade)
    ) if worker_facade is not None and not no_tools else []
    if (read_only or worker_facade is not None or os.environ.get("AGENT_CENTRAL_MANAGED_PARENT") == "1") and not no_tools:
        from agent_source_guidance import source_guidance

        source_prompt, source_reads = source_guidance(
            root, arguments, workers=worker_facade is not None
        )
    if contract.permission_mode is not None and not read_only:
        argv.extend(("--permission-mode", resolved.source_profile["permissionMode"]))
    if read_only:
        argv.extend(("--permission-mode", overlay["permission_mode"]))
        if no_tools:
            argv.extend(("--tools", ""))
        else:
            argv.extend(("--tools", ",".join(overlay["tools"])))
        argv.extend(("--setting-sources", ISOLATED_SETTING_SOURCES))
        mcp_config = (
            worker_facade.config()
            if worker_facade is not None and not no_tools
            else '{"mcpServers":{}}'
        )
        argv.extend(("--mcp-config", mcp_config))
        if worker_facade is not None and not no_tools:
            argv.extend(("--allowed-tools", ",".join([*facade_tools, *source_reads])))
        argv.extend(("--strict-mcp-config", "--disable-slash-commands", "--no-chrome"))
        if headless and (os.environ.get("AGENT_CENTRAL_MANAGED_PARENT") == "1"
                         or os.environ.get(WORKER_FACADE_MARKER) == "1"):
            # Launch-time readback, after optional facade validation. Routing's
            # conditional contract is not proof that a facade actually loaded.
            readback = {**overlay, "mcp": "stdio" if worker_facade is not None and not no_tools else "strict-empty",
                        "argv_scope": "launcher-owned options; task text excluded",
                        "model": resolved.resolved_model_id,
                        "effort": resolved.source_profile["effort"],
                        "allowed_tools": [*facade_tools, *source_reads]
                        if worker_facade is not None and not no_tools else []}
    if worker_facade is not None and not no_tools:
        source_prompt = "\n\n".join(filter(None, (WORKER_FACADE_SYSTEM_PROMPT, source_prompt)))
    if source_prompt:
        argv.extend(("--append-system-prompt", source_prompt))
    if contract.additional_directories is not None:
        for directory in resolve_profile_directories(resolved.source_profile["additionalDirectories"]):
            argv.extend(("--add-dir", os.fspath(directory)))
    if contract.isolated_settings:
        argv.extend(("--settings", os.fspath(canonical_settings_path(root))))
        if not read_only:
            argv.extend(("--setting-sources", ISOLATED_SETTING_SOURCES))
    if worker_facade is not None and not read_only:
        argv.extend(("--mcp-config", worker_facade.config()))
        argv.extend(("--allowed-tools", ",".join([*facade_tools, *source_reads])))
    if worker_facade is not None and not no_tools:
        from agent_workers.facade_context import WorkerFacadeContext

        if isinstance(worker_facade, WorkerFacadeContext):
            print("claude-profile: worker facade evidence " + json.dumps(
                {"serena": worker_facade.serena_evidence()}, sort_keys=True),
                file=sys.stderr, flush=True)
    argv.extend(claude_arguments)
    if readback is not None:
        # Protected options cannot be overridden; tokens after -- are task text,
        # not later mode/tool flags. Never dump caller prompts into diagnostics.
        print("claude-profile: read-only contract " + json.dumps(readback, sort_keys=True),
              file=sys.stderr, flush=True)
    if live_log is not None:
        display = select_live_display(requested_display, sys.stdout)
        return run_live(
            executable,
            argv,
            environment,
            live_log,
            display,
            profile_name,
            require_artifact,
        )
    os.execve(executable, argv, environment)


def main() -> int:
    parser = argparse.ArgumentParser(prog="claude-profile", allow_abbrev=False)
    parser.add_argument("root", type=Path)
    parser.add_argument("profile")
    parser.add_argument("claude_arguments", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()

    root = parsed.root.resolve()
    if parsed.profile == "doctor":
        profile_names = parsed.claude_arguments if parsed.claude_arguments else None
        try:
            from claude_model_catalog import run_doctor

            doc, code = run_doctor(root, profile_names)
            print(json.dumps(doc, indent=2))
            return code
        except Exception as error:
            parser.exit(2, f"claude-profile: {error}\n")

    try:
        return launch(root, parsed.profile, parsed.claude_arguments)
    except ProfileError as error:
        parser.exit(2, f"claude-profile: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
