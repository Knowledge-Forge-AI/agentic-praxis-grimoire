# APG152 — APGR V0120-G1 — Publication Preparation, Live Operator Wiring, and Authority Reconciliation Exit

Phase ID: `APG152`
Exit ID: `Exit 00201`  
Governing Decision: [ADR 0068](../../../../adr/2026/09/0068-release-authority-reconciliation-with-advanced-public-main.md)\
Entry Commit: `4a09a0a029dcd5d87428f32b9ab93977089d7ac5`  
Exit Target: `V0120_G1_PUBLICATION_PREPARATION_AND_OPERATOR_WIRING_COMPLETE`  

---

## 1. Status and Disposition

- **Disposition**: **accept**
- **Milestone Outcome**: `V0120_G1_PUBLICATION_PREPARATION_AND_OPERATOR_WIRING_COMPLETE`
- **Scope Delivery**: Reconciled release authority with advanced public `main` (`7c77619cdc54f1f6d87c36eb20a11ea0b30a2441`), registered deterministic release epoch `1789689600` (`2026-09-18T00:00:00Z`), updated `.github/workflows/release.yml` with compare API queries and removed stale PR association gates, implemented and verified live publication adapters, and constructed the complete immutable operator release packet.
- **Strict Zero-Mutation Boundary Confirmation**:
  - Phase APG152 / V0120-G1 only.
  - ZERO external release mutations performed: no git branch push, PR creation, merge, tag creation, GitHub Release publication, PyPI upload, npm upload, or Homebrew tap commit/PR.
  - Subphase V0120-G2 remains **NOT STARTED**.
  - Agent-Central (`~/projs/agent-central`) remains active, supported, and unmutated.
  - JACA remains unmutated.

---

## 2. Background and Operational Gaps Addressed

Following the publication of APGR v0.11.0, public repository `Knowledge-Forge-AI/agentic-praxis-grimoire` advanced on `main` with commit `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441` ("ci: remove stale run PR association gate").

This phase resolved all authority reconciliation and operator hardening findings:
1. **Linear Lineage Reconciliation**: Previous release tools (`apg_public_release.py`) assumed `base.head == tag:v0.11.0`. When `main` advanced with single-parent maintenance commits, verification failed. Lineage verification was extended to accept an advanced `premerge_main` descending linearly from `v0.11.0` via `git merge-base --is-ancestor`.
2. **Brittle Hosted Release Workflow Gates**: `.github/workflows/release.yml` contained a fragile jq filter checking `.pull_requests // []` that broke on squash merges. This was replaced with an authoritative GitHub Compare API query (`ahead|identical`, `behind_by == 0`) and `pr_base_sha == premerge_main` assertions.
3. **Live Operator Adapters**: Implemented concrete live adapters (`LiveGitHubApi`, `LiveGoProxy`, `LivePyPiApi`, `LiveNpmRegistry`, `LiveTapAdapter`) adhering to REG-P1 (numeric release ID binding), REG-P6 (platform before launcher), and fail-closed state machines.
4. **Preview Mode & Dual-Mode Execution**: Release operator CLI defaults to read-only preview mode unless explicitly confirmed with `--confirm` and `--live`. Direct script execution is supported via relative import fallbacks.
5. **Deterministic Epoch**: Registered `V012_RELEASE_EPOCH = 1_789_689_600` (`2026-09-18T00:00:00Z`) across distribution and publication tools.

---

## 3. Implementation Summary

### A. Version and Epoch Registration
- `src/agentic_praxis_grimoire/VERSION`: Bumped to `0.12.0`.
- `libexec/apg_python_distribution.py`: Registered `V012_RELEASE_EPOCH = 1_789_689_600` in `RELEASE_EPOCHS` and `RELEASE_EPOCH_BY_VERSION["0.12.0"]`.
- `libexec/apg_python_publication.py`: Updated `EPOCH = distribution.RELEASE_EPOCH_BY_VERSION["0.12.0"]`.
- `release/v0.12.0-notes.md`: Authored candidate release notes.
- `release/public-surface.json`: Registered `release/v0.12.0-notes.md` in `critical_files`.

