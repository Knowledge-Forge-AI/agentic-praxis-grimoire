"""Offline release tree and attestation refusal contracts."""

from pathlib import Path
import subprocess
from unittest import mock

import apg_public_release as release


class ReleaseBoundaryCases:
    def test_local_browser_selection_is_exact_and_separate_from_public_policy(self):
        nodes = release.LOCAL_BROWSER_DEFERRAL_NODES
        repository = release.Repository(Path("candidate"), "a" * 40, "b" * 40)
        policy = dict(release.audited_policy_surfaces("0.12.0")[0])
        policy["validation_categories"] = ["configured-tests"]
        files = tuple(sorted({node.split("::")[0] for node in nodes}))
        with mock.patch.object(release, "public_python_selection", return_value=files), \
             mock.patch.object(release, "run_checked_command") as command:
            for local in ((), nodes):
                command.reset_mock()
                release.validate_categories(repository, repository, policy, {}, "0.12.0",
                                            local_browser_deselections=local)
                argv = next(call.args[0] for call in command.call_args_list if "pytest" in call.args[0])
                self.assertEqual([node for node in nodes if node in argv], list(local))
                self.assertEqual(argv[-len(files):], list(files))
        self.assertTrue(set(nodes).isdisjoint(release.PUBLIC_VALIDATION_DESELECTIONS_BY_VERSION["0.12.0"]))
        for version, local in (("0.11.0", nodes), ("0.12.0", nodes[:3]), ("0.12.0", nodes + nodes[:1])):
            with self.subTest(version=version, nodes=local), self.assertRaises(release.ToolError):
                release.validate_categories(repository, repository, policy, {}, version,
                                            local_browser_deselections=local)
        for version, untagged, local in (("0.12.0", False, nodes), ("0.11.0", True, nodes), ("0.12.0", True, nodes[:3])):
            with self.subTest(version=version, untagged=untagged), self.assertRaises(release.ToolError):
                release.check_candidate(repository, repository, repository, version, None,
                                        untagged=untagged, local_browser_deselections=local)
        # Exact local selection must still execute the ordinary repository guard.
        with mock.patch.object(release, "validate_repository_separation", side_effect=release.ToolError("separation")):
            with self.assertRaisesRegex(release.ToolError, "separation"):
                release.check_candidate(repository, repository, repository, "0.12.0", None,
                                        untagged=True, local_browser_deselections=nodes)

    def test_candidate_version_selection_retains_compatibility_and_excludes_private_paths(self):
        repository = release.Repository(Path("synthetic-source"), "a" * 40, "b" * 40)
        public = release.Entry("100644", "blob", "c" * 40, b"README.md")
        private = release.Entry("100644", "blob", "d" * 40, b"private/evidence.json")
        generated = release.Entry("100644", "blob", "e" * 40, b"src/__pycache__/cached.pyc")
        entries = (public, private, generated)
        # Only the Git tree read is substituted; version selection and filters are real.
        with mock.patch.object(release, "tree_entries", return_value=entries):
            for version in ("0.7.0", "0.8.0", "0.8.1", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.12.0-rc.1+build"):
                with self.subTest(version=version):
                    self.assertEqual(release.public_candidate_entries(repository, version), (public,))
            for version in ("0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0"):
                with self.subTest(version=version):
                    self.assertEqual(release.public_candidate_entries(repository, version), entries)
            for version in ("not-a-version", "0.13.0", "0.1.0"):
                with self.subTest(version=version), self.assertRaisesRegex(release.ToolError, "malformed or unsupported"):
                    release.public_candidate_entries(repository, version)

    def test_tree_reader_refuses_unsafe_duplicate_and_nonblob_records(self):
        repository = release.Repository(Path("synthetic-source"), "a" * 40, "b" * 40)
        metadata = b"100644 blob " + b"c" * 40 + b"\t"
        cases = (
            (b"malformed\0", "malformed tree metadata"),
            (metadata + b"safe\0" + metadata + b"safe\0", "unsafe or duplicate"),
            (metadata + b"/absolute\0", "unsafe or duplicate"),
            (metadata + b"parent/../escape\0", "unsafe or duplicate"),
            (metadata + b"empty//component\0", "unsafe or duplicate"),
            (b"160000 commit " + b"c" * 40 + b"\tsubmodule\0", "unsupported public Git entry"),
            (b"100600 blob " + b"c" * 40 + b"\tmode\0", "unsupported public Git entry"),
        )
        for output, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic), mock.patch.object(
                release, "run_git", return_value=subprocess.CompletedProcess([], 0, output, b"")
            ), self.assertRaisesRegex(release.ToolError, diagnostic):
                release.tree_entries(repository)

    def test_merged_source_refuses_invalid_attestations_before_git_access(self):
        source = release.Repository(Path("source"), "a" * 40, "b" * 40)
        base = release.Repository(Path("base"), "c" * 40, "d" * 40)
        merged = release.Repository(Path("merged"), "e" * 40, "f" * 40)
        valid = dict(version="0.12.0", approved_pr="https://example.invalid/pull/1",
                     required_checks={"ci": "success"}, premerge_main=base.head)
        cases = (
            ({"version": "0.10.0"}, "only available"),
            ({"approved_pr": " "}, "approved public staging PR"),
            ({"premerge_main": "short"}, "pre-merge public main identity"),
            ({"merged_commit": "UPPERCASE"}, "merged commit identity"),
        )
        with mock.patch.object(release, "run_git", side_effect=AssertionError("Git must not run")):
            for mutation, diagnostic in cases:
                with self.subTest(mutation=mutation), self.assertRaisesRegex(release.InvocationError, diagnostic):
                    release.check_merged_source(source, base, merged, **{**valid, **mutation})
