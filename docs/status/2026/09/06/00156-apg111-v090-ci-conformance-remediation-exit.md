# APG111 v0.9.0 CI Conformance Qualification Remediation Exit

Phase ID: `APG111`

## Status

Terminal disposition: `V090_CI_CONFORMANCE_QUALIFIED`

This exit record documents the completion of defect remediation and review finding
resolution for backlog deliverable `APGR-CI-QUAL` in the v0.9 program, resolving all
findings raised against the APG110 qualification interface.

## Remediated Defects and Findings

1. **R1: Receipt Lifecycle Admission Safety**:
   - Path admission (`admit_summary_destination`) strictly precedes all filesystem
     effects. Refused paths (tracked repository files, Git metadata including linked worktrees,
     repository root, directories) produce no deletions, writes, chmod modifications, or
     parent directory creations.
   - At admitted target paths, recognized APGR v1 receipts are safely invalidated at entry;
     unrelated foreign files are never deleted and raise `InvocationError`.
   - Admitted symlinks: invalidation unlinks only the symlink itself, strictly preserving
     any backing file target unmodified.
   - Guarded invalidation in `_write_admitted`: if unlinking fails during error or
     interrupt handling, a bounded diagnostic is printed to `stderr` without raising an
     unhandled exception or masking process cancellation (exit 130).

2. **R2: Error Dominance and Outcome Reduction Symmetry**:
   - Unified exception handling across component and combined union coverage blocks in `run()`:
     `InvocationError` -> `has_invocation_error`
     `HarnessError` -> `has_harness_error`
     `PolicyCheckError` -> `has_assertion_error`
     `TestAssertionError` -> `has_assertion_error`
     `GateShortfallError` -> `has_gate_error`
     Generic `ToolError` -> `has_harness_error`
   - Strict status reduction hierarchy:
     `has_invocation_error` > `has_harness_error` > `has_assertion_error` > `has_gate_error`.
   - Harness faults strictly dominate simultaneous threshold shortfalls.

3. **R3: Test Fixture Isolation & Repository State Invariance**:
   - Disposable clones (`git clone -s`) isolate intentional inventory defects and
     `.git` metadata test fixtures from the active repository checkout.
   - Uncommitted candidate code (`libexec/apg_test.py`) is copied into disposable clones
     to ensure tests exercise candidate implementations rather than committed HEAD.
   - Multithreaded concurrent invocation isolation confirmed via `ThreadPoolExecutor(max_workers=2)`.
   - `repo_state_snapshot` autouse fixture mechanically asserts Git HEAD and working-tree
     porcelain cleanliness before and after test runs.

4. **Review Finding Remediation (Findings 1–9)**:
   - Moved `.git` metadata receipt preservation test into a disposable clone (Finding 1).
   - Ensured disposable clones bind to candidate code via explicit file synchronization (Finding 2).
   - Symmetrized generic `ToolError` and `PolicyCheckError` handling across component and union paths (Finding 3).
   - Guarded `destination.invalidate()` in `_write_admitted` against escaping `InvocationError` during SIGINT (Finding 4).
   - Cleaned up dead code (`_safe_write_summary`, `_check_summary_confinement`, `_invalidate_stale_summary`) into a single `SummaryDestination` owner (Finding 5).
   - Preserved symlink backing files on invalidation (Finding 6).
   - Closed test-strength gaps: tested `_scan_early_args` directly, verified exit 5 collection without mocks, asserted HEAD drift failure and stderr diagnostic, and verified SIGINT cancellation exits 130 with nested `--basetemp` (Finding 7).
   - Updated JACA CI handoff documentation: documented `--help` non-validation contract, clarified receipt emission on path refusal, updated unit test counts to 3,418, and documented fresh per-run receipt paths (Finding 8).
   - Created this exit status record `00156-apg111-v090-ci-conformance-remediation-exit.md` (Finding 9).

## Verification Summary

- `bin/apg-test policy`: PASS (inventory, skill library, and record identity checks passed, exit 0).
- `pytest src/test/unit/python/agentic-praxis-grimoire/libexec/apg_test.unit.test.py`: PASS (96 passed, exit 0).
- `pytest src/test/int/python/agentic-praxis-grimoire/bin/apg-test.int.test.py`: PASS (22 passed, exit 0).
- `git diff --check`: PASS (clean whitespace and syntax).
- Repository working tree invariance confirmed: only intended changes present, zero untracked files.
