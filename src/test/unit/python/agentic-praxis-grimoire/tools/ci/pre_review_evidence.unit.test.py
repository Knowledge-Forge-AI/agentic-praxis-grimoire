"""Unit tests for pre_review_evidence envelope creation, sealing, and verification."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.ci.pre_review_evidence import (
    LOG_CAP_BYTES,
    bounded_log,
    finalize_evidence,
    verify_evidence,
)
from tools.ci.pre_review_records import Check, Result


def test_bounded_log_within_limit() -> None:
    text = "clean log within limit"
    assert bounded_log(text) == text


def test_bounded_log_truncation() -> None:
    large_text = "x" * (LOG_CAP_BYTES + 500)
    capped = bounded_log(large_text)
    assert len(capped.encode("utf-8")) == LOG_CAP_BYTES
    assert "[log truncated at bounded evidence cap]" in capped


def test_finalize_and_verify_evidence(tmp_path: Path) -> None:
    c1 = Check("check1", ("echo", "hello"))
    c2 = Check("check2", ("echo", "world"))
    selected = (c1, c2)

    (tmp_path / "check1.log").write_text("log 1", encoding="utf-8")
    (tmp_path / "check2.log").write_text("log 2", encoding="utf-8")

    r1 = Result("check1", "passed", 0, 0.1, "clean", "passed", None)
    r2 = Result("check2", "passed", 0, 0.2, "clean", "passed", None)
    results = (r1, r2)

    headroom = finalize_evidence(tmp_path, selected, results)
    assert headroom > 0
    assert (tmp_path / "manifest.json").is_file()
    assert (tmp_path / "results.json").is_file()

    verify_evidence(tmp_path, selected)


def test_verify_evidence_rejects_missing_file(tmp_path: Path) -> None:
    c1 = Check("check1", ("echo", "hello"))
    (tmp_path / "check1.log").write_text("log 1", encoding="utf-8")
    finalize_evidence(tmp_path, (c1,), (Result("check1", "passed", 0, 0.1, "clean", "passed", None),))

    (tmp_path / "check1.log").unlink()
    with pytest.raises(RuntimeError, match="missing evidence path"):
        verify_evidence(tmp_path, (c1,))


def test_verify_evidence_rejects_unexpected_file(tmp_path: Path) -> None:
    c1 = Check("check1", ("echo", "hello"))
    (tmp_path / "check1.log").write_text("log 1", encoding="utf-8")
    finalize_evidence(tmp_path, (c1,), (Result("check1", "passed", 0, 0.1, "clean", "passed", None),))

    (tmp_path / "unexpected.txt").write_text("rogue", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unexpected evidence path"):
        verify_evidence(tmp_path, (c1,))


def test_verify_evidence_rejects_size_mismatch(tmp_path: Path) -> None:
    c1 = Check("check1", ("echo", "hello"))
    (tmp_path / "check1.log").write_text("log 1", encoding="utf-8")
    finalize_evidence(tmp_path, (c1,), (Result("check1", "passed", 0, 0.1, "clean", "passed", None),))

    (tmp_path / "check1.log").write_text("longer log content", encoding="utf-8")
    with pytest.raises(RuntimeError, match="size mismatch"):
        verify_evidence(tmp_path, (c1,))


def test_verify_evidence_rejects_digest_mismatch(tmp_path: Path) -> None:
    c1 = Check("check1", ("echo", "hello"))
    (tmp_path / "check1.log").write_text("log 1", encoding="utf-8")
    finalize_evidence(tmp_path, (c1,), (Result("check1", "passed", 0, 0.1, "clean", "passed", None),))

    # Same byte size (5 bytes), different content
    (tmp_path / "check1.log").write_text("log 2", encoding="utf-8")
    with pytest.raises(RuntimeError, match="digest mismatch"):
        verify_evidence(tmp_path, (c1,))


def test_verify_evidence_rejects_malformed_manifest(tmp_path: Path) -> None:
    c1 = Check("check1", ("echo", "hello"))
    (tmp_path / "check1.log").write_text("log 1", encoding="utf-8")
    finalize_evidence(tmp_path, (c1,), (Result("check1", "passed", 0, 0.1, "clean", "passed", None),))

    (tmp_path / "manifest.json").write_text("{not json}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="malformed"):
        verify_evidence(tmp_path, (c1,))
