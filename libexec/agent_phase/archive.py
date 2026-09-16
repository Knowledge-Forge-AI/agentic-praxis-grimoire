"""Atomic, no-clobber ZIP packaging for one finalized run directory."""

from __future__ import annotations

import os
import hashlib
from pathlib import Path
import zipfile
import uuid
import stat
from typing import Any, Callable


from .archive_snapshot import (
    ArchiveError, MANIFEST, Snapshot, dry_run_required, encoded, exclusion, identity,
)

MAX_ARCHIVE_BYTES = 256 * 1024 * 1024


def record(path: Path) -> dict[str, Any]:
    return {
        "attempted": False,
        "path": str(path),
        "status": "not_attempted",
        "succeeded": False,
        "failure": None,
    }


def finalize(
    directory,
    state: dict[str, Any],
    write_artifacts: Callable[[], None],
    finished: Callable[[], None],
) -> ArchiveError | None:
    """Persist final truth, seal it, and preserve any earlier primary blocker."""
    # Source records describe the snapshot attempt. A sibling receipt records
    # final delivery without rewriting bytes used by legacy resume verification.
    state["archive"] = {
        "attempted": True, "path": str(directory.archive_path),
        "status": "in_progress", "succeeded": False, "failure": None,
        "receipt_path": str(receipt_path(directory.archive_path)),
    }
    write_artifacts()
    try:
        create(directory)
    except ArchiveError as error:
        failure = {"code": error.code, "detail": error.detail}
        if hasattr(error, "verification"):
            failure["verification"] = error.verification
        state["archive"].update(status="failed", succeeded=False, failure=failure)
        # Retain the legacy secondary-failure list, but never make delivery a
        # semantic blocker or erase completed Git/publication facts.
        state.setdefault("finalization_failures", []).append(failure)
        if getattr(error, "archive_published", False) or error.code == "RUN_ARCHIVE_RECEIPT_FAILED":
            # Never rewrite source bytes already sealed in a published ZIP.
            state["archive"]["failure_receipt_path"] = str(failure_receipt_path(directory.archive_path))
            try:
                _write_receipt(failure_receipt_path(directory.archive_path), {
                    "schema": "agent-phase-transport-failure-v1", "status": "failed",
                    "purpose": "dispatcher-finalization", "zip_published": True,
                    "archive_name": directory.archive_path.name,
                    "archive_sha256": _digest(directory.archive_path), "failure": failure,
                })
                state["archive"]["failure_receipt_status"] = "written"
            except (OSError, ArchiveError):
                state["archive"]["failure_receipt_status"] = "unavailable"
        else:
            write_artifacts()
        finished()
        return error
    state["archive"].update(status="succeeded", succeeded=True)
    finished()
    return None


def excluded(relative: Path) -> bool:
    """Return whether one run-relative node is omitted from transport ZIPs."""
    return exclusion(relative) is not None


def receipt_path(target: Path) -> Path:
    name = target.name + ".receipt.json"
    if len(os.fsencode(name)) > 255:
        name = "transport-" + hashlib.sha256(os.fsencode(target.name)).hexdigest() + ".receipt.json"
    return target.with_name(name)


def failure_receipt_path(target: Path) -> Path:
    name = "transport-failure-" + hashlib.sha256(os.fsencode(target.name)).hexdigest() + ".json"
    return target.with_name(name)


def _publish(temporary: Path, target: Path) -> None:
    try:
        os.link(temporary, target)
    except FileExistsError as error:
        raise ArchiveError("RUN_ARCHIVE_COLLISION", "destination already exists") from error
    descriptor = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _receipt(target: Path, payload: dict) -> None:
    # The ZIP's manifest remains usable if receipt delivery fails. No source
    # record or published ZIP is edited to repair a failed receipt.
    try:
        _write_receipt(receipt_path(target), payload)
    except (OSError, ArchiveError) as error:
        raise ArchiveError("RUN_ARCHIVE_RECEIPT_FAILED", "ZIP published; final receipt delivery failed") from error


