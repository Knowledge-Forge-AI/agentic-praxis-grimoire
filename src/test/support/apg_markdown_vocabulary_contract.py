"""Independent exact accepted vocabulary for APG64 Markdown evidence."""

from __future__ import annotations

from typing import Any


ACCEPTED_VOCABULARY = {
    "owners": (
        "accessibility-owner", "data-language-owner", "embedded-language-owner",
        "generic-lifecycle", "host-owner", "html-owner", "human-instruction",
        "markdown-language-profile", "mdx-owner", "parser-tool-owner",
        "project-design", "project-policy", "repository-policy",
    ),
    "selections": (
        "embedded-route", "non-trigger", "route-to-owner", "selected",
    ),
    "responses": (
        "bounded-local-decision", "inspect-before-judgment", "proceed-routine",
        "stop-and-escalate",
    ),
    "structural_signals": (
        "code-prose-responsibility-mixing",
        "deep-or-inconsistent-heading-hierarchy", "duplicated-normative-truth",
        "history-guidance-mixing", "manual-generated-content-mixing",
        "multiple-independent-audiences", "multiple-independent-purposes",
        "navigation-failure", "oversized-single-section", "policy-evasion",
        "reference-tutorial-mixing", "repeated-definitions",
        "unsafe-source-of-truth-duplication", "whole-document-review-boundary",
    ),
    "semantic_signals": (
        "accidental-reclassification", "dialect-mismatch", "extension-unsupported",
        "false-completion", "frontmatter-body-corruption", "generated-source-drift",
        "link-destination-invalid", "normative-contradiction", "raw-html-boundary",
        "reference-definition-collision",
    ),
    "rollback_classes": (
        "none", "preserve-contradiction-pending-resolution",
        "preserve-navigation-move-map", "preserve-prechange-statements",
        "record-collision-definitions", "record-extraction-map",
        "record-frontmatter-bytes", "record-moved-responsibility",
        "record-predecision-behavior", "record-reclassified-region",
        "regenerate-from-owner",
    ),
    "source_boundary_classes": (
        "actual-parser-configuration", "actual-parser-plus-accessibility-policy",
        "actual-parser-plus-applicable-reference",
        "actual-parser-plus-bounded-reference", "actual-parser-plus-html-owner",
        "actual-parser-plus-repository-policy", "commonmark-plus-parser",
        "generator-plus-parser", "gfm-plus-parser", "host-renderer-evidence",
        "mdx-host-pipeline", "mdx-pipeline", "mdx-pipeline-outside-references",
        "parser-plus-artifact-classification", "parser-plus-navigation-evidence",
        "parser-plus-project-input", "parser-plus-reviewer-evidence",
        "pinned-specifications-plus-parser",
        "project-policy-plus-repository-evidence", "project-schema-plus-parser",
        "project-state-plus-link-policy", "repository-parser-evidence-required",
        "repository-policy-plus-parser",
    ),
}
ACCEPTED_ROUTE_TOKENS = ACCEPTED_VOCABULARY["owners"] + ("not-applicable",)
ACCEPTED_VOCABULARY_SOURCE_SHA256 = {
    "architecture": "2db5b76d6782fc073257bcd7ff377b7d507c3a4ab56cb5edc0840bd7a58f5fa6",
    "lean_contract": "46a2d79a6150f380a20f52d10e3e1ad6707d19c186318738f8ed0743273dd7ee",
    "register": "21a038ef8dc1c1f3c124e91fc20523e0a08266dc2375ec7692548d1ec21be5d1",
}


def verify_exact_vocabulary(vocabulary: Any) -> None:
    """Require the independently owned APG64 vocabulary arrays exactly."""

    if not isinstance(vocabulary, dict) or tuple(vocabulary) != tuple(ACCEPTED_VOCABULARY):
        raise ValueError("accepted vocabulary keys and order are not exact")
    for family, expected in ACCEPTED_VOCABULARY.items():
        actual = vocabulary[family]
        if not isinstance(actual, list) or tuple(actual) != expected:
            raise ValueError(f"accepted vocabulary {family} is not exact")
