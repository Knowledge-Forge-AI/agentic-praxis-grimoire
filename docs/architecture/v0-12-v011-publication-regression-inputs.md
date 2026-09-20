# v0.11 Publication Repair Cases as V0120-F Regression Inputs

- Status: Accepted Architecture Specification
- Target Version: APGR v0.12 (Stage `V0120-F`)
- Governing Decision: ADR 0062

## Overview

The terminal publication of APGR v0.11.0 required overcoming 13 distinct hosted CI / operator repair increments (R1–R13) across multiple runs and 12 publication-stage findings (F1–F12) during final release operator execution.

To guarantee that these edge cases never recur, this document codifies each incident into an explicit regression test specification. In stage `V0120-F`, these specifications will be implemented as automated unit and integration tests within the APGR release operator test suite.

### Identifier namespaces

Two distinct identifier namespaces appear in this document and must not be conflated:

- **`R1`–`R13`** and **`F1`–`F12`** are the *historical* identifiers owned by the
  v0.11 records: exit `00190` (`docs/status/2026/09/13/00190-apg145-*-exit.md`) for
  the repair increments, and `private/releases/v0.11.0/publication1/README.md` §1
  for the publication-stage findings. Those identifiers are immutable history and
  are never reassigned here.
- **`REG-R*`** and **`REG-P*`** are *new* regression-test identifiers owned by this
  document. `REG-R<n>` maps one-to-one onto historical `R<n>`. `REG-P<n>` is an
  independent publication-hardening test namespace that does **not** map
  positionally onto `F<n>`; §4 supplies the explicit `F1`–`F12` → `REG-P*`
  traceability table.

---

## 1. Historical Baseline Evidence (v0.11.0 Publication Proof)

The following historical values are recorded as immutable evidence from the successful v0.11.0 publication run (`publication1`):
- **Release Commit**: `58b80a1731e38afbdb98925777ed9479b5679d86`
- **Release Tree**: `eccac857cf19cc5b845c0f582be69f4549decd77`
- **Public Parent**: `250ce73a3dac71a89b8efeee9b8fe6cb0420bf18` (v0.10.0 release)
- **Release Tag**: `v0.11.0`
- **Deterministic Epoch**: `1789000000`
- **Deliverables**: 10 distinct distribution artifacts verified with SHA-256 digests.
- **Closure Accounting**: 55 inherited / 55 terminal / zero open / zero invalid.

---

## 2. Hosted CI Repair Cases (R1–R13)

### `REG-R1`: Static Analysis Bootstrap Dependency Isolation
- **Incident**: Pip reported an unsatisfiable dependency set between `tomli==2.0.1` and `pip-audit 2.10.1` (`tomli>=2.2.1`), while `semgrep 1.174.0` required `tomli~=2.4.0`.
- **Test Spec**: Ensure `tools/ci/bootstrap_static.sh` pins `tomli==2.4.1` and matches `CI_REQUIREMENTS` in `tools/ci/dependency_inventory.py`. Test that bootstrap installs cleanly in a fresh Python 3.11+ environment without dependency resolution conflicts.

### `REG-R2`: Clean-Root Package Qualification Directory Preparation
- **Incident**: Wheel qualification failed because builder scratch directory `python-work` was missing prior to execution.
- **Test Spec**: Verify that `tools/ci/qualify_packages.sh` asserts and pre-creates `"$pkg_root/python-work"` before invoking builders. Test execution from a completely clean repository root to builder boundaries.

### `REG-R3`: Go Toolchain Preflight and Diagnostic Capture on macOS Runners
- **Incident**: `macos-15` runner lacked Go in its default PATH; `libexec/apg_skill_library_check.py` dropped child stderr, masking missing toolchain errors as corpus mismatches.
- **Test Spec**: Verify `.github/workflows/public-pr.yml` contains pinned `actions/setup-go`. Verify that `libexec/apg_skill_library_check.py` captures up to 512 bytes of stderr/stdout and correctly differentiates missing toolchain prerequisites from actual skill corpus mismatches.

### `REG-R4`: OASIS SARIF 2.1.0 Component Resolution
- **Incident**: CodeQL queries via tool extensions were indexed through `toolComponentReference`. Advisory proposal to treat `-1` as driver violated OASIS SARIF §3.54.4.
- **Test Spec**: Test `tools/ci/codeql_policy.py` against OASIS SARIF 2.1.0 §§3.7.4, 3.54.2–3.54.5:
  1. Valid non-negative extension index resolves to extension component.
  2. Missing index falls back to GUID lookup across driver and extensions.
  3. Falls back to driver descriptor.
  4. Explicitly rejects negative indexes (`-1`) with a descriptive parse error.

