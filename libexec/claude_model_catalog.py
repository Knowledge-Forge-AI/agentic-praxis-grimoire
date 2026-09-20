#!/usr/bin/env python3
"""Strict Claude model catalog loader and compatibility probe."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, NamedTuple, Sequence

CATALOG_SCHEMA = "agent-central-claude-model-catalog-v1"
CATALOG_RELATIVE_PATH = "claude/model-catalog-v1.json"
DOCTOR_SCHEMA = "agent-central-claude-profile-doctor-v1"

SUPPORTED_ROLES = frozenset({"primary", "review"})
REQUIRED_TOP_LEVEL_KEYS = frozenset({"schema", "roles", "models"})
ALLOWED_MODEL_KEYS = frozenset({"id", "minimumClaudeCodeVersion", "adaptiveThinking"})

_ROLE_IDENTIFIER_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_CLAUDE_MODEL_ID_RE = re.compile(r"^claude-(opus|sonnet|haiku|fable)-[0-9]+(-[0-9]+)*$")
_VERSION_RE = re.compile(r"^[0-9]+(\.[0-9]+)+$")
_VERSION_PROBE_RE = re.compile(r"(\d+(?:\.\d+)+)")


class CatalogError(RuntimeError):
    """The model catalog violates validation or integrity requirements."""


class CatalogProvenance(NamedTuple):
    schema: str
    relativePath: str
    bytes: int
    sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "relativePath": self.relativePath,
            "bytes": self.bytes,
            "sha256": self.sha256,
        }


class ModelRecord(NamedTuple):
    id: str
    minimum_claude_code_version: str | None = None
    adaptive_thinking: bool = False


class CatalogData(NamedTuple):
    schema: str
    roles: dict[str, str]
    models: dict[str, ModelRecord]
    provenance: CatalogProvenance


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def locate_catalog_file(root_or_path: Path) -> Path:
    if root_or_path.is_symlink() or root_or_path.is_file():
        return root_or_path
    candidate_direct = root_or_path / "model-catalog-v1.json"
    if candidate_direct.is_symlink() or candidate_direct.is_file():
        return candidate_direct
    candidate_sub = root_or_path / "claude" / "model-catalog-v1.json"
    if candidate_sub.is_symlink() or candidate_sub.is_file():
        return candidate_sub
    return root_or_path / CATALOG_RELATIVE_PATH


def load_catalog(root_or_path: Path) -> CatalogData:
    path = locate_catalog_file(root_or_path)
    if path.is_symlink():
        raise CatalogError(f"catalog must not be a symlink: {path}")
    if not path.is_file():
        raise CatalogError(f"catalog file not found: {path}")

    try:
        raw_bytes = path.read_bytes()
    except OSError as error:
        raise CatalogError(f"unable to read catalog file {path}: {error}") from error

    byte_count = len(raw_bytes)
    sha256_digest = hashlib.sha256(raw_bytes).hexdigest()

    try:
        decoded_text = raw_bytes.decode("utf-8")
        parsed = json.loads(decoded_text, object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CatalogError(f"invalid catalog JSON {path}: {error}") from error

    if not isinstance(parsed, dict):
        raise CatalogError(f"catalog root must be an object: {path}")

    actual_keys = set(parsed)
    if actual_keys != REQUIRED_TOP_LEVEL_KEYS:
        raise CatalogError(
            f"catalog keys must be exactly {sorted(REQUIRED_TOP_LEVEL_KEYS)}, got {sorted(actual_keys)}"
        )

    if parsed["schema"] != CATALOG_SCHEMA:
        raise CatalogError(
            f"unsupported catalog schema: {parsed['schema']!r}, expected {CATALOG_SCHEMA!r}"
        )

    roles_raw = parsed["roles"]
    if not isinstance(roles_raw, dict):
        raise CatalogError("catalog roles must be an object")

    if set(roles_raw) != SUPPORTED_ROLES:
        raise CatalogError(
            f"catalog roles must have exact keys {sorted(SUPPORTED_ROLES)}, got {sorted(roles_raw)}"
        )

    roles: dict[str, str] = {}
    for role_name, model_key in roles_raw.items():
        if not isinstance(model_key, str) or not _ROLE_IDENTIFIER_RE.match(model_key):
            raise CatalogError(
                f"invalid model identifier {model_key!r} for role {role_name!r}"
            )
        roles[role_name] = model_key

    models_raw = parsed["models"]
    if not isinstance(models_raw, dict):
        raise CatalogError("catalog models must be an object")

    expected_model_keys = set(roles.values())
    if set(models_raw) != expected_model_keys:
        raise CatalogError(
            f"catalog models must match active referenced roles {sorted(expected_model_keys)}, "
            f"got {sorted(models_raw)}"
        )

    models: dict[str, ModelRecord] = {}
    seen_model_ids: set[str] = set()

    for model_key, model_data in models_raw.items():
        if not isinstance(model_data, dict):
            raise CatalogError(f"model record {model_key!r} must be an object")
        entry_keys = set(model_data)
        if not entry_keys.issubset(ALLOWED_MODEL_KEYS) or "id" not in entry_keys:
            raise CatalogError(
                f"model record {model_key!r} has invalid keys: {sorted(entry_keys)}"
            )

        model_id = model_data["id"]
        if not isinstance(model_id, str) or not _CLAUDE_MODEL_ID_RE.match(model_id):
            raise CatalogError(f"invalid Claude model ID {model_id!r} in {model_key!r}")

        if model_id == "claude-fable-5":
            raise CatalogError(
                f"legacy model ID 'claude-fable-5' is prohibited in active catalog ({model_key})"
            )

        if model_id in seen_model_ids:
            raise CatalogError(f"duplicate model ID {model_id!r} in catalog")
        seen_model_ids.add(model_id)

        min_version: str | None = None
        if "minimumClaudeCodeVersion" in model_data:
            min_version = model_data["minimumClaudeCodeVersion"]
            if not isinstance(min_version, str) or not _VERSION_RE.match(min_version):
                raise CatalogError(
                    f"invalid minimum Claude Code version {min_version!r} in {model_key!r}"
                )

        adaptive_thinking = False
        if "adaptiveThinking" in model_data:
            adaptive_thinking = model_data["adaptiveThinking"]
            if not isinstance(adaptive_thinking, bool):
                raise CatalogError(
                    f"adaptiveThinking must be a boolean in {model_key!r}"
                )

        models[model_key] = ModelRecord(
            id=model_id,
            minimum_claude_code_version=min_version,
            adaptive_thinking=adaptive_thinking,
        )

    provenance = CatalogProvenance(
        schema=CATALOG_SCHEMA,
        relativePath=CATALOG_RELATIVE_PATH,
        bytes=byte_count,
        sha256=sha256_digest,
    )
    return CatalogData(
        schema=CATALOG_SCHEMA,
        roles=roles,
        models=models,
        provenance=provenance,
    )


def resolve_role(catalog: CatalogData, role: str) -> dict[str, Any]:
    if role not in catalog.roles:
        raise CatalogError(f"unknown catalog role: {role!r}")
    model_key = catalog.roles[role]
    record = catalog.models[model_key]
    return {
        "model_role": role,
        "model_key": model_key,
        "resolved_model_id": record.id,
        "minimum_claude_code_version": record.minimum_claude_code_version,
        "adaptive_thinking": record.adaptive_thinking,
        "catalog": catalog.provenance.as_dict(),
    }


def parse_version(version_str: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version_str.split("."))
    except ValueError as error:
        raise CatalogError(f"malformed version component in {version_str!r}") from error


def is_version_compatible(observed: str | None, required: str | None) -> bool:
    if required is None:
        return True
    if observed is None:
        return False
    return parse_version(observed) >= parse_version(required)


def probe_claude_version(
    executable: str | Path | None = None,
) -> tuple[str | None, str]:
    if executable is None:
        executable = shutil.which("claude")
    if executable is None:
        return None, "unavailable"

    cmd = [os.fspath(executable), "--version"]
    clean_env = {
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", ""),
    }

    try:
        completed = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=5.0,
            text=True,
            env=clean_env,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, "unavailable"

    if completed.returncode != 0:
        return None, "unavailable"

    match = _VERSION_PROBE_RE.search(completed.stdout)
    if not match:
        return None, "unavailable"

    return match.group(1), "available"


def run_doctor(
    root: Path,
    profile_names: Sequence[str] | None = None,
    executable: str | Path | None = None,
) -> tuple[dict[str, Any], int]:
    catalog = load_catalog(root)
    observed_version, probe_status = probe_claude_version(executable)

    # Import profile definitions from claude_vc_profile
    import claude_vc_profile

    if profile_names is None:
        selected_profiles = sorted(claude_vc_profile.SUPPORTED_PROFILES)
    else:
        selected_profiles = list(profile_names)

    profiles_report: list[dict[str, Any]] = []
    has_failure = False

    for profile_name in selected_profiles:
        if profile_name not in claude_vc_profile.SUPPORTED_PROFILES:
            raise claude_vc_profile.ProfileError(f"unsupported profile: {profile_name}")

        contract = claude_vc_profile.PROFILE_CONTRACTS[profile_name]
        resolution = resolve_role(catalog, contract.model_role)
        required_version = resolution["minimum_claude_code_version"]

        if required_version is None:
            compatibility = "not-required"
        elif probe_status != "available" or observed_version is None:
            compatibility = "unavailable"
            has_failure = True
        elif is_version_compatible(observed_version, required_version):
            compatibility = "compatible"
        else:
            compatibility = "incompatible"
            has_failure = True

        profiles_report.append(
            {
                "profile": profile_name,
                "modelRole": contract.model_role,
                "resolvedModelId": resolution["resolved_model_id"],
                "requiredClaudeCodeVersion": required_version,
                "compatibilityStatus": compatibility,
            }
        )

    doctor_document = {
        "schema": DOCTOR_SCHEMA,
        "catalog": catalog.provenance.as_dict(),
        "observedClaudeCodeVersion": observed_version,
        "probeStatus": probe_status,
        "profiles": profiles_report,
    }

    exit_code = 1 if has_failure else 0
    return doctor_document, exit_code
