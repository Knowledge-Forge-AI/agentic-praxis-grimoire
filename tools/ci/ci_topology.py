#!/usr/bin/env python3
"""Validate GitHub Actions workflow topology against APGR security contracts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
WORKFLOWS_DIR = ROOT / ".github/workflows"

EXPECTED_REPO = "Knowledge-Forge-AI/agentic-praxis-grimoire"
EXPECTED_REPO_ID = "1306002537"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

REQUIRED_PR_JOBS = {
    "guard",
    "static-analysis",
    "policy",
    "unit-integration",
    "closure",
    "go",
    "package",
    "sbom-and-vulnerability",
    "codeql",
    "public-pr-gate",
}

STANDARD_RUNNERS = {"ubuntu-latest", "macos-15"}
GUARDED_JOBS = REQUIRED_PR_JOBS - {"guard", "public-pr-gate"}
EXPECTED_CODEQL_LANGUAGES = {
    "go",
    "python",
    "javascript-typescript",
    "actions",
}


def load_workflow_doc(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    from tools.ci.workflow_model import parse_yaml_or_json
    doc = parse_yaml_or_json(text)
    if not isinstance(doc, dict):
        raise TypeError(f"{path.name}: workflow root must be a mapping")
    return doc


def validate_public_pr(doc: dict[str, Any], path: Path) -> list[str]:
    errors = []

    # 1. Triggers
    on = doc.get("on")
    if not isinstance(on, dict) or set(on) != {"pull_request"}:
        errors.append(f"{path.name}: only pull_request execution is permitted")
    if not isinstance(on, dict) or "pull_request" not in on:
        errors.append(f"{path.name}: missing pull_request trigger")
    else:
        pr = on["pull_request"]
        branches = pr.get("branches", [])
        if branches != ["main"]:
            errors.append(f"{path.name}: pull_request must target 'main' branch")
        if any(key in pr for key in ("paths", "paths-ignore", "branches-ignore")):
            errors.append(f"{path.name}: required lanes cannot use event filters")
        types = set(pr.get("types", []))
        expected_types = {"opened", "synchronize", "reopened", "ready_for_review"}
        if not expected_types.issubset(types):
            missing_types = sorted(expected_types - types)
            errors.append(f"{path.name}: missing PR types: {missing_types}")

    # 2. Permissions
    perms = doc.get("permissions", {})
    if perms != {"contents": "read"}:
        errors.append(f"{path.name}: top-level permissions must be exactly {{contents: read}}, got {perms}")

    # 3. Concurrency
    concurrency = doc.get("concurrency")
    if not isinstance(concurrency, dict) or not concurrency.get("cancel-in-progress"):
        errors.append(f"{path.name}: concurrency must specify cancel-in-progress: true")

    # 4. Jobs inspection
    jobs = doc.get("jobs", {})
    if not isinstance(jobs, dict):
        errors.append(f"{path.name}: missing jobs section")
        return errors

    missing_jobs = REQUIRED_PR_JOBS - set(jobs.keys())
    if missing_jobs:
        errors.append(f"{path.name}: missing required jobs: {sorted(missing_jobs)}")

    for job_name, job_doc in jobs.items():
        if not isinstance(job_doc, dict):
            errors.append(f"{path.name}:{job_name}: job must be an object")
            continue

        # Runner check: standard GitHub-hosted runners only.  The canonical
        # APGR suite is macOS arm64 because its qualified Node/browser inputs
        # are Darwin-specific; all other lanes use standard Ubuntu.
        runs_on = job_doc.get("runs-on")
        if runs_on not in STANDARD_RUNNERS:
            errors.append(
                f"{path.name}:{job_name}: runs-on must be a standard runner, got {runs_on!r}"
            )
        if job_name == "unit-integration" and runs_on != "macos-15":
            errors.append(f"{path.name}:unit-integration: runs-on must be 'macos-15'")
        if job_name not in {"unit-integration"} and runs_on == "macos-15":
            errors.append(f"{path.name}:{job_name}: macos-15 is reserved for unit-integration")

        if job_name in GUARDED_JOBS:
            condition = str(job_doc.get("if", ""))
            required_guards = (
                "needs.guard.result == 'success'",
                EXPECTED_REPO,
                EXPECTED_REPO_ID,
                "github.base_ref == 'main'",
                "github.head_ref == 'staging'",
                "github.event.pull_request.head.repo.full_name == github.repository",
            )
            for guard in required_guards:
                if guard not in condition:
                    errors.append(f"{path.name}:{job_name}: missing job-level public guard {guard!r}")

        # Permissions check: CodeQL permissions only job; no publishing/OIDC
        job_perms = job_doc.get("permissions")
        if job_name == "codeql":
            expected_codeql_perms = {"contents": "read", "security-events": "write"}
            if job_perms != expected_codeql_perms:
                errors.append(
                    f"{path.name}:codeql: permissions must be {{contents: read, security-events: write}}, got {job_perms}"
                )
        elif job_perms is not None:
            if "id-token" in job_perms:
                errors.append(f"{path.name}:{job_name}: id-token write forbidden on public PR")
            if "security-events" in job_perms:
                errors.append(f"{path.name}:{job_name}: security-events write forbidden outside codeql job")
            if job_perms != {"contents": "read"}:
                errors.append(f"{path.name}:{job_name}: non-CodeQL job cannot increase permissions")

        # Step inspection
        steps = job_doc.get("steps", [])
        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            if uses:
                action_spec = uses.split("@")
                if len(action_spec) == 2:
                    action_ref = action_spec[1].strip()
                    if not SHA_PATTERN.match(action_ref):
                        errors.append(f"{path.name}:{job_name}: action {uses} not pinned to 40-char SHA")
                else:
                    errors.append(f"{path.name}:{job_name}: action {uses} not pinned to 40-char SHA")
            if "checkout" in str(uses).lower():
                with_params = step.get("with", {})
                if with_params.get("persist-credentials") is not False:
                    errors.append(f"{path.name}:{job_name}: checkout step must set persist-credentials: false")

        if job_name == "codeql":
            strategy = job_doc.get("strategy", {})
            matrix = strategy.get("matrix", {}) if isinstance(strategy, dict) else {}
            includes = matrix.get("include", []) if isinstance(matrix, dict) else []
            languages = {
                item.get("language")
                for item in includes
                if isinstance(item, dict)
            }
            if languages != EXPECTED_CODEQL_LANGUAGES:
                errors.append(
                    f"{path.name}:codeql: language matrix must be {sorted(EXPECTED_CODEQL_LANGUAGES)}, got {sorted(languages)}"
                )
            if len(includes) != len(languages):
                errors.append(f"{path.name}:codeql: language matrix contains duplicate members")

    # 5. Guard job checks
    guard_job = jobs.get("guard", {})
    guard_str = json.dumps(guard_job)
    if EXPECTED_REPO not in guard_str:
        errors.append(f"{path.name}: guard job must check repository {EXPECTED_REPO}")
    if EXPECTED_REPO_ID not in guard_str:
        errors.append(f"{path.name}: guard job must check repository ID {EXPECTED_REPO_ID}")
    if "staging" not in guard_str:
        errors.append(f"{path.name}: guard job must check head branch staging")

    gate = jobs.get("public-pr-gate", {})
    if "always()" not in str(gate.get("if", "")):
        errors.append(f"{path.name}: aggregate must run with always()")
    if set(gate.get("needs", [])) != REQUIRED_PR_JOBS - {"public-pr-gate"}:
        errors.append(f"{path.name}: aggregate dependency inventory is incomplete")
    if "--statuses-json" not in json.dumps(gate):
        errors.append(f"{path.name}: aggregate must inspect actual needs results")

    return errors


def validate_release_yml(doc: dict[str, Any], path: Path) -> list[str]:
    errors = []

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

    publish = jobs["publish"]
    if not isinstance(publish, dict):
        errors.append(f"{path.name}:publish: job must be an object")
        return errors

    # Runner check
    runs_on = publish.get("runs-on")
    if runs_on != "ubuntu-latest":
        errors.append(f"{path.name}:publish: runs-on must be ubuntu-latest, got {runs_on!r}")

    # Environment check
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

    for step in steps:
        if not isinstance(step, dict):
            continue
        uses = step.get("uses")
        if uses:
            action_spec = uses.split("@")
            if len(action_spec) == 2:
                action_ref = action_spec[1].strip()
                if not SHA_PATTERN.match(action_ref):
                    errors.append(f"{path.name}:publish: action {uses} not pinned to 40-char SHA")
            else:
                errors.append(f"{path.name}:publish: action {uses} not pinned to 40-char SHA")
        if "checkout" in str(uses).lower():
            with_params = step.get("with", {})
            if with_params.get("persist-credentials") is not False:
                errors.append(f"{path.name}:publish: checkout step must set persist-credentials: false")

    return errors


def validate_all_workflows() -> list[str]:
    if not WORKFLOWS_DIR.is_dir():
        return ["missing .github/workflows directory"]
    errors = []
    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    for wf in workflow_files:
        try:
            doc = load_workflow_doc(wf)
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            errors.append(f"{wf.name}: parse error: {error}")
            continue

        if wf.name in {"public-pr.yml", "public-pr.yaml"}:
            errors.extend(validate_public_pr(doc, wf))
        elif wf.name in {"release.yml", "release.yaml"}:
            errors.extend(validate_release_yml(doc, wf))
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
