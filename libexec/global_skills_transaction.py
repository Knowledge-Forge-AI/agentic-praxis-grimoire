"""Plan and apply one owned multi-source global skill transaction."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import os
from pathlib import Path
import secrets
import stat
from typing import Callable, Mapping, Sequence

from global_skills_inventory import (
    Inventory,
    InventoryError,
    PathIdentity,
    SkillRecord,
    build_inventory,
    read_skill_marker,
)
from global_skills_state import (
    apg_user_skills_guard,
    ContainerIdentity,
    created_container_identity,
    InstallState,
    LoadedState,
    LOCK_NAME,
    STATE_NAME,
    StateError,
    destination_lock,
    from_inventory,
    load_state,
    no_overwrite_move,
    read_private_regular,
    rename_directory_no_replace,
    write_state,
)


OTHER_OWNER_NAMES = frozenset(
    {
        ".flatten-skill-symlinks-state.json",
        ".flatten-skill-symlinks.lock",
    }
)
RESERVED_NAMES = frozenset({STATE_NAME, LOCK_NAME, *OTHER_OWNER_NAMES})


class TransactionError(RuntimeError):
    """Destination state, ownership, or a transaction step is unsafe."""


@dataclass(frozen=True, slots=True)
class Action:
    kind: str
    name: str
    old_target: str | None
    new_target: str | None


@dataclass(frozen=True, slots=True)
class Plan:
    agent: str
    inventory: Inventory
    state: LoadedState | None
    actions: tuple[Action, ...]
    unchanged: int
    state_changed: bool

    @property
    def changed(self) -> bool:
        return bool(self.actions) or self.state_changed

    def count(self, kind: str) -> int:
        return sum(action.kind == kind for action in self.actions)


@dataclass(frozen=True, slots=True)
class OperationResult:
    agent: str
    inventory: Inventory | None
    destination: Path
    mode: str
    created: int
    replaced: int
    removed: int
    unchanged: int
    changed: bool
    warnings: tuple[str, ...] = ()


class ChangeStage(IntEnum):
    PLANNED = 0
    OLD_QUARANTINED = 1
    NEW_INSTALLED = 2
    STATE_COMMITTED = 3
    BACKUP_CLEANED = 4


@dataclass(slots=True)
class AppliedChange:
    kind: str
    destination: Path
    old_target: str | None
    new_target: str | None
    new_identity: tuple[int, int] | None = None
    backup: Path | None = None
    old_identity: tuple[int, int] | None = None
    stage: ChangeStage = ChangeStage.PLANNED


def lexists(path: Path) -> bool:
    return os.path.lexists(path)


def reject_symlink_ancestors(path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        if not lexists(current):
            return
        metadata = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise TransactionError(f"destination has an unsafe ancestor: {current}")


def existing_entries(root: Path) -> dict[str, Path]:
    if not root.exists():
        return {}
    groups: dict[str, list[Path]] = {}
    for entry in root.iterdir():
        groups.setdefault(entry.name.casefold(), []).append(entry)
    duplicates = [group for group in groups.values() if len(group) > 1]
    if duplicates:
        names = ", ".join(path.name for group in duplicates for path in group)
        raise TransactionError(f"destination has case-colliding entries: {names}")
    return {key: group[0] for key, group in groups.items()}


def raw_link(path: Path) -> str:
    metadata = path.lstat()
    if not stat.S_ISLNK(metadata.st_mode):
        raise TransactionError(f"expected an owned symbolic link: {path.name}")
    return os.readlink(path)


def resolved_link(path: Path) -> Path:
    target = Path(raw_link(path))
    if not target.is_absolute():
        target = path.parent / target
    return target.resolve(strict=False)


def expected_state_changed(
    current: InstallState | None,
    agent: str,
    inventory: Inventory,
) -> bool:
    if current is None:
        return True
    desired = from_inventory(agent, inventory, current.created_containers, current)
    return (
        current.sources != desired.sources
        or dict(current.links) != dict(desired.links)
        or dict(current.skill_hashes) != dict(desired.skill_hashes)
    )


def validate_reserved(inventory: Inventory, entries: Mapping[str, Path]) -> None:
    reserved = {name.casefold() for name in RESERVED_NAMES}
    requested = sorted(
        skill.name
        for skill in inventory.skills
        if skill.name.casefold() in reserved
    )
    if requested:
        raise TransactionError(
            "skill names are reserved for ownership metadata: " + ", ".join(requested)
        )
    for name in OTHER_OWNER_NAMES:
        if name.casefold() in entries:
            raise TransactionError(
                f"destination contains state or a lock owned by another command: {name}"
            )


def plan(agent: str, inventory: Inventory, *, lock_held: bool = False) -> Plan:
    root = inventory.destination
    reject_symlink_ancestors(root)
    if root.exists() and (root.is_symlink() or not root.is_dir()):
        raise TransactionError("destination exists but is not a safe directory")
    entries = existing_entries(root)
    validate_reserved(inventory, entries)
    if not lock_held and LOCK_NAME.casefold() in entries:
        raise TransactionError("global skill installation is already active")
    try:
        loaded = load_state(root, agent) if root.exists() else None
    except StateError as error:
        raise TransactionError(str(error)) from error
    owned = {} if loaded is None else dict(loaded.state.links)
    desired = {skill.name: str(skill.source) for skill in inventory.skills}
    actions: list[Action] = []
    unchanged = 0
    for skill in inventory.skills:
        entry = entries.get(skill.name.casefold())
        if entry is None:
            actions.append(Action("create", skill.name, None, str(skill.source)))
            continue
        if entry.name != skill.name:
            raise TransactionError(
                f"unmanaged case-colliding destination entry: {entry.name}"
            )
        recorded = owned.get(skill.name)
        if recorded is None:
            raise TransactionError(f"unmanaged destination entry: {skill.name}")
        if resolved_link(entry) != Path(recorded):
            raise TransactionError(f"state-owned target changed: {skill.name}")
        if Path(recorded) == skill.source:
            unchanged += 1
        else:
            actions.append(Action("replace", skill.name, raw_link(entry), str(skill.source)))
    for name, recorded in sorted(owned.items(), key=lambda item: item[0].casefold()):
        if name in desired:
            continue
        entry = entries.get(name.casefold())
        if entry is None:
            continue
        if entry.name != name or resolved_link(entry) != Path(recorded):
            raise TransactionError(f"stale state-owned target changed: {name}")
        actions.append(Action("remove", name, raw_link(entry), None))
    return Plan(
        agent,
        inventory,
        loaded,
        tuple(actions),
        unchanged,
        expected_state_changed(
            None if loaded is None else loaded.state, agent, inventory
        ),
    )


def unique_sibling(destination: Path, label: str) -> Path:
    return destination.with_name(
        f".{destination.name}.{label}-{os.getpid()}-{secrets.token_hex(8)}"
    )


def link_snapshot(path: Path) -> tuple[tuple[int, int], str]:
    metadata = path.lstat()
    if not stat.S_ISLNK(metadata.st_mode):
        raise TransactionError(f"expected a symbolic link: {path.name}")
    return (metadata.st_dev, metadata.st_ino), os.readlink(path)


def require_snapshot(path: Path, identity: tuple[int, int], target: str) -> None:
    current_identity, current_target = link_snapshot(path)
    if current_identity != identity or current_target != target:
        raise TransactionError(f"destination changed during transaction: {path.name}")


def atomic_symlink(
    destination: Path,
    target: str,
    register: Callable[[tuple[int, int]], None] | None = None,
    validate: Callable[[], None] | None = None,
) -> tuple[int, int]:
    temporary = unique_sibling(destination, "install")
    identity: tuple[int, int] | None = None
    try:
        temporary.symlink_to(target, target_is_directory=True)
        identity, _ = link_snapshot(temporary)
        if validate is not None:
            validate()
        os.link(temporary, destination, follow_symlinks=False)
        installed_identity, installed_target = link_snapshot(destination)
        if installed_identity != identity or installed_target != target:
            raise TransactionError(f"installed target changed: {destination.name}")
        temporary.unlink()
        if register is not None:
            register(identity)
        return identity
    except BaseException:
        if identity is not None:
            try:
                if link_snapshot(destination)[0] == identity:
                    destination.unlink()
            except (OSError, TransactionError):
                pass
            try:
                if link_snapshot(temporary)[0] == identity:
                    temporary.unlink()
            except (OSError, TransactionError):
                pass
        raise


def quarantine(
    path: Path,
    identity: tuple[int, int],
    raw_target: str,
    backup: Path | None = None,
    register: Callable[[], None] | None = None,
) -> Path:
    selected = backup or unique_sibling(path, "rollback")
    try:
        no_overwrite_move(path, selected, identity)
        require_snapshot(selected, identity, raw_target)
        if register is not None:
            register()
    except BaseException:
        if lexists(selected) and not lexists(path):
            no_overwrite_move(selected, path, identity)
        raise
    return selected


def restore(change: AppliedChange) -> None:
    if (
        change.backup is None
        or change.old_target is None
        or change.old_identity is None
    ):
        raise TransactionError("rollback record is incomplete")
    if lexists(change.destination):
        try:
            require_snapshot(
                change.destination, change.old_identity, change.old_target
            )
        except TransactionError as error:
            raise TransactionError(
                f"rollback destination is occupied: {change.destination.name}"
            ) from error
        return
    if not lexists(change.backup):
        raise TransactionError(
            f"rollback backup is absent: {change.destination.name}"
        )
    require_snapshot(change.backup, change.old_identity, change.old_target)
    no_overwrite_move(
        change.backup, change.destination, change.old_identity
    )


def cleanup_backup(change: AppliedChange) -> None:
    if (
        change.backup is None
        or change.old_target is None
        or change.old_identity is None
    ):
        raise TransactionError("cleanup record is incomplete")
    require_snapshot(change.backup, change.old_identity, change.old_target)
    change.backup.unlink()
    change.stage = ChangeStage.BACKUP_CLEANED


def remove_new(change: AppliedChange) -> None:
    if change.new_target is None:
        raise TransactionError("rollback record is incomplete")
    if not lexists(change.destination):
        return
    if change.new_identity is None:
        raise TransactionError("rollback record is incomplete")
    identity, target = link_snapshot(change.destination)
    if target != change.new_target or identity != change.new_identity:
        raise TransactionError(
            f"rollback destination changed: {change.destination.name}"
        )
    backup = quarantine(
        change.destination, change.new_identity, change.new_target
    )
    backup.unlink()


def rollback(changes: Sequence[AppliedChange]) -> None:
    failures: list[str] = []
    for change in reversed(changes):
        try:
            if change.stage == ChangeStage.PLANNED:
                continue
            if change.stage >= ChangeStage.STATE_COMMITTED:
                continue
            if change.kind == "create":
                remove_new(change)
            elif change.kind == "replace":
                if change.stage >= ChangeStage.NEW_INSTALLED:
                    remove_new(change)
                restore(change)
            else:
                restore(change)
        except (OSError, TransactionError):
            failures.append(change.destination.name)
    if failures:
        raise TransactionError(
            "transaction rollback was incomplete: " + ", ".join(failures)
        )


def require_directory_identity(path: Path, expected: PathIdentity) -> None:
    metadata = path.lstat()
    observed = PathIdentity(
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IMODE(metadata.st_mode),
        metadata.st_uid,
    )
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or observed != expected
    ):
        raise TransactionError("source skill changed")


def validate_skill(skill: SkillRecord) -> None:
    try:
        require_directory_identity(
            skill.repository, skill.repository_identity
        )
        require_directory_identity(
            skill.skills_root, skill.skills_root_identity
        )
        relative = skill.source.relative_to(skill.skills_root)
        current = skill.skills_root
        for component in relative.parts:
            current /= component
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                raise TransactionError(
                    f"source skill changed: {skill.name}"
                )
        require_directory_identity(skill.source, skill.source_identity)
        marker_identity, marker_digest = read_skill_marker(
            skill.source / "SKILL.md"
        )
    except (
        InventoryError,
        OSError,
        TransactionError,
        ValueError,
    ) as error:
        raise TransactionError(
            f"source skill changed: {skill.name}"
        ) from error
    if (
        marker_identity != skill.marker_identity
        or marker_digest != skill.skill_sha256
    ):
        raise TransactionError(f"source skill changed: {skill.name}")


def cleanup_uncertain_container_install(
    staged: Path,
    destination: Path,
    expected: ContainerIdentity,
) -> tuple[str, ...]:
    residual: list[str] = []
    found = False
    for candidate in (staged, destination):
        try:
            metadata = os.stat(candidate, follow_symlinks=False)
        except FileNotFoundError:
            continue
        except OSError:
            residual.append(candidate.name)
            continue
        identity = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_uid,
            stat.S_IMODE(metadata.st_mode),
        )
        if identity == (
            expected.device,
            expected.inode,
            expected.owner,
            expected.mode,
        ):
            found = True
            try:
                candidate.rmdir()
            except OSError:
                residual.append(candidate.name)
        elif candidate == staged:
            residual.append(candidate.name)
    if not found and not residual:
        residual.append(destination.name)
    return tuple(residual)


def install_destination_component(
    path: Path,
    created: list[ContainerIdentity],
) -> None:
    staged = unique_sibling(path, "container")
    staged.mkdir(mode=0o700)
    staged_identity: ContainerIdentity | None = None
    try:
        staged_identity = created_container_identity(staged)
    except BaseException as error:
        if staged_identity is None:
            try:
                staged_identity = created_container_identity(staged)
            except BaseException:
                raise TransactionError(
                    "destination creation cleanup was incomplete: "
                    f"{path.name}"
                ) from error
        residual = remove_empty_containers((staged_identity,))
        if residual:
            raise TransactionError(
                "destination creation cleanup was incomplete: "
                f"{path.name}"
            ) from error
        raise
    try:
        rename_directory_no_replace(staged, path)
        recorded = ContainerIdentity(
            str(path),
            staged_identity.device,
            staged_identity.inode,
            staged_identity.owner,
            staged_identity.mode,
        )
        created.append(recorded)
        observed = created_container_identity(path)
        if (
            observed.device,
            observed.inode,
            observed.owner,
            observed.mode,
        ) != (
            recorded.device,
            recorded.inode,
            recorded.owner,
            recorded.mode,
        ):
            raise TransactionError(
                f"created destination component changed: {path.name}"
            )
    except BaseException as error:
        if any(item.path == str(path) for item in created):
            raise
        residual = cleanup_uncertain_container_install(
            staged, path, staged_identity
        )
        if residual:
            raise TransactionError(
                "destination creation cleanup was incomplete: "
                + ", ".join(residual)
            ) from error
        raise


def create_destination(root: Path) -> tuple[ContainerIdentity, ...]:
    reject_symlink_ancestors(root)
    missing: list[Path] = []
    current = root
    while not lexists(current):
        missing.append(current)
        current = current.parent
    created: list[ContainerIdentity] = []
    try:
        for path in reversed(missing):
            install_destination_component(path, created)
    except BaseException as error:
        residual = remove_empty_containers(created)
        if residual:
            raise TransactionError(
                "destination creation cleanup was incomplete: "
                + ", ".join(residual)
            ) from error
        raise
    return tuple(created)


def remove_empty_containers(
    containers: Sequence[ContainerIdentity],
) -> tuple[str, ...]:
    residual: list[str] = []
    for expected in reversed(containers):
        path = Path(expected.path)
        try:
            try:
                metadata = os.stat(path, follow_symlinks=False)
            except BaseException:
                descriptor = os.open(
                    path,
                    os.O_RDONLY
                    | getattr(os, "O_DIRECTORY", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                )
                try:
                    metadata = os.fstat(descriptor)
                finally:
                    os.close(descriptor)
            identity = (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_uid,
                stat.S_IMODE(metadata.st_mode),
            )
            if identity == (
                expected.device,
                expected.inode,
                expected.owner,
                expected.mode,
            ):
                path.rmdir()
            else:
                residual.append(path.name)
        except FileNotFoundError:
            continue
        except OSError:
            residual.append(path.name)
    return tuple(residual)


def locked_plan(
    agent: str, inventory: Inventory, initial: Plan
) -> tuple[Inventory, Plan]:
    refreshed = build_inventory(
        tuple(item.repository for item in inventory.sources),
        inventory.destination,
    )
    if refreshed != inventory:
        raise TransactionError("source inventory changed before lock acquisition")
    current = plan(agent, refreshed, lock_held=True)
    if (
        current.actions != initial.actions
        or current.state_changed != initial.state_changed
    ):
        raise TransactionError("destination changed before lock acquisition")
    validate_skills(refreshed.skills)
    return refreshed, current


def validate_skills(skills: Sequence[SkillRecord]) -> None:
    for skill in skills:
        validate_skill(skill)


def stage_actions(current: Plan, changes: list[AppliedChange]) -> None:
    skills = {skill.name: skill for skill in current.inventory.skills}
    for action in current.actions:
        destination = current.inventory.destination / action.name
        if action.kind in {"create", "replace"}:
            validate_skill(skills[action.name])
        if action.kind == "create":
            change = AppliedChange(
                "create", destination, None, action.new_target
            )
            changes.append(change)

            def installed(identity: tuple[int, int]) -> None:
                change.new_identity = identity
                change.stage = ChangeStage.NEW_INSTALLED

            atomic_symlink(
                destination,
                action.new_target or "",
                installed,
                lambda: validate_skill(skills[action.name]),
            )
            continue
        identity, raw_target = link_snapshot(destination)
        if raw_target != action.old_target:
            raise TransactionError(
                f"destination changed during transaction: {action.name}"
            )
        backup = unique_sibling(destination, "rollback")
        if action.kind == "replace":
            change = AppliedChange(
                "replace",
                destination,
                raw_target,
                action.new_target,
                backup=backup,
                old_identity=identity,
            )

            def quarantined() -> None:
                change.stage = ChangeStage.OLD_QUARANTINED
                changes.append(change)

            quarantine(
                destination,
                identity,
                raw_target,
                backup,
                quarantined,
            )

            def replacement_installed(
                new_identity: tuple[int, int],
            ) -> None:
                change.new_identity = new_identity
                change.stage = ChangeStage.NEW_INSTALLED

            atomic_symlink(
                destination,
                action.new_target or "",
                replacement_installed,
                lambda: validate_skill(skills[action.name]),
            )
        else:
            change = AppliedChange(
                "remove",
                destination,
                raw_target,
                None,
                backup=backup,
                old_identity=identity,
            )

            def removal_quarantined() -> None:
                change.stage = ChangeStage.OLD_QUARANTINED
                changes.append(change)

            quarantine(
                destination,
                identity,
                raw_target,
                backup,
                removal_quarantined,
            )


def commit_apply_state(
    agent: str,
    current: Plan,
    created_containers: tuple[ContainerIdentity, ...],
    committed: Callable[[], None],
) -> str | None:
    previous = None if current.state is None else current.state.state
    containers = (
        previous.created_containers
        if previous is not None
        else created_containers
    )
    if not current.changed:
        committed()
        return None
    validate_skills(current.inventory.skills)
    desired = from_inventory(
        agent, current.inventory, containers, previous
    )
    return write_state(
        current.inventory.destination,
        desired,
        current.state,
        lambda: validate_skills(current.inventory.skills),
        committed,
    )


def cleanup_changes(
    changes: Sequence[AppliedChange], operation: str
) -> list[str]:
    warnings: list[str] = []
    for change in changes:
        if change.backup is None:
            continue
        try:
            cleanup_backup(change)
        except (OSError, TransactionError):
            warnings.append(
                f"committed {operation} retained an owner-only rollback backup"
            )
    return warnings


def apply(
    agent: str,
    inventory: Inventory,
    environment: Mapping[str, str] | None = None,
) -> OperationResult:
    initial = plan(agent, inventory)
    created_containers: tuple[ContainerIdentity, ...] = ()
    changes: list[AppliedChange] = []
    committed = False
    warnings: list[str] = []
    try:
        created_containers = create_destination(inventory.destination)
        with destination_lock(inventory.destination):
            with apg_user_skills_guard(
                inventory.destination, environment or {}
            ):
                _, current = locked_plan(agent, inventory, initial)
                stage_actions(current, changes)

                def state_committed() -> None:
                    nonlocal committed
                    committed = True
                    for change in changes:
                        change.stage = ChangeStage.STATE_COMMITTED

                state_warning = commit_apply_state(
                    agent,
                    current,
                    created_containers,
                    state_committed,
                )
                if state_warning is not None:
                    warnings.append(state_warning)
            warnings.extend(cleanup_changes(changes, "transaction"))
    except BaseException as error:
        if not committed:
            failures: list[str] = []
            try:
                rollback(changes)
            except TransactionError as rollback_error:
                failures.append(str(rollback_error))
            residual = remove_empty_containers(created_containers)
            if residual:
                failures.append(
                    "destination cleanup was incomplete: "
                    + ", ".join(residual)
                )
            if failures:
                raise TransactionError("; ".join(failures)) from error
        raise
    return OperationResult(
        agent,
        inventory,
        inventory.destination,
        "apply",
        current.count("create"),
        current.count("replace"),
        current.count("remove"),
        current.unchanged,
        current.changed,
        tuple(warnings),
    )


def inspect(agent: str, inventory: Inventory, mode: str) -> OperationResult:
    current = plan(agent, inventory)
    return OperationResult(
        agent,
        inventory,
        inventory.destination,
        mode,
        current.count("create"),
        current.count("replace"),
        current.count("remove"),
        current.unchanged,
        current.changed,
    )


def uninstall_preflight(agent: str, root: Path) -> LoadedState:
    reject_symlink_ancestors(root)
    if not root.is_dir() or root.is_symlink():
        raise TransactionError("installer ownership state is absent")
    entries = existing_entries(root)
    validate_reserved(Inventory(root, (), ()), entries)
    if LOCK_NAME.casefold() in entries:
        raise TransactionError("global skill installation is already active")
    loaded = load_state(root, agent)
    if loaded is None:
        raise TransactionError("installer ownership state is absent")
    return loaded


def reload_uninstall_state(
    agent: str, root: Path, expected: LoadedState
) -> LoadedState:
    current = load_state(root, agent)
    if (
        current is None
        or current.identity != expected.identity
        or current.payload != expected.payload
    ):
        raise TransactionError("installer state changed before uninstall")
    return current


def stage_uninstall_links(
    root: Path,
    current: LoadedState,
    changes: list[AppliedChange],
) -> None:
    for name, target in sorted(current.state.links.items()):
        path = root / name
        if not path.is_symlink() or resolved_link(path) != Path(target):
            raise TransactionError(f"state-owned target changed: {name}")
        identity, raw_target = link_snapshot(path)
        backup = unique_sibling(path, "rollback")
        change = AppliedChange(
            "remove",
            path,
            raw_target,
            None,
            backup=backup,
            old_identity=identity,
        )

        def quarantined() -> None:
            change.stage = ChangeStage.OLD_QUARANTINED
            changes.append(change)

        quarantine(path, identity, raw_target, backup, quarantined)


def quarantine_uninstall_state(
    root: Path,
    current: LoadedState,
    backup: Path | None = None,
) -> Path:
    state_path = root / STATE_NAME
    selected = backup or unique_sibling(state_path, "uninstall")
    no_overwrite_move(state_path, selected, current.identity)
    try:
        _, payload = read_private_regular(selected, current.identity)
    except BaseException:
        if not lexists(state_path):
            no_overwrite_move(selected, state_path, current.identity)
        raise
    if payload != current.payload:
        if not lexists(state_path):
            no_overwrite_move(selected, state_path, current.identity)
        raise TransactionError("installer state changed during uninstall")
    return selected


def cleanup_state_backup(backup: Path) -> str | None:
    try:
        backup.unlink()
    except OSError:
        return "committed uninstall retained an owner-only state backup"
    return None


def uninstall(
    agent: str,
    root: Path,
    environment: Mapping[str, str] | None = None,
) -> OperationResult:
    loaded = uninstall_preflight(agent, root)
    changes: list[AppliedChange] = []
    warnings: list[str] = []
    committed = False
    try:
        with destination_lock(root):
            with apg_user_skills_guard(root, environment or {}):
                current = reload_uninstall_state(agent, root, loaded)
                stage_uninstall_links(root, current, changes)
                state_backup = unique_sibling(
                    root / STATE_NAME, "uninstall"
                )
                try:
                    quarantine_uninstall_state(
                        root, current, state_backup
                    )
                except BaseException:
                    if (
                        lexists(state_backup)
                        and not lexists(root / STATE_NAME)
                    ):
                        no_overwrite_move(
                            state_backup,
                            root / STATE_NAME,
                            current.identity,
                        )
                    raise
                committed = True
                for change in changes:
                    change.stage = ChangeStage.STATE_COMMITTED
            warnings.extend(cleanup_changes(changes, "uninstall"))
            state_warning = cleanup_state_backup(state_backup)
            if state_warning is not None:
                warnings.append(state_warning)
    except BaseException:
        if not committed:
            rollback(changes)
        raise
    remove_empty_containers(loaded.state.created_containers)
    return OperationResult(
        agent,
        None,
        root,
        "uninstall",
        0,
        0,
        len(changes),
        0,
        True,
        tuple(warnings),
    )
