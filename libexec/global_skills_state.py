"""Closed owner state for the multi-repository global skill installer."""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
from dataclasses import dataclass
import errno
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
from typing import Callable, Iterator, Mapping, Sequence

from global_skills_inventory import Inventory


STATE_NAME = ".install-global-skills-state.json"
LOCK_NAME = ".install-global-skills.lock"
OWNER = "agentic-praxis-grimoire/install-global-skills"
SCHEMA_VERSION = 1
STATE_KEYS = {
    "agent",
    "created_containers",
    "generation",
    "installation_id",
    "links",
    "owner",
    "schema_version",
    "skill_hashes",
    "skills_root",
    "sources",
}
SOURCE_KEYS = {"repository_root", "skills_root"}
CONTAINER_KEYS = {"device", "inode", "mode", "owner", "path"}


class StateError(RuntimeError):
    """Installer state is missing, malformed, unsafe, or contended."""


@dataclass(frozen=True, slots=True)
class StateSource:
    repository_root: str
    skills_root: str


@dataclass(frozen=True, slots=True)
class ContainerIdentity:
    path: str
    device: int
    inode: int
    owner: int
    mode: int


@dataclass(frozen=True, slots=True)
class InstallState:
    agent: str
    skills_root: str
    sources: tuple[StateSource, ...]
    links: Mapping[str, str]
    skill_hashes: Mapping[str, str]
    created_containers: tuple[ContainerIdentity, ...]
    installation_id: str
    generation: int


@dataclass(frozen=True, slots=True)
class LoadedState:
    state: InstallState
    identity: tuple[int, int]
    payload: bytes


