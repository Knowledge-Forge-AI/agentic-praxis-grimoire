#!/usr/bin/env python3
"""Focused unit tests for APG public release parsing and rendering."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_public_release as release  # noqa: E402


EXPECTED_V03_SKILLS = tuple(
    f"skills/{name}/SKILL.md"
    for name in (
        "agentic-praxis-grimoire-workflow",
        "bash-language-profile",
        "bats-test-profile",
        "composing-approved-roadmap-assignments",
        "composing-bounded-worker-assignments",
        "debugging-systematically",
        "designing-significant-changes",
        "go-language-profile",
        "implementing-with-test-discipline",
        "nix-language-profile",
        "planning-repository-work",
        "postgresql-database-profile",
        "python-language-profile",
        "reviewing-and-verifying-repository-work",
        "ruby-language-profile",
        "sqlite-database-profile",
        "synthesizing-repository-guidance",
        "zsh-language-profile",
        "zunit-test-profile",
    )
)
HISTORICAL_V02_SKILLS = tuple(
    f"skills/{name}/SKILL.md"
    for name in (
        "composing-bounded-worker-assignments",
        "debugging-systematically",
        "designing-significant-changes",
        "implementing-with-test-discipline",
        "planning-repository-work",
        "reviewing-and-verifying-repository-work",
    )
)


class APGPublicReleaseUnitTests(unittest.TestCase):
    def test_semver_accepts_release_and_prerelease(self) -> None:
        for value in ("0.2.0", "0.2.0-apg12.1", "2.3.4-rc.1+build.7"):
            self.assertEqual(release.validate_version(value), value)

    def test_semver_rejects_leading_v_and_leading_zero(self) -> None:
        for value in ("v0.2.0", "01.2.3", "1.2", "1.2.3-", "1.2.3-01", "1.2.3-alpha.01"):
            with self.subTest(value=value), self.assertRaises(release.InvocationError):
                release.validate_version(value)

    def test_release_date_requires_offset(self) -> None:
        self.assertEqual(
            release.validate_date("2026-07-20T12:00:00-04:00").utcoffset().total_seconds(),
            -14400,
        )
        for value in (
            "2026-07-20T12:00:00",
            "2026-07-20 12:00:00+00:00",
            "20260720T120000+00:00",
            "2026-W30-1T12:00:00+00:00",
            "2026-07-20T12:00:00+04",
        ):
            with self.subTest(value=value), self.assertRaises(release.InvocationError):
                release.validate_date(value)

    def test_identity_rejects_control_and_malformed_email(self) -> None:
        release.validate_identity("APG Release", "release@example.invalid")
        for name, email in (
            ("bad\nname", "a@example.invalid"),
            ("bad\tname", "a@example.invalid"),
            ("bad\0name", "a@example.invalid"),
            ("good", "bad email"),
            ("good", "bad\0@example.invalid"),
        ):
            with self.subTest(name=name, email=email), self.assertRaises(release.InvocationError):
                release.validate_identity(name, email)

    def test_policy_paths_are_normalized_relative_paths(self) -> None:
        for value in ("README.md", ".agents/skills/name", "path with spaces/file"):
            self.assertTrue(release.safe_policy_path(value))
        for value in ("", "/absolute", "../escape", "a/../b", "a\\b"):
            self.assertFalse(release.safe_policy_path(value))

    def test_unique_json_object_rejects_duplicate_keys(self) -> None:
        with self.assertRaises(ValueError):
            json.loads('{"a":1,"a":2}', object_pairs_hook=release.unique_object)

    def test_manifest_json_is_canonical(self) -> None:
        manifest = {
            "schema_version": 1,
            "entries": [],
        }
        rendered = release.render_manifest(manifest, "json")
        self.assertEqual(rendered, json.dumps(manifest, separators=(",", ":"), sort_keys=True) + "\n")

    def test_tagger_timestamp_is_deterministic(self) -> None:
        parsed = release.validate_date("2026-07-20T12:00:00-04:00")
        self.assertEqual(release.deterministic_tagger(parsed), "1784563200 -0400")

    def test_v0_3_audited_surface_requires_all_19_skills(self) -> None:
        self.assertEqual(release.AUDITED_SKILLS, EXPECTED_V03_SKILLS)
        self.assertEqual(
            release.AUDITED_PROJECTIONS,
            tuple(
                path.replace("skills/", ".agents/skills/", 1).removesuffix("/SKILL.md")
                for path in EXPECTED_V03_SKILLS
            ),
        )

    def test_v0_2_lineage_retains_only_the_exact_historical_exception(self) -> None:
        historical = release.audited_policy_surfaces("0.2.0")
        current = release.audited_policy_surfaces("0.3.0")
        self.assertEqual(historical[0]["required_skills"], HISTORICAL_V02_SKILLS)
        self.assertEqual(len(historical), 1)
        self.assertEqual(current[0]["required_skills"], EXPECTED_V03_SKILLS)
        self.assertEqual(len(current), 1)


if __name__ == "__main__":
    unittest.main()
