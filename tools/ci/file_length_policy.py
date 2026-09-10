#!/usr/bin/env python3
"""APGR deterministic tracked-Python file-length policy and gate.

Provenance notice:
Adapted from RepoMap tools/ci/file_length_policy.py and tools/ci/check_file_lengths.py
(RepoMap project, AGPL-3.0-or-later; see the existing attribution in NOTICE).
Extended for APGR manager-authorized file-length gate with per-file no-growth allowances
for pre-existing READINESS2 oversized files and unified tracked Python candidate census.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

if __package__ in (None, ""):
    tools_root = Path(__file__).resolve().parents[2]
    if str(tools_root) not in sys.path:
        sys.path.insert(0, str(tools_root))

from tools.ci.python_inventory import (
    PythonInventoryOperationalError,
    discover_python_inventory,
)

PROFILE_NAME = "file-length"
PROTOCOL_VERSION = 1
DEFAULT_WARNING_LIMIT = 400
DEFAULT_FAILURE_LIMIT = 1000
EXPECTED_SCHEMA = "apg-file-length-policy-v1"

Severity = Literal["warning", "failure"]
Status = Literal["passed", "passed_with_warnings", "failed"]


class FileLengthOperationalError(RuntimeError):
    """Report an operational failure or invalid policy separately from a policy violation."""


@dataclass(frozen=True, slots=True)
class Allowance:
    """A per-file no-growth allowance record for a pre-existing oversized file."""

    path: str
    role: str
    owner: str
    sha256: str
    count: int
    rationale: str
    maintenance: str

    def to_jsonable(self) -> dict[str, object]:
        return {
            "path": self.path,
            "role": self.role,
            "owner": self.owner,
            "sha256": self.sha256,
            "count": self.count,
            "rationale": self.rationale,
            "maintenance": self.maintenance,
        }


@dataclass(frozen=True, slots=True)
class Policy:
    """The immutable parsed policy specification."""

    schema: str
    warning_limit: int
    failure_limit: int
    allowances: dict[str, Allowance]


@dataclass(frozen=True, slots=True)
class Finding:
    """A warning or failure emitted during file-length scanning."""

    path: str
    line_count: int
    severity: Severity
    allowed_count: int | None = None
    message: str = ""

    def to_jsonable(self) -> dict[str, object]:
        doc: dict[str, object] = {
            "path": self.path,
            "line_count": self.line_count,
            "severity": self.severity,
        }
        if self.allowed_count is not None:
            doc["allowed_count"] = self.allowed_count
        if self.message:
            doc["message"] = self.message
        return doc


@dataclass(frozen=True, slots=True)
class FileLengthResult:
    """The stable result contract for one completed repository scan."""

    status: Status
    scanned_file_count: int
    warning_count: int
    failure_count: int
    findings: tuple[Finding, ...]
    warning_limit: int = DEFAULT_WARNING_LIMIT
    failure_limit: int = DEFAULT_FAILURE_LIMIT
    allowances_count: int = 0
    excluded_counts: dict[str, int] | None = None
    unmatched_allowances: tuple[str, ...] = ()

    def to_jsonable(self) -> dict[str, object]:
        return {
            "version": PROTOCOL_VERSION,
            "profile": PROFILE_NAME,
            "status": self.status,
            "warning_limit": self.warning_limit,
            "failure_limit": self.failure_limit,
            "scanned_file_count": self.scanned_file_count,
            "warning_count": self.warning_count,
            "failure_count": self.failure_count,
            "findings": [finding.to_jsonable() for finding in self.findings],
            "allowances_count": self.allowances_count,
            "unmatched_allowances": list(self.unmatched_allowances),
            "excluded_counts": self.excluded_counts,
        }


def count_physical_lines(path: Path) -> int:
    """Count LF-delimited physical lines: empty=0, final unterminated=1."""
    line_count = 0
    final_byte: int | None = None
    try:
        with path.open("rb") as source:
            while chunk := source.read(64 * 1024):
                line_count += chunk.count(b"\n")
                final_byte = chunk[-1]
    except OSError as error:
        raise FileLengthOperationalError(
            f"unable to read file: {path}"
        ) from error
    if final_byte is not None and final_byte != ord("\n"):
        line_count += 1
    return line_count


def classify_line_count(
    line_count: int,
    allowance_count: int | None = None,
    warning_limit: int = DEFAULT_WARNING_LIMIT,
    failure_limit: int = DEFAULT_FAILURE_LIMIT,
) -> tuple[Severity | None, str]:
    """Classify physical line count against warning/failure limits and allowances."""
    if line_count > failure_limit:
        if allowance_count is not None:
            if line_count > allowance_count:
                return (
                    "failure",
                    f"retained oversized file grew beyond allowance: {line_count} > {allowance_count}",
                )
            return (
                "warning",
                f"retained oversized file within allowance: {line_count} <= {allowance_count}",
            )
        return (
            "failure",
            f"file exceeds failure limit without allowance: {line_count} > {failure_limit}",
        )
    if line_count > warning_limit:
        return "warning", f"file exceeds warning limit: {line_count} > {warning_limit}"
    return None, ""


def load_policy(policy_path: Path) -> Policy:
    """Load and strictly validate a file-length policy JSON specification."""
    if not policy_path.is_file():
        raise FileLengthOperationalError(
            f"policy file does not exist: {policy_path}"
        )
    try:
        raw_text = policy_path.read_text(encoding="utf-8")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise FileLengthOperationalError("duplicate policy JSON key")
                result[key] = value
            return result
        data = json.loads(raw_text, object_pairs_hook=unique)
    except UnicodeError as error:
        raise FileLengthOperationalError(
            f"policy file is not valid UTF-8: {policy_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise FileLengthOperationalError(
            f"malformed policy JSON: {error}"
        ) from error

    if not isinstance(data, dict):
        raise FileLengthOperationalError("policy document must be a JSON object")

    schema = data.get("schema")
    if schema != EXPECTED_SCHEMA:
        raise FileLengthOperationalError(
            f"unsupported policy schema: {schema!r}, expected {EXPECTED_SCHEMA!r}"
        )
    if set(data) != {"schema", "warning_limit", "failure_limit", "allowances"}:
        raise FileLengthOperationalError("policy fields differ from the closed contract")

    warning_limit = data["warning_limit"]
    failure_limit = data["failure_limit"]
    if (type(warning_limit) is not int or type(failure_limit) is not int
            or (warning_limit, failure_limit) != (400, 1000)):
        raise FileLengthOperationalError("policy requires warning_limit=400 and failure_limit=1000")
    if not isinstance(warning_limit, int) or warning_limit <= 0:
        raise FileLengthOperationalError(
            f"warning_limit must be a positive integer, got: {warning_limit!r}"
        )
    if not isinstance(failure_limit, int) or failure_limit <= 0:
        raise FileLengthOperationalError(
            f"failure_limit must be a positive integer, got: {failure_limit!r}"
        )
    if failure_limit < warning_limit:
        raise FileLengthOperationalError(
            f"failure_limit ({failure_limit}) cannot be less than warning_limit ({warning_limit})"
        )

    raw_allowances = data.get("allowances")
    if not isinstance(raw_allowances, list):
        raise FileLengthOperationalError("policy allowances must be a JSON array")

    allowances: dict[str, Allowance] = {}
    seen_paths: set[str] = set()

    for idx, raw in enumerate(raw_allowances):
        if not isinstance(raw, dict):
            raise FileLengthOperationalError(
                f"allowance entry at index {idx} is not a JSON object"
            )
        if set(raw) != {"path", "role", "owner", "sha256", "count", "rationale", "maintenance"}:
            raise FileLengthOperationalError("allowance fields differ from the closed contract")
        for req_field in (
            "path",
            "role",
            "owner",
            "sha256",
            "count",
            "rationale",
            "maintenance",
        ):
            if req_field not in raw:
                raise FileLengthOperationalError(
                    f"allowance entry at index {idx} is missing required field: {req_field!r}"
                )

        rel_path = raw["path"]
        if not isinstance(rel_path, str) or not rel_path:
            raise FileLengthOperationalError(
                f"allowance at index {idx} has invalid path: {rel_path!r}"
            )
        posix = PurePosixPath(rel_path)
        if posix.is_absolute() or ".." in posix.parts:
            raise FileLengthOperationalError(
                f"allowance path escapes repository root: {rel_path!r}"
            )
        if rel_path != posix.as_posix():
            raise FileLengthOperationalError(
                f"allowance path is non-canonical: {rel_path!r}"
            )

        if rel_path in seen_paths:
            raise FileLengthOperationalError(
                f"duplicate allowance path detected: {rel_path!r}"
            )
        seen_paths.add(rel_path)

        count = raw["count"]
        if type(count) is not int or count <= failure_limit:
            raise FileLengthOperationalError(
                f"allowance count for {rel_path} must be an integer > failure_limit ({failure_limit}), got: {count!r}"
            )

        sha256 = raw["sha256"]
        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or not all(c in "0123456789abcdef" for c in sha256.lower())
        ):
            raise FileLengthOperationalError(
                f"allowance sha256 for {rel_path} must be a 64-char hex string, got: {sha256!r}"
            )

        role = raw["role"]
        owner = raw["owner"]
        rationale = raw["rationale"]
        maintenance = raw["maintenance"]
        if not all(
            isinstance(v, str) and v.strip()
            for v in (role, owner, rationale, maintenance)
        ):
            raise FileLengthOperationalError(
                f"allowance fields (role, owner, rationale, maintenance) for {rel_path} must be non-empty strings"
            )

        allowances[rel_path] = Allowance(
            path=rel_path,
            role=role,
            owner=owner,
            sha256=sha256.lower(),
            count=count,
            rationale=rationale,
            maintenance=maintenance,
        )

    return Policy(
        schema=schema,
        warning_limit=warning_limit,
        failure_limit=failure_limit,
        allowances=allowances,
    )


def evaluate_repository(
    repo_root: Path,
    policy: Policy | None = None,
    *,
    policy_path: Path | None = None,
    include_untracked: bool = False,
) -> FileLengthResult:
    """Evaluate repository tracked Python files against manager file-length policy."""
    if policy is None:
        if policy_path is None:
            policy_path = repo_root / "tools/ci/file_length_policy.json"
        policy = load_policy(policy_path)

    try:
        inventory = discover_python_inventory(
            repo_root,
            include_untracked=include_untracked,
        )
    except PythonInventoryOperationalError as error:
        raise FileLengthOperationalError(str(error)) from error

    findings: list[Finding] = []

    for entry in inventory.entries:
        allowance = policy.allowances.get(entry.path)
        allowance_count = allowance.count if allowance is not None else None
        severity, message = classify_line_count(
            entry.line_count,
            allowance_count=allowance_count,
            warning_limit=policy.warning_limit,
            failure_limit=policy.failure_limit,
        )
        if severity is not None:
            findings.append(
                Finding(
                    path=entry.path,
                    line_count=entry.line_count,
                    severity=severity,
                    allowed_count=allowance_count,
                    message=message,
                )
            )

    severity_order = {"failure": 0, "warning": 1}
    findings.sort(
        key=lambda finding: (
            severity_order[finding.severity],
            -finding.line_count,
            finding.path,
        )
    )

    warning_count = sum(f.severity == "warning" for f in findings)
    failure_count = sum(f.severity == "failure" for f in findings)
    if failure_count:
        status: Status = "failed"
    elif warning_count:
        status = "passed_with_warnings"
    else:
        status = "passed"

    matched_allowance_paths = {finding.path for finding in findings if finding.allowed_count is not None}
    unmatched_allowances = tuple(sorted(path for path in policy.allowances if path not in matched_allowance_paths))

    return FileLengthResult(
        status=status,
        scanned_file_count=inventory.total_files,
        warning_count=warning_count,
        failure_count=failure_count,
        findings=tuple(findings),
        warning_limit=policy.warning_limit,
        failure_limit=policy.failure_limit,
        allowances_count=len(policy.allowances),
        unmatched_allowances=unmatched_allowances,
        excluded_counts=inventory.excluded_counts,
    )


def render_json(result: FileLengthResult) -> str:
    """Render deterministic UTF-8 JSON report."""
    return json.dumps(result.to_jsonable(), indent=2, sort_keys=True) + "\n"


def _escape_text_path(path: str) -> str:
    return json.dumps(path, ensure_ascii=True)[1:-1]


def render_text(result: FileLengthResult) -> str:
    """Render human-readable report."""
    status_text = {
        "passed": "passed",
        "passed_with_warnings": "passed with warnings",
        "failed": "failed",
    }[result.status]
    lines = [
        f"file-length: {status_text}",
        f"limits: warning >{result.warning_limit}, failure >{result.failure_limit}",
        f"scanned: {result.scanned_file_count} Python files",
        f"warnings: {result.warning_count}",
        f"failures: {result.failure_count}",
    ]
    if result.findings:
        lines.append("")
        lines.extend(
            f"{finding.severity.upper():<7}  {finding.line_count:>4}  "
            f"{_escape_text_path(finding.path)}"
            for finding in result.findings
        )
    return "\n".join(lines) + "\n"


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="APGR manager-authorized file-length policy checker."
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(),
        help="explicit repository root for controlled invocation",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="explicit path to file_length_policy.json",
    )
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        default=False,
        help="include non-ignored untracked files for prospective capture testing",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        policy_path = (
            args.policy
            if args.policy is not None
            else args.repo_root / "tools/ci/file_length_policy.json"
        )
        policy = load_policy(policy_path)
        result = evaluate_repository(
            args.repo_root,
            policy=policy,
            include_untracked=args.include_untracked,
        )
        rendered = (
            render_json(result) if args.format == "json" else render_text(result)
        )
        sys.stdout.write(rendered)
    except FileLengthOperationalError as error:
        print(f"file-length: error: {error}", file=sys.stderr)
        return 2
    except PythonInventoryOperationalError as error:
        print(f"file-length: error: {error}", file=sys.stderr)
        return 2
    except (OSError, TypeError, UnicodeError, ValueError) as error:
        print(f"file-length: error: unable to complete profile: {error}", file=sys.stderr)
        return 2
    return 1 if result.failure_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
