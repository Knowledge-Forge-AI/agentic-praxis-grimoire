"""Small declarative APGR configuration and scalar precedence resolver."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import os
import re
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

SUPPORTED_TOP_LEVEL_KEYS = frozenset({"outbox_root", "dispatcher", "integrations", "skills"})
SUPPORTED_DISPATCHER_KEYS = frozenset({"bundle", "routing", "review_mutation", "context", "observations"})
_CONTEXT_KEYS = frozenset({"mode", "max_initial_context_bytes", "max_initial_context_characters",
                           "manifest_facts", "skills", "facts", "instructions"})
_CONTEXT_INSTRUCTION_MODES = ("projected", "static")
# Identical to libexec/agent_phase/context_inputs.py; a dispatcher parity test
# binds the two closed configuration owners together.
_CONTEXT_FACT_KINDS = ("language", "runtime", "test_framework", "repository_characteristic", "capability")
_CONTEXT_STAGES = ("plan", "review", "work")
_CONTEXT_SKILL_ID = re.compile(r"^(apgr|project|user):[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_CONTEXT_FACT_VALUE = re.compile(r"^[a-z0-9][a-z0-9._+-]{0,63}\Z")


def _validate_context_request(item: Any) -> str:
    if isinstance(item, str):
        item = {"id": item}
    if not isinstance(item, dict) or set(item) - {"id", "required", "stages"} or "id" not in item:
        raise ConfigError("skill request must be an ID or a table with id, required and stages")
    if not isinstance(item["id"], str) or not _CONTEXT_SKILL_ID.match(item["id"]):
        raise ConfigError(f"invalid qualified skill ID: {item['id']!r}")
    if "required" in item and type(item["required"]) is not bool:
        raise ConfigError("skill request required must be a boolean")
    stages = item.get("stages", list(_CONTEXT_STAGES))
    if (not isinstance(stages, list) or not stages or len(set(stages)) != len(stages)
            or any(s not in _CONTEXT_STAGES for s in stages)):
        raise ConfigError("skill request stages must be a non-empty subset of plan, review and work")
    return item["id"]


def _validate_context_inputs(context: dict[str, Any]) -> None:
    if "manifest_facts" in context and type(context["manifest_facts"]) is not bool:
        raise ConfigError("dispatcher.context.manifest_facts must be a boolean")
    if "instructions" in context and context["instructions"] not in _CONTEXT_INSTRUCTION_MODES:
        raise ConfigError("dispatcher.context.instructions must be projected or static")
    if "skills" in context:
        skills = context["skills"]
        if not isinstance(skills, list) or len(skills) > 64:
            raise ConfigError("dispatcher.context.skills must be a list of at most 64 entries")
        seen: set[str] = set()
        for item in skills:
            identifier = _validate_context_request(item)
            if identifier in seen:
                raise ConfigError(f"duplicate dispatcher.context.skills entry: {identifier}")
            seen.add(identifier)
    if "facts" in context:
        facts = context["facts"]
        if not isinstance(facts, dict):
            raise ConfigError("dispatcher.context.facts must be a table")
        for kind, values in facts.items():
            if kind == "work_class":
                raise ConfigError("dispatcher.context.facts.work_class is dispatcher-owned")
            if kind not in _CONTEXT_FACT_KINDS:
                raise ConfigError(f"unsupported dispatcher.context.facts kind: {kind}")
            if (not isinstance(values, list) or len(values) > 32
                    or any(not isinstance(v, str) or not _CONTEXT_FACT_VALUE.match(v) for v in values)
                    or len(set(values)) != len(values)):
                raise ConfigError(f"dispatcher.context.facts.{kind} must be a list of distinct "
                                  "lowercase fact values")
SUPPORTED_ROUTING_KEYS = frozenset({"execution_mode"})
SUPPORTED_REVIEW_MUTATION_KEYS = frozenset({"worktree", "index", "head"})
SUPPORTED_WORKTREE_POLICIES = frozenset({"block", "warn", "allow"})

SUPPORTED_INTEGRATIONS_KEYS = frozenset({"rtk"})
SUPPORTED_RTK_KEYS = frozenset(
    {"enabled", "executable", "required", "minimum_version", "providers"}
)
SUPPORTED_PROVIDER_KEYS = frozenset({"claude", "codex", "antigravity"})
SUPPORTED_CLAUDE_MODES = frozenset({"hook", "instructions", "off"})
SUPPORTED_CODEX_MODES = frozenset({"instructions", "hook", "off"})
SUPPORTED_ANTIGRAVITY_MODES = frozenset({"instructions", "hook", "off"})

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


def load_config(
    path: str | os.PathLike[str],
    raw_bytes: bytes | None = None,
) -> dict[str, Any]:
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
        if raw_bytes is not None:
            text = raw_bytes.decode("utf-8")
        else:
            text = config_path.read_text(encoding="utf-8")
        values: Any = tomllib.loads(text)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"could not read configuration: {config_path}") from error
    if not isinstance(values, dict):
        raise ConfigError("configuration must be a TOML table")
    unknown = sorted(set(values) - SUPPORTED_TOP_LEVEL_KEYS)
    if unknown:
        raise ConfigError(f"unsupported configuration key: {unknown[0]}")
    if "skills" in values:
        table = values["skills"]
        if not isinstance(table, dict) or set(table) - {"overrides"}:
            raise ConfigError("skills supports only the overrides table")
        overrides = table.get("overrides", {})
        if not isinstance(overrides, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in overrides.items()
        ):
            raise ConfigError("skills.overrides must map strings to strings")
    result: dict[str, Any] = {}
    if "skills" in values:
        result["skills"] = values["skills"]
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
        if "bundle" in dispatcher_table:
            bundle = dispatcher_table["bundle"]
            if not isinstance(bundle, dict) or set(bundle) - {"required"}:
                raise ConfigError("dispatcher.bundle supports only required")
            if "required" in bundle and type(bundle["required"]) is not bool:
                raise ConfigError("dispatcher.bundle.required must be a boolean")
            result.setdefault("dispatcher", {})["bundle"] = dict(bundle)
        if "observations" in dispatcher_table:
            observations = dispatcher_table["observations"]
            if not isinstance(observations, dict) or set(observations) - {"enabled"}:
                raise ConfigError("dispatcher.observations supports only enabled")
            if "enabled" in observations and type(observations["enabled"]) is not bool:
                raise ConfigError("dispatcher.observations.enabled must be a boolean")
            result.setdefault("dispatcher", {})["observations"] = dict(observations)
        if "context" in dispatcher_table:
            context = dispatcher_table["context"]
            if not isinstance(context, dict):
                raise ConfigError("dispatcher.context must be a table")
            if set(context) - _CONTEXT_KEYS:
                raise ConfigError("unsupported dispatcher.context key")
            _validate_context_inputs(context)
            if "mode" in context and context["mode"] not in ("static", "adaptive"):
                raise ConfigError("dispatcher.context.mode must be static or adaptive")
            for key in ("max_initial_context_bytes", "max_initial_context_characters"):
                if key in context and (type(context[key]) is not int or context[key] < 0):
                    raise ConfigError("dispatcher.context limits must be non-negative integers")
            result.setdefault("dispatcher", {})["context"] = dict(context)

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
        if "review_mutation" in dispatcher_table:
            rm_table = dispatcher_table["review_mutation"]
            if not isinstance(rm_table, dict):
                raise ConfigError("dispatcher.review_mutation configuration must be a TOML table")
            unknown_rm = sorted(set(rm_table) - SUPPORTED_REVIEW_MUTATION_KEYS)
            if unknown_rm:
                raise ConfigError(f"unsupported review_mutation configuration key: {unknown_rm[0]}")
            rm_dict: dict[str, str] = {}
            if "worktree" in rm_table:
                wt = rm_table["worktree"]
                if not isinstance(wt, str) or wt not in SUPPORTED_WORKTREE_POLICIES:
                    raise ConfigError(f"unsupported worktree review mutation policy: {wt}")
                rm_dict["worktree"] = wt
            if "index" in rm_table:
                idx = rm_table["index"]
                if not isinstance(idx, str) or idx != "block":
                    raise ConfigError(f"index review mutation policy must be 'block', got: {idx}")
                rm_dict["index"] = idx
            if "head" in rm_table:
                hd = rm_table["head"]
                if not isinstance(hd, str) or hd != "block":
                    raise ConfigError(f"head review mutation policy must be 'block', got: {hd}")
                rm_dict["head"] = hd
            result.setdefault("dispatcher", {})["review_mutation"] = rm_dict
    if "integrations" in values:
        integrations_table = values["integrations"]
        if not isinstance(integrations_table, dict):
            raise ConfigError("integrations configuration must be a TOML table")
        unknown_integrations = sorted(set(integrations_table) - SUPPORTED_INTEGRATIONS_KEYS)
        if unknown_integrations:
            raise ConfigError(f"unsupported integrations configuration key: {unknown_integrations[0]}")
        if "rtk" in integrations_table:
            rtk_table = integrations_table["rtk"]
            if not isinstance(rtk_table, dict):
                raise ConfigError("integrations.rtk configuration must be a TOML table")
            unknown_rtk = sorted(set(rtk_table) - SUPPORTED_RTK_KEYS)
            if unknown_rtk:
                raise ConfigError(f"unsupported integrations.rtk configuration key: {unknown_rtk[0]}")
            rtk_dict: dict[str, Any] = {}
            if "enabled" in rtk_table:
                enabled = rtk_table["enabled"]
                if not isinstance(enabled, bool):
                    raise ConfigError("integrations.rtk.enabled must be a boolean")
                rtk_dict["enabled"] = enabled
            if "executable" in rtk_table:
                executable = rtk_table["executable"]
                if not isinstance(executable, str) or not executable.strip():
                    raise ConfigError("integrations.rtk.executable must be a non-empty string")
                if executable.startswith("~"):
                    raise ConfigError("integrations.rtk.executable cannot use ~ interpolation; an absolute path is required")
                if "$" in executable:
                    raise ConfigError("integrations.rtk.executable cannot use variable interpolation; an absolute path is required")
                try:
                    raw_exe = os.fspath(executable)
                    if any(ord(c) < 32 or ord(c) == 127 for c in raw_exe):
                        raise ConfigError("integrations.rtk.executable contains a control character")
                    exe_path = Path(raw_exe)
                except ConfigError:
                    raise
                except (TypeError, ValueError, RuntimeError) as error:
                    raise ConfigError("integrations.rtk.executable is not a valid path") from error
                if not exe_path.is_absolute():
                    raise ConfigError("integrations.rtk.executable must be an absolute path")
                rtk_dict["executable"] = exe_path
            if "required" in rtk_table:
                required = rtk_table["required"]
                if not isinstance(required, bool):
                    raise ConfigError("integrations.rtk.required must be a boolean")
                if required:
                    raise ConfigError("strict rtk required=true is deferred; required must be false")
                rtk_dict["required"] = required
            if "minimum_version" in rtk_table:
                min_ver = rtk_table["minimum_version"]
                if not isinstance(min_ver, str) or not min_ver.strip():
                    raise ConfigError("integrations.rtk.minimum_version must be a non-empty string")
                rtk_dict["minimum_version"] = min_ver.strip()
            if "providers" in rtk_table:
                providers_table = rtk_table["providers"]
                if not isinstance(providers_table, dict):
                    raise ConfigError("integrations.rtk.providers configuration must be a TOML table")
                unknown_providers = sorted(set(providers_table) - SUPPORTED_PROVIDER_KEYS)
                if unknown_providers:
                    raise ConfigError(f"unsupported integrations.rtk.providers key: {unknown_providers[0]}")
                prov_dict: dict[str, str] = {}
                if "claude" in providers_table:
                    c_mode = providers_table["claude"]
                    if not isinstance(c_mode, str) or c_mode not in SUPPORTED_CLAUDE_MODES:
                        raise ConfigError(f"unsupported integrations.rtk.providers.claude mode: {c_mode}")
                    prov_dict["claude"] = c_mode
                if "codex" in providers_table:
                    cx_mode = providers_table["codex"]
                    if not isinstance(cx_mode, str) or cx_mode not in SUPPORTED_CODEX_MODES:
                        raise ConfigError(f"unsupported integrations.rtk.providers.codex mode: {cx_mode}")
                    prov_dict["codex"] = cx_mode
                if "antigravity" in providers_table:
                    ag_mode = providers_table["antigravity"]
                    if not isinstance(ag_mode, str) or ag_mode not in SUPPORTED_ANTIGRAVITY_MODES:
                        raise ConfigError(f"unsupported integrations.rtk.providers.antigravity mode: {ag_mode}")
                    prov_dict["antigravity"] = ag_mode
                rtk_dict["providers"] = prov_dict
            result.setdefault("integrations", {})["rtk"] = rtk_dict
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
    values = os.environ if environment is None else environment
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

    env_outbox = values.get("APGR_OUTBOX_ROOT")
    if env_outbox:
        return reject_reserved_adapter_path(
            _absolute(env_outbox, "APGR_OUTBOX_ROOT"), selected_home
        )

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


def resolve_rtk_configuration(*args: Any, **kwargs: Any) -> Any:
    from .rtk import resolve_rtk_configuration as _resolve
    return _resolve(*args, **kwargs)


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
    "resolve_rtk_configuration",
    "resolved_configuration",
]
