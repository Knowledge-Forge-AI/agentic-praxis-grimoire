# JACA Disposition Handoff: §18.13 Ownership Alignment and Go Interfaces (v0.12)

- Status: **Proposed** — APGR-side decision recorded; delivered unaccepted for JACA team disposition
- Target Version: APGR v0.12 / JACA Successor Architecture
- Inspected JACA Baseline: local checkout HEAD `08ca2208805cf446bd15da0a6b4c8c58db737587` (`docs/specs/roadmap/roadmap-orchestration-v1.md` §18.13 quoted verbatim below, plus ADR 0014). Remote `origin/main` was inspected at `20d50433e9e97b0a992110c64fcacb2b3692d666`, and remote dispatcher envelope commit `e1fafd1884e203a94151a3c429cbca6c313c2332` (PR #7) resolves in the git object database. All §18 specifications in `docs/specs/roadmap/` are verified byte-identical across all three commits.
- Governing Decisions: ADR 0058, ADR 0059, ADR 0060, ADR 0061, ADR 0065, ADR 0066

## Status and authority

This document has **no** authority over JACA. It records what APGR has decided on
its own side and what APGR would ask JACA to consider. Nothing here has been
reviewed or accepted by the JACA team, and no statement in it should be read as
JACA having agreed to anything. Every proposed matrix row, interface, and
qualification mode below is declinable in whole or in part.

## Overview

This handoff proposes amendments to the JACA Roadmap Orchestration Implementation Contract (§18.13 Ownership Matrix) that follow from APGR assuming permanent ownership of the lightweight single-phase execution runtime. It describes the boundary APGR proposes between JACA's multi-phase orchestration authority and APGR's single-phase execution runtime, and outlines the public Go package interfaces APGR exports for optional JACA consumption in milestone `V0120-E` (Phase `APG150`, ADR 0066).

---

## 1. §18.13 Ownership Matrix Amendment

In JACA `docs/specs/roadmap/roadmap-orchestration-v1.md` §18.13, the ownership matrix is currently defined as:

```text
| Owner | Owns | Does not own |
| --- | --- | --- |
| JACA | semantic graph; invocation binding; review policy and accounting; route policy/resolution; agenda and recovery; candidate and phase artifacts | provider-local profile meaning; provider CLI implementation; APGR release planning |
| `agent-central` | provider/profile catalogs; profile-to-model/effort/capability data; launchers; CLI normalization; optional raw availability observations | next semantic role; review budget; agenda transition; JACA artifact authority |
| future APGR generic library | only imported artifact/evidence primitives selected by a later decision | orchestration semantics, routing, budgets, providers, agenda, recovery, mutation authority |
| operator | approved roadmap scope; routing constraints; remediation authorization; escalation decisions | implicit model-generated scope expansion |
```

### Proposed Matrix Rows (Delivered Unaccepted for JACA Team Disposition)

Every row below is a **proposal**. Three rows are proposed for rewrite and one is
proposed unchanged; the per-row delta is stated explicitly so that JACA can
disposition each independently rather than inferring the change from the label.

| Owner | Owns | Does not own | Proposed delta |
| --- | --- | --- | --- |
| **JACA** *(Proposed rewrite — narrowing)* | Multi-phase roadmap agenda and cross-phase sequencing; semantic role graph policy; invocation attempt binding; review-budget policy and derived accounting; XO route policy and cross-phase resolution; multi-phase crash recovery; candidate and phase artifact authority; repository mutation fencing. | Provider CLI implementation; model profile compilation; APGR release planning; single-phase internal stage execution mechanics. | **This is not a preserved row.** It qualifies JACA's existing "semantic graph; invocation binding; review policy and accounting; route policy/resolution; agenda and recovery; candidate and phase artifacts" with *multi-phase* / *cross-phase* scoping, and adds "single-phase internal stage execution mechanics" to JACA's does-not-own column. That addition is the substantive ask, and JACA may decline it or scope it differently. It also drops "provider-local profile meaning" from the does-not-own column because that concern moves to the APGR row. |
| **`agent-central`** *(Proposed rewrite)* | Personal workstation developer UX; shell and client configuration; interactive ad-hoc worker supervisor (`bin/agent-worker`, `libexec/agent_workers/`); host credential access. | Single-phase dispatcher runtime; provider/profile catalogs; CLI launchers; CLI normalization; multi-phase agenda. | Removes provider/profile catalogs, launchers, CLI normalization, and raw availability observations from `agent-central`, which move to APGR. Agent-Central's own disposition is tracked separately in `v0-12-agent-central-ownership-transition.md` and is likewise unaccepted. |
| **APGR Phase-Execution Runtime and Library** *(Proposed rewrite — expansion)* | Single-phase execution runtime; process-level stage progression across the semantic roles of ADR 0059 (Planner, Plan Reviewer, Plan Review Disposition, Producer, Work Reviewer, Work Review Disposition, Reviser, Closeout Agent); normalized provider adapters (Codex, Claude, Antigravity); provider/profile catalogs; Request V1/V2 execution; policy-neutral routing ladder and observation digests; public Go domain packages (`phase`, `routing`, `evidence`, `candidate`, `provider`); single-phase SQLite state persistence (`~/.apgr/state/dispatcher.sqlite3`). | Multi-phase roadmap agenda; cross-phase recovery; global review-budget accounting; cross-phase XO route policy; phase-to-phase artifact authority; repository publication. | Replaces the existing "future APGR generic library" row, which today owns "only imported artifact/evidence primitives selected by a later decision". This is the largest proposed expansion and the row JACA should scrutinize first. |
| **Operator** *(Proposed unchanged)* | Approved roadmap scope; routing constraints; remediation authorization; escalation decisions. | Implicit model-generated scope expansion. | Verbatim as currently written; restated only for matrix completeness. |

**Semantic role vocabulary.** APGR's internal stage progression is described using
the ADR 0059 role names, which are aligned to JACA ADR 0014 successor
terminology. Where a single actor currently discharges merged roles (Plan Review
Disposition + Producer; Work Review Disposition + Reviser/Closeout), APGR still
emits distinct semantic records per role, so the roles can later unmerge without
schema reinterpretation. APGR does not use, and does not propose, a bare "Work"
or "Review" role name.

---

## 2. Preservation of JACA Policy Authority

The transfer of the single-phase runtime into APGR adheres strictly to the one-way dependency rule established in ADR 0051, renewed in ADR 0058, and codified in ADR 0066:
- **Zero Inbound Dependencies**: APGR never imports JACA packages, types, or protocols.
- **Zero Subprocess Coupling**: JACA must not shell out to APGR or parse APGR terminal text for canonical state (§18.12). All Go domain interactions occur in-process via compiled Go packages behind caller DTOs.
- **Zero Duplicate Runtime**: APGR does **not** provide a duplicate Go single-phase orchestrator or `ExecutePhase` function for v0.12. Standalone phase execution is owned exclusively by the APGR Python dispatcher runtime, while JACA retains exclusive ownership of its multi-phase XO execution loop.
- **JACA Maintains Complete Policy Ownership**:
  - JACA decides when to invoke a phase and compiles the task prompt (`Prompt Compiler`).
  - JACA controls the total review budget allocation across phases.
  - JACA determines how to interpret phase results and update roadmap items (`Item Dispositioner`).
  - JACA enforces multi-phase repository fencing and commits.
  - JACA resolves XO routing constraints across phases.

---

## 3. Exported Go Package Surfaces for JACA (`V0120-E`)

In milestone `V0120-E` (ADR 0066), APGR exports top-level Go packages suitable for consumption by JACA behind caller-owned DTO containment. All exported packages carry `Experimental` / `Provisional` maturity status for v0.12 under ICR-004 / ICR-005.

### `phase`
Provides core schema definitions, attempt derivation models, execution status constants, semantic role definitions, and routing integration adapters:
```go
package phase

// RequestV2 models the work-only single-phase execution request format.
// Embedded execution_mode, constraints, or runtime routing fields are strictly rejected.
type RequestV2 struct {
    Schema    string `json:"schema"`     // "agent-phase-request-v2"
    PhaseType string `json:"phase_type"` // e.g. "architecture_docs"
    Prompt    string `json:"prompt"`
}

type SemanticRole string
const (
    RolePlanner                 SemanticRole = "Planner"
    RolePlanReviewer            SemanticRole = "Plan Reviewer"
    RolePlanReviewDisposition   SemanticRole = "Plan Review Disposition"
    RoleProducer                SemanticRole = "Producer"
    RoleWorkReviewer            SemanticRole = "Work Reviewer"
    RoleWorkReviewDisposition   SemanticRole = "Work Review Disposition"
    RoleReviser                 SemanticRole = "Reviser"
    RoleCloseoutAgent           SemanticRole = "Closeout Agent"
)

type AttemptIdentity struct {
    AttemptID    string       `json:"attempt_id"`
    PhaseID      string       `json:"phase_id"`
    Role         SemanticRole `json:"role"`
    AttemptIndex int          `json:"attempt_index"`
}

type ActorBinding struct {
    BindingID            string         `json:"binding_id"`
    Roles                []SemanticRole `json:"roles"`
    PolicyName           string         `json:"policy_name"`
    IsMutating           bool           `json:"is_mutating"`
    ProcessReadOnly      bool           `json:"process_read_only"`
    RequiredCapabilities []string       `json:"required_capabilities"`
}

func ParseRequestV2(data []byte) (*RequestV2, error)
func DeriveAttemptIdentity(phaseID string, role SemanticRole, index int) AttemptIdentity
func BuildRouteRequirements(binding ActorBinding, phaseType string, priorResolutions map[string]routing.ResolvedActorRoute) routing.RouteRequirements
func ResolveActorBindingRoute(ctx context.Context, binding ActorBinding, phaseType string, catalog map[string]routing.EndpointCapabilities, observations []routing.OperationalObservation, priorResolutions map[string]routing.ResolvedActorRoute, now float64) (*routing.ResolvedActorRoute, error)
```

> [!IMPORTANT]
> **Rejection of Go `ExecutePhase`**:
> Unlike earlier draft proposals, APGR does **not** provide a Go `ExecutePhase` dispatcher function. Standalone phase execution is provided by the APGR Python dispatcher runtime (`bin/agent-phase-dispatch`), while JACA retains exclusive runtime ownership of its own XO execution loop. JACA consumes APGR's Go domain packages to model requests, validate schemas, resolve routes, and verify artifacts without running duplicate dispatcher machinery.
>
> **Package Coupling Note**: The `phase` package imports `routing` for `BuildRouteRequirements` and `ResolveActorBindingRoute`. Downstream consumers may adopt `routing` independently of `phase`, but adopting `phase` brings in `routing`.

### `routing`
Provides policy-neutral routing ladder resolution and Python-identical canonical observation digests:
```go
package routing

type RouteRequirements struct {
    PhaseType            string   `json:"phase_type"`
    RequiredCapabilities []string `json:"required_capabilities,omitempty"`
    RequiresMutating     bool     `json:"requires_mutating"`
    IsReviewTurn         bool     `json:"is_review_turn"`
    IsProducerTurn       bool     `json:"is_producer_turn"`
    DistinctProviders    []string `json:"distinct_providers,omitempty"`
}

type ResolveRequest struct {
    Requirements        RouteRequirements               `json:"requirements"`
    BindingID           string                          `json:"binding_id"`
    Roles               []string                        `json:"roles,omitempty"`
    CapabilitiesCatalog map[string]EndpointCapabilities `json:"capabilities_catalog"`
    Observations        []OperationalObservation        `json:"observations,omitempty"`
    PriorResolutions    map[string]ResolvedActorRoute   `json:"prior_resolutions,omitempty"`
    Now                 float64                         `json:"now"`
}

type ResolvedActorRoute struct {
    BindingID          string   `json:"binding_id"`
    Provider           string   `json:"provider"`
    Profile            string   `json:"profile"`
    EndpointAlias      string   `json:"endpoint_alias"`
    Capabilities       []string `json:"capabilities"`
    SelectionRationale string   `json:"selection_rationale"`
    Roles              []string `json:"roles,omitempty"`
}

type OperationalObservation struct {
    ObservationID   string         `json:"observation_id"`
    Producer        string         `json:"producer"`
    ObservationType string         `json:"observation_type"`
    Provider        string         `json:"provider"`
    Profile         *string        `json:"profile,omitempty"`
    Timestamp       float64        `json:"timestamp"`
    ExpiresAt       *float64       `json:"expires_at,omitempty"`
    StateValue      string         `json:"state_value"`
    Detail          map[string]any `json:"detail,omitempty"`
    Digest          string         `json:"digest,omitempty"`
}

// Resolve resolves route requirements against candidate options using a pure
// deterministic 6-stage precedence ladder (Explicit override -> Capability fit -> Performance ->
// Cooldown check -> Affinity -> Provider default). JACA retains XO route policy authority.
func Resolve(ctx context.Context, req ResolveRequest) (*ResolvedActorRoute, error)

// CanonicalDigest computes the deterministic SHA-256 digest over the compact,
// key-sorted JSON representation matching the APGR Python runtime oracle.
func CanonicalDigest(obs OperationalObservation) (string, error)
```

### `evidence`
Provides path-traversal-safe review finding structures, review dispositions, and validation receipts:
```go
package evidence

type Severity string
const (
    SeverityBlocking    Severity = "blocking"
    SeveritySubstantive Severity = "substantive"
    SeverityAdvisory    Severity = "advisory"
)

type Category string
const (
    CategoryCorrectness       Category = "correctness"
    CategoryContractViolation Category = "contract_violation"
    CategorySecurity          Category = "security"
    CategoryScope             Category = "scope"
    CategoryEvidence          Category = "evidence"
    CategoryClarity           Category = "clarity"
)

type ReviewFinding struct {
    FindingID string   `json:"finding_id"`
    Severity  Severity `json:"severity"`
    Category  Category `json:"category"`
    Summary   string   `json:"summary"`
    FilePath  string   `json:"file_path,omitempty"`
    LineStart int      `json:"line_start,omitempty"`
    LineEnd   int      `json:"line_end,omitempty"`
}

type DispositionAction string
const (
    DispositionAccept DispositionAction = "accept"
    DispositionAmend  DispositionAction = "amend"
    DispositionReject DispositionAction = "reject"
    DispositionDefer  DispositionAction = "defer"
)

type DispositionBasis string
const (
    BasisAcceptedAuthority DispositionBasis = "accepted_authority"
    BasisCanonicalEvidence DispositionBasis = "canonical_evidence"
    BasisScopeOwner        DispositionBasis = "scope_owner"
    BasisNone              DispositionBasis = "none"
)

type FindingDisposition struct {
    FindingID string            `json:"finding_id"`
    Action    DispositionAction `json:"action"`
    Basis     DispositionBasis  `json:"basis"`
    Rationale string            `json:"rationale"`
}

type ValidationReceipt struct {
    ReceiptID      string `json:"receipt_id"`
    RunID          string `json:"run_id"`
    PhaseID        string `json:"phase_id"`
    CompletedAt    string `json:"completed_at"`
    TerminalStatus string `json:"terminal_status"`
    ArchiveSHA256  string `json:"archive_sha256"`
}

func ValidateFinding(f ReviewFinding) error
func ValidateDisposition(d FindingDisposition) error
func ValidateReceipt(r ValidationReceipt) error
```

### `candidate`
Models immutable candidate identity and artifact manifests with strict path traversal rejection:
```go
package candidate

type CandidateIdentity struct {
    CandidateID       string  `json:"candidate_id"`
    Generation        int     `json:"generation"`
    ProducerRole      string  `json:"producer_role"`
    ProducerAttemptID string  `json:"producer_attempt_id"`
    PredecessorID     *string `json:"predecessor_id,omitempty"`
    Commit            string  `json:"commit,omitempty"`
    TreeDigest        string  `json:"tree_digest,omitempty"`
    ExpectedBase      string  `json:"expected_base,omitempty"`
}

type Artifact struct {
    ArtifactID   string `json:"artifact_id"`
    RunID        string `json:"run_id"`
    PhaseID      string `json:"phase_id"`
    RelativePath string `json:"relative_path"`
    MediaType    string `json:"media_type"`
    ByteSize     int64  `json:"byte_size"`
    SHA256       string `json:"sha256"`
}

type ArtifactManifest struct {
    Schema    string     `json:"schema"` // "agent-phase-artifact-manifest-v1"
    ProjectID string     `json:"project_id"`
    PhaseID   string     `json:"phase_id"`
    Artifacts []Artifact `json:"artifacts"`
}

func ValidateCandidate(c CandidateIdentity) error
func ValidateArtifact(a Artifact) error
func ValidateArtifactManifest(m ArtifactManifest) error
```

### `provider`
Provides access to normalized provider capability metadata across Codex, Claude, and Antigravity:
```go
package provider

type ConformanceRow struct {
    FeatureID     string `json:"feature_id"`
    Area          string `json:"area"`
    Requirement   string `json:"requirement"`
    Codex         string `json:"codex"`
    Claude        string `json:"claude"`
    Antigravity   string `json:"antigravity"`
    UnifiedStatus string `json:"unified_status"`
    Notes         string `json:"notes,omitempty"`
}

type ConformanceMatrix struct {
    Schema      string           `json:"schema"`
    GeneratedAt string           `json:"generated_at"`
    Providers   []string         `json:"providers"`
    Rows        []ConformanceRow `json:"rows"`
}

func LoadConformanceMatrix(data []byte) (*ConformanceMatrix, error)
func ValidateConformanceMatrix(matrix *ConformanceMatrix) error
```

---

## 4. Qualification Modes and Consumer Harness

APGR qualifies its Go surfaces under the following two integration lanes:

### Lane B: Pre-Release Consumer Harness (Qualified in `V0120-E`)
- Location: `testing/fixtures/jaca_consumer/` (module `example.invalid/apgr-jaca-consumer`).
- Architecture: Caller-owned DTO containment (`CallerPhaseRequest`, `CallerRouteSelection`, `CallerCandidateSummary`, `CallerReviewDisposition`).
- Invariant: Zero `os/exec` subprocess execution, zero APGR type leaks across boundary, zero imports of JACA packages in APGR.
- Qualification: Verified via `go test -v ./testing/fixtures/jaca_consumer/...` and verified in isolated temporary directories using Go module `replace` directives.

### Lane A: Post-Release Public Go Proxy (Deferred per ICR-004)
- Formal JACA adoption of a published semantic version (`go get github.com/Knowledge-Forge-AI/agentic-praxis-grimoire@v0.12.0`) is deferred until after public v0.12 release and JACA-team disposition.

### Zero Subprocess Coupling (§18.12)
The JACA contract at the inspected baseline states that JACA "must not shell out to APGR or parse its terminal prose for canonical state". This handoff reinforces that constraint: APGR provides structured in-process Go library packages to prevent any need for terminal prose scraping or subprocess invocation.
