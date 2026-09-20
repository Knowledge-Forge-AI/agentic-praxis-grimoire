# ADR 0069 — v0.13 Program Scope and Forward Dispatcher Reference Doctrine

- Status: Accepted
- Date: 2026-09-20
- Phase: APG159 (Roadmap Stage: V0130-A)

## Context

During the v0.12 architecture transfer, APGR adopted the lightweight single-phase execution runtime prototyped in Agent-Central (ADR 0058, ADR 0063). However, ADR 0067 §8 recorded standing doctrine that Agent-Central's dispatcher remained an active, supported reference implementation and was not being decommissioned. This dual-reference posture created ambiguity regarding forward ownership, schema evolution, and operational maintenance boundaries.

Under delegated program direction, the operator has authorized APGR v0.13.0 to establish APGR as the sole forward reference single-phase dispatcher. This requires superseding the forward-looking reference doctrine of ADR 0067 §8 while preserving historical parity evidence, outbox topology, and backward compatibility.

Crucially, the transition must be a reversible, owner-executed adoption by Agent-Central, rather than a forced deprecation or destructive cutover executed unilaterally by APGR. Furthermore, external worker-supervisor contracts must remain stable.

## Decision

### 1. Forward Reference Dispatcher Ownership
APGR becomes the authoritative reference implementation for single-phase dispatch, execution coordination, dynamic routing, and artifact finalization. ADR 0067 §8 is superseded prospectively on this point. Historical parity records, baseline observations, and outbox conventions established under v0.12 remain valid historical evidence.

### 2. Reversible Owner-Executed Adoption
The retirement of Agent-Central's internal dispatcher is owned and executed by the Agent-Central maintainer. APGR does not delete external code, replace external wrappers, alter host settings, or trigger workstation activations. APGR provides clean forwarding interfaces and handoff specifications (`docs/architecture/v0-13-agent-central-ownership-transition.md`) ensuring the Agent-Central owner can adopt APGR-native dispatch or roll back without service interruption.

### 3. Preservation of Compatibility Aliases and External Worker Facades
To guarantee seamless backward compatibility throughout v0.13:
- APGR-owned identifiers adopt forward names while maintaining compatibility aliases for at least one minor release:
  - `AGENT_PHASE_RUN_ROOT` -> `APGR_RUN_ROOT` (alias retained)
  - `AGENT_CENTRAL_GENERATION_STORE` -> `APGR_GENERATION_STORE` (alias retained)
  - `AGENT_CENTRAL_ACTIVE_ROOT` -> `APGR_ACTIVE_ROOT` (alias retained)
  - Diagnostics prefix `agent-central:` -> `apgr:` (alias retained)
- External worker-facade contracts defined by the interactive worker supervisor remain strictly unchanged:
  - `AGENT_CENTRAL_WORKER_*`, `AGENT_CENTRAL_PARENT_ID`, `AGENT_CENTRAL_MANAGED_PARENT`.
  - The interactive worker supervisor (`bin/agent-worker`, `libexec/agent_workers/`) remains external to APGR.

### 4. Standalone Operation Release Gate
APGR establishes a hard release gate for v0.13:
`V0130_I_NO_AGENT_CENTRAL_DISPATCHER_DEPENDENCY`
No APGR dispatch, resolve, resume, finalize, or archive operation may require an Agent-Central checkout or import external Agent-Central modules. Mechanical validation will enforce that no non-historical, non-allowlisted references to `agent-central` exist in operational execution paths.

## Consequences

- APGR is fully self-contained and independently testable without external checkouts.
- Agent-Central can migrate to APGR dispatch on its own schedule with zero lock-in.
- Historical evidence and parity baselines from v0.12 are preserved without contradiction.
