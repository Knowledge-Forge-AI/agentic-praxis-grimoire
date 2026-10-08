"""Strict current and historical worker policy parsing; parsing grants no admission."""
from collections.abc import Mapping

from .bundle import BundleError, WorkerPolicySnapshot
from .bundle_io import recursive_freeze


def parse_worker_policy(raw):
    def table(value, label):
        if not isinstance(value, Mapping):
            raise BundleError(f"workers.toml missing required {label} table")
        return value

    def exact(value, expected, label):
        if type(value) is not type(expected) or value != expected:
            kind = "boolean" if type(expected) is bool else "integer" if type(expected) is int else "string"
            raise BundleError(f"{label} must be {kind} {expected!r}, got {value!r}")

    raw = table(raw, "policy")
    limits = table(raw.get("limits"), "limits")
    selections = table(raw.get("selections"), "selections")
    name = (raw.get("policy") or {}).get("name")
    if name is None and raw.get("schema") == "agent-worker-policy-v1":
        name = "dual_pool_4x4"
    if name not in {"dual_pool_4x4", "triple_pool_4x4x4"}:
        raise BundleError(f"unknown worker policy selection name: {name!r}")
    triple = name == "triple_pool_4x4x4"
    exact(raw.get("schema"), "agent-worker-policy-v2" if triple else "agent-worker-policy-v1", "worker schema")
    if triple and (type(raw.get("generation")) is not int or raw["generation"] < 9):
        raise BundleError("triple policy requires generation 9 or later")
    exact(limits.get("max_gemini_workers_per_parent"), 4, "max_gemini_workers_per_parent")
    aggregate = "max_aggregate_workers_per_codex_parent" if triple else "max_aggregate_workers_per_astra_parent"
    exact(limits.get(aggregate), 12 if triple else 8, aggregate)
    pool = table(selections.get(name), name)
    kinds = ("gemini", "luna", "sonnet") if triple else ("gemini", "luna")
    for kind in kinds:
        exact(pool.get(f"max_{kind}"), 4, f"{name} max_{kind}")
    for key, value in (("borrowing", False), ("leaf_only", True), ("parent_authority", True)):
        exact(pool.get(key), value, f"{name} {key}")
    modes = pool.get("mode_requirements")
    if not isinstance(modes, (list, tuple)) or not modes or any(type(m) is not str or not m for m in modes):
        raise BundleError(f"{name} mode_requirements must be a non-empty sequence of strings")
    if "read_only" in pool and type(pool["read_only"]) is not bool:
        raise BundleError(f"{name} read_only must be a boolean")
    workers = {}
    for kind in kinds:
        worker = table(pool.get(f"{kind}_worker", raw.get("gemini_worker") if kind == "gemini" else None), f"{name} {kind}_worker")
        for key in ("provider", "profile"):
            if type(worker.get(key)) is not str or not worker[key]:
                raise BundleError(f"{name} {kind}_worker missing valid {key} string")
        workers[kind] = recursive_freeze(dict(worker))
    return WorkerPolicySnapshot(
        name=name, max_gemini=4, max_luna=4, max_sonnet=4 if triple else None,
        borrowing=False, leaf_only=True, parent_authority=True, mode_requirements=tuple(modes),
        gemini_worker=workers["gemini"], luna_worker=workers["luna"],
        sonnet_worker=workers.get("sonnet", recursive_freeze({})),
        limits=recursive_freeze(dict(limits)), raw=recursive_freeze(dict(raw)),
    )
