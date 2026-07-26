"""Unit contracts for operational report parsing, association, and rendering."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from agent_report import models, operational, safety  # noqa: E402


SHOW_COMMIT = "a" * 40
SHOW_ID = f"GIT-SHOW-REPORT-{SHOW_COMMIT}"
DIFF_ID = "GIT-DIFF-REPORT-" + "b" * 64


def parsed(record_type: str, version: int, record_id: str) -> models.ParsedRecord:
    record = models.ReportRecord(
        record_type, version, record_id, "project", "APG28A", b"payload\n"
    )
    return models.ParsedRecord(record, "0" * 64, 0, 1)


def source(raw: bytes) -> operational.OperationalSource:
    return operational.load_operational_source(Path("evidence.txt"), raw)


def build(
    item: operational.OperationalSource,
    *,
    related_commit: str = "NONE",
    related_id: str = "NONE",
    records: tuple[models.ParsedRecord, ...] = (),
) -> models.ReportRecord:
    return operational.build_operational_record(
        source=item,
        project="project",
        phase="APG28A",
        result="complete",
        final_gate="focused",
        related_commit=related_commit,
        related_git_report_id=related_id,
        existing_records=records,
    )


def test_related_git_id_and_source_schema_parsing_are_strict() -> None:
    assert operational.validate_related_git_report_id(SHOW_ID) == SHOW_ID
    assert operational.validate_related_git_report_id(DIFF_ID) == DIFF_ID
    for value in ("", "GIT-SHOW-REPORT-" + "g" * 40, "GIT-DIFF-REPORT-abc"):
        with pytest.raises(safety.UsageError, match="malformed"):
            operational.validate_related_git_report_id(value)

    declared = source(
        b"REPORT\nreport_schema: operational-report-v1\nphase: APG28A\n"
        b"outcome: complete\nprimary_commit: " + SHOW_COMMIT.encode() + b"\n"
        b"primary_git_report_id: " + DIFF_ID.encode()
    )
    assert declared.body_schema == "operational-report-v1"
    assert declared.declared_phase == "APG28A"
    assert declared.declared_outcome == "complete"
    assert declared.primary_commit == SHOW_COMMIT
    assert declared.primary_git_report_id == DIFF_ID
    assert declared.framed.endswith(b"\n")
    assert source(b"phase: OLD\noutcome: partial").body_schema == "legacy-key-value"
    assert source(b"# free form").body_schema == "free-form"


def test_source_parsing_rejects_empty_duplicates_and_unbounded_fields() -> None:
    with pytest.raises(safety.ReportError, match="empty"):
        source(b"")
    duplicate = (
        b"report_schema: operational-report-v1\nphase: APG28A\nphase: APG28A\n"
    )
    with pytest.raises(safety.ReportError, match="duplicate phase"):
        source(duplicate)
    unknown = source(
        b"report_schema: operational-report-v1\nphase: bad\x00value\n"
        b"outcome: " + b"x" * 257
    )
    assert unknown.declared_phase == "UNKNOWN"
    assert unknown.declared_outcome == "UNKNOWN"
    assert operational._bounded_field(b"\xff") == "UNKNOWN"
    assert operational._first_value(()) == b""
    assert operational._all_fields(b"phase: A\nphase: B", (b"phase",)) == (b"A", b"B")


def test_standalone_record_preserves_body_and_renders_integrity() -> None:
    item = source(
        b"REPORT\nreport_schema: operational-report-v1\n"
        b"phase: APG28A\noutcome: complete"
    )
    record = build(item)
    assert record.record_type == "operational-report"
    assert record.record_id.startswith("OPERATIONAL-REPORT-")
    assert b"BODY-SCHEMA-DETECTED: operational-report-v1\n" in record.payload
    assert b"RELATED-COMMIT-COUNT: 0\n" in record.payload
    assert b"END-OF-OPERATIONAL-BODY-REACHED: true\n" in record.payload
    assert item.framed in record.payload


def test_show_and_diff_associations_require_truthful_declared_identity() -> None:
    show_source = source(
        b"report_schema: operational-report-v1\nphase: APG28A\n"
        b"outcome: complete\nprimary_commit: " + SHOW_COMMIT.encode()
    )
    show_record = parsed("git-show-report", 2, SHOW_ID)
    rendered = build(
        show_source,
        related_commit=SHOW_COMMIT,
        related_id=SHOW_ID,
        records=(show_record,),
    )
    assert b"RELATED-COMMIT-COUNT: 1\n" in rendered.payload

    diff_source = source(
        b"report_schema: operational-report-v1\nphase: APG28A\n"
        b"outcome: complete\nprimary_git_report_id: " + DIFF_ID.encode()
    )
    diff_record = parsed("git-diff-report", 1, DIFF_ID)
    rendered = build(diff_source, related_id=DIFF_ID, records=(diff_record,))
    assert b"SOURCE-PRIMARY-GIT-REPORT-ID: " + DIFF_ID.encode() in rendered.payload


@pytest.mark.parametrize(
    "item,commit,relation,records,message",
    [
        (source(b"free form"), "NONE", SHOW_ID, (parsed("git-show-report", 2, SHOW_ID),), "must use operational-report-v1"),
        (source(b"report_schema: operational-report-v1\nphase: WRONG\noutcome: complete"), "NONE", "NONE", (), "phase does not match"),
        (source(b"report_schema: operational-report-v1\nphase: APG28A\noutcome: wrong"), "NONE", "NONE", (), "outcome does not match"),
        (source(b"report_schema: operational-report-v1\nphase: APG28A\noutcome: complete"), SHOW_COMMIT, "NONE", (), "requires a related"),
        (source(b"report_schema: operational-report-v1\nphase: APG28A\noutcome: complete"), "NONE", SHOW_ID, (parsed("git-show-report", 2, SHOW_ID),), "requires --related-commit"),
        (source(b"report_schema: operational-report-v1\nphase: APG28A\noutcome: complete\nprimary_commit: " + SHOW_COMMIT.encode()), "c" * 40, SHOW_ID, (parsed("git-show-report", 2, SHOW_ID),), "conflict"),
        (source(b"report_schema: operational-report-v1\nphase: APG28A\noutcome: complete\nprimary_commit: " + ("c" * 40).encode()), SHOW_COMMIT, SHOW_ID, (parsed("git-show-report", 2, SHOW_ID),), "primary_commit"),
        (source(b"report_schema: operational-report-v1\nphase: APG28A\noutcome: complete\nprimary_git_report_id: wrong"), "NONE", DIFF_ID, (parsed("git-diff-report", 1, DIFF_ID),), "primary_git_report_id"),
    ],
)
def test_association_failures_are_bounded(
    item: operational.OperationalSource,
    commit: str,
    relation: str,
    records: tuple[models.ParsedRecord, ...],
    message: str,
) -> None:
    with pytest.raises((safety.ReportError, safety.UsageError), match=message):
        build(item, related_commit=commit, related_id=relation, records=records)


def test_existing_git_records_must_be_canonical_and_match_the_destination() -> None:
    item = source(
        b"report_schema: operational-report-v1\nphase: APG28A\noutcome: complete"
    )
    cases = (
        parsed("git-show-report", 1, SHOW_ID),
        parsed("git-show-report", 2, "bad"),
        parsed("git-diff-report", 2, DIFF_ID),
        parsed("git-diff-report", 1, "bad"),
    )
    for record in cases:
        with pytest.raises(safety.ReportError, match="unsupported|malformed"):
            build(item, records=(record,))
    conflicting = models.ParsedRecord(
        models.ReportRecord("git-show-report", 2, SHOW_ID, "other", "APG28A", b""),
        "0" * 64,
        0,
        0,
    )
    with pytest.raises(safety.ReportError, match="identity conflicts"):
        build(item, records=(conflicting,))
    with pytest.raises(safety.ReportError, match="does not exist"):
        build(item, related_id=DIFF_ID)
