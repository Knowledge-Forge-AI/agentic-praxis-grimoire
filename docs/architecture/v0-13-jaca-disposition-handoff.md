# JACA Disposition Handoff: Hosting Seams and State Boundaries (v0.13)

- **Status**: **Proposed** — APGR-side decision recorded; delivered unaccepted for JACA team disposition
- **Target Version**: APGR v0.13 / JACA Successor Architecture
- **Governing ADRs**: [ADR 0069](../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md), [ADR 0070](../adr/2026/09/0070-configurable-review-stage-mutation-policy.md), [ADR 0071](../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md)
- **Phase**: APG159 (Milestone V0130-A)

---

## 1. Status and Authority

This document has **no** authority over JACA. It records what APGR has designed on its own side for v0.13.0 and what APGR offers for optional JACA consumption. Nothing here has been reviewed or accepted by the JACA team, and no statement in it should be interpreted as JACA agreement. Every proposed matrix row, DTO interface, and hosting seam remains declinable in whole or in part.

---

## 2. Hosting Seams and Invariants

### 2.1 Explicit Home Relocation (Zero `JACA_HOME` Coupling)
- APGR strictly adheres to the resolution hierarchy: `--apgr-home` > `APGR_HOME` > `~/.apgr`.
- **APGR never reads or infers paths from `JACA_HOME`**. If a JACA host embeds APGR, it supplies the APGR root explicitly (e.g. `APGR_HOME="$JACA_HOME/apgr"` or via explicit Go loader parameters).
- Filesystem layout conforms to [`apgr-home-layout-v1`](../specs/apgr-home-layout-v1.md).

### 2.2 Independent State Persistence
- APGR and JACA maintain **completely separate SQLite databases**.
- APGR does NOT implement shared `ext_*` tables, cross-product schema ownership, or a shared `database/sql` driver in v0.13.
- All integration between JACA and APGR occurs via typed Go DTOs and explicit record exchanges.

### 2.3 Deferral of Custom Go TOML Parser
- APGR has deferred the authoring of a handwritten Go TOML subset parser (H3).
- JACA or other hosting orchestrators embedding APGR's Go contracts pass typed DTO values or validated JSON documents directly to APGR validators. Consumers utilizing their own TOML parsers remain responsible for their own dependencies.

### 2.4 Review-Mutation Policy Go Contracts
- APGR exports typed Go structs and validators for review mutation observations:
  - `evidence.ReviewMutationPolicy` (`block`, `warn`, `allow`)
  - `evidence.ReviewMutationObservation`
  - `evidence.ValidateReviewMutationObservation()`
- JACA's heavier dispatcher may select `block` and ignore observation warnings without violating contract compatibility.

### 2.5 SQLite Schema Manifest and Go Row DTO Contracts
- APGR exports a machine-verifiable, normalized JSON schema manifest for its SQLite persistence database at `docs/architecture/dispatcher-sqlite-schema-v5.json`, generated directly from in-memory migrations by `libexec/agent_phase/schema_manifest.py`.
- APGR provides typed Go hosting contracts in package `schema`:
  - `schema.DispatcherSchemaManifest` and `schema.ValidateDispatcherSchemaManifest()` for structure and column/type validation.
  - Typed row DTOs (`RunRecord`, `RouteResolutionRecord`, `InvocationAttemptRecord`, `OperationalObservationRecord`, `ReviewMutationObservationRecord`, `ReviewMutationPolicyRecord`, `LegacyQuarantineObservationRecord`, `LegacyQuarantinePolicyRecord`) for marshaling database records into Go runtime structs without requiring a SQLite driver or CGo dependency.
- Consumer fixtures in `testing/fixtures/jaca_consumer/adapter.go` and `testing/fixtures/jaca_consumer/adapter_test.go` verify that JACA consumer adapters can inspect manifests and row records with zero type leaks (`schema.` prohibited in AST containment tests) and zero subprocess execution.

---

## 3. Compliance with JACA Interface Constraints

APGR v0.13 respects all four JACA Interface Control Requirements:
- **ICR-001 (Single Adapter)**: All APGR primitives are consumable through JACA's single roadmap adapter.
- **ICR-002 (Requalification Notice)**: Any selection-affecting changes to APGR corpus or rule identities trigger formal notice.
- **ICR-003 (Consumer Fixtures)**: All exported Go packages provide substantive, isolated consumer fixtures under `testing/fixtures/jaca_consumer/`.
- **ICR-004 (Published Release Consumption)**: JACA consumes APGR exclusively as a tagged, published Go module with verified sums; no local checkouts or `replace` directives are required.
