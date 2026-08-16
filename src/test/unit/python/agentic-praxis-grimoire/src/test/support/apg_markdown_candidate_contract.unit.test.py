#!/usr/bin/env python3
"""Unit ownership for the APG66 Markdown replay support."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_markdown_candidate_contract import (  # noqa: E402
    ContractError,
    TARGETED_GUARD_MARKERS,
    load_fixture,
    parse_clauses,
    parse_coverage,
    scenario_support,
    targeted_guard_failures,
    targeted_guard_states,
    validate_navigation,
)
from apg_markdown_token_guard_contract import SEMANTIC_SIGNAL_ALIASES  # noqa: E402


FIXTURE = load_fixture(
    ROOT / "src/test/fixtures/apg66-markdown-language-profile-scenarios.json"
)
ROWS = {row["id"]: row for row in FIXTURE["rows"]}
LEAF = (ROOT / "skills/markdown-language-profile/SKILL.md").read_text()
SPECIFICATION = (ROOT / "docs/specs/markdown-language-profile.md").read_text()
COVERAGE_TEXT = (
    ROOT / "docs/specs/markdown-language-profile-scenario-coverage.md"
).read_text()
CLAUSES = parse_clauses(LEAF, SPECIFICATION)
COVERAGE = parse_coverage(COVERAGE_TEXT)

SOURCE_BOUNDARY_CASES = (
    "APG63-MD-013", "APG63-MD-017", "APG63-MD-018", "APG63-MD-019",
    "APG63-MD-020", "APG63-MD-021", "APG63-MD-022", "APG63-MD-024",
    "APG63-MD-025", "APG63-MD-026", "APG63-MD-027", "APG63-MD-029",
    "APG63-MD-030", "APG63-MD-031", "APG63-MD-032", "APG63-MD-033",
    "APG63-MD-034",
)
SIGNAL_CASES = (
    ("APG63-MD-017", "semantic", "raw-html-boundary"),
    ("APG63-MD-018", "structural", "policy-evasion"),
    ("APG63-MD-018", "semantic", "raw-html-boundary"),
    ("APG63-MD-030", "structural", "multiple-independent-audiences"),
    ("APG63-MD-030", "structural", "multiple-independent-purposes"),
    ("APG63-MD-031", "structural", "oversized-single-section"),
    ("APG63-MD-031", "structural", "reference-tutorial-mixing"),
    ("APG63-MD-032", "structural", "duplicated-normative-truth"),
    ("APG63-MD-032", "semantic", "normative-contradiction"),
    ("APG63-MD-033", "structural", "navigation-failure"),
    ("APG63-MD-034", "semantic", "normative-contradiction"),
)
ROLLBACK_CASES = (
    ("APG63-MD-007", "record-predecision-behavior"),
    ("APG63-MD-010", "record-collision-definitions"),
    ("APG63-MD-014", "record-reclassified-region"),
    ("APG63-MD-018", "record-moved-responsibility"),
    ("APG63-MD-022", "record-frontmatter-bytes"),
    ("APG63-MD-029", "regenerate-from-owner"),
    ("APG63-MD-030", "preserve-navigation-move-map"),
    ("APG63-MD-031", "record-extraction-map"),
)


def _replace_mapped_with_global_near_miss(scenario: str) -> dict[str, str]:
    clauses = dict(CLAUSES)
    originals = []
    for clause in COVERAGE[scenario]:
        originals.append(clauses[clause])
        clauses[clause] = "unrelated mapped clause"
    clauses["MARKDOWN-UNRELATED"] = "\n".join(originals)
    return clauses


def _replace_local_signal(
    scenario: str, signal: str, replacement: str
) -> dict[str, str]:
    clauses = dict(CLAUSES)
    variants = (signal, *SEMANTIC_SIGNAL_ALIASES.get(signal, ()))
    replaced = False
    for clause in COVERAGE[scenario]:
        for variant in variants:
            clauses[clause], count = re.subn(
                re.escape(variant), replacement, clauses[clause], flags=re.IGNORECASE
            )
            if count:
                replaced = True
    assert replaced
    return clauses


def test_current_candidate_has_truthful_navigation_and_targeted_guards() -> None:
    validate_navigation(FIXTURE["rows"], COVERAGE, CLAUSES)
    results = [scenario_support(row, COVERAGE, CLAUSES) for row in FIXTURE["rows"]]
    assert len(results) == 34
    assert all(result["missing"] == [] for result in results)
    assert all("expected_consequence" not in result for result in results)
    assert all(result["local_negative_guards"] == [] for result in results)
    assert all(result["local_conflicts"] == [] for result in results)
    assert all("local_observed_tokens" in result for result in results)
    assert all("local_positive_guards" in result for result in results)
    assert targeted_guard_failures(CLAUSES) == []


def test_fixture_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}\n', encoding="utf-8")
    with pytest.raises(ContractError, match="duplicate JSON key: schema_version"):
        load_fixture(path)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("owner", "parser-tool-owner"), ("selection", "route-to-owner"),
        ("response", "inspect-before-judgment"), ("route", "project-policy"),
        ("nonowners", ["html-owner"]),
        ("structural_signals", ["multiple-independent-audiences"]),
        ("semantic_signals", ["normative-contradiction"]),
    ),
)
def test_fixture_fields_are_never_copied_as_observed_consequences(
    field: str, replacement: object
) -> None:
    row = deepcopy(ROWS["APG63-MD-013"])
    row[field] = replacement
    baseline = scenario_support(ROWS["APG63-MD-013"], COVERAGE, CLAUSES)
    result = scenario_support(row, COVERAGE, CLAUSES)
    assert "expected_consequence" not in result
    assert result == baseline


@pytest.mark.parametrize(
    ("scenario", "clause", "replacement", "diagnostic"),
    (
        ("APG63-MD-013", "MARKDOWN-FENCE", "host-owner route-to-owner", "source-boundary-evidence"),
        ("APG63-MD-017", "MARKDOWN-RAW-HTML", "project-policy", "source-boundary-evidence"),
        ("APG63-MD-018", "MARKDOWN-RAW-HTML", "html-owner", "source-boundary-evidence"),
        ("APG63-MD-030", "MARKDOWN-STRUCTURAL-SIGNALS", "project-design", "structural-signal"),
    ),
)
def test_unrelated_global_tokens_do_not_satisfy_mapped_evidence(
    scenario: str, clause: str, replacement: str, diagnostic: str
) -> None:
    clauses = dict(CLAUSES)
    clauses[clause] = replacement
    clauses["MARKDOWN-UNRELATED"] = CLAUSES[clause]
    result = scenario_support(ROWS[scenario], COVERAGE, clauses)
    assert any(item.startswith(diagnostic) for item in result["missing"])


def test_unrelated_global_normative_token_does_not_satisfy_row_032() -> None:
    clauses = dict(CLAUSES)
    originals = []
    for clause in COVERAGE["APG63-MD-032"]:
        originals.append(clauses[clause])
        clauses[clause] = "project-policy stop-and-escalate"
    clauses["MARKDOWN-UNRELATED"] = "\n".join(originals)
    result = scenario_support(ROWS["APG63-MD-032"], COVERAGE, clauses)
    assert "semantic-signal:normative-contradiction" in result["missing"]


@pytest.mark.parametrize("scenario", SOURCE_BOUNDARY_CASES, ids=SOURCE_BOUNDARY_CASES)
def test_each_source_boundary_requires_mapped_local_evidence(scenario: str) -> None:
    result = scenario_support(
        ROWS[scenario], COVERAGE, _replace_mapped_with_global_near_miss(scenario)
    )
    expected = f"source-boundary-evidence:{ROWS[scenario]['source_boundary_class']}"
    assert expected in result["missing"]


@pytest.mark.parametrize(
    ("scenario", "kind", "signal"),
    SIGNAL_CASES,
    ids=[f"{scenario}-{signal}" for scenario, _, signal in SIGNAL_CASES],
)
def test_each_local_signal_requires_mapped_local_evidence(
    scenario: str, kind: str, signal: str
) -> None:
    result = scenario_support(
        ROWS[scenario], COVERAGE, _replace_mapped_with_global_near_miss(scenario)
    )
    assert f"{kind}-signal:{signal}" in result["missing"]


@pytest.mark.parametrize(
    ("scenario", "rollback"),
    ROLLBACK_CASES,
    ids=[f"{scenario}-{rollback}" for scenario, rollback in ROLLBACK_CASES],
)
def test_each_non_none_rollback_requires_mapped_local_evidence(
    scenario: str, rollback: str
) -> None:
    result = scenario_support(
        ROWS[scenario], COVERAGE, _replace_mapped_with_global_near_miss(scenario)
    )
    assert f"rollback:{rollback}" in result["missing"]


@pytest.mark.parametrize(
    "contradiction",
    (
        "The markdown-language-profile is a non-owner for this boundary.",
        "This boundary is not owned by markdown-language-profile.",
    ),
)
def test_mapped_expected_owner_cannot_also_be_a_nonowner(
    contradiction: str,
) -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-FENCE"] += f"\n{contradiction}"
    result = scenario_support(ROWS["APG63-MD-013"], COVERAGE, clauses)
    assert (
        "owner-contradicted-as-nonowner:markdown-language-profile"
        in result["missing"]
    )


@pytest.mark.parametrize(
    "rule", ("Rollback is always required.", "Rollback applies unconditionally to every change.")
)
def test_no_rollback_row_rejects_mapped_unconditional_rule(
    rule: str,
) -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-STRUCTURAL-SIGNALS"] += f"\n{rule}"
    result = scenario_support(ROWS["APG63-MD-033"], COVERAGE, clauses)
    assert "rollback:unexpected-unconditional" in result["missing"]


@pytest.mark.parametrize(
    "rule",
    (
        "Every change requires rollback.",
        "All changes require rollback.",
        "Rollback is mandatory for each change.",
        "Each decision must include a rollback.",
        "Each change must have a rollback.",
        "Rollback is required for every change.",
    ),
)
def test_no_rollback_row_rejects_subject_first_obligations(rule: str) -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-STRUCTURAL-SIGNALS"] += f"\n{rule}"
    result = scenario_support(ROWS["APG63-MD-033"], COVERAGE, clauses)
    assert "rollback:unexpected-unconditional" in result["missing"]


@pytest.mark.parametrize(
    "rule",
    (
        "Rollback is not required.",
        "No rollback is required.",
        "Not every change requires rollback.",
        "Rollback applies only where material.",
    ),
)
def test_no_rollback_row_allows_explicit_negatives(rule: str) -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-STRUCTURAL-SIGNALS"] += f"\n{rule}"
    result = scenario_support(ROWS["APG63-MD-033"], COVERAGE, clauses)
    assert "rollback:unexpected-unconditional" not in result["missing"]


def test_no_rollback_row_rejects_positive_negative_conflict() -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-STRUCTURAL-SIGNALS"] += (
        "\nRollback is not required. Every change requires rollback."
    )
    result = scenario_support(ROWS["APG63-MD-033"], COVERAGE, clauses)
    assert "rollback:unexpected-unconditional" in result["missing"]


def test_no_rollback_row_ignores_other_artifact_obligation() -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-UNRELATED"] = (
        "The release tool requires rollback for every deployment."
    )
    result = scenario_support(ROWS["APG63-MD-033"], COVERAGE, clauses)
    assert "rollback:unexpected-unconditional" not in result["missing"]


@pytest.mark.parametrize("guard", tuple(TARGETED_GUARD_MARKERS))
def test_each_targeted_guard_rejects_global_only_near_miss(guard: str) -> None:
    clause, _ = TARGETED_GUARD_MARKERS[guard]
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-UNRELATED"] = clauses[clause]
    clauses[clause] = "related topic without the targeted contract"
    assert guard in targeted_guard_failures(clauses)


@pytest.mark.parametrize("guard", tuple(TARGETED_GUARD_MARKERS))
@pytest.mark.parametrize(
    "prefix",
    (
        "Do not claim ",
        "The following rejected phrase must not be used: ",
    ),
)
def test_each_targeted_guard_rejects_local_contradiction(
    guard: str, prefix: str
) -> None:
    clause, requirement = TARGETED_GUARD_MARKERS[guard]
    markers = (requirement,) if isinstance(requirement, str) else requirement
    clauses = dict(CLAUSES)
    clauses[clause] += "\n" + prefix + "; ".join(markers) + "."
    assert guard in targeted_guard_failures(clauses)


@pytest.mark.parametrize("guard", tuple(TARGETED_GUARD_MARKERS))
@pytest.mark.parametrize(
    "template",
    (
        'The rejected quotation is: "{markers}."',
        "Suppose {markers}.",
        "‘{markers}.’",
        "“{markers}.”",
        "«{markers}.»",
        "Assume {markers}.",
        "If {markers}, then continue.",
        "Were {markers} true, it would matter.",
        "Consider whether {markers}.",
    ),
)
def test_each_targeted_guard_rejects_quoted_and_hypothetical_local_forms(
    guard: str, template: str
) -> None:
    clause, requirement = TARGETED_GUARD_MARKERS[guard]
    markers = (requirement,) if isinstance(requirement, str) else requirement
    clauses = dict(CLAUSES)
    clauses[clause] += "\n" + template.format(markers="; ".join(markers))
    assert guard in targeted_guard_failures(clauses)


@pytest.mark.parametrize("guard", tuple(TARGETED_GUARD_MARKERS))
def test_each_targeted_guard_rejects_pure_direct_negative(guard: str) -> None:
    clause, requirement = TARGETED_GUARD_MARKERS[guard]
    markers = (requirement,) if isinstance(requirement, str) else requirement
    clauses = dict(CLAUSES)
    clauses[clause] = ". ".join(f"Do not claim {marker}" for marker in markers) + "."
    assert targeted_guard_states(clauses)[guard] == "negative"
    assert guard in targeted_guard_failures(clauses)


@pytest.mark.parametrize("guard", tuple(TARGETED_GUARD_MARKERS))
def test_each_targeted_guard_rejects_mapped_larger_token_near_miss(
    guard: str,
) -> None:
    clause, requirement = TARGETED_GUARD_MARKERS[guard]
    markers = (requirement,) if isinstance(requirement, str) else requirement
    clauses = dict(CLAUSES)
    clauses[clause] = "; ".join(f"{marker}-extra" for marker in markers)
    assert targeted_guard_states(clauses)[guard] == "absent"
    assert guard in targeted_guard_failures(clauses)


def test_fence_tuple_rejects_exact_audit_do_not_claim_variant() -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-FENCE"] += (
        "\nDo not claim the primary owner is markdown-language-profile, selection "
        "is embedded-route, response is proceed-routine, and route is "
        "embedded-language-owner."
    )
    assert "fence-owner-and-embedded-route" in targeted_guard_failures(clauses)


@pytest.mark.parametrize(
    ("scenario", "kind", "signal"),
    SIGNAL_CASES,
    ids=[f"{scenario}-{signal}" for scenario, _, signal in SIGNAL_CASES],
)
@pytest.mark.parametrize(
    "negative",
    (
        "{signal} does not apply.",
        "{signal} is absent.",
        "{signal} did not fire.",
        "{signal} is not present.",
        "{signal} is irrelevant.",
    ),
)
def test_each_local_signal_rejects_explicit_negation(
    scenario: str, kind: str, signal: str, negative: str
) -> None:
    clauses = dict(CLAUSES)
    clauses[COVERAGE[scenario][0]] += f"\n{negative.format(signal=signal)}"
    result = scenario_support(ROWS[scenario], COVERAGE, clauses)
    assert f"{kind}-signal:{signal}" in result["missing"]
    assert f"{kind}:{signal}" in result["local_conflicts"]
    assert signal not in result["local_observed_tokens"]


@pytest.mark.parametrize(
    ("scenario", "kind", "signal"),
    SIGNAL_CASES,
    ids=[f"{scenario}-{signal}" for scenario, _, signal in SIGNAL_CASES],
)
def test_each_local_signal_preserves_unrelated_negative(
    scenario: str, kind: str, signal: str
) -> None:
    clauses = dict(CLAUSES)
    clauses[COVERAGE[scenario][0]] += "\nanother-signal does not apply."
    result = scenario_support(ROWS[scenario], COVERAGE, clauses)
    assert f"{kind}-signal:{signal}" not in result["missing"]


@pytest.mark.parametrize(
    ("scenario", "kind", "signal"),
    SIGNAL_CASES,
    ids=[f"{scenario}-{signal}" for scenario, _, signal in SIGNAL_CASES],
)
def test_each_local_signal_rejects_pure_negative(
    scenario: str, kind: str, signal: str
) -> None:
    clauses = _replace_local_signal(scenario, signal, "removed-signal-evidence")
    clauses[COVERAGE[scenario][0]] += f"\n{signal} is absent."
    result = scenario_support(ROWS[scenario], COVERAGE, clauses)
    assert f"{kind}-signal:{signal}" in result["missing"]
    assert f"{kind}:{signal}" in result["local_negative_guards"]
    assert signal not in result["local_observed_tokens"]


@pytest.mark.parametrize(
    ("scenario", "kind", "signal"),
    SIGNAL_CASES,
    ids=[f"{scenario}-{signal}" for scenario, _, signal in SIGNAL_CASES],
)
def test_each_local_signal_rejects_larger_token_near_miss(
    scenario: str, kind: str, signal: str
) -> None:
    clauses = _replace_local_signal(scenario, signal, f"{signal}-extra")
    result = scenario_support(ROWS[scenario], COVERAGE, clauses)
    assert f"{kind}-signal:{signal}" in result["missing"]
    assert signal not in result["local_observed_tokens"]


def test_actual_parser_must_remain_first() -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-EFFECTIVE-GRAMMAR"] = (
        "1. CommonMark 0.31.2\n2. the actual repository renderer or parser\n"
        "3. GFM 0.29\n4. implementation-specific behavior\n"
        "never presented as one formally specified composite dialect"
    )
    assert "actual-parser-first-hierarchy" in targeted_guard_failures(clauses)


def test_navigation_only_orange_rejects_unqualified_rollback() -> None:
    clauses = dict(CLAUSES)
    clauses["MARKDOWN-VALIDATION"] = clauses["MARKDOWN-VALIDATION"].replace(
        "rollback\nwhere material", "rollback always"
    )
    assert "navigation-only-orange-no-material-rollback" in targeted_guard_failures(clauses)


@pytest.mark.parametrize(
    ("guard", "clause", "old", "new"),
    (
        (
            "host-fragment-embedded-route",
            "MARKDOWN-EMBEDDED-ROUTE",
            "judgment is limited\nto the identified fragment",
            "Markdown reclassifies the entire host file",
        ),
        (
            "generated-hand-edit-route",
            "MARKDOWN-GENERATED",
            "`route-to-owner` to\n`parser-tool-owner`",
            "`selected` with\n`not-applicable`",
        ),
        (
            "normative-contradiction-stop",
            "MARKDOWN-SEMANTIC-RISK",
            "dependent work stops",
            "dependent work proceeds routinely",
        ),
    ),
)
def test_targeted_guards_reject_semantic_near_misses(
    guard: str, clause: str, old: str, new: str
) -> None:
    clauses = dict(CLAUSES)
    assert old in clauses[clause]
    clauses[clause] = clauses[clause].replace(old, new)
    assert guard in targeted_guard_failures(clauses)


@pytest.mark.parametrize(
    "rule", ("A 500 line warning band applies.", "A 500-line warning band applies.")
)
def test_arbitrary_numeric_band_is_rejected(rule: str) -> None:
    numeric = dict(CLAUSES)
    numeric["MARKDOWN-STRUCTURAL-POLICY"] += f"\n{rule}"
    assert "no-numeric-bands" in targeted_guard_failures(numeric)


@pytest.mark.parametrize(
    "rule",
    (
        "Map Git, report, catalog, release, and projection operations into "
        "candidate semantics; delete current candidate surfaces when review rejects them.",
        "A Git review report decides whether the candidate remains in the catalog and "
        "release projection.",
    ),
)
def test_process_invariant_prose_without_row_id_is_rejected(rule: str) -> None:
    process = dict(CLAUSES)
    process["MARKDOWN-STOP"] += f"\n{rule}"
    assert "no-process-invariant-leakage" in targeted_guard_failures(process)


def test_clause_and_coverage_mutations_are_bounded() -> None:
    with pytest.raises(ContractError, match="duplicate clause ID"):
        parse_clauses(
            "<!-- APG-CLAUSE: MARKDOWN-TEST -->one\n"
            "<!-- APG-CLAUSE: MARKDOWN-TEST -->two"
        )
    with pytest.raises(ContractError, match="duplicate coverage scenario"):
        parse_coverage(
            "| APG63-MD-001 | x | `MARKDOWN-TEST` |\n"
            "| APG63-MD-001 | x | `MARKDOWN-TEST` |\n"
        )


@pytest.mark.parametrize("kind", ("unknown", "dead", "missing", "process"))
def test_navigation_closure_mutations_are_rejected(kind: str) -> None:
    coverage = dict(COVERAGE)
    clauses = dict(CLAUSES)
    if kind == "unknown":
        coverage["APG63-MD-001"] = ("MARKDOWN-UNKNOWN-CLAUSE",)
    elif kind == "dead":
        clauses["MARKDOWN-DEAD"] = "unused"
    elif kind == "missing":
        coverage.pop("APG63-MD-001")
    else:
        coverage["APG63-MD-035"] = coverage.pop("APG63-MD-001")
    with pytest.raises(ContractError):
        validate_navigation(FIXTURE["rows"], coverage, clauses)
