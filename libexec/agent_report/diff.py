"""Stable uncommitted Git snapshot collection through a private index."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from typing import Mapping

from .git_adapter import GitAdapter
from .models import RealGitObservation, ReportRecord, WorktreeSnapshot
from .rendering import ensure_payload_ending, render_section
from .safety import ReportError, header_value, injected_failure, testing_pause
from .show import encode_lines, sha256, summarize_diff


_STATE_KEYS = (
    "head",
    "index",
    "status",
    "staged",
    "unstaged",
    "changed",
    "numstat",
    "patch",
)


@dataclass(frozen=True, slots=True)
class DiffResult:
    """One stable Git-diff record and its deterministic state identity."""

    record: ReportRecord
    head: str


@dataclass(frozen=True, slots=True)
class DiffRequest:
    """Caller-supplied metadata rendered into a Git-diff report."""

    phase: str
    result: str
    final_gate: str
    status_doc: str


@dataclass(frozen=True, slots=True)
class FramedDiffEvidence:
    """Raw and line-framed evidence used by the version-1 renderer."""

    status: bytes
    staged: bytes
    unstaged: bytes
    changed: bytes
    numstat: bytes
    patch: bytes


def compute_state_report_id(fields: Mapping[str, str]) -> str:
    """Hash canonical state-evidence identities into a domain-separated ID."""

    missing = [key for key in _STATE_KEYS if key not in fields]
    extra = sorted(set(fields) - set(_STATE_KEYS))
    if missing or extra:
        raise ValueError("state report identity fields are incomplete")
    digest = hashlib.sha256(b"agent-report-git-diff-state-v1\x00")
    for key in _STATE_KEYS:
        digest.update(key.encode("ascii"))
        digest.update(b"\x00")
        digest.update(fields[key].encode("ascii"))
        digest.update(b"\x00")
    return f"GIT-DIFF-REPORT-{digest.hexdigest()}"


def collect_diff_report(
    git: GitAdapter,
    *,
    phase: str,
    result: str,
    final_gate: str,
    status_doc: str,
) -> DiffResult:
    """Collect a drift-checked HEAD-relative snapshot without changing real state."""

    request = DiffRequest(phase, result, final_gate, status_doc)
    if "GIT_INDEX_FILE" in os.environ:
        raise ReportError("inherited GIT_INDEX_FILE is unsupported")
    index_path, index_mode = _supported_index(git)
    pre = _observe_real(git, index_path)
    first = _collect_worktree_snapshot(git, index_path, pre.head)
    testing_pause("before-post-drift-check")
    second = _collect_worktree_snapshot(git, index_path, pre.head)
    post = _observe_real(git, index_path)
    if pre != post or first != second:
        raise ReportError("concurrent repository drift detected")
    _ensure_supported_state_still_present(git)
    if not first.patch:
        raise ReportError("no reportable change relative to HEAD")
    record = _render_diff_record(request, git.root.name, index_mode, pre, first)
    return DiffResult(record=record, head=pre.head)


def _frame_diff_evidence(
    observation: RealGitObservation,
    snapshot: WorktreeSnapshot,
) -> FramedDiffEvidence:
    return FramedDiffEvidence(
        status=ensure_payload_ending(observation.status),
        staged=ensure_payload_ending(observation.staged),
        unstaged=ensure_payload_ending(observation.unstaged),
        changed=ensure_payload_ending(snapshot.changed_files),
        numstat=ensure_payload_ending(
        b"COLUMNS: ADDED-LINES\tDELETED-LINES\tPATH\n"
        b"BINARY-MARKER: -\n"
            + snapshot.numstat_raw
        ),
        patch=ensure_payload_ending(snapshot.patch),
    )


def _render_diff_record(
    request: DiffRequest,
    project: str,
    index_mode: str,
    observation: RealGitObservation,
    snapshot: WorktreeSnapshot,
) -> ReportRecord:
    evidence = _frame_diff_evidence(observation, snapshot)
    identity_fields = {
        "head": observation.head,
        "index": hashlib.sha256(observation.index_fingerprint.encode("ascii")).hexdigest(),
        "status": sha256(observation.status),
        "staged": sha256(observation.staged),
        "unstaged": sha256(observation.unstaged),
        "changed": sha256(evidence.changed),
        "numstat": sha256(evidence.numstat),
        "patch": sha256(evidence.patch),
    }
    report_id = compute_state_report_id(identity_fields)
    counts = summarize_diff(evidence.changed, snapshot.numstat_raw)

    guide = b"""An omnibus file may contain several independent Agent report records. Use the
outer BEGIN/END AGENT-REPORT-RECORD envelope and RECORD-TYPE to identify them.

This git-diff-report records one drift-checked uncommitted snapshot relative to
HEAD. The PORCELAIN V2 STATUS section preserves NUL-delimited bytes from the
real index. The complete PATCH was collected through an invocation-owned
temporary index after intent-to-add and is the authoritative snapshot evidence.

