"""Generic candidate-surface schema and synthetic lifecycle test support."""

from __future__ import annotations

import ast
import fnmatch
import json
from pathlib import Path
import re
from typing import Any, NoReturn

from apg_candidate_lifecycle_schema_contract import (
    AUTHORITATIVE_REGULAR_FILE_READ,
    validate_manifest_lifecycle_schema,
    validate_actual_lifecycle_schema,
    validate_narrative_schema,
    validate_python_source_binding_schema,
)
from apg_candidate_foundation_contract import (
    validate_foundation_closure_contracts,
)
from apg_candidate_required_roles_contract import (
    CURRENT_SURVIVOR_PYTHON_BINDINGS,
    PYTHON_BINDINGS,
    validate_required_role_graph,
    validate_required_role_registry,
    validate_required_roles_declaration,
)
from apg_pinned_root_contract import pinned_repository_root
from apg_repository_path_contract import (
    RepositoryPathContract,
    RepositoryPathError,
)


class SurfaceContractError(ValueError):
    """A candidate-surface schema or lifecycle closure failure."""


MANIFEST_KEYS = {
    "artifact",
    "lifecycle_contracts",
    "lifecycle_labels",
    "owner_schema",
    "owners",
    "required_roles",
    "schema_version",
}
MANIFEST_OWNER_FIELDS = {
    "historical_preservation_rule",
    "owner_id",
    "present_state_obligation",
    "rejected_removal_obligation",
    "surface_class",
    "verification_family",
    "verification_method",
}
PLAN_KEYS = {
    "actions",
    "artifact",
    "candidate",
    "closure_contracts",
    "contract_foundation_exclusions",
    "owners",
    "schema_version",
    "source_contract_sha256",
}
PLAN_OWNER_FIELDS = {
    "actions",
    "owner_id",
    "rejected_stale_test",
    "retained_omission_test",
    "surface_class",
}
OWNER_CLASSES = {
    "current-integration-surface",
    "current-narrative-owner",
    "candidate-decision-lifecycle",
    "historical-evidence",
    "publication-excluded-history",
    "managed-report",
}
LIFECYCLE_ACTIONS = {
    "delete",
    "preserve-historical",
    "remove-entry",
    "rewrite-current-summary",
    "verify-absent",
    "verify-survivors",
}
CURRENT_CLASSES = {"current-integration-surface", "current-narrative-owner"}
LIFECYCLE_CLASSES = CURRENT_CLASSES | {"candidate-decision-lifecycle"}
LOCATORS = {"path", "path_pattern"}


def fail(message: str) -> NoReturn:
    raise SurfaceContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _read_json(path: Path, root: Path) -> dict[str, Any]:
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
        fail(f"candidate-surface JSON is unreadable: {error}")
    if not isinstance(value, dict):
        fail("candidate-surface JSON must be an object")
    return value


