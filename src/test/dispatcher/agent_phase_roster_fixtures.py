"""Test-owned dispatcher roster and provider-profile fixtures."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping

from agent_phase.request import EXECUTION_MODES, PHASE_TYPES
from agent_phase.roster import Endpoint, STANDARD_SLOTS
from claude_vc_profile import PROFILE_CONTRACTS
from claude_model_catalog import load_catalog, resolve_role

_CATALOG_FILE = Path(__file__).resolve().parents[3] / "claude/model-catalog-v1.json"
_CANONICAL_CATALOG = load_catalog(_CATALOG_FILE)
_CANONICAL_PRIMARY = resolve_role(_CANONICAL_CATALOG, "primary")
_CANONICAL_REVIEW = resolve_role(_CANONICAL_CATALOG, "review")


SYNTHETIC_GENERATION = 41
SYNTHETIC_ENDPOINTS = {
    "fixture-claude-primary": Endpoint("claude", "implementation-primary"),
    "fixture-claude-review": Endpoint("claude", "implementation-review"),
    "fixture-codex-primary": Endpoint("codex", "fixture-codex-primary"),
    "fixture-codex-review": Endpoint("codex", "fixture-codex-review"),
    "fixture-gemini-blue": Endpoint("antigravity", "fixture-gemini-blue"),
    "fixture-gemini-gold": Endpoint("antigravity", "fixture-gemini-gold"),
}
SYNTHETIC_INTELLIGENCE = {
    ("claude", "implementation-primary"): {
        "model_role": "primary",
        "model": _CANONICAL_PRIMARY["resolved_model_id"],
        "effort": PROFILE_CONTRACTS["implementation-primary"].effort,
        "catalog": _CANONICAL_PRIMARY["catalog"],
    },
    ("claude", "implementation-review"): {
        "model_role": "review",
        "model": _CANONICAL_REVIEW["resolved_model_id"],
        "effort": PROFILE_CONTRACTS["implementation-review"].effort,
        "catalog": _CANONICAL_REVIEW["catalog"],
    },
    ("codex", "fixture-codex-primary"): {
        "model": "fixture-codex-model-primary",
        "effort": "medium",
        "role": "parent",
        "workers": "inherited-provider-local",
    },
    ("codex", "fixture-codex-review"): {
        "model": "fixture-codex-model-review",
        "effort": "high",
        "role": "parent",
        "workers": "inherited-provider-local",
    },
    ("antigravity", "fixture-gemini-blue"): {
        "model": "fixture-gemini-blue-model"
    },
    ("antigravity", "fixture-gemini-gold"): {
        "model": "fixture-gemini-gold-model"
    },
}


@dataclass(frozen=True)
class SyntheticRoster:
    root: Path
    generation: int
    endpoints: Mapping[str, Endpoint]
    routes: Mapping[tuple[str, str], Mapping[str, str]]


def repeated(primary: str, reviewer: str) -> dict[str, str]:
    return {
        slot: reviewer if slot in {"plan_review", "final_review"} else primary
        for slot in STANDARD_SLOTS
    }


def synthetic_routes(variant: str = "mixed") -> dict[tuple[str, str], dict[str, str]]:
    if variant not in {"mixed", "permuted"}:
        raise ValueError(f"unknown synthetic roster variant: {variant}")
    routes: dict[tuple[str, str], dict[str, str]] = {}
    for phase_index, phase_type in enumerate(PHASE_TYPES):
        mixed = (
            {
                "plan": "fixture-gemini-blue",
                "plan_review": "fixture-claude-review",
                "work": "fixture-codex-primary",
                "final_review": "fixture-codex-review",
                "closeout": "fixture-claude-primary",
            }
            if phase_index % 2 == 0
            else {
                "plan": "fixture-codex-primary",
                "plan_review": "fixture-gemini-gold",
                "work": "fixture-claude-primary",
                "final_review": "fixture-claude-review",
                "closeout": "fixture-gemini-blue",
            }
        )
        permuted = {
            "plan": "fixture-claude-primary",
            "plan_review": "fixture-codex-review",
            "work": "fixture-gemini-gold",
            "final_review": "fixture-gemini-blue",
            "closeout": "fixture-codex-primary",
        }
        routes[(phase_type, "normal")] = mixed if variant == "mixed" else permuted
        gemini_sub_route = dict(routes[(phase_type, "normal")])
        gemini_sub_route["work"] = "fixture-codex-primary"
        routes[(phase_type, "gemini_sub")] = gemini_sub_route
        # This fixture's Codex profile is deliberately non-Astra.  The new
        # mode therefore preserves every gemini_sub endpoint here, exercising
        # the non-substitution side of the route transformation invariant.
        routes[(phase_type, "gemini_flash_sub")] = dict(gemini_sub_route)
        gemini_flash_opus_route = dict(gemini_sub_route)
        for slot, alias in list(gemini_flash_opus_route.items()):
            if alias == "fixture-claude-review":
                gemini_flash_opus_route[slot] = "fixture-claude-primary"
        routes[(phase_type, "gemini_flash_opus_sub")] = gemini_flash_opus_route
        routes[(phase_type, "conserve_claude")] = {
            "plan": "fixture-codex-primary",
            "plan_review": "fixture-claude-review",
            "work": "fixture-gemini-gold",
            "final_review": "fixture-codex-review",
            "closeout": "fixture-gemini-blue",
        }
        routes[(phase_type, "claude_only")] = repeated(
            "fixture-claude-primary", "fixture-claude-review"
        )
        routes[(phase_type, "codex_only")] = repeated(
            "fixture-codex-primary", "fixture-codex-review"
        )
        routes[(phase_type, "gemini_only")] = repeated(
            "fixture-gemini-blue", "fixture-gemini-gold"
        )
        routes[(phase_type, "gemini_opus")] = repeated(
            "fixture-gemini-gold", "fixture-claude-primary"
        )
        routes[(phase_type, "gemini_fable")] = {
            "plan": "fixture-gemini-gold",
            "plan_review": "fixture-claude-review",
            "work": "fixture-gemini-gold",
            "final_review": "fixture-claude-primary",
            "closeout": "fixture-gemini-gold",
        }
    assert set(routes) == {
        (phase_type, execution_mode)
        for phase_type in PHASE_TYPES
        for execution_mode in EXECUTION_MODES
    }
    return routes


def write_roster_sources(
    root: Path,
    endpoints: Mapping[str, Endpoint],
    routes: Mapping[tuple[str, str], Mapping[str, str]],
    *,
    generation: int = SYNTHETIC_GENERATION,
) -> None:
    dispatcher = root / "common/dispatcher"
    dispatcher.mkdir(parents=True, exist_ok=True)
    endpoint_lines = [
        'schema = "agent-phase-endpoints-v1"',
        f"generation = {generation}",
        "",
    ]
    for alias, endpoint in endpoints.items():
        endpoint_lines.extend(
            (
                f"[endpoints.{alias}]",
                f'provider = "{endpoint.provider}"',
                f'profile = "{endpoint.profile}"',
                "",
            )
        )
    (dispatcher / "endpoints.toml").write_text(
        "\n".join(endpoint_lines), encoding="utf-8"
    )

    route_lines = [
        'schema = "agent-phase-routes-v1"',
        f"generation = {generation}",
        "",
    ]
    for phase_type in PHASE_TYPES:
        for execution_mode in EXECUTION_MODES:
            route_lines.append(f"[routes.{phase_type}.{execution_mode}]")
            route = routes[(phase_type, execution_mode)]
            route_lines.extend(f'{slot} = "{route[slot]}"' for slot in STANDARD_SLOTS)
            route_lines.append("")
    (dispatcher / "routes.toml").write_text(
        "\n".join(route_lines), encoding="utf-8"
    )


def _write_profile_sources(root: Path) -> None:
    claude_dir = root / "claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "model-catalog-v1.json").write_bytes(_CATALOG_FILE.read_bytes())

    claude_profiles = root / "claude/profiles"
    claude_profiles.mkdir(parents=True, exist_ok=True)
    claude_documents = {
        "implementation-primary": {
            "modelRole": "primary",
            "effort": "medium",
        },
        "implementation-review": {
            "modelRole": "review",
            "effort": "medium",
            "permissionMode": "plan",
        },
    }
    for profile, document in claude_documents.items():
        (claude_profiles / f"{profile}.json").write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8"
        )

    codex_profiles = root / "codex/profiles"
    codex_profiles.mkdir(parents=True, exist_ok=True)
    for profile, model, effort in (
        ("fixture-codex-primary", "fixture-codex-model-primary", "medium"),
        ("fixture-codex-review", "fixture-codex-model-review", "high"),
    ):
        (codex_profiles / f"{profile}.config.toml").write_text(
            f'model = "{model}"\nmodel_reasoning_effort = "{effort}"\n',
            encoding="utf-8",
        )
    worker_source = root / "codex/config.d/170-subagents.toml"
    worker_source.parent.mkdir(parents=True, exist_ok=True)
    worker_source.write_text(
        "[agents]\n"
        "enabled = true\n"
        'default_subagent_model = "gpt-5.6-luna"\n'
        'default_subagent_reasoning_effort = "max"\n'
        "max_concurrent_threads_per_session = 10\n",
        encoding="utf-8",
    )

    antigravity_profiles = root / "antigravity/profiles"
    antigravity_profiles.mkdir(parents=True, exist_ok=True)
    for profile, model in (
        ("fixture-gemini-blue", "fixture-gemini-blue-model"),
        ("fixture-gemini-gold", "fixture-gemini-gold-model"),
    ):
        (antigravity_profiles / f"{profile}.json").write_text(
            json.dumps({"model": model}, indent=2) + "\n", encoding="utf-8"
        )


def build_synthetic_roster(
    base: Path, *, variant: str = "mixed"
) -> SyntheticRoster:
    root = base / "repository"
    routes = synthetic_routes(variant)
    write_roster_sources(root, SYNTHETIC_ENDPOINTS, routes)
    _write_profile_sources(root)
    return SyntheticRoster(
        root=root,
        generation=SYNTHETIC_GENERATION,
        endpoints=SYNTHETIC_ENDPOINTS,
        routes=routes,
    )


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"expected exactly one fixture occurrence, found {count}: {old!r}")
    return text.replace(old, new, 1)
