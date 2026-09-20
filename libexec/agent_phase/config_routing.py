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
import stat
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


SUPPORTED_POLICY_GENERATION = 9
POLICY_SCHEMA = "agent-phase-policy-v1"
SUPPORTED_WORKTREE_POLICIES = ("warn", "block", "allow")
DEFAULT_WORKTREE_POLICY = "warn"
DEFAULT_GIT_POLICY = "block"
DEFAULT_REVIEW_MUTATION_WORKTREE = DEFAULT_WORKTREE_POLICY
DEFAULT_REVIEW_MUTATION_GIT = DEFAULT_GIT_POLICY



@dataclass(frozen=True)
class ExecutionModeResolution:
    execution_mode: str
    winner: ConfigurationProvenance
    provenance_chain: tuple[ConfigurationProvenance, ...]


@dataclass(frozen=True)
class ReviewMutationPolicy:
    worktree: str = "warn"  # "block" | "warn" | "allow"
    index: str = "block"
    head: str = "block"
    generation: int = SUPPORTED_POLICY_GENERATION

    def as_dict(self) -> dict[str, Any]:
        return {
            "worktree": self.worktree,
            "index": self.index,
            "head": self.head,
            "generation": self.generation,
        }


@dataclass(frozen=True)
class ReviewMutationPolicyResolution:
    policy: ReviewMutationPolicy
    winner: ConfigurationProvenance
    provenance_chain: tuple[ConfigurationProvenance, ...]
    roster: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy.as_dict(),
            "winner": self.winner.as_dict(),
            "provenance_chain": [p.as_dict() for p in self.provenance_chain],
        }


def _absolute_path(value: os.PathLike[str] | str, label: str) -> Path:
    raw = os.fspath(value)
    if not raw or any(ord(c) < 32 or ord(c) == 127 for c in raw):
        raise ConfigError(f"{label} contains invalid or control characters")
    try:
        candidate = Path(raw).expanduser()
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


def resolve_home_with_provenance(
    cli_home: os.PathLike[str] | str | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    home: os.PathLike[str] | str | None = None,
) -> tuple[Path, str]:
    """Resolve APGR home and return (effective_home, precedence_source).

    Precedence:
    1. --apgr-home ('cli')
    2. APGR_HOME ('environment')
    3. ~/.apgr ('default')
    """
    values = os.environ if environment is None else environment
    if cli_home is not None:
        return resolve_global_home(cli_home, environment=environment, home=home), "cli"
    configured = values.get(APGR_HOME_ENVIRONMENT)
    if configured:
        return resolve_global_home(environment=environment, home=home), "environment"
    return resolve_global_home(environment=environment, home=home), "default"


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


_ALLOWED_ROOT_KEYS = {"outbox_root", "dispatcher", "integrations", "skills"}
_ALLOWED_DISPATCHER_KEYS = {"routing", "review_mutation", "context", "bundle", "observations"}
_ALLOWED_ROUTING_KEYS = {"execution_mode"}
_ALLOWED_REVIEW_MUTATION_KEYS = {"worktree", "index", "head"}
_ALLOWED_INTEGRATIONS_KEYS = {"rtk"}
_ALLOWED_RTK_KEYS = {"enabled", "executable", "required", "minimum_version", "providers"}
_ALLOWED_PROVIDER_KEYS = {"claude", "codex", "antigravity"}
_ALLOWED_CLAUDE_MODES = {"hook", "instructions", "off"}
_ALLOWED_CODEX_MODES = {"instructions", "hook", "off"}
_ALLOWED_ANTIGRAVITY_MODES = {"instructions", "hook", "off"}

DEFAULT_OUTBOX_RELATIVE = Path("Documents") / "agent" / "outbox"
RESERVED_ADAPTER_DIRECTORY = "agentic-praxis-grimoire-nd"


def default_outbox_root(home: str | os.PathLike[str] | None = None, **kwargs: Any) -> Path:
    base = Path.home() if home is None else _absolute_path(home, "HOME")
    return (base / DEFAULT_OUTBOX_RELATIVE).resolve()


