"""Read-only GitHub API client and domain verifications for APGR release boundary."""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from tools.ci.release_boundary_bundle import (
    GOVERNANCE_WAIVER_SCHEMA,
    canonical_flat_assets,
    compute_self_hash,
    sha256_bytes,
    strict_json,
    validate_self_hash,
)

EXPECTED_REPO = "Knowledge-Forge-AI/agentic-praxis-grimoire"
EXPECTED_REPO_ID = 1306002537
API_ROOT = "https://api.github.com"
GITHUB_ACTIONS_APP_ID = 15368
USER_AGENT = "apgr-release-boundary"

MAX_REDIRECTS = 3
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
MAX_JSON_BYTES = 10 * 1024 * 1024
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024

REQUIRED_PR_JOBS = frozenset({
    "guard",
    "static-analysis",
    "policy",
    "unit-integration",
    "closure",
    "go",
    "codeql (go)",
    "codeql (python)",
    "codeql (javascript-typescript)",
    "codeql (actions)",
    "public-pr-gate",
})

REQUIRED_NATIVE_JOBS = frozenset({
    "native-guard",
    "native-darwin-arm64",
    "native-linux-x64",
    "native-linux-arm64",
    "native-assemble",
    "native-consumer-darwin-arm64",
    "native-consumer-linux-x64",
    "native-consumer-linux-arm64",
    "native-release-scans",
    "native-release-candidate-gate",
})

REQUIRED_RULESET_CONTEXTS = frozenset({"public-pr-gate", "native-release-candidate-gate"})


