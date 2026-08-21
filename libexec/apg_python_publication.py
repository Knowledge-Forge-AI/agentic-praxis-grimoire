"""Build and validate the exact v0.6 Python publication bundle."""

from __future__ import annotations

from email.message import Message
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Sequence
import argparse
import hashlib
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

import apg_python_distribution as distribution


COMMAND = "apg-build-python-release-bundle"
EPOCH = 1_787_270_400
VERSION = "0.6.0"
PROJECT_NAME = "agentic-praxis-grimoire"
WHEEL_NAME = "agentic_praxis_grimoire-0.6.0-py3-none-any.whl"
SDIST_NAME = "agentic_praxis_grimoire-0.6.0.tar.gz"
CHECKSUM_NAME = "SHA256SUMS"
BUNDLE_NAMES = (WHEEL_NAME, SDIST_NAME, CHECKSUM_NAME)
_METADATA_FIELDS = ("Name", "Version", "Requires-Python", "License-Expression")
_MAX_SUBPROCESS_STDERR = 4096


class PublicationError(ValueError):
    """A publication bundle failed its exact local contract."""


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
    if not stat.S_ISDIR(status.st_mode) or path.is_symlink() or resolved != path.absolute():
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


def _metadata_contract(payload: bytes, label: str) -> bytes:
    message: Message = BytesParser().parsebytes(payload)
    values = {field: message.get(field) for field in _METADATA_FIELDS}
    expected = {
        "Name": PROJECT_NAME,
        "Version": VERSION,
        "Requires-Python": ">=3.10",
        "License-Expression": "AGPL-3.0-or-later",
    }
    if values != expected:
        _fail(f"{label} metadata does not match the v{VERSION} publication contract")
    return b"".join(
        f"{field}: {values[field]}\n".encode("utf-8") for field in _METADATA_FIELDS
    ) + b"\n"


def _wheel_metadata(path: Path) -> bytes:
    _regular(path, "wheel")
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                _fail("wheel contains duplicate members")
            for info in archive.infolist():
                _safe_archive_name(info.filename.rstrip("/"))
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    _fail("wheel contains a symbolic link")
            metadata_names = [
                name
                for name in names
                if name == f"agentic_praxis_grimoire-{VERSION}.dist-info/METADATA"
            ]
            if len(metadata_names) != 1:
                _fail("wheel must contain one exact METADATA member")
            return archive.read(metadata_names[0])
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise PublicationError("wheel is malformed") from error


def _sdist_metadata(path: Path) -> bytes:
    _regular(path, "normalized sdist")
    expected_root = f"agentic_praxis_grimoire-{VERSION}"
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
                if member.name != expected_root and not member.name.startswith(
                    expected_root + "/"
                ):
                    _fail("normalized sdist has an unexpected archive root")
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


def validate_distributions(wheel: Path, sdist: Path) -> tuple[bytes, bytes]:
    """Validate exact filenames, formats, metadata, and cross-format binding."""

    if wheel.name != WHEEL_NAME or sdist.name != SDIST_NAME:
        _fail(f"distribution filenames do not match the v{VERSION} publication contract")
    with tempfile.TemporaryDirectory(
        prefix=".apg-normalization-check-", dir=sdist.parent
    ) as temporary:
        normalized = Path(temporary) / SDIST_NAME
        try:
            distribution.normalize_archive(sdist, normalized, EPOCH)
        except distribution.NormalizationError as error:
            raise PublicationError("normalized sdist cannot be revalidated") from error
        if normalized.read_bytes() != sdist.read_bytes():
            _fail(f"sdist is not normalized under the v{VERSION} publication contract")
    wheel_contract = _metadata_contract(_wheel_metadata(wheel), "wheel")
    sdist_contract = _metadata_contract(_sdist_metadata(sdist), "normalized sdist")
    if wheel_contract != sdist_contract:
        _fail("wheel and normalized sdist metadata disagree")
    return wheel_contract, sdist_contract


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checksum_bytes(directory: Path) -> bytes:
    """Return canonical checksums for the exact two publication distributions."""

    wheel = directory / WHEEL_NAME
    sdist = directory / SDIST_NAME
    validate_distributions(wheel, sdist)
    return "".join(
        f"{_sha256(directory / name)}  {name}\n"
        for name in (WHEEL_NAME, SDIST_NAME)
    ).encode("ascii")


def validate_bundle(directory: Path) -> tuple[Path, Path, Path]:
    """Validate one exact wheel, normalized sdist, and checksum asset."""

    root = _directory(directory, "publication bundle")
    observed = {entry.name for entry in root.iterdir()}
    if observed != set(BUNDLE_NAMES):
        _fail("publication bundle must contain exactly the three expected assets")
    paths = tuple(root / name for name in BUNDLE_NAMES)
    for path in paths:
        _regular(path, f"publication asset {path.name}")
    expected = checksum_bytes(root)
    if paths[2].read_bytes() != expected:
        _fail("publication bundle SHA-256 manifest does not match its distributions")
    return paths  # type: ignore[return-value]


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
        )
    except OSError as error:
        raise PublicationError(
            f"publication subprocess failed during {operation}: {error}"
        ) from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or b"").decode("utf-8", "replace").strip()
        if len(detail) > _MAX_SUBPROCESS_STDERR:
            detail = detail[-_MAX_SUBPROCESS_STDERR:]
        suffix = f": {detail}" if detail else ""
        raise PublicationError(
            f"publication subprocess failed during {operation}{suffix}"
        ) from error


