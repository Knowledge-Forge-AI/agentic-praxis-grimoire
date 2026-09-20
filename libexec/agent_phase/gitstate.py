"""Dispatcher-owned git facts: entry state, phase delta, and the local commit.

The provider agents run inside sandboxes that deny `.git` writes. That is a
deliberate boundary, not an obstacle to route around, so the dispatcher — which
runs outside those sandboxes — owns the local commit instead of asking a model to
perform it.

Two distinctions are load-bearing here:

* The phase delta is the difference between the *entry* candidate tree and the
  *final* candidate tree, not `git diff HEAD`. When the operator entered with
  unrelated dirt, both trees contain that dirt identically and it cancels out.
  `git diff HEAD` would sweep it into the commit.
* A model may propose commit message text. It never supplies an executable,
  argv, path, ref, environment, or git config; this module builds all of those.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from typing import Any, NamedTuple
from pathlib import PurePosixPath

from . import candidate as candidate_module
from . import metadata_policy as metadata_policy_module


GIT_TIMEOUT_SECONDS = 120
GITLINK_MODE = "160000"
CANDIDATE_MANIFEST_SCHEMA = "agent-phase-candidate-manifest-v1"
_GIT_OPERATION_MARKERS = (
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "BISECT_LOG",
    "BISECT_START",
    "BISECT_HEAD",
    "rebase-merge",
    "rebase-apply",
    "sequencer",
)
_CANDIDATE_IDENTITY_KEYS = (
    "present", "type", "mode", "size_bytes", "sha256",
)


class GitStateError(RuntimeError):
    """A git fact the dispatcher requires could not be established."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class GitPushError(GitStateError):
    """A push failed after its target and optional remote result were known."""

    def __init__(
        self,
        detail: str,
        post_push_remote_head: str | None = None,
        *,
        code: str = "GIT_PUSH_FAILED",
        command_succeeded: bool = False,
    ) -> None:
        super().__init__(code, detail)
        self.post_push_remote_head = post_push_remote_head
        self.command_succeeded = command_succeeded


class Change(NamedTuple):
    status: str
    path: str


class PushTarget(NamedTuple):
    branch: str
    remote: str
    remote_ref: str
    upstream_branch: str
    push_url: str


class EntryState(NamedTuple):
    root: Path
    head: str
    branch: str
    tree: str
    dirty: dict[str, dict[str, Any]]
    index_identity: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": os.fspath(self.root),
            "head": self.head,
            "branch": self.branch,
            "tree": self.tree,
            "dirty": sorted(self.dirty),
            "index": self.index_identity,
        }


def index_identity(root: Path) -> dict[str, Any]:
    """Return the stable semantic identity of the real Git index.

    Raw index bytes include refreshable stat-cache data. The stage-zero listing
    binds every indexed path, mode, blob, and intent-to-add entry without
    treating a benign read-side cache refresh as mutation.
    """
    listing = _run(root, ["ls-files", "--stage", "-z", "--", ":/"])
    if listing.returncode != 0:
        raise GitStateError(
            "INDEX_IDENTITY_UNREADABLE",
            listing.stderr.decode("utf-8", "replace").strip(),
        )
    return {
        "kind": "git_ls_files_stage_v1",
        "sha256": hashlib.sha256(listing.stdout).hexdigest(),
        "size_bytes": len(listing.stdout),
        "entry_count": len([item for item in listing.stdout.split(b"\0") if item]),
    }