class GitHubBoundaryError(ValueError):
    """GitHub boundary contract failure."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _open(request: urllib.request.Request) -> Any:
    """Network seam; opener never follows redirects on its own."""
    return _OPENER.open(request, timeout=300)


class GitHubClient:
    """GET-only client contacting the fixed repository API."""

    def __init__(self, token: str = "", repository: str = EXPECTED_REPO) -> None:
        self.token = token
        self.repository = repository

    def _request(
        self,
        url: str,
        accept: str,
        limit: int,
    ) -> tuple[bytes, Mapping[str, str]]:
        if not url.startswith("https://"):
            raise GitHubBoundaryError("URL must use HTTPS protocol")
        if self.repository != EXPECTED_REPO or not url.startswith(f"{API_ROOT}/repos/{self.repository}/"):
            raise GitHubBoundaryError(f"refusing to contact URL outside {EXPECTED_REPO}: {url}")

        headers: dict[str, str] = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        current_url = url
        for _ in range(MAX_REDIRECTS + 1):
            req = urllib.request.Request(current_url, headers=headers, method="GET")
            try:
                response = _open(req)
            except urllib.error.HTTPError as error:
                if error.code not in REDIRECT_CODES:
                    raise GitHubBoundaryError(f"GitHub GET failed: HTTP {error.code}") from error
                loc = error.headers.get("Location") if error.headers is not None else None
                if getattr(error, "fp", None) is not None:
                    error.close()
                if not loc or not loc.startswith("https://"):
                    raise GitHubBoundaryError("redirect target is missing or not HTTPS") from error
                # Do not forward credentials across hosts or redirects
                headers = {"User-Agent": USER_AGENT}
                current_url = loc
                continue
            except (urllib.error.URLError, OSError) as error:
                raise GitHubBoundaryError(f"GitHub GET error: {type(error).__name__}") from error

            with response:
                payload = response.read(limit + 1)
                if len(payload) > limit:
                    raise GitHubBoundaryError(f"response exceeded limit of {limit} bytes")
                resp_headers = dict(response.headers.items()) if response.headers is not None else {}
                return payload, resp_headers
        raise GitHubBoundaryError("exceeded redirect limit")

    def get_json(self, url: str) -> Any:
        data, _ = self._request(url, accept="application/vnd.github+json", limit=MAX_JSON_BYTES)
        return strict_json(data, "GitHub API response")

    def get_bytes(self, url: str, limit: int = MAX_ARCHIVE_BYTES) -> bytes:
        data, _ = self._request(url, accept="application/vnd.github+json", limit=limit)
        return data


def verify_pull_request(
    client: GitHubClient,
    pr_number: int,
    expected_head: str,
    expected_base: str,
    *, allow_merged: bool = False,
) -> dict[str, Any]:
    """Verify PR metadata, head, base, repository identity, and test merge commit."""
    pr_url = f"{API_ROOT}/repos/{client.repository}/pulls/{pr_number}"
    pr = client.get_json(pr_url)
    if not isinstance(pr, dict):
        raise GitHubBoundaryError(f"invalid PR response: {pr}")

    head = pr.get("head") or {}
    base = pr.get("base") or {}
    head_repo = head.get("repo") or {}
    base_repo = base.get("repo") or {}

    if base.get("ref") != "main":
        raise GitHubBoundaryError(f"PR base ref must be 'main', got {base.get('ref')!r}")
    if head.get("ref") != "staging":
        raise GitHubBoundaryError(f"PR head ref must be 'staging', got {head.get('ref')!r}")
    if head_repo.get("full_name") != EXPECTED_REPO or base_repo.get("full_name") != EXPECTED_REPO:
        raise GitHubBoundaryError("PR must originate from and target the canonical non-fork repository")
    if head_repo.get("id") != EXPECTED_REPO_ID or base_repo.get("id") != EXPECTED_REPO_ID:
        raise GitHubBoundaryError("PR repository ID mismatch")

    head_sha = head.get("sha")
    base_sha = base.get("sha")
    if head_sha != expected_head:
        raise GitHubBoundaryError(f"PR head SHA mismatch: {head_sha} != {expected_head}")
    if not allow_merged and base_sha != expected_base:
        raise GitHubBoundaryError(f"PR base SHA mismatch: {base_sha} != {expected_base}")

    if type(pr_number) is not int or pr_number <= 0 or pr.get("number") != pr_number:
        raise GitHubBoundaryError(f"release boundary requires exact PR #{pr_number}")
    merge_commit_sha = pr.get("merge_commit_sha")
    if not isinstance(merge_commit_sha, str) or not re.match(r"^[0-9a-f]{40}$", merge_commit_sha):
        raise GitHubBoundaryError(f"PR lacks a valid merge_commit_sha: {merge_commit_sha!r}")

    return pr


def verify_commit_parents_tree(
    client: GitHubClient,
    commit_sha: str,
    expected_parents: list[str],
    expected_tree: str | None = None,
) -> dict[str, Any]:
    """Verify git commit object parents and tree SHA."""
    url = f"{API_ROOT}/repos/{client.repository}/git/commits/{commit_sha}"
    commit = client.get_json(url)
    if not isinstance(commit, dict):
        raise GitHubBoundaryError(f"invalid commit object: {commit}")

    if commit.get("sha") != commit_sha:
        raise GitHubBoundaryError("commit object SHA mismatch")
    parents = commit.get("parents") or []
    parent_shas = [p.get("sha") if isinstance(p, dict) else p for p in parents]
    if parent_shas != expected_parents:
        raise GitHubBoundaryError(f"commit {commit_sha} parents mismatch: {parent_shas} != {expected_parents}")

    tree = commit.get("tree") or {}
    tree_sha = tree.get("sha") if isinstance(tree, dict) else tree
    if not isinstance(tree_sha, str) or not re.match(r"^[0-9a-f]{40}$", tree_sha):
        raise GitHubBoundaryError(f"commit {commit_sha} has invalid tree: {tree_sha!r}")
    if expected_tree is not None and tree_sha != expected_tree:
        raise GitHubBoundaryError(f"commit {commit_sha} tree mismatch: {tree_sha} != {expected_tree}")

    return commit


def workflow_run_binding(run: Mapping[str, Any], head: str, base: str | None, *, pr_number: int) -> dict[str, Any]:
    """Capture durable run identity and the association verified before merge."""
    for key in ("run_attempt", "workflow_id", "check_suite_id"):
        if type(run.get(key)) is not int or run[key] <= 0:
            raise GitHubBoundaryError(f"workflow run lacks valid {key}")
    return {
        "run_id": str(run["id"]), "run_attempt": run["run_attempt"],
        "workflow_id": run["workflow_id"], "check_suite_id": run["check_suite_id"],
        "path": run["path"], "event": run["event"], "head_branch": run["head_branch"],
        "head_sha": run["head_sha"],
        "repository": {key: run["repository"][key] for key in ("id", "full_name")},
        "head_repository": {key: run["head_repository"][key] for key in ("id", "full_name")},
        "pr_number": pr_number, "pr_head_sha": head, "pr_base_sha": base,
    }


def verify_workflow_run(
    client: GitHubClient,
    run_id: str,
    expected_head: str,
    expected_jobs: frozenset[str],
    workflow_label: str,
    expected_base: str | None = None,
    *, pr_number: int, recorded_binding: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify workflow run conclusion, head SHA, PR event, and exact successful jobs."""
    url = f"{API_ROOT}/repos/{client.repository}/actions/runs/{run_id}"
    run = client.get_json(url)
    if not isinstance(run, dict):
        raise GitHubBoundaryError(f"invalid run response: {run}")

    if run.get("status") != "completed":
        raise GitHubBoundaryError(f"{workflow_label} run {run_id} is not completed (status={run.get('status')!r})")
    if run.get("conclusion") != "success":
        raise GitHubBoundaryError(f"{workflow_label} run {run_id} did not succeed (conclusion={run.get('conclusion')!r})")
    if run.get("head_sha") != expected_head:
        raise GitHubBoundaryError(f"{workflow_label} run {run_id} head SHA mismatch: {run.get('head_sha')} != {expected_head}")
    if run.get("event") != "pull_request":
        raise GitHubBoundaryError(f"{workflow_label} run {run_id} event must be pull_request: {run.get('event')}")

    repo_info = run.get("repository") or {}
    if repo_info.get("id") != EXPECTED_REPO_ID or repo_info.get("full_name") != EXPECTED_REPO:
        raise GitHubBoundaryError(f"{workflow_label} run {run_id} repository mismatch")

    expected_path = ".github/workflows/public-pr.yml" if workflow_label == "public PR" else ".github/workflows/native-qualification.yml"
    if str(run.get("id")) != run_id or run.get("path") != expected_path or run.get("head_branch") != "staging":
        raise GitHubBoundaryError("workflow run id/path/branch mismatch")
    head_repo = run.get("head_repository") or {}
    if head_repo.get("id") != EXPECTED_REPO_ID or head_repo.get("full_name") != EXPECTED_REPO:
        raise GitHubBoundaryError("workflow run head repository mismatch")
    if recorded_binding is None:
        prs = run.get("pull_requests", [])
        if not isinstance(prs, list) or any(not isinstance(pr, dict) for pr in prs):
            raise GitHubBoundaryError("workflow run PR association malformed")
        matches = [pr for pr in prs if pr.get("number") == pr_number]
        if len(matches) != 1 or matches[0].get("head", {}).get("sha") != expected_head or (expected_base is not None and matches[0].get("base", {}).get("sha") != expected_base):
            raise GitHubBoundaryError("workflow run PR head/base association mismatch")
    elif expected_base is None or recorded_binding != workflow_run_binding(run, expected_head, expected_base, pr_number=pr_number):
        raise GitHubBoundaryError("recorded workflow run identity/PR binding mismatch")
    jobs_url = f"{API_ROOT}/repos/{client.repository}/actions/runs/{run_id}/jobs?per_page=100"
    jobs_resp = client.get_json(jobs_url)
    jobs = (jobs_resp.get("jobs") if isinstance(jobs_resp, dict) else jobs_resp) or []
    if not isinstance(jobs, list):
        raise GitHubBoundaryError(f"malformed jobs for run {run_id}")

    if not isinstance(jobs_resp, dict) or jobs_resp.get("total_count") != len(jobs):
        raise GitHubBoundaryError("incomplete jobs readback")
    observed_names = set()
    for job in jobs:
        name = job.get("name")
        if name in observed_names:
            raise GitHubBoundaryError("duplicate workflow job")
        observed_names.add(name)
        if job.get("status") != "completed":
            raise GitHubBoundaryError(f"{workflow_label} job {name!r} not completed (status={job.get('status')!r})")
        if job.get("conclusion") != "success":
            raise GitHubBoundaryError(f"{workflow_label} job {name!r} not successful (conclusion={job.get('conclusion')!r})")

    if observed_names != expected_jobs:
        missing = sorted(expected_jobs - observed_names)
        extra = sorted(observed_names - expected_jobs)
        raise GitHubBoundaryError(
            f"{workflow_label} run {run_id} jobs mismatch: missing={missing}, extra={extra}"
        )

    workflow_run_binding(run, expected_head, expected_base, pr_number=pr_number)
    return run, jobs


