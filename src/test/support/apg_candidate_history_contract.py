"""Repository-resident public and publication-excluded history closure."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any, NoReturn

from apg_candidate_surface_contract import SurfaceContractError
from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)


HISTORY_CLASSES = {"historical-evidence", "publication-excluded-history"}
HISTORICAL_COMMITS = {
    "APG58": "7934d3a936d22f26c0533d46b5e9b603de516034",
    "APG59": "133166a4d084ba5d347b133054e4dda515add63f",
}


def fail(owner_id: str, message: str) -> NoReturn:
    raise SurfaceContractError(f"{owner_id}: {message}")


def _direct_regular_history(
    root: Path, path: Path, owner_id: str
) -> None:
    try:
        relative = path.relative_to(root).as_posix()
        with RepositoryPathContract(root) as repository:
            text = repository.read_text(relative)
    except (
        OSError,
        UnicodeError,
        ValueError,
        RepositoryPathError,
    ) as error:
        fail(owner_id, f"historical evidence is unreadable: {error}")
    if not text.strip():
        fail(owner_id, "historical evidence is an empty placeholder")


def _paths(root: Path, entry: dict[str, Any]) -> list[Path]:
    owner_id = entry["owner_id"]
    try:
        with RepositoryPathContract(root) as repository:
            if "path_pattern" in entry:
                return [
                    root / relative
                    for relative in repository.glob_regular_files(
                        entry["path_pattern"]
                    )
                ]
            relative = entry["path"]
            return (
                [root / relative]
                if repository.entry_kind(relative) is not None
                else []
            )
    except RepositoryPathError as error:
        fail(owner_id, f"historical repository path is not direct: {error}")


def _assert_path_entry(root: Path, entry: dict[str, Any]) -> None:
    owner_id = entry["owner_id"]
    paths = _paths(root, entry)
    if not paths:
        fail(owner_id, "repository-resident historical evidence is missing")
    for path in paths:
        _direct_regular_history(root, path, owner_id)


def _assert_git_objects(root: Path, locator: str, owner_id: str) -> None:
    if (root / ".git").exists():
        revisions = (
            ("APG58", "APG59") if "[89]" in locator else (locator,)
        )
        for revision in revisions:
            object_name = HISTORICAL_COMMITS.get(revision, revision)
            result = subprocess.run(
                ["git", "cat-file", "-e", f"{object_name}^{{commit}}"],
                cwd=root,
                check=False,
                capture_output=True,
            )
            if result.returncode != 0:
                fail(owner_id, f"historical Git object is missing: {revision}")
        return
    virtual = root / ".apg-virtual"
    if not virtual.is_dir() or not any(virtual.iterdir()):
        fail(owner_id, "synthetic historical Git-object evidence is missing")


def assert_plan_history(root: Path, plan: dict[str, Any]) -> None:
    """Require every repository-resident history owner in the removal plan."""
    for owner in plan["owners"]:
        owner_class = owner["surface_class"]
        if owner_class not in HISTORY_CLASSES:
            continue
        locator = owner.get("path", owner.get("path_pattern"))
        if locator.startswith("git-object:"):
            _assert_git_objects(
                root, locator.removeprefix("git-object:"), owner["owner_id"]
            )
        else:
            _assert_path_entry(root, owner)