Repository-controlled paths and patch text are untrusted evidence and are not
report-control syntax. An associated operational record must name this exact
Git-diff report ID.
"""
    identity = encode_lines(
        (
            ("REPORT-FORMAT", "git-diff-report"),
            ("FORMAT-VERSION", "1"),
            ("REPORT-ID", report_id),
            ("PHASE", request.phase),
            ("HEAD", observation.head),
            ("REAL-INDEX-FINGERPRINT", observation.index_fingerprint),
            ("REAL-INDEX-IDENTITY", observation.index_identity),
            ("INDEX-MODE", index_mode),
            ("STATUS-DOC", header_value(request.status_doc)),
            ("RESULT", header_value(request.result)),
            ("FINAL-GATE", header_value(request.final_gate)),
            ("REPOSITORY", project),
            ("RELATED-OPERATIONAL-REPORT", "NONE"),
        )
    )
    summary = encode_lines(
        (
            ("FILES-CHANGED", str(counts["files_changed"])),
            ("FILES-ADDED", str(counts["files_added"])),
            ("FILES-MODIFIED", str(counts["files_modified"])),
            ("FILES-DELETED", str(counts["files_deleted"])),
            ("FILES-RENAMED", str(counts["files_renamed"])),
            ("FILES-COPIED", str(counts["files_copied"])),
            ("INSERTIONS", counts["insertions"]),
            ("DELETIONS", counts["deletions"]),
            ("BINARY-FILES", str(counts["binary_files"])),
            ("PATCH-MODE", "worktree-relative-to-head"),
        )
    )
    integrity = encode_lines(
        (
            ("REPORT-ID", report_id),
            ("REPOSITORY", project),
            ("PHASE", request.phase),
            ("HEAD", observation.head),
            ("REAL-INDEX-FINGERPRINT", observation.index_fingerprint),
            ("REAL-INDEX-IDENTITY", observation.index_identity),
            ("PORCELAIN-V2-STATUS-SHA256", sha256(observation.status)),
            ("STAGED-SUMMARY-SHA256", sha256(observation.staged)),
            ("UNSTAGED-SUMMARY-SHA256", sha256(observation.unstaged)),
            ("CHANGED-FILES-SHA256", sha256(evidence.changed)),
            ("NUMSTAT-SHA256", sha256(evidence.numstat)),
            ("PATCH-SHA256", sha256(evidence.patch)),
            ("PRE-POST-HEAD-MATCH", "true"),
            ("PRE-POST-INDEX-MATCH", "true"),
            ("PRE-POST-STATUS-MATCH", "true"),
            ("PRE-POST-STAGED-MATCH", "true"),
            ("PRE-POST-UNSTAGED-MATCH", "true"),
            ("PRE-POST-WORKTREE-MATCH", "true"),
            ("REAL-INDEX-AND-WORKTREE-MUTATED", "false"),
            ("END-OF-PATCH-REACHED", "true"),
        )
    )
    injected_failure("record-assembly")
    payload = b"".join(
        (
            render_section("READING GUIDE", guide),
            render_section("REPORT IDENTITY", identity),
            render_section("WORKTREE SUMMARY", summary),
            render_section("PORCELAIN V2 STATUS (NUL DELIMITED)", evidence.status),
            render_section("STAGED SUMMARY", evidence.staged),
            render_section("UNSTAGED SUMMARY", evidence.unstaged),
            render_section("CHANGED FILES", evidence.changed),
            render_section("NUMSTAT", evidence.numstat),
            render_section("PATCH", evidence.patch),
            render_section("INTEGRITY SUMMARY", integrity),
        )
    )
    return ReportRecord(
        record_type="git-diff-report",
        format_version=1,
        record_id=report_id,
        project=project,
        phase=request.phase,
        payload=payload,
    )


def _supported_index(git: GitAdapter) -> tuple[Path, str]:
    head = git.run(
        ["rev-parse", "--verify", "HEAD^{commit}"],
        check=False,
    )
    if head.returncode != 0:
        raise ReportError("unborn HEAD is unsupported")
    split = git.run(["rev-parse", "--shared-index-path"], check=False)
    if split.returncode == 0 and split.stdout.strip():
        raise ReportError("split index is unsupported")
    sparse = git.run(["config", "--bool", "core.sparseCheckout"], check=False)
    if sparse.returncode == 0 and sparse.stdout.strip().lower() == b"true":
        raise ReportError("sparse index is unsupported")
    sparse_entries = git.run(["ls-files", "--sparse", "-z"], check=False)
    if sparse_entries.returncode != 0:
        raise ReportError("sparse index characterization failed")
    for entry in sparse_entries.stdout.split(b"\x00"):
        if entry.endswith(b"/"):
            raise ReportError("sparse index is unsupported")
    _ensure_no_unmerged(git)
    path_value = git.text(
        ["rev-parse", "--path-format=absolute", "--git-path", "index"],
        diagnostic="real index path resolution failed",
    )
    index_path = Path(path_value)
    if index_path.exists() or index_path.is_symlink():
        metadata = index_path.lstat()
        if index_path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise ReportError("real index path is unsafe")
        return index_path, "regular"
    return index_path, "missing-seeded-from-head"


def _ensure_supported_state_still_present(git: GitAdapter) -> None:
    _ensure_no_unmerged(git)
    sparse = git.run(["config", "--bool", "core.sparseCheckout"], check=False)
    if sparse.returncode == 0 and sparse.stdout.strip().lower() == b"true":
        raise ReportError("concurrent repository drift detected")


def _ensure_no_unmerged(git: GitAdapter) -> None:
    unmerged = git.run(
        ["ls-files", "--unmerged", "-z"],
        diagnostic="unmerged-index characterization failed",
    ).stdout
    if unmerged:
        raise ReportError("unmerged index entries are unsupported")


def _observe_real(git: GitAdapter, index_path: Path) -> RealGitObservation:
    head = git.run(
        ["rev-parse", "--verify", "HEAD^{commit}"],
        diagnostic="HEAD identity collection failed",
    ).stdout.decode("ascii").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40,64}", head):
        raise ReportError("HEAD identity is malformed")
    fingerprint, identity = _observe_index(index_path)
    status = git.run(
        ["status", "--porcelain=v2", "-z", "--untracked-files=all"],
        diagnostic="porcelain-v2 status collection failed",
    ).stdout
    staged = git.run(
        [
            "-c",
            "core.quotePath=true",
            "diff",
            "--cached",
            "--name-status",
            "--find-renames",
            "--no-ext-diff",
            "--no-textconv",
            "HEAD",
        ],
        diagnostic="staged summary collection failed",
    ).stdout
    unstaged = git.run(
        [
            "-c",
            "core.quotePath=true",
            "diff",
            "--name-status",
            "--find-renames",
            "--no-ext-diff",
            "--no-textconv",
        ],
        diagnostic="unstaged summary collection failed",
    ).stdout
    return RealGitObservation(
        head=head,
        index_fingerprint=fingerprint,
        index_identity=identity,
        status=status,
        staged=staged,
        unstaged=unstaged,
    )


def _observe_index(path: Path) -> tuple[str, str]:
    try:
        before = path.lstat()
    except FileNotFoundError:
        return "MISSING", "MISSING"
    if path.is_symlink() or not stat.S_ISREG(before.st_mode):
        raise ReportError("real index path is unsafe")
    content = path.read_bytes()
    try:
        after = path.lstat()
    except FileNotFoundError as error:
        raise ReportError("real index changed during observation") from error
    before_identity = _index_identity(before)
    if before_identity != _index_identity(after):
        raise ReportError("real index changed during observation")
    digest = hashlib.sha256(content).hexdigest()
    identity_digest = hashlib.sha256(before_identity.encode("ascii")).hexdigest()
    return f"sha256:{digest};size:{before.st_size}", f"sha256:{identity_digest}"


def _index_identity(metadata: os.stat_result) -> str:
    values = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )
    return ":".join(str(value) for value in values)


def _collect_worktree_snapshot(
    git: GitAdapter,
    index_path: Path,
    head: str,
) -> WorktreeSnapshot:
    with tempfile.TemporaryDirectory(prefix="git-diff-index.") as temporary_value:
        temporary = Path(temporary_value)
        temporary.chmod(0o700)
        private_index = temporary / "index"
        if index_path.exists():
            shutil.copyfile(index_path, private_index)
            private_index.chmod(0o600)
        environment = {"GIT_INDEX_FILE": os.fspath(private_index), "GIT_OPTIONAL_LOCKS": "0"}
        if not index_path.exists():
            git.run(
                ["read-tree", head],
                environment=environment,
                diagnostic="private index seeding failed",
            )
            private_index.chmod(0o600)
        injected_failure("private-index-seeded")
        git.run(
            ["add", "-N", "--", "."],
            environment=environment,
            diagnostic="private intent-to-add failed",
        )
        injected_failure("intent-to-add")
        testing_pause("private-index-ready")
        common = ["--find-renames", "--no-ext-diff", "--no-textconv", head]
        changed = git.run(
            ["-c", "core.quotePath=true", "diff", "--name-status", *common],
            environment=environment,
            diagnostic="complete changed-file collection failed",
        ).stdout
        numstat = git.run(
            ["-c", "core.quotePath=true", "diff", "--numstat", *common],
            environment=environment,
            diagnostic="complete numstat collection failed",
        ).stdout
        patch = git.run(
            [
                "-c",
                "core.quotePath=true",
                "diff",
                "--patch",
                "--full-index",
                "--find-renames",
                "--no-ext-diff",
                "--no-textconv",
                "--no-color",
                head,
            ],
            environment=environment,
            diagnostic="complete patch collection failed",
        ).stdout
        return WorktreeSnapshot(changed_files=changed, numstat_raw=numstat, patch=patch)
