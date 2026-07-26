#!/usr/bin/env python3
"""Focused integration tests for the Python agent-report commands."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
LIBEXEC = REPOSITORY_ROOT / "libexec"
sys.path.insert(0, str(LIBEXEC))

from agent_report import models, rendering  # noqa: E402


class AgentReportIntegrationTests(unittest.TestCase):
    """Exercise real Git repositories, filesystems, locking, and CLIs."""

    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="apg27-agent-report-test-")
        self.root = Path(self.temporary.name)
        self.report_root = self.root / "reports"
        self.repo = self.make_repo("work-repo")
        self.show_command = REPOSITORY_ROOT / "bin" / "git-show-report"
        self.diff_command = REPOSITORY_ROOT / "bin" / "git-diff-report"
        self.operational_command = REPOSITORY_ROOT / "bin" / "append-operational-report"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_repo(self, name: str) -> Path:
        repository = self.root / name
        repository.mkdir()
        self.git(repository, "init", "-q", "-b", "main")
        self.git(repository, "config", "user.email", "codex@example.invalid")
        self.git(repository, "config", "user.name", "Codex Test")
        (repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        (repository / "rename-source.txt").write_text("rename\n", encoding="utf-8")
        self.git(repository, "add", "tracked.txt", "rename-source.txt")
        self.git(repository, "commit", "-qm", "initial")
        return repository

    @staticmethod
    def git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["git", "-C", os.fspath(repository), *arguments],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_tool(
        self,
        command: Path,
        *arguments: str,
        repository: Path | None = None,
        extra_environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        environment = os.environ.copy()
        environment["GIT_SHOW_REPORT_ROOT"] = os.fspath(self.report_root)
        if extra_environment:
            environment.update(extra_environment)
        return subprocess.run(
            [os.fspath(command), *arguments],
            cwd=repository or self.repo,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def report_path(self, phase: str, repository: Path | None = None) -> Path:
        project = (repository or self.repo).name
        return self.report_root / project / f"{phase}.report.txt"

    @staticmethod
    def field_values(report: bytes, name: str) -> list[str]:
        prefix = name.encode("ascii") + b": "
        return [
            line[len(prefix) :].decode("utf-8")
            for line in report.splitlines()
            if line.startswith(prefix)
        ]

    def write_operational_body(self, name: str, fields: dict[str, str]) -> Path:
        source = self.root / name
        body = "REPORT\n" + "".join(f"{key}: {value}\n" for key, value in fields.items())
        source.write_text(body, encoding="utf-8")
        source.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return source

    def create_show_record(self, phase: str) -> tuple[str, str]:
        commit = self.git(self.repo, "rev-parse", "HEAD").stdout.decode().strip()
        result = self.run_tool(
            self.show_command,
            phase,
            commit,
            "docs/status/example.md",
            "passed",
            "focused",
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return commit, f"GIT-SHOW-REPORT-{commit}"

    def create_diff_record(self, phase: str) -> str:
        (self.repo / "tracked.txt").write_text("tracked\nchanged\n", encoding="utf-8")
        result = self.run_tool(self.diff_command, phase, "passed", "focused")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        report = self.report_path(phase).read_bytes()
        return next(
            value
            for value in self.field_values(report, "RECORD-ID")
            if value.startswith("GIT-DIFF-REPORT-")
        )

    def test_git_diff_captures_mixed_rename_binary_untracked_and_optional_status_doc(self) -> None:
        (self.repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        self.git(self.repo, "add", ".gitignore")
        self.git(self.repo, "commit", "-qm", "ignore fixture")
        self.git(self.repo, "mv", "rename-source.txt", "renamed.txt")
        (self.repo / "tracked.txt").write_text("staged\n", encoding="utf-8")
        self.git(self.repo, "add", "tracked.txt")
        (self.repo / "tracked.txt").write_text("staged\nunstaged\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("untracked\n", encoding="utf-8")
        (self.repo / "ignored.txt").write_text("ignored\n", encoding="utf-8")
        (self.repo / "binary.bin").write_bytes(b"\x00\x01\x02")
        index_before = (self.repo / ".git" / "index").read_bytes()
        status_before = self.git(self.repo, "status", "--porcelain=v2", "-z", "--untracked-files=all").stdout

        result = self.run_tool(
            self.diff_command,
            "DIFF-MIXED",
            "passed",
            "focused",
            "--status-doc",
            "docs/status/example.md",
        )

        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), index_before)
        self.assertEqual(
            self.git(self.repo, "status", "--porcelain=v2", "-z", "--untracked-files=all").stdout,
            status_before,
        )
        report = self.report_path("DIFF-MIXED").read_bytes()
        self.assertIn(b"RECORD-TYPE: git-diff-report\n", report)
        self.assertIn(b"RECORD-FORMAT-VERSION: 1\n", report)
        self.assertIn(b"STATUS-DOC: docs/status/example.md\n", report)
        self.assertIn(b"renamed.txt", report)
        self.assertIn(b"untracked.txt", report)
        self.assertNotIn(b"ignored.txt", report)
        self.assertIn(b"binary.bin", report)
        self.assertIn(b"BINARY-FILES: 1\n", report)
        self.assertIn(b"diff --git", report)
        self.assertIn(b"PRE-POST-HEAD-MATCH: true\n", report)
        self.assertIn(b"PRE-POST-INDEX-MATCH: true\n", report)
        self.assertIn(b"PRE-POST-WORKTREE-MATCH: true\n", report)
        self.assertEqual(len(rendering.parse_complete_records(report)), 1)

        second = self.run_tool(self.diff_command, "DIFF-NO-STATUS", "passed", "focused")
        self.assertEqual(second.returncode, 0, second.stderr.decode())
        second_report = self.report_path("DIFF-NO-STATUS").read_bytes()
        self.assertIn(b"STATUS-DOC: NONE\n", second_report)
        first_id = next(
            value
            for value in self.field_values(report, "RECORD-ID")
            if value.startswith("GIT-DIFF-REPORT-")
        )
        second_id = next(
            value
            for value in self.field_values(second_report, "RECORD-ID")
            if value.startswith("GIT-DIFF-REPORT-")
        )
        self.assertEqual(first_id, second_id)

    def test_git_diff_refuses_clean_custom_split_sparse_and_unmerged_states(self) -> None:
        clean = self.run_tool(self.diff_command, "CLEAN", "passed", "focused")
        self.assertEqual(clean.returncode, 1)
        self.assertIn(b"no reportable change", clean.stderr)

        custom = self.run_tool(
            self.diff_command,
            "CUSTOM",
            "passed",
            "focused",
            extra_environment={"GIT_INDEX_FILE": os.fspath(self.root / "custom-index")},
        )
        self.assertEqual(custom.returncode, 1)
        self.assertIn(b"GIT_INDEX_FILE", custom.stderr)

        unborn_repo = self.root / "unborn-repo"
        unborn_repo.mkdir()
        self.git(unborn_repo, "init", "-q", "-b", "main")
        (unborn_repo / "untracked.txt").write_text("unborn\n", encoding="utf-8")
        unborn = self.run_tool(
            self.diff_command,
            "UNBORN",
            "passed",
            "focused",
            repository=unborn_repo,
        )
        self.assertEqual(unborn.returncode, 1)
        self.assertIn(b"unborn HEAD", unborn.stderr)

        split_repo = self.make_repo("split-repo")
        self.git(split_repo, "update-index", "--split-index")
        (split_repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        split = self.run_tool(
            self.diff_command,
            "SPLIT",
            "passed",
            "focused",
            repository=split_repo,
        )
        self.assertEqual(split.returncode, 1)
        self.assertIn(b"split index", split.stderr)

        sparse_repo = self.make_repo("sparse-repo")
        self.git(sparse_repo, "config", "core.sparseCheckout", "true")
        (sparse_repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        sparse = self.run_tool(
            self.diff_command,
            "SPARSE",
            "passed",
            "focused",
            repository=sparse_repo,
        )
        self.assertEqual(sparse.returncode, 1)
        self.assertIn(b"sparse index", sparse.stderr)

        conflict_repo = self.make_repo("conflict-repo")
        self.git(conflict_repo, "checkout", "-qb", "other")
        (conflict_repo / "tracked.txt").write_text("other\n", encoding="utf-8")
        self.git(conflict_repo, "commit", "-qam", "other")
        self.git(conflict_repo, "checkout", "-q", "main")
        (conflict_repo / "tracked.txt").write_text("main\n", encoding="utf-8")
        self.git(conflict_repo, "commit", "-qam", "main")
        self.git(conflict_repo, "merge", "other", check=False)
        unmerged = self.run_tool(
            self.diff_command,
            "UNMERGED",
            "passed",
            "focused",
            repository=conflict_repo,
        )
        self.assertEqual(unmerged.returncode, 1)
        self.assertIn(b"unmerged", unmerged.stderr)

    def test_git_diff_rejects_malformed_optional_status_doc_arguments(self) -> None:
        result = self.run_tool(
            self.diff_command,
            "INVALID-STATUS",
            "passed",
            "focused",
            "--wrong-option",
            "docs/status/example.md",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn(b"Usage: git-diff-report", result.stderr)

    def test_git_diff_detects_drift_and_interruption_cleans_owned_temporary_state(self) -> None:
        (self.repo / "tracked.txt").write_text("before\n", encoding="utf-8")
        signal_dir = self.root / "drift-signal"
        signal_dir.mkdir()
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_SHOW_REPORT_ROOT": os.fspath(self.report_root),
                "AGENT_REPORT_TESTING": "1",
                "AGENT_REPORT_TEST_PAUSE_STEP": "before-post-drift-check",
                "AGENT_REPORT_TEST_SIGNAL_DIR": os.fspath(signal_dir),
            }
        )
        process = subprocess.Popen(
            [os.fspath(self.diff_command), "DRIFT", "passed", "focused"],
            cwd=self.repo,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.wait_for_path(signal_dir / "ready")
        (self.repo / "tracked.txt").write_text("after\n", encoding="utf-8")
        (signal_dir / "continue").touch()
        _, error = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 1)
        self.assertIn(b"concurrent repository drift", error)
        self.assertFalse(self.report_path("DRIFT").exists())

        index_path = self.repo / ".git" / "index"
        index_before = index_path.read_bytes()
        status_before = self.git(
            self.repo,
            "status",
            "--porcelain=v2",
            "-z",
            "--untracked-files=all",
        ).stdout
        signal_dir = self.root / "index-drift-signal"
        signal_dir.mkdir()
        environment["AGENT_REPORT_TEST_SIGNAL_DIR"] = os.fspath(signal_dir)
        process = subprocess.Popen(
            [os.fspath(self.diff_command), "INDEX-DRIFT", "passed", "focused"],
            cwd=self.repo,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.wait_for_path(signal_dir / "ready")
        replacement = self.repo / ".git" / "index.replacement"
        shutil.copy2(index_path, replacement)
        os.replace(replacement, index_path)
        (signal_dir / "continue").touch()
        _, error = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 1)
        self.assertIn(b"concurrent repository drift", error)
        self.assertFalse(self.report_path("INDEX-DRIFT").exists())
        self.assertEqual(index_path.read_bytes(), index_before)
        self.assertEqual(
            self.git(
                self.repo,
                "status",
                "--porcelain=v2",
                "-z",
                "--untracked-files=all",
            ).stdout,
            status_before,
        )

        (self.repo / "tracked.txt").write_text("interrupt\n", encoding="utf-8")
        for signal_name, signal_value in (
            ("TERM", signal.SIGTERM),
            ("HUP", signal.SIGHUP),
        ):
            with self.subTest(signal=signal_name):
                interruption_temp = self.root / f"interrupt-{signal_name.lower()}-temp"
                interruption_temp.mkdir()
                signal_dir = self.root / f"interrupt-{signal_name.lower()}-signal"
                signal_dir.mkdir()
                environment.update(
                    {
                        "TMPDIR": os.fspath(interruption_temp),
                        "AGENT_REPORT_TEST_PAUSE_STEP": "private-index-ready",
                        "AGENT_REPORT_TEST_SIGNAL_DIR": os.fspath(signal_dir),
                    }
                )
                phase = f"INTERRUPT-{signal_name}"
                process = subprocess.Popen(
                    [os.fspath(self.diff_command), phase, "passed", "focused"],
                    cwd=self.repo,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.wait_for_path(signal_dir / "ready")
                self.assertTrue(
                    any(
                        path.name.startswith("git-diff-index.")
                        for path in interruption_temp.iterdir()
                    )
                )
                process.send_signal(signal_value)
                process.communicate(timeout=10)
                self.assertNotEqual(process.returncode, 0)
                self.assertFalse(self.report_path(phase).exists())
                self.assertEqual(list(interruption_temp.iterdir()), [])

    def test_operational_standalone_and_show_association_are_validated(self) -> None:
        standalone_body = self.write_operational_body(
            "standalone.txt",
            {
                "report_schema": "operational-report-v1",
                "phase": "STANDALONE",
                "outcome": "passed",
            },
        )
        standalone = self.run_tool(
            self.operational_command,
            "STANDALONE",
            os.fspath(standalone_body),
            "passed",
            "focused",
        )
        self.assertEqual(standalone.returncode, 0, standalone.stderr.decode())
        self.assertIn(b"RELATED-GIT-REPORT-ID: NONE\n", self.report_path("STANDALONE").read_bytes())

        swap_source = self.root / "swap-source.txt"
        swap_source.write_bytes(b"public\n")
        swap_source.chmod(stat.S_IRUSR | stat.S_IWUSR)
        swap_replacement = self.root / "swap-replacement.txt"
        swap_replacement.write_bytes(b"secret\n")
        swap_replacement.chmod(stat.S_IRUSR | stat.S_IWUSR)
        swap_original = self.root / "swap-original.txt"
        swap_signal = self.root / "swap-signal"
        swap_signal.mkdir()
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_SHOW_REPORT_ROOT": os.fspath(self.report_root),
                "AGENT_REPORT_TESTING": "1",
                "AGENT_REPORT_TEST_PAUSE_STEP": "source-validated",
                "AGENT_REPORT_TEST_SIGNAL_DIR": os.fspath(swap_signal),
            }
        )
        process = subprocess.Popen(
            [
                os.fspath(self.operational_command),
                "SOURCE-SWAP",
                os.fspath(swap_source),
                "passed",
                "focused",
            ],
            cwd=self.repo,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.wait_for_path(swap_signal / "ready")
        swap_source.rename(swap_original)
        swap_source.symlink_to(swap_replacement)
        (swap_signal / "continue").touch()
        _, error = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 1)
        self.assertIn(b"source operational report", error)
        self.assertFalse(self.report_path("SOURCE-SWAP").exists())

        commit, show_id = self.create_show_record("SHOW-ASSOC")
        associated_body = self.write_operational_body(
            "show-associated.txt",
            {
                "report_schema": "operational-report-v1",
                "phase": "SHOW-ASSOC",
                "outcome": "passed",
                "primary_commit": commit,
            },
        )
        associated = self.run_tool(
            self.operational_command,
            "SHOW-ASSOC",
            os.fspath(associated_body),
            "passed",
            "focused",
            "--related-commit",
            commit[:12],
            "--related-git-report-id",
            show_id,
        )
        self.assertEqual(associated.returncode, 0, associated.stderr.decode())
        parsed = rendering.parse_complete_records(self.report_path("SHOW-ASSOC").read_bytes())
        self.assertEqual([item.record.record_type for item in parsed], ["git-show-report", "operational-report"])

        missing = self.run_tool(
            self.operational_command,
            "SHOW-ASSOC",
            os.fspath(associated_body),
            "passed",
            "focused",
        )
        self.assertEqual(missing.returncode, 1)
        self.assertIn(b"exact related Git report id", missing.stderr)

        nonexistent = self.run_tool(
            self.operational_command,
            "SHOW-ASSOC",
            os.fspath(associated_body),
            "passed",
            "focused",
            "--related-git-report-id",
            "GIT-SHOW-REPORT-" + "0" * 40,
        )
        self.assertEqual(nonexistent.returncode, 1)
        self.assertIn(b"does not exist", nonexistent.stderr)

        duplicate_body = self.root / "show-associated-duplicates.txt"
        duplicate_body.write_text(
            "REPORT\n"
            "report_schema: operational-report-v1\n"
            "report_schema: conflicting-schema\n"
            "phase: SHOW-ASSOC\n"
            "phase: OTHER-PHASE\n"
            "outcome: passed\n"
            f"primary_commit: {commit}\n"
            f"primary_commit: {'0' * len(commit)}\n",
            encoding="utf-8",
        )
        duplicate_body.chmod(stat.S_IRUSR | stat.S_IWUSR)
        duplicate = self.run_tool(
            self.operational_command,
            "SHOW-ASSOC",
            os.fspath(duplicate_body),
            "passed",
            "focused",
            "--related-commit",
            commit,
            "--related-git-report-id",
            show_id,
        )
        self.assertEqual(duplicate.returncode, 1)
        self.assertIn(b"duplicate", duplicate.stderr)

    def test_operational_diff_association_requires_truthful_schema_and_order(self) -> None:
        diff_id = self.create_diff_record("DIFF-ASSOC")
        body = self.write_operational_body(
            "diff-associated.txt",
            {
                "report_schema": "operational-report-v1",
                "phase": "DIFF-ASSOC",
                "outcome": "passed",
                "primary_git_report_id": diff_id,
            },
        )
        first = self.run_tool(
            self.operational_command,
            "DIFF-ASSOC",
            os.fspath(body),
            "passed",
            "focused",
            "--related-git-report-id",
            diff_id,
        )
        second = self.run_tool(
            self.operational_command,
            "DIFF-ASSOC",
            os.fspath(body),
            "passed",
            "focused",
            "--related-git-report-id",
            diff_id,
        )
        self.assertEqual(first.returncode, 0, first.stderr.decode())
        self.assertEqual(second.returncode, 0, second.stderr.decode())
        parsed = rendering.parse_complete_records(self.report_path("DIFF-ASSOC").read_bytes())
        self.assertEqual(
            [item.record.record_type for item in parsed],
            ["git-diff-report", "operational-report", "operational-report"],
        )
        self.assertEqual(parsed[1].record.record_id, parsed[2].record.record_id)

        wrong_body = self.write_operational_body(
            "wrong-diff.txt",
            {
                "report_schema": "operational-report-v1",
                "phase": "DIFF-ASSOC",
                "outcome": "passed",
                "primary_git_report_id": "GIT-DIFF-REPORT-" + "0" * 64,
            },
        )
        wrong = self.run_tool(
            self.operational_command,
            "DIFF-ASSOC",
            os.fspath(wrong_body),
            "passed",
            "focused",
            "--related-git-report-id",
            diff_id,
        )
        self.assertEqual(wrong.returncode, 1)
        self.assertIn(b"primary_git_report_id", wrong.stderr)

    def test_operational_conflict_multiple_records_and_concurrent_append_fail_closed(self) -> None:
        first_commit, first_id = self.create_show_record("MULTIPLE")
        (self.repo / "tracked.txt").write_text("second\n", encoding="utf-8")
        self.git(self.repo, "commit", "-qam", "second")
        second_commit = self.git(self.repo, "rev-parse", "HEAD").stdout.decode().strip()
        second_show = self.run_tool(
            self.show_command,
            "MULTIPLE",
            second_commit,
            "docs/status/example.md",
            "passed",
            "focused",
        )
        self.assertEqual(second_show.returncode, 0, second_show.stderr.decode())
        body = self.write_operational_body(
            "multiple.txt",
            {
                "report_schema": "operational-report-v1",
                "phase": "MULTIPLE",
                "outcome": "passed",
                "primary_commit": first_commit,
            },
        )
        ambiguous = self.run_tool(
            self.operational_command,
            "MULTIPLE",
            os.fspath(body),
            "passed",
            "focused",
        )
        self.assertEqual(ambiguous.returncode, 1)

        conflict = self.run_tool(
            self.operational_command,
            "MULTIPLE",
            os.fspath(body),
            "passed",
            "focused",
            "--related-commit",
            second_commit,
            "--related-git-report-id",
            first_id,
        )
        self.assertEqual(conflict.returncode, 2)
        self.assertIn(b"conflict", conflict.stderr)

        environment = os.environ.copy()
        environment["GIT_SHOW_REPORT_ROOT"] = os.fspath(self.report_root)
        arguments = [
            os.fspath(self.operational_command),
            "MULTIPLE",
            os.fspath(body),
            "passed",
            "focused",
            "--related-commit",
            first_commit,
            "--related-git-report-id",
            first_id,
        ]
        processes = [
            subprocess.Popen(arguments, cwd=self.repo, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for _ in range(2)
        ]
        results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]
        self.assertEqual([result[2] for result in results], [0, 0], results)
        report = self.report_path("MULTIPLE").read_bytes()
        parsed = rendering.parse_complete_records(report)
        self.assertEqual(len(parsed), 4)
        self.assertTrue(all(item.record.phase == "MULTIPLE" for item in parsed))
        self.assertFalse(self.report_path("MULTIPLE").with_suffix(".txt.lock").exists())

        invalid_phase = "INVALID-GIT-VERSION"
        invalid_commit = self.git(self.repo, "rev-parse", "HEAD").stdout.decode().strip()
        invalid_id = f"GIT-SHOW-REPORT-{invalid_commit}"
        invalid_record = models.ReportRecord(
            record_type="git-show-report",
            format_version=99,
            record_id=invalid_id,
            project=self.repo.name,
            phase=invalid_phase,
            payload=b"arbitrary payload\n",
        )
        invalid_report = self.report_path(invalid_phase)
        invalid_report.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        invalid_report.parent.chmod(0o700)
        invalid_report.write_bytes(rendering.build_record(invalid_record))
        invalid_report.chmod(stat.S_IRUSR | stat.S_IWUSR)
        invalid_body = self.write_operational_body(
            "invalid-version.txt",
            {
                "report_schema": "operational-report-v1",
                "phase": invalid_phase,
                "outcome": "passed",
                "primary_commit": invalid_commit,
            },
        )
        invalid = self.run_tool(
            self.operational_command,
            invalid_phase,
            os.fspath(invalid_body),
            "passed",
            "focused",
            "--related-commit",
            invalid_commit,
            "--related-git-report-id",
            invalid_id,
        )
        self.assertEqual(invalid.returncode, 1)
        self.assertIn(b"format version", invalid.stderr)

    def test_help_exit_classes_and_unsafe_destination_are_bounded(self) -> None:
        for command in (self.show_command, self.diff_command, self.operational_command):
            with self.subTest(command=command.name):
                help_result = self.run_tool(command, "--help")
                self.assertEqual(help_result.returncode, 0)
                usage_result = self.run_tool(command)
                self.assertEqual(usage_result.returncode, 2)

        (self.repo / "tracked.txt").write_text("changed content\n", encoding="utf-8")
        report_dir = self.report_root / self.repo.name
        report_dir.mkdir(parents=True, mode=0o700)
        target = self.root / "target"
        target.write_text("unsafe\n", encoding="utf-8")
        unsafe = report_dir / "UNSAFE.report.txt"
        unsafe.symlink_to(target)
        result = self.run_tool(self.diff_command, "UNSAFE", "passed", "focused")
        self.assertEqual(result.returncode, 1)
        self.assertIn(b"unsafe", result.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "unsafe\n")

    @staticmethod
    def wait_for_path(path: Path) -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if path.exists():
                return
            time.sleep(0.01)
        raise AssertionError(f"timed out waiting for {path.name}")


if __name__ == "__main__":
    unittest.main()
