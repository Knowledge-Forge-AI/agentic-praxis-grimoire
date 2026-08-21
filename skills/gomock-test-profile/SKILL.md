---
name: gomock-test-profile
description: Use when a project has already selected GoMock v0.6.0 and judgment is material to mockgen generation, generated mocks, controller lifecycle, expectations, call counts or order, matchers, or GoMock failure diagnosis; not for native test lifecycle, value diffs, or Go semantics.
---

# GoMock Test Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

Apply GoMock-specific judgment only after the repository has selected
`go.uber.org/mock` v0.6.0 and the current decision materially depends on
`mockgen`, generated mocks, a `Controller`, expectations, call counts or
ordering, matchers, actions, or GoMock-owned failure output. A different release
requires source revalidation before a release-sensitive conclusion.

Own the mock component only. Native test lifecycle remains with
`go-test-profile`; value comparison and diff construction remain with
`go-cmp-test-profile`; interface and language semantics remain with
`go-language-profile`. These owners are direct, independently selectable
siblings. No stack owner or mandatory invocation chain exists.

Use the highest justified `Green — routine`, `Yellow — caution`,
`Orange — warning`, or `Red — crisis / stop` response for one coherent
GoMock decision. A warning never supplies dependency, generation, mutation, or
release authority.

## Do not use

Do not use this profile for:

- deciding whether to adopt GoMock, `mockgen`, or any mocking dependency;
- native `go test` placement, table-driven tests, subtests, helpers, cleanup,
  parallelism, fuzzing, caching, or package lifecycle;
- value equality, structured diffing, or go-cmp option behavior;
- Go interface design, type identity, assignability, generics, concurrency, or
  other language semantics;
- generic test sufficiency, implementation sequence, planning, debugging, or
  review procedure;
- selecting Go, GoMock, generator, command, flag, package layout, coverage, CI,
  or generated-code policy; or
- authorizing dependency changes, host mutation, network access, publication,
  deployment, or destructive regeneration.

When an optional sibling is unavailable, route its surface to explicit
project-owned policy. Naming another owner places a boundary; it does not invoke
that owner or restate its procedure.

## Procedure

1. Establish task authority, repository policy, the exact selected
   `go.uber.org/mock` and `mockgen` versions, supported Go versions, package
   layout, generated-code classification, generation command owner, exact
   checks, protected-data policy, and rollback.
2. Classify each mock as generated, maintained, vendored, fixture, snapshot, or
   legacy. Generated output is changed through its evidenced generator; do not
   hand-edit it merely because the generated form is inconvenient.
3. Bind generation provenance: source, package, and archive mode inputs; exact
   interface set; destination and package; import and auxiliary-file inputs;
   typed-output choice; build constraints; generator version; and reproducible
   command or project-owned equivalent. Treat generation success as output
   production, not as compile or test success.
4. Inspect one controller's ownership and lifetime. Each test owner normally
   creates its own controller. When the reporter supports cleanup, controller
   construction registers final expectation checking. Under v0.6.0, that
   cleanup path silently tolerates a later duplicate `Finish`; without cleanup
   support, a repeated `Finish` is a hard failure. Avoid an explicit `Finish`
   when registered cleanup already owns completion so the lifetime has one
   clear owner.
5. Inspect every expectation's method, argument matchers, return or action,
   minimum and maximum count, prerequisite or sequence, override behavior, and
   diagnostic consequence. Unordered calls remain unordered unless
   `InOrder` or `After` states a dependency.
6. Check matcher truthfulness. A custom matcher must accept exactly the intended
   argument domain, be deterministic, avoid unsafe side effects, and render a
   bounded non-secret expectation. Formatting adapters improve diagnosis but do
   not change the match contract unless the wrapped matcher does.
7. Separate GoMock diagnosis from adjacent failures: unexpected or missing calls,
   count exhaustion, prerequisite failure, matcher mismatch, generator drift,
   Go compilation, native test reporting, and subject value differences have
   different owners.
8. Assign the highest response below. Proceed proportionally for Green; inspect
   version and regeneration evidence for Yellow; require a bounded accepted
   design and adverse-case checks for Orange; stop Red false-pass, unsafe
   mutation, nondeterminism, exposure, or unowned generation.
9. Pair independently with the applicable process skill. A behavior change may
   keep `implementing-with-test-discipline` primary while this profile supplies
   only GoMock judgment.

### Response model

