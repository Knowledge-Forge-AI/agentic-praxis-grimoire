# APG152C — APGR V0120-G1-REPAIR3 — Release Authority Evidence and Crash-Resume Closure Exit

Phase ID: `APG152C`
Exit ID: `Exit 00204`  
Governing Decisions: [ADR 0057](../../../../adr/2026/09/0057-public-staging-pr-release-procedure.md), [ADR 0068](../../../../adr/2026/09/0068-release-authority-reconciliation-with-advanced-public-main.md)\
Entry Commit: `7eff81f0c8abba2a63e892d2deb934f58e25f366`  
Exit Target: `V0120_G1_RELEASE_AUTHORITY_EVIDENCE_CLOSED_AND_G2_READY`  

---

## 1. Status and Disposition

- **Disposition**: **accept**
- **Milestone Outcome**: `V0120_G1_RELEASE_AUTHORITY_EVIDENCE_CLOSED_AND_G2_READY`
- **Scope Delivery**: Resolved all 16 post-work review findings (F1–F16) across Scopes A through P for APGR v0.12.0 release authority, hosted qualification, and crash-resumable execution:
  - **F1 [Scope C/O]**: In `reconcile_postmerge_action`, strictly requires `pr-check-receipt.json` and its `.sha256` sidecar, validates `hosted_qualification` and `aggregate_tested_tree`, enforces `aggregate_tested_tree == projected_tree`, and sets `"aggregate_tested_tree": aggregate_tested_tree` with zero `or projected_tree` fallback.
  - **F2 [Scope B]**: Candidate authority receipt (`candidate-authority-receipt.json`) is mandatory and fail-closed across `publish_staging_action`, `open_pr_action`, `check_pr_action`, `merge_pr_action`, and `reconcile_postmerge_action`. Added `--candidate-receipt` to CLI subparsers in `stage_operator.py`. Required valid `g2-staging-receipt.json` in `create_tag_action`.
  - **F3 [Scope I]**: In `stage_operator.py:check_pr_action`, PR-body waiver does not self-authorize without explicit `--governance-waiver` matching the bounded body block. Added fail-closed rejection test.
  - **F4 [Scope A]**: In `stage_operator.py:collect_hosted_qualification`, enforced all Requirement 5 constraints on explicitly supplied `workflow_run_id`; enforced exact PR number matching against run `pull_requests` metadata; sorted matching runs deterministically by immutable integer ID and recorded `run_selection_reason`.
  - **F5 [Scope F]**: In `github_release.py`, `_get_release_notes` fails closed if `release-notes.md` is missing or empty; release name and body matching are strictly required (exact bytes, no `.strip()`); `target_commitish` is checked across `prepare()`, `publish()`, `verify()`, and `resume()`. `DryRunGitHubApi` in `runner.py` and `test_release_operator_dry_runs.py` tracks and returns `name`, `body`, and `target_commitish`.
  - **F6 [Scope G]**: In `npm.py`, packages in `accepted` or `processing` state do not re-publish (proceeds directly to bounded polling); in `live.py:get_publication_status`, any non-200 2xx raises `NpmChannelError` and removed fallthrough `return "not_found"`.
  - **F7 [Scope K]**: In `pypi.py`, `started_after` is mandatory from GitHub channel receipt; in `live.py:observe_workflow_run`, `started_after` is required; `pypi.py` enforces real `digests.sha256` in both `prepare` and `verify` without fallback to `f.get("sha256")`. `MockPyPiApi` and `DryRunPyPiApi` upload normalizers emit canonical `digests: {"sha256": ...}`.
  - **F8 [Scope E]**: In `packet/preflight.py`, GitHub release checks strictly distinguish HTTP 200, HTTP 404 (absent), and unknown errors (fail-closed); in `resume-publication`, `receipts/channel-github.json` must exist and match remote numeric release ID.
  - **F9 [Scope O]**: AST static checks in `test_no_synthetic_authority.py` (`test_no_broad_exception_to_not_found`, `test_no_locally_fabricated_success_job_maps_or_matrices`, `test_no_postmerge_projected_tree_fallback`). Suite passes 11/11 in 0.31s.
  - **F10 [Scope L]**: In `authority.py` and `build_assets.py`, `SHA256SUMS` accepts 9 or 15 canonical deliverable rows. When 15 rows, `go/` rows are first-class verified authority validated against `canonical_manifest["binaries"][target]["sha256"]` and `["manifest"]["sha256"]`.
  - **F11 [Scope H]**: In `homebrew.py:publish` and `verify`, calls `self.tap.clone_or_sync_tap()`, performs exact SHA-256 byte digest comparison (no `.strip()`), and persists `observed_formula_sha`.
  - **F12 [Scope D]**: Derived deterministic tagger date from `DEFAULT_RELEASE_EPOCH = 1789689600`.
  - **F13 [Scope C]**: Removed ambiguous `calc_hq2` alternative for hosted qualification digest in `preflight.py`.
  - **F14**: Updated Exit Target string to `V0120_G1_RELEASE_AUTHORITY_EVIDENCE_CLOSED_AND_G2_READY`.
  - **F15**: Updated claims to strictly reflect candidate authority receipt and tree parity enforcement.
  - **F16**: Recorded all 22 required qualification gates with exact commands, exit codes, and test counts.
