"""Focused contracts for the v0.6 Python publication bundle."""

from __future__ import annotations

from email.parser import BytesParser
from io import BytesIO
from pathlib import Path
import gzip
import hashlib
import os
import subprocess
import sys
import tarfile
import zipfile

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_python_distribution as distribution  # noqa: E402
import apg_python_publication as publication  # noqa: E402


def _metadata() -> bytes:
    return (
        b"Metadata-Version: 2.4\n"
        b"Name: agentic-praxis-grimoire\n"
        b"Version: 0.6.0\n"
        b"License-Expression: AGPL-3.0-or-later\n"
        b"Requires-Python: >=3.10\n\n"
    )


def _wheel(path: Path, *, suffix: bytes = b"") -> None:
    metadata = _metadata()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("agentic_praxis_grimoire/__init__.py", b"" + suffix)
        archive.writestr(
            "agentic_praxis_grimoire-0.6.0.dist-info/METADATA", metadata
        )
        archive.writestr(
            "agentic_praxis_grimoire-0.6.0.dist-info/WHEEL",
            b"Wheel-Version: 1.0\nTag: py3-none-any\n",
        )
        archive.writestr(
            "agentic_praxis_grimoire-0.6.0.dist-info/RECORD", b""
        )


def _raw_sdist(path: Path, *, seed: int) -> None:
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", mtime=seed) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for name, content in (
                ("agentic_praxis_grimoire-0.6.0/PKG-INFO", _metadata()),
                ("agentic_praxis_grimoire-0.6.0/pyproject.toml", b"[build-system]\n"),
                (
                    "agentic_praxis_grimoire-0.6.0/"
                    "src/agentic_praxis_grimoire/__init__.py",
                    b"",
                ),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mtime = seed
                info.uid = seed
                info.gid = seed
                archive.addfile(info, BytesIO(content))
    path.write_bytes(payload.getvalue())


def _fake_runner(
    calls: list[tuple[str, ...]], *, divergent_wheel: bool = False
):
    def run(
        arguments: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        check: bool = False,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[bytes]:
        del cwd, check
        calls.append(tuple(os.fspath(value) for value in arguments))
        assert env is not None
        assert env["SOURCE_DATE_EPOCH"] == "1787270400"
        if arguments[1:5] == ["-m", "build", "--wheel", "--sdist"]:
            output = Path(arguments[arguments.index("--outdir") + 1])
            output.mkdir(parents=True, exist_ok=False)
            second = "build-b" in output.parts
            _wheel(
                output / publication.WHEEL_NAME,
                suffix=b"different" if divergent_wheel and second else b"",
            )
            _raw_sdist(output / publication.SDIST_NAME, seed=22 if second else 11)
        else:
            assert Path(arguments[1]).name == "apg-normalize-python-sdist"
            source = Path(arguments[arguments.index("--input") + 1])
            target = Path(arguments[arguments.index("--output") + 1])
            epoch = int(arguments[arguments.index("--epoch") + 1])
            distribution.normalize_archive(source, target, epoch)
        return subprocess.CompletedProcess(arguments, 0, b"", b"")

    return run


def test_build_bundle_invokes_normalizer_and_selects_only_reproducible_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        publication.subprocess, "run", _fake_runner(calls)
    )
    output = tmp_path / "publication"
    work = tmp_path / "work"
    work.mkdir()

    result = publication.build_bundle(
        REPOSITORY_ROOT, output, work, Path(sys.executable)
    )

    assert [path.name for path in result] == [
        publication.WHEEL_NAME,
        publication.SDIST_NAME,
        publication.CHECKSUM_NAME,
    ]
    assert sorted(path.name for path in output.iterdir()) == sorted(
        publication.BUNDLE_NAMES
    )
    assert len([call for call in calls if call[1:5] == ("-m", "build", "--wheel", "--sdist")]) == 2
    normalizers = [
        call for call in calls if Path(call[1]).name == "apg-normalize-python-sdist"
    ]
    assert len(normalizers) == 2
    assert all("--epoch" in call and "1787270400" in call for call in normalizers)
    assert not any(path.name.startswith("raw-") for path in output.iterdir())
    publication.validate_bundle(output)

    checksum_lines = (output / publication.CHECKSUM_NAME).read_text().splitlines()
    assert checksum_lines == [
        f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}"
        for name in (publication.WHEEL_NAME, publication.SDIST_NAME)
    ]
    assert all((path.stat().st_mode & 0o777) == 0o600 for path in result)


def test_build_bundle_fails_closed_on_cross_build_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        publication.subprocess,
        "run",
        _fake_runner([], divergent_wheel=True),
    )
    output = tmp_path / "publication"
    work = tmp_path / "work"
    work.mkdir()

    with pytest.raises(publication.PublicationError, match="reproducible"):
        publication.build_bundle(REPOSITORY_ROOT, output, work, Path(sys.executable))

    assert not output.exists()


