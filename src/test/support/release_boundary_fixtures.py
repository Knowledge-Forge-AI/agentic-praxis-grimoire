"""Test support fixtures and FakeGitHub in-memory server for release boundary tests."""

from __future__ import annotations

import io
import urllib.error
import zipfile
from typing import Any

from release.ci.matrix_receipts import PUBLIC_PR_MEMBER_JOBS
from tools.ci import native_seal
from tools.ci.native_seal import CANONICAL_TARGETS, REQUIRED_LANES
from tools.ci.release_boundary_bundle import (
    CHECKSUM_NAME,
    EXPECTED_VERSION,
    GOVERNANCE_WAIVER_SCHEMA,
    MANIFEST_NAME,
    canonical_flat_assets,
    canonical_json,
    canonical_logical_paths,
    finalize_self_hash,
    logical_path_to_flat_name,
    sha256_bytes,
)
from tools.ci.release_boundary_github import (
    EXPECTED_REPO,
    EXPECTED_REPO_ID,
    GITHUB_ACTIONS_APP_ID,
    REQUIRED_NATIVE_JOBS,
    REQUIRED_PR_JOBS,
    REQUIRED_RULESET_CONTEXTS,
)

HEAD_SHA = "1111111111111111111111111111111111111111"
BASE_SHA = "2222222222222222222222222222222222222222"
MERGE_SHA = "3333333333333333333333333333333333333333"
TREE_SHA = "4444444444444444444444444444444444444444"
SQUASH_SHA = "5555555555555555555555555555555555555555"
TAG_SHA = "6666666666666666666666666666666666666666"

PUBLIC_RUN_ID = "901"
NATIVE_RUN_ID = "902"
GATE_ARTIFACT_ID = "1001"
BUNDLE_ARTIFACT_ID = "1002"
PUBLIC_GATE_ARTIFACT_ID = "1003"
RULESET_ID = 1234
PR_NUMBER = 3
RELEASE_ID = 888

AUTHOR_LOGIN = "developer-a"
REVIEWER_LOGIN = "reviewer-b"


class FakeHTTPResponse(io.BytesIO):
    def __init__(self, data: bytes, headers: dict[str, str] | None = None) -> None:
        super().__init__(data)
        self.headers = headers or {"Content-Type": "application/vnd.github+json"}


class FakeGitHub:
    """In-memory GitHub API router for testing the release boundary network seam."""

    def __init__(self) -> None:
        self.routes: dict[str, tuple[bytes, dict[str, str]]] = {}
        self.redirects: dict[str, tuple[str, int]] = {}
        self.calls: list[str] = []
        self.call_headers: list[dict[str, str]] = []

    def set_route(self, url: str, data: bytes | str, content_type: str = "application/vnd.github+json") -> None:
        payload = data.encode("utf-8") if isinstance(data, str) else data
        self.routes[url] = (payload, {"Content-Type": content_type})

    def set_json(self, url: str, data: Any) -> None:
        self.set_route(url, canonical_json(data))

    def set_redirect(self, url: str, location: str, code: int = 302) -> None:
        self.redirects[url] = (location, code)

    def __call__(self, request: Any) -> FakeHTTPResponse:
        url = request.full_url
        self.calls.append(url)
        headers = dict(request.headers.items()) if hasattr(request, "headers") else {}
        self.call_headers.append(headers)

        if request.get_method() != "GET":
            raise urllib.error.HTTPError(url, 405, "Method Not Allowed", {}, None)

        if url in self.redirects:
            loc, code = self.redirects[url]
            raise urllib.error.HTTPError(url, code, "Redirect", {"Location": loc}, None)

        if url not in self.routes:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        payload, resp_headers = self.routes[url]
        return FakeHTTPResponse(payload, resp_headers)


