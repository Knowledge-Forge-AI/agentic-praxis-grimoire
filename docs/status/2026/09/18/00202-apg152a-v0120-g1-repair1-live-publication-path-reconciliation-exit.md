# APG152A — APGR V0120-G1-REPAIR1 — Live Publication Path Reconciliation Exit

Phase ID: `APG152A`
Exit ID: `Exit 00202`  
Governing Decisions: [ADR 0057](../../../../adr/2026/09/0057-public-staging-pr-release-procedure.md), [ADR 0068](../../../../adr/2026/09/0068-release-authority-reconciliation-with-advanced-public-main.md)\
Entry Commit: `482c5684179008421a90db69a5e5744ddffcc2d3`  
Exit Target: `V0120_G1_REPAIR1_LIVE_PUBLICATION_PATH_RECONCILED`  

---

## 1. Status and Disposition

- **Disposition**: **accept**
- **Milestone Outcome**: `V0120_G1_REPAIR1_LIVE_PUBLICATION_PATH_RECONCILED`
- **Scope Delivery**: Reconciled the entire live publication path for APGR v0.12.0 across all 19 findings (Scopes A–S), hardened channel adapters, implemented attended staging commands with `--force-with-lease` bound to the stale v0.11 staging head, integrated G2 postmerge authority receipt into executor and runner, updated Homebrew formula generation to npm platform tarball conventions, enforced clean public checkout and out-of-tree asset generation in `build_assets.py`, and verified the complete 18-step G2 campaign via comprehensive mocked testing with zero external mutations.
- **Strict Zero-Mutation Boundary Confirmation**:
  - Phase APG152A / V0120-G1-REPAIR1 only.
  - ZERO external mutations performed: no git branch push, PR creation, merge, tag creation, GitHub Release publication, PyPI upload, npm upload, or Homebrew tap commit/PR.
  - Public authorities remain frozen:
    - Expected private APGR main: `482c5684179008421a90db69a5e5744ddffcc2d3`
    - Public main: `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441`
    - Public staging: `a0e76457ca84d56099c9c42cfd32297809680339` (stale v0.11 staging head)
    - Latest release: `v0.11.0` (numeric ID `389919431`)
  - Subphase V0120-G2 remains **NOT STARTED**.
  - Agent-Central (`~/projs/agent-central`) remains active, supported, and unmutated.
  - JACA remains unmutated.

---

## 2. Background and Operational Gaps Addressed

Following the initial completion of APG152 (V0120-G1), a comprehensive pre-mutation review identified 19 findings across Scopes A through S that required resolution before initiating public mutations in V0120-G2:

