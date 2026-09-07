# APGR v0.9 Roadmap and Cross-Release Backlog Disposition

## 1. Authority and Current State

This roadmap defines the canonical work and dependency ordering for the
**Agentic Praxis Grimoire (APGR) v0.9 development program**.

### 1.1 Development Baseline
- **Release Status**: **v0.9 is active development, NOT a published release.**
  Current runtime version strings remain authoritative until a future explicit
  release phase; no new version tags or public releases are manufactured here.
- **Historical entry phase**: APG110 CI qualification conformance and JACA CI handoff.
- **Integrated Qualification Supersession**: For integrated source qualification,
  the entry development baseline (`apg110`) and intermediate defect/remediation stages
  (`apg111`, `apg112`, and `apg113`) have been superseded by phase APG114
  (`9e853c9 APG114: Qualify integrated CI and XO source with bound evidence`),
  which completed and established integrated CI summary and XO consumer fixture
  qualification on Darwin arm64 under exit record `00159`. All historical
  evidence manifests, producer runs, and intermediate receipts remain preserved
  as dated evidence without rewriting prior authority records.
- **Immutable Published Baseline**: The v0.8.1 product is published and frozen:
  - Public Git commit: `565f924aa8fda9551da8732cceb5708db069e127`
  - Public Git tree: `1ec7a01ca252a63cc869caf4e5bbe152fb6d2868`
  - Annotated tag: `b6b3e996536ac89e1a58912caf3b3cb9c251dbd7`

### 1.2 Operator Priority Order
Per operator direction, the roadmap priority order across consumers is:
1. **JACA CI**: CI-first qualification interface and deterministic evidence.
2. **JACA XO**: JACA XO consumption and Go package compatibility.
3. **Theme Forge**: Measured, reusable frontend and web capability profiles.
4. **Repo Map**: Graph-quality profiles, versioned protocols, and migration guidance.

### 1.3 Preserved Invariants and Integrity Rules
- **Historical Discovery Invariant**: Preserves the 9,527-byte discovery integrity
  control limit without compression tricks, artificial truncation, or raising the ceiling.
- **Canonical Skill Count**: Retains the 39 canonical skill leaves (14 stable / 25 provisional).
  **Zero new skill candidates are selected for the v0.9 foundation.**
- **Go Library Boundary**: Retains the six public Go packages (`schema`, `report`,
  `skills`, `envsnap`, `hotspot`, `footprint`) with one-way consumer dependency rules.
- **Packaging Integrity Obligations**: Preserves all permanent packaging regression
  obligations (Python wheel `METADATA`, prepared metadata, sdist `PKG-INFO` descriptions,
  four npm package `README.md` files, and Go package documentation). Packaging code
  remains untouched in this foundation phase.

---

## 2. Release Themes Across Candidate Milestones

### 2.1 v0.9 Active Development Line — CI-First & JACA XO
- **Theme**: CI-First qualification interface and JACA XO adapter compatibility.
- **Foundation Deliverable**: `APGR-CI-QUAL` — APGR-owned machine-readable validation
  interface emitting strict 6-field summary evidence (version 1 format: `version`,
  `subproject`, `suite`, `test_status`, `gate_status`, `source_commit`),
  exact Git commit binding of HEAD at execution time, a closed validation role taxonomy
  (`policy`, `unit`, `integration`, `unit-integration`, with `apg-dev-gate` as JACA's
  consumer role alias for `unit-integration`), deterministic JACA CI conformance fixtures,
  and a complete JACA CI handoff specification. Integrated source qualification
  is completed and verified on Darwin arm64 under phase APG114 (Exit `00159`), satisfying
  all canonical CI gates (policy clean, unit 85.87%/80.49%, integration 85.77%/80.01%,
  combined 90.38%/86.78%). Downstream runner registration in JACA CI (`tools/ci/evidence.go`)
  is consumer-owned and remains pending.
  *(Note: `--summary-file` and the `policy` role are active v0.9 development-checkout
  capabilities, not available in the frozen v0.8.1 release).*
- **XO Compatibility**: `APGR-XO-COMPAT` — Verify clean Go package consumption
  behind JACA's internal adapter. **Integrated Source Qualified** via caller-owned adapter fixture
  `testing/fixtures/xo_consumer/` with bounded static AST inspection verifying zero APGR type leaks,
  static dependency checks verifying absence of `os/exec` and internal/cmd/JACA imports, and
  in-memory smoke execution across dual lanes (Released v0.8.1 and Development Candidate) qualified
  in the integrated source checkout under phase APG114. Downstream JACA XO adoption (`xo/src/main/go`)
  is consumer-owned and remains pending.

