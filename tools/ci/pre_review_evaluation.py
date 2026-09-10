"""Evaluation and policy classification for APGR pre-review check results."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.pre_review_records import (
    CI_ROOT,
    FINDING_RETURN_CODES,
    INTERNAL_FAILURE,
    MODULE_FAILURE,
    POLICY_CHECKS,
    Check,
)
from tools.ci.betterleaks_dispositions import load_records, reconcile


def historical_ruff_findings(root: Path, findings: list) -> int:
    """Classify two immutable APG140 fixture observations, never a lint baseline.

    APGR-V0110-READINESS4 pre_final review under Decision B preserves accepted historical fixture bytes. The public
    APG140 support binding owns this exact source; independent pre-final review
    must disposition this classification with the rest of the candidate.
    """
    relative = "src/test/support/apg_external_compatibility_fixture.py"
    path = root / relative
    expected = {(31, 8, "`stat` imported but unused"),
                (32, 44, "`typing.Sequence` imported but unused")}
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != (
        "40b7e98fd862977d83a5e6a01113435bc1b6c47a710668c82faf5d45ff10369e"
    ):
        return 0
    accepted = 0
    for row in findings:
        location = row["location"]
        identity = (location["row"], location["column"], row["message"])
        reported = Path(row["filename"])
        if not reported.is_absolute():
            reported = root / reported
        if row["code"] == "F401" and reported == path and identity in expected:
            expected.remove(identity)
            accepted += 1
    return accepted


def baseline() -> dict:
    """Load the pre-review ratchets from the baseline JSON file."""
    return json.loads((CI_ROOT / "pre_review_baseline.json").read_text(encoding="utf-8"))[
        "ratchets"
    ]


def finding_count(policy: str, output: str) -> int:
    """Count findings in machine-readable checker output."""
    document = json.loads(output or "null")
    if policy == "hadolint":
        if not isinstance(document, list) or not all(isinstance(item, dict) for item in document):
            raise ValueError("hadolint JSON has no valid finding collection")
        return len(document)
    if policy == "pip-audit":
        dependencies = document.get("dependencies", document) if isinstance(document, dict) else document
        if isinstance(dependencies, list):
            return sum(len(item.get("vulns", [])) for item in dependencies if isinstance(item, dict))
        return 0
    if policy == "zizmor":
        if isinstance(document, list) and all(isinstance(item, dict) for item in document):
            return len(document)
        for key in ("findings", "results", "audits"):
            if isinstance(document, dict) and isinstance(document.get(key), list):
                if not all(isinstance(item, dict) for item in document[key]):
                    raise ValueError("zizmor finding collection is malformed")
                return len(document[key])
        raise ValueError("zizmor JSON has no finding collection")
    if policy == "betterleaks":
        if isinstance(document, list) and all(isinstance(item, dict) for item in document):
            return len(document)
        raise ValueError("BetterLeaks JSON has no valid finding collection")
    raise ValueError(f"unknown finding policy {policy}")


def _govulncheck_records(output: str) -> tuple[int, int, int]:
    """Return (all findings, reachable findings, error records) from JSONL output."""
    decoder = json.JSONDecoder()
    position = 0
    records: list[dict[str, Any]] = []
    while position < len(output):
        while position < len(output) and output[position].isspace():
            position += 1
        if position >= len(output):
            break
        try:
            value, position = decoder.raw_decode(output, position)
        except json.JSONDecodeError as error:
            raise ValueError("govulncheck JSON stream is malformed") from error
        if not isinstance(value, dict):
            raise TypeError("govulncheck JSON record is not an object")
        records.append(value)
    if not records:
        raise ValueError("govulncheck JSON stream is empty")
    if not any("config" in record for record in records):
        raise ValueError("govulncheck JSON stream has no configuration record")
    findings = 0
    reachable = 0
    errors = 0
    for record in records:
        if "error" in record:
            errors += 1
        finding = record.get("finding")
        if finding is None:
            continue
        if not isinstance(finding, dict):
            raise TypeError("govulncheck finding record is malformed")
        findings += 1
        trace = finding.get("trace", [])
        if trace is not None and not isinstance(trace, list):
            raise ValueError("govulncheck finding trace is malformed")
        if trace:
            reachable += 1
    return findings, reachable, errors


def evaluate(
    check: Check,
    returncode: int,
    stdout: str,
    stderr: str = "",
) -> tuple[str, str, str]:
    """Evaluate check execution outcome against policy, returning (status, detail, classification)."""
    failure_output = stdout + stderr

    # Explicit missing-executable exit from shells (127) or tool not found
    if returncode == 127 or "command not found" in failure_output or "No such file or directory" in stderr:
        return "failed", f"tool/executable unavailable: {check.name}", "tool-failure"

    if returncode != 0 and MODULE_FAILURE.search(failure_output):
        return "failed", "tool/bootstrap failure: Python module unavailable", "tool-failure"
    if returncode != 0 and INTERNAL_FAILURE.search(failure_output):
        return "failed", "tool/internal failure: bounded diagnostic retained", "tool-failure"

    if check.policy == "ruff":
        if returncode not in {0, 1}:
            return "failed", "Ruff execution failed", "tool-failure"
        try:
            findings = json.loads(stdout)
            if not isinstance(findings, list) or returncode != int(bool(findings)):
                raise ValueError("Ruff result/exit disagreement")
            historical = historical_ruff_findings(check.cwd, findings)
        except (OSError, KeyError, TypeError, ValueError):
            return "failed", "Ruff result or historical input invalid", "tool-failure"
        unresolved = len(findings) - historical
        detail = f"observations={len(findings)}; immutable_historical={historical}; unresolved={unresolved}"
        return ("failed", detail, "policy-finding") if unresolved else ("passed", detail, "passed")

    if check.policy == "file-length":
        if returncode not in {0, 1}:
            return "failed", "file-length input or tool failure", "tool-failure"
        try:
            document = json.loads(stdout)
            if document["version"] != 1 or document["profile"] != "file-length":
                raise ValueError("unsupported file-length result")
            if (document["warning_limit"], document["failure_limit"]) != (400, 1000):
                raise ValueError("unapproved limits")
            scanned, warnings, failures = (document[key] for key in
                                          ("scanned_file_count", "warning_count", "failure_count"))
            if any(type(n) is not int or n < 0 for n in (scanned, warnings, failures)) or not scanned:
                raise ValueError("invalid counts or zero targets")
            findings = document["findings"]
            if not isinstance(findings, list) or len(findings) != warnings + failures:
                raise ValueError("incomplete finding inventory")
            if sum(f["severity"] == "warning" for f in findings) != warnings:
                raise ValueError("warning count disagreement")
            if sum(f["severity"] == "failure" for f in findings) != failures:
                raise ValueError("failure count disagreement")
            expected_status = "failed" if failures else "passed_with_warnings" if warnings else "passed"
            if document["status"] != expected_status or returncode != int(bool(failures)):
                raise ValueError("exit/result disagreement")
        except (KeyError, TypeError, ValueError):
            return "failed", "file-length result contract invalid", "tool-failure"
        detail = f"scanned={scanned}; warnings={warnings}; failures={failures}"
        return ("failed", detail, "policy-finding") if failures else ("passed", detail, "passed")

    if check.policy == "retained-python-ratchets":
        try:
            document = json.loads(stdout)
            if document.get("schema") not in {
                "apg-retained-python-ratchets-result-v1",
                "repomap-retained-python-ratchets-result-v1",
            }:
                raise ValueError("invalid schema")
            classification = document["classification"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return "failed", "retained ratchet JSON was invalid", "tool-failure"
        expected = {
            0: "passed",
            1: "policy-finding",
            2: "tool-failure",
        }
        if expected.get(returncode) != classification:
            return "failed", "retained ratchet exit contract was invalid", "tool-failure"
        if returncode == 0:
            return "passed", "exact retained baseline", "passed"
        if returncode == 1:
            return "failed", "retained Python ratchet delta", "policy-finding"
        return "failed", "retained Python ratchet tool failure", "tool-failure"

    if check.name == "python-retention-inventory":
        try:
            document = json.loads(stdout)
            if not isinstance(document, dict):
                raise TypeError("retention inventory is not an object")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return "failed", "retention inventory JSON was invalid", "tool-failure"
        if "error" in document:
            return "failed", f"tool/validation failure: {document['error']}", "tool-failure"
        status = document.get("status", "passed" if returncode == 0 else "failed")
        classification = document.get("classification", "passed" if returncode == 0 else "policy-finding")
        detail = document.get("detail", f"status={status}; exit={returncode}")
        if status == "passed" and returncode == 0:
            return "passed", detail, "passed"
        return "failed", detail, classification

    if check.name == "govulncheck":
        try:
            finding_total, reachable, error_records = _govulncheck_records(stdout)
        except (TypeError, ValueError) as error:
            return "failed", str(error), "tool-failure"
        if error_records:
            return "failed", f"govulncheck reported {error_records} error record(s)", "tool-failure"
        if returncode not in {0, 3}:
            return "failed", f"govulncheck operational failure: exit={returncode}", "tool-failure"
        detail = f"findings={finding_total}; reachable={reachable}; module-package={finding_total - reachable}"
        if reachable:
            return "failed", detail, "policy-finding"
        return "passed", detail, "passed"

    if check.name == "pip-audit":
        try:
            document = json.loads(stdout)
            if document.get("schema") != "apg-dependency-audit-v1":
                raise ValueError("unsupported dependency-audit schema")
            inventories = document.get("inventories")
            if not isinstance(inventories, list) or not inventories:
                raise ValueError("dependency-audit inventories are empty")
            finding_total = document.get("finding_count")
            tool_failure_count = document.get("tool_failure_count")
            policy_finding_count = document.get("policy_finding_count")
            if not all(
                isinstance(value, int) and value >= 0
                for value in (finding_total, tool_failure_count, policy_finding_count)
            ):
                raise TypeError("dependency-audit counts are invalid")
            for inventory in inventories:
                if not isinstance(inventory, dict):
                    raise TypeError("dependency-audit inventory is malformed")
                if inventory.get("classification") not in {
                    "passed",
                    "policy-finding",
                    "tool-failure",
                }:
                    raise ValueError("dependency-audit inventory classification is invalid")
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return "failed", "dependency-audit JSON was invalid", "tool-failure"
        if tool_failure_count:
            return "failed", f"dependency-audit tool failures={tool_failure_count}", "tool-failure"
        if policy_finding_count:
            return "failed", f"dependency-audit findings={finding_total}", "policy-finding"
        if returncode == 0 and finding_total == 0 and document.get("classification") == "passed":
            return "passed", "dependency inventories resolved; findings=0", "passed"
        return "failed", "dependency-audit exit/result contract was invalid", "tool-failure"

    if check.policy == "betterleaks":
        if returncode not in {0, 1}:
            return "failed", f"scanner operational failure: exit={returncode}", "tool-failure"
        try:
            count = finding_count("betterleaks", stdout)
            if returncode and not count:
                return "failed", "scanner failure supplied no findings", "tool-failure"
            records = load_records(check.cwd / "tools/ci/betterleaks_dispositions.json")
            result = reconcile(check.cwd, json.loads(stdout), records)
        except (OSError, TypeError, ValueError, KeyError):
            return "failed", "BetterLeaks disposition/source readback invalid", "tool-failure"
        detail = "; ".join(f"{key}={value}" for key, value in result.items())
        blocking = result["unresolved"] or result["unmatched_dispositions"]
        return ("failed", detail, "policy-finding") if blocking else ("passed", detail, "passed")

    if check.policy in {"hadolint", "pip-audit", "zizmor"}:
        # zizmor runs with --no-exit-codes: findings remain in JSON while
        # nonzero means operational failure. Other pinned scanners use 1
        # for findings and must never turn arbitrary error exits into a pass.
        admitted_exits = {0} if check.policy == "zizmor" else {0, 1}
        if returncode not in admitted_exits:
            return "failed", f"scanner operational failure: exit={returncode}", "tool-failure"
        try:
            count = finding_count(check.policy, stdout)
        except (TypeError, ValueError, json.JSONDecodeError):
            return "failed", "machine-readable finding output was invalid", "tool-failure"
        allowed = baseline().get(check.policy, {}).get("findings", 0)
        if returncode and not count:
            return "failed", "scanner failure supplied no findings", "tool-failure"
        return (
            ("passed", f"findings={count}; baseline={allowed}", "passed")
            if count <= allowed
            else (
                "failed",
                f"findings={count}; baseline={allowed}",
                "policy-finding",
            )
        )

    if check.policy == "malskanner":
        try:
            document = json.loads(stdout)
            findings = document["findings"]
            verdict = document["verdict"]
            if not isinstance(findings, list) or not isinstance(verdict, str):
                raise ValueError("invalid MalSkanner fields")
            count = len(findings)
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return "failed", "MalSkanner output was invalid", "tool-failure"
        if returncode not in {0, 1}:
            return "failed", f"MalSkanner operational failure: exit={returncode}", "tool-failure"
        passed = returncode == 0 and verdict == "OK" and count == 0
        return (
            "passed" if passed else "failed",
            f"verdict={verdict}; findings={count}",
            "passed" if passed else "policy-finding",
        )

    if check.policy == "suppressions":
        try:
            document = json.loads(stdout)
            if document.get("schema") not in {
                "apg-scanner-suppression-inventory-v1",
                "repomap-scanner-suppression-inventory-v2",
                "apg-scanner-suppression-inventory-v3",
            }:
                raise ValueError("unsupported suppression schema")
            counts = {
                name: len(document[name])
                for name in ("added", "broadened", "context_changed", "removed", "unchanged", "unapproved_or_expired")
                if name in document
            }
            blocking = bool(document.get("blocking", False))
        except (KeyError, TypeError, json.JSONDecodeError, ValueError):
            return "failed", "suppression inventory output was invalid", "tool-failure"
        detail = "; ".join(f"{name}={counts[name]}" for name in counts)
        if returncode not in {0, 1} or blocking != (returncode == 1):
            return "failed", "suppression inventory exit contract was invalid", "tool-failure"
        return (
            ("failed", detail, "policy-finding")
            if blocking
            else ("passed", detail, "passed")
        )

    if check.name == "prompt-defense-audit":
        try:
            summary = json.loads(stdout)
            valid = isinstance(summary, dict) and all(
                key in summary
                for key in ("score", "missing", "embedded_payloads", "unicode_issues")
            )
            valid = valid and all(isinstance(summary[key], list) for key in ("missing", "embedded_payloads", "unicode_issues"))
            valid = valid and isinstance(summary["score"], (int, float)) and not isinstance(summary["score"], bool)
        except (TypeError, json.JSONDecodeError):
            valid = False
        if not valid:
            return "failed", "tool/configuration failure: invalid prompt audit", "tool-failure"
        if returncode not in {0, 1} or summary["missing"]:
            return "failed", "prompt audit inputs or execution unavailable", "tool-failure"
        min_score = baseline().get("prompt-defense", {}).get("minimum_score", 80)
        score = summary.get("score", 0)
        findings = len(summary.get("embedded_payloads", [])) + len(summary.get("unicode_issues", []))
        if score < min_score or findings > 0:
            return "failed", f"score={score} (min {min_score}); findings={findings}", "policy-finding"
        return "passed", f"score={score}", "passed"

    if check.name == "ci-topology":
        if returncode == 0:
            return "passed", "topology contracts satisfied", "passed"
        if returncode == 1:
            return "failed", f"topology violation: {stdout.strip() or stderr.strip()}", "policy-finding"
        return "failed", f"ci-topology error: exit={returncode}", "tool-failure"

    if check.name == "generated-code-drift":
        if returncode == 0:
            return "passed", "zero generated drift", "passed"
        if returncode == 1:
            return "failed", "generated artifact drift detected", "policy-finding"
        return "failed", f"tool/configuration failure: generated drift exit={returncode}", "tool-failure"

    if check.name == "liquibase":
        if returncode == 0:
            return "passed", "liquibase validation clean", "passed"
        if "Liquibase" in failure_output and "Validation" in failure_output:
            return "failed", f"liquibase validation finding: exit={returncode}", "policy-finding"
        return "failed", f"liquibase tool failure: exit={returncode}", "tool-failure"

    if check.name in FINDING_RETURN_CODES and returncode != 0:
        if returncode in FINDING_RETURN_CODES[check.name]:
            return "failed", f"{check.name} policy findings (exit={returncode})", "policy-finding"
        return "failed", f"tool/configuration failure: exit={returncode}", "tool-failure"

    if returncode == 0:
        return "passed", "exit=0", "passed"

    classification = "policy-finding" if check.name in POLICY_CHECKS else "tool-failure"
    return "failed", f"exit={returncode}", classification
