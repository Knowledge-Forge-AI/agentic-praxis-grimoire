# JACA XO Consumer Qualification Fixture

This directory provides an immutable caller-owned qualification fixture demonstrating
consumption of APGR's public Go packages (`phase`, `routing`, `evidence`, `candidate`,
`provider`) without leaking APGR domain types across the caller boundary and with zero
subprocess coupling.

Module identity: `example.invalid/apgr-jaca-consumer`

## Architectural Boundary Invariants

1. **Strict Type Containment**:
   All caller signatures and structs (`CallerPhaseRequest`, `CallerRouteSelection`,
   `CallerFindingEvidence`, `CallerFindingDisposition`, `CallerCandidateSummary`,
   `CallerArtifactRecord`, `CallerObservationFact`, `CallerConformanceSummary`)
   use primitive Go types. Zero APGR internal or domain types leak into caller DTOs.

2. **Zero Subprocess Coupling**:
   The adapter performs pure in-memory calculation and validation. Zero use of `os/exec`
   or terminal text scraping.

3. **Policy-Neutral Dynamic Routing**:
   `routing.Resolve` evaluates capability satisfaction, active observations, reviewer
   independence, and deterministic ranking without asserting route-policy authority.

4. **Strict Work-Only Request V2**:
   Request V2 enforces work-only parameters (`schema`, `phase_type`, `prompt`).
   Any caller payload containing `execution_mode`, `constraints`, or runtime fields
   fails closed.

5. **Strict CWD Independence**:
   All operations accept in-memory buffers or data structures; no reliance on ambient working directory.

---

## Execution Lanes

### Lane A: Released Baseline
*Status*: **Deferred to post-v0.12 release publication (ICR-004)**.
No published proxy module contains `phase`, `routing`, `evidence`, `candidate`, or `provider`.
Lane A qualification will run following public `v0.12.0` release publication.

### Lane B: Exact Candidate Source Under Qualification (Produces Qualification Receipt)
Run against the candidate repository checkout via an isolated invocation-local `replace` directive in a clean temporary directory:

```sh
SCRATCH=$(mktemp -d)
cp testing/fixtures/jaca_consumer/* "$SCRATCH/"
cd "$SCRATCH"
cp fixture-go.mod go.mod
go mod edit -replace github.com/Knowledge-Forge-AI/agentic-praxis-grimoire=/path/to/agentic-praxis-grimoire_dev
GOWORK=off go mod tidy
GOWORK=off go test -v -race -count=1 ./...
```

### In-Tree Main Module Verification
Because `testing/fixtures/jaca_consumer` does not commit a live `go.mod` (using `fixture-go.mod`),
the root repository test runner compiles and exercises the package in-tree:

```sh
go test -v -race ./testing/fixtures/jaca_consumer/...
```
