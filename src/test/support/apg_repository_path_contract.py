"""Repository-resident descriptor-relative path and read boundary."""

from __future__ import annotations

from contextvars import ContextVar, Token
import fnmatch
import os
from pathlib import Path
import stat
from typing import NoReturn, Sequence

from apg_exact_read_contract import READ_CHUNK_BYTES, read_exact
from apg_repository_absence_contract import confirm_component_absent


DEFAULT_MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_RETAINED_COMPONENTS = 4096
_open_component = os.open
_read_chunk = os.read
_read_link = os.readlink
_stat_component = os.stat
_fstat = os.fstat
_close_descriptor = os.close
_duplicate_descriptor = os.dup
_list_directory = os.listdir


class RepositoryPathError(ValueError):
    """A repository owner violates the physical path contract."""


def _fail(message: str) -> NoReturn:
    raise RepositoryPathError(message)


def _required_flags() -> tuple[int, int]:
    names = ("O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW")
    if any(not hasattr(os, name) for name in names):
        _fail("descriptor-relative no-follow traversal is unsupported")
    if os.open not in os.supports_dir_fd or os.stat not in os.supports_dir_fd:
        _fail("descriptor-relative no-follow traversal is unsupported")
    if os.readlink not in os.supports_dir_fd:
        _fail("descriptor-relative no-follow readlink is unsupported")
    common = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    return common, common | os.O_DIRECTORY


def _components(relative: str) -> tuple[str, ...]:
    if not isinstance(relative, str) or not relative or relative.startswith("/"):
        _fail("owner must be a nonempty repository-relative POSIX path")
    if "\\" in relative:
        _fail("repository-relative path must use POSIX separators")
    parts = relative.split("/")
    if any(
        not part
        or part in {".", ".."}
        or any(ord(character) < 32 or ord(character) == 127 for character in part)
        for part in parts
    ):
        _fail("repository-relative path has an invalid component")
    return tuple(parts)


def _link_text_components(link_text: str) -> tuple[str, ...]:
    if (
        not isinstance(link_text, str)
        or not link_text
        or link_text.startswith("/")
        or "\\" in link_text
    ):
        _fail("projection target must be a relative POSIX link")
    parts = link_text.split("/")
    if any(
        not part
        or part == "."
        or any(ord(character) < 32 or ord(character) == 127 for character in part)
        for part in parts
    ):
        _fail("projection target has an invalid component")
    return tuple(parts)


def _resolve_link_parts(
    parent: Sequence[str], link_text: str
) -> tuple[str, ...]:
    resolved = list(parent)
    for part in _link_text_components(link_text):
        if part == "..":
            if not resolved:
                _fail("projection target escapes the repository root")
            resolved.pop()
        else:
            resolved.append(part)
    if not resolved:
        _fail("projection target must name a repository owner")
    return tuple(resolved)


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


def _matches(pattern: Sequence[str], path: Sequence[str]) -> bool:
    if not pattern:
        return not path
    if pattern[0] == "**":
        return _matches(pattern[1:], path) or (
            bool(path) and _matches(pattern, path[1:])
        )
    return bool(path) and fnmatch.fnmatchcase(path[0], pattern[0]) and _matches(
        pattern[1:], path[1:]
    )


