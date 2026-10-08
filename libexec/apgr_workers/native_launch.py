"""Fresh Codex parent launch binding for the fixed Codex parent triple-pool policy.

The native Luna pool belongs to the Codex runtime.  This module therefore does
not reserve native children in the APGR ledger.  It reads the
provider-owned sources, freezes the effective launch overrides, and installs
the existing worker MCP facade as one explicitly configured server.  A launch
claim is durable and single-use: a second invocation with the same parent
identity cannot create another Codex root that would appear to share capacity.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from .facade_context import (
    ENV_LIFECYCLE_GENERATION,
    ENV_PARENT_FAMILY,
    ENV_PARENT_ID,
    ENV_PROFILE,
    ENV_SOURCE_ROOT,
    ENV_STATE_DIR,
    ENV_TASK_AUTHORITY,
    ENV_WORKSPACE,
    MCP_SERVER_NAME,
    MCP_TOOL_NAMES,
    FACADE_MARKER as FACADE_MARKER,
)
from .ledger import ParentLedger, sanitize_parent_id
from .policy import TRIPLE_POOL


SCHEMA_NAME = "agent-worker-native-launch-v1"
NATIVE_CAP = 4
NATIVE_SOURCE = Path("codex/config.d/170-subagents.toml")
LAUNCH_RECORD_NAME = "native-launch.json"
LAUNCH_LOCK_NAME = "native-launch.lock"
TERM_TO_KILL_GRACE_SECONDS = 2.0
KILL_REAP_GRACE_SECONDS = 2.0
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_TOML_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class NativeLaunchError(RuntimeError):
    """The fresh native parent launch cannot be bound safely."""


class FreshLaunchAlreadyClaimed(NativeLaunchError):
    """A parent identity already has a durable native launch claim."""


@dataclass(frozen=True)
class NativeWorkerSource:
    """Provider-owned native worker values read before launch."""

    source: str
    source_sha256: str
    enabled: bool
    model: str
    effort: str
    source_max_concurrent_threads: int
    projection_matches_selected: bool = True


@dataclass(frozen=True)
class NativeLaunchBinding:
    """All immutable facts needed to launch one fresh Codex parent."""

    parent_id: str
    parent_family: str
    parent_profile: str
    parent_model: str
    parent_effort: str
    workspace: Path
    state_dir: Path
    source_root: Path
    task_authority: str
    lifecycle_generation: str
    gemini_profile: str
    native_source: NativeWorkerSource
    mcp_command: str
    mcp_args: tuple[str, ...]
    mcp_environment: tuple[tuple[str, str], ...]
    allowlisted_tools: tuple[str, ...]
    profile_source: str
    profile_sha256: str
    allowed_worker_kinds: tuple[str, ...]
    excluded_worker_kinds: tuple[str, ...]
    native_enabled: bool
    facade_enabled: bool

    @property
    def native_model(self) -> str:
        return self.native_source.model

    @property
    def native_effort(self) -> str:
        return self.native_source.effort

    def facade_environment(self) -> dict[str, str]:
        """Return the fixed environment passed to the worker MCP server."""
        return dict(self.mcp_environment)

    def config_overrides(self) -> tuple[str, ...]:
        """Return TOML values for the launch-local Codex configuration."""
        env = _toml_inline_table(self.facade_environment())
        args = _toml_array(self.mcp_args)
        return (
            f"agents.enabled={str(self.native_enabled).lower()}",
            f"agents.default_subagent_model={_toml_string(self.native_model)}",
            f"agents.default_subagent_reasoning_effort={_toml_string(self.native_effort)}",
            f"agents.max_concurrent_threads_per_session={NATIVE_CAP}",
            f"mcp_servers.{MCP_SERVER_NAME}.enabled={str(self.facade_enabled).lower()}",
            f"mcp_servers.{MCP_SERVER_NAME}.command={_toml_string(self.mcp_command)}",
            f"mcp_servers.{MCP_SERVER_NAME}.args={args}",
            f"mcp_servers.{MCP_SERVER_NAME}.env={env}",
            f"mcp_servers.{MCP_SERVER_NAME}.required={str(self.facade_enabled).lower()}",
            f"mcp_servers.{MCP_SERVER_NAME}.enabled_tools={json.dumps([tool.removeprefix('mcp__agent_worker__') for tool in self.allowlisted_tools])}",
            # Worker delegation is authorized by the selected mode and bounded by
            # the facade ledger. Approve only this launch-owned closed tool set.
            *(f'mcp_servers.{MCP_SERVER_NAME}.tools.{tool.removeprefix("mcp__agent_worker__")}.approval_mode="approve"'
              for tool in self.allowlisted_tools),
        )

    def capability_fragment(self, argv: Sequence[str] | None = None) -> dict[str, Any]:
        """Return additive worker capability evidence for ledger snapshots."""
        fragment: dict[str, Any] = {
            "interface": "stdio-mcp" if self.facade_enabled else "none",
            "native_launch": self.evidence(),
        }
        if argv is not None:
            fragment["native_launch_binding"] = self.launch_binding(argv)
        return fragment

    def launch_binding(self, argv: Sequence[str]) -> dict[str, Any]:
        """Return the frozen launch identity consumed by Codex parent admission."""
        if not isinstance(argv, Sequence) or isinstance(argv, (str, bytes)):
            raise NativeLaunchError("native launch argv must be a sequence")
        encoded = json.dumps(list(argv), ensure_ascii=True, separators=(",", ":"))
        return {
            "schema": SCHEMA_NAME,
            "status": "bound",
            "source": "fresh_source_launcher",
            "cap": NATIVE_CAP,
            "argv_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            "native_enabled": self.native_enabled,
            "facade_enabled": self.facade_enabled,
        }

    def evidence(self) -> dict[str, Any]:
        """Return non-secret, source-bound launch evidence."""
        override_keys = [item.split("=", 1)[0] for item in self.config_overrides()]
        return {
            "schema": SCHEMA_NAME,
            "status": "bound",
            "transport": "codex_native",
            "policy_selection": TRIPLE_POOL,
            "fresh_launch_only": True,
            "resume_supported": False,
            "resume_unavailable_reason": (
                "exact native resume is not bound by this launcher; drain the "
                "prior lifetime and use a new parent identity"
            ),
            "parent": {
                "parent_id": self.parent_id,
                "family": self.parent_family,
                "profile": self.parent_profile,
                "model": self.parent_model,
                "effort": self.parent_effort,
                "task_authority": self.task_authority,
                "workspace": str(self.workspace),
                "lifecycle_generation": self.lifecycle_generation,
                "profile_source": self.profile_source,
                "profile_sha256": self.profile_sha256,
                "profile_launch": "source_overrides_only",
            },
            "native_worker": {
                "enabled": self.native_source.enabled,
                "model": self.native_model,
                "effort": self.native_effort,
                "source_max_concurrent_threads_per_session": (
                    self.native_source.source_max_concurrent_threads
                ),
                "effective_max_concurrent_threads_per_session": NATIVE_CAP,
                "effective_enabled": self.native_enabled,
                "occupancy_owner": "codex_runtime",
                "cap_binding": "launch_config_override",
                "source": self.native_source.source,
                "source_sha256": self.native_source.source_sha256,
                "projection_matches_selected": self.native_source.projection_matches_selected,
                "override_keys": override_keys,
            },
            "facade": {
                "server": MCP_SERVER_NAME,
                "enabled": self.facade_enabled,
                "command": self.mcp_command,
                "args": list(self.mcp_args),
                "environment_keys": sorted(self.facade_environment()),
                "allowlisted_tools": list(self.allowlisted_tools),
            },
            "gemini_profile": self.gemini_profile,
            "allowed_worker_kinds": list(self.allowed_worker_kinds),
            "excluded_worker_kinds": list(self.excluded_worker_kinds),
        }

    def profile_available(self) -> bool:
        """Return whether an optional live profile exactly matches the source.

        The launch remains valid without this profile because model and effort
        are always explicit command-line overrides.  A matching profile is
        useful only for the rest of the provider's ordinary base settings.
        """
        codex_home = Path(
            os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        ).expanduser()
        path = codex_home / f"{self.parent_profile}.config.toml"
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest() == self.profile_sha256
        except (OSError, ValueError):
            return False


def _toml_string(value: str) -> str:
    """Encode a string using the JSON/TOML basic-string intersection."""
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _toml_array(values: Sequence[str]) -> str:
    return "[" + ",".join(_toml_string(value) for value in values) + "]"


def _toml_inline_table(values: Mapping[str, str]) -> str:
    entries: list[str] = []
    for key in sorted(values):
        if _TOML_KEY_RE.fullmatch(key) is None:
            raise NativeLaunchError(f"unsafe MCP environment key {key!r}")
        entries.append(f"{key} = {_toml_string(values[key])}")
    return "{" + ", ".join(entries) + "}"


def _resolved_path(value: str | Path, name: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise NativeLaunchError(f"{name} must be absolute")
    try:
        return path.resolve()
    except OSError as error:
        raise NativeLaunchError(f"{name} cannot be resolved") from error


def _outside(path: Path, parent: Path) -> bool:
    try:
        return not path.is_relative_to(parent)
    except AttributeError:  # pragma: no cover - retained for supported older Python
        return not str(path).startswith(str(parent) + os.sep)


def _profile_path(root: Path, profile: str) -> Path:
    if not isinstance(profile, str) or _IDENTIFIER_RE.fullmatch(profile) is None:
        raise NativeLaunchError("parent profile is not a safe identifier")
    return root / "codex" / "profiles" / f"{profile}.config.toml"


def _load_parent_profile(root: Path, profile: str) -> tuple[str, str, str, str]:
    path = _profile_path(root, profile)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise NativeLaunchError(f"cannot read Codex parent profile {path}: {error}") from error
    from agent_phase.runtime_models import selection, classify_parent_family
    try:
        sel = selection(root, "codex", profile)
        model = sel.get("model")
        effort = sel.get("effort")
    except Exception as error:
        raise NativeLaunchError(f"cannot resolve Codex parent model from bundle: {error}") from error
    family = classify_parent_family("codex", model, role=sel.get("role"))
    if family not in {"codex_parent"}:
        raise NativeLaunchError(
            f"Codex parent profile must declare the parent role (got model {model!r})"
        )
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return model, effort, rel, hashlib.sha256(raw).hexdigest()


def load_native_worker_source(root: Path, luna_profile: str | None = None) -> NativeWorkerSource:
    """Read and validate the unmodified provider-owned worker source."""
    root = Path(root).expanduser().resolve()
    from agent_phase.runtime_models import selected_worker_profile
    luna_profile = luna_profile or selected_worker_profile(root, "luna")
    path = root / NATIVE_SOURCE
    try:
        raw = path.read_bytes()
        import tomllib

        parsed = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise NativeLaunchError(f"cannot read native worker source {path}") from error
    agents = parsed.get("agents") if isinstance(parsed, Mapping) else None
    if not isinstance(agents, Mapping):
        raise NativeLaunchError("native worker source lacks an agents table")
    # Source projections are checked against their source inventory; the captured
    # runtime selection below can deliberately differ and remains sole authority.
    source_policy = tomllib.loads((root / "common/dispatcher/workers.toml").read_text())
    source_profile = source_policy["selections"]["triple_pool_4x4x4"]["luna_worker"]["profile"]
    source_models = tomllib.loads((root / "common/dispatcher/models.toml").read_text())
    source_choice = source_models["providers"]["codex"][source_profile]
    if agents.get("default_subagent_model") != source_choice["model"]:
        raise NativeLaunchError("native model source projection mismatch")
    if agents.get("default_subagent_reasoning_effort") != source_choice["effort"]:
        raise NativeLaunchError("native reasoning effort source projection mismatch")
    enabled = agents.get("enabled")
    if enabled is not True:
        raise NativeLaunchError("native worker source must have agents.enabled=true")
    from agent_phase.runtime_models import selection
    try:
        sel = selection(root, "codex", luna_profile)
        model = sel.get("model")
        effort = sel.get("effort")
    except Exception as error:
        raise NativeLaunchError(f"cannot resolve Luna model from bundle: {error}") from error
    if not isinstance(model, str) or not model or not isinstance(effort, str) or not effort:
        raise NativeLaunchError(
            "native worker source model and effort must be non-empty"
        )
    return NativeWorkerSource(
        source=NATIVE_SOURCE.as_posix(),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        enabled=True,
        model=model,
        effort=effort,
        source_max_concurrent_threads=NATIVE_CAP,
        projection_matches_selected=(agents.get("default_subagent_model") == model and agents.get("default_subagent_reasoning_effort") == effort),
    )


def _validate_capability(capability: Mapping[str, Any] | None) -> str:
    if capability is None:
        return "gemini"
    if capability.get("parent_family") not in {None, "codex_parent"}:
        raise NativeLaunchError("native launch capability is not a codex_parent capability")
    if capability.get("policy_selection") not in {TRIPLE_POOL}:
        raise NativeLaunchError("native launch requires the triple_pool_4x4x4 selection")
    limits = capability.get("limits")
    if isinstance(limits, Mapping):
        gemini = limits.get("max_gemini", limits.get("max_gemini_workers_per_parent"))
        luna = limits.get("max_luna", limits.get("max_luna_workers_per_parent"))
        sonnet = limits.get("max_sonnet", limits.get("max_sonnet_workers_per_parent"))
        if gemini is not None and gemini != NATIVE_CAP:
            raise NativeLaunchError("native launch requires four Gemini slots")
        if luna is not None and luna != NATIVE_CAP:
            raise NativeLaunchError("native launch requires four Luna slots")
        if sonnet is not None and sonnet != NATIVE_CAP:
            raise NativeLaunchError("native launch requires four Sonnet slots")
    allowed = capability.get("allowed_worker_kinds")
    if allowed is not None:
        if not isinstance(allowed, list) or any(
            kind not in {"gemini", "sonnet"} for kind in allowed
        ) or len(set(allowed)) != len(allowed):
            raise NativeLaunchError(
                "Codex native launch cannot expose external Luna workers"
            )
    excluded = capability.get("excluded_worker_kinds", [])
    if not isinstance(excluded, list) or any(
        kind not in {"gemini", "luna", "sonnet"} for kind in excluded
    ) or len(set(excluded)) != len(excluded):
        raise NativeLaunchError("native launch worker exclusions are invalid")
    borrowing = capability.get("borrowing")
    if borrowing is not None and borrowing is not False:
        raise NativeLaunchError("native launch does not permit pool borrowing")
    worker = capability.get("gemini_worker")
    if not isinstance(worker, Mapping) or not isinstance(worker.get("profile"), str):
        raise NativeLaunchError("native launch capability lacks a Gemini profile")
    return worker["profile"]


def apply_worker_exclusions(
    capability: Mapping[str, Any], excluded_worker_kinds: Sequence[str] | None = None
) -> dict[str, Any]:
    """Freeze an operator's provider exclusions as a capability subset.

    Codex's native Luna ceiling remains four when Luna is excluded, but the
    launch-local ``agents.enabled`` value is false.  Excluding external kinds
    disables the worker MCP server when all external kinds are excluded.
    """
    if not isinstance(capability, Mapping):
        raise NativeLaunchError("worker capability must be a mapping")
    excluded = {str(kind) for kind in (excluded_worker_kinds or [])}
    if any(kind not in {"gemini", "luna", "sonnet"} for kind in excluded):
        raise NativeLaunchError("native launch worker exclusions are invalid")
    family = capability.get("parent_family")
    if family not in {"codex_parent"}:
        raise NativeLaunchError("worker exclusions are only supported for Codex launch")
    default_allowed = ["gemini", "sonnet"] if capability.get("policy_selection") == "triple_pool_4x4x4" else ["gemini"]
    allowed = capability.get("allowed_worker_kinds", default_allowed)
    if not isinstance(allowed, list) or any(kind not in {"gemini", "sonnet"} for kind in allowed):
        raise NativeLaunchError("Codex native launch capability has invalid worker kinds")
    result = json.loads(json.dumps(dict(capability)))
    result["allowed_worker_kinds"] = [kind for kind in allowed if kind not in excluded]
    result["excluded_worker_kinds"] = sorted(excluded)
    native_worker = result.get("native_worker")
    if not isinstance(native_worker, Mapping):
        native_worker = {}
    else:
        native_worker = dict(native_worker)
    if "luna" in excluded:
        native_worker["enabled"] = False
    result["native_worker"] = native_worker
    # ``allowed`` represents whether an external facade is available.  Native
    # work may still be enabled after external workers are excluded.
    result["allowed"] = bool(result.get("allowed", True)) and bool(
        result["allowed_worker_kinds"]
    )
    return result


def prepare_native_binding(
    root: Path,
    *,
    parent_id: str,
    parent_profile: str,
    workspace: Path,
    state_dir: Path,
    task_authority: str,
    lifecycle_generation: str | None = None,
    capability: Mapping[str, Any] | None = None,
    excluded_worker_kinds: Sequence[str] | None = None,
    python_executable: str | None = None,
) -> NativeLaunchBinding:
    """Resolve the source contract for one fresh Codex parent lifetime."""
    root = Path(root).expanduser().resolve()
    workspace = _resolved_path(workspace, "workspace")
    state_dir = _resolved_path(state_dir, "state_dir")
    if not parent_id or _IDENTIFIER_RE.fullmatch(parent_id) is None:
        raise NativeLaunchError("parent_id is not a safe identifier")
    if task_authority not in {"read_only", "mutation_capable"}:
        raise NativeLaunchError("task authority must be read_only or mutation_capable")
    if not _outside(state_dir, root):
        raise NativeLaunchError("worker state must remain outside the source root")
    if not _outside(state_dir, workspace):
        raise NativeLaunchError("worker state must remain outside the parent workspace")
    if not lifecycle_generation:
        lifecycle_generation = parent_id
    if not isinstance(lifecycle_generation, str) or not lifecycle_generation.strip():
        raise NativeLaunchError("lifecycle generation is required")
    parent_model, parent_effort, profile_source, profile_sha256 = _load_parent_profile(
        root, parent_profile
    )
    from agent_phase.runtime_models import selection, classify_parent_family
    sel = selection(root, "codex", parent_profile)
    parent_family = classify_parent_family("codex", parent_model, role=sel.get("role"))
    luna_profile_name = None
    if capability and isinstance(capability.get("luna_worker"), Mapping):
        luna_profile_name = capability["luna_worker"].get("profile")
    native_source = load_native_worker_source(root, luna_profile=luna_profile_name)
    gemini_profile = _validate_capability(capability)
    requested_excluded = set(excluded_worker_kinds or [])
    if any(kind not in {"gemini", "luna", "sonnet"} for kind in requested_excluded):
        raise NativeLaunchError("native launch worker exclusions are invalid")
    default_allowed = ["gemini", "sonnet"] if (capability and capability.get("policy_selection") == "triple_pool_4x4x4") or parent_family == "codex_parent" else ["gemini"]
    capability_allowed = (
        list(capability.get("allowed_worker_kinds", default_allowed))
        if capability is not None
        else default_allowed
    )
    capability_excluded = (
        list(capability.get("excluded_worker_kinds", []))
        if capability is not None
        else []
    )
    if any(kind not in {"gemini", "luna", "sonnet"} for kind in capability_excluded):
        raise NativeLaunchError("native launch worker exclusions are invalid")
    excluded = set(capability_excluded) | requested_excluded
    allowed_worker_kinds = tuple(
        kind for kind in capability_allowed if kind not in excluded
    )
    native_capability = capability.get("native_worker") if capability else None
    if native_capability is not None and not isinstance(native_capability, Mapping):
        raise NativeLaunchError("native launch native-worker capability is invalid")
    native_enabled = (
        bool(native_capability.get("enabled", True))
        if isinstance(native_capability, Mapping)
        else True
    ) and "luna" not in excluded
    facade_enabled = any(k in allowed_worker_kinds for k in ("gemini", "sonnet"))
    entrypoint = root / "bin" / "agent-worker-mcp"
    if not entrypoint.is_file() or not os.access(entrypoint, os.X_OK):
        facade_enabled = False
    command = _resolved_path(python_executable or sys.executable, "MCP command")
    environment = {
        ENV_PARENT_ID: parent_id,
        ENV_STATE_DIR: str(state_dir),
        ENV_SOURCE_ROOT: str(root),
        ENV_WORKSPACE: str(workspace),
        ENV_PARENT_FAMILY: parent_family,
        ENV_TASK_AUTHORITY: task_authority,
        ENV_LIFECYCLE_GENERATION: lifecycle_generation,
        ENV_PROFILE: gemini_profile,
    }
    for key in (
        "APGR_DISPATCH_MODELS",
        "APGR_DISPATCH_MODELS_SHA256",
        "APGR_DISPATCH_WORKERS",
        "APGR_DISPATCH_WORKERS_SHA256",
    ):
        if key in os.environ:
            environment[key] = os.environ[key]
    for key in list(environment.keys()):
        if key.startswith("AGENT_CENTRAL"):
            environment.pop(key, None)
    # Keep the profile hash in the source-bound object without putting it in the
    # MCP environment.  It is exposed through evidence below.
    binding = NativeLaunchBinding(
        parent_id=parent_id,
        parent_family=parent_family,
        parent_profile=parent_profile,
        parent_model=parent_model,
        parent_effort=parent_effort,
        workspace=workspace,
        state_dir=state_dir,
        source_root=root,
        task_authority=task_authority,
        lifecycle_generation=lifecycle_generation,
        gemini_profile=gemini_profile,
        native_source=native_source,
        mcp_command=str(command),
        mcp_args=(str(entrypoint),),
        mcp_environment=tuple(sorted(environment.items())),
        allowlisted_tools=tuple(MCP_TOOL_NAMES),
        profile_source=profile_source,
        profile_sha256=profile_sha256,
        allowed_worker_kinds=allowed_worker_kinds,
        excluded_worker_kinds=tuple(sorted(excluded)),
        native_enabled=native_enabled,
        facade_enabled=facade_enabled,
    )
    return binding


def capability_with_native_binding(
    capability: Mapping[str, Any],
    binding: NativeLaunchBinding,
    argv: Sequence[str],
) -> dict[str, Any]:
    """Freeze Codex parent launch evidence into the capability before registration."""
    if not isinstance(capability, Mapping):
        raise NativeLaunchError("worker capability must be a mapping")
    result = json.loads(json.dumps(dict(capability)))
    result.update(binding.capability_fragment(argv))
    result["source_root"] = str(binding.source_root)
    result["lifecycle_generation"] = binding.lifecycle_generation
    result["allowed_worker_kinds"] = list(binding.allowed_worker_kinds)
    result["excluded_worker_kinds"] = list(binding.excluded_worker_kinds)
    result["allowed"] = bool(result.get("allowed", True)) and binding.facade_enabled
    result["available"] = bool(result.get("available", True))
    native_worker = result.get("native_worker")
    if isinstance(native_worker, Mapping):
        native_worker = dict(native_worker)
    else:
        native_worker = {}
    native_worker.update(
        {
            "enabled": binding.native_enabled,
            "effective_max_concurrent_threads_per_session": NATIVE_CAP,
            "occupancy_owner": "codex_runtime",
        }
    )
    result["native_worker"] = native_worker
    return result


def apply_native_binding(
    argv: Sequence[str], binding: NativeLaunchBinding, *, rtk=None
) -> list[str]:
    """Insert fixed launch overrides before the provider's prompt sentinel."""
    result = list(argv)
    if len(result) < 2 or result[1] != "exec":
        raise NativeLaunchError("native binding requires a Codex exec argv")
    prompt_index = len(result)
    if result and result[-1] == "-":
        prompt_index = len(result) - 1

    for index, token in enumerate(result):
        if token in {"--model", "-m"}:
            raise NativeLaunchError("caller-supplied model is not allowed")
        if token in {"-c", "--config"} and index + 1 < len(result):
            key = result[index + 1].split("=", 1)[0]
            if (
                key == "developer_instructions"
                or key.startswith("agents.")
                or key.startswith(f"mcp_servers.{MCP_SERVER_NAME}")
            ):
                raise NativeLaunchError(f"caller-supplied {key} override is not allowed")
        if token == "--profile":
            if index + 1 >= len(result) or result[index + 1] != binding.parent_profile:
                raise NativeLaunchError("Codex profile does not match the bound source profile")

    from controller_generation import binding_for_root as binding_for_root
    if "--profile" in result:
        index = result.index("--profile")
        del result[index:index + 2]
        prompt_index -= 2
    additions: list[str] = []
    if "--ignore-user-config" not in result:
        additions.append("--ignore-user-config")
    if "--sandbox" not in result and "-s" not in result:
        additions.extend(("--sandbox", "read-only" if binding.task_authority == "read_only" else "workspace-write"))
    # Source guidance is additive and independent of the selected auth home.
    # Use one canonical file reference rather than relying on an ambient
    # same-name skill projection from a different installation.
    from agent_source_guidance import codex_guidance_overrides

    for override in codex_guidance_overrides(binding.source_root, workers=binding.facade_enabled, rtk=rtk):
        additions.extend(("-c", override))
    for override in binding.config_overrides():
        additions.extend(("-c", override))
    return result[:prompt_index] + additions + result[prompt_index:]


