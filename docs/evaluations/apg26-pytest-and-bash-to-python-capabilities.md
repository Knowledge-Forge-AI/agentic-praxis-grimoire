# APG26 Pytest and Bash-to-Python Capabilities

Phase ID: `APG26`

## Outcome

Complete — pytest and Bash-to-Python capabilities implemented provisionally.

| Candidate | Disposition | Behavior-bearing corrections | Current source basis |
| --- | --- | ---: | --- |
| `pytest-test-profile` | `retained-provisional` | 0 | pytest 9.1.1, pytest-xdist 3.8.0, pytest-cov 7.1.0, coverage.py 7.15.2, Python 3.14.6 documentation |
| `converting-bash-scripts-to-python` | `retained-provisional` | 1 | Python 3.14.6 documentation, current Git CLI documentation, GitPython 3.1.54 option analysis, current APG reporting architecture and read-only report family |

Both candidates satisfy the APG new-skill threshold: each owns one coherent
reusable problem not already covered end to end; has a precise trigger and
material non-triggers; preserves task and project authority; is independently
removable; has current source and rights evidence; and passes positive,
non-trigger, edge, stop, integration, and fresh-review gates.

## Pytest ownership and source boundary

`pytest-test-profile` owns materially pytest-specific judgment about discovery,
collection, naming, markers, fixtures and dependency graphs, autouse,
parametrization, monkeypatching, mocks and fakes, temporary paths, capture and
logging, skip and xfail behavior, strictness, plugin compatibility, xdist
isolation, subprocess and filesystem fixtures, unit/integration claims,
coverage collection and aggregation, and pytest structural warnings.

It does not select pytest or plugins, dependencies, Python versions, worker
counts, coverage thresholds, exact commands, test levels, or external action.
Generic implementation and review remain with their process owners. Python
semantics remain with `python-language-profile`. Project policy, including
APG's planned eight-worker and 80/80/85 coverage gates, controls over the
profile's defaults.

The source calibration was inspected on 2026-07-22. pytest, pytest-xdist, and
pytest-cov are MIT; coverage.py is Apache-2.0; Python documentation is PSF-2.0
with examples additionally available under 0BSD. APG uses independently
written synthesis and copies no upstream expression or code. These versions
are evidence, not target requirements.

## Pytest structural contract

| Signal | Green | Yellow | Orange | Red |
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

The profile defines physical-line, test-definition, collected-case, fixture-
depth, autouse-reach, replacement-seam, resource-domain, and responsibility
fallback counts. Three materially coupled Yellow signals normally justify
Orange. Two materially coupled Orange signals are presumptively Red unless an
accepted cohesive exception supplies evidence and rollback. One Red remains
Red. Classified and legacy artifacts retain proportional treatment, but no
classification suppresses a semantic stop.

The required Red stops cover unauthorized or unisolated consequential state,
mocked behavior represented as integrated, xdist collision or contamination,
false-passing required assertions, protected-data leakage, unsupported plugin
or runtime claims, incomplete collection/result/coverage evidence, and crisis-
level growth without decomposition or accepted exception.

## Pytest scenarios

All thirty frozen scenario families match the retained profile. They cover the
clear trigger; ordinary Python and non-pytest non-triggers; simple behavior;
fixture scope and autouse; useful and exploding parametrization; appropriate
and excessive mocks; truthful and false integration claims; temporary paths;
real Git; subprocess timeout/capture; xdist isolation, collisions, and worker
failure; no collection; skip/xfail; behavior assertions; brittle coverage-only
tests; source omission; exact threshold counts; process/language/profile
pairing; stricter policy; unsupported versions; protected output; and
destructive external authority.

Notable controls are that pytest exit code 5 does not pass an empty suite; a
session-scoped fixture is per xdist worker rather than globally once; worker
restart does not turn a crash into success; integration evidence uses the real
claimed boundary; and coverage completeness requires source, worker,
subprocess, combination, omission, warning, and exact-count evidence rather
than one displayed percentage.

## Bash-to-Python ownership and source boundary

`converting-bash-scripts-to-python` owns the bounded procedure for converting
an existing Bash executable or coherent script family to Python while
preserving or deliberately migrating its observable contract. Its nineteen-
step procedure covers authority and goal; interpreters and platforms; CLI and
help; standard streams; exit codes; environment and locale; cwd and paths;
file modes, ownership, and links; atomicity and locking; signals and cleanup;
subprocess vectors; Git semantics; protected data; characterization;
Python module and entry-point design; wrapper retention/removal; compatibility
rollout; rollback; and documentation/release projection.

It does not mandate conversion, own generic Bash/Python guidance, choose
dependencies or GitPython, add platform support, or authorize unrelated work,
cutover, release, or deletion. The migration owner pairs with the Bash and
Python profiles when their language judgments are independently material and
with the applicable implementation or review process owner.

