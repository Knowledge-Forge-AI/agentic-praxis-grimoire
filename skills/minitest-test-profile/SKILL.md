---
name: minitest-test-profile
description: Use when Minitest-specific judgment is material to test or spec organization, assertions, lifecycle, mocks, stubs, fixture alternatives, isolation, parallelism, filtering, runners, plugins, reporters, subprocess, filesystem, or database test boundaries, or warning and crisis thresholds beyond repository policy.
---

# Minitest Test Profile

## Core principle

Apply Minitest-specific judgment only when the task materially depends on
Minitest. Establish the repository's Ruby, Minitest, mock, plugin, engine, and
platform versions before relying on runner behavior. Use the highest justified
`Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response for the current coherent decision.

Own Minitest test and spec organization, discovery, assertions and refutations,
setup and teardown, lifecycle extensions, random and parallel order, skips,
filtering, autorun, plugins, reporters, mocks and stubs, fixture alternatives,
test isolation, Minitest-specific effects around project-owned subprocess,
filesystem, and database boundaries, and Minitest-specific structural
warnings. Preserve repository authority and keep ordinary implementation,
general real-boundary truthfulness, and Ruby subprocess semantics with their
existing owners.

## Do not use

Do not use this profile for:

- ordinary Ruby implementation with no material Minitest behavior;
- RSpec-specific work when no Minitest boundary is involved;
- a simple assertion or test edit requiring no Minitest-specific judgment;
- choosing Minitest, a plugin, a Ruby version, a Minitest version, a mock
  library, a reporter, a coverage tool, or another dependency;
- framework selection or migration between test frameworks;
- selecting project test files, exact commands, worker counts, CI matrices,
  coverage thresholds, or support matrices;
- changing project-owned unit, integration, coverage, CI, or test-command
  policy;
- harness-neutral subprocess, filesystem, or database integration with no
  material Minitest behavior;
- generic planning, implementation, debugging, or review procedure;
- authorizing live services, host mutation, protected-data access, dependencies,
  destructive action, release, or publication;
- automatic restructuring of a legacy test tree; or
- structural action on generated, vendored, fixture, snapshot, migration,
  compatibility, or data-driven artifacts before classification.

## Procedure

1. Establish task authority and repository policy. Record the selected Ruby
   engine and version; Minitest, mock, plugin, and reporter versions; test
   roots and naming; exact project commands; serial or parallel policy;
   external-resource boundary; expected test inventory; coverage policy;
   validation; and rollback. This profile does not grant or choose them.
2. Classify each affected artifact as a maintained test owner, spec owner,
   helper, lifecycle extension, plugin, reporter, legacy artifact, generated
   case family, vendored source, fixture, snapshot, migration, compatibility
   matrix, or data. Classification never suppresses a semantic Red stop.
3. Verify discovery and truthfulness. Identify expected `test_` methods, spec
   examples, dynamically generated cases, load paths, filters, skips, and
   plugins. Compare expected and observed test identities or counts. Treat
   silent omission or an unexpected zero-test run as failure.
4. State the observable behavior each test must prove. Choose the most direct
   assertion or refutation whose failure demonstrates the relevant defect or
   contract violation. Test execution, assertion count, mock verification, or
   coverage alone is not proof.
5. Map setup, teardown, and lifecycle-extension ownership. Trace effective
   inheritance, `super`, ordering, mutation, failure cleanup, and resource
   restoration. Give shared state no broader lifecycle than the real resource
   contract requires.
6. Preserve randomized-order evidence. Reproduce an order-sensitive failure
   with the reported seed, identify the leaking state, and verify isolation.
   Do not convert the suite permanently to sorted execution and call the
   isolation defect fixed.
7. Before `parallelize_me!`, identify the executor and every thread-shared or
   worker-shared writable domain. Require per-test or per-worker namespaces,
   thread-safe subjects and support, complete reporting, observed failures,
   deterministic cleanup, and project-owned worker policy.
8. Evaluate fixture alternatives and boundary evidence only where Minitest
   behavior is material. Prefer per-test factories, helpers, temporary
   resources, or project-owned fixtures according to lifecycle, restoration,
   isolation, and discovery needs; do not select fixture architecture or a
   dependency. For subprocess, filesystem, database, service, or protocol
   tests, inspect only Minitest-specific collection, lifecycle, filtering,
   parallel, and reporter effects around the project-owned evidence.
   `implementing-with-test-discipline` retains real-versus-fake selection and
   integration truthfulness; `ruby-language-profile` retains Ruby process
   lifecycle, arguments, environment, status, and timeout semantics; repository
   policy retains filesystem and database isolation.
9. Establish mock ownership by version. Minitest 6 removed
   `minitest/mock.rb`; `Minitest::Mock` and `Object#stub` in that generation
   require the separately versioned `minitest-mock` gem. Verify meaningful
   expectations explicitly. Keep stubs block-bounded, target the method the
   subject resolves, establish restoration on failure, and avoid concurrent
   visibility of temporary method replacement.
