"""Exact vocabulary, lexical-token, and bounded polarity guards for Markdown."""

from __future__ import annotations

import re
from typing import Iterable

from apg_markdown_vocabulary_contract import ACCEPTED_VOCABULARY

HUMAN_ROLLBACK_ROWS = frozenset({"APG63-MD-032", "APG63-MD-034"})
TOKEN_EDGE = r"[A-Za-z0-9_-]"
SEMANTIC_SIGNAL_ALIASES = {
    "extension-unsupported": ("unsupported construct", "another extension"),
    "dialect-mismatch": ("dialect mismatch", "conflicts with a bounded reference"),
    "link-destination-invalid": ("destination actually resolves",),
    "reference-definition-collision": ("reference labels resolve differently",),
    "accidental-reclassification": ("reclassifies following prose as code",),
    "raw-html-boundary": ("raw-html",),
    "frontmatter-body-corruption": ("reclassify frontmatter as body text",),
    "generated-source-drift": ("diverges from generator intent",),
    "normative-contradiction": ("normative statements", "governing statements"),
    "false-completion": ("false validation", "claim completion"),
}


def exact_token_pattern(token: str) -> re.Pattern[str]:
    """Match a closed token outside larger ASCII identifier-like strings."""

    return re.compile(rf"(?<!{TOKEN_EDGE}){re.escape(token)}(?!{TOKEN_EDGE})")


def exact_tokens(text: str, tokens: Iterable[str]) -> set[str]:
    return {token for token in tokens if exact_token_pattern(token).search(text)}


def contains_exact_phrase(text: str, phrase: str) -> bool:
    words = re.escape(phrase).replace(r"\ ", r"\s+")
    return re.search(rf"(?<!{TOKEN_EDGE}){words}(?!{TOKEN_EDGE})", text) is not None


def observed_semantic_signals(text: str) -> set[str]:
    observed = exact_tokens(text, ACCEPTED_VOCABULARY["semantic_signals"])
    for token, phrases in SEMANTIC_SIGNAL_ALIASES.items():
        if any(contains_exact_phrase(text, phrase) for phrase in phrases):
            observed.add(token)
    return observed


def observed_rollback_classes(text: str) -> set[str]:
    observed = exact_tokens(text, ACCEPTED_VOCABULARY["rollback_classes"])
    observed -= {
        "none",
        "preserve-prechange-statements",
        "preserve-contradiction-pending-resolution",
    }
    aliases = {
        "record-predecision-behavior": ("pre-decision behavior is recorded",),
        "record-collision-definitions": (
            "records both definitions",
            "both colliding reference definitions",
        ),
        "record-reclassified-region": (
            "pre-repair region is recorded",
            "pre-repair region of a reclassified document",
        ),
        "record-moved-responsibility": (
            "responsibility moved into an evasive embedding",
        ),
        "record-frontmatter-bytes": (
            "pre-repair bytes are recorded",
            "pre-repair frontmatter bytes",
        ),
        "regenerate-from-owner": ("regeneration as the rollback path",),
        "preserve-navigation-move-map": ("preserve navigation", "move map"),
        "record-extraction-map": ("extraction map",),
    }
    for token, phrases in aliases.items():
        if all(contains_exact_phrase(text, phrase) for phrase in phrases):
            observed.add(token)
    return observed


def pending_resolution_is_contradicted(text: str) -> bool:
    return any(
        contains_exact_phrase(text, phrase)
        for phrase in (
            "content rollback may precede authoritative resolution",
            "content rollback may precede resolution",
            "rollback before authoritative resolution is permitted",
        )
    )
