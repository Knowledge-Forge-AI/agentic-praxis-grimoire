"""Shared disposable repositories for user-scoped skill integration tests."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))
public_release = importlib.import_module("apg_public_release")

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


class APGUserSkillsFixture:
    """Build isolated release and user-state fixtures for lifecycle tests."""

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
        self.rewritten = self.make_release(self.root / "rewritten-v0.1.0", "0.1.0", "rewritten")
        self.launcher = self.root / "apg-user-skills-test-launcher.py"
        self.launcher.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'libexec')!r})\n"
            "import apg_user_skills as command\n"
            f"command.PUBLIC_V01_COMMIT = {self.git(self.first, 'rev-parse', 'HEAD').stdout.strip()!r}\n"
            f"command.PUBLIC_V01_TREE = {self.git(self.first, 'rev-parse', 'HEAD^{tree}').stdout.strip()!r}\n"
            "raise SystemExit(command.main())\n"
        )
        self.compatibility_launcher = self.root / "apg-user-skills-compatibility-launcher.py"
        self.compatibility_launcher.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'libexec')!r})\n"
            "import apg_user_skills as command\n"
            f"command.PUBLIC_V01_COMMIT = {self.git(self.rewritten, 'rev-parse', 'HEAD').stdout.strip()!r}\n"
            f"command.PUBLIC_V01_TREE = {self.git(self.rewritten, 'rev-parse', 'HEAD^{tree}').stdout.strip()!r}\n"
            f"command.LEGACY_V01_COMMIT = {self.git(self.first, 'rev-parse', 'HEAD').stdout.strip()!r}\n"
            f"command.LEGACY_V01_TREE = {self.git(self.first, 'rev-parse', 'HEAD^{tree}').stdout.strip()!r}\n"
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
        self,
        *arguments: str,
        environment: dict[str, str] | None = None,
        launcher: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(launcher or self.launcher), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.root,
            env=environment or self.environment,
        )

    def invoke(
        self,
        operation: str,
        *arguments: str,
        source: Path | None = None,
        launcher: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [operation]
        if operation in {"list", "install", "adopt", "update"}:
            command.extend(["--source", str(source or self.first)])
        command.extend(["--skills-root", str(self.skills_root), *arguments])
        return self.run_command(*command, launcher=launcher)

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
