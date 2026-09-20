# ADR 0064 — Request V2 Policy Externalization, Routing Architecture, and Dynamic Role Routing

- Status: Accepted (Supersedes and Amends ADR 0060)
- Date: 2026-09-16
- Phase: APG148 (Roadmap Stage: V0120-C)

## Context

ADR 0060 originally proposed allowing optional `execution_mode` and `constraints` fields inside `agent-phase-request-v2`, and scheduled dynamic routing for stage V0120-D. Following successful delivery of V0120-B parity migration (Phase APG147 / Exit 00192 / ADR 0063), the operator amended the V0120-A/B architecture:

1. Request documents must express task intent only ("work-only"), not runtime dispatcher policy or execution modes.
2. Routing policy, including `execution_mode`, belongs in TOML configuration and explicit CLI flags, not task identity.
3. Dynamic role routing (`execution_mode = "dynamic"`) should be integrated into stage V0120-C to provide an immediately usable default for Request V2.
4. Legacy named execution modes remain available as deterministic presets and fallbacks.
5. JACA XO is not expected to adopt APGR `execution_mode`; JACA remains free to resolve routes under its own policy and consume lower-level Go APIs later.

This record formally supersedes and amends ADR 0060 regarding Request V2 schema fields, routing policy ownership, database path generalization, and milestone staging.

## Decision

### 1. Request Protocol Separation

#### Request V1 (`agent-phase-request-v1`)
Request V1 remains 100% immutable for backward compatibility:
```json
{
  "schema": "agent-phase-request-v1",
  "phase_type": "...",
  "execution_mode": "...",
  "prompt": "..."
}
```
Its embedded `execution_mode` is strictly authoritative. Configuration policy and CLI flags must never silently reinterpret Request V1. Supplying `--execution-mode` on the CLI with a Request V1 document raises an explicit conflict error.

#### Request V2 (`agent-phase-request-v2`)
Request V2 is strictly work-only and contains exactly three fields:
```json
{
  "schema": "agent-phase-request-v2",
  "phase_type": "...",
  "prompt": "..."
}
```
Request V2 **MUST reject** `execution_mode`, `provider`, `model`, `profile`, routing `constraints`, `lifecycle`, `finalization`, `reviewer_count`, `executable`, `sandbox`, security policy, and any other runtime-routing or policy fields as unknown fields.

### 2. Configuration Contract and Execution Mode Precedence

Routing policy is resolved entirely outside Request V2 using APGR's closed TOML configuration structure and explicit CLI flags:
- Global: `<APGR_HOME>/config.toml` (where `APGR_HOME` is resolved via `--apgr-home` / `APGR_HOME` / `~/.apgr`).
- Project: `<project-root>/.apgr/config.toml`.

The closed TOML schema is extended to support:
```toml
[dispatcher.routing]
execution_mode = "dynamic"
```

Accepted values for `execution_mode`:
- `dynamic`
- Every retained V1 static preset: `normal`, `gemini_sub`, `gemini_flash_sub`, `gemini_flash_opus_sub`, `conserve_claude`, `claude_only`, `codex_only`, `gemini_only`, `gemini_opus`, `gemini_fable`.

Execution-mode resolution precedence for Request V2:
1. Explicit CLI argument: `--execution-mode <value>`
2. Project configuration: `<project-root>/.apgr/config.toml`
3. Global configuration: `<APGR_HOME>/config.toml`
4. Built-in default: `dynamic`

*Invariants*:
- No environment variable for `execution_mode`.
- No reading `execution_mode` from prompt text.
- Supplying `--execution-mode` on the CLI with a Request V1 document raises an explicit conflict error, refusing competing authorities.
- Existing `outbox_root` configuration semantics and precedence remain backward compatible.
- The TOML schema remains closed; any unrecognized keys or tables raise `ConfigError`.

### 3. Semantic Roles and Flexible Actor Binding (ADR 0059)

APGR Single-Phase Dispatcher adopts the 8 canonical responsibilities defined in ADR 0059:
- `Planner`: Explores requirements, authors initial plan material (read-only).
- `Plan Reviewer`: Evaluates plan material, emits typed findings (read-only).
- `Plan Review Disposition`: Dispositions plan proposal and findings (accept, amend, reject, defer, supersede).
- `Producer`: Authors candidate implementation modifications within task boundary (mutating).
- `Work Reviewer`: Evaluates implementation candidate against task and constraints, emits work findings (read-only).
- `Work Review Disposition`: Dispositions work findings, determining revision necessity.
- `Reviser`: Addresses findings and authors revised candidate (mutating).
- `Closeout Agent`: Verifies terminal criteria, records proofs, prepares final receipts (mutating).

