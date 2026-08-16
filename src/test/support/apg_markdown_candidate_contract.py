"""Focused parser for the APG66 Markdown candidate test contract."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
from typing import Any, NoReturn

from apg_markdown_clause_guard_contract import (
    CONFLICTED,
    NEGATIVE,
    POSITIVE,
    TARGETED_GUARD_MARKERS,
    local_guard_observations,
    targeted_guard_states,
    unconditional_rollback_state,
)
from apg_markdown_polarity_guard_contract import MACHINE_SOURCE_GUARDS
from apg_markdown_polarity_guard_contract import has_forbidden_numeric_policy
from apg_markdown_polarity_guard_contract import source_guard_state
from apg_markdown_token_guard_contract import (
    HUMAN_ROLLBACK_ROWS,
    TOKEN_EDGE,
    exact_tokens,
    observed_rollback_classes,
    pending_resolution_is_contradicted,
)
from apg_markdown_vocabulary_contract import ACCEPTED_VOCABULARY
from apg_markdown_vocabulary_contract import verify_exact_vocabulary

REGISTER_BLOB_OID = "d3ac0dc2140e9daa87cdde7249a80ca0fcb934d6"
CLAUSE_RE = re.compile(r"<!-- APG-CLAUSE: (MARKDOWN-[A-Z-]+) -->")
SCENARIO_RE = re.compile(r"APG63-MD-(\d{3})")
OWNER_PATTERN = "(?:" + "|".join(
    re.escape(token) for token in ACCEPTED_VOCABULARY["owners"]
) + ")"
OWNER_RE = re.compile(rf"(?<!{TOKEN_EDGE}){OWNER_PATTERN}(?!{TOKEN_EDGE})")
CONTRADICTED_OWNER_RE = re.compile(
    rf"(?:(?P<owner>{OWNER_RE.pattern})\s+(?:is|stays)\s+(?:a\s+)?non-owner\b|"
    rf"(?:not|never)\s+owned\s+by\s+(?P<reverse>{OWNER_RE.pattern}))"
)
LOCAL_SOURCE_BOUNDARY_MARKERS = MACHINE_SOURCE_GUARDS
LOCAL_SIGNAL_ROWS = frozenset({
    "APG63-MD-017", "APG63-MD-018", "APG63-MD-030", "APG63-MD-031",
    "APG63-MD-032", "APG63-MD-033", "APG63-MD-034",
})
AXIS_NAVIGATION_ROWS = frozenset({
    "APG63-MD-002", "APG63-MD-003", "APG63-MD-004",
    "APG63-MD-013", "APG63-MD-017", "APG63-MD-018",
    "APG63-MD-020", "APG63-MD-025", "APG63-MD-026",
})
ROW_KEYS = {
    "decision_class", "id", "nonowners", "owner", "response", "rollback_class",
    "route", "selection", "semantic_signals", "source_boundary_class",
    "structural_signals",
}

class ContractError(ValueError):
    """A candidate or vector violates the closed executable contract."""

def fail(message: str) -> NoReturn:
    raise ContractError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_fixture(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    validate_fixture(value)
    return value


def _strings(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(f"{context} must be a string array")
    if len(value) != len(set(value)):
        fail(f"{context} contains duplicates")
    return value


def _require_exact_vocabulary(vocabulary: Any) -> None:
    try:
        verify_exact_vocabulary(vocabulary)
    except ValueError as error:
        fail(str(error))


def validate_fixture(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {
        "authority", "rows", "schema_version", "vocabulary"
    }:
        fail("fixture top-level schema is invalid")
    if value["schema_version"] != 1:
        fail("fixture schema version is invalid")
    authority = value["authority"]
    if authority != {
        "source_phase": "APG64",
        "register_blob_oid": REGISTER_BLOB_OID,
        "semantic_rows": 34,
        "process_rows": 0,
    }:
        fail("fixture authority binding is invalid")
    vocabulary = value["vocabulary"]
    _require_exact_vocabulary(vocabulary)
    rows = value["rows"]
    if not isinstance(rows, list) or len(rows) != 34:
        fail("fixture must contain exactly 34 semantic rows")
    expected_ids = [f"APG63-MD-{index:03d}" for index in range(1, 35)]
    if [row.get("id") for row in rows if isinstance(row, dict)] != expected_ids:
        fail("fixture IDs must be contiguous semantic rows 001 through 034")
    route_tokens = set(vocabulary["owners"]) | {"not-applicable"}
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            fail("fixture row schema is invalid")
        for field in ("nonowners", "semantic_signals", "structural_signals"):
            _strings(row[field], f"{row['id']} {field}")
        for field, vocab_key in (
            ("owner", "owners"), ("selection", "selections"),
            ("response", "responses"), ("rollback_class", "rollback_classes"),
            ("source_boundary_class", "source_boundary_classes"),
        ):
            if row[field] not in vocabulary[vocab_key]:
                fail(f"{row['id']} uses unknown {field}")
        if row["route"] not in route_tokens:
            fail(f"{row['id']} uses unknown route")
        if not set(row["nonowners"]) <= set(vocabulary["owners"]):
            fail(f"{row['id']} uses unknown nonowner")
        for field, vocab_key in (
            ("semantic_signals", "semantic_signals"),
            ("structural_signals", "structural_signals"),
        ):
            if not set(row[field]) <= set(vocabulary[vocab_key]):
                fail(f"{row['id']} uses unknown {field}")
        if row["owner"] in row["nonowners"]:
            fail(f"{row['id']} owner is also a nonowner")


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
            next_heading = text.find("\n## ", match.end(), end)
            if next_heading >= 0:
                end = next_heading
            clauses[clause_id] = text[match.end():end].strip()
    return clauses


def parse_coverage(text: str) -> dict[str, tuple[str, ...]]:
    rows: dict[str, tuple[str, ...]] = {}
    for line in text.splitlines():
        if not line.startswith("| APG63-MD-"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 3:
            fail("coverage row shape is invalid")
        scenario = cells[0]
        if scenario in rows:
            fail(f"duplicate coverage scenario: {scenario}")
        clauses = tuple(re.findall(r"`(MARKDOWN-[A-Z-]+)`", cells[2]))
        if not clauses or len(clauses) != len(set(clauses)):
            fail(f"coverage clauses are invalid for {scenario}")
        rows[scenario] = clauses
    return rows


def validate_navigation(
    rows: list[dict[str, Any]], coverage: dict[str, tuple[str, ...]], clauses: dict[str, str]
) -> None:
    expected = {row["id"] for row in rows}
    if len(clauses) != 24:
        fail("candidate must contain exactly 24 clauses")
    if set(coverage) != expected:
        fail("coverage scenarios differ from the 34 semantic rows")
    referenced = {clause for mapped in coverage.values() for clause in mapped}
    if referenced - set(clauses):
        fail("coverage maps an unknown clause")
    if set(clauses) - referenced:
        fail("candidate contains a dead clause")


def parse_signal_table(clause: str) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in clause.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 5:
            fail("structural-signal table row is malformed")
        signal = cells[0].strip("`")
        if signal in rows:
            fail(f"duplicate structural signal: {signal}")
        response_tokens = sorted(exact_tokens(
            cells[3],
            ("bounded-local-decision", "inspect-before-judgment", "stop-and-escalate"),
        ))
        routes = sorted(exact_tokens(cells[3], ACCEPTED_VOCABULARY["owners"]))
        rows[signal] = {
            "evidence_class": cells[1],
            "observable_and_scope": cells[2],
            "responses": ",".join(response_tokens),
            "routes": ",".join(routes),
            "false_positive_control": cells[4],
        }
    return rows


def _normalized(text: str) -> str:
    return " ".join(text.replace("`", "").split()).lower()


def _contradicted_owners(text: str) -> set[str]:
    return {
        match.group("owner") or match.group("reverse")
        for match in CONTRADICTED_OWNER_RE.finditer(_normalized(text))
    }


def _rollback_aliases(text: str) -> set[str]:
    return observed_rollback_classes(_normalized(text))


def _rollback_guard_results(
    row: dict[str, Any], mapped_text: str
) -> tuple[list[str], list[str], str | None]:
    missing: list[str] = []
    human: list[str] = []
    state: str | None = None
    rollback = row["rollback_class"]
    if rollback == "none":
        state = unconditional_rollback_state(mapped_text)
        if state in {POSITIVE, CONFLICTED}:
            missing.append("rollback:unexpected-unconditional")
    elif row["id"] in HUMAN_ROLLBACK_ROWS:
        human.append("rollback_class")
    elif rollback not in _rollback_aliases(mapped_text):
        missing.append(f"rollback:{rollback}")
    if row["id"] == "APG63-MD-034" and pending_resolution_is_contradicted(
        _normalized(mapped_text)
    ):
        missing.append("rollback:pending-resolution-contradiction")
    return missing, human, state


def _source_guard_results(
    row: dict[str, Any], normalized: str
) -> tuple[list[str], list[str], str | None]:
    if row["id"] not in MACHINE_SOURCE_GUARDS:
        return [], ["source_boundary_class"], None
    state = source_guard_state(row["id"], normalized)
    if state == POSITIVE:
        return [], [], state
    return [f"source-boundary-evidence:{row['source_boundary_class']}"], [], state


def scenario_support(
    row: dict[str, Any], coverage: dict[str, tuple[str, ...]], clauses: dict[str, str]
) -> dict[str, Any]:
    mapped = coverage[row["id"]]
    unknown = set(mapped) - set(clauses)
    if unknown:
        fail(f"{row['id']} maps unknown clauses: {sorted(unknown)}")
    mapped_text = "\n".join(clauses[clause] for clause in mapped)
    normalized = _normalized(mapped_text)
    observed = local_guard_observations(row, mapped_text)
    missing: list[str] = []
    human_review_required: list[str] = []
    if row["id"] in AXIS_NAVIGATION_ROWS and "MARKDOWN-AXES" not in mapped:
        missing.append("axis-navigation")
    if row["id"] == "APG63-MD-013" and "MARKDOWN-EMBEDDED-ROUTE" in mapped:
        missing.append("reversed-embedding-direction")
    if row["owner"] in _contradicted_owners(mapped_text):
        missing.append(f"owner-contradicted-as-nonowner:{row['owner']}")
    if row["id"] in LOCAL_SIGNAL_ROWS:
        for signal in row["structural_signals"]:
            if signal not in observed["structural_signals"]:
                missing.append(f"structural-signal:{signal}")
        for signal in row["semantic_signals"]:
            if signal not in observed["semantic_signals"]:
                missing.append(f"semantic-signal:{signal}")
    rollback_missing, rollback_human, rollback_state = _rollback_guard_results(
        row, mapped_text
    )
    source_missing, source_human, source_state = _source_guard_results(row, normalized)
    missing.extend(rollback_missing)
    missing.extend(source_missing)
    human_review_required.extend(rollback_human)
    human_review_required.extend(source_human)
    guard_results = dict(observed["guard_states"])
    if rollback_state is not None:
        guard_results["rollback:unconditional"] = rollback_state
    if source_state is not None:
        guard_results["source-boundary"] = source_state
    observed_tokens = set().union(
        observed["owners"],
        observed["axes"],
        observed["structural_signals"],
        observed["semantic_signals"],
    )
    return {
        "id": row["id"], "mapped_clauses": mapped,
        "owners": sorted(observed["owners"]), "axes": sorted(observed["axes"]),
        "structural_signals": sorted(observed["structural_signals"]),
        "semantic_signals": sorted(observed["semantic_signals"]),
        "rollback_classes": sorted(_rollback_aliases(mapped_text)), "missing": missing,
        "local_observed_tokens": sorted(observed_tokens),
        "local_positive_guards": sorted(
            name for name, state in guard_results.items() if state == POSITIVE
        ),
        "local_negative_guards": sorted(
            name for name, state in guard_results.items() if state == NEGATIVE
        ),
        "local_conflicts": sorted(
            name for name, state in guard_results.items() if state == CONFLICTED
        ),
        "human_review_required": sorted(human_review_required),
    }


def targeted_guard_failures(clauses: dict[str, str]) -> list[str]:
    """Check only the APG66 amendment and named high-risk candidate guards."""
    failures: list[str] = []
    for name, state in targeted_guard_states(clauses).items():
        if state != POSITIVE:
            failures.append(name)
    grammar = _normalized(clauses.get("MARKDOWN-EFFECTIVE-GRAMMAR", ""))
    ordered = (
        grammar.find("1. the actual repository renderer or parser"),
        grammar.find("2. commonmark 0.31.2"),
        grammar.find("3. gfm 0.29"),
        grammar.find("4. implementation-specific behavior"),
    )
    if any(position < 0 for position in ordered) or tuple(sorted(ordered)) != ordered:
        failures.append("actual-parser-first-hierarchy")
    validation = clauses.get("MARKDOWN-VALIDATION", "")
    if orange_requires_unqualified_rollback(validation):
        failures.append("navigation-only-orange-no-material-rollback")
    raw_combined = "\n".join(clauses.values())
    combined = _normalized(raw_combined)
    if has_forbidden_numeric_policy(raw_combined):
        failures.append("no-numeric-bands")
    process_leak = re.search(r"apg63-md-03[56]", combined) or (
        all(re.search(rf"\b{term}\b", combined) for term in (
            "candidate", "catalog", "release", "projection",
        ))
        and any(re.search(rf"\b{term}\b", combined) for term in ("git", "report", "review"))
    ) or re.search(r"delete (?:the )?(?:only auditable corrected state|current candidate surfaces?)", combined)
    if process_leak:
        failures.append("no-process-invariant-leakage")
    return sorted(failures)


def orange_requires_unqualified_rollback(validation_clause: str) -> bool:
    normalized = _normalized(validation_clause)
    match = re.search(r"orange[^;]+", normalized)
    if not match:
        fail("Orange validation consequence is missing")
    orange = match.group(0)
    return "rollback" in orange and not re.search(
        r"rollback (?:when|where|if) (?:material|required|applicable)", orange
    )
