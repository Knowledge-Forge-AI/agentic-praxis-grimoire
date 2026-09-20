# APG160C — v0.13.0 Review-Policy Persistence Upgrade Repair 3 Exit

Phase ID: `APG160C`
Exit ID: `Exit 00210`
Roadmap Milestone: `V0130-B-REPAIR3`
Governing Decisions: [ADR 0070](../../../../adr/2026/09/0070-configurable-review-stage-mutation-policy.md), [ADR 0074](../../../../adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md)
Exit Target: `V0130_B_REVIEW_POLICY_UPGRADE_REPAIR_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **completed semantic work / blocked commit-local finalization** (bounded corrections C1–C5 implemented and qualified; finalization blocked under `commit-local` due to `COMMIT_MESSAGE_MISSING` with no commit executed; candidate tree adopted by APG160D for boundary repairs D1–D4)
- **Milestone Outcome**: `V0130_B_REVIEW_POLICY_UPGRADE_REPAIR_QUALIFIED`
- **Execution Boundary**: Dispatcher implementation across persistence (`persistence.py`), review drift and policy evaluation (`review_drift.py`), review binding (`review_binding.py`), multi-turn execution and prompt rendering (`v2_turns.py`, `v2_prompts.py`, `dispatch.py`, `resume_dispatch.py`), V2 dispatch prelaunch validation and finalization diagnostics (`v2_dispatch.py`), configuration resolution (`config_routing.py`, `cli.py`), Go evidence contracts (`evidence/observation.go`), cross-language conformance fixtures (`review_mutation_vectors.json`, `jaca_consumer/`), and comprehensive qualification suites. No agent Git mutation executed (publication owned by dispatcher under `commit-local`). Finalization blocked under `commit-local` (`COMMIT_MESSAGE_MISSING`); uncommitted candidate tree adopted by APG160D.

---

## 2. Core Delivery Summary (Clusters C1–C5)

### 2.1 Cluster C1 — Historical Migration Facts and Constraints
- **Schema Version 5 Advance**: Advanced to `SCHEMA_VERSION = 5` and implemented `migrate_schema_v5(conn)` with support for migrating from v1, v2, v3, and v4 databases.
- **Eliminated Synthesized Stub Runs**: Removed artificial insertion of synthetic execution rows (`status = 'completed'`) into `runs`.
- **Legacy Quarantine Stores**: Orphan observations and policy rows are cleanly isolated into dedicated quarantine tables (`legacy_quarantine_review_mutation_observations` and `legacy_quarantine_review_mutation_policies`) with provenance metadata (`quarantine_reason = 'orphaned_record_missing_parent_run'`) and zero execution semantics.
- **Foreign Key Validation**: Enforced pre-commit `PRAGMA foreign_key_check;` during migration. Pre-existing orphan policy rows no longer violate foreign key integrity post-migration.
- **Custom Index and Trigger Preservation**: Preserved pre-existing table triggers and custom indexes (including those matching prefix `idx_review_mutation_obs_`).
- **Caller Transaction Preservation**: Removed unconditional `conn.isolation_level = None`. Migration and observation persistence dynamically use `SAVEPOINT` when `conn.in_transaction` is active (preserving caller uncommitted writes and rollback capability) and `BEGIN IMMEDIATE` when standalone (preventing concurrent-writer lock escalation).
- **Nullable Policy Schema**: Added `worktree_policy` nullability verification and schema handling, accommodating legitimate configuration sources that omit review mutation settings.

### 2.2 Cluster C2 — Same-Attempt Evidence and Serialization
- **Attempt-Scoped Drift Retention**: Updated `apply_review_mutation_policy` to distinguish rechecks of the same attempt versus evaluations of new attempts. Same-attempt rechecks (`obs.attempt_id == prior_obs.get("attempt_id")`) retain cumulative drift flags and path deltas, preventing a clean recheck from erasing prior drift warnings. New attempts evaluate cleanly.
- **Limitations Field Roundtripping**: Standardized bidirectional handling between `limitations` and `observation_limitations` in `record_review_mutation_observation`, `record_review_mutation_policy_provenance`, and `get_review_mutation_observations`, ensuring zero metadata loss.
- **Truthful Candidate Freshness**: Hardened `derive_final_candidate_freshness` to require positive, runtime-owned git drift observation fields, rejecting raw dictionaries or boolean flags that lack explicit git inspection proof.

### 2.3 Cluster C3 — Durable Execution Evidence vs Optional SQL Indexing
- **Nonfatal SQLite Indexing Degradation**: Modified `v2_turns.py` post-runner handling so that a secondary SQLite observation indexing failure on an exit-zero provider does not abort transport or fail the turn.
- **Durable File-Backed Sinks**: As long as the file-backed observation sink (`.observation.json`) is intact, indexing failures are recorded as visible limitations in `attempt.observation_indexing_failure.json` and turn diagnostic metadata. Real authority violations (HEAD/index mutations) remain strictly fail-closed.

### 2.4 Cluster C4 — Complete Closeout and Finalization Diagnostics
- **V2 Finalization Diagnostic Projection**: Caught finalization errors (`FinalizationError`, `PublicationError`, `GitStateError`) are explicitly recorded in finalization state and injected into result payloads as `{"finalization_error": {"code": ..., "detail": ...}}`.
- **Truthful Publication Status**: Under `commit-local`, `publication_status` defaults strictly to `"not_attempted"`.
- **Contextual Closeout Validation**: Validated that commit-local requires a nonempty, valid commit message, ensuring that bare outcome objects are rejected and terminal handoffs include complete diagnostic context.

### 2.5 Cluster C5 — Qualification and Records
- **Manager Reproduction Parity**: 14 / 14 laboratory test cases in `reproduce_manager_cases.py` pass (all 9 historical contract failures resolved, 5 controls verified).
- **Portable Qualification**: Removed hardcoded host snapshot paths in portable test suites. Optional host snapshot runs operate via explicit local lane.
- **Attended Runbook**: Authored corrected attended migration runbook in qualification artifacts detailing quarantine semantics, transaction safety, and atomic WAL set backup/restore with closed connections.
- **Truthful Dirty Tree Identity**: Candidate trees are tracked via throwaway git index (`tree_identity`), distinguishing uncommitted candidate tree from base `HEAD^{tree}`.

---

## 3. Verification and Qualification Summary

| Check / Suite | Scope | Result | Details |
|---|---|---|---|
| `reproduce_manager_cases.py` | 14 test cases | **PASS** (14/14) | 9 historical defect reproductions resolved; 5 passing controls verified. |
| `test_agent_phase_review_mutation_repair.py` | Repair regressions | **PASS** (31/31) | Schema v5, quarantine, rollback, transaction safety, triggers, C1–C4 native tests (1 host snapshot skipped when env unset). |
| `test_agent_phase_review_mutation_policy.py` | Review mutation policy | **PASS** (39/39) | Policy enforcement, allow/deny/warn modes, provenance. |
| `test_agent_phase_review_immutability.py` | Immutability & drift | **PASS** (36/36) | Drift detection, immutability, candidate freshness. |
| `test_cross_language_conformance.py` | Python/Go conformance | **PASS** (6/6) | Conformance vectors, Go DTO parity, unavailability flags. |
| `test_agent_phase_lifecycle_dispatch.py` | Lifecycle & dispatch | **PASS** (41/41) | Lifecycle turns, prelaunch validation, result projection. |
| **Total Pytest Dispatcher Tests** | 5 suites | **PASS** (153/153) | 100% pass across all 154 dispatcher items (153 passed, 1 skipped). |
| `go test -count=1 ./...` | 21 Go packages | **PASS** (21/21) | Zero cache; 100% pass across Go domain, evidence, consumers. |
| `go vet ./...` | Go static analysis | **PASS** | Clean; zero vet diagnostics. |
| `bin/apg-check-skill-library` | Canonical skill catalog | **PASS** | 45 canonical skills, 45 catalog rows, 45 projections. |
| `bin/apg-check-roadmap-closure` | Legacy roadmap closure | **PASS** | 55 terminal rows, 0 open rows; zero backlog qualified. |
| `bin/apg-check-record-identity` | Phase & record identity | **PASS** | 74 ADRs, 208 exits, 208 phase IDs; next exit 00211; next ADR 0075. |

---

## 4. Explicit Not-Run Boundaries

Per governing authority and strict read-only git posture:
- **No Git Commit, Push, or Branching**: Dispatcher owns finalization and Git publication under `commit-local`. Finalization was blocked due to `COMMIT_MESSAGE_MISSING`. No `git add`, `git commit`, `git push`, `git checkout`, or `git reset` commands executed; no commit was generated.
- **Candidate Adoption**: The uncommitted produced candidate was preserved and adopted by APG160D for manager findings D1–D4.
- **Primary Commit Placeholder**: `__APG160C_FINAL_COMMIT__` retained in closeout operations records for dispatcher substitution.
- **Shared Host Database**: No migrations executed on live shared controller database (`~/.apgr/state/dispatcher.sqlite3`); all migrations qualified in disposable environments.
