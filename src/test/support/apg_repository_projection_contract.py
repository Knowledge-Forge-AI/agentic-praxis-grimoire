"""Stable no-follow projection identity and canonical-target validation.

The projection leaf is a symbolic link. Ordinary ``lstat`` metadata cannot
distinguish an unchanged link from an unlink-and-recreate whose replacement
reuses the same inode number and timestamps, so this owner retains a platform
handle to the link object itself. When no such handle exists the strong
projection mode fails closed rather than claiming an identity it cannot prove.
"""

from __future__ import annotations

import os
import stat
from typing import Sequence

import apg_repository_path_contract as owner
from apg_exact_read_contract import read_exact


if hasattr(os, "O_PATH"):
    SYMLINK_HANDLE_MECHANISM = "o-path-nofollow"
    SYMLINK_HANDLE_FLAGS: int | None = (
        os.O_PATH | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    )
elif hasattr(os, "O_SYMLINK"):
    SYMLINK_HANDLE_MECHANISM = "o-symlink"
    SYMLINK_HANDLE_FLAGS = os.O_SYMLINK | getattr(os, "O_CLOEXEC", 0)
else:
    SYMLINK_HANDLE_MECHANISM = "unsupported"
    SYMLINK_HANDLE_FLAGS = None


def _open_link_handle(parent: int, name: str) -> tuple[int, tuple[int, ...]]:
    """Open the projection link itself and retain its stable identity."""

    flags = SYMLINK_HANDLE_FLAGS
    if flags is None:
        owner._fail(
            "stable projection identity is unsupported on this platform"
        )
    handle = owner._open_component(name, flags, dir_fd=parent)
    try:
        value = owner._fstat(handle)
        if not stat.S_ISLNK(value.st_mode):
            owner._fail("projection leaf must be one direct symlink")
        if value.st_nlink < 1:
            owner._fail("projection leaf was already detached")
    except BaseException:
        owner._close_descriptor(handle)
        raise
    return handle, owner._identity(value)


def _open_target(
    contract: owner.RepositoryPathContract,
    parts: Sequence[str],
) -> tuple[owner._PathChain, int, tuple[int, ...]]:
    """Open, exactly read, and bind the canonical projection target."""

    chain = contract.open_chain(parts[:-1])
    assert chain is not None
    parent = chain.leaf
    descriptor: int | None = None
    try:
        entry_before = owner._stat_component(
            parts[-1],
            dir_fd=parent,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(entry_before.st_mode):
            owner._fail("projection target must be a direct regular file")
        descriptor = owner._open_component(
            parts[-1],
            contract._file_flags,
            dir_fd=parent,
        )
        opened_before = owner._fstat(descriptor)
        if owner._identity(entry_before) != owner._identity(opened_before):
            owner._fail("projection target changed before direct read")
        if opened_before.st_size > contract.max_file_bytes:
            owner._fail("projection target exceeds the bounded size ceiling")
        read_exact(
            descriptor,
            opened_before.st_size,
            read_chunk=owner._read_chunk,
            fail=owner._fail,
            subject="projection target",
        )
        opened_after = owner._fstat(descriptor)
        if owner._identity(opened_before) != owner._identity(opened_after):
            owner._fail("projection target changed during direct read")
        entry_after = owner._stat_component(
            parts[-1],
            dir_fd=parent,
            follow_symlinks=False,
        )
        if owner._identity(entry_before) != owner._identity(entry_after):
            owner._fail("projection target entry changed during validation")
        chain.record_entry(parent, parts[-1], entry_before)
        return chain, descriptor, owner._identity(entry_before)
    except owner.RepositoryPathError:
        _release(chain, descriptor)
        raise
    except OSError as error:
        _release(chain, descriptor)
        raise owner.RepositoryPathError(
            f"projection target cannot be inspected directly: {error}"
        ) from error
    except BaseException:
        _release(chain, descriptor)
        raise


def _release(chain: owner._PathChain | None, *descriptors: int | None) -> None:
    for descriptor in descriptors:
        if descriptor is not None:
            owner._close_descriptor(descriptor)
    if chain is not None:
        chain.close()


def assert_projection(
    contract: owner.RepositoryPathContract,
    relative: str,
    expected_link_text: str,
    target_relative: str,
) -> None:
    """Require one exact relative projection bound to its canonical owner."""

    parts = owner._components(relative)
    target_parts = owner._components(target_relative)
    resolved_target = owner._resolve_link_parts(
        parts[:-1], expected_link_text
    )
    if tuple(target_parts[:-1]) != resolved_target:
        owner._fail("projection target and canonical owner do not agree")
    chain = contract.open_chain(parts[:-1])
    assert chain is not None
    parent = chain.leaf
    handle: int | None = None
    target_chain: owner._PathChain | None = None
    target_descriptor: int | None = None
    try:
        before = owner._stat_component(
            parts[-1],
            dir_fd=parent,
            follow_symlinks=False,
        )
        if not stat.S_ISLNK(before.st_mode):
            owner._fail("projection leaf must be one direct symlink")
        handle, handle_identity = _open_link_handle(parent, parts[-1])
        link_text = owner._read_link(parts[-1], dir_fd=parent)
        after = owner._stat_component(
            parts[-1],
            dir_fd=parent,
            follow_symlinks=False,
        )
        if owner._identity(before) != owner._identity(after):
            owner._fail("projection changed during readlink")
        if link_text != expected_link_text:
            owner._fail(
                "projection target is not the exact expected relative link"
            )
        target_chain, target_descriptor, target_identity = _open_target(
            contract, target_parts
        )
        final_before = owner._stat_component(
            parts[-1],
            dir_fd=parent,
            follow_symlinks=False,
        )
        final_link_text = owner._read_link(parts[-1], dir_fd=parent)
        final_after = owner._stat_component(
            parts[-1],
            dir_fd=parent,
            follow_symlinks=False,
        )
        if owner._identity(final_before) != owner._identity(final_after):
            owner._fail("projection changed during final readlink")
        if (
            owner._identity(before) != owner._identity(final_after)
            or final_link_text != link_text
        ):
            owner._fail("projection changed during target validation")
        if owner._identity(owner._fstat(handle)) != handle_identity:
            owner._fail("projection leaf identity changed during validation")
        target_opened_final = owner._fstat(target_descriptor)
        target_entry_final = owner._stat_component(
            target_parts[-1],
            dir_fd=target_chain.leaf,
            follow_symlinks=False,
        )
        if (
            target_identity != owner._identity(target_opened_final)
            or target_identity != owner._identity(target_entry_final)
        ):
            owner._fail("projection target changed during final validation")
        chain.record_entry(parent, parts[-1], final_after)
        chain.revalidate()
        target_chain.revalidate()
    except owner.RepositoryPathError:
        raise
    except OSError as error:
        raise owner.RepositoryPathError(
            f"projection cannot be inspected directly: {error}"
        ) from error
    finally:
        _release(target_chain, target_descriptor, handle)
        chain.close()