def _exact_keys(value: Any, expected: set[str], context: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        fail(f"{context} schema has unknown or missing keys")


def _locator(owner: dict[str, Any], required: set[str], context: str) -> tuple[str, str]:
    locators = LOCATORS & set(owner)
    if len(locators) != 1 or set(owner) != required | locators:
        fail(f"{context} must have closed schema and exactly one locator")
    locator = next(iter(locators))
    value = owner[locator]
    if not isinstance(value, str) or not value or value.startswith("/"):
        fail(f"{context} locator must be a nonempty non-absolute string")
    return locator, value


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{context} must be a nonempty string")
    return value


def _validate_manifest_owner(owner: Any, index: int) -> None:
    if not isinstance(owner, dict):
        fail(f"manifest owner {index} must be an object")
    _locator(owner, MANIFEST_OWNER_FIELDS, f"manifest owner {index}")
    for field in MANIFEST_OWNER_FIELDS:
        _string(owner[field], f"manifest owner {index} {field}")
    if owner["surface_class"] not in OWNER_CLASSES:
        fail(f"manifest owner {index} has an unknown surface class")


def _validate_manifest_header(value: dict[str, Any]) -> None:
    _exact_keys(
        value["lifecycle_labels"],
        {"active_guidance", "candidate_phase", "evidence_status"},
        "lifecycle labels",
    )
    if value["lifecycle_labels"] != {
        "active_guidance": "not-active",
        "candidate_phase": "pre-authoring",
        "evidence_status": "rejected-evidence",
    }:
        fail("lifecycle labels must preserve the pre-authoring rejected-evidence boundary")
    validate_manifest_lifecycle_schema(
        value["lifecycle_contracts"],
        exact_keys=_exact_keys,
        fail=fail,
    )
    _exact_keys(
        value["owner_schema"],
        {"additional_properties", "allowed_surface_classes", "locator_rule", "required_fields"},
        "owner schema",
    )
    if value["owner_schema"]["additional_properties"] is not False:
        fail("owner schema must refuse additional properties")
    if set(value["owner_schema"]["allowed_surface_classes"]) != OWNER_CLASSES:
        fail("owner schema surface classes are incomplete")
    if set(value["owner_schema"]["required_fields"]) != MANIFEST_OWNER_FIELDS:
        fail("owner schema required fields are incomplete")


def validate_candidate_surface_manifest(value: Any) -> dict[str, Any]:
    _exact_keys(value, MANIFEST_KEYS, "candidate-surface manifest")
    if value["schema_version"] != 8 or value["artifact"] != "apg-skill-candidate-surfaces":
        fail("candidate-surface manifest identity is invalid")
    _validate_manifest_header(value)
    validate_required_roles_declaration(value["required_roles"], fail=fail)
    owners = value["owners"]
    if not isinstance(owners, list) or not owners:
        fail("candidate-surface manifest owners must be nonempty")
    for index, owner in enumerate(owners):
        _validate_manifest_owner(owner, index)
    ids = [owner["owner_id"] for owner in owners]
    if len(ids) != len(set(ids)):
        fail("candidate-surface manifest owner IDs must be unique")
    return value


def load_candidate_surface_manifest(
    path: Path,
    *,
    root: Path | None = None,
    value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if value is None and root is None:
        fail("candidate-surface manifest requires a physical repository root")
    return validate_candidate_surface_manifest(
        _read_json(path, root) if value is None else value
    )


def _validate_plan_owner(owner: Any, index: int) -> None:
    if not isinstance(owner, dict):
        fail(f"removal-plan owner {index} must be an object")
    _locator(owner, PLAN_OWNER_FIELDS, f"removal-plan owner {index}")
    for field in ("owner_id", "surface_class"):
        _string(owner[field], f"removal-plan owner {index} {field}")
    actions = owner["actions"]
    if not isinstance(actions, list) or actions != sorted(set(actions)):
        fail(f"removal-plan owner {index} actions must be sorted and unique")
    if not set(actions) <= LIFECYCLE_ACTIONS:
        fail(f"removal-plan owner {index} has an unknown action")
    for field in ("retained_omission_test", "rejected_stale_test"):
        if not isinstance(owner[field], bool):
            fail(f"removal-plan owner {index} {field} must be boolean")
    if owner["surface_class"] not in OWNER_CLASSES:
        fail(f"removal-plan owner {index} has an unknown surface class")


def _validate_plan_header(value: dict[str, Any]) -> None:
    _exact_keys(
        value["candidate"],
        {"active_guidance", "candidate_id", "candidate_phase", "evidence_status"},
        "CSS removal plan candidate",
    )
    if value["candidate"] != {
        "active_guidance": "not-active",
        "candidate_id": "css-language-profile",
        "candidate_phase": "pre-authoring",
        "evidence_status": "rejected-evidence",
    }:
        fail("CSS removal plan candidate is invalid")
    if value["actions"] != sorted(LIFECYCLE_ACTIONS):
        fail("CSS removal plan lifecycle action vocabulary is incomplete")
    digest = value["source_contract_sha256"]
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        fail("CSS removal plan source contract digest is invalid")


def _validate_closure_contracts(value: dict[str, Any]) -> None:
    closure = value["closure_contracts"]
    _exact_keys(
        closure,
        {
            "actual_lifecycle",
            "candidate_decision",
            "current_survivor_python_bindings",
            "derived_skill_set",
            "dynamic_consumer",
            "narrative_state",
            "python_source_binding",
            "python_bindings",
            "repository_path",
            "semantic_role_registry",
            "traceability",
        },
        "closure contracts",
    )
    traceability = closure["traceability"]
    _exact_keys(
        traceability,
        {
            "clause_marker_syntax",
            "clause_owner_ids",
            "clause_owner_paths",
            "contract_map_owner_id",
            "contract_path",
            "contract_revision",
            "contract_sha256",
            "schema_version",
            "semantic_boundary",
        },
        "traceability closure",
    )
    if (
        traceability["schema_version"] != 2
        or traceability["contract_revision"] != "APG60A"
        or traceability["contract_sha256"] != value["source_contract_sha256"]
        or traceability["clause_marker_syntax"]
        != "<!-- APG-CLAUSE: {clause_id} -->"
        or traceability["clause_owner_ids"]
        != ["canonical-leaf", "candidate-specification"]
        or traceability["semantic_boundary"]
        != "navigation-only; clause prose requires APG62 semantic validation"
        or traceability["clause_owner_paths"]
        != [
            "skills/{candidate_id}/SKILL.md",
            "docs/specs/{candidate_id}.md",
        ]
        or traceability["contract_map_owner_id"] != "candidate-contract-map"
    ):
        fail("traceability closure contract is invalid")
    _string(traceability["contract_path"], "traceability contract path")
    validate_foundation_closure_contracts(
        closure,
        exact_keys=_exact_keys,
        fail=fail,
    )
    validate_actual_lifecycle_schema(
        closure["actual_lifecycle"],
        exact_keys=_exact_keys,
        fail=fail,
    )
    validate_narrative_schema(
        closure["narrative_state"],
        exact_keys=_exact_keys,
        fail=fail,
    )
    bindings = closure["python_bindings"]
    if bindings != PYTHON_BINDINGS:
        fail("Python owner bindings disagree with the frozen owner variables")
    if (
        closure["current_survivor_python_bindings"]
        != CURRENT_SURVIVOR_PYTHON_BINDINGS
    ):
        fail("current survivor Python bindings are not contract-exact")
    validate_python_source_binding_schema(
        closure["python_source_binding"],
        fail=fail,
    )
    decision = closure["candidate_decision"]
    _exact_keys(
        decision,
        {
            "decision_owner_id",
            "index_owner_id",
            "index_path",
            "lifecycle_states",
            "retained_statuses",
        },
        "candidate decision closure",
    )
    if decision != {
        "decision_owner_id": "candidate-decision-record",
        "index_owner_id": "narrative-adr-index",
        "index_path": "docs/adr/README.md",
        "lifecycle_states": [
            "authored-proposed-unintegrated",
            "unused",
            "retained",
            "rejected",
        ],
        "retained_statuses": ["Accepted", "Accepted with amendment"],
    }:
        fail("candidate decision closure contract is invalid")
    repository_path = closure["repository_path"]
    _exact_keys(
        repository_path,
        {
            "authority_root",
            "direct_owner_ancestry",
            "glob_ownership",
            "projection_leaf",
            "projection_target",
            "regular_file_read",
        },
        "repository path closure",
    )
    if repository_path != {
        "authority_root": "single-resolved-physical-repository-root",
        "direct_owner_ancestry": "descriptor-relative-no-follow",
        "glob_ownership": "verified-direct-parent-and-direct-regular-matches",
        "projection_leaf": "exact-relative-symlink",
        "projection_target": "direct-regular-canonical-owner",
        "regular_file_read": AUTHORITATIVE_REGULAR_FILE_READ,
    }:
        fail("repository path closure contract is invalid")


def _validate_plan_exclusions(value: dict[str, Any]) -> None:
    exclusions = value["contract_foundation_exclusions"]
    if not isinstance(exclusions, list):
        fail("CSS removal plan exclusions must be an array")
    for exclusion in exclusions:
        _exact_keys(exclusion, {"path", "reason"}, "contract foundation exclusion")
        _string(exclusion["path"], "contract foundation exclusion path")
        _string(exclusion["reason"], "contract foundation exclusion reason")


def _validate_owner_actions(owner: dict[str, Any]) -> None:
    actions = set(owner["actions"])
    owner_class = owner["surface_class"]
    if owner_class == "current-integration-surface" and (
        "verify-absent" not in actions
        or actions & {"preserve-historical", "rewrite-current-summary"}
    ):
        fail(f"{owner['owner_id']} current integration actions are invalid")
    if owner_class == "current-narrative-owner" and actions != {
        "rewrite-current-summary", "verify-absent", "verify-survivors"
    }:
        fail(f"{owner['owner_id']} current narrative actions are invalid")
    if owner_class == "candidate-decision-lifecycle" and actions != {
        "preserve-historical", "verify-absent", "verify-survivors"
    }:
        fail(f"{owner['owner_id']} decision lifecycle actions are invalid")
    if owner_class not in LIFECYCLE_CLASSES and actions != {
        "preserve-historical", "verify-survivors"
    }:
        fail(f"{owner['owner_id']} historical actions are invalid")


def validate_removal_plan(value: Any) -> dict[str, Any]:
    _exact_keys(value, PLAN_KEYS, "CSS removal plan")
    if value["schema_version"] != 8 or value["artifact"] != "apg60-css-removal-plan":
        fail("CSS removal plan identity is invalid")
    _validate_plan_header(value)
    _validate_closure_contracts(value)
    _validate_plan_exclusions(value)
    owners = value["owners"]
    if not isinstance(owners, list) or not owners:
        fail("CSS removal plan owners must be nonempty")
    for index, owner in enumerate(owners):
        _validate_plan_owner(owner, index)
        _validate_owner_actions(owner)
    ids = [owner["owner_id"] for owner in owners]
    if len(ids) != len(set(ids)):
        fail("CSS removal plan owner IDs must be unique")
    return value


def load_removal_plan(
    path: Path,
    *,
    root: Path | None = None,
    value: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if value is None and root is None:
        fail("CSS removal plan requires a physical repository root")
    return validate_removal_plan(
        _read_json(path, root) if value is None else value
    )


def validate_candidate_surface_contract(
    manifest: dict[str, Any], plan: dict[str, Any]
) -> None:
    validate_candidate_surface_manifest(manifest)
    validate_removal_plan(plan)
    validate_required_role_graph(manifest, plan, fail=fail)
    validate_required_role_registry(manifest, plan, fail=fail)


def _synthetic_relative(owner: dict[str, Any]) -> Path:
    locator = owner.get("path", owner.get("path_pattern"))
    if locator.startswith(("git-object:", "managed-report:")):
        return Path(".apg-virtual") / re.sub(r"[^A-Za-z0-9._-]", "_", locator)
    if "path" in owner:
        return Path(locator)
    replacement = locator
    replacement = replacement.replace("**", "synthetic/record")
    replacement = replacement.replace("[89]", "8")
    replacement = replacement.replace("*", "surface")
    if replacement.endswith("/"):
        replacement += "record.md"
    path = Path(replacement)
    if path.suffix == "":
        path /= "record.md"
    return path


def _lexically_exists(path: Path) -> bool:
    """Observe a path entry without requiring its symlink target to exist."""
    return path.exists() or path.is_symlink()


def _read_python_states(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "APG_SYNTHETIC_OWNERS"
                for target in node.targets
            )
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, dict):
                return value
    return {}


def _read_owner_states(path: Path) -> dict[str, str]:
    if path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        return value.get("apg_synthetic_owners", {})
    if path.suffix == ".py":
        return _read_python_states(path)
    states: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("APG_SYNTHETIC_OWNER "):
            _, owner_id, state = line.split()
            states[owner_id] = state
    return states


def _python_owner_text(
    states: dict[str, str], represented_candidate: str
) -> str:
    variables = sorted(
        {
            PYTHON_BINDINGS[owner_id]
            for owner_id in states
            if owner_id in PYTHON_BINDINGS
        },
        key=lambda variable: (
            variable == "AUDITED_PROJECTIONS",
            variable,
        ),
    )
    bindings = []
    if "AUDITED_PROJECTIONS" in variables:
        bindings.append("from pathlib import PurePosixPath\n")
    for variable in variables:
        if variable == "AUDITED_PROJECTIONS":
            bindings.append(
                "AUDITED_PROJECTIONS = tuple(sorted(\n"
                '    f".agents/skills/{PurePosixPath(path).parent.name}"\n'
                "    for path in AUDITED_SKILLS\n"
                "))\n"
            )
        else:
            bindings.append(f"{variable} = ()\n")
    return (
        f"CANDIDATE = {represented_candidate!r}\n"
        + "".join(bindings)
        + f"APG_SYNTHETIC_OWNERS = {dict(sorted(states.items()))!r}\n"
    )


def _plain_owner_text(
    path: Path,
    states: dict[str, str],
    represented_candidate: str,
) -> str:
    existing = []
    if path.exists():
        existing = [
            line
            for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("APG_SYNTHETIC_OWNER ")
            and not line.startswith("candidate=")
        ]
    lines = [
        *existing,
        f"candidate={represented_candidate}",
        *(
            f"APG_SYNTHETIC_OWNER {key} {value}"
            for key, value in sorted(states.items())
        ),
    ]
    return "\n".join(lines) + "\n"


def _write_owner_state(
    root: Path, owner: dict[str, Any], candidate: str, state: str
) -> None:
    path = root / _synthetic_relative(owner)
    path.parent.mkdir(parents=True, exist_ok=True)
    if owner["owner_id"] == "projection":
        if path.is_symlink() or path.exists():
            path.unlink()
        path.symlink_to(Path("../../skills") / candidate)
        return
    if owner["surface_class"] == "current-narrative-owner":
        marker_state = (
            "retained-provisional" if state == "present" else "absent"
        )
        path.write_text(
            f"<!-- APG-CANDIDATE-STATE: {candidate} {marker_state} -->\n\n"
            f"{candidate} is "
            f"{'active and retained' if state == 'present' else 'rejected and absent'}.\n"
            f"APG_SYNTHETIC_OWNER {owner['owner_id']} {state}\n",
            encoding="utf-8",
        )
        return
    states = _read_owner_states(path) if path.exists() else {}
    states[owner["owner_id"]] = state
    represented_candidate = (
        "project-owned-fallback" if state == "survivor" else candidate
    )
    if path.suffix == ".json":
        value = {
            "apg_synthetic_owners": dict(sorted(states.items())),
            "candidate": represented_candidate,
        }
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    elif path.suffix == ".py":
        path.write_text(
            _python_owner_text(states, represented_candidate),
            encoding="utf-8",
        )
    else:
        path.write_text(
            _plain_owner_text(path, states, represented_candidate),
            encoding="utf-8",
        )


def _synthetic_state_for(
    owner: dict[str, Any],
    lifecycle: str,
    omit_owner: str | None,
    stale_owner: str | None,
) -> str | None:
    owner_id = owner["owner_id"]
    if owner_id == omit_owner:
        return None
    if owner["surface_class"] == "candidate-decision-lifecycle":
        return "present" if lifecycle == "retained" else "history"
    if owner["surface_class"] not in CURRENT_CLASSES:
        return "history"
    if lifecycle == "retained" or owner_id == stale_owner:
        return "present"
    if owner["surface_class"] == "current-narrative-owner":
        return "rejected"
    if "verify-survivors" in owner["actions"] and "delete" not in owner["actions"]:
        return "survivor"
    return None


def _write_synthetic_references(
    root: Path, lifecycle: str, current_ids: list[str]
) -> None:
    references = root / ".apg-synthetic-references"
    if lifecycle == "retained":
        references.write_text(
            "".join(f"APG_REF:{owner_id}\n" for owner_id in current_ids),
            encoding="utf-8",
        )
    else:
        references.write_text("APG_FALLBACK:project-policy\n", encoding="utf-8")


def _write_synthetic_decision(
    root: Path,
    plan: dict[str, Any],
    lifecycle: str,
    omit_owner: str | None,
    stale_owner: str | None,
) -> None:
    owner = next(
        item
        for item in plan["owners"]
        if item["surface_class"] == "candidate-decision-lifecycle"
    )
    if owner["owner_id"] == omit_owner:
        return
    candidate = plan["candidate"]["candidate_id"]
    status = "Accepted" if lifecycle == "retained" else "Rejected"
    state = "present" if lifecycle == "retained" else "history"
    _write_owner_state(root, owner, candidate, state)
    decision = root / owner["path"]
    decision.write_text(
        "# ADR 0036: CSS Language Profile from Frozen Contract\n\n"
        f"- Status: {status}\n"
        "- Proposed in: APG61\n"
        "- Decided in: APG62\n\n"
        f"{candidate} terminal decision.\n"
        f"APG_SYNTHETIC_OWNER {owner['owner_id']} {state}\n",
        encoding="utf-8",
    )
    index_owner = next(
        item for item in plan["owners"] if item["owner_id"] == "narrative-adr-index"
    )
    if omit_owner == index_owner["owner_id"]:
        return
    index_state = (
        "present"
        if lifecycle == "retained" or stale_owner == index_owner["owner_id"]
        else "rejected"
    )
    index = root / index_owner["path"]
    index.write_text(
        f"<!-- APG-CANDIDATE-STATE: {candidate} "
        f"{'retained-provisional' if lifecycle == 'retained' else 'absent'} -->\n\n"
        "- [`0036 — CSS Language Profile from Frozen Contract`]"
        "(2026/07/0036-css-language-profile-from-frozen-contract.md)\n"
        f"  — {status}\n"
        f"APG_SYNTHETIC_OWNER {index_owner['owner_id']} {index_state}\n",
        encoding="utf-8",
    )


def materialize_synthetic_state(
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    lifecycle: str,
    *,
    omit_owner: str | None = None,
    stale_owner: str | None = None,
) -> None:
    validate_candidate_surface_contract(manifest, plan)
    if lifecycle not in {"retained", "rejected"}:
        fail("synthetic lifecycle must be retained or rejected")
    root.mkdir(parents=True, exist_ok=True)
    candidate = plan["candidate"]["candidate_id"]
    current_ids: list[str] = []
    for owner in plan["owners"]:
        state = _synthetic_state_for(owner, lifecycle, omit_owner, stale_owner)
        if state is not None:
            _write_owner_state(root, owner, candidate, state)
        if state == "present" and owner["surface_class"] in LIFECYCLE_CLASSES:
            current_ids.append(owner["owner_id"])
    _write_synthetic_decision(
        root, plan, lifecycle, omit_owner, stale_owner
    )
    _write_synthetic_references(root, lifecycle, current_ids)


def _owner_paths(root: Path, owner: dict[str, Any]) -> list[Path]:
    locator = owner.get("path", owner.get("path_pattern"))
    if locator.startswith(("git-object:", "managed-report:")):
        path = root / _synthetic_relative(owner)
        return [path] if _lexically_exists(path) else []
    if "path_pattern" in owner:
        return [
            path
            for path in root.glob(locator)
            if path.is_file() or path.is_symlink()
        ]
    path = root / locator
    return [path] if _lexically_exists(path) else []


def _owner_state(root: Path, owner: dict[str, Any]) -> set[str]:
    if owner["owner_id"] == "projection":
        return {"present"} if any(path.is_symlink() for path in _owner_paths(root, owner)) else set()
    states: set[str] = set()
    for path in _owner_paths(root, owner):
        states.update(
            state
            for owner_id, state in _read_owner_states(path).items()
            if owner_id == owner["owner_id"]
        )
    return states


def _assert_verification_shape(
    root: Path, manifest_owner: dict[str, Any], plan_owner: dict[str, Any]
) -> None:
    paths = _owner_paths(root, plan_owner)
    if not paths:
        return
    method = manifest_owner["verification_method"]
    if "symlink" in method and not all(path.is_symlink() for path in paths):
        fail(f"{plan_owner['owner_id']} verification requires a symlink")
    if "AST" in method:
        for path in paths:
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"))
    if "JSON" in method:
        for path in paths:
            if path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))


