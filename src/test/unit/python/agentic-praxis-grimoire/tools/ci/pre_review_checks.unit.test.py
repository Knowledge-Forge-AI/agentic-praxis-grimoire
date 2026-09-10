"""Unit contracts for static-check ownership and sanitized attestations."""

from __future__ import annotations

from pathlib import Path

from tools.ci.pre_review_checks import _command_attestation, checks
from tools.ci.pre_review_records import ROOT, Check


def test_missing_pinned_tool_does_not_fall_back_to_ambient_binary(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.ci.pre_review_checks.shutil.which", lambda name: "/ambient/" + name)
    selected = {item.name: item for item in checks(tmp_path / "scratch", tmp_path / "tools")}
    assert selected["actionlint"].command[0] == str(tmp_path / "tools/bin/actionlint")
    assert selected["semgrep"].command[0] == str(tmp_path / "tools/python/bin/semgrep")
    assert selected["malskanner"].command[0] == str(tmp_path / "tools/node/node_modules/.bin/malskanner")


def test_command_attestation_redacts_unknown_absolute_external_paths() -> None:
    check = Check(
        "external",
        ("/opt/external-user/Library/Python/bin/pip-audit", "--format", "json"),
    )
    attestation = _command_attestation(check, None)
    assert "/opt/external-user" not in attestation
    assert "<external>/pip-audit" in attestation


def test_betterleaks_covers_the_complete_public_source_root_with_redaction() -> None:
    betterleaks = next(check for check in checks(Path(".")) if check.name == "betterleaks")

    assert betterleaks.command[1:] == (
        "dir",
        ".",
        "--no-banner",
        "--redact=100",
        "--report-format=json",
        "--report-path=-",
    )
    assert betterleaks.cwd.is_absolute()


def test_hadolint_retains_the_concrete_test_fixture_and_finding_exit() -> None:
    hadolint = next(check for check in checks(Path(".")) if check.name == "hadolint")

    assert "hotspot/testdata/classification/Dockerfile" in hadolint.command
    assert "--no-fail" not in hadolint.command


def test_zizmor_keeps_collection_and_tool_failures_distinct() -> None:
    zizmor = next(check for check in checks(Path(".")) if check.name == "zizmor")

    assert "--strict-collection" in zizmor.command
    assert "--no-exit-codes" in zizmor.command


def test_bootstrap_static_manifest_subset_and_no_uv() -> None:
    bootstrap_script = (ROOT / "tools/ci/bootstrap_static.sh").read_text(encoding="utf-8")
    import re
    loop_match = re.search(r"for tool in (.*?); do", bootstrap_script)
    assert loop_match is not None, "bootstrap_static.sh missing tool loop"
    looped_tools = loop_match.group(1).split()

    assert "uv" not in looped_tools
    assert "uv" not in bootstrap_script.split()

    from tools.ci.bootstrap_tool import load_manifest
    manifest = load_manifest()
    manifest_tools = manifest.get("tools", {})
    assert "uv" not in manifest_tools

    for tool in looped_tools:
        assert tool in manifest_tools
        assert "assets" in manifest_tools[tool]
        assert "darwin-arm64" in manifest_tools[tool]["assets"]
        assert "linux-amd64" in manifest_tools[tool]["assets"]


def test_checks_fails_explicitly_when_workflow_targets_absent(tmp_path: Path, monkeypatch) -> None:
    import subprocess
    empty_workflows = tmp_path / ".github/workflows"
    empty_workflows.mkdir(parents=True)
    monkeypatch.setattr("tools.ci.pre_review_checks.ROOT", tmp_path)

    selected = {check.name: check for check in checks(tmp_path / "scratch")}
    assert "ruff" in selected  # Independent lanes remain available.
    result = subprocess.run(selected["actionlint"].command, capture_output=True, text=True)
    assert result.returncode == 2
    assert "required workflow targets absent" in result.stderr


def test_hadolint_absent_dockerfiles_explicit_justified_failure_never_empty_invocation(
    tmp_path: Path, monkeypatch
) -> None:
    import subprocess
    orig_run = subprocess.run
    def mock_run(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "git":
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return orig_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: [])

    selected = {item.name: item for item in checks(tmp_path / "scratch")}
    hadolint = selected["hadolint"]

    # Must never be empty invocation (i.e. hadolint --format json without dockerfiles)
    assert hadolint.command != ("hadolint", "--format", "json")
    assert "--format" not in hadolint.command

    # Must be an explicit justified failure command
    assert "hadolint: required Dockerfile targets absent" in hadolint.command[2]

    proc = subprocess.run(hadolint.command, capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    assert "required Dockerfile targets absent" in proc.stderr



def test_file_length_lane_executes_maintained_json_policy(tmp_path):
    selected = {check.name: check for check in checks(tmp_path)}
    assert "ruff" in selected
    check = selected["file-length"]
    assert check.command[1:] == ("tools/ci/file_length_policy.py", "--format", "json")
    assert check.policy == "file-length"
