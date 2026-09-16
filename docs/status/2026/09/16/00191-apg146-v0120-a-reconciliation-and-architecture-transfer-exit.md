# APG146 — v0.11 Reconciliation and v0.12 Architecture Transfer Exit

Phase ID: `APG146`

## Status

Disposition: **amend**. Exit 00191 is allocated to APG146 without renumbering or substitution.  
Outcome: `V0120_A_ARCHITECTURE_ACCEPTED_AND_HANDOFFS_READY` (v0.11.0 terminal publication reconciled across all release documentation; v0.12 roadmap established with 7 substantive stages; ADRs 0058–0062 authored and accepted; Agent-Central migration inventory and transition handoff delivered; JACA §18.13 ownership amendment handoff and Go interfaces defined; v0.11 publication repair cases codified as V0120-F regression inputs).

Accounting: Historical v0.11 closure accounting remains terminal at 55/55/0/0 (45 canonical skills: 14 stable / 31 provisional; six active CSS/JS debts; description ceiling 11,507 bytes). v0.12 executes as an engineering milestone delivery program governed by ADRs 0058–0062 and regression suites without backlog ledger duplication.

The [evaluation](../../../../evaluations/apg146-v0120-a-reconciliation-and-architecture-transfer.md) records the full verification and disposition details for APG146 / V0120-A.

## Summary of Completed Work

1. **v0.11 Terminal Reconciliation**:
   - Updated `docs/roadmap.md`, `docs/v0-11-roadmap.md`, `docs/distribution.md`, `docs/README.md`, and `AGENTS.md` to reflect v0.11.0 as published terminal state across GitHub Releases, Go, PyPI, npm, and Homebrew tap.
   - Preserved all historical v0.11 phase and repair records (APG138–APG145) as immutable history.

2. **v0.12 Roadmap (`docs/v0-12-roadmap.md`)**:
   - Authored the APGR v0.12 roadmap defining 7 substantive, dependency-ordered stages:
     - `V0120-A`: Terminal Reconciliation and Architecture Transfer (current phase, APG146)
     - `V0120-B`: Agent-Central Dispatcher Parity Migration
     - `V0120-C`: Semantic Roles, Flexible Actor Binding, and SQLite Dispatcher Persistence
     - `V0120-D`: Bounded Dynamic Routing and Provider Parity
     - `V0120-E`: Go Surfaces and JACA Qualification / Handoff
     - `V0120-F`: Release Hardening, Conditional Nixpkgs, and Integrated Readiness
     - `V0120-G`: Deterministic v0.12.0 Publication and Terminal Reconciliation

3. **Architecture Decision Records (ADRs 0058–0062)**:
   - **ADR 0058**: Product boundary (APGR executes one phase; JACA orchestrates across phases), single-phase runtime permanent ownership in APGR, standalone APGR invariant (no outer roadmap loop, no daemon), amending ADR 0051 and extending `docs/architecture/apg-jaca-integration.md`.
   - **ADR 0059**: Decoupled semantic role graph aligned with JACA successor vocabulary (Planner, Plan Reviewer, Plan Review Disposition, Producer, Work Reviewer, Work Review Disposition, Reviser, Closeout Agent), flexible actor binding, and persistent decoupled records for merged stages.
   - **ADR 0060**: Request V1 backward compatibility, Request V2 protocol (`agent-phase-request-v2`), deterministic fallback routing, bounded dynamic router (evaluating role/work class, provider capabilities, reviewer independence, bounded availability, unknown usage, and recent typed failure history; no daemon, no predictive scheduling, no silent route replacement during recovery), and SQLite persistence under `~/.apgr/state/dispatcher.sqlite3` with run-owned files on disk.
   - **ADR 0061**: First-class provider targets (Codex, Claude, Antigravity), capability matrix, closing Agent-Central asymmetries where upstream allows, fail-closed refusal for unsupported features without weak emulation, minimal command/security brokering.
   - **ADR 0062**: Release operator hardening invariants (numeric draft release ID binding, strict release authority checking, trusted PyPI publishing alignment, npm distribution state machine, resumable channel receipts, automated Homebrew formula support, machine-readable postmerge proof), and conditional Nixpkgs admission policy based on Knowledge Forge AI precedent (Theme Forge).

4. **Architecture Handoffs and Inventory**:
   - `docs/architecture/v0-12-agent-central-migration-inventory.md`: Inventory of all 62 `libexec/agent_phase/` modules, the 10 `bin/agent-phase-*` wrappers, the `controller_generation*` bootstrap chain, provider catalogs/profile compilers, and the 65 dispatcher test suites, categorized into MIGRATE, COMPATIBILITY-SHIM (advisory recommendation for Agent-Central), RETAIN (excluded from APGR migration scope), and REJECT.
   - `docs/architecture/v0-12-jaca-disposition-handoff.md`: **Proposed, unaccepted** §18.13 ownership matrix rows with an explicit per-row delta, plus draft exported Go packages (`pkg/phase`, `pkg/candidate`, `pkg/evidence`, `pkg/provider`).
   - `docs/architecture/v0-12-agent-central-ownership-transition.md`: **Proposed, unaccepted** staged transition schedule and compatibility forwarding guidance.
   - `docs/architecture/v0-12-v011-publication-regression-inputs.md`: Codified 13 hosted CI repairs (`R1`–`R13`) into `REG-R*` and the publication-hardening themes into an independent `REG-P1`–`REG-P13` namespace, with an explicit `F1`–`F12` traceability table covering every historical publication finding.

