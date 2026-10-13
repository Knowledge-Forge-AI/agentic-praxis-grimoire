# Agent-Central Ownership Transition and Dispatcher Decommission Handoff (v0.13)

- **Status**: **Proposed** — APGR-side decision recorded; delivered unaccepted for Agent-Central team disposition
- **Target Version**: APGR v0.13 / Agent-Central Evolution
- **Governing ADR**: [ADR 0069](../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)
- **Phase**: APG159 (Milestone V0130-A)

---

## 1. Status and Authority

This document has **no** authority over Agent-Central. It records APGR's architecture decisions for v0.13.0 and offers coordination guidance for the Agent-Central maintainer. Nothing here has been reviewed or accepted by the Agent-Central team, APGR modifies zero files in that repository, and every recommendation below is declinable.

---

## 2. Transition Principles: Reversible, Owner-Executed Adoption

Under ADR 0069, APGR establishes itself as the forward reference single-phase dispatcher. However, APGR enforces strict operational discipline:
1. **Zero Unilateral Cutover**: APGR never modifies Agent-Central files, scripts, or workstation configurations.
2. **Owner-Executed Adoption**: The retirement of Agent-Central's internal dispatcher is owned and executed by the Agent-Central maintainer at a time of their choosing.
3. **Reversibility**: The transition is completely reversible. If unexpected issues arise, the Agent-Central maintainer can restore internal dispatching immediately.

---

## 3. Clear Separation of Concerns

The division of responsibilities between APGR and Agent-Central is formalized as follows:

| Subsystem / Responsibility | APGR Ownership | Agent-Central Ownership |
|---|---|---|
| **Single-Phase Execution Dispatcher** | Authoritative reference implementation (`bin/agent-phase-dispatch`, `libexec/agent_phase/`) | Legacy prototype; enters deprecation upon owner adoption |
| **Interactive Worker Supervisor** | External contract consumer | Sole authority (`bin/agent-worker`, `libexec/agent_workers/`) |
| **Worker Facade Environment** | Stable consumer (`AGENT_CENTRAL_WORKER_*`, `AGENT_CENTRAL_PARENT_ID`) | Sole authority defining variable semantics |
| **Operator Settings and Shell Hooks** | Read-only consumer (`claude/settings.json`, RTK doctor) | Sole authority managing workstation configuration |

---

## 4. Recommended Integration Architecture (Manager Disposition M3)

The previous unaccepted suggestion of a bare unconditional `exec apgr-phase-dispatch "$@"` wrapper is **withdrawn** (governing manager disposition M3). Neither command existence in `PATH` nor manual recovery guarantees normal local availability, and an unconditional wrapper risks disrupting the host prototype.

Any future Agent-Central owner-side transition must satisfy these safety principles:
1. **Retain Working Local Path**: Retain a verified local path/implementation rather than delegating blindly.
2. **Pre-Launch Fallback**: If APGR native dispatch is uninstalled, absent, or fails before provider launch, fallback must occur before provider invocation—never automatically replaying an attempt that may have produced side effects.
3. **Owner Deployment Exclusivity**: The Agent-Central repository owner alone deploys, wraps, or retires Agent-Central code. APGR does not deploy into Agent-Central.
4. **Resilience to External Ecosystem State**: Absence, staleness, or failure of external brokers, JACA, or Agent-Security daemons must not disrupt standalone local operation.

APGR guarantees:
- Compatibility aliases for all historical environment variables (`AGENT_PHASE_RUN_ROOT`, `AGENT_CENTRAL_ACTIVE_ROOT`, `AGENT_CENTRAL_GENERATION_STORE`).
- Backward-compatible Request V1 and V2 JSON schema handling.
- Outbox directory structure identical to historical runs.

---

## 5. Standalone Release Gate

APGR enforces release gate `V0130_I_NO_AGENT_CENTRAL_DISPATCHER_DEPENDENCY`:
- APGR's tests, tools, fixtures, and documentation operate 100% standalone.
- No APGR command requires an Agent-Central checkout to execute.
