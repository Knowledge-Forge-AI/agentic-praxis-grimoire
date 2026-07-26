"""Unconditional real-boundary tests for ``bin/git-show-report``."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import subprocess
import time

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "git-show-report"


def git(
    repository: Path, *arguments: str, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", os.fspath(repository), *arguments],
        check=True,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def initialize(repository: Path) -> dict[str, str]:
    repository.mkdir()
    git(repository, "init", "-q", "-b", "main")
    git(repository, "config", "user.name", "Report Author")
    git(repository, "config", "user.email", "report@example.invalid")
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_DATE": "2030-01-02T03:04:05+00:00",
            "GIT_COMMITTER_DATE": "2030-01-02T03:04:05+00:00",
        }
    )
    return environment


def commit(
    repository: Path,
    environment: dict[str, str],
    subject: str,
    *,
    body: str | None = None,
    allow_empty: bool = False,
) -> str:
    arguments = ["commit", "-q"]
    if allow_empty:
        arguments.append("--allow-empty")
    arguments.extend(["-m", subject])
    if body is not None:
        arguments.extend(["-m", body])
    git(repository, *arguments, environment=environment)
    return git(repository, "rev-parse", "HEAD").stdout.decode().strip()


def run_report(
    repository: Path,
    report_root: Path,
    *arguments: str,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    environment = os.environ.copy()
    environment["GIT_SHOW_REPORT_ROOT"] = os.fspath(report_root)
    if extra_environment:
        environment.update(extra_environment)
    return subprocess.run(
        [os.fspath(COMMAND), *arguments],
        cwd=repository,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def field(record: bytes, name: bytes) -> bytes:
    values = [line.removeprefix(name + b": ") for line in record.splitlines() if line.startswith(name + b": ")]
    assert values
    return values[-1]


def report_path(report_root: Path, repository: Path, phase: str) -> Path:
    return report_root / repository.name / f"{phase}.report.txt"


def test_root_ordinary_empty_rename_binary_unusual_and_first_parent_merge(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    environment = initialize(repository)
    report_root = tmp_path / "reports"
    (repository / "root.txt").write_text("root\n", encoding="utf-8")
    git(repository, "add", "root.txt")
    root = commit(repository, environment, "root subject", body="root body")
    result = run_report(repository, report_root, "ROOT", root, "", "passed", "gate")
    assert result.returncode == 0, result.stderr.decode()
    root_record = report_path(report_root, repository, "ROOT").read_bytes()
    assert field(root_record, b"ROOT-COMMIT") == b"true"
    assert field(root_record, b"PATCH-MODE") == b"root"
    assert field(root_record, b"STATUS-DOC") == b"NULL"
    assert b"root subject\n\nroot body" in root_record
    assert stat.S_IMODE(report_path(report_root, repository, "ROOT").stat().st_mode) == 0o600
    assert stat.S_IMODE((report_root / repository.name).stat().st_mode) == 0o700

    (repository / "root.txt").write_text("root\nordinary\n", encoding="utf-8")
    git(repository, "add", "root.txt")
    ordinary = commit(repository, environment, "ordinary")
    empty = commit(repository, environment, "empty", allow_empty=True)
    unusual = repository / "unusual name\t.txt"
    unusual.write_text("unusual\n", encoding="utf-8")
    (repository / "binary.bin").write_bytes(b"\x00\x01\x02\xff")
    git(repository, "mv", "root.txt", "renamed.txt")
    git(repository, "add", "--", unusual.name, "binary.bin", "renamed.txt")
    complex_commit = commit(repository, environment, "complex")
    git(repository, "checkout", "-qb", "side", ordinary)
    (repository / "side.txt").write_text("side\n", encoding="utf-8")
    git(repository, "add", "side.txt")
    commit(repository, environment, "side")
    git(repository, "checkout", "-q", "main")
    git(repository, "merge", "--no-ff", "-qm", "merge", "side", environment=environment)
    merge = git(repository, "rev-parse", "HEAD").stdout.decode().strip()

    cases = {
        "ORDINARY": ordinary,
        "EMPTY": empty,
        "COMPLEX": complex_commit,
        "MERGE": merge,
    }
    for phase, revision in cases.items():
        result = run_report(repository, report_root, phase, revision, "status.md", "passed", "gate")
        assert result.returncode == 0, result.stderr.decode()
    ordinary_record = report_path(report_root, repository, "ORDINARY").read_bytes()
    empty_record = report_path(report_root, repository, "EMPTY").read_bytes()
    complex_record = report_path(report_root, repository, "COMPLEX").read_bytes()
    merge_record = report_path(report_root, repository, "MERGE").read_bytes()
    assert field(ordinary_record, b"PATCH-MODE") == b"single-parent"
    assert field(empty_record, b"FILES-CHANGED") == b"0"
    assert field(empty_record, b"PATCH-SHA256") == hashlib.sha256(b"").hexdigest().encode()
    assert field(complex_record, b"FILES-RENAMED") == b"1"
    assert field(complex_record, b"BINARY-FILES") == b"1"
    assert b"unusual name\\t.txt" in complex_record
    assert b"GIT binary patch" not in complex_record
    assert field(merge_record, b"MERGE-COMMIT") == b"true"
    assert field(merge_record, b"PATCH-MODE") == b"first-parent-merge"
    assert b"side.txt" in merge_record


def test_usage_noncommit_and_unsafe_destination_fail_closed(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    environment = initialize(repository)
    (repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    git(repository, "add", "tracked.txt")
    revision = commit(repository, environment, "initial")
    report_root = tmp_path / "reports"
    assert subprocess.run([COMMAND, "--help"], check=False).returncode == 0
    assert subprocess.run([COMMAND], check=False).returncode == 2
    for phase in (".", "..", "../BAD", " leading", "trailing ", "bad\nline"):
        assert run_report(repository, report_root, phase, revision, "status", "passed", "gate").returncode == 2
    blob = git(repository, "hash-object", "-w", "--stdin").stdout.decode().strip()
    assert run_report(repository, report_root, "BLOB", blob, "status", "passed", "gate").returncode == 1
    assert run_report(repository, report_root, "A" + "0" * 128, revision, "status", "passed", "gate").returncode == 2

    destination = report_path(report_root, repository, "UNSAFE")
    destination.parent.mkdir(parents=True, mode=0o700)
    destination.write_text("preserve\n", encoding="utf-8")
    destination.chmod(0o660)
    assert run_report(repository, report_root, "UNSAFE", revision, "status", "passed", "gate").returncode == 1
    assert destination.read_bytes() == b"preserve\n"
    destination.unlink()
    destination.symlink_to(tmp_path / "missing")
    assert run_report(repository, report_root, "UNSAFE", revision, "status", "passed", "gate").returncode == 1


def test_records_are_deterministic_appendable_and_marker_safe(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    environment = initialize(repository)
    marker = repository / "markers.txt"
    marker.write_text(
        "BEGIN AGENT-REPORT-RECORD\nEND AGENT-REPORT-RECORD\nBEGIN PATCH\nEND PATCH\n",
        encoding="utf-8",
    )
    git(repository, "add", marker.name)
    first = commit(
        repository,
        environment,
        "BEGIN AGENT-REPORT-RECORD",
        body="END AGENT-REPORT-RECORD\nBEGIN PATCH\nEND PATCH",
    )
    report_root = tmp_path / "reports"
    result = run_report(repository, report_root, "DETERMINISTIC", first, "status", "passed", "gate")
    assert result.returncode == 0
    destination = report_path(report_root, repository, "DETERMINISTIC")
    first_bytes = destination.read_bytes()
    destination.unlink()
    assert run_report(repository, report_root, "DETERMINISTIC", first, "status", "passed", "gate").returncode == 0
    assert destination.read_bytes() == first_bytes
    assert first_bytes.count(b"\nBEGIN AGENT-REPORT-RECORD\n") == 2
    assert field(first_bytes, b"RECORD-COMPLETE") == b"true"

    (repository / "second.txt").write_text("second\n", encoding="utf-8")
    git(repository, "add", "second.txt")
    second = commit(repository, environment, "second")
    for revision in (first, second):
        assert run_report(repository, report_root, "APPEND", revision, "status", "passed", "gate").returncode == 0
    appended = report_path(report_root, repository, "APPEND").read_bytes()
    assert appended.count(b"ENVELOPE-FORMAT: agent-report-record\n") == 4
    assert appended.count(b"RECORD-COMPLETE: true\n") == 2


def test_generation_failures_preserve_destination_and_cleanup(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    environment = initialize(repository)
    (repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    git(repository, "add", "tracked.txt")
    revision = commit(repository, environment, "initial")
    report_root = tmp_path / "reports"
    destination = report_path(report_root, repository, "FAILURE")
    destination.parent.mkdir(parents=True, mode=0o700)
    destination.write_bytes(b"existing evidence\n")
    destination.chmod(0o600)
    for step in (
        "metadata",
        "changed-files",
        "numstat",
        "commit-message",
        "patch",
        "record-assembly",
        "before-destination-replacement",
    ):
        result = run_report(
            repository,
            report_root,
            "FAILURE",
            revision,
            "status",
            "passed",
            "gate",
            extra_environment={
                "GIT_SHOW_REPORT_TESTING": "1",
                "GIT_SHOW_REPORT_TEST_FAIL_STEP": step,
            },
        )
        assert result.returncode == 1
        assert destination.read_bytes() == b"existing evidence\n"
        assert not destination.with_name(destination.name + ".lock").exists()
        assert not list(destination.parent.glob(".FAILURE.report.*"))


def test_concurrent_append_and_released_lock_are_complete(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    environment = initialize(repository)
    (repository / "tracked.txt").write_text("first\n", encoding="utf-8")
    git(repository, "add", "tracked.txt")
    first = commit(repository, environment, "first")
    (repository / "tracked.txt").write_text("second\n", encoding="utf-8")
    git(repository, "add", "tracked.txt")
    second = commit(repository, environment, "second")
    report_root = tmp_path / "reports"
    process_environment = os.environ | {"GIT_SHOW_REPORT_ROOT": os.fspath(report_root)}
    processes = [
        subprocess.Popen(
            [COMMAND, "CONCURRENT", revision, "status", "passed", "gate"],
            cwd=repository,
            env=process_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for revision in (first, second)
    ]
    assert [process.wait() for process in processes] == [0, 0]
    concurrent = report_path(report_root, repository, "CONCURRENT").read_bytes()
    assert concurrent.count(b"RECORD-COMPLETE: true\n") == 2

    released = report_path(report_root, repository, "RELEASED")
    lock = released.with_name(released.name + ".lock")
    lock.mkdir(parents=True, mode=0o700)
    process = subprocess.Popen(
        [COMMAND, "RELEASED", second, "status", "passed", "gate"],
        cwd=repository,
        env=process_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(0.05)
    assert process.poll() is None
    lock.rmdir()
    stdout, stderr = process.communicate(timeout=10)
    assert process.returncode == 0, (stdout + stderr).decode()
    assert field(released.read_bytes(), b"RECORD-COMPLETE") == b"true"
    assert not lock.exists()
