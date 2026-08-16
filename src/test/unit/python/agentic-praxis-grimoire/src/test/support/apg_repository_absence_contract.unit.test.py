"""Bounded absent-entry and platform-stable path error controls."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_repository_path_contract import (  # noqa: E402
    RepositoryPathContract,
    RepositoryPathError,
)


def _appears_after_first_missing(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    present: os.stat_result,
) -> list[int]:
    module = importlib.import_module("apg_repository_path_contract")
    original = module._stat_component
    calls: list[int] = []

    def injected(component, *args, **kwargs):
        if component == name:
            calls.append(1)
            if len(calls) == 1:
                raise FileNotFoundError(component)
            return present
        return original(component, *args, **kwargs)

    monkeypatch.setattr(module, "_stat_component", injected)
    return calls


def test_final_missing_entry_appearing_before_return_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    (root / "owners").mkdir(parents=True)
    calls = _appears_after_first_missing(
        monkeypatch, "candidate", os.stat(root / "owners")
    )
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="changed during evaluation"):
            repository.entry_kind("owners/candidate")
    assert len(calls) == 2


@pytest.mark.parametrize("relative", ("missing/candidate", "missing/sub/candidate"))
def test_missing_ancestor_appearing_before_return_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, relative: str
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    calls = _appears_after_first_missing(monkeypatch, "missing", os.stat(root))
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="changed during evaluation"):
            repository.entry_kind(relative)
    assert len(calls) == 2


def test_missing_ancestor_appearing_as_symlink_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    link.symlink_to(outside, target_is_directory=True)
    calls = _appears_after_first_missing(monkeypatch, "missing", os.lstat(link))
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="changed during evaluation"):
            repository.entry_kind("missing/candidate")
    assert len(calls) == 2


def test_missing_glob_prefix_appearing_with_match_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    calls = _appears_after_first_missing(monkeypatch, "owners", os.stat(root))
    with RepositoryPathContract(root) as repository:
        with pytest.raises(RepositoryPathError, match="changed during evaluation"):
            repository.glob_regular_files("owners/*.txt")
    assert len(calls) == 2


def test_stable_final_and_ancestor_absence_pass(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    (root / "owners").mkdir(parents=True)
    with RepositoryPathContract(root) as repository:
        assert repository.entry_kind("owners/candidate") is None
        assert repository.entry_kind("missing/sub/candidate") is None
        assert repository.glob_regular_files("missing/*.txt") == ()


def test_present_direct_owner_behavior_is_unchanged(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    owner = root / "owners/candidate"
    owner.parent.mkdir(parents=True)
    owner.write_text("present\n", encoding="utf-8")
    with RepositoryPathContract(root) as repository:
        assert repository.entry_kind("owners/candidate") == "regular"


def test_detached_component_uses_stable_public_error_and_preserves_cause(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    (root / "owners").mkdir(parents=True)
    with RepositoryPathContract(root) as repository:
        chain = repository.open_chain(("owners",))
        assert chain is not None
        (root / "owners").rename(root / "detached")
        monkeypatch.setattr(repository, "assert_root_binding", lambda: None)
        with pytest.raises(
            RepositoryPathError,
            match=r"^repository path component changed during evaluation$",
        ) as failure:
            chain.revalidate()
        assert isinstance(failure.value.__cause__, FileNotFoundError)
        chain.close()


def test_glob_enumeration_errno_is_normalized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    owner = root / "owners/candidate.txt"
    owner.parent.mkdir(parents=True)
    owner.write_text("present\n", encoding="utf-8")
    module = importlib.import_module("apg_repository_path_contract")
    original = module._stat_component

    def disappear(name, *args, **kwargs):
        if name == "candidate.txt":
            raise FileNotFoundError("platform-specific spelling")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(module, "_stat_component", disappear)
    with RepositoryPathContract(root) as repository:
        with pytest.raises(
            RepositoryPathError,
            match=r"^repository glob changed during evaluation$",
        ) as failure:
            repository.glob_regular_files("owners/*.txt")
    assert isinstance(failure.value.__cause__, FileNotFoundError)
