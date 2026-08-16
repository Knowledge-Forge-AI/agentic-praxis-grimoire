"""Closed exact phase bundles for candidate lifecycle history."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, Sequence

from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)
from apg_candidate_surface_contract import SurfaceContractError


BUNDLE_KEYS = {
    "decision_adr_path",
    "decision_adr_role",
    "exit_path",
    "git_object_role",
    "managed_report_role",
    "phase_id",
    "private_index_path",
    "private_record_paths",
    "public_evaluation_path",
}
DOCUMENT_KEYS = {
    "artifact",
    "bundles",
    "schema_version",
    "state_requirements",
}
STATE_KEYS = {
    "authored_history",
    "foundation_history",
    "rejected_history",
    "retained_history",
}
DECISION_ROLES = {
    "none",
    "proposed-0035",
    "proposed-0036",
    "terminal-0036",
    "terminal-rejected-0035",
}
MANAGED_REPORT_ROLES = {
    "delivery-creates-associated-report",
    "external-associated-report",
    "future-associated-report",
}
GIT_OBJECT_ROLES = {
    "delivery-creates-commit",
    "external-historical-commit",
    "future-delivery-commit",
}
HISTORICAL_PHASE_IDS = [
    "APG58",
    "APG59",
    "APG60",
    "APG60A",
    "APG60B",
    "APG60C",
    "APG60D",
    "APG60E",
    "APG60F",
    "APG61",
    "APG62",
]
HISTORICAL_STATE_REQUIREMENTS = {
    "authored_history": ["APG61"],
    "foundation_history": [
        "APG58",
        "APG59",
        "APG60",
        "APG60A",
        "APG60B",
        "APG60C",
        "APG60D",
        "APG60E",
        "APG60F",
    ],
    "rejected_history": ["APG61", "APG62"],
    "retained_history": ["APG61", "APG62"],
}
CURRENT_PHASE_IDS = [
    *HISTORICAL_PHASE_IDS[:9],
    "APG60G",
    "APG60H",
    "APG60I",
    "APG61",
    "APG62",
]
CURRENT_STATE_REQUIREMENTS = {
    "authored_history": ["APG61"],
    "foundation_history": [
        *HISTORICAL_PHASE_IDS[:9],
        "APG60G",
        "APG60H",
        "APG60I",
    ],
    "rejected_history": ["APG61", "APG62"],
    "retained_history": ["APG61", "APG62"],
}
APG60H_PHASE_IDS = CURRENT_PHASE_IDS[:-3] + CURRENT_PHASE_IDS[-2:]
APG60H_STATE_REQUIREMENTS = {
    **CURRENT_STATE_REQUIREMENTS,
    "foundation_history": CURRENT_STATE_REQUIREMENTS["foundation_history"][:-1],
}
# Kept as aliases for callers that inspect the historical contract directly.
EXPECTED_PHASE_IDS = HISTORICAL_PHASE_IDS
EXPECTED_STATE_REQUIREMENTS = HISTORICAL_STATE_REQUIREMENTS
DECISION_PATHS = {
    "proposed-0035": (
        "docs/adr/2026/07/"
        "0035-css-language-profile-and-policy-selected-structural-limits.md"
    ),
    "proposed-0036": (
        "docs/adr/2026/07/"
        "0036-css-language-profile-from-frozen-contract.md"
    ),
    "terminal-0036": (
        "docs/adr/2026/07/"
        "0036-css-language-profile-from-frozen-contract.md"
    ),
    "terminal-rejected-0035": (
        "docs/adr/2026/07/"
        "0035-css-language-profile-and-policy-selected-structural-limits.md"
    ),
}


def fail(message: str) -> NoReturn:
    raise SurfaceContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"phase-history manifest has duplicate JSON key: {key}")
        value[key] = item
    return value


def _relative_file(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{context} must be a nonempty relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or any(token in value for token in ("*", "?", "["))
    ):
        fail(f"{context} must be an exact repository-relative path")
    return value


def _string_list(value: Any, context: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
        or value != list(dict.fromkeys(value))
    ):
        fail(f"{context} must be a nonempty duplicate-free string list")
    return value


def _expected_contract(
    value: dict[str, Any],
) -> tuple[list[str], dict[str, list[str]]]:
    identity = (value["artifact"], value["schema_version"])
    if identity == ("apg60f-css-phase-history", 1):
        return HISTORICAL_PHASE_IDS, HISTORICAL_STATE_REQUIREMENTS
    if identity == ("apg60h-css-phase-history", 3):
        return APG60H_PHASE_IDS, APG60H_STATE_REQUIREMENTS
    if identity == ("apg60i-css-phase-history", 4):
        return CURRENT_PHASE_IDS, CURRENT_STATE_REQUIREMENTS
    fail("phase-history manifest identity is invalid")


def _validate_bundle(
    bundle: Any, index: int
) -> tuple[str, list[str]]:
    if not isinstance(bundle, dict) or set(bundle) != BUNDLE_KEYS:
        fail(f"phase-history bundle {index} has unknown or missing keys")
    phase_id = bundle["phase_id"]
    if not isinstance(phase_id, str) or not phase_id.startswith("APG"):
        fail(f"phase-history bundle {index} has an invalid phase ID")
    if bundle["decision_adr_role"] not in DECISION_ROLES:
        fail(f"{phase_id} decision ADR role is invalid")
    decision_path = bundle["decision_adr_path"]
    expected_decision_path = DECISION_PATHS.get(bundle["decision_adr_role"])
    if decision_path != expected_decision_path:
        fail(f"{phase_id} decision ADR path and role do not agree")
    if decision_path is not None:
        _relative_file(decision_path, f"{phase_id} decision ADR")
    if bundle["managed_report_role"] not in MANAGED_REPORT_ROLES:
        fail(f"{phase_id} managed-report role is invalid")
    if bundle["git_object_role"] not in GIT_OBJECT_ROLES:
        fail(f"{phase_id} Git-object role is invalid")
    private_records = _string_list(
        bundle["private_record_paths"], f"{phase_id} private records"
    )
    paths = [
        _relative_file(
            bundle["public_evaluation_path"], f"{phase_id} public evaluation"
        ),
        _relative_file(bundle["exit_path"], f"{phase_id} exit"),
        _relative_file(bundle["private_index_path"], f"{phase_id} private index"),
        *(
            _relative_file(path, f"{phase_id} private record")
            for path in private_records
        ),
    ]
    private_parent = PurePosixPath(bundle["private_index_path"]).parent
    if any(PurePosixPath(path).parent != private_parent for path in private_records):
        fail(f"{phase_id} private records must share the phase directory")
    return phase_id, paths


def validate_phase_history(value: Any) -> dict[str, Any]:
    """Validate immutable APG60F/APG60H history or current APG60I history."""
    if not isinstance(value, dict) or set(value) != DOCUMENT_KEYS:
        fail("phase-history manifest has unknown or missing keys")
    expected_phase_ids, expected_states = _expected_contract(value)
    states = value["state_requirements"]
    if not isinstance(states, dict) or set(states) != STATE_KEYS:
        fail("phase-history state requirements have unknown or missing keys")
    for key in STATE_KEYS:
        _string_list(states[key], f"phase-history {key}")
    if states != expected_states:
        fail("phase-history state requirements are not contract-exact")
    bundles = value["bundles"]
    if not isinstance(bundles, list) or not bundles:
        fail("phase-history bundles must be a nonempty list")
    phase_ids: list[str] = []
    repository_paths: list[str] = []
    for index, bundle in enumerate(bundles):
        phase_id, paths = _validate_bundle(bundle, index)
        phase_ids.append(phase_id)
        repository_paths.extend(paths)
    if len(phase_ids) != len(set(phase_ids)):
        fail("phase-history bundle phase IDs are duplicated")
    if phase_ids != expected_phase_ids:
        fail("phase-history bundle phase IDs are not contract-exact")
    if len(repository_paths) != len(set(repository_paths)):
        fail("phase-history repository paths are duplicated")
    declared = set(phase_ids)
    for key in STATE_KEYS:
        if not set(states[key]) <= declared:
            fail(f"phase-history {key} names an undeclared phase")
    return value


def load_phase_history(
    path: Path, root: Path | None = None
) -> dict[str, Any]:
    """Load strict UTF-8 JSON without following a substituted manifest."""
    if root is None:
        fail("phase-history manifest requires a physical repository root")
    try:
        relative = path.relative_to(root).as_posix()
        with RepositoryPathContract(root) as repository:
            text = repository.read_text(relative)
        value = json.loads(text, object_pairs_hook=_strict_object)
    except (
        OSError,
        UnicodeError,
        ValueError,
        RepositoryPathError,
        json.JSONDecodeError,
    ) as error:
        fail(f"phase-history manifest is invalid or unreadable: {error}")
    expected = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if text != expected:
        fail("phase-history manifest is not canonical JSON")
    return validate_phase_history(value)


def _direct_regular_text(
    root: Path, relative: str, phase_id: str
) -> None:
    try:
        with RepositoryPathContract(root) as repository:
            text = repository.read_text(relative)
    except (OSError, UnicodeError, RepositoryPathError) as error:
        fail(f"{phase_id}: repository history is not valid UTF-8: {error}")
    if not text.strip():
        fail(f"{phase_id}: repository history is an empty placeholder")


def _assert_bundle(root: Path, bundle: dict[str, Any]) -> None:
    phase_id = bundle["phase_id"]
    required = [
        bundle["public_evaluation_path"],
        bundle["exit_path"],
        bundle["private_index_path"],
        *bundle["private_record_paths"],
    ]
    if bundle["decision_adr_path"] is not None:
        required.append(bundle["decision_adr_path"])
    for relative in required:
        _direct_regular_text(root, relative, phase_id)
    private_index = root / bundle["private_index_path"]
    private_root = private_index.parent
    private_relative = private_root.relative_to(root).as_posix()
    try:
        with RepositoryPathContract(root) as repository:
            actual = set(
                repository.glob_regular_files(f"{private_relative}/**/*")
            )
    except RepositoryPathError as error:
        fail(f"{phase_id}: publication-excluded bundle is not direct: {error}")
    expected = {
        bundle["private_index_path"],
        *bundle["private_record_paths"],
    }
    if actual != expected:
        fail(f"{phase_id}: publication-excluded phase bundle is not exact")


def assert_phase_bundles(
    root: Path,
    history: dict[str, Any],
    phase_ids: Sequence[str],
) -> None:
    """Require every selected phase's exact direct-regular repository bundle."""
    if len(phase_ids) != len(set(phase_ids)):
        fail("requested phase-history IDs are duplicated")
    by_id = {bundle["phase_id"]: bundle for bundle in history["bundles"]}
    for phase_id in phase_ids:
        bundle = by_id.get(phase_id)
        if bundle is None:
            fail(f"phase-history bundle is undeclared: {phase_id}")
        _assert_bundle(root, bundle)
