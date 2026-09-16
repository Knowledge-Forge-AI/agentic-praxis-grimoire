"""Finite archive input and verification work, before payload decompression."""

from pathlib import Path
import os
from types import SimpleNamespace
import zipfile

import pytest

from agent_phase import archive, archive_snapshot, archive_verify
from test_agent_phase_archive_receipts import _canonical_archive


def test_total_input_limit_preserves_full_local_evidence(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "run"
    source.mkdir()
    for name in archive_snapshot.CORE:
        (source / name).write_bytes(b"{}")
    (source / "evidence.bin").write_bytes(b"0123456789")
    monkeypatch.setattr(archive_snapshot, "MAX_TOTAL_BYTES", 12)
    monkeypatch.setattr(archive_snapshot, "MAX_FILE_BYTES", 10)
    with pytest.raises(archive.ArchiveError, match="RUN_ARCHIVE_LIMIT"):
        archive_snapshot.Snapshot(source)
    assert (source / "evidence.bin").read_bytes() == b"0123456789"


def test_member_length_mismatch_rejected_before_crc_decompression(tmp_path: Path, monkeypatch) -> None:
    source, target = _canonical_archive(tmp_path)
    replacement = tmp_path / "replacement.zip"
    with zipfile.ZipFile(target) as original, zipfile.ZipFile(replacement, "w") as changed:
        for info in original.infolist():
            data = original.read(info.filename)
            if info.filename == f"{source.name}/request.json":
                data += b" "
            changed.writestr(info, data)
    target.unlink()
    replacement.rename(target)
    def forbidden_crc(*args):
        raise AssertionError("invalid member lengths reached decompression")
    monkeypatch.setattr(zipfile.ZipFile, "testzip", forbidden_crc)
    with pytest.raises(archive_verify.VerificationError):
        archive_verify.verify_source_archive(source)


def test_archive_readback_rejects_oversized_before_read(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "archive.zip"
    target.write_bytes(b"long")
    monkeypatch.setattr(archive, "MAX_ARCHIVE_BYTES", 3)
    with pytest.raises(archive.ArchiveError, match="RUN_ARCHIVE_LIMIT"):
        archive._digest(target)


def test_excluded_runtime_root_can_change_type_during_packaging(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "run"
    source.mkdir()
    for name in archive_snapshot.CORE:
        (source / name).write_bytes(b"{}")
    runtime = source / "workers" / "parent" / "serena-home"
    runtime.mkdir(parents=True)
    directory = SimpleNamespace(path=source, leaf=source.name,
        archive_path=tmp_path / "run.zip", archive_temporary_path=tmp_path / "run.zip.tmp")
    original = zipfile.ZipFile.testzip
    def mutate_excluded(bundle):
        result = original(bundle)
        runtime.rmdir()
        os.mkfifo(runtime)
        return result
    monkeypatch.setattr(zipfile.ZipFile, "testzip", mutate_excluded)
    assert archive.create(directory) == directory.archive_path
    with zipfile.ZipFile(directory.archive_path) as bundle:
        assert not any("serena-home" in name for name in bundle.namelist())
