"""Shared contract and source-independent helpers for distribution candidates.

This module owns the public target matrix, canonical JSON rules, source
identity, and validation of the prebuilt Go binary/manifest pairs.  It has no
package-manager or compiler dependencies; archive-specific validation lives in
``apg_distribution_candidate_archives``.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Any, Mapping


MANIFEST_SCHEMA = "apg.distribution-manifest/v1"
DISTRIBUTION_MANIFEST_SCHEMA = MANIFEST_SCHEMA
SOURCE_CANDIDATE_SCHEMA = "apg.source-candidate/v1"
BINARY_MANIFEST_SCHEMA = "apg.binary-manifest/v1"
BUILD_INFO_SCHEMA = "apg.build-info/v1"
MODULE = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
BINARY_NAME = "apgr"
DIST_NAME = "agentic_praxis_grimoire"
PYTHON_PACKAGE = "agentic-praxis-grimoire"
MANIFEST_NAME = "apg-distribution-manifest.json"
CHECKSUM_NAME = "SHA256SUMS"
LICENSE_FILES = ("LICENSE", "NOTICE", "COMMERCIAL-LICENSE.md")
BUILD_FLAGS = ("CGO_ENABLED=0", "-trimpath", "-buildvcs=false", "-buildid=")


# These are distribution mappings, not version authorities.  The editable
# VERSION resource is read from the explicit source root by _source_identity.
TARGETS: tuple[dict[str, str], ...] = (
    {
        "go_target": "darwin/arm64",
        "goos": "darwin",
        "goarch": "arm64",
        "python_platform": "macosx_11_0_arm64",
        "npm_package": "@knowledge-forge-ai/apgr-darwin-arm64",
        "npm_os": "darwin",
        "npm_cpu": "arm64",
    },
    {
        "go_target": "linux/amd64",
        "goos": "linux",
        "goarch": "amd64",
        "python_platform": "manylinux_2_17_x86_64",
        "npm_package": "@knowledge-forge-ai/apgr-linux-x64",
        "npm_os": "linux",
        "npm_cpu": "x64",
    },
    {
        "go_target": "linux/arm64",
        "goos": "linux",
        "goarch": "arm64",
        "python_platform": "manylinux_2_17_aarch64",
        "npm_package": "@knowledge-forge-ai/apgr-linux-arm64",
        "npm_os": "linux",
        "npm_cpu": "arm64",
    },
)
TARGET_BY_GO = {value["go_target"]: value for value in TARGETS}
TARGET_BY_SLUG = {
    value["go_target"].replace("/", "-"): value for value in TARGETS
}
SUPPORTED_TARGETS = tuple(TARGET_BY_GO)
NPM_LAUNCHER_PACKAGE = "@knowledge-forge-ai/apgr"
NPM_PLATFORM_PACKAGES = tuple(mapping["npm_package"] for mapping in TARGETS)
NPM_PACKAGES = (*NPM_PLATFORM_PACKAGES, NPM_LAUNCHER_PACKAGE)

ROLE_MANIFEST = "distribution-manifest"
ROLE_CHECKSUMS = "checksums"
ROLE_PYTHON_WHEEL = "python-wheel"
ROLE_PYTHON_SDIST = "python-sdist"
ROLE_NPM_PLATFORM = "npm-platform-package"
ROLE_NPM_LAUNCHER = "npm-launcher-package"


class DistributionCandidateError(ValueError):
    """The local distribution candidate does not satisfy its contract."""


def npm_tarball_filename(package_name: str, version: str) -> str:
    """Derive the canonical npm tarball archive name."""
    if not package_name.startswith("@") or "/" not in package_name:
        raise DistributionCandidateError("npm package name is not scoped")
    scope, name = package_name[1:].split("/", 1)
    return f"{scope}-{name}-{version}.tgz"



def python_wheel_filename(target: str, version: str) -> str:
    """Derive the canonical platform Python wheel name."""
    if target not in TARGET_BY_GO:
        raise DistributionCandidateError(f"unsupported target: {target}")
    platform_tag = TARGET_BY_GO[target]["python_platform"]
    return f"{DIST_NAME}-{version}-py3-none-{platform_tag}.whl"


def python_sdist_filename(version: str) -> str:
    """Derive the canonical source distribution archive name."""
    return f"{DIST_NAME}-{version}.tar.gz"


def python_release_asset_names(version: str) -> tuple[str, ...]:
    """Return the ordered list of Python release distribution artifact filenames."""
    wheels = tuple(python_wheel_filename(target, version) for target in TARGET_BY_GO)
    return (*wheels, python_sdist_filename(version))


def npm_release_asset_names(version: str) -> tuple[str, ...]:
    """Return the ordered list of npm package tarball filenames."""
    platforms = tuple(npm_tarball_filename(mapping["npm_package"], version) for mapping in TARGETS)
    return (*platforms, npm_tarball_filename(NPM_LAUNCHER_PACKAGE, version))


def npm_publication_order(version: str | None = None) -> tuple[str, ...]:
    """Return the exact publication order for npm packages: platform packages first, launcher last."""
    return (*NPM_PLATFORM_PACKAGES, NPM_LAUNCHER_PACKAGE)


def release_asset_inventory(version: str) -> dict[str, dict[str, Any]]:
    """Return one authoritative machine-readable inventory of all GitHub Release assets and roles."""
    inventory: dict[str, dict[str, Any]] = {
        MANIFEST_NAME: {
            "name": MANIFEST_NAME,
            "role": ROLE_MANIFEST,
            "ecosystem": "manifest",
            "required": True,
        },
        CHECKSUM_NAME: {
            "name": CHECKSUM_NAME,
            "role": ROLE_CHECKSUMS,
            "ecosystem": "checksums",
            "required": True,
        },
    }
    for mapping in TARGETS:
        target = mapping["go_target"]
        wheel_name = python_wheel_filename(target, version)
        inventory[wheel_name] = {
            "name": wheel_name,
            "role": ROLE_PYTHON_WHEEL,
            "ecosystem": "python",
            "target": target,
            "python_platform": mapping["python_platform"],
            "package": PYTHON_PACKAGE,
            "required": True,
        }
    sdist_name = python_sdist_filename(version)
    inventory[sdist_name] = {
        "name": sdist_name,
        "role": ROLE_PYTHON_SDIST,
        "ecosystem": "python",
        "package": PYTHON_PACKAGE,
        "required": True,
    }
    for mapping in TARGETS:
        pkg_name = mapping["npm_package"]
        tgz_name = npm_tarball_filename(pkg_name, version)
        inventory[tgz_name] = {
            "name": tgz_name,
            "role": ROLE_NPM_PLATFORM,
            "ecosystem": "npm",
            "target": mapping["go_target"],
            "package": pkg_name,
            "required": True,
        }
    launcher_tgz = npm_tarball_filename(NPM_LAUNCHER_PACKAGE, version)
    inventory[launcher_tgz] = {
        "name": launcher_tgz,
        "role": ROLE_NPM_LAUNCHER,
        "ecosystem": "npm",
        "package": NPM_LAUNCHER_PACKAGE,
        "required": True,
    }
    return inventory


def classify_release_asset(filename: str, version: str) -> dict[str, Any] | None:
    """Classify a release asset filename into its canonical metadata and role."""
    inventory = release_asset_inventory(version)
    return inventory.get(filename)


class CandidateError(DistributionCandidateError):
    """Compatibility alias used by callers of the candidate helper."""


DistributionError = DistributionCandidateError


def _fail(message: str) -> None:
    raise DistributionCandidateError(message)


def _absolute_clean(value: Path | str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or path != Path(os.path.normpath(path)):
        _fail(f"{label} must be an absolute clean path")
    return path


def _directory(value: Path | str, label: str) -> Path:
    path = _absolute_clean(value, label)
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise DistributionCandidateError(f"{label} is unavailable") from error
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode) or resolved != path.absolute():
        _fail(f"{label} must be one direct real directory")
    return path


def _read_direct(value: Path | str, label: str) -> bytes:
    path = _absolute_clean(value, label)
    try:
        metadata = path.lstat()
    except OSError as error:
        raise DistributionCandidateError(f"{label} is unavailable") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        _fail(f"{label} must be a direct regular file")
    try:
        return path.read_bytes()
    except OSError as error:
        raise DistributionCandidateError(f"{label} cannot be read") from error


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path, label: str) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as error:
        raise DistributionCandidateError(f"{label} cannot be read") from error
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise DistributionCandidateError(f"{label} is malformed") from error
    if not isinstance(value, dict):
        _fail(f"{label} must be a JSON object")
    return value


def canonical_json(value: Mapping[str, Any]) -> bytes:
    """Render one compact, sorted JSON object with exactly one newline."""

    try:
        return (
            json.dumps(dict(value), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError) as error:
        raise DistributionCandidateError("manifest value is not canonical JSON") from error


def render_manifest(value: Mapping[str, Any]) -> bytes:
    """Compatibility name matching the lower-level artifact builders."""

    return canonical_json(value)


def _canonical_value(raw: bytes, label: str) -> dict[str, Any]:
    value = _parse_json(raw, label)
    if canonical_json(value) != raw:
        _fail(f"{label} is not canonical JSON")
    return value


def source_candidate_identity(
    version: str,
    corpus: str,
    *,
    sdist_sha256: str | None = None,
    npm_launcher_sha256: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic identity for the public release inputs.

    The identity intentionally contains only public semantic inputs and
    release-shaped source archive bytes.  It is not a Git revision, local
    path, timestamp, or claim about a private tree.  Its fingerprint is the
    SHA-256 of the canonical descriptor without the fingerprint member itself.

    The archive digests are optional for compatibility with callers that used
    the original two-argument helper.  The distribution manifest always
    supplies both values, so its identity is bound to source bytes rather
    than only to version and corpus metadata.
    """

    descriptor: dict[str, Any] = {
        "schema_version": SOURCE_CANDIDATE_SCHEMA,
        "version": version,
        "corpus_fingerprint": corpus,
        "module_path": MODULE,
        "binary_manifest_schema": BINARY_MANIFEST_SCHEMA,
        "build_info_schema": BUILD_INFO_SCHEMA,
        "target_matrix": [dict(mapping) for mapping in TARGETS],
        "source_artifacts": {
            "sdist_sha256": sdist_sha256 or "",
            "npm_launcher_sha256": npm_launcher_sha256 or "",
        },
    }
    return {**descriptor, "fingerprint": _sha256(canonical_json(descriptor))}


