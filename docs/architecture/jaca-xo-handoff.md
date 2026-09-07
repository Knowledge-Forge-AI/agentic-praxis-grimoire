# JACA XO Compatibility Handoff

## 1. Purpose & Authority Boundary

This document establishes the canonical APGR-owned compatibility handoff for
downstream consumption by the Joint Agentic Command Aegis (JACA) Executive
Orchestrator (XO). It fulfills the `APGR-XO-COMPAT` deliverable in the
[v0.9 Roadmap](../v0-9-roadmap.md).

> [!IMPORTANT]
> **Boundary of Authority**: This handoff defines APGR-local library compatibility
> evidence only. It confers **no authority** to modify JACA, change JACA production
> `go.mod`, alter JACA schemas, advance JACA roadmap gates, or activate production
> imports. Downstream gates (`JACA-APG0`, `CTX-DOCS`, and `XO-APGR1`) remain strictly
> JACA-owned and require separate authorization under JACA's own governance.
> Furthermore, the caller-owned adapter fixture in `testing/fixtures/xo_consumer/`
> is an APGR-local qualification fixture, not JACA's production adapter (which
> belongs in `xo/src/main/go`), and passive DTOs are not a workflow security proof.

---

## 2. Inspected JACA Revisions & Current State

JACA contracts and source checkouts were inspected as historical campaign evidence
at the following baseline:

| Repository / Component | Inspected Source Revision | Relative Path / Module | Current Observed State |
|---|---|---|---|
| **JACA Skunkworks / Dev** | APG113 inspection baseline | `docs/specs/roadmap/xo-capability-roadmap.md` | `JACA-APG0`, `CTX-DOCS`, and `XO-APGR1` are unstarted documentation/qualification gates |
| **JACA Interface Control** | APG113 inspection baseline | `docs/architecture/xo-reference-patterns-and-interface-control.md` | Interface control register rows `ICR-001` through `ICR-006` and `XO-ICR-009` accepted as documentation guidance |
| **JACA XO Go Module** | APG113 inspection baseline | `xo/src/main/go/go.mod` | Declares Go 1.25.0; contains zero APGR dependencies; APGR adapter is not yet exposed |

---

## 3. Package & API Mapping

Downstream consumption is bounded to two functional packages, plus supporting schema definitions:

| APGR Package | Consumed Public APIs | Request / Input Types | Output / Evidence Types | JACA Adapter Responsibility |
|---|---|---|---|---|
| `skills` | `skills.Resolve`, `skills.FootprintContext` | `skills.BundleRequest` (`Consumer`, `ExplicitSkillIDs`, `Budget`) | `skills.BundleResult`, `footprint.Record` | Translate into `CallerSkillEvidence`, `CallerFootprintEvidence`; evaluate applicability |
| `footprint` | `footprint.Measure`, `footprint.Compare`, `footprint.Project` | `footprint.MeasureRequest`, `footprint.CompareRequest`, `footprint.ProjectRequest` | `footprint.Record`, `footprint.Comparison`, `footprint.Projection` | Translate into `CallerFootprintEvidence`, `CallerComparisonDelta`, `CallerProjectionEvidence` |
| `schema` | `schema.SHA256`, `schema.EnvelopeVersion`, `schema.EnvelopeFormat` | Raw payload bytes, schema constants | Lowercase hex SHA-256 digest, version integer | Validate report envelope compatibility and payload digests |

### Excluded Packages

Per existing JACA and APGR architectural decisions:
- `report` and `report.Append`: collection and publication outbox transactions remain JACA-owned.
- `envsnap`: environment evaluation and secret channels remain under JACA/Agent-Security-ND ownership.
- `hotspot`: hotspot analysis remains deferred under `JACA-APG0`.

---

## 4. Caller DTO Type Containment & Invariants

To satisfy `XO-ICR-009`, all APGR types remain encapsulated behind the caller-owned
internal adapter. Outer caller-facing DTOs and method signatures must not leak
APGR domain types:

```text
+-------------------------------------------------------------------+
| JACA XO Orchestration                                              |
|   Caller DTOs: CallerSkillEvidence, CallerFootprintEvidence,      |
|                CallerComponentEvidence, CallerSourceReference,     |
|                CallerComparisonDelta, CallerProjectionEvidence    |
+---------------------------------+---------------------------------+
                                  | calls caller-owned methods
+---------------------------------v---------------------------------+
| APGR-Local Caller Adapter Fixture (xoconsumer.XOAdapter)           |
| (Illustrates caller-owned adapter shape for downstream JACA XO)   |
|   - translates DTOs <-> APGR requests / results                   |
|   - propagates context cancellation via errors.Is                 |
|   - preserves sentinel error families                             |
+---------------------------------+---------------------------------+
                                  | imports public Go packages
+---------------------------------v---------------------------------+
| APGR Public Libraries (github.com/Knowledge-Forge-AI/...)         |
|   - skills, footprint, schema                                     |
+-------------------------------------------------------------------+
```

### Verified Structural Invariants

