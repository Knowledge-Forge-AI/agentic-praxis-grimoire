#!/usr/bin/env python3
"""Behavioral contract tests for bin/apg-project-skills."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
COMMAND = REPOSITORY_ROOT / "bin" / "apg-project-skills"
CANONICAL_ROOT = REPOSITORY_ROOT / "skills"
V0_2_SKILLS = (
    "composing-bounded-worker-assignments",
    "debugging-systematically",
    "designing-significant-changes",
    "implementing-with-test-discipline",
    "planning-repository-work",
    "reviewing-and-verifying-repository-work",
)
SKILLS = tuple(
    sorted(
        (
            *V0_2_SKILLS,
            "agentic-praxis-grimoire-workflow",
            "bash-language-profile",
            "bats-test-profile",
            "composing-approved-roadmap-assignments",
            "go-language-profile",
            "nix-language-profile",
            "postgresql-database-profile",
            "python-language-profile",
            "ruby-language-profile",
            "sqlite-database-profile",
            "synthesizing-repository-guidance",
            "zsh-language-profile",
            "zunit-test-profile",
        )
    )
)
BEGIN_MARKER = "# BEGIN APG PROJECT SKILLS V1"
END_MARKER = "# END APG PROJECT SKILLS V1"
RESTART_REMINDER = "full Codex application restart may be needed"


class APGProjectSkillsTests(unittest.TestCase):
    """Exercise the command only against disposable Git worktrees."""

    maxDiff = None

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="apg-project-skills-test-"
        )
        self.base = Path(self.temporary.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "HOME": str(self.home),
                "LC_ALL": "C",
                "LANG": "C",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        self.repo = self.create_repository(self.base / "target")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(
        self,
        *arguments: str,
        repo: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(repo or self.repo), *arguments],
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment,
        )

    def create_repository(self, path: Path) -> Path:
        path.mkdir(parents=True)
        subprocess.run(
            ["git", "init", "-q", str(path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment,
        )
        for key, value in (
            ("user.name", "APG Test"),
            ("user.email", "apg-test@example.invalid"),
        ):
            subprocess.run(
                ["git", "-C", str(path), "config", key, value],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.environment,
            )
        (path / "README.md").write_text("temporary test repository\n")
        subprocess.run(
            ["git", "-C", str(path), "add", "README.md"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment,
        )
        subprocess.run(
            ["git", "-C", str(path), "commit", "-q", "-m", "Initial"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=self.environment,
        )
        return path

    def run_command(
        self,
        *arguments: str,
        repo: Path | None = None,
        cwd: Path | None = None,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        selected_repo = repo or self.repo
        command = [str(COMMAND), *arguments]
        if arguments and arguments[0] in {
            "install",
            "adopt",
            "check",
            "uninstall",
        } and "--repo" not in arguments:
            command.extend(["--repo", str(selected_repo)])
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(cwd or self.base),
            env=environment or self.environment,
        )

    def assert_success(
        self, result: subprocess.CompletedProcess[str]
    ) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def assert_safety_failure(
        self, result: subprocess.CompletedProcess[str], text: str
    ) -> None:
        self.assertEqual(result.returncode, 1, result)
        self.assertIn(text, result.stderr.lower())

    def git_path(self, relative: str, repo: Path | None = None) -> Path:
        selected_repo = repo or self.repo
        value = self.git(
            "rev-parse", "--git-path", relative, repo=selected_repo
        ).stdout.strip()
        path = Path(value)
        if not path.is_absolute():
            path = selected_repo / path
        return path.resolve()

    def state_path(self, repo: Path | None = None) -> Path:
        return self.git_path("info/apg-project-skills-v1", repo)

    def exclude_path(self, repo: Path | None = None) -> Path:
        return self.git_path("info/exclude", repo)

    def projection(self, skill: str, repo: Path | None = None) -> Path:
        return (repo or self.repo) / ".agents" / "skills" / skill

    def create_manual_link(
        self, skill: str, repo: Path | None = None, target: Path | None = None
    ) -> Path:
        link = self.projection(skill, repo)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target or (CANONICAL_ROOT / skill), target_is_directory=True)
        return link

    def read_state(self, repo: Path | None = None) -> dict[str, object]:
        return json.loads(self.state_path(repo).read_text())

    def tracked_fingerprint(self, repo: Path | None = None) -> tuple[str, str, str]:
        selected_repo = repo or self.repo
        return (
            self.git("rev-parse", "HEAD^{tree}", repo=selected_repo).stdout,
            self.git("diff", "--binary", repo=selected_repo).stdout,
            self.git("diff", "--cached", "--binary", repo=selected_repo).stdout,
        )

    def home_fingerprint(self) -> list[tuple[str, str, str]]:
        records: list[tuple[str, str, str]] = []
        for path in sorted(self.home.rglob("*")):
            relative = str(path.relative_to(self.home))
            if path.is_symlink():
                records.append((relative, "link", os.readlink(path)))
            elif path.is_dir():
                records.append((relative, "dir", ""))
            else:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                records.append((relative, "file", digest))
        return records

    def managed_fingerprint(
        self, skill: str, repo: Path | None = None
    ) -> tuple[bytes, bytes, tuple[str, str, str], int, str]:
        selected_repo = repo or self.repo
        link = self.projection(skill, selected_repo)
        return (
            self.state_path(selected_repo).read_bytes(),
            self.exclude_path(selected_repo).read_bytes(),
            self.tracked_fingerprint(selected_repo),
            link.lstat().st_ino,
            os.readlink(link),
        )

    def reinclude_managed_projection(
        self, skill: str, repo: Path | None = None
    ) -> bytes:
        selected_repo = repo or self.repo
        exclude = self.exclude_path(selected_repo)
        original = exclude.read_bytes()
        exclude.write_bytes(
            original + f"!/.agents/skills/{skill}\n".encode("ascii")
        )
        status = self.git(
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            f".agents/skills/{skill}",
            repo=selected_repo,
        ).stdout
        self.assertIn(f"?? .agents/skills/{skill}", status)
        return original

    def test_01_lists_the_current_release_set_without_a_repository(self) -> None:
        non_repository = self.base / "not-a-repository"
        non_repository.mkdir()
        result = self.run_command("list", cwd=non_repository)
        self.assert_success(result)
        self.assertEqual(result.stdout.splitlines(), list(SKILLS))

    def test_02_installs_all_nineteen_into_an_empty_worktree(self) -> None:
        result = self.run_command("install")
        self.assert_success(result)
        state = self.read_state()
        self.assertEqual(state["format_version"], 1)
        self.assertEqual(state["managed_skills"], list(SKILLS))
        self.assertEqual(Path(str(state["apg_root"])), REPOSITORY_ROOT)
        self.assertEqual(Path(str(state["target_root"])), self.repo.resolve())
        self.assertEqual(
            stat.S_IMODE(self.state_path().stat().st_mode),
            0o600,
        )
        for skill in SKILLS:
            link = self.projection(skill)
            self.assertTrue(link.is_symlink())
            self.assertTrue(os.path.isabs(os.readlink(link)))
            self.assertEqual(link.resolve(), (CANONICAL_ROOT / skill).resolve())

    def test_03_installs_a_selected_subset(self) -> None:
        selected = SKILLS[:2]
        result = self.run_command(
            "install", "--skill", selected[0], "--skill", selected[1]
        )
        self.assert_success(result)
        self.assertEqual(self.read_state()["managed_skills"], list(selected))
        self.assertEqual(
            sorted(path.name for path in self.projection(selected[0]).parent.iterdir()),
            list(selected),
        )

    def test_04_exact_reinstall_is_idempotent(self) -> None:
        self.assert_success(self.run_command("install"))
        link_inodes = {
            skill: self.projection(skill).lstat().st_ino for skill in SKILLS
        }
        state_bytes = self.state_path().read_bytes()
        exclude_bytes = self.exclude_path().read_bytes()
        result = self.run_command("install")
        self.assert_success(result)
        self.assertIn("already compliant", result.stdout.lower())
        self.assertEqual(
            link_inodes,
            {skill: self.projection(skill).lstat().st_ino for skill in SKILLS},
        )
        self.assertEqual(self.state_path().read_bytes(), state_bytes)
        self.assertEqual(self.exclude_path().read_bytes(), exclude_bytes)
        self.assert_success(self.run_command("check"))

    def test_05_check_reports_managed_compliance(self) -> None:
        self.assert_success(self.run_command("install"))
        result = self.run_command("check")
        self.assert_success(result)
        self.assertIn("compliant", result.stdout.lower())
        self.assertIn("19 managed", result.stdout.lower())

    def test_06_adopts_compatible_manual_links_without_retargeting(self) -> None:
        links = [self.create_manual_link(skill) for skill in SKILLS]
        inodes = [link.lstat().st_ino for link in links]
        targets = [os.readlink(link) for link in links]
        unmanaged = self.run_command("check")
        self.assert_success(unmanaged)
        self.assertIn("0 managed skills", unmanaged.stdout)
        self.assertIn("unmanaged projection paths", unmanaged.stdout)
        explicit = self.run_command("check", "--skill", SKILLS[0])
        self.assert_safety_failure(explicit, "not locally managed")
        result = self.run_command("adopt")
        self.assert_success(result)
        self.assertEqual(self.read_state()["managed_skills"], list(SKILLS))
        self.assertEqual([link.lstat().st_ino for link in links], inodes)
        self.assertEqual([os.readlink(link) for link in links], targets)
        state_bytes = self.state_path().read_bytes()
        exclude_bytes = self.exclude_path().read_bytes()
        repeated = self.run_command("adopt")
        self.assert_success(repeated)
        self.assertIn("already compliant", repeated.stdout.lower())
        self.assertEqual([link.lstat().st_ino for link in links], inodes)
        self.assertEqual([os.readlink(link) for link in links], targets)
        self.assertEqual(self.state_path().read_bytes(), state_bytes)
        self.assertEqual(self.exclude_path().read_bytes(), exclude_bytes)
        self.assert_success(self.run_command("check"))

    def test_07_adopt_refuses_a_mismatched_link(self) -> None:
        self.create_manual_link(SKILLS[0], target=CANONICAL_ROOT / SKILLS[1])
        result = self.run_command("adopt", "--skill", SKILLS[0])
        self.assert_safety_failure(result, "exact canonical")
        self.assertFalse(self.state_path().exists())

    def test_08_install_and_adopt_refuse_tracked_paths(self) -> None:
        path = self.projection(SKILLS[0])
        path.parent.mkdir(parents=True)
        path.write_text("tracked conflict\n")
        self.git("add", str(path.relative_to(self.repo)))
        self.git("commit", "-q", "-m", "Track projection conflict")
        for operation in ("install", "adopt"):
            with self.subTest(operation=operation):
                result = self.run_command(operation, "--skill", SKILLS[0])
                self.assert_safety_failure(result, "tracked")

    def test_09_install_refuses_file_and_directory_conflicts(self) -> None:
        for kind in ("file", "directory"):
            with self.subTest(kind=kind):
                repo = self.create_repository(self.base / f"conflict-{kind}")
                path = self.projection(SKILLS[0], repo)
                path.parent.mkdir(parents=True)
                if kind == "file":
                    path.write_text("conflict\n")
                else:
                    path.mkdir()
                result = self.run_command(
                    "install", "--skill", SKILLS[0], repo=repo
                )
                self.assert_safety_failure(result, "conflicting path")

    def test_10_symlinked_projection_parents_are_refused(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        agents = self.repo / ".agents"
        agents.symlink_to(outside, target_is_directory=True)
        result = self.run_command("install", "--skill", SKILLS[0])
        self.assert_safety_failure(result, "parent")
        agents.unlink()
        agents.mkdir()
        (agents / "skills").symlink_to(outside, target_is_directory=True)
        result = self.run_command("install", "--skill", SKILLS[0])
        self.assert_safety_failure(result, "parent")

    def test_11_malformed_and_unsupported_state_are_refused(self) -> None:
        state = self.state_path()
        for label, content in (
            ("malformed", b"not json\n"),
            (
                "unsupported",
                json.dumps(
                    {
                        "format_version": 2,
                        "apg_root": str(REPOSITORY_ROOT),
                        "target_root": str(self.repo.resolve()),
                        "managed_skills": [],
                        "created_containers": [],
                        "exclude_separator_added": False,
                    }
                ).encode(),
            ),
            (
                "duplicate key",
                (
                    b'{"format_version":1,"format_version":1,'
                    b'"apg_root":"unused","managed_skills":[],'
                    b'"target_root":"unused",'
                    b'"created_containers":[],'
                    b'"exclude_separator_added":false}\n'
                ),
            ),
        ):
            with self.subTest(label=label):
                state.write_bytes(content)
                state.chmod(0o600)
                result = self.run_command("check")
                self.assert_safety_failure(result, "state")

    def test_12_check_detects_missing_and_tampered_managed_links(self) -> None:
        self.assert_success(
            self.run_command("install", "--skill", SKILLS[0])
        )
        link = self.projection(SKILLS[0])
        link.unlink()
        result = self.run_command("check")
        self.assert_safety_failure(result, "missing")
        link.symlink_to(CANONICAL_ROOT / SKILLS[1], target_is_directory=True)
        result = self.run_command("check")
        self.assert_safety_failure(result, "exact canonical")

    def test_13_uninstall_refuses_a_retargeted_owned_link(self) -> None:
        self.assert_success(
            self.run_command("install", "--skill", SKILLS[0])
        )
        link = self.projection(SKILLS[0])
        link.unlink()
        link.symlink_to(CANONICAL_ROOT / SKILLS[1], target_is_directory=True)
        result = self.run_command("uninstall", "--skill", SKILLS[0])
        self.assert_safety_failure(result, "exact canonical")
        self.assertTrue(link.is_symlink())
        self.assertTrue(self.state_path().exists())

    def test_14_subset_uninstall_updates_links_state_and_exclusion(self) -> None:
        self.assert_success(self.run_command("install"))
        removed = SKILLS[0]
        result = self.run_command("uninstall", "--skill", removed)
        self.assert_success(result)
        self.assertFalse(os.path.lexists(self.projection(removed)))
        remaining = list(SKILLS[1:])
        self.assertEqual(self.read_state()["managed_skills"], remaining)
        exclude = self.exclude_path().read_text()
        self.assertNotIn(f"/.agents/skills/{removed}\n", exclude)
        for skill in remaining:
            self.assertIn(f"/.agents/skills/{skill}\n", exclude)

    def test_15_complete_uninstall_removes_owned_state_and_containers(self) -> None:
        self.assert_success(self.run_command("install"))
        result = self.run_command("uninstall")
        self.assert_success(result)
        self.assertFalse(self.state_path().exists())
        self.assertNotIn(BEGIN_MARKER, self.exclude_path().read_text())
        self.assertFalse((self.repo / ".agents").exists())

    def test_16_repeat_uninstall_is_an_explicit_no_op(self) -> None:
        self.assert_success(self.run_command("install"))
        self.assert_success(self.run_command("uninstall"))
        result = self.run_command("uninstall")
        self.assert_success(result)
        self.assertIn("no-op", result.stdout.lower())
        self.assertFalse(self.state_path().exists())
        check = self.run_command("check")
        self.assert_success(check)
        self.assertIn("compliant uninstalled state", check.stdout.lower())

    def test_17_uninstall_preserves_unrelated_skill_content(self) -> None:
        unrelated = self.repo / ".agents" / "skills" / "local-content"
        unrelated.mkdir(parents=True)
        note = unrelated / "README.md"
        note.write_text("unrelated\n")
        self.assert_success(
            self.run_command("install", "--skill", SKILLS[0])
        )
        self.assert_success(self.run_command("uninstall"))
        self.assertEqual(note.read_text(), "unrelated\n")
        self.assertTrue(unrelated.is_dir())

    def test_18_unrelated_exclude_bytes_are_preserved(self) -> None:
        original = b"# local rule\ncustom/**\nlast-without-newline"
        self.exclude_path().write_bytes(original)
        self.assert_success(
            self.run_command("install", "--skill", SKILLS[0])
        )
        self.assert_success(self.run_command("uninstall"))
        self.assertEqual(self.exclude_path().read_bytes(), original)

    def test_19_duplicate_and_malformed_exclude_blocks_are_refused(self) -> None:
        variants = {
            "duplicate": (
                f"{BEGIN_MARKER}\n{END_MARKER}\n"
                f"{BEGIN_MARKER}\n{END_MARKER}\n"
            ),
            "missing end": f"{BEGIN_MARKER}\n/.agents/skills/{SKILLS[0]}\n",
            "unexpected body": (
                f"{BEGIN_MARKER}\n/.agents/skills/not-canonical\n"
                f"{END_MARKER}\n"
            ),
        }
        for label, content in variants.items():
            with self.subTest(label=label):
                repo = self.create_repository(self.base / f"exclude-{label}")
                self.exclude_path(repo).write_text(content)
                result = self.run_command(
                    "install", "--skill", SKILLS[0], repo=repo
                )
                self.assert_safety_failure(result, "exclude")

    def test_20_target_path_containing_spaces_is_supported(self) -> None:
        repo = self.create_repository(self.base / "target repository with spaces")
        self.assert_success(
            self.run_command("install", "--skill", SKILLS[0], repo=repo)
        )
        self.assert_success(self.run_command("check", repo=repo))
        self.assert_success(self.run_command("uninstall", repo=repo))

        main = self.create_repository(self.base / "linked-main")
        linked = self.base / "linked worktree with spaces"
        self.git(
            "worktree",
            "add",
            "-q",
            "-b",
            "managed-linked",
            str(linked),
            repo=main,
        )
        self.assert_success(
            self.run_command("install", "--skill", SKILLS[0], repo=linked)
        )
        self.assertEqual(
            Path(str(self.read_state(linked)["target_root"])),
            linked.resolve(),
        )
        sibling_link = self.create_manual_link(SKILLS[0], repo=main)
        shared_state_check = self.run_command("check", repo=main)
        self.assert_safety_failure(shared_state_check, "different target worktree")
        shared_state_uninstall = self.run_command("uninstall", repo=main)
        self.assert_safety_failure(
            shared_state_uninstall,
            "different target worktree",
        )
        self.assertTrue(sibling_link.is_symlink())
        self.assertTrue(self.state_path(linked).exists())
        self.assert_success(self.run_command("check", repo=linked))
        self.assert_success(self.run_command("uninstall", repo=linked))

    def test_21_install_and_adopt_leave_normal_git_status_clean(self) -> None:
        self.assert_success(self.run_command("install"))
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        self.assert_success(self.run_command("uninstall"))
        repo = self.create_repository(self.base / "adopt-status")
        for skill in SKILLS:
            self.create_manual_link(skill, repo)
        before = self.git("status", "--porcelain", repo=repo).stdout
        self.assertNotEqual(before, "")
        self.assert_success(self.run_command("adopt", repo=repo))
        self.assertEqual(self.git("status", "--porcelain", repo=repo).stdout, "")

    def test_22_no_tracked_target_state_changes(self) -> None:
        before = self.tracked_fingerprint()
        self.assert_success(self.run_command("install"))
        self.assertEqual(self.tracked_fingerprint(), before)
        self.assert_success(self.run_command("uninstall"))
        self.assertEqual(self.tracked_fingerprint(), before)

        redirected = self.create_repository(self.base / "ambient-redirect")
        environment = self.environment.copy()
        environment.update(
            {
                "GIT_DIR": str(redirected / ".git"),
                "GIT_WORK_TREE": str(redirected),
                "GIT_INDEX_FILE": str(redirected / ".git" / "index"),
            }
        )
        result = self.run_command(
            "install",
            "--skill",
            SKILLS[0],
            environment=environment,
        )
        self.assert_success(result)
        self.assertTrue(self.projection(SKILLS[0]).is_symlink())
        self.assertFalse(os.path.lexists(self.projection(SKILLS[0], redirected)))
        self.assertEqual(self.tracked_fingerprint(), before)

    def test_23_user_level_codex_and_superpowers_files_are_unchanged(self) -> None:
        codex = self.home / ".codex"
        superpowers = codex / "plugins" / "superpowers"
        superpowers.mkdir(parents=True)
        (codex / "config.toml").write_text("sentinel = true\n")
        (superpowers / "SENTINEL").write_text("unchanged\n")
        before = self.home_fingerprint()
        self.assert_success(self.run_command("install"))
        self.assert_success(self.run_command("uninstall"))
        self.assertEqual(self.home_fingerprint(), before)

    def test_24_competing_mutation_lock_fails_closed(self) -> None:
        self.assert_success(
            self.run_command("install", "--skill", SKILLS[0])
        )
        with self.state_path().open("r+") as state:
            fcntl.flock(state.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = self.run_command("install", "--skill", SKILLS[1])
            self.assert_safety_failure(result, "lock")
        self.assertEqual(self.read_state()["managed_skills"], [SKILLS[0]])

    def test_25_mutating_success_includes_restart_reminder(self) -> None:
        install = self.run_command("install", "--skill", SKILLS[0])
        self.assert_success(install)
        self.assertIn(RESTART_REMINDER, install.stdout)
        uninstall = self.run_command("uninstall")
        self.assert_success(uninstall)
        self.assertIn(RESTART_REMINDER, uninstall.stdout)
        self.create_manual_link(SKILLS[0])
        adopt = self.run_command("adopt", "--skill", SKILLS[0])
        self.assert_success(adopt)
        self.assertIn(RESTART_REMINDER, adopt.stdout)

    def test_26_usage_and_exit_status_contract(self) -> None:
        for arguments in (
            (),
            ("unknown",),
            ("install", "--unknown"),
            ("install", "--skill", "not-a-canonical-skill"),
            ("list", "--repo", str(self.repo)),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_command(*arguments)
                self.assertEqual(result.returncode, 2, result)
        help_result = self.run_command("--help")
        self.assert_success(help_result)
        self.assertIn("install", help_result.stdout)

    def test_27_idempotent_install_refuses_visible_managed_projection(
        self,
    ) -> None:
        skill = SKILLS[0]
        self.assert_success(
            self.run_command("install", "--skill", skill)
        )
        self.reinclude_managed_projection(skill)
        unrelated = self.repo / "local-sentinel"
        unrelated.write_bytes(b"preserve me\n")
        before = self.managed_fingerprint(skill)

        result = self.run_command("install", "--skill", skill)

        self.assert_safety_failure(result, "visible in normal git status")
        self.assertIn("run check before retrying", result.stderr.lower())
        self.assertEqual(self.managed_fingerprint(skill), before)
        self.assertEqual(unrelated.read_bytes(), b"preserve me\n")
        check = self.run_command("check")
        self.assert_safety_failure(check, "not clean in normal git status")

    def test_29_mixed_process_and_profile_subset_is_supported(self) -> None:
        selected = ("debugging-systematically", "python-language-profile")
        result = self.run_command(
            "install", "--skill", selected[0], "--skill", selected[1]
        )
        self.assert_success(result)
        self.assertEqual(self.read_state()["managed_skills"], list(selected))
        self.assert_success(self.run_command("check"))

    def test_30_existing_six_skill_state_remains_valid_without_expansion(
        self,
    ) -> None:
        arguments = [item for skill in V0_2_SKILLS for item in ("--skill", skill)]
        self.assert_success(self.run_command("install", *arguments))
        inodes = {
            skill: self.projection(skill).lstat().st_ino for skill in V0_2_SKILLS
        }

        self.assert_success(self.run_command("check"))
        self.assert_success(self.run_command("install"))
        self.assert_success(self.run_command("adopt"))

        self.assertEqual(self.read_state()["managed_skills"], list(V0_2_SKILLS))
        self.assertEqual(
            inodes,
            {
                skill: self.projection(skill).lstat().st_ino
                for skill in V0_2_SKILLS
            },
        )

    def test_28_idempotent_adopt_refuses_visible_managed_projection(
        self,
    ) -> None:
        skill = SKILLS[0]
        self.create_manual_link(skill)
        self.assert_success(
            self.run_command("adopt", "--skill", skill)
        )
        self.reinclude_managed_projection(skill)
        unrelated = self.repo / "local-sentinel"
        unrelated.write_bytes(b"preserve me\n")
        before = self.managed_fingerprint(skill)

        result = self.run_command("adopt", "--skill", skill)

        self.assert_safety_failure(result, "visible in normal git status")
        self.assertIn("run check before retrying", result.stderr.lower())
        self.assertEqual(self.managed_fingerprint(skill), before)
        self.assertEqual(unrelated.read_bytes(), b"preserve me\n")
        check = self.run_command("check")
        self.assert_safety_failure(check, "not clean in normal git status")


if __name__ == "__main__":
    unittest.main(verbosity=2)
