#!/usr/bin/env python3
"""Mutation checks for the maintained CSS target-first fixture contract."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_css_profile_fixture_contract import (  # noqa: E402
    APG79C_KNOWN_DEBT_SHA256,
    FixtureError,
    KNOWN_DEBT_ENTRY_SHA256,
    load_known_debt,
    load_known_debt_summary,
    load_manifest,
    validate_css_known_debt,
    validate_known_debt_markdown,
    validate_known_debt_profile_deactivation,
    validate_known_debt_summary,
    validate_language_profile_known_debt,
    validate_manifest,
)


FIXTURE = ROOT / "src/test/fixtures/apg76-css-target-first"
MANIFEST = load_manifest(FIXTURE / "fixture-manifest.json")
KNOWN_DEBT = ROOT / "docs/governance/language-profile-known-debt.json"
KNOWN_DEBT_MARKDOWN = ROOT / "docs/governance/language-profile-known-debt.md"
KNOWN_DEBT_SUMMARY = (
    ROOT / "private/evaluations/apg79c/javascript-qualification-debt-register.json"
)
PRIVATE_KNOWN_DEBT_SUMMARY = pytest.mark.skipif(
    not KNOWN_DEBT_SUMMARY.is_file(),
    reason="publication-excluded known-debt summary is absent",
)


def test_manifest_shape_paths_and_current_boundaries_are_closed() -> None:
    assert len(MANIFEST["cases"]) == 14
    assert len(MANIFEST["source_bindings"]["modules"]) == 21
    assert "css-properties-values-api-1" in {
        source["shortname"] for source in MANIFEST["source_bindings"]["modules"]
    }


def test_duplicate_keys_relative_paths_and_source_count_drift_fail(tmp_path: Path) -> None:
    duplicate = '{"fixture":"a","fixture":"b"}'
    path = tmp_path / "duplicate.json"
    path.write_text(duplicate, encoding="utf-8")
    with pytest.raises(FixtureError, match="duplicate JSON key"):
        load_manifest(path)

    traversal = deepcopy(MANIFEST)
    traversal["cases"][0]["paths"] = ["../outside.css"]
    with pytest.raises(FixtureError, match="unsafe path"):
        validate_manifest(traversal, FIXTURE)

    drift = deepcopy(MANIFEST)
    drift["source_bindings"]["modules"].pop()
    with pytest.raises(FixtureError, match="source module count drift"):
        validate_manifest(drift, FIXTURE)


def test_role_state_and_present_required_evidence_contradictions_fail() -> None:
    role = deepcopy(MANIFEST)
    role["cases"][0]["parser_role_state"] = "transitive"
    with pytest.raises(FixtureError, match="unknown role state"):
        validate_manifest(role, FIXTURE)

    overlap = deepcopy(MANIFEST)
    overlap["cases"][0]["required_evidence"] = [
        overlap["cases"][0]["present_evidence"][0]
    ]
    with pytest.raises(FixtureError, match="copies present evidence"):
        validate_manifest(overlap, FIXTURE)


def test_current_decision_and_lifecycle_mutations_fail() -> None:
    proposed = deepcopy(MANIFEST)
    proposed["authority"]["adr_status"] = "Proposed"
    with pytest.raises(FixtureError, match="current decision authority"):
        validate_manifest(proposed, FIXTURE)

    unintegrated = deepcopy(MANIFEST)
    unintegrated["lifecycle"]["integrated"] = False
    with pytest.raises(FixtureError, match="current lifecycle"):
        validate_manifest(unintegrated, FIXTURE)


def test_current_known_debt_is_exact_and_human_accepted() -> None:
    value = load_known_debt(KNOWN_DEBT)
    assert validate_language_profile_known_debt(value) == {
        "debts": 10,
        "css": 5,
        "javascript": 5,
        "low": 1,
        "medium": 9,
    }
    assert validate_css_known_debt(value) == {
        "debts": 5,
        "low": 1,
        "medium": 4,
    }
    validate_known_debt_markdown(KNOWN_DEBT_MARKDOWN.read_text(encoding="utf-8"), value)
    assert {
        debt["debt_id"]: hashlib.sha256(
            json.dumps(
                debt, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
        ).hexdigest()
        for debt in value["debts"]
    } == KNOWN_DEBT_ENTRY_SHA256


@pytest.mark.parametrize(
    ("old", "new"),
    (
        ("supporting CommonJS qualification machinery only", "WRONG SEMANTIC OWNER"),
        (
            "Does not block under the explicit APG79C decision",
            "Blocks provisional integration",
        ),
        (
            "| `JS-QD-001` | Medium | supporting CommonJS qualification machinery only | Does not block under the explicit APG79C decision | Blocks until repaired or separately re-evaluated |",
            "| `JS-QD-001` | Medium | supporting CommonJS qualification machinery only | Does not block under the explicit APG79C decision | Does not block stable maturity |",
        ),
    ),
)
def test_known_debt_markdown_exact_row_mutations_fail(old: str, new: str) -> None:
    value = load_known_debt(KNOWN_DEBT)
    text = KNOWN_DEBT_MARKDOWN.read_text(encoding="utf-8")
    assert old in text
    with pytest.raises(FixtureError, match="rows are absent"):
        validate_known_debt_markdown(text.replace(old, new, 1), value)


@pytest.mark.parametrize(
    "extra_row",
    (
        "| `JS-QD-001` | High | WRONG SEMANTIC OWNER | Blocks provisional integration | Does not block stable maturity |",
        "| `JS-QD-001` | Medium | supporting CommonJS qualification machinery only | Does not block under the explicit APG79C decision | Blocks until repaired or separately re-evaluated |",
    ),
)
def test_known_debt_markdown_extra_or_duplicate_rows_fail(extra_row: str) -> None:
    value = load_known_debt(KNOWN_DEBT)
    text = KNOWN_DEBT_MARKDOWN.read_text(encoding="utf-8") + extra_row + "\n"
    with pytest.raises(FixtureError, match="extra, duplicated"):
        validate_known_debt_markdown(text, value)


@pytest.mark.parametrize(
    "mutation",
    (
        "duplicate-id",
        "missing-field",
        "extra-field",
        "wrong-type",
        "wrong-status",
        "wrong-id-set",
    ),
)
def test_known_debt_schema_and_exact_set_fail_closed(mutation: str) -> None:
    value = deepcopy(load_known_debt(KNOWN_DEBT))
    if mutation == "duplicate-id":
        value["debts"][1]["debt_id"] = value["debts"][0]["debt_id"]
    elif mutation == "missing-field":
        del value["debts"][0]["repair_condition"]
    elif mutation == "extra-field":
        value["debts"][0]["unexpected"] = "value"
    elif mutation == "wrong-type":
        value["debts"][0]["blocks_provisional"] = 0
    elif mutation == "wrong-status":
        value["debts"][0]["status"] = "pending"
    elif mutation == "wrong-id-set":
        value["debts"][4]["debt_id"] = "CSS-QD-006"
    with pytest.raises(FixtureError):
        validate_css_known_debt(value)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing-javascript-debt",
        "extra-javascript-debt",
        "wrong-javascript-severity",
        "critical-high-acceptance",
        "blocks-provisional",
        "missing-blocks-provisional",
        "blocks-stable-false",
        "missing-safety-basis",
        "missing-workaround",
        "missing-repair-condition",
        "missing-refresh-condition",
        "wrong-profile",
        "wrong-phase",
        "false-proxy-repaired",
        "report-bytes-unknown",
        "missing-report-tooling-refresh",
        "css-entry-drift",
    ),
)
def test_javascript_acceptance_and_css_preservation_fail_closed(mutation: str) -> None:
    value = deepcopy(load_known_debt(KNOWN_DEBT))
    javascript = value["debts"][-1]
    if mutation == "missing-javascript-debt":
        value["debts"].pop()
    elif mutation == "extra-javascript-debt":
        extra = deepcopy(value["debts"][-1])
        extra["debt_id"] = "JS-QD-005"
        value["debts"].append(extra)
    elif mutation == "wrong-javascript-severity":
        javascript["severity"] = "Low"
    elif mutation == "critical-high-acceptance":
        javascript["severity"] = "High"
    elif mutation == "blocks-provisional":
        javascript["blocks_provisional"] = True
    elif mutation == "missing-blocks-provisional":
        del javascript["blocks_provisional"]
    elif mutation == "blocks-stable-false":
        javascript["blocks_stable"] = False
    elif mutation == "missing-safety-basis":
        javascript["why_integration_remains_safe"] = ""
    elif mutation == "missing-workaround":
        javascript["workaround_or_stop_behavior"] = ""
    elif mutation == "missing-repair-condition":
        javascript["repair_condition"] = ""
    elif mutation == "missing-refresh-condition":
        javascript["refresh_condition"] = ""
    elif mutation == "wrong-profile":
        javascript["profile"] = "node-runtime-profile"
    elif mutation == "wrong-phase":
        javascript["accepted_phase"] = "APG79B"
    elif mutation == "false-proxy-repaired":
        javascript["known_consequence"] = "The maintained false proxy is repaired."
    elif mutation == "report-bytes-unknown":
        javascript["why_integration_remains_safe"] = (
            "The APG79B managed-report bytes are unknown or altered."
        )
    elif mutation == "missing-report-tooling-refresh":
        javascript["refresh_condition"] = "Only the source-role record changes."
    elif mutation == "css-entry-drift":
        value["debts"][0]["known_consequence"] += " Drift."
    with pytest.raises(FixtureError):
        validate_language_profile_known_debt(value)


@PRIVATE_KNOWN_DEBT_SUMMARY
def test_profile_rollbacks_and_public_private_summary_are_independent() -> None:
    value = load_known_debt(KNOWN_DEBT)
    css = [debt for debt in value["debts"] if debt["profile"] == "css-language-profile"]
    javascript = [
        debt for debt in value["debts"] if debt["profile"] == "javascript-language-profile"
    ]
    assert [debt["debt_id"] for debt in css] == [f"CSS-QD-{index:03d}" for index in range(1, 6)]
    assert [debt["debt_id"] for debt in javascript] == [f"JS-QD-{index:03d}" for index in range(1, 6)]
    assert len(css) == 5 and len(javascript) == 5
    validate_known_debt_profile_deactivation(
        value, "javascript-language-profile", css
    )
    validate_known_debt_profile_deactivation(
        value, "css-language-profile", javascript
    )
    with pytest.raises(FixtureError, match="another profile"):
        validate_known_debt_profile_deactivation(
            value, "javascript-language-profile", css[1:]
        )
    changed_css = deepcopy(css)
    changed_css[0]["known_consequence"] += " Drift."
    with pytest.raises(FixtureError, match="another profile"):
        validate_known_debt_profile_deactivation(
            value, "javascript-language-profile", changed_css
        )

    summary = load_known_debt_summary(
        KNOWN_DEBT_SUMMARY, value, APG79C_KNOWN_DEBT_SHA256
    )
    wrong = deepcopy(summary)
    wrong["entry_sha256"]["JS-QD-004"] = "0" * 64
    with pytest.raises(FixtureError, match="public/private"):
        validate_known_debt_summary(wrong, value, APG79C_KNOWN_DEBT_SHA256)


@PRIVATE_KNOWN_DEBT_SUMMARY
def test_private_known_debt_summary_file_mutations_fail(tmp_path: Path) -> None:
    value = load_known_debt(KNOWN_DEBT)
    original = KNOWN_DEBT_SUMMARY.read_text(encoding="utf-8")

    wrong_count = tmp_path / "wrong-count.json"
    wrong_count.write_text(
        original.replace('"unaccepted_findings":1', '"unaccepted_findings":0'),
        encoding="utf-8",
    )
    with pytest.raises(FixtureError, match="public/private"):
        load_known_debt_summary(wrong_count, value, APG79C_KNOWN_DEBT_SHA256)

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        original.replace(
            '"unaccepted_findings":1',
            '"unaccepted_findings":1,"unaccepted_findings":1',
        ),
        encoding="utf-8",
    )
    with pytest.raises(FixtureError, match="duplicate JSON key"):
        load_known_debt_summary(duplicate, value, APG79C_KNOWN_DEBT_SHA256)
