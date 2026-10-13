#!/usr/bin/env python3
"""Audit APGR runtime, test, and CI Python dependency inventories.

The inventories are deliberately separate.  The runtime inventory includes the
conditional Python 3.10 ``tomli`` fallback from ``pyproject.toml``; the test
inventory reads the maintained test requirements; and the CI inventory records
the exact Python tools installed by the public static lane.  pip-audit resolves
each inventory independently, so transitive dependencies are included without
installing into the repository or changing project constraints.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

RUNTIME_FALLBACK = {
    "declared": "tomli>=2.0.1; python_version < '3.11'",
    "audit_requirement": "tomli==2.0.1",
    "reason": "Python 3.10 runtime fallback declared by pyproject.toml",
}
CI_REQUIREMENTS = (
    "ruff==0.9.10",
    "mypy==1.15.0",
    "pip-audit==2.10.1",
    "semgrep==1.179.0",
    "tomli==2.4.1",
)
SCHEMA = "apg-dependency-audit-v1"


def _requirement_lines(path: Path) -> list[str]:
    """Read non-comment requirement lines without changing their source bytes."""
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lines:
        raise ValueError(f"dependency inventory is empty: {path.name}")
    if any(line.startswith(("-", "--")) for line in lines):
        raise ValueError(f"dependency inventory contains an unsupported option: {path.name}")
    return lines


def build_inventories(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """Build the public inventory descriptors used by the auditor."""
    pyproject = root / "pyproject.toml"
    test_requirements = root / "requirements/test.txt"
    if not pyproject.is_file():
        raise FileNotFoundError("pyproject.toml is missing")
    if not test_requirements.is_file():
        raise FileNotFoundError("requirements/test.txt is missing")

    # The project metadata is the authority for the marker.  The audit input is
    # intentionally exact so that the fallback is checked even on Python 3.13.
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10 uses the declared tomli fallback.
        import tomli as tomllib

    document = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    declared = document.get("project", {}).get("dependencies", [])
    if RUNTIME_FALLBACK["declared"] not in declared:
        raise ValueError("pyproject.toml does not declare the conditional tomli fallback")

    return {
        "runtime": {
            "source": "pyproject.toml",
            "requirements": [RUNTIME_FALLBACK["audit_requirement"]],
            "declared": [RUNTIME_FALLBACK["declared"]],
            "marker": "python_version < '3.11'",
            "reason": RUNTIME_FALLBACK["reason"],
        },
        "test": {
            "source": "requirements/test.txt",
            "requirements": _requirement_lines(test_requirements),
            "declared": [],
            "marker": None,
            "reason": "maintained APGR test runtime requirements",
        },
        "ci-tools": {
            "source": "public-pr-ci static bootstrap",
            "requirements": list(CI_REQUIREMENTS),
            "declared": [],
            "marker": None,
            "reason": "static-lane tools, audited with their transitive dependencies",
        },
    }


def _audit_records(document: object) -> list[dict[str, Any]]:
    """Extract pip-audit's dependency records from supported JSON envelopes."""
    if isinstance(document, list):
        records = document
    elif isinstance(document, dict) and isinstance(document.get("dependencies"), list):
        records = document["dependencies"]
    else:
        raise TypeError("pip-audit JSON has no dependency collection")
    if not records or not all(isinstance(item, dict) for item in records):
        raise ValueError("pip-audit dependency collection is empty or malformed")
    return records


ALLOWED_EXCEPTION_SCOPES = frozenset({"ci-tools"})
EXCEPTION_SCHEMA = "apg-dependency-exceptions-v1"
EXCEPTION_KEYS = frozenset({
    "package",
    "version",
    "scope",
    "advisories",
    "expiry",
    "review",
    "trigger",
})


