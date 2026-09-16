"""Integration tests for release readiness matrix private and public projection modes."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

if str(Path(__file__).resolve().parents[7]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[7]))

from tools.ci.pre_review_checks import checks

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


def test_full_private_check_enforces_repository_surface() -> None:
    checker_script = REPO_ROOT / "testing/release/check_release_matrix.py"
    proc = subprocess.run(
        [sys.executable, str(checker_script), "--mode", "private"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    present = [(REPO_ROOT / path).is_file() for path in PRIVATE_RELEASE_PATHS]
    if not any(present):
        assert proc.returncode == 1
        assert "FAIL: Release readiness matrix validation failed:" in proc.stderr
        for error in PRIVATE_MISSING_ERRORS:
            assert f"  - {error}\n" in proc.stderr
        return
    assert all(present), "Incomplete private release assets"
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert "PASS: Release readiness matrix valid (38 rows checked)" in proc.stdout
    assert "REG-R: 13/13" in proc.stdout
    assert "REG-P: 13/13" in proc.stdout
    assert "F-Traceability: 12/12" in proc.stdout


def test_public_mode_command_passes_on_repository() -> None:
    checker_script = REPO_ROOT / "testing/release/check_release_matrix.py"
    proc = subprocess.run(
        [sys.executable, str(checker_script), "--mode", "public"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert "PASS: Release readiness matrix valid (public projection mode: 38 rows checked)" in proc.stdout
    assert "REG-R: 13/13 (13 private-only disposition)" in proc.stdout
    assert "REG-P: 13/13 (13 private-only disposition)" in proc.stdout
    assert "F-Traceability: 12/12" in proc.stdout


def _build_disposable_public_checkout(target_root: Path) -> Path:
    """Materialize a clean disposable public checkout fixture containing only public files."""
    public_paths = [
        "testing/release/release-readiness-matrix.json",
        "testing/release/check_release_matrix.py",
        "testing/release/public-projection-contract.md",
        "tools/ci/bootstrap_static.sh",
        "tools/ci/qualify_packages.sh",
        "libexec/apg_skill_topology.py",
        "tools/ci/codeql_policy.py",
        "internal/cli/skills.go",
        "release/ci/matrix_receipts.py",
        "libexec/apg_staging_correction.py",
        "tools/ci/file_length_policy.py",
        "src/test/fixtures/apg123-browser-ui/supervisor.spec.js",
        "libexec/apg_test.py",
        "tools/ci/pre_review_evaluation.py",
        ".github/workflows/release.yml",
        "libexec/apg_python_distribution.py",
        "libexec/apg_public_release.py",
    ]
    for rel in public_paths:
        src = REPO_ROOT / rel
        assert src.exists(), f"Source path missing: {rel}"
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    assert not (target_root / "private").exists(), "Disposable public checkout must not have private directory"
    return target_root


def test_disposable_public_checkout_contract_passes(tmp_path: Path) -> None:
    disposable = _build_disposable_public_checkout(tmp_path / "disposable_public")
    checker_script = disposable / "testing/release/check_release_matrix.py"
    matrix_file = disposable / "testing/release/release-readiness-matrix.json"

    proc = subprocess.run(
        [
            sys.executable,
            str(checker_script),
            "--mode",
            "public",
            "--matrix-path",
            str(matrix_file),
            "--repo-root",
            str(disposable),
        ],
        cwd=disposable,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}"
    assert "PASS: Release readiness matrix valid (public projection mode: 38 rows checked)" in proc.stdout
    assert "REG-R: 13/13 (13 private-only disposition)" in proc.stdout
    assert "REG-P: 13/13 (13 private-only disposition)" in proc.stdout
    assert "F-Traceability: 12/12" in proc.stdout


def test_disposable_public_checkout_fails_strict_private_mode(tmp_path: Path) -> None:
    disposable = _build_disposable_public_checkout(tmp_path / "disposable_public")
    checker_script = disposable / "testing/release/check_release_matrix.py"
    matrix_file = disposable / "testing/release/release-readiness-matrix.json"

    proc = subprocess.run(
        [
            sys.executable,
            str(checker_script),
            "--mode",
            "private",
            "--matrix-path",
            str(matrix_file),
            "--repo-root",
            str(disposable),
        ],
        cwd=disposable,
        capture_output=True,
        text=True,
        check=False,
    )
    # Must fail closed in private mode because private files are absent
    assert proc.returncode == 1
    assert "FAIL: Release readiness matrix validation failed:" in proc.stderr
    assert "test_hosted_ci_regressions.py" in proc.stderr
    assert "test_release_operator_dry_runs.py" in proc.stderr


def test_disposable_public_checkout_fails_closed_when_disposition_is_missing(tmp_path: Path) -> None:
    disposable = _build_disposable_public_checkout(tmp_path / "disposable_public")
    checker_script = disposable / "testing/release/check_release_matrix.py"
    matrix_file = disposable / "testing/release/release-readiness-matrix.json"

    # Remove disposition from REG-R1
    data = json.loads(matrix_file.read_text(encoding="utf-8"))
    del data["reg_r_cases"][0]["disposition"]
    matrix_file.write_text(json.dumps(data), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(checker_script),
            "--mode",
            "public",
            "--matrix-path",
            str(matrix_file),
            "--repo-root",
            str(disposable),
        ],
        cwd=disposable,
        capture_output=True,
        text=True,
        check=False,
    )
    # Must fail closed without silent missing skip
    assert proc.returncode == 1
    assert "missing required field: disposition" in proc.stderr


def test_pre_review_wiring_for_hosted_vs_local(tmp_path: Path, monkeypatch) -> None:
    # 1. Local environment with private directory
    selected_local = {c.name: c for c in checks(tmp_path / "scratch")}
    assert "release-matrix" in selected_local
    assert "--mode" not in selected_local["release-matrix"].command

    # 2. Hosted / public projection environment without private directory
    empty_root = tmp_path / "public_root"
    empty_root.mkdir()
    monkeypatch.setattr("tools.ci.pre_review_checks.ROOT", empty_root)

    selected_hosted = {c.name: c for c in checks(tmp_path / "scratch")}
    assert "release-matrix" in selected_hosted
    assert selected_hosted["release-matrix"].command[-1] == "testing/release/check_release_matrix.py"


def test_static_stack_explicit_public_projection(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools/ci/run_pre_review.py"),
         "--check", "release-matrix", "--public-projection", "--evidence-dir", str(evidence)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "public projection mode" in (evidence / "release-matrix.log").read_text()


def test_public_evidence_section_cannot_disappear(tmp_path: Path) -> None:
    root = _build_disposable_public_checkout(tmp_path / "projection")
    evidence = root / "testing/release/public-projection-contract.md"
    evidence.write_text(evidence.read_text().replace("## REG-P1\n", "## Removed\n"))
    result = subprocess.run(
        [sys.executable, str(root / "testing/release/check_release_matrix.py"), "--mode", "public"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert "missing public evidence section" in result.stdout + result.stderr