Default Standard Actor Binding merges adjacent responsibilities into five turns:
1. Turn 1 (`binding_plan`): `[Planner]`
2. Turn 2 (`binding_plan_review`): `[Plan Reviewer]`
3. Turn 3 (`binding_work`): `[Plan Review Disposition, Producer]` (requires union of capabilities)
4. Turn 4 (`binding_work_review`): `[Work Reviewer]`
5. Turn 5 (`binding_closeout`): `[Work Review Disposition, Reviser, Closeout Agent]` (requires union of capabilities)

*Persistence Invariant*: Regardless of actor grouping, APGR persists distinct semantic records for each canonical responsibility. Actor binding policies remain decoupled from semantic records, enabling unmerging into 8 discrete turns without altering underlying data schemas.

### 4. Initial Bounded Dynamic Routing

When `execution_mode = "dynamic"`, routing is resolved role-by-role / invocation-by-invocation rather than as a single static whole-phase snapshot:
- Before each distinct top-level provider attempt, resolve the actor binding's route from a bounded operational snapshot.
- Persist the selected route into SQLite before launching the provider process.
- Recovery of the same attempt **MUST reuse** the persisted route; it must not query fresh state and swap providers silently.
- A distinct retry or subsequent invocation resolves using a fresh observation snapshot with predecessor attempt provenance.

#### Decision Order and Invariants
1. **Capability Eligibility (Fails Closed)**: Evaluated before operational preference. Provider/profile must satisfy all required capabilities of the binding (e.g. read tools, write tools, reasoning, tool execution). Ineligible profiles fail closed.
2. **Reviewer Independence Invariant**:
   - `Plan Reviewer != Planner` provider family.
   - `Work Reviewer != Producer` provider family, evaluated against the actual selected parent invocation provider that produced the reviewed candidate (provider-local workers do not alter top-level parent independence).
3. **Operational Snapshot Evaluation**:
   - Unavailable profiles are excluded.
   - Profiles with active, unexpired typed failure cooldowns are excluded.
   - Quota / usage state: if `unknown`, it is recorded truthfully as `unknown` and admitted (fail-open for quota among capability-eligible profiles); if `exhausted`, it is excluded. Usage numbers are never fabricated.
4. **Deterministic Ranking**: Given the same role, policy snapshot, eligible profiles, and operational observations, the dynamic router makes the exact same choice every time, using deterministic affinity scoring and lexical tie-breaking.
5. **Static Modes Fallback**: Static TOML/CLI modes use exact deterministic route presets from the V0120-B parity tables.

### 5. SQLite Dispatcher Persistence

Dispatcher persistence is located at `<APGR_HOME>/state/dispatcher.sqlite3`:
- Embedded SQLite only; no daemon, no background service, no lease server.
- Explicit schema versioning via `schema_migrations` table (Version 1).
- PRAGMA configuration: WAL journal mode (`PRAGMA journal_mode = WAL;`), foreign keys enabled (`PRAGMA foreign_keys = ON;`), busy timeout 5,000ms (`PRAGMA busy_timeout = 5000;`), synchronous NORMAL (`PRAGMA synchronous = NORMAL;`). State directory permissions set to `0o700`.
- Typed error `PersistenceError` on database lock or corruption.
- Relational tables: `schema_migrations`, `runs`, `configuration_provenance`, `actor_bindings`, `semantic_responsibilities`, `invocation_attempts`, `route_resolutions`, `operational_observations`, `candidates`, `review_records`, `review_findings`, `review_dispositions`, `artifacts`, `completion_receipts`, `resume_relations`.
- Large execution transcripts, stdout/stderr streams, model prose, and ZIP archives remain run-owned files on disk under the run directory. SQLite stores paths, sizes, and SHA-256 digests; tampering triggers verification failure.
- Request V1 execution continues to operate via flat-file runtime without requiring SQLite.

### 6. Resolver Output Contract (`agent-phase-resolved-v7`)

Request V1 continues emitting `agent-phase-resolved-v6` with 100% byte and schema parity.
Request V2 emits `agent-phase-resolved-v7`:
- Truthfully represents semantic responsibilities, actor binding policy, resolved configuration provenance, execution mode, dynamically selected route resolutions, and pending responsibilities deferred to invocation time.

## Consequences

- ADR 0060's provisions allowing `execution_mode` and `constraints` in Request V2 are superseded; Request V2 is strictly work-only with exactly three fields.
- ADR 0060's hardcoded database path `~/.apgr/state/dispatcher.sqlite3` is generalized to `<APGR_HOME>/state/dispatcher.sqlite3`.
- Milestone staging in `docs/v0-12-roadmap.md` is updated:
  - **V0120-C**: Delivers Request V2 (work-only), TOML/CLI routing policy externalization, semantic role graph and flexible actor bindings per ADR 0059, non-daemon SQLite persistence, and initial usable dynamic role routing.
  - **V0120-D**: Re-scoped to provider capability parity closure, adapter normalization, and dynamic-routing observation hardening.
