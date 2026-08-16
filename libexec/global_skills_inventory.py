"""Resolve and inventory local repositories for global skill projection."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
from typing import Mapping, Sequence


DEFAULT_EXCLUDED_DIR_NAMES = frozenset(
    {".git", ".hg", ".svn", ".venv", "venv", "__pycache__", "node_modules"}
)


class InventoryError(RuntimeError):
    """A source, destination, overlap, or collision is unsafe."""


@dataclass(frozen=True, slots=True)
class PathIdentity:
    device: int
    inode: int
    mode: int
    owner: int


@dataclass(frozen=True, slots=True)
class RepositoryRecord:
    repository: Path
    skills_root: Path
    repository_identity: PathIdentity
    skills_root_identity: PathIdentity


@dataclass(frozen=True, slots=True)
class SkillRecord:
    name: str
    source: Path
    repository: Path
    skills_root: Path
    relative_path: str
    skill_sha256: str
    repository_identity: PathIdentity
    skills_root_identity: PathIdentity
    source_identity: PathIdentity
    marker_identity: PathIdentity


@dataclass(frozen=True, slots=True)
class Inventory:
    destination: Path
    sources: tuple[RepositoryRecord, ...]
    skills: tuple[SkillRecord, ...]


def validate_component(value: str, label: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise InventoryError(f"{label} must be one safe path component")
    return value


def validate_path_spelling(value: Path | str, label: str) -> Path:
    text = os.fspath(value)
    if any(
        0 < ord(character) < 32 or ord(character) == 127
        for character in text
    ):
        raise InventoryError(f"{label} contains ASCII control characters")
    if "\x00" in text:
        try:
            os.lstat(text)
        except ValueError as error:
            raise InventoryError(f"{label} is not a valid path") from error
    return Path(text)


def lexical_absolute(path: Path, label: str = "path") -> Path:
    checked = validate_path_spelling(path, label).expanduser()
    return Path(os.path.abspath(os.fspath(checked)))


def identity(metadata: os.stat_result) -> PathIdentity:
    return PathIdentity(
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IMODE(metadata.st_mode),
        metadata.st_uid,
    )


def read_skill_marker(path: Path) -> tuple[PathIdentity, str]:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        )
    except OSError as error:
        raise InventoryError("source skill marker is unsafe") from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise InventoryError("source skill marker is unsafe")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
        path_after = path.lstat()
        if (
            identity(after) != identity(before)
            or after.st_size != before.st_size
            or not stat.S_ISREG(path_after.st_mode)
            or identity(path_after) != identity(before)
        ):
            raise InventoryError("source skill marker changed during inventory")
        return identity(before), digest.hexdigest()
    finally:
        os.close(descriptor)


def require_absolute_environment(
    environment: Mapping[str, str], name: str
) -> Path:
    value = environment.get(name)
    if not value:
        raise InventoryError(f"{name} must be an absolute path")
    checked = validate_path_spelling(value, name)
    if not checked.is_absolute():
        raise InventoryError(f"{name} must be an absolute path")
    return lexical_absolute(checked, name)


def destination_for(
    agent: str,
    override: Path | None,
    environment: Mapping[str, str],
) -> Path:
    if override is not None:
        checked = validate_path_spelling(override, "--skills-root")
        if not checked.is_absolute():
            raise InventoryError("--skills-root must be an absolute path")
        return lexical_absolute(checked, "--skills-root")
    if agent == "codex":
        return require_absolute_environment(environment, "HOME") / ".agents" / "skills"
    if agent != "claude":
        raise InventoryError(f"unsupported agent: {agent}")
    configured = environment.get("CLAUDE_CONFIG_DIR")
    if configured:
        checked = validate_path_spelling(configured, "CLAUDE_CONFIG_DIR")
        if not checked.is_absolute():
            raise InventoryError("CLAUDE_CONFIG_DIR must be an absolute path")
        base = lexical_absolute(checked, "CLAUDE_CONFIG_DIR")
    else:
        base = require_absolute_environment(environment, "HOME") / ".claude"
    return base / "skills"


def apg_repository(
    override: Path | None,
    environment: Mapping[str, str],
) -> Path:
    if override is not None:
        return validate_path_spelling(override, "--apg-root")
    local = environment.get("LOCAL_PROJ_INSTALL")
    if local:
        base = validate_path_spelling(local, "LOCAL_PROJ_INSTALL")
        if not base.is_absolute():
            raise InventoryError("LOCAL_PROJ_INSTALL must be an absolute path")
        base = lexical_absolute(base, "LOCAL_PROJ_INSTALL")
    else:
        base = require_absolute_environment(environment, "HOME") / ".local" / "share"
    return base / "agentic-praxis-grimoire"


def source_values(
    repositories: Sequence[Path],
    include_apg: bool,
    apg_root: Path | None,
    environment: Mapping[str, str],
) -> tuple[Path, ...]:
    explicit = tuple(
        validate_path_spelling(value, "repository argument")
        for value in repositories
    )
    if include_apg and not explicit:
        raise InventoryError("--include-apg requires an explicit repository")
    if explicit and apg_root is not None and not include_apg:
        raise InventoryError("--apg-root requires --include-apg with repositories")
    if not explicit:
        return (apg_repository(apg_root, environment),)
    if include_apg:
        return (*explicit, apg_repository(apg_root, environment))
    return explicit


def paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def resolve_repository(value: Path) -> RepositoryRecord:
    lexical = lexical_absolute(value, "repository argument")
    try:
        physical = lexical.resolve(strict=True)
    except OSError as error:
        raise InventoryError(f"source repository is unavailable: {value}") from error
    if lexical != physical:
        raise InventoryError(f"source repository path is symlinked: {value}")
    repository_metadata = physical.lstat()
    if not stat.S_ISDIR(repository_metadata.st_mode):
        raise InventoryError(f"source repository is not a directory: {value}")
    skills_root = physical / "skills"
    try:
        metadata = skills_root.lstat()
    except OSError as error:
        raise InventoryError(
            f"source repository requires a skills directory: {value}"
        ) from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise InventoryError(
            f"source repository skills path is unsafe: {value}"
        )
    return RepositoryRecord(
        physical,
        skills_root,
        identity(repository_metadata),
        identity(metadata),
    )


def discover_resolved(source: RepositoryRecord) -> tuple[SkillRecord, ...]:
    records: list[SkillRecord] = []
    for current_text, directory_names, file_names in os.walk(
        source.skills_root, followlinks=False
    ):
        current = Path(current_text)
        retained: list[str] = []
        for name in directory_names:
            candidate = current / name
            if (
                name not in DEFAULT_EXCLUDED_DIR_NAMES
                and not candidate.is_symlink()
            ):
                retained.append(name)
        directory_names[:] = sorted(retained, key=lambda item: (item.casefold(), item))
        marker = current / "SKILL.md"
        if "SKILL.md" not in file_names:
            continue
        marker_metadata = marker.lstat()
        if (
            stat.S_ISLNK(marker_metadata.st_mode)
            or not stat.S_ISREG(marker_metadata.st_mode)
        ):
            continue
        source_metadata = current.lstat()
        if (
            stat.S_ISLNK(source_metadata.st_mode)
            or not stat.S_ISDIR(source_metadata.st_mode)
        ):
            raise InventoryError("source skill directory changed during inventory")
        marker_identity, marker_digest = read_skill_marker(marker)
        name = validate_component(current.name, "skill name")
        relative = current.relative_to(source.repository).as_posix()
        records.append(
            SkillRecord(
                name,
                current,
                source.repository,
                source.skills_root,
                relative,
                marker_digest,
                source.repository_identity,
                source.skills_root_identity,
                identity(source_metadata),
                marker_identity,
            )
        )
    return tuple(
        sorted(records, key=lambda item: (item.name.casefold(), item.name, item.relative_path))
    )


def discover_repository(value: Path) -> tuple[SkillRecord, ...]:
    return discover_resolved(resolve_repository(value))


def collision_message(group: Sequence[SkillRecord]) -> str:
    name = group[0].name
    lines = [f"Duplicate global skill name {name!r}:"]
    for skill in group:
        lines.append(
            f"  repository={skill.repository} relative={skill.relative_path}"
        )
    return "\n".join(lines)


def build_inventory(
    repository_values: Sequence[Path],
    destination: Path,
) -> Inventory:
    resolved = tuple(resolve_repository(value) for value in repository_values)
    repositories = [item.repository for item in resolved]
    if len(set(repositories)) != len(repositories):
        raise InventoryError("duplicate source repository")
    for index, repository in enumerate(repositories):
        for other in repositories[index + 1 :]:
            if paths_overlap(repository, other):
                raise InventoryError("source repositories may not be nested")
    destination = lexical_absolute(destination)
    for repository in repositories:
        if paths_overlap(repository, destination):
            raise InventoryError("source repository and destination overlap")
    skills = tuple(
        skill
        for record in resolved
        for skill in discover_resolved(record)
    )
    if not skills:
        raise InventoryError("no direct regular SKILL.md markers were found")
    groups: dict[str, list[SkillRecord]] = {}
    for skill in skills:
        groups.setdefault(skill.name.casefold(), []).append(skill)
    collisions = [group for group in groups.values() if len(group) > 1]
    if collisions:
        raise InventoryError(
            "\n".join(collision_message(group) for group in collisions)
        )
    return Inventory(
        destination,
        tuple(sorted(resolved, key=lambda item: str(item.repository))),
        tuple(
            sorted(
                skills,
                key=lambda item: (
                    item.name.casefold(),
                    item.name,
                    str(item.repository),
                    item.relative_path,
                ),
            )
        ),
    )
