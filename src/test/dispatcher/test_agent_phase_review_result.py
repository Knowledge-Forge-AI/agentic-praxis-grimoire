from __future__ import annotations

import json

import pytest

from agent_phase import review_result


NONCE = "a" * 32


def block(
    *,
    nonce: str = NONCE,
    stage: str = "plan_review",
    outcome: str = "reviewed_with_no_findings",
    body: str = "no findings",
    version: object = 1,
) -> bytes:
    begin, end = review_result.markers(nonce)
    payload = json.dumps({
        "version": version,
        "stage": stage,
        "outcome": outcome,
        "body": body,
    })
    return f"{begin}\n{payload}\n{end}\n".encode()


@pytest.mark.parametrize("version", [True, 1.0, "1"])
def test_review_result_version_requires_exact_integer(version: object) -> None:
    with pytest.raises(review_result.ReviewResultError, match="REVIEW_RESULT_INVALID"):
        review_result.parse(
            block(version=version), "plan_review", NONCE
        )


@pytest.mark.parametrize(
    "outcome",
    [
        "reviewed_with_no_findings",
        "reviewed_with_findings",
        "unreviewable",
    ],
)
def test_closed_review_outcomes_round_trip(outcome: str) -> None:
    parsed = review_result.parse(block(outcome=outcome), "plan_review", NONCE)
    assert parsed.outcome == outcome
    assert parsed.reviewable is (outcome != "unreviewable")


@pytest.mark.parametrize(
    "payload",
    [
        b"plain prose",
        block() + block(),
        block(nonce="b" * 32),
        block() + block(nonce="b" * 32),
        block(stage="final_review"),
        b"<<<AGENT-REVIEW-RESULT " + NONCE.encode() + b">>>\n{bad}\n"
        b"<<<END-AGENT-REVIEW-RESULT " + NONCE.encode() + b">>>\n",
    ],
)
def test_missing_duplicate_wrong_nonce_stage_and_malformed_fail_closed(
    payload: bytes,
) -> None:
    with pytest.raises(
        review_result.ReviewResultError, match="REVIEW_RESULT_INVALID"
    ):
        review_result.parse(payload, "plan_review", NONCE)