def _assert_historical_states(root: Path, owners: list[dict[str, Any]]) -> None:
    for owner in owners:
        if owner["surface_class"] in LIFECYCLE_CLASSES:
            continue
        if "history" not in _owner_state(root, owner):
            fail(f"{owner['owner_id']} historical evidence was not preserved")


def _assert_current_state(
    root: Path,
    manifest_by_id: dict[str, dict[str, Any]],
    owner: dict[str, Any],
    lifecycle: str,
) -> None:
    if owner["surface_class"] == "candidate-decision-lifecycle":
        states = _owner_state(root, owner)
        expected = "present" if lifecycle == "retained" else "history"
        if expected not in states:
            fail(f"{owner['owner_id']} decision lifecycle is incomplete")
        return
    if owner["surface_class"] not in CURRENT_CLASSES:
        return
    owner_id = owner["owner_id"]
    states = _owner_state(root, owner)
    _assert_verification_shape(root, manifest_by_id[owner_id], owner)
    if lifecycle == "retained" and "present" not in states:
        fail(f"{owner_id} is omitted from retained closure")
    if lifecycle == "rejected" and "present" in states:
        fail(f"{owner_id} is a stale current owner after rejection")
    if (
        lifecycle == "rejected"
        and owner["surface_class"] == "current-integration-surface"
        and "verify-survivors" in owner["actions"]
        and "delete" not in owner["actions"]
        and "survivor" not in states
    ):
        fail(f"{owner_id} rejected survivor verification is missing")
    if (
        lifecycle == "rejected"
        and owner["surface_class"] == "current-narrative-owner"
        and "rejected" not in states
    ):
        fail(f"{owner_id} rejected current-summary repair is missing")


