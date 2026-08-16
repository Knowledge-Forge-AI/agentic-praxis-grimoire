"""Pinned decorated evaluations revalidate their physical root before success."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_pinned_root_contract import pinned_repository_root  # noqa: E402
from apg_repository_path_contract import (  # noqa: E402
    RepositoryPathContract,
    RepositoryPathError,
)


def _write(path: Path, content: bytes = b"owned\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _replace_root(root: Path, shape: str) -> None:
    detached = root.with_name(root.name + "-detached")
    root.rename(detached)
    if shape == "recreate":
        root.mkdir()
    elif shape == "symlink":
        root.symlink_to(detached, target_is_directory=True)
    elif shape == "other-directory":
        other = root.with_name(root.name + "-other")
        other.mkdir()
        other.rename(root)


def _read_owner(pinned: Path) -> bytes:
    with RepositoryPathContract(pinned) as nested:
        return nested.read_bytes("owners/value.txt")


@pytest.mark.parametrize(
    "shape", ("recreate", "symlink", "other-directory", "removed")
)
def test_decorated_evaluation_fails_after_root_replacement(
    tmp_path: Path, shape: str
) -> None:
    """Reproduce the APG60G decorated success after the pinned root moved."""

    root = tmp_path / "repository"
    _write(root / "owners/value.txt")

    @pinned_repository_root
    def replace(pinned: Path) -> str:
        _replace_root(pinned, shape)
        return "decorated success"

    with pytest.raises(
        RepositoryPathError, match="root entry|cannot be revalidated"
    ):
        replace(root)


def test_decorated_evaluation_succeeds_on_an_unchanged_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    _write(root / "owners/value.txt", b"kept")

    read = pinned_repository_root(_read_owner)
    assert read(root) == b"kept"


def test_nested_decorated_evaluations_share_one_physical_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    _write(root / "owners/value.txt", b"kept")
    observed: list[Path] = []

    @pinned_repository_root
    def inner(pinned: Path) -> bytes:
        observed.append(pinned)
        return _read_owner(pinned)

    @pinned_repository_root
    def outer(pinned: Path) -> bytes:
        observed.append(pinned)
        return inner(pinned)

    assert outer(root) == b"kept"
    assert observed == [root.resolve(), root.resolve()]


def test_nested_contract_over_the_same_physical_root_is_reused(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    link = tmp_path / "spelling"
    _write(root / "owners/value.txt", b"kept")
    link.symlink_to(root, target_is_directory=True)

    @pinned_repository_root
    def read_through_both_spellings(pinned: Path) -> tuple[bytes, bytes]:
        with RepositoryPathContract(link) as nested:
            spelled = nested.read_bytes("owners/value.txt")
        return _read_owner(pinned), spelled

    assert read_through_both_spellings(link) == (b"kept", b"kept")


def test_nested_evaluation_cannot_substitute_another_repository(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    other = tmp_path / "other"
    _write(root / "owners/value.txt")
    _write(other / "owners/value.txt", b"substitute")

    @pinned_repository_root
    def substitute(_pinned: Path) -> bytes:
        return _read_owner(other)

    with pytest.raises(RepositoryPathError, match="substitute another"):
        substitute(root)


def test_decorated_function_exception_stays_primary(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    _write(root / "owners/value.txt")

    @pinned_repository_root
    def fail_only(_pinned: Path) -> None:
        raise LookupError("owner-specific failure")

    with pytest.raises(LookupError, match="owner-specific failure"):
        fail_only(root)


def test_decorated_exception_is_not_masked_by_root_replacement(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    _write(root / "owners/value.txt")

    @pinned_repository_root
    def fail_after_replacement(pinned: Path) -> None:
        _replace_root(pinned, "recreate")
        raise LookupError("owner-specific failure")

    with pytest.raises(LookupError, match="owner-specific failure"):
        fail_after_replacement(root)


def test_decorated_evaluation_leaks_no_descriptor(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    _write(root / "owners/value.txt")
    read = pinned_repository_root(_read_owner)

    before = len(os.listdir("/dev/fd"))
    read(root)
    with pytest.raises(RepositoryPathError):
        pinned_repository_root(
            lambda pinned: _replace_root(pinned, "recreate")
        )(root)
    assert len(os.listdir("/dev/fd")) == before


def test_pinned_root_is_released_after_each_evaluation(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    other = tmp_path / "other"
    _write(root / "owners/value.txt")
    _write(other / "owners/value.txt", b"independent")
    read = pinned_repository_root(_read_owner)

    assert read(root) == b"owned\n"
    assert read(other) == b"independent"


def test_decorated_owner_identity_is_preserved(tmp_path: Path) -> None:
    @pinned_repository_root
    def documented_owner(_pinned: Path) -> None:
        """Owner docstring retained for review."""

    assert documented_owner.__name__ == "documented_owner"
    assert documented_owner.__doc__ == "Owner docstring retained for review."
