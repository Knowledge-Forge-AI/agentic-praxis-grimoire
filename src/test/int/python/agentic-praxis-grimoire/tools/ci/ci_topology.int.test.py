"""Integration tests for CI topology, cross-binding contracts, and shipped workflows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from release.ci.matrix_receipts import (
    DEFAULT_MEMBER_JOBS,
    NATIVE_MEMBER_JOBS,
    NATIVE_PRESCRIBED_ARTIFACTS,
    PROFILES,
)
from tools.ci.ci_topology import (
    EXPECTED_CODEQL_LANGUAGES,
    EXPECTED_VERIFY_PERMISSIONS,
    RELEASE_CHECKOUT_ACTION,
    RELEASE_CHECKOUT_PIN,
    RELEASE_STEP_NAMES,
    RELEASE_VERIFY_COMMAND,
    REQUIRED_PR_JOBS,
    load_workflow_doc,
    main,
    validate_all_workflows,
)
from tools.ci.native_topology import (
    GATE,
    MEMBER_JOBS,
    NATIVE_DOWNLOAD_PIN,
    REQUIRED_NATIVE_JOBS,
)
from tools.ci.nix_readback_topology import validate_nix_readback

ROOT = Path(__file__).resolve().parents[7]
WORKFLOWS = ROOT / ".github/workflows"
PUBLIC_PR_WORKFLOW = WORKFLOWS / "public-pr.yml"
NATIVE_WORKFLOW = WORKFLOWS / "native-qualification.yml"
RELEASE_WORKFLOW = WORKFLOWS / "release.yml"
NIX_READBACK_WORKFLOW = WORKFLOWS / "nix-post-tag-readback.yml"



def test_shipped_workflow_directory_is_exactly_the_two_pr_workflows_plus_release_and_readback() -> None:
    assert sorted(path.name for path in WORKFLOWS.iterdir()) == [
        "native-qualification.yml", "nix-post-tag-readback.yml", "public-pr.yml", "release.yml",
    ]


def test_cross_binding_public_jobs_members_and_gate() -> None:
    pr_jobs = load_workflow_doc(PUBLIC_PR_WORKFLOW)["jobs"]
    assert set(pr_jobs) == REQUIRED_PR_JOBS

    matrix_languages = {item["language"] for item in pr_jobs["codeql"]["strategy"]["matrix"]["include"]}
    assert matrix_languages == EXPECTED_CODEQL_LANGUAGES

    expected_members = (REQUIRED_PR_JOBS - {"codeql", "public-pr-gate"}) | {
        f"codeql-{language}" for language in EXPECTED_CODEQL_LANGUAGES
    }
    assert DEFAULT_MEMBER_JOBS == expected_members
    assert len(DEFAULT_MEMBER_JOBS) == 10

    gate = pr_jobs["public-pr-gate"]
    assert set(gate["needs"]) == REQUIRED_PR_JOBS - {"public-pr-gate"}
    assert set(json.loads(gate["env"]["MATRIX_NEEDS_RESULTS"])) == DEFAULT_MEMBER_JOBS


def test_cross_binding_native_jobs_members_and_gate() -> None:
    native_jobs = load_workflow_doc(NATIVE_WORKFLOW)["jobs"]
    assert set(native_jobs) == REQUIRED_NATIVE_JOBS
    assert NATIVE_MEMBER_JOBS == set(MEMBER_JOBS) and len(NATIVE_MEMBER_JOBS) == 9
    gate = native_jobs[GATE]
    assert set(gate["needs"]) == NATIVE_MEMBER_JOBS
    assert set(json.loads(gate["env"]["MATRIX_NEEDS_RESULTS"])) == NATIVE_MEMBER_JOBS
    assert set(NATIVE_PRESCRIBED_ARTIFACTS) == NATIVE_MEMBER_JOBS


def test_receipt_profiles_bind_the_shipped_workflow_files() -> None:
    assert PROFILES["public-pr"].workflow_path == PUBLIC_PR_WORKFLOW
    assert PROFILES["native-qualification"].workflow_path == NATIVE_WORKFLOW
    assert PROFILES["public-pr"].member_jobs == DEFAULT_MEMBER_JOBS
    assert PROFILES["native-qualification"].member_jobs == NATIVE_MEMBER_JOBS
    assert NATIVE_WORKFLOW.is_file() and PUBLIC_PR_WORKFLOW.is_file()


def test_every_native_member_emits_its_own_prescribed_artifacts_with_actual_status() -> None:
    native_jobs = load_workflow_doc(NATIVE_WORKFLOW)["jobs"]
    for job in sorted(NATIVE_MEMBER_JOBS):
        emits = [s for s in native_jobs[job]["steps"] if "matrix_receipts.py emit" in s.get("run", "")]
        assert len(emits) == 1, job
        assert "--workflow native-qualification" in emits[0]["run"]
        assert '--status "$CI_JOB_STATUS"' in emits[0]["run"]
        assert emits[0]["env"]["CI_JOB_STATUS"] == "${{ job.status }}"
        assert "always()" in emits[0]["if"]
        for artifact in NATIVE_PRESCRIBED_ARTIFACTS[job]:
            assert f"/{artifact}" in emits[0]["run"]


def test_release_workflow_has_exact_verify_topology() -> None:
    doc = load_workflow_doc(RELEASE_WORKFLOW)
    assert set(doc["jobs"]) == {"verify"}
    job = doc["jobs"]["verify"]
    assert job["runs-on"] == "ubuntu-latest"
    assert "environment" not in job
    assert job["permissions"] == EXPECTED_VERIFY_PERMISSIONS
    assert [step["name"] for step in job["steps"]] == RELEASE_STEP_NAMES
    checkout_step, verify_step = job["steps"]
    assert checkout_step["uses"] == f"{RELEASE_CHECKOUT_ACTION}@{RELEASE_CHECKOUT_PIN}"
    assert checkout_step["with"]["persist-credentials"] is False
    assert verify_step["run"] == RELEASE_VERIFY_COMMAND
    assert verify_step["env"] == {"GH_TOKEN": "${{ github.token }}"}
    assert "uses" not in verify_step


def test_nix_readback_workflow_has_exact_validator_contract() -> None:
    assert validate_nix_readback(load_workflow_doc(NIX_READBACK_WORKFLOW), NIX_READBACK_WORKFLOW) == []


def test_nix_readback_reuses_existing_native_action_pins() -> None:
    def uses(value: object) -> set[str]:
        if isinstance(value, dict):
            found: set[str] = set()
            for child in value.values():
                found.update(uses(child))
            return found
        if isinstance(value, list):
            found = set()
            for child in value:
                found.update(uses(child))
            return found
        return {value} if isinstance(value, str) and "@" in value else set()

    native = uses(load_workflow_doc(NATIVE_WORKFLOW))
    readback = uses(load_workflow_doc(NIX_READBACK_WORKFLOW))
    assert readback <= native


def test_native_post_lane_jobs_use_the_artifact_id_capable_download_pin_only() -> None:
    native_jobs = load_workflow_doc(NATIVE_WORKFLOW)["jobs"]
    for job_id, job in native_jobs.items():
        for step in job["steps"]:
            if str(step.get("uses", "")).startswith("actions/download-artifact@"):
                assert step["uses"].endswith(NATIVE_DOWNLOAD_PIN), job_id
                assert job["permissions"] == {"contents": "read", "actions": "read"}, job_id


@pytest.mark.parametrize("path", [PUBLIC_PR_WORKFLOW, NATIVE_WORKFLOW, RELEASE_WORKFLOW, NIX_READBACK_WORKFLOW])
def test_workflow_files_are_strict_json_documents(path: Path) -> None:
    assert isinstance(load_workflow_doc(path), dict)


def test_ci_topology_validation_passes_on_shipped_workflows() -> None:
    assert validate_all_workflows() == []


def test_ci_topology_cli_main_passes() -> None:
    assert main([]) == 0
