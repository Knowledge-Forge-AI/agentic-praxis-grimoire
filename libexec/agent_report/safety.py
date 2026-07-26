"""Path, source, lock, and same-directory replacement safety."""

from __future__ import annotations

from collections.abc import Callable
import contextlib
import os
from pathlib import Path, PurePath, PureWindowsPath
import re
import secrets
import shutil
import stat
import tempfile
import time

from .models import ParsedRecord
from .rendering import parse_canonical_records


MAX_SOURCE_BYTES = 8 * 1024 * 1024
_TICKET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class UsageError(ValueError):
    """A command-line value violates a deterministic usage contract."""


class ReportError(RuntimeError):
    """A report cannot be generated or appended safely."""


def contains_control(value: str) -> bool:
    """Return true for ASCII control characters rejected by report fields."""

    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def header_value(value: str) -> str:
    """Render empty operational metadata with the legacy NULL marker."""

    return value if value else "NULL"


def validate_ticket(value: str) -> str:
    """Validate one bounded phase/ticket file-name component."""

    if (
        len(value) > 128
        or value in {".", ".."}
        or not _TICKET.fullmatch(value)
    ):
        raise UsageError("ticket id is unsafe")
    return value


def validate_metadata(value: str, name: str = "operational metadata") -> str:
    """Reject control characters from line-oriented report fields."""

    if contains_control(value):
        raise UsageError(f"{name} contains a control character")
    return value


def source_value_is_absolute(value: str) -> bool:
    """Apply native lexical semantics before concrete-path normalization."""

    path_type = PureWindowsPath if os.name == "nt" else PurePath
    return path_type(value).is_absolute()


def validate_status_doc(value: str | None) -> str:
    """Validate an optional repository-relative status-document identity."""

    if value is None:
        return "NONE"
    validate_metadata(value, "status document path")
    if not value:
        raise UsageError("status document path is empty")
    separator = "\\" if os.name == "nt" else "/"
    if (
        separator * 2 in value
        or f"{separator}.{separator}" in value
        or f"{separator}..{separator}" in value
        or value.endswith(f"{separator}.")
        or value.endswith(f"{separator}..")
    ):
        raise UsageError("status document path must be clean and repository-relative")
    path: PurePath
    if os.name == "nt":
        path = PureWindowsPath(value)
    else:
        path = PurePath(value)
    if path.is_absolute() or path.anchor or any(part in {"", ".", ".."} for part in path.parts):
        raise UsageError("status document path must be clean and repository-relative")
    if os.name != "nt" and "\\" in value:
        raise UsageError("status document path uses a non-native separator")
    return value


def validate_source_path(
    path: Path,
    destination: Path | None = None,
    *,
    source_value: str | None = None,
) -> os.stat_result:
    """Validate an exact operational-body source on the supported POSIX boundary."""

    _validate_source_spelling(source_value)
    _validate_source_location(path)
    _validate_source_destination(path, destination)
    metadata = _source_metadata(path)
    return _validate_source_metadata(path, metadata)


def _validate_source_spelling(source_value: str | None) -> None:
    """Reject an explicitly supplied source spelling with a trailing separator."""

    separators = tuple(value for value in (os.sep, os.altsep) if value)
    if source_value is not None and source_value.endswith(separators):
        raise ReportError("source operational report is unsafe")


def _validate_source_location(path: Path) -> None:
    """Require an absolute, lexically clean source location."""

    if not path.is_absolute():
        raise UsageError("operational report path must be absolute")
    if any(part in {".", ".."} for part in path.parts):
        raise UsageError("operational report path is not clean")


def _validate_source_destination(path: Path, destination: Path | None) -> None:
    """Reject a source that aliases its canonical destination."""

    if destination is None:
        return
    try:
        aliases_destination = path.samefile(destination)
    except FileNotFoundError:
        return
    if aliases_destination:
        raise ReportError("source operational report is the destination report")


def _source_metadata(path: Path) -> os.stat_result:
    """Read source metadata through the lexical path without following links."""

    try:
        return path.lstat()
    except OSError as error:
        raise ReportError("source operational report is unsafe") from error


def _validate_source_metadata(path: Path, metadata: os.stat_result) -> os.stat_result:
    """Apply the supported platform's source-file safety contract."""

    if os.name == "nt":
        return _validate_windows_source(path, metadata)
    return _validate_posix_source(path, metadata)


