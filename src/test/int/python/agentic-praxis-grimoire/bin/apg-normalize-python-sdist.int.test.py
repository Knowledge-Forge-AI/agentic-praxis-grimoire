"""Integration contracts for the sdist normalizer wrapper."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import gzip
import os
import subprocess
import tarfile
import sys

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-normalize-python-sdist"


def _source_archive(path: Path) -> None:
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", filename="input.tar", mtime=5) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
            info = tarfile.TarInfo("package/data.txt")
            info.size = len(b"payload\n")
            info.mtime = 5
            info.uid = 12
            info.gid = 13
            info.uname = "source-user"
            info.gname = "source-group"
            info.pax_headers = {"APG.test": "input"}
            archive.addfile(info, BytesIO(b"payload\n"))
    path.write_bytes(payload.getvalue())


def _member_archive(path: Path, members: tuple[tuple[str, str], ...]) -> None:
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", filename="", mtime=5) as compressed:
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


def run_command(
    *arguments: str,
    source_date_epoch: str | None = "1700000000",
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["LC_ALL"] = "C"
    environment["LANG"] = "C"
    if source_date_epoch is None:
        environment.pop("SOURCE_DATE_EPOCH", None)
    else:
        environment["SOURCE_DATE_EPOCH"] = source_date_epoch
    return subprocess.run(
        [sys.executable, str(COMMAND), *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_wrapper_normalizes_archive_and_reports_help(tmp_path: Path) -> None:
    source = tmp_path / "source.tar.gz"
    output = tmp_path / "output.tar.gz"
    _source_archive(source)

    result = run_command(
        "--input",
        str(source),
        "--output",
        str(output),
        "--epoch",
        "1787270400",
        source_date_epoch="1787270400",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""
    assert output.is_file()

    help_result = run_command("--help")
    assert help_result.returncode == 0
    assert "--input PATH" in help_result.stdout
    assert "--output PATH" in help_result.stdout
    assert "--epoch SECONDS" in help_result.stdout


def test_wrapper_returns_exit_one_without_mutating_input_on_normalization_error(tmp_path: Path) -> None:
    source = tmp_path / "invalid.tar.gz"
    source.write_bytes(b"not a gzip archive")
    original = source.read_bytes()
    output = tmp_path / "output.tar.gz"

    result = run_command(
        "--input",
        str(source),
        "--output",
        str(output),
        "--epoch",
        "1700000000",
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("apg-normalize-python-sdist: error: ")
    assert source.read_bytes() == original
    assert not output.exists()


def test_wrapper_rejects_same_input_and_output_with_exit_one(tmp_path: Path) -> None:
    source = tmp_path / "source.tar.gz"
    _source_archive(source)
    result = run_command(
        "--input",
        str(source),
        "--output",
        str(source),
        "--epoch",
        "1700000000",
    )
    assert result.returncode == 1
    assert "distinct" in result.stderr


def test_wrapper_rejects_archive_and_argument_error_boundaries(tmp_path: Path) -> None:
    valid = tmp_path / "valid.tar.gz"
    _source_archive(valid)
    invalid_epoch = run_command(
        "--input",
        str(valid),
        "--output",
        str(tmp_path / "epoch.tar.gz"),
        "--epoch",
        str(0x100000000),
    )
    assert invalid_epoch.returncode == 2
    assert "epoch must be between" in invalid_epoch.stderr

    wrong_release_epoch = run_command(
        "--input",
        str(valid),
        "--output",
        str(tmp_path / "wrong-release-epoch.tar.gz"),
        "--epoch",
        "1700000001",
    )
    assert wrong_release_epoch.returncode == 2
    assert "release epoch must be one of 1700000000, 1787270400, 1787529600, 1788134400 seconds" in wrong_release_epoch.stderr

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
        _member_archive(source, members)
        result = run_command(
            "--input",
            str(source),
            "--output",
            str(tmp_path / f"{label}-output.tar.gz"),
            "--epoch",
            "1700000000",
        )
        assert result.returncode == 1
        assert message in result.stderr

    missing_parent = run_command(
        "--input",
        str(valid),
        "--output",
        str(tmp_path / "missing" / "output.tar.gz"),
        "--epoch",
        "1700000000",
    )
    assert missing_parent.returncode == 1
    assert "output directory" in missing_parent.stderr

    missing_environment = run_command(
        "--input",
        str(valid),
        "--output",
        str(tmp_path / "missing-environment.tar.gz"),
        "--epoch",
        "1700000000",
        source_date_epoch=None,
    )
    assert missing_environment.returncode == 1
    assert "SOURCE_DATE_EPOCH must equal 1700000000" in missing_environment.stderr

    mismatched_environment = run_command(
        "--input",
        str(valid),
        "--output",
        str(tmp_path / "mismatched-environment.tar.gz"),
        "--epoch",
        "1700000000",
        source_date_epoch="1700000001",
    )
    assert mismatched_environment.returncode == 1
    assert "SOURCE_DATE_EPOCH must equal 1700000000" in mismatched_environment.stderr


def test_wrapper_normalizes_pax_long_name(tmp_path: Path) -> None:
    long_name = f"package/{'z' * 120}.py"
    source = tmp_path / "long-source.tar.gz"
    output = tmp_path / "long-output.tar.gz"
    _member_archive(source, ((long_name, "file"),))

    result = run_command(
        "--input",
        str(source),
        "--output",
        str(output),
        "--epoch",
        "1700000000",
    )

    assert result.returncode == 0, result.stderr
    with tarfile.open(output, mode="r:gz") as archive:
        assert [member.name for member in archive.getmembers()] == [long_name]
