# JACA Compatibility and Adoption Report: APGR v0.12 Go Domain Surfaces

- Status: **Informational / Proposed Handoff**
- Target: Joint Agentic Command Aegis (JACA) XO Runtime Integration
- Phase: `APG150` (Milestone `V0120-E`, ADR 0066, Exit 00196)
- APGR Module: `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire`
- APGR Release Candidate: v0.12.0
- Inspected JACA Baselines:
  - Local checkout HEAD: `08ca2208805cf446bd15da0a6b4c8c58db737587`
  - Remote `origin/main`: `20d50433e9e97b0a992110c64fcacb2b3692d666`
  - Dispatcher envelope commit: `e1fafd1884e203a94151a3c429cbca6c313c2332` (PR #7)
  - Integrity Check: JACA repository was inspected strictly read-only; zero mutation. All §18 specifications in `docs/specs/roadmap/roadmap-orchestration-v1.md` are byte-identical across all three commits.

---

## 1. Executive Summary

Milestone **V0120-E** introduces five public, reusable Go domain packages in APGR:
1. `phase`: Single-phase request modeling (work-only Request V2), attempt identity derivation, phase execution status, semantic role constants, and route requirement adapters.
2. `routing`: Pure deterministic 6-stage routing ladder and byte-identical canonical telemetry observation digest calculation.
3. `evidence`: Path-traversal-safe review finding structures, finding dispositions, and validation receipts.
4. `candidate`: Immutable candidate workspace identity and artifact manifest specifications with path traversal rejection.
5. `provider`: Static provider conformance matrix validating 22 rows across Codex, Claude, and Antigravity models.

All five packages carry `Experimental` / `Provisional` maturity status for APGR v0.12 under ICR-004 and ICR-005. They are designed for optional, decoupled adoption by JACA's Execution Orchestration (XO) runtime. Note that `phase` imports `routing` for route binding adapters; `routing` may be adopted independently, while `phase` brings in `routing`.

---

## 2. JACA Roadmap Orchestration (§18) Successor Mapping

The exported Go packages directly model the data structures and pure algorithmic requirements established in JACA's Roadmap Orchestration Specification (`docs/specs/roadmap/roadmap-orchestration-v1.md` §18):

| JACA §18 Specification | JACA Concept | APGR v0.12 Exported Go Type / Function | Mapping & Adoption Guidance |
| --- | --- | --- | --- |
| **§18.4** Semantic Roles | Actor roles across stage progression | `phase.SemanticRole`<br>`phase.RolePlanner`, `phase.RoleProducer`, etc. | 1:1 mapping to JACA ADR 0014 terminology (8 canonical roles). Prevents stringly-typed role divergence across boundaries. |
| **§18.5** Launch Envelope | Task request specification | `phase.RequestV2`<br>`phase.ParseRequestV2` | Request V2 strictly limits input to work fields (`schema`, `phase_type`, `prompt`); strictly rejects `execution_mode`, `constraints`, and unknown fields. Request V1 is not exported in Go. |
| **§18.6** Invocation Binding | Attempt derivation and identity | `phase.AttemptIdentity`<br>`phase.DeriveAttemptIdentity` | Pure deterministic ID derivation (`att-<phase>-<role>-<index>`). Safe for concurrent execution. |
| **§18.7** Route Selection | 6-stage precedence ladder | `routing.Resolve`<br>`routing.RouteRequirements`<br>`routing.ResolveRequest`<br>`routing.ResolvedActorRoute` | Pure deterministic ladder (Explicit -> Capability -> Performance -> Cooldown -> Affinity -> Default). Policy-neutral: JACA supplies requirements and candidate sets. |
| **§18.7** Observation Digest | Route telemetry hashing | `routing.CanonicalDigest`<br>`routing.OperationalObservation` | SHA-256 canonical digest over telemetry observations, bit-for-bit identical with APGR Python implementation. |
| **§18.8** Review Findings | Finding records and severities | `evidence.ReviewFinding`<br>`evidence.Severity`<br>`evidence.ValidateFinding` | Validates closed severity enums (`blocking`, `substantive`, `advisory`), categories, non-empty summary, and rejects path traversal in file paths. |
| **§18.8** Review Dispositions | Stage finding dispositions | `evidence.FindingDisposition`<br>`evidence.ValidateDisposition` | Validates action enums (`accept`, `amend`, `reject`, `defer`), disposition basis (`accepted_authority`, `canonical_evidence`, `scope_owner`, `none`), and required rationale. |
| **§18.9** Gate Verification | Validation receipts | `evidence.ValidationReceipt`<br>`evidence.ValidateReceipt` | Structured verification receipts for terminal phase archive records (`receipt_id`, `run_id`, `phase_id`, `completed_at`, `terminal_status`, `archive_sha256`). |
| **§18.10** Candidate Workspace | Proposed workspace identity | `candidate.CandidateIdentity`<br>`candidate.ValidateCandidate` | Immutable candidate record tracking commit, tree digest, base, generation, and producer attempt. |
| **§18.10** Artifact Manifest | Emitted phase artifacts | `candidate.ArtifactManifest`<br>`candidate.Artifact`<br>`candidate.ValidateArtifact` | Strict path traversal rejection (`../`, `/absolute`, `\`), non-negative sizes, and lowercase hex SHA-256 validation. |
| **§18.11** Provider Capabilities | Provider/model capabilities | `provider.ConformanceMatrix`<br>`provider.ConformanceRow`<br>`provider.LoadConformanceMatrix`<br>`provider.ValidateConformanceMatrix` | Machine-readable matrix of 22 evaluated rows across Codex, Claude, and Antigravity models. Pure inspection; zero subprocess execution. |

---

## 3. Strict Boundary and Non-Goals

### Rejection of Go `ExecutePhase` Duplicate Runtime
Earlier draft handoffs contemplated an in-process Go dispatcher entrypoint (`ExecutePhase`). Under ADR 0066 and review disposition:
- **Decision**: APGR does **not** implement a duplicate Go dispatcher runtime for v0.12.
- **Rationale**: Standalone execution runtime is owned by the Python dispatcher runtime (`bin/agent-phase-dispatch`). JACA owns its own XO execution loop. Providing duplicate dispatcher execution in Go would create divergent subprocess execution, pipe monitoring, and signal handling loops.
- **Boundary**: APGR Go packages provide pure data models, serialization schemas, and deterministic validation algorithms. JACA's XO loop executes and manages provider processes under its own authority.

### Strict Request V2 Work-Only Contract
Request V2 in `phase.RequestV2` strictly enforces work-only parameters (`schema`, `phase_type`, `prompt`).
- Runtime fields such as `execution_mode`, `constraints`, or embedded provider overrides are rejected by schema validation.
- JACA's XO runtime owns route resolution and execution mode selection; it does not embed runtime commands in work request payloads.

### Subprocess Decoupling (§18.12)
JACA §18.12 explicitly mandates that JACA "must not shell out to APGR or parse its terminal prose for canonical state".
- The exported Go packages enable direct in-process interaction via strongly-typed Go structures.
- Terminal output parsing, regex scraping of stdout/stderr, and subprocess invocations are completely unnecessary and forbidden.

### One-Way Dependency Invariant
- APGR never imports JACA packages or references JACA-internal protocols.
- JACA imports APGR packages behind caller-owned DTO containment.

---

## 4. Consumer Qualification Evidence (Lane B)

To prove consumer qualification without creating premature production coupling, APGR constructed and verified a complete consumer qualification fixture in `testing/fixtures/jaca_consumer/`:

- **Module Identity**: `example.invalid/apgr-jaca-consumer`
- **Adapter Implementation**: `testing/fixtures/jaca_consumer/adapter.go`
  - Defines caller-owned DTOs (`CallerPhaseRequest`, `CallerRouteSelection`, `CallerCandidateSummary`, `CallerReviewDisposition`).
  - Wraps APGR Go packages (`phase`, `routing`, `evidence`, `candidate`, `provider`).
  - Contains **zero** calls to `os/exec`.
  - Leaks **zero** APGR types out of adapter boundaries.
- **Verification Suites**: `testing/fixtures/jaca_consumer/adapter_test.go`
  - In-tree test: `go test -v ./testing/fixtures/jaca_consumer/...` (PASSED).
  - Isolated out-of-tree test: Executed in temporary directory with isolated `go.mod` using `replace github.com/Knowledge-Forge-AI/agentic-praxis-grimoire => /path/to/candidate` (PASSED).
  - Demonstrates flawless compilation and runtime behavior under standard Go toolchain (Go 1.25).

---

## 5. Adoption Roadmap for JACA Team (Lane A)

1. **Pre-Release Review**:
   - Inspect this compatibility report and `docs/architecture/v0-12-jaca-disposition-handoff.md`.
   - Review proposed §18.13 ownership matrix modifications.
2. **Post-Release Adoption (Lane A)**:
   - Upon publication of APGR `v0.12.0` on GitHub Releases and proxy.golang.org:
     ```sh
     go get github.com/Knowledge-Forge-AI/agentic-praxis-grimoire@v0.12.0
     ```
   - Implement JACA internal adapter in `xo/src/main/go` following the pattern demonstrated in `testing/fixtures/jaca_consumer/adapter.go`.
   - Update JACA roadmap orchestration tests to validate against released APGR Go types.
