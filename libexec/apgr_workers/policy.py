"""Shared worker policy parsing, profile readback, and capability resolution."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
import tomllib
from pathlib import Path
from typing import Any

from .codex_external import load_luna_profile

SCHEMA_NAME = "agent-worker-policy-v2"
SCHEMA_V1 = "agent-worker-policy-v1"
ALLOWED_SCHEMAS = frozenset({SCHEMA_NAME, SCHEMA_V1})
DEFAULT_POLICY_PATH = Path("common/dispatcher/workers.toml")


def find_default_policy_path(root: Path) -> Path:
    return DEFAULT_POLICY_PATH


# These are policy defaults only.  The tracked policy file is the normal source
# of truth and is snapshotted into a parent context when it is registered.
DEFAULT_MAX_GEMINI = 4
DEFAULT_MAX_AGGREGATE_ASTRA = 8

PARENT_FAMILIES = frozenset({"codex_parent", "claude_opus", "claude_fable", "gemini_flash"})
TASK_AUTHORITIES = frozenset({"read_only", "mutation_capable"})
WORKER_CAPABLE_MODES = frozenset({'gemini_sub', 'gemini_flash_sub', 'gemini_flash_opus_sub', 'gemini_opus', 'gemini_fable', 'claude_only', 'dynamic'})
PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
DUAL_POOL = "dual_pool_4x4"
TRIPLE_POOL = "triple_pool_4x4x4"


class WorkerPolicyError(ValueError):
    """A worker policy violates schema or contains invalid limits."""


def _qualified_flash_profile(root: Path, profile: str) -> bool:
    """Use the bundle model selection for the complete Flash High profile contract."""
    from agent_phase.runtime_models import selection, classify_parent_family

    try:
        sel = selection(root, "antigravity", profile)
        return classify_parent_family("antigravity", sel["model"]) == "gemini_flash"
    except Exception:
        return False


def load_worker_policy(
    root: Path, policy_path: Path | None = None
) -> tuple[dict[str, Any], str, str]:
    """Load and validate worker policy, returning parsed data and provenance."""
    root = Path(root).resolve()
    raw: bytes
    sha256: str
    resolved_path: Path
    rel_path: str

    if policy_path is not None:
        resolved_path = Path(policy_path)
        if not resolved_path.is_absolute():
            resolved_path = root / resolved_path
        resolved_path = resolved_path.resolve()
        try:
            raw = resolved_path.read_bytes()
        except OSError as error:
            raise WorkerPolicyError(
                f"cannot read worker policy {resolved_path}: {error}"
            ) from error
        sha256 = hashlib.sha256(raw).hexdigest()
        try:
            rel_path = resolved_path.relative_to(root).as_posix()
        except ValueError:
            rel_path = resolved_path.as_posix()
    else:
        dispatch_workers = os.environ.get("APGR_DISPATCH_WORKERS")
        if dispatch_workers:
            dispatch_path = Path(dispatch_workers)
            if not dispatch_path.is_absolute():
                raise WorkerPolicyError(
                    f"APGR_DISPATCH_WORKERS must be an absolute path: {dispatch_workers}"
                )
            expected_digest = os.environ.get("APGR_DISPATCH_WORKERS_SHA256", "")
            if not expected_digest:
                raise WorkerPolicyError(
                    "APGR_DISPATCH_WORKERS_SHA256 required when APGR_DISPATCH_WORKERS is set"
                )
            try:
                fd = os.open(dispatch_path, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(fd, "rb") as stream:
                    before = os.fstat(stream.fileno())
                    if not stat.S_ISREG(before.st_mode) or before.st_size > 256 * 1024:
                        raise WorkerPolicyError("invalid captured workers policy")
                    raw = stream.read(256 * 1024 + 1)
                    after = os.fstat(stream.fileno())
                def identity(st):
                    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                if identity(before) != identity(after):
                    raise WorkerPolicyError("captured workers policy changed")
                sha256 = hashlib.sha256(raw).hexdigest()
                if sha256 != expected_digest:
                    raise WorkerPolicyError("captured workers policy digest mismatch")
                resolved_path = dispatch_path
                try:
                    rel_path = resolved_path.relative_to(root).as_posix()
                except ValueError:
                    rel_path = resolved_path.as_posix()
            except (OSError, ValueError) as error:
                raise WorkerPolicyError(
                    f"cannot read captured workers policy {dispatch_path}: {error}"
                ) from error
        else:
            try:
                try:
                    from agent_phase.runtime_models import current_bundle
                except ImportError:
                    libexec_path = str((root / "libexec").resolve())
                    if libexec_path not in sys.path:
                        sys.path.insert(0, libexec_path)
                    from agent_phase.runtime_models import current_bundle
                bundle = current_bundle(root)
                member = bundle.members["workers.toml"]
                raw = member.raw
                sha256 = member.sha256
                resolved_path = member.path
                try:
                    rel_path = resolved_path.relative_to(root).as_posix()
                except ValueError:
                    rel_path = resolved_path.as_posix()
            except Exception as error:
                raise WorkerPolicyError(
                    f"cannot load workers.toml from current bundle: {error}"
                ) from error

    try:
        text = raw.decode("utf-8")
        if resolved_path.suffix == ".toml":
            data = tomllib.loads(text)
        elif resolved_path.suffix == ".json":
            data = json.loads(text)
        else:
            try:
                data = tomllib.loads(text)
            except Exception:
                data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
        raise WorkerPolicyError(
            f"worker policy {resolved_path} is not valid syntax: {error}"
        ) from error

    if not isinstance(data, dict):
        raise WorkerPolicyError("worker policy must be a JSON object")
    schema = data.get("schema")
    if schema not in ALLOWED_SCHEMAS:
        raise WorkerPolicyError(
            f"worker policy schema must be {SCHEMA_NAME} or {SCHEMA_V1}, got {schema}"
        )

    limits = data.get("limits")
    if not isinstance(limits, dict):
        raise WorkerPolicyError("worker policy must contain a 'limits' object")
    max_gemini = limits.get("max_gemini_workers_per_parent")
    if type(max_gemini) is not int or max_gemini <= 0:
        raise WorkerPolicyError(
            "max_gemini_workers_per_parent must be a positive integer"
        )
    max_aggregate = limits.get("max_aggregate_workers_per_codex_parent")
    if max_aggregate is None:
        max_aggregate = limits.get("max_aggregate_workers_per_codex_parent", limits.get("max_aggregate_workers_per_astra_parent"))
    if type(max_aggregate) is not int or max_aggregate <= 0:
        raise WorkerPolicyError(
            "worker aggregate limit must be a positive integer"
        )
    if max_gemini > max_aggregate:
        raise WorkerPolicyError(
            "max_gemini_workers_per_parent cannot exceed aggregate limit"
        )

    gemini_worker = data.get("gemini_worker")
    if not isinstance(gemini_worker, dict):
        raise WorkerPolicyError("worker policy must contain a 'gemini_worker' object")
    provider = gemini_worker.get("provider")
    profile = gemini_worker.get("profile")
    if provider != "antigravity":
        raise WorkerPolicyError("gemini_worker provider must be 'antigravity'")
    if not isinstance(profile, str) or not PROFILE_NAME_RE.fullmatch(profile):
        raise WorkerPolicyError("gemini_worker profile is invalid")

    return data, rel_path, sha256


def identify_parent_family(root: Path, provider: str, profile: str) -> str | None:
    """Use the selected Codex parent role and provider-specific Claude/Gemini identity."""
    if not isinstance(provider, str) or not isinstance(profile, str):
        return None
    if not PROFILE_NAME_RE.fullmatch(profile):
        return None
    root = Path(root).resolve()
    from agent_phase.runtime_models import parent_family_for_endpoint
    return parent_family_for_endpoint(root, provider, profile)


def _gemini_profile_readback(root: Path, policy_data: dict[str, Any]) -> tuple[str, str]:
    from agent_phase.runtime_models import selection
    gemini_profile = str(policy_data["gemini_worker"]["profile"])
    try:
        sel = selection(root, "antigravity", gemini_profile)
        model = sel.get("model")
        if not isinstance(model, str) or not model:
            raise WorkerPolicyError(f"Gemini worker profile {gemini_profile} lacks a model")
        return gemini_profile, model
    except WorkerPolicyError:
        raise
    except Exception as error:
        raise WorkerPolicyError(
            f"cannot read Gemini worker profile {gemini_profile}: {error}"
        ) from error


def resolve_worker_capability(
    root: Path,
    provider: str,
    profile: str,
    execution_mode: str,
    *,
    custom_policy_path: Path | None = None,
    policy_selection: str | None = None,
) -> dict[str, Any] | None:
    """Resolve a worker capability for one endpoint in one execution mode.

    The four positional arguments are intentionally strict.  Stage and
    endpoint objects belong to the routing layer and must be unpacked there.
    """
    if execution_mode not in WORKER_CAPABLE_MODES:
        return None
    parent_family = identify_parent_family(root, provider, profile)
    if parent_family is None:
        return None
    if parent_family == "gemini_flash" and execution_mode not in {
        "gemini_flash_sub",
        "gemini_flash_opus_sub",
        "dynamic",
    }:
        return None

    try:
        policy_data, rel_path, sha256 = load_worker_policy(root, custom_policy_path)
        gemini_profile, gemini_model = _gemini_profile_readback(root, policy_data)
        if parent_family == "gemini_flash" and not _qualified_flash_profile(Path(root), gemini_profile):
            raise WorkerPolicyError("Gemini Flash parent requires a qualified Flash High worker profile")
    except WorkerPolicyError as error:
        return {
            "mode": "shared-local-worker",
            "available": False,
            "allowed": False,
            "reason": str(error),
            "parent_family": parent_family,
            "policy_source": (
                str(custom_policy_path)
                if custom_policy_path is not None
                else DEFAULT_POLICY_PATH.as_posix()
            ),
        }

    policy_pool_name = policy_data.get("policy", {}).get("name")
    active_pool = policy_pool_name if policy_pool_name in {TRIPLE_POOL, DUAL_POOL} else (
        TRIPLE_POOL if TRIPLE_POOL in policy_data.get("selections", {}) else DUAL_POOL
    )
    dual_or_triple_mode = execution_mode in {'gemini_sub', 'gemini_flash_sub', 'gemini_flash_opus_sub', 'claude_only', 'dynamic'}
    selection = policy_selection or (active_pool if dual_or_triple_mode else None)
    if selection is not None:
        try:
            capability = selected_capability(root, parent_family, policy_data, rel_path, sha256, selection,
                                             allow_luna=dual_or_triple_mode)
            if parent_family == "gemini_flash":
                from agent_phase.runtime_models import selection as model_selection
                parent_selected = model_selection(root, provider, profile)
                capability.update({
                    "execution_mode": execution_mode,
                    "parent_provider": provider,
                    "parent_profile": profile,
                    "parent_model": parent_selected["model"],
                    "parent_effort": parent_selected["effort"],
                    "interface": "cli",
                    "source_root": str(Path(root).resolve()),
                })
            return capability
        except WorkerPolicyError as error:
            return {"mode": "shared-local-worker", "available": False, "allowed": False,
                    "parent_family": parent_family, "policy_selection": selection, "reason": str(error)}

    max_gemini = policy_data["limits"]["max_gemini_workers_per_parent"]
    max_aggregate = (
        policy_data["limits"].get("max_aggregate_workers_per_codex_parent", policy_data["limits"].get("max_aggregate_workers_per_astra_parent"))
        if parent_family in {"codex_parent"}
        else max_gemini
    )
    capability: dict[str, Any] = {
        "mode": "shared-local-worker",
        "available": True,
        "allowed": True,
        "parent_family": parent_family,
        "limits": {
            "max_gemini": max_gemini,
            "max_aggregate": max_aggregate,
            "max_gemini_workers_per_parent": max_gemini,
            "max_aggregate_workers_per_codex_parent": max_aggregate,
        },
        "gemini_worker": {
            "provider": "antigravity",
            "profile": gemini_profile,
            "model": gemini_model,
            "maximum_concurrency": max_gemini,
        },
        "policy_source": rel_path,
        "policy_sha256": sha256,
    }

    if parent_family in {"codex_parent"}:
        # Native Codex admission cannot be claimed from a merely configured
        # hook.  Keep the optional external Gemini path disabled for Codex parents
        # until the installed runtime has a verified admission/bind boundary.
        capability["allowed"] = False
        capability["reason"] = "native admission enforcement is not qualified"
        # Keep the native source readback in the routing owner.  Import lazily
        # so provider-free policy resolution remains usable in small fixtures.
        try:
            from agent_phase.routing import codex_worker_contract

            capability["native_worker"] = codex_worker_contract(Path(root).resolve())
        except Exception as error:  # pragma: no cover - fixture-specific source errors
            capability["native_worker"] = {"available": False, "error": str(error)}
    return capability


def selected_capability(root: Path, family: str, data: dict[str, Any], source: str,
                        digest: str, selection: str, *, allow_luna: bool = True) -> dict[str, Any]:
    """Resolve a fresh fixed-pool lifetime; legacy snapshots are never migrated."""
    from agent_phase.worker_policy_schema import parse_worker_policy
    try:
        parsed = parse_worker_policy(data)
    except ValueError as error:
        raise WorkerPolicyError(str(error)) from error
    if parsed.name != TRIPLE_POOL:
        raise WorkerPolicyError("fresh fixed-pool admission requires triple_pool_4x4x4")
    if selection != TRIPLE_POOL:
        raise WorkerPolicyError("unknown optional worker policy selection")
    selections = data.get("selections")
    if not isinstance(selections, dict):
        raise WorkerPolicyError("optional worker policy selections unavailable")
    selected = selections.get(selection)
    if not isinstance(selected, dict):
        raise WorkerPolicyError("optional worker policy selections unavailable")

    gemini_profile, gemini_model = _gemini_profile_readback(root, data)
    from agent_phase.runtime_models import selection as model_selection
    gemini_selected = model_selection(root, "antigravity", gemini_profile)

    luna = selected.get("luna_worker", {})
    if not isinstance(luna, dict):
        raise WorkerPolicyError("invalid Luna worker profile")
    luna_profile_name = luna.get("profile")
    if luna.get("provider") != "codex" or not isinstance(luna_profile_name, str) or not PROFILE_NAME_RE.fullmatch(luna_profile_name):
        raise WorkerPolicyError("invalid Luna worker profile")
    try:
        luna_profile = load_luna_profile(root, luna_profile_name)
    except (OSError, ValueError) as error:
        raise WorkerPolicyError("Luna worker profile unavailable") from error

    native = family in {"codex_parent"}

    if selection == TRIPLE_POOL:
        if (selected.get("max_gemini") != 4 or selected.get("max_luna") != 4
                or selected.get("max_sonnet") != 4 or selected.get("borrowing") is not False):
            raise WorkerPolicyError("triple_pool_4x4x4 requires independent four-slot pools without borrowing")

        sonnet = selected.get("sonnet_worker", {})
        if not isinstance(sonnet, dict):
            raise WorkerPolicyError("invalid Sonnet worker profile")
        sonnet_profile_name = sonnet.get("profile")
        if sonnet.get("provider") != "claude" or not isinstance(sonnet_profile_name, str) or not PROFILE_NAME_RE.fullmatch(sonnet_profile_name):
            raise WorkerPolicyError("invalid Sonnet worker profile")
        try:
            sonnet_selected = model_selection(root, "claude", sonnet_profile_name)
            from claude_model_catalog import load_catalog
            catalog = load_catalog(Path(root) / "claude")
            if not any(record.id == sonnet_selected["model"] for record in catalog.models.values()):
                raise WorkerPolicyError("Sonnet model is absent from the Claude catalog")
            sonnet_model, sonnet_effort = sonnet_selected["model"], sonnet_selected["effort"]
            if (sonnet_model, sonnet_effort) != ("claude-sonnet-5-5", "high"):
                raise WorkerPolicyError("Sonnet selection must be claude-sonnet-5-5/high")
        except (OSError, ValueError, KeyError) as error:
            raise WorkerPolicyError("Sonnet worker selection unavailable") from error

        # Resolve Sonnet claude_native for Claude parents, claude_external for Codex/Gemini parents.
        sonnet_transport = "claude_native" if family in {"claude_opus", "claude_fable"} else "claude_external"
        luna_transport = "codex_native" if native else "codex_external"

        # allowed_worker_kinds external facade: Codex gemini,sonnet; Claude gemini,luna; Gemini gemini,luna,sonnet.
        if family == "codex_parent":
            allowed_kinds = ["gemini", "sonnet"]
        elif family in {"claude_opus", "claude_fable"}:
            allowed_kinds = ["gemini", "luna"]
        elif family == "gemini_flash":
            allowed_kinds = ["gemini", "luna", "sonnet"]
        else:
            allowed_kinds = ["gemini"]

        return {
            "mode": "shared-local-worker",
            "available": True,
            "allowed": True,
            "parent_family": family,
            "policy_selection": selection,
            "allowed_worker_kinds": allowed_kinds,
            "limits": {
                "max_gemini": 4,
                "max_luna": 4,
                "max_sonnet": 4,
                "max_aggregate": 12,
                "max_gemini_workers_per_parent": 4,
                "max_aggregate_workers_per_codex_parent": 12,
            },
            "borrowing": False, "leaf_only": True, "parent_authority": True,
            "gemini_worker": {
                "provider": "antigravity",
                "profile": gemini_profile,
                "model": gemini_model,
                "effort": gemini_selected["effort"],
                "maximum_concurrency": 4,
            },
            "luna_worker": {
                **luna,
                "model": luna_profile.model,
                "effort": luna_profile.effort,
                "transport": luna_transport,
                "maximum_concurrency": 4,
            },
            "sonnet_worker": {
                **sonnet,
                "model": sonnet_model,
                "effort": sonnet_effort,
                "transport": sonnet_transport,
                "maximum_concurrency": 4,
            },
            "native_worker": (
                {
                    "enabled": True,
                    "default_subagent_model": luna_profile.model,
                    "default_subagent_reasoning_effort": luna_profile.effort,
                    "max_concurrent_threads_per_session": 4,
                    "occupancy_owner": "codex_runtime",
                }
                if native
                else {"enabled": True, "model": sonnet_model, "effort": sonnet_effort,
                      "cap": 4, "transport": "claude_native", "occupancy_owner": "apgr_ledger"}
                if family in {"claude_opus", "claude_fable"} else {"enabled": False}
            ),
            "policy_source": source,
            "policy_sha256": digest,
        }
