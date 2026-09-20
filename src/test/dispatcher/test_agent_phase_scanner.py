from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agent_phase import scanner as scanner_module
from agent_phase.scanner import (
    LABEL_OPERATIONAL_FALSE_POSITIVE,
    LABEL_TRUE_POSITIVE,
    STATUS_ERROR,
    STATUS_SCANNED,
    STATUS_UNAVAILABLE,
    ScannerError,
    append_label,
    append_row,
    build_argv,
    scan,
    summarize,
)


SEGMENTS = [
    {"kind": "envelope", "start": 0, "end": 20},
    {"kind": "task_prompt", "start": 20, "end": 60},
]


FAKE_SCANNER_PREAMBLE = '''#!/usr/bin/env python3
import json, os, sys, pathlib
directory = pathlib.Path(sys.argv[-1])
record = os.environ.get("FAKE_SCANNER_RECORD")
if record:
    files = sorted(p.name for p in directory.iterdir())
    blobs = {p.name: p.read_bytes().hex() for p in directory.iterdir()}
    pathlib.Path(record).write_text(
        json.dumps({"argv": sys.argv, "files": files, "blobs": blobs})
    )
'''


def fake_scanner(tmp_path: Path, body: str) -> Path:
    """A deterministic stand-in for the pinned executable."""
    path = tmp_path / "fake-malskanner"
    path.write_text(FAKE_SCANNER_PREAMBLE + body + "\n")
    path.chmod(0o755)
    return path


def verdict_body(verdict: str, findings: list[dict] | None = None) -> str:
    payload = {"verdict": verdict, "findings": findings or []}
    return f"print(json.dumps({payload!r}))\nsys.exit(0)"


def test_absent_scanner_records_unavailable_without_blocking() -> None:
    row = scan(b"prompt", "plan", "run1", SEGMENTS, "01-plan.prompt.md", executable=None)
    assert row["status"] == STATUS_UNAVAILABLE
    assert row["verdict"] is None
    assert row["mode"] == "shadow"


@pytest.mark.parametrize("verdict", ["OK", "WARN", "REFUSE"])
def test_all_verdicts_are_recorded_distinctly(tmp_path: Path, verdict: str) -> None:
    executable = fake_scanner(tmp_path, verdict_body(verdict, [{"rule": "r1", "line": 1}]))
    row = scan(
        b"prompt", "plan", "run1", SEGMENTS, "01-plan.prompt.md",
        executable=str(executable), version="1.2.3",
    )
    assert row["status"] == STATUS_SCANNED
    assert row["verdict"] == verdict
    assert row["scanner_version"] == "1.2.3"


def test_scanner_error_is_never_reported_as_ok(tmp_path: Path) -> None:
    for body in (
        "print('not json'); sys.exit(0)",
        "print(json.dumps({'verdict': 'MAYBE'})); sys.exit(0)",
        "print(json.dumps({'findings': []})); sys.exit(0)",
    ):
        executable = fake_scanner(tmp_path, body)
        row = scan(
            b"prompt", "plan", "run1", SEGMENTS, "01-plan.prompt.md",
            executable=str(executable),
        )
        assert row["status"] == STATUS_ERROR
        assert row["verdict"] is None


def test_scanned_bytes_equal_the_model_facing_prompt(tmp_path: Path) -> None:
    record = tmp_path / "record.json"
    executable = fake_scanner(tmp_path, verdict_body("OK"))
    prompt = b"exact model-facing prompt bytes\n\xe2\x9c\x93"
    os.environ["FAKE_SCANNER_RECORD"] = str(record)
    try:
        scan(prompt, "plan", "run1", SEGMENTS, "01-plan.prompt.md", executable=str(executable))
    finally:
        del os.environ["FAKE_SCANNER_RECORD"]
    captured = json.loads(record.read_text())
    assert captured["files"] == ["01-plan.prompt.md"]
    assert bytes.fromhex(captured["blobs"]["01-plan.prompt.md"]) == prompt


def test_scan_directory_holds_exactly_one_artifact_and_no_repo_content(
    tmp_path: Path,
) -> None:
    record = tmp_path / "record.json"
    executable = fake_scanner(tmp_path, verdict_body("OK"))
    os.environ["FAKE_SCANNER_RECORD"] = str(record)
    try:
        scan(b"p", "plan", "run1", SEGMENTS, "01-plan.prompt.md", executable=str(executable))
    finally:
        del os.environ["FAKE_SCANNER_RECORD"]
    captured = json.loads(record.read_text())
    assert len(captured["files"]) == 1
    scanned_directory = Path(captured["argv"][-1])
    assert scanned_directory != Path.cwd()
    assert not str(scanned_directory).startswith(str(Path.cwd()))


def test_argv_never_enables_ai_and_never_uses_a_package_runner(tmp_path: Path) -> None:
    argv = build_argv("/usr/local/bin/malskanner", tmp_path)
    assert "--ai" not in argv
    assert not any("npx" in part for part in argv)
    assert argv[0] == "/usr/local/bin/malskanner"


def test_module_constructs_no_package_runner_command() -> None:
    source = Path(scanner_module.__file__).read_text()
    assert '"npx"' not in source
    assert "'npx'" not in source
    assert "shutil.which" in source


def test_findings_are_redacted_of_quoted_prompt_text(tmp_path: Path) -> None:
    finding = {
        "rule": "agent-directed-instruction",
        "severity": "warn",
        "line": 1,
        "match": "SECRET PROMPT TEXT",
        "excerpt": "SECRET PROMPT TEXT",
        "context": "SECRET PROMPT TEXT",
    }
    executable = fake_scanner(tmp_path, verdict_body("WARN", [finding]))
    row = scan(
        b"line one\nline two\n", "plan", "run1", SEGMENTS, "01-plan.prompt.md",
        executable=str(executable),
    )
    serialised = json.dumps(row)
    assert "SECRET PROMPT TEXT" not in serialised
    assert row["finding_rules"] == ["agent-directed-instruction"]
    assert row["finding_count"] == 1


