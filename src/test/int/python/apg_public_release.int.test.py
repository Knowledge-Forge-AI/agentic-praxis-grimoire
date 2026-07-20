#!/usr/bin/env python3
"""Behavioral contract tests for bin/apg-public-release."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Callable
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
COMMAND = REPOSITORY_ROOT / "bin" / "apg-public-release"
VERSION = "0.2.0-apg12.1"
RELEASE_DATE = "2026-07-20T12:00:00-04:00"


class APGPublicReleaseTests(unittest.TestCase):
    """Exercise release construction only in disposable repositories."""

    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="apg-public-release-")
        self.root = Path(self.temporary.name)
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "HOME": str(self.root / "home"),
                "LC_ALL": "C",
                "LANG": "C",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        Path(self.environment["HOME"]).mkdir()
        self.source = self.make_source(self.root / "source")
        self.base = self.make_base(self.root / "base")
        self.launcher = self.root / "apg-public-release-test-launcher.py"
        self.launcher.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'libexec')!r})\n"
            "import apg_public_release as command\n"
            f"command.PUBLIC_V01_COMMIT = {self.git(self.base, 'rev-parse', 'HEAD').stdout.strip()!r}\n"
            f"command.PUBLIC_V01_TREE = {self.git(self.base, 'rev-parse', 'HEAD^{tree}').stdout.strip()!r}\n"
            "raise SystemExit(command.main())\n"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(
        self, repo: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo), *arguments],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment,
        )

    def initialize(self, path: Path) -> None:
        path.mkdir(parents=True)
        self.git(path, "init", "-q", "-b", "main")
        self.git(path, "config", "user.name", "APG Test")
        self.git(path, "config", "user.email", "apg-test@example.invalid")

    def commit_all(self, repo: Path, subject: str) -> str:
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", subject)
        return self.git(repo, "rev-parse", "HEAD").stdout.strip()

    def policy(self) -> dict[str, object]:
        return json.loads((REPOSITORY_ROOT / "release" / "public-surface.json").read_text())

    def write_policy(self, repo: Path, value: dict[str, object] | None = None) -> None:
        path = repo / "release" / "public-surface.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value or self.policy(), indent=2, sort_keys=True) + "\n")

    def make_source(self, path: Path) -> Path:
        self.initialize(path)
        for name, content in {
            "README.md": "# Test\n\n[notice](NOTICE)\n",
            "LICENSE": "test license\n",
            "NOTICE": "test notice\n",
            "ordinary.txt": "ordinary bytes\n",
            "name with spaces.bin": "space path\n",
            "private/internal.txt": "excluded\n",
        }.items():
            target = path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        (path / "binary.bin").write_bytes(b"\x00\xff\x10binary\n")
        self.write_policy(path)
        policy = self.policy()
        for public_path in policy["critical_files"]:
            target = path / public_path
            if not os.path.lexists(target):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# Test owner\n")
        for public_path in policy["required_helpers"]:
            target = path / public_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# fixed helper fixture\n")
        for public_path in policy["required_licensing_files"]:
            target = path / public_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("fixture licensing owner\n")
        for public_path in policy["required_skills"]:
            target = path / public_path
            target.parent.mkdir(parents=True, exist_ok=True)
            name = target.parent.name
            target.write_text(f"---\nname: {name}\ndescription: fixture\n---\n\n# Fixture\n")
        for public_path in policy["required_projections"]:
            target = path / public_path
            target.parent.mkdir(parents=True, exist_ok=True)
            name = target.name
            target.symlink_to(f"../../skills/{name}", target_is_directory=True)
        for public_path in policy["required_wrappers"]:
            target = path / public_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("#!/bin/sh\nexit 0\n")
            target.chmod(0o755)
        for public_path in policy["required_test_entrypoints"]:
            target = path / public_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.suffix == ".bats":
                target.write_text('#!/usr/bin/env bats\n@test "fixture" { true; }\n')
            else:
                target.write_text("print('ok')\n")
        (path / "relative-link").symlink_to("ordinary.txt")
        self.commit_all(path, "Source")
        return path

    def make_base(self, path: Path) -> Path:
        self.initialize(path)
        (path / "README.md").write_text("# Public base\n")
        self.commit_all(path, "Release v0.1.0")
        self.git(path, "tag", "v0.1.0")
        return path

    def run_command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.launcher), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment,
            cwd=self.root,
        )

    def build(
        self,
        output: Path | None = None,
        source: Path | None = None,
        *,
        base: Path | None = None,
        version: str = VERSION,
    ) -> tuple[Path, subprocess.CompletedProcess[str]]:
        selected = output or (self.root / "candidate")
        result = self.run_command(
            "build",
            "--source",
            str(source or self.source),
            "--base",
            str(base or self.base),
            "--output",
            str(selected),
            "--version",
            version,
            "--release-date",
            RELEASE_DATE,
            "--author-name",
            "APG Release Test",
            "--author-email",
            "release@example.invalid",
        )
        return selected, result

    def check_candidate(
        self,
        candidate: Path,
        source: Path | None = None,
        *,
        base: Path | None = None,
        version: str = VERSION,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_command(
            "check",
            "--source",
            str(source or self.source),
            "--base",
            str(base or self.base),
            "--candidate",
            str(candidate),
            "--version",
            version,
        )

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")

    def fingerprint(self, repo: Path) -> tuple[str, str, str, str, str, str]:
        return (
            self.git(repo, "rev-parse", "HEAD").stdout,
            self.git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout,
            self.git(repo, "show", "HEAD^{tree}").stdout,
            self.git(repo, "for-each-ref", "--format=%(refname)%00%(objectname)", "refs").stdout,
            self.git(repo, "ls-files", "--stage").stdout,
            self.git(repo, "ls-files", "-v").stdout,
        )

    def copy_base(self, name: str) -> Path:
        target = self.root / name
        shutil.copytree(self.base, target, symlinks=True)
        return target

    def append_release(
        self,
        repo: Path,
        version: str,
        *,
        subject: str | None = None,
        parents: tuple[str, ...] | None = None,
    ) -> str:
        tree = self.git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
        selected_parents = parents or (self.git(repo, "rev-parse", "HEAD").stdout.strip(),)
        arguments = ["commit-tree", tree]
        for parent in selected_parents:
            arguments.extend(["-p", parent])
        arguments.extend(["-m", subject or f"Release v{version}"])
        commit = self.git(repo, *arguments).stdout.strip()
        self.git(repo, "update-ref", "refs/heads/main", commit)
        self.git(repo, "reset", "-q", "--hard", commit)
        self.git(repo, "tag", "-a", f"v{version}", "-m", f"Release v{version}")
        return commit

    def test_01_manifest_is_deterministic_in_text_and_json(self) -> None:
        text_one = self.run_command("manifest", "--source", str(self.source), "--format", "text")
        text_two = self.run_command("manifest", "--source", str(self.source), "--format", "text")
        json_result = self.run_command("manifest", "--source", str(self.source), "--format", "json")
        self.assert_success(text_one)
        self.assertEqual(text_one.stdout, text_two.stdout)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertNotIn("source_commit", payload)
        self.assertNotIn("source_tree", payload)
        self.assertNotIn(self.git(self.source, "rev-parse", "HEAD").stdout.strip(), text_one.stdout)
        self.assertNotIn("private/internal.txt", text_one.stdout)

    def test_02_manifest_requires_clean_source_and_valid_policy(self) -> None:
        (self.source / "ordinary.txt").write_text("dirty\n")
        self.assertEqual(self.run_command("manifest", "--source", str(self.source)).returncode, 1)
        self.git(self.source, "checkout", "--", "ordinary.txt")
        (self.source / "release" / "public-surface.json").write_text("{}\n")
        self.commit_all(self.source, "Malformed policy")
        result = self.run_command("manifest", "--source", str(self.source))
        self.assertEqual(result.returncode, 1)
        self.assertIn("policy", result.stderr.lower())

    def test_03_build_preserves_projection_bytes_modes_links_and_paths(self) -> None:
        candidate, result = self.build()
        self.assert_success(result)
        self.assertFalse((candidate / "private").exists())
        self.assertEqual((candidate / "ordinary.txt").read_bytes(), (self.source / "ordinary.txt").read_bytes())
        self.assertEqual((candidate / "binary.bin").read_bytes(), b"\x00\xff\x10binary\n")
        self.assertEqual((candidate / "name with spaces.bin").read_bytes(), b"space path\n")
        self.assertTrue((candidate / "relative-link").is_symlink())
        self.assertEqual(os.readlink(candidate / "relative-link"), "ordinary.txt")
        self.assertEqual(stat.S_IMODE((candidate / "bin" / "apg-project-skills").stat().st_mode), 0o755)

    def test_04_build_requires_clean_source_and_base_without_mutation(self) -> None:
        before_source = self.fingerprint(self.source)
        before_base = self.fingerprint(self.base)
        (self.base / "dirty").write_text("dirty\n")
        result = self.build()[1]
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.fingerprint(self.source), before_source)
        self.assertEqual(self.git(self.base, "rev-parse", "HEAD").stdout, before_base[0])

    def test_05_output_safety_refuses_nonempty_symlink_and_symlink_ancestor(self) -> None:
        same_repository = self.run_command(
            "build",
            "--source",
            str(self.source),
            "--base",
            str(self.source),
            "--output",
            str(self.root / "same-repository"),
            "--version",
            VERSION,
            "--release-date",
            RELEASE_DATE,
            "--author-name",
            "APG Release Test",
            "--author-email",
            "release@example.invalid",
        )
        self.assertEqual(same_repository.returncode, 2)
        nonempty = self.root / "nonempty"
        nonempty.mkdir()
        (nonempty / "keep").write_text("keep\n")
        self.assertEqual(self.build(nonempty)[1].returncode, 2)
        target = self.root / "target"
        target.mkdir()
        link = self.root / "output-link"
        link.symlink_to(target, target_is_directory=True)
        self.assertEqual(self.build(link)[1].returncode, 2)
        unsafe_parent = self.root / "unsafe-parent"
        unsafe_parent.symlink_to(target, target_is_directory=True)
        self.assertEqual(self.build(unsafe_parent / "candidate")[1].returncode, 2)
        source_child = self.source / "candidate"
        source_result = self.build(source_child)[1]
        self.assertEqual(source_result.returncode, 2, source_result.stderr)
        self.assertFalse(source_child.exists())
        base_child = self.base / "candidate"
        self.assertEqual(self.build(base_child)[1].returncode, 2)
        self.assertFalse(base_child.exists())

    def test_06_build_creates_one_deterministic_release_commit_and_tag(self) -> None:
        first, first_result = self.build(self.root / "first")
        second, second_result = self.build(self.root / "second")
        self.assert_success(first_result)
        self.assert_success(second_result)
        for repo in (first, second):
            self.assertEqual(self.git(repo, "rev-list", "--count", "v0.1.0..HEAD").stdout.strip(), "1")
            self.assertEqual(self.git(repo, "rev-parse", "HEAD^").stdout, self.git(self.base, "rev-parse", "HEAD").stdout)
            self.assertEqual(self.git(repo, "rev-parse", f"v{VERSION}^{{commit}}").stdout, self.git(repo, "rev-parse", "HEAD").stdout)
            self.assertEqual(self.git(repo, "log", "-1", "--format=%s").stdout.strip(), f"Release v{VERSION}")
            metadata = self.git(repo, "show", "-s", "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI").stdout.strip().split("\x00")
            self.assertEqual(metadata[:3], metadata[3:])
            self.assertEqual(metadata[:2], ["APG Release Test", "release@example.invalid"])
            self.assertEqual(metadata[2], RELEASE_DATE)
        self.assertEqual(self.git(first, "rev-parse", "HEAD").stdout, self.git(second, "rev-parse", "HEAD").stdout)
        self.assertEqual(self.git(first, "rev-parse", f"v{VERSION}^{{tag}}").stdout, self.git(second, "rev-parse", f"v{VERSION}^{{tag}}").stdout)

    def test_07_check_accepts_exact_candidate_and_is_read_only(self) -> None:
        candidate, build = self.build()
        self.assert_success(build)
        before_source = self.fingerprint(self.source)
        before_base = self.fingerprint(self.base)
        before = self.fingerprint(candidate)
        result = self.check_candidate(candidate)
        self.assert_success(result)
        self.assertEqual(self.fingerprint(candidate), before)
        self.assertEqual(self.fingerprint(self.source), before_source)
        self.assertEqual(self.fingerprint(self.base), before_base)
        self_comparison = self.run_command(
            "check",
            "--source",
            str(candidate),
            "--base",
            str(self.base),
            "--candidate",
            str(candidate),
            "--version",
            VERSION,
        )
        self.assertEqual(self_comparison.returncode, 2)

    def test_08_check_rejects_omission_extra_bytes_mode_link_and_private_path(self) -> None:
        mutations = (
            ("omit", lambda repo: (repo / "ordinary.txt").unlink()),
            ("extra", lambda repo: (repo / "extra.txt").write_text("extra\n")),
            ("bytes", lambda repo: (repo / "ordinary.txt").write_text("changed\n")),
            ("mode", lambda repo: os.chmod(repo / "bin" / "apg-project-skills", 0o644)),
            ("link", lambda repo: (repo / "relative-link").unlink()),
            ("private", lambda repo: ((repo / "private").mkdir(), (repo / "private" / "leak").write_text("leak\n"))),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                candidate, result = self.build(self.root / label)
                self.assert_success(result)
                mutate(candidate)
                if label == "link":
                    (candidate / "relative-link").symlink_to("README.md")
                self.git(candidate, "add", "-A")
                self.git(candidate, "commit", "-q", "-m", f"tamper {label}")
                self.assertEqual(self.check_candidate(candidate).returncode, 1)

    def test_09_check_rejects_missing_critical_wrapper_test_and_license(self) -> None:
        for path in (
            "bin/apg-project-skills",
            "libexec/apg_public_release.py",
            "src/test/int/python/apg_public_release.int.test.py",
            "LICENSE",
            "NOTICE",
        ):
            with self.subTest(path=path):
                policy = self.policy()
                source = self.make_source(self.root / path.replace("/", "-"))
                (source / path).unlink()
                self.commit_all(source, f"omit {path}")
                result = self.run_command("manifest", "--source", str(source))
                self.assertEqual(result.returncode, 1)
                self.assertIn(path, result.stderr)

    def test_10_v0_1_omitted_wrapper_class_fails_for_wrapper(self) -> None:
        candidate, build = self.build()
        self.assert_success(build)
        (candidate / "bin" / "apg-project-skills").unlink()
        self.git(candidate, "add", "-A")
        self.git(candidate, "commit", "-q", "-m", "Retain docs and helper but omit wrapper")
        result = self.check_candidate(candidate)
        self.assertEqual(result.returncode, 1)
        self.assertIn("bin/apg-project-skills", result.stderr)

    def test_11_check_rejects_broken_and_private_markdown_links(self) -> None:
        for content in ("[missing](missing.md)\n", "[private](private/internal.txt)\n"):
            with self.subTest(content=content):
                source = self.make_source(self.root / ("source-" + hashlib.sha256(content.encode()).hexdigest()[:8]))
                (source / "README.md").write_text(content)
                self.commit_all(source, "Add invalid public Markdown link")
                candidate, result = self.build(
                    self.root / hashlib.sha256(content.encode()).hexdigest()[:8],
                    source,
                )
                self.assert_success(result)
                checked = self.check_candidate(candidate, source)
                self.assertEqual(checked.returncode, 1)
                self.assertIn("Markdown", checked.stderr)

    def test_12_check_rejects_history_branch_and_tag_mismatch(self) -> None:
        scenarios = {
            "new-tag-missing": lambda repo: self.git(repo, "tag", "-d", f"v{VERSION}"),
            "base-tag-missing": lambda repo: self.git(repo, "tag", "-d", "v0.1.0"),
            "base-tag-retargeted": lambda repo: self.git(repo, "update-ref", "refs/tags/v0.1.0", "HEAD"),
            "main-moved": lambda repo: self.git(repo, "update-ref", "refs/heads/main", "HEAD"),
            "extra-tag": lambda repo: self.git(repo, "tag", "unexpected", "HEAD"),
            "extra-head": lambda repo: self.git(repo, "update-ref", "refs/heads/unexpected", "HEAD"),
            "extra-custom": lambda repo: self.git(repo, "update-ref", "refs/private/unexpected", "HEAD"),
        }
        for scenario, mutate in scenarios.items():
            with self.subTest(scenario=scenario):
                candidate, result = self.build(self.root / scenario)
                self.assert_success(result)
                mutate(candidate)
                self.assertEqual(self.check_candidate(candidate).returncode, 1)

    def test_13_build_refuses_existing_release_tag_collision(self) -> None:
        self.git(self.base, "tag", f"v{VERSION}")
        output = self.root / "collision"
        result = self.build(output)[1]
        self.assertEqual(result.returncode, 1)
        self.assertFalse(output.exists())

    def test_14_policy_cannot_remove_or_execute_a_required_wrapper(self) -> None:
        policy = self.policy()
        policy["required_wrappers"].remove("bin/apg-project-skills")
        self.write_policy(self.source, policy)
        (self.source / "bin" / "apg-project-skills").unlink()
        self.commit_all(self.source, "weaken policy")
        result = self.run_command("manifest", "--source", str(self.source))
        self.assertEqual(result.returncode, 1)
        self.assertIn("audited", result.stderr.lower())
        source = self.make_source(self.root / "weaken-critical")
        policy = self.policy()
        policy["critical_files"].remove("docs/provenance.md")
        self.write_policy(source, policy)
        self.commit_all(source, "weaken critical owners")
        result = self.run_command("manifest", "--source", str(source))
        self.assertEqual(result.returncode, 1)
        self.assertIn("critical_files", result.stderr)

    def test_15_build_and_check_make_no_network_or_push_side_effect(self) -> None:
        marker = self.root / "network-called"
        fsmonitor = self.root / "source-fsmonitor"
        fsmonitor.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n")
        fsmonitor.chmod(0o755)
        self.git(self.source, "config", "core.fsmonitor", str(fsmonitor))
        shim = self.root / "git-shim"
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        shim.mkdir()
        script = shim / "git"
        script.write_text(
            "#!/bin/sh\ncase \"$*\" in *push*|*fetch*|*pull*) touch \"$APG_TEST_MARKER\"; exit 99;; esac\n"
            f"exec {real_git} \"$@\"\n"
        )
        script.chmod(0o755)
        environment = self.environment.copy()
        environment["PATH"] = f"{shim}:{environment['PATH']}"
        environment["APG_TEST_MARKER"] = str(marker)
        original = self.environment
        self.environment = environment
        try:
            candidate, build = self.build()
            self.assert_success(build)
            self.assert_success(self.check_candidate(candidate))
        finally:
            self.environment = original
        self.assertFalse(marker.exists())

    def test_16_usage_status_is_two(self) -> None:
        for arguments in ((), ("unknown",), ("build",), ("check", "--source", str(self.source))):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.run_command(*arguments).returncode, 2)

    def test_17_confidentiality_rule_does_not_reject_its_own_helper(self) -> None:
        helper_copy = self.source / "self-check-helper.txt"
        helper_copy.write_bytes((REPOSITORY_ROOT / "libexec" / "apg_public_release.py").read_bytes())
        self.commit_all(self.source, "Include checker source as public content")
        candidate, build = self.build()
        self.assert_success(build)
        self.assert_success(self.check_candidate(candidate))

    def test_18_confidentiality_rule_rejects_generic_local_identity(self) -> None:
        (self.source / "leak.txt").write_text("local path: /" + "Users" + "/example/private\n")
        self.commit_all(self.source, "Add local path leak")
        candidate, build = self.build()
        self.assert_success(build)
        result = self.check_candidate(candidate)
        self.assertEqual(result.returncode, 1)
        self.assertIn("confidentiality", result.stderr)

    def test_19_source_and_candidate_manifests_are_identical(self) -> None:
        candidate, build = self.build()
        self.assert_success(build)
        source_manifest = self.run_command("manifest", "--source", str(self.source), "--format", "json")
        candidate_manifest = self.run_command("manifest", "--source", str(candidate), "--format", "json")
        self.assert_success(source_manifest)
        self.assert_success(candidate_manifest)
        self.assertEqual(source_manifest.stdout, candidate_manifest.stdout)

    def test_20_public_symlinks_must_be_relative_contained_and_resolvable(self) -> None:
        for label, target in (
            ("private", "private/internal.txt"),
            ("escape", "../outside"),
            ("absolute", "/absolute/target"),
            ("missing", "missing-target"),
        ):
            with self.subTest(label=label):
                source = self.make_source(self.root / f"unsafe-link-{label}")
                (source / "unsafe-link").symlink_to(target)
                self.commit_all(source, f"Add {label} public link")
                result = self.run_command("manifest", "--source", str(source))
                self.assertEqual(result.returncode, 1)
                self.assertIn("symlink", result.stderr)

        cycle = self.make_source(self.root / "committed-cycle")
        (cycle / "cycle-a").symlink_to("cycle-b")
        (cycle / "cycle-b").symlink_to("cycle-a")
        self.commit_all(cycle, "Add committed symlink cycle")
        for name in ("cycle-a", "cycle-b"):
            (cycle / name).unlink()
            (cycle / name).symlink_to("README.md")
        self.git(cycle, "update-index", "--skip-worktree", "cycle-a", "cycle-b")
        result = self.run_command("manifest", "--source", str(cycle))
        self.assertEqual(result.returncode, 1)

    def test_21_checker_and_configured_test_failures_are_observable(self) -> None:
        scenarios = {
            "checker": (
                "bin/apg-check-skill-library",
                '#!/bin/sh\n[ "$1" = "--help" ] && exit 0\nexit 1\n',
            ),
            "configured-test": (
                "src/test/unit/python/apg_public_release.unit.test.py",
                "raise SystemExit(1)\n",
            ),
        }
        for label, (path, content) in scenarios.items():
            with self.subTest(label=label):
                source = self.make_source(self.root / f"failing-{label}")
                (source / path).write_text(content)
                if path.startswith("bin/"):
                    (source / path).chmod(0o755)
                self.commit_all(source, f"Add failing {label}")
                candidate, build = self.build(self.root / f"candidate-{label}", source)
                self.assert_success(build)
                result = self.check_candidate(candidate, source)
                self.assertEqual(result.returncode, 1)
                self.assertIn(path, result.stderr)

    def test_22_index_flags_cannot_mask_a_failing_configured_test(self) -> None:
        path = "src/test/unit/python/apg_public_release.unit.test.py"
        source = self.make_source(self.root / "masked-test-source")
        (source / path).write_text("raise SystemExit(1)\n")
        self.commit_all(source, "Commit failing configured test")
        candidate, build = self.build(self.root / "masked-test-candidate", source)
        self.assert_success(build)
        (candidate / path).write_text("print('masked pass')\n")
        self.git(candidate, "update-index", "--skip-worktree", path)
        result = self.check_candidate(candidate, source)
        self.assertEqual(result.returncode, 1)
        self.assertIn("index flags", result.stderr)

    def test_23_build_rejects_an_unrelated_release_shaped_base(self) -> None:
        unrelated = self.root / "unrelated-base"
        self.initialize(unrelated)
        (unrelated / "README.md").write_text("# Unrelated release-shaped base\n")
        self.commit_all(unrelated, "Release v0.1.0")
        self.git(unrelated, "tag", "v0.1.0")
        output = self.root / "unrelated-base-candidate"
        result = self.run_command(
            "build",
            "--source",
            str(self.source),
            "--base",
            str(unrelated),
            "--output",
            str(output),
            "--version",
            VERSION,
            "--release-date",
            RELEASE_DATE,
            "--author-name",
            "APG Release Test",
            "--author-email",
            "release@example.invalid",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("accepted public v0.1.0", result.stderr)
        self.assertFalse(output.exists())

    def test_24_build_rejects_an_untagged_intermediate_release_commit(self) -> None:
        first = self.git(self.base, "rev-parse", "HEAD").stdout.strip()
        tree = self.git(self.base, "rev-parse", "HEAD^{tree}").stdout.strip()
        intermediate = self.git(
            self.base,
            "commit-tree",
            tree,
            "-p",
            first,
            "-m",
            "Untagged intermediate",
        ).stdout.strip()
        release_commit = self.git(
            self.base,
            "commit-tree",
            tree,
            "-p",
            intermediate,
            "-m",
            "Release v0.2.0",
        ).stdout.strip()
        self.git(self.base, "update-ref", "refs/heads/main", release_commit)
        self.git(self.base, "reset", "-q", "--hard", release_commit)
        self.git(self.base, "tag", "-a", "v0.2.0", "-m", "Release v0.2.0")
        output = self.root / "intermediate-history-candidate"
        result = self.build(output)[1]
        self.assertEqual(result.returncode, 1)
        self.assertIn("release tag", result.stderr)
        self.assertFalse(output.exists())

    def test_25_configured_test_cannot_mutate_the_original_base(self) -> None:
        path = self.policy()["required_test_entrypoints"][0]
        target = self.source / path
        target.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "Path(os.environ['APG12_PUBLIC_V01_ROOT'], 'APG12A_BASE_MUTATION').write_text('mutated\\n')\n"
        )
        self.commit_all(self.source, "Add base mutation regression")
        before = self.fingerprint(self.base)
        candidate, build = self.build()
        self.assert_success(build)
        result = self.check_candidate(candidate)
        self.assertEqual(result.returncode, 1)
        self.assertIn("base", result.stderr.lower())
        self.assertEqual(self.fingerprint(self.base), before)

    def test_26_configured_test_cannot_mutate_the_original_candidate(self) -> None:
        path = self.policy()["required_test_entrypoints"][0]
        target = self.source / path
        target.write_text(
            "from pathlib import Path\n"
            "Path('APG12A_CANDIDATE_MUTATION').write_text('mutated\\n')\n"
        )
        self.commit_all(self.source, "Add candidate mutation regression")
        candidate, build = self.build()
        self.assert_success(build)
        before = self.fingerprint(candidate)
        result = self.check_candidate(candidate)
        self.assertEqual(result.returncode, 1)
        self.assertIn("candidate", result.stderr.lower())
        self.assertEqual(self.fingerprint(candidate), before)

    def test_27_complete_public_base_lineage_matrix(self) -> None:
        later, later_build = self.build(
            self.root / "valid-later-base",
            version="0.2.0",
        )
        self.assert_success(later_build)
        candidate, result = self.build(
            self.root / "valid-later-candidate",
            base=later,
            version="0.3.0",
        )
        self.assert_success(result)
        self.assert_success(
            self.check_candidate(candidate, base=later, version="0.3.0")
        )

        scenarios: dict[str, Callable[[Path], None]]

        def missing(repo: Path) -> None:
            self.git(repo, "tag", "-d", "v0.1.0")

        def retargeted(repo: Path) -> None:
            self.append_release(repo, "0.2.0")
            self.git(repo, "update-ref", "refs/tags/v0.1.0", "HEAD")

        def current_tag_mismatch(repo: Path) -> None:
            self.append_release(repo, "0.2.0")
            self.git(repo, "tag", "-d", "v0.2.0")
            self.git(repo, "tag", "-a", "v0.2.0", "HEAD^", "-m", "Release v0.2.0")

        def merge(repo: Path) -> None:
            parent = self.git(repo, "rev-parse", "HEAD").stdout.strip()
            tree = self.git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
            side = self.git(
                repo,
                "commit-tree",
                tree,
                "-p",
                parent,
                "-m",
                "Side history",
            ).stdout.strip()
            self.append_release(repo, "0.2.0", parents=(parent, side))

        def subject_mismatch(repo: Path) -> None:
            self.append_release(repo, "0.2.0", subject="Wrong release subject")

        def truncated(repo: Path) -> None:
            tree = self.git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
            commit = self.git(
                repo,
                "commit-tree",
                tree,
                "-m",
                "Release v0.2.0",
            ).stdout.strip()
            self.git(repo, "update-ref", "refs/heads/main", commit)
            self.git(repo, "reset", "-q", "--hard", commit)
            self.git(repo, "tag", "-a", "v0.2.0", "-m", "Release v0.2.0")

        scenarios = {
            "missing-v0.1-tag": missing,
            "retargeted-v0.1-tag": retargeted,
            "current-tag-mismatch": current_tag_mismatch,
            "merge-release": merge,
            "subject-tag-mismatch": subject_mismatch,
            "truncated-chain": truncated,
        }
        for name, mutate in scenarios.items():
            with self.subTest(name=name):
                base = self.copy_base(f"lineage-{name}")
                mutate(base)
                output = self.root / f"candidate-{name}"
                result = self.build(output, base=base)[1]
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse(output.exists())

    def test_28_build_and_check_share_the_base_lineage_disposition(self) -> None:
        candidate, built = self.build()
        self.assert_success(built)
        self.git(self.base, "tag", "-d", "v0.1.0")
        build_output = self.root / "missing-tag-build"
        build_result = self.build(build_output)[1]
        check_result = self.check_candidate(candidate)
        self.assertEqual(build_result.returncode, 1)
        self.assertEqual(check_result.returncode, 1)
        self.assertIn("v0.1.0 tag", build_result.stderr)
        self.assertIn("v0.1.0 tag", check_result.stderr)
        self.assertFalse(build_output.exists())

    def test_29_configured_validation_uses_isolated_environment_roots(self) -> None:
        ambient = self.root / "ambient-validation-state"
        ambient.mkdir()
        path = self.policy()["required_test_entrypoints"][0]
        target = self.source / path
        target.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "names = ('HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', "
            "'XDG_RUNTIME_DIR', 'XDG_STATE_HOME', 'TMPDIR', 'PYTHONPYCACHEPREFIX')\n"
            "for name in names:\n"
            "    root = Path(os.environ[name])\n"
            "    assert root.is_absolute()\n"
            "    assert not root.is_relative_to(Path(os.environ['APG_TEST_AMBIENT_ROOT']))\n"
            "    (root / f'{name}.marker').write_text('isolated\\n')\n"
        )
        self.commit_all(self.source, "Add environment-isolation regression")
        candidate, built = self.build()
        self.assert_success(built)
        before = tuple(self.fingerprint(repo) for repo in (self.source, self.base, candidate))
        environment = self.environment.copy()
        environment.update(
            {
                "APG_TEST_AMBIENT_ROOT": str(ambient),
                "HOME": str(ambient / "home"),
                "XDG_CONFIG_HOME": str(ambient / "config"),
                "XDG_CACHE_HOME": str(ambient / "cache"),
                "XDG_DATA_HOME": str(ambient / "data"),
                "XDG_RUNTIME_DIR": str(ambient / "runtime"),
                "XDG_STATE_HOME": str(ambient / "state"),
                "TMPDIR": str(ambient / "tmp"),
                "PYTHONPYCACHEPREFIX": str(ambient / "pycache"),
            }
        )
        original = self.environment
        self.environment = environment
        try:
            result = self.check_candidate(candidate)
        finally:
            self.environment = original
        self.assert_success(result)
        self.assertEqual(
            tuple(self.fingerprint(repo) for repo in (self.source, self.base, candidate)),
            before,
        )
        self.assertEqual(list(ambient.rglob("*.marker")), [])

    def test_32_later_public_base_must_be_policy_complete(self) -> None:
        later, later_build = self.build(
            self.root / "policy-complete-v0.2-base",
            version="0.2.0",
        )
        self.assert_success(later_build)
        (later / "release" / "public-surface.json").write_text("{}\n")
        self.commit_all(later, "Release v0.3.0")
        self.git(later, "tag", "-a", "v0.3.0", "-m", "Release v0.3.0")

        output = self.root / "policy-incomplete-base-candidate"
        result = self.build(output, base=later, version="0.4.0")[1]
        self.assertEqual(result.returncode, 1)
        self.assertIn("policy", result.stderr.lower())
        self.assertFalse(output.exists())
        check_candidate = self.root / "policy-incomplete-check-candidate"
        shutil.copytree(self.source, check_candidate, symlinks=True)
        checked = self.check_candidate(
            check_candidate,
            base=later,
            version="0.4.0",
        )
        self.assertEqual(checked.returncode, 1)
        self.assertIn("policy", checked.stderr.lower())

    def test_30_v0_1_rejects_same_target_annotated_retag(self) -> None:
        base = self.copy_base("annotated-v0.1-retag")
        self.git(base, "tag", "-d", "v0.1.0")
        self.git(base, "tag", "-a", "v0.1.0", "HEAD", "-m", "Release v0.1.0")
        output = self.root / "annotated-retag-candidate"
        result = self.build(output, base=base)[1]
        self.assertEqual(result.returncode, 1)
        self.assertIn("tag identity", result.stderr)
        self.assertFalse(output.exists())

    def test_31_configured_validation_hides_ambient_working_directories(self) -> None:
        path = self.policy()["required_test_entrypoints"][0]
        target = self.source / path
        target.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "assert Path(os.environ['PWD']).resolve() == Path.cwd().resolve()\n"
            "assert 'OLDPWD' not in os.environ\n"
        )
        self.commit_all(self.source, "Add working-directory isolation regression")
        candidate, built = self.build()
        self.assert_success(built)
        environment = self.environment.copy()
        environment["PWD"] = str(self.source)
        environment["OLDPWD"] = str(self.base)
        original = self.environment
        self.environment = environment
        try:
            result = self.check_candidate(candidate)
        finally:
            self.environment = original
        self.assert_success(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
