# ADR 0065 — Operational Observation Model, Provider Parity Closure, and V2 Semantic Execution Runtime

- Status: Accepted
- Date: 2026-09-16
- Phase: APG149 (Roadmap Stage: V0120-D)

## Context

Following the delivery of Request V2 grammar, externalized TOML routing policy, flexible actor bindings, and SQLite persistence in stage V0120-C (ADR 0064 / Phase APG148 / Exit 00193), stage V0120-D was scoped to achieve:
1. Operational observation collection and precedence hardening.
2. Provider capability parity closure across Codex, Claude, and Antigravity.
3. Full Request V2 semantic multi-turn execution runtime.
4. Nonce-fenced candidate and review parsing, anti-tamper artifact verification, and terminal run archiving.

Independent plan review surfaced sixteen advisory findings (F1 through F16), recommending:
- Explicit integration of real provider runners via `provider.py` and `build_argv` alongside dry-run test callbacks (F1).
- Multi-turn execution resumption with attempt derivation and lineage tracking in `resume_relations` (F2).
- Strict enforcement of process posture (`read_only` vs `mutating`) and git worktree mutation guards (F3).
- Structured terminal ZIP archive creation with SHA-256 checksums in SQLite `runs` and `completion_receipts` (F4).
- Truthful recording of provider capabilities: acknowledging that upstream CLI flags do not natively support structured schema enforcement (relying on nonce-fenced decoding), and that auth/quota state cannot be queried without credential scraping or token burn (F5, F6).
- Hardening the 6-stage dynamic routing decision ladder with canonical SHA-256 observation digests and typed errors for unknown static bindings (F7, F8, F10).
- Registering an Antigravity review endpoint (`antigravity-claude-opus-review`) for reviewer independence (F9).
- Clean decomposition of runtime components to honor strict file length governance (F11).

This record formally documents these architectural decisions and closes provider capability parity for APGR v0.12.

## Decision

### 1. Bounded Operational Observation Model

Operational observations are collected on-demand via `libexec/agent_phase/probes.py`:
- **No Background Daemons**: Probes execute synchronously with a strict 5.0-second timeout ceiling.
- **Zero Credential Scraping**: Probes never inspect private keychains, token files, or authorization headers.
- **No Model Token Burn**: Probes never invoke generative model inference to determine availability or quota.
- **Truthful Unknown State**: When auth usability or remaining quota cannot be determined non-intrusively, observations truthfully report `state_value = "unknown"`.
- **Fail-Open Admission**: Dynamic routing admits capability-eligible endpoints with `unknown` quota, preventing speculative starvation.
- **Canonical SHA-256 Digests**: Every `OperationalObservation` computes a deterministic SHA-256 digest over its sorted JSON representation (`detail`, `expires_at`, `observation_id`, `observation_type`, `producer`, `profile`, `provider`, `state_value`, `timestamp`).

### 2. Truthful 22-Row Provider Conformance Matrix

APGR establishes a formal conformance evaluation across 22 capability dimensions (`docs/architecture/provider-conformance-matrix.json` and `.md`):
1. `executable_version_provenance`: Supported across all 3 providers.
2. `profile_resolution`: Supported across all 3 providers.
3. `requested_model_readback`: Supported across all 3 providers.
4. `reasoning_effort_readback`: Supported across all 3 providers where meaningful.
5. `planner_role_qualification`: Supported across all 3 providers.
6. `reviewer_role_qualification`: Supported across all 3 providers (`-s read-only` for Codex, `--read-only` for Claude, `--reviewer` for Antigravity).
7. `producer_role_qualification`: Supported across all 3 providers with mutation capability.
8. `reviser_role_qualification`: Supported across all 3 providers for post-review candidate amendments.
9. `closeout_role_qualification`: Supported across all 3 providers for terminal receipts and finalization.
10. `adapter_structured_output`: Truthfully unsupported at upstream CLI flag level across all 3 providers; APGR uses nonce-fenced structured decoding.
11. `process_group_cleanup`: Supported across all 3 providers.
12. `stdout_overflow_protection`: Supported across all 3 providers (4 MiB limit).
13. `stderr_overflow_drain`: Supported across all 3 providers.
14. `liveness_outer_ceiling`: Supported across all 3 providers (default 90,000s).
15. `liveness_advisory_silence`: Supported across all 3 providers (900s interval; never kills quiet processes).
16. `interruption_cleanup`: Supported across all 3 providers.
17. `tokenless_auth_probe`: Truthfully unsupported across all 3 providers (reports `unknown`).
18. `tokenless_quota_probe`: Truthfully unsupported across all 3 providers (reports `unknown`).
19. `subagent_worker_support`: Supported for Antigravity via worker facility; unsupported for standalone Codex and Claude CLIs.
20. `failure_cooldown_tracking`: Supported across all 3 providers via SQLite `invocation_attempts` within `window_seconds`.
21. `run_resumption`: Supported across all 3 providers via V2 dispatch attempt derivation.
22. `activity_pipe_telemetry`: Unique to Antigravity via `AGENT_CENTRAL_ANTIGRAVITY_ACTIVITY_FD`.

