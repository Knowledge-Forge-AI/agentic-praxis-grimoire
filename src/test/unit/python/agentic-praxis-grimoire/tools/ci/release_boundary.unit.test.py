"""Unit tests for tools/ci release boundary modules."""

from __future__ import annotations

import copy
import io
import json
import zipfile
from unittest import mock

import pytest

from src.test.support import release_boundary_fixtures as fix
from tools.ci import release_boundary_bundle as bundle
from tools.ci import release_boundary_github as gh


# 1. Bundle and Mapping Tests
def test_logical_path_to_flat_name_mapping() -> None:
    logical_paths = bundle.canonical_logical_paths("0.13.0")
    assert len(logical_paths) == 15

    flat_names = [bundle.logical_path_to_flat_name(p, "0.13.0") for p in logical_paths]
    assert len(flat_names) == 15
    assert len(set(flat_names)) == 15

    # Verify Go flat names
    assert bundle.logical_path_to_flat_name("go/darwin-arm64/apgr") == "apgr-darwin-arm64"
    assert bundle.logical_path_to_flat_name("go/darwin-arm64/apgr.binary-manifest.json") == "apgr-darwin-arm64.binary-manifest.json"
    assert bundle.logical_path_to_flat_name("go/linux-amd64/apgr") == "apgr-linux-amd64"
    assert bundle.logical_path_to_flat_name("go/linux-arm64/apgr") == "apgr-linux-arm64"

    # Full set of 16 flat assets including SHA256SUMS
    full_flat = bundle.canonical_flat_assets("0.13.0")
    assert len(full_flat) == 16
    assert "SHA256SUMS" in full_flat
    assert len(set(full_flat)) == 16

    # Rejection of unmapped logical paths
    with pytest.raises(bundle.BoundaryBundleError, match="unrecognized Go logical path"):
        bundle.logical_path_to_flat_name("go/darwin-arm64/unknown")
    with pytest.raises(bundle.BoundaryBundleError, match="unrecognized logical path"):
        bundle.logical_path_to_flat_name("rust/apgr")


def test_self_hash_computation_and_tamper_detection() -> None:
    doc = {"schema": "test/v1", "name": "sample", "value": 123}
    bundle.finalize_self_hash(doc)
    assert "self_sha256" in doc
    recorded_hash = doc["self_sha256"]

    # Validating intact doc must succeed
    assert bundle.validate_self_hash(doc) == recorded_hash

    # Tampering doc must raise
    tampered = copy.deepcopy(doc)
    tampered["value"] = 456
    with pytest.raises(bundle.BoundaryBundleError, match="tampered"):
        bundle.validate_self_hash(tampered)

    # Missing or invalid hash field must raise
    missing = copy.deepcopy(doc)
    del missing["self_sha256"]
    with pytest.raises(bundle.BoundaryBundleError, match="lacks a valid self_sha256"):
        bundle.validate_self_hash(missing)

    invalid_hex = copy.deepcopy(doc)
    invalid_hex["self_sha256"] = "not-a-valid-hex-digest"
    with pytest.raises(bundle.BoundaryBundleError, match="lacks a valid self_sha256"):
        bundle.validate_self_hash(invalid_hex)


def test_safe_member_path_and_archive_security() -> None:
    assert bundle.safe_member_path("foo/bar.txt") == "foo/bar.txt"

    invalid_names = [
        "/etc/passwd",
        "../escape",
        "foo/../../escape",
        "foo\\bar",
        "foo\x00bar",
        "C:file.txt",
        "",
        ".",
    ]
    for bad in invalid_names:
        with pytest.raises(bundle.BoundaryBundleError, match="unsafe archive member path"):
            bundle.safe_member_path(bad)

    # Non-regular ZIP member (symlink)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("symlink.txt")
        info.create_system = 3  # Unix
        info.external_attr = 0o120777 << 16  # S_IFLNK
        zf.writestr(info, "target.txt")

    with pytest.raises(bundle.BoundaryBundleError, match="non-regular member"):
        bundle.inspect_zip_bytes(buf.getvalue())


