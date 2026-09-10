"""Exact structure contract for the PyPI Trusted Publishing workflow."""

from __future__ import annotations

from pathlib import Path
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
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    assert job["runs-on"] == "ubuntu-latest"


def test_release_workflow_verifies_exact_assets_before_trusted_publish() -> None:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["publish"]["steps"]
    assert len(steps) == 2
    verify, publish = steps
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