The source calibration was inspected on 2026-07-22. Python documentation is
PSF-2.0 with examples additionally available under 0BSD; Git has a GPL-2.0-only
source boundary; GitPython 3.1.54 is BSD-3-Clause. Its 2026-07-22 security
release hardens unsafe Git option validation, reinforcing the fixed-vector
standard-library and Git CLI baseline. GitPython is a permitted future option,
not an adopted dependency. APG copies no upstream expression or code.

Fresh conversion-safety review applied the candidate's one behavior-bearing
correction. Executable and option tokens must remain fixed or trusted;
untrusted operands require validation and an end-of-options boundary where the
selected interface supports it without changing the preserved contract.
Disabling shell interpretation alone does not prevent argument or option
injection, and an unresolved injection path is a stop. The correction changes
no adapter selection, dependency, target report tool, or migration authority.

## Bash-to-Python scenarios and stops

All thirty frozen scenario families match the retained skill. They cover a
small portable utility; a clearer retained shell pipeline; no invented Windows
goal; exact public CLI behavior; sourced libraries; traps; append locks;
atomic replacement; modes/owners/links; fixed Git vectors; dynamic shell
construction; root and merge commits; binary and rename diffs; whitespace and
non-ASCII paths; Windows behavior; signals; partial failure; timeouts;
protected data; stdout consumers; wrappers and direct replacement; standard-
library Git CLI and GitPython options; unjustified dependencies; missing
characterization; equivalent and intentionally changed behavior;
process/Bash/Python pairing; and the trivial-new-Python non-trigger.

The skill stops for insufficient current characterization; unclear migration
authority or platforms; unresolved exact CLI/report compatibility; shell,
argument, or option injection; protected-data exposure; weakened file, lock,
or atomic behavior; approximated rather than verified Git semantics;
unresolved signal/process lifecycle; missing sourced-library or stream
migration; absent rollback; or an unrelated rewrite needed to claim
completion.

## Read-only report-tool dogfood

The candidate maps the current reporting family without changing it:

- `bin/git-show-report` is 313 lines and Bash line-count Orange;
- `bin/append-operational-report` is 240 lines and Bash line-count Yellow;
- `libexec/agent-report/common.sh` is 281 lines and Bash line-count Yellow,
  with 22 named functions also Yellow;
- the Git-show Bats owner is 493 lines/14 tests, Orange/Yellow; and
- the operational-report Bats owner is 324 lines/9 tests, Yellow/Green.

The future design separates a report model, section renderer, record envelope,
safe destination/locking owner, Git show and diff adapters, operational-body
adapter, thin CLIs, and optional compatibility wrappers. Fixed Git CLI argument
vectors remain the baseline because the contract exposes exact Git revision,
diff, quoting, rename, binary, configuration, byte, and status behavior.
GitPython currently demonstrates no bounded advantage that justifies its added
dependency and abstraction surface.

Existing Bats tests provide substantial POSIX characterization but do not
complete a cross-platform migration gate. A later phase still needs signal and
child-process cases, platform-specific file/lock/entry behavior, exact byte and
encoding cases, temporary-index diff cases, associated operational-record
cases, and old/new parity. APG26 changes none of these tools or tests.

## Integration and rollback

Private development contains 21 canonical direct-child skills, 21 catalog
rows, 21 relative checked-in projections, 14 stable rows, 7 provisional rows,
and 20 routable non-router capability-map entries. The capability map remains
sorted. Each new leaf has one matching provisional row and relative projection.

Rollback removes the two leaves, projections, catalog rows, routes, and active
focused assertions; restores the current checker expectation to 19/19/19; and
updates current documentation while preserving historical evaluation,
provenance, review, and exit records. Public and active v0.3.0 require no
rollback because the new candidates never enter those surfaces.

## Validation, review, and boundary

Failing-first focused contracts initially pass the sixty-scenario record check
and fail for the absent leaves and routes. The resulting six-method focused
APG26 contract file, affected integration checks, mechanical skill-library
checker, Python compilation, Bash syntax, Markdown/link/privacy/identity/
whitespace gates, and fresh pytest, conversion-safety, overlap/integration,
and complete-diff reviews accept the resulting state. No complete repository
suite is run; APG26 is not a readiness or release checkpoint.

Public and active v0.3.0 remain unchanged. The personal APG router remains
decommissioned, the three personal hygiene skills remain present, and APG26
does not convert a report tool, implement `git-diff-report`, migrate a pytest
suite, move a ChatGPT skill, implement a later profile, publish v0.4.0, or begin
a successor phase.

## Subsequent correction — APG26A

APG26A later identified that APG26's formal-phase commit preserved only the
subject and omitted the body required by ADR 0020 and the structured project
defaults. The historical commit is not amended or rewritten. APG26A corrects
forward by adding deterministic precommit and postcommit message validation.
This process correction does not change either APG26 capability disposition,
the single conversion-safety correction, scenario results, routing, maturity,
skill content, or distribution outcome.
