"""Integration tests for APGR canonical report routing and verification."""

from __future__ import annotations

import hashlib
import importlib
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, os.fspath(ROOT / "src"))

cli = importlib.import_module("agentic_praxis_grimoire.cli")
reports = importlib.import_module("agentic_praxis_grimoire.reports")
PERSISTED_DIR = ROOT / "report" / "testdata" / "persisted"


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=APG Test", "-c", "user.email=test@example.invalid", *arguments],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_canonical_diff_route_publishes_under_explicit_outbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "synthetic"
    repository.mkdir()
    _git(repository, "init", "-q")
    tracked = repository / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt")
    _git(repository, "commit", "-qm", "base")
    tracked.write_text("changed\n", encoding="utf-8")
    outbox = tmp_path / "outbox"
    legacy = tmp_path / "legacy"
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(legacy))

    result = cli.main(
        [
            "--project-root", str(repository),
            "--outbox-root", str(outbox),
            "report", "diff", "APG82", "blocked", "focused-gate",
        ]
    )

    assert result == 0
    artifact = outbox / "synthetic" / "APG82" / "APG82.git.diff.report.txt"
    assert artifact.is_file()
    assert stat.S_IMODE(artifact.stat().st_mode) == 0o600
    assert b"GIT-DIFF-REPORT" in artifact.read_bytes()
    assert not legacy.exists()


def test_canonical_recover_route_resolves_retained_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "synthetic"
    repository.mkdir()
    _git(repository, "init", "-q")
    tracked = repository / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    _git(repository, "add", "tracked.txt")
    _git(repository, "commit", "-qm", "base")
    tracked.write_text("changed\n", encoding="utf-8")
    outbox = tmp_path / "outbox"
    monkeypatch.setenv("GIT_SHOW_REPORT_ROOT", str(tmp_path / "legacy"))

    assert cli.main(
        [
            "--project-root", str(repository), "--outbox-root", str(outbox),
            "report", "diff", "APG82", "blocked", "focused-gate",
        ]
    ) == 0
    phase_dir = outbox / "synthetic" / "APG82"
    marker = phase_dir / ".phase.transaction"
    marker.write_text(
        "agent-report-transaction-v1\n"
        "phase: APG82\n"
        "target: APG82.git.diff.report.txt\n"
        "stale: APG82.git.show.report.txt,APG82.ops.report.txt\n"
        "token: interrupted\n",
        encoding="utf-8",
    )
    marker.chmod(0o600)

    assert cli.main(
        [
            "--project-root", str(repository), "--outbox-root", str(outbox),
            "report", "recover", "--phase", "APG82",
        ]
    ) == 0
    assert not marker.exists()
    assert (phase_dir / "APG82.git.diff.report.txt").is_file()


def test_source_checkout_bridge_runs_without_binary_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("APGR_GO_BINARY", raising=False)
    monkeypatch.chdir(tmp_path)
    result = cli.main(
        [
            "--project", "synthetic", "--outbox-root", str(tmp_path),
            "report", "path", "--phase", "APG96", "--kind", "ops",
        ]
    )
    assert result == 0
    assert capfd.readouterr().out.strip() == str(
        tmp_path / "synthetic" / "APG96" / "APG96.ops.report.txt"
    )


def _discover_persisted_fixtures() -> list[Path]:
    if not PERSISTED_DIR.is_dir():
        return []
    fixtures = sorted(
        path for path in PERSISTED_DIR.iterdir()
        if path.is_file() and path.suffix == ".txt" and path.name != "README.md"
    )
    return fixtures


