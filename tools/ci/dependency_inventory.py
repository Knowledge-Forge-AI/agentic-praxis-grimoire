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
import json
import subprocess
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
    "semgrep==1.174.0",
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


def parse_audit_output(stdout: str, *, returncode: int) -> dict[str, Any]:
    """Classify one pip-audit JSON result, including zero-exit findings."""
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

    findings = sum(
        len(item.get("vulns", []))
        for item in records
        if isinstance(item.get("vulns", []), list)
    )
    if any(not isinstance(item.get("vulns", []), list) for item in records):
        return {
            "status": "tool-failure",
            "classification": "tool-failure",
            "detail": "pip-audit vulnerability collection is malformed",
            "dependencies": records,
            "finding_count": findings,
            "returncode": returncode,
        }
    if returncode not in {0, 1}:
        status = "tool-failure"
        classification = "tool-failure"
        detail = f"pip-audit operational failure: exit={returncode}"
    elif findings:
        status = "policy-finding"
        classification = "policy-finding"
        detail = f"pip-audit findings={findings}"
    else:
        status = "passed"
        classification = "passed"
        detail = f"pip-audit resolved dependencies={len(records)}; findings=0"
    return {
        "status": status,
        "classification": classification,
        "detail": detail,
        "dependencies": records,
        "finding_count": findings,
        "resolved_count": len(records),
        "returncode": returncode,
    }


def audit_inventory(
    name: str,
    descriptor: dict[str, Any],
    auditor: str,
    scratch_dir: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
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
        result = parse_audit_output(completed.stdout, returncode=completed.returncode)
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
) -> dict[str, Any]:
    """Audit all separate inventories and aggregate without hiding failures."""
    inventories = build_inventories(root)
    if scratch_dir is None:
        with tempfile.TemporaryDirectory(prefix="apgr-dependency-audit-") as raw:
            return audit_all(auditor, root, Path(raw), runner=runner)
    results = [
        audit_inventory(name, descriptor, auditor, scratch_dir, runner=runner)
        for name, descriptor in inventories.items()
    ]
    findings = sum(item["finding_count"] for item in results)
    tool_failures = sum(item["classification"] == "tool-failure" for item in results)
    policy_findings = sum(item["classification"] == "policy-finding" for item in results)
    if tool_failures:
        status = "tool-failure"
        classification = "tool-failure"
    elif policy_findings:
        status = "policy-finding"
        classification = "policy-finding"
    else:
        status = "passed"
        classification = "passed"
    return {
        "schema": SCHEMA,
        "status": status,
        "classification": classification,
        "inventories": results,
        "finding_count": findings,
        "tool_failure_count": tool_failures,
        "policy_finding_count": policy_findings,
    }


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
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["classification"] == "tool-failure":
        return 2
    if report["classification"] == "policy-finding":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