def test_verify_bundle_contents_truthful_17_files() -> None:
    zip_bytes, _sums_map, _file_bytes, seal_doc = fix.build_test_bundle_zip("0.13.0")
    members = bundle.inspect_zip_bytes(zip_bytes)
    assert len(members) == 17  # 15 logical + SHA256SUMS + release-bundle-seal.json

    # Without index
    res = bundle.verify_bundle_contents(members, "0.13.0")
    assert res["asset_count"] == 16
    assert res["checksum_row_count"] == 15
    assert len(res["mapping"]) == 16
    assert res["mapping"]["SHA256SUMS"]["flat_name"] == "SHA256SUMS"

    # With index
    _, _index_doc = fix.build_test_gate_index_zip(
        bundle_digest=f"sha256:{bundle.sha256_bytes(zip_bytes)}",
        bundle_seal=seal_doc,
        bundle_zip_bytes=zip_bytes,
    )
    res_idx = bundle.verify_bundle_contents(members, "0.13.0", index=_index_doc)
    assert res_idx["asset_count"] == 16

    # Missing member fails
    broken_members = copy.deepcopy(members)
    del broken_members["go/darwin-arm64/apgr"]
    with pytest.raises(bundle.BoundaryBundleError, match="bundle archive file inventory mismatch"):
        bundle.verify_bundle_contents(broken_members, "0.13.0")

    # Extra member fails
    extra_members = copy.deepcopy(members)
    extra_members["unexpected.txt"] = (bundle.sha256_bytes(b"extra"), len(b"extra"), b"extra")
    with pytest.raises(bundle.BoundaryBundleError, match="bundle archive file inventory mismatch"):
        bundle.verify_bundle_contents(extra_members, "0.13.0")

    # Tampered file hash fails against SHA256SUMS
    tampered_members = copy.deepcopy(members)
    tampered_members["go/darwin-arm64/apgr"] = (bundle.sha256_bytes(b"bad"), len(b"bad"), b"bad")
    with pytest.raises(bundle.BoundaryBundleError, match="bundle sealed inventory or assets mismatch"):
        bundle.verify_bundle_contents(tampered_members, "0.13.0")

    # Tampered seal self-hash fails
    tampered_seal_members = copy.deepcopy(members)
    tampered_seal = copy.deepcopy(seal_doc)
    tampered_seal["source_commit"] = "0" * 40
    raw_bad_seal = bundle.canonical_json(tampered_seal)
    tampered_seal_members["release-bundle-seal.json"] = (bundle.sha256_bytes(raw_bad_seal), len(raw_bad_seal), raw_bad_seal)
    with pytest.raises(bundle.BoundaryBundleError, match="bundle seal bundle_seal_sha256 mismatch"):
        bundle.verify_bundle_contents(tampered_seal_members, "0.13.0")

    # Source commit / tree mismatch against RC index
    bad_index = copy.deepcopy(_index_doc)
    bad_index["source_commit"] = "a" * 40
    with pytest.raises(bundle.BoundaryBundleError, match="bundle seal source identity differs from RC index"):
        bundle.verify_bundle_contents(members, "0.13.0", index=bad_index)


def test_sha256sums_parsing_failures() -> None:
    # Malformed row
    with pytest.raises(bundle.BoundaryBundleError, match="malformed SHA256SUMS row"):
        bundle.parse_sha256sums("bad-format\n")

    # Duplicate logical path
    dup = f"{'a'*64}  go/darwin-arm64/apgr\n{'b'*64}  go/darwin-arm64/apgr\n"
    with pytest.raises(bundle.BoundaryBundleError, match="duplicate logical path in SHA256SUMS"):
        bundle.parse_sha256sums(dup)


