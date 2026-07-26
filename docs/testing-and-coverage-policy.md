# Testing and Coverage Policy

## Scope and ownership

This document owns APG's project testing defaults and adopted pytest, xdist,
coverage, inventory, and runner architecture. It does not select a test
framework or coverage policy for another project or authorize a dependency,
test expansion, readiness gate, or release outside the current task.

Framework-specific pytest judgment belongs to the provisional
`pytest-test-profile`. General implementation sequencing remains with
`implementing-with-test-discipline`. APG29 makes that process skill the
executable owner for the coverage-remediation model below and aligns planning
and review without changing project-owned thresholds or suite policy.

## Ordinary scoped-test default

An ordinary implementation phase runs:

- scoped unit tests for changed unit behavior; and
- scoped integration tests only when the changed contract crosses an
  integration boundary.

It does not run a combined suite, automated smoke/system suite, or complete
repository suite by default. A manager assignment references this default
rather than restating it.

Broader testing is justified only when:

- the phase changes testing infrastructure;
- the phase is a readiness, pre-release, or release checkpoint;
- CI/CD owns the broader gate;
- a reproduced defect requires the minimally broader scope;
- repository policy requires it; or
- the human or manager explicitly requests it within authority.

For APG, complete-suite execution belongs at pre-release smoke and release
preparation, not every implementation phase.

## Coverage-remediation decision model

Coverage is a contract signal. It is not permission to add brittle tests or to
exercise lines without a useful assertion.

When a required suite misses its statement or branch gate:

1. Inspect behavior changed by the current task and add reasonable,
   non-brittle tests for meaningful untested contracts.
2. If the gate still fails, inspect behavior adjacent to the current task.
3. Then inspect the same edited modules or files.
4. Then inspect the same package and subpackages.
5. Then inspect parent packages one level at a time.
6. Continue only while a real, useful, untested contract exists.
7. Stop for human input after the complete suite-owned source surface has been
   considered and the required gate still fails.

At every expansion:

- do not add a test solely to execute a line;
- do not assert implementation trivia or duplicate an existing contract test;
- do not overmock the behavior being claimed;
- do not retain dead or unreachable code merely for coverage;
- inspect whether the source target or exclusion policy is wrong;
- require accepted rationale for generated, platform-inapplicable,
  intentionally unreachable, or defensive exclusions; and
- compare exact counts rather than gaming rounded display values.

APG29 freezes coverage-failure cases and verifies this expansion and stop
behavior before accepting `implementing-with-test-discipline` as the executable
procedure owner.

## Mocks, fakes, and real boundaries

### Unit tests

Mocks, fakes, or monkeypatching are appropriate for external commands, network
clients, clocks and nondeterminism, OS adapters, process launch, expensive or
destructive collaborators, and filesystem behavior when filesystem semantics
are not the unit contract. The unit should still execute its real decision
logic. Mocking each internal call makes the test a duplicate of implementation
structure rather than a behavioral contract.

