"""Real-Git regressions for empty-root repository candidate capture.

Verifies the fix for the empty-tree root-commit candidate-capture defect where
``git add -u -- :/`` failed when the temporary index contained zero paths.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

from agent_phase.candidate import (
    CandidateError,
    git_directory,
    tree_identity,
)
from test_agent_phase_disposition_flow import (
    PHASE_ID,
    REQUEST,
    DispositionFakeRunner,
    make_dispatcher,
)


def git(cwd: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=cwd, capture_output=True, check=True
    )
    return completed.stdout.decode().strip()


@pytest.fixture
def empty_root_repo(tmp_path: Path) -> Path:
    """Create a repository whose HEAD is an empty-tree root commit."""
    root = tmp_path.resolve() / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    git(root, "commit", "--allow-empty", "-q", "-m", "empty root")
    return root


def test_empty_root_no_product_candidate_equals_head_tree(
    empty_root_repo: Path,
) -> None:
    """3.1 Empty root commit with no product produces the empty candidate tree.

    Candidate head matches HEAD, tree matches HEAD^{tree}, and worktree, index,
    and HEAD remain untouched.
    """
    head_before = git(empty_root_repo, "rev-parse", "HEAD")
    head_tree = git(empty_root_repo, "rev-parse", "HEAD^{tree}")
    index_path = git_directory(empty_root_repo) / "index"
    index_before = index_path.read_bytes() if index_path.is_file() else None

    candidate = tree_identity(empty_root_repo)

    assert candidate["kind"] == "git_tree"
    assert candidate["head"] == head_before
    assert candidate["tree"] == head_tree

    # Real worktree, index, and HEAD remain unchanged
    assert git(empty_root_repo, "rev-parse", "HEAD") == head_before
    if index_before is not None:
        assert index_path.read_bytes() == index_before
    listing = git(
        empty_root_repo, "ls-tree", "-r", "--name-only", str(candidate["tree"])
    )
    assert listing == ""


def test_empty_root_with_first_untracked_product_captured_in_candidate(
    empty_root_repo: Path,
) -> None:
    """3.2 Empty root commit with first untracked product captures candidate.

    Primary bug regression: untracked substantive product must enter the
    candidate tree even when no tracked entries exist in the initial index.
    HEAD remains the empty root and real index remains unchanged.
    """
    head_before = git(empty_root_repo, "rev-parse", "HEAD")
    index_path = git_directory(empty_root_repo) / "index"
    index_before = index_path.read_bytes() if index_path.is_file() else None

    product_file = empty_root_repo / "first_product.py"
    product_content = "def answer():\n    return 42\n"
    product_file.write_text(product_content, encoding="utf-8")

    candidate = tree_identity(empty_root_repo)

    assert candidate["kind"] == "git_tree"
    assert candidate["head"] == head_before

    # Verify candidate tree contains the exact product bytes and path
    listing = git(
        empty_root_repo, "ls-tree", "-r", "--name-only", str(candidate["tree"])
    ).splitlines()
    assert listing == ["first_product.py"]
    captured_content = git(
        empty_root_repo, "show", f"{candidate['tree']}:first_product.py"
    )
    assert captured_content == product_content.strip()

    # HEAD remains the empty root and real index is untouched
    assert git(empty_root_repo, "rev-parse", "HEAD") == head_before
    if index_before is not None:
        assert index_path.read_bytes() == index_before
    # In real index, first_product.py must remain untracked
    real_ls_files = git(
        empty_root_repo, "ls-files", "--cached", "--", "first_product.py"
    )
    assert real_ls_files == ""


def test_empty_root_real_index_absence_remains_absent(
    empty_root_repo: Path,
) -> None:
    """3.3 Real index absence remains absence after candidate capture.

    When the real index does not exist, tree_identity must seed from HEAD
    without writing a real index back to the repository.
    """
    git_dir = git_directory(empty_root_repo)
    real_index = git_dir / "index"
    if real_index.exists():
        real_index.unlink()
    assert not real_index.exists()

    product_file = empty_root_repo / "first_product.txt"
    product_file.write_text("substantive content\n", encoding="utf-8")

    candidate = tree_identity(empty_root_repo)

    # Real index must remain absent
    assert not real_index.exists(), "real index was created during capture"

    # Candidate tree still captures untracked product correctly
    listing = git(
        empty_root_repo, "ls-tree", "-r", "--name-only", str(candidate["tree"])
    ).splitlines()
    assert "first_product.txt" in listing


def test_empty_root_real_index_bytes_remain_byte_identical(
    empty_root_repo: Path,
) -> None:
    """3.4 Real index bytes remain byte-identical after candidate capture.

    Ensures that empty-root repository candidate capture never mutates
    the real index.
    """
    git_dir = git_directory(empty_root_repo)
    real_index = git_dir / "index"
    assert real_index.is_file()
    index_before = real_index.read_bytes()

    (empty_root_repo / "new_file.txt").write_text("hello\n", encoding="utf-8")
    tree_identity(empty_root_repo)

    assert real_index.read_bytes() == index_before


def test_empty_root_dispatcher_end_to_end_binds_first_product(
    tmp_path: Path,
) -> None:
    """4. Optional narrow end-to-end regression with cheap fake runner.

    Proves the first substantive product produced during a phase can reach
    candidate binding through the dispatcher in an empty-root repository.
    """
    resolved_tmp = tmp_path.resolve()
    repo = resolved_tmp / "e2e_repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    git(repo, "commit", "--allow-empty", "-q", "-m", "empty root")

    remote = resolved_tmp / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-q", "--set-upstream", "origin", "HEAD")

    def produce(cwd: Path, prompt: bytes) -> None:
        (cwd / "first_product.txt").write_text("first product content\n")

    runner = DispositionFakeRunner(hooks={2: produce})
    dispatcher = make_dispatcher(repo, resolved_tmp, runner)

    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    pre_final = state.get("pre_final_candidate")
    assert pre_final is not None
    listing = git(repo, "ls-tree", "-r", "--name-only", str(pre_final["tree"]))
    assert "first_product.txt" in listing.splitlines()


# APG166X-PILOT1: remaining empty-index shapes from the external report. Each
# case uses a host-independent Git configuration and the shared capture helper,
# which asserts real index bytes, HEAD, branch, and worktree nodes unchanged.
from test_agent_phase_candidate_tracked_ignores import (  # noqa: E402
    capture,
    git_text,
    literal_pathspec,
    run_git,
    tree_contents,
    tree_mode,
    tree_names,
    write,
)


@pytest.fixture
def isolated_empty_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.fspath(tmp_path / "gitconfig"))
    root = tmp_path / "empty"
    root.mkdir()
    run_git(root, "init", "-q")
    run_git(root, "config", "user.name", "Candidate Test")
    run_git(root, "config", "user.email", "candidate@example.invalid")
    run_git(root, "commit", "--allow-empty", "-qm", "empty root")
    assert git_text(root, "ls-files", "--cached") == ""
    return root


def _single_tracked_file(root: Path) -> None:
    write(root, "only.txt", b"only tracked\n")
    run_git(root, "add", "only.txt")
    run_git(root, "commit", "-qm", "one tracked file")


def test_staged_final_deletion_with_file_removed_yields_empty_tree(
    isolated_empty_root: Path,
) -> None:
    """HEAD is non-empty but the staged index is empty (second trigger)."""
    root = isolated_empty_root
    _single_tracked_file(root)
    run_git(root, "rm", "-q", "--", "only.txt")
    assert git_text(root, "ls-files", "--cached") == ""
    assert tree_names(root, capture(root)) == set()
    # The staged deletion remains staged in the real index.
    assert git_text(root, "diff", "--cached", "--name-status") == "D\tonly.txt"


def test_staged_final_deletion_with_file_kept_rediscovers_untracked(
    isolated_empty_root: Path,
) -> None:
    """A kept worktree file after ``rm --cached`` is untracked product.

    This matches the non-empty behaviour: the candidate reflects the worktree,
    not the staged deletion, while the real index keeps the deletion staged.
    """
    root = isolated_empty_root
    _single_tracked_file(root)
    run_git(root, "rm", "-q", "--cached", "--", "only.txt")
    assert git_text(root, "ls-files", "--cached") == ""
    tree = capture(root)
    assert tree_contents(root, tree, "only.txt") == b"only tracked\n"
    assert git_text(root, "diff", "--cached", "--name-status") == "D\tonly.txt"


def test_empty_root_staged_addition_captures_later_worktree_bytes(
    isolated_empty_root: Path,
) -> None:
    root = isolated_empty_root
    write(root, "staged.txt", b"staged\n")
    run_git(root, "add", "staged.txt")
    write(root, "staged.txt", b"staged then edited\n")
    tree = capture(root)
    assert tree_contents(root, tree, "staged.txt") == b"staged then edited\n"
    assert git_text(root, "diff", "--cached", "--name-status") == "A\tstaged.txt"


def test_empty_root_intent_to_add_is_captured_and_preserved(
    isolated_empty_root: Path,
) -> None:
    root = isolated_empty_root
    write(root, "intent.txt", b"intent body\n")
    run_git(root, "add", "-N", "--", "intent.txt")
    tree = capture(root)
    assert tree_contents(root, tree, "intent.txt") == b"intent body\n"
    # Real index still records only intent-to-add (empty blob, i-t-a flag).
    assert git_text(root, "diff", "--cached", "--name-only") == ""
    assert git_text(root, "ls-files", "--cached") == "intent.txt"


def test_empty_root_nested_invocation_captures_whole_worktree(
    isolated_empty_root: Path,
) -> None:
    root = isolated_empty_root
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    write(root, "top.txt", b"top\n")
    write(root, "a/b/deep.txt", b"deep\n")
    tree = capture(root, cwd=nested)
    assert tree_names(root, tree) == {"top.txt", "a/b/deep.txt"}


def test_empty_root_excludes_ignored_and_operational_metadata(
    isolated_empty_root: Path,
) -> None:
    root = isolated_empty_root
    write(root, ".git/info/exclude", b"*.ignored\n")
    write(root, "kept.txt", b"product\n")
    write(root, "noise.ignored", b"ignored\n")
    for metadata in (".scratch/run/log.txt", ".serena/cache.bin",
                     ".pytest_cache/v/x", ".claude/.cc-writes/w"):
        write(root, metadata, b"metadata\n")
    tree = capture(root)
    assert tree_names(root, tree) == {"kept.txt"}


def test_empty_root_force_tracked_fixture_under_ignored_directory(
    isolated_empty_root: Path,
) -> None:
    root = isolated_empty_root
    write(root, ".git/info/exclude", b"node_modules/\n")
    write(root, "node_modules/fixture.js", b"tracked fixture\n")
    write(root, "node_modules/sibling.js", b"ignored sibling\n")
    run_git(root, "add", "-f", "--", literal_pathspec("node_modules/fixture.js"))
    write(root, "node_modules/fixture.js", b"tracked fixture edited\n")
    tree = capture(root)
    assert tree_names(root, tree) == {"node_modules/fixture.js"}
    assert tree_contents(root, tree, "node_modules/fixture.js") == b"tracked fixture edited\n"


@pytest.mark.parametrize("name", ["*", ":(glob)x", " leading space", "new\nline", "[ab]"])
def test_empty_root_unusual_literal_names(isolated_empty_root: Path, name: str) -> None:
    root = isolated_empty_root
    write(root, name, b"literal\n")
    if name == "*":
        write(root, "decoy.txt", b"decoy must still be captured separately\n")
    tree = capture(root)
    assert name in tree_names(root, tree)
    assert tree_contents(root, tree, name) == b"literal\n"


def test_empty_root_executable_untracked_product_mode(isolated_empty_root: Path) -> None:
    root = isolated_empty_root
    script = write(root, "run.sh", b"#!/bin/sh\nexit 0\n")
    script.chmod(0o755)
    tree = capture(root)
    assert tree_mode(root, tree, "run.sh") == "100755"


def test_unborn_head_remains_a_bounded_candidate_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Characterization: a repository with no commit is outside this fix.

    A valid empty-tree HEAD is supported; an unborn HEAD fails closed with a
    bounded CandidateError rather than fabricating a base.
    """
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.fspath(tmp_path / "gitconfig"))
    root = tmp_path / "unborn"
    root.mkdir()
    run_git(root, "init", "-q")
    write(root, "product.txt", b"product\n")
    with pytest.raises(CandidateError, match="rev-parse HEAD"):
        tree_identity(root)
    assert not (root / ".git" / "index").exists()
