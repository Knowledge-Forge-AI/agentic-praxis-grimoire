"""Create a safe flat symlink projection of a nested skill library."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
import fnmatch
import os
from pathlib import Path
import secrets
import stat
import sys

from skill_projection_state import (
    LOCK_NAME,
    ProjectionState,
    STATE_NAME,
    StateError,
    load_state,
    projection_lock,
    write_state,
)


DEFAULT_EXCLUDED_DIR_NAMES = frozenset(
    {".git", ".hg", ".svn", ".venv", "venv", "__pycache__", "node_modules"}
)


class ProjectionError(RuntimeError):
    """A safe, user-correctable projection failure."""


@dataclass(frozen=True, slots=True)
class Skill:
    source: Path
    relative_source: Path
    link_name: str = ""


@dataclass(frozen=True, slots=True)
class ProjectionPlan:
    input_root: Path
    output_root: Path
    skills: tuple[Skill, ...]
    stale: tuple[Path, ...]
    owned: dict[str, str]
    had_state: bool


@dataclass(frozen=True, slots=True)
class AppliedChange:
    kind: str
    destination: Path
    old_target: str | None
    new_target: str | None
    new_identity: tuple[int, int] | None = None
    backup: Path | None = None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="flatten-skill-symlinks",
        description=(
            "Recursively find skill folders and expose them as a flat set of "
            "symlinks in an output directory."
        ),
    )
    parser.add_argument("input", type=Path, help="Root of the nested skill tree")
    parser.add_argument("output", type=Path, help="Flat symlink output directory")
    parser.add_argument(
        "--marker",
        default="SKILL.md",
        help="File that identifies an individual skill directory (default: SKILL.md)",
    )
    parser.add_argument(
        "--on-collision",
        choices=("error", "relative"),
        default="error",
        help=(
            "How to handle duplicate skill-directory basenames. 'error' stops; "
            "'relative' prefixes colliding names with their relative path "
            "(default: error)."
        ),
    )
    parser.add_argument(
        "--separator",
        default="__",
        help="Separator used by --on-collision relative (default: __)",
    )
    parser.add_argument(
        "--absolute",
        action="store_true",
        help="Create absolute rather than relative symlink targets",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace a wrong managed symlink; unmanaged links are never replaced",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Remove stale output symlinks whose targets are under the input tree; "
            "unrelated symlinks and all regular files/directories are preserved"
        ),
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help=(
            "Exclude a relative directory path matching this POSIX-style glob; "
            "repeatable (example: --exclude 'fixtures/**')"
        ),
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="Do not automatically skip common metadata/cache directories",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned operations without changing the filesystem",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report whether the projection is current without changing it",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-link output; errors and the final summary remain",
    )
    return parser.parse_args(argv)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_component(value: str, label: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ProjectionError(f"{label} must be one safe path component")
    return value


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def reject_symlink_ancestors(path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if current.is_symlink():
            raise ProjectionError(f"Output has a symlink ancestor: {current}")
        if not current.exists():
            return


def resolve_roots(input_value: Path, output_value: Path) -> tuple[Path, Path]:
    input_root = input_value.expanduser().resolve(strict=True)
    if not input_root.is_dir():
        raise ProjectionError(f"Input is not a directory: {input_root}")
    output_lexical = lexical_absolute(output_value)
    reject_symlink_ancestors(output_lexical)
    output_root = output_lexical.resolve(strict=False)
    if is_relative_to(output_root, input_root) or is_relative_to(input_root, output_root):
        raise ProjectionError("Input and output directories must not overlap")
    return input_root, output_root


def matches_exclusion(relative_dir: Path, patterns: Iterable[str]) -> bool:
    text = relative_dir.as_posix()
    return any(fnmatch.fnmatchcase(text, pattern) for pattern in patterns)


def discover_skills(
    input_root: Path,
    marker: str,
    exclusion_patterns: Sequence[str],
    use_default_excludes: bool,
) -> list[Skill]:
    skills: list[Skill] = []
    for current_text, dir_names, file_names in os.walk(input_root, followlinks=False):
        current = Path(current_text)
        relative_current = current.relative_to(input_root)
        retained_dirs: list[str] = []
        for dir_name in dir_names:
            candidate = current / dir_name
            relative_candidate = candidate.relative_to(input_root)
            if candidate.is_symlink():
                continue
            if use_default_excludes and dir_name in DEFAULT_EXCLUDED_DIR_NAMES:
                continue
            if matches_exclusion(relative_candidate, exclusion_patterns):
                continue
            retained_dirs.append(dir_name)
        dir_names[:] = sorted(retained_dirs, key=str.casefold)
        marker_path = current / marker
        if (
            marker in file_names
            and not marker_path.is_symlink()
            and stat.S_ISREG(marker_path.lstat().st_mode)
        ):
            skills.append(
                Skill(
                    source=current.resolve(strict=True),
                    relative_source=relative_current,
                )
            )
    return sorted(skills, key=lambda skill: skill.relative_source.as_posix())


def relative_name(skill: Skill, input_root: Path, separator: str) -> str:
    parts = skill.relative_source.parts or (input_root.name,)
    return separator.join(parts)


def collision_groups(skills: Sequence[Skill]) -> list[list[Skill]]:
    groups: dict[str, list[Skill]] = {}
    for skill in skills:
        groups.setdefault(skill.link_name.casefold(), []).append(skill)
    return [group for group in groups.values() if len(group) > 1]


def assign_link_names(
    skills: Sequence[Skill],
    input_root: Path,
    collision_mode: str,
    separator: str,
) -> list[Skill]:
    validate_component(separator, "--separator")
    assigned = [replace(skill, link_name=skill.source.name) for skill in skills]
    collisions = collision_groups(assigned)
    if collisions and collision_mode == "error":
        lines = ["Duplicate flat skill names were found:"]
        for group in collisions:
            lines.append(f"  {group[0].link_name!r}:")
            lines.extend(f"    - {skill.source}" for skill in group)
        lines.append("Use --on-collision relative to derive names from relative paths.")
        raise ProjectionError("\n".join(lines))
    colliding_sources = {skill.source for group in collisions for skill in group}
    if colliding_sources:
        assigned = [
            replace(skill, link_name=relative_name(skill, input_root, separator))
            if skill.source in colliding_sources
            else skill
            for skill in assigned
        ]
    for skill in assigned:
        validate_component(skill.link_name, "generated link name")
    unresolved = collision_groups(assigned)
    if unresolved:
        details = "\n".join(
            f"  {group[0].link_name!r}: "
            + ", ".join(str(item.source) for item in group)
            for group in unresolved
        )
        raise ProjectionError(
            "Generated names still collide; choose a different --separator:\n" + details
        )
    return sorted(assigned, key=lambda skill: skill.link_name.casefold())


def read_link_target(link: Path) -> Path:
    raw_target = Path(os.readlink(link))
    if not raw_target.is_absolute():
        raw_target = link.parent / raw_target
    return raw_target.resolve(strict=False)


def link_target_text(source: Path, output_root: Path, absolute: bool) -> str:
    return str(source) if absolute else os.path.relpath(source, start=output_root)


def preflight_output(
    skills: Sequence[Skill],
    output_root: Path,
    input_root: Path,
    replace_links: bool,
    state: ProjectionState | None,
) -> None:
    conflicts: list[str] = []
    owned = state.links if state is not None else {}
    for skill in skills:
        destination = output_root / skill.link_name
        if not destination.exists() and not destination.is_symlink():
            continue
        if not destination.is_symlink():
            conflicts.append(f"{destination}: existing regular file or directory")
            continue
        existing_target = read_link_target(destination)
        recorded = owned.get(skill.link_name)
        if recorded is None:
            conflicts.append(f"{destination}: unmanaged symlink is never adopted")
            continue
        if existing_target != Path(recorded):
            conflicts.append(f"{destination}: state-owned symlink has changed")
        elif existing_target == skill.source:
            continue
        elif not replace_links:
            conflicts.append(
                f"{destination}: points to {existing_target}, expected {skill.source} "
                "(use --replace to replace this managed symlink)"
            )
    if conflicts:
        raise ProjectionError("Output conflicts:\n  " + "\n  ".join(conflicts))


def stale_managed_links(
    skills: Sequence[Skill],
    output_root: Path,
    state: ProjectionState | None,
) -> list[Path]:
    desired_names = {skill.link_name for skill in skills}
    if not output_root.is_dir() or state is None:
        return []
    stale: list[Path] = []
    for name, recorded in state.links.items():
        if name in desired_names:
            continue
        entry = output_root / name
        if not entry.exists() and not entry.is_symlink():
            continue
        if not entry.is_symlink() or read_link_target(entry) != Path(recorded):
            raise ProjectionError(f"State-owned output changed: {entry}")
        stale.append(entry)
    return sorted(stale, key=lambda path: path.name.casefold())


def build_plan(args: argparse.Namespace) -> ProjectionPlan:
    if args.check and args.dry_run:
        raise ProjectionError("--check and --dry-run cannot be combined")
    validate_component(args.marker, "--marker")
    input_root, output_root = resolve_roots(args.input, args.output)
    if output_root.exists() and not output_root.is_dir():
        raise ProjectionError(f"Output exists but is not a directory: {output_root}")
    skills = discover_skills(
        input_root,
        args.marker,
        args.exclude,
        not args.no_default_excludes,
    )
    skills = assign_link_names(
        skills,
        input_root,
        args.on_collision,
        args.separator,
    )
    try:
        state = load_state(output_root, input_root) if output_root.exists() else None
    except StateError as error:
        raise ProjectionError(str(error)) from error
    reserved = sorted(
        skill.link_name
        for skill in skills
        if skill.link_name in {LOCK_NAME, STATE_NAME}
    )
    if reserved:
        raise ProjectionError(
            "Generated link name is reserved for projection metadata: "
            + ", ".join(reserved)
        )
    if not skills and not ((args.clean or args.check) and state is not None):
        raise ProjectionError(
            f"No skill directories containing {args.marker!r} were found under {input_root}"
        )
    preflight_output(skills, output_root, input_root, args.replace, state)
    stale = (
        stale_managed_links(skills, output_root, state)
        if args.clean or args.check
        else []
    )
    return ProjectionPlan(
        input_root,
        output_root,
        tuple(skills),
        tuple(stale),
        dict(state.links) if state is not None else {},
        state is not None,
    )


def emit(message: str, quiet: bool) -> None:
    if not quiet:
        print(message)


def unique_sibling(destination: Path, label: str) -> Path:
    return destination.with_name(
        f".{destination.name}.{label}-{os.getpid()}-{secrets.token_hex(8)}"
    )


def atomic_symlink(destination: Path, target_text: str) -> tuple[int, int]:
    """Install a symlink without replacing any entry created by another writer."""
    temporary = destination.with_name(
        f".{destination.name}.flatten-{os.getpid()}-{secrets.token_hex(8)}"
    )
    try:
        temporary.symlink_to(target_text, target_is_directory=True)
        os.link(temporary, destination, follow_symlinks=False)
        identity, installed_target = link_snapshot(destination)
        if installed_target != target_text:
            raise ProjectionError(f"Installed symlink changed: {destination}")
        return identity
    finally:
        temporary.unlink(missing_ok=True)


def link_snapshot(path: Path) -> tuple[tuple[int, int], str]:
    metadata = path.lstat()
    if not stat.S_ISLNK(metadata.st_mode):
        raise ProjectionError(f"Output changed; expected a symlink at {path}")
    return (metadata.st_dev, metadata.st_ino), os.readlink(path)


def require_link_snapshot(
    path: Path, identity: tuple[int, int], raw_target: str
) -> None:
    current_identity, current_target = link_snapshot(path)
    if current_identity != identity or current_target != raw_target:
        raise ProjectionError(f"Output changed during execution: {path}")


def quarantine_link(
    path: Path,
    identity: tuple[int, int],
    raw_target: str,
) -> Path:
    """Move an expected link aside without deleting an intervening entry."""
    backup = unique_sibling(path, "rollback")
    os.rename(path, backup)
    try:
        require_link_snapshot(backup, identity, raw_target)
    except (OSError, ProjectionError):
        if not path.exists() and not path.is_symlink():
            os.rename(backup, path)
            raise ProjectionError(f"Output changed during execution: {path}")
        raise ProjectionError(
            f"Output changed during execution; preserved displaced entry at {backup}"
        )
    return backup


def restore_quarantined(change: AppliedChange) -> None:
    if change.backup is None or change.old_target is None:
        raise ProjectionError("projection rollback record is incomplete")
    if change.destination.exists() or change.destination.is_symlink():
        raise ProjectionError(f"rollback destination is occupied: {change.destination}")
    _, backup_target = link_snapshot(change.backup)
    if backup_target != change.old_target:
        raise ProjectionError(f"rollback backup changed: {change.backup}")
    os.rename(change.backup, change.destination)


def remove_installed_link(change: AppliedChange) -> None:
    if change.new_identity is None or change.new_target is None:
        raise ProjectionError("projection rollback record is incomplete")
    quarantine = quarantine_link(
        change.destination,
        change.new_identity,
        change.new_target,
    )
    quarantine.unlink()


def apply_skill(
    skill: Skill,
    plan: ProjectionPlan,
    args: argparse.Namespace,
) -> tuple[str, AppliedChange | None]:
    destination = plan.output_root / skill.link_name
    target_text = link_target_text(skill.source, plan.output_root, args.absolute)
    if destination.is_symlink():
        if read_link_target(destination) == skill.source:
            emit(f"KEEP    {destination} -> {os.readlink(destination)}", args.quiet)
            return "unchanged", None
        identity, old_target = link_snapshot(destination)
        if plan.owned.get(skill.link_name) != str(read_link_target(destination)):
            raise ProjectionError(f"Output changed; unmanaged symlink at {destination}")
        emit(f"REPLACE {destination} -> {target_text}", args.quiet)
        backup = None
        new_identity = None
        if not (args.dry_run or args.check):
            backup = quarantine_link(destination, identity, old_target)
            try:
                new_identity = atomic_symlink(destination, target_text)
            except (OSError, ProjectionError):
                if not destination.exists() and not destination.is_symlink():
                    os.rename(backup, destination)
                raise
        return (
            "replaced",
            AppliedChange(
                "replaced",
                destination,
                old_target,
                target_text,
                new_identity,
                backup,
            ),
        )
    if destination.exists():
        raise ProjectionError(f"Output changed; refusing to overwrite {destination}")
    emit(f"CREATE  {destination} -> {target_text}", args.quiet)
    new_identity = None
    if not (args.dry_run or args.check):
        new_identity = atomic_symlink(destination, target_text)
    return "created", AppliedChange(
        "created",
        destination,
        None,
        target_text,
        new_identity,
    )


def rollback_changes(changes: Sequence[AppliedChange]) -> None:
    failures: list[str] = []
    for change in reversed(changes):
        try:
            if change.kind == "created":
                remove_installed_link(change)
            elif change.kind == "replaced":
                remove_installed_link(change)
                restore_quarantined(change)
            elif change.kind == "removed":
                restore_quarantined(change)
        except (OSError, ProjectionError):
            failures.append(str(change.destination))
    if failures:
        raise ProjectionError("projection rollback was incomplete")


def apply_plan(plan: ProjectionPlan, args: argparse.Namespace) -> int:
    counts = {"created": 0, "replaced": 0, "unchanged": 0}
    changes: list[AppliedChange] = []
    new_state = dict(plan.owned)
    state_committed = False
    try:
        for skill in plan.skills:
            outcome, change = apply_skill(skill, plan, args)
            counts[outcome] += 1
            if change is not None:
                changes.append(change)
            new_state[skill.link_name] = str(skill.source)
        for link in plan.stale:
            emit(f"REMOVE  {link}", args.quiet)
            identity, old_target = link_snapshot(link)
            backup = None
            if not (args.dry_run or args.check):
                backup = quarantine_link(link, identity, old_target)
            changes.append(
                AppliedChange("removed", link, old_target, None, backup=backup)
            )
            new_state.pop(link.name, None)
        if not (args.dry_run or args.check):
            current_state = load_state(plan.output_root, plan.input_root)
            if (
                plan.had_state != (current_state is not None)
                or (
                    current_state is not None
                    and dict(current_state.links) != plan.owned
                )
            ):
                raise ProjectionError("projection state changed during execution")
            write_state(
                plan.output_root,
                plan.input_root,
                new_state,
                current_state if plan.had_state else None,
            )
            state_committed = True
            for change in changes:
                if change.backup is not None:
                    try:
                        change.backup.unlink()
                    except OSError:
                        print(
                            "warning: committed projection retained rollback "
                            f"backup at {change.backup}",
                            file=sys.stderr,
                        )
    except (OSError, ProjectionError, StateError):
        if not (args.dry_run or args.check or state_committed):
            rollback_changes(changes)
        raise
    mode = "CHECK" if args.check else "DRY RUN" if args.dry_run else "DONE"
    print(
        f"{mode}: {len(plan.skills)} skills; {counts['created']} created, "
        f"{counts['replaced']} replaced, {counts['unchanged']} unchanged, "
        f"{len(plan.stale)} stale removed."
    )
    changed = counts["created"] + counts["replaced"] + len(plan.stale)
    return 1 if args.check and changed else 0


def apply_projection(args: argparse.Namespace) -> int:
    plan = build_plan(args)
    if args.dry_run or args.check:
        return apply_plan(plan, args)
    if not args.dry_run:
        plan.output_root.mkdir(parents=True, exist_ok=True)
        reject_symlink_ancestors(plan.output_root)
    try:
        with projection_lock(plan.output_root):
            return apply_plan(build_plan(args), args)
    except StateError as error:
        raise ProjectionError(str(error)) from error


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return apply_projection(parse_args(argv))
    except (OSError, ProjectionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