def reject_reserved_adapter_path(
    path: os.PathLike[str] | str,
    global_home: os.PathLike[str] | str,
) -> Path:
    candidate = _absolute_path(path, "path")
    reserved = _absolute_path(global_home, "APGR home") / RESERVED_ADAPTER_DIRECTORY
    try:
        candidate.resolve().relative_to(reserved.resolve())
    except ValueError:
        return candidate
    raise ConfigError(f"path is inside the reserved adapter root: {reserved}")


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
    **kwargs: Any,
) -> Path:
    values = os.environ if environment is None else environment
    selected_cli_home = (
        cli_home
        if cli_home is not None
        else apgr_home
        if apgr_home is not None
        else global_home
    )
    if explicit is not None:
        val = _absolute_path(explicit, "--outbox-root")
        selected_home = resolve_global_home(
            selected_cli_home,
            environment=environment,
            home=home,
        )
        return reject_reserved_adapter_path(val, selected_home).resolve()

    selected_home = resolve_global_home(
        selected_cli_home,
        environment=environment,
        home=home,
    )
    project = project_root
    if project is None and start is not None:
        project = discover_project_root(start)
    if project is not None:
        project_path = _absolute_path(project, "project_root")
        cfg_path = project_config_path(project_path)
        if cfg_path.is_file():
            p_data = load_config_file(cfg_path)
            if "outbox_root" in p_data:
                val = _absolute_path(p_data["outbox_root"], f"outbox_root in {cfg_path}")
                return reject_reserved_adapter_path(val, selected_home).resolve()

    g_cfg_path = global_config_path(selected_home)
    if g_cfg_path.is_file():
        g_data = load_config_file(g_cfg_path)
        if "outbox_root" in g_data:
            g_val = _absolute_path(g_data["outbox_root"], f"outbox_root in {g_cfg_path}")
            return reject_reserved_adapter_path(g_val, selected_home).resolve()

    env_run_root = values.get("APGR_RUN_ROOT") or values.get("AGENT_PHASE_RUN_ROOT")
    if env_run_root:
        val = _absolute_path(env_run_root, "APGR_RUN_ROOT")
        return reject_reserved_adapter_path(val, selected_home).resolve()

    env_outbox = values.get("APGR_OUTBOX_ROOT")
    if env_outbox:
        val = _absolute_path(env_outbox, "APGR_OUTBOX_ROOT")
        return reject_reserved_adapter_path(val, selected_home).resolve()

    def_root = default_outbox_root(home=home)
    return reject_reserved_adapter_path(def_root, selected_home).resolve()


