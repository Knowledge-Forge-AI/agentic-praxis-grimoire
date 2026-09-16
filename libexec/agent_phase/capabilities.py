"""Capabilities catalog and inspection for provider profiles."""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import NamedTuple


CAPABILITIES_SCHEMA = "agent-phase-capabilities-v1"
CAPABILITIES_SOURCE = Path("common/dispatcher/capabilities.toml")

VALID_CAPABILITIES = frozenset(
    {
        "read",
        "mutation",
        "execution",
        "reasoning",
        "structured_output",
        "subagent_workers",
    }
)
VALID_POSTURES = frozenset({"mutating", "read_only"})
VALID_PROVIDERS = frozenset({"antigravity", "claude", "codex"})


class CapabilityError(ValueError):
    """Raised when capabilities configuration or query is invalid."""


class EndpointCapabilities(NamedTuple):
    endpoint_alias: str
    provider: str
    profile: str
    capabilities: frozenset[str]
    posture: str

    @property
    def is_mutating(self) -> bool:
        return self.posture == "mutating"

    @property
    def is_read_only(self) -> bool:
        return self.posture == "read_only"

    def satisfies(self, required: frozenset[str], *, requires_mutating: bool = False, requires_read_only: bool = False) -> bool:
        if not required.issubset(self.capabilities):
            return False
        if requires_mutating and not self.is_mutating:
            return False
        if requires_read_only and not self.is_read_only:
            return False
        return True


def _default_endpoint_capabilities(endpoint_alias: str, provider: str, profile: str) -> EndpointCapabilities:
    is_review = "review" in endpoint_alias or "review" in profile
    if provider == "antigravity":
        if is_review or "opus" in profile:
            caps = frozenset({"read", "reasoning"})
            posture = "read_only"
        else:
            caps = frozenset({"read", "mutation", "execution", "reasoning", "subagent_workers"})
            posture = "mutating"
    elif provider == "claude":
        if is_review:
            caps = frozenset({"read", "reasoning", "structured_output"})
            posture = "read_only"
        else:
            caps = frozenset({"read", "mutation", "execution", "reasoning", "structured_output"})
            posture = "mutating"
    elif provider == "codex":
        if is_review:
            caps = frozenset({"read", "reasoning", "structured_output"})
            posture = "read_only"
        else:
            caps = frozenset({"read", "mutation", "execution", "reasoning", "structured_output"})
            posture = "mutating"
    else:
        caps = frozenset({"read"})
        posture = "read_only"
    return EndpointCapabilities(
        endpoint_alias=endpoint_alias,
        provider=provider,
        profile=profile,
        capabilities=caps,
        posture=posture,
    )


def load_capabilities(root: Path | None = None) -> dict[str, EndpointCapabilities]:
    """Load endpoint capability metadata from common/dispatcher/capabilities.toml."""
    repository_root = root or Path(__file__).resolve().parents[2]
    source_path = repository_root / CAPABILITIES_SOURCE
    if not source_path.is_file():
        return {}
    try:
        raw_text = source_path.read_text(encoding="utf-8")
        data = tomllib.loads(raw_text)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise CapabilityError(f"cannot read capabilities from {source_path}: {error}") from error

    if not isinstance(data, dict):
        raise CapabilityError("capabilities file must be a TOML table")
    if data.get("schema") != CAPABILITIES_SCHEMA:
        raise CapabilityError(f"capabilities schema must be {CAPABILITIES_SCHEMA}")

    endpoints_table = data.get("endpoints")
    if not isinstance(endpoints_table, dict):
        raise CapabilityError("capabilities missing [endpoints] table")

    result: dict[str, EndpointCapabilities] = {}
    for alias, entry in endpoints_table.items():
        if not isinstance(entry, dict):
            raise CapabilityError(f"endpoint {alias!r} must be a table")
        provider = entry.get("provider")
        profile = entry.get("profile")
        caps_raw = entry.get("capabilities", [])
        posture = entry.get("posture", "mutating")

        if provider not in VALID_PROVIDERS:
            raise CapabilityError(f"invalid provider {provider!r} for endpoint {alias!r}")
        if not isinstance(profile, str) or not profile:
            raise CapabilityError(f"invalid profile for endpoint {alias!r}")
        if not isinstance(caps_raw, list):
            raise CapabilityError(f"capabilities must be a list for endpoint {alias!r}")
        caps = frozenset(caps_raw)
        unknown_caps = caps - VALID_CAPABILITIES
        if unknown_caps:
            raise CapabilityError(f"unknown capabilities {sorted(unknown_caps)} for endpoint {alias!r}")
        if posture not in VALID_POSTURES:
            raise CapabilityError(f"invalid posture {posture!r} for endpoint {alias!r}")

        result[alias] = EndpointCapabilities(
            endpoint_alias=alias,
            provider=provider,
            profile=profile,
            capabilities=caps,
            posture=posture,
        )
    return result
