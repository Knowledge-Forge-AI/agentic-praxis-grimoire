"""Integration tests for public-pr workflow guards, actions pins, and execution simulation."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tools.ci.ci_topology import validate_all_workflows
from tools.ci.workflow_model import parse_yaml_or_json

ROOT = Path(__file__).resolve().parents[7]
WORKFLOW_PATH = ROOT / ".github/workflows/public-pr.yml"
RELEASE_WORKFLOW_PATH = ROOT / ".github/workflows/release.yml"

SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _guard_script() -> str:
    doc = parse_yaml_or_json(WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = doc["jobs"]["guard"]["steps"]
    for step in steps:
        if step.get("name") == "Verify repository and pull request boundary":
            return step["run"]
    raise RuntimeError("could not find guard script in workflow")


def test_public_pr_guard_passes_on_valid_inputs(tmp_path: Path) -> None:
    script = _guard_script()
    env = {
        "PATH": "/bin:/usr/bin:/usr/local/bin",
        "RUNNER_TEMP": str(tmp_path),
        "ACTUAL_REPO": "Knowledge-Forge-AI/agentic-praxis-grimoire",
        "ACTUAL_REPO_ID": "1306002537",
        "BASE_REF": "main",
        "HEAD_REF": "staging",
        "HEAD_REPO": "Knowledge-Forge-AI/agentic-praxis-grimoire",
        "GITHUB_SHA": "1234567890abcdef1234567890abcdef12345678",
    }
    # Run in bash from repo root
    res = subprocess.run(["bash", "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"Guard failed unexpectedly: {res.stderr}"


@pytest.mark.parametrize(
    ("override_key", "override_value", "expected_err"),
    [
        ("ACTUAL_REPO", "attacker/agentic-praxis-grimoire", "Unexpected repo"),
        ("ACTUAL_REPO_ID", "99999999", "Unexpected repo ID"),
        ("BASE_REF", "staging", "PR must target main"),
        ("HEAD_REF", "feature-branch", "PR must originate from staging"),
        ("HEAD_REPO", "forked-user/agentic-praxis-grimoire", "Forked PR forbidden"),
    ],
)
def test_public_pr_guard_refuses_invalid_inputs(
    override_key: str, override_value: str, expected_err: str
) -> None:
    script = _guard_script()
    env = {
        "PATH": "/bin:/usr/bin:/usr/local/bin",
        "ACTUAL_REPO": "Knowledge-Forge-AI/agentic-praxis-grimoire",
        "ACTUAL_REPO_ID": "1306002537",
        "BASE_REF": "main",
        "HEAD_REF": "staging",
        "HEAD_REPO": "Knowledge-Forge-AI/agentic-praxis-grimoire",
        "GITHUB_SHA": "1234567890abcdef1234567890abcdef12345678",
    }
    env[override_key] = override_value
    res = subprocess.run(["bash", "-c", script], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    assert res.returncode != 0
    assert expected_err in (res.stderr + res.stdout)


def test_all_action_uses_in_public_pr_are_pinned_to_sha() -> None:
    doc = parse_yaml_or_json(WORKFLOW_PATH.read_text(encoding="utf-8"))
    for job_name, job in doc.get("jobs", {}).items():
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses:
                action, _, ref = uses.partition("@")
                assert ref, f"Step in {job_name} has unpinned action: {uses}"
                assert SHA_PATTERN.match(ref), f"Action {action} in {job_name} not pinned to 40-char SHA: {ref}"


def test_all_shipped_workflows_structural_assertion() -> None:
    # 1. public-pr.yml structural assertion
    doc_pr = parse_yaml_or_json(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert doc_pr["name"] == "public-pr"
    assert isinstance(doc_pr.get("jobs"), dict)
    assert doc_pr.get("permissions") == {"contents": "read"}
    assert "pull_request" in doc_pr.get("on", {})
    assert "public-pr-gate" in doc_pr["jobs"]
    assert not {"nix", "package", "sbom-and-vulnerability"} & set(doc_pr["jobs"])
    native = parse_yaml_or_json((ROOT / ".github/workflows/native-qualification.yml").read_text())
    assert {native["jobs"][name]["runs-on"] for name in (
        "native-darwin-arm64", "native-linux-x64", "native-linux-arm64"
    )} == {"macos-15", "ubuntu-24.04", "ubuntu-24.04-arm"}

    # 2. release.yml structural assertion
    doc_rel = parse_yaml_or_json(RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert doc_rel["name"] == "Verify published release boundary"
    assert isinstance(doc_rel.get("jobs"), dict)
    assert doc_rel.get("permissions") == {}
    assert "release" in doc_rel.get("on", {})
    assert "verify" in doc_rel["jobs"]

    # 3. Structural and topology validation via existing ci_topology tool
    assert validate_all_workflows() == []


def test_release_workflow_is_read_only_and_cannot_publish_packages() -> None:
    doc = parse_yaml_or_json(RELEASE_WORKFLOW_PATH.read_text())
    steps = doc["jobs"]["verify"]["steps"]
    assert [step["name"] for step in steps] == [
        "Check out trusted repository",
        "Verify published release boundary",
    ]
    checkout_step = steps[0]
    assert checkout_step["uses"] == "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    assert checkout_step["with"]["persist-credentials"] is False

    verify_step = steps[1]
    assert "tools/ci/release_boundary.py verify-published" in verify_step["run"]
    assert verify_step["env"] == {"GH_TOKEN": "${{ github.token }}"}
    assert "uses" not in verify_step
    assert "environment" not in doc["jobs"]["verify"]
    assert "id-token" not in doc["jobs"]["verify"]["permissions"]


def test_native_failure_diagnostics_upload_is_bound_to_failed_qualify() -> None:
    doc = parse_yaml_or_json((ROOT / ".github/workflows/native-qualification.yml").read_text())
    for lane in ("native-darwin-arm64", "native-linux-x64", "native-linux-arm64"):
        steps = doc["jobs"][lane]["steps"]
        qualify = next(step for step in steps if step.get("id") == "qualify")
        assert '--diagnostics "$RUNNER_TEMP/lane-diagnostics"' in qualify["run"]
        uploads = [step for step in steps if step.get("with", {}).get("name") == f"{lane}-failure-diagnostics"]
        assert len(uploads) == 1
        upload = uploads[0]
        assert steps.index(upload) == steps.index(qualify) + 1
        assert upload["if"] == "${{ failure() && steps.qualify.outcome == 'failure' }}"
        assert upload["uses"] == "actions/upload-artifact@b7c566a772e6b6bfb58ed0dc250532a479d7789f"
        assert upload["with"] == {"name": f"{lane}-failure-diagnostics",
                                  "path": "${{ runner.temp }}/lane-diagnostics",
                                  "retention-days": 14, "if-no-files-found": "error"}


def test_native_jobs_own_nix_qualification() -> None:
    doc = parse_yaml_or_json((ROOT / ".github/workflows/native-qualification.yml").read_text())
    for lane in ("native-darwin-arm64", "native-linux-x64", "native-linux-arm64"):
        steps = doc["jobs"][lane]["steps"]
        assert any("install-nix-action" in step.get("uses", "") for step in steps)
        assert any(f"native_lane.py qualify --lane {lane}" in step.get("run", "") for step in steps)
        assert any("--workflow native-qualification" in step.get("run", "") for step in steps)


def test_failure_upload_matches_only_sanitized_browser_writer(tmp_path):
    """Exercise the maintained writer and the workflow's exact upload glob."""
    import json
    import sys
    sys.path.insert(0, str(ROOT / "src/test/support"))
    from apg123_browser_ui import BrowserHarnessConfig, retain_failure_evidence

    scratch = tmp_path.resolve() / "apgr-runtime"
    scratch.mkdir(mode=0o700)
    config = BrowserHarnessConfig(ROOT, scratch, Path(sys.executable), "fake", scratch, "fake", scratch)
    _, retained = retain_failure_evidence(config, "run-upload", scratch / "receipt.json", 1,
                                         "Authorization=fixture-secret", "Bearer fixture-token",
                                         str(scratch / "private-run"))
    (retained.parent / "run-npm-failure.json").write_text("npm private diagnostics")
    doc = parse_yaml_or_json(WORKFLOW_PATH.read_text())
    upload = next(step for step in doc["jobs"]["unit-integration"]["steps"]
                  if step.get("with", {}).get("name") == "browser-failure-evidence")
    assert upload["if"] == "${{ failure() }}"
    assert upload["with"]["if-no-files-found"] == "ignore"
    assert upload["with"]["retention-days"] == 7
    pattern = upload["with"]["path"].removeprefix("${{ runner.temp }}/")
    assert list(tmp_path.resolve().glob(pattern)) == [retained]
    serialized = json.dumps(json.loads(retained.read_text()))
    assert "fixture-secret" not in serialized and "fixture-token" not in serialized
    assert str(scratch) not in serialized


