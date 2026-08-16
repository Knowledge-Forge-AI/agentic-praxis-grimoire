"""Unit contracts for global-skill transaction planning."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root
from src.test.install_global_skills_cases import add_skill


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import global_skills_inventory as inventory  # noqa: E402
import global_skills_state as state  # noqa: E402
import global_skills_transaction as transaction  # noqa: E402


def test_plan_is_stable_after_apply_and_apply_is_byte_idempotent(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "alpha")
    root = tmp_path / "skills"
    requested = inventory.build_inventory((repository,), root)

    first = transaction.apply("codex", requested)
    state_path = root / state.STATE_NAME
    before = (state_path.stat().st_ino, state_path.read_bytes())
    current = transaction.plan("codex", requested)
    second = transaction.apply("codex", requested)
    after = (state_path.stat().st_ino, state_path.read_bytes())

    assert first.changed
    assert not current.changed
    assert not second.changed
    assert before == after


def test_plan_orders_remove_replace_and_create_by_skill_name(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    old = add_skill(repository, "old/remove")
    shared = add_skill(repository, "old/shared")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    (old / "SKILL.md").unlink()
    (shared / "SKILL.md").unlink()
    add_skill(repository, "new/shared")
    add_skill(repository, "new/add")

    planned = transaction.plan(
        "codex", inventory.build_inventory((repository,), root)
    )

    assert [(action.kind, action.name) for action in planned.actions] == [
        ("create", "add"),
        ("replace", "shared"),
        ("remove", "remove"),
    ]


def test_path_link_and_reserved_metadata_guards(tmp_path: Path) -> None:
    file_ancestor = tmp_path / "file"
    file_ancestor.write_text("not a directory", encoding="utf-8")
    with pytest.raises(transaction.TransactionError, match="unsafe ancestor"):
        transaction.reject_symlink_ancestors(file_ancestor / "skills")
    with pytest.raises(transaction.TransactionError, match="symbolic link"):
        transaction.raw_link(file_ancestor)
    with pytest.raises(transaction.TransactionError, match="symbolic link"):
        transaction.link_snapshot(file_ancestor)

    target = tmp_path / "target"
    target.mkdir()
    relative = tmp_path / "relative"
    relative.symlink_to("target")
    assert transaction.resolved_link(relative) == target

    repository = tmp_path / "repository"
    add_skill(repository, state.STATE_NAME)
    request = inventory.build_inventory(
        (repository,), tmp_path / "destination"
    )
    with pytest.raises(transaction.TransactionError, match="reserved"):
        transaction.plan("codex", request)

    alternate = tmp_path / "alternate"
    add_skill(alternate, state.STATE_NAME.upper())
    request = inventory.build_inventory(
        (alternate,), tmp_path / "alternate-destination"
    )
    with pytest.raises(transaction.TransactionError, match="reserved"):
        transaction.plan("codex", request)


def test_quarantine_does_not_overwrite_backup_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)
    identity, raw = transaction.link_snapshot(link)
    collision = tmp_path / "collision"
    collision.write_text("preserve\n", encoding="utf-8")
    monkeypatch.setattr(
        transaction, "unique_sibling", lambda _path, _label: collision
    )

    with pytest.raises(FileExistsError):
        transaction.quarantine(link, identity, raw)
    assert link.resolve() == target
    assert collision.read_text(encoding="utf-8") == "preserve\n"



def test_plan_refuses_case_shape_and_unsafe_destination_types(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "Skill")
    root = tmp_path / "skills"
    root.mkdir()
    (root / "skill").mkdir()
    request = inventory.build_inventory((repository,), root)
    with pytest.raises(transaction.TransactionError, match="case-colliding"):
        transaction.plan("codex", request)

    unsafe = tmp_path / "unsafe"
    unsafe.write_text("regular", encoding="utf-8")
    request = inventory.build_inventory((repository,), unsafe)
    with pytest.raises(transaction.TransactionError, match="unsafe ancestor"):
        transaction.plan("codex", request)


def test_snapshot_restore_cleanup_and_rollback_guards(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target)
    identity, raw = transaction.link_snapshot(link)
    with pytest.raises(transaction.TransactionError, match="changed"):
        transaction.require_snapshot(link, (0, 0), raw)

    backup = tmp_path / "backup"
    backup.symlink_to(target)
    backup_identity, backup_raw = transaction.link_snapshot(backup)
    occupied = transaction.AppliedChange(
        "remove",
        link,
        backup_raw,
        None,
        backup=backup,
        old_identity=backup_identity,
    )
    with pytest.raises(transaction.TransactionError, match="occupied"):
        transaction.restore(occupied)
    with pytest.raises(transaction.TransactionError, match="incomplete"):
        transaction.restore(
            transaction.AppliedChange("remove", link, None, None)
        )
    with pytest.raises(transaction.TransactionError, match="incomplete"):
        transaction.cleanup_backup(
            transaction.AppliedChange("remove", link, None, None)
        )
    with pytest.raises(transaction.TransactionError, match="incomplete"):
        transaction.remove_new(
            transaction.AppliedChange("create", link, None, None)
        )

    incomplete = [
        transaction.AppliedChange(
            "create",
            tmp_path / "one",
            None,
            None,
            stage=transaction.ChangeStage.NEW_INSTALLED,
        ),
        transaction.AppliedChange(
            "replace",
            tmp_path / "two",
            None,
            None,
            stage=transaction.ChangeStage.OLD_QUARANTINED,
        ),
        transaction.AppliedChange(
            "remove",
            tmp_path / "three",
            None,
            None,
            stage=transaction.ChangeStage.OLD_QUARANTINED,
        ),
    ]
    with pytest.raises(transaction.TransactionError, match="three, two, one"):
        transaction.rollback(incomplete)


def test_source_validation_and_container_identity_cleanup(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill = add_skill(repository, "skill", "# One\n")
    request = inventory.build_inventory(
        (repository,), tmp_path / "parent" / "skills"
    )
    record = request.skills[0]
    (skill / "SKILL.md").write_text("# Two\n", encoding="utf-8")
    with pytest.raises(transaction.TransactionError, match="source skill"):
        transaction.validate_skill(record)

    marker = skill / "SKILL.md"
    marker.unlink()
    target = tmp_path / "marker"
    target.write_text("# Link\n", encoding="utf-8")
    marker.symlink_to(target)
    with pytest.raises(transaction.TransactionError, match="source skill"):
        transaction.validate_skill(record)

    containers = transaction.create_destination(request.destination)
    assert request.destination.is_dir()
    wrong = state.ContainerIdentity(
        containers[-1].path,
        containers[-1].device,
        containers[-1].inode + 1,
        containers[-1].owner,
        containers[-1].mode,
    )
    transaction.remove_empty_containers((wrong,))
    assert request.destination.is_dir()
    transaction.remove_empty_containers(containers)
    assert not request.destination.exists()


def test_missing_stale_link_is_state_only_drift(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    skill = add_skill(repository, "skill")
    add_skill(repository, "keep")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    (root / "skill").unlink()
    (skill / "SKILL.md").unlink()

    planned = transaction.plan(
        "codex", inventory.build_inventory((repository,), root)
    )

    assert planned.changed
    assert planned.actions == ()
    assert planned.unchanged == 1


def test_partial_destination_creation_is_rolled_back_for_errors_and_interrupts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")

    cases = (
        (2, OSError("injected after first directory")),
        (3, OSError("injected after second directory")),
        (2, PermissionError("injected permission failure")),
        (2, KeyboardInterrupt()),
    )
    for fail_call, failure in cases:
        label = f"{failure.__class__.__name__}-{fail_call}"
        root = tmp_path / label / "one" / "two" / "skills"
        request = inventory.build_inventory((repository,), root)
        original_mkdir = Path.mkdir
        calls = 0

        def fail_second(
            path: Path,
            mode: int = 0o777,
            parents: bool = False,
            exist_ok: bool = False,
        ) -> None:
            nonlocal calls
            calls += 1
            if calls == fail_call:
                raise failure
            original_mkdir(
                path, mode=mode, parents=parents, exist_ok=exist_ok
            )

        monkeypatch.setattr(Path, "mkdir", fail_second)
        with pytest.raises(failure.__class__, match="injected" if str(failure) else None):
            transaction.apply("codex", request)
        assert not (tmp_path / label).exists()
        monkeypatch.undo()


def test_post_mkdir_identity_failure_rolls_back_created_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    base = tmp_path / "destination"
    root = base / "one" / "two" / "skills"
    request = inventory.build_inventory((repository,), root)
    original_lstat = Path.lstat

    def fail_after_mkdir(path: Path) -> os.stat_result:
        if path == base and path.exists():
            raise OSError("injected post-mkdir identity failure")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_after_mkdir)
    with pytest.raises(OSError, match="post-mkdir identity failure"):
        transaction.apply("codex", request)
    assert not base.exists()


def test_post_mkdir_descriptor_acquisition_failures_roll_back_created_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")

    for boundary, failure in (
        ("stat-error", OSError("injected post-mkdir stat failure")),
        ("stat-interrupt", KeyboardInterrupt()),
        ("open-error", OSError("injected post-mkdir open failure")),
        ("open-interrupt", KeyboardInterrupt()),
        ("fstat-error", OSError("injected post-mkdir fstat failure")),
        ("fstat-interrupt", KeyboardInterrupt()),
    ):
        base = tmp_path / boundary
        root = base / "one" / "two" / "skills"
        request = inventory.build_inventory((repository,), root)
        original_open = transaction.os.open
        original_fstat = transaction.os.fstat
        original_stat = transaction.os.stat
        destination_descriptor: int | None = None

        def fail_stat(
            path: os.PathLike[str] | str,
            *,
            dir_fd: int | None = None,
            follow_symlinks: bool = True,
        ) -> os.stat_result:
            if Path(path) == base and boundary.startswith("stat"):
                raise failure
            return original_stat(
                path,
                dir_fd=dir_fd,
                follow_symlinks=follow_symlinks,
            )

        def fail_open(
            path: os.PathLike[str] | str,
            flags: int,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> int:
            nonlocal destination_descriptor
            if Path(path) == base and boundary.startswith("open"):
                raise failure
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if Path(path) == base:
                destination_descriptor = descriptor
            return descriptor

        def fail_fstat(descriptor: int) -> os.stat_result:
            if descriptor == destination_descriptor:
                raise failure
            return original_fstat(descriptor)

        monkeypatch.setattr(transaction.os, "open", fail_open)
        monkeypatch.setattr(transaction.os, "stat", fail_stat)
        if boundary.startswith("fstat"):
            monkeypatch.setattr(transaction.os, "fstat", fail_fstat)
        with pytest.raises(
            failure.__class__,
            match="post-mkdir" if str(failure) else None,
        ):
            transaction.apply("codex", request)
        monkeypatch.undo()
        assert not base.exists()


def test_pre_capture_replacement_is_never_adopted_for_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "destination"
    root = base / "one" / "skills"
    original_stat = transaction.os.stat
    original_open = transaction.os.open
    replacement_identity: tuple[int, int] | None = None

    def replace_before_capture(
        path: os.PathLike[str] | str,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal replacement_identity
        if Path(path) == base and replacement_identity is None:
            base.rmdir()
            base.mkdir()
            metadata = original_stat(base, follow_symlinks=False)
            replacement_identity = (metadata.st_dev, metadata.st_ino)
            return metadata
        return original_stat(
            path,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )

    def fail_after_capture(
        path: os.PathLike[str] | str,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if Path(path) == base and replacement_identity is not None:
            raise OSError("injected open failure after replacement capture")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(transaction.os, "stat", replace_before_capture)
    monkeypatch.setattr(transaction.os, "open", fail_after_capture)
    with pytest.raises(
        transaction.TransactionError, match="cleanup was incomplete"
    ):
        transaction.create_destination(root)
    monkeypatch.undo()
    assert replacement_identity is not None
    assert base.exists()
    assert state.path_identity(base) == replacement_identity


def test_post_rename_interruption_removes_only_installed_staged_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for failure in (
        OSError("injected post-rename failure"),
        KeyboardInterrupt(),
    ):
        repository = tmp_path / failure.__class__.__name__ / "repository"
        add_skill(repository, "skill")
        base = tmp_path / failure.__class__.__name__ / "destination"
        root = base / "one" / "skills"
        request = inventory.build_inventory((repository,), root)
        original_rename = transaction.rename_directory_no_replace

        def interrupt_after_rename(
            source: Path, destination: Path
        ) -> None:
            original_rename(source, destination)
            raise failure

        monkeypatch.setattr(
            transaction,
            "rename_directory_no_replace",
            interrupt_after_rename,
        )
        with pytest.raises(
            failure.__class__,
            match="post-rename" if str(failure) else None,
        ):
            transaction.apply("codex", request)
        monkeypatch.undo()
        assert not base.exists()


def test_post_rename_pre_journal_interruption_reconciles_staged_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    base = tmp_path / "destination"
    root = base / "one" / "skills"
    request = inventory.build_inventory((repository,), root)
    original_identity = transaction.ContainerIdentity

    def interrupt_final_journal(
        path: str,
        device: int,
        inode: int,
        owner: int,
        mode: int,
    ) -> state.ContainerIdentity:
        if Path(path) == base:
            raise KeyboardInterrupt
        return original_identity(path, device, inode, owner, mode)

    monkeypatch.setattr(
        transaction, "ContainerIdentity", interrupt_final_journal
    )
    with pytest.raises(KeyboardInterrupt):
        transaction.apply("codex", request)
    monkeypatch.undo()
    assert not base.exists()


def test_partial_destination_cleanup_preserves_changed_or_nonempty_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")

    for mode in ("changed", "nonempty"):
        base = tmp_path / mode
        root = base / "one" / "two" / "skills"
        request = inventory.build_inventory((repository,), root)
        original_mkdir = Path.mkdir
        first: Path | None = None
        calls = 0

        def fail_second(
            path: Path,
            mode_bits: int = 0o777,
            parents: bool = False,
            exist_ok: bool = False,
            **kwargs: object,
        ) -> None:
            nonlocal calls, first
            calls += 1
            if calls == 1:
                original_mkdir(
                    path,
                    mode=kwargs.get("mode", mode_bits),
                    parents=parents,
                    exist_ok=exist_ok,
                )
                first = path
                return
            assert first is not None
            if mode == "changed":
                base.rmdir()
                original_mkdir(base)
            else:
                (base / "preserve").write_text(
                    "user data\n", encoding="utf-8"
                )
            raise OSError("injected creation failure")

        monkeypatch.setattr(Path, "mkdir", fail_second)
        with pytest.raises(Exception) as captured:
            transaction.apply("codex", request)
        assert "injected creation failure" in (
            str(captured.value) + str(captured.value.__cause__)
        )
        assert first is not None and base.is_dir()
        if mode == "nonempty":
            assert (base / "preserve").read_text(encoding="utf-8") == "user data\n"
        monkeypatch.undo()


def test_pre_quarantine_failure_preserves_original_error_and_old_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old = add_skill(repository, "old/shared")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    (old / "SKILL.md").unlink()
    add_skill(repository, "new/shared")

    def fail_move(*_arguments: object) -> None:
        raise OSError("injected quarantine failure")

    monkeypatch.setattr(transaction, "no_overwrite_move", fail_move)
    with pytest.raises(OSError, match="injected quarantine failure"):
        transaction.apply(
            "codex", inventory.build_inventory((repository,), root)
        )
    assert (root / "shared").resolve() == old


def test_source_identity_revalidation_rejects_same_marker_replacements(
    tmp_path: Path,
) -> None:
    mutators = ("skill-symlink", "skill-directory", "skills-root", "repository")
    for mutation in mutators:
        case = tmp_path / mutation
        repository = case / "repository"
        skill = add_skill(repository, "skill", "# Same\n")
        record = inventory.build_inventory(
            (repository,), case / "destination"
        ).skills[0]
        replacement = case / "replacement"
        replacement.mkdir(parents=True)
        (replacement / "SKILL.md").write_text("# Same\n", encoding="utf-8")

        if mutation == "skill-symlink":
            moved = case / "moved-skill"
            skill.rename(moved)
            skill.symlink_to(replacement, target_is_directory=True)
        elif mutation == "skill-directory":
            moved = case / "moved-skill"
            skill.rename(moved)
            replacement.rename(skill)
        elif mutation == "skills-root":
            skills_root = repository / "skills"
            skills_root.rename(case / "old-skills")
            new_skill = repository / "skills" / "skill"
            new_skill.mkdir(parents=True)
            (new_skill / "SKILL.md").write_text("# Same\n", encoding="utf-8")
        else:
            repository.rename(case / "old-repository")
            new_skill = repository / "skills" / "skill"
            new_skill.mkdir(parents=True)
            (new_skill / "SKILL.md").write_text("# Same\n", encoding="utf-8")

        with pytest.raises(transaction.TransactionError, match="source skill changed"):
            transaction.validate_skill(record)


def test_replacement_interruption_after_quarantine_restores_old_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old = add_skill(repository, "old/shared")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    (old / "SKILL.md").unlink()
    add_skill(repository, "new/shared")
    original_quarantine = transaction.quarantine

    def interrupt_after_quarantine(*arguments: object, **keywords: object) -> Path:
        original_quarantine(*arguments, **keywords)
        raise KeyboardInterrupt

    monkeypatch.setattr(transaction, "quarantine", interrupt_after_quarantine)
    with pytest.raises(KeyboardInterrupt):
        transaction.apply(
            "codex", inventory.build_inventory((repository,), root)
        )
    assert (root / "shared").resolve() == old


def test_replacement_backup_collision_is_pre_mutation_and_preserves_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old = add_skill(repository, "old/shared")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    (old / "SKILL.md").unlink()
    add_skill(repository, "new/shared")
    collision = root / ".shared.rollback-collision"
    collision.write_text("preserve\n", encoding="utf-8")
    monkeypatch.setattr(
        transaction,
        "unique_sibling",
        lambda _path, _label: collision,
    )

    with pytest.raises(FileExistsError):
        transaction.apply(
            "codex", inventory.build_inventory((repository,), root)
        )
    assert (root / "shared").resolve() == old
    assert collision.read_text(encoding="utf-8") == "preserve\n"


def test_replacement_link_failure_restores_old_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old = add_skill(repository, "old/shared")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    (old / "SKILL.md").unlink()
    add_skill(repository, "new/shared")
    original_link = transaction.os.link

    def fail_install(
        source: Path,
        destination: Path,
        *,
        follow_symlinks: bool,
    ) -> None:
        if destination.name == "shared" and ".install-" in source.name:
            raise OSError("injected new-link failure")
        original_link(
            source, destination, follow_symlinks=follow_symlinks
        )

    monkeypatch.setattr(transaction.os, "link", fail_install)
    with pytest.raises(OSError, match="injected new-link failure"):
        transaction.apply(
            "codex", inventory.build_inventory((repository,), root)
        )
    assert (root / "shared").resolve() == old


def test_second_replacement_failure_rolls_back_first_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old_a = add_skill(repository, "old/a")
    old_b = add_skill(repository, "old/b")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    before = {
        name: (root / name).resolve()
        for name in ("a", "b")
    }
    (old_a / "SKILL.md").unlink()
    (old_b / "SKILL.md").unlink()
    add_skill(repository, "new/a")
    add_skill(repository, "new/b")
    original_link = transaction.os.link

    def fail_second(
        source: Path,
        destination: Path,
        *,
        follow_symlinks: bool,
    ) -> None:
        if destination.name == "b" and ".install-" in source.name:
            raise OSError("injected second replacement failure")
        original_link(
            source, destination, follow_symlinks=follow_symlinks
        )

    monkeypatch.setattr(transaction.os, "link", fail_second)
    with pytest.raises(OSError, match="injected second replacement failure"):
        transaction.apply(
            "codex", inventory.build_inventory((repository,), root)
        )
    assert {
        name: (root / name).resolve()
        for name in ("a", "b")
    } == before


def test_source_replacement_is_detected_inside_link_and_state_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for boundary in ("link", "state"):
        case = tmp_path / boundary
        repository = case / "repository"
        skill = add_skill(repository, "skill", "# Same\n")
        root = case / "destination"
        requested = inventory.build_inventory((repository,), root)

        def replace_source() -> None:
            moved = case / "moved"
            skill.rename(moved)
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "# Same\n", encoding="utf-8"
            )

        if boundary == "link":
            original_atomic = transaction.atomic_symlink

            def race_link(
                destination: Path,
                target: str,
                register: object = None,
                validate: object = None,
            ) -> tuple[int, int]:
                replace_source()
                return original_atomic(
                    destination,
                    target,
                    register,  # type: ignore[arg-type]
                    validate,  # type: ignore[arg-type]
                )

            monkeypatch.setattr(
                transaction, "atomic_symlink", race_link
            )
        else:
            original_write = transaction.write_state

            def race_state(
                destination: Path,
                value: state.InstallState,
                expected: state.LoadedState | None,
                validate: object = None,
                committed: object = None,
            ) -> str | None:
                replace_source()
                return original_write(
                    destination,
                    value,
                    expected,
                    validate,  # type: ignore[arg-type]
                    committed,  # type: ignore[arg-type]
                )

            monkeypatch.setattr(transaction, "write_state", race_state)

        with pytest.raises(
            transaction.TransactionError, match="source skill changed"
        ):
            transaction.apply("codex", requested)
        assert not (root / "skill").exists()
        assert not (root / state.STATE_NAME).exists()
        monkeypatch.undo()


def test_marker_path_replacement_after_open_is_rejected_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    skill = add_skill(repository, "skill", "# Same\n")
    marker = skill / "SKILL.md"
    payload = marker.read_bytes()
    root = tmp_path / "destination"
    requested = inventory.build_inventory((repository,), root)
    saved = tmp_path / "opened-marker"
    original_open = inventory.os.open

    def replace_after_open(
        path: os.PathLike[str] | str,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        candidate = Path(path)
        if candidate != marker:
            return original_open(path, flags, mode, dir_fd=dir_fd)
        if saved.exists():
            marker.unlink()
            saved.rename(marker)
        descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
        marker.rename(saved)
        marker.write_bytes(payload)
        return descriptor

    monkeypatch.setattr(inventory.os, "open", replace_after_open)
    with pytest.raises(
        (inventory.InventoryError, transaction.TransactionError),
        match="source skill marker changed|source skill changed",
    ):
        transaction.apply("codex", requested)
    assert not (root / "skill").exists()
    assert not (root / state.STATE_NAME).exists()


def test_state_commit_is_acknowledged_before_write_state_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    target = add_skill(repository, "skill")
    root = tmp_path / "destination"
    requested = inventory.build_inventory((repository,), root)
    original_write = transaction.write_state

    def interrupt_after_commit(*args: object, **kwargs: object) -> str | None:
        original_write(*args, **kwargs)
        raise KeyboardInterrupt

    monkeypatch.setattr(transaction, "write_state", interrupt_after_commit)
    with pytest.raises(KeyboardInterrupt):
        transaction.apply("codex", requested)
    assert (root / "skill").resolve() == target
    assert state.load_state(root, "codex") is not None
