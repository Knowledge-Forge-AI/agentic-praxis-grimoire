"""Integration coverage for the deterministic distribution helper."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import gzip
import os
import sys
import tarfile

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_python_distribution as distribution  # noqa: E402


def _archive(path: Path, members: tuple[tuple[str, str], ...]) -> None:
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", filename="input.tar", mtime=7) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            for name, kind in members:
                info = tarfile.TarInfo(name)
                if kind == "symlink":
                    info.type = tarfile.SYMTYPE
                    info.linkname = "target"
                    archive.addfile(info)
                else:
                    info.size = len(b"payload")
                    archive.addfile(info, BytesIO(b"payload"))
    path.write_bytes(payload.getvalue())


def test_helper_normalizes_and_rejects_archive_boundaries(tmp_path: Path) -> None:
    valid = tmp_path / "valid.tar.gz"
    _archive(valid, (("package/data.txt", "file"),))
    output = tmp_path / "normalized.tar.gz"
    distribution.normalize_archive(valid, output, 1_700_000_000)
    assert output.is_file()

    long_name = f"package/{'z' * 120}.py"
    long_source = tmp_path / "long-source.tar.gz"
    _archive(long_source, ((long_name, "file"),))
    long_output = tmp_path / "long-output.tar.gz"
    distribution.normalize_archive(long_source, long_output, 1_700_000_000)
    with tarfile.open(long_output, mode="r:gz") as archive:
        assert [member.name for member in archive.getmembers()] == [long_name]

    cases = (
        ("parent", (("../escape.txt", "file"),), "parent"),
        ("windows", ((r"..\escape.txt", "file"),), "Windows path separator"),
        ("alias", (("package/./alias.txt", "file"),), "non-canonical"),
        ("drive", (("C:/escape.txt", "file"),), "Windows drive"),
        ("duplicate", (("same.txt", "file"), ("same.txt", "file")), "duplicate"),
        ("symlink", (("package/link", "symlink"),), "unsupported member type"),
    )
    for label, members, message in cases:
        source = tmp_path / f"{label}.tar.gz"
        _archive(source, members)
        with pytest.raises(distribution.NormalizationError, match=message):
            distribution.normalize_archive(
                source,
                tmp_path / f"{label}-output.tar.gz",
                1_700_000_000,
            )

    trailing = tmp_path / "trailing.tar.gz"
    _archive(trailing, (("package/data.txt", "file"),))
    trailing.write_bytes(trailing.read_bytes() + b"trailing")
    with pytest.raises(distribution.NormalizationError, match="trailing"):
        distribution.normalize_archive(
            trailing,
            tmp_path / "trailing-output.tar.gz",
            1_700_000_000,
        )

    with pytest.raises(distribution.NormalizationError, match="output directory"):
        distribution.normalize_archive(
            valid,
            tmp_path / "missing" / "output.tar.gz",
            1_700_000_000,
        )


def test_helper_rejects_unrepresentable_epoch_before_writing(tmp_path: Path) -> None:
    valid = tmp_path / "valid.tar.gz"
    _archive(valid, (("package/data.txt", "file"),))
    with pytest.raises(distribution.NormalizationError, match="epoch"):
        distribution.normalize_archive(valid, tmp_path / "output.tar.gz", 0x100000000)


def test_helper_rejects_path_stream_and_type_boundaries(tmp_path: Path) -> None:
    valid = tmp_path / "valid.tar.gz"
    _archive(valid, (("package/data.txt", "file"),))

    with pytest.raises(distribution.NormalizationError, match="integer"):
        distribution.normalize_archive(valid, tmp_path / "bool.tar.gz", True)
    with pytest.raises(distribution.NormalizationError, match="distinct"):
        distribution.normalize_archive(valid, valid, 1_700_000_000)
    with pytest.raises(distribution.NormalizationError, match="regular file"):
        distribution.normalize_archive(tmp_path, tmp_path / "directory.tar.gz", 1_700_000_000)

    hard_link = tmp_path / "hard-link.tar.gz"
    os.link(valid, hard_link)
    with pytest.raises(distribution.NormalizationError, match="distinct"):
        distribution.normalize_archive(valid, hard_link, 1_700_000_000)

    output_parent = tmp_path / "output-parent"
    output_parent.write_text("not a directory", encoding="utf-8")
    with pytest.raises(distribution.NormalizationError, match="cannot inspect output"):
        distribution.normalize_archive(
            valid,
            output_parent / "output.tar.gz",
            1_700_000_000,
        )

    invalid_gzip = tmp_path / "invalid.tar.gz"
    invalid_gzip.write_bytes(b"not gzip")
    with pytest.raises(distribution.NormalizationError, match="valid gzip"):
        distribution.normalize_archive(
            invalid_gzip,
            tmp_path / "invalid-output.tar.gz",
            1_700_000_000,
        )

    truncated = tmp_path / "truncated.tar.gz"
    truncated.write_bytes(valid.read_bytes()[:-4])
    with pytest.raises(distribution.NormalizationError, match="truncated"):
        distribution.normalize_archive(
            truncated,
            tmp_path / "truncated-output.tar.gz",
            1_700_000_000,
        )


def test_helper_rejects_malformed_tar_end_markers() -> None:
    with pytest.raises(distribution.NormalizationError, match="aligned"):
        distribution._validate_tar_end(b"unaligned")
    with pytest.raises(distribution.NormalizationError, match="incomplete end marker"):
        distribution._validate_tar_end(b"\0" * 512)
    with pytest.raises(distribution.NormalizationError, match="trailing data"):
        distribution._validate_tar_end((b"\0" * 1024) + b"\1" + (b"\0" * 511))
