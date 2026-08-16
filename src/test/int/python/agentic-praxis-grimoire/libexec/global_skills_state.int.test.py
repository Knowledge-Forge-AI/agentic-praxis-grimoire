"""Integration boundaries for serialized and external ownership state."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

import pytest

from src.test.apg_test_support import repository_root
from src.test.install_global_skills_cases import add_skill


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import global_skills_inventory as inventory  # noqa: E402
import global_skills_state as state  # noqa: E402


def expected_state(tmp_path: Path) -> tuple[Path, state.InstallState]:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    root = tmp_path / "skills"
    discovered = inventory.build_inventory((repository,), root)
    return root, state.from_inventory("codex", discovered, ())


def test_serialized_state_refuses_foreign_and_malformed_variants(
    tmp_path: Path,
) -> None:
    root, expected = expected_state(tmp_path)
    valid = json.loads(state.serialize_state(expected))

    def changed(**members: object) -> dict[str, object]:
        document = dict(valid)
        document.update(members)
        return document

    variants = [
        ("schema", {}),
        ("owner", changed(owner="foreign")),
        ("agent", changed(agent="claude")),
        ("destination", changed(skills_root=str(tmp_path / "other"))),
        ("generation", changed(generation=-1)),
        ("generation", changed(installation_id="wrong")),
        ("links", changed(links={})),
        ("links", changed(links={"bad/name": "/tmp/source"})),
        ("link target", changed(links={"skill": "relative"})),
        ("skill hashes", changed(skill_hashes={"skill": "wrong"})),
        ("differ", changed(skill_hashes={"other": "a" * 64})),
        ("sources", changed(sources=[])),
        ("source schema", changed(sources=[{"repository_root": "/tmp"}])),
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
                        "device": 1,
                        "inode": 1,
                        "mode": -1,
                        "owner": 1,
                        "path": "/tmp/container",
                    }
                ]
            ),
        ),
    ]
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
            b'{"schema_version":1,"schema_version":1}', "codex", root
        )


def test_state_order_and_external_owner_guards(tmp_path: Path) -> None:
    root, expected = expected_state(tmp_path)
    document = json.loads(state.serialize_state(expected))
    document["sources"] = [
        document["sources"][0],
        {"repository_root": "/000", "skills_root": "/000/skills"},
    ]
    with pytest.raises(state.StateError, match="not canonical"):
        state.parse_state(
            json.dumps(document, separators=(",", ":"), sort_keys=True).encode(),
            "codex",
            root,
        )

    destination = tmp_path / "destination"
    state.check_apg_user_skills_owner(destination, {})
    with pytest.raises(state.StateError, match="not absolute"):
        state.check_apg_user_skills_owner(
            destination, {"XDG_STATE_HOME": "relative"}
        )
    external = tmp_path / "external"
    state.check_apg_user_skills_owner(
        destination, {"XDG_STATE_HOME": str(external)}
    )
    owner = external / "agentic-praxis-grimoire"
    owner.mkdir(parents=True)
    (owner / "user-skills-v1.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(state.StateError, match="lock is unsafe"):
        state.check_apg_user_skills_owner(
            destination, {"XDG_STATE_HOME": str(external)}
        )
    lock = owner / "user-skills-v1.lock"
    lock.write_text("", encoding="utf-8")
    lock.chmod(0o644)
    with pytest.raises(state.StateError, match="lock is unsafe"):
        state.check_apg_user_skills_owner(
            destination, {"XDG_STATE_HOME": str(external)}
        )


def test_container_chain_and_interrupted_no_overwrite_moves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, expected = expected_state(tmp_path)
    document = json.loads(state.serialize_state(expected))
    victim = tmp_path / "unrelated"
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

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("preserve\n", encoding="utf-8")
    identity = state.path_identity(source)
    original_link = state.os.link

    def interrupt_after_link(
        input_path: Path,
        output_path: Path,
        *,
        follow_symlinks: bool,
    ) -> None:
        original_link(
            input_path,
            output_path,
            follow_symlinks=follow_symlinks,
        )
        raise KeyboardInterrupt

    with monkeypatch.context() as patch:
        patch.setattr(state.os, "link", interrupt_after_link)
        with pytest.raises(KeyboardInterrupt):
            state.no_overwrite_move(source, destination, identity)
    assert source.stat().st_nlink == 1
    assert not destination.exists()

    original_unlink = Path.unlink

    def interrupt_after_unlink(
        path: Path, missing_ok: bool = False
    ) -> None:
        original_unlink(path, missing_ok=missing_ok)
        if path == source:
            raise KeyboardInterrupt

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", interrupt_after_unlink)
        with pytest.raises(KeyboardInterrupt):
            state.no_overwrite_move(source, destination, identity)
    assert source.read_text(encoding="utf-8") == "preserve\n"
    assert not destination.exists()

    os.link(source, destination)
    with pytest.raises(FileExistsError):
        state.no_overwrite_move(source, destination, identity)
    assert state.path_identity(source) == state.path_identity(destination)


def test_private_state_exact_read_real_filesystem_guards(tmp_path: Path) -> None:
    valid = tmp_path / "valid"
    payload = b'{"state":"complete"}\n'
    valid.write_bytes(payload)
    valid.chmod(0o600)

    metadata, observed = state.read_private_regular(valid)
    assert observed == payload
    assert metadata.st_size == len(payload)
    with pytest.raises(state.StateError, match="unsafe"):
        state.read_private_regular(valid, (metadata.st_dev, metadata.st_ino + 1))

    empty = tmp_path / "empty"
    empty.touch(mode=0o600)
    with pytest.raises(state.StateError, match="unsafe"):
        state.read_private_regular(empty)

    permissive = tmp_path / "permissive"
    permissive.write_bytes(payload)
    permissive.chmod(0o644)
    with pytest.raises(state.StateError, match="unsafe"):
        state.read_private_regular(permissive)

    hard_link = tmp_path / "hard-link"
    os.link(valid, hard_link)
    with pytest.raises(state.StateError, match="unsafe"):
        state.read_private_regular(valid)

    target = tmp_path / "target"
    target.write_bytes(payload)
    target.chmod(0o600)
    symbolic = tmp_path / "symbolic"
    symbolic.symlink_to(target)
    with pytest.raises(state.StateError, match="unsafe"):
        state.read_private_regular(symbolic)


def test_private_state_exact_read_injected_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "private-state"
    payload = b"complete state\n"
    path.write_bytes(payload)
    path.chmod(0o600)
    original_read = state.os.read

    def short_read(descriptor: int, size: int) -> bytes:
        return original_read(descriptor, min(size, 1))

    monkeypatch.setattr(state.os, "read", short_read)
    assert state.read_private_regular(path)[1] == payload

    monkeypatch.setattr(state.os, "read", lambda _descriptor, _size: b"")
    with pytest.raises(state.StateError, match="incomplete"):
        state.read_private_regular(path)

    calls = 0

    def oversized_chunk(_descriptor: int, _size: int) -> bytes:
        nonlocal calls
        calls += 1
        return payload + b"x" if calls == 1 else b""

    monkeypatch.setattr(state.os, "read", oversized_chunk)
    with pytest.raises(state.StateError, match="grew"):
        state.read_private_regular(path)

    calls = 0

    def excess_after_size(_descriptor: int, _size: int) -> bytes:
        nonlocal calls
        calls += 1
        return payload if calls == 1 else b"x"

    monkeypatch.setattr(state.os, "read", excess_after_size)
    with pytest.raises(state.StateError, match="grew"):
        state.read_private_regular(path)

    monkeypatch.setattr(state.os, "read", original_read)
    original_fstat = state.os.fstat
    calls = 0

    def drift_mode(descriptor: int) -> os.stat_result:
        nonlocal calls
        calls += 1
        metadata = original_fstat(descriptor)
        if calls > 1:
            values = list(metadata)
            values[0] = metadata.st_mode ^ stat.S_IXUSR
            return os.stat_result(values)
        return metadata

    monkeypatch.setattr(state.os, "fstat", drift_mode)
    with pytest.raises(state.StateError, match="changed"):
        state.read_private_regular(path)


def test_atomic_directory_install_never_replaces_existing_entry(
    tmp_path: Path,
) -> None:
    staged = tmp_path / "staged"
    staged.mkdir(mode=0o700)
    staged_identity = state.path_identity(staged)
    destination = tmp_path / "destination"
    destination.mkdir(mode=0o700)
    destination_identity = state.path_identity(destination)

    with pytest.raises(FileExistsError):
        state.rename_directory_no_replace(staged, destination)
    assert state.path_identity(staged) == staged_identity
    assert state.path_identity(destination) == destination_identity

    destination.rmdir()
    state.rename_directory_no_replace(staged, destination)
    assert not staged.exists()
    assert state.path_identity(destination) == staged_identity
