"""Fixed-vector subprocess adapter for the Git command-line interface."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Mapping, Sequence


class GitError(RuntimeError):
    """A bounded Git discovery or collection failure."""


class GitAdapter:
    """Run Git without shell evaluation, pagers, optional locks, or color."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def discover(cwd: Path) -> "GitAdapter":
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            env=_base_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        if completed.returncode != 0:
            raise GitError("current directory is not inside a git repository")
        try:
            value = completed.stdout.rstrip(b"\n").decode("utf-8")
        except UnicodeDecodeError as error:
            raise GitError("repository root is not valid UTF-8") from error
        if not value:
            raise GitError("repository root is unavailable")
        return GitAdapter(Path(value))

    def run(
        self,
        arguments: Sequence[str],
        *,
        environment: Mapping[str, str] | None = None,
        input_bytes: bytes | None = None,
        diagnostic: str = "Git command failed",
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        child_environment = _base_environment()
        if environment:
            child_environment.update(environment)
        run_options: dict[str, object] = {
            "env": child_environment,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "shell": False,
        }
        if input_bytes is None:
            run_options["stdin"] = subprocess.DEVNULL
        else:
            run_options["input"] = input_bytes
        completed = subprocess.run(
            ["git", "-C", os.fspath(self.root), "--no-pager", *arguments],
            **run_options,
        )
        if check and completed.returncode != 0:
            raise GitError(diagnostic)
        return completed

    def text(self, arguments: Sequence[str], *, diagnostic: str) -> str:
        output = self.run(arguments, diagnostic=diagnostic).stdout.rstrip(b"\n")
        try:
            return output.decode("utf-8")
        except UnicodeDecodeError as error:
            raise GitError(f"{diagnostic}: output is not valid UTF-8") from error


def _base_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "LC_ALL": "C",
            "LANG": "C",
            "GIT_PAGER": "cat",
            "PAGER": "cat",
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )
    return environment