def test_validate_bundle_rejects_extra_missing_and_mismatched_assets(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    _wheel(bundle / publication.WHEEL_NAME)
    raw = bundle / "raw.tar.gz"
    _raw_sdist(raw, seed=3)
    distribution.normalize_archive(raw, bundle / publication.SDIST_NAME, publication.EPOCH)
    raw.unlink()
    checksums = publication.checksum_bytes(bundle)
    (bundle / publication.CHECKSUM_NAME).write_bytes(checksums)

    publication.validate_bundle(bundle)
    (bundle / "extra.whl").write_bytes(b"unexpected")
    with pytest.raises(publication.PublicationError, match="exactly"):
        publication.validate_bundle(bundle)
    (bundle / "extra.whl").unlink()
    (bundle / publication.CHECKSUM_NAME).write_text(
        "0" * 64 + f"  {publication.WHEEL_NAME}\n"
        + "0" * 64 + f"  {publication.SDIST_NAME}\n"
    )
    with pytest.raises(publication.PublicationError, match="SHA-256"):
        publication.validate_bundle(bundle)


def test_distribution_metadata_is_bound_across_wheel_and_normalized_sdist(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / publication.WHEEL_NAME
    sdist = tmp_path / publication.SDIST_NAME
    raw = tmp_path / "raw.tar.gz"
    _wheel(wheel)
    _raw_sdist(raw, seed=7)
    distribution.normalize_archive(raw, sdist, publication.EPOCH)

    wheel_metadata, sdist_metadata = publication.validate_distributions(wheel, sdist)

    parser = BytesParser()
    assert parser.parsebytes(wheel_metadata)["Name"] == "agentic-praxis-grimoire"
    assert wheel_metadata == sdist_metadata


def test_validate_distributions_rejects_an_unnormalized_sdist(tmp_path: Path) -> None:
    wheel = tmp_path / publication.WHEEL_NAME
    sdist = tmp_path / publication.SDIST_NAME
    _wheel(wheel)
    _raw_sdist(sdist, seed=7)

    with pytest.raises(publication.PublicationError, match="not normalized"):
        publication.validate_distributions(wheel, sdist)


@pytest.mark.parametrize(
    "name",
    ("", "/absolute", "back\\slash", "../escape", "root/./member"),
)
def test_archive_member_path_policy_rejects_unsafe_names(name: str) -> None:
    with pytest.raises(publication.PublicationError, match="unsafe member"):
        publication._safe_archive_name(name)


def test_distribution_contract_rejects_wrong_names_and_metadata(tmp_path: Path) -> None:
    wheel = tmp_path / publication.WHEEL_NAME
    sdist = tmp_path / publication.SDIST_NAME
    raw = tmp_path / "raw.tar.gz"
    _wheel(wheel)
    _raw_sdist(raw, seed=9)
    distribution.normalize_archive(raw, sdist, publication.EPOCH)

    with pytest.raises(publication.PublicationError, match="filenames"):
        publication.validate_distributions(tmp_path / "wrong.whl", sdist)
    with pytest.raises(publication.PublicationError, match="metadata"):
        publication._metadata_contract(
            _metadata().replace(b"Version: 0.6.0", b"Version: 9.9.9"), "wheel"
        )


def test_local_path_and_subprocess_guards_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(publication.PublicationError, match="unavailable"):
        publication._regular(missing, "asset")
    with pytest.raises(publication.PublicationError, match="unavailable"):
        publication._directory(missing, "directory")
    link = tmp_path / "link"
    link.symlink_to(tmp_path)
    with pytest.raises(publication.PublicationError, match="direct directory"):
        publication._directory(link, "directory")

    def fail_run(*_args: object, **_kwargs: object) -> None:
        raise subprocess.CalledProcessError(
            1, ["python", "build"], stderr=b"exact build failure\n"
        )

    monkeypatch.setattr(publication.subprocess, "run", fail_run)
    with pytest.raises(
        publication.PublicationError, match="subprocess failed"
    ) as captured:
        publication._run(
            ["python", "build"],
            source=tmp_path,
            environment={},
            operation="Python distribution build",
        )
    assert "exact build failure" in str(captured.value)


def test_cli_check_and_build_paths_are_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assets = tuple(tmp_path / name for name in publication.BUNDLE_NAMES)
    for path in assets:
        path.write_bytes(path.name.encode("ascii"))
    monkeypatch.setattr(publication, "validate_bundle", lambda _path: assets)
    assert publication.main(["check", "--bundle", str(tmp_path)]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 3

    monkeypatch.setattr(
        publication, "build_bundle", lambda *_arguments: assets
    )
    assert publication.main(
        [
            "build",
            "--source",
            str(tmp_path),
            "--output",
            str(tmp_path / "out"),
            "--work-root",
            str(tmp_path),
        ]
    ) == 0
    assert len(capsys.readouterr().out.splitlines()) == 3

    def reject(_path: Path) -> tuple[Path, Path, Path]:
        raise publication.PublicationError("rejected")

    monkeypatch.setattr(publication, "validate_bundle", reject)
    assert publication.main(["check", "--bundle", str(tmp_path)]) == 1
    assert "rejected" in capsys.readouterr().err


def test_reproducibility_comparison_binds_bytes_and_modes(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for name in publication.BUNDLE_NAMES:
        (first / name).write_bytes(name.encode("ascii"))
        (second / name).write_bytes(name.encode("ascii"))
        (first / name).chmod(0o600)
        (second / name).chmod(0o600)

    publication._compare(first, second)
    (second / publication.CHECKSUM_NAME).chmod(0o400)
    with pytest.raises(publication.PublicationError, match="mode"):
        publication._compare(first, second)


def test_direct_file_and_executable_guards_reject_wrong_kinds(tmp_path: Path) -> None:
    with pytest.raises(publication.PublicationError, match="regular file"):
        publication._regular(tmp_path, "asset")
    inert = tmp_path / "python"
    inert.write_text("#!/bin/sh\n")
    inert.chmod(0o600)
    with pytest.raises(publication.PublicationError, match="executable"):
        publication._executable(inert)


def test_wheel_rejects_duplicate_members(tmp_path: Path) -> None:
    wheel = tmp_path / publication.WHEEL_NAME
    metadata_name = "agentic_praxis_grimoire-0.6.0.dist-info/METADATA"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(metadata_name, _metadata())
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr(metadata_name, _metadata())
    with pytest.raises(publication.PublicationError, match="duplicate"):
        publication._wheel_metadata(wheel)