def build_test_bundle_zip(
    version: str = EXPECTED_VERSION,
    source_commit: str = MERGE_SHA,
    source_tree: str = TREE_SHA,
    lane_seals: dict[str, str] | None = None,
) -> tuple[bytes, dict[str, str], dict[str, bytes], dict[str, Any]]:
    """Build a truthful 17-file zip bundle and return (zip_bytes, sums_map, file_bytes, seal_doc)."""
    buf = io.BytesIO()
    logical_paths = canonical_logical_paths(version=version)
    file_bytes: dict[str, bytes] = {}
    file_digests: dict[str, str] = {}

    for path in sorted(logical_paths):
        if path == MANIFEST_NAME:
            manifest_doc = {
                "schema_version": "apg.distribution-manifest/v1",
                "version": version,
                "source_commit": source_commit,
                "source_tree": source_tree,
                "python": {"package": "agentic-praxis-grimoire"},
            }
            content = canonical_json(manifest_doc)
        else:
            content = f"content-for-{path}".encode()
        file_bytes[path] = content
        file_digests[path] = sha256_bytes(content)

    sums_lines = [f"{file_digests[p]}  {p}\n" for p in sorted(file_digests.keys())]
    sha256sums_bytes = "".join(sums_lines).encode("ascii")
    file_bytes[CHECKSUM_NAME] = sha256sums_bytes
    file_digests[CHECKSUM_NAME] = sha256_bytes(sha256sums_bytes)

    # 17th file: release-bundle-seal.json
    seal_name = "release-bundle-seal.json"
    files_meta = {p: {"sha256": file_digests[p], "size_bytes": len(file_bytes[p])} for p in sorted(file_bytes.keys())}
    asset_paths = set(files_meta) - {MANIFEST_NAME, CHECKSUM_NAME} - {p for p in files_meta if p.endswith(".binary-manifest.json")}
    lane_seals_map = lane_seals or {lane: "e" * 64 for lane in sorted(REQUIRED_LANES)}

    seal_doc: dict[str, Any] = {
        "schema_version": native_seal.RELEASE_BUNDLE_SEAL_SCHEMA,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "lane_seals": lane_seals_map,
        "manifest_sha256": file_digests[MANIFEST_NAME],
        "checksums_sha256": file_digests[CHECKSUM_NAME],
        "files": files_meta,
        "assets": {p: files_meta[p] for p in sorted(asset_paths)},
        "asset_count": 11,
    }
    finalize_self_hash(seal_doc, key="bundle_seal_sha256")
    seal_bytes = canonical_json(seal_doc)
    file_bytes[seal_name] = seal_bytes
    file_digests[seal_name] = sha256_bytes(seal_bytes)

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(file_bytes.keys()):
            zf.writestr(path, file_bytes[path])

    sums_map = {p: file_digests[p] for p in sorted(logical_paths)}
    return buf.getvalue(), sums_map, file_bytes, seal_doc