def build_native_argv(
    binding: NativeLaunchBinding,
    *,
    codex_executable: str | None = None,
    prompt: str = "-",
) -> list[str]:
    """Build a direct, fresh ``codex exec`` command for the bound parent."""
    executable = codex_executable or shutil.which("codex")
    if not executable:
        raise NativeLaunchError("Codex executable is unavailable")
    if not isinstance(prompt, str) or not prompt:
        raise NativeLaunchError("prompt sentinel must be non-empty text")
    sandbox = "read-only" if binding.task_authority == "read_only" else "workspace-write"
    base = [
        str(executable),
        "exec",
        "--ignore-user-config",
        "--cd",
        str(binding.workspace),
        "--sandbox",
        sandbox,
        "--json",
        prompt,
    ]
    bound = apply_native_binding(base, binding)
    from agent_phase.roster import Endpoint
    from agent_phase.runtime_models import apply_selection
    return apply_selection(bound, Endpoint("codex", binding.parent_profile), binding.source_root)


def _record_path(binding: NativeLaunchBinding) -> Path:
    return binding.state_dir / sanitize_parent_id(binding.parent_id) / LAUNCH_RECORD_NAME


def _lock_path(path: Path) -> Path:
    return path.with_name(LAUNCH_LOCK_NAME)


