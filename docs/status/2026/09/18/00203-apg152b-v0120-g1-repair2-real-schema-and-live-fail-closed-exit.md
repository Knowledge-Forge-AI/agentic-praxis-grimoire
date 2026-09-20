# APG152B — APGR V0120-G1-REPAIR2 — Real-Schema and Live Fail-Closed Release Path Hardening Exit

Phase ID: `APG152B`
Exit ID: `Exit 00203`  
Governing Decisions: [ADR 0057](../../../../adr/2026/09/0057-public-staging-pr-release-procedure.md), [ADR 0068](../../../../adr/2026/09/0068-release-authority-reconciliation-with-advanced-public-main.md)\
Entry Commit: `30e0b51e62bf1e38b0f6b872c51de143dfb63f72`  
Exit Target: `V0120_G1_REAL_SCHEMA_AND_LIVE_FAIL_CLOSED_READY`  

---

## 1. Status and Disposition

- **Disposition**: **accept**
- **Milestone Outcome**: `V0120_G1_REAL_SCHEMA_AND_LIVE_FAIL_CLOSED_READY`
- **Scope Delivery**: Resolved all 9 manager review advisory findings across Scopes A through T for APGR v0.12.0. Hardened the publication path to consume the real `size_bytes` canonical manifest schema emitted by `libexec/apg_distribution_candidate.py` (rejecting any competing `size` key intrusion); normalized real PyPI response digests at `file["digests"]["sha256"]`; hardened `stage_operator.py` to fail closed on remote staging/main drift and malformed PR JSON; enforced idempotent create-or-reuse in `open-pr`; explicitly bound bounded governance waiver markers (`<!-- BEGIN_GOVERNANCE_WAIVER -->` / `<!-- END_GOVERNANCE_WAIVER -->`) in PR verification and release workflow; bound full hosted CI workflow run, jobs, artifact IDs, and aggregate matrix qualification evidence into `check-pr` and `g2-staging-receipt.json`; implemented attended guarded annotated tag command `stage_operator.py create-tag`; implemented stage-aware preflight bindings across all 6 publication requirements; restored the proven v0.11 Homebrew package installation contract for npm platform tarballs; enforced operator state root isolation outside git checkouts; fixed resume path `NameError` in `channels/live.py`; authored maintained real-schema end-to-end test suite `test_real_schema_manifest_e2e.py`; and verified complete 18-step G2 campaign simulations with mocked boundaries while maintaining strict zero external mutations.
- **Strict Zero-Mutation Boundary Confirmation**:
  - Phase APG152B / V0120-G1-REPAIR2 only.
  - ZERO external mutations performed: no git branch push, PR creation, merge, tag creation, GitHub Release publication, PyPI upload, npm upload, or Homebrew tap commit/PR.
  - Public authorities remain frozen:
    - Expected private APGR main: `30e0b51e62bf1e38b0f6b872c51de143dfb63f72`
    - Public main: `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441`
    - Public staging: `a0e76457ca84d56099c9c42cfd32297809680339` (stale v0.11 staging head)
    - Latest release: `v0.11.0` (numeric ID `389919431`)
  - Subphase V0120-G2 remains **NOT STARTED**.
  - Agent-Central (`~/projs/agent-central`) remains active, supported, and unmutated.
  - JACA remains unmutated.

---

## 2. Advisory Findings Remediation Detail

Manager review of APG152A identified 9 advisory findings that have been completely addressed in APG152B:

1. **Scope A & P (Finding 1) — Canonical Manifest Schema & Real Producer Parity**:
   - `derive_operator_channel_view()` in `release_operator/authority.py` now consumes the actual canonical manifest schema strictly requiring `size_bytes` across wheels, sdist, and npm tarballs, rejecting any intrusion of `size`.
   - Replaced synthetic mocks with `private/releases/v0.12.0/test_real_schema_manifest_e2e.py`, importing `libexec.apg_distribution_candidate` to build real candidate deliverables (Go binaries, Python wheels/sdist, npm packages) and asserting fail-closed rejection on schema drift, `size` key intrusion, `size_bytes` omission, commit/tree mismatch, extraneous files, or asset corruption.

