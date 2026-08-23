"""Build and inspect the deterministic APGR npm package set.

This module is deliberately a packager, not a Go build owner. Its input is
one direct executable and one canonical ``apg.binary-manifest/v1`` JSON file
per supported target, as produced by :mod:`apg_go_build`. It copies those
bytes into the platform package and never invokes a compiler or a network
client.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import gzip
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
import tempfile
from typing import Any, Mapping, Sequence

import apg_distribution_candidate_contract as candidate_contract


MANIFEST_SCHEMA = "apg.binary-manifest/v1"
BUILD_INFO_SCHEMA = "apg.build-info/v1"
MODULE_PATH = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
BINARY_BASENAME = "apgr"
BUILD_FLAGS = ("CGO_ENABLED=0", "-trimpath", "-buildvcs=false", "-buildid=")
LAUNCHER_NAME = "@knowledge-forge-ai/apgr"
NODE_ENGINE = ">=22.0.0"
LICENSE_FILES = ("LICENSE", "NOTICE", "COMMERCIAL-LICENSE.md")
LAUNCHER_TEMPLATE = "launcher/package.json"
PLATFORM_TEMPLATE = "platform/package.json"
LAUNCHER_SOURCE = "launcher/index.js"

PUBLICATION_ORDER = candidate_contract.npm_publication_order()



@dataclass(frozen=True, slots=True)
class Target:
    go_target: str
    package_name: str
    os_name: str
    cpu: str
    slug: str


TARGETS = (
    Target(
        "darwin/arm64",
        "@knowledge-forge-ai/apgr-darwin-arm64",
        "darwin",
        "arm64",
        "darwin-arm64",
    ),
    Target(
        "linux/amd64",
        "@knowledge-forge-ai/apgr-linux-x64",
        "linux",
        "x64",
        "linux-x64",
    ),
    Target(
        "linux/arm64",
        "@knowledge-forge-ai/apgr-linux-arm64",
        "linux",
        "arm64",
        "linux-arm64",
    ),
)
TARGET_BY_GO = {target.go_target: target for target in TARGETS}
TARGET_BY_SLUG = {target.slug: target for target in TARGETS}


class NpmDistributionError(RuntimeError):
    """The npm candidate cannot be assembled or inspected safely."""


@dataclass(frozen=True, slots=True)
class Artifact:
    target: str
    binary: Path
    manifest_path: Path | None = None
    manifest_bytes: bytes | None = None


@dataclass(frozen=True, slots=True)
class PackageRecord:
    name: str
    version: str
    target: str | None
    filename: str
    sha256: str
    size_bytes: int


def _read_direct(path: Path, label: str) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise NpmDistributionError(f"{label} is unavailable") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise NpmDistributionError(f"{label} is not a direct regular file")
    try:
        return path.read_bytes()
    except OSError as error:
        raise NpmDistributionError(f"{label} cannot be read") from error


def _direct_path(value: Path, label: str) -> Path:
    if not value.is_absolute() or value != Path(os.path.normpath(value)):
        raise NpmDistributionError(f"{label} must be an absolute clean path")
    try:
        metadata = value.lstat()
    except OSError as error:
        raise NpmDistributionError(f"{label} is unavailable") from error
    if value.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise NpmDistributionError(f"{label} is not a direct regular file")
    return value


def _directory(path: Path, label: str, *, create: bool = False) -> Path:
    if not path.is_absolute() or path != Path(os.path.normpath(path)):
        raise NpmDistributionError(f"{label} must be an absolute clean path")
    if path.exists() or path.is_symlink():
        try:
            metadata = path.lstat()
        except OSError as error:
            raise NpmDistributionError(f"{label} is unavailable") from error
        if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
            raise NpmDistributionError(f"{label} is not a direct directory")
    elif create:
        try:
            path.mkdir(parents=True, mode=0o700)
        except OSError as error:
            raise NpmDistributionError(f"{label} cannot be created") from error
    else:
        raise NpmDistributionError(f"{label} is unavailable")
    return path


def version_authority(root: Path) -> str:
    raw = _read_direct(
        root / "src" / "agentic_praxis_grimoire" / "VERSION",
        "version authority",
    )
    try:
        value = raw.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise NpmDistributionError("version authority is not ASCII") from error
    if not value or any(character.isspace() for character in value):
        raise NpmDistributionError("version authority is malformed")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_manifest(
    raw: bytes, label: str, *, canonical: bool = True
) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise NpmDistributionError(f"{label} is malformed") from error
    if not isinstance(value, dict):
        raise NpmDistributionError(f"{label} is not a JSON object")
    if canonical and _canonical_json(value) != raw:
        raise NpmDistributionError(f"{label} is not canonical JSON")
    return value


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise NpmDistributionError("package metadata is not JSON serializable") from error


def _manifest_target(manifest: Mapping[str, Any]) -> str | None:
    value = manifest.get("target")
    if not isinstance(value, Mapping):
        return None
    go_target = value.get("go_target")
    goos = value.get("goos")
    goarch = value.get("goarch")
    if (
        isinstance(go_target, str)
        and isinstance(goos, str)
        and isinstance(goarch, str)
    ):
        return go_target
    return None


def _manifest_identity(manifest: Mapping[str, Any], label: str) -> dict[str, Any]:
    expected_keys = {
        "binary_name",
        "build_flags",
        "build_identity",
        "build_info_schema",
        "corpus_fingerprint",
        "module_path",
        "schema_version",
        "sha256",
        "size_bytes",
        "target",
        "version",
    }
    if set(manifest) != expected_keys:
        raise NpmDistributionError(f"{label} fields are not canonical")
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise NpmDistributionError(f"{label} schema is unsupported")
    target_value = manifest.get("target")
    if not isinstance(target_value, Mapping):
        raise NpmDistributionError(f"{label} target mapping is missing")
    version = manifest.get("version")
    target = _manifest_target(manifest)
    corpus = manifest.get("corpus_fingerprint")
    basename = manifest.get("binary_name")
    size = manifest.get("size_bytes")
    digest = manifest.get("sha256")
    if not isinstance(version, str) or not version:
        raise NpmDistributionError(f"{label} version is missing")
    if not isinstance(target, str) or target not in TARGET_BY_GO:
        raise NpmDistributionError(f"{label} target is unsupported")
    expected_target = {
        "go_target": target,
        "goos": TARGET_BY_GO[target].os_name,
        "goarch": "amd64" if TARGET_BY_GO[target].cpu == "x64" else TARGET_BY_GO[target].cpu,
        "python_platform": {
            "darwin/arm64": "macosx_11_0_arm64",
            "linux/amd64": "manylinux_2_17_x86_64",
            "linux/arm64": "manylinux_2_17_aarch64",
        }[target],
        "npm_package": TARGET_BY_GO[target].package_name,
        "npm_os": TARGET_BY_GO[target].os_name,
        "npm_cpu": TARGET_BY_GO[target].cpu,
    }
    if dict(target_value) != expected_target:
        raise NpmDistributionError(f"{label} target mapping is not canonical")
    if manifest.get("module_path") != MODULE_PATH:
        raise NpmDistributionError(f"{label} module identity is wrong")
    if manifest.get("build_info_schema") != BUILD_INFO_SCHEMA:
        raise NpmDistributionError(f"{label} build-info schema is wrong")
    if manifest.get("build_flags") != list(BUILD_FLAGS):
        raise NpmDistributionError(f"{label} build flags are wrong")
    build_identity = manifest.get("build_identity")
    if not isinstance(build_identity, Mapping) or set(build_identity) != {
        "corpus_fingerprint",
        "schema_version",
        "target",
        "version",
    }:
        raise NpmDistributionError(f"{label} build identity is wrong")
    if (
        build_identity.get("corpus_fingerprint") != corpus
        or build_identity.get("schema_version") != BUILD_INFO_SCHEMA
        or build_identity.get("target") != target
        or build_identity.get("version") != version
    ):
        raise NpmDistributionError(f"{label} build identity is inconsistent")
    if not isinstance(corpus, str) or len(corpus) != 64 or any(
        character not in "0123456789abcdef" for character in corpus
    ):
        raise NpmDistributionError(f"{label} corpus fingerprint is invalid")
    if not isinstance(basename, str) or basename != BINARY_BASENAME:
        raise NpmDistributionError(f"{label} basename is not apgr")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise NpmDistributionError(f"{label} size is invalid")
    if not isinstance(digest, str) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise NpmDistributionError(f"{label} SHA-256 is invalid")
    return {
        "schema_version": MANIFEST_SCHEMA,
        "version": version,
        "target": target,
        "corpus_fingerprint": corpus,
        "basename": basename,
        "size_bytes": size,
        "sha256": digest,
        "module_path": MODULE_PATH,
        "build_info_schema": BUILD_INFO_SCHEMA,
        "build_flags": list(BUILD_FLAGS),
        "build_identity": dict(build_identity),
    }


def _artifact_from_value(target: Target, value: Artifact | Mapping[str, Any]) -> Artifact:
    if isinstance(value, Artifact):
        if value.target != target.go_target:
            raise NpmDistributionError("artifact target does not match mapping key")
        return value
    binary_value = value.get("path", value.get("binary", value.get("binary_path")))
    manifest_value = value.get("manifest_path", value.get("manifest"))
    if not isinstance(binary_value, (str, os.PathLike)):
        raise NpmDistributionError(f"{target.go_target} artifact has no binary path")
    binary = Path(binary_value)
    manifest_path: Path | None = None
    manifest_bytes: bytes | None = None
    if isinstance(manifest_value, (bytes, bytearray)):
        manifest_bytes = bytes(manifest_value)
    elif isinstance(manifest_value, Mapping):
        raise NpmDistributionError(
            f"{target.go_target} artifact requires canonical manifest bytes or a manifest path"
        )
    elif isinstance(manifest_value, (str, os.PathLike)):
        manifest_path = Path(manifest_value)
    elif manifest_value is not None:
        raise NpmDistributionError(f"{target.go_target} artifact manifest is invalid")
    return Artifact(target.go_target, binary, manifest_path, manifest_bytes)


def _find_artifact(artifact_root: Path, target: Target) -> Artifact:
    candidates = (
        artifact_root / target.go_target,
        artifact_root / target.slug,
        artifact_root / target.go_target.replace("/", "-"),
        artifact_root / target.go_target.replace("/", "_"),
        artifact_root / f"apgr-{target.slug}",
    )
    for candidate in candidates:
        for binary in (candidate / BINARY_BASENAME, candidate / "bin" / BINARY_BASENAME):
            if not binary.exists() and not binary.is_symlink():
                continue
            for manifest in (
                candidate / "apgr.binary-manifest.json",
                candidate / "binary-manifest.json",
                candidate / "manifest.json",
                candidate / "bin" / "apgr.binary-manifest.json",
                candidate / "bin" / "binary-manifest.json",
            ):
                if manifest.exists() or manifest.is_symlink():
                    return Artifact(target.go_target, binary, manifest)
    raise NpmDistributionError(f"{target.go_target} binary/manifest pair is unavailable")


def _load_artifact(artifact: Artifact) -> tuple[bytes, bytes, dict[str, Any]]:
    binary = _direct_path(artifact.binary, f"{artifact.target} Go binary")
    binary_bytes = _read_direct(binary, f"{artifact.target} Go binary")
    if not (binary.stat().st_mode & 0o111):
        raise NpmDistributionError(f"{artifact.target} Go binary is not executable")
    if artifact.manifest_bytes is not None:
        manifest_bytes = artifact.manifest_bytes
    elif artifact.manifest_path is not None:
        manifest_bytes = _read_direct(artifact.manifest_path, f"{artifact.target} binary manifest")
    else:
        raise NpmDistributionError(f"{artifact.target} binary manifest is unavailable")
    manifest = _parse_manifest(manifest_bytes, f"{artifact.target} binary manifest")
    identity = _manifest_identity(manifest, f"{artifact.target} binary manifest")
    if identity["target"] != artifact.target:
        raise NpmDistributionError(f"{artifact.target} binary manifest target differs")
    if identity["size_bytes"] != len(binary_bytes):
        raise NpmDistributionError(f"{artifact.target} binary size differs from manifest")
    digest = hashlib.sha256(binary_bytes).hexdigest()
    if identity["sha256"] != digest:
        raise NpmDistributionError(f"{artifact.target} binary SHA-256 differs from manifest")
    return binary_bytes, manifest_bytes, identity


def _load_templates(root: Path) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    templates = root / "npm" / "templates"
    try:
        launcher = _parse_manifest(
            _read_direct(templates / LAUNCHER_TEMPLATE, "launcher package template"),
            "launcher package template",
            canonical=False,
        )
        platform = _parse_manifest(
            _read_direct(templates / PLATFORM_TEMPLATE, "platform package template"),
            "platform package template",
            canonical=False,
        )
        launcher_source = _read_direct(
            templates / LAUNCHER_SOURCE, "launcher source template"
        )
    except NpmDistributionError:
        raise
    if launcher.get("version") != "__APG_VERSION__" or platform.get("version") != "__APG_VERSION__":
        raise NpmDistributionError("npm package template has an unexpected version authority")
    return launcher, platform, launcher_source


def _package_json(
    template: Mapping[str, Any],
    *,
    name: str,
    version: str,
    target: Target | None,
    corpus: str,
    build_identity: Any = None,
) -> bytes:
    package = json.loads(json.dumps(template))
    package["name"] = name
    package["version"] = version
    package.setdefault("engines", {})["node"] = NODE_ENGINE
    if target is None:
        package["optionalDependencies"] = {
            value.package_name: version for value in TARGETS
        }
        package["apg"] = {
            "binary_manifest_schema": MANIFEST_SCHEMA,
            "corpus_fingerprint": corpus,
            "supported_targets": [value.go_target for value in TARGETS],
        }
    else:
        package["description"] = f"The Agentic Praxis Grimoire native executable for {target.go_target}."
        package["os"] = [target.os_name]
        package["cpu"] = [target.cpu]
        package["apg"] = {
            "binary_manifest_schema": MANIFEST_SCHEMA,
            "target": target.go_target,
            "corpus_fingerprint": corpus,
            "binary_basename": BINARY_BASENAME,
            "manifest_file": "bin/apgr.binary-manifest.json",
            "build_identity": build_identity,
        }
    if package.get("version") == "__APG_VERSION__" or "__APG_" in json.dumps(package):
        raise NpmDistributionError("npm package template placeholders were not rendered")
    return _canonical_json(package)


def _write_file(path: Path, content: bytes, mode: int) -> None:
    if path.exists() or path.is_symlink():
        raise NpmDistributionError(f"refusing to overwrite package member: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(content)
    path.chmod(mode)


def _package_files(
    root: Path,
    *,
    package_json: bytes,
    launcher_source: bytes | None,
    binary: bytes | None,
    manifest: bytes | None,
    source_root: Path,
) -> Path:
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    _write_file(root / "package.json", package_json, 0o644)
    if launcher_source is not None:
        _write_file(root / "index.js", launcher_source, 0o755)
    if binary is not None:
        _write_file(root / "bin" / BINARY_BASENAME, binary, 0o755)
    if manifest is not None:
        _write_file(root / "bin" / "apgr.binary-manifest.json", manifest, 0o644)
    for name in LICENSE_FILES:
        _write_file(root / name, _read_direct(source_root / name, name), 0o644)
    return root


def _safe_member_name(name: str) -> PurePosixPath:
    if not name or name.startswith("/") or "\\" in name:
        raise NpmDistributionError(f"unsafe archive member: {name!r}")
    path = PurePosixPath(name)
    if any(part in ("", ".", "..") for part in path.parts):
        raise NpmDistributionError(f"unsafe archive member: {name!r}")
    if path.parts[0] != "package":
        raise NpmDistributionError(f"archive member is outside package/: {name!r}")
    return path


def _pack_directory(package_root: Path, output: Path) -> None:
    files: list[Path] = []
    for candidate in sorted(package_root.rglob("*")):
        metadata = candidate.lstat()
        if candidate.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            if candidate.is_dir() and not candidate.is_symlink():
                continue
            raise NpmDistributionError(f"package contains unsafe member: {candidate.name}")
        files.append(candidate)
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", filename="", mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for candidate in files:
                relative = candidate.relative_to(package_root).as_posix()
                member = _safe_member_name(f"package/{relative}")
                raw = candidate.read_bytes()
                info = tarfile.TarInfo(member.as_posix())
                info.size = len(raw)
                info.mode = 0o755 if candidate.name == "index.js" or candidate.name == BINARY_BASENAME else 0o644
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.type = tarfile.REGTYPE
                info.pax_headers = {}
                archive.addfile(info, BytesIO(raw))
    data = payload.getvalue()
    output.write_bytes(data)
    output.chmod(0o600)


def npm_tarball_name(package_name: str, version: str) -> str:
    try:
        return candidate_contract.npm_tarball_filename(package_name, version)
    except candidate_contract.DistributionCandidateError as error:
        raise NpmDistributionError(str(error)) from error




def _ensure_empty_output(path: Path) -> Path:
    path = _directory(path, "npm output directory", create=True)
    try:
        next(path.iterdir())
    except StopIteration:
        return path
    raise NpmDistributionError("npm output directory must be empty")


def build_packages(
    source_root: Path,
    artifact_root: Path | None,
    output: Path,
    *,
    artifacts: Mapping[str, Artifact | Mapping[str, Any]] | None = None,
    work_root: Path | None = None,
) -> tuple[PackageRecord, ...]:
    """Render and pack all four npm packages from prebuilt Go artifacts."""

    source_root = source_root.resolve(strict=True)
    version = version_authority(source_root)
    if artifacts is None:
        if artifact_root is None:
            raise NpmDistributionError("an artifact root is required")
        artifact_root = _directory(artifact_root, "Go artifact root")
        artifact_map = {
            target.go_target: _find_artifact(artifact_root, target) for target in TARGETS
        }
    else:
        artifact_map = {}
        for target in TARGETS:
            value = artifacts.get(target.go_target)
            if value is None:
                raise NpmDistributionError(f"missing {target.go_target} artifact")
            artifact_map[target.go_target] = _artifact_from_value(target, value)
    loaded = {target.go_target: _load_artifact(artifact_map[target.go_target]) for target in TARGETS}
    corpus_values = {value[2]["corpus_fingerprint"] for value in loaded.values()}
    version_values = {value[2]["version"] for value in loaded.values()}
    if version_values != {version}:
        raise NpmDistributionError("binary manifest version does not match VERSION")
    if len(corpus_values) != 1:
        raise NpmDistributionError("target binary manifests disagree on corpus fingerprint")
    corpus = next(iter(corpus_values))
    launcher_template, platform_template, launcher_source = _load_templates(source_root)
    output = _ensure_empty_output(output)
    work = _directory(work_root or output.parent, "npm work directory", create=True)
    staged: list[tuple[Path, str, str | None]] = []
    with tempfile.TemporaryDirectory(prefix="apgr-npm-", dir=work) as temporary:
        staging = Path(temporary)
        launcher_dir = _package_files(
            staging / "launcher",
            package_json=_package_json(
                launcher_template,
                name=LAUNCHER_NAME,
                version=version,
                target=None,
                corpus=corpus,
            ),
            launcher_source=launcher_source,
            binary=None,
            manifest=None,
            source_root=source_root,
        )
        launcher_tgz = staging / npm_tarball_name(LAUNCHER_NAME, version)
        _pack_directory(launcher_dir, launcher_tgz)
        staged.append((launcher_tgz, LAUNCHER_NAME, None))
        for target in TARGETS:
            binary, manifest_bytes, identity = loaded[target.go_target]
            package_dir = _package_files(
                staging / target.slug,
                package_json=_package_json(
                    platform_template,
                    name=target.package_name,
                    version=version,
                    target=target,
                    corpus=corpus,
                    build_identity=identity["build_identity"],
                ),
                launcher_source=None,
                binary=binary,
                manifest=manifest_bytes,
                source_root=source_root,
            )
            tgz = staging / npm_tarball_name(target.package_name, version)
            _pack_directory(package_dir, tgz)
            staged.append((tgz, target.package_name, target.go_target))
        records: list[PackageRecord] = []
        for tgz, name, target in staged:
            destination = output / tgz.name
            if destination.exists() or destination.is_symlink():
                raise NpmDistributionError(f"refusing to overwrite npm artifact: {destination.name}")
            shutil.copyfile(tgz, destination)
            destination.chmod(0o600)
            data = destination.read_bytes()
            records.append(
                PackageRecord(name, version, target, destination.name, hashlib.sha256(data).hexdigest(), len(data))
            )
    check_packages(output, version=version)
    return tuple(records)


def _archive_members(path: Path) -> tuple[dict[str, tarfile.TarInfo], dict[str, bytes]]:
    raw = _read_direct(path, "npm tarball")
    members: dict[str, tarfile.TarInfo] = {}
    contents: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=BytesIO(raw), mode="r:gz") as archive:
            for info in archive:
                _safe_member_name(info.name)
                if info.name in members:
                    raise NpmDistributionError(f"duplicate archive member: {info.name}")
                if not info.isreg() or info.issym() or info.islnk() or info.mode & 0o002:
                    raise NpmDistributionError(f"unsafe archive member: {info.name}")
                extracted = archive.extractfile(info)
                if extracted is None:
                    raise NpmDistributionError(f"archive member cannot be read: {info.name}")
                members[info.name] = info
                contents[info.name] = extracted.read()
    except (OSError, tarfile.TarError) as error:
        raise NpmDistributionError("npm tarball is malformed") from error
    return members, contents


def _archive_package_json(contents: Mapping[str, bytes], path: Path) -> dict[str, Any]:
    try:
        package = _parse_manifest(contents["package/package.json"], f"{path.name} package.json")
    except KeyError as error:
        raise NpmDistributionError(f"{path.name} has no package.json") from error
    return package


def validate_tarball(path: Path, *, version: str | None = None) -> PackageRecord:
    members, contents = _archive_members(path)
    package = _archive_package_json(contents, path)
    name = package.get("name")
    package_version = package.get("version")
    if not isinstance(name, str) or not isinstance(package_version, str):
        raise NpmDistributionError(f"{path.name} package identity is malformed")
    if version is not None and package_version != version:
        raise NpmDistributionError(f"{path.name} package version differs")
    expected = {"package/package.json", "package/LICENSE", "package/NOTICE", "package/COMMERCIAL-LICENSE.md"}
    target: str | None = None
    if name == LAUNCHER_NAME:
        expected.add("package/index.js")
        if package.get("engines") != {"node": NODE_ENGINE}:
            raise NpmDistributionError("launcher Node engine contract is not exact")
        contract = package.get("apg")
        if not isinstance(contract, Mapping):
            raise NpmDistributionError("launcher package identity is malformed")
        corpus = contract.get("corpus_fingerprint")
        if not isinstance(corpus, str) or len(corpus) != 64 or any(
            character not in "0123456789abcdef" for character in corpus
        ):
            raise NpmDistributionError("launcher package corpus fingerprint is invalid")
        expected_contract = {
            "binary_manifest_schema": MANIFEST_SCHEMA,
            "corpus_fingerprint": corpus,
            "supported_targets": [value.go_target for value in TARGETS],
        }
        if contract != expected_contract:
            raise NpmDistributionError("launcher package identity is not exact")
        if "dependencies" in package:
            raise NpmDistributionError("launcher must not have runtime dependencies")
        optional = package.get("optionalDependencies")
        expected_optional = {value.package_name: package_version for value in TARGETS}
        if optional != expected_optional:
            raise NpmDistributionError("launcher optional platform dependencies are not exact")
        if "scripts" in package:
            raise NpmDistributionError("launcher must not have install scripts")
    else:
        targets = [value for value in TARGETS if value.package_name == name]
        if len(targets) != 1:
            raise NpmDistributionError(f"unsupported npm package name: {name}")
        selected = targets[0]
        target = selected.go_target
        expected.update({"package/bin/apgr", "package/bin/apgr.binary-manifest.json"})
        if package.get("engines") != {"node": NODE_ENGINE}:
            raise NpmDistributionError(f"{path.name} Node engine contract is not exact")
        if package.get("os") != [selected.os_name] or package.get("cpu") != [selected.cpu]:
            raise NpmDistributionError(f"{path.name} target restrictions are not exact")
        if "scripts" in package or "dependencies" in package:
            raise NpmDistributionError(f"{path.name} has forbidden runtime dependencies/scripts")
        manifest = _parse_manifest(contents["package/bin/apgr.binary-manifest.json"], path.name)
        identity = _manifest_identity(manifest, path.name)
        expected_contract = {
            "binary_manifest_schema": MANIFEST_SCHEMA,
            "target": target,
            "corpus_fingerprint": identity["corpus_fingerprint"],
            "binary_basename": BINARY_BASENAME,
            "manifest_file": "bin/apgr.binary-manifest.json",
            "build_identity": identity["build_identity"],
        }
        if package.get("apg") != expected_contract:
            raise NpmDistributionError(f"{path.name} package identity is not exact")
        binary = contents["package/bin/apgr"]
        if len(binary) != identity["size_bytes"] or hashlib.sha256(binary).hexdigest() != identity["sha256"]:
            raise NpmDistributionError(f"{path.name} binary does not match manifest")
        if not members["package/bin/apgr"].mode & 0o111:
            raise NpmDistributionError(f"{path.name} binary is not executable")
        if identity["target"] != target or identity["version"] != package_version:
            raise NpmDistributionError(f"{path.name} binary identity does not match package")
    if set(contents) != expected:
        raise NpmDistributionError(f"{path.name} contains unexpected package members")
    for member in expected:
        if member not in members:
            raise NpmDistributionError(f"{path.name} is missing {member}")
    data = path.read_bytes()
    return PackageRecord(name, package_version, target, path.name, hashlib.sha256(data).hexdigest(), len(data))


def check_packages(bundle: Path, *, version: str | None = None) -> tuple[PackageRecord, ...]:
    bundle = _directory(bundle, "npm bundle")
    paths = sorted(bundle.glob("*.tgz"))
    if len(paths) != 4:
        raise NpmDistributionError("npm bundle must contain exactly four tarballs")
    records = tuple(validate_tarball(path, version=version) for path in paths)
    names = {record.name for record in records}
    expected = {LAUNCHER_NAME, *(target.package_name for target in TARGETS)}
    if names != expected:
        raise NpmDistributionError("npm bundle package set is incomplete")
    if version is not None and {record.version for record in records} != {version}:
        raise NpmDistributionError("npm bundle versions are inconsistent")
    return records


def publication_order() -> tuple[str, ...]:
    """Return the exact publication order for npm packages."""
    return PUBLICATION_ORDER


def package_tarball_mapping(version: str) -> dict[str, str]:
    """Map each npm package name to its authoritative tarball filename."""
    return {
        name: npm_tarball_name(name, version)
        for name in PUBLICATION_ORDER
    }


def preflight_publication_tarballs(
    bundle_dir: Path, version: str, *, manifest: Mapping[str, Any] | None = None
) -> tuple[PackageRecord, ...]:
    """Preflight and validate the four publication tarballs against candidate contract and manifest."""
    bundle = _directory(bundle_dir, "npm bundle")
    expected_names = package_tarball_mapping(version)
    records_by_name: dict[str, PackageRecord] = {}
    for pkg_name in PUBLICATION_ORDER:
        expected_filename = expected_names[pkg_name]
        tarball_path = bundle / expected_filename
        if not tarball_path.is_file():
            raise NpmDistributionError(f"missing npm tarball for {pkg_name}: {expected_filename}")
        record = validate_tarball(tarball_path, version=version)
        if record.name != pkg_name:
            raise NpmDistributionError(f"tarball {expected_filename} has unexpected package name {record.name}")
        records_by_name[pkg_name] = record

    if manifest is not None:
        npm_manifest = manifest.get("npm", {})
        manifest_packages: dict[str, Mapping[str, Any]] = {}
        launcher = npm_manifest.get("launcher", {})
        if launcher:
            manifest_packages[launcher.get("name", "")] = launcher
        for platform_pkg in npm_manifest.get("platform_packages", []):
            manifest_packages[platform_pkg.get("name", "")] = platform_pkg

        for pkg_name in PUBLICATION_ORDER:
            if pkg_name not in manifest_packages:
                raise NpmDistributionError(f"distribution manifest missing npm package {pkg_name}")
            manifest_entry = manifest_packages[pkg_name]
            record = records_by_name[pkg_name]
            if manifest_entry.get("sha256") != record.sha256:
                raise NpmDistributionError(
                    f"tarball {record.filename} SHA-256 {record.sha256} disagrees with distribution manifest {manifest_entry.get('sha256')}"
                )
            if manifest_entry.get("size_bytes") != record.size_bytes:
                raise NpmDistributionError(
                    f"tarball {record.filename} size {record.size_bytes} disagrees with distribution manifest {manifest_entry.get('size_bytes')}"
                )

    return tuple(records_by_name[name] for name in PUBLICATION_ORDER)


def classify_registry_state(
    package_name: str,
    version: str,
    local_sha256: str,
    registry_info: Mapping[str, Any] | None,
) -> str:
    """Classify the npm registry state for one package version."""
    if registry_info is None or not registry_info:
        return "absent_safe_to_publish"
    reg_version = registry_info.get("version")
    version_data = registry_info
    if reg_version is None or reg_version != version:
        versions = registry_info.get("versions", {})
        if isinstance(versions, Mapping) and version in versions:
            version_data = versions[version]
        else:
            return "absent_safe_to_publish"

    dist = version_data.get("dist", {})
    reg_sha256 = dist.get("sha256") or version_data.get("sha256") or dist.get("tarball_sha256")
    if reg_sha256 and reg_sha256 == local_sha256:
        return "already_exact_no_op"
    reg_integrity = dist.get("integrity")
    if reg_integrity and reg_integrity.startswith("sha256-"):
        raw_b64 = reg_integrity[len("sha256-"):]
        try:
            import base64
            if base64.b64decode(raw_b64).hex() == local_sha256:
                return "already_exact_no_op"
        except Exception:
            pass
    if version_data.get("version") == version:
        return "mismatched_drift_stop"
    return "absent_safe_to_publish"


def evaluate_publication_plan(
    records: Sequence[PackageRecord | Mapping[str, Any]],
    registry_states: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any]:
    """Evaluate the npm publication plan across all packages in authoritative order."""
    record_map: dict[str, Any] = {}
    for rec in records:
        name = rec.name if isinstance(rec, PackageRecord) else rec["name"]
        record_map[name] = rec

    plan_packages = []
    states = []
    for pkg_name in PUBLICATION_ORDER:
        if pkg_name not in record_map:
            raise NpmDistributionError(f"publication record missing for {pkg_name}")
        rec = record_map[pkg_name]
        version = rec.version if isinstance(rec, PackageRecord) else rec["version"]
        sha256 = rec.sha256 if isinstance(rec, PackageRecord) else rec["sha256"]
        reg_info = registry_states.get(pkg_name)
        state = classify_registry_state(pkg_name, version, sha256, reg_info)
        states.append(state)
        plan_packages.append({
            "package": pkg_name,
            "version": version,
            "sha256": sha256,
            "state": state,
        })

    if all(s == "absent_safe_to_publish" for s in states):
        plan_action = "ready_for_first_publication_bootstrap"
    elif all(s == "already_exact_no_op" for s in states):
        plan_action = "already_published_exact"
    else:
        plan_action = "stop_partial_or_mismatched"

    return {
        "action": plan_action,
        "publication_order": list(PUBLICATION_ORDER),
        "packages": plan_packages,
    }


def verify_live_readback(
    package_name: str,
    version: str,
    local_sha256: str,
    registry_view: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify live readback from npm view response after publication."""
    if not registry_view or not isinstance(registry_view, Mapping):
        raise NpmDistributionError(f"live readback failed for {package_name}: empty response")
    observed_name = registry_view.get("name")
    if observed_name != package_name:
        raise NpmDistributionError(f"live readback name mismatch: expected {package_name}, got {observed_name}")
    observed_version = registry_view.get("version")
    if observed_version != version:
        raise NpmDistributionError(f"live readback version mismatch for {package_name}: expected {version}, got {observed_version}")
    dist = registry_view.get("dist")
    if not isinstance(dist, Mapping) or not dist.get("tarball"):
        raise NpmDistributionError(f"live readback missing distribution metadata for {package_name}")
    reg_sha256 = dist.get("sha256") or registry_view.get("sha256") or dist.get("tarball_sha256")
    if reg_sha256 and reg_sha256 != local_sha256:
        raise NpmDistributionError(f"live readback SHA-256 mismatch for {package_name}: expected {local_sha256}, got {reg_sha256}")
    return {
        "name": observed_name,
        "version": observed_version,
        "tarball": dist.get("tarball"),
        "verified": True,
    }