10. Use skip and include or exclude filtering truthfully. A skip records no
    passing behavior. A focused filter is useful only when the intended tests
    are observed. Establish version-specific option names and aliases rather
    than assuming one release's CLI contract.
11. Inspect `Minitest.autorun`, after-run hooks, fork or subprocess behavior,
    prior exceptions, argument ownership, and exit status when process-exit
    execution is material. Do not register multiple competing run owners.
12. Treat plugins and reporters as execution behavior. Verify explicit loading,
    option processing, initialization, reporter composition, result
    completeness, failure propagation, output safety, shutdown, and exact
    compatibility. A custom progress display does not replace the summary or
    test-inventory contract.
13. Measure current and projected structure using repository tooling when
    present. Otherwise use the APG fallback rules below and label the result.
    Assign the highest structural or semantic level.
14. Proceed proportionally for Green; inspect policy and evidence for Yellow;
    require an accepted local decision, rationale, rollback, and focused
    validation for Orange; stop a Red false pass, omission, false integration
    claim, collision, leak, unsafe mutation, unsupported claim, or crisis-level
    growth.
15. Pair independently with the applicable process and language owners. An
    authorized behavior change can keep `implementing-with-test-discipline`
    primary and add `ruby-language-profile` and this profile only where their
    judgments are material. Acceptance can keep
    `reviewing-and-verifying-repository-work` primary.
16. Preserve stricter repository policy. Report the level, signals, versions,
    expected and observed tests, assertion evidence, lifecycle, seed and
    filter evidence, isolation, real boundaries, skips, plugin or reporter
    assumptions, exception if any, and rollback.

### Structural threshold contract

These defaults apply mainly to maintained hand-written Minitest test classes or
spec owners. They are guidance signals, not automatic enforcement,
architecture selection, dependency policy, or project test policy.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Physical lines per test owner | `<= 200` | `201–350` | `351–600` | `>= 601` |
| Test methods or spec examples per owner | `<= 12` | `13–24` | `25–40` | `>= 41` |
| Effective setup, teardown, or lifecycle-extension hooks per owner | `<= 2` | `3–4` | `5–6` | `>= 7` |
| Helper modules mixed into one test owner | `0` | `1` | `2` | `>= 3` |
| Mock or stub boundaries in one test | `<= 2` | `3–5` | `6–9` | `>= 10` |
| Shared mutable resource domains per test owner | `0` | `1` | `2–3` | `>= 4` |
| Parallel-worker shared writable domains per test owner | `0` | `1, isolated` | `2–3, isolated` | `>= 4`, or any unisolated collision |
| Custom test-owner inheritance depth | `0–1` | `2` | `3` | `>= 4` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |
| Generated or parameterized cases from one definition family | `<= 20` | `21–100` | `101–500` | `>= 501` |

Count physical lines after universal-newline decoding. Blanks, comments, DSL
lines, heredoc payload, and a final non-empty unterminated segment count.
Measure the smallest coherent maintained test owner supported by repository
tooling and disclose file context when multiple owners share one file.

Count runner-recognized `test_` methods or Minitest spec examples once before
plugin or data expansion. Dynamically defined tests count. Generated or
parameterized cases separately count the maximum concrete cases produced from
one definition family; silent omission is a semantic defect, not a lower count.

Effective hooks include test-author `setup` and `teardown` plus materially
effective `before_setup`, `after_setup`, `before_teardown`, and
`after_teardown` extensions. Repeated inheritance of the same effective hook
counts once at the leaf owner; independently ordered or overriding hooks count
separately. Lifecycle extension hooks are primarily for library integration,
not ordinary test setup.

Count one helper module when it is mixed into the test owner and adds
independently maintained helper or lifecycle behavior. Ordinary inheritance
from `Minitest::Test` does not count toward custom depth; count custom test-owner
edges between the leaf and that framework base. Disclose overlap when one
included or inherited behavior affects both counts.

