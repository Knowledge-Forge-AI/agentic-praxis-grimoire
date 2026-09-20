# ADR 0074 — Context Plan, Byte Budgets, Late Acquisition, and Bounded APGR MCP Adapter

- Status: Accepted with Amendment to APGR-D8 (Amended under APG159A / V0130-A-CORR1)
- Date: 2026-09-20
- Phase: APG159A (Roadmap Stage: V0130-A-CORR1)

## Context

In v0.12, context delivery is static: every provider invocation receives all canonical projected skills and full standing instruction files. This consumes substantial token capacity on every turn, regardless of whether the skills are relevant to the assigned actor binding.

The adaptive context architecture establishes dynamic context selection under explicit budgets, with late acquisition mechanisms enabling agents to discover and retrieve deferred skills on demand.

In v0.8, disposition `APGR-D8` rejected embedding or distributing a general MCP suite, citing concerns over complexity, network authority, tool sprawl, and process coupling. However, evaluating late acquisition across modern providers demonstrates that:
1. In Claude read-only review stages, APGR strictly controls tools via `--tools <list>` and isolated MCP configurations. The CLI acquisition channel (`apgr skills acquire`) requires granting `Bash` execution, which violates least-privilege principles for a read-only reviewer.
2. A bounded, stdio-based MCP server providing read-only skill retrieval allows read-only reviewers to acquire skills in-band without granting shell access and without modifying the target repository.
3. Implementing a stdio JSON-RPC 2.0 server in Go requires only standard library packages (`encoding/json`, `bufio`), fully preserving APGR's zero-dependency policy.

## Decision

### 1. Per-Binding Context Planning and Byte Budgets
- **Keying**: Context plans are generated per `(run_id, binding_id, attempt_id)` and record the exact roles served.
- **Budgeting Units**: Budgets are enforced strictly on APGR-controlled bytes and UTF-8 characters. Token counts are classified as `unavailable` unless measured by a named tokenizer or provider API counter.
- **Mandatory Doctrine Invariant**: Non-negotiable repository doctrine, authority boundaries, review role restrictions, and late-acquisition recovery instructions are mandatory and NEVER truncated or dropped by ranking. If a configured budget cannot hold mandatory context, dispatch falls back to static baseline context delivery rather than failing closed.

### 2. Bounded Stdio MCP Adapter and Protocol Lifecycle
APG165 implements a candidate lightweight, native stdio MCP server inside the `apgr` binary (`apgr mcp serve`):
- **Protocol Revision**: Pins the official `2025-11-25` Model Context Protocol lifecycle specification as the implementation reference.
- **Negotiated Stdio Lifecycle**:
  1. `initialize` request from provider client; server responds with protocol version `2025-11-25` and declared capabilities (tools, resources).
  2. Client sends `notifications/initialized`.
  3. Normal operation: `tools/list`, `tools/call`, `resources/list`, `resources/read`.
  4. Shutdown: Per stdio specification, the client closes server standard input (`stdin`), waits for process exit within a finite timeout, and issues SIGTERM followed by SIGKILL if the process does not terminate. (Stdio transport defines no JSON-RPC shutdown or exit messages).
- **Protocol Purity & Bounds**: Logging is directed strictly to `stderr`, preserving `stdout` purity for JSON-RPC framing. Messages are bounded by maximum payload sizes (1 MB ceiling) and timeouts.
- **Bounded Surface**: Exposes exactly three tools (`skill_search`, `skill_acquire`, `context_explain`) and two resource templates (`apgr://skills/{namespace:id}` and `apgr://context/{run_id}/{binding_id}`).
- **Zero Network / Process Authority**: The server performs zero network requests, spawns zero subprocesses, reads zero credentials, and writes zero operator configurations.

### 3. Acquisition persistence contract (G candidate; not implemented by F)
To resolve the contradiction between a zero-dependency Go binary and SQLite persistence without adding a Go SQLite driver, subprocess bridge, or mandatory service daemon:
1. **Append-Only Run Event Artifacts**: During execution, the Go MCP server writes append-only event records to `<run_dir>/acquisitions/events-NNN.jsonl` along with the materialized skill bodies under `<run_dir>/acquisitions/skills/`.
2. **Per-Event Sequence Identity**: Future acquisition identity must be scoped to the emitting binding and attempt; a run-global counter is not an implemented F contract.
3. **Repeat Deliveries vs Ingestion Idempotency**:
   - Ingestion into SQLite is idempotent keyed on `event_id`. On crash recovery or resume, unimported events are ingested without duplicate state errors.
   - If an agent intentionally requests a skill a second time, a new event sequence ID is minted with `is_repeat_delivery = true`. Per F2 accounting rules, actual second transmissions count again in cumulative delivery metrics.
4. **Defined Lifecycle Seams**: The existing Python dispatcher persistence owner (`libexec/agent_phase/persistence.py`) validates and imports event artifacts into SQLite at defined lifecycle seams:
   - Between turn transitions,
   - At worker drain / supervisor checkpoints, and
   - During stage finalization.
