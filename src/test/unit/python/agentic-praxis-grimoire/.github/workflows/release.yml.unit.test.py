"""Exact structure contract for the PyPI Trusted Publishing workflow."""

from __future__ import annotations

from pathlib import Path
import json

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
PYPA_PUBLISH_COMMIT = "dc37677b2e1c63e2034f94d8a5b11f265b73ba33"


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
    assert "v0.6.0" in script
    assert "Knowledge-Forge-AI/agentic-praxis-grimoire" in script
    assert "agentic_praxis_grimoire-0.6.0-py3-none-any.whl" in script
    assert "agentic_praxis_grimoire-0.6.0.tar.gz" in script
    assert "SHA256SUMS" in script
    assert ".release.assets" in script
    assert "sha256sum --check --strict" in script
    assert "verified-dist" in script
    assert "release-assets" not in publish.get("with", {}).get("packages-dir", "")
    assert publish == {
        "name": "Publish verified distributions to PyPI",
        "uses": f"pypa/gh-action-pypi-publish@{PYPA_PUBLISH_COMMIT}",
        "with": {"packages-dir": "verified-dist"},
    }
