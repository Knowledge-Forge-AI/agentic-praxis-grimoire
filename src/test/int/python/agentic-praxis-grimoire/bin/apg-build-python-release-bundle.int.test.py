"""Integration contracts for the APG100 Python distribution wrapper."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import gzip
import os
import subprocess
import sys
import tarfile
import zipfile

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-build-python-release-bundle"
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_go_build as go_build  # noqa: E402
import apg_python_build_backend as backend  # noqa: E402
import apg_python_distribution as distribution  # noqa: E402
import apg_python_publication as publication  # noqa: E402


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


def _current_bundle(root: Path) -> Path:
    bundle = root / "bundle"
    bundle.mkdir()
    version, corpus = go_build.identities(REPOSITORY_ROOT)
    for target in publication.SUPPORTED_TARGETS:
        binary = root / f"{target.replace('/', '-')}.apgr"
        binary.write_bytes(f"fake-{target}".encode())
        manifest = go_build._manifest(
            target=target,
            version=version,
            corpus=corpus,
            binary=binary.read_bytes(),
        )
        identity = backend.BinaryIdentity(binary, go_build.render_manifest(manifest), target)
        backend._write_wheel(REPOSITORY_ROOT, target, bundle, identity)
    backend._write_sdist(REPOSITORY_ROOT, bundle)
    (bundle / publication.CHECKSUM_NAME).write_bytes(publication.checksum_bytes(bundle))
    return bundle


def _historical_bundle(root: Path) -> Path:
    bundle = root / "historical"
    bundle.mkdir()
    metadata = (
        b"Metadata-Version: 2.4\n"
        b"Name: agentic-praxis-grimoire\n"
        b"Version: 0.6.0\n"
        b"License-Expression: AGPL-3.0-or-later\n"
        b"Requires-Python: >=3.10\n\n"
    )
    with zipfile.ZipFile(bundle / publication.HISTORICAL_V06_WHEEL_NAME, "w") as archive:
        archive.writestr("agentic_praxis_grimoire/__init__.py", b"")
        archive.writestr("agentic_praxis_grimoire-0.6.0.dist-info/METADATA", metadata)
    payload = BytesIO()
    with gzip.GzipFile(fileobj=payload, mode="wb", mtime=1) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            info = tarfile.TarInfo("agentic_praxis_grimoire-0.6.0/PKG-INFO")
            info.size = len(metadata)
            archive.addfile(info, BytesIO(metadata))
    raw = root / "raw.tar.gz"
    raw.write_bytes(payload.getvalue())
    distribution.normalize_archive(
        raw,
        bundle / publication.HISTORICAL_V06_SDIST_NAME,
        distribution.V06_RELEASE_EPOCH,
    )
    raw.unlink()
    (bundle / publication.CHECKSUM_NAME).write_bytes(
        publication.checksum_bytes(bundle, historical=True)
    )
    return bundle


def test_wrapper_help_and_current_bundle_check(tmp_path: Path) -> None:
    bundle = _current_bundle(tmp_path)
    help_result = _run("--help")
    checked = _run("check", "--bundle", os.fspath(bundle))
    assert help_result.returncode == 0
    assert "platform" in help_result.stdout.lower()
    assert checked.returncode == 0
    assert publication.SDIST_NAME in checked.stdout
    assert all(name in checked.stdout for name in publication.WHEEL_NAMES)


def test_wrapper_preserves_historical_v06_check_surface(tmp_path: Path) -> None:
    bundle = _historical_bundle(tmp_path)
    checked = _run("check-v06", "--bundle", os.fspath(bundle))
    assert checked.returncode == 0
    assert publication.HISTORICAL_V06_WHEEL_NAME in checked.stdout
    assert publication.HISTORICAL_V06_SDIST_NAME in checked.stdout


def test_wrapper_rejects_checksum_and_asset_tampering(tmp_path: Path) -> None:
    bundle = _current_bundle(tmp_path)
    (bundle / publication.CHECKSUM_NAME).write_text("wrong\n", encoding="ascii")
    result = _run("check", "--bundle", os.fspath(bundle))
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("apg-build-python-release-bundle: error: ")

def test_wrapper_rejects_incomplete_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "empty"
    bundle.mkdir()
    result = _run("check", "--bundle", os.fspath(bundle))
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("apg-build-python-release-bundle: error: ")
