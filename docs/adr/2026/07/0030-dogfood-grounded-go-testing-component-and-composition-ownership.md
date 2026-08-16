# ADR 0030: Dogfood-Grounded Go Testing Component and Composition Ownership

- Status: Rejected
- Date: 2026-07-27
- Proposed in: APG48
- Decided in: APG49
- Relates to: ADR 0025 (Rejected), ADR 0026 (Accepted and controlling),
  ADR 0027 (Rejected), ADR 0029 (Accepted with amendment)

## Context

ADR 0026 is the current accepted Go testing architecture: two independent
component owners — `go-test-profile` for native lifecycle and
`go-cmp-test-profile` for exact version-bounded semantic comparison — with no
composition owner. ADR 0025 (four owners including a stack) and ADR 0027 (a
prior matryer/is third component) remain Rejected. ADR 0029 made matryer/is
and any stack owner evidence-tested candidates for v0.5: retention requires
that named dogfood repositories expose recurring work not already owned by
the retained profiles, project conventions, or a corrected matryer/is
profile. Nothing in this proposal alters any of those records while it is
Proposed, and APG48 changes no current architecture.

APG48 performed the bounded dogfood: read-only inspection of five public Go
repositories — two selecting matryer/is v1.4.1 and go-cmp v0.7.0 directly in
maintained tests, one declaring matryer/is only as an unused indirect
requirement, and two negative controls (one testify-convention, one pure
native) — under the APG47 evidence discipline, with remote-equality
verification for all five clones. The complete matrices, samples, and gate
applications are in the publication-excluded APG48 records; the public
summary is the
[APG48 evaluation](../../../evaluations/apg48-go-test-harness-dogfood-and-candidate-authoring.md).

The prior matryer/is failures were authoring defects, not capability
judgments: APG36 deferred it for reversed typed-nil behavior and an omitted
helper registry; APG38 deferred it for depth-based wrapper severity and
count-manufactured relaxed escalation; APG40 rejected ADR 0027 after the
candidate's equality mechanism invented a comparability precondition absent
from exact source. Each defect family now has a source-verified closure and a
frozen scenario in the new candidate, authored this time from dogfood-
calibrated evidence rather than corrected after review.

## Decision

APG49 rejects the proposed third component after the single authorized
correction pass. Fresh corrected-state review found new material behavior
defects:

1. the prose made strict parent-bound use inside a child subtest Red under
   native `FailNow` rules, while the controlling structural table still made
   the same generic parent-instance shape Orange;
2. the specification correctly made a maintained import at another selected
   version a source-refresh stop, then also classified another selected
   release as a non-trigger;
3. the source-filename exclusion pattern omitted the exact terminal anchor and
   consequently misstated its suffix-match and relocation boundaries; and
4. the public fixture preserved the APG48 scenario identifiers but reassigned
   APG48-IS-02 to a different family, so its test proved numeric continuity
   without semantic continuity.

The one-cycle rule permits no second behavior correction. The current
candidate leaf, specification, fixture, and focused owner are therefore
forward removed. `matryer-is-test-profile` is
`deferred-material-defect`; no third component is added. ADR 0026 remains
Accepted and controlling as the complete current Go owner-graph record. ADR
0025 and ADR 0027 remain Rejected.

The APG49-corrected proposal evaluated was:

1. **Add `matryer-is-test-profile` as a third independent Go testing
   component**, exact-version-bounded to matryer/is `v1.4.1`. Triggering is
   ordered: first establish maintained-test import and use; otherwise an
   indirect requirement or `go.sum` entry is a non-trigger at any version.
   Only then resolve the module-graph-selected version, proceeding for exact
   `v1.4.1` and stopping for source refresh on any other selected version.
   The task must also materially depend on library-specific behavior.
   Candidate disposition in APG48: `authored-pending-codex-review`.
2. **Create no composition owner.** `go-testing-stack` receives
   `not-authored-no-independent-value` on fresh five-repository evidence: the
   eight-part stack-evidence gate failed on residual ownership (parts 3 and
   4), procedure and trigger precision (parts 5 and 6), and the prohibition
   on presence-counting (part 8), and zero cases were observed of two
   selected owners giving contradictory answers about the same part of one
   test's observable contract. No stack leaf, specification, route, or
   subgraph exists.