def _write_receipt(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".transport-receipt-{uuid.uuid4().hex}.tmp")
    owned = False
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        owned = True
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded(payload))
            handle.flush()
            os.fsync(handle.fileno())
        _publish(temporary, path)
    finally:
        if owned:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _published_link(temporary: Path, target: Path) -> bool:
    try:
        left = temporary.lstat()
        right = target.lstat()
        return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)
    except OSError:
        return False


def create(directory, *, purpose: str = "dispatcher-finalization", required=None,
           snapshot: Snapshot | None = None) -> Path:
    """Publish a bounded evidence snapshot and a separate final delivery receipt."""
    source = directory.path
    target = directory.archive_path
    temporary = directory.archive_temporary_path
    if os.path.lexists(target) or os.path.lexists(receipt_path(target)):
        raise ArchiveError("RUN_ARCHIVE_COLLISION", "destination or receipt already exists")
    owned_temporary = False
    published = False
    try:
        if snapshot is None and required is None:
            # Dry-run has no result by contract; detect from bounded state bytes.
            required = dry_run_required(source)
        if snapshot is None:
            snapshot = Snapshot(source, required)
        manifest = snapshot.manifest(purpose)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            owned_temporary = True
            with zipfile.ZipFile(handle, mode="w", compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=9) as archive:
                archive.writestr(f"{directory.leaf}/", b"")
                for name in snapshot.directories:
                    archive.writestr(f"{directory.leaf}/{name}/", b"")
                for name, data in snapshot.files.items():
                    archive.writestr(f"{directory.leaf}/{name}", data)
                archive.writestr(f"{directory.leaf}/{MANIFEST}", encoded(manifest))
            handle.flush()
            os.fsync(handle.fileno())
        with zipfile.ZipFile(temporary, "r") as archive:
            if archive.testzip() is not None:
                raise ArchiveError("RUN_ARCHIVE_FAILED", "archive integrity check failed")
        verification = snapshot.verify_unchanged()
        _publish(temporary, target)
        published = True
        _receipt(target, {
            "schema": "agent-phase-transport-receipt-v1", "status": "succeeded",
            "purpose": purpose, "review_only": True,
            "archive_name": target.name, "archive_bytes": target.stat().st_size,
            "receipt_name": receipt_path(target).name,
            "archive_sha256": _digest(target),
            "manifest_sha256": hashlib.sha256(encoded(manifest)).hexdigest(),
            "verification": verification,
            "selected_count": len(snapshot.files), "selected_bytes": snapshot.total,
            "source_records": "unchanged source attempt; receipt is final delivery truth",
        })
        return target
    except ArchiveError as error:
        error.archive_published = published or (owned_temporary and _published_link(temporary, target))
        raise
    except (OSError, zipfile.BadZipFile) as error:
        failure = ArchiveError("RUN_ARCHIVE_FAILED", "archive or receipt delivery failed (OS/ZIP error)")
        failure.archive_published = published or (owned_temporary and _published_link(temporary, target))
        raise failure from error
    finally:
        if owned_temporary:
            try:
                temporary.unlink()
            except OSError:
                pass


def _digest(path: Path) -> str:
    """Bound even delivery readback; never follow a replacement special node."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARCHIVE_BYTES:
            raise ArchiveError("RUN_ARCHIVE_LIMIT", "delivery readback exceeds archive bound")
        digest = hashlib.sha256()
        remaining = info.st_size
        while remaining:
            data = handle.read(min(remaining, 1024 * 1024))
            if not data:
                raise ArchiveError("RUN_ARCHIVE_CHANGED", "archive changed during readback")
            digest.update(data)
            remaining -= len(data)
        if handle.read(1) or identity(os.fstat(handle.fileno())) != identity(info):
            raise ArchiveError("RUN_ARCHIVE_CHANGED", "archive changed during readback")
        return digest.hexdigest()
