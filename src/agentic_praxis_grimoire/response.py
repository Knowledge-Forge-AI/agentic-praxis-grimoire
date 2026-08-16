"""Atomic, numbered APGR final-response capture.

The response recorder deliberately owns only the response artifact contract.  It
does not select a project, discover a repository, or interpret Markdown.  The
caller supplies a project/phase identity and one byte-preserving input source;
this module returns the one path it created.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import contextmanager
import importlib
import fcntl
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time
from typing import BinaryIO, Iterator

from .config import ConfigError, resolve_outbox_root
from .paths import PathContractError, outbox_phase_path


MAX_COMPONENT_LENGTH = 128
MAX_RESPONSE_NUMBER = 999
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
LOCK_NAME = ".response.lock"
TEMP_GLOB = ".response-write.*.tmp"
LOCK_TIMEOUT_SECONDS = 10.0
LOCK_POLL_SECONDS = 0.01

_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_RESERVATION = re.compile(
    r"^\.([A-Za-z0-9][A-Za-z0-9._-]*)\.([0-9]{3})\.response\.md\.reservation\.([A-Za-z0-9_-]+)$"
)
_TEMPORARY = re.compile(r"^\.response-write\.[A-Za-z0-9_-]+\.tmp$")


class ResponseError(RuntimeError):
    """A response artifact could not be created or inspected safely."""


class ResponseUsageError(ResponseError, ValueError):
    """A caller supplied an invalid response identity or input selection."""


class ResponseInputError(ResponseError):
    """The selected response input could not be read as exact bytes."""


class ResponseAllocationError(ResponseError):
    """No response number could be reserved in the bounded phase range."""


def _shared_component_validator():
    """Return an optional package-owned component validator.

    APGR's path module is introduced alongside the CLI by the parent work unit.
    Keeping this lookup lazy lets this module remain independently usable while
    ensuring a later shared validator is authoritative when present.  Both
    names are accepted so the response owner does not need to edit that module.
    """

    package = __package__
    if not package:
        return None
    try:
        paths = importlib.import_module(f"{package}.paths")
    except ModuleNotFoundError as error:
        if error.name != f"{package}.paths":
            raise
        return None
    for name in ("validate_component", "validate_identifier"):
        validator = getattr(paths, name, None)
        if callable(validator):
            return validator
    return None


def _validate_component(value: str, label: str) -> str:
    """Validate one project/phase path component using the shared owner if available."""

    if not isinstance(value, str):
        raise ResponseUsageError(f"{label} is unsafe")
    validator = _shared_component_validator()
    if validator is not None:
        try:
            validated = validator(value)
        except (TypeError, ValueError, OSError) as error:
            raise ResponseUsageError(f"{label} is unsafe") from error
        if not isinstance(validated, str) or validated != value:
            raise ResponseUsageError(f"{label} is unsafe")
        return validated
    if (
        len(value) > MAX_COMPONENT_LENGTH
        or value in {".", ".."}
        or _COMPONENT.fullmatch(value) is None
    ):
        raise ResponseUsageError(f"{label} is unsafe")
    return value


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ResponseError(f"could not inspect response path: {path.name}") from error


def _lexists(path: Path) -> bool:
    return _lstat(path) is not None


def _ensure_directory(path: Path, *, private: bool) -> None:
    """Create or validate a directory without following a symlink."""

    metadata = _lstat(path)
    if metadata is None:
        try:
            path.mkdir(parents=True, mode=0o700)
        except FileExistsError:
            metadata = _lstat(path)
        except OSError as error:
            raise ResponseError("could not create response directory") from error
        else:
            metadata = _lstat(path)
    if metadata is None or stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ResponseError("response directory is unsafe")
    if metadata.st_uid != os.getuid():
        raise ResponseError("response directory owner is unsafe")
    if private and stat.S_IMODE(metadata.st_mode) != 0o700:
        raise ResponseError("response directory permissions must be 0700")


def phase_directory(
    outbox_root: str | os.PathLike[str], project: str, phase: str
) -> Path:
    """Return and create the private ``<outbox>/<project>/<phase>`` directory."""

    project = _validate_component(project, "project")
    phase = _validate_component(phase, "phase")
    try:
        phase_path = outbox_phase_path(outbox_root, project, phase)
    except PathContractError as error:
        raise ResponseUsageError(str(error)) from error
    root = phase_path.parent.parent
    _ensure_directory(root, private=False)
    project_path = phase_path.parent
    _ensure_directory(project_path, private=True)
    _ensure_directory(phase_path, private=True)
    return phase_path


def _response_path(phase_dir: Path, phase: str, number: int) -> Path:
    return phase_dir / f"{phase}.{number:03d}.response.md"


def _reservation_path(phase_dir: Path, phase: str, number: int, token: str) -> Path:
    return phase_dir / f".{phase}.{number:03d}.response.md.reservation.{token}"


def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise OSError("response write made no progress")
        offset += written


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _open_exclusive(path: Path) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(path, flags, 0o600)


def _open_lock(path: Path) -> int:
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(path, flags, 0o600)


def _remove_owned(path: Path, metadata: os.stat_result | None) -> None:
    """Remove exactly the invocation-owned regular file, if it still exists."""

    if metadata is None:
        return
    current = _lstat(path)
    if current is None:
        return
    if (
        current.st_dev != metadata.st_dev
        or current.st_ino != metadata.st_ino
        or not stat.S_ISREG(current.st_mode)
    ):
        raise ResponseError("response temporary artifact changed during cleanup")
    path.unlink()


def _read_source(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as error:
        raise ResponseInputError("could not read response input file") from error
    try:
        metadata = os.fstat(fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ResponseInputError("response input must be a regular file")
        if metadata.st_size > MAX_RESPONSE_BYTES:
            raise ResponseInputError("response input exceeds the 8 MiB limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(1024 * 1024, MAX_RESPONSE_BYTES + 1 - total))
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise ResponseInputError("response input exceeds the 8 MiB limit")
    except ResponseInputError:
        raise
    except OSError as error:
        raise ResponseInputError("could not read response input file") from error
    finally:
        os.close(fd)


def _read_input(
    *,
    body: bytes | bytearray | memoryview | None,
    source: str | os.PathLike[str] | None,
    input_path: str | os.PathLike[str] | None,
    stdin: BinaryIO | None,
) -> bytes:
    if source is not None and input_path is not None:
        raise ResponseUsageError("exactly one response input is required")
    selected_source = source if source is not None else input_path
    selected = sum(
        item is not None for item in (body, selected_source, stdin)
    )
    if selected != 1:
        raise ResponseUsageError("exactly one response input is required")
    if body is not None:
        if not isinstance(body, (bytes, bytearray, memoryview)):
            raise ResponseInputError("response body must be bytes")
        value = bytes(body)
        if len(value) > MAX_RESPONSE_BYTES:
            raise ResponseInputError("response input exceeds the 8 MiB limit")
        return value
    if selected_source is not None:
        return _read_source(Path(selected_source).expanduser())
    assert stdin is not None
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            value = stdin.read(min(1024 * 1024, MAX_RESPONSE_BYTES + 1 - total))
            if not isinstance(value, (bytes, bytearray, memoryview)):
                raise ResponseInputError("response stdin must provide bytes")
            chunk = bytes(value)
            if not chunk:
                break
            if total + len(chunk) > MAX_RESPONSE_BYTES:
                raise ResponseInputError("response input exceeds the 8 MiB limit")
            chunks.append(chunk)
            total += len(chunk)
    except (OSError, TypeError, ValueError) as error:
        raise ResponseInputError("could not read response stdin") from error
    return b"".join(chunks)


@contextmanager
def _phase_lock(phase_dir: Path) -> Iterator[None]:
    """Serialize allocation with an advisory lock released by process exit."""

    lock_path = phase_dir / LOCK_NAME
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    fd: int | None = None
    metadata: os.stat_result | None = None
    while fd is None:
        try:
            candidate = _open_lock(lock_path)
            current = os.fstat(candidate)
            if (
                not stat.S_ISREG(current.st_mode)
                or current.st_uid != os.getuid()
                or stat.S_IMODE(current.st_mode) != 0o600
            ):
                os.close(candidate)
                raise ResponseError("response lock is unsafe")
            try:
                fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(candidate)
                if time.monotonic() >= deadline:
                    raise ResponseAllocationError("response phase lock remained busy")
                time.sleep(LOCK_POLL_SECONDS)
                continue
            fd = candidate
            metadata = current
        except OSError as error:
            raise ResponseError("could not acquire response phase lock") from error
    try:
        os.ftruncate(fd, 0)
        _write_all(fd, b"response-lock-v2\n")
        os.fsync(fd)
        _fsync_directory(phase_dir)
        yield
    finally:
        if fd is not None:
            os.close(fd)


def _reserve(
    phase_dir: Path, phase: str
) -> tuple[int, Path, os.stat_result]:
    reserved_numbers = {
        int(match.group(2))
        for entry in phase_dir.iterdir()
        if (match := _reservation_match(entry)) is not None
        and match.group(1) == phase
    }
    for number in range(1, MAX_RESPONSE_NUMBER + 1):
        destination = _response_path(phase_dir, phase, number)
        if _lexists(destination):
            continue
        if number in reserved_numbers:
            continue
        reservation = _reservation_path(
            phase_dir, phase, number, secrets.token_hex(12)
        )
        try:
            fd = _open_exclusive(reservation)
        except FileExistsError:
            # Defensive collision handling for the random reservation token.
            continue
        try:
            _write_all(
                fd,
                f"response-reservation-v1\nphase={phase}\nnumber={number:03d}\n".encode(
                    "ascii"
                ),
            )
            os.fsync(fd)
            metadata = os.fstat(fd)
        except OSError as error:
            os.close(fd)
            try:
                reservation.unlink()
            except OSError:
                pass
            raise ResponseError("could not create response reservation") from error
        else:
            os.close(fd)
        try:
            _fsync_directory(phase_dir)
        except OSError as error:
            try:
                _remove_owned(reservation, metadata)
            except (OSError, ResponseError) as cleanup_error:
                raise ResponseError(
                    "response reservation durability failed and cleanup was incomplete"
                ) from cleanup_error
            raise ResponseError(
                "could not make response reservation durable"
            ) from error
        return number, reservation, metadata
    raise ResponseAllocationError("response numbers exhausted (001..999)")


def _write_temporary(phase_dir: Path, body: bytes) -> tuple[Path, os.stat_result]:
    for _attempt in range(8):
        temporary = phase_dir / f".response-write.{secrets.token_hex(12)}.tmp"
        try:
            fd = _open_exclusive(temporary)
        except FileExistsError:
            continue
        try:
            _write_all(fd, body)
            os.fsync(fd)
            metadata = os.fstat(fd)
        except OSError as error:
            os.close(fd)
            try:
                temporary.unlink()
            except OSError:
                pass
            raise ResponseError("could not write response temporary file") from error
        else:
            os.close(fd)
        return temporary, metadata
    raise ResponseError("could not reserve response temporary file")


def _clean_orphan_temporaries(phase_dir: Path) -> None:
    """Remove only directly owned response-write temporaries under the phase lock."""

    for entry in phase_dir.iterdir():
        if _TEMPORARY.fullmatch(entry.name) is None:
            continue
        metadata = _lstat(entry)
        if (
            metadata is None
            or stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ResponseError("response temporary artifact is unsafe")
        _remove_owned(entry, metadata)
    _fsync_directory(phase_dir)


def capture_response(
    *,
    outbox_root: str | os.PathLike[str],
    project: str,
    phase: str,
    body: bytes | bytearray | memoryview | None = None,
    source: str | os.PathLike[str] | None = None,
    input_path: str | os.PathLike[str] | None = None,
    stdin: BinaryIO | None = None,
) -> Path:
    """Capture one exact response body and return its newly created path.

    Exactly one of ``body``, ``source``/``input_path``, or ``stdin`` must be
    supplied.  The number allocation, reservation, same-directory temporary
    write, atomic replacement, and reservation cleanup all occur while one
    phase-scoped lock is held.
    """

    response_body = _read_input(
        body=body, source=source, input_path=input_path, stdin=stdin
    )
    phase_dir = phase_directory(outbox_root, project, phase)
    reservation: Path | None = None
    reservation_metadata: os.stat_result | None = None
    temporary: Path | None = None
    temporary_metadata: os.stat_result | None = None
    destination: Path | None = None
    destination_metadata: os.stat_result | None = None
    try:
        with _phase_lock(phase_dir):
            _clean_orphan_temporaries(phase_dir)
            _number, reservation, reservation_metadata = _reserve(phase_dir, phase)
            destination = _response_path(phase_dir, phase, _number)
            temporary, temporary_metadata = _write_temporary(phase_dir, response_body)
            if _lexists(destination):
                raise ResponseError("response destination appeared after reservation")
            destination_metadata = temporary_metadata
            try:
                os.link(temporary, destination, follow_symlinks=False)
            except OSError as error:
                raise ResponseError("atomic no-overwrite response publication failed") from error
            temporary.unlink()
            temporary = None
            temporary_metadata = None
            observed = _lstat(destination)
            if (
                observed is None
                or destination_metadata is None
                or observed.st_dev != destination_metadata.st_dev
                or observed.st_ino != destination_metadata.st_ino
                or not stat.S_ISREG(observed.st_mode)
            ):
                raise ResponseError("response destination is not a regular file")
            if stat.S_IMODE(observed.st_mode) != 0o600:
                raise ResponseError("response destination permissions are not 0600")
            # The exact body is now published without replacement.  From this
            # point onward cleanup or directory-sync failures must not erase
            # that immutable completed artifact.
            destination_metadata = None
            _fsync_directory(phase_dir)
            _remove_owned(reservation, reservation_metadata)
            reservation = None
            reservation_metadata = None
            _fsync_directory(phase_dir)
            return destination
    except Exception as error:
        cleanup_error: Exception | None = None
        try:
            if temporary is not None:
                _remove_owned(temporary, temporary_metadata)
            if destination is not None and destination_metadata is not None:
                _remove_owned(destination, destination_metadata)
            if reservation is not None:
                _remove_owned(reservation, reservation_metadata)
            _fsync_directory(phase_dir)
        except Exception as cleanup:
            cleanup_error = cleanup
        if isinstance(error, ResponseError):
            if cleanup_error is not None:
                error.add_note(f"response cleanup incomplete: {cleanup_error}")
            raise
        if cleanup_error is not None:
            raise ResponseError("response write failed and cleanup was incomplete") from error
        raise ResponseError("response write failed") from error


record_response = capture_response


def _reservation_match(path: Path) -> re.Match[str] | None:
    return _RESERVATION.fullmatch(path.name)


def list_reservation_artifacts(phase_dir: str | os.PathLike[str]) -> tuple[Path, ...]:
    """List valid, directly-owned reservation artifacts in one phase directory."""

    directory = Path(phase_dir)
    metadata = _lstat(directory)
    if metadata is None:
        return ()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ResponseError("response phase directory is unsafe")
    phase = _validate_component(directory.name, "phase")
    found = [
        entry
        for entry in directory.iterdir()
        if (match := _reservation_match(entry)) is not None and match.group(1) == phase
    ]
    for entry in found:
        entry_metadata = _lstat(entry)
        if (
            entry_metadata is None
            or stat.S_ISLNK(entry_metadata.st_mode)
            or not stat.S_ISREG(entry_metadata.st_mode)
            or entry_metadata.st_uid != os.getuid()
            or stat.S_IMODE(entry_metadata.st_mode) != 0o600
        ):
            raise ResponseError("response reservation artifact is unsafe")
    return tuple(sorted(found, key=lambda path: path.name))


def clean_reservation_artifact(
    path: str | os.PathLike[str],
    *,
    outbox_root: str | os.PathLike[str],
    project: str,
    phase: str,
) -> None:
    """Remove one exact reservation artifact, refusing unrelated paths/links."""

    reservation = Path(path)
    match = _reservation_match(reservation)
    if match is None:
        raise ResponseUsageError("path is not a response reservation artifact")
    try:
        expected_parent = outbox_phase_path(outbox_root, project, phase)
    except PathContractError as error:
        raise ResponseUsageError(str(error)) from error
    if reservation.parent != expected_parent or match.group(1) != phase:
        raise ResponseUsageError("reservation path does not belong to its phase")
    metadata = _lstat(reservation)
    if metadata is None:
        return
    ancestry: list[tuple[Path, os.stat_result]] = []
    for directory, private in (
        (expected_parent.parent.parent, False),
        (expected_parent.parent, True),
        (expected_parent, True),
    ):
        directory_metadata = _lstat(directory)
        if (
            directory_metadata is None
            or stat.S_ISLNK(directory_metadata.st_mode)
            or not stat.S_ISDIR(directory_metadata.st_mode)
            or directory_metadata.st_uid != os.getuid()
            or (private and stat.S_IMODE(directory_metadata.st_mode) != 0o700)
        ):
            raise ResponseError("response reservation ancestry is unsafe")
        ancestry.append((directory, directory_metadata))
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise ResponseError("response reservation must be a regular file")
    for directory, expected_metadata in ancestry:
        current = _lstat(directory)
        if (
            current is None
            or (current.st_dev, current.st_ino)
            != (expected_metadata.st_dev, expected_metadata.st_ino)
        ):
            raise ResponseError("response reservation ancestry changed")
    _remove_owned(reservation, metadata)
    _fsync_directory(reservation.parent)


def _parse_main_arguments(arguments: Sequence[str]) -> tuple[str, str | None, Path | None]:
    values = list(arguments)
    if values and values[0] in {"record", "capture"}:
        values.pop(0)
    phase: str | None = None
    source: Path | None = None
    input_selected = False
    while values:
        value = values.pop(0)
        if value in {"--help", "-h"}:
            print("usage: apgr response [record] [--phase PHASE] [--input PATH]")
            raise SystemExit(0)
        if value == "--phase":
            if not values or phase is not None:
                raise ResponseUsageError("--phase requires one value")
            phase = values.pop(0)
            continue
        if value in {"--input", "--file"}:
            if not values or input_selected:
                raise ResponseUsageError(f"{value} requires one value")
            input_selected = True
            source_value = values.pop(0)
            if source_value != "-":
                try:
                    source = Path(source_value).expanduser()
                except (OSError, RuntimeError, ValueError) as error:
                    raise ResponseUsageError("response input path is invalid") from error
            continue
        if value.startswith("--"):
            raise ResponseUsageError(f"unknown response option: {value}")
        if phase is not None:
            raise ResponseUsageError("response phase was specified more than once")
        phase = value
    return phase or "", None, source


def main(
    options: Mapping[str, str],
    arguments: Sequence[str],
    repository_root: Path | None = None,
) -> int:
    """CLI adapter used by the parent APGR dispatcher."""

    try:
        phase, _unused, source = _parse_main_arguments(arguments)
        if not phase:
            raise ResponseUsageError("response phase is required")
        project = options.get("project")
        if project is None and repository_root is not None:
            project = repository_root.name
        if project is None:
            raise ResponseUsageError("--project is required outside a repository")
        if (
            options.get("project") is not None
            and repository_root is not None
            and project != repository_root.name
        ):
            raise ResponseUsageError(
                "--project must match the repository basename for response writes"
            )
        outbox_root = resolve_outbox_root(
            options.get("outbox_root"),
            project_root=repository_root,
            apgr_home=options.get("apgr_home"),
        )
        if source is None:
            created = capture_response(
                outbox_root=outbox_root,
                project=project,
                phase=phase,
                stdin=sys.stdin.buffer,
            )
        else:
            created = capture_response(
                outbox_root=outbox_root,
                project=project,
                phase=phase,
                source=source,
            )
    except SystemExit:
        return 0
    except (ConfigError, PathContractError, ResponseError) as error:
        print(f"apgr response: {error}", file=sys.stderr)
        return 2
    print(created)
    return 0


__all__ = [
    "LOCK_NAME",
    "MAX_RESPONSE_NUMBER",
    "ResponseAllocationError",
    "ResponseError",
    "ResponseInputError",
    "ResponseUsageError",
    "TEMP_GLOB",
    "capture_response",
    "clean_reservation_artifact",
    "list_reservation_artifacts",
    "main",
    "phase_directory",
    "record_response",
]
