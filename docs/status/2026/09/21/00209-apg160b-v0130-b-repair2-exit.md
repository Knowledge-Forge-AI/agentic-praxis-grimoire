# APG160B — v0.13.0 Review-Policy Persistence Upgrade Repair 2 Exit

Phase ID: `APG160B`
Exit ID: `Exit 00209`
Roadmap Milestone: `V0130-B-REPAIR2`
Governing Decisions: [ADR 0070](../../../../adr/2026/09/0070-configurable-review-stage-mutation-policy.md)
Exit Target: `V0130_B_REVIEW_POLICY_UPGRADE_REPAIR_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **superseded / finalization-failed** (semantic work completed, finalization failed under commit-local without an established commit; reported as lacking commit message metadata per C4 review finding, with candidate adopted by APG160C for corrective repair of manager findings C1–C5)
- **Milestone Outcome**: `V0130_B_REVIEW_POLICY_UPGRADE_REPAIR_SUPERSEDED`
- **Execution Boundary**: Dispatcher implementation across persistence (`persistence.py`), review drift and policy evaluation (`review_drift.py`), review binding (`review_binding.py`), multi-turn execution and prompt rendering (`v2_turns.py`, `v2_prompts.py`, `dispatch.py`, `resume_dispatch.py`), V2 dispatch prelaunch validation (`v2_dispatch.py`), configuration resolution (`config_routing.py`, `cli.py`), Go evidence contracts (`evidence/observation.go`), cross-language conformance fixtures (`review_mutation_vectors.json`, `jaca_consumer/`), and comprehensive qualification suites. Phase produced candidate tree `7cb2a5caa679ae0cb234d297edea4143dfe6dbeb` across 22 paths (19 modified, 3 added). Publication under `commit-local` was not finalized; candidate adopted for corrective phase APG160C.

---

## 1.1 Superseding Manager Review and Defect Clusters (C1–C5)

Following APG160B execution, governing manager review evaluated the 22-path uncommitted candidate (`7cb2a5caa679ae0cb234d297edea4143dfe6dbeb`), dispositioning the run as semantic-completed, finalization-failed, commit absent. Prior acceptance claims are retained below as historical evidence, superseded by the following reproduced defect clusters assigned to corrective phase APG160C:

- **C1 (Historical Migration Facts & Constraints)**:
  - `migrate_schema_v4` synthesized artificial execution rows with `status: completed` in `runs` for orphaned observations; must instead preserve orphans in quarantine tables (`legacy_quarantine_review_mutation_observations`, `legacy_quarantine_review_mutation_policies`) with provenance and no execution semantics.
  - Pre-existing orphan policy rows failed foreign key checks post-migration; migration lacked FK validation before commit.
  - Table triggers and custom indexes starting with `idx_review_mutation_obs_` were dropped.
  - `conn.isolation_level = None` prematurely committed caller uncommitted writes.
  - Policy table retained legacy NOT NULL constraints on `worktree_policy`, failing on valid configurations omitting review policies.
- **C2 (Same-Attempt Evidence & Serialization)**:
  - Repeated clean recheck of the same attempt erroneously replaced stage observation and erased prior drift warnings; same-attempt rechecks must retain cumulative drift.
  - Observer emitted `observation_limitations` while persistence looked up `limitations`, dropping limitations metadata.
  - Freshness helper accepted matching trees without requiring positive runtime-owned git drift observations.
- **C3 (Durable Execution Evidence vs Optional SQL Indexing)**:
  - Turn coordinator raised an exception on SQLite indexing failures even when file-backed `.observation.json` evidence and provider exit zero permitted continuation.
- **C4 (Complete Closeout & Finalization Diagnostics)**:
  - Machine result emitted only bare `{"outcome": "completed"}` lacking required commit message fields, causing commit-local finalization failure.
  - Controller swallowed caught finalization errors, losing root failure diagnostics.
- **C5 (Qualification & Records)**:
  - Qualification hardcoded private host snapshot paths rather than using synthetic test fixtures.
  - Attended runbook claimed stub run synthesis and inaccurate file-copy rollback guidance for WAL-mode SQLite databases.
  - Qualification receipt reported base `HEAD^{tree}` instead of the uncommitted dirty candidate tree.

---

## 2. Core Delivery Summary

### 2.1 Host Database Qualification and Migration v4
- Real host snapshot qualified in read-only mode (`mode=ro`), confirming pre-v4 schema with migrations `[1, 2, 3]` and 2-column primary key `(run_id, stage)` lacking `sequence`.
- Bumped schema version to `SCHEMA_VERSION = 4`.
- Implemented `check_dispatcher_db_compatibility(conn)` and `_is_v4_shape(conn)` to validate table structure (all 33 columns, 3-column primary key `(run_id, stage, sequence)`, `resolved_mode` column in `review_mutation_policies`, and indexes `idx_review_mutation_obs_run` and `idx_review_mutation_obs_attempt`) before execution.
- Implemented transactional `migrate_schema_v4(conn)` using `conn.isolation_level = None` with explicit `BEGIN IMMEDIATE;` ... `COMMIT;` blocks under `PRAGMA foreign_keys = OFF;`, automatically creating stub runs for orphaned historical records and verifying `PRAGMA foreign_key_check;` before commit.
- Preserves legacy rows with honest `attempt_id = NULL` and limitations metadata `[{"kind": "legacy_migrated_record", "detail": "migrated from pre-v4 schema without attempt identity"}]`.
- Concurrency and race safety: queries `MAX(sequence)` inside `BEGIN IMMEDIATE` transactions, ensuring monotonic ordering without sequence collision.
- Replay idempotency: identical observation re-recording succeeds as a no-op; conflicting record modifications raise `PersistenceError`.

### 2.2 Truthful Review Observation and Candidate Freshness
- Extended `ReviewObservation` with attempt identity: `attempt_id`, `binding_id`, `attempt_number`, `policy_generation`, `raw_stdout_artifact`, `raw_stderr_artifact`, and `limitations`.
- Strict separation of drift and observation unavailabilities: `subject_drift_observed` strictly equals `worktree_drift or index_drift or head_drift`. Unavailabilities evaluate directly to `ACTION_BLOCKED` without corrupting drift flags.
- Removed sticky drift overwriting during turn retries: observations remain immutable turn snapshots without cross-turn flag mutability.
- Hardened `derive_final_candidate_freshness`:
  1. Default `has_verified_receipt = False`, requiring explicit receipt verification.
  2. Requires positive work review role (`work_reviewer`, `reviewer`) and subject kind (`work`, `work_product`), strictly rejecting plan reviews.
  3. Enforces 4-way candidate tree hash match: `work_review_candidate_tree == terminal_candidate_tree == obs.expected_tree == obs.observed_tree`.
  4. Strictly rejects candidate freshness on any observation unavailability, review coverage limitations, or allow-mode drift.
  5. Work review outcome `"unreviewable"` or empty explicitly invalidates receipts (`work_review_receipt_valid = False`), preventing false freshness.

### 2.3 Go Evidence Contracts and Conformance Synchronization
- Updated `evidence/observation.go` to include all v4 fields: `Sequence`, `PathsComplete`, `Detail`, `Transport`, `Paths`, `Code`, `ObservationLimitation`.
- Updated `ValidateReviewMutationObservation` to validate unavailabilities as fail-closed (`ActionBlocked`) with appropriate diagnostic codes without setting drift flags.
- Synchronized conformance fixture `testing/fixtures/conformance/review_mutation_vectors.json` and consumer adapter `testing/fixtures/jaca_consumer/adapter.go`.
- Synchronized Go API manifest `docs/architecture/v0-12-apgr-go-api-manifest.json` via `go test ./internal/apimanifest -update`.
- Added `TestReviewMutation_ActualPythonObserverOutputs` executing real Python runtime observations across 11 scenarios with Go cross-validation.

### 2.4 Multi-Turn V2 Runtime Scoping and Prompt Rendering
- Reordered post-runner turn completion in `v2_turns.py`: immediately writes `{attempt_id}.stdout.md` and `{attempt_id}.stderr.txt` before git state inspection or policy evaluation.
- Preserved genuine runner exit code on non-zero exit turns.
- Wrapped post-turn git state inspection in `try / except` to degrade gracefully into limitation records and `{attempt_id}.observation_indexing_failure.json` rather than aborting transport handling.
- Formats attribution-free review-window mutation notices in work and closeout prompts.

### 2.5 V2 Dispatch Prelaunch Checks and Suffix-Resume Prevention
- Integrated `check_dispatcher_db_compatibility(conn)` post-open in `v2_dispatch.py`.
- Rejects `resume_from_run_id is not None` with `PreLaunchFailureError` prelaunch, preventing invalid suffix resumes.
- Added `--inspect-policy` probe to `agent-phase-resolve` in `cli.py` to inspect resolved policy without requiring a request file.
- Closed root keys enforced in `load_policy_file`.

### 2.6 ADR 0074 Amendment
- Amended ADR 0074 Mandatory Doctrine Invariant: when configured budget cannot hold mandatory context, dispatch falls back to static baseline context delivery rather than failing closed.

---

## 3. Verification and Checks

1. `bin/apg-check-record-identity`: PASS (74 ADRs, 207 exits, 207 phase IDs; next ADR 0075; next exit 00210).
2. `bin/apg-check-skill-library`: PASS (45 skills, 45 catalog rows, 45 projections).
3. `bin/apg-check-roadmap-closure`: PASS (55 items, 0 open items, zero backlog qualified).
4. `go test ./...` and `go vet ./...`: PASS (100% across 21 Go packages including `evidence`, `jaca_consumer`, `xo_consumer`, `internal/apimanifest`).
5. Dedicated repair qualification suite `test_agent_phase_review_mutation_repair.py`: PASS (24/24 tests passed).
6. Dispatcher regression suites: PASS (122/122 tests passed across 4 suites):
   - `src/test/dispatcher/test_agent_phase_review_mutation_policy.py`: 39/39 passed
   - `src/test/dispatcher/test_agent_phase_review_immutability.py`: 36/36 passed
   - `src/test/dispatcher/test_agent_phase_lifecycle_dispatch.py`: 41/41 passed
   - `src/test/dispatcher/test_cross_language_conformance.py`: 6/6 passed
   Total Python dispatcher tests passed: 146 / 146 passed.

---

## 4. Work Review Findings Disposition (F1–F18) & Roadmap Requirements (R1–R6)

| ID | Topic | Disposition | Evidence / Resolution Details |
|---|---|---|---|
| **F1** | Cross-language test signature mismatch | Resolved | Added unavailability kwargs (`candidate_observation_unavailable`, etc.) to `ReviewObservation` in `test_cross_language_conformance.py`; all 6 tests pass. |
| **F2** | Record identity & exit counts mismatch | Resolved | Reconciled record identity: 74 ADRs, 207 exits, 207 phase IDs; next ADR 0075; next exit 00210; synced across status and qualification docs. |
| **F3** | Synthetic legacy v3 migration test coverage | Resolved | Implemented `test_synthetic_populated_legacy_v3_migration_preserves_exact_field_bytes` validating all 33 columns, 3-column PK, and byte fidelity. |
| **F4** | Host snapshot migration test assertions | Resolved | Fixed snapshot test with pre-population if empty, verifying schema v4, sequence >= 0, and legacy limitations. |
| **F5** | Migration edge-case and recovery tests | Resolved | Added 8 tests in repair suite: rollback on injected error, idempotent repeat upgrade, fresh/v2 upgrade, interrupted table recovery, future schema rejection, FK integrity/orphan preservation, pre-existing indexes preservation, concurrent competing writers. |
| **F6** | Runner exit code preservation | Resolved | In `v2_turns.py`, preserved genuine runner exit code `exit_code=exit_code` on non-zero exit turns. |
| **F7** | Guarded observation recording & artifact preservation | Resolved | Guarded `record_review_mutation_observation` in `v2_turns.py` to write `{attempt_id}.observation.json` and `{attempt_id}.observation_indexing_failure.json`, appending limitations without crashing transport. |
| **F8** | Sequence resolution & attempt lookup | Resolved | Fixed `record_review_mutation_observation` to look up sequence by `attempt_id` when present, otherwise compute `MAX(sequence) + 1`; set `sequence=curr_attempt_number - 1` in `v2_turns.py`. |
| **F9** | Go mirror observation struct completeness | Resolved | Added `Sequence`, `PathsComplete`, `Detail`, `Transport`, `Paths`, `Code` to `evidence.ReviewMutationObservation`, updated API manifest and adapter fixtures. |
| **F10** | Go end-to-end Python observer validation | Resolved | Added `TestReviewMutation_ActualPythonObserverOutputs` in `evidence/evidence_test.go` generating real Python observer output across 11 scenarios with Go validation. |
| **F11** | Prompt delivery & policy provenance tests | Resolved | Added `test_prompt_delivery_into_work_and_closeout_prompts` and `test_policy_provenance_per_source_resolved_mode_and_idempotency`. |
| **F12** | Migration runbook accuracy | Resolved | Updated runbook with `sqlite3 .backup` for WAL mode, `limitations_json` column name, FK regime, and dual index verification. |
| **F13** | Schema v4 foreign keys and index preservation | Resolved | Set `PRAGMA foreign_keys = OFF;` during rebuild in `migrate_schema_v4`, create stub runs for orphans, preserve pre-existing indexes, verify with `PRAGMA foreign_key_check;`. |
| **F14** | Marker swallow removal | Resolved | Removed swallowed exceptions on marker operations in `persistence.py`. |
| **F15** | Unreviewable receipt disqualifies freshness | Resolved | In `v2_turns.py`, set `work_review_receipt_valid = work_review_outcome not in ("unreviewable", "")`. |
| **F16** | Latent NameError in review_binding.py | Resolved | Imported `Mapping` from `collections.abc` in `review_binding.py`. |
| **F17** | Cohesive receipts, manifests, and documentation | Resolved | Synchronized qualification receipts, manifest, runbooks, and status records with exact counts. |
| **F18** | Complete execution and raw test logs | Resolved | Captured full foreground test execution log in `qualification/raw_test_execution_log.txt`. |

### Roadmap Requirements (R1–R6)

- **R1 (Upgrade-Safe SQLite Evolution)**: Schema bumped to version 4 with transactional table reconstruction under `BEGIN IMMEDIATE`, monotonic sequence allocation, legacy row preservation, and compatibility verification before execution.
- **R2 (Attempt-Centric Observability)**: `attempt_id`, `binding_id`, `attempt_number`, `policy_generation`, `limitations_json`, and raw output artifacts recorded per turn.
- **R3 (Strict Separation of Drift and Unavailability)**: Unavailability flags recorded distinctly without corrupting drift booleans; evaluate directly to `ACTION_BLOCKED`.
- **R4 (Truthful Final Candidate Freshness)**: 4-way tree hash matching, positive work review role/subject verification, structured receipt requirement, and rejection of all unavailabilities, limitations, and allow-mode drift.
- **R5 (Cross-Language Synchronization)**: Go evidence package, JACA consumer fixtures, and conformance test vectors updated and verified 100%.
- **R6 (Prelaunch Suffix-Resume & Policy Hardening)**: Prelaunch DB shape verification, suffix-resume rejection, CLI inspect-policy probe, and closed root keys.

---

## 5. Explicit Not-Run Boundaries

Per governing authority and strict read-only git posture:
- **No Git Commit, Push, or Branching**: Dispatcher owns finalization and Git publication under `commit-local`. No `git add`, `git commit`, `git push`, `git checkout`, or `git reset` commands executed.
- **Primary Commit Placeholder**: `__APG160B_FINAL_COMMIT__` retained in closeout operations records for dispatcher substitution.
