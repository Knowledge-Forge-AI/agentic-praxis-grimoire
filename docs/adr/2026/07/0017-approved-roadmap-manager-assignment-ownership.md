# ADR 0017: Approved-Roadmap Manager-Assignment Ownership

## Status

Accepted

## Date

2026-07-21

## Acceptance authority

The human maintainer's APG22A-to-APG22B assignment authorizes evaluation and
optional implementation of this owner. Acceptance follows an exhaustive
historic-corpus inventory, current official Codex capability review, an
ordinary-prompting baseline, 30 frozen scenarios, focused integration tests,
and fresh non-author review. It does not authorize roadmap creation, dispatch,
execution, phase acceptance, v0.3 publication, or APG23.

## Context

Current Codex can write prompts, discover repository instructions and skills,
delegate bounded work, consolidate results, and continue a saved task. Ordinary
reasoning also produced strong proportional manager assignments for all 14
positive baseline scenarios. APG therefore needs no generic prompt-writing
owner and cannot justify one by claiming native or ordinary prompting is
inadequate.

Historic manager and orchestration prompts nevertheless repeat one coherent
semantic problem: translating a human-approved roadmap phase into a durable
top-level manager assignment while preserving phase identity, authority,
scope, evidence, reporting order, partial and blocked outcomes, external
acceptance, and a terminal stop. Existing planning, worker-assignment, routing,
review, and repository-specific owners each cover only part of that boundary.
Private prompt expression has unresolved public reuse rights and contains
project-specific detail, so it cannot serve as a public template.

## Decision

Adopt one provisional public capability,
`composing-approved-roadmap-assignments`, to translate already approved
authority into one reviewable Markdown top-level manager assignment.

Human roadmap authority is a hard precondition. One approved phase is the
default unit. An explicitly preauthorized bounded sequence is supported only
when every phase, semantic identity, hard gate, separate record, separate
commit, separate report, and terminal boundary is supplied. Composition does
not approve, revise, dispatch, schedule, execute, review, accept, publish, or
continue the roadmap.

The skill uses a proportional core plus only risk-dependent modules made
material by the task. Semantic phase IDs and tracked current-state records are
finalized before commit; exact Git identities and commit-dependent reports
remain postcommit evidence. Private prompts are evidence for a clean-room
functional synthesis, not templates to copy.

Ordinary prompting remains the fallback and comparison baseline. Existing
owners remain separate:

- `planning-repository-work` owns implementation decomposition;
- `composing-bounded-worker-assignments` owns each independently authorized
  worker assignment;
- `agentic-praxis-grimoire-workflow` owns ambiguous capability selection;
- repository policy and the manager-worker protocol own project mechanics and
  actor authority; and
- `reviewing-and-verifying-repository-work` and the external project authority
  own evidence disposition and acceptance.

## Alternatives considered

### Ordinary prompting only

Viable and retained as the fallback. Rejected as the only owner because it
does not provide one stable, inspectable omission and authority contract across
repositories and phases.

### One giant mandatory prompt template

Rejected. It would add ceremony, obscure project-owned parameters, and make
small phases disproportionate.

### Expand `planning-repository-work`

Rejected. Plans decompose accepted implementation; they are not top-level
manager assignments and do not own dispatch or phase closeout semantics.

### Expand `composing-bounded-worker-assignments`

Rejected. A worker contract has a different actor, scope, and return boundary
and presupposes independently authorized delegation.

### Use the workflow router as a generator

Rejected. The router selects a capability; it does not copy or perform the
selected procedure.

### Project-specific templates only

Retained as an available local mechanism, but rejected as the sole general
answer because it repeats omission and authority review across projects and
cannot supply a public reusable semantic boundary.

### One bounded manager-assignment skill

Accepted. It adds a narrow reusable contract without replacing native writing
or existing APG owners.

## Consequences

Private development contains 18 canonical leaves, 18 relative projections,
6 stable rows, 12 provisional rows, and 17 routable non-router capability-map
entries. Public v0.2.0, active integration, the six managed defaults, and
schema version 1 remain unchanged.

The skill adds one maintenance and source-refresh obligation. Its benefit is
repeatable omission and authority control, not comparative prose superiority.
Every scenario passed with zero material candidate corrections.

APG22A also corrects the current development catalog's historical section
label. The checker continues to accept the legacy heading used by prior public
releases, so the documentation correction does not invalidate v0.1 or v0.2.

## Migration and rollback

No historic prompt, private skill, root instruction, public release, or active
integration is migrated. Rollback removes only the canonical leaf, relative
projection, provisional catalog row, capability-map entry, focused tests, and
known-unmanaged development name while preserving this ADR, evaluation, exit,
and provenance history. Ordinary prompting and every existing owner remain
available without restoration work. The corrected current-catalog heading and
legacy-heading checker compatibility remain because they correct shared
current and historical catalog ownership rather than implement the removable
candidate capability.

## Deferred decisions

Maturity review, public v0.3 distribution, active integration, application
smoke, private-source cutover, and APG23 remain separately authorized work.
