# APG113 v0.9.0 XO Compatibility Exit

Phase ID: `APG113`

## Status

Terminal disposition: `V090_XO_COMPATIBILITY_QUALIFIED`

This exit record documents the completion of caller evidence semantics corrections and
qualification deliverables for phase `APG113` in the v0.9 development program:
1. Caller Context Propagation Correction (`XOAdapter.FootprintSkills`).
2. Component-Level Caller Footprint DTOs (`CallerComponentEvidence`, `CallerSourceReference`).
3. Source-Bound Footprint Projection Modeling (`CallerProjectionEvidence`).
4. Honest Comparison Semantics & Verified Synthetic Source Provenance.
5. Bounded AST Containment & Negative Controls across all runtime fixture files.
6. Dual-Lane Conformance Verification with Dual-Consumer Execution (`xo_consumer` & `external_consumer`).
7. Correction and supersession of archived APG112 log hashes and timings.

## Superseding Reference & Historical Record Integrity

This phase (`APG113`, Exit `00158`) formally accepts and completes `APGR-XO-COMPAT`, superseding
the initial qualification record in `00157-apg112-v090-xo-compatibility-exit.md`.

The prior phase APG112 exit record and handoff cited preliminary log timings and hashes
(`05-go-lane-a.log` at 1.238s / `8b2310865b...`; `06-go-lane-b.log` at 1.246s / `2e42642f87...`)
that drifted from the archived final logs in the run outbox ZIP. The authentic archived final
hashes and timings for APG112 are:
- `05-go-lane-a.log`: `e4b3f3ba4b99ff943c22734bccead04f4a6310b23e624c9f788fc5c5d054b051` (1.242s)
- `06-go-lane-b.log`: `e4c2cebb71f77d5b44c7bd0830bcc418b00d4dae6fc0c923ed5477d2ed517b52` (1.237s)

The historical APG112 record is preserved as dated evidence. This record (`00158`) establishes
the superseding authoritative qualification baseline.

## Deliverables and Outcomes

### 1. Caller Context Propagation
- **Defect Remediated**: `XOAdapter.FootprintSkills` previously discarded caller `ctx` during
  `skills.Resolve(context.Background(), req)`, propagating `ctx` only to the subsequent
  `skills.FootprintContext` call.
- **Remediation**: `FootprintSkills` now passes `ctx` directly to both `skills.Resolve(ctx, req)`
  and `skills.FootprintContext(ctx, req, res)`.
- **Regression Verification**:
  - `errors.Is(err, context.Canceled)` on already-cancelled context.
  - `errors.Is(err, context.DeadlineExceeded)` on already-expired deadline context.
  - Cancelled context with an invalid skill identifier: proves `skills.Resolve` evaluates
    cancellation before input validation, preventing hidden execution under `context.Background()`.
  - Context cancellation on `MeasureFootprint` verifies preservation of `footprint.ErrContextCancelled`.

### 2. Component-Level Caller Footprint DTOs
- **Defect Remediated**: `CallerFootprintEvidence` previously flattened multi-component footprint
  metrics to zero/available defaults (`TotalBytes=0`, `HasUnavailableOverhead=false`), failing to
  capture individual component availability, reasons, and overlapping bundle dimensions.
- **Remediation**:
  - Introduced `CallerComponentEvidence` capturing `Kind`, `Name`, `Unit`, `Availability`
    ("available" | "unavailable"), `Value` (`*int64`, nil when unavailable, pointer to 0 or
    positive integer when available), and `Reason`.
  - Introduced `CallerSourceReference` capturing `URI`, `Digest`, `MediaType`, `Size`.
  - Updated `CallerFootprintEvidence` to expose `Components`, `SourceReferences`, `ObservationBasis`,
    `ObservationHarness`, and `ObservationExclusions` alongside `RecordFingerprint`, `SchemaVersion`, and `MetricCount`.
  - Implemented shared translation `translateRecordToCallerEvidence` shared across both
    `FootprintSkills` and `MeasureFootprint`.
- **Fidelity Verification**:
  - Direct parity test comparing `CallerFootprintEvidence` against raw `skills.Resolve` and
    `skills.FootprintContext` results for the same structural request, asserting exact match of
    fingerprints, component counts, names, units, availability, values, reasons, observation metadata,
    exclusions (`provider_total_context`, `provider_context_fit`), and source references (including `apgr:` corpus URI).
  - JSON round-trip serialization test (`json.Marshal` / `json.Unmarshal`) proving that
    unavailable metrics (`Value == nil`) and explicit available zero values (`*Value == 0`)
    remain distinguishable across serialization without coercion, and that observation metadata
    and source references round-trip faithfully.

### 3. Source-Bound Footprint Projection Modeling
- **Defect Remediated**: `CallerProjectionEvidence` previously described "projection estimation
  for a target model", emitted invented model name `TargetModel="in-memory-projection"`, and stored
  `CanonicalSourceSize` as `ProjectedBytes`. `CanonicalSourceSize` is the original source record's
  canonical byte size, not projected length or model capacity.
- **Remediation**:
  - Redesigned `CallerProjectionEvidence` to capture factual source binding and projection facts:
    `ProjectionFingerprint`, `ProjectionSchema`, `CanonicalSourceDigest`, `CanonicalSourceSchema`,
    `CanonicalSourceSize` (retained source record size), `Fidelity`, `OmittedFields`, `Sensitivity`,
    `Retention`, and `ProjectedRecordBytes` (measuring the canonical JSON byte length of `proj.Record`).
  - Removed `TargetModel` and misleading `ProjectedBytes` fields.
