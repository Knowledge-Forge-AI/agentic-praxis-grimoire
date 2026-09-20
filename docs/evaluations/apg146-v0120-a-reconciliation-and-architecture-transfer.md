# APG146 — v0.11 Reconciliation and v0.12 Architecture Transfer

## Scope and status

Phase ID: `APG146`  
Roadmap Stage: `V0120-A`  
Disposition: **amend** (incorporating independent plan-review findings)  
Outcome: `V0120_A_ARCHITECTURE_ACCEPTED_AND_HANDOFFS_READY`  

APG146 initiates the APGR v0.12 architecture and runtime transfer program under roadmap stage `V0120-A`. This phase is strictly architecture, documentation, and governance; it makes zero code, test-harness, packaging, or remote mutations.

## 1. Terminal Publication Reconciliation

APGR v0.11.0 publication is terminal, historical, and closed across GitHub Release, Go, PyPI, npm, and Homebrew tap.
- **Release Commit**: `58b80a1731e38afbdb98925777ed9479b5679d86`
- **Release Tree**: `eccac857cf19cc5b845c0f582be69f4549decd77`
- **Public Parent**: `250ce73a3dac71a89b8efeee9b8fe6cb0420bf18` (v0.10.0 release)
- **Tag**: `v0.11.0`
- **Deliverables**: 10 distribution artifacts verified with SHA-256 digests.
- **Closure Ledger**: `docs/governance/v0-11-closure-ledger.json` remains terminal at 55/55/0/0 (`inherited_roadmap_open_items = 0`).

Current release and process prose across `docs/roadmap.md`, `docs/v0-11-roadmap.md`, `docs/distribution.md`, `docs/README.md`, and `AGENTS.md` has been reconciled to reflect v0.11.0 as published terminal state. Historical phase records (APG138–APG145, READINESS1–4, STAGING-PREP1–4, REPAIR1–13) remain immutable contemporaneous evidence.

## 2. Pinned Baselines Inspected

- **APGR Working Baseline**: `d3e094bb15a2c5ea193afd4855d4a63b1aa06ab7` (main).
- **Agent-Central Pinned Baseline**: `56e9bb039536dfc8893e61a431681d6a32167b6f` (main).
- **JACA Baseline**: envelope-supplied pin `e1fafd1884e203a94151a3c429cbca6c313c2332` **does not resolve** in the inspected checkout. Content readback was performed against local checkout HEAD `08ca2208805cf446bd15da0a6b4c8c58db737587` (ADR 0014 and `docs/specs/roadmap/roadmap-orchestration-v1.md` §18.13, quoted verbatim in the handoff). Working tree clean; JACA unmodified by this phase.

## 3. Proposal and Review Disposition

The bound planner proposal (`agent-phase-plan-material-v1`, sha256 `570a6896...`) is **amended** within the original task scope to address all 11 independent plan-review findings:
- **Finding 1 (Phase ID Grammar Violation)**: Replaced invalid token `V0120-A` in status/record identities with the next sequential canonical phase ID `APG146`. The exit record is allocated as `00191-apg146-v0120-a-reconciliation-and-architecture-transfer-exit.md`, the evaluation as `apg146-v0120-a-reconciliation-and-architecture-transfer.md`, and `Phase ID: APG146` is explicitly bound. `V0120-A` is retained strictly as the roadmap stage label, maintaining mechanical conformance with `libexec/apg_record_identity.py`.
- **Finding 2 (Supersession / Boundary Amendment)**: ADR 0058 explicitly states its relationship to ADR 0051 (amending the orchestration boundary for single-phase execution runtime) and extends `docs/architecture/apg-jaca-integration.md` with a dedicated v0.12 successor boundary section.
- **Finding 3 (Release/Process Prose Reconciliation)**: Stale present-tense and candidate claims were reconciled across `docs/distribution.md`, `docs/v0-11-roadmap.md`, `docs/roadmap.md`, `docs/README.md`, and `AGENTS.md`.
- **Finding 4 (Index Updates)**: `docs/README.md` and `AGENTS.md` were updated with links to `docs/v0-12-roadmap.md` and the four new v0-12 architecture documents.
- **Finding 5 (Curated Surface Registration)**: Restricted `release/public-surface.json` edits to `docs/v0-12-roadmap.md` (matching `docs/v0-10-roadmap.md` and `docs/v0-11-roadmap.md`), preserving the curated nature of `critical_files`.
- **Finding 6 (Tool-Derived Counts)**: Replaced hardcoded count claims with live tool readouts. Terminal readout against the delivered tree: `PASS APG record identity: 62 ADRs, 189 exits, 189 phase IDs; next ADR 0063; next exit 00192`.
- **Finding 7 (Verification Suite Scope)**: Executed the full maintained suite of documentation, CI topology, prompt defense, generated drift, and skill library checks.
- **Finding 8 (Release Policy Invariants)**: ADR 0062 encodes durable release invariants (single parent, exact tree match, subject match, signed checksums); specific v0.11.0 commit and tree identities are segregated into `docs/architecture/v0-12-v011-publication-regression-inputs.md` as historical evidence.
- **Finding 9 (v0.12 Governance Clarification)**: `docs/v0-12-roadmap.md` explicitly defines the governance model: an engineering milestone progression governed by ADRs, bounded phase contracts, and regression test suites, rather than a cloned backlog closure ledger.
- **Finding 10 (Migration Inventory Boundary)**: In `docs/architecture/v0-12-agent-central-migration-inventory.md`, marked `COMPATIBILITY-SHIM` as a recommendation delivered for the Agent-Central team to disposition, strictly avoiding APGR mutations in Agent-Central.
- **Finding 11 (Baseline Hygiene)**: Cited the JACA baseline supplied by the dispatcher envelope. **Corrected at closeout**: `e1fafd1884e203a94151a3c429cbca6c313c2332` does not resolve as an object in the inspected JACA checkout (`git cat-file -t` fails). The JACA content readback actually performed was against local checkout HEAD `08ca2208805cf446bd15da0a6b4c8c58db737587`, whose §18.13 ownership matrix was re-verified verbatim at closeout. The handoff document now cites the inspected HEAD and records the envelope pin as unresolvable rather than asserting it.