def verify_check_contexts_app(
    client: GitHubClient,
    commit_sha: str,
    required_contexts: frozenset[str],
    expected_runs: Mapping[str, str] | None = None,
    *, historical: bool = False,
) -> None:
    """Verify check contexts originate from GitHub Actions app 15368."""
    url = f"{API_ROOT}/repos/{client.repository}/commits/{commit_sha}/check-runs?per_page=100"
    resp = client.get_json(url)
    runs = (resp.get("check_runs") if isinstance(resp, dict) else resp) or []
    if not isinstance(runs, list):
        raise GitHubBoundaryError("invalid check-runs response")

    if not isinstance(resp, dict) or resp.get("total_count") != len(runs):
        raise GitHubBoundaryError("incomplete check-runs readback")
    for name in required_contexts:
        matching = [cr for cr in runs if cr.get("name") == name]
        if not matching:
            raise GitHubBoundaryError(f"missing check context: {name}")
        if historical and expected_runs is not None:
            prefix = f"https://github.com/{EXPECTED_REPO}/actions/runs/{expected_runs[name]}/job/"
            matching = [cr for cr in matching if str(cr.get("html_url", "")).startswith(prefix)]
            if not matching:
                raise GitHubBoundaryError("recorded run has no matching check context")
        latest = max(matching, key=lambda cr: cr["id"])
        if latest.get("app", {}).get("id") != GITHUB_ACTIONS_APP_ID:
            raise GitHubBoundaryError("check context app source is not GitHub Actions")
        if latest.get("status") != "completed" or latest.get("conclusion") != "success":
            raise GitHubBoundaryError("latest check context did not succeed")
        if expected_runs is not None:
            run_id = expected_runs[name]
            prefix = f"https://github.com/{EXPECTED_REPO}/actions/runs/{run_id}/job/"
            if not str(latest.get("html_url", "")).startswith(prefix):
                raise GitHubBoundaryError("check context belongs to a different run")


