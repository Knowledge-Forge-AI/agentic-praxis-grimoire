"""Direct bounded-snapshot security and cleanup controls."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import shutil
import stat
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))


def _module():
    return importlib.import_module("apg_repository_snapshot_contract")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _root_fd(root: Path) -> int:
    return os.open(root, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)


def test_snapshot_is_descriptor_derived_read_only_and_cleaned(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    _write(root / "skills/example/SKILL.md", "---\nname: example\n---\n")
    _write(root / ".agents/README.md", "projection metadata\n")
    fd = _root_fd(root)
    try:
        with _module().worker_snapshot(fd) as snapshot:
            assert (snapshot / "skills/example/SKILL.md").read_text() == (
                "---\nname: example\n---\n"
            )
            assert stat.S_IMODE((snapshot / "skills").stat().st_mode) == 0o500
            assert stat.S_IMODE(
                (snapshot / "skills/example/SKILL.md").stat().st_mode
            ) == 0o400
            assert (snapshot / ".agents/README.md").exists()
            leaf_mode = (snapshot / "skills/example/SKILL.md").stat().st_mode
            assert not stat.S_IMODE(leaf_mode) & 0o222
        assert not snapshot.exists()
    finally:
        os.close(fd)


def test_snapshot_rejects_external_descendant_link_and_cleans(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "outside"
    _write(outside / "external/SKILL.md", "outside\n")
    (root / "skills").mkdir(parents=True)
    (root / "skills/external").symlink_to(
        outside / "external", target_is_directory=True
    )
    module = _module()
    created: list[Path] = []
    original_mkdtemp = module.tempfile.mkdtemp

    def capture_mkdtemp(*args, **kwargs):
        path = Path(original_mkdtemp(*args, **kwargs))
        created.append(path)
        return str(path)

    monkeypatch.setattr(module.tempfile, "mkdtemp", capture_mkdtemp)
    fd = _root_fd(root)
    try:
        with pytest.raises(ValueError, match="unsafe symbolic link|escapes"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)
    assert created and not created[0].exists()


def test_snapshot_rejects_directory_replacement_before_open(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    original = root / "skills/replaced"
    outside = tmp_path / "outside/replaced"
    _write(original / "SKILL.md", "original\n")
    _write(outside / "SKILL.md", "outside\n")
    module = _module()
    real_open = module.os.open
    swapped = False

    def swap_before_open(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if name == "replaced" and dir_fd is not None and not swapped:
            swapped = True
            original.rename(root / "skills/original")
            outside.rename(root / "skills/replaced")
        return real_open(name, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(module.os, "open", swap_before_open)
    fd = _root_fd(root)
    try:
        with pytest.raises(ValueError, match="directory changed during open"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)


def test_snapshot_rejects_absolute_and_backslash_links(
    tmp_path: Path,
) -> None:
    module = _module()
    for index, target in enumerate(("/outside", "outside\\skill")):
        root = tmp_path / f"repository-{index}"
        (root / "skills").mkdir(parents=True)
        (root / "skills/unsafe").symlink_to(target)
        fd = _root_fd(root)
        try:
            with pytest.raises(ValueError, match="unsafe symbolic link"):
                with module.worker_snapshot(fd):
                    pass
        finally:
            os.close(fd)


def test_snapshot_enforces_byte_ceiling_and_cleans(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    _write(root / "skills/example/SKILL.md", "more than one byte\n")
    module = _module()
    monkeypatch.setattr(module, "MAX_SNAPSHOT_BYTES", 1)
    created: list[Path] = []
    original_mkdtemp = module.tempfile.mkdtemp

    def capture_mkdtemp(*args, **kwargs):
        path = Path(original_mkdtemp(*args, **kwargs))
        created.append(path)
        return str(path)

    monkeypatch.setattr(module.tempfile, "mkdtemp", capture_mkdtemp)
    fd = _root_fd(root)
    try:
        with pytest.raises(ValueError, match="bounded ceiling"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)
    assert created and not created[0].exists()


# --- APG60H K1: the copy is exactly the declared bytes ----------------------


def _leaf(root: Path, payload: bytes) -> Path:
    path = root / "skills/example/SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _capture(monkeypatch: pytest.MonkeyPatch, module) -> list[Path]:
    created: list[Path] = []
    original = module.tempfile.mkdtemp

    def capture_mkdtemp(*args, **kwargs):
        path = Path(original(*args, **kwargs))
        created.append(path)
        return str(path)

    monkeypatch.setattr(module.tempfile, "mkdtemp", capture_mkdtemp)
    return created


def _scripted_reads(module, monkeypatch: pytest.MonkeyPatch, script) -> None:
    original = module._read_chunk
    calls = 0

    def read_chunk(descriptor: int, size: int) -> bytes:
        nonlocal calls
        calls += 1
        return script(calls, lambda window=size: original(descriptor, window))

    monkeypatch.setattr(module, "_read_chunk", read_chunk)


def _force_remove(path: Path) -> None:
    for current, directories, files in os.walk(path, topdown=False):
        for name in directories + files:
            child = Path(current) / name
            if not child.is_symlink():
                child.chmod(0o700)
    path.chmod(0o700)
    shutil.rmtree(path)


@pytest.mark.parametrize("payload", (b"", b"0123456789", b"x" * 5000))
def test_exact_snapshot_copies_every_declared_byte(
    tmp_path: Path, payload: bytes
) -> None:
    root = tmp_path / "repository"
    _leaf(root, payload)
    fd = _root_fd(root)
    try:
        with _module().worker_snapshot(fd) as snapshot:
            copied = (snapshot / "skills/example/SKILL.md").read_bytes()
    finally:
        os.close(fd)
    assert copied == payload


@pytest.mark.parametrize("window", (1, 3))
def test_short_snapshot_reads_are_completed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, window: int
) -> None:
    root = tmp_path / "repository"
    _leaf(root, b"0123456789")
    module = _module()
    _scripted_reads(module, monkeypatch, lambda _calls, read: read(window))
    fd = _root_fd(root)
    try:
        with module.worker_snapshot(fd) as snapshot:
            copied = (snapshot / "skills/example/SKILL.md").read_bytes()
    finally:
        os.close(fd)
    assert copied == b"0123456789"


def test_premature_end_of_file_after_a_partial_read_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reproduce the APG60G truncated snapshot and require it to fail."""

    root = tmp_path / "repository"
    _leaf(root, b"0123456789")
    module = _module()
    created = _capture(monkeypatch, module)
    _scripted_reads(
        module,
        monkeypatch,
        lambda calls, read: read(3) if calls == 1 else b"",
    )
    fd = _root_fd(root)
    try:
        with pytest.raises(ValueError, match="complete read"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)
    assert created and not created[0].exists()


