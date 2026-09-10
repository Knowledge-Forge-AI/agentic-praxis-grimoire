"""Unit tests for APGR file_length_policy manager-authorized gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ci.file_length_policy import (
    DEFAULT_FAILURE_LIMIT,
    DEFAULT_WARNING_LIMIT,
    FileLengthOperationalError,
    FileLengthResult,
    Finding,
    classify_line_count,
    count_physical_lines,
    load_policy,
    render_json,
    render_text,
)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"", 0),
        (b"x", 1),
        (b"x\n", 1),
        (b"x\r\n", 1),
        (b"x\r\ny\r\n", 2),
        (b"x\ny", 2),
        (b"\n", 1),
        (b"\n\n\n", 3),
        (b"a\n" * 1000, 1000),
        (b"a\n" * 1000 + b"b", 1001),
    ],
)
def test_count_physical_lines_boundaries(tmp_path: Path, content: bytes, expected: int) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(content)
    assert count_physical_lines(target) == expected


def test_count_physical_lines_large_multichunk(tmp_path: Path) -> None:
    target = tmp_path / "large.py"
    chunk = b"print('hello world')\n"
    # Write > 128 KB
    reps = 10000
    target.write_bytes(chunk * reps)
    assert count_physical_lines(target) == reps


@pytest.mark.parametrize(
    ("line_count", "allowance_count", "expected_severity"),
    [
        (0, None, None),
        (1, None, None),
        (400, None, None),
        (401, None, "warning"),
        (999, None, "warning"),
        (1000, None, "warning"),
        (1001, None, "failure"),
        (1001, 1001, "warning"),
        (1002, 1001, "failure"),
        (2500, 3000, "warning"),
        (3001, 3000, "failure"),
    ],
)
def test_classify_exact_boundaries(
    line_count: int,
    allowance_count: int | None,
    expected_severity: str | None,
) -> None:
    severity, _ = classify_line_count(
        line_count,
        allowance_count=allowance_count,
        warning_limit=DEFAULT_WARNING_LIMIT,
        failure_limit=DEFAULT_FAILURE_LIMIT,
    )
    assert severity == expected_severity


def test_load_policy_success(tmp_path: Path) -> None:
    policy_file = tmp_path / "policy.json"
    policy_doc = {
        "schema": "apg-file-length-policy-v1",
        "warning_limit": 400,
        "failure_limit": 1000,
        "allowances": [
            {
                "path": "libexec/sample.py",
                "role": "maintained-source",
                "owner": "sample-owner",
                "sha256": "a" * 64,
                "count": 1200,
                "rationale": "Sample oversized component",
                "maintenance": "Refactor planned",
            }
        ],
    }
    policy_file.write_text(json.dumps(policy_doc), encoding="utf-8")
    loaded = load_policy(policy_file)
    assert loaded.schema == "apg-file-length-policy-v1"
    assert loaded.warning_limit == 400
    assert loaded.failure_limit == 1000
    assert "libexec/sample.py" in loaded.allowances
    allowance = loaded.allowances["libexec/sample.py"]
    assert allowance.count == 1200
    assert allowance.owner == "sample-owner"


def test_load_policy_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileLengthOperationalError, match="does not exist"):
        load_policy(tmp_path / "absent.json")


def test_load_policy_rejects_malformed_json(tmp_path: Path) -> None:
    policy_file = tmp_path / "corrupt.json"
    policy_file.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(FileLengthOperationalError, match="malformed policy JSON"):
        load_policy(policy_file)


def test_load_policy_rejects_invalid_schema(tmp_path: Path) -> None:
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(
        json.dumps({"schema": "unknown-schema-v1", "allowances": []}),
        encoding="utf-8",
    )
    with pytest.raises(FileLengthOperationalError, match="unsupported policy schema"):
        load_policy(policy_file)


def test_load_policy_rejects_invalid_limits(tmp_path: Path) -> None:
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(
        json.dumps({
            "schema": "apg-file-length-policy-v1",
            "warning_limit": 1000,
            "failure_limit": 400,
            "allowances": [],
        }),
        encoding="utf-8",
    )
    with pytest.raises(FileLengthOperationalError, match="requires warning_limit=400"):
        load_policy(policy_file)


@pytest.mark.parametrize("mutation", ["missing", "unknown", "duplicate", "increase", "boolean"])
def test_closed_policy_cannot_silently_relax_gate(tmp_path, mutation):
    document = {"schema": "apg-file-length-policy-v1", "warning_limit": 400,
                "failure_limit": 1000, "allowances": []}
    if mutation == "missing":
        del document["failure_limit"]
    elif mutation == "unknown":
        document["allowed_failures"] = 20
    elif mutation == "increase":
        document["failure_limit"] = 2000
    elif mutation == "boolean":
        document["warning_limit"] = True
    text = json.dumps(document)
    if mutation == "duplicate":
        text = text.replace('"failure_limit": 1000', '"failure_limit": 2000, "failure_limit": 1000')
    path = tmp_path / "policy.json"
    path.write_text(text)
    with pytest.raises(FileLengthOperationalError):
        load_policy(path)


def test_load_policy_rejects_duplicate_allowance_paths(tmp_path: Path) -> None:
    policy_file = tmp_path / "policy.json"
    entry = {
        "path": "libexec/dup.py",
        "role": "maintained-source",
        "owner": "test",
        "sha256": "b" * 64,
        "count": 1500,
        "rationale": "test",
        "maintenance": "test",
    }
    policy_file.write_text(
        json.dumps({
            "schema": "apg-file-length-policy-v1",
            "warning_limit": 400,
            "failure_limit": 1000,
            "allowances": [entry, entry],
        }),
        encoding="utf-8",
    )
    with pytest.raises(FileLengthOperationalError, match="duplicate allowance path detected"):
        load_policy(policy_file)


def test_load_policy_rejects_path_escape(tmp_path: Path) -> None:
    policy_file = tmp_path / "policy.json"
    entry = {
        "path": "../escaping.py",
        "role": "maintained-source",
        "owner": "test",
        "sha256": "c" * 64,
        "count": 1500,
        "rationale": "test",
        "maintenance": "test",
    }
    policy_file.write_text(
        json.dumps({
            "schema": "apg-file-length-policy-v1",
            "warning_limit": 400,
            "failure_limit": 1000,
            "allowances": [entry],
        }),
        encoding="utf-8",
    )
    with pytest.raises(FileLengthOperationalError, match="escapes repository root"):
        load_policy(policy_file)


def test_load_policy_rejects_allowance_below_failure_limit(tmp_path: Path) -> None:
    policy_file = tmp_path / "policy.json"
    entry = {
        "path": "libexec/small.py",
        "role": "maintained-source",
        "owner": "test",
        "sha256": "d" * 64,
        "count": 900,
        "rationale": "test",
        "maintenance": "test",
    }
    policy_file.write_text(
        json.dumps({
            "schema": "apg-file-length-policy-v1",
            "warning_limit": 400,
            "failure_limit": 1000,
            "allowances": [entry],
        }),
        encoding="utf-8",
    )
    with pytest.raises(FileLengthOperationalError, match="must be an integer > failure_limit"):
        load_policy(policy_file)


def test_load_policy_rejects_invalid_sha256(tmp_path: Path) -> None:
    policy_file = tmp_path / "policy.json"
    entry = {
        "path": "libexec/bad_sha.py",
        "role": "maintained-source",
        "owner": "test",
        "sha256": "not-a-valid-sha256",
        "count": 1500,
        "rationale": "test",
        "maintenance": "test",
    }
    policy_file.write_text(
        json.dumps({
            "schema": "apg-file-length-policy-v1",
            "warning_limit": 400,
            "failure_limit": 1000,
            "allowances": [entry],
        }),
        encoding="utf-8",
    )
    with pytest.raises(FileLengthOperationalError, match="must be a 64-char hex string"):
        load_policy(policy_file)


def test_load_shipped_policy() -> None:
    repo_root = Path(__file__).resolve().parents[7]
    shipped_policy = repo_root / "tools/ci/file_length_policy.json"
    assert shipped_policy.is_file()
    policy = load_policy(shipped_policy)
    assert policy.schema == "apg-file-length-policy-v1"
    assert len(policy.allowances) == 18
    for allowance in policy.allowances.values():
        assert allowance.count > 1000
        assert len(allowance.sha256) == 64


def test_render_json_is_deterministic_and_newline_terminated() -> None:
    result = FileLengthResult(
        status="passed_with_warnings",
        scanned_file_count=2,
        warning_count=1,
        failure_count=0,
        findings=(
            Finding("tools/warn.py", 450, "warning", message="file exceeds warning limit: 450 > 400"),
        ),
        warning_limit=400,
        failure_limit=1000,
        allowances_count=0,
    )
    rendered1 = render_json(result)
    rendered2 = render_json(result)
    assert rendered1 == rendered2
    assert rendered1.endswith("\n") and not rendered1.endswith("\n\n")
    parsed = json.loads(rendered1)
    assert parsed["status"] == "passed_with_warnings"
    assert parsed["warning_count"] == 1
    assert parsed["failure_count"] == 0
    assert len(parsed["findings"]) == 1


def test_render_text_orders_failures_then_warnings() -> None:
    result = FileLengthResult(
        status="failed",
        scanned_file_count=3,
        warning_count=1,
        failure_count=1,
        findings=(
            Finding("tools/fail.py", 1200, "failure", message="exceeds limit"),
            Finding("tools/warn.py", 500, "warning", message="exceeds warning"),
        ),
        warning_limit=400,
        failure_limit=1000,
        allowances_count=0,
    )
    rendered = render_text(result)
    assert rendered.startswith("file-length: failed\n")
    lines = rendered.splitlines()
    assert "FAILURE  1200  tools/fail.py" in lines[6]
    assert "WARNING   500  tools/warn.py" in lines[7]
