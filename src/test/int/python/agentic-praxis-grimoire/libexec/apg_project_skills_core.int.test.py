"""Real filesystem contracts for libexec/apg_project_skills_core.py."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat

import pytest

from libexec import apg_project_skills_core as project_core
from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)


def test_atomic_replace_restore_and_inode_identity(tmp_path: Path) -> None:
    path = tmp_path / "state"
    project_core.atomic_replace(path, b"first", 0o600)
    assert path.read_bytes() == b"first"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    descriptor = os.open(path, os.O_RDONLY)
    try:
        assert project_core.inode_matches(path, descriptor)
        project_core.atomic_replace(path, b"second", 0o640)
        assert not project_core.inode_matches(path, descriptor)
    finally:
        os.close(descriptor)
    project_core.restore_snapshot(
        path,
        project_core.FileSnapshot(True, b"restored", 0o600),
    )
    assert path.read_bytes() == b"restored"
    project_core.restore_snapshot(
        path,
        project_core.FileSnapshot(False, b"", 0o600),
    )
    assert not path.exists()


def test_mutation_lock_tracks_placeholder_and_written_inode(tmp_path: Path) -> None:
    path = tmp_path / "state"
    with project_core.mutation_lock(path) as (descriptor, created):
        assert created
        assert project_core.inode_matches(path, descriptor)
    assert not path.exists()
    with project_core.mutation_lock(path) as (descriptor, created):
        assert created
        os.write(descriptor, b"state")
    assert path.read_bytes() == b"state"
    with project_core.mutation_lock(path) as (_descriptor, created):
        assert not created


def test_projection_links_use_exact_real_filesystem_targets(tmp_path: Path) -> None:
    repository = project_core.TargetRepository(
        tmp_path,
        tmp_path / "state",
        tmp_path / "exclude",
    )
    project_core.create_projection_parents(repository)
    skill = project_core.EXPECTED_SKILLS[0]
    canonical_leaf = tmp_path / "canonical" / skill
    canonical_leaf.mkdir(parents=True)
    (canonical_leaf / "SKILL.md").write_text(
        f"---\nname: {skill}\n---\n",
        encoding="utf-8",
    )
    canonical = {skill: canonical_leaf.resolve()}
    link = project_core.projection_path(repository, skill)
    link.symlink_to(canonical_leaf, target_is_directory=True)
    project_core.require_exact_link(
        repository,
        canonical,
        skill,
        missing_context="managed",
    )
    link.unlink()
    link.write_text("conflict\n", encoding="utf-8")
    with pytest.raises(project_core.ToolError, match="not a symbolic link"):
        project_core.require_exact_link(
            repository,
            canonical,
            skill,
            missing_context="managed",
        )


def test_real_state_files_enforce_type_size_mode_and_identity(tmp_path: Path) -> None:
    apg_root = tmp_path / "apg"
    target_root = tmp_path / "target"
    apg_root.mkdir()
    target_root.mkdir()
    state = project_core.LocalState(
        str(apg_root),
        str(target_root),
        (project_core.EXPECTED_SKILLS[0],),
        (),
        False,
    )
    path = tmp_path / "state.json"
    assert not project_core.regular_file_bytes(
        path,
        maximum=100,
        label="state",
    ).existed
    path.write_bytes(project_core.serialize_state(state))
    path.chmod(0o600)
    assert project_core.read_state(path, apg_root, target_root) == state
    path.chmod(0o644)
    with pytest.raises(project_core.ToolError, match="permissions"):
        project_core.read_state(path, apg_root, target_root)
    path.unlink()
    path.mkdir()
    with pytest.raises(project_core.ToolError, match="ordinary file"):
        project_core.regular_file_bytes(path, maximum=100, label="state")
    path.rmdir()
    path.write_bytes(b"x" * 101)
    with pytest.raises(project_core.ToolError, match="oversized"):
        project_core.regular_file_bytes(path, maximum=100, label="state")


def test_real_canonical_tree_rejects_leaf_file_and_name_drift(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    skills.mkdir()
    repository_skills = REPOSITORY_ROOT / "skills"
    for source_leaf in project_core._canonical_leaf_paths(repository_skills):
        relative_leaf = source_leaf.relative_to(repository_skills)
        shutil.copytree(
            source_leaf,
            skills / relative_leaf,
            symlinks=True,
        )
    canonical = project_core.canonical_skills(tmp_path)
    assert tuple(sorted(canonical)) == project_core.EXPECTED_SKILLS

    extra = skills / "extra-skill"
    extra.mkdir()
    (extra / "SKILL.md").write_text(
        "---\nname: extra-skill\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(project_core.ToolError, match="skill set differs"):
        project_core.canonical_skills(tmp_path)
    shutil.rmtree(extra)

    skill = project_core.EXPECTED_SKILLS[0]
    leaf = skills / skill
    saved = tmp_path / "saved-leaf"
    leaf.rename(saved)
    leaf.symlink_to(saved, target_is_directory=True)
    with pytest.raises(project_core.ToolError, match="unsupported owner or depth"):
        project_core.canonical_skills(tmp_path)
    leaf.unlink()
    saved.rename(leaf)

    skill_file = leaf / "SKILL.md"
    original = skill_file.read_bytes()
    skill_file.unlink()
    skill_file.symlink_to(skills / "README.md")
    with pytest.raises(project_core.ToolError, match="unsupported owner or depth"):
        project_core.canonical_skills(tmp_path)
    skill_file.unlink()
    skill_file.write_bytes(original)
    skill_file.write_text(
        "---\nname: different-skill\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(project_core.ToolError, match="identity is duplicated or disagrees"):
        project_core.canonical_skills(tmp_path)


def test_real_git_target_tracking_and_status_boundaries(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    project_core.run_git(tmp_path, ["init", "-q", str(repository_root)])
    nested = repository_root / "nested"
    nested.mkdir()
    target = project_core.resolve_target(str(nested))
    assert target.root == repository_root.resolve()
    assert not project_core.is_tracked(target, project_core.EXPECTED_SKILLS[0])
    assert project_core.managed_status(target, ()) == ""

    projection = project_core.projection_path(target, project_core.EXPECTED_SKILLS[0])
    projection.parent.mkdir(parents=True)
    projection.write_text("tracked\n", encoding="utf-8")
    project_core.run_git(
        repository_root,
        ["add", str(projection.relative_to(repository_root))],
    )
    assert project_core.is_tracked(target, project_core.EXPECTED_SKILLS[0])
    assert project_core.managed_status(target, (project_core.EXPECTED_SKILLS[0],))
    with pytest.raises(project_core.ToolError, match="not inside a Git worktree"):
        project_core.resolve_target(str(tmp_path / "outside"))


def test_projection_link_and_parent_failures_use_real_filesystem_shapes(
    tmp_path: Path,
) -> None:
    target = project_core.TargetRepository(tmp_path, tmp_path / "state", tmp_path / "exclude")
    project_core.create_projection_parents(target)
    skill = project_core.EXPECTED_SKILLS[0]
    canonical_leaf = tmp_path / "canonical" / skill
    canonical_leaf.mkdir(parents=True)
    (canonical_leaf / "SKILL.md").write_text(
        f"---\nname: {skill}\n---\n",
        encoding="utf-8",
    )
    canonical = {skill: canonical_leaf.resolve()}
    projection = project_core.projection_path(target, skill)
    with pytest.raises(project_core.ToolError, match="missing"):
        project_core.require_exact_link(target, canonical, skill, missing_context="managed")
    projection.symlink_to(tmp_path / "absent", target_is_directory=True)
    with pytest.raises(project_core.ToolError, match="broken"):
        project_core.require_exact_link(target, canonical, skill, missing_context="managed")
    projection.unlink()
    different = tmp_path / "different"
    different.mkdir()
    (different / "SKILL.md").write_text(
        f"---\nname: {skill}\n---\n",
        encoding="utf-8",
    )
    projection.symlink_to(different, target_is_directory=True)
    with pytest.raises(project_core.ToolError, match="does not resolve"):
        project_core.require_exact_link(target, canonical, skill, missing_context="managed")
    projection.unlink()
    skills_parent = tmp_path / ".agents/skills"
    skills_parent.rmdir()
    skills_parent.write_text("unsafe\n", encoding="utf-8")
    with pytest.raises(project_core.ToolError, match="projection parent"):
        project_core.validate_projection_parents(target)
    with pytest.raises(project_core.ToolError, match="became unsafe"):
        project_core.create_projection_parents(target)


def test_real_skill_metadata_files_reject_malformed_frontmatter(tmp_path: Path) -> None:
    leaf = tmp_path / "example-skill"
    leaf.mkdir()
    skill_file = leaf / "SKILL.md"
    for content, message in (
        (b"", "frontmatter"),
        (b"---\nname: example-skill\n", "terminator"),
        (b"---\n---\n", "one valid name"),
        (b"---\nname: Bad Name\n---\n", "one valid name"),
        (b"\xff", "unreadable"),
    ):
        skill_file.write_bytes(content)
        with pytest.raises(project_core.ToolError, match=message):
            project_core.frontmatter_name(skill_file)
    skill_file.write_text(
        "---\nname: example-skill\n---\n",
        encoding="utf-8",
    )
    assert project_core.frontmatter_name(skill_file) == "example-skill"
