"""Candidate identity that does not depend on a model's claim about its output.

The pre-final candidate is a real git tree object built from the working tree,
including untracked files, without ever writing the repository's own index.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


from . import metadata_policy as metadata_policy_module


GIT_TIMEOUT_SECONDS = 120


class CandidateError(RuntimeError):
    """A trustworthy candidate identity could not be constructed."""


class PlanArtifactError(CandidateError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _git(
    cwd: Path,
    arguments: list[str],
    environment: dict[str, str] | None = None,
    *,
    preserve_output: bool = False,
) -> str:
    argv = ["git", *arguments]
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=environment,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise CandidateError(f"git failed: {' '.join(argv)}: {error}") from error
    if completed.returncode != 0:
        detail = os.fsdecode(completed.stderr).strip()
        raise CandidateError(f"git failed: {' '.join(argv)}: {detail}")
    output = os.fsdecode(completed.stdout)
    return output if preserve_output else output.strip()


def git_directory(cwd: Path) -> Path:
    """Resolve the git directory, failing closed outside a worktree."""
    raw = _git(cwd, ["rev-parse", "--absolute-git-dir"])
    path = Path(raw)
    if not path.is_dir():
        raise CandidateError(f"git directory is not usable: {path}")
    return path


def require_worktree(cwd: Path) -> Path:
    """Validate up front that this run can ever bind a pre-final candidate."""
    try:
        return git_directory(cwd)
    except CandidateError as error:
        raise CandidateError(
            f"working directory is not inside a git worktree, so a pre-final "
            f"candidate could never be bound: {cwd}: {error}"
        ) from error


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plan_identity(data: bytes) -> dict[str, object]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PlanArtifactError(
            "PLAN_ARTIFACT_NOT_UTF8", f"plan output is not valid UTF-8: {error}"
        ) from error
    if not text.strip():
        raise PlanArtifactError(
            "PLAN_ARTIFACT_EMPTY",
            "plan output is empty after Unicode whitespace trimming",
        )
    return {"kind": "plan_bytes", "sha256": digest(data), "bytes": len(data)}


def plan_material_identity(
    data: bytes,
    provider: str,
    profile: str,
    *,
    _home: Path | None = None,
) -> dict[str, object]:
    """Build a provider-aware, versioned plan-material binding.

    The original ``plan_identity`` remains the narrow raw-stdout reader for
    legacy runs. New dispatches use this identity so a canonical run-owned
    artifact can be archived and independently verified.
    """

    from .plan_material import materialize

    return materialize(data, provider, profile, _home=_home).binding


def tree_identity(cwd: Path) -> dict[str, object]:
    """Build a candidate tree in a throwaway index, never the repository's own."""
    git_dir = git_directory(cwd)
    head = _git(cwd, ["rev-parse", "HEAD"])
    real_index = git_dir / "index"
    with tempfile.TemporaryDirectory(prefix="agent-phase-index-") as scratch:
        temporary_index = Path(scratch) / "index"
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = os.fspath(temporary_index)
        if real_index.is_file():
            # Seed from the real index so staged-but-uncommitted intent is
            # preserved. The copy is what git writes to; the original is only read.
            try:
                # Git uses the index timestamp to recheck racily clean files.
                # A newly timestamped copy can hide same-size worktree edits.
                shutil.copy2(real_index, temporary_index)
            except OSError as error:
                raise CandidateError(
                    f"cannot seed temporary index from {real_index}: {error}"
                ) from error
        else:
            _git(cwd, ["read-tree", "HEAD"], environment)
        unmerged_raw = _git(
            cwd,
            ["ls-files", "--unmerged", "-z", "--", ":/"],
            environment,
            preserve_output=True,
        )
        if any(unmerged_raw.split("\0")):
            raise CandidateError(
                "git index contains unmerged paths; candidate capture is unsafe"
            )
        # Refresh tracked entries separately: explicit add -A pathspecs can
        # reject tracked fixtures beneath ignored directories. Update only the
        # throwaway index, including tracked edits, deletions, and mode changes.
        _git(cwd, ["add", "-u", "--", ":/"], environment)
        # Discover only untracked product without traversing built-in cache
        # roots. Never force-add or hash ignored/metadata files just to remove
        # them afterward; tracked metadata-looking paths were updated above.
        exclusions = [
            f"--exclude=/{root}"
            for root in metadata_policy_module.OPERATIONAL_METADATA_ROOTS
        ]
        untracked_raw = _git(
            cwd, ["ls-files", "--full-name", "--others", "--exclude-standard", *exclusions, "-z", "--", ":/"],
            environment,
            preserve_output=True,
        )
        # Keep the NUL stream unstripped: paths may begin with whitespace or
        # contain newlines. os.fsdecode preserves undecodable bytes using the
        # filesystem encoding's surrogateescape convention.
        product_paths = sorted({
            path for path in untracked_raw.split("\0")
            if path and not metadata_policy_module.is_metadata_pattern(path)
        })
        for i in range(0, len(product_paths), 100):
            chunk = [f":(top,literal){path}" for path in product_paths[i:i + 100]]
            _git(cwd, ["add", "-A", "--", *chunk], environment)
        tree = _git(cwd, ["write-tree"], environment)
    if not tree:
        raise CandidateError("git write-tree produced no candidate tree")
    return {"kind": "git_tree", "head": head, "tree": tree}


def tree_delta(cwd: Path, before: str, after: str) -> list[str]:
    """Paths that changed between two candidate trees, for honest reporting."""
    if before == after:
        return []
    raw = _git(cwd, ["diff-tree", "-r", "--name-only", "--no-commit-id", before, after])
    return [line for line in raw.splitlines() if line]
