"""Bounded clause-polarity guards for Markdown candidate evidence."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from apg_markdown_token_guard_contract import (
    SEMANTIC_SIGNAL_ALIASES,
    exact_token_pattern,
)
from apg_markdown_vocabulary_contract import ACCEPTED_VOCABULARY


POSITIVE = "positive"
NEGATIVE = "negative"
CONFLICTED = "conflicted"
ABSENT = "absent"
HUMAN_REVIEW_REQUIRED = "human-review-required"
AXIS_TOKENS = ACCEPTED_VOCABULARY["selections"] + ACCEPTED_VOCABULARY["responses"]
TARGETED_GUARD_MARKERS = {
    "no-synthetic-commonmark-gfm-composite": ("MARKDOWN-EFFECTIVE-GRAMMAR", "never presented as one formally specified composite dialect"),
    "unknown-parser-route": ("MARKDOWN-UNKNOWN-GRAMMAR", "routes to parser-tool-owner with inspect-before-judgment"),
    "parser-conflict-stop": ("MARKDOWN-PARSER-CONFLICT", "parser-tool-owner decision reached through stop-and-escalate"),
    "selected-gfm-extension-tuple": ("MARKDOWN-EXTENSION-EVIDENCE", "primary owner is markdown-language-profile, selection is selected, response is proceed-routine, and route is not-applicable"),
    "fence-owner-and-embedded-route": ("MARKDOWN-FENCE", "primary owner is markdown-language-profile, selection is embedded-route, response is proceed-routine, and route is embedded-language-owner"),
    "unterminated-fence-bounded-repair": ("MARKDOWN-FENCE", "repair restores the smallest valid closing boundary"),
    "raw-html-ordinary-route": ("MARKDOWN-RAW-HTML", "primary owner is markdown-language-profile, selection is embedded-route, response is proceed-routine, and route is html-owner"),
    "raw-html-policy-evasion-route": ("MARKDOWN-RAW-HTML", "exact permission receiver is project-policy"),
    "repository-forbidden-raw-html-stop": ("MARKDOWN-RAW-HTML", "stop-and-escalate routed to repository-policy"),
    "valid-frontmatter-tuple": ("MARKDOWN-FRONTMATTER", "primary owner markdown-language-profile, selection selected, response proceed-routine, and route not-applicable"),
    "frontmatter-schema-route": ("MARKDOWN-FRONTMATTER", "schema identification to project-policy with inspect-before-judgment"),
    "frontmatter-delimiter-repair": ("MARKDOWN-FRONTMATTER", "only the evidenced boundary form is repaired"),
    "mdx-whole-file-nontrigger": ("MARKDOWN-MDX-HOST", "primary owner mdx-owner, selection non-trigger, response proceed-routine, and route mdx-owner"),
    "host-fragment-embedded-route": ("MARKDOWN-EMBEDDED-ROUTE", ("host retains whole-file ownership", "judgment is limited to the identified fragment", "inspect-before-judgment")),
    "generated-hand-edit-route": ("MARKDOWN-GENERATED", ("generator-owned output is never hand-refactored", "route-to-owner to parser-tool-owner", "bounded-local-decision", "regeneration as the rollback path")),
    "move-map-rollback": ("MARKDOWN-STRUCTURAL-POLICY", "preserve navigation and record the move map"),
    "extraction-map-rollback": ("MARKDOWN-STRUCTURAL-POLICY", "records the extraction map"),
    "normative-contradiction-stop": ("MARKDOWN-SEMANTIC-RISK", ("dependent work stops", "both statements are preserved", "project-policy")),
}

_NEGATIVE_PREFIX_RE = re.compile(
    r"(?:do not claim(?: the)?|it is false that|"
    r"(?:this )?hypothetical(?: claim)? is explicitly denied:|"
    r"the rejected quotation is:|suppose(?: that)?|assuming(?: that)?|"
    r"assume(?: that)?|imagine(?: that)?|hypothetically,?|if|were|"
    r"consider whether|"
    r"must not use|may not consider|must be ignored|"
    r"no evidence from|(?:evidence|source) (?:is )?(?:not owned by|not established by)|"
    r"rejected phrase(?: must not be used)?|prohibited phrase|"
    r"the following rejected phrase must not be used)\s*[:\"']?\s*$"
)
_NEGATIVE_SUFFIX_RE = re.compile(
    r"^\s*[\"']?\s*(?:does not apply|is absent|did not fire|is not present|"
    r"is irrelevant|provides no evidence|is invalid evidence|must be ignored|"
    r"must not be used|may not be considered|is not required|does not require|"
    r"is not owned by|is not established by|is explicitly disclaimed|"
    r"is rejected|; reject that claim)\b"
)
_NEGATIVE_STATEMENT_RE = re.compile(
    r"^\s*(?:do not claim|it is false that|(?:this )?hypothetical(?: claim)? "
    r"is explicitly denied:|suppose(?: that)?|assuming(?: that)?|"
    r"assume(?: that)?|imagine(?: that)?|hypothetically,?|if|were|"
    r"consider whether)\b"
)

_ROLLBACK_NEGATIVE_RE = re.compile(
    r"\b(?:rollback is not required|no rollback is required|"
    r"not every change requires rollback|rollback applies only where material)\b"
)
_ROLLBACK_POSITIVE_PATTERNS = (
    re.compile(
        r"\brollback\b.{0,40}\b(?:is always required|applies unconditionally|"
        r"is mandatory|is required for every change)\b"
    ),
    re.compile(r"\b(?:every|all) changes? require(?:s)? (?:a )?rollback\b"),
    re.compile(
        r"\beach (?:change|decision) must (?:include|have) (?:a )?rollback\b"
    ),
)


def _normalized(text: str) -> str:
    return " ".join(
        text.replace("`", "")
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("„", '"')
        .replace("‟", '"')
        .replace("«", '"')
        .replace("»", '"')
        .replace("‹", "'")
        .replace("›", "'")
        .lower()
        .split()
    )


def _occurrence_is_negative(text: str, start: int, end: int) -> bool:
    prefix = text[max(0, start - 96) : start]
    suffix = text[end : min(len(text), end + 96)]
    statement_prefix = re.split(r"[.!?\n]", prefix)[-1]
    opening_quote = prefix.rstrip()[-1:] if prefix.rstrip()[-1:] in {'"', "'"} else ""
    quoted = bool(
        any(
            prefix.count(quote) % 2 == 1 and quote in suffix
            for quote in ('"', "'")
        )
        or (
            opening_quote
            and re.match(rf"^[\s.,;:!?]*{re.escape(opening_quote)}", suffix)
        )
    )
    return bool(
        quoted
        or _NEGATIVE_PREFIX_RE.search(prefix)
        or _NEGATIVE_STATEMENT_RE.search(statement_prefix)
        or _NEGATIVE_SUFFIX_RE.search(suffix)
    )


def guard_state(
    text: str,
    markers: str | Iterable[str],
    *,
    direct_negations: Iterable[str] = (),
) -> str:
    """Classify exact markers under a bounded directly attached polarity grammar."""

    normalized = _normalized(text)
    variants = (markers,) if isinstance(markers, str) else tuple(markers)
    positive = False
    negative = any(
        re.search(exact_token_pattern(_normalized(phrase)), normalized)
        for phrase in direct_negations
    )
    for marker in variants:
        normalized_marker = _normalized(marker)
        pattern = exact_token_pattern(normalized_marker)
        negative_variant = re.compile(r"(?:the )?" + pattern.pattern, pattern.flags)
        for match in negative_variant.finditer(normalized):
            if _occurrence_is_negative(normalized, match.start(), match.end()):
                negative = True
        for match in pattern.finditer(normalized):
            if _occurrence_is_negative(normalized, match.start(), match.end()):
                negative = True
            else:
                positive = True
    if positive and negative:
        return CONFLICTED
    if positive:
        return POSITIVE
    if negative:
        return NEGATIVE
    return ABSENT


def guard_states(
    text: str, marker_aliases: Mapping[str, Iterable[str]]
) -> dict[str, str]:
    """Return one bounded state for each named token and its accepted aliases."""

    return {
        marker: guard_state(text, (marker, *tuple(aliases)))
        for marker, aliases in marker_aliases.items()
    }


def combined_guard_state(text: str, markers: Iterable[str]) -> str:
    """Require every marker positive and expose any local contradiction."""

    states = tuple(guard_state(text, marker) for marker in markers)
    if any(state == CONFLICTED for state in states):
        return CONFLICTED
    if any(state == NEGATIVE for state in states):
        return CONFLICTED if any(state == POSITIVE for state in states) else NEGATIVE
    if any(state == ABSENT for state in states):
        return ABSENT
    return POSITIVE


def unconditional_rollback_state(text: str) -> str:
    """Classify bounded unconditional rollback obligations in one mapped scope."""

    normalized = _normalized(text)
    negative_matches = tuple(_ROLLBACK_NEGATIVE_RE.finditer(normalized))
    masked = list(normalized)
    for match in negative_matches:
        masked[match.start() : match.end()] = " " * (match.end() - match.start())
    positive = any(pattern.search("".join(masked)) for pattern in _ROLLBACK_POSITIVE_PATTERNS)
    negative = bool(negative_matches)
    if positive and negative:
        return CONFLICTED
    if positive:
        return POSITIVE
    if negative:
        return NEGATIVE
    return ABSENT


def local_guard_observations(row: Mapping[str, object], mapped_text: str) -> dict[str, object]:
    """Return positive candidate observations and explicit signal states."""

    structural = tuple(row["structural_signals"])
    semantic = tuple(row["semantic_signals"])
    owner_states = {
        f"owner:{owner}": guard_state(mapped_text, owner)
        for owner in ACCEPTED_VOCABULARY["owners"]
    }
    axis_states = {
        f"axis:{axis}": guard_state(mapped_text, axis)
        for axis in AXIS_TOKENS
    }
    states = {
        f"structural:{signal}": guard_state(mapped_text, signal)
        for signal in structural
    }
    states.update(
        {
            f"semantic:{signal}": guard_state(
                mapped_text,
                (signal, *SEMANTIC_SIGNAL_ALIASES.get(signal, ())),
            )
            for signal in semantic
        }
    )
    return {
        "owners": {
            owner for owner in ACCEPTED_VOCABULARY["owners"]
            if owner_states[f"owner:{owner}"] == POSITIVE
        },
        "axes": {
            axis for axis in AXIS_TOKENS if axis_states[f"axis:{axis}"] == POSITIVE
        },
        "structural_signals": {
            signal for signal in structural if states[f"structural:{signal}"] == POSITIVE
        },
        "semantic_signals": {
            signal for signal in semantic if states[f"semantic:{signal}"] == POSITIVE
        },
        "guard_states": owner_states | axis_states | states,
    }


def targeted_guard_states(clauses: Mapping[str, str]) -> dict[str, str]:
    """Return one explicit state for each retained targeted candidate guard."""

    results: dict[str, str] = {}
    for name, (clause_id, requirement) in TARGETED_GUARD_MARKERS.items():
        markers = (requirement,) if isinstance(requirement, str) else requirement
        results[name] = combined_guard_state(clauses.get(clause_id, ""), markers)
    return results