1. **AST Mechanical Verification**: In `testing/fixtures/xo_consumer/`, `TestXOAdapterContainmentAndASTVerification` parses all non-test `.go` files in the package, verifying zero disallowed imports (including no dot or blank imports and no import aliases) and asserting that zero exported struct fields or method parameters/returns contain APGR package prefixes (`footprint.`, `skills.`, `schema.`, `agentic-praxis-grimoire`), failing closed on any unsupported non-struct exported type definitions. Backed by `TestXOAdapterContainmentNegativeControl`.
2. **Dependency Boundary**: `TestXOAdapterDependencyChainVerification` runs `go list -deps` to assert that `os/exec`, APGR `internal/` packages, APGR `cmd/` packages, and JACA modules are absent from the dependency graph.
3. **In-Memory Smoke Execution**: Adapter operations execute in memory without invoking external subprocesses (`apgr`, Python, npm) or provider network APIs, as verified by static dependency boundary checks and in-memory smoke testing.
4. **Context Propagation & Sentinel Fidelity**:
   - Cancelled or deadline-exceeded contexts in `skills.Resolve` return `ctx.Err()` (`context.Canceled` or `context.DeadlineExceeded`), while `skills.FootprintContext` and `footprint.Measure` wrap `footprint.ErrContextCancelled`.
   - Domain errors retain documented sentinels (`footprint.ErrUnitMismatch`, `footprint.ErrConsequenceBearingOmissionRefused`, `skills.ErrBudgetExceeded`).
5. **Metric Availability & Budget**: Unavailable metrics (such as prompt overhead in independent fixtures) remain unavailable with reason preserved (`Reason: "provider tokenizer is outside..."`), represented by a nil pointer (`Value: nil`), and are never coerced to zero. Explicit zero values remain distinguishable as `*Value == 0`. Explicit zero or exceeded budgets fail closed with `skills.ErrBudgetExceeded`.
6. **Non-Authority Contract**: Recommendations, footprints, and projections are passive informational observations; they convey zero authority to advance workflow, modify lifecycle state, select provider credentials, or persist artifacts. The bounded passive-DTO shape is checked across all six caller DTO types by `TestXOAdapterContractItem7NonAuthority` via reflection against strict allowlists. This does not enforce orchestration authority or prove universal workflow isolation.

---

## 5. Dual-Lane Conformance Evidence

APG114 owns integrated final-source qualification in
[exit 00159](../status/2026/09/06/00159-apg114-v090-integrated-source-qualification-exit.md),
which identifies the new closeout evidence attempt and its limitations. APG113
[exit 00158](../status/2026/09/06/00158-apg113-v090-xo-compatibility-exit.md)
remains historical implementation and producer evidence: its retained manifest
predates the closer's fixture changes and does not bind final closer source.
The original archive is preserved. APG114 closeout reruns passed on Darwin arm64 against the bound source and
fixture inventories. Containment results remain bounded to these fixtures.

### Lane A: Released Baseline `v0.8.1`
- **Module**: `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire`
- **Version**: `v0.8.1`
- **Proxy**: `https://proxy.golang.org`
- **Checksum DB**: `sum.golang.org`
- **Observed Module Selection (`go list -m all`)**:
  - `example.invalid/apgr-xo-consumer`
  - `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1`
- **Observed Module Sums (`go.sum`)**:
  - `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1 h1:V71VcfVQ5/u1mii2l1IS5fzww3wy3mDTwmdN6bmFjH8=`
  - `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1/go.mod h1:SYmdFxwFtkMr7Jp1zw5dvQ/ee6bWwE6edwmQUEQ+VuU=`
- **Verification Execution**: `go vet ./...` (clean, exit 0) and `go test -v -race -count=1 ./...` (clean, exit 0).
- **Retained Evidence**: Separate module, vet, race, sum, and before/after binding receipts are indexed by the APG114 closeout manifest referenced in exit 00159.

### Lane B: Exact Development Candidate
- **Module**: Candidate checkout via invocation-local `replace` directive in disposable storage:
  `replace github.com/Knowledge-Forge-AI/agentic-praxis-grimoire => <candidate-repo-checkout>`
- **Go Work**: Disabled (`GOWORK=off`).
- **Observed Module Selection (`go list -m all`)**:
  - `example.invalid/apgr-xo-consumer`
  - `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1 => <candidate-repo-checkout>`
- **Verification Execution**: `go vet ./...` (clean, exit 0) and `go test -v -race -count=1 ./...` (clean, exit 0).
- **Public Surface Invariance**: No breaking changes were made to public Go APIs in `skills`, `footprint`, or `schema`; observed dual-lane conformance demonstrates clean backward compatibility across the qualified public library APIs (`skills.Resolve`, `skills.FootprintContext`, `footprint.Measure`, `footprint.Compare`, `footprint.Project`).
- **Retained Evidence**: The complete library inventory and separate consumer identities, module selection, vet, and race receipts are indexed by the APG114 closeout manifest referenced in exit 00159.

---

## 6. JACA-Owned Next Actions

With APGR-local compatibility qualified and frozen, subsequent actions proceed under JACA authority:

1. **JACA-APG0**: Author JACA internal adapter design and acknowledge APGR interface control register rows.
2. **CTX-DOCS**: Formulate JACA total-context accounting and custody vocabulary.
3. **XO-APGR1**: Qualify JACA's own adapter implementation against published APGR `v0.8.1` sums within JACA's build and CI environment.
