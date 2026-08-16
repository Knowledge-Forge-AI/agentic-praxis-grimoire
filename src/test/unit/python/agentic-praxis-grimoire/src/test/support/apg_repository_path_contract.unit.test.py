"""Descriptor-relative repository path and complete path-chain contracts."""

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
from apg_repository_path_contract import (  # noqa: E402
    RepositoryPathContract,
    RepositoryPathError,
)


def _write(path: Path, content: bytes = b"owned\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _externalize(root: Path, outside: Path, relative: str) -> None:
    directory = root / relative
    directory.rename(outside)
    directory.symlink_to(outside, target_is_directory=True)


def test_root_symlink_resolves_once_to_physical_authority(tmp_path: Path) -> None:
    physical = tmp_path / "physical"
    replacement = tmp_path / "replacement"
    _write(physical / "owners/value.txt", b"physical")
    _write(replacement / "owners/value.txt", b"replacement")
    link = tmp_path / "repository"
    link.symlink_to(physical, target_is_directory=True)

    with RepositoryPathContract(link) as repository:
        link.unlink()
        link.symlink_to(replacement, target_is_directory=True)
        assert repository.root == physical.resolve()
        assert repository.read_bytes("owners/value.txt") == b"physical"
        with RepositoryPathContract(link) as nested:
            assert nested.root == physical.resolve()
            assert nested.read_bytes("owners/value.txt") == b"physical"


@pytest.mark.parametrize(
    "relative",
    (
        "",
        "/absolute",
        ".",
        "owners/.",
        "owners/..",
        "owners//value",
        "owners\\value",
        "owners/\x00value",
        "owners/\nvalue",
        "owners/\x7fvalue",
    ),
)
def test_invalid_repository_relative_paths_fail(
    tmp_path: Path, relative: str
) -> None:
    tmp_path.mkdir(exist_ok=True)
    with RepositoryPathContract(tmp_path) as repository:
        with pytest.raises(RepositoryPathError, match="relative|component"):
            repository.entry_kind(relative)


def test_direct_read_directory_and_missing_entry(tmp_path: Path) -> None:
    _write(tmp_path / "owners/value.txt", "snowman \N{SNOWMAN}\n".encode())
    with RepositoryPathContract(tmp_path) as repository:
        repository.assert_directory("owners")
        assert repository.directory_entries("owners") == ("value.txt",)
        assert repository.entry_kind("owners") == "directory"
        assert repository.entry_kind("owners/value.txt") == "regular"
        assert repository.entry_kind("owners/missing.txt") is None
        assert repository.read_text("owners/value.txt") == "snowman \N{SNOWMAN}\n"


@pytest.mark.parametrize("shape", ("external", "dangling", "wrong-target"))
def test_symlinked_ancestor_never_supplies_file(
    tmp_path: Path, shape: str
) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "outside"
    _write(root / "owners/value.txt")
    _externalize(root, outside, "owners")
    if shape == "dangling":
        outside.rename(tmp_path / "preserved")
    elif shape == "wrong-target":
        wrong = root / "wrong"
        outside.rename(wrong)
        (root / "owners").unlink()
        (root / "owners").symlink_to(wrong, target_is_directory=True)

    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="ancestor|directory"):
            repository.read_bytes("owners/value.txt")


def test_final_symlink_is_not_a_regular_file(tmp_path: Path) -> None:
    _write(tmp_path / "outside.txt")
    (tmp_path / "owners").mkdir()
    (tmp_path / "owners/value.txt").symlink_to(tmp_path / "outside.txt")
    with RepositoryPathContract(tmp_path) as repository:
        with pytest.raises(RepositoryPathError, match="regular|symlink"):
            repository.read_bytes("owners/value.txt")


def test_short_reads_are_completed(monkeypatch, tmp_path: Path) -> None:
    _write(tmp_path / "owners/value.txt", b"0123456789")
    original = path_contract._read_chunk

    def short_read(descriptor: int, size: int) -> bytes:
        return original(descriptor, min(size, 2))

    monkeypatch.setattr(path_contract, "_read_chunk", short_read)
    with RepositoryPathContract(tmp_path) as repository:
        assert repository.read_bytes("owners/value.txt") == b"0123456789"


@pytest.mark.parametrize("mutation", ("premature-eof", "grow", "shrink", "touch"))
def test_read_races_fail_closed(
    monkeypatch,
    tmp_path: Path,
    mutation: str,
) -> None:
    path = tmp_path / "owners/value.txt"
    _write(path, b"0123456789")
    original = path_contract._read_chunk
    calls = 0

    def mutate_read(descriptor: int, size: int) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 1:
            if mutation == "premature-eof":
                return b""
            if mutation == "grow":
                with path.open("ab") as stream:
                    stream.write(b"growth")
            elif mutation == "shrink":
                path.write_bytes(b"0")
            else:
                os.utime(path, ns=(1, 1))
        return original(descriptor, min(size, 2))

    monkeypatch.setattr(path_contract, "_read_chunk", mutate_read)
    with RepositoryPathContract(tmp_path) as repository:
        with pytest.raises(RepositoryPathError, match="changed|complete|size"):
            repository.read_bytes("owners/value.txt")


