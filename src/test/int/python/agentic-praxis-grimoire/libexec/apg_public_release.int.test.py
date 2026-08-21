#!/usr/bin/env python3
"""v0.3 policy and historical-lineage tests for APG public releases."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


FIXTURE_PATH = Path(__file__).parent.parent / "bin" / "apg-public-release.int.test.py"
SPEC = importlib.util.spec_from_file_location("apg_public_release_integration_fixture", FIXTURE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load APG public release integration fixture")
FIXTURE_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FIXTURE_MODULE
SPEC.loader.exec_module(FIXTURE_MODULE)
release = FIXTURE_MODULE.release


class APGPublicReleaseBoundaryTests(unittest.TestCase):
    """Exercise invocation and policy branches without repository substitution."""

    def test_policy_identity_selects_each_immutable_surface(self) -> None:
        for version, expected in (
            ("0.2.0", release.HISTORICAL_V02_SKILLS),
            ("0.3.0+build.1", release.HISTORICAL_V03_SKILLS),
            ("0.4.0-rc.1", release.HISTORICAL_V04_SKILLS),
            ("0.5.0", release.HISTORICAL_V05_SKILLS),
            ("0.6.0", release.AUDITED_SKILLS),
        ):
            with self.subTest(version=version):
                surfaces = release.audited_policy_surfaces(version)
                self.assertEqual(surfaces[0]["required_skills"], expected)
        for version in ("invalid", "0.5.1", "0.6.1"):
            with self.subTest(version=version):
                with self.assertRaisesRegex(release.ToolError, "policy identity"):
                    release.audited_policy_surfaces(version)

    def test_real_git_repository_resolution_tree_and_blob_boundaries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-public-git-") as temporary:
            root = Path(temporary) / "repository"
            release.run_git(Path(temporary), ["init", "-q", str(root)])
            release.run_git(root, ["config", "user.name", "APG Test"])
            release.run_git(root, ["config", "user.email", "apg@example.invalid"])
            (root / "private").mkdir()
            (root / "private/secret.txt").write_text("private\n", encoding="utf-8")
            (root / "README.md").write_text("public\n", encoding="utf-8")
            executable = root / "tool"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
            (root / "readme-link").symlink_to("README.md")
            release.run_git(root, ["add", "."])
            release.run_git(root, ["commit", "-q", "-m", "initial"])

            repository = release.resolve_repository(root, "fixture")
            entries = release.tree_entries(repository, excluded_prefix=b"private/")
            modes = {entry.display_path: entry.mode for entry in entries}
            self.assertEqual(modes["README.md"], "100644")
            self.assertEqual(modes["tool"], "100755")
            self.assertEqual(modes["readme-link"], "120000")
            self.assertNotIn("private/secret.txt", modes)
            release.validate_public_symlinks(repository, entries)
            with self.assertRaisesRegex(release.ToolError, "committed path is missing"):
                release.committed_bytes(repository, "missing.txt")

            (root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(release.ToolError, "must be clean"):
                release.resolve_repository(root, "fixture")
            release.resolve_repository(root, "fixture", require_clean=False)
            with self.assertRaisesRegex(release.ToolError, "not a Git worktree"):
                release.resolve_repository(Path(temporary), "outside")

    def test_policy_paths_reject_unsafe_forms(self) -> None:
        self.assertTrue(release.safe_policy_path("skills/example/SKILL.md"))
        for value in ("", "/absolute", "../escape", "a\\b", "a\x00b"):
            with self.subTest(value=value):
                self.assertFalse(release.safe_policy_path(value))

    def test_git_environment_removes_host_configuration_and_applies_extra(self) -> None:
        names = {
            "GIT_DIR": "foreign",
            "GIT_CONFIG_KEY_0": "credential.helper",
            "GIT_CONFIG_VALUE_0": "foreign",
        }
        original = {name: os.environ.get(name) for name in names}
        try:
            os.environ.update(names)
            environment = release.git_environment({"APG_BOUNDARY": "present"})
        finally:
            for name, value in original.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
        self.assertTrue(names.keys().isdisjoint(environment))
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(environment["APG_BOUNDARY"], "present")

    def test_manifest_rendering_and_versioned_exclusions_cover_both_formats(self) -> None:
        manifest = {
            "entries": [
                {"mode": "100644", "sha256": "a" * 64, "path": "README.md"}
            ]
        }
        self.assertEqual(
            json.loads(release.render_manifest(manifest, "json"))["entries"],
            manifest["entries"],
        )
        self.assertIn("100644 " + "a" * 64 + " README.md", release.render_manifest(manifest, "text"))
        entry = release.Entry("100644", "blob", "a" * 40, b"bin/git-diff-report")
        release.validate_versioned_policy_exclusions([entry], "0.4.0")
        with self.assertRaisesRegex(release.ToolError, "unsupported future owner"):
            release.validate_versioned_policy_exclusions([entry], "0.3.0")
        for path in sorted(release.APG55_V05_CRITICAL):
            future = release.Entry(
                "100644", "blob", "a" * 40, path.encode("ascii")
            )
            with self.assertRaisesRegex(
                release.ToolError, "unsupported future owner"
            ):
                release.validate_versioned_policy_exclusions(
                    [future], "0.4.0"
                )
        v06_path = sorted(release.V06_ONLY_SKILLS)[0]
        future = release.Entry("100644", "blob", "a" * 40, v06_path.encode("ascii"))
        with self.assertRaisesRegex(release.ToolError, "unsupported future owner"):
            release.validate_versioned_policy_exclusions([future], "0.5.0")
        release.validate_versioned_policy_exclusions([future], "0.6.0")

    def test_semver_date_and_author_boundaries_are_strict(self) -> None:
        self.assertEqual(release.validate_version("0.4.0-rc.1+build.2"), "0.4.0-rc.1+build.2")
        for value in ("v0.4.0", "0.4", "0.4.0-01"):
            with self.subTest(version=value):
                with self.assertRaises(release.InvocationError):
                    release.validate_version(value)
        self.assertIsNotNone(release.validate_date("2026-07-22T10:30:00Z").utcoffset())
        for value in ("2026-07-22", "2026-13-40T25:70:00+00:00"):
            with self.subTest(date=value):
                with self.assertRaises(release.InvocationError):
                    release.validate_date(value)
        release.validate_identity("APG Release", "release@example.invalid")
        for name, email in (("", "release@example.invalid"), ("Bad<Name", "release@example.invalid"), ("Good", "bad"), ("Good", "bad\n@example.invalid")):
            with self.subTest(name=name, email=email):
                with self.assertRaises(release.InvocationError):
                    release.validate_identity(name, email)

    def test_repository_separation_rejects_equal_and_nested_roots(self) -> None:
        repository = lambda path: release.Repository(path, "a" * 40, "b" * 40)
        release.validate_repository_separation(repository(Path("/one")), repository(Path("/two")))
        for second in (Path("/one"), Path("/one/nested"), Path("/")):
            with self.subTest(second=second):
                with self.assertRaisesRegex(release.InvocationError, "physically disjoint"):
                    release.validate_repository_separation(repository(Path("/one")), repository(second))

    def test_output_path_accepts_empty_directory_and_rejects_unsafe_shapes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="apg-output-boundary-") as raw:
            root = Path(raw)
            source = root / "source"
            base = root / "base"
            source.mkdir()
            base.mkdir()
            empty = root / "candidate"
            empty.mkdir()
            release.validate_output_path(empty, source, base)
            (empty / "member").write_text("occupied\n")
            with self.assertRaisesRegex(release.InvocationError, "nonempty"):
                release.validate_output_path(empty, source, base)
            plain = root / "plain"
            plain.write_text("file\n")
            with self.assertRaisesRegex(release.InvocationError, "unsafe type"):
                release.validate_output_path(plain, source, base)
            output_link = root / "output-link"
            output_link.symlink_to(root / "missing", target_is_directory=True)
            with self.assertRaisesRegex(release.InvocationError, "symlinked"):
                release.validate_output_path(output_link, source, base)
            link_parent = root / "link-parent"
            link_parent.symlink_to(base, target_is_directory=True)
            with self.assertRaisesRegex(release.InvocationError, "symlinked"):
                release.validate_output_path(link_parent / "candidate", source, base)
            broken_parent = root / "broken-parent"
            broken_parent.symlink_to(root / "missing", target_is_directory=True)
            with self.assertRaisesRegex(release.InvocationError, "broken symlink"):
                release.validate_output_path(
                    broken_parent / "candidate", source, base
                )
            file_parent = root / "file-parent"
            file_parent.write_text("not a directory\n")
            with self.assertRaisesRegex(
                release.InvocationError, "symlinked or non-directory"
            ):
                release.validate_output_path(
                    file_parent / "candidate", source, base
                )
            system_alias = Path("/var")
            if (
                system_alias.is_symlink()
                and system_alias.resolve(strict=True) == Path("/private/var")
            ):
                absent_parent = (
                    system_alias
                    / f"apg-output-boundary-absent-{os.getpid()}"
                )
                self.assertFalse(os.path.lexists(absent_parent))
                with self.assertRaisesRegex(
                    release.InvocationError, "parent cannot be resolved safely"
                ):
                    release.validate_output_path(
                        absent_parent / "candidate", source, base
                    )
            with self.assertRaisesRegex(release.InvocationError, "disjoint"):
                release.validate_output_path(
                    source.resolve() / "candidate", source.resolve(), base.resolve()
                )

    def test_critical_path_validation_reports_each_missing_owner(self) -> None:
        policy = {
            key: [f"{key}.txt"]
            for key in (
                "critical_files",
                "required_helpers",
                "required_licensing_files",
                "required_projections",
                "required_skills",
                "required_test_entrypoints",
                "required_wrappers",
            )
        }
        entries = [
            release.Entry("100644", "blob", "a" * 40, f"{key}.txt".encode())
            for key in policy
        ]
        release.validate_critical(entries, policy)
        for index, key in enumerate(policy):
            with self.subTest(key=key):
                with self.assertRaisesRegex(release.ToolError, "required public path"):
                    release.validate_critical(entries[:index] + entries[index + 1 :], policy)


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

    def make_historical_v0_3_source(self) -> Path:
        return self.fixture.copy_source_with_policy(
            "historical-v0.3-source",
            self.fixture.historical_v03_policy(),
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
        result = fixture.build(output, base=later, version="0.6.0")[1]
        self.assertEqual(result.returncode, 1)
        self.assertIn("policy", result.stderr.lower())
        self.assertFalse(output.exists())
        check_candidate = fixture.root / "policy-incomplete-check-candidate"
        shutil.copytree(fixture.source, check_candidate, symlinks=True)
        checked = fixture.check_candidate(
            check_candidate,
            base=later,
            version="0.6.0",
        )
        self.assertEqual(checked.returncode, 1)
        self.assertIn("policy", checked.stderr.lower())

    def test_v0_3_requires_all_19_skills_and_projections(self) -> None:
        fixture = self.fixture
        policy = fixture.historical_v03_policy()
        self.assertEqual(len(policy["required_skills"]), 19)
        self.assertEqual(len(policy["required_projections"]), 19)
        for path in (
            "skills/go-language-profile/SKILL.md",
            ".agents/skills/go-language-profile",
        ):
            with self.subTest(path=path):
                source = fixture.copy_source_with_policy(
                    f"missing-{Path(path).name}",
                    policy,
                )
                target = source / path
                target.unlink()
                fixture.commit_all(source, f"Remove {path}")
                result = fixture.build(
                    fixture.root / f"missing-{Path(path).name}-candidate",
                    source=source,
                    version="0.3.0",
                )[1]
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
        fixture.assert_success(
            fixture.check_candidate(
                later,
                source=historical_source,
                version="0.2.0",
            )
        )
        candidate, built = fixture.build(
            fixture.root / "current-from-historical-v0.2",
            base=later,
            version="0.6.0",
        )
        fixture.assert_success(built)
        fixture.assert_success(
            fixture.check_candidate(candidate, base=later, version="0.6.0")
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

        candidate, built_as_current = fixture.build(
            fixture.root / "valid-current-candidate",
            version="0.6.0",
        )
        fixture.assert_success(built_as_current)
        checked_as_v0_2 = fixture.check_candidate(candidate, version="0.2.0")
        self.assertEqual(checked_as_v0_2.returncode, 1)
        self.assertIn("policy", checked_as_v0_2.stderr.lower())

    def test_historical_v0_3_policy_reconstructs_build_and_check(self) -> None:
        fixture = self.fixture
        historical_source = self.make_historical_v0_3_source()
        candidate, built = fixture.build(
            fixture.root / "historical-v0.3-candidate",
            source=historical_source,
            version="0.3.0",
        )
        fixture.assert_success(built)
        fixture.assert_success(
            fixture.check_candidate(
                candidate,
                source=historical_source,
                version="0.3.0",
            )
        )

    def test_current_surface_requires_report_core_owner(self) -> None:
        fixture = self.fixture
        source = fixture.make_source(fixture.root / "missing-current-report-owner")
        target = source / "bin" / "git-diff-report"
        target.unlink()
        fixture.commit_all(source, "Remove current report owner")
        result = fixture.build(
            fixture.root / "missing-current-report-owner-candidate",
            source=source,
            version="0.6.0",
        )[1]
        self.assertEqual(result.returncode, 1)
        self.assertIn("bin/git-diff-report", result.stderr)

    def test_historical_v0_3_rejects_current_report_core_owner(self) -> None:
        fixture = self.fixture
        source = self.make_historical_v0_3_source()
        target = source / "bin" / "git-diff-report"
        target.write_text("#!/bin/sh\nexit 0\n")
        target.chmod(0o755)
        fixture.commit_all(source, "Add unsupported future report owner")
        result = fixture.build(
            fixture.root / "historical-v0.3-with-future-owner",
            source=source,
            version="0.3.0",
        )[1]
        self.assertEqual(result.returncode, 1)
        self.assertIn("bin/git-diff-report", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
