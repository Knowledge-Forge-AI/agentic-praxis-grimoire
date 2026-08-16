# ADR 0033: Multi-Repository Global Skill Installation

- Status: Accepted
- Date: 2026-07-28
- Decided in: APG54
- Relates to: ADR 0009, ADR 0019, ADR 0029, ADR 0031 (Rejected),
  ADR 0032

## Context

APG already owns two distinct projection contracts. `flatten-skill-symlinks`
projects one explicit nested source into one explicit flat destination.
`apg-user-skills` manages one verified public APG release through a
release-identity-aware user lifecycle. A supplied convenience script attempted
to install several repositories by invoking the one-source flattener
repeatedly against one destination. That shape could not express one combined
desired set, collision ledger, ownership state, update, rollback, or uninstall
boundary.

Official agent documentation reviewed on 2026-07-28 places personal Codex
skills below `$HOME/.agents/skills` and personal Claude Code skills below
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills`. These are mutable external
compatibility facts and must be refreshed if either agent changes its
documented discovery model.

## Decision

APG owns `bin/install-global-skills` as a thin launcher over Python 3.10+
standard-library implementation. The command accepts exactly `codex` or
`claude`. Its implicit destinations are `$HOME/.agents/skills` for Codex and
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills` for Claude. `--skills-root`
replaces the selected destination exactly; `CODEX_HOME` is not an implicit
destination owner.

With no repository arguments, the command selects
`${LOCAL_PROJ_INSTALL:-$HOME/.local/share}/agentic-praxis-grimoire`. Explicit
repository arguments replace that default. `--include-apg` adds the resolved
APG repository to an explicit set, and `--apg-root` changes only that resolved
APG source.

Every local source must provide a safe `skills/` directory. The command
recursively discovers direct regular `SKILL.md` markers without following
source symlinks or executing repository content. A skill directory basename
is its global name. Exact and case-insensitive duplicate names fail before
destination mutation; names are never auto-prefixed or renamed.

One invocation owns one complete desired repository set. It inventories all
sources, validates destination ownership, acquires a destination lock,
rebuilds source and destination evidence under the lock, stages no-overwrite
link changes, writes command-specific state last, and removes rollback
backups only after state commit. A pre-commit failure removes new links and
restores quarantined owned links. `--check` and `--dry-run` are read-only;
`--uninstall` removes only exact state-owned links and unchanged empty
containers created by the command.

The closed state records the agent, exact destination, deterministic source
and skill roots, name-to-source links, `SKILL.md` hashes, container identities,
installation identity, and generation. The source set is intentionally the
mutable desired state of one installation lineage: changing the repository
arguments updates that lineage and removes stale owned names. Another owner,
schema, agent, or destination fails closed. This interpretation reconciles
the required source-omission update with the assignment's separate warning
against adopting state from another source set.

`install-global-skills` does not adopt unmanaged links, flattener metadata, or
an `apg-user-skills` destination. Its lock provides cooperative same-user
serialization; it is not a hostile same-user security boundary. A future
migration or deprecation decision requires separate authorization.

Arbitrary local repositories receive structural projection validation only.
The command does not assert release identity, trust, maturity, catalog
completeness, runtime compatibility, package installation, or plugin
installation. APG54 proves disposable filesystem projection, not live Codex
or Claude discovery.

The launcher, maintained helpers, tests, evaluation, ADR, and exit are
current-development and future-v0.5 public-candidate surfaces. APG54 does not
publish v0.5 or change corrected v0.4.0.

APG55 leaves this decision Accepted and unchanged. Its forward implementation
correction journals partial destination creation inside cleanup, represents
replacement mutation stages explicitly, reads private state through exact EOF
with stable metadata, rejects control-bearing path spellings, and revalidates
repository, skills-root, skill-directory, and marker identities immediately
around destination and state mutation. These are safety corrections to this
architecture, not a new architecture decision.

## Alternatives considered

- Retain the Bash loop: rejected because sequential one-source cleanups cannot
  represent one multi-source transaction.
- Reuse the flattener state schema: rejected because it binds one source root
  to one destination.
- Expand `apg-user-skills`: rejected because its verified public-release
  lifecycle and source identity are deliberately narrower.
- Auto-prefix colliding names: rejected because it silently changes
  user-facing skill identities.
- Copy skill directories: rejected because projection should remain direct
  and source updates should not create an unowned second content store.

## Consequences and rollback

Users gain one deterministic local repository-set projection for either
agent, with explicit ownership, stale cleanup, rollback, and uninstall.
Sources must remain present because installed entries are absolute symbolic
links. State contains private local paths and must not be published.

Rollback may revert the APG54 repository commit. An existing installation
must first be removed through its exact `--uninstall` contract or otherwise
left untouched; deleting state or links manually is not an authorized
migration.

## Deferred decisions

Live agent invocation, migration from existing owners, command deprecation,
plugin packaging, v0.5 readiness/publication/deployment, and hostile same-user
defense remain separate decisions. ADR 0031 remains Rejected, all ten Web/Node
candidates remain deferred, and React and Vitest retain Policy A.
