# ADR 0018: v0.3 Readiness, Maturity, and Release Inclusion

## Status

Accepted

## Date

2026-07-21

## Context

APG22C is accepted as complete. Its corrected selected-user-startup controls
retain support only for ZUnit v0.8.2 with Zsh 5.9.2 in the tested environment,
retain exact Zsh 5.3.1 as unsupported, and establish no version range.

APG23 began in a new APG-rooted Codex session after the required full
application restart. All 19 repository development skill names were directly
visible and selectable. The client separately exposed repository-scoped and
personal same-name workflow routers, and repository selection used the supplied
repository path rather than inferred source.

Maturity and release inclusion answer different questions. Maturity describes
the evidence supporting routine bounded use. Release inclusion asks whether a
skill can be distributed truthfully and independently without an unresolved
material defect.

## Decision

Promote the workflow router, repository-guidance synthesis, Python, Bash, Bats,
Zsh, exact-bounded ZUnit, and Nix rows to `stable`. Retain approved-roadmap
assignments, Go, Ruby, PostgreSQL, and SQLite as `provisional`. Include all
13 v0.3 skills in the APG24 release scope.

A provisional row may be `include-v0.3` when its trigger, limitations,
source/version boundary, discovery, explicit use, public independence, and
rollback are complete and no material defect remains. Distribution success
alone never establishes maturity.

The resulting development state is 19 canonical skills, 19 catalog rows, 19
checked-in projections, 14 stable rows, 5 provisional rows, and 18 routable
non-router capabilities.

The ZUnit inclusion remains limited to v0.8.2 with Zsh 5.9.2 under the
APG22C-corrected selected-user-startup boundary. Exact Zsh 5.3.1 remains
unsupported; every other pair remains unverified.

APG23 makes no automatic-invocation, comparative-superiority, universal-use,
or production-warranty claim. Root reduction and private cutover are not
prerequisites for truthful public inclusion. Public v0.2 and its six stable
process leaves remain unchanged.

APG24 may begin only after APG23 is complete, committed, pushed, remote-equal,
fully reported, and externally accepted. APG24 separately owns candidate
construction, projection validation, publication, active integration work,
duplicate-source handling, and post-release rollback. It does not begin
automatically.

If a later material defect affects a scoped skill, exclude or correct that
skill through separately authorized work rather than silently narrowing v0.3.
Maturity rollback changes the catalog label and current records while
preserving APG23 history. Independent removal follows the recorded lifecycle
for that leaf.

## Alternatives considered

- Require every v0.3 skill to be stable. Rejected because truthful provisional
  inclusion and maturity are separate decisions.
- Release every provisional skill automatically. Rejected because each skill
  requires individual defect, source, integration, and rollback review.
- Treat distribution success as maturity. Rejected because discovery and
  projection do not establish semantic use.
- Review each skill independently. Accepted as part of this decision.
- Exclude a skill with a material defect. Accepted as the required response,
  although APG23 found none.
- Publish before application smoke. Rejected because direct discovery and
  explicit use are release-inclusion evidence.
- Use fresh-session smoke plus individual evidence. Accepted.

## Consequences

All original v0.3 objectives are terminal before release construction, and
APG24 is the only remaining v0.3 phase. Five rows remain truthfully provisional
without blocking inclusion. No public repository, active integration, managed
default, personal workflow, or target repository changes in APG23.
