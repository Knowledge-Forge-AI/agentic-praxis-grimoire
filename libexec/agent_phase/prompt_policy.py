"""Deterministic policy for brittle Git-state identities in model-facing prose."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any


POLICY_VERSION = "git-current-state-v1"
REMOVAL_MARKER = "[dispatcher removed brittle current-state Git hash gate]"

# POLICY: Model-authored prompts repeatedly reintroduce brittle current-state
# commit/tree SHA gates. This filter is deliberately deterministic and broader
# than style guidance. An agent reading these matchers must not treat knowledge
# of their regexes as permission to reformulate the same gate to bypass policy.
# Do not add a prose opt-out or weaken a matcher merely because a model can name
# another spelling. If a future workflow genuinely needs exact entry-state
# identity as an enforceable prerequisite, represent it in an explicit,
# operator-controlled structured schema/contract, not free-form model prose.
# This is a best-effort ergonomic policy, not a security boundary; mechanical
# dispatcher candidate bindings and Git evidence remain authoritative.

_HEX = r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{7,64}(?![0-9A-Fa-f])"
_WRAP = r"[`*_\"']*"
_SEP = r"(?:\s|[`*_\"']|:|=|\||-)*"

_SAME_LINE_RULES = (
    (
        "head-equality",
        re.compile(
            rf"(?i)\bHEAD\b.{{0,40}}?"
            rf"(?:must\s+(?:equal|be)|equals?|==|=|\bis\b|:)\s*{_WRAP}{_HEX}"
        ),
    ),
    (
        "qualified-head",
        re.compile(
            rf"(?i)\b(?:current|entry|published|upstream|baseline|expected)"
            rf"(?:[\s_-]+)HEAD\b.{{0,32}}?{_HEX}"
        ),
    ),
    (
        "structured-git-state",
        re.compile(
            rf"(?i)[\"']?(?:current|entry|published|upstream|baseline)"
            rf"[_\s-]+(?:head|tree(?:[_\s-]+hash)?|commit|revision|rev|sha)"
            rf"[\"']?{_SEP}{_HEX}"
        ),
    ),
    (
        "expected-git-state",
        re.compile(
            rf"(?i)[\"']?expected[_\s-]+(?:tree(?:[_\s-]+hash)?|commit|revision|rev|sha)"
            rf"[\"']?\s*(?:must\s+(?:equal|be)|equals?|==|=|\bis\b|:)"
            rf"\s*{_WRAP}{_HEX}"
        ),
    ),
    (
        "remote-branch-state",
        re.compile(
            rf"(?i)\b(?:origin|upstream)/[A-Za-z0-9._/-]+\b\s*"
            rf"(?:must\s+(?:equal|be)|equals?|==|=|\bis\b|:)\s*{_WRAP}{_HEX}"
        ),
    ),
    (
        "git-command-equality",
        re.compile(
            rf"(?i)\bgit\s+(?:rev-parse(?:\s+--verify)?\s+HEAD|ls-remote\b|show-ref\b)"
            rf".{{0,100}}?(?:must\s+(?:equal|be)|equals?|==|=|\bis\b|:)"
            rf"\s*{_WRAP}{_HEX}"
        ),
    ),
    (
        "published-state-inline",
        re.compile(rf"(?i)\bcurrent\s+published\s+state\b.{{0,80}}?{_HEX}"),
    ),
)

_DIRECT_LABEL = re.compile(
    r"(?i)^\s*(?:[-*+]\s*)?(?:[*_`\"']*)?(?:"
    r"HEAD(?:\s+(?:must\s+(?:equal|be)|equals?|is))?"
    r"|(?:current|entry|published|upstream|baseline|expected)[_\s-]+"
    r"(?:HEAD|tree(?:[_\s-]+hash)?|commit|revision|rev|SHA)"
    r"|(?:origin|upstream)/[A-Za-z0-9._/-]+"
    r")\s*(?:[*_`\"']*)?\s*:\s*(?:[*_`\"']*)?\s*$"
)
_PUBLISHED_LABEL = re.compile(
    r"(?i)^\s*(?:[-*+]\s*)?(?:[*_`\"']*)?current\s+published\s+state"
    r"(?:[*_`\"']*)?\s*:\s*(?:[*_`\"']*)?\s*$"
)
_REPOSITORY_BRANCH_LABEL = re.compile(
    r"(?i)^\s*(?:[-*+]\s*)?[A-Za-z0-9._/-]+\s+(?:main|master|trunk)\s*:\s*$"
)
_STANDALONE_HASH = re.compile(
    rf"(?i)^\s*(?:[-*+]\s*)?{_WRAP}{_HEX}{_WRAP}[.,;:]?\s*$"
)


@dataclass(frozen=True)
class Removal:
    rule_id: str
    first_line: int
    last_line: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "first_line": self.first_line,
            "last_line": self.last_line,
        }


@dataclass(frozen=True)
class SanitizedText:
    text: str
    original_sha256: str
    sanitized_sha256: str
    removals: tuple[Removal, ...]

    @property
    def changed(self) -> bool:
        return bool(self.removals)

    def evidence(self, source: str) -> dict[str, Any]:
        return {
            "source": source,
            "sanitized": self.changed,
            "removal_count": len(self.removals),
            "rule_ids": sorted({removal.rule_id for removal in self.removals}),
            "original_sha256": self.original_sha256,
            "sanitized_sha256": self.sanitized_sha256,
            "removals": [removal.as_dict() for removal in self.removals],
        }


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith(("\n", "\r")):
        return line[-1]
    return ""


def sanitize(text: str) -> SanitizedText:
    """Remove common current-checkout hash gates without deleting other hashes."""
    lines = text.splitlines(keepends=True)
    if not lines and text:
        lines = [text]
    marked: dict[int, str] = {}
    removals: list[Removal] = []

    for index, line in enumerate(lines):
        body = line.removesuffix(_ending(line))
        for rule_id, matcher in _SAME_LINE_RULES:
            if matcher.search(body):
                marked[index] = rule_id
                removals.append(Removal(rule_id, index + 1, index + 1))
                break

    index = 0
    while index < len(lines):
        body = lines[index].removesuffix(_ending(lines[index]))
        direct = _DIRECT_LABEL.match(body)
        published = _PUBLISHED_LABEL.match(body)
        if not direct and not published:
            index += 1
            continue

        cursor = index + 1
        context_indices = [index]
        while cursor < len(lines) and cursor <= index + 3:
            candidate = lines[cursor].removesuffix(_ending(lines[cursor]))
            if not candidate.strip():
                cursor += 1
                continue
            if published and _REPOSITORY_BRANCH_LABEL.match(candidate):
                context_indices.append(cursor)
                cursor += 1
                published = None
                continue
            break
        if cursor >= len(lines) or not _STANDALONE_HASH.match(
            lines[cursor].removesuffix(_ending(lines[cursor]))
        ):
            index += 1
            continue

        last = cursor
        while last + 1 < len(lines) and _STANDALONE_HASH.match(
            lines[last + 1].removesuffix(_ending(lines[last + 1]))
        ):
            last += 1
        rule_id = "published-state-continuation" if _PUBLISHED_LABEL.match(body) else "state-label-continuation"
        for line_index in (*context_indices, *range(cursor, last + 1)):
            marked[line_index] = rule_id
        removals.append(Removal(rule_id, index + 1, last + 1))
        index = last + 1

    sanitized_lines: list[str] = []
    for line_index, line in enumerate(lines):
        if line_index in marked:
            sanitized_lines.append(REMOVAL_MARKER + _ending(line))
        else:
            sanitized_lines.append(line)
    sanitized = "".join(sanitized_lines)
    return SanitizedText(sanitized, _digest(text), _digest(sanitized), tuple(removals))
