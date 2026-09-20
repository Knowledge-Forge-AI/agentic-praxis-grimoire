"""RTK (Rust Token Killer) configuration, resolution, probes, and doctor."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import stat
import subprocess
import time
from typing import IO, Any, Sequence, cast

from .paths import (
    discover_project_root,
    global_config_path,
    project_config_path,
    resolve_global_home,
)

DEFAULT_MINIMUM_VERSION = "0.43.0"
DEFAULT_RTK_TIMEOUT_SECONDS = 5.0
MAX_PROBE_OUTPUT_BYTES = 64 * 1024

SUPPORTED_RTK_KEYS = frozenset(
    {"enabled", "executable", "required", "minimum_version", "providers"}
)
SUPPORTED_PROVIDER_KEYS = frozenset({"claude", "codex", "antigravity"})
SUPPORTED_CLAUDE_MODES = frozenset({"hook", "instructions", "off"})
SUPPORTED_CODEX_MODES = frozenset({"instructions", "hook", "off"})
SUPPORTED_ANTIGRAVITY_MODES = frozenset({"instructions", "hook", "off"})

DEFAULT_PROVIDER_MODES: dict[str, str] = {
    "claude": "hook",
    "codex": "instructions",
    "antigravity": "instructions",
}


@dataclass(frozen=True)
class RTKFieldProvenance:
    source_type: str  # "project_config", "global_config", "default"
    source_path: str | None
    content_digest: str | None
    is_winner: bool
    precedence_rank: int  # project=2, global=3, default=4

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_path": self.source_path,
            "content_digest": self.content_digest,
            "is_winner": self.is_winner,
            "precedence_rank": self.precedence_rank,
        }


@dataclass(frozen=True)
class RTKConfig:
    enabled: bool
    executable: str | None
    required: bool
    minimum_version: str
    providers: dict[str, str]
    provenance: dict[str, RTKFieldProvenance]
    config_digest: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "executable": self.executable,
            "required": self.required,
            "minimum_version": self.minimum_version,
            "providers": dict(self.providers),
            "provenance": {k: v.as_dict() for k, v in self.provenance.items()},
            "config_digest": self.config_digest,
        }


@dataclass(frozen=True)
class RTKResolution:
    config: RTKConfig
    status: str  # "available", "unavailable", "disabled"
    configured_executable: str | None
    resolved_executable: str | None
    executable_identity: dict[str, Any]
    observed_version: str | None
    providers: dict[str, dict[str, str]]
    hook_registration: dict[str, Any]
    canonical_skill: dict[str, Any]
    probes: dict[str, Any]
    diagnostics: list[str]
    configuration_sources: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "enabled": self.config.enabled,
            "required": self.config.required,
            "configured_executable": self.configured_executable,
            "resolved_executable": self.resolved_executable,
            "executable_identity": self.executable_identity,
            "expected_version": f">= {self.config.minimum_version}",
            "observed_version": self.observed_version,
            "providers": self.providers,
            "hook_registration": self.hook_registration,
            "canonical_skill": self.canonical_skill,
            "probes": self.probes,
            "diagnostics": list(self.diagnostics),
            "configuration_sources": list(self.configuration_sources),
        }


def _parse_version(version_str: str) -> tuple[int, ...]:
    clean = version_str.strip().lstrip("v")
    main_part = clean.split("-")[0].split("+")[0]
    parts: list[int] = []
    for chunk in main_part.split("."):
        if chunk.isdigit():
            parts.append(int(chunk))
        else:
            return ()
    if parts and len(parts) < 3:
        while len(parts) < 3:
            parts.append(0)
    return tuple(parts)


def _is_rtk_hook_command(
    cmd: str,
    configured_executable: str | None = None,
    resolved_executable: str | None = None,
) -> bool:
    if not isinstance(cmd, str):
        return False
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return False
    if len(parts) < 3:
        return False
    if parts[1] != "hook" or parts[2] != "claude":
        return False
    exe_token = parts[0]
    exe_name = Path(exe_token).name.lower()
    if "/" not in exe_token and "\\" not in exe_token:
        return exe_name in ("rtk", "rtk.exe")
    if configured_executable:
        try:
            if Path(exe_token).resolve() == Path(configured_executable).resolve():
                return True
        except OSError:
            if exe_token == configured_executable:
                return True
    if resolved_executable:
        try:
            if Path(exe_token).resolve() == Path(resolved_executable).resolve():
                return True
        except OSError:
            if exe_token == resolved_executable:
                return True
    if exe_name in ("rtk", "rtk.exe"):
        return True
    return False


def _matcher_matches_bash(matcher: Any) -> bool | None:
    """Return True if matcher matches tool name 'Bash', False if it definitely
    does not, or None if the matcher syntax is unknown or unsupported.
    """
    if not isinstance(matcher, str):
        return None
    m = matcher.strip()
    if m == "Bash" or m == "^Bash$":
        return True
    if "|" in m:
        parts = [p.strip("^$ ").strip() for p in m.split("|")]
        if "Bash" in parts:
            return True
        if all(p in {"Read", "Edit", "Write", "Glob", "Grep", "NotebookCell"} for p in parts if p):
            return False
    if m in {"Read", "^Read$", "Edit", "^Edit$", "Write", "^Write$", "Glob", "^Glob$", "Grep", "^Grep$"}:
        return False
    try:
        pat = re.compile(m)
        return bool(pat.search("Bash"))
    except re.error:
        return None


def check_claude_hook_registration(
    project_root: Path | None,
    global_home: Path,
    environment: Mapping[str, str] | None = None,
    launch_arguments: Sequence[str] | None = None,
    configured_executable: str | None = None,
    resolved_executable: str | None = None,
) -> dict[str, Any]:
    """Inspect Claude settings files read-only for rtk hook registration."""
    env = os.environ if environment is None else environment
    claude_home = Path(env.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    explicit_sources: list[Path | tuple[str, str]] = []
    isolated_setting_sources = False

    if launch_arguments:
        for index, option in enumerate(launch_arguments):
            if option == "--setting-sources" and index + 1 < len(launch_arguments):
                val = launch_arguments[index + 1]
                if not val.strip():
                    isolated_setting_sources = True
            elif option.startswith("--setting-sources="):
                val = option.split("=", 1)[1]
                if not val.strip():
                    isolated_setting_sources = True
            elif option == "--settings" and index + 1 < len(launch_arguments):
                val = launch_arguments[index + 1]
                if val.strip().startswith("{") and val.strip().endswith("}"):
                    explicit_sources.append(("inline_json", val))
                else:
                    explicit_sources.append(Path(val))
            elif option.startswith("--settings="):
                val = option.split("=", 1)[1]
                if val.strip().startswith("{") and val.strip().endswith("}"):
                    explicit_sources.append(("inline_json", val))
                else:
                    explicit_sources.append(Path(val))

    candidate_sources: list[Path | tuple[str, str]] = list(explicit_sources)
    if not isolated_setting_sources:
        if project_root is not None:
            candidate_sources.append(project_root / ".claude" / "settings.local.json")
            candidate_sources.append(project_root / ".claude" / "settings.json")
        candidate_sources.append(global_home / "claude" / "settings.json")
        candidate_sources.append(claude_home / "settings.json")

    seen: set[str] = set()
    deduped_sources: list[Path | tuple[str, str]] = []
    for s in candidate_sources:
        if isinstance(s, tuple) and s[0] == "inline_json":
            deduped_sources.append(s)
            continue
        try:
            key = str(cast(Path, s).resolve())
        except OSError:
            key = str(s)
        if key not in seen:
            seen.add(key)
            deduped_sources.append(s)

    inspected: list[dict[str, Any]] = []
    registered = False
    registered_source: str | None = None
    registered_command: str | None = None
    hook_diagnostics: list[str] = []

    for source_item in deduped_sources:
        try:
            if isinstance(source_item, tuple) and source_item[0] == "inline_json":
                source_display = "<inline_json>"
                raw = source_item[1]
            else:
                source_path = cast(Path, source_item)
                source_display = str(source_path)
                if not source_path.is_file():
                    continue
                raw = source_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                inspected.append({
                    "path": source_display,
                    "exists": True,
                    "error": "settings_root_not_an_object",
                })
                continue
            has_hook = False
            hook_cmd: str | None = None
            hooks = data.get("hooks", {})
            if isinstance(hooks, dict):
                pre_tool_use = hooks.get("PreToolUse", [])
                if isinstance(pre_tool_use, list):
                    for entry in pre_tool_use:
                        if isinstance(entry, dict):
                            matcher = entry.get("matcher")
                            matches_bash = _matcher_matches_bash(matcher)
                            if matches_bash is None:
                                hook_diagnostics.append(
                                    f"claude hook matcher '{matcher}' in {source_display} is unknown or unsupported"
                                )
                            elif matches_bash is True:
                                subhooks = entry.get("hooks", [])
                                if isinstance(subhooks, list):
                                    for sub in subhooks:
                                        if isinstance(sub, dict):
                                            cmd = sub.get("command", "")
                                            if isinstance(cmd, str) and _is_rtk_hook_command(
                                                cmd,
                                                configured_executable=configured_executable,
                                                resolved_executable=resolved_executable,
                                            ):
                                                has_hook = True
                                                hook_cmd = cmd
                                                break
                                    if has_hook:
                                        break
            inspected.append({
                "path": source_display,
                "exists": True,
                "has_rtk_hook": has_hook,
            })
            if has_hook and not registered:
                registered = True
                registered_source = source_display
                registered_command = hook_cmd
        except (OSError, UnicodeError, json.JSONDecodeError):
            inspected.append({
                "path": str(source_item) if not isinstance(source_item, tuple) else "<inline_json>",
                "exists": True,
                "error": "unreadable_or_invalid_json",
            })

    targeting: str
    if registered and registered_command:
        try:
            parts = shlex.split(registered_command)
        except ValueError:
            parts = registered_command.strip().split()
        hook_bin = parts[0] if parts else ""
        is_bare = "/" not in hook_bin and "\\" not in hook_bin
        if is_bare:
            targeting = "bare_rtk_unresolved"
            hook_diagnostics.append(
                f"claude hook command '{registered_command}' uses bare executable '{hook_bin}'; target binary is unresolved and unverified against configured executable"
            )
        else:
            try:
                hook_bin_resolved = str(Path(hook_bin).resolve())
            except OSError:
                hook_bin_resolved = hook_bin

            target_matches = False
            if resolved_executable:
                try:
                    if hook_bin_resolved == str(Path(resolved_executable).resolve()):
                        target_matches = True
                except OSError:
                    if hook_bin_resolved == resolved_executable:
                        target_matches = True
            if not target_matches and configured_executable:
                try:
                    if hook_bin_resolved == str(Path(configured_executable).resolve()):
                        target_matches = True
                except OSError:
                    if hook_bin == configured_executable:
                        target_matches = True

            if target_matches:
                targeting = "matches_configured_executable"
            else:
                targeting = "mismatched_executable"
                hook_diagnostics.append(
                    f"claude hook executable '{hook_bin}' does not match configured rtk executable '{configured_executable or resolved_executable}'"
                )
    else:
        targeting = "unregistered"

    return {
        "claude": {
            "registered": registered,
            "source_file": registered_source,
            "command": registered_command,
            "targeting": targeting,
            "diagnostics": hook_diagnostics,
            "inspected_sources": inspected,
        }
    }


def inspect_canonical_skill(project_root: Path | None) -> dict[str, Any]:
    """Inspect discoverability of the provisional rtk-command-proxy canonical skill."""
    root = project_root if project_root is not None else Path.cwd()
    skill_path = root / "skills" / "rtk-command-proxy" / "SKILL.md"
    symlink_path = root / ".agents" / "skills" / "rtk-command-proxy"

    skill_exists = skill_path.is_file()
    symlink_exists = symlink_path.is_symlink() or symlink_path.exists()
    symlink_target: str | None = None
    if symlink_path.is_symlink():
        try:
            symlink_target = str(os.readlink(symlink_path))
        except OSError:
            symlink_target = None

    discoverable = skill_exists and symlink_exists
    return {
        "name": "rtk-command-proxy",
        "discoverable": discoverable,
        "path": str(skill_path) if skill_exists else None,
        "projection_path": str(symlink_path) if symlink_exists else None,
        "symlink_target": symlink_target,
    }


class ProbeExecutionResult(tuple):
    """5-element tuple (returncode, stdout, stderr, truncated, diagnostics)
    preserving 5-element unpacking with started and timed_out metadata.
    """
    started: bool
    timed_out: bool
    returncode: int | None
    stdout: str
    stderr: str
    truncated: bool
    diagnostics: list[str]

    def __new__(
        cls,
        returncode: int | None,
        stdout: str,
        stderr: str,
        truncated: bool,
        diagnostics: list[str],
        *,
        started: bool = False,
        timed_out: bool = False,
    ) -> ProbeExecutionResult:
        instance = super().__new__(cls, (returncode, stdout, stderr, truncated, diagnostics))
        instance.started = started
        instance.timed_out = timed_out
        instance.returncode = returncode
        instance.stdout = stdout
        instance.stderr = stderr
        instance.truncated = truncated
        instance.diagnostics = list(diagnostics)
        return instance


def _execute_bounded_probe(
    cmd: Sequence[str],
    deadline: float,
    max_bytes: int = MAX_PROBE_OUTPUT_BYTES,
) -> tuple[int | None, str, str, bool, list[str]]:
    """Execute a probe command with streaming bounded capture and timeout.

    Reaps direct child processes cleanly upon completion or timeout.
    """
    now = time.monotonic()
    if now >= deadline:
        return ProbeExecutionResult(
            None, "", "", False,
            [f"{' '.join(cmd)} probe deadline exceeded before execution"],
            started=False,
            timed_out=True,
        )

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as err:
        return ProbeExecutionResult(
            None, "", "", False,
            [f"{' '.join(cmd)} probe failed to start: {err}"],
            started=False,
            timed_out=False,
        )

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    stdout_bytes = 0
    stderr_bytes = 0
    truncated = False
    diagnostics: list[str] = []

    sel = selectors.DefaultSelector()
    if proc.stdout:
        os.set_blocking(proc.stdout.fileno(), False)
        sel.register(proc.stdout, selectors.EVENT_READ, data="stdout")
    if proc.stderr:
        os.set_blocking(proc.stderr.fileno(), False)
        sel.register(proc.stderr, selectors.EVENT_READ, data="stderr")

    timed_out = False
    try:
        while sel.get_map():
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                timed_out = True
                break
            events = sel.select(timeout=max(0.0, min(0.1, timeout)))
            for key, _ in events:
                stream_name = key.data
                fileobj = cast(IO[bytes], key.fileobj)
                try:
                    chunk = fileobj.read(4096)
                except OSError:
                    chunk = b""
                if chunk is None:
                    continue
                if not chunk:
                    sel.unregister(fileobj)
                else:
                    if stream_name == "stdout":
                        if stdout_bytes + len(chunk) <= max_bytes:
                            stdout_chunks.append(chunk)
                            stdout_bytes += len(chunk)
                        else:
                            allowed = max(0, max_bytes - stdout_bytes)
                            if allowed > 0:
                                stdout_chunks.append(chunk[:allowed])
                                stdout_bytes += allowed
                            truncated = True
                    elif stream_name == "stderr":
                        if stderr_bytes + len(chunk) <= max_bytes:
                            stderr_chunks.append(chunk)
                            stderr_bytes += len(chunk)
                        else:
                            allowed = max(0, max_bytes - stderr_bytes)
                            if allowed > 0:
                                stderr_chunks.append(chunk[:allowed])
                                stderr_bytes += allowed
                            truncated = True
            if proc.poll() is not None and not events:
                break
    finally:
        sel.close()

    raw_stdout = b"".join(stdout_chunks)
    raw_stderr = b"".join(stderr_chunks)

    if timed_out:
        diagnostics.append(f"{' '.join(cmd)} probe timed out")
        try:
            proc.kill()
            proc.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        out_str = raw_stdout.decode("utf-8", errors="replace").strip()
        err_str = raw_stderr.decode("utf-8", errors="replace").strip()
        return ProbeExecutionResult(
            None, out_str, err_str, truncated, diagnostics,
            started=True, timed_out=True,
        )

    try:
        rem = max(0.01, deadline - time.monotonic())
        proc.wait(timeout=rem)
    except subprocess.TimeoutExpired:
        diagnostics.append(f"{' '.join(cmd)} probe timed out waiting for exit")
        try:
            proc.kill()
            proc.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            pass
        out_str = raw_stdout.decode("utf-8", errors="replace").strip()
        err_str = raw_stderr.decode("utf-8", errors="replace").strip()
        return ProbeExecutionResult(
            None, out_str, err_str, truncated, diagnostics,
            started=True, timed_out=True,
        )

    try:
        stdout_str = raw_stdout.decode("utf-8")
    except UnicodeDecodeError:
        stdout_str = raw_stdout.decode("utf-8", errors="replace")
        diagnostics.append(f"{' '.join(cmd)} probe output contained invalid utf-8 bytes (replaced)")

    try:
        stderr_str = raw_stderr.decode("utf-8")
    except UnicodeDecodeError:
        stderr_str = raw_stderr.decode("utf-8", errors="replace")
        diagnostics.append(f"{' '.join(cmd)} probe stderr contained invalid utf-8 bytes (replaced)")

    if truncated:
        diagnostics.append(
            f"{' '.join(cmd)} probe output exceeded {max_bytes} bytes and was truncated"
        )

    return ProbeExecutionResult(
        proc.returncode,
        stdout_str.strip(),
        stderr_str.strip(),
        truncated,
        diagnostics,
        started=True,
        timed_out=False,
    )


def run_rtk_probes(
    executable_path: str,
    minimum_version: str,
    timeout: float = DEFAULT_RTK_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Execute bounded read-only probes against the resolved RTK binary."""
    results: dict[str, Any] = {
        "version": {
            "executed": False,
            "started": False,
            "timed_out": False,
            "command": [executable_path, "--version"],
            "exit_code": None,
            "stdout": None,
            "stderr": None,
            "duration_ms": 0,
            "ok": False,
        },
        "hook_check": {
            "executed": False,
            "started": False,
            "timed_out": False,
            "command": [executable_path, "hook", "check", "git status"],
            "exit_code": None,
            "stdout": None,
            "stderr": None,
            "duration_ms": 0,
            "ok": False,
        },
        "all_ok": False,
        "observed_version": None,
        "diagnostics": [],
    }

    deadline = time.monotonic() + timeout

    # Probe 1: Version check
    t0 = time.monotonic()
    v_res = _execute_bounded_probe(
        [executable_path, "--version"],
        deadline=deadline,
    )
    v_ret, v_stdout, v_stderr, _, v_diags = v_res
    v_started = getattr(v_res, "started", v_ret is not None)
    v_timed_out = getattr(v_res, "timed_out", False)
    v_ms = int((time.monotonic() - t0) * 1000)
    results["diagnostics"].extend(v_diags)
    results["version"]["duration_ms"] = v_ms
    results["version"]["executed"] = bool(v_started)
    results["version"]["started"] = bool(v_started)
    results["version"]["timed_out"] = bool(v_timed_out)
    results["version"]["stdout"] = v_stdout
    results["version"]["stderr"] = v_stderr
    results["version"]["exit_code"] = v_ret

    if v_ret is not None:
        if v_ret == 0 and v_stdout:
            parts = v_stdout.split()
            if not parts or parts[0].lower() != "rtk":
                results["diagnostics"].append(
                    f"rtk --version produced unexpected product banner: '{v_stdout}'"
                )
            else:
                observed = parts[1] if len(parts) >= 2 else parts[0]
                results["observed_version"] = observed
                min_tuple = _parse_version(minimum_version)
                obs_tuple = _parse_version(observed)
                if obs_tuple >= min_tuple:
                    results["version"]["ok"] = True
                else:
                    results["diagnostics"].append(
                        f"observed rtk version {observed} is older than minimum {minimum_version}"
                    )
        else:
            results["diagnostics"].append(
                f"rtk --version failed with exit code {v_ret}: {v_stderr or v_stdout}"
            )

    if not results["version"]["ok"]:
        return results

    # Probe 2: Hook check
    t1 = time.monotonic()
    h_res = _execute_bounded_probe(
        [executable_path, "hook", "check", "git status"],
        deadline=deadline,
    )
    h_ret, h_stdout, h_stderr, _, h_diags = h_res
    h_started = getattr(h_res, "started", h_ret is not None)
    h_timed_out = getattr(h_res, "timed_out", False)
    h_ms = int((time.monotonic() - t1) * 1000)
    results["diagnostics"].extend(h_diags)
    results["hook_check"]["duration_ms"] = h_ms
    results["hook_check"]["executed"] = bool(h_started)
    results["hook_check"]["started"] = bool(h_started)
    results["hook_check"]["timed_out"] = bool(h_timed_out)
    results["hook_check"]["stdout"] = h_stdout
    results["hook_check"]["stderr"] = h_stderr
    results["hook_check"]["exit_code"] = h_ret

    if h_ret is not None:
        if h_ret == 0:
            results["hook_check"]["ok"] = True
        else:
            results["diagnostics"].append(
                f"rtk hook check probe failed with exit code {h_ret}: {h_stderr or h_stdout}"
            )

    results["all_ok"] = results["version"]["ok"] and results["hook_check"]["ok"]
    return results


