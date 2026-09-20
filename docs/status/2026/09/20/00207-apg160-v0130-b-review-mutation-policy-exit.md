# APG160 — v0.13.0 Review-Stage Mutation Policy Qualification Exit

Phase ID: `APG160`
Exit ID: `Exit 00207`
Roadmap Milestone: `V0130-B`
Governing Decisions: [ADR 0070](../../../../adr/2026/09/0070-configurable-review-stage-mutation-policy.md)
Exit Target: `V0130_B_REVIEW_MUTATION_POLICY_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **accept** (review-stage mutation policy implementation and qualification complete)
- **Milestone Outcome**: `V0130_B_REVIEW_MUTATION_POLICY_QUALIFIED`
- **Execution Boundary**: Dispatcher implementation across V1 (`libexec/agent_phase/`) and V2 (`libexec/agent_phase/v2_turns.py`, `v2_dispatch.py`), pure Go contracts (`evidence/policy.go`, `evidence/observation.go`), cross-language golden conformance fixtures (`testing/fixtures/conformance/review_mutation_vectors.json`, `testing/fixtures/jaca_consumer/`), and comprehensive qualification suites. No git mutation executed by agent (dispatcher owns Git publication).

---

## 2. Core Delivery Summary

### 2.1 Unified Review Drift Observer Across 3 Axes
- Drift observer implemented in `libexec/agent_phase/review_drift.py` measuring drift independently across:
  - `worktree`: Working directory content drift compared to bound candidate tree.
  - `index`: Staged index changes compared to pre-review index state.
  - `head`: Current repository HEAD commit compared to pre-review HEAD.
- Unified observation struct `ReviewObservation` emitted under schema `agent-phase-review-mutation-observation-v1`.
- Raw reviewer output (stdout/stderr) and mutation observations are preserved even when review output is malformed, with fallback transport capture.

### 2.2 Tri-State Review Mutation Policy with Shipped Default `warn`
- Worktree tri-state policy:
  - `block`: Fails review stage immediately with `READ_ONLY_STAGE_MUTATED_CANDIDATE`.
  - `warn` (shipped default in `common/dispatcher/policy.toml`): Captures drift observations, preserves immutable review subject binding, parses findings, emits downstream warnings, and enforces closer path accountability.
  - `allow`: Captures drift observations and allows surviving paths into finalization without conferring review authority.
- Four-tier policy resolution hierarchy: CLI argument (`--review-mutation-worktree`) > Project config (`.apgr/config.toml`) > Global config (`<APGR_HOME>/config.toml`) > Tracked default (`common/dispatcher/policy.toml`).
- Provenance captured in `ConfigurationProvenance` and recorded in run artifacts and SQLite database.

### 2.3 Fail-Closed Git Authority
- Modifying the Git index or moving HEAD during read-only review turns remains strictly `block` in all v0.13 modes.
- Strict and distinct diagnostic codes emitted:
  - `READ_ONLY_STAGE_MUTATED_INDEX` for index mutations.
  - `READ_ONLY_STAGE_MUTATED_HEAD` for HEAD movements.

### 2.4 Truthful Candidate Freshness and Freshness Restoration (M1)
- `final_candidate_reviewed` derived strictly from eligible independent Work Reviews:
  - Authorized work review role (`work_reviewer`, V1 `work_review` / `final_review`).
  - Reviewed candidate tree matches terminal tree (`candidate_tree == terminal_tree`).
  - Zero drift observed during the qualifying review turn (`drift_observed == false`).
  - Verified structured receipt exists.
- Plan Review never certifies work candidate freshness.
- Earlier warning history does not permanently poison candidate freshness: a subsequent eligible independent review bound to the exact final candidate restores `final_candidate_reviewed = true`.

### 2.5 Closer Path Accountability Under `warn`
- Review-window mutations that survive to closeout under `warn` require explicit closer disposition:
  - `phase_owned`: Claimed as intentional phase product.
  - `exclude_unrelated`: Excluded operator dirt.
  - `exclude_environment`: Excluded environment dirt.
- Undispositioned review-window mutations block finalization with `OWNERSHIP_CHALLENGE_OPEN`.
- Closer disposition is ownership handling, not review certification.

### 2.6 Pure Go Evidence Contracts and Conformance
- Go contracts in `evidence/policy.go` and `evidence/observation.go` with strict validation.
- Conformance test suite in `evidence/evidence_test.go` and `testing/fixtures/jaca_consumer/adapter_test.go` validating 28 cross-product matrix combinations and edge cases.
- API manifest updated in `docs/architecture/v0-12-apgr-go-api-manifest.json`.
- Python-Go cross-language equivalence verified in `src/test/dispatcher/test_cross_language_conformance.py`.

---

## 3. Verification and Checks

All qualification suites and checks verified:
1. `bin/apg-check-record-identity`: PASS (74 ADRs, 205 exits, next exit 00208 allocated).
2. `bin/apg-check-skill-library`: PASS (45 skills, 45 catalog rows, 45 projections).
3. `bin/apg-check-roadmap-closure`: PASS (0 open items, zero backlog qualified).
4. `go test ./...` and `go vet ./...`: PASS (100% across all packages including `evidence`, `jaca_consumer`, `xo_consumer`, `internal/apimanifest`).
5. `bin/apg-test-dispatcher src/test/dispatcher/test_agent_phase_review_mutation_policy.py`: PASS (39 of 39 passed).
6. `bin/apg-test-dispatcher src/test/dispatcher/test_agent_phase_review_immutability.py`: PASS (36 of 36 passed).
7. `bin/apg-test-dispatcher src/test/dispatcher/test_cross_language_conformance.py`: PASS (6 of 6 passed).
8. Core regression test suite (154 passed): `test_agent_phase_lifecycle_dispatch.py` (41), `test_agent_phase_antigravity.py` (27), `test_agent_phase_disposition_flow.py` (30), `test_agent_phase_entry_adoption_boundary.py` (27), `test_agent_phase_v2_full_execution.py` (10), `test_agent_phase_review_recovery.py` (12), `test_agent_phase_persistence_feedback.py` (6), `test_controller_generation_real_cli.py` (1).

---

## 4. Work Review Findings Disposition

All 9 advisory findings from the independent Work Review were addressed, hardened, and verified:
1. **Finding 1 (HEAD fails open on unknown observation)**: Updated `review_drift.py` so HEAD read errors record `head_observation_unavailable` limitations, mark `paths_complete=False`, and block fail-closed under `READ_ONLY_STAGE_MUTATED_HEAD`.
2. **Finding 2 (Index untruthful fact & omission drift bypass)**: Updated `review_drift.py` so failed index reads preserve `observed_index=None`, record `index_observation_unavailable`, block fail-closed under `READ_ONLY_STAGE_MUTATED_INDEX`, and prevent defaulting `expected_index = observed_index` on omission.
3. **Finding 3 (Fabricated freshness on resume)**: Updated `resume_dispatch.py` to query observations without `{}` defaults and verify structured review receipts. Updated `derive_final_candidate_freshness` to explicitly reject empty observation maps.
4. **Finding 4 (Observation immutability across retries/checks)**: Added `sequence` column and `PRIMARY KEY (run_id, stage, sequence)` to SQLite `review_mutation_observations` in schema migration v3. Drift status is retained across retries so clean follow-up observations cannot overwrite prior warned drift with `action_taken='none'`.
5. **Finding 5 (Freshness Criterion 1 role authority enforcement)**: Updated `ReviewObservation` to carry `role` and `subject_kind`. Hardened `derive_final_candidate_freshness` to strictly reject plan review stages, roles, and subjects.
6. **Finding 6 (Warn-mode closer disposition suppressing ownership challenges)**: Reordered `_reason()` in `ownership_challenge.py` so `entry_dirt_overlap` and `unclaimed_tracked_deletion` are evaluated ahead of `review_window_mutation`, preventing deletions or entry dirt from being suppressed with `exclude_environment`.
7. **Finding 7 (V2 losing raw reviewer stdout)**: Updated `v2_turns.py` to write and register raw reviewer stdout files (`plan_review.stdout.md`, `work_review.stdout.md`, `final_review.stdout.md`) immediately upon runner execution, before policy evaluation or parsing failures.
8. **Finding 8 (Go/Python DTO divergence on index fields)**: Updated `evidence/observation.go` to type `ExpectedIndex` and `ObservedIndex` as `json.RawMessage`. Updated API manifest and conformance fixtures.
9. **Finding 9 (Regression Coverage Expansion)**: Added 5 regression tests in `test_agent_phase_review_mutation_policy.py` verifying all edge cases above (bringing suite to 39 tests, all passing).

---

## 5. Hard Stop Boundary and Publication

- Agent executed zero git staging, commit, push, or branch operations (dispatcher-owned Git publication).
- `closeout.response.md` and `closeout.ops.md` prepared in the launcher evidence directory with `__APG160_FINAL_COMMIT__` placeholder.

---

## 6. Gate Status and Next Authorized Step

- `V0130_B_REVIEW_MUTATION_POLICY_QUALIFIED`: Satisfied.
- Milestone V0130-B implementation and qualification are complete.

