"""Direct regular, no-follow current-survivor ownership."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, NoReturn

from apg_candidate_surface_contract import SurfaceContractError
from apg_python_source_binding_contract import read_bound_strings
from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)


def fail(owner_id: str, message: str) -> NoReturn:
    raise SurfaceContractError(f"{owner_id}: {message}")


def _strict_object(
    pairs: list[tuple[str, Any]], owner_id: str
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(owner_id, f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _parse_json(text: str, owner_id: str) -> None:
    try:
        json.loads(
            text,
            object_pairs_hook=lambda pairs: _strict_object(pairs, owner_id),
        )
    except json.JSONDecodeError as error:
        fail(owner_id, f"JSON current survivor is invalid: {error}")


def assert_current_survivor(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    variable: str | None = None,
) -> None:
    """Require the declared current survivor itself and parse its real type."""
    owner_id = owner["owner_id"]
    relative = owner.get("path")
    if not isinstance(relative, str):
        fail(owner_id, "current survivor requires one exact path")
    path = root / relative
    try:
        with RepositoryPathContract(root) as repository:
            text = repository.read_text(relative)
    except RepositoryPathError as error:
        if "invalid component" in str(error):
            fail(owner_id, "current survivor locator has an unsafe path component")
        fail(owner_id, f"current survivor path is not direct: {error}")
    if path.suffix == ".json":
        _parse_json(text, owner_id)
    elif path.suffix == ".py":
        try:
            ast.parse(text)
        except SyntaxError as error:
            fail(owner_id, f"Python current survivor is invalid: {error}")
        if variable is not None:
            values = read_bound_strings(
                path,
                variable,
                owner_id,
                source_text=text,
            )
            if any(candidate in value for value in values):
                fail(owner_id, f"{variable} retains candidate content")
    if candidate in text:
        fail(owner_id, "current survivor retains candidate content")