### 2.2 v0.10 Candidate — Reusable Theme Forge Support
- **Theme**: Measured reusable Theme Forge domain profiles.
- **Prerequisite Gate**: Formal Capacity Decision Record (`APGR-CAP1`) establishing
  a grounded accounting model separating global discovery limits from task-scoped
  materialized bundle limits.
- **Candidate Skill Scope**: Re-evaluate and cost six Theme Forge candidate surfaces:
  - SVG language profile (`svg-language-profile`)
  - Playwright testing profile (`playwright-test-profile`)
  - Web accessibility profile (`web-accessibility-profile`)
  - Browser runtime profile (`browser-runtime-profile`)
  - npm package manager profile (`npm-package-manager-profile`)
  - Vite build profile (`vite-build-profile`)
- **Anti-Pattern Guard**: No bundling of all candidates into a single release; each
  skill must independently pass mechanical and semantic validation.

### 2.3 v0.11 Candidate — Repo Map Graph-Quality and Protocol Guidance
- **Theme**: Grounded graph-quality, versioned protocol, and migration guidance.
- **Evidence Baseline**: Draw on RepoMap's completed JACA CI pilot
  (`jaca/ci`: `docs/specs/ci-cd/repo-map-pilot.md`)
  as reusable onboarding evidence, and await RepoMap ADR 0056/0057 protocol freezes.
- **Candidate Scope**:
  - Knowledge graph quality profile (`knowledge-graph-quality-profile`)
  - Versioned protocol profile (`versioned-protocol-profile`)
  - System implementation migration evaluation (`migrating-system-implementations`)
- **Prerequisites**: Demonstration that existing process skills do not already cover
  migration needs, and empirical multi-source graph evidence.

---

## 3. Comprehensive Backlog Crosswalk

Proposal references below preserve the previously dispositioned v0.9 planning
corpus and backlog decisions. Exact private source bindings remain historical
evidence; this public roadmap identifies their semantic scope.