def resolve_rtk_configuration(
    *,
    project_root: str | os.PathLike[str] | None = None,
    apgr_home: str | os.PathLike[str] | None = None,
    cli_home: str | os.PathLike[str] | None = None,
    global_home: str | os.PathLike[str] | None = None,
    environment: Mapping[str, str] | None = None,
    home: str | os.PathLike[str] | None = None,
    start: str | os.PathLike[str] | None = None,
    run_probes: bool = True,
    probe_timeout: float = DEFAULT_RTK_TIMEOUT_SECONDS,
    launch_arguments: Sequence[str] | None = None,
) -> RTKResolution:
    """Resolve closed [integrations.rtk] configuration with provenance and status."""
    from .config import ConfigError, load_config

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
    if project is None:
        project = discover_project_root(start if start is not None else Path.cwd())

    project_path = Path(project).expanduser().absolute() if project is not None else None

    # Load sources
    project_cfg_path: Path | None = None
    project_data: dict[str, Any] = {}
    project_digest: str | None = None
    project_exists = False
    if project_path is not None:
        cfg = project_config_path(project_path)
        project_cfg_path = cfg
        if cfg.is_file():
            project_exists = True
            raw_bytes = cfg.read_bytes()
            project_digest = hashlib.sha256(raw_bytes).hexdigest()
            project_data = load_config(cfg, raw_bytes=raw_bytes)

    global_cfg_path: Path | None = None
    global_data: dict[str, Any] = {}
    global_digest: str | None = None
    global_exists = False
    g_cfg = global_config_path(selected_home)
    global_cfg_path = g_cfg
    if g_cfg.is_file():
        global_exists = True
        raw_bytes = g_cfg.read_bytes()
        global_digest = hashlib.sha256(raw_bytes).hexdigest()
        global_data = load_config(g_cfg, raw_bytes=raw_bytes)

    config_sources: list[dict[str, Any]] = []
    if project_cfg_path is not None:
        config_sources.append({
            "source_type": "project_config",
            "path": str(project_cfg_path),
            "exists": project_exists,
            "digest": project_digest,
        })
    if global_cfg_path is not None:
        config_sources.append({
            "source_type": "global_config",
            "path": str(global_cfg_path),
            "exists": global_exists,
            "digest": global_digest,
        })

    p_rtk = (
        project_data.get("integrations", {}).get("rtk", {})
        if isinstance(project_data.get("integrations"), dict)
        else {}
    )
    g_rtk = (
        global_data.get("integrations", {}).get("rtk", {})
        if isinstance(global_data.get("integrations"), dict)
        else {}
    )

    # Per-field inheritance: Project > Global > Defaults
    provenance: dict[str, RTKFieldProvenance] = {}

    # 1. enabled
    if "enabled" in p_rtk:
        enabled = bool(p_rtk["enabled"])
        provenance["enabled"] = RTKFieldProvenance(
            source_type="project_config",
            source_path=str(project_cfg_path),
            content_digest=project_digest,
            is_winner=True,
            precedence_rank=2,
        )
    elif "enabled" in g_rtk:
        enabled = bool(g_rtk["enabled"])
        provenance["enabled"] = RTKFieldProvenance(
            source_type="global_config",
            source_path=str(global_cfg_path),
            content_digest=global_digest,
            is_winner=True,
            precedence_rank=3,
        )
    else:
        enabled = False
        provenance["enabled"] = RTKFieldProvenance(
            source_type="default",
            source_path=None,
            content_digest=None,
            is_winner=True,
            precedence_rank=4,
        )

    # 2. executable
    if "executable" in p_rtk and p_rtk["executable"]:
        executable = str(p_rtk["executable"])
        provenance["executable"] = RTKFieldProvenance(
            source_type="project_config",
            source_path=str(project_cfg_path),
            content_digest=project_digest,
            is_winner=True,
            precedence_rank=2,
        )
    elif "executable" in g_rtk and g_rtk["executable"]:
        executable = str(g_rtk["executable"])
        provenance["executable"] = RTKFieldProvenance(
            source_type="global_config",
            source_path=str(global_cfg_path),
            content_digest=global_digest,
            is_winner=True,
            precedence_rank=3,
        )
    else:
        executable = None
        provenance["executable"] = RTKFieldProvenance(
            source_type="default",
            source_path=None,
            content_digest=None,
            is_winner=True,
            precedence_rank=4,
        )

    # 3. required
    if "required" in p_rtk:
        req_val = p_rtk["required"]
        if req_val is True:
            raise ConfigError("strict rtk required=true is deferred; required must be false")
        required = False
        provenance["required"] = RTKFieldProvenance(
            source_type="project_config",
            source_path=str(project_cfg_path),
            content_digest=project_digest,
            is_winner=True,
            precedence_rank=2,
        )
    elif "required" in g_rtk:
        req_val = g_rtk["required"]
        if req_val is True:
            raise ConfigError("strict rtk required=true is deferred; required must be false")
        required = False
        provenance["required"] = RTKFieldProvenance(
            source_type="global_config",
            source_path=str(global_cfg_path),
            content_digest=global_digest,
            is_winner=True,
            precedence_rank=3,
        )
    else:
        required = False
        provenance["required"] = RTKFieldProvenance(
            source_type="default",
            source_path=None,
            content_digest=None,
            is_winner=True,
            precedence_rank=4,
        )

    # 4. minimum_version
    if "minimum_version" in p_rtk and p_rtk["minimum_version"]:
        min_ver = str(p_rtk["minimum_version"])
        provenance["minimum_version"] = RTKFieldProvenance(
            source_type="project_config",
            source_path=str(project_cfg_path),
            content_digest=project_digest,
            is_winner=True,
            precedence_rank=2,
        )
    elif "minimum_version" in g_rtk and g_rtk["minimum_version"]:
        min_ver = str(g_rtk["minimum_version"])
        provenance["minimum_version"] = RTKFieldProvenance(
            source_type="global_config",
            source_path=str(global_cfg_path),
            content_digest=global_digest,
            is_winner=True,
            precedence_rank=3,
        )
    else:
        min_ver = DEFAULT_MINIMUM_VERSION
        provenance["minimum_version"] = RTKFieldProvenance(
            source_type="default",
            source_path=None,
            content_digest=None,
            is_winner=True,
            precedence_rank=4,
        )

    # 5. providers
    p_providers = p_rtk.get("providers", {}) if isinstance(p_rtk.get("providers"), dict) else {}
    g_providers = g_rtk.get("providers", {}) if isinstance(g_rtk.get("providers"), dict) else {}
    resolved_providers: dict[str, str] = {}

    for prov_name in ("claude", "codex", "antigravity"):
        if prov_name in p_providers:
            resolved_providers[prov_name] = p_providers[prov_name]
            provenance[f"providers.{prov_name}"] = RTKFieldProvenance(
                source_type="project_config",
                source_path=str(project_cfg_path),
                content_digest=project_digest,
                is_winner=True,
                precedence_rank=2,
            )
        elif prov_name in g_providers:
            resolved_providers[prov_name] = g_providers[prov_name]
            provenance[f"providers.{prov_name}"] = RTKFieldProvenance(
                source_type="global_config",
                source_path=str(global_cfg_path),
                content_digest=global_digest,
                is_winner=True,
                precedence_rank=3,
            )
        else:
            resolved_providers[prov_name] = DEFAULT_PROVIDER_MODES[prov_name]
            provenance[f"providers.{prov_name}"] = RTKFieldProvenance(
                source_type="default",
                source_path=None,
                content_digest=None,
                is_winner=True,
                precedence_rank=4,
            )

    winning_digest = project_digest or global_digest
    rtk_config = RTKConfig(
        enabled=enabled,
        executable=executable,
        required=required,
        minimum_version=min_ver,
        providers=resolved_providers,
        provenance=provenance,
        config_digest=winning_digest,
    )

    # Inspection & Resolution
    diagnostics: list[str] = []
    status = "disabled"
    resolved_executable_str: str | None = None
    exec_identity: dict[str, Any] = {}
    observed_version: str | None = None
    probes_summary: dict[str, Any] = {
        "version": {"executed": False, "ok": False},
        "hook_check": {"executed": False, "ok": False},
    }

    if not enabled:
        status = "disabled"
        effective_providers = {
            "claude": {
                "declared_mode": resolved_providers["claude"],
                "effective_mode": "off",
                "reason": "rtk_disabled",
            },
            "codex": {
                "declared_mode": resolved_providers["codex"],
                "effective_mode": "off",
                "reason": "rtk_disabled",
            },
            "antigravity": {
                "declared_mode": resolved_providers["antigravity"],
                "effective_mode": "off",
                "reason": "rtk_disabled",
            },
        }
        hook_info: dict[str, Any] = {
            "claude": {
                "registered": False,
                "source_file": None,
                "command": None,
                "targeting": "uninspected",
                "diagnostics": [],
                "inspected_sources": [],
            }
        }
        skill_info = (
            inspect_canonical_skill(project_path)
            if run_probes
            else {
                "name": "rtk-command-proxy",
                "discoverable": False,
                "path": None,
                "projection_path": None,
                "symlink_target": None,
            }
        )
        return RTKResolution(
            config=rtk_config,
            status=status,
            configured_executable=executable,
            resolved_executable=None,
            executable_identity={},
            observed_version=None,
            providers=effective_providers,
            hook_registration=hook_info,
            canonical_skill=skill_info,
            probes=probes_summary,
            diagnostics=diagnostics,
            configuration_sources=config_sources,
        )

    # enabled == True
    if executable is None:
        status = "unavailable"
        diagnostics.append("rtk is enabled but executable is not configured")
    else:
        exec_path = Path(executable)
        if not exec_path.exists():
            status = "unavailable"
            diagnostics.append(f"configured rtk executable does not exist: {executable}")
        else:
            try:
                resolved_path = exec_path.resolve()
                resolved_executable_str = str(resolved_path)
                st = resolved_path.stat()
                is_reg = stat.S_ISREG(st.st_mode)
                is_x = os.access(resolved_path, os.X_OK)
                exec_identity = {
                    "path": resolved_executable_str,
                    "is_regular_file": is_reg,
                    "is_executable": is_x,
                }
                if not is_reg:
                    status = "unavailable"
                    diagnostics.append(
                        f"resolved rtk executable is not a regular file: {resolved_path}"
                    )
                elif not is_x:
                    status = "unavailable"
                    diagnostics.append(
                        f"resolved rtk executable is not executable: {resolved_path}"
                    )
                else:
                    if run_probes:
                        probes_result = run_rtk_probes(
                            resolved_executable_str,
                            min_ver,
                            timeout=probe_timeout,
                        )
                        probes_summary = probes_result
                        observed_version = probes_result.get("observed_version")
                        if not probes_result.get("all_ok"):
                            status = "unavailable"
                            diagnostics.extend(probes_result.get("diagnostics", []))
                        else:
                            status = "available"
                    else:
                        status = "unavailable"
                        diagnostics.append(
                            "rtk executable compatibility was not evaluated (run_probes=False)"
                        )
            except OSError as err:
                status = "unavailable"
                diagnostics.append(f"could not inspect rtk executable: {err}")

    hook_info = check_claude_hook_registration(
        project_path,
        selected_home,
        environment=environment,
        launch_arguments=launch_arguments,
        configured_executable=executable,
        resolved_executable=resolved_executable_str,
    )
    skill_info = inspect_canonical_skill(project_path)
    if hook_info.get("claude", {}).get("diagnostics"):
        diagnostics.extend(hook_info["claude"]["diagnostics"])

    # Provider effective mode logic
    effective_providers = {}
    for prov_name in ("claude", "codex", "antigravity"):
        decl = resolved_providers[prov_name]
        if status != "available":
            effective_providers[prov_name] = {
                "declared_mode": decl,
                "effective_mode": "off",
                "reason": "rtk_unavailable",
            }
        else:
            if prov_name == "claude":
                if decl == "hook":
                    c_hook = hook_info.get("claude", {})
                    if c_hook.get("registered"):
                        c_targeting = c_hook.get("targeting")
                        if c_targeting == "matches_configured_executable":
                            effective_providers["claude"] = {
                                "declared_mode": "hook",
                                "effective_mode": "hook",
                                "reason": "hook_registered",
                            }
                        elif c_targeting == "bare_rtk_unresolved":
                            effective_providers["claude"] = {
                                "declared_mode": "hook",
                                "effective_mode": "off",
                                "reason": "hook_registered_target_unresolved",
                            }
                        else:
                            effective_providers["claude"] = {
                                "declared_mode": "hook",
                                "effective_mode": "off",
                                "reason": "hook_registered_target_mismatch",
                            }
                    else:
                        effective_providers["claude"] = {
                            "declared_mode": "hook",
                            "effective_mode": "off",
                            "reason": "hook_unconfirmed_fallback_to_off",
                        }
                        diagnostics.append("claude provider declared hook mode but hook is unconfirmed; hook fallback to off")
                elif decl == "instructions":
                    c_hook = hook_info.get("claude", {})
                    if c_hook.get("registered") and c_hook.get("targeting") == "matches_configured_executable":
                        effective_providers["claude"] = {
                            "declared_mode": "instructions",
                            "effective_mode": "hook",
                            "reason": "hook_registered_avoids_double_wrap",
                        }
                        diagnostics.append("claude provider declared instructions mode but matching hook is registered; switching claude to hook mode to prevent double-wrapping")
                    else:
                        effective_providers["claude"] = {
                            "declared_mode": "instructions",
                            "effective_mode": "instructions",
                            "reason": "declared_mode",
                        }
                else:
                    effective_providers["claude"] = {
                        "declared_mode": "off",
                        "effective_mode": "off",
                        "reason": "declared_mode",
                    }
            elif prov_name == "codex":
                if decl == "hook":
                    effective_providers["codex"] = {
                        "declared_mode": "hook",
                        "effective_mode": "off",
                        "reason": "codex_hook_unsupported",
                    }
                    diagnostics.append("codex provider does not support hook mode; falling back to off")
                elif decl == "instructions":
                    effective_providers["codex"] = {
                        "declared_mode": "instructions",
                        "effective_mode": "instructions",
                        "reason": "declared_mode",
                    }
                else:
                    effective_providers["codex"] = {
                        "declared_mode": "off",
                        "effective_mode": "off",
                        "reason": "declared_mode",
                    }
            elif prov_name == "antigravity":
                if decl == "hook":
                    effective_providers["antigravity"] = {
                        "declared_mode": "hook",
                        "effective_mode": "off",
                        "reason": "antigravity_hook_unsupported",
                    }
                    diagnostics.append("antigravity provider does not support hook mode; falling back to off")
                elif decl == "instructions":
                    effective_providers["antigravity"] = {
                        "declared_mode": "instructions",
                        "effective_mode": "instructions",
                        "reason": "declared_mode",
                    }
                else:
                    effective_providers["antigravity"] = {
                        "declared_mode": "off",
                        "effective_mode": "off",
                        "reason": "declared_mode",
                    }

    return RTKResolution(
        config=rtk_config,
        status=status,
        configured_executable=executable,
        resolved_executable=resolved_executable_str,
        executable_identity=exec_identity,
        observed_version=observed_version,
        providers=effective_providers,
        hook_registration=hook_info,
        canonical_skill=skill_info,
        probes=probes_summary,
        diagnostics=diagnostics,
        configuration_sources=config_sources,
    )