### B. Authority Reconciliation Tooling
- `libexec/apg_public_release.py`:
  - Added `V012_CRITICAL_ADDITIONS` (`docs/v0-12-roadmap.md`, `release/v0.12.0-notes.md`) and audited surfaces for `0.12.0`.
  - Added `allow_advanced_head=(core == "0.12.0")` to `verify_public_release_lineage`, `build_candidate`, and `check_candidate`.
  - Added `allow_v011_compatibility=True` across `load_policy` invocations.
  - Reconciled `check_merged_source` to verify `premerge_main == base.head`, ancestor verification via `git merge-base --is-ancestor`, parent verification `parent_record[1] == premerge_main`, and single commit count.
- `libexec/apg_staging_correction.py`:
  - Updated `build_untagged_candidate` to allow `0.12.0` and pass `allow_advanced_head` and `allow_v011_compatibility`.

### C. Hosted CI Release Workflow
- `.github/workflows/release.yml`:
  - Maintained strict JSON-in-.yml structure with `checks: read` permissions.
  - Updated release tag/version to `v0.12.0` / `0.12.0` and predecessor to `v0.11.0`.
  - Derived `premerge_main="$merged_parent"`.
  - Wired Compare API query `gh api .../compare/$accepted_base...$premerge_main`.
  - Removed stale PR association gate filter.
  - Bound `pr_base_sha == $premerge_main` in `matrix-aggregate.json` and tested commit parent assertions.

### D. Live Operator Adapters and Execution Driver
- `private/releases/v0.12.0/release_operator/channels/live.py`: Created with `LiveGitHubApi`, `LiveGoProxy`, `LivePyPiApi`, `LiveNpmRegistry`, and `LiveTapAdapter`.
- `private/releases/v0.12.0/release_operator/runner.py`: Added dual-mode import fallbacks, `--confirm`, `--live`, packet derivation for `version`/`release_epoch`/`premerge_main`, and automatic fallback to read-only preview mode when `--confirm` is omitted.
- `private/releases/v0.12.0/release_operator/postmerge.py`: Added support for `premerge_main` alias in `verify_postmerge_squash_commit`.

### E. Immutable Operator Packet
Constructed complete packet in `private/releases/v0.12.0/packet/`:
- `operator-packet.json` and `operator-packet.sha256`
- `frozen-input-digests.json`
- `evidence-index.json`
- `command-receipts.json`
- `release-notes.md`
- `preflight.py`
- `execute.py`
- `reconcile_postmerge.py`
- `stage_operator.py`
- `build_assets.py`
- `README.md`

---

## 4. Verification Suite Results

All test suites passed 100% cleanly:

| Suite | Tests | Result | Coverage Area |
| :--- | :---: | :---: | :--- |
| `apg_python_publication.unit.test.py` | 66/66 | PASS | Python publication normalization and v0.12 registration |
| `apg-normalize-python-sdist.int.test.py` | 5/5 | PASS | Python sdist epoch and metadata normalization |
| `apg_staging_correction.unit.test.py` | 19/19 | PASS | Staging correction unit contract |
| `apg_staging_correction.int.test.py` | 21/21 | PASS | Untagged candidate build and check integration |
| `apg_public_release.unit.test.py` | 70/70 | PASS | Release policy, surfaces, candidate, and lineage unit tests |
| `apg_public_release.int.test.py` | 21/21 | PASS | Full release candidate build, check, and squash integration |
| `release.yml.int.test.py` | 34/34 | PASS | Hosted release workflow contract and compare API queries |
| `test_release_operator_dry_runs.py` | 19/19 | PASS | Release operator dry run and state machine suite |
| `test_hosted_ci_regressions.py` | 12/12 | PASS | Hosted CI regressions (REG-R1 through REG-R13) |
| `test_live_operator_adapters.py` | 35/35 | PASS | Live channel adapters unit tests with mocked boundaries |
| `release_operator/runner.py --dry-run` | 5/5 | PASS | Operator CLI dry run across all 5 channels |
| `packet/preflight.py` (online & offline) | All | PASS | Read-only remote query and packet integrity verification |

---

## 5. Zero-Mutation Verification Evidence

Live read-only verification confirms zero external mutations have occurred:
1. `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/heads/main`:
   - Returns `7c77619cdc54f1f6d87c36eb20a11ea0b30a2441` (unmutated).
2. `git ls-remote https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire.git refs/tags/v0.12.0`:
   - Returns empty output (tag does not exist).
3. PyPI query (`https://pypi.org/pypi/agentic-praxis-grimoire/0.12.0/json`):
   - Returns HTTP 404 (unreleased).
4. npm query (`https://registry.npmjs.org/@knowledge-forge-ai%2Fapgr/0.12.0`):
   - Returns HTTP 404 (unreleased).
