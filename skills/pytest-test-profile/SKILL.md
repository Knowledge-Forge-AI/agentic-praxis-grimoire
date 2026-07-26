---
name: pytest-test-profile
description: Use when pytest-specific judgment is material to discovery, collection, assertions, fixtures, parametrization, mocks, isolation, xdist, coverage, or warning and crisis thresholds beyond repository policy.
---

# Pytest Test Profile

## Core principle

Apply pytest-specific judgment only when the task materially depends on pytest.
Establish the repository's Python, pytest, plugin, and coverage versions before
relying on runner behavior. Use the highest justified `Green — routine`,
`Yellow — caution`, `Orange — warning`, or `Red — crisis / stop` response for
the current coherent decision.

Own pytest discovery and collection, naming, markers, fixture scopes and
dependency graphs, autouse, parametrization, monkeypatching, mocks and fakes,
temporary paths, capture and logging, skip and xfail behavior, strictness,
plugin compatibility, xdist isolation, subprocess and filesystem fixtures,
unit and integration boundaries, coverage collection and aggregation, and
pytest-specific structural warnings. Preserve project authority and keep
ordinary implementation and Python semantics with their existing owners.

## Do not use

Do not use this profile for:

- ordinary Python implementation with no material pytest behavior;
- `unittest` or another test harness when no pytest boundary is involved;
- choosing pytest, a plugin, a Python version, a coverage target, a worker
  count, an exact command, or a universal dependency set;
- generic planning, implementation, debugging, or review procedure;
- changing project-owned unit, integration, smoke, or release boundaries;
- authorizing network, service, host, database, protected-data, destructive,
  or other consequential external access;
- a comment, spelling fix, mechanical rename, or assertion text edit with no
  material harness judgment;
- automatic restructuring of a legacy test tree; or
- structural treatment of generated, vendored, snapshot, compatibility,
  migration, or data artifacts before classification.

## Procedure

1. Establish task authority and repository policy. Record supported Python,
   pytest, plugin, coverage, and platform versions; configured collection
   roots; selected suites; parallel policy; coverage policy; external-resource
   boundary; and rollback. This profile does not grant any of them.
2. Classify each affected artifact as maintained test, helper, `conftest.py`,
   plugin, legacy, generated, vendored, fixture, snapshot, compatibility
   matrix, migration, or data. Classification never suppresses a semantic Red
   stop.
3. Verify discovery and collection ownership: roots, filename/class/function
   patterns, import mode, markers, configuration precedence, plugin loading,
   platform guards, deselection, and the expected collected node IDs. Treat a
   no-tests-collected result as failure unless the project explicitly owns a
   different contract.
4. State the observable behavior each test must prove. Use required assertions
   that fail for the relevant defect or contract violation. Do not accept test
   count, execution, coverage, or a mock assertion as proof by itself.
5. Map fixture ownership before choosing scope. Give a fixture no broader
   scope than the resource lifecycle and isolation contract require. Trace
   transitive dependencies, teardown order, hidden autouse reach, and failure
   cleanup. Remember that xdist workers have independent fixture caches.
6. Bound parametrization by meaningful behavior dimensions and inspect the
   actual generated collection. Prefer named cases and useful failure
   localization. Decompose accidental Cartesian explosion rather than hiding
   it behind collection or reporting options.
7. Choose real boundaries, fakes, mocks, or monkeypatching according to the
   claim. A unit test may replace an external command, network client, clock,
   nondeterministic source, destructive collaborator, or filesystem adapter
   when that boundary is not the subject. Exercise the subject's real logic.
   An integration test must use the real boundary it claims.
8. When monkeypatching, patch the name the subject resolves, scope restoration,
   and avoid pytest internals or Python builtins unless the need and recovery
   are explicit. Count independent replacement seams, not raw setter calls.
9. Use pytest temporary paths, capture, logging, skip, xfail, and marker
   facilities truthfully. Verify real metadata, link, atomic, process, or Git
   behavior when those semantics are the contract; a temporary path alone does
   not prove them. Capture exact stdout, stderr, return status, timeouts, and
   cleanup when subprocess behavior matters.
10. For xdist, identify every worker-shared writable resource. Select unique
    per-test, per-worker, or per-test-run namespaces; add explicit coordination
    only where one shared owner is required. Verify consistent collection,
    worker crash handling, complete results, and cleanup. A session-scoped
    fixture runs once per worker; pytest-xdist has no built-in exactly-once
    cross-worker session fixture.
11. For coverage, verify configured source ownership, branch mode, worker and
    subprocess collection, data-file identity, complete combination, missing-
    source diagnostics, and raw executed/total counts. pytest-cov may combine
    xdist worker coverage, while pytest-cov 7 delegates subprocess measurement
    to coverage.py patch configuration. Do not infer completeness from one
    displayed percentage.
12. Measure current and projected structure using repository tooling when
    present. Otherwise apply the APG fallback rules below and label the counts.
    Assign the highest justified structural or semantic level.
13. Proceed proportionally for Green; inspect policy and evidence for Yellow;
    require an accepted local decision, rationale, rollback, and focused
    validation for Orange; stop a Red false-pass, false integration claim,
    collision, leak, unsafe mutation, unsupported claim, or crisis-level
    growth.