def test_release_notes_formatting_and_parsing() -> None:
    cand = {"schema": bundle.CANDIDATE_ATTESTATION_SCHEMA, "version": "0.13.0", "run_id": "123"}
    bundle.finalize_self_hash(cand)
    cand_hash = cand["self_sha256"]

    merged = {
        "schema": bundle.MERGED_ATTESTATION_SCHEMA,
        "candidate_attestation_sha256": cand_hash,
        "version": "0.13.0",
    }
    bundle.finalize_self_hash(merged)

    waiver = fix.make_governance_waiver()
    cand["governance"] = {"waiver_sha256": waiver["self_sha256"]}
    bundle.finalize_self_hash(cand)
    merged["candidate_attestation_sha256"] = cand["self_sha256"]
    bundle.finalize_self_hash(merged)

    notes = bundle.format_release_notes(cand, merged, waiver)
    assert f"Candidate-Attestation-SHA256: {cand['self_sha256']}" in notes

    parsed = bundle.parse_release_notes(notes)
    assert parsed["candidate_attestation_sha256"] == cand["self_sha256"]
    assert parsed["merged_attestation_sha256"] == merged["self_sha256"]
    assert parsed["governance_waiver"]["self_sha256"] == waiver["self_sha256"]

    # Tampered candidate doc fails
    bad_notes = notes.replace('"run_id":"123"', '"run_id":"999"')
    with pytest.raises(bundle.BoundaryBundleError, match="tampered"):
        bundle.parse_release_notes(bad_notes)

    # Missing hash header fails
    no_header = "\n".join(line for line in notes.splitlines() if "Candidate-Attestation-SHA256:" not in line)
    with pytest.raises(bundle.BoundaryBundleError, match="lack a valid Candidate-Attestation-SHA256"):
        bundle.parse_release_notes(no_header)

    # Mismatched candidate binding in merged attestation fails
    bad_merged_cand = copy.deepcopy(merged)
    bad_merged_cand["candidate_attestation_sha256"] = "0" * 64
    bundle.finalize_self_hash(bad_merged_cand)
    notes_bad_binding = bundle.format_release_notes(cand, bad_merged_cand, waiver)
    with pytest.raises(bundle.BoundaryBundleError, match="merged attestation candidate binding mismatch"):
        bundle.parse_release_notes(notes_bad_binding)


# 2. GitHub Client & Seam Tests
def test_github_client_seam_and_redirect_credentials() -> None:
    fake_gh = fix.FakeGitHub()
    client = gh.GitHubClient(token="secret-token")

    # Non-HTTPS URL rejected
    with (
        pytest.raises(gh.GitHubBoundaryError, match='HTTPS'),
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
    ):
        client.get_json("http://api.github.com/repos/Knowledge-Forge-AI/agentic-praxis-grimoire/pulls/1")

    # URL outside fixed repo rejected
    with (
        pytest.raises(gh.GitHubBoundaryError, match='outside Knowledge-Forge-AI/agentic-praxis-grimoire'),
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
    ):
        client.get_json("https://api.github.com/repos/attacker/evil-repo/pulls/1")

    # Redirect handling: credentials stripped on redirect
    orig_url = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/redirect-source"
    target_url = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/redirect-target"
    fake_gh.set_redirect(orig_url, target_url, code=302)
    fake_gh.set_json(target_url, {"success": True})

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        resp = client.get_json(orig_url)
        assert resp["success"] is True

    # Check that initial request had Authorization and redirect did NOT forward it
    assert len(fake_gh.calls) == 2
    assert fake_gh.call_headers[0].get("Authorization") == "Bearer secret-token"
    assert "Authorization" not in fake_gh.call_headers[1]

    # Redirect target non-HTTPS rejected
    non_https_redir = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/bad-redir"
    fake_gh.set_redirect(non_https_redir, "http://insecure.target/api", code=302)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='redirect target is missing or not HTTPS'),
    ):
        client.get_json(non_https_redir)

    # Exceeded redirect limit
    u0 = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/loop0"
    u1 = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/loop1"
    u2 = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/loop2"
    u3 = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/loop3"
    u4 = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/loop4"
    fake_gh.set_redirect(u0, u1)
    fake_gh.set_redirect(u1, u2)
    fake_gh.set_redirect(u2, u3)
    fake_gh.set_redirect(u3, u4)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='exceeded redirect limit'),
    ):
        client.get_json(u0)


