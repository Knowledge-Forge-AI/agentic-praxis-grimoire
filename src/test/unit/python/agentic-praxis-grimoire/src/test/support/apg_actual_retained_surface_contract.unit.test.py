"""Disposable actual-tree contracts for retained candidate-surface closure."""
from __future__ import annotations

import importlib
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
)
from apg_candidate_lifecycle_fixture import (  # noqa: E402
    materialize_actual_retained,
)


CANDIDATE = "css-language-profile"
MANIFEST = load_candidate_surface_manifest(
    ROOT / "testing/apg-skill-candidate-surfaces.json", root=ROOT
)
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)
CURRENT_IDS = [owner["owner_id"] for owner in PLAN["owners"] if owner["surface_class"].startswith("current-")]

def _checker():
    try:
        module = importlib.import_module("apg_actual_retained_surface_contract")
    except ModuleNotFoundError:
        pytest.fail("actual retained-surface checker is absent")
    return module.assert_actual_retained_surface_present

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, value: object) -> None:
    _write(path, json.dumps(value, indent=2) + "\n")


def _python_tuple(name: str, values: list[str]) -> str:
    return f"{name} = {tuple(values)!r}\n"


def _surface_paths() -> dict[str, str]:
    python = "python/agentic-praxis-grimoire/skills"
    return {
        "skill": f"skills/{CANDIDATE}/SKILL.md",
        "projection": f".agents/skills/{CANDIDATE}",
        "specification": f"docs/specs/{CANDIDATE}.md",
        "contract_map": f"docs/specs/{CANDIDATE}.contract-map.json",
        "fixture": f"src/test/fixtures/apg62-{CANDIDATE}-contract.json",
        "unit_test": f"src/test/unit/{python}/{CANDIDATE}/{CANDIDATE}.unit.test.py",
        "integration_test": (
            f"src/test/int/{python}/{CANDIDATE}/{CANDIDATE}.int.test.py"
        ),
    }


def _materialize_actual_retained(
    root: Path,
    omit: str | None = None,
    *,
    maturity: str = "provisional",
    decision_status: str = "Accepted",
) -> None:
    materialize_actual_retained(
        root,
        ROOT,
        PLAN,
        omit,
        maturity=maturity,
        decision_status=decision_status,
    )


def _externalize_directory(root: Path, outside: Path, relative: str) -> None:
    directory = root / relative
    destination = outside / relative.replace("/", "-").replace(".", "dot")
    directory.rename(destination)
    directory.symlink_to(destination, target_is_directory=True)

def test_fully_present_tree_passes_and_contract_map_is_closed(tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)
    contract_map = tmp_path / _surface_paths()["contract_map"]
    original = contract_map.read_text(encoding="utf-8")
    for scope, key, content in (
        ("top", "source_path", "/" "Users/example/private-source.css"),
        ("row", "target_expression", ".example { color: red; }"),
        ("row", "owner", r"C:\Users\example\evidence"), ("row", "required_response", "color: red"), ("row", "required_response", "@media screen"),
    ):
        value = json.loads(contract_map.read_text(encoding="utf-8"))
        target = value if scope == "top" else value["cases"][0]
        target[key] = content
        _write_json(contract_map, value)
        with pytest.raises(SurfaceContractError, match="candidate-contract-map"):
            _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)
        _write(contract_map, original)


def test_fully_retained_stable_actual_tree_passes(tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path, maturity="stable")
    _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)


@pytest.mark.parametrize("owner_id", CURRENT_IDS)
def test_each_current_owner_omission_fails_actual_retained_closure(
    tmp_path: Path, owner_id: str) -> None:
    _materialize_actual_retained(tmp_path, omit=owner_id)
    expected_owner = (
        "release-helper-audited-(?:skills|projections)"
        if owner_id == "release-helper-audited-skills"
        else owner_id
    )
    with pytest.raises(SurfaceContractError, match=expected_owner):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

@pytest.mark.parametrize("target", ("../../skills/missing", "../../skills/other"))
def test_wrong_or_dangling_projection_fails(tmp_path: Path, target: str) -> None:
    _materialize_actual_retained(tmp_path)
    projection = tmp_path / ".agents/skills/css-language-profile"
    projection.unlink()
    if target.endswith("other"):
        (tmp_path / "skills/other").mkdir()
    projection.symlink_to(target)
    with pytest.raises(SurfaceContractError, match="projection"):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

