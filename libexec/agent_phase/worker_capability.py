"""Optional worker capability resolution.

The shared worker facility is an enhancement to the local dispatcher.  The
dispatcher must remain importable when that facility is absent or damaged, so
this module deliberately has no import-time dependency on ``agent_workers``.
Only a worker-capable execution-mode request for a
potentially eligible parent reaches the optional import boundary.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import re
import stat
from typing import Any

from .request import WORKER_CAPABLE_MODES


_OPTIONAL_POLICY_MODULE = "agent_workers.policy"
_OPTIONAL_POLICY_API = "resolve_worker_capability"
_PARENT_PROVIDERS = frozenset({"claude", "codex", "antigravity"})
_WORKER_EXECUTABLE = Path("bin/agent-worker")
_PARENT_FAMILIES = frozenset({"claude_fable", "claude_opus", "codex_astra", "gemini_flash"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "mode": "shared-local-worker",
        "available": False,
        "allowed": False,
        "reason": reason,
    }


def _error_detail(error: Exception) -> str:
    """Keep optional-boundary diagnostics useful without preserving newlines."""
    detail = str(error).replace("\n", " ").strip()
    return detail[:240] if detail else "no diagnostic detail"


def _executable_error(root: Path, relative_path: Path = _WORKER_EXECUTABLE) -> str | None:
    path = root / relative_path
    try:
        value = path.stat()
    except OSError as error:
        return (
            "optional worker executable unavailable "
            f"({type(error).__name__}: {_error_detail(error)})"
        )
    if not stat.S_ISREG(value.st_mode):
        return "optional worker executable unavailable (not a regular file)"
    if not os.access(path, os.X_OK):
        return "optional worker executable unavailable (not executable)"
    return None


def _validate_allowed_capability(capability: dict[str, Any]) -> str | None:
    """Check fields consumed by the dispatcher before advertising a worker."""
    if capability.get("available") is not True:
        return "optional worker policy returned an inconsistent capability"
    if capability.get("parent_family") not in _PARENT_FAMILIES:
        return "optional worker policy returned an invalid parent family"
    limits = capability.get("limits")
    if not isinstance(limits, dict):
        return "optional worker policy capability lacks limits"
    for name in ("max_gemini", "max_aggregate"):
        value = limits.get(name)
        if type(value) is not int or value <= 0:
            return f"optional worker policy capability has invalid {name} limit"
    gemini_worker = capability.get("gemini_worker")
    if not isinstance(gemini_worker, dict):
        return "optional worker policy capability lacks Gemini worker details"
    if not isinstance(gemini_worker.get("profile"), str) or not gemini_worker["profile"]:
        return "optional worker policy capability lacks a Gemini worker profile"
    if not isinstance(capability.get("policy_source"), str) or not capability["policy_source"]:
        return "optional worker policy capability lacks policy provenance"
    policy_sha256 = capability.get("policy_sha256")
    if not isinstance(policy_sha256, str) or _SHA256.fullmatch(policy_sha256) is None:
        return "optional worker policy capability has invalid policy provenance"
    return None


def resolve_worker_capability(
    root: Path,
    provider: str,
    profile: str,
    execution_mode: str,
) -> dict[str, Any] | None:
    """Resolve an optional worker capability without coupling ordinary modes.

    Import, API, and resolver failures are local availability failures.  They
    are caught at this optional boundary so the caller can continue the parent
    task.  ``BaseException`` subclasses such as cancellation and
    ``SystemExit`` intentionally propagate.
    """
    if execution_mode not in WORKER_CAPABLE_MODES or provider not in _PARENT_PROVIDERS:
        return None
    if provider == "antigravity" and execution_mode not in (
        "gemini_flash_sub",
        "gemini_flash_opus_sub",
    ):
        return None

    repository_root = Path(root).resolve()
    try:
        module = importlib.import_module(_OPTIONAL_POLICY_MODULE)
        resolver = getattr(module, _OPTIONAL_POLICY_API)
        capability = resolver(repository_root, provider, profile, execution_mode)
    except Exception as error:
        return _unavailable(
            "optional worker policy module unavailable "
            f"({type(error).__name__}: {_error_detail(error)})"
        )

    if capability is None:
        # The policy resolver may intentionally report that an endpoint cannot
        # be a parent.  Preserve that distinction from a broken facility.
        return None
    if not isinstance(capability, dict):
        return _unavailable("optional worker policy returned an invalid capability")
    if capability.get("allowed") is False:
        return capability
    if capability.get("allowed") is not True:
        return _unavailable("optional worker policy returned an invalid capability")

    validation_error = _validate_allowed_capability(capability)
    if validation_error is not None:
        return _unavailable(validation_error)

    executable_error = _executable_error(repository_root)
    if executable_error is not None:
        return _unavailable(executable_error)
    if provider == "claude":
        facade_error = _executable_error(repository_root, Path("bin/agent-worker-mcp"))
        if facade_error is not None:
            return _unavailable("optional worker facade unavailable: " + facade_error)
        capability = {**capability, "interface": "stdio-mcp"}
    elif provider == "antigravity":
        try:
            from agent_workers.gemini_parent import capability_error

            validation_error = capability_error(capability)
        except Exception as error:
            return _unavailable(f"Gemini worker capability validation unavailable ({type(error).__name__})")
        if validation_error is not None:
            return _unavailable(validation_error)
        capability = {**capability, "interface": "cli"}
    return capability
