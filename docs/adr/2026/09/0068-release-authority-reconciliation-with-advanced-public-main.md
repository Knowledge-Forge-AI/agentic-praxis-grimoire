# ADR 0068 — Release Authority Reconciliation with Advanced Public Main and Hardened Attended Release Operator

- Status: Accepted
- Date: 2026-09-17
- Phase: APG152 (Roadmap Stage: V0120-G1)

## Context

Following the publication of APGR v0.11.0, the public repository `Knowledge-Forge-AI/agentic-praxis-grimoire` advanced on branch `main` with an operational maintenance commit:
`7c77619cdc54f1f6d87c36eb20a11ea0b30a2441` ("ci: remove stale run PR association gate").

Historical release tooling (`libexec/apg_public_release.py`, `libexec/apg_staging_correction.py`, and `release.yml`) was coupled to an assumption that the public base commit before staging matches the immediate preceding release tag (`v0.11.0`). When the remote repository advances due to CI maintenance, hotfixes, or governance actions, strict predecessor equality asserts failure, despite the repository preserving linear lineage.

Furthermore, post-v0.11 operational reviews identified several release operator hardening gaps:
1. **Lineage Inflexibility**: Inability of `verify_public_release_lineage` to accept an advanced, untagged `main` head descending linearly from the previous release tag.
2. **Brittle Hosted CI Release Gates**: `.github/workflows/release.yml` contained a fragile jq filter `(.pull_requests // [] | any(.number == ($number | tonumber)))` that failed closed in headless squash-merge triggers where GitHub Actions does not populate PR association in the workflow dispatch payload.
3. **Draft Release ID Binding**: Risk of mutating or publishing against the wrong GitHub release object without binding to a specific numeric draft release ID (`id: <integer>`) established prior to asset upload.
4. **Channel Sequence & State Machine**: Need for an explicit channel state machine enforcing atomic progression, idempotent resumption via durable receipts, and strict multi-platform ordering (e.g., publishing platform-specific npm packages before the root launcher package).
5. **Fail-Closed Operator Execution**: Attended release operator scripts must default to read-only dry-run or preview mode unless explicitly confirmed with `--confirm` and `--live`.

## Decision

### 1. Authority Reconciliation & Linear Lineage Verification (`apg_public_release.py`)
APGR updates `verify_public_release_lineage` and candidate checks to support `allow_advanced_head`:
- Proves ancestral continuity via `git merge-base --is-ancestor refs/tags/v0.11.0 $premerge_main`.
- Verifies that all commits between the predecessor tag and `premerge_main` are single-parent linear commits.
- Ensures the surface at `premerge_main` conforms strictly to the audited policy surface without unauthorized deletions or namespace alterations.
- Preserves full backward compatibility for historical releases (v0.1.0 through v0.11.0) under `allow_v011_compatibility=True`.

### 2. Hosted Release CI Hardening (`.github/workflows/release.yml`)
- Derives `premerge_main="$merged_parent"` directly from the squash-merge commit parent.
- Replaces the fragile jq PR association filter with an authoritative GitHub Compare API query:
  `gh api repos/{owner}/{repo}/compare/{accepted_base}...{premerge_main}` asserting `status` is in `(ahead|identical)` and `behind_by == 0`.
- Binds `pr_base_sha == $premerge_main` in `matrix-aggregate.json` and asserts `tested_commit_json.parents[0].sha == $premerge_main`.
- Enforces `checks: read` permissions in workflow permissions block.

### 3. Numeric Draft Release ID Binding (REG-P1)
- The GitHub release channel requires establishing an explicit draft release and recording its numeric ID (`id: <int>`).
- All subsequent operations (asset uploads, post-upload inspection, publication PATCH) must bind to this numeric ID.
- Publication is refused if the release ID references a mismatched tag or nonexistent object.

### 4. npm Package Ordering & State Machine (REG-P6)
- The npm release channel strictly enforces publishing the three platform-specific binary tarballs (`@knowledge-forge-ai/apgr-darwin-arm64`, `@knowledge-forge-ai/apgr-linux-arm64`, `@knowledge-forge-ai/apgr-linux-x64`) and verifying their registry status before publishing the root dependency-free launcher (`@knowledge-forge-ai/apgr`).
- Prevents end-user installation failures resulting from launcher availability prior to binary payload readiness.

### 5. Deterministic Release Epoch Registration (`apg_python_distribution.py`)
- Formally registers the v0.12 release epoch: `V012_RELEASE_EPOCH = 1_789_689_600` (UTC timestamp `2026-09-18T00:00:00Z`).
- Reconstructs all archive tar members and file modification times strictly against this deterministic epoch.

### 6. Attended Operator Driver & Preview Enforcement (`runner.py`, `execute.py`)
- The release operator CLI (`release_operator/runner.py` and `packet/execute.py`) executes in offline dry-run or preview mode by default.
- Live mutations against external channels require both `--live` and `--confirm`.
- Omitting `--confirm` when `--live` is specified automatically degrades execution to read-only preview mode.

## Consequences

- Staging PR validation and candidate builds succeed against the current public `main` (`7c77619cdc...`) without breaking historical release proofs.
- Release workflows in GitHub Actions can trigger reliably from squashed merges without headless payload failures.
- Multi-channel publication is protected by durable receipts, preventing duplicate uploads or partial state corruption.
- Phase V0120-G1 remains strictly non-mutating with zero external side effects.
