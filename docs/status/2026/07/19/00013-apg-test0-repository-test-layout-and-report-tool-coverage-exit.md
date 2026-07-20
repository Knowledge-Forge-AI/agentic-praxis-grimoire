# APG-TEST0 Repository Test Layout and Report-Tool Coverage Exit

## Phase identity

- **Phase:** APG-TEST0
- **Date:** 2026-07-19
- **Exit sequence:** `00013`
- **Disposition:** Complete — test ownership and layout established
- **Terminal result:** `test-layout-complete`

## Authority and objective

APG-TEST0 authorized a bounded repository test-ownership change. The phase
establishes the `src/test/unit/<language>` and `src/test/int/<language>`
convention, adds behavior-focused Bats tests for both APG report commands, and
migrates the existing project-skill Python suite into the integration layout.

The accepted report formats, command interfaces, shared helper behavior,
project-skill behavior, skill content, maturity model, dependency model, and
publication boundary remain unchanged.

## Resulting test layout

The repository now owns:

- `src/test/unit/bash/git-show-report.unit.test.bats`;
- `src/test/unit/bash/append-operational-report.unit.test.bats`; and
- `src/test/int/python/apg_project_skills.int.test.py`.

The Bats suites cover 22 behavior families across exact record construction,
hash and framing boundaries, input validation, Git commit forms, path handling,
private permissions, unsafe destinations, failure atomicity, concurrent
appends, duplicate records, and multi-project concatenation. Their expectations
use the canonical Agent report envelope and shared helper.

The migrated Python suite preserves all 28 project-skill integration families.
Only its repository-root resolution and path changed.

## Documentation and provenance

The README records the test-level directories, filename suffixes, framework
requirements, and direct suite commands. The APG7A provenance destination now
points to the migrated integration test. Historical exit records remain
unchanged.

No package manager, dependency manifest, generalized test runner, or coverage
gate was introduced.

## APG skill decisions

- `planning-repository-work` applied to the dependent inventory, baseline,
  migration, test-porting, documentation, verification, and publication units.
- `implementing-with-test-discipline` applied because the phase adds executable
  regression evidence and changes test discovery paths.
- `reviewing-and-verifying-repository-work` applied to the complete resulting
  state and terminal claims.
- `designing-significant-changes` was a material non-trigger because the
  maintainer supplied the test layout, ownership transfer, and phase identity.
- `debugging-systematically` was a material non-trigger because baseline and
  migrated suites exposed no unexplained failure.
- `composing-bounded-worker-assignments` was a non-trigger because no internal
  delegation was authorized or used.

No Superpowers skill was invoked or followed.

## Validation

Fresh validation from the resulting repository state established:

- 22 of 22 report-tool Bats tests passed;
- 28 of 28 project-skill Python integration tests passed;
- Bash syntax passed for both report commands and their shared helper;
- both report commands returned successful help output;
- the documented unit and integration paths matched repository test discovery;
- public Markdown headings, fences, local links, and confidentiality passed;
- the exit sequence was contiguous through `00013`; and
- both Git whitespace checks passed.

The phase changes no report implementation or project-skill implementation, so
no executable behavior delta required a source correction.

## Limitations and deferrals

- The Bats suites require Bats 1.5.0 or newer plus ordinary Bash, Git, and
  platform command-line utilities.
- The phase does not establish statement or branch coverage measurement.
- The phase does not add a unified repository test entrypoint.
- Cross-platform behavior beyond the existing Darwin and GNU compatibility
  branches remains unclaimed.

## Next authorization

APG-TEST0 is complete after one APG commit and push. It authorizes no report
format or implementation change, dependency manifest, test-runner abstraction,
coverage gate, workflow-skill maturity change, publication, release, or
successor phase automatically.
