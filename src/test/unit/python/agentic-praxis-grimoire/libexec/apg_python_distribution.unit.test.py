"""Focused contracts for deterministic Python sdist normalization."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import argparse
import gzip
import stat
import tarfile
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_python_distribution as distribution  # noqa: E402


EPOCH = 1_700_000_000


def _source_archive(
    path: Path,
    *,
    metadata: int,
    members: tuple[tuple[str, bytes | None, str], ...] = (
        ("package/", None, "directory"),
        ("package/module.py", b"print('stable')\n", "file"),
        ("package/data.bin", b"\x00\x01payload\xff", "file"),
    ),
) -> bytes:
    payload = BytesIO()
    with gzip.GzipFile(
        fileobj=payload,
        mode="wb",
        filename=f"source-{metadata}.tar",
        mtime=metadata,
    ) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name, content, kind in members:
                info = tarfile.TarInfo(name)
                info.mtime = metadata
                info.uid = metadata
                info.gid = metadata + 1
                info.uname = f"user-{metadata}"
                info.gname = f"group-{metadata}"
                info.mode = 0o600 + metadata % 0o77
                if kind == "directory":
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o700 + metadata % 0o77
                else:
                    assert content is not None
                    info.size = len(content)
                    info.pax_headers = {"APG.test": str(metadata)}
                archive.addfile(info, BytesIO(content) if content is not None else None)
    path.write_bytes(payload.getvalue())
    return payload.getvalue()


def _read_normalized(path: Path) -> tuple[bytes, list[tarfile.TarInfo]]:
    with gzip.open(path, "rb") as compressed:
        tar_bytes = compressed.read()
    with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:") as archive:
        members = archive.getmembers()
    return tar_bytes, members


def test_normalization_is_byte_reproducible_and_preserves_payload(tmp_path: Path) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    first_bytes = _source_archive(first, metadata=11)
    second_bytes = _source_archive(second, metadata=22)
    assert first_bytes != second_bytes

    first_output = tmp_path / "first-normalized.tar.gz"
    second_output = tmp_path / "second-normalized.tar.gz"
    distribution.normalize_archive(first, first_output, EPOCH)
    distribution.normalize_archive(second, second_output, EPOCH)

    assert first_output.read_bytes() == second_output.read_bytes()
    tar_bytes, members = _read_normalized(first_output)
    gzip_header = first_output.read_bytes()[:10]
    assert gzip_header[:3] == b"\x1f\x8b\x08"
    assert int.from_bytes(gzip_header[4:8], "little") == EPOCH
    assert not gzip_header[3] & 0x08
    assert [member.name for member in members] == [
        "package",
        "package/data.bin",
        "package/module.py",
    ]
    assert all(member.mtime == EPOCH for member in members)
    assert all(member.uid == 0 and member.gid == 0 for member in members)
    assert all(member.uname == "" and member.gname == "" for member in members)
    assert members[0].mode == 0o755
    assert all(member.mode == 0o644 for member in members[1:])
    assert members[1].pax_headers == {}
    with tarfile.open(fileobj=BytesIO(_read_normalized(first_output)[0]), mode="r:") as archive:
        assert archive.extractfile("package/data.bin").read() == b"\x00\x01payload\xff"


def test_normalization_is_idempotent_and_keeps_input_untouched(tmp_path: Path) -> None:
    source = tmp_path / "source.tar.gz"
    _source_archive(source, metadata=7)
    original = source.read_bytes()
    first_output = tmp_path / "first.tar.gz"
    second_output = tmp_path / "second.tar.gz"

    distribution.normalize_archive(source, first_output, EPOCH)
    distribution.normalize_archive(first_output, second_output, EPOCH)

    assert first_output.read_bytes() == second_output.read_bytes()
    assert source.read_bytes() == original
    assert stat.S_IMODE(first_output.stat().st_mode) == 0o600


def test_normalization_supports_deterministic_pax_long_names(tmp_path: Path) -> None:
    long_name = f"package/{'z' * 120}.py"
    source = tmp_path / "long-name.tar.gz"
    _source_archive(
        source,
        metadata=9,
        members=((long_name, b"payload\n", "file"),),
    )
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"

    distribution.normalize_archive(source, first, EPOCH)
    distribution.normalize_archive(source, second, EPOCH)

    assert first.read_bytes() == second.read_bytes()
    _, members = _read_normalized(first)
    assert [member.name for member in members] == [long_name]
    assert members[0].pax_headers == {"path": long_name}


@pytest.mark.parametrize(
    ("name", "kind", "message"),
    (
        ("/absolute.txt", "file", "absolute"),
        ("../parent.txt", "file", "parent"),
        ("package/../escape.txt", "file", "parent"),
        (r"..\escape.txt", "file", "Windows path separator"),
        ("./package.txt", "file", "non-canonical"),
        ("package/./alias.txt", "file", "non-canonical"),
        ("C:/escape.txt", "file", "Windows drive"),
        ("package/link", "symlink", "unsupported member type"),
    ),
)
def test_rejects_unsafe_or_unsupported_members(
    tmp_path: Path, name: str, kind: str, message: str
) -> None:
    source = tmp_path / "unsafe.tar.gz"
    if kind == "symlink":
        members = ((name, b"target", "symlink"),)
    else:
        members = ((name, b"payload", "file"),)
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", filename="", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            info = tarfile.TarInfo(name)
            info.size = len(members[0][1] or b"")
            if kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "target"
                info.size = 0
            archive.addfile(info, BytesIO(members[0][1] or b""))
    source.write_bytes(payload.getvalue())

    with pytest.raises(distribution.NormalizationError, match=message):
        distribution.normalize_archive(source, tmp_path / "output.tar.gz", EPOCH)


def test_rejects_duplicates_trailing_gzip_data_and_same_output(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.tar.gz"
    _source_archive(
        duplicate,
        metadata=3,
        members=(("same.txt", b"one", "file"), ("same.txt", b"two", "file")),
    )
    with pytest.raises(distribution.NormalizationError, match="duplicate"):
        distribution.normalize_archive(duplicate, tmp_path / "output.tar.gz", EPOCH)

    file_directory_collision = tmp_path / "file-directory-collision.tar.gz"
    _source_archive(
        file_directory_collision,
        metadata=3,
        members=(("same/", None, "directory"), ("same", b"payload", "file")),
    )
    with pytest.raises(distribution.NormalizationError, match="duplicate"):
        distribution.normalize_archive(
            file_directory_collision,
            tmp_path / "collision-output.tar.gz",
            EPOCH,
        )

    trailing = tmp_path / "trailing.tar.gz"
    _source_archive(trailing, metadata=3)
    trailing.write_bytes(trailing.read_bytes() + b"trailing")
    with pytest.raises(distribution.NormalizationError, match="trailing"):
        distribution.normalize_archive(trailing, tmp_path / "output.tar.gz", EPOCH)

    with pytest.raises(distribution.NormalizationError, match="distinct"):
        distribution.normalize_archive(trailing, trailing, EPOCH)


def test_rejects_non_integer_or_out_of_range_epoch(tmp_path: Path) -> None:
    source = tmp_path / "source.tar.gz"
    _source_archive(source, metadata=1)
    assert distribution._validate_epoch(0xFFFFFFFF) == 0xFFFFFFFF
    for epoch in (-1, 0x100000000):
        with pytest.raises(distribution.NormalizationError, match="epoch"):
            distribution.normalize_archive(source, tmp_path / f"{epoch}.tar.gz", epoch)


def test_cli_epoch_preserves_historical_values_and_binds_v08() -> None:
    assert distribution.V05_RELEASE_EPOCH == 1_700_000_000
    assert distribution.V06_RELEASE_EPOCH == 1_787_270_400
    assert distribution.V07_RELEASE_EPOCH == 1_787_529_600
    assert distribution.V08_RELEASE_EPOCH == 1_788_134_400
    assert distribution.V081_RELEASE_EPOCH == 1_788_393_600
    assert distribution._epoch_argument("1700000000") == distribution.V05_RELEASE_EPOCH
    assert distribution._epoch_argument("1787270400") == distribution.V06_RELEASE_EPOCH
    assert distribution._epoch_argument("1787529600") == distribution.V07_RELEASE_EPOCH
    assert distribution._epoch_argument("1788134400") == distribution.V08_RELEASE_EPOCH
    assert distribution._epoch_argument("1788393600") == distribution.V081_RELEASE_EPOCH
    assert distribution.release_epoch("0.5.0") == distribution.V05_RELEASE_EPOCH
    assert distribution.release_epoch("0.6.0") == distribution.V06_RELEASE_EPOCH
    assert distribution.release_epoch("0.7.0") == distribution.V07_RELEASE_EPOCH
    assert distribution.release_epoch("0.8.0+build.1") == distribution.V08_RELEASE_EPOCH
    assert distribution.release_epoch("0.8.1") == distribution.V081_RELEASE_EPOCH
    with pytest.raises(argparse.ArgumentTypeError, match="release epoch"):
        distribution._epoch_argument("1700000001")
    with pytest.raises(distribution.NormalizationError, match="no reproducible release epoch"):
        distribution.release_epoch("0.9.0")
