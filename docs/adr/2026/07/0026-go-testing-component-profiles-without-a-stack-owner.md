# ADR 0026: Go Testing Component Profiles Without a Stack Owner

- Status: Accepted
- Date: 2026-07-25
- Proposed in: APG37
- Accepted in: APG38
- Relates to: ADR 0025 (Rejected)

## Context

APG v0.4 still has no Go testing owner. ADR 0025 proposed four owners — a
native profile, two optional component profiles, and a thin composition stack —
and APG36 rejected it after independent source review. That rejection had two
distinct causes, and separating them is the whole basis of this decision.

The first cause was factual. All three component contracts stated behavior that
current primary sources contradict: the native draft treated calling the test
runner from `TestMain` as an unconditional API requirement, keyed language
semantics to the installed toolchain, conflated the fuzzing surfaces, imposed a
universal goroutine-join rule, and carried uncalibrated structural bands. The
matryer/is draft reversed the library's typed-nil equality behavior and omitted
its own helper registry. The go-cmp draft imposed a total-ordering requirement
on both sorting transformers. These are correctable authoring defects, not
evidence that the underlying capability is unsound.

The second cause was structural and specific to the stack. Its retention
precondition was its native owner, which was itself deferred. Counting native
testing as one owner meant that native-plus-one-component mechanically
satisfied the stack's two-owner trigger even when the roles were already
disjoint and no composition conflict existed. Its owner-count table declared
warning and crisis bands that required four or five coordinated component
owners in a three-component universe, so those bands were unreachable. The
strongest genuine cases were narrow residual owner conflicts, not ordinary
component selection.

APG37 redesigned the four deferred candidates from the APG36 defect dossier
against reverified current sources. It did not revive the stack. This ADR
records the bounded subset that survives APG38 terminal review. Native Go and
go-cmp remain independent owners; matryer/is is deferred after new
post-correction attribution and false-escalation defects; the composition owner
does not return.

## Decision

After APG38 independent validation, correction, and executable evidence:

1. `go-test-profile` owns native Go testing lifecycle and `go test` semantics:
   package placement, tests and subtests, helper attribution, fatal and
   nonfatal reporting, cleanup and isolation, `TestMain`, parallelism,
   goroutine reporting boundaries, examples, benchmarks, fuzzing, selection,
   caching, and the test-specific consequences of the effective language
   version.
2. `go-cmp-test-profile` owns exact version-bounded google/go-cmp behavior
   after the target repository has already selected the dependency, calibrated
   to `v0.7.0`.
3. **No separate `go-testing-stack` owner is proposed.** No composition leaf,
   specification, route, or router subgraph is created.
4. Ordinary composition is handled through direct component triggers,
   cross-references in each component leaf at genuine owner boundaries, the
   general APG router, repository-local testing conventions, and existing
   process skills.
5. Native Go testing remains the lifecycle owner wherever lifecycle is
   material. No component profile moves lifecycle ownership.
6. Both profiles remain independently triggerable and
   candidate-independently removable. Each is useful without the others.
   Removal also repairs surviving boundary references so they name a retained
   owner or the project-owned fallback.
7. The optional component is not required. A repository that has not selected
   go-cmp still uses the native owner independently.
8. Direct component selection is the normal path. Reaching a component profile
   without passing through another owner is expected, not an exception.
9. `go-language-profile` retains general Go semantics. The test profiles do
    not restate its contract.
10. Process skills retain implementation, planning, debugging, and review.
    Entering a test profile does not replace them, and none of them mandates
    entering a test profile.
11. The target repository retains dependency and version selection, exact
    commands and flags, package layout, race, fuzz, benchmark, coverage,
    worker, platform, and CI policy, and external-resource and
    destructive-action authority.
12. Both retained profiles begin `provisional`.
13. A future composition owner requires new evidence and a new decision record.
    It cannot be revived by implication from this ADR, and accepting this ADR
    does not reopen ADR 0025.

## Alternatives considered

**No APG Go-test profiles.** This is the current state after APG36. It is
coherent and carries no maintenance cost, but it leaves the observed failure
modes — a package that reports success without running its tests, attribution
that points away from the failing contract, ignore sets that quietly stop
protecting behavior — owned by nothing.

**Native profile only.** Rejected because it leaves semantic comparison
behavior unowned in repositories that have already selected go-cmp, where the
APG36 sorting finding shows that release-bounded facts are easy to reverse.

**Native plus one generic comparison section.** Rejected because generic
guidance cannot safely carry the release-bounded option, sorting, unexported,
approximation, and panic contracts. It would either omit those facts or state
them without a version boundary.

