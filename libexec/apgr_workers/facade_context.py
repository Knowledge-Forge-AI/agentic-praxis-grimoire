"""Validate and freeze the launcher-owned context for the Claude MCP facade.

The facade is optional.  This module is imported only after the launcher has
seen its private opt-in marker, and it never registers a parent or reloads a
policy.  The active ledger is the authority for identity, workspace, task
authority, and capability provenance.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

from .ledger import ParentLedger

FACADE_MARKER = "APGR_WORKER_FACADE"
ENV_PARENT_ID = "APGR_PARENT_ID"
ENV_STATE_DIR = "APGR_WORKER_STATE_DIR"
ENV_SOURCE_ROOT = "APGR_WORKER_SOURCE_ROOT"
ENV_WORKSPACE = "APGR_WORKER_WORKSPACE"
ENV_PARENT_FAMILY = "APGR_WORKER_PARENT_FAMILY"
ENV_TASK_AUTHORITY = "APGR_WORKER_TASK_AUTHORITY"
ENV_LIFECYCLE_GENERATION = "APGR_WORKER_LIFECYCLE_GENERATION"
ENV_PROFILE = "APGR_WORKER_PROFILE"

MCP_SERVER_NAME = "agent_worker"
MCP_TOOL_NAMES = (
    "mcp__agent_worker__submit",
    "mcp__agent_worker__status",
    "mcp__agent_worker__result",
    "mcp__agent_worker__wait",
    "mcp__agent_worker__outcome",
    "mcp__agent_worker__pause_pool",
    "mcp__agent_worker__abandon",
    "mcp__agent_worker__cancel",
)
SERENA_TOOL_NAMES = (
    "mcp__serena__get_symbols_overview",
    "mcp__serena__find_symbol",
    "mcp__serena__find_referencing_symbols",
    "mcp__serena__find_implementations",
    "mcp__serena__find_declaration",
    "mcp__serena__get_diagnostics_for_file",
    "mcp__serena__initial_instructions",
)

_SERENA_MODE_TEXT = """description: APGR read-only symbolic tools
prompt: |
  Use only read-only symbolic inspection tools. Do not edit files, execute
  commands, or read or write Serena memories.
fixed_tools:
  - get_symbols_overview
  - find_symbol
  - find_referencing_symbols
  - find_implementations
  - find_declaration
  - get_diagnostics_for_file
  - initial_instructions
