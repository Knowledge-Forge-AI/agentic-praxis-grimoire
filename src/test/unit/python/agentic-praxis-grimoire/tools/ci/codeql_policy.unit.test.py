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


def test_codeql_resolves_rules_from_tool_extensions() -> None:
    doc = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {"name": "CodeQL", "rules": []},
                "extensions": [{
                    "name": "codeql/python-queries",
                    "rules": [{
                        "id": "py/extension-rule",
                        "properties": {"security-severity": "8.5"},
                        "defaultConfiguration": {"level": "warning"},
                    }],
                }],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "py/extension-rule",
                    "index": 0,
                    "toolComponent": {"index": 0},
                },
                "ruleId": "py/extension-rule",
            }],
        }],
    }
    result = validate_sarif(doc, language="python")
    assert result["status"] == "failed"
    assert len(result["blocking_results"]) == 1
    assert result["blocking_results"][0]["ruleId"] == "py/extension-rule"
    assert result["blocking_results"][0]["security_severity"] == 8.5
    assert result["blocking_results"][0]["level"] == "warning"


def test_codeql_default_configuration_level_fallback() -> None:
    doc = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {"name": "CodeQL", "rules": []},
                "extensions": [{
                    "name": "codeql/javascript-queries",
                    "rules": [{
                        "id": "js/error-rule",
                        "defaultConfiguration": {"level": "error"},
                    }],
                }],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "js/error-rule",
                    "index": 0,
                    "toolComponent": {"index": 0, "name": "codeql/javascript-queries"},
                },
            }],
        }],
    }
    result = validate_sarif(doc, language="javascript-typescript")
    assert result["status"] == "failed"
    assert len(result["blocking_results"]) == 1
    assert result["blocking_results"][0]["level"] == "error"
    assert result["blocking_results"][0]["security_severity"] is None


def test_codeql_clean_run_with_extensions_passes() -> None:
    doc = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {"name": "CodeQL", "rules": []},
                "extensions": [{
                    "name": "codeql/go-queries",
                    "rules": [{"id": "go/sample-rule"}],
                }],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [],
        }],
    }
    result = validate_sarif(doc, language="go")
    assert result["status"] == "passed"
    assert result["result_count"] == 0
    assert result["blocking_results"] == []
    assert result["errors"] == []


@pytest.mark.parametrize(
    ("rule_ref", "expected_err"),
    [
        (
            {"index": 0, "toolComponent": {"index": 5}},
            "unknown tool component index",
        ),
        (
            {"index": 0, "toolComponent": {"name": "non-existent"}},
            "toolComponent name disagrees with driver",
        ),
        (
            {"id": "py/mismatched", "index": 0, "toolComponent": {"index": 0}},
            "identify different CodeQL rules",
        ),
        (
            {"index": 10, "toolComponent": {"index": 0}},
            "outside the CodeQL rule array",
        ),
        (
            {"index": 0, "toolComponent": {"index": -1}},
            "toolComponent.index is not a valid non-negative component index",
        ),
        (
            {"index": 0, "toolComponent": {"index": -2}},
            "toolComponent.index is not a valid non-negative component index",
        ),
        (
            {"index": 0, "toolComponent": {"index": True}},
            "toolComponent.index is not a valid non-negative component index",
        ),
        (
            {"index": 0, "toolComponent": {"index": "invalid"}},
            "toolComponent.index is not a valid non-negative component index",
        ),
        (
            {"index": 0, "toolComponent": {"name": "codeql/python-queries", "guid": "wrong-guid"}},
            "references an unknown tool component guid: wrong-guid",
        ),
        (
            {"index": 0, "toolComponent": {"guid": "correct-guid", "name": "mismatched-name"}},
            "toolComponent name disagrees with guid",
        ),
        (
            {"index": 0, "toolComponent": {"guid": ""}},
            "toolComponent guid is not a non-empty string",
        ),
    ],
)
def test_codeql_rejects_extension_negative_fixtures(rule_ref: dict, expected_err: str) -> None:
    doc = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {"name": "CodeQL", "rules": []},
                "extensions": [{
                    "name": "codeql/python-queries",
                    "guid": "correct-guid",
                    "rules": [{"id": "py/valid"}, {"id": "py/mismatched"}],
                }],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{"rule": rule_ref}],
        }],
    }
    result = validate_sarif(doc, language="python")
    assert result["status"] == "failed"
    assert any(expected_err in e for e in result["errors"])


