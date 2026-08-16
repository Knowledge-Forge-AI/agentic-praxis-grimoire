"""Integration contracts for the maintainer-supplied flat skill projection command."""

from __future__ import annotations

from pathlib import Path
import subprocess

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "flatten-skill-symlinks"


def run_command(*arguments: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(COMMAND), *(str(argument) for argument in arguments)],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def add_skill(root: Path, relative: str, body: str = "# Skill\n") -> Path:
    skill = root / relative
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    return skill


def source_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_help_and_usage_are_bounded() -> None:
    help_result = run_command("--help")
    assert help_result.returncode == 0
    assert "usage: flatten-skill-symlinks" in help_result.stdout
    assert help_result.stderr == ""

    usage_result = run_command()
    assert usage_result.returncode == 2
    assert "usage: flatten-skill-symlinks" in usage_result.stderr


def test_fresh_projection_and_idempotent_rerun_preserve_sources(
    tmp_path: Path,
) -> None:
    source = tmp_path / "shared skills"
    first = add_skill(source, "general/alpha")
    second = add_skill(source, "nested/βeta")
    output = tmp_path / "Claude skills"
    before = source_snapshot(source)

    created = run_command(source, output, "--clean")
    assert created.returncode == 0, created.stderr
    assert (output / "alpha").resolve() == first.resolve()
    assert (output / "βeta").resolve() == second.resolve()
    assert "2 created" in created.stdout
    assert source_snapshot(source) == before

    repeated = run_command(source, output)
    assert repeated.returncode == 0, repeated.stderr
    assert "0 created" in repeated.stdout
    assert "2 unchanged" in repeated.stdout
    assert source_snapshot(source) == before


