# APG28 Pytest Suite and Coverage Migration Exit

Phase ID: `APG28`

Status date: 2026-07-22

Disposition: Partial — migration candidate preserved but not adopted

## Scope and outcome

APG28 produced an uncommitted Python test-infrastructure candidate. ADR 0024
remains Proposed. The candidate includes one APG-owned runner, strict source
and mirror inventory, exact component and union arithmetic, and a proposed
retirement of the report-tool Bats suites.

The runner provides `unit`, `integration`, and `unit-integration`, defaults to
eight xdist workers, disables worker restarts, measures Python subprocesses,
and combines component coverage data by union. Fresh review rejected the first
denominator because it excluded most maintained sources. One bounded correction
placed all maintained sources in every component and union gate.

## Validation

The corrected unit run passed 152 tests but measured 1,850/4,623 statements and
554/1,774 branches. The integration candidate measured 3,682/4,623 statements
and 1,180/1,774 branches, with 188 passed, 5 skipped, and 4 failed
release-policy tests. The measured union reached 4,056/4,623 statements and
1,410/1,774 branches. Unit 80/80, integration 80/80, and union 85% branch
requirements did not pass.

Three fresh reviews found material denominator, subprocess-accounting,
worker-crash, coverage-artifact, count-validation, and Bats-equivalence defects.
The bounded correction fixed denominator, count, and artifact validation, then
the honest gates established the partial result. The remaining acceptance
reviews were not run.

## Preservation and deferral

APG27 remains a truthful partial phase and APG27A remains its forward adoption.
Public and active v0.3.0, target repositories, personal skills, ChatGPT skill
paths, and canonical skill content are unchanged. No v0.4 release occurs.

The candidate remains dirty and uncommitted. It was not staged, committed,
pushed, or reported. Missing unconditional Git-show pytest scenarios,
affirmative subprocess and worker-completion accounting, release-policy test
failures, and the exact coverage deficits require a separately authorized
correction phase. No phase after APG28 is authorized by this exit.

## Next authorization

Stop with the APG28 candidate preserved. Any correction, successor
implementation, readiness work, publication, topology change, or coverage
remediation requires a new human-maintainer assignment.

## Subsequent disposition

APG28A received that separate authorization. It captured this stopped worktree
in a complete managed Git-diff report with an associated operational record and
adopted the corrected candidate forward. APG28 remains Partial; exit 00047 owns
the later correction and adoption result.
