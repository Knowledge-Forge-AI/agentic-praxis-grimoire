"""Real CLI boundary tests for bin/apg-test."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-test"


def run_command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get(
        "PATH", ""
    )
    return subprocess.run(
        [str(COMMAND), *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_help_exposes_three_suites_and_worker_override() -> None:
    result = run_command("--help")
    assert result.returncode == 0
    assert "{unit,integration,unit-integration}" in result.stdout
    assert "--workers WORKERS" in result.stdout


def test_invalid_worker_count_fails_before_test_execution() -> None:
    result = run_command("unit", "--workers", "0")
    assert result.returncode == 1
    assert "workers must be between 1 and 64" in result.stderr


def test_standalone_unit_runner_executes_real_pytest_xdist_and_coverage_boundary() -> None:
    result = run_command("unit", "--workers", "2")
    assert result.returncode == 0, result.stderr
    assert "passed" in result.stdout
    assert "PASS unit: statements" in result.stdout
    assert "branches" in result.stdout


def test_missing_child_contribution_fixture_fails_the_real_runner() -> None:
    result = run_command(
        "unit",
        "--workers",
        "2",
        "--verify-failure-mode",
        "missing-child",
    )
    assert result.returncode == 1
    assert "required Python child has no observable coverage contribution" in result.stderr
    assert "injected-missing-child" in result.stderr


def test_real_worker_crash_fixture_fails_without_restart() -> None:
    result = run_command(
        "unit",
        "--workers",
        "2",
        "--verify-failure-mode",
        "worker-crash",
    )
    assert result.returncode == 1
    assert "worker" in result.stderr.lower()
    assert "worker-complete set is incomplete" in result.stderr
