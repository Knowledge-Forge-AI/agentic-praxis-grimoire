"""Exact structure contract for the read-only release verification workflow."""

from __future__ import annotations

import json

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
VERSION = (
    REPOSITORY_ROOT / "src" / "agentic_praxis_grimoire" / "VERSION"
).read_text(encoding="utf-8").strip()
EXPECTED_TAG = f"v{VERSION}"
CHECKOUT_COMMIT = "3d3c42e5aac5ba805825da76410c181273ba90b1"
EXPECTED_VERIFY_COMMAND = (
    'python3 tools/ci/release_boundary.py verify-published '
    '--event "$GITHUB_EVENT_PATH" --output "$RUNNER_TEMP/release-boundary"'
)


def test_release_workflow_is_json_compatible_yaml_with_exact_authority() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    workflow = json.loads(source)

    assert workflow["name"] == "Verify published release boundary"
    assert workflow["on"] == {"release": {"types": ["published"]}}
    assert "workflow_dispatch" not in source
    assert workflow.get("permissions") == {}
    assert list(workflow["jobs"]) == ["verify"]
    job = workflow["jobs"]["verify"]
    assert "environment" not in job
    assert job["permissions"] == {
        "actions": "read",
        "checks": "read",
        "contents": "read",
        "pull-requests": "read",
    }
    assert job["runs-on"] == "ubuntu-latest"


def test_release_workflow_has_exact_verify_steps() -> None:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["verify"]["steps"]
    assert len(steps) == 2
    checkout_step, verify_step = steps

    assert checkout_step == {
        "name": "Check out trusted repository",
        "uses": f"actions/checkout@{CHECKOUT_COMMIT}",
        "with": {"persist-credentials": False},
    }

    assert verify_step == {
        "name": "Verify published release boundary",
        "env": {"GH_TOKEN": "${{ github.token }}"},
        "run": EXPECTED_VERIFY_COMMAND,
    }


def test_release_workflow_has_no_publication_markers_or_secrets() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    for token in (
        "pypa/gh-action-pypi-publish",
        "twine",
        "secrets.",
        "id-token",
        "environment",
        "action-gh-release",
        "gh release",
        "docker push",
        "goreleaser",
        "gem push",
        "npm publish",
        "cargo publish",
    ):
        assert token not in source.lower()


def test_release_workflow_never_falls_back_to_building_locally() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    for token in ("go build", "go test", "nix build", "npm ci", "pip install", "gh workflow run"):
        assert token not in source