def safe_name(value: str) -> bool:
    return (
        bool(value)
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, member in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = member
    return value


def normalized_absolute(value: object, label: str) -> str:
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise StateError(f"installer state {label} is malformed")
    if os.path.normpath(value) != value:
        raise StateError(f"installer state {label} is not canonical")
    return value


def parse_sources(value: object) -> tuple[StateSource, ...]:
    if not isinstance(value, list) or not value:
        raise StateError("installer state sources are malformed")
    sources: list[StateSource] = []
    for member in value:
        if not isinstance(member, dict) or set(member) != SOURCE_KEYS:
            raise StateError("installer state source schema is malformed")
        sources.append(
            StateSource(
                normalized_absolute(member["repository_root"], "repository root"),
                normalized_absolute(member["skills_root"], "skill root"),
            )
        )
    if sources != sorted(sources, key=lambda item: item.repository_root):
        raise StateError("installer state sources are not canonical")
    if len({item.repository_root for item in sources}) != len(sources):
        raise StateError("installer state sources are duplicated")
    return tuple(sources)


def parse_mapping(value: object, label: str, digest: bool) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise StateError(f"installer state {label} are malformed")
    result: dict[str, str] = {}
    for name, member in value.items():
        if not isinstance(name, str) or not safe_name(name) or not isinstance(member, str):
            raise StateError(f"installer state {label} are malformed")
        if digest:
            if not re.fullmatch(r"[0-9a-f]{64}", member):
                raise StateError(f"installer state {label} are malformed")
        else:
            normalized_absolute(member, "link target")
        result[name] = member
    return dict(sorted(result.items()))


def parse_containers(
    value: object, expected_root: Path
) -> tuple[ContainerIdentity, ...]:
    if not isinstance(value, list):
        raise StateError("installer state containers are malformed")
    containers: list[ContainerIdentity] = []
    for member in value:
        if not isinstance(member, dict) or set(member) != CONTAINER_KEYS:
            raise StateError("installer state container schema is malformed")
        if any(
            type(member[key]) is not int or member[key] < 0
            for key in ("device", "inode", "mode", "owner")
        ):
            raise StateError("installer state container identity is malformed")
        containers.append(
            ContainerIdentity(
                normalized_absolute(member["path"], "container path"),
                member["device"],
                member["inode"],
                member["owner"],
                member["mode"],
            )
        )
    paths = [item.path for item in containers]
    if paths != sorted(set(paths), key=lambda item: (len(Path(item).parts), item)):
        raise StateError("installer state containers are not canonical")
    container_paths = tuple(Path(item) for item in paths)
    if container_paths and (
        container_paths[-1] != expected_root
        or any(
            child.parent != parent
            for parent, child in zip(
                container_paths, container_paths[1:]
            )
        )
    ):
        raise StateError(
            "installer state containers are outside the skills-root chain"
        )
    return tuple(containers)


def parse_state(payload: bytes, expected_agent: str, expected_root: Path) -> InstallState:
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise StateError("installer state is not valid JSON") from error
    if not isinstance(value, dict) or set(value) != STATE_KEYS:
        raise StateError("installer state schema is malformed or unsupported")
    if value["schema_version"] != SCHEMA_VERSION or value["owner"] != OWNER:
        raise StateError("installer state schema or owner is unsupported")
    if value["agent"] != expected_agent:
        raise StateError("installer state belongs to another agent")
    root = normalized_absolute(value["skills_root"], "skills root")
    if root != str(expected_root):
        raise StateError("installer state belongs to another destination")
    installation_id = value["installation_id"]
    generation = value["generation"]
    if (
        not isinstance(installation_id, str)
        or not re.fullmatch(r"[0-9a-f]{32}", installation_id)
        or type(generation) is not int
        or generation < 1
    ):
        raise StateError("installer state generation identity is malformed")
    links = parse_mapping(value["links"], "links", False)
    hashes = parse_mapping(value["skill_hashes"], "skill hashes", True)
    if set(links) != set(hashes):
        raise StateError("installer state link and hash sets differ")
    return InstallState(
        expected_agent,
        root,
        parse_sources(value["sources"]),
        links,
        hashes,
        parse_containers(value["created_containers"], expected_root),
        installation_id,
        generation,
    )


def serialize_state(value: InstallState) -> bytes:
    document = {
        "agent": value.agent,
        "created_containers": [
            {
                "device": item.device,
                "inode": item.inode,
                "mode": item.mode,
                "owner": item.owner,
                "path": item.path,
            }
            for item in value.created_containers
        ],
        "generation": value.generation,
        "installation_id": value.installation_id,
        "links": dict(sorted(value.links.items())),
        "owner": OWNER,
        "schema_version": SCHEMA_VERSION,
        "skill_hashes": dict(sorted(value.skill_hashes.items())),
        "skills_root": value.skills_root,
        "sources": [
            {
                "repository_root": item.repository_root,
                "skills_root": item.skills_root,
            }
            for item in value.sources
        ],
    }
    return (
        json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def from_inventory(
    agent: str,
    inventory: Inventory,
    containers: Sequence[ContainerIdentity],
    previous: InstallState | None = None,
) -> InstallState:
    return InstallState(
        agent,
        str(inventory.destination),
        tuple(
            StateSource(str(item.repository), str(item.skills_root))
            for item in inventory.sources
        ),
        {item.name: str(item.source) for item in inventory.skills},
        {item.name: item.skill_sha256 for item in inventory.skills},
        tuple(containers),
        previous.installation_id if previous else secrets.token_hex(16),
        previous.generation + 1 if previous else 1,
    )


def read_private_regular(
    path: Path,
    expected_identity: tuple[int, int] | None = None,
) -> tuple[os.stat_result, bytes]:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        )
    except FileNotFoundError:
        raise
    except OSError as error:
        raise StateError("installer state file is unsafe") from error
    try:
        before = os.fstat(descriptor)
        identity = (before.st_dev, before.st_ino)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or before.st_size == 0
            or before.st_size > 1024 * 1024
            or (expected_identity is not None and identity != expected_identity)
        ):
            raise StateError("installer state file is unsafe")
        remaining = before.st_size
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                raise StateError("installer state file is incomplete")
            if len(chunk) > remaining:
                raise StateError("installer state file grew while reading")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise StateError("installer state file grew while reading")
        after = os.fstat(descriptor)
        stable_fields = (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_uid",
            "st_gid",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
        if any(
            getattr(before, field) != getattr(after, field)
            for field in stable_fields
        ):
            raise StateError("installer state file changed while reading")
        payload = b"".join(chunks)
        if len(payload) != before.st_size:
            raise StateError("installer state file is incomplete")
        return before, payload
    finally:
        os.close(descriptor)


def load_state(root: Path, expected_agent: str) -> LoadedState | None:
    path = root / STATE_NAME
    try:
        metadata, payload = read_private_regular(path)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise StateError("installer state file is unsafe") from error
    current = path.lstat()
    identity = (metadata.st_dev, metadata.st_ino)
    if (current.st_dev, current.st_ino) != identity:
        raise StateError("installer state changed while reading")
    return LoadedState(
        parse_state(payload, expected_agent, root), identity, payload
    )


def path_identity(path: Path) -> tuple[int, int]:
    metadata = path.lstat()
    return metadata.st_dev, metadata.st_ino


def rename_directory_no_replace(source: Path, destination: Path) -> None:
    """Atomically install a staged directory without replacing another entry."""

    library = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if hasattr(library, "renameat2"):
        renameat2 = library.renameat2
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100,
            source_bytes,
            -100,
            destination_bytes,
            1,
        )
    elif hasattr(library, "renamex_np"):
        renamex = library.renamex_np
        renamex.argtypes = (
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renamex.restype = ctypes.c_int
        result = renamex(source_bytes, destination_bytes, 0x00000004)
    else:
        raise StateError(
            "atomic no-overwrite directory installation is unsupported"
        )
    if result == 0:
        return
    code = ctypes.get_errno()
    if code in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(
            code,
            "destination component appeared during creation",
            destination.name,
        )
    raise OSError(
        code,
        "destination component installation failed",
        destination.name,
    )


def created_container_identity(path: Path) -> ContainerIdentity:
    metadata = os.stat(path, follow_symlinks=False)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise StateError(
            f"created destination component is unsafe: {path.name}"
        )
    recorded = ContainerIdentity(
        str(path),
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_uid,
        stat.S_IMODE(metadata.st_mode),
    )
    descriptor = os.open(
        path,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        observed = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    path_observed = path.lstat()
    for current in (observed, path_observed):
        if (
            not stat.S_ISDIR(current.st_mode)
            or (
                current.st_dev,
                current.st_ino,
                current.st_uid,
                stat.S_IMODE(current.st_mode),
            )
            != (
                recorded.device,
                recorded.inode,
                recorded.owner,
                recorded.mode,
            )
        ):
            raise StateError(
                f"created destination component changed: {path.name}"
            )
    return recorded


def no_overwrite_move(
    source: Path,
    destination: Path,
    expected_identity: tuple[int, int],
) -> None:
    source_metadata = source.lstat()
    if (source_metadata.st_dev, source_metadata.st_ino) != expected_identity:
        raise StateError(f"path changed before backup: {source.name}")
    before_links = source_metadata.st_nlink
    linked = False
    try:
        os.link(source, destination, follow_symlinks=False)
        linked = True
        if (
            path_identity(destination) != expected_identity
            or path_identity(source) != expected_identity
        ):
            raise StateError(f"path changed during backup: {source.name}")
        source.unlink()
    except BaseException:
        try:
            if path_identity(destination) == expected_identity:
                if os.path.lexists(source):
                    current = source.lstat()
                    created = linked or (
                        (current.st_dev, current.st_ino)
                        == expected_identity
                        and current.st_nlink == before_links + 1
                    )
                    if created:
                        destination.unlink()
                elif linked:
                    os.link(
                        destination,
                        source,
                        follow_symlinks=False,
                    )
                    destination.unlink()
        except OSError:
            pass
        raise


def write_state(
    root: Path,
    value: InstallState,
    expected: LoadedState | None,
    validate: Callable[[], None] | None = None,
    committed: Callable[[], None] | None = None,
) -> str | None:
    descriptor, temporary_text = tempfile.mkstemp(prefix=f".{STATE_NAME}.", dir=root)
    temporary: Path | None = Path(temporary_text)
    backup: Path | None = None
    destination = root / STATE_NAME
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(serialize_state(value))
            stream.flush()
            os.fsync(stream.fileno())
        temporary_identity = path_identity(temporary)
        if expected is not None:
            backup = root / f".{STATE_NAME}.rollback-{os.getpid()}-{secrets.token_hex(8)}"
            no_overwrite_move(destination, backup, expected.identity)
            _, payload = read_private_regular(backup, expected.identity)
            if payload != expected.payload:
                if not os.path.lexists(destination):
                    no_overwrite_move(backup, destination, expected.identity)
                raise StateError("installer state changed during replacement")
        try:
            if validate is not None:
                validate()
            os.link(temporary, destination, follow_symlinks=False)
            if path_identity(destination) != temporary_identity:
                raise StateError("installer state changed during installation")
            temporary.unlink()
            temporary = None
        except BaseException:
            try:
                if path_identity(destination) == temporary_identity:
                    destination.unlink()
            except OSError:
                pass
            if backup is not None and not os.path.lexists(destination):
                no_overwrite_move(backup, destination, expected.identity)
            raise
        if committed is not None:
            committed()
        if backup is not None:
            try:
                backup.unlink()
            except OSError:
                return "committed state retained an owner-only rollback backup"
        return None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def destination_lock(root: Path) -> Iterator[None]:
    path = root / LOCK_NAME
    token = secrets.token_hex(16)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError as error:
        raise StateError("global skill installation is already active") from error
    metadata = path.lstat()
    identity = (metadata.st_dev, metadata.st_ino)
    owner = path / "owner"
    try:
        descriptor = os.open(owner, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(descriptor, (token + "\n").encode("ascii"))
        finally:
            os.close(descriptor)
        yield
    finally:
        try:
            current = path.lstat()
            if (
                stat.S_ISDIR(current.st_mode)
                and not path.is_symlink()
                and (current.st_dev, current.st_ino) == identity
                and owner.read_text(encoding="ascii") == token + "\n"
            ):
                owner.unlink()
                path.rmdir()
        except OSError:
            pass


@contextmanager
def apg_user_skills_guard(
    destination: Path,
    environment: Mapping[str, str],
) -> Iterator[None]:
    """Hold the separate APG lifecycle lock and refuse shared ownership."""

    home = environment.get("HOME")
    xdg = environment.get("XDG_STATE_HOME")
    if xdg:
        base = Path(xdg)
    elif home:
        base = Path(home) / ".local" / "state"
    else:
        yield
        return
    if not base.is_absolute():
        raise StateError("APG user-skill state root is not absolute")
    owner_root = Path(os.path.abspath(base / "agentic-praxis-grimoire"))
    state_path = owner_root / "user-skills-v1.json"
    lock_path = owner_root / "user-skills-v1.lock"
    if not os.path.lexists(lock_path):
        if os.path.lexists(state_path):
            raise StateError("APG user-skill owner lock is unsafe")
        yield
        return
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock_path, flags)
    except OSError as error:
        raise StateError("APG user-skill owner lock is unsafe") from error
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise StateError("APG user-skill owner lock is unsafe")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise StateError("APG user-skill owner is active") from error
        import apg_user_skills

        if os.path.lexists(state_path):
            try:
                owner_state = apg_user_skills.read_state(state_path)
            except apg_user_skills.ToolError as error:
                raise StateError(
                    "APG user-skill owner state is unsafe"
                ) from error
            if owner_state is None:
                raise StateError("APG user-skill owner state disappeared")
            recorded = Path(owner_state.skills_root)
            if recorded.resolve(strict=False) == destination.resolve(
                strict=False
            ):
                raise StateError(
                    "destination is owned by the separate apg-user-skills command"
                )
        yield
    finally:
        os.close(descriptor)


def check_apg_user_skills_owner(
    destination: Path,
    environment: Mapping[str, str],
) -> None:
    with apg_user_skills_guard(destination, environment):
        pass
