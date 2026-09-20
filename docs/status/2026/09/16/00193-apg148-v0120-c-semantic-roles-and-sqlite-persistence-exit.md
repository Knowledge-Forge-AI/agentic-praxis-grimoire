# APG148 — v0.12 Semantic Roles, Flexible Actor Binding, and SQLite Dispatcher Persistence Exit

Phase ID: `APG148`

## Status

Disposition: **amend**. Exit 00193 is allocated to APG148 without renumbering or substitution.  
Outcome: `V0120_C_SEMANTIC_ROUTING_AND_PERSISTENCE_READY` (single-phase Request V2 grammar implemented with work-only prompt semantics and strict rejection of execution policy; closed TOML configuration with 4-tier precedence CLI > project > global > default; 8 canonical semantic responsibilities decoupled per ADR 0059 with flexible actor bindings; capability metadata catalog in `common/dispatcher/capabilities.toml`; embedded non-daemon SQLite persistence under `<APGR_HOME>/state/dispatcher.sqlite3` with Schema Version 1, WAL mode, 0o700 state dir permissions, relational schema, and artifact digest verification; bounded dynamic routing with fail-closed capability eligibility, reviewer independence, and deterministic lexical ranking; deterministic fallbacks for retained V1 static modes; net-zero line growth in `dispatch.py`; 74 new unit and integration tests across 6 test suites; 100% pass rate on all 1807 dispatcher tests; zero git publication or commits performed).

Accounting: Historical v0.11 closure accounting remains terminal at 55/55/0/0. Milestone V0120-C delivers substantive architecture transfer and runtime qualification under ADR 0064.

## Exact Candidate and Baseline Provenance

- **Candidate APGR Commit**: `0cf473a6010f40a35b4b7f1c0650a7a053cb60cc` (APG147 / V0120-B).
- **Candidate APGR Tree**: Active working tree.
- **Source Agent-Central Baseline**: `56e9bb039536dfc8893e61a431681d6a32167b6f` (immutable commit).
- **JACA Reference Baseline**: `08ca2208805cf446bd15da0a6b4c8c58db737587` (unmodified).

## Deliverables Summary

1. **Request V2 Specification & Grammar**:
   - `schema = "agent-phase-request-v2"` with work-only prompt semantics (exactly 3 fields: `schema`, `phase_type`, `prompt`).
   - Strict rejection of embedded `execution_mode`, constraints, lifecycle, finalization, sandbox, and runtime policy fields.
   - Distinct parsers `parse_request_v2` and `load_request_v2` alongside unified `parse_any_request` and `load_any_request`.
   - V1 `parse_request` and `EXECUTION_MODES` preserved 100% byte-identical for backwards compatibility.

2. **Externalized Routing Policy & Precedence**:
   - Closed TOML configuration table `[dispatcher.routing]` with `execution_mode`.
   - 4-tier deterministic precedence: CLI `--execution-mode` > project `.apgr/config.toml` > global `<APGR_HOME>/config.toml` > default `dynamic`.
   - Rejection of unknown keys and tables fail-closed.
   - Preservation of existing scalar `outbox_root` configuration without regression.
   - Fatal error on Request V1 payloads when CLI `--execution-mode` is passed.
   - Multi-source audit trail recorded in `configuration_provenance` with SHA-256 digests and winning precedence rank.

3. **Decoupled Semantic Roles & Flexible Actor Binding**:
   - 8 canonical responsibilities per ADR 0059: `planner`, `plan_reviewer`, `plan_review_disposition`, `producer`, `work_reviewer`, `work_review_disposition`, `reviser`, `closeout_agent`.
   - Default standard policy (5 turns: `binding_plan`, `binding_plan_review`, `binding_work`, `binding_work_review`, `binding_closeout`).
   - Unmerged policy (8 discrete turns, one per responsibility).
   - Capability union for merged turns (e.g. work binding unions required capabilities of plan review disposition and producer).
   - Decoupled record schemas: `PlanProposalRecord`, `PlanReviewRecord`, `PlanDispositionRecord`, `ProducerCandidateRecord`, `WorkReviewRecord`, `WorkDispositionRecord`, `RevisionRecord`, `CloseoutReceiptRecord`.

