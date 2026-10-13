"""Provider-result importers for the APG166D execution package.

The three provider routes do not share a terminal wire format.  This module
keeps the provider bytes as an external receipt and extracts only fields that
were actually present in the receipt.  In particular, a successful process or
human-readable answer never becomes a semantic task-success claim here; the
task oracle owns that decision.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Iterable, Mapping

from . import response_contract


SCHEMA = "apg.h-provider-import/v1"
QUALIFICATION_SCHEMA = "apg.h-importer-qualification/v1"
PROVIDERS = frozenset({"codex", "claude", "antigravity"})
_QUALIFICATION_SCENARIOS = frozenset(f"scenario-{number:02d}" for number in range(1, 16))
_REVIEW_SCENARIOS = frozenset({"scenario-03", "scenario-11", "scenario-12", "scenario-14"})
_ERROR_TERMINAL_REASONS = frozenset({
    "aborted",
    "api_error",
    "canceled",
    "cancelled",
    "error",
    "failed",
    "failure",
    "interrupted",
    "timed_out",
    "timeout",
})
_FINDING_FIELDS = (
    "producer_revisions",
    "missing_guidance_findings",
    "restart_required_incidents",
)
_SESSION_FIELDS = (
    "session_id",
    "sessionId",
    "thread_id",
    "threadId",
    "conversation_id",
    "conversationId",
)
def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def _route_identity(route: Mapping[str, Any]) -> dict[str, Any]:
    """Return the observed route identity without inventing provider facts."""
    if not isinstance(route, Mapping):
        raise ValueError("provider route must be an object")
    provider = route.get("provider")
    if provider not in PROVIDERS:
        raise ValueError("unsupported provider route")
    identity: dict[str, Any] = {"provider": provider}
    for key in ("profile", "model", "binding_id", "execution", "requested_mode"):
        if key in route:
            identity[key] = route[key]
    role_binding = route.get("role_binding")
    if isinstance(role_binding, Mapping):
        for key in ("binding_id", "roles"):
            if key in role_binding and key not in identity:
                identity[key] = role_binding[key]
    if "roles" in route:
        identity["roles"] = route["roles"]
    return identity


def _json_values(raw: bytes) -> tuple[list[Any], str]:
    """Decode a whole JSON result or a JSON-lines terminal stream.

    A non-JSON provider answer is still a usable terminal text receipt.  A
    stream containing a malformed JSON line is classified as malformed rather
    than silently accepting a later line.
    """
    if not raw.strip():
        return [], "empty"
    try:
        return [json.loads(raw)], "structured"
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    lines = raw.splitlines()
    if not lines or any(not line.strip() for line in lines):
        return [], "text"
    values: list[Any] = []
    for line in lines:
        try:
            values.append(json.loads(line))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return [], "text"
    return values, "structured"


_INSTRUMENTED_SCHEMA = "apg.instrumented-provider/v1"


def _contains_instrumented_envelope(value: Any, *, depth: int = 0) -> bool:
    """Detect a fake-provider envelope at any structured wire position.

    A live provider answer may be arbitrary text, but a structured fake
    envelope nested inside a result is still an attempted instrumented route.
    Inspecting only the top-level object allowed that envelope to masquerade as
    a Claude/Codex terminal result.
    """
    if depth > 12:
        return False
    if isinstance(value, Mapping):
        if value.get("schema") == _INSTRUMENTED_SCHEMA:
            return True
        return any(_contains_instrumented_envelope(child, depth=depth + 1)
                   for child in value.values())
    if isinstance(value, list):
        return any(_contains_instrumented_envelope(child, depth=depth + 1)
                   for child in value)
    return False


def _review_response(
    parsed_result: Any,
    envelopes: list[dict[str, Any]],
    route: Mapping[str, Any],
) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    """Import the answer-neutral review envelope, if one was emitted.

    Only the terminal ``result`` value or the explicit instrumented fixture
    field is considered.  Recursive searching through arbitrary provider
    payloads would allow a model-authored nested object to become a second
    trusted answer.
    """
    candidate = parsed_result
    if isinstance(candidate, Mapping) and "review_response" in candidate:
        candidate = candidate["review_response"]
    if candidate is None:
        for envelope in reversed(envelopes):
            if envelope.get("schema") == _INSTRUMENTED_SCHEMA:
                candidate = envelope.get("review_response", envelope.get("evaluation_response"))
                if candidate is not None:
                    break
    scenario_id = route.get("scenario_id") if isinstance(route.get("scenario_id"), str) else None
    status, response = response_contract.parse_optional(candidate, scenario_id=scenario_id)
    if status != "accepted":
        return status, None, None
    return status, response, response_contract.identity(response)


def _top_level_objects(values: Iterable[Any]) -> Iterable[dict[str, Any]]:
    """Yield only provider envelope candidates.

    Provider task output is opaque to the importer.  Recursing through a
    result, message, or arbitrary JSON object would let a model's answer
    masquerade as a provider model/session identity.  Runtime observations
    therefore come only from top-level wire envelopes with a known marker.
    """
    for value in values:
        if isinstance(value, dict):
            yield value


def _known_envelopes(provider: str, values: list[Any], *, instrumented: bool = False) -> list[dict[str, Any]]:
    envelopes: list[dict[str, Any]] = []
    for value in _top_level_objects(values):
        if value.get("schema") == _INSTRUMENTED_SCHEMA:
            if instrumented:
                envelopes.append(value)
            continue
        marker = value.get("type")
        subtype = value.get("subtype")
        if provider == "claude" and (
            (marker == "system" and subtype == "init")
            or marker in {"result", "final"}
        ):
            envelopes.append(value)
        elif provider == "codex" and marker in {
            "thread.started", "turn.started", "turn.completed", "result", "final"
        }:
            envelopes.append(value)
        elif provider == "antigravity" and marker in {
            "result", "final", "completion", "terminal"
        }:
            envelopes.append(value)
    return envelopes


def _result_value(envelopes: list[dict[str, Any]]) -> tuple[Any, dict[str, Any] | None]:
    for value in reversed(envelopes):
        if "result" in value:
            return value["result"], value
        if value.get("type") in ("result", "final", "completion", "terminal"):
            for key in ("text", "output", "content", "message"):
                if key in value:
                    return value[key], value
    return None, None


def _result_identity(value: Any, raw: bytes) -> dict[str, Any]:
    if value is None:
        return {"kind": "raw", "bytes": len(raw), "sha256": _sha256(raw)}
    if isinstance(value, str):
        data = value.encode()
        return {"kind": "text", "bytes": len(data), "sha256": _sha256(data)}
    data = _canonical(value)
    return {"kind": "structured", "bytes": len(data), "sha256": _sha256(data)}


def _session(envelopes: list[dict[str, Any]]) -> dict[str, str] | None:
    found: dict[str, str] = {}
    for obj in envelopes:
        for key in _SESSION_FIELDS:
            value = obj.get(key)
            if isinstance(value, str) and value:
                found[key] = value
    return found or None


def _observed_list(envelopes: list[dict[str, Any]], key: str) -> list[Any] | None:
    value = next((item[key] for item in envelopes if key in item), None)
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"provider field {key} must be a list")
    return value


def _provider_error(
    values: list[Any],
    terminal_record: dict[str, Any] | None,
) -> tuple[dict[str, Any], bool]:
    """Retain provider error signals without promoting raw status text.

    Claude emits authentication failures on an assistant envelope and the
    terminal error details on the later result envelope.  The result subtype
    is deliberately not used here: native Claude can report ``subtype=success``
    alongside ``is_error=true``.  The second return value records the presence
    of an API-error assistant marker even when its error value is absent.
    """
    record = terminal_record if isinstance(terminal_record, Mapping) else {}
    assistant_errors: list[str] = []
    assistant_api_error = False
    for value in values:
        if not isinstance(value, Mapping) or value.get("type") != "assistant":
            continue
        if value.get("is_api_error_message") is True:
            assistant_api_error = True
            error = value.get("error")
            if isinstance(error, str) and error:
                assistant_errors.append(error)
    provider_error = {
        "is_error": record.get("is_error") if "is_error" in record else None,
        "terminal_reason": record.get("terminal_reason") if "terminal_reason" in record else None,
        "api_error_status": record.get("api_error_status") if "api_error_status" in record else None,
        "assistant_errors": assistant_errors,
    }
    reason = provider_error["terminal_reason"]
    normalized_reason = reason.casefold() if isinstance(reason, str) else None
    status = provider_error["api_error_status"]
    status_error = status not in (None, False, "", "0", 0)
    explicit_error = (
        provider_error["is_error"] is True
        or normalized_reason in _ERROR_TERMINAL_REASONS
        or (isinstance(normalized_reason, str) and normalized_reason.endswith("_error"))
        or status_error
        or assistant_api_error
    )
    return provider_error, explicit_error


def _successful_terminal(provider: str, terminal_record: dict[str, Any] | None) -> bool:
    """Return whether a recognized terminal carries its provider success value."""
    if not isinstance(terminal_record, Mapping):
        return False
    if provider == "claude":
        return terminal_record.get("subtype") == "success"
    return terminal_record.get("status") == "completed"


def _provider_outcome(
    provider: str,
    terminal_record: dict[str, Any] | None,
    provider_error: Mapping[str, Any],
    explicit_error: bool,
    terminal: Mapping[str, Any] | None,
) -> str | None:
    """Classify provider execution independently from task-result semantics."""
    exit_code = terminal.get("exit_code") if isinstance(terminal, Mapping) else None
    process_error = False
    if isinstance(terminal, Mapping):
        process_error = (
            isinstance(exit_code, int)
            and not isinstance(exit_code, bool)
            and exit_code != 0
        ) or any(bool(terminal.get(key)) for key in ("timeout", "truncated", "signal"))
    if explicit_error or process_error:
        return "error"
    if not _successful_terminal(provider, terminal_record):
        return None
    if provider_error.get("is_error") is True:
        return "error"
    return "success"


def import_provider_output(
    raw: bytes,
    route: Mapping[str, Any],
    *,
    terminal: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Import one provider's actual terminal bytes.

    ``terminal`` is dispatcher-owned process evidence (exit status, truncation,
    and cleanup facts).  It is retained separately from provider-reported
    status.  The returned ``observed`` fields are ``None`` when a provider did
    not emit that field; callers must not turn absence into a positive claim.
    """
    if not isinstance(raw, bytes):
        raise TypeError("provider output must be bytes")
    identity = _route_identity(route)
    values, parse_status = _json_values(raw)
    empty_provider_error, _ = _provider_error(values, None)
    # A live route must never accept an instrumented provider envelope, even
    # when a fake was nested beneath a native-looking result object.
    if identity.get("execution") == "live" and _contains_instrumented_envelope(values):
        return {
            "schema": SCHEMA,
            "provider": identity["provider"],
            "route": identity,
            "terminal": dict(terminal or {}),
            "provider_terminal_status": None,
            "provider_error": empty_provider_error,
            "provider_outcome": None,
            "raw": {"bytes": len(raw), "sha256": _sha256(raw)},
            "parse_status": "malformed",
            "result": {"kind": "raw", "bytes": len(raw), "sha256": _sha256(raw)},
            "session": None,
            "observed_model": None,
            "observed": {key: None for key in _FINDING_FIELDS},
            "model_observed": None,
            "review_response": None,
            "review_response_status": "malformed",
            "review_response_identity": None,
            **{key: None for key in _FINDING_FIELDS},
        }
    envelopes = _known_envelopes(identity["provider"], values, instrumented=identity.get("execution") == "instrumented")
    # Structured task JSON without a recognized provider terminal envelope is
    # ambiguous.  Keep its raw identity but refuse to treat it as a terminal
    # result; a non-JSON human-readable answer remains a valid text receipt.
    if parse_status == "structured" and not envelopes:
        parse_status = "malformed"
    parsed_result, terminal_record = _result_value(envelopes)
    observed_status = None
    if terminal_record is not None:
        for key in ("status", "subtype", "event", "type"):
            if isinstance(terminal_record.get(key), str):
                observed_status = terminal_record[key]
                break
    observed_model = next((item.get("model") for item in envelopes), None)
    if not isinstance(observed_model, str) or not observed_model:
        observed_model = None
    provider_error, explicit_error = _provider_error(values, terminal_record)
    provider_outcome = _provider_outcome(
        identity["provider"], terminal_record, provider_error, explicit_error, terminal
    )
    # Only the explicit fake-provider protocol owns these test-only fields.
    # Native provider envelopes do not attest semantic guidance use or findings.
    instrumented = [item for item in envelopes if item.get("schema") == _INSTRUMENTED_SCHEMA]
    observed = {key: _observed_list(instrumented, key) for key in _FINDING_FIELDS}
    model_observed = next((item.get("model_observed") for item in instrumented if "model_observed" in item), None)
    if model_observed is not None and not isinstance(model_observed, (bool, type(None))):
        raise ValueError("model_observed must be boolean or null")
    review_response_status, review_response, review_identity = _review_response(
        parsed_result, envelopes, route
    )
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "provider": identity["provider"],
        "route": identity,
        "terminal": dict(terminal or {}),
        "provider_terminal_status": observed_status,
        "provider_error": provider_error,
        "provider_outcome": provider_outcome,
        "raw": {"bytes": len(raw), "sha256": _sha256(raw)},
        "parse_status": parse_status,
        "result": _result_identity(parsed_result, raw),
        "session": _session(envelopes),
        "observed_model": observed_model,
        "observed": observed,
        "model_observed": model_observed,
        "review_response": review_response,
        "review_response_status": review_response_status,
        "review_response_identity": review_identity,
    }
    # These aliases make the receipt useful to existing pair consumers while
    # retaining None for provider formats that do not expose the field.
    result.update(observed)
    return result


