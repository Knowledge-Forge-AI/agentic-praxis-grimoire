"""Exact bounded descriptor-read controls shared by repository and snapshot."""

from __future__ import annotations

import sys
from typing import NoReturn

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_exact_read_contract import read_exact  # noqa: E402


class ReadError(ValueError):
    """Owner-specific failure raised by the injected fail hook."""


def _fail(message: str) -> NoReturn:
    raise ReadError(message)


def _scripted(*responses: bytes):
    """Return a read hook that replays exactly the scripted responses."""

    remaining = list(responses)

    def read_chunk(_descriptor: int, size: int) -> bytes:
        assert size > 0
        if not remaining:
            return b""
        return remaining.pop(0)

    return read_chunk


def _sized(payload: bytes, chunk: int):
    """Return a read hook that honours the requested size over ``payload``."""

    offset = 0

    def read_chunk(_descriptor: int, size: int) -> bytes:
        nonlocal offset
        window = payload[offset : offset + min(size, chunk)]
        offset += len(window)
        return window

    return read_chunk


def test_short_first_read_is_completed() -> None:
    collected: list[bytes] = []
    copied = read_exact(
        0,
        10,
        read_chunk=_scripted(b"012", b"3456789", b""),
        fail=_fail,
        subject="owner",
        sink=collected.append,
    )
    assert copied == 10
    assert b"".join(collected) == b"0123456789"


def test_many_small_reads_are_completed() -> None:
    collected: list[bytes] = []
    copied = read_exact(
        0,
        10,
        read_chunk=_sized(b"0123456789", 1),
        fail=_fail,
        subject="owner",
        sink=collected.append,
    )
    assert copied == 10
    assert len(collected) == 10
    assert b"".join(collected) == b"0123456789"


def test_premature_end_of_file_after_partial_read_fails() -> None:
    with pytest.raises(ReadError, match="complete read"):
        read_exact(
            0,
            10,
            read_chunk=_scripted(b"012", b""),
            fail=_fail,
            subject="owner",
        )


def test_immediate_end_of_file_for_a_nonempty_owner_fails() -> None:
    with pytest.raises(ReadError, match="complete read"):
        read_exact(
            0,
            10,
            read_chunk=_scripted(b""),
            fail=_fail,
            subject="owner",
        )


def test_excess_byte_beyond_the_declared_size_fails() -> None:
    with pytest.raises(ReadError, match="changed size"):
        read_exact(
            0,
            4,
            read_chunk=_scripted(b"0123", b"4"),
            fail=_fail,
            subject="owner",
        )


def test_chunk_longer_than_the_remaining_declaration_fails() -> None:
    with pytest.raises(ReadError, match="changed size"):
        read_exact(
            0,
            4,
            read_chunk=_scripted(b"012345"),
            fail=_fail,
            subject="owner",
        )


def test_exact_empty_owner_requires_only_an_explicit_end_of_file() -> None:
    calls: list[int] = []

    def read_chunk(_descriptor: int, size: int) -> bytes:
        calls.append(size)
        return b""

    assert (
        read_exact(0, 0, read_chunk=read_chunk, fail=_fail, subject="owner")
        == 0
    )
    assert calls == [1]


def test_exact_nonempty_owner_probes_end_of_file_once() -> None:
    calls: list[int] = []

    def read_chunk(_descriptor: int, size: int) -> bytes:
        calls.append(size)
        return b"0123" if len(calls) == 1 else b""

    assert (
        read_exact(0, 4, read_chunk=read_chunk, fail=_fail, subject="owner")
        == 4
    )
    assert calls == [4, 1]


def test_read_window_never_exceeds_the_chunk_ceiling() -> None:
    requested: list[int] = []
    delivered = 0

    def read_chunk(_descriptor: int, size: int) -> bytes:
        nonlocal delivered
        requested.append(size)
        window = min(size, 9 - delivered)
        delivered += window
        return b"x" * window

    read_exact(
        0,
        9,
        read_chunk=read_chunk,
        fail=_fail,
        subject="owner",
        chunk_bytes=3,
    )
    assert requested == [3, 3, 3, 1]


@pytest.mark.parametrize("expected", (-1, "4", None))
def test_invalid_declared_size_fails_closed(expected: object) -> None:
    with pytest.raises(ReadError, match="invalid size"):
        read_exact(
            0,
            expected,  # type: ignore[arg-type]
            read_chunk=_scripted(b""),
            fail=_fail,
            subject="owner",
        )


@pytest.mark.parametrize("chunk_bytes", (0, -1, "64"))
def test_invalid_chunk_ceiling_fails_closed(chunk_bytes: object) -> None:
    with pytest.raises(ReadError, match="read ceiling"):
        read_exact(
            0,
            4,
            read_chunk=_scripted(b"0123", b""),
            fail=_fail,
            subject="owner",
            chunk_bytes=chunk_bytes,  # type: ignore[arg-type]
        )
