---
name: agent-worker
description: >-
  Delegate separable implementation, codebase investigation, test analysis,
  documentation checks and cross-checks when enabled workers can improve
  correctness, parallel progress or parent-context efficiency, even without an
  explicit request for subagents. Use the existing launcher-bound context and
  only its enabled providers; collect results and recover bounded jobs.
---

# Agent worker facility

## When to delegate

Choose delegation at your discretion within the authorized task; ordinary
handoffs need no separate user request or approval. Prefer Gemini for substantial
bounded engineering and Luna for lighter inspection, mechanical work or targeted
checks, adjusting to observed results. Keep small or tightly coupled tasks local.
Capacity is a ceiling, not a fan-out target. Loading this skill does not require
starting a worker or creating a parent context.

Use only the worker kinds, limits and authority exposed at this session's launch.
Astra uses its native interface for Luna and the common facility for Gemini;
Claude uses the common facility for its enabled external workers. Do not expose
external Luna to Astra or add a Claude team or middle manager. A bare vendor CLI
is not promised external pools. Missing optional facilities leave direct work
available; this guidance neither selects a mode nor enables a pool.

The parent owns decomposition, integration, verification and disposition.
Internal findings never replace an independent dispatcher checkpoint. A read-only
parent cannot outsource tests, builds or writes. Workers cannot stage, commit or
publish even when the parent has finalization authority, recursively delegate,
or mint another budget. Follow [WORKER-RECOVERY.md](WORKER-RECOVERY.md) for bounded
waits, deliberate abandonment, partial-work adoption, pool pause and cleanup.

## Status and authority

Use the repository-owned `bin/agent-worker` command from the selected installation
or an explicit development checkout path. Do not assume a candidate is linked
into PATH. `gemini_sub`, `gemini_flash_sub`, `gemini_flash_opus_sub`, `gemini_opus`, and `gemini_fable`
change the top-level roster only when explicitly selected; `normal` remains
available.

In `gemini_sub`, eligible parents select `dual_pool_4x4`: independent four
Gemini and four Luna pools per logical parent, excluding the parent, with no
borrowing. Claude Fable/Opus use external Luna Max leaf sessions. Astra uses
native Luna Max children capped at four concurrently active tasks from session
launch; the external ledger owns only Gemini reservations. Completion-based
capacity reuse is valid when observed. Completion does not prove thread deletion
or closure; creation and exposed follow-up must both respect active capacity.
Ordinary native-only Astra retains its existing configuration. `normal` does not
select this experiment. `gemini_opus` and `gemini_fable` permit Gemini but exclude
Luna, including recovery. `codex_only` never gains hidden Gemini fallback.

In `gemini_flash_sub` and `gemini_flash_opus_sub`, only an Antigravity parent whose profile readback
identifies `gemini-3.8-flash-high` is recognized as the canonical `gemini_flash`
family. The mode selects `dual_pool_4x4` with up to four external Gemini leaves
and up to four external/direct Codex Luna leaves. Luna uses native-agent
disablement; both pools are independent and cannot borrow capacity. An alias,
mode string, malformed profile, or unrelated Antigravity profile grants no
parent capability. Gemini and Luna leaves remain bounded, nonrecursive leaves.

Legacy contexts retain their frozen policy and remain readable/drainable. Never
reinterpret a live legacy 4/10 context, hot-resize it, or mint a new allowance on
reconnect. Start a fresh correctly scoped lifetime after safely handling old work.
The fixed caps are ceilings, not required fan-out or performance claims.
Reservations, starting, stopping and unknown-cleanup jobs occupy external slots
until cleanup is proven. Native occupancy belongs to the runtime and is reported
separately from actual running external jobs.