def verify_artifact_download(
    client: GitHubClient,
    run_id: str,
    artifact_name: str,
    expected_digest: str | None = None,
    expected_id: str | None = None,
) -> tuple[dict[str, Any], bytes]:
    """Retrieve artifact metadata and download zip bytes; verifies unexpired and exact name."""
    url = f"{API_ROOT}/repos/{client.repository}/actions/runs/{run_id}/artifacts?per_page=100"
    resp = client.get_json(url)
    artifacts = (resp.get("artifacts") if isinstance(resp, dict) else resp) or []
    matching = [a for a in artifacts if a.get("name") == artifact_name]
    if len(matching) != 1:
        raise GitHubBoundaryError(f"run {run_id} artifact {artifact_name!r} not found or ambiguous ({len(matching)})")
    meta = matching[0]

    if not isinstance(resp, dict) or resp.get("total_count") != len(artifacts):
        raise GitHubBoundaryError("incomplete artifacts readback")
    if meta.get("expired") is not False:
        raise GitHubBoundaryError(f"artifact {artifact_name!r} is expired or lacks expiry state")
    try:
        expires = datetime.fromisoformat(meta["expires_at"].replace("Z", "+00:00"))
        if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
            raise ValueError("expired")
    except (KeyError, ValueError, TypeError) as error:
        raise GitHubBoundaryError("artifact expiry is invalid or expired") from error
    run = meta.get("workflow_run", {})
    if str(run.get("id")) != run_id or run.get("repository_id") != EXPECTED_REPO_ID or run.get("head_repository_id") != EXPECTED_REPO_ID:
        raise GitHubBoundaryError("artifact metadata is cross-run or cross-repository")
    artifact_id = str(meta.get("id"))
    if not re.fullmatch(r"[1-9][0-9]{0,18}", artifact_id) or (expected_id is not None and artifact_id != expected_id):
        raise GitHubBoundaryError("artifact id mismatch")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(meta.get("digest", ""))):
        raise GitHubBoundaryError("artifact metadata lacks digest")

    zip_url = f"{API_ROOT}/repos/{client.repository}/actions/artifacts/{artifact_id}/zip"
    zip_bytes = client.get_bytes(zip_url)

    actual_digest = f"sha256:{sha256_bytes(zip_bytes)}"
    if type(meta.get("size_in_bytes")) is not int or meta["size_in_bytes"] != len(zip_bytes):
        raise GitHubBoundaryError("artifact archive size mismatch")
    if expected_digest is not None and actual_digest != expected_digest:
        raise GitHubBoundaryError(f"artifact {artifact_name} digest mismatch: {actual_digest} != {expected_digest}")
    meta_digest = meta.get("digest")
    if meta_digest and meta_digest != actual_digest:
        raise GitHubBoundaryError(f"artifact {artifact_name} download digest mismatch with metadata: {actual_digest} != {meta_digest}")

    return meta, zip_bytes


