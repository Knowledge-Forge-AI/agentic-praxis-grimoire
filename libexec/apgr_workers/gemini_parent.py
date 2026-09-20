"""Qualified Gemini parent registration and bounded delegation provenance."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .policy import TRIPLE_POOL, identify_parent_family


def validate_registration(capability: Mapping[str, Any] | None) -> None:
    """A family label alone cannot create a Gemini parent allowance."""
    cap = capability if isinstance(capability, Mapping) else {}
    source = cap.get("source_root")
    if (
        cap.get("execution_mode") not in ("gemini_flash_sub", "gemini_flash_opus_sub", "dynamic")
        or cap.get("parent_provider") != "antigravity"
        or cap.get("parent_family") != "gemini_flash"
        or cap.get("policy_selection") not in (TRIPLE_POOL, "triple_pool_4x4x4")
        or cap.get("allowed") is not True
        or capability_error(cap) is not None
        or not isinstance(source, str)
        or identify_parent_family(Path(source), "antigravity", cap.get("parent_profile")) != "gemini_flash"
    ):
        raise ValueError("Gemini parent requires qualified profile and Flash High provenance")


def capability_error(capability: Mapping[str, Any]) -> str | None:
    """Reject inconsistent external-only capability flags before rendering them."""
    if (
        capability.get("parent_family") != "gemini_flash"
        or capability.get("execution_mode") not in ("gemini_flash_sub", "gemini_flash_opus_sub", "dynamic")
        or capability.get("native_worker") != {"enabled": False}
        or capability.get("borrowing") is not False
    ):
        return "Gemini Flash requires independent external pools"

    policy_selection = capability.get("policy_selection")
    luna = capability.get("luna_worker")
    limits = capability.get("limits")
    if not isinstance(limits, Mapping):
        return "Gemini Flash capability lacks limits"

    if policy_selection == "triple_pool_4x4x4":
        sonnet = capability.get("sonnet_worker")
        if (
            not isinstance(luna, Mapping)
            or luna.get("transport") != "codex_external"
            or luna.get("provider") != "codex"
            or not isinstance(sonnet, Mapping)
            or sonnet.get("transport") != "claude_external"
            or sonnet.get("provider") != "claude"
            or sonnet.get("model") != "claude-sonnet-5-5"
            or sonnet.get("effort") != "high"
            or capability.get("allowed_worker_kinds") != ["gemini", "luna", "sonnet"]
            or any(type(limits.get(key)) is not int or limits[key] != value
                   for key, value in (("max_gemini", 4), ("max_luna", 4), ("max_sonnet", 4), ("max_aggregate", 12)))
        ):
            return "Gemini Flash requires independent external Gemini, Luna, and Sonnet pools"
    else:
        return "fresh Gemini worker admission requires triple_pool_4x4x4"
    return None


def worker_provenance(capability: Mapping[str, Any], kind: str) -> dict[str, Any]:
    """Copy only source-owned identities, never prompts or environment."""
    keys = ("execution_mode", "parent_provider", "parent_profile", "parent_family",
            "parent_model", "parent_effort", "parent_run_id", "parent_stage",
            "lifecycle_generation", "policy_selection", "policy_sha256")
    worker = capability.get(f"{kind}_worker", {})
    generation = capability.get("controller_generation")
    controller = ({"controller_generation": {
        key: generation[key] for key in ("schema", "commit", "tree", "manifest_sha256", "safety_established")
        if key in generation
    }} if isinstance(generation, Mapping) else {})
    if kind == "sonnet":
        transport = "claude_external"
    elif kind == "luna":
        transport = "codex_external"
    else:
        transport = "antigravity"
    return {
        **{key: capability[key] for key in keys if key in capability},
        **controller,
        "worker_kind": kind,
        "worker": {key: worker[key] for key in ("provider", "profile", "model", "effort") if key in worker},
        "transport": transport,
    }