- **Strict Zero-Mutation Boundary Confirmation**:
  - Phase APG152C / V0120-G1-REPAIR3 produce and revise_close stages only.
  - ZERO external mutations performed: no git branch push, PR creation, squash merge, tag creation, GitHub Release publication, PyPI upload, npm upload, or Homebrew tap commit/PR.
  - Public authorities verified completely clean and frozen:
    - Expected private APGR main: `7eff81f0c8abba2a63e892d2deb934f58e25f366`
    - Public main: `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441`
    - Public staging: `a0e76457ca84d56099c9c42cfd32297809680339` (stale v0.11 staging head)
    - Latest release: `v0.11.0` (numeric ID `389919431`)
    - Tag `v0.12.0`: absent
    - PyPI `0.12.0`: HTTP 404 (absent)
    - npm `@knowledge-forge-ai/apgr*` (all 4 packages): HTTP 404 (absent)
    - Homebrew tap main: `db8e6bec3a2a6a5aa504b58add21896a655691f1` (unmutated baseline)
    - GitHub open PRs: 0 open PRs
  - Subphase V0120-G2 remains **NOT STARTED**.
  - Agent-Central (`~/projs/agent-central`) remains active, supported, and unmutated.

---

## 2. Full 22 Qualification Gates

All 22 qualification gates required for V0120-G1 completion and V0120-G2 readiness executed to terminal completion with recorded command lines, exit codes, and test counts:

