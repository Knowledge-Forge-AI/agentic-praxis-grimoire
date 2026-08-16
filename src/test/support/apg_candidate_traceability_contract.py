"""Closed future candidate traceability-map validation."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any, NoReturn

from apg_candidate_surface_contract import SurfaceContractError
from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)


TOP_LEVEL_KEYS = {
    "candidate_id",
    "cases",
    "contract_revision",
    "contract_sha256",
    "schema_version",
    "semantic_boundary",
}
ROW_KEYS = {
    "case_id",
    "clause_ids",
    "forbidden_actions",
    "required_actions",
    "rollback_required",
    "selected_owner",
}
CLAUSE_ID = re.compile(r"CSS-[A-Z0-9]+(?:-[A-Z0-9]+)*")
MARKER = re.compile(
    r"(?m)^<!-- APG-CLAUSE: (CSS-[A-Z0-9]+(?:-[A-Z0-9]+)*) -->$"
)
SEMANTIC_BOUNDARY = (
    "navigation-only; clause prose requires APG62 semantic validation"
)
PRIVATE_MARKERS = (
    "/" "Users/",
    r"C:\Users\\",
    "private/",
    "GIT-SHOW-REPORT-",
    "OPERATIONAL-REPORT-",
    "password",
    "credential",
    "api_key",
    "token=",
)


def fail(owner_id: str, message: str) -> NoReturn:
    raise SurfaceContractError(f"{owner_id}: {message}")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _read_json(
    root: Path, path: Path, owner_id: str
) -> tuple[dict[str, Any], bytes]:
    try:
        relative = path.relative_to(root).as_posix()
        with RepositoryPathContract(root) as repository:
            data = repository.read_bytes(relative)
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (
        OSError,
        UnicodeError,
        RepositoryPathError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        fail(owner_id, f"JSON is unreadable: {error}")
    if not isinstance(value, dict):
        fail(owner_id, "JSON must be an object")
    return value, data


def _string_list(value: Any, owner_id: str, field: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) for item in value)
        or len(value) != len(set(value))
    ):
        fail(owner_id, f"{field} must be a unique string array")
    return value


def _contract_cases(
    root: Path, config: dict[str, Any], owner_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    contract_path = root / config["contract_path"]
    contract, data = _read_json(root, contract_path, owner_id)
    digest = hashlib.sha256(data).hexdigest()
    if digest != config["contract_sha256"]:
        fail(owner_id, "frozen contract digest disagrees with closure metadata")
    if contract.get("contract_revision") != config["contract_revision"]:
        fail(owner_id, "frozen contract revision disagrees with closure metadata")
    cases = contract.get("cases")
    if not isinstance(cases, list) or len(cases) != 60:
        fail(owner_id, "frozen contract must contain sixty cases")
    if any(not isinstance(case, dict) for case in cases):
        fail(owner_id, "frozen contract case is not an object")
    return contract, cases, digest


def _expected_row(case: dict[str, Any], clause_ids: list[str]) -> dict[str, Any]:
    expected = case["expected"]
    return {
        "case_id": case["id"],
        "clause_ids": clause_ids,
        "forbidden_actions": sorted(expected["forbidden_actions"]),
        "required_actions": sorted(expected["required_actions"]),
        "rollback_required": expected["rollback"],
        "selected_owner": expected["selected_owner"],
    }


def _validate_row_shape(
    row: Any, case: dict[str, Any], owner_id: str
) -> list[str]:
    if not isinstance(row, dict) or set(row) != ROW_KEYS:
        fail(owner_id, "traceability row schema is invalid")
    clause_ids = _string_list(row["clause_ids"], owner_id, "clause_ids")
    if not clause_ids or any(CLAUSE_ID.fullmatch(item) is None for item in clause_ids):
        fail(owner_id, "clause IDs are empty or malformed")
    expected = _expected_row(case, clause_ids)
    if row != expected:
        fail(owner_id, f"{case['id']} traceability row disagrees with contract")
    return clause_ids


def _clause_markers(
    root: Path,
    config: dict[str, Any],
    candidate: str,
    owner_id: str,
) -> Counter[str]:
    markers: Counter[str] = Counter()
    for template in config["clause_owner_paths"]:
        path = root / template.replace("{candidate_id}", candidate)
        try:
            relative = path.relative_to(root).as_posix()
            with RepositoryPathContract(root) as repository:
                text = repository.read_text(relative)
        except (
            OSError,
            UnicodeError,
            ValueError,
            RepositoryPathError,
        ) as error:
            fail(owner_id, f"candidate clause owner is unreadable: {error}")
        markers.update(MARKER.findall(text))
    return markers


def _assert_privacy(value: dict[str, Any], owner_id: str) -> None:
    serialized = json.dumps(value, sort_keys=True)
    if any(marker.lower() in serialized.lower() for marker in PRIVATE_MARKERS):
        fail(owner_id, "traceability map contains private or operational data")


def assert_contract_map(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    config: dict[str, Any],
) -> None:
    """Require exact frozen-contract rows and reachable clause anchors."""
    owner_id = owner["owner_id"]
    path = root / owner["path"]
    value, _data = _read_json(root, path, owner_id)
    if set(value) != TOP_LEVEL_KEYS:
        fail(owner_id, "traceability map top-level schema is invalid")
    _contract, cases, digest = _contract_cases(root, config, owner_id)
    expected_header = {
        "candidate_id": candidate,
        "contract_revision": config["contract_revision"],
        "contract_sha256": digest,
        "schema_version": config["schema_version"],
        "semantic_boundary": SEMANTIC_BOUNDARY,
    }
    if any(value.get(key) != expected for key, expected in expected_header.items()):
        fail(owner_id, "traceability map identity is invalid")
    rows = value["cases"]
    if not isinstance(rows, list) or len(rows) != len(cases):
        fail(owner_id, "traceability map must contain sixty exact rows")
    referenced: Counter[str] = Counter()
    for row, case in zip(rows, cases, strict=True):
        referenced.update(_validate_row_shape(row, case, owner_id))
    markers = _clause_markers(root, config, candidate, owner_id)
    if any(count != 1 for count in markers.values()):
        fail(owner_id, "candidate clause marker is duplicated or ambiguous")
    if set(referenced) != set(markers):
        fail(owner_id, "candidate clauses are missing, unknown, or unreferenced")
    _assert_privacy(value, owner_id)