- **Projection Verification**:
  - Tested nontrivial permitted omission (`[]string{"body"}`) against direct `footprint.Project`,
    asserting exact match of source digest, source schema, source size, projection fingerprint,
    projected record byte length, omitted fields, sensitivity, and retention.
  - Tested refused consequence-bearing omission (`[]string{"observation"}`) returning
    `footprint.ErrConsequenceBearingOmissionRefused`.

### 4. Honest Comparison & Verified Provenance
- **Defect Remediated**: `CallerComparisonDelta` derived an invented `Significant: abs(delta)>5`
  threshold, conflating caller policy with APGR observational facts; and synthetic source
  references bound arbitrary byte counts to mismatched digest text ("xo-adapter-source").
- **Remediation**:
  - Removed `Significant` from `CallerComparisonDelta`. Exposes `ComparisonSchema`,
    `BaselineFingerprint`, `CandidateFingerprint`, `ComponentKind`, `ComponentName`, `Delta`,
    and `Unit`.
  - Bound synthetic source references to fixed fixture payload `const fixtureSourcePayload = "xo-adapter-fixture-source-v1"`
    where digest and size (28 bytes) match the actual payload bytes.

### 5. Bounded AST Containment & Non-Authority Verification
- **Defect Remediated**: AST checks previously parsed a single fixed file with a narrow string
  converter that returned empty strings for unhandled expressions, with no negative control,
  and non-authority testing touched only one DTO with overbroad claims.
- **Remediation**:
  - `TestXOAdapterContainmentAndASTVerification` dynamically enumerates and inspects all runtime
    (non-_test) `.go` files in `testing/fixtures/xo_consumer/`, asserting zero disallowed imports
    (excluding dot/blank imports and import aliasing), zero APGR types in exported structs or method
    signatures, and failing closed on unsupported non-struct exported type forms.
  - Replaced ad-hoc type printer with standard library `go/types.ExprString`, with fail-closed
    handling on empty type strings.
  - Added `TestXOAdapterContainmentNegativeControl` verifying that intentional APGR domain type
    leaks in exported structs, signatures, or non-struct type aliases are mechanically detected.
  - Bounded dependency verification via `go list -deps` confirms absence of `os/exec`, APGR `internal/`
    or `cmd/` packages, and JACA modules.
  - `TestXOAdapterContractItem7NonAuthority` inspects all six caller DTO types via structural reflection
    against an explicit allowlist of passive observation and provenance fields, verifying absence of
    authority tokens, provider credentials, route directives, or persistence execution handles.

### 6. Dual-Lane Conformance Verification with Dual-Consumer Execution
- **Lane A (Released Baseline v0.8.1)**:
  - Verified against published module `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1`
    via standard Go proxy (`proxy.golang.org`) and checksum database (`sum.golang.org`).
  - Observed module sums:
    - `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1 h1:V71VcfVQ5/u1mii2l1IS5fzww3wy3mDTwmdN6bmFjH8=`
    - `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1/go.mod h1:SYmdFxwFtkMr7Jp1zw5dvQ/ee6bWwE6edwmQUEQ+VuU=`
  - Executed `xo_consumer` suite (7 tests): PASS with `-race` (exit 0).
  - Executed reused `external_consumer` suite (5 tests): PASS with `-race` (exit 0).
- **Lane B (Exact Development Candidate)**:
  - Verified against candidate development repository via invocation-local `replace` directive
    to the active working checkout.
  - Confirmed public library Go packages (`skills`, `footprint`, `schema`) are completely
    untouched and immutable from baseline `ac53e01`.
  - Executed `xo_consumer` suite (7 tests): PASS with `-race` (exit 0).
  - Executed reused `external_consumer` suite (5 tests): PASS with `-race` (exit 0).

## Verification Summary

All task-scoped verification commands executed cleanly in the foreground. Command logs,
module manifests, and SHA-256 digests are retained in the private APG113 phase
evidence packet and linked by its manifest. The machine-local evidence locator
is intentionally omitted from this public record.

- `bin/apg-test policy`: PASS (exit 0; retained in `01-policy.log`).
- `python libexec/apg_record_identity.py --expect-allocated APG113`: PASS (52 ADRs, 158 exits, 158 phase IDs, exit 0; retained in `02-record-identity.log`).
- `pytest apg_test.unit.test.py`: PASS (97 passed in 2.42s, exit 0; retained in `03-unit-tests.log`).
- Go Conformance Lane A (Released v0.8.1): PASS (`go vet`, `go test -v -race -count=1 ./...` for `xo_consumer` [7 tests] and `external_consumer` [5 tests], exit 0; retained in `05-go-lane-a.log`).
- Go Conformance Lane B (Development Candidate): PASS (`go vet`, `go test -v -race -count=1 ./...` for `xo_consumer` [7 tests] and `external_consumer` [5 tests], exit 0; retained in `06-go-lane-b.log`).
- `git diff --check`: PASS (clean whitespace and syntax, exit 0; retained in `07-git-diff-check.log`).
- Public Go Package Immutability: `git status --porcelain -- footprint skills schema` and `git diff --stat ac53e01 -- footprint skills schema` confirm zero modifications to public Go libraries.
- Manifest: Complete manifest linking all execution logs, source commit binding, and SHA-256 digests retained in `manifest.json`.

## Deferrals and Consumer Ownership

- **JACA Downstream Adapter Implementation**: Implementing the production JACA XO adapter in
  `xo/src/main/go` remains consumer-owned under JACA roadmap gates `JACA-APG0`, `CTX-DOCS`, and `XO-APGR1`.
  APGR qualification confers zero mutation authority over downstream repositories.

## Terminal Disposition

Disposition: `V090_XO_COMPATIBILITY_QUALIFIED`