def test_duplicate_names_fail_before_mutation_and_relative_mode_is_deterministic(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    add_skill(source, "one/shared")
    add_skill(source, "two/shared")
    output = tmp_path / "output"

    collision = run_command(source, output)
    assert collision.returncode == 2
    assert "Duplicate flat skill names" in collision.stderr
    assert not output.exists()

    relative = run_command(source, output, "--on-collision", "relative")
    assert relative.returncode == 0, relative.stderr
    assert sorted(path.name for path in output.iterdir() if path.is_symlink()) == [
        "one__shared",
        "two__shared",
    ]


def test_source_destination_overlap_is_refused_in_both_directions(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    add_skill(source, "skill")
    nested_output = source / "projection"
    nested = run_command(source, nested_output)
    assert nested.returncode == 2
    assert "overlap" in nested.stderr.lower()
    assert not nested_output.exists()

    outer_output = tmp_path / "outer"
    nested_source = outer_output / "source"
    add_skill(nested_source, "skill")
    outer = run_command(nested_source, outer_output)
    assert outer.returncode == 2
    assert "overlap" in outer.stderr.lower()


def test_symlinked_output_ancestor_is_refused(tmp_path: Path) -> None:
    source = tmp_path / "source"
    add_skill(source, "skill")
    redirected = tmp_path / "redirected"
    redirected.mkdir()
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(redirected, target_is_directory=True)

    result = run_command(source, linked_parent / "output")
    assert result.returncode == 2
    assert "symlink ancestor" in result.stderr.lower()
    assert not (redirected / "output").exists()


def test_unmanaged_collisions_are_never_overwritten(tmp_path: Path) -> None:
    source = tmp_path / "source"
    add_skill(source, "skill")
    output = tmp_path / "output"
    output.mkdir()
    unmanaged_file = output / "skill"
    unmanaged_file.write_text("unmanaged\n", encoding="utf-8")
    result = run_command(source, output, "--replace")
    assert result.returncode == 2
    assert unmanaged_file.read_text(encoding="utf-8") == "unmanaged\n"

    unmanaged_file.unlink()
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (output / "skill").symlink_to(unrelated, target_is_directory=True)
    result = run_command(source, output, "--replace")
    assert result.returncode == 2
    assert "unmanaged" in result.stderr.lower()
    assert (output / "skill").resolve() == unrelated.resolve()

    (output / "skill").unlink()
    (output / "skill").symlink_to(source / "skill", target_is_directory=True)
    result = run_command(source, output)
    assert result.returncode == 2
    assert "never adopted" in result.stderr.lower()


def test_clean_removes_only_stale_managed_links_and_dry_run_is_stable(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    retained = add_skill(source, "retained")
    stale_target = add_skill(source, "removed")
    output = tmp_path / "output"
    initial = run_command(source, output)
    assert initial.returncode == 0, initial.stderr
    (stale_target / "SKILL.md").unlink()

    unmanaged_target = source / "manual"
    unmanaged_target.mkdir()
    (output / "manual").symlink_to(unmanaged_target, target_is_directory=True)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (output / "unrelated").symlink_to(unrelated, target_is_directory=True)

    check = run_command(source, output, "--check")
    assert check.returncode == 1
    assert "CHECK:" in check.stdout
    assert (output / "removed").is_symlink()

    first_dry_run = run_command(source, output, "--clean", "--dry-run")
    second_dry_run = run_command(source, output, "--clean", "--dry-run")
    assert first_dry_run.returncode == second_dry_run.returncode == 0
    assert first_dry_run.stdout == second_dry_run.stdout
    assert (output / "removed").is_symlink()
    assert (output / "retained").resolve() == retained.resolve()

    applied = run_command(source, output, "--clean")
    assert applied.returncode == 0, applied.stderr
    assert not (output / "removed").exists()
    assert (output / "manual").resolve() == unmanaged_target.resolve()
    assert (output / "unrelated").resolve() == unrelated.resolve()
    assert (output / "retained").resolve() == retained.resolve()


def test_check_and_clean_handle_last_removed_skill_and_metadata_names(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    only = add_skill(source, "only")
    output = tmp_path / "output"
    assert run_command(source, output).returncode == 0
    (only / "SKILL.md").unlink()
    assert run_command(source, output, "--check").returncode == 1
    assert run_command(source, output, "--clean").returncode == 0
    assert not (output / "only").exists()

    for reserved in (
        ".flatten-skill-symlinks-state.json",
        ".flatten-skill-symlinks.lock",
    ):
        reserved_source = tmp_path / reserved.replace(".", "_")
        add_skill(reserved_source, reserved)
        result = run_command(reserved_source, tmp_path / f"out-{reserved_source.name}")
        assert result.returncode == 2
        assert "reserved" in result.stderr.lower()


def test_state_owned_link_can_be_replaced_and_check_is_read_only(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    old = add_skill(source, "old/shared")
    output = tmp_path / "output"
    assert run_command(source, output).returncode == 0
    (old / "SKILL.md").unlink()
    new = add_skill(source, "new/shared")

    refused = run_command(source, output, "--clean")
    assert refused.returncode == 2
    assert "use --replace" in refused.stderr

    check = run_command(source, output, "--replace", "--clean", "--check")
    assert check.returncode == 1
    assert "CHECK:" in check.stdout
    assert (output / "shared").resolve() == old.resolve()

    replaced = run_command(source, output, "--replace", "--clean")
    assert replaced.returncode == 0, replaced.stderr
    assert (output / "shared").resolve() == new.resolve()
    assert run_command(source, output, "--check").returncode == 0


def test_existing_destination_lock_blocks_mutation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    add_skill(source, "skill")
    output = tmp_path / "output"
    output.mkdir()
    (output / ".flatten-skill-symlinks.lock").mkdir()
    result = run_command(source, output)
    assert result.returncode == 2
    assert "already active" in result.stderr
    assert not (output / "skill").exists()


def test_custom_marker_exclusions_absolute_links_and_quiet_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    custom = source / "custom"
    custom.mkdir(parents=True)
    (custom / "OWNER.md").write_text("# Custom\n", encoding="utf-8")
    add_skill(source, "ignored/skill")
    add_skill(source, "node_modules/dependency")
    output = tmp_path / "output"
    result = run_command(
        source,
        output,
        "--marker",
        "OWNER.md",
        "--exclude",
        "ignored/**",
        "--absolute",
        "--quiet",
    )
    assert result.returncode == 0, result.stderr
    assert (output / "custom").is_symlink()
    assert Path((output / "custom").readlink()).is_absolute()
    assert "CREATE" not in result.stdout
    assert "DONE:" in result.stdout
    assert not (output / "skill").exists()
    assert not (output / "dependency").exists()


def test_invalid_option_combinations_output_shape_and_changed_state_fail(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    skill = add_skill(source, "skill")
    output_file = tmp_path / "output-file"
    output_file.write_text("file\n", encoding="utf-8")
    shaped = run_command(source, output_file)
    assert shaped.returncode == 2
    assert "not a directory" in shaped.stderr

    for arguments in (
        ("--check", "--dry-run"),
        ("--marker", "../bad"),
        ("--separator", "/"),
    ):
        result = run_command(source, tmp_path / "output", *arguments)
        assert result.returncode == 2

    output = tmp_path / "managed"
    assert run_command(source, output).returncode == 0
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    (output / "skill").unlink()
    (output / "skill").symlink_to(replacement, target_is_directory=True)
    changed = run_command(source, output, "--clean", "--replace")
    assert changed.returncode == 2
    assert "changed" in changed.stderr.lower()
    assert skill.exists()


def test_additional_discovery_collision_and_stale_state_refusals(
    tmp_path: Path,
) -> None:
    input_file = tmp_path / "input-file"
    input_file.write_text("not a directory\n", encoding="utf-8")
    assert run_command(input_file, tmp_path / "output").returncode == 2

    empty = tmp_path / "empty"
    empty.mkdir()
    empty_result = run_command(empty, tmp_path / "empty-output")
    assert empty_result.returncode == 2
    assert "No skill" in empty_result.stderr

    source = tmp_path / "source"
    external = add_skill(tmp_path / "external", "linked")
    source.mkdir()
    (source / "linked").symlink_to(external, target_is_directory=True)
    assert run_command(source, tmp_path / "linked-output").returncode == 2

    colliding = tmp_path / "colliding"
    add_skill(colliding, "a__b/shared")
    add_skill(colliding, "a/b/shared")
    unresolved = run_command(
        colliding,
        tmp_path / "collision-output",
        "--on-collision",
        "relative",
    )
    assert unresolved.returncode == 2
    assert "still collide" in unresolved.stderr

    managed_source = tmp_path / "managed-source"
    stale = add_skill(managed_source, "stale")
    add_skill(managed_source, "live")
    output = tmp_path / "managed-output"
    assert run_command(managed_source, output).returncode == 0
    (stale / "SKILL.md").unlink()
    (output / "stale").unlink()
    missing = run_command(managed_source, output, "--clean")
    assert missing.returncode == 0, missing.stderr

    retained = add_skill(managed_source, "retained")
    assert run_command(managed_source, output).returncode == 0
    add_skill(managed_source, "survivor")
    assert run_command(managed_source, output).returncode == 0
    (retained / "SKILL.md").unlink()
    (output / "retained").unlink()
    (output / "retained").write_text("changed\n", encoding="utf-8")
    changed = run_command(managed_source, output, "--clean")
    assert changed.returncode == 2
