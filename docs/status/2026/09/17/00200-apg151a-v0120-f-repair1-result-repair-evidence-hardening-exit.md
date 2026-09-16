# APG151A — APGR V0120-F-REPAIR1 — V2 Result-Repair Evidence Fail-Closed Hardening Exit

Phase ID: `APG151A`
Exit ID: `Exit 00200`  
Governing Decision: [ADR 0062](../../../../adr/2026/09/0062-v012-release-hardening-and-conditional-nixpkgs.md)\
Entry Commit: `bb34161445bd4beda8e642553e63455d4918cf7c`  
Exit Target: `V0120_F_RESULT_REPAIR_EVIDENCE_HARDENED`  

---

## 1. Status and Disposition

- **Disposition**: **accept**
- **Milestone Outcome**: `V0120_F_RESULT_REPAIR_EVIDENCE_HARDENED`
- **Scope Delivery**: Resolved all fail-open evidence handling and synthetic repair-success defects in `libexec/agent_phase/v2_repair.py`, hardened auxiliary attempt accounting and semantic attempt lineage, enforced exact byte identity on repair artifacts, and fully qualified the dispatcher suite.
- **Strict Boundary Confirmation**:
  - Phase APG151A / V0120-F-REPAIR1 only.
  - Milestone V0120-G remains **NOT STARTED**.
  - v0.12.0 has **NOT** been tagged or published to any public channel.
  - Agent-Central remains active and supported.
  - JACA and Agent-Central have **NOT** been mutated.

---

## 2. Background and Defects Addressed

Manager post-publication review of the newly published `libexec/agent_phase/v2_repair.py` (introduced in APG151 Recovery1 via commit `bb34161`) identified three fail-closed/evidence defects and a qualification gap:
1. `record_repair_attempt()` caught every persistence exception and silently continued (`except Exception: pass`).
2. Result-repair artifact registration caught persistence exceptions and silently continued; additionally `result-repair-cwd.json` was written with formatted JSON + LF while its registered size/SHA were computed from a different unformatted serialized buffer.
3. An injected/custom repair runner returning `None` fabricated a synthetic `completed` closeout result (`commit_message: null`).
4. The complete `bin/apg-test-dispatcher -n auto` suite had not been executed against the integrated V2 repair engine after the adapter was added.

---

## 3. Implementation Summary

### A. Fail-Closed Persistence
- Removed broad `except Exception: pass` from `record_repair_attempt()` and all artifact registrations in `libexec/agent_phase/v2_repair.py`.
- Persistence failures now propagate fail-closed as typed `PersistenceError`.

### B. Exact Artifact Byte Identity
- Every repair artifact (`result-repair-cwd.json`, `result-repair.json`, `closeout.result.json`) is serialized once to canonical UTF-8 bytes with `indent=2, sort_keys=True` and a single trailing LF `\n`.
- The exact written byte buffer is passed to `record_artifact()`, ensuring `size_bytes == len(actual_bytes)` and `sha256 == sha256(actual_bytes)` unconditionally.

### C. Zero Synthetic Completion Fabrication
- Deleted the fallback that converted `runner -> None` into synthetic `completed` closeout results.
- Injected or custom runners returning `None` or unsupported shapes fail closed immediately with `FinalizationError("RESULT_REPAIR_TRANSPORT_INVALID")`.
- The failure is truthfully recorded in SQLite `invocation_attempts` as `failed` with exit code `1`.

### D. Auxiliary Attempt Accounting and Semantic Lineage Protection
- Added `attempt_kind` column (default `'semantic'`) to `invocation_attempts` table and automated migration in `init_dispatcher_db()`.
- Auxiliary repair attempts are persisted with `attempt_kind="auxiliary"`.
- `v2_turns.py` filters out auxiliary attempts when calculating `prior_attempts`, guaranteeing that retry/recovery paths derive clean semantic attempt numbers (e.g. attempt 2 rather than skipping to 3) and unpoisoned predecessor IDs.

---

## 4. Verification and Full Qualification

1. **Focused V2 Result-Repair Suite**:
   - `rtk pytest src/test/dispatcher/test_agent_phase_v2_result_repair.py` (15 passing tests covering all required regression cases).
2. **Complete Dispatcher Regression Suite**:
   - `bin/apg-test-dispatcher -n auto` executed to completion.
3. **Governance and Policy Checks**:
   - `bin/apg-check-record-identity` (PASS: 67 ADRs, 198 exits, 198 phase IDs; next exit 00201).
   - `bin/apg-check-roadmap-closure` (PASS: 55 roadmap rows terminal and valid).
   - `bin/apg-check-release-matrix` (PASS: 38 rows checked, 100% valid).
   - `tools/ci/check_generated_drift.py` (PASS).
   - `tools/ci/file_length_policy.py` (PASS).
   - `tools/ci/prompt_defense_check.py` (PASS: score 100).

Milestone V0120-G remains NOT STARTED.
