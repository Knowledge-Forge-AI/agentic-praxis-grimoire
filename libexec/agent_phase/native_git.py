"""Explicit native Git transition custody and reconciliation.

Independent verification of authorized native tool commits:
provider prose or structured claims alone never grant authority.
"""

from __future__ import annotations

from copy import deepcopy
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from . import gitstate, path_disposition


SCHEMA = "agent-phase-native-git-authority-v1"
MAX_PATHS = 1024
REQUIRED_FIELDS = frozenset({
    "schema",
    "phase_id",
    "request_sha256",
    "repository",
    "branch",
    "entry_head",
    "entry_tree",
    "entry_index",
    "authorized_stage",
    "authorized_paths",
    "max_commits",
    "publication_state",
    "reason",
    "plan_digest",
    "result_digest",
    "timestamp",
    "provider_invocations",
    "sha256",
})
OPTIONAL_FIELDS = frozenset({"commit_tree"})
FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS


class NativeGitError(ValueError):
    """Refusal on invalid native Git authority or transition."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class NativeGitAuthorityError(NativeGitError):
    """Specific refusal on invalid native Git authority receipt."""



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
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID",
            f"authority requires 1..{MAX_PATHS} explicitly selected paths",
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
            raise NativeGitError(
                "NATIVE_GIT_PATH_INVALID",
                f"authorized path is a symlink to a directory: {path}",
            )
        if target.is_dir() and not target.is_symlink():
            raise NativeGitError(
                "NATIVE_GIT_PATH_INVALID",
                f"authorized path is occupied by a directory: {path}",
            )
        for parent in target.parents:
            if parent == root:
                break
            if parent.is_symlink():
                raise NativeGitError(
                    "NATIVE_GIT_PATH_INVALID",
                    f"authorized path traverses a symlink alias: {path}",
                )


def create_authority(
    request_path: Path,
    root: Path,
    stage: str,
    paths: list[str],
    *,
    max_commits: int = 1,
    reason: str,
    plan_digest: str | None = None,
    result_digest: str | None = None,
    commit_tree: str | None = None,
    phase_id: str | None = None,
) -> dict[str, Any]:
    """Create a provider-free native Git authority receipt."""
    if not reason or not reason.strip():
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", "operator reason is required"
        )
    if max_commits < 1 or max_commits > 100:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", "max_commits must be between 1 and 100"
        )
    if not stage or not stage.strip():
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", "authorized stage is required"
        )
    from . import lifecycle as lifecycle_module
    valid_stages = {s.name for spec in lifecycle_module.LIFECYCLES.values() for s in spec.stages}
    if stage not in valid_stages:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID",
            f"unknown stage {stage!r}; expected one of {sorted(valid_stages)}",
        )

    root = gitstate.repository_root(root).resolve()
    gitstate.require_no_active_git_operations(root)
    clean_paths = canonical_paths(paths)
    require_safe_paths(root, clean_paths)

    from . import run as run_module
    from .request import load_request

    req_data = load_request(request_path)
    from . import adoption as adoption_module
    req_sha = adoption_module.digest(req_data.as_dict())
    actual_phase_id = phase_id or run_module.phase_id_from_request(request_path)

    head = gitstate.current_head(root)
    branch = gitstate.current_branch(root)
    head_tree = gitstate._text(root, ["rev-parse", "HEAD^{tree}"], "TREE_FAILED")
    idx_id = gitstate.index_identity(root)

    record: dict[str, Any] = {
        "schema": SCHEMA,
        "phase_id": actual_phase_id,
        "request_sha256": req_sha,
        "repository": repository_identity(root),
        "branch": branch,
        "entry_head": head,
        "entry_tree": head_tree,
        "entry_index": idx_id,
        "authorized_stage": stage,
        "authorized_paths": clean_paths,
        "max_commits": max_commits,
        "publication_state": "pending",
        "reason": reason.strip(),
        "plan_digest": plan_digest,
        "result_digest": result_digest,
        "commit_tree": commit_tree,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "provider_invocations": 0,
    }
    record["sha256"] = digest(record)
    return record


def validate_authority(
    root: Path,
    record: dict[str, Any],
    request_path: Path | None = None,
    phase_id: str | None = None,
    request: Any = None,
) -> dict[str, Any]:
    """Validate a native Git authority receipt against repository entry state."""
    if not isinstance(record, dict) or not REQUIRED_FIELDS.issubset(set(record)) or not set(record).issubset(FIELDS):
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", "invalid authority receipt fields"
        )
    if record.get("schema") != SCHEMA:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", f"unsupported schema: {record.get('schema')}"
        )

    expected = deepcopy(record)
    record_hash = expected.pop("sha256", None)
    if digest(expected) != record_hash:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", "authority receipt checksum differs"
        )

    if record.get("publication_state") != "pending":
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", "publication state must be pending"
        )

    repo_id = repository_identity(root)
    if (
        record["repository"]["device"] != repo_id["device"]
        or record["repository"]["inode"] != repo_id["inode"]
    ):
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", "repository identity differs from authority"
        )

    if phase_id is not None and record["phase_id"] != phase_id:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID", "authority is bound to a different phase"
        )

    if request is not None:
        from . import adoption as adoption_module
        expected_sha = adoption_module.digest(request.as_dict())
        if record["request_sha256"] != expected_sha:
            raise NativeGitError(
                "NATIVE_GIT_AUTHORITY_INVALID",
                "authority is bound to a different substantive request",
            )
    elif request_path is not None:
        raw_sha = hashlib.sha256(request_path.read_bytes()).hexdigest()
        from .request import load_request
        from . import adoption as adoption_module
        try:
            req_data = load_request(request_path)
            dict_sha = adoption_module.digest(req_data.as_dict())
        except Exception:
            dict_sha = None
        if record["request_sha256"] not in (raw_sha, dict_sha):
            raise NativeGitError(
                "NATIVE_GIT_AUTHORITY_INVALID",
                "authority is bound to a different substantive request",
            )

    curr_branch = gitstate.current_branch(root)
    if curr_branch != record["branch"]:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID",
            f"repository branch {curr_branch!r} differs from authorized {record['branch']!r}",
        )

    curr_head = gitstate.current_head(root)
    if curr_head != record["entry_head"]:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID",
            f"entry HEAD {curr_head} differs from authorized {record['entry_head']}",
        )

    curr_tree = gitstate._text(root, ["rev-parse", "HEAD^{tree}"], "TREE_FAILED")
    if curr_tree != record["entry_tree"]:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID",
            f"entry tree {curr_tree} differs from authorized {record['entry_tree']}",
        )

    curr_index = gitstate.index_identity(root)
    if curr_index != record["entry_index"]:
        raise NativeGitError(
            "NATIVE_GIT_AUTHORITY_INVALID",
            "entry index differs from authorized index",
        )

    clean_paths = canonical_paths(record["authorized_paths"])
    require_safe_paths(root, clean_paths)
    return record


def reconcile_native_transition(
    root: Path,
    state: dict[str, Any],
    stage_name: str,
    authority: dict[str, Any],
    exit_head: str,
    *,
    reported_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Independently verify an authorized native commit transition against 12 invariants."""
    auth_stage = authority.get("authorized_stage")
    if auth_stage != stage_name:
        raise NativeGitError(
            "NATIVE_COMMIT_STAGE_MISMATCH",
            f"authority authorized for stage {auth_stage!r}, not {stage_name!r}",
        )

    entry_head = authority["entry_head"]
    authorized_paths = set(authority["authorized_paths"])
    max_commits = authority["max_commits"]

    # Invariant 1: branch unchanged
    curr_branch = gitstate.current_branch(root)
    if curr_branch != authority["branch"]:
        raise NativeGitError(
            "GIT_AUTHORITY_BRANCH_MISMATCH",
            f"branch changed from {authority['branch']!r} to {curr_branch!r}",
        )

    # Invariant 2: no active Git operation
    active_ops = gitstate.active_git_operations(root)
    if active_ops:
        raise NativeGitError(
            "ENTRY_ACTIVE_GIT_OPERATION",
            f"active git operations present: {', '.join(active_ops)}",
        )

    # Invariant 3: exit HEAD descends from authorized accounted HEAD
    anc_check = subprocess.run(
        ["git", "merge-base", "--is-ancestor", entry_head, exit_head],
        cwd=root,
        capture_output=True,
    )
    if anc_check.returncode != 0:
        raise NativeGitError(
            "NATIVE_COMMIT_ANCESTRY_INVALID",
            f"exit HEAD {exit_head} does not descend from entry HEAD {entry_head}",
        )

    # Invariant 4: commit count within authority
    count_res = subprocess.run(
        ["git", "rev-list", "--count", f"{entry_head}..{exit_head}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if count_res.returncode != 0:
        raise NativeGitError(
            "NATIVE_COMMIT_HISTORY_INVALID", "failed to count native commits"
        )
    commit_count = int(count_res.stdout.strip())
    if commit_count < 1:
        raise NativeGitError(
            "NATIVE_COMMIT_MISSING", "HEAD did not advance"
        )
    if commit_count > max_commits:
        raise NativeGitError(
            "NATIVE_COMMIT_COUNT_EXCEEDED",
            f"commit count {commit_count} exceeds authorized maximum {max_commits}",
        )

    # Invariant 5: exact parent/chain accounted
    rev_res = subprocess.run(
        ["git", "rev-list", "--topo-order", "--reverse", f"{entry_head}..{exit_head}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    commits = [c.strip() for c in rev_res.stdout.splitlines() if c.strip()]
    if len(commits) != commit_count:
        raise NativeGitError(
            "NATIVE_COMMIT_HISTORY_INVALID", "commit chain length mismatch"
        )

    # Check linear single-parent chain
    prev = entry_head
    for c in commits:
        parents_res = subprocess.run(
            ["git", "rev-parse", f"{c}^@"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        parents = [p.strip() for p in parents_res.stdout.splitlines() if p.strip()]
        if len(parents) != 1 or parents[0] != prev:
            raise NativeGitError(
                "NATIVE_COMMIT_PARENT_MISMATCH",
                f"commit {c} parent {parents} does not match expected {prev}",
            )
        prev = c

    # Invariant 6: reported native result matches exit HEAD when available
    if reported_result is not None:
        git_disp = reported_result.get("git_disposition") or {}
        reported_commit = git_disp.get("commit") or reported_result.get("commit")
        if reported_commit is not None and reported_commit != exit_head:
            raise NativeGitError(
                "NATIVE_COMMIT_REPORT_MISMATCH",
                f"reported commit {reported_commit} does not match exit HEAD {exit_head}",
            )
        reported_parent = git_disp.get("parent")
        if reported_parent is not None and reported_parent != entry_head:
            raise NativeGitError(
                "NATIVE_COMMIT_PARENT_MISMATCH",
                f"reported parent {reported_parent} does not match entry HEAD {entry_head}",
            )

    # Invariant 7: changed paths stay within explicit authority and normal ownership scope
    diff_res = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", entry_head, exit_head],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    changed_paths = [p.strip() for p in diff_res.stdout.splitlines() if p.strip()]
    # Check unowned entry dirt: entry dirt not in authorized_paths or adoption
    dirty_raw = state.get("entry", {}).get("dirty", [])
    entry_dirt = set(dirty_raw.keys()) if isinstance(dirty_raw, dict) else set(dirty_raw)
    unowned_dirt = (entry_dirt & set(changed_paths)) - authorized_paths
    if unowned_dirt:
        raise NativeGitError(
            "ENTRY_DIRT_NOT_PRESERVED",
            f"native commit modified unowned entry dirt: {sorted(unowned_dirt)}",
        )

    unauthorized = set(changed_paths) - authorized_paths
    if unauthorized:
        raise NativeGitError(
            "NATIVE_COMMIT_UNAUTHORIZED_PATH",
            f"native commit touched unauthorized path(s): {sorted(unauthorized)}",
        )

    # Invariant 8: no unrelated staged entries
    cached_diff = subprocess.run(
        ["git", "diff-index", "--cached", "--name-only", exit_head, "--"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    staged_residue = [p.strip() for p in cached_diff.stdout.splitlines() if p.strip()]
    if staged_residue:
        raise NativeGitError(
            "NATIVE_COMMIT_STAGED_RESIDUE",
            f"unrelated staged entries after native commit: {sorted(staged_residue)}",
        )

    # Invariant 9: index/worktree are clean after native transaction for authorized paths
    status_res = subprocess.run(
        ["git", "status", "--porcelain", "--", *sorted(authorized_paths)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    dirty_authorized = [line.strip() for line in status_res.stdout.splitlines() if line.strip()]
    if dirty_authorized:
        raise NativeGitError(
            "NATIVE_COMMIT_WORKTREE_DIRTY",
            f"authorized paths dirty in worktree after native commit: {dirty_authorized}",
        )

    # Invariant 10: remote publication did not occur when dispatcher owns publication
    upstream_res = subprocess.run(
        ["git", "rev-parse", "--verify", "@{u}"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if upstream_res.returncode == 0:
        upstream_head = upstream_res.stdout.strip()
        # Upstream must not already contain exit_head if dispatcher owns publication
        is_published = subprocess.run(
            ["git", "merge-base", "--is-ancestor", exit_head, upstream_head],
            cwd=root,
            capture_output=True,
        )
        if is_published.returncode == 0:
            raise NativeGitError(
                "NATIVE_COMMIT_REMOTE_ADVANCED",
                f"remote tracking branch already advanced to include {exit_head}",
            )

    # Invariant 11: commit tree matches bound reviewed/native transaction identity if bound
    exit_commit_tree = gitstate._text(
        root, ["rev-parse", f"{exit_head}^{{tree}}"], "TREE_FAILED"
    )
    if authority.get("commit_tree") and authority["commit_tree"] != exit_commit_tree:
        raise NativeGitError(
            "NATIVE_COMMIT_TREE_MISMATCH",
            f"commit tree {exit_commit_tree} does not match authorized commit tree {authority['commit_tree']}",
        )
    if reported_result is not None:
        rep_tree = (
            reported_result.get("git_disposition", {}).get("tree")
            or reported_result.get("commit_tree")
        )
        if rep_tree is not None and rep_tree != exit_commit_tree:
            raise NativeGitError(
                "NATIVE_COMMIT_TREE_MISMATCH",
                f"reported commit tree {rep_tree} does not match exit commit tree {exit_commit_tree}",
            )
        if authority.get("plan_digest"):
            rep_plan = reported_result.get("plan_digest")
            if rep_plan and rep_plan != authority["plan_digest"]:
                raise NativeGitError(
                    "NATIVE_COMMIT_PLAN_MISMATCH",
                    f"reported plan digest {rep_plan} does not match authorized plan digest {authority['plan_digest']}",
                )
        if authority.get("result_digest"):
            rep_res = reported_result.get("result_digest")
            if rep_res and rep_res != authority["result_digest"]:
                raise NativeGitError(
                    "NATIVE_COMMIT_RESULT_MISMATCH",
                    f"reported result digest {rep_res} does not match authorized result digest {authority['result_digest']}",
                )

    # Invariant 12: symlink/path-prefix/alias safety remains fail closed
    require_safe_paths(root, changed_paths)

    transition_record = {
        "status": "accepted",
        "stage": stage_name,
        "commit": exit_head,
        "parent": entry_head,
        "commit_chain": commits,
        "commit_tree": exit_commit_tree,
        "changed_paths": sorted(changed_paths),
        "publication_state": "pending",
        "authority_sha256": authority["sha256"],
    }
    return transition_record
