"""Exact bounded descriptor reads shared by repository and snapshot owners."""

from __future__ import annotations

from typing import Callable, NoReturn


READ_CHUNK_BYTES = 64 * 1024

ReadChunk = Callable[[int, int], bytes]
Fail = Callable[[str], NoReturn]
Sink = Callable[[bytes], None]


def discard(_chunk: bytes) -> None:
    """Accept bytes when only the exact-length proof is required."""


def read_exact(
    descriptor: int,
    expected: int,
    *,
    read_chunk: ReadChunk,
    fail: Fail,
    subject: str,
    sink: Sink = discard,
    chunk_bytes: int = READ_CHUNK_BYTES,
) -> int:
    """Copy exactly ``expected`` bytes and require an explicit end of file.

    A short read is completed. A premature end of file, an excess byte beyond
    the declared size, and a negative or unbounded declaration all fail closed.
    The caller remains responsible for opening the descriptor no-follow and for
    revalidating entry and descriptor identity around this read.
    """

    if not isinstance(expected, int) or expected < 0:
        fail(f"{subject} declared an invalid size")
    if not isinstance(chunk_bytes, int) or chunk_bytes <= 0:
        fail(f"{subject} read ceiling must be positive")
    copied = 0
    while copied < expected:
        chunk = read_chunk(descriptor, min(chunk_bytes, expected - copied))
        if not chunk:
            fail(f"{subject} did not provide a complete read")
        copied += len(chunk)
        if copied > expected:
            fail(f"{subject} changed size during read")
        sink(chunk)
    if read_chunk(descriptor, 1):
        fail(f"{subject} changed size during read")
    if copied != expected:
        fail(f"{subject} did not provide a complete read")
    return copied
