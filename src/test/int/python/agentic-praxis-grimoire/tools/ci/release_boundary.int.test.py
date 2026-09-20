"""Integration tests for APGR release boundary CLI."""

from __future__ import annotations

import copy
import io
import json
import zipfile
from pathlib import Path
from unittest import mock

import pytest

from src.test.support import release_boundary_fixtures as fix
from tools.ci import release_boundary as cli
from tools.ci import release_boundary_bundle as bundle
from tools.ci import release_boundary_github as gh


@pytest.fixture(autouse=True)
def ensure_env():
    with mock.patch.dict("os.environ", {"GITHUB_REPOSITORY": gh.EXPECTED_REPO}):
        yield


@pytest.fixture
def tmp_dir(tmp_path: Path):
    return tmp_path


def test_cli_lifecycle_end_to_end_no_rebuild_unchanged_16_assets(tmp_dir: Path) -> None:
    """Full lifecycle: candidate -> merged (no tag) -> merged (require-tag) -> release (draft) -> release (published) -> verify-published."""
    fake_gh = fix.FakeGitHub()
    bundle_zip, _sums_map, _file_bytes, seal_doc = fix.build_test_bundle_zip("0.13.0")
    gate_zip, _index_doc = fix.build_test_gate_index_zip(bundle_seal=seal_doc, bundle_zip_bytes=bundle_zip)
    pub_gate_zip, _ = fix.build_test_public_gate_zip()

    # Initial state: candidate PR is open, not merged
    fix.populate_fake_github(
        fake_gh,
        bundle_zip_bytes=bundle_zip,
        gate_zip_bytes=gate_zip,
        public_gate_zip_bytes=pub_gate_zip,
        bundle_file_bytes=_file_bytes,
        pr_state="open",
        approval_mode="approval",
        tag_type="tag",
    )

    readback_path = tmp_dir / "ruleset-readback.json"
    readback_path.write_text(json.dumps(fix.make_ruleset_readback()), encoding="utf-8")

    # 1. Candidate command
    cand_out = tmp_dir / "candidate_out"
    cand_argv = [
        "candidate",
        "--pr", str(fix.PR_NUMBER),
        "--expect-head", fix.HEAD_SHA,
        "--expect-base", fix.BASE_SHA,
        "--public-run", fix.PUBLIC_RUN_ID,
        "--native-run", fix.NATIVE_RUN_ID,
        "--output", str(cand_out),
        "--ruleset-admin-readback", str(readback_path),
    ]

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(cand_argv) == 0

    cand_file = cand_out / "candidate-attestation.json"
    assert cand_file.is_file()
    cand_doc = json.loads(cand_file.read_text(encoding="utf-8"))
    bundle.validate_self_hash(cand_doc)
    assert cand_doc["schema"] == bundle.CANDIDATE_ATTESTATION_SCHEMA
    assert cand_doc["pr_number"] == fix.PR_NUMBER
    assert cand_doc["head_sha"] == fix.HEAD_SHA
    assert cand_doc["base_sha"] == fix.BASE_SHA
    assert cand_doc["merge_commit_sha"] == fix.MERGE_SHA
    assert cand_doc["tree_sha"] == fix.TREE_SHA
    assert cand_doc["tested_merge"] == {"sha": fix.MERGE_SHA, "parents": [fix.BASE_SHA, fix.HEAD_SHA], "tree_sha": fix.TREE_SHA}
    assert cand_doc["workflow_bindings"]["public_pr"]["pr_base_sha"] == fix.BASE_SHA
    assert cand_doc["workflow_bindings"]["native"]["pr_head_sha"] == fix.HEAD_SHA
    assert cand_doc["bundle"]["asset_count"] == 16
    assert cand_doc["bundle"]["checksum_row_count"] == 15
    assert len(cand_doc["bundle"]["mapping"]) == 16

    # Verify all 16 assets materialized into candidate_out/assets
    assets_dir = cand_out / "assets"
    assert assets_dir.is_dir()
    for entry in cand_doc["bundle"]["mapping"].values():
        asset_file = assets_dir / entry["flat_name"]
        assert asset_file.is_file()
        assert bundle.sha256_bytes(asset_file.read_bytes()) == entry["sha256"]

    # Realistic transition: PR is now merged on main tip S
    fix.populate_fake_github(
        fake_gh,
        bundle_zip_bytes=bundle_zip,
        gate_zip_bytes=gate_zip,
        public_gate_zip_bytes=pub_gate_zip,
        bundle_file_bytes=_file_bytes,
        pr_state="merged",
        approval_mode="approval",
        tag_type="tag",
    )

    # 2. Merged command without tag
    fake_gh.calls.clear()
    merged_no_tag_out = tmp_dir / "merged_no_tag_out"
    merged_no_tag_argv = [
        "merged",
        "--candidate", str(cand_file),
        "--output", str(merged_no_tag_out),
    ]
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(merged_no_tag_argv) == 0

    merged_no_tag_file = merged_no_tag_out / "merged-attestation.json"
    assert merged_no_tag_file.is_file()
    doc_no_tag = json.loads(merged_no_tag_file.read_text(encoding="utf-8"))
    bundle.validate_self_hash(doc_no_tag)
    assert doc_no_tag["tag"] is None

    # 3. Merged command with tag (require-tag)
    merged_tag_out = tmp_dir / "merged_tag_out"
    merged_tag_argv = [
        "merged",
        "--candidate", str(cand_file),
        "--output", str(merged_tag_out),
        "--require-tag",
    ]
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(merged_tag_argv) == 0

    merged_tag_file = merged_tag_out / "merged-attestation.json"
    assert merged_tag_file.is_file()
    merged_doc = json.loads(merged_tag_file.read_text(encoding="utf-8"))
    bundle.validate_self_hash(merged_doc)
    assert merged_doc["schema"] == bundle.MERGED_ATTESTATION_SCHEMA
    assert merged_doc["candidate_attestation_sha256"] == cand_doc["self_sha256"]
    assert merged_doc["squash_commit_sha"] == fix.SQUASH_SHA
    assert merged_doc["tag"] == {"tag_name": "v0.13.0", "tag_sha": fix.TAG_SHA}

    notes_file = merged_tag_out / "release-notes.md"
    assert notes_file.is_file()
    notes_text = notes_file.read_text(encoding="utf-8")

    # 4. Release command in draft state
    fix.populate_fake_github(
        fake_gh,
        bundle_zip_bytes=bundle_zip,
        gate_zip_bytes=gate_zip,
        public_gate_zip_bytes=pub_gate_zip,
        bundle_file_bytes=_file_bytes,
        pr_state="merged",
        approval_mode="approval",
        tag_type="tag",
        include_release=True,
        release_notes=notes_text,
        release_state="draft",
    )
    rel_draft_out = tmp_dir / "release_draft_out"
    rel_draft_argv = [
        "release",
        "--candidate", str(cand_file),
        "--merged", str(merged_tag_file),
        "--release-id", str(fix.RELEASE_ID),
        "--state", "draft",
        "--output", str(rel_draft_out),
    ]
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(rel_draft_argv) == 0

    rel_draft_file = rel_draft_out / "release-boundary-attestation.json"
    assert rel_draft_file.is_file()
    rel_draft_doc = json.loads(rel_draft_file.read_text(encoding="utf-8"))
    bundle.validate_self_hash(rel_draft_doc)
    assert rel_draft_doc["state"] == "draft"

    # 5. Release command in published state
    fix.populate_fake_github(
        fake_gh,
        bundle_zip_bytes=bundle_zip,
        gate_zip_bytes=gate_zip,
        public_gate_zip_bytes=pub_gate_zip,
        bundle_file_bytes=_file_bytes,
        pr_state="merged",
        approval_mode="approval",
        tag_type="tag",
        include_release=True,
        release_notes=notes_text,
        release_state="published",
    )
    rel_pub_out = tmp_dir / "release_pub_out"
    rel_pub_argv = [
        "release",
        "--candidate", str(cand_file),
        "--merged", str(merged_tag_file),
        "--release-id", str(fix.RELEASE_ID),
        "--state", "published",
        "--output", str(rel_pub_out),
    ]
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(rel_pub_argv) == 0

    rel_pub_file = rel_pub_out / "release-boundary-attestation.json"
    assert rel_pub_file.is_file()
    rel_pub_doc = json.loads(rel_pub_file.read_text(encoding="utf-8"))
    bundle.validate_self_hash(rel_pub_doc)
    assert rel_pub_doc["state"] == "published"
    assert len(rel_pub_doc["assets"]) == 16

    # 6. Verify-published postpublication command from release event
    event = {
        "action": "published",
        "repository": {"id": gh.EXPECTED_REPO_ID, "full_name": gh.EXPECTED_REPO},
        "release": {
            "id": fix.RELEASE_ID,
            "tag_name": "v0.13.0",
            "draft": False,
            "prerelease": False,
            "body": notes_text,
        },
    }
    event_file = tmp_dir / "release-event.json"
    event_file.write_text(json.dumps(event), encoding="utf-8")

    verify_pub_out = tmp_dir / "verify_pub_out"
    verify_argv = [
        "verify-published",
        "--event", str(event_file),
        "--output", str(verify_pub_out),
    ]
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(verify_argv) == 0

    pub_ver_file = verify_pub_out / "published-verification.json"
    assert pub_ver_file.is_file()
    pub_ver_doc = json.loads(pub_ver_file.read_text(encoding="utf-8"))
    bundle.validate_self_hash(pub_ver_doc)
    assert pub_ver_doc["release_id"] == fix.RELEASE_ID
    assert pub_ver_doc["state"] == "published"
    assert not any(url.endswith(f"/git/commits/{fix.MERGE_SHA}") for url in fake_gh.calls)


