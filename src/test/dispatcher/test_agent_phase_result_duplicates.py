from __future__ import annotations

import json

import pytest

from agent_phase import result as result_module


NONCE = "a" * 32


def payload(*, body: str = "done") -> bytes:
    return json.dumps(
        {
            "version": 1,
            "stage": "closeout",
            "outcome": "completed",
            "body": body,
            "commit_message": None,
        },
        separators=(",", ":"),
    ).encode()


def fenced(contents: bytes) -> bytes:
    begin, end = result_module.markers(NONCE)
    return begin.encode() + contents + end.encode()


def assert_duplicate_failure(data: bytes) -> None:
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(data, "closeout", NONCE)
    assert caught.value.code == "RESULT_DUPLICATE_FENCE"


def test_exact_duplicate_fences_collapse_to_one_semantic_result() -> None:
    block = fenced(payload())

    parsed = result_module.parse(block + b"\nprovider noise\n" + block, "closeout", NONCE)

    assert parsed.completed
    assert parsed.fence_copies == 2
    assert parsed.as_dict()["fence_copies"] == 2


@pytest.mark.parametrize(
    "second",
    [
        payload(body="different"),
        payload() + b"\n",
        b" " + payload(),
    ],
    ids=["different-json", "trailing-newline", "leading-space"],
)
def test_nonidentical_duplicate_payload_bytes_fail_closed(second: bytes) -> None:
    assert_duplicate_failure(fenced(payload()) + fenced(second))


def test_nested_duplicate_fences_fail_closed() -> None:
    begin, end = (marker.encode() for marker in result_module.markers(NONCE))
    data = begin + begin + payload() + end + end

    assert_duplicate_failure(data)


def test_overlapping_duplicate_fences_fail_closed() -> None:
    begin, end = (marker.encode() for marker in result_module.markers(NONCE))
    data = begin + b"first" + begin + b"second" + end + end

    assert_duplicate_failure(data)


@pytest.mark.parametrize(
    "data",
    [
        lambda begin, end: begin + payload() + end + begin + payload(),
        lambda begin, end: begin + payload() + end + end,
    ],
    ids=["missing-second-end", "extra-end"],
)
def test_unmatched_duplicate_markers_fail_closed(data) -> None:
    begin, end = (marker.encode() for marker in result_module.markers(NONCE))

    assert_duplicate_failure(data(begin, end))


def test_single_end_before_begin_retains_specific_order_failure() -> None:
    begin, end = (marker.encode() for marker in result_module.markers(NONCE))

    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(end + begin + payload(), "closeout", NONCE)

    assert caught.value.code == "RESULT_FENCE_ORDER"