def doctor_report(
    *,
    project_root: str | os.PathLike[str] | None = None,
    apgr_home: str | os.PathLike[str] | None = None,
    cli_home: str | os.PathLike[str] | None = None,
    global_home: str | os.PathLike[str] | None = None,
    environment: Mapping[str, str] | None = None,
    home: str | os.PathLike[str] | None = None,
    start: str | os.PathLike[str] | None = None,
    launch_arguments: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Run comprehensive read-only RTK doctor diagnostics."""
    resolution = resolve_rtk_configuration(
        project_root=project_root,
        apgr_home=apgr_home,
        cli_home=cli_home,
        global_home=global_home,
        environment=environment,
        home=home,
        start=start,
        run_probes=True,
        launch_arguments=launch_arguments,
    )

    selected_cli_home = (
        cli_home
        if cli_home is not None
        else apgr_home
        if apgr_home is not None
        else global_home
    )
    eff_home = resolve_global_home(
        selected_cli_home, environment=environment, home=home
    )
    eff_proj = project_root
    if eff_proj is None:
        eff_proj = discover_project_root(start if start is not None else Path.cwd())

    result = {
        "doctor_version": "apgr-rtk-doctor-v1",
        "status": resolution.status,
        "effective_home": str(eff_home),
        "target_project": str(eff_proj) if eff_proj else None,
        "configuration_sources": resolution.configuration_sources,
        "enabled": resolution.config.enabled,
        "required": resolution.config.required,
        "configured_executable": resolution.configured_executable,
        "resolved_executable": resolution.resolved_executable,
        "executable_identity": resolution.executable_identity,
        "expected_version": f">= {resolution.config.minimum_version}",
        "observed_version": resolution.observed_version,
        "providers": resolution.providers,
        "hook_registration": resolution.hook_registration,
        "canonical_skill": resolution.canonical_skill,
        "probes": resolution.probes,
        "diagnostics": resolution.diagnostics,
    }
    return result


def render_doctor_report(report: dict[str, Any], json_output: bool = False) -> str:
    """Format doctor report as json or structured text."""
    if json_output:
        return json.dumps(report, indent=2)

    lines = [
        "apgr rtk doctor:",
        f"  status: {report['status']}",
        f"  effective_home: {report['effective_home']}",
        f"  target_project: {report['target_project'] or 'none'}",
        f"  enabled: {str(report['enabled']).lower()}",
        f"  required: {str(report['required']).lower()}",
        f"  configured_executable: {report['configured_executable'] or 'none'}",
        f"  resolved_executable: {report['resolved_executable'] or 'none'}",
    ]
    if report.get("observed_version"):
        lines.append(f"  observed_version: {report['observed_version']} (expected: {report['expected_version']})")
    else:
        lines.append(f"  expected_version: {report['expected_version']}")

    lines.append("  providers:")
    for prov, pdata in sorted(report.get("providers", {}).items()):
        lines.append(
            f"    {prov}: {pdata['declared_mode']} (effective: {pdata['effective_mode']}, reason: {pdata['reason']})"
        )

    claude_hook = report.get("hook_registration", {}).get("claude", {})
    if claude_hook.get("registered"):
        lines.append(f"  hook_registration:\n    claude: registered ({claude_hook.get('source_file')})")
    else:
        lines.append("  hook_registration:\n    claude: not registered")

    skill = report.get("canonical_skill", {})
    skill_status = "discoverable" if skill.get("discoverable") else "unavailable"
    lines.append(f"  canonical_skill:\n    {skill.get('name')}: {skill_status}")

    if report.get("diagnostics"):
        lines.append("  diagnostics:")
        for diag in report["diagnostics"]:
            lines.append(f"    - {diag}")

    return "\n".join(lines) + "\n"
