"""Integration boundaries for repository and destination inventory."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import global_skills_inventory as inventory  # noqa: E402


def test_environment_and_repository_path_refusals(tmp_path: Path) -> None:
    with pytest.raises(inventory.InventoryError, match="absolute"):
        inventory.destination_for("codex", Path("relative"), {})
    with pytest.raises(inventory.InventoryError, match="unsupported"):
        inventory.destination_for("other", None, {"HOME": str(tmp_path)})
    with pytest.raises(inventory.InventoryError, match="CLAUDE_CONFIG_DIR"):
        inventory.destination_for(
            "claude",
            None,
            {"HOME": str(tmp_path), "CLAUDE_CONFIG_DIR": "relative"},
        )
    with pytest.raises(inventory.InventoryError, match="LOCAL_PROJ_INSTALL"):
        inventory.apg_repository(
            None, {"HOME": str(tmp_path), "LOCAL_PROJ_INSTALL": "relative"}
        )
    with pytest.raises(inventory.InventoryError, match="requires --include"):
        inventory.source_values(
            (tmp_path / "source",),
            False,
            tmp_path / "apg",
            {"HOME": str(tmp_path)},
        )

    with pytest.raises(inventory.InventoryError, match="unavailable"):
        inventory.resolve_repository(tmp_path / "missing")
    regular = tmp_path / "regular"
    regular.write_text("unsafe", encoding="utf-8")
    with pytest.raises(inventory.InventoryError, match="not a directory"):
        inventory.resolve_repository(regular)
    repository = tmp_path / "repository"
    repository.mkdir()
    with pytest.raises(inventory.InventoryError, match="requires a skills"):
        inventory.resolve_repository(repository)
    (repository / "skills").write_text("unsafe", encoding="utf-8")
    with pytest.raises(inventory.InventoryError, match="skills path is unsafe"):
        inventory.resolve_repository(repository)


def test_indirect_only_repository_has_no_installable_inventory(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill = repository / "skills" / "skill"
    skill.mkdir(parents=True)
    marker = tmp_path / "marker"
    marker.write_text("# Indirect\n", encoding="utf-8")
    (skill / "SKILL.md").symlink_to(marker)

    assert inventory.discover_repository(repository) == ()
    with pytest.raises(inventory.InventoryError, match="no direct regular"):
        inventory.build_inventory((repository,), tmp_path / "destination")