@pytest.mark.parametrize("run_id", [fix.PUBLIC_RUN_ID, fix.NATIVE_RUN_ID])
def test_candidate_requires_live_association_but_uses_tested_merge(tmp_dir: Path, run_id: str) -> None:
    fg = fix.FakeGitHub()
    bz, _, files, seal = fix.build_test_bundle_zip()
    iz, _ = fix.build_test_gate_index_zip(bundle_seal=seal, bundle_zip_bytes=bz)
    pz, _ = fix.build_test_public_gate_zip()
    fix.populate_fake_github(fg, bz, iz, pz, files)
    api = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}"
    pr = json.loads(fg.routes[f"{api}/pulls/3"][0])
    pr["merge_commit_sha"] = "7" * 40  # GitHub recomputed M; artifacts still bind tested M.
    fg.set_json(f"{api}/pulls/3", pr)
    with mock.patch("tools.ci.release_boundary_github._open", fg):
        cand, _ = cli._candidate_facts(gh.GitHubClient(), head=fix.HEAD_SHA, base=fix.BASE_SHA,
            public_run=fix.PUBLIC_RUN_ID, native_run=fix.NATIVE_RUN_ID, ruleset_data=fix.make_ruleset_readback())
    assert cand["merge_commit_sha"] == fix.MERGE_SHA
    assert f"{api}/git/commits/{'7' * 40}" not in fg.calls
    url = f"{api}/actions/runs/{run_id}"
    run = json.loads(fg.routes[url][0])
    run["pull_requests"] = []
    fg.set_json(url, run)
    with mock.patch("tools.ci.release_boundary_github._open", fg), pytest.raises(gh.GitHubBoundaryError, match="PR head/base association"):
        cli._candidate_facts(gh.GitHubClient(), head=fix.HEAD_SHA, base=fix.BASE_SHA,
            public_run=fix.PUBLIC_RUN_ID, native_run=fix.NATIVE_RUN_ID, ruleset_data=fix.make_ruleset_readback())