@contextlib.contextmanager
def _record_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(os.fspath(path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.chmod(path, 0o600)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise NativeLaunchError(f"native launch record is unreadable: {path}") from error
    if not isinstance(value, dict) or value.get("schema") != SCHEMA_NAME:
        raise NativeLaunchError("native launch record has an unsupported schema")
    return value


def claim_fresh_launch(
    binding: NativeLaunchBinding, *, argv: Sequence[str] | None = None,
    require_empty_ledger: bool = False,
) -> dict[str, Any]:
    """Atomically claim one parent lifetime and persist its frozen binding."""
    path = _record_path(binding)
    with _record_lock(_lock_path(path)):
        if path.exists():
            existing = _read_json(path)
            status = existing.get("status", "unknown")
            raise FreshLaunchAlreadyClaimed(
                f"parent {binding.parent_id!r} already has a native launch ({status}); "
                "resume is unavailable and a new parent identity is required"
            )
        if require_empty_ledger and (path.parent / "ledger.json").exists():
            raise FreshLaunchAlreadyClaimed("existing worker context cannot become a fresh parent; inspect and drain its custody")
        now = time.time()
        record: dict[str, Any] = {
            "schema": SCHEMA_NAME,
            "status": "claimed",
            "parent_id": binding.parent_id,
            "parent_family": binding.parent_family,
            "claimed_at": now,
            "updated_at": now,
            "binding": binding.evidence(),
            "native_launch_binding": (
                binding.launch_binding(argv) if argv is not None else None
            ),
            "process": None,
            "drain": None,
            "ledger_drain": None,
            "exit_code": None,
        }
        _write_json(path, record)
        return record


def read_launch_record(binding: NativeLaunchBinding) -> dict[str, Any]:
    """Read the retained launch record without changing its custody state."""
    path = _record_path(binding)
    from .inspection import snapshot
    records, limitations = snapshot(path.parent, records=(LAUNCH_RECORD_NAME,))
    if limitations or LAUNCH_RECORD_NAME not in records:
        raise NativeLaunchError("native launch record absent or snapshot incomplete")
    return records[LAUNCH_RECORD_NAME]


def _update_launch_record(binding: NativeLaunchBinding, **changes: Any) -> dict[str, Any]:
    path = _record_path(binding)
    with _record_lock(_lock_path(path)):
        if not path.exists():
            raise NativeLaunchError(f"native launch record is absent: {path}")
        record = _read_json(path)
        record.update(changes)
        record["updated_at"] = time.time()
        _write_json(path, record)
        return record


def _process_identity(pid: int, pgid: int) -> str | None:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart=", "-o", "pgid="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    if result.returncode != 0 or not value or len(value) > 240:
        return None
    return f"{value}|expected_pgid={pgid}"


def bind_parent_process(
    binding: NativeLaunchBinding, pid: int, pgid: int | None = None
) -> dict[str, Any]:
    """Persist the process and start identity immediately after Popen."""
    if type(pid) is not int or pid <= 0:
        raise NativeLaunchError("parent process PID is invalid")
    pgid = pid if pgid is None else pgid
    if type(pgid) is not int or pgid <= 0:
        raise NativeLaunchError("parent process group is invalid")
    identity = _process_identity(pid, pgid)
    record = _update_launch_record(
        binding,
        status="running" if identity is not None else "identity_unknown",
        process={"pid": pid, "pgid": pgid, "identity": identity},
    )
    if identity is None:
        raise NativeLaunchError("parent process identity could not be observed")
    return record


def _group_present(pgid: int | None) -> bool | None:
    if type(pgid) is not int or pgid <= 0 or pgid == os.getpgrp():
        return None
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    except OSError:
        return False
    return True


def _signal_group(process: Any, pgid: int | None, signum: int) -> bool:
    if type(pgid) is int and pgid > 0 and pgid != os.getpgrp():
        try:
            os.killpg(pgid, signum)
            return True
        except (OSError, ProcessLookupError):
            pass
    try:
        if signum == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
        return True
    except (AttributeError, OSError, ProcessLookupError):
        return False


def _wait(process: Any, timeout: float) -> bool:
    try:
        process.wait(timeout=max(timeout, 0.0))
        return True
    except subprocess.TimeoutExpired:
        return False
    except (AttributeError, OSError, ProcessLookupError):
        return False


def drain_parent_process(
    process: Any,
    pgid: int | None,
    *,
    cancel_requested: bool = False,
    term_grace_seconds: float = TERM_TO_KILL_GRACE_SECONDS,
    kill_grace_seconds: float = KILL_REAP_GRACE_SECONDS,
) -> dict[str, Any]:
    """Drain the owned Codex process group after explicit stop or exit."""
    result: dict[str, Any] = {
        "scope": "fresh-Codex-parent-process-group",
        "pgid": pgid,
        "cancel_requested": cancel_requested,
        "term_sent": False,
        "kill_sent": False,
        "wait_completed": False,
        "group_present_before": _group_present(pgid),
    }
    if process is None:
        result.update(
            {
                "status": "not_started",
                "group_present_after": False,
                "cleanup_proven": True,
            }
        )
        return result
    try:
        running = process.poll() is None
    except (AttributeError, OSError):
        running = None
    if running is True:
        result["term_sent"] = _signal_group(process, pgid, signal.SIGTERM)
        result["wait_completed"] = _wait(process, term_grace_seconds)
    elif running is False:
        result["wait_completed"] = True
    else:
        result["identity_status"] = "unknown"

    if _group_present(pgid) is True:
        result["term_sent"] = result["term_sent"] or _signal_group(
            process, pgid, signal.SIGTERM
        )
        _wait(process, term_grace_seconds)
    if _group_present(pgid) is True:
        result["kill_sent"] = _signal_group(process, pgid, signal.SIGKILL)
        result["wait_completed"] = _wait(process, kill_grace_seconds) or result["wait_completed"]
    result["group_present_after"] = _group_present(pgid)
    result["cleanup_proven"] = result["group_present_after"] is False
    if result["group_present_after"] is None:
        result["cleanup_proven"] = False
        result["status"] = "unknown"
    else:
        result["status"] = "drained" if result["cleanup_proven"] else "stopping"
    return result


def _wait_for_parent(
    process: Any,
    cancel_state: dict[str, Any],
    *,
    term_grace_seconds: float,
) -> int:
    kill_sent = False
    while True:
        try:
            return int(process.wait(timeout=0.2))
        except subprocess.TimeoutExpired:
            deadline = cancel_state.get("deadline")
            if (
                cancel_state.get("requested")
                and not kill_sent
                and isinstance(deadline, float)
                and time.monotonic() >= deadline
            ):
                _signal_group(process, cancel_state.get("pgid"), signal.SIGKILL)
                kill_sent = True
                cancel_state["kill_sent"] = True
        except KeyboardInterrupt:
            cancel_state["requested"] = True
            cancel_state.setdefault("deadline", time.monotonic() + term_grace_seconds)
        except (AttributeError, OSError, ProcessLookupError) as error:
            raise NativeLaunchError("parent process wait failed") from error


def launch_parent(
    root: Path,
    *,
    parent_id: str,
    parent_profile: str,
    workspace: Path,
    state_dir: Path,
    task_authority: str,
    capability: Mapping[str, Any],
    codex_executable: str | None = None,
    prompt_file: Path | None = None,
    prompt: str | None = None,
    output_dir: Path | None = None,
    popen_factory: Callable[..., Any] = subprocess.Popen,
    drain_timeout_seconds: float = 15.0,
    term_grace_seconds: float = TERM_TO_KILL_GRACE_SECONDS,
    kill_grace_seconds: float = KILL_REAP_GRACE_SECONDS,
) -> dict[str, Any]:
    """Register, claim, launch, and finally drain one fresh Codex parent."""
    binding = prepare_native_binding(
        root,
        parent_id=parent_id,
        parent_profile=parent_profile,
        workspace=workspace,
        state_dir=state_dir,
        task_authority=task_authority,
        capability=capability,
    )
    argv = build_native_argv(binding, codex_executable=codex_executable)
    frozen_capability = capability_with_native_binding(capability, binding, argv)
    policy_source = frozen_capability.get("policy_source")
    if isinstance(policy_source, str) and not Path(policy_source).is_absolute():
        frozen_capability["policy_source"] = str(
            (binding.source_root / policy_source).resolve()
        )
    claim_fresh_launch(binding, argv=argv, require_empty_ledger=True)
    ledger = ParentLedger(parent_id, binding.state_dir)
    pol_src = frozen_capability.get("policy_source")
    if pol_src:
        pol_path = Path(pol_src)
        if not pol_path.is_absolute():
            pol_path = (binding.source_root / pol_path).resolve()
    else:
        pol_path = (binding.source_root / "common/dispatcher/workers.toml").resolve()
    ledger.initialize_parent(
        parent_family="codex_parent",
        workspace=binding.workspace,
        task_authority=task_authority,
        policy_path=pol_path,
        worker_capability=frozen_capability,
    )
    status = ledger.get_status()
    if status.get("worker_capability", {}).get("policy_selection") != TRIPLE_POOL:
        raise NativeLaunchError("parent ledger is not bound to triple_pool_4x4x4")
    from .parent_custody import run_bound_parent
    return run_bound_parent(
        binding, argv, ledger, popen_factory=popen_factory, prompt_file=prompt_file,
        prompt=prompt, output_dir=output_dir,
        drain_timeout_seconds=drain_timeout_seconds,
        term_grace_seconds=term_grace_seconds, kill_grace_seconds=kill_grace_seconds,
    )
