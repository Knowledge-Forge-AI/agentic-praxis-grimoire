# APG32 Minitest Test Profile

## Objective and disposition

APG32 evaluates one bounded new-skill candidate:
`minitest-test-profile`. The candidate owns materially Minitest-specific
judgment without selecting the framework, dependencies, versions, project
commands, worker counts, coverage thresholds, CI policy, or external-action
authority.

The lifecycle evidence supports provisional retention subject to the terminal
fresh-review gate. No consequential project decision requires ADR 0025.

## Current source and rights

Primary sources were inspected on 2026-07-23:

- Minitest 6.0.6 tagged repository source, release history, runner, test owner,
  spec owner, README, and RubyGems metadata;
- the separately extracted `minitest-mock` 5.27.0 tagged repository source,
  documentation, and RubyGems metadata; and
- official Ruby 4.0.6 release and licensing information.

Minitest and `minitest-mock` are MIT-licensed. Ruby is available under the Ruby
License or two-clause BSD, subject to file-specific terms in `LEGAL`. APG uses
these versions as calibration evidence, not project requirements or a universal
compatibility matrix. The profile is independently written synthesis and
copies or adapts no upstream prose, code, examples, or table structure.

The calibration identifies two required version boundaries. Minitest 6 removed
core `minitest/mock.rb`, so mock and stub guidance must establish the separate
gem when that generation is in use. An unfiltered Minitest 6.0.6 run with zero
tests can return success, so a required suite must verify its expected
inventory rather than treating exit status as collection proof.

## Ownership and scenarios

The profile triggers only when Minitest-specific test or spec organization,
assertions, lifecycle, mocks or stubs, isolation, parallelism, filtering,
autorun, plugins, reporters, fixture alternatives, Minitest-specific effects
around subprocess, filesystem, or database tests, or structure materially
controls a decision.
Ordinary Ruby, RSpec-only work, simple harness-neutral tests, framework
selection, dependency selection, project commands and thresholds, generic
implementation, generic review, and harness-neutral boundary tests remain
non-triggers. General test discipline retains real-boundary truthfulness, Ruby
guidance retains subprocess semantics, and repository policy retains
filesystem and database isolation.

Thirty-six frozen families cover the required positive, non-trigger, lifecycle,
assertion, isolation, parallel, integration, mock, stub, skip, filter, autorun,
reporter, plugin, empty-run, version, privacy, project-policy, structure,
authority, pairing, and framework-selection outcomes. A mirrored unit contract
failed first before the candidate existed and passes against the integrated
candidate.

## Structural contract

The profile supplies Green/Yellow/Orange/Red fallback signals for physical
lines per test owner, test methods or spec examples, effective lifecycle hooks,
mixed-in helper modules, mock or stub boundaries, shared mutable domains,
parallel-worker writable domains, custom test-owner inheritance, independent
responsibilities, and generated or parameterized cases.

The thresholds follow APG test-profile and Ruby-profile precedent while using
Minitest-specific ownership definitions. Required Red stops remain semantic:
false-passing assertions, uncontrolled order or seed dependence, worker
collision, thread-unsafe parallel work, false integration claims, protected-
data leakage, unsupported version or plugin claims, silent omission or empty
required collection, unauthorized destructive mutation, and crisis-level
undecomposed ownership.

## Integration

The retained development shape is:

- 23 canonical skills, 23 catalog rows, and 23 flat projections;
- 14 stable and 9 provisional rows;
- 21 general-router entries, including the Minitest profile and the
  ChatGPT-manager subrouter;
- 1 ChatGPT-local entry; and
- 22 checked route edges in total.

The current-development release policy, release validator, and strict test
inventory include the new leaf, projection, scenario fixture, and mirrored
contract. Public and active v0.3.0 remain unchanged at 19/19/19.

## Candidate correction and validation

The candidate uses one behavior-bearing correction. Fresh review required
fixture alternatives and Minitest-specific effects around subprocess,
filesystem, and database tests to be explicit while returning generic
real-boundary truthfulness, Ruby subprocess semantics, and repository isolation
to their existing owners. The correction updates the leaf, route, catalog, and
focused contract as one coherent boundary change. It does not change a frozen
scenario outcome.

Two earlier focused test assertions were narrowed to the candidate's
already-present code-span and conjunction wording; neither changed candidate
behavior or a frozen outcome. The focused test also reads its executable
scenario contract only from the public fixture; private evidence explains that
contract but is not required by the public candidate.

Validation covers the failing-first and passing mirrored contract, skill
library, router and catalog, exact projection, release policy, strict inventory,
affected unit and integration selections, current and public-v0.3 checkers,
Python compilation, Markdown and links, privacy and durable identity,
whitespace, and a disposable current-development candidate without
publication. Readiness, smoke, release, and publication suites remain outside
APG32.

## Rollback and future boundary

Rollback removes the canonical leaf, flat projection, catalog row, general-map
entry, current-development release-policy and validator entries, inventory row,
focused test, scenario fixture, and current-surface test expectation together
while preserving this evaluation and the exit history. No private guidance was
migrated.

No phase after APG32 is authorized. Remaining test or platform profiles,
readiness, compatibility remediation, and v0.4.0 release work require separate
maintainer authority.
