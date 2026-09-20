"""Explicit entry-candidate adoption for pre-existing worktree modifications.

Provider-free authority record binding an approved worktree candidate that
predated dispatcher execution. Staged state is rejected in V1.

Entry adoption distinguishes two distinct validation moments:
1. Strict pre-provider entry validation (`validate_entry` / `validate_strict_entry`):
   Before provider one, proves that the live candidate exactly matches the
   provider-free adoption receipt byte-for-byte and mode-for-mode.
2. Retained boundary validation after mutating stages (`validate_retained_entry`):
   Validates the retained receipt structurally and cryptographically, checks
   repository identity and immutable base Git context (branch, HEAD, base tree,
   clean real index), and verifies that original Git candidate objects remain
   available, while allowing mutating stages to legitimately revise adopted paths.
"""

from __future__ import annotations

from copy import deepcopy
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from . import gitstate, path_disposition


SCHEMA = "agent-phase-entry-adoption-v1"
SOURCE_KIND = "entry_worktree"
MAX_PATHS = 1024
FIELDS = frozenset({
    "schema",
    "source_kind",
    "phase_id",
    "request_sha256",
    "repository",
    "branch",
    "base_head",
    "base_tree",
    "entry_index",
    "adopted_paths",
    "path_metadata",
    "candidate_tree",
    "candidate_manifest",
    "unadopted_dirty_paths",
    "reason",
    "timestamp",
    "provider_invocations",
    "sha256",
})