def verify_ruleset_readback(
    readback: Any,
    expected_contexts: frozenset[str] = REQUIRED_RULESET_CONTEXTS,
) -> dict[str, Any]:
    """Verify branch ruleset: active matching main, no bypass, required rules, strict checks=true, app 15368."""
    rulesets: list[dict[str, Any]] = []
    if isinstance(readback, list):
        rulesets = readback
    elif isinstance(readback, dict):
        if "rulesets" in readback and isinstance(readback["rulesets"], list):
            rulesets = readback["rulesets"]
        else:
            rulesets = [readback]
    else:
        raise GitHubBoundaryError("ruleset admin readback must be a list or object")

    matched_ruleset: dict[str, Any] | None = None
    for rs in rulesets:
        if not isinstance(rs, dict):
            continue
        enforcement = rs.get("enforcement")
        target = rs.get("target")
        conditions = rs.get("conditions") or {}
        ref_name = conditions.get("ref_name") or {}
        includes = ref_name.get("include") or []
        targets_main = (
            target == "branch" and includes == ["refs/heads/main"] and ref_name.get("exclude") == []
        )
        if enforcement == "active" and targets_main:
            matched_ruleset = rs
            break

    if matched_ruleset is None:
        raise GitHubBoundaryError("no active ruleset matching main found in admin readback")

    bypass_actors = matched_ruleset.get("bypass_actors")
    if bypass_actors != []:
        raise GitHubBoundaryError(f"ruleset allows bypass actors: {bypass_actors}")

    rules = matched_ruleset.get("rules") or []
    rule_types = {r.get("type") for r in rules if isinstance(r, dict)}
    required_types = {"pull_request", "non_fast_forward", "deletion", "required_status_checks"}
    missing_types = required_types - rule_types
    if missing_types:
        raise GitHubBoundaryError(f"ruleset is missing required rule types: {sorted(missing_types)}")

    status_rule = next(r for r in rules if isinstance(r, dict) and r.get("type") == "required_status_checks")
    params = status_rule.get("parameters") or {}
    if params.get("strict_required_status_checks_policy") is not True:
        raise GitHubBoundaryError("ruleset must configure strict_required_status_checks_policy: true")

    checks = params.get("required_status_checks") or []
    observed_contexts: set[str] = set()
    for chk in checks:
        if isinstance(chk, dict):
            ctx = chk.get("context")
            integration_id = chk.get("integration_id")
            if ctx:
                observed_contexts.add(ctx)
            if integration_id != GITHUB_ACTIONS_APP_ID:
                raise GitHubBoundaryError(f"ruleset check context {ctx!r} has invalid integration_id: {integration_id}")

    if not expected_contexts <= observed_contexts:
        missing = sorted(expected_contexts - observed_contexts)
        extra = sorted(observed_contexts - expected_contexts)
        raise GitHubBoundaryError(
            f"ruleset check contexts mismatch: missing={missing}, extra={extra}"
        )

    return matched_ruleset


