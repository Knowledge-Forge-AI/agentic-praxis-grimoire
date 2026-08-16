"""Mechanical contract for the APG75 TypeScript candidate and oracle fixture."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, NoReturn


CLAUSE_RE = re.compile(r"<!-- APG-CLAUSE: (TS-[A-Z-]+) -->")
ROLE_TOKENS = (
    "cli-checker",
    "declaration-emitter",
    "programmatic-compiler-api",
    "editor-language-service",
    "embedded-language-checker",
    "source-transformer-type-stripper",
    "build-orchestrator",
    "runtime-host",
)
SELECTION_TOKENS = ("selected", "embedded-route", "route-to-owner", "non-trigger")
RESPONSE_TOKENS = (
    "proceed-routine",
    "inspect-before-judgment",
    "bounded-local-decision",
    "stop-and-escalate",
)
ROW_KEYS = {
    "fact_summary",
    "forbid",
    "id",
    "input_class",
    "nonowned_conclusion",
    "owned_conclusion",
    "present_evidence",
    "required_evidence",
    "required_option_facts",
    "required_roles",
    "response",
    "rollback_or_provenance",
    "routes_or_obligations",
    "typescript_selection",
    "whole_file_owner",
}
OPERATIONAL_CLAUSES = {"TS-NONTRIGGER", "TS-STRUCTURE-DEFERRED"}
TARGET_ROUTES = (
    "project-configuration",
    "package-owner",
    "host-owner",
    "declaration-provenance-owner",
    "runtime-owner",
)
TARGET_PRESENT = (
    "exact live object",
    "manifest/lock/scripts",
    "exercised Astro checker on TS5.9.3",
    "TS7 destination",
)
TARGET_REQUIRED = (
    "TS7-capable host route or explicit temporary compatibility",
    "declaration-emitter invocation",
)
TARGET_FORBID = (
    "package presence proves role",
    "stale lock proves execution",
    "configured emit proves invocation",
    "automatic migration",
)
PROJECT_COMPILER_CASE_KEYS = {
    "compiler_version",
    "expected_analysis_version",
    "migration_verdict",
    "project_policy",
    "question",
    "role",
}


class ContractError(ValueError):
    """A maintained TypeScript contract surface is malformed."""


def fail(message: str) -> NoReturn:
    raise ContractError(message)


def validate_project_compiler_case(value: dict[str, Any]) -> None:
    """Validate a neutral exact-compiler project decision vector."""
    if not isinstance(value, dict) or set(value) != PROJECT_COMPILER_CASE_KEYS:
        fail("project compiler case shape is invalid")
    version = value["compiler_version"]
    expected = value["expected_analysis_version"]
    policy = value["project_policy"]
    role = value["role"]
    question = value["question"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        fail("project compiler version must be exact")
    if expected != version:
        fail("analysis is not bound to the exact project compiler")
    if not isinstance(policy, str) or version.split(".", 1)[0] not in policy or "current" not in policy:
        fail("project policy does not select the evidenced compiler line")
    if role != "exact current CLI checker":
        fail("project compiler role is not exact")
    if question not in {
        "TypeScript-specific static semantics",
        "static behavior under exact options",
    }:
        fail("project question is outside the neutral compiler case")
    if value["migration_verdict"] is not None:
        fail("project case invents a migration verdict")


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
        "authored_phase": "APG75",
        "current_phase": "APG75A",
        "source": (
            "two candidate-independent Codex oracle lanes resolved against "
            "exact compiler and fresh target evidence"
        ),
        "semantic_rows": 24,
        "fixture_rows": 14,
        "target_rows": 1,
    }:
        fail("scenario fixture authority is invalid")
    if value["vocabulary"] != {
        "selections": list(SELECTION_TOKENS),
        "responses": list(RESPONSE_TOKENS),
        "roles": list(ROLE_TOKENS),
    }:
        fail("scenario fixture vocabulary is invalid")
    if set(SELECTION_TOKENS) & set(RESPONSE_TOKENS):
        fail("selection and response vocabularies overlap")
    rows = value["rows"]
    if not isinstance(rows, list) or len(rows) != 39:
        fail("scenario fixture must contain 39 rows")
    expected = (
        [f"APG74-TS-{index:03d}" for index in range(1, 25)]
        + [f"APG74-FX-{index:03d}" for index in range(1, 15)]
        + ["APG75-TARGET-001"]
    )
    if [row.get("id") for row in rows if isinstance(row, dict)] != expected:
        fail("scenario IDs are not complete and ordered")
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            fail("scenario row schema is invalid")
        if row["typescript_selection"] not in SELECTION_TOKENS:
            fail(f"{row['id']} has an unknown selection")
        if row["response"] not in RESPONSE_TOKENS:
            fail(f"{row['id']} has an unknown response")
        for field in (
            "forbid", "present_evidence", "required_evidence",
            "required_option_facts", "required_roles", "routes_or_obligations",
        ):
            _strings(row[field], f"{row['id']} {field}")
        if not set(row["required_roles"]) <= set(ROLE_TOKENS):
            fail(f"{row['id']} has an unknown role")
        if any("=" not in fact for fact in row["required_option_facts"]):
            fail(f"{row['id']} has an option name without a value")
        if set(row["present_evidence"]) & set(row["required_evidence"]):
            fail(f"{row['id']} copies present evidence into required evidence")
        if not row["routes_or_obligations"] and row["response"] != "proceed-routine":
            fail(f"{row['id']} drops a route or obligation")
    by_id = {row["id"]: row for row in rows}
    for scenario in ("APG74-TS-020", "APG74-TS-021", "APG74-FX-006", "APG74-FX-008"):
        if by_id[scenario]["typescript_selection"] != "embedded-route":
            fail(f"{scenario} must preserve its non-TypeScript whole-file owner")
    if by_id["APG74-TS-014"]["required_roles"]:
        fail("unknown role case invents a role token")
    for scenario in ("APG74-TS-014", "APG74-FX-013", "APG74-FX-014"):
        if by_id[scenario]["response"] != "stop-and-escalate":
            fail(f"{scenario} must stop on unknown evidence")
    target = by_id["APG75-TARGET-001"]
    if target["response"] != "stop-and-escalate":
        fail("target migration must reject false completion")
    if tuple(target["routes_or_obligations"]) != TARGET_ROUTES:
        fail("target migration route set is incomplete or reordered")
    if target["required_roles"] != ["embedded-language-checker"]:
        fail("target embedded role is not independently bound")
    if tuple(target["present_evidence"]) != TARGET_PRESENT:
        fail("target present evidence is incomplete or altered")
    if tuple(target["required_evidence"]) != TARGET_REQUIRED:
        fail("target required evidence is incomplete or altered")
    if tuple(target["forbid"]) != TARGET_FORBID:
        fail("target negative controls are incomplete or altered")
    if "excludes TS7" not in target["owned_conclusion"]:
        fail("target migration baseline or TS7 destination is lost")
    for marker in ("current TS7 use", "runtime completion", "direct CLI role"):
        if marker not in target["nonowned_conclusion"]:
            fail(f"target non-owned conclusion loses {marker}")
    compatibility = by_id["APG74-FX-010"]
    if compatibility["typescript_selection"] != "non-trigger":
        fail("TypeScript 6 not-required case must remain a non-trigger")
    if compatibility["response"] != "proceed-routine":
        fail("TypeScript 6 not-required case must proceed routinely")
    if compatibility["routes_or_obligations"] != ["host-owner", "package-owner"]:
        fail("TypeScript 6 not-required obligations changed")
    scenario_024 = by_id["APG74-TS-024"]
    if scenario_024["fact_summary"] != (
        "project-selected primary compiler role plus conditional compatibility role"
    ):
        fail("scenario 024 is not project-neutral")
    if "TS7 remains destination" in scenario_024["owned_conclusion"]:
        fail("scenario 024 selects a universal compiler destination")


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
        if not line.startswith("| APG74-TS-"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4:
            fail("coverage row shape is invalid")
        scenario = cells[0]
        if scenario in rows:
            fail(f"duplicate coverage scenario: {scenario}")
        clauses = tuple(re.findall(r"`(TS-[A-Z-]+)`", cells[2]))
        if not clauses or len(clauses) != len(set(clauses)):
            fail(f"coverage clauses are invalid for {scenario}")
        rows[scenario] = clauses
    return rows


def validate_navigation(coverage: dict[str, tuple[str, ...]], clauses: dict[str, str]) -> None:
    expected = {f"APG74-TS-{index:03d}" for index in range(1, 25)}
    if len(clauses) != 24 or set(coverage) != expected:
        fail("candidate clause or scenario cardinality is invalid")
    referenced = {clause for mapped in coverage.values() for clause in mapped}
    if referenced - set(clauses):
        fail("coverage maps an unknown clause")
    if set(clauses) - referenced != OPERATIONAL_CLAUSES:
        fail("candidate clause reachability is invalid")


def validate_coverage_lifecycle(text: str) -> None:
    required = (
        "Current lifecycle: provisionally integrated after APG75 and APG75A",
        "ADR 0043: Accepted with amendment",
        "Historical authoring phase: APG74",
        "Semantic authority: maintained scenario fixture plus human/compiler review",
    )
    normalized = " ".join(text.lower().split())
    if any(marker.lower() not in normalized for marker in required):
        fail("coverage lifecycle is stale or incomplete")
    for stale in (
        "status: navigation record for the proposed candidate",
        "independent hardening review pending in apg75",
        "apg75: pending",
        "apg75 pending independent review",
    ):
        if stale in normalized:
            fail("coverage lifecycle retains proposed or pending state")


def candidate_guard_failures(
    leaf: str, specification: str, *, expected_lifecycle: str = "proposed"
) -> list[str]:
    normalized = " ".join((leaf + "\n" + specification).split())
    required = {
        "decision-scoped selection": "Selection is decision-scoped",
        "embedded ownership": "checked JavaScript use `embedded-route`",
        "ordered obligations": "small ordered set of routes or obligations",
        "unknown role separation": "`unknown` is an evidence state, never a role",
        "invocation separation": "invocation state (`invoked`, `not-invoked`, or `unknown`)",
        "overload specialization": "no universal \"first matching signature\" shortcut",
        "assertion qualification": "double assertion through `unknown`",
        "const enum isolation": "`isolatedModules=true` preserves the object",
        "migration route": "creates a compatibility/migration route",
        "static runtime refusal": "static success offered as runtime proof",
        "declaration provenance": "Generated declarations are compiler output",
        "source-kind distinction": "Collapsing `.mts` and `.cts` into one source kind",
        "generated declaration edit refusal": "never hand-edited",
        "project compiler authority": "exact project-selected compiler role and version",
        "compiler line neutrality": "TypeScript 5.x, 6.x, 7.x, or another exact supported line",
        "no destination selection": "does not choose a destination generation",
        "migration ownership": "compiler migration routes to project-design and compiler-configuration owners",
    }
    normalized_lower = normalized.lower()
    failures = [
        name for name, marker in required.items() if marker.lower() not in normalized_lower
    ]
    forbidden = {
        "singular receiving owner": "one exact receiving owner",
        "old overload rule": "selects the first matching declared signature",
        "automatic migration": "automatically migrate JavaScript",
        "universal TypeScript 7 destination": "TypeScript 7 is the intended primary compiler generation",
        "universal older-compiler migration baseline": (
            "any older compiler in a live target is migration baseline evidence, never the destination"
        ),
    }
    failures.extend(
        name for name, marker in forbidden.items() if marker.lower() in normalized_lower
    )
    if re.search(r"(?i)\b(?:300|600|900)\s*(?:lines?|band|threshold)", normalized):
        failures.append("numeric structural band")
    if re.search(
        r"(?i)\b\d{1,6}\s+(?:lines?|files?|statements?)\b[^.]{0,50}"
        r"\b(?:bands?|thresholds?|limits?)\b",
        normalized,
    ):
        failures.append("numeric structural band")
    if re.search(
        r"(?i)automatic(?:ally)?\s+[^.]{0,80}migration\s+(?:is|should be|must be)\s+"
        r"(?:required|recommended|performed|done)",
        normalized,
    ):
        failures.append("automatic migration")
    contradiction_patterns = {
        "automatic migration": (
            r"(?i)\bautomatically\s+(?:perform|apply|run|start|do|recommend|require)"
            r"[^.]{0,60}\bmigration\b",
            r"(?i)\bautomatic\s+[^.]{0,60}\bmigration\s+(?:is|must|should)\s+"
            r"(?:required|recommended|performed|enabled|done)",
        ),
        "source-kind contradiction": (
            r"(?i)\bcollapse\s+`?\.mts`?\s+and\s+`?\.cts`?\s+into\s+one\s+source\s+kind",
            r"(?i)\btreat\s+`?\.mts`?\s+and\s+`?\.cts`?\s+as\s+(?:the\s+)?same",
        ),
        "generated declaration edit contradiction": (
            r"(?i)generated declarations?\s+(?:may|can|should|must)\s+be\s+hand-edited",
        ),
        "static runtime contradiction": (
            r"(?i)static success\s+(?:proves|establishes|guarantees)\s+[^.]{0,40}runtime",
        ),
    }
    for diagnostic, patterns in contradiction_patterns.items():
        if any(re.search(pattern, normalized) for pattern in patterns):
            failures.append(diagnostic)
    lifecycle = expected_lifecycle.lower()
    lower = normalized.lower()
    if lifecycle == "proposed":
        if "status: proposed candidate" not in lower:
            failures.append("proposed lifecycle marker")
        if "provisionally-integrated" in lower or "status: provisionally integrated" in lower:
            failures.append("false integration marker")
    elif lifecycle == "integrated":
        if "status: provisionally integrated" not in lower:
            failures.append("integrated lifecycle marker")
        if "status: proposed candidate" in lower:
            failures.append("stale proposed lifecycle marker")
    else:
        fail(f"unknown expected lifecycle: {expected_lifecycle}")
    return failures


def validate_candidate(
    leaf: str,
    specification: str,
    coverage_text: str,
    *,
    expected_lifecycle: str = "proposed",
) -> None:
    frontmatter = parse_frontmatter(leaf)
    if frontmatter.get("name") != "typescript-language-profile":
        fail("candidate identity is invalid")
    clauses = parse_clauses(leaf, specification)
    coverage = parse_coverage(coverage_text)
    validate_navigation(coverage, clauses)
    if expected_lifecycle == "integrated":
        validate_coverage_lifecycle(coverage_text)
    failures = candidate_guard_failures(
        leaf, specification, expected_lifecycle=expected_lifecycle
    )
    if failures:
        fail("candidate guards failed: " + ", ".join(failures))