2. **Scope O (Finding 2) — Scope O Resume Path `NameError`**:
   - Added module-level `import hashlib` in `private/releases/v0.12.0/release_operator/channels/live.py`.
   - Added tests exercising `upload_asset` when matching assets already exist, verifying direct download by numeric asset ID and SHA-256 verification before accepting resumable state.

3. **Scope C (Finding 3) — Fail-Closed Staging Authority Reads in `publish-staging`**:
   - `stage_operator.py:publish_staging_action` fails closed immediately if `git ls-remote` on `staging` fails or outputs unexpected content. Nonzero return codes or empty outputs do not downgrade to a lease-free force push; exact lease `--force-with-lease=refs/heads/staging:<stale_sha>` is strictly enforced.

4. **Scope C (Finding 4) — Malformed PR JSON Handling in Staging Operator**:
   - `stage_operator.py` parses `gh pr list` output strictly, raising `RuntimeError` on invalid JSON or non-list payloads instead of swallowing errors.

5. **Scope D (Finding 5) — Idempotent PR Create-or-Reuse in `open-pr`**:
   - `stage_operator.py:open_pr_action` queries open PRs targeting `main` from `staging`. If exactly one PR matches the expected candidate head SHA and title, it reuses the PR rather than attempting duplicate creation. Mismatched or multiple open PRs raise fail-closed errors.
   - Post-creation readback strictly binds PR number, URL, head SHA, and base SHA, writing `pr-authority-receipt.json` and its `.sha256` sidecar atomically.

6. **Scope C & E (Finding 6) — Enumerated PR Gates & Bounded Governance Waiver**:
   - `stage_operator.py:check_pr_action` verifies PR state is strictly `OPEN`, verifies base/head commits match expected SHAs, and validates all 13 required checks.
   - Replaced unanchored regex scraping with explicit bounded governance waiver markers (`<!-- BEGIN_GOVERNANCE_WAIVER -->` ... `<!-- END_GOVERNANCE_WAIVER -->`) in PR body verification and `.github/workflows/release.yml`. Stale, unapproved, or unbounded PRs are rejected.

7. **Scope F (Finding 7) — Hosted CI Run & Aggregate Evidence in G2 Staging Receipt**:
   - `stage_operator.py:check_pr_action` queries and binds the public PR workflow run ID, workflow path, run event, per-job terminal success, public PR gate artifact ID, artifact digests, and aggregate matrix qualification evidence.
   - `reconcile_postmerge_action` binds this comprehensive `hosted_qualification` record, its SHA-256 digest, and `pr_check_receipt_sha256` directly into `g2-staging-receipt.json`.

8. **Scope H (Finding 8) — Stage-Aware Preflight with 6 Publication Bindings**:
   - `packet/preflight.py` implements 6 stage-aware bindings for publication mode:
     1. G2 staging receipt validation (`merged_commit_sha`, `projected_tree`, `hosted_qualification` evidence) and SHA-256 digest computation.
     2. Remote tag query and peeled commit resolution (`refs/tags/v0.12.0^{}`) bound to `merged_commit_sha`.
     3. Public remote `main` branch bound to `merged_commit_sha`.
     4. Canonical distribution manifest and exact 10 assets verified on disk via `derive_operator_channel_view`.
     5. GitHub Release state query (must be draft/absent for publication; published blocked unless `resume-publication`).
     6. PyPI and npm package absence (404 required for fresh publication; existing versions allowed only in `resume-publication`).
   - Wired `--g2-receipt` and `--assets-dir` CLI flags into `preflight.py` and `execute.py`.

9. **Scope J (Finding 9) — Explicit External Operator State Root**:
   - `release_operator/runner.py` derives and enforces `--operator-state-root` outside APGR source checkouts and public checkouts.
   - Clones the Homebrew tap inside the designated isolated state root and audits the actual formula path directly without cwd ambiguity.

---

## 3. Verification Suite Results

