"""Unit tests for ci_topology workflow validation."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.ci.ci_topology import (
    load_workflow_doc,
    validate_all_workflows,
    validate_public_pr,
    validate_release_yml,
)

ROOT = Path(__file__).resolve().parents[7]


@pytest.fixture
def valid_public_pr_doc() -> dict:
    wf = ROOT / ".github/workflows/public-pr.yml"
    return load_workflow_doc(wf)


def test_valid_public_pr_workflow_has_zero_errors(valid_public_pr_doc: dict) -> None:
    errors = validate_public_pr(valid_public_pr_doc, Path("public-pr.yml"))
    assert errors == []


def test_reject_missing_pull_request_trigger(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["on"] = {"push": {"branches": ["main"]}}
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("missing pull_request trigger" in e for e in errors)


def test_reject_wrong_target_branch(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["on"]["pull_request"]["branches"] = ["develop"]
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("must target 'main' branch" in e for e in errors)


def test_reject_unrestricted_permissions(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["permissions"] = {"contents": "write"}
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("top-level permissions" in e for e in errors)


def test_reject_missing_cancel_in_progress(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["concurrency"]["cancel-in-progress"] = False
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("cancel-in-progress" in e for e in errors)


def test_reject_unpinned_action_in_steps(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["guard"]["steps"][0]["uses"] = "actions/checkout@v4"
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("not pinned to 40-char SHA" in e for e in errors)


def test_reject_forbidden_id_token_permission(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["policy"]["permissions"] = {"id-token": "write"}
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("id-token write forbidden" in e for e in errors)


def test_rejects_linux_canonical_suite(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["unit-integration"]["runs-on"] = "ubuntu-latest"
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("unit-integration: runs-on must be 'macos-15'" in e for e in errors)


def test_rejects_expensive_job_without_public_guard(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["package"].pop("if")
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("package: missing job-level public guard" in e for e in errors)


def test_rejects_incomplete_codeql_matrix(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["codeql"]["strategy"]["matrix"]["include"].pop()
    errors = validate_public_pr(doc, Path("public-pr.yml"))
    assert any("language matrix" in e for e in errors)


def test_validate_all_shipped_workflows() -> None:
    errors = validate_all_workflows()
    assert errors == []


@pytest.mark.parametrize("mutation", ["privileged-event", "path-filter", "missing-needs", "non-always", "registry-write"])
def test_required_gate_cannot_be_bypassed(valid_public_pr_doc: dict, mutation: str) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    if mutation == "privileged-event":
        doc["on"]["pull_request_target"] = {}
    elif mutation == "path-filter":
        doc["on"]["pull_request"]["paths"] = ["src/**"]
    elif mutation == "missing-needs":
        doc["jobs"]["public-pr-gate"]["needs"].pop()
    elif mutation == "non-always":
        doc["jobs"]["public-pr-gate"]["if"] = "success()"
    else:
        doc["jobs"]["package"]["permissions"] = {"packages": "write"}
    assert validate_public_pr(doc, Path("public-pr.yml"))


@pytest.fixture
def valid_release_doc() -> dict:
    wf = ROOT / ".github/workflows/release.yml"
    return load_workflow_doc(wf)


def test_valid_release_workflow_has_zero_errors(valid_release_doc: dict) -> None:
    errors = validate_release_yml(valid_release_doc, Path("release.yml"))
    assert errors == []


def test_reject_release_wrong_trigger(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["on"] = {"push": {"branches": ["main"]}}
    errors = validate_release_yml(doc, Path("release.yml"))
    assert any("only release execution is permitted" in e for e in errors)


def test_reject_release_wrong_type(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["on"]["release"]["types"] = ["created"]
    errors = validate_release_yml(doc, Path("release.yml"))
    assert any("must specify types: ['published']" in e for e in errors)


def test_reject_release_non_empty_top_level_permissions(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["permissions"] = {"contents": "read"}
    errors = validate_release_yml(doc, Path("release.yml"))
    assert any("top-level permissions must be empty mapping" in e for e in errors)


def test_reject_release_missing_publish_job(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    del doc["jobs"]["publish"]
    errors = validate_release_yml(doc, Path("release.yml"))
    assert any("missing required 'publish' job" in e for e in errors)


def test_reject_release_wrong_runner(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["publish"]["runs-on"] = "macos-15"
    errors = validate_release_yml(doc, Path("release.yml"))
    assert any("runs-on must be ubuntu-latest" in e for e in errors)


def test_reject_release_wrong_environment(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["publish"]["environment"] = "staging"
    errors = validate_release_yml(doc, Path("release.yml"))
    assert any("environment must be 'pypi'" in e for e in errors)


def test_reject_release_missing_id_token_permission(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    # Publication requires id-token: write (distinct from PR which forbids it)
    doc["jobs"]["publish"]["permissions"] = {"contents": "read"}
    errors = validate_release_yml(doc, Path("release.yml"))
    assert any("permissions must be" in e for e in errors)


def test_reject_release_unpinned_action(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["publish"]["steps"][-1]["uses"] = "pypa/gh-action-pypi-publish@v1"
    errors = validate_release_yml(doc, Path("release.yml"))
    assert any("not pinned to 40-char SHA" in e for e in errors)