def test_codeql_rejects_driver_index_minus_one() -> None:
    doc = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "rules": [{
                        "id": "py/driver-rule",
                        "defaultConfiguration": {"level": "note"},
                    }],
                },
                "extensions": [{
                    "name": "codeql/python-queries",
                    "rules": [],
                }],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "py/driver-rule",
                    "index": 0,
                    "toolComponent": {"index": -1, "name": "CodeQL"},
                },
            }],
        }],
    }
    result = validate_sarif(doc, language="python")
    assert result["status"] == "failed"
    assert any("toolComponent.index is not a valid non-negative component index" in e for e in result["errors"])


def test_codeql_resolves_empty_tool_component_as_driver() -> None:
    doc = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "rules": [{
                        "id": "py/driver-rule",
                        "defaultConfiguration": {"level": "note"},
                    }],
                },
                "extensions": [],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "py/driver-rule",
                    "index": 0,
                    "toolComponent": {},
                },
            }],
        }],
    }
    result = validate_sarif(doc, language="python")
    assert result["status"] == "passed"
    assert result["result_count"] == 1
    assert result["blocking_results"] == []
    assert result["errors"] == []


def test_codeql_resolves_driver_name_only() -> None:
    doc = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "rules": [{
                        "id": "py/driver-rule",
                        "defaultConfiguration": {"level": "note"},
                    }],
                },
                "extensions": [],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "py/driver-rule",
                    "index": 0,
                    "toolComponent": {"name": "CodeQL"},
                },
            }],
        }],
    }
    result = validate_sarif(doc, language="python")
    assert result["status"] == "passed"
    assert result["result_count"] == 1
    assert result["blocking_results"] == []
    assert result["errors"] == []


def test_codeql_rejects_extension_name_only_disagreement_with_driver() -> None:
    doc = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "rules": [{
                        "id": "py/driver-rule",
                        "defaultConfiguration": {"level": "note"},
                    }],
                },
                "extensions": [{
                    "name": "codeql/python-queries",
                    "rules": [{"id": "py/ext-rule"}],
                }],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "py/ext-rule",
                    "index": 0,
                    "toolComponent": {"name": "codeql/python-queries"},
                },
            }],
        }],
    }
    result = validate_sarif(doc, language="python")
    assert result["status"] == "failed"
    assert any("toolComponent name disagrees with driver: codeql/python-queries" in e for e in result["errors"])


def test_codeql_resolves_guid_across_driver_and_extensions() -> None:
    # 1. GUID matching extension
    doc_ext = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {"name": "CodeQL", "rules": []},
                "extensions": [{
                    "name": "codeql/python-queries",
                    "guid": "ext-guid-1234",
                    "rules": [{
                        "id": "py/ext-rule",
                        "defaultConfiguration": {"level": "note"},
                    }],
                }],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "py/ext-rule",
                    "index": 0,
                    "toolComponent": {"guid": "ext-guid-1234", "name": "codeql/python-queries"},
                },
            }],
        }],
    }
    res_ext = validate_sarif(doc_ext, language="python")
    assert res_ext["status"] == "passed"
    assert res_ext["result_count"] == 1

    # 2. GUID matching driver
    doc_driver = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "guid": "driver-guid-5678",
                    "rules": [{
                        "id": "py/driver-rule",
                        "defaultConfiguration": {"level": "note"},
                    }],
                },
                "extensions": [],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "py/driver-rule",
                    "index": 0,
                    "toolComponent": {"guid": "driver-guid-5678", "name": "CodeQL"},
                },
            }],
        }],
    }
    res_driver = validate_sarif(doc_driver, language="python")
    assert res_driver["status"] == "passed"
    assert res_driver["result_count"] == 1

    # 3. Ambiguous GUID (present on both driver and extension)
    doc_ambiguous = {
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "CodeQL",
                    "guid": "shared-guid",
                    "rules": [],
                },
                "extensions": [{
                    "name": "codeql/python-queries",
                    "guid": "shared-guid",
                    "rules": [{"id": "py/ext-rule"}],
                }],
            },
            "invocations": [{"executionSuccessful": True}],
            "results": [{
                "rule": {
                    "id": "py/ext-rule",
                    "index": 0,
                    "toolComponent": {"guid": "shared-guid"},
                },
            }],
        }],
    }
    res_ambiguous = validate_sarif(doc_ambiguous, language="python")
    assert res_ambiguous["status"] == "failed"
    assert any("toolComponent guid is ambiguous: shared-guid" in e for e in res_ambiguous["errors"])


