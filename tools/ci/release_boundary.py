#!/usr/bin/env python3
"""CLI entry point and orchestrator for APGR release boundary attestation.

Only the closed ``RELEASE_CONTRACTS`` versions are supported: the immutable
historical v0.13.0 PR #3 contract and the approval-only v0.13.1 contract.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from release.ci.matrix_receipts import PUBLIC_PR_MEMBER_JOBS
from tools.ci.native_seal import CANONICAL_TARGETS, REQUIRED_LANES
from tools.ci.release_boundary_bundle import (
    CANDIDATE_ATTESTATION_SCHEMA,
    EXPECTED_VERSION,
    MERGED_ATTESTATION_SCHEMA,
    RELEASE_ATTESTATION_SCHEMA,
    RELEASE_CONTRACTS,
    BoundaryBundleError,
    canonical_json,
    finalize_self_hash,
    format_release_notes,
    inspect_zip_bytes,
    parse_release_notes,
    release_contract,
    sha256_bytes,
    strict_json,
    validate_self_hash,
    verify_bundle_contents,
)
from tools.ci.release_boundary_github import (
    EXPECTED_REPO,
    REQUIRED_NATIVE_JOBS,
    REQUIRED_PR_JOBS,
    GitHubBoundaryError,
    GitHubClient,
    verify_annotated_tag,
    verify_artifact_download,
    verify_check_contexts_app,
    verify_commit_parents_tree,
    verify_github_release,
    verify_governance,
    verify_pull_request,
    verify_ruleset_readback,
    verify_squash_and_branch,
    verify_workflow_run,
    workflow_run_binding,
)


class BoundaryError(ValueError):
    """Release boundary failure."""


def _load_json_file(path: Path, label: str) -> Any:
    if not path.is_file():
        raise BoundaryError(f"{label} file not found: {path}")
    if path.is_symlink():
        raise BoundaryError(f"{label} must be a direct regular file")
    return strict_json(path.read_bytes(), label)


def _safe_output(output_path: Path) -> None:
    for path in (output_path, *output_path.absolute().parents):
        if path.is_symlink():
            raise BoundaryError("output path cannot contain symlink ancestors")


def _write_canonical_json(output_path: Path, data: dict[str, Any]) -> None:
    _safe_output(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as stream:
        stream.write(canonical_json(data))


EXPECTED_TAG = f"v{EXPECTED_VERSION}"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BoundaryError(message)


def _contract_pr(version: str, pr_number: Any) -> tuple[dict[str, Any], int]:
    """Return the closed contract and its PR; a measured PR must be positive."""
    contract = release_contract(version)
    _require(type(pr_number) is int and pr_number > 0, "release boundary PR number must be a positive integer")
    pinned = contract["pr_number"]
    _require(pinned is None or pr_number == pinned, f"release boundary requires PR #{pinned}")
    return contract, pr_number


def _client() -> GitHubClient:
    _require(os.environ.get("GITHUB_REPOSITORY", EXPECTED_REPO) == EXPECTED_REPO, "wrong GITHUB_REPOSITORY")
    return GitHubClient(token=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", ""))


def _archive_document(client: GitHubClient, run: str, artifact: str, filename: str) -> tuple[dict[str, Any], dict[str, Any]]:
    meta, content = verify_artifact_download(client, run, artifact)
    files = inspect_zip_bytes(content, expected_digest=meta["digest"])
    _require(set(files) == {filename}, "aggregate artifact must contain exactly its authority file")
    doc = strict_json(files[filename][2], filename)
    _require(isinstance(doc, dict), "aggregate authority must be an object")
    return meta, doc


def _index_contract(index: dict[str, Any], identity: dict[str, str]) -> None:
    _require(index.get("schema") == "apgr.native-rc-index/v1" and index.get("status") == "passed", "native index is not passed")
    _require(all(index.get(k) == v for k, v in identity.items()), "native index source/head/base mismatch")
    expected = REQUIRED_NATIVE_JOBS - {"native-release-candidate-gate"}
    members = index.get("members", {})
    _require(set(members) == expected, "native index nine-job inventory mismatch")
    for job, member in members.items():
        _require(member.get("name") == job and member.get("status") == "passed" and all(member.get(k) == v for k, v in identity.items()), "native index member identity/status mismatch")
        _require(bool(re.fullmatch(r"[0-9a-f]{64}", str(member.get("matrix_receipt_sha256", "")))), "native member receipt digest missing")
    lanes = index.get("lane_artifacts", {})
    _require(set(lanes) == set(REQUIRED_LANES), "native index lane inventory mismatch")
    for lane, entry in lanes.items():
        _require(entry.get("target") == CANONICAL_TARGETS[lane]["target"], "native index lane target mismatch")
        for key in ("seal_sha256", "file_sha256"):
            _require(bool(re.fullmatch(r"[0-9a-f]{64}", str(entry.get(key, "")))), "native lane digest missing")
    bundle = index.get("bundle_artifact", {})
    _require(bundle.get("asset_count") == 11, "native index asset count mismatch")
    consumers = bundle.get("consumers", {})
    _require(set(consumers) == set(REQUIRED_LANES) and all(c.get("status") == "passed" for c in consumers.values()), "native index consumers incomplete")
    scans = bundle.get("scans", {})
    _require(scans.get("status") == "passed" and scans.get("asset_count") == 11 and scans.get("scan_count") == 14, "native scans incomplete")
    for key in ("receipt_sha256", "receipt_file_sha256", "results_sha256"):
        _require(bool(re.fullmatch(r"[0-9a-f]{64}", str(scans.get(key, "")))), "native scan digest missing")


def _candidate_facts(client: GitHubClient, *, version: str, pr_number: int, head: str, base: str, public_run: str, native_run: str,
                     ruleset_data: Any, waiver_data: Any = None, recorded_candidate: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    # The PR number is caller input; only the live PR, run, review and
    # squash-association readbacks below authenticate it.
    contract, pr_number = _contract_pr(version, pr_number)
    for sha in (head, base):
        _require(bool(re.fullmatch(r"[0-9a-f]{40}", sha)), "expected head/base must be SHA40")
    for run in (public_run, native_run):
        _require(bool(re.fullmatch(r"[1-9][0-9]{0,18}", run)), "run id must be decimal")
    pr = verify_pull_request(client, pr_number, head, base, allow_merged=recorded_candidate is not None)
    if recorded_candidate is None:
        _require(pr.get("state") == "open" and pr.get("merged") is False and pr.get("draft") is False, "candidate PR must be open and ready")
    else:
        _require(pr.get("state") == "closed" and pr.get("merged") is True, "post-merge revalidation requires merged PR")
        _require(set(recorded_candidate.get("workflow_bindings", {})) == {"public_pr", "native"}, "candidate lacks exact pre-merge workflow bindings")
        _require(all(isinstance(binding, dict) for binding in recorded_candidate["workflow_bindings"].values()), "candidate workflow binding malformed")
    bindings = recorded_candidate["workflow_bindings"] if recorded_candidate is not None else {}
    public_run_doc, _ = verify_workflow_run(client, public_run, head, REQUIRED_PR_JOBS, "public PR", base,
        pr_number=pr_number, recorded_binding=bindings.get("public_pr"))
    native_run_doc, _ = verify_workflow_run(client, native_run, head, REQUIRED_NATIVE_JOBS, "native qualification", base,
        pr_number=pr_number, recorded_binding=bindings.get("native"))
    public_meta, aggregate = _archive_document(client, public_run, "public-pr-gate-result", "matrix-aggregate.json")
    gate_meta, index = _archive_document(client, native_run, "native-release-candidate-gate-result", "native-rc-index.json")
    # Bind M to the tested index, not a potentially recomputed live PR merge ref.
    merge_sha, tree = index.get("source_commit"), index.get("source_tree")
    _require(all(isinstance(sha, str) and bool(re.fullmatch(r"[0-9a-f]{40}", sha)) for sha in (merge_sha, tree)), "native index source commit/tree invalid")
    tested_merge = {"sha": merge_sha, "parents": [base, head], "tree_sha": tree}
    if recorded_candidate is None:
        verify_commit_parents_tree(client, merge_sha, [base, head], tree)
    else:
        _require(recorded_candidate.get("tested_merge") == tested_merge
                 and recorded_candidate.get("merge_commit_sha") == merge_sha
                 and recorded_candidate.get("tree_sha") == tree, "recorded tested merge parents/tree mismatch")
    identity = {"source_commit": merge_sha, "source_tree": tree, "pr_head_sha": head, "pr_base_sha": base}
    members = aggregate.get("members", {})
    _require(aggregate.get("schema") == "apg-matrix-aggregate-v1" and aggregate.get("success") is True and aggregate.get("errors") == [], "public aggregate failed")
    _require(set(members) == set(PUBLIC_PR_MEMBER_JOBS) and aggregate.get("required_members_count") == len(PUBLIC_PR_MEMBER_JOBS) and aggregate.get("verified_members_count") == len(PUBLIC_PR_MEMBER_JOBS), "public aggregate members incomplete")
    _require(aggregate.get("member_receipt_status") == {job: "success" for job in PUBLIC_PR_MEMBER_JOBS}, "public aggregate statuses incomplete")
    for job, member in members.items():
        _require(member.get("schema") == "apg-matrix-receipt-v1" and member.get("workflow") == "public-pr" and member.get("job") == job and member.get("status") == "success", "public aggregate member failed")
        _require(member.get("sha") == merge_sha and member.get("pr_head_sha") == head and member.get("pr_base_sha") == base, "public aggregate merge/head/base mismatch")
    # The aggregate JSON is the artifact authority; the log trailer is not a ZIP member.
    _index_contract(index, identity)
    expected_runs = {"public-pr-gate": public_run, "native-release-candidate-gate": native_run}
    verify_check_contexts_app(client, head, frozenset(expected_runs), expected_runs, historical=recorded_candidate is not None)
    bundle = index["bundle_artifact"]
    bundle_meta, bundle_zip = verify_artifact_download(client, native_run, "native-release-candidate-bundle", bundle.get("artifact_digest"), bundle.get("artifact_id"))
    files = inspect_zip_bytes(bundle_zip, expected_digest=bundle_meta["digest"])
    verified = verify_bundle_contents(files, version, index=index)
    branch_rules = client.get_json(f"https://api.github.com/repos/{EXPECTED_REPO}/rules/branches/main")
    if ruleset_data is None:
        ids = {r.get("ruleset_id") for r in branch_rules if r.get("type") == "required_status_checks"}
        _require(len(ids) == 1 and None not in ids, "main status-check ruleset identity missing")
        ruleset_data = client.get_json(f"https://api.github.com/repos/{EXPECTED_REPO}/rulesets/{next(iter(ids))}")
    ruleset = verify_ruleset_readback(ruleset_data)
    _require(type(ruleset.get("id")) is int and ruleset["id"] > 0, "admin ruleset id missing")
    effective = [r for r in branch_rules if r.get("ruleset_id") == ruleset["id"]]
    _require({r.get("type") for r in effective} >= {"required_status_checks", "pull_request", "non_fast_forward", "deletion"}, "public main rules do not bind admin ruleset")
    admin_rules = {r["type"]: r for r in ruleset["rules"]}
    for row in effective:
        if row["type"] in admin_rules:
            _require(row.get("parameters", {}) == admin_rules[row["type"]].get("parameters", {}), "public/admin rule parameters differ")
    author = pr.get("user", {}).get("login")
    _require(isinstance(author, str) and bool(author), "PR author identity missing")
    gov = verify_governance(client, pr_number, head, base, merge_sha, author, waiver_data,
                            waiver_scope=contract["waiver_scope"])
    count = admin_rules["pull_request"].get("parameters", {}).get("required_approving_review_count")
    _require(type(count) is int and count >= 0, "ruleset review count missing")
    _require((gov["mode"] == "waiver" and count == 0) or (gov["mode"] == "approval" and len(gov["approvals"]) >= max(1, count)), "governance cannot satisfy ruleset review count")
    facts = {
        "schema": CANDIDATE_ATTESTATION_SCHEMA, "repo": EXPECTED_REPO, "version": version,
        "pr_number": pr_number, "head_sha": head, "base_sha": base, "merge_commit_sha": merge_sha, "tree_sha": tree,
        "tested_merge": tested_merge,
        "workflow_bindings": {"public_pr": workflow_run_binding(public_run_doc, head, base, pr_number=pr_number),
                              "native": workflow_run_binding(native_run_doc, head, base, pr_number=pr_number)},
        "public_run_id": public_run, "native_run_id": native_run,
        "public_aggregate": {"artifact_id": str(public_meta["id"]), "artifact_digest": public_meta["digest"]},
        "native_index": {"artifact_id": str(gate_meta["id"]), "artifact_digest": gate_meta["digest"]},
        "governance": {**gov, "ruleset_id": ruleset["id"], "ruleset": ruleset},
        "bundle": {"bundle_artifact_id": str(bundle_meta["id"]), "bundle_digest": bundle_meta["digest"],
                   "asset_count": verified["asset_count"], "checksum_row_count": verified["checksum_row_count"],
                   "sha256sums_digest": verified["sha256sums_digest"], "manifest_digest": verified["manifest_digest"], "mapping": verified["mapping"]},
    }
    finalize_self_hash(facts)
    return facts, files


def _revalidate(client: GitHubClient, candidate: dict[str, Any]) -> None:
    validate_self_hash(candidate, label="candidate attestation")
    version, pr_number = candidate.get("version"), candidate.get("pr_number")
    _require(candidate.get("schema") == CANDIDATE_ATTESTATION_SCHEMA and version in RELEASE_CONTRACTS and candidate.get("repo") == EXPECTED_REPO, "candidate schema/repo/version/PR mismatch")
    try:
        _contract_pr(version, pr_number)
    except BoundaryError as error:
        raise BoundaryError("candidate schema/repo/version/PR mismatch") from error
    gov = candidate["governance"]
    observed, _ = _candidate_facts(client, version=version, pr_number=pr_number, head=candidate["head_sha"], base=candidate["base_sha"],
        public_run=candidate["public_run_id"], native_run=candidate["native_run_id"], ruleset_data=gov["ruleset"],
        waiver_data=gov.get("waiver"), recorded_candidate=candidate)
    _require(observed == candidate, "candidate attestation differs from current exact CI/governance evidence")


def cmd_candidate(args: argparse.Namespace) -> int:
    contract, pr_number = _contract_pr(args.version, args.pr)
    _require(args.governance_waiver is None or contract["waiver_scope"] is not None,
             f"v{args.version} is approval-only; a governance waiver is not accepted")
    client = _client()
    rules = _load_json_file(args.ruleset_admin_readback, "ruleset admin readback")
    waiver = _load_json_file(args.governance_waiver, "governance waiver") if args.governance_waiver else None
    doc, files = _candidate_facts(client, version=args.version, pr_number=pr_number, head=args.expect_head, base=args.expect_base,
        public_run=args.public_run, native_run=args.native_run, ruleset_data=rules, waiver_data=waiver)
    _require(args.output.suffix != ".json", "candidate output must be a directory")
    _safe_output(args.output)
    assets = args.output / "assets"
    assets.mkdir(parents=True, exist_ok=False)
    for logical, entry in doc["bundle"]["mapping"].items():
        target = assets / entry["flat_name"]
        with target.open("xb") as sink:
            sink.write(files[logical][2])
        _require(sha256_bytes(target.read_bytes()) == entry["sha256"], "materialized asset hash mismatch")
    _write_canonical_json(args.output / "candidate-attestation.json", doc)
    return 0


def cmd_merged(args: argparse.Namespace) -> int:
    client = _client()
    cand_doc = _load_json_file(args.candidate, "candidate attestation")
    _revalidate(client, cand_doc)
    if cand_doc.get("schema") != CANDIDATE_ATTESTATION_SCHEMA:
        raise BoundaryError(f"unexpected candidate attestation schema: {cand_doc.get('schema')}")

    version = cand_doc["version"]
    pr_number = cand_doc["pr_number"]
    pr_head = cand_doc["head_sha"]
    pr_base = cand_doc["base_sha"]
    tree_sha = cand_doc["tree_sha"]
    waiver_hash = (cand_doc.get("governance") or {}).get("waiver_sha256")

    # Fetch main branch tip to identify squash commit S
    branch_url = f"https://api.github.com/repos/{client.repository}/branches/main"
    branch = client.get_json(branch_url)
    squash_sha = (branch.get("commit") or {}).get("sha")
    if not squash_sha or not isinstance(squash_sha, str):
        raise BoundaryError("failed to retrieve main branch tip commit")

    # Verify PR state
    pr_url = f"https://api.github.com/repos/{client.repository}/pulls/{pr_number}"
    pr = client.get_json(pr_url)
    _require(pr.get("merged") is True and pr.get("merge_commit_sha") == squash_sha and pr.get("head", {}).get("sha") == pr_head, "PR merged commit/head mismatch")

    # Verify squash commit S: sole parent B, tree T, subject Release v<version>, main==S ahead_by=1
    verify_squash_and_branch(
        client, pr_number, squash_sha, pr_base, tree_sha, version, waiver_hash
    )

    tag_info = None
    if args.require_tag:
        tag_name = f"v{version}"
        tag_obj = verify_annotated_tag(client, tag_name, squash_sha)
        tag_info = {"tag_name": tag_name, "tag_sha": tag_obj.get("sha")}

    merged_doc: dict[str, Any] = {
        "schema": MERGED_ATTESTATION_SCHEMA,
        "candidate_attestation_sha256": cand_doc["self_sha256"],
        "version": version,
        "pr_number": pr_number,
        "squash_commit_sha": squash_sha,
        "parent_sha": pr_base,
        "head_sha": pr_head,
        "tree_sha": tree_sha,
        "tag": tag_info,
    }
    finalize_self_hash(merged_doc)

    _require(args.output.suffix != ".json", "merged output must be a directory")
    out_file = args.output / "merged-attestation.json"
    _write_canonical_json(out_file, merged_doc)
    notes = out_file.parent / "release-notes.md"
    _safe_output(notes)
    with notes.open("x", encoding="utf-8") as stream:
        stream.write(format_release_notes(cand_doc, merged_doc, cand_doc["governance"].get("waiver")))
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    client = _client()
    cand_doc = _load_json_file(args.candidate, "candidate attestation")
    _revalidate(client, cand_doc)

    merged_doc = _load_json_file(args.merged, "merged attestation")
    validate_self_hash(merged_doc, label="merged attestation")

    # _revalidate admitted exactly one closed contract version and its PR.
    version, pr_number = cand_doc["version"], cand_doc["pr_number"]
    expected_tag = f"v{version}"
    _require(merged_doc.get("schema") == MERGED_ATTESTATION_SCHEMA and merged_doc.get("version") == version, "merged attestation schema/version mismatch")
    _require(merged_doc.get("head_sha") == cand_doc["head_sha"] and merged_doc.get("parent_sha") == cand_doc["base_sha"] and merged_doc.get("pr_number") == pr_number, "merged identity mismatch")
    pr = client.get_json(f"https://api.github.com/repos/{EXPECTED_REPO}/pulls/{pr_number}")
    squash = merged_doc["squash_commit_sha"]
    _require(pr.get("merged") is True and pr.get("merge_commit_sha") == squash and pr.get("head", {}).get("sha") == cand_doc["head_sha"], "release PR association mismatch")
    verify_squash_and_branch(client, pr_number, squash, cand_doc["base_sha"], cand_doc["tree_sha"], version, cand_doc["governance"].get("waiver_sha256"))
    tag = verify_annotated_tag(client, expected_tag, squash)
    _require(merged_doc.get("tag") == {"tag_name": expected_tag, "tag_sha": tag["sha"]}, "release tag object changed")
    if merged_doc.get("candidate_attestation_sha256") != cand_doc.get("self_sha256"):
        raise BoundaryError("merged attestation candidate binding mismatch")
    if merged_doc.get("tree_sha") != cand_doc.get("tree_sha"):
        raise BoundaryError("merged attestation tree SHA mismatch")

    path_mapping = (cand_doc.get("bundle") or {}).get("mapping") or {}

    # Verify GitHub release object
    release = verify_github_release(client, args.release_id, expected_tag, args.state, path_mapping)

    # Verify release notes carry Candidate-Attestation-SHA256 and embedded docs
    notes = release.get("body") or ""
    parsed_notes = parse_release_notes(notes)
    if parsed_notes["candidate_attestation_sha256"] != cand_doc["self_sha256"]:
        raise BoundaryError("release notes Candidate-Attestation-SHA256 mismatch")
    if parsed_notes["merged_attestation_sha256"] != merged_doc["self_sha256"]:
        raise BoundaryError("release notes merged attestation self-hash mismatch")

    waiver_hash = (cand_doc.get("governance") or {}).get("waiver_sha256")
    if waiver_hash is not None and not parsed_notes.get("governance_waiver"):
        raise BoundaryError("release notes missing embedded governance waiver")

    release_doc: dict[str, Any] = {
        "schema": RELEASE_ATTESTATION_SCHEMA,
        "release_id": args.release_id,
        "state": args.state,
        "tag_name": expected_tag,
        "squash_commit_sha": merged_doc.get("squash_commit_sha"),
        "candidate_attestation_sha256": cand_doc["self_sha256"],
        "merged_attestation_sha256": merged_doc["self_sha256"],
        "version": version,
        "release_url": release.get("html_url"),
        "assets": {asset["name"]: {"url": asset.get("browser_download_url"), "sha256": next(e["sha256"] for e in path_mapping.values() if e["flat_name"] == asset["name"])} for asset in release["assets"]},
        "candidate": cand_doc, "merged": merged_doc,
        "package_manager_publication": "not-performed",
    }
    finalize_self_hash(release_doc)

    out_file = args.output if args.output.suffix == ".json" else args.output / "release-boundary-attestation.json"
    _write_canonical_json(out_file, release_doc)
    print(f"release attestation generated: {out_file}")
    return 0


def cmd_verify_published(args: argparse.Namespace) -> int:
    event_data = _load_json_file(args.event, "GitHub release event")
    # Early event validation before network access
    action = event_data.get("action")
    if action != "published":
        raise BoundaryError(f"event action must be 'published', got {action!r}")
    release = event_data.get("release")
    if not isinstance(release, dict):
        raise BoundaryError("event lacks release object")
    if release.get("draft") is not False:
        raise BoundaryError("published release must not be draft")
    if release.get("prerelease") is not False:
        raise BoundaryError("published release must not be prerelease")
    # The event tag selects one closed contract; every other tag refuses here.
    tag_name = release.get("tag_name")
    supported_tags = {f"v{version}": version for version in RELEASE_CONTRACTS}
    if tag_name not in supported_tags:
        raise BoundaryError(f"published release tag mismatch: {tag_name} is not one of {sorted(supported_tags)}")

    _require(event_data.get("repository", {}).get("full_name") == EXPECTED_REPO and event_data.get("repository", {}).get("id") == 1306002537, "release event repository mismatch")
    _require(os.environ.get("GITHUB_REPOSITORY") == EXPECTED_REPO, "wrong GITHUB_REPOSITORY")
    _client()  # validates environment before any network access
    _safe_output(args.output)
    parsed = parse_release_notes(release.get("body") or "")
    _require(parsed["candidate_attestation"].get("version") == supported_tags[tag_name], "release notes candidate version differs from the published tag")
    # Reuse the exact draft/published verification contract through private temp
    # inputs beneath --output. No assets are materialized by this audit.
    args.output.mkdir(parents=True, exist_ok=False)
    candidate = args.output / "candidate-attestation.json"
    merged = args.output / "merged-attestation.json"
    _write_canonical_json(candidate, parsed["candidate_attestation"])
    _write_canonical_json(merged, parsed["merged_attestation"])
    return cmd_release(argparse.Namespace(candidate=candidate, merged=merged, release_id=release["id"], state="published", output=args.output / "published-verification.json"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release_boundary",
        description="APGR release boundary attestation verifier (closed v0.13.0 and v0.13.1 contracts)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # candidate
    p_cand = subparsers.add_parser("candidate", help="Verify candidate PR, runs, and governance")
    p_cand.add_argument("--version", choices=sorted(RELEASE_CONTRACTS), default=EXPECTED_VERSION, help="Closed release contract version")
    p_cand.add_argument("--pr", type=int, required=True, help="Measured staging PR number (v0.13.0 is pinned to PR 3)")
    p_cand.add_argument("--expect-head", type=str, required=True, help="Expected head commit SHA (H)")
    p_cand.add_argument("--expect-base", type=str, required=True, help="Expected base commit SHA (B)")
    p_cand.add_argument("--public-run", type=str, required=True, help="Public workflow run ID (R1)")
    p_cand.add_argument("--native-run", type=str, required=True, help="Native workflow run ID (R2)")
    p_cand.add_argument("--output", type=Path, required=True, help="Output directory or JSON path")
    p_cand.add_argument("--ruleset-admin-readback", type=Path, required=True, help="Ruleset admin readback JSON")
    p_cand.add_argument("--governance-waiver", type=Path, default=None, help="Optional governance waiver JSON")

    # merged
    p_merged = subparsers.add_parser("merged", help="Verify squash commit, tree, and main branch state")
    p_merged.add_argument("--candidate", type=Path, required=True, help="Path to candidate attestation JSON")
    p_merged.add_argument("--output", type=Path, required=True, help="Output directory or JSON path")
    p_merged.add_argument("--require-tag", action="store_true", help="Require and verify the annotated v<version> tag")

    # release
    p_rel = subparsers.add_parser("release", help="Verify draft or published release, notes, and 16 flat assets")
    p_rel.add_argument("--candidate", type=Path, required=True, help="Path to candidate attestation JSON")
    p_rel.add_argument("--merged", type=Path, required=True, help="Path to merged attestation JSON")
    p_rel.add_argument("--release-id", type=int, required=True, help="GitHub release ID")
    p_rel.add_argument("--state", choices=["draft", "published"], required=True, help="Expected release state")
    p_rel.add_argument("--output", type=Path, required=True, help="Output directory or JSON path")

    # verify-published
    p_ver = subparsers.add_parser("verify-published", help="Postpublication audit from release event")
    p_ver.add_argument("--event", type=Path, required=True, help="Path to GitHub release event JSON")
    p_ver.add_argument("--output", type=Path, required=True, help="Output directory or JSON path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.subcommand == "candidate":
            return cmd_candidate(args)
        if args.subcommand == "merged":
            return cmd_merged(args)
        if args.subcommand == "release":
            return cmd_release(args)
        if args.subcommand == "verify-published":
            return cmd_verify_published(args)
        raise BoundaryError(f"unknown subcommand: {args.subcommand}")
    except (BoundaryError, GitHubBoundaryError, BoundaryBundleError, OSError, KeyError, TypeError, ValueError) as err:
        print(f"release_boundary error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
