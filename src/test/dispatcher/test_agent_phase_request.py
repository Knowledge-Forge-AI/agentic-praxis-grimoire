from __future__ import annotations

import json

import pytest

from agent_phase.request import (
    MAX_PROMPT_BYTES,
    MAX_REQUEST_BYTES,
    PHASE_TYPES,
    EXECUTION_MODES,
    RequestError,
    parse_request,
)


def encode(payload: dict[str, object]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def valid() -> dict[str, object]:
    return {
        "schema": "agent-phase-request-v1",
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "prompt": "do the bounded thing",
    }


def test_valid_request_round_trips() -> None:
    for mode in ("normal", "conserve_claude"):
        payload = valid() | {"execution_mode": mode}
        request = parse_request(encode(payload))
        assert request.phase_type == "implementation_testing"
        assert request.execution_mode == mode
        assert request.prompt == "do the bounded thing"
        assert request.as_dict() == payload


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
@pytest.mark.parametrize("execution_mode", EXECUTION_MODES)
def test_every_allowed_combination_parses(phase_type: str, execution_mode: str) -> None:
    payload = valid() | {"phase_type": phase_type, "execution_mode": execution_mode}
    request = parse_request(encode(payload))
    assert (request.phase_type, request.execution_mode) == (phase_type, execution_mode)


def test_duplicate_top_level_key_is_rejected() -> None:
    raw = (
        b'{"schema":"agent-phase-request-v1","phase_type":"sysadmin",'
        b'"phase_type":"architecture_docs","execution_mode":"normal","prompt":"x"}'
    )
    with pytest.raises(RequestError, match="duplicate JSON key"):
        parse_request(raw)


def test_duplicate_nested_key_is_rejected() -> None:
    raw = b'{"schema":"agent-phase-request-v1","nested":{"a":1,"a":2}}'
    with pytest.raises(RequestError, match="duplicate JSON key"):
        parse_request(raw)


def test_unknown_key_is_rejected() -> None:
    payload = valid() | {"model": "claude-opus-5"}
    with pytest.raises(RequestError, match="exactly"):
        parse_request(encode(payload))


@pytest.mark.parametrize("field", sorted(valid()))
def test_missing_field_is_rejected(field: str) -> None:
    payload = valid()
    del payload[field]
    with pytest.raises(RequestError, match="exactly"):
        parse_request(encode(payload))


@pytest.mark.parametrize(
    "field",
    [
        "model",
        "profile",
        "reviewer",
        "review_checkpoints",
        "effort",
        "stage",
        "stages",
    ],
)
def test_routing_fields_are_structurally_unrepresentable(field: str) -> None:
    payload = valid() | {field: "anything"}
    with pytest.raises(RequestError, match="exactly"):
        parse_request(encode(payload))


def test_wrong_schema_value_is_rejected() -> None:
    payload = valid() | {"schema": "agent-phase-request-v2"}
    with pytest.raises(RequestError, match="schema must be"):
        parse_request(encode(payload))


def test_unsupported_enum_values_are_rejected() -> None:
    with pytest.raises(RequestError, match="unsupported phase_type"):
        parse_request(encode(valid() | {"phase_type": "research"}))
    with pytest.raises(RequestError, match="unsupported execution_mode"):
        parse_request(encode(valid() | {"execution_mode": "unsupported_mode"}))


@pytest.mark.parametrize("prompt", ["", "   ", "\n\t "])
def test_empty_prompt_is_rejected(prompt: str) -> None:
    with pytest.raises(RequestError, match="non-empty"):
        parse_request(encode(valid() | {"prompt": prompt}))


@pytest.mark.parametrize("value", [1, True, None, ["a"], {"a": 1}])
def test_non_string_field_is_rejected(value: object) -> None:
    with pytest.raises(RequestError, match="must be a string"):
        parse_request(encode(valid() | {"prompt": value}))


def test_non_object_top_level_is_rejected() -> None:
    for raw in (b'["a"]', b'"a"', b"42", b"null"):
        with pytest.raises(RequestError, match="top-level JSON object"):
            parse_request(raw)


def test_invalid_utf8_is_rejected() -> None:
    with pytest.raises(RequestError, match="not valid UTF-8"):
        parse_request(b'{"schema":"\xff\xfe"}')


@pytest.mark.parametrize("escaped", [br"\ud800", br"\udc00"])
def test_escaped_lone_surrogate_is_rejected_as_request_error(
    escaped: bytes,
) -> None:
    raw = (
        br'{"schema":"agent-phase-request-v1",'
        br'"phase_type":"implementation_testing",'
        br'"execution_mode":"normal","prompt":"'
        + escaped
        + br'"}'
    )

    with pytest.raises(RequestError, match="surrogate"):
        parse_request(raw)


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(RequestError, match="not valid JSON"):
        parse_request(b"{not json}")


def test_oversized_request_is_rejected() -> None:
    with pytest.raises(RequestError, match="exceeds"):
        parse_request(b"{" + b" " * (MAX_REQUEST_BYTES + 1))


def test_oversized_prompt_is_rejected() -> None:
    payload = valid() | {"prompt": "a" * (MAX_PROMPT_BYTES + 1)}
    raw = encode(payload)
    # Kept under the whole-request bound so the prompt bound is what fires.
    assert len(raw) <= MAX_REQUEST_BYTES
    with pytest.raises(RequestError, match="prompt exceeds"):
        parse_request(raw)
