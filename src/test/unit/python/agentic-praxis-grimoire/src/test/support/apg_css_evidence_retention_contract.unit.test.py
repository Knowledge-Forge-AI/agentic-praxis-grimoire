#!/usr/bin/env python3
"""Mutation checks for the APG77C compact CSS evidence contract."""

from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path
import sys
import zlib

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_css_evidence_retention_contract import (  # noqa: E402
    EvidenceContractError,
    FALSE_APG77B_DIFF_DIGEST,
    PRIVATE_BINDING_PREFIX,
    PRIVATE_BINDING_SUFFIX,
    canonical_json,
    load_json,
    private_source_binding_paths,
    unapproved_target_overlaps,
    validate_declared_css_lifecycle_labels,
    validate_current_contract,
    validate_css_known_debt,
    validate_diff_digest_claims,
    validate_lane_tombstone,
    validate_no_opaque_payload_fields,
    validate_patch_representations,
    validate_proportionality,
    validate_resolved_structured_decisions_v3,
    validate_route_obligations,
    validate_target_ledger,
)


PRIVATE_SOURCE_PATHS = private_source_binding_paths(ROOT, required=False)
if PRIVATE_SOURCE_PATHS is None:
    pytest.skip(
        "publication-excluded CSS evidence is unavailable",
        allow_module_level=True,
    )
SCENARIOS = ROOT / PRIVATE_SOURCE_PATHS["maintained_scenario_fixture"]
REGISTRY = ROOT / PRIVATE_SOURCE_PATHS["purpose_registry"]
LEDGER = ROOT / PRIVATE_SOURCE_PATHS["h1_target_ledger"]
LANE_N = ROOT / PRIVATE_SOURCE_PATHS["lane_n"]
LANE_T2 = ROOT / PRIVATE_SOURCE_PATHS["lane_t2"]
COMPACT = ROOT / PRIVATE_SOURCE_PATHS["compact_v3"]
KNOWN_DEBT = ROOT / "docs/governance/language-profile-known-debt.json"
PROVENANCE_V2 = ROOT / PRIVATE_SOURCE_PATHS["provenance_v2"]


def load_bundle() -> list[dict]:
    return [
        json.loads(SCENARIOS.read_text(encoding="utf-8")),
        load_json(LANE_N),
        load_json(LANE_T2),
        load_json(REGISTRY),
        load_json(LEDGER),
        load_json(COMPACT),
    ]


def validate_bundle(bundle: list[dict]) -> dict[str, int]:
    return validate_resolved_structured_decisions_v3(ROOT, *bundle)


def test_current_compact_contract_is_complete_and_proportionate() -> None:
    assert validate_current_contract(ROOT) == {
        "adjudications": 18,
        "bytes": 49248,
        "current_machine_bytes": 161893,
        "known_debt_debts": 5,
        "known_debt_low": 1,
        "known_debt_medium": 4,
        "row_fields": 14,
        "rows": 45,
    }


def test_private_source_binding_owner_fails_closed(tmp_path: Path) -> None:
    assert private_source_binding_paths(tmp_path, required=False) is None
    with pytest.raises(EvidenceContractError, match="unavailable"):
        private_source_binding_paths(tmp_path)

    owner_root = tmp_path / "private" / "evaluations" / "current"
    owner_root.mkdir(parents=True)
    owner = owner_root / "owner.md"
    payload = json.dumps(PRIVATE_SOURCE_PATHS, separators=(",", ":"), sort_keys=True)
    owner.write_text(
        f"{PRIVATE_BINDING_PREFIX}{payload} {PRIVATE_BINDING_SUFFIX}\n",
        encoding="utf-8",
    )
    assert private_source_binding_paths(tmp_path) == PRIVATE_SOURCE_PATHS

    redirect = dict(PRIVATE_SOURCE_PATHS)
    redirect["lane_t2"] = "unrelated/redirect/lane-t2-complete-vectors.json"
    owner.write_text(
        f"{PRIVATE_BINDING_PREFIX}"
        f"{json.dumps(redirect, separators=(',', ':'), sort_keys=True)} "
        f"{PRIVATE_BINDING_SUFFIX}\n",
        encoding="utf-8",
    )
    with pytest.raises(EvidenceContractError, match="commitment"):
        private_source_binding_paths(tmp_path)

    owner.write_text(
        f"{PRIVATE_BINDING_PREFIX}{payload} {PRIVATE_BINDING_SUFFIX}\n",
        encoding="utf-8",
    )

    duplicate = owner_root / "duplicate.md"
    duplicate.write_bytes(owner.read_bytes())
    with pytest.raises(EvidenceContractError, match="duplicated"):
        private_source_binding_paths(tmp_path)
    duplicate.unlink()

    unsafe = dict(PRIVATE_SOURCE_PATHS)
    unsafe["compact_v3"] = "/outside.json"
    owner.write_text(
        f"{PRIVATE_BINDING_PREFIX}"
        f"{json.dumps(unsafe, separators=(',', ':'), sort_keys=True)} "
        f"{PRIVATE_BINDING_SUFFIX}\n",
        encoding="utf-8",
    )
    with pytest.raises(EvidenceContractError, match="normalized and relative"):
        private_source_binding_paths(tmp_path)