| Gate | Verification Gate | Command | Exit Code | Tests / Checks | Result | Coverage Area |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **Gate 1** | Real Schema Manifest E2E | `pytest private/releases/v0.12.0/test_real_schema_manifest_e2e.py` | 0 | 16/16 | **PASS** | Canonical distribution manifest builder, `size_bytes` schema, 9/15 `SHA256SUMS` rows, fail-closed rejections |
| **Gate 2** | Stage Operator Unit & Hosted Qual | `pytest private/releases/v0.12.0/test_stage_operator.py` | 0 | 25/25 | **PASS** | Candidate authority receipts, real hosted qualification collector (11 failure modes), PR waiver markers |
| **Gate 3** | Live Operator Channel Adapters | `pytest private/releases/v0.12.0/test_live_operator_adapters.py` | 0 | 45/45 | **PASS** | Live channel adapters with mocked REST boundaries, npm 401/403/500 status checks, PyPI digests |
| **Gate 4** | Release Operator Dry-Runs | `pytest private/releases/v0.12.0/test_release_operator_dry_runs.py` | 0 | 19/19 | **PASS** | Release operator dry run and state machine suite across all 5 channels |
| **Gate 5** | Mocked Campaign & Anti-Synthetic | `pytest private/releases/v0.12.0/test_g2_mocked_campaign.py private/releases/v0.12.0/test_no_synthetic_authority.py` | 0 | 55/55 | **PASS** | 18-step G2 campaign simulation, fail-closed boundary injections, REG-P5 resume, AST synthetic authority checks |
| **Gate 6** | Release Workflow Contract Integration | `pytest src/test/int/python/agentic-praxis-grimoire/.github/workflows/release.yml.int.test.py` | 0 | 36/36 | **PASS** | Hosted release workflow contract, bounded governance waiver parsing, review validation |
| **Gate 7** | Release Workflow Unit & Regressions | `pytest src/test/unit/python/agentic-praxis-grimoire/.github/workflows/release.yml.unit.test.py private/releases/v0.12.0/test_hosted_ci_regressions.py` | 0 | 15/15 | **PASS** | Unit validation of release.yml and REG-R1 through REG-R13 hosted CI regressions |
| **Gate 8** | V2 Closeout & Result Repair Suite | `bin/apg-test-dispatcher -k "test_agent_phase_v2 or test_agent_phase_result_repair"` | 0 | 144/144 | **PASS** | V2 terminal closeout results, formatting repair loops, result-repair JSON evidence |
| **Gate 9** | Package Deliverable Qualification | `python3 libexec/apg_distribution_candidate.py check` & `test_real_schema_manifest_e2e.py` | 0 | 10 packages | **PASS** | Evaluated 10 canonical distribution packages (wheels, sdist, npm tarballs) against canonical manifest |
| **Gate 10** | Two-Pass Deterministic Builds | `test_real_schema_manifest_e2e.py::TestManifestSchemaE2E::test_01_builder_e2e_real_deliverables` & `build_assets.py` | 0 | Bit-for-bit identity | **PASS** | Verified secondary pass rebuild bit-for-bit SHA-256 equality across all release deliverables |
| **Gate 11** | Full Dispatcher Regression Suite | `bin/apg-test-dispatcher -n auto` | 0 | 1975 passed (5 skipped) | **PASS** | Comprehensive APGR dispatcher test suite executed in 447.21s (07:27) across 18 workers |
| **Gate 12** | Go Suite Comprehensive | `go test -count=1 ./...` | 0 | 19 packages | **PASS** | Full Go candidate, internal/cli, internal/gitexec, hotspot, report, envsnap test suites |
| **Gate 13** | Go Static Analysis (Vet) | `go vet ./...` | 0 | 19 packages (0 warnings) | **PASS** | Go compiler and static analyzer checks clean |
| **Gate 14** | Go Race Detector | `go test -race -count=1 ./...` | 0 | 19 packages | **PASS** | Full Go suite passed under Go thread-sanitizer race detector |
| **Gate 15** | Canonical Release Readiness Matrix | `bin/apg-check-release-matrix` | 0 | 38/38 rows | **PASS** | Release readiness matrix mechanical validation (13 REG-R, 13 REG-P, 12 F-traceability) |
| **Gate 16** | Record Identity & Exit Coverage | `bin/apg-check-record-identity --format json` | 0 | 202 exits / 68 ADRs | **PASS** | Record identity gate verified clean (`"status": "pass"`, next ADR: 0069, next exit: 00205) |
| **Gate 17** | Roadmap Closure Verification | `bin/apg-check-roadmap-closure --json` | 0 | 55/55 terminal | **PASS** | 55 terminal rows, 0 open items, `zero_backlog_qualified: true` |
| **Gate 18** | File Length Policy Gate | `python3 tools/ci/file_length_policy.py` | 0 | 0 violations | **PASS** | Strict repository file length policy compliance across all tracked Python files |
| **Gate 19** | Generated Corpus Drift Gate | `python3 tools/ci/check_generated_drift.py` | 0 | Clean | **PASS** | Corpus drift classification: passed (`apg-generated-corpus-drift-v1`) |
| **Gate 20** | Prompt Defense Audit Gate | `python3 tools/ci/prompt_defense_check.py` | 0 | Score: 100/100 | **PASS** | 46 files audited, 0 embedded payloads, 0 unicode issues |
| **Gate 21** | Pre-Review Static Checks | `python3 tools/ci/pre_review_checks.py` | 0 | Clean | **PASS** | Static evaluation, policy checks, scanner suppressions verified clean |
| **Gate 22** | JACA Consumer Policy Verification | `go test -v -count=1 ./testing/fixtures/jaca_consumer ./testing/fixtures/xo_consumer ./testing/fixtures/external_consumer` | 0 | 23/23 | **PASS** | JACA Lane B policy contract, XO adapter containment, external consumer boundaries verified |