def _for_provider(provider: str, raw: bytes, route: Mapping[str, Any], terminal: Mapping[str, Any] | None) -> dict[str, Any]:
    if route.get("provider") != provider:
        raise ValueError(f"{provider} importer received a different provider route")
    return import_provider_output(raw, route, terminal=terminal)


def import_codex(raw: bytes, route: Mapping[str, Any], *, terminal: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return _for_provider("codex", raw, route, terminal)


def import_claude(raw: bytes, route: Mapping[str, Any], *, terminal: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return _for_provider("claude", raw, route, terminal)


def import_antigravity(raw: bytes, route: Mapping[str, Any], *, terminal: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return _for_provider("antigravity", raw, route, terminal)


def importer_for(provider: str) -> Callable[..., dict[str, Any]]:
    """Return the importer for a frozen provider route."""
    try:
        return {"codex": import_codex, "claude": import_claude, "antigravity": import_antigravity}[provider]
    except KeyError as error:
        raise ValueError("unsupported provider") from error


def _qualification_route(provider: str, scenario_id: str, *, execution: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "profile": "qualification-profile",
        "model": "qualification-model",
        "binding_id": f"qualification-{provider}",
        "roles": ["Work Review"],
        "execution": execution,
        "scenario_id": scenario_id,
    }


def _qualification_wire(provider: str, result: Any) -> bytes:
    """Build a source-owned terminal fixture for one provider protocol."""
    if provider == "claude":
        values = [
            {"type": "system", "subtype": "init", "session_id": "qualification-session",
             "model": "qualification-model"},
            {"type": "result", "subtype": "success", "session_id": "qualification-session",
             "result": result},
        ]
    elif provider == "codex":
        values = [
            {"type": "thread.started", "thread_id": "qualification-thread"},
            {"type": "result", "status": "completed", "result": result},
        ]
    else:
        values = [{"type": "result", "status": "completed", "output": result}]
    return ("\n".join(json.dumps(value, sort_keys=True) for value in values) + "\n").encode("utf-8")


def _qualification_identity(raw: bytes, imported: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "raw": {"bytes": len(raw), "sha256": _sha256(raw)},
        "parse_status": imported.get("parse_status"),
        "review_response_status": imported.get("review_response_status"),
        "result": imported.get("result"),
    }


def qualify_importer(provider: str, scenario_id: str) -> dict[str, Any]:
    """Qualify one importer with source-owned positive and negative wires.

    The fixtures exercise only the byte importer.  They never start a provider
    process and their structured review response contains no scenario oracle
    facts.  A separate live-route fake envelope check proves that an
    instrumented result cannot masquerade as a native provider terminal.
    """
    if provider not in PROVIDERS:
        raise ValueError("unsupported provider")
    if scenario_id not in _QUALIFICATION_SCENARIOS:
        raise ValueError("unknown frozen scenario")
    review = None
    if scenario_id in _REVIEW_SCENARIOS:
        review = {
            "schema": response_contract.SCHEMA,
            "scenario_id": scenario_id,
            "summary": "Qualification response fixture.",
            "findings": [{
                "path": "docs/fixture.md",
                "category": "fixture",
                "summary": "A bounded source-owned fixture finding.",
                "evidence": ["fixture evidence"],
            }],
            "limitations": [],
        }
    good_raw = _qualification_wire(provider, review or "qualification-result")
    good_route = _qualification_route(provider, scenario_id, execution="instrumented")
    good = import_provider_output(good_raw, good_route, terminal={"exit_code": 0})

    malformed_response = {
        "schema": response_contract.SCHEMA,
        "scenario_id": scenario_id,
        "summary": "Malformed qualification response.",
        "findings": [{"path": "docs/fixture.md", "category": "fixture"}],
    }
    if review is not None:
        bad_raw = _qualification_wire(provider, malformed_response)
    else:
        # An unrecognized structured terminal must be classified as malformed;
        # arbitrary JSON is never accepted as a provider result.
        bad_raw = (json.dumps({"type": "unrecognized", "result": "fixture"}) + "\n").encode()
    bad = import_provider_output(bad_raw, good_route, terminal={"exit_code": 0})

    fake = {"schema": _INSTRUMENTED_SCHEMA, "result": "fake", "model_observed": True}
    live_fake_raw = _qualification_wire(provider, {"nested": fake})
    live_fake = import_provider_output(
        live_fake_raw,
        _qualification_route(provider, scenario_id, execution="live"),
        terminal={"exit_code": 0},
    )

    good_ok = (good.get("schema") == SCHEMA and good.get("parse_status") == "structured"
               and (review is None or good.get("review_response_status") == "accepted"))
    bad_ok = (bad.get("parse_status") == ("structured" if review is not None else "malformed")
              and (review is None or bad.get("review_response_status") == "malformed"))
    live_fake_ok = (live_fake.get("parse_status") == "malformed"
                    and live_fake.get("session") is None
                    and live_fake.get("model_observed") is None)
    result = {
        "schema": QUALIFICATION_SCHEMA,
        "provider": provider,
        "scenario_id": scenario_id,
        "provider_invocations": 0,
        "status": "complete" if good_ok and bad_ok and live_fake_ok else "incomplete",
        "good": _qualification_identity(good_raw, good),
        "bad": _qualification_identity(bad_raw, bad),
        "live_fake": _qualification_identity(live_fake_raw, live_fake),
    }
    if not good_ok:
        result["reason"] = "positive provider wire did not satisfy importer contract"
    elif not bad_ok:
        result["reason"] = "negative provider wire was accepted"
    elif not live_fake_ok:
        result["reason"] = "live instrumented provider wire was accepted"
    return result


def pair_fields(imported: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt an explicit structured result to the legacy pair callback shape.

    This adapter refuses provider formats that did not actually expose the
    fields rather than manufacturing empty finding lists.
    """
    if imported.get("parse_status") not in ("structured", "text"):
        raise ValueError("provider terminal result is unavailable")
    values = {key: imported.get(key) for key in _FINDING_FIELDS}
    if any(value is None for value in values.values()):
        raise ValueError("provider finding fields were not observed")
    return {**values, "model_observed": imported.get("model_observed")}


__all__ = [
    "SCHEMA",
    "import_provider_output",
    "import_codex",
    "import_claude",
    "import_antigravity",
    "importer_for",
    "qualify_importer",
    "pair_fields",
]
