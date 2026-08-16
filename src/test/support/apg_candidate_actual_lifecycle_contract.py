"""Complete actual absent, authored, retained, and rejected lifecycle gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, NoReturn

from apg_actual_retained_surface_contract import (
    assert_actual_retained_surface_present,
)
from apg_candidate_current_state_contract import assert_current_survivor
from apg_candidate_decision_contract import assert_candidate_decision
from apg_candidate_history_contract import (
    assert_plan_history,
)
from apg_candidate_phase_history_contract import (
    assert_phase_bundles,
    load_phase_history,
)
from apg_candidate_narrative_state_contract import assert_narrative_state
from apg_pinned_root_contract import pinned_repository_root
from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)
from apg_candidate_surface_contract import (
    SurfaceContractError,
    assert_actual_rejected_surface_absent,
    derive_skill_surface_counts,
    validate_candidate_surface_contract,
)
from apg_candidate_traceability_contract import assert_contract_map


def fail(message: str) -> NoReturn:
    raise SurfaceContractError(message)


def _matches(root: Path, owner: dict[str, Any]) -> list[Path]:
    locator = owner.get("path", owner.get("path_pattern"))
    try:
        with RepositoryPathContract(root) as repository:
            if "path_pattern" in owner:
                return [
                    root / relative
                    for relative in repository.glob_regular_files(locator)
                ]
            kind = repository.entry_kind(locator)
    except RepositoryPathError as error:
        fail(f"{owner['owner_id']}: repository path is not direct: {error}")
    return [root / locator] if kind is not None else []


def _regular_text(root: Path, path: Path, owner_id: str) -> str:
    try:
        relative = path.relative_to(root).as_posix()
        with RepositoryPathContract(root) as repository:
            return repository.read_text(relative)
    except (OSError, UnicodeError, ValueError, RepositoryPathError) as error:
        fail(f"{owner_id}: authored owner is unreadable: {error}")


def _assert_authored_owner(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    traceability: dict[str, Any],
) -> None:
    owner_id = owner["owner_id"]
    paths = _matches(root, owner)
    if len(paths) != 1:
        fail(f"{owner_id}: authored owner is missing or duplicated")
    if owner_id == "candidate-contract-map":
        assert_contract_map(root, owner, candidate, traceability)
        return
    text = _regular_text(root, paths[0], owner_id)
    if candidate not in text:
        fail(f"{owner_id}: authored owner does not identify the candidate")
    if owner_id == "canonical-leaf" and f"name: {candidate}" not in text:
        fail(f"{owner_id}: authored leaf frontmatter name is wrong")


def _assert_unintegrated_current(
    root: Path,
    plan: dict[str, Any],
    candidate: str,
) -> None:
    lifecycle = plan["closure_contracts"]["actual_lifecycle"]
    authored = set(lifecycle["authored_owner_ids"])
    excluded = {
        entry["path"] for entry in plan["contract_foundation_exclusions"]
    }
    for owner in plan["owners"]:
        if owner["surface_class"] != "current-integration-surface":
            continue
        owner_id = owner["owner_id"]
        if owner_id in authored:
            _assert_authored_owner(
                root,
                owner,
                candidate,
                plan["closure_contracts"]["traceability"],
            )
        elif "delete" in owner["actions"]:
            residue = [
                path
                for path in _matches(root, owner)
                if path.relative_to(root).as_posix() not in excluded
            ]
            if residue:
                fail(f"{owner_id}: unintegrated authored state has extra owners")
        else:
            assert_current_survivor(
                root,
                owner,
                candidate,
                plan["closure_contracts"][
                    "current_survivor_python_bindings"
                ].get(owner_id),
            )


def _assert_narratives_absent(
    root: Path, plan: dict[str, Any], candidate: str
) -> None:
    for owner in plan["owners"]:
        if owner["surface_class"] == "current-narrative-owner":
            assert_narrative_state(root, owner, candidate, "absent")


def _assert_integrated_count(
    root: Path,
    plan: dict[str, Any],
    candidate: str,
    *,
    authored: bool,
) -> None:
    canonical, catalog, projections = derive_skill_surface_counts(root)
    expected = plan["closure_contracts"]["actual_lifecycle"][
        "integrated_count"
    ]
    if authored:
        candidate_leaf = root / "skills" / candidate / "SKILL.md"
        canonical -= int(candidate_leaf.is_file() and not candidate_leaf.is_symlink())
    if (canonical, catalog, projections) != (expected, expected, expected):
        fail("actual integrated skill counts disagree with lifecycle state")


def _phase_history(
    root: Path, plan: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    lifecycle = plan["closure_contracts"]["actual_lifecycle"]
    history = load_phase_history(
        root / lifecycle["phase_history_manifest"], root
    )
    expected = {
        "authored_history": lifecycle["authoring_history"],
        "foundation_history": lifecycle["foundation_history"],
        "rejected_history": [
            *lifecycle["authoring_history"],
            *lifecycle["terminal_history"],
        ],
        "retained_history": [
            *lifecycle["authoring_history"],
            *lifecycle["terminal_history"],
        ],
    }
    if history["state_requirements"] != expected:
        fail("phase-history manifest and lifecycle plan disagree")
    return history, lifecycle


def _assert_base_history(root: Path, plan: dict[str, Any]) -> None:
    assert_plan_history(root, plan)
    history, lifecycle = _phase_history(root, plan)
    assert_phase_bundles(root, history, lifecycle["foundation_history"])


@pinned_repository_root
def assert_actual_pre_authoring_absent(
    root: Path, manifest: dict[str, Any], plan: dict[str, Any]
) -> None:
    """Require exact current pre-authoring absence and existing foundation history."""
    validate_candidate_surface_contract(manifest, plan)
    assert_actual_rejected_surface_absent(
        root, manifest, plan, decision_lifecycle="unused"
    )
    _assert_base_history(root, plan)
    _assert_integrated_count(
        root, plan, plan["candidate"]["candidate_id"], authored=False
    )


@pinned_repository_root
def assert_actual_authored_proposed_unintegrated(
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    candidate: str,
) -> None:
    """Require the exact APG61 authored-Proposed but unintegrated terminal tree."""
    validate_candidate_surface_contract(manifest, plan)
    if candidate != plan["candidate"]["candidate_id"]:
        fail("candidate does not match the lifecycle contract")
    _assert_unintegrated_current(root, plan, candidate)
    _assert_narratives_absent(root, plan, candidate)
    decision = next(
        owner
        for owner in plan["owners"]
        if owner["surface_class"] == "candidate-decision-lifecycle"
    )
    assert_candidate_decision(
        root,
        decision,
        candidate,
        plan["closure_contracts"]["candidate_decision"],
        "authored-proposed-unintegrated",
    )
    _assert_base_history(root, plan)
    history, lifecycle = _phase_history(root, plan)
    assert_phase_bundles(root, history, lifecycle["authoring_history"])
    _assert_integrated_count(root, plan, candidate, authored=True)


@pinned_repository_root
def assert_actual_retained(
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    candidate: str,
    maturity: str,
) -> None:
    """Require one exact provisional or stable retained state."""
    if maturity not in {"provisional", "stable"}:
        fail("retained maturity is invalid")
    assert_actual_retained_surface_present(
        root,
        manifest,
        plan,
        candidate,
        expected_state=f"retained-{maturity}",
    )
    _assert_base_history(root, plan)
    history, lifecycle = _phase_history(root, plan)
    assert_phase_bundles(
        root,
        history,
        [*lifecycle["authoring_history"], *lifecycle["terminal_history"]],
    )


@pinned_repository_root
def assert_actual_rejected_preserved(
    root: Path, manifest: dict[str, Any], plan: dict[str, Any]
) -> None:
    """Require terminal rejection, strict survivors, and all repository history."""
    validate_candidate_surface_contract(manifest, plan)
    assert_actual_rejected_surface_absent(
        root, manifest, plan, decision_lifecycle="rejected"
    )
    _assert_base_history(root, plan)
    history, lifecycle = _phase_history(root, plan)
    assert_phase_bundles(
        root,
        history,
        [*lifecycle["authoring_history"], *lifecycle["terminal_history"]],
    )
    _assert_integrated_count(
        root, plan, plan["candidate"]["candidate_id"], authored=False
    )


STATE_CHECKERS: dict[str, Callable[..., None]] = {
    "pre-authoring-absent": assert_actual_pre_authoring_absent,
    "authored-proposed-unintegrated": (
        assert_actual_authored_proposed_unintegrated
    ),
    "rejected-preserved": assert_actual_rejected_preserved,
}
