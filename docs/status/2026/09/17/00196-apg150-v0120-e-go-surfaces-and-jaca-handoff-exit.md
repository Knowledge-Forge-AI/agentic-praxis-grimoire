# APG150 — APGR V0120-E — Public Go Domain Surfaces and JACA XO Qualification Handoff Exit

Phase ID: `APG150`
Exit ID: `Exit 00196`

## Status

Disposition: **advance**. Exit 00196 records the successful completion of Milestone V0120-E, exporting public Go domain packages, establishing cross-language conformance fixtures and verification, qualifying a disposable consumer harness for Joint Agentic Command Aegis (JACA) Execution Orchestration (XO), establishing ADR 0066, and delivering the updated Proposed JACA disposition handoff and compatibility report.
Outcome: `V0120_E_GO_SURFACES_AND_JACA_HANDOFF_COMPLETE`

## Accomplishments

### 1. Public Go Domain Packages
APGR implemented five additive, top-level Go packages under module `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire`:
- `phase`: Immutable work-only Request V2 envelope (strictly rejecting embedded `execution_mode`, `constraints`, or runtime routing fields), attempt identity derivation (`att-<phase>-<role>-<index>`), phase status constants, semantic role constants aligned with JACA ADR 0014 and APGR ADR 0059, and routing integration adapters.
- `routing`: Pure deterministic 6-stage routing resolution ladder (`Resolve`) and canonical telemetry observation digest calculation (`CanonicalDigest`), achieving bit-for-bit identical SHA-256 output with the Python implementation. Policy-neutral: JACA retains XO route policy authority.
- `evidence`: Path-traversal-safe review finding structures (`ReviewFinding`), finding dispositions (`FindingDisposition`), and validation receipts (`ValidationReceipt`).
- `candidate`: Immutable candidate workspace identities (`CandidateIdentity`), artifact specifications (`Artifact`), and artifact manifests (`ArtifactManifest`) with strict path traversal rejection (`../`, `/`, `\`).
- `provider`: Static provider conformance matrix (`ConformanceMatrix`) validating 22 capability dimensions across Codex, Claude, and Antigravity models.

All five packages carry **Experimental / Provisional** maturity status for APGR v0.12 under ICR-004 / ICR-005. Note that `phase` imports `routing` for route binding adapters; `routing` may be adopted independently, while `phase` brings in `routing`.

### 2. Zero Duplicate Runtime & Subprocess Decoupling
- **Rejection of Duplicate Go Runtime**: Under ADR 0066, APGR explicitly rejected an in-process Go dispatcher entrypoint (`ExecutePhase`). Standalone phase execution is owned exclusively by the Python dispatcher runtime (`bin/agent-phase-dispatch`). JACA retains exclusive ownership of its multi-phase Execution Orchestration (XO) runtime.
- **Zero Subprocess Coupling**: Eliminates subprocess coupling per JACA §18.12 ("must not shell out to APGR or parse its terminal prose for canonical state"). JACA communicates with APGR Go domain structures directly in-process behind caller DTOs.
- **Strict One-Way Dependency**: APGR never imports JACA packages or references JACA-internal protocols.

### 3. Cross-Language Conformance Harness
- Generated a canonical golden vector corpus in `testing/fixtures/conformance/`:
  - `request_v2_vectors.json`
  - `semantic_roles_vectors.json`
  - `observation_digest_vectors.json`
  - `dynamic_routing_scenarios.json`
  - `evidence_review_vectors.json`
  - `candidate_artifact_vectors.json`
  - `provider_conformance_vectors.json`
- Created generator tool `tools/conformance/generate_conformance_corpus.py` supporting `--check` and `--generate` modes.
- Verified test agreement across languages:
  - Python: `src/test/dispatcher/test_cross_language_conformance.py` (5/5 passed).
  - Go: `go test -v ./...` and `go vet ./...` (100% green).

### 4. AST-Based API Manifest & Drift Gate
- Built `internal/apimanifest/manifest.go` to inspect Go ASTs and emit a canonical JSON surface manifest: `docs/architecture/v0-12-apgr-go-api-manifest.json`.
- Gated via `internal/apimanifest/manifest_test.go` to fail on any uncommitted signature changes, protecting downstream consumers from silent API drift.

### 5. JACA XO Consumer Qualification (Lane B)
- Implemented caller-owned qualification fixture in `testing/fixtures/jaca_consumer/` (`example.invalid/apgr-jaca-consumer`).
- Designed DTO containment adapter (`adapter.go`) demonstrating caller-owned types (`CallerPhaseRequest`, `CallerRouteSelection`, `CallerCandidateSummary`, `CallerReviewDisposition`) wrapping APGR Go packages with zero `os/exec` calls and zero APGR type leaks.
- Verified in-tree via `go test -v ./testing/fixtures/jaca_consumer/...` and verified out-of-tree in an isolated temporary directory via module `replace` directives.
- Production Lane A adoption (`go get`) is deferred to post-release per ICR-004.

### 6. Read-Only JACA Inspection & Alignment
- Inspected local checkout HEAD `08ca2208805cf446bd15da0a6b4c8c58db737587`, remote origin/main `20d50433e9e97b0a992110c64fcacb2b3692d666`, and remote PR #7 `e1fafd1884e203a94151a3c429cbca6c313c2332`.
- Confirmed JACA repository was maintained strictly read-only (zero commits, zero mutations).
- Confirmed all §18 specifications in `docs/specs/roadmap/` are byte-identical across all three commits.

### 7. Governance and Documentation Delivered
- Established ADR 0066 (`docs/adr/2026/09/0066-apgr-public-go-surfaces-and-jaca-xo-boundary.md`).
- Amended ADR 0058 with forward pointer to ADR 0066 superseding `pkg/*` path naming and in-process execution scope.
- Updated `docs/architecture/apg-jaca-integration.md` and `docs/reference/go-library.md`.
- Updated `docs/architecture/v0-12-jaca-disposition-handoff.md` (Proposed status for JACA team disposition).
- Created `docs/architecture/v0-12-jaca-compatibility-report.md`.
- Updated `docs/adr/README.md` and `docs/status/README.md`.
- Next milestone: **V0120-F** (Release Hardening, Conditional Nixpkgs, and Integrated Readiness).
