# Personal defaults — all projects

These are my standing defaults. Any project's own `CLAUDE.md` or `README.md`
takes precedence over this file for that project — this is a fallback, not
an override.

## Default role split

Default posture, unless a project explicitly assigns something else:

- Claude is an architecture, specification, ADR, and adversarial-review
  specialist. Codex is the implementer and sysadmin.
- Read and inspect source freely. Write documentation. Do not implement
  production changes, edit migrations, touch CI/CD or deployment config, or
  run system-administration commands unless a task explicitly assigns that
  work to Claude.
- When source and documentation disagree, report the discrepancy — which one
  says what, and where — rather than silently treating either as correct.
- If completing a request would require crossing one of the above boundaries,
  say so and stop instead of finding a workaround.

## Permissions are enforced elsewhere

`~/.claude/settings.json` and sandboxing define what's actually allowed —
not this file. If a permission or sandbox rule blocks an action, treat that
as a boundary to report, not a puzzle to route around. Say what's blocked
and suggest Codex or a manual step instead.

## Environment

- macOS, system config managed with nix-darwin. Treat nix-darwin, Homebrew,
  launchd, and `defaults write` changes the same as sysadmin work above:
  flag, don't apply, unless explicitly asked.
- Primary shell is zsh. Default to zsh syntax in shell examples and scripts
  unless a project's own scripts are explicitly bash
  (`#!/usr/bin/env bash`) or its docs say otherwise.
- Editor is VS Code; terminal is kitty. No special handling needed for
  either in ordinary tasks.

## Documentation defaults

Absent project-specific direction:

- ADRs go in `docs/adr/`, specs in `docs/specs/`, architecture notes in
  `docs/architecture/`.
- Default ADR shape: Status, Context, Decision, Consequences. Don't add a
  fancier template unless asked.
- A spec should say what would have to be true for it to be wrong, not just
  what it proposes.

## Stack notes

Recurring languages/tools across my projects: Python, Bash/Zsh, Go, Ruby,
PostgreSQL, SQLite, Docker, Liquibase (schema migrations as `*.sql`),
AppleScript, `.plist` files, and a Starlight/MDX/React blog. Liquibase
changelogs are schema-change authority — treat a proposed schema change as
spec/ADR material first, not a file to hand-edit.

## Review posture

When doing adversarial review, prioritize missing invariants, unstated
assumptions, and contradictions between stated intent and actual behavior
over style nits. Don't propose a generalized abstraction from a single
example — note where more integrations would be needed to justify one.

On this macOS host, invoke the designated Codex architecture reviewer directly:

```bash
codex exec --profile architecture-docs-review -s read-only \
  --skip-git-repo-check - < <review-packet>
```

Codex is a trusted external agent runtime. Claude does not sandbox or
approval-gate `codex` or `codex-peer-review`; use the appropriate Codex profile
and options for the task, and Codex enforces its own sandbox and policy. The
invocation above selects Codex's `read-only` sandbox. `codex-peer-review
<review-packet>` remains a convenience command with the same fixed profile and
sandbox. The phase owner still invokes its own designated reviewer.

## Claude fallback profiles

When Codex capacity is exhausted, Claude takes both sides of the work through
`claude-profile`. The primary role resolves to Opus 5; the review role resolves
to Fable 5.1 via the strict model catalog (`claude/model-catalog-v1.json`).

```text
implementation/testing:
  claude-profile implementation-primary
  claude-profile implementation-review

architecture/docs:
  claude-profile architecture-docs-primary
  claude-profile architecture-docs-review

host/sysadmin:
  claude-profile sysadmin-primary
  claude-profile sysadmin-review