"""
_SERENA_MODE_FILENAME = "zz-apgr-read-only.yml"
_SERENA_USAGE_REPORTING = "SERENA_USAGE_REPORTING"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_FAMILY_NAMES = frozenset({"claude_fable", "claude_opus", "codex_parent", "gemini_flash"})
_AUTHORITIES = frozenset({"read_only", "mutation_capable"})


class FacadeContextError(ValueError):
    """The optional facade context is absent, stale, or inconsistent."""


@dataclass(frozen=True)
class WorkerFacadeContext:
    """Immutable context copied from a validated active parent ledger."""

    parent_id: str
    state_dir: Path
    source_root: Path
    workspace: Path
    parent_family: str
    task_authority: str
    lifecycle_generation: str
    profile: str
    dispatch_models: str | None = None
    dispatch_models_sha256: str | None = None
    dispatch_workers: str | None = None
    dispatch_workers_sha256: str | None = None

    @property
    def ledger(self) -> ParentLedger:
        """Open this parent's existing ledger without registering a context."""
        return ParentLedger(self.parent_id, self.state_dir)

    def environment(self) -> dict[str, str]:
        """Return the fixed context passed to the child MCP process."""
        env = {
            ENV_PARENT_ID: self.parent_id,
            ENV_STATE_DIR: str(self.state_dir),
            ENV_SOURCE_ROOT: str(self.source_root),
            ENV_WORKSPACE: str(self.workspace),
            ENV_PARENT_FAMILY: self.parent_family,
            ENV_TASK_AUTHORITY: self.task_authority,
            ENV_LIFECYCLE_GENERATION: self.lifecycle_generation,
            ENV_PROFILE: self.profile,
        }
        for key, attr in (
            ("APGR_DISPATCH_MODELS", "dispatch_models"),
            ("APGR_DISPATCH_MODELS_SHA256", "dispatch_models_sha256"),
            ("APGR_DISPATCH_WORKERS", "dispatch_workers"),
            ("APGR_DISPATCH_WORKERS_SHA256", "dispatch_workers_sha256"),
        ):
            val = getattr(self, attr, None) or os.environ.get(key)
            if val is not None:
                env[key] = val
        return env

    def mcp_tool_names(self) -> tuple[str, ...]:
        """Return the fixed names exposed by the active optional servers."""
        names = list(MCP_TOOL_NAMES)
        try:
            if self._serena_server() is not None:
                names.extend(SERENA_TOOL_NAMES)
        except (FacadeContextError, OSError, tomllib.TOMLDecodeError):
            # Serena is an enhancement.  A stale optional installation must
            # not hide the worker facade or prevent ordinary Claude launch.
            pass
        return tuple(names)

    def serena_evidence(self) -> dict[str, Any]:
        """Return sanitized evidence for the optional Serena resolution."""
        try:
            available = self._serena_server() is not None
        except (FacadeContextError, OSError, tomllib.TOMLDecodeError):
            available = False
        return {
            "server": "serena",
            "available": available,
            "status": "available" if available else "unavailable",
        }

    def config(self, *, command: str | None = None) -> str:
        """Build the exact stdio MCP configuration for Claude Code."""
        entrypoint = self.source_root / "bin" / "agent-worker-mcp"
        if not entrypoint.is_file() or not os.access(entrypoint, os.X_OK):
            raise FacadeContextError("worker MCP entrypoint is unavailable")
        if command is None:
            command = sys.executable
        servers: dict[str, Any] = {
            MCP_SERVER_NAME: {
                "type": "stdio",
                "command": command,
                "args": [str(entrypoint)],
                "env": self.environment(),
            }
        }
        try:
            serena = self._serena_server()
        except (FacadeContextError, OSError, tomllib.TOMLDecodeError):
            serena = None
        if serena is not None:
            servers["serena"] = serena
        payload = {"mcpServers": servers}
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)

    def _serena_server(self) -> dict[str, Any] | None:
        """Build a source-owned, fixed read-only Serena server entry."""
        command = _serena_source_command(self.source_root)
        if command is None:
            return None
        project = _serena_project_root(self.workspace)
        if project is None:
            return None
        mode_path = self._serena_mode_path()
        serena_home = self.ledger.base_dir / "serena-home"
        serena_home.mkdir(mode=0o700, exist_ok=True)
        os.chmod(serena_home, 0o700)
        return {
            "type": "stdio",
            "command": command,
            "args": [
                "start-mcp-server",
                "--project",
                str(project),
                "--context=claude-code",
                "--mode",
                "planning",
                "--mode",
                "no-memories",
                "--mode",
                str(mode_path),
                "--enable-web-dashboard=false",
                "--enable-gui-log-window=false",
                "--open-web-dashboard=false",
                "--log-level",
                "ERROR",
            ],
            "env": {
                "SERENA_HOME": str(serena_home),
                _SERENA_USAGE_REPORTING: "false",
            },
        }

    def _serena_mode_path(self) -> Path:
        """Materialize the immutable launcher-owned Serena mode in parent state."""
        path = self.ledger.base_dir / _SERENA_MODE_FILENAME
        expected = _SERENA_MODE_TEXT.encode("utf-8")
        try:
            current = path.read_bytes()
        except FileNotFoundError:
            current = None
        if current is not None:
            if current != expected:
                raise FacadeContextError("Serena read-only mode was modified")
            os.chmod(path, 0o600)
            return path

        self.ledger.base_dir.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.ledger.base_dir, 0o700)
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileNotFoundError:
            raise FacadeContextError("Serena parent state disappeared") from None
        except FileExistsError:
            current = path.read_bytes()
            if current != expected:
                raise FacadeContextError("Serena read-only mode was modified")
        else:
            with os.fdopen(descriptor, "wb") as mode_file:
                mode_file.write(expected)
                mode_file.flush()
                os.fsync(mode_file.fileno())
        os.chmod(path, 0o600)
        return path

    def assert_current(self) -> dict[str, Any]:
        """Revalidate the active ledger before each facade operation."""
        status = self.ledger.get_status()
        _validate_snapshot(
            status,
            parent_id=self.parent_id,
            source_root=self.source_root,
            workspace=self.workspace,
            parent_family=self.parent_family,
            task_authority=self.task_authority,
            lifecycle_generation=self.lifecycle_generation,
            profile=self.profile,
        )
        return status


