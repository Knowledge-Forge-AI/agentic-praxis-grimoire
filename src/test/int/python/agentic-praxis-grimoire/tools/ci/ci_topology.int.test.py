"""Integration tests for CI topology, cross-binding contracts, and shipped workflows."""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

from release.ci.matrix_receipts import DEFAULT_MEMBER_JOBS
from tools.ci.ci_topology import (
    EXPECTED_CODEQL_LANGUAGES,
    REQUIRED_PR_JOBS,
    load_workflow_doc,
    main,
    validate_all_workflows,
)

ROOT = Path(__file__).resolve().parents[7]
PUBLIC_PR_WORKFLOW = ROOT / ".github/workflows/public-pr.yml"
RELEASE_WORKFLOW = ROOT / ".github/workflows/release.yml"


def test_cross_binding_pr_jobs_member_jobs_release_checks_and_workflow_lanes() -> None:
    """Cross-bind REQUIRED_PR_JOBS, DEFAULT_MEMBER_JOBS, release.yml required_checks, and workflow lanes."""
    # 1. Load workflows
    pr_doc = load_workflow_doc(PUBLIC_PR_WORKFLOW)
    rel_doc = load_workflow_doc(RELEASE_WORKFLOW)

    # 2. Workflow lane members in public-pr.yml match REQUIRED_PR_JOBS
    pr_jobs = pr_doc.get("jobs", {})
    workflow_lane_members = set(pr_jobs.keys())
    assert workflow_lane_members == REQUIRED_PR_JOBS

    # 3. CodeQL matrix languages in public-pr.yml match EXPECTED_CODEQL_LANGUAGES
    codeql_job = pr_jobs["codeql"]
    codeql_matrix_includes = codeql_job["strategy"]["matrix"]["include"]
    matrix_languages = {item["language"] for item in codeql_matrix_includes}
    assert matrix_languages == EXPECTED_CODEQL_LANGUAGES

    # 4. DEFAULT_MEMBER_JOBS cross-binds to REQUIRED_PR_JOBS with CodeQL expanded per language
    expected_member_jobs = (REQUIRED_PR_JOBS - {"codeql", "public-pr-gate"}) | {
        f"codeql-{lang}" for lang in EXPECTED_CODEQL_LANGUAGES
    }
    assert DEFAULT_MEMBER_JOBS == expected_member_jobs

    # 5. public-pr-gate dependencies and MATRIX_NEEDS_RESULTS cross-bind
    gate_job = pr_jobs["public-pr-gate"]
    gate_needs = set(gate_job["needs"])
    assert gate_needs == REQUIRED_PR_JOBS - {"public-pr-gate"}

    matrix_needs_raw = gate_job["env"]["MATRIX_NEEDS_RESULTS"]
    matrix_needs_keys = set(json.loads(matrix_needs_raw).keys())
    assert matrix_needs_keys == DEFAULT_MEMBER_JOBS

    # 6. release.yml required_checks array cross-binds to workflow lane members
    verify_step = next(
        step
        for step in rel_doc["jobs"]["publish"]["steps"]
        if step.get("name") == "Verify merged source, PR approval, and workflow checks"
    )
    script = verify_step["run"]

    checks_match = re.search(r"^required_checks=\((.*)\)$", script, re.MULTILINE)
    assert checks_match is not None, "release.yml missing required_checks array"
    required_checks = shlex.split(checks_match.group(1))

    # All non-matrix jobs appear by lane name; CodeQL appears as "codeql (<lang>)"
    expected_required_checks = (REQUIRED_PR_JOBS - {"codeql"}) | {
        f"codeql ({lang})" for lang in EXPECTED_CODEQL_LANGUAGES
    }
    assert set(required_checks) == expected_required_checks
    assert len(required_checks) == len(expected_required_checks), "duplicate checks in release.yml"

    # 7. release.yml required_receipts JSON array cross-binds to DEFAULT_MEMBER_JOBS
    receipts_match = re.search(r"^required_receipts='(.*)'$", script, re.MULTILINE)
    assert receipts_match is not None, "release.yml missing required_receipts JSON"
    required_receipts = set(json.loads(receipts_match.group(1)))
    assert required_receipts == DEFAULT_MEMBER_JOBS


def test_ci_topology_validation_passes_on_shipped_workflows() -> None:
    errors = validate_all_workflows()
    assert errors == []


def test_ci_topology_cli_main_passes() -> None:
    assert main([]) == 0