def test_rejected_narrative_contradicts_present_surfaces(tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    _write(tmp_path / "README.md", f"{CANDIDATE} is rejected and absent.\n")
    with pytest.raises(SurfaceContractError, match="narrative-readme"):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

def test_public_historical_preservation_is_required(tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    (
        tmp_path
        / "docs/adr/2026/07/0035-css-language-profile-and-policy-selected-structural-limits.md"
    ).unlink()
    with pytest.raises(SurfaceContractError, match="history-candidate-adr"):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

def test_dynamic_consumers_derive_live_state_without_candidate_row(
    tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    for relative in (
        "libexec/install_global_skills.py",
        "libexec/apg_skill_library_check.py",
        "libexec/apg_skill_topology.py",
        "skills/agentic-praxis-grimoire-workflow/SKILL.md",
    ):
        assert CANDIDATE not in (tmp_path / relative).read_text(encoding="utf-8")
    _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

def test_live_counts_are_derived_without_hard_coded_cardinality(
    tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    paths = _surface_paths()
    extra = paths["unit_test"].replace(".unit.test.py", "-extra.unit.test.py")
    _write(tmp_path / extra, f'CANDIDATE = "{CANDIDATE}"\n')
    for relative in (
        "libexec/apg_public_release.py",
        "src/test/int/python/agentic-praxis-grimoire/"
        "libexec/apg_public_release.int.test.py",
        "src/test/apg_public_release_cases.py",
        "src/test/unit/python/agentic-praxis-grimoire/"
        "libexec/apg_public_release.unit.test.py",
    ):
        owner = tmp_path / relative
        text = owner.read_text(encoding="utf-8").replace(
                repr(paths["integration_test"]),
                f"{extra!r}, {paths['integration_test']!r}",
        )
        _write(owner, text)
    policy_path = tmp_path / "release/public-surface.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["required_test_entrypoints"].append(extra)
    _write_json(policy_path, policy)
    inventory_path = tmp_path / "testing/apg-test-inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory["tests"].append(
        {"owner": paths["skill"], "path": extra, "suite": "unit"}
    )
    _write_json(inventory_path, inventory)
    _write(
        tmp_path / "skills/future-profile/SKILL.md",
        "---\nname: future-profile\ndescription: Future.\n---\n",
    )
    (tmp_path / ".agents/skills/future-profile").symlink_to(
        "../../skills/future-profile"
    )
    with (tmp_path / "skills/README.md").open("a", encoding="utf-8") as stream:
        stream.write(
            "| [`future-profile`](future-profile/SKILL.md) | Future | provisional |\n"
        )
    _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)


@pytest.mark.parametrize(
    ("target", "operation"),
    (
        ("dynamic-topology-consumer", "topology"),
        ("dynamic-skill-library-consumer", "library"),
        ("dynamic-global-installer-consumer", "installer"),
    ),
)
@pytest.mark.parametrize(
    "mutation",
    (
        "duplicate-other",
        "candidate-duplicate",
        "extra",
        "unsafe-control",
        "unsafe-separator",
    ),
)
def test_each_dynamic_consumer_rejects_non_exact_skill_sets(
    monkeypatch,
    tmp_path: Path,
    target: str,
    operation: str,
    mutation: str,
) -> None:
    _materialize_actual_retained(tmp_path)
    module = importlib.import_module("apg_actual_retained_surface_contract")
    counts = module.derive_skill_surface_counts(tmp_path)
    expected_names = module.canonical_skill_names(tmp_path)
    by_id = {owner["owner_id"]: owner for owner in PLAN["owners"]}

    received = list(expected_names)
    if mutation == "duplicate-other":
        received[0] = received[1]
    elif mutation == "candidate-duplicate":
        index = next(
            index for index, name in enumerate(received) if name != CANDIDATE
        )
        received[index] = CANDIDATE
    elif mutation == "extra":
        received.append("extra-only")
    elif mutation == "unsafe-control":
        received[0] = "unsafe-\x00name"
    else:
        received[0] = "unsafe/name"

    def duplicate_missing(_root, _path, _owner_id, current_operation):
        names = received if current_operation == operation else list(expected_names)
        if current_operation == "topology":
            return {"diagnostics": 0, "names": names}
        if current_operation == "library":
            return {
                "canonical_skills": counts[0],
                "catalog_rows": counts[1],
                "names": names,
                "passed": True,
                "projections": counts[2],
            }
        return {"names": names}

    monkeypatch.setattr(module, "_execute_repository_consumer", duplicate_missing)
    with pytest.raises(SurfaceContractError, match=target):
        if operation == "topology":
            module._assert_live_topology(
                tmp_path, by_id, CANDIDATE, expected_names
            )
        elif operation == "library":
            module._assert_live_library(
                tmp_path, by_id, counts, expected_names
            )
        else:
            module._assert_live_installer(
                tmp_path, by_id, CANDIDATE, expected_names
            )


@pytest.mark.parametrize(
    ("target", "operation"),
    (
        ("dynamic-topology-consumer", "topology"),
        ("dynamic-skill-library-consumer", "library"),
        ("dynamic-global-installer-consumer", "installer"),
    ),
)
def test_each_dynamic_consumer_rejects_candidate_absence(
    monkeypatch, tmp_path: Path, target: str, operation: str
) -> None:
    _materialize_actual_retained(tmp_path)
    module = importlib.import_module("apg_actual_retained_surface_contract")
    counts = module.derive_skill_surface_counts(tmp_path)
    expected_names = module.canonical_skill_names(tmp_path)
    by_id = {owner["owner_id"]: owner for owner in PLAN["owners"]}
    absent = list(expected_names)
    absent[absent.index(CANDIDATE)] = "other-a"

    def candidate_absent(_root, _path, _owner_id, current_operation):
        names = absent if current_operation == operation else list(expected_names)
        if current_operation == "topology":
            return {"diagnostics": 0, "names": names}
        if current_operation == "library":
            return {
                "canonical_skills": counts[0],
                "catalog_rows": counts[1],
                "names": names,
                "passed": True,
                "projections": counts[2],
            }
        return {"names": names}

    monkeypatch.setattr(module, "_execute_repository_consumer", candidate_absent)
    with pytest.raises(SurfaceContractError, match=target):
        if operation == "topology":
            module._assert_live_topology(tmp_path, by_id, CANDIDATE, expected_names)
        elif operation == "library":
            module._assert_live_library(tmp_path, by_id, counts, expected_names)
        else:
            module._assert_live_installer(tmp_path, by_id, CANDIDATE, expected_names)

def test_duplicate_candidate_owner_state_fails(tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    capability_map = (
        tmp_path
        / "skills/agentic-praxis-grimoire-workflow/references/capability-map.json"
    )
    value = json.loads(capability_map.read_text(encoding="utf-8"))
    value["capabilities"].append(dict(value["capabilities"][0]))
    _write_json(capability_map, value)
    with pytest.raises(SurfaceContractError, match="capability-map-entry"):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

@pytest.mark.parametrize(
    ("relative", "variable", "values", "owner_id"),
    (
        (
            "libexec/apg_project_skills_core.py",
            "EXPECTED_SKILLS",
            [CANDIDATE, CANDIDATE],
            "project-expected-skills",
        ),
        (
            "src/test/int/python/agentic-praxis-grimoire/"
            "libexec/apg_public_release.int.test.py",
            "EXPECTED_SURFACES",
            [CANDIDATE, CANDIDATE],
            "release-integration-mirror",
        ),
    ),
)
def test_duplicate_python_owner_membership_fails(
    tmp_path: Path,
    relative: str,
    variable: str,
    values: list[str],
    owner_id: str,
) -> None:
    _materialize_actual_retained(tmp_path)
    _write(tmp_path / relative, _python_tuple(variable, values))
    with pytest.raises(SurfaceContractError, match=owner_id):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

def test_duplicate_release_policy_membership_fails(tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    policy = tmp_path / "release/public-surface.json"
    value = json.loads(policy.read_text(encoding="utf-8"))
    value["required_skills"].append(value["required_skills"][0])
    _write_json(policy, value)
    with pytest.raises(SurfaceContractError, match="release-policy-required-skills"):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

def test_duplicate_test_inventory_membership_fails(tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    inventory = tmp_path / "testing/apg-test-inventory.json"
    value = json.loads(inventory.read_text(encoding="utf-8"))
    value["tests"].append(dict(value["tests"][0]))
    _write_json(inventory, value)
    with pytest.raises(SurfaceContractError, match="test-inventory-entry"):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

@pytest.mark.parametrize(
    ("relative", "needle", "owner_id"),
    (
        (
            "release/public-surface.json",
            "src/test/fixtures/apg62-css-language-profile-contract.json",
            "release-policy-critical-files",
        ),
        (
            "libexec/apg_public_release.py",
            "src/test/int/python/agentic-praxis-grimoire/skills/"
            "css-language-profile/css-language-profile.int.test.py",
            "release-helper-audited-tests",
        ),
        (
            "src/test/apg_public_release_cases.py",
            ".agents/skills/css-language-profile",
            "release-shared-case-mirror",
        ),
    ),
)
def test_partial_release_owner_membership_fails(
    tmp_path: Path, relative: str, needle: str, owner_id: str
) -> None:
    _materialize_actual_retained(tmp_path)
    path = tmp_path / relative
    if path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        value["critical_files"].remove(needle)
        _write_json(path, value)
    else:
        _write(
            path,
            path.read_text(encoding="utf-8").replace(repr(needle), "''"),
        )
    with pytest.raises(SurfaceContractError, match=owner_id):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

@pytest.mark.parametrize(
    ("relative", "content", "owner_id"),
    (
        (
            "src/test/fixtures/apg62-css-language-profile-contract.json",
            '{"candidate": "css-language-profile",',
            "candidate-fixture",
        ),
        (
            "src/test/unit/python/agentic-praxis-grimoire/skills/"
            "css-language-profile/css-language-profile.unit.test.py",
            'CANDIDATE = "css-language-profile"\nif ):\n',
            "focused-unit-test",
        ),
    ),
)
def test_malformed_candidate_owned_shape_fails(
    tmp_path: Path, relative: str, content: str, owner_id: str
) -> None:
    _materialize_actual_retained(tmp_path)
    _write(tmp_path / relative, content)
    with pytest.raises(SurfaceContractError, match=owner_id):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

def test_mixed_retained_and_rejected_narrative_fails(tmp_path: Path) -> None:
    _materialize_actual_retained(tmp_path)
    _write(
        tmp_path / "README.md",
        f"{CANDIDATE} is active and retained.\n"
        f"{CANDIDATE} is rejected and absent.\n",
    )
    with pytest.raises(SurfaceContractError, match="narrative-readme"):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)

@pytest.mark.parametrize("content", (
    '"""Generic live-inventory consumer."""\n',
    "INERT = 1\n",
    "def derive_live_inventory():\n    return ()\n",
))
def test_inert_dynamic_consumer_fails(tmp_path: Path, content: str) -> None:
    _materialize_actual_retained(tmp_path)
    _write(tmp_path / "libexec/apg_skill_topology.py", content)
    with pytest.raises(
        SurfaceContractError, match="dynamic-topology-consumer"
    ):
        _checker()(tmp_path, MANIFEST, PLAN, CANDIDATE)


@pytest.mark.parametrize(
    "relative",
    (
        "skills",
        "skills/css-language-profile",
        "docs/specs",
        ".agents",
        ".agents/skills",
        "libexec",
        "release",
        "testing",
        "src/test/unit",
        "src/test/int",
        "skills/agentic-praxis-grimoire-workflow/references",
        "docs",
    ),
    ids=(
        "skills-root",
        "candidate-skill-directory",
        "specification-parent",
        "projection-root",
        "projection-parent",
        "dynamic-consumer-parent",
        "release-parent",
        "test-inventory-parent",
        "unit-test-parent",
        "integration-test-parent",
        "capability-map-parent",
        "narrative-parent",
    ),
)
def test_retained_state_rejects_symlinked_owner_ancestor(
    tmp_path: Path,
    relative: str,
) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "external"
    outside.mkdir()
    _materialize_actual_retained(root)
    _externalize_directory(root, outside, relative)

    with pytest.raises(SurfaceContractError, match="ancestor|direct"):
        _checker()(root, MANIFEST, PLAN, CANDIDATE)