def _source_identity(source_root: Path | str) -> tuple[str, str]:
    root = _directory(source_root, "source root")
    version_raw = _read_direct(
        root / "src" / "agentic_praxis_grimoire" / "VERSION",
        "VERSION authority",
    )
    try:
        version = version_raw.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise DistributionCandidateError("VERSION authority is not ASCII") from error
    if not version or any(character.isspace() for character in version):
        _fail("VERSION authority is malformed")
    corpus = _sha256_file(
        root / "src" / "agentic_praxis_grimoire" / "resources" / "skill-metadata.json",
        "skill corpus authority",
    )
    return version, corpus


def _target_slug(target: str) -> str:
    try:
        return TARGET_BY_GO[target]["go_target"].replace("/", "-")
    except KeyError as error:
        raise DistributionCandidateError(f"unsupported target: {target}") from error


def _safe_member_name(name: str, label: str) -> str:
    first = name.split("/", 1)[0] if name else ""
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or "\x00" in name
        or (len(first) >= 2 and first[0].isalpha() and first[1] == ":")
        or any(part in {"", ".", ".."} for part in name.split("/"))
    ):
        _fail(f"{label} contains an unsafe member path")
    return PurePosixPath(name).as_posix()


def _manifest_target(value: Any, label: str) -> str:
    if isinstance(value, str):
        target = value
    elif isinstance(value, Mapping):
        target_value = value.get("go_target")
        if isinstance(target_value, str):
            target = target_value
        else:
            goos = value.get("goos")
            goarch = value.get("goarch")
            target = f"{goos}/{goarch}" if isinstance(goos, str) and isinstance(goarch, str) else ""
    else:
        target = ""
    if target not in TARGET_BY_GO:
        _fail(f"{label} target is unsupported")
    return target


