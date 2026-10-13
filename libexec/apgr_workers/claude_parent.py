"""Fresh Claude headless adapter using the existing profile/catalog path."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys

from .claude_native import (
    NATIVE_CAP,
    NATIVE_EFFORT,
    NATIVE_MODEL,
    READ_ONLY_LEAF_TOOLS,
    WRITER_LEAF_TOOLS,
    SCOPED_AGENT_NAME,
)
from .facade_context import WorkerFacadeContext
from .ledger import ParentLedger
from .native_launch import NativeLaunchError, _IDENTIFIER_RE, _outside, claim_fresh_launch
from .policy import identify_parent_family, find_default_policy_path
from .parent_custody import run_bound_parent


@dataclass(frozen=True)
class ClaudeBinding:
    parent_id: str
    parent_family: str
    parent_profile: str
    source_root: Path
    workspace: Path
    state_dir: Path
    task_authority: str
    capability: dict
    facade_enabled: bool
    native_enabled: bool = False
    native_cap: int = NATIVE_CAP
    native_model: str = NATIVE_MODEL
    native_effort: str = NATIVE_EFFORT
    native_agent: str = SCOPED_AGENT_NAME
    plugin_dir: Path | None = None

    def facade_environment(self):
        return WorkerFacadeContext(self.parent_id, self.state_dir, self.source_root,
            self.workspace, self.parent_family, self.task_authority, self.parent_id,
            self.capability["gemini_worker"]["profile"]).environment()

    def evidence(self):
        source = self.source_root / "claude/profiles" / (self.parent_profile + ".json")
        ev = {"provider": "claude", "profile": self.parent_profile,
              "profile_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "parent_id": self.parent_id, "parent_family": self.parent_family,
              "workspace": str(self.workspace), "task_authority": self.task_authority,
              "facade_enabled": self.facade_enabled,
              "policy_sha256": self.capability.get("policy_sha256"),
              "excluded_worker_kinds": self.capability.get("excluded_worker_kinds", []),
              "guidance_source": "claude/CLAUDE.md", "guidance_mechanism": "append-system-prompt"}
        if self.native_enabled:
            ev["native_worker"] = {
                "enabled": True,
                "model": self.native_model,
                "effort": self.native_effort,
                "cap": self.native_cap,
                "agent_name": self.native_agent,
                "mechanism": "plugin-dir",
                "leaf_tools": list(
                    READ_ONLY_LEAF_TOOLS if self.task_authority == "read_only" else WRITER_LEAF_TOOLS
                ),
            }
        return ev

    def launch_binding(self, argv):
        return {"source": "fresh_source_launcher",
                "cap": self.native_cap if self.native_enabled else None,
                "native_enabled": self.native_enabled,
                "facade_enabled": self.facade_enabled,
                "argv_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
                "native_model": self.native_model if self.native_enabled else None,
                "native_effort": self.native_effort if self.native_enabled else None,
                "native_agent": self.native_agent if self.native_enabled else None}


def prepare_claude_binding(root, *, parent_id, parent_profile, workspace, state_dir,
                           task_authority, capability):
    from claude_vc_profile import resolve_profile, PROFILE_CONTRACTS
    if not _IDENTIFIER_RE.fullmatch(parent_id):
        raise NativeLaunchError("parent_id is not a safe identifier")
    root, workspace, state_dir = (Path(p).resolve() for p in (root, workspace, state_dir))
    if not _outside(state_dir, root) or not _outside(state_dir, workspace):
        raise NativeLaunchError("state must be outside source and workspace")
    family = identify_parent_family(root, "claude", parent_profile)
    if family not in {"claude_opus", "claude_fable"}:
        raise NativeLaunchError("select a supported Claude profile; family cannot be inferred")
    resolve_profile(root / "claude", parent_profile)
    if task_authority == "mutation_capable" and PROFILE_CONTRACTS[parent_profile].permission_mode == "plan":
        raise NativeLaunchError("selected profile is read-only; select read_only authority")
    facade = bool(capability.get("allowed_worker_kinds")) and (root / "bin/agent-worker-mcp").is_file()
    native_enabled = (capability.get("policy_selection") == "triple_pool_4x4x4"
                      and capability.get("sonnet_worker", {}).get("transport") == "claude_native")
    plugin_dir = None
    return ClaudeBinding(parent_id, family, parent_profile, root, workspace, state_dir,
                         task_authority, capability, facade,
                         native_enabled=native_enabled, plugin_dir=plugin_dir)


def build_claude_argv(binding):
    argv = [sys.executable, str(binding.source_root / "libexec/claude_vc_profile.py"),
            str(binding.source_root / "claude"), binding.parent_profile, "--print"]
    if binding.task_authority == "read_only":
        argv.append("--read-only")
    if not binding.facade_enabled and binding.task_authority != "read_only":
        argv.extend(["--mcp-config", '{"mcpServers":{}}', "--strict-mcp-config"])
    return argv


def launch_claude_parent(binding, *, prompt=None, prompt_file=None, output_dir=None,
                         popen_factory=None):
    argv = build_claude_argv(binding)
    claim_fresh_launch(binding, argv=argv, require_empty_ledger=True)
    ledger = ParentLedger(binding.parent_id, binding.state_dir)
    ledger.initialize_parent(binding.parent_family, workspace=binding.workspace,
        task_authority=binding.task_authority, worker_capability=binding.capability,
        policy_path=binding.source_root / find_default_policy_path(binding.source_root))
    kwargs = {} if popen_factory is None else {"popen_factory": popen_factory}
    return run_bound_parent(binding, argv, ledger, prompt=prompt,
                            prompt_file=prompt_file, output_dir=output_dir, **kwargs)