def _resolved_path(value: str, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise FacadeContextError(f"{name} must be a non-empty path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise FacadeContextError(f"{name} must be absolute")
    try:
        return path.resolve()
    except OSError as error:
        raise FacadeContextError(f"{name} cannot be resolved") from error


def _serena_source_command(source_root: Path) -> str | None:
    """Resolve Serena only from the source-owned common MCP declaration."""
    config_path = source_root / "common" / "mcp.toml"
    try:
        document = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    servers = document.get("servers")
    if not isinstance(servers, list):
        return None
    for server in servers:
        if not isinstance(server, Mapping) or server.get("name") != "serena":
            continue
        if server.get("transport") != "stdio":
            return None
        clients = server.get("clients")
        if not isinstance(clients, Mapping) or clients.get("claude") != "enabled":
            return None
        command = server.get("command")
        if not isinstance(command, str) or not command.strip():
            return None
        candidate = Path(command).expanduser()
        if candidate.is_absolute():
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
            return None
        resolved = shutil.which(command)
        return resolved if resolved else None
    return None


def _serena_project_root(workspace: Path) -> Path | None:
    """Use only an existing Serena project to avoid auto-generating product files."""
    current = workspace
    while True:
        if (current / ".serena" / "project.yml").is_file():
            return current
        if current.parent == current:
            return None
        current = current.parent


def _env_get(environment: Mapping[str, str], name: str) -> str | None:
    val = environment.get(name)
    if val is not None and val.strip():
        return val
    return None

def _required_text(environment: Mapping[str, str], name: str) -> str:
    value = _env_get(environment, name)
    if not isinstance(value, str) or not value.strip():
        raise FacadeContextError(f"missing {name}")
    return value


def _validate_snapshot(
    status: Mapping[str, Any],
    *,
    parent_id: str,
    source_root: Path,
    workspace: Path,
    parent_family: str,
    task_authority: str,
    lifecycle_generation: str,
    profile: str,
) -> None:
    if status.get("registered") is not True or status.get("status") != "active":
        raise FacadeContextError("parent ledger is not active")
    if status.get("parent_id") != parent_id:
        raise FacadeContextError("parent ID does not match the active ledger")
    if status.get("parent_family") != parent_family:
        raise FacadeContextError("parent family does not match the active ledger")
    if status.get("task_authority") != task_authority:
        raise FacadeContextError("task authority does not match the active ledger")
    if status.get("workspace") != str(workspace):
        raise FacadeContextError("workspace does not match the active ledger")
    if parent_family not in _FAMILY_NAMES:
        raise FacadeContextError("unsupported Claude parent family")
    if task_authority not in _AUTHORITIES:
        raise FacadeContextError("unsupported task authority")
    if not _IDENTIFIER_RE.fullmatch(parent_id):
        raise FacadeContextError("parent ID is not a safe identifier")
    if not isinstance(lifecycle_generation, str) or not lifecycle_generation.strip():
        raise FacadeContextError("lifecycle generation is required")
    if not isinstance(profile, str) or not _IDENTIFIER_RE.fullmatch(profile):
        raise FacadeContextError("worker profile is invalid")

    capability = status.get("worker_capability")
    if not isinstance(capability, Mapping):
        raise FacadeContextError("active ledger lacks worker capability")
    if capability.get("available") is not True or capability.get("allowed") is not True:
        raise FacadeContextError("worker capability is unavailable")
    if capability.get("interface") != "stdio-mcp":
        raise FacadeContextError("worker capability is not bound to stdio MCP")
    if capability.get("parent_family") != parent_family:
        raise FacadeContextError("worker capability family does not match the ledger")
    if capability.get("source_root") != str(source_root):
        raise FacadeContextError("worker capability source root does not match")
    if capability.get("lifecycle_generation") != lifecycle_generation:
        raise FacadeContextError("worker capability lifecycle is stale")
    worker = capability.get("gemini_worker")
    if not isinstance(worker, Mapping) or worker.get("profile") != profile:
        raise FacadeContextError("worker profile does not match the ledger capability")


def load_launcher_context(
    source_root: Path,
    *,
    expected_parent_family: str,
    expected_task_authority: str,
    environment: Mapping[str, str] | None = None,
) -> WorkerFacadeContext:
    """Validate launcher environment and return an immutable facade context."""
    env = os.environ if environment is None else environment
    parent_id = _required_text(env, ENV_PARENT_ID)
    state_dir = _resolved_path(_required_text(env, ENV_STATE_DIR), ENV_STATE_DIR)
    source = Path(source_root).resolve()
    workspace = Path.cwd().resolve()
    advertised_source = _env_get(env, ENV_SOURCE_ROOT)
    advertised_workspace = _env_get(env, ENV_WORKSPACE)
    advertised_family = _env_get(env, ENV_PARENT_FAMILY)
    advertised_authority = _env_get(env, ENV_TASK_AUTHORITY)
    generation = _env_get(env, ENV_LIFECYCLE_GENERATION)
    profile = _env_get(env, ENV_PROFILE)
    if advertised_source is not None and _resolved_path(advertised_source, ENV_SOURCE_ROOT) != source:
        raise FacadeContextError("launcher source root does not match the active source")
    if advertised_workspace is not None and _resolved_path(advertised_workspace, ENV_WORKSPACE) != workspace:
        raise FacadeContextError("launcher workspace does not match the current directory")
    if advertised_family is not None and advertised_family != expected_parent_family:
        raise FacadeContextError("launcher parent family does not match the profile")
    if advertised_authority is not None and advertised_authority != expected_task_authority:
        raise FacadeContextError("launcher task authority does not match the profile")
    if not state_dir.is_dir():
        raise FacadeContextError("worker state directory is unavailable")
    try:
        if state_dir.is_relative_to(source):
            raise FacadeContextError("worker state must remain outside the source root")
    except AttributeError:  # pragma: no cover - Python 3.8 compatibility
        if str(state_dir).startswith(str(source) + os.sep):
            raise FacadeContextError("worker state must remain outside the source root")

    ledger = ParentLedger(parent_id, state_dir)
    status = ledger.get_status()
    capability = status.get("worker_capability")
    if not isinstance(capability, Mapping):
        raise FacadeContextError("active ledger lacks worker capability")
    # Dispatcher and direct launchers need only carry the parent ID and state
    # directory.  Derive the remaining immutable fields from the ledger and
    # accept explicit values only as consistency checks.
    if generation is None:
        generation = capability.get("lifecycle_generation")
    if profile is None:
        worker = capability.get("gemini_worker")
        profile = worker.get("profile") if isinstance(worker, Mapping) else None
    if not isinstance(generation, str) or not generation.strip():
        raise FacadeContextError("missing lifecycle generation")
    if not isinstance(profile, str) or not profile.strip():
        raise FacadeContextError("missing worker profile")
    context = WorkerFacadeContext(
        parent_id=parent_id,
        state_dir=state_dir,
        source_root=source,
        workspace=workspace,
        parent_family=expected_parent_family,
        task_authority=expected_task_authority,
        lifecycle_generation=generation,
        profile=profile,
        dispatch_models=_env_get(env, "APGR_DISPATCH_MODELS"),
        dispatch_models_sha256=_env_get(env, "APGR_DISPATCH_MODELS_SHA256"),
        dispatch_workers=_env_get(env, "APGR_DISPATCH_WORKERS"),
        dispatch_workers_sha256=_env_get(env, "APGR_DISPATCH_WORKERS_SHA256"),
    )
    _validate_snapshot(
        status,
        parent_id=context.parent_id,
        source_root=context.source_root,
        workspace=context.workspace,
        parent_family=context.parent_family,
        task_authority=context.task_authority,
        lifecycle_generation=context.lifecycle_generation,
        profile=context.profile,
    )
    return context


def load_server_context(environment: Mapping[str, str] | None = None) -> WorkerFacadeContext:
    """Validate the fixed environment supplied by Claude's MCP config."""
    env = os.environ if environment is None else environment
    source = _resolved_path(_required_text(env, ENV_SOURCE_ROOT), ENV_SOURCE_ROOT)
    workspace = _resolved_path(_required_text(env, ENV_WORKSPACE), ENV_WORKSPACE)
    family = _required_text(env, ENV_PARENT_FAMILY)
    authority = _required_text(env, ENV_TASK_AUTHORITY)
    generation = _required_text(env, ENV_LIFECYCLE_GENERATION)
    profile = _required_text(env, ENV_PROFILE)
    parent_id = _required_text(env, ENV_PARENT_ID)
    state_dir = _resolved_path(_required_text(env, ENV_STATE_DIR), ENV_STATE_DIR)
    if family not in _FAMILY_NAMES or authority not in _AUTHORITIES:
        raise FacadeContextError("invalid fixed parent context")
    if not _IDENTIFIER_RE.fullmatch(parent_id) or not _IDENTIFIER_RE.fullmatch(profile):
        raise FacadeContextError("invalid fixed parent identifier")
    if not state_dir.is_dir():
        raise FacadeContextError("worker state directory is unavailable")
    ledger = ParentLedger(parent_id, state_dir)
    status = ledger.get_status()
    _validate_snapshot(
        status,
        parent_id=parent_id,
        source_root=source,
        workspace=workspace,
        parent_family=family,
        task_authority=authority,
        lifecycle_generation=generation,
        profile=profile,
    )
    return WorkerFacadeContext(
        parent_id=parent_id,
        state_dir=state_dir,
        source_root=source,
        workspace=workspace,
        parent_family=family,
        task_authority=authority,
        lifecycle_generation=generation,
        profile=profile,
        dispatch_models=_env_get(env, "APGR_DISPATCH_MODELS"),
        dispatch_models_sha256=_env_get(env, "APGR_DISPATCH_MODELS_SHA256"),
        dispatch_workers=_env_get(env, "APGR_DISPATCH_WORKERS"),
        dispatch_workers_sha256=_env_get(env, "APGR_DISPATCH_WORKERS_SHA256"),
    )
