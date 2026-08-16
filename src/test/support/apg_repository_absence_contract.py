"""Second observation for one descriptor-relative absent component."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def confirm_component_absent(
    revalidate: Callable[[], None],
    parent: int,
    name: str,
    stat_component: Callable[..., Any],
    error_type: type[ValueError],
) -> None:
    """Require retained ancestors and the exact missing component to agree."""

    revalidate()
    try:
        stat_component(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return
    except OSError as error:
        raise error_type(
            "repository path component changed during evaluation"
        ) from error
    raise error_type("repository path component changed during evaluation")