def _assert_surviving_references(
    root: Path, owners: list[dict[str, Any]]
) -> None:
    references_path = root / ".apg-synthetic-references"
    references = (
        references_path.read_text(encoding="utf-8").splitlines()
        if references_path.exists()
        else []
    )
    for line in references:
        if not line.startswith("APG_REF:"):
            continue
        owner_id = line.removeprefix("APG_REF:")
        owner = next((item for item in owners if item["owner_id"] == owner_id), None)
        if owner is None or "present" not in _owner_state(root, owner):
            fail(f"surviving reference does not resolve to retained owner: {owner_id}")


def _assert_no_stale_content(
    root: Path, owners: list[dict[str, Any]], candidate: str
) -> None:
    for owner in owners:
        if owner["surface_class"] != "current-integration-surface":
            continue
        for path in _owner_paths(root, owner):
            stale = owner["owner_id"] == "projection"
            if not stale:
                stale = candidate in path.read_text(encoding="utf-8")
            if stale:
                fail(f"{owner['owner_id']} has stale candidate content after rejection")


def assert_synthetic_lifecycle(
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    lifecycle: str,
) -> None:
    validate_candidate_surface_contract(manifest, plan)
    manifest_by_id = {owner["owner_id"]: owner for owner in manifest["owners"]}
    owners = plan["owners"]
    _assert_historical_states(root, owners)
    for owner in owners:
        _assert_current_state(root, manifest_by_id, owner, lifecycle)
    _assert_surviving_references(root, owners)
    if lifecycle == "rejected":
        _assert_no_stale_content(root, owners, plan["candidate"]["candidate_id"])


