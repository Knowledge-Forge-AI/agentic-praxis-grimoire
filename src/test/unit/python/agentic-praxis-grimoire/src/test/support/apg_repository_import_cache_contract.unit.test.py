"""Bounded parent-cache assertions for repository-import isolation."""

from __future__ import annotations

import importlib
import importlib.machinery
import os
from pathlib import Path
import sys
from types import ModuleType

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_repository_import_cache_contract import (  # noqa: E402
    RepositoryImportCacheError,
    snapshot_repository_import_state,
)


def _module(name: str, origin: Path) -> ModuleType:
    module = ModuleType(name)
    module.__file__ = str(origin)
    module.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, origin=str(origin))
    return module


def _restore_module(name: str, previous: object) -> None:
    if previous is _ABSENT:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = previous


def _restore_importer(key: str, previous: object) -> None:
    if previous is _ABSENT:
        sys.path_importer_cache.pop(key, None)
    else:
        sys.path_importer_cache[key] = previous


class _EqualButDistinct:
    def __eq__(self, other: object) -> bool:
        return isinstance(other, _EqualButDistinct)


_ABSENT = object()
_MODULE_RESTORATION_ERROR = "pre-existing relevant module entry was not restored"
_NEW_MODULE_ERROR = "new relevant module entry survived"
_IMPORTER_RESTORATION_ERROR = "inspected-repository importer cache was not restored"


