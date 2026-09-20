"""Integration tests for the read-only release verification workflow and boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
VERSION = (
    REPOSITORY_ROOT / "src" / "agentic_praxis_grimoire" / "VERSION"
).read_text(encoding="utf-8").strip()
DEFAULT_TAG = f"v{VERSION}"
CHECKOUT_COMMIT = "3d3c42e5aac5ba805825da76410c181273ba90b1"
EXPECTED_VERIFY_COMMAND = (
    'python3 tools/ci/release_boundary.py verify-published '
    '--event "$GITHUB_EVENT_PATH" --output "$RUNNER_TEMP/release-boundary"'
)


def _get_boundary_worker():
    """Retrieve the boundary worker module if available, or None if pending."""
    try:
        if str(REPOSITORY_ROOT) not in sys.path:
            sys.path.insert(0, str(REPOSITORY_ROOT))
        import tools.ci.release_boundary as boundary

        return boundary
    except ImportError:
        return None


def _make_event_file(
    tmp_path: Path,
    *,
    tag_name: str = DEFAULT_TAG,
    draft: bool = False,
    prerelease: bool = False,
    repository: str = "Knowledge-Forge-AI/agentic-praxis-grimoire",
) -> Path:
    event_data = {
        "action": "published",
        "repository": {"full_name": repository, "id": 1306002537},
        "release": {
            "id": 42,
            "tag_name": tag_name,
            "draft": draft,
            "prerelease": prerelease,
            "assets": [],
        },
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event_data), encoding="utf-8")
    return event_path


def test_release_workflow_is_read_only_and_cannot_publish_any_package() -> None:
    doc = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    assert set(doc.get("jobs", {})) == {"verify"}
    job = doc["jobs"]["verify"]
    assert "environment" not in job

    perms = job.get("permissions", {})
    assert perms == {
        "actions": "read",
        "checks": "read",
        "contents": "read",
        "pull-requests": "read",
    }
    for perm_name, perm_val in perms.items():
        assert perm_val == "read", f"write permission {perm_name} is forbidden"

    assert "id-token" not in perms

    steps = job.get("steps", [])
    assert len(steps) == 2
    for step in steps:
        assert "pypi" not in str(step).lower()
        uses = step.get("uses", "")
        assert not uses.startswith("pypa/")
        assert not uses.startswith("softprops/action-gh-release")


def test_release_workflow_pinned_checkout_rejects_credential_leak() -> None:
    doc = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    checkout_step = doc["jobs"]["verify"]["steps"][0]
    assert checkout_step["name"] == "Check out trusted repository"
    assert checkout_step["uses"] == f"actions/checkout@{CHECKOUT_COMMIT}"
    assert checkout_step["with"]["persist-credentials"] is False


def test_release_workflow_verify_step_exact_command() -> None:
    doc = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    verify_step = doc["jobs"]["verify"]["steps"][1]
    assert verify_step["name"] == "Verify published release boundary"
    assert verify_step["run"] == EXPECTED_VERIFY_COMMAND
    assert verify_step["env"] == {"GH_TOKEN": "${{ github.token }}"}
    assert "uses" not in verify_step


def test_release_never_falls_back_to_building_locally() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    for token in (
        "go build",
        "go test",
        "nix build",
        "npm ci",
        "pip install",
        "gh workflow run",
    ):
        assert token not in source


def test_boundary_worker_contract_constants() -> None:
    boundary = _get_boundary_worker()
    assert boundary is not None, "release boundary verifier must be present"

    assert hasattr(boundary, "EXPECTED_VERSION")
    assert hasattr(boundary, "build_parser")
    assert hasattr(boundary, "main")
    assert boundary.EXPECTED_VERSION == VERSION
    expected_tag = getattr(boundary, "EXPECTED_TAG", f"v{boundary.EXPECTED_VERSION}")
    assert expected_tag == f"v{VERSION}"


@pytest.mark.parametrize(
    ("override", "description"),
    [
        ({"tag_name": "v0.12.0"}, "predecessor tag"),
        ({"tag_name": "v0.14.0"}, "future tag"),
        ({"draft": True}, "draft release"),
        ({"prerelease": True}, "prerelease"),
        ({"repository": "attacker/agentic-praxis-grimoire"}, "unauthorized repository"),
    ],
)
def test_release_boundary_early_event_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: dict,
    description: str,
) -> None:
    boundary = _get_boundary_worker()
    assert boundary is not None, "release boundary verifier must be present"

    event_path = _make_event_file(tmp_path, **override)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    repo = override.get("repository", "Knowledge-Forge-AI/agentic-praxis-grimoire")
    monkeypatch.setenv("GITHUB_REPOSITORY", repo)

    import tools.ci.release_boundary_github as github
    def refuse_network(request):
        raise AssertionError("early invalid event must fail before network access")
    monkeypatch.setattr(github, "_open", refuse_network)
    assert boundary.main([
        "verify-published", "--event", str(event_path), "--output", str(output_dir)
    ]) == 1
