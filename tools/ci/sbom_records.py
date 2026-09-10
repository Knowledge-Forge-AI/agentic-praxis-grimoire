#!/usr/bin/env python3
"""Generate and validate public-source and distribution SBOM evidence.

The ``scan`` command is deliberately an adapter around the supplied Syft and
Grype binaries.  It consumes an already-built, checksum-bound distribution
bundle, extracts archives into one disposable output tree, scans the source,
three native binaries, three wheels, one sdist, and four npm archives, and
records the resulting catalog and vulnerability evidence.  It does not build,
install, publish, or upload anything.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import stat
import subprocess
import sys
import tarfile
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "release/ci/sbom_policy.json"
SCAN_SCHEMA = "apg-sbom-scan-v1"
RECORD_SCHEMA = "apg-sbom-record-v1"
GRYPE_SCHEMA = "apg-grype-result-v1"


class ScanError(ValueError):
    """A scan input, scanner result, or evidence contract is invalid."""


class ConditionalCoverageError(ScanError):
    """A declared conditional dependency is absent from exact scan evidence."""


class ConditionalToolError(ScanError):
    """A conditional dependency installer or scanner failed operationally."""


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_pairs)


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str, *, label: str) -> str:
    if not value or value.startswith("/") or "\\" in value:
        raise ScanError(f"{label} is not a safe relative path")
    parts = PurePosixPath(value).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ScanError(f"{label} is not a safe relative path")
    return value


def _direct_file(path: Path, label: str) -> Path:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ScanError(f"{label} is unavailable") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise ScanError(f"{label} must be a direct regular file")
    return path


def _direct_directory(path: Path, label: str) -> Path:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ScanError(f"{label} is unavailable") from error
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise ScanError(f"{label} must be a direct real directory")
    return path


def _tree_digest(path: Path, excludes: Sequence[str] = ()) -> str:
    digest = hashlib.sha256()
    excluded = tuple(
        pattern.removeprefix("**/").removesuffix("/**")
        for pattern in excludes
    )
    for child in sorted(path.rglob("*")):
        relative = child.relative_to(path).as_posix()
        if any(relative == item or relative.startswith(f"{item}/") for item in excluded):
            continue
        if relative == ".git" or relative.startswith(".git/"):
            continue
        if child.is_symlink():
            digest.update(f"L\0{relative}\0{child.readlink()}\n".encode())
        elif child.is_file():
            mode = stat.S_IMODE(child.lstat().st_mode)
            digest.update(f"F\0{relative}\0{mode:o}\0".encode())
            digest.update(child.read_bytes())
            digest.update(b"\n")
    return digest.hexdigest()


def _target_digest(path: Path, excludes: Sequence[str] = ()) -> str:
    if path.is_symlink() or not path.exists():
        raise ScanError(f"scan target is missing or symlinked: {path}")
    if path.is_dir():
        return _tree_digest(path, excludes)
    if path.is_file():
        return _file_digest(path)
    raise ScanError(f"scan target is not a regular file or directory: {path}")


def _parse_duration_hours(value: Any) -> float:
    text = str(value).strip().lower()
    if text.endswith("h0m0s"):
        text = text[:-5]
    elif text.endswith("h"):
        text = text[:-1]
    try:
        hours = float(text)
    except ValueError as error:
        raise ScanError(f"invalid duration: {value!r}") from error
    if hours < 0:
        raise ScanError("database age must be nonnegative")
    return hours


def _parse_timestamp(value: Any, label: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise ScanError(f"{label} timestamp is invalid") from error
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _redact_paths(value: str, paths: Sequence[tuple[Path, str]]) -> str:
    result = value
    for path, replacement in paths:
        result = result.replace(os.fspath(path), replacement)
    return result


def _run(
    argv: list[str],
    *,
    environment: dict[str, str],
    timeout: int = 300,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return runner(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ScanError(f"scanner invocation failed: {type(error).__name__}") from error


def _load_policy(path: Path = POLICY) -> dict[str, Any]:
    document = _read_json(path)
    if not isinstance(document, dict) or document.get("schema") != "apg-sbom-policy-v1":
        raise ScanError("unsupported SBOM policy schema")
    scan = document.get("scan")
    if not isinstance(scan, dict):
        raise ScanError("SBOM policy has no scan contract")
    return document


def _resolve_config(
    scanner_root: Path,
    configured_name: str,
    fallback: Path | None,
) -> Path | None:
    candidate = scanner_root / configured_name
    if candidate.exists():
        return _direct_file(candidate, f"scanner config {configured_name}")
    if fallback is not None and fallback.is_file() and not fallback.is_symlink():
        return fallback
    return None


def _parse_config_text(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text, object_pairs_hook=_strict_pairs)
    except json.JSONDecodeError:
        # The task scanner bootstrap emits a small YAML mapping.  Avoid adding
        # a YAML dependency: parse only scalar/list keys owned by this policy.
        value: dict[str, Any] = {}
        section: dict[str, Any] | None = None
        for raw in text.splitlines():
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            item = raw.strip()
            if item.endswith(":"):
                key = item[:-1].strip()
                if indent == 0:
                    section = {}
                    value[key] = section
                elif section is not None:
                    section[key] = {}
                continue
            if ":" not in item:
                continue
            key, raw_value = (part.strip() for part in item.split(":", 1))
            if raw_value == "[]":
                parsed: Any = []
            elif raw_value.lower() in {"true", "false"}:
                parsed = raw_value.lower() == "true"
            else:
                parsed = raw_value.strip("'\"")
            if indent == 0:
                value[key] = parsed
                section = None
            elif section is not None:
                section[key] = parsed
        if not value:
            raise ScanError(f"scanner config is not a supported JSON/YAML mapping: {path}")
    if not isinstance(value, dict):
        raise ScanError(f"scanner config root is not a mapping: {path}")
    return value


def _scanner_identity(
    binary: Path,
    *,
    expected_version: str,
    name: str,
    environment: dict[str, str],
    redact: Sequence[tuple[Path, str]],
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> dict[str, Any]:
    metadata = _direct_file(binary, name)
    if not (stat.S_IMODE(metadata.stat().st_mode) & 0o111):
        raise ScanError(f"{name} is not executable")
    completed = _run(
        [os.fspath(binary), "version"],
        environment=environment,
        runner=runner,
    )
    stdout = completed.stdout.decode("utf-8", "replace")
    stderr = completed.stderr.decode("utf-8", "replace")
    if completed.returncode != 0:
        raise ScanError(f"{name} version command failed")
    if expected_version not in stdout and expected_version not in stderr:
        raise ScanError(f"{name} version does not identify {expected_version}")
    return {
        "name": name,
        "version": expected_version,
        "binary_sha256": _file_digest(binary),
        "version_output": _redact_paths(stdout.strip(), redact),
        "stderr_present": bool(stderr.strip()),
    }


def _validate_grype_config(config: dict[str, Any], policy: dict[str, Any]) -> None:
    grype_policy = policy["scan"]["scanner"]["grype"]
    # The task-local bootstrap may leave the threshold to the explicit CLI
    # ``--fail-on`` flag.  A configured value, when present, must still agree
    # with the policy; omission does not weaken the command-level guard.
    if config.get("fail-on-severity", grype_policy["fail_on"]) != grype_policy["fail_on"]:
        raise ScanError("Grype policy must block High and Critical findings")
    if config.get("only-fixed") is not False:
        raise ScanError("Grype policy must retain unfixed findings")
    if config.get("ignore", []) != []:
        raise ScanError("Grype policy contains custom ignore rules")
    database = config.get("db")
    if not isinstance(database, dict):
        raise ScanError("Grype policy has no database validation configuration")
    for key in ("require-update-check", "validate-age", "validate-by-hash-on-start"):
        if database.get(key) is not True:
            raise ScanError(f"Grype policy must enable {key}")


def _prepare_grype_database_cache(
    scanner_root: Path,
    environment: dict[str, str],
) -> Path:
    """Create and bind the task-owned Grype database cache directory."""
    database_root = scanner_root / "db"
    if database_root.is_symlink() or (
        database_root.exists() and not database_root.is_dir()
    ):
        raise ScanError("Grype database cache must be a direct real directory")
    if not database_root.exists():
        try:
            database_root.mkdir(mode=0o700)
        except OSError as error:
            raise ScanError("Grype database cache could not be created") from error
    environment["GRYPE_DB_CACHE_DIR"] = os.fspath(database_root)
    return database_root


def _update_grype_database(
    grype: Path,
    config_path: Path | None,
    environment: dict[str, str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> dict[str, Any]:
    """Run the real database update and retain only sanitized outcome facts."""
    command = [os.fspath(grype), "db", "update"]
    if config_path is not None:
        command.extend(["--config", os.fspath(config_path)])
    completed = _run(command, environment=environment, runner=runner)
    outcome = {
        "command": ["db", "update"],
        "returncode": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "stdout_present": bool(completed.stdout.strip()),
        "stderr_present": bool(completed.stderr.strip()),
    }
    if completed.returncode != 0:
        raise ScanError("Grype database update command failed")
    return outcome


def _database_identity(
    scanner_root: Path,
    grype: Path,
    config_path: Path | None,
    config: dict[str, Any],
    policy: dict[str, Any],
    environment: dict[str, str],
    *,
    now: datetime | None,
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> dict[str, Any]:
    scan = policy["scan"]
    database_policy = scan["scanner"]["database"]
    database_root = _prepare_grype_database_cache(scanner_root, environment)
    update = _update_grype_database(
        grype,
        config_path,
        environment,
        runner=runner,
    )
    relative = _safe_relative(database_policy["relative_path"], label="database path")
    database_path = _direct_file(scanner_root / relative, "Grype database")
    expected_digest = _file_digest(database_path)
    identity_path = scanner_root / database_policy["identity_file"]

    status_command = [os.fspath(grype), "db", "status"]
    if config_path is not None:
        status_command.extend(["--config", os.fspath(config_path)])
    status_command.extend(["-o", "json"])
    status = _run(status_command, environment=environment, runner=runner)
    if status.returncode != 0:
        raise ScanError("Grype database status command failed")
    try:
        status_document = json.loads(status.stdout.decode("utf-8"), object_pairs_hook=_strict_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ScanError("Grype database status is malformed") from error
    if not isinstance(status_document, dict) or status_document.get("valid") is not True:
        raise ScanError("Grype vulnerability database is not valid")
    built = status_document.get("built") or status_document.get("builtAt")
    if built is None:
        raise ScanError("Grype database status has no build timestamp")
    built_at = _parse_timestamp(built, "Grype database build")
    observed_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_hours = (observed_now - built_at).total_seconds() / 3600
    maximum_age = _parse_duration_hours(database_policy["max_age_hours"])
    if age_hours < 0 or age_hours > maximum_age:
        raise ScanError("Grype vulnerability database is stale")
    reported_path = status_document.get("path")
    if reported_path:
        try:
            reported = Path(str(reported_path)).resolve(strict=True)
        except OSError as error:
            raise ScanError("Grype database status path is unavailable") from error
        if reported != database_path.resolve(strict=True):
            raise ScanError("Grype database status names a different database")
    return {
        "schema_version": status_document.get("schemaVersion"),
        "built": str(built),
        "age_hours": round(age_hours, 3),
        "max_age_hours": maximum_age,
        "valid": True,
        "database_sha256": expected_digest,
        "database_path": relative,
        "update_check": "command-observed",
        "update": update,
        "database_cache": database_root.relative_to(scanner_root).as_posix(),
        "identity_file": (
            identity_path.relative_to(scanner_root).as_posix()
            if identity_path.is_file() and not identity_path.is_symlink()
            else None
        ),
        "identity_validated": False,
    }


def _installed_sdist_digests(install_root: Path) -> dict[str, Any]:
    """Bind the installed sdist tree, metadata, and native binary contents."""
    install_root = _direct_directory(install_root, "derived install root")
    metadata_paths = sorted(
        [
            *install_root.glob("*.dist-info/METADATA"),
            *install_root.glob("*.egg-info/PKG-INFO"),
        ]
    )
    if len(metadata_paths) != 1:
        raise ScanError("derived sdist install must contain exactly one package metadata file")
    metadata = _direct_file(metadata_paths[0], "derived package metadata")
    binary = _direct_file(
        install_root / "agentic_praxis_grimoire/bin/apgr",
        "derived package native binary",
    )
    if not (stat.S_IMODE(binary.stat().st_mode) & 0o111):
        raise ScanError("derived package native binary is not executable")
    return {
        "installed_tree_sha256": _tree_digest(install_root),
        "metadata": {
            "path": metadata.relative_to(install_root).as_posix(),
            "sha256": _file_digest(metadata),
        },
        "binary": {
            "path": binary.relative_to(install_root).as_posix(),
            "sha256": _file_digest(binary),
        },
    }


def _install_sdist(
    record: dict[str, Any],
    output: Path,
    installer_python: Path | None,
    environment: dict[str, str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> tuple[Path, dict[str, Any]]:
    """Install one exact sdist into task-owned output using offline pip flags."""
    archive = _direct_file(record["path"], "Python sdist")
    expected_digest = record.get("sha256")
    if not isinstance(expected_digest, str) or _file_digest(archive) != expected_digest:
        raise ScanError("Python sdist checksum differs from its manifest")
    install_parent = output / "installed"
    cache_root = output / "pip-cache"
    temporary_root = output / "pip-tmp"
    for directory, label in (
        (install_parent, "derived install directory"),
        (cache_root, "pip cache directory"),
        (temporary_root, "pip temporary directory"),
    ):
        if directory.is_symlink() or (
            directory.exists() and not directory.is_dir()
        ):
            raise ScanError(f"{label} must be a direct real directory")
        if not directory.exists():
            directory.mkdir(mode=0o700, parents=True)
    install_root = install_parent / record["id"]
    if install_root.exists() or install_root.is_symlink():
        raise ScanError("derived install target must be new and empty")
    install_root.mkdir(mode=0o700)
    installer = Path(installer_python or sys.executable).resolve(strict=True)
    installer = _direct_file(installer, "installer Python")
    if not (stat.S_IMODE(installer.stat().st_mode) & 0o111):
        raise ScanError("installer Python is not executable")
    install_environment = environment.copy()
    install_environment["PIP_CACHE_DIR"] = os.fspath(cache_root)
    install_environment["TMPDIR"] = os.fspath(temporary_root)
    install_environment["PIP_NO_INPUT"] = "1"
    install_environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    command = [
        os.fspath(installer),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--no-deps",
        "--no-build-isolation",
        "--target",
        os.fspath(install_root),
        os.fspath(archive),
    ]
    completed = _run(command, environment=install_environment, runner=runner)
    outcome = {
        "command": ["python", "-m", "pip", "install"],
        "returncode": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "stdout_present": bool(completed.stdout.strip()),
        "stderr_present": bool(completed.stderr.strip()),
    }
    if completed.returncode != 0:
        raise ScanError("offline sdist installation failed")
    if _file_digest(archive) != expected_digest:
        raise ScanError("Python sdist changed during derived installation")
    digests = _installed_sdist_digests(install_root)
    digests.update(
        {
            "target": install_root.relative_to(output).as_posix(),
            "archive_sha256": expected_digest,
            "installer": outcome,
        }
    )
    return install_root, digests


def _verify_installed_sdist_digests(
    install_root: Path,
    expected: dict[str, Any],
) -> None:
    """Refuse evidence if the derived install changed during scanner execution."""
    observed = _installed_sdist_digests(install_root)
    if observed != {
        key: expected[key]
        for key in ("installed_tree_sha256", "metadata", "binary")
    }:
        raise ScanError("derived sdist install changed during scanning")


def _member_target(name: str, destination: Path) -> Path:
    if not name or name.startswith("/") or "\\" in name:
        raise ScanError(f"unsafe archive member path: {name!r}")
    parts = PurePosixPath(name).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ScanError(f"unsafe archive member path: {name!r}")
    target = destination.joinpath(*parts)
    try:
        target.relative_to(destination)
    except ValueError as error:
        raise ScanError(f"archive member escapes extraction root: {name!r}") from error
    return target


def _ensure_parent(path: Path, destination: Path) -> None:
    current = destination
    for part in path.parent.relative_to(destination).parts:
        current /= part
        if current.exists() or current.is_symlink():
            if current.is_symlink() or not current.is_dir():
                raise ScanError("archive parent is not a direct real directory")
        else:
            current.mkdir(mode=0o700)


def _write_member(path: Path, payload: bytes, mode: int, destination: Path) -> None:
    _ensure_parent(path, destination)
    if path.exists() or path.is_symlink():
        raise ScanError(f"duplicate archive member: {path.relative_to(destination)}")
    with path.open("xb") as stream:
        stream.write(payload)
    path.chmod(mode & 0o777)


def _extract_archive(path: Path, destination: Path) -> dict[str, Any]:
    destination.mkdir(mode=0o700)
    members = 0
    regular_files = 0
    directories = 0
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            seen: set[str] = set()
            for member in archive.infolist():
                target = _member_target(member.filename, destination)
                if member.filename in seen:
                    raise ScanError(f"duplicate archive member: {member.filename}")
                seen.add(member.filename)
                members += 1
                mode = (member.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK or mode not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ScanError(f"archive contains a link or special file: {member.filename}")
                if member.is_dir() or mode == stat.S_IFDIR:
                    _ensure_parent(target, destination)
                    if target.exists() and not target.is_dir():
                        raise ScanError(f"archive directory collides with a file: {member.filename}")
                    target.mkdir(mode=0o700, exist_ok=True)
                    directories += 1
                else:
                    _write_member(
                        target,
                        archive.read(member),
                        (member.external_attr >> 16) & 0o777,
                        destination,
                    )
                    regular_files += 1
        return {
            "format": "zip",
            "members": members,
            "regular_files": regular_files,
            "directories": directories,
            "links": 0,
        }
    if path.name.endswith(".tar.gz") or path.name.endswith(".tgz"):
        with tarfile.open(path, "r:gz") as archive:
            seen = set()
            for member in archive.getmembers():
                target = _member_target(member.name, destination)
                if member.name in seen:
                    raise ScanError(f"duplicate archive member: {member.name}")
                seen.add(member.name)
                members += 1
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise ScanError(f"archive contains a link or special file: {member.name}")
                if member.isdir():
                    _ensure_parent(target, destination)
                    if target.exists() and not target.is_dir():
                        raise ScanError(f"archive directory collides with a file: {member.name}")
                    target.mkdir(mode=0o700, exist_ok=True)
                    directories += 1
                else:
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise ScanError(f"archive member cannot be read: {member.name}")
                    _write_member(target, stream.read(), member.mode, destination)
                    regular_files += 1
        return {
            "format": "tar.gz",
            "members": members,
            "regular_files": regular_files,
            "directories": directories,
            "links": 0,
        }
    raise ScanError(f"unsupported archive format: {path.name}")


def _parse_checksums(bundle: Path, checksum_name: str) -> dict[str, str]:
    path = _direct_file(bundle / checksum_name, checksum_name)
    records: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        if not raw.strip():
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})  (.+)", raw)
        if match is None:
            raise ScanError(f"malformed checksum line {line_number}")
        digest, relative = match.groups()
        relative = _safe_relative(relative, label=f"checksum path {line_number}")
        if relative in records:
            raise ScanError(f"duplicate checksum path: {relative}")
        records[relative] = digest.lower()
    if not records:
        raise ScanError("checksum manifest is empty")
    for relative, expected in records.items():
        actual = _file_digest(_direct_file(bundle / relative, f"checksum target {relative}"))
        if actual != expected:
            raise ScanError(f"checksum mismatch: {relative}")
    return records


def _manifest_file_records(
    bundle: Path,
    policy: dict[str, Any],
    checksums: dict[str, str],
) -> list[dict[str, Any]]:
    scan = policy["scan"]
    bundle_policy = scan["bundle"]
    go_by_target = {
        entry["target"]: (slug, entry)
        for slug, entry in bundle_policy["go"].items()
    }
    manifest_name = bundle_policy["manifest_file"]
    manifest_path = _direct_file(bundle / manifest_name, manifest_name)
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "apg.distribution-manifest/v1":
        raise ScanError("distribution manifest schema is invalid")
    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise ScanError("distribution manifest has no version")
    records: list[dict[str, Any]] = []
    expected_paths = {manifest_name, bundle_policy["checksum_file"]}

    binaries = manifest.get("binaries")
    if not isinstance(binaries, dict):
        raise ScanError("distribution manifest has no binary records")
    for slug, entry in bundle_policy["go"].items():
        target = entry["target"]
        binary_relative = entry["binary"]
        manifest_relative = entry["manifest"]
        expected_paths.update((binary_relative, manifest_relative))
        binary = _direct_file(bundle / binary_relative, binary_relative)
        binary_manifest_path = _direct_file(bundle / manifest_relative, manifest_relative)
        binary_manifest = _read_json(binary_manifest_path)
        if not isinstance(binary_manifest, dict):
            raise ScanError(f"binary manifest is not an object: {manifest_relative}")
        identity = binary_manifest.get("build_identity")
        if (
            binary_manifest.get("schema_version") != "apg.binary-manifest/v1"
            or binary_manifest.get("binary_name") != "apgr"
            or binary_manifest.get("target", {}).get("go_target") != target
            or not isinstance(identity, dict)
            or identity.get("target") != target
            or identity.get("version") != version
        ):
            raise ScanError(f"binary manifest identity is invalid: {manifest_relative}")
        binary_digest = _file_digest(binary)
        manifest_digest = _file_digest(binary_manifest_path)
        entry_record = binaries.get(target)
        if not isinstance(entry_record, dict):
            raise ScanError(f"distribution manifest lacks binary target: {target}")
        nested_manifest = entry_record.get("manifest", {})
        if (
            binary_manifest.get("sha256") != binary_digest
            or binary_manifest.get("size_bytes") != binary.stat().st_size
            or entry_record.get("size_bytes") != binary.stat().st_size
            or nested_manifest.get("size_bytes") != binary_manifest_path.stat().st_size
        ):
            raise ScanError(f"binary manifest digest disagrees: {manifest_relative}")
        if (
            entry_record.get("sha256") != binary_digest
            or nested_manifest.get("sha256") != manifest_digest
            or entry_record.get("version") != version
        ):
            raise ScanError(f"distribution manifest binary record disagrees: {target}")
        records.append(
            {
                "id": f"go-{slug}",
                "kind": "go-binary",
                "relative": binary_relative,
                "path": binary,
                "sha256": binary_digest,
                "target": target,
                "manifest_relative": manifest_relative,
                "manifest_sha256": manifest_digest,
                "version": version,
                "required_types": scan["artifact_requirements"]["go-binary"]["required_types"],
            }
        )

    python_policy = bundle_policy["python"]
    python_dir = bundle / python_policy["directory"]
    _direct_directory(python_dir, "Python artifact directory")
    wheels = sorted(python_dir.glob(python_policy["wheel_glob"]))
    sdist = sorted(python_dir.glob(python_policy["sdist_glob"]))
    if len(wheels) != python_policy["wheel_count"] or len(sdist) != python_policy["sdist_count"]:
        raise ScanError("Python artifact set is incomplete")
    python_manifest = manifest.get("python", {})
    wheel_records = python_manifest.get("wheels", [])
    if not isinstance(wheel_records, list) or {item.get("name") for item in wheel_records} != {
        path.name for path in wheels
    }:
        raise ScanError("distribution manifest Python wheels do not match bundle")
    for path in wheels:
        digest = _file_digest(_direct_file(path, path.name))
        record = next(item for item in wheel_records if item.get("name") == path.name)
        if (
            record.get("sha256") != digest
            or record.get("size_bytes") != path.stat().st_size
            or record.get("version") != version
        ):
            raise ScanError(f"Python wheel record disagrees: {path.name}")
        target = record.get("target")
        if target not in go_by_target:
            raise ScanError(f"Python wheel target is unsupported: {path.name}")
        relative = path.relative_to(bundle).as_posix()
        expected_paths.add(relative)
        records.append(
            {
                "id": f"python-wheel-{target.replace('/', '-')}",
                "kind": "python-wheel",
                "relative": relative,
                "path": path,
                "sha256": digest,
                "target": target,
                "version": version,
                "required_types": scan["artifact_requirements"]["python-wheel"]["required_types"],
                "embedded_relative": scan["artifact_requirements"]["python-wheel"]["embedded_binary"],
                "embedded_sha256": next(
                    item["sha256"]
                    for item in records
                    if item["kind"] == "go-binary" and item["target"] == target
                ),
                "embedded_manifest_relative": "agentic_praxis_grimoire/bin/apgr.binary-manifest.json",
                "embedded_manifest_sha256": next(
                    item["manifest_sha256"]
                    for item in records
                    if item["kind"] == "go-binary" and item["target"] == target
                ),
            }
        )
    sdist_path = _direct_file(sdist[0], sdist[0].name)
    sdist_record = python_manifest.get("sdist", {})
    if (
        sdist_record.get("name") != sdist_path.name
        or sdist_record.get("sha256") != _file_digest(sdist_path)
        or sdist_record.get("size_bytes") != sdist_path.stat().st_size
        or sdist_record.get("version") != version
    ):
        raise ScanError("Python sdist record disagrees with bundle")
    relative = sdist_path.relative_to(bundle).as_posix()
    expected_paths.add(relative)
    records.append(
        {
            "id": "python-sdist",
            "kind": "python-sdist",
            "relative": relative,
            "path": sdist_path,
            "sha256": _file_digest(sdist_path),
            "version": version,
            "required_types": scan["artifact_requirements"]["python-sdist"]["required_types"],
        }
    )

    npm_policy = bundle_policy["npm"]
    npm_dir = bundle / npm_policy["directory"]
    _direct_directory(npm_dir, "npm artifact directory")
    npm_paths = sorted(npm_dir.glob(npm_policy["glob"]))
    if len(npm_paths) != npm_policy["count"]:
        raise ScanError("npm artifact set is incomplete")
    npm_manifest = manifest.get("npm", {})
    launcher = npm_manifest.get("launcher", {})
    platform_records = npm_manifest.get("platform_packages", [])
    manifest_names = {launcher.get("filename")} | {
        item.get("filename") for item in platform_records
    }
    if (
        len(platform_records) != npm_policy["count"] - 1
        or manifest_names != {path.name for path in npm_paths}
    ):
        raise ScanError("distribution manifest npm records do not match bundle")
    for path in npm_paths:
        digest = _file_digest(_direct_file(path, path.name))
        if path.name == launcher.get("filename"):
            record = launcher
            kind = "npm-launcher"
            target = None
        else:
            record = next(item for item in platform_records if item.get("filename") == path.name)
            kind = "npm-platform"
            target = record.get("target")
        if (
            record.get("sha256") != digest
            or record.get("size_bytes") != path.stat().st_size
            or record.get("version") != version
        ):
            raise ScanError(f"npm record disagrees: {path.name}")
        relative = path.relative_to(bundle).as_posix()
        expected_paths.add(relative)
        item = {
            "id": f"npm-{path.stem}",
            "kind": kind,
            "relative": relative,
            "path": path,
            "sha256": digest,
            "target": target,
            "version": version,
            "required_types": scan["artifact_requirements"][kind]["required_types"],
        }
        if kind == "npm-platform":
            if target not in go_by_target:
                raise ScanError(f"npm platform target is unsupported: {path.name}")
            item["embedded_relative"] = scan["artifact_requirements"][kind]["embedded_binary"]
            item["embedded_sha256"] = next(
                binary["sha256"]
                for binary in records
                if binary["kind"] == "go-binary" and binary["target"] == target
            )
            item["embedded_manifest_relative"] = "package/bin/apgr.binary-manifest.json"
            item["embedded_manifest_sha256"] = next(
                binary["manifest_sha256"]
                for binary in records
                if binary["kind"] == "go-binary" and binary["target"] == target
            )
        records.append(item)

    symlinked_paths = [path for path in bundle.rglob("*") if path.is_symlink()]
    if symlinked_paths:
        raise ScanError(
            "bundle contains symlinked paths: "
            + ", ".join(path.relative_to(bundle).as_posix() for path in symlinked_paths)
        )
    observed_files = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    if observed_files != expected_paths:
        raise ScanError(
            f"bundle file set differs from manifest: extra={sorted(observed_files - expected_paths)}, "
            f"missing={sorted(expected_paths - observed_files)}"
        )
    # SHA256SUMS is the index itself and therefore cannot contain a stable
    # self-digest.  Every other bundle file must be covered exactly once.
    if set(checksums) != expected_paths - {bundle_policy["checksum_file"]}:
        raise ScanError("SHA256SUMS does not cover the exact bundle file set")
    for record in records:
        if checksums.get(record["relative"]) != record["sha256"]:
            raise ScanError(f"checksum record disagrees: {record['relative']}")
    if checksums.get(manifest_name) != _file_digest(manifest_path):
        raise ScanError("distribution manifest checksum is inconsistent")
    return records


def _catalog_summary(document: dict[str, Any]) -> dict[str, Any]:
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise ScanError("Syft SBOM has no artifact collection")
    types: Counter[str] = Counter()
    catalogers: Counter[str] = Counter()
    package_names: list[str] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ScanError("Syft artifact entry is malformed")
        artifact_type = artifact.get("type")
        found_by = artifact.get("foundBy")
        if isinstance(artifact_type, str):
            types[artifact_type] += 1
        if isinstance(found_by, str):
            catalogers[found_by] += 1
        if isinstance(artifact.get("name"), str):
            package_names.append(artifact["name"])
    return {
        "package_count": len(artifacts),
        "file_count": len(document.get("files", []))
        if isinstance(document.get("files"), list)
        else None,
        "types": dict(sorted(types.items())),
        "catalogers": dict(sorted(catalogers.items())),
        "package_names": sorted(package_names),
    }


def _severity_counts(document: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for match in document.get("matches", []):
        if not isinstance(match, dict):
            raise ScanError("Grype match entry is malformed")
        vulnerability = match.get("vulnerability")
        if not isinstance(vulnerability, dict):
            raise ScanError("Grype vulnerability entry is malformed")
        severity = vulnerability.get("severity")
        if not isinstance(severity, str):
            raise ScanError("Grype vulnerability severity is missing")
        counts[severity.lower()] += 1
    return dict(sorted(counts.items()))


def _scan_status(
    summary: dict[str, Any],
    required_types: Sequence[str],
    required_catalogers: Sequence[str] = (),
) -> tuple[str, list[str]]:
    missing = sorted(set(required_types) - set(summary["types"]))
    missing.extend(
        f"cataloger:{cataloger}"
        for cataloger in sorted(set(required_catalogers) - set(summary["catalogers"]))
    )
    if not summary["package_count"]:
        missing = sorted(set(missing) | set(required_types))
    return ("coverage-gap" if missing else "passed", missing)


def _conditional_policy(policy: dict[str, Any]) -> dict[str, Any]:
    """Validate the small policy contract for conditional runtime coverage."""
    try:
        value = policy["scan"]["coverage"]["conditional_dependency_inventory"]
    except (KeyError, TypeError) as error:
        raise ConditionalCoverageError(
            "conditional dependency inventory policy is missing"
        ) from error
    if not isinstance(value, dict):
        raise ConditionalCoverageError(
            "conditional dependency inventory policy is not a receipt contract"
        )
    required = {
        "path",
        "inventory",
        "source",
        "target_python",
        "required_package",
        "required_types",
    }
    if not required.issubset(value):
        raise ConditionalCoverageError(
            "conditional dependency inventory policy is incomplete"
        )
    if (
        not isinstance(value["path"], str)
        or not isinstance(value["inventory"], str)
        or not isinstance(value["source"], str)
        or not isinstance(value["target_python"], str)
        or not isinstance(value["required_package"], str)
        or not isinstance(value["required_types"], list)
        or not all(isinstance(item, str) for item in value["required_types"])
        or value["target_python"] != "3.10"
        or value["required_package"] != "tomli"
        or value["required_types"] != ["python"]
    ):
        raise ConditionalCoverageError(
            "conditional dependency inventory policy has an unsupported target"
        )
    return value


def _normalize_package_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _parse_exact_requirement(requirement: Any, expected_package: str) -> tuple[str, str]:
    if not isinstance(requirement, str):
        raise ConditionalCoverageError("conditional dependency requirement is missing")
    match = re.fullmatch(
        r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.+!_-]*)",
        requirement.strip(),
    )
    if match is None or _normalize_package_name(match.group(1)) != _normalize_package_name(expected_package):
        raise ConditionalCoverageError(
            "conditional dependency requirement is not an exact expected package pin"
        )
    return match.group(1), match.group(2)


def _conditional_source_inventory(
    source: Path,
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Load the maintained dependency inventory and bind its source files."""
    configuration = _conditional_policy(policy)
    inventory_relative = _safe_relative(configuration["path"], label="dependency inventory path")
    inventory_path = _direct_file(source / inventory_relative, "dependency inventory")
    source_relative = _safe_relative(configuration["source"], label="dependency source path")
    source_path = _direct_file(source / source_relative, "dependency source")
    inventory_digest = _file_digest(inventory_path)
    source_digest = _file_digest(source_path)
    try:
        namespace = runpy.run_path(
            os.fspath(inventory_path),
            run_name="__apg_conditional_dependency_inventory__",
        )
        builder = namespace.get("build_inventories")
        if not callable(builder):
            raise TypeError("build_inventories is not callable")
        inventories = builder(source)
    except Exception as error:
        raise ConditionalCoverageError(
            "conditional dependency inventory could not be evaluated: "
            f"{type(error).__name__}"
        ) from error
    if _file_digest(inventory_path) != inventory_digest or _file_digest(source_path) != source_digest:
        raise ConditionalCoverageError("conditional dependency inventory source changed during evaluation")
    if not isinstance(inventories, dict):
        raise ConditionalCoverageError("conditional dependency inventory result is malformed")
    runtime = inventories.get(configuration["inventory"])
    if not isinstance(runtime, dict):
        raise ConditionalCoverageError("conditional dependency runtime receipt is missing")
    requirements = runtime.get("requirements")
    declared = runtime.get("declared")
    marker = runtime.get("marker")
    if (
        not isinstance(requirements, list)
        or len(requirements) != 1
        or not isinstance(declared, list)
        or len(declared) != 1
        or not isinstance(declared[0], str)
        or not isinstance(marker, str)
    ):
        raise ConditionalCoverageError("conditional dependency runtime receipt is incomplete")
    package, version = _parse_exact_requirement(
        requirements[0],
        configuration["required_package"],
    )
    expected_marker = "python_version < '3.11'"
    if marker != expected_marker or "python_version < '3.11'" not in declared[0]:
        raise ConditionalCoverageError("conditional dependency marker is not bound to Python 3.10")
    return {
        "inventory_path": inventory_relative,
        "inventory_sha256": inventory_digest,
        "source_path": source_relative,
        "source_sha256": source_digest,
        "inventory": configuration["inventory"],
        "target_python": configuration["target_python"],
        "package": _normalize_package_name(package),
        "requirement": requirements[0],
        "version": version,
        "declared": declared[0],
        "marker": marker,
    }


