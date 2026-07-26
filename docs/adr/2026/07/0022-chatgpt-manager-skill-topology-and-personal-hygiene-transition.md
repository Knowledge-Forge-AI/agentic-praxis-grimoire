# ADR 0022: ChatGPT Manager Skill Topology and Personal Hygiene Transition

## Status

Accepted

## Date

2026-07-22

## Context

APG's nineteen current canonical skills are direct children of `skills/`, and
the general router enumerates every routable non-router capability. One
provisional leaf, `composing-approved-roadmap-assignments`, has a primary actor
and output specific to the ChatGPT top-level manager. Future manager-only
capabilities would make the general router and flat canonical ownership less
coherent if each were added directly.

Three personal hygiene skills overlap in part with APG process behavior,
repository-owned conventions, and machine/private policy. Removing them before
replacement, source-qualified shadow, non-trigger evidence, and restoration
proof would risk losing legitimate private-only behavior or confusing duplicate
discovery with precedence.

## Decision

Adopt `skills/chatgpt/<name>/` as the future canonical owner for capabilities
whose primary actor is the ChatGPT top-level manager. Keep Codex discovery flat
through `.agents/skills/<name>` relative links to the nested canonical leaf.

Create a future `chatgpt-manager-workflow` subrouter that selects only among
ChatGPT-manager capabilities. The general APG router references that subrouter
as one capability and does not enumerate its leaves. There is no mandatory
router chain; explicit applicable leaf selection remains valid, and ordinary
Codex managers do not route through ChatGPT skills.

Classify `composing-approved-roadmap-assignments` as the initial ChatGPT-manager
leaf. Keep worker-assignment composition, planning, design, implementation,
debugging, review, synthesis, and technical profiles general unless separate
actor-and-trigger evidence supports reclassification.

Later checkers and lifecycle tools recursively discover only allowed canonical
owners, retain global frontmatter-name uniqueness, validate catalog links and
exact flat projection targets, and resolve source-declared canonical paths
without assuming `skills/<name>`. Public projection must preserve nested
canonical bytes and flat links. Public v0.3.0 retains its immutable direct-child
shape.

Adopt a bounded transition ledger for `docs-only-change-hygiene`,
`git-history-hygiene`, and `repomap-phase-hygiene`. The current recommendations
are decommission candidate, scope-reduction candidate, and decommission
candidate respectively. Each transition requires source-qualified positive and
non-trigger shadow evidence, coherent private-only disposition, exact rollback,
fresh review, and explicit human removal authority.

## Alternatives considered

- Keep every future canonical leaf flat and enumerate it in the general router.
  Rejected because actor-specific growth would dilute general selection.
- Move every composition, planning, and review skill under ChatGPT. Rejected
  because their triggers apply to ordinary Codex managers and repository work.
- Require general router to subrouter to leaf for every selection. Rejected
  because it adds a mandatory chain and weakens explicit selection.
- Hide nested leaves from flat Codex projection. Rejected because the leaves
  must remain directly discoverable and source-qualified.
- Remove overlapping personal skills immediately. Rejected because overlap is
  not replacement evidence or removal authority.
- Copy private wording into public APG. Rejected because private material is
  evidence, not a public dependency or reuse source.
- Preserve private-only and machine-owned units while decommissioning or
  narrowing only proven duplicates. Accepted.

## Consequences

The future checker, catalog, project/user lifecycle, router maps, public
projection, tests, and documentation must support nested canonical ownership
without counting namespace directories as skills. The path migration remains a
separate behavior-bearing phase and keeps the old tree retrievable for rollback.

The personal transition becomes evidence-driven and reversible. General
docs-only and commit defaults move toward project ownership; personal flow and
authorized history-rewrite support may remain private; RepoMap-specific phase
mechanics remain RepoMap-owned; machine escalation and memory policy do not
become public APG procedure.

APG25 changes no canonical path, projection, router map, catalog row, lifecycle
schema, public release, active integration, or personal skill.

## Deferred decisions

Defer subrouter implementation, canonical relocation, checker and lifecycle
changes, public-release support, exact personal scope reduction or removal,
application shadow, active integration changes, maturity, and v0.4 publication
to separately authorized roadmap slices.

## Implementation disposition

APG30 implements the topology portion without changing this decision. The
checker accepts exactly direct canonical leaves and
`skills/chatgpt/<name>/SKILL.md`, preserves global identity and flat
projections, and rejects unsupported namespace depth. The new provisional
`chatgpt-manager-workflow` owns only the local manager-capability map.
`composing-approved-roadmap-assignments` moves with unchanged procedure bytes
and provisional maturity. Project, user, and current-development release
owners resolve source-declared paths, while historical v0.1.0 through v0.3.0
policy remains direct-child.

APG30 does not implement the personal transition portion, mutate public or
active v0.3.0, or establish post-restart application discovery. Those
boundaries remain gated to APG31 and the required full application restart.
