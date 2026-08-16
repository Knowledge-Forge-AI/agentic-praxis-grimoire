"""Code-owned semantic authority for generic candidate lifecycle roles.

The manifest and removal plan instantiate this registry; they do not define
what a required role means.  The registry is deliberately candidate-neutral
and permits additive roles only when they do not shadow a frozen semantic.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any, Callable, NoReturn


REGISTRY_SCHEMA_VERSION = 1
REGISTRY_PATH = "src/test/support/apg_candidate_required_role_registry.py"


@dataclass(frozen=True)
class SemanticRole:
    owner_id: str
    surface_class: str
    locator_kind: str
    generic_locator: str
    verification_family: str
    lifecycle_participation: str
    cardinality: str
    aliases: tuple[str, ...] = ()
    cross_reference_obligations: tuple[str, ...] = ()


def _role(
    owner_id: str,
    surface_class: str,
    locator_kind: str,
    generic_locator: str,
    verification_family: str,
    *,
    cardinality: str | None = None,
    cross_reference_obligations: tuple[str, ...] = (),
) -> SemanticRole:
    return SemanticRole(
        owner_id,
        surface_class,
        locator_kind,
        generic_locator,
        verification_family,
        surface_class,
        cardinality or ("exactly-one" if locator_kind == "path" else "declared-set"),
        (),
        cross_reference_obligations,
    )


ROLE_REGISTRY: tuple[SemanticRole, ...] = (
    _role("canonical-leaf", "current-integration-surface", "path", "skills/{candidate_id}/SKILL.md", "frontmatter", cross_reference_obligations=("closure_contracts.actual_lifecycle.authored_owner_ids",)),
    _role("candidate-fixture", "current-integration-surface", "path_pattern", "src/test/fixtures/**/*{candidate_id}*.json", "fixture", cardinality="candidate-set"),
    _role("candidate-specification", "current-integration-surface", "path", "docs/specs/{candidate_id}.md", "candidate-token", cross_reference_obligations=("closure_contracts.actual_lifecycle.authored_owner_ids",)),
    _role("candidate-contract-map", "current-integration-surface", "path", "docs/specs/{candidate_id}.contract-map.json", "contract-map", cross_reference_obligations=("closure_contracts.traceability.contract_map_owner_id", "closure_contracts.actual_lifecycle.authored_owner_ids")),
    _role("candidate-decision-record", "candidate-decision-lifecycle", "path", "docs/adr/2026/07/0036-{candidate_id}-from-frozen-contract.md", "decision", cross_reference_obligations=("closure_contracts.candidate_decision.decision_owner_id",)),
    _role("capability-map-entry", "current-integration-surface", "path", "skills/agentic-praxis-grimoire-workflow/references/capability-map.json", "capability"),
    _role("dynamic-global-installer-consumer", "current-integration-surface", "path", "libexec/install_global_skills.py", "dynamic"),
    _role("dynamic-skill-library-consumer", "current-integration-surface", "path", "libexec/apg_skill_library_check.py", "dynamic"),
    _role("dynamic-topology-consumer", "current-integration-surface", "path", "libexec/apg_skill_topology.py", "dynamic"),
    _role("focused-integration-test", "current-integration-surface", "path_pattern", "src/test/int/**/*{candidate_id}*.test.py", "test", cardinality="candidate-set"),
    _role("focused-unit-test", "current-integration-surface", "path_pattern", "src/test/unit/**/*{candidate_id}*.test.py", "test", cardinality="candidate-set"),
    _role("project-expected-skills", "current-integration-surface", "path", "libexec/apg_project_skills_core.py", "assignment", cross_reference_obligations=("closure_contracts.python_bindings.project-expected-skills", "closure_contracts.current_survivor_python_bindings.project-expected-skills")),
    _role("project-integration-mirror", "current-integration-surface", "path", "src/test/int/python/agentic-praxis-grimoire/libexec/apg_project_skills_core.int.test.py", "assignment"),
    _role("project-command-integration-mirror", "current-integration-surface", "path", "src/test/int/python/agentic-praxis-grimoire/bin/apg-project-skills.int.test.py", "assignment"),
    _role("project-unit-mirror", "current-integration-surface", "path", "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_project_skills_core.unit.test.py", "assignment"),
    _role("projection", "current-integration-surface", "path", ".agents/skills/{candidate_id}", "projection"),
    _role("release-helper-audited-critical", "current-integration-surface", "path", "libexec/apg_public_release.py", "assignment", cross_reference_obligations=("closure_contracts.python_bindings.release-helper-audited-critical", "closure_contracts.current_survivor_python_bindings.release-helper-audited-critical")),
    _role("release-helper-audited-projections", "current-integration-surface", "path", "libexec/apg_public_release.py", "assignment", cross_reference_obligations=("closure_contracts.python_bindings.release-helper-audited-projections", "closure_contracts.current_survivor_python_bindings.release-helper-audited-projections")),
    _role("release-helper-audited-skills", "current-integration-surface", "path", "libexec/apg_public_release.py", "assignment", cross_reference_obligations=("closure_contracts.python_bindings.release-helper-audited-skills", "closure_contracts.current_survivor_python_bindings.release-helper-audited-skills")),
    _role("release-helper-audited-tests", "current-integration-surface", "path", "libexec/apg_public_release.py", "assignment", cross_reference_obligations=("closure_contracts.python_bindings.release-helper-audited-tests", "closure_contracts.current_survivor_python_bindings.release-helper-audited-tests")),
    _role("release-integration-mirror", "current-integration-surface", "path", "src/test/int/python/agentic-praxis-grimoire/libexec/apg_public_release.int.test.py", "assignment"),
    _role("release-shared-case-mirror", "current-integration-surface", "path", "src/test/apg_public_release_cases.py", "assignment"),
    _role("release-policy-critical-files", "current-integration-surface", "path", "release/public-surface.json", "membership"),
    _role("release-policy-required-projections", "current-integration-surface", "path", "release/public-surface.json", "membership"),
    _role("release-policy-required-skills", "current-integration-surface", "path", "release/public-surface.json", "membership"),
    _role("release-policy-required-tests", "current-integration-surface", "path", "release/public-surface.json", "membership"),
    _role("release-unit-mirror", "current-integration-surface", "path", "src/test/unit/python/agentic-praxis-grimoire/libexec/apg_public_release.unit.test.py", "assignment"),
    _role("router-consumer", "current-integration-surface", "path", "skills/agentic-praxis-grimoire-workflow/SKILL.md", "router"),
    _role("skill-catalog-row", "current-integration-surface", "path", "skills/README.md", "catalog"),
    _role("skill-maturity-row", "current-integration-surface", "path", "skills/README.md", "catalog"),
    _role("test-inventory-entry", "current-integration-surface", "path", "testing/apg-test-inventory.json", "inventory"),
    _role("narrative-agents", "current-narrative-owner", "path", "AGENTS.md", "narrative"),
    _role("narrative-readme", "current-narrative-owner", "path", "README.md", "narrative"),
    _role("narrative-adr-index", "current-narrative-owner", "path", "docs/adr/README.md", "narrative", cross_reference_obligations=("closure_contracts.candidate_decision.index_owner_id",)),
    _role("narrative-provenance", "current-narrative-owner", "path", "docs/provenance.md", "narrative"),
    _role("narrative-project-model", "current-narrative-owner", "path", "docs/project-model.md", "narrative"),
    _role("narrative-project-skill-projection", "current-narrative-owner", "path", "docs/project-skill-projection.md", "narrative"),
    _role("narrative-public-release-process", "current-narrative-owner", "path", "docs/public-release-process.md", "narrative"),
    _role("narrative-roadmap", "current-narrative-owner", "path", "docs/roadmap.md", "narrative"),
    _role("narrative-skill-maintenance", "current-narrative-owner", "path", "docs/skill-authoring-and-maintenance.md", "narrative"),
    _role("narrative-status-index", "current-narrative-owner", "path", "docs/status/README.md", "narrative"),
    _role("narrative-v0-5-roadmap", "current-narrative-owner", "path", "docs/v0-5-roadmap.md", "narrative"),
    _role("history-candidate-adr", "historical-evidence", "path_pattern", "docs/adr/**/*{candidate_id}*.md", "history", cardinality="historical-set"),
    _role("history-candidate-evaluations", "historical-evidence", "path_pattern", "docs/evaluations/{candidate_phase_slug}.md", "history", cardinality="historical-set"),
    _role("history-candidate-exits", "historical-evidence", "path_pattern", "docs/status/**/{candidate_exit_slug}.md", "history", cardinality="historical-set"),
    _role("history-git-objects", "historical-evidence", "path_pattern", "git-object:{candidate_phase_id}", "history", cardinality="historical-set"),
    _role("history-predecessor-fact-check", "historical-evidence", "path", "docs/evaluations/apg45-fact-check-peer-review-and-roadmap-disposition.md", "history"),
    _role("history-predecessor-public-evidence", "historical-evidence", "path_pattern", "docs/**/*{candidate_family_token}*.md", "history", cardinality="historical-set"),
    _role("history-provenance-sections", "historical-evidence", "path", "docs/provenance.md", "history"),
    _role("private-candidate-phase-evidence", "publication-excluded-history", "path_pattern", "private/evaluations/{candidate_phase_id}/**", "history", cardinality="historical-set"),
    _role("private-predecessor-evidence", "publication-excluded-history", "path_pattern", "private/evaluations/{predecessor_phase_id}/**", "history", cardinality="historical-set"),
    _role("managed-candidate-reports", "managed-report", "path_pattern", "managed-report:{candidate_phase_id}", "report", cardinality="historical-set"),
)

ROLE_BY_ID = {role.owner_id: role for role in ROLE_REGISTRY}
REQUIRED_ROLE_IDS = frozenset(ROLE_BY_ID)

CROSS_REFERENCE_VALUES: dict[str, dict[str, object]] = {
    "canonical-leaf": {
        "closure_contracts.actual_lifecycle.authored_owner_ids": [
            "canonical-leaf",
            "candidate-contract-map",
            "candidate-specification",
        ],
    },
    "candidate-specification": {
        "closure_contracts.actual_lifecycle.authored_owner_ids": [
            "canonical-leaf",
            "candidate-contract-map",
            "candidate-specification",
        ],
    },
    "candidate-contract-map": {
        "closure_contracts.traceability.contract_map_owner_id": "candidate-contract-map",
        "closure_contracts.actual_lifecycle.authored_owner_ids": [
            "canonical-leaf",
            "candidate-contract-map",
            "candidate-specification",
        ],
    },
    "candidate-decision-record": {
        "closure_contracts.candidate_decision.decision_owner_id": "candidate-decision-record",
    },
    "narrative-adr-index": {
        "closure_contracts.candidate_decision.index_owner_id": "narrative-adr-index",
    },
}
for owner_id, variable in {
    "project-expected-skills": "EXPECTED_SKILLS",
    "release-helper-audited-critical": "AUDITED_CRITICAL",
    "release-helper-audited-projections": "AUDITED_PROJECTIONS",
    "release-helper-audited-skills": "AUDITED_SKILLS",
    "release-helper-audited-tests": "AUDITED_TESTS",
}.items():
    CROSS_REFERENCE_VALUES[owner_id] = {
        f"closure_contracts.python_bindings.{owner_id}": variable,
        f"closure_contracts.current_survivor_python_bindings.{owner_id}": variable,
    }


def _fail(message: str, fail: Callable[[str], NoReturn]) -> NoReturn:
    fail(message)
    raise AssertionError("unreachable")


def _locator(owner: dict[str, Any], owner_id: str, fail: Callable[[str], NoReturn]) -> tuple[str, str]:
    kinds = {kind for kind in ("path", "path_pattern") if kind in owner}
    if len(kinds) != 1:
        _fail(f"{owner_id}: role locator is ambiguous", fail)
    kind = next(iter(kinds))
    value = owner[kind]
    if not isinstance(value, str):
        _fail(f"{owner_id}: role locator is invalid", fail)
    return kind, value


def _render_locator(generic: str, candidate: str) -> str:
    rendered = generic.replace("{candidate_id}", candidate)
    return re.sub(r"\{[a-z][a-z0-9_]*\}", "*", rendered)


def _historical_locator_family(owner_id: str, candidate: str) -> str | None:
    """Return the frozen historical family for placeholder-based owners."""

    return {
        "history-candidate-adr": (
            f"docs/adr/2026/07/0035-{candidate}-and-policy-selected-structural-limits.md"
        ),
        "history-candidate-evaluations": (
            f"docs/evaluations/apg5[89]-{candidate}-*.md"
        ),
        "history-candidate-exits": (
            f"docs/status/2026/07/29/0007[89]-apg5[89]-{candidate}-*.md"
        ),
        "history-git-objects": "git-object:APG5[89]",
        "history-predecessor-public-evidence": "docs/**/*web*node*.md",
        "private-candidate-phase-evidence": "private/evaluations/apg5[89]/**",
        "private-predecessor-evidence": "private/evaluations/apg*/**",
        "managed-candidate-reports": "managed-report:APG5[89]",
    }.get(owner_id)


def _expected_plan_locator(role: SemanticRole, candidate: str) -> str:
    historical = _historical_locator_family(role.owner_id, candidate)
    if historical is not None:
        return historical
    return _render_locator(role.generic_locator, candidate)


def _nested_value(value: dict[str, Any], dotted: str) -> Any:
    current: Any = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _role_maps(
    manifest: dict[str, Any],
    plan: dict[str, Any],
    fail: Callable[[str], NoReturn],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    declaration = manifest.get("required_roles")
    if not isinstance(declaration, dict) or declaration.get("schema_version") != 2:
        _fail("required role registry schema version is invalid", fail)
    if declaration.get("registry") != REGISTRY_PATH:
        _fail("required role registry path is not exact", fail)
    roles = declaration.get("roles")
    if not isinstance(roles, list):
        _fail("required role registry declaration is invalid", fail)
    declared: dict[str, dict[str, Any]] = {}
    for role in roles:
        if not isinstance(role, dict) or not isinstance(role.get("owner_id"), str):
            _fail("required role registry declaration is invalid", fail)
        owner_id = role["owner_id"]
        if owner_id in declared:
            _fail("required role registry IDs are incomplete or duplicated", fail)
        declared[owner_id] = role
    if set(declared) != REQUIRED_ROLE_IDS:
        _fail("required role registry IDs are incomplete or duplicated", fail)
    manifest_owners = {
        owner["owner_id"]: owner
        for owner in manifest.get("owners", [])
        if isinstance(owner, dict) and isinstance(owner.get("owner_id"), str)
    }
    plan_owners = {
        owner["owner_id"]: owner
        for owner in plan.get("owners", [])
        if isinstance(owner, dict) and isinstance(owner.get("owner_id"), str)
    }
    return declared, manifest_owners, plan_owners


def _validate_declared_role(
    role: SemanticRole,
    declared: dict[str, Any],
    fail: Callable[[str], NoReturn],
) -> None:
    for field, expected in (
        ("owner_id", role.owner_id),
        ("surface_class", role.surface_class),
        ("locator_kind", role.locator_kind),
        ("generic_locator", role.generic_locator),
    ):
        if declared.get(field) != expected:
            _fail(f"{role.owner_id}: frozen semantic role {field} changed", fail)


def _validate_role_owners(
    role: SemanticRole,
    manifest_owner: dict[str, Any] | None,
    plan_owner: dict[str, Any] | None,
    candidate: str,
    fail: Callable[[str], NoReturn],
) -> None:
    if manifest_owner is None or plan_owner is None:
        _fail(f"{role.owner_id}: required role owner is missing", fail)
    manifest_kind, manifest_locator = _locator(manifest_owner, role.owner_id, fail)
    plan_kind, plan_locator = _locator(plan_owner, role.owner_id, fail)
    if (
        manifest_owner.get("surface_class") != role.surface_class
        or manifest_kind != role.locator_kind
        or manifest_locator != role.generic_locator
    ):
        _fail(f"{role.owner_id}: manifest does not reproduce frozen semantics", fail)
    expected = _expected_plan_locator(role, candidate)
    if (
        plan_owner.get("surface_class") != role.surface_class
        or plan_kind
        not in {
            role.locator_kind,
            "path" if role.locator_kind == "path_pattern" else role.locator_kind,
        }
        or plan_locator != expected
    ):
        _fail(f"{role.owner_id}: removal plan does not instantiate frozen semantics", fail)


def _validate_role_metadata(
    role: SemanticRole,
    manifest_owner: dict[str, Any],
    plan: dict[str, Any],
    fail: Callable[[str], NoReturn],
) -> None:
    if manifest_owner.get("verification_family") != role.verification_family:
        _fail(f"{role.owner_id}: verification family is not frozen", fail)
    method = manifest_owner.get("verification_method")
    prefix = f"family:{role.verification_family}| "
    if not isinstance(method, str) or not method.startswith(prefix):
        _fail(f"{role.owner_id}: verification family is not frozen", fail)
    if role.cardinality == "exactly-one" and role.locator_kind != "path":
        _fail(f"{role.owner_id}: cardinality is inconsistent with locator", fail)
    if role.aliases:
        _fail(f"{role.owner_id}: aliases are not permitted for required roles", fail)
    for obligation in role.cross_reference_obligations:
        expected = CROSS_REFERENCE_VALUES.get(role.owner_id, {}).get(obligation)
        if expected is None or _nested_value(plan, obligation) != expected:
            _fail(f"{role.owner_id}: cross-reference obligation changed", fail)


def _validate_manifest_semantics(
    manifest: dict[str, Any],
    fail: Callable[[str], NoReturn],
) -> None:
    actual = Counter()
    for owner in manifest.get("owners", []):
        if not isinstance(owner, dict) or not isinstance(owner.get("owner_id"), str):
            _fail("required role semantic owner is invalid", fail)
        actual[(owner.get("surface_class"), *_locator(owner, owner["owner_id"], fail))] += 1
    frozen = Counter(
        (role.surface_class, role.locator_kind, role.generic_locator)
        for role in ROLE_REGISTRY
    )
    if any(actual[semantic] != count for semantic, count in frozen.items()):
        _fail("required role semantic is missing, duplicated, or redirected", fail)


def validate_required_role_registry(
    manifest: dict[str, Any], plan: dict[str, Any], *, fail: Callable[[str], NoReturn]
) -> None:
    """Validate co-mutable artifacts against code-owned role semantics."""
    declared, manifest_owners, plan_owners = _role_maps(manifest, plan, fail)
    candidate = plan.get("candidate", {}).get("candidate_id", "")
    if not isinstance(candidate, str):
        _fail("candidate identity is invalid", fail)
    for role in ROLE_REGISTRY:
        manifest_owner = manifest_owners.get(role.owner_id)
        _validate_declared_role(role, declared[role.owner_id], fail)
        _validate_role_owners(
            role, manifest_owner, plan_owners.get(role.owner_id), candidate, fail
        )
        if manifest_owner is not None:
            _validate_role_metadata(role, manifest_owner, plan, fail)
    _validate_manifest_semantics(manifest, fail)
