"""Fail-closed structured review responses for the H evaluation harness.

The response contract is deliberately small.  It describes the shape of a
review answer, but it never contains the expected findings for a scenario.
Those facts remain owned by :mod:`testing.h_eval.oracles`.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping


SCHEMA = "apg.h-evaluation-response/v1"
MAX_FINDINGS = 128
MAX_SUMMARY_BYTES = 8 << 10
MAX_FINDING_SUMMARY_BYTES = 8 << 10
MAX_EVIDENCE_ITEMS = 32
MAX_EVIDENCE_BYTES = 8 << 10
_PATH_PARTS = re.compile(r"^[^/\\\x00]+$")
_CATEGORY = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_FIELDS = frozenset({"path", "category", "summary", "evidence"})
_TOP_LEVEL_FIELDS = frozenset({"schema", "scenario_id", "summary", "findings", "limitations"})
_EVIDENCE_FIELDS = frozenset({
    "source_path", "span", "snippet", "link_target", "return_expression",
    "declaration",
})


class ResponseContractError(ValueError):
    """A provider result does not contain the frozen review response shape."""


def _encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResponseContractError(f"{field} must be a non-empty string")
    if len(value.encode("utf-8")) > limit:
        raise ResponseContractError(f"{field} exceeds contract bound")
    return value


def _path(value: Any) -> str:
    value = _text(value, "finding path", 1024)
    if value.startswith(("/", "\\")) or ":" in value.split("/", 1)[0]:
        raise ResponseContractError("finding path must be relative")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or not _PATH_PARTS.fullmatch(part) for part in parts):
        raise ResponseContractError("finding path is unsafe")
    return value


def _span(value: Any) -> dict[str, int]:
    if isinstance(value, list) and len(value) == 2:
        start, end = value
    elif isinstance(value, Mapping) and set(value) == {"start", "end"}:
        start, end = value["start"], value["end"]
    else:
        raise ResponseContractError("source span must contain start and end")
    if (type(start) is not int or type(end) is not int or start < 1
            or end < start or end - start > MAX_EVIDENCE_ITEMS):
        raise ResponseContractError("source span is invalid")
    return {"start": start, "end": end}


def _objective_value(value: Any) -> Any:
    if isinstance(value, str):
        return _text(value, "objective evidence", MAX_EVIDENCE_BYTES)
    if isinstance(value, Mapping):
        if not value or any(not isinstance(key, str) for key in value):
            raise ResponseContractError("objective evidence mapping is invalid")
        normalized = {key: _text(item, "objective evidence value", 1024)
                      for key, item in value.items()}
    elif isinstance(value, list):
        if not value or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ResponseContractError("objective evidence list is invalid")
        normalized = [_text(item, "objective evidence value", 1024) for item in value]
    else:
        raise ResponseContractError("objective evidence value is invalid")
    if len(_encoded(normalized)) > MAX_EVIDENCE_BYTES:
        raise ResponseContractError("objective evidence exceeds contract bound")
    return normalized


def _objective_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    unknown = set(value) - _EVIDENCE_FIELDS
    if unknown:
        raise ResponseContractError("unknown objective evidence fields")
    if "source_path" not in value or "span" not in value or "snippet" not in value:
        raise ResponseContractError("objective evidence source binding is incomplete")
    result: dict[str, Any] = {
        "source_path": _path(value["source_path"]),
        "span": _span(value["span"]),
        "snippet": _text(value["snippet"], "source snippet", MAX_EVIDENCE_BYTES),
    }
    if "link_target" in value:
        result["link_target"] = _text(value["link_target"], "link target", MAX_EVIDENCE_BYTES)
    if "return_expression" in value:
        result["return_expression"] = _text(
            value["return_expression"], "return expression", MAX_EVIDENCE_BYTES
        )
    if "declaration" in value:
        result["declaration"] = _objective_value(value["declaration"])
    return result


def _evidence(value: Any) -> list[Any]:
    if not isinstance(value, list) or not value or len(value) > MAX_EVIDENCE_ITEMS:
        raise ResponseContractError("finding evidence must be a bounded non-empty list")
    result: list[Any] = []
    total = 0
    for item in value:
        if isinstance(item, Mapping):
            normalized: Any = _objective_evidence(item)
        else:
            # Keep the envelope parser backward-compatible for unrelated
            # custody tests.  Review-oracle qualification accepts only the
            # objective mapping form above; prose strings cannot satisfy a
            # source fact.
            normalized = _text(item, "finding evidence", MAX_EVIDENCE_BYTES)
        total += len(_encoded(normalized))
        if total > MAX_EVIDENCE_BYTES:
            raise ResponseContractError("finding evidence exceeds contract bound")
        result.append(normalized)
    return result


def validate(value: Mapping[str, Any], *, scenario_id: str | None = None) -> dict[str, Any]:
    """Validate and normalize one review response.

    Unknown fields are rejected so a provider cannot smuggle a second result
    or a self-described acceptance bit through the response envelope.
    """
    if not isinstance(value, Mapping):
        raise ResponseContractError("review response must be an object")
    unknown = set(value) - _TOP_LEVEL_FIELDS
    if unknown:
        raise ResponseContractError("unknown review response fields")
    if value.get("schema") != SCHEMA:
        raise ResponseContractError("review response schema mismatch")
    observed_scenario = _text(value.get("scenario_id"), "scenario_id", 128)
    if scenario_id is not None and observed_scenario != scenario_id:
        raise ResponseContractError("review response scenario mismatch")
    summary = _text(value.get("summary"), "summary", MAX_SUMMARY_BYTES)
    findings_value = value.get("findings")
    if not isinstance(findings_value, list) or len(findings_value) > MAX_FINDINGS:
        raise ResponseContractError("review findings must be a bounded list")
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in findings_value:
        if not isinstance(raw, Mapping) or set(raw) != _FIELDS:
            raise ResponseContractError("review finding fields are incomplete or unknown")
        finding = {
            "path": _path(raw["path"]),
            "category": _text(raw["category"], "finding category", 64).lower(),
            "summary": _text(raw["summary"], "finding summary", MAX_FINDING_SUMMARY_BYTES),
            "evidence": _evidence(raw["evidence"]),
        }
        if not _CATEGORY.fullmatch(finding["category"]):
            raise ResponseContractError("finding category is not normalized")
        key = (finding["category"], finding["path"])
        if key in seen:
            raise ResponseContractError("duplicate review finding")
        seen.add(key)
        findings.append(finding)
    limitations_value = value.get("limitations", [])
    if not isinstance(limitations_value, list) or len(limitations_value) > 32:
        raise ResponseContractError("review limitations must be a bounded list")
    limitations = [_text(item, "review limitation", MAX_EVIDENCE_BYTES)
                   for item in limitations_value]
    return {
        "schema": SCHEMA,
        "scenario_id": observed_scenario,
        "summary": summary,
        "findings": findings,
        "limitations": limitations,
    }


def parse(value: Any, *, scenario_id: str | None = None) -> dict[str, Any]:
    """Decode and validate an envelope supplied by a provider result."""
    if isinstance(value, (bytes, bytearray)):
        try:
            value = json.loads(bytes(value).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResponseContractError("review response is not valid UTF-8 JSON") from exc
    elif isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ResponseContractError("review response is not valid JSON") from exc
    return validate(value, scenario_id=scenario_id)


def parse_optional(value: Any, *, scenario_id: str | None = None) -> tuple[str, dict[str, Any] | None]:
    """Return ``missing``, ``accepted`` or ``malformed`` without guessing."""
    if value is None:
        return "missing", None
    try:
        return "accepted", parse(value, scenario_id=scenario_id)
    except ResponseContractError:
        return "malformed", None


def identity(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return the retained byte identity of a validated response."""
    normalized = validate(value)
    encoded = _encoded(normalized)
    return {"bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def instructions() -> str:
    """Stable, answer-neutral instructions for a review response."""
    return (
        "Return one JSON object with schema apg.h-evaluation-response/v1, "
        "scenario_id, summary, findings, and limitations. Each finding must "
        "contain path, category, summary, and a non-empty evidence list. Each "
        "objective evidence item must contain source_path, span with one-based "
        "start/end lines, and the exact source snippet for that span. Optional "
        "link_target, return_expression, or declaration fields may further "
        "identify the reported fact. Use repository-relative paths and concise evidence; "
        "do not add fields. "
        "Category is a descriptive label of your choice, not an acceptance code. "
        "Summary and category prose are descriptive only; acceptance follows "
        "the source-bound evidence. "
        "Use 1-64 lowercase letters, digits, dots, underscores or hyphens, "
        "starting with a letter or digit."
    )


__all__ = [
    "SCHEMA",
    "ResponseContractError",
    "identity",
    "instructions",
    "parse",
    "parse_optional",
    "validate",
]
