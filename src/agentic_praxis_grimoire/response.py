"""Compatibility adapter for the Go-owned APGR response recorder.

The Python module preserves the supported callable names and input-selection
surface, but it does not allocate response numbers, create directories, lock
files, or publish artifacts. Those consequence-bearing operations belong to
the private Go response owner and are reached through :mod:`go_bridge`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import re
import stat
import sys
from typing import BinaryIO

from . import go_bridge
from .config import ConfigError, resolve_outbox_root
from .paths import PathContractError, outbox_phase_path, validate_project_phase


MAX_COMPONENT_LENGTH = 128
MAX_RESPONSE_NUMBER = 999
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
LOCK_NAME = ".response.lock"
TEMP_GLOB = ".response-write.*.tmp"
# Retained scalar names for callers that inspected the former Python owner;
# lock acquisition itself is no longer performed in this module.
LOCK_TIMEOUT_SECONDS = 10.0
LOCK_POLL_SECONDS = 0.01

_RESERVATION = re.compile(
    r"^\.([A-Za-z0-9][A-Za-z0-9._-]*)\.([0-9]{3})\.response\.md\.reservation\.([A-Za-z0-9_-]+)$"
)


class ResponseError(RuntimeError):
    """A Go-owned response artifact could not be created or inspected safely."""


class ResponseUsageError(ResponseError, ValueError):
    """A caller supplied an invalid response identity or input selection."""


class ResponseInputError(ResponseError):
    """The selected response input could not be read as exact bytes."""


class ResponseAllocationError(ResponseError):
    """The Go response owner could not reserve a bounded response number."""


def _read_source(path: Path) -> bytes:
    """Read a compatibility file input without following a source symlink."""

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


def _read_stdin(stdin: BinaryIO) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
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
    except ResponseInputError:
        raise
    except (OSError, TypeError, ValueError) as error:
        raise ResponseInputError("could not read response stdin") from error
    return b"".join(chunks)


def _read_input(
    *,
    body: bytes | bytearray | memoryview | None,
    source: str | os.PathLike[str] | None,
    input_path: str | os.PathLike[str] | None,
    stdin: BinaryIO | None,
) -> bytes:
    """Read one in-memory/stdin input for the compatibility API."""

    if source is not None and input_path is not None:
        raise ResponseUsageError("exactly one response input is required")
    selected_source = source if source is not None else input_path
    selected = sum(item is not None for item in (body, selected_source, stdin))
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
        return _read_source(_input_path(selected_source))
    assert stdin is not None
    return _read_stdin(stdin)


def _input_path(value: str | os.PathLike[str]) -> Path:
    try:
        path = Path(value).expanduser()
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        raise ResponseUsageError("response input path is invalid") from error
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def phase_directory(
    outbox_root: str | os.PathLike[str], project: str, phase: str
) -> Path:
    """Return the canonical phase path without creating or inspecting it."""

    try:
        validate_project_phase(project, phase)
        return outbox_phase_path(outbox_root, project, phase)
    except PathContractError as error:
        raise ResponseUsageError(str(error)) from error


def list_reservation_artifacts(phase_dir: str | os.PathLike[str]) -> tuple[Path, ...]:
    """List reservation names without taking ownership of response mutation."""

    directory = Path(phase_dir)
    try:
        metadata = directory.lstat()
    except FileNotFoundError:
        return ()
    except OSError as error:
        raise ResponseError("could not inspect response phase directory") from error
    if directory.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise ResponseError("response phase directory is unsafe")
    phase = directory.name
    found: list[Path] = []
    try:
        entries = tuple(directory.iterdir())
    except OSError as error:
        raise ResponseError("could not inspect response reservations") from error
    for entry in entries:
        match = _RESERVATION.fullmatch(entry.name)
        if match is None or match.group(1) != phase:
            continue
        try:
            entry_metadata = entry.lstat()
        except OSError as error:
            raise ResponseError("could not inspect response reservation") from error
        if entry.is_symlink() or not stat.S_ISREG(entry_metadata.st_mode):
            raise ResponseError("response reservation artifact is unsafe")
        found.append(entry)
    return tuple(sorted(found, key=lambda path: path.name))


def clean_reservation_artifact(
    path: str | os.PathLike[str],
    *,
    outbox_root: str | os.PathLike[str],
    project: str,
    phase: str,
) -> None:
    """Refuse direct Python reservation deletion after the strangler cutover."""

    del path, outbox_root, project, phase
    raise ResponseError("response reservation cleanup is owned by the Go runtime")


def _parse_main_arguments(arguments: Sequence[str]) -> tuple[str, Path | None]:
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
                source = _input_path(source_value)
            continue
        if value.startswith("--"):
            raise ResponseUsageError(f"unknown response option: {value}")
        if phase is not None:
            raise ResponseUsageError("response phase was specified more than once")
        phase = value
    return phase or "", source


def _bridge_failure(result: go_bridge.CapturedResult) -> ResponseError:
    detail = result.stderr.decode("utf-8", errors="replace").strip()
    if not detail:
        detail = "Go response runtime failed"
    lower = detail.lower()
    if result.returncode == 130 or "interrupted" in lower:
        return ResponseError("response capture interrupted")
    if any(token in lower for token in ("input", "stdin", "8 mib", "regular file")):
        return ResponseInputError(detail)
    if any(
        token in lower
        for token in (
            "requires",
            "invalid",
            "exactly one",
            "option",
            "must be absolute",
            "must be clean",
        )
    ):
        return ResponseUsageError(detail)
    if any(
        token in lower
        for token in (
            "--project",
            "--phase",
            "project is ",
            "phase is ",
            "project must ",
            "phase must ",
        )
    ):
        return ResponseUsageError(detail)
    if any(token in lower for token in ("lock", "number", "reservation", "contention")):
        return ResponseAllocationError(detail)
    return ResponseError(detail)


def _created_path(result: go_bridge.CapturedResult) -> Path:
    if result.returncode != 0:
        raise _bridge_failure(result)
    output = result.stdout.decode("utf-8", errors="strict").strip()
    if not output or "\n" in output or "\r" in output:
        raise ResponseError("Go response runtime returned an invalid created path")
    try:
        path = Path(output)
    except (TypeError, ValueError) as error:
        raise ResponseError("Go response runtime returned an invalid created path") from error
    if not path.is_absolute() or path != Path(os.path.normpath(path)):
        raise ResponseError("Go response runtime returned a non-canonical created path")
    return path


def capture_response(
    *,
    outbox_root: str | os.PathLike[str],
    project: str,
    phase: str,
    body: bytes | bytearray | memoryview | None = None,
    source: str | os.PathLike[str] | None = None,
    input_path: str | os.PathLike[str] | None = None,
    stdin: BinaryIO | None = None,
    repository_root: Path | None = None,
) -> Path:
    """Delegate one exact response capture to the Go runtime."""

    try:
        try:
            validate_project_phase(project, phase)
        except PathContractError as error:
            raise ResponseUsageError(str(error)) from error
        if source is not None and input_path is not None:
            raise ResponseUsageError("exactly one response input is required")
        selected_source = source if source is not None else input_path
        selected = sum(item is not None for item in (body, selected_source, stdin))
        if selected != 1:
            raise ResponseUsageError("exactly one response input is required")
        input_bytes: bytes | None = None
        source_path: Path | None = None
        if body is not None:
            if not isinstance(body, (bytes, bytearray, memoryview)):
                raise ResponseInputError("response body must be bytes")
            input_bytes = bytes(body)
            if len(input_bytes) > MAX_RESPONSE_BYTES:
                raise ResponseInputError("response input exceeds the 8 MiB limit")
        elif stdin is not None:
            input_bytes = _read_stdin(stdin)
        else:
            assert selected_source is not None
            source_path = _input_path(selected_source)
        outbox = Path(outbox_root).expanduser()
        if not outbox.is_absolute() or outbox != Path(os.path.normpath(outbox)):
            raise ResponseUsageError("outbox root must be an absolute clean path")
        result = go_bridge.run_capture(
            go_bridge.response_arguments(
                repository_root=repository_root,
                outbox_root=outbox,
                project=project,
                phase=phase,
                source=source_path,
            ),
            repository_root=repository_root,
            input_bytes=input_bytes,
        )
        return _created_path(result)
    except go_bridge.GoBridgeError as error:
        raise ResponseError(str(error)) from error


record_response = capture_response


def main(
    options: Mapping[str, str],
    arguments: Sequence[str],
    repository_root: Path | None = None,
) -> int:
    """CLI adapter retaining response aliases while Go owns mutation."""

    try:
        phase, source = _parse_main_arguments(arguments)
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
                repository_root=repository_root,
            )
        else:
            created = capture_response(
                outbox_root=outbox_root,
                project=project,
                phase=phase,
                source=source,
                repository_root=repository_root,
            )
    except SystemExit:
        return 0
    except (ConfigError, PathContractError, ResponseError) as error:
        print(f"apgr response: {error}", file=sys.stderr)
        return 2 if isinstance(error, (ResponseUsageError, ResponseInputError)) else 1
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
