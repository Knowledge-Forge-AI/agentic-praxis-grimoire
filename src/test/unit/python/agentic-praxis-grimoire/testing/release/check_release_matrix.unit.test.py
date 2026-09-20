"""Unit tests for testing/release/check_release_matrix.py validation engine."""

from __future__ import annotations

import json
from pathlib import Path
import sys

if str(Path(__file__).resolve().parents[7]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[7]))
if str(Path(__file__).resolve().parents[7] / "testing/release") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[7] / "testing/release"))

import check_release_matrix as checker

REPO_ROOT = Path(__file__).resolve().parents[7]
PRIVATE_RELEASE_PATHS = (
    "private/releases/v0.12.0/test_hosted_ci_regressions.py",
    "private/releases/v0.12.0/test_release_operator_dry_runs.py",
    "private/releases/v0.12.0/release_operator/channels/github_release.py",
)
PRIVATE_MISSING_ERRORS = (
    f"REG-R row REG-R1 test_path does not exist: {PRIVATE_RELEASE_PATHS[0]}",
    f"REG-P row REG-P1 test_path does not exist: {PRIVATE_RELEASE_PATHS[1]}",
    f"REG-P row REG-P1 owning_code does not exist: {PRIVATE_RELEASE_PATHS[2]}",
)


def test_private_mode_enforces_repository_surface() -> None:
    res = checker.validate_matrix(checker.MATRIX_PATH, REPO_ROOT, mode="private")
    present = [(REPO_ROOT / path).is_file() for path in PRIVATE_RELEASE_PATHS]
    if any(present):
        assert all(present), "Incomplete private release assets"
        assert res["status"] == "passed", f"Validation errors: {res.get('errors')}"
    else:
        assert res["status"] == "failed"
        for error in PRIVATE_MISSING_ERRORS:
            assert error in res["errors"]
    assert res["summary"]["total_rules"] == 38
    assert res["summary"]["reg_r_count"] == 13
    assert res["summary"]["reg_p_count"] == 13
    assert res["summary"]["f_count"] == 12
    assert res["summary"]["private_only_count"] == 26
    assert res["summary"]["mode"] == "private"


def test_public_mode_passes_on_repository_matrix() -> None:
    res = checker.validate_matrix(checker.MATRIX_PATH, REPO_ROOT, mode="public")
    assert res["status"] == "passed", f"Validation errors: {res.get('errors')}"
    assert res["summary"]["total_rules"] == 38
    assert res["summary"]["private_only_count"] == 26
    assert res["summary"]["mode"] == "public"


def test_fails_closed_on_invalid_mode(tmp_path: Path) -> None:
    res = checker.validate_matrix(checker.MATRIX_PATH, REPO_ROOT, mode="invalid_mode")
    assert res["status"] == "failed"
    assert any("Invalid mode" in err for err in res["errors"])


def test_fails_closed_on_missing_disposition(tmp_path: Path) -> None:
    bad_matrix = tmp_path / "matrix.json"
    data = json.loads(checker.MATRIX_PATH.read_text(encoding="utf-8"))
    del data["reg_r_cases"][0]["disposition"]
    bad_matrix.write_text(json.dumps(data), encoding="utf-8")

    # In private mode
    res_private = checker.validate_matrix(bad_matrix, REPO_ROOT, mode="private")
    assert res_private["status"] == "failed"
    assert any("missing required field: disposition" in err for err in res_private["errors"])

    # In public mode (fail-closed, no silent missing skip)
    res_public = checker.validate_matrix(bad_matrix, REPO_ROOT, mode="public")
    assert res_public["status"] == "failed"
    assert any("missing required field: disposition" in err for err in res_public["errors"])


def test_fails_closed_on_invalid_disposition(tmp_path: Path) -> None:
    bad_matrix = tmp_path / "matrix.json"
    data = json.loads(checker.MATRIX_PATH.read_text(encoding="utf-8"))
    data["reg_p_cases"][0]["disposition"] = "unsupported_disposition_value"
    bad_matrix.write_text(json.dumps(data), encoding="utf-8")

    res = checker.validate_matrix(bad_matrix, REPO_ROOT, mode="private")
    assert res["status"] == "failed"
    assert any("invalid disposition" in err for err in res["errors"])


def test_private_mode_fails_closed_on_missing_disk_file(tmp_path: Path) -> None:
    bad_matrix = tmp_path / "matrix.json"
    data = json.loads(checker.MATRIX_PATH.read_text(encoding="utf-8"))
    data["reg_r_cases"][0]["owning_code"] = "nonexistent/file/path.sh"
    bad_matrix.write_text(json.dumps(data), encoding="utf-8")

    res = checker.validate_matrix(bad_matrix, REPO_ROOT, mode="private")
    assert res["status"] == "failed"
    assert any("owning_code does not exist: nonexistent/file/path.sh" in err for err in res["errors"])