def index_identity_for_tree(root: Path, treeish: str) -> dict[str, Any]:
    """Return the semantic index identity produced by exactly one treeish."""
    with tempfile.TemporaryDirectory(prefix="agent-phase-index-identity-") as scratch:
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = os.fspath(Path(scratch) / "index")
        read = subprocess.run(
            ["git", "read-tree", treeish], cwd=root, env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if read.returncode != 0:
            raise GitStateError(
                "INDEX_IDENTITY_UNREADABLE",
                read.stderr.decode("utf-8", "replace").strip(),
            )
        listing = subprocess.run(
            ["git", "ls-files", "--stage", "-z", "--", ":/"],
            cwd=root, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False,
        )
        if listing.returncode != 0:
            raise GitStateError(
                "INDEX_IDENTITY_UNREADABLE",
                listing.stderr.decode("utf-8", "replace").strip(),
            )
    return {
        "kind": "git_ls_files_stage_v1",
        "sha256": hashlib.sha256(listing.stdout).hexdigest(),
        "size_bytes": len(listing.stdout),
        "entry_count": len([item for item in listing.stdout.split(b"\0") if item]),
    }


def _run(root: Path, arguments: list[str], stdin: bytes | None = None
         ) -> subprocess.CompletedProcess:
    argv = ["git", *arguments]
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    options: dict[str, Any] = {"input": stdin} if stdin is not None else {
        "stdin": subprocess.DEVNULL
    }
    try:
        return subprocess.run(
            argv,
            cwd=root,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
            env=environment,
            **options,
        )
    except (OSError, subprocess.SubprocessError) as error:
        # Never serialize argv here. Push and ls-remote argv may contain a
        # credential-bearing URL, and TimeoutExpired includes argv in str(error).
        operation = arguments[0] if arguments else "command"
        raise GitStateError(
            "GIT_INVOCATION_FAILED",
            f"git {operation} invocation failed ({type(error).__name__})",
        ) from error


def _text(root: Path, arguments: list[str], code: str) -> str:
    completed = _run(root, arguments)
    if completed.returncode != 0:
        raise GitStateError(
            code,
            f"git {' '.join(arguments)}: "
            f"{completed.stderr.decode('utf-8', 'replace').strip()}",
        )
    return completed.stdout.decode("utf-8", "replace").strip()


def _literal(path: str) -> str:
    """Pathspec magic: exactly this path, rooted at the worktree top.

    A bare path is still a glob to git, so a filename containing `*`, `?`, `[`,
    or a leading `!` would over-match when staging.
    """
    return f":(top,literal){path}"


def literal_pathspec(path: str) -> str:
    """Expose the shared exact-path Git boundary to sibling modules."""
    return _literal(path)


def repository_root(cwd: Path) -> Path:
    return Path(_text(cwd, ["rev-parse", "--show-toplevel"], "NOT_A_WORKTREE"))


def active_git_operations(root: Path) -> tuple[str, ...]:
    """Return Git's own in-progress operation markers, without changing state."""
    active: list[str] = []
    for marker in _GIT_OPERATION_MARKERS:
        try:
            location = Path(_text(root, ["rev-parse", "--git-path", marker],
                                 "GIT_OPERATION_STATE_UNREADABLE"))
        except GitStateError:
            # The repository itself is valid if capture_entry got this far. A
            # marker lookup that cannot be completed is still a fail-closed
            # state, represented by a typed operation-state error.
            raise
        if not location.is_absolute():
            location = root / location
        try:
            if os.path.lexists(location):
                active.append(marker)
        except OSError as error:
            raise GitStateError(
                "GIT_OPERATION_STATE_UNREADABLE",
                f"cannot inspect Git operation state: {error}",
            ) from error
    return tuple(active)


def require_no_active_git_operations(root: Path) -> None:
    """Refuse a phase boundary while Git owns an unfinished operation."""
    operations = active_git_operations(root)
    if operations:
        raise GitStateError(
            "ENTRY_ACTIVE_GIT_OPERATION",
            "repository has active Git operation state: "
            + ", ".join(operations),
        )


def _identity(root: Path, path: str) -> dict[str, Any]:
    target = root / path
    try:
        info = os.lstat(target)
    except FileNotFoundError:
        return {"exists": False}
    except OSError as error:
        raise GitStateError("ENTRY_PATH_UNREADABLE", f"{path}: {error}")
    if stat.S_ISLNK(info.st_mode):
        try:
            link = os.readlink(target)
        except OSError as error:
            raise GitStateError("ENTRY_PATH_UNREADABLE", f"{path}: {error}")
        # Hash the link text, not the target: a dangling link has no contents,
        # and a link whose target changed must not read as unchanged.
        return {
            "exists": True,
            "type": "symlink",
            "sha256": hashlib.sha256(link.encode("utf-8")).hexdigest(),
        }
    if stat.S_ISDIR(info.st_mode):
        raise GitStateError(
            "ENTRY_SUBMODULE_UNSUPPORTED",
            f"dirty path is a directory, likely a submodule: {path}",
        )
    if not stat.S_ISREG(info.st_mode):
        raise GitStateError(
            "ENTRY_UNSUPPORTED_PATH_TYPE", f"dirty path is not a regular file: {path}"
        )
    try:
        data = target.read_bytes()
    except OSError as error:
        raise GitStateError("ENTRY_PATH_UNREADABLE", f"{path}: {error}")
    return {
        "exists": True,
        "type": "file",
        "executable": bool(info.st_mode & stat.S_IXUSR),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _status_records(root: Path) -> list[str]:
    completed = _run(
        root, ["status", "--porcelain=v2", "-z", "--untracked-files=all"]
    )
    if completed.returncode != 0:
        raise GitStateError(
            "STATUS_FAILED", completed.stderr.decode("utf-8", "replace").strip()
        )
    return completed.stdout.decode("utf-8", "surrogateescape").split("\0")


def dirty_paths(root: Path) -> list[str]:
    """Worktree paths differing from HEAD, including untracked, excluding ignored.

    porcelain-v2 without `--ignored` omits ignored files, which matches
    `candidate.tree_identity`: both sides ignore the same set, so ignored files
    can never desynchronize the delta from the dirty set.
    """
    records = _status_records(root)
    paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        kind = record[0]
        if kind == "?":
            path = record[2:]
            if not metadata_policy_module.is_metadata_pattern(path):
                paths.append(path)
        elif kind == "1":
            paths.append(record.split(" ", 8)[8])
        elif kind == "2":
            # A rename entry spends a second NUL-separated field on the original
            # path. Consume it so the record stream stays aligned.
            paths.append(record.split(" ", 9)[9])
            index += 1
        elif kind == "u":
            raise GitStateError(
                "ENTRY_UNMERGED",
                f"worktree has an unmerged path: {record.split(' ', 10)[-1]}",
            )
    return paths


def capture_entry(cwd: Path) -> EntryState:
    """Deterministic entry state, captured before any provider is invoked.

    V1 fails closed on a pre-existing staged index. `candidate.tree_identity`
    seeds its temporary index from the real one, so a staged path is already
    folded into the entry candidate tree; committing phase-only work while
    preserving a staged operator index would need partial-index surgery that this
    version does not implement.
    """
    root = repository_root(cwd)
    require_no_active_git_operations(root)
    if _run(root, ["rev-parse", "--verify", "HEAD"]).returncode != 0:
        raise GitStateError(
            "ENTRY_UNBORN_HEAD",
            "repository has no commits, so no entry HEAD can be recorded",
        )
    head = _text(root, ["rev-parse", "HEAD"], "ENTRY_HEAD_UNREADABLE")
    branch = _text(root, ["rev-parse", "--abbrev-ref", "HEAD"], "ENTRY_HEAD_UNREADABLE")

    listing = _run(root, ["ls-files", "--stage", "-z", "--", ":/"])
    if listing.returncode == 0:
        for entry in listing.stdout.decode("utf-8", "surrogateescape").split("\0"):
            if entry.startswith(GITLINK_MODE + " "):
                raise GitStateError(
                    "ENTRY_SUBMODULE_UNSUPPORTED",
                    f"repository contains a submodule gitlink: {entry.split(chr(9))[-1]}",
                )

    staged = _run(root, ["diff", "--cached", "--name-only", "-z", "HEAD", "--", ":/"])
    if staged.returncode != 0:
        raise GitStateError(
            "ENTRY_INDEX_UNREADABLE",
            staged.stderr.decode("utf-8", "replace").strip(),
        )
    staged_paths = [p for p in staged.stdout.decode("utf-8", "surrogateescape").split("\0") if p]
    if staged_paths:
        raise GitStateError(
            "ENTRY_STAGED_CHANGES",
            "refusing to run with a pre-existing staged index; V1 cannot commit "
            f"phase-only work while preserving it: {sorted(staged_paths)}",
        )

    dirty = {path: _identity(root, path) for path in dirty_paths(root)}
    identity = candidate_module.tree_identity(root)
    return EntryState(
        root=root,
        head=head,
        branch=branch,
        tree=str(identity["tree"]),
        dirty=dirty,
        index_identity=index_identity(root),
    )


def current_head(root: Path) -> str:
    """Return the exact checked-out commit without changing repository state."""
    return _text(root, ["rev-parse", "--verify", "HEAD"], "RESUME_HEAD_UNREADABLE")


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Return whether ``ancestor`` reaches ``descendant`` in the local graph."""
    completed = _run(root, ["merge-base", "--is-ancestor", ancestor, descendant])
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise GitStateError(
        "RESUME_HEAD_UNREADABLE",
        completed.stderr.decode("utf-8", "replace").strip()
        or "git could not compare repository ancestry",
    )


def current_branch(root: Path) -> str:
    """Return the exact symbolic branch without changing repository state."""
    return _text(
        root,
        ["rev-parse", "--abbrev-ref", "HEAD"],
        "RESUME_HEAD_UNREADABLE",
    )


def commit_message(root: Path, head: str) -> str:
    """Return a commit's complete message, including its terminating newline."""
    completed = _run(root, ["show", "-s", "--format=%B", head])
    if completed.returncode != 0:
        raise GitStateError(
            "RESUME_COMMIT_MISMATCH",
            completed.stderr.decode("utf-8", "replace").strip(),
        )
    # `--format` terminates the record in addition to the message's own final
    # newline. Normalize only that transport framing before policy comparison.
    return completed.stdout.decode("utf-8", "strict").rstrip("\n") + "\n"


def commit_subject(root: Path, head: str) -> str:
    """Return a commit's subject line."""
    completed = _run(root, ["show", "-s", "--format=%s", head])
    if completed.returncode != 0:
        raise GitStateError(
            "RESUME_COMMIT_MISMATCH",
            completed.stderr.decode("utf-8", "replace").strip(),
        )
    return completed.stdout.decode("utf-8", "strict").strip()


def verify_recorded_commit(
    root: Path,
    parent: str,
    head: str,
    final_tree: str,
    expected_paths: list[str] | tuple[str, ...] | set[str],
) -> None:
    """Verify an already-completed phase commit without requiring a new one.

    Finalization-only resume starts at the recorded phase commit, so the
    current boundary's HEAD is intentionally the same object as the recorded
    commit.  ``verify_commit`` is deliberately stricter for a newly-created
    commit and rejects that shape; this compatibility check keeps the same
    parent/path/content proof for the already-complete case while comparing
    candidate content only on phase-owned paths.
    """
    if head == parent:
        raise GitStateError("COMMIT_HEAD_UNCHANGED", "recorded commit is the entry HEAD")
    actual_parent = _text(root, ["rev-parse", f"{head}^"], "COMMIT_PARENT_UNREADABLE")
    if actual_parent != parent:
        raise GitStateError(
            "COMMIT_PARENT_MISMATCH",
            f"recorded commit's parent is {actual_parent}, expected {parent}",
        )
    expected = sorted(expected_paths)
    committed = _run(
        root,
        ["diff-tree", "-r", "-z", "--no-renames", "--name-only", parent, head],
    )
    if committed.returncode != 0:
        raise GitStateError(
            "COMMIT_VERIFY_FAILED",
            committed.stderr.decode("utf-8", "replace").strip(),
        )
    got = sorted(
        path
        for path in committed.stdout.decode("utf-8", "surrogateescape").split("\0")
        if path
    )
    if got != expected:
        raise GitStateError(
            "COMMIT_PATHS_MISMATCH",
            f"recorded commit changed {got}, phase manifest was {expected}",
        )
    if expected:
        drift = _run(
            root,
            [
                "diff-tree", "-r", "-z", "--no-renames", "--name-only",
                final_tree, f"{head}^{{tree}}", "--",
                *[_literal(path) for path in expected],
            ],
        )
        if drift.returncode != 0:
            raise GitStateError(
                "COMMIT_VERIFY_FAILED",
                drift.stderr.decode("utf-8", "replace").strip(),
            )
        drifted = sorted(
            path
            for path in drift.stdout.decode("utf-8", "surrogateescape").split("\0")
            if path
        )
        if drifted:
            raise GitStateError(
                "COMMIT_CONTENT_DRIFT",
                f"recorded commit differs from the final candidate tree: {drifted}",
            )


def phase_delta(root: Path, before_tree: str, after_tree: str) -> list[Change]:
    """Paths whose bytes, mode, or existence differ between two candidate trees.

    `--no-renames` is deliberate: a rename must surface as its delete/add pair so
    the path list handed to `git add` is exact and total.
    """
    if before_tree == after_tree:
        return []
    # `--raw` rather than `--name-status`: the mode columns are what let a
    # gitlink be refused. The entry scan only covers paths that already existed,
    # so a phase that runs `git init` in a subdirectory would otherwise commit a
    # 160000 entry whose delta semantics V1 does not define.
    completed = _run(
        root,
        ["diff-tree", "-r", "-z", "--no-renames", "--raw", before_tree, after_tree],
    )
    if completed.returncode != 0:
        raise GitStateError(
            "DELTA_FAILED", completed.stderr.decode("utf-8", "replace").strip()
        )
    fields = completed.stdout.decode("utf-8", "surrogateescape").split("\0")
    changes: list[Change] = []
    index = 0
    while index + 1 < len(fields):
        meta = fields[index]
        path = fields[index + 1]
        index += 2
        if not meta or not path:
            continue
        columns = meta.lstrip(":").split(" ")
        if len(columns) < 5:
            raise GitStateError("DELTA_FAILED", f"unparsable diff-tree record: {meta!r}")
        source_mode, target_mode, status = columns[0], columns[1], columns[4]
        if GITLINK_MODE in (source_mode, target_mode):
            raise GitStateError(
                "DELTA_SUBMODULE_UNSUPPORTED",
                f"phase delta contains a submodule gitlink: {path}",
            )
        changes.append(Change(status=status[0], path=path))
    return sorted(changes, key=lambda change: change.path)


def _tree_identities(
    root: Path,
    treeish: str,
    paths: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Read regular-file and symlink identities from a candidate tree."""
    arguments = ["ls-tree", "-r", "-z", "--full-tree", treeish]
    if paths is not None:
        selected = sorted(set(paths))
        if not selected:
            return {}
        arguments.extend(["--", *[_literal(path) for path in selected]])
    listing = _run(root, arguments)
    if listing.returncode != 0:
        raise GitStateError(
            "CANDIDATE_MANIFEST_TREE_UNREADABLE",
            listing.stderr.decode("utf-8", "replace").strip(),
        )
    identities: dict[str, dict[str, Any]] = {}
    for record in listing.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode_raw, kind_raw, object_id_raw = metadata.split(b" ", 2)
            path = raw_path.decode("utf-8")
            mode = mode_raw.decode("ascii")
            kind = kind_raw.decode("ascii")
            object_id = object_id_raw.decode("ascii")
        except (ValueError, UnicodeDecodeError) as error:
            raise GitStateError(
                "CANDIDATE_MANIFEST_TREE_UNREADABLE",
                "candidate tree contains an invalid path or entry",
            ) from error
        if not path or path.startswith("/") or "\x00" in path:
            raise GitStateError(
                "CANDIDATE_MANIFEST_PATH_INVALID",
                "candidate tree contains an invalid relative path",
            )
        if kind != "blob" or mode == GITLINK_MODE:
            raise GitStateError(
                "CANDIDATE_MANIFEST_SUBMODULE_UNSUPPORTED",
                f"candidate tree contains unsupported entry: {path}",
            )
        if mode not in ("100644", "100755", "120000"):
            raise GitStateError(
                "CANDIDATE_MANIFEST_PATH_TYPE_UNSUPPORTED",
                f"candidate tree contains unsupported mode {mode}: {path}",
            )
        material = _run(root, ["cat-file", "blob", object_id])
        if material.returncode != 0:
            raise GitStateError(
                "CANDIDATE_MANIFEST_TREE_UNREADABLE",
                material.stderr.decode("utf-8", "replace").strip(),
            )
        if path in identities:
            raise GitStateError(
                "CANDIDATE_MANIFEST_TREE_UNREADABLE",
                f"candidate tree repeats path: {path}",
            )
        identities[path] = {
            "present": True,
            "type": "symlink" if mode == "120000" else "file",
            "mode": mode,
            "size_bytes": len(material.stdout),
            "sha256": hashlib.sha256(material.stdout).hexdigest(),
        }
    return identities


def _absent_candidate_identity() -> dict[str, Any]:
    return {
        "present": False,
        "type": None,
        "mode": None,
        "size_bytes": None,
        "sha256": None,
    }


def _manifest_path_valid(path: str) -> bool:
    if not isinstance(path, str) or not path or "\x00" in path:
        return False
    parsed = PurePosixPath(path)
    return not parsed.is_absolute() and ".." not in parsed.parts and "." not in parsed.parts


def validate_candidate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the closed V1 shape before using candidate ownership evidence."""
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema", "entry_tree", "candidate_tree", "paths",
    }:
        raise GitStateError(
            "CANDIDATE_MANIFEST_INVALID",
            "candidate manifest has an unsupported schema or fields",
        )
    if manifest["schema"] != CANDIDATE_MANIFEST_SCHEMA:
        raise GitStateError(
            "CANDIDATE_MANIFEST_INVALID",
            "candidate manifest schema is unsupported",
        )
    for name in ("entry_tree", "candidate_tree"):
        value = manifest[name]
        if not isinstance(value, str) or len(value) != 40 or any(
            character not in "0123456789abcdef" for character in value
        ):
            raise GitStateError(
                "CANDIDATE_MANIFEST_INVALID",
                f"candidate manifest {name} is not a Git object id",
            )
    paths = manifest["paths"]
    if not isinstance(paths, dict):
        raise GitStateError(
            "CANDIDATE_MANIFEST_INVALID", "candidate manifest paths are not an object"
        )
    for path, identity in paths.items():
        if not _manifest_path_valid(path) or not isinstance(identity, dict):
            raise GitStateError(
                "CANDIDATE_MANIFEST_INVALID", "candidate manifest path is invalid"
            )
        if set(identity) != set(_CANDIDATE_IDENTITY_KEYS):
            raise GitStateError(
                "CANDIDATE_MANIFEST_INVALID",
                f"candidate manifest identity fields are invalid for {path}",
            )
        present = identity["present"]
        if not isinstance(present, bool):
            raise GitStateError(
                "CANDIDATE_MANIFEST_INVALID", f"candidate presence is invalid for {path}"
            )
        if present:
            if identity["type"] not in ("file", "symlink"):
                raise GitStateError(
                    "CANDIDATE_MANIFEST_INVALID", f"candidate type is invalid for {path}"
                )
            if identity["mode"] not in ("100644", "100755", "120000"):
                raise GitStateError(
                    "CANDIDATE_MANIFEST_INVALID", f"candidate mode is invalid for {path}"
                )
            if not isinstance(identity["size_bytes"], int) or identity["size_bytes"] < 0:
                raise GitStateError(
                    "CANDIDATE_MANIFEST_INVALID", f"candidate size is invalid for {path}"
                )
            digest = identity["sha256"]
            if not isinstance(digest, str) or len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise GitStateError(
                    "CANDIDATE_MANIFEST_INVALID", f"candidate digest is invalid for {path}"
                )
        elif any(identity[key] is not None for key in _CANDIDATE_IDENTITY_KEYS[1:]):
            raise GitStateError(
                "CANDIDATE_MANIFEST_INVALID",
                f"absent candidate identity is not null for {path}",
            )
    return manifest


def candidate_manifest(
    root: Path,
    entry_tree: str,
    candidate_tree: str,
    paths: list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, Any]:
    """Build a closed manifest for phase-owned paths relative to entry_tree."""
    changed = (
        {change.path for change in phase_delta(root, entry_tree, candidate_tree)}
        if paths is None else set(paths)
    )
    if any(not _manifest_path_valid(path) for path in changed):
        raise GitStateError(
            "CANDIDATE_MANIFEST_PATH_INVALID",
            "phase-owned candidate path is not a safe relative path",
        )
    candidate_identities = _tree_identities(root, candidate_tree, changed)
    entry_identities = (
        _tree_identities(root, entry_tree, changed) if paths is None else {}
    )
    # An explicit path set is allowed to include an unchanged path when an
    # inherited candidate already exists at the current boundary. Its current
    # identity remains evidence even though it is absent from tree delta.
    records = {
        path: candidate_identities.get(path, _absent_candidate_identity())
        for path in sorted(changed)
    }
    if paths is None:
        records = {
            path: identity
            for path, identity in records.items()
            if entry_identities.get(path, _absent_candidate_identity()) != identity
        }
    manifest = {
        "schema": CANDIDATE_MANIFEST_SCHEMA,
        "entry_tree": entry_tree,
        "candidate_tree": candidate_tree,
        "paths": records,
    }
    return validate_candidate_manifest(manifest)


def candidate_manifest_conflicts(
    root: Path, current_tree: str, manifest: dict[str, Any]
) -> list[str]:
    """Return inherited phase paths whose current identity differs."""
    validate_candidate_manifest(manifest)
    current = _tree_identities(root, current_tree, set(manifest["paths"]))
    absent = _absent_candidate_identity()
    return sorted(
        path for path, expected in manifest["paths"].items()
        if current.get(path, absent) != expected
    )


def _stage_exact_paths(root: Path, paths: list[str]) -> None:
    """Refresh owned tracked paths without re-admitting them through ignores."""
    indexed = _run(root, ["ls-files", "--cached", "--full-name", "-z", "--",
                          *[_literal(path) for path in paths]])
    if indexed.returncode != 0:
        raise GitStateError(
            "GIT_STAGE_FAILED", indexed.stderr.decode("utf-8", "replace").strip()
        )
    tracked = set(indexed.stdout.decode("utf-8", "surrogateescape").split("\0"))
    # Unlike candidate capture, this is the real index: every update remains
    # limited to the explicitly owned paths. Never refresh the whole worktree.
    for option, selected in (
        ("-u", [path for path in paths if path in tracked]),
        ("-A", [path for path in paths if path not in tracked]),
    ):
        if not selected:
            continue
        staged = _run(root, ["add", option, "--", *[_literal(path) for path in selected]])
        if staged.returncode != 0:
            raise GitStateError(
                "GIT_STAGE_FAILED", staged.stderr.decode("utf-8", "replace").strip()
            )


def commit(root: Path, paths: list[str], message: str, expected_branch: str | None = None) -> str:
    """Stage exactly `paths` and commit. Message travels on stdin, never argv."""
    if expected_branch is not None:
        curr = current_branch(root)
        if curr != expected_branch:
            raise GitStateError(
                "GIT_AUTHORITY_BRANCH_MISMATCH",
                f"current branch {curr!r} differs from expected entry branch {expected_branch!r}",
            )
    if not paths:
        raise GitStateError(
            "GIT_COMMIT_EMPTY_SCOPE", "refusing a commit without phase-owned paths"
        )
    pathspecs = [_literal(path) for path in paths]
    _stage_exact_paths(root, paths)
    # No -c override, no --no-verify: repository hooks run and are inside the
    # trust boundary. A hook rejection is a real GIT_COMMIT_FAILED.
    committed = _run(
        root,
        [
            "commit",
            "--only",
            "--cleanup=verbatim",
            "--file=-",
            "--",
            *pathspecs,
        ],
        stdin=message.encode("utf-8"),
    )
    if committed.returncode != 0:
        detail = (
            committed.stderr.decode("utf-8", "replace").strip()
            or committed.stdout.decode("utf-8", "replace").strip()
        )
        raise GitStateError("GIT_COMMIT_FAILED", detail)
    return _text(root, ["rev-parse", "HEAD"], "GIT_COMMIT_FAILED")


def verify_commit(
    root: Path,
    entry: EntryState,
    delta: list[Change],
    final_tree: str,
    head: str,
    *,
    expected_parent: str | None = None,
) -> None:
    """Prove mechanically what was committed and what was left alone."""
    expected = sorted(change.path for change in delta)

    if head == entry.head:
        raise GitStateError("COMMIT_HEAD_UNCHANGED", "HEAD did not advance")
    parent = _text(root, ["rev-parse", f"{head}^"], "COMMIT_PARENT_UNREADABLE")
    target_parent = expected_parent or entry.head
    if parent != target_parent:
        raise GitStateError(
            "COMMIT_PARENT_MISMATCH",
            f"new commit's parent is {parent}, entry HEAD was {target_parent}",
        )

    committed = _run(
        root, ["diff-tree", "-r", "-z", "--no-renames", "--name-only",
               entry.head, head]
    )
    if committed.returncode != 0:
        raise GitStateError(
            "COMMIT_VERIFY_FAILED",
            committed.stderr.decode("utf-8", "replace").strip(),
        )
    got = sorted(
        p for p in committed.stdout.decode("utf-8", "surrogateescape").split("\0") if p
    )
    if got != expected:
        raise GitStateError(
            "COMMIT_PATHS_MISMATCH",
            f"commit changed {got}, phase delta was {expected}",
        )

    # Path set alone would not catch a worktree write between the final-tree
    # capture and `git add`. Bind the committed blobs and modes to the recorded
    # final candidate for exactly the delta paths.
    if expected:
        drift = _run(
            root,
            ["diff-tree", "-r", "-z", "--no-renames", "--name-only",
             final_tree, f"{head}^{{tree}}", "--",
             *[_literal(path) for path in expected]],
        )
        if drift.returncode != 0:
            raise GitStateError(
                "COMMIT_VERIFY_FAILED",
                drift.stderr.decode("utf-8", "replace").strip(),
            )
        drifted = sorted(
            p for p in drift.stdout.decode("utf-8", "surrogateescape").split("\0") if p
        )
        if drifted:
            raise GitStateError(
                "COMMIT_CONTENT_DRIFT",
                f"committed bytes differ from the final candidate tree: {drifted}",
            )

    exit_dirty = set(dirty_paths(root))
    if exit_dirty & set(expected):
        raise GitStateError(
            "COMMIT_PHASE_DIRT_REMAINS",
            f"phase paths still dirty after commit: {sorted(exit_dirty & set(expected))}",
        )
    expected_remaining_dirty = set(entry.dirty) - set(expected)
    if exit_dirty != expected_remaining_dirty:
        raise GitStateError(
            "ENTRY_DIRT_NOT_PRESERVED",
            f"exit dirty set {sorted(exit_dirty)} differs from preserved entry "
            f"{sorted(expected_remaining_dirty)}",
        )
    for path, identity in entry.dirty.items():
        if path in expected:
            continue
        if _identity(root, path) != identity:
            raise GitStateError(
                "ENTRY_DIRT_NOT_PRESERVED", f"operator dirt was modified: {path}"
            )


def _config_values(root: Path, key: str) -> list[str]:
    completed = _run(root, ["config", "--get-all", key])
    if completed.returncode == 1:
        return []
    if completed.returncode != 0:
        raise GitStateError(
            "GIT_PUSH_TARGET_INVALID", f"cannot read configured upstream key {key}"
        )
    return completed.stdout.decode("utf-8", "replace").splitlines()


def push_target(root: Path, expected_branch: str | None = None) -> PushTarget:
    """Resolve exactly the current branch's configured upstream push target."""
    symbolic = _run(root, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    if symbolic.returncode != 0:
        raise GitStateError(
            "GIT_PUSH_TARGET_INVALID",
            "HEAD is detached; preserve the local phase commit, attach the intended branch, "
            "configure its upstream, and push manually",
        )
    branch = symbolic.stdout.decode("utf-8", "replace").strip()
    if expected_branch is not None and branch != expected_branch:
        raise GitStateError(
            "GIT_AUTHORITY_BRANCH_MISMATCH",
            f"current branch {branch!r} differs from expected entry branch {expected_branch!r}",
        )
    remotes = _config_values(root, f"branch.{branch}.remote")
    merges = _config_values(root, f"branch.{branch}.merge")
    if len(remotes) != 1 or len(merges) != 1:
        raise GitStateError(
            "GIT_PUSH_TARGET_INVALID",
            f"branch {branch!r} needs exactly one configured upstream remote and branch; "
            "the local phase commit is preserved for operator recovery",
        )
    remote, remote_ref = remotes[0], merges[0]
    if not remote or not remote_ref.startswith("refs/heads/") or remote_ref == "refs/heads/":
        raise GitStateError(
            "GIT_PUSH_TARGET_INVALID",
            f"branch {branch!r} has an unusable configured upstream; the local phase "
            "commit is preserved for operator recovery",
        )
    valid_ref = _run(root, ["check-ref-format", remote_ref])
    if valid_ref.returncode != 0:
        raise GitStateError(
            "GIT_PUSH_TARGET_INVALID",
            f"branch {branch!r} has an invalid upstream branch ref; the local phase "
            "commit is preserved for operator recovery",
        )
    urls = _run(root, ["remote", "get-url", "--push", "--all", "--", remote])
    push_urls = urls.stdout.decode("utf-8", "replace").splitlines()
    if urls.returncode != 0 or len(push_urls) != 1:
        raise GitStateError(
            "GIT_PUSH_TARGET_INVALID",
            f"upstream remote {remote!r} needs exactly one push URL; the local phase "
            "commit is preserved for operator recovery",
        )
    return PushTarget(
        branch, remote, remote_ref, remote_ref.removeprefix("refs/heads/"), push_urls[0]
    )


def remote_head(root: Path, target: PushTarget) -> str | None:
    completed = _run(
        root, ["ls-remote", "--refs", "--", target.push_url, target.remote_ref]
    )
    if completed.returncode != 0:
        raise GitStateError(
            "GIT_PUSH_FAILED",
            f"cannot query upstream {target.remote}/{target.upstream_branch}",
        )
    rows = [line for line in completed.stdout.decode("utf-8", "replace").splitlines() if line]
    if not rows:
        return None
    if len(rows) != 1:
        raise GitStateError(
            "GIT_PUSH_FAILED",
            f"upstream query for {target.remote}/{target.upstream_branch} was ambiguous",
        )
    sha, separator, ref = rows[0].partition("\t")
    if not separator or ref != target.remote_ref or len(sha) != 40:
        raise GitStateError(
            "GIT_PUSH_FAILED",
            f"upstream query for {target.remote}/{target.upstream_branch} was malformed",
        )
    return sha


def preexisting_unpushed_count(
    root: Path, remote_sha: str | None, entry_head: str
) -> int | None:
    if remote_sha is None:
        return None
    ancestor = _run(root, ["merge-base", "--is-ancestor", remote_sha, entry_head])
    if ancestor.returncode != 0:
        # A divergent SHA may not exist in the local object database at all.
        # Either way, the ancestor count is indeterminate and does not prevent
        # the normal non-force push from producing the authoritative rejection.
        return None
    count = _text(
        root, ["rev-list", "--count", f"{remote_sha}..{entry_head}"], "GIT_PUSH_FAILED"
    )
    try:
        return int(count)
    except ValueError as error:
        raise GitStateError("GIT_PUSH_FAILED", "git returned an invalid ancestor count") from error


def push_verified(root: Path, target: PushTarget, phase_commit: str) -> str | None:
    """Push one explicit commit/ref pair and query the live target after any attempt."""
    command_detail: str | None = None
    completed: subprocess.CompletedProcess | None = None
    try:
        completed = _run(
            root,
            [
                "push", "--no-force", "--no-follow-tags", "--no-mirror", "--porcelain",
                "--", target.push_url, f"{phase_commit}:{target.remote_ref}",
            ],
        )
    except GitStateError as error:
        command_detail = f"push invocation failed: {error.detail}"

    post_head: str | None = None
    query_detail: str | None = None
    try:
        post_head = remote_head(root, target)
    except GitStateError as error:
        query_detail = error.detail

    if completed is None or completed.returncode != 0:
        if command_detail is None and completed is not None:
            output = (
                completed.stderr.decode("utf-8", "replace").strip()
                or completed.stdout.decode("utf-8", "replace").strip()
            )
            output = output.replace(target.push_url, target.remote)
            command_detail = f"normal non-force push was rejected or failed: {output}"
        failure = command_detail or "push failed"
        if post_head == phase_commit:
            failure += "; upstream nevertheless equals the phase commit"
        if query_detail:
            failure += f"; post-attempt verification failed: {query_detail}"
        raise GitPushError(failure, post_head)
    if query_detail:
        raise GitPushError(
            f"push returned success but live verification failed: {query_detail}",
            post_head,
            code="GIT_PUSH_POST_VERIFY_MISMATCH",
            command_succeeded=True,
        )
    if post_head != phase_commit:
        raise GitPushError(
            "push returned success but the upstream no longer equals the phase commit; "
            "it may have advanced concurrently",
            post_head,
            code="GIT_PUSH_POST_VERIFY_MISMATCH",
            command_succeeded=True,
        )
    return post_head


def verify_untouched(root: Path, entry: EntryState) -> None:
    """Postcondition for a run that committed nothing."""
    head = _text(root, ["rev-parse", "HEAD"], "COMMIT_VERIFY_FAILED")
    if head != entry.head:
        raise GitStateError(
            "HEAD_MOVED_WITHOUT_COMMIT",
            f"HEAD is {head}, entry HEAD was {entry.head}",
        )
    exit_dirty = set(dirty_paths(root))
    if exit_dirty != set(entry.dirty):
        raise GitStateError(
            "ENTRY_DIRT_NOT_PRESERVED",
            f"exit dirty set {sorted(exit_dirty)} differs from entry "
            f"{sorted(entry.dirty)}",
        )
    for path, identity in entry.dirty.items():
        if _identity(root, path) != identity:
            raise GitStateError(
                "ENTRY_DIRT_NOT_PRESERVED", f"operator dirt was modified: {path}"
            )
