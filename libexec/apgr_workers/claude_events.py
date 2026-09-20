"""Bounded Claude stream events, observed identities, and explicit quota evidence."""
from __future__ import annotations
import json
import re
from typing import Any, Iterable, Mapping

_QUOTA_TEXT_RE = re.compile(
    r"(?:^\s*quota\s*(?:is\s*)?exhausted\b|"
    r"^\s*insufficient[_ -]?quota\b|"
    r"^\s*you['’]ve hit your usage limit\.|"
    r"^\s*usage limit exceeded|"
    r"^\s*credit balance is too low)",
    re.IGNORECASE,
)
_QUOTA_CODE_RE = re.compile(
    r"^(?:insufficient[_ -]?quota|quota[_ -]?exhausted|credit_exhausted)$",
    re.IGNORECASE,
)
_TRANSIENT_ERROR_RE = re.compile(
    r"(?:rate[\s_-]*limit|retry[\s_-]*after|per[\s_-]?minute|"
    r"too many requests|temporar(?:y|ily)|throttl)",
    re.IGNORECASE,
)
_FAILED_STDERR_QUOTA_RE = re.compile(
    r"(?:(?:claude(?:\s+code)?:\s*)|)"
    r"(?:you['’]ve hit your usage limit\.|"
    r"quota\s*(?:is\s*)?exhausted\b|"
    r"insufficient[_ -]?quota\b|"
    r"credit balance is too low)",
    re.IGNORECASE,
)
_ERROR_EVENT_TYPES = frozenset({"error", "turn.failed"})
_TEXT_KEYS = ("text", "delta", "content", "message", "output_text", "final_message")
_MODEL_KEYS = ("model", "model_slug", "model_name", "model_id")
_EFFORT_KEYS = ("effort", "perTurnEffort", "reasoning_effort", "model_reasoning_effort")
_ID_KEYS = ("session_id", "sessionId", "thread_id", "threadId", "conversation_id", "uuid")


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
    """Extract model text from common Claude stream-json event shapes."""
    event_type = event.get("type")
    # Assistant messages
    if event_type == "assistant":
        msg = event.get("message")
        if isinstance(msg, Mapping):
            content = msg.get("content")
            if isinstance(content, str) and content:
                return content
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, Mapping) and block.get("type") == "text":
                        t = block.get("text")
                        if isinstance(t, str):
                            parts.append(t)
                if parts:
                    return "".join(parts)
        for key in _TEXT_KEYS:
            val = event.get(key)
            if isinstance(val, str) and val:
                return val

    # Streaming content deltas
    if event_type == "content_block_delta":
        delta = event.get("delta")
        if isinstance(delta, Mapping):
            t = delta.get("text")
            if isinstance(t, str):
                return t

    # Final result / completed turn
    if event_type in {"result", "turn.completed"}:
        res = event.get("result")
        if isinstance(res, str) and res:
            return res
        if isinstance(res, Mapping):
            for key in _TEXT_KEYS:
                val = res.get(key)
                if isinstance(val, str) and val:
                    return val

    return None


def _provider_status(event: Mapping[str, Any]) -> str | None:
    """Return a bounded provider status without retaining diagnostic text."""
    event_type = event.get("type")
    if not isinstance(event_type, str) or not event_type.strip():
        return None
    for key in ("status", "subtype", "terminal_reason"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:64]
    return event_type.strip()[:64]


