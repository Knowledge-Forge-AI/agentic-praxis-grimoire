# ADR 0027: Version-Bounded matryer/is as an Independent Go Test Component

- Status: Rejected
- Date: 2026-07-26
- Proposed in: APG39
- Disposed in: APG40
- Relates to: ADR 0026 (Accepted), ADR 0025 (Rejected)

## Context

ADR 0026 is the current accepted Go testing architecture: two independent,
directly triggerable component owners — `go-test-profile` for native lifecycle
and `go-cmp-test-profile` for exact version-bounded semantic comparison after
project selection — with no composition owner. ADR 0025, which proposed four
owners including a `go-testing-stack`, remains Rejected. Nothing in this
proposal alters either record during APG39.

APG38 deferred `matryer-is-test-profile` with two terminal corrected-state
defects: its wrapper rule escalated on nesting alone even though a nested
wrapper that registers itself through the library's own helper registry can
preserve relevant caller attribution, and its relaxed-mode rule manufactured
Orange severity from continuation counts that its own structural rule said do
not escalate. Both defects were authoring defects in the candidate contract,
not evidence that the capability is unjustified: APG38's disposition was
`deferred-material-defect`, the recoverable class that ADR 0026 itself
distinguishes from the stack's terminal `rejected-no-independent-value`.

APG39 authored a narrowly corrected replacement candidate that closes exactly
those two defects while preserving every other APG38-accepted correction. This
ADR records, in advance and conditionally, what retaining that candidate would
mean for the Go owner graph, so that a later separately authorized Codex phase
can decide the architecture and the candidate together rather than improvising
the owner-graph consequence at integration time.

## Decision — rejected in APG40

APG40 independently reviewed and corrected the candidate once. Corrected-state
review then found that the equality mechanism still invented a comparability
condition absent from exact `v1.4.1`: after nil handling and failed deep
equality, the implementation unconditionally compares the two reflected-value
wrappers. The one-cycle rule therefore requires
`deferred-material-defect`; the candidate is not retained.

ADR 0026 remains Accepted and controlling, with `go-test-profile` and
`go-cmp-test-profile` as the two independent current component owners. No
`go-testing-stack`, composition owner, route, or subgraph exists. The
conditional design below is retained as the rejected proposal's historical
boundary, not as current architecture or future authority.

## Rejected conditional design

1. ADR 0026 remains the current accepted architecture during APG39. This ADR
   changes nothing while it is Proposed.
2. A later separately authorized Codex phase may add `matryer-is-test-profile`
   as a third independent Go testing component only when the corrected
   candidate passes fresh independent source, behavior, structural, rights,
   privacy, and executable-evidence review.
3. The component is exact-version-bounded to matryer/is `v1.4.1`. A differing
   selected release is a stop-and-reverify condition, never an assumed
   compatibility.
4. The component triggers only in a repository that has already selected the
   dependency. Selection is a precondition, never an outcome, and dependency
   adoption remains project-owned.
5. The component owns only matryer/is-specific behavior: construction and
   mode, the four assertion families, equality and nil behavior, the
   library's own helper registry and wrapper attribution, relaxed-mode
   continuation, and its diagnostic surface.
6. Native Go test lifecycle remains with `go-test-profile` wherever lifecycle
   is material. No lifecycle ownership moves.
7. Structured or domain-sensitive semantic comparison remains with
   `go-cmp-test-profile` after selection, or with project-owned comparison
   policy. The terse-equality versus semantic-comparison boundary is stated
   from each side without sequencing an invocation.
8. No `go-testing-stack` owner returns. No composition leaf, specification,
   route, or router subgraph is created.
9. Direct component selection remains the normal path: reaching this
   component without passing through another owner is expected.
10. No mandatory chain exists. No profile requires another at runtime, and
    all three components remain independently triggerable and independently
    useful.
11. Candidate-independent removal deletes the component's canonical leaf and
    every integration surface its adopting phase created, repairs surviving
    cross-references to a retained owner or the project-owned fallback, and
    never adds, removes, or changes a target repository's dependency.
12. If a later phase accepts this ADR, it supersedes ADR 0026 **only as the
    complete current Go owner-graph record**. Every accepted ADR 0026
    decision that is still valid is preserved unchanged: native-Go and go-cmp
    ownership, the no-stack decision, direct triggering, component
    optionality, project-owned parameters, the provisional starting maturity,
    the general-Go and process-skill boundaries, non-restatement of another
    profile's procedure, the rollback model, and the requirement that any
    future composition owner needs new evidence and a new ADR. Acceptance adds
    one owner; it reverses nothing.
13. If the matryer/is candidate is deferred again or rejected, the deciding
    phase should mark this ADR Rejected, and ADR 0026 remains the complete
    and controlling owner-graph record.

## Alternatives considered

**Retain ADR 0026 unchanged and add no third owner.** This is the current
state and remains correct if the candidate fails review. It leaves
matryer/is-specific failure modes — reversed nil expectations, misattributed
wrapper failures, forced terse equality — owned by nothing in repositories
that already use the library.

**Add matryer/is as a third independent owner.** Proposed here, conditional
on the corrected candidate passing. It matches the accepted component model:
optional, exact-version-bounded, directly triggerable, independently
removable.

**Fold matryer/is behavior into `go-test-profile`.** Rejected: it binds
universal native semantics to an optional dependency, triggers the native
owner's contract on a library decision, and couples two unrelated refresh
cycles.

**Fold matryer/is behavior into `go-cmp-test-profile`.** Rejected: the two
libraries are independently selected and solve different problems; a
repository may use either without the other, and the combined leaf could not
be partially removed.

**Restore a composition stack.** Rejected. ADR 0025's stack rejection was
terminal, and APG38's representative composed tasks found no residual
recurring coordination work. A third component adds boundary statements, not
a coordinator.

**Leave the behavior project-owned.** Correct for the parameters this
proposal explicitly leaves project-owned, but as a general answer it
reproduces the same release-bounded research in every repository that selects
the library.

## Consequences

### Owner graph that was proposed

```text
go-language-profile        general Go semantics (existing)
  go-test-profile          native testing lifecycle and go test semantics
  matryer-is-test-profile  optional, after project selection, exact v1.4.1
  go-cmp-test-profile      optional, after project selection, exact v0.7.0
```

Indentation records subject-matter narrowing only. There is no composition
node, no entry order, and no dependency among components.

### Maintenance

A third owner adds a third refresh cycle. The matryer/is cycle carries a
specific staleness risk: the calibrated release remains the newest upstream
tag and predates this proposal by more than three years, while untagged
upstream activity would not surface through routine APG work. The leaf therefore
treats a differing selected release as a stop-and-reverify condition before
any behavior claim.

### Status boundary

This ADR was Proposed in APG39, an authoring phase, and Rejected in APG40 after
the candidate's corrected-state review. Nothing from this proposal is
integrated, adopted, mature, published, or deployed. ADR 0026 remains Accepted
and controlling. Rejection grants no readiness, release, publication,
deployment, or successor-phase authority.