14. Pair independently with the applicable process and language owners. An
    authorized behavior change can keep `implementing-with-test-discipline`
    primary and add `python-language-profile` and this profile only where their
    judgments are material. Acceptance can keep
    `reviewing-and-verifying-repository-work` primary.
15. Report level, signals, version and plugin assumptions, collection and
    assertion evidence, isolation and cleanup, coverage completeness,
    exception if any, and rollback.

### Structural threshold contract

These defaults apply mainly to maintained hand-written pytest owners. They are
guidance signals, not automatic enforcement, architecture selection, or
project coverage policy.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Test-file physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |
| Tests per file | `<= 12` | `13–24` | `25–40` | `>= 41` |
| Fixture definitions per file or local `conftest.py` owner | `<= 5` | `6–10` | `11–18` | `>= 19` |
| Maximum fixture dependency depth | `<= 2` | `3` | `4–5` | `>= 6` |
| Collected tests reached by one autouse fixture | `<= 10` | `11–30` | `31–100` | `>= 101` |
| Generated cases for one parametrized test definition | `<= 20` | `21–100` | `101–500` | `>= 501` |
| Mock or monkeypatch boundaries in one test | `<= 2` | `3–5` | `6–9` | `>= 10` |
| Shared mutable resource domains per test owner | `0` | `1` | `2–3` | `>= 4` |
| Worker-shared writable resource domains per test owner | `0` | `1, isolated` | `2–3, isolated` | `>= 4` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Measure physical lines after universal-newline decoding; blank and comment
lines count, and a final non-empty segment without a line ending counts once.
Count test definitions before parametrization for `Tests per file`, and count
the collected item expansion for `Generated cases`. A test method or function
counts once in the first measure even when it generates many items.

Fixture dependency depth is the maximum number of fixture-to-fixture edges
below a fixture directly requested by a test or activated through autouse.
Count built-in and third-party fixture dependencies only where they are visible
and material to the project contract; do not invent their undocumented
internals. Autouse breadth is the number of collected tests one fixture can
affect in the selected run.

Count one mock or monkeypatch boundary per independently replaceable symbol,
collaborator, environment family, or process seam. Repeated changes to the same
seam count once. Count independently colliding writable namespaces such as a
database, port allocator, destination path, process-global environment,
service account, or shared cache as resource domains. A unique per-test or
per-worker instance is not worker-shared.

Name independently changeable behavior or external-contract families for the
responsibility count. Helpers and fixtures serving one cohesive outcome do not
automatically add responsibilities.

Three materially coupled Yellow signals normally justify Orange.
Two materially coupled Orange signals affecting the same owner are
presumptively Red unless a cohesive-artifact rationale, repository acceptance,
evidence, validation, growth bound, and rollback justify retaining Orange.
One Red signal remains Red. Do not aggregate unrelated findings into a score.

An existing Red legacy test owner may receive the smallest safe fix when it
adds no independent responsibility or meaningful structural growth. Record a
decomposition or follow-up boundary. A new responsibility remains Red.
Generated, vendored, snapshot, migration, compatibility, and data artifacts
retain their producer or project ownership; their classification cannot
downgrade a semantic Red stop.

### Pytest semantic response guide

- Collection is evidence. Verify selected roots and node IDs, and fail on
  unexpected omissions, duplicates, collection errors, or exit code 5 for no
  tests collected. A selected platform guard may skip truthfully; it must not
  make an unsupported platform look verified.
- Plain assertions are useful only when the required condition can fail.
  Approximate comparison, exception, warning, and log assertions need explicit
  tolerances or match boundaries. A vacuous predicate, swallowed assertion,
  unawaited coroutine, or missing subprocess/result assertion is Red when it
  can false-pass a required contract.
- Use function scope by default unless a broader resource lifecycle is real.
  Wider fixtures can be efficient but need isolation, reset, failure cleanup,
  and order-independence evidence. Broad autouse is Orange when hidden coupling
  is material and Red when it permits a false-pass, contamination, or unsafe
  mutation.
- Parametrize behavior dimensions, not implementation trivia. Large but
  cohesive data-driven cases require a bounded rationale and useful failure
  identity. A generated-case Red remains Red without decomposition or an
  accepted bounded exception.
- A mock can isolate a boundary; it cannot prove that boundary. Mocking Git and
  calling the result Git integration, mocking a filesystem and claiming mode
  or atomic-replace behavior, or mocking a subprocess and claiming process
  lifecycle is a Red false representation. Use disposable real boundaries.
- `tmp_path` provides a per-test location, not a proof of ownership, mode,
  symlink, hard-link, atomicity, encoding, or cross-platform behavior. Exercise
  those semantics directly when claimed.
- Use skip for an inapplicable or unavailable supported condition. Use xfail
  for a known expected defect and strict xfail when an unexpected pass must be
  visible. Register markers and prefer strict marker/config behavior when the
  project adopts it.
