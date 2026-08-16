"""Real CLI boundary tests for bin/apg-test."""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-test"
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_test  # noqa: E402


def run_command(
    *arguments: str, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy() if environment is None else environment.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get(
        "PATH", ""
    )
    worker_root = Path(environment["TMPDIR"]).resolve(strict=True)
    with tempfile.TemporaryDirectory(
        prefix="apg-nested-pytest-", dir=worker_root.parent
    ) as pytest_root:
        environment["PYTEST_ADDOPTS"] = f"--basetemp={shlex.quote(pytest_root)}"
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


def test_typescript_preflight_and_cli_reject_missing_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert apg_test.validate_typescript_compiler(REPOSITORY_ROOT) == "Version 7.0.2"
    monkeypatch.delenv("APG_TYPESCRIPT_TSC")
    with pytest.raises(apg_test.ToolError, match="test prerequisite is unavailable"):
        apg_test.validate_typescript_compiler(REPOSITORY_ROOT)
    environment = os.environ.copy()
    result = run_command("unit", environment=environment)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        "apg-test: TypeScript test prerequisite is unavailable: set "
        "APG_TYPESCRIPT_TSC to an absolute executable typescript@7.0.2 tsc "
        "installed outside the repository checkout\n"
    )


def test_typescript_preflight_rejects_unsafe_or_wrong_compiler_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiler = Path(os.environ["APG_TYPESCRIPT_TSC"])
    link = tmp_path / "tsc-link"
    link.symlink_to(compiler)
    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(link))
    with pytest.raises(apg_test.ToolError, match="absolute regular executable"):
        apg_test.validate_typescript_compiler(REPOSITORY_ROOT)

    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(COMMAND))
    with pytest.raises(apg_test.ToolError, match="outside the repository checkout"):
        apg_test.validate_typescript_compiler(REPOSITORY_ROOT)

    wrong = tmp_path / "wrong-tsc"
    wrong.write_text("#!/bin/sh\nprintf 'Version 7.0.1\\n'\n", encoding="utf-8")
    wrong.chmod(0o700)
    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(wrong))
    with pytest.raises(apg_test.ToolError, match="version mismatch"):
        apg_test.validate_typescript_compiler(REPOSITORY_ROOT)


def test_standalone_unit_runner_executes_real_pytest_xdist_and_coverage_boundary() -> None:
    result = run_command("unit", "--workers", "2")
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"
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
    assert "required Python child has no observable coverage contribution" in result.stderr, (
        f"{result.stderr}\n{result.stdout}"
    )
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
