"""Unit tests for matrix receipts and completeness verification (public-pr and native profiles)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from release.ci.matrix_receipts import (
    DEFAULT_MEMBER_JOBS,
    NATIVE_MEMBER_JOBS,
    NATIVE_PRESCRIBED_ARTIFACTS,
    PRESCRIBED_JOB_ARTIFACTS,
    emit_receipt,
    main,
    verify_matrix,
)

SHA = "11223344556677889900aabbccddeeff11223344"
NATIVE = "native-qualification"
PRESCRIBED = {"public-pr": PRESCRIBED_JOB_ARTIFACTS, NATIVE: NATIVE_PRESCRIBED_ARTIFACTS}


@pytest.fixture
def native_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PR_HEAD_SHA", "1" * 40)
    monkeypatch.setenv("PR_BASE_SHA", "2" * 40)


def _emit_complete_receipt(
    job: str,
    receipt_dir: Path,
    sha: str,
    status: str = "success",
    artifacts: dict[str, str] | None = None,
    workflow: str = "public-pr",
) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    resolved_artifacts = dict(artifacts or {})
    if status == "success":
        for art_name in PRESCRIBED[workflow].get(job, ()):
            if art_name not in resolved_artifacts:
                art_file = receipt_dir / art_name
                # Payload is job independent: native lanes share one receipt directory in this helper.
                art_file.write_bytes(f"test payload for {art_name}".encode("utf-8"))
                resolved_artifacts[art_name] = hashlib.sha256(art_file.read_bytes()).hexdigest()
    return emit_receipt(
        job, receipt_dir, status=status, sha=sha, artifacts=resolved_artifacts, workflow=workflow
    )


def _emit_all(tmp_path: Path, workflow: str = "public-pr", *, skip: str | None = None,
              failed: tuple[str, ...] = ()) -> None:
    members = NATIVE_MEMBER_JOBS if workflow == NATIVE else DEFAULT_MEMBER_JOBS
    for job in sorted(members - {skip}):
        _emit_complete_receipt(job, tmp_path, SHA, "failure" if job in failed else "success", workflow=workflow)


def test_public_default_profile_has_exactly_ten_members() -> None:
    assert DEFAULT_MEMBER_JOBS == {
        "guard", "static-analysis", "policy", "unit-integration", "closure", "go",
        "codeql-go", "codeql-python", "codeql-javascript-typescript", "codeql-actions",
    }


def test_native_profile_has_exactly_nine_members_and_prescribed_files() -> None:
    assert len(NATIVE_MEMBER_JOBS) == 9
    assert NATIVE_PRESCRIBED_ARTIFACTS["native-guard"] == ("identity.json",)
    assert NATIVE_PRESCRIBED_ARTIFACTS["native-assemble"] == ("release-bundle-seal.json", "public-projection-manifest.json")
    assert NATIVE_PRESCRIBED_ARTIFACTS["native-release-scans"] == ("scan-receipt.json",)
    for lane in ("native-darwin-arm64", "native-linux-x64", "native-linux-arm64"):
        assert NATIVE_PRESCRIBED_ARTIFACTS[lane] == ("lane-seal.json",)
        assert NATIVE_PRESCRIBED_ARTIFACTS[lane.replace("native-", "native-consumer-")] == (
            "consumer-receipt.json",
        )


def test_emit_receipt_creates_valid_file(tmp_path: Path) -> None:
    p = emit_receipt("guard", tmp_path, status="success", sha="a" * 40)
    assert p.is_file()
    assert p.name == "guard-receipt.json"
    assert json.loads(p.read_text(encoding="utf-8"))["workflow"] == "public-pr"


def test_emit_receipt_requires_the_explicit_native_profile(tmp_path: Path, native_identity: None) -> None:
    with pytest.raises(ValueError, match="unknown matrix member: native-guard"):
        emit_receipt("native-guard", tmp_path, status="success", sha="a" * 40)
    with pytest.raises(ValueError, match="unknown matrix member: guard"):
        emit_receipt("guard", tmp_path, status="success", sha="a" * 40, workflow=NATIVE)
    with pytest.raises(ValueError, match="unknown workflow profile"):
        emit_receipt("guard", tmp_path, status="success", sha="a" * 40, workflow="release")
    path = emit_receipt("native-guard", tmp_path, status="success", sha="a" * 40, workflow=NATIVE)
    assert json.loads(path.read_text(encoding="utf-8"))["workflow"] == NATIVE


def test_native_success_receipt_requires_exact_pr_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PR_HEAD_SHA", raising=False)
    monkeypatch.delenv("PR_BASE_SHA", raising=False)
    with pytest.raises(ValueError, match="requires an exact PR_HEAD_SHA"):
        emit_receipt("native-guard", tmp_path, status="success", sha="a" * 40, workflow=NATIVE)
    # A red job must still always be able to record its actual status.
    path = emit_receipt("native-guard", tmp_path, status="failure", sha="a" * 40, workflow=NATIVE)
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "failure"


def test_verify_matrix_succeeds_when_all_members_pass(tmp_path: Path) -> None:
    _emit_all(tmp_path)
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is True
    assert doc["success"] is True
    assert doc["workflow"] == "public-pr"
    assert doc["required_members_count"] == len(DEFAULT_MEMBER_JOBS) == 10
    assert doc["verified_members_count"] == 10


def test_verify_matrix_rejects_missing_member(tmp_path: Path) -> None:
    _emit_all(tmp_path, skip="codeql-go")
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is False
    assert any("missing receipt for job: codeql-go" in err for err in doc["errors"])


@pytest.mark.parametrize("status", ["failure", "cancelled", "skipped"])
def test_verify_matrix_rejects_non_success_member(tmp_path: Path, status: str) -> None:
    for job in sorted(DEFAULT_MEMBER_JOBS):
        _emit_complete_receipt(job, tmp_path, SHA, status if job == "policy" else "success")
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is False
    assert any(f"job policy did not succeed: status={status}" in err for err in doc["errors"])


def test_verify_matrix_rejects_sha_mismatch(tmp_path: Path) -> None:
    for job in sorted(DEFAULT_MEMBER_JOBS):
        _emit_complete_receipt(job, tmp_path, "a" * 40 if job == "guard" else "b" * 40)
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha="b" * 40)
    assert ok is False
    assert any("SHA mismatch for job guard" in err for err in doc["errors"])


def test_verify_matrix_rejects_artifact_digest_substitution(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_bytes(b"actual content")
    for job in sorted(DEFAULT_MEMBER_JOBS):
        artifacts = {"manifest.json": "0" * 64} if job == "static-analysis" else None
        _emit_complete_receipt(job, tmp_path, SHA, artifacts=artifacts)
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is False
    assert any("artifact digest substitution detected" in err for err in doc["errors"])


def test_verify_matrix_rejects_missing_prescribed_artifact(tmp_path: Path) -> None:
    for job in sorted(DEFAULT_MEMBER_JOBS):
        if job == "static-analysis":
            emit_receipt(job, tmp_path, status="success", sha=SHA, artifacts={})
        else:
            _emit_complete_receipt(job, tmp_path, SHA)
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is False
    assert any("missing prescribed artifact for static-analysis: manifest.json" in err for err in doc["errors"])


def test_verify_matrix_requires_explicit_needs_success(tmp_path: Path) -> None:
    _emit_all(tmp_path)
    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    statuses["codeql-actions"] = "skipped"
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA, expected_statuses=statuses)
    assert ok is False
    assert doc["errors"] == [
        "matrix codeql needs result did not succeed: status=skipped; no member receipt reports failure"
    ]


def test_shared_matrix_failure_names_only_failing_member_receipts(tmp_path: Path) -> None:
    _emit_all(tmp_path, failed=("codeql-python",))
    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    for job in ("codeql-go", "codeql-python", "codeql-javascript-typescript", "codeql-actions"):
        statuses[job] = "failure"
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA, expected_statuses=statuses)
    assert ok is False
    assert sorted(doc["errors"]) == sorted([
        "job codeql-python did not succeed: status=failure",
        "matrix codeql needs result did not succeed: status=failure; failing member receipts: codeql-python",
    ])
    assert doc["member_receipt_status"]["codeql-go"] == "success"
    assert doc["member_receipt_status"]["codeql-python"] == "failure"


def test_ungrouped_needs_failure_with_green_receipt_still_fails_closed(tmp_path: Path) -> None:
    _emit_all(tmp_path)
    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    assert verify_matrix(tmp_path, expected_sha=SHA, expected_statuses=statuses)[0] is True
    statuses["static-analysis"] = "failure"
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA, expected_statuses=statuses)
    assert ok is False
    assert doc["errors"] == ["job static-analysis needs result did not succeed: status=failure"]
    assert set(doc["member_receipt_status"].values()) == {"success"}


def test_downloaded_matrix_preserves_duplicate_detection(tmp_path: Path) -> None:
    for job in DEFAULT_MEMBER_JOBS:
        _emit_complete_receipt(job, tmp_path / job, "c" * 40)
    statuses = {job: "success" for job in DEFAULT_MEMBER_JOBS}
    assert verify_matrix(tmp_path, expected_sha="c" * 40, expected_statuses=statuses)[0]
    _emit_complete_receipt("guard", tmp_path / "duplicate", "c" * 40)
    ok, _, doc = verify_matrix(tmp_path, expected_sha="c" * 40, expected_statuses=statuses)
    assert not ok
    assert "duplicate receipts for job: guard" in doc["errors"]


def test_receipt_identity_and_missing_needs_are_refused(tmp_path: Path) -> None:
    _emit_all(tmp_path)
    p = tmp_path / "guard-receipt.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["job"] = "policy"
    p.write_text(json.dumps(doc), encoding="utf-8")
    ok, _, result = verify_matrix(tmp_path, expected_sha=SHA, expected_statuses={})
    assert not ok
    assert any("member identity mismatch" in x for x in result["errors"])
    assert any("needs result did not succeed" in x for x in result["errors"])


def test_emit_receipt_allows_unavailable_artifacts_on_failure(tmp_path: Path) -> None:
    p = emit_receipt("static-analysis", tmp_path, status="failure", sha="e" * 40,
                     unavailable_artifacts=["manifest.json"])
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["status"] == "failure"
    assert doc["unavailable_artifacts"] == ["manifest.json"]


def test_emit_receipt_rejects_unavailable_artifacts_on_success(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="successful job cannot have unavailable artifacts"):
        emit_receipt("static-analysis", tmp_path, status="success", sha="e" * 40,
                     unavailable_artifacts=["manifest.json"])


def test_main_emit_handles_missing_file_on_failure(tmp_path: Path) -> None:
    receipt_dir = tmp_path / "receipts"
    code = main(["emit", "--job", "static-analysis", "--dir", str(receipt_dir), "--status", "failure",
                 "--sha", "f" * 40, "--artifact", str(tmp_path / "absent-manifest.json")])
    assert code == 0
    doc = json.loads((receipt_dir / "static-analysis-receipt.json").read_text(encoding="utf-8"))
    assert doc["status"] == "failure"
    assert doc["unavailable_artifacts"] == ["absent-manifest.json"]


def test_main_emit_refuses_missing_file_on_success(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="receipt artifact missing for successful job"):
        main(["emit", "--job", "static-analysis", "--dir", str(tmp_path / "receipts"),
              "--status", "success", "--sha", "f" * 40, "--artifact", str(tmp_path / "absent.json")])


def test_verify_matrix_rejects_success_receipt_with_unavailable_artifacts(tmp_path: Path) -> None:
    _emit_all(tmp_path)
    receipt_file = tmp_path / "static-analysis-receipt.json"
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    data["unavailable_artifacts"] = ["some-unavailable-artifact.json"]
    receipt_file.write_text(json.dumps(data), encoding="utf-8")
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is False
    assert any("successful job static-analysis contains unavailable artifacts: "
               "['some-unavailable-artifact.json']" in err for err in doc["errors"])


def test_verify_matrix_rejects_malformed_unavailable_artifacts(tmp_path: Path) -> None:
    _emit_all(tmp_path)
    receipt_file = tmp_path / "guard-receipt.json"
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    data["unavailable_artifacts"] = "not-a-list"
    receipt_file.write_text(json.dumps(data), encoding="utf-8")
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is False
    assert any("malformed unavailable_artifacts for job: guard" in err for err in doc["errors"])


def test_verify_matrix_rejects_workflow_digest_tamper(tmp_path: Path) -> None:
    _emit_all(tmp_path)
    receipt_file = tmp_path / "go-receipt.json"
    data = json.loads(receipt_file.read_text(encoding="utf-8"))
    data["workflow_sha256"] = "0" * 64
    receipt_file.write_text(json.dumps(data), encoding="utf-8")
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is False
    assert doc["errors"] == ["workflow policy digest mismatch for job go"]


def test_verify_matrix_refuses_a_missing_workflow_policy_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import release.ci.matrix_receipts as module

    _emit_all(tmp_path)
    monkeypatch.setitem(module.PROFILES, "public-pr", module.ProfileConfig(
        "public-pr", tmp_path / "absent.yml", module.PUBLIC_PR_MEMBER_JOBS, {}, {},
    ))
    ok, msg, _doc = verify_matrix(tmp_path, expected_sha=SHA)
    assert ok is False
    assert "workflow policy file missing" in msg


def test_native_matrix_succeeds_with_all_nine_members(tmp_path: Path, native_identity: None) -> None:
    _emit_all(tmp_path, NATIVE)
    statuses = {job: "success" for job in NATIVE_MEMBER_JOBS}
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA, expected_statuses=statuses, workflow=NATIVE)
    assert ok is True, doc["errors"]
    assert doc["workflow"] == NATIVE
    assert doc["verified_members_count"] == 9


def test_native_receipts_do_not_satisfy_the_public_profile_and_vice_versa(
    tmp_path: Path, native_identity: None
) -> None:
    _emit_all(tmp_path / "native", NATIVE)
    ok, _msg, doc = verify_matrix(tmp_path / "native", expected_sha=SHA)
    assert ok is False
    assert any("unexpected receipt for job: native-guard" in err for err in doc["errors"])
    _emit_all(tmp_path / "public")
    ok, _msg, doc = verify_matrix(tmp_path / "public", expected_sha=SHA, workflow=NATIVE)
    assert ok is False
    assert any("unexpected receipt for job: guard" in err for err in doc["errors"])
    assert any("missing receipt for job: native-guard" in err for err in doc["errors"])


@pytest.mark.parametrize("job", sorted(NATIVE_MEMBER_JOBS))
def test_native_matrix_rejects_each_missing_or_red_member(
    tmp_path: Path, native_identity: None, job: str
) -> None:
    _emit_all(tmp_path / "missing", NATIVE, skip=job)
    ok, _msg, doc = verify_matrix(tmp_path / "missing", expected_sha=SHA, workflow=NATIVE)
    assert not ok and f"missing receipt for job: {job}" in doc["errors"]
    _emit_all(tmp_path / "red", NATIVE, failed=(job,))
    ok, _msg, doc = verify_matrix(tmp_path / "red", expected_sha=SHA, workflow=NATIVE)
    assert not ok and f"job {job} did not succeed: status=failure" in doc["errors"]


@pytest.mark.parametrize("job", sorted(NATIVE_MEMBER_JOBS))
def test_native_matrix_requires_each_prescribed_artifact_file(
    tmp_path: Path, native_identity: None, job: str
) -> None:
    for member in sorted(NATIVE_MEMBER_JOBS):
        if member == job:
            emit_receipt(member, tmp_path, status="success", sha=SHA, artifacts={}, workflow=NATIVE)
        else:
            _emit_complete_receipt(member, tmp_path, SHA, workflow=NATIVE)
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA, workflow=NATIVE)
    artifact = NATIVE_PRESCRIBED_ARTIFACTS[job][0]
    assert not ok and f"missing prescribed artifact for {job}: {artifact}" in doc["errors"]


def test_native_matrix_rejects_artifact_substitution_and_deletion(
    tmp_path: Path, native_identity: None
) -> None:
    _emit_all(tmp_path, NATIVE)
    (tmp_path / "scan-receipt.json").write_bytes(b"substituted")
    (tmp_path / "identity.json").unlink()
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA, workflow=NATIVE)
    assert not ok
    assert any("digest substitution detected for native-release-scans artifact scan-receipt.json" in e
               for e in doc["errors"])
    assert "missing receipt artifact for native-guard: identity.json" in doc["errors"]


def test_native_matrix_binds_workflow_digest_profile_and_identity(
    tmp_path: Path, native_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _emit_all(tmp_path, NATIVE)
    guard = tmp_path / "native-guard-receipt.json"
    data = json.loads(guard.read_text(encoding="utf-8"))
    data["workflow_sha256"] = "0" * 64
    guard.write_text(json.dumps(data), encoding="utf-8")
    lane = tmp_path / "native-linux-x64-receipt.json"
    data = json.loads(lane.read_text(encoding="utf-8"))
    data["workflow"] = "public-pr"
    lane.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("PR_BASE_SHA", "3" * 40)
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA, workflow=NATIVE)
    assert not ok
    assert "workflow policy digest mismatch for job native-guard" in doc["errors"]
    assert "receipt workflow profile mismatch for job: native-linux-x64" in doc["errors"]
    assert "pr_base_sha mismatch for job native-assemble" in doc["errors"]


def test_native_matrix_refuses_verification_without_pr_identity(
    tmp_path: Path, native_identity: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _emit_all(tmp_path, NATIVE)
    monkeypatch.delenv("PR_HEAD_SHA")
    ok, msg, _doc = verify_matrix(tmp_path, expected_sha=SHA, workflow=NATIVE)
    assert not ok and "requires an exact PR_HEAD_SHA" in msg


def test_native_matrix_rejects_failed_needs_despite_green_receipt(
    tmp_path: Path, native_identity: None
) -> None:
    _emit_all(tmp_path, NATIVE)
    statuses = {job: "success" for job in NATIVE_MEMBER_JOBS}
    statuses["native-assemble"] = "cancelled"
    ok, _msg, doc = verify_matrix(tmp_path, expected_sha=SHA, expected_statuses=statuses, workflow=NATIVE)
    assert not ok
    assert doc["errors"] == ["job native-assemble needs result did not succeed: status=cancelled"]


def test_native_cli_emit_records_red_status_and_verify_uses_the_profile(
    tmp_path: Path, native_identity: None, capsys: pytest.CaptureFixture[str]
) -> None:
    receipts = tmp_path / "receipts"
    code = main(["emit", "--workflow", NATIVE, "--job", "native-linux-x64", "--dir", str(receipts),
                 "--status", "failure", "--sha", SHA, "--artifact", str(tmp_path / "absent" / "lane-seal.json")])
    assert code == 0
    doc = json.loads((receipts / "native-linux-x64-receipt.json").read_text(encoding="utf-8"))
    assert (doc["workflow"], doc["status"]) == (NATIVE, "failure")
    assert doc["unavailable_artifacts"] == ["lane-seal.json"]
    statuses = json.dumps({job: "success" for job in NATIVE_MEMBER_JOBS})
    assert main(["verify", "--workflow", NATIVE, "--dir", str(receipts), "--sha", SHA,
                 "--statuses-json", statuses]) == 1
    assert "FAILED: matrix verification failed" in capsys.readouterr().err
