#!/usr/bin/env python3
"""v0.3 policy and historical-lineage tests for APG public releases."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
import unittest


FIXTURE_PATH = Path(__file__).with_name("apg_public_release.int.test.py")
SPEC = importlib.util.spec_from_file_location("apg_public_release_integration_fixture", FIXTURE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load APG public release integration fixture")
FIXTURE_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FIXTURE_MODULE
SPEC.loader.exec_module(FIXTURE_MODULE)


class APGPublicReleaseV03PolicyTests(unittest.TestCase):
    """Exercise v0.3 policy behavior through a composed disposable fixture."""

    def setUp(self) -> None:
        self.fixture = FIXTURE_MODULE.APGPublicReleaseTests(
            "test_01_manifest_is_deterministic_in_text_and_json"
        )
        self.fixture.setUp()

    def tearDown(self) -> None:
        self.fixture.tearDown()

    def make_historical_v0_2_source(self) -> Path:
        return self.fixture.copy_source_with_policy(
            "historical-v0.2-source",
            self.fixture.historical_v02_policy(),
        )

    def test_later_public_base_must_be_policy_complete(self) -> None:
        fixture = self.fixture
        historical_source = self.make_historical_v0_2_source()
        later, later_build = fixture.build(
            fixture.root / "policy-complete-v0.2-base",
            source=historical_source,
            version="0.2.0",
        )
        fixture.assert_success(later_build)
        (later / "release" / "public-surface.json").write_text("{}\n")
        fixture.commit_all(later, "Release v0.3.0")
        fixture.git(later, "tag", "-a", "v0.3.0", "-m", "Release v0.3.0")

        output = fixture.root / "policy-incomplete-base-candidate"
        result = fixture.build(output, base=later, version="0.4.0")[1]
        self.assertEqual(result.returncode, 1)
        self.assertIn("policy", result.stderr.lower())
        self.assertFalse(output.exists())
        check_candidate = fixture.root / "policy-incomplete-check-candidate"
        shutil.copytree(fixture.source, check_candidate, symlinks=True)
        checked = fixture.check_candidate(
            check_candidate,
            base=later,
            version="0.4.0",
        )
        self.assertEqual(checked.returncode, 1)
        self.assertIn("policy", checked.stderr.lower())

    def test_v0_3_requires_all_19_skills_and_projections(self) -> None:
        fixture = self.fixture
        policy = fixture.policy()
        self.assertEqual(len(policy["required_skills"]), 19)
        self.assertEqual(len(policy["required_projections"]), 19)
        for path in (
            "skills/go-language-profile/SKILL.md",
            ".agents/skills/go-language-profile",
        ):
            with self.subTest(path=path):
                source = fixture.make_source(
                    fixture.root / f"missing-{Path(path).name}"
                )
                target = source / path
                target.unlink()
                fixture.commit_all(source, f"Remove {path}")
                result = fixture.run_command("manifest", "--source", str(source))
                self.assertEqual(result.returncode, 1)
                self.assertIn(path, result.stderr)

    def test_historical_v0_2_six_skill_lineage_remains_valid(self) -> None:
        fixture = self.fixture
        historical_source = self.make_historical_v0_2_source()
        later, later_build = fixture.build(
            fixture.root / "historical-v0.2-base",
            source=historical_source,
            version="0.2.0",
        )
        fixture.assert_success(later_build)
        candidate, built = fixture.build(
            fixture.root / "v0.3-from-historical-v0.2",
            base=later,
            version="0.3.0",
        )
        fixture.assert_success(built)
        fixture.assert_success(
            fixture.check_candidate(candidate, base=later, version="0.3.0")
        )

    def test_build_and_check_reject_current_surface_under_v0_2_identity(self) -> None:
        fixture = self.fixture
        output = fixture.root / "v0.2-with-current-surface"
        built_as_v0_2 = fixture.build(
            output,
            version="0.2.0",
        )[1]
        self.assertEqual(built_as_v0_2.returncode, 1)
        self.assertIn("policy", built_as_v0_2.stderr.lower())
        self.assertFalse(output.exists())

        candidate, built_as_v0_3 = fixture.build(
            fixture.root / "valid-v0.3-candidate",
            version="0.3.0",
        )
        fixture.assert_success(built_as_v0_3)
        checked_as_v0_2 = fixture.check_candidate(candidate, version="0.2.0")
        self.assertEqual(checked_as_v0_2.returncode, 1)
        self.assertIn("policy", checked_as_v0_2.stderr.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