def _build_once(source: Path, root: Path, python: Path, seed: str) -> Path:
    build_root = root / f"build-{seed}"
    raw = build_root / "raw-dist"
    final = build_root / "publication"
    build_root.mkdir(mode=0o700)
    home = build_root / "home"
    temporary = build_root / "tmp"
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    environment = {
        "HOME": os.fspath(home),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "SOURCE_DATE_EPOCH": str(EPOCH),
        "TMPDIR": os.fspath(temporary),
        "TZ": "UTC",
    }
    _run(
        [
            os.fspath(python),
            "-m",
            "build",
            "--wheel",
            "--sdist",
            "--no-isolation",
            "--outdir",
            os.fspath(raw),
            os.fspath(source),
        ],
        source=source,
        environment=environment,
        operation="Python distribution build",
    )
    if not raw.is_dir() or {entry.name for entry in raw.iterdir()} != {
        WHEEL_NAME,
        SDIST_NAME,
    }:
        _fail("raw build output must contain exactly the expected wheel and sdist")
    final.mkdir(mode=0o700)
    wheel = final / WHEEL_NAME
    wheel.write_bytes((raw / WHEEL_NAME).read_bytes())
    wheel.chmod(0o600)
    normalized = final / SDIST_NAME
    _run(
        [
            os.fspath(python),
            os.fspath(source / "bin" / "apg-normalize-python-sdist"),
            "--input",
            os.fspath(raw / SDIST_NAME),
            "--output",
            os.fspath(normalized),
            "--epoch",
            str(EPOCH),
        ],
        source=source,
        environment=environment,
        operation="sdist normalization",
    )
    manifest = final / CHECKSUM_NAME
    manifest.write_bytes(checksum_bytes(final))
    manifest.chmod(0o600)
    validate_bundle(final)
    return final


def _compare(first: Path, second: Path) -> None:
    for name in BUNDLE_NAMES:
        left = first / name
        right = second / name
        if left.read_bytes() != right.read_bytes():
            _fail(f"publication asset is not byte reproducible: {name}")
        if stat.S_IMODE(left.stat().st_mode) != stat.S_IMODE(right.stat().st_mode):
            _fail(f"publication asset mode is not reproducible: {name}")


def build_bundle(
    source: Path, output: Path, work_root: Path, python: Path
) -> tuple[Path, Path, Path]:
    """Build twice, normalize twice, compare, and select one immutable bundle."""

    source_root = _directory(source, "publication source")
    work = _directory(work_root, "publication work root")
    python_command = _executable(python)
    if output.exists() or output.is_symlink():
        _fail("publication output must not already exist")
    try:
        output_parent = output.parent.resolve(strict=True)
    except OSError as error:
        raise PublicationError("publication output parent is unavailable") from error
    if output_parent != output.parent.absolute() or output.parent.is_symlink():
        _fail("publication output parent must be one real direct directory")
    if work.stat().st_dev != output_parent.stat().st_dev:
        _fail("publication output and work root must share one filesystem")
    version = source_root / "src" / "agentic_praxis_grimoire" / "VERSION"
    normalizer = source_root / "bin" / "apg-normalize-python-sdist"
    _regular(version, "package version resource")
    _regular(normalizer, "sdist normalizer")
    if version.read_text(encoding="utf-8").strip() != VERSION:
        _fail(f"package version resource is not exact v{VERSION}")
    if any((work / f"build-{seed}").exists() for seed in ("a", "b")):
        _fail("publication build roots must not already exist")

    first = _build_once(source_root, work, python_command, "a")
    second = _build_once(source_root, work, python_command, "b")
    _compare(first, second)
    os.replace(first, output)
    return validate_bundle(output)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog=COMMAND,
        description=f"Build or validate the exact normalized v{VERSION} publication bundle.",
    )
    subcommands = command.add_subparsers(dest="subcommand", required=True)
    build = subcommands.add_parser("build", help="build twice and select exact bytes")
    build.add_argument("--source", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--work-root", required=True, type=Path)
    build.add_argument("--python", default=Path(sys.executable), type=Path)
    check = subcommands.add_parser("check", help="validate one exact bundle")
    check.add_argument("--bundle", required=True, type=Path)
    return command


def main(arguments: Sequence[str] | None = None) -> int:
    args = parser().parse_args(arguments)
    try:
        if args.subcommand == "build":
            paths = build_bundle(args.source, args.output, args.work_root, args.python)
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