def test_private_mode_fails_closed_on_missing_fixture(tmp_path: Path) -> None:
    bad_matrix = tmp_path / "matrix.json"
    data = json.loads(checker.MATRIX_PATH.read_text(encoding="utf-8"))
    public_test = "src/test/unit/python/agentic-praxis-grimoire/testing/release/check_release_matrix.unit.test.py"
    row = data["reg_r_cases"][0]
    row.update(
        owning_code="testing/release/check_release_matrix.py",
        test_path=public_test,
        test_command=f"python3 -m pytest --import-mode=importlib {public_test}",
        disposition="public",
        public_evidence="testing/release/public-projection-contract.md#reg-r1",
        fixture="test_non_existent_fixture_function",
    )
    bad_matrix.write_text(json.dumps(data), encoding="utf-8")

    res = checker.validate_matrix(bad_matrix, REPO_ROOT, mode="private")
    assert res["status"] == "failed"
    assert [error for error in res["errors"] if error.startswith("REG-R row REG-R1 ")] == [
        f"REG-R row REG-R1 fixture function 'test_non_existent_fixture_function' not found in {public_test}"
    ]


def test_public_mode_fails_closed_on_private_publication_leak(tmp_path: Path) -> None:
    bad_matrix = tmp_path / "matrix.json"
    data = json.loads(checker.MATRIX_PATH.read_text(encoding="utf-8"))
    # Mark a row as public while it references a private path
    data["reg_p_cases"][0]["disposition"] = "public"
    bad_matrix.write_text(json.dumps(data), encoding="utf-8")

    res = checker.validate_matrix(bad_matrix, REPO_ROOT, mode="public")
    assert res["status"] == "failed"
    assert any("public row references private path" in err for err in res["errors"])


def test_public_mode_fails_closed_if_public_row_missing_on_disk(tmp_path: Path) -> None:
    bad_matrix = tmp_path / "matrix.json"
    data = json.loads(checker.MATRIX_PATH.read_text(encoding="utf-8"))
    # Public row pointing to missing file
    data["reg_r_cases"][0]["disposition"] = "public"
    data["reg_r_cases"][0]["owning_code"] = "tools/ci/nonexistent_public_file.py"
    data["reg_r_cases"][0]["test_path"] = "tools/ci/nonexistent_test.py"
    bad_matrix.write_text(json.dumps(data), encoding="utf-8")

    res = checker.validate_matrix(bad_matrix, REPO_ROOT, mode="public")
    assert res["status"] == "failed"
    assert any("owning_code does not exist: tools/ci/nonexistent_public_file.py" in err for err in res["errors"])


def test_public_mode_validates_public_traceability(tmp_path: Path) -> None:
    bad_matrix = tmp_path / "matrix.json"
    data = json.loads(checker.MATRIX_PATH.read_text(encoding="utf-8"))
    data["f_traceability"][0]["mapped_regression_ids"] = ["REG-UNKNOWN-99"]
    bad_matrix.write_text(json.dumps(data), encoding="utf-8")

    res = checker.validate_matrix(bad_matrix, REPO_ROOT, mode="public")
    assert res["status"] == "failed"
    assert any("references unknown regression ID: REG-UNKNOWN-99" in err for err in res["errors"])


def test_parse_args_supports_mode_and_public_aliases() -> None:
    args_default = checker.parse_args([])
    assert args_default.mode == "private"
    assert not args_default.public

    args_public_flag = checker.parse_args(["--public"])
    assert args_public_flag.public

    args_mode_public = checker.parse_args(["--mode", "public"])
    assert args_mode_public.mode == "public"

    args_mode_proj = checker.parse_args(["--mode", "public-projection"])
    assert args_mode_proj.mode == "public-projection"


def test_public_evidence_binding_is_required(tmp_path: Path) -> None:
    data = json.loads(checker.MATRIX_PATH.read_text(encoding="utf-8"))
    data["reg_p_cases"][0]["public_evidence"] = "missing.md#reg-p1"
    matrix = tmp_path / "matrix.json"
    matrix.write_text(json.dumps(data), encoding="utf-8")
    for mode in ("private", "public"):
        result = checker.validate_matrix(matrix, REPO_ROOT, mode=mode)
        assert result["status"] == "failed"
        assert any("public evidence binding" in error for error in result["errors"])
