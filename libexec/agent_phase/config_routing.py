"""Configuration loading and execution mode resolution for the dispatcher.

Maintains 4-tier precedence:
1. Explicit CLI argument (--execution-mode)
2. Project configuration (.apgr/config.toml -> [dispatcher.routing].execution_mode)
3. Global configuration (<APGR_HOME>/config.toml -> [dispatcher.routing].execution_mode)
4. Default mode ('dynamic')
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tomllib
from typing import Any, Mapping

DEFAULT_EXECUTION_MODE = "dynamic"

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

SUPPORTED_EXECUTION_MODES = (DEFAULT_EXECUTION_MODE, *RETAINED_STATIC_MODES)
ROUTING_MODES = SUPPORTED_EXECUTION_MODES

APGR_HOME_ENVIRONMENT = "APGR_HOME"
CONFIGURATION_FILENAME = "config.toml"


class ConfigError(ValueError):
    """Raised when configuration validation or parsing fails."""


@dataclass(frozen=True)
class ConfigurationProvenance:
    source_type: str  # "cli", "project_config", "global_config", "default"
    source_path: str | None
    content_digest: str | None
    resolved_mode: str
    is_winner: bool
    precedence_rank: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_path": self.source_path,
            "content_digest": self.content_digest,
            "resolved_mode": self.resolved_mode,
            "is_winner": self.is_winner,
            "precedence_rank": self.precedence_rank,
        }


@dataclass(frozen=True)
class ExecutionModeResolution:
    execution_mode: str
    winner: ConfigurationProvenance
    provenance_chain: tuple[ConfigurationProvenance, ...]


def _absolute_path(value: os.PathLike[str] | str, label: str) -> Path:
    try:
        candidate = Path(value).expanduser()
    except (TypeError, ValueError, RuntimeError) as error:
        raise ConfigError(f"{label} is not a valid path") from error
    if not candidate.is_absolute():
        raise ConfigError(f"{label} must be an absolute path")
    return candidate


def resolve_global_home(
    cli_home: os.PathLike[str] | str | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    home: os.PathLike[str] | str | None = None,
) -> Path:
    values = os.environ if environment is None else environment
    if cli_home is not None:
        return _absolute_path(cli_home, "--apgr-home")
    configured = values.get(APGR_HOME_ENVIRONMENT)
    if configured:
        return _absolute_path(configured, APGR_HOME_ENVIRONMENT)
    operator_home = Path.home() if home is None else _absolute_path(home, "HOME")
    return _absolute_path(operator_home / ".apgr", "APGR home")


def discover_project_root(
    start: os.PathLike[str] | str | None = None,
) -> Path | None:
    current = Path.cwd() if start is None else Path(start).expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".apgr").is_dir():
            return candidate
    return None


def project_config_path(project_root: os.PathLike[str] | str) -> Path:
    return Path(project_root) / ".apgr" / CONFIGURATION_FILENAME


def global_config_path(global_home: os.PathLike[str] | str) -> Path:
    return Path(global_home) / CONFIGURATION_FILENAME


_ALLOWED_ROOT_KEYS = {"outbox_root", "dispatcher"}
_ALLOWED_DISPATCHER_KEYS = {"routing"}
_ALLOWED_ROUTING_KEYS = {"execution_mode"}


def _validate_closed_table(data: dict[str, Any], path: Path) -> None:
    unknown_roots = set(data.keys()) - _ALLOWED_ROOT_KEYS
    if unknown_roots:
        first = sorted(unknown_roots)[0]
        raise ConfigError(f"unsupported configuration key in {path}: {first}")

    if "dispatcher" in data:
        disp = data["dispatcher"]
        if not isinstance(disp, dict):
            raise ConfigError(f"[dispatcher] in {path} must be a table")
        unknown_disp = set(disp.keys()) - _ALLOWED_DISPATCHER_KEYS
        if unknown_disp:
            first = sorted(unknown_disp)[0]
            raise ConfigError(f"unsupported key in [dispatcher] in {path}: {first}")

        if "routing" in disp:
            routing = disp["routing"]
            if not isinstance(routing, dict):
                raise ConfigError(f"[dispatcher.routing] in {path} must be a table")
            unknown_routing = set(routing.keys()) - _ALLOWED_ROUTING_KEYS
            if unknown_routing:
                first = sorted(unknown_routing)[0]
                raise ConfigError(f"unsupported key in [dispatcher.routing] in {path}: {first}")

            if "execution_mode" in routing:
                mode = routing["execution_mode"]
                if not isinstance(mode, str):
                    raise ConfigError(f"execution_mode in {path} must be a string")
                if mode not in SUPPORTED_EXECUTION_MODES:
                    raise ConfigError(f"unsupported execution_mode in {path}: {mode}")


def load_config_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML in {path}: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"configuration root in {path} must be a table")

    # Validate closed schema
    _validate_closed_table(data, path)
    return data


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
    if project is None:
        project = discover_project_root(Path.cwd())

    if project is not None:
        project_path = Path(project).expanduser()
        cfg_path = project_config_path(project_path)
        if cfg_path.is_file():
            raw_bytes = cfg_path.read_bytes()
            digest = hashlib.sha256(raw_bytes).hexdigest()
            values = load_config_file(cfg_path)
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
            else:
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

    g_cfg_path = global_config_path(selected_home)
    if g_cfg_path.is_file():
        raw_bytes = g_cfg_path.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        values = load_config_file(g_cfg_path)
        disp = values.get("dispatcher")
        routing = disp.get("routing") if isinstance(disp, dict) else None
        if isinstance(routing, dict) and "execution_mode" in routing:
            mode = routing["execution_mode"]
            winner = ConfigurationProvenance(
                source_type="global_config",
                source_path=str(g_cfg_path),
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
        else:
            chain.append(
                ConfigurationProvenance(
                    source_type="global_config",
                    source_path=str(g_cfg_path),
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
