# Project-Local APG Skill Projection

## Purpose

`apg-project-skills` manages opt-in Codex project discovery links from a target
Git worktree to the six canonical APG skills. It installs, adopts, checks, and
removes local symbolic links without copying skill content, changing tracked
target files, or modifying user-level Codex or Superpowers state.

[ADR 0004](adr/2026/07/0004-project-local-skill-projection-and-rollback.md)
defines the normative ownership, conflict, and rollback design.

## Canonical and projected skills

Canonical procedure content remains in the APG checkout:

```text
<apg-root>/skills/<skill-name>/SKILL.md
```

An opted-in target receives only a symbolic-link projection:

```text
<target-root>/.agents/skills/<skill-name> -> <apg-root>/skills/<skill-name>
```

Cross-repository links use machine-local absolute targets because the two
repositories may be unrelated filesystem siblings. Those paths are local state
and must not be copied into public documentation, fixtures, or reports.

## Prerequisites

- a readable APG checkout containing `bin/apg-project-skills` and the six
  canonical skill leaves;
- Python 3.10+ with the standard library;
- Git and a non-bare target worktree;
- local symbolic-link support and POSIX advisory locking; and
- permission to create local untracked paths and Git-local metadata in the
  target.

The current verified environment is macOS. The command requires no network,
Homebrew package, Nix-only tool, or third-party Python package.

## Commands

List the canonical names without a target repository:

```sh
<apg-root>/bin/apg-project-skills list
```

Install every skill in a target:

```sh
<apg-root>/bin/apg-project-skills install --repo <target-path>
```

Install a subset by repeating `--skill`:

```sh
<apg-root>/bin/apg-project-skills install \
  --repo <target-path> \
  --skill <skill-name> \
  --skill <another-skill-name>
```

Adopt compatible manually created links:

```sh
<apg-root>/bin/apg-project-skills adopt --repo <target-path>
```

Verify all locally managed skills:

```sh
<apg-root>/bin/apg-project-skills check --repo <target-path>
```

Remove selected or all locally managed skills:

```sh
<apg-root>/bin/apg-project-skills uninstall \
  --repo <target-path> \
  --skill <skill-name>

<apg-root>/bin/apg-project-skills uninstall --repo <target-path>
```

When `--repo` is omitted, Git resolves the worktree containing the current
directory. Install and adopt default to all six canonical skills. Check and
uninstall default to the valid locally managed set.

## Target effects

The command may create or update only:

```text
<target-root>/.agents/skills/
<target-git-path>/info/exclude
<target-git-path>/info/apg-project-skills-v1
```

The version-1 JSON state records the physical APG root, physical target
worktree, sorted managed names, the empty parent containers the tool created,
and one exclusion-preservation flag. It is private Git metadata with mode
`0600` in the verified environment. It is the only authority for destructive
uninstall.

Git may return one shared `info` path for linked worktrees. The target-root field
prevents a sibling worktree from claiming that state. Version 1 permits only one
managed target per shared state path; check or uninstall from the recorded
target before enrolling its sibling.

The Git-local exclusion block is exact and narrow:

```text
# BEGIN APG PROJECT SKILLS V1
/.agents/skills/<skill-name>
# END APG PROJECT SKILLS V1
```

It contains one line per managed projection. The tool preserves unrelated
exclude bytes, never edits tracked `.gitignore`, and does not ignore all of
`.agents/`.

## Install, adopt, check, and uninstall

Install creates only missing links and is idempotent when state, links,
exclusion, and the effective normal Git status of the complete managed set
agree. An exact pre-existing link without ownership state is not silently
claimed; use adopt.

Adopt verifies every requested manual link before writing ownership state. Each
link must be untracked, resolve to the exact matching current canonical leaf,
and expose a readable `SKILL.md` with the matching frontmatter name. Adopt does
not replace or retarget a link. Repeated adopt reports idempotent success only
when the complete managed set also remains hidden from normal Git status.

Check is read-only. It validates the complete state schema, source root,
canonical leaves, requested membership, exact links, tracked-path absence,
exclusion agreement, and normal Git status for managed paths. A compatible
manual link without state is not reported as managed. An entirely absent state
and APG exclusion block is a compliant uninstalled state for default check.