def test_package_export_copies_only_distribution_artifacts(tmp_path):
    import os
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[7]
    script = (root / "tools/ci/qualify_packages.sh").read_text()
    start = script.index('mkdir -p "$RUNNER_TEMP/deliverables"')
    end = script.index('(cd "$RUNNER_TEMP/deliverables"', start)
    packages = tmp_path / "packages"
    files = {
        "python-work/build-a/binaries/darwin-arm64/apgr": b"binary",
        "python/example.whl": b"wheel",
        "python/example.tar.gz": b"sdist",
        "python/SHA256SUMS": b"nested build checksum; not a release artifact",
        "npm-a/example.tgz": b"npm archive",
        "manifest/apg-distribution-manifest.json": b"{}",
        "manifest/SHA256SUMS": b"distribution checksums",
    }
    for relative, content in files.items():
        path = packages / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    environment = dict(os.environ, RUNNER_TEMP=str(tmp_path), pkg_root=str(packages))
    result = subprocess.run(["bash", "-euc", script[start:end]], env=environment,
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    exported = tmp_path / "deliverables"
    assert {p.relative_to(exported).as_posix() for p in exported.rglob("*") if p.is_file()} == {
        "go/darwin-arm64/apgr", "python/example.whl", "python/example.tar.gz",
        "npm/example.tgz", "apg-distribution-manifest.json", "SHA256SUMS",
    }
    assert (exported / "python/example.whl").read_bytes() == b"wheel"
