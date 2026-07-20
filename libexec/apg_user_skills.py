"""Safe user-scoped APG skill lifecycle from verified public sources."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Iterator, NoReturn, Sequence

from apg_skill_library_check import check_library
import apg_public_release as public_release


COMMAND = "apg-user-skills"
SCHEMA_VERSION = 1
SKILLS = (
    "composing-bounded-worker-assignments",
    "debugging-systematically",
    "designing-significant-changes",
    "implementing-with-test-discipline",
    "planning-repository-work",
    "reviewing-and-verifying-repository-work",
)
STATE_KEYS = {
    "created_containers",
    "current_source",
    "managed_skills",
    "previous_source",
    "schema_version",
    "skills_root",
}
SOURCE_KEYS = {"commit", "path", "skill_hashes", "tag", "tree", "version"}
RESTART_REMINDER = (
    "Codex normally detects skill changes automatically. If the change does "
    "not appear, fully restart Codex."
)
PUBLIC_V01_COMMIT = "f53342d4e5079ff2a73c0a107777a92910d016a1"
PUBLIC_V01_TREE = "0163a2931e65eb822f44a41d6cd0105e671015ad"
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


class ToolError(Exception):
    """A bounded safety, source, state, or ownership failure."""


@dataclass(frozen=True)
class SourceIdentity:
    """One verified immutable public-source identity."""

    path: str
    version: str
    tag: str
    commit: str
    tree: str
    skill_hashes: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "commit": self.commit,
            "path": self.path,
            "skill_hashes": dict(self.skill_hashes),
            "tag": self.tag,
            "tree": self.tree,
            "version": self.version,
        }


@dataclass(frozen=True)
class State:
    """Strict version-1 user ownership state."""

    skills_root: str
    current_source: SourceIdentity
    previous_source: SourceIdentity | None
    managed_skills: tuple[str, ...]
    created_containers: tuple["ContainerIdentity", ...]


@dataclass(frozen=True)
class ContainerIdentity:
    """Identity of one directory created solely for the managed links."""

    path: str
    device: int
    inode: int
    owner: int
    mode: int

    def as_dict(self) -> dict[str, object]:
        return {
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
            "owner": self.owner,
            "path": self.path,
        }


def fail(message: str) -> NoReturn:
    raise ToolError(message)


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


def text_git(repository: Path, arguments: Sequence[str], *, allow_failure: bool = False) -> str:
    result = run_git(repository, arguments, allow_failure=allow_failure)
    return result.stdout.decode("utf-8", "strict").strip()


def frontmatter_name(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        fail(f"source skill is unreadable: {path.parent.name}")
    if not lines or lines[0] != "---":
        fail(f"source skill frontmatter is malformed: {path.parent.name}")
    try:
        end = lines.index("---", 1)
    except ValueError:
        fail(f"source skill frontmatter is unterminated: {path.parent.name}")
    names = [line.removeprefix("name:").strip() for line in lines[1:end] if line.startswith("name:")]
    if names != [path.parent.name]:
        fail(f"source skill name is malformed or mismatched: {path.parent.name}")
    return names[0]


def verify_source(requested: str | Path) -> SourceIdentity:
    candidate = Path(requested)
    result = run_git(candidate, ["rev-parse", "--show-toplevel"], allow_failure=True)
    if result.returncode:
        fail("source is not a Git worktree")
    try:
        root = Path(result.stdout.decode().strip()).resolve(strict=True)
    except (OSError, UnicodeError):
        fail("source root cannot be resolved safely")
    if Path(os.path.abspath(candidate)) != root:
        try:
            if candidate.resolve(strict=True) != root:
                fail("source must name the Git worktree root")
        except OSError:
            fail("source root cannot be resolved safely")
    if run_git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout:
        fail("source repository must be clean")
    if run_git(root, ["ls-files", "-z", "--", "private"]).stdout:
        fail("source is not a public release because it tracks private/")
    commit = text_git(root, ["rev-parse", "HEAD^{commit}"])
    tree = text_git(root, ["rev-parse", "HEAD^{tree}"])
    try:
        release_repository = public_release.resolve_repository(root, "source")
        lineage = public_release.verify_public_release_lineage(
            release_repository,
            accepted_commit=PUBLIC_V01_COMMIT,
            accepted_tree=PUBLIC_V01_TREE,
        )
    except public_release.ToolError as error:
        fail(f"source public release lineage is invalid: {error}")
    current_release = lineage[-1]
    library_result = check_library(root)
    if not library_result.passed:
        diagnostic = library_result.diagnostics[0]
        fail(f"source APG skill library is invalid: {diagnostic.code} {diagnostic.path}")
    if commit != PUBLIC_V01_COMMIT:
        try:
            policy = public_release.load_policy(release_repository)
            release_entries = public_release.tree_entries(
                release_repository, excluded_prefix=b"private/"
            )
            public_release.validate_critical(release_entries, policy)
            public_release.validate_public_symlinks(release_repository, release_entries)
        except public_release.ToolError as error:
            fail(f"source public release policy is invalid: {error}")
    directory_names: list[str] = []
    skills_root = root / "skills"
    if skills_root.is_symlink() or not skills_root.is_dir():
        fail("source skills directory is missing or unsafe")
    for entry in skills_root.iterdir():
        if entry.is_dir() or entry.is_symlink():
            directory_names.append(entry.name)
    if tuple(sorted(directory_names)) != SKILLS:
        fail("source does not contain exactly the six canonical skills")
    hashes: list[tuple[str, str]] = []
    for name in SKILLS:
        leaf = skills_root / name
        skill_file = leaf / "SKILL.md"
        if leaf.is_symlink() or not leaf.is_dir() or skill_file.is_symlink() or not skill_file.is_file():
            fail(f"source canonical skill path is unsafe: {name}")
        frontmatter_name(skill_file)
        content = run_git(root, ["show", f"{commit}:skills/{name}/SKILL.md"], allow_failure=True)
        if content.returncode:
            fail(f"source canonical skill is not committed: {name}")
        if content.stdout != skill_file.read_bytes():
            fail(f"source canonical skill differs from committed bytes: {name}")
        hashes.append((name, hashlib.sha256(content.stdout).hexdigest()))
    tag = current_release.tag
    version = current_release.version
    return SourceIdentity(str(root), version, tag, commit, tree, tuple(hashes))


def state_root() -> Path:
    home_value = os.environ.get("HOME")
    if not home_value or not Path(home_value).is_absolute():
        fail("HOME must be an absolute path")
    xdg_value = os.environ.get("XDG_STATE_HOME")
    if xdg_value:
        base = Path(xdg_value)
        if not base.is_absolute():
            fail("XDG_STATE_HOME must be an absolute path")
    else:
        base = Path(home_value) / ".local" / "state"
    return Path(os.path.abspath(base / "agentic-praxis-grimoire"))


def default_skills_root() -> Path:
    home_value = os.environ.get("HOME")
    if not home_value or not Path(home_value).is_absolute():
        fail("HOME must be an absolute path")
    return Path(home_value) / ".agents" / "skills"


def absolute_root(value: str | None) -> Path:
    path = Path(value) if value else default_skills_root()
    if not path.is_absolute():
        fail("skills root must be absolute")
    return Path(os.path.abspath(path))


def paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def physical_location(path: Path) -> Path:
    existing = path
    missing: list[str] = []
    while not os.path.lexists(existing):
        missing.append(existing.name)
        existing = existing.parent
    try:
        physical = existing.resolve(strict=True)
    except OSError:
        fail("mutation root cannot be resolved safely")
    for component in reversed(missing):
        physical /= component
    return physical


def reject_mutation_root(
    root: Path,
    source: SourceIdentity | None = None,
    label: str = "skills root",
) -> None:
    physical_root = physical_location(root)
    if source is not None and paths_overlap(physical_root, Path(source.path).resolve(strict=True)):
        fail(f"{label} must be disjoint from the public source checkout")
    existing = root
    while not os.path.lexists(existing):
        existing = existing.parent
    result = run_git(existing, ["rev-parse", "--show-toplevel"], allow_failure=True)
    if not result.returncode:
        repository = Path(result.stdout.decode().strip()).resolve(strict=True)
        if paths_overlap(physical_root, repository):
            fail(f"a mutating {label} may not be inside or contain a Git worktree")


def verify_existing_ancestors(path: Path) -> None:
    allowed_system_aliases = {
        (Path("/tmp"), Path("/private/tmp")),
        (Path("/var"), Path("/private/var")),
    }
    current = path
    while True:
        if os.path.lexists(current):
            metadata = current.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                try:
                    alias = (current, current.resolve(strict=True))
                except OSError:
                    fail(f"path has a broken symlink ancestor: {current}")
                if alias not in allowed_system_aliases:
                    fail(f"path has a symlinked or non-directory ancestor: {current}")
            elif not stat.S_ISDIR(metadata.st_mode):
                fail(f"path has a symlinked or non-directory ancestor: {current}")
        if current == current.parent:
            break
        current = current.parent


def ensure_state_directory() -> Path:
    directory = state_root()
    verify_existing_ancestors(directory.parent)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = directory.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        fail("state directory is unsafe")
    directory.chmod(0o700)
    return directory


@contextmanager
def state_lock() -> Iterator[tuple[Path, Path]]:
    directory = ensure_state_directory()
    state_path = directory / "user-skills-v1.json"
    lock_path = directory / "user-skills-v1.lock"
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as error:
        fail(f"user-state lock cannot be opened safely: {error.strerror}")
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            fail("user-state lock has unsafe type or permissions")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("another user-skill command holds the mutation lock")
        yield state_path, lock_path
    finally:
        os.close(descriptor)


@contextmanager
def read_only_state_lock() -> Iterator[tuple[Path, Path]]:
    directory = state_root()
    verify_existing_ancestors(directory)
    if not os.path.lexists(directory):
        fail("user skill ownership state is absent")
    metadata = directory.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        fail("state directory is unsafe")
    if stat.S_IMODE(metadata.st_mode) != 0o700:
        fail("state directory has unsafe permissions")
    state_path = directory / "user-skills-v1.json"
    lock_path = directory / "user-skills-v1.lock"
    if not os.path.lexists(state_path):
        fail("user skill ownership state is absent")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags)
    except OSError as error:
        fail(f"user-state lock cannot be opened read-only: {error.strerror}")
    try:
        lock_metadata = os.fstat(descriptor)
        if not stat.S_ISREG(lock_metadata.st_mode) or stat.S_IMODE(lock_metadata.st_mode) != 0o600:
            fail("user-state lock has unsafe type or permissions")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("another user-skill command holds the mutation lock")
        yield state_path, lock_path
    finally:
        os.close(descriptor)


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def parse_source(value: object) -> SourceIdentity:
    if not isinstance(value, dict) or set(value) != SOURCE_KEYS:
        fail("user state source identity is malformed")
    if any(not isinstance(value[key], str) for key in ("commit", "path", "tag", "tree", "version")):
        fail("user state source identity types are malformed")
    hashes = value["skill_hashes"]
    if not isinstance(hashes, dict) or tuple(sorted(hashes)) != SKILLS:
        fail("user state source skill hashes are malformed")
    if any(not isinstance(member, str) or not re.fullmatch(r"[0-9a-f]{64}", member) for member in hashes.values()):
        fail("user state source skill hashes are malformed")
    return SourceIdentity(
        value["path"],
        value["version"],
        value["tag"],
        value["commit"],
        value["tree"],
        tuple(sorted(hashes.items())),
    )


def parse_container(value: object) -> ContainerIdentity:
    keys = {"device", "inode", "mode", "owner", "path"}
    if not isinstance(value, dict) or set(value) != keys:
        fail("user state created-container identity is malformed")
    if not isinstance(value["path"], str) or not Path(value["path"]).is_absolute():
        fail("user state created-container path is malformed")
    if any(type(value[key]) is not int or value[key] < 0 for key in ("device", "inode", "mode", "owner")):
        fail("user state created-container metadata is malformed")
    return ContainerIdentity(
        value["path"], value["device"], value["inode"], value["owner"], value["mode"]
    )


def read_state(path: Path) -> State | None:
    if not os.path.lexists(path):
        return None
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_nlink != 1:
        fail("user state has unsafe type, permissions, or link count")
    if metadata.st_size > 256 * 1024 or metadata.st_size == 0:
        fail("user state is empty or oversized")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        fail("user state is malformed")
    if not isinstance(value, dict) or set(value) != STATE_KEYS:
        fail("user state schema is malformed or unsupported")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        fail("user state schema version is unsupported")
    if not isinstance(value["skills_root"], str) or not Path(value["skills_root"]).is_absolute():
        fail("user state skills root is malformed")
    if os.path.normpath(value["skills_root"]) != value["skills_root"]:
        fail("user state skills root is not canonical")
    managed = value["managed_skills"]
    if managed != list(SKILLS):
        fail("user state managed skill list is malformed")
    containers = value["created_containers"]
    if not isinstance(containers, list):
        fail("user state created-container ownership is malformed")
    parsed_containers = tuple(parse_container(item) for item in containers)
    paths = [item.path for item in parsed_containers]
    if paths != sorted(set(paths), key=lambda item: (len(Path(item).parts), item)):
        fail("user state created-container ownership is not canonical")
    root = Path(value["skills_root"])
    container_paths = tuple(Path(item) for item in paths)
    if container_paths and (
        container_paths[-1] != root
        or any(child.parent != parent for parent, child in zip(container_paths, container_paths[1:]))
    ):
        fail("user state created-container ownership is outside the skills-root chain")
    previous = None if value["previous_source"] is None else parse_source(value["previous_source"])
    return State(
        value["skills_root"],
        parse_source(value["current_source"]),
        previous,
        tuple(managed),
        parsed_containers,
    )


def serialize_state(state: State) -> bytes:
    value = {
        "created_containers": [item.as_dict() for item in state.created_containers],
        "current_source": state.current_source.as_dict(),
        "managed_skills": list(state.managed_skills),
        "previous_source": None if state.previous_source is None else state.previous_source.as_dict(),
        "schema_version": SCHEMA_VERSION,
        "skills_root": state.skills_root,
    }
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_state_write(path: Path, state: State) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".user-skills-v1.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        content = serialize_state(state)
        os.write(descriptor, content)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary_path, path)
        path.chmod(0o600)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)


def source_matches(recorded: SourceIdentity) -> SourceIdentity:
    verified = verify_source(recorded.path)
    if verified != recorded:
        fail("recorded public source release identity has changed")
    return verified


def exact_links(root: Path, source: SourceIdentity) -> None:
    verify_existing_ancestors(root)
    if not root.is_dir() or root.is_symlink():
        fail("managed user skill root is missing or unsafe")
    for name in SKILLS:
        link = root / name
        if not os.path.lexists(link):
            fail(f"managed user skill link is missing: {name}")
        if not link.is_symlink():
            fail(f"managed user skill path is not a symbolic link: {name}")
        expected = Path(source.path) / "skills" / name
        if os.readlink(link) != str(expected):
            fail(f"managed user skill raw link target changed: {name}")
        try:
            if link.resolve(strict=True) != expected.resolve(strict=True):
                fail(f"managed user skill link is retargeted: {name}")
        except OSError:
            fail(f"managed user skill link is broken: {name}")


def create_containers(root: Path) -> tuple[ContainerIdentity, ...]:
    verify_existing_ancestors(root)
    missing: list[Path] = []
    current = root
    while not os.path.lexists(current):
        missing.append(current)
        current = current.parent
    if current.is_symlink() or not current.is_dir():
        fail("user skill root has an unsafe existing ancestor")
    created: list[ContainerIdentity] = []
    for path in reversed(missing):
        path.mkdir(mode=0o755)
        metadata = path.lstat()
        created.append(
            ContainerIdentity(
                str(path),
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_uid,
                stat.S_IMODE(metadata.st_mode),
            )
        )
    return tuple(created)


def preflight_absent(root: Path) -> None:
    for name in SKILLS:
        path = root / name
        if os.path.lexists(path):
            fail(f"unmanaged or conflicting user skill path exists: {name}; use adopt only for exact links")


def create_links(root: Path, source: SourceIdentity) -> None:
    created: list[Path] = []
    try:
        for name in SKILLS:
            link = root / name
            link.symlink_to(Path(source.path) / "skills" / name, target_is_directory=True)
            created.append(link)
    except OSError as error:
        for link in reversed(created):
            link.unlink(missing_ok=True)
        fail(f"user skill links could not be created safely: {error.strerror}")


def verify_adoptable(root: Path, source: SourceIdentity) -> None:
    verify_existing_ancestors(root)
    if not root.is_dir() or root.is_symlink():
        fail("user skill root is missing or unsafe for adoption")
    for name in SKILLS:
        link = root / name
        if not link.is_symlink():
            fail(f"adoption requires an exact existing symbolic link: {name}")
        try:
            resolved = link.resolve(strict=True)
        except OSError:
            fail(f"adoption link is broken: {name}")
        if resolved != (Path(source.path) / "skills" / name).resolve(strict=True):
            fail(f"adoption link target is mismatched: {name}")
        if os.readlink(link) != str(Path(source.path) / "skills" / name):
            fail(f"adoption requires the exact canonical raw link target: {name}")


def replace_links(root: Path, old: SourceIdentity, new: SourceIdentity) -> None:
    exact_links(root, old)
    for name in SKILLS:
        for suffix in ("new", "rollback"):
            temporary = root / f".{name}.apg-user-skills-{suffix}"
            if os.path.lexists(temporary):
                fail(f"interrupted temporary link requires inspection: {temporary.name}")
    replaced: list[str] = []
    try:
        for name in SKILLS:
            link = root / name
            temporary = root / f".{name}.apg-user-skills-new"
            temporary.symlink_to(Path(new.path) / "skills" / name, target_is_directory=True)
            os.replace(temporary, link)
            replaced.append(name)
    except (OSError, ToolError) as error:
        for name in reversed(replaced):
            link = root / name
            temporary = root / f".{name}.apg-user-skills-rollback"
            temporary.symlink_to(Path(old.path) / "skills" / name, target_is_directory=True)
            os.replace(temporary, link)
        if isinstance(error, ToolError):
            raise
        fail(f"user skill update failed and prior links were restored: {error.strerror}")


def repository_duplicates(requested: str | None) -> tuple[str, ...]:
    if not requested:
        return ()
    path = Path(requested)
    result = run_git(path, ["rev-parse", "--show-toplevel"], allow_failure=True)
    if result.returncode:
        fail("duplicate-check repository is not a Git worktree")
    repo_root = Path(result.stdout.decode().strip()).resolve(strict=True)
    current = path.resolve(strict=True)
    scopes: list[Path] = []
    while True:
        scopes.append(current / ".agents" / "skills")
        if current == repo_root:
            break
        if repo_root not in current.parents:
            fail("duplicate-check path is outside its reported repository root")
        current = current.parent
    duplicates: set[str] = set()
    for scope in scopes:
        if not scope.is_dir() or scope.is_symlink():
            continue
        for name in SKILLS:
            skill_file = scope / name / "SKILL.md"
            if skill_file.is_file():
                try:
                    if frontmatter_name(skill_file) == name:
                        duplicates.add(name)
                except ToolError:
                    continue
    return tuple(sorted(duplicates))


def render_source(identity: SourceIdentity, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(
            {"schema_version": 1, "skills": list(SKILLS), "source": identity.as_dict()},
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"
    return "\n".join(SKILLS) + "\n"


def do_install(source: SourceIdentity, root: Path, state_path: Path) -> str:
    state = read_state(state_path)
    if state is not None:
        if state.skills_root != str(root) or state.current_source != source:
            fail("existing user state belongs to another root or source")
        source_matches(state.current_source)
        exact_links(root, state.current_source)
        return "PASS user skills already installed; no discovery state changed."
    created = create_containers(root)
    links_created = False
    try:
        preflight_absent(root)
        create_links(root, source)
        links_created = True
        atomic_state_write(state_path, State(str(root), source, None, SKILLS, created))
    except Exception:
        if links_created:
            for name in SKILLS:
                link = root / name
                if link.is_symlink() and os.readlink(link) == str(Path(source.path) / "skills" / name):
                    link.unlink()
        for container in sorted((Path(item.path) for item in created), key=lambda item: len(item.parts), reverse=True):
            try:
                container.rmdir()
            except OSError:
                pass
        raise
    return f"PASS installed six user skills. {RESTART_REMINDER}"


def do_adopt(source: SourceIdentity, root: Path, state_path: Path) -> str:
    state = read_state(state_path)
    if state is not None:
        if state.skills_root == str(root) and state.current_source == source:
            exact_links(root, source)
            return "PASS user skills already adopted; no discovery state changed."
        fail("existing user state belongs to another root or source")
    verify_adoptable(root, source)
    atomic_state_write(state_path, State(str(root), source, None, SKILLS, ()))
    return f"PASS adopted six exact user skill links. {RESTART_REMINDER}"


def do_check(root: Path, state_path: Path, repo: str | None, output_format: str) -> str:
    state = read_state(state_path)
    if state is None:
        fail("user skill ownership state is absent")
    if state.skills_root != str(root):
        fail("user state belongs to another skill root")
    source_matches(state.current_source)
    exact_links(root, state.current_source)
    duplicates = repository_duplicates(repo)
    if output_format == "json":
        return json.dumps(
            {
                "duplicate_repository_skills": list(duplicates),
                "schema_version": 1,
                "source": state.current_source.as_dict(),
                "status": "pass",
            },
            separators=(",", ":"),
            sort_keys=True,
        ) + "\n"
    lines = [f"PASS managed user skills: {state.current_source.tag} at {state.current_source.commit}"]
    if duplicates:
        lines.append(
            "WARNING duplicate repository-scope skill names may both appear and are not merged: "
            + ", ".join(duplicates)
        )
    return "\n".join(lines) + "\n"


def do_update(source: SourceIdentity, root: Path, state_path: Path) -> str:
    state = read_state(state_path)
    if state is None:
        fail("install or adopt before update")
    if state.skills_root != str(root):
        fail("user state belongs to another skill root")
    source_matches(state.current_source)
    if source.path == state.current_source.path or source.commit == state.current_source.commit:
        fail("update requires a distinct public release source")
    replace_links(root, state.current_source, source)
    try:
        atomic_state_write(state_path, State(str(root), source, state.current_source, SKILLS, state.created_containers))
    except Exception:
        replace_links(root, source, state.current_source)
        raise
    return f"PASS updated six user skills to {source.tag}. {RESTART_REMINDER}"


def do_rollback(source_argument: str | None, root: Path, state_path: Path) -> str:
    state = read_state(state_path)
    if state is None or state.previous_source is None:
        fail("no previous public source is available for rollback")
    if state.skills_root != str(root):
        fail("user state belongs to another skill root")
    source_matches(state.current_source)
    desired = verify_source(source_argument) if source_argument else source_matches(state.previous_source)
    expected = state.previous_source
    if (
        desired.version,
        desired.tag,
        desired.commit,
        desired.tree,
        desired.skill_hashes,
    ) != (
        expected.version,
        expected.tag,
        expected.commit,
        expected.tree,
        expected.skill_hashes,
    ):
        fail("rollback source does not match the recorded previous release")
    replace_links(root, state.current_source, desired)
    try:
        atomic_state_write(state_path, State(str(root), desired, state.current_source, SKILLS, state.created_containers))
    except Exception:
        replace_links(root, desired, state.current_source)
        raise
    return f"PASS rolled back six user skills to {desired.tag}. {RESTART_REMINDER}"


def do_uninstall(root: Path, state_path: Path) -> str:
    state = read_state(state_path)
    if state is None:
        return "PASS user skills are already uninstalled; no discovery state changed."
    if state.skills_root != str(root):
        fail("user state belongs to another skill root")
    source_matches(state.current_source)
    exact_links(root, state.current_source)
    removed: list[str] = []
    try:
        for name in SKILLS:
            (root / name).unlink()
            removed.append(name)
    except OSError as error:
        for name in removed:
            (root / name).symlink_to(Path(state.current_source.path) / "skills" / name, target_is_directory=True)
        fail(f"uninstall failed and removed links were restored: {error.strerror}")
    state_path.unlink()
    for identity in sorted(state.created_containers, key=lambda item: len(Path(item.path).parts), reverse=True):
        container = Path(identity.path)
        try:
            metadata = container.lstat()
            current_identity = (
                metadata.st_dev,
                metadata.st_ino,
                metadata.st_uid,
                stat.S_IMODE(metadata.st_mode),
            )
            recorded_identity = (identity.device, identity.inode, identity.owner, identity.mode)
            if current_identity == recorded_identity:
                container.rmdir()
        except OSError:
            pass
    return f"PASS uninstalled six owned user skills. {RESTART_REMINDER}"


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog=COMMAND,
        description="Manage six direct user-scoped APG skill links from a verified public release.",
    )
    subcommands = root.add_subparsers(dest="operation", required=True)
    list_parser = subcommands.add_parser("list", help="list six skills from a verified public source")
    list_parser.add_argument("--source", required=True)
    list_parser.add_argument("--skills-root")
    list_parser.add_argument("--format", choices=("text", "json"), default="text")
    for operation in ("install", "adopt", "update"):
        command = subcommands.add_parser(operation, help=f"{operation} user-scoped skill links")
        command.add_argument("--source", required=True)
        command.add_argument("--skills-root")
    check = subcommands.add_parser("check", help="verify managed user-scoped links read-only")
    check.add_argument("--skills-root")
    check.add_argument("--repo")
    check.add_argument("--format", choices=("text", "json"), default="text")
    rollback = subcommands.add_parser("rollback", help="retarget to the recorded previous public release")
    rollback.add_argument("--source")
    rollback.add_argument("--skills-root")
    uninstall = subcommands.add_parser("uninstall", help="remove only state-proven user links")
    uninstall.add_argument("--skills-root")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.operation == "list":
            identity = verify_source(arguments.source)
            sys.stdout.write(render_source(identity, arguments.format))
            return 0
        root = absolute_root(arguments.skills_root)
        user_state_root = state_root()
        if paths_overlap(physical_location(root), physical_location(user_state_root)):
            fail("skills root and user-state root must be disjoint")
        verify_existing_ancestors(root)
        verified_source = None
        if arguments.operation in {"install", "adopt", "update"}:
            verified_source = verify_source(arguments.source)
        if arguments.operation != "check":
            reject_mutation_root(root, verified_source)
        reject_mutation_root(user_state_root, verified_source, "user-state root")
        lock_context = read_only_state_lock() if arguments.operation == "check" else state_lock()
        with lock_context as (state_path, _lock_path):
            if arguments.operation == "install":
                output = do_install(verified_source, root, state_path)
            elif arguments.operation == "adopt":
                output = do_adopt(verified_source, root, state_path)
            elif arguments.operation == "check":
                sys.stdout.write(do_check(root, state_path, arguments.repo, arguments.format))
                return 0
            elif arguments.operation == "update":
                output = do_update(verified_source, root, state_path)
            elif arguments.operation == "rollback":
                output = do_rollback(arguments.source, root, state_path)
            else:
                output = do_uninstall(root, state_path)
        print(output)
        return 0
    except ToolError as error:
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
