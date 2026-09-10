# APG145 — Hosted CI Repair and Staging Correction Exit

Phase ID: `APG145`

## Status

Disposition: **amend**. Exit 00190 is allocated to APG145 without renumbering or substitution.
Outcome: `V0110_HOSTED_CI_REPAIR_PREPARED` (local readiness).

Accounting remains 55 inherited / 55 terminal / zero OPEN / zero invalid (45 canonical skills: 14 stable / 31 provisional; six active CSS/JS debts; description ceiling 11,507 bytes).

## Hosted CI Failure Analysis and Remediation (PR #1 Run 34796052087)

Investigation of the 7 failed jobs and 1 skipped job in public PR #1 (`staging -> main`) run `34796052087` identified distinct root causes across toolchain bootstrap, environment preparation, platform prerequisites, SARIF schema interpretation, source code security, matrix receipt reporting, and release operator workflows. The remediation incorporates 9 independent plan-review and work-review findings, while deliberately reversing advisory finding E2 (which proposed treating `toolComponent.index == -1` as driver) to adhere strictly to OASIS SARIF 2.1.0 §§3.7.4, 3.54.2–3.54.5 component resolution:

1. **R1 (Static Analysis Bootstrap Pin Fix)**:
   - Root Cause: Job `static-analysis-and-audit` failed during tool installation: pip reported an unsatisfiable dependency set between explicit pin `tomli==2.0.1` and `pip-audit 2.10.1` (`tomli>=2.2.1`), while `semgrep 1.174.0` required `tomli~=2.4.0`.
   - Resolution: Pinned `tomli==2.4.1` in `tools/ci/bootstrap_static.sh` and synchronized `CI_REQUIREMENTS` in `tools/ci/dependency_inventory.py`. Verified pin and compatibility assertions in `src/test/unit/python/agentic-praxis-grimoire/tools/ci/pre_review_checks.unit.test.py` (`test_bootstrap_static_pins_and_tomli_compatibility`) and `dependency_inventory.unit.test.py`.

2. **R2 (Package Qualification Directory Preparation & Hosted Boundary)**:
   - Root Cause: Job `package-qualification` failed because directory `python-work` was missing prior to wheel qualification.
   - Resolution: Added `"$pkg_root/python-work"` directory creation to `tools/ci/qualify_packages.sh`. Verified directory assertions and clean-root execution to builder boundary in `src/test/unit/python/agentic-praxis-grimoire/tools/ci/pre_review_checks.unit.test.py` (`test_qualify_packages_prepares_python_work_root` and `test_qualify_packages_clean_root_execution_to_builder_boundary`). Local macOS runner preconditions verified; full Linux manylinux wheel packaging and Syft/Grype deliverable vulnerability scans are explicitly hosted-pending acceptance checks for the subsequent hosted run.

3. **R3 (macOS Go Preflight Diagnostic Capture & Toolchain Provisioning)**:
   - Root Cause: Job `unit-integration (macos-15)` failed during `bin/apg-test policy` preflight because `_embedded_corpus_failure` in `libexec/apg_skill_library_check.py` mapped any nonzero exit of `skills verify-corpus` to corpus mismatch and dropped child stderr, while the `macos-15` runner lacked Go in its default PATH (identified as a runner provisioning gap and plausible root explanation).
   - Resolution: Added pinned `actions/setup-go@b7ad1dad31e06c5925ef5d2fc7ad053ef454303e` (`go-version: 1.25.14`) to `unit-integration` in `.github/workflows/public-pr.yml`. Updated `libexec/apg_skill_library_check.py` to capture child stderr/stdout up to 512 bytes and differentiate missing Go toolchain / execution prerequisites from genuine corpus mismatch. Verified across 110 passing unit tests in `src/test/unit/python/agentic-praxis-grimoire/libexec/apg_skill_library_check.unit.test.py`.

4. **R4 (CodeQL SARIF Tool Extension Support & Evidence Replay)**:
   - Root Cause: Job `codeql-policy` failed evaluating uploaded SARIF reports because query rules provided via tool extensions were indexed through `toolComponentReference` (by index, name, or guid) and `reportingDescriptorReference`, rather than driver rules.
   - Resolution: Updated `tools/ci/codeql_policy.py` to conform to OASIS SARIF 2.1.0 §§3.7.4, 3.54.2–3.54.5 component lookup order: non-negative extension index -> GUID lookup across driver and extensions -> driver fallback. Rejects negative indexes (including `-1`) per §3.54.4; the advisory recommendation in finding E2 to treat `-1` as the driver component was deliberately reversed because §3.54.4 permits only non-negative integers. Name is treated strictly as agreement metadata. Verified across 28 unit tests in `src/test/unit/python/agentic-praxis-grimoire/tools/ci/codeql_policy.unit.test.py`.
   - Evidence Replay: Replayed the 3 downloaded SARIF artifacts from PR #1 run `34796052087` evidence:
     - `go`: exit 1 (policy verdict), 0 structural errors (`errors: []`), 1 blocking finding (severity 8.1).
     - `javascript-typescript`: exit 1, 0 structural errors, 8 findings (7 blocking, 1 Medium).
     - `python`: exit 1, 0 structural errors, 7 findings (7 blocking).
     - Preserves all 16 findings (15 blocking, 1 Medium) with 0 structural errors, confirming SARIF ingestion correctness. Formal disposition: 15 blocking findings remain open pending fresh hosted CodeQL analysis; 1 Medium finding (5.0 score in runner.mjs worker postMessage) is accepted with documented justification.

