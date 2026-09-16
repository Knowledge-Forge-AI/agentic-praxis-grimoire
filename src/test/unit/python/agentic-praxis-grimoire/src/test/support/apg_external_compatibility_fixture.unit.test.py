"""Unit tests for APG140 bounded synthetic APGR consumer fixtures.

Exercises wire version selection, legacy version 0 array parsing, version 1 presentation
envelopes, policy-driven fail-closed validation, adverse cases, caller expected bindings,
pre-consumption cancellation, caller refusal, synthetic graph checking with cycle tolerance
and provenance separation, and strict manifest byte and member set verification.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
FIXTURES_DIR = ROOT / "testing/fixtures/external_compatibility/apg140"
sys.path.insert(0, str(SUPPORT))

from apg_external_compatibility_fixture import (  # noqa: E402
    PUBLIC_CONTRACT_ID,
    CallerBinding,
    CallerRefusalError,
    CancellationToken,
    EnvelopeValidationError,
    FixtureCancellationError,
    IdentityDriftError,
    ManifestVerificationError,
    SyntheticGraphChecker,
    UnknownFieldError,
    WireVersionError,
    parse_and_validate_envelope,
    validate_wire_version,
    verify_fixture_manifest,
    admit_negotiation_observation,
)


# --- 1. Wire Version Selection Tests ---

def test_valid_wire_versions() -> None:
    assert validate_wire_version(0) == 0
    assert validate_wire_version(1) == 1


@pytest.mark.parametrize("bad_bool", [True, False])
def test_wire_version_boolean_refused(bad_bool: bool) -> None:
    with pytest.raises(WireVersionError, match="boolean schema versions are refused"):
        validate_wire_version(bad_bool)


@pytest.mark.parametrize("bad_version", [2, -1, 42, 100])
def test_wire_version_unsupported_integers(bad_version: int) -> None:
    with pytest.raises(WireVersionError, match="unsupported wire version"):
        validate_wire_version(bad_version)


@pytest.mark.parametrize("bad_type", ["1", "0", 1.0, None, [1], {"version": 1}])
def test_wire_version_non_integer_types(bad_type: object) -> None:
    with pytest.raises(WireVersionError, match="wire version must be integer"):
        validate_wire_version(bad_type)


# --- 2. Version 0 Legacy Bounded Array Tests ---

def test_v0_legacy_nodes_array_file_consumption() -> None:
    case_path = FIXTURES_DIR / "cases/v0_legacy_nodes_array.json"
    result = parse_and_validate_envelope(
        case_path.read_text(encoding="utf-8"),
        wire_version=0,
    )
    assert result.wire_version == 0
    assert result.result_kind == "legacy_bounded_array"
    assert len(result.items) == 2
    assert result.page is None
    assert result.diagnostics == []
    # Legacy bounded array cannot prove completeness
    assert result.is_complete is False
    assert result.proves_completeness() is False


def test_v0_legacy_array_rejects_object() -> None:
    with pytest.raises(EnvelopeValidationError, match="expects JSON array"):
        parse_and_validate_envelope({"some": "object"}, wire_version=0)


def test_v0_legacy_array_detects_wire_version_drift() -> None:
    binding = CallerBinding(expected_wire_version=1)
    with pytest.raises(IdentityDriftError, match="wire version drift"):
        parse_and_validate_envelope([{"key": "val"}], wire_version=0, caller_binding=binding)


# --- 3. Version 1 Canonical Nodes and Edges Presentation Envelopes ---

def test_v1_canonical_nodes_exhausted_case() -> None:
    case_path = FIXTURES_DIR / "cases/v1_canonical_nodes_exhausted.json"
    result = parse_and_validate_envelope(
        case_path.read_text(encoding="utf-8"),
        wire_version=1,
    )
    assert result.wire_version == 1
    assert result.result_kind == "canonical_nodes"
    assert len(result.items) == 3
    assert result.page is not None
    assert result.page.limit == 50
    assert result.page.offset == 0
    assert result.page.returned == 3
    assert result.page.truncated is False
    assert result.page.next_offset is None
    assert result.diagnostics == []
    assert result.is_complete is True
    assert result.proves_completeness() is True


def test_v1_canonical_nodes_truncated_case() -> None:
    case_path = FIXTURES_DIR / "cases/v1_canonical_nodes_truncated.json"
    result = parse_and_validate_envelope(
        case_path.read_text(encoding="utf-8"),
        wire_version=1,
    )
    assert result.wire_version == 1
    assert result.result_kind == "canonical_nodes"
    assert len(result.items) == 2
    assert result.page is not None
    assert result.page.limit == 2
    assert result.page.offset == 0
    assert result.page.returned == 2
    assert result.page.truncated is True
    assert result.page.next_offset == 2
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "result_truncated"
    assert result.diagnostics[0].message == "additional results are available"
    # Incomplete / truncated page cannot prove completeness
    assert result.is_complete is False
    assert result.proves_completeness() is False


def test_v1_canonical_edges_exhausted_case() -> None:
    case_path = FIXTURES_DIR / "cases/v1_canonical_edges_exhausted.json"
    result = parse_and_validate_envelope(
        case_path.read_text(encoding="utf-8"),
        wire_version=1,
    )
    assert result.wire_version == 1
    assert result.result_kind == "canonical_edges"
    assert len(result.items) == 2
    assert result.page is not None
    assert result.page.truncated is False
    assert result.page.next_offset is None
    assert result.is_complete is True


def test_v1_canonical_edges_truncated_case() -> None:
    case_path = FIXTURES_DIR / "cases/v1_canonical_edges_truncated.json"
    result = parse_and_validate_envelope(
        case_path.read_text(encoding="utf-8"),
        wire_version=1,
    )
    assert result.wire_version == 1
    assert result.result_kind == "canonical_edges"
    assert len(result.items) == 1
    assert result.page is not None
    assert result.page.truncated is True
    assert result.page.next_offset == 1
    assert result.is_complete is False


# --- 4. Adverse Cases and Fail-Closed Policy Enforcement ---

def test_unknown_envelope_field_fails_closed_under_apgr_policy() -> None:
    case_path = FIXTURES_DIR / "cases/v1_unknown_envelope_field.json"
    with pytest.raises(UnknownFieldError) as exc_info:
        parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))
    msg = str(exc_info.value)
    assert "fail closed under APGR selected policy" in msg
    assert "unexpected_field_policy_violation" in msg


def test_unknown_page_descriptor_field_fails_closed() -> None:
    payload = {
        "schema_version": 1,
        "result_kind": "canonical_nodes",
        "items": [],
        "page": {
            "limit": 50,
            "offset": 0,
            "returned": 0,
            "truncated": False,
            "next_offset": None,
            "extra_page_token": "disallowed",
        },
        "diagnostics": [],
    }
    with pytest.raises(UnknownFieldError, match="unknown page field.*fail closed"):
        parse_and_validate_envelope(payload)


def test_missing_envelope_page_field() -> None:
    case_path = FIXTURES_DIR / "cases/v1_partial_missing_page.json"
    with pytest.raises(EnvelopeValidationError, match="missing required envelope field.*page"):
        parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))


def test_missing_page_limit_field() -> None:
    case_path = FIXTURES_DIR / "cases/v1_partial_missing_limit.json"
    with pytest.raises(EnvelopeValidationError, match="missing required page descriptor field.*limit"):
        parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("bad_limit", [0, -1, 201, 500, "50", True])
def test_page_limit_range_violations(bad_limit: object) -> None:
    payload = {
        "schema_version": 1,
        "result_kind": "canonical_nodes",
        "items": [],
        "page": {
            "limit": bad_limit,
            "offset": 0,
            "returned": 0,
            "truncated": False,
            "next_offset": None,
        },
        "diagnostics": [],
    }
    with pytest.raises(EnvelopeValidationError, match="'page.limit' must be integer in range"):
        parse_and_validate_envelope(payload)


@pytest.mark.parametrize("bad_offset", [-1, -10, "0", True])
def test_page_offset_range_violations(bad_offset: object) -> None:
    payload = {
        "schema_version": 1,
        "result_kind": "canonical_nodes",
        "items": [],
        "page": {
            "limit": 50,
            "offset": bad_offset,
            "returned": 0,
            "truncated": False,
            "next_offset": None,
        },
        "diagnostics": [],
    }
    with pytest.raises(EnvelopeValidationError, match="'page.offset' must be non-negative integer"):
        parse_and_validate_envelope(payload)


def test_page_returned_count_mismatch() -> None:
    case_path = FIXTURES_DIR / "cases/v1_count_mismatch.json"
    with pytest.raises(EnvelopeValidationError, match="'page.returned' .* does not match actual length"):
        parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))


def test_page_returned_exceeds_limit() -> None:
    payload = {
        "schema_version": 1,
        "result_kind": "canonical_nodes",
        "items": [{"canonical_key": "n:1"}, {"canonical_key": "n:2"}],
        "page": {
            "limit": 1,
            "offset": 0,
            "returned": 2,
            "truncated": False,
            "next_offset": None,
        },
        "diagnostics": [],
    }
    with pytest.raises(EnvelopeValidationError, match="exceeds declared 'page.limit'"):
        parse_and_validate_envelope(payload)


def test_diagnostic_inconsistency_truncated_missing_code() -> None:
    case_path = FIXTURES_DIR / "cases/v1_diagnostic_inconsistent_truncated.json"
    with pytest.raises(EnvelopeValidationError, match="diagnostic consistency violation.*lacks required 'result_truncated'"):
        parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))


def test_diagnostic_inconsistency_exhausted_with_code() -> None:
    case_path = FIXTURES_DIR / "cases/v1_diagnostic_inconsistent_exhausted.json"
    with pytest.raises(EnvelopeValidationError, match="diagnostic consistency violation.*page is exhausted.*contains 'result_truncated'"):
        parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))


def test_next_offset_mismatch_when_truncated() -> None:
    payload = {
        "schema_version": 1,
        "result_kind": "canonical_nodes",
        "items": [{"canonical_key": "n:1"}],
        "page": {
            "limit": 1,
            "offset": 10,
            "returned": 1,
            "truncated": True,
            "next_offset": 99,  # Should be 10 + 1 = 11
        },
        "diagnostics": [{"code": "result_truncated", "message": "additional results are available"}],
    }
    with pytest.raises(EnvelopeValidationError, match=r"'page.next_offset' .* must equal offset \+ returned"):
        parse_and_validate_envelope(payload)


def test_next_offset_must_be_null_when_exhausted() -> None:
    payload = {
        "schema_version": 1,
        "result_kind": "canonical_nodes",
        "items": [],
        "page": {
            "limit": 50,
            "offset": 0,
            "returned": 0,
            "truncated": False,
            "next_offset": 0,  # Must be null
        },
        "diagnostics": [],
    }
    with pytest.raises(EnvelopeValidationError, match="'page.next_offset' must be null"):
        parse_and_validate_envelope(payload)


def test_malformed_json_syntax_rejection() -> None:
    case_path = FIXTURES_DIR / "cases/malformed_syntax.json"
    with pytest.raises(EnvelopeValidationError, match="malformed JSON payload"):
        parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))


# --- 5. Caller Expected Binding & Identity Drift Tests ---

def test_identity_drift_result_kind_mismatch() -> None:
    case_path = FIXTURES_DIR / "cases/identity_drift_binding.json"
    binding = CallerBinding(expected_result_kind="canonical_nodes")
    with pytest.raises(IdentityDriftError, match="result_kind identity drift"):
        parse_and_validate_envelope(
            case_path.read_text(encoding="utf-8"),
            caller_binding=binding,
        )


def test_identity_drift_public_contract_id_mismatch() -> None:
    binding = CallerBinding(expected_public_id="APG999-UNRECOGNIZED")
    case_path = FIXTURES_DIR / "cases/v1_canonical_nodes_exhausted.json"
    with pytest.raises(IdentityDriftError, match="public contract identity drift"):
        parse_and_validate_envelope(
            case_path.read_text(encoding="utf-8"),
            caller_binding=binding,
        )


def test_caller_expected_binding_matches_cleanly() -> None:
    binding = CallerBinding(
        expected_result_kind="canonical_nodes",
        expected_public_id=PUBLIC_CONTRACT_ID,
        expected_wire_version=1,
    )
    case_path = FIXTURES_DIR / "cases/v1_canonical_nodes_exhausted.json"
    res = parse_and_validate_envelope(
        case_path.read_text(encoding="utf-8"),
        caller_binding=binding,
    )
    assert res.result_kind == "canonical_nodes"


# --- 6. Caller Refusal and Explicit Cancellation Tests ---

def test_caller_owned_refusal_error() -> None:
    binding = CallerBinding(refuse_reason="pre-flight authorization revoked")
    with pytest.raises(CallerRefusalError, match="caller refused consumption: pre-flight authorization revoked"):
        parse_and_validate_envelope("{}", caller_binding=binding)


def test_pre_consumption_cancellation_distinct_error() -> None:
    cancel_token = CancellationToken()
    cancel_token.cancel("timeout window exceeded")

    # Even with completely invalid or malformed JSON, cancellation raises distinct error FIRST
    with pytest.raises(FixtureCancellationError, match="consumption cancelled before processing: timeout window exceeded"):
        parse_and_validate_envelope("invalid non-json text", cancel_token=cancel_token)


def test_uncancelled_token_proceeds_normally() -> None:
    cancel_token = CancellationToken()
    case_path = FIXTURES_DIR / "cases/v1_canonical_nodes_exhausted.json"
    res = parse_and_validate_envelope(
        case_path.read_text(encoding="utf-8"),
        cancel_token=cancel_token,
    )
    assert res.is_complete is True


# --- 7. Embedded Collections (Neighborhood) Tests ---

def test_v1_embedded_neighborhood_exhausted() -> None:
    case_path = FIXTURES_DIR / "cases/v1_embedded_neighborhood_exhausted.json"
    res = parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))
    assert res.result_kind == "canonical_neighborhood"
    assert res.embedded_result is not None
    assert res.embedded_result["center"] == "n:core:router"
    assert res.collections is not None
    assert "nodes" in res.collections
    assert "edges" in res.collections
    assert res.collections["nodes"].truncated is False
    assert res.collections["edges"].truncated is False
    assert res.is_complete is True


def test_v1_embedded_neighborhood_truncated() -> None:
    case_path = FIXTURES_DIR / "cases/v1_embedded_neighborhood_truncated.json"
    res = parse_and_validate_envelope(case_path.read_text(encoding="utf-8"))
    assert res.result_kind == "canonical_neighborhood"
    assert res.collections is not None
    assert res.collections["nodes"].truncated is True
    assert res.collections["nodes"].next_offset == 1
    assert res.is_complete is False


# --- 8. Source-Bound Synthetic Graph Checker Tests ---

def test_synthetic_graph_checker_exact_match() -> None:
    checker = SyntheticGraphChecker()
    nodes = [
        {"canonical_key": "n:auth:1", "kind": "service"},
        {"canonical_key": "n:core:2", "kind": "router"},
    ]
    edges = [
        ("n:auth:1", "verifies", "n:core:2", "h:auth:tls"),
    ]
    report = checker.check_graph(nodes, edges, nodes, edges)
    assert report.storage_is_exact_match is True
    assert report.matched_nodes == ["n:auth:1", "n:core:2"]
    assert len(report.matched_edges) == 1
    assert report.missing_nodes == []
    assert report.spurious_nodes == []
    assert report.duplicate_nodes == []


def test_synthetic_graph_checker_accepts_cycles() -> None:
    checker = SyntheticGraphChecker()
    case_nodes = json.loads((FIXTURES_DIR / "cases/v1_cyclic_graph.json").read_text())["items"]
    case_edges = json.loads((FIXTURES_DIR / "cases/v1_cyclic_graph_edges.json").read_text())["items"]

    # Graph is a directed 3-cycle: alpha -> beta -> gamma -> alpha
    expected_nodes = [{"canonical_key": "n:cycle:" + name, "kind": "module"}
                      for name in ("alpha", "beta", "gamma")]
    expected_edges = [("n:cycle:alpha", "calls", "n:cycle:beta", "h:cycle:ab"),
                      ("n:cycle:beta", "calls", "n:cycle:gamma", "h:cycle:bg"),
                      ("n:cycle:gamma", "calls", "n:cycle:alpha", "h:cycle:ga")]
    report = checker.check_graph(expected_nodes, expected_edges, case_nodes, case_edges)
    assert report.storage_is_exact_match is True
    assert report.cycles_accepted is True
    assert len(report.cycles_detected) >= 1
    # Check that cycle nodes are present
    cycle_flattened = [node for c in report.cycles_detected for node in c]
    assert "n:cycle:alpha" in cycle_flattened


def test_synthetic_graph_checker_missing_spurious_duplicate_conflict() -> None:
    checker = SyntheticGraphChecker()
    expected_nodes = [
        {"canonical_key": "n:conflict:node_a", "kind": "worker"},
        {"canonical_key": "n:conflict:node_b", "kind": "service_original"},
        {"canonical_key": "n:missing:node_c", "kind": "module"},
    ]
    expected_edges = [
        ("n:conflict:node_a", "calls", "n:conflict:node_b", "h:expected_hash"),
    ]

    # Observed nodes loaded from fixture case (contains duplicate node_a, modified node_b, and spurious)
    obs_nodes = json.loads((FIXTURES_DIR / "cases/v1_graph_with_conflicts.json").read_text())["items"]
    obs_edges = [
        ("n:conflict:node_a", "calls", "n:conflict:node_b", "h:different_hash"),
        ("n:conflict:node_a", "calls", "n:conflict:node_b", "h:different_hash"),  # duplicate edge
        ("n:spurious:src", "calls", "n:spurious:tgt", "h:spurious"),
    ]

    report = checker.check_graph(expected_nodes, expected_edges, obs_nodes, obs_edges)
    assert report.storage_is_exact_match is False
    # Check node findings
    assert "n:conflict:node_a" in report.duplicate_nodes
    assert "n:missing:node_c" in report.missing_nodes
    assert "n:conflict:spurious" in report.spurious_nodes
    assert any(c["canonical_key"] == "n:conflict:node_b" for c in report.conflicted_nodes)
    # Check edge findings
    assert ("n:conflict:node_a", "calls", "n:conflict:node_b", "h:different_hash") in report.duplicate_edges
    assert any(c["conflict"] == "identity_metadata_hash_mismatch" for c in report.conflicted_edges)
    assert ("n:spurious:src", "calls", "n:spurious:tgt", "h:spurious") in report.spurious_edges


def test_synthetic_graph_checker_provenance_separation() -> None:
    checker = SyntheticGraphChecker()
    nodes = [{"canonical_key": "n:test:1", "kind": "unit"}]
    edges = [("n:test:1", "links", "n:test:1", "h:self")]

    # Storage matches perfectly, but provenance is degraded/missing
    exp_prov = {"generation": "sg1:expected", "origin": "extractor-v1"}
    obs_prov = {"generation": "sg1:mismatched_generation", "extra_trace": "unlinked_val"}

    report = checker.check_graph(
        nodes,
        edges,
        nodes,
        edges,
        expected_provenance=exp_prov,
        observed_provenance=obs_prov,
    )

    # Storage claims are satisfied
    assert report.storage_is_exact_match is True

    # Provenance quality is separated and reports failure
    assert report.provenance_is_sound is False
    statuses = {f.key: f.status for f in report.provenance_findings}
    assert statuses["generation"] == "mismatched"
    assert statuses["origin"] == "missing"
    assert statuses["extra_trace"] == "unlinked"


# --- 9. Fixture Cases Manifest Verification & Mutation Controls ---

def test_fixture_manifest_verification_on_checked_in_suite() -> None:
    res = verify_fixture_manifest(FIXTURES_DIR)
    assert res["verified_members_count"] == 18
    assert res["public_contract_id"] == PUBLIC_CONTRACT_ID
    assert len(res["manifest_digest"]) == 64


def test_manifest_verification_fails_on_tampered_byte(tmp_path: Path) -> None:
    import shutil
    copy_dir = tmp_path / "apg140_tamper"
    shutil.copytree(FIXTURES_DIR, copy_dir)

    # Tamper with one case file byte keeping exact same byte length to trigger sha256 mismatch
    target_case = copy_dir / "cases/v1_canonical_nodes_exhausted.json"
    raw_bytes = bytearray(target_case.read_bytes())
    raw_bytes[10] ^= 0x01
    target_case.write_bytes(raw_bytes)

    with pytest.raises(ManifestVerificationError, match="member SHA-256 digest mismatch"):
        verify_fixture_manifest(copy_dir)


def test_manifest_verification_fails_on_size_mismatch(tmp_path: Path) -> None:
    import shutil
    copy_dir = tmp_path / "apg140_size_mismatch"
    shutil.copytree(FIXTURES_DIR, copy_dir)

    target_case = copy_dir / "cases/v1_canonical_nodes_exhausted.json"
    content = target_case.read_text()
    # Change length to trigger size mismatch
    target_case.write_text(content + "\n")

    with pytest.raises(ManifestVerificationError, match="member size mismatch"):
        verify_fixture_manifest(copy_dir)


def test_manifest_verification_fails_on_unlisted_file(tmp_path: Path) -> None:
    import shutil
    copy_dir = tmp_path / "apg140_unlisted"
    shutil.copytree(FIXTURES_DIR, copy_dir)

    # Drop an unlisted file into cases
    unlisted = copy_dir / "cases/unlisted_fixture.json"
    unlisted.write_text("{}", encoding="utf-8")

    with pytest.raises(ManifestVerificationError, match="unlisted file found in fixture directory"):
        verify_fixture_manifest(copy_dir)


def test_manifest_verification_fails_on_omitted_file(tmp_path: Path) -> None:
    import shutil
    copy_dir = tmp_path / "apg140_omitted"
    shutil.copytree(FIXTURES_DIR, copy_dir)

    # Remove a declared member
    omitted = copy_dir / "cases/v1_canonical_nodes_truncated.json"
    omitted.unlink()

    with pytest.raises(ManifestVerificationError, match="declared member file does not exist"):
        verify_fixture_manifest(copy_dir)


def test_manifest_verification_fails_on_symlink(tmp_path: Path) -> None:
    import shutil
    copy_dir = tmp_path / "apg140_symlink"
    shutil.copytree(FIXTURES_DIR, copy_dir)

    # Create a symlink inside cases
    target = copy_dir / "cases/v1_canonical_nodes_exhausted.json"
    link = copy_dir / "cases/symlink_case.json"
    link.symlink_to(target.name)

    with pytest.raises(ManifestVerificationError, match="symlink"):
        verify_fixture_manifest(copy_dir)


def test_manifest_verification_fails_on_path_traversal(tmp_path: Path) -> None:
    import shutil
    copy_dir = tmp_path / "apg140_traversal"
    shutil.copytree(FIXTURES_DIR, copy_dir)

    manifest_p = copy_dir / "manifest.json"
    m_data = json.loads(manifest_p.read_text())
    m_data["members"][0]["path"] = "../outside.json"
    manifest_p.write_text(json.dumps(m_data))

    with pytest.raises(ManifestVerificationError, match="illegal path traversal"):
        verify_fixture_manifest(copy_dir)


@pytest.mark.parametrize("damage", ["no_collections", "count", "unknown_page", "false_diagnostic"])
def test_embedded_evidence_cannot_hide_missing_or_inconsistent_collections(damage):
    value = json.loads((FIXTURES_DIR / "cases/v1_embedded_neighborhood_exhausted.json").read_text())
    if damage == "no_collections":
        value["collections"] = {}
    elif damage == "count":
        value["collections"]["nodes"]["returned"] = 100
    elif damage == "unknown_page":
        value["collections"]["nodes"]["extra"] = 1
    else:
        value["diagnostics"] = [{"code": "result_truncated", "message": "additional results are available", "collection": "nodes"}]
    with pytest.raises(EnvelopeValidationError):
        parse_and_validate_envelope(value)


def test_duplicate_json_and_invalid_utf8_are_caller_owned_refusals():
    with pytest.raises(EnvelopeValidationError):
        parse_and_validate_envelope('{"schema_version":1,"schema_version":1}')
    with pytest.raises(EnvelopeValidationError):
        parse_and_validate_envelope(bytes([255]))


@pytest.mark.parametrize("damage", ["hidden", "duplicate", "manifest_link", "directory_link"])
def test_manifest_complete_inventory_refuses_omissions_and_linked_owners(tmp_path, damage):
    import shutil
    dest = tmp_path / "fixture"
    shutil.copytree(FIXTURES_DIR, dest)
    manifest = dest / "manifest.json"
    if damage == "hidden":
        (dest / "cases/.unlisted.json").write_text("{}")
    elif damage == "duplicate":
        data = json.loads(manifest.read_text())
        data["members"].append(data["members"][0])
        manifest.write_text(json.dumps(data))
    elif damage == "manifest_link":
        actual = tmp_path / "manifest.json"
        manifest.rename(actual)
        manifest.symlink_to(actual)
    else:
        (dest / "cases").rename(dest / "actual-cases")
        (dest / "cases").symlink_to("actual-cases", target_is_directory=True)
    with pytest.raises(ManifestVerificationError):
        verify_fixture_manifest(dest)


def test_graph_conflicting_duplicate_and_missing_attribute_do_not_match():
    expected = [{"canonical_key": "node:a", "kind": "file"}]
    checker = SyntheticGraphChecker()
    for observed in ([{"canonical_key": "node:a"}], expected + [{"canonical_key": "node:a", "kind": "tool"}]):
        result = checker.check_graph(expected, [], observed, [])
        assert not result.storage_is_exact_match
    result = checker.check_graph(expected, [], expected, [], expected_provenance={"a": "source-a"}, observed_provenance={"a": "source-a", "b": "invented"})
    assert not result.provenance_is_sound


@pytest.mark.parametrize("versions", [[], [0], [2], [1, 2], [True], "1"])
def test_fixed_async1_negotiation_projection_refuses_unqualified_versions(versions):
    assert admit_negotiation_observation({"schema_version": 1, "protocol_versions": [1]}) == 1
    with pytest.raises(WireVersionError, match="negotiation_failed"):
        admit_negotiation_observation({"schema_version": 1, "protocol_versions": versions})


def test_source_bound_support_members_match_checked_in_bytes():
    bindings = json.loads((ROOT / "docs/governance/external/apg140/support-bindings.json").read_text())
    paths = [row["path"] for row in bindings["members"]]
    assert len(paths) == len(set(paths)) == 15
    assert "report/types.go" in paths
    assert "src/test/support/apg140_migration_fixture.py" in paths
    for row in bindings["members"]:
        path = ROOT / row["path"]
        assert not path.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    # The member manifest binds its own cases as a complete set, not just an index.
    verify_fixture_manifest(FIXTURES_DIR)


def test_duplicate_materialization_and_unavailable_provenance_are_distinct():
    report = SyntheticGraphChecker().check_graph(["node:a"], [], ["node:a", "node:a"], [])
    assert report.duplicate_nodes == ["node:a"]
    assert not report.storage_is_exact_match
    assert report.provenance_is_sound is None


def test_duplicate_field_in_otherwise_valid_envelope_refuses():
    raw = (FIXTURES_DIR / "cases/v1_canonical_nodes_exhausted.json").read_text()
    raw = raw.replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,')
    with pytest.raises(EnvelopeValidationError, match="duplicate JSON field"):
        parse_and_validate_envelope(raw)
