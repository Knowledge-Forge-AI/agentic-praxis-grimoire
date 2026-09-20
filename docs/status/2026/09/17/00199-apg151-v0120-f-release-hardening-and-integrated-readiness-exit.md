# APG151 — APGR V0120-F — Release Hardening, Conditional Nixpkgs, and Integrated Readiness Exit

Phase ID: `APG151`
Exit ID: `Exit 00199`  
Governing Decision: [ADR 0062](../../../../adr/2026/09/0062-v012-release-hardening-and-conditional-nixpkgs.md)\
Entry Commit: `faf07edd271fd866cfc795e1bca6f405f5838b3c`  
Exit Target: `V0120_F_RELEASE_HARDENING_AND_INTEGRATED_READINESS_COMPLETE`  

---

## 1. Status and Disposition

- **Disposition**: **advance**
- **Milestone Outcome**: `V0120_F_RELEASE_HARDENING_AND_INTEGRATED_READINESS_COMPLETE`
- **Scope Delivery**: Complete technical release readiness for APGR v0.12.0 delivered without performing public release.
- **Strict Boundary Confirmation**:
  - Phase V0120-F only.
  - Milestone V0120-G has **NOT** begun.
  - v0.12.0 has **NOT** been tagged or published to any public channel.
  - JACA and Agent-Central have **NOT** been mutated.

---

## 2. Accomplishments by Scope Area

### A. Release Operator Architecture & State Machine
Consolidated the release operator into a modular, deterministic, resumable state machine in `private/releases/v0.12.0/release_operator/`:
- **Placement Decision**: Consistent with v0.11 precedent (`private/releases/v0.11.0/`), the v0.12 operator lives under `private/releases/v0.12.0/release_operator/`. This avoids polluting the public candidate tree (`is_v012_candidate_path`), avoids unneeded entries in `release/public-surface.json` and `AUDITED_*` registers, and eliminates test mirroring overhead in `testing/apg-test-inventory.json`.
- **Channel Lifecycle States**: Enforces declared per-channel states without fabricating provider states:
  - npm: `not_started`, `prepared`, `accepted`, `processing`, `published`, `verified`, `blocked`.
  - GitHub, Go, PyPI, Homebrew: `not_started`, `prepared`, `published`, `verified`, `blocked`.
- **Design Invariant (No Background Daemon)**: The release operator runs strictly as an attended, synchronous foreground state machine. Zero background daemons, detached services, or polling loops exist.

### B. Numeric GitHub Draft Release ID Binding (REG-P1)
- Operator release adapter (`private/releases/v0.12.0/release_operator/channels/github_release.py`) binds strictly to the integer draft release ID (`id: int`).
- All subsequent asset operations target the numeric ID (`/repos/{owner}/{repo}/releases/{id}/assets`), eliminating tag-name ambiguity and race conditions.
- On resume, checks that recorded draft ID belongs to expected repository, tag, and release. ID/tag mismatch fails closed to `blocked`.

### C. Release Authority Pre-Check (REG-P2)
- Implemented in `private/releases/v0.12.0/release_operator/authority.py` and `libexec/apg_public_release.py`:
  - Verified single parent commit.
  - **Dynamic Predecessor Resolution**: Resolves predecessor commit SHA dynamically from git tag `refs/tags/v{pred}` (e.g. `v0.11.0`), eliminating hardcoded historical commit gates in release policy while preserving them as regression evidence.
  - Candidate tree matches projected publishable tree (`is_v012_candidate_path`).
  - Commit subject format matches `Release vX.Y.Z`.
  - Version/tag parity verified.
  - Strict zero-tolerance for publication-excluded paths (`private/`, `__pycache__`, etc.).

### D. PyPI OIDC Trusted Publishing Alignment (REG-P3)
- Evaluated `.github/workflows/release.yml`:
  - Verified `id-token: write` permission.
  - Verified `environment: pypi` binding.
  - Verified zero token secret fallbacks (`PYPI_API_TOKEN` or `TWINE_PASSWORD`).
- **Repository-Side vs. Account-Side Split**: Formally distinguished proven repository-side workflow configuration from external account-side PyPI trusted-publisher configuration on `pypi.org`, which is recorded as an explicit **operator readback requirement in V0120-G**.

### E. npm Distribution State Machine (REG-P4)
- Platform package ordering: platform binaries (`darwin-arm64`, `linux-arm64`, `linux-x64`) strictly precede launcher package (`apgr`).
- Full lifecycle progression: `prepared` -> `accepted` -> `processing` -> `published` -> `verified`.
- Tarball verification: downloads published tarball and verifies byte SHA-256 against distribution manifest.
- Recoverable partial state: mid-run failures halt and record partial progress (`recoverable_partial_state`); never silently marked completed; no destructive unpublish.

