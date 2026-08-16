"""Descriptor ownership for one isolated repository worker launch."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Any, Iterator


@contextmanager
def repository_worker_descriptors(repository: Any) -> Iterator[tuple[int, int]]:
    """Yield duplicated root descriptors and close every acquired handle."""

    root_descriptor: int | None = None
    root_parent_descriptor: int | None = None
    try:
        root_descriptor = repository.duplicate_root_descriptor()
        root_parent_descriptor = repository.duplicate_root_parent_descriptor()
        yield root_descriptor, root_parent_descriptor
    finally:
        if root_descriptor is not None:
            os.close(root_descriptor)
        if root_parent_descriptor is not None:
            os.close(root_parent_descriptor)