Claude planning/review launcher posture removes Bash. Eligible Fable and Opus
parents receive the narrow `agent_worker` MCP tools from the launcher. The
interface does not grant general shell or write authority. Missing optional
configuration leaves ordinary parent work available with delegation unavailable.
The launcher records a bounded worker-facade diagnostic on optional setup failure.
Headless read-only launches with a validated facade use vendor `default` mode
with the same closed inspection tools and exact worker permissions. Read-only
is product task authority; it permits owned orchestration side effects. The
source profile's permission preference remains unchanged. Interactive planning
retains its mode, tools and permissions, but worker controls are now truthfully
annotated as side-effecting; interactive worker delegation remains unqualified.
No-worker and no-tools launches retain their existing posture. If facade setup
fails, the restricted Plan fallback and unavailable delegation are reported.

## Claude MCP operations

Use `mcp__agent_worker__submit` with the bounded task, idempotency key,
acceptance criteria and, for authorized writing tasks, explicit relative path
scope. Use `status`, `result`, `wait`, `outcome`, `cancel`, `abandon` and `pause_pool` from the same server for
that job. Set `worker_kind` to `gemini` or `luna` only when allowed by the
frozen policy. A bounded wait returns control for a deliberate decision. Continue
other work, investigate, or use `abandon` with a reason; do not poll indefinitely
just to obtain success. Follow [WORKER-RECOVERY.md](WORKER-RECOVERY.md).

Parent identity, source, workspace, lifetime and maximum authority come from
launcher context. They are not tool inputs. A read-only parent can submit only
read-only work. CLI and MCP requests share the same ledger and capacity.
The launcher owns the MCP server configuration and permits only its fixed worker
operations; caller MCP configuration overrides are refused while it is active.
Writable parents retain their existing tools and servers, with worker authority
bounded by the registered task and explicit mutation scope.
Read-only delegation is an inspection operation. The server's ledger/outbox
bookkeeping does not authorize product mutation or require a plan-file workflow.
Keep the current permission mode and use only explicitly exposed tools.

For an existing Serena project, the launcher also exposes a fixed set of
read-only symbolic and diagnostic tools. Serena shell, edit and memory tools
are excluded; its launcher configuration and home stay in owned parent state.
An absent Serena executable or project leaves worker delegation available.

## Stable parent context

Dispatcher-managed eligible stages supply `AGENT_CENTRAL_PARENT_ID`. Outside
that mode, initialize once using the actual top-level session identity and
reuse that ID across every shell call. Replace the placeholders below with the
owned session ID, workspace and absolute candidate command path:

```bash
/path/to/agent-central/bin/agent-worker parent init \
  --parent-id <stable-top-level-session-id> \
  --parent-family claude_opus --workspace <workspace> \
  --task-authority read_only
```

Fable uses `--parent-family claude_fable`. For the experiment add
`--worker-policy dual_pool_4x4`. Astra must use the source-owned fresh launch
path described in `docs/ops/dual-pool-workers.md` so native settings are bound before Gemini
is exposed; parent registration alone is not runtime cap proof. Do not initialize a parent
from a worker. Resuming an existing parent must preserve its budget and policy.

For a dispatcher-bound `gemini_flash_sub` or `gemini_flash_opus_sub` Gemini parent, the dispatcher already
binds the parent ID, workspace, authority, and worker state. Use
`bin/agent-worker parent status` and the job commands below; do not run
`parent init` or select a different parent, workspace, provider, or profile:

```bash
bin/agent-worker parent status
bin/agent-worker job launch --key <key> --worker-kind gemini \
  --task-file <task-file> --task-authority <authority> \
  --acceptance-criteria "<criterion>"
bin/agent-worker job wait --job-id <job-id> --timeout 120
bin/agent-worker job status --job-id <job-id>
bin/agent-worker parent drain
```

The parent may use either listed worker kind within its pool ceiling, but a
leaf cannot initialize a parent, launch another worker, or inherit parent
authority. The environment marker and inherited-facade removal are
same-user coordination controls, not hostile-user confinement.

For direct Claude use, the operator initializes the parent before starting the
model, then supplies `AGENT_CENTRAL_WORKER_FACADE=1`,
`AGENT_CENTRAL_PARENT_ID` and `AGENT_CENTRAL_WORKER_STATE_DIR` to the chosen
source `bin/claude-profile` invocation. Use `--read-only` for planning/review
and initialize with `--task-authority read_only`. Keep the ledger in an owned
outbox outside the product workspace. The launcher validates that context
against its source and selected provider profile. The operator or owning
launcher must drain the same parent after Claude exits; MCP server exit alone
does not prove worker cleanup. Dispatcher stages manage this setup and drain.