5. **Index and Surface Updates**:
   - Indexed ADRs 0058–0062 in `docs/adr/README.md`.
   - Indexed exit 00191 in `docs/status/README.md`.
   - Registered `docs/v0-12-roadmap.md` in `critical_files` under `release/public-surface.json`.

## Closeout Disposition of Work-Review Findings

The terminal closeout disposition is **amend**. The independent work review
returned 15 advisory findings (`F-A`–`F-O`). Fourteen were accepted and applied;
one was accepted as already-correct with a clarifying cross-reference. Four were
first re-verified against live sources before amendment:

| Finding | Verification performed at closeout | Disposition |
| --- | --- | --- |
| `F-A` Publication `F1`–`F12` identifier collision | Read `private/releases/v0.11.0/publication1/README.md` §1; confirmed all 12 slots carried different content | Accepted — new `REG-P*` namespace plus `F1`–`F12` traceability table; dropped lessons (epoch binding, PyPI verification-only, host-binary destructive risk, attestation, tap baseline) restored as `REG-P9`–`REG-P13` |
| `F-B` Uppercase SHA-256 assertion inverted | Inspected `publication1/assets/SHA256SUMS`: all entries lowercase | Accepted — `REG-P8` now asserts lowercase and rejects uppercase |
| `F-C` Inventory covered 33 of 62 modules | `ls libexec/agent_phase/*.py` at the pinned Agent-Central baseline: 62 | Accepted — all 62 enumerated, plus wrappers, bootstrap chain, and test suites; coverage statement added |
| `F-D` Inaccurate module descriptions | Extracted every module docstring at the pinned baseline via `ast.get_docstring` | Accepted — rationales rewritten from source docstrings; `dispatch.py`, `cli.py`, `lifecycle_dispatch.py`, `candidate.py`, `envelope.py`, `run.py`, `failure_boundary.py`, `ownership_challenge.py`, `routing.py`, and others corrected |
| `F-E` Presumed JACA/Agent-Central acceptance | — | Accepted — both handoffs restated as Proposed/unaccepted; ADR 0058 consequence rewritten; CLI-parity premise withdrawn against JACA §18.12 |
| `F-F` Unamended contradicting v0.7 statements | — | Accepted — scoping notes added to `apg-jaca-integration.md`; forward-pointer amendment notice added to ADR 0051 |
| `F-G` Role vocabulary regression | — | Accepted — ADR 0059 role names restored in the JACA handoff matrix |
| `F-H` "Preserved" label on a rewritten row | — | Accepted — per-row proposed-delta column added; JACA row relabelled a narrowing rewrite |
| `F-I` JACA baseline pin unresolvable | `git cat-file -t e1fafd18…` fails; HEAD is `08ca2208…`; §18.13 re-verified verbatim | Accepted — inspected HEAD cited, envelope pin recorded as unresolvable |
| `F-J` RETAIN rows naming non-repository paths | — | Accepted — RETAIN redefined as "excluded from APGR migration scope"; host/home items generalized |
| `F-K` Go surfaces missing `context.Context` | — | Accepted — `InspectWorkingTree`, `ComputeTreeDigest`, `LookupCapability` now take `ctx` |
| `F-L` Undefined CLI surface presented as usable | `internal/cli/cli.go` exposes only `build-info`, `report`, `skills`, `footprint`, `env`, `analyze`, `response`, `legacy` | Accepted — marked prospective and deferred to `V0120-B` |
| `F-M` Stale tool readout | Re-ran `bin/apg-check-record-identity` | Accepted — refreshed to 189 exits / next 00192 |
| `F-N` Wrong `stage_operator.py` path | — | Accepted — corrected to `private/releases/v0.11.0/stage_operator.py` |
| `F-O` Fail-open vs fail-closed precedence | — | Accepted as a clarification — precedence rule added to ADR 0060 §3 and cross-referenced from ADR 0061 §3 |

No finding was rejected, deferred, or overruled.

## Preservation and Next Boundary

- Neither Agent-Central nor JACA was mutated; both remained strictly read-only evidence sources. Both working trees were re-confirmed clean at closeout.
- No public releases were created, modified, or deleted.
- No host or workstation system configurations were modified.
- The next separately authorized phase is **`V0120-B` (Agent-Central Dispatcher Parity Migration)**. It must not begin until separately authorized and dispatched.
