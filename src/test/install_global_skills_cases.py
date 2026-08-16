"""Shared disposable fixtures for the global-skill installer tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Mapping

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "install-global-skills"


def add_skill(repository: Path, relative: str, body: str = "# Skill\n") -> Path:
    skill = repository / "skills" / relative
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(body, encoding="utf-8")
    return skill.resolve()


def run_command(
    *arguments: object,
    environment: Mapping[str, str] | None = None,
    cwd: Path = REPOSITORY_ROOT,
) -> subprocess.CompletedProcess[str]:
    command_environment = os.environ.copy()
    if environment is not None:
        command_environment.update(environment)
    return subprocess.run(
        [str(COMMAND), *(str(argument) for argument in arguments)],
        cwd=cwd,
        env=command_environment,
        text=True,
        capture_output=True,
        check=False,
    )


def tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes | str], ...]:
    if not root.exists():
        return ()
    entries: list[tuple[str, str, bytes | str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append((relative, "link", os.readlink(path)))
        elif path.is_file():
            entries.append((relative, "file", path.read_bytes()))
        elif path.is_dir():
            entries.append((relative, "directory", b""))
    return tuple(entries)


def read_state(skills_root: Path) -> dict[str, object]:
    return json.loads(
        (skills_root / ".install-global-skills-state.json").read_text(
            encoding="utf-8"
        )
    )