FORBIDDEN_CREDENTIAL_PATTERNS = (
    "_authtoken",
    "node_auth_token",
    "npm_token",
    "npm_auth_token",
    "//registry.npmjs.org/:_authtoken",
)


def verify_credential_safety(
    command_args: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Verify that command arguments and environment do not leak credentials or use persistent token fallback."""
    if command_args:
        for arg in command_args:
            lower = arg.lower()
            for pattern in FORBIDDEN_CREDENTIAL_PATTERNS:
                if pattern in lower:
                    raise NpmDistributionError(f"credential safety violation in arguments: contains {pattern}")
    if environment:
        for key, value in environment.items():
            key_lower = key.lower()
            for pattern in ("node_auth_token", "npm_token", "npm_auth_token"):
                if pattern in key_lower and value:
                    raise NpmDistributionError(f"credential safety violation in environment: {key} is set")



def _json_records(records: tuple[PackageRecord, ...]) -> str:
    return json.dumps([asdict(record) for record in records], sort_keys=True, separators=(",", ":"))


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="apg-build-npm-distribution")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--source", type=Path, required=True)
    build.add_argument("--artifact-root", "--artifacts", dest="artifact_root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--work-root", type=Path)
    check = commands.add_parser("check")
    check.add_argument("--bundle", type=Path, required=True)
    try:
        if arguments is None:
            arguments = sys.argv[1:]
        parsed = parser.parse_args(arguments)
        if parsed.command == "build":
            records = build_packages(parsed.source, parsed.artifact_root, parsed.output, work_root=parsed.work_root)
        else:
            records = check_packages(parsed.bundle)
        print(_json_records(records))
        return 0
    except NpmDistributionError as error:
        print(f"apg-build-npm-distribution: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

