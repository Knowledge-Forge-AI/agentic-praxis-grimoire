"""Unit contracts for report path, source, lock, and replacement safety."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from agent_report import models, rendering, safety  # noqa: E402


def record(identifier: str = "TEST-RECORD") -> bytes:
    return rendering.build_record(
        models.ReportRecord(
            "test-report",
            1,
            identifier,
            "project",
            "APG28A",
            b"payload\n",
        )
    )


def test_ticket_metadata_and_status_document_validation_are_strict() -> None:
    assert safety.validate_ticket("APG28A") == "APG28A"
    assert safety.header_value("") == "NULL"
    assert safety.header_value("value") == "value"
    assert safety.validate_status_doc(None) == "NONE"
    assert safety.validate_status_doc("docs/status/exit.md") == "docs/status/exit.md"
    for value in ("", "/absolute", "a//b", "a/./b", "a/../b", "a\\b"):
        with pytest.raises(safety.UsageError):
            safety.validate_status_doc(value)
    for value in (".", "..", "bad value", "x" * 129):
        with pytest.raises(safety.UsageError, match="ticket"):
            safety.validate_ticket(value)
    with pytest.raises(safety.UsageError, match="control"):
        safety.validate_metadata("bad\nvalue")


def test_source_validation_and_read_preserve_exact_private_bytes(tmp_path: Path) -> None:
    path = tmp_path / "source"
    path.write_bytes(b"evidence\n")
    path.chmod(0o600)
    metadata = safety.validate_source_path(path, source_value=str(path))
    assert safety.read_validated_source(path, metadata, max_bytes=32) == b"evidence\n"
    with pytest.raises(safety.ReportError, match="oversized"):
        safety.read_validated_source(path, metadata, max_bytes=3)
    with pytest.raises(safety.ReportError, match="destination"):
        safety.validate_source_path(path, destination=path)
    with pytest.raises(safety.ReportError, match="unsafe"):
        safety.validate_source_path(path, source_value=str(path) + os.sep)
    path.chmod(0o644)
    with pytest.raises(safety.ReportError, match="permissions"):
        safety.validate_source_path(path)
    path.unlink()
    path.mkdir()
    with pytest.raises(safety.ReportError, match="unsafe"):
        safety.validate_source_path(path)


def test_injected_failure_and_pause_hooks_are_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AGENT_REPORT_TESTING", raising=False)
    safety.injected_failure("step")
    safety.testing_pause("step")
    monkeypatch.setenv("AGENT_REPORT_TESTING", "1")
    monkeypatch.setenv("AGENT_REPORT_TEST_FAIL_STEP", "step")
    with pytest.raises(safety.ReportError, match="injected"):
        safety.injected_failure("step")
    monkeypatch.delenv("AGENT_REPORT_TEST_FAIL_STEP")
    monkeypatch.setenv("AGENT_REPORT_TEST_PAUSE_STEP", "step")
    with pytest.raises(safety.ReportError, match="signal directory"):
        safety.testing_pause("step")
    monkeypatch.setenv("AGENT_REPORT_TEST_SIGNAL_DIR", str(tmp_path))
    (tmp_path / "continue").touch()
    safety.testing_pause("step")
    assert (tmp_path / "ready").exists()


def test_private_temporary_directory_is_private_and_removed() -> None:
    with safety.private_temporary_directory("test-command") as path:
        assert path.is_dir() and stat.S_IMODE(path.stat().st_mode) == 0o700
        retained = path
    assert not retained.exists()


def test_destination_append_preserves_existing_records_and_builder_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(tmp_path / "reports"))
    destination = safety.Destination(tmp_path / "project", "APG28A")
    first = record("TEST-ONE")
    assert destination.append(first) == first
    observed: list[int] = []

    def builder(existing: bytes, records: tuple[models.ParsedRecord, ...]) -> bytes:
        assert existing == first
        observed.append(len(records))
        return record("TEST-TWO")

    destination.append(builder)
    assert observed == [1]
    parsed = rendering.parse_canonical_records(destination.path.read_bytes())
    assert [item.record.record_id for item in parsed] == ["TEST-ONE", "TEST-TWO"]
    assert stat.S_IMODE(destination.path.stat().st_mode) == 0o600
    assert not destination.lock_path.exists()


def test_destination_rejects_invalid_records_and_unsafe_existing_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(tmp_path / "reports"))
    destination = safety.Destination(tmp_path / "project", "APG28A")
    with pytest.raises(safety.ReportError, match="envelope"):
        destination.append(b"not a record\n")
    destination.path.mkdir()
    with pytest.raises(safety.ReportError, match="unsafe"):
        destination._read_existing()


def test_destination_lock_refuses_unsafe_or_contended_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(tmp_path / "reports"))
    destination = safety.Destination(tmp_path / "project", "APG28A")
    destination.lock_path.write_text("unsafe")
    with pytest.raises(safety.ReportError, match="lock is unsafe"):
        with destination.lock():
            pass


def test_private_directory_and_fsync_helpers_fail_closed(tmp_path: Path) -> None:
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    safety._validate_private_directory(directory)
    directory.chmod(0o755)
    with pytest.raises(safety.ReportError, match="unsafe"):
        safety._validate_private_directory(directory)
    safety._fsync_directory(tmp_path / "missing")
    assert not safety._is_windows_reparse(os.stat_result((0,) * 10))
