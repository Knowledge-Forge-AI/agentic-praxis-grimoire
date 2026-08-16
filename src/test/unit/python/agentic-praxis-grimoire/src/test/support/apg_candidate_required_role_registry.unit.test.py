"""Independent semantic-role authority for candidate lifecycle surfaces."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_required_role_registry import (  # noqa: E402
    REGISTRY_PATH,
    ROLE_BY_ID,
    ROLE_REGISTRY,
    validate_required_role_registry,
)
from apg_candidate_surface_contract import (  # noqa: E402
    SurfaceContractError,
    load_candidate_surface_manifest,
    load_removal_plan,
    validate_candidate_surface_contract,
)


MANIFEST = load_candidate_surface_manifest(
    ROOT / "testing/apg-skill-candidate-surfaces.json", root=ROOT
)
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)


def _fail(message: str) -> None:
    raise SurfaceContractError(message)


def test_registry_is_candidate_neutral_and_complete() -> None:
    assert REGISTRY_PATH.endswith("apg_candidate_required_role_registry.py")
    assert len(ROLE_REGISTRY) == 52
    assert "css-language-profile" not in repr(ROLE_REGISTRY)
    assert set(ROLE_BY_ID) == {
        role["owner_id"] for role in MANIFEST["required_roles"]["roles"]
    }


def test_manifest_and_plan_pass_independent_registry() -> None:
    validate_required_role_registry(MANIFEST, PLAN, fail=_fail)


@pytest.mark.parametrize(
    "owner_id",
    (
        "candidate-fixture",
        "candidate-contract-map",
        "candidate-decision-record",
        "focused-unit-test",
        "focused-integration-test",
        "release-policy-required-skills",
        "projection",
        "test-inventory-entry",
    ),
)
def test_coordinated_redirection_fails_against_code_owned_semantics(
    owner_id: str,
) -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    declaration = next(
        role
        for role in manifest["required_roles"]["roles"]
        if role["owner_id"] == owner_id
    )
    declaration["locator_kind"] = "path"
    declaration["generic_locator"] = "skills/{candidate_id}/SKILL.md"
    manifest_owner = next(
        owner for owner in manifest["owners"] if owner["owner_id"] == owner_id
    )
    for locator in ("path", "path_pattern"):
        manifest_owner.pop(locator, None)
    manifest_owner["path"] = "skills/{candidate_id}/SKILL.md"
    plan_owner = next(
        owner for owner in plan["owners"] if owner["owner_id"] == owner_id
    )
    for locator in ("path", "path_pattern"):
        plan_owner.pop(locator, None)
    plan_owner["path"] = "skills/css-language-profile/SKILL.md"
    with pytest.raises(SurfaceContractError, match=owner_id):
        validate_required_role_registry(manifest, plan, fail=_fail)


def test_wrong_verification_family_fails_independently() -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    target = next(
        owner for owner in manifest["owners"]
        if owner["owner_id"] == "candidate-fixture"
    )
    target["verification_family"] = "decision"
    with pytest.raises(SurfaceContractError, match="candidate-fixture"):
        validate_required_role_registry(manifest, plan, fail=_fail)


def test_verification_method_keywords_cannot_substitute_for_family_token() -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    target = next(
        owner for owner in manifest["owners"]
        if owner["owner_id"] == "candidate-fixture"
    )
    target["verification_method"] = "family:decision| fixture"
    with pytest.raises(SurfaceContractError, match="candidate-fixture"):
        validate_required_role_registry(manifest, plan, fail=_fail)


def test_cross_reference_obligation_is_code_owned() -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    plan["closure_contracts"]["candidate_decision"][
        "decision_owner_id"
    ] = "candidate-specification"
    with pytest.raises(SurfaceContractError, match="candidate-decision-record"):
        validate_required_role_registry(manifest, plan, fail=_fail)


@pytest.mark.parametrize(
    "owner_id",
    (
        "history-candidate-adr",
        "history-candidate-evaluations",
        "history-candidate-exits",
        "history-git-objects",
        "history-predecessor-public-evidence",
        "private-candidate-phase-evidence",
        "private-predecessor-evidence",
        "managed-candidate-reports",
    ),
)
def test_historical_locator_family_cannot_be_redirected(
    owner_id: str,
) -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    owner = next(item for item in plan["owners"] if item["owner_id"] == owner_id)
    locator = "path_pattern" if "path_pattern" in owner else "path"
    narrowed = {
        "history-candidate-adr": "docs/adr/2026/07/0035-css-language-profile-wrong.md",
        "history-candidate-evaluations": "docs/evaluations/apg58-css-language-profile-wrong.md",
        "history-candidate-exits": "docs/status/2026/07/29/00078-apg58-css-language-profile-wrong.md",
        "history-git-objects": "git-object:APG58",
        "history-predecessor-public-evidence": "docs/x/web-wrong-node.md",
        "private-candidate-phase-evidence": "private/evaluations/apg999/**",
        "private-predecessor-evidence": "private/evaluations/apg60f/**",
        "managed-candidate-reports": "managed-report:APG58",
    }
    owner[locator] = narrowed[owner_id]
    with pytest.raises(SurfaceContractError, match=owner_id):
        validate_required_role_registry(manifest, plan, fail=_fail)
    with pytest.raises(SurfaceContractError, match=owner_id):
        validate_candidate_surface_contract(manifest, plan)


def test_additive_unrelated_role_does_not_shadow_required_registry() -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    manifest["owners"].append(
        {
            "historical_preservation_rule": "An unrelated additive record.",
            "owner_id": "future-additive-history",
            "path": "docs/future-additive-history.md",
            "present_state_obligation": "Historical only.",
            "rejected_removal_obligation": "Preserve it.",
            "surface_class": "historical-evidence",
            "verification_family": "history",
            "verification_method": "historical path presence check",
        }
    )
    plan["owners"].append(
        {
            "actions": ["preserve-historical", "verify-survivors"],
            "owner_id": "future-additive-history",
            "path": "docs/future-additive-history.md",
            "rejected_stale_test": False,
            "retained_omission_test": False,
            "surface_class": "historical-evidence",
        }
    )
    validate_candidate_surface_contract(manifest, plan)
