# APG19A Semantic Phase Identity and APG19 Reconciliation Evaluation

## Outcome

Complete — semantic phase identity adopted and APG19 reconciled.

Phase ID: `APG19A`

APG19A accepts APG19's substantive partial outcome: ADR 0014, separate Bash,
Bats, Zsh, and reserved ZUnit ownership, three provisional retained profiles,
the ZUnit source/version deferral, calibrated warning bands, combined-signal
escalation, semantic Red stops, read-only dogfood, twelve-skill development
integration, six-skill public v0.2 lifecycle, unchanged maturity, and deferred
application smoke.

## Semantic identity and record policy

[ADR 0015](../adr/2026/07/0015-semantic-phase-identity-and-record-finalization.md)
and the [phase and record identity guide](../phase-and-record-identity.md) adopt:

- globally unique, never-reused, uppercase semantic phase IDs assigned before
  implementation;
- ADR sequences unique within `docs/adr/` and exit sequences unique within
  `docs/status/`, with no cross-comparison;
- semantic durable references for phases, decisions, exits, releases, source
  versions, and phase-local evidence;
- managed reports and transient verification as the owners of exact Git IDs;
- precommit finalization of implementation, current owners, evaluation, exit,
  applicable ADR, and indexes; and
- forward correction of historical records rather than invented retroactive
  policy.

The standard-library `apg-check-record-identity` command validates indexed exit
existence and exact coverage, independent sequence uniqueness, case-insensitive
phase uniqueness, canonical spelling, new-record agreement, phase allocation
expectations, and independently computed next values. The public-release gate
includes the command, helper, integration tests, help, compilation, and
configured validation without changing schema version 1 or the six critical
v0.2 skills.

## Durable-reference reconciliation

APG19 tracked evidence now identifies dogfood and candidate cases with stable
phase-local IDs instead of content digests. bats-core v1.13.0, Zsh 5.9.2, and
ZUnit v0.8.2 replace source commits where semantic releases exist. The dated
unreleased ZUnit observation uses a phase-local source ID, public locator, and
explicit mutability limitation.

Current provenance and the skill catalog replace unversioned third-party Git
pins with phase-local source IDs, public locators, inspection dates, and stated
revision limitations. Root and private instructions, project governance,
coordination, authoring, roadmap, catalog, integration, release, evaluation,
and status owners now implement the semantic identity and precommit policy.

The focused scan covers changed tracked files and current identity owners. It
does not impose a repository-wide hexadecimal ban that would confuse licenses,
fixtures, historical raw evidence, or report-owned objects with durable
semantic references.

## Focused APG19 profile audit

Bash threshold, quoting, expansion, pipeline, `set -e`, `pipefail`, trap,
temporary-resource, dynamic-execution, destructive-target, legacy-fix, and
process-owner boundaries were accepted without correction. The Bash leaf
remains byte-identical to APG19.

Zsh option locality, emulation, arrays, splitting, expansion, globbing,
startup, autoload, hooks, ZLE, completion, module, dynamic-source,
destructive-glob, legacy-fix, and process-owner boundaries were accepted
without correction. The Zsh leaf remains byte-identical to APG19.

ZUnit v0.8.2 remains the latest canonical release, the later default-branch
observation remains documentation-only, and historical CI still ends at Zsh
5.3.1. The ADR 0014 re-entry condition remains truthful and no ZUnit skill is
implemented.

The Bats audit reproduced one material fallback-count defect. bats-core v1.13.0
supports a comment function form such as `function case_name { #@test`; the
APG19 instruction to count `@test` declarations after excluding comments could
omit runner-recognized tests and understate Yellow, Orange, or Red bands. One
forward correction now counts runner-recognized native and supported comment
forms, excludes incidental strings, comments, heredocs, fixtures, and static
samples, and forbids evaluating a target Bats file merely to count without
authority. All thresholds and other Bats semantics remain unchanged.

The corrected Bats contract was reapplied to the shared structural,
domain-specific, exact-boundary, coupled-signal, and seven-category read-only
dogfood evidence. The supported comment-form boundary now receives the same
test-count band as the runner. No second correction was required.

## Current state and integration

Private development remains twelve canonical skills and projections: six
stable process skills and six provisional v0.3 skills. The router remains
provisional with eleven routable non-router entries. Project, user, and public
release lifecycle defaults remain exactly the six stable v0.2 skills under
schema version 1. Public v0.2.0 and the active integration are unchanged.

The identity command, helper, tests, ADR, guide, evaluation, and exit are exact
public-surface additions for a future authorized release; APG19A performs no
publication. The Bats correction changes one existing provisional leaf without
changing maturity, routing, catalog membership, projection shape, installer
state, or release skill policy.

## Validation and review

Failing-first evidence covered the Bats count wording and the absent identity
command. Focused tests then passed for supported comment-form wording,
independent ADR/exit namespaces, duplicate sequences, exact exit indexing,
case-insensitive phase uniqueness, canonical spelling, record-field agreement,
new-record explicit phase fields, and phase allocation expectations.

The complete resulting tree passed the repository's Bats, skill-library,
record-identity, project, checker, release, and user unit/integration suites;
development and fresh public-v0.2 checker text/JSON; Python compilation;
applicable shell syntax; command help; Markdown and local-link review; privacy,
mode, schema, current-state, identity, sequence, and whitespace checks. Fresh
non-author policy, profile, integration, and complete-diff reviews accepted the
resolved tree.

## Boundary and APG20 gate

No root guidance was removed, no private skill was decommissioned, and no
public, reference, RepoMap, active-integration, or dogfood source was mutated.
No application smoke was run; APG23 and APG24 retain that responsibility. No
Go, Ruby, Nix, PostgreSQL, SQLite, ZUnit, or manager-prompt profile or skill was
implemented in APG19A.

The maintainer's two-phase assignment authorizes APG20 only after APG19A's
independent review, precommit record finalization, identity checks, commit,
push, remote equality, and schema-valid managed reports all complete. No phase
after APG20 is authorized.

## Subsequent APG22B disposition

APG22B later retains a provisional ZUnit profile only for exact ZUnit v0.8.2
with Zsh 5.9.2 in the tested environment. The exact Zsh 5.3.1 pair is
unsupported. This subsequent result preserves APG19A's semantic identity policy
and historical reconciliation record.
