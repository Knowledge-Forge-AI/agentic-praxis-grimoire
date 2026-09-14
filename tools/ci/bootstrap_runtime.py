#!/usr/bin/env python3
"""Materialize the exact disposable runtime required by ``bin/apg-test``.

The canonical APGR runner intentionally rejects ordinary setup-node or local
cache paths.  This adapter provisions each input into a task-owned directory,
checks the immutable identities declared in ``testing/public-ci-runtime.json``,
and writes only environment bindings for the following job.  It never writes
the checkout, Git metadata, or a user-wide tool cache.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CONFIG = ROOT / "testing/public-ci-runtime.json"
EXPECTED_PYTHON_PACKAGES = {
    "coverage": "7.15.2",
    "pytest": "9.1.1",
    "pytest-cov": "7.1.0",
    "pytest-xdist": "3.8.0",
}
EXPECTED_NPM_PACKAGES = {
    "typescript": "7.0.2",
    "npm": "12.0.2",
    "@playwright/test": "1.62.1",
    "vite": "8.2.2",
    "rolldown": "1.2.7",
}
EXPECTED_BROWSERS = ("chromium", "firefox", "webkit")
_ALLOWED_SYMLINK_ALIASES = {
    (Path("/tmp"), Path("/private/tmp")),
    (Path("/var"), Path("/private/var")),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError(f"duplicate public CI runtime manifest key: {key}")
        document[key] = value
    return document


def load_runtime(path: Path = RUNTIME_CONFIG) -> dict[str, Any]:
    document = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
    )
    if not isinstance(document, dict):
        raise ValueError("public CI runtime manifest must be an object")
    if document.get("schema_version") != "apg.public-ci-runtime/v1":
        raise ValueError("unsupported public CI runtime schema")
    if document.get("platform") != "darwin/arm64":
        raise ValueError("public CI runtime is only qualified for darwin/arm64")
    if document.get("runner") != "macos-15":
        raise ValueError("public CI runtime is only qualified for the macos-15 runner")
    required = {"primary_node", "secondary_node", "python_packages", "npm_packages", "browsers"}
    if not required.issubset(document):
        raise ValueError("public CI runtime is missing a required section")
    python_packages = document["python_packages"]
    npm_packages = document["npm_packages"]
    browsers = document["browsers"]
    if not isinstance(python_packages, dict) or python_packages != EXPECTED_PYTHON_PACKAGES:
        raise ValueError("public CI Python package pins are not the qualified set")
    if not isinstance(npm_packages, dict) or npm_packages != EXPECTED_NPM_PACKAGES:
        raise ValueError("public CI npm package pins are not the qualified set")
    if not isinstance(browsers, list) or tuple(browsers) != EXPECTED_BROWSERS:
        raise ValueError("public CI browser pins are not the qualified set")
    primary = document["primary_node"]
    secondary = document["secondary_node"]
    if not isinstance(primary, dict) or not isinstance(secondary, dict):
        raise ValueError("public CI Node sections must be objects")
    if (
        primary.get("version") != "22.22.2"
        or primary.get("root_owned") is not True
        or primary.get("required_root") != "/nix/store"
        or not isinstance(primary.get("source"), str)
        or not primary["source"].startswith("github:NixOS/nixpkgs/")
        or not isinstance(primary.get("attribute"), str)
        or not isinstance(primary.get("sha256"), str)
        or len(primary["sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in primary["sha256"].lower()
        )
        or not isinstance(secondary.get("url"), str)
        or not secondary["url"].startswith("https://")
        or secondary.get("binary_member") != "node-v24.19.0-darwin-arm64/bin/node"
        or not isinstance(secondary.get("archive_sha256"), str)
        or len(secondary["archive_sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in secondary["archive_sha256"].lower()
        )
        or not isinstance(secondary.get("sha256"), str)
        or len(secondary["sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in secondary["sha256"].lower()
        )
    ):
        raise ValueError("public CI Node identities are not the qualified set")
    return document


def _is_within(path: Path, ancestor: Path) -> bool:
    return path == ancestor or ancestor in path.parents


def _resolve_candidate(path: Path, label: str) -> Path:
    if not path.is_absolute():
        raise ValueError(f"{label} must be an absolute path")
    return Path(os.path.abspath(path))


def _allowed_alias(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    return (path, resolved) in _ALLOWED_SYMLINK_ALIASES


def _validate_external_path(
    path: Path,
    repository: Path,
    *,
    label: str,
    require_absent: bool,
) -> Path:
    candidate = _resolve_candidate(path, label)
    repository = repository.resolve(strict=True)
    parent = candidate.parent
    try:
        parent_metadata = parent.lstat()
    except OSError as error:
        raise ValueError(f"{label} parent is unavailable") from error
    if not stat.S_ISDIR(parent_metadata.st_mode) and not (
        stat.S_ISLNK(parent_metadata.st_mode) and _allowed_alias(parent)
    ):
        raise ValueError(f"{label} parent must be a direct directory")
    current = parent
    while True:
        try:
            metadata = current.lstat()
        except OSError as error:
            raise ValueError(f"{label} ancestry cannot be inspected") from error
        if stat.S_ISLNK(metadata.st_mode) and not _allowed_alias(current):
            raise ValueError(f"{label} has a symlinked ancestor")
        if not stat.S_ISLNK(metadata.st_mode) and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"{label} ancestry contains a non-directory")
        if (current / ".git").exists() or (current / ".git").is_symlink():
            raise ValueError(f"{label} is inside an active repository")
        if current == current.parent:
            break
        current = current.parent
    try:
        physical = candidate.resolve(strict=False)
    except OSError as error:
        raise ValueError(f"{label} cannot be resolved safely") from error
    if _is_within(physical, repository) or _is_within(repository, physical):
        raise ValueError(f"{label} overlaps the repository checkout")
    if os.path.lexists(candidate):
        if require_absent:
            raise ValueError(f"{label} must be a fresh path")
        raise ValueError(f"{label} already exists")
    # Keep the caller-visible path canonical when an approved system alias such
    # as /tmp -> /private/tmp was used.  Later direct-file checks must compare
    # the same identity rather than treating that alias as an unsafe link.
    return physical


def _ensure_task_root(root: Path, repository: Path) -> Path:
    candidate = _validate_external_path(
        root,
        repository,
        label="runtime root",
        require_absent=True,
    )
    try:
        candidate.mkdir(mode=0o700)
        metadata = candidate.lstat()
    except OSError as error:
        raise ValueError("runtime root could not be created safely") from error
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise ValueError("runtime root ownership or mode is unsafe")
    return candidate


def _validate_runtime_root(root: Path) -> Path:
    """Require the fresh caller-owned root used by all materialized inputs."""
    root = _resolve_candidate(root, "runtime root")
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("runtime root must be an existing direct directory")
    try:
        resolved = root.resolve(strict=True)
        metadata = root.lstat()
    except OSError as error:
        raise RuntimeError("runtime root identity could not be read") from error
    repository = ROOT.resolve(strict=True)
    if _is_within(resolved, repository) or _is_within(repository, resolved):
        raise RuntimeError("runtime root overlaps the repository checkout")
    current = root.parent
    while True:
        try:
            ancestor = current.lstat()
        except OSError as error:
            raise RuntimeError("runtime root ancestry cannot be inspected") from error
        if stat.S_ISLNK(ancestor.st_mode) and not _allowed_alias(current):
            raise RuntimeError("runtime root has a symlinked ancestor")
        if not stat.S_ISLNK(ancestor.st_mode) and not stat.S_ISDIR(ancestor.st_mode):
            raise RuntimeError("runtime root ancestry contains a non-directory")
        if (current / ".git").exists() or (current / ".git").is_symlink():
            raise RuntimeError("runtime root is inside an active repository")
        if current == current.parent:
            break
        current = current.parent
    if (root / ".git").exists() or (root / ".git").is_symlink():
        raise RuntimeError("runtime root is an active repository")
    root = resolved
    if (
        metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise RuntimeError("runtime root ownership or mode is unsafe")
    return root


def _validate_environment_output(path: Path, repository: Path, runtime_root: Path | None) -> Path:
    candidate = _validate_external_path(
        path,
        repository,
        label="environment output",
        require_absent=True,
    )
    if runtime_root is not None:
        root = runtime_root.resolve(strict=False)
        physical = candidate.resolve(strict=False)
        if _is_within(physical, root) or _is_within(root, physical):
            raise ValueError("environment output overlaps runtime root")
    return candidate


def _run(
    command: list[str],
    *,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    completed = runner(
        command,
        cwd=ROOT,
        env=dict(env) if env is not None else None,
        check=False,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"runtime bootstrap command failed: {Path(command[0]).name}")
    return completed


def _private_directory(root: Path, name: str) -> Path:
    path = root / name
    try:
        if not os.path.lexists(path):
            path.mkdir(mode=0o700)
        metadata = path.lstat()
    except OSError as error:
        raise RuntimeError(f"private runtime directory could not be created: {name}") from error
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise RuntimeError(f"private runtime directory is unsafe: {name}")
    return path


def _isolated_environment(root: Path) -> dict[str, str]:
    root = _validate_runtime_root(root)
    home = _private_directory(root, "home")
    cache = _private_directory(root, "npm-cache")
    pip_cache = _private_directory(root, "pip-cache")
    tmp = _private_directory(root, "tmp")
    xdg_cache = _private_directory(root, "xdg-cache")
    xdg_config = _private_directory(root, "xdg-config")
    environment = dict(os.environ)
    for name in (
        "HOME",
        "USERPROFILE",
        "TMPDIR",
        "TMP",
        "TEMP",
        "npm_config_cache",
        "npm_config_globalconfig",
        "npm_config_prefix",
        "npm_config_userconfig",
        "NPM_CONFIG_CACHE",
        "NPM_CONFIG_GLOBALCONFIG",
        "NPM_CONFIG_PREFIX",
        "NPM_CONFIG_USERCONFIG",
        "PIP_CONFIG_FILE",
        "PIP_CACHE_DIR",
        "PYTHONUSERBASE",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
    ):
        environment.pop(name, None)
    environment.update(
        {
            "HOME": os.fspath(home),
            "TMPDIR": os.fspath(tmp),
            "TMP": os.fspath(tmp),
            "TEMP": os.fspath(tmp),
            "XDG_CACHE_HOME": os.fspath(xdg_cache),
            "XDG_CONFIG_HOME": os.fspath(xdg_config),
            "NIX_USER_CONF_FILES": os.devnull,
            "npm_config_cache": os.fspath(cache),
            "npm_config_userconfig": os.fspath(root / "npmrc"),
            "npm_config_globalconfig": os.devnull,
            "npm_config_update_notifier": "false",
            "npm_config_fund": "false",
            "npm_config_audit": "false",
            "PIP_CACHE_DIR": os.fspath(pip_cache),
            "PIP_CONFIG_FILE": os.devnull,
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONUSERBASE": os.fspath(root / "python-user"),
        }
    )
    return environment


def _direct_file(path: Path, owner: Path, label: str, *, executable: bool) -> Path:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise RuntimeError(f"{label} must be an owned direct regular file")
    try:
        resolved = path.resolve(strict=True)
        metadata = path.lstat()
        owner = owner.resolve(strict=True)
    except OSError as error:
        raise RuntimeError(f"{label} identity could not be read") from error
    if (
        resolved != path
        or not _is_within(resolved, owner)
        or metadata.st_uid != os.getuid()
        or (executable and not os.access(path, os.X_OK))
    ):
        raise RuntimeError(f"{label} must remain inside its owned runtime root")
    return path


def _verify_node(
    path: Path,
    *,
    expected_sha256: str,
    required_root: Path | None = None,
    required_uid: int | None = None,
) -> Path:
    if (
        not path.is_absolute()
        or path.is_symlink()
        or not path.is_file()
        or not os.access(path, os.X_OK)
    ):
        raise ValueError("runtime Node binding must be a direct executable file")
    resolved = path.resolve(strict=True)
    if resolved != path:
        raise ValueError("runtime Node binding contains a symlinked path")
    if required_root is not None:
        required_root = required_root.resolve(strict=True)
        if not _is_within(resolved, required_root):
            raise ValueError("primary Node binding is outside the approved root")
    info = path.lstat()
    if required_uid is not None and info.st_uid != required_uid:
        raise ValueError("runtime Node binding ownership does not match the approved owner")
    actual = _sha256(path)
    if actual != expected_sha256:
        raise ValueError(f"runtime Node digest mismatch: expected {expected_sha256}")
    return path


def materialize_primary_node(
    config: Mapping[str, Any],
    *,
    environment: Mapping[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Path:
    node = config["primary_node"]
    source = str(node["source"])
    attribute = str(node["attribute"])
    nix = shutil.which("nix")
    if nix is None:
        raise RuntimeError("qualified Nix is unavailable; primary Node cannot be provisioned")
    output = _run(
        [
            nix,
            "--extra-experimental-features",
            "nix-command flakes",
            "build",
            "--no-link",
            "--print-out-paths",
            f"{source}#{attribute}",
        ],
        env=environment,
        runner=runner,
    )
    paths = [Path(line.strip()) for line in output.stdout.splitlines() if line.strip()]
    if len(paths) != 1:
        raise RuntimeError("Nix primary Node resolution did not return exactly one output")
    return _verify_node(
        paths[0] / "bin/node",
        expected_sha256=str(node["sha256"]),
        required_root=Path(str(node["required_root"])),
        required_uid=0 if node.get("root_owned") else None,
    )


def _download(opener: Callable[..., AbstractContextManager[Any]], url: str) -> bytes:
    with opener(url, timeout=120) as response:
        return response.read()


def materialize_secondary_node(
    config: Mapping[str, Any],
    root: Path,
    *,
    opener: Callable[..., AbstractContextManager[Any]] = urlopen,
) -> Path:
    node = config["secondary_node"]
    payload = _download(opener, str(node["url"]))
    actual_archive_sha = hashlib.sha256(payload).hexdigest()
    if actual_archive_sha != node["archive_sha256"]:
        raise ValueError("secondary Node archive digest mismatch")
    root = _validate_runtime_root(root)
    destination = root / "secondary-node" / "bin" / "node"
    try:
        secondary_root = root / "secondary-node"
        secondary_root.mkdir(mode=0o700)
        destination.parent.mkdir(mode=0o700)
    except OSError as error:
        raise RuntimeError("secondary Node destination could not be created safely") from error
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        member_name = str(node["binary_member"])
        try:
            member = archive.getmember(member_name)
        except KeyError as error:
            raise ValueError("secondary Node binary member is missing") from error
        if not member.isfile() or member.issym() or member.islnk():
            raise ValueError("secondary Node binary member is not a regular file")
        extracted = archive.extractfile(member)
        if extracted is None:
            raise ValueError("secondary Node binary member is unreadable")
        try:
            with destination.open("xb") as stream:
                stream.write(extracted.read())
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as error:
            raise ValueError("secondary Node destination already exists") from error
    destination.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return _verify_node(
        destination,
        expected_sha256=str(node["sha256"]),
        required_root=root,
        required_uid=os.getuid(),
    )


def install_python_requirements(root: Path, config: Mapping[str, Any]) -> Path:
    root = _validate_runtime_root(root)
    venv = root / "python"
    environment = _isolated_environment(root)
    _run([sys.executable, "-m", "venv", "--copies", str(venv)], env=environment)
    python = venv / "bin" / "python"
    if not python.is_file() or python.is_symlink():
        raise RuntimeError("Python virtual environment did not produce a direct interpreter")
    _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--requirement",
            str(ROOT / "requirements/test.txt"),
        ],
        env=environment,
    )
    for package, expected in config["python_packages"].items():
        actual = _package_version(python, package, environment)
        if actual != expected:
            raise RuntimeError(
                f"Python runtime package mismatch: {package}=={actual}; expected {expected}"
            )
    return python


def _package_version(python: Path, package: str, environment: Mapping[str, str]) -> str:
    result = _run(
        [
            str(python),
            "-c",
            "import importlib.metadata,sys; print(importlib.metadata.version(sys.argv[1]))",
            package,
        ],
        env=environment,
    )
    return result.stdout.strip()


def install_npm_runtime(
    root: Path,
    config: Mapping[str, Any],
    primary_node: Path,
) -> tuple[Path, Path]:
    root = _validate_runtime_root(root)
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm bootstrap command is unavailable")
    package_root = _private_directory(root, "npm")
    environment = _isolated_environment(root)
    packages = [f"{name}@{version}" for name, version in config["npm_packages"].items()]
    _run(
        [
            npm,
            "install",
            "--prefix",
            str(package_root),
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            *packages,
        ],
        env=environment,
    )
    npm_root = package_root / "node_modules" / "npm"
    npm_cli = npm_root / "bin" / "npm-cli.js"
    _direct_file(npm_cli, root, "npm CLI", executable=False)
    package_paths = {
        name: package_root / "node_modules" / name
        for name in config["npm_packages"]
    }
    for name, package_path in package_paths.items():
        _verify_package(package_path, name, config["npm_packages"][name], root)
    playwright_version = config["npm_packages"]["@playwright/test"]
    for name in ("playwright", "playwright-core"):
        _verify_package(
            package_root / "node_modules" / name,
            name,
            playwright_version,
            root,
        )
    _verify_package(
        package_root / "node_modules" / "@rolldown" / "binding-darwin-arm64",
        "@rolldown/binding-darwin-arm64",
        config["npm_packages"]["rolldown"],
        root,
    )
    typescript_root = package_paths["typescript"]
    tsc = typescript_root / "bin" / "tsc"
    _direct_file(tsc, root, "TypeScript compiler", executable=True)
    npm_version = _run(
        [str(primary_node), str(npm_cli), "--version"],
        env=environment,
    ).stdout.strip()
    if npm_version != config["npm_packages"]["npm"]:
        raise RuntimeError(f"npm runtime version mismatch: {npm_version}")
    typescript_version = _run(
        [str(primary_node), str(tsc), "--version"],
        env=environment,
    ).stdout.strip()
    if typescript_version != f"Version {config['npm_packages']['typescript']}":
        raise RuntimeError(f"TypeScript runtime version mismatch: {typescript_version}")
    browser_root = _private_directory(root, "browsers")
    browser_env = {**environment, "PLAYWRIGHT_BROWSERS_PATH": str(browser_root)}
    _run(
        [
            str(primary_node),
            str(npm_cli),
            "exec",
            "--prefix",
            str(package_root),
            "--",
            "playwright",
            "install",
            *config["browsers"],
        ],
        env=browser_env,
    )
    return package_root, tsc


def _verify_package(
    package_root: Path,
    expected_name: str,
    expected_version: str,
    owner: Path,
) -> None:
    if not package_root.is_absolute() or package_root.is_symlink() or not package_root.is_dir():
        raise RuntimeError(f"package root is not a direct directory: {expected_name}")
    resolved = package_root.resolve(strict=True)
    if resolved != package_root or not _is_within(resolved, owner.resolve(strict=True)):
        raise RuntimeError(f"package root is outside the owned runtime: {expected_name}")
    manifest = package_root / "package.json"
    _direct_file(manifest, owner, f"package manifest for {expected_name}", executable=False)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if document.get("name") != expected_name or document.get("version") != expected_version:
        raise RuntimeError(f"package identity mismatch for {expected_name}")


def _remove_created_file(path: Path, identity: tuple[int, int] | None) -> None:
    """Remove a file only while its destination identity is still ours."""
    if identity is None:
        return
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    except OSError:
        return
    if (
        stat.S_ISREG(metadata.st_mode)
        and (metadata.st_dev, metadata.st_ino) == identity
    ):
        try:
            path.unlink()
        except OSError:
            pass


def write_environment(
    path: Path,
    values: Mapping[str, Path | str],
    *,
    repository: Path = ROOT,
    runtime_root: Path | None = None,
) -> None:
    """Create one private, non-overwriting environment file outside the checkout."""
    destination = _validate_environment_output(path, repository, runtime_root)
    lines: list[str] = []
    for key, value in sorted(values.items()):
        if not isinstance(key, str) or not key or any(
            character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"
            for character in key
        ):
            raise ValueError(
                "environment variable names must contain only ASCII letters, digits, "
                "and underscores"
            )
        rendered = os.fspath(value)
        if "\n" in rendered or "\r" in rendered:
            raise ValueError("environment values must not contain line breaks")
        lines.append(f"{key}={rendered}")
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    identity: tuple[int, int] | None = None
    try:
        descriptor = os.open(os.fspath(destination), flags, 0o600)
        metadata = os.fstat(descriptor)
        identity = (metadata.st_dev, metadata.st_ino)
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
    except OSError:
        _remove_created_file(destination, identity)
        raise
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _remove_created_root(root: Path, identity: tuple[int, int] | None) -> None:
    """Clean up only the fresh runtime root whose identity was recorded."""
    if identity is None:
        return
    try:
        metadata = root.lstat()
    except FileNotFoundError:
        return
    except OSError:
        return
    if (
        stat.S_ISDIR(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and (metadata.st_dev, metadata.st_ino) == identity
    ):
        try:
            shutil.rmtree(root)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap APGR's exact disposable public CI runtime"
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--runtime-file", type=Path, default=RUNTIME_CONFIG)
    args = parser.parse_args(argv)
    root: Path | None = None
    root_identity: tuple[int, int] | None = None
    succeeded = False
    try:
        config = load_runtime(args.runtime_file)
        env_path = _validate_environment_output(args.env_file, ROOT, args.root)
        root = _ensure_task_root(args.root, ROOT)
        root_metadata = root.lstat()
        root_identity = (root_metadata.st_dev, root_metadata.st_ino)
        environment = _isolated_environment(root)
        primary = materialize_primary_node(config, environment=environment)
        secondary = materialize_secondary_node(config, root)
        python = install_python_requirements(root, config)
        package_root, tsc = install_npm_runtime(root, config, primary)
        browsers = root / "browsers"
        values: dict[str, Path | str] = {
            "APG_JAVASCRIPT_NODE": primary,
            "APG_NODEJS_PRIMARY_NODE": primary,
            "APG_NODEJS_SECONDARY_NODE": secondary,
            "APG_NODEJS_OWNED_SCRATCH_ROOT": root,
            "APG_TYPESCRIPT_TSC": tsc,
            "APG_NPM_OWNED_SCRATCH_ROOT": root,
            "APG_NPM_PACKAGE_ROOT": package_root / "node_modules" / "npm",
            "APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT": root,
            "APG_PLAYWRIGHT_PACKAGE_ROOT": package_root,
            "APG_VITE_OWNED_SCRATCH_ROOT": root,
            "APG_VITE_PACKAGE_ROOT": package_root,
            "PLAYWRIGHT_BROWSERS_PATH": browsers,
            "APGR_TEST_PYTHON": python,
        }
        write_environment(env_path, values, repository=ROOT, runtime_root=root)
        print(
            json.dumps(
                {
                    "schema": "apg-public-ci-runtime-result-v1",
                    "status": "passed",
                    "primary_sha256": _sha256(primary),
                    "secondary_sha256": _sha256(secondary),
                }
            )
        )
        succeeded = True
        return 0
    except (OSError, RuntimeError, TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {
                    "schema": "apg-public-ci-runtime-result-v1",
                    "status": "failed",
                    "error": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 1
    finally:
        if not succeeded and root is not None:
            _remove_created_root(root, root_identity)


if __name__ == "__main__":
    raise SystemExit(main())