def test_lane_t_tombstone_requires_exact_bound_replacement() -> None:
    tombstone = load_json(ROOT / PRIVATE_SOURCE_PATHS["lane_t"])
    expected = PRIVATE_SOURCE_PATHS["lane_t2"]
    assert validate_lane_tombstone(
        tombstone, expected_replacement=expected
    ) == tombstone
    redirected = deepcopy(tombstone)
    redirected["replacement"] = "unrelated/redirect/lane-t2-complete-vectors.json"
    with pytest.raises(EvidenceContractError, match="identity"):
        validate_lane_tombstone(redirected, expected_replacement=expected)


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
    value = deepcopy(load_json(KNOWN_DEBT))
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
    with pytest.raises(EvidenceContractError):
        validate_css_known_debt(value)


def test_current_known_debt_is_exact_and_human_accepted() -> None:
    assert validate_css_known_debt(load_json(KNOWN_DEBT)) == {
        "debts": 5,
        "low": 1,
        "medium": 4,
    }


def test_h1_target_identity_baseline_is_exact() -> None:
    ledger = load_json(LEDGER)
    validate_target_ledger(ledger)
    assert [target["tracked_path_count"] for target in ledger["targets"]] == [17, 69]
    assert [target["target_key"] for target in ledger["targets"]] == ["website", "theme"]


@pytest.mark.parametrize("path", (LEDGER, REGISTRY, LANE_N, LANE_T2, COMPACT))
def test_duplicate_json_keys_fail_closed(path: Path, tmp_path: Path) -> None:
    duplicate = path.read_text(encoding="utf-8").replace("{", '{"schema_version":99,', 1)
    candidate = tmp_path / path.name
    candidate.write_text(duplicate, encoding="utf-8")
    with pytest.raises(EvidenceContractError, match="duplicate JSON key"):
        load_json(candidate)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing-purpose",
        "duplicate-purpose",
        "purpose-id-gap",
        "wrong-row-class",
        "wrong-purpose-content",
        "purpose-digest-drift",
    ),
)
def test_purpose_identity_mutations_fail(mutation: str) -> None:
    bundle = deepcopy(load_bundle())
    resolved, registry = bundle[0], bundle[3]
    if mutation == "missing-purpose":
        registry["purposes"].pop()
    elif mutation == "duplicate-purpose":
        registry["purposes"][-1] = deepcopy(registry["purposes"][-2])
    elif mutation == "purpose-id-gap":
        registry["purposes"][1]["id"] = "APG77-CSS-099"
    elif mutation == "wrong-row-class":
        registry["purposes"][0]["row_class"] = "target"
    elif mutation == "wrong-purpose-content":
        resolved["rows"][0]["purpose"] = "different purpose"
    elif mutation == "purpose-digest-drift":
        registry["purposes"][0]["purpose_sha256"] = "0" * 64
    with pytest.raises(EvidenceContractError):
        validate_bundle(bundle)


def test_target_006_content_under_target_007_id_fails() -> None:
    bundle = deepcopy(load_bundle())
    replacement = deepcopy(bundle[0]["rows"][-2])
    replacement["id"] = "APG77-TARGET-007"
    bundle[0]["rows"][-1] = replacement
    with pytest.raises(EvidenceContractError):
        validate_bundle(bundle)