### F. Resumable Multi-Channel Receipts (REG-P5)
- Independent durable receipts under `<run_dir>/receipts/`:
  - Per-channel files: `channel-{channel}.json`.
  - Append-only event journal: `event-log.jsonl`.
  - Unified terminal receipt: `terminal-receipt.json`.
- **Core Resume Invariant**: On resume, channels in `verified` state are read back and **never** republished or re-uploaded. The operator resumes strictly from the first unverified or blocked channel.

### G. Homebrew Formula Generation & Live Tap Baseline (REG-P6)
- Formula generator in `private/releases/v0.12.0/release_operator/channels/homebrew.py` targeting `darwin/arm64`, `linux/amd64`, `linux/arm64`.
- Validates platform artifact SHA-256 digests against distribution manifest.
- Pluggable `TapRepositoryAdapter` seam ensures hermetic, deterministic testing of fresh vs. stale baselines.
- Stale cached tap baseline strictly fails closed.
- Before/after patch diff is generated and retained. Live tap was **not** mutated during V0120-F.

### H. Postmerge Source Proof (REG-P7)
- Implemented in `private/releases/v0.12.0/release_operator/postmerge.py` and `libexec/apg_public_release.py:check_merged_source`.
- Confirms that squashed merge commit on `main` contains the exact projected tree of the release candidate and a single parent pointing to the predecessor release commit before tagging.
- Emits deterministic machine receipt `postmerge-receipt.json`.

### I. Manifest & Receipt Serialization Integrity (REG-P8)
- All manifests, provenance receipts, and binary manifests enforce deterministic serialization: sorted keys, single trailing LF (`\n`), and lowercase SHA-256 hex digests (`[0-9a-f]{64}`).
- Uppercase hex digests are rejected fail-closed with `ReceiptSerializationError` / `ReleaseAuthorityError`.

### J. Deterministic Release Epoch Policy (REG-P9)
- Release epochs resolve strictly from `RELEASE_EPOCH_BY_VERSION[requested_version]` in `libexec/apg_python_distribution.py`.
- Tested historical fixtures: `0.11.0` binds `1789000000`; stale v0.10 epoch `1788996391` is rejected.
- Missing epoch for `0.12.0` fails closed with `NormalizationError`. Epoch selection is surfaced as an explicit **V0120-G precondition**.

### K. Merged-Check Contract Stability (REG-P10)
- `libexec/apg_public_release.py:check_merged_source` and operator postmerge verification make zero network calls to GitHub and enforce zero hidden approval or merge-commit-SHA gates.
- Passes deterministically on single-parent release commit on `main`.

### L. Operator Preconditions & Attestation Binding (REG-P11)
- Requires explicit `--premerge-main` commit SHA and complete set of `--required-check NAME=success` flags.
- Any governance waiver supplied via `--approved-pr` is preserved verbatim in the receipt, never normalized into an unqualified approval claim.

### M. PyPI Verification-Only Fail-Closed Path (REG-P12)
- If version already exists on PyPI:
  - Exact match of file count (3 wheels + 1 sdist) and byte-identical SHA-256 digests switches channel to verification-only.
  - Missing file, extra file, count mismatch, or digest mismatch halts fail-closed (`blocked`).
  - `--skip-existing` is strictly forbidden.

### N. Non-Destructive Host Binary Coexistence (REG-P13)
- Implemented in `private/releases/v0.12.0/release_operator/coexistence.py`:
  - Inspects `PATH` for pre-existing `apgr` (e.g. `/run/current-system/sw/bin/apgr`).
  - Never blindly unlinks, force-links, or overwrites host binaries.
  - Surfaces collision as explicit operator limitation (`detected_nondestructive_coexistence`).

### O. Hosted-CI Repair Cases (REG-R1 through REG-R13)
Codified in `private/releases/v0.12.0/test_hosted_ci_regressions.py` and registered in the canonical matrix:
- `REG-R1`: `tomli==2.4.1` pinning in `tools/ci/bootstrap_static.sh` and `tools/ci/dependency_inventory.py`.
- `REG-R2`: Scratch directory `python-work` pre-creation in `tools/ci/qualify_packages.sh`.
- `REG-R3`: Pinned `actions/setup-go` in `public-pr.yml` and 512-byte stderr diagnostic capture in `libexec/apg_skill_topology.py`.
- `REG-R4`: OASIS SARIF 2.1.0 `toolComponentReference` in `tools/ci/codeql_policy.py`.
- `REG-R5`: Zero unchecked capacity expansion in `internal/cli/skills.go` and `0o700`/`0o600` permissions.
- `REG-R6`: Matrix receipt resilience in `release/ci/matrix_receipts.py`.
- `REG-R7`: Linear staging correction discipline in `libexec/apg_staging_correction.py` and `test_stage_operator.py`.
- `REG-R8/R9`: Tracked Python file length policy in `tools/ci/file_length_policy.py`.
- `REG-R10`: APFS rename write permission pre-check (0o700) and Playwright cleanup.
- `REG-R11`: Test coverage enforcement (>=80%) across test inventory.
- `REG-R12`: Single-root operator handoff structure in `private/releases/`.
- `REG-R13`: Govulncheck symbol-level call-trace classification in `testing/public-ci-runtime.json`.

