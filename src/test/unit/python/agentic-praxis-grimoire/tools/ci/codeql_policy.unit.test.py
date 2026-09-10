"""Unit tests for CodeQL scanning policy and hosted success boundaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ci.codeql_policy import validate_sarif

ROOT = Path(__file__).resolve().parents[7]


def test_codeql_policy_languages_and_modes() -> None:
    policy_path = ROOT / "release/ci/codeql_policy.json"
    assert policy_path.is_file()

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    assert policy.get("schema") == "apg-codeql-policy-v1"

    languages = policy.get("languages", {})
    assert "go" in languages
    assert "python" in languages
    assert "javascript-typescript" in languages
    assert "actions" in languages

    # Go uses manual build mode
    assert languages["go"]["build_mode"] == "manual"
    assert "cmd/apgr" in languages["go"]["build_command"]

    # Python, JS/TS, Actions require none
    assert languages["python"]["build_mode"] == "none"
    assert languages["javascript-typescript"]["build_mode"] == "none"
    assert languages["actions"]["build_mode"] == "none"

    # All declare categories
    for cfg in languages.values():
        assert cfg["category"].startswith("/language:")


def test_codeql_policy_alert_merge_protection_and_no_hosted_claim() -> None:
    policy_path = ROOT / "release/ci/codeql_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    # Alert merge protection covers error and high
    protection = policy["alert_merge_protection"]
    assert "error" in protection["enforced_levels"]
    assert "high" in protection["enforced_levels"]
    assert protection["sarif_upload"] is True

    # Hosted success claim MUST be explicitly false
    claim = policy["hosted_success_claim"]
    assert claim["claimed"] is False
    assert "Hosted" in claim["rationale"] or "infrastructure" in claim["rationale"]


def test_codeql_sarif_requires_successful_invocation_and_blocks_high() -> None:
    clean = {
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "CodeQL"}},
            "invocations": [{"executionSuccessful": True}],
            "results": [],
        }],
    }
    result = validate_sarif(clean, language="python")
    assert result["status"] == "passed"
    assert result["matrix_member"] == "codeql-python"

    finding = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "rules": [{
                        "id": "py/test",
                        "properties": {"security-severity": "8.0"},
                    }],
                },
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "ruleId": "py/test",
                "level": "warning",
            }],
        }],
    }
    result = validate_sarif(finding, language="python")
    assert result["status"] == "failed"
    assert result["blocking_results"][0]["ruleId"] == "py/test"


def test_codeql_rule_index_resolves_driver_rule_severity() -> None:
    finding = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "rules": [
                        {"id": "py/low", "properties": {"security-severity": "2.0"}},
                        {"id": "py/high", "properties": {"security-severity": "7.0"}},
                    ],
                },
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{"ruleIndex": 1, "level": "warning"}],
        }],
    }
    result = validate_sarif(finding, language="python")
    assert result["status"] == "failed"
    assert result["blocking_results"] == [
        {"ruleId": "py/high", "level": "warning", "security_severity": 7.0}
    ]


def test_codeql_error_level_blocks_without_security_severity() -> None:
    document = {
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "CodeQL", "rules": [{"id": "py/error"}]}},
            "invocations": [{"executionSuccessful": True}],
            "results": [{"ruleId": "py/error", "level": "error"}],
        }],
    }
    result = validate_sarif(document, language="python")
    assert result["status"] == "failed"
    assert result["blocking_results"] == [
        {"ruleId": "py/error", "level": "error", "security_severity": None}
    ]


@pytest.mark.parametrize(
    ("result", "message"),
    [
        ({"ruleIndex": 4}, "outside"),
        ({"ruleId": "py/missing"}, "not present"),
        ({"ruleIndex": True}, "non-negative integer"),
    ],
)
def test_codeql_rejects_malformed_rule_references(result: dict[str, object], message: str) -> None:
    document = {
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "CodeQL", "rules": [{"id": "py/known"}]}},
            "invocations": [{"executionSuccessful": True}],
            "results": [result],
        }],
    }
    validated = validate_sarif(document, language="python")
    assert validated["status"] == "failed"
    assert any(message in error for error in validated["errors"])


def test_codeql_rejects_malformed_severity_and_invocation_error_notification() -> None:
    document = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "rules": [{"id": "py/test", "properties": {"security-severity": "NaN"}}],
                },
            },
            "invocations": [{
                "executionSuccessful": True,
                "toolExecutionNotifications": [{"level": "error"}],
            }],
            "results": [{"ruleId": "py/test", "level": "warning"}],
        }],
    }
    result = validate_sarif(document, language="python")
    assert result["status"] == "failed"
    assert any("outside the 0.0-10.0 range" in error for error in result["errors"])
    assert any("reports a CodeQL error" in error for error in result["errors"])