| Stable ID | Source Path & Revision / Clause | Disposition | Consumer & Priority | APGR Owner vs Consumer Owner | Reusable Gap | Dependency | Bounded Deliverable | Acceptance Test | Compatibility Impact | Relative Size/Risk | Release Allocation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `APGR-CI-QUAL` | `jaca/ci`: `docs/adr/2026/08/0008-ci-cd-platform-topology-and-boundary-contracts.md`, §CI-CD; APGR ICR-003 | **Integrated Source Qualified (JACA CI Registration Pending)** | JACA CI (Priority 1) | APGR owns test entry points & summary; JACA owns pipeline runner | Machine-readable qualification interface with exact commit binding | Existing `apg-test` runner, git rev-parse | `--summary-file` CLI option emitting strict 6-field JACA summary; `policy` role | `src/test/unit/.../apg_test.unit.test.py` and `src/test/int/.../apg-test.int.test.py` | Non-breaking additive CLI options | Small / Low | **v0.9 (Current Slice)** |
| `APGR-XO-COMPAT` | Planning request: `RESPONSE-AND-AMENDED-JACA-APGR-INTEGRATION-AND-CONTEXT-ECONOMY-DISPOSITION-PROPOSAL--20260827 (1).md` (PU-APGR-JACA); ICR-001..006 | **Integrated Source Qualified (JACA Adoption Pending)** | JACA XO (Priority 2) | APGR owns Go package models; JACA owns adapter & execution | Verify Go package imports (`skills`, `footprint`) behind JACA-owned adapter | Released module or local replacement in conformance tests | Caller-owned adapter fixture verifying AST zero-type-leak, zero-subprocess, zero internal/cmd imports, and dual-lane execution | `testing/fixtures/xo_consumer/adapter_test.go` | Observed dual-lane conformance with v0.8.1 | Small / Low | **v0.9 (Current Slice)** |
| `APGR-CAP1` | Planning request: `RESPONSE-AND-AMENDED-APGR-CONSOLIDATED-DISPOSITION-PROPOSAL--20260827.md` (PU-APGR-CAP; CAP0 §3.2); `APG-THEME-FORGE-SKILL-INVENTORY-EXPANSION-PROPOSAL.md` §2; `APG-REPOMAP-REFACTOR-TEAM-DISPOSITION-PROPOSAL.md` §5 | **Deferred** | Cross-consumer (Priority 3/4) | APGR governance | Decide discovery vs bundle capacity model before adding skills | Real routing measurement; preserve 9,527-byte invariant | Formal capacity decision record (ADR) | Capacity and discovery byte accounting tests | No mutation in v0.9 foundation | Medium / Medium | v0.10 Candidate |
| `SKILL-SVG` | Planning request: `APG-THEME-FORGE-SKILL-INVENTORY-EXPANSION-PROPOSAL.md` §1, Item 1 | **Deferred** | Theme Forge (Priority 3) | APGR reusable domain | SVG syntax, viewBox, coordinates, path semantics, transforms | CAP1 capacity gate, TF evidence | Bounded `svg-language-profile` skill leaf | Skill library mechanical tests & positive/negative fixtures | Additive provisional skill | Medium / Low | v0.10 Candidate |
| `SKILL-PLAYWRIGHT` | Planning request: `APG-THEME-FORGE-SKILL-INVENTORY-EXPANSION-PROPOSAL.md` §1, Item 2 | **Deferred** | Theme Forge (Priority 3) | APGR reusable domain | Playwright test fixtures, selectors, page objects, assertions | CAP1 capacity gate, browser runtime contract | Bounded `playwright-test-profile` skill leaf | Skill library mechanical tests & positive/negative fixtures | Additive provisional skill | Medium / Low | v0.10 Candidate |
| `SKILL-A11Y` | Planning request: `APG-THEME-FORGE-SKILL-INVENTORY-EXPANSION-PROPOSAL.md` §1, Item 3 | **Deferred** | Theme Forge (Priority 3) | APGR reusable domain | WAI-ARIA, accessibility trees, keyboard navigation, contrast | CAP1 capacity gate | Bounded `web-accessibility-profile` skill leaf | Skill library mechanical tests & positive/negative fixtures | Additive provisional skill | Medium / Low | v0.10 Candidate |
| `SKILL-BROWSER` | Planning request: `APG-THEME-FORGE-SKILL-INVENTORY-EXPANSION-PROPOSAL.md` §1, Item 4 | **Deferred** | Theme Forge (Priority 3) | APGR reusable domain | Browser runtime, DOM events, Web APIs, storage, workers | CAP1 capacity gate | Bounded `browser-runtime-profile` skill leaf | Skill library mechanical tests & positive/negative fixtures | Additive provisional skill | Medium / Medium | v0.10 Candidate |
| `SKILL-NPM-PKG` | Planning request: `APG-THEME-FORGE-SKILL-INVENTORY-EXPANSION-PROPOSAL.md` §1, Item 5 | **Deferred** | Theme Forge (Priority 3) | APGR reusable domain | npm/pnpm workspaces, exports maps, lockfiles, publishing | CAP1 capacity gate | Bounded `npm-package-manager-profile` skill leaf | Skill library mechanical tests & positive/negative fixtures | Additive provisional skill | Medium / Low | v0.10 Candidate |
| `SKILL-VITE` | Planning request: `APG-THEME-FORGE-SKILL-INVENTORY-EXPANSION-PROPOSAL.md` §1, Item 6 | **Deferred** | Theme Forge (Priority 3) | APGR reusable domain | Vite configuration, plugins, SSR, transforms, bundling | CAP1 capacity gate | Bounded `vite-build-profile` skill leaf | Skill library mechanical tests & positive/negative fixtures | Additive provisional skill | Medium / Low | v0.10 Candidate |
| `SKILL-KG-QUALITY` | Planning request: `APG-REPOMAP-REFACTOR-TEAM-DISPOSITION-PROPOSAL.md` §1, APG-D3; `repo-map`: `docs/adr/0056-semantic-subgraphs-and-materialization.md` (not found at cited path in the inspected Repo Map development source; actual inspected ADRs are `docs/adr/2026/08/0056-reconciled-investigation-and-program-direction.md` and `docs/adr/2026/08/0057-cloud-first-multi-source-architecture-reconciliation.md`) | **Deferred** | Repo Map (Priority 4) | APGR reusable domain | Graph identity, provenance, claim strength, multi-source resolution | CAP1 capacity gate, RM multi-source data | Bounded `knowledge-graph-quality-profile` skill leaf | Skill library mechanical tests & positive/negative fixtures | Additive provisional skill | Medium / Medium | v0.11 Candidate |
| `SKILL-VER-PROTO` | Planning request: `APG-REPOMAP-REFACTOR-TEAM-DISPOSITION-PROPOSAL.md` §1, APG-D4; ICR-001 | **Deferred** | Repo Map (Priority 4) | APGR reusable domain | Semantic vs wire contracts, framing, compatibility, error envelopes | CAP1 capacity gate, RM protocol freeze | Bounded `versioned-protocol-profile` skill leaf | Skill library mechanical tests & positive/negative fixtures | Additive provisional skill | Medium / Medium | v0.11 Candidate |
| `SKILL-MIGRATION` | Planning request: `APG-REPOMAP-REFACTOR-TEAM-DISPOSITION-PROPOSAL.md` §1, APG-D5 | **Deferred (Needs Evidence)** | Repo Map (Priority 4) | APGR reusable domain | Systematic codebase migration; potential generalization of bash-to-python | Proof that existing process skills leave a demonstrable gap | Ownership analysis document & potential skill revision | Overlap analysis against existing process skills | Potential supersession of existing skill | Medium / High | v0.11 Candidate |
| `APGR-CXT2B` | Planning request: `APG-V0.8.0-CAVEMAN-CONTEXT-ECONOMY-EXPLORATION--20260822.md` §5.2; PU-APGR-CAP | **Deferred** | Diagnostic consumers | APGR diagnostic adapter | Optional Caveman format importer | Pinned format version, fail-closed mapping, JACA disposition | Optional adapter module in separate package | Fixture decoding & refusal tests | Isolated non-core package | Low / Low | Post-v0.11 / Future |

