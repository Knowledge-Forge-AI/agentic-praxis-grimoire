"""Review/source gates cannot be satisfied by producer mechanism evidence."""
from pathlib import Path
import pytest

from testing.h_eval.readiness import make_qual5_seal, verify_seal


ROOT = Path(__file__).resolve().parents[3]


def test_producer_evidence_cannot_grant_readiness():
    baseline = make_qual5_seal(ROOT)
    evidence = {"complete_execution_package": True, "runtime_manifest_complete": True,
                "dry_run": {"complete_records": 15, "provider_invocations": 0},
                "d1": {"status": "qualified", "probe_id": "APG166D-PROBE-D1", "source_identity": baseline["source_identity"]},
                "runtime_manifest_sha256": "a" * 64, "dry_run_sha256": "b" * 64, "d1_evidence_sha256": "c" * 64}
    candidate = make_qual5_seal(ROOT, evidence)
    assert candidate["prerequisites_ready"] is False
    assert "manager_review_required" in candidate["blockers"]
    assert candidate["manager_review_required"] is True
    verify_seal(ROOT, candidate)


def test_review_must_bind_current_source_and_promotion():
    with pytest.raises(ValueError, match="custody belongs to dispatcher/manager"):
        make_qual5_seal(ROOT, {}, {"disposition": "accept", "source_identity": "a" * 64,
                                  "promotion_preregistration": "accept", "evidence_sha256": "b" * 64})
