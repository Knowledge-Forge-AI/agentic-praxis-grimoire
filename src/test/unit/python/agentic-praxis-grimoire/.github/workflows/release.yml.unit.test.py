"""Exact structure contract for the PyPI Trusted Publishing workflow."""

from __future__ import annotations

import json
import re
import shlex

import pytest

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
VERSION = (
    REPOSITORY_ROOT / "src" / "agentic_praxis_grimoire" / "VERSION"
).read_text(encoding="utf-8").strip()
EXPECTED_TAG = f"v{VERSION}"
PYPA_PUBLISH_COMMIT = "dc37677b2e1c63e2034f94d8a5b11f265b73ba33"


def _parse_shell_assignment(script: str, variable: str) -> str:
    matches = re.findall(rf"^{re.escape(variable)}=(.*)$", script, flags=re.MULTILINE)
    assert len(matches) == 1, (
        f"expected exactly one shell assignment for {variable!r}, found {len(matches)}: {matches}"
    )
    all_assigns = re.findall(rf"\b{re.escape(variable)}=", script)
    assert len(all_assigns) == 1, (
        f"expected exactly one occurrence of {variable}=, found {len(all_assigns)}"
    )
    values = shlex.split(matches[0])
    assert len(values) == 1
    return values[0]


def test_release_workflow_is_json_compatible_yaml_with_exact_authority() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    workflow = json.loads(source)

    assert workflow["on"] == {"release": {"types": ["published"]}}
    assert "workflow_dispatch" not in source
    assert workflow.get("permissions") == {}
    assert list(workflow["jobs"]) == ["publish"]
    job = workflow["jobs"]["publish"]
    assert job["environment"] == "pypi"
    assert job["permissions"] == {
        "actions": "read",
        "checks": "read",
        "contents": "read",
        "id-token": "write",
        "pull-requests": "read",
    }
    assert job["runs-on"] == "ubuntu-latest"


def test_release_workflow_verifies_exact_assets_before_trusted_publish() -> None:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["publish"]["steps"]
    assert len(steps) == 3
    verify, merged, publish = steps
    script = verify["run"]

    assert verify["env"] == {"GH_TOKEN": "${{ github.token }}"}
    assert "actions/checkout" not in WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in WORKFLOW.read_text(encoding="utf-8")

    expected_version = _parse_shell_assignment(script, "expected_version")
    expected_tag = _parse_shell_assignment(script, "expected_tag")
    assert expected_version == VERSION
    assert expected_tag == EXPECTED_TAG

    assert "Knowledge-Forge-AI/agentic-praxis-grimoire" in script
    assert "apg-distribution-manifest.json" in script
    assert ".python.wheels" in script
    assert ".python.sdist" in script
    assert "py3-none-any" not in script
    assert "SHA256SUMS" in script
    assert ".release.assets" in script
    assert "verified-dist" in script
    merged_script = merged["run"]
    assert merged["name"] == "Verify merged source, PR approval, and workflow checks"
    assert merged["env"] == {"GH_TOKEN": "${{ github.token }}"}
    assert "pulls/$pr_number/reviews" in merged_script
    assert "APPROVED" in merged_script
    assert "group_by(.user.login)" in merged_script
    assert "sort_by(.id) | last" in merged_script
    assert "commit_id == $head" in merged_script
    assert ".github/workflows/public-pr.yml" in merged_script
    assert "/actions/runs?" in merged_script
    assert "/actions/runs/$run_id/jobs?" in merged_script
    assert "/actions/runs/$run_id/artifacts?" in merged_script
    assert "/actions/artifacts/$aggregate_artifact_id/zip" in merged_script
    assert "actions/runs?event=pull_request&branch=staging" in merged_script
    assert "public-pr-gate-result" in merged_script
    assert "matrix-aggregate.json" in merged_script
    assert "apg-matrix-aggregate-v1" in merged_script
    assert "required_receipts" in merged_script
    assert "aggregate_artifact_digest" in merged_script
    assert ".path == $path" in merged_script
    assert ".head_repository.full_name == $repo" in merged_script
    assert "workflow_name" not in merged_script
    assert ".source_commit" in merged_script
    assert ".source_tree" in merged_script
    assert "tested_tree" in merged_script
    assert "tested_sha" in merged_script
    assert ".parents[0].sha == $expected_base" in merged_script
    assert ".parents[1].sha == $expected_head" in merged_script
    assert '--arg head "$pr_head_sha"' in merged_script
    assert '--arg expected_head "$pr_head_sha"' in merged_script
    assert '[[ "$tested_sha" == "$run_head_sha" ]]' not in merged_script
    assert "release-assets" not in publish.get("with", {}).get("packages-dir", "")
    assert publish == {
        "name": "Publish verified distributions to PyPI",
        "uses": f"pypa/gh-action-pypi-publish@{PYPA_PUBLISH_COMMIT}",
        "with": {"packages-dir": "verified-dist"},
    }


def test_release_workflow_assignment_parser_rejects_duplicates() -> None:
    with pytest.raises(AssertionError):
        _parse_shell_assignment(
            f"expected_version={VERSION}\nexpected_version={VERSION}\n", "expected_version"
        )
    with pytest.raises(AssertionError):
        _parse_shell_assignment(
            f"expected_tag={EXPECTED_TAG}\nexpected_tag={EXPECTED_TAG}\n", "expected_tag"
        )
    with pytest.raises(AssertionError):
        _parse_shell_assignment(
            f"expected_tag={EXPECTED_TAG}; expected_tag={EXPECTED_TAG}\n", "expected_tag"
        )
    with pytest.raises(AssertionError):
        _parse_shell_assignment("other=1\n", "expected_version")
