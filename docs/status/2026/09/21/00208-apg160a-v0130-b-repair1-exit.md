# APG160A — v0.13.0 Review-Policy Persistence Upgrade Repair 1 Exit

Phase ID: `APG160A`
Exit ID: `Exit 00208`
Roadmap Milestone: `V0130-B-REPAIR1`
Governing Decisions: [ADR 0070](../../../../adr/2026/09/0070-configurable-review-stage-mutation-policy.md)
Exit Target: `V0130_B_REVIEW_POLICY_UPGRADE_REPAIR_FAILED`

---

## 1. Status and Disposition

- **Disposition**: **failed** (terminal failure at planner observation due to legacy v3 schema incompatibility without fabricated receipts)
- **Milestone Outcome**: `V0130_B_REVIEW_POLICY_UPGRADE_REPAIR_FAILED`
- **Execution Boundary**: Initial launch of APG160A corrective phase. Phase terminated during planner execution after producing planning stdout, before plan candidate handoff or Git publication.

---

## 2. Terminal Failure Analysis

### 2.1 Cause of Failure
During the execution of phase APG160A, the dispatcher attempted to record an observation into the existing dispatcher SQLite database using the schema updated in APG160.
The target database was an unmigrated legacy v3 database containing migrations `[1, 2, 3]` with a two-column primary key `(run_id, stage)` and lacking the `sequence` column expected by the new insertion query:
```text
sqlite3.OperationalError: no such column: sequence
```

### 2.2 Failure Confinement
- The failure occurred at the boundary of recording the planner review observation.
- The phase halted cleanly without corrupting the host database.
- Zero plan candidates were handed off or certified.
- No git commits, tags, or branches were created.
- In accordance with APGR integrity doctrine, no synthetic or fabricated receipts were manufactured to mask the failure.

---

## 3. Corrective Disposition and Hand-off to APG160B

The failure demonstrated that runtime schema assumptions without transactional migration or compatibility checks against real host databases risk catastrophic launch failures.
The operator directed that APG160A not be resumed or rerun, and authorized the subsequent corrective phase:
- **Successor Phase**: `APG160B` (`V0130-B-REPAIR2`)
- **Required Remediation**:
  1. Transactional schema migration to v4 handling pre-v4 databases with legacy row preservation (`attempt_id = NULL`, limitations metadata).
  2. Prelaunch database compatibility checking.
  3. Immutable attempt-scoped review observations with explicit sequence numbers.
  4. Strict candidate freshness validation requiring 4-way tree hash equivalence and honest receipt checks.
