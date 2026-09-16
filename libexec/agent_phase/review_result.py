"""Nonce-bound structured outcomes for independent review stages."""

from __future__ import annotations

import json
import re
import secrets
from typing import Any, NamedTuple

from .jsonc import JSONCLexError, raw_decode, strip_json_whitespace, unicode_scalars


RESULT_VERSION = 1
MAX_RESULT_BYTES = 4 * 1024 * 1024
OUTCOME_NO_FINDINGS = "reviewed_with_no_findings"
OUTCOME_FINDINGS = "reviewed_with_findings"
OUTCOME_UNREVIEWABLE = "unreviewable"
OUTCOMES = (OUTCOME_NO_FINDINGS, OUTCOME_FINDINGS, OUTCOME_UNREVIEWABLE)
RESULT_FIELDS = frozenset({"version", "stage", "outcome", "body"})
_BEGIN = "<<<AGENT-REVIEW-RESULT {nonce}>>>"
_END = "<<<END-AGENT-REVIEW-RESULT {nonce}>>>"
_ANY_BEGIN = re.compile(rb"<<<AGENT-REVIEW-RESULT ([^>\r\n]*)>>>")
_ANY_END = re.compile(rb"<<<END-AGENT-REVIEW-RESULT ([^>\r\n]*)>>>")


class ReviewResultError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class ReviewResult(NamedTuple):
    version: int
    stage: str
    outcome: str
    body: str
    nonce: str

    @property
    def reviewable(self) -> bool:
        return self.outcome != OUTCOME_UNREVIEWABLE

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "stage": self.stage,
            "outcome": self.outcome,
            "body": self.body,
            "nonce": self.nonce,
        }


def new_nonce() -> str:
    return secrets.token_hex(16)


def markers(nonce: str) -> tuple[str, str]:
    return _BEGIN.format(nonce=nonce), _END.format(nonce=nonce)


def contract(stage: str, nonce: str) -> str:
    begin, end = markers(nonce)
    return f"""\
## Required independent-review result

End your output with exactly one fenced review result:

{begin}
{{
  "version": 1,
  "stage": "{stage}",
  "outcome": "reviewed_with_no_findings",
  "body": "review findings or the reason the subject is unreviewable"
}}
{end}

- `outcome` is exactly one of `reviewed_with_no_findings`,
  `reviewed_with_findings`, or `unreviewable`.
- Findings are advisory and belong in `body`; substantive disagreement is not
  a veto. Use `unreviewable` only when the bound subject cannot structurally be
  reviewed.
- Emit the nonce-bound markers exactly once. Missing, duplicate, malformed,
  wrong-stage, or wrong-nonce results do not complete a review checkpoint.
- The fenced object may use strict JSON plus line comments, block comments, and
  trailing commas. This JSONC-compatible subset is not full JSON5; emit no prose
  or second object inside the markers.
"""


def _duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReviewResultError("REVIEW_RESULT_INVALID", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse(data: bytes, stage: str, nonce: str) -> ReviewResult:
    begin, end = (value.encode("utf-8") for value in markers(nonce))
    begin_matches = list(_ANY_BEGIN.finditer(data))
    end_matches = list(_ANY_END.finditer(data))
    if (
        len(begin_matches) != 1
        or len(end_matches) != 1
        or begin_matches[0].group(1) != nonce.encode("ascii")
        or end_matches[0].group(1) != nonce.encode("ascii")
    ):
        raise ReviewResultError(
            "REVIEW_RESULT_INVALID",
            "review result requires exactly one matching nonce-bound marker pair",
        )
    starts = [begin_matches[0].start()]
    ends = [end_matches[0].start()]
    payload_start = starts[0] + len(begin)
    if ends[0] < payload_start:
        raise ReviewResultError("REVIEW_RESULT_INVALID", "review result fences are out of order")
    payload = data[payload_start:ends[0]]
    if len(payload) > MAX_RESULT_BYTES:
        raise ReviewResultError("REVIEW_RESULT_INVALID", "review result exceeds bound")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ReviewResultError("REVIEW_RESULT_INVALID", f"review result is not UTF-8: {error}")
    try:
        value, trailing = raw_decode(text, object_pairs_hook=_duplicate_keys)
    except (json.JSONDecodeError, JSONCLexError) as error:
        raise ReviewResultError(
            "REVIEW_RESULT_INVALID", f"review result is not JSONC-compatible: {error}"
        ) from error
    if strip_json_whitespace(trailing):
        raise ReviewResultError("REVIEW_RESULT_INVALID", "review result carries content after the JSON payload")
    if not isinstance(value, dict):
        return ReviewResult(
            RESULT_VERSION,
            stage,
            OUTCOME_UNREVIEWABLE,
            "syntactically valid JSON did not provide recognizable review semantics",
            nonce,
        )
    if "version" in value and value["version"] is not None:
        if type(value["version"]) is not int or value["version"] != RESULT_VERSION:
            raise ReviewResultError("REVIEW_RESULT_INVALID", "review result identity mismatch")
    if "stage" in value and value["stage"] is not None and value["stage"] != stage:
        raise ReviewResultError("REVIEW_RESULT_INVALID", "review result identity mismatch")
    raw_outcome = value.get("outcome")
    if raw_outcome in OUTCOMES:
        outcome = raw_outcome
        raw_body = value.get("body", "")
        if raw_body is None:
            raw_body = ""
        elif not isinstance(raw_body, str):
            raise ReviewResultError("REVIEW_RESULT_INVALID", "review result outcome or body is invalid")
        try:
            body = unicode_scalars(raw_body)
        except JSONCLexError as error:
            raise ReviewResultError(
                "REVIEW_RESULT_INVALID", "review result body contains an unpaired surrogate"
            ) from error
        if outcome in {OUTCOME_FINDINGS, OUTCOME_UNREVIEWABLE} and not body.strip():
            if outcome == OUTCOME_UNREVIEWABLE:
                body = "syntactically valid JSON did not provide recognizable review semantics"
            else:
                raise ReviewResultError("REVIEW_RESULT_INVALID", "review result body is required")
        return ReviewResult(
            RESULT_VERSION, stage, outcome, body, nonce
        )
    return ReviewResult(
        RESULT_VERSION,
        stage,
        OUTCOME_UNREVIEWABLE,
        "syntactically valid JSON did not provide recognizable review semantics",
        nonce,
    )
