"""Actual-tree retained candidate-surface closure; integration shape only."""

from __future__ import annotations

import ast
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any, NoReturn, Sequence

from apg_candidate_decision_contract import assert_candidate_decision
from apg_candidate_narrative_state_contract import assert_narrative_state
from apg_pinned_root_contract import pinned_repository_root
from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)
from apg_candidate_surface_contract import (
    PYTHON_BINDINGS,
    SurfaceContractError,
    derive_skill_surface_counts,
    validate_candidate_surface_contract,
)
from apg_candidate_traceability_contract import assert_contract_map
from apg_live_owner_binding_contract import (
    assert_audited_assignment,
    assert_bound_assignment,
)
from apg_repository_import_contract import (
    RepositoryImportError,
    execute_repository_consumer,
)
from apg_skill_set_contract import (
    SkillSetError,
    canonical_skill_names,
    require_exact_skill_names,
)


CURRENT_CLASSES = {"current-integration-surface", "current-narrative-owner"}
DEFAULT_PYTHON_BINDINGS = PYTHON_BINDINGS


def fail(owner_id: str, message: str) -> NoReturn:
    raise SurfaceContractError(f"{owner_id}: {message}")


def _paths(root: Path, owner: dict[str, Any]) -> list[Path]:
    locator = owner.get("path", owner.get("path_pattern"))
    if locator.startswith(("git-object:", "managed-report:")):
        return []
    try:
        with RepositoryPathContract(root) as repository:
            if "path_pattern" in owner:
                return [
                    root / relative
                    for relative in repository.glob_regular_files(locator)
                ]
            kind = repository.entry_kind(locator)
    except RepositoryPathError as error:
        fail(owner["owner_id"], f"repository path ancestor is not direct: {error}")
    return [root / locator] if kind is not None else []


def _regular_text(root: Path, path: Path, owner_id: str) -> str:
    try:
        relative = path.relative_to(root).as_posix()
        with RepositoryPathContract(root) as repository:
            return repository.read_text(relative)
    except (OSError, UnicodeError, ValueError, RepositoryPathError) as error:
        fail(owner_id, f"owner is unreadable: {error}")


def _json_object(root: Path, path: Path, owner_id: str) -> dict[str, Any]:
    text = _regular_text(root, path, owner_id)

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                fail(owner_id, f"JSON owner has duplicate key: {key}")
            value[key] = item
        return value

    try:
        value = json.loads(text, object_pairs_hook=strict_object)
    except json.JSONDecodeError as error:
        fail(owner_id, f"JSON owner is invalid: {error}")
    if not isinstance(value, dict):
        fail(owner_id, "JSON owner must be an object")
    return value


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [
            string
            for key, item in value.items()
            for string in (*_strings(key), *_strings(item))
        ]
    if isinstance(value, (list, tuple, set, frozenset)):
        return [string for item in value for string in _strings(item)]
    return []


def _candidate_counter(values: Sequence[str], candidate: str) -> Counter[str]:
    return Counter(value for value in values if candidate in value)


def _require_json_membership(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    field: str,
    expected: Sequence[str],
) -> None:
    owner_id = owner["owner_id"]
    paths = _paths(root, owner)
    if len(paths) != 1:
        fail(owner_id, "JSON owner is missing or duplicated")
    value = _json_object(root, paths[0], owner_id)
    if field not in value or _candidate_counter(
        _strings(value[field]), candidate
    ) != Counter(expected):
        fail(owner_id, f"{field} candidate membership is incomplete or duplicated")


def _assert_projection(
    root: Path, owner: dict[str, Any], candidate: str
) -> None:
    owner_id = owner["owner_id"]
    expected = f"../../skills/{candidate}"
    try:
        with RepositoryPathContract(root) as repository:
            repository.assert_projection(
                owner["path"],
                expected,
                f"skills/{candidate}/SKILL.md",
            )
    except RepositoryPathError as error:
        fail(owner_id, f"candidate projection is invalid: {error}")


