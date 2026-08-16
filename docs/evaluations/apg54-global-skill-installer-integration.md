# APG54 Global Skill Installer Integration

## Result

APG54 is complete. The exact APG53 recovery shape—one formal phase commit,
its sole-parent forward baseline-audit correction, and one managed omnibus
containing both complete Git-show records plus the correction-associated
operational record—was verified before work began. Development and remote
main were equal at that corrected object.

The supplied Bash prototype was identified as 944 bytes with SHA-256
`2548411aec0848cfa44743730280c18901bb6131ffc01e1af28aebb88810e3b9`.
Its intended convenience workflow was retained, but its expression was not
used as the production implementation.

## Prototype disposition

The review confirmed all eight declared defect families:

- argument access and agent selection were not bounded;
- personal paths were embedded;
- Codex used an obsolete implicit destination;
- multiple sources were applied as sequential one-source cleanups;
- cross-repository output names could be renamed or collide;
- no combined ownership or rollback existed;
- agent roots lacked a current source-of-truth review; and
- coexistence with existing APG owners was undefined.

The replacement is a thin `bin/install-global-skills` launcher over maintained
Python modules. It uses only the Python 3.10+ standard library.

## Command

```text
install-global-skills AGENT [REPOSITORY ...] [options]

install-global-skills codex
install-global-skills claude
install-global-skills codex repo-a repo-b
install-global-skills claude repo-a --include-apg
```

`AGENT` is exactly `codex` or `claude`. With no repository arguments, the
source is
`${LOCAL_PROJ_INSTALL:-$HOME/.local/share}/agentic-praxis-grimoire/skills`.
Explicit repositories replace that default; `--include-apg` adds it back.
`--apg-root` overrides only the APG repository.

Codex defaults to `$HOME/.agents/skills`. Claude defaults to
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills`. `--skills-root` is an exact
destination override, and `CODEX_HOME` is not consulted for the default.
`--check`, `--dry-run`, `--uninstall`, canonical JSON, deterministic text, and
documented exit classes 0, 1, and 2 are supported.

The compatibility facts were refreshed on 2026-07-28 from the official
[Codex Build skills documentation](https://learn.chatgpt.com/docs/build-skills)
and [Claude Code Skills documentation](https://code.claude.com/docs/en/skills),
with `CLAUDE_CONFIG_DIR` behavior checked against the official
[Claude directory documentation](https://code.claude.com/docs/en/claude-directory).
These mutable facts require review when agent discovery documentation changes.

## Inventory, ownership, and coexistence

All local repositories are inventoried before mutation. Discovery uses direct
regular `SKILL.md` markers, skips metadata and dependency directories, never
follows source symlinks, and never executes or fetches source content. Skill
directory basenames become global names. Exact or case-insensitive duplicates
fail closed; the command does not rename them.

One closed, owner-only state file records the complete deterministic source
set, owned link targets and hashes, created containers, installation identity,
and generation. Updates add new names, refresh hashes and targets, and remove
stale names only when state proves ownership. The destination lock, second
preflight, no-overwrite link staging, state-last commit, and rollback backups
bound one combined transaction.

`flatten-skill-symlinks` remains the one-source, explicit-destination utility.
`apg-user-skills` remains the APG-only, verified-release lifecycle. The new
command refuses unmanaged collisions, flattener metadata, and a destination
claimed by the APG user lifecycle. No migration or adoption was performed.

## Verification and boundaries

Failing-first characterization reproduced the prototype's unbounded argument
failure and two-source one-state incompatibility. Focused unit and integration
tests cover roots, source-set semantics, discovery, collisions, state safety,
ownership, read-only modes, update, stale cleanup, rollback, concurrency,
uninstall, canonical output, and source preservation. Disposable Codex and
Claude roots exercised default APG, two sources, `--include-apg`, check,
dry-run, update, omission, collision refusal, unmanaged preservation, and
uninstall.

ADR 0033 is Accepted. The command and its maintained owners are future-v0.5
candidate content; immutable historical v0.4 policy remains reconstructible.
The skill library remains 28/28/28 with fourteen stable and fourteen
provisional entries. ADR 0031 remains Rejected, all ten Web/Node candidates
remain deferred, and corrected public and active v0.4.0 are unchanged.

No live Codex or Claude installation, agent invocation, package/plugin
installation, source execution, readiness, publication, deployment, Web/Node
work, browser work, or successor phase occurred.
