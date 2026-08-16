"""Descriptor-bound temporary storage orchestration for isolated APG workers."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from apg_worker_temp_cleanup_contract import descriptor_child
from apg_worker_temp_root_binding_contract import (
    WorkerTempCleanupError,
    WorkerTempError,
    selected_worker_temp_root,
)


@dataclass(frozen=True)
class WorkerTempContext:
    """One operation child and the exact descriptor inherited by its worker."""

    environment: dict[str, str]
    descriptor: int


@contextmanager
def worker_temp_environment(repository_root: Path) -> Iterator[WorkerTempContext]:
    """Yield one descriptor-bound parent-owned worker operation child."""

    selected = selected_worker_temp_root(repository_root)
    failure: BaseException | None = None
    try:
        try:
            with descriptor_child(selected.descriptor, prefix="apg-worker-") as child:
                selected.revalidate()
                assert child.name is not None
                assert child.descriptor is not None
                text = str(selected.path / child.name)
                yield WorkerTempContext(
                    environment={"TMPDIR": text, "TMP": text, "TEMP": text},
                    descriptor=child.descriptor,
                )
        except BaseException as error:
            failure = error
            raise
    finally:
        try:
            selected.revalidate()
        except BaseException as root_error:
            if failure is None:
                raise WorkerTempError(
                    "worker temporary root changed during operation"
                ) from root_error
            setattr(
                failure,
                "worker_temp_root_failure",
                "worker temporary root changed during operation",
            )
        finally:
            selected.close()
