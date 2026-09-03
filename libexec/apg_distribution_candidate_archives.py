"""Archive validators for the APGR distribution candidate contract."""

from __future__ import annotations

import base64
from email.parser import BytesParser
from io import BytesIO
import hashlib
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
import tarfile
import zipfile

import apg_distribution_candidate_contract as contract


# Keep the lower-level names available for compatibility with callers that
# imported the original monolithic helper while the facade delegates here.
_fail = contract._fail
_read_direct = contract._read_direct
_sha256 = contract._sha256
_sha256_file = contract._sha256_file
_safe_member_name = contract._safe_member_name
_archive_file_mode = contract._archive_file_mode
_canonical_value = contract._canonical_value
_binary_manifest_identity = contract._binary_manifest_identity
_parse_json = contract._parse_json
canonical_json = contract.canonical_json
TARGETS = contract.TARGETS
TARGET_BY_GO = contract.TARGET_BY_GO
TARGET_BY_SLUG = contract.TARGET_BY_SLUG
LICENSE_FILES = contract.LICENSE_FILES
BINARY_MANIFEST_SCHEMA = contract.BINARY_MANIFEST_SCHEMA
BUILD_INFO_SCHEMA = contract.BUILD_INFO_SCHEMA
BINARY_NAME = contract.BINARY_NAME
DIST_NAME = contract.DIST_NAME
PYTHON_PACKAGE = contract.PYTHON_PACKAGE


def _wheel_members(path: Path) -> tuple[dict[str, zipfile.ZipInfo], dict[str, bytes]]:
    raw = _read_direct(path, f"wheel {path.name}")
    members: dict[str, zipfile.ZipInfo] = {}
    contents: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            for info in archive.infolist():
                name = _safe_member_name(info.filename, f"wheel {path.name}")
                if "private" in PurePosixPath(name).parts or ".git" in PurePosixPath(name).parts:
                    _fail(f"wheel {path.name} contains private development material")
                if name in members:
                    _fail(f"wheel {path.name} contains duplicate members")
                _archive_file_mode(info.external_attr >> 16, f"wheel {path.name}")
                if info.is_dir():
                    _fail(f"wheel {path.name} contains directory members")
                members[name] = info
                contents[name] = archive.read(info)
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise contract.DistributionCandidateError(f"wheel {path.name} is malformed") from error
    return members, contents


def _wheel_record_valid(
    contents: Mapping[str, bytes], *, record_name: str, label: str
) -> None:
    raw = contents.get(record_name)
    if raw is None:
        _fail(f"{label} has no RECORD")
    seen: set[str] = set()
    try:
        rows = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise contract.DistributionCandidateError(f"{label} RECORD is not UTF-8") from error
    for row in rows:
        fields = row.split(",")
        if len(fields) != 3:
            _fail(f"{label} RECORD has a malformed row")
        name, digest, size = fields
        if name in seen:
            _fail(f"{label} RECORD contains duplicate rows")
        seen.add(name)
        if name == record_name:
            if digest or size:
                _fail(f"{label} RECORD self-row is not empty")
            continue
        if name not in contents:
            _fail(f"{label} RECORD names a missing member")
        expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(contents[name]).digest()).rstrip(b"=").decode("ascii")
        if digest != expected or size != str(len(contents[name])):
            _fail(f"{label} RECORD hash or size does not match member")
    if seen != set(contents):
        _fail(f"{label} RECORD does not cover every member")


def _metadata_contract(raw: bytes, *, version: str, label: str) -> None:
    try:
        message = BytesParser().parsebytes(raw)
    except (TypeError, ValueError) as error:
        raise contract.DistributionCandidateError(f"{label} metadata is malformed") from error
    expected = {
        "Name": PYTHON_PACKAGE,
        "Version": version,
        "Requires-Python": ">=3.10",
        "License-Expression": "AGPL-3.0-or-later",
    }
    if {key: message.get(key) for key in expected} != expected:
        _fail(f"{label} metadata does not match VERSION authority")