### P. F1–F12 Traceability Mapping
Canonical mapping registered in `testing/release/release-readiness-matrix.json` matching `docs/architecture/v0-12-v011-publication-regression-inputs.md` §4:
- `F1` -> `REG-P9` (durable)
- `F2` -> `REG-P10` (durable)
- `F3` -> `REG-P11`, `REG-P2` (durable)
- `F4` -> `REG-P11` (durable)
- `F5` -> `REG-P6` (durable)
- `F6` -> `REG-P12` (durable)
- `F7` -> `REG-P13` (durable)
- `F8` -> `REG-P4` (npm recovery durable; closeout completeness enforced by V0120-G contract)
- `F9` -> `REG-R11` / release test suite gate (durable)
- `F10` -> `REG-R12`, `REG-P8` (durable)
- `F11` -> `REG-P8` (durable)
- `F12` -> `REG-P3` (superseded scheduling artifact)

### Q. Canonical Release Readiness Matrix & Mechanical Checker
- Created `testing/release/release-readiness-matrix.json` (38 total rows: 13 REG-R, 13 REG-P, 12 F-traceability).
- Created maintained checker `testing/release/check_release_matrix.py` and launcher `bin/apg-check-release-matrix`.
- Enforces mechanical `fixture` existence validation on all 38 rows, checking that every referenced python function physically exists in its declared `test_path`.
- Wired into CI pre-review gates: added `Check("release-matrix", ...)` to `tools/ci/pre_review_checks.py` and registered `"release-matrix"` in `POLICY_CHECKS` (`tools/ci/pre_review_records.py`).
- Added integration test `src/test/int/python/agentic-praxis-grimoire/bin/apg-check-release-matrix.int.test.py` and registered ownership in `testing/apg-test-inventory.json`.

### R. Release Operator Dry-Run Fixtures
All 19 dry-run fixtures implemented in `private/releases/v0.12.0/test_release_operator_dry_runs.py` passed with 100% success (19/19 passed in 0.037s):
- REG-P1: Draft release ID binding and mismatch detection.
- REG-P2: Candidate authority pre-checks (single-parent, tree match, version match, excluded path checks, distribution manifest asset checksum validation).
- REG-P3: PyPI OIDC trusted publisher workflow validation.
- REG-P4: npm multi-stage lifecycle, tarball SHA verification, and recoverable partial state.
- REG-P5: Resumable multi-channel receipts with non-repetition of verified channels.
- REG-P6: Homebrew formula generation, digest verification, and live tap baseline refresh.
- REG-P7: Postmerge source tree proof.
- REG-P8: Manifest and receipt serialization integrity (rejecting uppercase digests).
- REG-P9: Deterministic release epoch binding.
- REG-P10: Merged-check contract stability (zero GitHub network calls, single-parent squash).
- REG-P11: Operator precondition and attestation binding (verbatim waiver preservation).
- REG-P12: PyPI verification-only fail-closed path.
- REG-P13: Non-destructive host binary coexistence.
- Channel state transition legal matrix guards (rejecting illegal transitions, terminal verified protection, sequence number increments).

### S. Nixpkgs Conditional Disposition
- Fully evaluated and documented in `docs/evaluations/apg151-v0120-f-nixpkgs-conditional-disposition.md`.
- Formally dispositioned as **`condition-not-met` / `deferred-not-admitted-for-v0.12`** based on audit of `theme-forge-stellar-burst_dev`.
- V0120-G proceeds with 5 channels.

### T. Agent-Central Reference Doctrine
Preserved intact. Agent-Central is active and supported; no retirement, mutation, or decommissioning occurred.

