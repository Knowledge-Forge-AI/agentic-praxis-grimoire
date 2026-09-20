"""Small declarative APGR configuration and scalar precedence resolver."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, NamedTuple

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
DEFAULT_EXECUTION_MODE = "dynamic"

SUPPORTED_TOP_LEVEL_KEYS = frozenset({"outbox_root", "dispatcher"})
SUPPORTED_DISPATCHER_KEYS = frozenset({"routing"})
SUPPORTED_ROUTING_KEYS = frozenset({"execution_mode"})

RETAINED_STATIC_MODES = (
    "normal",
    "gemini_sub",
    "gemini_flash_sub",
    "gemini_flash_opus_sub",
    "conserve_claude",
    "claude_only",
    "codex_only",
    "gemini_only",
    "gemini_opus",
    "gemini_fable",
)
ROUTING_MODES = (DEFAULT_EXECUTION_MODE, *RETAINED_STATIC_MODES)
SUPPORTED_EXECUTION_MODES = frozenset(ROUTING_MODES)
SUPPORTED_KEYS = SUPPORTED_TOP_LEVEL_KEYS


class ConfigurationProvenance(NamedTuple):
    source_type: str
    source_path: str | None
    content_digest: str | None
    resolved_mode: str
    is_winner: bool = False
    precedence_rank: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_path": self.source_path,
            "content_digest": self.content_digest,
            "resolved_mode": self.resolved_mode,
            "is_winner": self.is_winner,
            "precedence_rank": self.precedence_rank,
        }


class ExecutionModeResolution(NamedTuple):
    execution_mode: str
    winner: ConfigurationProvenance
    provenance_chain: tuple[ConfigurationProvenance, ...]


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


def load_config(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Read one APGR TOML file with a closed, declarative schema."""

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
    unknown = sorted(set(values) - SUPPORTED_TOP_LEVEL_KEYS)
    if unknown:
        raise ConfigError(f"unsupported configuration key: {unknown[0]}")
    result: dict[str, Any] = {}
    if "outbox_root" in values:
        value = values["outbox_root"]
        if not isinstance(value, str) or not value:
            raise ConfigError("outbox_root must be a non-empty string")
        result["outbox_root"] = _absolute(value, "outbox_root")
    if "dispatcher" in values:
        dispatcher_table = values["dispatcher"]
        if not isinstance(dispatcher_table, dict):
            raise ConfigError("dispatcher configuration must be a TOML table")
        unknown_dispatcher = sorted(set(dispatcher_table) - SUPPORTED_DISPATCHER_KEYS)
        if unknown_dispatcher:
            raise ConfigError(f"unsupported dispatcher configuration key: {unknown_dispatcher[0]}")
        if "routing" in dispatcher_table:
            routing_table = dispatcher_table["routing"]
            if not isinstance(routing_table, dict):
                raise ConfigError("dispatcher.routing configuration must be a TOML table")
            unknown_routing = sorted(set(routing_table) - SUPPORTED_ROUTING_KEYS)
            if unknown_routing:
                raise ConfigError(f"unsupported routing configuration key: {unknown_routing[0]}")
            if "execution_mode" in routing_table:
                mode = routing_table["execution_mode"]
                if not isinstance(mode, str) or not mode:
                    raise ConfigError("execution_mode must be a non-empty string")
                if mode not in SUPPORTED_EXECUTION_MODES:
                    raise ConfigError(f"unsupported execution_mode: {mode}")
                result.setdefault("dispatcher", {})["routing"] = {"execution_mode": mode}
    return result


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