def test_immediate_end_of_file_for_a_nonempty_owner_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _leaf(root, b"0123456789")
    module = _module()
    _scripted_reads(module, monkeypatch, lambda _calls, _read: b"")
    fd = _root_fd(root)
    try:
        with pytest.raises(ValueError, match="complete read"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)


def test_excess_byte_beyond_the_declared_size_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _leaf(root, b"0123456789")
    module = _module()
    _scripted_reads(
        module,
        monkeypatch,
        lambda calls, read: read() if calls == 1 else b"excess",
    )
    fd = _root_fd(root)
    try:
        with pytest.raises(ValueError, match="changed size"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)


@pytest.mark.parametrize("mutation", ("grow", "shrink", "same-size", "symlink"))
def test_source_drift_during_copy_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutation: str
) -> None:
    root = tmp_path / "repository"
    leaf = _leaf(root, b"0123456789")
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"external!!")
    module = _module()

    def mutate(calls, read):
        if calls == 1:
            if mutation == "grow":
                with leaf.open("ab") as stream:
                    stream.write(b"growth")
            elif mutation == "shrink":
                leaf.write_bytes(b"0")
            elif mutation == "same-size":
                leaf.unlink()
                leaf.write_bytes(b"abcdefghij")
            else:
                leaf.unlink()
                leaf.symlink_to(outside)
        return read(2)

    _scripted_reads(module, monkeypatch, mutate)
    fd = _root_fd(root)
    try:
        with pytest.raises(ValueError, match="changed|complete"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)


def test_aggregate_ceiling_counts_every_copied_owner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    _write(root / "skills/first/SKILL.md", "first" * 4)
    _write(root / "skills/second/SKILL.md", "second" * 4)
    module = _module()
    monkeypatch.setattr(module, "MAX_SNAPSHOT_BYTES", 30)
    fd = _root_fd(root)
    try:
        with pytest.raises(ValueError, match="bounded ceiling"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)


# --- APG60H K1B: cleanup proves the copy is gone ----------------------------