def test_wrong_target_identity_fails() -> None:
    bundle = deepcopy(load_bundle())
    bundle[4]["targets"][0]["commit"] = "0" * 40
    with pytest.raises(EvidenceContractError):
        validate_bundle(bundle)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing-row",
        "duplicate-row",
        "unknown-field",
        "field-from-nowhere",
        "wrong-selection",
        "wrong-response",
        "wrong-source-id",
        "wrong-edit-class",
        "wrong-completion-class",
    ),
)
def test_compact_schema_and_structured_mutations_fail(mutation: str) -> None:
    bundle = deepcopy(load_bundle())
    compact = bundle[5]
    if mutation == "missing-row":
        compact["rows"].pop()
    elif mutation == "duplicate-row":
        compact["rows"][-1] = deepcopy(compact["rows"][-2])
    elif mutation == "unknown-field":
        compact["rows"][0]["reasoning_summary"] = "not current machine authority"
    elif mutation == "field-from-nowhere":
        compact["rows"][0]["artifact_class"] = "invented artifact"
    elif mutation == "wrong-selection":
        compact["rows"][0]["css_selection"] = "non-trigger"
    elif mutation == "wrong-response":
        compact["rows"][0]["response"] = "stop-and-escalate"
    elif mutation == "wrong-source-id":
        compact["rows"][0]["normative_authority_ids"].append("invented-source")
    elif mutation == "wrong-edit-class":
        compact["rows"][0]["edit_permission_class"] = "unrestricted"
    elif mutation == "wrong-completion-class":
        compact["rows"][0]["completion_class"] = "complete-everything"
    with pytest.raises(EvidenceContractError):
        validate_bundle(bundle)


@pytest.mark.parametrize(
    ("decision", "index", "bad_value"),
    (
        ("retain-n", 0, "bounded-local-decision"),
        ("retain-t2", 1, "inspect-before-judgment"),
        ("synthesize", 2, "retain-n"),
    ),
)
def test_adjudication_action_semantics_fail_closed(
    decision: str,
    index: int,
    bad_value: str,
) -> None:
    bundle = deepcopy(load_bundle())
    adjudication = bundle[5]["adjudications"][index]
    assert adjudication["decision"] == decision
    if decision == "synthesize":
        adjudication["decision"] = bad_value
    else:
        adjudication["resolved_value"] = bad_value
    with pytest.raises(EvidenceContractError, match="action semantics"):
        validate_bundle(bundle)


@pytest.mark.parametrize("field", ("reason", "source_ids", "reviewer"))
def test_synthesize_requires_row_specific_source_backed_review(field: str) -> None:
    bundle = deepcopy(load_bundle())
    adjudication = next(
        item for item in bundle[5]["adjudications"] if item["decision"] == "synthesize"
    )
    adjudication[field] = [] if field == "source_ids" else ""
    with pytest.raises(EvidenceContractError):
        validate_bundle(bundle)


def test_agreement_must_not_be_adjudicated() -> None:
    bundle = deepcopy(load_bundle())
    bundle[2]["vectors"][0]["response"] = bundle[1]["vectors"][0]["response"]
    with pytest.raises(EvidenceContractError):
        validate_bundle(bundle)


def test_partial_route_deletion_fails() -> None:
    bundle = deepcopy(load_bundle())
    row = next(item for item in bundle[5]["rows"] if len(item["route_obligations"]) > 1)
    row["route_obligations"].pop()
    with pytest.raises(EvidenceContractError, match="incomplete"):
        validate_bundle(bundle)


def test_same_owner_different_scope_collapse_fails_independently() -> None:
    expected = [
        {"obligation_id": "R-01", "owner": "host-owner", "decision_scope": "host-file", "stop_state": "outside"},
        {"obligation_id": "R-02", "owner": "host-owner", "decision_scope": "host-extraction", "stop_state": "outside"},
    ]
    collapsed = [
        {"obligation_id": "R-01", "owner": "host-owner", "decision_scope": "host-file-and-extraction", "stop_state": "outside"}
    ]
    with pytest.raises(EvidenceContractError, match="incomplete"):
        validate_route_obligations(collapsed, expected=expected)


def test_conflicting_or_duplicate_route_obligation_fails() -> None:
    value = [
        {"obligation_id": "R-01", "owner": "runtime-owner", "decision_scope": "runtime", "stop_state": "open"},
        {"obligation_id": "R-01", "owner": "runtime-owner", "decision_scope": "runtime", "stop_state": "blocked"},
    ]
    with pytest.raises(EvidenceContractError, match="duplicate"):
        validate_route_obligations(value)


def test_stale_lane_t_cannot_be_current_authority() -> None:
    bundle = deepcopy(load_bundle())
    bundle[5]["source_bindings"]["lane_t"]["authority_class"] = "current-product-semantics"
    with pytest.raises(EvidenceContractError, match="authority classification"):
        validate_bundle(bundle)


def scanner_findings(candidate: str, target: bytes) -> list[tuple[str, str, str]]:
    return unapproved_target_overlaps(
        {"artifact": {"field": "prefix " + candidate + " suffix"}},
        {"target": b"unrelated " + target + b" bytes"},
        allowed_values=set(),
    )


