from __future__ import annotations

import json
from pathlib import Path
import pytest

from agent_phase.request import (
    MAX_PROMPT_BYTES,
    PHASE_TYPES,
    PhaseRequest,
    PhaseRequestV2,
    RequestError,
    SCHEMA_V1,
    SCHEMA_V2,
    load_any_request,
    load_request_v2,
    parse_any_request,
    parse_request_v2,
)


def encode(payload: dict[str, object]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def valid_v2() -> dict[str, object]:
    return {
        "schema": SCHEMA_V2,
        "phase_type": "implementation_testing",
        "prompt": "do the bounded work only",
    }


def test_valid_v2_request_round_trips() -> None:
    payload = valid_v2()
    req = parse_request_v2(encode(payload))
    assert isinstance(req, PhaseRequestV2)
    assert req.schema == SCHEMA_V2
    assert req.phase_type == "implementation_testing"
    assert req.prompt == "do the bounded work only"
    assert req.as_dict() == payload


@pytest.mark.parametrize("phase_type", PHASE_TYPES)
def test_every_allowed_phase_type_parses_v2(phase_type: str) -> None:
    payload = valid_v2() | {"phase_type": phase_type}
    req = parse_request_v2(encode(payload))
    assert req.phase_type == phase_type


def test_reject_execution_mode_in_v2() -> None:
    payload = valid_v2() | {"execution_mode": "normal"}
    with pytest.raises(RequestError) as exc_info:
        parse_request_v2(encode(payload))
    msg = str(exc_info.value)
    assert "request keys must be exactly ['phase_type', 'prompt', 'schema']" in msg
    assert "unsupported request key for agent-phase-request-v2: execution_mode" in msg


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "constraints",
        "lifecycle",
        "finalization",
        "sandbox",
        "runtime_policy",
        "reviewer_selection",
        "model",
        "provider",
    ],
)
def test_reject_forbidden_policy_fields_in_v2(forbidden_key: str) -> None:
    payload = valid_v2() | {forbidden_key: "forbidden_value"}
    with pytest.raises(RequestError) as exc_info:
        parse_request_v2(encode(payload))
    msg = str(exc_info.value)
    assert "request keys must be exactly" in msg
    assert f"unsupported request key for agent-phase-request-v2: {forbidden_key}" in msg


def test_reject_missing_keys_in_v2() -> None:
    for missing_key in ("schema", "phase_type", "prompt"):
        payload = valid_v2()
        del payload[missing_key]
        with pytest.raises(RequestError) as exc_info:
            parse_request_v2(encode(payload))
        assert "request keys must be exactly" in str(exc_info.value)


def test_reject_unsupported_schema_in_v2() -> None:
    payload = valid_v2() | {"schema": "agent-phase-request-v3"}
    with pytest.raises(RequestError, match="request schema must be agent-phase-request-v2"):
        parse_request_v2(encode(payload))


def test_reject_unsupported_phase_type_in_v2() -> None:
    payload = valid_v2() | {"phase_type": "arbitrary_phase"}
    with pytest.raises(RequestError, match="unsupported phase_type"):
        parse_request_v2(encode(payload))


def test_reject_empty_or_whitespace_prompt_in_v2() -> None:
    for empty in ("", "   ", "\n\t"):
        payload = valid_v2() | {"prompt": empty}
        with pytest.raises(RequestError, match="prompt must be non-empty"):
            parse_request_v2(encode(payload))


def test_reject_non_string_prompt_in_v2() -> None:
    payload = valid_v2() | {"prompt": 12345}
    with pytest.raises(RequestError, match="request field must be a string: prompt"):
        parse_request_v2(encode(payload))


def test_reject_oversized_payload_in_v2() -> None:
    huge_prompt = "a" * (MAX_PROMPT_BYTES + 1)
    payload = valid_v2() | {"prompt": huge_prompt}
    raw = encode(payload)
    with pytest.raises(RequestError):
        parse_request_v2(raw)


def test_reject_invalid_json_in_v2() -> None:
    with pytest.raises(RequestError, match="request is not valid JSON"):
        parse_request_v2(b"not json")


def test_reject_non_dict_json_in_v2() -> None:
    with pytest.raises(RequestError, match="request must be a top-level JSON object"):
        parse_request_v2(b"[1, 2, 3]")


def test_load_request_v2(tmp_path: Path) -> None:
    req_file = tmp_path / "req_v2.json"
    req_file.write_text(json.dumps(valid_v2()))
    loaded = load_request_v2(req_file)
    assert isinstance(loaded, PhaseRequestV2)
    assert loaded.prompt == "do the bounded work only"

    with pytest.raises(RequestError, match="cannot read"):
        load_request_v2(tmp_path / "nonexistent.json")


def test_parse_any_request_dispatches_correctly() -> None:
    v1_raw = encode({
        "schema": SCHEMA_V1,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "prompt": "v1 prompt",
    })
    v2_raw = encode(valid_v2())

    req1 = parse_any_request(v1_raw)
    assert isinstance(req1, PhaseRequest)
    assert req1.execution_mode == "normal"

    req2 = parse_any_request(v2_raw)
    assert isinstance(req2, PhaseRequestV2)
    assert req2.prompt == "do the bounded work only"


def test_load_any_request(tmp_path: Path) -> None:
    v1_file = tmp_path / "v1.json"
    v1_file.write_text(json.dumps({
        "schema": SCHEMA_V1,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "prompt": "v1 prompt",
    }))
    v2_file = tmp_path / "v2.json"
    v2_file.write_text(json.dumps(valid_v2()))

    assert isinstance(load_any_request(v1_file), PhaseRequest)
    assert isinstance(load_any_request(v2_file), PhaseRequestV2)
