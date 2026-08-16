"""Exact markers plus bounded diagnostics; arbitrary prose needs human review."""

from __future__ import annotations

from pathlib import Path
import re
from typing import NoReturn

from apg_candidate_surface_contract import SurfaceContractError
from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)


STATES = {"absent", "retained-provisional", "retained-stable"}
MARKER = re.compile(
    r"<!-- APG-CANDIDATE-STATE: "
    r"([a-z0-9]+(?:-[a-z0-9]+)*) "
    r"([a-z]+(?:-[a-z]+)*) -->"
)
MARKER_PREFIX = "<!-- APG-CANDIDATE-STATE:"
RETAINED_TERMINAL = r"(?:active|integrated|current|present|retained)"
RETAINED_INCOMPATIBLE = (
    r"(?:(?:currently|still|now)\s+)?(?:"
    r"inactive|rejected|absent|removed|deferred|unintegrated|"
    r"not\s+(?:(?:currently|yet|still|now)\s+)?"
    + RETAINED_TERMINAL
    + r"|no\s+longer\s+"
    + RETAINED_TERMINAL
    + r")"
)
MECHANICAL_AUTHORITY = "exact candidate-state marker"
DIAGNOSTIC_SCOPE = "frozen bounded contradiction vocabulary"
HUMAN_REVIEW_BOUNDARY = "human review remains required for arbitrary prose"
HISTORICAL_HEADING = re.compile(
    r"^#{1,6}\s+.*\b(?:historical|history|prior|past)\b",
    re.IGNORECASE,
)


def fail(owner_id: str, message: str) -> NoReturn:
    raise SurfaceContractError(f"{owner_id}: {message}")


def marker(candidate: str, state: str) -> str:
    if state not in STATES:
        raise ValueError(f"unknown candidate state: {state}")
    return f"<!-- APG-CANDIDATE-STATE: {candidate} {state} -->"


def _paragraphs(text: str) -> list[str]:
    without_markers = MARKER.sub("", text)
    current: list[str] = []
    historical_section = False
    for paragraph in re.split(r"\n[ \t]*\n", without_markers):
        stripped = paragraph.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            historical_section = HISTORICAL_HEADING.match(stripped) is not None
        if not historical_section:
            current.append(paragraph)
    return current


def _has_retained_contradiction(paragraph: str, candidate: str) -> bool:
    lowered = " ".join(paragraph.lower().split())
    if candidate not in lowered:
        return False
    candidate_terminal = re.compile(
        rf"\b{re.escape(candidate)}\b.{{0,80}}\b"
        r"(?:is|remains|status(?:\s+is)?|state(?:\s+is)?)\s+"
        + RETAINED_INCOMPATIBLE
        + r"\b"
    )
    paragraph_terminal = re.compile(
        r"\b(?:status|current\s+state)\s*:\s*"
        + RETAINED_INCOMPATIBLE
        + r"\b"
    )
    frozen_direct = re.compile(
        rf"\b{re.escape(candidate)}\b.{{0,80}}(?:"
        r"\bis\s+(?:a\s+)?"
        r"(?:rejected|absent|removed|deferred)(?:\s+candidate)?\b"
        r"|\b(?:has\s+been|was)\s+(?:rejected|removed)\b"
        r"|\bis\s+not\s+being\s+(?:integrated|retained)\b"
        r"|\bis\s+no\s+longer\s+(?:an?\s+)?"
        r"(?:integrated|current|retained)\s+(?:skill|candidate)\b"
        r"|\s(?:—|–|-|:)\s*(?:rejected|absent|removed|deferred)\b"
        r"|\bremains\s+(?:under\s+rejection|marked\s+rejected)\b"
        r")"
    )
    return (
        candidate_terminal.search(lowered) is not None
        or paragraph_terminal.search(lowered) is not None
        or frozen_direct.search(lowered) is not None
    )


def _has_absent_contradiction(paragraph: str, candidate: str) -> bool:
    lowered = " ".join(paragraph.lower().split())
    if candidate not in lowered:
        return False
    active_claim = re.compile(
        rf"\b{re.escape(candidate)}\b.{{0,80}}\b"
        r"(?:is|remains|status(?:\s+is)?|state(?:\s+is)?)\s+"
        r"(?:(?:currently|still|now)\s+)?"
        r"(?:active|current|integrated|present|retained)\b"
    )
    return active_claim.search(lowered) is not None


def assert_narrative_state(
    root: Path,
    owner: dict[str, object],
    candidate: str,
    expected_state: str,
) -> None:
    """Prove marker state and diagnose only the frozen bounded vocabulary."""
    owner_id = str(owner["owner_id"])
    if expected_state not in STATES:
        fail(owner_id, "expected narrative state is unknown")
    path = root / str(owner["path"])
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
        fail(owner_id, f"current narrative owner is unreadable: {error}")
    candidate_markers = [
        state
        for marked_candidate, state in MARKER.findall(text)
        if marked_candidate == candidate
    ]
    prefix_count = sum(
        1
        for line in text.splitlines()
        if MARKER_PREFIX in line and candidate in line
    )
    if (
        prefix_count != 1
        or candidate_markers != [expected_state]
        or any(state not in STATES for state in candidate_markers)
    ):
        fail(
            owner_id,
            f"{path}: candidate-state marker is missing, duplicate, or invalid",
        )
    contradiction = (
        _has_absent_contradiction
        if expected_state == "absent"
        else _has_retained_contradiction
    )
    if any(contradiction(paragraph, candidate) for paragraph in _paragraphs(text)):
        fail(
            owner_id,
            f"{path}: current narrative contradicts candidate-state marker",
        )
