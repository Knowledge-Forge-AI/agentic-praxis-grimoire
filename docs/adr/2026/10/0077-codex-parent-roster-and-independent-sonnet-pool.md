# ADR 0077: Codex parent roster and independent Sonnet pool

Status: Proposed — APG166ZO reviewed and amended candidate; qualification incomplete.

## Context

The authorized v0.13 roster change selects GPT-6.1 Sol/xhigh for every Codex
parent and adds Sonnet 5.5/high to stages that already receive both standard
worker pools. Model-specific parent-family labels and two-pool artifact names
cannot truthfully describe this fresh configuration.

## Decision

Generation 9 selects `gpt-6.1-sol`/`xhigh` for all six Codex parent profiles.
The source-owned Codex `parent` role determines `codex_parent`; model suffixes
do not determine admission. Luna remains `gpt-6-luna`/`max`.

`agent-worker-policy-v2` selects `triple_pool_4x4x4`: Gemini, Luna and Sonnet
each have four independent slots, with no borrowing and the parent excluded.
Sonnet is `claude-sonnet-5-5`/`high`. Existing worker-disabled and Gemini-only
routes retain their availability boundaries.

Claude parents use `claude_native` Sonnet; Codex and Gemini parents use
`claude_external`. Codex native occupancy continues to own Luna only.
Children are nonrecursive leaves bounded by parent task authority. Native
Sonnet leaves have no Bash, Agent, Task or worker facade. Launcher-owned
hooks enforce the permitted agent type, model-override refusal and atomic
four-slot admission. Agent is exposed without pre-approval; admission failures
return blocking exit 2, including guarded import failures and a ten-second
deadline below the provider hook timeout. Calls require explicit foreground
selection. Native writers register disjoint paths against native and foreign
reservations. Interrupted calls retain custody until cleanup is observed.

All dispatcher bundle members advance together. Retained generation-8 bundles
remain inspectable; fresh admission requires the new three-pool authority.
Historical runs resume through their pinned controller and retain two pools.
Old artifacts never acquire Sonnet authority through inspection or recovery.

This decision partly supersedes ADR 0075's current parent roster and two-pool
selection while preserving captured authority, provider observation, custody,
availability-first operation and explicit operator rollback.

## Consequences

Fresh qualification and staging-candidate reconstruction are required after
local finalization. The earlier public candidate is historical evidence.
This phase grants no staging update, PR mutation, merge, tag or publication.
H/D1 remains unstarted; changing its separate preregistration authority requires
explicit disposition. Optional external subsystems remain optional.

Rollback selects a previous complete runtime/bundle after owned custody drains;
it does not resize an admitted lifetime or reinterpret an existing ledger.

The Claude plugin supplies a namespaced agent definition with pinned model and
frontmatter effort. Global plugin hooks carry explicit ledger identity and a
capability digest. Agent completion observations remain separate from requested
values; missing provider effort is recorded as unknown. Worker-enabled Claude
parents retain Agent in the final CLI tool inventory: denying its legacy Task
alias removes Agent too. Caller tool-selection overrides are refused for native
parents. Readback describes configuration; only a provider init event establishes
observed availability. Leaves continue to deny both Agent and Task.

Correlated foreground completion releases capacity exactly once independently
of model or effort observation. A returned foreground tool failure retains a
closed failed record; interruption, async or unknown live evidence remains
accounted until terminal reconciliation or observed parent exit. Closed tool-use
identities cannot be admitted again. Task disposition remains parent-owned;
unknown telemetry never becomes an observed match. Model identifiers are compared
exactly, so aliases and dated variants are conservatively mismatched and retained.

Fresh bundle admission requires generation at least 9 and the three-pool policy;
generation remains a coherent operator counter. Historical two-pool inspection,
settlement and pinned-controller recovery remain separate. Native file tools have
no shell or recursive agent facility. External Sonnet uses restricted Claude
file tools, empty settings sources, strict empty MCP and the existing worker
scope audit; write-scope confinement is not claimed as an OS sandbox.

Provider contracts: [Claude subagents](https://code.claude.com/docs/en/sub-agents),
[Claude hooks](https://code.claude.com/docs/en/hooks), and
[plugin reference](https://code.claude.com/docs/en/plugins-reference).

The maintained canary runner adds explicitly selected native Sonnet, foreground
sequential reuse, Codex external and Gemini external cases with separate Sonnet
attempt authority. Default campaigns remain unchanged. Deterministic fixtures
establish receipt handling; terminal live qualification requires an independently
reviewed candidate materialized into a fresh runtime. Missing observed effort
remains a partial qualification even when child lifecycle and cleanup are proven.
This correction does not establish terminal live native model/effort or cleanup
qualification. Native writing tools do not establish OS-enforced path confinement;
authority downgrade and occupancy presentation remain separate deferred work.
