"""Bounded source and numeric polarity guards for Markdown evidence."""

from __future__ import annotations

import re

from apg_markdown_clause_guard_contract import POSITIVE, guard_state


MACHINE_SOURCE_GUARDS = {
    "APG63-MD-013": "profile owns fence",
    "APG63-MD-017": "selected markdown syntax recognizes",
    "APG63-MD-018": "exact permission receiver is project-policy",
    "APG63-MD-019": "repository rule forbids raw html",
    "APG63-MD-020": "parser-established boundary",
    "APG63-MD-021": "documented schema",
    "APG63-MD-022": "configured parser reclassify frontmatter",
    "APG63-MD-024": ".mdx is a whole-file non-trigger",
    "APG63-MD-025": ".mdx is a whole-file non-trigger",
    "APG63-MD-026": ".mdx is a whole-file non-trigger",
    "APG63-MD-027": "host retains whole-file ownership",
    "APG63-MD-029": "generator-owned output",
    "APG63-MD-030": "project input",
    "APG63-MD-031": "bounded reviewer judgment",
    "APG63-MD-032": "project-policy",
    "APG63-MD-033": "navigation",
    "APG63-MD-034": "project-policy",
}
SOURCE_DIRECT_NEGATIONS = {
    "APG63-MD-013": ("profile does not own the fence",),
    "APG63-MD-017": ("selected markdown syntax does not recognize",),
    "APG63-MD-018": ("exact permission receiver is not project-policy",),
    "APG63-MD-019": ("repository rule does not forbid raw html",),
    "APG63-MD-020": (
        "parser-established boundary does not apply",
        "parser-established boundary must be ignored",
    ),
    "APG63-MD-021": ("schema is not documented",),
    "APG63-MD-022": ("configured parser does not reclassify frontmatter",),
    "APG63-MD-024": (".mdx is not a whole-file non-trigger",),
    "APG63-MD-025": (".mdx is not a whole-file non-trigger",),
    "APG63-MD-026": (".mdx is not a whole-file non-trigger",),
    "APG63-MD-027": ("host does not retain whole-file ownership",),
    "APG63-MD-029": ("output is not generator-owned",),
    "APG63-MD-030": (
        "project input is not an evidentiary source",
        "project input is irrelevant to the decision",
    ),
    "APG63-MD-031": (
        "reviewer judgment is not bounded",
        "bounded reviewer judgment is invalid evidence",
    ),
    "APG63-MD-032": ("project-policy is not the source owner",),
    "APG63-MD-033": (
        "navigation is not evidence",
        "navigation provides no evidence",
    ),
    "APG63-MD-034": (
        "project-policy does not require repository evidence",
        "repository evidence is not required",
        "repository evidence must not be used",
        "no repository evidence may be considered",
    ),
}


def source_guard_state(row_id: str, mapped_text: str) -> str:
    """Return bounded positive, negative, conflict, or absent source evidence."""

    marker = MACHINE_SOURCE_GUARDS.get(row_id)
    if marker is None:
        return "human-review-required"
    return guard_state(
        mapped_text,
        marker,
        direct_negations=SOURCE_DIRECT_NEGATIONS.get(row_id, ()),
    )


def source_guard_passes(row_id: str, mapped_text: str) -> bool:
    return source_guard_state(row_id, mapped_text) == POSITIVE


COUNT_RE = r"\b(?:\d+\s*-\s*\d+(?:\s*-?\s*lines?)?|\d+\s*-?\s*lines?)\b"
POLICY_ACTION_RE = re.compile(
    r"\b(?:classif(?:y|ies|ying)|trigger(?:s|ed|ing)?|fir(?:e|es|ed|ing)|"
    r"select(?:s|ed|ing)?|authoriz(?:e|es|ed|ing)|requir(?:e|es|ed|ing)|"
    r"split(?:s|ting)?(?: the document)?)\b"
)
NEGATED_ACTION_PREFIX_RE = re.compile(
    r"(?:(?:does not|do not|never|cannot|is insufficient to|are insufficient to)\s+|"
    r"(?:does not|do not|never|cannot)\b.{0,40}\bor\s+|no\s+)$"
)
NEGATED_ACTION_SUFFIX_RE = re.compile(r"^\s+(?:no|not)\s+(?:signal|response|split)\b")
COORDINATOR_RE = re.compile(
    r"(?:[;:,]|\b(?:and|but|while|whereas|however|therefore|then)\b)"
)
SUBJECT_TOKEN_RE = re.compile(r"^[a-z][a-z0-9-]*$")
SUBJECT_DETERMINERS = {"a", "an", "the"}
INHERITED_SUBJECT_HEADS = {
    "count", "document", "it", "line", "lines", "measurement", "number",
    "that", "these", "they", "this", "those",
}
PREDICATE_LEAD_INS = {
    "also", "always", "are", "be", "been", "being", "can", "could", "did",
    "do", "does", "had", "has", "have", "instead", "is", "may", "might",
    "must", "never", "often", "ought", "perhaps", "rather", "shall", "should",
    "sometimes", "still", "then", "therefore", "usually", "was", "were",
    "will", "would", "yet",
}
ASPECTUAL_PREDICATE_HEADS = {
    "appears", "begins", "ceases", "continues", "finishes", "keeps", "needs",
    "persists", "proceeds", "remains", "resumes", "seems", "starts", "stops",
    "tends", "tries",
}
PREDICATE_PARTICIPLES = {
    "authorized", "classified", "fired", "required", "selected", "triggered",
}


