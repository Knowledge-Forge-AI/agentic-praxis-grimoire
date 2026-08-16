"""Bounded APGR home, project, identifier, and path-safety primitives."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import re


class PathContractError(ValueError):
    """Raised when an APGR path or identifier is outside its contract."""


APGR_HOME_ENVIRONMENT = "APGR_HOME"
CONFIGURATION_FILENAME = "config.toml"
RESERVED_ADAPTER_DIRECTORY = "agentic-praxis-grimoire-nd"
_IDENTIFIER_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _absolute_path(value: os.PathLike[str] | str, label: str) -> Path:
    try:
        candidate = Path(value).expanduser()
    except (TypeError, ValueError, RuntimeError) as error:
        raise PathContractError(f"{label} is not a valid path") from error
    if not candidate.is_absolute():
        raise PathContractError(f"{label} must be an absolute path")
    return candidate


def resolve_global_home(
    cli_home: os.PathLike[str] | str | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    home: os.PathLike[str] | str | None = None,
) -> Path:
    """Resolve ``--apgr-home`` over ``APGR_HOME`` over ``~/.apgr``."""

    values = os.environ if environment is None else environment
    if cli_home is not None:
        return _absolute_path(cli_home, "--apgr-home")
    configured = values.get(APGR_HOME_ENVIRONMENT)
    if configured:
        return _absolute_path(configured, APGR_HOME_ENVIRONMENT)
    operator_home = Path.home() if home is None else _absolute_path(home, "HOME")
    return _absolute_path(operator_home / ".apgr", "APGR home")


def resolve_apgr_home(
    cli_home: os.PathLike[str] | str | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    home: os.PathLike[str] | str | None = None,
) -> Path:
    """Compatibility spelling for :func:`resolve_global_home`."""

    return resolve_global_home(cli_home, environment=environment, home=home)


def ensure_global_home(
    cli_home: os.PathLike[str] | str | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    home: os.PathLike[str] | str | None = None,
) -> Path:
    """Create the APGR home privately and return it.

    The operation is intentionally explicit; merely resolving a path never
    mutates the operator's home.
    """

    path = resolve_global_home(cli_home, environment=environment, home=home)
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise PathContractError("APGR home is not an ordinary directory")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def global_config_path(global_home: os.PathLike[str] | str) -> Path:
    """Return the global declarative configuration file path."""

    return _absolute_path(global_home, "APGR home") / CONFIGURATION_FILENAME


def project_config_root(project_root: os.PathLike[str] | str) -> Path:
    """Return the project-local declarative configuration root."""

    root = _absolute_path(project_root, "project root")
    return root / ".apgr"


def project_config_path(project_root: os.PathLike[str] | str) -> Path:
    """Return ``<project-root>/.apgr/config.toml``."""

    return project_config_root(project_root) / CONFIGURATION_FILENAME


def validate_identifier(value: str, label: str = "identifier") -> str:
    """Validate a bounded project or phase path component."""

    if not isinstance(value, str) or value in {".", ".."}:
        raise PathContractError(f"{label} is not a safe path identifier")
    if "\x00" in value or "/" in value or "\\" in value:
        raise PathContractError(f"{label} must not contain a path separator")
    if not _IDENTIFIER_PATTERN.fullmatch(value):
        raise PathContractError(f"{label} is not a safe path identifier")
    return value


validate_component = validate_identifier


def validate_project_phase(project: str, phase: str) -> tuple[str, str]:
    """Validate both path components used below an outbox root."""

    return validate_identifier(project, "project"), validate_identifier(phase, "phase")


def outbox_phase_path(
    outbox_root: os.PathLike[str] | str,
    project: str,
    phase: str,
) -> Path:
    """Build a safe ``<outbox>/<project>/<phase>`` path without creating it."""

    root = _absolute_path(outbox_root, "outbox root")
    project_name, phase_name = validate_project_phase(project, phase)
    return root / project_name / phase_name


def reserved_adapter_path(global_home: os.PathLike[str] | str) -> Path:
    """Return the reserved future nix-darwin adapter checkout root."""

    return _absolute_path(global_home, "APGR home") / RESERVED_ADAPTER_DIRECTORY


def reject_reserved_adapter_path(
    path: os.PathLike[str] | str,
    global_home: os.PathLike[str] | str,
) -> Path:
    """Reject the reserved adapter root and every descendant beneath it."""

    candidate = _absolute_path(path, "path")
    reserved = reserved_adapter_path(global_home)
    try:
        candidate.resolve(strict=False).relative_to(reserved.resolve(strict=False))
    except ValueError:
        return candidate
    raise PathContractError(
        f"path is inside the reserved adapter root: {reserved}"
    )


def discover_project_root(
    start: os.PathLike[str] | str | None = None,
    *,
    explicit: os.PathLike[str] | str | None = None,
) -> Path | None:
    """Find the nearest Git worktree marker without crossing it.

    An explicit root is allowed for synthetic projects and is never replaced
    by an unrelated ancestor. Without an explicit root, only an ancestor with
    a ``.git`` directory or worktree file is authoritative.
    """

    if explicit is not None:
        root = _absolute_path(explicit, "--project-root")
        if not root.is_dir():
            raise PathContractError("--project-root must be an existing directory")
        return root.resolve()

    candidate = Path.cwd() if start is None else _absolute_path(start, "project search root")
    if candidate.is_file():
        candidate = candidate.parent
    if not candidate.is_dir():
        return None
    candidate = candidate.resolve()
    for root in (candidate, *candidate.parents):
        marker = root / ".git"
        if marker.is_dir() or marker.is_file():
            return root
    return None


def require_project_root(
    start: os.PathLike[str] | str | None = None,
    *,
    explicit: os.PathLike[str] | str | None = None,
) -> Path:
    """Resolve a project root or raise a bounded diagnostic."""

    root = discover_project_root(start, explicit=explicit)
    if root is None:
        raise PathContractError("an APGR project root requires a Git worktree")
    return root


__all__ = [
    "APGR_HOME_ENVIRONMENT",
    "CONFIGURATION_FILENAME",
    "PathContractError",
    "RESERVED_ADAPTER_DIRECTORY",
    "discover_project_root",
    "ensure_global_home",
    "global_config_path",
    "outbox_phase_path",
    "project_config_path",
    "project_config_root",
    "reject_reserved_adapter_path",
    "require_project_root",
    "resolve_apgr_home",
    "resolve_global_home",
    "reserved_adapter_path",
    "validate_identifier",
    "validate_component",
    "validate_project_phase",
]