class EntryAdoptionError(ValueError):
    """Refusal on invalid entry candidate adoption."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def encoded(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def repository_identity(root: Path) -> dict[str, Any]:
    info = root.stat()
    return {
        "root": str(root),
        "device": info.st_dev,
        "inode": info.st_ino,
        "context": ".",
    }


def canonical_paths(paths: list[str]) -> list[str]:
    if not paths or len(paths) > MAX_PATHS:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID",
            f"adoption requires 1..{MAX_PATHS} explicitly selected paths",
        )
    path_disposition.validate_dispositions(
        [{"path": p, "disposition": "phase_owned"} for p in paths]
    )
    selected = sorted(set(paths))
    return selected


def require_safe_paths(root: Path, paths: list[str]) -> None:
    for path in paths:
        target = root / path
        if target.is_symlink() and target.is_dir():
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_PATH_INVALID",
                f"adopted path is a symlink to a directory: {path}",
            )
        if target.is_dir() and not target.is_symlink():
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_PATH_INVALID",
                f"adopted path is occupied by a directory: {path}",
            )
        for parent in target.parents:
            if parent == root:
                break
            if parent.is_symlink():
                raise EntryAdoptionError(
                    "ENTRY_ADOPTION_PATH_INVALID",
                    f"adopted path traverses a symlink alias: {path}",
                )


def _file_mode_and_blob(
    root: Path, path: str, *, write_object: bool = True
) -> tuple[str, str, str, bool]:
    """Inspect a worktree file: mode ('100644', '100755', '120000'), blob SHA, content sha256, tracked."""
    target = root / path
    if not target.exists() and not target.is_symlink():
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_PATH_MISSING", f"adopted path does not exist: {path}"
        )

    if target.is_symlink():
        mode = "120000"
        link_target = os.readlink(target).encode("utf-8", "surrogateescape")
        content_sha = hashlib.sha256(link_target).hexdigest()
        cmd = ["git", "hash-object", "--stdin"]
        if write_object:
            cmd = ["git", "hash-object", "-w", "--stdin"]
        blob_res = subprocess.run(
            cmd,
            input=link_target,
            cwd=root,
            capture_output=True,
            check=False,
        )
    elif target.is_file():
        mode = "100755" if os.access(target, os.X_OK) else "100644"
        content = target.read_bytes()
        content_sha = hashlib.sha256(content).hexdigest()
        cmd = ["git", "hash-object", "--", path]
        if write_object:
            cmd = ["git", "hash-object", "-w", "--", path]
        blob_res = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_PATH_INVALID", f"unsupported object type: {path}"
        )

    if blob_res.returncode != 0:
        err_msg = (
            blob_res.stderr.decode("utf-8", "replace").strip()
            if isinstance(blob_res.stderr, bytes)
            else str(blob_res.stderr).strip()
        )
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_HASH_FAILED",
            f"failed to compute blob hash for {path}: {err_msg}",
        )
    blob_sha = (
        blob_res.stdout.decode("utf-8", "replace").strip()
        if isinstance(blob_res.stdout, bytes)
        else str(blob_res.stdout).strip()
    )

    # Tracked status
    ls_res = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=root,
        capture_output=True,
    )
    tracked = ls_res.returncode == 0
    return mode, blob_sha, content_sha, tracked


def _synthetic_candidate_tree(
    root: Path, base_tree: str, path_meta: dict[str, dict[str, Any]]
) -> str:
    """Construct synthetic candidate tree from base_tree + adopted path blobs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_idx = Path(tmpdir) / "index"
        env = {**os.environ, "GIT_INDEX_FILE": str(tmp_idx)}

        # Seed from base_tree
        res = subprocess.run(
            ["git", "read-tree", base_tree],
            cwd=root,
            env=env,
            capture_output=True,
            check=False,
        )
        if res.returncode != 0:
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_TREE_FAILED", "failed to read base tree into temporary index"
            )

        # Update index with each adopted path
        for path, meta in path_meta.items():
            subprocess.run(
                [
                    "git",
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    meta["mode"],
                    meta["blob_sha"],
                    path,
                ],
                cwd=root,
                env=env,
                capture_output=True,
                check=True,
            )

        write_res = subprocess.run(
            ["git", "write-tree"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if write_res.returncode != 0:
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_TREE_FAILED", f"failed to write synthetic candidate tree: {write_res.stderr.strip()}"
            )
        return write_res.stdout.strip()


def create(
    request_path: Path,
    root: Path,
    paths: list[str],
    *,
    reason: str,
    phase_id: str | None = None,
) -> dict[str, Any]:
    """Create a provider-free entry adoption receipt for pre-existing worktree candidate."""
    if not reason or not reason.strip():
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID", "operator reason is required"
        )

    root = gitstate.repository_root(root).resolve()
    gitstate.require_no_active_git_operations(root)

    # Reject staged changes in V1!
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z", "HEAD", "--", ":/"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if staged.returncode != 0:
        raise EntryAdoptionError(
            "ENTRY_INDEX_UNREADABLE", staged.stderr.decode("utf-8", "replace").strip()
        )
    staged_paths = [p for p in staged.stdout.decode("utf-8", "surrogateescape").split("\0") if p]
    if staged_paths:
        raise EntryAdoptionError(
            "ENTRY_STAGED_CHANGES",
            f"V1 entry adoption rejects pre-existing staged index: {sorted(staged_paths)}",
        )

    clean_paths = canonical_paths(paths)
    require_safe_paths(root, clean_paths)

    from . import run as run_module
    from .request import load_any_request
    from . import adoption as adoption_module

    req_data = load_any_request(request_path)
    req_sha = adoption_module.digest(req_data.as_dict())
    actual_phase_id = phase_id or run_module.phase_id_from_request(request_path)

    head = gitstate.current_head(root)
    branch = gitstate.current_branch(root)
    base_tree = gitstate._text(root, ["rev-parse", "HEAD^{tree}"], "TREE_FAILED")
    idx_id = gitstate.index_identity(root)

    # Collect path metadata
    path_meta: dict[str, dict[str, Any]] = {}
    for p in clean_paths:
        mode, blob_sha, content_sha, tracked = _file_mode_and_blob(root, p)
        path_meta[p] = {
            "mode": mode,
            "blob_sha": blob_sha,
            "content_sha256": content_sha,
            "tracked": tracked,
        }

    candidate_tree = _synthetic_candidate_tree(root, base_tree, path_meta)
    manifest = gitstate.candidate_manifest(
        root, base_tree, candidate_tree, paths=clean_paths
    )

    all_dirty = set(gitstate.dirty_paths(root))
    unadopted_dirty = sorted(all_dirty - set(clean_paths))

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "source_kind": SOURCE_KIND,
        "phase_id": actual_phase_id,
        "request_sha256": req_sha,
        "repository": repository_identity(root),
        "branch": branch,
        "base_head": head,
        "base_tree": base_tree,
        "entry_index": idx_id,
        "adopted_paths": clean_paths,
        "path_metadata": path_meta,
        "candidate_tree": candidate_tree,
        "candidate_manifest": manifest,
        "unadopted_dirty_paths": unadopted_dirty,
        "reason": reason.strip(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "provider_invocations": 0,
    }
    record["sha256"] = digest(record)
    return record


