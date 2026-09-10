"""Unit tests for matrix receipts and completeness verification."""

from __future__ import annotations

from pathlib import Path

from release.ci.matrix_receipts import (
    DEFAULT_MEMBER_JOBS,
    emit_receipt,
    verify_matrix,
)


def test_emit_receipt_creates_valid_file(tmp_path: Path) -> None:
    p = emit_receipt("guard", tmp_path, status="success", sha="a" * 40)
    assert p.is_file()
    assert p.name == "guard-receipt.json"


def test_verify_matrix_succeeds_when_all_members_pass(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        emit_receipt(job, tmp_path, status="success", sha=sha)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is True
    assert doc["success"] is True
    assert doc["required_members_count"] == len(DEFAULT_MEMBER_JOBS)
    assert doc["verified_members_count"] == len(DEFAULT_MEMBER_JOBS)


def test_verify_matrix_rejects_missing_member(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    # Emit all except one concrete CodeQL matrix member.
    for job in DEFAULT_MEMBER_JOBS - {"codeql-go"}:
        emit_receipt(job, tmp_path, status="success", sha=sha)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("missing receipt for job: codeql-go" in err for err in doc["errors"])


def test_verify_matrix_rejects_failed_member(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        status = "failure" if job == "policy" else "success"
        emit_receipt(job, tmp_path, status=status, sha=sha)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("job policy did not succeed: status=failure" in err for err in doc["errors"])


def test_verify_matrix_rejects_cancelled_or_skipped_member(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        status = "cancelled" if job == "go" else "success"
        emit_receipt(job, tmp_path, status=status, sha=sha)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("job go did not succeed: status=cancelled" in err for err in doc["errors"])


def test_verify_matrix_rejects_sha_mismatch(tmp_path: Path) -> None:
    for job in DEFAULT_MEMBER_JOBS:
        sha = "a" * 40 if job == "guard" else "b" * 40
        emit_receipt(job, tmp_path, status="success", sha=sha)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha="b" * 40)
    assert ok is False
    assert any("SHA mismatch for job guard" in err for err in doc["errors"])


def test_verify_matrix_rejects_artifact_digest_substitution(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    # Create fake artifact file
    art_file = tmp_path / "deliverables.tar.gz"
    art_file.write_bytes(b"actual content")

    # Record wrong hash in receipt
    for job in DEFAULT_MEMBER_JOBS:
        artifacts = {"deliverables.tar.gz": "0" * 64} if job == "package" else {}
        emit_receipt(job, tmp_path, status="success", sha=sha, artifacts=artifacts)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("artifact digest substitution detected" in err for err in doc["errors"])


def test_verify_matrix_requires_explicit_needs_success(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        emit_receipt(job, tmp_path, status="success", sha=sha)

    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    statuses["codeql-actions"] = "skipped"
    ok, _msg, doc = verify_matrix(
        tmp_path, expected_sha=sha, expected_statuses=statuses
    )
    assert ok is False
    assert any("codeql-actions needs result did not succeed" in err for err in doc["errors"])


def test_downloaded_matrix_preserves_duplicate_detection(tmp_path: Path) -> None:
    sha = "c" * 40
    for job in DEFAULT_MEMBER_JOBS:
        emit_receipt(job, tmp_path / job, sha=sha)
    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    assert verify_matrix(tmp_path, expected_sha=sha, expected_statuses=statuses)[0]
    emit_receipt("guard", tmp_path / "duplicate", sha=sha)
    ok, _, doc = verify_matrix(tmp_path, expected_sha=sha, expected_statuses=statuses)
    assert not ok
    assert "duplicate receipts for job: guard" in doc["errors"]


def test_receipt_identity_and_missing_needs_are_refused(tmp_path: Path) -> None:
    import json
    sha = "d" * 40
    for job in DEFAULT_MEMBER_JOBS:
        emit_receipt(job, tmp_path, sha=sha)
    p = tmp_path / "guard-receipt.json"
    doc = json.loads(p.read_text())
    doc["job"] = "policy"
    p.write_text(json.dumps(doc))
    ok, _, result = verify_matrix(tmp_path, expected_sha=sha, expected_statuses={})
    assert not ok
    assert any("member identity mismatch" in x for x in result["errors"])
    assert any("needs result did not succeed" in x for x in result["errors"])