def _binary_manifest_identity(
    raw: bytes,
    *,
    label: str,
    target: str,
    version: str,
    corpus: str,
    binary: bytes,
) -> dict[str, Any]:
    value = _canonical_value(raw, label)
    if value.get("schema_version") != BINARY_MANIFEST_SCHEMA:
        _fail(f"{label} schema is unsupported")
    if value.get("version") != version:
        _fail(f"{label} version does not match VERSION")
    raw_target = value.get("target")
    if _manifest_target(raw_target, label) != target:
        _fail(f"{label} target does not match its artifact")
    if isinstance(raw_target, Mapping) and dict(raw_target) != dict(TARGET_BY_GO[target]):
        _fail(f"{label} target mapping is not canonical")
    if value.get("binary_name") != BINARY_NAME:
        _fail(f"{label} binary name is not apgr")
    if value.get("corpus_fingerprint") != corpus:
        _fail(f"{label} corpus fingerprint does not match VERSION authority")
    if value.get("module_path") != MODULE:
        _fail(f"{label} module path does not match APGR")
    if value.get("build_info_schema") != BUILD_INFO_SCHEMA:
        _fail(f"{label} build-info schema is unsupported")
    if value.get("build_flags") != list(BUILD_FLAGS):
        _fail(f"{label} build flags are not canonical")
    build_identity = value.get("build_identity")
    expected_identity = {
        "corpus_fingerprint": corpus,
        "schema_version": BUILD_INFO_SCHEMA,
        "target": target,
        "version": version,
    }
    if build_identity != expected_identity:
        _fail(f"{label} build identity is not exact")
    size = value.get("size_bytes")
    digest = value.get("sha256")
    observed_digest = _sha256(binary)
    if not isinstance(size, int) or isinstance(size, bool) or size != len(binary):
        _fail(f"{label} binary size does not match its member")
    if digest != observed_digest:
        _fail(f"{label} binary SHA-256 does not match its member")
    return {
        "schema_version": BINARY_MANIFEST_SCHEMA,
        "version": version,
        "target": target,
        "corpus_fingerprint": corpus,
        "module_path": MODULE,
        "build_info_schema": BUILD_INFO_SCHEMA,
        "build_flags": list(BUILD_FLAGS),
        "binary_name": BINARY_NAME,
        "size_bytes": len(binary),
        "sha256": observed_digest,
    }