def validate_dependency_exceptions(exceptions: list[dict[str, Any]], *, today: date | None = None) -> None:
    """Validate dependency exceptions against the strict closed contract."""
    if not isinstance(exceptions, list):
        raise ValueError("dependency exceptions must be a list")
    if today is None:
        today = date.today()

    for idx, exc in enumerate(exceptions):
        if not isinstance(exc, dict):
            raise ValueError(f"exception at index {idx} must be a dictionary")
        if set(exc.keys()) != EXCEPTION_KEYS:
            raise ValueError(
                f"exception at index {idx} keys differ from closed contract: {set(exc.keys()) ^ EXCEPTION_KEYS}"
            )

        pkg = exc.get("package")
        if not isinstance(pkg, str) or not pkg.strip():
            raise ValueError(f"exception at index {idx} package must be a non-empty string")

        version = exc.get("version")
        if not isinstance(version, str) or not version.strip() or "*" in version:
            raise ValueError(
                f"exception at index {idx} version must be a non-empty exact version string without wildcards"
            )

        scope = exc.get("scope")
        if scope not in ALLOWED_EXCEPTION_SCOPES:
            raise ValueError(
                f"exception at index {idx} scope {scope!r} is not permitted; allowed: {sorted(ALLOWED_EXCEPTION_SCOPES)}"
            )

        advisories = exc.get("advisories")
        if (
            not isinstance(advisories, list)
            or not advisories
            or not all(isinstance(a, str) and a.strip() for a in advisories)
        ):
            raise ValueError(f"exception at index {idx} advisories must be a non-empty list of non-empty strings")
        if len(advisories) != len(set(advisories)):
            raise ValueError(f"exception at index {idx} advisories contains duplicates")

        expiry_str = exc.get("expiry")
        if not isinstance(expiry_str, str):
            raise ValueError(f"exception at index {idx} expiry must be an ISO date string")
        try:
            exp_date = date.fromisoformat(expiry_str)
        except ValueError as err:
            raise ValueError(f"exception at index {idx} expiry is not a valid ISO date: {err}") from err
        if exp_date < today:
            raise ValueError(
                f"exception at index {idx} for {pkg}=={version} expired on {expiry_str} (today is {today.isoformat()})"
            )

        review = exc.get("review")
        if not isinstance(review, str) or not review.strip():
            raise ValueError(f"exception at index {idx} review must be a non-empty string")

        trigger = exc.get("trigger")
        if not isinstance(trigger, str) or not trigger.strip():
            raise ValueError(f"exception at index {idx} trigger must be a non-empty string")


def load_dependency_exceptions(path: Path | None = None, *, today: date | None = None) -> list[dict[str, Any]]:
    """Load and strictly validate reviewed dependency exceptions from JSON."""
    if path is None:
        path = ROOT / "tools/ci/dependency_exceptions.json"
    if not path.is_file():
        return []
    try:
        raw_text = path.read_text(encoding="utf-8")
        doc = json.loads(raw_text)
    except Exception as error:
        raise ValueError(f"failed to load dependency exceptions from {path}: {error}") from error

    if not isinstance(doc, dict):
        raise ValueError("dependency exceptions document must be a JSON object")

    if set(doc.keys()) != {"schema", "exceptions"}:
        raise ValueError(
            f"dependency exceptions document keys differ from closed contract: {set(doc.keys()) ^ {'schema', 'exceptions'}}"
        )

    if doc.get("schema") != EXCEPTION_SCHEMA:
        raise ValueError(
            f"unsupported dependency exceptions schema: {doc.get('schema')!r}, expected {EXCEPTION_SCHEMA!r}"
        )

    exceptions = doc.get("exceptions", [])
    validate_dependency_exceptions(exceptions, today=today)
    return exceptions


