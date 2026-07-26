#!/usr/bin/env python3
"""Focused unit tests for the Python agent-report core."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

from src.test.apg_test_support import repository_root
from unittest import mock


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from agent_report import models, rendering, safety  # noqa: E402
from agent_report.diff import compute_state_report_id  # noqa: E402


class AgentReportUnitTests(unittest.TestCase):
    """Exercise deterministic models, rendering, parsing, and validation."""

    def test_payload_ending_preserves_empty_and_adds_one_required_newline(self) -> None:
        self.assertEqual(rendering.ensure_payload_ending(b""), b"")
        self.assertEqual(rendering.ensure_payload_ending(b"payload"), b"payload\n")
        self.assertEqual(rendering.ensure_payload_ending(b"payload\n"), b"payload\n")
        self.assertEqual(rendering.ensure_payload_ending(b"payload\n\n"), b"payload\n\n")

    def test_rendering_rejects_unsafe_section_and_record_fields(self) -> None:
        for name in ("", "bad\nname", "nonascii-\N{SNOWMAN}"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                rendering.render_section(name, b"payload")
        for value in ("", "bad\nfield"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rendering._field(value)

    def test_low_level_line_and_header_parsers_fail_closed(self) -> None:
        self.assertIsNone(rendering._read_line(b"unterminated", 0))
        self.assertIsNone(rendering._read_lines(b"one\n", 0, 2))
        record = models.ReportRecord("type", 1, "id", "project", "phase", b"payload\n")
        encoded = rendering.build_record(record)
        lines = encoded.splitlines()[:12]
        for index, replacement in (
            (0, b"bad envelope"),
            (2, b"bad format"),
            (11, b"bad boundary"),
            (4, b"bad prefix"),
            (5, b"RECORD-FORMAT-VERSION: invalid"),
            (9, b"PAYLOAD-SHA256: invalid"),
            (10, b"PAYLOAD-SIZE-BYTES: -1"),
        ):
            changed = list(lines)
            changed[index] = replacement
            with self.subTest(index=index):
                self.assertIsNone(rendering._parse_header(changed))

    def test_canonical_parser_rejects_incomplete_gaps_and_suffixes(self) -> None:
        record = models.ReportRecord("type", 1, "id", "project", "phase", b"payload\n")
        encoded = rendering.build_record(record)
        with self.assertRaises(rendering.RecordParseError):
            rendering.parse_canonical_records(encoded[:-1])
        with self.assertRaises(rendering.RecordParseError):
            rendering.parse_canonical_records(encoded + b"suffix")
        with self.assertRaises(rendering.RecordParseError):
            rendering.parse_canonical_records(encoded + b"gap" + encoded)

    def test_section_rendering_preserves_untrusted_marker_bytes(self) -> None:
        body = b"BEGIN AGENT-REPORT-RECORD\nEND AGENT-REPORT-RECORD\n"
        rendered = rendering.render_section("PATCH", body)
        self.assertIn(body, rendered)
        self.assertTrue(rendered.startswith(rendering.SECTION_LINE + b"\nBEGIN PATCH\n"))
        self.assertTrue(rendered.endswith(b"END PATCH\n" + rendering.SECTION_LINE + b"\n"))

    def test_common_envelope_round_trips_a_complete_record(self) -> None:
        payload = rendering.render_section("BODY", b"exact\x00bytes\n")
        record = models.ReportRecord(
            record_type="git-diff-report",
            format_version=1,
            record_id="GIT-DIFF-REPORT-" + "1" * 64,
            project="example",
            phase="APG27",
            payload=payload,
        )
        encoded = rendering.build_record(record)
        parsed = rendering.parse_complete_records(encoded)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].record, record)
        self.assertEqual(parsed[0].start, 0)
        self.assertEqual(parsed[0].end, len(encoded))
        self.assertEqual(parsed[0].payload_sha256, hashlib.sha256(payload).hexdigest())

    def test_parser_ignores_legacy_prefix_and_payload_marker_text(self) -> None:
        payload = b"legacy-like\n" + rendering.ENVELOPE_LINE + b"\nEND AGENT-REPORT-RECORD\n"
        record = models.ReportRecord(
            record_type="operational-report",
            format_version=1,
            record_id="OPERATIONAL-REPORT-" + "2" * 64,
            project="example",
            phase="APG27",
            payload=payload,
        )
        prefix = b"historical prefix without a terminal newline"
        encoded = prefix + b"\n" + rendering.build_record(record)
        parsed = rendering.parse_complete_records(encoded)
        self.assertEqual([item.record for item in parsed], [record])

    def test_parser_rejects_truncated_or_digest_mismatched_records(self) -> None:
        record = models.ReportRecord(
            record_type="git-show-report",
            format_version=2,
            record_id="GIT-SHOW-REPORT-" + "3" * 40,
            project="example",
            phase="APG27",
            payload=b"payload\n",
        )
        encoded = rendering.build_record(record)
        self.assertEqual(rendering.parse_complete_records(encoded[:-1]), ())
        corrupted = encoded.replace(b"payload\n", b"payloae\n", 1)
        self.assertEqual(rendering.parse_complete_records(corrupted), ())

    def test_state_report_id_is_deterministic_and_domain_separated(self) -> None:
        fields = {
            "head": "a" * 40,
            "index": "b" * 64,
            "status": "c" * 64,
            "staged": "d" * 64,
            "unstaged": "e" * 64,
            "changed": "f" * 64,
            "numstat": "0" * 64,
            "patch": "1" * 64,
        }
        first = compute_state_report_id(fields)
        second = compute_state_report_id(dict(reversed(tuple(fields.items()))))
        self.assertEqual(first, second)
        self.assertRegex(first, r"^GIT-DIFF-REPORT-[0-9a-f]{64}$")
        changed = dict(fields, patch="2" * 64)
        self.assertNotEqual(first, compute_state_report_id(changed))

    def test_ticket_and_status_document_validation_are_bounded(self) -> None:
        self.assertEqual(safety.validate_ticket("APG27"), "APG27")
        self.assertEqual(safety.validate_status_doc(None), "NONE")
        self.assertEqual(safety.validate_status_doc("docs/status/example.md"), "docs/status/example.md")
        for value in ("../APG27", ".", "APG27/child", "A" * 129):
            with self.subTest(ticket=value):
                with self.assertRaises(safety.UsageError):
                    safety.validate_ticket(value)
        for value in (
            "/absolute.md",
            "../escape.md",
            "docs/../escape.md",
            "docs//nested.md",
            "docs\x00bad",
        ):
            with self.subTest(status_doc=value):
                with self.assertRaises(safety.UsageError):
                    safety.validate_status_doc(value)
        repository = Path("repository")
        with mock.patch.object(safety.os, "name", "nt"):
            self.assertTrue(
                safety.source_value_is_absolute(r"C:\evidence\operational-report.txt")
            )
            with self.assertRaisesRegex(
                safety.ReportError,
                "Windows report replacement safety",
            ):
                safety.Destination(repository, "WINDOWS")

    def test_source_path_branch_helpers_validate_spelling_location_and_destination(self) -> None:
        safety._validate_source_spelling(None)
        safety._validate_source_spelling("/private/tmp/report.txt")
        with self.assertRaises(safety.ReportError):
            safety._validate_source_spelling("/private/tmp/report.txt/")
        with self.assertRaises(safety.UsageError):
            safety._validate_source_location(Path("relative-report.txt"))
        with self.assertRaises(safety.UsageError):
            safety._validate_source_location(Path("/private/tmp/../report.txt"))

        with tempfile.TemporaryDirectory(prefix="apg27a-source-helper-") as temporary:
            source = Path(temporary) / "source.txt"
            source.write_text("source\n", encoding="utf-8")
            source.chmod(0o600)
            self.assertEqual(
                safety.validate_source_path(source, source_value=os.fspath(source)),
                source.lstat(),
            )
            safety._validate_source_destination(source, None)
            safety._validate_source_destination(source, source.with_name("missing.txt"))
            with self.assertRaises(safety.ReportError):
                safety._validate_source_destination(source, source)
            with self.assertRaises(safety.ReportError):
                safety.validate_source_path(source, source, source_value=os.fspath(source))
            with self.assertRaises(safety.ReportError):
                safety.validate_source_path(
                    source.with_name("missing.txt"),
                    source_value=os.fspath(source.with_name("missing.txt")),
                )

    def test_source_path_branch_helpers_validate_metadata_and_platform(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg27a-source-metadata-") as temporary:
            source = Path(temporary) / "source.txt"
            source.write_text("source\n", encoding="utf-8")
            source.chmod(0o600)
            metadata = safety._source_metadata(source)
            self.assertEqual(safety._validate_source_metadata(source, metadata), metadata)

            source.chmod(0o644)
            with self.assertRaises(safety.ReportError):
                safety.validate_source_path(source, source_value=os.fspath(source))
            with self.assertRaises(safety.ReportError):
                safety._source_metadata(source.with_name("missing.txt"))

            directory = Path(temporary) / "directory"
            directory.mkdir()
            with self.assertRaises(safety.ReportError):
                safety.validate_source_path(directory, source_value=os.fspath(directory))

            target = Path(temporary) / "target.txt"
            target.write_text("target\n", encoding="utf-8")
            target.chmod(0o600)
            symlink = Path(temporary) / "source-link"
            symlink.symlink_to(target)
            with self.assertRaises(safety.ReportError):
                safety.validate_source_path(symlink, source_value=os.fspath(symlink))

            linked = Path(temporary) / "linked.txt"
            os.link(target, linked)
            with self.assertRaises(safety.ReportError):
                safety.validate_source_path(target, source_value=os.fspath(target))

            wrong_owner = mock.Mock(
                st_mode=stat.S_IFREG | 0o600,
                st_uid=os.getuid() + 1,
                st_nlink=1,
            )
            with mock.patch.object(safety, "_source_metadata", return_value=wrong_owner):
                with self.assertRaises(safety.ReportError):
                    safety.validate_source_path(source, source_value=os.fspath(source))

    def test_source_path_public_contract_rejects_windows_unsafe_types(self) -> None:
        path = Path("/private/tmp/windows-source.txt")
        regular = mock.Mock(st_mode=stat.S_IFREG | 0o600)
        nonregular = mock.Mock(st_mode=stat.S_IFDIR | 0o700)

        with mock.patch.object(safety.os, "name", "nt"):
            with mock.patch.object(safety, "_source_metadata", return_value=regular):
                with mock.patch.object(Path, "is_symlink", return_value=False):
                    with mock.patch.object(safety, "_is_windows_reparse", return_value=False):
                        self.assertEqual(
                            safety.validate_source_path(path, source_value=os.fspath(path)),
                            regular,
                        )
                    with mock.patch.object(safety, "_is_windows_reparse", return_value=True):
                        with self.assertRaises(safety.ReportError):
                            safety.validate_source_path(path, source_value=os.fspath(path))
                with mock.patch.object(Path, "is_symlink", return_value=True):
                    with self.assertRaises(safety.ReportError):
                        safety.validate_source_path(path, source_value=os.fspath(path))
            with mock.patch.object(safety, "_source_metadata", return_value=nonregular):
                with mock.patch.object(Path, "is_symlink", return_value=False):
                    with mock.patch.object(safety, "_is_windows_reparse", return_value=False):
                        with self.assertRaises(safety.ReportError):
                            safety.validate_source_path(path, source_value=os.fspath(path))

    def test_lock_initialization_failure_removes_only_the_owned_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg27-lock-test-") as temporary_value:
            root = Path(temporary_value)
            repository = root / "repository"
            repository.mkdir()
            with mock.patch.dict(
                os.environ,
                {"GIT_SHOW_REPORT_ROOT": os.fspath(root / "reports")},
            ):
                destination = safety.Destination(repository, "LOCK-INIT")

            original_write_text = Path.write_text

            def fail_owner_write(path: Path, *args, **kwargs):
                if path.name == "owner":
                    raise OSError("injected owner write failure")
                return original_write_text(path, *args, **kwargs)

            with mock.patch.object(Path, "write_text", new=fail_owner_write):
                with self.assertRaises(OSError):
                    with destination.lock():
                        self.fail("lock body must not run")

            self.assertFalse(destination.lock_path.exists())

            def fail_after_partial_write(path: Path, *args, **kwargs):
                if path.name == "owner":
                    original_write_text(path, "partial-token", encoding="utf-8")
                    raise OSError("injected partial owner write failure")
                return original_write_text(path, *args, **kwargs)

            with mock.patch.object(Path, "write_text", new=fail_after_partial_write):
                with self.assertRaises(OSError):
                    with destination.lock():
                        self.fail("lock body must not run")

            self.assertFalse(destination.lock_path.exists())

            def replace_owner_before_failure(path: Path, *args, **kwargs):
                if path.name == "owner":
                    path.unlink()
                    original_write_text(path, "foreign-token\n", encoding="utf-8")
                    raise OSError("injected foreign owner replacement")
                return original_write_text(path, *args, **kwargs)

            with mock.patch.object(Path, "write_text", new=replace_owner_before_failure):
                with self.assertRaises(OSError):
                    with destination.lock():
                        self.fail("lock body must not run")

            self.assertTrue(destination.lock_path.is_dir())
            self.assertEqual(
                (destination.lock_path / "owner").read_text(encoding="utf-8"),
                "foreign-token\n",
            )


if __name__ == "__main__":
    unittest.main()
