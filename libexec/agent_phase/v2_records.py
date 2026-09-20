"""Typed semantic records and database persistence helpers for Request V2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import sqlite3
from typing import Any

from .persistence import (
    record_candidate,
    record_review_disposition,
    record_review_finding,
    record_review_record,
    utc_now_iso,
)
from .semantic_roles import (
    PlanProposalRecord,
)


def save_plan_candidate(
    conn: sqlite3.Connection,
    run_id: str,
    relative_path: str,
    sha256: str,
    bytes_count: int,
    provider: str,
    profile: str,
) -> PlanProposalRecord:
    now = utc_now_iso()
    cid = f"cand-{run_id}-plan"
    record = PlanProposalRecord(
        run_id=run_id,
        started_at=now,
        completed_at=now,
        candidate_id=cid,
        outcome="completed",
    )
    manifest = {
        "relative_path": relative_path,
        "sha256": sha256,
        "bytes": bytes_count,
        "provider": provider,
        "profile": profile,
        "record": record.as_dict(),
    }
    record_candidate(
        conn,
        candidate_id=cid,
        run_id=run_id,
        responsibility_name="planner",
        candidate_type="plan_material",
        manifest=manifest,
    )
    return record


def save_review(
    conn: sqlite3.Connection,
    run_id: str,
    responsibility_name: str,
    stage_name: str,
    reviewer_provider: str,
    reviewer_profile: str,
    outcome: str,
    body: str,
    findings: Sequence[Mapping[str, Any]] = (),
    candidate_id: str | None = None,
) -> str:
    review_id = f"rev-{run_id}-{stage_name}"
    record_review_record(
        conn,
        review_id=review_id,
        run_id=run_id,
        responsibility_name=responsibility_name,
        reviewer_provider=reviewer_provider,
        reviewer_profile=reviewer_profile,
        outcome=outcome,
        findings_count=len(findings),
        candidate_id=candidate_id,
    )
    for idx, f in enumerate(findings):
        fid = f"find-{review_id}-{idx + 1}"
        record_review_finding(
            conn,
            finding_id=fid,
            review_id=review_id,
            severity=f.get("severity", "advisory"),
            title=f.get("title", f"Finding {idx + 1}"),
            detail=f.get("detail") or f.get("body"),
            disposition_status=f.get("disposition_status"),
            disposition_rationale=f.get("disposition_rationale"),
        )
    return review_id


def save_disposition(
    conn: sqlite3.Connection,
    run_id: str,
    responsibility_name: str,
    review_id: str,
    outcome: str,
    rationale: str,
) -> str:
    disposition_id = f"disp-{run_id}-{responsibility_name}"
    record_review_disposition(
        conn,
        disposition_id=disposition_id,
        run_id=run_id,
        responsibility_name=responsibility_name,
        review_id=review_id,
        disposition_outcome=outcome,
        rationale=rationale,
    )
    return disposition_id
