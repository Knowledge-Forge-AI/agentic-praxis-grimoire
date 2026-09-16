#!/usr/bin/env python3
"""Unit tests for staging correction helpers and validation logging."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_public_release as release  # noqa: E402
import apg_staging_correction as staging_correction  # noqa: E402


class TestRunCheckedCommand(unittest.TestCase):
    def test_run_checked_command_without_log(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("APG_VALIDATION_OUTPUT_LOG", None)
                staging_correction.run_checked_command([sys.executable, "-c", "print('hello from check')"], temp_path)

    def test_run_checked_command_with_log_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / "work"
            work_dir.mkdir()
            log_file = Path(temp_dir) / "output.log"
            with mock.patch.dict(os.environ, {"APG_VALIDATION_OUTPUT_LOG": str(log_file)}):
                staging_correction.run_checked_command([sys.executable, "-c", "print('hello stdout')"], work_dir)
            self.assertTrue(log_file.exists())
            content = log_file.read_text(encoding="utf-8")
            self.assertIn("--- COMMAND: ", content)
            self.assertIn("RETURNCODE: 0", content)
            self.assertIn("hello stdout", content)

    def test_run_checked_command_with_log_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / "work"
            work_dir.mkdir()
            log_file = Path(temp_dir) / "output.log"
            with mock.patch.dict(os.environ, {"APG_VALIDATION_OUTPUT_LOG": str(log_file)}):
                with self.assertRaisesRegex(release.ToolError, "configured validation failed"):
                    staging_correction.run_checked_command(
                        [sys.executable, "-c", "import sys; sys.stderr.write('fatal err'); sys.exit(2)"], work_dir
                    )
            self.assertTrue(log_file.exists())
            content = log_file.read_text(encoding="utf-8")
            self.assertIn("RETURNCODE: 2", content)
            self.assertIn("fatal err", content)

    def test_run_checked_command_refuses_relative_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            with mock.patch.dict(os.environ, {"APG_VALIDATION_OUTPUT_LOG": "relative/path.log"}):
                with self.assertRaisesRegex(release.ToolError, "validation output log path must be absolute"):
                    staging_correction.run_checked_command([sys.executable, "-c", "pass"], temp_path)

    def test_run_checked_command_refuses_overlapping_log_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            overlap = temp_path / "inside" / "log.txt"
            overlap.parent.mkdir(parents=True)
            with mock.patch.dict(os.environ, {"APG_VALIDATION_OUTPUT_LOG": str(overlap)}):
                with self.assertRaisesRegex(release.ToolError, "validation output log path cannot overlap"):
                    staging_correction.run_checked_command([sys.executable, "-c", "pass"], temp_path)

    def test_run_checked_command_refuses_log_overlapping_base_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir) / "base"
            base_dir.mkdir()
            work_dir = Path(temp_dir) / "work"
            work_dir.mkdir()
            overlap = base_dir / "log.txt"
            with mock.patch.dict(os.environ, {"APG_VALIDATION_OUTPUT_LOG": str(overlap)}):
                with self.assertRaisesRegex(release.ToolError, "validation output log path cannot overlap"):
                    staging_correction.run_checked_command(
                        [sys.executable, "-c", "pass"], work_dir, {"APG12_PUBLIC_V01_ROOT": str(base_dir)}
                    )

    def test_run_checked_command_log_write_oserror(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / "work"
            work_dir.mkdir()
            log_file = Path(temp_dir) / "output.log"
            with (
                mock.patch.dict(os.environ, {"APG_VALIDATION_OUTPUT_LOG": str(log_file)}),
                mock.patch("os.open", side_effect=OSError("disk full")),
            ):
                with self.assertRaisesRegex(release.ToolError, "could not write validation output log: disk full"):
                    staging_correction.run_checked_command([sys.executable, "-c", "pass"], work_dir)

    def test_run_checked_command_launch_oserror(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir) / "work"
            work_dir.mkdir()
            with mock.patch("subprocess.run", side_effect=OSError("exec failed")):
                with self.assertRaisesRegex(release.ToolError, "configured validation could not run: nonexistent_executable: exec failed"):
                    staging_correction.run_checked_command(["nonexistent_executable"], work_dir)


class TestRequiredChecksNormalisation(unittest.TestCase):
    def test_required_check_receipts_are_success_only_and_deterministic(self) -> None:
        self.assertEqual(
            staging_correction.normalise_required_checks(
                {"unit-integration": "success", "guard": "success"}
            ),
            {"guard": "success", "unit-integration": "success"},
        )
        self.assertEqual(
            staging_correction.normalise_required_checks(("guard", "policy")),
            {"guard": "success", "policy": "success"},
        )
        with self.assertRaisesRegex(release.ToolError, "did not succeed"):
            staging_correction.normalise_required_checks({"guard": "failure"})
        with self.assertRaisesRegex(release.InvocationError, "duplicate"):
            staging_correction.normalise_required_checks(("guard", "guard"))


class TestStagingCorrectionMode(unittest.TestCase):
    def setUp(self) -> None:
        self.source = release.Repository(Path("source"), "s" * 40, "t" * 40)
        self.base = release.Repository(Path("base"), "b" * 40, "c" * 40)
        self.candidate = release.Repository(Path("candidate"), "k" * 40, "l" * 40)
        self.staging_parent = "p" * 40
        self.common_patches = [
            mock.patch.object(release, "validate_repository_separation"),
            mock.patch.object(release, "verify_public_release_lineage"),
            mock.patch.object(release, "require_unchanged"),
            mock.patch.object(release, "load_policy", return_value={}),
            mock.patch.object(release, "repository_fingerprint", return_value=mock.Mock()),
            mock.patch.object(release, "public_candidate_entries", return_value=()),
            mock.patch.object(release, "tree_entries", return_value=()),
            mock.patch.object(release, "validate_versioned_policy_exclusions"),
            mock.patch.object(release, "validate_critical"),
            mock.patch.object(release, "validate_public_symlinks"),
            mock.patch.object(release, "validate_categories_in_isolation"),
        ]
        for p in self.common_patches:
            p.start()
            self.addCleanup(p.stop)

    def test_v011_untagged_builder_rejects_historical_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                release.InvocationError,
                "only available for v0.11.0",
            ):
                staging_correction.build_untagged_candidate(
                    self.source,
                    self.base,
                    Path(temporary) / "candidate",
                    "0.10.0",
                )

    def test_check_candidate_staging_correction_success(self) -> None:
        def text_git(_root: Path, args: list[str], **_kwargs: object) -> str:
            if args == ["rev-list", "--parents", "-n", "1", "HEAD"]:
                return f"{self.candidate.head} {self.staging_parent}"
            if args == ["branch", "--show-current"]:
                return "staging"
            if args == ["log", "-1", "--format=%s"]:
                return "APG145: Repair hosted CI bootstrap and CodeQL validation"
            raise AssertionError(f"unexpected text_git call: {args}")

        def run_git(_root: Path, args: list[str], **_kwargs: object) -> mock.Mock:
            if args == ["merge-base", "--is-ancestor", self.base.head, "HEAD"]:
                return mock.Mock(returncode=0)
            if args[:2] == ["show-ref", "--verify"]:
                return mock.Mock(returncode=1)
            if args[:2] == ["for-each-ref", "--format=%(refname)%00%(objectname)"]:
                if args[2] == "refs/heads":
                    return mock.Mock(stdout=f"refs/heads/main\x00{self.base.head}\nrefs/heads/staging\x00{self.candidate.head}\n".encode())
                if args[2] == "refs/tags":
                    return mock.Mock(stdout=b"")
                if args[2] == "refs":
                    return mock.Mock(stdout=f"refs/heads/main\x00{self.base.head}\nrefs/heads/staging\x00{self.candidate.head}\n".encode())
                return mock.Mock(stdout=b"")
            raise AssertionError(f"unexpected run_git call: {args}")

        with (
            mock.patch.object(release, "text_git", side_effect=text_git),
            mock.patch.object(release, "run_git", side_effect=run_git),
        ):
            res = release.check_candidate(
                self.source,
                self.base,
                self.candidate,
                "0.11.0",
                None,
                allow_staging_correction=True,
                correction_parent=self.staging_parent,
                correction_subject="APG145: Repair hosted CI bootstrap and CodeQL validation",
                untagged=True,
            )
            self.assertEqual(res["status"], "pass")
            self.assertEqual(res["branch"], "staging")
            self.assertEqual(res["candidate_commit"], self.candidate.head)

    def test_check_candidate_staging_correction_requires_correction_parent(self) -> None:
        with self.assertRaisesRegex(
            release.ToolError, "candidate correction check requires an explicit correction_parent"
        ):
            release.check_candidate(
                self.source,
                self.base,
                self.candidate,
                "0.11.0",
                None,
                allow_staging_correction=True,
                correction_parent=None,
            )

    def test_check_candidate_staging_correction_parent_mismatch(self) -> None:
        def text_git(_root: Path, args: list[str], **_kwargs: object) -> str:
            if args == ["rev-list", "--parents", "-n", "1", "HEAD"]:
                return f"{self.candidate.head} {'z' * 40}"
            raise AssertionError(f"unexpected text_git: {args}")

        with (
            mock.patch.object(release, "run_git", return_value=mock.Mock(returncode=0)),
            mock.patch.object(release, "text_git", side_effect=text_git),
        ):
            with self.assertRaisesRegex(release.ToolError, "candidate correction parent mismatch"):
                release.check_candidate(
                    self.source,
                    self.base,
                    self.candidate,
                    "0.11.0",
                    None,
                    allow_staging_correction=True,
                    correction_parent=self.staging_parent,
                )

    def test_check_candidate_staging_correction_wrong_branch(self) -> None:
        def text_git(_root: Path, args: list[str], **_kwargs: object) -> str:
            if args == ["rev-list", "--parents", "-n", "1", "HEAD"]:
                return f"{self.candidate.head} {self.staging_parent}"
            if args == ["branch", "--show-current"]:
                return "main"
            raise AssertionError(f"unexpected text_git: {args}")

        with (
            mock.patch.object(release, "run_git", return_value=mock.Mock(returncode=0)),
            mock.patch.object(release, "text_git", side_effect=text_git),
        ):
            with self.assertRaisesRegex(release.ToolError, "candidate is on the wrong release branch"):
                release.check_candidate(
                    self.source,
                    self.base,
                    self.candidate,
                    "0.11.0",
                    None,
                    allow_staging_correction=True,
                    correction_parent=self.staging_parent,
                )

    def test_check_candidate_staging_correction_subject_mismatch(self) -> None:
        def text_git(_root: Path, args: list[str], **_kwargs: object) -> str:
            if args == ["rev-list", "--parents", "-n", "1", "HEAD"]:
                return f"{self.candidate.head} {self.staging_parent}"
            if args == ["branch", "--show-current"]:
                return "staging"
            if args == ["log", "-1", "--format=%s"]:
                return "Wrong subject"
            raise AssertionError(f"unexpected text_git: {args}")

        with (
            mock.patch.object(release, "run_git", return_value=mock.Mock(returncode=0)),
            mock.patch.object(release, "text_git", side_effect=text_git),
        ):
            with self.assertRaisesRegex(release.ToolError, "candidate release subject is incorrect"):
                release.check_candidate(
                    self.source,
                    self.base,
                    self.candidate,
                    "0.11.0",
                    None,
                    allow_staging_correction=True,
                    correction_parent=self.staging_parent,
                    correction_subject="Expected subject",
                )

    def test_check_candidate_staging_correction_not_ancestor(self) -> None:
        with mock.patch.object(release, "run_git", return_value=mock.Mock(returncode=1)):
            with self.assertRaisesRegex(
                release.ToolError, "candidate release commit does not have the public base in its ancestry"
            ):
                release.check_candidate(
                    self.source,
                    self.base,
                    self.candidate,
                    "0.11.0",
                    None,
                    allow_staging_correction=True,
                    correction_parent=self.staging_parent,
                )

    def test_check_untagged_candidate_forwards_staging_correction(self) -> None:
        with mock.patch.object(release, "check_candidate", return_value={"ok": True}) as mock_check:
            res = staging_correction.check_untagged_candidate(
                self.source,
                self.base,
                self.candidate,
                "0.11.0",
                allow_staging_correction=True,
                correction_parent=self.staging_parent,
                correction_subject="Subject",
            )
            self.assertEqual(res, {"ok": True})
            mock_check.assert_called_once_with(
                self.source,
                self.base,
                self.candidate,
                "0.11.0",
                None,
                untagged=True,
                allow_staging_correction=True,
                correction_parent=self.staging_parent,
                correction_subject="Subject",
            )

    def test_cli_allow_staging_correction_requires_correction_parent(self) -> None:
        with (
            mock.patch.object(release, "resolve_repository", return_value=self.candidate),
            mock.patch.object(release, "validate_version", return_value="0.11.0"),
        ):
            code = release.main([
                "check",
                "--source", "source",
                "--base", "base",
                "--candidate", "candidate",
                "--version", "0.11.0",
                "--allow-staging-correction",
            ])
            self.assertEqual(code, 2)

    def test_build_untagged_candidate_with_staging_parent_and_subject(self) -> None:
        def text_git(_root: Path, args: list[str], **_kwargs: object) -> str:
            if args[:3] == ["show", "-s", "--format=%an%x00%ae%x00%aI"]:
                return "Author\x00author@example.com\x002026-09-13T00:00:00Z"
            if args[0] == "write-tree":
                return "t" * 40
            if args[0] == "commit-tree":
                self.assertIn("-p", args)
                idx = args.index("-p")
                self.assertEqual(args[idx + 1], self.staging_parent)
                self.assertIn("-m", args)
                midx = args.index("-m")
                self.assertEqual(args[midx + 1], "APG145: Repair hosted CI bootstrap and CodeQL validation")
                return "c" * 40
            raise AssertionError(f"unexpected text_git call: {args}")

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            mock.patch.object(release, "validate_repository_separation"),
            mock.patch.object(release, "verify_public_release_lineage"),
            mock.patch.object(release, "public_candidate_entries", return_value=()),
            mock.patch.object(release, "initialize_candidate"),
            mock.patch.object(release, "run_git", return_value=mock.Mock(returncode=0, stdout=b"")),
            mock.patch.object(release, "text_git", side_effect=text_git),
        ):
            out_dir = Path(temp_dir) / "output"
            out_dir.mkdir()
            tree, commit = staging_correction.build_untagged_candidate(
                self.source,
                self.base,
                out_dir,
                "0.11.0",
                staging_parent=self.staging_parent,
                subject="APG145: Repair hosted CI bootstrap and CodeQL validation",
            )
            self.assertEqual(tree, "t" * 40)
            self.assertEqual(commit, "c" * 40)


if __name__ == "__main__":
    unittest.main()