# 3. Pull Request and Commits Tests
def test_verify_pull_request_success_and_failures() -> None:
    fake_gh = fix.FakeGitHub()
    client = gh.GitHubClient()
    api = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}"

    valid_pr = {
        "number": 3,
        "state": "open",
        "merged": False,
        "merge_commit_sha": fix.MERGE_SHA,
        "base": {"ref": "main", "sha": fix.BASE_SHA, "repo": {"id": gh.EXPECTED_REPO_ID, "full_name": gh.EXPECTED_REPO}},
        "head": {"ref": "staging", "sha": fix.HEAD_SHA, "repo": {"id": gh.EXPECTED_REPO_ID, "full_name": gh.EXPECTED_REPO}},
        "user": {"login": fix.AUTHOR_LOGIN},
    }
    fake_gh.set_json(f"{api}/pulls/3", valid_pr)

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        pr = gh.verify_pull_request(client, 3, fix.HEAD_SHA, fix.BASE_SHA)
        assert pr["number"] == 3

    # PR base ref mismatch
    bad_base_ref = copy.deepcopy(valid_pr)
    bad_base_ref["base"]["ref"] = "master"
    fake_gh.set_json(f"{api}/pulls/3", bad_base_ref)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match="PR base ref must be 'main'"),
    ):
        gh.verify_pull_request(client, 3, fix.HEAD_SHA, fix.BASE_SHA)

    # PR head ref mismatch
    bad_head_ref = copy.deepcopy(valid_pr)
    bad_head_ref["head"]["ref"] = "feature"
    fake_gh.set_json(f"{api}/pulls/3", bad_head_ref)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match="PR head ref must be 'staging'"),
    ):
        gh.verify_pull_request(client, 3, fix.HEAD_SHA, fix.BASE_SHA)

    # PR repo ID mismatch (fork or spoofed)
    bad_repo_id = copy.deepcopy(valid_pr)
    bad_repo_id["head"]["repo"]["id"] = 999999
    fake_gh.set_json(f"{api}/pulls/3", bad_repo_id)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='PR repository ID mismatch'),
    ):
        gh.verify_pull_request(client, 3, fix.HEAD_SHA, fix.BASE_SHA)

    # PR head SHA mismatch
    fake_gh.set_json(f"{api}/pulls/3", valid_pr)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='PR head SHA mismatch'),
    ):
        gh.verify_pull_request(client, 3, "0" * 40, fix.BASE_SHA)


def test_verify_commit_parents_tree_failures() -> None:
    fake_gh = fix.FakeGitHub()
    client = gh.GitHubClient()
    api = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}"

    # Commit with wrong parents
    fake_gh.set_json(f"{api}/git/commits/{fix.MERGE_SHA}", {
        "sha": fix.MERGE_SHA,
        "parents": [{"sha": fix.BASE_SHA}],  # Missing head parent
        "tree": {"sha": fix.TREE_SHA},
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='parents mismatch'),
    ):
        gh.verify_commit_parents_tree(client, fix.MERGE_SHA, [fix.BASE_SHA, fix.HEAD_SHA])

    # Commit with wrong tree
    fake_gh.set_json(f"{api}/git/commits/{fix.MERGE_SHA}", {
        "sha": fix.MERGE_SHA,
        "parents": [{"sha": fix.BASE_SHA}, {"sha": fix.HEAD_SHA}],
        "tree": {"sha": "0" * 40},
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='tree mismatch'),
    ):
        gh.verify_commit_parents_tree(client, fix.MERGE_SHA, [fix.BASE_SHA, fix.HEAD_SHA], expected_tree=fix.TREE_SHA)


# 4. Workflow Run and Jobs Tests
def test_verify_workflow_run_success_and_failures() -> None:
    fake_gh = fix.FakeGitHub()
    client = gh.GitHubClient()
    api = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}"

    valid_run = {
        "id": int(fix.PUBLIC_RUN_ID),
        "run_attempt": 1,
        "workflow_id": 7001,
        "check_suite_id": 7101,
        "status": "completed",
        "conclusion": "success",
        "head_sha": fix.HEAD_SHA,
        "head_branch": "staging",
        "path": ".github/workflows/public-pr.yml",
        "event": "pull_request",
        "repository": {"id": gh.EXPECTED_REPO_ID, "full_name": gh.EXPECTED_REPO},
        "head_repository": {"id": gh.EXPECTED_REPO_ID, "full_name": gh.EXPECTED_REPO},
        "pull_requests": [{"number": 3, "head": {"sha": fix.HEAD_SHA}, "base": {"sha": fix.BASE_SHA}}],
    }
    fake_gh.set_json(f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}", valid_run)
    fake_gh.set_json(f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}/jobs?per_page=100", {
        "total_count": len(gh.REQUIRED_PR_JOBS),
        "jobs": [{"name": j, "status": "completed", "conclusion": "success"} for j in sorted(gh.REQUIRED_PR_JOBS)],
    })

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        _run, jobs = gh.verify_workflow_run(client, fix.PUBLIC_RUN_ID, fix.HEAD_SHA, gh.REQUIRED_PR_JOBS, "public PR", fix.BASE_SHA)
        assert len(jobs) == len(gh.REQUIRED_PR_JOBS)

    # Incomplete jobs readback (total_count mismatch)
    fake_gh.set_json(f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}/jobs?per_page=100", {
        "total_count": 999,
        "jobs": [{"name": j, "status": "completed", "conclusion": "success"} for j in sorted(gh.REQUIRED_PR_JOBS)],
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='incomplete jobs readback'),
    ):
        gh.verify_workflow_run(client, fix.PUBLIC_RUN_ID, fix.HEAD_SHA, gh.REQUIRED_PR_JOBS, "public PR")

    # Duplicate job in jobs list
    dup_jobs = [{"name": j, "status": "completed", "conclusion": "success"} for j in sorted(gh.REQUIRED_PR_JOBS)]
    dup_jobs.append(dup_jobs[0])
    fake_gh.set_json(f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}/jobs?per_page=100", {
        "total_count": len(dup_jobs),
        "jobs": dup_jobs,
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='duplicate workflow job'),
    ):
        gh.verify_workflow_run(client, fix.PUBLIC_RUN_ID, fix.HEAD_SHA, gh.REQUIRED_PR_JOBS, "public PR")

    # Failed job
    failed_jobs = [{"name": j, "status": "completed", "conclusion": "success"} for j in sorted(gh.REQUIRED_PR_JOBS)]
    failed_jobs[0]["conclusion"] = "failure"
    fake_gh.set_json(f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}/jobs?per_page=100", {
        "total_count": len(failed_jobs),
        "jobs": failed_jobs,
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='not successful'),
    ):
        gh.verify_workflow_run(client, fix.PUBLIC_RUN_ID, fix.HEAD_SHA, gh.REQUIRED_PR_JOBS, "public PR")


