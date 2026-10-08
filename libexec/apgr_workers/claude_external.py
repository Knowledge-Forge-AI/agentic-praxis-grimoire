"""Direct, bounded Claude CLI transport for an external Sonnet leaf worker.

The parent supplies the selected worker-policy profile name ("sonnet-worker").
This module reads that profile from bundle and catalog, constructs a fixed
``claude`` CLI invocation with restricted mode and leaf tool confinement, and
parses stream-json events without exposing arbitrary executable, model,
credential, or parent-context arguments to the worker interface.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .claude_events import (parse_claude_events as parse_claude_events,
                            classify_explicit_quota as classify_explicit_quota,
                            classify_quota_evidence as classify_quota_evidence)

_PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
CANONICAL_SONNET_PROFILE = "sonnet-worker"
CANONICAL_SONNET_MODEL = "claude-sonnet-5-5"
CANONICAL_SONNET_EFFORT = "high"


class ClaudeExternalError(ValueError):
    """The tracked Sonnet leaf profile or fixed transport contract is invalid."""


@dataclass(frozen=True)
class SonnetProfile:
    """Source-owned model and runtime settings for one Sonnet leaf."""

    name: str
    model: str
    effort: str
    source: str
    source_sha256: str
    projection_matches_selected: bool = True

    def evidence(self) -> dict[str, Any]:
        """Return non-secret profile provenance suitable for a worker result."""
        return {
            "profile": self.name,
            "model": self.model,
            "effort": self.effort,
            "source": self.source,
            "source_sha256": self.source_sha256,
            "projection_matches_selected": self.projection_matches_selected,
        }


def _repository_root(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def load_sonnet_profile(
    root: Path | None = None, profile: str | None = None
) -> SonnetProfile:
    """Load and validate the external Sonnet profile from bundle and catalog."""
    repository = _repository_root(root)
    profile = profile or CANONICAL_SONNET_PROFILE
    if profile != CANONICAL_SONNET_PROFILE:
        raise ClaudeExternalError(f"selected worker policy requires profile {CANONICAL_SONNET_PROFILE!r}")
    if not isinstance(profile, str) or not _PROFILE_RE.fullmatch(profile):
        raise ClaudeExternalError(f"invalid Sonnet worker profile name {profile!r}")

    from agent_phase.runtime_models import selection
    from claude_model_catalog import load_catalog
    try:
        selected = selection(repository, "claude", profile)
        catalog = load_catalog(repository / "claude")
        if not any(record.id == selected["model"] for record in catalog.models.values()):
            raise ClaudeExternalError("selected Sonnet is absent from its source catalog")
        if (selected["model"], selected["effort"]) != (CANONICAL_SONNET_MODEL, CANONICAL_SONNET_EFFORT):
            raise ClaudeExternalError("Sonnet requires claude-sonnet-5-5/high")
        source = repository / "common/dispatcher/models.toml"
        return SonnetProfile(profile, selected["model"], selected["effort"],
                             source.relative_to(repository).as_posix(), hashlib.sha256(source.read_bytes()).hexdigest())
    except (OSError, ValueError, KeyError) as error:
        raise ClaudeExternalError("source-owned Sonnet selection is unavailable") from error


def build_claude_argv(
    profile: SonnetProfile,
    workspace: Path,
    task_authority: str,
    mutation_scope: list[str] | None = None,
) -> list[str]:
    """Build the fixed installed ``claude`` argv for a Sonnet leaf."""
    if (
        not isinstance(profile, SonnetProfile)
        or not profile.name
        or not profile.model
        or not profile.effort
    ):
        raise ClaudeExternalError(
            "external Sonnet transport requires a valid SonnetProfile"
        )
    workspace = Path(workspace).expanduser().resolve()
    if task_authority not in {"read_only", "mutation_capable"}:
        raise ClaudeExternalError("task authority must be read_only or mutation_capable")
    if task_authority == "mutation_capable" and not mutation_scope:
        raise ClaudeExternalError("mutation_capable tasks require an explicit mutation_scope")

    argv = [
        "claude",
        "--print",
        "--verbose",
        "--output-format",
        "stream-json",
        "--model",
        profile.model,
        "--effort",
        profile.effort,
        "--restricted",
        "--setting-sources",
        "",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--strict-mcp-config",
        "--disallowed-tools",
        "Agent,Task",
        "--no-chrome",
        "--disable-slash-commands",
    ]

    if task_authority == "read_only":
        argv.extend([
            "--permission-mode",
            "plan",
            "--tools",
            "Read,Glob,Grep",
        ])
    else:
        argv.extend([
            "--permission-mode",
            "acceptEdits",
            "--tools",
            "Read,Glob,Grep,Write,Edit",
        ])

    return argv


build_claude_exec_argv = build_claude_argv


def scrub_leaf_environment(
    env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Scrub parent APGR identity and session state while preserving provider auth."""
    child_env = dict(os.environ if env is None else env)
    for key in list(child_env):
        if key.startswith(("APGR_", "CODEX_", "AGENT_CENTRAL")) or (
            key.startswith("CLAUDE_CODE_") and key != "CLAUDE_CODE_OAUTH_TOKEN"
        ):
            child_env.pop(key, None)
    child_env["APGR_WORKER_LEAF"] = "1"
    return child_env
