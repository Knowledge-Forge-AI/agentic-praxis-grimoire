# ADR 0057: Public Staging PR Release Procedure

## Status

Accepted implementation; dated APG144 disposition (2026-09-13)

## Decision date

2026-09-12 (route accepted); 2026-09-13 (implementation accepted under APG144)

## Context

APG develops in a private repository history and projects public releases as clean,
reproducible commits onto the public repository. Prior public releases (v0.1.0 through
v0.10.0) built a squashed candidate commit locally with an annotated tag and anticipated
direct publication to public `main`.

For the v0.11 release architecture, user governance accepts the exact public branch route
**staging -> main PR -> release**. Public releases must not bypass this pull request
review and CI validation boundary. The implementation choices below were reviewed under the
APGR-V0110-READINESS4 pre_final review and are formally dispositioned in APG144. They separate
into machinery implemented and qualified locally versus operations requiring live-host
execution during the attended staging and release phases.

1. **Premerge base requirement**: The public `main` branch tip prior to merge must strictly
   match the accepted public base (for v0.11, the accepted public v0.10 base). If the public
   `main` branch tip has moved, the process must immediately halt, rebind, and requalify
   against the updated base. The staging PR must never bypass this base verification.
2. **Squash commit subject**: When the staging PR is merged to `main`, GitHub squash merge
   must adopt the explicit subject format: `Release v0.11.0` (or `Release v<version>`).
3. **No predicting GitHub squash SHA**: GitHub creates the squash merge commit dynamically,
   generating committer metadata and timestamps that cannot be predicted ahead of merge.
   Tooling must never attempt to predict the GitHub squash commit SHA.
4. **Separation of modes**: Release procedures must separate into three distinct phases:
   - Untagged PR candidate mode: builds and verifies the staging candidate branch and tree
     without requiring release dates, author overrides, or premature annotated tags.
   - Actual merged source checks: verifies the actual merged commit on public `main` after
     squash merge (verifying sole accepted-base parent, approved PR, checks, and projected tree).
   - Final tagged release: verifies and creates the annotated tag `v<version>` only after the
     actual merged commit exists on `main`.
5. **Post-merge binary rebuilds**: Binaries and distribution packages containing embedded commit
   metadata (such as Go build info and git commit SHAs) cannot be finalized before merge because
   the squash commit SHA is unknown prior to merge. They must be rebuilt, requalified, and rescanned
   after merge against the actual merged commit on `main`.
6. **Disclosure-before-staging**: Strict confidentiality, privacy boundary (`private/` exclusion),
   intellectual property rights, and clean history checks must be satisfied before creating the
   public staging PR. No force overwriting of public branches is permitted. Actual branch protection
   rules are enforced in later governance phase V0110-G. Existing public v0.10
   objects remain immutable. Staging corrections bind changed source and require
   candidate requalification; they do not overwrite public history.

## Accepted implementation contract

The contract distinguishes implemented and locally qualified machinery from operations
deferred to live-host execution:

### Implemented and locally qualified in APGR tooling
- **Untagged PR candidate mode**: `bin/apg-public-release build --untagged` and
  `check --untagged` construct and validate the single-parent candidate commit on `staging`
  without annotated tags or release date stamps.
- **Actual merged source checks**: `bin/apg-public-release merged-check` validates squash
  merge commits on `main` against prospective source and base.
- **Disclosure-before-staging checks**: Local qualification checks confidentiality,
  `private/` exclusions, and license/notice files prior to staging push.
- **Attended stage-only operator**: Maintained release staging operator tooling enforces
  base identity, untagged candidate verification, staging push without tags or history transfer,
  and PR creation with public-safe release notes.
- **Staging correction commit discipline**: When hosted CI or review detects defects on the public
  staging PR prior to merge, corrections are prepared as ordinary, linear fast-forward commits
  on top of the existing staging branch head. Force-pushing (`+`), history rewriting, branch deletion,
  and new PR creation are strictly forbidden. The stage operator operates in `--update` mode,
  verifying that the public base commit is in candidate ancestry, the immediate parent matches
  the expected prior staging tip, the open PR is preserved and reused, and post-push readbacks
  confirm exact remote commit and tree identity.

### Deferred to live-host execution (attended staging and V0110-G)
- **Premerge tip enforcement**: Live read of remote `main` immediately prior to merge.
- **Host PR and CI readback**: Reading hosted PR approval and `public-pr-gate` check runs.
- **Post-merge binary rebuild**: Rebuilding and scanning commit-bound binaries on the squash SHA.
- **Annotated release tagging and package publication**: Executed only after verified merge.

## Alternatives

- Direct push of tagged release to `main`: rejected; user explicitly directs staging -> main PR ->
  release workflow with pull request governance.
- Predicting GitHub squash commit SHA: rejected; GitHub generates non-deterministic committer and
  date metadata during squash merge, making pre-merge SHA prediction impossible and brittle.
- Pre-merge tagging on staging branch: rejected; tagging unmerged staging commits creates disconnected
  tags if squash merge creates a new commit object on `main`.
- Building release binaries before PR merge: rejected; binaries embedding git commit metadata would
  contain the staging branch SHA instead of the final release commit SHA on `main`.

## Consequences, rollback and deferred decisions

- Release candidates can be built and audited in untagged mode prior to PR submission.
- Public `main` history remains clean single-parent squash commits with subject `Release v<version>`.
- Rollback before merge is trivial: close the staging PR and delete the staging branch.
- Rollback after merge requires explicit release coordination; no force-push is permitted on public `main`.
- Formal GitHub branch protection rules are scheduled for implementation in V0110-G.