def _verify_conditional_source(
    source: Path,
    evidence: dict[str, Any],
) -> None:
    inventory = _direct_file(source / evidence["inventory_path"], "dependency inventory")
    source_file = _direct_file(source / evidence["source_path"], "dependency source")
    if (
        _file_digest(inventory) != evidence["inventory_sha256"]
        or _file_digest(source_file) != evidence["source_sha256"]
    ):
        raise ConditionalCoverageError("conditional dependency source changed during scanning")


def _conditional_direct_child(parent: Path, name: str, label: str) -> Path:
    child = parent / name
    if child.exists() or child.is_symlink():
        raise ConditionalCoverageError(f"{label} must be a new direct directory")
    try:
        child.mkdir(mode=0o700)
    except OSError as error:
        raise ConditionalCoverageError(f"{label} could not be created") from error
    return child


def _conditional_run(
    command: list[str],
    *,
    environment: dict[str, str],
    operation: str,
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> subprocess.CompletedProcess[bytes]:
    try:
        completed = _run(command, environment=environment, runner=runner)
    except ScanError as error:
        raise ConditionalToolError(f"conditional dependency {operation} invocation failed") from error
    if completed.returncode != 0:
        raise ConditionalToolError(
            f"conditional dependency {operation} failed: exit={completed.returncode}"
        )
    return completed


def _conditional_metadata(site: Path, package: str, version: str) -> dict[str, Any]:
    metadata_paths = sorted(site.glob("*.dist-info/METADATA"))
    if len(metadata_paths) != 1:
        raise ConditionalCoverageError(
            "conditional dependency install must contain exactly one metadata receipt"
        )
    metadata_path = _direct_file(metadata_paths[0], "conditional dependency metadata")
    try:
        lines = metadata_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ConditionalCoverageError("conditional dependency metadata is unreadable") from error
    names = [line[6:].strip() for line in lines if line.startswith("Name:")]
    versions = [line[8:].strip() for line in lines if line.startswith("Version:")]
    if len(names) != 1 or len(versions) != 1:
        raise ConditionalCoverageError("conditional dependency metadata is incomplete")
    if _normalize_package_name(names[0]) != package or versions[0] != version:
        raise ConditionalCoverageError("conditional dependency metadata was substituted")
    return {
        "path": metadata_path.relative_to(site).as_posix(),
        "sha256": _file_digest(metadata_path),
        "name": names[0],
        "version": versions[0],
    }


def _conditional_wheel(download: Path, package: str, version: str) -> Path:
    entries = sorted(download.iterdir())
    if len(entries) != 1 or entries[0].is_symlink() or not entries[0].is_file():
        raise ConditionalCoverageError(
            "conditional dependency download must contain exactly one regular wheel"
        )
    wheel = _direct_file(entries[0], "conditional dependency wheel")
    if wheel.suffix.lower() != ".whl":
        raise ConditionalCoverageError("conditional dependency download is not a wheel")
    parts = wheel.stem.split("-")
    if (
        len(parts) < 5
        or _normalize_package_name(parts[0]) != package
        or parts[1] != version
    ):
        raise ConditionalCoverageError("conditional dependency wheel identity is substituted")
    return wheel


def _conditional_package_record(
    document: dict[str, Any],
    package: str,
    version: str,
) -> dict[str, Any]:
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise ConditionalCoverageError("conditional dependency SBOM has no artifact collection")
    matches: list[dict[str, Any]] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("type") != "python":
            continue
        name = artifact.get("name")
        if not isinstance(name, str) or _normalize_package_name(name) != package:
            continue
        if artifact.get("version") != version:
            raise ConditionalCoverageError("conditional dependency SBOM package was substituted")
        purl = artifact.get("purl")
        if purl is not None and purl != f"pkg:pypi/{package}@{version}":
            raise ConditionalCoverageError("conditional dependency SBOM package locator was substituted")
        matches.append(artifact)
    if len(matches) != 1:
        raise ConditionalCoverageError("conditional dependency is absent from the exact SBOM")
    artifact = matches[0]
    return {
        "type": "python",
        "name": artifact.get("name"),
        "version": artifact.get("version"),
        "purl": artifact.get("purl"),
        "found_by": artifact.get("foundBy"),
    }


def _verify_conditional_receipt(path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    """Require the task-owned conditional receipt before accepting evidence."""
    receipt = _direct_file(path, "conditional dependency receipt")
    actual = _file_digest(receipt)
    if expected_sha256 is not None and actual != expected_sha256:
        raise ConditionalCoverageError("conditional dependency receipt digest changed")
    document = _read_json(receipt)
    if not isinstance(document, dict) or document.get("schema") != "apg-conditional-sbom-receipt-v1":
        raise ConditionalCoverageError("conditional dependency receipt is malformed")
    return document


def _scan_conditional_dependency(
    source: Path,
    output: Path,
    *,
    syft: Path,
    syft_config: Path | None,
    grype: Path,
    grype_config: Path | None,
    environment: dict[str, str],
    policy: dict[str, Any],
    redact: Sequence[tuple[Path, str]],
    installer_python: Path | None,
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> dict[str, Any]:
    """Materialize, scan, and receipt-bind the Python 3.10 fallback package."""
    source = _direct_directory(source, "public source")
    output = _direct_directory(output, "SBOM output")
    configuration = _conditional_policy(policy)
    source_evidence = _conditional_source_inventory(source, policy)
    conditional_root = _conditional_direct_child(
        output,
        "conditional-runtime",
        "conditional runtime root",
    )
    target_root = _conditional_direct_child(
        conditional_root,
        f"python-{source_evidence['target_python']}",
        "conditional runtime target",
    )
    download_root = _conditional_direct_child(target_root, "download", "conditional download root")
    site_root = _conditional_direct_child(target_root, "site", "conditional site root")
    cache_root = _conditional_direct_child(target_root, "pip-cache", "conditional pip cache")
    temporary_root = _conditional_direct_child(target_root, "pip-tmp", "conditional pip temporary root")
    pycache_root = _conditional_direct_child(target_root, "pycache", "conditional Python bytecode root")
    installer = Path(installer_python or sys.executable).resolve(strict=True)
    installer = _direct_file(installer, "conditional installer Python")
    if not (stat.S_IMODE(installer.stat().st_mode) & 0o111):
        raise ConditionalCoverageError("conditional installer Python is not executable")
    install_environment = environment.copy()
    install_environment.update(
        {
            "PIP_CACHE_DIR": os.fspath(cache_root),
            "TMPDIR": os.fspath(temporary_root),
            "PIP_NO_INPUT": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_CONFIG_FILE": os.devnull,
            "PYTHONNOUSERSITE": "1",
            "PYTHONPYCACHEPREFIX": os.fspath(pycache_root),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    requirement = source_evidence["requirement"]
    download_command = [
        os.fspath(installer),
        "-m",
        "pip",
        "download",
        "--disable-pip-version-check",
        "--no-deps",
        "--only-binary=:all:",
        "--dest",
        os.fspath(download_root),
        "--python-version",
        source_evidence["target_python"],
        "--implementation",
        "cp",
        "--abi",
        "cp310",
        "--platform",
        "any",
        requirement,
    ]
    download_run = _conditional_run(
        download_command,
        environment=install_environment,
        operation="dependency download",
        runner=runner,
    )
    wheel = _conditional_wheel(
        download_root,
        source_evidence["package"],
        source_evidence["version"],
    )
    wheel_evidence = {
        "path": wheel.relative_to(output).as_posix(),
        "sha256": _file_digest(wheel),
        "size_bytes": wheel.stat().st_size,
    }
    install_command = [
        os.fspath(installer),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-index",
        "--no-deps",
        "--no-build-isolation",
        "--no-compile",
        "--find-links",
        os.fspath(download_root),
        "--target",
        os.fspath(site_root),
        requirement,
    ]
    install_run = _conditional_run(
        install_command,
        environment=install_environment,
        operation="dependency installation",
        runner=runner,
    )
    if _file_digest(wheel) != wheel_evidence["sha256"]:
        raise ConditionalCoverageError("conditional dependency wheel changed during installation")
    metadata = _conditional_metadata(
        site_root,
        source_evidence["package"],
        source_evidence["version"],
    )
    package_directory = _direct_directory(
        site_root / source_evidence["package"].replace("-", "_"),
        "conditional dependency package",
    )
    _direct_file(package_directory / "__init__.py", "conditional dependency package initializer")
    view = {
        "target_python": source_evidence["target_python"],
        "requirement": requirement,
        "declared": source_evidence["declared"],
        "marker": source_evidence["marker"],
        "wheel": wheel_evidence,
        "metadata": metadata,
        "package": {
            "path": package_directory.relative_to(output).as_posix(),
            "tree_sha256": _tree_digest(package_directory),
        },
        "site_tree_sha256": _tree_digest(site_root),
        "download": {
            "status": "passed",
            "returncode": download_run.returncode,
            "stdout_present": bool(download_run.stdout.strip()),
            "stderr_present": bool(download_run.stderr.strip()),
        },
        "installation": {
            "status": "passed",
            "returncode": install_run.returncode,
            "stdout_present": bool(install_run.stdout.strip()),
            "stderr_present": bool(install_run.stderr.strip()),
        },
    }
    _verify_conditional_source(source, source_evidence)
    sbom_path = target_root / "sbom.syft.json"
    try:
        sbom_document, syft_run = _scan_document(
            scanner=syft,
            config=syft_config,
            source=f"dir:{site_root}",
            output=sbom_path,
            environment=environment,
            runner=runner,
        )
    except ScanError as error:
        raise ConditionalToolError("conditional dependency Syft scan failed") from error
    _direct_file(sbom_path, "conditional dependency SBOM")
    sbom_summary = _catalog_summary(sbom_document)
    coverage_status, missing_types = _scan_status(
        sbom_summary,
        configuration["required_types"],
    )
    if coverage_status != "passed":
        raise ConditionalCoverageError(
            "conditional dependency SBOM coverage is incomplete: "
            + ",".join(missing_types)
        )
    package_record = _conditional_package_record(
        sbom_document,
        source_evidence["package"],
        source_evidence["version"],
    )
    sbom_evidence = {
        "path": sbom_path.relative_to(output).as_posix(),
        "sha256": _file_digest(sbom_path),
        "input_view_sha256": view["site_tree_sha256"],
        "package_count": sbom_summary["package_count"],
        "file_count": sbom_summary["file_count"],
        "types": sbom_summary["types"],
        "catalogers": sbom_summary["catalogers"],
        "package_names": sbom_summary["package_names"],
        "required_types": configuration["required_types"],
        "missing_types": missing_types,
        "coverage_status": coverage_status,
        "package": package_record,
        "syft_returncode": syft_run.returncode,
        "syft_stderr": bool(syft_run.stderr.strip()),
    }
    grype_path = target_root / "grype.json"
    try:
        grype_document, grype_run = _grype_document(
            scanner=grype,
            config=grype_config,
            sbom=sbom_path,
            output=grype_path,
            environment=environment,
            runner=runner,
        )
    except ScanError as error:
        raise ConditionalToolError("conditional dependency Grype scan failed") from error
    _direct_file(grype_path, "conditional dependency Grype report")
    matches = grype_document.get("matches")
    if not isinstance(matches, list):
        raise ConditionalToolError("conditional dependency Grype report is malformed")
    severities = _severity_counts(grype_document)
    blocking = [severity for severity in ("high", "critical") if severities.get(severity)]
    vulnerability_status = (
        "policy-finding"
        if grype_run.returncode == 2 or blocking
        else "passed"
    )
    grype_evidence = {
        "path": grype_path.relative_to(output).as_posix(),
        "sha256": _file_digest(grype_path),
        "input_sbom_sha256": sbom_evidence["sha256"],
        "match_count": len(matches),
        "severity_counts": severities,
        "blocking_severities": blocking,
        "returncode": grype_run.returncode,
        "status": vulnerability_status,
        "source": grype_document.get("source"),
        "descriptor": grype_document.get("descriptor"),
    }
    _verify_conditional_source(source, source_evidence)
    if _file_digest(wheel) != wheel_evidence["sha256"]:
        raise ConditionalCoverageError("conditional dependency wheel changed during scanning")
    if _tree_digest(site_root) != view["site_tree_sha256"]:
        raise ConditionalCoverageError("conditional dependency view changed during scanning")
    receipt_path = target_root / "receipt.json"
    receipt_document = {
        "schema": "apg-conditional-sbom-receipt-v1",
        "target": "conditional-runtime/python-3.10",
        "source": source_evidence,
        "view": view,
        "sbom": sbom_evidence,
        "grype": grype_evidence,
        "status": vulnerability_status,
    }
    receipt_path.write_text(
        json.dumps(receipt_document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt_sha256 = _file_digest(receipt_path)
    _verify_conditional_receipt(receipt_path, receipt_sha256)
    redacted = tuple((path, replacement) for path, replacement in redact)
    return {
        "id": "conditional-python-runtime",
        "kind": "conditional-dependency",
        "target": "conditional-runtime/python-3.10",
        "target_python": source_evidence["target_python"],
        "source": source_evidence,
        "view": view,
        "sbom": sbom_evidence,
        "grype": grype_evidence,
        "receipt": {
            "path": receipt_path.relative_to(output).as_posix(),
            "sha256": receipt_sha256,
        },
        "status": vulnerability_status,
        "redacted_scanners": {
            "syft": _redact_paths(os.fspath(syft), redacted),
            "grype": _redact_paths(os.fspath(grype), redacted),
        },
    }


def _scan_document(
    *,
    scanner: Path,
    config: Path | None,
    source: str,
    output: Path,
    environment: dict[str, str],
    exclude: Sequence[str] = (),
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[bytes]]:
    command = [os.fspath(scanner), "scan", source]
    if config is not None:
        command.extend(["--config", os.fspath(config)])
    command.extend(["--override-default-catalogers", "all", "--quiet"])
    for pattern in exclude:
        command.extend(["--exclude", pattern])
    command.extend(["-o", f"syft-json={output}"])
    completed = _run(command, environment=environment, runner=runner)
    if completed.returncode != 0 or not output.is_file():
        raise ScanError("Syft failed to produce an SBOM")
    document = _read_json(output)
    if not isinstance(document, dict):
        raise ScanError("Syft SBOM root is not an object")
    return document, completed


def _grype_document(
    *,
    scanner: Path,
    config: Path | None,
    sbom: Path,
    output: Path,
    environment: dict[str, str],
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[bytes]]:
    command = [os.fspath(scanner), f"sbom:{sbom}"]
    if config is not None:
        command.extend(["--config", os.fspath(config)])
    command.extend(["--quiet", "-o", "json", "--file", os.fspath(output), "--fail-on", "high"])
    completed = _run(command, environment=environment, runner=runner)
    if not output.is_file():
        raise ScanError("Grype failed to produce a report")
    document = _read_json(output)
    if not isinstance(document, dict):
        raise ScanError("Grype report root is not an object")
    if completed.returncode not in {0, 2}:
        raise ScanError("Grype scanner failed operationally")
    return document, completed


def _scan_derived_sdist(
    record: dict[str, Any],
    *,
    output: Path,
    install_root: Path,
    installation: dict[str, Any],
    syft: Path,
    syft_config: Path | None,
    grype: Path,
    grype_config: Path | None,
    environment: dict[str, str],
    policy: dict[str, Any],
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> dict[str, Any]:
    """Scan the installed sdist and retain its raw/derived coverage boundary."""
    derived_output = output / "artifacts" / record["id"] / "derived-install"
    derived_output.mkdir(mode=0o700)
    sbom_path = derived_output / "sbom.syft.json"
    sbom, syft_completed = _scan_document(
        scanner=syft,
        config=syft_config,
        source=f"dir:{install_root}",
        output=sbom_path,
        environment=environment,
        runner=runner,
    )
    summary = _catalog_summary(sbom)
    coverage_status, missing_types = _scan_status(
        summary,
        record["required_types"],
    )
    grype_path = derived_output / "grype.json"
    grype_document, grype_completed = _grype_document(
        scanner=grype,
        config=grype_config,
        sbom=sbom_path,
        output=grype_path,
        environment=environment,
        runner=runner,
    )
    matches = grype_document.get("matches", [])
    if not isinstance(matches, list):
        raise ScanError("derived Grype report match collection is malformed")
    severities = _severity_counts(grype_document)
    blocking = [severity for severity in ("high", "critical") if severities.get(severity)]
    vulnerability_status = (
        "policy-finding"
        if grype_completed.returncode == 2 or blocking
        else "passed"
    )
    if _file_digest(record["path"]) != record["sha256"]:
        raise ScanError("Python sdist changed during derived scanning")
    _verify_installed_sdist_digests(install_root, installation)
    return {
        "installation": installation,
        "source_archive_sha256": installation["archive_sha256"],
        "sbom": {
            "path": sbom_path.relative_to(output).as_posix(),
            "sha256": _file_digest(sbom_path),
            "source_archive_sha256": installation["archive_sha256"],
            "package_count": summary["package_count"],
            "file_count": summary["file_count"],
            "types": summary["types"],
            "catalogers": summary["catalogers"],
            "package_names": summary["package_names"],
            "required_types": record["required_types"],
            "missing_types": missing_types,
            "coverage_status": coverage_status,
            "source": sbom.get("source"),
            "syft_returncode": syft_completed.returncode,
            "syft_stderr": bool(syft_completed.stderr.strip()),
        },
        "grype": {
            "path": grype_path.relative_to(output).as_posix(),
            "sha256": _file_digest(grype_path),
            "source_archive_sha256": installation["archive_sha256"],
            "input_sbom_sha256": _file_digest(sbom_path),
            "match_count": len(matches),
            "severity_counts": severities,
            "blocking_severities": blocking,
            "returncode": grype_completed.returncode,
            "status": vulnerability_status,
            "source": grype_document.get("source"),
            "descriptor": grype_document.get("descriptor"),
        },
    }


def _coverage_union(
    raw_summary: dict[str, Any],
    derived_summary: dict[str, Any],
    required_types: Sequence[str],
) -> dict[str, Any]:
    """Combine only the raw archive and derived install catalog coverage."""
    covered_types = sorted(
        set(raw_summary.get("types", {})) | set(derived_summary.get("types", {}))
    )
    missing_types = sorted(set(required_types) - set(covered_types))
    return {
        "required_types": list(required_types),
        "covered_types": covered_types,
        "missing_types": missing_types,
        "status": "coverage-gap" if missing_types else "passed",
    }


def _scan_record(
    record: dict[str, Any],
    *,
    source: Path,
    output: Path,
    syft: Path,
    syft_config: Path | None,
    grype: Path,
    grype_config: Path | None,
    environment: dict[str, str],
    policy: dict[str, Any],
    redact: Sequence[tuple[Path, str]],
    installer_python: Path | None,
    runner: Callable[..., subprocess.CompletedProcess[bytes]],
) -> dict[str, Any]:
    artifact_output = output / "artifacts" / record["id"]
    artifact_output.mkdir(mode=0o700, parents=True)
    scan_root = record["path"]
    extraction: dict[str, Any] | None = None
    if record["kind"] in {"python-wheel", "python-sdist", "npm-launcher", "npm-platform"}:
        extraction_root = output / "extracted" / record["id"]
        extraction = _extract_archive(record["path"], extraction_root)
        scan_root = extraction_root
        embedded_relative = record.get("embedded_relative")
        if embedded_relative:
            embedded = _direct_file(extraction_root / embedded_relative, "embedded native binary")
            embedded_digest = _file_digest(embedded)
            if embedded_digest != record["embedded_sha256"]:
                raise ScanError(f"embedded binary digest mismatch: {record['id']}")
            embedded_manifest_relative = record.get("embedded_manifest_relative")
            embedded_manifest_sha256 = record.get("embedded_manifest_sha256")
            if embedded_manifest_relative and embedded_manifest_sha256:
                embedded_manifest_path = _direct_file(
                    extraction_root / embedded_manifest_relative,
                    "embedded binary manifest",
                )
                if _file_digest(embedded_manifest_path) != embedded_manifest_sha256:
                    raise ScanError(f"embedded binary manifest digest mismatch: {record['id']}")
                embedded_manifest = _read_json(embedded_manifest_path)
                identity = (
                    embedded_manifest.get("build_identity")
                    if isinstance(embedded_manifest, dict)
                    else None
                )
                if (
                    not isinstance(embedded_manifest, dict)
                    or embedded_manifest.get("schema_version") != "apg.binary-manifest/v1"
                    or embedded_manifest.get("sha256") != embedded_digest
                    or not isinstance(identity, dict)
                    or identity.get("target") != record.get("target")
                    or identity.get("version") != record.get("version")
                ):
                    raise ScanError(f"embedded binary manifest identity mismatch: {record['id']}")
            extraction["embedded_binary"] = {
                "path": embedded_relative,
                "sha256": embedded_digest,
                "matches": True,
            }
    sbom_path = artifact_output / "sbom.syft.json"
    source_arg = (
        f"file:{scan_root}" if record["kind"] == "go-binary" else f"dir:{scan_root}"
    )
    sbom, syft_completed = _scan_document(
        scanner=syft,
        config=syft_config,
        source=source_arg,
        output=sbom_path,
        environment=environment,
        runner=runner,
    )
    summary = _catalog_summary(sbom)
    raw_coverage_status, raw_missing_types = _scan_status(
        summary,
        record["required_types"],
    )
    coverage_status = raw_coverage_status
    grype_path = artifact_output / "grype.json"
    grype_document, grype_completed = _grype_document(
        scanner=grype,
        config=grype_config,
        sbom=sbom_path,
        output=grype_path,
        environment=environment,
        runner=runner,
    )
    matches = grype_document.get("matches", [])
    if not isinstance(matches, list):
        raise ScanError("Grype report match collection is malformed")
    severities = _severity_counts(grype_document)
    blocking = [severity for severity in ("high", "critical") if severities.get(severity)]
    if grype_completed.returncode == 2 or blocking:
        vulnerability_status = "policy-finding"
    else:
        vulnerability_status = "passed"
    derived_install: dict[str, Any] | None = None
    coverage_union: dict[str, Any] | None = None
    if record["kind"] == "python-sdist":
        install_root, installation = _install_sdist(
            record,
            output,
            installer_python,
            environment,
            runner=runner,
        )
        derived_install = _scan_derived_sdist(
            record,
            output=output,
            install_root=install_root,
            installation=installation,
            syft=syft,
            syft_config=syft_config,
            grype=grype,
            grype_config=grype_config,
            environment=environment,
            policy=policy,
            runner=runner,
        )
        coverage_union = _coverage_union(
            summary,
            derived_install["sbom"],
            record["required_types"],
        )
        coverage_status = coverage_union["status"]
        if derived_install["grype"]["status"] != "passed":
            vulnerability_status = derived_install["grype"]["status"]
    status = "passed" if coverage_status == "passed" else "coverage-gap"
    if status == "passed" and vulnerability_status != "passed":
        status = vulnerability_status
    redacted = tuple((path, replacement) for path, replacement in redact)
    result = {
        "id": record["id"],
        "kind": record["kind"],
        "target": record["relative"],
        "target_sha256": record["sha256"],
        "target_platform": record.get("target"),
        "embedded_binary": extraction.get("embedded_binary") if extraction else None,
        "extraction": extraction,
        "sbom": {
            "path": sbom_path.relative_to(output).as_posix(),
            "sha256": _file_digest(sbom_path),
            "package_count": summary["package_count"],
            "file_count": summary["file_count"],
            "types": summary["types"],
            "catalogers": summary["catalogers"],
            "package_names": summary["package_names"],
            "required_types": record["required_types"],
            "missing_types": raw_missing_types,
            "coverage_status": raw_coverage_status,
            "source": sbom.get("source"),
            "syft_returncode": syft_completed.returncode,
            "syft_stderr": bool(syft_completed.stderr.strip()),
        },
        "grype": {
            "path": grype_path.relative_to(output).as_posix(),
            "sha256": _file_digest(grype_path),
            "input_sbom_sha256": _file_digest(sbom_path),
            "match_count": len(matches),
            "severity_counts": severities,
            "blocking_severities": blocking,
            "returncode": grype_completed.returncode,
            "status": vulnerability_status,
            "source": grype_document.get("source"),
            "descriptor": grype_document.get("descriptor"),
        },
        "status": status,
        "redacted_scanners": {
            "syft": _redact_paths(os.fspath(syft), redacted),
            "grype": _redact_paths(os.fspath(grype), redacted),
        },
    }
    if derived_install is not None and coverage_union is not None:
        result["derived_install"] = derived_install
        result["coverage_union"] = coverage_union
    return result


def _ecosystems(document: dict[str, Any]) -> set[str]:
    """Return ecosystem names from SPDX or Syft JSON package records."""
    found: set[str] = set()
    records = document.get("packages", document.get("artifacts", []))
    if not isinstance(records, list):
        return found
    for package in records:
        if not isinstance(package, dict):
            continue
        package_type = str(package.get("type", ""))
        if package_type == "go-module":
            found.add("go-module")
        elif package_type == "python":
            found.add("python-package")
        elif package_type == "npm":
            found.add("npm-package")
        references = package.get("externalRefs", [])
        if isinstance(references, list):
            for reference in references:
                if not isinstance(reference, dict):
                    continue
                locator = str(reference.get("referenceLocator", ""))
                if locator.startswith("pkg:golang/"):
                    found.add("go-module")
                elif locator.startswith("pkg:pypi/"):
                    found.add("python-package")
                elif locator.startswith("pkg:npm/"):
                    found.add("npm-package")
        purl = str(package.get("purl", ""))
        if purl.startswith("pkg:golang/"):
            found.add("go-module")
        elif purl.startswith("pkg:pypi/"):
            found.add("python-package")
        elif purl.startswith("pkg:npm/"):
            found.add("npm-package")
    return found


def _load_spdx(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"SBOM must be a direct regular file: {path}")
    document = _read_json(path)
    if not isinstance(document, dict) or document.get("spdxVersion") not in {"SPDX-2.2", "SPDX-2.3"}:
        raise ValueError(f"unsupported SPDX version in {path.name}")
    packages = document.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError(f"SBOM has no packages: {path.name}")
    return document


def _iter_targets(policy: dict[str, Any]) -> Iterable[tuple[str, Path, Path]]:
    source = policy["targets"]["source"]
    yield "source", ROOT / source["path"], ROOT / source["sbom_file"]
    python = policy["targets"]["deliverables"]["python"]
    yield "python-deliverables", ROOT / python["artifacts_dir"], ROOT / python["sbom_file"]
    for target in policy["targets"]["deliverables"]["native_binaries"]["targets"]:
        yield target["binary"], ROOT / target["path"], ROOT / target["sbom_file"]


def record_sboms(policy_path: Path = POLICY) -> dict[str, Any]:
    """Retain the legacy local-build record command for existing CI owners."""
    policy = _load_policy(policy_path)
    records: list[dict[str, Any]] = []
    covered: set[str] = set()
    for name, target, sbom in _iter_targets(policy):
        document = _load_spdx(sbom)
        ecosystems = sorted(_ecosystems(document))
        covered.update(ecosystems)
        records.append(
            {
                "name": name,
                "target": target.relative_to(ROOT).as_posix(),
                "target_sha256": _target_digest(target),
                "sbom": sbom.relative_to(ROOT).as_posix(),
                "sbom_sha256": _file_digest(sbom),
                "package_count": len(document["packages"]),
                "ecosystems": ecosystems,
            }
        )
    required = set(policy["coverage"]["required_ecosystems"])
    missing = sorted(required - covered)
    if missing:
        raise ValueError(f"SBOM ecosystem coverage is incomplete: {missing}")
    result = {
        "schema": RECORD_SCHEMA,
        "algorithm": policy["coverage"]["digest_algorithm"],
        "targets": records,
        "covered_ecosystems": sorted(covered),
        "required_ecosystems": sorted(required),
        "status": "passed",
    }
    output = ROOT / "build/sboms/manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def validate_grype_report(
    report_path: Path,
    *,
    policy_path: Path = ROOT / "release/ci/grype.yaml",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate Grype identity, freshness, and High/Critical policy results."""
    config = _parse_config_text(policy_path)
    if config.get("fail-on-severity") != "high":
        raise ValueError("Grype policy must block High and Critical findings")
    if config.get("only-fixed") is not False:
        raise ValueError("Grype policy must retain unfixed findings")
    database = config.get("db")
    if not isinstance(database, dict):
        raise TypeError("Grype policy has no database validation configuration")
    for key in ("require-update-check", "validate-age", "validate-by-hash-on-start"):
        if database.get(key) is not True:
            raise ValueError(f"Grype policy must enable {key}")
    waivers = config.get("ignore", [])
    if not isinstance(waivers, list):
        raise TypeError("Grype policy ignore list is malformed")
    now = now or datetime.now(timezone.utc)
    for waiver in waivers:
        if not isinstance(waiver, dict):
            raise TypeError("Grype waiver is malformed")
        if not all(
            waiver.get(key) for key in ("vulnerability", "package", "reason", "owner", "expires")
        ):
            raise ValueError("Grype waiver must identify finding, package, reason, owner, and expiry")
        expires = _parse_timestamp(waiver["expires"], "Grype waiver expiry")
        if expires <= now.astimezone(timezone.utc):
            raise ValueError(f"Grype waiver is expired: {waiver['vulnerability']}")
    report = _read_json(report_path)
    if not isinstance(report, dict) or not isinstance(report.get("matches"), list):
        raise TypeError("Grype report has no match collection")
    descriptor = report.get("descriptor")
    if not isinstance(descriptor, dict) or not descriptor.get("version"):
        raise TypeError("Grype report has no tool identity")
    database_report = report.get("db") or descriptor.get("db")
    if not isinstance(database_report, dict):
        raise TypeError("Grype report has no vulnerability database identity")
    status = database_report.get("status")
    if status in {"error", "failed", "unavailable"}:
        raise TypeError("Grype vulnerability database reports failure")
    if database_report.get("valid") is False:
        raise TypeError("Grype vulnerability database is invalid")
    built = database_report.get("built") or database_report.get("builtAt") or database_report.get("lastChecked")
    if not built:
        raise ValueError("Grype report has no database freshness timestamp")
    built_at = _parse_timestamp(built, "Grype database freshness")
    observed_now = now.astimezone(timezone.utc)
    age_hours = (observed_now - built_at).total_seconds() / 3600
    maximum_age = _parse_duration_hours(database.get("max-allowed-built-age", "120h"))
    if age_hours < 0 or age_hours > maximum_age:
        raise ValueError("Grype vulnerability database is stale")
    blocking: list[dict[str, Any]] = []
    severities: Counter[str] = Counter()
    for match in report["matches"]:
        if not isinstance(match, dict):
            raise TypeError("Grype match is malformed")
        vulnerability = match.get("vulnerability", {})
        if not isinstance(vulnerability, dict):
            raise TypeError("Grype vulnerability is malformed")
        severity_value = vulnerability.get("severity")
        if not isinstance(severity_value, str) or not severity_value.strip():
            raise TypeError("Grype vulnerability severity is missing")
        severity = severity_value.lower()
        severities[severity] += 1
        if severity in {"high", "critical"}:
            artifact = match.get("artifact", {})
            blocking.append(
                {
                    "id": vulnerability.get("id", "<unknown>"),
                    "severity": severity,
                    "artifact": artifact.get("name", "<unknown>")
                    if isinstance(artifact, dict)
                    else "<unknown>",
                }
            )
    return {
        "schema": GRYPE_SCHEMA,
        "report": (
            report_path.relative_to(ROOT).as_posix()
            if report_path.is_relative_to(ROOT)
            else report_path.name
        ),
        "tool_version": descriptor["version"],
        "database": {
            "status": database_report.get("status", "observed"),
            "built": str(built),
            "age_hours": round(age_hours, 3),
        },
        "match_count": len(report["matches"]),
        "severity_counts": dict(sorted(severities.items())),
        "blocking_findings": blocking,
        "status": "passed" if not blocking else "failed",
    }


def scan_bundle(
    source: Path,
    artifacts: Path,
    output: Path,
    scanner_root: Path,
    *,
    policy_path: Path = POLICY,
    installer_python: Path | None = None,
    now: datetime | None = None,
    runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> dict[str, Any]:
    """Scan one public source tree and one exact exported distribution bundle."""
    source = _direct_directory(source.resolve(strict=True), "public source")
    artifacts = _direct_directory(artifacts.resolve(strict=True), "exported bundle")
    scanner_root = _direct_directory(scanner_root.resolve(strict=True), "scanner root")
    output = output.resolve()
    if source == artifacts or source == scanner_root or artifacts == scanner_root:
        raise ScanError("scan roots must be distinct")
    for root, label in (
        (source, "public source"),
        (artifacts, "exported bundle"),
        (scanner_root, "scanner root"),
    ):
        if output == root or output.is_relative_to(root) or root.is_relative_to(output):
            raise ScanError(f"scan output overlaps {label}")
    if (source / "private").exists() or (source / "private").is_symlink():
        raise ScanError("public source contains publication-excluded private content")
    if output.exists():
        if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
            raise ScanError("scan output must be a new empty directory")
    else:
        output.mkdir(mode=0o700, parents=True)
    policy = _load_policy(policy_path)
    scan = policy["scan"]
    syft_policy = scan["scanner"]["syft"]
    grype_policy = scan["scanner"]["grype"]
    syft = _direct_file(scanner_root / syft_policy["binary"], "Syft binary")
    grype = _direct_file(scanner_root / grype_policy["binary"], "Grype binary")
    if not (stat.S_IMODE(syft.stat().st_mode) & 0o111) or not (stat.S_IMODE(grype.stat().st_mode) & 0o111):
        raise ScanError("scanner binaries must be executable")
    syft_config = _resolve_config(scanner_root, syft_policy["config"], None)
    grype_config = _resolve_config(
        scanner_root,
        grype_policy["config"],
        ROOT / "release/ci/grype.yaml",
    )
    grype_config_values = _parse_config_text(grype_config)
    _validate_grype_config(grype_config_values, policy)
    environment = os.environ.copy()
    _prepare_grype_database_cache(scanner_root, environment)
    environment["GRYPE_CHECK_FOR_APP_UPDATE"] = "false"
    environment["GRYPE_EXTERNAL_SOURCES_ENABLE"] = "false"
    redact = ((source, "<source>"), (artifacts, "<artifacts>"), (scanner_root, "<scanner>"), (output, "<output>"))
    identities = {
        "syft": _scanner_identity(
            syft,
            expected_version=syft_policy["version"],
            name="Syft",
            environment=environment,
            redact=redact,
            runner=runner,
        ),
        "grype": _scanner_identity(
            grype,
            expected_version=grype_policy["version"],
            name="Grype",
            environment=environment,
            redact=redact,
            runner=runner,
        ),
    }
    database = _database_identity(
        scanner_root,
        grype,
        grype_config,
        grype_config_values,
        policy,
        environment,
        now=now,
        runner=runner,
    )
    checksums = _parse_checksums(artifacts, scan["bundle"]["checksum_file"])
    records = _manifest_file_records(artifacts, policy, checksums)
    for directory in ("source", "artifacts", "extracted"):
        (output / directory).mkdir(mode=0o700)
    source_sbom_path = output / "source" / "source.syft.json"
    source_document, source_syft = _scan_document(
        scanner=syft,
        config=syft_config,
        source=f"dir:{source}",
        output=source_sbom_path,
        environment=environment,
        exclude=scan["source"]["exclude"],
        runner=runner,
    )
    source_summary = _catalog_summary(source_document)
    source_coverage, source_missing = _scan_status(
        source_summary,
        scan["coverage"]["required_source_types"],
        scan["source"].get("required_catalogers", ()),
    )
    source_grype_path = output / "source" / "grype.json"
    source_grype, source_grype_run = _grype_document(
        scanner=grype,
        config=grype_config,
        sbom=source_sbom_path,
        output=source_grype_path,
        environment=environment,
        runner=runner,
    )
    source_severity = _severity_counts(source_grype)
    source_blocking = [severity for severity in ("high", "critical") if source_severity.get(severity)]
    source_record = {
        "target": ".",
        "target_sha256": _target_digest(source, scan["source"]["exclude"]),
        "sbom": {
            "path": source_sbom_path.relative_to(output).as_posix(),
            "sha256": _file_digest(source_sbom_path),
            "package_count": source_summary["package_count"],
            "file_count": source_summary["file_count"],
            "types": source_summary["types"],
            "catalogers": source_summary["catalogers"],
            "package_names": source_summary["package_names"],
            "required_types": scan["coverage"]["required_source_types"],
            "required_catalogers": scan["source"].get("required_catalogers", []),
            "missing_types": source_missing,
            "coverage_status": source_coverage,
            "syft_returncode": source_syft.returncode,
        },
        "grype": {
            "path": source_grype_path.relative_to(output).as_posix(),
            "sha256": _file_digest(source_grype_path),
            "input_sbom_sha256": _file_digest(source_sbom_path),
            "match_count": len(source_grype.get("matches", [])),
            "severity_counts": source_severity,
            "blocking_severities": source_blocking,
            "returncode": source_grype_run.returncode,
            "status": "policy-finding" if source_blocking or source_grype_run.returncode == 2 else "passed",
            "descriptor": source_grype.get("descriptor"),
        },
        "status": (
            "coverage-gap"
            if source_coverage != "passed"
            else "policy-finding"
            if source_blocking or source_grype_run.returncode == 2
            else "passed"
        ),
    }
    artifact_results: list[dict[str, Any]] = []
    for record in records:
        try:
            artifact_results.append(
                _scan_record(
                    record,
                    source=source,
                    output=output,
                    syft=syft,
                    syft_config=syft_config,
                    grype=grype,
                    grype_config=grype_config,
                    environment=environment,
                    policy=policy,
                    redact=redact,
                    installer_python=installer_python,
                    runner=runner,
                )
            )
        except (OSError, ScanError, TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
            artifact_results.append(
                {
                    "id": record["id"],
                    "kind": record["kind"],
                    "target": record["relative"],
                    "target_sha256": record["sha256"],
                    "status": "tool-failure",
                    "error": str(error),
                }
            )
    conditional_target = "conditional-runtime/python-3.10"
    try:
        conditional_result = _scan_conditional_dependency(
            source,
            output,
            syft=syft,
            syft_config=syft_config,
            grype=grype,
            grype_config=grype_config,
            environment=environment,
            policy=policy,
            redact=redact,
            installer_python=installer_python,
            runner=runner,
        )
    except ConditionalToolError as error:
        conditional_result = {
            "id": "conditional-python-runtime",
            "kind": "conditional-dependency",
            "target": conditional_target,
            "status": "tool-failure",
            "error": str(error),
        }
    except (OSError, ConditionalCoverageError, ScanError, TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        conditional_result = {
            "id": "conditional-python-runtime",
            "kind": "conditional-dependency",
            "target": conditional_target,
            "status": "coverage-gap",
            "error": str(error),
        }
    all_results = [source_record, *artifact_results, conditional_result]
    severity_counts: Counter[str] = Counter()
    for result in all_results:
        grype_results: list[dict[str, Any]] = []
        if isinstance(result.get("grype"), dict):
            grype_results.append(result["grype"])
        derived = result.get("derived_install")
        if isinstance(derived, dict) and isinstance(derived.get("grype"), dict):
            grype_results.append(derived["grype"])
        for grype_result in grype_results:
            for severity, count in grype_result.get("severity_counts", {}).items():
                severity_counts[severity] += count
    missing = [
        result.get("target", result.get("id", "<unknown>"))
        for result in all_results
        if result.get("status") == "coverage-gap"
    ]
    findings = [
        result.get("target", result.get("id", "<unknown>"))
        for result in all_results
        if result.get("status") == "policy-finding"
    ]
    failures = [
        result.get("target", result.get("id", "<unknown>"))
        for result in all_results
        if result.get("status") == "tool-failure"
    ]
    result = {
        "schema": SCAN_SCHEMA,
        "source": source_record,
        "artifacts": artifact_results,
        "conditional_dependency": conditional_result,
        "scanner": identities,
        "database": database,
        "policy": {
            "grype_fail_on": grype_policy["fail_on"],
            "custom_ignores": grype_policy["custom_ignores"],
            "catalogers": "all",
            "lower_severities_retained": True,
            "empty_or_unsupported_inventory_is_clean": False,
        },
        "summary": {
            "artifact_count": len(artifact_results),
            "conditional_dependency_count": 1,
            "sbom_count": 1
            + sum(
                int("sbom" in item)
                + int(
                    isinstance(item.get("derived_install"), dict)
                    and "sbom" in item["derived_install"]
                )
                for item in artifact_results
            )
            + int("sbom" in conditional_result),
            "conditional_sbom_count": int("sbom" in conditional_result),
            "grype_count": 1
            + sum(
                int("grype" in item)
                + int(
                    isinstance(item.get("derived_install"), dict)
                    and "grype" in item["derived_install"]
                )
                for item in artifact_results
            )
            + int("grype" in conditional_result),
            "conditional_grype_count": int("grype" in conditional_result),
            "coverage_gaps": missing,
            "policy_findings": findings,
            "tool_failures": failures,
            "severity_counts": dict(sorted(severity_counts.items())),
            "status": "passed" if not missing and not findings and not failures else "blocked",
        },
    }
    result["status"] = result["summary"]["status"]
    output_report = output / "scan-results.json"
    output_report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    record = subparsers.add_parser("record")
    record.add_argument("--policy", type=Path, default=POLICY)
    grype = subparsers.add_parser("grype")
    grype.add_argument("--report", required=True, type=Path)
    scan = subparsers.add_parser("scan")
    scan.add_argument("--source", required=True, type=Path)
    scan.add_argument("--artifacts", required=True, type=Path)
    scan.add_argument("--output", required=True, type=Path)
    scan.add_argument("--scanner-root", required=True, type=Path)
    scan.add_argument("--installer-python", type=Path, default=None)
    scan.add_argument("--policy", type=Path, default=POLICY)
    args = parser.parse_args(argv)
    try:
        if args.command == "record":
            result = record_sboms(args.policy)
        elif args.command == "grype":
            result = validate_grype_report(args.report)
        else:
            result = scan_bundle(
                args.source,
                args.artifacts,
                args.output,
                args.scanner_root,
                policy_path=args.policy,
                installer_python=args.installer_python,
            )
    except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(json.dumps({"schema": SCAN_SCHEMA, "status": "failed", "error": str(error)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "passed" or result.get("summary", {}).get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
