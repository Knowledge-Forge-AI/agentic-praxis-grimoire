"""Unit contracts for separate APGR dependency inventory auditing."""

from __future__ import annotations

from datetime import date
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
    assert "semgrep==1.179.0" in inventories["ci-tools"]["requirements"]
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


def test_dependency_exceptions_scope_and_ratchet() -> None:
    exceptions = [
        {
            "package": "pyjwt",
            "version": "2.13.0",
            "scope": "ci-tools",
            "advisories": ["CVE-2022-29217", "GHSA-4897-c689-p66r"],
            "expiry": "2099-12-31",
            "review": "test exception",
            "trigger": "test trigger",
        }
    ]

    raw_output = json.dumps([
        {
            "name": "pyjwt",
            "version": "2.13.0",
            "vulns": [{"id": "CVE-2022-29217", "aliases": ["GHSA-4897-c689-p66r"]}],
        }
    ])

    # 1. Matching exception in ci-tools passes with 0 findings and records exception
    ci_res = parse_audit_output(
        raw_output,
        returncode=1,
        inventory_name="ci-tools",
        exceptions=exceptions,
    )
    assert ci_res["status"] == "passed"
    assert ci_res["classification"] == "passed"
    assert ci_res["finding_count"] == 0
    assert ci_res["excepted_count"] == 1
    assert "excepted=1" in ci_res["detail"]

    # 2. Same advisory in runtime inventory is NEVER excepted (scope enforcement)
    runtime_res = parse_audit_output(
        raw_output,
        returncode=1,
        inventory_name="runtime",
        exceptions=exceptions,
    )
    assert runtime_res["status"] == "policy-finding"
    assert runtime_res["classification"] == "policy-finding"
    assert runtime_res["finding_count"] == 1
    assert "excepted_count" not in runtime_res

    # 3. Unlisted advisory in ci-tools fails as policy-finding
    unlisted_output = json.dumps([
        {
            "name": "pyjwt",
            "version": "2.13.0",
            "vulns": [{"id": "CVE-9999-9999", "aliases": []}],
        }
    ])
    unlisted_res = parse_audit_output(
        unlisted_output,
        returncode=1,
        inventory_name="ci-tools",
        exceptions=exceptions,
    )
    assert unlisted_res["status"] == "policy-finding"
    assert unlisted_res["finding_count"] == 1

    # 4. Expired exception does not except
    expired_exceptions = [
        {
            "package": "pyjwt",
            "version": "2.13.0",
            "scope": "ci-tools",
            "advisories": ["CVE-2022-29217"],
            "expiry": "2020-01-01",
            "review": "expired",
            "trigger": "expired",
        }
    ]
    expired_res = parse_audit_output(
        raw_output,
        returncode=1,
        inventory_name="ci-tools",
        exceptions=expired_exceptions,
    )
    assert expired_res["status"] == "policy-finding"
    assert expired_res["finding_count"] == 1


def test_validate_dependency_exceptions_rejects_malformed_and_wildcards(tmp_path: Path) -> None:
    import pytest
    from tools.ci.dependency_inventory import (
        load_dependency_exceptions,
        validate_dependency_exceptions,
    )

    fixed_today = date(2026, 10, 1)
    valid_base = {
        "package": "pyjwt",
        "version": "2.13.0",
        "scope": "ci-tools",
        "advisories": ["CVE-2026-101917"],
        "expiry": "2026-11-01",
        "review": "test review",
        "trigger": "test trigger",
    }

    # 1. Valid base passes with fixed today
    validate_dependency_exceptions([valid_base], today=fixed_today)

    # 2. Missing/empty/wildcard version fails
    for bad_ver in (None, "", "  ", "*", "2.*"):
        case = dict(valid_base, version=bad_ver)
        with pytest.raises(ValueError, match="version"):
            validate_dependency_exceptions([case], today=fixed_today)

    # 3. Unpermitted scope fails
    for bad_scope in ("runtime", "test", "global", ""):
        case = dict(valid_base, scope=bad_scope)
        with pytest.raises(ValueError, match="scope"):
            validate_dependency_exceptions([case], today=fixed_today)

    # 4. Duplicate or empty advisories fail
    with pytest.raises(ValueError, match="advisories"):
        validate_dependency_exceptions([dict(valid_base, advisories=[])], today=fixed_today)
    with pytest.raises(ValueError, match="duplicates"):
        validate_dependency_exceptions([dict(valid_base, advisories=["CVE-1", "CVE-1"])], today=fixed_today)

    # 5. Invalid / expired expiry fails (preserving explicit expired assertions)
    with pytest.raises(ValueError, match="expiry"):
        validate_dependency_exceptions([dict(valid_base, expiry="invalid-date")], today=fixed_today)
    with pytest.raises(ValueError, match="expired"):
        validate_dependency_exceptions([dict(valid_base, expiry="2020-01-01")], today=fixed_today)

    # 6. Extra or missing keys fail
    with pytest.raises(ValueError, match="differ from closed contract"):
        extra = dict(valid_base, unexpected_field="bogus")
        validate_dependency_exceptions([extra], today=fixed_today)
    with pytest.raises(ValueError, match="differ from closed contract"):
        missing = dict(valid_base)
        del missing["review"]
        validate_dependency_exceptions([missing], today=fixed_today)

    # 7. load_dependency_exceptions raises on malformed document
    bad_doc_path = tmp_path / "bad_exceptions.json"
    bad_doc_path.write_text(json.dumps({"schema": "unknown-schema", "exceptions": []}))
    with pytest.raises(ValueError, match="unsupported dependency exceptions schema"):
        load_dependency_exceptions(bad_doc_path, today=fixed_today)


