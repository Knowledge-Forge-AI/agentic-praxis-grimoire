"""Integration tests for CI topology, cross-binding contracts, and the two shipped PR workflows."""

from __future__ import annotations

import json
import re
import shlex
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
    NATIVE_GATE_ARTIFACT,
    NATIVE_INDEX_SCHEMA,
    REQUIRED_PR_JOBS,
    load_workflow_doc,
    main,
    validate_all_workflows,
)
from tools.ci.native_topology import GATE, MEMBER_JOBS, NATIVE_DOWNLOAD_PIN, REQUIRED_NATIVE_JOBS

ROOT = Path(__file__).resolve().parents[7]
WORKFLOWS = ROOT / ".github/workflows"
PUBLIC_PR_WORKFLOW = WORKFLOWS / "public-pr.yml"
NATIVE_WORKFLOW = WORKFLOWS / "native-qualification.yml"
RELEASE_WORKFLOW = WORKFLOWS / "release.yml"


def _release_script() -> str:
    doc = load_workflow_doc(RELEASE_WORKFLOW)
    return next(
        step["run"]
        for step in doc["jobs"]["publish"]["steps"]
        if step.get("name") == "Verify merged source, PR approval, and workflow checks"
    )


def _array(script: str, name: str) -> list[str]:
    match = re.search(rf"^{name}=\((.*)\)$", script, re.MULTILINE)
    assert match is not None, f"release.yml missing {name} array"
    return shlex.split(match.group(1))


def test_shipped_workflow_directory_is_exactly_the_two_pr_workflows_plus_release() -> None:
    assert sorted(path.name for path in WORKFLOWS.iterdir()) == [
        "native-qualification.yml", "public-pr.yml", "release.yml",
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


def test_release_checks_cross_bind_both_pr_workflows() -> None:
    script = _release_script()
    pr_jobs = load_workflow_doc(PUBLIC_PR_WORKFLOW)["jobs"]
    native_jobs = load_workflow_doc(NATIVE_WORKFLOW)["jobs"]

    expected_public_checks = (REQUIRED_PR_JOBS - {"codeql"}) | {
        f"codeql ({language})" for language in EXPECTED_CODEQL_LANGUAGES
    }
    public_checks = _array(script, "required_checks")
    assert set(public_checks) == expected_public_checks
    assert len(public_checks) == len(expected_public_checks), "duplicate checks in release.yml"
    rendered_names = {
        job["name"].replace("${{ matrix.language }}", language)
        for job_id, job in pr_jobs.items()
        for language in (EXPECTED_CODEQL_LANGUAGES if job_id == "codeql" else {""})
    }
    assert rendered_names == expected_public_checks

    native_checks = _array(script, "native_required_checks")
    assert set(native_checks) == REQUIRED_NATIVE_JOBS and len(native_checks) == 10
    assert {job["name"] for job in native_jobs.values()} == set(native_checks)

    receipts = re.search(r"^required_receipts='(.*)'$", script, re.MULTILINE)
    assert receipts is not None, "release.yml missing required_receipts JSON"
    assert set(json.loads(receipts.group(1))) == DEFAULT_MEMBER_JOBS


def test_release_native_evidence_is_the_native_gate_artifact_with_a_digest() -> None:
    script = _release_script()
    native_jobs = load_workflow_doc(NATIVE_WORKFLOW)["jobs"]
    uploads = [
        step["with"]["name"]
        for step in native_jobs[GATE]["steps"]
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    ]
    assert NATIVE_GATE_ARTIFACT in uploads
    assert f".github/workflows/{NATIVE_WORKFLOW.name}" in script
    assert NATIVE_INDEX_SCHEMA in script
    assert 'native_artifact_digest" =~ ^sha256:[0-9a-f]{64}$' in script
    assert '"$actual_native_digest" == "$native_artifact_digest"' in script


def test_native_post_lane_jobs_use_the_artifact_id_capable_download_pin_only() -> None:
    native_jobs = load_workflow_doc(NATIVE_WORKFLOW)["jobs"]
    for job_id, job in native_jobs.items():
        for step in job["steps"]:
            if str(step.get("uses", "")).startswith("actions/download-artifact@"):
                assert step["uses"].endswith(NATIVE_DOWNLOAD_PIN), job_id
                assert job["permissions"] == {"contents": "read", "actions": "read"}, job_id


@pytest.mark.parametrize("path", [PUBLIC_PR_WORKFLOW, NATIVE_WORKFLOW, RELEASE_WORKFLOW])
def test_workflow_files_are_strict_json_documents(path: Path) -> None:
    assert isinstance(load_workflow_doc(path), dict)


def test_ci_topology_validation_passes_on_shipped_workflows() -> None:
    assert validate_all_workflows() == []


def test_ci_topology_cli_main_passes() -> None:
    assert main([]) == 0
