"""Bounded parent-process state checks for repository-import isolation."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import Iterable


_MODULE_NAME = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*\Z"
)


class RepositoryImportCacheError(AssertionError):
    """Relevant parent-process import state was not restored."""


def _resolved_path(value: object) -> Path | None:
    try:
        return Path(os.fspath(value)).resolve(strict=False)
    except (OSError, RuntimeError, TypeError, ValueError):
        return None


def _within(root: Path, value: object) -> bool:
    resolved = _resolved_path(value)
    return resolved is not None and resolved.is_relative_to(root)


def _module_paths(module: object) -> tuple[object, ...]:
    values: list[object] = []
    direct = getattr(module, "__file__", None)
    if direct is not None:
        values.append(direct)
    spec = getattr(module, "__spec__", None)
    origin = getattr(spec, "origin", None)
    if origin not in (None, "built-in", "frozen"):
        values.append(origin)
    locations = getattr(spec, "submodule_search_locations", None)
    if locations is not None:
        values.extend(locations)
    package_path = getattr(module, "__path__", None)
    if package_path is not None:
        values.extend(package_path)
    return tuple(values)


def _module_within(root: Path, module: object) -> bool:
    return any(_within(root, value) for value in _module_paths(module))


def _relevant_importer_entries(root: Path) -> tuple[tuple[str, object], ...]:
    return tuple(
        sorted(
            (
                (key, importer)
                for key, importer in sys.path_importer_cache.items()
                if _within(root, key)
            ),
            key=lambda item: item[0],
        )
    )


@dataclass(frozen=True, slots=True)
class RepositoryImportState:
    """One relevant parent-state snapshot for an inspected repository root."""

    root: Path
    local_names: frozenset[str]
    module_entries: tuple[tuple[str, object], ...]
    absent_local_names: frozenset[str]
    parent_path: tuple[str, ...]
    importer_entries: tuple[tuple[str, object], ...]

    def assert_restored(self) -> None:
        """Reject relevant residue without claiming global-cache equality."""

        if tuple(sys.path) != self.parent_path:
            raise RepositoryImportCacheError("parent search path was not restored")
        before_modules = dict(self.module_entries)
        for name, module in self.module_entries:
            if name not in sys.modules or sys.modules[name] is not module:
                raise RepositoryImportCacheError(
                    "pre-existing relevant module entry was not restored"
                )
        if any(name in sys.modules for name in self.absent_local_names):
            raise RepositoryImportCacheError("new relevant module entry survived")
        for name, module in tuple(sys.modules.items()):
            if _module_within(self.root, module) and before_modules.get(name) is not module:
                raise RepositoryImportCacheError(
                    "module from the inspected repository survived"
                )
        current_importers = _relevant_importer_entries(self.root)
        if len(current_importers) != len(self.importer_entries) or any(
            current_key != before_key or current is not before
            for (current_key, current), (before_key, before) in zip(
                current_importers,
                self.importer_entries,
                strict=True,
            )
        ):
            raise RepositoryImportCacheError(
                "inspected-repository importer cache was not restored"
            )


def snapshot_repository_import_state(
    root: Path,
    local_module_names: Iterable[str],
) -> RepositoryImportState:
    """Capture only state relevant to one inspected repository."""

    physical_root = root.resolve(strict=True)
    if not physical_root.is_dir():
        raise RepositoryImportCacheError("inspected repository root is not a directory")
    names = frozenset(local_module_names)
    if any(not isinstance(name, str) or _MODULE_NAME.fullmatch(name) is None for name in names):
        raise RepositoryImportCacheError("relevant module name is invalid")
    module_entries = tuple(
        sorted(
            (
                (name, module)
                for name, module in sys.modules.items()
                if name in names or _module_within(physical_root, module)
            ),
            key=lambda item: item[0],
        )
    )
    present_names = frozenset(name for name, _ in module_entries)
    return RepositoryImportState(
        root=physical_root,
        local_names=names,
        module_entries=module_entries,
        absent_local_names=names - present_names,
        parent_path=tuple(sys.path),
        importer_entries=_relevant_importer_entries(physical_root),
    )