# 5. Check Contexts & App Tests
def test_verify_check_contexts_app_source() -> None:
    fake_gh = fix.FakeGitHub()
    client = gh.GitHubClient()
    api = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}"

    contexts = frozenset({"public-pr-gate", "native-release-candidate-gate"})
    expected_runs = {"public-pr-gate": fix.PUBLIC_RUN_ID, "native-release-candidate-gate": fix.NATIVE_RUN_ID}

    valid_runs = [
        {
            "id": 8001,
            "name": "public-pr-gate",
            "status": "completed",
            "conclusion": "success",
            "app": {"id": gh.GITHUB_ACTIONS_APP_ID},
            "html_url": f"https://github.com/{gh.EXPECTED_REPO}/actions/runs/{fix.PUBLIC_RUN_ID}/job/9001",
        },
        {
            "id": 8002,
            "name": "native-release-candidate-gate",
            "status": "completed",
            "conclusion": "success",
            "app": {"id": gh.GITHUB_ACTIONS_APP_ID},
            "html_url": f"https://github.com/{gh.EXPECTED_REPO}/actions/runs/{fix.NATIVE_RUN_ID}/job/9002",
        },
    ]
    fake_gh.set_json(f"{api}/commits/{fix.HEAD_SHA}/check-runs?per_page=100", {
        "total_count": 2,
        "check_runs": valid_runs,
    })

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        gh.verify_check_contexts_app(client, fix.HEAD_SHA, contexts, expected_runs)

    # Missing app ID (wrong integration / third-party app)
    bad_app_runs = copy.deepcopy(valid_runs)
    bad_app_runs[0]["app"]["id"] = 99999
    fake_gh.set_json(f"{api}/commits/{fix.HEAD_SHA}/check-runs?per_page=100", {
        "total_count": 2,
        "check_runs": bad_app_runs,
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='check context app source is not GitHub Actions'),
    ):
        gh.verify_check_contexts_app(client, fix.HEAD_SHA, contexts, expected_runs)


# 6. Artifact Download Tests
def test_verify_artifact_download_validation() -> None:
    fake_gh = fix.FakeGitHub()
    client = gh.GitHubClient()
    api = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}"

    raw_zip = b"fake-zip-payload"
    c_hash = f"sha256:{bundle.sha256_bytes(raw_zip)}"
    art_meta = {
        "id": 1001,
        "name": "test-artifact",
        "expired": False,
        "expires_at": "2099-01-01T00:00:00Z",
        "size_in_bytes": len(raw_zip),
        "digest": c_hash,
        "workflow_run": {
            "id": int(fix.PUBLIC_RUN_ID),
            "repository_id": gh.EXPECTED_REPO_ID,
            "head_repository_id": gh.EXPECTED_REPO_ID,
        },
    }
    fake_gh.set_json(f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}/artifacts?per_page=100", {
        "total_count": 1,
        "artifacts": [art_meta],
    })
    fake_gh.set_route(f"{api}/actions/artifacts/1001/zip", raw_zip)

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        meta, content = gh.verify_artifact_download(client, fix.PUBLIC_RUN_ID, "test-artifact")
        assert meta["id"] == 1001
        assert content == raw_zip

    # Expired artifact fails
    expired_meta = copy.deepcopy(art_meta)
    expired_meta["expired"] = True
    fake_gh.set_json(f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}/artifacts?per_page=100", {
        "total_count": 1,
        "artifacts": [expired_meta],
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='expired or lacks expiry state'),
    ):
        gh.verify_artifact_download(client, fix.PUBLIC_RUN_ID, "test-artifact")

    # Cross-run artifact fails
    cross_meta = copy.deepcopy(art_meta)
    cross_meta["workflow_run"]["id"] = 99999
    fake_gh.set_json(f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}/artifacts?per_page=100", {
        "total_count": 1,
        "artifacts": [cross_meta],
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='cross-run or cross-repository'),
    ):
        gh.verify_artifact_download(client, fix.PUBLIC_RUN_ID, "test-artifact")


