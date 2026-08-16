"""Wrapper boundary for the exact Python publication bundle command."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import gzip
import hashlib
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import warnings
import zipfile

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-build-python-release-bundle"
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_python_distribution as distribution  # noqa: E402
import apg_python_publication as publication  # noqa: E402


def _metadata() -> bytes:
    return (
        b"Metadata-Version: 2.4\n"
        b"Name: agentic-praxis-grimoire\n"
        b"Version: 0.5.0\n"
        b"License-Expression: AGPL-3.0-or-later\n"
        b"Requires-Python: >=3.10\n\n"
    )


def _bundle(root: Path) -> None:
    root.mkdir()
    with zipfile.ZipFile(root / publication.WHEEL_NAME, "w") as archive:
        archive.writestr("agentic_praxis_grimoire/__init__.py", b"")
        archive.writestr(
            "agentic_praxis_grimoire-0.5.0.dist-info/METADATA", _metadata()
        )
    raw = root.parent / "raw.tar.gz"
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", mtime=1) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            info = tarfile.TarInfo("agentic_praxis_grimoire-0.5.0/PKG-INFO")
            info.size = len(_metadata())
            archive.addfile(info, BytesIO(_metadata()))
    raw.write_bytes(payload.getvalue())
    distribution.normalize_archive(raw, root / publication.SDIST_NAME, publication.EPOCH)
    (root / publication.CHECKSUM_NAME).write_bytes(publication.checksum_bytes(root))


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [os.fspath(COMMAND), *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _write_manifest(root: Path) -> None:
    (root / publication.CHECKSUM_NAME).write_text(
        "".join(
            f"{hashlib.sha256((root / name).read_bytes()).hexdigest()}  {name}\n"
            for name in (publication.WHEEL_NAME, publication.SDIST_NAME)
        ),
        encoding="ascii",
    )


def test_wrapper_reports_help_and_validates_one_exact_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    _bundle(bundle)

    help_result = _run("--help")
    checked = _run("check", "--bundle", os.fspath(bundle))

    assert help_result.returncode == 0
    assert "build or validate" in help_result.stdout.lower()
    assert checked.returncode == 0
    assert publication.WHEEL_NAME in checked.stdout
    assert publication.SDIST_NAME in checked.stdout
    assert publication.CHECKSUM_NAME in checked.stdout


def test_wrapper_rejects_an_incomplete_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    result = _run("check", "--bundle", os.fspath(bundle))

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("apg-build-python-release-bundle: error: ")


def test_bundle_validation_rejects_filesystem_and_artifact_tampering(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _bundle(source)
    publication.validate_bundle(source)

    extra = tmp_path / "extra"
    shutil.copytree(source, extra)
    (extra / "unexpected.whl").write_bytes(b"unexpected")
    with pytest.raises(publication.PublicationError, match="exactly"):
        publication.validate_bundle(extra)

    mismatch = tmp_path / "mismatch"
    shutil.copytree(source, mismatch)
    (mismatch / publication.CHECKSUM_NAME).write_bytes(b"wrong\n")
    with pytest.raises(publication.PublicationError, match="SHA-256"):
        publication.validate_bundle(mismatch)

    unnormalized = tmp_path / "unnormalized"
    shutil.copytree(source, unnormalized)
    raw = tmp_path / "raw.tar.gz"
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", mtime=7) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            info = tarfile.TarInfo("agentic_praxis_grimoire-0.5.0/PKG-INFO")
            info.size = len(_metadata())
            info.uid = 7
            info.gid = 7
            info.mtime = 7
            archive.addfile(info, BytesIO(_metadata()))
    raw.write_bytes(payload.getvalue())
    (unnormalized / publication.SDIST_NAME).write_bytes(raw.read_bytes())
    _write_manifest(unnormalized)
    with pytest.raises(publication.PublicationError, match="not normalized"):
        publication.validate_bundle(unnormalized)

    linked = tmp_path / "linked"
    shutil.copytree(source, linked)
    (linked / publication.WHEEL_NAME).unlink()
    (linked / publication.WHEEL_NAME).symlink_to(source / publication.WHEEL_NAME)
    with pytest.raises(publication.PublicationError, match="regular file"):
        publication.validate_bundle(linked)

    wrong_metadata = tmp_path / "wrong-metadata"
    shutil.copytree(source, wrong_metadata)
    with zipfile.ZipFile(
        wrong_metadata / publication.WHEEL_NAME, "w"
    ) as archive:
        archive.writestr(
            "agentic_praxis_grimoire-0.5.0.dist-info/METADATA",
            _metadata().replace(b"Version: 0.5.0", b"Version: 9.9.9"),
        )
    _write_manifest(wrong_metadata)
    with pytest.raises(publication.PublicationError, match="metadata"):
        publication.validate_bundle(wrong_metadata)


def test_bundle_validation_rejects_archive_identity_tampering(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _bundle(source)

    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(source, target_is_directory=True)
    with pytest.raises(publication.PublicationError, match="direct directory"):
        publication.validate_bundle(linked_root)

    with pytest.raises(publication.PublicationError, match="filenames"):
        publication.validate_distributions(
            source / "wrong.whl", source / publication.SDIST_NAME
        )

    duplicate = tmp_path / "duplicate"
    shutil.copytree(source, duplicate)
    with zipfile.ZipFile(duplicate / publication.WHEEL_NAME, "a") as archive:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            archive.writestr(
                "agentic_praxis_grimoire-0.5.0.dist-info/METADATA", _metadata()
            )
    with pytest.raises(publication.PublicationError, match="duplicate"):
        publication.validate_bundle(duplicate)

    linked_member = tmp_path / "linked-member"
    shutil.copytree(source, linked_member)
    with zipfile.ZipFile(linked_member / publication.WHEEL_NAME, "w") as archive:
        archive.writestr(
            "agentic_praxis_grimoire-0.5.0.dist-info/METADATA", _metadata()
        )
        info = zipfile.ZipInfo("agentic_praxis_grimoire/link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"target")
    with pytest.raises(publication.PublicationError, match="symbolic link"):
        publication.validate_bundle(linked_member)

    missing_metadata = tmp_path / "missing-metadata"
    shutil.copytree(source, missing_metadata)
    with zipfile.ZipFile(
        missing_metadata / publication.WHEEL_NAME, "w"
    ) as archive:
        archive.writestr("agentic_praxis_grimoire/__init__.py", b"")
    with pytest.raises(publication.PublicationError, match="METADATA"):
        publication.validate_bundle(missing_metadata)

    malformed = tmp_path / "malformed"
    shutil.copytree(source, malformed)
    (malformed / publication.WHEEL_NAME).write_bytes(b"not a zip archive")
    with pytest.raises(publication.PublicationError, match="malformed"):
        publication.validate_bundle(malformed)

    unsafe_member = tmp_path / "unsafe-member"
    shutil.copytree(source, unsafe_member)
    with zipfile.ZipFile(unsafe_member / publication.WHEEL_NAME, "w") as archive:
        archive.writestr(
            "agentic_praxis_grimoire-0.5.0.dist-info/METADATA", _metadata()
        )
        archive.writestr("/absolute", b"")
    with pytest.raises(publication.PublicationError, match="unsafe member"):
        publication.validate_bundle(unsafe_member)


def test_publication_subprocess_diagnostics_preserve_bounded_causes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "work"
    output = tmp_path / "output"
    work.mkdir()
    output.mkdir()
    with pytest.raises(publication.PublicationError, match="must not already exist"):
        publication.build_bundle(
            REPOSITORY_ROOT, output, work, Path(sys.executable)
        )

    def os_failure(*_args: object, **_kwargs: object) -> None:
        raise OSError("unavailable executable")

    monkeypatch.setattr(publication.subprocess, "run", os_failure)
    with pytest.raises(publication.PublicationError, match="unavailable executable"):
        publication._run(
            ["python", "build"],
            source=tmp_path,
            environment={},
            operation="build",
        )

    failures = iter(
        (
            subprocess.CalledProcessError(1, ["python"], stderr=b"x" * 5000),
            subprocess.CalledProcessError(1, ["python"], stderr=b""),
        )
    )

    def command_failure(*_args: object, **_kwargs: object) -> None:
        raise next(failures)

    monkeypatch.setattr(publication.subprocess, "run", command_failure)
    # This private seam isolates child-failure rendering without running a build.
    with pytest.raises(publication.PublicationError) as bounded:
        publication._run(
            ["python", "build"],
            source=tmp_path,
            environment={},
            operation="build",
        )
    assert len(str(bounded.value)) < publication._MAX_SUBPROCESS_STDERR + 100
    with pytest.raises(publication.PublicationError, match="during build$"):
        publication._run(
            ["python", "build"],
            source=tmp_path,
            environment={},
            operation="build",
        )


def test_publication_selection_rejects_release_root_drift(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for name in publication.BUNDLE_NAMES:
        (first / name).write_bytes(name.encode("ascii"))
        (second / name).write_bytes(name.encode("ascii"))
        (first / name).chmod(0o600)
        (second / name).chmod(0o600)

    (second / publication.WHEEL_NAME).write_bytes(b"drift")
    with pytest.raises(publication.PublicationError, match="byte reproducible"):
        publication._compare(first, second)
    (second / publication.WHEEL_NAME).write_bytes(
        (first / publication.WHEEL_NAME).read_bytes()
    )
    (second / publication.SDIST_NAME).chmod(0o400)
    with pytest.raises(publication.PublicationError, match="mode"):
        publication._compare(first, second)

    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(publication.PublicationError, match="output parent"):
        publication.build_bundle(
            REPOSITORY_ROOT,
            tmp_path / "missing-parent" / "publication",
            work,
            Path(sys.executable),
        )

    matching_source = tmp_path / "matching-source"
    matching_version = (
        matching_source / "src" / "agentic_praxis_grimoire" / "VERSION"
    )
    matching_version.parent.mkdir(parents=True)
    matching_version.write_text("0.5.0\n", encoding="utf-8")
    matching_normalizer = matching_source / "bin" / "apg-normalize-python-sdist"
    matching_normalizer.parent.mkdir()
    matching_normalizer.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (work / "build-a").mkdir()
    with pytest.raises(
        publication.PublicationError, match="build roots must not already exist"
    ):
        publication.build_bundle(
            matching_source,
            tmp_path / "publication",
            work,
            Path(sys.executable),
        )

    wrong_source = tmp_path / "wrong-source"
    version = wrong_source / "src" / "agentic_praxis_grimoire" / "VERSION"
    version.parent.mkdir(parents=True)
    version.write_text("9.9.9\n", encoding="utf-8")
    normalizer = wrong_source / "bin" / "apg-normalize-python-sdist"
    normalizer.parent.mkdir()
    normalizer.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    clean_work = tmp_path / "clean-work"
    clean_work.mkdir()
    with pytest.raises(publication.PublicationError, match="not exact v0.5.0"):
        publication.build_bundle(
            wrong_source,
            tmp_path / "wrong-publication",
            clean_work,
            Path(sys.executable),
        )