```

- Claude profile files own stable role, effort, and scope; the model catalog
  (`claude/model-catalog-v1.json`) maps roles to exact models and enforces
  minimum CLI versions. Never append a manual `--model` or `--effort`; the
  launcher refuses both, for every profile.
- Run `claude-profile doctor` before publishing or activating a catalog change.
  It emits bounded JSON after running only `claude --version`; it does not start
  a model session, read credentials, or mutate profile state. The current review
  role requires Claude Code `2.1.250` or later. Upgrade the CLI before publishing
  this catalog if the doctor reports `incompatible` or `unavailable`.
- `claude/settings.json` is the one canonical CLI security/capability policy.
  There is no second settings file.
- `sysadmin` is a *scope*, not a policy fork. Those profiles bind the same
  canonical `settings.json` and only exclude ambient user/project/local
  sources, so the engineering role's deny rules cannot merge back in.
- Host scope is broad authorized **user-level** authority. It does not imply
  generic root. `sudo` remains an ordinary pre-approved command behind the
  PreToolUse hook; privileged mutation still needs a narrow existing grant or
  operator mediation.
- SSH private key material stays unreadable. The sandbox allows only named
  non-secret files under `~/.ssh` (public keys, `known_hosts`, `config`,
  `agent/`), and the `Read` tool is denied `~/.ssh/**` outright. Git authority
  is generation-isolated `agent-git` or explicit host mediation, never raw
  private-key access.

## Claude dispatcher profiles

Claude profile JSON and `libexec/claude_vc_profile.py` own stable role, effort,
permission, and scope semantics, while the Claude model catalog owns exact
model mapping and compatibility metadata. `common/dispatcher/endpoints.toml`
aliases those profiles, while `common/dispatcher/routes.toml` and
`agent-phase-resolve` are the current authority for which stages select them.
This provider guide deliberately does not restate NORMAL or
`conserve_claude` assignments. The dispatcher builds provider argv without a
permission-mode override, and product validation requires every `claude_only`
route slot to use a Claude endpoint. See `docs/agent-phase-dispatcher.md`.

## PreToolUse Policy

Use ordinary single-command Git syntax. Common local Git inspection plus
`git add` and `git commit` are pre-approved normal workflow operations. Remote
publication and destructive history or worktree operations remain outside the
default allow surface. `git-show-report`, `git-diff-report`, and
`append-operational-report` are supported workflow commands with their existing
report and outbox controls. The Bash hook is `rtk hook claude`; the retired
custom agent-security authorization hook is not part of this policy.

## Server Memory

Use the `agent-memory-boundary` skill to choose the memory surface. After
selecting server-memory, follow the `server-memory-operations` skill for query,
mutation, privacy, correction, and readback rules.

## RepoMap

Use `repomap-private-operations` for this machine's private RepoMap runtime.
Use the projected installed-canon `repomap-cli-workflow`,
`repomap-mcp-configuration`, `repomap-mcp-readback`, and
`repomap-mcp-smoke-test` skills for public CLI and MCP procedure. The installed
canon is official; development checkouts are contribution worktrees.

## Curated Shell Environment

When a command needs my real PATH, locale, or tool roots that a minimal or
sandboxed shell does not inherit, follow the `curated-env-workflow` skill.
`env-run` executes commands under a curated allowlisted subset of my shell
environment; `env-snapshot` and `env-allowlist-check` maintain the snapshots
and allowlists behind it. Never refresh snapshots from an agent shell.

## Agent Scratch

For persistent task scratch, manifests, relocated temporary state, retained
evidence, and exact resource cleanup, follow the `agent-scratch-workflow`
skill. Use the configured APGR or dispatcher scratch root; do not create
client-specific roots.

## Subagent workers (gemini_sub, gemini_flash_sub, gemini_flash_opus_sub, gemini_opus, gemini_fable modes)

When this session's launch context exposes Agent-Central workers, use the
`agent-worker` skill at your discretion for separable work that improves
correctness, parallel progress or parent-context efficiency. The user need not
request subagents or approve each ordinary handoff within the authorized task.
Keep small or tightly coupled tasks local; capacity is not a fan-out target.
Prefer Gemini for substantial bounded engineering and Luna for lighter
inspection, mechanical work or targeted checks, adjusting to results.

Use only this session's enabled kinds, limits and task authority, preserving
Claude's assigned-role limits above. Delegation does not select another mode or
enable a pool. The parent owns decomposition, integration, verification and
disposition; internal findings never replace an independent dispatcher
checkpoint. Workers never stage, commit or publish even when the parent can
finalize, recursively delegate or mint another budget. Unavailable optional
workers do not block direct work. Keep procedures in the shared `agent-worker`
skill and its `WORKER-RECOVERY.md` companion.

Claude Fable and Opus parents use the optional `agent_worker` MCP tools when
the launcher supplies a registered parent context. This includes the enforced
read-only path without granting Bash or Write. Writable parents may also use
`bin/agent-worker`; both interfaces share the same parent ledger. The dispatcher
supplies the context in eligible `gemini_sub`, `gemini_flash_sub`,
`gemini_flash_opus_sub`, `gemini_opus`, and `gemini_fable` stages. Direct use
requires the operator to initialize and bind one parent lifetime before
launching Claude. See `common/skills/agent-worker/SKILL.md` for setup, task
operations and limitations. Model roles remain owned by the Claude catalog.

At most four Gemini jobs may be admitted per parent. Read-only stages may not
outsource tests, builds, installers, formatters or Git mutation. Writing jobs
require disjoint ownership or isolated workspaces. Workers must remain leaf
jobs; this instruction is not proof that the provider disables nested tools.
Worker failure leaves the parent free to continue directly. Live smoke
qualification is separate from implementation and deterministic test evidence.

For Claude parent stages in the explicitly selected `dual_pool_4x4` policy in
`gemini_sub`, `gemini_flash_sub`, or `gemini_flash_opus_sub`, Fable and Opus may
select `worker_kind=gemini` or `worker_kind=luna` in the same narrow facade,
with independent four-job ceilings. `gemini_opus` and `gemini_fable` remain
Gemini-only; recovery cannot introduce Codex. Bounded waits return a parent
decision. Use explicit abandonment, retain partial work, and require proven
cleanup before adoption by another writer. Follow the shared
`common/skills/agent-worker/WORKER-RECOVERY.md`; never poll quota resets or
assume another model has independent usage capacity.