---

## 4. First Implementation Slice: APGR CI Qualification Interface (Integrated Source Qualified / JACA Registration Pending)

### 4.1 Implemented Deliverables
1. **Validation Role Taxonomy**:
   - `policy`: Fast (<1.5s warm cache, ~5–15s cold cache estimated, with 120s timeout bound)
     mechanical validation executing repository inventory verification (`validate_inventory`),
     toolchain dependency version verification (`dependency_versions`), skill library mechanical
     checks and Go embedded corpus integrity (`apg_skill_library_check.check_library` and
     `_embedded_corpus_failure`), and record/phase identity (`apg_record_identity.check_records`).
     Qualified on Darwin arm64; Linux x86_64 marked pending runner qualification.
   - `unit`: Python unit testing with exact 80/80 statement and branch coverage gates.
     Qualified on Darwin arm64; Linux x86_64 blocked by whole-inventory preflight pinning Darwin arm64 runtimes.
   - `integration`: Python integration testing with exact 80/80 statement and branch coverage gates.
     Qualified on Darwin arm64; Linux x86_64 blocked by whole-inventory preflight pinning Darwin arm64 runtimes.
   - `unit-integration` (`combined`): Combined union gate requiring 85/85 statement and branch coverage.
     Qualified on Darwin arm64; Linux x86_64 blocked by whole-inventory preflight pinning Darwin arm64 runtimes.
2. **Machine-Readable Summary**: Added `--summary-file <path>` CLI option to `libexec/apg_test.py`
   (invoked canonically via `apgr test ...` and legacy wrapper `bin/apg-test`). Emits strict
   6-field JACA-compatible evidence JSON (`version`, `subproject`, `suite`, `test_status`,
   `gate_status`, `source_commit`).
3. **JACA CI Conformance Fixtures**: Added maintained APGR-local illustrative fixtures under
   `testing/fixtures/jaca_ci/`
   (schema `apgr-ci-illustrative-fixture-v1`) modeling valid PR qualification, invalid
   role selection, drift detection, and sample outputs.
4. **Handoff Specification**: Created `docs/architecture/jaca-ci-handoff.md`
   following Section 2 of the JACA Project Onboarding Contract.
5. **Qualification Status and Consumer Handoff**: APGR-local qualification conformance
   is completed and verified on Darwin arm64. Downstream runner registration in JACA CI
   (`tools/ci/evidence.go`, `workflow.go`, `trustedRoleOrder`) is consumer-owned and
   remains pending.

### 4.2 Responsibility Boundary
- **APGR Owns**: Internal test suite execution, coverage gates, policy checks, exit
  codes, and subproject-level summary JSON output.
