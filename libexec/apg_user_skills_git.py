"""Bounded Git process helpers for the user-scoped skill lifecycle."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Callable, NoReturn, Sequence


GIT_ENV_NAMES = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}


def git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if name in GIT_ENV_NAMES or name.startswith("GIT_CONFIG_KEY_") or name.startswith("GIT_CONFIG_VALUE_"):
            environment.pop(name)
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return environment


def run_git(
    repository: Path,
    arguments: Sequence[str],
    *,
    allow_failure: bool = False,
    fail: Callable[[str], NoReturn],
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.fsmonitor=false",
                "-c",
                f"core.hooksPath={os.devnull}",
                "-C",
                str(repository),
                *arguments,
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=git_environment(),
        )
    except OSError as error:
        fail(f"Git could not be executed: {error.strerror}")
    if result.returncode and not allow_failure:
        detail = result.stderr.decode("utf-8", "replace").strip() or "Git returned no diagnostic"
        fail(f"Git source query failed: {detail}")
    return result


def text_git(
    repository: Path,
    arguments: Sequence[str],
    *,
    allow_failure: bool = False,
    run_git: Callable[..., subprocess.CompletedProcess[bytes]],
) -> str:
    result = run_git(repository, arguments, allow_failure=allow_failure)
    return result.stdout.decode("utf-8", "strict").strip()