def test_final_entry_replacement_after_descriptor_stat_fails(
    monkeypatch, tmp_path: Path
) -> None:
    path = tmp_path / "owners/value.txt"
    replacement = tmp_path / "replacement.txt"
    _write(path, b"0123456789")
    _write(replacement, b"abcdefghij")
    original = path_contract._fstat
    regular_stats = 0

    def replace_after_final_descriptor_stat(descriptor: int):
        nonlocal regular_stats
        value = original(descriptor)
        if stat.S_ISREG(value.st_mode):
            regular_stats += 1
            if regular_stats == 2:
                path.unlink()
                path.write_bytes(replacement.read_bytes())
        return value

    monkeypatch.setattr(
        path_contract,
        "_fstat",
        replace_after_final_descriptor_stat,
    )
    with RepositoryPathContract(tmp_path) as repository:
        with pytest.raises(RepositoryPathError, match="entry|changed"):
            repository.read_bytes("owners/value.txt")


def test_final_swap_before_open_never_follows_replacement(
    monkeypatch, tmp_path: Path
) -> None:
    path = tmp_path / "owners/value.txt"
    outside = tmp_path / "outside.txt"
    _write(path)
    _write(outside, b"external")
    original = path_contract._open_component
    swapped = False

    def swap_open(name, flags, *, dir_fd=None):
        nonlocal swapped
        if name == "value.txt" and not swapped:
            swapped = True
            path.unlink()
            path.symlink_to(outside)
        return original(name, flags, dir_fd=dir_fd)

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(path_contract, "_open_component", swap_open)
        with pytest.raises(RepositoryPathError, match="regular|symlink|open"):
            repository.read_bytes("owners/value.txt")