5. **Truthful State Transitions**: Emission, materialization, optional index ingestion, transport delivery and model observation are independent dimensions. Index ingestion neither establishes nor precedes delivery authority; an index failure is diagnostic and cannot erase a valid run-owned record. A provider write or invocation alone does not prove model consumption.
6. **Raw Artifact Retention**: Event JSONL files and materialized bodies remain permanently on disk in the run directory as canonical raw evidence; SQLite acts as an indexed query projection.

### 4. Amendment to APGR-D8
APGR formally amends `APGR-D8`:
- The prohibition against distributing a *general-purpose* MCP suite (such as shell executors, browser automation, web scrapers, memory services, or external credential brokers) remains **strictly in effect**.
- A **bounded, internal-only adapter over APGR's native skill and context APIs** is admitted as an authorized acquisition channel.

### 5. Pre-Launch and Mid-Turn Fallback Without Replay
- **Pre-Launch Fallback**: If MCP is disabled, unsupported, absent, or fails pre-launch negotiation, dispatch cleanly selects static mode before launch.
- **Mid-Turn Recovery Under Actor Permissions**: Adaptive qualification requires that every provider/role binding have an independently usable recovery path under unchanged permissions:
  - Run-owned snapshots of applicable skills are pre-materialized at `<run_dir>/snapshots/skills/` prior to launch.
  - If MCP exits mid-turn, the attempt is preserved and the actor recovers by reading the local snapshot via native tools (e.g. `view_file` for a read-only reviewer without Bash).
  - If an actor lacks tools to read local snapshots independently, the dispatcher selects static context before launch rather than attempting adaptive execution.
- **Zero Blind Replay of Mutating Turns**: Mid-turn server failure NEVER triggers an automatic blind restart or replay of a producer stage that may have already executed filesystem mutations or external side effects.

## Consequences

- Read-only review actors can dynamically search and acquire skills without requiring shell execution authority.
- Prospective controlled-byte reduction can be measured; tokens, model consumption and live benefit remain unavailable until qualified.
- Go MCP server retains zero CGO or SQLite driver dependencies via clean JSONL handoff to Python persistence.
- Crash recovery, idempotency, and cumulative repeat delivery metrics are rigorously supported.
- The immutability fence is fully preserved during late acquisition.

## APG164 F candidate implementation boundary

F implements the versioned pure `skills.PlanContext` and `skills plan --stdin`
boundary and optional V1/V2 invocation adapter. Requested context mode is separate
from runtime routing. Python alone captures and validates the closed context
configuration; static is the default and does not call the optional planner or
catalog. Mandatory-only overflow or optional planning failure preserves the
ordinary static provider transport. Malformed operator configuration and real
provider failures retain their error semantics.

An immutable run/binding/attempt plan precedes launch. Actual runner-bound argv
and stdin are measured separately and count once each; source and rendered
instruction views do not add extra transmissions. Plan references attach through
existing state/artifact owners. Separate transport observations record runner
return, failed start or partial/unknown execution without rewriting the plan.
No SQLite migration or new Go database driver is introduced. Completed attempts
are read as historical files and are not replanned by collection.

Selective projection and independent same-permission recovery are required
qualification inputs. F provides a caller-owned seam and instrumented fixtures;
no real provider is enabled for adaptive reduction. Acquisition commands, MCP
services, mid-turn acquisition event implementation and live benefit claims remain
future G/H work. This amendment does not authorize those successors.

## APG165 G produced-candidate boundary

The shared private Go acquisition engine serves the CLI and pinned MCP tools and
resources. It retains one exclusive JSONL artifact per event and snapshots under
`acquisitions/skills/<snapshot-digest>/<selected-id>/`; these refine the
illustrative filenames above. Identities include run, binding, attempt, sequence
and random process nonce. Recovery uses those same independently pre-materialized
run-owned files, rather than a second snapshot-copy implementation.

Requested, materialized, available and successful channel-write facts remain
separate immutable events. Python optionally indexes the existing artifact table
at V2 adaptive invocation completion. Other callers may invoke the same bounded
idempotent projection; broader automatic lifecycle ingestion remains deferred.
No migration or server-side subprocess bridge is introduced.

The caller-owned adaptive projection seam supports explicit native argv contracts
and bounded server preflight. The ordinary V1/V2 provider matrix remains static;
no real provider is promoted to qualified. Instrumented actors and real MCP
subprocesses establish controlled byte recovery and Git authority preservation,
not model observation, task quality or measured benefit. See the
[implemented acquisition contract](../../../guides/skill-acquisition.md).


APG165 revise-close separates prelaunch preparation from agent-channel requests
and deliveries, publishes completed events atomically, preserves corrupt optional
records with diagnostic collection, and caps materialization and binding events.
The advertised RFC 6570 skill template is `apgr://skills/{namespace}:{id}`;
it denotes the same qualified-ID family as the illustrative notation above.
Reserved MCP metadata is accepted without granting new authority. Native read
permission remains independently caller-owned. These amendments follow supplied
work review and have no second independent review.
