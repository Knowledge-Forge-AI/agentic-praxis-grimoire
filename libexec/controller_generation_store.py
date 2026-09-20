"""Owner-private Git-object generations and the short startup/cutover lock.

No existing generation is repaired, replaced or removed by materialization.
Only explicit GC may remove a previously published generation.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import time
from uuid import uuid4

SCHEMA_GENERATION = "controller-generation-v1"
SCHEMA_MANIFEST = "controller-generation-manifest-v1"
DEFAULT_LOCK_TIMEOUT = 10.0
MAX_FILES = 10000
MAX_SINGLE_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 100 * 1024 * 1024
ALLOWLIST = ("bin/", "libexec/", "common/dispatcher/", "common/workers/",
             "common/skills/agent-worker/", "common/mcp.toml", "codex/profiles/",
             "codex/config.d/170-subagents.toml", "codex/AGENTS.md",
             "claude/profiles/", "claude/model-catalog-v1.json", "claude/CLAUDE.md",
             "antigravity/profiles/", "antigravity/GEMINI.md", "README.md", "tools/add_dispatcher_roster_operator_directions.py")


class GenerationError(RuntimeError):
    pass
class StoreSecurityError(GenerationError):
    pass
class StoreLockTimeoutError(GenerationError):
    pass
class GenerationSecurityError(GenerationError):
    pass
class GenerationLimitError(GenerationSecurityError):
    pass
class GenerationValidationError(GenerationError):
    pass


def canonical_root(root: Path) -> Path:
    path = Path(root).resolve(strict=True)
    if not path.is_dir():
        raise StoreSecurityError("controller root is not a directory")
    return path


def canonical_root_sha256(root: Path) -> str:
    return hashlib.sha256(str(canonical_root(root)).encode()).hexdigest()


def resolve_controller_dir(root: Path, store: Path | None = None) -> Path:
    if store is not None:
        return Path(store).expanduser().absolute()
    base = Path(os.environ.get("AGENT_CENTRAL_GENERATION_STORE",
                               "~/.local/state/agent-central/generations")).expanduser().absolute()
    return base / canonical_root_sha256(root)


def no_symlinks(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise StoreSecurityError("store path is a symlink")
        if part.exists():
            info = part.stat()
            if info.st_uid not in {0, os.getuid()}:
                raise StoreSecurityError("store ancestor has another owner")
            if stat.S_ISDIR(info.st_mode) and info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
                raise StoreSecurityError("store ancestor is group/world writable")


def private_directory(path: Path) -> None:
    no_symlinks(path)
    if not path.exists():
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise StoreSecurityError("store directory is nonprivate or group/world writable")


def _outside_repositories(path: Path, root: Path) -> None:
    if path.is_relative_to(root):
        raise StoreSecurityError("generation store must be outside the controller")
    if any((p / ".git").exists() for p in (path, *path.parents)):
        raise StoreSecurityError("generation store must be outside product repositories")


@contextmanager
def coordinate(root: Path, store: Path | None = None, *, timeout: float | None = None):
    controller = resolve_controller_dir(root, store)
    _outside_repositories(controller, canonical_root(root))
    # Parent directories are never chmod'ed. The selected store itself is private.
    private_directory(controller)
    lock = controller / ".lock"
    no_symlinks(lock)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
            raise StoreSecurityError("unsafe cutover lock")
        deadline = time.monotonic() + (DEFAULT_LOCK_TIMEOUT if timeout is None else timeout)
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise StoreLockTimeoutError("Timed out acquiring cutover lock")
                time.sleep(0.02)
        if (lock.stat().st_dev, lock.stat().st_ino) != (info.st_dev, info.st_ino):
            raise StoreSecurityError("cutover lock was replaced")
        yield controller
    finally:
        os.close(fd)


def _git(root: Path, args: list[str], *, data: bytes | None = None) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1")
    result = subprocess.run(["git", "-C", str(root), *args], env=env,
                            input=data, capture_output=True, timeout=120, check=False)
    if result.returncode:
        raise GenerationError("generation Git object read failed")
    return result.stdout


def is_allowlisted(path: str) -> bool:
    return any((path.startswith(p) or path == p[:-1]) if p.endswith("/") else path == p for p in ALLOWLIST)


def check_path_hygiene(path: str) -> None:
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or parsed.as_posix() != path or ".." in parsed.parts:
        raise GenerationSecurityError("unsafe generation path")
    name = parsed.name.lower()
    if any(p in {"__pycache__", ".serena", ".pytest_cache", "usr", "user-canon"} for p in parsed.parts):
        raise GenerationSecurityError("Cache or user canon path forbidden")
    if name.endswith((".pyc", ".pyo")) or name == ".ds_store":
        raise GenerationSecurityError("Cache file forbidden")
    if name.startswith(".env") or name.endswith((".pem", ".key", ".p12")) or any(
            word in name for word in ("credential", "password", "secret", "token", "id_rsa")):
        raise GenerationSecurityError("Credential or secret file forbidden")
    if name in {"settings.json", "settings.local.json", "claude_desktop_config.json", "config.toml"}:
        raise GenerationSecurityError("Ambient settings file forbidden")


def _objects(root: Path, commit: str) -> dict:
    result = {}
    total = 0
    for entry in _git(root, ["ls-tree", "-r", "-l", "-z", "--full-tree", commit]).split(b"\0"):
        if not entry:
            continue
        header, raw = entry.split(b"\t", 1)
        path = raw.decode("utf-8")
        if not is_allowlisted(path):
            continue
        mode, kind, blob, raw_size = header.decode().split()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise GenerationSecurityError("Symlink or gitlink rejected")
        check_path_hygiene(path)
        size = int(raw_size)
        total += size
        if size > MAX_SINGLE_FILE_BYTES or total > MAX_TOTAL_BYTES or len(result) >= MAX_FILES:
            raise GenerationLimitError("generation size exceeds limit")
        result[path] = {"blob_sha": blob, "git_mode": mode, "size": size}
    # Check the complete size budget before asking Git for any blob bytes.
    batch = _git(root, ["cat-file", "--batch"],
                 data="".join(item["blob_sha"] + "\n" for item in result.values()).encode())
    cursor = 0
    for item in result.values():
        end = batch.index(b"\n", cursor)
        expected = f"{item['blob_sha']} blob {item['size']}".encode()
        if batch[cursor:end] != expected:
            raise GenerationValidationError("Git blob batch binding mismatch")
        cursor = end + 1
        data = batch[cursor:cursor + item["size"]]
        cursor += item["size"]
        if batch[cursor:cursor + 1] != b"\n":
            raise GenerationValidationError("Git blob batch length mismatch")
        cursor += 1
        item.update(sha256=hashlib.sha256(data).hexdigest(), data=data)
    if cursor != len(batch):
        raise GenerationValidationError("Git blob batch trailing bytes")
    return result


def _manifest(root: Path, commit: str, tree: str, objects: dict) -> bytes:
    entries = {p: {k: v for k, v in item.items() if k != "data"} for p, item in objects.items()}
    return json.dumps({"schema": SCHEMA_MANIFEST, "commit": commit, "tree": tree,
                       "controller_root": str(root), "entries": entries}, sort_keys=True).encode()


def _read_private(path: Path) -> bytes:
    no_symlinks(path)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 8 * 1024 * 1024):
        raise GenerationValidationError("unsafe generation metadata")
    return path.read_bytes()


def _write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def _safe_remove_tree(path: Path) -> None:
    """For owned staging/test directories only. GC validates its own exact root."""
    no_symlinks(path)
    for directory, dirs, _files in os.walk(path, followlinks=False):
        os.chmod(directory, 0o700)
    shutil.rmtree(path)


def _publish_payload(target: Path, objects: dict) -> None:
    temporary = target.with_name(".staging-" + uuid4().hex)
    temporary.mkdir(mode=0o700)
    try:
        for relative, entry in objects.items():
            path = temporary / relative
            path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            path.write_bytes(entry["data"])
            path.chmod(0o500 if entry["git_mode"] == "100755" else 0o400)
        for directory, _dirs, _files in os.walk(temporary, topdown=False):
            os.chmod(directory, 0o500)
        if os.path.lexists(target):
            raise GenerationValidationError("generation already exists")
        temporary.rename(target)
    finally:
        if temporary.exists():
            _safe_remove_tree(temporary)


def materialize(root: Path, controller_dir: Path, commit: str | None = None) -> dict:
    root = canonical_root(root)
    private_directory(controller_dir)
    _outside_repositories(controller_dir, root)
    commit = commit or _git(root, ["rev-parse", "HEAD"]).decode().strip()
    if not isinstance(commit, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit):
        raise GenerationSecurityError("invalid generation commit")
    for name in ("objects", "records", "manifests"):
        private_directory(controller_dir / name)
    target = controller_dir / "objects" / commit
    metadata = controller_dir / "records" / (commit + ".json")
    manifest = controller_dir / "manifests" / (commit + ".json")
    if any(os.path.lexists(p) for p in (target, metadata, manifest)):
        record = json.loads(_read_private(metadata))
        validate_generation(record, controller_dir)
        return record
    tree = _git(root, ["rev-parse", commit + "^{tree}"]).decode().strip()
    objects = _objects(root, commit)
    raw = _manifest(root, commit, tree, objects)
    record = {"schema": SCHEMA_GENERATION, "commit": commit, "tree": tree,
              "controller_id": canonical_root_sha256(root),
              "controller_root": str(root), "generation_root": str(target),
              "manifest_sha256": hashlib.sha256(raw).hexdigest(), "safety_established": True}
    _publish_payload(target, objects)
    _write_private(manifest, raw)
    _write_private(metadata, json.dumps(record, sort_keys=True).encode())
    validate_generation(record, controller_dir)
    return record


def _validate_payload(target: Path, objects: dict) -> None:
    expected_dirs = {"."}
    for relative in objects:
        expected_dirs.update(p.as_posix() for p in PurePosixPath(relative).parents)
    found_files, found_dirs = set(), set()
    for directory, dirs, files in os.walk(target, followlinks=False):
        path = Path(directory)
        relative = path.relative_to(target).as_posix()
        found_dirs.add(relative)
        info = path.lstat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o500:
            raise GenerationValidationError("generation directory mode mismatch")
        if relative not in expected_dirs or any((path / d).is_symlink() for d in dirs):
            raise GenerationValidationError("added directory or Symlink in generation")
        for name in files:
            item = path / name
            key = item.relative_to(target).as_posix()
            info = item.lstat()
            if key not in objects or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise GenerationValidationError("Unauthorized file or Symlink in generation")
            entry = objects[key]
            mode = 0o500 if entry["git_mode"] == "100755" else 0o400
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != mode:
                raise GenerationValidationError("Mode mismatch in generation")
            if info.st_size != entry["size"] or item.read_bytes() != entry["data"]:
                raise GenerationValidationError("Content or Size mismatch in generation")
            found_files.add(key)
    if found_files != set(objects) or found_dirs != expected_dirs:
        raise GenerationValidationError("generation membership mismatch")


def validate_generation(record: dict, controller_dir: Path) -> bool:
    if not isinstance(record, dict) or record.get("schema") != SCHEMA_GENERATION or record.get("safety_established") is not True:
        raise GenerationValidationError("invalid generation record")
    commit = record.get("commit")
    if not isinstance(commit, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit):
        raise GenerationValidationError("invalid generation commit")
    private_directory(controller_dir)
    for name in ("objects", "records", "manifests"):
        private_directory(controller_dir / name)
    target = controller_dir / "objects" / commit
    no_symlinks(target)
    if record.get("generation_root") != str(target) or not target.is_dir():
        raise GenerationValidationError("generation root missing or different")
    root = canonical_root(Path(record["controller_root"]))
    if record.get("controller_id") != canonical_root_sha256(root):
        raise GenerationValidationError("controller identity mismatch")
    if resolve_controller_dir(root) != controller_dir:
        # Explicit stores used by callers still bind through their record root.
        stored = json.loads(_read_private(controller_dir / "records" / (commit + ".json")))
        if stored.get("controller_root") != str(root):
            raise GenerationValidationError("controller identity mismatch")
    _outside_repositories(controller_dir, root)
    tree = _git(root, ["rev-parse", commit + "^{tree}"]).decode().strip()
    if record.get("tree") != tree:
        raise GenerationValidationError("Tree mismatch")
    objects = _objects(root, commit)
    raw = _read_private(controller_dir / "manifests" / (commit + ".json"))
    if hashlib.sha256(raw).hexdigest() != record.get("manifest_sha256") or raw != _manifest(root, commit, tree, objects):
        raise GenerationValidationError("Manifest hash mismatch")
    _validate_payload(target, objects)
    return True