def test_parse_audit_output_exact_negative_controls() -> None:
    exceptions = [
        {
            "package": "pyjwt",
            "version": "2.13.0",
            "scope": "ci-tools",
            "advisories": ["CVE-2022-29217"],
            "expiry": "2099-12-31",
            "review": "test",
            "trigger": "test",
        }
    ]

    # Different version is never excepted
    diff_ver_output = json.dumps([
        {"name": "pyjwt", "version": "2.14.0", "vulns": [{"id": "CVE-2022-29217", "aliases": []}]}
    ])
    res = parse_audit_output(diff_ver_output, returncode=1, inventory_name="ci-tools", exceptions=exceptions)
    assert res["status"] == "policy-finding"
    assert res["finding_count"] == 1

    # Different package is never excepted
    diff_pkg_output = json.dumps([
        {"name": "requests", "version": "2.13.0", "vulns": [{"id": "CVE-2022-29217", "aliases": []}]}
    ])
    res = parse_audit_output(diff_pkg_output, returncode=1, inventory_name="ci-tools", exceptions=exceptions)
    assert res["status"] == "policy-finding"
    assert res["finding_count"] == 1


def test_audit_all_stale_active_exception_fails_closed(tmp_path: Path) -> None:
    from tools.ci.dependency_inventory import audit_all

    # Mock runner returning 0 vulnerabilities for all inventories
    def clean_runner(command, **_kwargs):
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=json.dumps([{"name": "tomli", "version": "2.0.1", "vulns": []}]),
            stderr="",
        )

    # With clean results, the active pyjwt exception matches 0 vulnerabilities -> STALE!
    exceptions_file = tmp_path / "exceptions.json"
    exceptions_file.write_text(
        json.dumps({
            "schema": "apg-dependency-exceptions-v1",
            "exceptions": [
                {
                    "package": "pyjwt",
                    "version": "2.13.0",
                    "scope": "ci-tools",
                    "advisories": ["CVE-2026-101917"],
                    "expiry": "2099-12-31",
                    "review": "test review",
                    "trigger": "test trigger",
                }
            ],
        }),
        encoding="utf-8",
    )

    report = audit_all("pip-audit", scratch_dir=tmp_path / "scratch", runner=clean_runner, exceptions_file=exceptions_file)
    assert report["status"] == "policy-finding"
    assert report["classification"] == "policy-finding"
    assert report["policy_finding_count"] >= 1
    assert "stale dependency exception" in report.get("stale_exceptions_detail", "")


def test_maintained_dependency_exceptions_file_schema_and_empty_loader() -> None:
    from tools.ci.dependency_inventory import (
        EXCEPTION_SCHEMA,
        ROOT,
        load_dependency_exceptions,
    )

    exceptions_path = ROOT / "tools/ci/dependency_exceptions.json"
    assert exceptions_path.is_file(), "tools/ci/dependency_exceptions.json must exist"

    raw_doc = json.loads(exceptions_path.read_text(encoding="utf-8"))
    assert set(raw_doc.keys()) == {"schema", "exceptions"}
    assert raw_doc["schema"] == EXCEPTION_SCHEMA
    assert raw_doc["exceptions"] == []

    # Loader returns empty list when loading maintained file; pass fixed today where exposed
    fixed_today = date(2026, 10, 1)
    loaded = load_dependency_exceptions(exceptions_path, today=fixed_today)
    assert loaded == []


def test_audit_all_clean_with_empty_exceptions_passes_without_stale_detail(tmp_path: Path) -> None:
    from tools.ci.dependency_inventory import ROOT, audit_all

    def clean_runner(command, **_kwargs):
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=json.dumps([{"name": "tomli", "version": "2.0.1", "vulns": []}]),
            stderr="",
        )

    # Auditing with maintained empty exceptions file passes cleanly without stale detail
    report = audit_all(
        "pip-audit",
        scratch_dir=tmp_path / "scratch",
        runner=clean_runner,
        exceptions_file=ROOT / "tools/ci/dependency_exceptions.json",
    )
    assert report["status"] == "passed"
    assert report["classification"] == "passed"
    assert report["finding_count"] == 0
    assert report["tool_failure_count"] == 0
    assert report["policy_finding_count"] == 0
    assert "stale_exceptions_detail" not in report
    assert "unmatched_advisory_aliases" not in report
