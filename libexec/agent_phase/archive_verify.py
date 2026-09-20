"""Read-only verification of legacy and receipt-backed run transports."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any
import zipfile

from . import archive
from . import archive_snapshot


class VerificationError(RuntimeError):
    """A source run or its sibling transport does not cross-verify."""

    code = "RESUME_ARTIFACT_MISMATCH"

    def __init__(self, detail: str) -> None:
        self.detail = "".join(c if c.isprintable() else "?" for c in detail)[:1200]
        super().__init__(self.detail)


def _mismatch(detail: str) -> VerificationError:
    return VerificationError(detail)


def _archive_path(source: Path) -> Path:
    return source.parent / f"{source.name}.zip"


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zip_info_kind(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0o170000


def source_manifest(source: Path) -> dict[str, Any]:
    """Capture selected source bytes without entering excluded runtimes."""
    try:
        snapshot = archive_snapshot.Snapshot(source, required=())
    except archive_snapshot.ArchiveError as error:
        raise _mismatch(f"source run cannot be snapshotted: {error.detail}") from error
    archive_path = _archive_path(source)
    try:
        archive_sha256 = _digest_file(archive_path)
    except OSError as error:
        raise _mismatch("source archive is unavailable") from error
    return {
        "files": {
            name: _digest_bytes(data)
            for name, data in sorted(snapshot.files.items())
        },
        "archive_sha256": archive_sha256,
        "file_count": len(snapshot.files),
    }


def _read_manifest(
    archive_file: zipfile.ZipFile, manifest_name: str
) -> tuple[bytes, dict[str, Any]]:
    try:
        manifest_info = archive_file.getinfo(manifest_name)
        if manifest_info.file_size > archive_snapshot.MAX_FILE_BYTES:
            raise _mismatch("transport manifest exceeds the bounded file limit")
        manifest_bytes = archive_file.read(manifest_info)
        if len(manifest_bytes) > archive_snapshot.MAX_FILE_BYTES:
            raise _mismatch("transport manifest exceeds the bounded file limit")
        manifest = json.loads(manifest_bytes)
    except VerificationError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _mismatch("transport manifest is unreadable") from error
    if not isinstance(manifest, dict):
        raise _mismatch("transport manifest is not an object")
    return manifest_bytes, manifest


def _validate_manifest_inventory(
    manifest: dict[str, Any], snapshot: archive_snapshot.Snapshot, leaf: str
) -> None:
    if (
        manifest.get("schema") != "agent-phase-transport-v1"
        or manifest.get("purpose") != "dispatcher-finalization"
        or manifest.get("review_only") is not True
        or manifest.get("source_leaf") != leaf
    ):
        raise _mismatch("transport manifest identity is invalid")
    expected_manifest = snapshot.manifest("dispatcher-finalization")
    included = manifest.get("included")
    if not isinstance(included, list):
        raise _mismatch("transport manifest included inventory is invalid")
    expected_included = {
        entry["path"]: entry for entry in expected_manifest["included"]
    }
    observed_included: dict[str, dict[str, Any]] = {}
    for entry in included:
        if not isinstance(entry, dict):
            raise _mismatch("transport manifest includes a non-object entry")
        path = entry.get("path")
        if not isinstance(path, str) or path in observed_included:
            raise _mismatch("transport manifest has a duplicate or invalid path")
        observed_included[path] = entry
    if observed_included != expected_included:
        raise _mismatch("transport manifest file inventory differs from source")

    directories = manifest.get("directories")
    if not isinstance(directories, list) or any(
        not isinstance(path, str) for path in directories
    ):
        raise _mismatch("transport manifest directory inventory is invalid")
    if directories != expected_manifest["directories"]:
        raise _mismatch("transport manifest directory inventory differs from source")
    # Generator policy/prose is historical metadata bound by the receipt, not
    # a requirement that today's constants or explanatory text remain equal.
    limits = manifest.get("limits")
    if (not isinstance(limits, dict) or set(limits) != set(expected_manifest["limits"])
            or any(type(value) is not int or value <= 0 for value in limits.values())):
        raise _mismatch("transport manifest historical limits are invalid")
    # Exclusions describe the historical snapshot, not runtime/cache identity.
    # New Finder metadata or changed excluded runtime roots cannot invalidate
    # unchanged selected evidence. Validate the recorded selection policy only.
    exclusions = manifest.get("excluded")
    if not isinstance(exclusions, list):
        raise _mismatch("transport manifest exclusions are invalid")
    seen_exclusions: set[str] = set()
    for item in exclusions:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise _mismatch("transport manifest exclusion is invalid")
        relative = Path(item["path"])
        if (item["path"] in seen_exclusions or relative.is_absolute() or ".." in relative.parts
                or archive_snapshot.exclusion(relative) != item.get("reason")
                or archive_snapshot.exclusion(relative) is None
                or archive_snapshot.exclusion(relative.parent) is not None):
            raise _mismatch("transport manifest exclusion does not match selection policy")
        seen_exclusions.add(item["path"])
    if any(
        manifest.get(key) != expected_manifest[key]
        for key in (
            "selected_count",
            "selected_bytes",
            "size_count_omissions",
            "missing_required",
            "source_artifact_observations",
            "source_issue_records_not_inspected",
            "required",
        )
    ):
        raise _mismatch("transport manifest selection totals are invalid")


def _read_receipt(path: Path, expected_identity: tuple[int, ...], size: int) -> bytes:
    """Read a bounded receipt through an O_NOFOLLOW descriptor."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = archive_snapshot.identity(os.fstat(fd))
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read(size + 1)
            after = archive_snapshot.identity(os.fstat(handle.fileno()))
        if before != expected_identity or len(data) != size or before != after:
            raise OSError("receipt changed while reading")
        return data
    finally:
        os.close(fd)