# 7. Ruleset Readback Tests
def test_ruleset_readback_validation() -> None:
    valid_readback = fix.make_ruleset_readback()
    res = gh.verify_ruleset_readback(valid_readback)
    assert res["id"] == fix.RULESET_ID

    # Disabled ruleset fails
    disabled = fix.make_ruleset_readback(active=False)
    with pytest.raises(gh.GitHubBoundaryError, match="no active ruleset"):
        gh.verify_ruleset_readback(disabled)

    # Missing strict_required_status_checks_policy fails
    non_strict = fix.make_ruleset_readback(strict=False)
    with pytest.raises(gh.GitHubBoundaryError, match="strict_required_status_checks_policy: true"):
        gh.verify_ruleset_readback(non_strict)

    # Missing required context fails
    missing_ctx = set(gh.REQUIRED_RULESET_CONTEXTS) - {"native-release-candidate-gate"}
    bad_ctx_readback = fix.make_ruleset_readback(contexts=missing_ctx)
    with pytest.raises(gh.GitHubBoundaryError, match="ruleset check contexts mismatch"):
        gh.verify_ruleset_readback(bad_ctx_readback)

    # Bypass actors present fails
    bypass_readback = fix.make_ruleset_readback(bypass_actors=[{"actor_id": 1, "actor_type": "Integration"}])
    with pytest.raises(gh.GitHubBoundaryError, match="allows bypass actors"):
        gh.verify_ruleset_readback(bypass_readback)

    # Missing required rule type fails
    missing_rule = fix.make_ruleset_readback(rule_types={"pull_request", "deletion", "required_status_checks"})
    with pytest.raises(gh.GitHubBoundaryError, match="missing required rule types"):
        gh.verify_ruleset_readback(missing_rule)


