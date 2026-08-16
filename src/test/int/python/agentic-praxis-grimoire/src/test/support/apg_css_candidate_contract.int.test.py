#!/usr/bin/env python3
"""Integration coverage for APG60 CSS contract and removal closure."""

from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_surface_contract import (  # noqa: E402
    SurfaceContractError,
    assert_actual_rejected_surface_absent,
    assert_synthetic_lifecycle,
    derive_skill_surface_counts,
    load_candidate_surface_manifest,
    load_removal_plan,
    materialize_synthetic_state,
)
from apg_candidate_actual_lifecycle_contract import (  # noqa: E402
    assert_actual_rejected_preserved,
)
from apg_css_candidate_contract import (  # noqa: E402
    assert_case_expected,
    load_contract,
    validate_collected_case_ids,
)


APG58 = "7934d3a936d22f26c0533d46b5e9b603de516034"
APG59 = "133166a4d084ba5d347b133054e4dda515add63f"
APG60 = "15e253eea62c3f0fd9286cdd604b2f7231f81b64"
CONTRACT = load_contract(
    ROOT / "src/test/fixtures/apg60-css-reentry-contract.json", ROOT
)
MANIFEST = load_candidate_surface_manifest(
    ROOT / "testing/apg-skill-candidate-surfaces.json", root=ROOT
)
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)
CURRENT_IDS = [
    owner["owner_id"] for owner in PLAN["owners"]
    if owner["surface_class"].startswith("current-")
]
HISTORICAL_IDS = [
    owner["owner_id"] for owner in PLAN["owners"]
    if not owner["surface_class"].startswith("current-")
]
SURVIVOR_IDS = [
    owner["owner_id"] for owner in PLAN["owners"]
    if owner["surface_class"] == "current-integration-surface"
    and "verify-survivors" in owner["actions"]
    and "delete" not in owner["actions"]
]


@pytest.mark.parametrize("case", CONTRACT["cases"], ids=lambda case: case["id"])
def test_all_sixty_cases_are_collected_and_executed(case: dict[str, object]) -> None:
    assert_case_expected(case)


def test_all_sixty_case_ids_are_complete() -> None:
    validate_collected_case_ids(CONTRACT, [case["id"] for case in CONTRACT["cases"]])


def test_apg60a_revision_preserves_exact_unrelated_contract_semantics() -> None:
    original = json.loads(
        subprocess.run(
            [
                "git",
                "show",
                f"{APG60}:src/test/fixtures/apg60-css-reentry-contract.json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert CONTRACT["schema_version"] == 2
    assert CONTRACT["contract_revision"] == "APG60A"
    assert CONTRACT["supersedes_contract_sha256"] == (
        "d0847c10577ed59336693093dbaf422ac9944a4ab1631833ebf328680c283858"
    )
    for field in ("candidate", "counting", "policy", "status"):
        assert CONTRACT[field] == original[field]
    assert [case["id"] for case in CONTRACT["cases"]] == [
        case["id"] for case in original["cases"]
    ]
    for corrected, historical in zip(
        CONTRACT["cases"], original["cases"], strict=True
    ):
        grant_source = corrected["exception_grant_source"]
        comparable = dict(corrected)
        comparable.pop("exception_grant_source")
        if corrected["id"] == "APG60-CSS-024":
            assert grant_source == "repository-policy"
            for field in comparable.keys() - {"expected"}:
                assert comparable[field] == historical[field]
            assert comparable["expected"]["selected_owner"] == "repository-policy"
            assert "apply-repository-policy" in comparable["expected"]["required_actions"]
        else:
            assert grant_source is None
            assert comparable == historical


def test_synthetic_fully_present_and_removed_lifecycles(tmp_path: Path) -> None:
    retained = tmp_path / "retained"
    rejected = tmp_path / "rejected"
    materialize_synthetic_state(retained, MANIFEST, PLAN, "retained")
    materialize_synthetic_state(rejected, MANIFEST, PLAN, "rejected")
    assert_synthetic_lifecycle(retained, MANIFEST, PLAN, "retained")
    assert_synthetic_lifecycle(rejected, MANIFEST, PLAN, "rejected")


@pytest.mark.parametrize("owner_id", CURRENT_IDS)
def test_each_current_owner_omission_fails_retained_closure(
    tmp_path: Path, owner_id: str
) -> None:
    materialize_synthetic_state(
        tmp_path, MANIFEST, PLAN, "retained", omit_owner=owner_id
    )
    with pytest.raises(SurfaceContractError, match=owner_id):
        assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "retained")


@pytest.mark.parametrize("owner_id", CURRENT_IDS)
def test_each_current_owner_stale_fails_rejected_closure(
    tmp_path: Path, owner_id: str
) -> None:
    materialize_synthetic_state(
        tmp_path, MANIFEST, PLAN, "rejected", stale_owner=owner_id
    )
    with pytest.raises(SurfaceContractError, match=owner_id):
        assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "rejected")


@pytest.mark.parametrize("owner_id", HISTORICAL_IDS)
def test_each_historical_owner_must_survive_rejected_cleanup(
    tmp_path: Path, owner_id: str
) -> None:
    materialize_synthetic_state(
        tmp_path, MANIFEST, PLAN, "rejected", omit_owner=owner_id
    )
    with pytest.raises(SurfaceContractError, match=owner_id):
        assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "rejected")


