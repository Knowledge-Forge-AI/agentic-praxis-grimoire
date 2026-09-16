#!/usr/bin/env python3
"""APGR tracked Python candidate inventory and exclusion census manager."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

CANDIDATE_ROOTS = (
    "src/agentic_praxis_grimoire",
    "libexec",
    "tools",
    "release/ci",
    "src/test",
    "bin",
)

EXCLUSION_CLASSES = (
    "private",
    "cache",
    "vendor",
    "generated",
    "projections",
    "non_python",
    "non_candidate_root",
)


class PythonInventoryOperationalError(RuntimeError):
    """Report an operational failure during Python inventory discovery."""


@dataclass(frozen=True, slots=True)
class PythonFileEntry:
    """A repository-relative tracked Python candidate file."""

    path: str
    line_count: int
    syntax_owner: str
    lint_owner: str
    type_owner: str | None
    role: str
    sha256: str

    def to_jsonable(self) -> dict[str, object]:
        return {
            "path": self.path,
            "lines": self.line_count,
            "syntax_owner": self.syntax_owner,
            "lint_owner": self.lint_owner,
            "type_owner": self.type_owner,
            "role": self.role,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class InventoryResult:
    """Stable result contract for one completed repository Python census."""

    entries: tuple[PythonFileEntry, ...]
    excluded_counts: dict[str, int]
    total_files: int
    total_lines: int

    def to_jsonable(self) -> dict[str, object]:
        return {
            "schema": "apg-python-inventory-result-v1",
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "excluded_counts": dict(self.excluded_counts),
            "modules": [entry.to_jsonable() for entry in self.entries],
        }


def count_physical_lines(path: Path) -> int:
    """Count LF-delimited physical lines: empty=0, final unterminated=1."""
    line_count = 0
    final_byte: int | None = None
    try:
        with path.open("rb") as source:
            while chunk := source.read(64 * 1024):
                line_count += chunk.count(b"\n")
                final_byte = chunk[-1]
    except OSError as error:
        raise PythonInventoryOperationalError(
            f"unable to read candidate file: {path}"
        ) from error
    if final_byte is not None and final_byte != ord("\n"):
        line_count += 1
    return line_count


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of file physical bytes."""
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as source:
            while chunk := source.read(64 * 1024):
                hasher.update(chunk)
    except OSError as error:
        raise PythonInventoryOperationalError(
            f"unable to read candidate file: {path}"
        ) from error
    return hasher.hexdigest()


def is_candidate_root(parts: tuple[str, ...]) -> bool:
    """Determine if path parts belong to an approved candidate directory."""
    if not parts:
        return False
    if parts[0] in ("libexec", "tools", "bin"):
        return True
    return len(parts) >= 2 and parts[:2] in (
        ("release", "ci"),
        ("src", "agentic_praxis_grimoire"),
        ("src", "test"),
    )


def classify_exclusion(parts: tuple[str, ...]) -> str | None:
    """Classify excluded paths by explicit class."""
    if "private" in parts:
        return "private"
    if any(
        part in (
            ".pytest_cache",
            "__pycache__",
            ".mypy_cache",
            ".ruff_cache",
            ".tox",
            ".nox",
        )
        for part in parts
    ):
        return "cache"
    if any(part in ("node_modules", ".venv", "vendor") for part in parts):
        return "vendor"
    if any(part in ("build", "dist") or part.endswith(".egg-info") for part in parts):
        return "generated"
    if parts[:2] == (".agents", "skills"):
        return "projections"
    if ".scratch" in parts:
        return "generated"
    if not is_candidate_root(parts):
        return "non_candidate_root"
    return None


def is_python_candidate(
    posix_path: PurePosixPath,
    full_path: Path | None = None,
) -> bool:
    """Check whether a path under approved candidate roots is a Python candidate."""
    parts = posix_path.parts
    if not is_candidate_root(parts):
        return False
    if parts[0] == "bin":
        if posix_path.suffix == ".py":
            return True
        if posix_path.suffix == "" and full_path is not None:
            try:
                with full_path.open("rb") as stream:
                    first_line = stream.readline()
                return first_line.startswith(b"#!") and b"python" in first_line
            except OSError as error:
                raise PythonInventoryOperationalError("Python entry-script input is unreadable") from error
        return False
    return posix_path.suffix == ".py"


def _git_clean_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }


def _run_git_ls_files(
    repo_root: Path,
    include_untracked: bool = False,
) -> list[str]:
    """Query Git index inventory (and optionally untracked files)."""
    env = _git_clean_env()
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-z"],
            check=False,
            capture_output=True,
            env=env,
        )
    except OSError as error:
        raise PythonInventoryOperationalError(
            f"unable to run Git in {repo_root}"
        ) from error
    if proc.returncode != 0:
        raise PythonInventoryOperationalError(
            f"Git ls-files failed in {repo_root}"
        )

    raw_paths = [os.fsdecode(item) for item in proc.stdout.split(b"\0") if item]

    if include_untracked:
        try:
            untracked_proc = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "ls-files",
                    "-z",
                    "--others",
                    "--exclude-standard",
                ],
                check=False,
                capture_output=True,
                env=env,
            )
            if untracked_proc.returncode != 0:
                raise PythonInventoryOperationalError("untracked inventory command failed")
            raw_paths.extend(os.fsdecode(item) for item in untracked_proc.stdout.split(b"\0") if item)
        except OSError as error:
            raise PythonInventoryOperationalError("untracked inventory unavailable") from error

    return sorted(set(raw_paths))


