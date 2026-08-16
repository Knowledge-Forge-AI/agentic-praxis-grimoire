#!/usr/bin/env python3
"""Focused APG47 provenance-policy contracts."""

import json
import re

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
POLICY = ROOT / "docs/provenance.md"
FIXTURE = ROOT / "src/test/fixtures/apg47-accepted-evidence-guidance-cases.json"


def section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + 3)
    return text[start:] if end < 0 else text[start:end]


def test_claim_relative_authority_is_normative_only_in_provenance() -> None:
    policy = POLICY.read_text()
    authority = section(policy, "Claim-relative source authority")
    text = " ".join(authority.split())
    assert policy.index("## Claim-relative source authority") < policy.index(
        "## Material access limitations"
    ) < policy.index("## Public provenance template")
    for phrase in (
        "how directly its inspectable basis bears on the exact claim",
        "first-party source may settle its own formal record",
        "does not automatically control conclusions about impact, reliability, "
        "safety, quality",
        "one corroborating lineage, not independent confirmation",
        "derivative summary may still aid discovery",
        "no universal source tiers and no source-count minimum",
        "searching for the opposing claim",
    ):
        assert phrase in text
    assert "recency" not in authority.casefold()

    duplicated_policy = (
        "one corroborating lineage",
        "universal source tiers",
        "source-count minimum",
    )
    for skill in (ROOT / "skills").glob("**/SKILL.md"):
        skill_text = skill.read_text()
        for phrase in duplicated_policy:
            assert phrase not in skill_text


def test_material_access_limitations_remain_optional_private_prose() -> None:
    policy = POLICY.read_text()
    access = section(policy, "Material access limitations")
    assert policy.index("## Material access limitations") < policy.index(
        "## Public provenance template"
    )
    normalized = " ".join(access.split())
    for phrase in (
        "could materially affect a conclusion",
        "how that limitation constrained validation, confidence, or the terminal "
        "claim",
        "without exposing protected content, credentials, private paths, machine "
        "topology, or confidential source details",
        "Omit the note when access was complete or when the limitation was "
        "immaterial",
        "adds no required field, key, schema, or validator",
        "existing free-prose provenance records remain valid",
    ):
        assert phrase in normalized
    assert "|" not in access
    assert "```" not in access
    assert not re.search(r"(?m)^\s*(access|limitation)[a-z_]*\s*:", access)


def test_apg47_fixture_maps_only_accepted_provenance_recommendations() -> None:
    document = json.loads(FIXTURE.read_text())
    rows = {row["id"]: row for row in document["recommendations"]}
    assert set(rows) == {"REC-01", "REC-02", "REC-03", "REC-04"}
    assert rows["REC-03"]["owner"] == "docs/provenance.md"
    assert rows["REC-04"]["owner"] == "docs/provenance.md"
    assert rows["REC-03"]["supporting"] == [
        "S08",
        "S09",
        "S10",
        "S11",
        "S17",
        "S18",
        "S19",
        "S20",
        "S24",
        "S25",
        "S26",
        "S28",
    ]
    assert rows["REC-03"]["adverse"] == ["S01", "S22", "S34"]
    assert rows["REC-04"]["supporting"] == ["S12", "S13", "S30"]
    assert rows["REC-04"]["adverse"] == ["S01", "S22", "S36", "S39"]
    assert rows["REC-03"]["contracts"] == [
        "Authority is relative to the exact claim and inspectable basis.",
        "Formal first-party records do not settle interested interpretations "
        "automatically.",
        "Common-origin restatements remain one lineage and derivative summaries "
        "may aid discovery.",
        "Contested claims may require counter-search and independently produced "
        "evidence.",
        "Corroboration remains claim- and project-owned without universal tiers, "
        "counts, or recency ceremony.",
    ]
    assert rows["REC-04"]["contracts"] == [
        "A material access boundary and its effect on the conclusion are recorded "
        "in prose.",
        "Complete or immaterial access produces no additional note.",
        "Protected details remain undisclosed.",
        "No required field, pseudo-schema, ledger, or validator is introduced.",
    ]
