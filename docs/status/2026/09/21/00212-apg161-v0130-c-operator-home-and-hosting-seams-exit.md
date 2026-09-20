# APG161 — v0.13.0 Operator Home, Closed Config, and State Seams Exit

Phase ID: `APG161`
Exit ID: `Exit 00212`
Roadmap Milestone: `V0130-C`
Governing Decisions: [ADR 0071](../../../../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md), [ADR 0069](../../../../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)
Exit Target: `V0130_C_HOME_LAYOUT_AND_HOSTING_SEAMS_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **checkpoint-ready (manager correction required)** (milestone V0130-C clusters C1–C4 implemented and verified in APG161 checkpoint candidate; manager review withheld V0130-C acceptance due to R1–R3 boundary defects; APG161A / V0130-C-REPAIR1 authorized to complete corrections)
- **Milestone Outcome**: `manager-review pending` (retained candidate adopted into APG161A)
- **Execution Boundary**: Dispatcher implementation across canonical home inspection (`home.py`, `home.go`, `cli.py`, `internal/cli/`), roster and dynamic routing closure (`roster.py`, `capabilities.py`, `dynamic_router.py`, `resolution_v2.py`, `v2_dispatch.py`, `v2_turns.py`, `config_routing.py`), settings and environment aliases (`claude_vc_profile.py`, `run.py`, `controller_generation_store.py`, `controller_generation_bootstrap.py`, `claude_profile_directories.py`), and SQLite schema manifest with Go hosting contracts (`schema_manifest.py`, `docs/architecture/dispatcher-sqlite-schema-v5.json`, `schema/`, `testing/fixtures/jaca_consumer/`).
- **Publication Authority**: Finalization is strictly `checkpoint` under `gemini_flash_sub` execution mode. The dispatcher owns stage transitions, reviewer selection, and Git publication. No agent Git mutation (`git add`, `git commit`, `git push`, `git checkout`, `git branch`) executed.

---

## 2. Core Delivery Summary (Clusters C1–C4)

### 2.1 Cluster C1 — Canonical Home Inspection and Layout
- **Canonical Layout (`apgr-home-layout-v1`)**: Implemented `src/agentic_praxis_grimoire/home.py` defining `home_layout_paths` and `inspect_home`. Fully non-mutating inspection returning `layout_version`, `precedence_source`, `effective_home`, `paths` dictionary, and non-fatal `diagnostics`. Non-existent home directories or missing files do not create directories or alter filesystem state.
- **Precedence Hierarchy**: Strict resolution `--apgr-home` (CLI) > `APGR_HOME` (environment) > `~/.apgr` (default). Zero coupling to `JACA_HOME` or ambient foreign orchestrator variables.
- **CLI Subcommand**: Added `apgr home show [--json]` to Python and Go CLIs (`src/agentic_praxis_grimoire/cli.py` and `internal/cli/home.go`) with exact JSON field parity. Added `--apgr-home` global flag support across both CLIs and wired `Dispatcher.__init__` to preserve effective `apgr_home`.

### 2.2 Cluster C2 — Coherent Configuration & Fail-Closed Roster
- **Bundle Integrity & Generation Matching**: Updated `load_roster` in `libexec/agent_phase/roster.py` to inspect `<APGR_HOME>/dispatcher/`. Requires all 4 operator files (`routes.toml`, `endpoints.toml`, `capabilities.toml`, `policy.toml`) with matching integer `generation` numbers. Partial bundles and generation mismatches fail closed with clear diagnostics; when no operator bundle exists, falls back cleanly to tracked `common/dispatcher/`.
- **Fail-Closed Dynamic Routing**: Hardened `resolution_v2.py`, `v2_dispatch.py`, and `v2_turns.py` so dynamic routing without a valid capabilities catalog fails closed before launch with `RoutingResolutionError` / `PreLaunchFailureError`.
- **Static Preset Route Fallback**: Fixed preset routes (`fixed_claude`, `fixed_codex`, etc.) fall back to `_default_endpoint_capabilities` so non-dynamic runs execute predictably without dynamic catalog dependencies.
- **Review Mutation Policy Tier 4**: Updated `resolve_review_mutation_policy` to load from operator `policy.toml` when present, else tracked fallback.

### 2.3 Cluster C3 — Settings, Generation Roots & Aliases
- **Operator Claude Settings Isolation**: Updated `canonical_settings_path` in `libexec/claude_vc_profile.py` to check `<APGR_HOME>/claude/settings.json` first (read-only, non-symlink regular file, valid JSON). Falls back to `<controller_root>/claude/settings.json` when absent. In `launch()`, records SHA-256 before argument preparation and verifies presence and identical SHA-256 after preparation to prevent in-flight tampering.
- **Root and Store Aliases**:
  - `run.py` and `outbox_projection.py`: `APGR_RUN_ROOT` takes precedence over historical `AGENT_PHASE_RUN_ROOT`.
  - `controller_generation_store.py`: `APGR_GENERATION_STORE` takes precedence over `AGENT_CENTRAL_GENERATION_STORE`, defaulting to `<APGR_HOME>/generations`.
  - **Legacy Readback Rule**: Legacy store `~/.local/state/agent-central/generations` is checked only when using default home (`~/.apgr`); an explicitly relocated home (`APGR_HOME`) never reads from the legacy store unless explicitly configured.
  - `controller_generation_bootstrap.py`: `APGR_ACTIVE_ROOT` takes precedence over `AGENT_CENTRAL_ACTIVE_ROOT`.
  - `claude_profile_directories.py`: Added `create: bool = True` to `resolve_scratch` to permit non-mutating path resolution without creating or chmodding directories.

### 2.4 Cluster C4 — SQLite Schema Manifest & Go Hosting Contracts
- **Schema Manifest Generator**: Created `libexec/agent_phase/schema_manifest.py` to extract PRAGMA table information, foreign keys, and indexes from in-memory migrated SQLite database, producing `docs/architecture/dispatcher-sqlite-schema-v5.json`.
- **Go Hosting Contracts in `schema/`**:
  - Created `schema/manifest.go` defining `DispatcherSchemaManifest`, `TableShape`, `ColumnShape`, `ForeignKeyShape`, `IndexShape`, and validation function `ValidateDispatcherSchemaManifest`.
  - Created `schema/records.go` defining typed row DTOs for `RunRecord`, `RouteResolutionRecord`, `InvocationAttemptRecord`, `OperationalObservationRecord`, `ReviewMutationObservationRecord`, `ReviewMutationPolicyRecord`, `LegacyQuarantineObservationRecord`, and `LegacyQuarantinePolicyRecord` with pointer-based nullability.
  - Package `schema/` isolated from `internal/apimanifest`, maintaining zero drift in `docs/architecture/v0-12-apgr-go-api-manifest.json`.
- **Consumer Fixture Integration**: Updated `testing/fixtures/jaca_consumer/adapter.go` with `CallerSchemaManifest`, `CallerRunRecord`, `ValidateSchemaManifest`, and `ValidateRunRecord`. Verified AST containment with `schema.` in prohibited prefixes (zero leaked types and zero forbidden imports).
- **Drift Protection**: Added `src/test/dispatcher/test_agent_phase_schema_manifest.py` verifying zero drift between live migration and committed JSON manifest.

---

## 3. Verification and Qualification Summary

| Check / Suite | Scope | Result | Details |
|---|---|---|---|
| `test_agent_phase_home_show.py` | Home layout & inspection | **PASS** (10/10) | Precedence, layout paths, diagnostics, non-mutating inspection. |
| `internal/cli/home_test.go` | Go CLI home show | **PASS** (5/5) | JSON output format parity, flag precedence. |
| `test_agent_phase_roster.py` | Roster bundle validation | **PASS** (37/37) | Generation matching, partial bundle rejection, operator bundle loading. |
| `test_agent_phase_dynamic_routing.py` | Dynamic routing closure | **PASS** (11/11) | Fail-closed dynamic routing on missing catalog, static preset fallback. |
| `test_agent_phase_config_routing.py` | Configuration routing | **PASS** (21/21) | Tiered policy resolution, operator policy precedence. |
| `test_claude_profile_directories.py` | Profile dirs & settings | **PASS** (67/67) | Settings precedence, JSON validation, tampering detection, create=False. |
| `test_controller_generation_store.py` | Generation store & aliases | **PASS** (41/41) | APGR_GENERATION_STORE, legacy readback rule, APGR_ACTIVE_ROOT precedence. |
| `test_agent_phase_run_layout.py` | Run layout & outbox | **PASS** (35/35) | APGR_RUN_ROOT winning over AGENT_PHASE_RUN_ROOT. |
| `test_agent_phase_schema_manifest.py` | Schema manifest drift | **PASS** (2/2) | Zero drift against committed JSON manifest and table coverage. |
| `go test -count=1 ./schema/...` | Go schema package | **PASS** (5/5) | Manifest validation, record roundtrips, quarantine nullability. |
| `go test -count=1 ./testing/fixtures/jaca_consumer/...` | JACA consumer fixture | **PASS** (12/12) | AST containment (zero leaked types), dependency boundary, schema adapter. |
| `go test -count=1 ./...` | All 21 Go packages | **PASS** | 19 packages with tests passed, 2 packages without test files; zero cache. |
| `go vet ./...` | Go static analysis | **PASS** | Clean; zero vet diagnostics. |
| `bin/apg-check-record-identity` | Phase & record identity | **PASS** | 74 ADRs, 210 exits, 210 phase IDs; next exit 00213; next ADR 0075. |
| `bin/apg-check-skill-library` | Canonical skill catalog | **PASS** | 45 canonical skills, 45 catalog rows, 45 projections. |
| `bin/apg-check-roadmap-closure` | Legacy roadmap closure | **PASS** | 55 terminal rows, 0 open rows; zero backlog qualified. |

---

## 4. Explicit Not-Run Boundaries and Residual Limitations

- **No Git Commit, Push, or Branching**: Dispatcher owns finalization and Git publication under `checkpoint`. No Git mutation commands executed.
- **Live Shared Database**: No operations executed against live shared operator database (`~/.apgr/state/dispatcher.sqlite3`); all persistence testing conducted in isolated memory or scratch databases.
- **Dispatcher Review**: Dispatcher owns reviewer selection and post-work verification.
- **Zero Implicit Run Migration**: Existing run directories in `<APGR_HOME>/state/runs` or outbox remain untouched; APGR does not execute implicit backward migrations.
