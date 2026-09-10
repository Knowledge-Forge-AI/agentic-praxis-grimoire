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
WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/public-pr.yml"

DEFAULT_MEMBER_JOBS = {
    "guard",
    "static-analysis",
    "policy",
    "unit-integration",
    "closure",
    "go",
    "package",
    "sbom-and-vulnerability",
    "codeql-go",
    "codeql-python",
    "codeql-javascript-typescript",
    "codeql-actions",
}

VALID_STATUSES = {"success", "failure", "cancelled", "skipped"}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit_receipt(
    job_name: str,
    receipt_dir: Path,
    *,
    status: str = "success",
    artifacts: dict[str, str] | None = None,
    sha: str | None = None,
) -> Path:
    if job_name not in DEFAULT_MEMBER_JOBS:
        raise ValueError(f"unknown matrix member: {job_name}")
    if status not in VALID_STATUSES:
        raise ValueError(f"unknown member status: {status}")
    resolved_sha = sha or os.environ.get("COMMIT_SHA") or os.environ.get("GITHUB_SHA") or "unknown"
    if re.fullmatch(r"[0-9a-f]{40}", resolved_sha) is None:
        raise ValueError("receipt requires an exact tested commit SHA")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_dir / f"{job_name}-receipt.json"
    doc = {
        "schema": SCHEMA,
        "job": job_name,
        "status": status,
        "sha": resolved_sha,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "artifacts": artifacts or {},
        "pr_head_sha": os.environ.get("PR_HEAD_SHA", ""),
        "pr_base_sha": os.environ.get("PR_BASE_SHA", ""),
        "workflow_sha256": _digest(WORKFLOW),
    }
    receipt_path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt_path


def verify_matrix(
    receipt_dir: Path,
    expected_jobs: set[str] | None = None,
    expected_sha: str | None = None,
    expected_statuses: dict[str, str] | None = None,
    check_disk_artifacts: bool = True,
) -> tuple[bool, str, dict[str, Any]]:
    targets = expected_jobs if expected_jobs is not None else DEFAULT_MEMBER_JOBS
    if expected_sha is not None and re.fullmatch(r"[0-9a-f]{40}", expected_sha) is None:
        return False, "expected SHA must be an exact tested commit identity", {}
    if not receipt_dir.is_dir():
        return False, f"receipt directory not found: {receipt_dir}", {}

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

    # Preserve the artifact directory boundary. Flattening downloads before
    # this check could silently overwrite a duplicate matrix member.
    candidates: dict[str, list[Path]] = {}
    for path in sorted(receipt_dir.rglob("*-receipt.json")):
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

        status = doc.get("status")
        if status != "success":
            errors.append(f"job {job} did not succeed: status={status}")
            continue

        expected_status = expected_statuses.get(job)
        if needs_statuses_supplied and expected_status != "success":
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
        if doc.get("workflow_sha256") != _digest(WORKFLOW):
            errors.append(f"workflow policy digest mismatch for job {job}")

        # Verify artifacts if specified
        artifacts = doc.get("artifacts", {})
        if not isinstance(artifacts, dict):
            errors.append(f"malformed artifact inventory for job: {job}")
        elif check_disk_artifacts:
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

    success = len(errors) == 0
    aggregate_doc = {
        "schema": "apg-matrix-aggregate-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "required_members_count": len(targets),
        "verified_members_count": len(receipts),
        "errors": errors,
        "members": receipts,
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

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--dir", required=True, type=Path)
    verify_parser.add_argument("--sha", required=True)
    verify_parser.add_argument("--statuses-json", required=True)

    args = parser.parse_args(argv)

    if args.command == "emit":
        artifacts = {}
        args.dir.mkdir(parents=True, exist_ok=True)
        for source in args.artifact:
            if source.is_symlink() or not source.is_file() or source.name in artifacts:
                raise ValueError("receipt artifact must be a distinct direct file")
            payload = source.read_bytes()
            (args.dir / source.name).write_bytes(payload)
            artifacts[source.name] = hashlib.sha256(payload).hexdigest()
        p = emit_receipt(args.job, args.dir, status=args.status, sha=args.sha, artifacts=artifacts)
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
        )
        print(json.dumps(doc, indent=2, sort_keys=True))
        if not ok:
            print(f"FAILED: {msg}", file=sys.stderr)
            return 1
        print(f"PASSED: {msg}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
