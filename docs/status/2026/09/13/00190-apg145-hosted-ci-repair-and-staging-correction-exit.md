# APG145 — Hosted CI Repair and Staging Correction Exit

Phase ID: `APG145`

## Status

Disposition: **amend**. Exit 00190 is allocated to APG145 without renumbering or substitution.
Outcome: `V0110_CI_REPAIR_AND_HOMEBREW_PREPARATION_QUALIFIED` (local canonical and candidate qualification passed on Candidate V8 under verified runtime; pre-review static analysis verified with 18 passed checks and 2 documented policy findings; operator archive packaged under single-root `apg145-repair8/` calling checkout operator without bypasses; Homebrew formula generation, validation, and handoff prepared for additive tap publication; Linux wheel packaging, Syft/Grype deliverable scans, fresh hosted CodeQL analysis, and actual tap publication remain hosted-pending acceptance checks).

Accounting remains 55 inherited / 55 terminal / zero OPEN / zero invalid (45 canonical skills: 14 stable / 31 provisional; six active CSS/JS debts; description ceiling 11,507 bytes).

## Hosted CI Failure Analysis and Remediation (PR #1 Runs 34796052087 and 34854230191)

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

8. **R8 (Hosted CI Run #2 Failure Analysis: Static File Length Regressions, CodeQL Permission Finding, and macOS Unit-Integration Failures)**:
   - Hosted CI Run #2 (`34854230191`) executed against staging correction head `24adef16955d6a3a3096d9765c8f09d9b6b13040`. Terminal inspection records 9 succeeded member jobs (`guard`, `package`, `closure`, `policy`, `go`, `codeql (actions)`, `codeql (go)`, `codeql (javascript-typescript)`, `sbom-and-vulnerability`), 3 failed member jobs, and aggregate `public-pr-gate` failure:
     a. `static-analysis-and-audit`: Failed `file-length` check due to 4 file-length regressions exceeding configured limits/allowances without raising allowances:
        - `libexec/apg_public_release.py`: 4,733 lines (allowance: 4,584; +149 lines).
        - `src/test/unit/python/agentic-praxis-grimoire/libexec/apg_skill_library_check.unit.test.py`: 3,128 lines (allowance: 3,104; +24 lines).
        - `libexec/apg_skill_library_check.py`: 2,343 lines (allowance: 2,330; +13 lines).
        - `src/test/unit/python/agentic-praxis-grimoire/libexec/apg_public_release.unit.test.py`: 1,599 lines (allowance: 1,282; +317 lines).
     b. `codeql-policy`: Uploaded `python` SARIF evaluation reported 1 blocking finding:
        - Query: `py/overly-permissive-file`
        - Rule ID: `py/overly-permissive-file`, Severity Score: 7.8 (blocking >= 7.0 threshold).
        - Location: `src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg124_npm.unit.test.py:137`.
        - Root cause: Test helper applied `0o710` directory permissions to verify refusal of non-0700 permissions, but granting group execution (`--x------`) triggered CodeQL's overly permissive file creation warning.
     c. `unit-integration`: Completed in 35m53s with 8 failed test nodes across 4 distinct failure mechanisms (Group A: 3 nodes, Group B: 1 node, Group C: 3 nodes, Group D: 1 node) on `macos-15`, detailed in R10.
     d. `public-pr-gate`: Failed verifying member receipts due to the 3 failed jobs.

9. **R9 (Hosted CI Run #2 Remediation: Cohesive Extractions, Restrictive Permission Testing, and Candidate V4 Qualification)**:
   - **CodeQL Finding Remediation**:
     - Updated `src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg124_npm.unit.test.py`: replaced `0o710` with owner-only restrictive mode `0o500` (`r-x------`, read and execute for owner only, strictly 0 for group and other), wrapped in `try...finally: os.chmod(bad_mode_scratch, 0o700)` to ensure clean teardown. Verifies rejection of non-0700 permissions without opening group or world permissions.
   - **Skill Library Check Extractions & Test Preservation**:
     - Extracted corpus failure formatting helper `format_embedded_corpus_failure` to `libexec/apg_skill_topology.py`.
     - Delegated formatting in `libexec/apg_skill_library_check.py`, reducing line count to 2,327 lines (allowance: 2,330).
     - Preserved test assertions and collected test coverage: extracted detailed corpus failure formatting cases into `src/test/unit/python/agentic-praxis-grimoire/libexec/apg_skill_topology.unit.test.py` (`test_format_embedded_corpus_failure`, expanding to 5 branch assertions) while retaining `test_go_embedded_corpus_verification_fails_closed` in `apg_skill_library_check.unit.test.py`; line count is 3,100 lines (allowance: 3,104) and test collections are strictly preserved (110 collected in `apg_skill_library_check.unit.test.py`, 172 in `apg_skill_topology.unit.test.py`, 282 total across modules).
     - Added comprehensive unit tests in `src/test/unit/python/agentic-praxis-grimoire/libexec/apg_skill_topology.unit.test.py` (781 lines <= 1,000 limit).
   - **Staging Correction Module Extraction**:
     - Created new cohesive library module `libexec/apg_staging_correction.py` (313 lines <= 400 limit) providing `run_checked_command`, `verify_candidate_lineage`, `build_untagged_candidate`, `check_untagged_candidate`, and `normalise_required_checks`.
     - Refactored `libexec/apg_public_release.py` to import and delegate staging correction routines, aliasing `_normalise_required_checks = normalise_required_checks`. Reduced line count to 4,420 lines (allowance: 4,584).
   - **Release Test Suite Extraction**:
     - Created dedicated test module `src/test/unit/python/agentic-praxis-grimoire/libexec/apg_staging_correction.unit.test.py` (384 lines <= 400 limit) covering `run_checked_command`, correction mode CLI and options, required checks normalization, and historical release rejection.
     - Extracted staging correction tests from `src/test/unit/python/agentic-praxis-grimoire/libexec/apg_public_release.unit.test.py`, reducing line count to 1,271 lines (allowance: 1,282).
     - Registered known `# noqa: E402` scanner suppressions for `apg_staging_correction.unit.test.py` in `tools/ci/scanner_suppressions_known.json`.
   - **Policy, Surface, and Inventory Alignment**:
     - Registered `libexec/apg_staging_correction.py` in `release/public-surface.json` (`critical_files`, `required_helpers`, and `required_test_entrypoints`).
     - Registered coverage and test entries in `testing/apg-test-inventory.json`.
     - Added `sys.path.insert(0, str(REPO_ROOT / "libexec"))` and top-level import in `private/releases/v0.11.0/stage_operator.py`.
   - **Candidate V4 Build and Qualification**:
     - Captured prospective worktree into a disposable local staging worktree.
     - Built untagged candidate commit `948b69643bc20517e54407f5bd4594ab80eaa1f2` (tree `558ca0ce43630e66fdfd23267900a8e44210cdbd`) as direct linear child of current staging tip `24adef16955d6a3a3096d9765c8f09d9b6b13040`.
     - Verified linear ancestry: `948b696` -> `24adef1` -> `cd525f3` -> `250ce73`.
     - Qualified via `bin/apg-public-release check` under the pinned runtime environment.

10. **R10 (macOS Hosted CI Failure Analysis: Classification of 8 Failure Nodes, Toolchain Provisioning, and Candidate V5 Qualification)**:
    - **Hosted CI Run #2 Unit-Integration Failure Classification**:
      Detailed diagnosis of the 8 failed test nodes in the `unit-integration` job on `macos-15` (actual split: **A=3, B=1, C=3, D=1**):
      a. *Primary Node 1 & Nested Cascades 2–3 (Group A: APFS Directory Permission Rename / Teardown [3 nodes])*:
         - Primary Node 1: `src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_repository_snapshot_contract.unit.test.py::test_cleanup_does_not_chmod_through_a_replacement_root_symlink`.
         - Nested Cascades 2–3: Exactly 2 nested runner integration tests in `src/test/int/python/agentic-praxis-grimoire/bin/apg-test.int.test.py`:
           1. `src/test/int/python/agentic-praxis-grimoire/bin/apg-test.int.test.py::test_missing_child_contribution_fixture_fails_the_real_runner`
           2. `src/test/int/python/agentic-praxis-grimoire/bin/apg-test.int.test.py::test_standalone_unit_runner_executes_real_pytest_xdist_and_coverage_boundary`
         - Mechanism: Darwin/APFS filesystem semantics require directory write permissions to rename a directory. `_populate_snapshot` in `src/test/support/apg_repository_snapshot_contract.py` (line 258) set directory permissions to `0o500` (`r-x------`). In the test body, `snapshot.rename(original_snapshot)` (executed prior to the symlink substitution, not during teardown or cleanup) failed with `PermissionError: [Errno 13] Permission denied`. The nested runner integration tests independently re-executed this failing snapshot unit test; the failure does not represent global workspace corruption from leftover unrenamed directories.
         - Resolution: Added descriptor-bound owner-only permission restoration (`os.fchmod(dir_fd, 0o700)` with `O_NOFOLLOW`) prior to `snapshot.rename()`.
      b. *Primary Node 4 (Group B: Release Workflow Shell & Mapfile Incompatibility [1 node])*:
         - Primary Node 4: `src/test/int/python/agentic-praxis-grimoire/.github/workflows/release.yml.int.test.py::test_verification_step_selects_the_exact_checked_distribution_paths`.
         - Mechanism: Step 2 of `release.yml` invoked `mapfile -t`, which is unsupported in the macOS default ambient `/bin/bash` 3.2 shell.
         - Resolution: Replaced `mapfile` with the portable `while IFS= read -r member; do ...; done < <(unzip -Z1 "$aggregate_zip")` pattern already standard across step 1 of `.github/workflows/release.yml`. Compatible with required Bash versions; uses process substitution and arrays (compatible Bash syntax, not POSIX-sh portability). Added companion positive controls under pinned Bash and macOS system `/bin/bash` 3.2, and replaced the ineffective ambient shell regression with a strict non-Bash fail-closed test with positive control.
      c. *Nodes 5–7 (Group C: Toolchain Prerequisites & Historical Validation [3 nodes])*:
         - Three historical release validation nodes:
           1. `src/test/int/python/agentic-praxis-grimoire/libexec/apg_public_release.int.test.py::APGPublicReleaseV03PolicyTests::test_historical_v0_2_six_skill_lineage_remains_valid`
           2. `src/test/int/python/agentic-praxis-grimoire/libexec/apg_public_release.int.test.py::APGPublicReleaseV03PolicyTests::test_historical_v0_3_policy_reconstructs_build_and_check`
           3. `src/test/int/python/agentic-praxis-grimoire/bin/apg-public-release.int.test.py::APGPublicReleaseTests::test_27_complete_public_base_lineage_matrix`
         - Mechanism & Root Cause Uncertainty: Toolchain prerequisite failures during candidate verification under the ambient runner environment. Nixpkgs provisioning of `bats` 1.12.0 and `bash` 5.3p3 resolved the failure, but historical certainty regarding which exact executable was missing on the hosted runner is unproven. Preserved executable basename diagnostic in `run_checked_command` in `libexec/apg_staging_correction.py`.
         - Resolution: Updated `testing/public-ci-runtime.json` with pinned Nixpkgs packages for `bats` (1.12.0) and `bash` (5.3p3). Updated `tools/ci/bootstrap_runtime.py` to materialize both binaries into `/nix/store`, export `APG_BATS` and `APG_BASH`, and emit `--path-file` for `$GITHUB_PATH`. Updated `.github/workflows/public-pr.yml` to wire `--path-file` into `$GITHUB_PATH`. Enhanced `run_checked_command` in `libexec/apg_staging_correction.py` to preserve executable basename in failure diagnostics.
      d. *Primary Node 8 (Group D: Playwright Interruption PW10 Readiness & Timeout [1 node])*:
         - Primary Node 8: `src/test/int/python/agentic-praxis-grimoire/skills/playwright-test-profile/SKILL.int.test.py::test_playwright_and_svg_real_browser_lanes` (interrupted in `src/test/fixtures/apg123-browser-ui/supervisor_runner.mjs` test PW10).
         - Mechanism: In run 2, the post-SIGINT timeout handler in old source used an 8-second sentinel (`setTimeout(() => resolve(-1), 8000)`), yielding "Expected runner interruption exit 130, got: -1" when runner shutdown exceeded 8s. Furthermore, undrained child process streams could experience OS pipe buffer backpressure deadlocks during shutdown.
         - Resolution: Separately documented: (1) explicit bounded `APG_SIGNAL_FILE` readiness handshake before SIGINT, (2) continuous stream data handlers on stdout/stderr to drain pipe buffers actively, (3) 8s→15s post-SIGINT timeout deadline (bounded headroom) alongside timeout sentinel, and (4) preservation of strict exit code 130 and process-group SIGKILL cleanup.
    - **Candidate Qualification & Verification Accounting**:
      - Captured prospective source worktree via `bin/apg-capture-source`.
      - Built untagged candidate commit descending linearly from staging parent `24adef16955d6a3a3096d9765c8f09d9b6b13040` (descending from `cd525f3` and public base `250ce73`).
      - Candidate V5 historical observation: verified `5,182 passed, 63 skipped, 6 deselected, 1,571 subtests passed in 2,213.18s` under `bin/apg-public-release check`.
      - For subsequent candidates, exact execution results belong in source-bound private/external receipts, and preparedness requires satisfying both canonical component/union coverage and candidate release check gates.
      - Confirmed 0 file-length failures and 0 allowance increases via `tools/ci/file_length_policy.py`.

11. **R11 (REPAIR7 / Candidate V7 Qualification, Coverage Gap Closure, and Incomplete Prerequisites)**:
    - **Coverage Gap Closure & Opt-In Export**:
      - Added opt-in `--export-coverage` CLI flag to `bin/apg-test` (`libexec/apg_test.py`) to retain coverage JSON artifacts inside `finally` block on both passing and failing runs without modifying default behavior.
      - Added comprehensive integration test module `src/test/int/python/agentic-praxis-grimoire/libexec/apg_staging_correction.int.test.py` (550 lines <= 1,000 limit, 21 tests) covering 75 branches in `libexec/apg_staging_correction.py` across real disposable git repositories and command validation.
      - Canonical suite run under candidate projection achieved all component and union coverage thresholds: Unit statement 11,490/13,361 (86.00% >= 80.00%), Unit branch 4,212/5,254 (80.17% >= 80.00%), Integration statement 11,536/13,361 (86.34% >= 80.00%), Integration branch 4,215/5,254 (80.22% >= 80.00%), Combined union statement 12,137/13,361 (90.84% >= 85.00%), Combined union branch 4,583/5,254 (87.23% >= 85.00%).
    - **Denominator Movement & Code Normalisation Disclosure**:
      - `libexec/apg_test.py` refactoring shifted measured statements from 13,380 to 13,361 (-19) and branches from 5,242 to 5,254 (+12).
      - Normalisation collapsed defensive guards in `_is_apgr_receipt` into boolean return expressions, consolidated 15 exception handlers across `run()` and `main()` into 3 tuple handlers, and simplified path iteration in `admit_summary_destination`. File length remains compliant at 3,018 lines (allowance: 3,034).
    - **Repeatable Qualification Adapter**:
      - Added `private/releases/v0.11.0/qualify_helper.py` to load and validate pinned CI runtime identities (`APGR_TEST_PYTHON`, `APG_BATS`, `APG_BASH`, `APG_JAVASCRIPT_NODE`), prepend toolchain to PATH, run preflight, and record command receipts with start/end timestamps, exit codes, and completed execution state.
    - **Incomplete Prerequisites & Diagnostic Handoff**:
      - Local host environment lacks pinned static analysis tools (`ruff`, `mypy`, `actionlint`, etc.).
      - Pre-review inspection identified two default ruff rule violations in the captured Candidate V7 public test module (`F401` unused `import subprocess`, `F841` unused `custom_msgs = []`). Both violations are remediated in the working tree along with return assertions.
      - Candidate rebuild against amended working tree, re-run of canonical qualification, and complete static analysis verification remain required prerequisites before staging publication.
      - Operator handoff is labelled diagnostic/not-ready; `--skip-commit-check` was removed from the attended path to ensure fail-closed execution.

12. **R12 (REPAIR8 / Candidate V8 Qualification, Opus-Review Cutover, Homebrew Preparation, and Operator Archive Remediation)**:
    - **User-Authorized Release Amendment**: Sam explicitly selected execution mode `gemini_flash_opus_sub` and added `Knowledge-Forge-AI/homebrew-tap` (observed main `8c4d59cd33aec3f4e19dc182f4238209b3d548ef`) as an additive publication target for `Formula/agentic-praxis-grimoire.rb` installing the native portable `apgr` executable.
    - **Provider Routing & Worker Ceilings**: Active route cut over to Gemini planning/work/closeout and independent Claude Opus-profile plan review and work review. Zero Codex/Luna workers across all stages.
    - **Operator Handoff Archive Remediation**: Remediated REPAIR7 packaging defect (43 paired flat and nested files where root copies retained `--skip-commit-check`). Delivered a fresh, single-root archive structure (`apg145-repair8/`) calling `stage_operator.py` directly from the private checkout, strictly enforcing linear correction mode on staging parent `24adef16955d6a3a3096d9765c8f09d9b6b13040` and PR #1 without bypasses or missing-source fallbacks.
    - **Homebrew Subsystem & Validation**: Created `private/releases/v0.11.0/homebrew_formula.py` and unit test suite `test_homebrew_formula.py` (10 tests passing). Supports `AgenticPraxisGrimoire < Formula`, maps `darwin/arm64`, `linux/amd64` (to `linux-x64`), and `linux/arm64`, rejects Intel macOS (`darwin/amd64`), and installs `bin/apgr`, `bin/apgr.binary-manifest.json`, and license files into `pkgshare`. In staging preparation, marks unreleased formula non-publishable with placeholder digests until upstream tag/release assets exist. Prepared `TAP_README_ADDITION.md` and `HOMEBREW-HANDOFF.md` for post-release tap PR.
    - **Static Analysis Suite Verification**: Executed `tools/ci/run_pre_review.py` via pinned static toolchain: 18 passed checks (including ruff with 2 accepted historical fixture observations, pyflakes, mypy, actionlint, zizmor, pip-audit, semgrep, malskanner, prompt defense, and zero generated drift) and 2 documented policy findings (`govulncheck` reachable findings in standard Go module, `betterleaks` scanning unredacted local development root).
    - **Candidate V8 Build and Canonical Qualification**: Captured source and built Candidate V8 descending linearly from `24adef16955d6a3a3096d9765c8f09d9b6b13040`. Passed `bin/apg-public-release check` (exit 0) and canonical `bin/apg-test unit-integration --public-version 0.11.0 --export-coverage <dir>` satisfying all unit, integration, and union coverage thresholds.

13. **R13 (REPAIR9 / Static Analysis Alignment, Evaluator Classification Correction, and Sanitized Review Capsule)**:
    - **Govulncheck Trace Classification Fix**: Corrected `tools/ci/pre_review_evaluation.py` against pinned v1.1.4 producer schema. Evaluator now verifies `scan_mode` and `scan_level == "symbol"`, inspects trace frames for explicit function/receiver symbols, distinguishes module-only and package-only non-reachable findings from reachable symbol findings, separates unique OSV counts from raw finding records, handles binary mode symbol presence, and handles operational failure exits fail-closed. Added comprehensive regression tests in `src/test/unit/python/agentic-praxis-grimoire/tools/ci/pre_review_evaluation.unit.test.py`.
    - **Toolchain Alignment & Static Findings Reconciliation**: Local toolchain was aligned with maintained CI pin (Go 1.25.14 vs local default 1.25.10). Replay of retained records confirmed zero vulnerabilities under CI-pinned Go 1.25.14, while older 1.25.10 observations (GO-2026-4970 in `os`, GO-2026-6088 in `encoding/xml`) are documented as resolved in the pinned runtime. Betterleaks nonsecret dispositions verified; scanner execution isolated from ephemeral test caches.
    - **Homebrew Qualification Demarcation**: Clarified documentation and caveats in `docs/distribution.md`, `docs/public-release-process.md`, and `private/releases/v0.11.0/homebrew_formula.py` to distinguish qualified native binary execution from pending Homebrew tap formula load, install, and coexistence verification. Validated package manifest and licensing assertions.
    - **Operator Handoff & Sanitized Review Capsule**: Prepared single-root `apg145-repair9/` handoff with direct `stage_operator.py` execution sequence (`readback -> remote preview -> attended update`), strict staging parent and PR #1 pins, and zero bypass flags. Assembled compact private review capsule (`private/releases/v0.11.0/repair9-review-capsule/`) containing verification receipts, static summary tables, and dispositions for independent review.

## Preservation, Local Verification, and External Status

All 55 inherited decisions, 45 canonical skills (14 stable / 31 provisional), six active CSS/JS debts, and the 11,507-byte description ceiling remain intact.

Existing public PR #1 (`staging -> main`) and staging head `24adef16955d6a3a3096d9765c8f09d9b6b13040` are preserved. No new PR is created, no force-push is performed, no Git history is reset, no refs are deleted, no tags are created, and no fixture cleanup is executed.

Verification status distinguishes:
1. Prepared source and fixture remediations across R1–R10;
2. Focused local test suite passes (including unit, integration, and policy checks);
3. Static analysis file length check passes with 0 failures across all modules;
4. Candidate qualification under the pinned CI runtime with complete diagnostic logging and exact test accounting recorded in source-bound verification receipts;
5. Hosted-pending acceptance checks (Linux-native wheel qualification, Syft/Grype deliverable scans, and fresh hosted CodeQL analysis).

External CI status:
- `hosted_pr_run_1: failed` (PR #1 run `34796052087`: 5 success, 7 failure, 1 skipped; preserved as historical record, must not be re-run).
- `hosted_pr_run_2: failed` (PR #1 run `34854230191`: 9 succeeded, 3 member jobs failed [`static-analysis` with 4 file-length regressions, `codeql (python)` with 1 permission finding, `unit-integration` with 8 failure nodes across 4 distinct mechanisms (Group A APFS directory permission rename and nested cascades [3], Group B release workflow mapfile incompatibility [1], Group C historical release validation toolchain prerequisites [3], Group D Playwright supervisor interruption timeout [1])], aggregate `public-pr-gate` failed; preserved as historical record, must not be re-run).
- `correction_hosted_validation: pending` (awaits operator fast-forward push to update PR #1, triggering a new `pull_request/synchronize` workflow run).
- `public_release: not_started`.

This dispatch performs no Git publication or remote mutations. Dispatcher stage owns Git publication under `--finalization publish`. Attended staging update, PR review, squash merge, tagging, and package release await separate authorization.