def _find_go_pair(root: Path, target: str) -> tuple[Path, Path]:
    slug = _target_slug(target)
    candidates = (
        root / slug,
        root / target,
        root / f"apgr-{slug}",
        root / target.replace("/", "_"),
    )
    for candidate in candidates:
        binary_candidates = (candidate / BINARY_NAME, candidate / "bin" / BINARY_NAME)
        manifest_candidates = (
            candidate / f"{BINARY_NAME}.binary-manifest.json",
            candidate / "binary-manifest.json",
            candidate / "manifest.json",
            candidate / "bin" / f"{BINARY_NAME}.binary-manifest.json",
        )
        for binary in binary_candidates:
            for manifest in manifest_candidates:
                if (binary.exists() or binary.is_symlink()) and (
                    manifest.exists() or manifest.is_symlink()
                ):
                    return binary, manifest
    _fail(f"{target} Go binary/manifest pair is unavailable")


def _load_go_artifacts(
    artifact_root: Path | str, *, version: str, corpus: str
) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    root = _directory(artifact_root, "Go artifact root")
    records: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    for target in TARGET_BY_GO:
        binary_path, manifest_path = _find_go_pair(root, target)
        if binary_path.name != BINARY_NAME or manifest_path.name != f"{BINARY_NAME}.binary-manifest.json":
            _fail(f"{target} Go artifact names are not canonical")
        binary = _read_direct(binary_path, f"{target} Go binary")
        try:
            mode = binary_path.stat().st_mode
        except OSError as error:
            raise DistributionCandidateError(f"{target} Go binary cannot be inspected") from error
        if not mode & 0o111:
            _fail(f"{target} Go binary is not executable")
        if mode & 0o002:
            _fail(f"{target} Go binary is world-writable")
        manifest = _read_direct(manifest_path, f"{target} binary manifest")
        identity = _binary_manifest_identity(
            manifest,
            label=f"{target} binary manifest",
            target=target,
            version=version,
            corpus=corpus,
            binary=binary,
        )
        slug = _target_slug(target)
        records[target] = {
            "name": BINARY_NAME,
            "version": version,
            "target": target,
            "corpus_fingerprint": corpus,
            "size_bytes": len(binary),
            "sha256": _sha256(binary),
            "manifest": {
                "name": f"{BINARY_NAME}.binary-manifest.json",
                "size_bytes": len(manifest),
                "sha256": _sha256(manifest),
            },
            "build_identity": {
                "corpus_fingerprint": corpus,
                "schema_version": BUILD_INFO_SCHEMA,
                "target": target,
                "version": version,
            },
            "build_configuration": {
                "module_path": identity["module_path"],
                "build_info_schema": identity["build_info_schema"],
                "build_flags": identity["build_flags"],
            },
        }
        paths[f"go/{slug}/{BINARY_NAME}"] = binary_path
        paths[f"go/{slug}/{BINARY_NAME}.binary-manifest.json"] = manifest_path
    return records, paths


def _archive_file_mode(mode: int, label: str) -> None:
    kind = stat.S_IFMT(mode)
    if kind not in (0, stat.S_IFREG):
        _fail(f"{label} contains an unsupported member type")
    if mode & 0o002:
        _fail(f"{label} contains a world-writable member")
