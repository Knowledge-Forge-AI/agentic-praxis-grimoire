"""Unit contracts for separate APGR dependency inventory auditing."""

from __future__ import annotations

from datetime import date
import json
import subprocess
from pathlib import Path

import pytest

import tools.ci.dependency_inventory as dependency_inventory
from tools.ci.dependency_inventory import (
    audit_inventory,
    build_inventories,
    parse_audit_output,
)

# The reviewed CI-tools exceptions committed in
# tools/ci/dependency_exceptions.json.  Production expiry keeps the real clock;
# these tests observe the record on a fixed review date instead.
MCP_EXCEPTION = {
    "package": "mcp",
    "version": "1.29.0",
    "scope": "ci-tools",
    "advisories": ["CVE-2026-59951", "GHSA-84m7-p3x7-pcfv"],
    "expiry": "2026-10-28",
    "review": "release/v0.13.1-notes.md#ci-tool-dependency-review",
    "trigger": (
        "Remove at the first compatible Semgrep release accepting a patched MCP version, "
        "any MCP HTTP-server use, or expiry on 2026-10-28, whichever occurs first; "
        "do not renew automatically."
    ),
}
OTEL_EXCEPTION = {
    "package": "opentelemetry-api",
    "version": "1.37.0",
    "scope": "ci-tools",
    "advisories": ["CVE-2026-114603", "GHSA-xcq7-p3pf-p88h"],
    "expiry": "2026-10-28",
    "review": "release/v0.13.1-notes.md#ci-tool-dependency-review",
    "trigger": (
        "Remove at the first compatible Semgrep release accepting a patched OpenTelemetry family; "
        "any enabled Semgrep tracing, trace flags or OTEL/Semgrep trace environment configuration; "
        "any ingestion of untrusted tracestate through HTTP, environment or another carrier; "
        "or expiry on 2026-10-28, whichever occurs first. Do not renew automatically."
    ),
}
OBSERVED = date(2026, 10, 21)

# pip-audit's raw JSON envelope for the transitive Semgrep MCP finding.  No fix
# version is asserted here.
MCP_FINDING = {
    "name": "mcp",
    "version": "1.29.0",
    "vulns": [{"id": "GHSA-84m7-p3x7-pcfv", "aliases": ["CVE-2026-59951"]}],
}
OTEL_FINDING = {
    "name": "opentelemetry-api",
    "version": "1.37.0",
    "vulns": [{"id": "GHSA-xcq7-p3pf-p88h", "aliases": ["CVE-2026-114603"]}],
}
UNRELATED_FINDING = {
    "name": "requests",
    "version": "2.13.0",
    "vulns": [{"id": "CVE-9999-0001", "aliases": []}],
}


def _fixed_clock(monkeypatch: pytest.MonkeyPatch, day: date) -> None:
    """Pin the auditor module's calendar date without changing production code."""

    class _FixedDate(date):
        @classmethod
        def today(cls) -> date:
            return cls(day.year, day.month, day.day)

    monkeypatch.setattr(dependency_inventory, "date", _FixedDate)


def _audit_document(*records: dict[str, object]) -> str:
    return json.dumps({"dependencies": list(records)})


def _empty_policy(tmp_path: Path) -> Path:
    path = tmp_path / "empty-exceptions.json"
    path.write_text(
        json.dumps({"schema": "apg-dependency-exceptions-v1", "exceptions": []}),
        encoding="utf-8",
    )
    return path


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


def test_audit_inventory_records_tool_failures_and_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The runner path loads the maintained policy, so observe it on the review date.
    _fixed_clock(monkeypatch, OBSERVED)
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


def test_maintained_dependency_exceptions_file_holds_exact_reviewed_records() -> None:
    from tools.ci.dependency_inventory import (
        EXCEPTION_SCHEMA,
        ROOT,
        load_dependency_exceptions,
        validate_dependency_exceptions,
    )

    exceptions_path = ROOT / "tools/ci/dependency_exceptions.json"
    assert exceptions_path.is_file(), "tools/ci/dependency_exceptions.json must exist"

    raw_doc = json.loads(exceptions_path.read_text(encoding="utf-8"))
    assert raw_doc == {"schema": EXCEPTION_SCHEMA, "exceptions": [MCP_EXCEPTION, OTEL_EXCEPTION]}

    loaded = load_dependency_exceptions(exceptions_path, today=OBSERVED)
    assert loaded == [MCP_EXCEPTION, OTEL_EXCEPTION]

    # The review reference names a real section in the release notes.
    review_path, anchor = MCP_EXCEPTION["review"].split("#")
    assert anchor == "ci-tool-dependency-review"
    notes = (ROOT / review_path).read_text(encoding="utf-8").splitlines()
    assert "## CI tool dependency review" in notes

    # Expiry is an inclusive calendar date and is never renewed automatically.
    validate_dependency_exceptions(loaded, today=date(2026, 10, 28))
    with pytest.raises(ValueError, match="expired"):
        validate_dependency_exceptions(loaded, today=date(2026, 10, 29))
    with pytest.raises(ValueError, match="expired"):
        load_dependency_exceptions(exceptions_path, today=date(2026, 10, 29))


