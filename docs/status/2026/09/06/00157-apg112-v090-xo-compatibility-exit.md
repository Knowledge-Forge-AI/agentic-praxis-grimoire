# APG112 v0.9.0 XO Compatibility Exit

Phase ID: `APG112`

## Status

Terminal disposition: `V090_XO_COMPATIBILITY_QUALIFIED`

This exit record documents the completion of qualification and remediation deliverables
for phase `APG112` in the v0.9 development program:
1. CI Receipt-Alias Carry-In Correction (`APGR-CI-QUAL` remediation).
2. APGR-Owned XO Compatibility Qualification (`APGR-XO-COMPAT`).

## Deliverables and Outcomes

### 1. Work Package 1: CI Receipt-Alias Carry-In Correction
- **Symlink Invalidation Safety**: Corrected `SummaryDestination.invalidate()` in `libexec/apg_test.py`
  so that if `self.target.is_symlink()` is true, it immediately raises `InvocationError`
  rather than unlinking, preventing modification or removal of symlink entries and preserving
  foreign files on entry.
- **Triple-Boundary Destination Evaluation**: Overhauled `admit_summary_destination()`:
  - Leaf symlinks are unconditionally refused (`cannot target a symlink`) across addressed
    entry and addressed-in-parent views before any filesystem mutation or parent directory creation.
  - Three distinct path viewpoints are evaluated:
    1. Lexical target path: `Path(os.path.normpath(str(raw_target)))`.
    2. Addressed-in-parent boundary: `lexical_target.parent.resolve() / lexical_target.name`.
    3. Resolved target path: `target.resolve()`.
  - Git repository metadata, repository roots, and directories are unconditionally refused across all views.
  - In-repo paths are verified against Git tracking (`git ls-files --error-unmatch`) and
    Git ignore rules (`git check-ignore -q`). Tracked files are refused; untracked, unignored
    repository paths are refused.
  - Probe failures, timeouts, and `OSError` exceptions fail closed safely with `InvocationError`.
- **Test Coverage**:
  - `src/test/unit/.../apg_test.unit.test.py`: Added `test_admit_summary_destination_inverse_alias_and_dual_boundary`
    testing inverse aliases in disposable clones, positive gitignored target paths, positive
    scratch paths, and fail-closed timeout handling. Unit test count: 97 passed.
  - `src/test/int/.../apg-test.int.test.py`: Added `test_inverse_alias_refused_and_preserved_in_disposable_repo`
    testing CLI invocation rejection of inverse aliases, preservation of symlink targets,
    refusal under invalid argv, and positive qualification of ignored and scratch outputs,
    guarded by `repo_state_snapshot`. Integration test count: 23 passed.

### 2. Work Package 2: APGR-XO-COMPAT Qualification
- **Caller-Owned Adapter Fixture**: Implemented `testing/fixtures/xo_consumer/` modeling an
  external caller adapter consuming APGR's public Go packages (`skills`, `footprint`, and supporting `schema`).
  - Implemented caller-owned DTOs (`CallerSkillEvidence`, `CallerFootprintEvidence`, `CallerComparisonDelta`,
    `CallerProjectionEvidence`) ensuring zero APGR domain models leak into caller signatures or fields.
  - Uses official public Go types (`skills.BundleResult`, `footprint.Record`, `schema.SHA256`, `schema.EnvelopeVersion`).
  - AST-level validation verifies:
    - Zero APGR types appear in caller signatures or struct field definitions.
    - Zero `os/exec` subprocess invocations exist in the adapter package.
    - Zero imports of APGR `internal/` or `cmd/` packages.
    - Zero imports of JACA modules (confirming JACA-APG0 non-dependency).
  - Semantic conformance validates:
    - Repeatable skill evaluation and footprint projection across calls.
    - Context cancellation propagation (`footprint.ErrContextCancelled`).
    - Sentinel error preservation and mapping (`ErrUnitMismatch`, `ErrConsequenceBearingOmissionRefused`, `skills.ErrBudgetExceeded`).
    - Supporting schema consumption (`schema.SHA256` digest calculation, `schema.EnvelopeVersion` / format verification).
    - Caller contract item 7 non-authority (caller determines execution policy; DTOs contain purely observational data).
- **Dual-Lane Verification**:
  - **Lane A (Released Baseline v0.8.1)**: Clean verification of `example.invalid/apgr-xo-consumer`
    against `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1` via standard Go module
    resolution and sumdb verification. `go mod tidy`, `go vet`, and `go test -v -race` all pass cleanly.
  - **Lane B (Exact Development Candidate)**: Disposable local `replace` verified against the active
    uncommitted development tree. `go mod tidy`, `go vet`, and `go test -v -race` all pass cleanly.
- **Handoff Documentation**: Created `docs/architecture/jaca-xo-handoff.md` providing complete interface
  control, DTO mapping rules, error envelopes, and step-by-step consumer onboarding guidance.

### 3. Documentation & Crosswalk Updates
- Indexed `docs/architecture/jaca-xo-handoff.md` in `docs/README.md`.
- Linked handoff specification in `docs/architecture/apg-jaca-integration.md`.
- Updated terminal qualification semantics in `docs/architecture/jaca-ci-handoff.md`.
- Updated `docs/v0-9-roadmap.md` lines 52–60 and backlog row 99 to reflect APGR-side qualification,
  and added Section 5 documenting the XO compatibility implementation slice.

## Verification Summary

All task-scoped verification commands executed cleanly in the foreground. Raw command logs, module manifests, execution outputs, and SHA-256 digests are retained in `.test-reports/evidence/` and the phase run outbox (`evidence/`):

- `bin/apg-test policy`: PASS (inventory, skill library, embedded corpus, and record identity checks passed in 0.47s, exit 0; retained in `01-policy.log`).
- `python libexec/apg_record_identity.py`: PASS (52 ADRs, 157 exits, 157 phase IDs, exit 0; retained in `02-record-identity.log`).
- `pytest src/test/unit/.../apg_test.unit.test.py`: PASS (97 passed in 2.70s, exit 0; retained in `03-unit-tests.log`).
- `pytest src/test/int/.../apg-test.int.test.py`: PASS (23 passed in 137.64s, exit 0; retained in `04-int-tests.log`).
- Go Conformance Lane A (Released v0.8.1): PASS (`go vet`, `go test -v -race -count=1 ./...` 6 of 6 passed in 1.238s, exit 0; retained in `05-go-lane-a.log`).
- Go Conformance Lane B (Development Candidate): PASS (`go vet`, `go test -v -race -count=1 ./...` 6 of 6 passed in 1.246s, exit 0; retained in `06-go-lane-b.log`).
- `git diff --check`: PASS (clean whitespace and syntax, exit 0; retained in `07-git-diff-check.log`).
- Manifest: Complete manifest linking all logs, source commit binding, and SHA-256 digests retained in `manifest.json`.
- Repository working tree invariance confirmed: only intended changes present, zero untracked scratch files outside gitignored `.test-reports/`.

## Deferrals and Consumer Ownership

- **JACA CI Downstream Registration**: Downstream runner registration in JACA CI (`tools/ci/evidence.go`,
  `workflow.go`, `trustedRoleOrder`) remains consumer-owned.
- **JACA XO Downstream Adapter Adoption**: Implementing the JACA-side adapter in `xo/src/main/go` remains
  consumer-owned and unstarted; APGR qualification confers no automatic mutation authority over JACA repos.

## Next Authorized Action

Pre-final dispatcher review checkpoint and stage publication.
