# Public release qualification traceability

The public projection validates every public code owner below and retains an explicit
disposition for regression tests exercised only during private release preparation.
Public validation does not claim those excluded operator tests ran in hosted CI.
Full development validation continues to require every original owner, fixture, and command.

Public mode is selected explicitly with `--public-projection` in the hosted static stack.
Deleting private inputs does not change the default full validation mode.

## REG-R1

Static Analysis Bootstrap Dependency Isolation

Disposition: private qualification test; public traceability retained.

Public owner: [`tools/ci/bootstrap_static.sh`](../../tools/ci/bootstrap_static.sh).

## REG-R2

Clean-Root Package Qualification Directory Preparation

Disposition: private qualification test; public traceability retained.

Public owner: [`tools/ci/qualify_packages.sh`](../../tools/ci/qualify_packages.sh).

## REG-R3

Go Toolchain Preflight and Diagnostic Capture on macOS Runners

Disposition: private qualification test; public traceability retained.

Public owner: [`libexec/apg_skill_topology.py`](../../libexec/apg_skill_topology.py).

## REG-R4

OASIS SARIF 2.1.0 Component Resolution

Disposition: private qualification test; public traceability retained.

Public owner: [`tools/ci/codeql_policy.py`](../../tools/ci/codeql_policy.py).

## REG-R5

Source Vulnerability and Permission Defenses

Disposition: private qualification test; public traceability retained.

Public owner: [`internal/cli/skills.go`](../../internal/cli/skills.go).

## REG-R6

Matrix Receipt Resilience and Honest Failure Reporting

Disposition: private qualification test; public traceability retained.

Public owner: [`release/ci/matrix_receipts.py`](../../release/ci/matrix_receipts.py).

## REG-R7

Linear Staging Correction Discipline

Disposition: private qualification test; public traceability retained.

Public owner: [`libexec/apg_staging_correction.py`](../../libexec/apg_staging_correction.py).

## REG-R8

Static File Length Policy Enforcement

Disposition: private qualification test; public traceability retained.

Public owner: [`tools/ci/file_length_policy.py`](../../tools/ci/file_length_policy.py).

## REG-R9

Cohesive Extraction Discipline

Disposition: private qualification test; public traceability retained.

Public owner: [`libexec/apg_staging_correction.py`](../../libexec/apg_staging_correction.py).

## REG-R10

APFS Directory Rename Permissions and Playwright Cleanup

Disposition: private qualification test; public traceability retained.

Public owner: [`src/test/fixtures/apg123-browser-ui/supervisor.spec.js`](../../src/test/fixtures/apg123-browser-ui/supervisor.spec.js).

## REG-R11

Test Coverage Enforcement (>=80%)

Disposition: private qualification test; public traceability retained.

Public owner: [`libexec/apg_test.py`](../../libexec/apg_test.py).

## REG-R12

Single-Root Operator Handoff Structure

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-R13

Govulncheck Symbol-Level Classification

Disposition: private qualification test; public traceability retained.

Public owner: [`tools/ci/pre_review_evaluation.py`](../../tools/ci/pre_review_evaluation.py).

## REG-P1

Numeric Draft Release ID Binding

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P2

Release Authority Pre-Check

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P3

PyPI OIDC Trusted Publishing Alignment

Disposition: private qualification test; public traceability retained.

Public owner: [`.github/workflows/release.yml`](../../.github/workflows/release.yml).

## REG-P4

npm Distribution State Machine

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P5

Resumable Multi-Channel Receipts

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P6

Homebrew Formula Generation, Validation, and Live Tap Baseline

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P7

Postmerge Source Proof (reconcile_postmerge.py)

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P8

Manifest and Receipt Serialization Integrity

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P9

Deterministic Release Epoch Binding

Disposition: private qualification test; public traceability retained.

Public owner: [`libexec/apg_python_distribution.py`](../../libexec/apg_python_distribution.py).

## REG-P10

merged-check Contract Stability

Disposition: private qualification test; public traceability retained.

Public owner: [`libexec/apg_public_release.py`](../../libexec/apg_public_release.py).

## REG-P11

Operator Precondition and Attestation Binding

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P12

PyPI Verification-Only Fail-Closed Path

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.

## REG-P13

Non-Destructive Host Binary Coexistence

Disposition: private qualification test; public traceability retained.

Owner: publication-excluded attended release operation.