All unit, integration, release operator, and mocked campaign test suites pass 100% cleanly:

| Suite | Tests / Checks | Result | Coverage Area |
| :--- | :---: | :---: | :--- |
| `test_real_schema_manifest_e2e.py` | 12/12 | PASS | Real canonical distribution manifest builder, `size_bytes` schema, 10-asset derivation, fail-closed rejections |
| `test_live_operator_adapters.py` | 40/40 | PASS | Hardened live channel adapters with mocked REST boundaries and resume paths |
| `test_release_operator_dry_runs.py` | 19/19 | PASS | Release operator dry run and state machine suite (14 fixtures) |
| `test_hosted_ci_regressions.py` | 12/12 | PASS | Hosted CI regressions (REG-R1 through REG-R13) |
| `test_g2_mocked_campaign.py` | 44/44 | PASS | 18-step G2 mocked campaign, fail-closed boundaries, tag creation, Scope F hosted qualification, and REG-P5 resume |
| `release.yml.int.test.py` | 36/36 | PASS | Hosted release workflow contract, bounded governance waiver, and review validation |
| `version.unit.test.py` | 1/1 | PASS | Python library version agreement with VERSION token |
| `cli.unit.test.py` | 59/59 | PASS | Python CLI version flag and command execution tests |
| `apg-build-go-cli.int.test.py` | 3/3 | PASS | Go CLI build, wrapper, and v0.12 version token integration |
| `bin/apg-check-release-matrix` | 38/38 | PASS | Release readiness matrix mechanical validation (13 REG-R, 13 REG-P, 12 F-traceability) |
| `apg-check-release-matrix.int.test.py` | 2/2 | PASS | Integration tests for release matrix mechanical validator |
| `go test ./...` | All packages | PASS | Complete Go suite (candidate, internal/cli, internal/gitexec, etc.) |
| `go vet ./...` | All packages | PASS | Go static analysis and vet checks |
| `frozen-input-digests.json` | 8/8 | PASS | Cryptographic digest parity across all critical release inputs (including updated `release.yml`) |
| `operator-packet.sha256` | 1/1 | PASS | Cryptographic integrity of operator release packet |
| `tools/ci/file_length_policy.py` | Clean | PASS | All files strictly conform to repository file length policy |
| `tools/ci/pre_review_checks.py` | Clean | PASS | Pre-review static analysis and integrity evaluation |

---

## 4. Zero-Mutation Verification Evidence

Live read-only verification confirms zero external mutations have occurred:

1. **Public `main` branch**:
   - Command: `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/heads/main`
   - Readback: `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441 refs/heads/main` (unmutated).
2. **Public `staging` branch**:
   - Command: `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/heads/staging`
   - Readback: `a0e76457ca84d56099c9c42cfd32297809680339 refs/heads/staging` (unmutated stale v0.11 tip).
3. **Public `v0.12.0` tag**:
   - Command: `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/tags/v0.12.0`
   - Readback: Empty output (tag absent).
4. **Public GitHub Release**:
   - Command: `gh api repos/Knowledge-Forge-AI/agentic-praxis-grimoire/releases/latest --jq '{tag_name, id, draft, prerelease}'`
   - Readback: Numeric release ID `389919431` (`v0.11.0`) remains latest release. No `v0.12.0` release exists.
5. **PyPI Index**:
   - URL: `https://pypi.org/pypi/agentic-praxis-grimoire/0.12.0/json`
   - Readback: HTTP 404 (absent).
6. **npm Registry**:
   - URLs: `https://registry.npmjs.org/@knowledge-forge-ai/apgr/0.12.0` and platform packages `darwin-arm64`, `linux-x64`, `linux-arm64`.
   - Readback: HTTP 404 across all 4 packages (absent).
7. **Homebrew Tap**:
   - Command: `git ls-remote https://github.com/Knowledge-Forge-AI/homebrew-tap.git refs/heads/main`
   - Readback: `db8e6bec3a2a6a5aa504b58add21896a655691f1 refs/heads/main` (unmutated baseline).