- Under xdist, every worker collects tests and maintains its own fixture cache.
  Use worker identity for worker-local resources and test-run identity for
  run-wide namespaces. Shared exactly-once initialization needs tested
  interprocess coordination; fixture scope alone does not provide it.
- A worker crash is a test failure even when xdist restarts a worker. Configure
  restart policy at the project boundary and verify that all expected results
  and coverage fragments are present before accepting the run.
- Coverage is a contract signal, not a reason for brittle tests. Verify branch
  and statement ownership, source targets, subprocess configuration, parallel
  data combination, omissions, and warnings. Apply project thresholds to exact
  counts; do not game displayed rounding or average per-worker percentages.
- Sanitize captured streams, node IDs, parameter values, logs, tracebacks,
  reports, coverage paths, temporary paths, and retained artifacts. Protected
  data leaks are Red even when tests otherwise pass.
- A test can mutate real consequential state only with exact authority, target
  validation, isolation, cleanup, and recovery. Without them, stop.

### Source and maintenance boundary

This profile was inspected and calibrated on 2026-07-22 from pytest 9.1.1,
pytest-xdist 3.8.0, pytest-cov 7.1.0, coverage.py 7.15.2, and Python 3.14.6
documentation. pytest, pytest-xdist, and pytest-cov are MIT; coverage.py is
Apache-2.0; Python documentation is PSF-2.0 with examples additionally
available under 0BSD. APG copies or adapts no source expression or code; this
profile is independently written synthesis.

These versions are calibration evidence, not required project versions or
dependencies. Refresh affected guidance before a behavior-bearing correction,
maturity review, or publication when collection, assertion, fixture, plugin,
xdist, coverage, or supported-runtime behavior materially changes.

Behavior-bearing corrections follow the APG skill authoring and maintenance
guide. Deprecation or removal removes the canonical leaf, checked projection,
catalog and capability-map entries, and focused active tests while preserving
evaluation, provenance, and exit history.

## Project-owned parameters

The target repository owns:

- supported Python, pytest, plugin, coverage, and platform versions;
- framework and dependency selection, package and supply-chain policy;
- test roots, discovery patterns, markers, suites, commands, worker count,
  scheduling, timeouts, retries, and CI behavior;
- unit, integration, system, smoke, external-service, and release boundaries;
- statement, line, branch, source-target, exclusion, and rounding policy;
- fixtures, test data, generated artifacts, snapshots, compatibility matrices,
  and accepted structural exceptions;
- external resources, protected data, cleanup, retention, and reporting;
- architecture, validation, rollback, mutation, release, publication, and
  destructive-action authority.

Stricter project policy controls. APG's future eight-worker and 80/80/85
coverage policy is a project-owned example, not a universal pytest default.
No local exception weakens a superior safety, privacy, compatibility, or task-
authority stop.

## Evidence and completion

When material, report:

```text
Pytest profile level: Green | Yellow | Orange | Red
Versions and plugins: <selected Python, pytest, xdist, coverage, and plugins>
Signals: <structure, fixtures, mocks, resources, collection, or coverage>
Behavior claim: <observable assertion and real or replaced boundaries>
Isolation: <test, worker, run, cleanup, and external-resource evidence>
Coverage evidence: <source, branch, worker/subprocess completeness, raw counts>
Required response: <normal, inspect, redesign/decompose, or stop>
Rollback: <exception, fixture, test-owner, or configuration rollback>
```

Green normally needs supported-version awareness and focused project checks.
Yellow adds local lifecycle, collection, or replacement-boundary evidence.
Orange adds an accepted design, adverse-case validation, growth bound where
relevant, and concrete rollback. Red records the stopped claim or action, the
false-pass, collision, leak, authority, compatibility, or growth defect, and
the exact condition required before reconsideration.

## Stop or escalate

Stop or escalate when:

- a test can mutate real consequential state without authority or isolation;
- mocked behavior is represented as integrated;
- an xdist collision can corrupt or cross-contaminate results;
- a required assertion can false-pass;
- protected data leaks through test input, capture, logs, paths, reports, or
  coverage artifacts;
- unsupported plugin or runtime behavior is represented as verified;
- collection, worker, result, or coverage evidence is incomplete but would be
  accepted as passing;
- cleanup, timeout, child-process, or shared-resource ownership is unresolved;
  or
- crisis-level test-owner growth lacks decomposition or an accepted exception.

## Common mistakes

- Treating every Python test edit as pytest-profile work.
- Choosing pytest, plugins, versions, workers, commands, or coverage thresholds
  for the project.
- Assuming fixture scope equals cross-worker singleton ownership.
- Using autouse to conceal required dependencies.
- Counting decorators instead of generated parametrized items.
- Mocking the subject's behavior or the boundary claimed as integrated.
- Treating `tmp_path`, test execution, or a coverage percentage as proof by
  itself.
- Ignoring no-tests-collected, worker-crash, source-omission, or incomplete-
  combination outcomes.
- Adding brittle implementation-trivia assertions solely to execute lines.
- Letting one sub-threshold signal hide a semantic Red stop.
- Forcing unrelated restructuring of an existing Red legacy test owner.
- Describing a collision, false-pass, leak, or authority crisis while allowing
  the proposed action to continue.
