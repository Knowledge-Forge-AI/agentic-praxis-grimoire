"""Exact required-role and cross-reference contract for candidate lifecycles."""

from __future__ import annotations

from collections import Counter
import fnmatch
import re
from typing import Any, Callable, NoReturn

from apg_candidate_required_role_registry import (
    REGISTRY_PATH,
    validate_required_role_registry,
)


Fail = Callable[[str], NoReturn]
ROLE_FIELDS = {
    "generic_locator",
    "locator_kind",
    "owner_id",
    "surface_class",
}
LOCATOR_KINDS = {"path", "path_pattern"}
LIFECYCLE_CLASSES = {
    "candidate-decision-lifecycle",
    "current-integration-surface",
    "current-narrative-owner",
}
PYTHON_BINDINGS = {
    "project-command-integration-mirror": "EXPECTED_SKILLS",
    "project-expected-skills": "EXPECTED_SKILLS",
    "project-integration-mirror": "EXPECTED_SKILLS",
    "project-unit-mirror": "EXPECTED_SKILLS",
    "release-helper-audited-critical": "AUDITED_CRITICAL",
    "release-helper-audited-projections": "AUDITED_PROJECTIONS",
    "release-helper-audited-skills": "AUDITED_SKILLS",
    "release-helper-audited-tests": "AUDITED_TESTS",
    "release-integration-mirror": "EXPECTED_SURFACES",
    "release-shared-case-mirror": "EXPECTED_SURFACES",
    "release-unit-mirror": "EXPECTED_SURFACES",
}
CURRENT_SURVIVOR_PYTHON_BINDINGS = {
    "project-expected-skills": "EXPECTED_SKILLS",
    "release-helper-audited-critical": "AUDITED_CRITICAL",
    "release-helper-audited-projections": "AUDITED_PROJECTIONS",
    "release-helper-audited-skills": "AUDITED_SKILLS",
    "release-helper-audited-tests": "AUDITED_TESTS",
}
DYNAMIC_ROLE_IDS = {
    "dynamic-global-installer-consumer",
    "dynamic-skill-library-consumer",
    "dynamic-topology-consumer",
}
NARRATIVE_ROLE_IDS = {
    "narrative-adr-index",
    "narrative-agents",
    "narrative-project-model",
    "narrative-project-skill-projection",
    "narrative-provenance",
    "narrative-public-release-process",
    "narrative-readme",
    "narrative-roadmap",
    "narrative-skill-maintenance",
    "narrative-status-index",
    "narrative-v0-5-roadmap",
}
HISTORY_ROLE_IDS = {
    "history-candidate-adr",
    "history-candidate-evaluations",
    "history-candidate-exits",
    "history-git-objects",
    "history-predecessor-fact-check",
    "history-predecessor-public-evidence",
    "history-provenance-sections",
    "private-candidate-phase-evidence",
    "private-predecessor-evidence",
}
MANAGED_REPORT_ROLE_IDS = {"managed-candidate-reports"}
REQUIRED_ROLE_IDS = frozenset(
    {
        "canonical-leaf",
        "candidate-contract-map",
        "candidate-decision-record",
        "candidate-fixture",
        "candidate-specification",
        "capability-map-entry",
        "focused-integration-test",
        "focused-unit-test",
        "project-command-integration-mirror",
        "project-expected-skills",
        "project-integration-mirror",
        "project-unit-mirror",
        "projection",
        "release-helper-audited-critical",
        "release-helper-audited-projections",
        "release-helper-audited-skills",
        "release-helper-audited-tests",
        "release-integration-mirror",
        "release-policy-critical-files",
        "release-policy-required-projections",
        "release-policy-required-skills",
        "release-policy-required-tests",
        "release-shared-case-mirror",
        "release-unit-mirror",
        "router-consumer",
        "skill-catalog-row",
        "skill-maturity-row",
        "test-inventory-entry",
    }
    | DYNAMIC_ROLE_IDS
    | NARRATIVE_ROLE_IDS
    | HISTORY_ROLE_IDS
    | MANAGED_REPORT_ROLE_IDS
)


def _string(value: Any, context: str, fail: Fail) -> str:
    if not isinstance(value, str) or not value or value.startswith("/"):
        fail(f"{context} must be a nonempty non-absolute string")
    return value


