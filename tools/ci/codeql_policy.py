#!/usr/bin/env python3
"""Validate one CodeQL SARIF member against APGR's blocking policy.

The hosted CodeQL action owns upload and GitHub alert state.  This small local
validator makes the evidence contract explicit: a missing or malformed SARIF,
an unsuccessful invocation, an analysis error, or a High/Critical result fails
the matrix member.  It deliberately does not claim that hosted merge
protection has been observed.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "release/ci/codeql_policy.json"
_SARIF_LEVELS = frozenset({"none", "note", "warning", "error"})


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "apg-codeql-policy-v1":
        raise ValueError("unsupported CodeQL policy schema")
    languages = document.get("languages")
    if not isinstance(languages, dict) or not languages:
        raise ValueError("CodeQL policy has no languages")
    return document


def _parse_security_severity(
    value: Any,
    *,
    context: str,
    errors: list[str],
) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        errors.append(f"{context} security-severity is not numeric")
        return None
    try:
        severity = float(value)
    except (TypeError, ValueError):
        errors.append(f"{context} security-severity is not numeric")
        return None
    if not math.isfinite(severity) or not 0.0 <= severity <= 10.0:
        errors.append(f"{context} security-severity is outside the 0.0-10.0 range")
        return None
    return severity


def _rule_records(
    driver: dict[str, Any],
    *,
    run_index: int,
    errors: list[str],
) -> tuple[list[dict[str, Any] | None], dict[str, int]]:
    raw_rules = driver.get("rules", [])
    if not isinstance(raw_rules, list):
        errors.append(f"run {run_index} CodeQL driver rules are not an array")
        return [], {}
    records: list[dict[str, Any] | None] = []
    by_id: dict[str, int] = {}
    for rule_index, raw_rule in enumerate(raw_rules):
        if not isinstance(raw_rule, dict):
            errors.append(f"run {run_index} CodeQL rule {rule_index} is not an object")
            records.append(None)
            continue
        rule_id = raw_rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            errors.append(f"run {run_index} CodeQL rule {rule_index} has no valid id")
            records.append(None)
            continue
        if rule_id in by_id:
            errors.append(f"run {run_index} CodeQL rule id is duplicated: {rule_id}")
        else:
            by_id[rule_id] = rule_index
        properties = raw_rule.get("properties", {})
        if not isinstance(properties, dict):
            errors.append(f"run {run_index} CodeQL rule {rule_id} properties are not an object")
            severity = None
        elif "security-severity" in properties:
            severity = _parse_security_severity(
                properties["security-severity"],
                context=f"run {run_index} CodeQL rule {rule_id}",
                errors=errors,
            )
        else:
            severity = None
        records.append({"id": rule_id, "security_severity": severity})
    return records, by_id


def _resolve_rule(
    result: dict[str, Any],
    *,
    records: list[dict[str, Any] | None],
    by_id: dict[str, int],
    run_index: int,
    result_index: int,
    errors: list[str],
) -> dict[str, Any] | None:
    context = f"run {run_index} result {result_index}"
    raw_rule_id = result.get("ruleId")
    rule_id: str | None
    if raw_rule_id is None:
        rule_id = None
    elif isinstance(raw_rule_id, str) and raw_rule_id:
        rule_id = raw_rule_id
    else:
        errors.append(f"{context} ruleId is not a non-empty string")
        rule_id = None

    raw_rule_index = result.get("ruleIndex")
    rule_index: int | None = None
    if raw_rule_index is not None:
        if (
            isinstance(raw_rule_index, bool)
            or not isinstance(raw_rule_index, int)
            or raw_rule_index < 0
        ):
            errors.append(f"{context} ruleIndex is not a non-negative integer")
        elif raw_rule_index >= len(records):
            errors.append(f"{context} ruleIndex is outside the CodeQL rule array")
        elif records[raw_rule_index] is None:
            errors.append(f"{context} ruleIndex references a malformed CodeQL rule")
        else:
            rule_index = raw_rule_index

    selected_index = rule_index
    if rule_id is not None:
        id_index = by_id.get(rule_id)
        if id_index is None:
            errors.append(f"{context} ruleId is not present in the CodeQL rule array: {rule_id}")
        elif selected_index is not None and selected_index != id_index:
            errors.append(f"{context} ruleId and ruleIndex identify different CodeQL rules")
        else:
            selected_index = id_index
    if selected_index is None:
        if rule_id is None and raw_rule_index is None:
            errors.append(f"{context} has neither ruleId nor ruleIndex")
        return None
    return records[selected_index]


def _validate_notifications(
    invocation: dict[str, Any],
    *,
    run_index: int,
    invocation_index: int,
    errors: list[str],
) -> None:
    for field in ("toolExecutionNotifications", "configurationNotifications"):
        raw_notifications = invocation.get(field, [])
        if not isinstance(raw_notifications, list):
            errors.append(
                f"run {run_index} invocation {invocation_index} {field} are not an array"
            )
            continue
        for notification_index, notification in enumerate(raw_notifications):
            context = (
                f"run {run_index} invocation {invocation_index} "
                f"{field} {notification_index}"
            )
            if not isinstance(notification, dict):
                errors.append(f"{context} is not an object")
                continue
            raw_level = notification.get("level")
            if raw_level is None:
                continue
            if not isinstance(raw_level, str) or raw_level.lower() not in _SARIF_LEVELS:
                errors.append(f"{context} has an invalid level")
            elif raw_level.lower() == "error":
                errors.append(f"{context} reports a CodeQL error")


def validate_sarif(
    sarif: dict[str, Any],
    *,
    language: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = policy or load_policy()
    language_policy = policy.get("languages", {}).get(language)
    if not isinstance(language_policy, dict):
        raise TypeError(f"unknown CodeQL language: {language}")
    if sarif.get("version") != "2.1.0":
        raise ValueError("CodeQL SARIF version must be 2.1.0")
    runs = sarif.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("CodeQL SARIF must contain at least one run")

    errors: list[str] = []
    blocking_results: list[dict[str, Any]] = []
    result_count = 0
    threshold = float(policy["alert_merge_protection"]["high_security_severity_threshold"])
    for run_index, run in enumerate(runs):
        if not isinstance(run, dict):
            errors.append(f"run {run_index} is not an object")
            continue
        raw_tool = run.get("tool", {})
        if not isinstance(raw_tool, dict):
            errors.append(f"run {run_index} tool is not an object")
            tool: dict[str, Any] = {}
        else:
            raw_driver = raw_tool.get("driver", {})
            if not isinstance(raw_driver, dict):
                errors.append(f"run {run_index} CodeQL driver is not an object")
                tool = {}
            else:
                tool = raw_driver
        if tool.get("name") not in {"CodeQL", "codeql"}:
            errors.append(f"run {run_index} does not identify CodeQL")
        records, by_id = _rule_records(tool, run_index=run_index, errors=errors)
        invocations = run.get("invocations", [])
        if not isinstance(invocations, list):
            errors.append(f"run {run_index} invocations are not an array")
            invocations = []
        if not invocations:
            errors.append(f"run {run_index} has no invocation record")
        for invocation_index, invocation in enumerate(invocations):
            if not isinstance(invocation, dict):
                errors.append(f"run {run_index} has malformed invocation")
                continue
            if invocation.get("executionSuccessful") is not True:
                errors.append(f"run {run_index} CodeQL invocation was unsuccessful")
            _validate_notifications(
                invocation,
                run_index=run_index,
                invocation_index=invocation_index,
                errors=errors,
            )
        results = run.get("results", [])
        if not isinstance(results, list):
            errors.append(f"run {run_index} results are not an array")
            continue
        result_count += len(results)
        for result_index, result in enumerate(results):
            if not isinstance(result, dict):
                errors.append(f"run {run_index} contains a malformed result")
                continue
            raw_level = result.get("level", "warning")
            if not isinstance(raw_level, str) or raw_level.lower() not in _SARIF_LEVELS:
                errors.append(f"run {run_index} result {result_index} has an invalid level")
                level = "warning"
            else:
                level = raw_level.lower()
            rule = _resolve_rule(
                result,
                records=records,
                by_id=by_id,
                run_index=run_index,
                result_index=result_index,
                errors=errors,
            )
            result_properties = result.get("properties")
            if result_properties is not None and not isinstance(result_properties, dict):
                errors.append(f"run {run_index} result {result_index} properties are not an object")
            elif isinstance(result_properties, dict) and "security-severity" in result_properties:
                _parse_security_severity(
                    result_properties["security-severity"],
                    context=f"run {run_index} result {result_index}",
                    errors=errors,
                )
                errors.append(
                    f"run {run_index} result {result_index} places security-severity "
                    "on the result instead of its CodeQL rule"
                )
            severity = rule.get("security_severity") if rule is not None else None
            resolved_rule_id = (
                rule.get("id") if rule is not None else result.get("ruleId", "<unknown>")
            )
            if level == "error" or (
                severity is not None
                and severity >= threshold
            ):
                blocking_results.append(
                    {
                        "ruleId": resolved_rule_id,
                        "level": level,
                        "security_severity": severity,
                    }
                )

    return {
        "schema": "apg-codeql-result-v1",
        "language": language,
        "matrix_member": language_policy["matrix_member"],
        "sarif_file": language_policy["sarif_file"],
        "result_count": result_count,
        "blocking_results": blocking_results,
        "errors": errors,
        "status": "passed" if not errors and not blocking_results else "failed",
    }


def _find_sarif(directory: Path, filename: str) -> Path:
    exact = directory / filename
    if exact.is_file() and not exact.is_symlink():
        return exact
    matches = sorted(
        path for path in directory.rglob("*.sarif")
        if path.is_file() and not path.is_symlink() and path.name == filename
    )
    if len(matches) != 1:
        raise ValueError(f"expected one SARIF file named {filename}, found {len(matches)}")
    return matches[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True)
    parser.add_argument("--sarif-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        policy = load_policy()
        language_policy = policy["languages"].get(args.language)
        if not isinstance(language_policy, dict):
            raise TypeError(f"unknown CodeQL language: {args.language}")
        path = _find_sarif(args.sarif_dir, language_policy["sarif_file"])
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise TypeError("SARIF root must be an object")
        result = validate_sarif(document, language=args.language, policy=policy)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(
            json.dumps(
                {"schema": "apg-codeql-result-v1", "status": "failed", "errors": [str(error)]}
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