def _validate_windows_source(path: Path, metadata: os.stat_result) -> os.stat_result:
    """Reject uncharacterized Windows reparse and non-regular source state."""

    if path.is_symlink() or _is_windows_reparse(metadata):
        raise ReportError("source operational report has unsupported Windows reparse semantics")
    if not stat.S_ISREG(metadata.st_mode):
        raise ReportError("source operational report is unsafe")
    return metadata


def _validate_posix_source(path: Path, metadata: os.stat_result) -> os.stat_result:
    """Require the characterized POSIX owner, mode, link, and file-type state."""

    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise ReportError("source operational report is unsafe")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ReportError("source operational report permissions are unsafe")
    if metadata.st_nlink != 1:
        raise ReportError("source operational report hard links are unsafe")
    return metadata


def injected_failure(step: str) -> None:
    """Raise the existing test-only failure at a named generation boundary."""

    testing = (
        os.environ.get("AGENT_REPORT_TESTING")
        or os.environ.get("agent_REPORT_TESTING")
        or os.environ.get("GIT_SHOW_REPORT_TESTING")
    )
    selected = (
        os.environ.get("AGENT_REPORT_TEST_FAIL_STEP")
        or os.environ.get("agent_REPORT_TEST_FAIL_STEP")
        or os.environ.get("GIT_SHOW_REPORT_TEST_FAIL_STEP")
    )
    if testing == "1" and selected == step:
        raise ReportError(f"injected failure at {step}")