1. **Version Alignment (Scope A)**: Unit tests in `version.unit.test.py` and `cli.unit.test.py` and integration tests in `apg-build-go-cli.int.test.py` asserted stale `"0.11.0"` expectations.
2. **Public CI Workflow (Scope B)**: `.github/workflows/public-pr.yml` line 246 contained a hardcoded `--public-version 0.11.0` flag and stale documentation references.
3. **Release Workflow Review Gate (Scope C)**: `.github/workflows/release.yml` verification step failed on authorized governance waivers because it lacked conditional waiver acceptance.
4. **Distribution Manifest Derivation (Scope D)**: Distribution assets required deterministic mapping from `apg.distribution-manifest/v1` and `SHA256SUMS` into operator-expected flat channel views.
5. **G2 Receipt Argument Integration (Scope E)**: Operator executor (`execute.py`) and runner (`runner.py`) required `--g2-receipt` and `--assets-dir` flags bound to cryptographic checksum validation.
6. **Direct REST Asset Upload (Scope F)**: `LiveGitHubApi.upload_asset` was hardened to use direct REST uploads via `POST https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets` instead of CLI invocations.
7. **Attended Go Proxy Backoff (Scope G)**: `LiveGoProxy` lacked exponential backoff and retry handling for 404/410 eventual consistency.
8. **Conjunctive PyPI Workflow Observation (Scope H)**: `LivePyPiApi.observe_workflow_run` required conjunctive matching on workflow path (`release.yml`), event (`release`), tag, and commit SHA.
9. **Registry Pinning (Scope I)**: `LiveNpmRegistry.publish_package` required explicit `--registry https://registry.npmjs.org` pinning.
10. **Formula Stem Collision & Fail-Closed Checks (Scope J)**: `LiveTapAdapter` suffered from `.rb.rb` collisions and soft failures when `brew` or `ruby` were missing from PATH.
11. **Homebrew Formula Generation (Scope K)**: `channels/homebrew.py` generated formula content with non-existent asset names instead of npm platform tarballs.
12. **Preflight Verifier Modes (Scope L)**: `packet/preflight.py` lacked support for `offline`, `preview`, and `live-confirmed` operational modes.
13. **Asset Builder Enforcements (Scope M)**: `packet/build_assets.py` needed strict checks for clean public checkout, HEAD tree matching, and out-of-tree destination.
14. **Attended Stage Operator Commands (Scope N)**: `packet/stage_operator.py` required 8 discrete attended commands for Phase V0120-G2 execution.
15. **Safe Inter-Cycle Staging Push (Scope O)**: Staging push required `--force-with-lease=staging:a0e76457ca84d56099c9c42cfd32297809680339` bound to the stale staging tip.
16. **Operator Packet Metadata & Documentation (Scope P)**: `operator-packet.json` needed `staging_authority.branch` set to `"staging"`, `operator-packet.sha256` recomputed, and `README.md` updated with the 18-step G2 plan.
17. **ADR 0057 Alignment (Scope Q)**: ADR 0057 amended to clarify inter-cycle staging branch replacement vs intra-cycle linear PR discipline.
18. **Comprehensive Mocked Campaign Test Suite (Scope R)**: Verification of the full 18-step execution flow with mocked adapters.
19. **Zero-Mutation Readback (Scope S)**: Live read-only verification that public GitHub, PyPI, and npm remain unmutated.

---

## 3. Implementation Summary

### A. Version and CI Alignment (Scopes A, B, C)
- `version.unit.test.py` and `cli.unit.test.py`: Updated `CURRENT_VERSION = "0.12.0"`.
- `apg-build-go-cli.int.test.py`: Updated version assertions to `"0.12.0"`. All 63 tests pass.
- `.github/workflows/public-pr.yml`: Updated line 246 to `--public-version 0.12.0`. Updated `docs/public-pr-ci.md`.
- `tools/ci/qualify_packages.sh`: Dynamically derives version from `src/agentic_praxis_grimoire/VERSION`.
- `.github/workflows/release.yml`: Verification step accepts either approved review or authorized governance waiver (`reviews[].state == "APPROVED"` or `pr_body | test("governance waiver|governance-waiver"; "i")`). All 35 integration tests pass.
- `frozen-input-digests.json`: Recomputed deterministic SHA-256 for `release.yml`.

### B. Channel Adapters and Manifest View (Scopes D, E, F, G, H, I, J, K)
- `release_operator/authority.py`: Implemented `derive_operator_channel_view` mapping the 10 flat release deliverables.
- `release_operator/runner.py` and `packet/execute.py`: Wired `--g2-receipt` and `--assets-dir` flags, enforcing SHA-256 checksum and schema `apgr.g2-staging-receipt/v1`.
- `channels/live.py`:
  - `LiveGitHubApi`: Direct REST asset upload with `Authorization: Bearer <token>`, `Content-Type: application/octet-stream`, URL-encoded filenames, and release ID validation.
  - `LiveGoProxy`: Attended exponential backoff for 404/410 query retries.
  - `LivePyPiApi`: Conjunction-bound workflow observation polling (`path` ends with `release.yml`, `event == "release"`, tag, commit SHA).
  - `LiveNpmRegistry`: Enforces `--registry https://registry.npmjs.org`.
  - `LiveTapAdapter`: Formula stem normalization preventing `.rb.rb` extensions; fail-closed `HomebrewChannelError` when `brew` or `ruby` are absent.
- `channels/homebrew.py`: Generates formula pointing to npm platform tarball release deliverables (`knowledge-forge-ai-apgr-{platform}-{version}.tgz`).