def _validate_wheel(
    path: Path,
    *,
    target: str,
    version: str,
    corpus: str,
    binary: Mapping[str, Any],
) -> dict[str, Any]:
    expected_name = f"{DIST_NAME}-{version}-py3-none-{TARGET_BY_GO[target]['python_platform']}.whl"
    if path.name != expected_name:
        _fail(f"wheel filename does not match {target}")
    members, contents = _wheel_members(path)
    info = f"{DIST_NAME}-{version}.dist-info"
    metadata_name = f"{info}/METADATA"
    wheel_name = f"{info}/WHEEL"
    binary_name = "agentic_praxis_grimoire/bin/apgr"
    binary_manifest_name = "agentic_praxis_grimoire/bin/apgr.binary-manifest.json"
    record_name = f"{info}/RECORD"
    required = (metadata_name, wheel_name, binary_name, binary_manifest_name, record_name)
    if any(name not in contents for name in required):
        _fail(f"wheel {path.name} is missing a required member")
    _metadata_contract(contents[metadata_name], version=version, label=f"wheel {path.name}")
    try:
        wheel_text = contents[wheel_name].decode("ascii", "strict")
    except UnicodeDecodeError as error:
        raise contract.DistributionCandidateError(f"wheel {path.name} WHEEL metadata is not ASCII") from error
    expected_tag = TARGET_BY_GO[target]["python_platform"]
    if "Root-Is-Purelib: false\n" not in wheel_text or f"Tag: py3-none-{expected_tag}\n" not in wheel_text:
        _fail(f"wheel {path.name} platform tag is not exact")
    _wheel_record_valid(contents, record_name=record_name, label=f"wheel {path.name}")
    packaged_binary = contents[binary_name]
    if not members[binary_name].external_attr >> 16 & 0o111:
        _fail(f"wheel {path.name} Go binary is not executable")
    if _sha256(packaged_binary) != binary["sha256"] or len(packaged_binary) != binary["size_bytes"]:
        _fail(f"wheel {path.name} binary differs from the canonical Go binary")
    _binary_manifest_identity(
        contents[binary_manifest_name],
        label=f"wheel {path.name} binary manifest",
        target=target,
        version=version,
        corpus=corpus,
        binary=packaged_binary,
    )
    if _sha256(contents[binary_manifest_name]) != binary["manifest"]["sha256"]:
        _fail(f"wheel {path.name} binary manifest differs from the canonical manifest")
    for license_name in LICENSE_FILES:
        if f"{info}/licenses/{license_name}" not in contents:
            _fail(f"wheel {path.name} is missing {license_name}")
    return {
        "name": path.name,
        "package": PYTHON_PACKAGE,
        "version": version,
        "target": target,
        "python_platform": expected_tag,
        "size_bytes": len(_read_direct(path, f"wheel {path.name}")),
        "sha256": _sha256_file(path, f"wheel {path.name}"),
        "binary": {"member": binary_name, "size_bytes": len(packaged_binary), "sha256": _sha256(packaged_binary)},
        "manifest": {"member": binary_manifest_name, "size_bytes": len(contents[binary_manifest_name]), "sha256": _sha256(contents[binary_manifest_name])},
    }


def _find_python_files(root: Path, *, version: str) -> tuple[dict[str, Path], Path]:
    expected = {
        target: root / f"{DIST_NAME}-{version}-py3-none-{mapping['python_platform']}.whl"
        for target, mapping in TARGET_BY_GO.items()
    }
    sdist = root / f"{DIST_NAME}-{version}.tar.gz"
    for target, path in expected.items():
        _read_direct(path, f"{target} Python wheel")
    _read_direct(sdist, "Python sdist")
    allowed = {path.name for path in expected.values()} | {sdist.name, "SHA256SUMS"}
    observed = {entry.name for entry in root.iterdir()}
    if not observed.issubset(allowed):
        _fail("Python artifact root contains an unexpected file")
    return expected, sdist


