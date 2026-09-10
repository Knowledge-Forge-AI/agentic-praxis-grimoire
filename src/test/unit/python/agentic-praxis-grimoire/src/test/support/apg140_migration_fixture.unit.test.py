"""Source-bound synthetic migration planning evidence, without database execution."""

import copy
import sys

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))
from apg140_migration_fixture import EvidenceRefused, assess, read_packet  # noqa: E402


def packet():
    return read_packet((ROOT / "docs/governance/external/apg140/migration-fixture.json").read_text())


def test_complete_source_bound_composition_is_admitted_without_mutation():
    value = packet()
    original = copy.deepcopy(value)
    assert assess(value) == "synthetic-composition-supported"
    assert value == original


@pytest.mark.parametrize("field,value,reason", [
    ("schema_version", 2, "unsupported_version"),
    ("schema_version", True, "unsupported_version"),
    ("source_contract", "unobserved-source", "source_identity_drift"),
    ("scope", "hosted", "unqualified_scope_or_owner"),
    ("owner", "unowned", "unqualified_scope_or_owner"),
    ("ledger", {"applied": ["different"], "expected": ["prior", "next"]}, "diverged_schema_ledger"),
    ("backup", {"checksum_verified": True, "restore_supported": False,
                "restore_rehearsal": "synthetic-success"}, "backup_restore_evidence_incomplete"),
    ("backup", {"checksum_verified": True, "restore_supported": True,
                "restore_rehearsal": "failed"}, "backup_restore_evidence_incomplete"),
    ("before", [2, 1, 1, 1], "diverged_repository_identity"),
    ("before", [2, 2, 0, 1], "diverged_repository_identity"),
    ("before", [True, 1, 0, 1], "malformed_identity_state"),
    ("after", [2, 1, 0, 1], "repository_identity_verification_failed"),
    ("after", [1, 1, 0], "malformed_identity_state"),
    ("steps", ["drop-legacy", "verify-backup"], "unsafe_cutover_order"),
    ("rollback", "unknown", "rollback_unavailable"),
])
def test_adverse_migration_evidence_refuses_before_any_cutover(field, value, reason):
    evidence = packet()
    evidence[field] = value
    with pytest.raises(EvidenceRefused, match=reason):
        assess(evidence)


def test_partial_unknown_malformed_and_duplicate_fields_refuse():
    for evidence in ({}, {**packet(), "unknown": 1}):
        with pytest.raises(EvidenceRefused, match="invalid_fields"):
            assess(evidence)
    with pytest.raises(EvidenceRefused, match="malformed_json"):
        read_packet('{"schema_version":')
    with pytest.raises(EvidenceRefused, match="duplicate_field"):
        read_packet('{"schema_version":1,"schema_version":1}')