### C. Packet and Tooling Hardening (Scopes L, M, N, O, P, Q)
- `packet/preflight.py`: Added operational modes (`offline`, `preview`, `live-confirmed`); validates PyPI and all 4 npm packages absence; verifies tools in PATH and GitHub auth.
- `packet/build_assets.py`: Enforces clean public checkout, verifies HEAD commit, tree, and VERSION, and requires empty out-of-tree destination directory.
- `packet/stage_operator.py`: Implemented 8 attended commands (`inspect`, `build-candidate`, `check-candidate`, `publish-staging`, `open-pr`, `check-pr`, `merge-pr`, `reconcile-postmerge`). `publish-staging` uses `--force-with-lease=staging:a0e76457ca84d56099c9c42cfd32297809680339`.
- `packet/operator-packet.json`: Set `staging_authority.branch` to `"staging"`. Signed digest in `operator-packet.sha256`.
- `packet/README.md`: Documented 8 stage operator commands and detailed the 18-step G2 execution plan.
- `docs/adr/2026/09/0057-public-staging-pr-release-procedure.md`: Clarified inter-cycle staging replacement under `--force-with-lease` bound to stale SHA.

### D. Campaign Mock Test Suite (Scope R)
- `private/releases/v0.12.0/test_g2_mocked_campaign.py`: Created comprehensive 24-test suite covering:
  - 8 attended stage operator commands.
  - Fail-closed stop boundaries (staging drift, missing PR CI checks, missing review/waiver, postmerge ancestry drift, postmerge tree mismatch, tampered G2 receipt).
  - End-to-end 18-step mocked campaign simulation.
  - Durable resumption invariant REG-P5 across channel execution.

---

## 4. Verification Suite Results

All verification suites pass 100% cleanly:

| Suite | Tests | Result | Coverage Area |
| :--- | :---: | :---: | :--- |
| `apg-build-go-cli.int.test.py` | 63/63 | PASS | Go CLI build, wrapper, and v0.12 version token integration |
| `version.unit.test.py` | 1/1 | PASS | Python library version agreement with VERSION token |
| `cli.unit.test.py` | 14/14 | PASS | Python CLI version flag and execution tests |
| `release.yml.int.test.py` | 35/35 | PASS | Hosted release workflow contract and governance waiver validation |
| `test_hosted_ci_regressions.py` | 12/12 | PASS | Hosted CI regressions (REG-R1 through REG-R13) |
| `test_live_operator_adapters.py` | 35/35 | PASS | Hardened live channel adapters with mocked REST boundaries |
| `test_release_operator_dry_runs.py` | 19/19 | PASS | Release operator dry run and state machine suite (14 fixtures) |
| `test_g2_mocked_campaign.py` | 24/24 | PASS | 18-step G2 mocked campaign, fail-closed boundaries, and REG-P5 resume |
| `file_length_policy.py` | Clean | PASS | All files strictly under 1,000 line policy limit |
| `check_release_matrix.py` | Clean | PASS | Release readiness matrix mechanical validation |
| `frozen-input-digests.json` | 8/8 | PASS | Cryptographic digest parity across all critical release inputs |
| `operator-packet.sha256` | 1/1 | PASS | Cryptographic integrity of operator release packet |

---

## 5. Zero-Mutation Verification Evidence (Scope S)

Live read-only verification confirms zero external mutations have occurred:

1. **Public `main` branch**:
   - `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/heads/main`:
   - Returns `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441` (unmutated).
2. **Public `staging` branch**:
   - `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/heads/staging`:
   - Returns `a0e76457ca84d56099c9c42cfd32297809680339` (unmutated stale v0.11 tip).
3. **Public `v0.12.0` tag**:
   - `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/tags/v0.12.0`:
   - Returns empty output (tag absent).
4. **Public GitHub Release**:
   - Numeric release ID `389919431` (`v0.11.0`) remains latest release. No `v0.12.0` release exists.
5. **PyPI Index**:
   - Returns HTTP 404 for `agentic-praxis-grimoire==0.12.0`.
6. **npm Registry**:
   - Returns HTTP 404 for `@knowledge-forge-ai/apgr@0.12.0` and all 3 platform packages.
