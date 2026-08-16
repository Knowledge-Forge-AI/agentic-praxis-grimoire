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
_PRIMARY_TYPES = {
    "git-show-report": "git.show",
    "git-diff-report": "git.diff",
    "operational-report": "ops",
}


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


def validate_path_identifier(value: str, name: str = "path identifier") -> str:
    """Validate a bounded identifier used as one outbox path component."""

    if len(value) > 128 or value in {".", ".."} or not _TICKET.fullmatch(value):
        raise UsageError(f"{name} is unsafe")
    return value


def validate_metadata(value: str, name: str = "operational metadata") -> str:
    """Reject control characters from line-oriented report fields."""

    if contains_control(value):
        raise UsageError(f"{name} contains a control character")
    return value


def infer_project_name(git_root: Path) -> str:
    """Return a safe report identity with every leading ASCII period removed."""

    project = git_root.name.lstrip(".")
    if not project:
        raise ReportError("normalized repository name is empty")
    if contains_control(project):
        raise ReportError("repository name contains a control character")
    if "/" in project or "\\" in project:
        raise ReportError("repository name contains a path separator")
    return project


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
    """Private report destination with legacy and single-primary outbox modes.

    ``GIT_SHOW_REPORT_ROOT`` intentionally selects the historical omnibus
    layout.  Without it, each phase owns a private directory and exactly one
    current primary artifact.  The latter mode is deliberately kept here,
    beside the existing lock and replacement code, so the Git and operational
    adapters cannot accidentally choose different storage semantics.
    """

    def __init__(self, git_root: Path, ticket: str, *, outbox_root: Path | None = None) -> None:
        if os.name == "nt":
            raise ReportError(
                "Windows report replacement safety is not yet characterized; "
                "interpreter invocation is supported only for fail-closed diagnostics"
            )
        self.project = infer_project_name(git_root)
        self.ticket = validate_path_identifier(ticket, "phase identifier")
        configured = os.environ.get("GIT_SHOW_REPORT_ROOT")
        # An explicit canonical outbox is authoritative.  The legacy variable
        # remains a compatibility-wrapper selector only when no canonical
        # destination was supplied by the APGR route.
        self.legacy = bool(configured) and outbox_root is None
        if self.legacy:
            assert configured is not None
            self.root = Path(configured)
            self.project_directory = self.root / self.project
            self.directory = self.project_directory
            self._legacy_path = self.directory / f"{self.ticket}.report.txt"
            self.lock_path = self._legacy_path.with_name(
                self._legacy_path.name + ".lock"
            )
            self.transaction_path = self._legacy_path.with_name(
                self._legacy_path.name + ".transaction"
            )
        else:
            validate_path_identifier(self.project, "project identifier")
            configured_outbox = os.environ.get("APGR_OUTBOX_ROOT")
            if outbox_root is not None:
                self.root = Path(outbox_root)
                if not self.root.is_absolute():
                    raise UsageError("outbox root must be absolute")
            elif configured_outbox:
                self.root = Path(configured_outbox)
                if not self.root.is_absolute():
                    raise UsageError("APGR_OUTBOX_ROOT must be absolute")
            else:
                self.root = Path.home() / "Documents" / "agent" / "outbox"
            self.project_directory = self.root / self.project
            self.directory = self.project_directory / self.ticket
            self._legacy_path = None
            self.lock_path = self.directory / ".phase.lock"
            self.transaction_path = self.directory / ".phase.transaction"
        self._show_path = self.directory / f"{self.ticket}.git.show.report.txt"
        self._diff_path = self.directory / f"{self.ticket}.git.diff.report.txt"
        self._ops_path = self.directory / f"{self.ticket}.ops.report.txt"
        self._token = f"{os.getpid()}-{secrets.token_hex(8)}-{self.ticket}"
        self._locked = False
        self._lock_identity: tuple[int, int] | None = None
        self._owner_identity: tuple[int, int] | None = None
        self._owner_initialized = False
        self._transaction_identity: tuple[int, int] | None = None
        self._prepare_directory()

    @property
    def path(self) -> Path:
        """Return the current primary path, refusing unresolved publication."""

        self._ensure_no_unresolved_transaction()
        if self.legacy:
            assert self._legacy_path is not None
            return self._legacy_path
        return self._current_path() or self._ops_path

    @property
    def primary_paths(self) -> tuple[Path, Path, Path]:
        """Return show, diff, and ops paths in their canonical order."""

        return self._show_path, self._diff_path, self._ops_path

    def _prepare_directory(self) -> None:
        if self.root.is_symlink():
            raise ReportError("report root is unsafe")
        try:
            self.root.mkdir(parents=True)
            self.root.chmod(0o700)
        except FileExistsError:
            pass
        _validate_private_directory(self.root)
        if self.project_directory.is_symlink():
            raise ReportError("report directory is unsafe")
        try:
            self.project_directory.mkdir()
            self.project_directory.chmod(0o700)
        except FileExistsError:
            pass
        _validate_private_directory(self.project_directory)
        if self.legacy:
            return
        if self.directory.is_symlink():
            raise ReportError("phase directory is unsafe")
        try:
            self.directory.mkdir()
            self.directory.chmod(0o700)
        except FileExistsError:
            pass
        _validate_private_directory(self.directory)

    def _ensure_no_unresolved_transaction(self) -> None:
        try:
            metadata = self.transaction_path.lstat()
        except FileNotFoundError:
            return
        except OSError as error:
            raise ReportError("report transaction marker is unsafe") from error
        if (
            self.transaction_path.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ReportError("report transaction marker is unsafe")
        raise ReportError("unresolved report transaction marker")

    def recover_transaction(self) -> bool:
        """Complete or roll back one interrupted supersession under the phase lock."""

        if self.legacy:
            return False
        with self.lock():
            try:
                metadata = self.transaction_path.lstat()
            except FileNotFoundError:
                return False
            except OSError as error:
                raise ReportError("report transaction marker is unsafe") from error
            raw = self._read_regular_file(self.transaction_path, metadata)
            try:
                lines = raw.decode("utf-8").splitlines()
            except UnicodeDecodeError as error:
                raise ReportError("report transaction marker is unsafe") from error
            fields = dict(
                line.split(": ", 1) for line in lines[1:] if ": " in line
            )
            if (
                not lines
                or lines[0] != "agent-report-transaction-v1"
                or fields.get("phase") != self.ticket
                or "target" not in fields
                or "stale" not in fields
            ):
                raise ReportError("report transaction marker is unsafe")
            allowed = {path.name: path for path in self.primary_paths}
            target = allowed.get(fields["target"])
            stale_names = tuple(filter(None, fields["stale"].split(",")))
            if target is None or any(name not in allowed for name in stale_names):
                raise ReportError("report transaction marker is unsafe")
            if self._exists_safe(target):
                for name in stale_names:
                    if name != target.name:
                        self._unlink_stale(allowed[name])
            current = self.transaction_path.lstat()
            if (current.st_ino, current.st_dev) != (metadata.st_ino, metadata.st_dev):
                raise ReportError("report transaction marker ownership changed")
            self.transaction_path.unlink()
            _fsync_directory(self.directory)
            return True

    @contextlib.contextmanager
    def lock(self):
        """Acquire the report's atomic lock directory and release only our token."""

        recovered = False
        for _ in range(400):
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
                if not recovered and self._recover_stale_lock(metadata):
                    recovered = True
                    continue
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
                _write_all(descriptor, (self._token + "\n").encode("ascii"))
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            self._owner_initialized = True
            yield
        finally:
            self._release_lock()

    def _recover_stale_lock(self, directory_metadata: os.stat_result) -> bool:
        """Remove one owner-proven lock whose recorded process no longer exists."""

        owner = self.lock_path / "owner"
        try:
            metadata = owner.lstat()
        except FileNotFoundError:
            if time.time() - directory_metadata.st_mtime < 1.0:
                return False
            current_directory = self.lock_path.lstat()
            if (
                (current_directory.st_dev, current_directory.st_ino)
                != (directory_metadata.st_dev, directory_metadata.st_ino)
                or any(self.lock_path.iterdir())
            ):
                return False
            self.lock_path.rmdir()
            _fsync_directory(self.directory)
            return True
        except OSError as error:
            raise ReportError("report append lock owner is unsafe") from error
        if (
            owner.is_symlink()
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ReportError("report append lock owner is unsafe")
        try:
            token = self._read_regular_file(owner, metadata).decode("ascii").rstrip("\n")
        except UnicodeDecodeError as error:
            raise ReportError("report append lock owner is unsafe") from error
        try:
            pid = int(token.split("-", 1)[0])
            if pid <= 0:
                raise ValueError
        except ValueError as error:
            raise ReportError("report append lock owner is unsafe") from error
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        except PermissionError:
            return False
        else:
            return False
        current_directory = self.lock_path.lstat()
        current_owner = owner.lstat()
        if (
            (current_directory.st_dev, current_directory.st_ino)
            != (directory_metadata.st_dev, directory_metadata.st_ino)
            or (current_owner.st_dev, current_owner.st_ino)
            != (metadata.st_dev, metadata.st_ino)
        ):
            raise ReportError("report append lock ownership changed")
        owner.unlink()
        self.lock_path.rmdir()
        _fsync_directory(self.directory)
        return True

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
        """Append a record; a different primary type supersedes its stale sibling."""

        with self.lock():
            self._ensure_no_unresolved_transaction()
            current = self._current_path()
            existing = self._read_existing(current)
            records = self._parse_existing(existing)
            record = (
                record_or_builder(existing, records)
                if callable(record_or_builder)
                else record_or_builder
            )
            parsed_new = self._parse_new(record)
            target = self._target_for_type(parsed_new[0].record.record_type)
            if target != current:
                existing = self._read_existing(target)
                records = self._parse_existing(existing)
                if callable(record_or_builder):
                    record = record_or_builder(existing, records)
                    parsed_new = self._parse_new(record)
                    target = self._target_for_type(parsed_new[0].record.record_type)
            combined = existing + (b"\n" if existing and not existing.endswith(b"\n") else b"") + record
            self._parse_existing(combined)
            if self.legacy:
                return self._replace_legacy(combined, target)
            stale = tuple(path for path in self.primary_paths if path != target)
            return self._replace_outbox(target, combined, stale)

    @staticmethod
    def _parse_existing(existing: bytes) -> tuple[ParsedRecord, ...]:
        try:
            return parse_canonical_records(existing)
        except ValueError as error:
            raise ReportError("existing report record structure is unsafe") from error

    @staticmethod
    def _parse_new(record: bytes) -> tuple[ParsedRecord, ...]:
        try:
            parsed = parse_canonical_records(record)
        except ValueError as error:
            raise ReportError("report record envelope is invalid") from error
        if len(parsed) != 1 or parsed[0].start != 0 or parsed[0].end != len(record):
            raise ReportError("report record envelope is invalid")
        return parsed

    def _target_for_type(self, record_type: str) -> Path:
        if self.legacy:
            assert self._legacy_path is not None
            return self._legacy_path
        suffix = _PRIMARY_TYPES.get(record_type)
        if suffix == "git.show":
            return self._show_path
        if suffix == "git.diff":
            return self._diff_path
        if suffix == "ops":
            git_path = self._current_git_path()
            return self._ops_path if git_path is None else git_path
        raise ReportError("unsupported report record type for the APGR outbox")

    def _replace_legacy(self, combined: bytes, target: Path) -> bytes:
        return self._write_replacement(combined, target, f".{self.ticket}.report.")

    def _replace_outbox(
        self, target: Path, combined: bytes, stale: tuple[Path, ...]
    ) -> bytes:
        self._begin_transaction(target, stale)
        try:
            result = self._write_replacement(combined, target, f".{self.ticket}.primary.")
            for path in stale:
                self._unlink_stale(path)
            self._finish_transaction()
            return result
        except BaseException:
            # Retain the marker: recovery can distinguish pre-publication rollback
            # from post-publication stale-primary completion.
            self._transaction_identity = None
            raise

    def _write_replacement(self, combined: bytes, target: Path, prefix: str) -> bytes:
        replacement: Path | None = None
        descriptor, replacement_value = tempfile.mkstemp(prefix=prefix, dir=self.directory)
        replacement = Path(replacement_value)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(combined)
                stream.flush()
                os.fsync(stream.fileno())
            injected_failure("before-destination-replacement")
            os.replace(replacement, target)
            replacement = None
            target.chmod(0o600)
            _fsync_directory(self.directory)
            return combined
        finally:
            if replacement is not None:
                replacement.unlink(missing_ok=True)

    def _begin_transaction(self, target: Path, stale: tuple[Path, ...]) -> None:
        self._ensure_no_unresolved_transaction()
        try:
            descriptor = os.open(
                self.transaction_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as error:
            self._ensure_no_unresolved_transaction()
            raise ReportError("report transaction marker is already active") from error
        try:
            self._transaction_identity = os.fstat(descriptor).st_ino, os.fstat(descriptor).st_dev
            details = "\n".join(
                (
                    "agent-report-transaction-v1",
                    f"phase: {self.ticket}",
                    f"target: {target.name}",
                    "stale: " + ",".join(path.name for path in stale),
                    f"token: {self._token}",
                    "",
                )
            ).encode("utf-8")
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(details)
                stream.flush()
                os.fsync(stream.fileno())
            _fsync_directory(self.directory)
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            self.transaction_path.unlink(missing_ok=True)
            self._transaction_identity = None
            raise

    def _finish_transaction(self) -> None:
        if self._transaction_identity is None:
            return
        metadata = self.transaction_path.lstat()
        identity = metadata.st_ino, metadata.st_dev
        if identity != self._transaction_identity:
            raise ReportError("report transaction marker ownership changed")
        self.transaction_path.unlink()
        _fsync_directory(self.directory)
        self._transaction_identity = None

    def _abort_transaction(self) -> None:
        if self._transaction_identity is None:
            return
        try:
            metadata = self.transaction_path.lstat()
            identity = metadata.st_ino, metadata.st_dev
            if identity == self._transaction_identity:
                self.transaction_path.unlink()
                _fsync_directory(self.directory)
        except OSError:
            pass
        finally:
            self._transaction_identity = None

    def _unlink_stale(self, path: Path) -> None:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            return
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise ReportError("stale report artifact is unsafe")
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise ReportError("stale report artifact is unsafe")
        path.unlink()

    def _current_git_path(self) -> Path | None:
        present = [path for path in (self._show_path, self._diff_path) if self._exists_safe(path)]
        if len(present) > 1:
            raise ReportError("multiple current Git report artifacts")
        return present[0] if present else None

    def _current_path(self) -> Path | None:
        if self.legacy:
            return self._legacy_path
        git_path = self._current_git_path()
        ops_present = self._exists_safe(self._ops_path)
        if git_path is not None and ops_present:
            raise ReportError("multiple current primary report artifacts")
        if git_path is not None:
            return git_path
        return self._ops_path if ops_present else None

    def _exists_safe(self, path: Path) -> bool:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            return False
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise ReportError("existing report file is unsafe")
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise ReportError("existing report file is unsafe")
        return True

    def _read_existing(self, path: Path | None = None) -> bytes:
        self._ensure_no_unresolved_transaction()
        target = self.path if path is None else path
        try:
            metadata = target.lstat()
        except FileNotFoundError:
            return b""
        except OSError as error:
            raise ReportError("existing report file is unsafe") from error
        return self._read_regular_file(target, metadata)

    @staticmethod
    def _read_regular_file(path: Path, expected: os.stat_result) -> bytes:
        """Read one exact private regular file without following replacement links."""

        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
        except OSError as error:
            raise ReportError("existing report file is unsafe") from error
        try:
            observed = os.fstat(descriptor)
            if (
                not stat.S_ISREG(observed.st_mode)
                or observed.st_uid != os.getuid()
                or stat.S_IMODE(observed.st_mode) != 0o600
                or (observed.st_dev, observed.st_ino)
                != (expected.st_dev, expected.st_ino)
            ):
                raise ReportError("existing report file is unsafe")
            chunks: list[bytes] = []
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
            return b"".join(chunks)
        except OSError as error:
            raise ReportError("existing report file is unsafe") from error
        finally:
            os.close(descriptor)


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


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(descriptor, view[offset:])
        if written <= 0:
            raise OSError("report lock owner write made no progress")
        offset += written


def _is_windows_reparse(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse)