@pytest.mark.parametrize("mutation, message", [
    ("removed", None), ("reassociated", None),
    ("run_attempt", "recorded workflow run"), ("workflow_id", "recorded workflow run"),
    ("check_suite_id", "recorded workflow run"), ("head_sha", "head SHA mismatch"),
    ("conclusion", "did not succeed"), ("binding-missing", "pre-merge workflow bindings"),
    ("binding-pr_number", "recorded workflow run"), ("binding-pr_base_sha", "recorded workflow run"),
    ("binding-run_id", "recorded workflow run"), ("binding-run_attempt", "recorded workflow run"),
    ("merge-parents", "tested merge parents/tree"), ("merge-tree_sha", "tested merge parents/tree"),
    ("artifact-expired", "expired"), ("jobs-failed", "not successful"),
])
def test_post_merge_revalidation_preserves_captured_authority(mutation: str, message: str | None) -> None:
    fg = fix.FakeGitHub()
    bz, _, files, seal = fix.build_test_bundle_zip()
    iz, _ = fix.build_test_gate_index_zip(bundle_seal=seal, bundle_zip_bytes=bz)
    pz, _ = fix.build_test_public_gate_zip()
    fix.populate_fake_github(fg, bz, iz, pz, files)
    with mock.patch("tools.ci.release_boundary_github._open", fg):
        cand, _ = cli._candidate_facts(gh.GitHubClient(), head=fix.HEAD_SHA, base=fix.BASE_SHA,
            public_run=fix.PUBLIC_RUN_ID, native_run=fix.NATIVE_RUN_ID, ruleset_data=fix.make_ruleset_readback())
    fix.populate_fake_github(fg, bz, iz, pz, files, pr_state="merged")
    api = f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}"
    url = f"{api}/actions/runs/{fix.PUBLIC_RUN_ID}"
    run = json.loads(fg.routes[url][0])
    if mutation == "reassociated":
        run["pull_requests"] = [{"number": 99, "head": {"sha": "0" * 40}}]
    elif mutation in {"run_attempt", "workflow_id", "check_suite_id"}:
        run[mutation] += 1
    elif mutation == "head_sha":
        run[mutation] = "0" * 40
    elif mutation == "conclusion":
        run[mutation] = "failure"
    elif mutation == "binding-missing":
        del cand["workflow_bindings"]["public_pr"]
    elif mutation.startswith("binding-"):
        key = mutation.removeprefix("binding-")
        cand["workflow_bindings"]["public_pr"][key] = 99 if key in {"pr_number", "run_attempt"} else "0" * 40
    elif mutation.startswith("merge-"):
        key = mutation.removeprefix("merge-")
        cand["tested_merge"][key] = [fix.HEAD_SHA, fix.BASE_SHA] if key == "parents" else "0" * 40
    elif mutation == "artifact-expired":
        art_url = url + "/artifacts?per_page=100"
        artifacts = json.loads(fg.routes[art_url][0])
        artifacts["artifacts"][0]["expired"] = True
        fg.set_json(art_url, artifacts)
    elif mutation == "jobs-failed":
        jobs_url = url + "/jobs?per_page=100"
        jobs = json.loads(fg.routes[jobs_url][0])
        jobs["jobs"][0]["conclusion"] = "failure"
        fg.set_json(jobs_url, jobs)
    fg.set_json(url, run)
    bundle.finalize_self_hash(cand)
    fg.calls.clear()
    with mock.patch("tools.ci.release_boundary_github._open", fg):
        if message is None:
            cli._revalidate(gh.GitHubClient(), cand)
        else:
            with pytest.raises((cli.BoundaryError, gh.GitHubBoundaryError), match=message):
                cli._revalidate(gh.GitHubClient(), cand)
    assert f"{api}/git/commits/{fix.MERGE_SHA}" not in fg.calls


