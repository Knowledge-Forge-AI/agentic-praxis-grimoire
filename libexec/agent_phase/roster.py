"""Closed, bounded capture and lookup for the tracked dispatcher roster."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import re
import stat
import tomllib
from types import MappingProxyType
from typing import Callable, Mapping, NamedTuple

from .request import EXECUTION_MODES, PHASE_TYPES


ENDPOINTS_SCHEMA = "agent-phase-endpoints-v1"
ROUTES_SCHEMA = "agent-phase-routes-v1"
PROVENANCE_SCHEMA = "agent-phase-roster-provenance-v1"
ENDPOINTS_SOURCE = Path("common/dispatcher/endpoints.toml")
ROUTES_SOURCE = Path("common/dispatcher/routes.toml")
STANDARD_SLOTS = ("plan", "plan_review", "work", "final_review", "closeout")
PROVIDERS = frozenset({"antigravity", "claude", "codex"})
MODE_PROVIDER_REQUIREMENTS = {
    "claude_only": "claude",
    "codex_only": "codex",
    "gemini_only": "antigravity",
}
MODE_FORBIDDEN_PROVIDERS = {
    "gemini_opus": "codex",
    "gemini_fable": "codex",
}
MAX_ROSTER_BYTES = 256 * 1024
MAX_ROSTER_GENERATION = (1 << 63) - 1
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_READ_CHUNK = 64 * 1024


class RosterError(RuntimeError):
    """Tracked dispatcher roster data is missing or invalid."""


class Endpoint(NamedTuple):
    provider: str
    profile: str


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


@dataclass(frozen=True)
class RosterSource:
    path: Path
    sha256: str
    raw: bytes = field(repr=False)
    identity: PhysicalIdentity = field(repr=False)

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path.as_posix(), "sha256": self.sha256}


@dataclass(frozen=True)
class _CapturedSource:
    path: Path
    raw: bytes
    identity: PhysicalIdentity


@dataclass(frozen=True)
class RosterSnapshot:
    endpoints: Mapping[str, Endpoint]
    routes: Mapping[tuple[str, str], Mapping[str, str]]
    generation: int
    endpoints_source: RosterSource
    routes_source: RosterSource

    def __post_init__(self) -> None:
        endpoints = MappingProxyType(dict(self.endpoints))
        routes = MappingProxyType(
            {
                key: MappingProxyType(dict(aliases))
                for key, aliases in self.routes.items()
            }
        )
        object.__setattr__(self, "endpoints", endpoints)
        object.__setattr__(self, "routes", routes)

    def route_aliases(self, phase_type: str, execution_mode: str) -> dict[str, str]:
        key = (phase_type, execution_mode)
        aliases = self.routes.get(key)
        if aliases is None:
            raise RosterError(f"no tracked route for {key}")
        return dict(aliases)

    def route_endpoints(
        self, phase_type: str, execution_mode: str
    ) -> dict[str, Endpoint]:
        return {
            slot: self.endpoints[alias]
            for slot, alias in self.route_aliases(phase_type, execution_mode).items()
        }

    def provenance(self) -> dict[str, object]:
        return {
            "schema": PROVENANCE_SCHEMA,
            "generation": self.generation,
            "sources": {
                "endpoints": self.endpoints_source.as_dict(),
                "routes": self.routes_source.as_dict(),
            },
        }


# Compatibility for callers that imported the original type name.
Roster = RosterSnapshot


def _display(relative: Path) -> str:
    return relative.as_posix()


def _path_error(relative: Path, detail: str) -> RosterError:
    return RosterError(f"cannot read tracked roster {_display(relative)}: {detail}")


def _validate_relative(relative: Path) -> None:
    if relative.is_absolute() or not relative.parts or any(
        part in ("", ".", "..") for part in relative.parts
    ):
        raise RosterError(f"invalid tracked roster path: {_display(relative)}")


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _open_parent(root: Path, relative: Path) -> tuple[int, str]:
    """Open the roster parent without following a root-relative symlink."""
    _validate_relative(relative)
    try:
        root_stat = os.lstat(root)
    except OSError as error:
        raise _path_error(relative, str(error)) from error
    if stat.S_ISLNK(root_stat.st_mode):
        raise _path_error(relative, "repository root is a symlink")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise _path_error(relative, "repository root is not a directory")
    try:
        descriptor = os.open(root, _directory_flags())
    except OSError as error:
        raise _path_error(relative, str(error)) from error
    try:
        opened_root = os.fstat(descriptor)
        if (opened_root.st_dev, opened_root.st_ino) != (
            root_stat.st_dev,
            root_stat.st_ino,
        ):
            raise _path_error(relative, "repository root moved during capture")
        for index, component in enumerate(relative.parts[:-1]):
            traversed = Path(*relative.parts[: index + 1])
            try:
                before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            except OSError as error:
                raise _path_error(relative, str(error)) from error
            if stat.S_ISLNK(before.st_mode):
                raise _path_error(relative, f"symlinked ancestor: {traversed.as_posix()}")
            if not stat.S_ISDIR(before.st_mode):
                raise _path_error(relative, f"ancestor is not a directory: {traversed.as_posix()}")
            try:
                next_descriptor = os.open(
                    component, _directory_flags(), dir_fd=descriptor
                )
            except OSError as error:
                raise _path_error(relative, str(error)) from error
            after = os.fstat(next_descriptor)
            if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
                os.close(next_descriptor)
                raise _path_error(relative, f"ancestor moved during capture: {traversed.as_posix()}")
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor, relative.name
    except BaseException:
        os.close(descriptor)
        raise


def _validate_regular(
    relative: Path, value: os.stat_result, *, expected: PhysicalIdentity | None = None
) -> PhysicalIdentity:
    identity = PhysicalIdentity.from_stat(value)
    if expected is not None and identity != expected:
        raise _path_error(relative, "roster source changed during capture")
    if stat.S_ISLNK(value.st_mode):
        raise _path_error(relative, "roster leaf is a symlink")
    if not stat.S_ISREG(value.st_mode):
        raise _path_error(relative, "roster leaf is not a regular file")
    if value.st_nlink != 1:
        raise _path_error(relative, "roster leaf must be a single-link file")
    expected_owner = os.geteuid()
    if value.st_uid != expected_owner:
        raise _path_error(relative, "roster leaf is not owned by the effective account")
    return identity


def _capture_source(root: Path, relative: Path) -> _CapturedSource:
    parent_descriptor, leaf = _open_parent(root, relative)
    descriptor: int | None = None
    try:
        try:
            named = os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False)
        except OSError as error:
            raise _path_error(relative, str(error)) from error
        identity = _validate_regular(relative, named)
        if identity.size > MAX_ROSTER_BYTES:
            raise RosterError(
                f"tracked roster {_display(relative)} exceeds {MAX_ROSTER_BYTES} bytes"
            )
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            descriptor = os.open(leaf, flags, dir_fd=parent_descriptor)
        except OSError as error:
            raise _path_error(relative, str(error)) from error
        _validate_regular(relative, os.fstat(descriptor), expected=identity)
        chunks: list[bytes] = []
        total = 0
        while total <= MAX_ROSTER_BYTES:
            try:
                chunk = os.read(
                    descriptor,
                    min(_READ_CHUNK, MAX_ROSTER_BYTES + 1 - total),
                )
            except OSError as error:
                raise _path_error(relative, str(error)) from error
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total > MAX_ROSTER_BYTES:
            raise RosterError(
                f"tracked roster {_display(relative)} exceeds {MAX_ROSTER_BYTES} bytes"
            )
        _validate_regular(relative, os.fstat(descriptor), expected=identity)
        if total != identity.size:
            raise _path_error(relative, "roster source changed size during capture")
        return _CapturedSource(relative, b"".join(chunks), identity)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent_descriptor)


def _revalidate_source(root: Path, source: _CapturedSource) -> None:
    parent_descriptor, leaf = _open_parent(root, source.path)
    try:
        try:
            named = os.stat(leaf, dir_fd=parent_descriptor, follow_symlinks=False)
        except OSError as error:
            raise _path_error(source.path, str(error)) from error
        _validate_regular(source.path, named, expected=source.identity)
    finally:
        os.close(parent_descriptor)


def _parse_toml(source: _CapturedSource) -> dict[str, object]:
    try:
        text = source.raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RosterError(
            f"tracked roster {_display(source.path)} is not UTF-8: {error}"
        ) from error
    try:
        value = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise RosterError(
            f"tracked roster {_display(source.path)} is not valid TOML: {error}"
        ) from error
    if not isinstance(value, dict):
        raise RosterError(f"tracked roster {_display(source.path)} is not a table")
    return value


def _generation(value: object, label: str) -> int:
    if type(value) is not int or not 1 <= value <= MAX_ROSTER_GENERATION:
        raise RosterError(
            f"{label} roster generation must be a positive bounded integer"
        )
    return value


def _parse_endpoints(
    value: dict[str, object],
) -> tuple[int, dict[str, Endpoint]]:
    if set(value) != {"schema", "generation", "endpoints"}:
        raise RosterError("endpoints roster top-level fields are not closed")
    if value.get("schema") != ENDPOINTS_SCHEMA:
        raise RosterError(f"endpoints roster schema must be {ENDPOINTS_SCHEMA}")
    generation = _generation(value.get("generation"), "endpoints")
    table = value.get("endpoints")
    if not isinstance(table, dict) or not table:
        raise RosterError("endpoints roster must contain endpoint tables")
    endpoints: dict[str, Endpoint] = {}
    for alias, raw_endpoint in sorted(table.items()):
        if not isinstance(alias, str) or _NAME.fullmatch(alias) is None:
            raise RosterError(f"invalid endpoint alias: {alias!r}")
        if not isinstance(raw_endpoint, dict) or set(raw_endpoint) != {
            "provider",
            "profile",
        }:
            raise RosterError(f"endpoint {alias} fields must be provider and profile")
        provider = raw_endpoint.get("provider")
        profile = raw_endpoint.get("profile")
        if type(provider) is not str or provider not in PROVIDERS:
            raise RosterError(f"endpoint {alias} has unknown provider: {provider!r}")
        if type(profile) is not str or _NAME.fullmatch(profile) is None:
            raise RosterError(f"endpoint {alias} has invalid profile")
        endpoints[alias] = Endpoint(provider, profile)
    return generation, endpoints


def _validate_mode_provider(
    phase_type: str,
    execution_mode: str,
    aliases: Mapping[str, str],
    endpoints: Mapping[str, Endpoint],
) -> None:
    required_provider = MODE_PROVIDER_REQUIREMENTS.get(execution_mode)
    if required_provider is not None:
        if any(
            endpoints[alias].provider != required_provider for alias in aliases.values()
        ):
            raise RosterError(
                f"route {phase_type}/{execution_mode} must use only "
                f"{required_provider} endpoints"
            )
    forbidden_provider = MODE_FORBIDDEN_PROVIDERS.get(execution_mode)
    if forbidden_provider is not None:
        if any(
            endpoints[alias].provider == forbidden_provider for alias in aliases.values()
        ):
            raise RosterError(
                f"route {phase_type}/{execution_mode} must not use "
                f"{forbidden_provider} endpoints"
            )


def _parse_routes(
    value: dict[str, object], endpoints: Mapping[str, Endpoint]
) -> tuple[int, dict[tuple[str, str], dict[str, str]]]:
    if set(value) != {"schema", "generation", "routes"}:
        raise RosterError("routes roster top-level fields are not closed")
    if value.get("schema") != ROUTES_SCHEMA:
        raise RosterError(f"routes roster schema must be {ROUTES_SCHEMA}")
    generation = _generation(value.get("generation"), "routes")
    phases = value.get("routes")
    if not isinstance(phases, dict) or set(phases) != set(PHASE_TYPES):
        raise RosterError("routes roster phase types are incomplete or unsupported")
    result: dict[tuple[str, str], dict[str, str]] = {}
    for phase_type in PHASE_TYPES:
        modes = phases.get(phase_type)
        if not isinstance(modes, dict) or set(modes) != set(EXECUTION_MODES):
            raise RosterError(
                f"routes roster modes for {phase_type} are incomplete or unsupported"
            )
        for execution_mode in EXECUTION_MODES:
            raw_route = modes.get(execution_mode)
            if not isinstance(raw_route, dict) or set(raw_route) != set(STANDARD_SLOTS):
                raise RosterError(
                    f"route {phase_type}/{execution_mode} must contain exactly "
                    f"{list(STANDARD_SLOTS)}"
                )
            aliases: dict[str, str] = {}
            for slot in STANDARD_SLOTS:
                alias = raw_route.get(slot)
                if type(alias) is not str or alias not in endpoints:
                    raise RosterError(
                        f"route {phase_type}/{execution_mode} references unknown "
                        f"endpoint alias in {slot}: {alias!r}"
                    )
                aliases[slot] = alias
            _validate_mode_provider(phase_type, execution_mode, aliases, endpoints)
            result[(phase_type, execution_mode)] = aliases
    return generation, result


def _source(value: _CapturedSource) -> RosterSource:
    return RosterSource(
        path=value.path,
        sha256=hashlib.sha256(value.raw).hexdigest(),
        raw=value.raw,
        identity=value.identity,
    )


def load_roster(root: Path) -> RosterSnapshot:
    """Capture, revalidate, parse, and freeze one coherent roster generation."""
    repository_root = Path(os.path.abspath(os.fspath(root)))
    endpoints_source = _capture_source(repository_root, ENDPOINTS_SOURCE)
    routes_source = _capture_source(repository_root, ROUTES_SOURCE)
    _revalidate_source(repository_root, endpoints_source)
    _revalidate_source(repository_root, routes_source)
    endpoints_value = _parse_toml(endpoints_source)
    routes_value = _parse_toml(routes_source)
    endpoints_generation, endpoints = _parse_endpoints(endpoints_value)
    routes_generation, routes = _parse_routes(routes_value, endpoints)
    if endpoints_generation != routes_generation:
        raise RosterError(
            "endpoints and routes roster generation values must match exactly"
        )
    return RosterSnapshot(
        endpoints=endpoints,
        routes=routes,
        generation=endpoints_generation,
        endpoints_source=_source(endpoints_source),
        routes_source=_source(routes_source),
    )


def validate_profiles(
    roster: RosterSnapshot, validator: Callable[[str, Endpoint], None]
) -> None:
    """Validate every tracked alias through provider-owned profile authority."""
    for alias, endpoint in sorted(roster.endpoints.items()):
        validator(alias, endpoint)