def validate_worktree_root(repo_root: Path) -> Path:
    """Validate and resolve repository root, ensuring it is a Git worktree."""
    try:
        resolved = repo_root.expanduser().resolve()
    except (OSError, RuntimeError) as error:
        raise PythonInventoryOperationalError(
            f"unable to resolve repository root: {repo_root}"
        ) from error
    if not resolved.is_dir():
        raise PythonInventoryOperationalError(
            f"repository root is not a directory: {resolved}"
        )

    env = _git_clean_env()
    try:
        proc = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            env=env,
        )
    except OSError as error:
        raise PythonInventoryOperationalError(
            f"unable to run Git to validate worktree: {resolved}"
        ) from error
    if proc.returncode != 0:
        raise PythonInventoryOperationalError(
            f"repository root is not a Git worktree: {resolved}"
        )

    top_level = Path(os.fsdecode(proc.stdout.strip())).resolve()
    if top_level != resolved:
        raise PythonInventoryOperationalError(
            f"repository root {resolved} is not top-level Git worktree {top_level}"
        )
    return resolved


def discover_python_inventory(
    repo_root: Path,
    *,
    include_untracked: bool = False,
) -> InventoryResult:
    """Perform shared deterministic Python candidate discovery and exclusion census."""
    resolved_root = validate_worktree_root(repo_root)
    tracked_paths = _run_git_ls_files(resolved_root, include_untracked=include_untracked)

    excluded_counts: dict[str, int] = {cls: 0 for cls in EXCLUSION_CLASSES}
    entries: list[PythonFileEntry] = []

    for rel_str in tracked_paths:
        posix_path = PurePosixPath(rel_str)
        if posix_path.is_absolute() or ".." in posix_path.parts:
            raise PythonInventoryOperationalError(
                f"tracked path escapes repository root: {rel_str}"
            )

        parts = posix_path.parts
        exclusion_class = classify_exclusion(parts)
        if exclusion_class is not None:
            excluded_counts[exclusion_class] += 1
            continue

        full_path = resolved_root.joinpath(*posix_path.parts)
        ancestor = resolved_root
        for part in posix_path.parts[:-1]:
            ancestor = ancestor / part
            if ancestor.is_symlink():
                raise PythonInventoryOperationalError("candidate ancestor is a symlink")
        if full_path.is_symlink():
            raise PythonInventoryOperationalError(
                f"tracked candidate path is a symlink: {rel_str}"
            )
        if not full_path.is_file():
            raise PythonInventoryOperationalError(
                f"tracked candidate is missing or not a regular file: {rel_str}"
            )

        if is_python_candidate(posix_path, full_path):
            line_count = count_physical_lines(full_path)
            sha256 = compute_file_sha256(full_path)
            role = (
                "fixture-or-test"
                if len(parts) >= 2 and parts[:2] == ("src", "test")
                else "maintained-source"
            )
            type_owner = (
                "mypy"
                if len(parts) >= 2 and parts[:2] == ("src", "agentic_praxis_grimoire")
                else None
            )
            entries.append(
                PythonFileEntry(
                    path=posix_path.as_posix(),
                    line_count=line_count,
                    syntax_owner="python-compile",
                    lint_owner="ruff",
                    type_owner=type_owner,
                    role=role,
                    sha256=sha256,
                )
            )
        else:
            excluded_counts["non_python"] += 1

    entries.sort(key=lambda item: item.path)
    if not entries:
        raise PythonInventoryOperationalError("Python candidate inventory is empty")
    total_lines = sum(item.line_count for item in entries)
    return InventoryResult(
        entries=tuple(entries),
        excluded_counts=excluded_counts,
        total_files=len(entries),
        total_lines=total_lines,
    )


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="APGR tracked Python candidate inventory and census."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(),
        help="repository root directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=True,
        help="emit JSON output",
    )
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        default=False,
        help="include non-ignored untracked files for prospective capture testing",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = discover_python_inventory(
            args.repo_root,
            include_untracked=args.include_untracked,
        )
        rendered = json.dumps(result.to_jsonable(), indent=2, sort_keys=True) + "\n"
        sys.stdout.write(rendered)
        return 0
    except PythonInventoryOperationalError as error:
        print(f"python-inventory: error: {error}", file=sys.stderr)
        return 2
    except (OSError, TypeError, ValueError) as error:
        print(f"python-inventory: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