def verify_governance(
    client: GitHubClient,
    pr_number: int,
    head_sha: str,
    base_sha: str,
    merge_sha: str,
    author_login: str,
    waiver_data: Mapping[str, Any] | None = None,
    *, waiver_scope: str | None,
) -> dict[str, Any]:
    """Verify eligible non-author approval or canonical governance waiver.

    ``waiver_scope`` is the release contract's only accepted waiver scope.  An
    approval-only release supplies ``None``, so no waiver can satisfy it.
    """
    reviews_url = f"{API_ROOT}/repos/{client.repository}/pulls/{pr_number}/reviews?per_page=100"
    reviews = client.get_json(reviews_url)
    if not isinstance(reviews, list):
        raise GitHubBoundaryError("invalid PR reviews response")

    page_size = len(reviews)
    for page in range(2, 22):
        if page_size < 100:
            break
        more = client.get_json(reviews_url + f"&page={page}")
        if not isinstance(more, list) or len(more) > 100:
            raise GitHubBoundaryError("invalid review pagination")
        reviews.extend(more)
        page_size = len(more)
    else:
        raise GitHubBoundaryError("review pagination exceeds bound")
    user_latest_reviews: dict[str, dict[str, Any]] = {}
    for r in reviews:
        if isinstance(r, dict):
            login = (r.get("user") or {}).get("login")
            if login:
                user_latest_reviews[login] = r

    eligible_approvals = []
    for login, r in user_latest_reviews.items():
        if login == author_login:
            continue
        if r.get("state") == "APPROVED" and r.get("commit_id") == head_sha and r.get("author_association") in {"OWNER", "MEMBER", "COLLABORATOR"}:
            eligible_approvals.append({"user": login, "id": r.get("id"), "commit_id": head_sha})

    if eligible_approvals:
        return {
            "mode": "approval",
            "approvals": eligible_approvals,
            "waiver": None,
        }

    if waiver_data is None:
        raise GitHubBoundaryError("neither eligible non-author approval nor governance waiver provided")
    if waiver_scope is None:
        raise GitHubBoundaryError("release contract is approval-only; a governance waiver cannot satisfy it")

    validate_self_hash(waiver_data, label="governance waiver")
    if waiver_data.get("schema") != GOVERNANCE_WAIVER_SCHEMA:
        raise GitHubBoundaryError(f"unexpected governance waiver schema: {waiver_data.get('schema')}")
    if waiver_data.get("pr_head_sha") != head_sha:
        raise GitHubBoundaryError(f"waiver pr_head_sha mismatch: {waiver_data.get('pr_head_sha')} != {head_sha}")
    if waiver_data.get("pr_base_sha") != base_sha:
        raise GitHubBoundaryError(f"waiver pr_base_sha mismatch: {waiver_data.get('pr_base_sha')} != {base_sha}")
    if waiver_data.get("merge_ref_sha") != merge_sha:
        raise GitHubBoundaryError(f"waiver merge_ref_sha mismatch: {waiver_data.get('merge_ref_sha')} != {merge_sha}")

    if waiver_data.get("repo") != EXPECTED_REPO or waiver_data.get("pr") != pr_number or waiver_data.get("scope") != waiver_scope:
        raise GitHubBoundaryError("waiver repo/PR/scope mismatch")
    for key in ("reason", "approved_by", "approved_at"):
        if not isinstance(waiver_data.get(key), str) or not waiver_data[key].strip():
            raise GitHubBoundaryError(f"waiver missing {key}")
    try:
        approved_at = datetime.fromisoformat(waiver_data["approved_at"].replace("Z", "+00:00"))
        if approved_at.tzinfo is None or approved_at > datetime.now(timezone.utc):
            raise ValueError("invalid approval time")
    except ValueError as error:
        raise GitHubBoundaryError("waiver approval time invalid") from error
    waiver_hash = compute_self_hash(waiver_data)
    return {
        "mode": "waiver",
        "approvals": [],
        "waiver": dict(waiver_data),
        "waiver_sha256": waiver_hash,
    }


