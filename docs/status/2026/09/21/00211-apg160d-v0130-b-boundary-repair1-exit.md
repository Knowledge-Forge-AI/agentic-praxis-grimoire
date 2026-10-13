# APG160D — v0.13.0 Review-Policy Boundary Repair 1 Exit

Phase ID: `APG160D`
Exit ID: `Exit 00211`
Roadmap Milestone: `V0130-B-BOUNDARY-REPAIR1`
Governing Decisions: [ADR 0070](../../../../adr/2026/09/0070-configurable-review-stage-mutation-policy.md), [ADR 0074](../../../../adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md)
Exit Target: `V0130_B_BOUNDARY_REPAIR_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **qualified checkpoint candidate** (bounded boundary repairs D1–D4 implemented and qualified; produced candidate tree verified foreground for dispatcher-owned work review and manager acceptance)
- **Milestone Outcome**: `V0130_B_BOUNDARY_REPAIR_QUALIFIED`
- **Execution Boundary**: Dispatcher implementation across persistence (`persistence.py`), review drift and policy evaluation (`review_drift.py`), qualification tests (`test_agent_phase_review_mutation_repair.py`, `test_agent_phase_review_mutation_policy.py`), and documentation records (`docs/status/`). Finalization is strictly `checkpoint` under `gemini_flash_sub` mode; dispatcher owns review orchestration, stage transitions, and Git publication. No agent Git mutation executed.

---

## 2. Core Delivery Summary (Clusters D1–D4)

### 2.1 Cluster D1 — Candidate Freshness Axis Symmetry
- **Positive HEAD and Index Evidence Requirement**: Enforced that `derive_final_candidate_freshness` strictly requires positive, non-empty expected and observed evidence for *both* HEAD and index axes (`expected_head`, `observed_head`, `expected_index`, `observed_index`).
- **Symmetric Schema Enforcement**: Applied symmetric validation across both `ReviewObservation` instances and `Mapping` dictionary inputs. Observations lacking either axis fail closed (`False`).
- **Characterized Explicit Absence**: Explicit characterized absence (e.g., `{"present": False}`) is recognized as valid structural evidence, whereas missing fields or `None` values are rejected.

### 2.2 Cluster D2 — Transaction Boundary Integrity in Schema Migration
- **Active Caller Transaction Rejection**: Fixed transaction ownership in public `migrate_schema(conn)` by explicitly probing `conn.in_transaction` prior to executing any DDL or DML statements. Active caller transactions are rejected with `PersistenceError("active caller transaction detected; migrate_schema refuses execution while a transaction is active")`, preventing unintended auto-commits of caller work.
- **Lower Helper Preservation**: Preserved `SAVEPOINT` semantics in lower-level migration helpers (`migrate_schema_v4`, `migrate_schema_v5`) to permit coordinated nested migrations within managed transactions.
- **Idle Open Safety**: Ensured ordinary `open_dispatcher_db` calls on idle connections continue to migrate schemas cleanly to current `SCHEMA_VERSION = 5`.

### 2.3 Cluster D3 — SQLite Migration Preservation and Shape Validation
- **D3.1 Deduplicated Custom Index Recreation**: Tracked recreated index names (`recreated_indexes: set[str]`) during `migrate_schema_v5` table recreation. Captured pre-existing indexes from `sqlite_master` are recreated directly from their original SQL exactly once, retaining custom multi-column and UNIQUE semantics while suppressing duplicate creation of standard indexes.
- **D3.2 Pre-Destructive Unique Constraint Rejection**: Probed `PRAGMA index_list` for table-declared `UNIQUE(...)` constraints (`origin == 'u'`) on both `review_mutation_observations` and `review_mutation_policies` before any table drops or data copying. Databases with unsupported table-level UNIQUE constraints are rejected immediately with `PersistenceError`, keeping the existing schema and data intact.
- **D3.3 Split Multi-Statement Table Creation**: Replaced compound multi-statement `conn.execute()` in the missing table fallback branch of `migrate_schema_v5` with discrete single-statement calls for table creation and each index creation.
- **D3.4 Strict V5 Shape Validation and Future Version Rejection**: Hardened `check_dispatcher_db_compatibility` to validate the presence, primary keys (`['run_id', 'source_type']`), and column nullability of `review_mutation_policies`, `review_mutation_observations`, and both legacy quarantine tables via unified `REQUIRED_OBSERVATION_COLUMNS` shape definitions. Added strict pre-checks in both `check_dispatcher_db_compatibility` and `migrate_schema` to refuse future schema versions (`> SCHEMA_VERSION`) with `PersistenceError`.

### 2.4 Cluster D4 — Status and Governance Reconciliation
- **APG160C Terminal Record Update**: Updated Exit 00210 to reflect APG160C as completed semantic work with blocked commit-local finalization (`COMMIT_MESSAGE_MISSING`) and no commit.
- **APG160B Speculative Claim Removal**: Removed the speculative "candidate mismatch" claim from Exit 00209 disposition text.
- **APG160D Exit Allocation**: Allocated next available exit `00211` for APG160D as a qualified checkpoint candidate pending manager acceptance.
- **Status Index Synchronization**: Indexed Exit 00211 in `docs/status/README.md` and verified record identity cleanly via `bin/apg-check-record-identity`.

---

## 3. Verification and Qualification Summary

| Check / Suite | Scope | Result | Details |
|---|---|---|---|
| `testing/reproduce_manager_cases.py` | 14 test cases | **PASS** (14/14) | All defect reproductions and controls pass. |
| `test_agent_phase_review_mutation_repair.py` | Repair regressions | **PASS** (37/37) | D1–D3 regression suites, transaction boundaries, index deduplication, shape checks (36 passed, 1 host snapshot skipped when env unset in produce; 37 passed in revise_close). |
| `test_agent_phase_review_mutation_policy.py` | Policy enforcement | **PASS** (39/39) | Axis completeness, policy evaluation, allow/deny/warn modes. |
| `test_agent_phase_review_immutability.py` | Immutability & drift | **PASS** (36/36) | Immutability, drift retention, candidate freshness. |
| `test_cross_language_conformance.py` | Conformance vectors | **PASS** (6/6) | Conformance vectors, Go DTO parity, unavailability flags. |
| `test_agent_phase_lifecycle_dispatch.py` | Lifecycle & dispatch | **PASS** (41/41) | Lifecycle turns, prelaunch validation, result projection. |
| `go test -count=1 ./...` | 21 Go packages | **PASS** | 19 packages with tests passed, 2 packages without test files; zero cache. |
| `go vet ./...` | Go static analysis | **PASS** | Clean; zero vet diagnostics. |
| `bin/apg-check-skill-library` | Canonical skill catalog | **PASS** | 45 canonical skills, 45 catalog rows, 45 projections. |
| `bin/apg-check-roadmap-closure` | Legacy roadmap closure | **PASS** | 55 terminal rows, 0 open rows; zero backlog qualified. |
| `bin/apg-check-record-identity` | Phase & record identity | **PASS** | 74 ADRs, 209 exits, 209 phase IDs; next exit 00212; next ADR 0075. |

---

## 4. Explicit Not-Run Boundaries and Residual Limitations

Per governing authority and strict read-only git posture:
- **No Git Commit, Push, or Branching**: Dispatcher owns finalization and Git publication under `checkpoint`. No `git add`, `git commit`, `git push`, `git checkout`, or `git reset` commands executed.
- **Shared Host Database**: No migrations executed on live shared controller database (`~/.apgr/state/dispatcher.sqlite3`); all migrations qualified in disposable test environments.
- **Dispatcher Review**: Dispatcher owns reviewer selection and post-work verification.
- **Known Pre-existing Limitation**: In `migrate_schema_v5`, a legacy database bearing a custom index referencing a column absent from the v5 schema fails migration during index recreation; rollback safely preserves schema and rows intact, but such custom shapes cannot be upgraded without schema alignment (outside D3 scope).
- **Candidate Tree Identity Separation**: The produce-stage tested candidate snapshot tree (`858d8af076dc6da193f250c7f3f6339ee133cd4b`) and the final revisor-closed candidate tree are separately identified in the qualification receipt and closeout response.

---

## 5. Outcome Addendum: Manager B Acceptance

- **Acceptance Status**: **ACCEPTED** by Manager B under local finish commit `bf6776a4a7bbfb7b66b2d6343ab59f96d6b1d680` (`APG160D-LOCAL-FINISH2`).
- **Milestone Disposition**: `V0130-B` is fully closed and qualified for local development integration.
- **Interrupted Lifecycle**: The native APG160D run remained interrupted in `revise_close` without a validated final provider response or completed checkpoint; the separate manager-controlled finalization created the commit rather than reconstructing that missing lifecycle.
- **Carried Qualification Baseline**: 159 tests passed, 1 skip (optional host snapshot lane), with the accepted exact-whitespace-readback exit 2 exception (for four accepted EOF blank lines cleaned up during C).
- **Handoff Target**: Program advances to Milestone `V0130-C` (Phase `APG161`, Exit `00212`).