4. **Capability Metadata Substrate**:
   - Closed TOML catalog `common/dispatcher/capabilities.toml` (`agent-phase-capabilities-v1`) mapping 19 endpoints across Codex, Claude, and Antigravity.
   - Explicit declaration of provider, profile, posture (`mutating` vs `read_only`), and capabilities (`read`, `mutation`, `execution`, `reasoning`, `structured_output`, `subagent_workers`).
   - `capabilities.py` loader and `EndpointCapabilities` inspection.

5. **Embedded Non-Daemon SQLite Persistence**:
   - Database at `<APGR_HOME>/state/dispatcher.sqlite3` with Schema Version 1.
   - Restrictive directory permissions (`0o700`), WAL mode, `PRAGMA foreign_keys = ON`, busy timeout (5000ms).
   - Full relational schema: `runs`, `configuration_provenance`, `actor_bindings`, `semantic_responsibilities`, `invocation_attempts`, `route_resolutions`, `operational_observations`, `candidates`, `review_records`, `review_findings`, `review_dispositions`, `artifacts`, `completion_receipts`, `resume_relations`.
   - Transactional rollback on integrity violations.
   - Pre-launch route persistence before invocation.
   - Same-attempt recovery route immutability (route re-read from persistence, never recalculated).
   - On-disk artifact digest verification (SHA-256 and byte length) with tampering detection.
   - Clean embedded process exit (no background daemon, no lease server).

6. **Bounded Deterministic Dynamic Routing**:
   - Capability-first eligibility filtering (fails closed if required capability missing).
   - Reviewer independence invariant: Plan Reviewer != Planner; Work Reviewer != Producer (strictly different endpoint provider/model).
   - Operational snapshot evaluation: active cooldown and unavailable exclusions; unknown quota admitted fail-open per ADR 0060/0064 §4 without speculative blocking.
   - Deterministic lexical tie-breaking: `-score`, provider, profile, endpoint alias.
   - Static presets equivalence for retained V1 modes (`normal`, `codex_only`, `claude_only`, `gemini_sub`, etc.).
   - Resolution schema `agent-phase-resolved-v7` registered in `SUPPORTED_RESOLVED_SCHEMAS`.

7. **Dispatcher Runtime & CLI Wiring**:
   - Isolated `libexec/agent_phase/v2_dispatch.py` ensuring net-zero line growth in `libexec/agent_phase/dispatch.py` (strictly pinned at 2132 lines).
   - `libexec/agent_phase/cli.py` branches on request schema (`agent-phase-request-v2` vs `agent-phase-request-v1`).
   - Standalone `libexec/agent_phase/config_routing.py` ensuring candidate generation qualification has zero runtime dependency on `src/`.

8. **Test Inventory and Qualification Suites**:
   - 74 comprehensive unit and integration tests across 6 test files:
     - `src/test/dispatcher/test_agent_phase_request_v2.py` (24 tests)
     - `src/test/dispatcher/test_agent_phase_config_routing.py` (14 tests)
     - `src/test/dispatcher/test_agent_phase_semantic_roles.py` (7 tests)
     - `src/test/dispatcher/test_agent_phase_sqlite_persistence.py` (11 tests)
     - `src/test/dispatcher/test_agent_phase_dynamic_routing.py` (9 tests)
     - `src/test/dispatcher/test_agent_phase_v2_dispatch.py` (9 tests)
   - All 1733 legacy dispatcher tests passing 100% (1807 total passing dispatcher tests).
   - All new modules registered in `testing/apg-test-inventory.json`.
   - File length policy passes with zero violations and zero headroom growth on allowanced files.
   - Record identity passes with 64 ADRs and 191 exits.

## Review Findings Disposition (Pre-Planning and Work-Review F1–F13)

