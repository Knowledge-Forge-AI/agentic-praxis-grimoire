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


@pytest.mark.parametrize(
    ("basename", "expected"),
    [
        ("repo", "repo"),
        (".repo", "repo"),
        ("..repo", "repo"),
        ("...repo", "repo"),
        ("repo.dev", "repo.dev"),
        (".repo.dev", "repo.dev"),
        ("repo.", "repo."),
        ("repo with space", "repo with space"),
        (".répertoire", "répertoire"),
    ],
)
def test_project_name_removes_only_leading_ascii_periods(
    basename: str, expected: str
) -> None:
    assert safety.infer_project_name(Path("/workspace") / basename) == expected


@pytest.mark.parametrize("basename", [".", "..", "..."])
def test_project_name_rejects_an_all_dot_basename(basename: str) -> None:
    with pytest.raises(safety.ReportError, match="empty"):
        safety.infer_project_name(Path(basename))


def test_destination_uses_new_default_and_preserves_exact_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    default = safety.Destination(tmp_path / ".project", "APG53")
    assert default.project == "project"
    assert default.root == tmp_path / "home" / "Documents" / "agent" / "outbox"
    assert default.directory == default.root / "project" / "APG53"
    assert default.path == default.directory / "APG53.ops.report.txt"
    assert stat.S_IMODE(default.root.stat().st_mode) == 0o700
    assert stat.S_IMODE(default.directory.stat().st_mode) == 0o700

    explicit = tmp_path / "explicit"
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(explicit))
    overridden = safety.Destination(tmp_path / "..project", "APG53")
    assert overridden.root == explicit
    assert overridden.path == explicit / "project" / "APG53.report.txt"
    assert "reports" not in overridden.path.relative_to(explicit).parts

    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT")
    parameterized = safety.Destination(
        tmp_path / "project", "APG53", outbox_root=tmp_path / "parameterized"
    )
    assert parameterized.root == tmp_path / "parameterized"


