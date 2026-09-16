#!/usr/bin/env python3
"""Integration tests for staging correction helpers and coverage export."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from src.test.apg_test_support import repository_root

REPO_ROOT = repository_root(__file__)
LIBEXEC = REPO_ROOT / "libexec"

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "bin" / "apg-public-release.int.test.py"
SPEC = importlib.util.spec_from_file_location("apg_public_release_integration_fixture", FIXTURE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load APG public release integration fixture")
FIXTURE_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FIXTURE_MODULE
SPEC.loader.exec_module(FIXTURE_MODULE)
release = FIXTURE_MODULE.release

if "apg_staging_correction" in sys.modules:
    staging_correction = sys.modules["apg_staging_correction"]
else:
    CORRECTION_SPEC = importlib.util.spec_from_file_location(
        "apg_staging_correction", LIBEXEC / "apg_staging_correction.py"
    )
    if CORRECTION_SPEC is None or CORRECTION_SPEC.loader is None:
        raise RuntimeError("could not load apg_staging_correction")
    staging_correction = importlib.util.module_from_spec(CORRECTION_SPEC)
    sys.modules["apg_staging_correction"] = staging_correction
    CORRECTION_SPEC.loader.exec_module(staging_correction)

if "apg_test" in sys.modules:
    apg_test = sys.modules["apg_test"]
else:
    TEST_SPEC = importlib.util.spec_from_file_location("apg_test", LIBEXEC / "apg_test.py")
    if TEST_SPEC is None or TEST_SPEC.loader is None:
        raise RuntimeError("could not load apg_test")
    apg_test = importlib.util.module_from_spec(TEST_SPEC)
    sys.modules["apg_test"] = apg_test
    TEST_SPEC.loader.exec_module(apg_test)


class TestRunCheckedCommandIntegration(unittest.TestCase):
    """Exercise run_checked_command with real child processes and output logging."""

    def test_run_checked_command_without_log_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-cmd-") as temp_dir:
            work = Path(temp_dir)
            old_log = os.environ.pop("APG_VALIDATION_OUTPUT_LOG", None)
            try:
                res = staging_correction.run_checked_command(
                    [sys.executable, "-c", "import sys; sys.stdout.write('ok')"],
                    work,
                )
                self.assertIsNone(res)
            finally:
                if old_log is not None:
                    os.environ["APG_VALIDATION_OUTPUT_LOG"] = old_log

    def test_run_checked_command_with_log_success_and_contents(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-cmd-") as temp_dir:
            work = Path(temp_dir) / "work"
            work.mkdir()
            log_path = Path(temp_dir) / "output.log"
            old_log = os.environ.get("APG_VALIDATION_OUTPUT_LOG")
            os.environ["APG_VALIDATION_OUTPUT_LOG"] = str(log_path)
            try:
                staging_correction.run_checked_command(
                    [sys.executable, "-c", "print('command-stdout'); import sys; sys.stderr.write('command-stderr\\n')"],
                    work,
                )
            finally:
                if old_log is not None:
                    os.environ["APG_VALIDATION_OUTPUT_LOG"] = old_log
                else:
                    os.environ.pop("APG_VALIDATION_OUTPUT_LOG", None)
            self.assertTrue(log_path.is_file())
            content = log_path.read_text(encoding="utf-8")
            self.assertIn("--- COMMAND: ", content)
            self.assertIn("RETURNCODE: 0", content)
            self.assertIn("command-stdout", content)
            self.assertIn("command-stderr", content)
            self.assertIn("--- END COMMAND ---", content)

    def test_run_checked_command_refuses_relative_log_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-cmd-") as temp_dir:
            work = Path(temp_dir)
            old_log = os.environ.get("APG_VALIDATION_OUTPUT_LOG")
            os.environ["APG_VALIDATION_OUTPUT_LOG"] = "relative-path.log"
            try:
                with self.assertRaises(release.ToolError) as ctx:
                    staging_correction.run_checked_command(
                        [sys.executable, "-c", "print('ok')"], work
                    )
                self.assertIn("must be absolute", str(ctx.exception))
            finally:
                if old_log is not None:
                    os.environ["APG_VALIDATION_OUTPUT_LOG"] = old_log
                else:
                    os.environ.pop("APG_VALIDATION_OUTPUT_LOG", None)

    def test_run_checked_command_refuses_overlapping_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-cmd-") as temp_dir:
            work = Path(temp_dir) / "work"
            work.mkdir()
            overlap_log = work / "log.txt"
            old_log = os.environ.get("APG_VALIDATION_OUTPUT_LOG")
            os.environ["APG_VALIDATION_OUTPUT_LOG"] = str(overlap_log)
            try:
                with self.assertRaises(release.ToolError) as ctx:
                    staging_correction.run_checked_command(
                        [sys.executable, "-c", "print('ok')"],
                        work,
                        environment={"APG12_PUBLIC_V01_ROOT": str(work)},
                    )
                self.assertIn("cannot overlap repository or validation roots", str(ctx.exception))
            finally:
                if old_log is not None:
                    os.environ["APG_VALIDATION_OUTPUT_LOG"] = old_log
                else:
                    os.environ.pop("APG_VALIDATION_OUTPUT_LOG", None)

    def test_run_checked_command_nonzero_exit_raises_tool_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-cmd-") as temp_dir:
            work = Path(temp_dir)
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.run_checked_command(
                    [sys.executable, "-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(7)"],
                    work,
                )
            self.assertIn("configured validation failed", str(ctx.exception))
            self.assertIn("boom", str(ctx.exception))

    def test_run_checked_command_os_error_raises_with_basename(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-cmd-") as temp_dir:
            work = Path(temp_dir)
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.run_checked_command(["/no/such/binary_executable"], work)
            self.assertIn("configured validation could not run: binary_executable", str(ctx.exception))

    def test_run_checked_command_custom_fail_callable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-cmd-") as temp_dir:
            work = Path(temp_dir)
            messages: list[str] = []

            def _custom_fail(msg: str) -> None:
                messages.append(msg)
                raise RuntimeError(f"custom:{msg}")

            with self.assertRaises(RuntimeError) as ctx:
                staging_correction.run_checked_command(
                    [sys.executable, "-c", "import sys; sys.exit(3)"],
                    work,
                    fail=_custom_fail,
                )
            self.assertTrue(str(ctx.exception).startswith("custom:configured validation failed"))
            self.assertEqual(len(messages), 1)


class TestVerifyCandidateLineageIntegration(unittest.TestCase):
    """Exercise lineage and branch verification using real Git repositories."""

    def _init_repo(self, path: Path) -> None:
        release.run_git(path.parent, ["init", "-q", "-b", "main", str(path)])
        release.run_git(path, ["config", "user.name", "APG Integration"])
        release.run_git(path, ["config", "user.email", "apg-int@example.invalid"])

    def test_verify_candidate_lineage_correction_mode_success_and_refusals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-lineage-") as temp_dir:
            root = Path(temp_dir)
            base_dir = root / "base"
            self._init_repo(base_dir)
            (base_dir / "base.txt").write_text("base\n", encoding="utf-8")
            release.run_git(base_dir, ["add", "base.txt"])
            release.run_git(base_dir, ["commit", "-q", "-m", "base commit"])
            base_repo = release.resolve_repository(base_dir, "base")

            cand_dir = root / "candidate"
            release.run_git(root, ["clone", "-q", str(base_dir), str(cand_dir)])
            release.run_git(cand_dir, ["config", "user.name", "APG Integration"])
            release.run_git(cand_dir, ["config", "user.email", "apg-int@example.invalid"])
            release.run_git(cand_dir, ["checkout", "-q", "-b", "staging"])

            # Parent 1: staging parent
            (cand_dir / "parent.txt").write_text("parent\n", encoding="utf-8")
            release.run_git(cand_dir, ["add", "parent.txt"])
            release.run_git(cand_dir, ["commit", "-q", "-m", "staging parent commit"])
            staging_parent_sha = release.text_git(cand_dir, ["rev-parse", "HEAD"])

            # Child commit: staging correction
            (cand_dir / "correction.txt").write_text("correction\n", encoding="utf-8")
            release.run_git(cand_dir, ["add", "correction.txt"])
            release.run_git(cand_dir, ["commit", "-q", "-m", "Release v0.11.0 staging correction"])
            cand_repo = release.resolve_repository(cand_dir, "candidate")

            # Positive case: valid staging correction
            staging_correction.verify_candidate_lineage(
                cand_repo,
                base_repo,
                "0.11.0",
                allow_staging_correction=True,
                correction_parent=staging_parent_sha,
                correction_subject="Release v0.11.0 staging correction",
            )

            # Positive case: correction_subject is None (checks non-empty subject)
            staging_correction.verify_candidate_lineage(
                cand_repo,
                base_repo,
                "0.11.0",
                allow_staging_correction=True,
                correction_parent=staging_parent_sha,
                correction_subject=None,
            )

            # Refusal 1: missing correction parent
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.verify_candidate_lineage(
                    cand_repo,
                    base_repo,
                    "0.11.0",
                    allow_staging_correction=True,
                    correction_parent=None,
                )
            self.assertIn("requires an explicit correction_parent", str(ctx.exception))

            # Refusal 2: parent mismatch
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.verify_candidate_lineage(
                    cand_repo,
                    base_repo,
                    "0.11.0",
                    allow_staging_correction=True,
                    correction_parent="0" * 40,
                )
            self.assertIn("parent mismatch", str(ctx.exception))

            # Refusal 3: wrong subject
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.verify_candidate_lineage(
                    cand_repo,
                    base_repo,
                    "0.11.0",
                    allow_staging_correction=True,
                    correction_parent=staging_parent_sha,
                    correction_subject="Wrong Subject",
                )
            self.assertIn("candidate release subject is incorrect", str(ctx.exception))

            # Refusal 4: wrong branch
            release.run_git(cand_dir, ["checkout", "-q", "-b", "feature-branch"])
            cand_repo = release.resolve_repository(cand_dir, "candidate")
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.verify_candidate_lineage(
                    cand_repo,
                    base_repo,
                    "0.11.0",
                    allow_staging_correction=True,
                    correction_parent=staging_parent_sha,
                )
            self.assertIn("candidate is on the wrong release branch", str(ctx.exception))

            # Refusal 5: custom fail callable
            with self.assertRaises(RuntimeError):
                staging_correction.verify_candidate_lineage(
                    cand_repo,
                    base_repo,
                    "0.11.0",
                    allow_staging_correction=True,
                    correction_parent=staging_parent_sha,
                    fail=lambda msg: (_ for _ in ()).throw(RuntimeError(msg)),
                )

    def test_verify_candidate_lineage_non_correction_mode_success_and_refusals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-lineage-") as temp_dir:
            root = Path(temp_dir)
            base_dir = root / "base"
            self._init_repo(base_dir)
            (base_dir / "base.txt").write_text("base\n", encoding="utf-8")
            release.run_git(base_dir, ["add", "base.txt"])
            release.run_git(base_dir, ["commit", "-q", "-m", "base commit"])
            base_repo = release.resolve_repository(base_dir, "base")

            cand_dir = root / "candidate"
            release.run_git(root, ["clone", "-q", str(base_dir), str(cand_dir)])
            release.run_git(cand_dir, ["config", "user.name", "APG Integration"])
            release.run_git(cand_dir, ["config", "user.email", "apg-int@example.invalid"])
            release.run_git(cand_dir, ["checkout", "-q", "-b", "staging"])

            # Add exactly one commit after base
            (cand_dir / "release.txt").write_text("release\n", encoding="utf-8")
            release.run_git(cand_dir, ["add", "release.txt"])
            release.run_git(cand_dir, ["commit", "-q", "-m", "Release v0.11.0"])
            cand_repo = release.resolve_repository(cand_dir, "candidate")

            # Positive: untagged mode on staging
            staging_correction.verify_candidate_lineage(
                cand_repo,
                base_repo,
                "0.11.0",
                untagged=True,
                allow_staging_correction=False,
            )

            # Positive: tagged mode on release/0.11.0
            release.run_git(cand_dir, ["checkout", "-q", "-b", "release/0.11.0"])
            cand_repo = release.resolve_repository(cand_dir, "candidate")
            staging_correction.verify_candidate_lineage(
                cand_repo,
                base_repo,
                "0.11.0",
                untagged=False,
                allow_staging_correction=False,
            )

            # Refusal: commit after base has wrong subject
            (cand_dir / "bad_subject.txt").write_text("bad\n", encoding="utf-8")
            release.run_git(cand_dir, ["add", "bad_subject.txt"])
            release.run_git(cand_dir, ["commit", "-q", "--amend", "-m", "Wrong Subject"])
            cand_repo = release.resolve_repository(cand_dir, "candidate")
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.verify_candidate_lineage(
                    cand_repo,
                    base_repo,
                    "0.11.0",
                    untagged=False,
                    allow_staging_correction=False,
                )
            self.assertIn("candidate release subject is incorrect", str(ctx.exception))

            # Refusal: wrong branch
            release.run_git(cand_dir, ["checkout", "-q", "-b", "other"])
            cand_repo = release.resolve_repository(cand_dir, "candidate")
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.verify_candidate_lineage(
                    cand_repo,
                    base_repo,
                    "0.11.0",
                    untagged=False,
                    allow_staging_correction=False,
                )
            self.assertIn("candidate is on the wrong release branch", str(ctx.exception))

            # Refusal: multiple commits after base
            release.run_git(cand_dir, ["checkout", "-q", "release/0.11.0"])
            (cand_dir / "extra.txt").write_text("extra\n", encoding="utf-8")
            release.run_git(cand_dir, ["add", "extra.txt"])
            release.run_git(cand_dir, ["commit", "-q", "-m", "Release v0.11.0"])
            cand_repo = release.resolve_repository(cand_dir, "candidate")
            with self.assertRaises(release.ToolError) as ctx:
                staging_correction.verify_candidate_lineage(
                    cand_repo,
                    base_repo,
                    "0.11.0",
                    untagged=False,
                    allow_staging_correction=False,
                )
            self.assertIn("does not have the public base as sole parent", str(ctx.exception))


class TestBuildUntaggedCandidateIntegration(unittest.TestCase):
    """Exercise build_untagged_candidate boundary checks."""

    def test_build_untagged_candidate_version_mismatch_refusal(self) -> None:
        with self.assertRaises(release.InvocationError) as ctx:
            staging_correction.build_untagged_candidate(
                None, None, Path("/tmp/ignored"), "0.10.0"
            )
        self.assertIn("untagged candidate mode is only available for v0.11.0", str(ctx.exception))

    def test_build_untagged_candidate_staging_parent_refusals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-build-") as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            base_dir = root / "base"
            release.run_git(root, ["init", "-q", "-b", "main", str(source_dir)])
            release.run_git(root, ["init", "-q", "-b", "main", str(base_dir)])
            for d in (source_dir, base_dir):
                release.run_git(d, ["config", "user.name", "APG Integration"])
                release.run_git(d, ["config", "user.email", "apg-int@example.invalid"])
                (d / "README.md").write_text("test\n", encoding="utf-8")
                release.run_git(d, ["add", "."])
                release.run_git(d, ["commit", "-q", "-m", "init"])

            source_repo = release.resolve_repository(source_dir, "source")
            base_repo = release.resolve_repository(base_dir, "base")

            # Mock lineage verification to reach staging branch / parent checks
            with mock.patch.object(release, "verify_public_release_lineage"):
                with mock.patch.object(release, "validate_repository_separation"):
                    with mock.patch.object(release, "load_policy", return_value={}):
                        with mock.patch.object(release, "public_candidate_entries", return_value=()):
                            with mock.patch.object(release, "validate_versioned_policy_exclusions"):
                                with mock.patch.object(release, "validate_critical"):
                                    with mock.patch.object(release, "validate_public_symlinks"):
                                        with mock.patch.object(release, "validate_output_path"):
                                            # Non-ancestor staging parent refusal
                                            with self.assertRaises(release.ToolError) as ctx:
                                                staging_correction.build_untagged_candidate(
                                                    source_repo,
                                                    base_repo,
                                                    root / "candidate",
                                                    "0.11.0",
                                                    staging_parent="0" * 40,
                                                )
                                            self.assertIn("public base is not an ancestor of staging parent", str(ctx.exception))

                                            # Staging parent is None but base already has staging branch
                                            release.run_git(base_dir, ["branch", "staging"])
                                            with self.assertRaises(release.ToolError) as ctx:
                                                staging_correction.build_untagged_candidate(
                                                    source_repo,
                                                    base_repo,
                                                    root / "candidate",
                                                    "0.11.0",
                                                    staging_parent=None,
                                                )
                                            self.assertIn("public base already contains the staging branch", str(ctx.exception))


class TestNormaliseRequiredChecksIntegration(unittest.TestCase):
    """Exercise normalise_required_checks with valid inputs and refusal conditions."""

    def test_normalise_mapping_input(self) -> None:
        result = staging_correction.normalise_required_checks({"test": "success", "build": "success"})
        self.assertEqual(result, {"build": "success", "test": "success"})

    def test_normalise_sequence_input(self) -> None:
        result = staging_correction.normalise_required_checks(["test", "lint"])
        self.assertEqual(result, {"lint": "success", "test": "success"})

    def test_normalise_string_input_rejected(self) -> None:
        with self.assertRaises(release.InvocationError) as ctx:
            staging_correction.normalise_required_checks("single-check")
        self.assertIn("must be a sequence of names", str(ctx.exception))

    def test_normalise_empty_input_rejected(self) -> None:
        with self.assertRaises(release.InvocationError) as ctx:
            staging_correction.normalise_required_checks([])
        self.assertIn("at least one approved required check is required", str(ctx.exception))

    def test_normalise_invalid_name_rejected(self) -> None:
        with self.assertRaises(release.InvocationError) as ctx:
            staging_correction.normalise_required_checks(["   "])
        self.assertIn("must be nonempty strings", str(ctx.exception))

    def test_normalise_non_success_status_rejected(self) -> None:
        with self.assertRaises(release.ToolError) as ctx:
            staging_correction.normalise_required_checks({"test": "failure"})
        self.assertIn("approved required check did not succeed: test", str(ctx.exception))

    def test_normalise_duplicate_rejected(self) -> None:
        with self.assertRaises(release.InvocationError) as ctx:
            staging_correction.normalise_required_checks(["build", "build"])
        self.assertIn("contain a duplicate: build", str(ctx.exception))

    def test_normalise_custom_callables(self) -> None:
        def _custom_unsafe(msg: str) -> None:
            raise ValueError(f"unsafe:{msg}")

        def _custom_fail(msg: str) -> None:
            raise TypeError(f"fail:{msg}")

        with self.assertRaises(ValueError) as ctx:
            staging_correction.normalise_required_checks([], unsafe=_custom_unsafe)
        self.assertTrue(str(ctx.exception).startswith("unsafe:at least one"))

        with self.assertRaises(TypeError) as ctx:
            staging_correction.normalise_required_checks({"a": "bad"}, fail=_custom_fail)
        self.assertTrue(str(ctx.exception).startswith("fail:approved required check did not succeed"))


class TestApgTestCoverageExportIntegration(unittest.TestCase):
    """Exercise coverage export admission and copy operations in apg_test."""

    def test_admit_export_destination_success_and_refusals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-export-") as temp_dir:
            temp_root = Path(temp_dir)
            target = temp_root / "coverage-export"

            # Positive: safe external target
            admitted = apg_test.admit_export_destination(REPO_ROOT, target)
            self.assertEqual(admitted, target.resolve())

            # Refusal 1: git metadata
            with self.assertRaises(apg_test.InvocationError) as ctx:
                apg_test.admit_export_destination(REPO_ROOT, REPO_ROOT / ".git" / "coverage")
            self.assertIn("cannot target Git metadata", str(ctx.exception))

            # Refusal 2: repo root
            with self.assertRaises(apg_test.InvocationError) as ctx:
                apg_test.admit_export_destination(REPO_ROOT, REPO_ROOT)
            self.assertIn("cannot target repository root", str(ctx.exception))

            # Refusal 3: symlink
            symlink_target = temp_root / "symlink-target"
            symlink_target.symlink_to(temp_root)
            with self.assertRaises(apg_test.InvocationError) as ctx:
                apg_test.admit_export_destination(REPO_ROOT, symlink_target)
            self.assertIn("cannot target a symlink", str(ctx.exception))

    def test_export_coverage_artifacts_copies_expected_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-int-export-") as temp_dir:
            temp_root = Path(temp_dir)
            artifacts = temp_root / "artifacts"
            export_dir = temp_root / "exported"

            # Create mock artifacts
            unit_dir = artifacts / "unit"
            int_dir = artifacts / "integration"
            unit_dir.mkdir(parents=True)
            int_dir.mkdir(parents=True)

            (unit_dir / "unit.json").write_text('{"suite":"unit"}', encoding="utf-8")
            (unit_dir / "unit.workers.jsonl").write_text('{"worker":1}\n', encoding="utf-8")
            (int_dir / "integration.json").write_text('{"suite":"integration"}', encoding="utf-8")
            (int_dir / "integration.children.jsonl").write_text('{"child":1}\n', encoding="utf-8")
            (artifacts / "combined.json").write_text('{"suite":"combined"}', encoding="utf-8")

            # Call export
            apg_test._export_coverage_artifacts(
                artifacts,
                export_dir,
                ["unit", "integration"],
                "combined",
            )

            # Assert exported files exist with matching content
            self.assertTrue((export_dir / "unit" / "unit.json").is_file())
            self.assertTrue((export_dir / "unit" / "unit.workers.jsonl").is_file())
            self.assertTrue((export_dir / "integration" / "integration.json").is_file())
            self.assertTrue((export_dir / "integration" / "integration.children.jsonl").is_file())
            self.assertTrue((export_dir / "combined.json").is_file())
            self.assertEqual(
                json.loads((export_dir / "combined.json").read_text(encoding="utf-8")),
                {"suite": "combined"},
            )


if __name__ == "__main__":
    unittest.main()