All 13 work-review findings from the producer candidate review have been incorporated under disposition `amend`:
- **F1 (CLI Roster Root Argument)**: Passed explicit repository root to `load_roster(root)` in `resolution_v2.py` and `v2_dispatch.py` to fix positional argument `TypeError` during CLI execution.
- **F2 (V2 Dispatch & Resolution Integrating Test Suite)**: Authored `src/test/dispatcher/test_agent_phase_v2_dispatch.py` exercising `resolve_v2`, `dispatch_v2`, dry-run, test runner execution, Invariant 14 pre-launch route verification, attempt route reuse recovery, retry predecessor linking, daemon-free SQLite lifecycle, and CLI error handling.
- **F3 (CLI Exception Handling Coverage)**: Extended `cli.ERRORS` to catch `NoRouteAvailableError`, `RoutingResolutionError`, `PersistenceError`, `CapabilityError`, and `V2DispatchError`, ensuring CLI exits with code 2 without unhandled Python tracebacks.
- **F4 (Pre-Launch Route vs Staged Dispatch Semantics)**: Updated `dispatch_v2` to support `runner`, emit display progress, and report status `"completed"` on actual execution, `"dry_run"` on dry run, and `"staged_pre_launch"` when no runner is supplied (avoiding false "dispatched" claim).
- **F5 (Table Helper Functions & Recovery Readback)**: Implemented complete CRUD helper functions across all relational tables in `persistence.py`; re-read existing routes via `get_attempt_route_resolution` during attempt recovery to guarantee route immutability.
- **F6 (Persistence Immutability and Relational Coverage)**: Replaced `INSERT OR REPLACE` with plain `INSERT` in `persistence.py` across `runs`, `route_resolutions`, `actor_bindings`, `configuration_provenance`, and `artifacts` to prevent accidental overwrites and cascading deletions; implemented dedicated readers/writers for all 14 schema tables.
- **F7 (Cascade Prevention & Status Updates)**: Added `update_run_status` and `get_run` to mutate run status safely without triggering foreign-key cascades on child rows.
- **F8 (Reviewer Independence Keying)**: Keyed reviewer independence checks in `dynamic_router.py` on exact semantic roles (`ROLE_PLANNER in prior_roles`, `ROLE_PRODUCER in prior_roles`) or exact binding IDs (`== "binding_plan"`, `== "binding_work"`), resolving substring collision between `binding_plan` and `binding_plan_review`.
- **F9 (Static Preset Deduplication & Multi-Turn Dynamic Resolution)**: Replaced duplicate mode tuple in `resolution_v2.py` with import of `RETAINED_STATIC_MODES`; added `resolve_all_dynamic` support accumulating prior turn resolutions to enable reviewer independence across multi-turn plans.
- **F10 (Planner Posture Capability Matching)**: Removed posture restriction forcing Plan turns to be strictly read-only review endpoints, permitting capable mutating endpoints (e.g. `codex-architecture-docs-primary`) to serve planning turns.
- **F11 (Dual TOML Config Parity Tests)**: Aligned `source_type` in `agentic_praxis_grimoire.config` to `"project_config"` and `"global_config"`; added comprehensive cross-check parity test in `test_agent_phase_config_routing.py` verifying identical parsing, validation, precedence resolution, and error handling.
- **F12 (V1 Resume Boundary Preservation)**: Removed `RESOLVED_V7` from V1 `SUPPORTED_RESOLVED_SCHEMAS` in `route_provenance.py` so V1 resume validation strictly rejects V7 documents with `RESUME_RESOLVED_SCHEMA_UNSUPPORTED`.
- **F13 (Candidate Commit and Provenance Correction)**: Corrected candidate commit reference in Exit 00193 to APG147 `0cf473a6010f40a35b4b7f1c0650a7a053cb60cc`.

## Known Gaps Explicitly Deferred

The following items are intentionally deferred and tracked for subsequent phases:
- **V0120-D**: Operational observations ingestion pipeline, cooldown decay automation, candidate hardening, live provider canary runs.
- **V0120-D/E**: Automated CI pipeline execution for `bin/apg-test-dispatcher` sidecar test lane (currently verified locally via dedicated qualification harness); positive worker capability branch and upstream worker pool integration (`agent_workers`).
- **V0120-E**: Go dispatcher surfaces and JACA integration.

## Next Separately Authorized Phase

The next phase is **V0120-D** (`APG149` — Bounded Dynamic Routing, Operational Observations, and Candidate Hardening). No V0120-D work is begun in this dispatch.