def validate_required_roles_declaration(
    value: Any,
    *,
    fail: Fail,
) -> tuple[dict[str, Any], ...]:
    """Validate the versioned closed declaration of all required role IDs."""
    if (
        not isinstance(value, dict)
        or set(value) != {"registry", "roles", "schema_version"}
    ):
        fail("required roles declaration has unknown or missing keys")
    if value["schema_version"] != 2:
        fail("required roles declaration schema version is invalid")
    if value["registry"] != REGISTRY_PATH:
        fail("required roles declaration registry path is invalid")
    roles = value["roles"]
    if not isinstance(roles, list) or not roles:
        fail("required roles declaration must contain role records")
    for index, role in enumerate(roles):
        if not isinstance(role, dict) or set(role) != ROLE_FIELDS:
            fail(f"required role {index} has unknown or missing keys")
        _string(role["owner_id"], f"required role {index} owner ID", fail)
        _string(
            role["surface_class"],
            f"required role {index} surface class",
            fail,
        )
        _string(
            role["generic_locator"],
            f"required role {index} generic locator",
            fail,
        )
        if role["locator_kind"] not in LOCATOR_KINDS:
            fail(f"required role {index} locator kind is invalid")
    ids = [role["owner_id"] for role in roles]
    duplicates = sorted(
        owner_id for owner_id, count in Counter(ids).items() if count != 1
    )
    if duplicates:
        fail("required role IDs are duplicated: " + ", ".join(duplicates))
    missing = sorted(REQUIRED_ROLE_IDS - set(ids))
    extra = sorted(set(ids) - REQUIRED_ROLE_IDS)
    if missing:
        fail("required roles declaration is missing: " + ", ".join(missing))
    if extra:
        fail("required roles declaration has unknown IDs: " + ", ".join(extra))
    return tuple(roles)


def _locator(owner: dict[str, Any], owner_id: str, fail: Fail) -> tuple[str, str]:
    kinds = LOCATOR_KINDS & set(owner)
    if len(kinds) != 1:
        fail(f"{owner_id}: owner must have exactly one locator")
    kind = next(iter(kinds))
    return kind, _string(owner[kind], f"{owner_id} locator", fail)