**Three independent component profiles.** Proposed by APG37 but not accepted as
a complete set. Terminal APG38 review found new post-correction matryer/is
attribution and count-only escalation defects, so that owner is deferred under
the one-cycle rule.

**Two independent profiles.** Accepted. Native lifecycle and exact go-cmp
comparison remain independently useful, directly triggerable, separately
removable, and bounded to their own refresh cycles.

**Monolithic Go testing skill.** Rejected because it binds universal native
semantics to an optional dependency, triggers on repositories that do not use
it, cannot be partially removed, and carries two unrelated calibration and
refresh cycles in one leaf.

**Component profiles plus a stack.** This was ADR 0025 and it remains rejected.
APG37 found no new evidence of a residual composition problem that the
component leaves' own cross-references cannot state.

**Project-only guidance.** Rejected as a general answer because it reproduces
the same version-bounded research in every repository, though it remains
correct for the parameters this proposal explicitly leaves project-owned.

## Consequences

### Proposed owner graph

```text
go-language-profile        general Go semantics
  go-test-profile          native testing lifecycle and structure
  go-cmp-test-profile      optional, after project dependency selection
```

Indentation shows subject-matter narrowing, not a mandatory chain. There is no
composition node. Nothing in this graph is entered automatically.

### Why ADR 0025 remains Rejected

ADR 0025 is not superseded, amended, or reopened by this record. It remains the
durable rejected record of the four-owner proposal, including its stack, and
APG37 makes no change to its status or text.

Component ideas may nonetheless be redesigned despite that rejection because
APG36's component dispositions were `deferred-material-defect`, not
`rejected-no-independent-value`. A deferral records that the authored contract
was wrong, not that the capability is unjustified. Only `go-testing-stack`
received the terminal no-value disposition, and only it is excluded from
redesign. Treating a deferral as a permanent bar would make any authoring defect
unrecoverable; treating the stack's rejection as reversible would ignore a
finding that survived independent review.

### No mandatory chain

No profile requires another at runtime. A component leaf may cross-reference
another only to state a genuine owner boundary, such as native lifecycle versus
semantic comparison. A cross-reference names an owner; it does not sequence an
invocation. No router subgraph is created.

### Overlap

One overlap is foreseeable and is bounded by rule rather than by a coordinating
owner. Native testing owns the reporting mechanism, subtest structure,
parallelism, and goroutine rules, while go-cmp owns only its own API's behavior
within those rules.

### Maintenance and versioning

This proposal carries two refresh cycles rather than four. Native testing
refreshes on Go releases and `testing` API changes and is exercised by ordinary
activity. The optional component refreshes on its own releases and carries a
specific staleness risk because an upstream change would not surface through
routine APG work. Its leaf therefore treats a differing selected release as a
refresh condition before any behavior claim rather than assuming the calibrated
behavior holds.

### Structural calibration

Structural signals in both retained leaves are categorical rather than numeric
wherever the inspected corpus does not support a numeric cutoff. Measurement
against the Go standard library and toolchain test corpus showed that absolute
file size and test-function count do not predict ownership or truthfulness
risk, so the earlier numeric crisis bands would have marked ordinary,
well-maintained upstream test files as crises. A structural Red must correspond
to an ownership, truthfulness, safety, or maintainability risk.

### Rollback

Each leaf is removed through a candidate-independent change that deletes its
canonical leaf, checked projection, catalog and capability-map entries,
current-development release policy, strict inventory entry, focused contract,
and public scenario fixture while preserving ADR, evaluation, and exit history.
The same change repairs surviving cross-references to name a retained owner or
project-owned fallback. Removing the native profile also makes the component
leaves' native-lifecycle fallback explicit. Because there is no composition
owner, removal never creates a replacement stack and never changes a target
repository's dependency.

### Future composition evidence

A future composition owner would require evidence this proposal does not have:
recurring conflicts where two already-selected owners give contradictory
answers about the same part of one test's observable contract, which the
component leaves' own boundary statements cannot resolve. Owner redundancy,
predetermined routing, and ordinary multi-dependency selection are not that
evidence. Such a proposal needs a new ADR and fresh maintainer authority.

### Status boundary

APG38 accepts this ADR for the two retained provisional Go profiles after
independent source, owner-graph, structural, compatibility, rights, privacy,
and corrected-state review. `matryer-is-test-profile` and `nix-test-profile`
are independently deferred after new post-correction defects. Integrated
development is 27 canonical skills, 27 catalog rows, and 27 flat projections.
Public and active v0.3.0 remain 19/19/19. Acceptance does not grant readiness,
release, publication, deployment, or successor-phase authority.
