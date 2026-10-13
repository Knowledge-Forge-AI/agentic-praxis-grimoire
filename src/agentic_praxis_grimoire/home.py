"""Canonical operator home layout inspection and resolution (apgr-home-layout-v1)."""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
from pathlib import Path
import stat
from typing import Any

try:  # pragma: no cover - branch depends on Python version
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from .config import (
    default_outbox_root,
    load_config,
    resolve_outbox_root,
)
from .paths import (
    APGR_HOME_ENVIRONMENT,
    _absolute_path,
    resolve_global_home,
)

LAYOUT_VERSION = "apgr-home-layout-v1"


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


def home_layout_paths(
    home_path: Path,
    outbox_root: Path | None = None,
) -> dict[str, Path]:
    """Return canonical directory paths for apgr-home-layout-v1."""
    effective_home = _absolute_path(home_path, "APGR home")
    effective_outbox = (
        _absolute_path(outbox_root, "outbox root")
        if outbox_root is not None
        else default_outbox_root()
    )
    return {
        "home": effective_home,
        "config": effective_home / "config.toml",
        "dispatcher": effective_home / "dispatcher",
        "claude_settings": effective_home / "claude" / "settings.json",
        "database": effective_home / "state" / "dispatcher.sqlite3",
        "state": effective_home / "state",
        "state_runs": effective_home / "state" / "runs",
        "generations": effective_home / "generations",
        "scratch": effective_home / "scratch",
        "skills": effective_home / "skills",
        "outbox_root": effective_outbox,
    }


def inspect_home(
    cli_home: os.PathLike[str] | str | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    home: os.PathLike[str] | str | None = None,
    outbox_root: os.PathLike[str] | str | None = None,
    project_root: os.PathLike[str] | str | None = None,
) -> dict[str, Any]:
    """Inspect the operator home without side effects."""
    effective_home, source = resolve_home_with_provenance(
        cli_home=cli_home, environment=environment, home=home
    )
    resolved_outbox = resolve_outbox_root(
        explicit=outbox_root,
        project_root=project_root,
        apgr_home=effective_home,
        environment=environment,
        home=home,
    )
    paths_dict = home_layout_paths(effective_home, outbox_root=resolved_outbox)

    diagnostics: list[str] = []

    if not effective_home.exists():
        diagnostics.append(f"home directory does not exist: {effective_home}")
    elif effective_home.is_symlink():
        diagnostics.append(f"home directory must not be a symlink: {effective_home}")
    elif not effective_home.is_dir():
        diagnostics.append(f"home path is not a directory: {effective_home}")
    else:
        # Check config
        cfg = paths_dict["config"]
        if cfg.exists():
            if cfg.is_symlink():
                diagnostics.append(f"config file must not be a symlink: {cfg}")
            elif not cfg.is_file():
                diagnostics.append(f"config path is not a regular file: {cfg}")
            else:
                try:
                    load_config(cfg)
                except Exception as err:
                    diagnostics.append(f"config file error: {err}")

        # Check dispatcher roster bundle
        disp = paths_dict["dispatcher"]
        if disp.exists():
            if disp.is_symlink():
                diagnostics.append(f"dispatcher roster directory must not be a symlink: {disp}")
            elif not disp.is_dir():
                diagnostics.append(f"dispatcher roster path is not a directory: {disp}")
            else:
                required_files = ("routes.toml", "endpoints.toml", "capabilities.toml", "policy.toml", "models.toml", "workers.toml")
                missing = [f for f in required_files if not (disp / f).exists()]
                if missing:
                    diagnostics.append(f"partial operator dispatcher roster in {disp}: missing {sorted(missing)}")
                else:
                    symlinked = [f for f in required_files if (disp / f).is_symlink() or not (disp / f).is_file()]
                    if symlinked:
                        diagnostics.append(
                            f"operator dispatcher roster file must be a regular non-symlink file: {disp / sorted(symlinked)[0]}"
                        )
                    else:
                        gens: dict[str, int] = {}
                        for fname in required_files:
                            fpath = disp / fname
                            try:
                                data = tomllib.loads(fpath.read_text(encoding="utf-8"))
                                gen = data.get("generation")
                                if isinstance(gen, int) and not isinstance(gen, bool) and gen >= 1:
                                    gens[fname] = gen
                                else:
                                    diagnostics.append(f"missing or non-integer generation in {fpath}")
                                if fname == "policy.toml":
                                    rm = data.get("review_mutation")
                                    if not isinstance(rm, dict):
                                        diagnostics.append(f"[review_mutation] in {fpath} must be a table")
                                    else:
                                        wt = rm.get("worktree")
                                        if wt not in ("block", "warn", "allow"):
                                            diagnostics.append(f"unsupported worktree in [review_mutation] in {fpath}: {wt}")
                                        idx = rm.get("index")
                                        if idx != "block":
                                            diagnostics.append(f"index in [review_mutation] in {fpath} must be 'block', got: {idx}")
                                        hd = rm.get("head")
                                        if hd != "block":
                                            diagnostics.append(f"head in [review_mutation] in {fpath} must be 'block', got: {hd}")
                            except Exception as err:
                                diagnostics.append(f"cannot read roster file {fpath}: {err}")
                        if len(set(gens.values())) > 1:
                            diagnostics.append(f"operator dispatcher roster generation mismatch: {gens}")

        if disp.is_dir() and not disp.is_symlink():
            try:
                import importlib
                bundle = importlib.import_module("agent_phase.bundle")
                bundle.load_bundle(target_override=disp, required=True)
            except Exception as err:
                diagnostics.append(f"dispatcher bundle error: {err}")

        # Check state directory permissions
        state = paths_dict["state"]
        if state.exists():
            if state.is_symlink():
                diagnostics.append(f"state directory must not be a symlink: {state}")
            elif not state.is_dir():
                diagnostics.append(f"state path is not a directory: {state}")
            else:
                try:
                    st = state.stat()
                    mode = stat.S_IMODE(st.st_mode)
                    if mode != 0o700:
                        diagnostics.append(f"state directory permissions are {oct(mode)}, expected 0700: {state}")
                except OSError as err:
                    diagnostics.append(f"cannot stat state directory {state}: {err}")

        # Check claude settings
        settings = paths_dict["claude_settings"]
        if settings.exists():
            if settings.is_symlink():
                diagnostics.append(f"claude settings must not be a symlink: {settings}")
            elif not settings.is_file():
                diagnostics.append(f"claude settings path is not a regular file: {settings}")
            else:
                try:
                    json.loads(settings.read_text(encoding="utf-8"))
                except Exception as err:
                    diagnostics.append(f"claude settings is invalid JSON: {err}")

    return {
        "layout_version": LAYOUT_VERSION,
        "scope": "resolved_config",
        "precedence_source": source,
        "effective_home": str(effective_home),
        "paths": {k: str(v) for k, v in paths_dict.items()},
        "diagnostics": diagnostics,
    }


__all__ = [
    "LAYOUT_VERSION",
    "home_layout_paths",
    "inspect_home",
    "resolve_home_with_provenance",
]
