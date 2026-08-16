"""Descriptor-relative creation and cleanup for worker temporary children."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
import secrets
import stat
from typing import Iterator, NoReturn

from apg_worker_temp_root_binding_contract import (
    WorkerTempCleanupError,
    WorkerTempError,
    identity,
)


CHILD_CREATE_ATTEMPTS = 8
_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


@dataclass
class ChildState:
    parent_fd: int
    prefix: str
    name: str | None = None
    entry_identity: tuple[int, int, int] | None = None
    descriptor: int | None = None


def _fail(message: str) -> NoReturn:
    raise WorkerTempError(message)


def _candidate_name(prefix: str) -> str:
    return f"{prefix}{secrets.token_hex(12)}"


def _safe_component(value: str, *, prefix: str) -> bool:
    return (
        value.startswith(prefix)
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def _mkdir_child(state: ChildState, name: str) -> None:
    os.mkdir(name, 0o700, dir_fd=state.parent_fd)


def _candidate_exists(parent_fd: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise WorkerTempError(
            "worker temporary root cannot inspect a child candidate"
        ) from error
    return True


def _open_child(parent_fd: int, name: str) -> int:
    return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)


def _record_child(state: ChildState) -> None:
    for _attempt in range(CHILD_CREATE_ATTEMPTS):
        name = _candidate_name(state.prefix)
        if not _safe_component(name, prefix=state.prefix):
            _fail("worker temporary child name is unsafe")
        if _candidate_exists(state.parent_fd, name):
            continue
        state.name = name
        try:
            _mkdir_child(state, name)
        except FileExistsError:
            state.name = None
            continue
        except OSError as error:
            raise WorkerTempError(
                "worker temporary root is not writable"
            ) from error
        assert state.name == name
        try:
            entry = os.stat(name, dir_fd=state.parent_fd, follow_symlinks=False)
        except OSError as error:
            raise WorkerTempError(
                "worker temporary child cannot be inspected"
            ) from error
        if not stat.S_ISDIR(entry.st_mode):
            _fail("worker temporary child is not a direct directory")
        state.entry_identity = identity(entry)
        try:
            state.descriptor = _open_child(state.parent_fd, name)
        except OSError as error:
            raise WorkerTempError(
                "worker temporary child cannot be opened"
            ) from error
        _verify_child(state)
        return
    _fail("worker temporary child allocation was exhausted")


def _verify_child(state: ChildState) -> None:
    assert state.name is not None
    assert state.entry_identity is not None
    assert state.descriptor is not None
    try:
        entry = os.stat(
            state.name, dir_fd=state.parent_fd, follow_symlinks=False
        )
        opened = os.fstat(state.descriptor)
    except OSError as error:
        raise WorkerTempError(
            "worker temporary child changed during open"
        ) from error
    if (
        not stat.S_ISDIR(entry.st_mode)
        or identity(entry) != state.entry_identity
        or identity(opened) != state.entry_identity
    ):
        _fail("worker temporary child changed during open")


def _cleanup_fail(error: BaseException | None = None) -> NoReturn:
    if error is None:
        _fail("isolated worker temporary cleanup left residue")
    raise WorkerTempError(
        "isolated worker temporary cleanup left residue"
    ) from error


def _list_entries(parent_fd: int) -> tuple[str, ...]:
    try:
        return tuple(os.listdir(parent_fd))
    except OSError as error:
        _cleanup_fail(error)


def _direct_entry(parent_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as error:
        _cleanup_fail(error)


def _unlink_entry(parent_fd: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=parent_fd)
    except OSError as error:
        _cleanup_fail(error)


def _remove_directory_entry(
    parent_fd: int, name: str, entry: os.stat_result
) -> None:
    try:
        child_fd = _open_child(parent_fd, name)
    except OSError as error:
        _cleanup_fail(error)
    try:
        if identity(os.fstat(child_fd)) != identity(entry):
            _cleanup_fail()
        try:
            os.fchmod(child_fd, 0o700)
        except OSError:
            pass
        _remove_entries(child_fd)
    finally:
        os.close(child_fd)
    after = _direct_entry(parent_fd, name)
    if after is None or identity(after) != identity(entry):
        _cleanup_fail()
    try:
        os.rmdir(name, dir_fd=parent_fd)
    except OSError as error:
        _cleanup_fail(error)


def _remove_entries(parent_fd: int) -> None:
    for name in _list_entries(parent_fd):
        entry = _direct_entry(parent_fd, name)
        if entry is None:
            continue
        if stat.S_ISDIR(entry.st_mode):
            _remove_directory_entry(parent_fd, name, entry)
        else:
            _unlink_entry(parent_fd, name)


def _clean_opened_child(state: ChildState) -> None:
    assert state.descriptor is not None
    descriptor = state.descriptor
    state.descriptor = None
    try:
        try:
            os.fchmod(descriptor, 0o700)
        except OSError:
            pass
        _remove_entries(descriptor)
    finally:
        os.close(descriptor)


def _remove_recorded_child_entry(state: ChildState) -> None:
    assert state.entry_identity is not None
    for name in _list_entries(state.parent_fd):
        entry = _direct_entry(state.parent_fd, name)
        if entry is None or identity(entry) != state.entry_identity:
            continue
        try:
            os.rmdir(name, dir_fd=state.parent_fd)
        except OSError as error:
            _cleanup_fail(error)


def _remove_lexical_child_entry(state: ChildState) -> None:
    assert state.name is not None
    entry = _direct_entry(state.parent_fd, state.name)
    if entry is None:
        return
    try:
        if stat.S_ISDIR(entry.st_mode):
            os.rmdir(state.name, dir_fd=state.parent_fd)
        else:
            os.unlink(state.name, dir_fd=state.parent_fd)
    except OSError as error:
        _cleanup_fail(error)


def _prove_child_absent(state: ChildState) -> None:
    assert state.name is not None
    if _direct_entry(state.parent_fd, state.name) is not None:
        _cleanup_fail()


def _cleanup_child(state: ChildState) -> None:
    if state.name is None:
        return
    if state.descriptor is not None:
        _clean_opened_child(state)
    if state.entry_identity is not None:
        _remove_recorded_child_entry(state)
    _remove_lexical_child_entry(state)
    _prove_child_absent(state)


def _attach_cleanup_failure(failure: BaseException) -> None:
    setattr(
        failure,
        "worker_temp_cleanup_failure",
        "isolated worker temporary cleanup left residue",
    )


@contextmanager
def descriptor_child(parent_fd: int, *, prefix: str) -> Iterator[ChildState]:
    """Yield one retained child created and cleaned relative to ``parent_fd``."""

    state = ChildState(parent_fd=parent_fd, prefix=prefix)
    failure: BaseException | None = None
    try:
        try:
            _record_child(state)
            assert state.descriptor is not None
            yield state
        except BaseException as error:
            failure = error
            raise
    finally:
        try:
            _cleanup_child(state)
        except BaseException as cleanup_error:
            if failure is None:
                raise WorkerTempCleanupError(
                    "isolated worker temporary cleanup left residue"
                ) from cleanup_error
            _attach_cleanup_failure(failure)