def test_cli_candidate_waiver_and_trailer_lifecycle(tmp_dir: Path) -> None:
    """Waiver lifecycle: candidate with waiver -> merged with trailer -> release."""
    fake_gh = fix.FakeGitHub()
    bundle_zip, _sums_map, _file_bytes, seal_doc = fix.build_test_bundle_zip("0.13.0")
    gate_zip, _ = fix.build_test_gate_index_zip(bundle_seal=seal_doc, bundle_zip_bytes=bundle_zip)
    pub_gate_zip, _ = fix.build_test_public_gate_zip()

    waiver = fix.make_governance_waiver()
    waiver_path = tmp_dir / "waiver.json"
    waiver_path.write_text(json.dumps(waiver), encoding="utf-8")

    readback_path = tmp_dir / "waiver-readback.json"
    readback_path.write_text(json.dumps(fix.make_ruleset_readback(review_count=0)), encoding="utf-8")

    # Initial candidate setup with no approvals
    fix.populate_fake_github(
        fake_gh,
        bundle_zip_bytes=bundle_zip,
        gate_zip_bytes=gate_zip,
        public_gate_zip_bytes=pub_gate_zip,
        bundle_file_bytes=_file_bytes,
        pr_state="open",
        approval_mode="waiver",
        tag_type="tag",
        waiver_hash=waiver["self_sha256"],
    )

    cand_out = tmp_dir / "cand_waiver_out"
    cand_argv = [
        "candidate",
        "--pr", str(fix.PR_NUMBER),
        "--expect-head", fix.HEAD_SHA,
        "--expect-base", fix.BASE_SHA,
        "--public-run", fix.PUBLIC_RUN_ID,
        "--native-run", fix.NATIVE_RUN_ID,
        "--output", str(cand_out),
        "--ruleset-admin-readback", str(readback_path),
        "--governance-waiver", str(waiver_path),
    ]

    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(cand_argv) == 0

    cand_file = cand_out / "candidate-attestation.json"
    cand_doc = json.loads(cand_file.read_text(encoding="utf-8"))
    assert cand_doc["governance"]["mode"] == "waiver"
    assert cand_doc["governance"]["waiver_sha256"] == waiver["self_sha256"]

    # Transition to merged: missing waiver trailer fails
    fix.populate_fake_github(
        fake_gh,
        bundle_zip_bytes=bundle_zip,
        gate_zip_bytes=gate_zip,
        public_gate_zip_bytes=pub_gate_zip,
        bundle_file_bytes=_file_bytes,
        pr_state="merged",
        approval_mode="waiver",
        tag_type="tag",
        waiver_hash=None,  # No trailer in squash commit
    )
    bad_merged_out = tmp_dir / "bad_merged_out"
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(["merged", "--candidate", str(cand_file), "--output", str(bad_merged_out)]) == 1

    # Transition to merged: with waiver trailer succeeds
    fix.populate_fake_github(
        fake_gh,
        bundle_zip_bytes=bundle_zip,
        gate_zip_bytes=gate_zip,
        public_gate_zip_bytes=pub_gate_zip,
        bundle_file_bytes=_file_bytes,
        pr_state="merged",
        approval_mode="waiver",
        tag_type="tag",
        waiver_hash=waiver["self_sha256"],
    )
    merged_waiver_out = tmp_dir / "merged_waiver_out"
    with mock.patch("tools.ci.release_boundary_github._open", fake_gh):
        assert cli.main(["merged", "--candidate", str(cand_file), "--output", str(merged_waiver_out), "--require-tag"]) == 0


