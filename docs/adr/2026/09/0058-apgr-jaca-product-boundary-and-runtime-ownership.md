# ADR 0058 — APGR-JACA Product Boundary and Single-Phase Runtime Ownership

- Status: Accepted
- Date: 2026-09-16
- Phase: APG146 (Roadmap Stage: V0120-A)

## Context

During the v0.7–v0.11 programs, Agentic Praxis Grimoire (APGR) evolved from a repository-local guidance and skill-collection tool into an embeddable Go library and multi-ecosystem CLI. Meanwhile, single-phase agent dispatch was prototyped within Agent-Central (`agent-phase-dispatch`, `libexec/agent_phase`, `common/dispatcher`), and multi-phase roadmap orchestration was developed in Joint Agentic Command Aegis (JACA; see JACA ADR 0014 and `docs/specs/roadmap/roadmap-orchestration-v1.md`).

ADR 0051 (`docs/adr/2026/08/0051-v0-7-embeddable-toolkit-architecture-and-roadmap.md`) previously decided: "JACA imports APG public packages directly; APG does not import JACA or own orchestration." `docs/architecture/apg-jaca-integration.md` likewise froze that "APG never imports JACA. JACA decides when to call APG", returning deterministic in-memory models.

However, as agentic workflows matured, single-phase dispatch became a distinct, reusable runtime layer separate from multi-phase roadmap agendas. Housing single-phase dispatch logic within Agent-Central conflated personal workstation configurations with reusable agent-execution machinery. Furthermore, JACA required a reliable single-phase execution engine beneath its multi-phase agenda.

## Decision

1. **Product Boundary**:
   - **APGR executes one phase**: APGR accepts a structured phase request JSON, manages the bounded stage progression within that single phase (e.g., planning, plan review, production, work review, revision, closeout), invokes provider CLI processes, enforces bounded dynamic routing, and emits an authoritative phase result, evidence, and archive.
   - **JACA orchestrates across phases**: JACA owns the multi-phase roadmap agenda, inter-phase dependency resolution, global review-budget accounting, XO route policy, cross-phase crash recovery, repository-wide mutation fencing, and phase-to-phase artifact authority.
2. **Permanent Single-Phase Runtime Ownership**:
   - APGR becomes the permanent owner of the lightweight, one-phase phase-execution runtime prototyped in Agent-Central (`agent-phase-dispatch`, `libexec/agent_phase`, `common/dispatcher`), including dispatcher-consumed provider/profile catalogs and reusable Go surfaces.
   - APGR will maintain and evolve this runtime natively as part of the APGR codebase starting in v0.12.
3. **Standalone APGR Invariant**:
   - Standalone APGR executes strictly within a single phase envelope. It receives a request JSON from an external caller (a human operator or an external orchestrator like JACA) and emits an authoritative phase result with accompanying evidence and archive references.
   - Standalone APGR contains NO outer roadmap manager loop, NO background daemon, and NO autonomous multi-phase agenda sequencing. Advancing to subsequent phases is always initiated externally.
4. **Relationship to ADR 0051 and Integration Boundary**:
   - This decision amends ADR 0051 and extends `docs/architecture/apg-jaca-integration.md`.
   - The one-way dependency rule is strictly maintained: APGR never imports JACA. JACA imports APGR's public Go packages (e.g., `pkg/phase`, `pkg/candidate`, `pkg/evidence`, `pkg/provider`) to invoke individual phases.
   - Single-phase execution within APGR is explicitly classified as execution runtime, not cross-phase orchestration. JACA retains exclusive authority over multi-phase orchestration.

## Alternatives Considered

- **Retaining Single-Phase Dispatch in Agent-Central**: Rejected because Agent-Central is a personal workstation configuration repository. Coupling reusable execution runtime to personal dotfiles and workstation scripts impedes portability, multi-project adoption, and CI integration.
- **Moving Full Roadmap Orchestration into APGR**: Rejected because multi-phase agenda tracking, cross-phase rollback, and global review accounting belong to JACA's orchestration mission. Bloating APGR with multi-phase agenda management violates its core design as a lightweight, embeddable toolkit.

## Consequences

- In v0.12 stage `V0120-B`, the core dispatcher runtime and profile machinery will migrate from Agent-Central into APGR.
- `docs/architecture/v0-12-jaca-disposition-handoff.md` delivers a **proposed** amendment to JACA's §18.13 ownership matrix for the JACA team to disposition. JACA owns that matrix; this ADR neither amends it nor claims JACA acceptance, and APGR's runtime ownership does not depend on JACA adopting the proposal. If JACA declines or amends it differently, the divergence is recorded and this ADR's decision stands on the APGR side only.
- `docs/architecture/apg-jaca-integration.md` is amended to document the v0.12 single-phase execution interface alongside existing library functions, and to scope the v0.7 exclusion statements that this decision supersedes.
- This ADR amends ADR 0051; a forward pointer is recorded there so the amendment is discoverable from the superseded text.
- **Amendment Note (ADR 0066 / V0120-E)**: ADR 0066 supersedes the `pkg/*` package path layout in Section 4 in favor of top-level Go packages (`phase`, `routing`, `evidence`, `candidate`, `provider`). Furthermore, ADR 0066 and the V0120-E review disposition reject a duplicate Go `ExecutePhase` dispatcher runtime for v0.12. Standalone phase execution is provided by the APGR Python dispatcher runtime, while JACA retains exclusive ownership of its multi-phase XO orchestration loop. APGR's Go domain packages provide immutable data models, pure schema validation, and deterministic algorithms without subprocess invocation or duplicate runtime execution.