def build_test_public_gate_zip(
    source_commit: str = MERGE_SHA,
    head_sha: str = HEAD_SHA,
    base_sha: str = BASE_SHA,
) -> tuple[bytes, dict[str, Any]]:
    """Build synthetic public-pr-gate-result artifact with matrix-aggregate.json."""
    aggregate_doc: dict[str, Any] = {
        "schema": "apg-matrix-aggregate-v1",
        "success": True,
        "errors": [],
        "required_members_count": len(PUBLIC_PR_MEMBER_JOBS),
        "verified_members_count": len(PUBLIC_PR_MEMBER_JOBS),
        "member_receipt_status": {job: "success" for job in sorted(PUBLIC_PR_MEMBER_JOBS)},
        "members": {
            job: {
                "schema": "apg-matrix-receipt-v1",
                "workflow": "public-pr",
                "job": job,
                "status": "success",
                "sha": source_commit,
                "pr_head_sha": head_sha,
                "pr_base_sha": base_sha,
            }
            for job in sorted(PUBLIC_PR_MEMBER_JOBS)
        },
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("matrix-aggregate.json", canonical_json(aggregate_doc))
    return buf.getvalue(), aggregate_doc


def build_test_gate_index_zip(
    source_commit: str = MERGE_SHA,
    source_tree: str = TREE_SHA,
    head_sha: str = HEAD_SHA,
    base_sha: str = BASE_SHA,
    bundle_digest: str | None = None,
    bundle_seal: dict[str, Any] | None = None,
    bundle_zip_bytes: bytes | None = None,
    lane_seals: dict[str, str] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Build synthetic native gate artifact containing native-rc-index.json."""
    lanes_map = lane_seals or {lane: "e" * 64 for lane in sorted(REQUIRED_LANES)}
    lane_artifacts = {
        lane: {
            "target": CANONICAL_TARGETS[lane]["target"],
            "seal_sha256": lanes_map[lane],
            "file_sha256": "f" * 64,
        }
        for lane in sorted(REQUIRED_LANES)
    }

    b_digest = bundle_digest or (f"sha256:{sha256_bytes(bundle_zip_bytes)}" if bundle_zip_bytes else "sha256:" + "a" * 64)
    bundle_artifact = {
        "artifact_id": BUNDLE_ARTIFACT_ID,
        "artifact_digest": b_digest,
        "asset_count": 11,
        "seal_sha256": bundle_seal["bundle_seal_sha256"] if bundle_seal else "b" * 64,
        "file_sha256": sha256_bytes(canonical_json(bundle_seal)) if bundle_seal else "b" * 64,
        "manifest_sha256": bundle_seal["manifest_sha256"] if bundle_seal else "m" * 64,
        "checksums_sha256": bundle_seal["checksums_sha256"] if bundle_seal else "c" * 64,
        "consumers": {lane: {"status": "passed"} for lane in sorted(REQUIRED_LANES)},
        "scans": {
            "status": "passed",
            "asset_count": 11,
            "scan_count": 14,
            "receipt_sha256": "9" * 64,
            "receipt_file_sha256": "9" * 64,
            "results_sha256": "9" * 64,
        },
    }

    index_doc: dict[str, Any] = {
        "schema": "apgr.native-rc-index/v1",
        "status": "passed",
        "retention_class": "routine",
        "source_commit": source_commit,
        "source_tree": source_tree,
        "pr_head_sha": head_sha,
        "pr_base_sha": base_sha,
        "members": {
            job: {
                "name": job,
                "status": "passed",
                "source_commit": source_commit,
                "source_tree": source_tree,
                "pr_head_sha": head_sha,
                "pr_base_sha": base_sha,
                "matrix_receipt_sha256": "8" * 64,
            }
            for job in sorted(REQUIRED_NATIVE_JOBS - {"native-release-candidate-gate"})
        },
        "lane_artifacts": lane_artifacts,
        "bundle_artifact": bundle_artifact,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("native-rc-index.json", canonical_json(index_doc))
    return buf.getvalue(), index_doc


def make_ruleset_readback(
    contexts: set[str] | None = None,
    strict: bool = True,
    bypass_actors: list[Any] | None = None,
    active: bool = True,
    rule_types: set[str] | None = None,
    ruleset_id: int = RULESET_ID,
    review_count: int = 1,
) -> dict[str, Any]:
    """Generate admin readback data for branch ruleset."""
    ctx_list = sorted(contexts if contexts is not None else REQUIRED_RULESET_CONTEXTS)
    status_checks = [{"context": c, "integration_id": GITHUB_ACTIONS_APP_ID} for c in ctx_list]

    types = rule_types or {"pull_request", "non_fast_forward", "deletion", "required_status_checks"}
    rules = []
    for rt in sorted(types):
        if rt == "required_status_checks":
            rules.append({
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": strict,
                    "required_status_checks": status_checks,
                },
            })
        elif rt == "pull_request":
            rules.append({
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": review_count,
                },
            })
        else:
            rules.append({"type": rt, "parameters": {}})

    return {
        "id": ruleset_id,
        "name": "main-branch-protection",
        "target": "branch",
        "enforcement": "active" if active else "disabled",
        "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
        "bypass_actors": bypass_actors or [],
        "rules": rules,
    }


def make_governance_waiver(
    head_sha: str = HEAD_SHA,
    base_sha: str = BASE_SHA,
    merge_sha: str = MERGE_SHA,
    reason: str = "emergency fix authorized by maintainer",
    approved_by: str = "maintainer",
    approved_at: str = "2026-10-13T00:00:00Z",
) -> dict[str, Any]:
    """Generate a canonical governance waiver document."""
    doc: dict[str, Any] = {
        "schema": GOVERNANCE_WAIVER_SCHEMA,
        "version": EXPECTED_VERSION,
        "repo": EXPECTED_REPO,
        "pr": PR_NUMBER,
        "scope": "v0.13.0-review-only",
        "pr_head_sha": head_sha,
        "pr_base_sha": base_sha,
        "merge_ref_sha": merge_sha,
        "reason": reason,
        "approved_by": approved_by,
        "approved_at": approved_at,
    }
    finalize_self_hash(doc)
    return doc


def populate_fake_github(
    gh: FakeGitHub,
    bundle_zip_bytes: bytes,
    gate_zip_bytes: bytes,
    public_gate_zip_bytes: bytes | None = None,
    bundle_file_bytes: dict[str, bytes] | None = None,
    pr_state: str = "open",
    approval_mode: str = "approval",
    review_count: int = 1,
    tag_type: str = "tag",
    include_release: bool = True,
    release_notes: str = "",
    release_state: str = "published",
    author_login: str = AUTHOR_LOGIN,
    reviewer_login: str = REVIEWER_LOGIN,
    reviewer_association: str = "MEMBER",
    waiver_hash: str | None = None,
    head_sha: str = HEAD_SHA,
    base_sha: str = BASE_SHA,
    merge_sha: str = MERGE_SHA,
    tree_sha: str = TREE_SHA,
    squash_sha: str = SQUASH_SHA,
    tag_sha: str = TAG_SHA,
) -> None:
    """Populate FakeGitHub with realistic and truthful passing routes for candidate, merged, and release."""
    api = f"https://api.github.com/repos/{EXPECTED_REPO}"

    if public_gate_zip_bytes is None:
        public_gate_zip_bytes, _ = build_test_public_gate_zip(source_commit=merge_sha, head_sha=head_sha, base_sha=base_sha)

    # 1. Pull request route
    is_merged = (pr_state == "merged")
    gh.set_json(f"{api}/pulls/{PR_NUMBER}", {
        "number": PR_NUMBER,
        "state": "closed" if is_merged else "open",
        "merged": is_merged,
        "draft": False,
        "merged_at": "2026-10-13T01:00:00Z" if is_merged else None,
        "merge_commit_sha": squash_sha if is_merged else merge_sha,
        "base": {"ref": "main", "sha": base_sha, "repo": {"id": EXPECTED_REPO_ID, "full_name": EXPECTED_REPO}},
        "head": {"ref": "staging", "sha": head_sha, "repo": {"id": EXPECTED_REPO_ID, "full_name": EXPECTED_REPO}},
        "user": {"login": author_login},
    })

    # PR pre-merge test commit M
    if is_merged:
        gh.routes.pop(f"{api}/git/commits/{merge_sha}", None)
    else:
        gh.set_json(f"{api}/git/commits/{merge_sha}", {
            "sha": merge_sha,
            "parents": [{"sha": base_sha}, {"sha": head_sha}],
            "tree": {"sha": tree_sha},
            "message": "Merge staging into main",
        })

    # 2. PR Reviews route
    if approval_mode == "approval":
        gh.set_json(f"{api}/pulls/{PR_NUMBER}/reviews?per_page=100", [
            {
                "id": 401,
                "user": {"login": reviewer_login},
                "state": "APPROVED",
                "commit_id": head_sha,
                "author_association": reviewer_association,
            },
        ])
    else:
        gh.set_json(f"{api}/pulls/{PR_NUMBER}/reviews?per_page=100", [])

    # 3. Public PR run R1
    gh.set_json(f"{api}/actions/runs/{PUBLIC_RUN_ID}", {
        "id": int(PUBLIC_RUN_ID),
        "run_attempt": 1,
        "workflow_id": 7001,
        "check_suite_id": 7101,
        "status": "completed",
        "conclusion": "success",
        "head_sha": head_sha,
        "head_branch": "staging",
        "event": "pull_request",
        "path": ".github/workflows/public-pr.yml",
        "repository": {"id": EXPECTED_REPO_ID, "full_name": EXPECTED_REPO},
        "head_repository": {"id": EXPECTED_REPO_ID, "full_name": EXPECTED_REPO},
        "pull_requests": [] if is_merged else [{"number": PR_NUMBER, "head": {"sha": head_sha}, "base": {"sha": base_sha}}],
    })
    gh.set_json(
        f"{api}/actions/runs/{PUBLIC_RUN_ID}/jobs?per_page=100",
        {
            "total_count": len(REQUIRED_PR_JOBS),
            "jobs": [{"name": job, "status": "completed", "conclusion": "success"} for job in sorted(REQUIRED_PR_JOBS)],
        },
    )
    pub_digest = f"sha256:{sha256_bytes(public_gate_zip_bytes)}"
    gh.set_json(f"{api}/actions/runs/{PUBLIC_RUN_ID}/artifacts?per_page=100", {
        "total_count": 1,
        "artifacts": [
            {
                "id": int(PUBLIC_GATE_ARTIFACT_ID),
                "name": "public-pr-gate-result",
                "expired": False,
                "expires_at": "2099-01-01T00:00:00Z",
                "size_in_bytes": len(public_gate_zip_bytes),
                "digest": pub_digest,
                "workflow_run": {
                    "id": int(PUBLIC_RUN_ID),
                    "repository_id": EXPECTED_REPO_ID,
                    "head_repository_id": EXPECTED_REPO_ID,
                },
            },
        ],
    })
    gh.set_route(f"{api}/actions/artifacts/{PUBLIC_GATE_ARTIFACT_ID}/zip", public_gate_zip_bytes, "application/zip")

    # 4. Native qualification run R2
    gh.set_json(f"{api}/actions/runs/{NATIVE_RUN_ID}", {
        "id": int(NATIVE_RUN_ID),
        "run_attempt": 1,
        "workflow_id": 7002,
        "check_suite_id": 7102,
        "status": "completed",
        "conclusion": "success",
        "head_sha": head_sha,
        "head_branch": "staging",
        "event": "pull_request",
        "path": ".github/workflows/native-qualification.yml",
        "repository": {"id": EXPECTED_REPO_ID, "full_name": EXPECTED_REPO},
        "head_repository": {"id": EXPECTED_REPO_ID, "full_name": EXPECTED_REPO},
        "pull_requests": [] if is_merged else [{"number": PR_NUMBER, "head": {"sha": head_sha}, "base": {"sha": base_sha}}],
    })
    gh.set_json(
        f"{api}/actions/runs/{NATIVE_RUN_ID}/jobs?per_page=100",
        {
            "total_count": len(REQUIRED_NATIVE_JOBS),
            "jobs": [{"name": job, "status": "completed", "conclusion": "success"} for job in sorted(REQUIRED_NATIVE_JOBS)],
        },
    )
    gate_digest = f"sha256:{sha256_bytes(gate_zip_bytes)}"
    bundle_digest = f"sha256:{sha256_bytes(bundle_zip_bytes)}"
    gh.set_json(f"{api}/actions/runs/{NATIVE_RUN_ID}/artifacts?per_page=100", {
        "total_count": 2,
        "artifacts": [
            {
                "id": int(GATE_ARTIFACT_ID),
                "name": "native-release-candidate-gate-result",
                "expired": False,
                "expires_at": "2099-01-01T00:00:00Z",
                "size_in_bytes": len(gate_zip_bytes),
                "digest": gate_digest,
                "workflow_run": {
                    "id": int(NATIVE_RUN_ID),
                    "repository_id": EXPECTED_REPO_ID,
                    "head_repository_id": EXPECTED_REPO_ID,
                },
            },
            {
                "id": int(BUNDLE_ARTIFACT_ID),
                "name": "native-release-candidate-bundle",
                "expired": False,
                "expires_at": "2099-01-01T00:00:00Z",
                "size_in_bytes": len(bundle_zip_bytes),
                "digest": bundle_digest,
                "workflow_run": {
                    "id": int(NATIVE_RUN_ID),
                    "repository_id": EXPECTED_REPO_ID,
                    "head_repository_id": EXPECTED_REPO_ID,
                },
            },
        ],
    })
    gh.set_route(f"{api}/actions/artifacts/{GATE_ARTIFACT_ID}/zip", gate_zip_bytes, "application/zip")
    gh.set_route(f"{api}/actions/artifacts/{BUNDLE_ARTIFACT_ID}/zip", bundle_zip_bytes, "application/zip")

    # 5. Check-runs for commit H (only 2 aggregate contexts required)
    gh.set_json(f"{api}/commits/{head_sha}/check-runs?per_page=100", {
        "total_count": 2,
        "check_runs": [
            {
                "id": 8001,
                "name": "public-pr-gate",
                "status": "completed",
                "conclusion": "success",
                "app": {"id": GITHUB_ACTIONS_APP_ID},
                "html_url": f"https://github.com/{EXPECTED_REPO}/actions/runs/{PUBLIC_RUN_ID}/job/9001",
            },
            {
                "id": 8002,
                "name": "native-release-candidate-gate",
                "status": "completed",
                "conclusion": "success",
                "app": {"id": GITHUB_ACTIONS_APP_ID},
                "html_url": f"https://github.com/{EXPECTED_REPO}/actions/runs/{NATIVE_RUN_ID}/job/9002",
            },
        ],
    })

    # 6. Ruleset routes
    admin_ruleset = make_ruleset_readback(review_count=(0 if approval_mode == "waiver" else review_count))
    gh.set_json(f"{api}/rulesets/{RULESET_ID}", admin_ruleset)
    effective_rules = [
        {"ruleset_id": RULESET_ID, "type": r["type"], "parameters": r.get("parameters", {})}
        for r in admin_ruleset["rules"]
    ]
    gh.set_json(f"{api}/rules/branches/main", effective_rules)

    # 7. Squash commit S and branch main
    commit_msg = f"Release v{EXPECTED_VERSION}"
    if waiver_hash:
        commit_msg += f"\n\nGovernance-Waiver-SHA256: {waiver_hash}"
    gh.set_json(f"{api}/commits/{squash_sha}", {
        "sha": squash_sha,
        "parents": [{"sha": base_sha}],
        "commit": {
            "tree": {"sha": tree_sha},
            "message": commit_msg,
        },
    })
    gh.set_json(f"{api}/commits/{squash_sha}/pulls", [{"number": PR_NUMBER}])
    gh.set_json(f"{api}/branches/main", {
        "name": "main",
        "commit": {"sha": squash_sha},
    })
    gh.set_json(f"{api}/compare/{base_sha}...{squash_sha}", {
        "status": "ahead",
        "ahead_by": 1,
        "behind_by": 0,
    })

    # 8. Tag v0.13.0
    if tag_type == "tag":
        gh.set_json(f"{api}/git/ref/tags/v{EXPECTED_VERSION}", {
            "ref": f"refs/tags/v{EXPECTED_VERSION}",
            "object": {"sha": tag_sha, "type": "tag"},
        })
        gh.set_json(f"{api}/git/tags/{tag_sha}", {
            "tag": f"v{EXPECTED_VERSION}",
            "sha": tag_sha,
            "message": f"Release v{EXPECTED_VERSION}\n",
            "object": {"sha": squash_sha, "type": "commit"},
        })
    elif tag_type == "lightweight":
        gh.set_json(f"{api}/git/ref/tags/v{EXPECTED_VERSION}", {
            "ref": f"refs/tags/v{EXPECTED_VERSION}",
            "object": {"sha": squash_sha, "type": "commit"},
        })

    # 9. GitHub Release with 16 flat assets
    if include_release:
        flat_names = canonical_flat_assets(version=EXPECTED_VERSION)
        assets = []
        for i, flat_name in enumerate(flat_names):
            asset_id = 5000 + i
            # Find matching content
            if bundle_file_bytes is not None:
                if flat_name == CHECKSUM_NAME:
                    content = bundle_file_bytes[CHECKSUM_NAME]
                else:
                    logical = next(lp for lp in canonical_logical_paths(EXPECTED_VERSION) if logical_path_to_flat_name(lp) == flat_name)
                    content = bundle_file_bytes[logical]
            else:
                content = b"sample-bytes"

            c_hash = sha256_bytes(content)
            assets.append({
                "id": asset_id,
                "name": flat_name,
                "size": len(content),
                "digest": f"sha256:{c_hash}",
                "state": "uploaded",
                "browser_download_url": f"https://github.com/{EXPECTED_REPO}/releases/download/v{EXPECTED_VERSION}/{flat_name}",
            })
            gh.set_route(f"{api}/releases/assets/{asset_id}", content, "application/octet-stream")

        gh.set_json(f"{api}/releases/{RELEASE_ID}", {
            "id": RELEASE_ID,
            "tag_name": f"v{EXPECTED_VERSION}",
            "draft": (release_state == "draft"),
            "prerelease": False,
            "body": release_notes,
            "html_url": f"https://github.com/{EXPECTED_REPO}/releases/tag/v{EXPECTED_VERSION}",
            "assets": assets,
        })