3. Component ownership and composition ownership remain distinct questions.
   This ADR adds evidence to both: a corrected component owner is supportable;
   a composition owner is not.
4. ADR 0025 remains Rejected; ADR 0026 remains Accepted and controlling
   during APG48; ADR 0027 remains Rejected. This ADR explains new dogfood
   evidence rather than reopening those records.
5. Direct component selection remains the normal path; no profile requires
   another at runtime; no mandatory chain or router subgraph is created.
   Optional `cmp.Diff` plus exact empty-string assertion is direct composition:
   go-cmp owns semantic comparison, and matryer/is owns only string assertion
   and routing.
6. Dependency selection, version and upgrade policy, assertion-style and
   mixed-library conventions, and all test-execution policy remain
   project-owned.
7. Removal of the new component is candidate-independent: it deletes the leaf
   and every integration surface its adopting phase created and repairs
   surviving cross-references, preserving ADR, evaluation, and exit history,
   and never changes a target repository's dependency.
8. **This ADR makes no current architecture change.** While Proposed, the
   owner graph, catalog, projections, routes, maturity, release policy, and
   inventories are exactly those of ADR 0026, and integrated development
   remains 28 canonical skills, 28 catalog rows, and 28 projections.
9. Exact v1.4.1 behavior includes six reflected nil kinds (Chan, Func,
   Interface, Map, Ptr, Slice), lexical rather than syntax-aware diagnostic
   recovery, lexical source-filename frame exclusion, and per-instance
   registry state. Strict parent-bound child-subtest use is a native lifecycle
   stop; relaxed parent-bound use marks the parent while the child continues
   and requires an explicit accepted boundary.

## APG49 evidence

APG49 verified the immutable APG48 object and managed reports, delivered the
exact Claude branch, independently read exact canonical v1.4.1 bytes, re-read
the five dogfood repositories at their recorded commits, created and ran
public-safe failing-first controls, and ran isolated exact-version probes for
nil, equality fallback, routing, registry, attribution, subtests, concurrency,
diagnostics, and protected output. It collected all initial material findings,
applied one coherent correction pass, and then used fresh non-author reviewers.
The defects in this decision were found only in that corrected-state review.

## Supersession boundary

The proposed supersession did not activate. ADR 0026 remains the complete
current Go owner-graph record. Any future candidate requires fresh maintainer
authority, exact source and runtime evidence, a new correction allowance, and
a new decision record; it cannot treat APG49's corrected draft as retained.

## Alternatives considered

**Retain ADR 0026 unchanged and author nothing.** Truthful but incomplete:
two of five dogfood repositories select the library directly in maintained
tests at exactly the calibratable release, and the observed failure-mode
surface (attribution divergence, diagnostic loss, indirect-presence
misfires) is currently owned by nothing.

**Author the stack as well.** Rejected by evidence: the gate's residual test
failed in five repositories, reproducing APG36's no-independent-value result
on fresh grounds. The strongest observed shape is a repository-local helper
convention partly outside the three-component universe.

**Fold matryer/is behavior into an existing profile.** Rejected previously
(ADR 0027 alternatives) and still wrong: it would bind universal or
independently selected owners to an optional dependency and couple unrelated
refresh cycles.

**Proposed graph.** Identical to the rejected ADR 0027 target graph — three
independent components under the language profile, no composition node — but
proposed this time from dogfood-calibrated authoring rather than a corrected
draft, with the equality-mechanism defect closed at authoring time.

## Consequences

ADR 0026 stands complete. Development remains 28/28/28 with fourteen stable
and fourteen provisional rows. The exact-source, runtime, dogfood, and defect
records remain durable evidence, but no candidate surface survives current
state. The stack question remains settled for v0.5 by fresh evidence: any
future composition proposal needs the recurring contradictory-answer evidence
ADR 0026 already requires, which five repositories did not produce.
