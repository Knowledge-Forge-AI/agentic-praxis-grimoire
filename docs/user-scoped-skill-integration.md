# User-Scoped Skill Integration

## Supported discovery model

Official Codex skill documentation was inspected on 2026-07-20 at
[Build skills](https://learn.chatgpt.com/docs/build-skills.md). It documents
repository discovery under `.agents/skills` between the working directory and
repository root, user discovery under `$HOME/.agents/skills`, support for
symbolic-link targets, and duplicate skill names that are not merged and may
both appear. Codex normally detects skill changes automatically; a full restart
is the documented fallback when a change does not appear. Plugins are the
preferred broader distribution mechanism.

Those facts are current compatibility evidence, not timeless APG policy.
APG12 supports one maintainer-scoped integration from a local public APG
release checkout. It does not create a plugin.

## Command and source requirements

[`bin/apg-user-skills`](../bin/apg-user-skills) is a Python 3 and Git command:

```text
apg-user-skills list --source <public-checkout> [--format text|json]
apg-user-skills install --source <public-checkout> [--skills-root <path>]
apg-user-skills adopt --source <public-checkout> [--skills-root <path>]
apg-user-skills check [--skills-root <path>] [--repo <path>] \
  [--format text|json]
apg-user-skills update --source <new-public-checkout> [--skills-root <path>]
apg-user-skills rollback [--source <restored-public-checkout>] \
  [--skills-root <path>]
apg-user-skills uninstall [--skills-root <path>]
apg-user-skills --help
```

Exit `0` is success, exit `1` is source, state, ownership, or lifecycle
noncompliance, and exit `2` is invalid usage.

The source must be a clean, tagged, non-bare APG public checkout with exactly
the six canonical skills, no tracked `private/` path, and a valid public skill
library. Public v0.1.0 is accepted only by its exact commit and tree identity;
later sources must carry the strict public policy and descend from the accepted
v0.1.0 commit while preserving its tag. The command validates the tag, commit,
tree, policy, history, and skill hashes and never mutates the source. The
default discovery root is `$HOME/.agents/skills`;
`--skills-root` exists for isolated tests or separately authorized alternate
local roots. The command never writes Codex configuration or a target
repository.

APG12A strengthens “descend” into one shared release-lineage contract used by
the release and user tools. Exact public v0.1.0 remains the special root.
Every later commit must be the next single-parent release, carry exactly one
matching SemVer tag and matching release subject, and preserve all preceding
release tags. Merge, retagged, truncated, untagged-intermediate, or
current-tag-mismatched sources fail before any user link or state mutation.

## Ownership and lifecycle

The command creates six direct absolute symbolic links, one for each canonical
skill. It does not create an aggregate directory link or copy skill content.
State lives under
`${XDG_STATE_HOME:-$HOME/.local/state}/agentic-praxis-grimoire/` in a strict
schema-version-1 JSON file. State records the exact skills root, current and
previous source version, tag, commit, tree, skill hashes, six managed names, and
identity of containers created by the command. State and the separate
persistent lock are mode `0600`; replacement of valid state is atomic.

- `list` validates and reports the six source skills without writing state.
- `install` requires six absent destinations and records only the links and
  containers it creates.
- `adopt` requires six pre-existing exact compatible direct links. It claims
  those links but not their parent containers.
- `check` proves state, immutable source identity, exact raw link targets, and
  managed names. With `--repo`, it also reports matching repository-scoped
  names as warnings without asserting precedence or invocation source.
- `update` verifies the current installation, preflights all replacement
  paths, records the current source as previous, retargets the links, and
  commits state last.
- `rollback` retargets to the exact stored previous identity. An explicit
  `--source` is accepted only when its immutable identity matches the stored
  previous source.
- `uninstall` removes only exact state-proven links. It removes only unchanged,
  empty containers whose recorded device, inode, owner, and mode prove that the
  tool created them. Unrelated user skills remain untouched.

Mutating success reminds the user that a full Codex restart may be needed if
the discovery change does not appear.

`check` is structurally read-only. It computes state paths without creating
them, requires the existing safe state directory and persistent lock of a
managed installation, opens that lock without `O_CREAT`, and holds a shared
nonblocking lock while validating state and links. Missing or incomplete state
fails without creating or replacing a directory, lock, state file, or link.
Install, adopt, update, rollback, and uninstall retain the exclusive persistent
mutation lock.

The existing state directory must remain mode `0700`. Read-only `check` rejects
an overpermissive directory without repairing or otherwise changing it.

## Migration and isolated validation

An existing user-owned or legacy aggregate-link setup must not be normalized
implicitly. Review its public source, six names, link shape, ownership, update
owner, and rollback boundary first. Rehearse install, check, update, rollback,
and uninstall with temporary `HOME`, XDG state, discovery root, public release,
and candidate. Only a separately authorized phase may replace active discovery
state. APG12 performed the comparison read-only. APG14 preserves the existing
maintainer-owned aggregate-link shape and updates it only by fast-forwarding
the public source checkout from v0.1.0 to v0.2.0. It does not use `install`,
`adopt`, `update`, `rollback`, or `uninstall` against that active integration,
does not create schema-version-1 user state for it, and does not change Codex
configuration. A full restart and fresh-session discovery smoke remain external
application observations after the source update.

Project-local adoption remains a separate operation owned by
[`apg-project-skills`](project-skill-projection.md). User and project scope have
different roots, state, duplicate behavior, exclusion rules, and removal
authority and therefore do not share a command.

## Failure recovery and privacy

On a refusal, preserve the state file and inspect source identity, all six raw
link targets, container identity, and the diagnostic before retrying. State-last
updates make interruption visible; they do not guess ownership. A competing
operation holds the persistent advisory lock. Do not remove a mismatched link,
container, or state file merely to make a command pass.

State necessarily records local source and discovery paths and is private
user-local data. Do not publish it, commit it, or include it in public reports.
The command performs no network access, package installation, registry or daemon
operation, plugin management, or invocation-source inference.

## Limitations

The source checkout must remain available because the installation uses direct
links. Validation proves mechanical public lineage and structure, not publisher
signature or cryptographic authenticity. Advisory locking does not defend
against a hostile same-user writer.
Six link replacements are not one filesystem transaction; conservative
state-last recovery favors refusal over ambiguous cleanup. Discovery and check
success do not establish automatic invocation, precedence, maturity, or plugin
distribution.