def test_snapshot_accepts_exact_relevant_state(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    name = "apg_cache_exact"
    previous = sys.modules.get(name, _ABSENT)
    module = _module(name, tmp_path / "outside.py")
    sys.modules[name] = module
    try:
        state = snapshot_repository_import_state(root, {name})
        state.assert_restored()
        assert sys.modules[name] is module
    finally:
        _restore_module(name, previous)


@pytest.mark.parametrize(
    ("name", "before_kind", "mutation", "expected_error"),
    (
        pytest.param("apg66d_preserved_module", "module", "keep", None, id="module-object"),
        pytest.param("apg66d_preserved_none", "none", "keep", None, id="none-sentinel"),
        pytest.param("apg66d_preserved_package", "module", "keep", None, id="package-object"),
        pytest.param("apg66d_preserved_package.child", "module", "keep", None, id="submodule-object"),
        pytest.param("apg66d_preserved_none_package", "none", "keep", None, id="package-none"),
        pytest.param("apg66d_preserved_none_package.child", "none", "keep", None, id="submodule-none"),
        pytest.param("apg66d_removed_module", "module", "remove", _MODULE_RESTORATION_ERROR, id="module-removed"),
        pytest.param("apg66d_removed_none", "none", "remove", _MODULE_RESTORATION_ERROR, id="none-removed"),
        pytest.param("apg66d_module_to_none", "module", "none", _MODULE_RESTORATION_ERROR, id="module-to-none"),
        pytest.param("apg66d_none_to_module", "none", "module", _MODULE_RESTORATION_ERROR, id="none-to-module"),
        pytest.param("apg66d_module_to_module", "module", "module", _MODULE_RESTORATION_ERROR, id="module-to-module"),
        pytest.param("apg66d_removed_package", "module", "remove", _MODULE_RESTORATION_ERROR, id="package-removed"),
        pytest.param("apg66d_removed_package.child", "module", "remove", _MODULE_RESTORATION_ERROR, id="submodule-removed"),
        pytest.param("apg66d_new_relevant_none", "absent", "none", _NEW_MODULE_ERROR, id="absent-to-none"),
        pytest.param("apg66d_new_relevant_module", "absent", "module", _NEW_MODULE_ERROR, id="absent-to-module"),
    ),
)
def test_snapshot_module_entry_presence_and_identity_matrix(
    tmp_path: Path, name: str, before_kind: str, mutation: str,
    expected_error: str | None,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    previous = sys.modules.get(name, _ABSENT)
    original = None if before_kind == "none" else _module(name, tmp_path / "original.py")
    if before_kind != "absent":
        sys.modules[name] = original
    else:
        sys.modules.pop(name, None)
    state = snapshot_repository_import_state(root, {name})
    if mutation == "remove":
        del sys.modules[name]
    elif mutation == "none":
        sys.modules[name] = None
    elif mutation == "module":
        sys.modules[name] = _module(name, tmp_path / "replacement.py")
    try:
        if expected_error is None:
            state.assert_restored()
            assert name in sys.modules and sys.modules[name] is original
        else:
            with pytest.raises(RepositoryImportCacheError, match=expected_error):
                state.assert_restored()
    finally:
        _restore_module(name, previous)


def test_snapshot_leaves_unrelated_preexisting_none_untouched(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    name = "apg66d_unrelated_preexisting_none"
    previous = sys.modules.get(name, _ABSENT)
    sys.modules[name] = None
    try:
        state = snapshot_repository_import_state(root, {"apg66d_absent_local"})
        state.assert_restored()
        assert name in sys.modules
        assert sys.modules[name] is None
    finally:
        _restore_module(name, previous)


def test_snapshot_rejects_deleted_entry_despite_new_relevant_entry(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    removed = "apg66d_coordinated_removed"
    introduced = "apg66d_coordinated_introduced"
    previous_removed = sys.modules.get(removed, _ABSENT)
    previous_introduced = sys.modules.get(introduced, _ABSENT)
    sys.modules[removed] = None
    state = snapshot_repository_import_state(root, {removed, introduced})
    del sys.modules[removed]
    sys.modules[introduced] = None
    try:
        with pytest.raises(RepositoryImportCacheError, match=_MODULE_RESTORATION_ERROR):
            state.assert_restored()
    finally:
        _restore_module(removed, previous_removed)
        _restore_module(introduced, previous_introduced)


def test_unrelated_none_does_not_mask_relevant_none_removal(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    relevant = "apg66d_relevant_none"
    unrelated = "apg66d_unrelated_none"
    previous_relevant = sys.modules.get(relevant, _ABSENT)
    previous_unrelated = sys.modules.get(unrelated, _ABSENT)
    sys.modules[relevant] = None
    state = snapshot_repository_import_state(root, {relevant})
    del sys.modules[relevant]
    sys.modules[unrelated] = None
    try:
        with pytest.raises(RepositoryImportCacheError, match=_MODULE_RESTORATION_ERROR):
            state.assert_restored()
    finally:
        _restore_module(relevant, previous_relevant)
        _restore_module(unrelated, previous_unrelated)


def test_same_suffix_name_does_not_mask_relevant_removal(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    relevant = "apg66d_suffix_owner.child"
    unrelated = "apg66d_other_owner.child"
    previous_relevant = sys.modules.get(relevant, _ABSENT)
    previous_unrelated = sys.modules.get(unrelated, _ABSENT)
    original = _module(relevant, tmp_path / "outside.py")
    sys.modules[relevant] = original
    state = snapshot_repository_import_state(root, {relevant})
    del sys.modules[relevant]
    sys.modules[unrelated] = original
    try:
        with pytest.raises(RepositoryImportCacheError, match=_MODULE_RESTORATION_ERROR):
            state.assert_restored()
    finally:
        _restore_module(relevant, previous_relevant)
        _restore_module(unrelated, previous_unrelated)


@pytest.mark.parametrize("removed", ("parent", "child"))
def test_parent_and_child_entries_are_checked_independently(tmp_path: Path, removed: str) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    parent = "apg66d_independent_package"
    child = parent + ".child"
    previous_parent = sys.modules.get(parent, _ABSENT)
    previous_child = sys.modules.get(child, _ABSENT)
    sys.modules[parent] = _module(parent, tmp_path / "package.py")
    sys.modules[child] = None
    state = snapshot_repository_import_state(root, {parent, child})
    del sys.modules[parent if removed == "parent" else child]
    try:
        with pytest.raises(RepositoryImportCacheError, match=_MODULE_RESTORATION_ERROR):
            state.assert_restored()
    finally:
        _restore_module(parent, previous_parent)
        _restore_module(child, previous_child)


def test_equal_but_distinct_preexisting_value_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    name = "apg66d_equal_but_distinct"
    previous = sys.modules.get(name, _ABSENT)
    original = _EqualButDistinct()
    replacement = _EqualButDistinct()
    assert replacement == original
    assert replacement is not original
    sys.modules[name] = original
    state = snapshot_repository_import_state(root, {name})
    sys.modules[name] = replacement
    try:
        with pytest.raises(RepositoryImportCacheError, match=_MODULE_RESTORATION_ERROR):
            state.assert_restored()
    finally:
        _restore_module(name, previous)


def test_present_none_and_absent_local_name_are_independent(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    present = "apg66d_present_none"
    absent = "apg66d_absent_companion"
    previous_present = sys.modules.get(present, _ABSENT)
    previous_absent = sys.modules.get(absent, _ABSENT)
    sys.modules[present] = None
    sys.modules.pop(absent, None)
    try:
        state = snapshot_repository_import_state(root, {present, absent})
        state.assert_restored()
        assert present in sys.modules and sys.modules[present] is None
        assert absent not in sys.modules
    finally:
        _restore_module(present, previous_present)
        _restore_module(absent, previous_absent)


def test_none_sentinel_survives_unrelated_importer_cache_growth(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    name = "apg66d_none_with_unrelated_cache_growth"
    key = str(outside)
    previous_module = sys.modules.get(name, _ABSENT)
    previous_importer = sys.path_importer_cache.get(key, _ABSENT)
    sys.modules[name] = None
    state = snapshot_repository_import_state(root, {name})
    sys.path_importer_cache[key] = object()
    try:
        state.assert_restored()
        assert name in sys.modules and sys.modules[name] is None
    finally:
        _restore_module(name, previous_module)
        _restore_importer(key, previous_importer)


def test_import_distinguishes_present_none_from_absent_key(tmp_path: Path) -> None:
    root = tmp_path / "disposable-import-root"
    root.mkdir()
    name = "apg66d_disposable_import_semantics"
    (root / f"{name}.py").write_text("VALUE = 'loaded'\n", encoding="utf-8")
    key = str(root)
    previous_module = sys.modules.get(name, _ABSENT)
    previous_importer = sys.path_importer_cache.get(key, _ABSENT)
    parent_path = tuple(sys.path)
    sys.path.insert(0, key)
    try:
        sys.modules[name] = None
        with pytest.raises(ModuleNotFoundError, match=f"import of {name} halted"):
            importlib.import_module(name)
        del sys.modules[name]
        loaded = importlib.import_module(name)
        assert loaded.VALUE == "loaded"
    finally:
        _restore_module(name, previous_module)
        assert sys.path[0] == key
        del sys.path[0]
        _restore_importer(key, previous_importer)
        assert tuple(sys.path) == parent_path


def test_snapshot_preserves_relevant_none_importer_entry(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    key = str(root)
    previous = sys.path_importer_cache.get(key, _ABSENT)
    sys.path_importer_cache[key] = None
    try:
        state = snapshot_repository_import_state(root, set())
        state.assert_restored()
        assert key in sys.path_importer_cache
        assert sys.path_importer_cache[key] is None
    finally:
        _restore_importer(key, previous)


@pytest.mark.parametrize(
    ("before_kind", "mutation"),
    (
        ("object", "remove"),
        ("none", "remove"),
        ("object", "replace"),
        ("none", "replace"),
        ("absent", "insert-none"),
    ),
    ids=(
        "object-removed",
        "none-removed",
        "object-replaced",
        "none-replaced",
        "absent-key-gains-none",
    ),
)
def test_snapshot_rejects_relevant_importer_entry_mutations(
    tmp_path: Path, before_kind: str, mutation: str
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    key = str(root)
    previous = sys.path_importer_cache.get(key, _ABSENT)
    if before_kind == "object":
        sys.path_importer_cache[key] = object()
    elif before_kind == "none":
        sys.path_importer_cache[key] = None
    else:
        sys.path_importer_cache.pop(key, None)
    state = snapshot_repository_import_state(root, set())
    if mutation == "remove":
        del sys.path_importer_cache[key]
    elif mutation == "replace":
        sys.path_importer_cache[key] = object()
    else:
        sys.path_importer_cache[key] = None
    try:
        with pytest.raises(RepositoryImportCacheError, match=_IMPORTER_RESTORATION_ERROR):
            state.assert_restored()
    finally:
        _restore_importer(key, previous)


def test_snapshot_rejects_repository_module_residue(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    name = "apg_cache_leaked"
    previous = sys.modules.get(name, _ABSENT)
    state = snapshot_repository_import_state(root, {name})
    sys.modules[name] = _module(name, root / "helper.py")
    try:
        with pytest.raises(RepositoryImportCacheError):
            state.assert_restored()
    finally:
        _restore_module(name, previous)


def test_snapshot_rejects_unlisted_repository_module_residue(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    name = "apg_cache_unlisted_leak"
    previous = sys.modules.get(name, _ABSENT)
    state = snapshot_repository_import_state(root, set())
    sys.modules[name] = _module(name, root / "helper.py")
    try:
        with pytest.raises(RepositoryImportCacheError, match="inspected repository"):
            state.assert_restored()
    finally:
        _restore_module(name, previous)


def test_snapshot_rejects_repository_residue_after_exception(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    name = "apg_cache_exception_leak"
    previous = sys.modules.get(name, _ABSENT)
    state = snapshot_repository_import_state(root, {name})

    def failing_operation() -> None:
        sys.modules[name] = _module(name, root / "helper.py")
        raise RuntimeError("operation failed after repository import")

    try:
        with pytest.raises(RuntimeError, match="failed after repository import"):
            failing_operation()
        with pytest.raises(
            RepositoryImportCacheError,
            match="new relevant module entry survived",
        ):
            state.assert_restored()
    finally:
        _restore_module(name, previous)


@pytest.mark.parametrize("name", ("apg_cache_package", "apg_cache_package.child"))
def test_snapshot_checks_repository_package_and_submodule(
    tmp_path: Path,
    name: str,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    previous = sys.modules.get(name, _ABSENT)
    state = snapshot_repository_import_state(
        root,
        {"apg_cache_package", "apg_cache_package.child"},
    )
    relative = "package/__init__.py" if "." not in name else "package/child.py"
    sys.modules[name] = _module(name, root / relative)
    try:
        with pytest.raises(RepositoryImportCacheError):
            state.assert_restored()
    finally:
        _restore_module(name, previous)


@pytest.mark.parametrize("change", ("replace", "remove"))
def test_snapshot_rejects_changed_preexisting_relevant_entry(
    tmp_path: Path,
    change: str,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    name = "apg_cache_preexisting"
    previous = sys.modules.get(name, _ABSENT)
    original = _module(name, tmp_path / "original.py")
    sys.modules[name] = original
    state = snapshot_repository_import_state(root, {name})
    if change == "replace":
        sys.modules[name] = _module(name, tmp_path / "replacement.py")
    else:
        sys.modules.pop(name)
    try:
        with pytest.raises(RepositoryImportCacheError, match="relevant module entry"):
            state.assert_restored()
    finally:
        _restore_module(name, previous)


def test_snapshot_rejects_parent_search_path_residue(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    state = snapshot_repository_import_state(root, set())
    sys.path.append(str(root))
    try:
        with pytest.raises(RepositoryImportCacheError, match="search path"):
            state.assert_restored()
    finally:
        sys.path.pop()


@pytest.mark.parametrize("change", ("add", "replace"))
def test_snapshot_rejects_repository_importer_cache_residue(
    tmp_path: Path,
    change: str,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    key = str(root)
    previous = sys.path_importer_cache.get(key, _ABSENT)
    if change == "replace":
        sys.path_importer_cache[key] = object()
    state = snapshot_repository_import_state(root, set())
    sys.path_importer_cache[key] = object()
    try:
        with pytest.raises(RepositoryImportCacheError, match="importer cache"):
            state.assert_restored()
    finally:
        if previous is _ABSENT:
            sys.path_importer_cache.pop(key, None)
        else:
            sys.path_importer_cache[key] = previous


def test_snapshot_allows_unrelated_first_loaded_module(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "harness"
    root.mkdir()
    outside.mkdir()
    name = "apg_cache_unrelated_harness"
    previous = sys.modules.get(name, _ABSENT)
    state = snapshot_repository_import_state(root, {"apg_cache_local"})
    module = _module(name, outside / "helper.py")
    sys.modules[name] = module
    try:
        state.assert_restored()
        assert sys.modules[name] is module
    finally:
        _restore_module(name, previous)


def test_snapshot_leaves_preexisting_unrelated_module_untouched(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    name = "apg_cache_preexisting_unrelated"
    previous = sys.modules.get(name, _ABSENT)
    module = _module(name, tmp_path / "outside.py")
    sys.modules[name] = module
    try:
        state = snapshot_repository_import_state(root, {"apg_cache_local"})
        state.assert_restored()
        assert sys.modules[name] is module
    finally:
        _restore_module(name, previous)


def test_snapshot_uses_origin_not_resembling_module_name(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    local = "apg_cache_local"
    resembling = local + "_helper"
    previous = sys.modules.get(resembling, _ABSENT)
    state = snapshot_repository_import_state(root, {local})
    sys.modules[resembling] = _module(resembling, Path(os.__file__))
    try:
        state.assert_restored()
    finally:
        _restore_module(resembling, previous)


def test_unrelated_module_cannot_mask_repository_residue(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "harness"
    root.mkdir()
    outside.mkdir()
    local = "apg_cache_masked_local"
    unrelated = "apg_cache_masking_harness"
    prior_local = sys.modules.get(local, _ABSENT)
    prior_unrelated = sys.modules.get(unrelated, _ABSENT)
    state = snapshot_repository_import_state(root, {local})
    sys.modules[unrelated] = _module(unrelated, outside / "helper.py")
    sys.modules[local] = _module(local, root / "helper.py")
    try:
        with pytest.raises(RepositoryImportCacheError):
            state.assert_restored()
    finally:
        _restore_module(local, prior_local)
        _restore_module(unrelated, prior_unrelated)


def test_physical_path_rejects_lexical_prefix_near_misses(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "repository-near"
    root.mkdir()
    outside.mkdir()
    name = "apg_cache_prefix_near_miss"
    previous_module = sys.modules.get(name, _ABSENT)
    cache_key = str(outside)
    previous_cache = sys.path_importer_cache.get(cache_key, _ABSENT)
    state = snapshot_repository_import_state(root, set())
    sys.modules[name] = _module(name, outside / "helper.py")
    sys.path_importer_cache[cache_key] = object()
    try:
        state.assert_restored()
    finally:
        _restore_module(name, previous_module)
        if previous_cache is _ABSENT:
            sys.path_importer_cache.pop(cache_key, None)
        else:
            sys.path_importer_cache[cache_key] = previous_cache


def test_snapshot_checks_namespace_package_search_locations(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    package = root / "package"
    package.mkdir(parents=True)
    name = "apg_cache_namespace"
    previous = sys.modules.get(name, _ABSENT)
    state = snapshot_repository_import_state(root, {name})
    module = ModuleType(name)
    spec = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    spec.submodule_search_locations = [str(package)]
    module.__spec__ = spec
    module.__path__ = [str(package)]
    sys.modules[name] = module
    try:
        with pytest.raises(RepositoryImportCacheError):
            state.assert_restored()
    finally:
        _restore_module(name, previous)