# 8. Governance Tests
def test_governance_verification() -> None:
    fake_gh = fix.FakeGitHub()
    client = gh.GitHubClient(token="test")
    api = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}"

    # Author cannot approve own PR
    fake_gh.set_json(f"{api}/pulls/3/reviews?per_page=100", [
        {"id": 1, "user": {"login": fix.AUTHOR_LOGIN}, "state": "APPROVED", "commit_id": fix.HEAD_SHA, "author_association": "OWNER"},
    ])
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='neither eligible non-author approval nor governance waiver'),
    ):
        gh.verify_governance(client, 3, fix.HEAD_SHA, fix.BASE_SHA, fix.MERGE_SHA, fix.AUTHOR_LOGIN, None)

    # Stale review on old commit rejected
    fake_gh.set_json(f"{api}/pulls/3/reviews?per_page=100", [
        {"id": 2, "user": {"login": fix.REVIEWER_LOGIN}, "state": "APPROVED", "commit_id": "0" * 40, "author_association": "MEMBER"},
    ])
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='neither eligible non-author approval nor governance waiver'),
    ):
        gh.verify_governance(client, 3, fix.HEAD_SHA, fix.BASE_SHA, fix.MERGE_SHA, fix.AUTHOR_LOGIN, None)

    # Ineligible author association (e.g. CONTRIBUTOR) rejected
    fake_gh.set_json(f"{api}/pulls/3/reviews?per_page=100", [
        {"id": 3, "user": {"login": fix.REVIEWER_LOGIN}, "state": "APPROVED", "commit_id": fix.HEAD_SHA, "author_association": "CONTRIBUTOR"},
    ])
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='neither eligible non-author approval nor governance waiver'),
    ):
        gh.verify_governance(client, 3, fix.HEAD_SHA, fix.BASE_SHA, fix.MERGE_SHA, fix.AUTHOR_LOGIN, None)

    # Non-author approval with MEMBER association succeeds
    fake_gh.set_json(f"{api}/pulls/3/reviews?per_page=100", [
        {"id": 4, "user": {"login": fix.REVIEWER_LOGIN}, "state": "APPROVED", "commit_id": fix.HEAD_SHA, "author_association": "MEMBER"},
    ])
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        gov = gh.verify_governance(client, 3, fix.HEAD_SHA, fix.BASE_SHA, fix.MERGE_SHA, fix.AUTHOR_LOGIN, None)
        assert gov["mode"] == "approval"
        assert gov["approvals"][0]["user"] == fix.REVIEWER_LOGIN

    # In absence of approval, valid waiver succeeds
    fake_gh.set_json(f"{api}/pulls/3/reviews?per_page=100", [])
    waiver = fix.make_governance_waiver(head_sha=fix.HEAD_SHA, base_sha=fix.BASE_SHA, merge_sha=fix.MERGE_SHA)
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        gov_waiver = gh.verify_governance(client, 3, fix.HEAD_SHA, fix.BASE_SHA, fix.MERGE_SHA, fix.AUTHOR_LOGIN, waiver)
        assert gov_waiver["mode"] == "waiver"
        assert gov_waiver["waiver_sha256"] == waiver["self_sha256"]

    # Mismatched waiver head SHA fails
    bad_waiver = fix.make_governance_waiver(head_sha="0" * 40, base_sha=fix.BASE_SHA, merge_sha=fix.MERGE_SHA)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh),
        pytest.raises(gh.GitHubBoundaryError, match='waiver pr_head_sha mismatch'),
    ):
        gh.verify_governance(client, 3, fix.HEAD_SHA, fix.BASE_SHA, fix.MERGE_SHA, fix.AUTHOR_LOGIN, bad_waiver)


# 9. Squash Commit and Main Branch Tests
def test_squash_and_branch_verification() -> None:
    fake_gh = fix.FakeGitHub()
    bundle_zip, _, _file_bytes, seal_doc = fix.build_test_bundle_zip()
    gate_zip, _ = fix.build_test_gate_index_zip(bundle_seal=seal_doc, bundle_zip_bytes=bundle_zip)
    fix.populate_fake_github(fake_gh, bundle_zip, gate_zip, bundle_file_bytes=_file_bytes)
    client = gh.GitHubClient()

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        commit = gh.verify_squash_and_branch(
            client, fix.PR_NUMBER, fix.SQUASH_SHA, fix.BASE_SHA, fix.TREE_SHA, "0.13.0"
        )
        assert commit["sha"] == fix.SQUASH_SHA

    # Extra parent fails
    fake_gh_bad = copy.deepcopy(fake_gh)
    fake_gh_bad.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/commits/{fix.SQUASH_SHA}", {
        "sha": fix.SQUASH_SHA,
        "parents": [{"sha": fix.BASE_SHA}, {"sha": fix.HEAD_SHA}],
        "commit": {"tree": {"sha": fix.TREE_SHA}, "message": "Release v0.13.0"},
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh_bad),
        pytest.raises(gh.GitHubBoundaryError, match='sole parent'),
    ):
        gh.verify_squash_and_branch(client, fix.PR_NUMBER, fix.SQUASH_SHA, fix.BASE_SHA, fix.TREE_SHA, "0.13.0")

    # Tree mismatch fails
    fake_gh_tree = copy.deepcopy(fake_gh)
    fake_gh_tree.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/commits/{fix.SQUASH_SHA}", {
        "sha": fix.SQUASH_SHA,
        "parents": [{"sha": fix.BASE_SHA}],
        "commit": {"tree": {"sha": "0" * 40}, "message": "Release v0.13.0"},
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh_tree),
        pytest.raises(gh.GitHubBoundaryError, match='squash commit tree mismatch'),
    ):
        gh.verify_squash_and_branch(client, fix.PR_NUMBER, fix.SQUASH_SHA, fix.BASE_SHA, fix.TREE_SHA, "0.13.0")

    # Main branch advanced (ahead_by != 1) fails
    fake_gh_comp = copy.deepcopy(fake_gh)
    fake_gh_comp.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/compare/{fix.BASE_SHA}...{fix.SQUASH_SHA}", {
        "ahead_by": 2,
        "behind_by": 0,
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh_comp),
        pytest.raises(gh.GitHubBoundaryError, match='main comparison to base invalid'),
    ):
        gh.verify_squash_and_branch(client, fix.PR_NUMBER, fix.SQUASH_SHA, fix.BASE_SHA, fix.TREE_SHA, "0.13.0")


