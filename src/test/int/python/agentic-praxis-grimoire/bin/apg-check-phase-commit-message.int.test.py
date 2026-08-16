#!/usr/bin/env python3
"""Integration tests for bin/apg-check-phase-commit-message."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-check-phase-commit-message"
HELPER = REPOSITORY_ROOT / "libexec" / "apg_phase_commit_message.py"
PACKAGE = REPOSITORY_ROOT / "src" / "agentic_praxis_grimoire"
DIRECT_HELPERS = (
    "apg_phase_commit_message.py",
    "apg_project_skills_commands.py",
    "apg_public_release.py",
    "apg_record_identity.py",
    "apg_skill_library_check.py",
    "apg_test.py",
    "apg_user_skills.py",
)
FIXTURE = (
    REPOSITORY_ROOT
    / "src"
    / "test"
    / "fixtures"
    / "apg26a"
    / "apg26-subject-only.message.txt"
)
VALID_MESSAGE = """APG26A: Enforce formal-phase commit messages

Scope:
- Add the checker.

Result:
- Formal-phase commit messages are mechanically validated.

Verification:
- Focused tests pass.

Not run:
- none
"""


class APGPhaseCommitMessageIntegrationTests(unittest.TestCase):
    """Exercise message-file, Git, usage, and installed-layout behavior."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="apg-commit-message-")
        self.root = Path(self.temporary.name)
        self.message_file = self.root / "message.txt"
        self.message_file.write_text(VALID_MESSAGE, encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_checker(
        self,
        *arguments: str,
        command: Path = COMMAND,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(command), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd if cwd is not None else self.root,
            env=os.environ.copy(),
        )

    def git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.root,
            env=os.environ.copy(),
        )

    def initialize_repository(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.name", "APG Test")
        self.git("config", "user.email", "apg-test@example.invalid")
        tracked = self.root / "tracked.txt"
        tracked.write_text("tracked\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        self.git("commit", "-q", "-F", str(self.message_file))

    def test_message_file_text_and_json_results(self) -> None:
        text_result = self.run_checker(
            "--phase",
            "APG26A",
            "--message-file",
            str(self.message_file),
        )
        self.assertEqual(text_result.returncode, 0, text_result)
        self.assertEqual(
            text_result.stdout,
            "PASS APG phase commit message: APG26A (message-file)\n",
        )

        invalid = self.root / "private-value.message.txt"
        invalid.write_bytes(FIXTURE.read_bytes())
        json_result = self.run_checker(
            "--phase",
            "APG26",
            "--message-file",
            str(invalid),
            "--format",
            "json",
        )
        self.assertEqual(json_result.returncode, 1, json_result)
        payload = json.loads(json_result.stdout)
        self.assertEqual(payload["status"], "fail")
        self.assertIn(
            "APGCM006", {item["code"] for item in payload["diagnostics"]}
        )
        self.assertNotIn(invalid.name, json_result.stdout)

    def test_exactly_one_message_source_is_required(self) -> None:
        missing = self.run_checker("--phase", "APG26A")
        duplicate = self.run_checker(
            "--phase",
            "APG26A",
            "--message-file",
            str(self.message_file),
            "--commit",
            "HEAD",
        )
        self.assertEqual(missing.returncode, 2, missing)
        self.assertEqual(duplicate.returncode, 2, duplicate)

    def test_commit_source_reads_the_exact_git_commit_message(self) -> None:
        self.initialize_repository()
        result = self.run_checker(
            "--phase",
            "APG26A",
            "--commit",
            "HEAD",
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result)
        self.assertEqual(
            result.stdout,
            "PASS APG phase commit message: APG26A (commit)\n",
        )

    def test_noncommit_revision_is_a_repository_error(self) -> None:
        self.initialize_repository()
        blob = self.root / "blob.txt"
        blob.write_text("not a commit\n", encoding="utf-8")
        object_id = self.git("hash-object", "-w", "blob.txt").stdout.strip()
        result = self.run_checker(
            "--phase",
            "APG26A",
            "--commit",
            object_id,
            "--format",
            "json",
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 3, result)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["diagnostics"][0]["code"], "APGCMR001")
        self.assertNotIn(object_id, result.stdout)

    def test_incomplete_commit_object_is_a_repository_error(self) -> None:
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake_git = fake_bin / "git"
        fake_git.write_text(
            "#!/bin/sh\n"
            "case \"$*\" in\n"
            "  *rev-parse*) printf '%040d\\n' 0 ;;\n"
            "  *cat-file*) printf 'malformed commit object\\n' ;;\n"
            "  *) exit 2 ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"
        result = subprocess.run(
            [
                str(COMMAND),
                "--phase",
                "APG26A",
                "--commit",
                "HEAD",
                "--format",
                "json",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.root,
            env=environment,
        )
        self.assertEqual(result.returncode, 3, result)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["diagnostics"][0]["code"], "APGCMR001")

    def test_remaining_python_helpers_expose_direct_help_entrypoints(self) -> None:
        for helper_name in DIRECT_HELPERS:
            with self.subTest(helper=helper_name):
                result = subprocess.run(
                    [
                        sys.executable,
                        os.fspath(REPOSITORY_ROOT / "libexec" / helper_name),
                        "--help",
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=REPOSITORY_ROOT,
                    env=os.environ.copy(),
                )
                self.assertEqual(result.returncode, 0, result)
                self.assertIn("usage:", result.stdout)

    def test_installed_style_layout_finds_its_helper(self) -> None:
        installed = self.root / "installed"
        installed_bin = installed / "bin"
        installed_libexec = installed / "libexec"
        installed_bin.mkdir(parents=True)
        installed_libexec.mkdir()
        command = installed_bin / COMMAND.name
        shutil.copy2(COMMAND, command)
        shutil.copy2(HELPER, installed_libexec / HELPER.name)
        shutil.copytree(
            PACKAGE,
            installed / "src" / PACKAGE.name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        result = self.run_checker(
            "--phase",
            "APG26A",
            "--message-file",
            str(self.message_file),
            command=command,
        )
        self.assertEqual(result.returncode, 0, result)

    def test_wrapper_delegates_exact_arguments_to_canonical_adapter(self) -> None:
        installed = self.root / "adapter-install"
        command = installed / "bin" / COMMAND.name
        adapter = installed / "src" / "agentic_praxis_grimoire"
        (installed / "libexec").mkdir(parents=True)
        command.parent.mkdir(parents=True)
        adapter.mkdir(parents=True)
        shutil.copy2(COMMAND, command)
        command.chmod(0o755)
        (installed / "libexec" / HELPER.name).write_text("# adapter fixture\n")
        (adapter / "__init__.py").write_text("", encoding="utf-8")
        (adapter / "cli.py").write_text(
            "import sys\n"
            "from pathlib import Path\n"
            "def compatibility_main(command, root):\n"
            "    print(f'{command}|{Path(root)}|{sys.argv[1:]}')\n"
            "    return 7\n",
            encoding="utf-8",
        )
        result = self.run_checker(
            "--phase",
            "APG26A",
            "--message-file",
            str(self.message_file),
            command=command,
        )
        expected_root = command.parent.parent.resolve()
        self.assertEqual(result.returncode, 7, result)
        self.assertEqual(
            result.stdout,
            f"apg-check-phase-commit-message|{expected_root}|"
            "['--phase', 'APG26A', '--message-file', "
            f"'{self.message_file}']\n",
        )
        self.assertEqual(result.stderr, "")

    def test_real_cli_rejects_each_message_structure_boundary(self) -> None:
        cases = (
            (b"\xff", "APGCM001"),
            (b"APG26A: Result\tbad\n", "APGCM002"),
            (b"", "APGCM003"),
            (VALID_MESSAGE.replace("APG26A:", "APG27:").encode(), "APGCM004"),
            (VALID_MESSAGE.replace("APG26A: Enforce formal-phase commit messages", "APG26A: ").encode(), "APGCM005"),
            (VALID_MESSAGE.replace("\n\nScope:", "\nScope:").encode(), "APGCM006"),
            (VALID_MESSAGE.replace("Not run:\n- none\n", "").encode(), "APGCM007"),
            (VALID_MESSAGE.replace("Scope:\n- Add the checker.\n\nResult:\n- Formal-phase commit messages are mechanically validated.", "Result:\n- Formal-phase commit messages are mechanically validated.\n\nScope:\n- Add the checker.").encode(), "APGCM008"),
            (VALID_MESSAGE.replace("Verification:\n- Focused tests pass.", "Verification:\n").encode(), "APGCM009"),
            (VALID_MESSAGE.replace("Not run:\n- none", "Not run:\nnone").encode(), "APGCM010"),
        )
        for index, (content, code) in enumerate(cases):
            path = self.root / f"invalid-{index}.message.txt"
            path.write_bytes(content)
            result = self.run_checker(
                "--phase",
                "APG26A",
                "--message-file",
                str(path),
                "--format",
                "json",
            )
            self.assertEqual(result.returncode, 1, result)
            self.assertIn(code, {item["code"] for item in json.loads(result.stdout)["diagnostics"]})

        invalid_phase = self.run_checker(
            "--phase",
            "apg26a",
            "--message-file",
            str(self.message_file),
        )
        self.assertEqual(invalid_phase.returncode, 2)
        control_revision = self.run_checker(
            "--phase",
            "APG26A",
            "--commit",
            "bad\nrevision",
        )
        self.assertEqual(control_revision.returncode, 2)

    def test_message_file_source_rejects_symlink_directory_and_missing_path(self) -> None:
        symlink = self.root / "message-link"
        symlink.symlink_to(self.message_file)
        directory = self.root / "message-directory"
        directory.mkdir()
        for path in (symlink, directory, self.root / "missing"):
            result = self.run_checker(
                "--phase",
                "APG26A",
                "--message-file",
                str(path),
                "--format",
                "json",
            )
            self.assertEqual(result.returncode, 3, result)
            self.assertEqual(
                json.loads(result.stdout)["diagnostics"][0]["code"],
                "APGCMR002",
            )

    def test_revision_length_boundaries_are_usage_errors(self) -> None:
        for revision in ("", "x" * 1025):
            with self.subTest(length=len(revision)):
                result = self.run_checker(
                    "--phase",
                    "APG26A",
                    "--commit",
                    revision,
                )
                self.assertEqual(result.returncode, 2, result)

    def test_invalid_message_has_bounded_text_diagnostics(self) -> None:
        self.message_file.write_text("APG26A: \n", encoding="utf-8")
        result = self.run_checker(
            "--phase",
            "APG26A",
            "--message-file",
            str(self.message_file),
        )
        self.assertEqual(result.returncode, 1, result)
        self.assertIn("FAIL APG phase commit message", result.stdout)
        self.assertIn("diagnostics", result.stdout)


if __name__ == "__main__":
    unittest.main()
