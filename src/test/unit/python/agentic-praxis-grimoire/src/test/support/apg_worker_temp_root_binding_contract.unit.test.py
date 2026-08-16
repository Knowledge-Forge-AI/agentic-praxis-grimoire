"""APG60I worker-temp root-binding controls."""

from __future__ import annotations

import importlib
from pathlib import Path
import shutil
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))


def _module():
    return importlib.import_module("apg_worker_temp_contract")


def _cleanup_module():
    return importlib.import_module("apg_worker_temp_cleanup_contract")


def _owned_roots(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    selected = tmp_path / "authorized"
    selected.mkdir()
    return repository, selected


def _restore_selected(selected: Path, original: Path) -> None:
    if selected.is_symlink():
        selected.unlink()
    elif selected.exists():
        shutil.rmtree(selected)
    if original.exists():
        original.rename(selected)


def test_replaced_temp_root_symlink_never_receives_a_repository_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _owned_roots(tmp_path)
    original_selected = tmp_path / "authorized-original"
    module = _module()
    cleanup = _cleanup_module()
    original_mkdir = cleanup._mkdir_child
    created_in_repository: list[bool] = []
    substituted = False

    def replace_then_create(state, name: str) -> None:
        nonlocal substituted
        selected.rename(original_selected)
        selected.symlink_to(repository, target_is_directory=True)
        substituted = True
        original_mkdir(state, name)
        created_in_repository.append((repository / name).exists())

    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setattr(cleanup, "_mkdir_child", replace_then_create)
    rejected = False
    try:
        try:
            with module.worker_temp_environment(repository):
                pass
        except module.WorkerTempError:
            rejected = True
        assert not any(created_in_repository), (
            "validated temporary-root substitution created a repository child"
        )
        assert substituted, "temporary-root substitution hook did not run"
        assert rejected, "temporary-root substitution was not rejected"
    finally:
        _restore_selected(selected, original_selected)


def test_recreated_direct_temp_root_receives_no_child_and_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _owned_roots(tmp_path)
    original_selected = tmp_path / "authorized-original"
    module = _module()
    cleanup = _cleanup_module()
    original_mkdir = cleanup._mkdir_child
    created_in_replacement: list[bool] = []
    substituted = False

    def replace_then_create(state, name: str) -> None:
        nonlocal substituted
        selected.rename(original_selected)
        selected.mkdir()
        substituted = True
        original_mkdir(state, name)
        created_in_replacement.append((selected / name).exists())

    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setattr(cleanup, "_mkdir_child", replace_then_create)
    rejected = False
    try:
        try:
            with module.worker_temp_environment(repository):
                pass
        except module.WorkerTempError:
            rejected = True
        assert not any(created_in_replacement), (
            "recreated temporary-root replacement received a worker child"
        )
        assert substituted, "temporary-root substitution hook did not run"
        assert rejected, "direct temporary-root substitution was not rejected"
    finally:
        _restore_selected(selected, original_selected)


def test_post_create_physical_validation_failure_leaves_no_residue(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repository, selected = _owned_roots(tmp_path)
    module = _module()
    cleanup = _cleanup_module()
    def fail_child_validation(_state) -> None:
        raise module.WorkerTempError("controlled child validation failure")

    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setattr(
        cleanup, "_verify_child", fail_child_validation
    )
    with pytest.raises(module.WorkerTempError, match="child validation"):
        with module.worker_temp_environment(repository):
            pytest.fail("post-create validation failure was not raised")

    children = tuple(selected.iterdir())
    try:
        assert children == (), (
            "post-create validation failure left an unowned worker child"
        )
    finally:
        for child in children:
            if child.is_symlink() or child.is_file():
                child.unlink()
            else:
                shutil.rmtree(child)


@pytest.mark.parametrize("replacement", ("repository-symlink", "direct-directory"))
def test_replaced_temp_root_ancestor_is_rejected_without_external_child(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    replacement: str,
) -> None:
    repository = tmp_path / "repository"
    (repository / "authorized").mkdir(parents=True)
    ancestor = tmp_path / "scratch-parent"
    selected = ancestor / "authorized"
    selected.mkdir(parents=True)
    original_ancestor = tmp_path / "scratch-parent-original"
    module = _module()
    cleanup = _cleanup_module()
    original_mkdir = cleanup._mkdir_child

    def replace_ancestor_then_create(state, name: str) -> None:
        ancestor.rename(original_ancestor)
        if replacement == "repository-symlink":
            ancestor.symlink_to(repository, target_is_directory=True)
        else:
            (ancestor / "authorized").mkdir(parents=True)
        original_mkdir(state, name)

    monkeypatch.setenv("TMPDIR", str(selected))
    monkeypatch.setattr(cleanup, "_mkdir_child", replace_ancestor_then_create)
    try:
        with pytest.raises(module.WorkerTempError, match="changed"):
            with module.worker_temp_environment(repository):
                pytest.fail("replaced ancestor was accepted")
        assert tuple((original_ancestor / "authorized").iterdir()) == ()
        assert tuple((repository / "authorized").iterdir()) == ()
        if replacement == "direct-directory":
            assert tuple((ancestor / "authorized").iterdir()) == ()
    finally:
        if ancestor.is_symlink():
            ancestor.unlink()
        elif ancestor.exists():
            shutil.rmtree(ancestor)
        original_ancestor.rename(ancestor)
