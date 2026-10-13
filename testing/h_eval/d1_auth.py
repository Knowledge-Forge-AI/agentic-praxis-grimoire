"""Narrow D1 authentication context and non-consuming supported CLI preflight.

Only paths/identity variables are retained. Credential contents and token
variables are never copied into evidence or forwarded by this owner.
"""
import json
import re
import subprocess
from pathlib import Path

AUTH_NAMES = frozenset({"HOME", "USER", "LOGNAME", "CLAUDE_CONFIG_DIR", "SECURITYSESSIONID"})
AUTH_SCHEMA = "apg.d1-auth-context/v1"
FIXED_OPTIONS = ("--safe-mode", "--no-session-persistence")


def validate_context(values, *, forbidden_roots=()):
    if (not isinstance(values, dict) or "HOME" not in values
            or not set(values) <= AUTH_NAMES
            or any(not isinstance(v, str) or not v or "\0" in v for v in values.values())):
        raise ValueError("invalid D1 authentication context names or values")
    for name in ("HOME", "CLAUDE_CONFIG_DIR"):
        if name not in values:
            continue
        path = Path(values[name])
        if not path.is_absolute() or not path.is_dir():
            raise ValueError("D1 authentication directory must be absolute and existing")
        physical = path.resolve()
        if any(physical.is_relative_to(Path(root).resolve()) for root in forbidden_roots):
            raise ValueError("D1 authentication directory overlaps task custody or source")
    return dict(values)


def capture_context(environment, *, forbidden_roots=()):
    return validate_context({k: environment[k] for k in AUTH_NAMES if k in environment},
                            forbidden_roots=forbidden_roots)


def check_status(executable, environment):
    """Help-gated status only; never persist raw status output or account details."""
    def run(arguments):
        return subprocess.run([executable, *arguments], env=dict(environment),
                              cwd=environment["TMPDIR"], capture_output=True,
                              text=True, timeout=15, check=False)

    for args, required in ((["--help"], ("auth", *FIXED_OPTIONS)),
                           (["auth", "--help"], ("status",)),
                           (["auth", "status", "--help"], ("--json",))):
        result = run(args)
        if result.returncode or any(word not in result.stdout for word in required):
            raise ValueError("D1 auth status unsupported or required isolation options unavailable")
    result = run(["auth", "status", "--json"])
    try:
        status = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise ValueError("D1 auth status indeterminate") from None
    if not isinstance(status, dict):
        raise ValueError("D1 auth status indeterminate")
    if status.get("loggedIn") is False:
        raise ValueError("D1 auth status unauthenticated; attempt not consumed")
    if status.get("loggedIn") is not True or result.returncode:
        raise ValueError("D1 auth status indeterminate; attempt not consumed")
    # Do not retain arbitrary provider strings (email, org, endpoints, tokens).
    method = status.get("authMethod")
    if method not in {"oauth_token", "api_key", "claude.ai", "console", "none"}:
        method = "unreported"
    return {"surface": "auth status --json", "status": "authenticated", "auth_method": method}


def settings_snapshot(context):
    """Observe settings drift by digest only, including symlink targets."""
    import hashlib
    directory = Path(context.get("CLAUDE_CONFIG_DIR", str(Path(context["HOME"]) / ".claude")))
    path = directory / "settings.json"
    result = {"path": str(path), "status": "absent"}
    if path.is_symlink():
        result.update(status="symlink", target=str(path.resolve()))
    if path.is_file():
        data = path.read_bytes()
        result.update(status="symlink" if path.is_symlink() else "present",
                      sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    return result


def auto_memory_path(context, run_dir):
    import re
    directory = Path(context.get("CLAUDE_CONFIG_DIR", str(Path(context["HOME"]) / ".claude")))
    return directory / "projects" / re.sub(r"[^a-zA-Z0-9]", "-", str(run_dir)) / "memory"


def require_fresh_memory(context, run_dir):
    """Inspect only the prospective task's memory directory; never create it."""
    path = auto_memory_path(context, run_dir)
    if path.is_symlink() or (path.exists() and (not path.is_dir() or any(path.iterdir()))):
        raise ValueError("D1 auto-memory path is not fresh; attempt not consumed")


BUILTIN_AGENTS = frozenset({"claude", "Explore", "general-purpose", "Plan", "statusline-setup"})


def _builtin_plugins(plugins):
    """Validate provider-advertised provenance, not provider-internal isolation."""
    if not isinstance(plugins, list):
        return False
    names = set()
    for plugin in plugins:
        if not isinstance(plugin, dict) or set(plugin) != {"name", "path", "source"}:
            return False
        name = plugin["name"]
        if (not isinstance(name, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None
                or name in names
                or plugin["path"] != "builtin" or plugin["source"] != name + "@builtin"):
            return False
        names.add(name)
    return True


def surface_failures(init, contract):
    """Builtin labels are diagnostic metadata, not proof of internal isolation."""
    failures = []
    if "skills" in init and init["skills"] != []:
        failures.append("SKILLS_NON_EMPTY")
    if "plugins" in init and not _builtin_plugins(init["plugins"]):
        failures.append("PLUGINS_NOT_BUILTIN")
    if "agents" in init and (not isinstance(init["agents"], list)
                             or any(not isinstance(agent, str) for agent in init["agents"])
                             or len(set(init["agents"])) != len(init["agents"])
                             or not set(init["agents"]) <= BUILTIN_AGENTS):
        failures.append("AGENTS_MISMATCH")
    if "memory_paths" in init:
        memory = init["memory_paths"]
        settings = (contract or {}).get("settings_sources", {}).get("home_settings", {})
        cwd = (contract or {}).get("roots", {}).get("run_dir")
        expected = None
        if settings.get("path") and cwd:
            expected = auto_memory_path({"HOME": "unused", "CLAUDE_CONFIG_DIR": str(Path(settings["path"]).parent)}, cwd)
        if (not isinstance(memory, dict) or set(memory) - {"auto"}
                or (memory and (not isinstance(memory.get("auto"), str)
                                or expected is None or Path(memory["auto"]) != expected))):
            failures.append("MEMORY_PATHS_MISMATCH")
    return failures
