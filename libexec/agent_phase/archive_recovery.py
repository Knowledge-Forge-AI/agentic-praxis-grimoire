"""Provider-free, Git-free review transport from one exact settled local run."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace
import uuid

from . import archive
from .archive_snapshot import ArchiveError, Snapshot, load_record


def _object(data: bytes, name: str) -> dict:
    try:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError("not an object")
        return value
    except ValueError as error:
        raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", f"invalid settlement record: {name}") from error


def _settled(snapshot: Snapshot) -> None:
    state = _object(snapshot.files["state.json"], "state.json")
    result = _object(snapshot.files["result.json"], "result.json")
    if (state.get("outcome") not in {"completed", "blocked", "failed", "interrupted"}
            or result.get("outcome") != state.get("outcome")
            or state.get("worker_cleanup_pending")):
        raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", "source is not terminal with settled custody")
    delivery = state.get("archive") or {}
    if not isinstance(delivery, dict):
        raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", "invalid source archive record")
    if delivery.get("status") == "in_progress":
        from .archive_verify import VerificationError, require_source_state, verify_source_archive
        try:
            verified = verify_source_archive(snapshot.source)
            require_source_state(snapshot.source, state, verified)
        except VerificationError as error:
            target = snapshot.source.with_name(snapshot.source.name + ".zip")
            failure = load_record(target.parent, archive.failure_receipt_path(target).name)
            if (failure.get("schema") != "agent-phase-transport-failure-v1"
                    or failure.get("status") != "failed"
                    or failure.get("purpose") != "dispatcher-finalization"
                    or failure.get("zip_published") is not True
                    or failure.get("archive_name") != target.name
                    or failure.get("archive_sha256") != archive._digest(target)):
                raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", "source delivery receipt does not verify") from error
    elif delivery.get("status") not in {"failed", "succeeded"}:
        raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", "source has no terminal archive attempt")
    for name, raw in snapshot.files.items():
        if name.endswith(".worker-drain.json") or (
                len(Path(name).parts) == 3 and name.startswith("workers/")
                and name.endswith("/ledger.json")):
            record = _object(raw, name)
            if record.get("status") != "closed" or record.get("uncertain_cleanup"):
                raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", f"worker custody not closed: {name}")
            jobs = record.get("gemini_jobs") or {}
            native = record.get("native_agents") or {}
            if not isinstance(jobs, dict) or not isinstance(native, dict):
                raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", f"invalid worker custody: {name}")
            for job in jobs.values():
                if not isinstance(job, dict) or not isinstance(job.get("result") or {}, dict):
                    raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", f"invalid worker result: {name}")
                if (job.get("status") not in {"completed", "failed", "cancelled"}
                        or not (job.get("cleanup_proven") is True
                                or (job.get("result") or {}).get("cleanup_proven") is True)):
                    raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", f"worker cleanup unproven: {name}")
            if any(not isinstance(job, dict) or job.get("status") != "closed"
                   for job in native.values()):
                raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", f"native worker not closed: {name}")


def recover(source: Path, target: Path) -> Path:
    """Snapshot source, validate settlement, publish new bytes outside it."""
    source = Path(os.path.abspath(source))
    target = Path(os.path.abspath(target))
    if target.suffix.lower() != ".zip":
        raise ArchiveError("RUN_ARCHIVE_DESTINATION", "new output must have .zip suffix")
    if target.parent.resolve().is_relative_to(source.resolve()):
        raise ArchiveError("RUN_ARCHIVE_DESTINATION", "output must be outside the source run")
    if os.path.lexists(target) or os.path.lexists(archive.receipt_path(target)):
        raise ArchiveError("RUN_ARCHIVE_COLLISION", "destination or receipt already exists")
    snapshot = Snapshot(source)
    try:
        _settled(snapshot)
    except OSError as error:
        raise ArchiveError("RUN_ARCHIVE_NOT_SETTLED", "cannot verify source delivery receipt") from error
    directory = SimpleNamespace(
        path=source, leaf=source.name, archive_path=target,
        archive_temporary_path=target.with_name(f".agent-phase-archive-{uuid.uuid4().hex}.tmp"),
    )
    return archive.create(directory, purpose="archive-only-recovery", snapshot=snapshot)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase-archive", allow_abbrev=False,
        description="Build a new review-only transport; full local run remains resume authority.")
    parser.add_argument("source", type=Path, help="exact terminal run directory")
    parser.add_argument("output", type=Path, help="new .zip path outside the source run")
    args = parser.parse_args(argv)
    try:
        target = recover(args.source, args.output)
        print(archive.receipt_path(target).read_text(), end="")
    except ArchiveError as error:
        parser.exit(3, f"agent-phase-archive: {error}\n")
    return 0
