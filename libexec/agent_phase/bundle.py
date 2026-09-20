"""Dispatcher configuration bundle management (Generation 8).

This module provides complete capture, atomic projection/publication,
verification, and runtime loading for the canonical six-member dispatcher
configuration bundle:
    - models.toml
    - workers.toml
    - endpoints.toml
    - routes.toml
    - capabilities.toml
    - policy.toml
along with the authoritative bundle manifest:
    - bundle.json

Atomic Projection & Platform Limitations:
    True atomic replacement of an existing directory is performed using actual
    single-syscall directory exchange primitives:
    - Darwin (macOS): renamex_np with RENAME_SWAP
    - Linux: renameat2 with RENAME_EXCHANGE (or SYS_renameat2)
    If atomic directory exchange is unsupported by the host platform or filesystem,
    replacement publish rejects overwrite with an explicit unsupported diagnostic,
    guaranteeing there is never a rename-aside absent target window.

Precedence and Fallback:
    Runtime authority is the captured home bundle (<APGR_HOME>/dispatcher).
    Source-defaults fallback (<repo_root>/common/dispatcher) is permitted only
    when the home bundle is absent AND neither config.toml nor arguments require it.
    If dispatcher.bundle.required is set in <APGR_HOME>/config.toml, missing home
    bundle fails closed with BundleNotFoundError immediately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tomllib
from typing import Any, Mapping, NamedTuple

from .bundle_io import (
    LEGACY_MEMBERS as LEGACY_MEMBERS,
    MAX_BUNDLE_GENERATION,
    MAX_MEMBER_BYTES as MAX_MEMBER_BYTES,
    BundleError,
    BundleGenerationError,
    BundleNotFoundError,
    BundleTamperError,
    LegacyBundleError as LegacyBundleError,
    atomic_exchange_directories as atomic_exchange_directories,
    check_legacy_roster,
    check_root_directory,
    open_parent_no_follow as open_parent_no_follow,
    publish_bundle_io,
    read_home_bundle_required,
    read_member_file_strict,
    recursive_freeze,
)
from .config_routing import resolve_global_home

BUNDLE_GENERATION = 9
BUNDLE_SCHEMA = "agent-dispatcher-bundle-v1"
MANIFEST_FILENAME = "bundle.json"

BUNDLE_MEMBERS = (
    "models.toml",
    "workers.toml",
    "endpoints.toml",
    "routes.toml",
    "capabilities.toml",
    "policy.toml",
)

MEMBER_SCHEMAS: dict[str, tuple[str, ...]] = {
    "models.toml": ("agent-phase-models-v1", "agent-dispatcher-models-v1"),
    "workers.toml": ("agent-worker-policy-v2", "agent-worker-policy-v1", "agent-phase-workers-v1"),
    "endpoints.toml": ("agent-phase-endpoints-v1",),
    "routes.toml": ("agent-phase-routes-v1",),
    "capabilities.toml": ("agent-phase-capabilities-v1",),
    "policy.toml": ("agent-phase-policy-v1",),
}

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\Z")


class Endpoint(NamedTuple):
    provider: str
    profile: str


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class BundleMember:
    name: str
    path: Path
    sha256: str
    size: int
    raw: bytes = field(repr=False)
    parsed: Mapping[str, Any] = field(repr=False)
    generation: int
    schema: str


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    profile: str
    model: str
    effort: str | None
    role: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "profile": self.profile,
            "model": self.model,
            "effort": self.effort,
            "role": self.role,
        }


@dataclass(frozen=True)
class WorkerPolicySnapshot:
    name: str
    max_gemini: int
    max_luna: int
    borrowing: bool
    leaf_only: bool
    parent_authority: bool
    mode_requirements: tuple[str, ...]
    gemini_worker: Mapping[str, Any]
    luna_worker: Mapping[str, Any]
    limits: Mapping[str, Any]
    raw: Mapping[str, Any] = field(repr=False)
    max_sonnet: int | None = None
    sonnet_worker: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data = {
            "name": self.name,
            "max_gemini": self.max_gemini,
            "max_luna": self.max_luna,
            "borrowing": self.borrowing,
            "leaf_only": self.leaf_only,
            "parent_authority": self.parent_authority,
            "mode_requirements": list(self.mode_requirements),
            "gemini_worker": dict(self.gemini_worker),
            "luna_worker": dict(self.luna_worker),
            "limits": dict(self.limits),
        }
        if self.max_sonnet is not None:
            data["max_sonnet"] = self.max_sonnet
        if self.sonnet_worker:
            data["sonnet_worker"] = dict(self.sonnet_worker)
        return data


@dataclass(frozen=True)
class DispatcherBundleSnapshot:
    generation: int
    bundle_dir: Path
    members: Mapping[str, BundleMember]
    manifest: Mapping[str, Any]
    models_catalog: Mapping[str, Any]
    worker_policy: WorkerPolicySnapshot
    endpoints: Mapping[str, Endpoint]
    routes: Mapping[tuple[str, str], Mapping[str, str]]
    capabilities: Mapping[str, Any]
    policy: Mapping[str, Any]

    def select_model(self, provider: str, profile: str) -> ModelSelection:
        """Select model and effort for a provider profile from the immutable models catalog.

        Rejects invalid referenced model IDs, types, and effort without coercion.
        Does not enforce whole unused inventory catalog equality gates.
        """
        if type(provider) is not str or not provider:
            raise BundleError(f"provider must be a non-empty string, got {provider!r}")
        if type(profile) is not str or not profile:
            raise BundleError(f"profile must be a non-empty string, got {profile!r}")

        providers = self.models_catalog.get("providers")
        if isinstance(providers, Mapping):
            provider_table = providers.get(provider)
            if isinstance(provider_table, Mapping):
                entry = provider_table.get(profile)
                if isinstance(entry, Mapping) and "model" in entry:
                    model_val = entry["model"]
                    if type(model_val) is not str or not model_val:
                        raise BundleError(
                            f"invalid model ID in models.toml for provider {provider!r} and profile {profile!r}: {model_val!r}"
                        )
                    effort_val = entry.get("effort")
                    if effort_val is not None and (type(effort_val) is not str or not effort_val):
                        raise BundleError(
                            f"invalid effort in models.toml for provider {provider!r} and profile {profile!r}: {effort_val!r}"
                        )
                    role_val = entry.get("role")
                    if role_val is not None and (type(role_val) is not str or not role_val):
                        raise BundleError(
                            f"invalid role in models.toml for provider {provider!r} and profile {profile!r}: {role_val!r}"
                        )
                    return ModelSelection(
                        provider=provider,
                        profile=profile,
                        model=model_val,
                        effort=effort_val,
                        role=role_val,
                    )

        # Fallback to roles catalog
        roles = self.models_catalog.get("roles")
        if isinstance(roles, Mapping):
            provider_roles = roles.get(provider)
            if isinstance(provider_roles, Mapping) and profile in provider_roles:
                role_model = provider_roles[profile]
                if type(role_model) is not str or not role_model:
                    raise BundleError(
                        f"invalid model ID for role {profile!r} in models.toml: {role_model!r}"
                    )
                return ModelSelection(
                    provider=provider,
                    profile=profile,
                    model=role_model,
                    effort=None,
                    role=profile,
                )

        raise BundleError(
            f"no model mapping found in models.toml for provider {provider!r} and profile {profile!r}"
        )

    def select_role_model(self, provider: str, role: str) -> str:
        """Look up default model for a named role from the immutable models catalog."""
        if type(provider) is not str or not provider:
            raise BundleError(f"provider must be a non-empty string, got {provider!r}")
        if type(role) is not str or not role:
            raise BundleError(f"role must be a non-empty string, got {role!r}")

        roles = self.models_catalog.get("roles")
        if isinstance(roles, Mapping):
            provider_roles = roles.get(provider)
            if isinstance(provider_roles, Mapping) and role in provider_roles:
                model_val = provider_roles[role]
                if type(model_val) is not str or not model_val:
                    raise BundleError(
                        f"invalid model ID for role {role!r} in models.toml: {model_val!r}"
                    )
                return model_val
        raise BundleError(
            f"no role mapping found in models.toml for provider {provider!r} and role {role!r}"
        )

    def get_worker_policy(self) -> WorkerPolicySnapshot:
        """Return the immutable worker policy snapshot."""
        return self.worker_policy

    def get_endpoint(self, alias: str) -> Endpoint:
        """Return the endpoint for an alias."""
        endpoint = self.endpoints.get(alias)
        if endpoint is None:
            raise BundleError(f"unknown endpoint alias: {alias!r}")
        return endpoint

    def route_aliases(self, phase_type: str, execution_mode: str) -> dict[str, str]:
        """Return slot -> endpoint_alias mapping for a phase type and execution mode."""
        key = (phase_type, execution_mode)
        aliases = self.routes.get(key)
        if aliases is None:
            raise BundleError(f"no route found in bundle for {key}")
        return dict(aliases)

    def route_endpoints(self, phase_type: str, execution_mode: str) -> dict[str, Endpoint]:
        """Return slot -> Endpoint mapping for a phase type and execution mode."""
        aliases = self.route_aliases(phase_type, execution_mode)
        return {slot: self.get_endpoint(alias) for slot, alias in aliases.items()}

    def validate_mode_requirements(self, mode: str) -> bool:
        """Check if an execution mode meets the worker policy mode requirements."""
        return mode in self.worker_policy.mode_requirements

    def provenance(self) -> dict[str, Any]:
        """Return structured provenance evidence for this bundle snapshot."""
        return {
            "schema": "agent-dispatcher-bundle-provenance-v1",
            "generation": self.generation,
            "bundle_dir": str(self.bundle_dir),
            "authority": self.manifest.get("authority", "source_default"),
            "manifest_sha256": hashlib.sha256(
                json.dumps(_plain(self.manifest), sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "members": {
                name: {
                    "sha256": member.sha256,
                    "size": member.size,
                    "schema": member.schema,
                }
                for name, member in sorted(self.members.items())
            },
        }


def capture_member_file(
    root: Path,
    member_name: str,
    *,
    expected_generation: int | None = None,
) -> BundleMember:
    """Capture one bundle member file strictly verifying no-follow, permissions, schema, and generation."""
    raw_bytes, sha256, size = read_member_file_strict(root, member_name)

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BundleError(f"bundle member {member_name} is not valid UTF-8: {error}") from error

    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise BundleError(f"bundle member {member_name} is not valid TOML: {error}") from error

    if not isinstance(parsed, Mapping):
        raise BundleError(f"bundle member {member_name} must be a TOML table")

    # Schema verification
    schema = parsed.get("schema")
    if not isinstance(schema, str):
        raise BundleError(f"bundle member {member_name} missing 'schema' field")
    allowed_schemas = MEMBER_SCHEMAS.get(member_name, ())
    if schema not in allowed_schemas:
        raise BundleError(
            f"bundle member {member_name} schema {schema!r} not in allowed schemas: {allowed_schemas}"
        )

    # Generation verification
    gen = parsed.get("generation")
    if type(gen) is not int or type(gen) is bool or not (1 <= gen <= MAX_BUNDLE_GENERATION):
        raise BundleGenerationError(
            f"bundle member {member_name} generation must be a positive bounded integer, got {gen!r}"
        )
    if expected_generation is not None and gen != expected_generation:
        raise BundleGenerationError(
            f"bundle member {member_name} generation mismatch: expected {expected_generation}, got {gen}"
        )

    return BundleMember(
        name=member_name,
        path=root / member_name,
        sha256=sha256,
        size=size,
        raw=raw_bytes,
        parsed=recursive_freeze(parsed),
        generation=gen,
        schema=schema,
    )


def _capture_identities(directory: Path, names: tuple[str, ...]) -> dict:
    """Fence the complete set before reading any member, then revalidate it."""
    from .bundle_io import PhysicalIdentity
    try:
        return {name: PhysicalIdentity.from_stat(os.stat(directory / name, follow_symlinks=False))
                for name in (".", *names)}
    except OSError as error:
        raise BundleError(f"cannot capture bundle identity: {error}") from error


def _revalidate_identities(directory: Path, identities: dict) -> None:
    current = _capture_identities(directory, tuple(name for name in identities if name != "."))
    if current != identities:
        raise BundleError("bundle source changed during capture (set identity)")


def capture_bundle(
    source_dir: Path,
    *,
    expected_generation: int | None = None,
    authority: str | None = None,
) -> tuple[dict[str, BundleMember], dict[str, Any]]:
    """Capture and validate all six canonical bundle members from source_dir."""
    check_root_directory(source_dir)
    check_legacy_roster(source_dir)

    for m in BUNDLE_MEMBERS:
        m_path = source_dir / m
        try:
            st = os.lstat(m_path)
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
                raise BundleError(f"bundle member {m} in {source_dir} is not a regular file")
        except FileNotFoundError:
            raise BundleError(f"incomplete dispatcher bundle in {source_dir}: missing member {m}")

    identities = _capture_identities(source_dir, BUNDLE_MEMBERS)
    members: dict[str, BundleMember] = {}
    for member_name in BUNDLE_MEMBERS:
        member = capture_member_file(source_dir, member_name, expected_generation=expected_generation)
        members[member_name] = member

    _revalidate_identities(source_dir, identities)

    # Verify generation coherence across all captured members
    generations = {m.generation for m in members.values()}
    if len(generations) != 1:
        raise BundleGenerationError(
            f"partial generation detected in {source_dir}: members have differing generations: "
            f"{ {name: m.generation for name, m in members.items()} }"
        )
    coherent_gen = generations.pop()
    if expected_generation is not None and coherent_gen != expected_generation:
        raise BundleGenerationError(
            f"bundle generation mismatch: expected {expected_generation}, got {coherent_gen}"
        )

    manifest = create_bundle_manifest(members, generation=coherent_gen, authority=authority)

    # Strictly validate worker policy and tables
    _parse_worker_policy(members["workers.toml"].parsed)
    _parse_endpoints_data(members["endpoints.toml"].parsed)
    _parse_routes_data(members["routes.toml"].parsed)

    return members, manifest


def create_bundle_manifest(
    members: Mapping[str, BundleMember],
    *,
    generation: int = BUNDLE_GENERATION,
    authority: str | None = None,
) -> dict[str, Any]:
    """Construct the authoritative bundle.json manifest dictionary."""
    files: dict[str, Any] = {}
    for name in BUNDLE_MEMBERS:
        member = members[name]
        files[name] = {
            "sha256": member.sha256,
            "bytes": member.size,
            "schema": member.schema,
        }
    manifest: dict[str, Any] = {
        "schema": BUNDLE_SCHEMA,
        "generation": generation,
        "files": files,
    }
    if authority is not None:
        manifest["authority"] = authority
        manifest["source_default"] = (authority == "source_default")
    return manifest


def verify_bundle(
    bundle_dir: Path,
    *,
    expected_generation: int | None = None,
) -> dict[str, Any]:
    """Verify integrity, manifest hashes, and generation coherence of a published bundle.

    Single-pass validation: computes hash from read bytes and compares to manifest.
    """
    check_root_directory(bundle_dir)
    _root_identity = os.stat(bundle_dir, follow_symlinks=False)
    check_legacy_roster(bundle_dir)

    manifest_path = bundle_dir / MANIFEST_FILENAME
    try:
        st = os.lstat(manifest_path)
    except FileNotFoundError:
        raise BundleTamperError(f"authoritative {MANIFEST_FILENAME} manifest missing in {bundle_dir}")
    except OSError as error:
        raise BundleTamperError(f"cannot access {manifest_path}: {error}") from error

    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise BundleTamperError(f"manifest {MANIFEST_FILENAME} missing or symlinked in {bundle_dir}")

    _identities = _capture_identities(bundle_dir, (*BUNDLE_MEMBERS, MANIFEST_FILENAME))
    try:
        manifest_raw, _, _ = read_member_file_strict(bundle_dir, MANIFEST_FILENAME)
        manifest_data = json.loads(manifest_raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BundleTamperError(f"unusable {MANIFEST_FILENAME} in {bundle_dir}: {error}") from error

    if not isinstance(manifest_data, Mapping):
        raise BundleTamperError(f"{MANIFEST_FILENAME} must be a JSON object")

    manifest_schema = manifest_data.get("schema")
    if manifest_schema != BUNDLE_SCHEMA:
        raise BundleTamperError(
            f"{MANIFEST_FILENAME} schema mismatch: expected {BUNDLE_SCHEMA}, got {manifest_schema!r}"
        )

    manifest_gen = manifest_data.get("generation")
    if type(manifest_gen) is not int or type(manifest_gen) is bool or not (1 <= manifest_gen <= MAX_BUNDLE_GENERATION):
        raise BundleGenerationError(
            f"{MANIFEST_FILENAME} generation must be a positive bounded integer, got {manifest_gen!r}"
        )
    if expected_generation is not None and manifest_gen != expected_generation:
        raise BundleGenerationError(
            f"{MANIFEST_FILENAME} generation mismatch: expected {expected_generation}, got {manifest_gen!r}"
        )

    manifest_files = manifest_data.get("files") or manifest_data.get("members")
    if not isinstance(manifest_files, Mapping):
        raise BundleTamperError(f"{MANIFEST_FILENAME} missing 'files' mapping")

    missing = [name for name in BUNDLE_MEMBERS if name not in manifest_files]
    if missing:
        raise BundleTamperError(f"{MANIFEST_FILENAME} is missing required members: {sorted(missing)}")

    for member_name in BUNDLE_MEMBERS:
        raw_bytes, actual_sha256, _ = read_member_file_strict(bundle_dir, member_name)

        entry = manifest_files.get(member_name)
        if isinstance(entry, Mapping):
            expected_sha256 = entry.get("sha256")
        elif isinstance(entry, str):
            expected_sha256 = entry
        else:
            raise BundleTamperError(f"invalid manifest entry for {member_name}")

        if actual_sha256 != expected_sha256:
            raise BundleTamperError(
                f"manifest tamper: SHA-256 mismatch for {member_name} "
                f"(expected {expected_sha256}, got {actual_sha256})"
            )

        try:
            parsed = tomllib.loads(raw_bytes.decode("utf-8"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
            raise BundleTamperError(f"bundle member {member_name} is invalid TOML/UTF-8: {error}") from error

        file_gen = parsed.get("generation")
        if file_gen != manifest_gen:
            raise BundleGenerationError(
                f"generation mismatch in {member_name}: expected {manifest_gen}, got {file_gen!r}"
            )

    return manifest_data


def publish_bundle(
    source_dir: Path,
    target_dir: Path,
    *,
    expected_generation: int | None = None,
) -> DispatcherBundleSnapshot:
    """Atomically project and publish a six-member bundle to target_dir.

    Implements staging-directory creation on the same filesystem and atomic replacement
    via atomic exchange (Darwin renamex_np / Linux renameat2), fully eliminating any
    absent target window. Rejects overwrite on unsupported platforms.
    """
    check_root_directory(source_dir)
    authority = "home" if target_dir.name == "dispatcher" else "override"
    members, manifest = capture_bundle(
        source_dir, expected_generation=expected_generation, authority=authority
    )

    publish_bundle_io(target_dir, members, manifest)

    target_members: dict[str, BundleMember] = {
        name: BundleMember(
            name=m.name,
            path=target_dir / m.name,
            sha256=m.sha256,
            size=m.size,
            raw=m.raw,
            parsed=m.parsed,
            generation=m.generation,
            schema=m.schema,
        )
        for name, m in members.items()
    }
    return _build_snapshot(
        target_dir, target_members, manifest, manifest["generation"], authority=authority
    )


def _parse_worker_policy(raw_policy: Mapping[str, Any]) -> WorkerPolicySnapshot:
    from .worker_policy_schema import parse_worker_policy
    return parse_worker_policy(raw_policy)


def _parse_endpoints_data(raw_endpoints: Mapping[str, Any]) -> dict[str, Endpoint]:
    table = raw_endpoints.get("endpoints")
    if not isinstance(table, Mapping):
        return {}
    result: dict[str, Endpoint] = {}
    for alias, entry in table.items():
        if isinstance(entry, Mapping) and "provider" in entry and "profile" in entry:
            provider = entry["provider"]
            profile = entry["profile"]
            if type(provider) is not str or not provider or type(profile) is not str or not profile:
                raise BundleError(f"invalid endpoint entry for alias {alias!r}")
            result[alias] = Endpoint(provider, profile)
    return result


def _parse_routes_data(raw_routes: Mapping[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    table = raw_routes.get("routes")
    if not isinstance(table, Mapping):
        return {}
    result: dict[tuple[str, str], dict[str, str]] = {}
    for phase_type, modes in table.items():
        if isinstance(modes, Mapping):
            for mode, slots in modes.items():
                if isinstance(slots, Mapping):
                    slot_map: dict[str, str] = {}
                    for slot, alias in slots.items():
                        if type(alias) is not str or not alias:
                            raise BundleError(f"invalid route alias for {phase_type}.{mode}.{slot}: {alias!r}")
                        slot_map[slot] = alias
                    result[(phase_type, mode)] = slot_map
    return result


def _single_pass_load_dir(
    bundle_dir: Path,
    expected_generation: int | None = None,
) -> tuple[dict[str, BundleMember], dict[str, Any], int]:
    """Read manifest and all bundle members in a single pass verifying hashes without TOCTOU."""
    check_root_directory(bundle_dir)
    _root_identity = os.stat(bundle_dir, follow_symlinks=False)
    check_legacy_roster(bundle_dir)

    manifest_path = bundle_dir / MANIFEST_FILENAME
    try:
        st = os.lstat(manifest_path)
    except FileNotFoundError:
        raise BundleTamperError(f"authoritative {MANIFEST_FILENAME} manifest missing in {bundle_dir}")
    except OSError as error:
        raise BundleTamperError(f"cannot access {manifest_path}: {error}") from error

    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise BundleTamperError(f"manifest {MANIFEST_FILENAME} missing or symlinked in {bundle_dir}")

    _identities = _capture_identities(bundle_dir, (*BUNDLE_MEMBERS, MANIFEST_FILENAME))
    try:
        manifest_raw, _, _ = read_member_file_strict(bundle_dir, MANIFEST_FILENAME)
        manifest_data = json.loads(manifest_raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BundleTamperError(f"unusable {MANIFEST_FILENAME} in {bundle_dir}: {error}") from error

    if not isinstance(manifest_data, Mapping):
        raise BundleTamperError(f"{MANIFEST_FILENAME} must be a JSON object")

    manifest_schema = manifest_data.get("schema")
    if manifest_schema != BUNDLE_SCHEMA:
        raise BundleTamperError(
            f"{MANIFEST_FILENAME} schema mismatch: expected {BUNDLE_SCHEMA}, got {manifest_schema!r}"
        )

    manifest_gen = manifest_data.get("generation")
    if type(manifest_gen) is not int or type(manifest_gen) is bool or not (1 <= manifest_gen <= MAX_BUNDLE_GENERATION):
        raise BundleGenerationError(
            f"{MANIFEST_FILENAME} generation must be a positive bounded integer, got {manifest_gen!r}"
        )
    if expected_generation is not None and manifest_gen != expected_generation:
        raise BundleGenerationError(
            f"{MANIFEST_FILENAME} generation mismatch: expected {expected_generation}, got {manifest_gen!r}"
        )

    manifest_files = manifest_data.get("files") or manifest_data.get("members")
    if not isinstance(manifest_files, Mapping):
        raise BundleTamperError(f"{MANIFEST_FILENAME} missing 'files' mapping")

    missing = [name for name in BUNDLE_MEMBERS if name not in manifest_files]
    if missing:
        raise BundleTamperError(f"{MANIFEST_FILENAME} is missing required members: {sorted(missing)}")

    members: dict[str, BundleMember] = {}
    for member_name in BUNDLE_MEMBERS:
        member = capture_member_file(bundle_dir, member_name, expected_generation=manifest_gen)
        entry = manifest_files.get(member_name)
        if isinstance(entry, Mapping):
            expected_sha256 = entry.get("sha256")
        elif isinstance(entry, str):
            expected_sha256 = entry
        else:
            raise BundleTamperError(f"invalid manifest entry for {member_name}")

        if member.sha256 != expected_sha256:
            raise BundleTamperError(
                f"manifest tamper: SHA-256 mismatch for {member_name} "
                f"(expected {expected_sha256}, got {member.sha256})"
            )
        members[member_name] = member

    # Strictly validate worker policy and tables
    _parse_worker_policy(members["workers.toml"].parsed)
    _parse_endpoints_data(members["endpoints.toml"].parsed)
    _parse_routes_data(members["routes.toml"].parsed)

    _revalidate_identities(bundle_dir, _identities)
    current = os.stat(bundle_dir, follow_symlinks=False)
    if (current.st_dev, current.st_ino) != (_root_identity.st_dev, _root_identity.st_ino):
        raise BundleTamperError("bundle directory changed during capture")
    return members, manifest_data, manifest_gen


def load_bundle(
    apgr_home: Path | str | None = None,
    repo_root: Path | str | None = None,
    *,
    required: bool | None = None,
    target_override: Path | None = None,
    expected_generation: int | None = None,
) -> DispatcherBundleSnapshot:
    """Load the immutable dispatcher bundle snapshot.

    Precedence:
    1. Explicit target_override (if provided).
    2. Authoritative captured home bundle (<APGR_HOME>/dispatcher).
    3. Source defaults (<repo_root>/common/dispatcher) IF home bundle is absent AND neither
       parameter required nor <APGR_HOME>/config.toml dispatcher.bundle.required is True.
    """
    if required is not None and type(required) is not bool:
        raise BundleError(f"required must be a boolean or None, got {required!r}")

    effective_root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )

    if target_override is not None:
        bundle_dir = Path(target_override)
        members, manifest, gen = _single_pass_load_dir(bundle_dir, expected_generation=expected_generation)
        return _build_snapshot(bundle_dir, members, manifest, gen, authority="override")

    effective_home = resolve_global_home(apgr_home)
    home_config_required = read_home_bundle_required(effective_home)
    is_required = (required is True) or (home_config_required is True)

    home_bundle_dir = effective_home / "dispatcher"
    home_bundle_exists = False
    try:
        st = os.lstat(home_bundle_dir)
        if stat.S_ISLNK(st.st_mode):
            raise BundleError(f"home bundle directory is a symlink: {home_bundle_dir}")
        if not stat.S_ISDIR(st.st_mode):
            raise BundleError(f"home bundle is not a directory: {home_bundle_dir}")
        home_bundle_exists = True
    except FileNotFoundError:
        home_bundle_exists = False

    if home_bundle_exists:
        members, manifest, gen = _single_pass_load_dir(home_bundle_dir, expected_generation=expected_generation)
        return _build_snapshot(home_bundle_dir, members, manifest, gen, authority="home")

    if is_required:
        raise BundleNotFoundError(
            f"authoritative home dispatcher bundle not found at {home_bundle_dir} and bundle is required"
        )

    # Fallback to source defaults in common/dispatcher
    source_defaults_dir = effective_root / "common" / "dispatcher"
    if source_defaults_dir.resolve() != source_defaults_dir:
        raise BundleError("symlinked ancestor in source dispatcher bundle")
    check_root_directory(source_defaults_dir)
    check_legacy_roster(source_defaults_dir)

    members, manifest = capture_bundle(
        source_defaults_dir,
        expected_generation=expected_generation,
        authority="source_default",
    )
    return _build_snapshot(
        source_defaults_dir,
        members,
        manifest,
        manifest["generation"],
        authority="source_default",
    )


def _build_snapshot(
    bundle_dir: Path,
    members: Mapping[str, BundleMember],
    manifest: Mapping[str, Any],
    generation: int,
    authority: str = "source_default",
) -> DispatcherBundleSnapshot:
    """Freeze parsed bundle members into a truly immutable DispatcherBundleSnapshot."""
    models_catalog = members["models.toml"].parsed
    workers_raw = members["workers.toml"].parsed
    endpoints_raw = members["endpoints.toml"].parsed
    routes_raw = members["routes.toml"].parsed
    capabilities_raw = members["capabilities.toml"].parsed
    policy_raw = members["policy.toml"].parsed

    worker_policy = _parse_worker_policy(workers_raw)
    endpoints = _parse_endpoints_data(endpoints_raw)
    routes = _parse_routes_data(routes_raw)

    manifest_dict = dict(manifest)
    manifest_dict.setdefault("authority", authority)
    manifest_dict.setdefault("source_default", (authority == "source_default"))

    frozen_members = recursive_freeze(dict(members))
    frozen_manifest = recursive_freeze(manifest_dict)
    frozen_models = recursive_freeze(dict(models_catalog))
    frozen_endpoints = recursive_freeze(endpoints)
    frozen_routes = recursive_freeze(routes)
    frozen_capabilities = recursive_freeze(dict(capabilities_raw))
    frozen_policy = recursive_freeze(dict(policy_raw))

    return DispatcherBundleSnapshot(
        generation=generation,
        bundle_dir=bundle_dir,
        members=frozen_members,
        manifest=frozen_manifest,
        models_catalog=frozen_models,
        worker_policy=worker_policy,
        endpoints=frozen_endpoints,
        routes=frozen_routes,
        capabilities=frozen_capabilities,
        policy=frozen_policy,
    )


def require_fresh_bundle(bundle):
    """Retained generations may be read; new dispatches require current authority."""
    gen = getattr(bundle, "generation", None)
    policy = getattr(bundle, "worker_policy", None)
    policy_name = getattr(policy, "name", None)
    if (
        bundle is None
        or type(gen) is not int
        or gen < BUNDLE_GENERATION
        or policy_name != "triple_pool_4x4x4"
    ):
        raise BundleGenerationError(
            "fresh dispatch requires generation >= 9 and triple_pool_4x4x4; reproject or resume under the pinned controller generation"
        )
