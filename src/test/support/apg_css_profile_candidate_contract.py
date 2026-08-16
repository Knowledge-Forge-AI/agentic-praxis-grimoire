"""Maintained APG77 contract for the CSS profile and independent scenario oracle."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
from typing import Any, NoReturn


CLAUSE_RE = re.compile(r"<!-- APG-CLAUSE: (CSS-[A-Z-]+) -->")
SELECTIONS = ("selected", "embedded-route", "route-to-owner", "non-trigger")
RESPONSES = (
    "proceed-routine",
    "inspect-before-judgment",
    "bounded-local-decision",
    "stop-and-escalate",
)
ROUTES = (
    "DOM-owner", "host-owner", "project-configuration", "project-design-owner",
    "browser-compatibility-owner", "build-transform-owner",
    "generated-artifact-owner", "visual-validation-owner",
    "accessibility-owner", "runtime-owner", "asset-owner", "font-owner",
    "network-owner", "security-owner", "performance-owner", "deployment-owner",
)
SCENARIO_CONCLUSION_SHA256 = (
    "36b164ce4262aa957a14e7f05bc74fcc88f9a849bb64af717cd4044ceaea8ce2"
)
ROW_KEYS = {
    "artifact_class", "authority", "conclusion", "css_selection", "edit",
    "forbid", "id", "present", "purpose", "required", "response", "routes",
    "whole_file_owner",
}
OPERATIONAL_CLAUSES = {"CSS-NONTRIGGER", "CSS-STRUCTURE-DEFERRED"}


class ContractError(ValueError):
    """The maintained CSS profile contract is malformed."""


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strings(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(f"{context} must be a string array")
    if len(value) != len(set(value)):
        fail(f"{context} contains duplicates")
    return value


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        fail("candidate frontmatter is missing")
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            return result
        key, separator, value = line.partition(": ")
        if not separator or key in result:
            fail("candidate frontmatter is malformed")
        result[key] = value
    fail("candidate frontmatter is unterminated")


def parse_clauses(*texts: str) -> dict[str, str]:
    clauses: dict[str, str] = {}
    for text in texts:
        matches = list(CLAUSE_RE.finditer(text))
        for index, match in enumerate(matches):
            clause_id = match.group(1)
            if clause_id in clauses:
                fail(f"duplicate clause ID: {clause_id}")
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            clauses[clause_id] = text[match.end():end].strip()
    return clauses


def parse_coverage(text: str) -> dict[str, tuple[str, ...]]:
    rows: dict[str, tuple[str, ...]] = {}
    for line in text.splitlines():
        if not line.startswith("| `APG76-CSS-"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4:
            fail("coverage row shape is invalid")
        scenario = cells[0].strip("`")
        if scenario in rows:
            fail(f"duplicate coverage scenario: {scenario}")
        clauses = tuple(re.findall(r"`(CSS-[A-Z-]+)`", cells[2]))
        if not clauses or len(clauses) != len(set(clauses)):
            fail(f"coverage clauses are invalid for {scenario}")
        rows[scenario] = clauses
    return rows


def validate_navigation(coverage: dict[str, tuple[str, ...]], clauses: dict[str, str]) -> None:
    expected = {f"APG76-CSS-{index:03d}" for index in range(1, 25)}
    if len(clauses) != 27 or set(coverage) != expected:
        fail("candidate clause or scenario cardinality is invalid")
    referenced = {clause for mapped in coverage.values() for clause in mapped}
    if referenced - set(clauses):
        fail("coverage maps an unknown clause")
    if set(clauses) - referenced != OPERATIONAL_CLAUSES:
        fail("candidate clause reachability is invalid")


def load_scenario_fixture(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    validate_scenario_fixture(value)
    return value


def validate_scenario_fixture(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {
        "authority", "rows", "schema_version", "vocabulary"
    }:
        fail("scenario fixture top-level schema is invalid")
    if value["schema_version"] != 1:
        fail("scenario fixture schema version is invalid")
    if value["authority"] != {
        "phase": "APG77",
        "source": "two independent Codex oracles resolved against primary sources and fresh target evidence",
        "semantic_rows": 24,
        "fixture_rows": 14,
        "target_rows": 7,
    }:
        fail("scenario fixture authority is invalid")
    if value["vocabulary"] != {
        "selections": list(SELECTIONS), "responses": list(RESPONSES),
        "routes": list(ROUTES),
    }:
        fail("scenario fixture vocabulary is invalid")
    if set(SELECTIONS) & set(RESPONSES):
        fail("selection and response vocabularies overlap")
    rows = value["rows"]
    if not isinstance(rows, list) or len(rows) != 45:
        fail("scenario fixture must contain 45 rows")
    expected = (
        [f"APG77-CSS-{index:03d}" for index in range(1, 25)]
        + [f"APG77-FX-{index:03d}" for index in range(1, 15)]
        + [f"APG77-TARGET-{index:03d}" for index in range(1, 8)]
    )
    if [row.get("id") for row in rows if isinstance(row, dict)] != expected:
        fail("scenario IDs are not complete and ordered")
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            fail("scenario row schema is invalid")
        if row["css_selection"] not in SELECTIONS:
            fail(f"{row['id']} has an unknown selection")
        if row["response"] not in RESPONSES:
            fail(f"{row['id']} has an unknown response")
        for field in ("authority", "forbid", "present", "required", "routes"):
            _strings(row[field], f"{row['id']} {field}")
        if not set(row["routes"]) <= set(ROUTES):
            fail(f"{row['id']} has an unknown route owner")
        if set(row["present"]) & set(row["required"]):
            fail(f"{row['id']} copies present evidence into required evidence")
        if not row["routes"] and row["response"] != "proceed-routine":
            fail(f"{row['id']} drops a route or obligation")
        for field in ("artifact_class", "conclusion", "edit", "purpose", "whole_file_owner"):
            if not isinstance(row[field], str) or not row[field]:
                fail(f"{row['id']} has an empty {field}")
    by_id = {row["id"]: row for row in rows}
    media_conclusion = by_id["APG77-CSS-016"]["conclusion"]
    if "unknown" not in media_conclusion or "evaluates false" in media_conclusion:
        fail("unknown media semantics were reduced to false")
    if "stronger than token parsing" not in by_id["APG77-CSS-017"]["conclusion"]:
        fail("supports semantics were reduced to parsing")
    for row_id in ("APG77-TARGET-002", "APG77-TARGET-003", "APG77-TARGET-004"):
        if by_id[row_id]["css_selection"] != "embedded-route":
            fail(f"{row_id} loses decision-scoped CSS participation")
    generated = by_id["APG77-TARGET-005"]
    if "read-only" not in generated["conclusion"] or generated["edit"] != "owner permission required":
        fail("generated semantic reading and edit permission are conflated")
    unknown = by_id["APG77-TARGET-006"]
    if unknown["response"] != "stop-and-escalate":
        fail("unknown tool or browser state does not stop dependent claims")
    website = by_id["APG77-TARGET-007"]
    if website["css_selection"] != "embedded-route" or "embedded CSS" not in website["conclusion"]:
        fail("website embedded SVG CSS boundary is missing")
    conclusion_bytes = "\n".join(
        row["id"] + "\0" + row["conclusion"] for row in rows
    ).encode("utf-8")
    if hashlib.sha256(conclusion_bytes).hexdigest() != SCENARIO_CONCLUSION_SHA256:
        fail("candidate-independent scenario consequences changed")


def _split_top_level(value: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for index, character in enumerate(value):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        elif character == "," and depth == 0:
            parts.append(value[start:index].strip())
            start = index + 1
    parts.append(value[start:].strip())
    return parts


def selector_specificity(selector: str) -> tuple[int, int, int]:
    """Compute the bounded Selectors-4 subset used by APG77 controls."""
    total = [0, 0, 0]
    remaining = selector
    function = re.compile(r":(is|not|has|where)\(([^()]*)\)")
    while True:
        match = function.search(remaining)
        if not match:
            break
        name, arguments = match.groups()
        contribution = (0, 0, 0) if name == "where" else max(
            selector_specificity(part) for part in _split_top_level(arguments)
        )
        total = [left + right for left, right in zip(total, contribution)]
        remaining = remaining[:match.start()] + " " + remaining[match.end():]
    total[0] += len(re.findall(r"#[A-Za-z_][\w-]*", remaining))
    total[1] += len(re.findall(r"\.[A-Za-z_][\w-]*", remaining))
    total[1] += len(re.findall(r"\[[^\]]+\]", remaining))
    total[1] += len(re.findall(r"(?<!:):(?!:)[A-Za-z_][\w-]*", remaining))
    total[2] += len(re.findall(r"::[A-Za-z_][\w-]*", remaining))
    stripped = re.sub(
        r"#[\w-]+|\.[\w-]+|\[[^\]]+\]|::?[\w-]+|[>+~*]", " ", remaining
    )
    total[2] += len(re.findall(r"(?<![-\w])[A-Za-z_][\w-]*", stripped))
    return tuple(total)


def selector_list_forgiving(function_name: str | None) -> bool:
    return function_name in {"is", "where"}


def cascade_rank(
    *, important: bool, element_attached: bool, layer_index: int | None,
    specificity: tuple[int, int, int], order: int,
) -> tuple[int, int, int, tuple[int, int, int], int]:
    """Rank bounded author-origin declarations under Cascade 5."""
    importance = 1 if important else 0
    attached = 1 if element_attached else 0
    if layer_index is None:
        layer = -1 if important else 1_000_000
    else:
        layer = -layer_index if important else layer_index
    return importance, attached, layer, specificity, order


def media_query_branch(kind: str, *, negated: bool = False) -> str:
    """Model the distinct Media Queries 4 error and unknown branches."""
    if kind in {"unknown-feature", "unknown-value"}:
        return "unknown-does-not-match"  # feature negation remains unknown
    if kind == "grammar-invalid":
        return "not-all-does-not-match"
    if kind == "unknown-media-type":
        return "matches" if negated else "does-not-match"
    if kind == "known":
        return "environment-required"
    fail("unknown media-query control kind")


def custom_property_consequence(
    state: str, *, registered_syntax: str | None = None, target_inherits: bool = False
) -> str:
    """Return the bounded Variables-1 consequence used by the fixture."""
    if state == "missing-with-fallback":
        return "fallback"
    if state == "empty":
        return "substitute-empty-then-validate"
    if state in {"cycle", "invalid-target-value", "missing-without-fallback"}:
        if registered_syntax and registered_syntax != "*":
            return "registered-initial-or-inherited"
        return "inherited" if target_inherits else "initial"
    fail("unknown custom-property control state")


def shorthand_longhands(
    prior: dict[str, str], values: dict[str, str], family: tuple[str, ...], initial: str
) -> dict[str, str]:
    result = dict(prior)
    for longhand in family:
        result[longhand] = values.get(longhand, initial)
    return result


def supports_declaration_result(*, accepted_and_usable: bool) -> str:
    return "implementation-support-not-render" if accepted_and_usable else "not-supported"


def nesting_specificity(
    parent_selectors: list[str], nested_selector: str
) -> tuple[int, int, int]:
    parent = max(selector_specificity(item) for item in parent_selectors)
    nested = selector_specificity(nested_selector.replace("&", ""))
    return tuple(left + right for left, right in zip(parent, nested))


def logical_inline_start(
    *, writing_mode: str, direction: str, text_orientation: str
) -> str:
    if text_orientation not in {"mixed", "upright", "sideways"}:
        fail("unknown text orientation")
    if writing_mode == "horizontal-tb":
        return "left" if direction == "ltr" else "right"
    if writing_mode in {"vertical-rl", "vertical-lr"}:
        return "top" if direction == "ltr" else "bottom"
    fail("unknown writing mode")


def current_color(element_color: str) -> str:
    return element_color


def pseudo_box_generated(*, content: str, replaced: bool, displayed: bool) -> bool:
    return displayed and not replaced and content not in {"none", "normal"}


def candidate_guard_failures(leaf: str, specification: str) -> list[str]:
    normalized = " ".join((leaf + "\n" + specification).split())
    lower = normalized.lower()
    required = {
        "construct-selected normative authority": "normative module is selected by the construct and claim",
        "decision-scoped role state": "role state is decision-scoped",
        "framework-selected pipeline": "framework-selected pipeline",
        "inline CSS participation": "style attribute contains CSS declarations",
        "SVG CSS participation": "recognized SVG presentation attribute",
        "read-only semantic decision": "read-only CSS semantic decision",
        "edit permission separation": "does not grant edit permission",
        "bounded cascade": "winner within an explicitly bounded declaration set",
        "motion disposition": "animation and transition timing or runtime effects route",
    }
    failures = [name for name, marker in required.items() if marker.lower() not in lower]
    failures.extend(
        f"missing response token {token}" for token in RESPONSES if token not in lower
    )
    forbidden = {
        "fictional project module configuration": "exact project-selected source modules",
        "generated reading forbidden": "never admit `selected`, even for reading",
        "media false collapse": "unknown media feature evaluates false",
        "supports parse collapse": "tests parse acceptance",
        "universal declaration graph": "every participating declaration or stop",
    }
    failures.extend(name for name, marker in forbidden.items() if marker.lower() in lower)
    if re.search(r"(?i)\b(?:300|600|900)\s*(?:lines?|band|threshold)", normalized):
        failures.append("numeric structural band")
    for marker, name in (
        ("record-growth-state", "growth-state obligation"),
        ("sixty-row", "sixty-row action map"),
        ("automatically convert", "automatic conversion"),
    ):
        if marker in lower:
            failures.append(name)
    return failures


def validate_candidate(leaf: str, specification: str, coverage: str) -> None:
    frontmatter = parse_frontmatter(leaf)
    if frontmatter != {
        "name": "css-language-profile",
        "description": (
            "Use when a material decision depends on CSS-specific static semantics — "
            "syntax validity, selector specificity, cascade ordering, inheritance, "
            "shorthand resets, custom-property substitution, or value consequences — "
            "for an established CSS region whose artifact boundary and consequence-bearing "
            "evidence are identified."
        ),
    }:
        fail("candidate frontmatter is invalid")
    clauses = parse_clauses(leaf, specification)
    navigation = parse_coverage(coverage)
    validate_navigation(navigation, clauses)
    failures = candidate_guard_failures(leaf, specification)
    if failures:
        fail("candidate guard failures: " + ", ".join(failures))
    if "navigation only" not in coverage.lower():
        fail("coverage is not navigation-only")
    if re.search(r"(?im)^\s*(?:expected (?:result|outcome|action)|result|outcome):", coverage):
        fail("coverage contains an expected consequence")