Uninstall removes only links proven owned by valid local state and still exact
at removal time. A selected missing, retargeted, non-symlink, or tracked path
stops the operation before any selected link is removed. Subset removal updates
state and exclusion. Final removal deletes state and its exclusion block and
removes only empty parent directories recorded as tool-created. Unrelated
`.agents/skills` content and manually created parent directories remain.

Successful install, adopt, and uninstall commands remind the operator that a
full Codex application restart may be needed before the observed project-skill
set changes. The command does not control Codex process lifetime, discovery
caching, or plugin state.

## Conflict and refusal behavior

The command fails closed on:

- a non-Git, bare, or unreadable target;
- an unknown skill or malformed option;
- tracked projection paths;
- ordinary files, directories, or unmanaged symbolic links at requested paths;
- symlinked `.agents` or `.agents/skills` parents;
- broken, retargeted, or unreadable managed links;
- malformed, unsupported, overly permissive, or source-mismatched state;
- duplicate, malformed, or state-mismatched APG exclusion blocks; and
- a later ignore or negation rule that makes a managed projection visible in
  normal Git status; and
- an active cooperating mutation lock.

There is no `--force`, automatic repair, broad ignore pattern, or destructive
stale-lock recovery. Preserve the reported path, inspect the failed invariant,
and restore exact agreement before retrying.

## Moving the APG checkout

Managed links and state record the physical APG root. Before moving or removing
the checkout:

1. run `check` in each managed target;
2. run `uninstall` while the recorded APG root remains available;
3. move the APG checkout;
4. run `install` from its new location; and
5. restart Codex when needed in the observed environment.

If the checkout moved first, restore the old location long enough to perform
the proven uninstall. When that is impossible, inspect the local state, each
link, and the exact exclusion block before a separately reviewed manual cleanup.
Do not fabricate or edit ownership state to make uninstall proceed.

## Migrating manually linked repositories

For a repository with existing manual links:

1. inspect every link and confirm it resolves to the matching current APG leaf;
2. confirm each link is untracked and no broad tracked ignore rule is required;
3. run `adopt` for the intended names;
4. run `check`;
5. verify normal Git status is clean for those paths; and
6. restart Codex if the application has not refreshed project discovery.

A mismatch is not a migration candidate. Preserve or remove it manually after
determining its owner; the APG command will not retarget it.

APG8 records one real-project application of this sequence in RepoMap. Six
existing exact manual links were adopted as the default canonical set. Link
identity and targets were preserved, pre-existing exact manual exclusion lines
remained user-owned and byte-identical outside the new APG block, default and
explicit checks passed, and the tracked repository remained unchanged. This is
one deployment observation, not a general compatibility or invocation claim.

## Troubleshooting and rollback

- **Tracked path:** restore the repository's intended tracked content or choose
  another target. The command does not untrack files.
- **Unmanaged exact link:** run adopt after independently confirming its source.
- **Retargeted or missing managed link:** restore the exact state-recorded
  canonical link, run check, then retry uninstall.
- **State/exclusion disagreement:** reconstruct the exact block from valid state
  only after reviewing ownership. Do not broaden ignore scope.
- **Managed path visible despite an exact APG block:** inspect later local or
  tracked ignore rules, restore the intended exact ignore behavior without
  moving or rewriting the APG block, run check, and retry the original command.
- **Empty state file:** treat it as possible interrupted first mutation. Inspect
  links and the APG block before removing the stale placeholder or adopting
  exact unclaimed links.
- **Active lock:** wait for the other command. If no command is active, inspect
  the state file as interrupted local metadata; there is no automatic recovery.
- **Skills still visible after success:** perform a full Codex application
  restart. Persistent discovery disagreement is application-level evidence, not
  permission to alter global plugin state.

The ordinary rollback is `apg-project-skills uninstall`. It removes only proven
local ownership and leaves canonical skills, history, evaluations, and global
Codex or Superpowers state unchanged.

## Limitations

- Current portability evidence covers macOS, Python 3.10+, Git, POSIX symbolic links,
  and advisory locking.
- Advisory locks coordinate command instances, not a hostile same-user writer.
- Abrupt process loss can leave conservative disagreement requiring inspection;
  the command favors refusing uncertain cleanup over guessing ownership.
- Project projection success does not prove Codex invocation, automatic trigger
  selection, skill maturity, production readiness, or Superpowers decommission
  readiness.
- The command manages exactly the accepted six APG v0.1 skills and is not a
  general skill installer or package manager.
