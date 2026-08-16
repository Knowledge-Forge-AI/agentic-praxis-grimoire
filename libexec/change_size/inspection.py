"""Content classification for tracked Git blobs."""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch

from .policy import Policy


LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1\n"


@dataclass(frozen=True, slots=True)
class BlobInspection:
    classification: str
    binary: bool
    archive: bool
    lfs_pointer: bool
    longest_line_bytes: int | None


def inspect_blob(path: str, mode: str, payload: bytes, policy: Policy) -> BlobInspection:
    del mode
    generated = any(
        fnmatch.fnmatchcase(path, pattern)
        for pattern in policy.generated_derived_evidence_globs
    )
    suffix_archive = any(
        path.casefold().endswith(suffix.casefold())
        for suffix in policy.archive_extensions
    )
    signature_archive = any(
        payload[item.offset : item.offset + len(item.value)] == item.value
        for item in policy.archive_signatures
    )
    archive = suffix_archive or signature_archive
    lfs_pointer = payload.startswith(LFS_PREFIX)
    try:
        payload.decode("utf-8", errors="strict")
        valid_utf8 = True
    except UnicodeDecodeError:
        valid_utf8 = False
    binary = b"\0" in payload or not valid_utf8
    longest = None if binary else max((len(line) for line in payload.split(b"\n")), default=0)
    return BlobInspection(
        classification=(
            "generated-derived-evidence" if generated else "ordinary"
        ),
        binary=binary,
        archive=archive,
        lfs_pointer=lfs_pointer,
        longest_line_bytes=longest,
    )
