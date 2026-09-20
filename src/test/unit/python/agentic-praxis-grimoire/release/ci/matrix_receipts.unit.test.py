"""Unit tests for matrix receipts and completeness verification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from release.ci.matrix_receipts import (
    DEFAULT_MEMBER_JOBS,
    PRESCRIBED_JOB_ARTIFACTS,
    emit_receipt,
    main,
    verify_matrix,
)


def _emit_complete_receipt(
    job: str,
    receipt_dir: Path,
    sha: str,
    status: str = "success",
    artifacts: dict[str, str] | None = None,
) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    resolved_artifacts = dict(artifacts or {})
    if status == "success":
        for art_name in PRESCRIBED_JOB_ARTIFACTS.get(job, ()):
            if art_name not in resolved_artifacts:
                art_file = receipt_dir / art_name
                if not art_file.exists():
                    art_file.write_bytes(f"test payload for {job} {art_name}".encode("utf-8"))
                resolved_artifacts[art_name] = hashlib.sha256(art_file.read_bytes()).hexdigest()
    return emit_receipt(job, receipt_dir, status=status, sha=sha, artifacts=resolved_artifacts)


def test_emit_receipt_creates_valid_file(tmp_path: Path) -> None:
    p = emit_receipt("guard", tmp_path, status="success", sha="a" * 40)
    assert p.is_file()
    assert p.name == "guard-receipt.json"


def test_verify_matrix_succeeds_when_all_members_pass(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success")

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is True
    assert doc["success"] is True
    assert doc["required_members_count"] == len(DEFAULT_MEMBER_JOBS)
    assert doc["verified_members_count"] == len(DEFAULT_MEMBER_JOBS)


def test_verify_matrix_rejects_missing_member(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    # Emit all except one concrete CodeQL matrix member.
    for job in DEFAULT_MEMBER_JOBS - {"codeql-go"}:
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success")

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("missing receipt for job: codeql-go" in err for err in doc["errors"])


def test_verify_matrix_rejects_failed_member(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        status = "failure" if job == "policy" else "success"
        _emit_complete_receipt(job, tmp_path, sha=sha, status=status)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("job policy did not succeed: status=failure" in err for err in doc["errors"])


def test_verify_matrix_rejects_cancelled_or_skipped_member(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        status = "cancelled" if job == "go" else "success"
        _emit_complete_receipt(job, tmp_path, sha=sha, status=status)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("job go did not succeed: status=cancelled" in err for err in doc["errors"])


def test_verify_matrix_rejects_sha_mismatch(tmp_path: Path) -> None:
    for job in DEFAULT_MEMBER_JOBS:
        sha = "a" * 40 if job == "guard" else "b" * 40
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success")

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha="b" * 40)
    assert ok is False
    assert any("SHA mismatch for job guard" in err for err in doc["errors"])


def test_verify_matrix_rejects_artifact_digest_substitution(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    # Create fake artifact file with valid prescribed name
    art_file = tmp_path / "apg-distribution-manifest.json"
    art_file.write_bytes(b"actual content")

    # Record wrong hash in receipt
    for job in DEFAULT_MEMBER_JOBS:
        artifacts = {"apg-distribution-manifest.json": "0" * 64} if job == "package" else None
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success", artifacts=artifacts)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("artifact digest substitution detected" in err for err in doc["errors"])


def test_verify_matrix_rejects_missing_prescribed_artifact(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        if job == "package":
            emit_receipt(job, tmp_path, status="success", sha=sha, artifacts={})
        else:
            _emit_complete_receipt(job, tmp_path, sha=sha, status="success")

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("missing prescribed artifact for package: apg-distribution-manifest.json" in err for err in doc["errors"])


def test_verify_matrix_requires_explicit_needs_success(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success")

    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    statuses["codeql-actions"] = "skipped"
    ok, _msg, doc = verify_matrix(
        tmp_path, expected_sha=sha, expected_statuses=statuses
    )
    assert ok is False
    assert doc["errors"] == [
        "matrix codeql needs result did not succeed: status=skipped; no member receipt reports failure"
    ]


def test_shared_matrix_failure_names_only_failing_member_receipts(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        failed = job in {"codeql-python", "nix-x86_64-linux"}
        _emit_complete_receipt(job, tmp_path, sha=sha, status="failure" if failed else "success")
    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    for job in ("codeql-go", "codeql-python", "codeql-javascript-typescript", "codeql-actions",
                "nix-x86_64-linux", "nix-aarch64-darwin"):
        statuses[job] = "failure"
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha, expected_statuses=statuses)
    assert ok is False
    assert sorted(doc["errors"]) == sorted([
        "job codeql-python did not succeed: status=failure",
        "job nix-x86_64-linux did not succeed: status=failure",
        "matrix codeql needs result did not succeed: status=failure; failing member receipts: codeql-python",
        "matrix nix needs result did not succeed: status=failure; failing member receipts: nix-x86_64-linux",
    ])
    assert doc["member_receipt_status"]["codeql-go"] == "success"
    assert doc["member_receipt_status"]["nix-aarch64-darwin"] == "success"
    assert doc["member_receipt_status"]["codeql-python"] == "failure"
    assert not any("codeql-go" in err or "aarch64-darwin" in err for err in doc["errors"])


def test_ungrouped_needs_failure_with_green_receipt_still_fails_closed(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success")
    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    assert verify_matrix(tmp_path, expected_sha=sha, expected_statuses=statuses)[0] is True
    statuses["static-analysis"] = "failure"
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha, expected_statuses=statuses)
    assert ok is False
    assert doc["errors"] == ["job static-analysis needs result did not succeed: status=failure"]
    assert set(doc["member_receipt_status"].values()) == {"success"}


def test_downloaded_matrix_preserves_duplicate_detection(tmp_path: Path) -> None:
    sha = "c" * 40
    for job in DEFAULT_MEMBER_JOBS:
        _emit_complete_receipt(job, tmp_path / job, sha=sha)
    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    assert verify_matrix(tmp_path, expected_sha=sha, expected_statuses=statuses)[0]
    _emit_complete_receipt("guard", tmp_path / "duplicate", sha=sha)
    ok, _, doc = verify_matrix(tmp_path, expected_sha=sha, expected_statuses=statuses)
    assert not ok
    assert "duplicate receipts for job: guard" in doc["errors"]


def test_receipt_identity_and_missing_needs_are_refused(tmp_path: Path) -> None:
    sha = "d" * 40
    for job in DEFAULT_MEMBER_JOBS:
        _emit_complete_receipt(job, tmp_path, sha=sha)
    p = tmp_path / "guard-receipt.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["job"] = "policy"
    p.write_text(json.dumps(doc), encoding="utf-8")
    ok, _, result = verify_matrix(tmp_path, expected_sha=sha, expected_statuses={})
    assert not ok
    assert any("member identity mismatch" in x for x in result["errors"])
    assert any("needs result did not succeed" in x for x in result["errors"])


def test_emit_receipt_allows_unavailable_artifacts_on_failure(tmp_path: Path) -> None:
    p = emit_receipt(
        "package",
        tmp_path,
        status="failure",
        sha="e" * 40,
        unavailable_artifacts=["apg-distribution-manifest.json"],
    )
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["status"] == "failure"
    assert doc["unavailable_artifacts"] == ["apg-distribution-manifest.json"]


def test_emit_receipt_rejects_unavailable_artifacts_on_success(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="successful job cannot have unavailable artifacts"):
        emit_receipt(
            "package",
            tmp_path,
            status="success",
            sha="e" * 40,
            unavailable_artifacts=["apg-distribution-manifest.json"],
        )


def test_main_emit_handles_missing_file_on_failure(tmp_path: Path) -> None:
    missing = tmp_path / "absent-manifest.json"
    receipt_dir = tmp_path / "receipts"
    code = main([
        "emit",
        "--job", "package",
        "--dir", str(receipt_dir),
        "--status", "failure",
        "--sha", "f" * 40,
        "--artifact", str(missing),
    ])
    assert code == 0
    p = receipt_dir / "package-receipt.json"
    assert p.is_file()
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["status"] == "failure"
    assert doc["unavailable_artifacts"] == ["absent-manifest.json"]


def test_main_emit_refuses_missing_file_on_success(tmp_path: Path) -> None:
    missing = tmp_path / "absent-manifest.json"
    receipt_dir = tmp_path / "receipts"
    with pytest.raises(ValueError, match="receipt artifact missing for successful job"):
        main([
            "emit",
            "--job", "package",
            "--dir", str(receipt_dir),
            "--status", "success",
            "--sha", "f" * 40,
            "--artifact", str(missing),
        ])


def test_verify_matrix_rejects_success_receipt_with_unavailable_artifacts(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success")

    # Contradictory success receipt: prescribed artifacts are present on disk and valid,
    # but unavailable_artifacts is non-empty.
    receipt_file = tmp_path / "package-receipt.json"
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    data["unavailable_artifacts"] = ["some-unavailable-artifact.json"]
    receipt_file.write_text(json.dumps(data), encoding="utf-8")

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("successful job package contains unavailable artifacts: ['some-unavailable-artifact.json']" in err for err in doc["errors"])


def test_verify_matrix_rejects_success_receipt_with_malformed_unavailable_artifacts(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success")

    receipt_file = tmp_path / "guard-receipt.json"
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    data["unavailable_artifacts"] = "not-a-list"
    receipt_file.write_text(json.dumps(data), encoding="utf-8")

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("malformed unavailable_artifacts for job: guard" in err for err in doc["errors"])


def test_emit_receipt_creates_valid_nix_receipts(tmp_path: Path) -> None:
    p_linux = emit_receipt("nix-x86_64-linux", tmp_path, status="success", sha="a" * 40)
    assert p_linux.is_file()
    assert p_linux.name == "nix-x86_64-linux-receipt.json"

    p_darwin = emit_receipt("nix-aarch64-darwin", tmp_path, status="success", sha="a" * 40)
    assert p_darwin.is_file()
    assert p_darwin.name == "nix-aarch64-darwin-receipt.json"


def test_verify_matrix_rejects_missing_nix_member(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS - {"nix-x86_64-linux"}:
        _emit_complete_receipt(job, tmp_path, sha=sha, status="success")

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("missing receipt for job: nix-x86_64-linux" in err for err in doc["errors"])


def test_verify_matrix_rejects_failed_nix_member(tmp_path: Path) -> None:
    sha = "11223344556677889900aabbccddeeff11223344"
    for job in DEFAULT_MEMBER_JOBS:
        status = "failure" if job == "nix-aarch64-darwin" else "success"
        _emit_complete_receipt(job, tmp_path, sha=sha, status=status)

    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=sha)
    assert ok is False
    assert any("job nix-aarch64-darwin did not succeed: status=failure" in err for err in doc["errors"])

