#!/usr/bin/env python3
"""Integration tests for bin/apg-check-release-matrix."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

if str(Path(__file__).resolve().parents[6]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[6]))
if str(Path(__file__).resolve().parents[6] / "testing/release") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[6] / "testing/release"))

from src.test.apg_test_support import repository_root
import check_release_matrix as checker

REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-check-release-matrix"
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


class APGCheckReleaseMatrixTests(unittest.TestCase):
    """Exercise the release matrix validation command and engine."""

    def test_launcher_default_enforces_repository_surface(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(COMMAND)],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        present = [(REPOSITORY_ROOT / path).is_file() for path in PRIVATE_RELEASE_PATHS]
        if not any(present):
            self.assertEqual(proc.returncode, 1)
            self.assertIn("FAIL: Release readiness matrix validation failed:", proc.stderr)
            for error in PRIVATE_MISSING_ERRORS:
                self.assertIn(f"  - {error}\n", proc.stderr)
            return
        self.assertTrue(all(present), "Incomplete private release assets")
        self.assertEqual(proc.returncode, 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")
        self.assertIn("PASS: Release readiness matrix valid (38 rows checked)", proc.stdout)
        self.assertIn("REG-R: 13/13", proc.stdout)
        self.assertIn("REG-P: 13/13", proc.stdout)
        self.assertIn("F-Traceability: 12/12", proc.stdout)

    def test_validator_fails_closed_on_missing_fixture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="matrix-test-") as td:
            bad_matrix = Path(td) / "matrix.json"
            data = json.loads((REPOSITORY_ROOT / "testing/release/release-readiness-matrix.json").read_text(encoding="utf-8"))
            # Corrupt one row by pointing fixture to non-existent function
            public_test = "src/test/unit/python/agentic-praxis-grimoire/testing/release/check_release_matrix.unit.test.py"
            row = data["reg_r_cases"][0]
            row.update(
                owning_code="testing/release/check_release_matrix.py",
                test_path=public_test,
                test_command=f"python3 -m pytest --import-mode=importlib {public_test}",
                disposition="public",
                public_evidence="testing/release/public-projection-contract.md#reg-r1",
                fixture="test_non_existent_function_name",
            )
            bad_matrix.write_text(json.dumps(data), encoding="utf-8")

            res = checker.validate_matrix(bad_matrix, REPOSITORY_ROOT)
            self.assertEqual(res["status"], "failed")
            self.assertEqual(
                [error for error in res["errors"] if error.startswith("REG-R row REG-R1 ")],
                [f"REG-R row REG-R1 fixture function 'test_non_existent_function_name' not found in {public_test}"],
            )


if __name__ == "__main__":
    unittest.main()