def test_findings_are_attributed_to_their_segment(tmp_path: Path) -> None:
    prompt = b"envelope line\ntask line\n"
    segments = [
        {"kind": "envelope", "start": 0, "end": 14},
        {"kind": "task_prompt", "start": 14, "end": len(prompt)},
    ]
    executable = fake_scanner(
        tmp_path, verdict_body("WARN", [{"rule": "r", "line": 2}])
    )
    row = scan(prompt, "plan", "run1", segments, "01-plan.prompt.md", executable=str(executable))
    assert row["finding_segments"] == ["task_prompt"]


def test_telemetry_rows_are_append_only(tmp_path: Path) -> None:
    path = tmp_path / "shadow.jsonl"
    append_row(path, {"scan_id": "a", "verdict": "OK"})
    first = path.read_bytes()
    append_row(path, {"scan_id": "b", "verdict": "WARN"})
    assert path.read_bytes().startswith(first)
    assert len(path.read_text().splitlines()) == 2


def test_labels_never_mutate_prior_scan_rows(tmp_path: Path) -> None:
    scans = tmp_path / "shadow.jsonl"
    labels = tmp_path / "labels.jsonl"
    append_row(scans, {"scan_id": "a", "verdict": "WARN", "finding_count": 1})
    before = scans.read_bytes()
    append_label(labels, "a", LABEL_OPERATIONAL_FALSE_POSITIVE, "envelope wording")
    assert scans.read_bytes() == before
    assert json.loads(labels.read_text().splitlines()[0])["label"] == (
        LABEL_OPERATIONAL_FALSE_POSITIVE
    )


def test_label_correction_is_an_append_and_last_wins(tmp_path: Path) -> None:
    scans = tmp_path / "shadow.jsonl"
    labels = tmp_path / "labels.jsonl"
    append_row(scans, {"scan_id": "a", "verdict": "WARN", "finding_count": 1})
    append_label(labels, "a", LABEL_TRUE_POSITIVE, None)
    append_label(labels, "a", LABEL_OPERATIONAL_FALSE_POSITIVE, "corrected")
    assert len(labels.read_text().splitlines()) == 2
    summary = summarize(scans, labels)
    assert summary["overall"]["operational_false_positives"] == 1


def test_unsupported_label_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ScannerError, match="unsupported label"):
        append_label(tmp_path / "labels.jsonl", "a", "looks_fine", None)


def test_summary_arithmetic(tmp_path: Path) -> None:
    scans = tmp_path / "shadow.jsonl"
    labels = tmp_path / "labels.jsonl"
    rows = [
        {"scan_id": "1", "boundary": "plan", "verdict": "OK", "finding_count": 0,
         "finding_rules": [], "status": STATUS_SCANNED},
        {"scan_id": "2", "boundary": "plan", "verdict": "WARN", "finding_count": 1,
         "finding_rules": ["r1"], "status": STATUS_SCANNED},
        {"scan_id": "3", "boundary": "plan_review", "verdict": "WARN", "finding_count": 1,
         "finding_rules": ["r1"], "status": STATUS_SCANNED},
        {"scan_id": "4", "boundary": "work", "verdict": "REFUSE", "finding_count": 2,
         "finding_rules": ["r2"], "status": STATUS_SCANNED},
        {"scan_id": "5", "boundary": "work", "verdict": "REFUSE", "finding_count": 1,
         "finding_rules": ["r2"], "status": STATUS_SCANNED},
    ]
    for row in rows:
        append_row(scans, row)
    append_label(labels, "2", LABEL_OPERATIONAL_FALSE_POSITIVE, None)
    append_label(labels, "3", LABEL_TRUE_POSITIVE, None)
    append_label(labels, "4", LABEL_OPERATIONAL_FALSE_POSITIVE, None)
    # scan 5 stays unlabeled

    summary = summarize(scans, labels)
    assert summary["total_scans"] == 5
    assert summary["verdict_counts"] == {"OK": 1, "REFUSE": 2, "WARN": 2}

    # findings-bearing = scans 2,3,4,5 -> labeled 3, false positives 2
    assert summary["overall"]["scans"] == 4
    assert summary["overall"]["labeled"] == 3
    assert summary["overall"]["unlabeled"] == 1
    assert summary["overall"]["operational_false_positives"] == 2
    assert summary["overall"]["false_positive_rate"] == pytest.approx(2 / 3)

    # REFUSE = scans 4,5 -> labeled 1, false positives 1
    assert summary["refuse_only"]["false_positive_rate"] == pytest.approx(1.0)
    # WARN = scans 2,3 -> labeled 2, false positives 1
    assert summary["warn_only"]["false_positive_rate"] == pytest.approx(0.5)

    assert summary["per_detector"]["r1"]["labeled"] == 2
    assert summary["per_detector"]["r2"]["operational_false_positives"] == 1
    assert summary["per_boundary"]["work"]["scans"] == 2

    assert summary["hard_gate"] is False
    assert summary["sufficient_for_hard_gate_decision"] is False


def test_summary_reports_no_rate_without_labels(tmp_path: Path) -> None:
    scans = tmp_path / "shadow.jsonl"
    append_row(scans, {"scan_id": "1", "verdict": "WARN", "finding_count": 1,
                       "finding_rules": ["r"], "boundary": "plan"})
    summary = summarize(scans, tmp_path / "labels.jsonl")
    assert summary["overall"]["false_positive_rate"] is None
    assert summary["overall"]["unlabeled"] == 1