---

## 3. Zero-Mutation Verification Evidence & Handoff

Live read-only verification confirms zero external mutations have occurred between phase entry and phase exit:

1. **Public `main` branch**:
   - Command: `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/heads/main`
   - Entry Readback: `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441 refs/heads/main`
   - Exit Readback: `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441 refs/heads/main` (unmutated).
2. **Public `staging` branch**:
   - Command: `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/heads/staging`
   - Entry Readback: `a0e76457ca84d56099c9c42cfd32297809680339 refs/heads/staging`
   - Exit Readback: `a0e76457ca84d56099c9c42cfd32297809680339 refs/heads/staging` (unmutated stale v0.11 tip).
3. **Public `v0.12.0` tag**:
   - Command: `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git 'refs/tags/v0.12.0*'`
   - Entry Readback: Empty output (tag absent).
   - Exit Readback: Empty output (tag absent).
4. **Public GitHub Release**:
   - Command: `gh api repos/Knowledge-Forge-AI/agentic-praxis-grimoire/releases/latest --jq '{tag_name, id, draft, prerelease}'`
   - Entry Readback: Numeric release ID `389919431` (`v0.11.0`).
   - Exit Readback: Numeric release ID `389919431` (`v0.11.0`) remains latest release. No `v0.12.0` release exists.
5. **PyPI Index**:
   - URL: `https://pypi.org/pypi/agentic-praxis-grimoire/0.12.0/json`
   - Entry Readback: HTTP 404 (absent).
   - Exit Readback: HTTP 404 (absent).
6. **npm Registry**:
   - URLs: `https://registry.npmjs.org/@knowledge-forge-ai/apgr/0.12.0` and platform packages `darwin-arm64`, `linux-x64`, `linux-arm64`.
   - Entry Readback: HTTP 404 across all 4 packages (absent).
   - Exit Readback: HTTP 404 across all 4 packages (absent).
7. **Homebrew Tap**:
   - Command: `git ls-remote https://github.com/Knowledge-Forge-AI/homebrew-tap.git refs/heads/main`
   - Entry Readback: `db8e6bec3a2a6a5aa504b58add21896a655691f1 refs/heads/main`
   - Exit Readback: `db8e6bec3a2a6a5aa504b58add21896a655691f1 refs/heads/main` (unmutated baseline).
8. **GitHub Pull Requests**:
   - Command: `gh pr list --repo Knowledge-Forge-AI/agentic-praxis-grimoire --state open`
   - Entry Readback: `[]` (0 open PRs).
   - Exit Readback: `[]` (0 open PRs).

### Repository Identity Evidence:
- **Private Working Commit**: `7eff81f0c8abba2a63e892d2deb934f58e25f366`
- **Private Working Tree SHA**: `4dcaa61140b232c0e97c1abdb650e39aba990b3c`
- **Candidate Commit (to be published in G2)**: `482c5684179008421a90db69a5e5744ddffcc2d3`

### Exact First G2 Staging Handoff Command:
```bash
python3 private/releases/v0.12.0/packet/stage_operator.py publish-staging 482c5684179008421a90db69a5e5744ddffcc2d3 --candidate-receipt private/releases/v0.12.0/packet/candidate-authority-receipt.json --confirm
```