5. **R5 (Source Vulnerability Remediation)**:
   - Remediation in `internal/cli/skills.go`: Removed unnecessary unchecked capacity addition `+64` in line 257 while preserving byte parity and error behavior.
   - Remediation in `src/test/fixtures/apg123-browser-ui/runner.mjs`:
     - TOCTOU file race resolved using descriptor-based `fs.openSync(safeFilePath, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW)` + `fs.fstatSync(fd).isFile()` + `fs.readFileSync(fd)` + `fs.closeSync(fd)` with prefix checking.
     - Origin reflection eliminated by strictly binding CORS responses to `primaryOrigin` across 6 endpoints; added `primaryOrigin` type and non-empty string validation to `startSecondaryServer`.
     - Worker postMessage: Documented rationale for `worker.js:1` (MessageEvent.origin is standard and empty string for DedicatedWorker parent communication; score 5.0 Medium is below the 7.0 blocking threshold).
   - Remediation in Python test suites: Adjusted permission constants to `0o700` for git executable modes (`100755`), `0o600` for non-executable files (`100644`), `0o710` for non-0700 directory checks, and removed `mode: int = 0o777` defaults from mock opens forwarding `*args, **kwargs`.

6. **R6 (Matrix Receipts & Prescribed Artifacts)**:
   - Root Cause: CI steps emitting receipts via `release/ci/matrix_receipts.py emit` on job failure crashed with unhandled `ValueError` when expected artifacts were not produced, and sibling upload-artifact steps with `if: always()` failed due to `if-no-files-found: error`.
   - Resolution: Defined `PRESCRIBED_JOB_ARTIFACTS` for all 12 matrix member jobs in `release/ci/matrix_receipts.py`. Allowed missing `--artifact` arguments on failed jobs to emit honest failure receipts recording `unavailable_artifacts`. Updated `verify_matrix` to enforce that success receipts contain all prescribed artifacts and explicitly reject success receipts containing non-empty or malformed `unavailable_artifacts`. Changed `if-no-files-found` from `error` to `warn` on always-run evidence upload steps in `.github/workflows/public-pr.yml` to prevent artifact absence from causing false secondary failures. Verified across 17 unit tests in `matrix_receipts.unit.test.py`.

7. **R7 (Stage Operator, Public Release Candidate, & ADR 0057)**:
   - Updated ADR 0057 (`docs/adr/2026/09/0057-public-staging-pr-release-procedure.md`) to define linear staging correction commit discipline.
   - Added `--update`, `--expected-staging-parent`, `--expected-subject`, and `--expected-pr` modes to `private/releases/v0.11.0/stage_operator.py`. Enforced `--expected-pr` in CLI when `--update`; enforced non-truthy `state` check (`OPEN`), complete `mergedAt` check (must be `None`), `merged is not True`, `headRefOid` matching staging parent or candidate commit, re-verified in immediate pre-push check and post-push readback, and verified partial receipt retention on staging reuse and readback failure across 38 hermetic unit tests in `private/releases/v0.11.0/test_stage_operator.py`.
   - Updated `libexec/apg_public_release.py` (`build_untagged_candidate`, `check_candidate`, `check_untagged_candidate`) and CLI to support linear staging correction commits descending from staging parent `cd525f33ba2527862670d34d01fbdfb5f267b66c` with public base ancestry `250ce73a...`, enforcing staging branch, correction parent requirement, and subject validation. Verified across 89 unit tests in `src/test/unit/python/agentic-praxis-grimoire/libexec/apg_public_release.unit.test.py` (including 9 dedicated tests in `TestStagingCorrectionMode`).

## Preservation, Local Verification, and External Status

All 55 inherited decisions, 45 canonical skills (14 stable / 31 provisional), six active CSS/JS debts, and the 11,507-byte description ceiling remain intact.

Existing public PR #1 (`staging -> main`) and staging head `cd525f33ba2527862670d34d01fbdfb5f267b66c` are preserved. No new PR is created, no force-push is performed, no Git history is reset, no refs are deleted, no tags are created, and no fixture cleanup is executed.

Verification status distinguishes:
1. Prepared source and fixture remediations across R1–R7;
2. Focused local test suite passes (including unit, integration, and policy checks);
3. Initial candidate verification failure under ambient Python missing runtime environment variables (exit 1, 105 failed, 5,065 passed);
4. Maintained candidate qualification under the pinned CI runtime with complete diagnostic logging;
5. Hosted-pending acceptance checks (Linux-native wheel qualification, Syft/Grype deliverable scans, and fresh hosted CodeQL analysis).

External CI status:
- `hosted_pr_run_1: failed` (PR #1 run `34796052087`: 5 success, 7 failure, 1 skipped; preserved as historical record, must not be re-run).
- `correction_hosted_validation: pending` (awaits operator fast-forward push to update PR #1, triggering a new `pull_request/synchronize` workflow run).
- `public_release: not_started`.

This dispatch performs no Git publication or remote mutations. Dispatcher stage owns Git publication under `--finalization publish`. Attended staging update, PR review, squash merge, tagging, and package release await separate authorization.
