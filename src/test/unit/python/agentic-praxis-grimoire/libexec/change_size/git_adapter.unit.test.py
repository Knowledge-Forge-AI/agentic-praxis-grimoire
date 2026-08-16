"""Fixed-argument Git adapter parsing and refusal contracts."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from change_size import git_adapter  # noqa: E402


def completed(stdout: bytes, returncode: int = 0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, b"failure")


def test_discover_environment_and_invoke_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: completed(str(tmp_path).encode() + b"\n"),
    )
    repository = git_adapter.GitRepository.discover(tmp_path)
    assert repository.root == tmp_path
    assert git_adapter.GitRepository._environment()["GIT_NO_REPLACE_OBJECTS"] == "1"
    monkeypatch.setattr(
        subprocess, "run", lambda *_args, **_kwargs: completed(b"", returncode=1)
    )
    with pytest.raises(git_adapter.GitError, match="inspection"):
        git_adapter.GitRepository._invoke(tmp_path, ["status"])


def test_commit_parent_path_and_tree_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = git_adapter.GitRepository(tmp_path)
    oid = "a" * 40
    monkeypatch.setattr(repository, "run", lambda *_args, **_kwargs: (oid + "\n").encode())
    assert repository.resolve_commit("HEAD") == oid
    monkeypatch.setattr(repository, "run", lambda *_args, **_kwargs: b"bad\n")
    with pytest.raises(git_adapter.GitError, match="identity"):
        repository.resolve_commit("HEAD")
    monkeypatch.setattr(repository, "run", lambda *_args, **_kwargs: f"{oid}\n".encode())
    assert repository.parent(oid) is None
    parent = "b" * 40
    monkeypatch.setattr(
        repository, "run", lambda *_args, **_kwargs: f"{oid} {parent}\n".encode()
    )
    assert repository.parent(oid) == parent
    assert repository._path(b"safe path") == "safe path"
    with pytest.raises(git_adapter.GitError, match="unsafe"):
        repository._path(b"/absolute")
    with pytest.raises(git_adapter.GitError, match="unsafe"):
        repository._path(b"ordinary\nviolations: NONE")
    tree = (
        f"100644 blob {oid} 3\tfile.txt".encode()
        + b"\0"
        + f"040000 tree {parent} 0\tdirectory".encode()
        + b"\0"
    )
    monkeypatch.setattr(repository, "run", lambda *_args, **_kwargs: tree)
    assert repository.tree_entries(oid)["file.txt"].size == 3


def test_sizes_index_blob_cache_and_object_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = git_adapter.GitRepository(tmp_path)
    first, second = "a" * 40, "b" * 40
    assert repository._sizes([]) == {}
    monkeypatch.setattr(
        repository,
        "run",
        lambda arguments, **_kwargs: (
            f"{first} blob 2\n{second} blob 3\n".encode()
            if arguments[0] == "cat-file" and "--batch-check" in arguments[1]
            else (
                f"100644 {first} 0\tone\0"
                f"100755 {second} 0\ttwo\0"
                f"160000 {first} 0\tvendor/sub\0"
            ).encode()
        ),
    )
    entries = repository.index_entries()
    assert entries["one"].size == 2 and entries["two"].mode == "100755"
    assert "vendor/sub" not in entries
    calls = 0

    def blob_run(arguments: list[str], **_kwargs: object) -> bytes:
        nonlocal calls
        calls += 1
        return b"blob"

    monkeypatch.setattr(repository, "run", blob_run)
    assert repository.blob(first) == repository.blob(first) == b"blob"
    assert calls == 1
    assert repository.object_file("HEAD", "file") == b"blob"


def test_malformed_tree_sizes_and_unmerged_index_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = git_adapter.GitRepository(tmp_path)
    monkeypatch.setattr(repository, "run", lambda *_args, **_kwargs: b"malformed\0")
    with pytest.raises(git_adapter.GitError, match="tree entry"):
        repository.tree_entries("HEAD")
    oid = "a" * 40
    monkeypatch.setattr(
        repository, "run", lambda *_args, **_kwargs: f"{oid} blob 1\n".encode()
    )
    with pytest.raises(git_adapter.GitError, match="incomplete"):
        repository._sizes([oid, "b" * 40])
    monkeypatch.setattr(
        repository, "run", lambda *_args, **_kwargs: f"100644 {oid} 1\tfile\0".encode()
    )
    with pytest.raises(git_adapter.GitError, match="unmerged"):
        repository.index_entries()
