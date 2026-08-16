"""Integration boundaries for transaction evidence and recovery helpers."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root
from src.test.install_global_skills_cases import add_skill
from src.test.install_global_skills_cases import tree_snapshot


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import global_skills_inventory as inventory  # noqa: E402
import global_skills_state as state  # noqa: E402
import global_skills_transaction as transaction  # noqa: E402


def test_path_snapshot_and_rollback_refusals(tmp_path: Path) -> None:
    regular = tmp_path / "regular"
    regular.write_text("unsafe", encoding="utf-8")
    with pytest.raises(transaction.TransactionError, match="unsafe ancestor"):
        transaction.reject_symlink_ancestors(regular / "skills")
    with pytest.raises(transaction.TransactionError, match="owned symbolic"):
        transaction.raw_link(regular)
    with pytest.raises(transaction.TransactionError, match="symbolic link"):
        transaction.link_snapshot(regular)

    target = tmp_path / "target"
    target.mkdir()
    relative = tmp_path / "relative"
    relative.symlink_to("target")
    assert transaction.resolved_link(relative) == target
    _, raw = transaction.link_snapshot(relative)
    with pytest.raises(transaction.TransactionError, match="changed"):
        transaction.require_snapshot(relative, (0, 0), raw)

    backup = tmp_path / "backup"
    backup.symlink_to(target)
    backup_identity, backup_raw = transaction.link_snapshot(backup)
    occupied = transaction.AppliedChange(
        "remove",
        relative,
        backup_raw,
        None,
        backup=backup,
        old_identity=backup_identity,
    )
    with pytest.raises(transaction.TransactionError, match="occupied"):
        transaction.restore(occupied)
    for operation in (
        transaction.restore,
        transaction.cleanup_backup,
        transaction.remove_new,
    ):
        with pytest.raises(transaction.TransactionError, match="incomplete"):
            operation(
                transaction.AppliedChange(
                    "create", tmp_path / operation.__name__, None, None
                )
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


def test_reserved_case_source_and_container_guards(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, state.STATE_NAME)
    request = inventory.build_inventory(
        (repository,), tmp_path / "destination"
    )
    with pytest.raises(transaction.TransactionError, match="reserved"):
        transaction.plan("codex", request)

    repository = tmp_path / "case-repository"
    add_skill(repository, "Skill")
    root = tmp_path / "skills"
    root.mkdir()
    (root / "skill").mkdir()
    request = inventory.build_inventory((repository,), root)
    with pytest.raises(transaction.TransactionError, match="case-colliding"):
        transaction.plan("codex", request)

    repository = tmp_path / "changed-repository"
    skill = add_skill(repository, "skill", "# One\n")
    request = inventory.build_inventory(
        (repository,), tmp_path / "parent" / "skills"
    )
    record = request.skills[0]
    (skill / "SKILL.md").write_text("# Two\n", encoding="utf-8")
    with pytest.raises(transaction.TransactionError, match="source skill"):
        transaction.validate_skill(record)
    (skill / "SKILL.md").unlink()
    marker = tmp_path / "marker"
    marker.write_text("# Marker\n", encoding="utf-8")
    (skill / "SKILL.md").symlink_to(marker)
    with pytest.raises(transaction.TransactionError, match="source skill"):
        transaction.validate_skill(record)

    containers = transaction.create_destination(request.destination)
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


def test_destination_container_reconciliation_preserves_foreign_entries(
    tmp_path: Path,
) -> None:
    staged = tmp_path / "staged"
    staged.mkdir(mode=0o700)
    expected = state.created_container_identity(staged)
    destination = tmp_path / "destination"
    assert (
        transaction.cleanup_uncertain_container_install(
            staged, destination, expected
        )
        == ()
    )
    assert not staged.exists()

    assert transaction.cleanup_uncertain_container_install(
        staged, destination, expected
    ) == (destination.name,)

    foreign = tmp_path / "foreign"
    foreign.mkdir(mode=0o700)
    assert transaction.cleanup_uncertain_container_install(
        foreign, destination, expected
    ) == (foreign.name,)
    assert foreign.is_dir()

    foreign_destination = tmp_path / "foreign-destination"
    foreign_destination.mkdir(mode=0o700)
    assert transaction.cleanup_uncertain_container_install(
        staged, foreign_destination, expected
    ) == (foreign_destination.name,)
    assert foreign_destination.is_dir()

    occupied = tmp_path / "occupied"
    occupied.mkdir(mode=0o700)
    occupied_identity = state.created_container_identity(occupied)
    (occupied / "preserve").write_text("user data\n", encoding="utf-8")
    assert transaction.cleanup_uncertain_container_install(
        staged, occupied, occupied_identity
    ) == (occupied.name,)
    assert (occupied / "preserve").read_text(encoding="utf-8") == "user data\n"

    created: list[state.ContainerIdentity] = []
    with pytest.raises(FileExistsError):
        transaction.install_destination_component(occupied, created)
    assert created == []
    assert state.path_identity(occupied) == (
        occupied_identity.device,
        occupied_identity.inode,
    )
    assert list(tmp_path.glob(".occupied.container-*")) == []

    unsafe = tmp_path / "unsafe"
    unsafe.mkdir(mode=0o755)
    with pytest.raises(state.StateError, match="unsafe"):
        state.created_container_identity(unsafe)


def test_destination_creation_rolls_back_post_install_identity_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "skills"
    original_identity = transaction.created_container_identity

    def drift_after_install(path: Path) -> state.ContainerIdentity:
        observed = original_identity(path)
        if path == destination:
            return state.ContainerIdentity(
                observed.path,
                observed.device,
                observed.inode + 1,
                observed.owner,
                observed.mode,
            )
        return observed

    monkeypatch.setattr(
        transaction, "created_container_identity", drift_after_install
    )
    with pytest.raises(
        transaction.TransactionError,
        match="created destination component changed",
    ):
        transaction.create_destination(destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".skills.container-*")) == []


def test_locked_refresh_cleanup_and_uninstall_preflight_branches(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill = add_skill(repository, "skill", "# One\n")
    root = tmp_path / "skills"
    request = inventory.build_inventory((repository,), root)
    initial = transaction.plan("codex", request)
    (skill / "SKILL.md").write_text("# Two\n", encoding="utf-8")
    with pytest.raises(transaction.TransactionError, match="source inventory"):
        transaction.locked_plan("codex", request, initial)

    missing = tmp_path / "missing"
    with pytest.raises(transaction.TransactionError, match="state is absent"):
        transaction.uninstall_preflight("codex", missing)
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(transaction.TransactionError, match="state is absent"):
        transaction.uninstall_preflight("codex", empty)
    (empty / state.LOCK_NAME).mkdir()
    with pytest.raises(transaction.TransactionError, match="already active"):
        transaction.uninstall_preflight("codex", empty)

    target = tmp_path / "target"
    target.mkdir()
    backup = tmp_path / "backup"
    backup.symlink_to(target)
    identity, raw = transaction.link_snapshot(backup)
    complete = transaction.AppliedChange(
        "remove",
        tmp_path / "destination",
        raw,
        None,
        backup=backup,
        old_identity=identity,
    )
    skipped = transaction.AppliedChange(
        "create", tmp_path / "skipped", None, str(target)
    )
    assert transaction.cleanup_changes((skipped, complete), "test") == []
    assert not backup.exists()
    incomplete_backup = tmp_path / "incomplete-backup"
    incomplete_backup.symlink_to(target)
    warnings = transaction.cleanup_changes(
        (
            transaction.AppliedChange(
                "remove",
                tmp_path / "incomplete",
                None,
                None,
                backup=incomplete_backup,
            ),
        ),
        "test",
    )
    assert len(warnings) == 1


def test_real_transaction_rolls_back_create_replace_and_remove(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old_replace = add_skill(repository, "old/m-replace")
    old_remove = add_skill(repository, "old/z-remove")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    before = tree_snapshot(root)

    (old_replace / "SKILL.md").unlink()
    (old_remove / "SKILL.md").unlink()
    add_skill(repository, "new/a-create")
    add_skill(repository, "new/m-replace")
    requested = inventory.build_inventory((repository,), root)

    def fail_state(*_arguments: object) -> None:
        raise OSError("injected pre-commit failure")

    monkeypatch.setattr(transaction, "write_state", fail_state)
    with pytest.raises(OSError, match="injected pre-commit"):
        transaction.apply("codex", requested)

    assert tree_snapshot(root) == before


def test_apply_preserves_intervening_same_target_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    target = add_skill(repository, "alpha")
    root = tmp_path / "skills"
    requested = inventory.build_inventory((repository,), root)
    original = transaction.os.link

    def race(
        source: Path,
        destination: Path,
        *,
        follow_symlinks: bool,
    ) -> None:
        if destination.name == "alpha":
            destination.symlink_to(target)
        original(
            source,
            destination,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(transaction.os, "link", race)
    with pytest.raises(
        transaction.TransactionError, match="destination cleanup was incomplete"
    ):
        transaction.apply("codex", requested)

    assert (root / "alpha").is_symlink()
    assert (root / "alpha").resolve() == target
    assert not (root / state.STATE_NAME).exists()


def test_atomic_link_and_rollback_stage_noop_boundaries(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    destination = tmp_path / "installed"
    identity = transaction.atomic_symlink(destination, str(target))
    assert transaction.link_snapshot(destination) == (identity, str(target))

    change = transaction.AppliedChange(
        "create",
        destination,
        None,
        str(target),
        new_identity=identity,
        stage=transaction.ChangeStage.NEW_INSTALLED,
    )
    transaction.remove_new(change)
    transaction.remove_new(change)

    transaction.rollback(
        (
            transaction.AppliedChange(
                "create",
                tmp_path / "planned",
                None,
                None,
                stage=transaction.ChangeStage.PLANNED,
            ),
            transaction.AppliedChange(
                "create",
                tmp_path / "committed",
                None,
                None,
                stage=transaction.ChangeStage.STATE_COMMITTED,
            ),
        )
    )