class _PathChain:
    """Retain one complete repository-relative observation for revalidation.

    Every descended component keeps its direct parent descriptor, its component
    name, the entry identity observed before the child was opened, and the
    opened child descriptor. Enumerated leaf entries are retained by identity
    alone. ``revalidate`` proves the pinned physical root and every retained
    component still name the same objects, so a bounded operation cannot
    succeed through an ancestor that was renamed, replaced, detached,
    symlinked, or recreated. It is not a claim of atomicity after return.
    """

    __slots__ = ("_contract", "_descriptors", "_components")

    def __init__(self, contract: RepositoryPathContract) -> None:
        self._contract = contract
        self._descriptors: list[int] = [
            _duplicate_descriptor(contract._require_open())
        ]
        self._components: list[
            tuple[int, str, tuple[int, ...], int | None]
        ] = []

    @property
    def leaf(self) -> int:
        return self._descriptors[-1]

    def _retain(
        self,
        parent: int,
        name: str,
        identity: tuple[int, ...],
        descriptor: int | None,
    ) -> None:
        if len(self._components) >= MAX_RETAINED_COMPONENTS:
            _fail("repository path observation exceeds the retained ceiling")
        self._components.append((parent, name, identity, descriptor))

    def open_child(self, parent: int, name: str) -> int:
        """Open one direct child directory and retain its bound identity."""

        entry = _stat_component(name, dir_fd=parent, follow_symlinks=False)
        descriptor = _open_component(
            name,
            self._contract._directory_flags,
            dir_fd=parent,
        )
        try:
            opened = _fstat(descriptor)
            if not stat.S_ISDIR(opened.st_mode):
                _fail("repository owner ancestors must be direct directories")
            if _identity(entry) != _identity(opened):
                _fail("repository path component changed during open")
            self._retain(parent, name, _identity(entry), descriptor)
        except BaseException:
            _close_descriptor(descriptor)
            raise
        self._descriptors.append(descriptor)
        return descriptor

    def descend(self, name: str) -> int:
        return self.open_child(self._descriptors[-1], name)

    def record_entry(
        self, parent: int, name: str, entry: os.stat_result
    ) -> None:
        """Retain one enumerated leaf entry without holding a descriptor."""

        self._retain(parent, name, _identity(entry), None)

    def revalidate(self) -> None:
        """Require the pinned root and every retained component to still bind."""

        self._contract.assert_root_binding()
        for parent, name, identity, descriptor in self._components:
            try:
                entry = _stat_component(
                    name,
                    dir_fd=parent,
                    follow_symlinks=False,
                )
                opened = None if descriptor is None else _fstat(descriptor)
            except OSError as error:
                raise RepositoryPathError(
                    "repository path component changed during evaluation"
                ) from error
            if _identity(entry) != identity or (
                opened is not None and _identity(opened) != identity
            ):
                _fail("repository path component changed during evaluation")

    def close(self) -> None:
        self._components.clear()
        while self._descriptors:
            _close_descriptor(self._descriptors.pop())

    def confirm_absent(self, parent: int, name: str) -> None:
        """Revalidate retained ancestors and observe the same absence again."""

        confirm_component_absent(
            self.revalidate,
            parent,
            name,
            _stat_component,
            RepositoryPathError,
        )