def test_destination_rejects_symlinked_default_reports_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    agent_root = home / "Documents" / "agent"
    agent_root.mkdir(parents=True)
    redirected = tmp_path / "redirected"
    redirected.mkdir(mode=0o700)
    (agent_root / "outbox").symlink_to(redirected, target_is_directory=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    with pytest.raises(safety.ReportError, match="report root is unsafe"):
        safety.Destination(tmp_path / "project", "APG53")


def test_destination_supersedes_current_primary_and_keeps_operations_with_git(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    destination = safety.Destination(tmp_path / "project", "APG53")
    show = rendering.build_record(
        models.ReportRecord(
            "git-show-report", 2, "GIT-SHOW-REPORT-" + "a" * 40, "project", "APG53", b"show\n"
        )
    )
    diff = rendering.build_record(
        models.ReportRecord(
            "git-diff-report", 1, "GIT-DIFF-REPORT-" + "b" * 64, "project", "APG53", b"diff\n"
        )
    )
    operational = rendering.build_record(
        models.ReportRecord(
            "operational-report", 1, "OPERATIONAL-REPORT-" + "c" * 64, "project", "APG53", b"ops\n"
        )
    )

    destination.append(show)
    show_path = destination.directory / "APG53.git.show.report.txt"
    diff_path = destination.directory / "APG53.git.diff.report.txt"
    ops_path = destination.directory / "APG53.ops.report.txt"
    assert show_path.exists()
    assert not diff_path.exists()
    assert not ops_path.exists()

    destination.append(operational)
    assert [item.record.record_type for item in rendering.parse_canonical_records(show_path.read_bytes())] == [
        "git-show-report",
        "operational-report",
    ]
    assert not ops_path.exists()

    destination.append(diff)
    assert not show_path.exists()
    assert diff_path.exists()
    assert not ops_path.exists()


def test_destination_rejects_simultaneous_git_and_ops_primaries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    destination = safety.Destination(tmp_path / "project", "APG53")
    show_path = destination.directory / "APG53.git.show.report.txt"
    ops_path = destination.directory / "APG53.ops.report.txt"
    show_path.write_bytes(record("GIT-SHOW-REPORT-" + "a" * 40))
    ops_path.write_bytes(record("OPERATIONAL-REPORT-" + "b" * 64))
    show_path.chmod(0o600)
    ops_path.chmod(0o600)

    with pytest.raises(safety.ReportError, match="multiple current primary"):
        destination._current_path()


def test_destination_refuses_unresolved_transaction_and_can_recover_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    destination = safety.Destination(tmp_path / "project", "APG53")
    destination.transaction_path.write_text(
        "agent-report-transaction-v1\n"
        "phase: APG53\n"
        "target: APG53.git.show.report.txt\n"
        "stale: APG53.git.diff.report.txt,APG53.ops.report.txt\n"
        "token: interrupted\n",
        encoding="utf-8",
    )
    destination.transaction_path.chmod(0o600)
    with pytest.raises(safety.ReportError, match="transaction"):
        destination._read_existing()
    assert destination.recover_transaction() is True
    assert not destination.transaction_path.exists()
    assert destination._read_existing() == b""


def test_destination_failure_retains_recoverable_outbox_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    monkeypatch.setenv("AGENT_REPORT_TESTING", "1")
    monkeypatch.setenv("AGENT_REPORT_TEST_FAIL_STEP", "before-destination-replacement")
    destination = safety.Destination(tmp_path / "project", "APG53")
    show = rendering.build_record(
        models.ReportRecord(
            "git-show-report", 2, "GIT-SHOW-REPORT-" + "a" * 40, "project", "APG53", b"show\n"
        )
    )
    with pytest.raises(safety.ReportError, match="injected failure"):
        destination.append(show)
    assert destination.transaction_path.exists()
    assert destination.primary_paths[0].exists() is False
    assert destination.recover_transaction() is True
    assert not destination.transaction_path.exists()


def test_recovery_completes_post_publication_stale_primary_removal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    destination = safety.Destination(tmp_path / "project", "APG53")
    ops = rendering.build_record(
        models.ReportRecord(
            "operational-report", 1, "OPERATIONAL-REPORT-" + "b" * 64,
            "project", "APG53", b"ops\n"
        )
    )
    destination.append(ops)
    show = rendering.build_record(
        models.ReportRecord(
            "git-show-report", 2, "GIT-SHOW-REPORT-" + "a" * 40,
            "project", "APG53", b"show\n"
        )
    )
    original = destination._unlink_stale
    calls = 0

    def fail_once(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise safety.ReportError("injected stale removal failure")
        original(path)

    monkeypatch.setattr(destination, "_unlink_stale", fail_once)
    with pytest.raises(safety.ReportError, match="stale removal"):
        destination.append(show)
    assert destination.transaction_path.exists()
    assert destination.primary_paths[0].exists()
    assert destination.primary_paths[2].exists()
    monkeypatch.setattr(destination, "_unlink_stale", original)
    assert destination.recover_transaction() is True
    assert destination.primary_paths[0].exists()
    assert not destination.primary_paths[2].exists()


def test_lock_recovers_owner_proven_dead_process_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    destination = safety.Destination(tmp_path / "project", "APG53")
    destination.lock_path.mkdir(mode=0o700)
    owner = destination.lock_path / "owner"
    owner.write_text("99999999-dead-owner-APG53\n", encoding="ascii")
    owner.chmod(0o600)

    with destination.lock():
        assert destination.lock_path.is_dir()

    assert not destination.lock_path.exists()


def test_lock_recovers_ownerless_interrupted_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("GIT_SHOW_REPORT_ROOT", raising=False)
    monkeypatch.delenv("APGR_OUTBOX_ROOT", raising=False)
    destination = safety.Destination(tmp_path / "project", "APG53")
    destination.lock_path.mkdir(mode=0o700)
    monkeypatch.setattr(safety.time, "time", lambda: 10_000_000_000.0)
    monkeypatch.setattr(
        safety.time, "sleep", lambda _seconds: None
    )

    with destination.lock():
        assert destination.lock_path.is_dir()

    assert not destination.lock_path.exists()


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