def _assert_leaf(root: Path, owner: dict[str, Any], candidate: str) -> None:
    owner_id = owner["owner_id"]
    paths = _paths(root, owner)
    if len(paths) != 1:
        fail(owner_id, "canonical leaf is missing or duplicated")
    text = _regular_text(root, paths[0], owner_id)
    if f"name: {candidate}" not in text:
        fail(owner_id, "frontmatter name does not identify candidate")


def _assert_candidate_files(
    root: Path, owner: dict[str, Any], candidate: str
) -> None:
    owner_id = owner["owner_id"]
    paths = _paths(root, owner)
    if not paths:
        fail(owner_id, "candidate file set is empty")
    for path in paths:
        text = _regular_text(root, path, owner_id)
        if path.suffix == ".json":
            _json_object(root, path, owner_id)
        elif path.suffix == ".py":
            try:
                ast.parse(text)
            except SyntaxError as error:
                fail(owner_id, f"Python owner is invalid: {error}")
        if candidate not in text:
            fail(owner_id, "candidate file does not identify candidate")


def _assert_contract_map(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    config: dict[str, Any] | None = None,
) -> None:
    if config is None:
        fail(owner["owner_id"], "candidate contract map lacks closure metadata")
    assert_contract_map(root, owner, candidate, config)


def _assert_capability_map(
    root: Path, owner: dict[str, Any], candidate: str
) -> None:
    owner_id = owner["owner_id"]
    paths = _paths(root, owner)
    if len(paths) != 1:
        fail(owner_id, "capability map is missing or duplicated")
    value = _json_object(root, paths[0], owner_id)
    capabilities = value.get("capabilities")
    if not isinstance(capabilities, list):
        fail(owner_id, "capabilities must be an array")
    names = [
        item.get("name")
        for item in capabilities
        if isinstance(item, dict)
    ]
    if names.count(candidate) != 1:
        fail(owner_id, "candidate capability must occur exactly once")


def _catalog_rows(root: Path, owner: dict[str, Any], candidate: str) -> list[str]:
    owner_id = owner["owner_id"]
    paths = _paths(root, owner)
    if len(paths) != 1:
        fail(owner_id, "skill catalog is missing or duplicated")
    return [
        line
        for line in _regular_text(root, paths[0], owner_id).splitlines()
        if line.startswith("| [`") and f"`{candidate}`" in line
    ]


def _assert_catalog(root: Path, owner: dict[str, Any], candidate: str) -> None:
    rows = _catalog_rows(root, owner, candidate)
    if len(rows) != 1 or f"({candidate}/SKILL.md)" not in rows[0]:
        fail(owner["owner_id"], "candidate catalog row is missing or duplicated")


def _assert_maturity(root: Path, owner: dict[str, Any], candidate: str) -> None:
    rows = _catalog_rows(root, owner, candidate)
    if len(rows) != 1 or not any(
        f"| {state} |" in rows[0] for state in ("stable", "provisional")
    ):
        fail(owner["owner_id"], "candidate maturity state is invalid")


def _retained_narrative_state(
    root: Path, owners: list[dict[str, Any]], candidate: str
) -> str:
    owner = next(
        item for item in owners if item["owner_id"] == "skill-maturity-row"
    )
    rows = _catalog_rows(root, owner, candidate)
    if len(rows) != 1:
        fail(owner["owner_id"], "candidate maturity row is missing")
    for maturity in ("stable", "provisional"):
        if f"| {maturity} |" in rows[0]:
            return f"retained-{maturity}"
    fail(owner["owner_id"], "candidate maturity state is invalid")