### U. Request V2 Terminal Closeout Result Repair Integration (Recovery1)
- **Failure Root Cause Analysis**: Preserved failed historical run `apgr-run-v2-implementation_testing-20260918T003756Z-0774ecbe` as immutable evidence. Across semantic turns 1 through 4, all operations succeeded. At Turn 5 (closeout agent), the LLM emitted valid closeout JSON with start fence `<<<AGENT-PHASE-RESULT <nonce>>>>` but omitted the trailing closing fence, triggering `RESULT_MISSING_FENCE`. While V1 single-phase dispatch possesses a mature repository-detached formatting repair loop (`result_repair.py`), Request V2 (`v2_turns.py`) lacked the wiring to invoke this repair mechanism, failing closed prematurely.
- **Reference Parity Repair Architecture**:
  - Implemented `libexec/agent_phase/v2_repair.py` providing single-shot, repository-detached formatting repair for Request V2 terminal closeout responses.
  - Strict admission criteria: terminal process launched, transport exit 0, all prior semantic turns complete, candidate tree captured and stable, typed `ResultError`, formatting-repairable under mature policy (no structured authority / no invalid path dispositions), strictly 1-shot.
  - Invariants enforced: same provider/profile, fresh nonce, empty isolated temp scratch directory outside git checkouts, read-only posture, pass only retained response as inert data, zero candidate mutations (`RESULT_REPAIR_CANDIDATE_MUTATED`), zero scratch side effects (`RESULT_REPAIR_SIDE_EFFECT`), strict parse repaired response.
  - Machine evidence recorded in `result-repair.json` and `result-repair-cwd.json`, auxiliary attempt persisted in SQLite `invocation_attempts` (`att-{run_id}-{binding_id}-repair-1`), and accounted in `result.json` (`auxiliary_provider_invocations: 1`, `total_effective_provider_turns: 6`) and `result.md`.
  - Comprehensive regression test suite delivered in `src/test/dispatcher/test_agent_phase_v2_result_repair.py` (7 tests).

---

## 3. Verification and Qualification Summary

| Verification Gate | Command | Result |
| :--- | :--- | :--- |
| **Release Readiness Matrix** | `bin/apg-check-release-matrix` | **PASS** (38/38 rows verified, 100% fixtures validated) |
| **Release Operator Dry-Runs** | `PYTHONPATH=private/releases/v0.12.0 python3 private/releases/v0.12.0/test_release_operator_dry_runs.py` | **PASS** (19/19 passed in 0.037s) |
| **Hosted CI Regressions** | `python3 private/releases/v0.12.0/test_hosted_ci_regressions.py` | **PASS** (12/12 passed in 0.133s) |
| **Matrix Integration Test** | `python3 src/test/int/python/agentic-praxis-grimoire/bin/apg-check-release-matrix.int.test.py` | **PASS** (2/2 passed in 0.056s) |
| **V2 Result Repair Tests** | `python3 bin/apg-test-dispatcher src/test/dispatcher/test_agent_phase_v2_result_repair.py` | **PASS** (7/7 passed in 7.72s) |
| **V2 & Repair Test Suite** | `python3 bin/apg-test-dispatcher -k "test_agent_phase_v2 or test_agent_phase_result_repair"` | **PASS** (144/144 passed in 308.87s) |
| **Test Inventory Integrity** | `apg_test.validate_inventory` | **PASS** (190 tests, zero missing, zero stale) |
| **Pre-Review Static Checks** | `pytest src/test/unit/python/agentic-praxis-grimoire/tools/ci/pre_review_*.py` | **PASS** (18/18 passed in 0.22s) |
| **File Length Gate** | `python3 tools/ci/file_length_policy.py` | **PASS** (0 failures across all tracked Python files) |
| **Record Identity Gate** | `bin/apg-check-record-identity --format json` | **PASS** (next exit: 00199, next ADR: 0068) |
| **Roadmap Closure Gate** | `bin/apg-check-roadmap-closure --json` | **PASS** (55/55 terminal, zero open) |
| **Generated Drift Gate** | `python3 tools/ci/check_generated_drift.py` | **PASS** |
| **Prompt Defense Gate** | `python3 tools/ci/prompt_defense_check.py` | **PASS** (score: 100/100) |

---

## 4. Operational Transition to V0120-G

Technical release readiness for APGR v0.12.0 is fully established. All invariants from ADR 0062 are mechanically verified.

### Pre-Release Preconditions Surfaced for V0120-G:
1. **v0.12 Release Epoch Selection**: Repository policy must select and register the v0.12 reproducible timestamp in `RELEASE_EPOCH_BY_VERSION["0.12.0"]` (`libexec/apg_python_distribution.py`).
2. **PyPI Account-Side Readback**: Operator must perform external readback of the PyPI trusted publisher configuration on `pypi.org`.
3. **Release Workflow Alignment**: `.github/workflows/release.yml` hardcodes `expected_tag=v0.11.0` and `expected_version=0.11.0`, which must be aligned to `v0.12.0` upon candidate branch cut.
4. **Five-Channel Execution**: Publication will execute across GitHub Releases, Go, PyPI, npm, and Homebrew.

Milestone V0120-G has **NOT** begun.