def _validate_record_structure(record: dict[str, Any]) -> None:
    if not isinstance(record, dict) or set(record) != FIELDS:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID", "invalid entry adoption receipt fields"
        )
    if record.get("schema") != SCHEMA:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID", f"unsupported schema: {record.get('schema')}"
        )
    if record.get("source_kind") != SOURCE_KIND:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID", f"unsupported source kind: {record.get('source_kind')}"
        )

    expected = deepcopy(record)
    record_hash = expected.pop("sha256", None)
    if digest(expected) != record_hash:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID", "entry adoption checksum differs"
        )


def _validate_base_git_context(root: Path, record: dict[str, Any]) -> list[str]:
    repo_id = repository_identity(root)
    if (
        record["repository"]["device"] != repo_id["device"]
        or record["repository"]["inode"] != repo_id["inode"]
    ):
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID", "repository identity differs from adoption receipt"
        )

    gitstate.require_no_active_git_operations(root)

    curr_branch = gitstate.current_branch(root)
    if curr_branch != record["branch"]:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID",
            f"repository branch {curr_branch!r} differs from adoption {record['branch']!r}",
        )

    curr_head = gitstate.current_head(root)
    if curr_head != record["base_head"]:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID",
            f"entry HEAD {curr_head} differs from adoption {record['base_head']}",
        )

    curr_tree = gitstate._text(root, ["rev-parse", "HEAD^{tree}"], "TREE_FAILED")
    if curr_tree != record["base_tree"]:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID",
            f"entry base tree {curr_tree} differs from adoption {record['base_tree']}",
        )

    # Reject staged changes
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z", "HEAD", "--", ":/"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if staged.returncode != 0 or any(
        p for p in staged.stdout.decode("utf-8", "surrogateescape").split("\0") if p
    ):
        raise EntryAdoptionError(
            "ENTRY_STAGED_CHANGES", "V1 entry adoption rejects pre-existing staged index"
        )

    curr_index = gitstate.index_identity(root)
    if curr_index != record["entry_index"]:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID", "entry index differs from adoption receipt"
        )

    clean_paths = canonical_paths(record["adopted_paths"])
    require_safe_paths(root, clean_paths)
    return clean_paths


def _validate_retained_git_objects(
    root: Path, record: dict[str, Any], clean_paths: list[str]
) -> None:
    res = subprocess.run(
        ["git", "cat-file", "-e", f"{record['base_tree']}^{{tree}}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_OBJECT_MISSING",
            f"base tree object {record['base_tree']} is unavailable in git",
        )

    res = subprocess.run(
        ["git", "cat-file", "-e", f"{record['candidate_tree']}^{{tree}}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if res.returncode != 0:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_OBJECT_MISSING",
            f"candidate tree object {record['candidate_tree']} is unavailable in git",
        )

    path_meta = record.get("path_metadata", {})
    for p in clean_paths:
        meta = path_meta.get(p)
        if not meta or not isinstance(meta, dict) or "blob_sha" not in meta:
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_INVALID", f"missing metadata for adopted path {p}"
            )
        res = subprocess.run(
            ["git", "cat-file", "-e", meta["blob_sha"]],
            cwd=root,
            capture_output=True,
            check=False,
        )
        if res.returncode != 0:
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_OBJECT_MISSING",
                f"adopted blob object {meta['blob_sha']} for path {p} is unavailable in git",
            )

    synthetic = _synthetic_candidate_tree(root, record["base_tree"], path_meta)
    if synthetic != record["candidate_tree"]:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_TREE_MISMATCH",
            "synthetic candidate tree does not match receipt candidate tree",
        )

    manifest = gitstate.candidate_manifest(
        root, record["base_tree"], record["candidate_tree"], paths=clean_paths
    )
    if manifest != record["candidate_manifest"]:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID",
            "adopted Git candidate manifest differs from receipt",
        )


