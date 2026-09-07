# APGR JACA XO Consumer Compatibility Fixture

This documentation covers 0.9.0 qualification. The released control lane stays
at published v0.8.1 with its checked-in requirement and sums unchanged.
Prospective verification uses a separate disposable local module replacement;
once 0.9.0 is published, a separate lane can verify it through the public proxy.
This fixture is an adapter example and bounded
compatibility evidence. It is not an activated production JACA adapter or a
universal security proof. JACA owns registration, production integration, and
adoption.

## Purpose

This fixture provides an independent, caller-owned Go adapter verifying APGR-side
compatibility for downstream JACA XO orchestrator integration, covering the
public `skills` and `footprint` Go packages (plus supporting `schema`).

The fixture verifies that a caller (such as JACA) can consume APGR library
capabilities behind an internal adapter without leaking APGR domain types into
caller-facing DTOs, without subprocess execution, and without implicit workflow
authority.

---

## Seven Core Compatibility Guarantees

| # | Guarantee | Requirement | Verification Mechanism |
|---|---|---|---|
| 1 | **Public API & Real Fields** | Direct calls to public `skills.Resolve`, `skills.FootprintContext`, `footprint.Measure`, `Compare`, `Project` using real request structs | `adapter.go` uses official public structs and enums; no invented types or CLI flags |
| 2 | **Repeatability & Identity** | Deterministic canonical JSON and stable fingerprints across identical invocations | `TestXOAdapterPublicWorkflowAndContainment` asserts byte and digest identity |
| 3 | **Cancellation & Sentinels** | `context.Context` cancellation/deadline propagated via `errors.Is`, preserving APGR sentinels | `TestXOAdapterCancellationAndSentinelPreservation` tests `context.Canceled`, `context.DeadlineExceeded`, `ErrContextCancelled`, `ErrUnitMismatch`, `ErrConsequenceBearingOmissionRefused`, `ErrBudgetExceeded` |
| 4 | **Metric Availability & Budget** | Unavailable metrics remain unavailable with reason preserved; budget refusal returns `ErrBudgetExceeded` | `TestXOAdapterPublicWorkflowAndContainment` validates unavailable prompt overhead; `TestXOAdapterCancellationAndSentinelPreservation` tests budget refusal |
| 5 | **APGR Type Containment** | Outer caller-facing DTOs (`CallerSkillEvidence`, `CallerFootprintEvidence`, `CallerComponentEvidence`, `CallerSourceReference`, `CallerComparisonDelta`, `CallerProjectionEvidence`) and method signatures do not leak APGR implementation types | Bounded static inspection of all runtime fixture files via `TestXOAdapterContainmentAndASTVerification` (with fail-closed non-struct checking and import alias exclusions) and negative control `TestXOAdapterContainmentNegativeControl` |
| 6 | **Zero Delegation & Imports** | No subprocess dependencies (`os/exec`), no APGR `internal/` or `cmd/` packages, no JACA imports | `TestXOAdapterContainmentAndASTVerification` (static AST) and `TestXOAdapterDependencyChainVerification` (`go list -deps`) |
| 7 | **Pure In-Memory Semantics** | Observations carry zero workflow authority, routing choices, provider execution, or persistence effects | `TestXOAdapterContractItem7NonAuthority` verifies passive DTO reflection allowlists; `TestXOAdapterPureInMemoryRuntimeSmoke` checks in-memory smoke execution |

---

## Gap-to-Existing-Coverage Analysis

This fixture reuses coverage from `testing/fixtures/external_consumer/consumer_test.go`
and isolates the missing boundary characteristics required for JACA XO integration:

| Coverage Area | Existing Fixture (`external_consumer/`) | New XO Fixture (`xo_consumer/`) | Architectural Role |
|---|---|---|---|
| **Direct Library Calls** | Comprehensive matrix of public methods, options, round-trip JSON | Streamlined adapter calls wrapping public methods | Reused |
| **Data Types** | Exercises raw APGR public structs directly (`footprint.Record`, `skills.BundleResult`) | Caller-owned DTOs (`CallerSkillEvidence`, `CallerFootprintEvidence`, `CallerComponentEvidence`, `CallerSourceReference`, `CallerComparisonDelta`, `CallerProjectionEvidence`) | **New Boundary (Contract Item 5)** |
| **AST Type Containment** | None (consumer directly imports and consumes types) | Bounded static inspection verifies zero APGR types in exported DTOs or public signatures, failing closed on unsupported non-struct forms | **New Boundary (Contract Item 5)** |
| **Dependency Boundary** | Verifies basic imports | Verifies zero `os/exec`, zero APGR `internal/` or `cmd/`, zero JACA imports via AST and `go list -deps` | **New Boundary (Contract Item 6)** |
| **Cancellation & Sentinels** | Tests `errors.Is` on raw APGR calls | Tests `errors.Is` across caller adapter translation layer (including `ErrBudgetExceeded`) | Reused & Verified across adapter |
| **Non-Authority Contract** | None (library-level testing) | Structural reflection verifies all caller DTO fields match passive domain metric and provenance allowlists | **New Boundary (Contract Item 7)** |

---

## Dual-Lane Execution

### Lane A: Released Baseline (`v0.8.1`)
Run against the published module on `proxy.golang.org` with checksum database verification:
```sh
cd $(mktemp -d)
cp /path/to/testing/fixtures/xo_consumer/* .
cp fixture-go.mod go.mod
GOPROXY=https://proxy.golang.org GOSUMDB=sum.golang.org GOWORK=off go mod tidy
GOPROXY=https://proxy.golang.org GOSUMDB=sum.golang.org GOWORK=off go test -v -race -count=1 ./...
```
Expected sums in `go.sum`:
- `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1 h1:V71VcfVQ5/u1mii2l1IS5fzww3wy3mDTwmdN6bmFjH8=`
- `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1/go.mod h1:SYmdFxwFtkMr7Jp1zw5dvQ/ee6bWwE6edwmQUEQ+VuU=`

### Lane B: Exact Development Candidate
Run against the local candidate repository checkout via an invocation-local `replace` directive:
```sh
cd $(mktemp -d)
cp /path/to/testing/fixtures/xo_consumer/* .
cp fixture-go.mod go.mod
go mod edit -replace github.com/Knowledge-Forge-AI/agentic-praxis-grimoire=/path/to/candidate
GOWORK=off go mod tidy
GOWORK=off go test -v -race -count=1 ./...
```
