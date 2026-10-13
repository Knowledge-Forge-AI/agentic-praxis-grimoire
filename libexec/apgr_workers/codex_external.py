"""Direct, bounded Codex CLI transport for an external Luna leaf worker.

The parent supplies the selected worker-policy profile name.  This module
reads that tracked profile, constructs a fixed ``codex exec`` invocation, and
parses JSONL events without exposing arbitrary executable, model, credential,
or parent-context arguments to the worker interface.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

_PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_QUOTA_TEXT_RE = re.compile(
    r"(?:^\s*quota\s*(?:is\s*)?exhausted\b|"
    r"^\s*insufficient[_ -]?quota\b|"
    r"^\s*you['’]ve hit your usage limit\.)",
    re.IGNORECASE,
)
_QUOTA_CODE_RE = re.compile(
    r"^(?:insufficient[_ -]?quota|quota[_ -]?exhausted)$",
    re.IGNORECASE,
)
_TRANSIENT_ERROR_RE = re.compile(
    r"(?:rate[\s_-]*limit|retry[\s_-]*after|per[\s_-]?minute|"
    r"too many requests|temporar(?:y|ily)|throttl)",
    re.IGNORECASE,
)
# Stderr is only considered after an unsuccessful provider invocation. Keep
# the match line-oriented and allow only the known direct/wrapper prefixes so
# copied answer, tool, or fixture prose cannot become a pause signal.
_FAILED_STDERR_QUOTA_RE = re.compile(
    r"\A\s*(?:antigravity-profile:\s+provider ended with status\s+"
    r"[A-Za-z][A-Za-z0-9_.-]{0,63}\s*\n)?"
    r"(?:(?:antigravity-profile:\s+provider error:\s*)|"
    r"(?:codex(?:\s+(?:exec|cli))?:\s*)|)"
    r"(?:you['’]ve hit your usage limit\.|"
    r"quota\s*(?:is\s*)?exhausted\b|"
    r"insufficient[_ -]?quota\b)",
    re.IGNORECASE,
)
_ANTIGRAVITY_STATUS_RE = re.compile(
    r"^\s*antigravity-profile:\s+provider ended with status\s+"
    r"([A-Za-z][A-Za-z0-9_.-]{0,63})\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_ERROR_EVENT_TYPES = frozenset({"error", "turn.failed"})
_TEXT_KEYS = ("text", "delta", "content", "message", "output_text", "final_message")
_MODEL_KEYS = ("model", "model_slug", "model_name", "model_id")
_EFFORT_KEYS = ("reasoning_effort", "model_reasoning_effort", "effort")
_ID_KEYS = ("thread_id", "threadId", "session_id", "sessionId", "conversation_id")


class CodexExternalError(ValueError):
    """The tracked Luna leaf profile or fixed transport contract is invalid."""


@dataclass(frozen=True)
class LunaProfile:
    """Source-owned model and runtime settings for one Luna leaf."""

    name: str
    model: str
    effort: str
    agents_enabled: bool
    source: str
    source_sha256: str
    projection_matches_selected: bool = True

    def evidence(self) -> dict[str, Any]:
        """Return non-secret profile provenance suitable for a worker result."""
        return {
            "profile": self.name,
            "model": self.model,
            "effort": self.effort,
            "agents_enabled": self.agents_enabled,
            "source": self.source,
            "source_sha256": self.source_sha256,
            "projection_matches_selected": self.projection_matches_selected,
        }


def _repository_root(root: Path | None = None) -> Path:
    if root is not None:
        return Path(root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def load_luna_profile(
    root: Path | None = None, profile: str | None = None
) -> LunaProfile:
    """Load and validate the external Luna profile."""
    from agent_phase.runtime_models import selected_worker_profile
    selected_profile = selected_worker_profile(_repository_root(root), "luna")
    profile = profile or selected_profile
    if profile != selected_profile:
        raise CodexExternalError(f"selected worker policy requires profile {selected_profile!r}")
    if not isinstance(profile, str) or not _PROFILE_RE.fullmatch(profile):
        raise CodexExternalError(f"invalid Luna worker profile name {profile!r}")
    repository = _repository_root(root)
    path = repository / "codex/profiles" / f"{profile}.config.toml"
    try:
        raw = path.read_bytes()
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise CodexExternalError(f"cannot read Luna worker profile {path}: {error}") from error
    if not isinstance(parsed, dict):
        raise CodexExternalError("Luna worker profile must contain a TOML table")
    agents = parsed.get("agents")
    enabled = agents.get("enabled") if isinstance(agents, Mapping) else None
    if enabled is not False:
        raise CodexExternalError(
            "Luna worker posture requires agents.enabled=false"
        )
    from agent_phase.runtime_models import selection
    try:
        sel = selection(repository, "codex", profile)
        bundle_model = sel.get("model")
        bundle_effort = sel.get("effort")
    except Exception as error:
        raise CodexExternalError(f"cannot resolve Luna model from bundle: {error}") from error
    if not isinstance(bundle_model, str) or not bundle_model or not isinstance(bundle_effort, str) or not bundle_effort:
        raise CodexExternalError(
            f"invalid selected model/effort for Luna worker profile {profile}"
        )
    try:
        source = path.relative_to(repository).as_posix()
    except ValueError:
        source = path.as_posix()
    return LunaProfile(
        name=profile,
        model=bundle_model,
        effort=bundle_effort,
        agents_enabled=False,
        source=source,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        projection_matches_selected=(parsed.get("model") == bundle_model and parsed.get("model_reasoning_effort") == bundle_effort),
    )


def build_codex_exec_argv(
    profile: LunaProfile,
    workspace: Path,
    task_authority: str,
) -> list[str]:
    """Build the fixed installed ``codex exec`` argv for a Luna leaf."""
    if (
        not isinstance(profile, LunaProfile)
        or not profile.name
        or not profile.model
        or not profile.effort
        or profile.agents_enabled is not False
    ):
        raise CodexExternalError(
            "external Luna transport requires a valid LunaProfile with agents disabled"
        )
    workspace = Path(workspace).expanduser().resolve()
    if task_authority not in {"read_only", "mutation_capable"}:
        raise CodexExternalError("task authority must be read_only or mutation_capable")
    sandbox = "read-only" if task_authority == "read_only" else "workspace-write"
    # ``codex`` is resolved through the inherited, operator-authorized PATH.
    # The tracked profile is source evidence, rather than a live CODEX_HOME
    # dependency.  Explicit overrides make the selected model, effort, and
    # leaf setting observable even when the active home has no profile link.
    # ``--ignore-user-config`` keeps unrelated user MCP/plugin configuration
    # out of this leaf.  Codex still reads auth from CODEX_HOME; this flag does
    # not change credentials or select an alternate account.
    # A read-only leaf may use an isolated non-Git workspace. Mutating leaves
    # retain the provider's Git trust check. Retain
    # the normal provider session so effective runtime selection is observable;
    # downstream evidence extracts metadata and a digest, never raw transcripts.
    return [
        "codex",
        "exec",
        "--json",
        *(["--skip-git-repo-check"] if task_authority == "read_only" else []),
        "--ignore-user-config",
        "-c",
        f"model={json.dumps(profile.model)}",
        "-c",
        f"model_reasoning_effort={json.dumps(profile.effort)}",
        "-c",
        "agents.enabled=false",
        "--cd",
        str(workspace),
        "--sandbox",
        sandbox,
        "-",
    ]


def _walk(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _first_string(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _text_from_event(event: Mapping[str, Any]) -> str | None:
    """Extract model text from common Codex JSONL event shapes."""
    event_type = event.get("type")
    # Lifecycle and usage events often contain a nested ``message`` field that
    # is diagnostic text, not the worker answer.  Prefer explicit output event
    # types and final/item messages before a conservative recursive fallback.
    preferred = (
        event_type in {
            "item.completed",
            "item.output_text.delta",
            "response.output_text.delta",
            "response.output_text.done",
            "message",
            "agent_message",
            "turn.completed",
            "final",
        }
    )
    if preferred:
        for key in _TEXT_KEYS:
            value = event.get(key)
            if isinstance(value, str) and value:
                return value
        item = event.get("item")
        if isinstance(item, Mapping):
            value = _first_string(item, _TEXT_KEYS)
            if value:
                return value
    return None


def _provider_status(event: Mapping[str, Any]) -> str | None:
    """Return a bounded provider status without retaining diagnostic text."""
    event_type = event.get("type")
    if not isinstance(event_type, str) or not event_type.strip():
        return None
    for key in ("status", "subtype"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:64]
    return event_type.strip()[:64]


def _quota_event_evidence(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Recognize explicit exhaustion only in provider failure envelopes.

    The provider's output and tool payloads may contain arbitrary text.  Limit
    structured inspection to the two failure event types currently emitted by
    the Codex transport and to their direct error fields.
    """
    event_type = event.get("type")
    if not isinstance(event_type, str):
        return None
    event_type = event_type.strip().lower()
    if event_type not in _ERROR_EVENT_TYPES:
        return None

    error = event.get("error")
    error_mapping = error if isinstance(error, Mapping) else None
    provider_status = _provider_status(event)
    # Explicit retry/throttling meaning wins over ambiguous quota wording.
    # Only the failure envelope and its direct error object are diagnostic.
    for diagnostic in (event, error_mapping):
        if diagnostic is None:
            continue
        if any(diagnostic.get(key) is not None for key in (
            "retry_after", "retryAfter", "retry_after_seconds",
        )):
            return None
        if any(isinstance(diagnostic.get(key), str)
               and _TRANSIENT_ERROR_RE.search(diagnostic[key])
               for key in ("message", "reason", "code", "error_code", "errorCode",
                           "status", "subtype")):
            return None

    # Keep the actual field path as bounded provenance.  Do not retain the
    # provider's message, which may include billing links or reset timestamps.
    message_fields: list[tuple[str, Any]] = []
    if event_type == "error":
        message_fields.append(("event.message", event.get("message")))
        if error_mapping is not None:
            message_fields.append(("event.error.message", error_mapping.get("message")))
    else:
        if error_mapping is not None:
            message_fields.append(("event.error.message", error_mapping.get("message")))
        message_fields.append(("event.message", event.get("message")))
    # Preserve the older explicit diagnostic fields, but only within a
    # recognized provider-error envelope.
    message_fields.append(("event.reason", event.get("reason")))
    if error_mapping is not None:
        message_fields.append(("event.error.reason", error_mapping.get("reason")))

    for source, value in message_fields:
        if (
            isinstance(value, str)
            and not _TRANSIENT_ERROR_RE.search(value)
            and _QUOTA_TEXT_RE.search(value)
        ):
            return {
                "source": source,
                "confidence": "explicit_provider",
                "provider_status": provider_status or event_type,
            }

    code_fields: list[tuple[str, Any]] = [
        ("event.code", event.get("code")),
        ("event.error_code", event.get("error_code")),
        ("event.errorCode", event.get("errorCode")),
    ]
    if error_mapping is not None:
        code_fields.extend(
            (
                ("event.error.code", error_mapping.get("code")),
                ("event.error.error_code", error_mapping.get("error_code")),
                ("event.error.errorCode", error_mapping.get("errorCode")),
            )
        )
    for source, value in code_fields:
        if isinstance(value, str) and _QUOTA_CODE_RE.fullmatch(value.strip()):
            return {
                "source": source,
                "confidence": "explicit_provider_code",
                "provider_status": provider_status or event_type,
            }

    # An explicit boolean is an existing provider field.  Restrict it to the
    # recognized envelope so nested fixture/tool content remains inert.
    if event.get("quota_exhausted") is True or event.get("quotaExhausted") is True:
        source = (
            "event.quota_exhausted"
            if event.get("quota_exhausted") is True
            else "event.quotaExhausted"
        )
        return {
            "source": source,
            "confidence": "explicit_provider_flag",
            "provider_status": provider_status or event_type,
        }
    if error_mapping is not None and (
        error_mapping.get("quota_exhausted") is True
        or error_mapping.get("quotaExhausted") is True
    ):
        source = (
            "event.error.quota_exhausted"
            if error_mapping.get("quota_exhausted") is True
            else "event.error.quotaExhausted"
        )
        return {
            "source": source,
            "confidence": "explicit_provider_flag",
            "provider_status": provider_status or event_type,
        }
    return None


