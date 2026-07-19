---
name: reviewing-and-verifying-repository-work
description: Use when a bounded repository artifact, change, phase, commit, or worker result requires evidence-backed acceptance, correction, disposition, or a completion claim.
---

# Reviewing and Verifying Repository Work

## Core principle

Accept work and make completion claims from fresh evidence in the resulting
state, not from artifact existence or self-report.

## Do not use

Do not use this skill to invent review authority, replace unresolved design,
approve work outside the reviewer mandate, or require a branch, pull request,
commit, push, or managed report that the project does not own. Casual feedback
that requests no disposition may use a lighter review.

## Procedure

1. Establish the authorized scope, acceptance criteria, evidence owner, and
   exact artifact or resulting state under review.
2. Inspect current repository state and the complete relevant change rather
   than relying on a summary, commit existence, worker result, or report.
3. Review in this order:
   1. scope and authority;
   2. correctness and regressions;
   3. safety and privacy;
   4. contract and architectural fit;
   5. test and verification adequacy;
   6. maintainability;
   7. documentation and provenance; and
   8. style.
4. Match every material claim to fresh evidence from the resulting state.
   Interpret the output, exit state, coverage, and limitations; do not treat a
   command name or checkmark as proof by itself.
5. Record actionable findings with evidence, impact, and the smallest safe
   correction. Distinguish blockers, material findings, and optional advice
   using the project's vocabulary.
6. Evaluate responses to findings technically. Clarify ambiguous feedback,
   accept sound corrections, and reject false positives with evidence.
7. Re-run affected verification after correction and inspect the integrated
   state again.
8. Return an explicit disposition: accept, accept with follow-up, correction
   required, reject, defer, or the project-owned equivalent. State unrun checks,
   residual risk, and the reached boundary.

A no-finding review does not create a reason to modify the artifact.

## Project-owned parameters

The project owns reviewer independence, severity labels, required tests,
security and privacy review, Git and hosting workflow, correction authority,
publication gates, durable records, and final acceptance actor.

## Evidence and completion

A completion claim names the resulting state, checks actually run, relevant
outputs, checks not run and why, unresolved findings, repository cleanliness,
and any external state such as remote parity that was separately verified.
Review evidence informs disposition but does not expand authority.

## Stop or escalate

Stop when the reviewed state is ambiguous, required evidence is stale or
missing, private material cannot be handled safely, findings require authority
outside the current task, the artifact changes during review, or a blocker
cannot be resolved within the authorized correction boundary.

## Common mistakes

- reviewing only the summary or changed-file list;
- treating a commit, worker result, report, or passing test as acceptance;
- leading with style while correctness or safety remains uncertain;
- applying ambiguous feedback without verification;
- rerunning focused checks but not the affected final gate; and
- claiming completion while hiding stale, skipped, or failed evidence.
