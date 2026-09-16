from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import pytest

from agent_phase import gitstate
from agent_phase.candidate import (
    CandidateError,
    plan_identity,
    require_worktree,
    tree_delta,
    tree_identity,
)


def git(cwd: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=cwd, capture_output=True, check=True
    )
    return completed.stdout.decode().strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "tracked.txt").write_text("one\n")
    git(root, "add", "tracked.txt")
    git(root, "commit", "-q", "-m", "initial")
    return root


def test_plan_identity_binds_exact_bytes() -> None:
    identity = plan_identity(b"plan bytes")
    assert identity["kind"] == "plan_bytes"
    assert identity["bytes"] == 10
    assert identity["sha256"] == hashlib.sha256(b"plan bytes").hexdigest()
    assert plan_identity(b"plan byteS") != identity


def test_require_worktree_fails_closed_outside_a_repository(tmp_path: Path) -> None:
    outside = tmp_path / "plain"
    outside.mkdir()
    with pytest.raises(CandidateError, match="not inside a git worktree"):
        require_worktree(outside)


def test_tree_identity_records_head_and_tree(repository: Path) -> None:
    identity = tree_identity(repository)
    assert identity["kind"] == "git_tree"
    assert identity["head"] == git(repository, "rev-parse", "HEAD")
    assert len(str(identity["tree"])) == 40


def test_real_index_is_never_written(repository: Path) -> None:
    index = repository / ".git/index"
    before = index.read_bytes()
    (repository / "untracked.txt").write_text("new\n")
    (repository / "tracked.txt").write_text("changed\n")
    tree_identity(repository)
    assert index.read_bytes() == before


def test_untracked_files_are_included_in_the_candidate(repository: Path) -> None:
    baseline = tree_identity(repository)
    (repository / "untracked.txt").write_text("new\n")
    candidate = tree_identity(repository)
    assert candidate["tree"] != baseline["tree"]
    listing = git(repository, "ls-tree", "-r", "--name-only", str(candidate["tree"]))
    assert "untracked.txt" in listing.splitlines()


def test_ignored_files_are_excluded_from_the_candidate(repository: Path) -> None:
    (repository / ".gitignore").write_text("secret.txt\n")
    (repository / "secret.txt").write_text("do not bind me\n")
    candidate = tree_identity(repository)
    listing = git(repository, "ls-tree", "-r", "--name-only", str(candidate["tree"]))
    assert "secret.txt" not in listing.splitlines()


def test_worktree_modifications_change_the_candidate(repository: Path) -> None:
    baseline = tree_identity(repository)
    (repository / "tracked.txt").write_text("mutated\n")
    assert tree_identity(repository)["tree"] != baseline["tree"]


def test_staged_intent_is_preserved_by_seeding_from_the_real_index(
    repository: Path,
) -> None:
    (repository / "staged.txt").write_text("staged\n")
    git(repository, "add", "staged.txt")
    candidate = tree_identity(repository)
    listing = git(repository, "ls-tree", "-r", "--name-only", str(candidate["tree"]))
    assert "staged.txt" in listing.splitlines()


def test_binding_from_a_subdirectory_covers_the_whole_worktree(
    repository: Path,
) -> None:
    nested = repository / "nested"
    nested.mkdir()
    (nested / "inner.txt").write_text("inner\n")
    (repository / "outer.txt").write_text("outer\n")
    candidate = tree_identity(nested)
    listing = git(
        repository, "ls-tree", "-r", "--name-only", str(candidate["tree"])
    ).splitlines()
    assert "outer.txt" in listing
    assert "nested/inner.txt" in listing


def test_tree_delta_reports_paths_changed_after_binding(repository: Path) -> None:
    before = tree_identity(repository)
    assert tree_delta(repository, str(before["tree"]), str(before["tree"])) == []
    (repository / "tracked.txt").write_text("closeout correction\n")
    after = tree_identity(repository)
    assert tree_delta(repository, str(before["tree"]), str(after["tree"])) == [
        "tracked.txt"
    ]


def test_commit_excludes_a_concurrent_real_index_addition(
    repository: Path,
) -> None:
    (repository / "phase.txt").write_text("phase\n")
    (repository / "operator.txt").write_text("operator\n")
    git(repository, "add", "operator.txt")

    head = gitstate.commit(repository, ["phase.txt"], "Commit phase only\n")

    committed = git(
        repository,
        "diff-tree",
        "-r",
        "--no-commit-id",
        "--name-only",
        f"{head}^",
        head,
    ).splitlines()
    assert committed == ["phase.txt"]
    assert git(repository, "diff", "--cached", "--name-only") == "operator.txt"


def test_commit_rejects_an_empty_phase_path_scope(repository: Path) -> None:
    (repository / "operator.txt").write_text("operator work\n")

    with pytest.raises(gitstate.GitStateError) as caught:
        gitstate.commit(repository, [], "Must not commit\n")

    assert caught.value.code == "GIT_COMMIT_EMPTY_SCOPE"
    assert git(repository, "status", "--short") == "?? operator.txt"