Count one mock or stub boundary per independently replaceable collaborator,
symbol, method, environment family, or process seam. Repeated expectations on
one collaborator method remain one boundary unless they represent independent
seams. Count independently mutable or colliding resources such as a database,
port allocator, destination tree, process-global environment, service account,
or shared cache as domains. A unique per-test or per-worker instance is not
worker-shared. Responsibilities are independently changeable behavior or
external-contract families, not every context, assertion, helper, or data row.

Three materially coupled Yellow signals normally justify Orange. Two
materially coupled Orange signals affecting the same owner are presumptively
Red unless a cohesive-artifact rationale, repository acceptance, evidence,
validation, growth bound, and rollback justify retaining Orange. One Red signal
remains Red. Do not aggregate unrelated findings into a score.

An existing Red legacy owner may receive the smallest safe fix when it adds no
independent responsibility or meaningful structural growth and records a
decomposition or follow-up boundary. New responsibility remains Red.
Generated, vendored, fixture, snapshot, migration, compatibility, and data
artifacts retain their producer or project ownership. A cohesive generated
matrix can lower only a line-count response by one level; classification cannot
downgrade a semantic Red stop.

### Minitest semantic response guide

- A direct assertion or refutation is Green only when it observes the required
  outcome and can fail for the relevant defect. A vacuous predicate, swallowed
  assertion, unobserved subprocess result, or interaction check substituted for
  behavior is Red when it can false-pass a required contract.
- `Minitest::Test` discovers public instance methods beginning with `test_` in
  the inspected release. Minitest `describe` and `it` compile examples into
  test methods. Dynamic definition, inheritance, filtering, load-path mistakes,
  and plugins can change the observed inventory; verify identities or counts
  rather than inferring collection from file presence.
- In the inspected lifecycle, setup hooks and the test body run inside captured
  exception handling, followed by separately protected teardown hooks. Verify
  cleanup after setup, assertion, subject, teardown, interruption, and process
  failure. Teardown is an attempted lifecycle step, not proof that every
  resource was restored.
- Random order is evidence against hidden state. Preserve the reported seed,
  reproduce, minimize, and fix the leak. Sorted order can be a temporary
  diagnostic but cannot convert an order-dependent suite into passing evidence.
- `parallelize_me!` uses the configured Minitest parallel executor and runs
  test work in threads for the inspected release. Establish exact version and
  engine semantics. Thread-local test data does not isolate process-global
  environment, constants, class state, paths, ports, databases, caches,
  services, plugins, or reporters.
- Minitest mocks do not support multithreading in the inspected
  `minitest-mock` documentation. A mock or stub reachable by parallel work is
  Red until confined to one thread, replaced by a thread-safe test boundary, or
  excluded from parallel execution with project acceptance.
- `Minitest::Mock` expectations are verified, but interaction evidence does not
  prove observable behavior by itself. `Object#stub` temporarily replaces an
  existing method and restores it after the block. Wrong-target stubbing,
  excessive internal replacement, concurrent visibility, or failed restoration
  is Orange or Red according to false-pass and contamination risk.
- For subprocess, filesystem, or database tests, inspect Minitest-specific
  collection, lifecycle, filtering, parallel, and reporter effects around the
  project-owned evidence. General test discipline owns the real-versus-fake
  claim and treats a mocked or stubbed boundary represented as integrated as
  Red. Ruby guidance owns process lifecycle, arguments, environment, status,
  and timeout semantics. Repository policy owns disposable filesystem and
  database isolation and cleanup.
- A skip with a bounded reason reports no passing behavior. A required
  completion claim depending on a skip is Red. Include and exclude filters must
  prove that the intended cases ran; a convenient focused command cannot stand
  in for the repository-owned full boundary.
- `Minitest.autorun` registers process-exit execution once in the inspected
  release. Prior exceptions, `SystemExit`, forks, subprocesses, multiple
  libraries, and after-run hooks can affect ownership. Inspect exit behavior
  rather than assuming requiring the file proves a complete run.
- Minitest 6.0.6 uses opt-in plugin loading. Plugins can change options,
  reporters, and execution. Custom reporters join a composite lifecycle with
  start, record, report, and pass/fail behavior. Missing results, hidden
  failures, incomplete shutdown, unsafe output, or unsupported compatibility
  is Red.
- In Minitest 6.0.6, an unfiltered zero-test run can return success, while an
  unmatched include filter receives different handling. Required suites must
  compare observed collection with a repository-owned expectation. Unexpected
  empty collection or silent omission is Red regardless of process status.
