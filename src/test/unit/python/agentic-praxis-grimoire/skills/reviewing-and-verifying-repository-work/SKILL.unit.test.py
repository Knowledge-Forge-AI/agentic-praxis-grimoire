#!/usr/bin/env python3
"""Focused review-skill contracts through APG47."""

import json

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
SKILL = (
    REPOSITORY_ROOT
    / "skills/reviewing-and-verifying-repository-work/SKILL.md"
)
FIXTURE = (
    REPOSITORY_ROOT
    / "src/test/fixtures/apg47-accepted-evidence-guidance-cases.json"
)
PROJECTION = (
    REPOSITORY_ROOT
    / ".agents/skills/reviewing-and-verifying-repository-work"
)

SEMANTIC_CASES = (
    (
        "unsupported-aesthetic-preference",
        ("Unsupported preference or taste is advice, not a required finding",),
    ),
    (
        "policy-grounded-evaluative-finding",
        (
            "judgment or interpretation may be a finding",
            "repository policy, an accepted contract",
        ),
    ),
    (
        "observable-structural-finding",
        ("observable structure, demonstrated behavior",),
    ),
    (
        "named-safety-or-operational-risk",
        ("a named risk supports that disposition",),
    ),
    (
        "weak-counterevidence",
        (
            "relevance to the exact claim",
            "directness of its inspectable basis",
            "evidentiary lineage is shared or independent",
        ),
    ),
    (
        "strong-counterevidence",
        (
            "method or reliability when material",
            "strength and scope",
            "may support a finding",
        ),
    ),
    (
        "mixed-counterevidence",
        (
            "an unresolved disposition, a narrower claim, a request for "
            "additional evidence, or no change",
        ),
    ),
    (
        "routine-established-claim",
        (
            "claim already established by fresh resulting-state evidence needs "
            "no additional evidence-direction statement",
        ),
    ),
)


def normalized_skill() -> str:
    return " ".join(SKILL.read_text().split())


def test_review_skill_checks_useful_tests_honest_coverage_and_reports() -> None:
    text = normalized_skill()
    for phrase in (
        "useful observable behavior",
        "exact coverage arithmetic",
        "complete maintained-source inventory",
        "exclusions have an explicit owner and rationale",
        "unit replacements do not erase the subject behavior",
        "integration claims exercise the real boundary they name",
        "A deliberately mocked unsafe external service remains a unit or "
        "bounded-adapter claim",
        "worker and subprocess completeness when material",
        "Broader test gates require a recorded justification",
        "deliberately unrun comprehensive suites",
        "Git-diff evidence for a dirty stopped result",
        "associated operational evidence",
    ):
        assert phrase in text


@pytest.mark.parametrize(
    ("case_id", "required_phrases"),
    SEMANTIC_CASES,
    ids=[case_id for case_id, _ in SEMANTIC_CASES],
)
def test_apg47_semantic_case(
    case_id: str, required_phrases: tuple[str, ...]
) -> None:
    text = normalized_skill()
    assert case_id
    for phrase in required_phrases:
        assert phrase in text


def test_material_claim_dispositions_are_complete_and_non_overbroad() -> None:
    text = normalized_skill()
    for phrase in (
        "Treat a forecast as a forecast rather than an established current fact",
        "narrow the assertion, defer it, or state the limitation",
        "unstated material inference",
        "When evidence does not establish a material claim",
        "does not automatically refute the claim, create a finding, or outweigh "
        "stronger evidence",
    ):
        assert phrase in text
    assert (
        "Evidence against a claim justifies a finding or an unresolved disposition"
        not in text
    )


def test_material_claim_guidance_remains_proportional() -> None:
    text = normalized_skill()
    for phrase in (
        "not a claim ledger, fixed taxonomy, or classification step added to "
        "routine review",
        "claim already established by fresh resulting-state evidence needs no "
        "additional evidence-direction statement",
    ):
        assert phrase in text


def test_evidence_directions_remain_distinct_and_scoped() -> None:
    text = normalized_skill()
    for phrase in (
        "no relevant evidence within the inspected scope",
        "relevant but inconclusive evidence",
        "evidence that weighs against the claim",
        "Name the inspected scope when reporting absence",
        "do not report missing support as refutation",
    ):
        assert phrase in text


def test_implied_completion_requires_its_own_evidence() -> None:
    text = normalized_skill()
    for phrase in (
        "unstated material inference",
        "state that inference as its own claim",
        "require evidence matching it",
    ):
        assert phrase in text


def test_debugging_procedure_is_not_duplicated() -> None:
    section = SKILL.read_text().split(
        "### Material claims and evidence direction", maxsplit=1
    )[1].split("### Test, coverage, and report review", maxsplit=1)[0]
    for debugging_procedure in (
        "root cause",
        "list explicit hypotheses",
        "test one variable at a time",
        "reproduce the symptom",
    ):
        assert debugging_procedure not in section


def test_review_bundle_owner_projection_and_rollback_boundary() -> None:
    text = SKILL.read_text()
    document = json.loads(FIXTURE.read_text())
    rows = {row["id"]: row for row in document["recommendations"]}
    before, remainder = text.split(
        "### Material claims and evidence direction", maxsplit=1
    )
    material_claims, after = remainder.split(
        "### Test, coverage, and report review", maxsplit=1
    )
    assert rows["REC-01"]["owner"] == SKILL.relative_to(REPOSITORY_ROOT).as_posix()
    assert rows["REC-02"]["owner"] == SKILL.relative_to(REPOSITORY_ROOT).as_posix()
    assert text.count("### Material claims and evidence direction") == 1
    assert before.rstrip().endswith(
        "A no-finding review does not create a reason to modify the artifact."
    )
    assert "unstated material inference" in material_claims
    assert after.lstrip().startswith(
        "Verify that tests assert useful observable behavior"
    )
    assert PROJECTION.is_symlink()
    assert PROJECTION.readlink().as_posix() == (
        "../../skills/reviewing-and-verifying-repository-work"
    )
    assert (PROJECTION / "SKILL.md").resolve() == SKILL


def test_apg47_fixture_maps_only_accepted_review_recommendations() -> None:
    document = json.loads(FIXTURE.read_text())
    rows = {row["id"]: row for row in document["recommendations"]}
    assert document["schema_version"] == 1
    assert document["source_phase"] == "APG47"
    assert rows["REC-01"]["supporting"] == [
        "S02",
        "S04",
        "S05",
        "S06",
        "S07",
        "S17",
    ]
    assert rows["REC-01"]["adverse"] == ["S03", "S27", "S34", "S39"]
    assert rows["REC-02"]["supporting"] == ["S14", "S15", "S32"]
    assert rows["REC-02"]["adverse"] == ["S27"]
    assert rows["REC-01"]["contracts"] == [
        "Material implied completion is stated and evidenced.",
        "Unsupported taste is advice while grounded evaluation may remain a "
        "finding.",
        "Forecasts and undefined checks are not presented as established current "
        "facts.",
        "Routine or already established claims gain no classification ceremony.",
    ]
    assert rows["REC-02"]["contracts"] == [
        "Scoped absence, inconclusive evidence, and evidence weighing against a "
        "claim remain distinct.",
        "Countervailing evidence is evaluated before its effect is dispositioned.",
        "Established claims gain no additional report state.",
    ]
