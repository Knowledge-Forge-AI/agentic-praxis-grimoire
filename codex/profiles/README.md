# Codex parent profiles

These tracked profile files select only the model and reasoning effort for an
explicitly chosen top-level Codex parent:

Parent profiles at GPT-6 Astra medium reasoning drive phase work:

- `implementation-testing` — implementation and testing work.
- `architecture-docs-primary` — architecture and documentation work.
- `sysadmin-primary` — host and system-administration work.

Parent profiles at GPT-6 Astra medium reasoning drive adversarial review of a
bound candidate:

- `implementation-testing-review` — implementation and testing candidates.
- `architecture-docs-review` — architecture and documentation candidates,
  including Claude-authored ones.
- `sysadmin-review` — host and system-administration candidates.

The review profiles exist so that a required review can be a *separate*
top-level Codex process. `agent-phase-dispatch` launches that second process
itself; a primary must never satisfy its own required review by delegating to a
Luna worker or by invoking the Codex CLI on its own behalf. See
`docs/agent-phase-dispatcher.md`.

Select a profile explicitly with the native Codex CLI:

```text
codex --profile implementation-testing
codex-peer-review path/to/review-packet.md
```

Codex layers the selected `$CODEX_HOME/<name>.config.toml` file over the base
user `config.toml`. Per the Codex profile contract, project configuration and
command-line overrides have higher precedence. The profiles intentionally
contain no other configuration, so security, MCP, plugins, projects, memories,
shell environment, service tier, notifications, and runtime state continue to
inherit from the compiled base.

Claude treats Codex as a trusted external agent runtime: direct `codex` and the
`codex-peer-review` convenience launcher are excluded from Claude's sandbox and
pre-approved by Claude's permission layer. The selected Codex profile and
invocation remain responsible for Codex's sandbox and policy; the convenience
launcher selects the `architecture-docs-review` profile and `read-only` sandbox.

Base `model` and `model_reasoning_effort` remain mutable Desktop/runtime
passthrough values; they are not phase policy. The explicit profile selection
deterministically overrides them for that invocation. The installer owns the
compatibility symlinks from these tracked sources into `CODEX_HOME`; the files
remain outside the `config.d` source and ownership graph.

Codex CLI 0.147.0 silently continues with the mutable base when a requested
profile file is missing. A successful installer run and the expected live link
are therefore preconditions for profile use. Profile names select parent
intelligence; they are not security or authority boundaries.

Luna worker defaults and concurrency are separately owned by
`config.d/170-subagents.toml`; named worker roles are owned by `agents/*.toml`.
Neither is part of these Astra parent profiles. For `conserve_claude`, route
resolution reads that exact source and records its repository-relative path,
SHA-256, enabled state, Luna model, Max effort, and concurrency in
`resolved.json`; any semantic mismatch blocks before provider invocation.

## External Luna leaf profile

`luna-worker.config.toml` is consumed directly by Agent-Central's external
worker adapter. The adapter translates its model, Max effort and
`agents.enabled=false` into explicit launch overrides. It does not require a
live `$CODEX_HOME` profile link and does not alter the base compiler graph.
Claude uses this external leaf only when the fixed dual-pool policy permits
Luna. Astra uses its separate launch-bound native pool, never this route.