def _excluded_paths(plan: dict[str, Any]) -> set[str]:
    return {
        exclusion["path"]
        for exclusion in plan["contract_foundation_exclusions"]
    }


def _pattern_matches(root: Path, pattern: str) -> list[Path]:
    if pattern.startswith(("git-object:", "managed-report:")):
        return []
    return [path for path in root.glob(pattern) if _lexically_exists(path)]


def derive_skill_surface_counts(root: Path) -> tuple[int, int, int]:
    try:
        with RepositoryPathContract(root) as repository:
            nested_kind = repository.entry_kind("skills/chatgpt")
            if nested_kind not in {None, "directory"}:
                fail("nested skill root must be a direct directory")
            canonical = {
                *repository.glob_regular_files("skills/*/SKILL.md"),
                *(
                    repository.glob_regular_files(
                        "skills/chatgpt/*/SKILL.md"
                    )
                    if nested_kind == "directory"
                    else ()
                ),
            }
            catalog = sum(
                line.startswith("| [`")
                for line in repository.read_text(
                    "skills/README.md"
                ).splitlines()
            )
            projections = len(
                repository.directory_entries(".agents/skills")
            )
    except RepositoryPathError as error:
        fail(f"skill surface path ownership is invalid: {error}")
    return len(canonical), catalog, projections


