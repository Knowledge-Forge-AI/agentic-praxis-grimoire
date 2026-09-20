# ADR 0060 — Request V2 Protocol, Bounded Dynamic Routing, and SQLite Dispatcher Persistence

- Status: Accepted (Amended and Superseded in Part by [ADR 0064](0064-request-v2-policy-externalization-and-dynamic-role-routing.md))
- Date: 2026-09-16
- Phase: APG146 (Roadmap Stage: V0120-A)

> [!NOTE]
> **Forward Amendment (ADR 0064 / APG148)**:
> Section 2 (`agent-phase-request-v2` fields `execution_mode` and `constraints`), Section 4 (hardcoded `~/.apgr/state/` database path), and Consequences (staging dynamic routing in V0120-D) are superseded by [ADR 0064](0064-request-v2-policy-externalization-and-dynamic-role-routing.md). Request V2 is strictly work-only (3 fields), routing policy is externalized to TOML/CLI, the SQLite store path is generalized to `<APGR_HOME>/state/dispatcher.sqlite3`, and initial dynamic routing is delivered in V0120-C. The historical text below is preserved for provenance.

## Context

The prototype dispatcher relied on `agent-phase-request-v1`, which required four mandatory fields: `schema`, `phase_type`, `execution_mode`, and `prompt`. The `execution_mode` field selected a static routing tuple (e.g., `gemini_flash_opus_sub`, `codex_claude_hybrid`) mapping dispatcher stages directly to predefined model profiles.

While deterministic and simple, static execution modes present several limitations:
1. Orchestrators like JACA may prefer to specify task intent and requirements without hardcoding specific underlying provider modes.
2. Static modes cannot adapt to temporary provider outages, rate limits, or quota exhaustion without manual intervention.
3. Tracking phase execution state across stages in purely flat files on disk complicates concurrent inspection, failure recovery, and structured queryability.

## Decision

1. **Request V1 Backward Compatibility**:
   APGR retains complete backward compatibility for `agent-phase-request-v1`. Any request containing the mandatory four fields (`schema="agent-phase-request-v1"`, `phase_type`, `execution_mode`, `prompt`) resolves strictly via the static route table.

2. **Request V2 Protocol (`agent-phase-request-v2`)**:
   APGR introduces `agent-phase-request-v2`:
   - `schema`: `"agent-phase-request-v2"` (mandatory)
   - `phase_type`: phase classification (mandatory)
   - `prompt`: task instructions (mandatory)
   - `execution_mode`: string identifier (optional)
   - `constraints`: optional routing and execution constraints (e.g., prohibited providers, required capabilities, max review budget).
   - When `execution_mode` is provided in a V2 request, APGR resolves it deterministically via the static route table as a compatibility and deterministic fallback path.

3. **Bounded Optional APGR Dynamic Router**:
   When `execution_mode` is omitted in a V2 request, APGR executes a bounded dynamic route resolution algorithm using:
   - **Role and Work Class**: Matches task complexity (`architecture_docs`, `implementation_testing`, `sysadmin`) against profile fitness.
   - **Provider Capabilities**: Evaluates provider features (extended thinking/reasoning, structured outputs, code synthesis, large context).
   - **Reviewer Independence Invariant**: Enforces that `Plan Reviewer != Planner` and `Work Reviewer != Producer/Reviser` across distinct provider families or independent model profiles.
   - **Bounded Availability and Quota Observations**: Considers recent local availability signals and quota exhaustion markers without long-running probes.
   - **Explicit Handling of Unknown Usage**: If usage or quota state is unknown, defaults to fail-open under conservative quotas rather than speculative blockage.
   - **Recent Typed Failure History**: Avoids selecting routes with recent unrecovered transient failures (e.g., repeated transport drops, active 429 rate limits, context window overflow).
   - **Operator Preferences**: Respects explicit operator hints or profile priority lists.
   - **Dynamic Router Invariants**:
     - *No Background Daemon*: Routing logic executes strictly within the CLI invocation process.
     - *No Predictive Scheduler*: Decisions are based on immediate local evidence, not probabilistic future load modeling.
     - *No Silent Route Replacement During Recovery*: Once an execution route is durably bound for an attempt, crash recovery never silently switches routes behind the caller's back. Any reroute requires an explicit new attempt record.
   - **Precedence Between Unknown Usage and Unsupported Capability**: The fail-open default above applies **only** to unknown *usage or quota state*. It never overrides ADR 0061 §3, which fails closed on an unsupported *capability*. When both apply to one route decision, capability support is evaluated first and fails closed: a provider that cannot satisfy a required capability is never selected, regardless of how favourable its usage state is or how unknown. Fail-open is therefore a tie-break among already capability-eligible routes, not a bypass.

4. **Dispatcher State Persistence via SQLite**:
   - APGR introduces lightweight SQLite persistence located at `~/.apgr/state/dispatcher.sqlite3`.
   - The database maintains structured tables for phase requests, stage envelopes, actor bindings, candidate transitions, review findings, finding dispositions, and completion receipts.
   - **Run-Owned Artifact File Invariant**: SQLite stores relational metadata, stage states, and artifact digests. Large execution transcripts, raw stdout/stderr logs, and zip/tar archives remain run-owned files stored directly on disk (e.g., under run-specific directories in `~/.apgr/runs/<run_id>/`), referenced in the database strictly by path and SHA-256 hash.

## Alternatives Considered

- **External Route Brokering Daemon**: Rejected. Introducing a long-running system daemon introduces operational fragility, IPC complexity, and lifecycle management overhead inconsistent with APGR's lightweight design.
- **Storing Large Blobs in SQLite**: Rejected. Storing multi-megabyte raw agent transcripts directly in SQLite leads to database bloat, performance degradation, and difficult external diff inspection.

## Consequences

- In stage `V0120-C`, APGR will implement the SQLite state schema and Request V2 parsing.
- In stage `V0120-D`, APGR will implement the bounded dynamic router algorithm and fallback mechanisms.
- Callers like JACA can either supply an explicit `execution_mode`, rely on APGR's bounded router, or bypass top-level dispatch by invoking lower-level Go APIs directly.