def test_cli_candidate_negative_cases(tmp_dir: Path) -> None:
    """Test candidate failure cases for CI identity, public aggregate, native index, bundle, and metadata."""
    bundle_zip, _, _file_bytes, seal_doc = fix.build_test_bundle_zip("0.13.0")
    gate_zip, _ = fix.build_test_gate_index_zip(bundle_seal=seal_doc, bundle_zip_bytes=bundle_zip)
    pub_gate_zip, _ = fix.build_test_public_gate_zip()

    readback_path = tmp_dir / "ruleset-readback.json"
    readback_path.write_text(json.dumps(fix.make_ruleset_readback()), encoding="utf-8")

    def run_cand(fg: fix.FakeGitHub, out_name: str, **kwargs) -> int:
        out = tmp_dir / out_name
        argv = [
            "candidate",
            "--pr", str(fix.PR_NUMBER),
            "--expect-head", kwargs.get("head", fix.HEAD_SHA),
            "--expect-base", kwargs.get("base", fix.BASE_SHA),
            "--public-run", fix.PUBLIC_RUN_ID,
            "--native-run", fix.NATIVE_RUN_ID,
            "--output", str(out),
            "--ruleset-admin-readback", str(readback_path),
        ]
        with mock.patch("tools.ci.release_boundary_github._open", fg):
            return cli.main(argv)

    # 1. Expect-head mismatch
    fg1 = fix.FakeGitHub()
    fix.populate_fake_github(fg1, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    assert run_cand(fg1, "c1", head="0" * 40) == 1

    # 2. Expect-base mismatch
    fg2 = fix.FakeGitHub()
    fix.populate_fake_github(fg2, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    assert run_cand(fg2, "c2", base="0" * 40) == 1

    # 3. Wrong M parents
    fg3 = fix.FakeGitHub()
    fix.populate_fake_github(fg3, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    fg3.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/git/commits/{fix.MERGE_SHA}", {
        "sha": fix.MERGE_SHA,
        "parents": [{"sha": fix.BASE_SHA}],  # Missing head parent
        "tree": {"sha": fix.TREE_SHA},
    })
    assert run_cand(fg3, "c3") == 1

    # 4. Wrong M tree
    fg4 = fix.FakeGitHub()
    fix.populate_fake_github(fg4, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    fg4.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/git/commits/{fix.MERGE_SHA}", {
        "sha": fix.MERGE_SHA,
        "parents": [{"sha": fix.BASE_SHA}, {"sha": fix.HEAD_SHA}],
        "tree": {"sha": "0" * 40},
    })
    assert run_cand(fg4, "c4") == 1

    # 5. Public workflow run wrong path
    fg5 = fix.FakeGitHub()
    fix.populate_fake_github(fg5, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    run_obj = json.loads(fg5.routes[f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/actions/runs/{fix.PUBLIC_RUN_ID}"][0].decode("utf-8"))
    run_obj["path"] = ".github/workflows/other.yml"
    fg5.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/actions/runs/{fix.PUBLIC_RUN_ID}", run_obj)
    assert run_cand(fg5, "c5") == 1

    # 6. Public aggregate failure (success is False)
    fg6 = fix.FakeGitHub()
    _bad_pub_gate, _ = fix.build_test_public_gate_zip()
    bad_pub_buf = io.BytesIO()
    with zipfile.ZipFile(bad_pub_buf, "w") as zf:
        zf.writestr("matrix-aggregate.json", json.dumps({"schema": "apg-matrix-aggregate-v1", "success": False, "errors": ["failed"]}))
    bad_pub_bytes = bad_pub_buf.getvalue()
    fix.populate_fake_github(fg6, bundle_zip, gate_zip, bad_pub_bytes, _file_bytes)
    assert run_cand(fg6, "c6") == 1

    # 7. Public gate ZIP contains extra member (must contain exactly matrix-aggregate.json)
    fg7 = fix.FakeGitHub()
    extra_pub_buf = io.BytesIO()
    with zipfile.ZipFile(extra_pub_buf, "w") as zf:
        zf.writestr("matrix-aggregate.json", json.dumps({"schema": "apg-matrix-aggregate-v1", "success": True, "errors": [], "members": {}}))
        zf.writestr("extra.txt", "extra")
    fix.populate_fake_github(fg7, bundle_zip, gate_zip, extra_pub_buf.getvalue(), _file_bytes)
    assert run_cand(fg7, "c7") == 1

    # 8. Native index status != "passed"
    fg8 = fix.FakeGitHub()
    bad_index_buf = io.BytesIO()
    with zipfile.ZipFile(bad_index_buf, "w") as zf:
        zf.writestr("native-rc-index.json", json.dumps({"schema": "apgr.native-rc-index/v1", "status": "failed"}))
    fix.populate_fake_github(fg8, bundle_zip, bad_index_buf.getvalue(), pub_gate_zip, _file_bytes)
    assert run_cand(fg8, "c8") == 1

    # 9. Artifact expired
    fg9 = fix.FakeGitHub()
    fix.populate_fake_github(fg9, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    art_obj = json.loads(fg9.routes[f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/actions/runs/{fix.NATIVE_RUN_ID}/artifacts?per_page=100"][0].decode("utf-8"))
    art_obj["artifacts"][0]["expired"] = True
    fg9.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/actions/runs/{fix.NATIVE_RUN_ID}/artifacts?per_page=100", art_obj)
    assert run_cand(fg9, "c9") == 1

    # 10. Ruleset check context integration ID wrong
    fg10 = fix.FakeGitHub()
    fix.populate_fake_github(fg10, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    bad_readback = fix.make_ruleset_readback()
    bad_readback["rules"][3]["parameters"]["required_status_checks"][0]["integration_id"] = 99999
    bad_rb_file = tmp_dir / "bad_rb_10.json"
    bad_rb_file.write_text(json.dumps(bad_readback), encoding="utf-8")
    out10 = tmp_dir / "c10"
    argv10 = [
        "candidate",
        "--pr", str(fix.PR_NUMBER),
        "--expect-head", fix.HEAD_SHA,
        "--expect-base", fix.BASE_SHA,
        "--public-run", fix.PUBLIC_RUN_ID,
        "--native-run", fix.NATIVE_RUN_ID,
        "--output", str(out10),
        "--ruleset-admin-readback", str(bad_rb_file),
    ]
    with mock.patch("tools.ci.release_boundary_github._open", fg10):
        assert cli.main(argv10) == 1


def test_cli_merged_negative_cases(tmp_dir: Path) -> None:
    """Test merged failure cases for PR state, squash parents, tree, subject, and tag."""
    bundle_zip, _sums_map, _file_bytes, seal_doc = fix.build_test_bundle_zip("0.13.0")
    gate_zip, _ = fix.build_test_gate_index_zip(bundle_seal=seal_doc, bundle_zip_bytes=bundle_zip)
    pub_gate_zip, _ = fix.build_test_public_gate_zip()

    candidate_gh = fix.FakeGitHub()
    fix.populate_fake_github(candidate_gh, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    with mock.patch("tools.ci.release_boundary_github._open", candidate_gh):
        cand_doc, _ = cli._candidate_facts(gh.GitHubClient(), head=fix.HEAD_SHA, base=fix.BASE_SHA,
            public_run=fix.PUBLIC_RUN_ID, native_run=fix.NATIVE_RUN_ID, ruleset_data=fix.make_ruleset_readback())
    bundle.finalize_self_hash(cand_doc)
    cand_file = tmp_dir / "valid-candidate.json"
    cand_file.write_text(json.dumps(cand_doc), encoding="utf-8")

    # 1. PR not merged (merged: False)
    fg1 = fix.FakeGitHub()
    fix.populate_fake_github(fg1, bundle_zip, gate_zip, pub_gate_zip, _file_bytes, pr_state="open")
    with mock.patch("tools.ci.release_boundary_github._open", fg1):
        assert cli.main(["merged", "--candidate", str(cand_file), "--output", str(tmp_dir / "m1")]) == 1

    # 2. Squash commit wrong parents (2 parents instead of sole parent B)
    fg2 = fix.FakeGitHub()
    fix.populate_fake_github(fg2, bundle_zip, gate_zip, pub_gate_zip, _file_bytes, pr_state="merged")
    fg2.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/commits/{fix.SQUASH_SHA}", {
        "sha": fix.SQUASH_SHA,
        "parents": [{"sha": fix.BASE_SHA}, {"sha": fix.HEAD_SHA}],
        "commit": {"tree": {"sha": fix.TREE_SHA}, "message": "Release v0.13.0"},
    })
    with mock.patch("tools.ci.release_boundary_github._open", fg2):
        assert cli.main(["merged", "--candidate", str(cand_file), "--output", str(tmp_dir / "m2")]) == 1

    # 3. Squash commit wrong subject
    fg3 = fix.FakeGitHub()
    fix.populate_fake_github(fg3, bundle_zip, gate_zip, pub_gate_zip, _file_bytes, pr_state="merged")
    fg3.set_json(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/commits/{fix.SQUASH_SHA}", {
        "sha": fix.SQUASH_SHA,
        "parents": [{"sha": fix.BASE_SHA}],
        "commit": {"tree": {"sha": fix.TREE_SHA}, "message": "Incorrect subject"},
    })
    with mock.patch("tools.ci.release_boundary_github._open", fg3):
        assert cli.main(["merged", "--candidate", str(cand_file), "--output", str(tmp_dir / "m3")]) == 1

    # 4. Lightweight tag when require-tag is passed
    fg4 = fix.FakeGitHub()
    fix.populate_fake_github(fg4, bundle_zip, gate_zip, pub_gate_zip, _file_bytes, pr_state="merged", tag_type="lightweight")
    with mock.patch("tools.ci.release_boundary_github._open", fg4):
        assert cli.main(["merged", "--candidate", str(cand_file), "--output", str(tmp_dir / "m4"), "--require-tag"]) == 1


def test_cli_release_negative_cases(tmp_dir: Path) -> None:
    """Test release failure cases for state mismatch, prerelease, missing asset, and asset tampering."""
    bundle_zip, _sums_map, _file_bytes, seal_doc = fix.build_test_bundle_zip("0.13.0")
    gate_zip, _ = fix.build_test_gate_index_zip(bundle_seal=seal_doc, bundle_zip_bytes=bundle_zip)
    pub_gate_zip, _ = fix.build_test_public_gate_zip()

    candidate_gh = fix.FakeGitHub()
    fix.populate_fake_github(candidate_gh, bundle_zip, gate_zip, pub_gate_zip, _file_bytes)
    with mock.patch("tools.ci.release_boundary_github._open", candidate_gh):
        cand_doc, _ = cli._candidate_facts(gh.GitHubClient(), head=fix.HEAD_SHA, base=fix.BASE_SHA,
            public_run=fix.PUBLIC_RUN_ID, native_run=fix.NATIVE_RUN_ID, ruleset_data=fix.make_ruleset_readback())
    bundle.finalize_self_hash(cand_doc)
    cand_file = tmp_dir / "valid-candidate.json"
    cand_file.write_text(json.dumps(cand_doc), encoding="utf-8")

    merged_doc: dict = {
        "schema": bundle.MERGED_ATTESTATION_SCHEMA,
        "candidate_attestation_sha256": cand_doc["self_sha256"],
        "version": "0.13.0",
        "pr_number": fix.PR_NUMBER,
        "squash_commit_sha": fix.SQUASH_SHA,
        "parent_sha": fix.BASE_SHA,
        "head_sha": fix.HEAD_SHA,
        "tree_sha": fix.TREE_SHA,
        "tag": {"tag_name": "v0.13.0", "tag_sha": fix.TAG_SHA},
    }
    bundle.finalize_self_hash(merged_doc)
    merged_file = tmp_dir / "valid-merged.json"
    merged_file.write_text(json.dumps(merged_doc), encoding="utf-8")

    notes = bundle.format_release_notes(cand_doc, merged_doc)

    # 1. State mismatch (expected published but release draft: True)
    fg1 = fix.FakeGitHub()
    fix.populate_fake_github(fg1, bundle_zip, gate_zip, pub_gate_zip, _file_bytes, pr_state="merged", include_release=True, release_notes=notes, release_state="draft")
    with mock.patch("tools.ci.release_boundary_github._open", fg1):
        assert cli.main(["release", "--candidate", str(cand_file), "--merged", str(merged_file), "--release-id", str(fix.RELEASE_ID), "--state", "published", "--output", str(tmp_dir / "r1")]) == 1

    # 2. Release asset byte content tampered (SHA256 mismatch)
    fg2 = fix.FakeGitHub()
    fix.populate_fake_github(fg2, bundle_zip, gate_zip, pub_gate_zip, _file_bytes, pr_state="merged", include_release=True, release_notes=notes, release_state="published")
    fg2.set_route(f"{gh.API_ROOT}/repos/{gh.EXPECTED_REPO}/releases/assets/5000", b"tampered-content", "application/octet-stream")
    with mock.patch("tools.ci.release_boundary_github._open", fg2):
        assert cli.main(["release", "--candidate", str(cand_file), "--merged", str(merged_file), "--release-id", str(fix.RELEASE_ID), "--state", "published", "--output", str(tmp_dir / "r2")]) == 1


def test_cli_verify_published_negative_cases(tmp_dir: Path) -> None:
    """Test verify-published early event and environment validation (before any network access)."""
    valid_event = {
        "action": "published",
        "repository": {"id": gh.EXPECTED_REPO_ID, "full_name": gh.EXPECTED_REPO},
        "release": {
            "id": fix.RELEASE_ID,
            "tag_name": "v0.13.0",
            "draft": False,
            "prerelease": False,
            "body": "sample",
        },
    }

    def run_verify(ev: dict, out_name: str) -> int:
        p = tmp_dir / f"{out_name}.json"
        p.write_text(json.dumps(ev), encoding="utf-8")
        out = tmp_dir / out_name
        with mock.patch("tools.ci.release_boundary_github._open", side_effect=AssertionError("Network must not be reached!")):
            return cli.main(["verify-published", "--event", str(p), "--output", str(out)])

    # Action != "published"
    ev1 = copy.deepcopy(valid_event)
    ev1["action"] = "created"
    assert run_verify(ev1, "vp1") == 1

    # Release draft is True
    ev2 = copy.deepcopy(valid_event)
    ev2["release"]["draft"] = True
    assert run_verify(ev2, "vp2") == 1

    # Release prerelease is True
    ev3 = copy.deepcopy(valid_event)
    ev3["release"]["prerelease"] = True
    assert run_verify(ev3, "vp3") == 1

    # Wrong repository full_name
    ev4 = copy.deepcopy(valid_event)
    ev4["repository"]["full_name"] = "attacker/repo"
    assert run_verify(ev4, "vp4") == 1

    # GITHUB_REPOSITORY environment variable mismatch
    with mock.patch.dict("os.environ", {"GITHUB_REPOSITORY": "attacker/repo"}):
        assert run_verify(valid_event, "vp5") == 1
