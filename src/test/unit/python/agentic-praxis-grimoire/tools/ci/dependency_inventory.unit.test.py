"""Unit contracts for separate APGR dependency inventory auditing."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.ci.dependency_inventory import (
    audit_inventory,
    build_inventories,
    parse_audit_output,
)


def test_build_inventories_keeps_runtime_marker_and_separate_scopes() -> None:
    inventories = build_inventories()
    assert inventories["runtime"]["requirements"] == ["tomli==2.0.1"]
    assert inventories["runtime"]["marker"] == "python_version < '3.11'"
    assert inventories["test"]["source"] == "requirements/test.txt"
    assert "semgrep==1.174.0" in inventories["ci-tools"]["requirements"]
    assert inventories["runtime"]["source"] != inventories["ci-tools"]["source"]


def test_parse_audit_output_rejects_empty_and_malformed_results() -> None:
    empty = parse_audit_output("", returncode=0)
    assert empty["classification"] == "tool-failure"

    malformed = parse_audit_output("not json", returncode=0)
    assert malformed["classification"] == "tool-failure"

    clean = parse_audit_output(
        json.dumps([{"name": "tomli", "version": "2.0.1", "vulns": []}]),
        returncode=0,
    )
    assert clean["classification"] == "passed"


def test_parse_audit_output_retains_zero_exit_findings() -> None:
    finding = parse_audit_output(
        json.dumps([{"name": "tomli", "version": "2.0.1", "vulns": [{"id": "PYSEC-1"}]}]),
        returncode=0,
    )
    assert finding["classification"] == "policy-finding"
    assert finding["finding_count"] == 1


def test_audit_inventory_records_tool_failures_and_scope(tmp_path: Path) -> None:
    descriptor = {
        "source": "fixture",
        "requirements": ["tomli==2.0.1"],
        "declared": [],
        "marker": None,
        "reason": "fixture",
    }

    def runner(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["pip-audit"],
            returncode=2,
            stdout="{}",
            stderr="database unavailable",
        )

    result = audit_inventory("runtime", descriptor, "pip-audit", tmp_path, runner=runner)
    assert result["name"] == "runtime"
    assert result["classification"] == "tool-failure"
    assert (tmp_path / "runtime.txt").read_text(encoding="utf-8") == "tomli==2.0.1\n"
