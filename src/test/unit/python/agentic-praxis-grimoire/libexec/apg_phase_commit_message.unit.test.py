#!/usr/bin/env python3
"""Focused unit tests for APG formal-phase commit-message validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
FIXTURE_ROOT = REPOSITORY_ROOT / "src" / "test" / "fixtures" / "apg26a"
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_phase_commit_message as checker  # noqa: E402


VALID_MESSAGE = b"""APG26A: Enforce formal-phase commit messages

Scope:
- Add the APG phase commit-message checker and focused tests.

Result:
- Subject-only formal phase messages are rejected.

Verification:
- Focused unit and integration tests pass.

Not run:
- none
"""


class APGPhaseCommitMessageUnitTests(unittest.TestCase):
    """Exercise the deterministic message validator and renderers."""

    @staticmethod
    def codes(message: bytes, phase: str = "APG26A") -> set[str]:
        result = checker.validate_message(phase, message)
        return {diagnostic.code for diagnostic in result.diagnostics}

    def test_valid_apg26a_message_passes(self) -> None:
        result = checker.validate_message("APG26A", VALID_MESSAGE)
        self.assertTrue(result.passed)
        self.assertEqual(result.diagnostics, ())

    def test_subject_only_apg26_regression_fixture_fails(self) -> None:
        message = (FIXTURE_ROOT / "apg26-subject-only.message.txt").read_bytes()
        codes = self.codes(message, phase="APG26")
        self.assertIn("APGCM006", codes)
        self.assertIn("APGCM007", codes)

    def test_wrong_phase_and_empty_result_fail(self) -> None:
        wrong_phase = VALID_MESSAGE.replace(b"APG26A:", b"APG27:", 1)
        empty_result = VALID_MESSAGE.replace(
            b"APG26A: Enforce formal-phase commit messages",
            b"APG26A: ",
            1,
        )
        self.assertIn("APGCM004", self.codes(wrong_phase))
        self.assertIn("APGCM005", self.codes(empty_result))

    def test_missing_and_duplicate_sections_fail_cardinality(self) -> None:
        missing = VALID_MESSAGE.replace(
            b"Verification:\n- Focused unit and integration tests pass.\n\n",
            b"",
            1,
        )
        duplicate = VALID_MESSAGE.replace(
            b"Result:\n- Subject-only formal phase messages are rejected.\n",
            b"Result:\n- Subject-only formal phase messages are rejected.\n"
            b"Result:\n- The duplicate is rejected.\n",
            1,
        )
        self.assertIn("APGCM007", self.codes(missing))
        self.assertIn("APGCM007", self.codes(duplicate))

    def test_out_of_order_sections_fail(self) -> None:
        result_section = (
            b"Result:\n- Subject-only formal phase messages are rejected.\n\n"
        )
        verification_section = (
            b"Verification:\n- Focused unit and integration tests pass.\n\n"
        )
        out_of_order = VALID_MESSAGE.replace(result_section, b"", 1).replace(
            verification_section,
            verification_section + result_section,
            1,
        )
        self.assertIn("APGCM008", self.codes(out_of_order))

    def test_empty_section_and_nonlist_content_fail(self) -> None:
        empty = VALID_MESSAGE.replace(
            b"Result:\n- Subject-only formal phase messages are rejected.\n\n",
            b"Result:\n\n",
            1,
        )
        nonlist = VALID_MESSAGE.replace(
            b"- Subject-only formal phase messages are rejected.",
            b"Subject-only formal phase messages are rejected.",
            1,
        )
        self.assertIn("APGCM009", self.codes(empty))
        self.assertIn("APGCM010", self.codes(nonlist))

    def test_missing_blank_line_fails(self) -> None:
        message = VALID_MESSAGE.replace(b"messages\n\nScope:", b"messages\nScope:", 1)
        self.assertIn("APGCM006", self.codes(message))

    def test_not_run_none_is_valid(self) -> None:
        self.assertTrue(checker.validate_message("APG26A", VALID_MESSAGE).passed)

    def test_malformed_controls_and_invalid_utf8_fail_without_content(self) -> None:
        controlled = VALID_MESSAGE.replace(b"Scope:", b"Scope:\x00", 1)
        controlled_result = checker.validate_message("APG26A", controlled)
        self.assertIn(
            "APGCM002",
            {diagnostic.code for diagnostic in controlled_result.diagnostics},
        )
        self.assertNotIn("\x00", checker.render_text(controlled_result, "message-file"))
        self.assertIn("APGCM001", self.codes(VALID_MESSAGE + b"\xff"))

    def test_phase_argument_requires_canonical_phase_identity(self) -> None:
        self.assertEqual(checker.phase_argument("APG26A"), "APG26A")
        for value in ("apg26a", "deadbeef", "APG26AA"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    checker.phase_argument(value)

    def test_revision_argument_rejects_empty_long_and_control_bearing_values(self) -> None:
        self.assertEqual(checker.revision_argument("HEAD"), "HEAD")
        for value in ("", "x" * 1025, "bad\nrevision", "bad\x7frevision"):
            with self.subTest(value=value[:20]), self.assertRaises(argparse.ArgumentTypeError):
                checker.revision_argument(value)

    def test_empty_message_and_unsafe_message_file_fail_closed(self) -> None:
        self.assertIn("APGCM003", self.codes(b""))
        with self.assertRaises(checker.RepositoryFailure):
            checker._read_message_file(Path("missing-message"))
        with mock.patch.object(Path, "is_file", return_value=True), mock.patch.object(
            Path, "is_symlink", return_value=True
        ):
            with self.assertRaises(checker.RepositoryFailure):
                checker._read_message_file(Path("symlink-message"))

    def test_git_execution_and_commit_object_failures_are_bounded(self) -> None:
        with mock.patch.object(checker.subprocess, "run", side_effect=OSError("missing")):
            with self.assertRaises(checker.RepositoryFailure):
                checker._run_git(("status",))
        unresolved = mock.Mock(returncode=1, stdout=b"", stderr=b"")
        with mock.patch.object(checker, "_run_git", return_value=unresolved):
            with self.assertRaises(checker.RepositoryFailure):
                checker._read_commit_message("HEAD")
        resolved = mock.Mock(returncode=0, stdout=(b"a" * 40) + b"\n", stderr=b"")
        incomplete = mock.Mock(returncode=0, stdout=b"tree " + b"b" * 40, stderr=b"")
        with mock.patch.object(checker, "_run_git", side_effect=(resolved, incomplete)):
            with self.assertRaises(checker.RepositoryFailure):
                checker._read_commit_message("HEAD")

    def test_text_and_json_output_are_deterministic(self) -> None:
        result = checker.validate_message("APG26A", VALID_MESSAGE)
        self.assertEqual(
            checker.render_text(result, "message-file"),
            "PASS APG phase commit message: APG26A (message-file)\n",
        )
        payload = json.loads(checker.render_json(result, "message-file"))
        self.assertEqual(
            payload,
            {
                "diagnostics": [],
                "phase": "APG26A",
                "schema_version": 1,
                "source": "message-file",
                "status": "pass",
            },
        )


if __name__ == "__main__":
    unittest.main()