def _validate_sdist(path: Path, *, version: str) -> dict[str, Any]:
    expected_root = f"{DIST_NAME}-{version}"
    raw = _read_direct(path, "Python sdist")
    names: set[str] = set()
    contents: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=BytesIO(raw), mode="r:gz") as archive:
            for member in archive.getmembers():
                name = _safe_member_name(member.name, "Python sdist")
                relative_name = name[len(expected_root) + 1 :] if name.startswith(expected_root + "/") else name
                if relative_name == "private" or relative_name.startswith("private/") or relative_name == ".git" or relative_name.startswith(".git/"):
                    _fail("Python sdist contains private development material")
                if name in names:
                    _fail("Python sdist contains duplicate members")
                names.add(name)
                if name != expected_root and not name.startswith(expected_root + "/"):
                    _fail("Python sdist has an unexpected archive root")
                if not member.isfile() and not member.isdir():
                    _fail("Python sdist contains an unsupported member")
                if member.mode & 0o002:
                    _fail("Python sdist contains a world-writable member")
                if name.endswith("/bin/apgr") or name.endswith("/bin/apgr.binary-manifest.json"):
                    _fail("Python sdist must not contain a prebuilt Go binary")
                if member.isfile():
                    stream = archive.extractfile(member)
                    if stream is None:
                        _fail("Python sdist member cannot be read")
                    contents[name] = stream.read()
    except (OSError, tarfile.TarError) as error:
        raise contract.DistributionCandidateError("Python sdist is malformed") from error
    metadata_name = f"{expected_root}/PKG-INFO"
    _metadata_contract(contents.get(metadata_name, b""), version=version, label="Python sdist")
    required = {
        f"{expected_root}/go.mod",
        f"{expected_root}/pyproject.toml",
        f"{expected_root}/src/agentic_praxis_grimoire/VERSION",
        f"{expected_root}/libexec/apg_go_build.py",
        f"{expected_root}/libexec/apg_python_build_backend.py",
    }
    if not required.issubset(names) or not any(
        name.startswith(f"{expected_root}/skills/") and name.endswith("/SKILL.md") for name in names
    ):
        _fail("Python sdist does not contain complete Go/Python/skill source")
    if contents[f"{expected_root}/src/agentic_praxis_grimoire/VERSION"].decode("ascii").strip() != version:
        _fail("Python sdist VERSION differs from authority")
    return {
        "name": path.name,
        "package": PYTHON_PACKAGE,
        "version": version,
        "size_bytes": len(raw),
        "sha256": _sha256(raw),
    }


def _npm_tarball_name(package: str, version: str) -> str:
    return contract.npm_tarball_filename(package, version)



def _npm_members(path: Path) -> tuple[dict[str, tarfile.TarInfo], dict[str, bytes]]:
    raw = _read_direct(path, f"npm tarball {path.name}")
    members: dict[str, tarfile.TarInfo] = {}
    contents: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=BytesIO(raw), mode="r:gz") as archive:
            for member in archive:
                name = _safe_member_name(member.name, f"npm tarball {path.name}")
                if not name.startswith("package/"):
                    _fail(f"npm tarball {path.name} member is outside package/")
                if name in members:
                    _fail(f"npm tarball {path.name} contains duplicate members")
                if not member.isfile() or member.issym() or member.islnk():
                    _fail(f"npm tarball {path.name} contains an unsupported member")
                _archive_file_mode(member.mode, f"npm tarball {path.name}")
                stream = archive.extractfile(member)
                if stream is None:
                    _fail(f"npm tarball {path.name} member cannot be read")
                members[name] = member
                contents[name] = stream.read()
    except (OSError, tarfile.TarError) as error:
        raise contract.DistributionCandidateError(f"npm tarball {path.name} is malformed") from error
    return members, contents


