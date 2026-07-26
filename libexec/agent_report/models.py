"""Immutable data contracts for agent report records and Git observations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReportRecord:
    """One complete report payload and its common-envelope identity."""

    record_type: str
    format_version: int
    record_id: str
    project: str
    phase: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class ParsedRecord:
    """A validated record and its exact byte range in a report file."""

    record: ReportRecord
    payload_sha256: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class RealGitObservation:
    """Read-only evidence collected from HEAD, the real index, and worktree."""

    head: str
    index_fingerprint: str
    index_identity: str
    status: bytes
    staged: bytes
    unstaged: bytes


@dataclass(frozen=True, slots=True)
class WorktreeSnapshot:
    """Complete HEAD-relative evidence collected through a private index."""

    changed_files: bytes
    numstat_raw: bytes
    patch: bytes
