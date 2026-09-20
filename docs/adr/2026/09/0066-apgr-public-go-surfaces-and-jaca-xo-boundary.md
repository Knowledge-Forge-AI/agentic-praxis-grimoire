# ADR 0066 — Public Go Domain Surfaces, Rejection of Duplicate Go Runtime, and JACA XO Boundary

- Status: Accepted
- Date: 2026-09-17
- Phase: APG150 (Roadmap Stage: V0120-E)

## Context

Following the migration and hardening of the single-phase execution runtime in stages V0120-B, V0120-C, and V0120-D (ADRs 0060, 0061, 0064, 0065), stage V0120-E was chartered to deliver public Go domain packages and provide a consumer qualification harness for Joint Agentic Command Aegis (JACA) Execution Orchestration (XO).

During plan review and architectural alignment, critical boundaries and authority constraints were established:
1. **Rejection of Duplicate Go Dispatcher Runtime**: Draft proposals in ADR 0058 suggested an in-process Go single-phase orchestrator (`ExecutePhase`). However, implementing full stage progression, subprocess management, streaming pipes, and provider CLI execution in Go would create an untested second runtime in APGR that duplicates the hardened Python dispatcher, risking behavioral drift and operational bugs.
2. **Request V2 Work-Only Invariant**: Draft proposals retained runtime fields (`execution_mode`, `constraints`) in Request V2. The approved V2 contract must be strictly work-only (`schema`, `phase_type`, `prompt`), rejecting all embedded runtime routing directives.
3. **Package Directory Structure**: The draft `pkg/` hierarchy proposed in ADR 0058 conflicts with standard Go idioms used elsewhere in APGR (e.g. `schema`, `report`, `skills`, `footprint`).
4. **Subprocess Decoupling (JACA §18.12)**: JACA's roadmap specification strictly prohibits shelling out to APGR or parsing terminal text.
5. **Cross-Language Conformance**: Go domain models and validation logic must maintain 100% byte-for-byte serialization and digest parity with APGR Python implementations.

This ADR formalizes these decisions and establishes the public Go surface architecture for APGR v0.12.

## Decision

### 1. Top-Level Public Go Package Architecture

APGR establishes five additive, top-level Go domain packages under module `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire`:
- `phase`: Immutable work-only Request V2 envelope definition, attempt identity derivation (`DeriveAttemptIdentity`), phase execution status constants, and semantic role constants aligned with JACA ADR 0014 and APGR ADR 0059.
- `routing`: Pure deterministic 6-stage routing resolution ladder (`Resolve`) and canonical telemetry observation digest calculation (`CanonicalDigest`).
- `evidence`: Path-traversal-safe review finding models (`ReviewFinding`), finding dispositions (`FindingDisposition`), and validation receipts (`ValidationReceipt`).
- `candidate`: Immutable candidate workspace identities (`CandidateIdentity`), artifact specifications (`Artifact`), and artifact manifests (`ArtifactManifest`) with path traversal rejection.
- `provider`: Machine-readable provider conformance matrix (`ConformanceMatrix`) validating 22 capability dimensions across Codex, Claude, and Antigravity models.

All five packages carry **Experimental / Provisional** maturity status for APGR v0.12 under ICR-004 and ICR-005. Note that `phase` imports `routing` for route binding adapters; `routing` may be adopted independently, while `phase` brings in `routing`.

### 2. Rejection of Duplicate Go `ExecutePhase` Runtime

APGR explicitly rejects an in-process Go dispatcher runtime (`ExecutePhase`) for v0.12:
- Standalone single-phase execution is owned exclusively by the APGR Python dispatcher runtime (`bin/agent-phase-dispatch`).
- JACA retains exclusive ownership of its multi-phase Execution Orchestration (XO) runtime. JACA executes provider processes and coordinates workflow stages under its own authority.
- APGR's Go domain packages provide immutable data models, pure schema validation, and deterministic algorithms without subprocess invocation or duplicate runtime execution.

### 3. Strict Request V2 Work-Only Grammar

The Go `phase.RequestV2` structure strictly models the work-only contract:
```go
type RequestV2 struct {
    Schema    string `json:"schema"`
    PhaseType string `json:"phase_type"`
    Prompt    string `json:"prompt"`
}
```
Validation strictly rejects payloads containing unknown keys or embedded runtime routing fields (`execution_mode`, `constraints`).

### 4. Policy Neutrality in `routing`

The `routing` package is strictly policy-neutral:
- `routing.RouteRequirements` does not import `phase` or assume APGR-specific role semantics.
- Route selection is executed through a pure 6-stage precedence ladder (Explicit override -> Capability fit -> Performance -> Cooldown check -> Affinity -> Provider default).
- JACA supplies the candidate options and requirements; APGR's resolver executes pure precedence evaluation without usurping JACA's XO route policy authority.
- `routing.CanonicalDigest` implements canonical JSON serialization and SHA-256 calculation, producing bit-for-bit identical hashes with the Python observation model.

### 5. Cross-Language Conformance and Drift Protection

APGR implements a dual-language golden vector conformance corpus (`testing/fixtures/conformance/`):
- Seven golden vector test suites cover Request V2, semantic roles, observation digests, dynamic routing scenarios, evidence reviews, candidate artifacts, and provider capabilities.
- Generator tool `tools/conformance/generate_conformance_corpus.py` supports deterministic generation and verification (`--check`).
- Unit test suites in Python (`src/test/dispatcher/test_cross_language_conformance.py`) and Go (`go test ./...`) validate against the exact same corpus.
- AST-based API manifest generation (`internal/apimanifest`) generates `docs/architecture/v0-12-apgr-go-api-manifest.json`, with automated test gating against unintended signature drift.

### 6. Consumer Qualification Harness (Lane B)

APGR implements an immutable consumer qualification fixture in `testing/fixtures/jaca_consumer`:
- Module: `example.invalid/apgr-jaca-consumer`.
- Implements caller-owned DTO containment wrapping all five domain packages.
- Proves zero subprocess execution (`os/exec`), zero APGR type leaks, and zero reverse dependencies.
- Qualified both in-tree and in isolated out-of-tree temporary workspaces via Go module `replace` directives.
- Production Lane A adoption (`go get`) is deferred to post-release per ICR-004.

## Consequences

- ADR 0058 §4 is superseded regarding the package directory hierarchy (`pkg/*` replaced by top-level packages) and in-process single-phase execution scope.
- `docs/architecture/apg-jaca-integration.md` is updated to reflect top-level Go packages and the absence of a duplicate Go runtime.
- `docs/architecture/v0-12-jaca-disposition-handoff.md` and `docs/architecture/v0-12-jaca-compatibility-report.md` are established as Proposed handoff documentation for JACA team disposition.
- Public release allowlists (`release/public-surface.json`) remain unchanged in V0120-E and are scheduled for formal update in V0120-F.