def read_validated_source(
    path: Path,
    expected: os.stat_result,
    *,
    max_bytes: int,
) -> bytes:
    """Read the exact validated POSIX source through one no-follow descriptor."""

    if os.name == "nt":
        raise ReportError("source read safety is unsupported on Windows")
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    if not no_follow:
        raise ReportError("source no-follow safety is unavailable")
    flags = os.O_RDONLY | no_follow | getattr(os, "O_CLOEXEC", 0)
    injected_failure("source-read")
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ReportError("source operational report is unsafe") from error
    try:
        before = os.fstat(descriptor)
        expected_identity = _source_identity(expected)
        if _source_identity(before) != expected_identity:
            raise ReportError("source operational report changed before reading")
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = os.read(descriptor, min(65536, max_bytes + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > max_bytes:
                raise ReportError("source operational report is oversized")
        after = os.fstat(descriptor)
        if _source_identity(after) != expected_identity or size != expected.st_size:
            raise ReportError("source operational report changed during reading")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _source_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def testing_pause(step: str) -> None:
    """Expose a bounded synchronization point for drift and interruption tests."""

    if os.environ.get("AGENT_REPORT_TESTING") != "1":
        return
    if os.environ.get("AGENT_REPORT_TEST_PAUSE_STEP") != step:
        return
    signal_value = os.environ.get("AGENT_REPORT_TEST_SIGNAL_DIR")
    if not signal_value:
        raise ReportError("test pause signal directory is unavailable")
    signal_dir = Path(signal_value)
    signal_dir.joinpath("ready").touch(mode=0o600)
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        if signal_dir.joinpath("continue").exists():
            return
        time.sleep(0.01)
    raise ReportError("test pause timed out")


@contextlib.contextmanager
def private_temporary_directory(command_name: str):
    """Create and deterministically remove one invocation-owned private directory."""

    path = Path(tempfile.mkdtemp(prefix=f"{command_name}."))
    path.chmod(0o700)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


RecordBuilder = Callable[[bytes, tuple[ParsedRecord, ...]], bytes]


class Destination:
    """Canonical private report destination with serialized atomic append."""

    def __init__(self, git_root: Path, ticket: str) -> None:
        if os.name == "nt":
            raise ReportError(
                "Windows report replacement safety is not yet characterized; "
                "interpreter invocation is supported only for fail-closed diagnostics"
            )
        self.project = git_root.name
        validate_metadata(self.project, "repository name")
        configured = os.environ.get("GIT_SHOW_REPORT_ROOT")
        self.root = Path(configured) if configured else Path.home() / "Documents" / "agent"
        self.directory = self.root / self.project
        self.path = self.directory / f"{ticket}.report.txt"
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.ticket = ticket
        self._token = f"{os.getpid()}-{secrets.token_hex(8)}-{ticket}"
        self._locked = False
        self._lock_identity: tuple[int, int] | None = None
        self._owner_identity: tuple[int, int] | None = None
        self._owner_initialized = False
        self._prepare_directory()

    def _prepare_directory(self) -> None:
        if not self.root.exists():
            self.root.mkdir(parents=True)
        if self.directory.is_symlink():
            raise ReportError("report directory is unsafe")
        try:
            self.directory.mkdir()
            self.directory.chmod(0o700)
        except FileExistsError:
            pass
        _validate_private_directory(self.directory)

    @contextlib.contextmanager
    def lock(self):
        """Acquire the report's atomic lock directory and release only our token."""

        for _ in range(200):
            try:
                self.lock_path.mkdir()
                metadata = self.lock_path.lstat()
                if self.lock_path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
                    raise ReportError("report append lock is unsafe")
                self._lock_identity = (metadata.st_dev, metadata.st_ino)
                self._locked = True
                break
            except FileExistsError:
                try:
                    metadata = self.lock_path.lstat()
                except FileNotFoundError:
                    continue
                if self.lock_path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
                    raise ReportError("report append lock is unsafe")
                time.sleep(0.01)
        if not self._locked:
            raise ReportError("report append is already active")
        try:
            self.lock_path.chmod(0o700)
            owner = self.lock_path / "owner"
            descriptor = os.open(owner, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                owner_metadata = os.fstat(descriptor)
                self._owner_identity = (owner_metadata.st_dev, owner_metadata.st_ino)
            finally:
                os.close(descriptor)
            owner.write_text(self._token + "\n", encoding="utf-8")
            owner.chmod(0o600)
            self._owner_initialized = True
            yield
        finally:
            self._release_lock()

    def _release_lock(self) -> None:
        if not self._locked:
            return
        owner = self.lock_path / "owner"
        try:
            metadata = self.lock_path.lstat()
            identity = (metadata.st_dev, metadata.st_ino)
            if (
                self.lock_path.is_symlink()
                or not stat.S_ISDIR(metadata.st_mode)
                or identity != self._lock_identity
            ):
                return
            if not owner.exists():
                self.lock_path.rmdir()
            elif not owner.is_symlink() and owner.is_file():
                owner_metadata = owner.lstat()
                owner_identity = (owner_metadata.st_dev, owner_metadata.st_ino)
                if owner_identity != self._owner_identity:
                    return
                if (
                    not self._owner_initialized
                    or owner.read_text(encoding="utf-8").rstrip("\n") == self._token
                ):
                    owner.unlink()
                    self.lock_path.rmdir()
        except OSError:
            pass
        finally:
            self._locked = False
            self._lock_identity = None
            self._owner_identity = None
            self._owner_initialized = False

    def append(self, record_or_builder: bytes | RecordBuilder) -> bytes:
        """Append one complete record after validation under the phase lock."""

        replacement: Path | None = None
        with self.lock():
            existing = self._read_existing()
            try:
                records = parse_canonical_records(existing)
            except ValueError as error:
                raise ReportError("existing report record structure is unsafe") from error
            record = (
                record_or_builder(existing, records)
                if callable(record_or_builder)
                else record_or_builder
            )
            parsed_new = parse_canonical_records(record)
            if len(parsed_new) != 1 or parsed_new[0].start != 0 or parsed_new[0].end != len(record):
                raise ReportError("report record envelope is invalid")
            descriptor, replacement_value = tempfile.mkstemp(
                prefix=f".{self.ticket}.report.", dir=self.directory
            )
            replacement = Path(replacement_value)
            try:
                os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(existing)
                    if existing and not existing.endswith(b"\n"):
                        stream.write(b"\n")
                    stream.write(record)
                    stream.flush()
                    os.fsync(stream.fileno())
                injected_failure("before-destination-replacement")
                os.replace(replacement, self.path)
                replacement = None
                self.path.chmod(0o600)
                _fsync_directory(self.directory)
            finally:
                if replacement is not None:
                    replacement.unlink(missing_ok=True)
        return record

    def _read_existing(self) -> bytes:
        try:
            metadata = self.path.lstat()
        except FileNotFoundError:
            return b""
        if self.path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise ReportError("existing report file is unsafe")
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise ReportError("existing report file is unsafe")
        return self.path.read_bytes()


def _validate_private_directory(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ReportError("report directory is unsafe") from error
    if path.is_symlink() or not stat.S_ISDIR(metadata.st_mode):
        raise ReportError("report directory is unsafe")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise ReportError("report directory is unsafe")


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _is_windows_reparse(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse)
