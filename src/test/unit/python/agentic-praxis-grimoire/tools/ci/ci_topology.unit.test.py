"""Unit tests for ci_topology workflow validation (public-pr and release; native has its own file)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.ci import ci_topology
from tools.ci.ci_topology import (
    GLOBAL_FORBIDDEN_PUBLICATION_MARKERS,
    check_global_publication_markers,
    check_workflow_permissions,
    load_workflow_doc,
    validate_all_workflows,
    validate_public_pr,
    validate_release_yml,
)

ROOT = Path(__file__).resolve().parents[7]
PUBLIC = Path("public-pr.yml")
RELEASE = Path("release.yml")


@pytest.fixture
def valid_public_pr_doc() -> dict:
    return load_workflow_doc(ROOT / ".github/workflows/public-pr.yml")


@pytest.fixture
def valid_release_doc() -> dict:
    return load_workflow_doc(ROOT / ".github/workflows/release.yml")


def _step(doc: dict, job: str, needle: str) -> dict:
    return next(s for s in doc["jobs"][job]["steps"]
                if needle in s.get("run", "") or str(s.get("uses", "")).startswith(needle))


def test_valid_public_pr_workflow_has_zero_errors(valid_public_pr_doc: dict) -> None:
    assert validate_public_pr(valid_public_pr_doc, PUBLIC) == []


def test_public_pr_job_set_is_the_reduced_two_workflow_profile(valid_public_pr_doc: dict) -> None:
    assert set(valid_public_pr_doc["jobs"]) == ci_topology.REQUIRED_PR_JOBS
    assert not {"package", "sbom-and-vulnerability", "nix"} & set(valid_public_pr_doc["jobs"])


def test_reject_missing_pull_request_trigger(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["on"] = {"push": {"branches": ["main"]}}
    assert any("missing pull_request trigger" in e for e in validate_public_pr(doc, PUBLIC))


def test_reject_wrong_target_branch(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["on"]["pull_request"]["branches"] = ["develop"]
    assert any("must target 'main' branch" in e for e in validate_public_pr(doc, PUBLIC))


def test_reject_unrestricted_permissions(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["permissions"] = {"contents": "write"}
    assert any("top-level permissions" in e for e in validate_public_pr(doc, PUBLIC))


def test_reject_missing_cancel_in_progress(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["concurrency"]["cancel-in-progress"] = False
    assert any("cancel-in-progress" in e for e in validate_public_pr(doc, PUBLIC))


def test_reject_unpinned_action_in_steps(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["guard"]["steps"][0]["uses"] = "actions/checkout@v4"
    assert any("not pinned to 40-char SHA" in e for e in validate_public_pr(doc, PUBLIC))


def test_reject_pinned_but_unapproved_action(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["policy"]["steps"].append({"uses": "pypa/gh-action-pypi-publish@" + "a" * 40})
    assert any("not an approved action pin" in e for e in validate_public_pr(doc, PUBLIC))


def test_reject_forbidden_id_token_permission(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["policy"]["permissions"] = {"id-token": "write"}
    assert any("id-token write forbidden" in e for e in validate_public_pr(doc, PUBLIC))


def test_rejects_linux_canonical_suite(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["unit-integration"]["runs-on"] = "ubuntu-latest"
    assert any("unit-integration: runs-on must be 'macos-15'" in e
               for e in validate_public_pr(doc, PUBLIC))


def test_rejects_expensive_job_without_public_guard(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["unit-integration"].pop("if")
    assert any("unit-integration: missing job-level public guard" in e
               for e in validate_public_pr(doc, PUBLIC))


@pytest.mark.parametrize("job", ["static-analysis", "policy", "closure", "go", "codeql"])
def test_guard_condition_must_be_exact_not_merely_mention_the_guards(valid_public_pr_doc: dict, job: str) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"][job]["if"] = doc["jobs"][job]["if"].replace(" }}", " || always() }}")
    assert any(f"{job}: missing job-level public guard" in e for e in validate_public_pr(doc, PUBLIC))


def test_rejects_incomplete_codeql_matrix(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["codeql"]["strategy"]["matrix"]["include"].pop()
    assert any("language matrix" in e for e in validate_public_pr(doc, PUBLIC))


@pytest.mark.parametrize("extra", ["package", "sbom-and-vulnerability", "nix"])
def test_rejects_unexpected_job_in_public_pr(valid_public_pr_doc: dict, extra: str) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"][extra] = {"runs-on": "ubuntu-latest"}
    assert any("unexpected jobs in public PR" in e for e in validate_public_pr(doc, PUBLIC))


def test_rejects_macos_on_non_permitted_job(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["policy"]["runs-on"] = "macos-15"
    assert any("macos-15 is reserved for unit-integration" in e for e in validate_public_pr(doc, PUBLIC))


def test_rejects_exact_dependency_drift(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"]["go"]["needs"] = []
    assert any("go: needs must be ['guard']" in e for e in validate_public_pr(doc, PUBLIC))


def test_rejects_gate_that_drops_a_member_from_needs_results(valid_public_pr_doc: dict) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    env = doc["jobs"]["public-pr-gate"]["env"]
    env["MATRIX_NEEDS_RESULTS"] = env["MATRIX_NEEDS_RESULTS"].replace('\"codeql-go\":', '\"codeql-gone\":')
    assert any("needs.codeql.result for codeql-go" in e for e in validate_public_pr(doc, PUBLIC))


@pytest.mark.parametrize("mutation, expected", [
    ("expression", "run step contains expression"),
    ("continue-on-error", "continue-on-error is forbidden"),
    ("working-directory", "working-directory is forbidden"),
    ("suppress", "suppression token"),
    ("wrong-caller", "wrong helper path"),
    ("missing-helper", "nonexistent or wrong helper path"),
    ("workspace-output", "output path must be under RUNNER_TEMP"),
    ("workspace-upload", "path must be under runner.temp"),
    ("secrets", "forbidden token 'secrets.'"),
])
def test_public_pr_step_policy_has_no_suppression_or_path_loopholes(
    valid_public_pr_doc: dict, mutation: str, expected: str
) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    step = _step(doc, "policy", "bin/apg-check-skill-library")
    emit = _step(doc, "policy", "matrix_receipts.py emit")
    if mutation == "expression":
        step["run"] += "echo ${{ github.head_ref }}\n"
    elif mutation == "continue-on-error":
        step["continue-on-error"] = True
    elif mutation == "working-directory":
        step["working-directory"] = "src"
    elif mutation == "suppress":
        step["run"] += "false || true\n"
    elif mutation == "wrong-caller":
        step["run"] += "python3 release/ci/native_lane.py guard\n"
    elif mutation == "missing-helper":
        step["run"] += "python3 tools/ci/not_a_helper.py\n"
    elif mutation == "workspace-output":
        emit["run"] = emit["run"].replace('--dir "${RUNNER_TEMP}/receipts"', "--dir receipts")
    elif mutation == "workspace-upload":
        _step(doc, "policy", "actions/upload-artifact")["with"]["path"] = "receipts"
    else:
        step.setdefault("env", {})["TOKEN"] = "${{ secrets.TOKEN }}"
    assert any(expected in e for e in validate_public_pr(doc, PUBLIC)), expected


def test_validate_all_shipped_workflows() -> None:
    assert validate_all_workflows() == []


def test_rejects_unknown_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_topology, "WORKFLOWS_DIR", tmp_path)
    (tmp_path / "unknown.yml").write_text("{}", encoding="utf-8")
    errors = ci_topology.validate_all_workflows()
    assert any("unknown.yml: unknown workflow" in e for e in errors)


def test_requires_exactly_the_three_shipped_workflows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_topology, "WORKFLOWS_DIR", tmp_path)
    assert ci_topology.validate_all_workflows() == [
        "missing required workflows: ['native-qualification', 'public-pr', 'release']"
    ]
    source = ROOT / ".github/workflows/public-pr.yml"
    (tmp_path / "public-pr.yml").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    assert ci_topology.validate_all_workflows() == [
        "missing required workflows: ['native-qualification', 'release']"
    ]


def test_unparseable_workflow_is_a_parse_error_not_a_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_topology, "WORKFLOWS_DIR", tmp_path)
    (tmp_path / "release.yml").write_text("not: [json", encoding="utf-8")
    assert any("release.yml: parse error" in e for e in ci_topology.validate_all_workflows())


@pytest.mark.parametrize("mutation", ["old", "missing-version", "missing-setup"])
def test_every_go_job_requires_the_approved_release_compiler(valid_public_pr_doc: dict, mutation: str) -> None:
    for name in ("static-analysis", "unit-integration", "go", "codeql"):
        doc = copy.deepcopy(valid_public_pr_doc)
        steps = doc["jobs"][name]["steps"]
        setup = next(step for step in steps if str(step.get("uses", "")).startswith("actions/setup-go@"))
        if mutation == "old":
            setup["with"]["go-version"] = "1.25.14"
        elif mutation == "missing-version":
            del setup["with"]["go-version"]
        else:
            steps.remove(setup)
        errors = validate_public_pr(doc, Path("synthetic/public-pr.yml"))
        assert any(f":{name}:" in error and "setup-go" in error for error in errors)


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
        doc["jobs"]["go"]["permissions"] = {"packages": "write"}
    assert validate_public_pr(doc, PUBLIC)


def test_valid_release_workflow_has_zero_errors(valid_release_doc: dict) -> None:
    assert validate_release_yml(valid_release_doc, RELEASE) == []


def test_reject_release_wrong_trigger(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["on"] = {"push": {"branches": ["main"]}}
    assert any("only release execution is permitted" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_wrong_type(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["on"]["release"]["types"] = ["created"]
    assert any("must specify types: ['published']" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_non_empty_top_level_permissions(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["permissions"] = {"contents": "read"}
    assert any("top-level permissions must be empty mapping" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_missing_verify_job(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    del doc["jobs"]["verify"]
    assert any("missing required 'verify' job" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_extra_job(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["rebuild"] = {"runs-on": "ubuntu-latest", "steps": []}
    assert any("unexpected jobs in release" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_wrong_runner(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["runs-on"] = "macos-15"
    assert any("runs-on must be ubuntu-latest" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_environment_forbidden(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["environment"] = "pypi"
    assert any("environment is forbidden" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_id_token_forbidden(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["permissions"]["id-token"] = "write"
    assert any("permissions must be" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_unpinned_checkout(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["steps"][0]["uses"] = "actions/checkout@v4"
    assert any("not pinned to 40-char SHA" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_unapproved_checkout_pin(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["steps"][0]["uses"] = "actions/checkout@" + "b" * 40
    assert any("is not the approved checkout pin" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_checkout_credentials_leak(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["steps"][0]["with"]["persist-credentials"] = True
    assert any("persist-credentials: false" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_step1_extra_action(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["steps"][1]["uses"] = "actions/checkout@" + "3d3c42e5aac5ba805825da76410c181273ba90b1"
    assert any("step 1 must not use an action" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_step1_wrong_command(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["steps"][1]["run"] = "echo forbidden"
    assert any("step 1 run command must be" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_step1_wrong_env(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["steps"][1]["env"] = {}
    assert any("step 1 env must be" in e for e in validate_release_yml(doc, RELEASE))


def test_reject_release_wrong_step_count(valid_release_doc: dict) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["steps"].append({"name": "extra", "run": "true"})
    assert any("steps must contain exactly 2 steps" in e for e in validate_release_yml(doc, RELEASE))


@pytest.mark.parametrize("token", ["go build ./...", "nix build .#x", "python3 -m build", "pip install x"])
def test_reject_release_local_build_fallback(valid_release_doc: dict, token: str) -> None:
    doc = copy.deepcopy(valid_release_doc)
    doc["jobs"]["verify"]["steps"][1]["run"] += f"\n{token}\n"
    assert any("step 1 run command must be" in e for e in validate_release_yml(doc, RELEASE))


@pytest.mark.parametrize("marker", GLOBAL_FORBIDDEN_PUBLICATION_MARKERS)
def test_reject_global_publication_markers(marker: str) -> None:
    errors = check_global_publication_markers(f"# some comment with {marker} token", Path("test.yml"))
    assert any("forbidden publication marker" in e for e in errors), f"marker {marker!r} not detected"


@pytest.mark.parametrize(
    ("job", "perm"),
    [
        ("guard", "contents"),
        ("policy", "packages"),
        ("unit-integration", "id-token"),
        ("closure", "security-events"),
        ("go", "actions"),
    ],
)
def test_check_workflow_permissions_rejects_forbidden_writes(
    valid_public_pr_doc: dict, job: str, perm: str
) -> None:
    doc = copy.deepcopy(valid_public_pr_doc)
    doc["jobs"][job]["permissions"] = {perm: "write"}
    errors = check_workflow_permissions(doc, PUBLIC)
    assert any(f"write permission {perm!r} is forbidden" in e for e in errors)


def test_check_workflow_permissions_allows_public_pr_codeql_security_events(
    valid_public_pr_doc: dict,
) -> None:
    errors = check_workflow_permissions(valid_public_pr_doc, PUBLIC)
    assert errors == []


@pytest.mark.parametrize("mutation", [
    "checkout-run", "checkout-repository", "verifier-shell", "verifier-if", "trigger-filter",
])
def test_release_step_and_trigger_authority_keys_are_closed(mutation):
    doc = load_workflow_doc(ROOT / ".github/workflows/release.yml")
    first, second = doc["jobs"]["verify"]["steps"]
    if mutation == "checkout-run":
        first["run"] = "arbitrary-command"
    elif mutation == "checkout-repository":
        first["with"]["repository"] = "other/repository"
    elif mutation == "verifier-shell":
        second["shell"] = "arbitrary-executable {0}"
    elif mutation == "verifier-if":
        second["if"] = "false"
    else:
        doc["on"]["release"]["branches"] = ["other"]
    assert validate_release_yml(doc, Path("release.yml"))
