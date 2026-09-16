"""Pure resolution of a phase request into a routed phase plan.

Resolution launches nothing, mutates nothing, and never inspects model prose.

The tracked roster stores provider and profile only. Model and effort are
deliberately absent: each provider's profile source is already the authority for
them, and a second copy here would be a competing source of truth. The resolved
document instead carries a *derived* `intelligence` block read back from that
authority. Codex parent intelligence remains scoped to the two profile keys;
the conserve route additionally attests the separate repository-owned worker
source without copying worker settings into any parent profile.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import tomllib
from typing import Any

from .lifecycle import (
    FINALIZATION_PUBLISH,
    LIFECYCLE_STANDARD,
    LifecycleSpec,
    get_lifecycle,
    validate_finalization,
)
from .request import PhaseRequest
from .roster import (
    Endpoint,
    RosterError,
    RosterSnapshot,
    load_roster,
    validate_profiles,
)


from .route_provenance import RESOLVED_V6, build_fresh_effective_routes
from .worker_capability import resolve_worker_capability

RESOLVED_SCHEMA = RESOLVED_V6
# Compatibility exports describe the default lifecycle. Operator-selected
# lifecycle is deliberately outside the semantic request, whose prose and
# fields cannot grant or reduce review authority.
_STANDARD = get_lifecycle(LIFECYCLE_STANDARD)
CHECKPOINTS = _STANDARD.checkpoints
CHECKPOINT_COUNT = _STANDARD.expected_review_count
PROVIDER_INVOCATIONS = _STANDARD.expected_provider_invocations

PROVIDER_CLAUDE = "claude"
PROVIDER_CODEX = "codex"
PROVIDER_ANTIGRAVITY = "antigravity"

CODEX_PARENT_KEYS = ("model", "model_reasoning_effort")
CODEX_WORKER_SOURCE = Path("codex/config.d/170-subagents.toml")
CODEX_WORKER_CONTRACT = {
    "enabled": True,
    "default_subagent_model": "gpt-5.6-luna",
    "default_subagent_reasoning_effort": "max",
    "max_concurrent_threads_per_session": 10,
}


class RoutingError(RuntimeError):
    """A route cannot be resolved against a verifiable profile source."""


STAGE_ROLES = tuple((stage.name, stage.role) for stage in _STANDARD.stages)


def claude_intelligence(
    root: Path | str, profile: str | None = None
) -> dict[str, Any]:
    if profile is None:
        profile_name = str(root)
        root_path = Path(__file__).resolve().parents[2]
    else:
        profile_name = profile
        root_path = Path(root)

    from claude_vc_profile import PROFILE_CONTRACTS
    from claude_model_catalog import load_catalog, resolve_role

    contract = PROFILE_CONTRACTS.get(profile_name)
    if contract is None:
        raise RoutingError(f"unknown Claude profile: {profile_name}")
    try:
        catalog = load_catalog(root_path)
        resolution = resolve_role(catalog, contract.model_role)
    except Exception as error:
        raise RoutingError(
            f"cannot resolve Claude catalog for profile {profile_name}: {error}"
        ) from error

    return {
        "model_role": contract.model_role,
        "model": resolution["resolved_model_id"],
        "effort": contract.effort,
        "catalog": resolution["catalog"],
    }


def codex_worker_contract(root: Path) -> dict[str, Any]:
    path = root / CODEX_WORKER_SOURCE
    try:
        raw = path.read_bytes()
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise RoutingError(f"unusable Codex worker source {path}: {error}") from error
    agents = parsed.get("agents") if isinstance(parsed, dict) else None
    if not isinstance(agents, dict):
        raise RoutingError("Codex worker source lacks an agents table")
    for key, expected in CODEX_WORKER_CONTRACT.items():
        actual = agents.get(key)
        if type(actual) is not type(expected):
            raise RoutingError(f"Codex worker {key} has the wrong type")
        if actual != expected:
            label = {
                "enabled": "disabled",
                "default_subagent_model": "model",
                "default_subagent_reasoning_effort": "reasoning effort",
                "max_concurrent_threads_per_session": "concurrency",
            }[key]
            raise RoutingError(f"Codex worker {label} contract mismatch")
    return {
        "mode": "provider-local",
        "enabled": agents["enabled"],
        "model": agents["default_subagent_model"],
        "reasoning_effort": agents["default_subagent_reasoning_effort"],
        "maximum_concurrency": agents["max_concurrent_threads_per_session"],
        "source_path": CODEX_WORKER_SOURCE.as_posix(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
    }


def codex_intelligence(
    root: Path, profile: str, *, attest_workers: bool = False
) -> dict[str, Any]:
    # Codex CLI silently continues with the mutable base config when a profile
    # file is missing, so an unverified profile name is a real mis-routing
    # hazard rather than a loud failure. Verify the source here instead.
    path = root / "codex/profiles" / f"{profile}.config.toml"
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise RoutingError(f"unusable Codex profile source {path}: {error}") from error
    missing = [key for key in CODEX_PARENT_KEYS if key not in parsed]
    if missing:
        raise RoutingError(f"Codex profile {profile} lacks {missing}")
    if any(type(parsed[key]) is not str or not parsed[key] for key in CODEX_PARENT_KEYS):
        raise RoutingError(f"Codex profile {profile} has invalid parent intelligence")
    result: dict[str, Any] = {
        "model": parsed["model"],
        "effort": parsed["model_reasoning_effort"],
        "role": "parent",
        "workers": "inherited-provider-local",
    }
    if attest_workers:
        result["workers"] = codex_worker_contract(root)
    return result


def antigravity_intelligence(root: Path, profile: str) -> dict[str, str]:
    from antigravity_profile import ProfileError, load_profile

    try:
        source = load_profile(root / "antigravity", profile)
    except ProfileError as error:
        raise RoutingError(str(error)) from error
    return {"model": source.model}


def describe(
    root: Path,
    role: str,
    endpoint: Endpoint,
    *,
    attest_workers: bool = False,
) -> dict[str, object]:
    if endpoint.provider == PROVIDER_CLAUDE:
        intelligence = claude_intelligence(root, endpoint.profile)
    elif endpoint.provider == PROVIDER_CODEX:
        intelligence = codex_intelligence(
            root, endpoint.profile, attest_workers=attest_workers
        )
    elif endpoint.provider == PROVIDER_ANTIGRAVITY:
        intelligence = antigravity_intelligence(root, endpoint.profile)
    else:
        raise RoutingError(f"unknown provider: {endpoint.provider}")
    return {
        "role": role,
        "provider": endpoint.provider,
        "profile": endpoint.profile,
        "intelligence": intelligence,
    }


def enforced_posture(
    root: Path, endpoint: Endpoint, process_read_only: bool
) -> dict[str, object]:
    if not process_read_only:
        return {"enforced": False, "mode": "mutation-capable"}
    if endpoint.provider == PROVIDER_CODEX:
        codex_intelligence(root, endpoint.profile)
        return {"enforced": True, "mode": "codex-sandbox-read-only"}
    if endpoint.provider == PROVIDER_CLAUDE:
        from claude_vc_profile import ProfileError, read_only_contract

        try:
            contract = read_only_contract(root / "claude", endpoint.profile)
        except ProfileError as error:
            raise RoutingError(str(error)) from error
        # Resolution precedes facade validation; only startup can select the
        # effective permission mode. Do not label an unresolved stage as plan.
        return {"mode": "claude-launcher-read-only", **contract, "permission_mode": "conditional"}
    if endpoint.provider == PROVIDER_ANTIGRAVITY:
        antigravity_intelligence(root, endpoint.profile)
        return {"enforced": True, "mode": "antigravity-plan-no-bypass"}
    raise RoutingError(f"unknown provider: {endpoint.provider}")


def load_validated_roster(root: Path) -> RosterSnapshot:
    """Load one immutable roster snapshot and validate every profile authority."""
    try:
        roster = load_roster(root)
        validate_profiles(
            roster,
            lambda _alias, endpoint: describe(root, "roster-validation", endpoint),
        )
        return roster
    except RosterError as error:
        raise RoutingError(str(error)) from error


def _standard_route(
    request: PhaseRequest,
    root: Path,
    roster: RosterSnapshot | None = None,
) -> tuple[dict[str, Endpoint], dict[str, str], RosterSnapshot]:
    snapshot = roster if roster is not None else load_validated_roster(root)
    try:
        aliases = snapshot.route_aliases(request.phase_type, request.execution_mode)
        endpoints = snapshot.route_endpoints(
            request.phase_type, request.execution_mode
        )
    except RosterError as error:
        raise RoutingError(str(error)) from error
    return endpoints, aliases, snapshot


def route(
    request: PhaseRequest,
    lifecycle: str | LifecycleSpec = LIFECYCLE_STANDARD,
    *,
    root: Path | None = None,
    roster: RosterSnapshot | None = None,
) -> dict[str, Endpoint]:
    specification = (
        get_lifecycle(lifecycle) if isinstance(lifecycle, str) else lifecycle
    )
    repository_root = root or Path(__file__).resolve().parents[2]
    standard, _aliases, _roster = _standard_route(
        request, repository_root, roster
    )
    return {
        stage.name: standard[stage.routing_slot] for stage in specification.stages
    }


def resolve(
    request: PhaseRequest,
    root: Path,
    lifecycle: str = LIFECYCLE_STANDARD,
    finalization_policy: str = FINALIZATION_PUBLISH,
    *,
    roster: RosterSnapshot | None = None,
) -> dict[str, object]:
    specification = get_lifecycle(lifecycle)
    validate_finalization(finalization_policy)
    standard, standard_aliases, snapshot = _standard_route(request, root, roster)
    endpoints = {
        stage.name: standard[stage.routing_slot] for stage in specification.stages
    }
    stages: dict[str, dict[str, object]] = {}
    for stage in specification.stages:
        endpoint = endpoints[stage.name]
        conserve_codex = (
            request.execution_mode == "conserve_claude"
            and endpoint.provider == PROVIDER_CODEX
        )
        described = describe(
            root, stage.role, endpoint, attest_workers=conserve_codex
        )
        if conserve_codex and stage.name == "final_review":
            described["review_process"] = {
                "identity": "fresh-top-level-sol-parent",
                "provider_local_workers_are_checkpoint": False,
            }
        stage_record = {
            **described,
            "endpoint_alias": standard_aliases[stage.routing_slot],
            "candidate_mutation": stage.is_mutating,
            "process_read_only": enforced_posture(
                root, endpoint, stage.process_read_only
            )["enforced"],
            "process_posture": enforced_posture(
                root, endpoint, stage.process_read_only
            ),
            "routing_source_slot": stage.routing_slot,
            "artifact_prefix": stage.prefix,
            "review_checkpoint": stage.checkpoint,
            "candidate_binding_key": stage.candidate_key,
        }
        worker_cap = resolve_worker_capability(
            root, endpoint.provider, endpoint.profile, request.execution_mode
        )
        if worker_cap is not None:
            stage_record["worker_capability"] = worker_cap
        stages[stage.name] = stage_record
    resolved = {
        "schema": RESOLVED_SCHEMA,
        "phase_type": request.phase_type,
        "execution_mode": request.execution_mode,
        "lifecycle": specification.name,
        "finalization_policy": finalization_policy,
        "expected_stages": list(specification.stage_names),
        "checkpoints": list(specification.checkpoints),
        "checkpoint_count": specification.expected_review_count,
        "expected_review_count": specification.expected_review_count,
        "provider_invocations": specification.expected_provider_invocations,
        "expected_provider_invocations": specification.expected_provider_invocations,
        "terminal_result_stage": specification.terminal_result_stage,
        "provider_local_workers_count_as_invocations": False,
        "provider_local_workers_count_as_reviews": False,
        "roster": snapshot.provenance(),
        "stages": stages,
    }
    resolved["effective_stage_routes"] = build_fresh_effective_routes(
        resolved, specification
    )
    resolved["route_transition"] = None
    return resolved
