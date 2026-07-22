---
name: composing-approved-roadmap-assignments
description: Use when a human-approved roadmap phase or explicitly approved bounded phase sequence must become a reviewable top-level coding-agent manager assignment with authority, scope, evidence, acceptance, stop, reporting, and handoff boundaries.
---

# Composing Approved Roadmap Assignments

## Core principle

Translate approved authority; do not create authority. Compose one reviewable
top-level manager assignment for one approved phase by default. Support an
explicitly approved bounded phase sequence only when every phase, identity,
gate, and terminal boundary is already authorized.

Keep the assignment proportional. Existing APG skills and repository documents
remain the procedure owners; this skill only composes their applicable inputs
and boundaries into one manager-facing artifact. Composition does not execute,
dispatch, schedule, review, accept, or continue the work.

## Do not use

Do not use this skill to:

- invent, approve, revise, reorder, merge, split, or extend a roadmap;
- allocate a semantic phase ID;
- handle one simple direct task that already has adequate instructions;
- decompose implementation work owned by `planning-repository-work`;
- compose one internal worker assignment owned by
  `composing-bounded-worker-assignments`;
- resolve skill-selection ambiguity owned by
  `agentic-praxis-grimoire-workflow`;
- review or accept a result owned by
  `reviewing-and-verifying-repository-work`;
- dispatch workers, schedule work, or operate a manager runtime;
- continue automatically into a successor phase;
- copy a private or protected prompt template; or
- require delegation or a mandatory chain of APG skills.

## Procedure

1. Verify the human-approved objective and exact roadmap scope. If approval is
   absent, ambiguous, or limited to evaluation, preserve that limit or stop.
2. Identify the canonical semantic phase ID supplied by the project. Stop
   rather than inventing an unallocated identity or using a future commit hash
   as tracked identity.
3. Inspect current repository instructions, accepted decisions, roadmap,
   current owners, and repository state. Surface conflicts or unexpected state
   rather than silently reconciling, resetting, cleaning, or stashing it.
4. Select one phase by default. Use an explicitly approved bounded phase
   sequence only when every phase and hard gate is supplied; keep each phase's
   records, review, commit, push, reports, and outcome separate.
5. Compose the proportional core:
   - approved objective and terminal outcome;
   - repositories, source and write scopes, and precedence;
   - preserved invariants and material prohibitions;
   - required deliverables and evidence;
   - observable acceptance criteria and external acceptance owner;
   - stop, partial, blocked, and failure behavior; and
   - terminal handoff and no-successor boundary.
6. Add only modules made material by the approved work:
   - source identity, provenance, rights, and private and public treatment;
   - frozen scenarios, baseline comparison, and correction limit;
   - delegation roles and exclusive scopes, without composing the individual
     worker assignments unless separately requested;
   - behavior tests, static checks, complete-diff review, and unrun checks;
   - migration, recovery, rollback, or destructive-action authority;
   - precommit tracked-document finalization and postcommit Git, push, parity,
     and operational reporting;
   - release candidate, remote-race, publication, and post-publication gates;
     and
   - application-smoke timing and the evidence that is deliberately deferred.
7. Reference `planning-repository-work` for implementation decomposition and
   `composing-bounded-worker-assignments` for each independently authorized
   worker contract. Do not duplicate either procedure.
8. Keep result review and acceptance external. Reference
   `reviewing-and-verifying-repository-work` when evidence needs disposition.
9. Self-review authority fidelity, objective fidelity, omissions, unnecessary
   ceremony, stale current state, privacy, and proportionality.
10. Output one independently understandable Markdown manager assignment.

Do not execute, dispatch, accept, or continue the assignment.

Use headings that fit the work. Do not force every optional module or one giant
template into a small phase.

## Project-owned parameters

The human, project, or current task owns:

- roadmap and phase approval;
- semantic phase IDs and current-state identities;
- repository identities, branches, source and write scopes, and precedence;
- exact commands, test gates, thresholds, and supported versions;
- delegation decisions, worker roles, worker limits, and harness capabilities;
- privacy classes, source rights, and private and public treatment;
- commit, push, publication authority, release version, and rollback policy;
- report commands, schemas, order, and storage;
- application-smoke timing; and
- result review and acceptance authority.

Preserve supplied values exactly enough to remain reviewable. Mark unresolved
required values as blockers; do not fabricate them or infer authority from a
roadmap title, historic prompt, report, commit, or recommendation.

## Evidence and completion

The output is complete when a reviewer can answer:

- What exactly is approved, and what terminal result is requested?
- What may be inspected and changed, and what must remain unchanged?
- Which existing procedure owners apply without being duplicated?
- What evidence and deliverables are required?
- What produces a stop, partial, blocked, or failed result?
- What tracked current owners and records must be final before commit?
- What reports or remote checks occur only postcommit?
- Who reviews and accepts the result?
- What rollback or recovery authority exists?
- What work, smoke, publication, or successor does not begin automatically?

Completion means the assignment artifact is reviewable and authority faithful.
It does not mean the assignment was dispatched, executed, accepted, committed,
reported, published, or continued.

## Stop or escalate

Stop and return the unresolved boundary when:

- roadmap approval or semantic phase identity is absent or ambiguous;
- a later accepted decision or current owner conflicts with the roadmap;
- source, write, commit, push, publication, or destructive authority is
  unclear;
- private and public treatment or reuse rights are unresolved;
- an unexpected repository state changes the approved baseline;
- a requested assignment adds authority not present in the approval;
- a phase sequence contains an unapproved phase or missing hard gate;
- continuation or acceptance is assigned to the generated prompt itself; or
- public output would require private wording or private-only context.

Do not hide these conditions inside placeholders that make the assignment look
dispatch-ready.

## Common mistakes

- turning an approved roadmap into a new roadmap;
- confusing an implementation plan with a manager assignment;
- duplicating worker-assignment, routing, or review procedure;
- copying every repository rule or adding every optional section;
- inventing phase IDs, paths, commands, tests, versions, or report mechanics;
- using a future commit hash as tracked phase identity;
- treating reports, worker returns, or successful tests as external acceptance;
- making delegation, publication, smoke, or the next phase automatic; and
- exposing private prompt structure or operational detail in public text.