def _validate_npm_package(
    path: Path,
    *,
    version: str,
    corpus: str,
    binaries: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    members, contents = _npm_members(path)
    package = _parse_json(contents.get("package/package.json", b""), f"npm {path.name} package.json")
    if canonical_json(package) != contents["package/package.json"]:
        _fail(f"npm {path.name} package.json is not canonical JSON")
    name = package.get("name")
    if not isinstance(name, str) or package.get("version") != version:
        _fail(f"npm {path.name} package identity is not exact")
    expected_files = {"package/package.json", *(f"package/{license_name}" for license_name in LICENSE_FILES)}
    if version >= "0.8.1" or "package/README.md" in contents:
        expected_files.add("package/README.md")
    target: str | None = None
    binary_record: dict[str, Any] | None = None
    manifest_record: dict[str, Any] | None = None
    if name == "@knowledge-forge-ai/apgr":
        expected_files.add("package/index.js")
        if not members["package/index.js"].mode & 0o111:
            _fail(f"npm {path.name} launcher is not executable")
        if package.get("optionalDependencies") != {
            mapping["npm_package"]: version for mapping in TARGETS
        }:
            _fail("npm launcher optional platform dependencies are not exact")
        if package.get("dependencies") or package.get("scripts"):
            _fail("npm launcher contains runtime dependencies or install scripts")
        apg = package.get("apg")
        if not isinstance(apg, Mapping) or apg.get("binary_manifest_schema") != BINARY_MANIFEST_SCHEMA or apg.get("corpus_fingerprint") != corpus:
            _fail("npm launcher identity is not bound to the corpus")
    else:
        target_candidates = [mapping for mapping in TARGETS if mapping["npm_package"] == name]
        if len(target_candidates) != 1:
            _fail(f"npm {path.name} package name is unsupported")
        mapping = target_candidates[0]
        target = mapping["go_target"]
        expected_files.update({"package/bin/apgr", "package/bin/apgr.binary-manifest.json"})
        if package.get("os") != [mapping["npm_os"]] or package.get("cpu") != [mapping["npm_cpu"]]:
            _fail(f"npm {path.name} platform restrictions are not exact")
        if package.get("dependencies") or package.get("scripts"):
            _fail(f"npm {path.name} contains runtime dependencies or install scripts")
        apg = package.get("apg")
        if (
            not isinstance(apg, Mapping)
            or apg.get("binary_manifest_schema") != BINARY_MANIFEST_SCHEMA
            or apg.get("target") != target
            or apg.get("corpus_fingerprint") != corpus
            or apg.get("binary_basename") != BINARY_NAME
            or apg.get("manifest_file") != "bin/apgr.binary-manifest.json"
            or apg.get("build_identity") != binaries[target]["build_identity"]
        ):
            _fail(f"npm {path.name} target/corpus identity is not exact")
        packaged_binary = contents.get("package/bin/apgr", b"")
        canonical = binaries[target]
        if _sha256(packaged_binary) != canonical["sha256"] or len(packaged_binary) != canonical["size_bytes"]:
            _fail(f"npm {path.name} binary differs from the canonical Go binary")
        if not members["package/bin/apgr"].mode & 0o111:
            _fail(f"npm {path.name} Go binary is not executable")
        _binary_manifest_identity(
            contents["package/bin/apgr.binary-manifest.json"],
            label=f"npm {path.name} binary manifest",
            target=target,
            version=version,
            corpus=corpus,
            binary=packaged_binary,
        )
        if _sha256(contents["package/bin/apgr.binary-manifest.json"]) != binaries[target]["manifest"]["sha256"]:
            _fail(f"npm {path.name} binary manifest differs from the canonical manifest")
        binary_record = {"member": "package/bin/apgr", "size_bytes": len(packaged_binary), "sha256": _sha256(packaged_binary)}
        manifest_bytes = contents["package/bin/apgr.binary-manifest.json"]
        manifest_record = {"member": "package/bin/apgr.binary-manifest.json", "size_bytes": len(manifest_bytes), "sha256": _sha256(manifest_bytes)}
    if set(contents) != expected_files:
        _fail(f"npm {path.name} contains unexpected or missing members")
    record: dict[str, Any] = {
        "name": name,
        "version": version,
        "filename": path.name,
        "size_bytes": len(_read_direct(path, f"npm tarball {path.name}")),
        "sha256": _sha256_file(path, f"npm tarball {path.name}"),
    }
    if target is not None:
        record.update({"target": target, "binary": binary_record, "manifest": manifest_record})
    return record


def _find_npm_files(root: Path, *, version: str) -> dict[str, Path]:
    expected = {"@knowledge-forge-ai/apgr": root / _npm_tarball_name("@knowledge-forge-ai/apgr", version)}
    expected.update(
        {
            mapping["npm_package"]: root / _npm_tarball_name(mapping["npm_package"], version)
            for mapping in TARGETS
        }
    )
    for name, path in expected.items():
        _read_direct(path, f"npm {name} tarball")
    allowed = {path.name for path in expected.values()} | {"SHA256SUMS"}
    if not {entry.name for entry in root.iterdir()}.issubset(allowed):
        _fail("npm artifact root contains an unexpected file")
    return expected
