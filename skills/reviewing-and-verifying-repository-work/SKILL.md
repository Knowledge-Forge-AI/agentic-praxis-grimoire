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

### Material claims and evidence direction

Before disposing a material claim, identify what kind of claim it is: a fact
that can presently be checked, a judgment or interpretation, a forecast, or an
assertion with no presently defined check or disconfirming observation. Verify
the checkable fact. Unsupported preference or taste is advice, not a required
finding. A judgment or interpretation may be a finding when its stated basis in
repository policy, an accepted contract, observable structure, demonstrated
behavior, or a named risk supports that disposition. Treat a forecast as a
forecast rather than an established current fact; verify the current facts
that bear on it, which may support a bounded risk judgment. Do not represent an
assertion with no presently defined check or disconfirming observation as
established; narrow the assertion, defer it, or state the limitation. When
acceptance would rely on an unstated material inference, state that inference
as its own claim and require evidence matching it. This is proportional
judgment applied to material claims, not a claim ledger, fixed taxonomy, or
classification step added to routine review, and it does not weaken the fresh
resulting-state evidence that completion claims already require.

When evidence does not establish a material claim, report the direction of what
was found: no relevant evidence within the inspected scope, relevant but
inconclusive evidence, or evidence that weighs against the claim. Name the
inspected scope when reporting absence, and do not report missing support as
refutation. Evaluate evidence that weighs against a claim for its relevance to
the exact claim, the directness of its inspectable basis, whether its
evidentiary lineage is shared or independent, its method or reliability when
material, and its strength and scope. After that evaluation it may support a
finding, an unresolved disposition, a narrower claim, a request for additional
evidence, or no change; it does not automatically refute the claim, create a
finding, or outweigh stronger evidence. A claim already established by fresh
resulting-state evidence needs no additional evidence-direction statement.

### Test, coverage, and report review

Verify that tests assert useful observable behavior and can fail for the stated
contract. Confirm that unit replacements do not erase the subject behavior and
that integration claims exercise the real boundary they name. A deliberately
mocked unsafe external service remains a unit or bounded-adapter claim, not
evidence that the service was integrated.

For a coverage claim, inspect exact coverage arithmetic, the complete
maintained-source inventory, worker and subprocess completeness when material,
and whether exclusions have an explicit owner and rationale. Reject tests added
only to execute lines, private-order assertions, duplicated contracts,
denominator or rounding manipulation, and unowned exclusions.

Broader test gates require a recorded justification tied to risk, a focused
failure, a project checkpoint, or an explicit requirement. Report deliberately
unrun comprehensive suites truthfully. Verify the project's actual status and
delivery convention: use Git-diff evidence for a dirty stopped result, Git-show
evidence for a committed result, and associated operational evidence when the
project requires it. Do not infer completion from any report's existence.

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