@pytest.mark.parametrize("owner_id", SURVIVOR_IDS)
def test_each_rejected_survivor_container_must_remain(
    tmp_path: Path, owner_id: str
) -> None:
    materialize_synthetic_state(
        tmp_path, MANIFEST, PLAN, "rejected", omit_owner=owner_id
    )
    with pytest.raises(SurfaceContractError, match=owner_id):
        assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "rejected")


def test_surviving_reference_requires_retained_owner_or_fallback(tmp_path: Path) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    (tmp_path / ".apg-synthetic-references").write_text(
        "APG_REF:canonical-leaf\n", encoding="utf-8"
    )
    with pytest.raises(SurfaceContractError, match="surviving reference"):
        assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "rejected")
    (tmp_path / ".apg-synthetic-references").write_text(
        "APG_FALLBACK:project-policy\n", encoding="utf-8"
    )
    assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "rejected")


def test_exact_apg58_apg59_history_and_live_integrated_surface() -> None:
    def tree_has(revision: str, path: str) -> bool:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{revision}:{path}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    assert tree_has(APG58, "skills/css-language-profile/SKILL.md")
    assert tree_has(APG58, "docs/specs/css-language-profile.md")
    assert not tree_has(APG59, "skills/css-language-profile/SKILL.md")
    assert not tree_has(APG59, "docs/specs/css-language-profile.md")
    for revision in (APG58, APG59):
        assert tree_has(
            revision,
            "docs/adr/2026/07/0035-css-language-profile-and-policy-selected-structural-limits.md",
        )
        assert tree_has(
            revision,
            "docs/evaluations/apg58-css-language-profile-pilot-authoring.md",
        )
    assert subprocess.run(
        ["git", "rev-parse", f"{APG58}^{{tree}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "da8b8169f633f2861ab28a3f7ef1cc8581d6d317"
    assert subprocess.run(
        ["git", "rev-parse", f"{APG59}^{{tree}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == "ba6bd057cfdbe81ee111287e6c268b8c5ca8cceb"
    assert subprocess.run(
        ["git", "rev-list", "--parents", "-1", APG59],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split() == [APG59, APG58]
    assert (ROOT / "skills/css-language-profile/SKILL.md").is_file()
    assert (ROOT / ".agents/skills/css-language-profile").is_symlink()
    assert "Accepted with amendment (APG77D)" in (
        ROOT
        / "docs/adr/2026/08/0044-css-language-profile-candidate-and-target-first-harness.md"
    ).read_text(encoding="utf-8")
    assert derive_skill_surface_counts(ROOT) == (33, 33, 33)


def test_raw_apg59_revert_restores_candidate_and_fails_closure() -> None:
    checkout_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="apg60-revert-") as temporary:
        checkout_path = Path(temporary) / "checkout"
        subprocess.run(
            ["git", "clone", "--shared", "--no-checkout", str(ROOT), str(checkout_path)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "--detach", APG59],
            cwd=checkout_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "revert", "--no-commit", APG59],
            cwd=checkout_path,
            check=True,
            capture_output=True,
        )
        with pytest.raises(SurfaceContractError, match="current candidate surface"):
            assert_actual_rejected_surface_absent(checkout_path, MANIFEST, PLAN)
    assert checkout_path is not None
    assert not checkout_path.exists()


def test_lifecycle_helpers_do_not_mutate_live_repository(tmp_path: Path) -> None:
    before = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "retained")
    assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "retained")
    after = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert after == before
    assert shutil.which("git")


def test_owner_markers_cannot_be_relocated_away_from_declared_locator(
    tmp_path: Path,
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "retained")
    leaf = tmp_path / "skills/css-language-profile/SKILL.md"
    moved = tmp_path / "unrelated.txt"
    moved.write_text(leaf.read_text(encoding="utf-8"), encoding="utf-8")
    leaf.unlink()
    with pytest.raises(SurfaceContractError, match="canonical-leaf"):
        assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "retained")


def test_unmarked_stale_release_content_fails_rejected_closure(
    tmp_path: Path,
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    policy = tmp_path / "release/public-surface.json"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        '{"required_skills":["skills/css-language-profile/SKILL.md"]}\n',
        encoding="utf-8",
    )
    with pytest.raises(SurfaceContractError, match="release-policy"):
        assert_synthetic_lifecycle(tmp_path, MANIFEST, PLAN, "rejected")


