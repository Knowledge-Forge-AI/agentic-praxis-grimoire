#!/usr/bin/env python3
"""Focused unit tests for APG public release parsing and rendering."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from src.test.apg_test_support import repository_root


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
EXPECTED_APG81H_SKILLS = tuple(
    sorted(
        (
            *(
                path
                for path in EXPECTED_V03_SKILLS
                if not path.endswith(
                    "/composing-approved-roadmap-assignments/SKILL.md"
                )
            ),
            "skills/chatgpt/chatgpt-manager-workflow/SKILL.md",
            "skills/chatgpt/composing-approved-roadmap-assignments/SKILL.md",
            "skills/converting-bash-scripts-to-python/SKILL.md",
            "skills/css-language-profile/SKILL.md",
            "skills/dockerfile-profile/SKILL.md",
            "skills/go-cmp-test-profile/SKILL.md",
            "skills/go-test-profile/SKILL.md",
            "skills/javascript-language-profile/SKILL.md",
            "skills/markdown-language-profile/SKILL.md",
            "skills/minitest-test-profile/SKILL.md",
            "skills/nix-test-profile/SKILL.md",
            "skills/nodejs-runtime-profile/SKILL.md",
            "skills/pytest-test-profile/SKILL.md",
            "skills/typescript-language-profile/SKILL.md",
            "skills/vagrantfile-profile/SKILL.md",
        )
    )
)
EXPECTED_APG81H_PROJECTIONS = tuple(
    sorted(
        f".agents/skills/{Path(path).parent.name}"
        for path in EXPECTED_APG81H_SKILLS
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


class APGPublicReleaseCaseMixin:
    def valid_policy(self) -> dict[str, object]:
        surface = release.audited_policy_surfaces("0.5.0")[0]
        return {
            "schema_version": 1,
            "canonical_public_identity": "agentic-praxis-grimoire",
            "excluded_prefix": "private/",
            **{key: list(value) for key, value in surface.items()},
        }

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

    def test_current_audited_surface_requires_all_33_skills(self) -> None:
        self.assertEqual(release.AUDITED_SKILLS, EXPECTED_APG81H_SKILLS)
        self.assertEqual(
            release.AUDITED_PROJECTIONS,
            EXPECTED_APG81H_PROJECTIONS,
        )
        self.assertIn(
            "src/test/fixtures/apg32-minitest-scenario-families.json",
            release.AUDITED_CRITICAL,
        )
        self.assertIn(
            "src/test/unit/python/agentic-praxis-grimoire/skills/"
            "minitest-test-profile/SKILL.unit.test.py",
            release.AUDITED_TESTS,
        )
        self.assertIn(
            "src/test/fixtures/apg33-dockerfile-scenario-families.json",
            release.AUDITED_CRITICAL,
        )
        self.assertIn(
            "src/test/unit/python/agentic-praxis-grimoire/skills/"
            "dockerfile-profile/SKILL.unit.test.py",
            release.AUDITED_TESTS,
        )
        self.assertIn(
            "src/test/fixtures/apg34-vagrantfile-scenario-families.json",
            release.AUDITED_CRITICAL,
        )
        self.assertIn(
            "src/test/unit/python/agentic-praxis-grimoire/skills/"
            "vagrantfile-profile/SKILL.unit.test.py",
            release.AUDITED_TESTS,
        )
        for fixture in (
            "src/test/fixtures/apg37-go-test-scenario-families.json",
            "src/test/fixtures/apg37-go-cmp-scenario-families.json",
            "src/test/fixtures/apg39-nix-test-scenario-families.json",
            "src/test/fixtures/apg66-markdown-language-profile-scenarios.json",
            "src/test/fixtures/apg77-css-language-profile-scenarios.json",
            "src/test/fixtures/apg79-javascript-language-profile-scenarios.json",
        ):
            self.assertIn(fixture, release.AUDITED_CRITICAL)
        for support in (
            "src/test/fixtures/apg64-markdown-scenario-register.md",
            "src/test/support/apg_markdown_candidate_contract.py",
            "src/test/support/apg_markdown_clause_guard_contract.py",
            "src/test/support/apg_markdown_polarity_guard_contract.py",
            "src/test/support/apg_markdown_register_contract.py",
            "src/test/support/apg_markdown_token_guard_contract.py",
            "src/test/support/apg_markdown_vocabulary_contract.py",
            "src/test/support/apg_repository_import_cache_contract.py",
            "docs/evaluations/apg66a-markdown-replay-evidence-truth.md",
            "docs/evaluations/apg66c-markdown-clause-polarity-and-predicate-binding.md",
            "docs/evaluations/apg66d-repository-import-cache-entry-presence.md",
            "docs/status/2026/08/01/00096-apg66a-markdown-replay-evidence-truth-exit.md",
            "docs/status/2026/08/01/00098-apg66c-markdown-clause-polarity-and-predicate-binding-exit.md",
            "docs/status/2026/08/01/00099-apg66d-repository-import-cache-entry-presence-exit.md",
        ):
            self.assertIn(support, release.AUDITED_CRITICAL)
        for test in (
            "src/test/unit/python/agentic-praxis-grimoire/skills/markdown-language-profile/SKILL.unit.test.py",
            "src/test/int/python/agentic-praxis-grimoire/skills/markdown-language-profile/SKILL.int.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_candidate_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_clause_guard_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_polarity_guard_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_register_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_token_guard_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_markdown_vocabulary_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_import_cache_contract.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/skills/css-language-profile/SKILL.unit.test.py",
            "src/test/unit/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.unit.test.py",
            "src/test/int/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.int.test.py",
        ):
            self.assertIn(test, release.AUDITED_TESTS)

    def test_policy_surfaces_are_exactly_version_bounded(self) -> None:
        historical_v02 = release.audited_policy_surfaces("0.2.0")
        historical_v03 = release.audited_policy_surfaces("0.3.0")
        current = release.audited_policy_surfaces("0.5.0")

        self.assertEqual(historical_v02[0]["required_skills"], HISTORICAL_V02_SKILLS)
        self.assertEqual(historical_v03[0]["required_skills"], EXPECTED_V03_SKILLS)
        self.assertEqual(current[0]["required_skills"], EXPECTED_APG81H_SKILLS)
        self.assertEqual(
            current[0]["required_projections"],
            EXPECTED_APG81H_PROJECTIONS,
        )
        self.assertIn("libexec/agent-report/common.sh", historical_v03[0]["required_helpers"])
        self.assertNotIn("bin/git-diff-report", historical_v03[0]["required_wrappers"])
        self.assertIn("libexec/agent_report/diff.py", current[0]["required_helpers"])
        self.assertIn("bin/git-diff-report", current[0]["required_wrappers"])
        self.assertEqual(len(historical_v02), 1)
        self.assertEqual(len(historical_v03), 1)
        self.assertEqual(len(current), 1)

    def test_historical_v0_4_excludes_every_apg66_owner(self) -> None:
        historical = release.audited_policy_surfaces("0.4.0")[0]
        current = release.audited_policy_surfaces("0.5.0")[0]
        for key, owners in (
            ("required_skills", release.APG66_V05_SKILLS),
            ("required_projections", release.APG66_V05_PROJECTIONS),
            ("required_test_entrypoints", release.APG66_V05_TESTS),
            ("critical_files", release.APG66_V05_CRITICAL),
        ):
            self.assertTrue(owners <= set(current[key]))
            self.assertFalse(owners & set(historical[key]))

    def test_historical_v0_4_excludes_apg66d_records(self) -> None:
        historical = release.audited_policy_surfaces("0.4.0")[0]
        current = release.audited_policy_surfaces("0.5.0")[0]
        owners = release.APG66D_V05_CRITICAL
        self.assertTrue(owners <= set(current["critical_files"]))
        self.assertFalse(owners & set(historical["critical_files"]))

    def test_historical_v0_4_excludes_every_apg77d_owner(self) -> None:
        historical = release.audited_policy_surfaces("0.4.0")[0]
        current = release.audited_policy_surfaces("0.5.0")[0]
        for key, owners in (
            ("required_skills", release.APG77D_V05_SKILLS),
            ("required_projections", release.APG77D_V05_PROJECTIONS),
            ("required_test_entrypoints", release.APG77D_V05_TESTS),
            ("critical_files", release.APG77D_V05_CRITICAL),
        ):
            self.assertTrue(owners <= set(current[key]))
            self.assertFalse(owners & set(historical[key]))

    def test_historical_v0_4_excludes_every_apg79e_owner(self) -> None:
        historical = release.audited_policy_surfaces("0.4.0")[0]
        current = release.audited_policy_surfaces("0.5.0")[0]
        for key, owners in (
            ("required_skills", release.APG79E_V05_SKILLS),
            ("required_projections", release.APG79E_V05_PROJECTIONS),
            ("required_test_entrypoints", release.APG79E_V05_TESTS),
            ("critical_files", release.APG79E_V05_CRITICAL),
        ):
            self.assertTrue(owners <= set(current[key]))
            self.assertFalse(owners & set(historical[key]))

    def test_historical_v0_3_surface_is_independent_of_current_arrays(self) -> None:
        historical = release.audited_policy_surfaces("0.3.0")[0]
        original = (
            release.AUDITED_LICENSING,
            release.AUDITED_SKILLS,
            release.AUDITED_PROJECTIONS,
            release.AUDITED_CRITICAL,
        )
        try:
            release.AUDITED_LICENSING = (*release.AUDITED_LICENSING, "FUTURE-LICENSE")
            release.AUDITED_SKILLS = (*release.AUDITED_SKILLS, "skills/future/SKILL.md")
            release.AUDITED_PROJECTIONS = (*release.AUDITED_PROJECTIONS, ".agents/skills/future")
            release.AUDITED_CRITICAL = (*release.AUDITED_CRITICAL, "docs/future.md")
            self.assertEqual(release.audited_policy_surfaces("0.3.0")[0], historical)
        finally:
            (
                release.AUDITED_LICENSING,
                release.AUDITED_SKILLS,
                release.AUDITED_PROJECTIONS,
                release.AUDITED_CRITICAL,
            ) = original

    def test_historical_v0_4_surface_fingerprint_fails_closed(self) -> None:
        historical = release.audited_policy_surfaces("0.4.0")[0]
        original = release.HISTORICAL_V04_HELPERS
        try:
            release.HISTORICAL_V04_HELPERS = (
                *release.HISTORICAL_V04_HELPERS,
                "libexec/future-owner.py",
            )
            with self.assertRaisesRegex(
                release.ToolError,
                "historical public v0.4.0 policy surface changed",
            ):
                release.audited_policy_surfaces("0.4.0")
        finally:
            release.HISTORICAL_V04_HELPERS = original
        self.assertEqual(release.audited_policy_surfaces("0.4.0")[0], historical)

    def test_unknown_policy_surface_identity_fails_closed(self) -> None:
        for version in ("0.1.0", "0.3.1", "0.5.1", "1.0.0", "invalid"):
            with self.subTest(version=version), self.assertRaises(release.ToolError):
                release.audited_policy_surfaces(version)

    def test_git_environment_removes_repository_and_numbered_config_state(self) -> None:
        self.assertEqual(release.git_environment()["GIT_OPTIONAL_LOCKS"], "0")
        with mock.patch.dict(
            release.os.environ,
            {
                "GIT_DIR": "unsafe",
                "GIT_CONFIG_KEY_0": "unsafe",
                "GIT_CONFIG_VALUE_0": "unsafe",
                "KEEP": "yes",
            },
            clear=True,
        ):
            value = release.git_environment({"EXTRA": "yes"})
        self.assertNotIn("GIT_DIR", value)
        self.assertNotIn("GIT_CONFIG_KEY_0", value)
        self.assertEqual(value["KEEP"], "yes")
        self.assertEqual(value["EXTRA"], "yes")

    def test_load_policy_rejects_each_schema_and_array_failure(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        policy = self.valid_policy()
        mutations = [
            ({**policy, "schema_version": True}, "schema version"),
            (
                {**policy, "canonical_public_identity": "other"},
                "canonical identity",
            ),
            ({**policy, "excluded_prefix": "public/"}, "excluded prefix"),
            (
                {**policy, "required_helpers": "not-an-array"},
                "string array",
            ),
            (
                {**policy, "required_helpers": ["z", "a"]},
                "sorted and unique",
            ),
            (
                {**policy, "required_helpers": ["../unsafe"]},
                "unsafe path",
            ),
            (
                {**policy, "required_helpers": ["private/unsafe"]},
                "private paths",
            ),
            (
                {**policy, "validation_categories": ["unknown"]},
                "unknown validation",
            ),
            (
                {**policy, "required_helpers": ["libexec/future.py"]},
                "audited schema",
            ),
        ]

        for candidate, message in mutations:
            raw = json.dumps(candidate, sort_keys=True).encode()
            with self.subTest(message=message):
                with mock.patch.object(release, "committed_bytes", return_value=raw):
                    with self.assertRaisesRegex(release.ToolError, message):
                        release.load_policy(repository)

    def test_load_policy_rejects_oversized_malformed_and_wrong_top_level(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        for raw in (b"x" * (256 * 1024 + 1), b"{", b"[]", b'{"schema_version":1}'):
            with self.subTest(size=len(raw)):
                with mock.patch.object(release, "committed_bytes", return_value=raw):
                    with self.assertRaises(release.ToolError):
                        release.load_policy(repository)

    def test_tree_entry_parser_rejects_malformed_unsafe_and_unsupported_rows(self) -> None:
        repository = release.Repository(Path("repo"), "a" * 40, "b" * 40)
        outputs = (
            b"malformed\0",
            b"100644 blob " + b"a" * 40 + b"\t../unsafe\0",
            b"040000 tree " + b"a" * 40 + b"\tdirectory\0",
        )
        for output in outputs:
            result = mock.Mock(stdout=output)
            with self.subTest(output=output[:12]):
                with mock.patch.object(release, "run_git", return_value=result):
                    with self.assertRaises(release.ToolError):
                        release.tree_entries(repository)

    def test_critical_validation_reports_every_required_owner_class(self) -> None:
        policy = self.valid_policy()
        for key in (
            "critical_files",
            "required_helpers",
            "required_licensing_files",
            "required_projections",
            "required_skills",
            "required_test_entrypoints",
            "required_wrappers",
        ):
            isolated = {**policy, key: [f"missing/{key}"]}
            present = {
                path
                for owner in (
                    "critical_files",
                    "required_helpers",
                    "required_licensing_files",
                    "required_projections",
                    "required_skills",
                    "required_test_entrypoints",
                    "required_wrappers",
                )
                for path in isolated[owner]
                if path != f"missing/{key}"
            }
            entries = tuple(
                release.Entry("100644", "blob", "a" * 40, path.encode())
                for path in present
            )
            with self.subTest(key=key), self.assertRaisesRegex(
                release.ToolError, f"missing/{key}"
            ):
                release.validate_critical(entries, isolated)

    def test_candidate_checker_reports_projection_set_and_content_drift(self) -> None:
        source = release.Repository(Path("source"), "a" * 40, "b" * 40)
        base = release.Repository(Path("base"), "c" * 40, "d" * 40)
        candidate = release.Repository(Path("candidate"), "e" * 40, "f" * 40)
        first = release.Entry("100644", "blob", "1" * 40, b"README.md")
        second = release.Entry("100644", "blob", "2" * 40, b"NOTICE")
        cases = (
            ((first,), (), "missing README.md"),
            ((), (second,), "extra NOTICE"),
            ((first,), (second,), "missing README.md extra NOTICE"),
        )
        for source_entries, candidate_entries, message in cases:
            with (
                self.subTest(message=message),
                mock.patch.object(release, "verify_public_release_lineage"),
                mock.patch.object(release, "load_policy", return_value=self.valid_policy()),
                mock.patch.object(release, "tree_entries", side_effect=(source_entries, candidate_entries)),
                mock.patch.object(release, "validate_critical"),
                mock.patch.object(release, "entry_bytes", return_value=b"content"),
            ):
                with self.assertRaisesRegex(release.ToolError, message):
                    release.check_candidate(source, base, candidate, "0.4.0", None)
        with (
            mock.patch.object(release, "verify_public_release_lineage"),
            mock.patch.object(release, "load_policy", return_value=self.valid_policy()),
            mock.patch.object(release, "tree_entries", side_effect=((first,), (first,))),
            mock.patch.object(release, "validate_critical"),
            mock.patch.object(release, "entry_bytes", side_effect=(b"one", b"two")),
        ):
            with self.assertRaisesRegex(release.ToolError, "mode, bytes"):
                release.check_candidate(source, base, candidate, "0.4.0", None)

    def test_candidate_checker_reports_each_history_identity_mismatch(self) -> None:
        source = release.Repository(Path("source"), "a" * 40, "b" * 40)
        base = release.Repository(Path("base"), "c" * 40, "d" * 40)
        candidate = release.Repository(Path("candidate"), "e" * 40, "f" * 40)
        entry = release.Entry("100644", "blob", "1" * 40, b"README.md")
        metadata = "Author\0author@example.invalid\0" + "2026-07-20T12:00:00-04:00"
        defaults = {
            ("rev-parse", "HEAD^"): base.head,
            ("rev-list", "--parents", "-n", "1", "HEAD"): f"{candidate.head} {base.head}",
            ("rev-list", "--count", f"{base.head}..HEAD"): "1",
            ("branch", "--show-current"): "release/0.4.0",
            ("log", "-1", "--format=%s"): "Release v0.4.0",
            ("cat-file", "-t", "refs/tags/v0.4.0"): "tag",
            ("show", "-s", "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI", "HEAD"): f"{metadata}\0{metadata}",
            ("for-each-ref", "--format=%(taggername)%00%(taggeremail:trim)%00%(taggerdate:iso-strict)%00%(contents:subject)", "refs/tags/v0.4.0"): f"{metadata}\0Release v0.4.0",
        }
        cases = (
            (("rev-parse", "HEAD^"), "wrong", "sole parent"),
            (("rev-list", "--parents", "-n", "1", "HEAD"), candidate.head, "exactly one parent"),
            (("rev-list", "--count", f"{base.head}..HEAD"), "2", "exactly one commit"),
            (("branch", "--show-current"), "main", "wrong release branch"),
            (("log", "-1", "--format=%s"), "wrong", "subject is incorrect"),
            (("cat-file", "-t", "refs/tags/v0.4.0"), "commit", "annotated tag"),
        )
        for key, value, message in cases:
            values = {**defaults, key: value}
            with (
                self.subTest(message=message),
                mock.patch.object(release, "verify_public_release_lineage"),
                mock.patch.object(release, "load_policy", return_value=self.valid_policy()),
                mock.patch.object(release, "tree_entries", side_effect=((entry,), (entry,))),
                mock.patch.object(release, "validate_critical"),
                mock.patch.object(release, "entry_bytes", return_value=b"content"),
                mock.patch.object(
                    release,
                    "text_git",
                    side_effect=lambda _root, arguments, **_kwargs: values[tuple(arguments)],
                ),
                mock.patch.object(
                    release,
                    "run_git",
                    return_value=mock.Mock(returncode=0, stdout=(candidate.head + "\n").encode()),
                ),
            ):
                with self.assertRaisesRegex(release.ToolError, message):
                    release.check_candidate(source, base, candidate, "0.4.0", None)

        for key, value, message in (
            (("show", "-s", "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI", "HEAD"), "bad", "author and committer"),
            (("for-each-ref", "--format=%(taggername)%00%(taggeremail:trim)%00%(taggerdate:iso-strict)%00%(contents:subject)", "refs/tags/v0.4.0"), "bad", "annotated-tag metadata"),
        ):
            values = {**defaults, key: value}
            with (
                self.subTest(message=message),
                mock.patch.object(release, "verify_public_release_lineage"),
                mock.patch.object(release, "load_policy", return_value=self.valid_policy()),
                mock.patch.object(release, "tree_entries", side_effect=((entry,), (entry,))),
                mock.patch.object(release, "validate_critical"),
                mock.patch.object(release, "entry_bytes", return_value=b"content"),
                mock.patch.object(
                    release,
                    "text_git",
                    side_effect=lambda _root, arguments, **_kwargs: values[tuple(arguments)],
                ),
                mock.patch.object(
                    release,
                    "run_git",
                    return_value=mock.Mock(returncode=0, stdout=(candidate.head + "\n").encode()),
                ),
            ):
                with self.assertRaisesRegex(release.ToolError, message):
                    release.check_candidate(source, base, candidate, "0.4.0", None)
