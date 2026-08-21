"""Deterministic Python source-distribution archive helpers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from io import BytesIO
import gzip
import os
from pathlib import Path
import stat
import sys
import tarfile
import tempfile
from typing import Sequence
import zlib


COMMAND = "apg-normalize-python-sdist"
V05_RELEASE_EPOCH = 1_700_000_000
V06_RELEASE_EPOCH = 1_787_270_400
RELEASE_EPOCHS = (V05_RELEASE_EPOCH, V06_RELEASE_EPOCH)
# The gzip header is the tighter of the gzip uint32 and tar timestamp bounds.
MAX_ARCHIVE_MTIME = 0xFFFFFFFF
_BLOCK_SIZE = 512
_ZERO_BLOCK = b"\0" * _BLOCK_SIZE


class NormalizationError(ValueError):
    """Raised when an input archive cannot be safely normalized."""


@dataclass(frozen=True)
class _Member:
    name: str
    directory: bool
    content: bytes


def _validate_epoch(epoch: int) -> int:
    if isinstance(epoch, bool) or not isinstance(epoch, int):
        raise NormalizationError("epoch must be an integer number of seconds")
    if epoch < 0 or epoch > MAX_ARCHIVE_MTIME:
        raise NormalizationError(
            f"epoch must be between 0 and {MAX_ARCHIVE_MTIME} seconds"
        )
    return epoch


def _validate_paths(input_path: Path, output_path: Path) -> None:
    try:
        same_path = input_path.resolve(strict=True) == output_path.resolve(
            strict=False
        )
    except OSError as error:
        raise NormalizationError(f"cannot resolve input/output paths: {error}") from error
    if same_path:
        raise NormalizationError("input and output paths must be distinct")
    try:
        input_stat = input_path.stat()
    except OSError as error:
        raise NormalizationError(
            f"cannot read input {os.fspath(input_path)}: {error}"
        ) from error
    if not stat.S_ISREG(input_stat.st_mode):
        raise NormalizationError("input must be a regular file")
    try:
        output_stat = output_path.stat()
    except FileNotFoundError:
        output_stat = None
    except OSError as error:
        raise NormalizationError(
            f"cannot inspect output {os.fspath(output_path)}: {error}"
        ) from error
    if output_stat is not None and os.path.samestat(input_stat, output_stat):
        raise NormalizationError("input and output paths must be distinct")
    parent = output_path.parent
    try:
        parent_stat = parent.stat()
    except OSError as error:
        raise NormalizationError(
            f"output directory {os.fspath(parent)} is unavailable: {error}"
        ) from error
    if not stat.S_ISDIR(parent_stat.st_mode):
        raise NormalizationError("output parent must be a directory")


def _decompress_gzip(source: bytes) -> bytes:
    """Decode one trusted, locally built release sdist in memory."""
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        tar_bytes = decoder.decompress(source)
        tar_bytes += decoder.flush()
    except zlib.error as error:
        raise NormalizationError(f"input is not a valid gzip stream: {error}") from error
    if not decoder.eof:
        raise NormalizationError("input gzip stream is truncated")
    if decoder.unused_data or decoder.unconsumed_tail:
        raise NormalizationError("input gzip stream has trailing data")
    if not tar_bytes:
        raise NormalizationError("input gzip stream contains no tar data")
    return tar_bytes


def _tar_size(header: bytes) -> int:
    try:
        value = tarfile.TarInfo.frombuf(
            header,
            encoding="utf-8",
            errors="surrogateescape",
        ).size
    except (TypeError, ValueError, UnicodeError, tarfile.HeaderError) as error:
        raise NormalizationError("tar member has an invalid size field") from error
    if value < 0:
        raise NormalizationError("tar member has a negative size")
    return value


def _validate_tar_end(tar_bytes: bytes) -> None:
    """Require complete 512-byte records and no non-zero trailing bytes."""
    if len(tar_bytes) % _BLOCK_SIZE:
        raise NormalizationError("tar stream is not aligned to 512-byte records")
    offset = 0
    while offset + _BLOCK_SIZE <= len(tar_bytes):
        header = tar_bytes[offset : offset + _BLOCK_SIZE]
        if header == _ZERO_BLOCK:
            if offset + (2 * _BLOCK_SIZE) > len(tar_bytes):
                raise NormalizationError("tar stream has an incomplete end marker")
            if tar_bytes[offset + _BLOCK_SIZE : offset + (2 * _BLOCK_SIZE)] != _ZERO_BLOCK:
                raise NormalizationError("tar stream has an incomplete end marker")
            if any(tar_bytes[offset + (2 * _BLOCK_SIZE) :]):
                raise NormalizationError("tar stream has trailing data")
            return
        size = _tar_size(header)
        data_blocks = (size + (_BLOCK_SIZE - 1)) // _BLOCK_SIZE
        offset += _BLOCK_SIZE + (data_blocks * _BLOCK_SIZE)
        if offset > len(tar_bytes):
            raise NormalizationError("tar member extends beyond the archive")
    raise NormalizationError("tar stream has no complete end marker")


def _member_name(member: tarfile.TarInfo) -> str:
    name = member.name
    if not isinstance(name, str) or not name:
        raise NormalizationError("tar member has an empty name")
    try:
        encoded = name.encode("utf-8", "surrogateescape")
    except UnicodeEncodeError as error:
        raise NormalizationError("tar member name is not valid UTF-8") from error
    if encoded.startswith(b"/"):
        raise NormalizationError(f"tar member has an absolute name: {name!r}")
    if b"\\" in encoded:
        raise NormalizationError(
            f"tar member has a Windows path separator: {name!r}"
        )
    if b"\0" in encoded:
        raise NormalizationError("tar member name contains a NUL byte")
    path_bytes = encoded[:-1] if encoded.endswith(b"/") else encoded
    components = path_bytes.split(b"/")
    if b".." in components:
        raise NormalizationError(f"tar member has a parent component: {name!r}")
    if b"" in components or b"." in components:
        raise NormalizationError(
            f"tar member has a non-canonical path component: {name!r}"
        )
    first = components[0]
    if len(first) >= 2 and first[:1].isalpha() and first[1:2] == b":":
        raise NormalizationError(f"tar member has a Windows drive name: {name!r}")
    if member.isdir():
        if name in (".", "./"):
            raise NormalizationError("tar member has an unusable directory name")
        return name if name.endswith("/") else f"{name}/"
    if name.endswith("/"):
        raise NormalizationError("regular tar member has a directory name")
    return name


def _read_members(tar_bytes: bytes) -> tuple[_Member, ...]:
    _validate_tar_end(tar_bytes)
    members: list[_Member] = []
    names: set[bytes] = set()
    try:
        archive = tarfile.open(
            fileobj=BytesIO(tar_bytes),
            mode="r:",
            errorlevel=2,
            encoding="utf-8",
            errors="surrogateescape",
        )
    except (tarfile.TarError, OSError, UnicodeError) as error:
        raise NormalizationError(f"input tar stream is invalid: {error}") from error
    try:
        for member in archive.getmembers():
            if not (member.isdir() or member.isreg()):
                raise NormalizationError(
                    f"unsupported member type for {member.name!r}"
                )
            if member.isdir() and member.size:
                raise NormalizationError(
                    f"directory member has non-zero content: {member.name!r}"
                )
            name = _member_name(member)
            key = name.rstrip("/").encode("utf-8", "surrogateescape")
            if key in names:
                raise NormalizationError(f"duplicate tar member: {name!r}")
            names.add(key)
            content = b""
            if member.isreg():
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise NormalizationError(
                        f"regular member content is unavailable: {name!r}"
                    )
                with extracted:
                    content = extracted.read()
                if len(content) != member.size:
                    raise NormalizationError(
                        f"regular member content is truncated: {name!r}"
                    )
            members.append(_Member(name, member.isdir(), content))
    except NormalizationError:
        raise
    except (tarfile.TarError, OSError, UnicodeError) as error:
        raise NormalizationError(f"input tar stream is invalid: {error}") from error
    finally:
        archive.close()
    return tuple(sorted(members, key=lambda item: item.name.encode("utf-8", "surrogateescape")))


def _canonical_info(member: _Member, epoch: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(member.name)
    info.type = tarfile.DIRTYPE if member.directory else tarfile.REGTYPE
    info.mode = 0o755 if member.directory else 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = epoch
    info.size = 0 if member.directory else len(member.content)
    info.linkname = ""
    info.devmajor = 0
    info.devminor = 0
    info.pax_headers = {}
    return info


def _write_archive(output_path: Path, members: Sequence[_Member], epoch: int) -> None:
    descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{output_path.name}.", dir=output_path.parent
        )
        temporary_path = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            with gzip.GzipFile(
                fileobj=stream,
                mode="wb",
                filename="",
                mtime=epoch,
                compresslevel=9,
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed,
                    mode="w",
                    format=tarfile.PAX_FORMAT,
                    encoding="utf-8",
                    errors="surrogateescape",
                ) as archive:
                    for member in members:
                        info = _canonical_info(member, epoch)
                        archive.addfile(
                            info,
                            BytesIO(member.content) if not member.directory else None,
                        )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, output_path)
        parent_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        parent_descriptor = os.open(output_path.parent, parent_flags)
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    except NormalizationError:
        raise
    except (OSError, ValueError, UnicodeError, tarfile.TarError) as error:
        raise NormalizationError(
            f"cannot write output {os.fspath(output_path)}: {error}"
        ) from error
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def normalize_archive(
    input_path: Path | str, output_path: Path | str, epoch: int
) -> None:
    """Normalize one gzip-compressed tar source distribution atomically."""
    input_file = Path(input_path)
    output_file = Path(output_path)
    selected_epoch = _validate_epoch(epoch)
    _validate_paths(input_file, output_file)
    try:
        source = input_file.read_bytes()
    except OSError as error:
        raise NormalizationError(
            f"cannot read input {os.fspath(input_file)}: {error}"
        ) from error
    members = _read_members(_decompress_gzip(source))
    _write_archive(output_file, members, selected_epoch)


def _epoch_argument(value: str) -> int:
    try:
        epoch = int(value, 10)
    except ValueError as error:
        raise argparse.ArgumentTypeError("epoch must be an integer number of seconds") from error
    try:
        selected = _validate_epoch(epoch)
    except NormalizationError as error:
        raise argparse.ArgumentTypeError(
            str(error)
        ) from error
    if selected not in RELEASE_EPOCHS:
        raise argparse.ArgumentTypeError(
            "release epoch must be one of "
            + ", ".join(str(epoch) for epoch in RELEASE_EPOCHS)
            + " seconds"
        )
    return selected


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog=COMMAND,
        description="Normalize a gzip-compressed Python sdist deterministically.",
    )
    value.add_argument("--input", required=True, metavar="PATH")
    value.add_argument("--output", required=True, metavar="PATH")
    value.add_argument("--epoch", required=True, metavar="SECONDS", type=_epoch_argument)
    return value


def main(arguments: Sequence[str] | None = None) -> int:
    args = parser().parse_args(arguments)
    if os.environ.get("SOURCE_DATE_EPOCH") != str(args.epoch):
        print(
            f"{COMMAND}: error: SOURCE_DATE_EPOCH must equal {args.epoch}",
            file=sys.stderr,
        )
        return 1
    try:
        normalize_archive(args.input, args.output, args.epoch)
    except NormalizationError as error:
        print(f"{COMMAND}: error: {error}", file=sys.stderr)
        return 1
    return 0