# 10. Tag Verification Tests
def test_tag_verification() -> None:
    fake_gh = fix.FakeGitHub()
    bundle_zip, _, _file_bytes, seal_doc = fix.build_test_bundle_zip()
    gate_zip, _ = fix.build_test_gate_index_zip(bundle_seal=seal_doc, bundle_zip_bytes=bundle_zip)
    fix.populate_fake_github(fake_gh, bundle_zip, gate_zip, bundle_file_bytes=_file_bytes, tag_type="tag")
    client = gh.GitHubClient()

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        tag_obj = gh.verify_annotated_tag(client, "v0.13.0", fix.SQUASH_SHA)
        assert tag_obj["tag"] == "v0.13.0"

    # Lightweight tag rejected
    fake_gh_lw = fix.FakeGitHub()
    fix.populate_fake_github(fake_gh_lw, bundle_zip, gate_zip, bundle_file_bytes=_file_bytes, tag_type="lightweight")
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh_lw),
        pytest.raises(gh.GitHubBoundaryError, match='annotated tag'),
    ):
        gh.verify_annotated_tag(client, "v0.13.0", fix.SQUASH_SHA)

    # Empty tag message rejected
    fake_gh_nomsg = copy.deepcopy(fake_gh)
    fake_gh_nomsg.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/git/tags/{fix.TAG_SHA}", {
        "tag": "v0.13.0",
        "sha": fix.TAG_SHA,
        "message": "",
        "object": {"sha": fix.SQUASH_SHA, "type": "commit"},
    })
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh_nomsg),
        pytest.raises(gh.GitHubBoundaryError, match='annotated tag identity or message missing'),
    ):
        gh.verify_annotated_tag(client, "v0.13.0", fix.SQUASH_SHA)


# 11. Release Verification Tests
def test_release_verification() -> None:
    fake_gh = fix.FakeGitHub()
    bundle_zip, _sums_map, _file_bytes, seal_doc = fix.build_test_bundle_zip()
    gate_zip, _ = fix.build_test_gate_index_zip(bundle_seal=seal_doc, bundle_zip_bytes=bundle_zip)
    fix.populate_fake_github(fake_gh, bundle_zip, gate_zip, bundle_file_bytes=_file_bytes, release_state="published")
    client = gh.GitHubClient()

    # Create mapping from 17-file bundle
    members = bundle.inspect_zip_bytes(bundle_zip)
    v_res = bundle.verify_bundle_contents(members, "0.13.0")
    path_mapping = v_res["mapping"]

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        rel = gh.verify_github_release(client, fix.RELEASE_ID, "v0.13.0", "published", path_mapping)
        assert rel["id"] == fix.RELEASE_ID

    # Prerelease marked release rejected
    fake_gh_pre = copy.deepcopy(fake_gh)
    rel_pre = fake_gh.routes[f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/releases/{fix.RELEASE_ID}"]
    rel_obj = json.loads(rel_pre[0].decode("utf-8"))
    rel_obj["prerelease"] = True
    fake_gh_pre.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/releases/{fix.RELEASE_ID}", rel_obj)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh_pre),
        pytest.raises(gh.GitHubBoundaryError, match='release must not be marked as a prerelease'),
    ):
        gh.verify_github_release(client, fix.RELEASE_ID, "v0.13.0", "published", path_mapping)

    # Missing assets fails
    fake_gh_bad = copy.deepcopy(fake_gh)
    rel_obj_bad = copy.deepcopy(rel_obj)
    rel_obj_bad["prerelease"] = False
    rel_obj_bad["assets"] = [{"id": 1, "name": "apg-distribution-manifest.json", "size": 10, "state": "uploaded"}]
    fake_gh_bad.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/releases/{fix.RELEASE_ID}", rel_obj_bad)
    with (
        mock.patch('tools.ci.release_boundary_github._open', fake_gh_bad),
        pytest.raises(gh.GitHubBoundaryError, match='release assets mismatch'),
    ):
        gh.verify_github_release(client, fix.RELEASE_ID, "v0.13.0", "published", path_mapping)
