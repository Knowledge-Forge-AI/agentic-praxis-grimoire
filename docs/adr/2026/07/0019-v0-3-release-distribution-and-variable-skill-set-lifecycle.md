# ADR 0019: v0.3 Release Distribution and Variable Skill-Set Lifecycle

## Status

Accepted

## Date

2026-07-22

## Context

APG23 is accepted as complete. It places all thirteen v0.3 additions in release
scope, promotes eight of those rows to `stable`, retains five as
`provisional`, and leaves the complete development catalog at nineteen skills,
fourteen stable rows, and five provisional rows. Release inclusion describes a
truthful distribution boundary; it does not change maturity.

Public v0.2.0 and the existing user and project lifecycle defaults contain six
stable process skills. The public release policy also treats those six skills
and projections as its critical set. APG24 must distribute the accepted
nineteen-skill release without making existing six-skill state ambiguous,
removing unrelated paths, rewriting public history, or silently changing the
maintainer's active integration ownership model.

The existing version-1 user state already records the current and previous
source identities, each source's exact skill-hash mapping, and the managed-name
set. The existing version-1 project state records an explicit managed subset.
Those representations can express six-skill and nineteen-skill releases and an
existing six-skill project subset without a lossy migration.

## Decision

Public v0.3.0 contains all nineteen APG skills and their nineteen checked-in
projections. The public policy's current critical skill and projection sets are
the exact APG23 release-included set. The catalog remains fourteen `stable` and
five `provisional` rows; release inclusion does not promote maturity.

The exact release set is:

- `agentic-praxis-grimoire-workflow`;
- `bash-language-profile`;
- `bats-test-profile`;
- `composing-approved-roadmap-assignments`;
- `composing-bounded-worker-assignments`;
- `debugging-systematically`;
- `designing-significant-changes`;
- `go-language-profile`;
- `implementing-with-test-discipline`;
- `nix-language-profile`;
- `planning-repository-work`;
- `postgresql-database-profile`;
- `python-language-profile`;
- `reviewing-and-verifying-repository-work`;
- `ruby-language-profile`;
- `sqlite-database-profile`;
- `synthesizing-repository-guidance`;
- `zsh-language-profile`; and
- `zunit-test-profile`.

Retain schema version 1 for both lifecycle tools. This is a representation
decision, not an instruction to retain six-name behavior. User lifecycle
commands derive the managed set independently from each verified public release
identity. A transition between releases computes retained names, additions, and
removals, validates both source-declared sets, preflights every destination and
temporary path, changes links under the existing lock, and commits state last.
Failure restores the exact prior set. Rollback restores the previous release's
exact source-declared set rather than assuming that every release contains the
same names.

The user lifecycle never removes an unrelated skill or an unowned path. An
addition conflict stops before mutation. A missing, retargeted, malformed, or
otherwise unproven owned path stops removal. Duplicate repository- and
user-scope names are warnings only; the command does not infer discovery
precedence or invocation source.

Project-local lifecycle exposes the complete current nineteen-skill release as
the default for a new install or adopt and continues to accept explicit
subsets. Existing version-1 state remains authoritative for its recorded
managed subset, including a six-skill v0.2 subset. Check and uninstall do not
implicitly expand that state. APG24 mutates no real target project.

The active maintainer integration retains its existing aggregate-link owner and
link shape. It changes only by fast-forwarding the clean public-backed source
checkout to the verified v0.3.0 commit after publication. APG24 does not create
user-lifecycle state for that integration or run install, adopt, update,
rollback, or uninstall against it.

The personal same-name workflow router remains installed during an explicit
post-release dual-source shadow. Source-qualified fresh-session evidence is
required before any later private-router decommission, which needs separate
human authority. No duplicate name establishes precedence by itself.

Public history remains one appended squashed release commit per version.
v0.3.0 has public v0.2.0 as its sole parent and one annotated `v0.3.0` tag.
Rollback preserves v0.2.0 and its tag and never rewrites, deletes, or retags
public history.

## Alternatives considered

- Keep public distribution at six. Rejected because it would omit the accepted
  APG23 release set.
- Publish nineteen while leaving lifecycle commands six-only. Rejected because
  source validation, update, rollback, and new project installation would not
  describe the published release truthfully.
- Manage only stable skills. Rejected because maturity and APG23 release
  inclusion are independent decisions.
- Manage all APG23 release-included skills. Accepted.
- Replace existing user state wholesale. Rejected because it would discard
  verified previous-source and ownership evidence needed for exact rollback.
- Compute source-specific additions, retargets, and removals. Accepted because
  it preserves explicit ownership across release-set changes.
- Increment the state schemas. Rejected because the version-1 representations
  already encode source-specific hash maps and explicit managed subsets;
  executable compatibility evidence is required to retain this conclusion.
- Migrate the active integration to direct user links. Rejected because APG24
  does not own that integration migration and the existing aggregate owner can
  safely consume the release by source fast-forward.
- Preserve the active aggregate-link owner. Accepted.
- Decommission the personal router in APG24. Rejected because the authorized
  release requires a source-qualified dual-router shadow first.

## Consequences

The release, user, and project tools must validate variable source-declared
skill sets while preserving strict lineage, path ownership, state integrity,
and failure recovery. Existing six-skill project and user release identities
remain readable. New default project installs expand to nineteen, but existing
managed subsets do not expand implicitly.

The existing public-release module was already Red at 1,245 lines. APG24
accepts a bounded legacy exception for its growth to 1,430 lines
solely to keep the current v0.3 and immutable historical v0.2 audited policy
surfaces explicit in the existing release owner. This adds no responsibility or
dependency. A dedicated policy-data owner may reduce that legacy size only
through separately authorized follow-up; this decision does not authorize a
successor phase. The user-lifecycle module remains at the 1,000-line Orange
boundary, and variable-set integration coverage remains in a separate test
module rather than pushing the existing lifecycle test owner into Red.

Public v0.2.0 remains the immutable prior release and rollback source. Exact
ZUnit support remains limited to ZUnit v0.8.2 with Zsh 5.9.2 in the tested
environment and recorded startup boundary; Zsh 5.3.1 is unsupported and every
other pair is unverified. Nix and database profile distribution grants no live
evaluation, build, connection, migration, or mutation authority.

## Deferred decisions

Fresh-session source-qualified shadow observation remains external after the
active source update. Private-router decommission, root or private guidance
removal, active-integration ownership migration, plugin or registry packaging,
and any successor roadmap require separate human authority.
