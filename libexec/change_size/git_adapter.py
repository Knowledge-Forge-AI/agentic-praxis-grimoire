"""Fixed-argument Git object access for change-size checking."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
from typing import Iterable


_OID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class GitError(RuntimeError):
    """Git state is unavailable or malformed."""


@dataclass(frozen=True, slots=True)
class Entry:
    path: str
    mode: str
    oid: str
    size: int


class GitRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._blob_cache: dict[str, bytes] = {}

    @classmethod
    def discover(cls, cwd: Path) -> "GitRepository":
        result = cls._invoke(cwd, ["rev-parse", "--show-toplevel"])
        try:
            root = Path(result.stdout.rstrip(b"\n").decode("utf-8"))
        except UnicodeError as error:
            raise GitError("Git root is not valid UTF-8") from error
        if not root.is_absolute() or not root.is_dir():
            raise GitError("Git root is malformed")
        return cls(root)

    @staticmethod
    def _environment() -> dict[str, str]:
        allowed = {
            key: value
            for key, value in os.environ.items()
            if key in {"HOME", "PATH", "SYSTEMROOT", "TMPDIR"}
        }
        allowed.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": os.devnull,
                "GIT_NO_LAZY_FETCH": "1",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_PAGER": "cat",
                "LC_ALL": "C",
            }
        )
        return allowed

    @classmethod
    def _invoke(
        cls,
        cwd: Path,
        arguments: list[str],
        *,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            env=cls._environment(),
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            raise GitError("Git object inspection failed")
        return result

    def run(self, arguments: list[str], *, input_bytes: bytes | None = None) -> bytes:
        return self._invoke(self.root, arguments, input_bytes=input_bytes).stdout

    def resolve_commit(self, value: str) -> str:
        raw = self.run(["rev-parse", "--verify", f"{value}^{{commit}}"])
        try:
            oid = raw.rstrip(b"\n").decode("ascii").lower()
        except UnicodeError as error:
            raise GitError("commit identity is malformed") from error
        if not _OID.fullmatch(oid):
            raise GitError("commit identity is malformed")
        return oid

    def head(self) -> str:
        return self.resolve_commit("HEAD")

    def parent(self, commit: str) -> str | None:
        raw = self.run(["rev-list", "--parents", "-n", "1", commit])
        parts = raw.decode("ascii").strip().split()
        if not parts or parts[0] != commit:
            raise GitError("commit parent data is malformed")
        return parts[1] if len(parts) > 1 else None

    @staticmethod
    def _path(raw: bytes) -> str:
        try:
            path = raw.decode("utf-8")
        except UnicodeError as error:
            raise GitError("tracked path is not valid UTF-8") from error
        if (
            not path
            or path.startswith("/")
            or any(ord(character) < 32 or ord(character) == 127 for character in path)
        ):
            raise GitError("tracked path is unsafe")
        return path

    def tree_entries(self, commit: str) -> dict[str, Entry]:
        records = self.run(["ls-tree", "-rlz", commit]).split(b"\0")
        entries: dict[str, Entry] = {}
        for record in records:
            if not record:
                continue
            try:
                metadata, raw_path = record.split(b"\t", 1)
                mode, object_type, raw_oid, raw_size = metadata.split(b" ", 3)
                if object_type != b"blob":
                    continue
                oid = raw_oid.decode("ascii")
                size = int(raw_size)
            except (ValueError, UnicodeError) as error:
                raise GitError("tree entry is malformed") from error
            path = self._path(raw_path)
            entries[path] = Entry(path, mode.decode("ascii"), oid, size)
        return entries

    def _sizes(self, oids: Iterable[str]) -> dict[str, int]:
        unique = sorted(set(oids))
        if not unique:
            return {}
        output = self.run(
            ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
            input_bytes=("".join(f"{oid}\n" for oid in unique)).encode("ascii"),
        )
        sizes: dict[str, int] = {}
        for line in output.splitlines():
            try:
                raw_oid, object_type, raw_size = line.split(b" ")
                if object_type != b"blob":
                    raise ValueError
                sizes[raw_oid.decode("ascii")] = int(raw_size)
            except (ValueError, UnicodeError) as error:
                raise GitError("blob size response is malformed") from error
        if set(sizes) != set(unique):
            raise GitError("blob size response is incomplete")
        return sizes

    def index_entries(self) -> dict[str, Entry]:
        records = self.run(["ls-files", "-s", "-z"]).split(b"\0")
        parsed: list[tuple[str, str, str]] = []
        for record in records:
            if not record:
                continue
            try:
                metadata, raw_path = record.split(b"\t", 1)
                raw_mode, raw_oid, stage = metadata.split(b" ")
            except ValueError as error:
                raise GitError("index entry is malformed") from error
            if stage != b"0":
                raise GitError("unmerged index entries are unsupported")
            if raw_mode == b"160000":
                continue
            parsed.append(
                (
                    self._path(raw_path),
                    raw_mode.decode("ascii"),
                    raw_oid.decode("ascii"),
                )
            )
        sizes = self._sizes(oid for _, _, oid in parsed)
        return {
            path: Entry(path, mode, oid, sizes[oid])
            for path, mode, oid in parsed
        }

    def blob(self, oid: str) -> bytes:
        if oid not in self._blob_cache:
            self._blob_cache[oid] = self.run(["cat-file", "blob", oid])
        return self._blob_cache[oid]

    def object_file(self, revision: str, path: str) -> bytes:
        return self.run(["show", f"{revision}:{path}"])
