"""Owner state and serialization for the flat skill projection command."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile
from typing import Iterator, Mapping


STATE_NAME = ".flatten-skill-symlinks-state.json"
LOCK_NAME = ".flatten-skill-symlinks.lock"


class StateError(RuntimeError):
    """Projection owner state is missing, malformed, unsafe, or contended."""


@dataclass(frozen=True, slots=True)
class ProjectionState:
    input_root: str
    links: Mapping[str, str]
    identity: tuple[int, int]
    payload: bytes


def _safe_name(value: str) -> bool:
    return (
        bool(value)
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
    )


def _validate_links(value: object, input_root: Path) -> dict[str, str]:
    if not isinstance(value, dict):
        raise StateError("projection state links must be an object")
    links: dict[str, str] = {}
    for name, target in value.items():
        if (
            not isinstance(name, str)
            or not _safe_name(name)
            or any(ord(character) < 32 or ord(character) == 127 for character in name)
            or not isinstance(target, str)
        ):
            raise StateError("projection state contains an unsafe link entry")
        target_path = Path(target)
        if (
            not target_path.is_absolute()
            or target_path.resolve(strict=False) != target_path
            or not target_path.is_relative_to(input_root)
        ):
            raise StateError("projection state target is outside its input root")
        links[name] = target
    return links


def _read_private_regular(
    path: Path,
    expected_identity: tuple[int, int] | None = None,
) -> tuple[os.stat_result, bytes]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        identity = (metadata.st_dev, metadata.st_ino)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or (expected_identity is not None and identity != expected_identity)
        ):
            raise StateError("projection state file is unsafe")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            payload = stream.read()
        return metadata, payload
    finally:
        os.close(descriptor)


def load_state(output_root: Path, input_root: Path) -> ProjectionState | None:
    path = output_root / STATE_NAME
    try:
        metadata, payload = _read_private_regular(path)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise StateError("projection state file is unsafe") from error
    try:
        current = path.lstat()
    except OSError as error:
        raise StateError("projection state changed while reading") from error
    if (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino):
        raise StateError("projection state file is unsafe")
    try:
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise StateError("projection state is not valid JSON") from error
    if not isinstance(value, dict) or set(value) != {
        "input_root",
        "links",
        "schema_version",
    }:
        raise StateError("projection state schema is not closed")
    if value["schema_version"] != 1 or value["input_root"] != str(input_root):
        raise StateError("projection state belongs to a different input root")
    return ProjectionState(
        input_root=value["input_root"],
        links=_validate_links(value["links"], input_root),
        identity=(metadata.st_dev, metadata.st_ino),
        payload=payload,
    )


def write_state(
    output_root: Path,
    input_root: Path,
    links: Mapping[str, str],
    expected: ProjectionState | None = None,
) -> None:
    payload = json.dumps(
        {
            "input_root": str(input_root),
            "links": dict(sorted(links.items())),
            "schema_version": 1,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    descriptor, temporary_text = tempfile.mkstemp(
        prefix=f".{STATE_NAME}.", dir=output_root
    )
    temporary: Path | None = Path(temporary_text)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        destination = output_root / STATE_NAME
        backup: Path | None = None
        if expected is not None:
            backup = output_root / (
                f".{STATE_NAME}.rollback-{os.getpid()}-{secrets.token_hex(8)}"
            )
            os.rename(destination, backup)
            try:
                _, backup_payload = _read_private_regular(
                    backup,
                    expected.identity,
                )
            except (OSError, StateError):
                backup_payload = b""
            if backup_payload != expected.payload:
                if not destination.exists() and not destination.is_symlink():
                    os.rename(backup, destination)
                raise StateError(
                    f"projection state changed; preserved displaced entry at {backup}"
                )
        try:
            os.link(temporary, destination, follow_symlinks=False)
        except OSError:
            if (
                backup is not None
                and not destination.exists()
                and not destination.is_symlink()
            ):
                os.rename(backup, destination)
            raise
        installed = destination.lstat()
        installed_identity = (installed.st_dev, installed.st_ino)
        try:
            temporary.unlink()
        except OSError as error:
            try:
                current = destination.lstat()
                if (current.st_dev, current.st_ino) == installed_identity:
                    destination.unlink()
                if (
                    backup is not None
                    and not destination.exists()
                    and not destination.is_symlink()
                ):
                    os.rename(backup, destination)
            except OSError:
                pass
            raise StateError("projection state installation cleanup failed") from error
        temporary = None
        if backup is not None:
            try:
                backup.unlink()
            except OSError:
                # The new state is committed and authoritative. Retaining the
                # owner-only old-state backup is safer than rolling link changes
                # back against the committed state.
                pass
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


@contextmanager
def projection_lock(output_root: Path) -> Iterator[None]:
    path = output_root / LOCK_NAME
    token = secrets.token_hex(16)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError as error:
        raise StateError("projection update is already active") from error
    metadata = path.lstat()
    identity = (metadata.st_dev, metadata.st_ino)
    owner = path / "owner"
    try:
        descriptor = os.open(owner, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, (token + "\n").encode("ascii"))
        finally:
            os.close(descriptor)
        yield
    finally:
        try:
            current = path.lstat()
            if (
                not path.is_symlink()
                and stat.S_ISDIR(current.st_mode)
                and (current.st_dev, current.st_ino) == identity
                and owner.read_text(encoding="ascii") == token + "\n"
            ):
                owner.unlink()
                path.rmdir()
        except OSError:
            pass
