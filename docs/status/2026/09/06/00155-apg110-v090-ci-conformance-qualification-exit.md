# APG110 v0.9.0 CI Conformance Qualification Exit

Phase ID: `APG110`

## Status

Terminal disposition: `V090_CI_CONFORMANCE_QUALIFIED`

This exit record documents completion of the APGR-owned deliverable for backlog
entry `APGR-CI-QUAL` in the v0.9 program, establishing the integration interface
and machine-readable qualification contract between Agentic Praxis Grimoire (APGR)
and Joint Agentic Command Aegis (JACA) CI.

Note on phase chronology: As recorded in the phase contract, the APG109 baseline
commit subject has no dedicated status row; the sequence advances directly from
APG108 / exit 00154 to APG110 / exit 00155 (with next ADR sequence 0053).

## Scope and Delivered Contracts

1. **Terminal Semantics and Error Classification (C1, F1, F2, F3, F4, F9)**:
   - Corrected qualification terminal semantics in `libexec/apg_test.py` to distinguish
     operational and invocation faults from test assertion failures.
     Missing prerequisites (missing `APG_TYPESCRIPT_TSC`, missing `APG_JAVASCRIPT_NODE`,
     unresolvable Node.js runtimes, missing scratch roots, invalid `APG_TEST_ARTIFACT_ROOT`,
     empty test collections) raise `InvocationError` and emit `test_status: "error", gate_status: "error"`
     with exit code 1.
   - Harness faults (unreadable or malformed manifests, missing coverage contexts, coverage JSON
     structural errors, unexpected artifact directory contents, child manifest differences,
     combine coverage errors, artifact directory identity changes, and `NodeProfileCleanupError`
     inheriting `HarnessError`) raise `HarnessError` and emit `test_status: "error", gate_status: "error"`.
   - Inventory invariant violations in `validate_inventory` raise `PolicyCheckError` and emit
     `test_status: "fail", gate_status: "fail"`.
   - In `_run_pytest`, non-assertion return codes (exit 2 `KeyboardInterrupt`, exit 4 `InvocationError`,
     exit 5 empty collection `InvocationError`, exit 3 `HarnessError`) are handled before worker
     manifest validation, ensuring unmanaged crashes or collection failures are accurately classified.
   - Entry-time freshness invalidation: pre-existing summary receipts at `--summary-file` are safely
     invalidated at command entry before test suite execution begins, closing any residual window
     for reading stale passes.
   - Coverage threshold shortfalls raise `GateShortfallError` and emit
     `test_status: "pass", gate_status: "fail"`.
   - CLI argument parsing errors exit 2 and emit sentinel `"suite": "unknown"`
     along with `test_status: "error", gate_status: "error"` when `--summary-file`
     is requested.

2. **Truthful Platform and Toolchain Audit (C2, F7, F8)**:
   - Published a comprehensive Per-Role Prerequisite & Platform Support Matrix in
     `docs/architecture/jaca-ci-handoff.md`, distinguishing `policy` requirements (Python 3.11+,
     Go 1.25+ toolchain, offline with warm cache, no compiler/Node preflight) from test runner
     suites (`unit`, `integration`, `combined`).
   - Clarified that `run()` performs whole-inventory preflight checking compiler, JavaScript
     engine, and Node profile requirements across all maintained test paths.
   - Documented that while macOS (Darwin arm64) is fully qualified, Linux (x86_64) is
     currently BLOCKED for `unit`, `integration`, and `unit-integration` suites
     because whole-inventory preflight binds Darwin arm64 Nix store digests.
     Linux `policy` qualification remains pending.
   - Updated Go prerequisite documentation to Go 1.25+ (matching `go.mod`).
   - Qualified cold-cache toolchain timings as estimates (~5–15s for Go-Python bridge
     compilation) versus measured warm-cache timing (~1.1s).
   - Documented deterministic artifact sizes under the 6-field schema, explicitly detailing the
     +1 byte per `"error"` status length expansion.

