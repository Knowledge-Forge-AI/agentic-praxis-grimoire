"""Real-Git regressions for tracked fixtures beneath ignored directories."""

from __future__ import annotations

import errno
import os
from pathlib import Path
import stat
import subprocess
import time

import pytest

from agent_phase.candidate import CandidateError, tree_identity


def run_git(
    root: Path, *arguments: str, check: bool = True
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )


def git_text(root: Path, *arguments: str) -> str:
    return os.fsdecode(run_git(root, *arguments).stdout).strip()


def git_bytes(root: Path, *arguments: str) -> bytes:
    return run_git(root, *arguments).stdout


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use a private Git configuration so tests do not depend on host state."""
    for name in tuple(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.fspath(tmp_path / "gitconfig"))

    root = tmp_path / "repo"
    root.mkdir()
    run_git(root, "init", "-q")
    run_git(root, "config", "user.name", "Candidate Test")
    run_git(root, "config", "user.email", "candidate@example.invalid")
    write(root, ".gitignore", b"node_modules/\n*.ignored\n")
    write(root, "ordinary.txt", b"baseline\n")
    run_git(root, "add", ".gitignore", "ordinary.txt")
    run_git(root, "commit", "-qm", "baseline")
    run_git(root, "branch", "-M", "main")
    return root


def write(root: Path, name: str, contents: bytes) -> Path:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(contents)
    return target


def literal_pathspec(name: str) -> str:
    return f":(top,literal){name}"


def track(root: Path, name: str, contents: bytes = b"tracked fixture\n") -> Path:
    target = write(root, name, contents)
    run_git(root, "add", "-f", "--", literal_pathspec(name))
    run_git(root, "commit", "-qm", "track fixture deliberately")
    return target


def capture(root: Path, cwd: Path | None = None) -> str:
    """Capture and prove Git and worktree state are unchanged."""
    git_dir = Path(git_text(root, "rev-parse", "--absolute-git-dir"))
    index = git_dir / "index"
    before_index = index.read_bytes()
    before_head = git_bytes(root, "rev-parse", "HEAD")
    before_branch = git_bytes(root, "branch", "--show-current")
    before_worktree = snapshot_worktree(root)
    try:
        identity = tree_identity(root if cwd is None else cwd)
    finally:
        assert index.read_bytes() == before_index, "real index bytes changed"
        assert git_bytes(root, "rev-parse", "HEAD") == before_head, "HEAD changed"
        assert git_bytes(root, "branch", "--show-current") == before_branch, "branch changed"
        assert snapshot_worktree(root) == before_worktree, "worktree nodes changed"
    return str(identity["tree"])


def snapshot_worktree(root: Path) -> dict[str, tuple[object, ...]]:
    """Record worktree nodes without traversing symlink targets or ``.git``."""
    snapshot: dict[str, tuple[object, ...]] = {}
    root_name = os.fspath(root)

    def visit(directory: str) -> None:
        with os.scandir(directory) as entries:
            for entry in entries:
                relative = os.path.relpath(entry.path, root_name)
                if relative == ".git" or relative.startswith(f".git{os.sep}"):
                    continue
                info = entry.stat(follow_symlinks=False)
                mode = stat.S_IMODE(info.st_mode)
                if stat.S_ISLNK(info.st_mode):
                    snapshot[relative] = (
                        "symlink",
                        mode,
                        os.fsencode(os.readlink(entry.path)),
                    )
                elif stat.S_ISDIR(info.st_mode):
                    snapshot[relative] = ("directory", mode)
                    visit(entry.path)
                elif stat.S_ISREG(info.st_mode):
                    snapshot[relative] = ("file", mode, Path(entry.path).read_bytes())
                else:
                    snapshot[relative] = ("other", mode)

    visit(root_name)
    return snapshot


def tree_names(root: Path, tree: str) -> set[str]:
    raw = git_bytes(root, "ls-tree", "-rz", "--name-only", tree)
    return {os.fsdecode(path) for path in raw.split(b"\0") if path}


def tree_contents(root: Path, tree: str, name: str) -> bytes:
    return git_bytes(root, "show", f"{tree}:{name}")


def tree_mode(root: Path, tree: str, name: str) -> str:
    raw = git_bytes(root, "ls-tree", "-z", tree, "--", name)
    entry = raw.rstrip(b"\0")
    return os.fsdecode(entry.split(b"\t", 1)[0].split(b" ", 1)[0])


def test_clean_tracked_ignored_fixture_matches_head(repository: Path) -> None:
    track(repository, "src/test/fixtures/bulk/email_export/node_modules/ignored.js")
    assert capture(repository) == git_text(repository, "rev-parse", "HEAD^{tree}")


def test_modified_tracked_ignored_fixture_is_captured(repository: Path) -> None:
    name = "fixtures/node_modules/ignored.js"
    fixture = track(repository, name)
    fixture.write_bytes(b"modified fixture\n")
    assert tree_contents(repository, capture(repository), name) == b"modified fixture\n"
    assert fixture.read_bytes() == b"modified fixture\n"


def test_deleted_tracked_ignored_fixture_is_captured(repository: Path) -> None:
    name = "fixtures/node_modules/ignored.js"
    track(repository, name).unlink()
    assert name not in tree_names(repository, capture(repository))
    assert not (repository / name).exists()


def test_untracked_ignored_sibling_is_neither_added_nor_hashed(repository: Path) -> None:
    track(repository, "fixtures/node_modules/ignored.js")
    sibling = write(
        repository,
        "fixtures/node_modules/untracked.js",
        b"untracked excluded sentinel 93814\n",
    )
    oid = git_text(repository, "hash-object", "--", os.fspath(sibling))
    assert run_git(repository, "cat-file", "-e", oid, check=False).returncode != 0
    assert "fixtures/node_modules/untracked.js" not in tree_names(repository, capture(repository))
    assert run_git(repository, "cat-file", "-e", oid, check=False).returncode != 0
    assert sibling.exists()


def test_new_product_added_while_ignored_file_excluded(repository: Path) -> None:
    write(repository, "new-product.txt", b"product\n")
    write(repository, "secret.ignored", b"not candidate\n")
    tree = capture(repository)
    assert "new-product.txt" in tree_names(repository, tree)
    assert "secret.ignored" not in tree_names(repository, tree)


def test_tracked_metadata_remains_product_untracked_metadata_excluded(
    repository: Path,
) -> None:
    name = ".serena/config.json"
    track(repository, name, b"old\n").write_bytes(b"new\n")
    metadata = write(repository, ".serena/cache/private.txt", b"private cache sentinel 27811\n")
    scratch = write(repository, ".scratch/session.txt", b"local scratch\n")
    metadata_oid = git_text(repository, "hash-object", "--", os.fspath(metadata))
    scratch_oid = git_text(repository, "hash-object", "--", os.fspath(scratch))
    tree = capture(repository)
    assert tree_contents(repository, tree, name) == b"new\n"
    names = tree_names(repository, tree)
    assert ".serena/cache/private.txt" not in names
    assert ".scratch/session.txt" not in names
    assert run_git(repository, "cat-file", "-e", metadata_oid, check=False).returncode != 0
    assert run_git(repository, "cat-file", "-e", scratch_oid, check=False).returncode != 0


@pytest.mark.parametrize("name", [
    "racy.txt", ".serena/config.json", "fixtures/node_modules/ignored.js",
])
def test_racy_same_size_edit_preserves_index_timestamp_checks(
    repository: Path, name: str,
) -> None:
    # Force coarse stat comparison so the regression cannot pass by timing luck.
    run_git(repository, "config", "core.trustctime", "false")
    run_git(repository, "config", "core.checkStat", "minimal")
    stamp = int(time.time()) - 20
    product = write(repository, name, b"old\n")
    os.utime(product, (stamp, stamp))
    run_git(repository, "add", "-f", "--", literal_pathspec(name))
    run_git(repository, "commit", "-qm", "tracked racy fixture")
    product.write_bytes(b"new\n")
    os.utime(product, (stamp, stamp))
    index = repository / ".git/index"
    os.utime(index, (stamp, stamp))
    index_mtime = index.stat().st_mtime_ns

    assert tree_contents(repository, capture(repository), name) == b"new\n"
    assert index.stat().st_mtime_ns == index_mtime


def test_staged_ignored_addition_is_retained_in_temporary_index(repository: Path) -> None:
    name = "fixtures/node_modules/staged.js"
    write(repository, name, b"stage me\n")
    run_git(repository, "add", "-f", "--", literal_pathspec(name))
    assert tree_contents(repository, capture(repository), name) == b"stage me\n"


def test_staged_ignored_modification_then_later_worktree_bytes_are_captured(
    repository: Path,
) -> None:
    name = "fixtures/node_modules/staged-modification.js"
    fixture = track(repository, name, b"original\n")
    fixture.write_bytes(b"staged bytes\n")
    run_git(repository, "add", "-f", "--", literal_pathspec(name))
    fixture.write_bytes(b"later worktree bytes\n")
    tree = capture(repository)
    assert tree_contents(repository, tree, name) == b"later worktree bytes\n"
    assert git_bytes(repository, "show", f":0:{name}") == b"staged bytes\n"
    assert fixture.read_bytes() == b"later worktree bytes\n"


def test_staged_ignored_deletion_keeps_present_worktree_file_out_of_candidate(
    repository: Path,
) -> None:
    name = "fixtures/node_modules/staged-deletion.js"
    fixture = track(repository, name, b"keep in worktree\n")
    run_git(repository, "rm", "--cached", "-q", "--", literal_pathspec(name))
    tree = capture(repository)
    assert name not in tree_names(repository, tree)
    assert fixture.read_bytes() == b"keep in worktree\n"


def test_literal_product_path_is_not_a_glob(repository: Path) -> None:
    names = ("new dir/literal[0]*?.txt", "--option.txt", "!prefix.txt")
    for name in names:
        write(repository, name, f"{name}\n".encode())
    tree = capture(repository)
    for name in names:
        assert tree_contents(repository, tree, name) == f"{name}\n".encode()


def test_nested_cwd_captures_whole_worktree(repository: Path) -> None:
    write(repository, "outside.txt", b"outside\n")
    write(repository, "nested/inside.txt", b"inside\n")
    tree = capture(repository, repository / "nested")
    names = tree_names(repository, tree)
    assert "outside.txt" in names
    assert "nested/inside.txt" in names


def create_tracked_shape(repository: Path, kind: str, tmp_path: Path) -> None:
    if kind == "file":
        track(repository, "shape", b"source file\n")
        return
    if kind == "directory":
        track(repository, "shape/child.txt", b"source child\n")
        return
    if kind == "symlink":
        target = tmp_path / "source-target"
        target.mkdir()
        (target / "private.txt").write_bytes(b"source target\n")
        (repository / "shape").symlink_to(target, target_is_directory=True)
        run_git(repository, "add", "--", literal_pathspec("shape"))
        run_git(repository, "commit", "-qm", "track source symlink")
        return
    raise AssertionError(f"unknown source shape: {kind}")


def replace_shape(repository: Path, source: str, target: str, tmp_path: Path) -> None:
    shape = repository / "shape"
    if source == "directory":
        (shape / "child.txt").unlink()
        shape.rmdir()
    else:
        shape.unlink()

    if target == "file":
        shape.write_bytes(b"target file\n")
    elif target == "directory":
        shape.mkdir()
        (shape / "child.txt").write_bytes(b"target child\n")
    elif target == "symlink":
        target_root = tmp_path / "target-root"
        target_root.mkdir()
        (target_root / "private.txt").write_bytes(b"never import me\n")
        shape.symlink_to(target_root, target_is_directory=True)
    else:
        raise AssertionError(f"unknown target shape: {target}")


@pytest.mark.parametrize(
    ("source", "target"),
    (
        ("file", "directory"),
        ("file", "symlink"),
        ("directory", "file"),
        ("directory", "symlink"),
        ("symlink", "file"),
        ("symlink", "directory"),
    ),
    ids=lambda value: value,
)
def test_all_shape_transitions_capture_target_and_preserve_worktree(
    repository: Path,
    tmp_path: Path,
    source: str,
    target: str,
) -> None:
    create_tracked_shape(repository, source, tmp_path)
    replace_shape(repository, source, target, tmp_path)
    tree = capture(repository)
    names = tree_names(repository, tree)
    if target == "file":
        assert "shape" in names
        assert "shape/child.txt" not in names
        assert tree_mode(repository, tree, "shape") == "100644"
        assert tree_contents(repository, tree, "shape") == b"target file\n"
    elif target == "directory":
        assert "shape" not in names
        assert "shape/child.txt" in names
        assert tree_mode(repository, tree, "shape/child.txt") == "100644"
        assert tree_contents(repository, tree, "shape/child.txt") == b"target child\n"
    else:
        assert "shape" in names
        assert "shape/private.txt" not in names
        assert tree_mode(repository, tree, "shape") == "120000"
        assert tree_contents(repository, tree, "shape") == os.fsencode(
            tmp_path / "target-root"
        )
        assert os.readlink(repository / "shape") == os.fspath(tmp_path / "target-root")


def test_linked_worktree_real_index_is_preserved(repository: Path, tmp_path: Path) -> None:
    track(repository, "fixtures/node_modules/ignored.js")
    linked = tmp_path / "linked"
    run_git(repository, "worktree", "add", "-q", "-b", "linked-test", os.fspath(linked))
    write(linked, "fixtures/node_modules/ignored.js", b"linked change\n")
    assert tree_contents(linked, capture(linked), "fixtures/node_modules/ignored.js") == b"linked change\n"
    assert git_text(linked, "branch", "--show-current") == "linked-test"


def test_leading_whitespace_and_newline_pathnames_are_preserved(repository: Path) -> None:
    names = (" leading\nname.txt", "newline\ninside.txt")
    for name in names:
        write(repository, name, f"{name}\n".encode())
    tree = capture(repository)
    candidate_names = tree_names(repository, tree)
    assert set(names) <= candidate_names
    for name in names:
        assert tree_contents(repository, tree, name) == f"{name}\n".encode()


def test_non_utf8_pathname_round_trips_with_filesystem_encoding(
    repository: Path,
) -> None:
    raw_name = b"nonutf8-\xff.txt"
    name = os.fsdecode(raw_name)
    try:
        write(repository, name, b"non-UTF-8 product\n")
    except OSError as error:
        if error.errno not in {errno.EILSEQ, errno.EINVAL, errno.ENOTSUP}:
            raise
        pytest.skip(f"filesystem does not support non-UTF-8 names: {error}")
    tree = capture(repository)
    assert name in tree_names(repository, tree)
    assert tree_contents(repository, tree, name) == b"non-UTF-8 product\n"


def test_staged_deletion_with_worktree_file_is_rediscovered_as_untracked(
    repository: Path,
) -> None:
    name = "staged-delete.txt"
    fixture = track(repository, name, b"original\n")
    run_git(repository, "rm", "--cached", "-q", "--", literal_pathspec(name))
    assert git_text(repository, "diff", "--cached", "--name-status") == f"D\t{name}"
    assert tree_contents(repository, capture(repository), name) == b"original\n"
    assert fixture.read_bytes() == b"original\n"


def test_executable_mode_change_is_captured_without_changing_worktree_mode(
    repository: Path,
) -> None:
    name = "fixtures/node_modules/mode.sh"
    fixture = track(repository, name, b"#!/bin/sh\nexit 0\n")
    fixture.chmod(0o755)
    tree = capture(repository)
    assert tree_mode(repository, tree, name) == "100755"
    assert fixture.stat().st_mode & 0o777 == 0o755


def test_unmerged_index_is_rejected_before_temporary_refresh(repository: Path) -> None:
    run_git(repository, "checkout", "-q", "-b", "side")
    write(repository, "conflict.txt", b"side\n")
    run_git(repository, "add", "conflict.txt")
    run_git(repository, "commit", "-qm", "side conflict")
    run_git(repository, "checkout", "-q", "main")
    write(repository, "conflict.txt", b"main\n")
    run_git(repository, "add", "conflict.txt")
    run_git(repository, "commit", "-qm", "main conflict")
    merge = run_git(repository, "merge", "side", check=False)
    assert merge.returncode != 0
    try:
        with pytest.raises(CandidateError, match="unmerged paths"):
            capture(repository)
    finally:
        run_git(repository, "merge", "--abort")
