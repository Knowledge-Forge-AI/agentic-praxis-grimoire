"""Confidentiality validation test cases for APG public release."""

from __future__ import annotations

from pathlib import Path
import sys
from unittest import mock

import apg_public_release as release


MARKER_USERS = "/" + "Users" + "/"
MARKER_FILE_URI = "file:" + "///"


class ReleaseConfidentialityCases:
    """Regression test cases verifying public release confidentiality scanning."""

    def test_confidentiality_marker_users_fails_before_configured_tests(self) -> None:
        repository = release.Repository(Path("candidate"), "a" * 40, "b" * 40)
        entry = release.Entry("100644", "blob", "c" * 40, b"src/module.py")
        content = f"prefix {MARKER_USERS} path\n".encode("utf-8")
        policy = {
            "validation_categories": ["confidentiality", "configured-tests"],
            "required_wrappers": [],
            "required_helpers": [],
            "required_test_entrypoints": ["src/test/sample.py"],
        }
        with (
            mock.patch.object(release, "tree_entries", return_value=(entry,)),
            mock.patch.object(release, "entry_bytes", return_value=content),
            mock.patch.object(release, "run_checked_command") as run_command,
        ):
            with self.assertRaisesRegex(
                release.ToolError,
                r"generic local-path confidentiality check failed: src/module\.py",
            ):
                release.validate_categories(repository, repository, policy, {}, "0.10.0")
            run_command.assert_not_called()

    def test_confidentiality_marker_file_uri_fails_before_configured_tests(self) -> None:
        repository = release.Repository(Path("candidate"), "a" * 40, "b" * 40)
        entry = release.Entry("100644", "blob", "c" * 40, b"docs/guide.md")
        content = f"see {MARKER_FILE_URI}local/file\n".encode("utf-8")
        policy = {
            "validation_categories": ["confidentiality", "configured-tests"],
            "required_wrappers": [],
            "required_helpers": [],
            "required_test_entrypoints": ["src/test/sample.py"],
        }
        with (
            mock.patch.object(release, "tree_entries", return_value=(entry,)),
            mock.patch.object(release, "entry_bytes", return_value=content),
            mock.patch.object(release, "run_checked_command") as run_command,
        ):
            with self.assertRaisesRegex(
                release.ToolError,
                r"generic local-path confidentiality check failed: docs/guide\.md",
            ):
                release.validate_categories(repository, repository, policy, {}, "0.10.0")
            run_command.assert_not_called()

    def test_confidentiality_clean_candidate_reaches_configured_tests(self) -> None:
        repository = release.Repository(Path("candidate"), "a" * 40, "b" * 40)
        entry = release.Entry("100644", "blob", "c" * 40, b"src/clean.py")
        content = b"def run():\n    return 42\n"
        policy = {
            "validation_categories": ["confidentiality", "configured-tests"],
            "required_wrappers": [],
            "required_helpers": [],
            "required_test_entrypoints": ["src/test/sample.py"],
        }
        with (
            mock.patch.object(release, "tree_entries", return_value=(entry,)),
            mock.patch.object(release, "entry_bytes", return_value=content),
            mock.patch.object(release, "run_checked_command") as run_command,
        ):
            release.validate_categories(repository, repository, policy, {}, "0.10.0")
            run_command.assert_called_once_with(
                [sys.executable, "src/test/sample.py"],
                repository.root,
                {},
            )

    def test_confidentiality_skips_binary_and_non_utf8_entries(self) -> None:
        repository = release.Repository(Path("candidate"), "a" * 40, "b" * 40)
        binary_entry = release.Entry("100644", "blob", "b" * 40, b"assets/image.png")
        clean_entry = release.Entry("100644", "blob", "c" * 40, b"src/clean.py")
        marker_entry = release.Entry("100644", "blob", "d" * 40, b"src/bad.py")
        binary_bytes = b"\x80\xff\xfe\x00\x01\x81"
        clean_bytes = b"clean code\n"
        marker_bytes = f"leak {MARKER_USERS} here\n".encode("utf-8")

        def fake_entry_bytes(_repo: release.Repository, entry: release.Entry) -> bytes:
            if entry.path == b"assets/image.png":
                return binary_bytes
            if entry.path == b"src/clean.py":
                return clean_bytes
            if entry.path == b"src/bad.py":
                return marker_bytes
            raise AssertionError(f"unexpected entry: {entry.display_path}")

        policy = {
            "validation_categories": ["confidentiality", "configured-tests"],
            "required_wrappers": [],
            "required_helpers": [],
            "required_test_entrypoints": ["src/test/sample.py"],
        }
        # 1. Binary entry followed by clean entry passes scan and reaches tests
        with (
            mock.patch.object(release, "tree_entries", return_value=(binary_entry, clean_entry)),
            mock.patch.object(release, "entry_bytes", side_effect=fake_entry_bytes),
            mock.patch.object(release, "run_checked_command") as run_command,
        ):
            release.validate_categories(repository, repository, policy, {}, "0.10.0")
            run_command.assert_called_once_with(
                [sys.executable, "src/test/sample.py"],
                repository.root,
                {},
            )

        # 2. Binary entry followed by marker entry still detects marker without crashing
        with (
            mock.patch.object(release, "tree_entries", return_value=(binary_entry, marker_entry)),
            mock.patch.object(release, "entry_bytes", side_effect=fake_entry_bytes),
            mock.patch.object(release, "run_checked_command") as run_command,
        ):
            with self.assertRaisesRegex(
                release.ToolError,
                r"generic local-path confidentiality check failed: src/bad\.py",
            ):
                release.validate_categories(repository, repository, policy, {}, "0.10.0")
            run_command.assert_not_called()

    def test_confidentiality_diagnostic_identifies_offending_path(self) -> None:
        repository = release.Repository(Path("candidate"), "a" * 40, "b" * 40)
        offending_path = "libexec/internal/credential_store.py"
        entry = release.Entry("100644", "blob", "c" * 40, offending_path.encode("utf-8"))
        content = f"target = '{MARKER_USERS}admin'\n".encode("utf-8")
        policy = {
            "validation_categories": ["confidentiality"],
            "required_wrappers": [],
            "required_helpers": [],
            "required_test_entrypoints": [],
        }
        with (
            mock.patch.object(release, "tree_entries", return_value=(entry,)),
            mock.patch.object(release, "entry_bytes", return_value=content),
        ):
            with self.assertRaises(release.ToolError) as direct_ctx:
                release.validate_confidentiality(repository)
            self.assertEqual(
                str(direct_ctx.exception),
                f"generic local-path confidentiality check failed: {offending_path}",
            )

            with self.assertRaises(release.ToolError) as category_ctx:
                release.validate_categories(repository, repository, policy, {}, "0.10.0")
            self.assertEqual(
                str(category_ctx.exception),
                f"generic local-path confidentiality check failed: {offending_path}",
            )