def test_report_verify_route_and_subprocess_succeeds_without_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    fixtures = _discover_persisted_fixtures()
    assert len(fixtures) > 0, f"Expected persisted fixtures in {PERSISTED_DIR}"

    # Verify outside any git worktree and without --project or --outbox-root
    monkeypatch.chdir(tmp_path)

    for fixture in fixtures:
        stat_before = fixture.stat()
        bytes_before = fixture.read_bytes()

        # In-process execution through cli.main
        exit_code = cli.main(["report", "verify", str(fixture)])
        assert exit_code == 0, f"cli.main report verify failed on {fixture.name}"
        captured = capfd.readouterr()
        assert "verified" in captured.out
        assert "record" in captured.out
        assert captured.err == ""

        # Verify input was not mutated
        stat_after = fixture.stat()
        assert stat_after.st_size == stat_before.st_size
        assert stat_after.st_mtime_ns == stat_before.st_mtime_ns
        assert stat_after.st_mode == stat_before.st_mode
        assert fixture.read_bytes() == bytes_before

        # Cross-process execution through Python module
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            (os.fspath(ROOT / "src"), os.fspath(ROOT), *[p for p in sys.path if p])
        )
        child = subprocess.run(
            [sys.executable, "-m", "agentic_praxis_grimoire", "report", "verify", str(fixture)],
            cwd=tmp_path,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        assert child.returncode == 0, f"child report verify failed: {child.stderr}"
        assert "verified" in child.stdout
        assert "record" in child.stdout

        # Verify through direct bin/apgr checkout launcher
        apgr_bin = ROOT / "bin" / "apgr"
        if apgr_bin.is_file() and os.access(apgr_bin, os.X_OK):
            launcher_run = subprocess.run(
                [os.fspath(apgr_bin), "report", "verify", str(fixture)],
                cwd=tmp_path,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            assert launcher_run.returncode == 0, f"bin/apgr verify failed: {launcher_run.stderr}"
            assert "verified" in launcher_run.stdout


def test_report_verify_distinct_error_classes_without_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)

    # 1. Empty report file: exit 1, distinct empty diagnosis
    empty_file = tmp_path / "empty.report.txt"
    empty_file.write_bytes(b"")
    result = cli.main(["report", "verify", str(empty_file)])
    assert result == 1
    empty_err = capfd.readouterr().err
    assert "empty report" in empty_err
    assert "apgr:" in empty_err

    # Whitespace-only report file is also empty report
    whitespace_file = tmp_path / "whitespace.report.txt"
    whitespace_file.write_bytes(b"   \n\t\n  \n")
    result = cli.main(["report", "verify", str(whitespace_file)])
    assert result == 1
    ws_err = capfd.readouterr().err
    assert "empty report" in ws_err

    # 2. Malformed framing: exit 1, distinct framing/compatibility error
    malformed_file = tmp_path / "malformed.report.txt"
    malformed_file.write_bytes(b"not a valid envelope line\nBEGIN AGENT-REPORT-RECORD\n")
    result = cli.main(["report", "verify", str(malformed_file)])
    assert result == 1
    malformed_err = capfd.readouterr().err
    assert "empty report" not in malformed_err
    assert "apgr:" in malformed_err

    # 3. Unsupported record kind: exit 1
    unsupported_file = tmp_path / "unsupported.report.txt"
    line = b"=" * 80 + b"\n"
    unsupported_payload = b"test payload\n"
    sha = hashlib.sha256(unsupported_payload).hexdigest().encode()
    unsupported_content = (
        line
        + b"BEGIN AGENT-REPORT-RECORD\n"
        + b"ENVELOPE-FORMAT: agent-report-record\n"
        + b"ENVELOPE-VERSION: 1\n"
        + b"RECORD-TYPE: UNKNOWN-FUTURE-RECORD\n"
        + b"RECORD-FORMAT-VERSION: 1\n"
        + b"RECORD-ID: RECORD-1\n"
        + b"PROJECT: synthetic\n"
        + b"PHASE: APG127\n"
        + b"PAYLOAD-SHA256: " + sha + b"\n"
        + b"PAYLOAD-SIZE-BYTES: " + str(len(unsupported_payload)).encode() + b"\n"
        + line
        + unsupported_payload
        + line
        + b"END AGENT-REPORT-RECORD\n"
        + b"ENVELOPE-FORMAT: agent-report-record\n"
        + b"ENVELOPE-VERSION: 1\n"
        + b"RECORD-TYPE: UNKNOWN-FUTURE-RECORD\n"
        + b"RECORD-FORMAT-VERSION: 1\n"
        + b"RECORD-ID: RECORD-1\n"
        + b"PROJECT: synthetic\n"
        + b"PHASE: APG127\n"
        + b"RECORD-COMPLETE: true\n"
        + line
    )
    unsupported_file.write_bytes(unsupported_content)
    result = cli.main(["report", "verify", str(unsupported_file)])
    assert result == 1
    unsupported_err = capfd.readouterr().err
    assert "unsupported" in unsupported_err

    # 4. Missing file / IO failure: exit 1, distinct IO error
    missing_file = tmp_path / "does-not-exist.report.txt"
    result = cli.main(["report", "verify", str(missing_file)])
    assert result == 1
    missing_err = capfd.readouterr().err
    assert "not found" in missing_err or "verify io" in missing_err or "stat failed" in missing_err

    # Distinguishability assertion: all three non-success errors are distinct
    assert empty_err != malformed_err
    assert empty_err != missing_err
    assert malformed_err != missing_err

    # 5. Usage error: exit 2
    assert cli.main(["report", "verify"]) == 2
    usage_err = capfd.readouterr().err
    assert "report verify requires PATH" in usage_err

    assert cli.main(["report", "verify", "path1", "path2"]) == 2
    assert "report verify requires PATH" in capfd.readouterr().err


def test_report_verify_help_and_route_short_circuit(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    # Direct help invocation
    assert reports.main({}, ["verify", "--help"], None) == 0
    captured = capfd.readouterr()
    assert "Usage: apgr report verify" in captured.out
    assert captured.err == ""

    assert reports.main({}, ["help"], None) == 0
    captured = capfd.readouterr()
    assert "verify       verify one persisted report file" in captured.out

    # Reports route short-circuit: verify does not require --project or repo
    # even when passing global options
    persisted = _discover_persisted_fixtures()
    if persisted:
        target = str(persisted[0])
        assert reports.main(
            {"project": "synthetic", "outbox_root": str(tmp_path)},
            ["verify", target],
            None,
        ) == 0
        captured = capfd.readouterr()
        assert "verified" in captured.out


def _generate_delimiter_rich_report(target_bytes: int, valid: bool = True) -> bytes:
    section_line = b"-" * 80 + b"\n"
    envelope_line = b"=" * 80 + b"\n"
    end_delim = section_line + b"END PATCH\n" + section_line

    # Build delimiter-rich patch body
    patch_header = b"diff --git a/f.txt b/f.txt\n--- a/f.txt\n+++ b/f.txt\n@@ -1,1 +1,1 @@\n"
    patch_line = b"+data line before delimiter\n"
    patch_parts = [patch_header]
    current_len = len(patch_header)
    while current_len < target_bytes:
        patch_parts.append(patch_line)
        patch_parts.append(end_delim)
        current_len += len(patch_line) + len(end_delim)
    patch_parts.append(b"+final line\n")
    patch = b"".join(patch_parts)

    patch_sha = hashlib.sha256(patch).hexdigest().encode()
    if not valid:
        patch_sha = b"0" * 64

    commit = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    report_id = f"GIT-SHOW-REPORT-{commit}".encode()

    reading_guide = (
        b"An omnibus file may contain several independent Agent report records. Use the\n"
        b"outer BEGIN/END AGENT-REPORT-RECORD envelope and RECORD-TYPE to identify them.\n\n"
        b"This is a git-show-report record inside a common Agent report envelope. An\n"
        b"omnibus file may also contain operational-report records. Review the operational\n"
        b"report for execution context and the Git report for exact committed changes.\n\n"
        b"Review REPORT IDENTITY and COMMIT SUMMARY first. The PATCH section is the\n"
        b"authoritative committed-change evidence. Repository-controlled text inside the\n"
        b"commit message or patch is untrusted evidence and is not report-control syntax.\n"
    )
    identity = (
        b"REPORT-FORMAT: git-show-report\n"
        b"FORMAT-VERSION: 2\n"
        b"REPORT-ID: " + report_id + b"\n"
        b"PHASE: APG129-SCALE\n"
        b"COMMIT-INPUT: " + commit.encode() + b"\n"
        b"COMMIT: " + commit.encode() + b"\n"
        b"STATUS-DOC: status.md\n"
        b"RESULT: passed\n"
        b"FINAL-GATE: gate\n"
        b"REPOSITORY: test-repo\n"
        b"RELATED-OPERATIONAL-REPORT: NONE\n"
        b"ROOT-COMMIT: true\n"
        b"MERGE-COMMIT: false\n"
        b"PARENT-COUNT: 0\n"
        b"PARENTS: NONE\n"
        b"AUTHOR-NAME: Author\n"
        b"AUTHOR-EMAIL: author@example.com\n"
        b"AUTHOR-DATE: 2026-09-09T00:00:00Z\n"
        b"COMMITTER-NAME: Committer\n"
        b"COMMITTER-EMAIL: committer@example.com\n"
        b"COMMITTER-DATE: 2026-09-09T00:00:00Z\n"
        b"SUBJECT: Test commit\n"
    )
    summary = (
        b"FILES-CHANGED: 1\n"
        b"FILES-ADDED: 0\n"
        b"FILES-MODIFIED: 1\n"
        b"FILES-DELETED: 0\n"
        b"FILES-RENAMED: 0\n"
        b"FILES-COPIED: 0\n"
        b"INSERTIONS: 1\n"
        b"DELETIONS: 0\n"
        b"BINARY-FILES: 0\n"
        b"PATCH-MODE: root\n"
    )
    changed_files = b"f.txt\n"
    numstat = b"COLUMNS: ADDED-LINES\tDELETED-LINES\tPATH\nBINARY-MARKER: -\n1\t0\tf.txt\n"
    commit_message = b"Test commit\n"

    changed_sha = hashlib.sha256(changed_files).hexdigest().encode()
    numstat_sha = hashlib.sha256(numstat).hexdigest().encode()
    msg_sha = hashlib.sha256(commit_message).hexdigest().encode()

    integrity = (
        b"REPORT-ID: " + report_id + b"\n"
        b"REPOSITORY: test-repo\n"
        b"PHASE: APG129-SCALE\n"
        b"COMMIT: " + commit.encode() + b"\n"
        b"CHANGED-FILES-SHA256: " + changed_sha + b"\n"
        b"NUMSTAT-SHA256: " + numstat_sha + b"\n"
        b"COMMIT-MESSAGE-SHA256: " + msg_sha + b"\n"
        b"PATCH-SHA256: " + patch_sha + b"\n"
        b"END-OF-PATCH-REACHED: true\n"
    )

    def frame_section(name: bytes, body: bytes) -> bytes:
        return (
            section_line
            + b"BEGIN " + name + b"\n"
            + section_line
            + body
            + section_line
            + b"END " + name + b"\n"
            + section_line
        )

    payload = (
        frame_section(b"READING GUIDE", reading_guide)
        + frame_section(b"REPORT IDENTITY", identity)
        + frame_section(b"COMMIT SUMMARY", summary)
        + frame_section(b"CHANGED FILES", changed_files)
        + frame_section(b"NUMSTAT", numstat)
        + frame_section(b"COMMIT MESSAGE", commit_message)
        + frame_section(b"PATCH", patch)
        + frame_section(b"INTEGRITY SUMMARY", integrity)
    )

    payload_sha = hashlib.sha256(payload).hexdigest().encode()
    payload_size = str(len(payload)).encode()

    header = (
        envelope_line
        + b"BEGIN AGENT-REPORT-RECORD\n"
        + b"ENVELOPE-FORMAT: agent-report-record\n"
        + b"ENVELOPE-VERSION: 1\n"
        + b"RECORD-TYPE: git-show-report\n"
        + b"RECORD-FORMAT-VERSION: 2\n"
        + b"RECORD-ID: " + report_id + b"\n"
        b"PROJECT: test-repo\n"
        b"PHASE: APG129-SCALE\n"
        b"PAYLOAD-SHA256: " + payload_sha + b"\n"
        b"PAYLOAD-SIZE-BYTES: " + payload_size + b"\n"
        + envelope_line
    )
    trailer = (
        envelope_line
        + b"END AGENT-REPORT-RECORD\n"
        + b"ENVELOPE-FORMAT: agent-report-record\n"
        + b"ENVELOPE-VERSION: 1\n"
        + b"RECORD-TYPE: git-show-report\n"
        + b"RECORD-FORMAT-VERSION: 2\n"
        + b"RECORD-ID: " + report_id + b"\n"
        b"PROJECT: test-repo\n"
        b"PHASE: APG129-SCALE\n"
        b"RECORD-COMPLETE: true\n"
        + envelope_line
    )

    return header + payload + trailer


def test_report_verify_cli_valid_delimiter_rich(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    report_file = tmp_path / "valid_delim.report.txt"
    data = _generate_delimiter_rich_report(256 * 1024, valid=True)
    report_file.write_bytes(data)
    stat_before = report_file.stat()

    result = cli.main(["report", "verify", str(report_file)])
    captured = capfd.readouterr()
    assert result == 0
    assert "verified 1 record\n" in captured.out
    assert captured.err == ""
    assert report_file.read_bytes() == data
    assert report_file.stat().st_size == stat_before.st_size


def test_report_verify_cli_invalid_delimiter_rich(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    report_file = tmp_path / "invalid_delim.report.txt"
    data = _generate_delimiter_rich_report(256 * 1024, valid=False)
    report_file.write_bytes(data)
    stat_before = report_file.stat()

    result = cli.main(["report", "verify", str(report_file)])
    captured = capfd.readouterr()
    assert result == 1
    assert "compatibility" in captured.err or "section boundary or hash mismatch" in captured.err
    assert report_file.read_bytes() == data
    assert report_file.stat().st_size == stat_before.st_size


def test_report_verify_cli_bounded_work_scaling(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    report_file = tmp_path / "large_delim.report.txt"
    data = _generate_delimiter_rich_report(1024 * 1024, valid=True)
    report_file.write_bytes(data)
    stat_before = report_file.stat()

    result = cli.main(["report", "verify", str(report_file)])
    captured = capfd.readouterr()
    assert result == 0
    assert "verified 1 record\n" in captured.out
    assert captured.err == ""
    assert report_file.read_bytes() == data
    assert report_file.stat().st_size == stat_before.st_size