def _owners_by_id(
    owners: Any,
    artifact: str,
    fail: Fail,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(owners, list):
        fail(f"{artifact} owners must be an array")
    indexed: dict[str, list[dict[str, Any]]] = {}
    for owner in owners:
        if not isinstance(owner, dict) or not isinstance(owner.get("owner_id"), str):
            fail(f"{artifact} owner record is invalid")
        indexed.setdefault(owner["owner_id"], []).append(owner)
    return indexed


def _exact_owner(
    indexed: dict[str, list[dict[str, Any]]],
    owner_id: str,
    artifact: str,
    fail: Fail,
) -> dict[str, Any]:
    matches = indexed.get(owner_id, [])
    if len(matches) != 1:
        fail(f"{owner_id}: required role must exist exactly once in {artifact}")
    return matches[0]


def _render_generic(generic: str, candidate: str) -> str:
    rendered = generic.replace("{candidate_id}", candidate)
    return re.sub(r"\{[a-z][a-z0-9_]*\}", "*", rendered)


def _concrete_agrees(generic: str, concrete: str, candidate: str) -> bool:
    rendered = _render_generic(generic, candidate)
    return concrete == rendered or fnmatch.fnmatchcase(concrete, rendered)


def _semantic(role: dict[str, Any]) -> tuple[str, str, str]:
    return (
        role["surface_class"],
        role["locator_kind"],
        role["generic_locator"],
    )


def _manifest_semantic(owner: dict[str, Any], fail: Fail) -> tuple[str, str, str]:
    owner_id = owner["owner_id"]
    kind, locator = _locator(owner, owner_id, fail)
    return owner["surface_class"], kind, locator


def _validate_required_owners(
    roles: tuple[dict[str, Any], ...],
    manifest_index: dict[str, list[dict[str, Any]]],
    plan_index: dict[str, list[dict[str, Any]]],
    candidate: str,
    fail: Fail,
) -> None:
    manifest_owners = [
        owner for matches in manifest_index.values() for owner in matches
    ]
    declared_semantics = Counter(_semantic(role) for role in roles)
    actual_semantics = Counter(
        _manifest_semantic(owner, fail) for owner in manifest_owners
    )
    for semantic, expected_count in declared_semantics.items():
        if actual_semantics[semantic] != expected_count:
            role_ids = sorted(
                role["owner_id"] for role in roles if _semantic(role) == semantic
            )
            fail(
                "required role semantic is missing or duplicated: "
                + ", ".join(role_ids)
            )
    for role in roles:
        owner_id = role["owner_id"]
        manifest_owner = _exact_owner(
            manifest_index, owner_id, "manifest", fail
        )
        plan_owner = _exact_owner(plan_index, owner_id, "removal plan", fail)
        if manifest_owner["surface_class"] != role["surface_class"]:
            fail(f"{owner_id}: manifest required role has the wrong surface class")
        if plan_owner["surface_class"] != role["surface_class"]:
            fail(f"{owner_id}: removal-plan required role has the wrong surface class")
        manifest_kind, generic = _locator(manifest_owner, owner_id, fail)
        plan_kind, concrete = _locator(plan_owner, owner_id, fail)
        if manifest_kind != role["locator_kind"] or generic != role["generic_locator"]:
            fail(f"{owner_id}: manifest required role locator is not exact")
        kind_agrees = plan_kind == role["locator_kind"] or (
            role["locator_kind"] == "path_pattern" and plan_kind == "path"
        )
        if not kind_agrees or not _concrete_agrees(generic, concrete, candidate):
            fail(f"{owner_id}: removal-plan locator disagrees with generic role")


def _validate_owner_relations(
    manifest_index: dict[str, list[dict[str, Any]]],
    plan_index: dict[str, list[dict[str, Any]]],
    candidate: str,
    fail: Fail,
) -> None:
    if set(manifest_index) != set(plan_index):
        fail("manifest and removal-plan owner sets differ")
    for owner_id, manifest_matches in manifest_index.items():
        manifest_owner = _exact_owner(
            manifest_index, owner_id, "manifest", fail
        )
        plan_owner = _exact_owner(plan_index, owner_id, "removal plan", fail)
        if manifest_owner["surface_class"] != plan_owner["surface_class"]:
            fail(f"{owner_id}: surface class differs between artifacts")
        manifest_kind, generic = _locator(manifest_owner, owner_id, fail)
        plan_kind, concrete = _locator(plan_owner, owner_id, fail)
        is_lifecycle = plan_owner["surface_class"] in LIFECYCLE_CLASSES
        if is_lifecycle and manifest_kind != plan_kind:
            fail(f"{owner_id}: current locator kind differs between artifacts")
        if is_lifecycle and generic.replace("{candidate_id}", candidate) != concrete:
            fail(f"{owner_id}: current locator does not instantiate the manifest")
        if plan_owner["retained_omission_test"] is not is_lifecycle:
            fail(f"{owner_id}: retained omission control differs from owner class")
        if plan_owner["rejected_stale_test"] is not is_lifecycle:
            fail(f"{owner_id}: rejected stale control differs from owner class")
        if len(manifest_matches) != 1:
            fail(f"{owner_id}: manifest owner is duplicated")


def _require_class(
    plan_index: dict[str, list[dict[str, Any]]],
    owner_id: str,
    expected: str,
    context: str,
    fail: Fail,
) -> dict[str, Any]:
    owner = _exact_owner(plan_index, owner_id, "removal plan", fail)
    if owner["surface_class"] != expected:
        fail(f"{owner_id}: {context} requires {expected}")
    return owner


def _validate_cross_references(
    plan: dict[str, Any],
    plan_index: dict[str, list[dict[str, Any]]],
    candidate: str,
    fail: Fail,
) -> None:
    closure = plan["closure_contracts"]
    for owner_id in closure["actual_lifecycle"]["authored_owner_ids"]:
        _require_class(
            plan_index,
            owner_id,
            "current-integration-surface",
            "authored-owner cross-reference",
            fail,
        )
    for field in ("python_bindings", "current_survivor_python_bindings"):
        for owner_id in closure[field]:
            _require_class(
                plan_index,
                owner_id,
                "current-integration-surface",
                f"{field} cross-reference",
                fail,
            )
    traceability = closure["traceability"]
    _require_class(
        plan_index,
        traceability["contract_map_owner_id"],
        "current-integration-surface",
        "traceability map cross-reference",
        fail,
    )
    clause_ids = traceability["clause_owner_ids"]
    clause_paths = traceability["clause_owner_paths"]
    if len(clause_ids) != len(clause_paths):
        fail("traceability clause owner IDs and paths differ in cardinality")
    for owner_id, expected_path in zip(clause_ids, clause_paths, strict=True):
        owner = _require_class(
            plan_index,
            owner_id,
            "current-integration-surface",
            "traceability clause-owner cross-reference",
            fail,
        )
        kind, actual_path = _locator(owner, owner_id, fail)
        if kind != "path" or actual_path != expected_path.replace(
            "{candidate_id}", candidate
        ):
            fail(f"{owner_id}: traceability clause-owner path is not exact")
    decision = closure["candidate_decision"]
    _require_class(
        plan_index,
        decision["decision_owner_id"],
        "candidate-decision-lifecycle",
        "candidate decision cross-reference",
        fail,
    )
    index_owner = _require_class(
        plan_index,
        decision["index_owner_id"],
        "current-narrative-owner",
        "candidate decision index cross-reference",
        fail,
    )
    index_kind, index_path = _locator(
        index_owner, decision["index_owner_id"], fail
    )
    if index_kind != "path" or index_path != decision["index_path"]:
        fail("candidate decision index owner path is not exact")


def validate_required_role_graph(
    manifest: dict[str, Any],
    plan: dict[str, Any],
    *,
    fail: Fail,
) -> None:
    """Require complete roles, artifact agreement, and exact cross-references."""
    roles = validate_required_roles_declaration(
        manifest["required_roles"],
        fail=fail,
    )
    candidate = plan["candidate"]["candidate_id"]
    manifest_index = _owners_by_id(manifest["owners"], "manifest", fail)
    plan_index = _owners_by_id(plan["owners"], "removal plan", fail)
    _validate_owner_relations(
        manifest_index,
        plan_index,
        candidate,
        fail,
    )
    _validate_required_owners(
        roles,
        manifest_index,
        plan_index,
        candidate,
        fail,
    )
    _validate_cross_references(plan, plan_index, candidate, fail)
