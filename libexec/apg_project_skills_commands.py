"""Command operations and CLI for project-local APG skill projection."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import sys
from typing import NoReturn, Sequence

from apg_project_skills_core import (
    AUTHORIZED_CONTAINERS,
    COMMAND_NAME,
    EXPECTED_SKILLS,
    KNOWN_UNMANAGED_SKILLS,
    MAX_EXCLUDE_BYTES,
    RESTART_REMINDER,
    FileSnapshot,
    LocalState,
    TargetRepository,
    ToolError,
    atomic_replace,
    canonical_skills,
    create_projection_parents,
    fail,
    frontmatter_name,
    fsync_directory,
    inode_matches,
    is_tracked,
    managed_status,
    mutation_lock,
    parse_exclude,
    parse_state,
    physical_apg_root,
    projection_path,
    read_locked_state,
    read_state,
    regular_file_bytes,
    require_exact_link,
    resolve_target,
    restore_snapshot,
    serialize_state,
    updated_exclude,
    validate_owned_projections,
    validate_projection_parents,
    validate_state_and_exclude,
)

def selected_skills(
    parser: argparse.ArgumentParser,
    requested: list[str] | None,
) -> tuple[str, ...]:
    values = requested or []
    unknown = [name for name in values if name not in EXPECTED_SKILLS]
    if unknown:
        parser.error(f"unknown or unmanaged release skill: {unknown[0]}")
    if len(values) != len(set(values)):
        parser.error("a managed release skill may be selected only once")
    return tuple(sorted(values))


def state_content_matches(path: Path, desired: bytes | None) -> bool:
    if desired is None:
        return not os.path.lexists(path)
    try:
        return path.is_file() and not path.is_symlink() and path.read_bytes() == desired
    except OSError:
        return False


def require_idempotent_status_compliance(
    repository: TargetRepository,
    managed_skills: Sequence[str],
) -> None:
    if managed_status(repository, managed_skills):
        fail(
            "managed projection paths are visible in normal Git status; "
            "restore the exact local ignore behavior and run check before "
            "retrying"
        )


def rollback_install(
    repository: TargetRepository,
    canonical: dict[str, Path],
    created_links: Sequence[str],
    created_containers: Sequence[str],
    exclude_snapshot: FileSnapshot,
) -> None:
    errors: list[str] = []
    try:
        restore_snapshot(repository.exclude_path, exclude_snapshot)
    except (OSError, ToolError) as error:
        errors.append(f"exclude restore failed: {error}")
    for skill in reversed(created_links):
        link = projection_path(repository, skill)
        try:
            if link.is_symlink() and link.resolve(strict=True) == canonical[skill]:
                link.unlink()
            elif os.path.lexists(link):
                errors.append(f"created link changed concurrently: {skill}")
        except OSError as error:
            errors.append(f"link cleanup failed for {skill}: {error}")
    for relative in reversed(created_containers):
        path = repository.root / relative
        try:
            if path.is_dir() and not path.is_symlink() and not any(path.iterdir()):
                path.rmdir()
        except OSError as error:
            errors.append(f"container cleanup failed for {relative}: {error}")
    if errors:
        fail(
            "mutation failed and rollback was incomplete; inspect target state: "
            + "; ".join(errors)
        )


def install(
    repository: TargetRepository,
    canonical: dict[str, Path],
    requested: tuple[str, ...],
    apg_root: Path,
) -> None:
    with mutation_lock(repository.state_path) as (descriptor, created_placeholder):
        state = read_locked_state(
            descriptor,
            created_placeholder=created_placeholder,
            apg_root=apg_root,
            target_root=repository.root,
        )
        exclude_snapshot = regular_file_bytes(
            repository.exclude_path,
            maximum=MAX_EXCLUDE_BYTES,
            label="exclude",
        )
        exclude = parse_exclude(exclude_snapshot.content)
        validate_state_and_exclude(state, exclude)
        validate_projection_parents(repository)
        if state is not None:
            validate_owned_projections(repository, canonical, state)

        if not requested:
            requested = state.managed_skills if state else EXPECTED_SKILLS

        already_managed = set(state.managed_skills if state else ())
        for skill in requested:
            if is_tracked(repository, skill):
                fail(
                    f"projection path is tracked for {skill}; untrack or choose "
                    "another target before retrying"
                )
            path = projection_path(repository, skill)
            if skill in already_managed:
                require_exact_link(
                    repository,
                    canonical,
                    skill,
                    missing_context="managed",
                )
                continue
            if os.path.lexists(path):
                if path.is_symlink():
                    fail(
                        f"unmanaged existing link conflicts for {skill}; use "
                        "adopt after verifying the manual projection"
                    )
                fail(
                    f"conflicting path exists for {skill}; preserve or relocate "
                    "it before retrying"
                )

        desired = tuple(sorted(already_managed | set(requested)))
        if state is not None and desired == state.managed_skills:
            require_idempotent_status_compliance(repository, desired)
            print(f"install: already compliant; {len(desired)} managed skill(s)")
            print(RESTART_REMINDER)
            return

        new_exclude, separator_added = updated_exclude(
            exclude_snapshot,
            exclude,
            desired,
            state.exclude_separator_added if state else False,
        )
        parsed_new_exclude = parse_exclude(new_exclude)
        if parsed_new_exclude.entries != desired:
            fail("constructed APG exclude block failed validation; no change made")

        created_containers: list[str] = []
        created_links: list[str] = []
        inherited_containers = list(state.created_containers if state else ())
        desired_state: LocalState | None = None
        desired_state_bytes: bytes | None = None
        try:
            created_containers = create_projection_parents(repository)
            for skill in requested:
                if skill in already_managed:
                    continue
                link = projection_path(repository, skill)
                try:
                    link.symlink_to(canonical[skill], target_is_directory=True)
                except FileExistsError:
                    fail(
                        f"projection path changed concurrently for {skill}; "
                        "inspect it before retrying"
                    )
                except OSError as error:
                    fail(
                        f"projection creation failed for {skill}: {error.strerror}; "
                        "inspect target permissions"
                    )
                created_links.append(skill)
                require_exact_link(
                    repository,
                    canonical,
                    skill,
                    missing_context="new",
                )

            if new_exclude != exclude_snapshot.content:
                atomic_replace(
                    repository.exclude_path,
                    new_exclude,
                    exclude_snapshot.mode,
                )
            if managed_status(repository, desired):
                fail(
                    "managed projection paths remain visible in normal Git "
                    "status; inspect local exclusion before retrying"
                )
            owned_containers = tuple(
                relative
                for relative in AUTHORIZED_CONTAINERS
                if relative in set(inherited_containers + created_containers)
            )
            desired_state = LocalState(
                str(apg_root),
                str(repository.root),
                desired,
                owned_containers,
                separator_added,
            )
            desired_state_bytes = serialize_state(desired_state)
            parse_state(desired_state_bytes, apg_root, repository.root)
            atomic_replace(repository.state_path, desired_state_bytes, 0o600)
        except BaseException:
            if not state_content_matches(repository.state_path, desired_state_bytes):
                rollback_install(
                    repository,
                    canonical,
                    created_links,
                    created_containers,
                    exclude_snapshot,
                )
            raise
        print(f"install: managed {len(desired)} skill(s)")
        print(RESTART_REMINDER)


def adopt(
    repository: TargetRepository,
    canonical: dict[str, Path],
    requested: tuple[str, ...],
    apg_root: Path,
) -> None:
    with mutation_lock(repository.state_path) as (descriptor, created_placeholder):
        state = read_locked_state(
            descriptor,
            created_placeholder=created_placeholder,
            apg_root=apg_root,
            target_root=repository.root,
        )
        exclude_snapshot = regular_file_bytes(
            repository.exclude_path,
            maximum=MAX_EXCLUDE_BYTES,
            label="exclude",
        )
        exclude = parse_exclude(exclude_snapshot.content)
        validate_state_and_exclude(state, exclude)
        validate_projection_parents(repository)
        if state is not None:
            validate_owned_projections(repository, canonical, state)

        if not requested:
            requested = state.managed_skills if state else EXPECTED_SKILLS

        already_managed = set(state.managed_skills if state else ())
        for skill in requested:
            if is_tracked(repository, skill):
                fail(
                    f"projection path is tracked for {skill}; adoption requires "
                    "an untracked exact manual link"
                )
            require_exact_link(
                repository,
                canonical,
                skill,
                missing_context="manual",
            )

        desired = tuple(sorted(already_managed | set(requested)))
        if state is not None and desired == state.managed_skills:
            require_idempotent_status_compliance(repository, desired)
            print(f"adopt: already compliant; {len(desired)} managed skill(s)")
            print(RESTART_REMINDER)
            return

        new_exclude, separator_added = updated_exclude(
            exclude_snapshot,
            exclude,
            desired,
            state.exclude_separator_added if state else False,
        )
        if parse_exclude(new_exclude).entries != desired:
            fail("constructed APG exclude block failed validation; no change made")
        desired_state = LocalState(
            str(apg_root),
            str(repository.root),
            desired,
            state.created_containers if state else (),
            separator_added,
        )
        desired_state_bytes = serialize_state(desired_state)
        try:
            if new_exclude != exclude_snapshot.content:
                atomic_replace(
                    repository.exclude_path,
                    new_exclude,
                    exclude_snapshot.mode,
                )
            if managed_status(repository, desired):
                fail(
                    "adopted projection paths remain visible in normal Git "
                    "status; inspect local exclusion before retrying"
                )
            atomic_replace(repository.state_path, desired_state_bytes, 0o600)
        except BaseException:
            if not state_content_matches(repository.state_path, desired_state_bytes):
                restore_snapshot(repository.exclude_path, exclude_snapshot)
            raise
        print(f"adopt: managed {len(desired)} skill(s)")
        print(RESTART_REMINDER)


def check(
    repository: TargetRepository,
    canonical: dict[str, Path],
    requested: tuple[str, ...],
    apg_root: Path,
) -> None:
    state = read_state(repository.state_path, apg_root, repository.root)
    exclude_snapshot = regular_file_bytes(
        repository.exclude_path,
        maximum=MAX_EXCLUDE_BYTES,
        label="exclude",
    )
    exclude = parse_exclude(exclude_snapshot.content)
    validate_state_and_exclude(state, exclude)
    if state is None:
        if requested:
            fail(
                "requested skills are not locally managed; run install or adopt "
                "before treating them as managed"
            )
        unmanaged_present = any(
            os.path.lexists(projection_path(repository, skill))
            for skill in (*EXPECTED_SKILLS, *KNOWN_UNMANAGED_SKILLS)
        )
        if unmanaged_present:
            print(
                "check: compliant local ownership state; 0 managed skills; "
                "unmanaged projection paths were not claimed or validated"
            )
        else:
            print("check: compliant uninstalled state; 0 managed skills")
        return

    validate_owned_projections(repository, canonical, state)
    unmanaged = [name for name in requested if name not in state.managed_skills]
    if unmanaged:
        fail(
            f"requested skill is not in local ownership state: {unmanaged[0]}; "
            "install or adopt it first"
        )
    if managed_status(repository, state.managed_skills):
        fail(
            "managed projection paths are not clean in normal Git status; "
            "restore the exact APG exclusion block"
        )
    selected = requested or state.managed_skills
    print(f"check: compliant; {len(selected)} managed skill(s) verified")


def recreate_removed_links(
    repository: TargetRepository,
    canonical: dict[str, Path],
    removed_links: Sequence[str],
    removed_containers: Sequence[str],
) -> list[str]:
    errors: list[str] = []
    for relative in AUTHORIZED_CONTAINERS:
        if relative not in removed_containers:
            continue
        path = repository.root / relative
        try:
            path.mkdir(mode=0o755)
        except FileExistsError:
            if path.is_symlink() or not path.is_dir():
                errors.append(f"container changed concurrently: {relative}")
        except OSError as error:
            errors.append(f"container restore failed for {relative}: {error}")
    for skill in removed_links:
        link = projection_path(repository, skill)
        try:
            if not os.path.lexists(link):
                link.symlink_to(canonical[skill], target_is_directory=True)
            elif not link.is_symlink() or link.resolve(strict=True) != canonical[skill]:
                errors.append(f"link changed concurrently: {skill}")
        except OSError as error:
            errors.append(f"link restore failed for {skill}: {error}")
    return errors


def uninstall(
    repository: TargetRepository,
    canonical: dict[str, Path],
    requested: tuple[str, ...],
    apg_root: Path,
) -> None:
    with mutation_lock(repository.state_path) as (descriptor, created_placeholder):
        state = read_locked_state(
            descriptor,
            created_placeholder=created_placeholder,
            apg_root=apg_root,
            target_root=repository.root,
        )
        exclude_snapshot = regular_file_bytes(
            repository.exclude_path,
            maximum=MAX_EXCLUDE_BYTES,
            label="exclude",
        )
        exclude = parse_exclude(exclude_snapshot.content)
        validate_state_and_exclude(state, exclude)
        if state is None:
            unmanaged_present = any(
                os.path.lexists(projection_path(repository, skill))
                for skill in EXPECTED_SKILLS
            )
            if unmanaged_present:
                print(
                    "uninstall: no-op; no locally managed state; unmanaged "
                    "projection paths were left unchanged"
                )
            else:
                print("uninstall: no-op; repository is already fully uninstalled")
            print(RESTART_REMINDER)
            return

        validate_owned_projections(repository, canonical, state)
        selected = requested or state.managed_skills
        unmanaged = [name for name in selected if name not in state.managed_skills]
        if unmanaged:
            fail(
                f"uninstall requested a skill not owned by local state: "
                f"{unmanaged[0]}; leave the unmanaged path unchanged"
            )
        for skill in selected:
            if is_tracked(repository, skill):
                fail(
                    f"managed projection became tracked for {skill}; restore "
                    "tracked state before uninstalling"
                )
            require_exact_link(
                repository,
                canonical,
                skill,
                missing_context="managed",
            )

        remaining = tuple(
            skill for skill in state.managed_skills if skill not in set(selected)
        )
        new_exclude, _ = updated_exclude(
            exclude_snapshot,
            exclude,
            remaining,
            state.exclude_separator_added,
        )
        parsed_new = parse_exclude(new_exclude)
        if remaining and parsed_new.entries != remaining:
            fail("constructed APG exclude block failed validation; no change made")
        if not remaining and parsed_new.present:
            fail("constructed APG exclude removal failed validation; no change made")

        desired_state_bytes: bytes | None
        if remaining:
            desired_state = LocalState(
                state.apg_root,
                state.target_root,
                remaining,
                state.created_containers,
                state.exclude_separator_added,
            )
            desired_state_bytes = serialize_state(desired_state)
        else:
            desired_state_bytes = None

        removed_links: list[str] = []
        removed_containers: list[str] = []
        try:
            for skill in selected:
                projection_path(repository, skill).unlink()
                removed_links.append(skill)
            if new_exclude != exclude_snapshot.content:
                atomic_replace(
                    repository.exclude_path,
                    new_exclude,
                    exclude_snapshot.mode,
                )
            if remaining:
                if managed_status(repository, remaining):
                    fail(
                        "remaining projections are not clean in normal Git status; "
                        "restore the exact exclusion block"
                    )
                atomic_replace(repository.state_path, desired_state_bytes, 0o600)
            else:
                for relative in reversed(state.created_containers):
                    path = repository.root / relative
                    if (
                        path.is_dir()
                        and not path.is_symlink()
                        and not any(path.iterdir())
                    ):
                        path.rmdir()
                        removed_containers.append(relative)
                if not inode_matches(repository.state_path, descriptor):
                    fail(
                        "local state changed concurrently before removal; inspect "
                        "Git metadata"
                    )
                repository.state_path.unlink()
                fsync_directory(repository.state_path.parent)
        except BaseException:
            if not state_content_matches(repository.state_path, desired_state_bytes):
                errors = recreate_removed_links(
                    repository,
                    canonical,
                    removed_links,
                    removed_containers,
                )
                try:
                    restore_snapshot(repository.exclude_path, exclude_snapshot)
                except (OSError, ToolError) as error:
                    errors.append(f"exclude restore failed: {error}")
                if errors:
                    fail(
                        "uninstall failed and rollback was incomplete; inspect "
                        "target state: " + "; ".join(errors)
                    )
            raise
        print(
            f"uninstall: removed {len(selected)} skill(s); "
            f"{len(remaining)} remain managed"
        )
        print(RESTART_REMINDER)


def install_signal_handlers() -> None:
    def interrupted(signum: int, _frame: object) -> NoReturn:
        name = signal.Signals(signum).name
        fail(
            f"mutation interrupted by {name}; rollback was attempted and target "
            "state must be checked before retrying"
        )

    for name in ("SIGINT", "SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), interrupted)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description=(
            "Manage local symbolic-link projections of the current APG "
            "release skills in an opted-in Git worktree."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "list",
        help="list managed current-release skill names without a target",
    )
    for command, help_text in (
        ("install", "create missing local projections and ownership state"),
        ("adopt", "claim compatible existing manual projections"),
        ("check", "verify local managed projection compliance read-only"),
        ("uninstall", "remove only projections proven owned by local state"),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument(
            "--repo",
            action="append",
            metavar="PATH",
            help="target path inside a non-bare Git worktree (default: current)",
        )
        command_parser.add_argument(
            "--skill",
            action="append",
            metavar="NAME",
            help=(
                "limit the operation to one managed current-release skill; "
                "repeat as needed"
            ),
        )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(arguments)
    apg_root = physical_apg_root()
    canonical = canonical_skills(apg_root)
    if namespace.command == "list":
        for skill in EXPECTED_SKILLS:
            print(skill)
        return 0

    if namespace.repo and len(namespace.repo) > 1:
        parser.error("--repo may be specified only once")
    requested = selected_skills(parser, namespace.skill)
    repository = resolve_target(namespace.repo[0] if namespace.repo else ".")
    if namespace.command == "install":
        install_signal_handlers()
        install(repository, canonical, requested, apg_root)
    elif namespace.command == "adopt":
        install_signal_handlers()
        adopt(repository, canonical, requested, apg_root)
    elif namespace.command == "check":
        check(repository, canonical, requested, apg_root)
    elif namespace.command == "uninstall":
        install_signal_handlers()
        uninstall(repository, canonical, requested, apg_root)
    else:
        parser.error(f"unsupported command: {namespace.command}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ToolError as error:
        print(f"{COMMAND_NAME}: {error}", file=sys.stderr)
        raise SystemExit(1) from None