def _assert_dynamic_owner(
    root: Path, owner: dict[str, Any], candidate: str
) -> None:
    owner_id = owner["owner_id"]
    paths = _paths(root, owner)
    if len(paths) != 1:
        fail(owner_id, "dynamic consumer is missing or duplicated")
    text = _regular_text(root, paths[0], owner_id)
    if paths[0].suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError as error:
            fail(owner_id, f"Python owner is invalid: {error}")
        operational_nodes = (
            ast.Assign,
            ast.AnnAssign,
            ast.ClassDef,
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.Import,
            ast.ImportFrom,
        )
        if not any(isinstance(node, operational_nodes) for node in tree.body):
            fail(owner_id, "dynamic Python consumer has no operational shape")
    elif not any(line.startswith("## ") for line in text.splitlines()):
        fail(owner_id, "router consumer has no operational section")
    if candidate in text:
        fail(owner_id, "dynamic consumer hard-codes candidate state")


def _assert_narrative(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    expected_state: str = "retained-provisional",
) -> None:
    assert_narrative_state(root, owner, candidate, expected_state)


def _assert_historical_public(
    root: Path, owners: list[dict[str, Any]]
) -> None:
    for owner in owners:
        if owner["surface_class"] != "historical-evidence":
            continue
        locator = owner.get("path", owner.get("path_pattern"))
        if locator.startswith("git-object:"):
            continue
        paths = _paths(root, owner)
        if not paths or any(not path.exists() for path in paths):
            fail(owner["owner_id"], "public historical evidence is missing")


def _surface_expectations(
    root: Path, owners: list[dict[str, Any]], candidate: str
) -> dict[str, list[str]]:
    by_id = {owner["owner_id"]: owner for owner in owners}

    def relative_paths(owner_id: str) -> list[str]:
        return [
            path.relative_to(root).as_posix()
            for path in _paths(root, by_id[owner_id])
        ]

    leaf = relative_paths("canonical-leaf")
    projection = relative_paths("projection")
    specification = relative_paths("candidate-specification")
    contract_map = relative_paths("candidate-contract-map")
    fixtures = relative_paths("candidate-fixture")
    unit_tests = relative_paths("focused-unit-test")
    integration_tests = relative_paths("focused-integration-test")
    return {
        "candidate": [candidate],
        "skills": leaf,
        "projections": projection,
        "critical": specification + contract_map + fixtures,
        "unit_tests": unit_tests,
        "integration_tests": integration_tests,
        "tests": unit_tests + integration_tests,
        "release": (
            leaf
            + projection
            + specification
            + contract_map
            + fixtures
            + unit_tests
            + integration_tests
        ),
    }


def _assert_direct_owner(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    closure: dict[str, Any],
) -> bool:
    owner_id = owner["owner_id"]
    if owner_id == "canonical-leaf":
        _assert_leaf(root, owner, candidate)
    elif owner_id == "candidate-contract-map":
        _assert_contract_map(
            root, owner, candidate, closure["traceability"]
        )
    elif owner_id in {
        "candidate-fixture",
        "candidate-specification",
        "focused-integration-test",
        "focused-unit-test",
    }:
        _assert_candidate_files(root, owner, candidate)
    elif owner_id == "projection":
        _assert_projection(root, owner, candidate)
    elif owner_id == "capability-map-entry":
        _assert_capability_map(root, owner, candidate)
    elif owner_id.startswith("dynamic-") or owner_id == "router-consumer":
        _assert_dynamic_owner(root, owner, candidate)
    else:
        return False
    return True


def _assert_project_owner(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    expected: dict[str, list[str]],
    bindings: dict[str, str] = DEFAULT_PYTHON_BINDINGS,
) -> bool:
    owner_id = owner["owner_id"]
    if owner_id.startswith("project-"):
        path = _paths(root, owner)[0]
        assert_bound_assignment(
            root,
            owner,
            candidate,
            expected["candidate"],
            bindings[owner_id],
            source_text=_regular_text(root, path, owner_id),
        )
    else:
        return False
    return True


def _assert_release_helper(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    expected: dict[str, list[str]],
    bindings: dict[str, str] = DEFAULT_PYTHON_BINDINGS,
) -> bool:
    owner_id = owner["owner_id"]
    if not owner_id.startswith("release-helper-audited-"):
        return False
    variable = bindings[owner_id]
    expectation = expected[variable.removeprefix("AUDITED_").lower()]
    path = _paths(root, owner)[0]
    assert_audited_assignment(
        root,
        owner,
        candidate,
        expectation,
        variable,
        source_text=_regular_text(root, path, owner_id),
    )
    return True


