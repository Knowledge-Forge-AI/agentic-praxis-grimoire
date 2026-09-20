"""Strict provider stage-result parsing.

A provider process exiting 0 means the CLI returned normally. It does not mean
the phase completed: the first dogfood run exited 0 while its closeout reported
a blocked commit, and the dispatcher recorded that run as complete. This module
is how the dispatcher learns the difference, without ever reading model prose.

Extraction is nonce-fenced rather than whole-stdout. Provider CLIs put framing on
their own streams (codex 0.147.0 emits its banner, hook lines, and MCP transport
errors on stderr), and a contract that requires stdout to be nothing but JSON
depends on an output guarantee no provider actually publishes. The dispatcher
generates the nonce, so only bytes it delimited are parsed. Inside the fence the
payload is exact: one JSONC-compatible object, no trailing prose.

The fence is an extraction boundary, not a trust boundary. A `completed` outcome
is necessary but never sufficient; the dispatcher still proves what happened from
git objects.
"""

from __future__ import annotations

import json
import re
import secrets
from typing import Any, NamedTuple

from .jsonc import JSONCLexError, raw_decode, strip_json_whitespace, unicode_scalars


RESULT_VERSION = 1
MAX_RESULT_BYTES = 256 * 1024

OUTCOME_COMPLETED = "completed"
OUTCOME_BLOCKED = "blocked"
OUTCOME_FAILED = "failed"
OUTCOMES = (OUTCOME_COMPLETED, OUTCOME_BLOCKED, OUTCOME_FAILED)

RESULT_FIELDS = frozenset({"version", "stage", "outcome", "body", "commit_message"})
COMMIT_FIELDS = frozenset({"subject", "body"})

# common/usr/docs/general/specs/git/commit-standards-draft.md: imperative subject
# at 72 characters, blank line, body wrapped at 80. The body bound enforced here
# is 100 rather than 80: the draft states a wrapping habit, and hard-failing at
# 80 would reject legitimate long URLs and command lines in a Verification block.
MAX_SUBJECT_BYTES = 72
MAX_BODY_LINE_BYTES = 100

_BEGIN = "<<<AGENT-PHASE-RESULT {nonce}>>>"
_END = "<<<END-AGENT-PHASE-RESULT {nonce}>>>"

# Control characters are rejected in commit text: the message reaches git on
# stdin, and an embedded NUL or escape sequence is never a legitimate subject.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