def _snapshot_root(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    _leaf(root, b"---\nname: example\n---\n")
    return root


def _refuse_removal(module, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "_remove_tree", lambda *_a, **_k: None)


def test_cleanup_failure_fails_an_otherwise_successful_operation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Reproduce the APG60G silent residue and require it to fail."""

    root = _snapshot_root(tmp_path)
    module = _module()
    created = _capture(monkeypatch, module)
    _refuse_removal(module, monkeypatch)
    fd = _root_fd(root)
    try:
        with pytest.raises(module.SnapshotCleanupError, match="residue"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)
    assert created and created[0].exists()
    _force_remove(created[0])


@pytest.mark.parametrize("shape", ("file", "directory", "symlink"))
def test_residual_snapshot_entries_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, shape: str
) -> None:
    root = _snapshot_root(tmp_path)
    module = _module()
    created = _capture(monkeypatch, module)
    original = module._remove_tree

    def leave_residue(path, *args, **kwargs):
        original(path, *args, **kwargs)
        Path(path).mkdir()
        residue = Path(path) / "residue"
        if shape == "file":
            residue.write_text("residue\n", encoding="utf-8")
        elif shape == "directory":
            residue.mkdir()
        else:
            residue.symlink_to("elsewhere")

    monkeypatch.setattr(module, "_remove_tree", leave_residue)
    fd = _root_fd(root)
    try:
        with pytest.raises(module.SnapshotCleanupError, match="residue"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)
    assert created and created[0].exists()
    _force_remove(created[0])


def test_permission_restoration_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _snapshot_root(tmp_path)
    module = _module()
    created = _capture(monkeypatch, module)

    def refuse_chmod(*_args, **_kwargs):
        raise PermissionError("injected permission-restoration failure")

    monkeypatch.setattr(module, "_set_mode", refuse_chmod)
    monkeypatch.setattr(module, "_remove_tree", lambda *_a, **_k: None)
    fd = _root_fd(root)
    try:
        with pytest.raises(module.SnapshotCleanupError, match="residue"):
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)
    assert created
    _force_remove(created[0])


def test_body_failure_stays_primary_and_records_cleanup_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _snapshot_root(tmp_path)
    module = _module()
    created = _capture(monkeypatch, module)
    _refuse_removal(module, monkeypatch)
    fd = _root_fd(root)
    try:
        with pytest.raises(LookupError, match="body failure") as failure:
            with module.worker_snapshot(fd):
                raise LookupError("body failure")
    finally:
        os.close(fd)
    assert "residue" in getattr(failure.value, "snapshot_cleanup_failure", "")
    assert created and created[0].exists()
    _force_remove(created[0])


def test_body_failure_records_nothing_when_cleanup_succeeds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _snapshot_root(tmp_path)
    module = _module()
    created = _capture(monkeypatch, module)
    fd = _root_fd(root)
    try:
        with pytest.raises(LookupError) as failure:
            with module.worker_snapshot(fd):
                raise LookupError("body failure")
    finally:
        os.close(fd)
    assert not hasattr(failure.value, "snapshot_cleanup_failure")
    assert created and not created[0].exists()


def test_interruption_still_removes_the_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _snapshot_root(tmp_path)
    module = _module()
    created = _capture(monkeypatch, module)
    fd = _root_fd(root)
    try:
        with pytest.raises(KeyboardInterrupt):
            with module.worker_snapshot(fd):
                raise KeyboardInterrupt
    finally:
        os.close(fd)
    assert created and not created[0].exists()


def test_cleanup_never_follows_a_snapshot_symlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _snapshot_root(tmp_path)
    outside = tmp_path / "outside"
    _write(outside / "preserved.txt", "preserved\n")
    module = _module()
    created = _capture(monkeypatch, module)
    original = module._remove_tree

    def link_then_remove(path, *args, **kwargs):
        (Path(path) / "external").symlink_to(outside, target_is_directory=True)
        original(path, *args, **kwargs)

    monkeypatch.setattr(module, "_remove_tree", link_then_remove)
    fd = _root_fd(root)
    try:
        with module.worker_snapshot(fd):
            pass
    finally:
        os.close(fd)
    assert created and not created[0].exists()
    assert (outside / "preserved.txt").read_text(encoding="utf-8") == "preserved\n"


def test_cleanup_does_not_chmod_through_a_replacement_root_symlink(
    tmp_path: Path,
) -> None:
    root = _snapshot_root(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o755)
    outside_mode = stat.S_IMODE(os.lstat(outside).st_mode)
    original_snapshot: Path | None = None
    replacement: Path | None = None
    fd = _root_fd(root)
    try:
        with pytest.raises(_module().SnapshotCleanupError, match="residue"):
            with _module().worker_snapshot(fd) as snapshot:
                original_snapshot = snapshot.with_name(snapshot.name + "-original")
                snapshot.rename(original_snapshot)
                snapshot.symlink_to(outside, target_is_directory=True)
                replacement = snapshot
    finally:
        os.close(fd)
        if replacement is not None and replacement.is_symlink():
            replacement.unlink()
        if original_snapshot is not None and original_snapshot.exists():
            _force_remove(original_snapshot)
    assert stat.S_IMODE(os.lstat(outside).st_mode) == outside_mode


def test_cleanup_failure_message_hides_the_temporary_location(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _snapshot_root(tmp_path)
    module = _module()
    created = _capture(monkeypatch, module)
    _refuse_removal(module, monkeypatch)
    fd = _root_fd(root)
    try:
        with pytest.raises(module.SnapshotCleanupError) as failure:
            with module.worker_snapshot(fd):
                pass
    finally:
        os.close(fd)
    assert str(created[0]) not in str(failure.value)
    assert "apg-consumer-snapshot" not in str(failure.value)
    _force_remove(created[0])
