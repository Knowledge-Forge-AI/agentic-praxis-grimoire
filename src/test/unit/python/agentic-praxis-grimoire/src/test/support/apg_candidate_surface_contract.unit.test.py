#!/usr/bin/env python3
"""Unit contracts for the generic APG candidate-surface lifecycle model."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_surface_contract import (  # noqa: E402
    SurfaceContractError,
    load_candidate_surface_manifest,
    load_removal_plan,
    validate_candidate_surface_contract,
)


MANIFEST_PATH = ROOT / "testing/apg-skill-candidate-surfaces.json"
PLAN_PATH = ROOT / "src/test/fixtures/apg60-css-removal-plan.json"
CONTRACT_PATH = ROOT / "src/test/fixtures/apg60-css-reentry-contract.json"
MANIFEST = load_candidate_surface_manifest(MANIFEST_PATH, root=ROOT)
PLAN = load_removal_plan(PLAN_PATH, root=ROOT)


def test_manifest_and_plan_are_closed_canonical_and_bound() -> None:
    validate_candidate_surface_contract(MANIFEST, PLAN)
    assert MANIFEST["schema_version"] == 8
    assert MANIFEST["required_roles"]["schema_version"] == 2
    assert MANIFEST["required_roles"]["registry"].endswith(
        "apg_candidate_required_role_registry.py"
    )
    assert PLAN["schema_version"] == 8
    for path, value in ((MANIFEST_PATH, MANIFEST), (PLAN_PATH, PLAN)):
        assert path.read_bytes() == (
            json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        ).encode()
    assert PLAN["source_contract_sha256"] == hashlib.sha256(
        CONTRACT_PATH.read_bytes()
    ).hexdigest()
    for value, validator in (
        (deepcopy(MANIFEST), load_candidate_surface_manifest),
        (deepcopy(PLAN), load_removal_plan),
    ):
        value["unknown"] = True
        with pytest.raises(SurfaceContractError, match="unknown|schema"):
            validator(PLAN_PATH, value=value)


def test_python_owner_bindings_are_frozen_to_exact_variables() -> None:
    plan = deepcopy(PLAN)
    plan["closure_contracts"]["python_bindings"][
        "project-integration-mirror"
    ] = "UNRELATED"
    with pytest.raises(SurfaceContractError, match="frozen owner variables"):
        load_removal_plan(PLAN_PATH, value=plan)
    plan = deepcopy(PLAN)
    del plan["closure_contracts"]["current_survivor_python_bindings"][
        "project-expected-skills"
    ]
    with pytest.raises(
        SurfaceContractError, match="current survivor Python bindings"
    ):
        load_removal_plan(PLAN_PATH, value=plan)


def test_owner_classes_actions_and_relational_mapping() -> None:
    assert {owner["surface_class"] for owner in MANIFEST["owners"]} == {
        "candidate-decision-lifecycle",
        "current-integration-surface",
        "current-narrative-owner",
        "historical-evidence",
        "publication-excluded-history",
        "managed-report",
    }
    assert PLAN["actions"] == [
        "delete",
        "preserve-historical",
        "remove-entry",
        "rewrite-current-summary",
        "verify-absent",
        "verify-survivors",
    ]
    assert {owner["owner_id"] for owner in MANIFEST["owners"]} == {
        owner["owner_id"] for owner in PLAN["owners"]
    }
    current = [
        owner for owner in PLAN["owners"]
        if owner["surface_class"].startswith("current-")
        or owner["surface_class"] == "candidate-decision-lifecycle"
    ]
    assert current
    assert all(owner["retained_omission_test"] for owner in current)
    assert all(owner["rejected_stale_test"] for owner in current)


def test_contract_derives_owner_cardinality() -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    extra_manifest = deepcopy(
        next(
            owner for owner in manifest["owners"]
            if owner["owner_id"] == "history-candidate-evaluations"
        )
    )
    extra_plan = deepcopy(
        next(
            owner for owner in plan["owners"]
            if owner["owner_id"] == "history-candidate-evaluations"
        )
    )
    extra_manifest["owner_id"] = "future-generic-history-owner"
    extra_manifest["path_pattern"] = "docs/evaluations/{candidate_id}-future-*.md"
    extra_plan["owner_id"] = "future-generic-history-owner"
    extra_plan["path_pattern"] = "docs/evaluations/css-language-profile-future-*.md"
    manifest["owners"].append(extra_manifest)
    plan["owners"].append(extra_plan)
    validate_candidate_surface_contract(manifest, plan)


def test_lifecycle_labels_and_action_semantics_are_closed() -> None:
    active = deepcopy(MANIFEST)
    active["lifecycle_labels"]["active_guidance"] = "active-css-guidance"
    with pytest.raises(SurfaceContractError, match="lifecycle"):
        load_candidate_surface_manifest(MANIFEST_PATH, value=active)
    destructive = deepcopy(PLAN)
    historical = next(
        owner for owner in destructive["owners"]
        if owner["surface_class"] == "historical-evidence"
    )
    historical["actions"] = ["delete"]
    with pytest.raises(SurfaceContractError, match="historical|action"):
        load_removal_plan(PLAN_PATH, value=destructive)


def test_required_owner_families_cannot_self_delete_from_both_artifacts() -> None:
    required_owner_ids = {
        role["owner_id"] for role in MANIFEST["required_roles"]["roles"]
    }
    assert len(required_owner_ids) == 52
    assert required_owner_ids == {
        owner["owner_id"] for owner in MANIFEST["owners"]
    }
    assert required_owner_ids == {
        owner["owner_id"] for owner in PLAN["owners"]
    }


@pytest.mark.parametrize(
    "owner_id",
    tuple(
        sorted(
            role["owner_id"]
            for role in MANIFEST["required_roles"]["roles"]
        )
    ),
)
def test_each_required_owner_cannot_self_delete_from_both_artifacts(
    owner_id: str,
) -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    manifest["owners"] = [
        owner for owner in manifest["owners"]
        if owner["owner_id"] != owner_id
    ]
    plan["owners"] = [
        owner for owner in plan["owners"]
        if owner["owner_id"] != owner_id
    ]

    with pytest.raises(SurfaceContractError, match=owner_id):
        validate_candidate_surface_contract(manifest, plan)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("surface_class", "historical-evidence"),
        ("generic_locator", "skills/unrelated/SKILL.md"),
    ),
)
def test_required_role_declaration_rejects_wrong_semantics(
    field: str,
    value: str,
) -> None:
    manifest = deepcopy(MANIFEST)
    manifest["required_roles"]["roles"][0][field] = value
    with pytest.raises(SurfaceContractError, match="canonical-leaf"):
        validate_candidate_surface_contract(manifest, deepcopy(PLAN))


def test_additive_owner_cannot_duplicate_required_role_semantics() -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    duplicate_manifest = deepcopy(manifest["owners"][0])
    duplicate_plan = deepcopy(plan["owners"][0])
    duplicate_manifest["owner_id"] = "future-canonical-leaf"
    duplicate_plan["owner_id"] = "future-canonical-leaf"
    manifest["owners"].append(duplicate_manifest)
    plan["owners"].append(duplicate_plan)
    with pytest.raises(SurfaceContractError, match="canonical-leaf"):
        validate_candidate_surface_contract(manifest, plan)


def test_required_role_rejects_wrong_concrete_locator() -> None:
    plan = deepcopy(PLAN)
    owner = next(
        item for item in plan["owners"]
        if item["owner_id"] == "candidate-contract-map"
    )
    owner["path"] = "docs/specs/unrelated.contract-map.json"
    with pytest.raises(SurfaceContractError, match="candidate-contract-map"):
        validate_candidate_surface_contract(deepcopy(MANIFEST), plan)


def test_coherent_required_role_redirection_cannot_change_semantics() -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    declaration = next(
        role
        for role in manifest["required_roles"]["roles"]
        if role["owner_id"] == "candidate-fixture"
    )
    declaration["generic_locator"] = "skills/{candidate_id}/SKILL.md"
    declaration["locator_kind"] = "path"
    manifest_owner = next(
        owner for owner in manifest["owners"]
        if owner["owner_id"] == "candidate-fixture"
    )
    manifest_owner.pop("path_pattern")
    manifest_owner["path"] = "skills/{candidate_id}/SKILL.md"
    plan_owner = next(
        owner for owner in plan["owners"]
        if owner["owner_id"] == "candidate-fixture"
    )
    plan_owner.pop("path_pattern")
    plan_owner["path"] = "skills/css-language-profile/SKILL.md"
    with pytest.raises(SurfaceContractError, match="candidate-fixture"):
        validate_candidate_surface_contract(manifest, plan)


@pytest.mark.parametrize(
    ("closure", "field", "value"),
    (
        ("traceability", "contract_map_owner_id", "undeclared-map-owner"),
        ("traceability", "clause_owner_ids", ["canonical-leaf", "projection"]),
        ("candidate_decision", "decision_owner_id", "undeclared-decision"),
        ("candidate_decision", "index_owner_id", "narrative-readme"),
        ("candidate_decision", "index_path", "docs/adr/unrelated.md"),
    ),
)
def test_cross_references_are_contract_exact(
    closure: str,
    field: str,
    value: str | list[str],
) -> None:
    plan = deepcopy(PLAN)
    plan["closure_contracts"][closure][field] = value
    with pytest.raises(SurfaceContractError):
        validate_candidate_surface_contract(deepcopy(MANIFEST), plan)


@pytest.mark.parametrize(
    "owner_id",
    ("candidate-contract-map", "candidate-decision-record"),
)
def test_critical_required_role_self_deletion_fails_bounded(
    owner_id: str,
) -> None:
    manifest = deepcopy(MANIFEST)
    plan = deepcopy(PLAN)
    manifest["owners"] = [
        owner for owner in manifest["owners"]
        if owner["owner_id"] != owner_id
    ]
    plan["owners"] = [
        owner for owner in plan["owners"]
        if owner["owner_id"] != owner_id
    ]

    with pytest.raises(SurfaceContractError, match=owner_id):
        validate_candidate_surface_contract(manifest, plan)


@pytest.mark.parametrize(
    ("relative", "source", "loader"),
    (
        (
            "testing/apg-skill-candidate-surfaces.json",
            MANIFEST_PATH,
            load_candidate_surface_manifest,
        ),
        (
            "src/test/fixtures/apg60-css-removal-plan.json",
            PLAN_PATH,
            load_removal_plan,
        ),
    ),
    ids=("candidate-surface-manifest", "removal-plan"),
)
def test_authority_json_rejects_symlinked_repository_ancestor(
    tmp_path: Path,
    relative: str,
    source: Path,
    loader,
) -> None:
    root = tmp_path / "repository"
    path = root / relative
    external_parent = tmp_path / f"external-{path.parent.name}"
    external_parent.mkdir(parents=True)
    (external_parent / path.name).write_bytes(source.read_bytes())
    path.parent.parent.mkdir(parents=True)
    path.parent.symlink_to(external_parent, target_is_directory=True)

    with pytest.raises(SurfaceContractError, match="ancestor|direct"):
        loader(path, root=root)
