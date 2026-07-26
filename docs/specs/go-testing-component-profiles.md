# Specification: Go Testing Component Profiles

Status: Accepted by [ADR 0026](../adr/2026/07/0026-go-testing-component-profiles-without-a-stack-owner.md) in APG38.

This specification defines the owner graph, triggers, boundaries, and removal
model for APG's Go testing component profiles. It does not restate the
component procedures; each leaf owns its own procedure, structural contract,
and stops.

## Owner graph

Two independent owners are retained. There is no composition owner.

```text
go-language-profile        general Go semantics (existing)
  go-test-profile          native testing lifecycle and go test semantics
  go-cmp-test-profile      optional, after project dependency selection
```

Indentation records subject-matter narrowing only. It is not a call sequence,
an entry order, or a dependency.

| Owner | Owns | Does not own |
| --- | --- | --- |
| `go-test-profile` | native `testing` and `go test` behavior: placement, subtests, helper attribution, reporting, cleanup and isolation, `TestMain`, parallelism, goroutine reporting boundaries, examples, benchmarks, fuzzing, selection, caching, and test-specific effects of the effective language version | dependency selection, library-specific behavior, general Go semantics, project commands and policy |
| `go-cmp-test-profile` | version-bounded go-cmp behavior after selection: equality versus diff, option composition and filters, comparer and transformer obligations, ignoring and unexported boundaries, sorting and approximation contracts, ambiguity and panic conditions, diagnostic exposure | whether to adopt the dependency, native lifecycle, terse local assertions, production equality design, project commands and policy |

## Trigger rules

Each profile is triggered directly by the material judgment it owns.
Reaching a component profile without passing through another owner is the
normal path.

1. `go-test-profile` triggers when a task materially depends on native test
   lifecycle, structure, isolation, reporting, or `go test` behavior. It does
   not require any dependency to be present.
2. `go-cmp-test-profile` triggers only when the repository has **already
   selected** google/go-cmp and the task materially depends on semantic
   comparison. Selection is a precondition, never an outcome.
3. A question about whether to adopt the dependency is a non-trigger for
   every profile here and is project-owned.
4. Ordinary Go implementation with no material test-specific decision is a
   non-trigger; `go-language-profile` or a process skill applies.
5. Entering either profile never replaces a process skill. A behavior
   change can keep `implementing-with-test-discipline` primary; a review can
   keep `reviewing-and-verifying-repository-work` primary.

## No stack and no mandatory chain

No composition owner is created or implied.

- No `go-testing-stack` leaf, specification, catalog row, projection, route, or
  router subgraph is created by this specification or by ADR 0026.
- No profile requires another at runtime. Selecting a component profile does
  not require entering the native profile first, and entering the native
  profile does not require a component profile even when a dependency exists.
- Using native test lifecycle and the optional comparison component together
  does not create a separate coordination obligation; each owner remains
  directly selectable where its own behavior is material.
- A future composition owner requires new evidence and a new ADR. ADR 0025
  remains Rejected and is not revived by implication.

## Cross-reference rules

A component leaf may name another owner only to state a genuine boundary, and
only under these constraints:

1. A cross-reference names the owner of a contract; it does not sequence an
   invocation or require entry.
2. A cross-reference must not restate the referenced owner's procedure,
   structural contract, thresholds, or API surface.
3. A cross-reference must be reciprocal in meaning but need not be reciprocal
   in text; each leaf states the boundary from its own side.
4. Permitted cross-references are limited to: native lifecycle routed to a
   retained `go-test-profile`; structured or domain-sensitive comparison routed
   to a retained `go-cmp-test-profile` after selection; general Go semantics
   routed to `go-language-profile`; and all assertion, selection, command,
   flag, fallback, and policy questions routed to the target repository. When
   a named optional owner is unavailable, the cross-reference states the
   project-owned fallback rather than pointing to an absent skill.
5. A cross-reference that would only exist to coordinate two owners, rather
   than to place one contract, indicates a composition claim and must be
   raised as new ADR evidence rather than added.

## Version and source boundaries

| Owner | Calibration | Refresh condition |
| --- | --- | --- |
| `go-test-profile` | current supported Go 1.26.5 and 1.25.12 sources plus installed Go 1.25.10 compatibility evidence, the language-version specification, and build constraints | `testing` API, language-version rules, fuzzing or artifact behavior, caching, or false-escalation evidence changes materially |
| `go-cmp-test-profile` | google/go-cmp `v0.7.0` comparison, option, sorting, and equating sources | the selected release differs, or the option set, comparer obligations, transformer filtering, unexported handling, sorting or approximation contracts, or documented panics change |

