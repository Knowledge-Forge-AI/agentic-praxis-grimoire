"""Failing-first actual rejected-history closure for APG60C."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_actual_lifecycle_contract import (  # noqa: E402
    assert_actual_rejected_preserved,
)
from apg_candidate_lifecycle_fixture import (  # noqa: E402
    materialize_actual_rejected_preserved,
)
from apg_candidate_history_contract import assert_plan_history  # noqa: E402
from apg_candidate_surface_contract import (  # noqa: E402
    SurfaceContractError,
    load_candidate_surface_manifest,
    load_removal_plan,
)


MANIFEST = load_candidate_surface_manifest(
    ROOT / "testing/apg-skill-candidate-surfaces.json", root=ROOT
)
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)
LIFECYCLE = PLAN["closure_contracts"]["actual_lifecycle"]
PLAN_PUBLIC = [
    owner
    for owner in PLAN["owners"]
    if owner["surface_class"] == "historical-evidence"
    and not owner.get("path_pattern", "").startswith("git-object:")
]
PLAN_PRIVATE = [
    owner
    for owner in PLAN["owners"]
    if owner["surface_class"] == "publication-excluded-history"
]
PUBLIC_ENTRIES = PLAN_PUBLIC
PRIVATE_ENTRIES = PLAN_PRIVATE


def _remove_entry(root: Path, entry: dict[str, object]) -> None:
    if "path" in entry:
        paths = [root / str(entry["path"])]
    else:
        paths = list(root.glob(str(entry["path_pattern"])))
    for path in paths:
        if path.is_file() or path.is_symlink():
            path.unlink()


def test_actual_rejection_requires_repository_history(
    tmp_path: Path,
) -> None:
    materialize_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)
    current_paths = {
        owner["path"]
        for owner in PLAN["owners"]
        if owner["surface_class"].startswith("current-") and "path" in owner
    }
    for owner in PLAN["owners"]:
        if owner["surface_class"] not in {
            "historical-evidence",
            "publication-excluded-history",
        }:
            continue
        locator = owner.get("path", owner.get("path_pattern"))
        if locator.startswith(("git-object:", "managed-report:")):
            continue
        for path in tmp_path.glob(locator):
            if path.relative_to(tmp_path).as_posix() in current_paths:
                continue
            if path.is_file() or path.is_symlink():
                path.unlink()

    with pytest.raises(SurfaceContractError, match="histor"):
        assert_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize(
    "entry",
    PUBLIC_ENTRIES,
    ids=lambda entry: str(entry["owner_id"]),
)
def test_each_public_history_owner_is_required(
    tmp_path: Path, entry: dict[str, object]
) -> None:
    materialize_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)
    _remove_entry(tmp_path, entry)
    with pytest.raises(SurfaceContractError):
        assert_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize(
    "entry",
    PRIVATE_ENTRIES,
    ids=lambda entry: str(entry["owner_id"]),
)
def test_each_publication_excluded_history_owner_is_required(
    tmp_path: Path, entry: dict[str, object]
) -> None:
    materialize_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)
    _remove_entry(tmp_path, entry)
    with pytest.raises(SurfaceContractError):
        assert_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)


def test_required_historical_owner_must_not_be_a_symlink(
    tmp_path: Path,
) -> None:
    materialize_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)
    path = (
        tmp_path
        / "docs/evaluations/apg58-css-language-profile-pilot-authoring.md"
    )
    target = path.with_name("preserved-apg58-evaluation.md")
    path.rename(target)
    path.symlink_to(target.name)
    with pytest.raises(SurfaceContractError, match="direct regular"):
        assert_actual_rejected_preserved(tmp_path, MANIFEST, PLAN)


def test_history_owner_symlinked_ancestor_is_rejected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    materialize_actual_rejected_preserved(root, MANIFEST, PLAN)
    evaluations = root / "docs/evaluations"
    external = tmp_path / "external-evaluations"
    evaluations.rename(external)
    evaluations.symlink_to(external, target_is_directory=True)

    with pytest.raises(SurfaceContractError, match="direct directories"):
        assert_plan_history(root, PLAN)