3. **Contract and Verification Coverage Completeness (C3, F5, F6, F10, F11)**:
   - **Path Confinement**: Summary file destinations are strictly confined; writing to
     `.git/` or unignored repository paths raises `InvocationError`. Refactored confinement
     tests to use disposable repository fixtures, eliminating exposure to real repo paths.
   - **Stale Receipt Invalidation**: On invocation error, test failure, drift, or at command
     entry, any pre-existing APGR v1 summary receipt at `--summary-file` is safely unlinked.
   - **Git HEAD Drift Detection**: Entry and exit HEAD commits are checked; if drift
     occurs during test execution, summary emission is aborted and any pre-existing
     summary is invalidated.
   - **Clean-Tree Truthfulness**: Documented that `source_commit` attests only to the Git
     HEAD commit identity, not clean working tree state; working tree stability and
     untracked artifact isolation remain consumer-verified via candidate tree hashes
     in JACA CI.
   - **Summary Write Durability**: Summary write failures (e.g. disk full / OSError)
     emit bounded diagnostics to `stderr` and ensure the command exits non-zero,
     never silently swallowing write errors.
   - **Maintained Conformance Fixtures**: Conformance tests in `bin/apg-test.int.test.py`
     mechanically validate that on-disk fixtures in `testing/fixtures/jaca_ci/` (`sample-summary-pass.json`,
     `sample-summary-fail.json`, `valid-apg-pr.json`, `invalid-role-pr.json`, `drift-pr.json`)
     strictly conform to schema and expected status.
   - **Executable JACA CI Conformance Model**: Integrated an in-process conformance
     test modeling JACA's `tools/ci/evidence.go` (`consumeRoleEvidence` and
     `digestEvidenceFile` pinned to `lair001/joint-agentic-command-aegis_dev@4fcc610f0b9ae8142e0ab9f7d29f75b43f187b90`),
     verifying path confinement, symlink absence, file size constraints, strict schema
     key rejection (`DisallowUnknownFields`), and SHA-256 digest computation. Noted that strict
     key rejection represents the proposed contract, following `ci-policy` rather than `rnr-unit`.

4. **Consumer Documentation Hygiene (C4, F10)**:
   - Updated `docs/v0-9-roadmap.md` entry development HEAD to `16bdf96be6c2ac217e716a110ba9bc74bc794d09`
     and recorded that APGR-local qualification conformance is completed while consumer-side
     runner registration in JACA CI remains pending.
   - Stripped all operator-local absolute file URLs across `docs/v0-9-roadmap.md` and
     `docs/architecture/jaca-ci-handoff.md`.
   - Corrected RepoMap ADR citations to explicit repository and commit provenance
     (`docs/adr/2026/08/0056-...` and `0057-...` in `lair001/repo-map_dev@7174e661`).
   - Clarified active v0.9 development checkout capabilities versus frozen v0.8.1
     release baselines and verified absence of unauthorized schema tokens.

## Verification

The following verification gates were executed and passed on Darwin arm64:
- `python3 libexec/apg_record_identity.py --format json`: 0 diagnostics, schema version 1 pass.
- Unit test suite (`libexec/apg_test.unit.test.py`): 87 passing tests covering error
  classification, summary write failure diagnostics, entry and failure stale receipt invalidation,
  disposable path confinement, git HEAD drift detection, and complete pytest exit code mappings.
- Integration test suite (`bin/apg-test.int.test.py`): 17 passing tests exercising the
  real CLI binary, worker crash reclassification (`error`/`error`), missing compiler
  prerequisites (TypeScript and JavaScript node), policy inventory violations (`fail`/`fail`),
  reused summary paths, argument parsing failures, maintained fixture conformance, and the
  JACA CI conformance model.
- Real CLI policy validation: `bin/apg-test policy --summary-file ...` executed cleanly
  with mode `0o600` artifact emission.
- Raw command logs and qualification result JSON retained in the phase outbox.

## Deferred Work and Next Authorization

- Linux platform runtime qualification remains deferred until whole-inventory Node.js
  preflight hashes can be parameterized across platforms.
- Consumer-side registration of `apg-*` roles in `lair001/joint-agentic-command-aegis_dev`
  (`tools/ci/evidence.go`, `workflow.go`, and `trustedRoleOrder`) is consumer-owned.
- Handoff deliverable `docs/architecture/jaca-ci-handoff.md` is staged for publication
  and exported to the phase outbox.
