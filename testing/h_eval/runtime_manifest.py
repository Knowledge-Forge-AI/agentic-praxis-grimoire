"""Private, bounded runtime inputs for the provider-free H transaction.

The v2 manifest is an inventory of physical inputs and version observations.
It never discovers an executable through ``PATH`` and it never records file
contents for operator-owned settings.  A captured manifest must be sealed
before a transaction can use it; revalidation is required at both transaction
boundaries.

The module intentionally keeps the v1 ``capture``/``verify`` API for the
historical preregistration owner.  H qualification uses ``capture_complete``
and the v2 lifecycle helpers below.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import subprocess
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from agent_phase.transmission import direct_bytes

SCHEMA = "apg.h-runtime-inputs/v1"
COMPLETE_SCHEMA = "apg.h-runtime-inputs/v2"

# These groups are deliberately source-oriented. Cache and environment input
# groups are required so a passing manifest cannot silently fall back to an
# ambient package cache or shell environment.
REQUIRED_GROUPS = frozenset({
    "route_sources",
    "operator_settings",
    "catalog_inputs",
    "projection_inputs",
    "apgr_generation",
    "toolchain_inputs",
    "cache_inputs",
    "environment_inputs",
})

PROVIDERS = frozenset({"claude", "codex", "antigravity"})
REQUIRED_COMMANDS = frozenset({
    "apgr",
    "bash",
    "cc",
    "git",
    "go",
    "make",
    "node",
    "npm",
    "pytest",
    "python",
    "sqlite3",
    "tsc",
})
# A machine may expose Python or TypeScript under the conventional alternate
# name. The stored command identity remains the caller's explicit name.
REQUIRED_COMMAND_ALTERNATIVES = (
    frozenset({"python", "python3"}),
    frozenset({"tsc", "typescript"}),
    frozenset({"cc", "clang", "gcc"}),
)

VERSION_ARGUMENTS = ("--version", "version", "-V")
MAX_INPUT_BYTES = 256 << 20
MAX_DIRECTORY_ENTRIES = 100_000
MAX_VERSION_BYTES = 4_096
# A discovery observation may bind a symlink whose target does not exist.
# Only these errors prove there is no hidden target content; permission and
# other errors still refuse because the target may hold unseen content.
_UNRESOLVED_LINK_ERRNOS = frozenset({errno.ENOENT, errno.ENOTDIR, errno.ELOOP})
_LIFECYCLE_FIELDS = {"state", "sealed_sha256"}
_LIFECYCLE_STATES = frozenset({"captured", "sealed", "expired"})
_ENVIRONMENT_BOUNDARY_KEYS = frozenset({"PATH", "HOME", "TMPDIR", "TMP", "TEMP"})
_FORBIDDEN_ENVIRONMENT_KEYS = frozenset({
    "LD_PRELOAD", "LD_LIBRARY_PATH", "LD_AUDIT", "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH", "NODE_OPTIONS", "PYTHONINSPECT", "PYTHONSTARTUP",
    "RUBYOPT", "PERL5OPT",
})
# These keys either select a network endpoint or let a package manager inject
# one.  An explicit offline policy is safer when these values are rejected
# than when a caller accidentally records an operator shell's setting.
_NETWORK_ENVIRONMENT_KEYS = frozenset({
    "ALL_PROXY", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "GOPROXY", "GOSUMDB", "GONOSUMDB",
    "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST", "PIP_FIND_LINKS",
    "npm_config_registry", "npm_config_proxy", "npm_config_http_proxy",
    "npm_config_https_proxy", "npm_config_noproxy", "npm_config_offline",
    "npm_config_prefer_offline", "npm_config_audit", "npm_config_fund",
    "PIP_NO_INDEX",
})
_SAFE_NETWORK_VALUES = {
    "ALL_PROXY": "",
    "HTTP_PROXY": "",
    "HTTPS_PROXY": "",
    "NO_PROXY": "*",
    "GOPROXY": "off",
    "GOSUMDB": "off",
    "GONOSUMDB": "*",
    "npm_config_offline": "true",
    "npm_config_prefer_offline": "true",
    "npm_config_audit": "false",
    "npm_config_fund": "false",
    "PIP_NO_INDEX": "1",
}


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def manifest_digest(value: Mapping[str, Any]) -> str:
    """Return the deterministic digest of a manifest without lifecycle state."""
    payload = deepcopy(dict(value))
    payload.pop("lifecycle", None)
    return hashlib.sha256(_canonical(payload)).hexdigest()


def file_identity(path: str | Path) -> dict[str, Any]:
    """Return the public v1 byte identity for one physical regular file."""
    raw = direct_bytes(Path(path), utf8=False, max_bytes=MAX_INPUT_BYTES)
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _physical(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError("absolute runtime input required")
    try:
        physical = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError("runtime input is unavailable") from error
    if not physical.is_absolute():
        raise ValueError("runtime input is not physical")
    return physical


def _regular_identity(path: Path) -> dict[str, Any]:
    """Read a regular file through the descriptor-relative transport owner."""
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("runtime input must be a regular file or directory")
    raw = direct_bytes(path, utf8=False, max_bytes=MAX_INPUT_BYTES)
    after = path.stat()
    key = (before.st_dev, before.st_ino, before.st_mode, before.st_size, before.st_mtime_ns)
    if key != (after.st_dev, after.st_ino, after.st_mode, after.st_size, after.st_mtime_ns):
        raise ValueError("runtime input changed during capture")
    return {
        "kind": "file",
        "physical_path": str(path),
        "device": int(after.st_dev),
        "inode": int(after.st_ino),
        "mode": stat.S_IMODE(after.st_mode),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _directory_stat_key(info: os.stat_result) -> tuple[int, int, int, int, int]:
    """Return the directory metadata used for race and drift detection."""
    return (
        int(info.st_dev),
        int(info.st_ino),
        int(info.st_mode),
        int(info.st_size),
        int(info.st_mtime_ns),
    )


def _consume_directory_budget(budget: dict[str, int], *, entries: int = 0, bytes_: int = 0) -> None:
    """Charge one shared budget for a complete directory identity walk."""
    budget["entries"] += entries
    budget["bytes"] += bytes_
    if budget["entries"] > MAX_DIRECTORY_ENTRIES or budget["bytes"] > MAX_INPUT_BYTES:
        raise ValueError("runtime input directory exceeds bound")


def _directory_identity(
    path: Path,
    *,
    _budget: dict[str, int] | None = None,
    _active: set[tuple[int, int]] | None = None,
    unresolved_links: bool = False,
) -> dict[str, Any]:
    """Capture a bounded tree, retaining directory symlink targets.

    Ordinary nested directories retain the historical v2 representation: only
    files and symlinks appear in ``entries``.  A symlink to a directory is an
    explicit entry with its link text and a complete nested ``target_identity``.
    The target walk shares the parent byte/entry budget and an active physical
    directory set, so a link cannot evade limits or recurse forever.

    ``unresolved_links`` is for observation owners only; manifest capture and
    verification keep the strict default, so sealed digests are unchanged.
    """
    budget = _budget if _budget is not None else {"entries": 0, "bytes": 0}
    active = _active if _active is not None else set()
    starting_bytes = budget["bytes"]
    before = path.stat()
    if not stat.S_ISDIR(before.st_mode):
        raise ValueError("runtime input must be a regular file or directory")
    key = (int(before.st_dev), int(before.st_ino))
    if key in active:
        raise ValueError("runtime input directory symlink cycle")
    active.add(key)
    try:
        entries = _directory_entries(path, prefix=Path("."), budget=budget, active=active,
                                     unresolved_links=unresolved_links)
        after = path.stat()
        if _directory_stat_key(before) != _directory_stat_key(after):
            raise ValueError("runtime input directory changed during capture")
        entry_bytes = _canonical(entries)
        return {
            "kind": "directory",
            "physical_path": str(path),
            "device": int(after.st_dev),
            "inode": int(after.st_ino),
            "mode": stat.S_IMODE(after.st_mode),
            "bytes": budget["bytes"] - starting_bytes,
            "sha256": hashlib.sha256(entry_bytes).hexdigest(),
            "entries": entries,
        }
    finally:
        active.remove(key)


def _directory_entries(
    path: Path,
    *,
    prefix: Path,
    budget: dict[str, int],
    active: set[tuple[int, int]],
    unresolved_links: bool = False,
) -> list[dict[str, Any]]:
    """Walk one physical directory while preserving relative entry paths."""
    before = path.stat()
    if not stat.S_ISDIR(before.st_mode):
        raise ValueError("runtime input directory is not a directory")
    entries: list[dict[str, Any]] = []
    for candidate in sorted(path.iterdir(), key=lambda value: value.name):
        relative = prefix / candidate.name
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode):
            if unresolved_links:
                unresolved = _unresolved_link(candidate, relative)
                if unresolved is not None:
                    _consume_directory_budget(budget, entries=1)
                    entries.append(unresolved)
                    continue
            target = _physical(candidate)
            target_info = target.stat()
            if stat.S_ISREG(target_info.st_mode):
                target_before = _directory_stat_key(target_info)
                raw = direct_bytes(target, utf8=False, max_bytes=MAX_INPUT_BYTES)
                target_after = target.stat()
                if target_before != _directory_stat_key(target_after):
                    raise ValueError("runtime input symlink target changed during capture")
                entry = {
                    "kind": "symlink",
                    "relative_path": str(relative),
                    "link_target": os.readlink(candidate),
                    "physical_path": str(target),
                    "device": int(target_after.st_dev),
                    "inode": int(target_after.st_ino),
                    "mode": stat.S_IMODE(target_after.st_mode),
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
                _consume_directory_budget(budget, entries=1, bytes_=int(entry["bytes"]))
                entries.append(entry)
                continue
            if stat.S_ISDIR(target_info.st_mode):
                target_identity = _directory_identity(target, _budget=budget, _active=active,
                                                      unresolved_links=unresolved_links)
                entry = {
                    "kind": "symlink",
                    "relative_path": str(relative),
                    "link_target": os.readlink(candidate),
                    "target_kind": "directory",
                    "physical_path": str(target),
                    "device": int(target_info.st_dev),
                    "inode": int(target_info.st_ino),
                    "mode": stat.S_IMODE(target_info.st_mode),
                    "bytes": int(target_identity["bytes"]),
                    "sha256": target_identity["sha256"],
                    "target_identity": target_identity,
                }
                # The target walk charged all target files. Charge the link
                # itself separately so every retained entry consumes one slot.
                _consume_directory_budget(budget, entries=1)
                entries.append(entry)
                continue
            raise ValueError("runtime input directory contains a nonregular symlink target")
        if stat.S_ISDIR(info.st_mode):
            child_key = (int(info.st_dev), int(info.st_ino))
            if child_key in active:
                raise ValueError("runtime input directory symlink cycle")
            # Preserve the pre-directory-link v2 entry shape for ordinary
            # nested directories.  The recursive walk below adds their
            # contents while charging the same shared entry budget.
            entries.append({
                "kind": "directory",
                "relative_path": str(relative),
                "physical_path": str(candidate),
                "device": int(info.st_dev),
                "inode": int(info.st_ino),
                "mode": stat.S_IMODE(info.st_mode),
                "bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
            })
            _consume_directory_budget(budget, entries=1)
            active.add(child_key)
            try:
                entries.extend(_directory_entries(candidate, prefix=relative, budget=budget, active=active,
                                                  unresolved_links=unresolved_links))
            finally:
                active.remove(child_key)
            continue
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("runtime input directory contains a nonregular entry")
        entry = _regular_identity(candidate)
        entry["relative_path"] = str(relative)
        _consume_directory_budget(budget, entries=1, bytes_=int(entry["bytes"]))
        entries.append(entry)
    after = path.stat()
    if _directory_stat_key(before) != _directory_stat_key(after):
        raise ValueError("runtime input directory changed during capture")
    return entries


def _unresolved_link(candidate: Path, relative: Path) -> dict[str, Any] | None:
    """Bind a symlink whose target cannot exist, or return ``None``.

    ``os.stat`` classifies the target before any ``resolve``: its errno is the
    same on every supported Python, whereas strict ``resolve`` reports a loop
    differently before 3.13.  The link text and errno are both bound, so a
    retargeted link, a target that appears, or a changed errno is drift.
    """
    try:
        os.stat(candidate)
    except OSError as error:
        if error.errno not in _UNRESOLVED_LINK_ERRNOS:
            raise ValueError("runtime input is unavailable") from error
        try:
            link_target = os.readlink(candidate)
        except OSError as read_error:
            raise ValueError("runtime input directory changed during capture") from read_error
        return {
            "kind": "symlink",
            "relative_path": str(relative),
            "link_target": link_target,
            "target_kind": "unresolved",
            "unresolved_errno": errno.errorcode[error.errno],
            "bytes": 0,
            "sha256": hashlib.sha256(b"").hexdigest(),
        }
    return None


def _input(path: str | Path, *, unresolved_links: bool = False) -> dict[str, Any]:
    candidate = Path(path)
    if candidate.is_symlink():
        physical = _physical(candidate)
        info = physical.stat()
        if stat.S_ISDIR(info.st_mode):
            identity = _directory_identity(physical, unresolved_links=unresolved_links)
            identity["link_target"] = os.readlink(candidate)
            identity["target_kind"] = "directory"
            return identity
    physical = _physical(path)
    info = physical.stat()
    if stat.S_ISREG(info.st_mode):
        return _regular_identity(physical)
    if stat.S_ISDIR(info.st_mode):
        return _directory_identity(physical, unresolved_links=unresolved_links)
    raise ValueError("runtime input must be a regular file or directory")


def _identity_matches(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    """Accept pre-directory-link v2 identities while binding new link text.

    A prior v2 capture of a top-level directory symlink resolved the path and
    therefore had no logical link fields.  Such a record remains readable for
    compatibility.  New captures include ``link_target`` and
    ``target_kind``; those fields are compared exactly and bind future drift.
    """
    actual_value = dict(actual)
    expected_value = dict(expected)
    if actual_value == expected_value:
        return True
    if (actual_value.get("kind") == "directory"
            and expected_value.get("kind") == "directory"
            and "link_target" not in expected_value
            and "target_kind" not in expected_value):
        actual_value.pop("link_target", None)
        actual_value.pop("target_kind", None)
        return actual_value == expected_value
    return False


def _version_arguments(value: Any, *, provider: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)) or len(value) != 1 or not isinstance(value[0], str):
        raise ValueError("bounded version arguments required")
    arguments = [value[0]]
    if arguments[0] not in VERSION_ARGUMENTS:
        raise ValueError("only bounded version probes are permitted")
    if provider and arguments != ["--version"]:
        raise ValueError("provider version probe must use --version")
    return arguments


def _declaration(value: Any, *, provider: bool = False) -> tuple[Path | None, list[str], bool]:
    if isinstance(value, Mapping):
        available = value.get("available", True)
        executable = value.get("executable")
        arguments = value.get("version_arguments", ["--version"])
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        available, executable, arguments = True, value[0], value[1]
    else:
        raise ValueError("runtime declaration must bind executable and version arguments")
    if type(available) is not bool:
        raise ValueError("runtime availability must be boolean")
    if not available:
        if not provider or executable is not None:
            raise ValueError("only an unavailable provider may omit its executable")
        return None, [], False
    if not isinstance(executable, (str, Path)):
        raise ValueError("runtime executable path required")  # noqa: TRY004
    return Path(executable), _version_arguments(arguments, provider=provider), True


def _version_observation(executable: str | Path, arguments: Sequence[str], *, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    arguments = _version_arguments(list(arguments))
    physical = _physical(executable)
    if not os.access(physical, os.X_OK):
        raise ValueError("runtime is not executable")
    version_env = dict(env or {})
    # A version probe receives a closed environment. In particular, it never
    # inherits a caller's proxy, package-manager, or model settings.
    version_env.setdefault("PATH", str(physical.parent))
    version_env.setdefault("LC_ALL", "C")
    version_env.setdefault("LANG", "C")
    try:
        # Version tools sometimes create state even for --version. Never give
        # them the installation directory or an operator HOME as writable state.
        with tempfile.TemporaryDirectory(prefix="apg-version-") as temporary:
            probe_root = Path(temporary).resolve()
            home, tmp = probe_root / "home", probe_root / "tmp"
            home.mkdir(mode=0o700)
            tmp.mkdir(mode=0o700)
            config = home / ".config"
            # Go's version command may start a telemetry child. Seed its
            # documented mode file inside this private HOME before launch so
            # that child cannot race cleanup of the version-only transaction.
            for directory in (config / "go/telemetry", home / "Library/Application Support/go/telemetry"):
                directory.mkdir(parents=True, mode=0o700)
                mode_file = directory / "mode"
                mode_file.write_text("off\n", encoding="utf-8")
                mode_file.chmod(0o600)
            version_env.update(HOME=str(home), TMPDIR=str(tmp), TMP=str(tmp), TEMP=str(tmp),
                               XDG_CONFIG_HOME=str(config), APPDATA=str(config))
            result = subprocess.run(
                [str(physical), *arguments],
                cwd=str(probe_root),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                env=version_env,
                timeout=15,
                check=True,
            )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("bounded runtime version probe failed") from error
    if len(result.stdout) > MAX_VERSION_BYTES or len(result.stderr) > MAX_VERSION_BYTES:
        raise ValueError("version output exceeds bound")
    try:
        stdout = result.stdout.decode("utf-8").strip()
        result.stderr.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("version output is not UTF-8") from error
    if not stdout:
        raise ValueError("bounded version response is empty")
    return {
        "version_stdout": stdout,
        "version_stdout_bytes": len(result.stdout),
        "version_stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "version_stderr_bytes": len(result.stderr),
        "version_stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
    }


def _unavailable_observation() -> dict[str, Any]:
    empty = hashlib.sha256(b"").hexdigest()
    return {
        "version_stdout": "unavailable",
        "version_stdout_bytes": 0,
        "version_stdout_sha256": empty,
        "version_stderr_bytes": 0,
        "version_stderr_sha256": empty,
    }


def _version(executable: str | Path, arguments: Sequence[str]) -> str:
    """Compatibility helper returning only the bounded version text."""
    return str(_version_observation(executable, arguments)["version_stdout"])


def _required_commands_present(commands: Iterable[str]) -> bool:
    names = set(commands)
    # Canonical names are required except for the three documented platform
    # aliases. This still forces the complete Scenario 04/06/15 tool closure.
    for name in REQUIRED_COMMANDS - {"python", "tsc", "cc"}:
        if name not in names:
            return False
    for alternatives in REQUIRED_COMMAND_ALTERNATIVES:
        if not names.intersection(alternatives):
            return False
    return True


def _default_environment(path_dirs: Iterable[str], *, supplied: Mapping[str, Any] | None = None) -> dict[str, Any]:
    supplied = dict(supplied or {})
    raw_values = supplied.get("values")
    if raw_values is None:
        raw_values = {key: value for key, value in supplied.items()
                      if isinstance(key, str) and key.isupper()}
    values = raw_values
    if not isinstance(values, Mapping) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in values.items()):
        raise ValueError("runtime environment values must be string keyed")
    forbidden = ("TOKEN", "SECRET", "PASSWORD", "COOKIE", "PRIVATE_KEY", "API_KEY")
    if any(any(part in key.upper() for part in forbidden) for key in values):
        raise ValueError("runtime environment must not carry credentials")
    for key, value in values.items():
        if key in _NETWORK_ENVIRONMENT_KEYS and value != _SAFE_NETWORK_VALUES.get(key, ""):
            raise ValueError("runtime environment must not carry network endpoint settings")
    if any(key == "PATH" for key in values):
        raise ValueError("runtime environment boundary values must use dedicated fields")
    if any(key in _FORBIDDEN_ENVIRONMENT_KEYS for key in values):
        raise ValueError("runtime environment loader/interpreter overrides are forbidden")
    base = {
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
        "GOPROXY": "off",
        "GOSUMDB": "off",
        "GONOSUMDB": "*",
        "GOTOOLCHAIN": "local",
        "npm_config_offline": "true",
        "npm_config_prefer_offline": "true",
        "npm_config_audit": "false",
        "npm_config_fund": "false",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_ADDOPTS": "-p no:cacheprovider",
        "NO_PROXY": "*",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "ALL_PROXY": "",
    }
    # HOME/TMPDIR are accepted as input shorthand but are represented in
    # dedicated manifest fields, never as mutable command overrides.
    values = {key: value for key, value in values.items() if key not in _ENVIRONMENT_BOUNDARY_KEYS}
    base.update({str(k): str(v) for k, v in values.items()})
    path_values = supplied.get("path_dirs", path_dirs)
    if not isinstance(path_values, (list, tuple)) or not path_values or any(not isinstance(p, str) for p in path_values):
        raise ValueError("manifest PATH directories required")
    normalized = sorted(dict.fromkeys(path_values))
    if any(not Path(path).is_absolute() or Path(path).is_symlink() for path in normalized):
        raise ValueError("runtime PATH directories must be absolute physical paths")
    home = supplied.get("home", raw_values.get("HOME") if isinstance(raw_values, Mapping) else None)
    temp_root = supplied.get("temp_root", raw_values.get("TMPDIR") if isinstance(raw_values, Mapping) else None)
    for name, value in (("home", home), ("temp_root", temp_root)):
        if value is not None:
            physical = _physical(value)
            if not physical.is_dir():
                raise ValueError(f"runtime {name} must be a directory")
            supplied[name] = str(physical)
    cache_paths = supplied.get("cache_paths", [])
    if not isinstance(cache_paths, list) or any(not isinstance(p, str) for p in cache_paths):
        raise ValueError("runtime cache paths must be a list")
    return {
        "schema": "apg.h-runtime-environment/v1",
        "network": "configured_offline_not_os_enforced",
        "network_disabled": False,
        "set": base,
        "path_dirs": normalized,
        "home": supplied.get("home"),
        "temp_root": supplied.get("temp_root"),
        "cache_paths": sorted(dict.fromkeys(cache_paths)),
    }


def capture(*, files, providers, routes):
    """Historical v1 capture: only a bounded provider version is executed."""
    if not files or not providers or not routes:
        raise ValueError("complete runtime inputs required")
    value = {
        "schema": SCHEMA,
        "files": {str(p): file_identity(p) for p in files},
        "providers": {},
        "routes": routes,
    }
    for provider, executable in providers.items():
        if provider not in PROVIDERS or str(executable) not in value["files"]:
            raise ValueError("provider executable must be bound")
        observation = _version_observation(executable, ["--version"])
        value["providers"][provider] = {
            "executable": str(executable),
            "version_stdout": observation["version_stdout"],
        }
    verify(value)
    return value


def verify(value, *, probe_versions=False):
    if isinstance(value, Mapping) and value.get("schema") == COMPLETE_SCHEMA:
        return verify_complete(value, probe_versions=probe_versions)
    if (not isinstance(value, Mapping) or set(value) != {"schema", "files", "providers", "routes"}
            or value["schema"] != SCHEMA or not value["files"] or not value["providers"] or not value["routes"]):
        raise ValueError("invalid runtime manifest")
    for path, expected in value["files"].items():
        if file_identity(path) != expected:
            raise ValueError("runtime input drift")
    for provider, record in value["providers"].items():
        if (provider not in PROVIDERS or set(record) != {"executable", "version_stdout"}
                or record["executable"] not in value["files"] or not record["version_stdout"]):
            raise ValueError("invalid runtime provider")
        if probe_versions and _version(record["executable"], ["--version"]) != record["version_stdout"]:
            raise ValueError("runtime version drift")
    return value


def _complete_fields() -> set[str]:
    return {
        "schema", "files", "providers", "commands", "runtimes", "routes", "groups",
        "absent_settings", "environment", "lifecycle",
    }


def capture_complete(
    *,
    providers: Mapping[str, Any],
    commands: Mapping[str, Any],
    groups: Mapping[str, Iterable[str | Path]],
    routes: Mapping[str, Any],
    absent_settings: Iterable[str | Path] = (),
    environment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Capture a complete v2 inventory and bounded version observations.

    ``providers`` and ``commands`` are explicit executable declarations. Each
    declaration is probed once with its bounded version argument; no task argv
    is accepted by this owner. Group paths may be regular files or physical
    directories, allowing local module/cache dependencies to be bound without
    copying their contents into public evidence.
    """
    if not isinstance(providers, Mapping) or set(providers) != set(PROVIDERS):
        raise ValueError("all three provider runtimes required")
    if not isinstance(commands, Mapping) or not commands or not _required_commands_present(commands):
        raise ValueError("complete runtime tool inventory required")
    if set(providers) & set(commands):
        raise ValueError("provider and command runtime names must be distinct")
    if not isinstance(groups, Mapping) or set(groups) != set(REQUIRED_GROUPS):
        raise ValueError("incomplete runtime source groups")
    if not isinstance(routes, Mapping) or not routes:
        raise ValueError("runtime routes required")

    files: dict[str, dict[str, Any]] = {}
    normalized_groups: dict[str, list[str]] = {}
    for group, paths in groups.items():
        if isinstance(paths, (str, Path)):
            paths = [paths]
        paths = list(paths)
        if not paths:
            raise ValueError("runtime source group must not be empty")
        normalized: list[str] = []
        for path in paths:
            if not isinstance(path, (str, Path)) or not Path(path).is_absolute():
                raise ValueError("absolute runtime input required")
            key = str(path)
            files[key] = _input(path)
            normalized.append(key)
        normalized_groups[group] = sorted(dict.fromkeys(normalized))

    declarations: dict[str, tuple[Path | None, list[str], bool, bool]] = {}
    for provider, declaration in providers.items():
        executable, arguments, available = _declaration(declaration, provider=True)
        declarations[provider] = (executable, arguments, True, available)
    for command, declaration in commands.items():
        executable, arguments, available = _declaration(declaration)
        declarations[command] = (executable, arguments, False, available)

    # Resolve every declared executable before probing any version.  A script
    # such as ``#!/usr/bin/env node`` may need a sibling runtime directory;
    # probing each executable with only its own parent would accidentally
    # reintroduce ambient PATH discovery.
    prepared: dict[str, tuple[Path | None, list[str], bool, str | None]] = {}
    path_dirs: list[str] = []
    for name, (executable, arguments, provider, available) in declarations.items():
        if not available:
            prepared[name] = (None, [], provider, None)
            continue
        assert executable is not None
        if not executable.is_absolute():
            raise ValueError("runtime executable path must be absolute")
        physical = _physical(executable)
        key = str(executable)
        files[key] = _input(physical)
        if files[key]["kind"] != "file" or not os.access(files[key]["physical_path"], os.X_OK):
            raise ValueError("runtime is not an executable regular file")
        prepared[name] = (physical, arguments, provider, key)
        path_dirs.append(str(physical.parent))

    absent: list[str] = []
    for path in absent_settings:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise ValueError("absolute absent setting required")
        if candidate.exists() or candidate.is_symlink():
            raise ValueError("absent runtime setting is present")
        absent.append(str(candidate))

    cache_paths = [
        entry["physical_path"] for key, entry in files.items()
        if key in normalized_groups.get("cache_inputs", []) and entry["kind"] == "directory"
    ]
    supplied_environment = dict(environment or {})
    supplied_environment.setdefault("cache_paths", cache_paths)
    environment_value = _default_environment(path_dirs, supplied=supplied_environment)
    runtimes: dict[str, dict[str, Any]] = {}
    version_environment = _version_environment(environment_value)
    for name, (physical, arguments, provider, key) in prepared.items():
        if physical is None:
            runtimes[name] = {
                "executable": None,
                "version_arguments": [],
                **_unavailable_observation(),
            }
            continue
        assert key is not None
        observation = _version_observation(physical, arguments, env=version_environment)
        runtimes[name] = {
            "executable": key,
            "version_arguments": arguments,
            **observation,
        }
    value: dict[str, Any] = {
        "schema": COMPLETE_SCHEMA,
        "files": files,
        "providers": sorted(providers),
        "commands": sorted(commands),
        "runtimes": runtimes,
        "routes": deepcopy(dict(routes)),
        "groups": normalized_groups,
        "absent_settings": sorted(dict.fromkeys(absent)),
        "environment": environment_value,
        "lifecycle": {"state": "captured", "sealed_sha256": None},
    }
    return verify_complete(value)