def validate_retained_entry(
    root: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    """Validate retained entry adoption receipt at stage and finalization boundaries.

    Verifies the receipt's structural and cryptographic integrity, repository
    identity, and immutable Git base context (branch, HEAD, base tree, real index).
    Proves that original adopted candidate Git objects remain available and
    consistent without requiring current worktree bytes or modes to match
    pre-provider entry snapshots.
    """
    _validate_record_structure(record)
    clean_paths = _validate_base_git_context(root, record)
    _validate_retained_git_objects(root, record, clean_paths)
    return record


def validate_strict_entry(
    root: Path,
    record: dict[str, Any],
    request_path: Path | None = None,
    phase_id: str | None = None,
    request: Any = None,
) -> dict[str, Any]:
    """Validate entry adoption receipt strictly against live repository before provider execution.

    In addition to structural, repository, and Git base context validation,
    strictly verifies that live worktree files for all adopted paths exist
    and match the entry snapshot byte-for-byte and mode-for-mode. Also verifies
    retained Git objects, synthetic candidate tree, and candidate manifest.
    """
    _validate_record_structure(record)
    clean_paths = _validate_base_git_context(root, record)

    if phase_id is not None and record["phase_id"] != phase_id:
        raise EntryAdoptionError(
            "ENTRY_ADOPTION_INVALID", "adoption is bound to a different phase"
        )

    if request is not None:
        from . import adoption as adoption_module
        expected_sha = adoption_module.digest(request.as_dict())
        if record["request_sha256"] != expected_sha:
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_INVALID",
                "adoption is bound to a different substantive request",
            )
    elif request_path is not None:
        raw_sha = hashlib.sha256(request_path.read_bytes()).hexdigest()
        from .request import load_any_request
        from . import adoption as adoption_module
        try:
            req_data = load_any_request(request_path)
            dict_sha = adoption_module.digest(req_data.as_dict())
        except Exception:
            dict_sha = None
        if record["request_sha256"] not in (raw_sha, dict_sha):
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_INVALID",
                "adoption is bound to a different substantive request",
            )

    # Re-verify each adopted path byte-for-byte against current worktree
    path_meta = record.get("path_metadata", {})
    for p in clean_paths:
        meta = path_meta.get(p)
        if not meta:
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_INVALID", f"missing metadata for adopted path {p}"
            )
        target = root / p
        if not target.exists() and not target.is_symlink():
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_PATH_MISSING", f"adopted path missing from worktree: {p}"
            )
        mode, blob_sha, content_sha, tracked = _file_mode_and_blob(root, p, write_object=False)
        if blob_sha != meta["blob_sha"] or content_sha != meta["content_sha256"]:
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_DRIFT", f"adopted file {p} has drifted since adoption"
            )
        if mode != meta["mode"]:
            raise EntryAdoptionError(
                "ENTRY_ADOPTION_DRIFT", f"adopted file {p} mode changed since adoption"
            )

    _validate_retained_git_objects(root, record, clean_paths)
    return record


def validate_entry(
    root: Path,
    record: dict[str, Any],
    request_path: Path | None = None,
    phase_id: str | None = None,
    request: Any = None,
) -> dict[str, Any]:
    """Validate entry adoption receipt strictly against live repository before provider execution.

    `validate_entry` always performs strict pre-provider entry validation.
    It verifies that the live worktree matches the provider-free adoption receipt
    byte-for-byte and mode-for-mode, regardless of whether optional request/phase
    binding arguments are supplied. Any live file drift raises ENTRY_ADOPTION_DRIFT.

    For post-entry boundary validation after mutating stages (where legitimate
    worktree changes occur), callers must explicitly use `validate_retained_entry()`.
    """
    return validate_strict_entry(
        root, record, request_path=request_path, phase_id=phase_id, request=request
    )