def _validate_closed_table(data: dict[str, Any], path: Path) -> None:
    unknown_roots = set(data.keys()) - _ALLOWED_ROOT_KEYS
    if unknown_roots:
        first = sorted(unknown_roots)[0]
        raise ConfigError(f"unsupported configuration key in {path}: {first}")

    if "skills" in data:
        table = data["skills"]
        if not isinstance(table, dict) or set(table) - {"overrides"}:
            raise ConfigError("skills supports only the overrides table")
        overrides = table.get("overrides", {})
        if not isinstance(overrides, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in overrides.items()
        ):
            raise ConfigError("skills.overrides must map strings to strings")

    if "outbox_root" in data:
        value = data["outbox_root"]
        if not isinstance(value, str) or not value.strip():
            raise ConfigError(f"outbox_root in {path} must be a non-empty string")
        _absolute_path(value, f"outbox_root in {path}")

    if "dispatcher" in data:
        disp = data["dispatcher"]
        if not isinstance(disp, dict):
            raise ConfigError(f"[dispatcher] in {path} must be a table")
        unknown_disp = set(disp.keys()) - _ALLOWED_DISPATCHER_KEYS
        if unknown_disp:
            first = sorted(unknown_disp)[0]
            raise ConfigError(f"unsupported key in [dispatcher] in {path}: {first}")

        if "bundle" in disp:
            bundle = disp["bundle"]
            if not isinstance(bundle, dict) or set(bundle) - {"required"}:
                raise ConfigError("dispatcher.bundle accepts only required")
            if "required" in bundle and type(bundle["required"]) is not bool:
                raise ConfigError("dispatcher.bundle.required must be a boolean")

        if "observations" in disp:
            observations = disp["observations"]
            if not isinstance(observations, dict) or set(observations) - {"enabled"}:
                raise ConfigError("dispatcher.observations accepts only enabled")
            if "enabled" in observations and type(observations["enabled"]) is not bool:
                raise ConfigError("dispatcher.observations.enabled must be a boolean")

        if "context" in disp:
            context = disp["context"]
            if not isinstance(context, dict):
                raise ConfigError("dispatcher.context must be a table")
            from .context_inputs import CONTEXT_KEYS, validate_context_table
            if set(context) - CONTEXT_KEYS:
                raise ConfigError("unsupported dispatcher.context key")
            validate_context_table(context, ConfigError)
            if "mode" in context and context["mode"] not in ("static", "adaptive"):
                raise ConfigError("dispatcher.context.mode must be static or adaptive")
            for key in ("max_initial_context_bytes", "max_initial_context_characters"):
                if key in context and (type(context[key]) is not int or context[key] < 0):
                    raise ConfigError("dispatcher.context limits must be non-negative integers")

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

        if "review_mutation" in disp:
            rm = disp["review_mutation"]
            if not isinstance(rm, dict):
                raise ConfigError(f"[dispatcher.review_mutation] in {path} must be a table")
            unknown_rm = set(rm.keys()) - _ALLOWED_REVIEW_MUTATION_KEYS
            if unknown_rm:
                first = sorted(unknown_rm)[0]
                raise ConfigError(f"unsupported key in [dispatcher.review_mutation] in {path}: {first}")

            if "worktree" in rm:
                wt = rm["worktree"]
                if not isinstance(wt, str):
                    raise ConfigError(f"worktree review mutation policy in {path} must be a string")
                if wt not in SUPPORTED_WORKTREE_POLICIES:
                    raise ConfigError(f"unsupported worktree review mutation policy in {path}: {wt}")

            if "index" in rm:
                idx = rm["index"]
                if not isinstance(idx, str) or idx != "block":
                    raise ConfigError(f"index review mutation policy must be 'block' in {path}, got: {idx}")

            if "head" in rm:
                hd = rm["head"]
                if not isinstance(hd, str) or hd != "block":
                    raise ConfigError(f"head review mutation policy must be 'block' in {path}, got: {hd}")

    if "integrations" in data:
        integrations = data["integrations"]
        if not isinstance(integrations, dict):
            raise ConfigError(f"[integrations] in {path} must be a table")
        unknown_integrations = set(integrations.keys()) - _ALLOWED_INTEGRATIONS_KEYS
        if unknown_integrations:
            first = sorted(unknown_integrations)[0]
            raise ConfigError(f"unsupported key in [integrations] in {path}: {first}")
        if "rtk" in integrations:
            rtk = integrations["rtk"]
            if not isinstance(rtk, dict):
                raise ConfigError(f"[integrations.rtk] in {path} must be a table")
            unknown_rtk = set(rtk.keys()) - _ALLOWED_RTK_KEYS
            if unknown_rtk:
                first = sorted(unknown_rtk)[0]
                raise ConfigError(f"unsupported key in [integrations.rtk] in {path}: {first}")
            if "enabled" in rtk:
                enabled = rtk["enabled"]
                if not isinstance(enabled, bool):
                    raise ConfigError(f"enabled in [integrations.rtk] in {path} must be a boolean")
            if "executable" in rtk:
                executable = rtk["executable"]
                if not isinstance(executable, str) or not executable.strip():
                    raise ConfigError(f"executable in [integrations.rtk] in {path} must be a non-empty string")
                if executable.startswith("~"):
                    raise ConfigError(f"executable in [integrations.rtk] in {path} cannot use ~ interpolation; an absolute path is required")
                if "$" in executable:
                    raise ConfigError(f"executable in [integrations.rtk] in {path} cannot use variable interpolation; an absolute path is required")
                _absolute_path(executable, f"executable in {path}")
            if "required" in rtk:
                required = rtk["required"]
                if not isinstance(required, bool):
                    raise ConfigError(f"required in [integrations.rtk] in {path} must be a boolean")
                if required:
                    raise ConfigError(f"strict rtk required=true is deferred; required must be false in {path}")
            if "minimum_version" in rtk:
                min_ver = rtk["minimum_version"]
                if not isinstance(min_ver, str) or not min_ver.strip():
                    raise ConfigError(f"minimum_version in [integrations.rtk] in {path} must be a non-empty string")
            if "providers" in rtk:
                provs = rtk["providers"]
                if not isinstance(provs, dict):
                    raise ConfigError(f"[integrations.rtk.providers] in {path} must be a table")
                unknown_provs = set(provs.keys()) - _ALLOWED_PROVIDER_KEYS
                if unknown_provs:
                    first = sorted(unknown_provs)[0]
                    raise ConfigError(f"unsupported key in [integrations.rtk.providers] in {path}: {first}")
                if "claude" in provs:
                    c_mode = provs["claude"]
                    if not isinstance(c_mode, str) or c_mode not in _ALLOWED_CLAUDE_MODES:
                        raise ConfigError(f"unsupported claude mode in [integrations.rtk.providers] in {path}: {c_mode}")
                if "codex" in provs:
                    cx_mode = provs["codex"]
                    if not isinstance(cx_mode, str) or cx_mode not in _ALLOWED_CODEX_MODES:
                        raise ConfigError(f"unsupported codex mode in [integrations.rtk.providers] in {path}: {cx_mode}")
                if "antigravity" in provs:
                    ag_mode = provs["antigravity"]
                    if not isinstance(ag_mode, str) or ag_mode not in _ALLOWED_ANTIGRAVITY_MODES:
                        raise ConfigError(f"unsupported antigravity mode in [integrations.rtk.providers] in {path}: {ag_mode}")