def verify_squash_and_branch(
    client: GitHubClient,
    pr_number: int,
    squash_sha: str,
    base_sha: str,
    tree_sha: str,
    version: str,
    waiver_hash: str | None = None,
) -> dict[str, Any]:
    """Verify squash commit S: sole parent B, tree T, subject Release vX, ahead_by=1 on main, waiver trailer."""
    url = f"{API_ROOT}/repos/{client.repository}/commits/{squash_sha}"
    commit_data = client.get_json(url)
    if not isinstance(commit_data, dict):
        raise GitHubBoundaryError(f"invalid commit response for {squash_sha}")

    if commit_data.get("sha") != squash_sha:
        raise GitHubBoundaryError("squash commit object SHA mismatch")
    parents = commit_data.get("parents") or []
    parent_shas = [p.get("sha") if isinstance(p, dict) else p for p in parents]
    if parent_shas != [base_sha]:
        raise GitHubBoundaryError(f"squash commit must have sole parent {base_sha}, got {parent_shas}")

    commit_obj = commit_data.get("commit") or {}
    tree = commit_obj.get("tree") or {}
    actual_tree = tree.get("sha")
    if actual_tree != tree_sha:
        raise GitHubBoundaryError(f"squash commit tree mismatch: {actual_tree} != {tree_sha}")

    message = commit_obj.get("message") or ""
    first_line = message.splitlines()[0] if message else ""
    expected_subject = f"Release v{version}"
    if first_line != expected_subject:
        raise GitHubBoundaryError(f"squash commit subject must be {expected_subject!r}, got {first_line!r}")

    if waiver_hash is not None and message.splitlines().count(f"Governance-Waiver-SHA256: {waiver_hash}") != 1:
        raise GitHubBoundaryError("squash commit message missing required waiver trailer")

    pulls_url = f"{API_ROOT}/repos/{client.repository}/commits/{squash_sha}/pulls"
    pulls = client.get_json(pulls_url)
    if not isinstance(pulls, list) or [p.get("number") for p in pulls] != [pr_number]:
        raise GitHubBoundaryError("squash commit lacks exact PR association")
    branch_url = f"{API_ROOT}/repos/{client.repository}/branches/main"
    branch = client.get_json(branch_url)
    branch_commit = (branch.get("commit") or {}).get("sha")
    if branch_commit != squash_sha:
        raise GitHubBoundaryError(f"main branch tip is not squash commit {squash_sha}: got {branch_commit}")

    comp_url = f"{API_ROOT}/repos/{client.repository}/compare/{base_sha}...{squash_sha}"
    comp = client.get_json(comp_url)
    ahead_by = comp.get("ahead_by")
    behind_by = comp.get("behind_by")
    if ahead_by != 1 or behind_by != 0:
        raise GitHubBoundaryError(f"main comparison to base invalid: ahead_by={ahead_by}, behind_by={behind_by}")

    return commit_data


def verify_annotated_tag(
    client: GitHubClient,
    tag_name: str,
    expected_commit: str,
) -> dict[str, Any]:
    """Verify annotated tag only, pointing to expected commit."""
    ref_url = f"{API_ROOT}/repos/{client.repository}/git/ref/tags/{tag_name}"
    ref = client.get_json(ref_url)
    obj = ref.get("object") or {}
    obj_type = obj.get("type")
    if obj_type != "tag":
        raise GitHubBoundaryError(f"tag {tag_name} must be an annotated tag, got type: {obj_type!r}")
    tag_sha = obj.get("sha")

    tag_obj_url = f"{API_ROOT}/repos/{client.repository}/git/tags/{tag_sha}"
    tag_obj = client.get_json(tag_obj_url)
    target_obj = tag_obj.get("object") or {}
    target_sha = target_obj.get("sha")
    target_type = target_obj.get("type")

    if tag_obj.get("tag") != tag_name:
        raise GitHubBoundaryError(f"tag object name mismatch: {tag_obj.get('tag')} != {tag_name}")
    if target_type != "commit" or target_sha != expected_commit:
        raise GitHubBoundaryError(f"tag object points to {target_sha} ({target_type}), expected commit {expected_commit}")

    if not isinstance(tag_obj.get("message"), str) or not tag_obj["message"].strip() or tag_obj.get("sha") != tag_sha:
        raise GitHubBoundaryError("annotated tag identity or message missing")
    return tag_obj


