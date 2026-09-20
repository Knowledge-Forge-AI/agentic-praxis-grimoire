#!/usr/bin/env python3
"""Matrix completeness and member receipt verification for APGR CI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "apg-matrix-receipt-v1"
PUBLIC_PR_WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/public-pr.yml"
NATIVE_QUALIFICATION_WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github/workflows/native-qualification.yml"
)

PUBLIC_PR_MEMBER_JOBS = {
    "guard",
    "static-analysis",
    "policy",
    "unit-integration",
    "closure",
    "go",
    "codeql-go",
    "codeql-python",
    "codeql-javascript-typescript",
    "codeql-actions",
}

NATIVE_MEMBER_JOBS = {
    "native-guard",
    "native-darwin-arm64",
    "native-linux-x64",
    "native-linux-arm64",
    "native-assemble",
    "native-consumer-darwin-arm64",
    "native-consumer-linux-x64",
    "native-consumer-linux-arm64",
    "native-release-scans",
}

# Default member jobs references public-pr for backward compatibility
DEFAULT_MEMBER_JOBS = PUBLIC_PR_MEMBER_JOBS

VALID_STATUSES = {"success", "failure", "cancelled", "skipped"}

PUBLIC_PR_MATRIX_GROUPS: dict[str, tuple[str, ...]] = {
    "codeql": ("codeql-go", "codeql-python", "codeql-javascript-typescript", "codeql-actions"),
}

PUBLIC_PR_PRESCRIBED_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "guard": (),
    "static-analysis": ("manifest.json",),
    "policy": (),
    "unit-integration": ("apgr-unit-integration-summary.json",),
    "closure": (),
    "go": (),
    "codeql-go": ("codeql-go.sarif",),
    "codeql-python": ("codeql-python.sarif",),
    "codeql-javascript-typescript": ("codeql-javascript-typescript.sarif",),
    "codeql-actions": ("codeql-actions.sarif",),
}

NATIVE_MATRIX_GROUPS: dict[str, tuple[str, ...]] = {}

NATIVE_PRESCRIBED_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "native-guard": ("identity.json",),
    "native-darwin-arm64": ("lane-seal.json",),
    "native-linux-x64": ("lane-seal.json",),
    "native-linux-arm64": ("lane-seal.json",),
    "native-assemble": ("release-bundle-seal.json", "public-projection-manifest.json"),
    "native-consumer-darwin-arm64": ("consumer-receipt.json",),
    "native-consumer-linux-x64": ("consumer-receipt.json",),
    "native-consumer-linux-arm64": ("consumer-receipt.json",),
    "native-release-scans": ("scan-receipt.json",),
}

PRESCRIBED_JOB_ARTIFACTS = PUBLIC_PR_PRESCRIBED_ARTIFACTS
MATRIX_GROUPS = PUBLIC_PR_MATRIX_GROUPS
WORKFLOW = PUBLIC_PR_WORKFLOW


class ProfileConfig:
    def __init__(
        self,
        name: str,
        workflow_path: Path,
        member_jobs: set[str],
        matrix_groups: dict[str, tuple[str, ...]],
        prescribed_artifacts: dict[str, tuple[str, ...]],
        require_pr_identity: bool = False,
    ):
        self.name = name
        self.workflow_path = workflow_path
        self.member_jobs = member_jobs
        self.matrix_groups = matrix_groups
        self.prescribed_artifacts = prescribed_artifacts
        self.require_pr_identity = require_pr_identity


PROFILES: dict[str, ProfileConfig] = {
    "public-pr": ProfileConfig(
        name="public-pr",
        workflow_path=PUBLIC_PR_WORKFLOW,
        member_jobs=PUBLIC_PR_MEMBER_JOBS,
        matrix_groups=PUBLIC_PR_MATRIX_GROUPS,
        prescribed_artifacts=PUBLIC_PR_PRESCRIBED_ARTIFACTS,
    ),
    "native-qualification": ProfileConfig(
        name="native-qualification",
        workflow_path=NATIVE_QUALIFICATION_WORKFLOW,
        member_jobs=NATIVE_MEMBER_JOBS,
        matrix_groups=NATIVE_MATRIX_GROUPS,
        prescribed_artifacts=NATIVE_PRESCRIBED_ARTIFACTS,
        require_pr_identity=True,
    ),
}


def get_profile(name: str | None = None) -> ProfileConfig:
    key = name or "public-pr"
    if key not in PROFILES:
        raise ValueError(f"unknown workflow profile: {key}")
    return PROFILES[key]


def _digest(path: Path) -> str:
    if not path.is_file():
        return "0" * 64
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit_receipt(
    job_name: str,
    receipt_dir: Path,
    *,
    status: str = "success",
    artifacts: dict[str, str] | None = None,
    sha: str | None = None,
    unavailable_artifacts: list[str] | None = None,
    workflow: str = "public-pr",
    profile: str | None = None,
) -> Path:
    prof = get_profile(profile or workflow)

    if job_name not in prof.member_jobs:
        raise ValueError(f"unknown matrix member: {job_name}")
    if status not in VALID_STATUSES:
        raise ValueError(f"unknown member status: {status}")
    resolved_sha = sha or os.environ.get("COMMIT_SHA") or os.environ.get("GITHUB_SHA") or "unknown"
    if re.fullmatch(r"[0-9a-f]{40}", resolved_sha) is None:
        raise ValueError("receipt requires an exact tested commit SHA")
    if status == "success" and unavailable_artifacts:
        raise ValueError("successful job cannot have unavailable artifacts")
    if not prof.workflow_path.is_file():
        raise ValueError(f"workflow policy file missing for profile: {prof.name}")
    if status == "success" and prof.require_pr_identity:
        for env_name in ("PR_HEAD_SHA", "PR_BASE_SHA"):
            if re.fullmatch(r"[0-9a-f]{40}", os.environ.get(env_name, "")) is None:
                raise ValueError(f"{prof.name} receipt requires an exact {env_name}")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{job_name}-receipt.json"
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "job": job_name,
        "workflow": prof.name,
        "status": status,
        "sha": resolved_sha,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts or {},
        "pr_head_sha": os.environ.get("PR_HEAD_SHA", ""),
        "pr_base_sha": os.environ.get("PR_BASE_SHA", ""),
        "workflow_sha256": _digest(prof.workflow_path),
    }
    if unavailable_artifacts:
        doc["unavailable_artifacts"] = list(unavailable_artifacts)
    receipt_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt_path


def verify_matrix(
    receipt_dir: Path,
    expected_jobs: set[str] | None = None,
    expected_sha: str | None = None,
    expected_statuses: dict[str, str] | None = None,
    check_disk_artifacts: bool = True,
    workflow: str = "public-pr",
    profile: str | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    prof = get_profile(profile or workflow)
    targets = expected_jobs if expected_jobs is not None else prof.member_jobs
    matrix_groups = prof.matrix_groups
    prescribed_artifacts = prof.prescribed_artifacts
    workflow_path = prof.workflow_path

    if expected_sha is not None and re.fullmatch(r"[0-9a-f]{40}", expected_sha) is None:
        return False, "expected SHA must be an exact tested commit identity", {}
    if not receipt_dir.is_dir():
        return False, f"receipt directory not found: {receipt_dir}", {}
    if not workflow_path.is_file():
        return False, f"workflow policy file missing for profile: {prof.name}", {}
    if prof.require_pr_identity:
        for env_name in ("PR_HEAD_SHA", "PR_BASE_SHA"):
            if re.fullmatch(r"[0-9a-f]{40}", os.environ.get(env_name, "")) is None:
                return False, f"{prof.name} verification requires an exact {env_name}", {}

    needs_statuses_supplied = expected_statuses is not None
    expected_statuses = expected_statuses or {}
    unknown_status_jobs = set(expected_statuses) - set(targets)
    if unknown_status_jobs:
        return False, f"statuses supplied for unknown jobs: {sorted(unknown_status_jobs)}", {}
    invalid_statuses = {
        job: status
        for job, status in expected_statuses.items()
        if status not in VALID_STATUSES
    }
    if invalid_statuses:
        return False, f"invalid expected statuses: {invalid_statuses}", {}

    receipts: dict[str, Any] = {}
    errors: list[str] = []
    receipt_statuses: dict[str, str] = {}
    group_of = {member: group for group, members in matrix_groups.items() for member in members}
    failed_groups: dict[str, str] = {}

    candidates: dict[str, list[Path]] = {}
    # Native proof documents share the receipt suffix. Only files explicitly
    # hash-bound by a matrix member may be treated as collateral evidence.
    collateral: set[Path] = set()
    if prof.name == "native-qualification":
        for member in targets:
            for wrapper in receipt_dir.rglob(f"{member}-receipt.json"):
                if wrapper.is_symlink():
                    continue
                try:
                    document = json.loads(wrapper.read_text())
                    listed = document.get("artifacts", {})
                    if document.get("schema") != SCHEMA or document.get("job") != member or not isinstance(listed, dict):
                        continue
                    for relative, expected in listed.items():
                        if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
                            continue
                        proof = wrapper.parent / relative
                        if proof.name in {"consumer-receipt.json", "scan-receipt.json"} and proof.is_file() and not proof.is_symlink() and _digest(proof) == expected:
                            collateral.add(proof)
                except (OSError, ValueError, AttributeError):
                    continue
    for path in sorted(receipt_dir.rglob("*-receipt.json")):
        if path in collateral:
            continue
        name = path.name.removesuffix("-receipt.json")
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            errors.append(f"unsafe receipt path for job: {name}")
            continue
        if name not in targets:
            errors.append(f"unexpected receipt for job: {name}")
            continue
        candidates.setdefault(name, []).append(path)

    for job in sorted(targets):
        matches = candidates.get(job, [])
        if not matches:
            errors.append(f"missing receipt for job: {job}")
            continue
        if len(matches) != 1:
            errors.append(f"duplicate receipts for job: {job}")
            continue
        receipt_file = matches[0]

        try:
            content = receipt_file.read_text(encoding="utf-8")
            if not content.strip():
                errors.append(f"empty receipt for job: {job}")
                continue
            doc = json.loads(content)
        except (OSError, TypeError, UnicodeError, ValueError) as error:
            errors.append(f"malformed receipt for job: {job}: {error}")
            continue

        if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
            errors.append(f"invalid schema in receipt for job: {job}")
            continue
        if doc.get("job") != job:
            errors.append(f"receipt member identity mismatch for job: {job}")
            continue
        if doc.get("workflow") != prof.name:
            errors.append(f"receipt workflow profile mismatch for job: {job}")
            continue

        status = doc.get("status")
        receipt_statuses[job] = status if isinstance(status, str) else "malformed"
        if status != "success":
            errors.append(f"job {job} did not succeed: status={status}")
            continue

        unavailable = doc.get("unavailable_artifacts")
        if unavailable is not None:
            if not isinstance(unavailable, list):
                errors.append(f"malformed unavailable_artifacts for job: {job}")
            elif unavailable:
                errors.append(f"successful job {job} contains unavailable artifacts: {unavailable}")

        expected_status = expected_statuses.get(job)
        if needs_statuses_supplied and expected_status != "success":
            if job in group_of:
                failed_groups.setdefault(group_of[job], expected_status or "missing")
            else:
                errors.append(
                    f"job {job} needs result did not succeed: status={expected_status or 'missing'}"
                )

        sha = doc.get("sha")
        if expected_sha and sha != expected_sha:
            errors.append(f"SHA mismatch for job {job}: expected {expected_sha}, got {sha}")
        for field, env_name in (("pr_head_sha", "PR_HEAD_SHA"), ("pr_base_sha", "PR_BASE_SHA")):
            expected = os.environ.get(env_name)
            if expected and doc.get(field) != expected:
                errors.append(f"{field} mismatch for job {job}")
        if doc.get("workflow_sha256") != _digest(workflow_path):
            errors.append(f"workflow policy digest mismatch for job {job}")

        artifacts = doc.get("artifacts", {})
        if not isinstance(artifacts, dict):
            errors.append(f"malformed artifact inventory for job: {job}")
        elif check_disk_artifacts:
            for req_art in prescribed_artifacts.get(job, ()):
                if req_art not in artifacts:
                    errors.append(f"missing prescribed artifact for {job}: {req_art}")
            for rel_path, expected_hash in artifacts.items():
                if (
                    not isinstance(rel_path, str)
                    or Path(rel_path).is_absolute()
                    or ".." in Path(rel_path).parts
                    or not isinstance(expected_hash, str)
                    or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None
                ):
                    errors.append(f"unsafe artifact inventory for job: {job}")
                    continue
                art_file = receipt_file.parent / rel_path
                if not art_file.is_file() or art_file.is_symlink():
                    errors.append(f"missing receipt artifact for {job}: {rel_path}")
                    continue
                actual_hash = _digest(art_file)
                if actual_hash != expected_hash:
                    errors.append(
                        f"artifact digest substitution detected for {job} artifact {rel_path}: "
                        f"expected {expected_hash}, got {actual_hash}"
                    )

        receipts[job] = doc

    for group, group_status in sorted(failed_groups.items()):
        failing = [member for member in matrix_groups[group]
                   if member in targets and receipt_statuses.get(member) != "success"]
        errors.append(
            f"matrix {group} needs result did not succeed: status={group_status}; "
            + (f"failing member receipts: {', '.join(failing)}" if failing
               else "no member receipt reports failure")
        )

    success = len(errors) == 0
    aggregate_doc = {
        "schema": "apg-matrix-aggregate-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow": prof.name,
        "success": success,
        "required_members_count": len(targets),
        "verified_members_count": len(receipts),
        "errors": errors,
        "members": receipts,
        "member_receipt_status": {job: receipt_statuses.get(job, "missing") for job in sorted(targets)},
    }

    detail = "matrix completeness verified" if success else f"matrix verification failed: {'; '.join(errors)}"
    return success, detail, aggregate_doc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="APGR Matrix receipt manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    emit_parser = subparsers.add_parser("emit")
    emit_parser.add_argument("--job", required=True)
    emit_parser.add_argument("--dir", required=True, type=Path)
    emit_parser.add_argument("--status", default="success")
    emit_parser.add_argument("--sha", required=True)
    emit_parser.add_argument("--artifact", type=Path, action="append", default=[])
    emit_parser.add_argument("--workflow", "--profile", default="public-pr", dest="workflow")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--dir", required=True, type=Path)
    verify_parser.add_argument("--sha", required=True)
    verify_parser.add_argument("--statuses-json", required=True)
    verify_parser.add_argument("--workflow", "--profile", default="public-pr", dest="workflow")

    args = parser.parse_args(argv)

    if args.command == "emit":
        artifacts = {}
        unavailable_artifacts = []
        args.dir.mkdir(parents=True, exist_ok=True)
        for source in args.artifact:
            if source.is_symlink() or ".." in source.parts:
                raise ValueError("receipt artifact must be a safe path")
            if source.name in artifacts or source.name in unavailable_artifacts:
                raise ValueError("receipt artifact must be distinct")
            if not source.is_file():
                if args.status == "success":
                    raise ValueError(f"receipt artifact missing for successful job: {source}")
                unavailable_artifacts.append(source.name)
                continue
            payload = source.read_bytes()
            (args.dir / source.name).write_bytes(payload)
            artifacts[source.name] = hashlib.sha256(payload).hexdigest()
        p = emit_receipt(
            args.job,
            args.dir,
            status=args.status,
            sha=args.sha,
            artifacts=artifacts,
            unavailable_artifacts=unavailable_artifacts,
            workflow=args.workflow,
        )
        print(f"Emitted receipt for {args.job} at {p}")
        return 0

    if args.command == "verify":
        statuses = None
        if args.statuses_json:
            try:
                decoded = json.loads(args.statuses_json)
            except json.JSONDecodeError as error:
                print(f"FAILED: malformed --statuses-json: {error}", file=sys.stderr)
                return 2
            if not isinstance(decoded, dict) or not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in decoded.items()
            ):
                print("FAILED: --statuses-json must be an object of string statuses", file=sys.stderr)
                return 2
            statuses = decoded
        ok, msg, doc = verify_matrix(
            args.dir,
            expected_sha=args.sha,
            expected_statuses=statuses,
            workflow=args.workflow,
        )
        print(json.dumps(doc, indent=2, sort_keys=True))
        if not ok:
            print(f"FAILED: {msg}", file=sys.stderr)
            return 1
        print(f"PASSED: {msg}", file=sys.stderr)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