def _quota_event_evidence(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Recognize explicit exhaustion in Claude provider envelopes."""
    event_type = event.get("type")
    if not isinstance(event_type, str):
        return None
    event_type = event_type.strip().lower()

    is_error = (
        event_type in _ERROR_EVENT_TYPES
        or event.get("is_error") is True
        or event.get("subtype") in {"error", "api_error"}
    )
    if not is_error:
        return None

    error = event.get("error")
    error_mapping = error if isinstance(error, Mapping) else None
    provider_status = _provider_status(event)

    # Check for transient errors / retry-after
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

    # Inspect message fields
    message_fields: list[tuple[str, Any]] = [
        ("event.message", event.get("message")),
        ("event.reason", event.get("reason")),
    ]
    if error_mapping is not None:
        message_fields.extend([
            ("event.error.message", error_mapping.get("message")),
            ("event.error.reason", error_mapping.get("reason")),
        ])

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
        code_fields.extend([
            ("event.error.code", error_mapping.get("code")),
            ("event.error.error_code", error_mapping.get("error_code")),
            ("event.error.errorCode", error_mapping.get("errorCode")),
        ])
    for source, value in code_fields:
        if isinstance(value, str) and _QUOTA_CODE_RE.fullmatch(value.strip()):
            return {
                "source": source,
                "confidence": "explicit_provider_code",
                "provider_status": provider_status or event_type,
            }

    if event.get("quota_exhausted") is True or event.get("quotaExhausted") is True:
        source = "event.quota_exhausted" if event.get("quota_exhausted") is True else "event.quotaExhausted"
        return {
            "source": source,
            "confidence": "explicit_provider_flag",
            "provider_status": provider_status or event_type,
        }
    if error_mapping is not None and (
        error_mapping.get("quota_exhausted") is True or error_mapping.get("quotaExhausted") is True
    ):
        source = "event.error.quota_exhausted" if error_mapping.get("quota_exhausted") is True else "event.error.quotaExhausted"
        return {
            "source": source,
            "confidence": "explicit_provider_flag",
            "provider_status": provider_status or event_type,
        }

    return None


def parse_claude_events(raw: bytes | str) -> dict[str, Any]:
    """Parse Claude stream-json into response and explicitly observed evidence."""
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
    final_response = None
    terminal_result = False
    provider_error = False

    for event in events:
        event_type = event.get("type")
        # Extract model and effort from init, usage, result, or assistant metadata
        metadata = event_type in {
            "system", "session.started", "turn.started", "turn.completed",
            "result", "usage", "assistant", "model_info"
        }
        # Only provider metadata is authoritative. Tool inputs/results and
        # assistant content can contain requested identities and are excluded.
        metadata_items = [event]
        message = event.get("message")
        if event_type == "assistant" and isinstance(message, Mapping):
            metadata_items.append(message)
        for item in metadata_items:
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

        msg = _text_from_event(event)
        if event_type in {"result", "turn.completed"}:
            terminal_result = True
            final_response = msg
        elif msg:
            response_parts.append(msg)
        provider_error |= (event_type in _ERROR_EVENT_TYPES or event.get("is_error") is True
                           or event.get("subtype") in {"error", "api_error"})

    # Consensus model and effort
    unique_models = set(observed_models)
    effective_model = observed_models[0] if len(unique_models) == 1 else None
    unique_efforts = set(observed_efforts)
    effective_effort = observed_efforts[0] if len(unique_efforts) == 1 else None

    return {
        "response": final_response if final_response is not None else "".join(response_parts),
        "terminal_result": terminal_result,
        "provider_error": provider_error,
        "effective_model": effective_model,
        "effective_effort": effective_effort,
        "observed_models": observed_models,
        "observed_efforts": observed_efforts,
        "provider_identifiers": identifiers,
        "malformed_event_lines": malformed,
        "quota": {
            "exhausted": explicit_quota,
            "classification": "explicit_quota_exhaustion" if explicit_quota else None,
            "source": quota_evidence.get("source") if quota_evidence else None,
            "confidence": quota_evidence.get("confidence", "unknown") if quota_evidence else "unknown",
            "provider_status": quota_evidence.get("provider_status") if quota_evidence else None,
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
    """Return bounded exhaustion provenance and provider status for Claude."""
    parsed = parse_claude_events(raw)
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
            evidence.update(
                {
                    "exhausted": True,
                    "classification": "explicit_quota_exhaustion",
                    "source": "failed_stderr",
                    "confidence": "explicit_failed_stderr",
                    "provider_status": "quota_exhausted",
                }
            )
    return evidence
