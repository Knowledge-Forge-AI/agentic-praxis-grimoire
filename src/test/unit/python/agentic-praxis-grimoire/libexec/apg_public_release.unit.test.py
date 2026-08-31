#!/usr/bin/env python3
"""Focused unit tests for APG public release parsing and rendering."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from src.test.apg_test_support import repository_root
from src.test.apg_public_release_cases import APGPublicReleaseCaseMixin


REPOSITORY_ROOT = repository_root(__file__)
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


class APGPublicReleaseUnitTests(APGPublicReleaseCaseMixin, unittest.TestCase):
    def test_live_committed_v07_manifest_exercises_complete_policy_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-hardlinks",
                    str(REPOSITORY_ROOT),
                    str(source),
                ],
                check=True,
            )
            repository = release.resolve_repository(source, "source")
            manifest = release.build_manifest(repository, "0.7.0")

        paths = {entry["path"] for entry in manifest["entries"]}
        self.assertGreater(len(paths), 1000)
        self.assertIn("cmd/apgr/main.go", paths)
        self.assertIn("hotspot/testdata/classification/sample.md", paths)
        self.assertFalse(any(path == "private" or path.startswith("private/") for path in paths))
        self.assertEqual(manifest["canonical_public_identity"], "agentic-praxis-grimoire")

    def test_prominent_public_guidance_matches_current_skill_topology(self) -> None:
        surface = json.loads(
            (REPOSITORY_ROOT / "release" / "public-surface.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(surface["required_skills"]), 39)
        self.assertEqual(len(surface["required_projections"]), 39)
        expected = {
            "README.md": (
                "39 canonical agent skills",
                "APG has 39 canonical leaves: 14 stable and 25 provisional",
                "39 canonical / 39 catalog / 39 projections / 39\n  discoverable",
            ),
            "skills/README.md": (
                "thirty-nine canonical skills: fourteen\nstable rows and twenty-five provisional rows",
                "39 canonical skills, 39 catalog rows, and 39 projections,\nwith fourteen stable and twenty-five provisional rows",
            ),
            "docs/history/releases-and-phases.md": (
                "thirty-nine relative symbolic links contain no\n  independent skill content",
            ),
            "AGENTS.md": (
                "thirty-nine skill owners, fourteen stable\n  and twenty-five provisional",
            ),
            "docs/project-skill-projection.md": (
                "nineteen\n  skills for public v0.3.0 and thirty-nine for current development",
            ),
        }
        for relative, fragments in expected.items():
            source = (REPOSITORY_ROOT / relative).read_text(encoding="utf-8")
            for fragment in fragments:
                with self.subTest(path=relative, fragment=fragment):
                    self.assertIn(fragment, source)

    def test_v07_surface_separates_historical_python_oracles(self) -> None:
        historical = release.audited_policy_surfaces("0.6.0")[0]
        current = release.audited_policy_surfaces("0.7.0")[0]

        self.assertEqual(len(current["required_skills"]), 39)
        self.assertEqual(len(current["required_projections"]), 39)
        self.assertIn("libexec/agent_report/diff.py", historical["required_helpers"])
        self.assertNotIn("libexec/agent_report/diff.py", current["required_helpers"])
        self.assertIn("src/agentic_praxis_grimoire/skills.py", historical["required_helpers"])
        self.assertNotIn("src/agentic_praxis_grimoire/skills.py", current["required_helpers"])
        for path in (
            "libexec/apg_distribution_candidate.py",
            "libexec/apg_npm_distribution.py",
            "libexec/apg_python_build_backend.py",
        ):
            self.assertIn(path, current["required_helpers"])
        for path in (
            "go.mod",
            "cmd/apgr/main.go",
            "internal/response/response.go",
            "libexec/apg_go_build.py",
            "npm/templates/launcher/index.js",
            "src/agentic_praxis_grimoire/go_bridge.py",
        ):
            self.assertIn(path, current["critical_files"])

    def test_v08_surface_is_additive_and_inherits_v07_exclusion_rules(self) -> None:
        current = release.audited_policy_surfaces("0.7.0")[0]
        v08 = release.audited_policy_surfaces("0.8.0")[0]

        self.assertTrue(set(current["critical_files"]).issubset(v08["critical_files"]))
        for path in (
            "footprint/doc.go",
            "footprint/json.go",
            "footprint/types.go",
            "footprint/validation.go",
            "internal/cli/footprint.go",
            "skills/footprint.go",
        ):
            self.assertIn(path, v08["critical_files"])
        self.assertEqual(v08["required_skills"], current["required_skills"])
        self.assertFalse(release.is_v08_candidate_path("libexec/agent_report/diff.py"))
        self.assertFalse(release.is_v08_candidate_path("dist/example.whl"))
        self.assertFalse(release.is_v08_candidate_path("private/evaluation.txt"))
        self.assertTrue(release.is_v08_candidate_path("footprint/doc.go"))

        policy = json.loads(
            (REPOSITORY_ROOT / "release" / "public-surface.json").read_text(
                encoding="utf-8"
            )
        )
        for key, expected in v08.items():
            self.assertEqual(policy[key], list(expected))

        private = release.Entry("100644", "blob", "a" * 40, b"private/secret.txt")
        with self.assertRaisesRegex(release.ToolError, "publication-excluded"):
            release.validate_versioned_policy_exclusions((private,), "0.8.0")

    def test_historical_v06_surface_is_snapshot_not_current_tuple_alias(self) -> None:
        original = release.AUDITED_HELPERS
        try:
            release.AUDITED_HELPERS = (*original, "libexec/future-owner.py")
            historical = release.audited_policy_surfaces("0.6.0")[0]
        finally:
            release.AUDITED_HELPERS = original
        self.assertNotIn("libexec/future-owner.py", historical["required_helpers"])
        self.assertEqual(
            release.HISTORICAL_V06_SURFACE_SHA256,
            "40edfbe25f52fae4f15f2801525ce2c50cee5f360b02191393a431ca25f76b51",
        )

    def test_v07_candidate_path_filter_keeps_npm_and_excludes_oracles(self) -> None:
        retained = (
            "bin/apgr",
            "go.mod",
            "npm/launcher/package.json",
            "skills/example/SKILL.md",
        )
        excluded = (
            "libexec/agent_report/diff.py",
            "report/testdata/python_oracle.py",
            "src/agentic_praxis_grimoire/skills.py",
            "src/test/int/python/agentic-praxis-grimoire/libexec/apg_test.int.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/agentic_praxis_grimoire/skills.unit.test.py",
            "bin/apgr-darwin-arm64",
            "dist/example.whl",
            ".scratch/local.txt",
            "out/example.zip",
            "private/evaluation.txt",
        )
        for path in retained:
            with self.subTest(path=path):
                self.assertTrue(release.is_v07_candidate_path(path))
        for path in excluded:
            with self.subTest(path=path):
                self.assertFalse(release.is_v07_candidate_path(path))

    def test_public_symlink_validation_accepts_contained_links_and_rejects_unsafe_targets(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        regular = release.Entry("100644", "blob", "a" * 40, b"target/file")
        link = release.Entry("120000", "blob", "b" * 40, b"link")
        nested = release.Entry("120000", "blob", "c" * 40, b"nested/link")
        with mock.patch.object(release, "entry_bytes", return_value=b"target/file"):
            release.validate_public_symlinks(repository, (regular, link))
        with mock.patch.object(release, "entry_bytes", return_value=b"../target/file"):
            release.validate_public_symlinks(repository, (regular, nested))

        for target, message in (
            (b"", "unsafe"),
            (b"/absolute", "unsafe"),
            (b"bad\\target", "unsafe"),
            (b"../escape", "escapes"),
            (b"private/secret", "private"),
            (b"missing", "missing"),
            (b"\xff", "UTF-8"),
        ):
            with self.subTest(target=target):
                with mock.patch.object(release, "entry_bytes", return_value=target):
                    with self.assertRaisesRegex(release.ToolError, message):
                        release.validate_public_symlinks(repository, (regular, link))

    def test_public_symlink_validation_rejects_committed_cycles(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        first = release.Entry("120000", "blob", "a" * 40, b"first")
        second = release.Entry("120000", "blob", "b" * 40, b"second")

        def content(_repository: release.Repository, entry: release.Entry) -> bytes:
            return b"second" if entry.path == b"first" else b"first"

        with mock.patch.object(release, "entry_bytes", side_effect=content):
            with self.assertRaisesRegex(release.ToolError, "cyclic"):
                release.validate_public_symlinks(repository, (first, second))

    def test_manifest_build_and_release_surface_validate_complete_projection(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        regular = release.Entry("100644", "blob", "c" * 40, b"README.md")
        link = release.Entry("120000", "blob", "d" * 40, b"README-link")
        policy = self.valid_policy()
        with (
            mock.patch.object(release, "load_policy", return_value=policy),
            mock.patch.object(release, "tree_entries", return_value=(regular, link)),
            mock.patch.object(release, "validate_critical") as critical,
            mock.patch.object(release, "validate_public_symlinks") as symlinks,
            mock.patch.object(
                release,
                "entry_bytes",
                side_effect=lambda _repo, entry: b"README.md" if entry is link else b"content",
            ),
        ):
            manifest = release.build_manifest(repository)
        self.assertEqual([item["type"] for item in manifest["entries"]], ["file", "symlink"])
        self.assertEqual(manifest["entries"][1]["symlink_target"], "README.md")
        critical.assert_called_once()
        symlinks.assert_called_once()

        with (
            mock.patch.object(release, "load_policy", return_value=policy),
            mock.patch.object(release, "tree_entries", return_value=(regular,)),
            mock.patch.object(release, "validate_critical") as critical,
            mock.patch.object(release, "validate_public_symlinks") as symlinks,
        ):
            release.validate_public_release_surface(repository, "0.4.0")
        critical.assert_called_once()
        symlinks.assert_called_once()

    def test_versioned_exclusions_and_text_manifest_rendering(self) -> None:
        future = release.HISTORICAL_V03_FORBIDDEN_REPORT_OWNERS[0]
        entry = release.Entry("100644", "blob", "a" * 40, future.encode())
        release.validate_versioned_policy_exclusions((entry,), "0.4.0")
        with self.assertRaisesRegex(release.ToolError, "future owner"):
            release.validate_versioned_policy_exclusions((entry,), "0.3.0")
        manifest = {
            "entries": [{"mode": "100644", "sha256": "abc", "path": "README.md"}]
        }
        self.assertEqual(
            release.render_manifest(manifest, "text"),
            "APG public manifest v1\n100644 abc README.md\n",
        )

    def test_apg54_and_apg55_surfaces_are_v05_only_without_historical_v04_drift(
        self,
    ) -> None:
        historical = release.audited_policy_surfaces("0.4.0")[0]
        current = release.audited_policy_surfaces("0.5.0")[0]
        installer = "bin/install-global-skills"
        transaction = "libexec/global_skills_transaction.py"

        self.assertNotIn(installer, historical["required_wrappers"])
        self.assertNotIn(transaction, historical["required_helpers"])
        self.assertIn(installer, current["required_wrappers"])
        self.assertIn(transaction, current["required_helpers"])
        entry = release.Entry(
            "100755", "blob", "a" * 40, installer.encode("ascii")
        )
        with self.assertRaisesRegex(release.ToolError, "future owner"):
            release.validate_versioned_policy_exclusions(
                (entry,), "0.4.0"
            )
        self.assertTrue(
            release.APG55_V05_CRITICAL.isdisjoint(
                historical["critical_files"]
            )
        )
        self.assertTrue(
            release.APG55_V05_CRITICAL.issubset(
                current["critical_files"]
            )
        )
        for path in sorted(release.APG55_V05_CRITICAL):
            future = release.Entry(
                "100644", "blob", "a" * 40, path.encode("ascii")
            )
            with self.assertRaisesRegex(release.ToolError, "future owner"):
                release.validate_versioned_policy_exclusions(
                    (future,), "0.4.0"
                )
        self.assertEqual(
            release.HISTORICAL_V04_SURFACE_SHA256,
            "4bc8571149c708023712f3963e81e0594d46a9a78da74ac48d8dba3e4b73a083",
        )

    def test_repository_separation_and_output_path_reject_overlap_and_unsafe_types(self) -> None:
        first = release.Repository(Path("/one"), "a" * 40, "b" * 40)
        child = release.Repository(Path("/one/child"), "c" * 40, "d" * 40)
        with self.assertRaises(release.InvocationError):
            release.validate_repository_separation(first, child)
        release.validate_repository_separation(first, release.Repository(Path("/two"), "c" * 40, "d" * 40))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            source = base / "source"
            public = base / "public"
            source.mkdir()
            public.mkdir()
            with self.assertRaises(release.InvocationError):
                release.validate_output_path(source / "candidate", source, public)
            output = base / "candidate"
            release.validate_output_path(output, source, public)
            output.write_text("unsafe")
            with self.assertRaisesRegex(release.InvocationError, "unsafe type"):
                release.validate_output_path(output, source, public)

    def test_object_reference_and_fingerprint_helpers_use_exact_git_bytes(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)

        def git_result(_root: Path, arguments: list[str], **kwargs: object) -> mock.Mock:
            del kwargs
            if arguments[0] == "rev-list":
                return mock.Mock(stdout=b"c\nd\n")
            if arguments[:2] == ["for-each-ref", "--format=%(objectname)"]:
                return mock.Mock(stdout=b"e\n")
            if arguments[0] == "for-each-ref":
                return mock.Mock(stdout=b"refs/heads/main\0a\n")
            if arguments[0] == "ls-files":
                return mock.Mock(stdout=b"index")
            if arguments[0] == "status":
                return mock.Mock(stdout=b"")
            raise AssertionError(arguments)

        with (
            mock.patch.object(release, "run_git", side_effect=git_result),
            mock.patch.object(release, "text_git", side_effect=("a" * 40, "b" * 40)),
        ):
            self.assertEqual(release.reachable_objects(repository), ("c", "d", "e"))
            self.assertEqual(release.reference_map(repository, "refs"), {"refs/heads/main": "a"})
            fingerprint = release.repository_fingerprint(repository)
        self.assertEqual(fingerprint.head, "a" * 40)
        self.assertEqual(fingerprint.index, b"index")

    def test_import_object_requires_identity_preservation(self) -> None:
        source = release.Repository(Path("source"), "a" * 40, "b" * 40)
        with (
            mock.patch.object(release, "text_git", side_effect=("blob", "c" * 40)),
            mock.patch.object(release, "run_git", return_value=mock.Mock(stdout=b"content")),
        ):
            release.import_object(source, Path("destination"), "c" * 40)
        with (
            mock.patch.object(release, "text_git", side_effect=("blob", "wrong")),
            mock.patch.object(release, "run_git", return_value=mock.Mock(stdout=b"content")),
        ):
            with self.assertRaisesRegex(release.ToolError, "identity changed"):
                release.import_object(source, Path("destination"), "c" * 40)

    def test_markdown_link_validation_accepts_external_and_rejects_broken_private_links(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        readme = release.Entry("100644", "blob", "c" * 40, b"docs/README.md")
        target = release.Entry("100644", "blob", "d" * 40, b"docs/target.md")
        with (
            mock.patch.object(release, "tree_entries", return_value=(readme, target)),
            mock.patch.object(
                release,
                "entry_bytes",
                side_effect=lambda _repo, entry: (
                    b"[ok](target.md) [web](https://example.test) [anchor](#x)" if entry is readme else b"target"
                ),
            ),
        ):
            release.validate_markdown_links(repository)
        for body, message in ((b"[bad](missing.md)", "broken"), (b"[bad](../private/x)", "private")):
            with (
                self.subTest(body=body),
                mock.patch.object(release, "tree_entries", return_value=(readme, target)),
                mock.patch.object(release, "entry_bytes", return_value=body),
                self.assertRaisesRegex(release.ToolError, message),
            ):
                release.validate_markdown_links(repository)

    def test_markdown_link_validation_excludes_only_hotspot_testdata(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        fixture = release.Entry(
            "100644",
            "blob",
            "c" * 40,
            b"hotspot/testdata/classification/sample.md",
        )
        human_doc = release.Entry("100644", "blob", "d" * 40, b"docs/README.md")

        with (
            mock.patch.object(release, "tree_entries", return_value=(fixture,)),
            mock.patch.object(release, "entry_bytes", return_value=b"[fixture](target)"),
        ):
            release.validate_markdown_links(repository)

        with (
            mock.patch.object(
                release,
                "tree_entries",
                return_value=(fixture, human_doc),
            ),
            mock.patch.object(release, "entry_bytes", return_value=b"[broken](missing.md)"),
            self.assertRaisesRegex(release.ToolError, "docs/README.md"),
        ):
            release.validate_markdown_links(repository)

    def test_private_policy_and_category_validation_cover_configured_boundaries(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        entry = release.Entry("100755", "blob", "c" * 40, b"bin/tool")
        with tempfile.TemporaryDirectory() as temporary:
            policy_path = Path(temporary) / "policy.json"
            policy_path.write_text('{"forbidden_text_patterns":["SECRET"],"schema_version":1}')
            with (
                mock.patch.object(release, "tree_entries", return_value=(entry,)),
                mock.patch.object(release, "entry_bytes", return_value=b"safe"),
            ):
                release.validate_private_policy(repository, str(policy_path))
            with (
                mock.patch.object(release, "tree_entries", return_value=(entry,)),
                mock.patch.object(release, "entry_bytes", return_value=b"SECRET"),
                self.assertRaisesRegex(release.ToolError, "matched"),
            ):
                release.validate_private_policy(repository, str(policy_path))

        policy = {
            "validation_categories": sorted(release.ALLOWED_CATEGORIES),
            "required_wrappers": ["bin/tool"],
            "required_helpers": [],
            "required_test_entrypoints": [
                "src/test/unit/python/agentic-praxis-grimoire/example.test.py"
            ],
        }
        with (
            mock.patch.object(release, "run_checked_command") as command,
            mock.patch.object(release, "tree_entries", return_value=(entry,)),
            mock.patch.object(release, "entry_bytes", return_value=b"#!/bin/sh\nsafe\n"),
        ):
            release.validate_categories(repository, repository, policy, {"HOME": "/tmp"})
        rendered_commands = [call.args[0] for call in command.call_args_list]
        self.assertTrue(any("pytest" in values for values in rendered_commands))
        self.assertTrue(any(values[:2] == ["bash", "-n"] for values in rendered_commands))

    def test_isolated_environment_and_checked_command_failures_are_bounded(self) -> None:
        candidate = release.Repository(Path("candidate"), "a" * 40, "b" * 40)
        base = release.Repository(Path("base"), "c" * 40, "d" * 40)
        with tempfile.TemporaryDirectory() as temporary:
            environment = release.isolated_validation_environment(Path(temporary), candidate, base)
            self.assertEqual(environment["PWD"], "candidate")
            self.assertEqual(environment["APG12_PUBLIC_V01_ROOT"], "base")
            self.assertTrue(
                environment["PYTHONPATH"].startswith(
                    os.pathsep.join(("candidate/src", "candidate"))
                )
            )
            pytest_root = Path(environment["PYTEST_DEBUG_TEMPROOT"])
            worker_root = Path(environment["TMPDIR"])
            self.assertTrue(pytest_root.is_dir())
            self.assertEqual(pytest_root.parent, worker_root.parent)
            self.assertNotEqual(pytest_root, worker_root)
            self.assertNotIn("OLDPWD", environment)
        with mock.patch.object(
            release.subprocess,
            "run",
            return_value=mock.Mock(returncode=1, stderr=b"failed", stdout=b""),
        ):
            with self.assertRaisesRegex(release.ToolError, "configured validation failed"):
                release.run_checked_command(["tool"], Path("."))

    def test_main_routes_manifest_build_check_and_errors(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        with (
            mock.patch.object(release, "resolve_repository", return_value=repository),
            mock.patch.object(release, "build_manifest", return_value={"entries": []}),
            mock.patch.object(release, "render_manifest", return_value="manifest\n"),
        ):
            self.assertEqual(release.main(["manifest", "--source", "repo"]), 0)
        with mock.patch.object(release, "resolve_repository", side_effect=release.ToolError("bad")):
            self.assertEqual(release.main(["manifest", "--source", "repo"]), 1)

    def test_repository_resolution_rejects_nonworktree_dirty_and_index_flags(self) -> None:
        root = Path("/repo")
        responses = iter(
            (
                mock.Mock(returncode=1, stdout=b""),
                mock.Mock(returncode=0, stdout=b"/repo\n"),
                mock.Mock(returncode=0, stdout=b"dirty"),
                mock.Mock(returncode=0, stdout=b"/repo\n"),
                mock.Mock(returncode=0, stdout=b""),
                mock.Mock(returncode=0, stdout=b"S file\0"),
            )
        )
        with mock.patch.object(release, "run_git", side_effect=lambda *args, **kwargs: next(responses)), mock.patch.object(
            release, "text_git", return_value="true"
        ), mock.patch.object(Path, "resolve", return_value=root):
            with self.assertRaisesRegex(release.ToolError, "not a Git"):
                release.resolve_repository(root, "source")
            with self.assertRaisesRegex(release.ToolError, "clean"):
                release.resolve_repository(root, "source")
            with self.assertRaisesRegex(release.ToolError, "index flags"):
                release.resolve_repository(root, "source")

    def test_semver_tags_skip_nonrelease_tags_and_require_resolvable_release_tags(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        with mock.patch.object(
            release,
            "run_git",
            side_effect=(mock.Mock(stdout=b"not-a-release\nv0.3.0\n"), mock.Mock(returncode=0, stdout=b"c" * 40)),
        ):
            self.assertEqual(release.semver_release_tags(repository), {"c" * 40: [("v0.3.0", "0.3.0")]})
        with mock.patch.object(
            release,
            "run_git",
            side_effect=(mock.Mock(stdout=b"v0.3.0\n"), mock.Mock(returncode=1, stdout=b"")),
        ):
            with self.assertRaisesRegex(release.ToolError, "cannot be resolved"):
                release.semver_release_tags(repository)

    def test_private_policy_none_malformed_and_configured_test_variants(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        release.validate_private_policy(repository, None)
        with self.assertRaisesRegex(release.ToolError, "malformed"):
            release.validate_private_policy(repository, "/missing")
        policy = {
            "validation_categories": ["configured-tests"],
            "required_wrappers": [],
            "required_helpers": [],
            "required_test_entrypoints": ["legacy.test.py", "legacy.test.bats"],
        }
        with mock.patch.object(release, "run_checked_command") as command:
            release.validate_categories(repository, repository, policy, {})
        self.assertEqual(command.call_args_list[0].args[0], ["bats", "legacy.test.bats"])
        self.assertEqual(command.call_args_list[1].args[0], [sys.executable, "legacy.test.py"])

    def test_v07_public_validation_deselects_only_publication_excluded_cases(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        policy = {
            "validation_categories": ["configured-tests"],
            "required_wrappers": [],
            "required_helpers": [],
            "required_test_entrypoints": list(release.V07_TESTS),
        }
        with mock.patch.object(release, "run_checked_command") as command:
            release.validate_categories(repository, repository, policy, {})
        arguments = command.call_args.args[0]
        observed = [
            arguments[index + 1]
            for index, value in enumerate(arguments)
            if value == "--deselect"
        ]
        self.assertEqual(observed, list(release.V07_PUBLIC_VALIDATION_DESELECTIONS))
        self.assertEqual(observed, sorted(set(observed)))
        for node_id in observed:
            self.assertIn(node_id.split("::", 1)[0], release.V07_TESTS)

    def test_v07_public_test_sources_do_not_trigger_confidentiality_scan(self) -> None:
        for relative_path in release.V07_TESTS:
            content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
            for marker in release.LOCAL_PATH_MARKERS:
                self.assertNotIn(marker, content, relative_path)

    def test_require_unchanged_and_confidentiality_failures_are_bounded(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        fingerprint = release.RepositoryFingerprint("a", "b", (), b"", b"", b"")
        with mock.patch.object(release, "repository_fingerprint", return_value=fingerprint):
            release.require_unchanged(repository, fingerprint, "source")
        with mock.patch.object(
            release,
            "repository_fingerprint",
            return_value=release.RepositoryFingerprint("c", "b", (), b"", b"", b""),
        ):
            with self.assertRaisesRegex(release.ToolError, "changed"):
                release.require_unchanged(repository, fingerprint, "source")
        entry = release.Entry("100644", "blob", "c" * 40, b"README.md")
        policy = {"validation_categories": ["confidentiality"], "required_wrappers": [], "required_helpers": [], "required_test_entrypoints": []}
        with mock.patch.object(release, "tree_entries", return_value=(entry,)), mock.patch.object(
            release, "entry_bytes", return_value=release.LOCAL_PATH_MARKERS[0].encode()
        ):
            with self.assertRaisesRegex(release.ToolError, "confidentiality"):
                release.validate_categories(repository, repository, policy, {})

    def test_public_lineage_accepts_exact_v01_terminal_identity(self) -> None:
        commit = release.PUBLIC_V01_COMMIT
        tree = release.PUBLIC_V01_TREE
        repository = release.Repository(Path("repo"), commit, tree)

        def git(_root: Path, arguments: list[str], **kwargs: object) -> mock.Mock:
            del kwargs
            if arguments == ["rev-parse", "refs/tags/v0.1.0"]:
                return mock.Mock(returncode=0, stdout=(commit + "\n").encode())
            if arguments == ["rev-parse", f"{commit}^{{commit}}"]:
                return mock.Mock(returncode=0, stdout=(commit + "\n").encode())
            raise AssertionError(arguments)

        with (
            mock.patch.object(release, "run_git", side_effect=git),
            mock.patch.object(release, "text_git", return_value=tree),
            mock.patch.object(
                release,
                "semver_release_tags",
                return_value={commit: [("v0.1.0", "0.1.0")]},
            ),
        ):
            identities = release.verify_public_release_lineage(
                repository, accepted_commit=commit, accepted_tree=tree
            )
        self.assertEqual(identities, (release.ReleaseIdentity("0.1.0", "v0.1.0", commit, tree),))

    def test_public_lineage_accepts_one_annotated_linear_release(self) -> None:
        accepted = "a" * 40
        accepted_tree = "b" * 40
        head = "c" * 40
        head_tree = "d" * 40
        repository = release.Repository(Path("repo"), head, head_tree)

        def git(_root: Path, arguments: list[str], **kwargs: object) -> mock.Mock:
            del kwargs
            if arguments == ["rev-parse", "refs/tags/v0.1.0"]:
                return mock.Mock(returncode=0, stdout=(accepted + "\n").encode())
            if arguments == ["rev-parse", f"{accepted}^{{commit}}"]:
                return mock.Mock(returncode=0, stdout=(accepted + "\n").encode())
            if arguments[0] == "merge-base":
                return mock.Mock(returncode=0, stdout=b"")
            if arguments[0] == "rev-list":
                return mock.Mock(returncode=0, stdout=f"{head} {accepted}\n".encode())
            raise AssertionError(arguments)

        def text(_root: Path, arguments: list[str], **kwargs: object) -> str:
            del kwargs
            if arguments == ["rev-parse", f"{accepted}^{{tree}}"]:
                return accepted_tree
            if arguments[0] == "cat-file":
                return "tag"
            if arguments[0] == "log":
                return "Release v0.2.0"
            if arguments == ["rev-parse", f"{head}^{{tree}}"]:
                return head_tree
            raise AssertionError(arguments)

        with (
            mock.patch.object(release, "run_git", side_effect=git),
            mock.patch.object(release, "text_git", side_effect=text),
            mock.patch.object(
                release,
                "semver_release_tags",
                return_value={
                    accepted: [("v0.1.0", "0.1.0")],
                    head: [("v0.2.0", "0.2.0")],
                },
            ),
            mock.patch.object(release, "validate_public_release_surface") as validate,
        ):
            identities = release.verify_public_release_lineage(
                repository, accepted_commit=accepted, accepted_tree=accepted_tree
            )
        self.assertEqual(identities[-1], release.ReleaseIdentity("0.2.0", "v0.2.0", head, head_tree))
        validate.assert_called_once_with(repository, "0.2.0")


    def test_candidate_builder_writes_deterministic_release_objects(self) -> None:
        source = release.Repository(Path("source"), "a" * 40, "b" * 40)
        base = release.Repository(Path("base"), "c" * 40, "d" * 40)
        entry = release.Entry("100644", "blob", "e" * 40, b"README.md")
        calls: list[list[str]] = []

        def git(_root: Path, arguments: list[str], **_kwargs: object) -> mock.Mock:
            calls.append(arguments)
            return mock.Mock(
                returncode=1 if arguments[0] == "show-ref" else 0,
                stdout=b"",
            )

        def text(_root: Path, arguments: list[str], **_kwargs: object) -> str:
            values = {
                "write-tree": "f" * 40,
                "commit-tree": "1" * 40,
                "mktag": "2" * 40,
            }
            return values[arguments[0]]

        with (
            mock.patch.object(release, "verify_public_release_lineage"),
            mock.patch.object(release, "load_policy", return_value=self.valid_policy()),
            mock.patch.object(release, "tree_entries", return_value=(entry,)),
            mock.patch.object(release, "validate_critical"),
            mock.patch.object(release, "initialize_candidate"),
            mock.patch.object(release, "import_object"),
            mock.patch.object(release, "run_git", side_effect=git),
            mock.patch.object(release, "text_git", side_effect=text),
        ):
            result = release.build_candidate(
                source,
                base,
                Path("candidate"),
                "0.6.0",
                "2026-07-20T12:00:00-04:00",
                "Release Author",
                "release@example.invalid",
            )
        self.assertEqual(result, ("f" * 40, "1" * 40, "2" * 40))
        self.assertTrue(any(arguments[0] == "update-index" for arguments in calls))
        self.assertTrue(any(arguments[:2] == ["symbolic-ref", "HEAD"] for arguments in calls))



if __name__ == "__main__":
    unittest.main()