def parse_audit_output(
    stdout: str,
    *,
    returncode: int,
    inventory_name: str | None = None,
    exceptions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Classify one pip-audit JSON result, including zero-exit findings and scoped exceptions."""
    if not stdout.strip():
        return {
            "status": "tool-failure",
            "classification": "tool-failure",
            "detail": "pip-audit returned empty output",
            "dependencies": [],
            "finding_count": 0,
            "returncode": returncode,
        }
    try:
        document = json.loads(stdout)
        records = _audit_records(document)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return {
            "status": "tool-failure",
            "classification": "tool-failure",
            "detail": f"pip-audit output was malformed: {error}",
            "dependencies": [],
            "finding_count": 0,
            "returncode": returncode,
        }

    if any(not isinstance(item.get("vulns", []), list) for item in records):
        return {
            "status": "tool-failure",
            "classification": "tool-failure",
            "detail": "pip-audit vulnerability collection is malformed",
            "dependencies": records,
            "finding_count": 0,
            "returncode": returncode,
        }

    if exceptions is None and inventory_name:
        exceptions = load_dependency_exceptions()
    elif exceptions is None:
        exceptions = []

    excepted_vulns: list[dict[str, Any]] = []
    matched_exceptions: set[int] = set()
    matched_advisories: set[str] = set()
    unexcepted_findings = 0
    today = date.today()

    for item in records:
        pkg_name = str(item.get("name", "")).lower()
        pkg_version = str(item.get("version", ""))
        for vuln in item.get("vulns", []):
            vuln_id = str(vuln.get("id", ""))
            vuln_aliases = [str(a) for a in vuln.get("aliases", [])]
            all_ids = {vuln_id, *vuln_aliases}

            matched_exc = None
            if inventory_name:
                for idx, exc in enumerate(exceptions):
                    if (
                        exc.get("scope") == inventory_name
                        and exc.get("package", "").lower() == pkg_name
                        and exc.get("version") == pkg_version
                        and any(adv in exc.get("advisories", []) for adv in all_ids)
                    ):
                        try:
                            exp_date = date.fromisoformat(exc.get("expiry", "1970-01-01"))
                            if exp_date >= today:
                                matched_exc = exc
                                matched_exceptions.add(idx)
                                for adv in all_ids:
                                    if adv in exc.get("advisories", []):
                                        matched_advisories.add(adv)
                                break
                        except (ValueError, TypeError):
                            pass

            if matched_exc:
                excepted_vulns.append({
                    "package": pkg_name,
                    "version": pkg_version,
                    "advisory": vuln_id,
                    "expiry": matched_exc.get("expiry"),
                    "review": matched_exc.get("review"),
                })
            else:
                unexcepted_findings += 1

    if returncode not in {0, 1}:
        status = "tool-failure"
        classification = "tool-failure"
        detail = f"pip-audit operational failure: exit={returncode}"
    elif unexcepted_findings:
        status = "policy-finding"
        classification = "policy-finding"
        detail = f"pip-audit findings={unexcepted_findings}"
        if excepted_vulns:
            detail += f"; excepted={len(excepted_vulns)}"
    else:
        status = "passed"
        classification = "passed"
        if excepted_vulns:
            detail = f"pip-audit resolved dependencies={len(records)}; findings=0; excepted={len(excepted_vulns)}"
        else:
            detail = f"pip-audit resolved dependencies={len(records)}; findings=0"

    result: dict[str, Any] = {
        "status": status,
        "classification": classification,
        "detail": detail,
        "dependencies": records,
        "finding_count": unexcepted_findings,
        "resolved_count": len(records),
        "returncode": returncode,
        "matched_exception_indices": sorted(matched_exceptions),
        "matched_advisories": sorted(matched_advisories),
    }
    if excepted_vulns:
        result["excepted_count"] = len(excepted_vulns)
        result["excepted_vulnerabilities"] = excepted_vulns
    return result


def audit_inventory(
    name: str,
    descriptor: dict[str, Any],
    auditor: str,
    scratch_dir: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    exceptions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audit one descriptor through an external pip-audit executable."""
    scratch_dir.mkdir(parents=True, exist_ok=True)
    requirement_path = scratch_dir / f"{name.replace('-', '_')}.txt"
    requirement_path.write_text(
        "\n".join(descriptor["requirements"]) + "\n",
        encoding="utf-8",
    )
    command = [
        auditor,
        "--requirement",
        str(requirement_path),
        "--format",
        "json",
        "--progress-spinner",
        "off",
        "--strict",
    ]
    try:
        completed = runner(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as error:
        result = {
            "status": "tool-failure",
            "classification": "tool-failure",
            "detail": f"pip-audit invocation failed: {type(error).__name__}",
            "dependencies": [],
            "finding_count": 0,
            "returncode": None,
        }
    else:
        result = parse_audit_output(
            completed.stdout,
            returncode=completed.returncode,
            inventory_name=name,
            exceptions=exceptions,
        )
        if completed.stderr.strip() and result["status"] == "passed":
            result["stderr_present"] = True
    return {
        "name": name,
        "source": descriptor["source"],
        "declared": descriptor["declared"],
        "marker": descriptor["marker"],
        "reason": descriptor["reason"],
        **result,
    }


def audit_all(
    auditor: str,
    root: Path = ROOT,
    scratch_dir: Path | None = None,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    exceptions_file: Path | None = None,
) -> dict[str, Any]:
    """Audit all separate inventories and aggregate without hiding failures."""
    inventories = build_inventories(root)
    if scratch_dir is None:
        with tempfile.TemporaryDirectory(prefix="apgr-dependency-audit-") as raw:
            return audit_all(auditor, root, Path(raw), runner=runner, exceptions_file=exceptions_file)
    exceptions = load_dependency_exceptions(exceptions_file or (root / "tools/ci/dependency_exceptions.json"))
    results = [
        audit_inventory(name, descriptor, auditor, scratch_dir, runner=runner, exceptions=exceptions)
        for name, descriptor in inventories.items()
    ]
    findings = sum(item["finding_count"] for item in results)
    tool_failures = sum(item["classification"] == "tool-failure" for item in results)
    policy_findings = sum(item["classification"] == "policy-finding" for item in results)

    # Aggregate staleness evaluation across all inventories:
    all_matched_indices: set[int] = set()
    all_matched_advisories: set[str] = set()
    for item in results:
        all_matched_indices.update(item.get("matched_exception_indices", []))
        all_matched_advisories.update(item.get("matched_advisories", []))

    stale_exceptions = [
        exc for idx, exc in enumerate(exceptions)
        if idx not in all_matched_indices
    ]

    unmatched_aliases: dict[str, list[str]] = {}
    for idx, exc in enumerate(exceptions):
        if idx in all_matched_indices:
            unmatched = [adv for adv in exc.get("advisories", []) if adv not in all_matched_advisories]
            if unmatched:
                unmatched_aliases[f"{exc['package']}=={exc['version']}"] = unmatched

    stale_detail = None
    if stale_exceptions:
        stale_desc = [f"{e['package']}=={e['version']} (scope: {e['scope']})" for e in stale_exceptions]
        policy_findings += len(stale_exceptions)
        stale_detail = f"stale dependency exception(s) matching 0 vulnerabilities: {', '.join(stale_desc)}"

    if tool_failures:
        status = "tool-failure"
        classification = "tool-failure"
    elif policy_findings:
        status = "policy-finding"
        classification = "policy-finding"
    else:
        status = "passed"
        classification = "passed"

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": status,
        "classification": classification,
        "inventories": results,
        "finding_count": findings,
        "tool_failure_count": tool_failures,
        "policy_finding_count": policy_findings,
    }
    if stale_detail:
        report["stale_exceptions_detail"] = stale_detail
    if unmatched_aliases:
        report["unmatched_advisory_aliases"] = unmatched_aliases
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit separate APGR Python dependency inventories")
    parser.add_argument("--auditor", required=True)
    parser.add_argument("--scratch-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        report = audit_all(args.auditor, scratch_dir=args.scratch_dir)
    except (ImportError, OSError, TypeError, ValueError, UnicodeError) as error:
        report = {
            "schema": SCHEMA,
            "status": "tool-failure",
            "classification": "tool-failure",
            "detail": str(error),
            "inventories": [],
            "finding_count": 0,
            "tool_failure_count": 1,
            "policy_finding_count": 0,
        }
    for item in report.get("inventories", []):
        for exc in item.get("excepted_vulnerabilities", []):
            print(
                f"EXCEPTED: {exc['package']}=={exc['version']} ({exc['advisory']}, expiry {exc['expiry']})",
                file=sys.stderr,
            )
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["classification"] == "tool-failure":
        return 2
    if report["classification"] == "policy-finding":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
