#!/usr/bin/env python3
"""Behavioral contract tests for bin/apg-user-skills."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))
import apg_public_release as public_release

COMMAND = REPOSITORY_ROOT / "bin" / "apg-user-skills"
SKILLS = (
    "composing-bounded-worker-assignments",
    "debugging-systematically",
    "designing-significant-changes",
    "implementing-with-test-discipline",
    "planning-repository-work",
    "reviewing-and-verifying-repository-work",
)
RESTART = "restart"
REQUIRED_H2S = (
    "Core principle",
    "Do not use",
    "Procedure",
    "Project-owned parameters",
    "Evidence and completion",
    "Stop or escalate",
    "Common mistakes",
)


class APGUserSkillsTests(unittest.TestCase):
    """Exercise user lifecycle only in temporary HOME and XDG roots."""

    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="apg-user-skills-")
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.state_home = self.root / "state"
        self.skills_root = self.root / "user skills"
        self.home.mkdir()
        self.state_home.mkdir()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "HOME": str(self.home),
                "XDG_STATE_HOME": str(self.state_home),
                "LC_ALL": "C",
                "LANG": "C",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        self.first = self.make_release(self.root / "public-v0.1.0", "0.1.0", "first")
        self.second = self.make_release(self.root / "public-v0.2.0", "0.2.0-apg12.1", "second")
        self.graft_second_release()
        self.launcher = self.root / "apg-user-skills-test-launcher.py"
        self.launcher.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'libexec')!r})\n"
            "import apg_user_skills as command\n"
            f"command.PUBLIC_V01_COMMIT = {self.git(self.first, 'rev-parse', 'HEAD').stdout.strip()!r}\n"
            f"command.PUBLIC_V01_TREE = {self.git(self.first, 'rev-parse', 'HEAD^{tree}').stdout.strip()!r}\n"
            "raise SystemExit(command.main())\n"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, repo: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo), *arguments],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment,
        )

    def make_release(self, path: Path, version: str, marker: str) -> Path:
        path.mkdir(parents=True)
        self.git(path, "init", "-q", "-b", "main")
        self.git(path, "config", "user.name", "APG Test")
        self.git(path, "config", "user.email", "apg-test@example.invalid")
        (path / "README.md").write_text(f"# Public {version}\n")
        (path / "LICENSE").write_text("license\n")
        policy = json.loads((REPOSITORY_ROOT / "release" / "public-surface.json").read_text())
        for key, values in public_release.audited_policy_surfaces("0.2.0")[-1].items():
            policy[key] = list(values)
        policy_path = path / "release" / "public-surface.json"
        policy_path.parent.mkdir(parents=True)
        policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n")
        for name in SKILLS:
            leaf = path / "skills" / name
            leaf.mkdir(parents=True)
            sections = "\n\n".join(
                f"## {heading}\n\nFixture for {heading.lower()}." for heading in REQUIRED_H2S
            )
            (leaf / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: Use when {marker} {name} applies.\n---\n\n"
                f"# {name}\n\n{sections}\n"
            )
        rows = "\n".join(
            f"| [`{name}`]({name}/SKILL.md) | Use when {marker} {name} applies | `provisional` |"
            for name in SKILLS
        )
        (path / "skills" / "README.md").write_text(
            "# APG Skill Library\n\n## APG v0.1 catalog\n\n"
            "| Skill | Trigger boundary | Maturity |\n"
            "| --- | --- | --- |\n"
            f"{rows}\n"
        )
        projection = path / ".agents" / "skills"
        projection.mkdir(parents=True)
        for name in SKILLS:
            (projection / name).symlink_to(f"../../skills/{name}", target_is_directory=True)
        for public_path in policy["critical_files"]:
            target = path / public_path
            if not os.path.lexists(target):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# Fixture public owner\n")
        for public_path in policy["required_helpers"]:
            target = path / public_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# Fixture helper\n")
        for public_path in policy["required_licensing_files"]:
            target = path / public_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("Fixture licensing owner\n")
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
                target.write_text("print('fixture')\n")
        self.git(path, "add", "-A")
        self.git(path, "commit", "-q", "-m", f"Release v{version}")
        if version == "0.1.0":
            self.git(path, "tag", f"v{version}")
        else:
            self.git(path, "tag", "-a", f"v{version}", "-m", f"Release v{version}")
        return path

    def graft_second_release(self) -> None:
        parent = self.git(self.first, "rev-parse", "HEAD").stdout.strip()
        tree = self.git(self.second, "rev-parse", "HEAD^{tree}").stdout.strip()
        self.git(
            self.second,
            "fetch",
            "-q",
            str(self.first),
            "refs/tags/v0.1.0:refs/tags/v0.1.0",
        )
        commit = self.git(
            self.second,
            "commit-tree",
            tree,
            "-p",
            parent,
            "-m",
            "Release v0.2.0-apg12.1",
        ).stdout.strip()
        self.git(self.second, "update-ref", "refs/heads/main", commit)
        self.git(self.second, "reset", "-q", "--hard", commit)
        self.git(
            self.second,
            "tag",
            "-f",
            "-a",
            "v0.2.0-apg12.1",
            "-m",
            "Release v0.2.0-apg12.1",
        )

    def run_command(
        self, *arguments: str, environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.launcher), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.root,
            env=environment or self.environment,
        )

    def invoke(self, operation: str, *arguments: str, source: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [operation]
        if operation in {"list", "install", "adopt", "update"}:
            command.extend(["--source", str(source or self.first)])
        command.extend(["--skills-root", str(self.skills_root), *arguments])
        return self.run_command(*command)

    def assert_success(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")

    @property
    def state_path(self) -> Path:
        return self.state_home / "agentic-praxis-grimoire" / "user-skills-v1.json"

    @property
    def lock_path(self) -> Path:
        return self.state_home / "agentic-praxis-grimoire" / "user-skills-v1.lock"

    def state(self) -> dict[str, object]:
        return json.loads(self.state_path.read_text())

    def source_fingerprint(self, source: Path) -> tuple[str, str, str, str, str]:
        return (
            self.git(source, "rev-parse", "HEAD").stdout,
            self.git(source, "status", "--porcelain=v1", "--untracked-files=all").stdout,
            self.git(source, "for-each-ref", "--format=%(refname)%00%(objectname)", "refs").stdout,
            self.git(source, "ls-files", "--stage").stdout,
            self.git(source, "ls-files", "-v").stdout,
        )

    def copy_release(self, source: Path, name: str) -> Path:
        target = self.root / name
        shutil.copytree(source, target, symlinks=True)
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

    def install(self) -> subprocess.CompletedProcess[str]:
        return self.invoke("install")

    def test_01_list_is_deterministic_and_reports_six_canonical_skills(self) -> None:
        first = self.invoke("list", "--format", "json")
        second = self.invoke("list", "--format", "json")
        self.assert_success(first)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(tuple(json.loads(first.stdout)["skills"]), SKILLS)

    def test_02_source_must_be_clean_public_and_structurally_valid(self) -> None:
        (self.first / "dirty").write_text("dirty\n")
        self.assertEqual(self.invoke("list").returncode, 1)
        (self.first / "dirty").unlink()
        (self.first / "skills" / SKILLS[0] / "SKILL.md").write_text("bad\n")
        self.git(self.first, "add", "-A")
        self.git(self.first, "commit", "-q", "-m", "invalid")
        self.git(self.first, "tag", "-f", "v0.1.0")
        self.assertEqual(self.invoke("list").returncode, 1)
        private_source = self.make_release(self.root / "private-source", "0.3.0", "private")
        (private_source / "private").mkdir()
        (private_source / "private" / "evidence").write_text("private\n")
        self.git(private_source, "add", "-A")
        self.git(private_source, "commit", "-q", "-m", "private path")
        self.assertEqual(self.invoke("list", source=private_source).returncode, 1)

    def test_03_install_creates_exact_direct_links_state_and_restart_reminder(self) -> None:
        result = self.install()
        self.assert_success(result)
        self.assertIn(RESTART, result.stdout.lower())
        for name in SKILLS:
            link = self.skills_root / name
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), (self.first / "skills" / name).resolve())
        state = self.state()
        self.assertEqual(state["schema_version"], 1)
        self.assertEqual(state["managed_skills"], list(SKILLS))
        self.assertEqual(self.state_path.stat().st_mode & 0o777, 0o600)

    def test_04_exact_install_is_idempotent(self) -> None:
        self.assert_success(self.install())
        before = self.state_path.read_bytes()
        inodes = {name: (self.skills_root / name).lstat().st_ino for name in SKILLS}
        self.assert_success(self.install())
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertEqual(inodes, {name: (self.skills_root / name).lstat().st_ino for name in SKILLS})

    def test_05_adopt_claims_only_exact_compatible_links(self) -> None:
        self.skills_root.mkdir(parents=True)
        for name in SKILLS:
            (self.skills_root / name).symlink_to(self.first.resolve() / "skills" / name, target_is_directory=True)
        result = self.invoke("adopt")
        self.assert_success(result)
        self.assertTrue(self.state_path.is_file())

    def test_06_adopt_rejects_mismatch_and_install_rejects_conflicts(self) -> None:
        scenarios = ("mismatch", "file", "directory", "unmanaged-link", "exact-unmanaged-link")
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                root = self.root / f"skills-{scenario}"
                root.mkdir()
                path = root / SKILLS[0]
                if scenario == "file":
                    path.write_text("keep\n")
                elif scenario == "directory":
                    path.mkdir()
                else:
                    target = (
                        self.first / "skills" / SKILLS[0]
                        if scenario == "exact-unmanaged-link"
                        else self.second / "skills" / SKILLS[0]
                    )
                    path.symlink_to(target, target_is_directory=True)
                operation = "adopt" if scenario == "mismatch" else "install"
                result = self.run_command(operation, "--source", str(self.first), "--skills-root", str(root))
                self.assertEqual(result.returncode, 1)
                self.assertTrue(os.path.lexists(path))

    def test_07_symlinked_user_root_ancestor_is_refused(self) -> None:
        real = self.root / "real"
        real.mkdir()
        link = self.root / "linked"
        link.symlink_to(real, target_is_directory=True)
        result = self.run_command("install", "--source", str(self.first), "--skills-root", str(link / "skills"))
        self.assertEqual(result.returncode, 1)

    def test_08_malformed_unsupported_and_overpermissive_state_are_refused(self) -> None:
        self.assert_success(self.install())
        for content in (b"{}\n", b'{"schema_version":2}\n'):
            with self.subTest(content=content):
                self.state_path.write_bytes(content)
                self.state_path.chmod(0o600)
                self.assertEqual(self.invoke("check").returncode, 1)
                self.assertEqual(self.state_path.read_bytes(), content)
        self.state_path.chmod(0o644)
        before = self.state_path.read_bytes()
        self.assertEqual(self.invoke("check").returncode, 1)
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertEqual(self.state_path.stat().st_mode & 0o777, 0o644)

    def test_09_check_detects_missing_retargeted_and_changed_source(self) -> None:
        for scenario in ("missing", "retarget", "changed-source"):
            with self.subTest(scenario=scenario):
                root = self.root / f"case-{scenario}"
                original_environment = self.environment
                selected_environment = original_environment.copy()
                selected_environment["XDG_STATE_HOME"] = str(self.root / f"state-{scenario}")
                self.environment = selected_environment
                try:
                    result = self.run_command("install", "--source", str(self.first), "--skills-root", str(root))
                    self.assert_success(result)
                    link = root / SKILLS[0]
                    if scenario == "missing":
                        link.unlink()
                    elif scenario == "retarget":
                        link.unlink()
                        link.symlink_to(self.second / "skills" / SKILLS[0], target_is_directory=True)
                    else:
                        (self.first / "README.md").write_text("changed\n")
                        self.git(self.first, "add", "README.md")
                        self.git(self.first, "commit", "-q", "-m", "changed source")
                    check = self.run_command("check", "--skills-root", str(root))
                    self.assertEqual(check.returncode, 1)
                    if scenario == "changed-source":
                        self.git(self.first, "reset", "--hard", "HEAD^")
                finally:
                    self.environment = original_environment

    def test_10_check_warns_on_repository_duplicate_without_precedence_claim(self) -> None:
        self.assert_success(self.install())
        repo = self.root / "target repo"
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main")
        duplicate = repo / ".agents" / "skills" / SKILLS[0]
        duplicate.mkdir(parents=True)
        (duplicate / "SKILL.md").write_text(f"---\nname: {SKILLS[0]}\ndescription: duplicate\n---\n")
        before_status = self.git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout
        result = self.invoke("check", "--repo", str(repo))
        self.assert_success(result)
        self.assertIn("duplicate", result.stdout.lower())
        self.assertNotIn("precedence", result.stdout.lower())
        self.assertNotIn("invoked from", result.stdout.lower())
        self.assertEqual(self.git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout, before_status)

    def test_11_update_preserves_prior_identity_and_rollback_restores_it(self) -> None:
        self.assert_success(self.install())
        update = self.invoke("update", source=self.second)
        self.assert_success(update)
        self.assertIn(RESTART, update.stdout.lower())
        self.assertEqual((self.skills_root / SKILLS[0]).resolve(), (self.second / "skills" / SKILLS[0]).resolve())
        self.assertEqual(self.state()["previous_source"]["path"], str(self.first.resolve()))
        rollback = self.invoke("rollback")
        self.assert_success(rollback)
        self.assertIn(RESTART, rollback.stdout.lower())
        self.assertEqual((self.skills_root / SKILLS[0]).resolve(), (self.first / "skills" / SKILLS[0]).resolve())

    def test_12_rollback_refuses_missing_or_wrong_prior_source(self) -> None:
        self.assert_success(self.install())
        self.assert_success(self.invoke("update", source=self.second))
        self.git(self.first, "tag", "-d", "v0.1.0")
        before = self.state_path.read_bytes()
        result = self.invoke("rollback")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.state_path.read_bytes(), before)
        self.assertEqual((self.skills_root / SKILLS[0]).resolve(), (self.second / "skills" / SKILLS[0]).resolve())

    def test_13_conflicting_update_is_transactional(self) -> None:
        self.assert_success(self.install())
        link = self.skills_root / SKILLS[-1]
        link.unlink()
        link.write_text("conflict\n")
        before = self.state_path.read_bytes()
        result = self.invoke("update", source=self.second)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.state_path.read_bytes(), before)
        for name in SKILLS[:-1]:
            self.assertEqual((self.skills_root / name).resolve(), (self.first / "skills" / name).resolve())

    def test_14_uninstall_removes_owned_links_only_and_is_repeatable(self) -> None:
        unrelated = self.skills_root / "unrelated-skill"
        unrelated.mkdir(parents=True)
        (unrelated / "SKILL.md").write_text("keep\n")
        self.assert_success(self.install())
        result = self.invoke("uninstall")
        self.assert_success(result)
        self.assertIn(RESTART, result.stdout.lower())
        self.assertTrue(unrelated.is_dir())
        self.assertFalse(self.state_path.exists())
        self.assert_success(self.invoke("uninstall"))

    def test_15_created_empty_containers_are_removed_conservatively(self) -> None:
        root = self.home / ".agents" / "skills"
        result = self.run_command("install", "--source", str(self.first), "--skills-root", str(root))
        self.assert_success(result)
        self.assert_success(self.run_command("uninstall", "--skills-root", str(root)))
        self.assertFalse(root.exists())
        self.assertFalse(root.parent.exists())

    def test_16_lock_conflict_is_refused(self) -> None:
        self.lock_path.parent.mkdir(parents=True)
        descriptor = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.install().returncode, 1)
        finally:
            os.close(descriptor)

    def test_17_interrupted_temporary_link_refuses_without_drift(self) -> None:
        self.assert_success(self.install())
        temporary = self.skills_root / f".{SKILLS[0]}.apg-user-skills-new"
        temporary.symlink_to(self.second / "skills" / SKILLS[0], target_is_directory=True)
        before_state = self.state_path.read_bytes()
        before_targets = {name: os.readlink(self.skills_root / name) for name in SKILLS}
        result = self.invoke("update", source=self.second)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.state_path.read_bytes(), before_state)
        self.assertEqual({name: os.readlink(self.skills_root / name) for name in SKILLS}, before_targets)

    def test_18_raw_link_alias_and_git_worktree_root_are_refused(self) -> None:
        self.assert_success(self.install())
        link = self.skills_root / SKILLS[0]
        link.unlink()
        relative = os.path.relpath(self.first / "skills" / SKILLS[0], self.skills_root)
        link.symlink_to(relative, target_is_directory=True)
        self.assertEqual(self.invoke("check").returncode, 1)
        self.assertEqual(self.invoke("uninstall").returncode, 1)
        result = self.run_command(
            "install",
            "--source",
            str(self.second),
            "--skills-root",
            str(self.second / "managed-skills"),
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.second / "managed-skills").exists())

    def test_19_home_xdg_source_repo_and_codex_config_are_isolated(self) -> None:
        codex = self.home / ".codex" / "config.toml"
        codex.parent.mkdir()
        codex.write_text("preserve = true\n")
        before_config = codex.read_bytes()
        before_source = self.source_fingerprint(self.first)
        self.assert_success(self.install())
        self.assert_success(self.invoke("check"))
        self.assert_success(self.invoke("uninstall"))
        self.assertEqual(codex.read_bytes(), before_config)
        self.assertEqual(self.source_fingerprint(self.first), before_source)

    def test_20_no_network_action_occurs(self) -> None:
        marker = self.root / "network-called"
        fsmonitor = self.root / "source-fsmonitor"
        fsmonitor.write_text(f"#!/bin/sh\ntouch {marker}\nexit 0\n")
        fsmonitor.chmod(0o755)
        self.git(self.first, "config", "core.fsmonitor", str(fsmonitor))
        shim = self.root / "git-shim"
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        shim.mkdir()
        script = shim / "git"
        script.write_text(
            "#!/bin/sh\ncase \"$*\" in *clone*|*fetch*|*pull*|*push*|*ls-remote*) touch \"$APG_TEST_MARKER\"; exit 99;; esac\n"
            f"exec {real_git} \"$@\"\n"
        )
        script.chmod(0o755)
        environment = self.environment.copy()
        environment["PATH"] = f"{shim}:{environment['PATH']}"
        environment["APG_TEST_MARKER"] = str(marker)
        original = self.environment
        self.environment = environment
        try:
            self.assert_success(self.install())
            self.assert_success(self.invoke("check"))
            self.assert_success(self.invoke("uninstall"))
        finally:
            self.environment = original
        self.assertFalse(marker.exists())

    def test_21_usage_and_noncompliance_statuses(self) -> None:
        self.assertEqual(self.run_command().returncode, 2)
        self.assertEqual(self.run_command("unknown").returncode, 2)
        self.skills_root.mkdir()
        (self.skills_root / SKILLS[0]).write_text("conflict\n")
        self.assertEqual(self.install().returncode, 1)

    @unittest.skipUnless(os.environ.get("APG12_PUBLIC_V01_ROOT"), "public v0.1.0 root not supplied")
    def test_22_lists_actual_public_v0_1_0(self) -> None:
        public = Path(os.environ["APG12_PUBLIC_V01_ROOT"])
        result = subprocess.run(
            [str(COMMAND), "list", "--source", str(public), "--skills-root", str(self.skills_root)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.root,
            env=self.environment,
        )
        self.assert_success(result)
        for name in SKILLS:
            self.assertIn(name, result.stdout)

    def test_23_tampered_container_ownership_cannot_remove_unrelated_directory(self) -> None:
        self.assert_success(self.install())
        unrelated = self.root / "unrelated-empty"
        unrelated.mkdir()
        metadata = unrelated.lstat()
        state = self.state()
        state["created_containers"].append(
            {
                "device": metadata.st_dev,
                "inode": metadata.st_ino,
                "mode": metadata.st_mode & 0o777,
                "owner": metadata.st_uid,
                "path": str(unrelated),
            }
        )
        state["created_containers"].sort(
            key=lambda item: (len(Path(item["path"]).parts), item["path"])
        )
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
        self.state_path.chmod(0o600)
        self.assertEqual(self.invoke("uninstall").returncode, 1)
        self.assertTrue(unrelated.is_dir())

    def test_24_state_root_inside_git_worktree_is_refused_without_mutation(self) -> None:
        repository = self.root / "target-repository"
        repository.mkdir()
        self.git(repository, "init", "-q", "-b", "main")
        before = self.git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout
        environment = self.environment.copy()
        environment["XDG_STATE_HOME"] = str(repository / ".state")
        result = self.run_command(
            "install",
            "--source",
            str(self.first),
            "--skills-root",
            str(self.skills_root),
            environment=environment,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            self.git(repository, "status", "--porcelain=v1", "--untracked-files=all").stdout,
            before,
        )
        self.assertFalse((repository / ".state").exists())

    def test_25_canonical_checker_rejects_incomplete_named_skills(self) -> None:
        skill_file = self.second / "skills" / SKILLS[0] / "SKILL.md"
        skill_file.write_text(
            f"---\nname: {SKILLS[0]}\ndescription: Use when incomplete behavior applies.\n---\n\n"
            f"# {SKILLS[0]}\n"
        )
        self.git(self.second, "add", "-A")
        self.git(self.second, "commit", "-q", "-m", "Release v0.2.0-apg12.2")
        self.git(
            self.second,
            "tag",
            "-a",
            "v0.2.0-apg12.2",
            "-m",
            "Release v0.2.0-apg12.2",
        )
        result = self.invoke("list", source=self.second)
        self.assertEqual(result.returncode, 1)
        self.assertIn("skill library", result.stderr)

    def test_26_unrelated_policy_complete_release_history_is_refused(self) -> None:
        unrelated = self.make_release(self.root / "unrelated-release", "9.9.9", "unrelated")
        result = self.invoke("list", source=unrelated)
        self.assertEqual(result.returncode, 1)
        self.assertIn("accepted public v0.1.0", result.stderr)

    def test_27_physical_state_and_skills_overlap_is_refused(self) -> None:
        if Path("/tmp").resolve() == Path("/tmp"):
            self.skipTest("system does not expose a distinct /tmp physical alias")
        alias_root = Path(tempfile.mkdtemp(prefix="apg-user-alias-", dir="/tmp"))
        try:
            shared = alias_root / "shared"
            skills_root = shared / "agentic-praxis-grimoire"
            environment = self.environment.copy()
            environment["XDG_STATE_HOME"] = str(alias_root.resolve(strict=True) / "shared")
            result = self.run_command(
                "install",
                "--source",
                str(self.first),
                "--skills-root",
                str(skills_root),
                environment=environment,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("must be disjoint", result.stderr)
            self.assertFalse(shared.exists())
        finally:
            shutil.rmtree(alias_root)

    def test_28_public_v0_1_requires_its_exact_release_tag(self) -> None:
        self.git(self.first, "tag", "-d", "v0.1.0")
        self.git(self.first, "tag", "-a", "v9.9.9", "-m", "Release v9.9.9")
        result = self.invoke("list")
        self.assertEqual(result.returncode, 1)
        self.assertIn("tag identity is invalid", result.stderr)

    def test_29_release_source_rejects_invalid_semver_prerelease_tag(self) -> None:
        self.git(self.second, "tag", "-d", "v0.2.0-apg12.1")
        self.git(self.second, "tag", "-a", "v0.2.0-01", "-m", "Invalid SemVer tag")
        result = self.invoke("list", source=self.second)
        self.assertEqual(result.returncode, 1)
        self.assertIn("exactly one matching", result.stderr)

    def test_30_release_source_rejects_an_untagged_intermediate_commit(self) -> None:
        parent = self.git(self.second, "rev-parse", "HEAD").stdout.strip()
        tree = self.git(self.second, "rev-parse", "HEAD^{tree}").stdout.strip()
        intermediate = self.git(
            self.second,
            "commit-tree",
            tree,
            "-p",
            parent,
            "-m",
            "Untagged intermediate",
        ).stdout.strip()
        release_commit = self.git(
            self.second,
            "commit-tree",
            tree,
            "-p",
            intermediate,
            "-m",
            "Release v0.3.0",
        ).stdout.strip()
        self.git(self.second, "update-ref", "refs/heads/main", release_commit)
        self.git(self.second, "reset", "-q", "--hard", release_commit)
        self.git(self.second, "tag", "-a", "v0.3.0", "-m", "Release v0.3.0")
        result = self.invoke("list", source=self.second)
        self.assertEqual(result.returncode, 1)
        self.assertIn("release tag", result.stderr)

    def test_31_absent_check_does_not_create_state_or_lock(self) -> None:
        directory = self.state_path.parent
        self.assertFalse(directory.exists())
        result = self.invoke("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("state is absent", result.stderr)
        self.assertFalse(directory.exists())

    def test_32_check_preserves_existing_state_and_lock_metadata(self) -> None:
        self.assert_success(self.install())
        before_state = (
            self.state_path.read_bytes(),
            self.state_path.stat().st_ino,
            self.state_path.stat().st_mode,
            self.state_path.stat().st_mtime_ns,
        )
        before_lock = (
            self.lock_path.read_bytes(),
            self.lock_path.stat().st_ino,
            self.lock_path.stat().st_mode,
            self.lock_path.stat().st_mtime_ns,
        )
        self.assert_success(self.invoke("check"))
        self.assertEqual(
            (
                self.state_path.read_bytes(),
                self.state_path.stat().st_ino,
                self.state_path.stat().st_mode,
                self.state_path.stat().st_mtime_ns,
            ),
            before_state,
        )
        self.assertEqual(
            (
                self.lock_path.read_bytes(),
                self.lock_path.stat().st_ino,
                self.lock_path.stat().st_mode,
                self.lock_path.stat().st_mtime_ns,
            ),
            before_lock,
        )

    def test_33_check_uses_a_shared_nonmutating_lock(self) -> None:
        self.assert_success(self.install())
        descriptor = os.open(self.lock_path, os.O_RDONLY)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
            self.assert_success(self.invoke("check"))
        finally:
            os.close(descriptor)

    def test_34_complete_user_source_lineage_matrix(self) -> None:
        self.assert_success(self.invoke("list", source=self.first))
        self.assert_success(self.invoke("list", source=self.second))

        def retargeted(repo: Path) -> None:
            self.git(repo, "update-ref", "refs/tags/v0.1.0", "HEAD")

        def current_tag_mismatch(repo: Path) -> None:
            self.git(repo, "tag", "-d", "v0.2.0-apg12.1")
            self.git(
                repo,
                "tag",
                "-a",
                "v0.2.0-apg12.1",
                "HEAD^",
                "-m",
                "Release v0.2.0-apg12.1",
            )

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
            self.append_release(repo, "0.3.0", parents=(parent, side))

        def subject_mismatch(repo: Path) -> None:
            self.append_release(repo, "0.3.0", subject="Wrong release subject")

        def truncated(repo: Path) -> None:
            tree = self.git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
            commit = self.git(
                repo,
                "commit-tree",
                tree,
                "-m",
                "Release v0.3.0",
            ).stdout.strip()
            self.git(repo, "update-ref", "refs/heads/main", commit)
            self.git(repo, "reset", "-q", "--hard", commit)
            self.git(repo, "tag", "-a", "v0.3.0", "-m", "Release v0.3.0")

        scenarios = {
            "retargeted-v0.1-tag": retargeted,
            "current-tag-mismatch": current_tag_mismatch,
            "merge-release": merge,
            "subject-tag-mismatch": subject_mismatch,
            "truncated-chain": truncated,
        }
        for name, mutate in scenarios.items():
            with self.subTest(name=name):
                source = self.copy_release(self.second, f"user-lineage-{name}")
                mutate(source)
                before = self.source_fingerprint(source)
                result = self.invoke("list", source=source)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(self.source_fingerprint(source), before)

    def test_35_invalid_lineage_cannot_drive_user_mutation(self) -> None:
        invalid = self.copy_release(self.second, "invalid-mutation-source")
        parent = self.git(invalid, "rev-parse", "HEAD").stdout.strip()
        tree = self.git(invalid, "rev-parse", "HEAD^{tree}").stdout.strip()
        intermediate = self.git(
            invalid,
            "commit-tree",
            tree,
            "-p",
            parent,
            "-m",
            "Untagged intermediate",
        ).stdout.strip()
        release_commit = self.git(
            invalid,
            "commit-tree",
            tree,
            "-p",
            intermediate,
            "-m",
            "Release v0.3.0",
        ).stdout.strip()
        self.git(invalid, "update-ref", "refs/heads/main", release_commit)
        self.git(invalid, "reset", "-q", "--hard", release_commit)
        self.git(invalid, "tag", "-a", "v0.3.0", "-m", "Release v0.3.0")
        source_before = self.source_fingerprint(invalid)
        for operation in ("list", "install", "adopt"):
            with self.subTest(operation=operation):
                result = self.invoke(operation, source=invalid)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(self.state_path.parent.exists())
                self.assertFalse(self.skills_root.exists())
        self.assertEqual(self.source_fingerprint(invalid), source_before)

        self.assert_success(self.install())
        before_state = self.state_path.read_bytes()
        before_links = {name: os.readlink(self.skills_root / name) for name in SKILLS}
        self.assertEqual(self.invoke("update", source=invalid).returncode, 1)
        self.assertEqual(self.state_path.read_bytes(), before_state)
        self.assertEqual(
            {name: os.readlink(self.skills_root / name) for name in SKILLS},
            before_links,
        )

    def test_36_valid_check_is_fully_read_only_and_deterministic(self) -> None:
        unrelated = self.skills_root / "unrelated-skill" / "SKILL.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("unrelated\n")
        self.assert_success(self.install())
        repo = self.root / "check-repo"
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main")

        def path_fingerprint(path: Path) -> tuple[tuple[str, int, int, int, str], ...]:
            rows: list[tuple[str, int, int, int, str]] = []
            for member in sorted(path.rglob("*")):
                metadata = member.lstat()
                content = os.readlink(member) if member.is_symlink() else (
                    hashlib.sha256(member.read_bytes()).hexdigest() if member.is_file() else ""
                )
                rows.append(
                    (
                        str(member.relative_to(path)),
                        metadata.st_ino,
                        metadata.st_mode,
                        metadata.st_mtime_ns,
                        content,
                    )
                )
            return tuple(rows)

        before_source = self.source_fingerprint(self.first)
        before_user = path_fingerprint(self.root)
        text_one = self.invoke("check", "--repo", str(repo), "--format", "text")
        text_two = self.invoke("check", "--repo", str(repo), "--format", "text")
        json_one = self.invoke("check", "--repo", str(repo), "--format", "json")
        json_two = self.invoke("check", "--repo", str(repo), "--format", "json")
        for result in (text_one, text_two, json_one, json_two):
            self.assert_success(result)
        self.assertEqual(text_one.stdout, text_two.stdout)
        self.assertEqual(json_one.stdout, json_two.stdout)
        self.assertEqual(path_fingerprint(self.root), before_user)
        self.assertEqual(self.source_fingerprint(self.first), before_source)
        self.assertEqual(unrelated.read_text(), "unrelated\n")

    def test_37_active_mutation_lock_refuses_check_without_lock_change(self) -> None:
        self.assert_success(self.install())
        descriptor = os.open(self.lock_path, os.O_RDWR)
        before = (
            self.lock_path.read_bytes(),
            self.lock_path.stat().st_ino,
            self.lock_path.stat().st_mode,
            self.lock_path.stat().st_mtime_ns,
        )
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.invoke("check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("mutation lock", result.stderr)
        finally:
            os.close(descriptor)
        self.assertEqual(
            (
                self.lock_path.read_bytes(),
                self.lock_path.stat().st_ino,
                self.lock_path.stat().st_mode,
                self.lock_path.stat().st_mtime_ns,
            ),
            before,
        )

    def test_38_overpermissive_state_directory_is_rejected_unchanged(self) -> None:
        self.assert_success(self.install())
        directory = self.state_path.parent
        directory.chmod(0o755)
        before = (
            directory.stat().st_ino,
            directory.stat().st_mode,
            directory.stat().st_mtime_ns,
            self.state_path.read_bytes(),
            self.lock_path.read_bytes(),
        )
        result = self.invoke("check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("state directory", result.stderr)
        self.assertEqual(
            (
                directory.stat().st_ino,
                directory.stat().st_mode,
                directory.stat().st_mtime_ns,
                self.state_path.read_bytes(),
                self.lock_path.read_bytes(),
            ),
            before,
        )

    def test_39_public_v0_1_rejects_same_target_annotated_retag(self) -> None:
        self.git(self.first, "tag", "-d", "v0.1.0")
        self.git(self.first, "tag", "-a", "v0.1.0", "HEAD", "-m", "Release v0.1.0")
        before = self.source_fingerprint(self.first)
        result = self.invoke("list")
        self.assertEqual(result.returncode, 1)
        self.assertIn("tag identity", result.stderr)
        self.assertEqual(self.source_fingerprint(self.first), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
