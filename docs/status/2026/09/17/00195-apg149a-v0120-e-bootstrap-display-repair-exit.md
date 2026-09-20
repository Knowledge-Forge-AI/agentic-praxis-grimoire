# APG149A — APGR V0120-E-REPAIR1 — Request V2 Live-Display Contract and Pre-Launch Reconciliation Repair Exit

Phase ID: `APG149A`
Exit ID: `Exit 00195`

## Status

Disposition: **amend**. Exit 00195 records the bounded runtime repair resolving the Request V2 live-display contract mismatch and pre-launch attempt reconciliation failure that blocked V0120-E dispatch.
Outcome: `V0120_E_BOOTSTRAP_DISPLAY_REPAIR_COMPLETE`

## Root Cause Analysis

A real Request V2 dispatch of the approved `V0120-E` request failed before provider launch with:
```
agent-phase-dispatch: Turn execution failed:
Display.stage_started() missing 2 required positional arguments:
'role' and 'endpoint'
```

1. **API Contract Mismatch**: `Display.stage_started` defines signature `(index: int, stage: str, role: str, endpoint: Any, stage_count: int = 5)`. The V2 call site in `libexec/agent_phase/v2_turns.py` invoked `display.stage_started(binding.binding_id, route.endpoint_alias)` with only 2 arguments instead of 5, missing `role` and `endpoint` and passing the binding ID into `index`.
2. **Pre-Launch Attempt Inconsistency**: Prior to runner invocation, `v2_turns.py` persisted an invocation attempt with status `running` and updated semantic responsibilities to `running`. When an exception occurred during the display observer call or pre-launch preparation, the outer dispatcher marked the run status as `failed`, but the inner invocation attempt and semantic responsibilities remained falsely trapped in `running` status with null completion timestamps.

## Repaired Architecture and Contracts

1. **Display Call Contract**:
   - `Display` is preserved as an observer without altering or weakening its V1 contract.
   - V2 calls `display.stage_started`:
     - `index`: 1-based top-level invocation index (1..stage_count).
     - `stage`: `binding.binding_id` (documented stable V2 actor binding label).
     - `role`: deterministic comma-separated string of bound semantic responsibilities (`", ".join(binding.roles)`).
     - `endpoint`: `route` (`ResolvedActorRoute`), exposing truthful `.provider` and `.profile` attributes without leaking sensitive policies.
     - `stage_count`: `len(binding_policy.bindings)` (5 for default topology, 8 for unmerged topology).
   - `display.stage_finished(binding.binding_id, exit_code, t_elapsed)` called on successful turn execution.
   - `display.stage_failed(binding.binding_id, detail)` safely called on runner failure or exception.
   - Observer methods are wrapped safely via `_safe_display_call` so broken displays cannot mask or alter execution exceptions.

2. **Pre-Launch Reconciliation**:
   - Invocation attempt is initially recorded with status `staged`.
   - `status` is transitioned to `running` immediately before provider runner invocation.
   - `try ... except BaseException` encloses the turn execution:
     - Pre-launch exceptions (before `runner_launched`): attempt is durably updated to `status="failed_pre_launch"`, `exit_code=None`, `completed_at` set. Semantic responsibilities for active roles updated to `status="failed"`, `outcome="failed_pre_launch"`.
     - Substantive failures (after `runner_launched`): attempt is durably updated to `status="failed"`, `completed_at` set.
     - Re-raises `PreLaunchFailureError` (subclass of `V2TurnError`) so `v2_dispatch.py` marks `runs.status="failed"` with `runs.outcome="failed_pre_launch"`.
     - No execution receipts or candidates are fabricated.
     - Route resolution provenance in `route_resolutions` table is preserved intact.

3. **Historical Failed Run Evidence**:
   - The operator's prior failed local SQLite database remains completely untouched and unmutated.
   - Exact historical reconciliation cannot be proven from durable evidence alone without guessing, so prior records are left intact as immutable historical evidence.
   - Fresh dispatch runs mint new unique run IDs cleanly under the repaired engine.

4. **Terminal Revisor Amendments (Post-Review Hardening)**:
   - **Operator Interrupt Handling**: `dispatch_v2` catches `KeyboardInterrupt` and `BaseException`, terminalizing `runs.status="failed"`, `outcome="operator_interrupted"`, `semantic_outcome="operator_interrupted"`, preventing runs from lingering falsely active.
   - **Consistent Pre-Launch Run Classification**: Any exception prior to runner launch (including invariant-14 `V2TurnError`) is raised as `PreLaunchFailureError`, ensuring both attempt (`status="failed_pre_launch"`) and run (`outcome="failed_pre_launch"`) are classified identically.
   - **Truthful Staging Posture**: Responsibilities remain `status="pending"` in staged mode (`runner=None`), transitioning to `running` only upon actual provider launch.
   - **Accurate Post-Launch Exit Code**: Provider exit code is preserved on downstream failure without coalescing to `NULL`.
   - **Observer Deduplication**: Guard prevents duplicate `display.stage_failed` calls on handled turn failures.

5. **Product Scope Separation**:
   - Zero V0120-E product code (Go packages, JACA handoffs) has been started.
   - Rerun instruction: execute the existing unchanged `V0120-E.request.json`.