### 3. Hardened 6-Stage Dynamic Routing Ladder

The dynamic router (`libexec/agent_phase/dynamic_router.py`) executes a strict 6-stage decision ladder:
1. **Capability Eligibility (Fails Closed)**: Filters candidate endpoints against `required_capabilities` of the actor binding.
2. **Hard Unusable Exclusion**: Excludes endpoints with `availability == "unavailable"` or `authentication == "unusable"`.
3. **Quota Exhaustion**: Excludes endpoints with `quota == "exhausted"`. Endpoints with `unknown` quota are admitted fail-open.
4. **Active Cooldown Exclusion**: Excludes endpoints with active failure cooldowns recorded in SQLite within `window_seconds`.
5. **Reviewer Independence Invariant**:
   - `Plan Reviewer != Planner` provider family.
   - `Work Reviewer != Producer parent` provider family.
6. **Deterministic Ranking & Lexical Tie-Break**: Sorts eligible endpoints by affinity score descending, breaking ties lexically by `(provider, profile, endpoint_alias)`. Explicit availability scoring distinguishes known available from unknown or unobserved states.

Static preset routing (`resolve_static_preset_route`) raises typed `RoutingResolutionError` if an unmerged or unknown binding ID is passed, preventing silent fallback misrouting.

### 4. Full Request V2 Semantic Execution Runtime

Multi-turn execution is coordinated via `libexec/agent_phase/v2_turns.py` and `libexec/agent_phase/v2_dispatch.py`:
- Enforces worktree requirements up front via `candidate.require_worktree(work_tree)`.
- Orchestrates configured actor bindings (`binding_plan`, `binding_plan_review`, `binding_work`, `binding_work_review`, `binding_closeout`, or unmerged 8-turn bindings).
- Derives invocation attempt numbers dynamically and verifies predecessor lineage against persisted SQLite records.
- Reuses pinned routes upon retry/recovery within the same attempt (Invariant 14).
- Enforces read-only posture on review bindings, actively comparing pre- and post-turn git tree SHAs to detect and reject unrecorded mutations.
- Strict review validation: reviews must parse valid nonce fences; review findings are extracted and saved into `review_findings`.
- Disposition transitions: reviews with findings transition to `amend`, unreviewable reviews transition to `reject`, and no findings transition to `accept`. Rejections block subsequent mutating work.
- When amended, Reviser turns create and persist `cand-{run_id}-revision` git tree candidates.
- Typed failure handling: non-zero provider exit codes mark attempt and semantic responsibilities as failed, distinguishing pre-substantive from substantive failures.
- On run completion, builds a terminal ZIP archive (`{run_id}.zip`), computes its SHA-256 digest, updates `runs`, and records a `completion_receipts` entry.

### 5. Decomposition and Line-Length Governance

To comply with APGR's strict file length policies (<400 lines warning threshold, <=1000 lines failure threshold), the V2 runtime is decomposed into focused modules:
- `libexec/agent_phase/probes.py` (305 lines)
- `libexec/agent_phase/v2_prompts.py` (137 lines)
- `libexec/agent_phase/v2_records.py` (124 lines)
- `libexec/agent_phase/v2_turns.py` (477 lines)
- `libexec/agent_phase/v2_dispatch.py` (261 lines)
- `libexec/agent_phase/dynamic_router.py` (375 lines)
- `libexec/agent_phase/persistence.py` (990 lines, compacted under 1000 lines)

## Consequences

- Milestone V0120-D (`V0120_D_PROVIDER_PARITY_AND_DYNAMIC_ROUTING_HARDENED`) is completely achieved: provider capability parity is formally closed, dynamic routing is hardened with truthful observation semantics, and the full Request V2 multi-turn runtime is qualified.
- Golden parity corpus and existing Request V1 execution paths remain 100% untouched and byte-compatible.
- All 38 new deterministic unit and integration tests pass cleanly without regressions.