def test_actual_closure_rejects_active_claim_despite_later_history(
    tmp_path: Path,
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    readme = tmp_path / "README.md"
    readme.write_text(
        "css-language-profile is ACTIVE CURRENT GUIDANCE\n"
        "Historical note: css-language-profile was rejected\n",
        encoding="utf-8",
    )
    with pytest.raises(SurfaceContractError, match="README"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize(
    "target",
    (
        "../../skills/css-language-profile",
        "../../skills/missing-css-language-profile",
    ),
)
def test_actual_rejected_scan_detects_dangling_candidate_projection(
    tmp_path: Path, target: str
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    projection = tmp_path / ".agents/skills/css-language-profile"
    projection.parent.mkdir(parents=True, exist_ok=True)
    projection.symlink_to(target)
    with pytest.raises(SurfaceContractError, match="current candidate surface"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_actual_rejected_scan_detects_projection_to_unrelated_target(
    tmp_path: Path,
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    unrelated = tmp_path / "skills/unrelated-profile"
    unrelated.mkdir(parents=True)
    projection = tmp_path / ".agents/skills/css-language-profile"
    projection.parent.mkdir(parents=True, exist_ok=True)
    projection.symlink_to("../../skills/unrelated-profile")
    with pytest.raises(SurfaceContractError, match="current candidate surface"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_actual_rejected_scan_detects_broken_pattern_symlink(
    tmp_path: Path,
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    fixture = tmp_path / "src/test/fixtures/candidate-css-language-profile.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.symlink_to("missing-candidate-fixture.json")
    with pytest.raises(SurfaceContractError, match="current candidate surface"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


@pytest.mark.parametrize("stale_kind", ("file", "directory"))
def test_actual_rejected_scan_detects_regular_or_directory_leaf_residue(
    tmp_path: Path, stale_kind: str
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    leaf = tmp_path / "skills/css-language-profile/SKILL.md"
    leaf.parent.mkdir(parents=True, exist_ok=True)
    if stale_kind == "file":
        leaf.write_text("stale candidate\n", encoding="utf-8")
    else:
        leaf.mkdir()
    with pytest.raises(SurfaceContractError, match="current candidate surface"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_actual_rejected_scan_allows_absence_and_foundation_exclusions(
    tmp_path: Path,
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    for exclusion in PLAN["contract_foundation_exclusions"]:
        path = tmp_path / exclusion["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("candidate-independent foundation\n", encoding="utf-8")
    assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_actual_unintegrated_proposed_decision_is_not_terminal(
    tmp_path: Path,
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    decision_owner = next(
        owner
        for owner in PLAN["owners"]
        if owner["surface_class"] == "candidate-decision-lifecycle"
    )
    decision = tmp_path / decision_owner["path"]
    decision.write_text(
        decision.read_text(encoding="utf-8").replace(
            "- Status: Rejected", "- Status: Proposed"
        ),
        encoding="utf-8",
    )
    index = tmp_path / PLAN["closure_contracts"]["candidate_decision"]["index_path"]
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "— Rejected", "— Proposed"
        ),
        encoding="utf-8",
    )

    with pytest.raises(SurfaceContractError, match="not terminal"):
        assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_actual_rejected_scan_does_not_conflate_historical_symlink(
    tmp_path: Path,
) -> None:
    materialize_synthetic_state(tmp_path, MANIFEST, PLAN, "rejected")
    target = tmp_path / "docs/evaluations/apg58-css-language-profile-history.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("historical rejected candidate evidence\n", encoding="utf-8")
    link = tmp_path / "docs/evaluations/apg59-css-language-profile-history.md"
    link.symlink_to(target.name)
    assert_actual_rejected_surface_absent(tmp_path, MANIFEST, PLAN)


def test_apg59_and_live_counts_preserve_css_rejection_across_growth(
    tmp_path: Path,
) -> None:
    checkout = tmp_path / "apg59"
    subprocess.run(
        ["git", "clone", "--shared", "--no-checkout", str(ROOT), str(checkout)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "--detach", APG59],
        cwd=checkout,
        check=True,
        capture_output=True,
    )
    assert derive_skill_surface_counts(checkout) == (28, 28, 28)
    assert derive_skill_surface_counts(ROOT) == (33, 33, 33)
    for repository, expected in ((checkout, 28), (ROOT, 33)):
        result = subprocess.run(
            ["bin/apg-check-skill-library", "--format", "json"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        assert json.loads(result.stdout)["summary"] == {
            "canonical_skills": expected,
            "catalog_rows": expected,
            "projections": expected,
        }