def _verify_lifecycle(value: Mapping[str, Any]) -> None:
    lifecycle = value.get("lifecycle")
    if not isinstance(lifecycle, Mapping) or set(lifecycle) != _LIFECYCLE_FIELDS:
        raise ValueError("runtime lifecycle is incomplete")
    state = lifecycle.get("state")
    if state not in _LIFECYCLE_STATES:
        raise ValueError("invalid runtime lifecycle state")
    digest = lifecycle.get("sealed_sha256")
    if state == "captured" and digest is not None:
        raise ValueError("captured runtime must not carry a seal")
    if state in {"sealed", "expired"} and (not isinstance(digest, str) or len(digest) != 64):
        raise ValueError("sealed runtime digest is invalid")
    if state == "sealed" and digest != manifest_digest(value):
        raise ValueError("sealed runtime manifest changed")


def verify_complete(value: Mapping[str, Any], *, probe_versions: bool = False) -> dict[str, Any]:
    """Validate v2 source, executable, environment, and lifecycle identity."""
    if not isinstance(value, Mapping) or set(value) != _complete_fields() or value.get("schema") != COMPLETE_SCHEMA:
        raise ValueError("incomplete runtime manifest")
    if set(value.get("providers", ())) != set(PROVIDERS) or len(value["providers"]) != 3:
        raise ValueError("all three provider runtimes required")
    commands = value.get("commands")
    if not isinstance(commands, list) or not commands or not _required_commands_present(commands):
        raise ValueError("complete runtime tool inventory required")
    if len(set(commands)) != len(commands) or set(commands) & set(PROVIDERS):
        raise ValueError("runtime command inventory is invalid")
    if not isinstance(value.get("routes"), Mapping) or not value["routes"]:
        raise ValueError("runtime routes required")
    files = value.get("files")
    if not isinstance(files, Mapping) or not files:
        raise ValueError("runtime input inventory is empty")
    groups = value.get("groups")
    if not isinstance(groups, Mapping) or set(groups) != set(REQUIRED_GROUPS):
        raise ValueError("incomplete runtime source groups")
    for paths in groups.values():
        if not isinstance(paths, list) or not paths or any(p not in files for p in paths):
            raise ValueError("runtime group lacks bound input")
    absent = value.get("absent_settings")
    if not isinstance(absent, list) or len(set(absent)) != len(absent):
        raise ValueError("runtime absence assertions are invalid")
    for path in absent:
        candidate = Path(path)
        if not candidate.is_absolute() or candidate.exists() or candidate.is_symlink():
            raise ValueError("previously absent runtime setting appeared")

    for path, expected in files.items():
        if not isinstance(path, str) or not Path(path).is_absolute() or not isinstance(expected, Mapping):
            raise ValueError("runtime file inventory is invalid")
        if not _identity_matches(_input(path), expected):
            raise ValueError("runtime file or executable target drift")

    runtimes = value.get("runtimes")
    if not isinstance(runtimes, Mapping) or set(runtimes) != set(value["providers"]) | set(commands):
        raise ValueError("runtime owner mismatch")
    for name, record in runtimes.items():
        fields = {
            "executable", "version_arguments", "version_stdout", "version_stdout_bytes",
            "version_stdout_sha256", "version_stderr_bytes", "version_stderr_sha256",
        }
        if not isinstance(record, Mapping) or set(record) != fields:
            raise ValueError("runtime identity not bound")
        executable = record.get("executable")
        if executable is None:
            if name != "antigravity" or record["version_arguments"] != [] or record["version_stdout"] != "unavailable":
                raise ValueError("runtime executable is not bound")
            if any(record[key] != value for key, value in {
                "version_stdout_bytes": 0,
                "version_stderr_bytes": 0,
                "version_stdout_sha256": hashlib.sha256(b"").hexdigest(),
                "version_stderr_sha256": hashlib.sha256(b"").hexdigest(),
            }.items()):
                raise ValueError("unavailable runtime observation is invalid")
            continue
        if executable not in files or files[executable].get("kind") != "file":
            raise ValueError("runtime executable is not a bound file")
        arguments = _version_arguments(record.get("version_arguments"), provider=name in PROVIDERS)
        if (not isinstance(record["version_stdout"], str) or not record["version_stdout"]
                or type(record["version_stdout_bytes"]) is not int
                or type(record["version_stderr_bytes"]) is not int
                or record["version_stdout_bytes"] > MAX_VERSION_BYTES
                or record["version_stderr_bytes"] > MAX_VERSION_BYTES
                or not _hex_digest(record["version_stdout_sha256"])
                or not _hex_digest(record["version_stderr_sha256"])):
            raise ValueError("runtime version observation is invalid")
        if probe_versions:
            observation = _version_observation(
                files[executable]["physical_path"],
                arguments,
                env=_version_environment(value["environment"]),
            )
            if any(record[key] != observation[key] for key in observation):
                raise ValueError("runtime version drift")

    _verify_environment(value["environment"], files, runtimes, groups)
    _verify_lifecycle(value)
    return dict(value)


