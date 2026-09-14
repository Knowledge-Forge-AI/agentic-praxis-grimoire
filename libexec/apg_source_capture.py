"""Capture one prospective APGR worktree into a clean disposable Git root.

The source repository is read only.  The destination receives one root commit
whose tree is the source's current tracked worktree plus explicitly reviewed
new paths.  No source Git objects, refs, index entries, or history are copied.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
from typing import Iterable, Mapping, NoReturn, Sequence
import zlib


COMMAND = "apg-capture-source"
SCHEMA_VERSION = 1
_CREDENTIAL_NAMES = {".env", ".env.local", "id_rsa", "id_ed25519"}
_RUNTIME_PARTS = {
    ".git",
    ".scratch",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}


class CaptureError(ValueError):
    """The source, selection, or destination is unsuitable for capture."""


@dataclass(frozen=True)
class CaptureResult:
    """The disposable repository and its source-bound manifest."""

    root: Path
    head: str
    tree: str
    manifest: dict[str, object]


@dataclass(frozen=True)
class _PathIdentity:
    """Descriptor identity observed for one source path."""

    path: str
    device: int
    inode: int
    mode: int


@dataclass(frozen=True)
class _Entry:
    path: str
    kind: str
    mode: int
    content: bytes
    baseline: bool
    identities: tuple[_PathIdentity, ...]

    @property
    def git_mode(self) -> bytes:
        if self.kind == "symlink":
            return b"120000"
        return b"100755" if self.mode & 0o111 else b"100644"

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class _State:
    head: str
    tree: str
    head_ref: bytes
    refs: bytes
    index: bytes | None
    selection: bytes
    entries: tuple[tuple[str, str, int, str], ...]
    root_identity: _PathIdentity
    path_identities: tuple[_PathIdentity, ...]


@dataclass(frozen=True)
class _ReadResult:
    """An entry, if present, and all identities observed while locating it."""

    entry: _Entry | None
    identities: tuple[_PathIdentity, ...]


def _fail(message: str) -> NoReturn:
    raise CaptureError(message)


def _git_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith("GIT_"):
            environment.pop(name)
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    if extra:
        environment.update(extra)
    return environment


def _git(
    root: Path,
    arguments: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    allow_failure: bool = False,
    environment: Mapping[str, str] | None = None,
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
                str(root),
                *arguments,
            ],
            input=input_bytes,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_git_environment(environment),
        )
    except OSError as error:
        _fail(f"Git could not be executed: {error.strerror}")
    if result.returncode and not allow_failure:
        detail = result.stderr.decode("utf-8", "replace").strip()
        _fail(f"Git operation failed: {detail or 'no diagnostic'}")
    return result


def _text_git(root: Path, arguments: Sequence[str], **kwargs: object) -> str:
    return _git(root, arguments, **kwargs).stdout.decode("utf-8", "strict").strip()


def _normal_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        _fail("reviewed path is malformed")
    if "\\" in value or value.startswith("/") or value.endswith("/"):
        _fail(f"reviewed path is unsafe: {value!r}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _fail(f"reviewed path is unsafe: {value!r}")
    normalized = PurePosixPath(value).as_posix()
    if normalized != value or any(part.startswith("-") for part in parts):
        _fail(f"reviewed path is non-canonical: {value!r}")
    return normalized


def _forbidden_path(path: str) -> str | None:
    parts = path.split("/")
    if any(part in _RUNTIME_PARTS for part in parts):
        return "runtime or scratch path"
    name = parts[-1]
    if name in _CREDENTIAL_NAMES or name.startswith(".env."):
        return "credential path"
    if name.endswith((".pem", ".key", ".p12", ".pfx")):
        return "credential path"
    if "credential" in name.lower() or "secret" in name.lower():
        return "credential path"
    return None


def _read_reviewed_manifest(value: Path | Mapping[str, object] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        parsed: object = value.get(
            "new_files", value.get("added_paths", value.get("paths", ()))
        )
    else:
        try:
            parsed = json.loads(value.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            _fail(f"reviewed manifest cannot be read: {error}")
    if isinstance(parsed, Mapping):
        parsed = parsed.get(
            "new_files", parsed.get("added_paths", parsed.get("paths", ()))
        )
    if not isinstance(parsed, list):
        _fail("reviewed manifest new_files must be a list")
    paths: list[str] = []
    for item in parsed:
        if isinstance(item, str):
            path = item
        elif isinstance(item, Mapping) and isinstance(item.get("path"), str):
            path = item["path"]
        else:
            _fail("reviewed manifest contains a malformed path")
        paths.append(_normal_path(path))
    if len(set(paths)) != len(paths):
        _fail("reviewed manifest contains duplicate paths")
    return tuple(sorted(paths))


def _source_root(requested: Path | str) -> tuple[Path, Path, str, str]:
    path = Path(requested)
    probe = _git(path, ["rev-parse", "--show-toplevel"], allow_failure=True)
    if probe.returncode:
        _fail("source is not a Git worktree")
    try:
        root = Path(os.fsdecode(probe.stdout.rstrip(b"\n"))).resolve(strict=True)
    except (OSError, UnicodeError) as error:
        _fail(f"source root cannot be resolved safely: {error}")
    if not root.is_dir() or _text_git(root, ["rev-parse", "--is-inside-work-tree"]) != "true":
        _fail("source must be a non-bare Git worktree")
    git_dir_value = _text_git(root, ["rev-parse", "--git-dir"])
    git_dir = Path(git_dir_value)
    if not git_dir.is_absolute():
        git_dir = root / git_dir
    try:
        git_dir = git_dir.resolve(strict=True)
    except OSError as error:
        _fail(f"source Git metadata cannot be resolved safely: {error}")
    head_result = _git(root, ["rev-parse", "HEAD^{commit}"], allow_failure=True)
    if head_result.returncode:
        _fail("source must have a committed HEAD")
    head = head_result.stdout.decode("ascii", "strict").strip()
    tree = _text_git(root, ["rev-parse", "HEAD^{tree}"])
    return root, git_dir, head, tree


def _validate_no_operation(git_dir: Path) -> None:
    if (git_dir / "index.lock").exists():
        _fail("source has an active Git index operation")
    markers = (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "rebase-apply",
        "rebase-merge",
        "sequencer",
    )
    if any((git_dir / marker).exists() for marker in markers):
        _fail("source has an active Git operation")


def _index_path(root: Path) -> Path:
    value = _text_git(root, ["rev-parse", "--git-path", "index"])
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path


def _baseline(root: Path) -> tuple[dict[str, bytes], bytes]:
    raw = _git(root, ["ls-tree", "-r", "-z", "--full-tree", "HEAD"]).stdout
    entries: dict[str, bytes] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, kind, oid = header.split(b" ")
        path = _normal_path(os.fsdecode(raw_path))
        reason = _forbidden_path(path)
        if reason:
            _fail(f"tracked path {path!r} is an unsafe {reason}")
        if mode == b"160000" or kind == b"commit":
            _fail(f"tracked gitlink is unsupported: {path}")
        if kind != b"blob" or mode not in {b"100644", b"100755", b"120000"}:
            _fail(f"tracked entry type is unsupported: {path}")
        entries[path] = mode
    return entries, raw


def _index_selection(root: Path, baseline: Mapping[str, bytes], reviewed: set[str]) -> bytes:
    raw = _git(root, ["ls-files", "-s", "-z"]).stdout
    index_paths: set[str] = set()
    for record in raw.split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, _oid, stage = header.split(b" ")
        path = _normal_path(os.fsdecode(raw_path))
        if stage != b"0":
            _fail(f"source has an unresolved index conflict: {path}")
        reason = _forbidden_path(path)
        if reason:
            _fail(f"indexed path {path!r} is an unsafe {reason}")
        if mode == b"160000":
            _fail(f"indexed gitlink is unsupported: {path}")
        index_paths.add(path)
    unreviewed = sorted(index_paths - set(baseline) - reviewed)
    if unreviewed:
        _fail(f"staged new path is not reviewed: {unreviewed[0]}")
    return raw


def _path_identity(path: str, metadata: os.stat_result) -> _PathIdentity:
    return _PathIdentity(
        path,
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IMODE(metadata.st_mode),
    )


def _root_identity(root: Path) -> _PathIdentity:
    try:
        metadata = root.lstat()
    except OSError as error:
        _fail(f"source root cannot be inspected safely: {error}")
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        _fail("source root must be a direct directory")
    return _path_identity("", metadata)


def _walk_parent(
    root: Path,
    path: str,
    root_identity: _PathIdentity,
) -> tuple[Path | None, tuple[_PathIdentity, ...]]:
    current = root
    parts = path.split("/")
    identities = [root_identity]
    for part in parts[:-1]:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return None, tuple(identities)
        except OSError as error:
            _fail(f"source path cannot be inspected: {path}: {error}")
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail(f"source path has an unsafe ancestor: {path}")
        identities.append(_path_identity("/".join(parts[: len(identities)]), metadata))
    return root.joinpath(*parts), tuple(identities)


def _read_entry(
    root: Path,
    path: str,
    baseline: bool,
    root_identity: _PathIdentity,
) -> _ReadResult:
    walked = _walk_parent(root, path, root_identity)
    target, ancestor_identities = walked
    if target is None:
        return _ReadResult(None, ancestor_identities)
    try:
        before = target.lstat()
    except FileNotFoundError:
        return _ReadResult(None, ancestor_identities)
    except OSError as error:
        _fail(f"source path cannot be inspected: {path}: {error}")
    if stat.S_ISLNK(before.st_mode):
        try:
            raw_target = os.fsencode(os.readlink(target))
            after = target.lstat()
        except OSError as error:
            _fail(f"source symlink cannot be read: {path}: {error}")
        if (
            before.st_dev,
            before.st_ino,
            before.st_mtime_ns,
            before.st_size,
            before.st_mode,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mtime_ns,
            after.st_size,
            after.st_mode,
        ):
            _fail(f"source changed while reading: {path}")
        identities = ancestor_identities + (_path_identity(path, after),)
        return _ReadResult(
            _Entry(path, "symlink", 0, raw_target, baseline, identities),
            identities,
        )
    if not stat.S_ISREG(before.st_mode):
        _fail(f"source entry type is unsupported: {path}")
    try:
        descriptor = os.open(target, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as error:
        _fail(f"source file cannot be opened safely: {path}: {error}")
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_mode,
        ) != (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_mode,
        ):
            _fail(f"source changed while opening: {path}")
        remaining = opened.st_size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                _fail(f"source file was truncated while reading: {path}")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail(f"source file grew while reading: {path}")
        content = b"".join(chunks)
        after = os.fstat(descriptor)
    except OSError as error:
        _fail(f"source file cannot be read safely: {path}: {error}")
    finally:
        os.close(descriptor)
    try:
        final = target.lstat()
    except OSError as error:
        _fail(f"source disappeared while reading: {path}: {error}")
    if (
        final.st_dev,
        final.st_ino,
        final.st_size,
        final.st_mtime_ns,
        final.st_mode,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_mode,
    ):
        _fail(f"source changed while reading: {path}")
    mode = stat.S_IMODE(after.st_mode)
    if mode & 0o7000:
        _fail(f"source file has unsupported special mode: {path}")
    identities = ancestor_identities + (_path_identity(path, after),)
    return _ReadResult(
        _Entry(path, "file", mode, content, baseline, identities),
        identities,
    )


def _observe(root: Path, git_dir: Path, reviewed: tuple[str, ...]) -> tuple[_State, tuple[_Entry, ...]]:
    root_identity = _root_identity(root)
    _validate_no_operation(git_dir)
    head = _text_git(root, ["rev-parse", "HEAD^{commit}"])
    tree = _text_git(root, ["rev-parse", "HEAD^{tree}"])
    head_ref = _git(root, ["symbolic-ref", "-q", "HEAD"], allow_failure=True).stdout
    refs = _git(root, ["for-each-ref", "--format=%(refname)%00%(objectname)", "refs"]).stdout
    index_file = _index_path(root)
    try:
        index = index_file.read_bytes()
    except FileNotFoundError:
        index = None
    except OSError as error:
        _fail(f"source index cannot be read: {error}")
    baseline, tree_selection = _baseline(root)
    index_selection = _index_selection(root, baseline, set(reviewed))
    specs: list[_Entry] = []
    path_identities: dict[str, _PathIdentity] = {"": root_identity}

    def record_identities(identities: tuple[_PathIdentity, ...]) -> None:
        for identity in identities:
            previous = path_identities.get(identity.path)
            if previous is not None and previous != identity:
                _fail(f"source changed while observing: {identity.path or '.'}")
            path_identities[identity.path] = identity

    for path in sorted(baseline):
        result = _read_entry(root, path, True, root_identity)
        record_identities(result.identities)
        if result.entry is not None:
            specs.append(result.entry)
    for path in reviewed:
        if path in baseline:
            _fail(f"reviewed path is already tracked: {path}")
        result = _read_entry(root, path, False, root_identity)
        record_identities(result.identities)
        if result.entry is None:
            _fail(f"reviewed path is absent: {path}")
        specs.append(result.entry)
        ignored = _git(root, ["check-ignore", "--no-index", "-q", "--", path], allow_failure=True)
        if ignored.returncode == 0:
            _fail(f"reviewed path is ignored: {path}")
    deleted = sorted(set(baseline) - {entry.path for entry in specs})
    selection = tree_selection + b"\0" + index_selection + b"\0" + "\n".join(reviewed).encode()
    signatures = tuple(
        (entry.path, entry.kind, entry.mode & 0o777, entry.digest)
        for entry in specs
    ) + tuple((path, "deleted", 0, "") for path in deleted)
    return (
        _State(
            head,
            tree,
            head_ref,
            refs,
            index,
            hashlib.sha256(selection).digest(),
            tuple(sorted(signatures)),
            root_identity,
            tuple(sorted(path_identities.values(), key=lambda identity: identity.path)),
        ),
        tuple(sorted(specs, key=lambda entry: entry.path)),
    )


def _allowed_alias(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        return False
    return (path, resolved) in {
        (Path("/tmp"), Path("/private/tmp")),
        (Path("/var"), Path("/private/var")),
    }


def _validate_output(output: Path, source: Path, git_dir: Path) -> Path:
    absolute = Path(os.path.abspath(output))
    if absolute.name == ".git":
        _fail("capture output cannot be Git metadata")
    if os.path.lexists(absolute):
        metadata = absolute.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            _fail("capture output must be a direct directory")
        if any(absolute.iterdir()):
            _fail("capture output must be absent or empty")
        _fail("capture output already exists")
    current = absolute.parent
    while True:
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            _fail("capture output parent must already exist")
        except OSError as error:
            _fail(f"capture output ancestry cannot be inspected: {error}")
        if stat.S_ISLNK(metadata.st_mode) and not _allowed_alias(current):
            _fail("capture output has a symlinked ancestor")
        if not stat.S_ISLNK(metadata.st_mode) and not stat.S_ISDIR(metadata.st_mode):
            _fail("capture output has a non-directory ancestor")
        if (current / ".git").exists() or (current / ".git").is_symlink():
            _fail("capture output is inside an active repository")
        if current == current.parent:
            break
        current = current.parent
    try:
        physical = absolute.resolve(strict=True) if os.path.lexists(absolute) else absolute.parent.resolve(strict=True) / absolute.name
        source_physical = source.resolve(strict=True)
        git_physical = git_dir.resolve(strict=True)
    except OSError as error:
        _fail(f"capture output cannot be resolved safely: {error}")
    if any(
        candidate == physical
        or candidate in physical.parents
        or physical in candidate.parents
        for candidate in (source_physical, git_physical)
    ):
        _fail("capture output overlaps source or Git metadata")
    return absolute


def _validate_manifest_output(
    manifest_output: Path,
    source: Path,
    git_dir: Path,
    capture_output: Path,
) -> Path:
    absolute = _validate_output(manifest_output, source, git_dir)
    try:
        sidecar_parent = absolute.parent.resolve(strict=True)
        capture_physical = capture_output.resolve(strict=False)
    except OSError as error:
        _fail(f"manifest output cannot be resolved safely: {error}")
    if (
        absolute == capture_output
        or capture_physical in absolute.parents
        or absolute in capture_physical.parents
        or sidecar_parent == capture_physical
    ):
        _fail("manifest output overlaps capture output")
    return absolute


def _mkdir_parent(root: Path, relative: str) -> Path:
    current = root
    for part in relative.split("/")[:-1]:
        current /= part
        if os.path.lexists(current):
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                _fail(f"capture destination has an unsafe ancestor: {relative}")
        else:
            current.mkdir(mode=0o755)
    return root / relative


def _write_entry(root: Path, entry: _Entry) -> None:
    destination = _mkdir_parent(root, entry.path)
    if os.path.lexists(destination):
        _fail(f"capture destination path collided: {entry.path}")
    if entry.kind == "symlink":
        try:
            os.symlink(os.fsdecode(entry.content), destination)
        except OSError as error:
            _fail(f"capture symlink cannot be created: {entry.path}: {error}")
        return
    try:
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            entry.mode & 0o777,
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(entry.content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as error:
        _fail(f"capture file cannot be written: {entry.path}: {error}")
    try:
        os.chmod(destination, entry.mode & 0o777, follow_symlinks=False)
    except OSError as error:
        _fail(f"capture file mode cannot be preserved: {entry.path}: {error}")


def _manifest_entries(entries: Iterable[_Entry]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for entry in entries:
        item: dict[str, object] = {
            "mode": entry.git_mode.decode("ascii"),
            "path": entry.path,
            "sha256": entry.digest,
            "type": entry.kind,
        }
        if entry.kind == "file":
            item["executable"] = bool(entry.mode & 0o111)
            item["permissions"] = format(entry.mode & 0o777, "04o")
        else:
            item["symlink_target"] = os.fsdecode(entry.content)
        result.append(item)
    return result


def _object_format(root: Path) -> str:
    value = _text_git(root, ["rev-parse", "--show-object-format"])
    if value not in {"sha1", "sha256"}:
        _fail(f"unsupported Git object format: {value}")
    return value


def _blob_oid(content: bytes, object_format: str) -> str:
    payload = b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    return hashlib.new(object_format, payload).hexdigest()


def _write_blob(root: Path, content: bytes, object_format: str) -> str:
    oid = _blob_oid(content, object_format)
    object_path = root / ".git" / "objects" / oid[:2] / oid[2:]
    if not object_path.exists():
        object_path.parent.mkdir(mode=0o755, exist_ok=True)
        try:
            with object_path.open("xb") as stream:
                stream.write(zlib.compress(b"blob " + str(len(content)).encode("ascii") + b"\0" + content))
        except FileExistsError:
            pass
    return oid


def _materialize(output: Path, entries: tuple[_Entry, ...]) -> tuple[str, str]:
    _git(output, ["init", "-q", "-b", "main"])
    object_format = _object_format(output)
    for entry in entries:
        _write_entry(output, entry)
    payload_parts: list[bytes] = []
    for entry in entries:
        oid = _write_blob(output, entry.content, object_format)
        payload_parts.append(entry.git_mode + b" " + oid.encode("ascii") + b"\t" + os.fsencode(entry.path) + b"\0")
    _git(output, ["update-index", "-z", "--index-info"], input_bytes=b"".join(payload_parts))
    tree = _text_git(output, ["write-tree"])
    identity = {
        "GIT_AUTHOR_NAME": "APGR Source Capture",
        "GIT_AUTHOR_EMAIL": "apgr-source-capture@example.invalid",
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
        "GIT_COMMITTER_NAME": "APGR Source Capture",
        "GIT_COMMITTER_EMAIL": "apgr-source-capture@example.invalid",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
    }
    head = _text_git(output, ["commit-tree", tree, "-m", "Capture prospective source"], environment=identity)
    _git(output, ["update-ref", "refs/heads/main", head])
    _git(output, ["symbolic-ref", "HEAD", "refs/heads/main"])
    _git(output, ["update-index", "--refresh"])
    if _git(output, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout:
        _fail("captured repository is not clean")
    return head, tree


def _remove_created(path: Path, identity: tuple[int, int]) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    except OSError:
        return
    if (metadata.st_dev, metadata.st_ino) != identity:
        return
    if stat.S_ISDIR(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode):
        shutil.rmtree(path)


def capture_source(
    source: Path | str,
    output: Path | str,
    *,
    reviewed_paths: Iterable[str] = (),
    reviewed_manifest: Path | Mapping[str, object] | None = None,
) -> CaptureResult:
    """Materialize the current prospective source into a clean Git repository."""

    explicit = tuple(sorted({_normal_path(path) for path in reviewed_paths}))
    manifest_paths = _read_reviewed_manifest(reviewed_manifest)
    if set(explicit) & set(manifest_paths):
        _fail("reviewed paths were supplied more than once")
    reviewed = tuple(sorted((*explicit, *manifest_paths)))
    for path in reviewed:
        reason = _forbidden_path(path)
        if reason:
            _fail(f"reviewed path {path!r} is an unsafe {reason}")
    root, git_dir, _head, _tree = _source_root(source)
    destination = _validate_output(Path(output), root, git_dir)
    created_identity: tuple[int, int] | None = None
    try:
        before, entries = _observe(root, git_dir, reviewed)
        try:
            destination.mkdir(mode=0o700)
        except OSError as error:
            _fail(f"capture output cannot be created: {error}")
        metadata = destination.lstat()
        created_identity = (metadata.st_dev, metadata.st_ino)
        captured_head, captured_tree = _materialize(destination, entries)
        after, final_entries = _observe(root, git_dir, reviewed)
        if before != after:
            _fail("source changed during capture")
        if tuple(_manifest_entries(entries)) != tuple(_manifest_entries(final_entries)):
            _fail("source content changed during capture")
        expected = {entry.path: entry for entry in final_entries}
        object_format = _object_format(destination)
        actual = _git(destination, ["ls-tree", "-r", "-z", "--full-tree", "HEAD"]).stdout
        actual_records = [record for record in actual.split(b"\0") if record]
        if len(actual_records) != len(expected):
            _fail("captured tree does not match the source manifest")
        for record in actual_records:
            header, raw_path = record.split(b"\t", 1)
            mode, kind, oid = header.split(b" ")
            path = os.fsdecode(raw_path)
            entry = expected.get(path)
            if entry is None or mode != entry.git_mode or kind != b"blob":
                _fail("captured tree does not match the source manifest")
            if oid.decode("ascii") != _blob_oid(entry.content, object_format):
                _fail("captured tree bytes do not match the source manifest")
            materialized = destination / path
            if entry.kind == "symlink":
                if not materialized.is_symlink() or os.fsencode(os.readlink(materialized)) != entry.content:
                    _fail("captured symlink bytes do not match the source manifest")
            else:
                metadata = materialized.lstat()
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or not stat.S_ISREG(metadata.st_mode)
                    or stat.S_IMODE(metadata.st_mode) != (entry.mode & 0o777)
                    or materialized.read_bytes() != entry.content
                ):
                    _fail("captured file bytes or mode do not match the source manifest")
        deleted = sorted(
            path for path, kind, _mode, _digest in before.entries if kind == "deleted"
        )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "format": "apg-source-capture/v1",
            "source": {
                "head": before.head,
                "tree": before.tree,
                "refs_sha256": hashlib.sha256(before.refs).hexdigest(),
                "index_sha256": hashlib.sha256(before.index or b"").hexdigest(),
                "selection_sha256": before.selection.hex(),
            },
            "entries": _manifest_entries(final_entries),
            "deleted": deleted,
            "reviewed_new_files": list(reviewed),
            "output": {"head": captured_head, "tree": captured_tree},
        }
        return CaptureResult(destination, captured_head, captured_tree, manifest)
    except BaseException:
        if created_identity is not None:
            _remove_created(destination, created_identity)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--new-file", action="append", default=[])
    parser.add_argument("--reviewed-manifest", "--manifest", dest="manifest")
    parser.add_argument("--manifest-output")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        source_root, git_dir, _head, _tree = _source_root(arguments.source)
        capture_output = _validate_output(Path(arguments.output), source_root, git_dir)
        manifest_output = (
            _validate_manifest_output(
                Path(arguments.manifest_output),
                source_root,
                git_dir,
                capture_output,
            )
            if arguments.manifest_output
            else None
        )
        result = capture_source(
            arguments.source,
            arguments.output,
            reviewed_paths=arguments.new_file,
            reviewed_manifest=Path(arguments.manifest) if arguments.manifest else None,
        )
        if manifest_output is not None:
            payload = json.dumps(result.manifest, sort_keys=True, indent=2).encode("utf-8") + b"\n"
            try:
                with manifest_output.open("xb") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                manifest_output.chmod(0o600)
            except OSError as error:
                _fail(f"manifest output cannot be written safely: {error}")
        if arguments.format == "json":
            print(json.dumps(result.manifest, sort_keys=True, separators=(",", ":")))
        else:
            print(f"PASS captured prospective source: {result.root} ({result.head})")
        return 0
    except CaptureError as error:
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
