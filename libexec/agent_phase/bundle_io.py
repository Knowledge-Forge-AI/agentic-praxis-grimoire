"""Low-level I/O, atomic directory exchange, and filesystem security for dispatcher bundle.

Decomposed from bundle.py to ensure fail-closed security, single-pass capture,
and atomic exchange without rename-aside race windows.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import tomllib
from types import MappingProxyType
from typing import Any, Mapping
import uuid


MAX_MEMBER_BYTES = 256 * 1024
# Owners accepted only for a marker-verified immutable installed runtime: the
# root-owned, read-only Nix store. Home and override bundles never use this.
# Inside a Linux build sandbox the store owner may instead be unmapped; see
# _unmapped_owner.
TRUSTED_IMMUTABLE_OWNERS = (0,)
MAX_BUNDLE_GENERATION = (1 << 63) - 1
_READ_CHUNK = 64 * 1024


class BundleError(RuntimeError):
    """Base error for dispatcher bundle operations."""


class LegacyBundleError(BundleError):
    """Explicit error raised when a legacy four-file (generation <= 7) configuration is detected."""


class BundleTamperError(BundleError):
    """Manifest tampering or content hash mismatch detected."""


class BundleGenerationError(BundleError):
    """Bundle generation mismatch or partial generation detected."""


class BundleNotFoundError(BundleError):
    """Required bundle directory is absent."""


@dataclass(frozen=True)
class PhysicalIdentity:
    device: int
    inode: int
    mode: int
    owner: int
    links: int
    size: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> PhysicalIdentity:
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            mode=value.st_mode,
            owner=value.st_uid,
            links=value.st_nlink,
            size=value.st_size,
            modified_ns=value.st_mtime_ns,
            changed_ns=value.st_ctime_ns,
        )


def recursive_freeze(value: Any) -> Any:
    """Recursively freeze mappings, sequences, and sets into immutable types."""
    if isinstance(value, Mapping):
        return MappingProxyType({k: recursive_freeze(v) for k, v in value.items()})
    elif type(value) is list:
        return tuple(recursive_freeze(item) for item in value)
    elif type(value) is tuple:
        return tuple(recursive_freeze(item) for item in value)
    elif isinstance(value, (set, frozenset)):
        return frozenset(recursive_freeze(item) for item in value)
    return value


def directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def check_root_directory(path: Path) -> None:
    """Strictly verify that path exists and is a directory without following symlinks.

    Fails closed immediately on dangling symlinks, non-directory paths, or symlinked roots.
    """
    try:
        root_stat = os.lstat(path)
    except FileNotFoundError:
        raise BundleNotFoundError(f"bundle directory not found: {path}")
    except OSError as error:
        raise BundleError(f"cannot access bundle directory {path}: {error}") from error

    if stat.S_ISLNK(root_stat.st_mode):
        raise BundleError(f"bundle root directory is a symlink: {path}")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise BundleError(f"bundle root is not a directory: {path}")


def open_parent_no_follow(root: Path, relative: Path) -> tuple[int, str]:
    """Open root-relative parent directory strictly verifying no symlinks are traversed."""
    if relative.is_absolute() or not relative.parts or any(p in ("", ".", "..") for p in relative.parts):
        raise BundleError(f"invalid relative bundle path: {relative.as_posix()}")

    check_root_directory(root)
    root_stat = os.lstat(root)

    try:
        descriptor = os.open(root, directory_flags())
    except OSError as error:
        raise BundleError(f"cannot open root directory {root}: {error}") from error

    try:
        opened_root = os.fstat(descriptor)
        if (opened_root.st_dev, opened_root.st_ino) != (root_stat.st_dev, root_stat.st_ino):
            raise BundleError(f"root directory moved during access: {root}")

        for index, component in enumerate(relative.parts[:-1]):
            traversed = Path(*relative.parts[: index + 1])
            try:
                before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            except OSError as error:
                raise BundleError(f"cannot stat ancestor {traversed}: {error}") from error
            if stat.S_ISLNK(before.st_mode):
                raise BundleError(f"symlinked ancestor encountered: {traversed.as_posix()}")
            if not stat.S_ISDIR(before.st_mode):
                raise BundleError(f"ancestor is not a directory: {traversed.as_posix()}")
            try:
                next_descriptor = os.open(component, directory_flags(), dir_fd=descriptor)
            except OSError as error:
                raise BundleError(f"cannot open ancestor {traversed}: {error}") from error
            after = os.fstat(next_descriptor)
            if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
                os.close(next_descriptor)
                raise BundleError(f"ancestor moved during access: {traversed.as_posix()}")
            os.close(descriptor)
            descriptor = next_descriptor

        return descriptor, relative.name
    except BaseException:
        os.close(descriptor)
        raise


def installed_source_defaults(root: Path) -> bool:
    """Whether root is this marker-verified immutable runtime's own source defaults.

    Callers pass canonical paths; an unresolved alias compares unequal and fails closed.
    """
    runtime = Path(__file__).resolve().parents[2]
    if Path(root).absolute() != runtime / "common" / "dispatcher":
        return False
    from controller_generation import installed_runtime
    return installed_runtime(runtime) is not None


_PROC_RECORD_LIMIT = 64 * 1024  # uid_map holds at most 340 rows of ~33 bytes


def _read_proc(path: str) -> str:
    with open(path, encoding="ascii") as handle:
        text = handle.read(_PROC_RECORD_LIMIT + 1)
    if len(text) > _PROC_RECORD_LIMIT:
        raise ValueError(f"{path} exceeds its bounded size")  # never judge a truncated map
    return text


def _unmapped_owner(uid: int) -> bool:
    """Whether uid is the kernel overflow id standing in for an unmapped owner.

    In a Linux user namespace such as the Nix build sandbox, files whose owner
    has no mapping (host root owning /nix/store) report the overflow uid. It
    is admitted only when no uid_map range maps it, so a real account holding
    that uid never qualifies. Any unreadable or malformed record refuses.
    """
    if platform.system() != "Linux":
        return False
    try:
        overflow = int(_read_proc("/proc/sys/kernel/overflowuid"))
        ranges = [tuple(int(field) for field in line.split())
                  for line in _read_proc("/proc/self/uid_map").splitlines() if line.strip()]
    except (OSError, ValueError):
        return False
    if uid != overflow or not ranges or any(len(fields) != 3 for fields in ranges):
        return False
    return not any(inside <= uid < inside + count for inside, _outside, count in ranges)


def validate_regular_file(
    path: Path, value: os.stat_result, *, expected: PhysicalIdentity | None = None,
    immutable: bool = False,
) -> PhysicalIdentity:
    identity = PhysicalIdentity.from_stat(value)
    if expected is not None and identity != expected:
        raise BundleError(f"file {path.name} changed during capture")
    if stat.S_ISLNK(value.st_mode):
        raise BundleError(f"bundle member {path.name} is a symlink")
    if not stat.S_ISREG(value.st_mode):
        raise BundleError(f"bundle member {path.name} is not a regular file")
    # Store optimisation hard-links identical immutable files.
    if value.st_nlink != 1 and not immutable:
        raise BundleError(f"bundle member {path.name} has multiple hard links ({value.st_nlink})")
    expected_owner = os.geteuid()
    if value.st_uid != expected_owner and not (
            immutable and not value.st_mode & 0o222
            and (value.st_uid in TRUSTED_IMMUTABLE_OWNERS or _unmapped_owner(value.st_uid))):
        raise BundleError(
            f"bundle member {path.name} is not owned by effective account (uid {value.st_uid} != {expected_owner})"
        )
    return identity


def read_member_file_strict(root: Path, relative_name: str) -> tuple[bytes, str, int]:
    """Single-pass strict read and SHA-256 computation of a bundle member file.

    Guarantees no symlinks followed, single hard link, owner verification, and
    accurate size matching. Returns (raw_bytes, sha256_hex, size_bytes).
    """
    relative = Path(relative_name)
    immutable = installed_source_defaults(root)
    parent_descriptor, leaf = open_parent_no_follow(root, relative)
    descriptor: int | None = None
    try:
        try:
            stat_before = os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False)
        except OSError as error:
            raise BundleError(f"cannot stat bundle member {relative_name}: {error}") from error

        identity = validate_regular_file(relative, stat_before, immutable=immutable)
        if identity.size > MAX_MEMBER_BYTES:
            raise BundleError(f"bundle member {relative_name} exceeds {MAX_MEMBER_BYTES} bytes")

        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            descriptor = os.open(leaf, flags, dir_fd=parent_descriptor)
        except OSError as error:
            raise BundleError(f"cannot open bundle member {relative_name}: {error}") from error

        validate_regular_file(relative, os.fstat(descriptor), expected=identity, immutable=immutable)

        chunks: list[bytes] = []
        total = 0
        while total <= MAX_MEMBER_BYTES:
            try:
                chunk = os.read(descriptor, min(_READ_CHUNK, MAX_MEMBER_BYTES + 1 - total))
            except OSError as error:
                raise BundleError(f"cannot read bundle member {relative_name}: {error}") from error
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)

        if total > MAX_MEMBER_BYTES:
            raise BundleError(f"bundle member {relative_name} exceeds {MAX_MEMBER_BYTES} bytes")

        validate_regular_file(relative, os.fstat(descriptor), expected=identity, immutable=immutable)
        if total != identity.size:
            raise BundleError(f"bundle member {relative_name} changed size during capture")

        validate_regular_file(relative, os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False), expected=identity, immutable=immutable)
        raw_bytes = b"".join(chunks)
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        return raw_bytes, sha256, total
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)


def read_home_bundle_required(home: Path) -> bool:
    """Read dispatcher.bundle.required from <APGR_HOME>/config.toml if present.

    Fails closed if the required setting has a non-boolean type.
    """
    config_path = home / "config.toml"
    try:
        st = os.lstat(config_path)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise BundleError(f"cannot access {config_path}: {error}") from error

    if stat.S_ISLNK(st.st_mode):
        raise BundleError(f"configuration file is a symlink: {config_path}")
    if not stat.S_ISREG(st.st_mode):
        raise BundleError(f"configuration file is not a regular file: {config_path}")

    try:
        raw_bytes, _, _ = read_member_file_strict(home, "config.toml")
        data = tomllib.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise BundleError(f"unusable configuration file {config_path}: {error}") from error

    if not isinstance(data, Mapping):
        return False

    dispatcher = data.get("dispatcher")
    if dispatcher is None:
        return False
    if not isinstance(dispatcher, Mapping):
        raise BundleError("dispatcher configuration must be a table")

    bundle = dispatcher.get("bundle")
    if bundle is None:
        return False
    if not isinstance(bundle, Mapping):
        raise BundleError("dispatcher.bundle configuration must be a table")

    if "required" in bundle:
        val = bundle["required"]
        if type(val) is not bool:
            raise BundleError(
                f"invalid non-boolean dispatcher.bundle.required in {config_path}: {val!r}"
            )
        return val

    return False


def _darwin_exchange(dir1: Path, dir2: Path) -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
    except Exception as error:
        raise BundleError(f"failed to load libc on Darwin: {error}") from error

    if not hasattr(libc, "renamex_np"):
        raise BundleError(
            "atomic directory exchange overwrite is unsupported on this macOS version; "
            "overwrite rejected without absent target window"
        )

    renamex_np = libc.renamex_np
    renamex_np.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    renamex_np.restype = ctypes.c_int

    RENAME_SWAP = 0x00000002
    ret = renamex_np(str(dir1).encode("utf-8"), str(dir2).encode("utf-8"), RENAME_SWAP)
    if ret != 0:
        err = ctypes.get_errno()
        raise BundleError(
            f"atomic directory exchange overwrite failed ({os.strerror(err)}, errno={err}); "
            f"overwrite rejected without absent target window"
        )


def _linux_exchange(dir1: Path, dir2: Path) -> None:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
    except Exception as error:
        raise BundleError(f"failed to load libc on Linux: {error}") from error

    RENAME_EXCHANGE = 2
    AT_FDCWD = -100

    if hasattr(libc, "renameat2"):
        renameat2 = libc.renameat2
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        ret = renameat2(AT_FDCWD, str(dir1).encode("utf-8"), AT_FDCWD, str(dir2).encode("utf-8"), RENAME_EXCHANGE)
        if ret != 0:
            err = ctypes.get_errno()
            raise BundleError(
                f"atomic directory exchange overwrite failed ({os.strerror(err)}, errno={err}); "
                f"overwrite rejected without absent target window"
            )
        return

    # Syscall fallback
    if hasattr(libc, "syscall"):
        machine = platform.machine().lower()
        sys_renameat2 = 316 if machine in ("x86_64", "amd64") else (276 if machine in ("aarch64", "arm64") else None)
        if sys_renameat2 is not None:
            syscall = libc.syscall
            syscall.argtypes = [ctypes.c_long, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
            syscall.restype = ctypes.c_int
            ret = syscall(sys_renameat2, AT_FDCWD, str(dir1).encode("utf-8"), AT_FDCWD, str(dir2).encode("utf-8"), RENAME_EXCHANGE)
            if ret != 0:
                err = ctypes.get_errno()
                raise BundleError(
                    f"atomic directory exchange overwrite failed ({os.strerror(err)}, errno={err}); "
                    f"overwrite rejected without absent target window"
                )
            return

    raise BundleError(
        "atomic directory exchange overwrite is unsupported on this Linux environment; "
        "overwrite rejected without absent target window"
    )


def atomic_exchange_directories(dir1: Path, dir2: Path) -> None:
    """Atomically exchange two existing directories in a single atomic syscall.

    Supports Darwin (renamex_np with RENAME_SWAP) and Linux (renameat2 with RENAME_EXCHANGE).
    Rejects overwrite on unsupported platforms or filesystems with an explicit diagnostic.
    Guarantees no rename-aside window where target_dir is absent.
    """
    sys_name = platform.system()
    if sys_name == "Darwin":
        _darwin_exchange(dir1, dir2)
    elif sys_name == "Linux":
        _linux_exchange(dir1, dir2)
    else:
        raise BundleError(
            f"atomic directory exchange overwrite is unsupported on {sys_name}; "
            f"overwrite rejected without absent target window"
        )


LEGACY_MEMBERS = (
    "endpoints.toml",
    "routes.toml",
    "capabilities.toml",
    "policy.toml",
)


def check_legacy_roster(bundle_dir: Path, expected_generation: int = 9) -> None:
    """Detect if bundle_dir is a legacy four-file roster and raise explicit error."""
    try:
        st = os.lstat(bundle_dir)
    except FileNotFoundError:
        return
    except OSError as error:
        raise BundleError(f"cannot access bundle directory {bundle_dir}: {error}") from error

    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        return

    has_legacy_files = any((bundle_dir / name).is_file() for name in LEGACY_MEMBERS)
    missing_new_members = [
        name for name in ("models.toml", "workers.toml")
        if not (bundle_dir / name).is_file()
    ]

    if has_legacy_files and missing_new_members:
        raise LegacyBundleError(
            f"legacy four-file dispatcher configuration detected in {bundle_dir}; "
            f"migration to six-file bundle (generation {expected_generation}) required: "
            f"missing {', '.join(sorted(missing_new_members))}"
        )


def publish_bundle_io(
    target_dir: Path,
    members: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    """Stage, write, fsync, and atomically publish bundle member files to target_dir.

    Uses atomic exchange when target_dir exists, or atomic rename when it does not.
    Eliminates rename-aside absent target window.
    """
    parent_dir = target_dir.parent
    parent_dir.mkdir(parents=True, exist_ok=True)

    session_id = uuid.uuid4().hex[:8]
    staging_dir = parent_dir / f".tmp_{target_dir.name}_{os.getpid()}_{session_id}"

    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)
    # Bundles are private to the effective account that reads them back.
    staging_dir.mkdir(mode=0o700)

    try:
        for name, member in members.items():
            dest_file = staging_dir / name
            fd = os.open(dest_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(fd, member.raw)
                os.fsync(fd)
            finally:
                os.close(fd)

        manifest_raw = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
        manifest_file = staging_dir / "bundle.json"
        fd = os.open(manifest_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, manifest_raw)
            os.fsync(fd)
        finally:
            os.close(fd)

        target_exists = False
        try:
            st = os.lstat(target_dir)
            if stat.S_ISLNK(st.st_mode):
                raise BundleError(f"target directory is a symlink: {target_dir}")
            if not stat.S_ISDIR(st.st_mode):
                raise BundleError(f"target path is not a directory: {target_dir}")
            target_exists = True
        except FileNotFoundError:
            target_exists = False

        if not target_exists:
            os.replace(staging_dir, target_dir)
        else:
            atomic_exchange_directories(staging_dir, target_dir)
            shutil.rmtree(staging_dir, ignore_errors=True)
    except BaseException:
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        raise