| Level | GoMock condition | Required response |
| --- | --- | --- |
| Green — routine | pinned generation provenance, isolated controller, explicit deterministic expectations | run focused generation or test checks owned by the project |
| Yellow — caution | version-sensitive mode, regeneration drift, broad matcher, flexible count, or diagnostic-format dependence | inspect exact source, generated diff, and local policy |
| Orange — warning | shared controller, generated public surface, custom matcher/action with consequential effects, expectation override, or broad regeneration | require an accepted bounded design, adverse cases, rollback, and generated-diff review |
| Red — crisis / stop | required calls can false-pass, controller lifetime is unowned, generation inputs are unknown, matcher behavior is nondeterministic, repeated `Finish` can hard-fail, or protected data can enter diagnostics | stop until ownership, truthfulness, safety, and rollback are restored |

Counts are semantic contracts, not style. `Times` states an exact count;
`AnyTimes` permits zero; `MinTimes` and `MaxTimes` can alter the opposite
bound under v0.6.0 rules. Use only the flexibility the observable contract
allows. Do not add ordering merely to mirror implementation order; do require it
when order is itself observable.

Actions such as `Do`, `DoAndReturn`, `Return`, and `SetArg` participate
in the fake boundary. They cannot prove the real collaborator. A mocked boundary
must not be described as integration evidence.

### Generation and maintenance boundary

`mockgen` v0.6.0 supports source, package, and archive generation modes. Mode
selection is project-owned and must follow the actual input and build boundary.
Generated placement must avoid import cycles, preserve package visibility, and
remain reproducible from recorded inputs. A generated header is classification
evidence, not proof that current bytes match current interfaces.

Regeneration is a source-to-derived-state migration. Review additions,
removals, renamed methods, imports, package names, typed helpers, build
constraints, and call sites. A clean generator exit does not authorize or prove
acceptance of the resulting diff.

### Source and maintenance boundary

This profile was independently written from the upstream Uber GoMock v0.6.0
README, changelog, `mockgen` sources, and `gomock` package documentation and
source. The repository is Apache-2.0 licensed. APG copies no upstream prose,
code, example, table, or diagnostic text; factual API identifiers and behavior
are used as facts.

Refresh before a behavior-bearing correction, maturity review, or publication
when the selected release changes, generation modes or flags change, controller
cleanup or concurrency changes, call-count coupling changes, matcher or action
semantics change, or documented failure behavior changes.

Removal is candidate-independent. Remove the canonical leaf, projection,
catalog and capability-map entries, current-development release-policy entry,
strict inventory row, focused tests, and public scenario fixture; repair
surviving cross-references to the retained owner or project-owned fallback; and
preserve ADR, evaluation, exit, and provenance history. Removal never changes a
target repository's dependency or generated mocks.

## Project-owned parameters

The target repository owns whether GoMock is selected; exact module and
generator versions; supported Go versions and platforms; interface and package
layout; generation mode, command, flags, destinations, `go:generate` policy,
generated-file classification, review, and retention; test commands, race,
coverage, fuzz, benchmark, worker, CI, timeout, and retry policy; matcher and
diagnostic conventions; protected-data rules; accepted exceptions; validation;
rollback; dependency mutation; release; publication; deployment; and
destructive-action authority.

Stricter repository policy controls. No local exception weakens a superior
safety, privacy, truthfulness, compatibility, or task-authority stop.

## Evidence and completion

When material, report the exact GoMock and generator versions, generation mode
and inputs, artifact classification, controller owner and lifetime, expectation
and matcher contract, response level, generated diff or freshness evidence,
focused checks, replaced versus real boundaries, protected diagnostic handling,
exception if any, and rollback. Distinguish static inspection, generated output,
mocked tests, compilation, and executed integration evidence.

Green needs project checks. Yellow adds exact version and regeneration evidence.
Orange adds an accepted bounded design, adverse-case validation, and concrete
rollback. Red records the stopped false-pass, unsafe generation, exposure, or
ownership defect and the condition required before reconsideration.

## Stop or escalate

Stop when the selected release or generator identity is unknown for a
version-sensitive claim; generated provenance is missing; a required call can
be accepted as optional; expectation ordering encodes an unsupported contract;
a controller or reporter lifetime cannot be bounded; completion ownership is
unclear or repeated `Finish` can hard-fail for a reporter without cleanup; a
matcher or action is nondeterministic or mutates unowned state; generated
output would be edited directly or destructively replaced without authority
and rollback; protected values can reach failure output; mocked behavior is
represented as integrated; or an unsupported release is represented as
verified.

## Common mistakes

- Selecting GoMock because an interface or test exists.
- Treating a generator command, generated header, clean compile, and passing
  test as interchangeable evidence.
- Sharing one controller across unrelated test owners.
- Calling `Finish` redundantly after registered cleanup already owns completion.
- Using `AnyTimes` or broad matchers to silence a missing contract.
- Adding call order that merely mirrors the implementation.
- Treating matcher formatting as value comparison or redaction.
- Hand-editing generated mocks instead of the authorized generator input.
- Calling a mocked collaborator real integration evidence.
- Inventing dependency, version, command, policy, or mutation authority.
