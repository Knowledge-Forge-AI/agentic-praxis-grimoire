---
name: go-test-profile
description: Use when native Go test judgment is material to package placement, subtests, helper attribution, cleanup and isolation, TestMain, parallelism, goroutine reporting, examples, benchmarks, fuzzing, caching, effective language version, or warning and crisis thresholds beyond repository policy.
---

# Go Test Profile

## Core principle

Apply native Go test judgment only when the task materially depends on the
`testing` package or `go test` behavior. Establish the repository's module
`go` directive, effective per-file language version, and selected toolchain
before relying on any version-sensitive semantics. Use the highest justified
`Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response for the current coherent decision.

Own test package placement, tests and subtests, helper attribution, fatal and
nonfatal reporting, cleanup and isolation, `TestMain`, parallelism, goroutine
reporting boundaries, examples, benchmarks, fuzzing, selection and caching.
Leave general Go structure, errors, context, interfaces, generics, and
concurrency design to `go-language-profile` when those semantics are
independently material.

## Do not use

Do not use this profile for:

- ordinary Go implementation or review with no material test-specific decision;
- general Go semantics already owned by `go-language-profile`;
- choosing whether to adopt an assertion or comparison dependency;
- assertion-library behavior after selection, owned by project-owned assertion
  policy unless a retained version-bounded owner exists;
- go-cmp comparison behavior after selection, owned by
  `go-cmp-test-profile` when that retained owner is available, otherwise by
  explicit project policy;
- generic implementation, debugging, planning, or review procedure;
- selecting Go releases, commands, flags, race, coverage, fuzz duration,
  benchmark, worker, platform, or CI policy;
- authorizing live services, host mutation, credentials, or destructive action;
- a typo, comment, rename, or test edit with no test-specific judgment; or
- structural judgment of generated, vendored, fixture, snapshot, or
  data-driven artifacts before classification.

## Procedure

1. Establish task authority, repository policy, module `go` directive,
   effective file language version, selected toolchain, package layout, test
   placement, exact checks, and rollback.
2. Classify the artifact as maintained test, helper, legacy, generated,
   vendored, fixture, snapshot, or data. Classification never suppresses a
   semantic Red stop.
3. Determine what each test must prove and whether the evidence is static,
   unit, or integration. Mocked behavior is never integration evidence.
4. Inspect placement and visibility, subtest naming and selection, helper
   attribution, fatal and nonfatal reporting, cleanup and resource lifetime,
   temporary directory, environment and working-directory isolation,
   `TestMain`, parallelism, goroutine reporting, examples, benchmarks, fuzz
   surfaces, and caching.
5. Assign the highest level justified by a concrete risk in the structural
   contract below. Coupled signals may explain one higher-level risk, but their
   count never manufactures Orange or Red. One semantic Red remains Red. Do
   not aggregate unrelated findings.
6. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an accepted local design, rationale, rollback, and focused
   validation for Orange; stop a Red false-pass, leak, unsafe mutation,
   exposure, or crisis-level growth.
7. Pair independently with a process skill and, only when material, with
   `go-language-profile` or a selected component profile. A behavior change can
   keep `implementing-with-test-discipline` primary; a test review can keep
   `reviewing-and-verifying-repository-work` primary.
8. Preserve stricter repository policy. Relax only a profile default through
   accepted scope, rationale, evidence, validation, and rollback; never relax a
   superior safety, privacy, truthfulness, or authority stop.
9. Report level, signals, version assumptions, evidence class, isolation and
   cleanup evidence, exception if any, and rollback.

### Effective language version

The selected toolchain is not the language version. The module `go` directive
establishes the module version, while a file constraint naming a Go release can
establish a different effective file version under the current language rules.
For a module at Go 1.21, for example, a `go1.22` file constraint can select
Go 1.22 semantics for that file. A vendored or generated file can therefore
have different semantics from a neighbouring file.

Route general language-version consequences to `go-language-profile`. Retain
the test-specific consequence: from language version `go1.22`, each `for`
iteration has its own iteration variables. Table-driven subtests and parallel
subtests that capture the loop variable therefore behave differently across the
boundary. Establish the effective version from the module and file rather than
from the installed toolchain. Asserting capture behavior from the toolchain
alone is Red.

### TestMain

`TestMain` runs on the main goroutine, and `flag.Parse` has not run when it is
called. The generated test binary calls `TestMain(m)` and then exits with the
runner's recorded exit code, so a normal return propagates the recorded result
without an explicit `os.Exit`. Distinguish three cases:

- **Normal package lifecycle.** `TestMain` performs setup, calls `m.Run`, and
  lets the recorded result propagate. A project may instead call `os.Exit`,
  but that ends the process without running deferred functions, so all
  required cleanup must already have occurred. Green or Yellow.
- **Intentional package-level suppression or custom result.** A package may
  deliberately return without running its tests, or exit with a project-chosen
  code. The recorded exit code defaults to zero, so a package that never runs
  its tests still reports success. This is exceptional, project-owned behavior
  that requires an explicit accepted rationale, and the result must never be
  described as evidence that the package's tests ran. Orange.
- **Missing or accidental `m.Run`, or a hardcoded success code.** The binary
  reports success while the package's required tests never executed. Red
  false-pass and omitted-test stop.

The API does not universally require calling `m.Run`. The truthfulness contract
does: never state that package tests ran or passed unless they did.

### Goroutine and reporting boundary

`FailNow`, `Fatal`, `Fatalf`, `SkipNow`, `Skip`, `Skipf`, and `Parallel` must be
called only from the goroutine running the test function. The `Log` and `Error`
variants may be called simultaneously from multiple goroutines. A test also ends
when its function returns, so reporting after that point is unsafe.

There is no universal rule that every goroutine must be joined. Apply a bounded
truthfulness contract instead:

- no goroutine may let required behavior false-pass;
- a result-bearing goroutine must deliver its required result and the test must
  check that result before the owner returns;
- a resource-owning goroutine must complete or be cancelled, with release
  confirmed before the owner returns;
- a goroutine that is genuinely independent of the result and owns nothing the
  test must release may outlive the test when the repository accepts it;
- a fatal or skip call from a non-test goroutine is Red;
- project policy may require stricter joining, and stricter policy wins.

### Cleanup and isolation

Registered cleanup functions are unwound in reverse registration order after
the test and its descendants finish. A per-test temporary directory is removed
by the framework after that owner completes. Environment and
working-directory helpers restore prior process state through cleanup, and
because both affect the whole process they cannot be used in a parallel test or
a test with a parallel ancestor. Treating either as parallel-safe is Red.

Confirm release of every process, port, environment change, and external
object. Unexpected, unauthorized, unbounded, or privacy-unsafe persistence is
Red. A retained test artifact that the repository explicitly authorizes,
minimizes, and bounds is not automatically Red; record its owner and removal
policy. On toolchains that provide `ArtifactDir`, retention still depends on
the selected artifact policy and flags.

### Benchmarks

Separate measured work from setup and teardown. The supported benchmark loop
form depends on the selected toolchain and project support floor, not merely on
the effective file language version. In particular, use `B.Loop` only after
confirming that the selected standard library provides the behavior the
benchmark expects. Exact commands, repetitions, time, memory reporting, and
performance acceptance remain project-owned.

### Fuzzing

Keep these surfaces distinct:

- **Setup and seed registration.** `F` methods may be called only before the
  fuzz target is provided. Seed entries come from `F.Add` and from the fuzz
  test's directory under `testdata/fuzz`.
- **Target execution.** The target receives a `*T` followed by supported input
  types. Use the test object for target reporting; only the documented fuzz
  queries remain valid through the fuzz owner. Each invocation must produce a
  repeatable result from its arguments, avoid mutable cross-invocation state,
  and leave the supplied input storage untouched after return.
- **Coverage corpus.** Inputs that expand coverage can be retained under the
  fuzz cache. They are engine-owned search material and are not automatically
  part of ordinary test execution.
- **Failures and replay.** A failing input is written under
  `testdata/fuzz/<Name>` only when writable; otherwise it is retained in the
  fuzz cache. Package seed files are replayed by ordinary test runs. Cache
  entries and repository seed files are different artifact classes and need
  separate retention, review, and cleanup policy.

Fuzz duration, worker count, and corpus retention are project-owned. Classify
generated and persisted inputs before use. Stop Red when protected data would
cross an unauthorized boundary or an input could cause an unauthorized
destructive effect; generation alone is not a crisis.

### Structural threshold contract

Measured against maintained small, medium, large, parallel, and
integration-heavy Go repositories as well as the Go toolchain corpus,
absolute file size and test-function count do not predict ownership or
truthfulness risk: routine, well-maintained test files in that corpus reach many
hundreds of lines and dozens of test functions. Numeric size cutoffs are
therefore not used as crisis signals here, and a large but coherent test file
is not by itself a finding.

Apply these categorical conditions to the actual maintained lifecycle owner.
That can be one `_test.go` file, a cross-file suite, or a package-wide owner
governed by `TestMain` or package-global state. Include every helper and fixture
that participates in the claimed lifecycle.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | --- | --- | --- | --- |
| Responsibility mixing | one or more isolated, attributable families | related families with a shared, documented setup | independent families sharing mutable setup with concrete attribution work | failures cannot be attributed to an owner |
| Shared mutable state | none beyond one test | one documented package-level or fixture domain | state reached across unrelated tests with concrete isolation work | state makes results order-dependent without accepted isolation |
| Parallel resource domains | none shared | owned and isolated domains | contention bounded only by timing or incomplete isolation | unsafe sharing, or process-wide mutation under parallelism |
| Helper indirection | attribution reaches the failing contract directly | one helper layer marked as a helper | layered helpers that relocate attribution | attribution that points away from the failing contract |
| `TestMain` breadth | absent, or one setup outcome | two outcomes with explicit ordering | independent outcomes with separate failure and rollback contracts | package result cannot be reported truthfully |
| External-resource breadth | none | provisioned and released resources with local ownership | shared lifetime or attribution requiring accepted design | lifetime, authority, or rollback cannot be bounded |

Treat a responsibility family as one independently accepted behavioral outcome
with its own change and rollback lifecycle, not one per test function. Treat a
shared mutable domain when behavior reads or mutates a package-level variable,
shared fixture, global registry, process environment, working directory, or
shared file; state fully isolated to one test is not a risk signal. An external
family remains attributable when it is independently provisioned, authorized,
and released.
Expand statically bounded table data into concrete cases when judging
attribution, and disclose correlated table and subtest fan-out without stacking
it as independent findings.

Separate the subject under test from the harness. An expected panic, assertion
failure, misattribution, or unsafe operation that the harness deliberately
contains and verifies is evidence about the subject, not automatically a
defect in the maintained test owner. Escalating on size or family count alone
is a defect. Every Orange or Red must name the concrete ownership,
truthfulness, safety, or maintainability risk.

Classify generated, vendored, fixture, snapshot, and data-driven artifacts
before structural action. An existing Red legacy owner may receive the smallest
safe authorized fix that adds no independent responsibility and records a
decomposition boundary; new responsibility remains Red.

### Source and maintenance boundary

This profile was corrected on 2026-07-25 against Go 1.26.5 and Go 1.25.12
`testing` and `cmd/go` sources, the language-version and build-constraint
references, the installed Go 1.25.10 compatibility toolchain, and a bounded
public structural corpus. Go source and source-derived package documentation
are BSD-licensed; general go.dev site prose is separately licensed. The
procedure is independently worded and uses factual API identifiers.

Refresh before a behavior-bearing correction, maturity review, or publication
when the `testing` API, the generated test main's result propagation,
language-version rules, fuzzing behavior, caching, artifact retention, or
representative false-escalation evidence materially change. Removal is
candidate-independent but must delete the canonical leaf, checked projection,
catalog and capability-map entries, current-development release-policy entry,
strict inventory entry, focused tests, and public fixture. It must also repair
surviving cross-references with the retained owner or project-owned fallback
while preserving ADR, evaluation, and exit history.

## Project-owned parameters

The repository owns supported Go releases and toolchain selection, the module
`go` directive, package layout and test placement, exact commands and flags,
race, coverage, fuzz duration and corpus retention, benchmark policy, worker
count, platform and CI policy, timeouts, fixtures, temporary roots, live-service
policy, artifact classification, accepted exceptions, authority, validation, and
rollback.

## Evidence and completion

When material, report the profile level, structural and lifecycle signals,
module and effective language-version assumptions, evidence class, attribution
and isolation evidence, cleanup and goroutine bounding, exception if any, and
rollback. Distinguish static or mocked evidence from executed evidence, and
name every check that was not run. Orange requires an accepted local design and
focused adverse-case evidence. Red records the stopped false-pass, leak, unsafe
mutation, exposure, or growth and the condition required before reconsideration.

## Stop or escalate

Stop or escalate when required tests are omitted or can false-pass; a
`TestMain` result is misrepresented, including a package that reports success
without running its tests; effective language semantics are assumed from the
toolchain alone; a helper or goroutine boundary cannot report truthfully;
cleanup or resource lifetime is unbounded; parallel state is unsafe; order,
time, randomness, or cache behavior is uncontrolled while a deterministic result
is claimed; a fuzz-generated or persisted corpus entry crosses a protected-data
or destructive boundary; mocked behavior is described as integration evidence;
unsupported release, flag, or API behavior is represented as verified; or
crisis-level ownership lacks decomposition or an accepted bounded exception.

## Common mistakes

- Treating ordinary Go work as native-test-profile work.
- Stating that the API requires `TestMain` to call the runner, or assuming a
  package that exits zero actually ran its tests.
- Reading loop-variable or other language semantics from the installed
  toolchain instead of the effective module and file version.
- Requiring every goroutine to be joined instead of bounding result and
  resource ownership.
- Calling a fatal or skip method from a goroutine the test started.
- Using the environment or working-directory helper in a parallel test.
- Conflating the fuzz setup surface, the fuzz target, generated inputs, and the
  persisted seed corpus.
- Treating a persisted fuzz failure as transient rather than reviewed source.
- Reporting a cached result as a fresh execution, or an empty selection as a
  passing suite.
- Escalating on file size or test count alone.
- Inventing project commands, flags, versions, or action authority.
