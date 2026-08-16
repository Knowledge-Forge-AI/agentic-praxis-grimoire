"""Unit contracts for global-skill ownership state and transactions."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace

import pytest

from src.test.apg_test_support import repository_root
from src.test.install_global_skills_cases import add_skill


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import global_skills_inventory as inventory  # noqa: E402
import global_skills_state as state  # noqa: E402
import global_skills_transaction as transaction  # noqa: E402
import apg_user_skills  # noqa: E402


def desired_state(tmp_path: Path) -> tuple[Path, state.InstallState]:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    root = tmp_path / "skills"
    discovered = inventory.build_inventory((repository,), root)
    return root, state.from_inventory("codex", discovered, ())


def test_state_round_trip_is_closed_canonical_private_and_single_linked(
    tmp_path: Path,
) -> None:
    root, expected = desired_state(tmp_path)
    root.mkdir()
    state.write_state(root, expected, None)
    loaded = state.load_state(root, "codex")
    assert loaded is not None
    assert loaded.state == expected
    metadata = (root / state.STATE_NAME).stat()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    assert metadata.st_nlink == 1
    assert loaded.payload.endswith(b"\n")


def test_state_rejects_symlink_hardlink_open_schema_and_wrong_agent(
    tmp_path: Path,
) -> None:
    root, expected = desired_state(tmp_path)
    root.mkdir()
    path = root / state.STATE_NAME
    target = tmp_path / "target"
    target.write_text("{}\n", encoding="utf-8")
    path.symlink_to(target)
    with pytest.raises(state.StateError, match="unsafe"):
        state.load_state(root, "codex")
    path.unlink()
    state.write_state(root, expected, None)
    with pytest.raises(state.StateError, match="agent"):
        state.load_state(root, "claude")
    hardlink = tmp_path / "hardlink"
    os.link(path, hardlink)
    with pytest.raises(state.StateError, match="unsafe"):
        state.load_state(root, "codex")
    hardlink.unlink()
    path.write_text('{"schema_version":1,"extra":true}\n', encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(state.StateError, match="schema"):
        state.load_state(root, "codex")


def test_state_parser_rejects_closed_schema_and_identity_variants(
    tmp_path: Path,
) -> None:
    root, expected = desired_state(tmp_path)
    valid = json.loads(state.serialize_state(expected))

    variants: list[tuple[str, object]] = []

    def changed(**members: object) -> dict[str, object]:
        document = dict(valid)
        document.update(members)
        return document

    variants.extend(
        [
            ("schema", {}),
            ("owner", changed(owner="another-owner")),
            ("agent", changed(agent="claude")),
            ("destination", changed(skills_root=str(tmp_path / "other"))),
            ("generation", changed(generation=0)),
            ("generation", changed(installation_id="invalid")),
            ("links", changed(links={})),
            ("links", changed(links={"bad/name": "/tmp/source"})),
            ("link target", changed(links={"skill": "relative"})),
            ("skill hashes", changed(skill_hashes={"skill": "invalid"})),
            ("differ", changed(skill_hashes={"other": "a" * 64})),
            ("sources", changed(sources=[])),
            (
                "source schema",
                changed(sources=[{"repository_root": "/tmp"}]),
            ),
            (
                "repository root",
                changed(
                    sources=[
                        {
                            "repository_root": "relative",
                            "skills_root": "/tmp/skills",
                        }
                    ]
                ),
            ),
            (
                "not canonical",
                changed(
                    sources=[
                        {
                            "repository_root": "/tmp/../tmp/repository",
                            "skills_root": "/tmp/skills",
                        }
                    ]
                ),
            ),
            (
                "duplicated",
                changed(sources=[valid["sources"][0], valid["sources"][0]]),
            ),
            ("containers", changed(created_containers="wrong")),
            (
                "container schema",
                changed(created_containers=[{"path": "/tmp"}]),
            ),
            (
                "container identity",
                changed(
                    created_containers=[
                        {
                            "device": -1,
                            "inode": 1,
                            "mode": 0o755,
                            "owner": 1,
                            "path": "/tmp/container",
                        }
                    ]
                ),
            ),
        ]
    )
    for message, document in variants:
        payload = json.dumps(
            document, separators=(",", ":"), sort_keys=True
        ).encode()
        with pytest.raises(state.StateError, match=message):
            state.parse_state(payload, "codex", root)

    with pytest.raises(state.StateError, match="valid JSON"):
        state.parse_state(b"\xff", "codex", root)
    with pytest.raises(state.StateError, match="valid JSON"):
        state.parse_state(
            b'{"schema_version":1,"schema_version":1}',
            "codex",
            root,
        )


def test_state_parser_rejects_unsorted_sources_and_containers(
    tmp_path: Path,
) -> None:
    root, expected = desired_state(tmp_path)
    valid = json.loads(state.serialize_state(expected))
    second = {
        "repository_root": "/000",
        "skills_root": "/000/skills",
    }
    valid["sources"] = [valid["sources"][0], second]
    with pytest.raises(state.StateError, match="not canonical"):
        state.parse_state(
            json.dumps(valid, separators=(",", ":"), sort_keys=True).encode(),
            "codex",
            root,
        )

    valid = json.loads(state.serialize_state(expected))
    valid["created_containers"] = [
        {
            "device": 1,
            "inode": 1,
            "mode": 0o755,
            "owner": 1,
            "path": "/longer/path",
        },
        {
            "device": 1,
            "inode": 2,
            "mode": 0o755,
            "owner": 1,
            "path": "/short",
        },
    ]
    with pytest.raises(state.StateError, match="not canonical"):
        state.parse_state(
            json.dumps(valid, separators=(",", ":"), sort_keys=True).encode(),
            "codex",
            root,
        )


def test_state_parser_rejects_container_chain_outside_destination(
    tmp_path: Path,
) -> None:
    root, expected = desired_state(tmp_path)
    document = json.loads(state.serialize_state(expected))
    victim = tmp_path / "unrelated-empty-directory"
    victim.mkdir()
    metadata = victim.lstat()
    document["created_containers"] = [
        {
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode),
            "owner": metadata.st_uid,
            "path": str(victim),
        }
    ]

    with pytest.raises(state.StateError, match="outside the skills-root chain"):
        state.parse_state(
            json.dumps(
                document, separators=(",", ":"), sort_keys=True
            ).encode(),
            "codex",
            root,
        )
    assert victim.is_dir()


def test_state_create_does_not_overwrite_intervening_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, expected = desired_state(tmp_path)
    root.mkdir()
    destination = root / state.STATE_NAME
    original_link = state.os.link

    def race(source: Path, target: Path, *, follow_symlinks: bool) -> None:
        destination.write_text("unmanaged\n", encoding="utf-8")
        original_link(source, target, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(state.os, "link", race)
    with pytest.raises(FileExistsError):
        state.write_state(root, expected, None)
    assert destination.read_text(encoding="utf-8") == "unmanaged\n"


def test_state_replacement_does_not_overwrite_backup_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, expected = desired_state(tmp_path)
    root.mkdir()
    state.write_state(root, expected, None)
    loaded = state.load_state(root, "codex")
    assert loaded is not None
    collision = (
        root
        / f".{state.STATE_NAME}.rollback-{os.getpid()}-collision"
    )
    collision.write_text("preserve\n", encoding="utf-8")
    monkeypatch.setattr(state.secrets, "token_hex", lambda _size: "collision")

    with pytest.raises(FileExistsError):
        state.write_state(root, expected, loaded)
    assert collision.read_text(encoding="utf-8") == "preserve\n"
    after = state.load_state(root, "codex")
    assert after is not None and after.payload == loaded.payload


def test_destination_lock_is_exclusive_and_owner_only(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    root.mkdir()
    with state.destination_lock(root):
        lock = root / state.LOCK_NAME
        assert stat.S_IMODE(lock.stat().st_mode) == 0o700
        with pytest.raises(state.StateError, match="active"):
            with state.destination_lock(root):
                pass
    assert not (root / state.LOCK_NAME).exists()


def test_atomic_link_never_overwrites_intervening_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "skill"
    target = tmp_path / "target"
    target.mkdir()
    unmanaged = tmp_path / "unmanaged"
    unmanaged.mkdir()
    original_link = transaction.os.link

    def race(source: Path, output: Path, *, follow_symlinks: bool) -> None:
        destination.symlink_to(unmanaged)
        original_link(source, output, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(transaction.os, "link", race)
    with pytest.raises(FileExistsError):
        transaction.atomic_symlink(destination, str(target))
    assert destination.resolve() == unmanaged.resolve()


def test_apply_rolls_links_back_when_state_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "alpha")
    root = tmp_path / "skills"
    request = inventory.build_inventory((repository,), root)

    def fail_state(*_arguments: object) -> None:
        raise OSError("injected state failure")

    monkeypatch.setattr(transaction, "write_state", fail_state)
    with pytest.raises(OSError, match="injected"):
        transaction.apply("codex", request)
    assert not (root / "alpha").exists()
    assert not (root / state.STATE_NAME).exists()


def test_apply_and_uninstall_roll_back_on_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "alpha")
    root = tmp_path / "skills"
    request = inventory.build_inventory((repository,), root)

    def interrupt_state(*_arguments: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(transaction, "write_state", interrupt_state)
    with pytest.raises(KeyboardInterrupt):
        transaction.apply("codex", request)
    assert not (root / "alpha").exists()
    assert not (root / state.STATE_NAME).exists()

    monkeypatch.undo()
    transaction.apply("codex", request)
    before = (root / state.STATE_NAME).read_bytes()
    monkeypatch.setattr(
        transaction, "quarantine_uninstall_state", interrupt_state
    )
    with pytest.raises(KeyboardInterrupt):
        transaction.uninstall("codex", root)
    assert (root / "alpha").is_symlink()
    assert (root / state.STATE_NAME).read_bytes() == before


def test_interrupt_after_replacement_link_returns_restores_old_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old = add_skill(repository, "old/shared")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    before = (root / state.STATE_NAME).read_bytes()
    (old / "SKILL.md").unlink()
    add_skill(repository, "new/shared")
    requested = inventory.build_inventory((repository,), root)
    original = transaction.atomic_symlink

    def interrupt_after_link(
        destination: Path,
        target: str,
        register: object = None,
        validate: object = None,
    ) -> tuple[int, int]:
        original(
            destination,
            target,
            register,  # type: ignore[arg-type]
            validate,  # type: ignore[arg-type]
        )
        raise KeyboardInterrupt

    monkeypatch.setattr(transaction, "atomic_symlink", interrupt_after_link)
    with pytest.raises(KeyboardInterrupt):
        transaction.apply("codex", requested)

    assert (root / "shared").resolve() == old
    assert (root / state.STATE_NAME).read_bytes() == before
    assert not any("rollback" in entry.name for entry in root.iterdir())


def test_interrupt_after_quarantine_returns_restores_removed_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old = add_skill(repository, "old")
    add_skill(repository, "keep")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    before = (root / state.STATE_NAME).read_bytes()
    (old / "SKILL.md").unlink()
    requested = inventory.build_inventory((repository,), root)
    original = transaction.quarantine

    def interrupt_after_move(
        path: Path,
        identity: tuple[int, int],
        raw_target: str,
        backup: Path | None = None,
        register: object | None = None,
    ) -> Path:
        original(
            path,
            identity,
            raw_target,
            backup,
            register,  # type: ignore[arg-type]
        )
        raise KeyboardInterrupt

    monkeypatch.setattr(transaction, "quarantine", interrupt_after_move)
    with pytest.raises(KeyboardInterrupt):
        transaction.apply("codex", requested)

    assert (root / "old").resolve() == old
    assert (root / state.STATE_NAME).read_bytes() == before
    assert not any("rollback" in entry.name for entry in root.iterdir())


def test_atomic_link_interrupt_during_temporary_cleanup_is_precommit_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "alpha")
    root = tmp_path / "skills"
    requested = inventory.build_inventory((repository,), root)
    original = Path.unlink

    def interrupt_temporary(
        path: Path, missing_ok: bool = False
    ) -> None:
        original(path, missing_ok=missing_ok)
        if path.name.startswith(".alpha.install-"):
            raise KeyboardInterrupt

    monkeypatch.setattr(Path, "unlink", interrupt_temporary)
    with pytest.raises(KeyboardInterrupt):
        transaction.apply("codex", requested)

    assert not (root / "alpha").exists()
    assert not (root / state.STATE_NAME).exists()


def test_no_overwrite_move_interrupt_after_unlink_restores_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("preserve\n", encoding="utf-8")
    identity = state.path_identity(source)
    original = Path.unlink

    def interrupt_source(
        path: Path, missing_ok: bool = False
    ) -> None:
        original(path, missing_ok=missing_ok)
        if path == source:
            raise KeyboardInterrupt

    monkeypatch.setattr(Path, "unlink", interrupt_source)
    with pytest.raises(KeyboardInterrupt):
        state.no_overwrite_move(source, destination, identity)

    assert source.read_text(encoding="utf-8") == "preserve\n"
    assert not destination.exists()


def test_no_overwrite_move_interrupt_after_link_removes_owned_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("preserve\n", encoding="utf-8")
    identity = state.path_identity(source)
    original = state.os.link

    def interrupt_after_link(
        input_path: Path,
        output_path: Path,
        *,
        follow_symlinks: bool,
    ) -> None:
        original(
            input_path,
            output_path,
            follow_symlinks=follow_symlinks,
        )
        raise KeyboardInterrupt

    monkeypatch.setattr(state.os, "link", interrupt_after_link)
    with pytest.raises(KeyboardInterrupt):
        state.no_overwrite_move(source, destination, identity)

    assert source.stat().st_nlink == 1
    assert not destination.exists()


def test_no_overwrite_move_preserves_preexisting_same_inode_collision(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("preserve\n", encoding="utf-8")
    os.link(source, destination)
    identity = state.path_identity(source)

    with pytest.raises(FileExistsError):
        state.no_overwrite_move(source, destination, identity)

    assert state.path_identity(source) == state.path_identity(destination)
    assert source.stat().st_nlink == 2


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


def test_plan_refuses_unmanaged_and_other_command_metadata(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    skill = add_skill(repository, "skill")
    root = tmp_path / "skills"
    root.mkdir()
    (root / "skill").symlink_to(skill)
    request = inventory.build_inventory((repository,), root)
    with pytest.raises(transaction.TransactionError, match="unmanaged"):
        transaction.plan("codex", request)
    (root / "skill").unlink()
    (root / ".flatten-skill-symlinks-state.json").write_text(
        "{}\n", encoding="utf-8"
    )
    with pytest.raises(transaction.TransactionError, match="another command"):
        transaction.plan("codex", request)


def test_check_detects_hash_drift_without_mutation(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    skill = add_skill(repository, "skill", "# One\n")
    root = tmp_path / "skills"
    request = inventory.build_inventory((repository,), root)
    transaction.apply("codex", request)
    before = state.load_state(root, "codex")
    (skill / "SKILL.md").write_text("# Two\n", encoding="utf-8")
    changed = inventory.build_inventory((repository,), root)
    plan = transaction.plan("codex", changed)
    assert plan.changed
    after = state.load_state(root, "codex")
    assert before is not None and after is not None
    assert before.payload == after.payload


def test_separate_apg_user_owner_is_detected_read_only(tmp_path: Path) -> None:
    destination = tmp_path / "skills"
    xdg = tmp_path / "state"
    owner_root = xdg / "agentic-praxis-grimoire"
    owner_root.mkdir(parents=True, mode=0o700)
    source = apg_user_skills.SourceIdentity(
        str(tmp_path / "public"),
        "0.4.0",
        "v0.4.0",
        "a" * 40,
        "b" * 40,
        (("skill", "c" * 64),),
    )
    owner_state = apg_user_skills.State(
        str(destination), source, None, ("skill",), ()
    )
    state_path = owner_root / "user-skills-v1.json"
    state_path.write_bytes(apg_user_skills.serialize_state(owner_state))
    state_path.chmod(0o600)
    lock_path = owner_root / "user-skills-v1.lock"
    lock_path.write_text("", encoding="utf-8")
    lock_path.chmod(0o600)
    before = state_path.read_bytes()
    with pytest.raises(state.StateError, match="separate apg-user-skills"):
        state.check_apg_user_skills_owner(
            destination, {"XDG_STATE_HOME": str(xdg)}
        )
    assert state_path.read_bytes() == before


def test_apg_user_owner_appearing_after_inventory_is_refused(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "skills"
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    requested = inventory.build_inventory((repository,), destination)
    xdg = tmp_path / "state"
    owner_root = xdg / "agentic-praxis-grimoire"
    owner_root.mkdir(parents=True, mode=0o700)
    source = apg_user_skills.SourceIdentity(
        str(tmp_path / "public"),
        "0.4.0",
        "v0.4.0",
        "a" * 40,
        "b" * 40,
        (("skill", "c" * 64),),
    )
    owner_state = apg_user_skills.State(
        str(destination), source, None, ("skill",), ()
    )
    state_path = owner_root / "user-skills-v1.json"
    state_path.write_bytes(apg_user_skills.serialize_state(owner_state))
    state_path.chmod(0o600)
    lock_path = owner_root / "user-skills-v1.lock"
    lock_path.write_text("", encoding="utf-8")
    lock_path.chmod(0o600)

    with pytest.raises(state.StateError, match="separate apg-user-skills"):
        transaction.apply(
            "codex", requested, {"XDG_STATE_HOME": str(xdg)}
        )
    assert not destination.exists()


def test_locked_rebuild_refuses_destination_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    source = add_skill(repository, "skill")
    root = tmp_path / "skills"
    request = inventory.build_inventory((repository,), root)
    original_create = transaction.create_destination

    def race(destination: Path) -> tuple[state.ContainerIdentity, ...]:
        created = original_create(destination)
        (destination / "skill").symlink_to(source)
        return created

    monkeypatch.setattr(transaction, "create_destination", race)
    with pytest.raises(
        transaction.TransactionError, match="destination cleanup was incomplete"
    ) as captured:
        transaction.apply("codex", request)
    assert captured.value.__cause__ is not None
    assert "unmanaged" in str(captured.value.__cause__)
    assert (root / "skill").resolve() == source


def test_locked_rebuild_refuses_source_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    skill = add_skill(repository, "skill", "# One\n")
    root = tmp_path / "skills"
    request = inventory.build_inventory((repository,), root)
    original_build = transaction.build_inventory
    calls = 0

    def race(
        repositories: tuple[Path, ...], destination: Path
    ) -> inventory.Inventory:
        nonlocal calls
        calls += 1
        if calls == 1:
            (skill / "SKILL.md").write_text("# Two\n", encoding="utf-8")
        return original_build(repositories, destination)

    monkeypatch.setattr(transaction, "build_inventory", race)
    with pytest.raises(transaction.TransactionError, match="source inventory changed"):
        transaction.apply("codex", request)
    assert not (root / "skill").exists()


def test_cleanup_race_leaves_backup_after_committed_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    old = add_skill(repository, "old/shared")
    root = tmp_path / "skills"
    transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    (old / "SKILL.md").unlink()
    new = add_skill(repository, "new/shared")

    def refuse_cleanup(_change: transaction.AppliedChange) -> None:
        raise transaction.TransactionError("injected cleanup race")

    monkeypatch.setattr(transaction, "cleanup_backup", refuse_cleanup)
    result = transaction.apply(
        "codex", inventory.build_inventory((repository,), root)
    )
    assert result.warnings
    assert (root / "shared").resolve() == new
    assert state.load_state(root, "codex") is not None
    assert any("rollback" in entry.name for entry in root.iterdir())


def private_payload(tmp_path: Path, payload: bytes = b"complete state\n") -> Path:
    path = tmp_path / "private-state"
    path.write_bytes(payload)
    path.chmod(0o600)
    return path


def test_private_state_read_loops_until_exact_eof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = private_payload(tmp_path)
    original_read = state.os.read

    def short_read(descriptor: int, size: int) -> bytes:
        return original_read(descriptor, min(size, 1))

    monkeypatch.setattr(state.os, "read", short_read)
    _, payload = state.read_private_regular(path)
    assert payload == b"complete state\n"


def test_private_state_read_rejects_premature_eof_and_excess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = private_payload(tmp_path)

    monkeypatch.setattr(state.os, "read", lambda _descriptor, _size: b"")
    with pytest.raises(state.StateError, match="incomplete"):
        state.read_private_regular(path)

    calls = 0
    expected = path.read_bytes()

    def excess(_descriptor: int, _size: int) -> bytes:
        nonlocal calls
        calls += 1
        return expected if calls == 1 else b"x"

    monkeypatch.setattr(state.os, "read", excess)
    with pytest.raises(state.StateError, match="grew"):
        state.read_private_regular(path)


def test_private_state_read_rejects_metadata_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = private_payload(tmp_path)
    original_fstat = state.os.fstat
    fields = (
        ("st_mode", stat.S_IFREG | 0o640),
        ("st_nlink", 2),
        ("st_uid", os.getuid() + 1),
        ("st_ino", path.stat().st_ino + 1),
        ("st_dev", path.stat().st_dev + 1),
        ("st_size", path.stat().st_size + 1),
        ("st_mtime_ns", path.stat().st_mtime_ns + 1),
        ("st_ctime_ns", path.stat().st_ctime_ns + 1),
    )
    for field, changed in fields:
        calls = 0

        def drifting(descriptor: int) -> object:
            nonlocal calls
            calls += 1
            metadata = original_fstat(descriptor)
            values = {
                name: getattr(metadata, name)
                for name in (
                    "st_dev",
                    "st_ino",
                    "st_mode",
                    "st_uid",
                    "st_gid",
                    "st_nlink",
                    "st_size",
                    "st_mtime_ns",
                    "st_ctime_ns",
                )
            }
            if calls > 1:
                values[field] = changed
            return SimpleNamespace(**values)

        monkeypatch.setattr(state.os, "fstat", drifting)
        with pytest.raises(state.StateError, match="changed"):
            state.read_private_regular(path)
        monkeypatch.setattr(state.os, "fstat", original_fstat)


def test_private_state_read_closes_after_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = private_payload(tmp_path)
    descriptor_seen: int | None = None

    def interrupt(descriptor: int, _size: int) -> bytes:
        nonlocal descriptor_seen
        descriptor_seen = descriptor
        raise KeyboardInterrupt

    monkeypatch.setattr(state.os, "read", interrupt)
    with pytest.raises(KeyboardInterrupt):
        state.read_private_regular(path)
    assert descriptor_seen is not None
    with pytest.raises(OSError):
        os.fstat(descriptor_seen)


def test_private_state_read_rejects_growth_shrink_and_link_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_read = state.os.read

    growth_root = tmp_path / "growth"
    growth_root.mkdir()
    growth = private_payload(growth_root, b"abcdef")

    def grow(descriptor: int, size: int) -> bytes:
        chunk = original_read(descriptor, size)
        if chunk:
            with growth.open("ab") as stream:
                stream.write(b"x")
        return chunk

    monkeypatch.setattr(state.os, "read", grow)
    with pytest.raises(state.StateError, match="grew|changed"):
        state.read_private_regular(growth)
    monkeypatch.undo()

    shrink = tmp_path / "shrink" / "private-state"
    shrink.parent.mkdir()
    shrink.write_bytes(b"abcdef")
    shrink.chmod(0o600)
    first = True

    def truncate(descriptor: int, size: int) -> bytes:
        nonlocal first
        chunk = original_read(descriptor, min(size, 2))
        if first:
            first = False
            shrink.write_bytes(b"ab")
            shrink.chmod(0o600)
        return chunk

    monkeypatch.setattr(state.os, "read", truncate)
    with pytest.raises(state.StateError, match="incomplete"):
        state.read_private_regular(shrink)
    monkeypatch.undo()

    linked = tmp_path / "linked" / "private-state"
    linked.parent.mkdir()
    linked.write_bytes(b"abcdef")
    linked.chmod(0o600)
    hardlink = linked.parent / "second-name"
    first = True

    def add_link(descriptor: int, size: int) -> bytes:
        nonlocal first
        chunk = original_read(descriptor, size)
        if first:
            first = False
            os.link(linked, hardlink)
        return chunk

    monkeypatch.setattr(state.os, "read", add_link)
    with pytest.raises(state.StateError, match="changed"):
        state.read_private_regular(linked)


def test_private_state_read_rejects_unsafe_file_shapes(tmp_path: Path) -> None:
    target = private_payload(tmp_path, b"valid\n")
    symlink = tmp_path / "symlink"
    symlink.symlink_to(target)
    with pytest.raises(state.StateError, match="unsafe"):
        state.read_private_regular(symlink)

    hardlink = tmp_path / "hardlink"
    os.link(target, hardlink)
    with pytest.raises(state.StateError, match="unsafe"):
        state.read_private_regular(target)
    hardlink.unlink()

    oversized = tmp_path / "oversized"
    oversized.write_bytes(b"x" * (1024 * 1024 + 1))
    oversized.chmod(0o600)
    with pytest.raises(state.StateError, match="unsafe"):
        state.read_private_regular(oversized)
