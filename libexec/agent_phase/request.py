"""Strict `agent-phase-request-v1` parsing.

The request carries phase semantics only. Model, profile, reviewer, and review
cadence are dispatcher policy and are structurally unrepresentable here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple


SCHEMA_NAME = "agent-phase-request-v1"
SCHEMA_V1 = SCHEMA_NAME
SCHEMA_V2 = "agent-phase-request-v2"
PHASE_TYPES = ("implementation_testing", "architecture_docs", "sysadmin")
EXECUTION_MODES = (
    "normal",
    "gemini_sub",
    "gemini_flash_sub",
    "gemini_flash_opus_sub",
    "conserve_claude",
    "claude_only",
    "codex_only",
    "gemini_only",
    "gemini_opus",
    "gemini_fable",
)
WORKER_CAPABLE_MODES = frozenset(
    {
        "gemini_sub",
        "gemini_flash_sub",
        "gemini_flash_opus_sub",
        "gemini_opus",
        "gemini_fable",
    }
)
REQUEST_FIELDS = frozenset({"schema", "phase_type", "execution_mode", "prompt"})
REQUEST_V2_FIELDS = frozenset({"schema", "phase_type", "prompt"})
MAX_PROMPT_BYTES = 256 * 1024
# Headroom for JSON framing and escaping, so the prompt bound is the one that
# actually fires on an oversized prompt rather than being shadowed by this one.
MAX_REQUEST_BYTES = MAX_PROMPT_BYTES + 64 * 1024


class RequestError(ValueError):
    """A request violates the v1 schema."""


class PhaseRequest(NamedTuple):
    phase_type: str
    execution_mode: str
    prompt: str

    def as_dict(self) -> dict[str, str]:
        return {
            "schema": SCHEMA_NAME,
            "phase_type": self.phase_type,
            "execution_mode": self.execution_mode,
            "prompt": self.prompt,
        }


def _unicode_scalars(value: str, field: str) -> str:
    """Reject lone UTF-16 surrogates and combine valid escaped pairs."""
    if not any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        return value
    result: list[str] = []
    index = 0
    while index < len(value):
        codepoint = ord(value[index])
        if 0xD800 <= codepoint <= 0xDBFF:
            if index + 1 >= len(value):
                raise RequestError(
                    f"request field contains an unpaired surrogate: {field}"
                )
            low = ord(value[index + 1])
            if not 0xDC00 <= low <= 0xDFFF:
                raise RequestError(
                    f"request field contains an unpaired surrogate: {field}"
                )
            result.append(chr(
                0x10000 + ((codepoint - 0xD800) << 10) + (low - 0xDC00)
            ))
            index += 2
            continue
        if 0xDC00 <= codepoint <= 0xDFFF:
            raise RequestError(
                f"request field contains an unpaired surrogate: {field}"
            )
        result.append(value[index])
        index += 1
    return "".join(result)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RequestError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_request(raw: bytes) -> PhaseRequest:
    if len(raw) > MAX_REQUEST_BYTES:
        raise RequestError(
            f"request exceeds {MAX_REQUEST_BYTES} bytes: {len(raw)}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RequestError(f"request is not valid UTF-8: {error}") from error
    try:
        value = json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise RequestError(f"request is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise RequestError("request must be a top-level JSON object")
    # One check covers unknown keys and missing keys, so no field can be added
    # by a producer and no field can be silently defaulted by the dispatcher.
    if set(value) != REQUEST_FIELDS:
        raise RequestError(
            f"request keys must be exactly {sorted(REQUEST_FIELDS)}"
        )
    for field, field_value in sorted(value.items()):
        if not isinstance(field_value, str):
            raise RequestError(f"request field must be a string: {field}")
        value[field] = _unicode_scalars(field_value, field)
    if value["schema"] != SCHEMA_NAME:
        raise RequestError(f"request schema must be {SCHEMA_NAME}")
    if value["phase_type"] not in PHASE_TYPES:
        raise RequestError(f"unsupported phase_type: {value['phase_type']}")
    if value["execution_mode"] not in EXECUTION_MODES:
        raise RequestError(f"unsupported execution_mode: {value['execution_mode']}")
    prompt = value["prompt"]
    if not prompt.strip():
        raise RequestError("prompt must be non-empty")
    prompt_bytes = len(prompt.encode("utf-8"))
    if prompt_bytes > MAX_PROMPT_BYTES:
        raise RequestError(
            f"prompt exceeds {MAX_PROMPT_BYTES} bytes: {prompt_bytes}"
        )
    return PhaseRequest(value["phase_type"], value["execution_mode"], prompt)


def load_request(path: Path) -> PhaseRequest:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise RequestError(f"cannot read request {path}: {error}") from error
    return parse_request(raw)


class PhaseRequestV2(NamedTuple):
    phase_type: str
    prompt: str
    schema: str = SCHEMA_V2

    def as_dict(self) -> dict[str, str]:
        return {
            "schema": self.schema,
            "phase_type": self.phase_type,
            "prompt": self.prompt,
        }


def parse_request_v2(raw: bytes) -> PhaseRequestV2:
    if len(raw) > MAX_REQUEST_BYTES:
        raise RequestError(
            f"request exceeds {MAX_REQUEST_BYTES} bytes: {len(raw)}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RequestError(f"request is not valid UTF-8: {error}") from error
    try:
        value = json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as error:
        raise RequestError(f"request is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise RequestError("request must be a top-level JSON object")
    if set(value) != REQUEST_V2_FIELDS:
        unsupported = sorted(set(value) - REQUEST_V2_FIELDS)
        if unsupported:
            raise RequestError(
                f"unsupported request key for {SCHEMA_V2}: {unsupported[0]}; "
                f"request keys must be exactly {sorted(REQUEST_V2_FIELDS)}"
            )
        raise RequestError(
            f"request keys must be exactly {sorted(REQUEST_V2_FIELDS)}"
        )
    for field, field_value in sorted(value.items()):
        if not isinstance(field_value, str):
            raise RequestError(f"request field must be a string: {field}")
        value[field] = _unicode_scalars(field_value, field)
    if value["schema"] != SCHEMA_V2:
        raise RequestError(f"request schema must be {SCHEMA_V2}")
    if value["phase_type"] not in PHASE_TYPES:
        raise RequestError(f"unsupported phase_type: {value['phase_type']}")
    prompt = value["prompt"]
    if not prompt.strip():
        raise RequestError("prompt must be non-empty")
    prompt_bytes = len(prompt.encode("utf-8"))
    if prompt_bytes > MAX_PROMPT_BYTES:
        raise RequestError(
            f"prompt exceeds {MAX_PROMPT_BYTES} bytes: {prompt_bytes}"
        )
    return PhaseRequestV2(value["phase_type"], prompt)


def load_request_v2(path: Path) -> PhaseRequestV2:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise RequestError(f"cannot read request {path}: {error}") from error
    return parse_request_v2(raw)


def parse_any_request(raw: bytes) -> PhaseRequest | PhaseRequestV2:
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(data, dict) and data.get("schema") == SCHEMA_V2:
            return parse_request_v2(raw)
    except Exception:
        pass
    return parse_request(raw)


def load_any_request(path: Path) -> PhaseRequest | PhaseRequestV2:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise RequestError(f"cannot read request {path}: {error}") from error
    return parse_any_request(raw)
