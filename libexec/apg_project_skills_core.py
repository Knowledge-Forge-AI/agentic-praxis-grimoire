"""Manage local APG skill projections in an opted-in Git worktree."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import errno
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
from typing import Iterator, NoReturn, Sequence


COMMAND_NAME = "apg-project-skills"
FORMAT_VERSION = 1
STATE_KEYS = {
    "format_version",
    "apg_root",
    "target_root",
    "managed_skills",
    "created_containers",
    "exclude_separator_added",
}
STATE_RELATIVE_PATH = "info/apg-project-skills-v1"
EXCLUDE_RELATIVE_PATH = "info/exclude"
BEGIN_TOKEN = b"# BEGIN APG PROJECT SKILLS V1"
END_TOKEN = b"# END APG PROJECT SKILLS V1"
BEGIN_LINE = BEGIN_TOKEN + b"\n"
END_LINE = END_TOKEN + b"\n"
PROJECTION_PREFIX = "/.agents/skills/"
MAX_STATE_BYTES = 64 * 1024
MAX_EXCLUDE_BYTES = 4 * 1024 * 1024
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPECTED_SKILLS = (
    "composing-bounded-worker-assignments",
    "debugging-systematically",
    "designing-significant-changes",
    "implementing-with-test-discipline",
    "planning-repository-work",
    "reviewing-and-verifying-repository-work",
)
AUTHORIZED_CONTAINERS = (".agents", ".agents/skills")
RESTART_REMINDER = (
    "A full Codex application restart may be needed before added or removed "
    "project skills are reflected."
)
GIT_REPOSITORY_ENVIRONMENT = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_REPLACE_REF_BASE",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
}


class ToolError(Exception):
    """A bounded operational, state, or safety failure."""


@dataclass(frozen=True)
class LocalState:
    """Validated local ownership state."""

    apg_root: str
    target_root: str
    managed_skills: tuple[str, ...]
    created_containers: tuple[str, ...]
    exclude_separator_added: bool


@dataclass(frozen=True)
class ExcludeBlock:
    """Parsed APG block and unrelated surrounding bytes."""

    present: bool
    entries: tuple[str, ...]
    prefix: bytes
    suffix: bytes


@dataclass(frozen=True)
class FileSnapshot:
    """Original bytes and mode for rollback."""

    existed: bool
    content: bytes
    mode: int


@dataclass(frozen=True)
class TargetRepository:
    """Git-resolved target worktree paths."""

    root: Path
    state_path: Path
    exclude_path: Path


def fail(message: str) -> NoReturn:
    raise ToolError(message)


def run_git(
    directory: Path | str,
    arguments: Sequence[str],
    *,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if (
            name in GIT_REPOSITORY_ENVIRONMENT
            or name.startswith("GIT_CONFIG_KEY_")
            or name.startswith("GIT_CONFIG_VALUE_")
        ):
            environment.pop(name)
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
    except OSError as error:
        fail(f"Git could not be executed: {error.strerror}; install Git and retry")
    if result.returncode != 0 and not allow_failure:
        detail = result.stderr.strip() or "Git returned no diagnostic"
        fail(f"Git repository query failed: {detail}")
    return result


def physical_apg_root() -> Path:
    try:
        module = Path(__file__).resolve(strict=True)
    except OSError as error:
        fail(
            "canonical source resolution failed: "
            f"{error.strerror}; restore the APG executable and retry"
        )
    root = module.parent.parent
    executable = root / "bin" / COMMAND_NAME
    if not executable.is_file():
        fail(
            "canonical source resolution failed: APG executable is not in the "
            "expected bin directory; restore the installed checkout"
        )
    return root


def frontmatter_name(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        fail(
            f"canonical skill metadata is unreadable for {path.parent.name}: "
            f"{error}; restore the canonical leaf"
        )
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        fail(
            f"canonical skill metadata is malformed for {path.parent.name}: "
            "restore the frontmatter"
        )
    try:
        end = lines.index("---", 1)
    except ValueError:
        fail(
            f"canonical skill metadata is malformed for {path.parent.name}: "
            "restore the frontmatter terminator"
        )
    names = [
        line.removeprefix("name:").strip()
        for line in lines[1:end]
        if line.startswith("name:")
    ]
    if len(names) != 1 or not SKILL_NAME.fullmatch(names[0]):
        fail(
            f"canonical skill metadata is malformed for {path.parent.name}: "
            "restore one valid name field"
        )
    return names[0]


def canonical_skills(root: Path) -> dict[str, Path]:
    skills_root = root / "skills"
    if skills_root.is_symlink() or not skills_root.is_dir():
        fail("canonical skills directory is unsafe; restore the APG checkout")
    directory_names = sorted(
        entry.name
        for entry in skills_root.iterdir()
        if entry.is_dir() or entry.is_symlink()
    )
    if tuple(directory_names) != EXPECTED_SKILLS:
        fail(
            "canonical skill set differs from the accepted six leaves; "
            "reconcile APG before managing a target"
        )

    leaves: dict[str, Path] = {}
    for name in EXPECTED_SKILLS:
        if not SKILL_NAME.fullmatch(name):
            fail(f"canonical skill name is invalid: {name}")
        leaf = skills_root / name
        skill_file = leaf / "SKILL.md"
        if leaf.is_symlink() or not leaf.is_dir():
            fail(f"canonical skill leaf is unsafe for {name}; restore it")
        if skill_file.is_symlink() or not skill_file.is_file():
            fail(f"canonical SKILL.md is unsafe for {name}; restore it")
        if not os.access(skill_file, os.R_OK):
            fail(f"canonical SKILL.md is unreadable for {name}; restore access")
        if frontmatter_name(skill_file) != name:
            fail(
                f"canonical frontmatter name disagrees for {name}; "
                "restore the accepted leaf"
            )
        leaves[name] = leaf.resolve(strict=True)
    return leaves


def git_resolved_path(root: Path, relative: str) -> Path:
    value = run_git(root, ["rev-parse", "--git-path", relative]).stdout.strip()
    if not value:
        fail(f"Git returned an empty path for {relative}; repair the repository")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return Path(os.path.abspath(path))


def resolve_target(requested: str) -> TargetRepository:
    candidate = Path(requested)
    result = run_git(
        candidate,
        ["rev-parse", "--show-toplevel"],
        allow_failure=True,
    )
    if result.returncode != 0:
        fail(
            "target is not inside a Git worktree; select an initialized "
            "non-bare repository with --repo"
        )
    try:
        root = Path(result.stdout.strip()).resolve(strict=True)
    except OSError as error:
        fail(
            f"target worktree root is unreadable: {error.strerror}; "
            "repair the repository and retry"
        )
    if not root.is_dir():
        fail("target worktree root is not a directory; repair it and retry")
    inside = run_git(root, ["rev-parse", "--is-inside-work-tree"]).stdout.strip()
    bare = run_git(root, ["rev-parse", "--is-bare-repository"]).stdout.strip()
    if inside != "true" or bare != "false":
        fail("target must be a non-bare Git worktree; select another repository")

    state_path = git_resolved_path(root, STATE_RELATIVE_PATH)
    exclude_path = git_resolved_path(root, EXCLUDE_RELATIVE_PATH)
    for label, path in (("state", state_path), ("exclude", exclude_path)):
        if path.parent.is_symlink() or not path.parent.is_dir():
            fail(
                f"Git-local {label} parent is unsafe; repair Git metadata "
                "before retrying"
            )
    return TargetRepository(root, state_path, exclude_path)


def relative_projection(skill: str) -> str:
    return f".agents/skills/{skill}"


def projection_path(repository: TargetRepository, skill: str) -> Path:
    return repository.root / relative_projection(skill)


def is_tracked(repository: TargetRepository, skill: str) -> bool:
    result = run_git(
        repository.root,
        ["ls-files", "--error-unmatch", "--", relative_projection(skill)],
        allow_failure=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    fail(
        f"tracked-path query failed for {skill}; inspect the target repository "
        "before retrying"
    )


def managed_status(repository: TargetRepository, skills: Sequence[str]) -> str:
    if not skills:
        return ""
    result = run_git(
        repository.root,
        [
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            *(relative_projection(skill) for skill in skills),
        ],
    )
    return result.stdout


def validate_projection_parents(repository: TargetRepository) -> None:
    for relative in AUTHORIZED_CONTAINERS:
        path = repository.root / relative
        if not os.path.lexists(path):
            continue
        if path.is_symlink() or not path.is_dir():
            fail(
                f"projection parent {relative} is unsafe; replace it with an "
                "ordinary directory or select another target"
            )


def require_exact_link(
    repository: TargetRepository,
    canonical: dict[str, Path],
    skill: str,
    *,
    missing_context: str,
) -> None:
    link = projection_path(repository, skill)
    if not os.path.lexists(link):
        fail(
            f"{missing_context} projection is missing for {skill}; restore the "
            "exact link before retrying"
        )
    if not link.is_symlink():
        fail(
            f"conflicting path for {skill} is not a symbolic link; preserve it "
            "and choose a different action"
        )
    try:
        resolved = link.resolve(strict=True)
    except OSError:
        fail(
            f"projection for {skill} is broken and does not resolve to the exact "
            "canonical leaf; restore it before retrying"
        )
    if resolved != canonical[skill]:
        fail(
            f"projection for {skill} does not resolve to the exact canonical "
            "leaf; restore or remove the unmanaged link"
        )
    skill_file = link / "SKILL.md"
    if not skill_file.is_file() or not os.access(skill_file, os.R_OK):
        fail(
            f"projected SKILL.md is unreadable for {skill}; restore canonical "
            "access before retrying"
        )
    if frontmatter_name(skill_file) != skill:
        fail(
            f"projected frontmatter name disagrees for {skill}; restore the "
            "exact canonical link"
        )


def create_projection_parents(repository: TargetRepository) -> list[str]:
    created: list[str] = []
    for relative in AUTHORIZED_CONTAINERS:
        path = repository.root / relative
        if os.path.lexists(path):
            if path.is_symlink() or not path.is_dir():
                fail(
                    f"projection parent {relative} became unsafe; inspect the "
                    "target before retrying"
                )
            continue
        try:
            path.mkdir(mode=0o755)
            path.chmod(0o755)
        except OSError as error:
            fail(
                f"could not create projection parent {relative}: "
                f"{error.strerror}; inspect target permissions"
            )
        created.append(relative)
    return created


def parse_state(content: bytes, apg_root: Path, target_root: Path) -> LocalState:
    if not content:
        fail(
            "local state is empty, possibly after an interrupted mutation; "
            "inspect the target Git metadata before retrying"
        )
    if len(content) > MAX_STATE_BYTES:
        fail("local state is oversized; inspect and repair it before retrying")
    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, member in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON member: {key}")
            value[key] = member
        return value

    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=unique_object,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError):
        fail("local state is malformed; inspect and repair it before retrying")
    if not isinstance(value, dict) or set(value) != STATE_KEYS:
        fail(
            "local state schema is malformed or unsupported; inspect and "
            "repair it before retrying"
        )
    if type(value["format_version"]) is not int or value["format_version"] != 1:
        fail(
            "local state format version is unsupported; use a compatible APG "
            "checkout or uninstall with the original version"
        )
    recorded_root = value["apg_root"]
    if not isinstance(recorded_root, str) or not Path(recorded_root).is_absolute():
        fail("local state APG root is malformed; inspect it before retrying")
    if recorded_root != str(apg_root):
        fail(
            "local state belongs to a different APG root; restore that checkout "
            "and uninstall before moving or reinstalling"
        )
    recorded_target = value["target_root"]
    if not isinstance(recorded_target, str) or not Path(recorded_target).is_absolute():
        fail("local state target root is malformed; inspect it before retrying")
    if recorded_target != str(target_root):
        fail(
            "local state belongs to a different target worktree that shares "
            "Git metadata; run from the recorded target to check or uninstall"
        )

    managed = value["managed_skills"]
    if (
        not isinstance(managed, list)
        or not managed
        or any(not isinstance(name, str) for name in managed)
        or managed != sorted(set(managed))
        or any(name not in EXPECTED_SKILLS for name in managed)
    ):
        fail("local state managed skill list is malformed; inspect it before retrying")

    containers = value["created_containers"]
    valid_container_sets = (
        [],
        [".agents/skills"],
        [".agents", ".agents/skills"],
    )
    if not isinstance(containers, list) or containers not in valid_container_sets:
        fail(
            "local state container ownership is malformed; inspect it before "
            "retrying"
        )
    separator = value["exclude_separator_added"]
    if type(separator) is not bool:
        fail("local state exclude metadata is malformed; inspect it before retrying")
    return LocalState(
        recorded_root,
        recorded_target,
        tuple(managed),
        tuple(containers),
        separator,
    )


def serialize_state(state: LocalState) -> bytes:
    value = {
        "format_version": FORMAT_VERSION,
        "apg_root": state.apg_root,
        "target_root": state.target_root,
        "managed_skills": list(state.managed_skills),
        "created_containers": list(state.created_containers),
        "exclude_separator_added": state.exclude_separator_added,
    }
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def regular_file_bytes(path: Path, *, maximum: int, label: str) -> FileSnapshot:
    if not os.path.lexists(path):
        return FileSnapshot(False, b"", 0o600)
    try:
        metadata = path.lstat()
    except OSError as error:
        fail(f"Git-local {label} could not be inspected: {error.strerror}")
    if not stat.S_ISREG(metadata.st_mode):
        fail(
            f"Git-local {label} is not an ordinary file; restore safe Git "
            "metadata before retrying"
        )
    if metadata.st_size > maximum:
        fail(f"Git-local {label} is oversized; inspect it before retrying")
    try:
        content = path.read_bytes()
    except OSError as error:
        fail(f"Git-local {label} could not be read: {error.strerror}")
    return FileSnapshot(True, content, stat.S_IMODE(metadata.st_mode))


def read_state(path: Path, apg_root: Path, target_root: Path) -> LocalState | None:
    snapshot = regular_file_bytes(path, maximum=MAX_STATE_BYTES, label="state")
    if not snapshot.existed:
        return None
    if snapshot.mode != 0o600:
        fail(
            "local state permissions are unsafe; set mode 0600 after inspection "
            "and retry"
        )
    return parse_state(snapshot.content, apg_root, target_root)


def read_locked_state(
    descriptor: int,
    *,
    created_placeholder: bool,
    apg_root: Path,
    target_root: Path,
) -> LocalState | None:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        fail("local state lock inode is unsafe; inspect Git metadata")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        fail("local state permissions are unsafe; inspect it before retrying")
    os.lseek(descriptor, 0, os.SEEK_SET)
    content = os.read(descriptor, MAX_STATE_BYTES + 1)
    if created_placeholder:
        if content:
            fail("new local state lock was changed concurrently; inspect it")
        return None
    return parse_state(content, apg_root, target_root)


def parse_exclude(content: bytes) -> ExcludeBlock:
    if len(content) > MAX_EXCLUDE_BYTES:
        fail("Git exclude file is oversized; inspect it before retrying")
    lines = content.splitlines(keepends=True)
    starts: list[int] = []
    ends: list[int] = []
    offset = 0
    for line in lines:
        if line == BEGIN_LINE:
            starts.append(offset)
        if line == END_LINE:
            ends.append(offset)
        offset += len(line)
    if BEGIN_TOKEN in content and content.count(BEGIN_TOKEN) != len(starts):
        fail("APG exclude block has a malformed begin marker; repair it first")
    if END_TOKEN in content and content.count(END_TOKEN) != len(ends):
        fail("APG exclude block has a malformed end marker; repair it first")
    if not starts and not ends:
        return ExcludeBlock(False, (), content, b"")
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        fail("APG exclude block is duplicate or malformed; repair it first")

    start = starts[0]
    end = ends[0]
    body = content[start + len(BEGIN_LINE) : end]
    body_lines = body.splitlines(keepends=True)
    entries: list[str] = []
    for line in body_lines:
        if not line.endswith(b"\n"):
            fail("APG exclude block body is malformed; repair it first")
        try:
            text = line[:-1].decode("ascii")
        except UnicodeError:
            fail("APG exclude block body is malformed; repair it first")
        if not text.startswith(PROJECTION_PREFIX):
            fail("APG exclude block contains an unsafe path; repair it first")
        name = text.removeprefix(PROJECTION_PREFIX)
        if name not in EXPECTED_SKILLS:
            fail("APG exclude block contains an unknown path; repair it first")
        entries.append(name)
    if entries != sorted(set(entries)):
        fail("APG exclude block entries are duplicate or unsorted; repair it first")
    return ExcludeBlock(
        True,
        tuple(entries),
        content[:start],
        content[end + len(END_LINE) :],
    )


def build_exclude_block(skills: Sequence[str]) -> bytes:
    paths = b"".join(
        f"{PROJECTION_PREFIX}{skill}\n".encode("ascii") for skill in skills
    )
    return BEGIN_LINE + paths + END_LINE


def updated_exclude(
    snapshot: FileSnapshot,
    parsed: ExcludeBlock,
    skills: Sequence[str],
    separator_added: bool,
) -> tuple[bytes, bool]:
    if skills:
        block = build_exclude_block(skills)
        if parsed.present:
            return parsed.prefix + block + parsed.suffix, separator_added
        prefix = snapshot.content
        added = False
        if prefix and not prefix.endswith(b"\n"):
            prefix += b"\n"
            added = True
        return prefix + block, added

    if not parsed.present:
        return snapshot.content, separator_added
    prefix = parsed.prefix
    if separator_added and not parsed.suffix and prefix.endswith(b"\n"):
        prefix = prefix[:-1]
    return prefix + parsed.suffix, False


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_replace(path: Path, content: bytes, mode: int) -> None:
    if os.path.lexists(path):
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            fail(f"refusing atomic replacement of unsafe path {path.name}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        descriptor = -1
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if os.path.lexists(temporary):
            temporary.unlink()


def restore_snapshot(path: Path, snapshot: FileSnapshot) -> None:
    if snapshot.existed:
        atomic_replace(path, snapshot.content, snapshot.mode)
        return
    if os.path.lexists(path):
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            fail(f"rollback found an unsafe replacement at {path.name}")
        path.unlink()
        fsync_directory(path.parent)


def inode_matches(path: Path, descriptor: int) -> bool:
    try:
        path_metadata = path.lstat()
        descriptor_metadata = os.fstat(descriptor)
    except OSError:
        return False
    return (
        stat.S_ISREG(path_metadata.st_mode)
        and path_metadata.st_dev == descriptor_metadata.st_dev
        and path_metadata.st_ino == descriptor_metadata.st_ino
    )


@contextmanager
def mutation_lock(path: Path) -> Iterator[tuple[int, bool]]:
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    flags = os.O_RDWR | no_follow
    created = False
    try:
        descriptor = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
        os.fchmod(descriptor, 0o600)
        created = True
    except FileExistsError:
        try:
            descriptor = os.open(path, flags)
        except OSError as error:
            fail(
                "local state lock path is unsafe: "
                f"{error.strerror}; inspect Git metadata"
            )
    except OSError as error:
        fail(f"local state lock could not be created: {error.strerror}")

    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail(
                "a project-skill mutation lock is active; wait for it to finish "
                "or inspect a stale lock state"
            )
        yield descriptor, created
    finally:
        try:
            if (
                created
                and inode_matches(path, descriptor)
                and os.fstat(descriptor).st_size == 0
            ):
                path.unlink()
                fsync_directory(path.parent)
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)


def validate_state_and_exclude(
    state: LocalState | None,
    exclude: ExcludeBlock,
) -> None:
    if state is None:
        if exclude.present:
            fail(
                "APG exclude block exists without valid ownership state; inspect "
                "and repair the interrupted or manual state"
            )
        return
    if not exclude.present:
        fail(
            "valid ownership state has no APG exclude block; restore the exact "
            "block before retrying"
        )
    if exclude.entries != state.managed_skills:
        fail(
            "APG exclude block disagrees with ownership state; restore exact "
            "managed paths before retrying"
        )


def validate_owned_projections(
    repository: TargetRepository,
    canonical: dict[str, Path],
    state: LocalState,
) -> None:
    validate_projection_parents(repository)
    for skill in state.managed_skills:
        if is_tracked(repository, skill):
            fail(
                f"managed projection path is tracked for {skill}; restore the "
                "tracked repository state before retrying"
            )
        require_exact_link(
            repository,
            canonical,
            skill,
            missing_context="managed",
        )