def _assert_release_or_registry_owner(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    expected: dict[str, list[str]],
    bindings: dict[str, str] = DEFAULT_PYTHON_BINDINGS,
) -> bool:
    owner_id = owner["owner_id"]
    if owner_id.startswith("release-policy-"):
        field = owner_id.removeprefix("release-policy-").replace("-", "_")
        if field == "required_tests":
            field = "required_test_entrypoints"
        expectation_key = (
            owner_id.removeprefix("release-policy-")
            .removeprefix("required-")
            .replace("-files", "")
        )
        _require_json_membership(
            root, owner, candidate, field, expected[expectation_key]
        )
    elif owner_id.startswith("release-"):
        path = _paths(root, owner)[0]
        assert_bound_assignment(
            root,
            owner,
            candidate,
            expected["release"],
            bindings[owner_id],
            source_text=_regular_text(root, path, owner_id),
        )
    elif owner_id == "skill-catalog-row":
        _assert_catalog(root, owner, candidate)
    elif owner_id == "skill-maturity-row":
        _assert_maturity(root, owner, candidate)
    elif owner_id == "test-inventory-entry":
        paths = _paths(root, owner)
        if len(paths) != 1:
            fail(owner_id, "test inventory is missing or duplicated")
        tests = _json_object(root, paths[0], owner_id).get("tests")
        candidate_records = [
            item
            for item in tests if isinstance(item, dict) and _candidate_counter(
                _strings(item), candidate
            )
        ] if isinstance(tests, list) else []
        expected_records = [
            {"owner": expected["skills"][0], "path": path, "suite": suite}
            for suite, paths_for_suite in (
                ("unit", expected["unit_tests"]),
                ("integration", expected["integration_tests"]),
            )
            for path in paths_for_suite
        ] if len(expected["skills"]) == 1 else []
        if Counter(
            json.dumps(item, sort_keys=True) for item in candidate_records
        ) != Counter(json.dumps(item, sort_keys=True) for item in expected_records):
            fail(owner_id, "candidate test inventory is incomplete or duplicated")
    else:
        return False
    return True


def _assert_integration_owner(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    expected: dict[str, list[str]],
    closure: dict[str, Any],
) -> None:
    if _assert_direct_owner(root, owner, candidate, closure):
        return
    for handler in (
        _assert_project_owner,
        _assert_release_helper,
        _assert_release_or_registry_owner,
    ):
        if handler(
            root,
            owner,
            candidate,
            expected,
            closure["python_bindings"],
        ):
            return
    fail(owner["owner_id"], "current integration verification is undefined")


def _execute_repository_consumer(
    root: Path,
    path: Path,
    owner_id: str,
    operation: str,
) -> dict[str, Any]:
    try:
        relative = path.relative_to(root).as_posix()
        return execute_repository_consumer(root, relative, operation)
    except (OSError, ValueError, RepositoryImportError) as error:
        fail(owner_id, f"closed dynamic consumer execution failed: {error}")


def _assert_live_topology(
    root: Path,
    by_id: dict[str, dict[str, Any]],
    candidate: str,
    expected_names: tuple[str, ...],
) -> None:
    topology_id = "dynamic-topology-consumer"
    topology_path = _paths(root, by_id[topology_id])[0]
    result = _execute_repository_consumer(
        root,
        topology_path,
        topology_id,
        "topology",
    )
    names = result["names"]
    try:
        require_exact_skill_names(
            names,
            expected_names,
            consumer=topology_id,
        )
    except SkillSetError as error:
        fail(topology_id, str(error))
    if result["diagnostics"] or names.count(candidate) != 1:
        fail(topology_id, "live topology does not derive retained state")