def _hex_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _verify_environment(environment: Any, files: Mapping[str, Any], runtimes: Mapping[str, Any],
                        groups: Mapping[str, Any]) -> None:
    fields = {"schema", "network", "network_disabled", "set", "path_dirs", "home", "temp_root", "cache_paths"}
    if not isinstance(environment, Mapping) or set(environment) != fields:
        raise ValueError("runtime environment policy is incomplete")
    if (environment["schema"] != "apg.h-runtime-environment/v1"
            or environment["network"] != "configured_offline_not_os_enforced"
            or environment["network_disabled"] is not False):
        raise ValueError("configured offline policy required; OS network confinement is not provided")
    values = environment["set"]
    if not isinstance(values, Mapping) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in values.items()):
        raise ValueError("runtime environment values are invalid")
    if "PATH" in values or any(key in _ENVIRONMENT_BOUNDARY_KEYS for key in values):
        raise ValueError("runtime environment boundary values must use dedicated fields")
    if any(key in _FORBIDDEN_ENVIRONMENT_KEYS for key in values):
        raise ValueError("runtime environment loader/interpreter overrides are forbidden")
    for key, expected in (
        ("GOPROXY", "off"), ("GOSUMDB", "off"), ("GONOSUMDB", "*"),
        ("GOTOOLCHAIN", "local"), ("npm_config_offline", "true"),
        ("npm_config_prefer_offline", "true"), ("npm_config_audit", "false"),
        ("npm_config_fund", "false"), ("PIP_NO_INDEX", "1"),
        ("PYTHONNOUSERSITE", "1"), ("PYTHONDONTWRITEBYTECODE", "1"),
        ("PYTEST_ADDOPTS", "-p no:cacheprovider"), ("NO_PROXY", "*"),
        ("HTTP_PROXY", ""), ("HTTPS_PROXY", ""), ("ALL_PROXY", ""),
    ):
        if values.get(key) != expected:
            raise ValueError("runtime environment network/cache policy is incomplete")
    path_dirs = environment["path_dirs"]
    expected_dirs = {
        str(Path(files[record["executable"]]["physical_path"]).parent)
        for record in runtimes.values()
        if isinstance(record, Mapping) and record.get("executable") in files
    }
    if (not isinstance(path_dirs, list) or not path_dirs or set(path_dirs) != expected_dirs
            or any(not isinstance(path, str) or not Path(path).is_absolute()
                   or Path(path).resolve() != Path(path) or not Path(path).is_dir()
                   or Path(path).is_symlink() for path in path_dirs)):
        raise ValueError("runtime PATH is not manifest-derived")
    for name in ("home", "temp_root"):
        path = environment[name]
        if path is not None and (not isinstance(path, str) or not Path(path).is_dir() or Path(path).is_symlink()):
            raise ValueError(f"runtime {name} is not physical")
    caches = environment["cache_paths"]
    cache_files = {
        entry["physical_path"]
        for path in groups.get("cache_inputs", [])
        if path in files
        for entry in (files[path],)
        if isinstance(entry, Mapping) and entry.get("kind") == "directory"
    }
    def cache_is_bound(path: str) -> bool:
        candidate = Path(path)
        return path in cache_files or any(candidate == Path(root) or candidate.is_relative_to(root)
                                          for root in cache_files)

    if (not isinstance(caches, list)
            or any(not isinstance(path, str) or not Path(path).is_absolute()
                   or Path(path).resolve() != Path(path) or not Path(path).is_dir()
                   or Path(path).is_symlink() or not cache_is_bound(path) for path in caches)):
        raise ValueError("runtime cache inventory is invalid")