## Job handoff and results

Use explicit task data. The child does not inherit the parent conversation or
tool context. Include the bounded objective, required context, read/write
ownership and acceptance criteria. Ask for distilled findings, source references,
validation actually performed and remaining uncertainties, not an exploratory
transcript. Read-only authority forbids **all** test
runners, builds, installers, formatters and Git mutation. Workers are leaf jobs:
no recursive workers, new root budget, dispatcher lifecycle or peer reviews.
External Luna disables native agent tools with `agents.enabled=false`.
The AGY 1.1.27 canary exposed nested-agent tools without a supported disable
control in its inspected help. Gemini leaf instructions and inherited-facade
removal are coordination controls, not verified suppression of those tools or
hostile-same-user confinement. See the source fixed-pool guide for native
active-concurrency qualification boundaries.

```bash
/path/to/agent-central/bin/agent-worker job launch \
  --parent-id <stable-top-level-session-id> --key parser-inspection \
  --task-file <handoff-file> --task-authority read_only \
  --acceptance-criteria "Return source findings and their file references"
```

For an authorized writing task use `--task-authority mutation_capable` and
`--mutation-scope "path/one,path/two"`. Concurrent writers require disjoint
path ownership or isolated workspaces. The parent integrates changes. Workers
never stage, commit, push, or satisfy an independent review checkpoint.

```bash
/path/to/agent-central/bin/agent-worker job status --parent-id <parent> --job-id <job>
/path/to/agent-central/bin/agent-worker job wait --parent-id <parent> --job-id <job> --timeout 120
/path/to/agent-central/bin/agent-worker job cancel --parent-id <parent> --job-id <job>
/path/to/agent-central/bin/agent-worker job list --parent-id <parent>
/path/to/agent-central/bin/agent-worker parent status --parent-id <parent>
/path/to/agent-central/bin/agent-worker parent drain --parent-id <parent>
```

The wait timeout bounds the wait call, not worker lifetime. Silence does not
cancel jobs. Cancellation may return `stopping` or `orphaned`; neither proves
termination or releases capacity. Unknown supervisor identity is not signalled. Inspect the final structured result and its
artifact references. A failed editing job may leave changes; never retry it
automatically. A repeated idempotency key returns the existing job. A replacement uses the
same `task_id`, `previous_job_id`, and an explicit `recovery_decision` plus
`recovery_reason`, after proven cleanup and inspection of retained changes.
At most two delegated attempts belong to one logical task. A new key alone
does not reset this allowance.

Missing provider/state facilities disable optional delegation while ordinary
parent work continues. Do not repair bookkeeping by resetting a ledger,
pretending a live child vanished, or killing healthy jobs for silence. Drain
owned jobs before handing stage authority onward. Uncertain cleanup must be
reported with retained evidence. No Agent-Security, JACA, tmux, daemon, account
migration or new credentials are required by this facility.

A stop request is monotonic. A claimed launch without a bound supervisor keeps
its slot until the launch owner resolves the handoff. A late supervisor cannot
undo stopping or start a provider after losing admission. Unknown cleanup stays
in custody; it cannot produce a clean stage capture or terminal commit.

The helper rejects root registration and further launches when the inherited
worker-leaf marker is present. It is an additional local coordination check;
it is not resistant to a same-user process clearing its environment. Explicit
parent initialization freezes the worker profile as well as the policy digest.
A legacy prototype context lacking that profile cannot launch new jobs; start
a new parent lifetime only after the old context has drained.

Structured results retain actual response text, cleanup evidence, optional
provider conversation/session identifiers, and artifact references. A null
`changed_files` means not observed. A non-null list is workspace Git status,
which includes pre-existing changes and is not exclusive worker attribution.
Test evidence in the response is not independently verified by the supervisor.
