"""Failing-first traceability semantics for APG60B."""
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

from apg_candidate_surface_contract import SurfaceContractError  # noqa: E402
from apg_candidate_surface_contract import load_removal_plan  # noqa: E402
from apg_candidate_lifecycle_fixture import (  # noqa: E402
    materialize_actual_retained,
    surface_paths,
)


CANDIDATE = "css-language-profile"
OWNER = {
    "owner_id": "candidate-contract-map",
    "path": "docs/specs/css-language-profile.contract-map.json",
}
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)


def _checker():
    module = importlib.import_module("apg_actual_retained_surface_contract")
    return module._assert_contract_map


def test_private_marker_scanner_does_not_embed_its_posix_user_prefix() -> None:
    module = importlib.import_module("apg_candidate_traceability_contract")
    marker = "/" "Users/"
    assert marker in module.PRIVATE_MARKERS
    assert marker not in Path(module.__file__).read_text(encoding="utf-8")


def _materialize(root: Path) -> Path:
    materialize_actual_retained(root, ROOT, PLAN)
    return root / surface_paths()["contract_map"]


def _assert_exact(root: Path) -> None:
    _checker()(
        root,
        OWNER,
        CANDIDATE,
        PLAN["closure_contracts"]["traceability"],
    )


def _write_map(root: Path, value: dict[str, object]) -> None:
    path = root / OWNER["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _legacy_map() -> dict[str, object]:
    return {
        "schema_version": 1,
        "candidate_id": CANDIDATE,
        "cases": [
            {
                "case_id": f"APG60-CSS-{index:03d}",
                "clause_ids": ["CSS-001"],
                "owner": "owner:css-language-profile",
                "required_response": ["apply"],
                "rollback_or_exception": "not-applicable",
            }
            for index in range(1, 61)
        ],
    }


def test_frozen_contract_rejects_symlinked_fixture_ancestor(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    _materialize(root)
    fixtures = root / "src/test/fixtures"
    external = tmp_path / "external-fixtures"
    fixtures.rename(external)
    fixtures.symlink_to(external, target_is_directory=True)

    with pytest.raises(SurfaceContractError, match="direct|ancestor"):
        _assert_exact(root)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("clause_ids", ["CSS-999"]),
        ("owner", "owner:banana"),
        ("required_response", ["totally-wrong"]),
        ("rollback_or_exception", "arbitrary-rollback"),
    ),
)
def test_legacy_syntactic_rows_do_not_satisfy_contract_exactness(
    tmp_path: Path, field: str, value: object
) -> None:
    contract_map = _legacy_map()
    contract_map["cases"][0][field] = value
    _write_map(tmp_path, contract_map)

    with pytest.raises(SurfaceContractError, match="candidate-contract-map"):
        _checker()(tmp_path, OWNER, CANDIDATE)


def test_contract_map_without_frozen_contract_sha_fails(tmp_path: Path) -> None:
    _write_map(tmp_path, _legacy_map())

    with pytest.raises(SurfaceContractError, match="candidate-contract-map"):
        _checker()(tmp_path, OWNER, CANDIDATE)


def test_exact_v2_map_and_clause_navigation_pass(tmp_path: Path) -> None:
    _materialize(tmp_path)
    _assert_exact(tmp_path)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("selected_owner", "banana"),
        ("required_actions", ["totally-wrong"]),
        ("required_actions", []),
        ("forbidden_actions", ["totally-wrong"]),
        ("rollback_required", True),
    ),
)
def test_v2_row_must_equal_frozen_case(
    tmp_path: Path, field: str, replacement: object
) -> None:
    path = _materialize(tmp_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if field == "rollback_required":
        replacement = not value["cases"][0][field]
    value["cases"][0][field] = replacement
    _write_map(tmp_path, value)

    with pytest.raises(SurfaceContractError, match="disagrees with contract"):
        _assert_exact(tmp_path)


def test_wrong_contract_sha_and_semantic_boundary_fail(tmp_path: Path) -> None:
    path = _materialize(tmp_path)
    original = json.loads(path.read_text(encoding="utf-8"))
    for field, replacement in (
        ("contract_sha256", "0" * 64),
        ("semantic_boundary", "proves candidate prose"),
    ):
        value = dict(original)
        value[field] = replacement
        _write_map(tmp_path, value)
        with pytest.raises(SurfaceContractError, match="identity"):
            _assert_exact(tmp_path)


def test_duplicate_json_key_fails_closed(tmp_path: Path) -> None:
    path = _materialize(tmp_path)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '"selected_owner": "css-language-profile"',
        '"selected_owner": "banana", '
        '"selected_owner": "css-language-profile"',
        1,
    )
    path.write_text(text, encoding="utf-8")

    with pytest.raises(SurfaceContractError, match="duplicate JSON key"):
        _assert_exact(tmp_path)


@pytest.mark.parametrize("mode", ("duplicate", "missing", "unreferenced"))
def test_clause_markers_are_unique_reachable_and_live(
    tmp_path: Path, mode: str
) -> None:
    _materialize(tmp_path)
    paths = surface_paths()
    leaf = tmp_path / paths["skill"]
    specification = tmp_path / paths["specification"]
    marker = "<!-- APG-CLAUSE: CSS-FROZEN-CONTRACT -->\n"
    if mode == "duplicate":
        specification.write_text(marker, encoding="utf-8")
    elif mode == "missing":
        leaf.write_text(
            leaf.read_text(encoding="utf-8").replace(marker, ""),
            encoding="utf-8",
        )
    else:
        specification.write_text(
            "<!-- APG-CLAUSE: CSS-UNREFERENCED -->\n",
            encoding="utf-8",
        )

    with pytest.raises(SurfaceContractError, match="clause"):
        _assert_exact(tmp_path)
