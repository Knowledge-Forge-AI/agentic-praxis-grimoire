# ADR 0025: Go Testing Component and Stack Ownership

- Status: Rejected
- Date: 2026-07-25
- Proposed in: APG35
- Disposed in: APG36

## Context

APG v0.4 needs Go testing capability. Three distinct concerns appear in real Go
repositories and they do not have the same owner.

Native Go testing is universal. Every Go repository with tests uses the standard
library's test type, its execution lifecycle, its subtests, its cleanup and
isolation helpers, its parallelism rules, and its selection and caching
behavior. None of that depends on a third-party dependency.

matryer/is and google/go-cmp are optional and independently selected. A
repository may use neither, either, or both. They solve different problems.
matryer/is is a deliberately minimal assertion surface: calibration release
`v1.4.1` exposes four assertion families and no option surface. google/go-cmp is
a configurable semantic comparison engine: calibration release `v0.7.0` exposes
an extensive option, comparer, transformer, and filter surface whose composition
determines what a test can still detect.

`go-language-profile` already owns general Go semantics and does not address
test-specific judgment. APG's process skills already own implementation,
planning, debugging, and review. Neither addresses which testing owner holds
which part of a test's contract.

The design question is how many owners APG should create, and whether a
composition owner is justified. A single monolithic Go testing skill would bind
universal native semantics to two optional dependencies. Component profiles
alone would leave the recurring cross-component question — which owner holds
which part of the contract — unowned. This ADR proposes the split and the thin
composition owner, and records the alternatives considered.

APG35 authored the candidate leaves but did not integrate or test them. APG36
then performed fresh independent source, ownership, structure, privacy, and
rights review; converted all 154 frozen families into transient executable
fixtures; and ran focused disposable Go compatibility evidence. That review
found multiple independent behavior corrections in every component and no
viable retained owner graph for the stack. APG36 therefore rejects this
proposal.

## Proposal evaluated

1. `go-test-profile` owns native Go `testing` and `go test` semantics: test
   package placement, tests and subtests, helper attribution, fatal and nonfatal
   failure, cleanup ordering, temporary directories and environment and
   working-directory isolation, `TestMain`, parallelism, goroutine lifetime and
   reporting, examples, benchmarks, fuzzing, selection patterns, and caching.
2. `matryer-is-test-profile` owns matryer/is-specific assertion semantics after
   the target repository has already selected the dependency: instance
   construction and strict or relaxed mode, the available assertion families,
   equality and typed-nil behavior, failure formatting, source-comment
   diagnostics, and the library's own attribution mechanism.
3. `go-cmp-test-profile` owns google/go-cmp-specific semantic comparison after
   the target repository has already selected the dependency: equality versus
   diff, option composition and filtering, custom comparers and transformers,
   ignoring and unexported-field boundaries, approximate and error comparison,
   ambiguity and panic conditions, and deterministic ordering.
4. `go-testing-stack` owns thin composition among the selected components: which
   already-selected owner holds which part of one test's observable contract.
5. Native Go testing remains the lifecycle owner in every composition. No
   component profile and no composition may move lifecycle ownership.
6. Component profiles remain independently triggerable and independently
   removable. Each is useful without the others and without the stack.
7. The stack does not force matryer/is, does not force go-cmp, and does not
   force all three components. It composes only what the repository already
   selected.
8. The stack does not duplicate component APIs, procedures, or structural
   tables. It holds composition signals only.
9. `go-language-profile` retains general Go semantics. Test-specific profiles do
   not restate its contract.
10. Process skills retain implementation, planning, debugging, and review.
    Entering a test profile does not replace them, and none of them mandates
    entering a test profile.
11. The target repository retains dependency selection and version; exact
    commands and flags; package layout; race, fuzz, benchmark, coverage, worker,
    platform, and CI policy; and external-resource and destructive-action
    authority.
12. Each leaf that a later phase retains begins `provisional`.
13. Codex owns executable fixtures, failing-first tests, integration,
    corrections, acceptance, mainline adoption, reporting, readiness,
    publication, and deployment.

## Alternatives considered

The first four alternatives below record APG35's proposal-era analysis. APG36's
terminal disposition follows each premise that independent review overturned.

**Native Go test profile only.** APG35 rejected it because it leaves assertion
and comparison behavior unowned in repositories that have already selected
those dependencies, where the observed failure modes — misleading attribution,
hidden semantics behind terse equality, ignore sets that quietly stop
protecting behavior — are concrete and consequential.