def test_empty_policy_loader_returns_no_exceptions(tmp_path: Path) -> None:
    from tools.ci.dependency_inventory import load_dependency_exceptions

    assert load_dependency_exceptions(_empty_policy(tmp_path), today=OBSERVED) == []


def test_audit_all_clean_with_empty_exceptions_passes_without_stale_detail(tmp_path: Path) -> None:
    from tools.ci.dependency_inventory import audit_all

    def clean_runner(command, **_kwargs):
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=json.dumps([{"name": "tomli", "version": "2.0.1", "vulns": []}]),
            stderr="",
        )

    # An explicit temporary empty policy audits cleanly without stale detail.
    report = audit_all(
        "pip-audit",
        scratch_dir=tmp_path / "scratch",
        runner=clean_runner,
        exceptions_file=_empty_policy(tmp_path),
    )
    assert report["status"] == "passed"
    assert report["classification"] == "passed"
    assert report["finding_count"] == 0
    assert report["tool_failure_count"] == 0
    assert report["policy_finding_count"] == 0
    assert "stale_exceptions_detail" not in report
    assert "unmatched_advisory_aliases" not in report


def test_mcp_exception_excepts_raw_shaped_ci_tools_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    _fixed_clock(monkeypatch, OBSERVED)
    result = parse_audit_output(
        _audit_document(MCP_FINDING),
        returncode=1,
        inventory_name="ci-tools",
        exceptions=[MCP_EXCEPTION],
    )
    assert result["status"] == "passed"
    assert result["classification"] == "passed"
    assert result["finding_count"] == 0
    assert result["excepted_count"] == 1
    assert "excepted=1" in result["detail"]
    # The raw finding stays recorded with its exception metadata.
    assert result["excepted_vulnerabilities"] == [
        {
            "package": "mcp",
            "version": "1.29.0",
            "advisory": "GHSA-84m7-p3x7-pcfv",
            "expiry": "2026-10-28",
            "review": "release/v0.13.1-notes.md#ci-tool-dependency-review",
        }
    ]
    assert result["matched_exception_indices"] == [0]
    assert result["matched_advisories"] == ["CVE-2026-59951", "GHSA-84m7-p3x7-pcfv"]
    assert result["dependencies"] == [MCP_FINDING]


def test_mcp_exception_does_not_hide_unrelated_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    _fixed_clock(monkeypatch, OBSERVED)
    result = parse_audit_output(
        _audit_document(MCP_FINDING, UNRELATED_FINDING),
        returncode=1,
        inventory_name="ci-tools",
        exceptions=[MCP_EXCEPTION],
    )
    assert result["status"] == "policy-finding"
    assert result["classification"] == "policy-finding"
    assert result["finding_count"] == 1
    assert result["excepted_count"] == 1
    assert "excepted=1" in result["detail"]


@pytest.mark.parametrize("inventory_name", ["runtime", "test"])
def test_mcp_exception_refuses_runtime_and_test_inventories(
    monkeypatch: pytest.MonkeyPatch, inventory_name: str
) -> None:
    _fixed_clock(monkeypatch, OBSERVED)
    result = parse_audit_output(
        _audit_document(MCP_FINDING),
        returncode=1,
        inventory_name=inventory_name,
        exceptions=[MCP_EXCEPTION],
    )
    assert result["status"] == "policy-finding"
    assert result["finding_count"] == 1
    assert "excepted_count" not in result
    assert result["matched_exception_indices"] == []


@pytest.mark.parametrize(
    "record",
    [
        dict(MCP_FINDING, version="1.29.1"),
        dict(MCP_FINDING, name="mcp-server"),
        dict(MCP_FINDING, vulns=[{"id": "GHSA-0000-0000-0000", "aliases": ["CVE-2026-00001"]}]),
    ],
    ids=["wrong-version", "wrong-package", "unlisted-advisory"],
)
def test_mcp_exception_refuses_inexact_findings(
    monkeypatch: pytest.MonkeyPatch, record: dict[str, object]
) -> None:
    _fixed_clock(monkeypatch, OBSERVED)
    result = parse_audit_output(
        _audit_document(record),
        returncode=1,
        inventory_name="ci-tools",
        exceptions=[MCP_EXCEPTION],
    )
    assert result["status"] == "policy-finding"
    assert result["finding_count"] == 1
    assert "excepted_count" not in result


def test_mcp_exception_stops_applying_after_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    _fixed_clock(monkeypatch, date(2026, 10, 28))
    last_day = parse_audit_output(
        _audit_document(MCP_FINDING),
        returncode=1,
        inventory_name="ci-tools",
        exceptions=[MCP_EXCEPTION],
    )
    assert last_day["status"] == "passed"

    _fixed_clock(monkeypatch, date(2026, 10, 29))
    expired = parse_audit_output(
        _audit_document(MCP_FINDING),
        returncode=1,
        inventory_name="ci-tools",
        exceptions=[MCP_EXCEPTION],
    )
    assert expired["status"] == "policy-finding"
    assert expired["finding_count"] == 1
    assert "excepted_count" not in expired


