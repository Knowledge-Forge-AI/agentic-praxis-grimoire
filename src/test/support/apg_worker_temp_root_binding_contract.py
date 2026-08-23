"""No-follow absolute path-chain binding for worker temporary roots."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import sys
from typing import NoReturn


_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


class WorkerTempError(ValueError):
    """The isolated worker temporary-storage contract is unavailable."""


class WorkerTempCleanupError(WorkerTempError):
    """Descriptor-relative cleanup could not prove lexical absence."""


@dataclass
class OpenedWorkerTempRoot:
    """Retained final root plus its complete no-follow path identity chain."""

    path: Path
    parent_fd: int
    descriptor: int
    name: str
    identity: tuple[int, int, int]
    chain_identities: tuple[tuple[int, int, int], ...]

    def revalidate(self) -> None:
        probe: OpenedWorkerTempRoot | None = None
        try:
            entry = os.stat(
                self.name, dir_fd=self.parent_fd, follow_symlinks=False
            )
            opened = os.fstat(self.descriptor)
            probe = open_absolute_directory(
                str(self.path), subject="worker temporary root"
            )
        except (OSError, WorkerTempError) as error:
            raise WorkerTempError(
                "worker temporary root changed during operation"
            ) from error
        try:
            if (
                identity(entry) != self.identity
                or identity(opened) != self.identity
                or probe.chain_identities != self.chain_identities
            ):
                fail("worker temporary root changed during operation")
        finally:
            probe.close()

    def close(self) -> None:
        os.close(self.descriptor)
        os.close(self.parent_fd)


def fail(message: str) -> NoReturn:
    raise WorkerTempError(message)


def identity(value: os.stat_result) -> tuple[int, int, int]:
    return value.st_dev, value.st_ino, stat.S_IFMT(value.st_mode)


def _absolute_components(value: str, *, subject: str) -> tuple[str, ...]:
    if (
        not value
        or not os.path.isabs(value)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        fail(f"{subject} must be an absolute control-free path")
    components = tuple(part for part in value.split("/") if part)
    if not components or any(part in {".", ".."} for part in components):
        fail(f"{subject} must name a direct directory")
    return components


def open_absolute_directory(value: str, *, subject: str) -> OpenedWorkerTempRoot:
    components = _absolute_components(value, subject=subject)
    current: int | None = None
    child: int | None = None
    identities: list[tuple[int, int, int]] = []
    try:
        current = os.open("/", _DIRECTORY_FLAGS)
        identities.append(identity(os.fstat(current)))
        for index, name in enumerate(components):
            try:
                before = os.stat(name, dir_fd=current, follow_symlinks=False)
                child = os.open(name, _DIRECTORY_FLAGS, dir_fd=current)
                opened = os.fstat(child)
                after = os.stat(name, dir_fd=current, follow_symlinks=False)
            except OSError as error:
                raise WorkerTempError(f"{subject} is unavailable") from error
            if (
                not stat.S_ISDIR(before.st_mode)
                or identity(before) != identity(opened)
                or identity(opened) != identity(after)
            ):
                fail(f"{subject} must be a direct directory")
            identities.append(identity(opened))
            if index == len(components) - 1:
                result = OpenedWorkerTempRoot(
                    path=Path(value),
                    parent_fd=current,
                    descriptor=child,
                    name=name,
                    identity=identity(opened),
                    chain_identities=tuple(identities),
                )
                current = None
                child = None
                return result
            os.close(current)
            current = child
            child = None
    finally:
        if child is not None:
            os.close(child)
        if current is not None:
            os.close(current)
    raise AssertionError("absolute directory traversal did not return")


def selected_worker_temp_root(repository_root: Path) -> OpenedWorkerTempRoot:
    raw = os.environ.get("TMPDIR")
    if raw is None:
        fail("isolated worker requires an explicit temporary root")
    if raw.startswith(("/var/", "/tmp/")) and sys.platform == "darwin":
        prefix = "/var" if raw.startswith("/var/") else "/tmp"
        if Path(prefix).is_symlink() and Path(prefix).resolve() == Path(f"/private{prefix}"):
            raw = f"/private{raw}"
    selected = open_absolute_directory(raw, subject="worker temporary root")
    repository: OpenedWorkerTempRoot | None = None
    try:
        repository = open_absolute_directory(
            str(Path(repository_root).resolve(strict=True)),
            subject="inspected repository root",
        )
        if (
            selected.identity == repository.identity
            or repository.identity in selected.chain_identities
        ):
            fail("worker temporary root must be outside the repository")
        selected.revalidate()
        return selected
    except BaseException:
        selected.close()
        raise
    finally:
        if repository is not None:
            repository.close()