**One monolithic Go testing skill.** APG35 rejected it because it binds
universal native semantics to two optional dependencies, triggers on
repositories that use neither, cannot be partially removed, and would carry
three unrelated calibration and refresh cycles in one leaf.

**Component profiles with no stack.** APG35 rejected this closest alternative
on the premise that a recurring cross-component question deserved its own
owner. APG36 did not validate that premise: ordinary native-plus-one-component
roles were already disjoint, and the narrower residual conflict cases did not
justify the authored stack after the component dispositions.

**Native profile plus generic assertion guidance.** APG35 rejected it because
generic guidance cannot state the observed library-specific facts that matter,
such as a four-family assertion surface with no option surface, or an
attribution mechanism that reads the assertion's own source line rather than
using the native helper mechanism.

**Four owners with thin optional composition.** Proposed by APG35 and rejected
by APG36. Native lifecycle, matryer/is, and go-cmp source contracts each need
more than the permitted one behavior correction. The stack cannot exist
without the native owner and does not demonstrate independent current value.

**Existing project and process owners.** This is the APG36 result. It adds no
new Go-testing owner while replacement component contracts and any narrower
composition value remain unevidenced.

## Consequences

### Proposed owner graph — not adopted

```text
go-language-profile        general Go semantics
  go-test-profile          native testing lifecycle and structure  (always applicable)
    matryer-is-test-profile   optional, after project dependency selection
    go-cmp-test-profile       optional, after project dependency selection
  go-testing-stack         thin composition, only when >= 2 owners are selected
```

Indentation showed the intended subject-matter narrowing rather than a mandatory
chain. APG36 did not adopt this graph. Existing language, repository, and
process owners remain unchanged.

### Proposed overlap controls and observed result

APG35 proposed the following three overlap controls:

- **Terse assertion versus semantic comparison.** Both can compare two values.
  The boundary is that structured or domain-sensitive comparison requiring
  ignoring, ordering, tolerance, error identity, or a custom rule belongs to
  go-cmp; simple local expectations belong to matryer/is.
- **Component profile versus native profile.** Both touch failure reporting. The
  boundary is that native testing owns the reporting mechanism, subtest
  structure, parallelism, and goroutine rules, while a component owns only its
  own API's behavior within those rules.
- **Stack versus components.** The stack could drift into restating component
  detail. Decisions 7 and 8 attempted to bound it.

APG36 found that the component facts and stack controls did not satisfy these
premises. The candidate leaves were removed, and no route was added. Existing
language, repository, and process owners continue to govern current work.

### Proposed maintenance cost

The proposal would have carried four refresh cycles. Native testing would
refresh on Go release
and `testing` API changes. matryer/is refreshes on its release, assertion
surface, equality, and attribution behavior. go-cmp refreshes on its release,
option set, documented comparer obligations, and panic conditions. The stack
would hold no independent API calibration by design and refresh only when a
boundary between owners moves.

The two optional components carried a specific staleness risk: matryer/is is at a
2023 release and go-cmp at a 2025 release, so an unnoticed upstream change would
not surface through routine APG activity. Both candidate leaves treated
a differing selected release as a refresh condition before any behavior claim,
rather than assuming the calibrated behavior holds.

### Proposed rollback and observed removal

APG35 proposed that each leaf would be independently removable. The proposed
mechanical removal would delete its leaf, flat projection, catalog and
general-map entries, current-development release policy, strict test inventory,
focused contract, and public scenario fixture while preserving evaluation and
exit history. APG36 found the claimed independent usefulness false for the
stack without its native owner and did not integrate any of these surfaces.

APG36 preserves the exact APG35 authoring commit in mainline history and removes
the four Go candidate leaves through its forward integration commit. No
projection, catalog, router, release-policy, inventory, or current fixture
surface is added.

### Future work — not authorized

- Whether a fifth Go testing owner is justified for integration or contract
  testing is deferred. No current evidence demands one.
- Whether a future matryer/is profile should use a version-bounded trigger.
- Whether a differently bounded composition owner can demonstrate independent
  value after component source contracts are redesigned.
- Exact catalog wording, route triggers, capability classes, projections, and
  maturity for any future replacement candidates.

These questions require fresh maintainer authority and a new decision. They do
not leave this proposal unresolved.

### Status boundary

This ADR is Rejected. The five candidate leaves authored in APG35 are not
integrated, adopted, mature, published, or deployed; APG36 removes them from the
current tree after independent review and executable evidence. Integrated
development remains 25 canonical skills, 25 catalog rows, and 25 flat
projections. Public and active v0.3.0 remain 19/19/19.
