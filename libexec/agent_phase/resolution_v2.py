"""Resolution logic and agent-phase-resolved-v7 contract for Request V2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .capabilities import load_capabilities
from .dynamic_router import (
    resolve_dynamic_route,
    resolve_static_preset_route,
)
from .lifecycle import (
    FINALIZATION_PUBLISH,
    LIFECYCLE_STANDARD,
    get_lifecycle,
    validate_finalization,
)
from .request import PhaseRequestV2
from .roster import RosterSnapshot, load_roster

from .config_routing import RETAINED_STATIC_MODES
from .route_provenance import RESOLVED_V7
from .semantic_roles import (
    CANONICAL_RESPONSIBILITIES,
    ActorBindingPolicy,
    create_default_binding_policy,
)


def resolve_v2(
    request: PhaseRequestV2,
    root: Path,
    *,
    execution_mode: str = "dynamic",
    configuration_provenance: Mapping[str, Any] | None = None,
    lifecycle: str = LIFECYCLE_STANDARD,
    finalization_policy: str = FINALIZATION_PUBLISH,
    binding_policy: ActorBindingPolicy | None = None,
    roster: RosterSnapshot | None = None,
    operational_observations: Sequence[Any] = (),
    prior_resolutions: Mapping[str, Any] | None = None,
    resolve_all_dynamic: bool = False,
) -> dict[str, Any]:
    """Resolve a Request V2 document into an agent-phase-resolved-v7 record."""
    validate_finalization(finalization_policy)
    spec = get_lifecycle(lifecycle)
    snap = roster or load_roster(root)
    policy = binding_policy or create_default_binding_policy()
    caps_catalog = load_capabilities(root)

    route_resolutions: dict[str, Any] = {}
    pending_responsibilities: list[str] = []

    if execution_mode in RETAINED_STATIC_MODES:
        for binding in policy.bindings:
            res = resolve_static_preset_route(
                binding, request.phase_type, execution_mode, roster=snap, root=root
            )
            route_resolutions[binding.binding_id] = res.as_dict()
    else:
        if resolve_all_dynamic:
            accumulated: dict[str, Any] = dict(prior_resolutions or {})
            for binding in policy.bindings:
                res = resolve_dynamic_route(
                    binding,
                    request.phase_type,
                    capabilities_catalog=caps_catalog,
                    operational_observations=operational_observations,
                    prior_resolutions=accumulated,
                )
                accumulated[binding.binding_id] = res
                route_resolutions[binding.binding_id] = res.as_dict()
        else:
            # Dynamic: resolve initial binding, leave subsequent bindings pending
            initial_binding = policy.bindings[0]
            initial_route = resolve_dynamic_route(
                initial_binding,
                request.phase_type,
                capabilities_catalog=caps_catalog,
                operational_observations=operational_observations,
                prior_resolutions=prior_resolutions or {},
            )
            route_resolutions[initial_binding.binding_id] = initial_route.as_dict()
            for binding in policy.bindings[1:]:
                for r in binding.roles:
                    pending_responsibilities.append(r)

    resolved: dict[str, Any] = {
        "schema": RESOLVED_V7,
        "request_schema": request.schema,
        "phase_type": request.phase_type,
        "execution_mode": execution_mode,
        "lifecycle": spec.name,
        "finalization_policy": finalization_policy,
        "configuration_provenance": configuration_provenance or {},
        "actor_binding_policy": policy.as_dict(),
        "semantic_responsibilities": list(CANONICAL_RESPONSIBILITIES),
        "route_resolutions": route_resolutions,
        "pending_responsibilities": pending_responsibilities,
    }
    return resolved
