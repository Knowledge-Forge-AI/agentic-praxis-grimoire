#!/usr/bin/env python3
"""Validate GitHub Actions workflow topology against APGR security contracts."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
WORKFLOWS_DIR = ROOT / ".github/workflows"

from tools.ci.native_topology import (  # noqa: E402
    EXPECTED_REPO,
    EXPECTED_REPO_ID,
    GATE as NATIVE_GATE,
    MEMBER_JOBS as NATIVE_MEMBER_JOBS,
    SHA_PATTERN,
    check_go_setups,
    check_pull_request_workflow,
    check_step_policy,
    condition_clauses,
    guard_clauses,
    validate_native_qualification,
)

REQUIRED_PR_JOBS = {
    "guard",
    "static-analysis",
    "policy",
    "unit-integration",
    "closure",
    "go",
    "codeql",
    "public-pr-gate",
}

STANDARD_RUNNERS = {"ubuntu-latest", "macos-15"}
GUARDED_JOBS = REQUIRED_PR_JOBS - {"guard", "public-pr-gate"}
GO_SETUP_JOBS = {"static-analysis", "unit-integration", "go", "codeql"}
EXPECTED_CODEQL_LANGUAGES = {
    "go",
    "python",
    "javascript-typescript",
    "actions",
}
NATIVE_WORKFLOW_PATH = ".github/workflows/native-qualification.yml"
NATIVE_INDEX_SCHEMA = "apgr.native-rc-index/v1"
NATIVE_GATE_ARTIFACT = "native-release-candidate-gate-result"
RELEASE_PUBLISH_ACTION = "pypa/gh-action-pypi-publish"
RELEASE_PUBLISH_PIN = "dc37677b2e1c63e2034f94d8a5b11f265b73ba33"
RELEASE_STEP_NAMES = [
    "Download and verify exact GitHub Release assets",
    "Verify merged source, PR approval, and workflow checks",
    "Publish verified distributions to PyPI",
]
RELEASE_JOB_KEYS = {"runs-on", "environment", "permissions", "steps"}
RELEASE_FORBIDDEN_TOKENS = (
    "continue-on-error", "go build", "go test", "nix build", "nix develop", "npm ci",
    "npm run", "pip install", "-m build", "gh workflow run", "gh run rerun",
)
RELEASE_VERIFY_FRAGMENTS = (
    f"native_workflow_path={NATIVE_WORKFLOW_PATH}",
    NATIVE_GATE_ARTIFACT,
    NATIVE_INDEX_SCHEMA,
    '.status == "passed"',
    "unzip -Z1",
    'actual_native_digest="sha256:',
    '[[ "$actual_native_digest" == "$native_artifact_digest" ]]',
)


def load_workflow_doc(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    from tools.ci.workflow_model import parse_yaml_or_json
    doc = parse_yaml_or_json(text)
    if not isinstance(doc, dict):
        raise TypeError(f"{path.name}: workflow root must be a mapping")
    return doc


def _gate_needs_results(gate: dict[str, Any]) -> str:
    env = gate.get("env")
    return str(env.get("MATRIX_NEEDS_RESULTS", "")) if isinstance(env, dict) else ""


def validate_public_pr(doc: dict[str, Any], path: Path) -> list[str]:
    from release.ci.matrix_receipts import PUBLIC_PR_MEMBER_JOBS

    errors = check_pull_request_workflow(doc, path)
    jobs = doc.get("jobs", {})
    if not isinstance(jobs, dict):
        return [*errors, f"{path.name}: missing jobs section"]

    missing_jobs = REQUIRED_PR_JOBS - set(jobs.keys())
    if missing_jobs:
        errors.append(f"{path.name}: missing required jobs: {sorted(missing_jobs)}")
    unexpected_jobs = set(jobs.keys()) - REQUIRED_PR_JOBS
    if unexpected_jobs:
        errors.append(f"{path.name}: unexpected jobs in public PR: {sorted(unexpected_jobs)}")

    for job_name, job_doc in jobs.items():
        if not isinstance(job_doc, dict):
            errors.append(f"{path.name}:{job_name}: job must be an object")
            continue
        label = f"{path.name}:{job_name}"
        steps = check_step_policy(errors, path, job_name, job_doc, native=False)

        runs_on = job_doc.get("runs-on")
        if runs_on not in STANDARD_RUNNERS:
            errors.append(f"{label}: runs-on must be a standard runner, got {runs_on!r}")
        if job_name == "unit-integration" and runs_on != "macos-15":
            errors.append(f"{label}: runs-on must be 'macos-15'")
        if job_name != "unit-integration" and runs_on == "macos-15":
            errors.append(f"{label}: macos-15 is reserved for unit-integration")

        expected_needs = {
            "guard": set(),
            "public-pr-gate": REQUIRED_PR_JOBS - {"public-pr-gate"},
        }.get(job_name, {"guard"})
        needs = job_doc.get("needs", [])
        if not isinstance(needs, list) or sorted(needs) != sorted(expected_needs):
            errors.append(f"{label}: needs must be {sorted(expected_needs)}, got {needs!r}")

        if job_name in GUARDED_JOBS:
            if condition_clauses(job_doc.get("if")) != guard_clauses("guard"):
                errors.append(f"{label}: missing job-level public guard; condition must be exactly "
                              f"{guard_clauses('guard')}")
        elif job_name == "guard":
            if condition_clauses(job_doc.get("if")) != guard_clauses(None):
                errors.append(f"{label}: guard job must be bound to the exact repository identity")
        elif condition_clauses(job_doc.get("if")) != guard_clauses(None, always=True):
            errors.append(f"{path.name}: aggregate must run with always() and the repository identity")

        # Permissions check: CodeQL permissions only job; no publishing/OIDC
        job_perms = job_doc.get("permissions")
        if job_name == "codeql":
            expected_codeql_perms = {"contents": "read", "security-events": "write"}
            if job_perms != expected_codeql_perms:
                errors.append(
                    f"{label}: permissions must be {{contents: read, security-events: write}}, got {job_perms}"
                )
        elif job_perms is not None:
            if "id-token" in job_perms:
                errors.append(f"{label}: id-token write forbidden on public PR")
            if "security-events" in job_perms:
                errors.append(f"{label}: security-events write forbidden outside codeql job")
            if job_perms != {"contents": "read"}:
                errors.append(f"{label}: non-CodeQL job cannot increase permissions")

        check_go_setups(errors, label, steps, required=job_name in GO_SETUP_JOBS,
                        forbidden=False, no_cache=False)
        if job_name == "codeql":
            _check_codeql_matrix(errors, path, job_doc)

    # Guard job checks
    guard_str = json.dumps(jobs.get("guard", {}))
    if EXPECTED_REPO not in guard_str:
        errors.append(f"{path.name}: guard job must check repository {EXPECTED_REPO}")
    if EXPECTED_REPO_ID not in guard_str:
        errors.append(f"{path.name}: guard job must check repository ID {EXPECTED_REPO_ID}")
    if "staging" not in guard_str:
        errors.append(f"{path.name}: guard job must check head branch staging")

    gate = jobs.get("public-pr-gate", {})
    if not isinstance(gate, dict):
        return errors
    if "--statuses-json" not in json.dumps(gate):
        errors.append(f"{path.name}: aggregate must inspect actual needs results")
    matrix = _gate_needs_results(gate)
    for member in sorted(PUBLIC_PR_MEMBER_JOBS):
        owner = "codeql" if member.startswith("codeql-") else member
        if f'"{member}":"${{{{ needs.{owner}.result }}}}"' not in matrix:
            errors.append(f"{path.name}: aggregate MATRIX_NEEDS_RESULTS must carry needs.{owner}.result for {member}")

    return errors


def _check_codeql_matrix(errors: list[str], path: Path, job_doc: dict[str, Any]) -> None:
    strategy = job_doc.get("strategy", {})
    matrix = strategy.get("matrix", {}) if isinstance(strategy, dict) else {}
    includes = matrix.get("include", []) if isinstance(matrix, dict) else []
    languages = {item.get("language") for item in includes if isinstance(item, dict)}
    if languages != EXPECTED_CODEQL_LANGUAGES:
        errors.append(
            f"{path.name}:codeql: language matrix must be {sorted(EXPECTED_CODEQL_LANGUAGES)}, "
            f"got {sorted(str(language) for language in languages)}"
        )
    if len(includes) != len(languages):
        errors.append(f"{path.name}:codeql: language matrix contains duplicate members")


def _script_array(script: str, name: str) -> list[str] | None:
    match = re.search(rf"^{name}=\((.*)\)$", script, re.MULTILINE)
    return shlex.split(match.group(1)) if match else None


def _check_release_verification(errors: list[str], path: Path, script: str) -> None:
    from release.ci.matrix_receipts import PUBLIC_PR_MEMBER_JOBS

    label = f"{path.name}:publish"
    public_checks = sorted((REQUIRED_PR_JOBS - {"codeql"})
                           | {f"codeql ({language})" for language in EXPECTED_CODEQL_LANGUAGES})
    for name, expected in (
        ("required_checks", public_checks),
        ("native_required_checks", sorted([*NATIVE_MEMBER_JOBS, NATIVE_GATE])),
    ):
        actual = _script_array(script, name)
        if actual is None or sorted(actual) != expected:
            errors.append(f"{label}: {name} must be exactly {expected}, got {actual}")
    receipts = re.search(r"^required_receipts='(.*)'$", script, re.MULTILINE)
    try:
        listed = sorted(json.loads(receipts.group(1))) if receipts else None
    except ValueError:
        listed = None
    if listed != sorted(PUBLIC_PR_MEMBER_JOBS):
        errors.append(f"{label}: required_receipts must be exactly {sorted(PUBLIC_PR_MEMBER_JOBS)}")
    for fragment in RELEASE_VERIFY_FRAGMENTS:
        if fragment not in script:
            errors.append(f"{label}: release verification must contain {fragment!r}")


def validate_release_yml(doc: dict[str, Any], path: Path) -> list[str]:
    errors = []
    for key in sorted(set(doc) - {"name", "on", "permissions", "jobs"}):
        errors.append(f"{path.name}: unsupported top-level key {key!r}")

    # 1. Triggers
    on = doc.get("on")
    if not isinstance(on, dict) or set(on) != {"release"}:
        errors.append(f"{path.name}: only release execution is permitted")
    elif not isinstance(on.get("release"), dict) or on["release"].get("types") != ["published"]:
        errors.append(f"{path.name}: release trigger must specify types: ['published']")

    # 2. Top-level permissions
    perms = doc.get("permissions")
    if perms != {}:
        errors.append(
            f"{path.name}: top-level permissions must be empty mapping {{}}, got {perms}"
        )

    # 3. Jobs inspection
    jobs = doc.get("jobs", {})
    if not isinstance(jobs, dict) or "publish" not in jobs:
        errors.append(f"{path.name}: missing required 'publish' job")
        return errors
    if set(jobs) != {"publish"}:
        errors.append(f"{path.name}: unexpected jobs in release: {sorted(set(jobs) - {'publish'})}")

    publish = jobs["publish"]
    if not isinstance(publish, dict):
        errors.append(f"{path.name}:publish: job must be an object")
        return errors
    for key in sorted(set(publish) - RELEASE_JOB_KEYS):
        errors.append(f"{path.name}:publish: unsupported job key {key!r}")

    runs_on = publish.get("runs-on")
    if runs_on != "ubuntu-latest":
        errors.append(f"{path.name}:publish: runs-on must be ubuntu-latest, got {runs_on!r}")

    environment = publish.get("environment")
    if environment != "pypi":
        errors.append(f"{path.name}:publish: environment must be 'pypi', got {environment!r}")

    # Publication permissions check (distinct from PR)
    expected_publish_perms = {
        "actions": "read",
        "checks": "read",
        "contents": "read",
        "id-token": "write",
        "pull-requests": "read",
    }
    job_perms = publish.get("permissions")
    if job_perms != expected_publish_perms:
        errors.append(
            f"{path.name}:publish: permissions must be {expected_publish_perms}, got {job_perms}"
        )

    # Step inspection
    steps = publish.get("steps", [])
    if not isinstance(steps, list) or not steps:
        errors.append(f"{path.name}:publish: job must contain non-empty steps")
        return errors
    if [step.get("name") if isinstance(step, dict) else None for step in steps] != RELEASE_STEP_NAMES:
        errors.append(f"{path.name}:publish: steps must be exactly {RELEASE_STEP_NAMES}")

    for step in steps:
        if not isinstance(step, dict):
            errors.append(f"{path.name}:publish: step must be an object")
            continue
        uses = step.get("uses")
        if uses:
            action, _, ref = str(uses).partition("@")
            if not SHA_PATTERN.match(ref.strip()):
                errors.append(f"{path.name}:publish: action {uses} not pinned to 40-char SHA")
            elif (action, ref) != (RELEASE_PUBLISH_ACTION, RELEASE_PUBLISH_PIN):
                errors.append(f"{path.name}:publish: action {uses} is not the approved publisher pin")
        for token in RELEASE_FORBIDDEN_TOKENS:
            if token in str(step.get("run", "")) or token in step:
                errors.append(f"{path.name}:publish: forbidden release step token {token!r}")
        if "checkout" in str(uses).lower() and step.get("with", {}).get("persist-credentials") is not False:
            errors.append(f"{path.name}:publish: checkout step must set persist-credentials: false")
    if [s for s in steps if isinstance(s, dict) and "uses" in s] != [steps[-1]]:
        errors.append(f"{path.name}:publish: only the final step may use an action")
    verify = next((s for s in steps if isinstance(s, dict)
                   and s.get("name") == RELEASE_STEP_NAMES[1]), None)
    if verify is not None:
        _check_release_verification(errors, path, str(verify.get("run", "")))

    return errors


def validate_all_workflows() -> list[str]:
    if not WORKFLOWS_DIR.is_dir():
        return ["missing .github/workflows directory"]
    errors = []
    validators = {
        "public-pr": validate_public_pr,
        "native-qualification": validate_native_qualification,
        "release": validate_release_yml,
    }
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    seen: set[str] = set()
    for wf in workflow_files:
        validator = validators.get(wf.stem)
        if validator is None:
            errors.append(f"{wf.name}: unknown workflow")
            continue
        seen.add(wf.stem)
        try:
            doc = load_workflow_doc(wf)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            errors.append(f"{wf.name}: parse error: {error}")
            continue
        errors.extend(validator(doc, wf))
    if not set(validators) <= seen:
        errors.append(f"missing required workflows: {sorted(set(validators) - seen)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)

    errors = validate_all_workflows()
    if errors:
        print(f"FAILED CI topology validation ({len(errors)} errors):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("topology contracts satisfied: all workflows compliant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
