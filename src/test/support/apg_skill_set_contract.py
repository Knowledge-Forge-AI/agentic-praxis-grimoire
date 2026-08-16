"""Exact canonical skill-name derivation for retained dynamic consumers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NoReturn, Sequence

from apg_repository_path_contract import RepositoryPathContract, RepositoryPathError


SAFE_SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class SkillSetError(ValueError):
    """A dynamic skill-name set is unsafe or does not match canonical owners."""


def _fail(message: str) -> NoReturn:
    raise SkillSetError(message)


def _require_name(name: str) -> str:
    if not isinstance(name, str) or len(name) > 64 or not SAFE_SKILL_NAME.fullmatch(name):
        _fail("skill name is not one safe canonical component")
    return name


def canonical_skill_names(root: Path) -> tuple[str, ...]:
    """Derive the expected set only from descriptor-relative canonical leaves."""

    names: list[str] = []
    try:
        with RepositoryPathContract(root) as repository:
            if repository.entry_kind("skills") != "directory":
                _fail("canonical skills root is not a direct directory")
            for entry in repository.directory_entries("skills"):
                if entry == "README.md":
                    continue
                if entry == "chatgpt":
                    if repository.entry_kind("skills/chatgpt") != "directory":
                        _fail("canonical namespace is not a direct directory")
                    leaves = repository.directory_entries("skills/chatgpt")
                    prefix = "skills/chatgpt"
                else:
                    leaves = (entry,)
                    prefix = "skills"
                for leaf in leaves:
                    name = _require_name(leaf)
                    leaf_relative = f"{prefix}/{leaf}"
                    if repository.entry_kind(leaf_relative) != "directory":
                        _fail("canonical skill leaf is not a direct directory")
                    marker = f"{leaf_relative}/SKILL.md"
                    if repository.entry_kind(marker) != "regular":
                        _fail("canonical skill marker is not a direct regular file")
                    names.append(name)
    except RepositoryPathError as error:
        raise SkillSetError(f"canonical skill set path is invalid: {error}") from error
    if len(names) != len(set(names)):
        _fail("canonical skill-name set contains duplicates")
    return tuple(sorted(names))


def require_exact_skill_names(
    names: Sequence[str], expected: Sequence[str], *, consumer: str
) -> tuple[str, ...]:
    """Reject unsafe, unsorted, duplicate, missing, or extra dynamic names."""

    received = list(names)
    if any(
        not isinstance(name, str)
        or len(name) > 64
        or not SAFE_SKILL_NAME.fullmatch(name)
        for name in received
    ):
        _fail(f"{consumer} returned an unsafe skill name")
    if received != sorted(received):
        _fail(f"{consumer} returned an unsorted skill set")
    if len(received) != len(set(received)):
        _fail(f"{consumer} returned duplicate skill names")
    expected_tuple = tuple(expected)
    if tuple(received) != expected_tuple:
        _fail(f"{consumer} returned a skill set different from canonical owners")
    return expected_tuple