def _assert_live_library(
    root: Path,
    by_id: dict[str, dict[str, Any]],
    counts: tuple[int, int, int],
    expected_names: tuple[str, ...],
) -> None:
    library_id = "dynamic-skill-library-consumer"
    result = _execute_repository_consumer(
        root,
        _paths(root, by_id[library_id])[0],
        library_id,
        "library",
    )
    result_counts = (
        result["canonical_skills"],
        result["catalog_rows"],
        result["projections"],
    )
    if not result["passed"] or result_counts != counts:
        fail(library_id, "live library check does not derive retained state")
    try:
        require_exact_skill_names(
            result["names"],
            expected_names,
            consumer=library_id,
        )
    except SkillSetError as error:
        fail(library_id, str(error))


def _assert_live_installer(
    root: Path,
    by_id: dict[str, dict[str, Any]],
    candidate: str,
    expected_names: tuple[str, ...],
) -> None:
    installer_id = "dynamic-global-installer-consumer"
    result = _execute_repository_consumer(
        root,
        _paths(root, by_id[installer_id])[0],
        installer_id,
        "installer",
    )
    inventory_names = result["names"]
    try:
        require_exact_skill_names(
            inventory_names,
            expected_names,
            consumer=installer_id,
        )
    except SkillSetError as error:
        fail(installer_id, str(error))
    if inventory_names.count(candidate) != 1:
        fail(installer_id, "live installer does not derive retained state")


def _assert_live_router(
    root: Path, by_id: dict[str, dict[str, Any]]
) -> None:
    router_id = "router-consumer"
    router_text = _regular_text(
        root, _paths(root, by_id[router_id])[0], router_id
    )
    if "references/capability-map.json" not in router_text:
        fail(router_id, "router does not consume the live capability map")


def _assert_live_dynamic_consumers(
    root: Path,
    owners: list[dict[str, Any]],
    candidate: str,
    counts: tuple[int, int, int],
) -> None:
    by_id = {owner["owner_id"]: owner for owner in owners}
    expected_names = canonical_skill_names(root)
    if len(expected_names) != counts[0]:
        fail(
            "dynamic-skill-set-contract",
            "canonical owner names and surface count disagree",
        )
    _assert_live_topology(root, by_id, candidate, expected_names)
    _assert_live_library(root, by_id, counts, expected_names)
    _assert_live_installer(root, by_id, candidate, expected_names)
    _assert_live_router(root, by_id)


@pinned_repository_root
def assert_actual_retained_surface_present(
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    candidate: str,
    expected_state: str | None = None,
) -> None:
    """Require complete actual integration ownership, not candidate prose quality."""
    validate_candidate_surface_contract(manifest, plan)
    if candidate != plan["candidate"]["candidate_id"]:
        raise SurfaceContractError("candidate does not match the removal plan")
    owners = plan["owners"]
    closure = plan["closure_contracts"]
    expected = _surface_expectations(root, owners, candidate)
    for owner in owners:
        if owner["surface_class"] == "current-integration-surface":
            _assert_integration_owner(
                root, owner, candidate, expected, closure
            )
    narrative_state = _retained_narrative_state(root, owners, candidate)
    if expected_state is not None and narrative_state != expected_state:
        raise SurfaceContractError(
            "candidate maturity row disagrees with required retained state"
        )
    for owner in owners:
        owner_class = owner["surface_class"]
        if owner_class == "current-narrative-owner":
            _assert_narrative(
                root, owner, candidate, narrative_state
            )
        elif owner_class == "candidate-decision-lifecycle":
            assert_candidate_decision(
                root,
                owner,
                candidate,
                closure["candidate_decision"],
                "retained",
            )
    _assert_historical_public(root, owners)
    canonical, catalog, projections = derive_skill_surface_counts(root)
    if canonical != catalog or canonical != projections:
        raise SurfaceContractError(
            "dynamic live inventories disagree for retained candidate closure"
        )
    _assert_live_dynamic_consumers(
        root,
        owners,
        candidate,
        (canonical, catalog, projections),
    )