def load_config_file(path: Path, raw_bytes: bytes | None = None) -> dict[str, Any]:
    raw_str = os.fspath(path)
    if any(ord(c) < 32 or ord(c) == 127 for c in raw_str):
        raise ConfigError(f"configuration path contains invalid or control characters: {path}")
    try:
        st = path.lstat()
    except FileNotFoundError:
        return {}
    except OSError as error:
        raise ConfigError(f"could not inspect configuration: {path}") from error
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise ConfigError(f"configuration path is not an ordinary file: {path}")
    data_bytes = raw_bytes if raw_bytes is not None else path.read_bytes()
    try:
        data = tomllib.loads(data_bytes.decode("utf-8"))
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
            values = load_config_file(cfg_path, raw_bytes=raw_bytes)
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
        values = load_config_file(g_cfg_path, raw_bytes=raw_bytes)
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


def load_policy_file(
    path: Path,
    raw_bytes: bytes | None = None,
    expected_generation: int | None = None,
) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"policy file not found at {path}")
    data_bytes = raw_bytes if raw_bytes is not None else path.read_bytes()
    try:
        data = tomllib.loads(data_bytes.decode("utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML in {path}: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"policy root in {path} must be a table")
    _ALLOWED_POLICY_ROOT_KEYS = {"schema", "generation", "review_mutation"}
    unknown_roots = set(data.keys()) - _ALLOWED_POLICY_ROOT_KEYS
    if unknown_roots:
        first = sorted(unknown_roots)[0]
        raise ConfigError(f"unsupported key in policy file {path}: {first}")
    schema = data.get("schema")
    if schema != POLICY_SCHEMA:
        raise ConfigError(f"policy schema in {path} must be '{POLICY_SCHEMA}', got: {schema}")
    generation = data.get("generation")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        raise ConfigError(f"missing or non-integer generation in {path}")
    if expected_generation is not None and generation != expected_generation:
        raise ConfigError(f"policy generation mismatch in {path}: expected {expected_generation}, got: {generation}")
    rm = data.get("review_mutation")
    if not isinstance(rm, dict):
        raise ConfigError(f"[review_mutation] in {path} must be a table")
    unknown_rm = set(rm.keys()) - _ALLOWED_REVIEW_MUTATION_KEYS
    if unknown_rm:
        first = sorted(unknown_rm)[0]
        raise ConfigError(f"unsupported key in [review_mutation] in {path}: {first}")
    wt = rm.get("worktree")
    if wt not in SUPPORTED_WORKTREE_POLICIES:
        raise ConfigError(f"unsupported worktree in [review_mutation] in {path}: {wt}")
    idx = rm.get("index")
    if idx != "block":
        raise ConfigError(f"index in [review_mutation] in {path} must be 'block', got: {idx}")
    hd = rm.get("head")
    if hd != "block":
        raise ConfigError(f"head in [review_mutation] in {path} must be 'block', got: {hd}")
    return data


def resolve_review_mutation_policy(
    explicit: str | None = None,
    *,
    project_root: str | os.PathLike[str] | None = None,
    project: str | os.PathLike[str] | None = None,
    work_tree: str | os.PathLike[str] | None = None,
    apgr_home: str | os.PathLike[str] | None = None,
    cli_home: str | os.PathLike[str] | None = None,
    global_home: str | os.PathLike[str] | None = None,
    repository_root: str | os.PathLike[str] | None = None,
    environment: Mapping[str, str] | None = None,
    home: str | os.PathLike[str] | None = None,
    start: str | os.PathLike[str] | None = None,
    roster: Any | None = None,
) -> ReviewMutationPolicyResolution:
    if explicit is not None and explicit not in SUPPORTED_WORKTREE_POLICIES:
        raise ConfigError(f"unsupported review_mutation_worktree: {explicit}")

    repo_root = (
        Path(repository_root).resolve()
        if repository_root is not None
        else Path(__file__).resolve().parents[2]
    )

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

    eff_project = project_root if project_root is not None else project
    eff_start = start if start is not None else work_tree
    project = eff_project
    if project is None and eff_start is not None:
        project = discover_project_root(eff_start)
    if project is None:
        project = discover_project_root(Path.cwd())

    chain: list[ConfigurationProvenance] = []
    winner: ConfigurationProvenance | None = None
    winner_worktree: str | None = None

    # Tier 1: Explicit CLI
    if explicit is not None:
        winner = ConfigurationProvenance(
            source_type="cli",
            source_path=None,
            content_digest=None,
            resolved_mode=explicit,
            is_winner=True,
            precedence_rank=1,
        )
        winner_worktree = explicit
        chain.append(winner)

    # Tier 2: Project config (.apgr/config.toml)
    if project is not None:
        project_path = Path(project).expanduser()
        cfg_path = project_config_path(project_path)
        if cfg_path.is_file():
            raw_bytes = cfg_path.read_bytes()
            digest = hashlib.sha256(raw_bytes).hexdigest()
            values = load_config_file(cfg_path, raw_bytes=raw_bytes)
            disp = values.get("dispatcher")
            rm = disp.get("review_mutation") if isinstance(disp, dict) else None
            if isinstance(rm, dict) and "worktree" in rm:
                proj_mode = rm["worktree"]
                is_win = winner is None
                prov = ConfigurationProvenance(
                    source_type="project_config",
                    source_path=str(cfg_path),
                    content_digest=digest,
                    resolved_mode=proj_mode,
                    is_winner=is_win,
                    precedence_rank=2,
                )
                if is_win:
                    winner = prov
                    winner_worktree = proj_mode
                chain.append(prov)
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

    # Tier 3: Global config (<APGR_HOME>/config.toml)
    g_cfg_path = global_config_path(selected_home)
    if g_cfg_path.is_file():
        raw_bytes = g_cfg_path.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        values = load_config_file(g_cfg_path, raw_bytes=raw_bytes)
        disp = values.get("dispatcher")
        rm = disp.get("review_mutation") if isinstance(disp, dict) else None
        if isinstance(rm, dict) and "worktree" in rm:
            glob_mode = rm["worktree"]
            is_win = winner is None
            prov = ConfigurationProvenance(
                source_type="global_config",
                source_path=str(g_cfg_path),
                content_digest=digest,
                resolved_mode=glob_mode,
                is_winner=is_win,
                precedence_rank=3,
            )
            if is_win:
                winner = prov
                winner_worktree = glob_mode
            chain.append(prov)
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

    # Tier 4: Operator bundle policy or Tracked default policy
    op_disp = selected_home / "dispatcher"
    bundle_roster = None
    if op_disp.exists():
        if roster is not None and getattr(roster, "policy", None) is not None:
            bundle_roster = roster
        else:
            from .roster import RosterError, load_roster
            try:
                bundle_roster = load_roster(repo_root, apgr_home=selected_home)
            except RosterError as err:
                raise ConfigError(str(err)) from err
        policy_path = op_disp / "policy.toml"
        prov_source_type = "operator_default"
        bundle_generation = bundle_roster.generation
        policy_data = bundle_roster.policy
        policy_mode = policy_data["review_mutation"]["worktree"] if policy_data else DEFAULT_WORKTREE_POLICY
        policy_generation = bundle_roster.generation
        policy_digest = bundle_roster.policy_source.sha256 if bundle_roster.policy_source else None
    else:
        policy_path = repo_root / "common" / "dispatcher" / "policy.toml"
        prov_source_type = "tracked_default"
        bundle_generation = SUPPORTED_POLICY_GENERATION

        policy_mode = DEFAULT_WORKTREE_POLICY
        policy_digest = None
        policy_generation = bundle_generation
        if policy_path.is_file():
            raw_bytes = policy_path.read_bytes()
            policy_digest = hashlib.sha256(raw_bytes).hexdigest()
            policy_data = load_policy_file(policy_path, raw_bytes=raw_bytes, expected_generation=bundle_generation)
            policy_mode = policy_data["review_mutation"]["worktree"]
            policy_generation = policy_data["generation"]

    is_win = winner is None
    default_prov = ConfigurationProvenance(
        source_type=prov_source_type,
        source_path=str(policy_path) if policy_path.is_file() else None,
        content_digest=policy_digest,
        resolved_mode=policy_mode,
        is_winner=is_win,
        precedence_rank=4,
    )
    chain.append(default_prov)
    if is_win:
        winner = default_prov
        winner_worktree = policy_mode

    assert winner is not None
    assert winner_worktree is not None
    policy = ReviewMutationPolicy(
        worktree=winner_worktree,
        index="block",
        head="block",
        generation=policy_generation,
    )
    return ReviewMutationPolicyResolution(
        policy=policy,
        winner=winner,
        provenance_chain=tuple(chain),
        roster=bundle_roster or roster,
    )
