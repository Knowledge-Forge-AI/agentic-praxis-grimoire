"""Strict current-survivor ownership for APG60C."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_surface_contract import (  # noqa: E402
    SurfaceContractError,
    assert_actual_rejected_surface_absent,
    load_candidate_surface_manifest,
    load_removal_plan,
    materialize_synthetic_state,
)
from apg_candidate_current_state_contract import (  # noqa: E402
    assert_current_survivor,
)


MANIFEST = load_candidate_surface_manifest(
    ROOT / "testing/apg-skill-candidate-surfaces.json", root=ROOT
)
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)
CANDIDATE = "css-language-profile"


def _tree(root: Path) -> None:
    materialize_synthetic_state(root, MANIFEST, PLAN, "rejected")


def test_symlinked_json_survivor_is_not_authoritative(
    tmp_path: Path,
) -> None:
    _tree(tmp_path)
    owner = tmp_path / "release/public-surface.json"
    target = tmp_path / "unrelated.json"
    target.write_text("{}\n", encoding="utf-8")
    owner.unlink()
    owner.symlink_to(target)
    with pytest.raises(SurfaceContractError, match="release-policy"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize("target_kind", ("dangling", "unrelated"))
def test_json_survivor_symlink_target_does_not_matter(
    tmp_path: Path, target_kind: str
) -> None:
    _tree(tmp_path)
    owner = tmp_path / "release/public-surface.json"
    owner.unlink()
    target = tmp_path / "unrelated.json"
    if target_kind == "unrelated":
        target.write_text("{}\n", encoding="utf-8")
    owner.symlink_to(target)
    with pytest.raises(SurfaceContractError, match="release-policy"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_symlinked_python_survivor_is_not_authoritative(
    tmp_path: Path,
) -> None:
    _tree(tmp_path)
    owner = tmp_path / "libexec/apg_project_skills_core.py"
    target = tmp_path / "unrelated.py"
    target.write_text("SAFE = ()\n", encoding="utf-8")
    owner.unlink()
    owner.symlink_to(target)
    with pytest.raises(SurfaceContractError, match="project-expected-skills"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_duplicate_key_json_survivor_fails_closed(tmp_path: Path) -> None:
    _tree(tmp_path)
    owner = tmp_path / "release/public-surface.json"
    owner.write_text('{"clean": true, "clean": false}\n', encoding="utf-8")
    with pytest.raises(SurfaceContractError, match="release-policy"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_direct_regular_survivors_pass(tmp_path: Path) -> None:
    _tree(tmp_path)
    assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_malformed_python_survivor_fails_closed(tmp_path: Path) -> None:
    _tree(tmp_path)
    owner = tmp_path / "libexec/apg_project_skills_core.py"
    owner.write_text("if ):\n", encoding="utf-8")
    with pytest.raises(SurfaceContractError, match="project-expected-skills"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_python_survivor_requires_its_exact_bound_variable(
    tmp_path: Path,
) -> None:
    _tree(tmp_path)
    owner = tmp_path / "libexec/apg_project_skills_core.py"
    owner.write_text("SAFE = ()\n", encoding="utf-8")
    with pytest.raises(
        SurfaceContractError, match="EXPECTED_SKILLS assignment"
    ):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_survivor_cannot_escape_through_parent_traversal(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    (tmp_path / "outside.md").write_text("safe\n", encoding="utf-8")
    owner = {"owner_id": "survivor", "path": "../outside.md"}
    with pytest.raises(SurfaceContractError, match="unsafe path component"):
        assert_current_survivor(root, owner, CANDIDATE)
