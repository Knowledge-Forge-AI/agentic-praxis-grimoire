#!/usr/bin/env python3
"""Validate GitHub Actions workflow topology against APGR security contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.native_topology import (
    EXPECTED_REPO,
    EXPECTED_REPO_ID,
    SHA_PATTERN,
    check_go_setups,
    check_pull_request_workflow,
    check_step_policy,
    condition_clauses,
    guard_clauses,
    validate_native_qualification,
)
from tools.ci.nix_readback_maintenance import (
    WORKFLOW_PATH as NIX_READBACK_MAINTENANCE_WORKFLOW,
)
from tools.ci.nix_readback_maintenance import (
    validate_current_maintenance,
)
from tools.ci.nix_readback_topology import validate_nix_readback

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = ROOT / ".github/workflows"

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
RELEASE_CHECKOUT_ACTION = "actions/checkout"
RELEASE_CHECKOUT_PIN = "3d3c42e5aac5ba805825da76410c181273ba90b1"
RELEASE_STEP_NAMES = [
    "Check out trusted repository",
    "Verify published release boundary",
]
RELEASE_VERIFY_COMMAND = (
    'python3 tools/ci/release_boundary.py verify-published '
    '--event "$GITHUB_EVENT_PATH" --output "$RUNNER_TEMP/release-boundary"'
)
RELEASE_JOB_KEYS = {"runs-on", "permissions", "steps"}
EXPECTED_VERIFY_PERMISSIONS = {
    "actions": "read",
    "checks": "read",
    "contents": "read",
    "pull-requests": "read",
}
RELEASE_FORBIDDEN_TOKENS = (
    "continue-on-error", "go build", "go test", "nix build", "nix develop", "npm ci",
    "npm run", "pip install", "-m build", "gh workflow run", "gh run rerun",
)
GLOBAL_FORBIDDEN_PUBLICATION_MARKERS = (
    "gh-action-pypi-publish",
    "twine",
    "npm publish",
    "pnpm publish",
    "yarn publish",
    "uv publish",
    "poetry publish",
    "flit publish",
    "hatch publish",
    "cargo publish",
    "gem push",
    "goreleaser",
    "docker push",
    "brew",
    "homebrew",
    "pypi_",
    "npm_token",
    "node_auth_token",
    "registry-url",
    "id-token",
    "secrets.",
    "gh release",
    "action-gh-release",
)
PUBLISH_COMMAND_PATTERN = re.compile(
    r"\b(npm|pnpm|yarn|uv|poetry|flit|hatch|cargo)\s+publish\b", re.IGNORECASE
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


def check_global_publication_markers(raw_text: str, path: Path) -> list[str]:
    errors = []
    lower = raw_text.lower()
    for marker in GLOBAL_FORBIDDEN_PUBLICATION_MARKERS:
        if marker in lower:
            errors.append(f"{path.name}: forbidden publication marker {marker!r}")
    match = PUBLISH_COMMAND_PATTERN.search(raw_text)
    if match:
        matched_cmd = match.group(0).lower()
        if not any(marker == matched_cmd for marker in GLOBAL_FORBIDDEN_PUBLICATION_MARKERS):
            errors.append(f"{path.name}: forbidden publication marker {match.group(0)!r}")
    return errors


def check_workflow_permissions(doc: dict[str, Any], path: Path) -> list[str]:
    errors = []
    top_perms = doc.get("permissions")
    if isinstance(top_perms, dict):
        for perm, val in top_perms.items():
            if val == "write":
                errors.append(
                    f"{path.name}: top-level write permission {perm!r} is forbidden"
                )
    elif top_perms == "write-all":
        errors.append(f"{path.name}: top-level write-all permission is forbidden")

    jobs = doc.get("jobs", {})
    if isinstance(jobs, dict):
        for job_name, job_doc in jobs.items():
            if not isinstance(job_doc, dict):
                continue
            job_perms = job_doc.get("permissions")
            if isinstance(job_perms, dict):
                for perm, val in job_perms.items():
                    if val == "write" and not (
                        path.stem == "public-pr" and job_name == "codeql" and perm == "security-events"
                    ):
                        errors.append(f"{path.name}:{job_name}: write permission {perm!r} is forbidden "
                                      "(only public-pr:codeql may write security-events)")
            elif job_perms == "write-all":
                errors.append(
                    f"{path.name}:{job_name}: write-all permission is forbidden"
                )
    return errors


def validate_release_yml(doc: dict[str, Any], path: Path) -> list[str]:
    errors = []
    for key in sorted(set(doc) - {"name", "on", "permissions", "jobs"}):
        errors.append(f"{path.name}: unsupported top-level key {key!r}")

    # 1. Triggers
    on = doc.get("on")
    if not isinstance(on, dict) or set(on) != {"release"}:
        errors.append(f"{path.name}: only release execution is permitted")
    elif on != {"release": {"types": ["published"]}}:
        errors.append(f"{path.name}: release trigger must specify types: ['published']")

    # 2. Top-level permissions
    perms = doc.get("permissions")
    if perms != {}:
        errors.append(
            f"{path.name}: top-level permissions must be empty mapping {{}}, got {perms}"
        )

    # 3. Jobs inspection
    jobs = doc.get("jobs", {})
    if not isinstance(jobs, dict) or "verify" not in jobs:
        errors.append(f"{path.name}: missing required 'verify' job")
        return errors
    if set(jobs) != {"verify"}:
        errors.append(f"{path.name}: unexpected jobs in release: {sorted(set(jobs) - {'verify'})}")

    verify = jobs["verify"]
    if not isinstance(verify, dict):
        errors.append(f"{path.name}:verify: job must be an object")
        return errors
    for key in sorted(set(verify) - RELEASE_JOB_KEYS):
        errors.append(f"{path.name}:verify: unsupported job key {key!r}")

    if "environment" in verify:
        errors.append(f"{path.name}:verify: environment is forbidden")

    runs_on = verify.get("runs-on")
    if runs_on != "ubuntu-latest":
        errors.append(f"{path.name}:verify: runs-on must be ubuntu-latest, got {runs_on!r}")

    job_perms = verify.get("permissions")
    if job_perms != EXPECTED_VERIFY_PERMISSIONS:
        errors.append(
            f"{path.name}:verify: permissions must be {EXPECTED_VERIFY_PERMISSIONS}, got {job_perms}"
        )

    steps = verify.get("steps", [])
    if not isinstance(steps, list) or len(steps) != 2:
        errors.append(f"{path.name}:verify: steps must contain exactly 2 steps, got {len(steps) if isinstance(steps, list) else type(steps)}")
        return errors

    step_names = [step.get("name") if isinstance(step, dict) else None for step in steps]
    if step_names != RELEASE_STEP_NAMES:
        errors.append(f"{path.name}:verify: steps must be exactly {RELEASE_STEP_NAMES}")

    step0, step1 = steps[0], steps[1]
    if not isinstance(step0, dict) or not isinstance(step1, dict):
        errors.append(f"{path.name}:verify: steps must be objects")
        return errors

    if set(step0) != {"name", "uses", "with"} or step0.get("with") != {"persist-credentials": False}:
        errors.append(f"{path.name}:verify: checkout step keys/options must be exact")
    if set(step1) != {"name", "env", "run"}:
        errors.append(f"{path.name}:verify: verifier step keys must be exact")
    uses0 = step0.get("uses")
    if not uses0:
        errors.append(f"{path.name}:verify: step 0 must use checkout action")
    else:
        action, _, ref = str(uses0).partition("@")
        if not SHA_PATTERN.match(ref.strip()):
            errors.append(f"{path.name}:verify: action {uses0} not pinned to 40-char SHA")
        elif (action, ref) != (RELEASE_CHECKOUT_ACTION, RELEASE_CHECKOUT_PIN):
            errors.append(
                f"{path.name}:verify: action {uses0} is not the approved checkout pin"
            )
    if step0.get("with", {}).get("persist-credentials") is not False:
        errors.append(f"{path.name}:verify: checkout step must set persist-credentials: false")

    if "uses" in step1:
        errors.append(f"{path.name}:verify: step 1 must not use an action")

    run_cmd = str(step1.get("run", "")).strip()
    if run_cmd != RELEASE_VERIFY_COMMAND:
        errors.append(
            f"{path.name}:verify: step 1 run command must be {RELEASE_VERIFY_COMMAND!r}, got {run_cmd!r}"
        )

    env1 = step1.get("env")
    expected_env = {"GH_TOKEN": "${{ github.token }}"}
    if env1 != expected_env:
        errors.append(f"{path.name}:verify: step 1 env must be {expected_env}, got {env1}")

    for token in RELEASE_FORBIDDEN_TOKENS:
        if token in run_cmd or token in step1:
            errors.append(f"{path.name}:verify: forbidden release step token {token!r}")

    return errors


def validate_all_workflows() -> list[str]:
    if not WORKFLOWS_DIR.is_dir():
        return ["missing .github/workflows directory"]
    errors = []
    validators = {
        "public-pr": validate_public_pr,
        "native-qualification": validate_native_qualification,
        "nix-post-tag-readback": validate_nix_readback,
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
        raw_text = wf.read_text(encoding="utf-8")
        errors.extend(check_global_publication_markers(raw_text, wf))
        try:
            doc = load_workflow_doc(wf)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            errors.append(f"{wf.name}: parse error: {error}")
            continue
        errors.extend(check_workflow_permissions(doc, wf))
        errors.extend(validator(doc, wf))
    if not set(validators) <= seen:
        errors.append(f"missing required workflows: {sorted(set(validators) - seen)}")
    readback_name = Path(NIX_READBACK_MAINTENANCE_WORKFLOW).name
    if (WORKFLOWS_DIR / readback_name).is_file():
        workflow_root = ROOT
        canonical_workflows = ROOT / ".github/workflows"
        if WORKFLOWS_DIR != canonical_workflows:
            workflow_root = WORKFLOWS_DIR.parent.parent
        errors.extend(validate_current_maintenance(workflow_root))
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
