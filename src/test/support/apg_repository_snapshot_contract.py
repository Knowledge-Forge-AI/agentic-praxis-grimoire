"""Bounded descriptor-derived snapshot for retained dynamic consumers."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
from typing import Iterator

from apg_exact_read_contract import READ_CHUNK_BYTES, read_exact


MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024
SNAPSHOT_ROOTS = ("skills", ".agents")
_read_chunk = os.read
_remove_tree = shutil.rmtree
_set_mode = os.fchmod


class SnapshotCleanupError(ValueError):
    """Bounded snapshot cleanup could not prove that the copy is gone."""


def _fail(message: str) -> None:
    raise ValueError(message)


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _link_parts(parent: tuple[str, ...], target: str) -> None:
    if not target or target.startswith("/") or "\\" in target:
        _fail("worker snapshot contains an unsafe symbolic link")
    resolved = list(parent)
    for part in PurePosixPath(target).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not resolved:
                _fail("worker snapshot link escapes the repository")
            resolved.pop()
        else:
            resolved.append(part)
    if not any(
        tuple(resolved[: len(root.split("/"))]) == tuple(root.split("/"))
        for root in SNAPSHOT_ROOTS
    ):
        _fail("worker snapshot link escapes the bounded surface")


def _finish_entry(source_parent: int, name: str, before: os.stat_result) -> None:
    try:
        after = os.stat(name, dir_fd=source_parent, follow_symlinks=False)
    except OSError as error:
        raise ValueError("worker snapshot source disappeared") from error
    if _identity(before) != _identity(after):
        _fail("worker snapshot entry changed during copy")


def _copy_directory(
    source_parent: int,
    name: str,
    destination: Path,
    relative: tuple[str, ...],
    before: os.stat_result,
    total: list[int],
) -> None:
    destination.mkdir()
    try:
        child_fd = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY,
            dir_fd=source_parent,
        )
    except OSError as error:
        raise ValueError("worker snapshot directory is unsafe") from error
    try:
        opened = os.fstat(child_fd)
        if _identity(opened) != _identity(before):
            _fail("worker snapshot directory changed during open")
        for child in sorted(os.listdir(child_fd)):
            _entry(child_fd, child, destination, relative, total)
        after = os.fstat(child_fd)
        if _identity(opened) != _identity(after):
            _fail("worker snapshot directory changed during read")
    finally:
        os.close(child_fd)
    destination.chmod(0o500)


def _copy_regular(
    source_parent: int,
    name: str,
    destination: Path,
    before: os.stat_result,
    total: list[int],
) -> None:
    """Copy exactly the declared bytes and require an explicit end of file."""

    try:
        source_fd = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=source_parent,
        )
    except OSError as error:
        raise ValueError("worker snapshot file is unsafe") from error
    try:
        opened = os.fstat(source_fd)
        if _identity(opened) != _identity(before):
            _fail("worker snapshot file changed during open")
        expected = opened.st_size
        if total[0] + expected > MAX_SNAPSHOT_BYTES:
            _fail("worker snapshot exceeds the bounded ceiling")
        with destination.open("wb") as output:
            copied = read_exact(
                source_fd,
                expected,
                read_chunk=_read_chunk,
                fail=_fail,
                subject="worker snapshot file",
                sink=output.write,
                chunk_bytes=READ_CHUNK_BYTES,
            )
        after = os.fstat(source_fd)
    finally:
        os.close(source_fd)
    try:
        entry_after = os.stat(name, dir_fd=source_parent, follow_symlinks=False)
    except OSError as error:
        raise ValueError("worker snapshot source disappeared") from error
    if _identity(opened) != _identity(after) or _identity(after) != _identity(entry_after):
        _fail("worker snapshot file changed during read")
    if copied != expected:
        _fail("worker snapshot file did not provide a complete read")
    total[0] += copied
    destination.chmod(0o400)


def _entry(
    source_parent: int,
    name: str,
    destination_parent: Path,
    relative_parent: tuple[str, ...],
    total: list[int],
) -> None:
    try:
        before = os.stat(name, dir_fd=source_parent, follow_symlinks=False)
    except OSError as error:
        raise ValueError("worker snapshot source disappeared") from error
    destination = destination_parent / name
    relative = (*relative_parent, name)
    if stat.S_ISLNK(before.st_mode):
        try:
            target = os.readlink(name, dir_fd=source_parent)
        except OSError as error:
            raise ValueError("worker snapshot link is unreadable") from error
        _link_parts(relative_parent, target)
        destination.symlink_to(target)
    elif stat.S_ISDIR(before.st_mode):
        _copy_directory(
            source_parent, name, destination, relative, before, total
        )
    elif stat.S_ISREG(before.st_mode):
        _copy_regular(source_parent, name, destination, before, total)
    else:
        _fail("worker snapshot contains an unsupported entry")
    _finish_entry(source_parent, name, before)


def _restore_owner_permissions(path: Path) -> None:
    """Restore owner traversal on copied directories without following links."""

    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY
    try:
        root_fd = os.open(path, flags)
    except OSError:
        return
    pending = [root_fd]
    opened = [root_fd]
    try:
        while pending:
            parent = pending.pop()
            try:
                names = os.listdir(parent)
            except OSError:
                names = ()
            for name in names:
                try:
                    value = os.stat(name, dir_fd=parent, follow_symlinks=False)
                    if not stat.S_ISDIR(value.st_mode):
                        continue
                    child = os.open(name, flags, dir_fd=parent)
                except OSError:
                    continue
                opened.append(child)
                pending.append(child)
        for descriptor in reversed(opened):
            try:
                _set_mode(descriptor, 0o700)
            except OSError:
                pass
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


def _present(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _cleanup(path: Path) -> None:
    """Remove the snapshot and prove its lexical absence, or fail closed."""

    _restore_owner_permissions(path)
    try:
        _remove_tree(path)
    except OSError:
        pass
    if _present(path):
        raise SnapshotCleanupError(
            "worker snapshot cleanup left copied repository residue"
        )


def cleanup_tree(path: Path) -> None:
    """Remove one owned temporary tree without following replacement links."""

    _cleanup(path)


def _populate_snapshot(root_fd: int, snapshot: Path) -> None:
    total = [0]
    for name in SNAPSHOT_ROOTS:
        try:
            os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        _entry(root_fd, name, snapshot, (), total)
    snapshot.chmod(0o500)


@contextmanager
def _descriptor_worker_snapshot(root_fd: int, temp_fd: int) -> Iterator[Path]:
    from apg_worker_temp_contract import (  # worker-harness dependency
        WorkerTempCleanupError,
        descriptor_child,
    )

    previous_fd: int | None = None
    failure: BaseException | None = None
    try:
        with descriptor_child(temp_fd, prefix="apg-consumer-snapshot-") as child:
            assert child.descriptor is not None
            previous_fd = os.open(".", os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
            try:
                os.fchdir(child.descriptor)
                _populate_snapshot(root_fd, Path("."))
                yield Path(".")
            except BaseException as error:
                failure = error
                raise
            finally:
                restore_fd = previous_fd
                previous_fd = None
                try:
                    try:
                        os.fchdir(restore_fd)
                    finally:
                        os.close(restore_fd)
                except BaseException:
                    if failure is None:
                        raise SnapshotCleanupError(
                            "worker snapshot cleanup left copied repository residue"
                        )
                    setattr(
                        failure,
                        "snapshot_cleanup_failure",
                        "worker snapshot cleanup left copied repository residue",
                    )
    except WorkerTempCleanupError as error:
        if failure is not None:
            raise failure
        raise SnapshotCleanupError(
            "worker snapshot cleanup left copied repository residue"
        ) from error
    except BaseException as error:
        if hasattr(error, "worker_temp_cleanup_failure"):
            setattr(
                error,
                "snapshot_cleanup_failure",
                "worker snapshot cleanup left copied repository residue",
            )
        raise
    finally:
        if previous_fd is not None:
            restore_fd = previous_fd
            previous_fd = None
            try:
                os.fchdir(restore_fd)
            finally:
                os.close(restore_fd)


@contextmanager
def worker_snapshot(root_fd: int, temp_fd: int | None = None) -> Iterator[Path]:
    """Yield a bounded read-only snapshot derived only through ``root_fd``.

    Cleanup is part of the operation. When the body succeeded but the copy
    could not be proven gone, the operation fails. When the body already
    failed, that failure stays primary and the cleanup failure is recorded on
    it as ``snapshot_cleanup_failure`` secondary evidence. No message exposes
    the temporary snapshot location.
    """

    if temp_fd is not None:
        with _descriptor_worker_snapshot(root_fd, temp_fd) as snapshot:
            yield snapshot
        return

    snapshot = Path(tempfile.mkdtemp(prefix="apg-consumer-snapshot-"))
    failure: BaseException | None = None
    try:
        try:
            _populate_snapshot(root_fd, snapshot)
            yield snapshot
        except BaseException as error:
            failure = error
            raise
    finally:
        try:
            _cleanup(snapshot)
        except SnapshotCleanupError as cleanup_error:
            if failure is None:
                raise
            setattr(failure, "snapshot_cleanup_failure", str(cleanup_error))