def _version_environment(environment: Mapping[str, Any]) -> dict[str, str]:
    values = {str(k): str(v) for k, v in environment["set"].items()}
    values["PATH"] = os.pathsep.join(environment["path_dirs"])
    values["HOME"] = environment.get("home") or environment["path_dirs"][0]
    temp_root = environment.get("temp_root") or values["HOME"]
    values["TMPDIR"] = str(temp_root)
    values["TMP"] = str(temp_root)
    values["TEMP"] = str(temp_root)
    return values


def seal(value: Mapping[str, Any]) -> dict[str, Any]:
    """Seal one captured manifest for a single bounded transaction."""
    current = verify_complete(value)
    lifecycle = current["lifecycle"]
    if lifecycle["state"] == "sealed":
        return deepcopy(current)
    if lifecycle["state"] != "captured":
        raise ValueError("only a captured runtime manifest can be sealed")
    result = deepcopy(current)
    result["lifecycle"] = {"state": "sealed", "sealed_sha256": manifest_digest(current)}
    return verify_complete(result)


def revalidate(value: Mapping[str, Any], *, probe_versions: bool = False) -> dict[str, Any]:
    """Revalidate a sealed manifest before or after its bounded transaction."""
    lifecycle = value.get("lifecycle") if isinstance(value, Mapping) else None
    if not isinstance(lifecycle, Mapping) or lifecycle.get("state") != "sealed":
        raise ValueError("sealed runtime manifest required for transaction")
    current = verify_complete(value, probe_versions=probe_versions)
    return current


