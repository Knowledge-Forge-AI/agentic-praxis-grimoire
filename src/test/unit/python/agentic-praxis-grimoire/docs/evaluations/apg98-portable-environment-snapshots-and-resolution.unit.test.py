#!/usr/bin/env python3
"""Focused APG98 evaluation and public-boundary contract."""

from __future__ import annotations

from pathlib import Path
import unittest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
EVALUATION = ROOT / (
    "docs/evaluations/apg98-portable-environment-snapshots-and-resolution.md"
)
EXIT = ROOT / (
    "docs/status/2026/08/22/00147-apg98-portable-environment-snapshots-"
    "and-resolution-exit.md"
)
PUBLIC_DOCS = (
    EVALUATION,
    EXIT,
    ROOT / "docs/guides/environment-snapshots.md",
    ROOT / "docs/environment-snapshot-cutover-contract.md",
)
FIXTURE_ROOT = ROOT / "src/test/fixtures/apg98-environment"


class APG98EvaluationContractTests(unittest.TestCase):
    maxDiff = None

    def test_evaluation_records_the_frozen_public_api_and_schemas(self) -> None:
        text = " ".join(EVALUATION.read_text(encoding="utf-8").split())
        for phrase in (
            "provider-neutral Go package `envsnap`",
            "`ValidateProfile`, `Capture`, `Store`, `Load`, and `Resolve`",
            "`apg.environment-profile/v1`",
            "`apg.environment-snapshot/v1`",
            "explicit-map capture",
            "Defaults are metadata only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_evaluation_records_security_resolution_and_storage_boundaries(
        self,
    ) -> None:
        text = " ".join(EVALUATION.read_text(encoding="utf-8").split())
        for phrase in (
            "token-aware rather than a naive substring test",
            "`SSH_AUTH_SOCK` receives a narrow documented capability-path",
            "absent and empty values as missing",
            "Isolated mode is the default",
            "override over snapshot over base",
            "0700 and 0600",
            "interprocess lock",
            "without advancing the capture timestamp",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_evaluation_records_cli_bridge_and_successor_boundaries(self) -> None:
        text = " ".join(EVALUATION.read_text(encoding="utf-8").split())
        for phrase in (
            "`env profile-check`, `snapshot`, `show`, `resolve`, and `run`",
            "exact argument vector directly to a child process without a shell",
            "Normal Python `apgr env` routes delegate to that Go family",
            "thin-hook contract",
            "APG98 changes no `.flakes`, Nix, shell hook, live snapshot, JACA, hotspot",
            "APG99 remains separately authorized",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_thin_cutover_contract_is_readable_but_not_activated(self) -> None:
        text = " ".join(
            (ROOT / "docs/environment-snapshot-cutover-contract.md")
            .read_text(encoding="utf-8")
            .split()
        )
        for phrase in (
            "not an activation instruction",
            "exact argv",
            "one immediate refresh",
            "every Zsh `precmd`",
            "without duplicates",
            "avoid `eval`, `source`, `bash -c`, or `zsh -c`",
            "must not become a hidden second authority",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_environment_docs_name_each_intentional_difference(self) -> None:
        text = " ".join(
            (ROOT / "docs/guides/environment-snapshots.md")
            .read_text(encoding="utf-8")
            .split()
        ).lower()
        for phrase in (
            "strict canonical json",
            "explicit map",
            "isolated",
            "sensitive names",
            "fingerprint excludes time/path",
            "interprocess lock",
            "no-churn",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_exit_records_terminal_disposition_and_preserved_invariants(self) -> None:
        text = EXIT.read_text(encoding="utf-8")
        for phrase in (
            "V07_ENVIRONMENT_SNAPSHOTS_READY_FOR_APG99",
            "All twelve validators",
            "Canonical JSON identities are stable",
            "A disposable external Go module",
            "The thin-hook contract is documented but not activated",
            "39/39/39/39",
            "9,504 description bytes",
            "9,492 characters",
            "9,527-byte ceiling",
            "APG99 may implement the structural-hotspot contract only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_publishable_docs_and_fixtures_are_present_and_path_safe(self) -> None:
        for path in PUBLIC_DOCS:
            with self.subTest(path=path):
                self.assertTrue(path.is_file(), path)

        fixture_files = tuple(sorted(path for path in FIXTURE_ROOT.rglob("*") if path.is_file()))
        self.assertTrue(fixture_files, "APG98 parity fixture directory is empty")
        private_path_markers = tuple(
            "/" + component + "/" for component in ("Users", "home", "private")
        )
        for path in (*PUBLIC_DOCS, *fixture_files):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                for marker in private_path_markers:
                    self.assertNotIn(marker, text)
                self.assertNotIn("slair", text.lower())


if __name__ == "__main__":
    unittest.main()
