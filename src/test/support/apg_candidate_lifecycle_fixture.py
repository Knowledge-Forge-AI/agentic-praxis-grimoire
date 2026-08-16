"""Disposable candidate lifecycle trees for focused contract tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

from apg_candidate_phase_history_contract import load_phase_history
from apg_repository_path_contract import RepositoryPathContract
from apg_candidate_surface_contract import materialize_synthetic_state


CANDIDATE = "css-language-profile"
SEMANTIC_BOUNDARY = (
    "navigation-only; clause prose requires APG62 semantic validation"
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write(path, json.dumps(value, indent=2) + "\n")


def python_tuple(name: str, values: list[str]) -> str:
    return f"{name} = {tuple(values)!r}\n"


def surface_paths() -> dict[str, str]:
    python = "python/agentic-praxis-grimoire/skills"
    return {
        "skill": f"skills/{CANDIDATE}/SKILL.md",
        "projection": f".agents/skills/{CANDIDATE}",
        "specification": f"docs/specs/{CANDIDATE}.md",
        "contract_map": f"docs/specs/{CANDIDATE}.contract-map.json",
        "fixture": f"src/test/fixtures/apg62-{CANDIDATE}-contract.json",
        "unit_test": (
            f"src/test/unit/{python}/{CANDIDATE}/{CANDIDATE}.unit.test.py"
        ),
        "integration_test": (
            f"src/test/int/{python}/{CANDIDATE}/{CANDIDATE}.int.test.py"
        ),
    }


def _traceability_rows(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "case_id": case["id"],
            "clause_ids": ["CSS-FROZEN-CONTRACT"],
            "forbidden_actions": sorted(case["expected"]["forbidden_actions"]),
            "required_actions": sorted(case["expected"]["required_actions"]),
            "rollback_required": case["expected"]["rollback"],
            "selected_owner": case["expected"]["selected_owner"],
        }
        for case in contract["cases"]
    ]


def _materialize_candidate_files(
    root: Path,
    source_root: Path,
    plan: dict[str, Any],
    omit: str | None,
    paths: dict[str, str],
) -> None:
    contract_relative = plan["closure_contracts"]["traceability"]["contract_path"]
    with RepositoryPathContract(source_root) as repository:
        contract_bytes = repository.read_bytes(contract_relative)
    contract = json.loads(contract_bytes)
    contract_path = root / contract_relative
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_bytes(contract_bytes)
    if omit != "canonical-leaf":
        write(
            root / paths["skill"],
            "---\n"
            f"name: {CANDIDATE}\n"
            "description: Disposable candidate.\n"
            "---\n\n"
            "<!-- APG-CLAUSE: CSS-FROZEN-CONTRACT -->\n",
        )
    if omit != "candidate-specification":
        write(root / paths["specification"], f"# {CANDIDATE}\n")
    if omit != "candidate-contract-map":
        write_json(
            root / paths["contract_map"],
            {
                "schema_version": 2,
                "candidate_id": CANDIDATE,
                "contract_revision": "APG60A",
                "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
                "semantic_boundary": SEMANTIC_BOUNDARY,
                "cases": _traceability_rows(contract),
            },
        )
    if omit != "candidate-fixture":
        write_json(
            root / paths["fixture"],
            {"candidate": CANDIDATE, "schema_version": 1},
        )
    if omit != "focused-unit-test":
        write(root / paths["unit_test"], f'CANDIDATE = "{CANDIDATE}"\n')
    if omit != "focused-integration-test":
        write(
            root / paths["integration_test"],
            f'CANDIDATE = "{CANDIDATE}"\n',
        )
    if omit != "projection":
        projection = root / paths["projection"]
        projection.parent.mkdir(parents=True, exist_ok=True)
        projection.symlink_to(Path("../../skills") / CANDIDATE)


def _materialize_routing_and_project(
    root: Path, omit: str | None
) -> None:
    capabilities = (
        []
        if omit == "capability-map-entry"
        else [{"name": CANDIDATE, "trigger": "Disposable retained candidate."}]
    )
    write_json(
        root
        / "skills/agentic-praxis-grimoire-workflow/references/capability-map.json",
        {
            "capabilities": capabilities,
            "router_name": "workflow",
            "schema_version": 1,
        },
    )
    dynamic_owners = {
        "dynamic-global-installer-consumer": "libexec/install_global_skills.py",
        "dynamic-skill-library-consumer": "libexec/apg_skill_library_check.py",
        "dynamic-topology-consumer": "libexec/apg_skill_topology.py",
        "router-consumer": "skills/agentic-praxis-grimoire-workflow/SKILL.md",
    }
    for owner_id, relative in dynamic_owners.items():
        if omit == owner_id:
            continue
        if owner_id == "dynamic-topology-consumer":
            body = (
                "def discover_canonical_leaves(root, skills, report):\n"
                "    return tuple(sorted(\n"
                "        path for path in skills.iterdir()\n"
                "        if path.is_dir() and (path / 'SKILL.md').is_file()\n"
                "    ))\n"
            )
        elif owner_id == "dynamic-skill-library-consumer":
            body = (
                "from types import SimpleNamespace\n\n"
                "def check_library(root):\n"
                "    canonical = len(list(root.glob('skills/**/SKILL.md')))\n"
                "    catalog = sum(line.startswith('| [`') for line in "
                "(root / 'skills/README.md').read_text().splitlines())\n"
                "    projections = len(list((root / '.agents/skills').iterdir()))\n"
                "    return SimpleNamespace(passed=canonical == catalog == "
                "projections, canonical_skills=canonical, catalog_rows=catalog, "
                "projections=projections)\n"
            )
        elif owner_id == "dynamic-global-installer-consumer":
            body = (
                "from types import SimpleNamespace\n\n"
                "def build_inventory(repositories, destination):\n"
                "    skills = tuple(SimpleNamespace(name=path.parent.name) "
                "for path in repositories[0].glob('skills/**/SKILL.md'))\n"
                "    return SimpleNamespace(skills=skills)\n"
            )
        else:
            body = (
                "# Workflow router\n\n## Procedure\n\n"
                "Derive routing from "
                "[the capability map](references/capability-map.json).\n"
            )
        write(root / relative, body)
    if omit != "router-consumer":
        projection = root / ".agents/skills/agentic-praxis-grimoire-workflow"
        projection.parent.mkdir(parents=True, exist_ok=True)
        projection.symlink_to("../../skills/agentic-praxis-grimoire-workflow")
    values = [] if omit == "project-expected-skills" else [CANDIDATE]
    write(
        root / "libexec/apg_project_skills_core.py",
        python_tuple("EXPECTED_SKILLS", values),
    )
    mirrors = {
        "project-integration-mirror": (
            "src/test/int/python/agentic-praxis-grimoire/"
            "libexec/apg_project_skills_core.int.test.py"
        ),
        "project-command-integration-mirror": (
            "src/test/int/python/agentic-praxis-grimoire/"
            "bin/apg-project-skills.int.test.py"
        ),
        "project-unit-mirror": (
            "src/test/unit/python/agentic-praxis-grimoire/"
            "libexec/apg_project_skills_core.unit.test.py"
        ),
    }
    for owner_id, relative in mirrors.items():
        values = [] if omit == owner_id else [CANDIDATE]
        write(root / relative, python_tuple("EXPECTED_SKILLS", values))


def _materialize_release(
    root: Path, omit: str | None, paths: dict[str, str]
) -> None:
    values = {
        "AUDITED_SKILLS": [paths["skill"]],
        "AUDITED_PROJECTIONS": [paths["projection"]],
        "AUDITED_CRITICAL": [
            paths["specification"],
            paths["contract_map"],
            paths["fixture"],
        ],
        "AUDITED_TESTS": [paths["unit_test"], paths["integration_test"]],
    }
    for variable in tuple(values):
        owner = "release-helper-audited-" + variable.removeprefix(
            "AUDITED_"
        ).lower()
        if omit == owner:
            values[variable] = []
    projections = (
        "AUDITED_PROJECTIONS = tuple(sorted(\n"
        '    f".agents/skills/{PurePosixPath(path).parent.name}"\n'
        "    for path in AUDITED_SKILLS\n"
        "))\n"
        if values["AUDITED_PROJECTIONS"]
        else "AUDITED_PROJECTIONS = ()\n"
    )
    write(
        root / "libexec/apg_public_release.py",
        "from pathlib import PurePosixPath\n"
        + python_tuple("AUDITED_SKILLS", values["AUDITED_SKILLS"])
        + projections
        + python_tuple("AUDITED_CRITICAL", values["AUDITED_CRITICAL"])
        + python_tuple("AUDITED_TESTS", values["AUDITED_TESTS"]),
    )
    policy = {
        "critical_files": values["AUDITED_CRITICAL"],
        "required_projections": values["AUDITED_PROJECTIONS"],
        "required_skills": values["AUDITED_SKILLS"],
        "required_test_entrypoints": values["AUDITED_TESTS"],
    }
    policy_owners = {
        "release-policy-critical-files": "critical_files",
        "release-policy-required-projections": "required_projections",
        "release-policy-required-skills": "required_skills",
        "release-policy-required-tests": "required_test_entrypoints",
    }
    if omit in policy_owners:
        policy[policy_owners[omit]] = []
    write_json(root / "release/public-surface.json", policy)
    release = [
        paths[key]
        for key in (
            "skill",
            "projection",
            "specification",
            "contract_map",
            "fixture",
            "unit_test",
            "integration_test",
        )
    ]
    mirrors = {
        "release-integration-mirror": (
            "src/test/int/python/agentic-praxis-grimoire/"
            "libexec/apg_public_release.int.test.py"
        ),
        "release-shared-case-mirror": "src/test/apg_public_release_cases.py",
        "release-unit-mirror": (
            "src/test/unit/python/agentic-praxis-grimoire/"
            "libexec/apg_public_release.unit.test.py"
        ),
    }
    for owner_id, relative in mirrors.items():
        write(
            root / relative,
            python_tuple(
                "EXPECTED_SURFACES", [] if omit == owner_id else release
            ),
        )


def _materialize_catalog_inventory_narrative(
    root: Path,
    plan: dict[str, Any],
    omit: str | None,
    paths: dict[str, str],
    maturity: str,
) -> None:
    catalog_row = (
        "| [`css-language-profile`](css-language-profile/SKILL.md) "
        f"| CSS | {maturity} |\n"
    )
    catalog = (
        "| [`agentic-praxis-grimoire-workflow`]"
        "(agentic-praxis-grimoire-workflow/SKILL.md) "
        "| Workflow | provisional |\n"
        + ("" if omit == "skill-catalog-row" else catalog_row)
    )
    if omit == "skill-maturity-row":
        catalog = catalog.replace("| CSS | provisional |", "| CSS | rejected |")
    write(root / "skills/README.md", "# APG Skill Library\n\n" + catalog)
    tests = (
        []
        if omit == "test-inventory-entry"
        else [
            {"owner": paths["skill"], "path": paths["unit_test"], "suite": "unit"},
            {
                "owner": paths["skill"],
                "path": paths["integration_test"],
                "suite": "integration",
            },
        ]
    )
    write_json(
        root / "testing/apg-test-inventory.json",
        {"coverage_sources": [], "schema_version": 1, "tests": tests},
    )
    state = (
        "<!-- APG-CANDIDATE-STATE: css-language-profile "
        f"retained-{maturity} -->"
    )
    for owner in plan["owners"]:
        if owner["surface_class"] == "current-narrative-owner" and omit != owner["owner_id"]:
            write(
                root / owner["path"],
                state
                + "\n\n"
                + f"{CANDIDATE} is active and retained guidance.\n",
            )
    write(
        root
        / "docs/adr/2026/07/0035-css-language-profile-and-policy-selected-structural-limits.md",
        f"{CANDIDATE} historical Rejected evidence.\n",
    )
    write(
        root / "docs/evaluations/apg58-css-language-profile-pilot-authoring.md",
        f"{CANDIDATE} historical candidate evidence.\n",
    )
    write(
        root
        / "docs/status/2026/07/29/00078-apg58-css-language-profile-pilot-authoring-exit.md",
        f"{CANDIDATE} historical phase exit.\n",
    )
    write(
        root
        / "docs/evaluations/apg45-fact-check-peer-review-and-roadmap-disposition.md",
        "Historical predecessor evidence.\n",
    )
    write(root / "docs/web-node-history.md", "Historical web and node evidence.\n")


def _materialize_decision(
    root: Path,
    plan: dict[str, Any],
    omit: str | None,
    decision_status: str,
) -> None:
    owner = next(
        item
        for item in plan["owners"]
        if item["owner_id"] == "candidate-decision-record"
    )
    if omit == owner["owner_id"]:
        return
    write(
        root / owner["path"],
        "# ADR 0036: CSS Language Profile from Frozen Contract\n\n"
        f"- Status: {decision_status}\n"
        "- Proposed in: APG61\n"
        "- Decided in: APG62\n\n"
        f"{CANDIDATE} retained decision.\n",
    )
    index = root / plan["closure_contracts"]["candidate_decision"]["index_path"]
    with index.open("a", encoding="utf-8") as stream:
        stream.write(
            "\n- [`0036 — CSS Language Profile from Frozen Contract`]"
            "(2026/07/0036-css-language-profile-from-frozen-contract.md)"
            f"\n  — {decision_status}\n"
        )


def materialize_actual_retained(
    root: Path,
    source_root: Path,
    plan: dict[str, Any],
    omit: str | None = None,
    *,
    maturity: str = "provisional",
    decision_status: str = "Accepted",
) -> None:
    if maturity not in {"provisional", "stable"}:
        raise ValueError(f"unsupported maturity: {maturity}")
    paths = surface_paths()
    _materialize_candidate_files(root, source_root, plan, omit, paths)
    _materialize_routing_and_project(root, omit)
    _materialize_release(root, omit, paths)
    _materialize_catalog_inventory_narrative(
        root, plan, omit, paths, maturity
    )
    _materialize_decision(root, plan, omit, decision_status)
    lifecycle = plan["closure_contracts"]["actual_lifecycle"]
    _materialize_phase_bundles(
        root,
        [
            *lifecycle["foundation_history"],
            *lifecycle["authoring_history"],
            *lifecycle["terminal_history"],
        ],
        plan,
    )


def _materialize_integrated_baseline(
    root: Path, plan: dict[str, Any]
) -> None:
    expected = plan["closure_contracts"]["actual_lifecycle"][
        "integrated_count"
    ]
    skills = root / "skills"
    existing = sorted(
        path.parent.name for path in skills.glob("*/SKILL.md")
    )
    for index in range(expected - len(existing)):
        name = f"fixture-profile-{index + 1:02d}"
        write(
            skills / name / "SKILL.md",
            f"---\nname: {name}\ndescription: Fixture.\n---\n",
        )
    names = sorted(path.parent.name for path in skills.glob("*/SKILL.md"))
    catalog = root / "skills/README.md"
    write(
        catalog,
        "<!-- APG_SYNTHETIC_OWNER skill-catalog-row survivor -->\n"
        "<!-- APG_SYNTHETIC_OWNER skill-maturity-row survivor -->\n"
        + "".join(
            f"| [`{name}`]({name}/SKILL.md) | Fixture | provisional |\n"
            for name in names
        ),
    )
    projections = root / ".agents/skills"
    projections.mkdir(parents=True, exist_ok=True)
    for name in names:
        projection = projections / name
        if not projection.exists() and not projection.is_symlink():
            projection.symlink_to(Path("../../skills") / name)


def _materialize_phase_bundles(
    root: Path, phase_ids: list[str], plan: dict[str, Any]
) -> None:
    lifecycle = plan["closure_contracts"]["actual_lifecycle"]
    relative = lifecycle["phase_history_manifest"]
    destination = root / relative
    if not destination.exists():
        source = Path(__file__).parent.parent / "fixtures" / Path(relative).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    write(root / ".apg-virtual/history", "synthetic Git-object evidence.\n")
    history = load_phase_history(destination, root)
    by_id = {bundle["phase_id"]: bundle for bundle in history["bundles"]}
    for phase_id in phase_ids:
        bundle = by_id[phase_id]
        private_root = (root / bundle["private_index_path"]).parent
        if private_root.exists():
            shutil.rmtree(private_root)
        write(
            root / bundle["public_evaluation_path"],
            f"{phase_id} public evaluation history.\n",
        )
        write(root / bundle["exit_path"], f"{phase_id} exit history.\n")
        write(
            root / bundle["private_index_path"],
            f"# {phase_id} publication-excluded evidence index\n",
        )
        for record in bundle["private_record_paths"]:
            write(root / record, f"{phase_id} exact private history.\n")


def _write_absent_index(root: Path, plan: dict[str, Any]) -> None:
    write(
        root / plan["closure_contracts"]["candidate_decision"]["index_path"],
        "<!-- APG-CANDIDATE-STATE: "
        "css-language-profile absent -->\n\n"
        "APG_SYNTHETIC_OWNER narrative-adr-index rejected\n",
    )


def _write_actual_decision(
    root: Path, plan: dict[str, Any], status: str
) -> None:
    owner = next(
        item
        for item in plan["owners"]
        if item["owner_id"] == "candidate-decision-record"
    )
    decided = "" if status == "Proposed" else "- Decided in: APG62\n"
    write(
        root / owner["path"],
        "# ADR 0036: CSS Language Profile from Frozen Contract\n\n"
        f"- Status: {status}\n"
        "- Proposed in: APG61\n"
        f"{decided}\n"
        f"{CANDIDATE} lifecycle decision.\n",
    )
    write(
        root / plan["closure_contracts"]["candidate_decision"]["index_path"],
        "<!-- APG-CANDIDATE-STATE: "
        "css-language-profile absent -->\n\n"
        "- [`0036 — CSS Language Profile from Frozen Contract`]"
        "(2026/07/0036-css-language-profile-from-frozen-contract.md)\n"
        f"  — {status}\n",
    )


def materialize_actual_pre_authoring_absent(
    root: Path, manifest: dict[str, Any], plan: dict[str, Any]
) -> None:
    materialize_synthetic_state(root, manifest, plan, "rejected")
    decision = next(
        item
        for item in plan["owners"]
        if item["owner_id"] == "candidate-decision-record"
    )
    decision_path = root / decision["path"]
    if decision_path.exists() or decision_path.is_symlink():
        decision_path.unlink()
    _write_absent_index(root, plan)
    _materialize_integrated_baseline(root, plan)
    _materialize_phase_bundles(
        root,
        plan["closure_contracts"]["actual_lifecycle"]["foundation_history"],
        plan,
    )


def _materialize_authored_files(
    root: Path, source_root: Path, plan: dict[str, Any]
) -> None:
    paths = surface_paths()
    contract_relative = plan["closure_contracts"]["traceability"][
        "contract_path"
    ]
    with RepositoryPathContract(source_root) as repository:
        contract_bytes = repository.read_bytes(contract_relative)
    contract = json.loads(contract_bytes)
    contract_path = root / contract_relative
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_bytes(contract_bytes)
    write(
        root / paths["skill"],
        "---\n"
        f"name: {CANDIDATE}\n"
        "description: Disposable authored candidate.\n"
        "---\n\n"
        "<!-- APG-CLAUSE: CSS-FROZEN-CONTRACT -->\n",
    )
    write(
        root / paths["specification"],
        f"# {CANDIDATE}\n",
    )
    write_json(
        root / paths["contract_map"],
        {
            "schema_version": 2,
            "candidate_id": CANDIDATE,
            "contract_revision": "APG60A",
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "semantic_boundary": SEMANTIC_BOUNDARY,
            "cases": _traceability_rows(contract),
        },
    )


def materialize_actual_authored_proposed(
    root: Path,
    source_root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    materialize_actual_pre_authoring_absent(root, manifest, plan)
    _materialize_authored_files(root, source_root, plan)
    _write_actual_decision(root, plan, "Proposed")
    _materialize_phase_bundles(
        root,
        plan["closure_contracts"]["actual_lifecycle"]["authoring_history"],
        plan,
    )


def materialize_actual_rejected_preserved(
    root: Path, manifest: dict[str, Any], plan: dict[str, Any]
) -> None:
    materialize_actual_pre_authoring_absent(root, manifest, plan)
    _write_actual_decision(root, plan, "Rejected")
    lifecycle = plan["closure_contracts"]["actual_lifecycle"]
    _materialize_phase_bundles(
        root,
        [*lifecycle["authoring_history"], *lifecycle["terminal_history"]],
        plan,
    )
