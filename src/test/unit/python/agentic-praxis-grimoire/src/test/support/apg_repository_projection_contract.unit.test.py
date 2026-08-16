"""Projection stable-identity, target coherence, and platform controls."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

import apg_repository_path_contract as path_contract  # noqa: E402
import apg_repository_projection_contract as projection_contract  # noqa: E402
from apg_repository_path_contract import (  # noqa: E402
    RepositoryPathContract,
    RepositoryPathError,
)


PROJECTION = ".agents/skills/example"
LINK_TEXT = "../../skills/example"
TARGET = "skills/example/SKILL.md"


def _write(path: Path, content: bytes = b"owned\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _externalize(root: Path, outside: Path, relative: str) -> None:
    directory = root / relative
    directory.rename(outside)
    directory.symlink_to(outside, target_is_directory=True)


def _projection_tree(root: Path) -> None:
    _write(root / TARGET, b"---\nname: example\n---\n")
    projection = root / PROJECTION
    projection.parent.mkdir(parents=True)
    projection.symlink_to(LINK_TEXT)


def _assert_projection(repository: RepositoryPathContract) -> None:
    repository.assert_projection(PROJECTION, LINK_TEXT, TARGET)


def test_expected_relative_projection_and_direct_target(tmp_path: Path) -> None:
    _projection_tree(tmp_path)
    with RepositoryPathContract(tmp_path) as repository:
        _assert_projection(repository)


@pytest.mark.parametrize(
    "shape",
    ("wrong", "dangling", "absolute", "escape", "projection-parent", "target-parent"),
)
def test_invalid_projection_or_target_fails(tmp_path: Path, shape: str) -> None:
    root = tmp_path / "repository"
    _projection_tree(root)
    projection = root / PROJECTION
    if shape in {"wrong", "dangling", "absolute", "escape"}:
        projection.unlink()
        targets = {
            "wrong": "../../skills/other",
            "dangling": "../../skills/missing",
            "absolute": "/tmp/example",
            "escape": "../../../../outside",
        }
        projection.symlink_to(targets[shape])
    elif shape == "projection-parent":
        _externalize(root, tmp_path / "external-projections", ".agents/skills")
    else:
        _externalize(root, tmp_path / "external-skills", "skills")

    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError):
            _assert_projection(repository)


def test_projection_swap_during_readlink_fails(monkeypatch, tmp_path: Path) -> None:
    _projection_tree(tmp_path)
    projection = tmp_path / PROJECTION
    original = path_contract._read_link

    def swap_link(name, *, dir_fd=None):
        text = original(name, dir_fd=dir_fd)
        projection.unlink()
        projection.symlink_to("../../skills/other")
        return text

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(path_contract, "_read_link", swap_link)
        with pytest.raises(RepositoryPathError, match="changed|projection"):
            _assert_projection(repository)


def test_projection_target_swap_after_link_validation_fails(
    monkeypatch, tmp_path: Path
) -> None:
    _projection_tree(tmp_path)
    target = tmp_path / TARGET
    outside = tmp_path / "outside.md"
    _write(outside, b"external")
    original = path_contract._read_link

    def swap_target(name, *, dir_fd=None):
        text = original(name, dir_fd=dir_fd)
        target.unlink()
        target.symlink_to(outside)
        return text

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(path_contract, "_read_link", swap_target)
        with pytest.raises(RepositoryPathError, match="regular|symlink|open"):
            _assert_projection(repository)


def test_projection_swap_after_link_validation_before_target_open_fails(
    monkeypatch, tmp_path: Path
) -> None:
    _projection_tree(tmp_path)
    projection = tmp_path / PROJECTION
    original = path_contract._open_component
    swapped = False

    def swap_before_target(name, flags, *, dir_fd=None):
        nonlocal swapped
        if name == "SKILL.md" and not swapped:
            swapped = True
            projection.unlink()
            projection.symlink_to("../../skills/other")
        return original(name, flags, dir_fd=dir_fd)

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(path_contract, "_open_component", swap_before_target)
        with pytest.raises(RepositoryPathError, match="projection|changed"):
            _assert_projection(repository)


def test_target_replaced_during_final_projection_read_fails(
    monkeypatch, tmp_path: Path
) -> None:
    _projection_tree(tmp_path)
    target = tmp_path / TARGET
    replacement = tmp_path / "replacement.md"
    replacement.write_bytes(b"x" * target.stat().st_size)
    original = path_contract._read_link
    reads = 0

    def replace_target_on_final_link(name, *, dir_fd=None):
        nonlocal reads
        link_text = original(name, dir_fd=dir_fd)
        reads += 1
        if reads == 2:
            target.unlink()
            target.symlink_to(replacement)
        return link_text

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(
            path_contract, "_read_link", replace_target_on_final_link
        )
        with pytest.raises(RepositoryPathError, match="target changed"):
            _assert_projection(repository)


@pytest.mark.parametrize("replacement", ("same-size-file", "symlink"))
def test_open_projection_target_replaced_before_final_entry_check_fails(
    monkeypatch, tmp_path: Path, replacement: str
) -> None:
    _projection_tree(tmp_path)
    target = tmp_path / TARGET
    replacement_file = tmp_path / "replacement.md"
    replacement_file.write_bytes(b"x" * target.stat().st_size)
    original = path_contract._read_chunk
    swapped = False

    def replace_target(descriptor, size):
        nonlocal swapped
        chunk = original(descriptor, size)
        if chunk and not swapped:
            swapped = True
            target.unlink()
            if replacement == "symlink":
                target.symlink_to(replacement_file)
            else:
                target.write_bytes(replacement_file.read_bytes())
        return chunk

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(path_contract, "_read_chunk", replace_target)
        with pytest.raises(RepositoryPathError, match="target|changed|direct"):
            _assert_projection(repository)


@pytest.mark.parametrize("replacement", ("same-size-file", "symlink"))
def test_projection_target_replaced_after_open_object_validation_fails(
    monkeypatch, tmp_path: Path, replacement: str
) -> None:
    _projection_tree(tmp_path)
    target = tmp_path / TARGET
    replacement_file = tmp_path / "replacement.md"
    replacement_file.write_bytes(b"x" * target.stat().st_size)
    original = path_contract._fstat
    regular_stats = 0

    def replace_after_stable_fstat(descriptor):
        nonlocal regular_stats
        value = original(descriptor)
        if stat.S_ISREG(value.st_mode):
            regular_stats += 1
            if regular_stats == 2:
                target.unlink()
                if replacement == "symlink":
                    target.symlink_to(replacement_file)
                else:
                    target.write_bytes(replacement_file.read_bytes())
        return value

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(path_contract, "_fstat", replace_after_stable_fstat)
        with pytest.raises(RepositoryPathError, match="target entry changed"):
            _assert_projection(repository)


def test_projection_composite_descriptors_close_after_interruption(
    monkeypatch, tmp_path: Path
) -> None:
    _projection_tree(tmp_path)
    opened: list[int] = []
    original_open = path_contract._open_component

    def track_open(*args, **kwargs):
        descriptor = original_open(*args, **kwargs)
        opened.append(descriptor)
        return descriptor

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    with RepositoryPathContract(tmp_path) as repository:
        root_descriptor = repository._root_descriptor
        monkeypatch.setattr(path_contract, "_open_component", track_open)
        monkeypatch.setattr(path_contract, "_read_chunk", interrupt)
        with pytest.raises(KeyboardInterrupt):
            _assert_projection(repository)
        assert root_descriptor is not None
        os.fstat(root_descriptor)

    for descriptor in opened:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def _reuse_identity(monkeypatch, projection: Path) -> None:
    """Force every later leaf ``lstat`` to replay the original identity."""

    recorded = os.lstat(projection)
    original = path_contract._stat_component

    def reused(name, *, dir_fd=None, follow_symlinks=True):
        value = original(name, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if name == projection.name and stat.S_ISLNK(value.st_mode):
            return recorded
        return value

    monkeypatch.setattr(path_contract, "_stat_component", reused)


def test_unlink_and_recreate_with_reused_stat_identity_fails(
    monkeypatch, tmp_path: Path
) -> None:
    """Reproduce the ABA the APG60G stat tuple could not distinguish."""

    _projection_tree(tmp_path)
    projection = tmp_path / PROJECTION
    _reuse_identity(monkeypatch, projection)
    original = path_contract._read_chunk
    swapped = False

    def recreate(descriptor, size):
        nonlocal swapped
        chunk = original(descriptor, size)
        if chunk and not swapped:
            swapped = True
            projection.unlink()
            projection.symlink_to(LINK_TEXT)
        return chunk

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(path_contract, "_read_chunk", recreate)
        with pytest.raises(RepositoryPathError, match="projection leaf identity"):
            _assert_projection(repository)


def _drifted(value: os.stat_result, *, ino: int = 0, nlink: int = 0) -> os.stat_result:
    return os.stat_result(
        (
            value.st_mode,
            value.st_ino + ino,
            value.st_dev,
            value.st_nlink + nlink,
            value.st_uid,
            value.st_gid,
            value.st_size,
            0,
            0,
            0,
        )
    )


def _drift_link_handle(monkeypatch, *, occurrence: int, **drift: int) -> None:
    original = path_contract._fstat
    link_stats = 0

    def drifted(descriptor):
        nonlocal link_stats
        value = original(descriptor)
        if stat.S_ISLNK(value.st_mode):
            link_stats += 1
            if link_stats == occurrence:
                return _drifted(value, **drift)
        return value

    monkeypatch.setattr(path_contract, "_fstat", drifted)


def test_projection_handle_identity_drift_fails(monkeypatch, tmp_path: Path) -> None:
    """A changed stable handle fails even when every lstat tuple agrees."""

    _projection_tree(tmp_path)
    _reuse_identity(monkeypatch, tmp_path / PROJECTION)
    _drift_link_handle(monkeypatch, occurrence=2, ino=1)
    with RepositoryPathContract(tmp_path) as repository:
        with pytest.raises(RepositoryPathError, match="projection leaf identity"):
            _assert_projection(repository)


def test_already_detached_projection_handle_fails(
    monkeypatch, tmp_path: Path
) -> None:
    _projection_tree(tmp_path)
    _drift_link_handle(monkeypatch, occurrence=1, nlink=-1)
    with RepositoryPathContract(tmp_path) as repository:
        with pytest.raises(RepositoryPathError, match="already detached"):
            _assert_projection(repository)


def test_platform_symlink_handle_capability_is_declared() -> None:
    if sys.platform.startswith("linux"):
        assert projection_contract.SYMLINK_HANDLE_MECHANISM == "o-path-nofollow"
    elif sys.platform == "darwin":
        assert projection_contract.SYMLINK_HANDLE_MECHANISM == "o-symlink"
    assert (projection_contract.SYMLINK_HANDLE_FLAGS is None) == (
        projection_contract.SYMLINK_HANDLE_MECHANISM == "unsupported"
    )


def test_missing_platform_capability_fails_closed(
    monkeypatch, tmp_path: Path
) -> None:
    _projection_tree(tmp_path)
    monkeypatch.setattr(projection_contract, "SYMLINK_HANDLE_FLAGS", None)
    with RepositoryPathContract(tmp_path) as repository:
        with pytest.raises(RepositoryPathError, match="unsupported on this platform"):
            _assert_projection(repository)


def test_real_filesystem_unlink_recreate_smoke_control(tmp_path: Path) -> None:
    """One unmocked per-platform control over the retained link handle."""

    _projection_tree(tmp_path)
    projection = tmp_path / PROJECTION
    parent = os.open(
        projection.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    )
    try:
        handle = os.open(
            projection.name,
            projection_contract.SYMLINK_HANDLE_FLAGS,
            dir_fd=parent,
        )
        try:
            before = os.fstat(handle)
            assert stat.S_ISLNK(before.st_mode)
            assert before.st_nlink == 1
            projection.unlink()
            projection.symlink_to(LINK_TEXT)
            after = os.fstat(handle)
            assert after.st_nlink == 0
        finally:
            os.close(handle)
    finally:
        os.close(parent)