DRIFT_SCHEMA = "apg.h-runtime-drift/v1"
_MAX_DRIFT_ROWS = 64
_SCALAR_FILE_FIELDS = ("kind", "physical_path", "device", "inode", "mode", "bytes", "sha256")


def drift_report(value: Mapping[str, Any]) -> dict[str, Any]:
    """Describe which retained file identities differ from the current host.

    This is a bounded diagnostic companion to ``verify_complete``; it never
    replaces or relaxes that guard.  Every bound file and absence assertion is
    compared, drift is reported instead of raised, and no version probe or
    other process runs.  Rows carry only paths, group names, changed field
    names and, for regular files, the scalar identity values of those fields.
    Directory entries and file contents are never exported.
    """
    files = value.get("files") if isinstance(value, Mapping) else None
    if not isinstance(files, Mapping) or not files:
        raise ValueError("runtime manifest file inventory is unavailable")
    groups = value.get("groups") if isinstance(value.get("groups"), Mapping) else {}
    membership: dict[str, list[str]] = {}
    for group, paths in groups.items():
        for path in paths if isinstance(paths, list) else []:
            membership.setdefault(str(path), []).append(str(group))
    rows: list[dict[str, Any]] = []
    counts = {"compared": 0, "different": 0, "unavailable": 0, "appeared": 0}
    for path in sorted(str(key) for key in files):
        expected = files[path]
        counts["compared"] += 1
        row: dict[str, Any] = {"path": path, "groups": sorted(membership.get(path, []))}
        try:
            actual = _input(path)
        except (OSError, ValueError) as error:
            counts["unavailable"] += 1
            rows.append({**row, "status": "unavailable", "type": type(error).__name__})
            continue
        if isinstance(expected, Mapping) and _identity_matches(actual, expected):
            continue
        expected = dict(expected) if isinstance(expected, Mapping) else {}
        changed = sorted(key for key in set(actual) | set(expected) if actual.get(key) != expected.get(key))
        counts["different"] += 1
        row.update(status="different", changed_fields=changed)
        if actual.get("kind") == "file" and expected.get("kind") == "file":
            scalar = [key for key in _SCALAR_FILE_FIELDS if key in changed]
            row["before"] = {key: expected.get(key) for key in scalar}
            row["after"] = {key: actual.get(key) for key in scalar}
        rows.append(row)
    absent = value.get("absent_settings") if isinstance(value, Mapping) else None
    for path in sorted(str(item) for item in absent) if isinstance(absent, list) else []:
        candidate = Path(path)
        if candidate.exists() or candidate.is_symlink():
            counts["appeared"] += 1
            rows.append({"path": path, "groups": ["absent_settings"], "status": "appeared"})
    return {
        "schema": DRIFT_SCHEMA,
        **counts,
        "rows": rows[:_MAX_DRIFT_ROWS],
        "rows_omitted": max(0, len(rows) - _MAX_DRIFT_ROWS),
        "versions": "not_probed",
    }


