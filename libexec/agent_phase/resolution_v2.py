"""Resolution logic and agent-phase-resolved-v7 contract for Request V2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .capabilities import load_capabilities
from .dynamic_router import (
    RoutingResolutionError,
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
    apgr_home: Path | str | None = None,
    bundle: Any = None,
    snapshot: Any = None,
    worker_qualifier: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Resolve a Request V2 document into an agent-phase-resolved-v7 record."""
    validate_finalization(finalization_policy)
    spec = get_lifecycle(lifecycle)
    snap = roster or load_roster(root, apgr_home=apgr_home)
    policy = binding_policy or create_default_binding_policy()
    caps_catalog = load_capabilities(root, apgr_home=apgr_home, roster=snap)

    route_resolutions: dict[str, Any] = {}
    pending_responsibilities: list[str] = []

    effective_bundle = snapshot if snapshot is not None else bundle
    if effective_bundle is None:
        effective_bundle = snap.bundle
    from .bundle import DispatcherBundleSnapshot, require_fresh_bundle
    authority_bundle = effective_bundle if isinstance(effective_bundle, DispatcherBundleSnapshot) else snap.bundle
    if authority_bundle is not None:
        require_fresh_bundle(authority_bundle)
    from . import runtime_models
    from contextlib import nullcontext
    capture_ctx = runtime_models.captured(effective_bundle) if effective_bundle is not None else nullcontext()

    with capture_ctx:
        if execution_mode in RETAINED_STATIC_MODES:
            for binding in policy.bindings:
                res = resolve_static_preset_route(
                    binding,
                    request.phase_type,
                    execution_mode,
                    roster=snap,
                    root=root,
                    capabilities=caps_catalog,
                    apgr_home=apgr_home,
                )
                route_resolutions[binding.binding_id] = res.as_dict()
        else:
            if not caps_catalog:
                raise RoutingResolutionError(
                    "dynamic execution mode requires a usable capabilities catalog, but capabilities are missing or empty"
                )
            if resolve_all_dynamic:
                accumulated: dict[str, Any] = dict(prior_resolutions or {})
                for binding in policy.bindings:
                    res = resolve_dynamic_route(
                        binding,
                        request.phase_type,
                        capabilities_catalog=caps_catalog,
                        operational_observations=operational_observations,
                        prior_resolutions=accumulated,
                        worker_qualifier=worker_qualifier,
                        execution_mode=execution_mode,
                        root=root,
                        bundle=effective_bundle,
                        snapshot=effective_bundle,
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
                    worker_qualifier=worker_qualifier,
                    execution_mode=execution_mode,
                    root=root,
                    bundle=effective_bundle,
                    snapshot=effective_bundle,
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
    if bundle is not None:
        if hasattr(bundle, "provenance") and callable(bundle.provenance):
            resolved["bundle_provenance"] = bundle.provenance()
        elif isinstance(bundle, dict):
            resolved["bundle"] = bundle
    if snapshot is not None:
        if hasattr(snapshot, "provenance") and callable(snapshot.provenance):
            resolved["snapshot_provenance"] = snapshot.provenance()
        elif isinstance(snapshot, dict):
            resolved["snapshot"] = snapshot
    return resolved