def _action_is_negative(statement: str, action: re.Match[str]) -> bool:
    prefix = statement[max(0, action.start() - 48) : action.start()]
    suffix = statement[action.end() : min(len(statement), action.end() + 32)]
    return bool(
        NEGATED_ACTION_PREFIX_RE.search(prefix)
        or NEGATED_ACTION_SUFFIX_RE.search(suffix)
    )


def _has_independent_subject(
    statement: str, count_end: int, action: re.Match[str]
) -> bool:
    between = statement[count_end:action.start()]
    coordinators = tuple(COORDINATOR_RE.finditer(between))
    if not coordinators:
        return False
    tail = between[coordinators[-1].end() :].strip()
    tail = re.sub(r"^(?:therefore|then|also)\s+", "", tail)
    words = tail.split()
    while words and (words[0] in PREDICATE_LEAD_INS or words[0].endswith("ly")):
        words.pop(0)
    if words and words[0] in SUBJECT_DETERMINERS:
        words.pop(0)
    if not words:
        return False
    subject_head = words[0]
    predicate_only = (
        subject_head in PREDICATE_LEAD_INS
        or subject_head in ASPECTUAL_PREDICATE_HEADS
        or (
            words[-1] == "to"
            and (
                len(words) <= 2
                or (len(words) == 3 and words[-2] in PREDICATE_PARTICIPLES)
            )
        )
        or (
            len(words) == 1
            and action.group().endswith(("ed", "ing"))
        )
    )
    return bool(
        SUBJECT_TOKEN_RE.fullmatch(subject_head)
        and subject_head not in INHERITED_SUBJECT_HEADS
        and not predicate_only
        and not subject_head.endswith("ly")
    )


def _count_anchor_is_forbidden(statement: str, count: re.Match[str]) -> bool:
    if re.search(COUNT_RE, statement) is None:
        return False
    level = r"(?:green|yellow|orange|red)"
    nearby = statement[max(0, count.start() - 36) : min(len(statement), count.end() + 48)]
    if re.search(rf"{COUNT_RE}\s+(?:(?:is|are)\s+)?{level}\b", nearby) or re.search(
        rf"\b{level}\b.{{0,24}}{COUNT_RE}", nearby
    ):
        return True
    threshold_word = r"(?:thresholds?|bands?)"
    before = statement[max(0, count.start() - 40) : count.end()]
    after = statement[count.start() : min(len(statement), count.end() + 48)]
    escaped_count = re.escape(count.group())
    threshold = re.search(
        rf"^{escaped_count}.{{0,36}}\b{threshold_word}\b", after
    ) or re.search(rf"\b{threshold_word}\b.{{0,36}}{escaped_count}$", before)
    threshold_negative = re.search(
        rf"^{escaped_count}.{{0,24}}(?:is not|does not create|is no)\s+"
        rf"(?:a\s+)?(?:threshold|band)\b",
        after,
    ) or (
        re.search(rf"\bno\s+{escaped_count}$", before)
        and re.search(rf"^{escaped_count}.{{0,24}}(?:threshold|band)\b", after)
    )
    threshold_negative = threshold_negative or re.search(
        rf"\bno\s+{threshold_word}\b.{{0,24}}{escaped_count}$", before
    )
    if threshold and not threshold_negative:
        return True
    for action in POLICY_ACTION_RE.finditer(statement, count.end()):
        if _has_independent_subject(statement, count.end(), action):
            continue
        if not _action_is_negative(statement, action):
            return True
    return False


def has_forbidden_numeric_policy(text: str) -> bool:
    """Detect bounded normative count policy while permitting stated negatives."""

    normalized = text.replace("`", "").replace("–", "-").replace("—", "-").lower()
    statements = re.split(r"[\n.!?]+", normalized)
    return any(
        _count_anchor_is_forbidden(statement, count)
        for statement in statements
        for count in re.finditer(COUNT_RE, statement)
    )
