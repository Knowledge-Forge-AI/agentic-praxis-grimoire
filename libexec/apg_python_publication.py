"""Build and validate APGR's local Python distribution candidates.

v0.7 wheels are platform-specific and contain one exact Go executable plus its
canonical manifest.  The Go build helper remains the compiler/identity owner;
this module only assembles and validates package archives.  The explicit v0.6
helpers retain the historical universal-wheel reconstruction contract without
making the current VERSION authority historical again.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.message import Message
from email.parser import BytesParser
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tarfile
import tempfile
from typing import Any, Mapping, Sequence
import zipfile

import apg_distribution_candidate_contract as candidate_contract
import apg_python_distribution as distribution


COMMAND = "apg-build-python-release-bundle"
PROJECT_NAME = "agentic-praxis-grimoire"
DIST_NAME = "agentic_praxis_grimoire"
MODULE = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
SUPPORTED_TARGETS = ("darwin/arm64", "linux/amd64", "linux/arm64")


def _canonical_target_tags() -> dict[str, str]:
    helper_directory = os.fspath(Path(__file__).resolve().parent)
    if helper_directory not in sys.path:
        sys.path.insert(0, helper_directory)
    try:
        import apg_go_build

        result: dict[str, str] = {}
        for target in SUPPORTED_TARGETS:
            mapping = apg_go_build.target_mapping(target)
            value = mapping.get("python_platform")
            if not isinstance(value, str) or not value:
                raise PublicationError(f"Go target mapping lacks a Python platform tag: {target}")
            result[target] = value
        return result
    except (ImportError, AttributeError) as error:
        raise PublicationError("canonical Go target mapping could not be loaded") from error


TARGET_TAGS = _canonical_target_tags()
EPOCH = getattr(distribution, "V07_RELEASE_EPOCH", distribution.V06_RELEASE_EPOCH)
HISTORICAL_V06_VERSION = "0.6.0"
HISTORICAL_V06_WHEEL_NAME = (
    f"{DIST_NAME}-{HISTORICAL_V06_VERSION}-py3-none-any.whl"
)
HISTORICAL_V06_SDIST_NAME = f"{DIST_NAME}-{HISTORICAL_V06_VERSION}.tar.gz"
HISTORICAL_V06_BUNDLE_NAMES = (
    HISTORICAL_V06_WHEEL_NAME,
    HISTORICAL_V06_SDIST_NAME,
    "SHA256SUMS",
)
_METADATA_FIELDS = ("Name", "Version", "Requires-Python", "License-Expression")
_MAX_SUBPROCESS_STDERR = 4096


class PublicationError(ValueError):
    """A publication candidate failed its exact local contract."""


@dataclass(frozen=True)
class Layout:
    version: str
    wheel_names: tuple[str, ...]
    sdist_name: str
    checksum_name: str = "SHA256SUMS"
    historical: bool = False

    @property
    def artifact_names(self) -> tuple[str, ...]:
        return (*self.wheel_names, self.sdist_name)

    @property
    def bundle_names(self) -> tuple[str, ...]:
        return (*self.artifact_names, self.checksum_name)


def _fail(message: str) -> None:
    raise PublicationError(message)


def _regular(path: Path, label: str) -> None:
    try:
        status = path.lstat()
    except OSError as error:
        raise PublicationError(f"{label} is unavailable") from error
    if not stat.S_ISREG(status.st_mode) or path.is_symlink():
        _fail(f"{label} must be a direct regular file")


def _directory(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
        status = path.lstat()
    except OSError as error:
        raise PublicationError(f"{label} is unavailable") from error
    # A temporary root may have a platform-owned lexical prefix such as
    # /var -> /private on macOS.  Reject a symlink at the designated directory
    # itself, while allowing harmless ancestor aliases.
    if not stat.S_ISDIR(status.st_mode) or path.is_symlink():
        _fail(f"{label} must be one real direct directory")
    return resolved


def _executable(path: Path) -> Path:
    absolute = path.absolute()
    try:
        target = absolute.resolve(strict=True)
        target_status = target.stat()
        parent = absolute.parent.resolve(strict=True)
    except OSError as error:
        raise PublicationError("publication Python is unavailable") from error
    if (
        parent != absolute.parent
        or not stat.S_ISREG(target_status.st_mode)
        or not os.access(absolute, os.X_OK)
    ):
        _fail("publication Python must resolve from one real directory to an executable")
    return absolute


def _source_version(source: Path) -> str:
    path = source / "src" / "agentic_praxis_grimoire" / "VERSION"
    _regular(path, "package version resource")
    value = path.read_text(encoding="ascii").strip()
    if not value or any(character.isspace() for character in value):
        _fail("package version resource is malformed")
    return value


def _corpus_fingerprint(source: Path) -> str:
    path = source / "src" / "agentic_praxis_grimoire" / "resources" / "skill-metadata.json"
    _regular(path, "skill corpus identity")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def layout(source: Path, *, historical: bool = False) -> Layout:
    version = HISTORICAL_V06_VERSION if historical else _source_version(source)
    if historical:
        return Layout(
            version,
            (HISTORICAL_V06_WHEEL_NAME,),
            HISTORICAL_V06_SDIST_NAME,
            historical=True,
        )
    wheels = tuple(
        candidate_contract.python_wheel_filename(target, version)
        for target in SUPPORTED_TARGETS
    )
    return Layout(version, wheels, candidate_contract.python_sdist_filename(version))



def _repository_layout() -> Layout:
    return layout(Path(__file__).resolve().parent.parent)


# Current names remain available to repository callers, but are derived from
# VERSION at import time.  WHEEL_NAME is a compatibility alias for the first
# (darwin/arm64) wheel; new code should use WHEEL_NAMES.
VERSION = _repository_layout().version
WHEEL_NAMES = _repository_layout().wheel_names
WHEEL_NAME = WHEEL_NAMES[0]
SDIST_NAME = _repository_layout().sdist_name
CHECKSUM_NAME = "SHA256SUMS"
BUNDLE_NAMES = (*WHEEL_NAMES, SDIST_NAME, CHECKSUM_NAME)


def _safe_archive_name(name: str) -> None:
    pure = PurePosixPath(name)
    lexical_parts = name.split("/")
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or pure.is_absolute()
        or any(part in {"", ".", ".."} for part in lexical_parts)
    ):
        _fail("distribution archive contains an unsafe member path")


def _metadata_contract(
    payload: bytes, label: str, *, version: str | None = None
) -> bytes:
    message: Message = BytesParser().parsebytes(payload)
    values = {field: message.get(field) for field in _METADATA_FIELDS}
    expected = {
        "Name": PROJECT_NAME,
        "Version": VERSION if version is None else version,
        "Requires-Python": ">=3.10",
        "License-Expression": "AGPL-3.0-or-later",
    }
    if values != expected:
        _fail(f"{label} metadata does not match the v{expected['Version']} publication contract")
    return b"".join(
        f"{field}: {values[field]}\n".encode("utf-8") for field in _METADATA_FIELDS
    ) + b"\n"


def _wheel_metadata(path: Path, *, expected_version: str | None = None) -> bytes:
    _regular(path, "wheel")
    version = VERSION if expected_version is None else expected_version
    info_name = f"{DIST_NAME}-{version}.dist-info/METADATA"
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                _fail("wheel contains duplicate members")
            for info in archive.infolist():
                _safe_archive_name(info.filename.rstrip("/"))
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode):
                    _fail("wheel contains an unsupported member type")
            metadata_names = [name for name in names if name == info_name]
            if len(metadata_names) != 1:
                _fail("wheel must contain one exact METADATA member")
            return archive.read(metadata_names[0])
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise PublicationError("wheel is malformed") from error


def _sdist_metadata(path: Path, *, expected_version: str | None = None) -> bytes:
    _regular(path, "normalized sdist")
    version = VERSION if expected_version is None else expected_version
    expected_root = f"{DIST_NAME}-{version}"
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            if len(names) != len(set(names)):
                _fail("normalized sdist contains duplicate members")
            for member in members:
                _safe_archive_name(member.name)
                if not member.isfile() and not member.isdir():
                    _fail("normalized sdist contains an unsupported member")
                if member.name != expected_root and not member.name.startswith(expected_root + "/"):
                    _fail("normalized sdist has an unexpected archive root")
                if member.name.endswith("/bin/apgr") or member.name.endswith("/bin/apgr.exe"):
                    _fail("sdist must not contain a prebuilt Go binary")
            metadata = [
                member
                for member in members
                if member.name == f"{expected_root}/PKG-INFO" and member.isfile()
            ]
            if len(metadata) != 1:
                _fail("normalized sdist must contain one exact PKG-INFO member")
            stream = archive.extractfile(metadata[0])
            if stream is None:
                _fail("normalized sdist PKG-INFO is unreadable")
            return stream.read()
    except (OSError, tarfile.TarError) as error:
        raise PublicationError("normalized sdist is malformed") from error


def _manifest_field(value: Mapping[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = value
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                current = None
                break
            current = current[key]
        if current is not None:
            return current
    return None


def _validate_manifest(
    manifest_bytes: bytes,
    binary: bytes,
    *,
    source: Path,
    target: str,
    version: str,
) -> None:
    try:
        parsed = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublicationError("binary manifest is malformed") from error
    if not isinstance(parsed, dict):
        _fail("binary manifest must be a JSON object")
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
    if set(parsed) != expected_keys:
        _fail("binary manifest fields do not match apg.binary-manifest/v1")
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    if canonical != manifest_bytes:
        _fail("binary manifest is not canonical")
    observed_version = _manifest_field(parsed, ("version",), ("build", "version"))
    if observed_version != version:
        _fail("binary manifest version does not match package version")
    observed_target = _manifest_field(parsed, ("target",))
    helper_directory = os.fspath(Path(__file__).resolve().parent)
    if helper_directory not in sys.path:
        sys.path.insert(0, helper_directory)
    try:
        import apg_go_build

        expected_target = apg_go_build.target_mapping(target)
    except (ImportError, AttributeError) as error:
        raise PublicationError("canonical Go target mapping could not be loaded") from error
    if not isinstance(observed_target, Mapping) or dict(observed_target) != expected_target:
        _fail("binary manifest target does not match wheel target")
    digest = hashlib.sha256(binary).hexdigest()
    observed_digest = _manifest_field(
        parsed,
        ("sha256",),
        ("binary", "sha256"),
        ("binary", "sha_256"),
    )
    if observed_digest != digest:
        _fail("binary manifest SHA-256 does not match packaged binary")
    observed_size = _manifest_field(parsed, ("size_bytes",), ("binary", "size_bytes"))
    if observed_size != len(binary):
        _fail("binary manifest size does not match packaged binary")
    observed_corpus = _manifest_field(parsed, ("corpus_fingerprint",), ("build", "corpus_fingerprint"))
    expected_corpus = _corpus_fingerprint(source)
    if observed_corpus != expected_corpus:
        _fail("binary manifest corpus fingerprint does not match package corpus")
    schema = _manifest_field(parsed, ("schema_version",), ("schema",), ("schema_id",))
    if schema != apg_go_build.MANIFEST_SCHEMA:
        _fail("binary manifest schema is unsupported")
    if parsed["module_path"] != apg_go_build.MODULE:
        _fail("binary manifest module identity is wrong")
    if parsed["build_info_schema"] != apg_go_build.BUILD_INFO_SCHEMA:
        _fail("binary manifest build-info schema is unsupported")
    if parsed["build_flags"] != list(apg_go_build.BUILD_FLAGS):
        _fail("binary manifest build flags are wrong")
    if parsed["binary_name"] != apg_go_build.BINARY_NAME:
        _fail("binary manifest binary name is wrong")
    expected_build_identity = {
        "corpus_fingerprint": expected_corpus,
        "schema_version": apg_go_build.BUILD_INFO_SCHEMA,
        "target": target,
        "version": version,
    }
    if parsed["build_identity"] != expected_build_identity:
        _fail("binary manifest build identity is inconsistent")


def _validate_wheel_structure(
    path: Path,
    *,
    source: Path,
    target: str,
    version: str,
) -> None:
    expected_name = f"{DIST_NAME}-{version}-py3-none-{TARGET_TAGS[target]}.whl"
    if path.name != expected_name:
        _fail("wheel filename does not match its target-derived v" + version + " contract")
    _regular(path, "wheel")
    info_name = f"{DIST_NAME}-{version}.dist-info"
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                _fail("wheel contains duplicate members")
            for member in archive.infolist():
                _safe_archive_name(member.filename.rstrip("/"))
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode):
                    _fail("wheel contains an unsupported member type")
            wheel_name = f"{info_name}/WHEEL"
            manifest_name = "agentic_praxis_grimoire/bin/apgr.binary-manifest.json"
            binary_name = "agentic_praxis_grimoire/bin/apgr"
            record_name = f"{info_name}/RECORD"
            for required in (wheel_name, manifest_name, binary_name, record_name):
                if names.count(required) != 1:
                    _fail(f"wheel is missing required member: {required}")
            wheel_text = archive.read(wheel_name).decode("ascii")
            if "Root-Is-Purelib: false\n" not in wheel_text:
                _fail("wheel must declare Root-Is-Purelib false")
            if f"Tag: py3-none-{TARGET_TAGS[target]}\n" not in wheel_text:
                _fail("wheel tag does not match its target")
            binary = archive.read(binary_name)
            mode = archive.getinfo(binary_name).external_attr >> 16
            if not stat.S_IXUSR & mode:
                _fail("packaged Go binary is not executable")
            _validate_manifest(archive.read(manifest_name), binary, source=source, target=target, version=version)
            record_lines = archive.read(record_name).decode("utf-8").splitlines()
            seen: set[str] = set()
            for line in record_lines:
                fields = line.split(",")
                if len(fields) != 3:
                    _fail("wheel RECORD has a malformed row")
                name, digest, size = fields
                if name in seen:
                    _fail("wheel RECORD contains a duplicate row")
                seen.add(name)
                if name == record_name:
                    if digest or size:
                        _fail("wheel RECORD self-row must be empty")
                    continue
                if name not in names:
                    _fail("wheel RECORD names a missing member")
                expected_digest = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(archive.read(name)).digest()).rstrip(b"=").decode("ascii")
                if digest != expected_digest or size != str(len(archive.read(name))):
                    _fail("wheel RECORD hash or size does not match member")
            if set(names) != seen:
                _fail("wheel RECORD does not cover every member")
            for license_name in ("LICENSE", "NOTICE", "COMMERCIAL-LICENSE.md"):
                if f"{info_name}/licenses/{license_name}" not in names:
                    _fail("wheel is missing required licensing material")
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, KeyError) as error:
        raise PublicationError("wheel is malformed") from error


def _validate_sdist_sources(path: Path, *, version: str) -> None:
    root = f"{DIST_NAME}-{version}/"
    try:
        with tarfile.open(path, mode="r:gz") as archive:
            names = {member.name for member in archive.getmembers()}
    except (OSError, tarfile.TarError) as error:
        raise PublicationError("normalized sdist is malformed") from error
    required = {
        root + "go.mod",
        root + "pyproject.toml",
        root + "libexec/apg_go_build.py",
        root + "libexec/apg_python_build_backend.py",
        root + "src/agentic_praxis_grimoire/VERSION",
    }
    if not required.issubset(names):
        _fail("sdist does not contain the complete Go/Python build source")
    if not any(name.startswith(root + "skills/") and name.endswith("/SKILL.md") for name in names):
        _fail("sdist does not contain canonical skill source")


def validate_distributions(
    wheel: Path,
    sdist: Path,
    *,
    source: Path | None = None,
    target: str | None = None,
    historical: bool = False,
) -> tuple[bytes, bytes]:
    """Validate one wheel/sdist pair and their shared metadata contract."""

    if not historical and wheel.name == HISTORICAL_V06_WHEEL_NAME:
        # Keep the pre-APG100 call shape usable for historical reconstruction;
        # v0.7 callers still receive the strict target-wheel path below.
        historical = True
    source_root = source or Path(__file__).resolve().parent.parent
    selected_layout = layout(source_root, historical=historical)
    expected_wheel = (
        HISTORICAL_V06_WHEEL_NAME
        if historical
        else next((name for name in selected_layout.wheel_names if name == wheel.name), None)
    )
    if wheel.name != expected_wheel or sdist.name != selected_layout.sdist_name:
        _fail("distribution filenames do not match the publication contract")
    with tempfile.TemporaryDirectory(prefix=".apg-normalization-check-", dir=sdist.parent) as temporary:
        normalized = Path(temporary) / sdist.name
        try:
            distribution.normalize_archive(sdist, normalized, EPOCH)
        except distribution.NormalizationError as error:
            raise PublicationError("normalized sdist cannot be revalidated") from error
        if normalized.read_bytes() != sdist.read_bytes():
            _fail(f"sdist is not normalized under the v{selected_layout.version} publication contract")
    wheel_contract = _metadata_contract(
        _wheel_metadata(wheel, expected_version=selected_layout.version),
        "wheel",
        version=selected_layout.version,
    )
    sdist_contract = _metadata_contract(
        _sdist_metadata(sdist, expected_version=selected_layout.version),
        "normalized sdist",
        version=selected_layout.version,
    )
    if wheel_contract != sdist_contract:
        _fail("wheel and sdist metadata disagree")
    if not historical:
        if target is None:
            target = next(
                target_name
                for target_name in SUPPORTED_TARGETS
                if wheel.name.endswith(f"-{TARGET_TAGS[target_name]}.whl")
            )
        _validate_wheel_structure(wheel, source=source_root, target=target, version=selected_layout.version)
        _validate_sdist_sources(sdist, version=selected_layout.version)
    return wheel_contract, sdist_contract


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checksum_bytes(
    directory: Path,
    *,
    historical: bool = False,
    source: Path | None = None,
) -> bytes:
    """Return canonical checksums for the current or historical artifacts."""

    source_root = source or Path(__file__).resolve().parent.parent
    if not historical and (directory / HISTORICAL_V06_WHEEL_NAME).exists():
        historical = True
    selected_layout = layout(source_root, historical=historical)
    if historical:
        validate_distributions(
            directory / selected_layout.wheel_names[0],
            directory / selected_layout.sdist_name,
            source=source_root,
            historical=True,
        )
    else:
        for wheel_name in selected_layout.wheel_names:
            target = next(target for target in SUPPORTED_TARGETS if wheel_name.endswith(f"-{TARGET_TAGS[target]}.whl"))
            validate_distributions(
                directory / wheel_name,
                directory / selected_layout.sdist_name,
                source=source_root,
                target=target,
            )
    return "".join(
        f"{_sha256(directory / name)}  {name}\n" for name in selected_layout.artifact_names
    ).encode("ascii")


def validate_bundle(
    directory: Path,
    *,
    historical: bool = False,
    source: Path | None = None,
) -> tuple[Path, ...]:
    """Validate one exact candidate bundle."""

    root = _directory(directory, "publication bundle")
    if not historical and (root / HISTORICAL_V06_WHEEL_NAME).exists():
        historical = True
    source_root = source or Path(__file__).resolve().parent.parent
    selected_layout = layout(source_root, historical=historical)
    observed = {entry.name for entry in root.iterdir()}
    if observed != set(selected_layout.bundle_names):
        _fail("publication bundle must contain exactly the expected assets")
    paths = tuple(root / name for name in selected_layout.bundle_names)
    for path in paths:
        _regular(path, f"publication asset {path.name}")
    expected = checksum_bytes(root, historical=historical, source=source_root)
    if paths[-1].read_bytes() != expected:
        _fail("publication bundle SHA-256 manifest does not match its distributions")
    return paths


def validate_v06_bundle(directory: Path) -> tuple[Path, ...]:
    """Preserve exact v0.6 bundle validation for historical reconstruction."""

    return validate_bundle(directory, historical=True)


def _run(
    arguments: list[str],
    *,
    source: Path,
    environment: dict[str, str],
    operation: str,
) -> None:
    try:
        subprocess.run(
            arguments,
            cwd=source,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            shell=False,
        )
    except OSError as error:
        raise PublicationError(f"publication subprocess failed during {operation}: {error}") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or b"").decode("utf-8", "replace").strip()
        if len(detail) > _MAX_SUBPROCESS_STDERR:
            detail = detail[-_MAX_SUBPROCESS_STDERR:]
        suffix = f": {detail}" if detail else ""
        raise PublicationError(f"publication subprocess failed during {operation}{suffix}") from error


def _backend(source: Path):
    helper_directory = os.fspath(source / "libexec")
    if helper_directory not in sys.path:
        sys.path.insert(0, helper_directory)
    try:
        import apg_python_build_backend as backend
    except ImportError as error:
        raise PublicationError("Python build backend could not be loaded") from error
    return backend


def _build_once(source: Path, root: Path, python: Path, seed: str) -> Path:
    del python
    build_root = root / f"build-{seed}"
    final = build_root / "publication"
    build_root.mkdir(mode=0o700)
    final.mkdir(mode=0o700)
    backend = _backend(source)
    binaries = build_root / "binaries"
    for target in SUPPORTED_TARGETS:
        target_root = binaries / target.replace("/", "-")
        target_root.mkdir(parents=True, mode=0o700)
        identity = backend._build_binary(source, target, target_root / "apgr")
        wheel = final / f"{DIST_NAME}-{_source_version(source)}-py3-none-{TARGET_TAGS[target]}.whl"
        backend._write_wheel(source, target, final, identity)
        if not wheel.is_file():
            _fail("Python backend did not create the expected target wheel")
    backend._write_sdist(source, final)
    return final


def _compare(first: Path, second: Path, names: Sequence[str] | None = None) -> None:
    selected = tuple(names or sorted(entry.name for entry in first.iterdir()))
    for name in selected:
        left = first / name
        right = second / name
        if left.read_bytes() != right.read_bytes():
            _fail(f"publication asset is not byte reproducible: {name}")
        if stat.S_IMODE(left.stat().st_mode) != stat.S_IMODE(right.stat().st_mode):
            _fail(f"publication asset mode is not reproducible: {name}")


def build_bundle(
    source: Path, output: Path, work_root: Path, python: Path
) -> tuple[Path, ...]:
    """Build all three platform wheels and one sdist twice, then select one."""

    source_root = _directory(source, "publication source")
    work = _directory(work_root, "publication work root")
    python_command = _executable(python)
    del python_command
    if output.exists() or output.is_symlink():
        _fail("publication output must not already exist")
    try:
        output_parent = output.parent.resolve(strict=True)
    except OSError as error:
        raise PublicationError("publication output parent is unavailable") from error
    if output.parent.is_symlink():
        _fail("publication output parent must be one real direct directory")
    if work.stat().st_dev != output_parent.stat().st_dev:
        _fail("publication output and work root must share one filesystem")
    if any((work / f"build-{seed}").exists() for seed in ("a", "b")):
        _fail("publication build roots must not already exist")
    selected_layout = layout(source_root)
    first = _build_once(source_root, work, python, "a")
    second = _build_once(source_root, work, python, "b")
    _compare(first, second, selected_layout.artifact_names)
    expected = set(selected_layout.artifact_names)
    if {entry.name for entry in first.iterdir()} != expected:
        _fail("Python build output contains unexpected assets")
    final = work / "build-a" / "publication"
    (final / selected_layout.checksum_name).write_bytes(checksum_bytes(final))
    (final / selected_layout.checksum_name).chmod(0o600)
    second_checksum = work / "build-b" / "publication" / selected_layout.checksum_name
    second_checksum.write_bytes(checksum_bytes(work / "build-b" / "publication"))
    second_checksum.chmod(0o600)
    _compare(final, work / "build-b" / "publication", selected_layout.bundle_names)
    os.replace(final, output)
    return validate_bundle(output)


def build_historical_bundle(
    source: Path, output: Path, work_root: Path, python: Path
) -> tuple[Path, ...]:
    """Reconstruct the exact v0.6 universal wheel/sdist bundle."""

    source_root = _directory(source, "historical publication source")
    if _source_version(source_root) != HISTORICAL_V06_VERSION:
        _fail("historical source is not exact v0.6.0")
    work = _directory(work_root, "historical publication work root")
    _executable(python)
    if output.exists() or output.is_symlink():
        _fail("publication output must not already exist")
    first_root = work / "build-a"
    second_root = work / "build-b"
    for build_root in (first_root, second_root):
        build_root.mkdir(mode=0o700)
        raw = build_root / "raw-dist"
        raw.mkdir(mode=0o700)
        environment = {
            "HOME": os.fspath(build_root / "home"),
            "LANG": "C",
            "LC_ALL": "C",
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": str(EPOCH),
            "TMPDIR": os.fspath(build_root),
            "TZ": "UTC",
        }
        (build_root / "home").mkdir(mode=0o700)
        _run(
            [os.fspath(python), "-m", "build", "--wheel", "--sdist", "--no-isolation", "--outdir", os.fspath(raw), os.fspath(source_root)],
            source=source_root,
            environment=environment,
            operation="historical Python distribution build",
        )
        final = build_root / "publication"
        final.mkdir(mode=0o700)
        wheel = raw / HISTORICAL_V06_WHEEL_NAME
        sdist = raw / HISTORICAL_V06_SDIST_NAME
        _regular(wheel, "historical wheel")
        _regular(sdist, "historical sdist")
        (final / HISTORICAL_V06_WHEEL_NAME).write_bytes(wheel.read_bytes())
        distribution.normalize_archive(sdist, final / HISTORICAL_V06_SDIST_NAME, EPOCH)
        (final / "SHA256SUMS").write_bytes(checksum_bytes(final, historical=True))
    _compare(first_root / "publication", second_root / "publication", HISTORICAL_V06_BUNDLE_NAMES)
    os.replace(first_root / "publication", output)
    return validate_v06_bundle(output)


def parser() -> Any:
    import argparse

    command = argparse.ArgumentParser(
        prog=COMMAND,
        description="Build or validate deterministic v0.7 Python platform distributions.",
    )
    subcommands = command.add_subparsers(dest="subcommand", required=True)
    build = subcommands.add_parser("build", help="build three wheels and one sdist twice")
    build.add_argument("--source", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--work-root", required=True, type=Path)
    build.add_argument("--python", default=Path(sys.executable), type=Path)
    historical = subcommands.add_parser("build-v06", help="reconstruct the historical v0.6 bundle")
    historical.add_argument("--source", required=True, type=Path)
    historical.add_argument("--output", required=True, type=Path)
    historical.add_argument("--work-root", required=True, type=Path)
    historical.add_argument("--python", default=Path(sys.executable), type=Path)
    check = subcommands.add_parser("check", help="validate one exact v0.7 bundle")
    check.add_argument("--bundle", required=True, type=Path)
    historical_check = subcommands.add_parser("check-v06", help="validate one historical v0.6 bundle")
    historical_check.add_argument("--bundle", required=True, type=Path)
    return command


def main(arguments: Sequence[str] | None = None) -> int:
    args = parser().parse_args(arguments)
    try:
        if args.subcommand == "build":
            paths = build_bundle(args.source, args.output, args.work_root, args.python)
        elif args.subcommand == "build-v06":
            paths = build_historical_bundle(args.source, args.output, args.work_root, args.python)
        elif args.subcommand == "check-v06":
            paths = validate_v06_bundle(args.bundle)
        else:
            paths = validate_bundle(args.bundle)
    except PublicationError as error:
        print(f"{COMMAND}: error: {error}", file=sys.stderr)
        return 1
    for path in paths:
        print(f"{_sha256(path)}  {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