@pytest.mark.parametrize("encoding", ("raw", "json", "hex", "base64", "backslash-hex", "unicode"))
def test_supported_no_copy_forms_are_detected(encoding: str) -> None:
    copied = b"synthetic target expression exceeds thirty two bytes exactly"
    candidates = {
        "raw": copied.decode(),
        "json": json.loads('"synthetic \\u0074arget expression exceeds thirty two bytes exactly"'),
        "hex": copied.hex(),
        "base64": base64.b64encode(copied).decode(),
        "backslash-hex": "".join(f"\\x{byte:02x}" for byte in copied),
        "unicode": "".join(f"\\u{byte:04x}" for byte in copied),
    }
    assert scanner_findings(candidates[encoding], copied)


def test_valid_unicode_surrogate_pairs_are_detected() -> None:
    copied = ("😀" * 12).encode("utf-8")
    escaped = "\\ud83d\\ude00" * 12
    assert scanner_findings(escaped, copied)


def test_unsupported_compressed_form_is_not_overclaimed() -> None:
    copied = b"synthetic target expression exceeds thirty two bytes exactly"
    compressed = base64.b64encode(zlib.compress(copied)).decode()
    assert not scanner_findings(compressed, copied)


@pytest.mark.parametrize(
    "field",
    (
        "target_excerpt",
        "source_excerpt",
        "raw_source",
        "source_body",
        "encoded_source",
        "compressed_source",
        "payload_bytes",
        "reconstruction_script",
    ),
)
def test_banned_opaque_payload_fields_fail(field: str) -> None:
    with pytest.raises(EvidenceContractError, match="banned opaque payload"):
        validate_no_opaque_payload_fields({"row": {field: "opaque"}})


def test_current_machine_artifacts_have_no_banned_payload_fields() -> None:
    for path in (SCENARIOS, REGISTRY, COMPACT):
        validate_no_opaque_payload_fields(load_json(path) if path != SCENARIOS else json.loads(path.read_text()))


def test_named_patch_representation_is_exact() -> None:
    validate_patch_representations(load_json(COMPACT)["patch_representations"])


def test_unnamed_diff_digest_fails() -> None:
    with pytest.raises(EvidenceContractError, match="no matching named byte stream"):
        validate_diff_digest_claims({"diff_sha256": "a" * 64})


def test_mislabeled_or_false_patch_digest_fails() -> None:
    record = deepcopy(load_json(COMPACT)["patch_representations"])
    record[0]["sha256"] = FALSE_APG77B_DIFF_DIGEST
    with pytest.raises(EvidenceContractError):
        validate_patch_representations(record)


def test_declared_lifecycle_labels_accept_only_proposed_correction_or_provisional_integration() -> None:
    validate_declared_css_lifecycle_labels("corrected-awaiting-fresh-review", adr_status="Proposed", integrated=False)
    validate_declared_css_lifecycle_labels("provisionally-integrated", adr_status="Accepted with amendment", integrated=True)
    with pytest.raises(EvidenceContractError):
        validate_declared_css_lifecycle_labels("provisionally-integrated", adr_status="Proposed", integrated=True)
    with pytest.raises(EvidenceContractError):
        validate_declared_css_lifecycle_labels("corrected-awaiting-fresh-review", adr_status="Rejected", integrated=False)


def test_artifact_size_ceilings_fail_closed() -> None:
    with pytest.raises(EvidenceContractError, match="120 KiB"):
        validate_proportionality({"resolved-structured-decisions-v3.json": b"x" * (120 * 1024 + 1)})
    with pytest.raises(EvidenceContractError, match="150 KiB"):
        validate_proportionality({
            "resolved-structured-decisions-v3.json": b"{}",
            "other.json": b"x" * (150 * 1024 + 1),
        })
    with pytest.raises(EvidenceContractError, match="350 KiB"):
        validate_proportionality({
            "resolved-structured-decisions-v3.json": b"x" * (120 * 1024),
            "a.json": b"x" * (120 * 1024),
            "b.json": b"x" * (120 * 1024),
        })


def test_historical_provenance_is_retained_but_not_current_machine_authority() -> None:
    compact = load_json(COMPACT)
    binding = compact["source_bindings"]["provenance_v2"]
    assert binding["authority_class"] == "historical-non-current-review-evidence"
    assert PROVENANCE_V2.stat().st_size == 747455


def test_compact_canonical_encoding_rejects_pretty_json(tmp_path: Path) -> None:
    compact = load_json(COMPACT)
    pretty = tmp_path / "pretty.json"
    pretty.write_text(canonical_json(compact).replace("{", "{\n", 1), encoding="utf-8")
    with pytest.raises(EvidenceContractError, match="compact canonical JSON"):
        load_json(pretty)
