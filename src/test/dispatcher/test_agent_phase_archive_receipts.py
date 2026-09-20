from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from agent_phase import archive as archive_module
from agent_phase import archive_snapshot as snapshot_module
from agent_phase import result_repair
from agent_phase.resume_validation import ResumeError


def _source(tmp_path: Path, *, status: str = "in_progress") -> tuple[Path, SimpleNamespace]:
    source = tmp_path / "RUN--20260908T020000000000Z"
    source.mkdir()
    target = source.parent / f"{source.name}.zip"
    receipt = archive_module.receipt_path(target)
    archive_record = {
        "attempted": True,
        "path": str(target),
        "status": status,
        "succeeded": status == "succeeded",
        "failure": None,
    }
    if status == "in_progress":
        archive_record["receipt_path"] = str(receipt)
    payload = {
        "run_id": source.name,
        "outcome": "completed",
        "complete": True,
        "archive": archive_record,
    }
    for name, value in {
        "request.json": {"phase": "archive-receipt"},
        "resolved.json": {"schema": "test"},
        "state.json": payload,
        "result.json": payload,
    }.items():
        (source / name).write_text(
            json.dumps(value, sort_keys=True) + "\n", encoding="utf-8"
        )
    worker = source / "workers" / "parent"
    worker.mkdir(parents=True)
    (worker / "ledger.json").write_text('{"status":"closed"}\n', encoding="utf-8")
    directory = SimpleNamespace(
        path=source,
        leaf=source.name,
        archive_path=target,
        archive_temporary_path=source.parent / f".{source.name}.zip.tmp",
    )
    return source, directory


def _canonical_archive(
    tmp_path: Path, *, purpose: str = "dispatcher-finalization"
) -> tuple[Path, Path]:
    source, directory = _source(tmp_path)
    archive_module.create(directory, purpose=purpose, required=snapshot_module.CORE)
    return source, directory.archive_path


