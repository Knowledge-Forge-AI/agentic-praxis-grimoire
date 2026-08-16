"""Migrated real-boundary tests for append-operational-report."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))
from agent_report import safety  # noqa: E402

COMMAND = REPOSITORY_ROOT / "bin" / "append-operational-report"


def initialize_repository(path: Path) -> str:
    path.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "APG Test"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "apg@example.invalid"],
        check=True,
    )
    (path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-q", "-m", "initial"], check=True)
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def run_command(
    repository: Path, report_root: Path, *arguments: str
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["GIT_SHOW_REPORT_ROOT"] = os.fspath(report_root)
    return subprocess.run(
        [os.fspath(COMMAND), *arguments],
        cwd=repository,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_operational_report_preserves_source_and_writes_private_complete_record(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    commit = initialize_repository(repository)
    report_root = tmp_path / "reports"
    source = tmp_path / "operational.txt"
    body = (
        "REPORT\n"
        "report_schema: operational-report-v1\n"
        "phase: APG28-TEST\n"
        "outcome: passed\n"
        f"primary_commit: {commit}"
    ).encode()
    source.write_bytes(body)
    source.chmod(0o600)

    result = run_command(
        repository,
        report_root,
        "APG28-TEST",
        os.fspath(source),
        "passed",
        "pytest",
    )

    assert result.returncode == 0, result.stderr.decode()
    assert source.read_bytes() == body
    destination = report_root / "repository" / "APG28-TEST.report.txt"
    record = destination.read_bytes()
    digest = hashlib.sha256(body).hexdigest().encode()
    assert b"RECORD-TYPE: operational-report\n" in record
    assert b"RECORD-COMPLETE: true\n" in record
    assert b"SOURCE-PAYLOAD-SHA256: " + digest + b"\n" in record
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert stat.S_IMODE(destination.parent.stat().st_mode) == 0o700


def test_default_outbox_writes_ops_only_primary_without_legacy_override(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    initialize_repository(repository)
    home = tmp_path / "home"
    source = tmp_path / "operational-default.txt"
    body = (
        "REPORT\n"
        "report_schema: operational-report-v1\n"
        "phase: APG82-OPS\n"
        "outcome: passed\n"
    ).encode()
    source.write_bytes(body)
    source.chmod(0o600)
    environment = os.environ.copy()
    environment.pop("GIT_SHOW_REPORT_ROOT", None)
    environment["HOME"] = os.fspath(home)
    result = subprocess.run(
        [
            os.fspath(COMMAND),
            "APG82-OPS",
            os.fspath(source),
            "passed",
            "pytest",
        ],
        cwd=repository,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode == 0, result.stderr.decode()
    phase_directory = home / "Documents" / "agent" / "outbox" / "repository" / "APG82-OPS"
    destination = phase_directory / "APG82-OPS.ops.report.txt"
    assert destination.exists()
    assert b"RECORD-TYPE: operational-report\n" in destination.read_bytes()
    assert stat.S_IMODE(phase_directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert not (phase_directory / "APG82-OPS.git.show.report.txt").exists()
    assert not (phase_directory / "APG82-OPS.git.diff.report.txt").exists()


def test_operational_report_rejects_symlink_source_without_destination(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    commit = initialize_repository(repository)
    target = tmp_path / "target.txt"
    target.write_text("private evidence\n", encoding="utf-8")
    target.chmod(0o600)
    source = tmp_path / "source-link"
    source.symlink_to(target)
    report_root = tmp_path / "reports"

    result = run_command(
        repository, report_root, "APG28-TEST", os.fspath(source), "passed", "pytest"
    )

    assert result.returncode == 1
    assert b"source operational report" in result.stderr
    assert not list(report_root.rglob("*.report.txt"))


def test_report_field_validators_cover_safe_and_rejected_forms() -> None:
    assert safety.header_value("") == "NULL"
    assert safety.header_value("value") == "value"
    assert safety.validate_ticket("APG28-A.1") == "APG28-A.1"
    for value in (".", "..", "bad/value", "x" * 129):
        with pytest.raises(safety.UsageError, match="ticket id is unsafe"):
            safety.validate_ticket(value)
    assert safety.validate_metadata("clean") == "clean"
    with pytest.raises(safety.UsageError, match="control character"):
        safety.validate_metadata("bad\nvalue", "field")
    assert safety.validate_status_doc(None) == "NONE"
    assert safety.validate_status_doc("docs/status/record.md") == "docs/status/record.md"
    for value in ("", "/absolute", "docs//record.md", "docs/../record.md", "docs\\record.md"):
        with pytest.raises(safety.UsageError):
            safety.validate_status_doc(value)


def test_source_validation_and_reading_enforce_real_posix_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_bytes(b"payload")
    source.chmod(0o600)
    expected = safety.validate_source_path(source.resolve())
    assert safety.read_validated_source(source.resolve(), expected, max_bytes=7) == b"payload"
    with pytest.raises(safety.ReportError, match="oversized"):
        safety.read_validated_source(source.resolve(), expected, max_bytes=6)
    with pytest.raises(safety.UsageError, match="must be absolute"):
        safety.validate_source_path(Path("relative"))
    with pytest.raises(safety.ReportError, match="destination report"):
        safety.validate_source_path(source.resolve(), source.resolve())
    with pytest.raises(safety.ReportError, match="unsafe"):
        safety.validate_source_path(tmp_path / "missing")
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(safety.ReportError, match="unsafe"):
        safety.validate_source_path(directory.resolve())
    source.chmod(0o644)
    with pytest.raises(safety.ReportError, match="permissions"):
        safety.validate_source_path(source.resolve())
    source.chmod(0o600)
    hard_link = tmp_path / "hard-link"
    os.link(source, hard_link)
    with pytest.raises(safety.ReportError, match="hard links"):
        safety.validate_source_path(source.resolve())


def test_source_spelling_and_injected_failure_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="utf-8")
    source.chmod(0o600)
    with pytest.raises(safety.ReportError, match="unsafe"):
        safety.validate_source_path(source.resolve(), source_value=str(source) + os.sep)
    safety.injected_failure("boundary")
    monkeypatch.setenv("AGENT_REPORT_TESTING", "1")
    monkeypatch.setenv("AGENT_REPORT_TEST_FAIL_STEP", "boundary")
    with pytest.raises(safety.ReportError, match="injected failure"):
        safety.injected_failure("boundary")
    monkeypatch.delenv("AGENT_REPORT_TEST_FAIL_STEP")
    monkeypatch.setenv("AGENT_REPORT_TEST_PAUSE_STEP", "boundary")
    with pytest.raises(safety.ReportError, match="signal directory"):
        safety.testing_pause("boundary")


def test_private_temporary_directory_and_directory_validation(tmp_path: Path) -> None:
    with safety.private_temporary_directory("apg-boundary") as directory:
        assert directory.is_dir()
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
        retained = directory
    assert not retained.exists()
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    safety._validate_private_directory(private)
    private.chmod(0o755)
    with pytest.raises(safety.ReportError, match="unsafe"):
        safety._validate_private_directory(private)
    plain = tmp_path / "plain"
    plain.write_text("file", encoding="utf-8")
    with pytest.raises(safety.ReportError, match="unsafe"):
        safety._validate_private_directory(plain)


def test_destination_lock_lifecycle_and_existing_file_safety(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_root = tmp_path / "reports"
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(report_root))
    destination = safety.Destination(tmp_path / "repository", "APG28-LOCK")
    destination._release_lock()
    with destination.lock():
        assert destination._locked
        assert destination.lock_path.is_dir()
    assert not destination.lock_path.exists()
    assert destination._read_existing() == b""
    destination.path.write_bytes(b"existing")
    destination.path.chmod(0o600)
    assert destination._read_existing() == b"existing"
    destination.path.chmod(0o644)
    with pytest.raises(safety.ReportError, match="existing report file is unsafe"):
        destination._read_existing()
    destination.path.unlink()
    destination.path.mkdir()
    with pytest.raises(safety.ReportError, match="existing report file is unsafe"):
        destination._read_existing()


def test_destination_rejects_unsafe_directory_and_lock_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_root = tmp_path / "reports"
    project_directory = report_root / "repository"
    report_root.mkdir(mode=0o700)
    target = tmp_path / "target"
    target.mkdir()
    project_directory.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(report_root))
    with pytest.raises(safety.ReportError, match="report directory is unsafe"):
        safety.Destination(tmp_path / "repository", "APG28-LOCK")
    project_directory.unlink()
    destination = safety.Destination(tmp_path / "repository", "APG28-LOCK")
    destination.lock_path.write_text("not a directory", encoding="utf-8")
    with pytest.raises(safety.ReportError, match="append lock is unsafe"):
        with destination.lock():
            pass


def test_destination_release_preserves_changed_owner_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(tmp_path / "reports"))
    destination = safety.Destination(tmp_path / "repository", "APG28-LOCK")
    with destination.lock():
        owner = destination.lock_path / "owner"
        owner.unlink()
        owner.write_text("foreign\n", encoding="utf-8")
        owner.chmod(0o600)
    assert destination.lock_path.is_dir()
    owner.unlink()
    destination.lock_path.rmdir()


def test_destination_release_removes_lock_when_owner_disappears(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(tmp_path / "reports"))
    destination = safety.Destination(tmp_path / "repository", "APG28-LOCK")
    with destination.lock():
        (destination.lock_path / "owner").unlink()
    assert not destination.lock_path.exists()


def test_real_cli_rejects_empty_oversized_and_unclean_sources(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    initialize_repository(repository)
    report_root = tmp_path / "reports"
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    empty.chmod(0o600)
    result = run_command(
        repository,
        report_root,
        "APG28-TEST",
        os.fspath(empty),
        "passed",
        "pytest",
    )
    assert result.returncode == 1
    assert b"empty" in result.stderr

    oversized = tmp_path / "oversized.txt"
    oversized.write_bytes(b"x" * (safety.MAX_SOURCE_BYTES + 1))
    oversized.chmod(0o600)
    result = run_command(
        repository,
        report_root,
        "APG28-TEST",
        os.fspath(oversized),
        "passed",
        "pytest",
    )
    assert result.returncode == 1
    assert b"oversized" in result.stderr

    unclean = os.fspath(tmp_path / "missing" / ".." / "source.txt")
    result = run_command(
        repository,
        report_root,
        "APG28-TEST",
        unclean,
        "passed",
        "pytest",
    )
    assert result.returncode == 2


def test_real_cli_rejects_incomplete_duplicate_and_unknown_relation_options(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    initialize_repository(repository)
    report_root = tmp_path / "reports"
    source = tmp_path / "source.txt"
    source.write_text("body\n", encoding="utf-8")
    source.chmod(0o600)
    base = (
        "APG28-TEST",
        os.fspath(source),
        "passed",
        "pytest",
    )
    for extra in (
        ("--related-commit",),
        ("--related-git-report-id",),
        ("--unknown", "value"),
        ("--related-commit", "abcdef0", "--related-commit", "abcdef1"),
        ("--related-git-report-id", "GIT-SHOW-REPORT-" + "a" * 40, "--related-git-report-id", "GIT-SHOW-REPORT-" + "b" * 40),
    ):
        result = run_command(repository, report_root, *base, *extra)
        assert result.returncode == 2


def test_real_cli_rejects_invalid_relation_combinations_and_resolution(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    commit = initialize_repository(repository)
    report_root = tmp_path / "reports"
    source = tmp_path / "source.txt"
    source.write_text("body\n", encoding="utf-8")
    source.chmod(0o600)
    base = ("APG28-TEST", os.fspath(source), "passed", "pytest")
    show_id = "GIT-SHOW-REPORT-" + "0" * 40
    diff_id = "GIT-DIFF-REPORT-" + "0" * 64

    relative = run_command(
        repository,
        report_root,
        "APG28-TEST",
        source.name,
        "passed",
        "pytest",
    )
    commit_without_report = run_command(
        repository,
        report_root,
        *base,
        "--related-commit",
        "0" * 40,
    )
    commit_with_diff = run_command(
        repository,
        report_root,
        *base,
        "--related-commit",
        "0" * 40,
        "--related-git-report-id",
        diff_id,
    )
    unresolved = run_command(
        repository,
        report_root,
        *base,
        "--related-commit",
        "0" * 40,
        "--related-git-report-id",
        show_id,
    )
    conflicting = run_command(
        repository,
        report_root,
        *base,
        "--related-commit",
        commit,
        "--related-git-report-id",
        "GIT-SHOW-REPORT-" + "f" * 40,
    )

    assert relative.returncode == 2
    assert commit_without_report.returncode == 2
    assert commit_with_diff.returncode == 2
    assert unresolved.returncode == 2
    assert b"does not resolve" in unresolved.stderr
    assert conflicting.returncode == 2
    assert b"conflict" in conflicting.stderr


def test_real_cli_outside_git_repository_reports_bounded_discovery_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.txt"
    source.write_text("body\n", encoding="utf-8")
    source.chmod(0o600)
    result = run_command(
        tmp_path,
        tmp_path / "reports",
        "APG28-TEST",
        os.fspath(source),
        "passed",
        "pytest",
    )
    assert result.returncode == 1
    assert b"not inside a git repository" in result.stderr