def test_mcp_exception_keeps_operational_failure_as_tool_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _fixed_clock(monkeypatch, OBSERVED)
    result = parse_audit_output(
        _audit_document(MCP_FINDING),
        returncode=2,
        inventory_name="ci-tools",
        exceptions=[MCP_EXCEPTION],
    )
    assert result["status"] == "tool-failure"
    assert result["classification"] == "tool-failure"


def _inventory_runner(ci_tools_records: list[dict[str, object]]):
    def runner(command, **_kwargs):
        requirement = Path(command[command.index("--requirement") + 1]).name
        records = ci_tools_records if requirement == "ci_tools.txt" else []
        stdout = _audit_document(*records, {"name": "tomli", "version": "2.0.1", "vulns": []})
        return subprocess.CompletedProcess(
            args=command,
            returncode=1 if records else 0,
            stdout=stdout,
            stderr="",
        )

    return runner


def test_audit_all_applies_maintained_exceptions_to_ci_tools_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.ci.dependency_inventory import ROOT, audit_all

    _fixed_clock(monkeypatch, OBSERVED)
    report = audit_all(
        "pip-audit",
        scratch_dir=tmp_path / "scratch",
        runner=_inventory_runner([MCP_FINDING, OTEL_FINDING]),
        exceptions_file=ROOT / "tools/ci/dependency_exceptions.json",
    )
    assert report["status"] == "passed"
    assert report["classification"] == "passed"
    assert report["finding_count"] == 0
    assert report["tool_failure_count"] == 0
    assert report["policy_finding_count"] == 0
    assert "stale_exceptions_detail" not in report
    assert "unmatched_advisory_aliases" not in report

    by_name = {item["name"]: item for item in report["inventories"]}
    assert by_name["ci-tools"]["excepted_count"] == 2
    assert {item["advisory"] for item in by_name["ci-tools"]["excepted_vulnerabilities"]} == {
        "GHSA-84m7-p3x7-pcfv", "GHSA-xcq7-p3pf-p88h",
    }
    assert "excepted_count" not in by_name["runtime"]
    assert "excepted_count" not in by_name["test"]


def test_audit_all_reports_maintained_exceptions_as_stale_when_unmatched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tools.ci.dependency_inventory import ROOT, audit_all

    _fixed_clock(monkeypatch, OBSERVED)
    report = audit_all(
        "pip-audit",
        scratch_dir=tmp_path / "scratch",
        runner=_inventory_runner([]),
        exceptions_file=ROOT / "tools/ci/dependency_exceptions.json",
    )
    assert report["status"] == "policy-finding"
    assert report["classification"] == "policy-finding"
    assert report["policy_finding_count"] == 2
    assert "mcp==1.29.0 (scope: ci-tools)" in report["stale_exceptions_detail"]
    assert "opentelemetry-api==1.37.0 (scope: ci-tools)" in report["stale_exceptions_detail"]


@pytest.mark.parametrize(
    "scope,record,day,excepted",
    [
        ("ci-tools", OTEL_FINDING, date(2026, 10, 28), True),
        ("ci-tools", OTEL_FINDING, date(2026, 10, 29), False),
        ("runtime", OTEL_FINDING, OBSERVED, False),
        ("test", OTEL_FINDING, OBSERVED, False),
        ("ci-tools", dict(OTEL_FINDING, version="1.37.1"), OBSERVED, False),
        ("ci-tools", dict(OTEL_FINDING, name="opentelemetry-sdk"), OBSERVED, False),
        ("ci-tools", dict(OTEL_FINDING, vulns=[{"id": "CVE-9999-0002", "aliases": []}]), OBSERVED, False),
    ],
    ids=["inclusive-expiry", "expired", "runtime", "test", "wrong-version", "wrong-package", "unlisted-advisory"],
)
def test_otel_exception_matches_only_reviewed_scope_version_advisory_and_date(
    monkeypatch: pytest.MonkeyPatch,
    scope: str,
    record: dict[str, object],
    day: date,
    excepted: bool,
) -> None:
    _fixed_clock(monkeypatch, day)
    result = parse_audit_output(
        _audit_document(record, UNRELATED_FINDING),
        returncode=1,
        inventory_name=scope,
        exceptions=[OTEL_EXCEPTION],
    )
    # An unrelated finding stays blocking even when the exact OTEL record matches.
    assert result["status"] == "policy-finding"
    assert result["finding_count"] == (1 if excepted else 2)
    assert result.get("excepted_count", 0) == int(excepted)
    assert result["dependencies"] == [record, UNRELATED_FINDING]
    if excepted:
        assert result["excepted_vulnerabilities"] == [{
            "package": "opentelemetry-api",
            "version": "1.37.0",
            "advisory": "GHSA-xcq7-p3pf-p88h",
            "expiry": "2026-10-28",
            "review": "release/v0.13.1-notes.md#ci-tool-dependency-review",
        }]