- **JACA Owns**: Workflow pipeline definition, candidate-tree prospective hashing
  (`tools/ci/candidate.go`), tree stability verification (`ExecutionSource{Commit, CandidateTree, Stable}`),
  role execution timeouts, process stdout/stderr stream logging, and promotion decision logic.

---

## 5. Second Implementation Slice: APGR XO Compatibility (Integrated Source Qualified / JACA Adoption Pending)

### 5.1 Implemented Deliverables
1. **Caller-Owned Adapter Fixture**: Added `testing/fixtures/xo_consumer/` modeling an external
   Go caller consuming APGR's public Go packages (`skills`, `footprint`, and supporting `schema`).
   Implements caller DTOs (`CallerSkillEvidence`, `CallerFootprintEvidence`, `CallerComponentEvidence`,
   `CallerSourceReference`, `CallerComparisonDelta`, `CallerProjectionEvidence`) ensuring zero APGR domain types leak into caller boundaries.
2. **AST and Process Conformance Verification**: Automated test suite `adapter_test.go` verifying:
   - Bounded static AST inspection: Zero APGR types in caller signatures or struct fields across all runtime files (failing closed on unsupported non-struct forms), with negative controls (`TestXOAdapterContainmentNegativeControl`).
   - Bounded static dependency boundary: Zero `os/exec` imports or dependencies, zero imports of `internal/` or `cmd/` packages, and zero imports of JACA modules (`go list -deps`).
   - In-memory execution: In-memory smoke execution without subprocess invocation (`TestXOAdapterPureInMemoryRuntimeSmoke`).
   - Invariant enforcement: Context propagation (`skills.Resolve` and `skills.FootprintContext` evaluate caller `ctx`),
     sentinel error translation (`ErrUnitMismatch`, `ErrConsequenceBearingOmissionRefused`, `skills.ErrBudgetExceeded`),
     context cancellation propagation, supporting schema consumption (`schema.SHA256`), and reflection-verified caller contract item 7 non-authority.
3. **Dual-Lane Verification**:
   - **Lane A (Released Baseline v0.8.1)**: Module `example.invalid/apgr-xo-consumer` pinned to
     `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.8.1` verified against public Go proxy / sumdb.
   - **Lane B (Exact Development Candidate)**: Disposable local `replace` verified against the active
     development tree.
4. **Handoff Specification**: Created `docs/architecture/jaca-xo-handoff.md` defining interface
   mechanics, DTO isolation, error mappings, and downstream adoption instructions.

### 5.2 Responsibility Boundary
- **APGR Owns**: Public Go package APIs (`skills`, `footprint`, `schema`), DTO stability, semantic error sentinels,
  and APGR-side qualification fixtures.
- **JACA Owns**: JACA XO execution architecture, adapter implementation in `xo/src/main/go`, domain mapping,
  and integration timing.


## 6. Integrated qualification and remaining release boundary

APG114 [exit 00159](status/2026/09/06/00159-apg114-v090-integrated-source-qualification-exit.md)
owns the Darwin arm64 integrated qualification result and its exact closeout
evidence location. Producer passes remain historical; the source-bound closeout rerun and final
binding check now establish integrated qualification. The summary's `source_commit`
is entry HEAD evidence, not a substitute for the tested candidate inventory.

> [!NOTE]
> **Supersession and Evidence Preservation**: APG114 integrated source qualification
> supersedes prior intermediate qualification runs (APG110 through APG113) for
> integrated source conformance on Darwin arm64. All historical producer passes,
> intermediate candidate archives, and dated manifests are preserved as immutable
> historical evidence rather than retroactively modified. Active release preparation
> builds upon this integrated source qualification baseline; v0.9 remains an unpublished
> development candidate pending separate release authorization.

Remaining work is separated by owner:

1. APGR integrated CI/XO source qualification is addressed by APG114.
2. APG115 prepared v0.9.0 source versions, metadata, human documentation and
   inclusion policy. APG116 corrects permanent package-facing release wording
   found during qualification. The amended committed source requires fresh
   deterministic public candidate/bundle qualification before a publication
   handoff. Attended publication/readback and optional host flake promotion
   remain separate boundaries.
3. JACA owns CI role registration, platform qualification, and production XO
   adoption. These consumer gates are not APGR runtime dependencies.
4. Theme Forge and then Repo Map retain their later backlog decisions above.
   JACA CI and JACA XO remain ahead of both; no successor starts automatically.
