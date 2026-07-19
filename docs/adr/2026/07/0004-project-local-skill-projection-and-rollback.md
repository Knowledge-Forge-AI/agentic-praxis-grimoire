# ADR 0004: Project-Local Skill Projection and Rollback

## Status

Accepted

## Date

2026-07-19

## Acceptance authority

The human maintainer's APG7 assignment accepts this decision. The assignment
authorizes one focused project-local projection command and its documentation,
tests, and evidence. It does not authorize global Codex or plugin mutation,
automatic project enrollment, or changes to another real project.

## Context

APG4A established that the six canonical APG skills remain under
`skills/<skill-name>/SKILL.md` while Codex repository discovery uses symbolic
links under `.agents/skills/`. APG5 confirmed discovery and explicit use through
the checked-in APG projection. APG6 then used equivalent manually created links
in a second real repository and recorded that a full Codex application restart
was needed before those links appeared in the observed environment.

Manual links proved the cross-repository representation, but they did not
provide machine-verifiable ownership, conflict handling, local Git exclusion,
or safe removal. APG also needs an uninstall path as one documented component
of its still-incomplete Superpowers decommission gate. A project-local tool can
close those narrow operational gaps without becoming a plugin, package manager,
registry, daemon, or global installer.

## Decision

### Canonical source and target projection

`bin/apg-project-skills` derives the physical APG root from its own installed
location. It validates the accepted direct-child canonical leaves and matching
frontmatter names before using them. Callers cannot supply an alternate source.

A target is resolved through Git and must be a non-bare worktree. Each managed
entry is a local symbolic link at
`.agents/skills/<skill-name>` whose absolute target is the exact matching APG
canonical skill directory. Absolute targets are permitted because the APG and
target repositories may be unrelated filesystem siblings; local paths remain
runtime state and do not enter public artifacts.

### Command grammar

The supported command surface is:

```text
apg-project-skills list
apg-project-skills install [--repo <path>] [--skill <name> ...]
apg-project-skills adopt [--repo <path>] [--skill <name> ...]
apg-project-skills check [--repo <path>] [--skill <name> ...]
apg-project-skills uninstall [--repo <path>] [--skill <name> ...]
apg-project-skills --help
```

`--repo` defaults to the current Git worktree. Repeated `--skill` options select
canonical names. `install` and `adopt` default to all six skills; `check` and
`uninstall` default to the locally managed set. Unknown names and malformed
arguments are usage failures with status `2`. Safety, state, and operational
failures use status `1`; success uses status `0`.

### Git-local ownership state

The exact path returned by Git for `info/apg-project-skills-v1` contains one
strict JSON object with:

- `format_version`, equal to `1`;
- `apg_root`, the physical absolute APG root used by the links;
- `target_root`, the physical target worktree that owns the projections;
- `managed_skills`, a sorted unique list of canonical names;
- `created_containers`, the subset of `.agents` and `.agents/skills` created by
  the tool; and
- `exclude_separator_added`, a Boolean used to preserve pre-existing exclude
  bytes during final removal.

Unknown or duplicate keys, invalid types, duplicate or unknown skills, an
unsupported version, an unexpected source or target root, unsafe permissions,
or an unsafe file type invalidate the state. The state is private, untracked
Git metadata written by same-directory temporary-file replacement. It is the
sole authority for destructive uninstall ownership. Existing paths are never
claimed implicitly.

Mutations serialize with a non-blocking advisory lock on the state-file inode.
For a first mutation, an exclusively created empty state placeholder supplies
the lock inode and is removed on an ordinary pre-commit failure. An empty
unlocked placeholder after interruption is invalid state and stops later work
for explicit inspection; no automatic stale-lock recovery is attempted.

### Git-local exclusion

The tool owns at most one block in the Git-local `info/exclude` file:

```text
# BEGIN APG PROJECT SKILLS V1
/.agents/skills/<skill-name>
# END APG PROJECT SKILLS V1
```

The body contains one exact root-anchored path per managed skill in sorted
order. Duplicate markers, malformed framing, duplicate or unexpected entries,
and disagreement with valid state fail closed. Updates use atomic replacement
and preserve unrelated bytes. The tool never edits `.gitignore` and never
ignores `.agents/` broadly.

### Install and adoption

`install` creates only missing projections. It is idempotent when valid state,
links, canonical leaves, and exclusion agree exactly. It refuses tracked paths,
ordinary-file or directory conflicts, symlinked parent directories, unmanaged
existing links, changed managed links, invalid state or exclusion, and any
condition that would require force. There is no force option.

`adopt` is the explicit transition for compatible manual links. Before claiming
ownership, it proves that every requested path is untracked, is a symbolic link
to the current matching canonical directory, exposes a readable matching
`SKILL.md`, and can be represented by the exact exclusion block. It does not
create, replace, or retarget a projection.

### Check

`check` is read-only. With valid local state it verifies the complete state
schema, source root, requested membership, canonical leaves, link types and
targets, tracked-path absence, exclusion agreement, and clean normal Git status
for managed paths. A compatible manual link without state is not reported as
managed success. A fully uninstalled repository with no state or APG exclusion
block is a compliant no-op state when no explicit skill was requested.

### Uninstall ownership and rollback