- Seeds, names, failure diagnostics, captured output, reporter payloads,
  fixture values, paths, database identifiers, and service responses must not
  expose protected data. Actual leakage is Red and must be sanitized at the
  source before evidence is accepted.

### Source and maintenance boundary

This profile was inspected on 2026-07-23 against the MIT-licensed Minitest
6.0.6 tagged documentation and source, the MIT-licensed `minitest-mock` 5.27.0
extraction, RubyGems release metadata, and official Ruby 4.0.6 release and
licensing information. Minitest 6.0.6 declares Ruby 3.2 or later;
`minitest-mock` 5.27.0 declares Ruby 3.1 or later. These are calibration facts,
not selected project versions or a verified combination matrix.

Minitest 6 removed `minitest/mock.rb` from core, changed primary filtering
terminology, and made plugin loading opt-in. Refresh before a behavior-bearing
correction, maturity review, or publication when those boundaries, lifecycle,
spec, discovery, empty-run, parallel, reporter, plugin, mock, or supported-Ruby
semantics materially change. APG copies or adapts no source expression, code,
example, or table; this procedure is independently written synthesis.

Removal is candidate-independent. It must delete the leaf, flat projection,
catalog and capability-map entries, current-development release policy, strict
test inventory, focused test, and public scenario fixture while preserving
evaluation and exit history. The project-scoped projection owner and its
fixtures must remove only `minitest-test-profile`, preserve every other live
skill, and recompute all surviving skill, catalog, projection, route, fixture,
and test counts. Derive counts from the resulting live inventories; a raw
APG32 commit revert is not valid rollback because it would restore historical
counts and integration state. No private guidance was migrated, so rollback
restores none of it.

## Project-owned parameters

The target repository owns Ruby engines and versions; Minitest, mock, plugin,
reporter, Rails, Bundler, gem, and platform versions; framework selection and
dependencies; test layout, discovery roots, naming, filters, commands, worker
counts, seeds, CI, coverage, fixture architecture and dependencies, timeouts,
temporary roots, live-service and integration policy, expected test inventory,
supported combinations, artifact classification, accepted exceptions,
validation, rollback, protected data, external mutation, release, and
destructive-action authority.

## Evidence and completion

When material, report the Minitest profile level, structural and semantic
signals, exact version and engine basis, expected and observed test identities
or counts, assertions, skips, lifecycle and restoration, seed and filter
evidence, serial or parallel isolation, Minitest-specific effects around
project-owned integration-boundary evidence, mock and stub ownership, plugin
and reporter behavior, protected-output review, accepted exception if any, and
rollback. Green needs project checks. Yellow
needs focused inspection. Orange needs an accepted local decision and adverse-
case validation. Red records the stopped false pass, omission, collision,
misrepresentation, leak, unsupported claim, unsafe mutation, or growth and the
condition required before reconsideration.

## Stop or escalate

Stop or escalate when a required assertion can false-pass; expected tests are
silently omitted or an empty required suite is accepted; test state is
order-dependent or seed-sensitive without controlled isolation; a parallel
worker can collide or observe thread-unsafe state; a mocked or stubbed boundary
is represented as integrated; teardown or stub restoration cannot reliably
contain mutation; protected data can leak; Ruby, Minitest, mock, plugin, or
reporter support is unverified; a test can mutate destructive or consequential
external state without exact authority and disposable isolation; or meaningful
Red growth lacks decomposition or an accepted bounded exception.

## Common mistakes

- Triggering for ordinary Ruby work or a trivial test edit.
- Selecting Minitest, versions, plugins, commands, workers, or coverage policy.
- Assuming file presence or exit status proves the expected tests ran.
- Treating an unfiltered zero-test success as a passing required suite.
- Converting randomized tests to sorted order instead of repairing leaked
  state.
- Enabling `parallelize_me!` over shared writable or thread-unsafe resources.
- Assuming Minitest 6 still bundles mocks or that mocks are thread-safe.
- Taking ownership of generic process, filesystem, database, or service
  integration rather than pairing with its existing owner.
- Treating teardown, an at-exit hook, or a timeout as complete cleanup proof.
- Loading plugins or replacing reporters without exact compatibility and
  result-completeness evidence.
- Duplicating Ruby semantics instead of pairing `ruby-language-profile` when
  material.
- Using structure levels as permission, maturity, or automatic rewrite rules.
