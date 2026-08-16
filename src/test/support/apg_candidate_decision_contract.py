"""Fresh candidate ADR lifecycle closure."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, NoReturn

from apg_candidate_surface_contract import SurfaceContractError
from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)


RETAINED_STATUSES = {"Accepted", "Accepted with amendment"}
STATES = {
    "authored-proposed-unintegrated",
    "unused",
    "retained",
    "rejected",
}
STATUS = re.compile(r"(?m)^- Status: (.+)$")


def fail(owner_id: str, message: str) -> NoReturn:
    raise SurfaceContractError(f"{owner_id}: {message}")


def _status(text: str, owner_id: str) -> str:
    matches = STATUS.findall(text)
    if len(matches) != 1:
        fail(owner_id, "candidate decision ADR status is missing or duplicated")
    return matches[0]


def _expected_statuses(lifecycle: str) -> set[str]:
    if lifecycle == "authored-proposed-unintegrated":
        return {"Proposed"}
    if lifecycle == "retained":
        return RETAINED_STATUSES
    return {"Rejected"}


def _assert_provenance(
    text: str,
    owner_id: str,
    candidate: str,
    lifecycle: str,
) -> None:
    required = [candidate, "- Proposed in: APG61"]
    if lifecycle != "authored-proposed-unintegrated":
        required.append("- Decided in: APG62")
    if any(item not in text for item in required):
        fail(
            owner_id,
            "candidate decision ADR identity or phase provenance is incomplete",
        )
    if (
        lifecycle == "authored-proposed-unintegrated"
        and "- Decided in:" in text
    ):
        fail(owner_id, "Proposed candidate decision claims a later decision")


def _assert_index_entry(
    lines: list[str],
    matching_lines: list[int],
    relative: str,
    status: str,
    owner_id: str,
) -> None:
    if len(matching_lines) != 1:
        fail(owner_id, "ADR index entry is missing or duplicated")
    position = matching_lines[0]
    if (
        not lines[position].endswith(f"]({relative})")
        or position + 1 >= len(lines)
        or lines[position + 1] != f"  — {status}"
    ):
        fail(owner_id, "ADR index does not agree with candidate decision")


def assert_candidate_decision(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    config: dict[str, Any],
    lifecycle: str,
) -> None:
    """Require unused, terminal retained, or preserved rejected ADR state."""
    owner_id = owner["owner_id"]
    if lifecycle not in STATES:
        fail(owner_id, "candidate decision lifecycle is unknown")
    relative_path = owner["path"]
    try:
        with RepositoryPathContract(root) as repository:
            index = repository.read_text(config["index_path"])
            decision_kind = repository.entry_kind(relative_path)
            text = (
                repository.read_text(relative_path)
                if decision_kind is not None
                else None
            )
    except RepositoryPathError as error:
        fail(owner_id, f"candidate decision path is not direct: {error}")
    relative = owner["path"].removeprefix("docs/adr/")
    lines = index.splitlines()
    matching_lines = [
        position
        for position, line in enumerate(lines)
        if f"]({relative})" in line
    ]
    if lifecycle == "unused":
        if decision_kind is not None or matching_lines:
            fail(owner_id, "unused candidate decision ADR is unexpectedly present")
        return
    if text is None:
        fail(owner_id, "candidate decision ADR must be a regular file")
    status = _status(text, owner_id)
    if status not in _expected_statuses(lifecycle):
        fail(owner_id, "candidate decision ADR is not terminal for lifecycle")
    _assert_provenance(text, owner_id, candidate, lifecycle)
    _assert_index_entry(
        lines,
        matching_lines,
        relative,
        status,
        owner_id,
    )
