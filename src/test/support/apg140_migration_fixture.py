"""APG140 synthetic migration-evidence admission, never a migration executor.

Source: APG140-RM-MAIN-20260912 runtime/schema_upgrade.py and
runtime/schema_decommission.py. The extra restore rehearsal and ownership
evidence requirements are APGR composition policy, not a claim about execution.
"""

from __future__ import annotations

import json


class EvidenceRefused(ValueError):
    """Caller-owned refusal with a bounded reason, without runtime side effects."""


def assess(packet: dict) -> str:
    """Admit only a complete synthetic local migration planning record."""
    fields = {"schema_version", "source_contract", "scope", "owner", "ledger",
              "backup", "before", "after", "steps", "rollback"}
    if not isinstance(packet, dict) or set(packet) != fields:
        raise EvidenceRefused("invalid_fields")
    if type(packet["schema_version"]) is not int or packet["schema_version"] != 1:
        raise EvidenceRefused("unsupported_version")
    if packet["source_contract"] != "APG140-RM-MAIN-20260912":
        raise EvidenceRefused("source_identity_drift")
    if packet["scope"] != "synthetic-local" or packet["owner"] != "fixture-owner":
        raise EvidenceRefused("unqualified_scope_or_owner")
    # The source admits an exact migration-ledger prefix, not arbitrary history.
    ledger = packet["ledger"]
    if not isinstance(ledger, dict) or set(ledger) != {"applied", "expected"}:
        raise EvidenceRefused("malformed_ledger")
    applied, expected = ledger["applied"], ledger["expected"]
    if (not isinstance(applied, list) or not isinstance(expected, list)
            or not applied or len(applied) >= len(expected)
            or not all(isinstance(x, str) and x for x in expected)
            or len(set(expected)) != len(expected) or applied != expected[:len(applied)]):
        raise EvidenceRefused("diverged_schema_ledger")
    if (not isinstance(packet["backup"], dict)
            or type(packet["backup"].get("checksum_verified")) is not bool
            or type(packet["backup"].get("restore_supported")) is not bool
            or packet["backup"] != {"checksum_verified": True, "restore_supported": True,
                            "restore_rehearsal": "synthetic-success"}):
        raise EvidenceRefused("backup_restore_evidence_incomplete")
    # Reject bools explicitly; they compare equal to integer counts in Python.
    for name in ("before", "after"):
        counts = packet[name]
        if (not isinstance(counts, list) or len(counts) != 4
                or any(type(x) is not int or x < 0 for x in counts)):
            raise EvidenceRefused("malformed_identity_state")
    total, expected_rows, other_rows, current_rows = packet["before"]
    if (total <= 0 or expected_rows > 1 or other_rows != 0
            or current_rows > total or expected_rows + other_rows > total):
        raise EvidenceRefused("diverged_repository_identity")
    if packet["after"] != [1, 1, 0, 1]:
        raise EvidenceRefused("repository_identity_verification_failed")
    if packet["steps"] != ["verify-backup", "compare-schema", "add-identity",
                            "reconcile-identity", "verify-stable", "drop-legacy",
                            "verify-ledger"]:
        raise EvidenceRefused("unsafe_cutover_order")
    if packet["rollback"] != "restore-verified-backup-under-owner-authority":
        raise EvidenceRefused("rollback_unavailable")
    return "synthetic-composition-supported"


def read_packet(raw: str) -> dict:
    """Reject malformed and duplicate-key evidence before evaluating it."""
    def unique(pairs: list) -> dict:
        value = {}
        for key, item in pairs:
            if key in value:
                raise EvidenceRefused("duplicate_field")
            value[key] = item
        return value

    try:
        return json.loads(raw, object_pairs_hook=unique)
    except json.JSONDecodeError as error:
        raise EvidenceRefused("malformed_json") from error
