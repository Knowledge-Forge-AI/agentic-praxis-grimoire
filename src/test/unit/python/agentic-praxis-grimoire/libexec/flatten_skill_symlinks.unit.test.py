"""Unit contracts for skill projection owner state and rollback."""

from __future__ import annotations

from pathlib import Path
import stat
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import flatten_skill_symlinks as projection  # noqa: E402
import skill_projection_state as state  # noqa: E402


def add_skill(root: Path, relative: str) -> Path:
    skill = root / relative
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    return skill.resolve()


def test_state_round_trip_is_canonical_private_and_source_bound(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    skill = add_skill(source, "skill")
    output = tmp_path / "output"
    output.mkdir()
    state.write_state(output, source.resolve(), {"skill": str(skill)})
    loaded = state.load_state(output, source.resolve())
    assert loaded is not None and loaded.links == {"skill": str(skill)}
    state_path = output / state.STATE_NAME
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600
    assert state_path.stat().st_nlink == 1
    with pytest.raises(state.StateError, match="different input"):
        state.load_state(output, tmp_path.resolve())


def test_state_rejects_symlink_and_open_schema(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    unsafe = output / state.STATE_NAME
    target = tmp_path / "target"
    target.write_text("{}\n", encoding="utf-8")
    unsafe.symlink_to(target)
    with pytest.raises(state.StateError, match="unsafe"):
        state.load_state(output, source.resolve())
    unsafe.unlink()
    unsafe.write_text('{"schema_version":1,"unknown":true}\n', encoding="utf-8")
    unsafe.chmod(0o600)
    with pytest.raises(state.StateError, match="closed"):
        state.load_state(output, source.resolve())


def test_state_create_does_not_overwrite_intervening_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    destination = output / state.STATE_NAME
    original_link = state.os.link

    def race(source_path: Path, target: Path, *, follow_symlinks: bool) -> None:
        destination.write_text("unmanaged\n", encoding="utf-8")
        original_link(source_path, target, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(state.os, "link", race)
    with pytest.raises(FileExistsError):
        state.write_state(output, source.resolve(), {})
    assert destination.read_text(encoding="utf-8") == "unmanaged\n"


def test_lock_is_exclusive_and_removed(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    with state.projection_lock(output):
        with pytest.raises(state.StateError, match="already active"):
            with state.projection_lock(output):
                pass
    assert not (output / state.LOCK_NAME).exists()


def test_marker_must_be_a_direct_regular_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    external = tmp_path / "external"
    external.write_text("# External\n", encoding="utf-8")
    skill = source / "linked-marker"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").symlink_to(external)
    assert projection.discover_skills(source, "SKILL.md", [], True) == []


def test_state_write_failure_rolls_back_created_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    add_skill(source, "skill")
    output = tmp_path / "output"
    output.mkdir()
    arguments = projection.parse_args([str(source), str(output)])
    plan = projection.build_plan(arguments)

    def fail_state(*_arguments: object) -> None:
        raise OSError("injected state failure")

    monkeypatch.setattr(projection, "write_state", fail_state)
    with pytest.raises(OSError, match="injected"):
        projection.apply_plan(plan, arguments)
    assert not (output / "skill").exists()
    assert not (output / state.STATE_NAME).exists()


def test_collision_relative_exclusion_and_component_validation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    first = add_skill(source, "one/shared")
    second = add_skill(source, "two/shared")
    skills = projection.discover_skills(source, "SKILL.md", ["ignored/**"], True)
    with pytest.raises(projection.ProjectionError, match="Duplicate"):
        projection.assign_link_names(skills, source, "error", "__")
    assigned = projection.assign_link_names(skills, source, "relative", "__")
    assert [item.link_name for item in assigned] == ["one__shared", "two__shared"]
    assert {item.source for item in assigned} == {first, second}
    with pytest.raises(projection.ProjectionError, match="component"):
        projection.validate_component("../bad", "value")


def test_root_overlap_symlink_ancestor_and_empty_discovery_fail(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(projection.ProjectionError, match="overlap"):
        projection.resolve_roots(source, source / "output")
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)
    with pytest.raises(projection.ProjectionError, match="symlink ancestor"):
        projection.resolve_roots(source, linked / "output")
    args = projection.parse_args([str(source), str(tmp_path / "output")])
    with pytest.raises(projection.ProjectionError, match="No skill"):
        projection.build_plan(args)


def test_unmanaged_and_changed_owned_outputs_are_refused(tmp_path: Path) -> None:
    source = tmp_path / "source"
    skill = add_skill(source, "skill")
    output = tmp_path / "output"
    output.mkdir()
    destination = output / "skill"
    destination.symlink_to(skill)
    discovered = [projection.Skill(skill, Path("skill"), "skill")]
    with pytest.raises(projection.ProjectionError, match="unmanaged"):
        projection.preflight_output(discovered, output, source.resolve(), False, None)
    destination.unlink()
    destination.write_text("unmanaged\n", encoding="utf-8")
    with pytest.raises(projection.ProjectionError, match="regular"):
        projection.preflight_output(discovered, output, source.resolve(), False, None)


def test_check_dry_run_replace_and_owned_clean_paths(tmp_path: Path) -> None:
    source = tmp_path / "source"
    old = add_skill(source, "old")
    new = add_skill(source, "new")
    output = tmp_path / "output"
    output.mkdir()
    (output / "old").symlink_to(old)
    state.write_state(output, source.resolve(), {"old": str(old)})
    args = projection.parse_args(
        [str(source), str(output), "--clean", "--check"]
    )
    plan = projection.build_plan(args)
    assert projection.apply_plan(plan, args) == 1
    assert (output / "old").is_symlink()

    old_marker = old / "SKILL.md"
    old_marker.unlink()
    check = projection.parse_args([str(source), str(output), "--check"])
    check_plan = projection.build_plan(check)
    assert [item.name for item in check_plan.stale] == ["old"]
    assert projection.apply_plan(check_plan, check) == 1
    assert (output / "old").is_symlink()

    dry = projection.parse_args(
        [str(source), str(output), "--clean", "--dry-run"]
    )
    dry_plan = projection.build_plan(dry)
    assert [item.name for item in dry_plan.stale] == ["old"]
    assert projection.apply_plan(dry_plan, dry) == 0
    assert (output / "old").is_symlink()

    apply = projection.parse_args([str(source), str(output), "--clean"])
    assert projection.apply_projection(apply) == 0
    assert not (output / "old").exists()
    assert (output / "new").is_symlink()


def test_link_snapshot_atomic_rollback_and_main_error_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    source = tmp_path / "source"
    source.mkdir()
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    link = output / "link"
    projection.atomic_symlink(link, str(source))
    identity, target = projection.link_snapshot(link)
    projection.require_link_snapshot(link, identity, target)
    with pytest.raises(projection.ProjectionError, match="expected a symlink"):
        projection.link_snapshot(source)

    created = output / "created"
    created_identity = projection.atomic_symlink(created, str(source))
    removed = output / "removed"
    removed.symlink_to(source)
    removed_identity, removed_target = projection.link_snapshot(removed)
    removed_backup = projection.quarantine_link(
        removed, removed_identity, removed_target
    )
    old_identity, old_target = projection.link_snapshot(link)
    replaced_backup = projection.quarantine_link(link, old_identity, old_target)
    new_identity = projection.atomic_symlink(link, str(replacement))
    projection.rollback_changes(
        [
            projection.AppliedChange(
                "removed",
                removed,
                removed_target,
                None,
                backup=removed_backup,
            ),
            projection.AppliedChange(
                "created",
                created,
                None,
                str(source),
                new_identity=created_identity,
            ),
            projection.AppliedChange(
                "replaced",
                link,
                old_target,
                str(replacement),
                new_identity,
                replaced_backup,
            ),
        ]
    )
    assert not created.exists()
    assert removed.is_symlink()
    assert link.resolve() == source.resolve()
    monkeypatch.setattr(
        projection,
        "apply_projection",
        lambda _args: (_ for _ in ()).throw(projection.ProjectionError("bounded")),
    )
    assert projection.main([str(source), str(output)]) == 2


def test_atomic_create_never_overwrites_intervening_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "skill"
    unmanaged = tmp_path / "unmanaged"
    unmanaged.mkdir()
    original_link = projection.os.link

    def race(source: Path, target: Path, *, follow_symlinks: bool) -> None:
        destination.symlink_to(unmanaged)
        original_link(source, target, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(projection.os, "link", race)
    with pytest.raises(FileExistsError):
        projection.atomic_symlink(destination, str(tmp_path / "source"))
    assert destination.resolve() == unmanaged.resolve()
