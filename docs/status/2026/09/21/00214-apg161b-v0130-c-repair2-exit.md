# APG161B / V0130-C-REPAIR2 — Native Home and Bundle Integration Repair Exit

Phase ID: `APG161B`
Exit ID: `Exit 00214`
Roadmap Milestone: `V0130-C` (`V0130-C-REPAIR2`)
Governing Decisions: [ADR 0071](../../../../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md), [ADR 0069](../../../../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)
Exit Target: `V0130_C_REPAIR2_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **checkpoint-ready** (V0130-C-REPAIR2 completed, verified, and qualified; candidate tree left dirty unstaged for revise_close checkpoint finalization)
- **Milestone Outcome**: **ACCEPTED** (V0130-C accepted under local finish commit `7e3a61b5055255f697309cefc63dbe9c92e0461d`)
- **Execution Mode**: `gemini_flash_sub`, native V1 `work-reviewed` (produce, independent work review, revise_close), finalization `checkpoint`.
- **Publication Authority**: The dispatcher owns stage transitions, reviewer selection, and Git publication. No agent Git mutation (`git add`, `git commit`, `git push`, `git checkout`, `git branch`) executed.

---

## 2. Core Corrections (B1–B4)

### 2.1 B1 — Effective-Home and Outbox Consumers
- **Scoped Home in V1 Resume & Monkeypatch Sensitivity**: Passed `apgr_home` conditionally (only when `apgr_home is not None`) in `libexec/agent_phase/dispatch.py`, `resume_dispatch.py`, and `result_repair.py`. Preserves backward compatibility with legacy positional monkeypatches while properly propagating explicit `--apgr-home` to `_scoped_apgr_home` during resume execution.
- **Strict Absolute Path Validation Before Resolution**: In `libexec/agent_phase/v2_dispatch.py` and `dispatch.py`, validated that `apgr_home` is an absolute path before calling `.resolve()`, raising `ValueError` rather than silently normalizing relative paths.
- **Hermetic Outbox Projection Closure**: In `libexec/agent_phase/outbox_projection.py`, eliminated dependency on `src/agentic_praxis_grimoire` by importing path primitives directly from `agent_phase.config_routing`, ensuring isolated generation and packaging closures execute without `ModuleNotFoundError`.
- **Outbox Precedence Resolution**: In `libexec/agent_phase/config_routing.py:resolve_outbox_root`, established clear precedence hierarchy: explicit argument / API > project-local configuration (`.apgr/config.toml`) > custom global operator configuration (`<APGR_HOME>/config.toml`) > ambient environment variables (`APGR_RUN_ROOT` > `AGENT_PHASE_RUN_ROOT` > `APGR_OUTBOX_ROOT`) > default outbox directory (`~/Documents/agent/outbox`). Global configuration precedence is strictly source-based rather than value-dependent, cleanly overriding ambient environment variables regardless of whether configured values coincide with defaults. Distinct from V2 run directory (`<APGR_HOME>/state/runs`). `ConfigError` is surfaced rather than swallowed.

### 2.2 B2 — Legacy Startup Sequencing and Generation Store
- **Decoupled Historical Readback from Writable Creation**: In `libexec/controller_generation_store.py` and `controller_generation_bootstrap.py`, separated historical generation readback and validation from writable store directory creation. `resolve_controller_dir` supports `lookup_only=True` and `commit=True` semantics, ensuring missing generation directories are not spuriously created during read-only lookup.
- **No Masking of Legacy Store**: Ensured writable store directory creation does not mask the legacy generation store (`~/.local/state/agent-central/generations`) when checking for existing generations under the default home before objects are materialized.
- **Native Bootstrap Sequencing & Immutability Verification**: Tested native `enter(repo)` startup sequence on resume. Verified legacy store files, byte digests (SHA-256), and file modes (`st_mode`) remain 100% unchanged, with zero locks or leases in the legacy store, while all new coordination locks, leases, and materialization are isolated in the new selected store (`~/.apgr/generations/<digest>`). Relocated homes (`source != "default"`) strictly bypass legacy store searches.

### 2.3 B3 — Single Captured Roster Bundle Across Policy, Routing, and Capabilities
- **Threaded Roster Snapshot Across V1 and V2**: In `libexec/agent_phase/cli.py` and `dispatch.py`, threaded the captured `RosterSnapshot` from policy resolution into `Dispatcher(roster=roster)` and `resolve(..., roster=self.roster)`, eliminating secondary roster loads on V1 dispatch and dry-run `continue_from` paths. In `v2_dispatch.py`, threaded `RosterSnapshot` across policy resolution, dynamic routing, and capability loading (`load_capabilities(roster=roster)` and `execute_v2_turns(roster=roster)`).
- **Fail-Closed Generation Mismatch & Byte Change Rejection**: Prelaunch verification rejects generation mismatches or uncommitted byte changes between policy, routes, endpoints, and capabilities across all provenance sources (inspecting winner or provenance chain for operator default coherence).
- **Lazy Roster Resolution on Dispatcher**: In `libexec/agent_phase/dispatch.py`, shifted fallback roster loading from eager `__init__` instantiation to lazy `_ensure_roster_and_policy()` called on demand during `dispatch()` and `dry_run()`. Enables finalize-only resumes and mocked fixtures to initialize cleanly without failing on missing or broken TOML files when the current roster is unneeded. In `cli.py:dispatch_main`, removed redundant eager `load_roster` invocation. In `v2_dispatch.py`, restricted `resume_from_run_id` prelaunch check to live execution (`not dry_run`), preserving dry-run persistence tests.

### 2.4 B4 — Governance Records and Qualification
- **Exit Record Allocation**: Allocated Exit 00214 (`docs/status/2026/09/21/00214-apg161b-v0130-c-repair2-exit.md`) and indexed in `docs/status/README.md`.
- **Roadmap Synchronization**: Updated `docs/v0-13-roadmap.md` milestone V0130-C with phase `APG161B` and exit `00214`.
- **Candidate Delta Reconciliation**: Reconciles the 59 candidate delta paths against the 56 paths adopted by the launcher: the 56 adopted candidate paths plus 3 APG161B governance records (`00214` exit record, `docs/status/README.md`, `docs/v0-13-roadmap.md`).
- **Qualification Artifacts**: Bound qualification receipt to dirty candidate tree identity with foreground test logs and JUnit XML under launcher qualification directory. Toolchain versions recorded explicitly (`Python 3.13.12, pytest-8.4.2; go version go1.25.10 darwin/arm64`).

---

## 3. Verification Matrix

| Check / Suite | Scope | Result | Details |
|---|---|---|---|
| `test_agent_phase_dispatch.py` | V1 dispatcher execution & lazy roster | **PASS** (117/117) | Lazy roster initialization, finalize-only resume without current roster. |
| `test_agent_phase_resume_boundaries.py` | Resume boundary conditions | **PASS** (34/34) | Boundary checks, stage transitions, error states. |
| `test_agent_phase_resume_dispatch.py` | Resume dispatch lifecycle | **PASS** (7/7) | Scoped apgr_home propagation, state reload. |
| `test_agent_phase_resume_roster_transition.py` | Resume roster transitions | **PASS** (11/11) | Roster transition rules, cross-generation resume. |
| `test_agent_phase_resume_cli.py` | CLI resume command | **PASS** (7/7) | CLI invocation, argument propagation. |
| `test_agent_phase_v2_dispatch.py` | V2 execution & prelaunch gates | **PASS** (11/11) | Absolute path checks, dry-run resume allowance, single snapshot threading. |
| `test_agent_phase_v2_full_execution.py` | V2 full execution pipeline | **PASS** (10/10) | End-to-end multi-turn execution with threaded capabilities. |
| `test_agent_phase_v2_outbox_projection.py` | V2 outbox projection & hermetic imports | **PASS** (12/12) | Hermetic imports, locator metadata, archive hashing. |
| `test_agent_phase_run_layout.py` | Run layout & outbox precedence | **PASS** (53/53) | Precedence: API > project > custom global > ambient env > default outbox. |
| `test_agent_phase_config_routing.py` | Config routing & policy | **PASS** (23/23) | 4-tier policy resolution, operator bundle generation matching, value-independent outbox, V1 roster reuse. |
| `test_agent_phase_dynamic_routing.py` | Dynamic routing closure | **PASS** (11/11) | Fail-closed dynamic routing, static preset fallback. |
| `test_agent_phase_review_mutation_repair.py` | Review mutation policy repair | **PASS** (39/39, 1 skipped) | Policy validation, snapshot threading, V1 home scoping. |
| `test_agent_phase_roster.py` | Roster bundle validation | **PASS** (38/38) | Generation matching, bundle completeness, operator bundle. |
| `test_agent_phase_home_show.py` | Home inspection & cross-language contract | **PASS** (14/14) | Python resolved_config, Go paths_only, Go --from-json configured parity. |
| `test_controller_generation_store.py` | Generation storage & bootstrap | **PASS** (44/44) | Historical readback vs writable creation, enter() native bootstrap, legacy immutability, legacy fallback. |
| `test_controller_generation_real_cli.py` | Controller CLI generation real test | **PASS** (1/1) | Real CLI invocation with isolated generation store. |
| `test_claude_profile_directories.py` | Claude profile settings & directories | **PASS** (67/67) | Canonical settings precedence, tampering detection, scratch isolation. |
| `test_agent_phase_schema_manifest.py` | SQLite schema manifest export | **PASS** (2/2) | V5 schema manifest validation, table and column parity. |
| `test_agent_phase_resume.py` | Resume lifecycle & home scoping | **PASS** (14/14) | Scoped apgr_home propagation on success/failure. |
| `go test -count=1 ./...` | Full Go workspace | **PASS** (21 packages: 20 ok, 1 no test files) | Clean go test across all packages under go1.25.10. |
| `go vet ./...` | Go static analysis | **PASS** | Clean, exit 0. |
| `bin/apg-check-record-identity` | Record governance | **PASS** | 74 ADRs, 212 exits, 212 phase IDs; next ADR 0075; next exit 00215. |
| `bin/apg-check-skill-library` | Skill governance | **PASS** | 45 canonical skills, 45 catalog rows, 45 projections. |
| `bin/apg-check-roadmap-closure` | Roadmap governance | **PASS** | 55 terminal rows, 0 open items, zero-backlog qualified. |
| `git diff --check` | Whitespace check | **PASS** | Clean, zero whitespace errors. |

---

## 4. Operational Boundaries

- **Candidate Retained Dirty**: All modified paths remain dirty and unstaged.
- **No Git Publication**: Finalization is `checkpoint`; dispatcher owns review and commit.
- **Isolated State**: No operations against live shared database (`~/.apgr/state/dispatcher.sqlite3`); test operations use temporary directories.

---

## 5. Outcome Addendum: Manager C Acceptance

- **Acceptance Status**: **ACCEPTED** by Manager C under local finish commit `7e3a61b5055255f697309cefc63dbe9c92e0461d`.
- **Milestone Disposition**: `V0130-C` is fully closed and qualified for local development integration.
- **Handoff Target**: Program advances to Milestone `V0130-D` (Phase `APG162`, Exit `00215`).
