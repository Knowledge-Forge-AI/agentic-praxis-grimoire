"""Real rollback filesystem contracts for project-skill commands."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_project_skills_commands as commands  # noqa: E402
import apg_project_skills_core as core  # noqa: E402


def repository(root: Path) -> core.TargetRepository:
    return core.TargetRepository(root, root / "state", root / "exclude")


def test_install_rollback_restores_exclude_links_and_owned_containers(
    tmp_path: Path,
) -> None:
    target = repository(tmp_path)
    target.exclude_path.write_bytes(b"changed")
    skill = core.EXPECTED_SKILLS[0]
    canonical = tmp_path / "canonical" / skill
    canonical.mkdir(parents=True)
    projection = core.projection_path(target, skill)
    projection.parent.mkdir(parents=True)
    projection.symlink_to(canonical, target_is_directory=True)
    commands.rollback_install(
        target,
        {skill: canonical.resolve()},
        [skill],
        [".agents", ".agents/skills"],
        core.FileSnapshot(True, b"original", 0o644),
    )
    assert target.exclude_path.read_bytes() == b"original"
    assert not (tmp_path / ".agents").exists()


def test_install_rollback_reports_changed_link_and_unsafe_exclude(
    tmp_path: Path,
) -> None:
    target = repository(tmp_path)
    target.exclude_path.mkdir()
    skill = core.EXPECTED_SKILLS[0]
    canonical = tmp_path / "canonical" / skill
    canonical.mkdir(parents=True)
    projection = core.projection_path(target, skill)
    projection.parent.mkdir(parents=True)
    projection.write_text("changed\n", encoding="utf-8")
    with pytest.raises(core.ToolError, match="rollback was incomplete"):
        commands.rollback_install(
            target,
            {skill: canonical.resolve()},
            [skill],
            [".agents/skills"],
            core.FileSnapshot(False, b"", 0o644),
        )


def test_removed_links_and_containers_recreate_or_report_concurrent_drift(
    tmp_path: Path,
) -> None:
    target = repository(tmp_path)
    skill = core.EXPECTED_SKILLS[0]
    canonical = tmp_path / "canonical" / skill
    canonical.mkdir(parents=True)
    errors = commands.recreate_removed_links(
        target,
        {skill: canonical.resolve()},
        [skill],
        list(core.AUTHORIZED_CONTAINERS),
    )
    assert errors == []
    projection = core.projection_path(target, skill)
    assert projection.resolve() == canonical.resolve()

    projection.unlink()
    projection.write_text("changed\n", encoding="utf-8")
    errors = commands.recreate_removed_links(
        target,
        {skill: canonical.resolve()},
        [skill],
        [],
    )
    assert any("link changed concurrently" in error for error in errors)

    skills_container = tmp_path / ".agents/skills"
    projection.unlink()
    skills_container.rmdir()
    skills_container.write_text("changed\n", encoding="utf-8")
    errors = commands.recreate_removed_links(
        target,
        {skill: canonical.resolve()},
        [],
        [".agents/skills"],
    )
    assert any("container changed concurrently" in error for error in errors)
