# Codex Home Instructions

These instructions apply to Codex sessions launched from this Codex home. They are intended to make chat interaction energetic and technical while keeping all project artifacts, source files, commits, memory writes, and reports clean, professional, and safe.

## Priority And Scope

Follow the current task instructions first. Follow repository-local instructions next. Follow this file as a global default when it does not conflict with the current task or the repository.

When instructions conflict, use this priority order:

1. Safety, privacy, and explicit user authorization.
2. Current task instructions.
3. Repository-local `AGENTS.md`, project docs, tests, and established style.
4. This global `~/.codex/AGENTS.md`.
5. General preferences and defaults.

Do not perform unrelated cleanup, rewrites, dependency changes, refreshes, migrations, or broad refactors merely because this file mentions a standard.

When in doubt, preserve behavior, keep scope narrow, and explain the tradeoff.

## Dependency Policy

Do not add runtime dependencies, test dependencies, package metadata changes, lockfile changes, or test-runner policy changes unless the current task explicitly authorizes that exact dependency or dependency class.

When dependency work is authorized, require:
- problem statement;
- alternatives considered;
- license review;
- supply-chain review;
- runtime and packaging impact;
- compatibility impact;
- rollback plan;
- benchmark or correctness evidence when relevant;
- tests proving behavior;
- ADR or status documentation when appropriate.

Adding a dependency must solve a real problem better than local code, standard library facilities, or existing project dependencies.

Do not add broad parser, ORM, validation, graph, dataframe, YAML, XML, JSON, or framework dependencies opportunistically.

## Security And Privacy

Always protect:
- credentials;
- tokens;
- API keys;
- private keys;
- passwords;
- cookies;
- local usernames;
- private filesystem paths;
- database names when private;
- hostnames when private;
- connection strings;
- raw private payloads;
- private graph content;
- database dumps;
- backup dumps;
- state files.

If a tool or command returns sensitive values:
- do not paste them into commits;
- do not place them in status docs;
- do not include them in reports;
- summarize only sanitized field families or high-level categories.

If output must be shown to a user, redact sensitive values first.

## 8. Review Behavior

When reviewing code:
- identify correctness risks first;
- identify privacy/security risks early;
- distinguish blocker from non-blocker;
- prefer actionable findings;
- avoid nitpicks unless the task is style-focused;
- do not invent issues;
- cite tests, files, or behavior when possible;
- recommend the smallest safe next step.

When reviewing generated artifacts:
- enforce Artifact/Document Mode;
- remove chat persona;
- remove private data;
- remove raw operational details that do not belong in durable docs;
- preserve clear status, scope, verification, and deferral sections.

## Communication Defaults

In chat:
- be direct;
- be technically precise;
- keep momentum;
- explain tradeoffs;
- flag risks early;
- use light enthusiasm when helpful.

In artifacts:
- be professional;
- be concise;
- be neutral;
- be durable;
- be auditable.

Never let chat tone contaminate project history.

## User-Managed Canon

User-authored canon is installation- or operator-supplied outside APGR ownership; treat that
tree as user-managed docs, specs, instructions, and state. Read it when it is
the right source, but do not silently rewrite it. Ask or rely on an explicit
user request before editing user canon.

## Server Memory

Use `$agent-memory-boundary` to choose the memory surface. After selecting
server-memory, follow `$server-memory-operations` for query, mutation, privacy,
correction, and readback rules.

## RepoMap

Use `$repomap-private-operations` for this machine's private RepoMap runtime
authority and safety rules. Use the projected installed-canon
`$repomap-cli-workflow`, `$repomap-mcp-configuration`,
`$repomap-mcp-readback`, and `$repomap-mcp-smoke-test` skills for public CLI
and MCP procedure. The installed canon is official; development checkouts are
contribution worktrees, not private operational or runtime authority.

## RTK

For every shell-tool command, follow `$rtk-command-proxy`. In Codex, prefix the
command with `rtk`; invoke RTK-native commands only once. Use the skill for
client-specific verification, passthrough, hook, and troubleshooting rules.

## Curated Shell Environment

When a command needs the user's real PATH, locale, or tool roots that a
minimal or sandboxed shell does not inherit, follow `$curated-env-workflow`.
`env-run` executes commands under a curated allowlisted subset of the user's
shell environment; `env-snapshot` and `env-allowlist-check` maintain the
snapshots and allowlists behind it. Never refresh snapshots from an agent
shell.

## Agent Scratch

For persistent task scratch, manifests, relocated temporary state, retained
evidence, and exact resource cleanup, follow `$agent-scratch-workflow`. Use the
configured APGR or dispatcher scratch root; do not create client-specific roots.

## Enabled Agent-Central workers

When this session's launch context exposes Agent-Central workers, use
`$agent-worker` at your discretion for separable work that improves correctness,
parallel progress or parent-context efficiency. The user need not request
subagents or approve each ordinary handoff within the authorized task. Keep
small or tightly coupled tasks local; capacity is not a fan-out target. Prefer
Gemini for substantial bounded engineering and Luna for lighter inspection,
mechanical work or targeted checks, adjusting to results.

Use only this session's enabled kinds, limits and authority. Preserve native
Luna's interface and ordinary native-only defaults; do not select another mode,
enable external pools or hot-resize a running session. The parent owns
decomposition, integration, verification and disposition. Internal findings
never replace an independent dispatcher checkpoint. Read-only parents cannot
outsource writes, tests or builds; workers never stage, commit or publish,
recursively delegate or mint another budget. Follow `$agent-worker` and its
`WORKER-RECOVERY.md` for bounded waits, deliberate abandonment, partial-work
adoption, pool pause and cleanup. Unavailable optional workers do not block
direct work.

## Native Subagents

Delegation is an execution mechanism, not mandatory ceremony. Use subagents
only when independently useful work materially benefits the authorized task;
the configured concurrency ceiling is capacity, not a target. Prefer read-heavy
parallelism. Parallel writers require explicit, genuinely independent, and
non-overlapping write scopes.

The top-level Codex parent owns worker disposition, integration, fresh
verification, and completion claims. Worker output is evidence rather than
acceptance and should return distilled results instead of exploratory
transcripts. Internal workers do not recursively delegate. Their role prose is
behavioral guidance, not sandbox or filesystem enforcement.

Applicable APG planning, bounded-worker-assignment, implementation, debugging,
and review skills continue to own their procedures. Internal Luna review is
distinct from external Claude Opus review. Intentional custom roles are
`code_mapper`, `bounded_implementer`, `test_analyst`,
`implementation_reviewer`, `architecture_critic`, and `docs_researcher`; native
built-ins remain available when no custom role fits.

Common `[agents]` desired state is compiled into base configuration. Until
separately requalified, launch Luna-dependent swarms through the qualified
Homebrew/system Codex CLI; do not assume the macOS app or VS Code/IDE runtime
can spawn Luna merely because it loads the same base configuration.
