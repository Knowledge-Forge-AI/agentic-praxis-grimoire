"""MalSkanner SHADOW telemetry.

This module measures false positives on the exact prompt surfaces a later phase
might hard-gate. It never gates anything: no caller branches on the verdict, and
`REFUSE` is telemetry until an operator decides otherwise on real data.

Two deliberate omissions:
  * there is no `npx` code path at all, so no unpinned fetch is reachable;
  * `--ai` is never constructed, so shadow data stays deterministic.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
from typing import Any


SCANNER_NAME = "malskanner"
VERDICT_OK = "OK"
VERDICT_WARN = "WARN"
VERDICT_REFUSE = "REFUSE"
VERDICTS = (VERDICT_OK, VERDICT_WARN, VERDICT_REFUSE)

STATUS_SCANNED = "SCANNED"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUS_ERROR = "SCANNER_ERROR"

LABEL_TRUE_POSITIVE = "true_positive"
LABEL_OPERATIONAL_FALSE_POSITIVE = "operational_false_positive"
LABEL_AMBIGUOUS = "ambiguous"
LABEL_SCANNER_ERROR = "scanner_error"
LABELS = (
    LABEL_TRUE_POSITIVE,
    LABEL_OPERATIONAL_FALSE_POSITIVE,
    LABEL_AMBIGUOUS,
    LABEL_SCANNER_ERROR,
)

SCAN_TIMEOUT_SECONDS = 120
# Findings may quote the prompt that matched. Prompts carry prior model material
# and operator task text, and this telemetry file is long-lived and append-only,
# so only non-quoting fields are ever persisted.
FINDING_FIELDS = ("rule", "severity", "line")


class ScannerError(RuntimeError):
    """The scanner could not be invoked as shadow telemetry requires."""


def resolve_scanner() -> str | None:
    """Installed, pinned executable only. No package-runner fallback exists."""
    return shutil.which(SCANNER_NAME)


def scanner_version(executable: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            timeout=SCAN_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8", "replace").strip() or None


def build_argv(executable: str, directory: Path) -> list[str]:
    """Deterministic scan of one isolated directory.

    The subcommand shape is the documented expectation for the pinned
    executable; it is asserted by test and must be re-verified when MalSkanner is
    actually installed on a host.
    """
    return [executable, "scan", "--json", os.fspath(directory)]


def redact_findings(payload: Any) -> list[dict[str, Any]]:
    findings = payload.get("findings") if isinstance(payload, dict) else None
    if not isinstance(findings, list):
        return []
    redacted: list[dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        redacted.append(
            {field: finding.get(field) for field in FINDING_FIELDS if field in finding}
        )
    return redacted


def attribute(finding: dict[str, Any], segments: list[dict[str, Any]], text: bytes) -> str | None:
    """Map a finding to its originating segment when the scanner locates it."""
    line = finding.get("line")
    if not isinstance(line, int) or line < 1:
        return None
    offset = 0
    for index, raw_line in enumerate(text.splitlines(keepends=True), start=1):
        if index == line:
            break
        offset += len(raw_line)
    else:
        return None
    for segment in segments:
        if segment["start"] <= offset < segment["end"]:
            return str(segment["kind"])
    return None


def scan(
    prompt: bytes,
    boundary: str,
    run_id: str,
    segments: list[dict[str, Any]],
    artifact_name: str,
    executable: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """Scan exactly the model-facing prompt bytes, in isolation from any repo."""
    row: dict[str, Any] = {
        "schema": "malskanner-shadow-v1",
        "scan_id": f"{run_id}-{boundary}-{secrets.token_hex(4)}",
        "run_id": run_id,
        "boundary": boundary,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
        "prompt_bytes": len(prompt),
        "segments": segments,
        "mode": "shadow",
        "scanner": SCANNER_NAME,
        "scanner_version": version,
        "invocation": None,
        "exit_code": None,
        "verdict": None,
        "finding_count": 0,
        "finding_rules": [],
        "finding_segments": [],
        "status": STATUS_UNAVAILABLE,
        "detail": None,
    }
    if executable is None:
        row["detail"] = "malskanner executable not found on PATH"
        return row
    row["scanner_executable"] = executable

    # The scan directory contains exactly the one prompt artifact. Scanning the
    # target repository instead would mix repository findings into prompt FPR data.
    with tempfile.TemporaryDirectory(prefix="agent-phase-scan-") as scratch:
        directory = Path(scratch)
        (directory / artifact_name).write_bytes(prompt)
        argv = build_argv(executable, directory)
        row["invocation"] = list(argv)
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                timeout=SCAN_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            row["status"] = STATUS_ERROR
            row["detail"] = f"scanner invocation failed: {error}"
            return row

    row["exit_code"] = completed.returncode
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        row["status"] = STATUS_ERROR
        row["detail"] = f"scanner output is not JSON: {error}"
        return row

    verdict = payload.get("verdict") if isinstance(payload, dict) else None
    if verdict not in VERDICTS:
        row["status"] = STATUS_ERROR
        row["detail"] = f"unrecognised scanner verdict: {verdict!r}"
        return row

    findings = redact_findings(payload)
    row["status"] = STATUS_SCANNED
    row["verdict"] = verdict
    row["finding_count"] = len(findings)
    row["finding_rules"] = sorted(
        {str(finding["rule"]) for finding in findings if finding.get("rule")}
    )
    row["finding_segments"] = [attribute(finding, segments, prompt) for finding in findings]
    return row


def append_row(path: Path, row: dict[str, Any]) -> None:
    """Append one JSONL record under an advisory lock. Rows are never rewritten."""
    line = json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    descriptor = os.open(path, flags, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        os.write(descriptor, line.encode("utf-8"))
    finally:
        os.close(descriptor)


def append_label(path: Path, scan_id: str, label: str, note: str | None) -> dict[str, Any]:
    """Labels live in their own append-only file; scan rows stay immutable."""
    if label not in LABELS:
        raise ScannerError(f"unsupported label: {label}")
    record = {
        "schema": "malskanner-shadow-label-v1",
        "scan_id": scan_id,
        "label": label,
        "note": note,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    append_row(path, record)
    return record


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def summarize(scan_path: Path, label_path: Path) -> dict[str, Any]:
    scans = read_rows(scan_path)
    # Last label wins: correction is an append, never an edit of a prior row.
    labels: dict[str, str] = {}
    for record in read_rows(label_path):
        scan_id = record.get("scan_id")
        label = record.get("label")
        if isinstance(scan_id, str) and label in LABELS:
            labels[scan_id] = label

    def rate(subset: list[dict[str, Any]]) -> dict[str, Any]:
        labeled = [row for row in subset if labels.get(row.get("scan_id", "")) is not None]
        false_positives = [
            row
            for row in labeled
            if labels[row["scan_id"]] == LABEL_OPERATIONAL_FALSE_POSITIVE
        ]
        return {
            "scans": len(subset),
            "labeled": len(labeled),
            "unlabeled": len(subset) - len(labeled),
            "operational_false_positives": len(false_positives),
            "false_positive_rate": (
                len(false_positives) / len(labeled) if labeled else None
            ),
        }

    findings_bearing = [row for row in scans if row.get("finding_count")]
    refusals = [row for row in scans if row.get("verdict") == VERDICT_REFUSE]
    warnings = [row for row in scans if row.get("verdict") == VERDICT_WARN]

    per_detector: dict[str, list[dict[str, Any]]] = {}
    for row in scans:
        for rule in row.get("finding_rules") or []:
            per_detector.setdefault(str(rule), []).append(row)
    per_boundary: dict[str, list[dict[str, Any]]] = {}
    for row in findings_bearing:
        per_boundary.setdefault(str(row.get("boundary")), []).append(row)

    overall = rate(findings_bearing)
    return {
        "schema": "malskanner-shadow-summary-v1",
        "mode": "shadow",
        "hard_gate": False,
        "total_scans": len(scans),
        "status_counts": _counts(scans, "status"),
        "verdict_counts": _counts(scans, "verdict"),
        "overall": overall,
        "refuse_only": rate(refusals),
        "warn_only": rate(warnings),
        "per_detector": {rule: rate(rows) for rule, rows in sorted(per_detector.items())},
        "per_boundary": {name: rate(rows) for name, rows in sorted(per_boundary.items())},
        "sufficient_for_hard_gate_decision": False,
        "caveat": (
            "Shadow telemetry only. False-positive rate is computed over labeled "
            "findings-bearing scans; unlabeled scans are excluded from the "
            "denominator, so a small or skewed labeled sample does not support "
            "any hard-gate decision."
        ),
    }


def _counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))