## 4. Architecture Decisions Formalized

The phase authored five sequential ADRs (0058–0062):
1. **[ADR 0058](../adr/2026/09/0058-apgr-jaca-product-boundary-and-runtime-ownership.md)**: APGR-JACA Product Boundary and Single-Phase Runtime Ownership.
2. **[ADR 0059](../adr/2026/09/0059-decoupled-semantic-role-graph-and-flexible-actor-binding.md)**: Decoupled Semantic Role Graph and Flexible Actor Binding.
3. **[ADR 0060](../adr/2026/09/0060-request-v2-dynamic-routing-and-sqlite-persistence.md)**: Request V2 Protocol, Bounded Dynamic Routing, and SQLite Dispatcher Persistence.
4. **[ADR 0061](../adr/2026/09/0061-provider-capability-matrix-and-parity.md)**: First-Class Provider Capability Matrix and Asymmetry Reconciliation.
5. **[ADR 0062](../adr/2026/09/0062-v012-release-hardening-and-conditional-nixpkgs.md)**: v0.12 Release Hardening, Operator Discipline, and Conditional Nixpkgs Policy.

## 5. Delivered Architecture Artifacts

- **[APGR v0.12 Roadmap](../v0-12-roadmap.md)**: Establishes the 7 substantive stages (V0120-A through V0120-G).
- **[Agent-Central Migration Inventory](../architecture/v0-12-agent-central-migration-inventory.md)**: All 62 `libexec/agent_phase/` modules, 10 `bin/agent-phase-*` wrappers, the `controller_generation*` bootstrap chain, provider catalogs and profile compilers, and 65 dispatcher test suites, with MIGRATE, COMPATIBILITY-SHIM, RETAIN, and REJECT classifications derived from source docstrings at the pinned baseline.
- **[JACA Disposition Handoff](../architecture/v0-12-jaca-disposition-handoff.md)**: **Proposed, unaccepted** §18.13 ownership matrix rows with per-row deltas, and draft exported Go package definitions (`pkg/phase`, `pkg/candidate`, `pkg/evidence`, `pkg/provider`).
- **[Agent-Central Ownership Transition](../architecture/v0-12-agent-central-ownership-transition.md)**: **Proposed, unaccepted** staged migration schedule and compatibility forwarding guidance.
- **[v0.11 Publication Regression Inputs](../architecture/v0-12-v011-publication-regression-inputs.md)**: Codifies 13 hosted CI repair increments (`R1`–`R13`) as `REG-R*`, and the publication-hardening themes as an independent `REG-P1`–`REG-P13` namespace with an explicit `F1`–`F12` traceability table, for stage V0120-F.

## 6. Closeout Disposition

Terminal closeout disposition: **amend**. The independent work review returned 15
advisory findings (`F-A`–`F-O`); all 15 were accepted and applied, none rejected,
deferred, or overruled. Four (`F-A`, `F-B`, `F-C`, `F-D`) were re-verified against
live sources before amendment and were confirmed factual errors in the pre-final
candidate. The per-finding disposition table, with the verification performed for
each, is recorded in [exit 00191](../status/2026/09/16/00191-apg146-v0120-a-reconciliation-and-architecture-transfer-exit.md).

Closeout also amended two files outside the pre-final candidate set:
`docs/adr/2026/08/0051-v0-7-embeddable-toolkit-architecture-and-roadmap.md`
(forward-pointer amendment notice required by `F-F`) and
`docs/architecture/apg-jaca-integration.md` (scoping notes on the v0.7 exclusion
statements that ADR 0058/0060/0061 supersede).

## 7. Next Separately Authorized Phase

The next phase in the v0.12 program is **`V0120-B` (Agent-Central Dispatcher Parity Migration)**. It must be separately authorized and dispatched. It is not started in this phase.
