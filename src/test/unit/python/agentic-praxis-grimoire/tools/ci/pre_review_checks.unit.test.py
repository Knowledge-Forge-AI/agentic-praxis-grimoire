"""Unit contracts for static-check ownership and sanitized attestations."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

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


def test_bootstrap_static_pins_and_tomli_compatibility() -> None:
    text = (ROOT / "tools/ci/bootstrap_static.sh").read_text(encoding="utf-8")
    assert '"ruff==0.9.10"' in text
    assert '"mypy==1.15.0"' in text
    assert '"pip-audit==2.10.1"' in text
    assert '"semgrep==1.179.0"' in text
    assert '"tomli==2.4.1"' in text
    assert '"tomli==2.0.1"' not in text

    import re
    tomli_match = re.search(r"tomli==([0-9]+\.[0-9]+\.[0-9]+)", text)
    assert tomli_match is not None
    tomli_ver = tuple(int(x) for x in tomli_match.group(1).split("."))
    # pip-audit requires tomli >= 2.2.1
    assert tomli_ver >= (2, 2, 1)
    # The tomli 2.4 constraint was established for Semgrep 1.174.0.
    # Semgrep 1.179.0 resolver compatibility is an attended host gate.
    assert tomli_ver[:2] == (2, 4)
    assert tomli_ver[2] >= 0


def test_qualify_packages_prepares_python_work_root() -> None:
    text = (ROOT / "tools/ci/qualify_packages.sh").read_text(encoding="utf-8")
    assert 'mkdir -p "$pkg_root/python-work"' in text
    assert 'mkdir -p "$pkg_root/python"' not in text


def test_qualify_packages_clean_root_execution_to_builder_boundary(tmp_path: Path) -> None:
    """Execute qualify_packages.sh from clean RUNNER_TEMP to verify work-root creation up to builder boundary."""
    runner_temp = tmp_path / "runner_temp"
    runner_temp.mkdir()
    pkg_root = runner_temp / "apgr-packages"
    assert not pkg_root.exists()

    # Local recording builder script shadowing python3 on PATH
    mock_bin = tmp_path / "mock_bin"
    mock_bin.mkdir()
    intercept_log = tmp_path / "intercepted.log"
    mock_python = mock_bin / "python3"
    mock_python.write_text(
        f'#!/usr/bin/env bash\n'
        f'if [[ "$*" == *"bin/apg-build-python-release-bundle"* ]]; then\n'
        f'    echo "$*" > "{intercept_log}"\n'
        f'    exit 99\n'
        f'fi\n'
        f'exec "{sys.executable}" "$@"\n',
        encoding="utf-8",
    )
    mock_python.chmod(0o755)

    env = os.environ.copy()
    env["RUNNER_TEMP"] = str(runner_temp)
    env["GITHUB_WORKSPACE"] = str(ROOT)
    env["PATH"] = f"{mock_bin}:{env.get('PATH', '')}"

    res = subprocess.run(
        ["bash", str(ROOT / "tools/ci/qualify_packages.sh")],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 99
    assert intercept_log.is_file()
    assert "bin/apg-build-python-release-bundle" in intercept_log.read_text(encoding="utf-8")

    # Verify work roots created
    assert (pkg_root / "python-work").is_dir()
    assert (pkg_root / "npm-a").is_dir()
    assert (pkg_root / "npm-work-a").is_dir()
    assert (pkg_root / "npm-b").is_dir()
    assert (pkg_root / "npm-work-b").is_dir()

    # Verify output directories retain absent/empty semantics
    assert not (pkg_root / "python").exists()
    assert not (runner_temp / "deliverables").exists()


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


def test_checks_propagate_tool_root_to_mypy_and_ratchets(tmp_path: Path) -> None:
    tool_root = tmp_path / "tools"
    selected = {c.name: c for c in checks(tmp_path / "scratch", tool_root=tool_root)}

    mypy_cmd = selected["mypy"].command
    assert "--tool-root" in mypy_cmd
    tool_root_idx = mypy_cmd.index("--tool-root")
    assert mypy_cmd[tool_root_idx + 1] == str(tool_root)

    ratchet_cmd = selected["retained-python-ratchets"].command
    assert "--tool-root" in ratchet_cmd
    tool_root_idx = ratchet_cmd.index("--tool-root")
    assert ratchet_cmd[tool_root_idx + 1] == str(tool_root)


def test_checks_without_tool_root_are_rootless(tmp_path: Path) -> None:
    selected = {c.name: c for c in checks(tmp_path / "scratch", tool_root=None)}

    mypy_cmd = selected["mypy"].command
    assert "--tool-root" not in mypy_cmd

    ratchet_cmd = selected["retained-python-ratchets"].command
    assert "--tool-root" not in ratchet_cmd


def test_bootstrap_static_pip_direct_specifiers_equality_with_ci_requirements() -> None:
    import shlex
    from tools.ci.dependency_inventory import CI_REQUIREMENTS

    script_text = (ROOT / "tools/ci/bootstrap_static.sh").read_text(encoding="utf-8")
    pip_line = next(line for line in script_text.splitlines() if "pip install" in line)

    tokens = shlex.split(pip_line)
    install_idx = tokens.index("install")
    args = tokens[install_idx + 1:]

    direct_specifiers = []
    requirements_files = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-r":
            i += 1
            requirements_files.append(args[i])
        elif arg.startswith("-r"):
            requirements_files.append(arg[2:])
        elif arg.startswith("-"):
            pass
        else:
            direct_specifiers.append(arg)
        i += 1

    assert requirements_files == ["requirements/test.txt"]
    assert tuple(direct_specifiers) == CI_REQUIREMENTS


def test_semgrep_cross_site_identity() -> None:
    """Verify exact Semgrep 1.179.0 identity across bootstrap, registry, and CI_REQUIREMENTS."""
    import re
    from tools.ci.bootstrap_tool import load_manifest
    from tools.ci.dependency_inventory import CI_REQUIREMENTS

    # 1. tools/ci/bootstrap_static.sh
    bootstrap_text = (ROOT / "tools/ci/bootstrap_static.sh").read_text(encoding="utf-8")
    semgrep_match = re.search(r'"semgrep==([^"]+)"', bootstrap_text)
    assert semgrep_match is not None, "semgrep pin missing from bootstrap_static.sh"
    bootstrap_version = semgrep_match.group(1)
    assert bootstrap_version == "1.179.0"

    # 2. tools/ci/pre_review_tools.json (registry)
    manifest = load_manifest()
    semgrep_tool = manifest.get("tools", {}).get("semgrep", {})
    manifest_version = semgrep_tool.get("version")
    manifest_pin = semgrep_tool.get("immutable_pin")
    assert manifest_version == "1.179.0"
    assert manifest_pin == "exact direct pin semgrep==1.179.0"

    # 3. tools/ci/dependency_inventory.py (CI_REQUIREMENTS)
    semgrep_ci_req = next((req for req in CI_REQUIREMENTS if req.startswith("semgrep==")), None)
    assert semgrep_ci_req is not None, "semgrep missing from CI_REQUIREMENTS"
    ci_req_version = semgrep_ci_req.split("==")[1]
    assert ci_req_version == "1.179.0"

    # Exact cross-site identity across all three maintained identities
    assert bootstrap_version == manifest_version == ci_req_version == "1.179.0"