### `REG-R5`: Source Vulnerability and Permission Defenses
- **Incident**: Unchecked capacity expansion in Go slices; TOCTOU file read race; CORS origin reflection; loose file mode defaults (`0o777`).
- **Test Spec**:
  1. `internal/cli/skills.go`: verify zero unchecked capacity additions.
  2. Browser runners: verify descriptor-based `O_NOFOLLOW` file opening and exact origin binding (rejecting reflection).
  3. Python test suites: verify permissions default to `0o700` (executables) or `0o600` (non-executables).

### `REG-R6`: Matrix Receipt Resilience and Honest Failure Reporting
- **Incident**: Failed matrix jobs crashed when emitting receipts if expected artifacts were absent, causing unhandled exceptions.
- **Test Spec**: Test `release/ci/matrix_receipts.py`:
  1. Missing artifacts on failed jobs emit valid failure receipts recording `unavailable_artifacts`.
  2. Success receipts containing non-empty `unavailable_artifacts` are strictly rejected.
  3. Workflow evidence upload steps configure `if-no-files-found: warn` instead of `error`.

### `REG-R7`: Linear Staging Correction Discipline
- **Incident**: Diverged staging branch with unverified commits required force-push or PR recreation.
- **Test Spec**: Test `private/releases/v0.11.0/stage_operator.py` update mode:
  1. Validates `--expected-staging-parent` and `--expected-pr`.
  2. Requires non-truthy state (`OPEN`), `mergedAt: null`.
  3. Verifies `headRefOid` matches staging parent or candidate commit.
  4. Preserves existing PR without force-push.

### `REG-R8/R9`: Static File Length Policy and Cohesive Extraction
- **Incident**: Adding staging correction logic exceeded configured file length limits in `apg_public_release.py` and test suites.
- **Test Spec**: Run `python3 tools/ci/file_length_policy.py`. Assert zero unallowed growth across all tracked Python source files. Verify extracted helper modules maintain strict single-responsibility cohesion.

### `REG-R10`: APFS Directory Rename Permissions and Playwright Cleanup
- **Incident**: APFS denied directory rename on read-only directories; Playwright left orphan node processes on timeout.
- **Test Spec**:
  1. Directory renames ensure write permissions (`0o700`) prior to rename.
  2. Test harness uses portable `while read` loops over Bash `mapfile`.
  3. Playwright test supervisor handles SIGTERM, drains process groups, and cleans up temporary browser profiles upon exit.

### `REG-R11`: Test Coverage Enforcement
- **Incident**: Integration branch coverage fell below 80% threshold during interim stages.
- **Test Spec**: Full CI test run enforces statement and branch coverage >= 80% across unit and integration suites, with opt-in `--export-coverage` retention.

### `REG-R12`: Single-Root Operator Handoff Structure
- **Incident**: Nested archive structures caused unbundling ambiguity during operator handoffs.
- **Test Spec**: Verify operator archives unbundle strictly into a single root folder containing all handoff manifests, scripts, and checksums.

### `REG-R13`: Govulncheck Symbol-Level Classification
- **Incident**: False positive alerts on transitively vendored test symbols.
- **Test Spec**: Govulncheck evaluation differentiates call-trace reachable symbols from unreferenced module dependencies.

---

## 3. Publication Hardening Cases (`REG-P1`–`REG-P13`)

These are the publication-channel regression themes required by ADR 0062. The
identifiers are this document's own; see §4 for the mapping back onto the
historical `F1`–`F12` publication findings.

### `REG-P1`: Numeric Draft Release ID Binding
- **Test Spec**: Operator release script must fetch and bind the GitHub numeric draft release ID before uploading release assets, preventing API race conditions and tag-name ambiguity.

### `REG-P2`: Release Authority Pre-Check
- **Test Spec**: Verify that release automation rejects any candidate whose base commit is not the immediately preceding public release tag, or whose commit subject deviates from `Release vX.Y.Z`.

### `REG-P3`: PyPI OIDC Trusted Publishing Alignment
- **Test Spec**: Verify that the GitHub Actions release workflow permissions and job environment match the configured PyPI trusted publisher claims. Supersedes the deferred v0.11 alignment proposal (`pypi-alignment-proposal.md`).

### `REG-P4`: npm Distribution State Machine
- **Test Spec**: Test npm publication poller:
  1. Correctly classifies `accepted` (job queued).
  2. Correctly classifies `processing` (metadata registered).
  3. Verifies final `published` status by downloading and checking tarball SHA-256 against the distribution manifest.
  4. A partial npm publication halts with a recoverable, resumable state rather than a silent partial success.

### `REG-P5`: Resumable Multi-Channel Receipts
- **Test Spec**: Simulate failure during channel 3 of 5. Verify that restarting the operator resumes from channel 3, verifies channels 1 and 2 without re-publishing, and emits unified final receipts.