def parse_codex_events(raw: bytes | str) -> dict[str, Any]:
    """Parse Codex JSONL into response and explicitly observed evidence.

    Malformed or non-JSON lines are retained as a transport diagnostic but do
    not manufacture model, effort, quota, or terminal evidence.  Unknown
    observations stay ``None`` so callers can distinguish absence from a
    provider claim.
    """
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = raw
    events: list[Mapping[str, Any]] = []
    malformed = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            malformed += 1
            continue
        if isinstance(value, Mapping):
            events.append(value)
        else:
            malformed += 1

    response_parts: list[str] = []
    observed_models: list[str] = []
    observed_efforts: list[str] = []
    identifiers: dict[str, str] = {}
    explicit_quota = False
    quota_evidence: dict[str, str] | None = None
    for event in events:
        metadata = event.get("type") in {"model_info", "session.started", "session_meta", "turn_context", "turn.started"}
        for item in _walk(event) if metadata else (event,):
            model = _first_string(item, _MODEL_KEYS) if metadata else None
            if model and model not in observed_models:
                observed_models.append(model)
            effort = _first_string(item, _EFFORT_KEYS) if metadata else None
            if effort and effort not in observed_efforts:
                observed_efforts.append(effort)
            for key in _ID_KEYS:
                value = item.get(key)
                if isinstance(value, str) and value.strip() and key not in identifiers:
                    identifiers[key] = value.strip()
        event_quota_evidence = _quota_event_evidence(event)
        if event_quota_evidence is not None and quota_evidence is None:
            quota_evidence = event_quota_evidence
            explicit_quota = True
        message = _text_from_event(event)
        if message:
            response_parts.append(message)

    # A plain final response can be nested under an item; recover it once
    # without duplicating the explicit event-level extraction above.
    if not response_parts:
        for event in events:
            for item in _walk(event):
                message = _first_string(item, ("final_message", "output_text", "text"))
                if message:
                    response_parts.append(message)
                    break
            if response_parts:
                break

    return {
        "response": "".join(response_parts),
        "effective_model": observed_models[-1] if observed_models else None,
        "effective_effort": observed_efforts[-1] if observed_efforts else None,
        "observed_models": observed_models,
        "observed_efforts": observed_efforts,
        "provider_identifiers": identifiers,
        "malformed_event_lines": malformed,
        "quota": {
            "exhausted": explicit_quota,
            "classification": "explicit_quota_exhaustion"
            if explicit_quota
            else None,
            "source": quota_evidence.get("source") if quota_evidence else None,
            "confidence": quota_evidence.get("confidence", "unknown")
            if quota_evidence
            else "unknown",
            "provider_status": quota_evidence.get("provider_status")
            if quota_evidence
            else None,
        },
    }