def resolve_execution_mode(
    explicit: str | None = None,
    *,
    project_root: str | os.PathLike[str] | None = None,
    apgr_home: str | os.PathLike[str] | None = None,
    cli_home: str | os.PathLike[str] | None = None,
    global_home: str | os.PathLike[str] | None = None,
    environment: Mapping[str, str] | None = None,
    home: str | os.PathLike[str] | None = None,
    start: str | os.PathLike[str] | None = None,
) -> ExecutionModeResolution:
    """Resolve execution_mode in explicit CLI / project / global / default order."""

    if explicit is not None:
        if explicit not in SUPPORTED_EXECUTION_MODES:
            raise ConfigError(f"unsupported execution_mode: {explicit}")
        prov = ConfigurationProvenance(
            source_type="cli",
            source_path=None,
            content_digest=None,
            resolved_mode=explicit,
            is_winner=True,
            precedence_rank=1,
        )
        return ExecutionModeResolution(
            execution_mode=explicit,
            winner=prov,
            provenance_chain=(prov,),
        )

    chain: list[ConfigurationProvenance] = []
    selected_cli_home = (
        cli_home
        if cli_home is not None
        else apgr_home
        if apgr_home is not None
        else global_home
    )
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
        cfg_path = project_config_path(project_path)
        if cfg_path.is_file():
            raw_bytes = cfg_path.read_bytes()
            digest = hashlib.sha256(raw_bytes).hexdigest()
            values = load_config(cfg_path)
            disp = values.get("dispatcher")
            routing = disp.get("routing") if isinstance(disp, dict) else None
            if isinstance(routing, dict) and "execution_mode" in routing:
                mode = routing["execution_mode"]
                winner = ConfigurationProvenance(
                    source_type="project_config",
                    source_path=str(cfg_path),
                    content_digest=digest,
                    resolved_mode=mode,
                    is_winner=True,
                    precedence_rank=2,
                )
                chain.append(winner)
                return ExecutionModeResolution(
                    execution_mode=mode,
                    winner=winner,
                    provenance_chain=tuple(chain),
                )
            chain.append(
                ConfigurationProvenance(
                    source_type="project_config",
                    source_path=str(cfg_path),
                    content_digest=digest,
                    resolved_mode="",
                    is_winner=False,
                    precedence_rank=2,
                )
            )

    global_cfg = global_config_path(selected_home)
    if global_cfg.is_file():
        raw_bytes = global_cfg.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        values = load_config(global_cfg)
        disp = values.get("dispatcher")
        routing = disp.get("routing") if isinstance(disp, dict) else None
        if isinstance(routing, dict) and "execution_mode" in routing:
            mode = routing["execution_mode"]
            winner = ConfigurationProvenance(
                source_type="global_config",
                source_path=str(global_cfg),
                content_digest=digest,
                resolved_mode=mode,
                is_winner=True,
                precedence_rank=3,
            )
            chain.append(winner)
            return ExecutionModeResolution(
                execution_mode=mode,
                winner=winner,
                provenance_chain=tuple(chain),
            )
        chain.append(
            ConfigurationProvenance(
                source_type="global_config",
                source_path=str(global_cfg),
                content_digest=digest,
                resolved_mode="",
                is_winner=False,
                precedence_rank=3,
            )
        )

    default_prov = ConfigurationProvenance(
        source_type="default",
        source_path=None,
        content_digest=None,
        resolved_mode=DEFAULT_EXECUTION_MODE,
        is_winner=True,
        precedence_rank=4,
    )
    chain.append(default_prov)
    return ExecutionModeResolution(
        execution_mode=DEFAULT_EXECUTION_MODE,
        winner=default_prov,
        provenance_chain=tuple(chain),
    )


__all__ = [
    "ConfigError",
    "ConfigurationProvenance",
    "DEFAULT_EXECUTION_MODE",
    "DEFAULT_OUTBOX_RELATIVE",
    "ExecutionModeResolution",
    "RETAINED_STATIC_MODES",
    "ROUTING_MODES",
    "SUPPORTED_EXECUTION_MODES",
    "default_outbox_root",
    "discover_project_root",
    "global_config_path",
    "load_config",
    "project_config_path",
    "resolve_execution_mode",
    "resolve_outbox_root",
    "resolved_configuration",
]