def verify_github_release(
    client: GitHubClient,
    release_id: int,
    expected_tag: str,
    expected_state: str,
    path_mapping: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    """Verify GitHub release: tag, draft/published state, release notes, and 16 flat assets."""
    rel_url = f"{API_ROOT}/repos/{client.repository}/releases/{release_id}"
    release = client.get_json(rel_url)
    if not isinstance(release, dict):
        raise GitHubBoundaryError(f"invalid release response for ID {release_id}")

    if release.get("tag_name") != expected_tag:
        raise GitHubBoundaryError(f"release tag mismatch: {release.get('tag_name')} != {expected_tag}")

    if release.get("id") != release_id or type(release.get("draft")) is not bool:
        raise GitHubBoundaryError("release id/draft state missing")
    draft = release["draft"]
    if release.get("prerelease") is not False:
        raise GitHubBoundaryError("release must not be marked as a prerelease")

    if expected_state == "draft":
        if not draft:
            raise GitHubBoundaryError("expected release to be a draft, but draft is false")
    elif expected_state == "published":
        if draft:
            raise GitHubBoundaryError("expected release to be published, but draft is true")
    else:
        raise GitHubBoundaryError(f"unsupported expected release state: {expected_state!r}")

    assets = release.get("assets") or []
    if not isinstance(assets, list):
        raise GitHubBoundaryError("release assets must be an array")

    observed_names = [a.get("name") for a in assets if isinstance(a, dict)]
    if len(observed_names) != len(set(observed_names)):
        raise GitHubBoundaryError(f"release contains duplicate asset names: {observed_names}")

    # The asset set belongs to the tag's release; canonical_flat_assets refuses
    # any version outside the closed contract table.
    if not isinstance(expected_tag, str) or not expected_tag.startswith("v"):
        raise GitHubBoundaryError(f"release tag is not a v<version> tag: {expected_tag!r}")
    expected_flat = canonical_flat_assets(version=expected_tag[1:])
    if sorted(observed_names) != sorted(expected_flat):
        missing = sorted(set(expected_flat) - set(observed_names))
        extra = sorted(set(observed_names) - set(expected_flat))
        raise GitHubBoundaryError(
            f"release assets mismatch (expected 16 flat assets): missing={missing}, extra={extra}"
        )

    if {entry["flat_name"] for entry in path_mapping.values()} != set(expected_flat) or len(path_mapping) != 16:
        raise GitHubBoundaryError("release mapping is incomplete")
    expected = {entry["flat_name"]: entry for entry in path_mapping.values()}
    for asset in assets:
        entry = expected[asset["name"]]
        if asset.get("state") != "uploaded" or type(asset.get("size")) is not int or asset["size"] != int(entry["size_in_bytes"]):
            raise GitHubBoundaryError("release asset state or size mismatch")
        if type(asset.get("id")) is not int or asset["id"] <= 0:
            raise GitHubBoundaryError("release asset id invalid")
        url = f"{API_ROOT}/repos/{client.repository}/releases/assets/{asset['id']}"
        content, _ = client._request(url, "application/octet-stream", MAX_ARCHIVE_BYTES)
        if len(content) != asset["size"] or sha256_bytes(content) != entry["sha256"]:
            raise GitHubBoundaryError("release asset bytes or SHA256 mismatch")
        if asset.get("digest") is not None and asset["digest"] != "sha256:" + entry["sha256"]:
            raise GitHubBoundaryError("release asset GitHub digest mismatch")
    return release