The optional component profile treats a differing selected release as a **stop and
reverify** condition before any behavior claim, not as an assumption of
compatibility. The native profile distinguishes the module `go` directive, the
effective per-file language version, and the installed toolchain, and never
infers language semantics from the toolchain alone.

APG text is independently written. No upstream prose, code, example, table, or
diagnostic text is copied or adapted; factual API identifiers are used as facts.

## Project-owned inputs

These profiles never select, and always defer to the repository on: whether
the dependency exists and at what version; supported Go releases and
toolchain selection; the module `go` directive; package layout and test
placement; exact commands and flags; race, coverage, fuzz duration and corpus
retention, benchmark, and worker policy; platform and CI policy; timeouts,
fixtures, and temporary roots; live-service and destructive-action authority;
protected-data classification and redaction policy; artifact classification;
accepted exceptions; validation; and rollback.

A stricter project policy always wins over a profile default. A more permissive
project policy may relax only a profile default, through an accepted bounded
exception with an owner, evidence, adverse-case validation, a growth limit, a
refresh condition, and rollback. No exception relaxes a safety, privacy,
truthfulness, or authority stop.

## Overlap and conflict handling

One overlap is foreseeable and is resolved by rule, not by another owner:

- **Component versus native reporting.** Native testing owns the reporting
  mechanism, subtest structure, parallelism, and goroutine rules. A component
  owns only its own API's behavior within those rules. In particular,
  `go-cmp` owns comparison and diff-rendering behavior; native testing still
  owns how a test reports or withholds that diagnostic.

When two owners appear to give contradictory answers about the same part of one
test's observable contract, that is a finding to escalate to the maintainer and
to record as candidate composition evidence — not a case to resolve by inventing
a coordinating owner.

## Removal

Each leaf is removable through a candidate-independent mechanical operation.
Removing one requires
deleting its canonical leaf, checked flat projection, catalog row, capability-map
entry, current-development release-policy entry, strict inventory entry, focused
contract, and public scenario fixture, while preserving ADR, evaluation, and
exit history.

Because no composition owner exists, removal does not require a replacement
stack. It does require the same change to repair surviving cross-references and
state the retained owner or project-owned fallback. Removing native Go also
requires remaining component leaves to state that native lifecycle is
project-owned until a retained native owner exists. Removal never adds,
removes, or changes a target repository's dependency, and grants no execution
authority.

## Codex integration requirements

Before any candidate is retained, a later separately authorized Codex phase
must:

1. independently reverify every behavior claim against current primary sources,
   treating the APG37 leaves as evidence rather than as accepted procedure;
2. create public-safe executable fixtures from the frozen APG37 scenario
   families and establish failing-first evidence;
3. run pinned compatibility probes for the native lifecycle and for each
   selected component release;
4. independently review structural calibration for false escalation against a
   corpus it selects;
5. decide ADR 0026;
6. integrate only the candidates that pass, each beginning `provisional`, with
   projection, catalog row, general-router entry, release policy, and strict
   inventory added together;
7. verify that no `go-testing-stack` artifact, route, or subgraph appears; and
8. run proportional validation and reports within the currently authorized
   phase; retention never implies readiness, publication, deployment, or
   successor-phase authority.

## Falsification conditions

This specification is wrong, and must be revised or withdrawn, if any of the
following turns out to be true:

1. **The components are not independently useful.** If review finds that a
   component profile is never materially applicable without the native profile
   also being entered, the independent-triggerability claim fails and the split
   should collapse toward fewer owners.
2. **The boundaries do not hold in practice.** If ordinary tasks repeatedly
   produce contradictory answers between two owners about the same part of one
   test's contract, the no-composition decision is wrong and ADR 0026 must be
   reconsidered with that evidence.
3. **Version bounding is unworkable.** If repositories commonly select releases
   other than the calibrated ones, so that the component profiles stop and
   reverify more often than they answer, the version-bounded trigger is the
   wrong mechanism.
4. **The calibration is unstable.** If the categorical structural signals
   cannot be applied consistently by independent reviewers, or if they still
   escalate on ordinary maintained upstream test files, the structural contract
   is wrong regardless of the ownership decision.
5. **A component's facts are release-specific in a way the leaf cannot carry.**
   If the calibrated behavior changes across patch releases, a leaf pinned to a
   single release is the wrong unit and the capability belongs to project
   policy.
6. **Native ownership is insufficient.** If `go-test-profile` cannot state the
   native contract without restating `go-language-profile`, the owner boundary
   between language and test semantics is misplaced.

Each condition is intended to be checkable by a later phase against executable
evidence rather than by argument.