`uninstall` removes only requested links named by valid local state after
proving every selected path is still the exact untracked symbolic link the tool
owns. Any missing, retargeted, tracked, or non-symlink path stops the complete
requested operation before removal.

After selected links are removed, exclusion and state are updated atomically;
state is removed only after the final owned links and exclusion block are gone.
If an ordinary failure occurs before state commit, the tool restores links and
the previous exclusion content. It removes `.agents/skills` or `.agents` only
when the directory is empty and state records that the tool created it. Any
unrelated content is preserved. Repeating uninstall after complete removal is a
successful explicit no-op.

For install and adoption, links and exclusion are committed before ownership
state. An interruption can therefore leave unclaimed compatible links or an
orphan exclusion block, but not valid state claiming links that were never
created. For uninstall, state remains authoritative until link removal and
exclusion update finish; interrupted disagreement stops subsequent mutation
for inspection and repair rather than guessing ownership.

### No-global-state boundary and restart guidance

The tool reads and writes only the opted-in worktree projection directory and
the Git-resolved local state and exclusion files. It does not inspect or modify
user-level Codex configuration, plugin state, Superpowers files, or another
project automatically.

Successful mutating commands remind the user that a full Codex application
restart may be needed before additions or removals appear. This is operational
guidance from the observed APG6 environment, not a claim that the tool controls
Codex caching or plugin state.

## Alternatives considered

### Manual links only

Manual links remain compatible evidence and can be adopted when exact. They are
not the selected default because they provide no durable ownership proof,
conflict diagnostics, exclusion management, or bounded uninstall operation.

### Copied skill directories

Rejected. Copies create a second source of truth, can drift from reviewed
canonical content, and complicate provenance and rollback.

### User-global installation

Rejected. Global installation expands the authority and blast radius, obscures
project opt-in, and would interact with user-level discovery state outside
APG7's authority.

### Project-local managed links

Accepted. Exact symbolic links preserve one canonical source while Git-local
state supplies explicit ownership and removal proof at the smallest authorized
scope.

### Plugin packaging

Rejected. A plugin is unnecessary for local filesystem projection and would add
packaging, lifecycle, compatibility, and global-state concerns outside APG7.

## Consequences

- A repository can opt into any or all six APG skills without tracked changes.
- Manual compatible links require an explicit adoption step before managed
  uninstall is available.
- Moving the APG checkout can invalidate managed absolute links and state; the
  supported path is to uninstall before moving and reinstall afterward.
- Linked worktrees may share the Git-resolved `info` path. Target-root ownership
  prevents one worktree from treating another's state as its own; version 1
  permits only one managed target for a shared state path at a time.
- Strict conflict and state validation can require manual inspection after an
  abrupt interruption. This is preferred to destructive inference.
- The executable requires Python 3.10+, Git, symbolic-link support, and POSIX
  file locking as available in the supported macOS environment. It uses only
  the Python standard library and portable Git commands; it does not require
  GNU path tools, Homebrew, Nix, a network, or third-party packages.
- The projection uninstall path and a human Superpowers rollback runbook can
  satisfy the rollback-plan documentation component of the decommission gate.
  They do not satisfy the human decision, actual removal, or post-removal smoke
  components.

## Security and portability risks

- Filesystem races are reduced through Git root resolution, parent and file-type
  checks, non-blocking locking, atomic replacement, and immediate pre-mutation
  revalidation. The tool does not claim protection against a hostile local user
  with concurrent write access to the target repository.
- Symbolic links are never followed as writable parents. Managed link targets
  must resolve to the exact physical canonical directory.
- The state file contains a machine-local APG path. It remains private Git
  metadata and must not be copied into public evidence.
- Advisory locking depends on cooperating writers. Unmanaged edits are detected
  by exact state, link, and exclusion checks rather than silently overwritten.
- Python, Git, and POSIX symbolic-link and locking semantics define the current
  portability boundary. Other operating systems remain unverified.

## Rollback

For a healthy managed repository, run `apg-project-skills uninstall` and then
restart Codex if the application still presents removed project skills. The
command removes only state-proven links and its exact local exclusion block.

If state, links, or exclusion disagree, do not force removal. Inspect the
reported invariant, restore the exact expected link or exclusion content when
ownership is known, run `check`, and retry uninstall. If the APG checkout was
moved, restore its former location long enough to uninstall or perform a
carefully reviewed manual cleanup of the target's Git-local APG records.
Historical APG decisions, evaluations, and provenance remain intact.

## Non-goals

- global Codex or Superpowers installation, removal, or configuration;
- automatic enrollment or discovery of target repositories;
- skill copying, synchronization, updates, version selection, or packaging;
- a plugin, registry, daemon, package manager, or generalized harness adapter;
- control over Codex process lifetime, caching, or restart behavior;
- modification of tracked target files;
- network access or remote repository operations;
- support for arbitrary caller-provided skill sources; and
- decommissioning Superpowers in APG7.

## Deferred decisions

- broader operating-system and Git implementation support;
- public release, packaging, APG licensing, and contribution policy;
- additional harness projections or global installation mechanisms;
- skill version selection and canonical-checkout relocation automation;
- broader repeated real-project use and regression evidence;
- promotion of any skill beyond `provisional`;
- an explicit human Superpowers decommission decision;
- actual global Superpowers disable or removal; and
- post-decommission smoke validation.