def test_ancestor_swap_before_traversal_never_follows_replacement(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "outside"
    _write(root / "owners/value.txt")
    original = path_contract._open_component
    swapped = False

    def swap_open(name, flags, *, dir_fd=None):
        nonlocal swapped
        if name == "owners" and not swapped:
            swapped = True
            _externalize(root, outside, "owners")
        return original(name, flags, dir_fd=dir_fd)

    with RepositoryPathContract(root) as repository:
        monkeypatch.setattr(path_contract, "_open_component", swap_open)
        with pytest.raises(RepositoryPathError, match="ancestor|directory|open"):
            repository.read_bytes("owners/value.txt")


def test_descriptors_close_after_interruption(monkeypatch, tmp_path: Path) -> None:
    _write(tmp_path / "owners/value.txt")
    opened: list[int] = []
    original = path_contract._open_component

    def record_open(name, flags, *, dir_fd=None):
        descriptor = original(name, flags, dir_fd=dir_fd)
        opened.append(descriptor)
        return descriptor

    def interrupt(_descriptor: int, _size: int) -> bytes:
        raise KeyboardInterrupt

    with RepositoryPathContract(tmp_path) as repository:
        monkeypatch.setattr(path_contract, "_open_component", record_open)
        monkeypatch.setattr(path_contract, "_read_chunk", interrupt)
        with pytest.raises(KeyboardInterrupt):
            repository.read_bytes("owners/value.txt")
        for descriptor in opened:
            with pytest.raises(OSError):
                os.fstat(descriptor)


@pytest.mark.parametrize("failure", ("oserror", "interrupt"))
def test_root_descriptor_closes_when_inspection_fails(
    monkeypatch, tmp_path: Path, failure: str
) -> None:
    opened: list[int] = []
    original_open = path_contract._open_component

    def record_open(name, flags, *, dir_fd=None):
        descriptor = original_open(name, flags, dir_fd=dir_fd)
        opened.append(descriptor)
        return descriptor

    def fail_inspection(_descriptor: int):
        if failure == "oserror":
            raise OSError("injected root inspection failure")
        raise KeyboardInterrupt

    monkeypatch.setattr(path_contract, "_open_component", record_open)
    monkeypatch.setattr(path_contract, "_fstat", fail_inspection)
    expected = RepositoryPathError if failure == "oserror" else KeyboardInterrupt
    with pytest.raises(expected):
        RepositoryPathContract(tmp_path)
    assert opened
    for descriptor in opened:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def test_glob_enumerates_only_direct_repository_files(tmp_path: Path) -> None:
    _write(tmp_path / "fixtures/a-example.json")
    _write(tmp_path / "fixtures/nested/b-example.json")
    with RepositoryPathContract(tmp_path) as repository:
        assert repository.glob_regular_files(
            "fixtures/**/*example*.json"
        ) == (
            "fixtures/a-example.json",
            "fixtures/nested/b-example.json",
        )
    _externalize(tmp_path, tmp_path / "external-fixtures", "fixtures")
    with RepositoryPathContract(tmp_path) as repository:
        with pytest.raises(RepositoryPathError, match="ancestor|directory"):
            repository.glob_regular_files("fixtures/**/*example*.json")


# --- APG60H K2: complete repository-relative path-chain observation ---------


def _nested_tree(root: Path) -> None:
    _write(root / "testing/nested/manifest.txt", b"OLD")
    _write(root / "testing/nested/other.txt", b"OLD")


def _detach(root: Path, relative: str, *, shape: str = "recreate") -> None:
    """Replace one intermediate component while its own parent is untouched."""

    current = root / relative
    detached = current.with_name(current.name + "-detached")
    current.rename(detached)
    if shape == "symlink":
        current.symlink_to(detached, target_is_directory=True)
        return
    if shape == "removed":
        return
    current.mkdir()
    _write(current / "manifest.txt", b"NEW")
    _write(current / "other.txt", b"NEW")


def _swap_during(monkeypatch, action) -> None:
    original = path_contract._stat_component
    fired = False

    def observe(name, *, dir_fd=None, follow_symlinks=True):
        nonlocal fired
        value = original(name, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if not fired and name == "manifest.txt":
            fired = True
            action()
        return value

    monkeypatch.setattr(path_contract, "_stat_component", observe)


@pytest.mark.parametrize("shape", ("recreate", "symlink", "removed"))
def test_detached_intermediate_ancestor_never_supplies_a_read(
    monkeypatch, tmp_path: Path, shape: str
) -> None:
    """Reproduce the APG60G detached-ancestor read and require it to fail."""

    root = tmp_path / "repository"
    _nested_tree(root)
    _swap_during(
        monkeypatch, lambda: _detach(root, "testing/nested", shape=shape)
    )
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="component changed"):
            repository.read_bytes("testing/nested/manifest.txt")


def test_top_level_ancestor_detach_is_detected(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _nested_tree(root)
    _swap_during(monkeypatch, lambda: _detach(root, "testing"))
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="root entry|component"):
            repository.read_bytes("testing/nested/manifest.txt")


def _detach_after_listing(monkeypatch, root: Path) -> None:
    original = path_contract._list_directory
    fired = False

    def detach(descriptor: int):
        nonlocal fired
        names = original(descriptor)
        if not fired and "manifest.txt" in names:
            fired = True
            _detach(root, "testing/nested")
        return names

    monkeypatch.setattr(path_contract, "_list_directory", detach)


def test_detached_ancestor_blocks_directory_enumeration(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _nested_tree(root)
    _detach_after_listing(monkeypatch, root)
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="component changed"):
            repository.directory_entries("testing/nested")


def test_detached_ancestor_blocks_a_glob(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repository"
    _nested_tree(root)
    _detach_after_listing(monkeypatch, root)
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="component changed"):
            repository.glob_regular_files("testing/**/*.txt")


def test_detached_branch_blocks_a_recursive_glob(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _write(root / "skills/first/SKILL.md")
    _write(root / "skills/second/SKILL.md")
    original = path_contract._stat_component
    fired = False

    def detach_first_branch(name, *, dir_fd=None, follow_symlinks=True):
        nonlocal fired
        value = original(name, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if not fired and name == "SKILL.md":
            fired = True
            _detach(root, "skills/first")
        return value

    monkeypatch.setattr(path_contract, "_stat_component", detach_first_branch)
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="component changed"):
            repository.glob_regular_files("skills/**/SKILL.md")


def test_entry_kind_reports_absence_only_on_a_coherent_chain(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _nested_tree(root)
    original = path_contract._stat_component
    fired = False

    def detach_on_lookup(name, *, dir_fd=None, follow_symlinks=True):
        nonlocal fired
        if not fired and name == "missing.txt":
            fired = True
            _detach(root, "testing/nested")
        return original(name, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(path_contract, "_stat_component", detach_on_lookup)
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="component changed"):
            repository.entry_kind("testing/nested/missing.txt")


def test_unchanged_direct_chain_succeeds(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    _nested_tree(root)
    with RepositoryPathContract(root) as repository:
        assert repository.read_bytes("testing/nested/manifest.txt") == b"OLD"
        assert repository.entry_kind("testing/nested") == "directory"
        assert repository.directory_entries("testing/nested") == (
            "manifest.txt",
            "other.txt",
        )
        repository.assert_directory("testing/nested")
        assert repository.glob_regular_files("testing/**/*.txt") == (
            "testing/nested/manifest.txt",
            "testing/nested/other.txt",
        )


def test_retained_component_ceiling_fails_closed(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _nested_tree(root)
    monkeypatch.setattr(path_contract, "MAX_RETAINED_COMPONENTS", 1)
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="retained ceiling"):
            repository.read_bytes("testing/nested/manifest.txt")


def test_chain_descriptors_close_after_every_operation(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    _nested_tree(root)
    with RepositoryPathContract(root) as repository:
        before = len(os.listdir("/dev/fd"))
        repository.read_bytes("testing/nested/manifest.txt")
        repository.directory_entries("testing/nested")
        repository.glob_regular_files("testing/**/*.txt")
        repository.entry_kind("testing/nested/manifest.txt")
        assert len(os.listdir("/dev/fd")) == before
