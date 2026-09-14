"""Integration tests for APGR pre-review check assembly and target binding."""

from __future__ import annotations

from pathlib import Path

from tools.ci.pre_review_checks import _command_attestation, checks
from tools.ci.pre_review_records import POLICY_CHECKS


def test_checks_assemble_real_environment_and_workflows(tmp_path: Path) -> None:
    all_checks = checks(tmp_path / "scratch")
    check_map = {c.name: c for c in all_checks}

    # Ensure all policy checks are present
    for policy_name in POLICY_CHECKS:
        assert policy_name in check_map, f"missing expected pre-review check: {policy_name}"

    # Actionlint must target real workflows and never be empty invocation
    actionlint = check_map["actionlint"]
    assert len(actionlint.command) >= 4
    workflow_args = actionlint.command[3:]
    assert any("public-pr.yml" in arg for arg in workflow_args)
    assert any("release.yml" in arg for arg in workflow_args)

    # Hadolint must target the maintained Dockerfile fixture and never be empty invocation
    hadolint = check_map["hadolint"]
    assert len(hadolint.command) >= 4
    assert any("Dockerfile" in arg for arg in hadolint.command[3:])

    # Every check must have valid non-empty command and exist under valid cwd
    for check in all_checks:
        assert check.command
        assert all(isinstance(part, str) and part for part in check.command)
        assert check.cwd.is_absolute()
        assert check.cwd.is_dir()


def test_checks_with_real_tool_root_materializes_paths(tmp_path: Path) -> None:
    tool_root = tmp_path / "tools"
    all_checks = checks(tmp_path / "scratch", tool_root=tool_root)
    check_map = {c.name: c for c in all_checks}

    assert check_map["actionlint"].command[0] == str(tool_root / "bin/actionlint")
    assert check_map["zizmor"].command[0] == str(tool_root / "bin/zizmor")
    assert check_map["betterleaks"].command[0] == str(tool_root / "bin/betterleaks")
    assert check_map["semgrep"].command[0] == str(tool_root / "python/bin/semgrep")
    assert check_map["malskanner"].command[0] == str(tool_root / "node/node_modules/.bin/malskanner")


def test_command_attestation_end_to_end_across_all_checks(tmp_path: Path) -> None:
    tool_root = tmp_path / "tools"
    tool_root.mkdir(parents=True, exist_ok=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    all_checks = checks(scratch, tool_root=tool_root)

    for check in all_checks:
        attestation = _command_attestation(check, tool_root)
        assert isinstance(attestation, str)
        assert attestation
        # Ensure local home directory is never leaked into attestation
        assert str(Path.home()) not in attestation
