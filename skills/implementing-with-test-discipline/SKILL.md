---
name: implementing-with-test-discipline
description: Use when implementing a bugfix, new behavior, behavioral refactor, schema or contract change, or another code change whose correctness benefits from executable evidence.
---

# Implementing with Test Discipline

## Core principle

Make behavioral evidence proportional to risk and distinguish exploratory
learning from a completed change.

## Do not use

Do not use this skill for pure prose or formatting edits, read-only diagnosis,
an unresolved design, or work whose implementation is not authorized. Do not
impose a universal red-green ritual when executable behavior is unchanged or a
different evidence form is more appropriate.

## Procedure

1. Confirm the authorized behavior, preserved contracts, risk class, and
   repository-owned verification policy.
2. Inspect existing tests and current behavior before changing implementation.
3. For a bug, reproduce the defect before fixing it when practical. For a
   refactor, preserve baseline tests or characterization evidence. For new
   behavior, establish the intended observable outcome before or alongside the
   implementation.
4. Select the smallest useful evidence layer: focused unit behavior, connected
   integration behavior, contract or migration checks, or another project-
   accepted executable signal.
5. Implement the narrowest coherent change. Remove locally owned code or test
   artifacts whose only purpose ended because of the authorized change when
   repository policy and removal authority are clear. Keep unrelated cleanup
   and new abstractions outside the slice.
6. Run focused feedback while iterating, then execute the proportional final
   gate from the integrated resulting state.
7. Treat exploratory spikes explicitly: bound them, avoid completion claims,
   and either remove or clean them before final verification.
8. Record evidence actually observed, checks not run and why, remaining risk,
   and any behavior intentionally deferred.

Mechanical or documentation-only portions of a mixed change use their
applicable checks; they do not justify skipping evidence for the behavioral
portion.

### Coverage remediation and test scope

Distinguish a behavior or test failure from a coverage-only failure. Repair
behavior, collection, completeness, and source-target defects before expanding
tests for coverage. When correct tests pass but a project-owned gate fails,
inspect exact per-file statement and branch counts and the complete maintained-
source inventory rather than displayed rounding or aggregate percentages.

Expand only while a useful observable contract exists, in this order:

1. current-task behavior;
2. adjacent behavior affected by the change;
3. the same maintained module;
4. its package and subpackages; and
5. a justified parent package.

At each layer, keep unit isolation proportional and exercise the real boundary
for any integration claim. Stop and request project disposition when the
complete suite-owned surface is exhausted, the gate still fails, and no useful
observable contract remains. Record the exact deficit and the layers examined.

Do not add tests only to execute lines, assert private implementation order,
duplicate an existing contract, or replace subject behavior with mocks. Inspect
an incomplete source target, dead or unreachable code, and any proposed
exclusion. Remove dead code only within authority. Exclude generated,
platform-inapplicable, intentionally unreachable, or defensive code only when
the project accepts an explicit rationale and owner. Never change denominators,
thresholds, branch mode, source inventory, exclusions, or rounding merely to
make the gate pass.

Preserve the scoped-test default: run focused unit evidence and changed-
boundary integration evidence first. Do not broaden to combined, full, smoke,
readiness, or release suites unless a focused result, project checkpoint, or
explicit manager requirement justifies that smallest broader gate.

## Project-owned parameters

The project owns test levels, commands, coverage policy, mock and fixture
rules, database or service boundaries, generated-file treatment, acceptable
manual evidence, and release gates. Use those parameters without inventing
universal thresholds.

## Evidence and completion

Completion requires evidence tied to the changed behavior and fresh final
verification against the resulting state. A passing focused test alone does
not establish broader compatibility, and an unexecuted test plan is not test
evidence.

## Stop or escalate

Stop when intended behavior is unresolved, safe reproduction is unavailable
and mutation would be speculative, required infrastructure or authority is
missing, the change exposes a new issue class, or the project gate cannot be
run and no authorized substitute exists.

## Common mistakes

- writing a test that passes before it can demonstrate the intended delta;
- testing implementation details instead of behavior without a contract need;
- treating mocks, coverage, or test count as proof by themselves;
- retaining spike shortcuts in the finished change;
- broad cleanup during a behavioral slice; and
- reporting only passing checks while hiding skipped or failed evidence.