Pytest's `monkeypatch` fixture safely restores changed attributes, mappings,
environment variables, paths, and current directories after the requesting
test or fixture. Patch the reference used by the subject and keep the patch
scope narrow; the [pytest monkeypatch guidance](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
also warns that patching pytest's own standard-library dependencies can break
the harness.

### Integration tests

An integration test uses the real boundary it claims:

- a real disposable Git repository for Git semantics;
- a real temporary filesystem for path, mode, rename, link, and atomicity;
- a real subprocess when process behavior is the contract; and
- real report assembly when envelope and append behavior are the contract.

A mock may stand in for a boundary outside the test's stated scope or one that
is unsafe or unavailable. The test must then describe the integrated boundary
narrowly and must not represent the mocked collaborator as integrated.

## Accepted APG pytest architecture

APG uses the APG28A-adopted stack:

```text
pytest
pytest-xdist
pytest-cov backed by coverage.py branch measurement
default local worker count: 8
```

APG28A selects and locks pytest 9.1.1, pytest-xdist 3.8.0, pytest-cov 7.1.0,
and coverage.py 7.15.2 as development-test dependencies after compatibility,
process-accounting, and coverage gates pass. They are project choices, not
universal defaults.

### Coverage transport decision

Use pytest-cov as the default xdist coverage transport. Its
[distributed-testing guidance](https://pytest-cov.readthedocs.io/en/latest/xdist.html)
documents coverage of local and remote workers and combined reporting, while
its [overview](https://pytest-cov.readthedocs.io/en/stable/readme.html)
documents automatic data-file erase/combine behavior and the requirement that
workers have the plugin installed.

For each suite, create a fresh run-nonce data root, set a suite-specific
`COVERAGE_FILE`, enable branch measurement, and run pytest-cov under xdist.
Reject pre-existing, stale, or unexpectedly named data before combination.
Retain the unit and integration data sets separately. Build the combined result
with an explicit coverage.py data combination in a fresh temporary directory
after accounting for every expected input. Treat an unreadable or skipped input
and every combine warning as failure. Coverage.py documents parallel data and
combination; see
[`coverage combine`](https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html)
and [reporting](https://coverage.readthedocs.io/en/latest/commands/cmd_reporting.html).

Pytest-cov 7 removed its own subprocess-start mechanism and directs projects to
coverage.py's patch support. For every suite whose contract launches Python
children, the selected default therefore configures `[run] patch = subprocess`
in the shared coverage configuration. That patch enables parallel data. Child
processes must receive the same source, branch, context, and data-root
configuration and terminate through a supported clean path; an abrupt or
unaccounted process is incomplete evidence. See the current
[pytest-cov subprocess guidance](https://pytest-cov.readthedocs.io/en/latest/subprocess-support.html)
and [coverage.py subprocess guidance](https://coverage.readthedocs.io/en/latest/subprocess.html).

Direct coverage.py parallel collection without pytest-cov remains a bounded
fallback only when a characterized process boundary cannot work through the
selected pytest-cov/controller path. It has the same nonce, process accounting,
clean-termination, readability, and strict-combine requirements. A custom
aggregation plugin is rejected as the default because the supported
combination already exists and custom code would own more failure modes.

### Test roots and path mirror

Python tests live under:

```text
src/test/unit/python/agentic-praxis-grimoire/
src/test/int/python/agentic-praxis-grimoire/
```

Below the hyphenated path-mirror directory, each test mirrors the production
path and uses `.unit.test.py` or `.int.test.py`:

```text
bin/git-show-report
src/test/int/python/agentic-praxis-grimoire/bin/git-show-report.int.test.py

libexec/agent_report/rendering.py
src/test/unit/python/agentic-praxis-grimoire/libexec/agent_report/rendering.unit.test.py
```

The hyphenated directory is a collection and ownership boundary, not an
importable Python package. Production modules receive valid Python package
names where imports are needed; path-mirror tests may load executable adapters
through a bounded helper.

`bin/apg-test` requires one declared production owner per mirrored test path,
rejects duplicate or stale mirror paths, and lists intentionally unmirrored
tests. APG28A accepts the migration only after legacy Python test locations are
empty or explicitly retained by an accepted exception.

APG27 does not perform that pytest or path-mirror migration. Its focused
standard-library tests remain in the current `src/test/unit/python` and
`src/test/int/python` roots. The existing 23 Bats contracts continue to own
entry-point compatibility, failures, permissions, append, and contention. The
focused Python unit contracts own models, rendering, record parsing, state IDs,
and lexical safety. Real disposable-repository integration contracts own
private-index diff behavior, drift and interruption cleanup, association, and
concurrency. A phase-only parity harness accepts an explicitly supplied frozen
pre-conversion tool root and compares exact compatible report bytes; it skips
when that conversion evidence is not supplied.

APG27A corrects and adopts the report core without changing this test layout,
adding pytest dependencies, or moving a test. APG28 separately owns the
authorized pytest, xdist, coverage, and mirrored-path migration.

APG28 stops Partial with its candidate preserved. APG28A corrects and adopts
the migration without changing the accepted scoped-test or real-boundary rules.

### Suite gates

The unit suite must:

- collect at least one test;
- pass;
- reach at least 80% statement coverage; and
- reach at least 80% branch coverage.

The integration suite has the same independent 80% statement and 80% branch
gates. The combined runner fails if either component suite fails, or if the
union of their executed coverage data is below 85% statements or 85% branches.
The combined value is a data union, never an average of suite percentages.

Threshold validation uses integer counts from coverage JSON. For a threshold
`T`, require `covered * 100 >= T * total` independently for statements and
branches. Display rounding cannot change the result. A zero branch denominator
is reported explicitly and passes only when the configured source inventory
truthfully contains no measurable branches; it cannot hide an omitted source
target. A zero statement denominator is likewise an explicit source-inventory
failure unless an accepted inventory genuinely contains no measurable
statements; APG's ordinary executable source cannot silently pass that case.

### Collection and isolation controls

The runner:

- invoke exactly one configured test root per component suite;
- register and enforce strict unit and integration markers;
- treat pytest exit code 5, no tests collected, as failure, consistent with the
  [pytest exit-code contract](https://docs.pytest.org/en/stable/reference/exit-codes.html);
- reject collected nodes outside the selected suite root or with the wrong
  suite marker;
- compare collected node IDs to detect duplicates;
- verify the configured production source inventory before testing and compare
  it with the coverage report afterward;
- fail when an expected source file is omitted unexpectedly;
- create a fresh suite data root and reject every stale, foreign, duplicate,
  unreadable, or unexpected coverage artifact;
- create per-run and per-worker resource namespaces;
- set xdist's maximum worker restart count to zero so a crash is not obscured
  by a replacement worker; and
- require a successful controller result and complete worker-finish evidence
  before accepting coverage.

Worker completion alone is insufficient. The migration must implement one
reviewed accounting mechanism that relates each started worker and expected
Python child process to incorporated coverage data—for example, nonce-bound
worker/process manifests plus coverage contexts or a non-threshold-bearing
sentinel. The runner compares collected and executed node IDs, worker/process
manifests, pre-combine data inputs, the combined readable data set, and reported
contexts. A missing expected payload, unexpected payload, stale nonce, combine
warning, or context disagreement fails before any 80/80/85 threshold check.

Pytest-xdist supplies `worker_id` and `testrun_uid` for unique resources, as
documented in its [worker-identification guidance](https://pytest-xdist.readthedocs.io/en/stable/how-to.html).
Its [crash behavior](https://pytest-xdist.readthedocs.io/en/latest/crash.html)
restarts workers by default, so APG disables restart for deterministic failure
and incomplete-data detection.

Shared ports, paths, repositories, lock files, databases, and environment
variables must be isolated by test-run and worker identity or be deliberately
serialized. Fixture scope does not make a resource cross-worker singleton.

### Platform behavior

Platform-specific tests declare their supported platform and reason. A skip on
one platform is not evidence for that platform's behavior. Required release
platforms must each collect their applicable tests in CI or a recorded
readiness gate. An unsupported platform-specific import must produce an
explicit skip or collection failure; silent omission is rejected.

## APG28 stopped candidate

APG28 evaluates the architecture through an uncommitted `bin/apg-test`, exact pinned test
dependencies, mirrored Python roots, and `testing/apg-test-inventory.json`.
The runner defaults to eight workers and exposes `unit`, `integration`, and
`unit-integration`.

Every maintained Python source must appear in coverage JSON and participate in
the component and union denominators. Fresh review rejected the first candidate
because it excluded 12 of 17 sources from every gate. The bounded correction
restored the full inventory, after which the candidate failed honestly.

The corrected unit evidence is 1,850/4,623 statements and 554/1,774 branches.
The integration candidate is 3,682/4,623 statements and 1,180/1,774 branches,
with four test failures. The measured union is 4,056/4,623 statements and
1,410/1,774 branches. The architecture remains future work until the exact
80/80 component and 85/85 union gates and completeness contracts pass.

## APG28A adopted implementation

APG28A preserves APG28's stopped measurements and adopts the corrected
implementation. Combined mode attempts both valid components and aggregates
their failures. Invocation-scoped manifests prove worker start, collection,
terminal results, completion, node-down, and required Python-child coverage
contribution. Missing, duplicate, foreign, stale, wrong-run, incomplete, and
crash evidence fails before coverage acceptance.

Artifacts are invocation-owned, removed after success, and removed after
failure unless explicit bounded retention is requested. Current v0.4 configured
release validation directly invokes every required Bats and mirrored pytest
owner in a sanitized environment. It does not trust a caller-controlled
recursion guard; nested release fixtures remain bounded by their explicit test
policy. Historical v0.2.0 and v0.3.0 policy remains immutable. Both Bats owners
remain because their complete shell-boundary replacement was not proven.
