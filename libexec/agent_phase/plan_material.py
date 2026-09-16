"""Dispatcher-owned, byte-bound material for a planning checkpoint.

Provider stdout is retained as raw evidence by the stage runner.  This module
selects the exact bytes that may cross the plan-review boundary and records a
small, run-relative binding for those bytes.  Antigravity is the only provider
with a provider-native file-material adapter; the adapter is deliberately
closed over Antigravity's fixed brain path and never accepts an arbitrary file
path supplied by a caller.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import pwd
import re
import stat
from typing import Any
from urllib.parse import unquote_to_bytes, urlsplit

from .candidate import CandidateError


SCHEMA = "agent-phase-plan-material-v1"
PLAN_MATERIAL_SCHEMA = SCHEMA
CANONICAL_PATH = "plan-material.md"
CANONICAL_ARTIFACT = CANONICAL_PATH
MAX_PLAN_BYTES = 4 * 1024 * 1024

_SAFE_COMPONENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_FILE_URI = re.compile(r"file://[^\s<>\"']+", re.IGNORECASE)
_MARKDOWN_LINK = re.compile(
    r"\[(?P<label>[^\]]*)\]\((?P<uri>file://[^\s<>\"')]+)\)",
    re.IGNORECASE,
)
_MARKDOWN_DELIMITERS = frozenset(" \t\n\r\v\f*_`.,;:!?]}\"')<>")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_BINDING_FIELDS = frozenset(
    {
        "schema",
        "relative_path",
        "bytes",
        "sha256",
        "materialization_kind",
        "provider",
        "profile",
    }
)
_MATERIALIZATION_KINDS = frozenset({"inline_stdout", "antigravity_brain_file"})


class PlanMaterialError(CandidateError):
    """Plan material is absent, unsafe, malformed, or no longer bound."""

    def __init__(self, code: str, detail: str) -> None:
        # Details intentionally describe only the failure class.  In
        # particular, provider-private absolute paths and URIs must not reach
        # dispatcher state, result, or review prompts through an exception.
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class PlanMaterial:
    """Exact bytes and their non-secret, run-relative binding."""

    data: bytes
    binding: dict[str, object]


def _fail(code: str, detail: str) -> PlanMaterialError:
    return PlanMaterialError(code, detail)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_plan_bytes(data: bytes, *, source: str) -> None:
    if type(data) is not bytes:
        raise _fail("PLAN_ARTIFACT_INVALID", "plan material must be bytes")
    if len(data) > MAX_PLAN_BYTES:
        raise _fail(
            "PLAN_ARTIFACT_SOURCE_OVERSIZED" if source == "brain" else "PLAN_ARTIFACT_OVERSIZED",
            "plan material exceeds the bounded plan size",
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _fail(
            "PLAN_ARTIFACT_SOURCE_NOT_UTF8" if source == "brain" else "PLAN_ARTIFACT_NOT_UTF8",
            "plan material is not valid UTF-8",
        ) from error
    if not text.strip():
        raise _fail("PLAN_ARTIFACT_EMPTY", "plan material is empty")


def _binding(
    data: bytes, provider: str, profile: str, materialization_kind: str
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "relative_path": CANONICAL_PATH,
        "bytes": len(data),
        "sha256": _sha256(data),
        "materialization_kind": materialization_kind,
        "provider": provider,
        "profile": profile,
    }


def _effective_home(override: Path | None) -> Path:
    """Resolve the effective account home; the override is test-only plumbing.

    The dispatcher does not expose a provider-home request field.  Tests can
    use the private ``_home`` parameter of :func:`materialize` to keep all
    provider state disposable without changing that production boundary.
    """

    if override is not None:
        return Path(override).absolute()
    try:
        return Path(pwd.getpwuid(os.geteuid()).pw_dir).absolute()
    except (KeyError, OSError) as error:
        raise _fail(
            "PLAN_ARTIFACT_SOURCE_UNREADABLE",
            "effective account home cannot be resolved",
        ) from error


def _extract_uri(text: str, home: Path) -> tuple[str, str] | None:
    candidates: set[tuple[str, str]] = set()
    handled_starts: set[int] = set()
    for match in _MARKDOWN_LINK.finditer(text):
        end = match.end()
        if end < len(text):
            next_char = text[end]
            if not next_char.isspace() and next_char not in _MARKDOWN_DELIMITERS:
                continue
        uri = match.group("uri")
        handled_starts.add(match.start("uri"))
        parts = _brain_parts(uri, home)
        if parts is not None:
            candidates.add(parts)
    for match in _FILE_URI.finditer(text):
        if match.start() in handled_starts:
            continue
        uri = match.group(0).rstrip(".,;:)]}")
        parts = _brain_parts(uri, home)
        if parts is not None:
            candidates.add(parts)
    if len(candidates) > 1:
        raise _fail(
            "PLAN_ARTIFACT_SOURCE_AMBIGUOUS",
            "Antigravity output contains multiple brain plan artifacts",
        )
    return next(iter(candidates), None)


def _brain_parts(uri: str, home: Path) -> tuple[str, str] | None:
    try:
        parsed = urlsplit(uri)
    except ValueError as error:
        raise _fail("PLAN_ARTIFACT_SOURCE_UNSAFE", "malformed file artifact URI") from error
    if parsed.scheme.lower() != "file":
        return None
    try:
        decoded_path_bytes = unquote_to_bytes(parsed.path)
    except ValueError as error:
        raise _fail("PLAN_ARTIFACT_SOURCE_UNSAFE", "file artifact URI is malformed") from error
    home_path = str(home).rstrip("/")
    brain_path = f"{home_path}/.gemini/antigravity-cli/brain"
    brain_path_bytes = brain_path.encode("utf-8")
    if decoded_path_bytes != brain_path_bytes and not decoded_path_bytes.startswith(
        brain_path_bytes + b"/"
    ):
        return None
    try:
        decoded_path = decoded_path_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _fail("PLAN_ARTIFACT_SOURCE_UNSAFE", "file artifact URI is not valid UTF-8") from error
    if "\x00" in decoded_path:
        raise _fail("PLAN_ARTIFACT_SOURCE_UNSAFE", "file artifact URI contains a NUL")
    if parsed.netloc or parsed.query or parsed.fragment:
        raise _fail(
            "PLAN_ARTIFACT_SOURCE_UNSAFE",
            "brain artifact URI contains unsupported authority or suffix data",
        )
    suffix = decoded_path[len(brain_path) :]
    parts = suffix[1:].split("/") if suffix.startswith("/") else []
    if len(parts) != 2:
        raise _fail(
            "PLAN_ARTIFACT_SOURCE_UNSAFE",
            "file artifact does not use the fixed Antigravity brain shape",
        )
    session, name = parts
    if not _SAFE_COMPONENT.fullmatch(session) or not name.endswith(".md"):
        raise _fail(
            "PLAN_ARTIFACT_SOURCE_UNSAFE",
            "file artifact contains an unsafe brain component",
        )
    if not _SAFE_COMPONENT.fullmatch(name[:-3]):
        raise _fail(
            "PLAN_ARTIFACT_SOURCE_UNSAFE",
            "file artifact contains an unsafe brain name",
        )
    return session, name


def _uid() -> int:
    try:
        return os.geteuid()
    except AttributeError:  # pragma: no cover - supported host is POSIX.
        return os.stat(Path.cwd()).st_uid


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_uid,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
    )


def _directory_mode(info: os.stat_result) -> None:
    if not stat.S_ISDIR(info.st_mode):
        raise _fail("PLAN_ARTIFACT_SOURCE_TYPE", "brain path component is not a directory")
    if info.st_uid != _uid():
        raise _fail("PLAN_ARTIFACT_SOURCE_OWNER", "brain path component has the wrong owner")
    if stat.S_IMODE(info.st_mode) & 0o022:
        raise _fail("PLAN_ARTIFACT_SOURCE_MODE", "brain path component has unsafe permissions")


def _file_mode(info: os.stat_result, *, source: str) -> None:
    if stat.S_ISLNK(info.st_mode):
        raise _fail("PLAN_ARTIFACT_SOURCE_SYMLINK", "brain artifact is a symbolic link")
    if not stat.S_ISREG(info.st_mode):
        raise _fail("PLAN_ARTIFACT_SOURCE_TYPE", "brain artifact is not a regular file")
    if info.st_uid != _uid():
        raise _fail("PLAN_ARTIFACT_SOURCE_OWNER", "brain artifact has the wrong owner")
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o022 or mode & 0o111:
        raise _fail("PLAN_ARTIFACT_SOURCE_MODE", "brain artifact has unsafe permissions")
    if info.st_nlink != 1:
        raise _fail("PLAN_ARTIFACT_SOURCE_LINKS", "brain artifact link identity is invalid")
    if info.st_size > MAX_PLAN_BYTES:
        raise _fail("PLAN_ARTIFACT_SOURCE_OVERSIZED", "brain artifact exceeds the bounded plan size")


def _open_directory(parent: int, name: str) -> int:
    try:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError as error:
        raise _fail("PLAN_ARTIFACT_SOURCE_MISSING", "brain artifact path is missing") from error
    except OSError as error:
        raise _fail("PLAN_ARTIFACT_SOURCE_UNREADABLE", "brain artifact path cannot be inspected") from error
    if stat.S_ISLNK(info.st_mode):
        raise _fail("PLAN_ARTIFACT_SOURCE_SYMLINK", "brain path component is a symbolic link")
    _directory_mode(info)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=parent)
    except FileNotFoundError as error:
        raise _fail("PLAN_ARTIFACT_SOURCE_MISSING", "brain artifact path is missing") from error
    except OSError as error:
        raise _fail("PLAN_ARTIFACT_SOURCE_UNREADABLE", "brain artifact path cannot be opened") from error
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(info):
            raise _fail("PLAN_ARTIFACT_SOURCE_REPLACED", "brain path changed while opening")
        _directory_mode(opened)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _read_brain_artifact(home: Path, session: str, name: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        root_fd = os.open(home, flags)
    except OSError as error:
        raise _fail("PLAN_ARTIFACT_SOURCE_MISSING", "effective Antigravity home is unavailable") from error
    descriptors = [root_fd]
    try:
        _directory_mode(os.fstat(root_fd))
        parent = root_fd
        for component in (".gemini", "antigravity-cli", "brain", session):
            parent = _open_directory(parent, component)
            descriptors.append(parent)
        try:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError as error:
            raise _fail("PLAN_ARTIFACT_SOURCE_MISSING", "brain artifact is missing") from error
        except OSError as error:
            raise _fail("PLAN_ARTIFACT_SOURCE_UNREADABLE", "brain artifact cannot be inspected") from error
        _file_mode(info, source="brain")
        file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            descriptor = os.open(name, file_flags, dir_fd=parent)
        except FileNotFoundError as error:
            raise _fail("PLAN_ARTIFACT_SOURCE_MISSING", "brain artifact is missing") from error
        except OSError as error:
            raise _fail("PLAN_ARTIFACT_SOURCE_UNREADABLE", "brain artifact cannot be opened") from error
        descriptors.append(descriptor)
        try:
            opened = os.fstat(descriptor)
            if _identity(opened) != _identity(info):
                raise _fail("PLAN_ARTIFACT_SOURCE_REPLACED", "brain artifact changed while opening")
            _file_mode(opened, source="brain")
            remaining = MAX_PLAN_BYTES + 1
            chunks: list[bytes] = []
            total = 0
            while remaining:
                chunk = os.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                remaining -= len(chunk)
            data = b"".join(chunks)
            if len(data) > MAX_PLAN_BYTES:
                raise _fail("PLAN_ARTIFACT_SOURCE_OVERSIZED", "brain artifact exceeds the bounded plan size")
            after = os.fstat(descriptor)
            try:
                path_after = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except OSError as error:
                raise _fail("PLAN_ARTIFACT_SOURCE_REPLACED", "brain artifact disappeared while reading") from error
            if (
                _identity(after) != _identity(info)
                or _identity(path_after) != _identity(info)
                or len(data) != info.st_size
            ):
                raise _fail("PLAN_ARTIFACT_SOURCE_REPLACED", "brain artifact changed while reading")
            _validate_plan_bytes(data, source="brain")
            return data
        except OSError as error:
            raise _fail("PLAN_ARTIFACT_SOURCE_UNREADABLE", "brain artifact could not be read") from error
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def materialize(
    stdout: bytes,
    provider: str,
    profile: str,
    *,
    _home: Path | None = None,
) -> PlanMaterial:
    """Select canonical plan bytes from provider stdout.

    ``_home`` is intentionally private test plumbing.  Production callers use
    the effective account home inherited by the dispatcher process, and the
    only accepted provider file source is one fixed Antigravity brain artifact.
    """

    if not isinstance(provider, str) or not provider:
        raise _fail("PLAN_ARTIFACT_INVALID", "plan provider is invalid")
    if not isinstance(profile, str) or not profile:
        raise _fail("PLAN_ARTIFACT_INVALID", "plan profile is invalid")
    _validate_plan_bytes(stdout, source="stdout")
    materialization_kind = "inline_stdout"
    data = stdout
    if provider == "antigravity":
        text = stdout.decode("utf-8")
        if _FILE_URI.search(text) is not None:
            effective_home = _effective_home(_home)
            parts = _extract_uri(text, effective_home)
            if parts is not None:
                session, name = parts
                data = _read_brain_artifact(effective_home, session, name)
                materialization_kind = "antigravity_brain_file"
    return PlanMaterial(data, _binding(data, provider, profile, materialization_kind))


def bind(
    stdout: bytes,
    provider: str,
    profile: str,
    *,
    _home: Path | None = None,
) -> dict[str, object]:
    """Compatibility helper returning only the new schema binding."""

    return materialize(stdout, provider, profile, _home=_home).binding


def _validate_binding(binding: dict[str, Any]) -> None:
    if not isinstance(binding, dict) or set(binding) != _BINDING_FIELDS:
        raise _fail("PLAN_ARTIFACT_BINDING_INVALID", "plan material binding schema is invalid")
    if binding["schema"] != SCHEMA or binding["relative_path"] != CANONICAL_PATH:
        raise _fail("PLAN_ARTIFACT_BINDING_INVALID", "plan material binding identity is invalid")
    if (
        type(binding["bytes"]) is not int
        or binding["bytes"] < 1
        or binding["bytes"] > MAX_PLAN_BYTES
        or not isinstance(binding["sha256"], str)
        or _DIGEST.fullmatch(binding["sha256"]) is None
        or binding["materialization_kind"] not in _MATERIALIZATION_KINDS
        or not isinstance(binding["provider"], str)
        or not binding["provider"]
        or not isinstance(binding["profile"], str)
        or not binding["profile"]
    ):
        raise _fail("PLAN_ARTIFACT_BINDING_INVALID", "plan material binding values are invalid")


def write(directory: Any, material: PlanMaterial) -> Path:
    """Write exactly one canonical run-owned plan artifact."""

    _validate_binding(material.binding)
    _validate_plan_bytes(material.data, source="stdout")
    if _sha256(material.data) != material.binding["sha256"] or len(material.data) != material.binding["bytes"]:
        raise _fail("PLAN_ARTIFACT_BINDING_MISMATCH", "plan material bytes disagree with binding")
    if not isinstance(directory, (str, os.PathLike)) and hasattr(directory, "write_bytes"):
        return directory.write_bytes(CANONICAL_PATH, material.data)
    target = Path(directory) / CANONICAL_PATH
    target.write_bytes(material.data)
    return target


def _read_run_artifact(path: Path) -> bytes:
    try:
        info = os.lstat(path)
    except OSError as error:
        raise _fail("PLAN_ARTIFACT_MISSING", "canonical plan artifact is missing") from error
    if stat.S_ISLNK(info.st_mode):
        raise _fail("PLAN_ARTIFACT_SYMLINK", "canonical plan artifact is a symbolic link")
    if not stat.S_ISREG(info.st_mode):
        raise _fail("PLAN_ARTIFACT_TYPE", "canonical plan artifact is not a regular file")
    if info.st_size > MAX_PLAN_BYTES:
        raise _fail("PLAN_ARTIFACT_OVERSIZED", "canonical plan artifact exceeds the bounded plan size")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise _fail("PLAN_ARTIFACT_UNREADABLE", "canonical plan artifact cannot be opened") from error
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(info):
            raise _fail("PLAN_ARTIFACT_REPLACED", "canonical plan artifact changed while opening")
        chunks: list[bytes] = []
        remaining = MAX_PLAN_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        try:
            after_path = os.lstat(path)
        except OSError as error:
            raise _fail("PLAN_ARTIFACT_REPLACED", "canonical plan artifact disappeared while reading") from error
        if len(data) != info.st_size or _identity(os.fstat(descriptor)) != _identity(info) or _identity(after_path) != _identity(info):
            raise _fail("PLAN_ARTIFACT_REPLACED", "canonical plan artifact changed while reading")
        _validate_plan_bytes(data, source="stdout")
        return data
    except OSError as error:
        raise _fail("PLAN_ARTIFACT_UNREADABLE", "canonical plan artifact could not be read") from error
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass


def verify(directory: Any, binding: dict[str, Any]) -> bytes:
    """Read and verify the run-owned artifact against every binding field."""

    _validate_binding(binding)
    root = Path(directory.path) if hasattr(directory, "path") else Path(directory)
    data = _read_run_artifact(root / CANONICAL_PATH)
    if (
        len(data) != binding["bytes"]
        or _sha256(data) != binding["sha256"]
    ):
        raise _fail("PLAN_ARTIFACT_BINDING_MISMATCH", "canonical plan artifact disagrees with binding")
    return data


def materialize_plan(
    stdout: bytes,
    provider: str,
    profile: str,
    *,
    _home: Path | None = None,
) -> PlanMaterial:
    """Descriptive alias retained for callers that name the operation."""

    return materialize(stdout, provider, profile, _home=_home)


def verify_artifact(directory: Any, binding: dict[str, Any]) -> bytes:
    return verify(directory, binding)