class ResultError(ValueError):
    """A stage result could not be trusted. `code` is the recorded blocker."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class CommitMessage(NamedTuple):
    subject: str
    body: str

    def render(self) -> str:
        if not self.body:
            return self.subject + "\n"
        return f"{self.subject}\n\n{self.body.rstrip()}\n"


class StageResult(NamedTuple):
    version: int
    stage: str
    outcome: str
    body: str
    commit_message: CommitMessage | None
    fence_copies: int = 1
    path_dispositions: tuple[dict[str, str], ...] = ()
    ownership_resolutions: tuple[dict[str, str], ...] = ()

    @property
    def completed(self) -> bool:
        return self.outcome == OUTCOME_COMPLETED

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "stage": self.stage,
            "outcome": self.outcome,
            "body": self.body,
            "commit_message": (
                None if self.commit_message is None
                else {"subject": self.commit_message.subject,
                      "body": self.commit_message.body}
            ),
            "fence_copies": self.fence_copies,
            **({"path_dispositions": list(self.path_dispositions)} if self.path_dispositions else {}),
            **({"ownership_resolutions": list(self.ownership_resolutions)} if self.ownership_resolutions else {}),
        }


def new_nonce() -> str:
    return secrets.token_hex(16)


def markers(nonce: str) -> tuple[str, str]:
    return _BEGIN.format(nonce=nonce), _END.format(nonce=nonce)


def _extract_payload(data: bytes, nonce: str) -> tuple[str, int]:
    """Return the exact fenced payload, or fail closed.

    Operates on bytes because transport noise outside the fence may not be valid
    UTF-8; only the payload is decoded, and it is decoded strictly.
    """
    begin, end = markers(nonce)
    begin_bytes = begin.encode("utf-8")
    end_bytes = end.encode("utf-8")
    starts = _occurrences(data, begin_bytes)
    ends = _occurrences(data, end_bytes)
    if not starts or not ends:
        raise ResultError(
            "RESULT_MISSING_FENCE",
            "stage output does not carry the dispatcher's result markers",
        )
    if len(starts) != len(ends):
        raise ResultError(
            "RESULT_DUPLICATE_FENCE",
            f"ambiguous fenced result: found {len(starts)} begin and "
            f"{len(ends)} end markers",
        )
    payloads: list[bytes] = []
    previous_end = -1
    for begin_at, end_at in zip(starts, ends, strict=True):
        start = begin_at + len(begin_bytes)
        if begin_at < previous_end or end_at < start:
            code = "RESULT_FENCE_ORDER" if len(starts) == 1 else "RESULT_DUPLICATE_FENCE"
            raise ResultError(code, "result fences overlap, nest, or are out of order")
        payloads.append(data[start:end_at])
        previous_end = end_at + len(end_bytes)
    payload = payloads[0]
    if any(candidate != payload for candidate in payloads[1:]):
        raise ResultError(
            "RESULT_DUPLICATE_FENCE",
            "duplicate fenced result payloads are not byte-identical",
        )
    if len(payload) > MAX_RESULT_BYTES:
        raise ResultError(
            "RESULT_TOO_LARGE",
            f"fenced result exceeds {MAX_RESULT_BYTES} bytes: {len(payload)}",
        )
    try:
        return payload.decode("utf-8"), len(payloads)
    except UnicodeDecodeError as error:
        raise ResultError("RESULT_NOT_UTF8", f"fenced result is not UTF-8: {error}")


def extract(data: bytes, nonce: str) -> str:
    """Return the validated payload text, collapsing exact duplicate copies."""
    return _extract_payload(data, nonce)[0]


def _occurrences(data: bytes, needle: bytes) -> list[int]:
    found: list[int] = []
    index = data.find(needle)
    while index != -1:
        found.append(index)
        index = data.find(needle, index + 1)
    return found


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            if key in {"ownership_resolutions", "challenge_id", "decision"}:
                code = "OWNERSHIP_PROVIDER_RESOLUTION_INVALID"
            elif key in {"path_dispositions", "path", "disposition"}:
                code = "PATH_DISPOSITION_INVALID"
            else:
                code = "RESULT_DUPLICATE_KEY"
            raise ResultError(code, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse(data: bytes, stage: str, nonce: str) -> StageResult:
    """Parse a fenced stage result, binding it to the dispatched stage."""
    text, fence_copies = _extract_payload(data, nonce)
    try:
        value, trailing = raw_decode(text, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, JSONCLexError) as error:
        raise ResultError(
            "RESULT_NOT_JSON", f"fenced result is not JSONC-compatible: {error}"
        ) from error
    # Anything after the object is rejected: a second concatenated object and a
    # trailing sentence are the same failure, and neither may be interpreted.
    if strip_json_whitespace(trailing):
        raise ResultError(
            "RESULT_TRAILING_CONTENT",
            "fenced result carries content after the JSON object",
        )
    return _parse_value(value, stage, fence_copies)


def _parse_value(value: Any, stage: str, fence_copies: int) -> StageResult:
    if not isinstance(value, dict):
        return StageResult(
            version=RESULT_VERSION,
            stage=stage,
            outcome=OUTCOME_BLOCKED,
            body="",
            commit_message=None,
            fence_copies=fence_copies,
            path_dispositions=(),
            ownership_resolutions=(),
        )

    if "version" in value and value["version"] is not None:
        if type(value["version"]) is not int or value["version"] != RESULT_VERSION:
            raise ResultError(
                "RESULT_VERSION", f"result version must be {RESULT_VERSION}"
            )

    if "stage" in value and value["stage"] is not None and value["stage"] != stage:
        raise ResultError(
            "RESULT_STAGE_MISMATCH",
            f"result declares stage {value['stage']!r}, dispatched {stage!r}",
        )

    raw_outcome = value.get("outcome")
    if raw_outcome in OUTCOMES:
        outcome = raw_outcome
    elif raw_outcome is None:
        outcome = OUTCOME_BLOCKED
    else:
        raise ResultError(
            "RESULT_OUTCOME",
            f"outcome must be one of {list(OUTCOMES)}, got {raw_outcome!r}",
        )

    raw_body = value.get("body", "")
    if raw_body is None:
        raw_body = ""
    elif not isinstance(raw_body, str):
        raise ResultError("RESULT_BODY", "result body must be a string")
    try:
        result_body = unicode_scalars(raw_body)
    except JSONCLexError as error:
        raise ResultError("RESULT_BODY", "result body contains an unpaired surrogate") from error

    commit_message = _parse_commit_message(value.get("commit_message"))

    from .path_disposition import validate_dispositions
    dispositions = validate_dispositions(value.get("path_dispositions", []))

    from .lifecycle import LIFECYCLES
    if ("ownership_resolutions" in value
            and stage not in {spec.terminal_result_stage for spec in LIFECYCLES.values()}):
        raise ResultError("OWNERSHIP_PROVIDER_RESOLUTION_INVALID",
                          "only terminal stages may supply ownership resolutions")
    from .ownership_challenge import validate_resolutions
    resolutions = validate_resolutions(value.get("ownership_resolutions", []))

    return StageResult(
        version=RESULT_VERSION,
        stage=stage,
        outcome=outcome,
        body=result_body,
        commit_message=commit_message,
        fence_copies=fence_copies,
        path_dispositions=tuple(dispositions),
        ownership_resolutions=tuple(resolutions),
    )


def _parse_commit_message(value: Any) -> CommitMessage | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ResultError(
            "COMMIT_MESSAGE_SHAPE", "commit_message must be null or an object"
        )
    if set(value) != COMMIT_FIELDS:
        raise ResultError(
            "COMMIT_MESSAGE_SHAPE",
            f"commit_message keys must be exactly {sorted(COMMIT_FIELDS)}",
        )
    subject = value["subject"]
    body = value["body"]
    if not isinstance(subject, str) or not isinstance(body, str):
        raise ResultError(
            "COMMIT_MESSAGE_SHAPE", "commit_message fields must be strings"
        )
    try:
        subject = unicode_scalars(subject)
        body = unicode_scalars(body)
    except JSONCLexError as error:
        raise ResultError(
            "COMMIT_MESSAGE_SHAPE", "commit message contains an unpaired surrogate"
        ) from error
    return validate_commit_message(subject, body)


def validate_commit_message(subject: str, body: str) -> CommitMessage:
    if _CONTROL.search(subject) or _CONTROL.search(body):
        raise ResultError(
            "COMMIT_CONTROL_CHARACTER",
            "commit message contains a control character",
        )
    if "\n" in subject or "\r" in subject:
        raise ResultError("COMMIT_SUBJECT_MULTILINE", "commit subject must be one line")
    if not subject.strip():
        raise ResultError("COMMIT_SUBJECT_EMPTY", "commit subject must be non-empty")
    if subject != subject.strip():
        raise ResultError(
            "COMMIT_SUBJECT_WHITESPACE",
            "commit subject has leading or trailing whitespace",
        )
    encoded = len(subject.encode("utf-8"))
    if encoded > MAX_SUBJECT_BYTES:
        raise ResultError(
            "COMMIT_SUBJECT_TOO_LONG",
            f"commit subject exceeds {MAX_SUBJECT_BYTES} bytes: {encoded}",
        )
    if subject.endswith("."):
        raise ResultError(
            "COMMIT_SUBJECT_TRAILING_PERIOD",
            "commit subject must not end with a period",
        )
    for line in body.splitlines():
        length = len(line.encode("utf-8"))
        if length > MAX_BODY_LINE_BYTES:
            raise ResultError(
                "COMMIT_BODY_LINE_TOO_LONG",
                f"commit body line exceeds {MAX_BODY_LINE_BYTES} bytes: {length}",
            )
    return CommitMessage(subject=subject, body=body.strip("\n"))