class RepositoryPathContract:
    """Hold one canonical physical root and validate descendant owners."""

    def __init__(
        self,
        root: Path,
        *,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    ) -> None:
        if not isinstance(max_file_bytes, int) or max_file_bytes <= 0:
            _fail("repository file size ceiling must be positive")
        requested = Path(os.path.abspath(root))
        active = _ACTIVE_REPOSITORY.get()
        if active is not None and requested in {
            active.requested_root,
            active.root,
        }:
            self._file_flags = active._file_flags
            self._directory_flags = active._directory_flags
            self.root = active.root
            self.requested_root = active.requested_root
            self._root_descriptor = _duplicate_descriptor(
                active._require_open()
            )
            self._root_parent_descriptor = _duplicate_descriptor(
                active._require_parent_open()
            )
            self._root_name = active._root_name
            self._root_entry_identity = active._root_entry_identity
            self._requested_entry_identity = active._requested_entry_identity
            self.max_file_bytes = max_file_bytes
            self._context_token: Token[RepositoryPathContract | None] | None = (
                None
            )
            return
        try:
            physical = requested.resolve(strict=True)
        except (OSError, RuntimeError) as error:
            raise RepositoryPathError(
                f"repository root is unreadable: {error}"
            ) from error
        if not physical.is_dir():
            _fail("resolved repository root must be a directory")
        pinned = PINNED_ROOT.get()
        if pinned is not None and physical != pinned:
            _fail(
                "nested repository evaluation cannot substitute another "
                "physical repository root"
            )
        self._file_flags, self._directory_flags = _required_flags()
        parent_descriptor: int | None = None
        descriptor: int | None = None
        try:
            parent_descriptor = _open_component(
                physical.parent,
                self._directory_flags,
            )
            descriptor = _open_component(
                physical.name,
                self._directory_flags,
                dir_fd=parent_descriptor,
            )
            root_stat = _fstat(descriptor)
            root_entry = _stat_component(
                physical.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            requested_entry = _stat_component(
                requested,
                follow_symlinks=False,
            )
        except BaseException as error:
            if descriptor is not None:
                _close_descriptor(descriptor)
            if parent_descriptor is not None:
                _close_descriptor(parent_descriptor)
            if isinstance(error, OSError):
                raise RepositoryPathError(
                    f"repository root cannot be opened directly: {error}"
                ) from error
            raise
        assert descriptor is not None
        assert parent_descriptor is not None
        if not stat.S_ISDIR(root_stat.st_mode):
            _close_descriptor(descriptor)
            _close_descriptor(parent_descriptor)
            _fail("resolved repository root must be a direct directory")
        if _identity(root_stat) != _identity(root_entry):
            _close_descriptor(descriptor)
            _close_descriptor(parent_descriptor)
            _fail("repository root changed during direct open")
        self.root = physical
        self.requested_root = requested
        self._root_descriptor: int | None = descriptor
        self._root_parent_descriptor: int | None = parent_descriptor
        self._root_name = physical.name
        self._root_entry_identity = _identity(root_entry)
        self._requested_entry_identity = _identity(requested_entry)
        self.max_file_bytes = max_file_bytes
        self._context_token = None

    def __enter__(self) -> RepositoryPathContract:
        self._require_open()
        if self._context_token is not None:
            _fail("repository path contract cannot be entered twice")
        self._context_token = _ACTIVE_REPOSITORY.set(self)
        return self

    def __exit__(self, *_exc: object) -> None:
        token = self._context_token
        self._context_token = None
        try:
            if token is not None:
                _ACTIVE_REPOSITORY.reset(token)
        finally:
            self.close()

    def close(self) -> None:
        descriptor = self._root_descriptor
        if descriptor is not None:
            self._root_descriptor = None
            _close_descriptor(descriptor)
        parent_descriptor = self._root_parent_descriptor
        if parent_descriptor is not None:
            self._root_parent_descriptor = None
            _close_descriptor(parent_descriptor)

    def _require_open(self) -> int:
        if self._root_descriptor is None:
            _fail("repository path contract is closed")
        return self._root_descriptor

    def _require_parent_open(self) -> int:
        if self._root_parent_descriptor is None:
            _fail("repository path contract is closed")
        return self._root_parent_descriptor

    def duplicate_root_descriptor(self) -> int:
        """Return one read-only descriptor suitable for a bounded child."""

        return _duplicate_descriptor(self._require_open())

    def duplicate_root_parent_descriptor(self) -> int:
        """Return the pinned physical-root parent descriptor for revalidation."""

        return _duplicate_descriptor(self._require_parent_open())

    @property
    def root_name(self) -> str:
        return self._root_name

    @property
    def root_identity(self) -> tuple[int, ...]:
        return self._root_entry_identity

    @property
    def requested_root_identity(self) -> tuple[int, ...]:
        return self._requested_entry_identity

    def assert_root_binding(self) -> None:
        """Require the pinned physical root object and entry to remain bound.

        A caller-facing symlink may be retargeted after resolution without
        changing the physical object this contract owns. Descendant reads and
        worker execution remain bound to the physical parent entry and root
        descriptor; the requested spelling is retained only as input evidence.
        """

        try:
            root_stat = _fstat(self._require_open())
            physical_entry = _stat_component(
                self._root_name,
                dir_fd=self._require_parent_open(),
                follow_symlinks=False,
            )
        except OSError as error:
            raise RepositoryPathError(
                f"repository root binding cannot be revalidated: {error}"
            ) from error
        if (
            _identity(root_stat) != self._root_entry_identity
            or _identity(physical_entry) != self._root_entry_identity
        ):
            _fail("repository root entry changed during evaluation")

    def open_chain(
        self,
        parts: Sequence[str],
        *,
        missing_ok: bool = False,
    ) -> _PathChain | None:
        """Open every ancestor component and retain the complete path chain."""

        chain = _PathChain(self)
        try:
            for part in parts:
                try:
                    chain.descend(part)
                except FileNotFoundError:
                    if missing_ok:
                        chain.confirm_absent(chain.leaf, part)
                        chain.close()
                        return None
                    raise
        except RepositoryPathError:
            chain.close()
            raise
        except OSError as error:
            chain.close()
            raise RepositoryPathError(
                "repository owner ancestors must be direct directories: "
                f"{error}"
            ) from error
        except BaseException:
            chain.close()
            raise
        return chain

    def entry_kind(self, relative: str) -> str | None:
        parts = _components(relative)
        chain = self.open_chain(parts[:-1], missing_ok=True)
        if chain is None:
            return None
        try:
            try:
                value = _stat_component(
                    parts[-1],
                    dir_fd=chain.leaf,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                chain.confirm_absent(chain.leaf, parts[-1])
                return None
            except OSError as error:
                raise RepositoryPathError(
                    f"repository owner cannot be inspected directly: {error}"
                ) from error
            chain.record_entry(chain.leaf, parts[-1], value)
            chain.revalidate()
            if stat.S_ISREG(value.st_mode):
                return "regular"
            if stat.S_ISDIR(value.st_mode):
                return "directory"
            if stat.S_ISLNK(value.st_mode):
                return "symlink"
            return "other"
        finally:
            chain.close()

    def assert_directory(self, relative: str) -> None:
        chain = self.open_chain(_components(relative))
        assert chain is not None
        try:
            chain.revalidate()
        finally:
            chain.close()

    def read_bytes(
        self,
        relative: str,
        *,
        max_bytes: int | None = None,
    ) -> bytes:
        parts = _components(relative)
        ceiling = self.max_file_bytes if max_bytes is None else max_bytes
        if not isinstance(ceiling, int) or ceiling <= 0:
            _fail("repository file size ceiling must be positive")
        chain = self.open_chain(parts[:-1])
        assert chain is not None
        parent = chain.leaf
        descriptor: int | None = None
        try:
            try:
                entry_before = _stat_component(
                    parts[-1],
                    dir_fd=parent,
                    follow_symlinks=False,
                )
                if not stat.S_ISREG(entry_before.st_mode):
                    _fail("repository owner must be a direct regular file")
                descriptor = _open_component(
                    parts[-1],
                    self._file_flags,
                    dir_fd=parent,
                )
            except OSError as error:
                raise RepositoryPathError(
                    "repository owner direct regular file is missing, "
                    f"unreadable, or a symlink: {error}"
                ) from error
            before = _fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                _fail("repository owner must be a direct regular file")
            if _identity(entry_before) != _identity(before):
                _fail("repository owner changed before direct read")
            if before.st_size > ceiling:
                _fail("repository owner exceeds the bounded size ceiling")
            chunks: list[bytes] = []
            read_exact(
                descriptor,
                before.st_size,
                read_chunk=_read_chunk,
                fail=_fail,
                subject="repository owner",
                sink=chunks.append,
            )
            after = _fstat(descriptor)
            if _identity(before) != _identity(after):
                _fail("repository owner metadata changed during read")
            entry_after = _stat_component(
                parts[-1],
                dir_fd=parent,
                follow_symlinks=False,
            )
            if _identity(entry_before) != _identity(entry_after):
                _fail("repository owner entry changed during read")
            chain.record_entry(parent, parts[-1], entry_before)
            chain.revalidate()
            return b"".join(chunks)
        except OSError as error:
            raise RepositoryPathError(
                f"repository owner read failed closed: {error}"
            ) from error
        finally:
            if descriptor is not None:
                _close_descriptor(descriptor)
            chain.close()

    def read_text(
        self,
        relative: str,
        *,
        max_bytes: int | None = None,
    ) -> str:
        try:
            return self.read_bytes(relative, max_bytes=max_bytes).decode("utf-8")
        except UnicodeDecodeError as error:
            raise RepositoryPathError(
                f"repository owner is not valid UTF-8: {error}"
            ) from error

    def directory_entries(self, relative: str) -> tuple[str, ...]:
        chain = self.open_chain(_components(relative))
        assert chain is not None
        try:
            names = tuple(sorted(_list_directory(chain.leaf)))
            chain.revalidate()
            return names
        except OSError as error:
            raise RepositoryPathError(
                f"repository directory cannot be enumerated: {error}"
            ) from error
        finally:
            chain.close()

    def assert_projection(
        self,
        relative: str,
        expected_link_text: str,
        target_relative: str,
    ) -> None:
        from apg_repository_projection_contract import (  # local owner
            assert_projection,
        )

        assert_projection(self, relative, expected_link_text, target_relative)

    def glob_regular_files(self, pattern: str) -> tuple[str, ...]:
        pattern_parts = _components(pattern)
        prefix_length = 0
        for part in pattern_parts:
            if any(token in part for token in ("*", "?", "[")):
                break
            prefix_length += 1
        if prefix_length == 0:
            _fail("repository glob must have a direct parent prefix")
        prefix = pattern_parts[:prefix_length]
        chain = self.open_chain(prefix, missing_ok=True)
        if chain is None:
            return ()
        matches: list[str] = []
        try:
            self._enumerate_regular(
                chain,
                chain.leaf,
                tuple(prefix),
                pattern_parts,
                matches,
            )
            chain.revalidate()
        except RepositoryPathError:
            raise
        except OSError as error:
            raise RepositoryPathError(
                "repository glob changed during evaluation"
            ) from error
        finally:
            chain.close()
        return tuple(sorted(matches))

    def _enumerate_regular(
        self,
        chain: _PathChain,
        descriptor: int,
        relative: tuple[str, ...],
        pattern: tuple[str, ...],
        matches: list[str],
    ) -> None:
        for name in sorted(_list_directory(descriptor)):
            value = _stat_component(
                name,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
            candidate = (*relative, name)
            if stat.S_ISDIR(value.st_mode):
                child = chain.open_child(descriptor, name)
                self._enumerate_regular(
                    chain, child, candidate, pattern, matches
                )
            elif _matches(pattern, candidate):
                if not stat.S_ISREG(value.st_mode):
                    _fail("repository glob match must be a direct regular file")
                chain.record_entry(descriptor, name, value)
                matches.append("/".join(candidate))


_ACTIVE_REPOSITORY: ContextVar[RepositoryPathContract | None] = ContextVar(
    "apg_active_repository_path_contract",
    default=None,
)
PINNED_ROOT: ContextVar[Path | None] = ContextVar(
    "apg_pinned_repository_root",
    default=None,
)