def classify_explicit_quota(
    raw: bytes | str,
    *,
    stderr: bytes | str = b"",
    exit_code: int | None = None,
) -> str | None:
    """Return a compatibility pause cause for explicit exhaustion evidence."""
    evidence = classify_quota_evidence(raw, stderr=stderr, exit_code=exit_code)
    return evidence["classification"] if evidence["exhausted"] else None


def classify_quota_evidence(
    raw: bytes | str,
    *,
    stderr: bytes | str = b"",
    exit_code: int | None = None,
) -> dict[str, Any]:
    """Return bounded exhaustion provenance and provider status.

    Failed stderr is considered only after an unsuccessful invocation.  The
    helper retains no provider message, URL, account, or reset-time details.
    """
    parsed = parse_codex_events(raw)
    evidence = dict(parsed["quota"])
    if evidence["exhausted"] or exit_code in (None, 0):
        return evidence

    if exit_code not in (None, 0):
        stderr_text = (
            stderr.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes)
            else stderr
        )
        if (
            _FAILED_STDERR_QUOTA_RE.search(stderr_text)
            and not _TRANSIENT_ERROR_RE.search(stderr_text)
        ):
            status_match = _ANTIGRAVITY_STATUS_RE.search(stderr_text)
            evidence.update(
                {
                    "exhausted": True,
                    "classification": "explicit_quota_exhaustion",
                    "source": "failed_stderr",
                    "confidence": "explicit_failed_stderr",
                    "provider_status": (
                        status_match.group(1)[:64]
                        if status_match is not None
                        else None
                    ),
                }
            )
    return evidence