### `REG-P6`: Homebrew Formula Generation, Validation, and Live Tap Baseline
- **Test Spec**:
  1. Verify that `generate_formula.py` outputs a valid Ruby formula with correct SHA-256 digests for `darwin/arm64`, `linux/amd64`, and `linux/arm64`. Test formula with `brew audit --strict` in CI.
  2. Verify the tap patch is computed against a freshly fetched live remote tap `main`, not a stale cached baseline, and that a before/after patch artifact is emitted.

### `REG-P7`: Postmerge Source Proof (`reconcile_postmerge.py`)
- **Test Spec**: Verify that `reconcile_postmerge.py` confirms that the squashed merge commit on `main` contains the exact projected tree of the release candidate before tagging.

### `REG-P8`: Manifest and Receipt Serialization Integrity
- **Test Spec**: Validate that all distribution manifests, provenance receipts, and binary manifests use deterministic serialization: sorted keys, a single trailing LF, and **lowercase** SHA-256 hex digests. Lowercase is the published v0.11.0 encoding (`private/releases/v0.11.0/publication1/assets/SHA256SUMS`) and is the format `sha256sum`/`shasum` emit and verify; the test must assert lowercase and must reject uppercase.

### `REG-P9`: Deterministic Release Epoch Binding
- **Test Spec**: Verify the operator resolves the epoch strictly from `RELEASE_EPOCH_BY_VERSION[<version>]` for the version under release, and fails closed rather than inheriting a prior version's epoch. Regression fixture: releasing `0.11.0` must bind `1789000000` and must reject the stale v0.10 epoch `1788996391`.

### `REG-P10`: `merged-check` Contract Stability
- **Test Spec**: Verify that maintained `bin/apg-public-release merged-check` performs no network calls to GitHub and enforces no GitHub approval or merge-commit-SHA gate, so that operator preflight cannot silently acquire a hidden remote dependency. Assert it passes on a single-parent release commit.

### `REG-P11`: Operator Precondition and Attestation Binding
- **Test Spec**:
  1. Verify the operator requires an explicit `--premerge-main` base commit, the complete set of `--required-check NAME=success` flags, and tag parity verification before tag creation.
  2. Verify that any governance waiver recorded against `--approved-pr` is preserved verbatim in the receipt rather than normalized into an unqualified approval claim.

### `REG-P12`: PyPI Verification-Only Fail-Closed Path
- **Test Spec**: Test `execute.py` PyPI handling:
  1. Byte-identical already-published files switch the channel to verification-only.
  2. A partial or mismatched already-published version halts fail-closed.
  3. Exactly the expected file count is required, with no extras tolerated.
  4. `--skip-existing` is forbidden.

### `REG-P13`: Non-Destructive Host Binary Coexistence
- **Test Spec**: Verify that release and install tooling detects a pre-existing host `apgr` on `PATH` (v0.11 observed `/run/current-system/sw/bin/apgr`), records the coexistence limitation, and never blindly unlinks, force-links, or overwrites it. Any collision must surface as an explicit operator decision, not an automatic replacement.

---

## 4. Traceability: v0.11 Publication Findings `F1`–`F12`

Authoritative source: `private/releases/v0.11.0/publication1/README.md` §1. Every
historical finding is accounted for; findings whose remedy was a one-time
authoring or scheduling act, rather than a durable code invariant, are recorded
as such instead of being given a synthetic test.

| v0.11 finding | Theme | V0120-F regression coverage |
| --- | --- | --- |
| `F1` Epoch binding | Deterministic epoch resolution; reject stale prior-version epoch | `REG-P9` |
| `F2` Maintained check reconciliation | `merged-check` performs no GitHub contact or approval gate | `REG-P10` |
| `F3` Invocation and preconditions | `--premerge-main`, required-check flags, tag parity | `REG-P11.1`, `REG-P2` |
| `F4` PR attestation | Governance waiver preserved verbatim, not normalized | `REG-P11.2` |
| `F5` Tap baseline | Refresh tap baseline from live remote; emit before/after patch | `REG-P6.2` |
| `F6` PyPI verification-only fail-closed | Idempotent republish detection, no `--skip-existing` | `REG-P12` |
| `F7` Destructive risk: pre-existing host `apgr` | Non-destructive coexistence; no blind unlink/force-link | `REG-P13` |
| `F8` Missing closeout content | Release-event outcome, Go module visibility, partial npm stop-with-recovery | `REG-P4.4` (npm recovery); remainder is closeout-record completeness, enforced by the `V0120-G` closeout contract rather than a unit test |
| `F9` Verification gap: test suite | Full release-tool suite executed before publication | `REG-R11` plus the `V0120-F` release-suite CI gate |
| `F10` Operator pattern completeness | Complete operator packet file set | `REG-R12`, `REG-P8` |
| `F11` Deliverables count consistency | Deliverable inventory reconciles to the manifest (v0.11: 8 packages + 2 metadata = 10) | `REG-P8` |
| `F12` PyPI alignment proposal | Scheduling artifact; no durable invariant of its own | Superseded by `REG-P3` |
