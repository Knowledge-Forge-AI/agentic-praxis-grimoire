# ADR 0021: Python-First Test and Agent-Reporting Architecture

## Status

Accepted

## Date

2026-07-22

## Context

APG's managed reporting commands are Bash programs with shared shell safety,
formatting, Git extraction, locking, and atomic-replacement behavior. They are
tested, but future cross-platform growth, a required uncommitted-diff report,
and stronger operational-record association would increase shell complexity.

APG's Python tests currently use standard-library `unittest` from flat unit and
integration roots. The accepted v0.4 goals require pytest-specific guidance,
eight-worker parallel execution, independent and combined statement and branch
coverage gates, mirrored test ownership, and explicit detection of incomplete
collection or coverage data. The RepoMap prototype supplies useful suite and
threshold evidence but does not currently aggregate xdist coverage.

## Decision

Adopt Python as the default language for new executable APG project tooling.
Use shell only as a thin launcher or when shell semantics are materially
simpler. Node.js requires a strong project-specific reason.

Design one future shared Python reporting core with separate Git source,
report-model, renderer, envelope, safe-destination/lock, operational-framing,
and CLI-adapter owners. Use fixed-argument `subprocess` calls to the Git CLI as
the baseline. GitPython is permitted only after a bounded dependency and parity
evaluation demonstrates an advantage.

Preserve current root, single-parent, and first-parent merge behavior for
`git-show-report`. Add a future `git-diff-report` that captures status plus the
complete `git diff HEAD` state, including untracked intent, through a
characterized private temporary index and `git add -N -- .` only there. Capture
the real index fingerprint before observation, disable optional index refresh
and external diff/text conversion, detect concurrent drift, and fail closed on
an uncharacterized split, sparse, custom, or unmerged index. The real index and
worktree must remain byte- and status-equivalent.

When a Git show or Git diff record exists for a result, append the operational
record to the same phase report and relate it explicitly. Permit a standalone
operational report only when no associated Git record exists; reject or visibly
diagnose conflicting standalone creation. Derive one canonical destination and
hold one project/result association lock across lookup and write. Preserve the
current behavior in which every invocation appends a distinct record; dedupe or
replacement is a separate compatibility decision.

For APG's later test migration, select pytest, pytest-xdist, and pytest-cov over
coverage.py branch measurement. Use eight workers by default. Store tests under
unit and integration roots that mirror production paths beneath an
`agentic-praxis-grimoire` path directory. Require each component suite to pass
and reach 80% statements and 80% branches. Require their data union to reach
85% statements and 85% branches. Compare exact integer counts, not rounded
display percentages.

Use pytest-cov's supported xdist aggregation per suite and coverage.py combine
for the separate unit and integration data union. Because pytest-cov 7 removed
its own subprocess-start mechanism, configure coverage.py's `patch = subprocess`
for Python child-process contracts. Retain direct coverage.py parallel data as a
bounded fallback. Fresh nonce-scoped data roots, worker/process accounting,
strict readable combination, and stale or unexpected data rejection precede
threshold evaluation.

## Alternatives considered

- Continue growing the shell reporting core. Rejected as the default because
  cross-platform path, locking, parsing, and model growth would remain coupled
  to CLI formatting.
- Rewrite tooling in Node.js. Rejected because APG already has Python tooling
  and Node adds a larger project-specific runtime without a demonstrated need.
- Use GitPython for all Git behavior. Deferred because it adds a dependency and
  does not eliminate the need to verify exact Git CLI semantics.
- Use fixed-argument Git CLI calls from Python. Accepted as the smallest exact
  baseline.
- Run `git add -N` against the real index and restore it. Rejected because a
  crash can leave staged-state changes; a temporary index avoids the mutation.
- Average unit and integration coverage percentages. Rejected because an
  average is not the coverage union and can hide unexecuted statements.
- Use the RepoMap runner unchanged. Rejected because it is project-specific and
  its current xdist path disables coverage rather than aggregating it.
- Implement a custom xdist coverage aggregator first. Rejected because
  pytest-cov and coverage.py provide primary-source-supported mechanisms.

## Consequences

Future executable work has a consistent cross-platform default and a smaller
dependency baseline. The migration must characterize current bytes, exit codes,
Git semantics, destination checks, lock behavior, and interruption recovery
before switching adapters.

The pytest architecture makes suite separation and coverage union explicit.
The runner must fail on no tests collected, source omission, stale or duplicate
mirror paths, suite contamination, worker crash, missing or foreign worker/
process data, zero source statements, incomplete or unreadable combination,
exact-gate failure, and unsupported-platform collection. Real Git, filesystem,
subprocess, and report boundaries remain integration-test contracts rather
than mocked claims.

Report migration must also prove NUL-safe Git parsing, current bounded textual
binary summaries, deterministic association-before-destination lock ordering,
and POSIX local-filesystem replacement. Windows replacement and network
filesystem behavior remain fail-closed until characterized.

APG25 changes no script, dependency, package metadata, test location, runner,
public release, or active integration.

## Deferred decisions

Defer exact dependency versions, package layout, report schema and duplicate-
record semantics, GitPython adoption, cross-platform implementation details,
report conversion, new diff command, test migration, CI matrix, and release
inclusion to their separately authorized roadmap slices.