def expire(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return an explicitly expired copy; it cannot be used for a transaction."""
    if not isinstance(value, Mapping) or set(value) != _complete_fields() or value.get("schema") != COMPLETE_SCHEMA:
        raise ValueError("incomplete runtime manifest")
    _verify_lifecycle(value)
    if value["lifecycle"]["state"] == "expired":
        return deepcopy(dict(value))
    result = deepcopy(dict(value))
    result["lifecycle"] = {"state": "expired", "sealed_sha256": manifest_digest(value)}
    return result


def resolve_executable(value: Mapping[str, Any], name: str) -> str:
    """Resolve only a runtime name already bound by the complete manifest."""
    current = verify_complete(value)
    if current["lifecycle"]["state"] != "sealed":
        raise ValueError("sealed runtime manifest required for executable resolution")
    record = current["runtimes"].get(name)
    if not isinstance(record, Mapping):
        raise ValueError("runtime name is not bound")  # noqa: TRY004
    entry = current["files"].get(record.get("executable"))
    if not isinstance(entry, Mapping) or entry.get("kind") != "file":
        raise ValueError("runtime executable is not bound")
    return str(entry["physical_path"])


def capture_and_seal(**kwargs: Any) -> dict[str, Any]:
    """Capture and seal one v2 manifest as one explicit operator step."""
    return seal(capture_complete(**kwargs))
