"""Current-maintenance inventory for the post-tag Nix readback route."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

INVENTORY_SCHEMA = "apgr.nix-readback-maintenance-inventory/v1"
BASE_RELEASE = "v0.13.1"
WORKFLOW_PATH = ".github/workflows/nix-post-tag-readback.yml"

# These owners describe the current maintenance route. They deliberately live
# outside the frozen release/public-surface.json policy: the route was added
# after v0.13.1 and must be audited without redefining that tagged surface.
OWNER_RECORDS = (
    {"path": WORKFLOW_PATH, "role": "workflow"},
    {"path": "tools/ci/nix_readback_topology.py", "role": "workflow-validator"},
    {"path": "tools/ci/ci_topology.py", "role": "topology-registration"},
    {"path": "tools/ci/nix_readback_maintenance.py", "role": "maintenance-inventory"},
    {"path": "docs/guides/nix-flake.md", "role": "operator-guide"},
    {
        "path": "src/test/unit/python/agentic-praxis-grimoire/tools/ci/ci_topology.unit.test.py",
        "role": "topology-unit-test",
    },
    {
        "path": "src/test/int/python/agentic-praxis-grimoire/tools/ci/ci_topology.int.test.py",
        "role": "topology-integration-test",
    },
)

INVENTORY: dict[str, object] = {
    "schema": INVENTORY_SCHEMA,
    "base_release": BASE_RELEASE,
    "workflow": WORKFLOW_PATH,
    "owners": OWNER_RECORDS,
}


def _error(label: str, detail: str) -> str:
    return f"nix-readback maintenance inventory: {label} {detail}"


def validate_inventory(
    inventory: Mapping[str, object],
    repo_root: Path,
) -> list[str]:
    """Validate the exact owner inventory and its source files."""

    errors: list[str] = []
    expected_keys = {"schema", "base_release", "workflow", "owners"}
    if set(inventory) != expected_keys:
        errors.append(
            _error(
                "keys must be exact:",
                f"expected={sorted(expected_keys)}, got={sorted(inventory)}",
            )
        )

    if inventory.get("schema") != INVENTORY_SCHEMA:
        errors.append(_error("schema must be", repr(INVENTORY_SCHEMA)))
    if inventory.get("base_release") != BASE_RELEASE:
        errors.append(_error("base_release must be", repr(BASE_RELEASE)))
    if inventory.get("workflow") != WORKFLOW_PATH:
        errors.append(_error("workflow must be", repr(WORKFLOW_PATH)))

    owners = inventory.get("owners")
    if not isinstance(owners, Sequence) or isinstance(owners, (str, bytes)):
        errors.append(_error("owners must be", "an ordered sequence of path records"))
        return errors

    normalized: list[dict[str, Any]] = []
    for index, owner in enumerate(owners):
        if not isinstance(owner, Mapping) or set(owner) != {"path", "role"}:
            errors.append(_error(f"owner[{index}] must have", "exact path and role keys"))
            continue
        path = owner.get("path")
        role = owner.get("role")
        if not isinstance(path, str) or not path:
            errors.append(_error(f"owner[{index}] path must be", "a non-empty string"))
        if not isinstance(role, str) or not role:
            errors.append(_error(f"owner[{index}] role must be", "a non-empty string"))
        normalized.append({"path": path, "role": role})

    expected_records = [dict(record) for record in OWNER_RECORDS]
    if normalized != expected_records:
        errors.append(
            _error(
                "owners must match the exact current route:",
                f"expected={expected_records!r}, got={normalized!r}",
            )
        )

    seen_paths: set[str] = set()
    for owner in normalized:
        path = owner.get("path")
        if not isinstance(path, str):
            continue
        if path in seen_paths:
            errors.append(_error("owners contain duplicate path", repr(path)))
        seen_paths.add(path)
        source = repo_root / path
        if source.is_symlink() or not source.is_file():
            errors.append(_error("owner source is missing or not a regular file", repr(path)))

    return errors


def validate_current_maintenance(repo_root: Path = ROOT) -> list[str]:
    """Validate this route only when its post-tag workflow is present."""

    workflow = repo_root / WORKFLOW_PATH
    if not workflow.exists():
        return []
    return validate_inventory(INVENTORY, repo_root)