def _validate_receipt(
    source: Path,
    manifest_bytes: bytes,
    snapshot: archive_snapshot.Snapshot,
) -> dict[str, Any]:
    receipt_path = archive.receipt_path(_archive_path(source))
    try:
        info = os.lstat(receipt_path)
    except OSError as error:
        raise _mismatch("transport receipt is unavailable") from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise _mismatch("transport receipt is not a regular file")
    if info.st_size > archive_snapshot.MAX_FILE_BYTES:
        raise _mismatch("transport receipt exceeds the bounded file limit")
    try:
        receipt_bytes = _read_receipt(
            receipt_path, archive_snapshot.identity(info), info.st_size
        )
        receipt = json.loads(receipt_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _mismatch("transport receipt is unreadable") from error
    if not isinstance(receipt, dict):
        raise _mismatch("transport receipt is not an object")
    archive_path = _archive_path(source)
    if (
        receipt.get("schema") != "agent-phase-transport-receipt-v1"
        or receipt.get("status") != "succeeded"
        or receipt.get("purpose") != "dispatcher-finalization"
        or receipt.get("review_only") is not True
        or receipt.get("archive_name") != archive_path.name
        or receipt.get("receipt_name") != receipt_path.name
        or receipt.get("archive_sha256") != _digest_file(archive_path)
        or receipt.get("manifest_sha256") != _digest_bytes(manifest_bytes)
        or receipt.get("selected_count") != len(snapshot.files)
        or receipt.get("selected_bytes") != snapshot.total
    ):
        raise _mismatch("transport receipt does not bind the verified archive")
    return receipt


def _validate_manifest_and_receipt(
    archive_file: zipfile.ZipFile,
    source: Path,
    snapshot: archive_snapshot.Snapshot,
    names: set[str],
) -> tuple[bytes | None, dict[str, Any] | None]:
    manifest_name = f"{source.name}/{archive_snapshot.MANIFEST}"
    if manifest_name not in names:
        return None, None
    manifest_bytes, manifest = _read_manifest(archive_file, manifest_name)
    _validate_manifest_inventory(manifest, snapshot, source.name)
    receipt = _validate_receipt(source, manifest_bytes, snapshot)
    return manifest_bytes, receipt


def _verify_member_info(info: zipfile.ZipInfo, files: dict[str, bytes], manifest_name: str) -> None:
    kind = _zip_info_kind(info)
    if info.filename == manifest_name:
        if kind not in (0, stat.S_IFREG) or info.file_size > archive_snapshot.MAX_FILE_BYTES:
            raise _mismatch("transport manifest is not a bounded regular member")
    elif info.filename.endswith("/"):
        if kind not in (0, stat.S_IFDIR) or info.file_size != 0:
            raise _mismatch("source archive directory has invalid type or size")
    elif kind not in (0, stat.S_IFREG):
        raise _mismatch(f"source archive member is not a regular file: {info.filename}")
    elif info.file_size != len(files[info.filename]):
        raise _mismatch(f"source archive member differs from source directory: {info.filename}")


def _verify_members(archive_file: zipfile.ZipFile, snapshot: archive_snapshot.Snapshot) -> tuple[set[str], bool]:
    leaf = snapshot.source.name
    manifest_name = f"{leaf}/{archive_snapshot.MANIFEST}"
    infos = archive_file.infolist()
    names = [item.filename for item in infos]
    if len(names) != len(set(names)):
        raise _mismatch("source archive contains duplicate members")
    present = manifest_name in names
    files = {f"{leaf}/{name}": data for name, data in snapshot.files.items()}
    directories = {f"{leaf}/"} | {f"{leaf}/{name}/" for name in snapshot.directories}
    expected = set(files) | directories | ({manifest_name} if present else set())
    extras = set(names) - expected
    if present or not all(_legacy_excluded(name, leaf) for name in extras):
        if extras:
            raise _mismatch("source archive member set differs from source directory")
    if expected - set(names):
        raise _mismatch("source archive member set differs from source directory")
    # Bind every advertised length before CRC/decompression. Aggregate work is
    # bounded by selected source bytes plus the one bounded generated manifest.
    for info in infos:
        if info.filename in expected:
            _verify_member_info(info, files, manifest_name)
    if not extras and archive_file.testzip() is not None:
        raise _mismatch("source archive CRC validation failed")
    for name, data in files.items():
        if archive_file.read(name) != data:
            raise _mismatch(f"source archive member differs from source directory: {name}")
    return expected, present


def _legacy_excluded(name: str, leaf: str) -> bool:
    """Legacy runtime payload stays compressed and unobserved, not source authority."""
    if not name.startswith(leaf + "/"):
        return False
    relative = Path(name[len(leaf) + 1:])
    return (not relative.is_absolute() and ".." not in relative.parts
            and archive_snapshot.exclusion(relative) is not None)


def _verified_contents(handle, source: Path, required) -> dict[str, Any]:
    with zipfile.ZipFile(handle, "r") as archive_file:
        archive_member_count = len(archive_file.infolist())
        manifest_name = f"{source.name}/{archive_snapshot.MANIFEST}"
        if manifest_name in archive_file.namelist():
            required = archive_snapshot.dry_run_required(source)
        snapshot = archive_snapshot.Snapshot(source, required=required)
        names, present = _verify_members(archive_file, snapshot)
        manifest_bytes, receipt = _validate_manifest_and_receipt(
            archive_file, source, snapshot, names
        )
        snapshot.verify_unchanged()
    return {
        "member_count": archive_member_count, "selected_member_count": len(names),
        "verified_against_source_directory": True,
        "transport": "canonical" if present else "legacy",
        "manifest_sha256": _digest_bytes(manifest_bytes) if manifest_bytes is not None else None,
        "receipt_path": os.fspath(archive.receipt_path(_archive_path(source))) if receipt is not None else None,
        "receipt_verified": receipt is not None,
    }


def verify_source_archive(source: Path, *, required=()) -> dict[str, Any]:
    """Verify bounded legacy/canonical bytes through one no-follow descriptor."""
    path = _archive_path(source)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > archive.MAX_ARCHIVE_BYTES:
                raise _mismatch("source archive is not a bounded regular file")
            expected = archive_snapshot.identity(info)
            result = _verified_contents(handle, source, required)
            if archive_snapshot.identity(os.fstat(handle.fileno())) != expected:
                raise _mismatch("source archive changed during verification")
            archive_sha256 = _digest_file(path)
            if archive_snapshot.identity(os.lstat(path)) != expected:
                raise _mismatch("source archive changed during digest readback")
    except VerificationError:
        raise
    except (OSError, zipfile.BadZipFile, archive_snapshot.ArchiveError) as error:
        raise _mismatch("source archive or selected source evidence is invalid") from error
    return {"path": os.fspath(path), "sha256": archive_sha256, **result}


def require_source_state(
    source: Path,
    state: dict[str, Any],
    archive_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Accept legacy success or in-progress source state with a verified receipt."""
    recorded = state.get("archive")
    if not isinstance(recorded, dict):
        raise _mismatch("source archive record is unavailable")
    expected_archive = _archive_path(source).resolve()
    if Path(str(recorded.get("path", ""))).resolve() != expected_archive:
        raise _mismatch("source archive path disagrees")
    if (
        recorded.get("attempted") is True
        and recorded.get("status") == "succeeded"
        and recorded.get("succeeded") is True
        and recorded.get("failure") is None
    ):
        return archive_record or verify_source_archive(source)
    if (
        recorded.get("attempted") is True
        and recorded.get("status") == "in_progress"
        and recorded.get("succeeded") is False
        and recorded.get("failure") is None
    ):
        verified = archive_record or verify_source_archive(source)
        if verified.get("transport") != "canonical" or not verified.get("receipt_verified"):
            raise _mismatch("canonical source archive lacks a validated success receipt")
        receipt_path = recorded.get("receipt_path")
        expected_receipt = archive.receipt_path(_archive_path(source)).resolve()
        if receipt_path is None or Path(str(receipt_path)).resolve() != expected_receipt:
            raise _mismatch("source archive receipt path disagrees")
        return verified
    raise _mismatch("source archive was not recorded successful")

def _digest_file(path: Path) -> str:
    try:
        return archive._digest(path)
    except archive.ArchiveError as error:
        raise OSError("bounded archive digest failed") from error
