# ADR 0020: Structured Project Phase Defaults and Prompt Compression

## Status

Accepted

## Date

2026-07-22

## Context

APG's formal phases repeatedly restate repository-controlled commit, status,
ADR, docs-only, scoped-test, push, remote-equality, and managed-report procedure
inside top-level manager assignments. The repetition makes material deviations
and authority boundaries harder to review and increases the chance that copied
mechanics become stale.

The existing `composing-approved-roadmap-assignments` skill correctly preserves
authority, acceptance, stop, and no-successor boundaries, but it treats
precommit and postcommit mechanics as optional prompt modules without first
loading a repository-owned structured default. APG also lacks one current owner
for ordinary non-phase commit and docs-only behavior.

## Decision

Adopt [`docs/structured-project-phase-defaults.md`](../../../structured-project-phase-defaults.md)
as APG's project-owned convention for formal phases and ordinary non-phase
work.

A formal APG phase normally has one semantic phase, one commit, a finalized
exit before commit, proportional validation, authorized push and remote parity,
one postcommit Git report with one associated operational record, and a hard
stop before an unauthorized successor. One-commit exceptions require an
explicit integration, release, correction, or partial/blocked-result reason.

Ordinary implementation testing is scoped: unit behavior receives scoped unit
tests, and a changed integration boundary receives scoped integration tests.
Combined, smoke/system, and complete suites are not default implementation
gates. Broader tests require an explicit project, defect, testing-infrastructure,
readiness, release, CI/CD, or human reason.

Outside a formal phase, commit authority permits clean atomic commits without
invented phase, exit, or ADR ceremony. Docs-only work receives proportional
link, identity, privacy, diff, and whitespace checks; source tests run only
when the affected contract or repository requires them.

Apply one bounded behavior-bearing correction to
`composing-approved-roadmap-assignments`. It must load the repository default,
reference it once, omit redundant default mechanics, and retain deviations,
phase-specific evidence, unusual scope, acceptance, stop, and successor
boundaries. Missing, conflicting, release, destructive, or otherwise high-risk
defaults require expanded detail.

APG framing does not become universal. A target repository's more specific
status, commit, test, or report owner replaces APG convention.

## Alternatives considered

- Continue repeating every formal mechanic in every assignment. Rejected
  because it obscures deviations and creates stale copies.
- Remove mechanics without a named current owner. Rejected because omission
  would make assignments incomplete rather than compressed.
- Create a rigid universal assignment template. Rejected because proportional
  work and repository-specific conventions require different modules.
- Create a new prompt-compression skill. Rejected because the existing
  approved-roadmap composition trigger already owns this judgment.
- Let the manager omit authority and stop boundaries along with procedure.
  Rejected because those values are task-specific and cannot be inherited
  safely.
- Adopt project-owned defaults and make one bounded existing-owner correction.
  Accepted.

## Consequences

Manager assignments become shorter when APG defaults apply, but remain
independently reviewable. Prompt quality is evaluated by completeness and
authority fidelity before line or byte reduction. Formal docs-only phases keep
their semantic and reporting ceremony; non-phase docs-only work does not gain
it.

The accepted defaults are documentation, not commit, push, publication,
destructive-action, or successor authority. Current report executables retain
their behavior until the separate reporting roadmap slice.

Coverage remediation, mock boundaries, and framework-specific pytest behavior
remain separately owned. APG25 assigns future corrections but does not broaden
those skill procedures beyond the single approved composition correction.

## Deferred decisions

Defer implementation of coverage-remediation and other process-skill
corrections, Python report conversion, pytest migration, ChatGPT canonical-path
relocation, personal hygiene-skill transition, readiness, and v0.4 publication
to separately authorized roadmap slices.
