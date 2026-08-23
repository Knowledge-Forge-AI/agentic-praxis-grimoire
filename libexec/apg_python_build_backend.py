"""Small, dependency-free PEP 517 backend for APGR platform artifacts.

The source distribution deliberately carries this backend instead of relying on
an installer to fetch a packaging framework.  A wheel built from a checkout or
an extracted sdist contains the host-target Go executable and its canonical
manifest.  The publication helper supplies a previously built executable when
it is assembling a cross-target wheel, so Python and npm package the same bytes.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import platform
import stat
import sys
import tarfile
import tempfile
from typing import Any, Mapping
import zipfile


PROJECT_NAME = "agentic-praxis-grimoire"
DIST_NAME = "agentic_praxis_grimoire"
MODULE = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
SUPPORTED_TARGETS = ("darwin/arm64", "linux/amd64", "linux/arm64")
DEFAULT_EPOCH = 1_787_270_400
MANIFEST_SCHEMA = "apg.binary-manifest/v1"

# The Python distribution is a thin compatibility front door.  Keep this
# allowlist explicit so a legacy consumer module cannot enter a public wheel
# merely because it happens to remain in the checkout.
PACKAGE_FILES = (
    "VERSION",
    "__init__.py",
    "__main__.py",
    "cli.py",
    "config.py",
    "go_bridge.py",
    "paths.py",
    "reports.py",
    "response.py",
    "version.py",
    "resources/__init__.py",
    "resources/skill-metadata.json",
)


class BackendError(RuntimeError):
    """A source distribution or wheel cannot be built safely."""


@dataclass(frozen=True)
class BinaryIdentity:
    path: Path
    manifest: bytes
    target: str


def _target_tags() -> dict[str, str]:
    """Read Python compatibility tags from the canonical Go target mapping."""

    helper_directory = Path(__file__).resolve().parent
    if os.fspath(helper_directory) not in sys.path:
        sys.path.insert(0, os.fspath(helper_directory))
    try:
        import apg_go_build  # type: ignore[import-not-found]

        result: dict[str, str] = {}
        for target in SUPPORTED_TARGETS:
            mapping = apg_go_build.target_mapping(target)
            platform_tag = mapping.get("python_platform")
            if not isinstance(platform_tag, str) or not platform_tag:
                raise BackendError(f"Go target mapping lacks a Python platform tag: {target}")
            result[target] = platform_tag
        return result
    except (ImportError, AttributeError) as error:
        raise BackendError("canonical Go target mapping could not be loaded") from error


TARGET_TAGS = _target_tags()


def _root() -> Path:
    candidate = Path(__file__).resolve().parent.parent
    if not (candidate / "pyproject.toml").is_file():
        raise BackendError("project root is unavailable")
    return candidate


def _direct_file(path: Path, label: str, *, executable: bool = False) -> Path:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise BackendError(f"{label} is unavailable") from error
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BackendError(f"{label} must be a direct regular file")
    if executable and not os.access(path, os.X_OK):
        raise BackendError(f"{label} must be executable")
    return path


def _version(root: Path) -> str:
    path = _direct_file(root / "src" / "agentic_praxis_grimoire" / "VERSION", "VERSION")
    value = path.read_text(encoding="ascii").strip()
    if not value or any(character.isspace() for character in value):
        raise BackendError("VERSION is malformed")
    return value


def _corpus_fingerprint(root: Path) -> str:
    path = _direct_file(
        root / "src" / "agentic_praxis_grimoire" / "resources" / "skill-metadata.json",
        "skill corpus identity",
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not digest:
        raise BackendError("skill corpus identity is empty")
    return digest


def _host_target() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin" and machine in {"arm64", "aarch64"}:
        return "darwin/arm64"
    if system == "linux" and machine in {"x86_64", "amd64"}:
        return "linux/amd64"
    if system == "linux" and machine in {"arm64", "aarch64"}:
        return "linux/arm64"
    raise BackendError(
        f"unsupported Python wheel host target: {platform.system()}/{platform.machine()}"
    )


def _target(value: str | None) -> str:
    selected = value or os.environ.get("APG_BUILD_TARGET") or _host_target()
    if selected not in SUPPORTED_TARGETS:
        raise BackendError(f"unsupported APGR target: {selected}")
    return selected


def _config_value(config: Mapping[str, Any] | None, name: str) -> str | None:
    if not config:
        return None
    for key in (name, f"--{name}"):
        if key in config:
            value = config[key]
            if isinstance(value, (list, tuple)):
                value = value[-1] if value else None
            return None if value is None else str(value)
    return None


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _manifest_from_builder(
    root: Path,
    target: str,
    binary: Path,
    result: Any,
    manifest_hint: Path | None,
) -> bytes:
    """Read the manifest emitted by the canonical Go builder.

    APG96/APG99 exposed a small ``build`` result, while APG100's builder adds
    a manifest.  Supporting both shapes keeps this adapter narrow and lets the
    builder remain the single owner of compiler flags and build identity.
    """

    candidates: list[Any] = []
    if manifest_hint is not None:
        candidates.append(manifest_hint)
    if isinstance(result, Mapping):
        for key in ("manifest_path", "manifest_file", "manifest"):
            if key in result:
                candidates.append(result[key])
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            return _canonical_json(candidate)
        if isinstance(candidate, (str, os.PathLike)):
            path = Path(candidate)
            if path.is_file() and not path.is_symlink():
                payload = path.read_bytes()
                try:
                    parsed = json.loads(payload)
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise BackendError("Go binary manifest is malformed") from error
                if not isinstance(parsed, dict):
                    raise BackendError("Go binary manifest must be a JSON object")
                return _canonical_json(parsed)

    raise BackendError("canonical Go build did not return a binary manifest")


def _validated_manifest(
    root: Path, target: str, binary: Path, payload: bytes
) -> bytes:
    """Require the one manifest shape emitted by ``apg_go_build``."""

    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BackendError("binary manifest is malformed") from error
    if not isinstance(parsed, dict):
        raise BackendError("binary manifest must be a JSON object")
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
        raise BackendError("binary manifest fields do not match apg.binary-manifest/v1")
    canonical = _canonical_json(parsed)
    if canonical != payload:
        raise BackendError("binary manifest is not canonical JSON")
    version = _version(root)
    corpus = _corpus_fingerprint(root)
    helper_directory = os.fspath(root / "libexec")
    if helper_directory not in sys.path:
        sys.path.insert(0, helper_directory)
    try:
        import apg_go_build  # type: ignore[import-not-found]

        expected_target = apg_go_build.target_mapping(target)
    except (ImportError, AttributeError) as error:
        raise BackendError("canonical Go target mapping could not be loaded") from error
    observed_target = parsed["target"]
    if observed_target != expected_target:
        raise BackendError("binary manifest target disagrees with requested target")
    if parsed["schema_version"] != MANIFEST_SCHEMA:
        raise BackendError("binary manifest schema is unsupported")
    if parsed["build_info_schema"] != "apg.build-info/v1":
        raise BackendError("binary manifest build-info schema is unsupported")
    build_identity = parsed["build_identity"]
    if not isinstance(build_identity, Mapping) or build_identity != {
        "corpus_fingerprint": corpus,
        "schema_version": "apg.build-info/v1",
        "target": target,
        "version": version,
    }:
        raise BackendError("binary manifest build identity is wrong")
    if parsed["module_path"] != MODULE or parsed["version"] != version:
        raise BackendError("binary manifest release identity disagrees with VERSION")
    if parsed["binary_name"] != "apgr" or parsed["corpus_fingerprint"] != corpus:
        raise BackendError("binary manifest binary/corpus identity is wrong")
    content = binary.read_bytes()
    if parsed["size_bytes"] != len(content) or parsed["sha256"] != hashlib.sha256(content).hexdigest():
        raise BackendError("binary manifest does not match packaged binary")
    return payload


def _build_binary(root: Path, target: str, output: Path) -> BinaryIdentity:
    helper_path = root / "libexec" / "apg_go_build.py"
    _direct_file(helper_path, "Go build helper")
    helper_directory = os.fspath(helper_path.parent)
    if helper_directory not in sys.path:
        sys.path.insert(0, helper_directory)
    try:
        import apg_go_build  # type: ignore[import-not-found]
    except ImportError as error:
        raise BackendError("canonical Go build helper could not be loaded") from error
    output = output.absolute()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        result = apg_go_build.build(root, target, output)
    except Exception as error:  # helper exposes a bounded BuildError type
        if isinstance(error, BackendError):
            raise
        raise BackendError(f"canonical Go build failed: {error}") from error
    binary = _direct_file(output, "built APGR binary", executable=False)
    binary.chmod(0o755)
    manifest_hint: Path | None = None
    if isinstance(result, Mapping):
        for key in ("manifest_path", "manifest_file"):
            candidate = result.get(key)
            if candidate is not None:
                manifest_hint = Path(os.fspath(candidate))
                break
    manifest = _validated_manifest(
        root,
        target,
        binary,
        _manifest_from_builder(root, target, binary, result, manifest_hint),
    )
    return BinaryIdentity(binary, manifest, target)


def _provided_binary(
    root: Path, target: str, binary_value: str | None, manifest_value: str | None
) -> BinaryIdentity | None:
    if binary_value is None and manifest_value is None:
        return None
    if binary_value is None or manifest_value is None:
        raise BackendError("binary and binary manifest must be supplied together")
    binary = _direct_file(Path(binary_value), "provided APGR binary")
    manifest_path = _direct_file(Path(manifest_value), "provided APGR binary manifest")
    raw = manifest_path.read_bytes()
    try:
        parsed = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BackendError("provided APGR binary manifest is malformed") from error
    if not isinstance(parsed, dict):
        raise BackendError("provided APGR binary manifest must be an object")
    return BinaryIdentity(
        binary,
        _validated_manifest(root, target, binary, raw),
        target,
    )


def _binary_for_build(
    root: Path, target: str, config: Mapping[str, Any] | None, temporary: Path
) -> BinaryIdentity:
    supplied = _provided_binary(
        root,
        target,
        _config_value(config, "build-binary") or os.environ.get("APG_BUILD_BINARY"),
        _config_value(config, "build-manifest") or os.environ.get("APG_BUILD_MANIFEST"),
    )
    if supplied is not None:
        return supplied
    return _build_binary(root, target, temporary / "apgr")


def _metadata(root: Path) -> bytes:
    version = _version(root)
    return (
        "Metadata-Version: 2.4\n"
        f"Name: {PROJECT_NAME}\n"
        f"Version: {version}\n"
        "Summary: Bounded language, tooling, and agent workflow guidance for Agentic Praxis Grimoire.\n"
        "Requires-Python: >=3.10\n"
        "License-Expression: AGPL-3.0-or-later\n"
        "Requires-Dist: tomli>=2.0.1; python_version < \"3.11\"\n\n"
    ).encode("utf-8")


def _dist_info(root: Path) -> str:
    return f"{DIST_NAME}-{_version(root)}.dist-info"


def _wheel_entries(root: Path, binary: BinaryIdentity) -> dict[str, tuple[bytes, int]]:
    package = root / "src" / "agentic_praxis_grimoire"
    _direct_file(package / "__init__.py", "package source")
    entries: dict[str, tuple[bytes, int]] = {}
    for relative in PACKAGE_FILES:
        path = package / relative
        _direct_file(path, f"package source {relative}")
        entries[f"agentic_praxis_grimoire/{relative}"] = (path.read_bytes(), 0o644)
    entries["agentic_praxis_grimoire/bin/apgr"] = (binary.path.read_bytes(), 0o755)
    entries["agentic_praxis_grimoire/bin/apgr.binary-manifest.json"] = (binary.manifest, 0o644)
    info = _dist_info(root)
    entries[f"{info}/METADATA"] = (_metadata(root), 0o644)
    entries[f"{info}/WHEEL"] = (
        "Wheel-Version: 1.0\n"
        "Generator: apg-python-build-backend\n"
        "Root-Is-Purelib: false\n"
        f"Tag: py3-none-{TARGET_TAGS[binary.target]}\n\n"
    ).encode("ascii"), 0o644
    entries[f"{info}/entry_points.txt"] = (
        b"[console_scripts]\napgr = agentic_praxis_grimoire.__main__:main\n",
        0o644,
    )
    for license_name in ("LICENSE", "NOTICE", "COMMERCIAL-LICENSE.md"):
        license_path = root / license_name
        _direct_file(license_path, license_name)
        entries[f"{info}/licenses/{license_name}"] = (license_path.read_bytes(), 0o644)
    return entries


def _zip_info(name: str, mode: int, epoch: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name)
    info.date_time = datetime.fromtimestamp(epoch, timezone.utc).timetuple()[:6]
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    return info


def _record(entries: Mapping[str, tuple[bytes, int]]) -> bytes:
    rows: list[str] = []
    for name in sorted(entries):
        content = entries[name][0]
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode("ascii")
        rows.append(f"{name},sha256={digest},{len(content)}")
    rows.append(f"{_dist_info_from_entries(entries)}/RECORD,,")
    return ("\n".join(rows) + "\n").encode("utf-8")


def _dist_info_from_entries(entries: Mapping[str, tuple[bytes, int]]) -> str:
    values = [name for name in entries if name.endswith(".dist-info/METADATA")]
    if len(values) != 1:
        raise BackendError("wheel metadata identity is ambiguous")
    return values[0].split("/", 1)[0]


def _write_wheel(root: Path, target: str, wheel_directory: Path, binary: BinaryIdentity) -> str:
    version = _version(root)
    filename = f"{DIST_NAME}-{version}-py3-none-{TARGET_TAGS[target]}.whl"
    entries = _wheel_entries(root, binary)
    record = _record(entries)
    entries[f"{_dist_info_from_entries(entries)}/RECORD"] = (record, 0o644)
    wheel_directory.mkdir(parents=True, exist_ok=True)
    output = wheel_directory / filename
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_EPOCH))
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(entries):
            content, mode = entries[name]
            archive.writestr(_zip_info(name, mode, epoch), content)
    output.chmod(0o644)
    return filename


def _sdist_paths(root: Path) -> tuple[Path, ...]:
    selected: list[Path] = []
    top_level_files = (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "NOTICE",
        "COMMERCIAL-LICENSE.md",
        "go.mod",
    )
    for relative in top_level_files:
        path = root / relative
        _direct_file(path, relative)
        selected.append(path)
    roots = ("cmd", "envsnap", "hotspot", "internal", "report", "schema", "skills")
    for name in roots:
        directory = root / name
        if not directory.is_dir() or directory.is_symlink():
            raise BackendError(f"sdist source directory is unavailable: {name}")
        selected.extend(
            path
            for path in sorted(directory.rglob("*"))
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts
        )
    package = root / "src" / "agentic_praxis_grimoire"
    for relative in PACKAGE_FILES:
        path = package / relative
        _direct_file(path, f"package source {relative}")
        selected.append(path)
    for relative in (
        "libexec/apg_go_build.py",
        "libexec/apg_python_build_backend.py",
        "libexec/apg_python_distribution.py",
        "libexec/apg_python_publication.py",
    ):
        path = root / relative
        _direct_file(path, relative)
        selected.append(path)
    unique = {path.resolve(): path for path in selected}
    return tuple(sorted(unique.values(), key=lambda path: path.relative_to(root).as_posix()))


def _sdist_metadata(root: Path) -> bytes:
    return _metadata(root).replace(b"Summary:", b"Summary:")


def _write_sdist(root: Path, output_directory: Path) -> str:
    version = _version(root)
    filename = f"{DIST_NAME}-{version}.tar.gz"
    output_directory.mkdir(parents=True, exist_ok=True)
    output = output_directory / filename
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", DEFAULT_EPOCH))
    prefix = f"{DIST_NAME}-{version}"
    members: list[tuple[str, bytes, int]] = [(f"{prefix}/PKG-INFO", _sdist_metadata(root), 0o644)]
    for path in _sdist_paths(root):
        relative = path.relative_to(root).as_posix()
        members.append((f"{prefix}/{relative}", path.read_bytes(), 0o644))
    members.sort(key=lambda item: item[0])
    with output.open("wb") as stream:
        import gzip

        with gzip.GzipFile(fileobj=stream, mode="wb", filename="", mtime=epoch, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for name, content, mode in members:
                    info = tarfile.TarInfo(name)
                    info.type = tarfile.REGTYPE
                    info.mode = mode
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = epoch
                    info.size = len(content)
                    info.pax_headers = {}
                    archive.addfile(info, BytesIO(content))
    output.chmod(0o644)
    return filename


def build_wheel(
    wheel_directory: str,
    config_settings: Mapping[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    del metadata_directory
    root = _root()
    target = _target(_config_value(config_settings, "build-target"))
    with tempfile.TemporaryDirectory(prefix="apg-python-wheel-") as temporary:
        binary = _binary_for_build(root, target, config_settings, Path(temporary))
        return _write_wheel(root, target, Path(wheel_directory), binary)


def build_sdist(
    sdist_directory: str,
    config_settings: Mapping[str, Any] | None = None,
) -> str:
    del config_settings
    return _write_sdist(_root(), Path(sdist_directory))


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: Mapping[str, Any] | None = None,
) -> str:
    root = _root()
    info = _dist_info(root)
    directory = Path(metadata_directory) / info
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "METADATA").write_bytes(_metadata(root))
    (directory / "WHEEL").write_text(
        "Wheel-Version: 1.0\nGenerator: apg-python-build-backend\nRoot-Is-Purelib: false\n",
        encoding="ascii",
    )
    return info


def get_requires_for_build_wheel(config_settings: Mapping[str, Any] | None = None) -> list[str]:
    del config_settings
    return []


def get_requires_for_build_sdist(config_settings: Mapping[str, Any] | None = None) -> list[str]:
    del config_settings
    return []


def get_requires_for_build_editable(config_settings: Mapping[str, Any] | None = None) -> list[str]:
    del config_settings
    return []


def build_editable(
    wheel_directory: str,
    config_settings: Mapping[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    del wheel_directory, config_settings, metadata_directory
    raise BackendError("editable APGR builds are not part of the release contract")
