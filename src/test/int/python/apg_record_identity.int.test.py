#!/usr/bin/env python3
"""Integration tests for bin/apg-check-record-identity."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
COMMAND = REPOSITORY_ROOT / "bin" / "apg-check-record-identity"


class APGRecordIdentityTests(unittest.TestCase):
    """Exercise the public command against generated APG-shaped records."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="apg-record-test-")
        self.root = Path(self.temporary.name) / "repository"
        self.create_valid_repository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_valid_repository(self, root: Path) -> None:
        adr = root / "docs" / "adr" / "2026" / "07"
        status = root / "docs" / "status" / "2026" / "07" / "21"
        adr.mkdir(parents=True)
        status.mkdir(parents=True)
        (root / "docs" / "adr" / "README.md").write_text(
            "# Architecture Decision Records\n\n"
            "- [`0001 — First Decision`](2026/07/0001-first-decision.md)\n",
            encoding="utf-8",
        )
        (adr / "0001-first-decision.md").write_text(
            "# 0001 — First Decision\n", encoding="utf-8"
        )
        (root / "docs" / "status" / "README.md").write_text(
            "# Exit Records\n\n"
            "- [`00001 — APG1 First Exit`](2026/07/21/00001-apg1-first-exit.md)\n"
            "- [`00029 — APG19A Identity Exit`](2026/07/21/00029-apg19a-identity-exit.md)\n",
            encoding="utf-8",
        )
        (status / "00001-apg1-first-exit.md").write_text(
            "# APG1 First Exit\n", encoding="utf-8"
        )
        (status / "00029-apg19a-identity-exit.md").write_text(
            "# APG19A Identity Exit\n\nPhase ID: `APG19A`\n",
            encoding="utf-8",
        )

    def run_checker(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(COMMAND), "--root", str(self.root), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.root,
            env=os.environ.copy(),
        )

    def codes(self) -> set[str]:
        result = self.run_checker("--format", "json")
        self.assertEqual(result.returncode, 1, result)
        payload = json.loads(result.stdout)
        return {item["code"] for item in payload["diagnostics"]}

    def test_independent_namespaces_and_phase_expectations_pass(self) -> None:
        result = self.run_checker(
            "--format",
            "json",
            "--expect-allocated",
            "APG19A",
            "--expect-available",
            "APG20",
        )
        self.assertEqual(result.returncode, 0, result)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["summary"]["next_adr"], "0002")
        self.assertEqual(payload["summary"]["next_exit"], "00030")

    def test_duplicate_adr_sequence_fails_only_adr_namespace(self) -> None:
        path = self.root / "docs" / "adr" / "2026" / "07" / "0001-duplicate.md"
        path.write_text("# 0001 — Duplicate\n", encoding="utf-8")
        self.assertIn("APGR002", self.codes())

    def test_duplicate_exit_sequence_fails(self) -> None:
        path = (
            self.root
            / "docs"
            / "status"
            / "2026"
            / "07"
            / "21"
            / "00029-apg20-duplicate-exit.md"
        )
        path.write_text(
            "# APG20 Duplicate Exit\n\nPhase ID: `APG20`\n",
            encoding="utf-8",
        )
        self.assertIn("APGR005", self.codes())

    def test_index_must_cover_each_exit_exactly_once(self) -> None:
        index = self.root / "docs" / "status" / "README.md"
        text = index.read_text(encoding="utf-8")
        index.write_text(text + text.splitlines()[-1] + "\n", encoding="utf-8")
        self.assertIn("APGR008", self.codes())

    def test_phase_identity_is_case_insensitively_unique(self) -> None:
        status = self.root / "docs" / "status" / "2026" / "07" / "21"
        duplicate = status / "00030-apg19a-duplicate-exit.md"
        duplicate.write_text(
            "# apg19a Duplicate Exit\n\nPhase ID: `apg19a`\n",
            encoding="utf-8",
        )
        index = self.root / "docs" / "status" / "README.md"
        index.write_text(
            index.read_text(encoding="utf-8")
            + "- [`00030 — apg19a Duplicate Exit`](2026/07/21/00030-apg19a-duplicate-exit.md)\n",
            encoding="utf-8",
        )
        codes = self.codes()
        self.assertIn("APGR011", codes)
        self.assertIn("APGR014", codes)

    def test_path_index_heading_and_explicit_field_must_agree(self) -> None:
        path = (
            self.root
            / "docs"
            / "status"
            / "2026"
            / "07"
            / "21"
            / "00029-apg19a-identity-exit.md"
        )
        path.write_text("# APG20 Identity Exit\n\nPhase ID: `APG20`\n", encoding="utf-8")
        self.assertIn("APGR010", self.codes())

    def test_new_exit_requires_explicit_phase_field(self) -> None:
        path = (
            self.root
            / "docs"
            / "status"
            / "2026"
            / "07"
            / "21"
            / "00029-apg19a-identity-exit.md"
        )
        path.write_text("# APG19A Identity Exit\n", encoding="utf-8")
        self.assertIn("APGR009", self.codes())

    def test_expectation_failure_is_reported(self) -> None:
        result = self.run_checker("--format", "json", "--expect-allocated", "APG20")
        self.assertEqual(result.returncode, 1, result)
        payload = json.loads(result.stdout)
        self.assertIn("APGR012", {item["code"] for item in payload["diagnostics"]})

    def test_empty_tree_cannot_pass_as_a_repository(self) -> None:
        empty = Path(self.temporary.name) / "empty"
        empty.mkdir()
        self.root = empty
        result = self.run_checker("--format", "json")
        self.assertEqual(result.returncode, 1, result)
        payload = json.loads(result.stdout)
        codes = {item["code"] for item in payload["diagnostics"]}
        self.assertIn("APGR001", codes)
        self.assertIn("APGR003", codes)
        self.assertIn("APGR006", codes)

    def test_exit_path_phase_token_must_be_lowercase(self) -> None:
        status = self.root / "docs" / "status" / "2026" / "07" / "21"
        original = status / "00029-apg19a-identity-exit.md"
        uppercase = status / "00029-APG19A-identity-exit.md"
        original.rename(uppercase)
        index = self.root / "docs" / "status" / "README.md"
        index.write_text(
            index.read_text(encoding="utf-8").replace(
                "00029-apg19a-identity-exit.md",
                "00029-APG19A-identity-exit.md",
            ),
            encoding="utf-8",
        )
        self.assertIn("APGR015", self.codes())


if __name__ == "__main__":
    unittest.main()
