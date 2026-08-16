"""Pinned physical-root binding for one bounded repository evaluation.

A decorated evaluation opens one repository path contract, proves the physical
root binding before the evaluation runs, and proves it again before returning.
Success is therefore bounded to the final revalidation rather than to the first
one, and no caller has to remember to add its own closing check.
"""

from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Callable, Concatenate, ParamSpec, TypeVar

from apg_repository_path_contract import PINNED_ROOT, RepositoryPathContract


_Parameters = ParamSpec("_Parameters")
_Result = TypeVar("_Result")


def pinned_repository_root(
    function: Callable[Concatenate[Path, _Parameters], _Result],
) -> Callable[Concatenate[Path, _Parameters], _Result]:
    """Retain and revalidate one physical root across one bounded evaluation.

    While the evaluation runs, nested repository owners may reuse the same
    physical root but may not substitute another one. An exception raised by
    the decorated function stays primary and is never masked by the closing
    root check.
    """

    @wraps(function)
    def pinned(
        root: Path,
        *args: _Parameters.args,
        **kwargs: _Parameters.kwargs,
    ) -> _Result:
        with RepositoryPathContract(root) as repository:
            token = PINNED_ROOT.set(repository.root)
            try:
                repository.assert_root_binding()
                result = function(repository.root, *args, **kwargs)
                repository.assert_root_binding()
            finally:
                PINNED_ROOT.reset(token)
            return result

    return pinned