def _current_integration_residue(
    root: Path, plan: dict[str, Any], candidate: str
) -> list[str]:
    from apg_candidate_current_state_contract import (
        assert_current_survivor,
    )

    excluded = _excluded_paths(plan)
    residue: list[str] = []
    for owner in plan["owners"]:
        if owner["surface_class"] != "current-integration-surface":
            continue
        locator = owner.get("path", owner.get("path_pattern"))
        if "delete" in owner["actions"]:
            matches = _pattern_matches(root, locator) if "path_pattern" in owner else [root / locator]
            residue.extend(
                str(path.relative_to(root))
                for path in matches
                if (
                    _lexically_exists(path)
                    and str(path.relative_to(root)) not in excluded
                )
            )
        elif locator.startswith(("git-object:", "managed-report:")):
            continue
        else:
            assert_current_survivor(
                root,
                owner,
                candidate,
                plan["closure_contracts"][
                    "current_survivor_python_bindings"
                ].get(
                    owner["owner_id"]
                ),
            )
    return residue


@pinned_repository_root
def assert_actual_rejected_surface_absent(
    root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    *,
    decision_lifecycle: str | None = None,
) -> None:
    """Reject current residue while preserving truthful narrative history."""
    from apg_candidate_decision_contract import assert_candidate_decision
    from apg_candidate_narrative_state_contract import assert_narrative_state

    validate_candidate_surface_contract(manifest, plan)
    candidate = plan["candidate"]["candidate_id"]
    residue = _current_integration_residue(root, plan, candidate)
    if residue:
        fail("current candidate surface remains: " + ", ".join(sorted(set(residue))))
    for owner in plan["owners"]:
        if owner["surface_class"] == "current-narrative-owner":
            assert_narrative_state(root, owner, candidate, "absent")
        elif owner["surface_class"] == "candidate-decision-lifecycle":
            lifecycle = decision_lifecycle
            if lifecycle is None:
                decision = root / owner["path"]
                lifecycle = (
                    "rejected"
                    if decision.exists() or decision.is_symlink()
                    else "unused"
                )
            assert_candidate_decision(
                root,
                owner,
                candidate,
                plan["closure_contracts"]["candidate_decision"],
                lifecycle,
            )
