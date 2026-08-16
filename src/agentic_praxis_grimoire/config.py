"""Small declarative APGR configuration and scalar precedence resolver."""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import stat
from typing import Any

try:  # pragma: no cover - the branch depends on the supported interpreter.
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10.
    import tomli as tomllib  # type: ignore[no-redef]

from .paths import (
    discover_project_root,
    global_config_path,
    project_config_path,
    reject_reserved_adapter_path,
    resolve_global_home,
)


class ConfigError(ValueError):
    """Raised for malformed or unsupported APGR configuration."""


DEFAULT_OUTBOX_RELATIVE = Path("Documents") / "agent" / "outbox"
SUPPORTED_KEYS = frozenset({"outbox_root"})


def _absolute(value: str | os.PathLike[str], label: str) -> Path:
    try:
        raw = os.fspath(value)
        if not isinstance(raw, str):
            raise TypeError("path must be text")
        if any(ord(character) < 32 or ord(character) == 127 for character in raw):
            raise ConfigError(f"{label} contains a control character")
        path = Path(raw).expanduser()
    except ConfigError:
        raise
    except (TypeError, ValueError, RuntimeError) as error:
        raise ConfigError(f"{label} is not a valid path") from error
    if not path.is_absolute():
        raise ConfigError(f"{label} must be an absolute path")
    return path


def load_config(path: str | os.PathLike[str]) -> dict[str, Path]:
    """Read one APGR TOML file with a deliberately scalar schema."""

    config_path = _absolute(path, "configuration path")
    try:
        metadata = config_path.lstat()
    except FileNotFoundError:
        return {}
    except OSError as error:
        raise ConfigError(f"could not inspect configuration: {config_path}") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ConfigError("configuration path is not an ordinary file")
    try:
        values: Any = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"could not read configuration: {config_path}") from error
    if not isinstance(values, dict):
        raise ConfigError("configuration must be a TOML table")
    unknown = sorted(set(values) - SUPPORTED_KEYS)
    if unknown:
        raise ConfigError(f"unsupported configuration key: {unknown[0]}")
    if "outbox_root" not in values:
        return {}
    value = values["outbox_root"]
    if not isinstance(value, str) or not value:
        raise ConfigError("outbox_root must be a non-empty string")
    return {"outbox_root": _absolute(value, "outbox_root")}


def default_outbox_root(
    *,
    home: str | os.PathLike[str] | None = None,
) -> Path:
    """Return the built-in terminal outbox root beneath the operator home."""

    operator_home = Path.home() if home is None else _absolute(home, "HOME")
    return operator_home / DEFAULT_OUTBOX_RELATIVE


def resolve_outbox_root(
    explicit: str | os.PathLike[str] | None = None,
    *,
    project_root: str | os.PathLike[str] | None = None,
    apgr_home: str | os.PathLike[str] | None = None,
    cli_home: str | os.PathLike[str] | None = None,
    global_home: str | os.PathLike[str] | None = None,
    environment: Mapping[str, str] | None = None,
    home: str | os.PathLike[str] | None = None,
    start: str | os.PathLike[str] | None = None,
) -> Path:
    """Resolve the scalar outbox setting in explicit/project/global/default order."""

    selected_cli_home = (
        cli_home
        if cli_home is not None
        else apgr_home
        if apgr_home is not None
        else global_home
    )
    if explicit is not None:
        value = _absolute(explicit, "--outbox-root")
        selected_home = resolve_global_home(
            selected_cli_home,
            environment=environment,
            home=home,
        )
        return reject_reserved_adapter_path(value, selected_home)

    selected_home = resolve_global_home(
        selected_cli_home,
        environment=environment,
        home=home,
    )
    project = project_root
    if project is None and start is not None:
        project = discover_project_root(start)
    if project is not None:
        project_path = Path(project).expanduser()
        project_values = load_config(project_config_path(project_path))
        if "outbox_root" in project_values:
            return reject_reserved_adapter_path(
                project_values["outbox_root"], selected_home
            )
    global_values = load_config(global_config_path(selected_home))
    if "outbox_root" in global_values:
        return reject_reserved_adapter_path(global_values["outbox_root"], selected_home)
    return reject_reserved_adapter_path(default_outbox_root(home=home), selected_home)


def resolved_configuration(
    *,
    explicit: str | os.PathLike[str] | None = None,
    project_root: str | os.PathLike[str] | None = None,
    apgr_home: str | os.PathLike[str] | None = None,
    environment: Mapping[str, str] | None = None,
    home: str | os.PathLike[str] | None = None,
) -> dict[str, Path]:
    """Expose the resolved scalar for callers that need structured output."""

    return {
        "outbox_root": resolve_outbox_root(
            explicit,
            project_root=project_root,
            apgr_home=apgr_home,
            environment=environment,
            home=home,
        )
    }


__all__ = [
    "ConfigError",
    "DEFAULT_OUTBOX_RELATIVE",
    "default_outbox_root",
    "discover_project_root",
    "global_config_path",
    "load_config",
    "project_config_path",
    "resolve_outbox_root",
    "resolved_configuration",
]