def _legacy_archive(tmp_path: Path) -> tuple[Path, Path]:
    source, directory = _source(tmp_path, status="succeeded")
    snapshot = snapshot_module.Snapshot(source, required=snapshot_module.CORE)
    with zipfile.ZipFile(directory.archive_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(f"{source.name}/", b"")
        for name in snapshot.directories:
            bundle.writestr(f"{source.name}/{name}/", b"")
        for name, data in snapshot.files.items():
            bundle.writestr(f"{source.name}/{name}", data)
    return source, directory.archive_path


def test_canonical_archive_accepts_in_progress_source_record_and_receipt(
    tmp_path: Path,
) -> None:
    source, archive_path = _canonical_archive(tmp_path)

    verified = result_repair._verify_source_archive(source)
    state = json.loads((source / "state.json").read_text(encoding="utf-8"))

    assert verified["transport"] == "canonical"
    assert verified["receipt_verified"] is True
    assert state["archive"]["status"] == "in_progress"
    assert state["archive"]["succeeded"] is False
    assert result_repair._require_source_state(source, state, verified) == verified
    assert verified["sha256"] == hashlib.sha256(archive_path.read_bytes()).hexdigest()


def test_legacy_archive_without_manifest_remains_readable(tmp_path: Path) -> None:
    source, _archive_path = _legacy_archive(tmp_path)

    verified = result_repair._verify_source_archive(source)
    state = json.loads((source / "state.json").read_text(encoding="utf-8"))

    assert verified["transport"] == "legacy"
    assert verified["receipt_verified"] is False
    assert result_repair._require_source_state(source, state, verified) == verified


def test_archive_only_recovery_is_rejected_by_resume_consumers(tmp_path: Path) -> None:
    source, _archive_path = _canonical_archive(tmp_path, purpose="archive-only-recovery")

    with pytest.raises(ResumeError, match="transport manifest identity is invalid"):
        result_repair._verify_source_archive(source)


def test_canonical_receipt_digest_tampering_fails_after_archive_verification(
    tmp_path: Path,
) -> None:
    source, archive_path = _canonical_archive(tmp_path)
    receipt_path = archive_module.receipt_path(archive_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["manifest_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")

    with pytest.raises(ResumeError, match="transport receipt does not bind"):
        result_repair._verify_source_archive(source)


def test_canonical_manifest_tampering_fails_member_validation(tmp_path: Path) -> None:
    source, archive_path = _canonical_archive(tmp_path)
    leaf = source.name
    rewritten = tmp_path / "rewritten.zip"
    with zipfile.ZipFile(archive_path) as original, zipfile.ZipFile(
        rewritten, "w", compression=zipfile.ZIP_DEFLATED
    ) as replacement:
        for info in original.infolist():
            data = original.read(info.filename)
            if info.filename == f"{leaf}/TRANSPORT-MANIFEST.json":
                manifest = json.loads(data)
                manifest["selected_bytes"] += 1
                data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
            replacement.writestr(info, data)
    archive_path.unlink()
    rewritten.replace(archive_path)

    with pytest.raises(ResumeError, match="transport receipt does not bind|transport manifest selection"):
        result_repair._verify_source_archive(source)


def test_source_byte_drift_fails_manifest_source_binding(tmp_path: Path) -> None:
    source, _archive_path = _canonical_archive(tmp_path)
    (source / "request.json").write_bytes(b'{"phase":"changed"}\n')

    with pytest.raises(ResumeError, match="source archive member differs"):
        result_repair._verify_source_archive(source)


def test_real_legacy_runtime_members_remain_compressed_and_unobserved(tmp_path: Path, monkeypatch) -> None:
    source, target = _legacy_archive(tmp_path)
    runtime = source / "workers" / "parent" / "serena-home"
    runtime.mkdir()
    (runtime / "compiler.bin").write_bytes(b"legacy runtime bytes")
    with zipfile.ZipFile(target, "a", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(f"{source.name}/workers/parent/serena-home/", b"")
        bundle.write(runtime / "compiler.bin", f"{source.name}/workers/parent/serena-home/compiler.bin")
    (runtime / "compiler.bin").unlink()
    os.mkfifo(runtime / "compiler.bin")
    original_read = zipfile.ZipFile.read
    def guarded_read(bundle, name, *args, **kwargs):
        filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
        assert "/serena-home" not in filename
        return original_read(bundle, name, *args, **kwargs)
    def forbidden_testzip(*args):
        raise AssertionError("legacy runtime decompressed by global CRC test")
    monkeypatch.setattr(zipfile.ZipFile, "read", guarded_read)
    monkeypatch.setattr(zipfile.ZipFile, "testzip", forbidden_testzip)
    verified = result_repair._verify_source_archive(source)
    assert verified["transport"] == "legacy"
    assert verified["member_count"] == verified["selected_member_count"] + 2
    result_repair._require_source_state(source, json.loads((source / "state.json").read_bytes()), verified)


def test_legacy_does_not_accept_unrelated_extra_evidence(tmp_path: Path) -> None:
    source, target = _legacy_archive(tmp_path)
    with zipfile.ZipFile(target, "a") as bundle:
        bundle.writestr(f"{source.name}/unexpected.txt", b"unexpected")
    with pytest.raises(ResumeError, match="member set differs"):
        result_repair._verify_source_archive(source)


def test_historical_limit_values_do_not_pin_future_archive_policy(tmp_path: Path, monkeypatch) -> None:
    source, _ = _canonical_archive(tmp_path)
    monkeypatch.setattr(snapshot_module, "MAX_FILE_BYTES", snapshot_module.MAX_FILE_BYTES + 1)
    assert result_repair._verify_source_archive(source)["receipt_verified"] is True


def test_canonical_dry_run_without_result_remains_verifiable(tmp_path: Path) -> None:
    source, directory = _source(tmp_path)
    state = json.loads((source / "state.json").read_bytes())
    state["dry_run"] = True
    (source / "state.json").write_text(json.dumps(state))
    (source / "result.json").unlink()
    archive_module.create(directory)
    assert result_repair._verify_source_archive(source)["receipt_verified"] is True
