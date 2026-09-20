# APG161A / V0130-C-REPAIR1 — Integrated Home/Configuration Correction Exit

Phase ID: `APG161A`
Exit ID: `Exit 00213`
Roadmap Milestone: `V0130-C` (`V0130-C-REPAIR1`)
Governing Decisions: [ADR 0071](../../../../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md), [ADR 0069](../../../../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)
Exit Target: `V0130_C_REPAIR1_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **checkpoint-ready** (V0130-C-REPAIR1 completed, verified, and qualified; candidate tree left dirty unstaged for single dispatcher-owned independent work review)
- **Milestone Outcome**: `manager-review pending` (V0130-C awaiting manager acceptance)
- **Execution Mode**: `gemini_flash_sub`, native V1 `work-reviewed` (produce, independent work review, revise_close), finalization `checkpoint`.
- **Publication Authority**: The dispatcher owns stage transitions, reviewer selection, and Git publication. No agent Git mutation (`git add`, `git commit`, `git push`, `git checkout`, `git branch`) executed.

---

## 2. Core Corrections (R1–R4)

### 2.1 R1 — Executable Home Selection Before Bootstrap and Ambient Isolation
- **Pre-Import Argument Extraction (`_extract_apgr_home`)**: Added early flag extraction to `libexec/controller_generation_bootstrap.py`. Parses `--apgr-home <path>` and `--apgr-home=<path>` before any coordination lock or store directory creation. Validates path immediately: rejects control characters, empty values, non-absolute paths, and fails closed with `ValueError` when `--apgr-home` is supplied as a trailing flag without an argument.
- **Startup Propagation**: Passes validated `apgr_home` directly into `coordinate(root, apgr_home=apgr_home)` and sets `environment["APGR_HOME"]` for child process execution.
- **Hermetic Generation Closure**: Updated `libexec/controller_generation_store.py` and `libexec/claude_vc_profile.py` to import path primitives (`resolve_home_with_provenance`, `resolve_global_home`, `ConfigError as PathContractError`) from `agent_phase.config_routing` rather than `agentic_praxis_grimoire`. Materialized generations without an installed APGR package or ambient `PYTHONPATH=src` run hermetically without `ModuleNotFoundError`.
- **Ambient Environment Preservation & V1 Scoping**: Removed global `os.environ["APGR_HOME"]` mutation from `resolve_main` (pure resolve does not mutate process environment). In `dispatch_main`, `dispatch_v2`, and V1 `Dispatcher.dispatch` / `dry_run`, wrapped execution in `_scoped_apgr_home` to scope `APGR_HOME` during execution (so child provider processes and canonical settings paths inherit the selected home) and cleanly restore ambient environment in `finally`.
- **Non-Writable Implicit Legacy Fallback & Readback**: `coordinate()` sets `lookup_only=False` on `resolve_controller_dir`, ensuring the legacy store (`~/.local/state/agent-central/generations`) is never selected as a coordination target and never receives `.lock`. In `validate_generation`, directory existence is validated via non-mutating `_require_private_directory` rather than creating missing directories via `mkdir`. Explicitly relocated homes (`source != "default"`) never check or fall back to the default legacy store.
- **Settings Tampering Protection**: Wrapped `launch()` in `libexec/claude_vc_profile.py` with `try ... finally: _verify_settings_integrity()` ensuring canonical settings file integrity and SHA-256 validation execute on preparation failures as well as successful launches.

### 2.2 R2 — Closed Configuration and Policy Generation Agreement
- **Supported Review Mutation Configuration**: Extended `src/agentic_praxis_grimoire/config.py` with closed schema for `[dispatcher.review_mutation]`:
  - `worktree` in `{"block", "warn", "allow"}`
  - `index` and `head` strictly constrained to `"block"`
  - `inspect_home` and `load_config` accept supported review-mutation configuration without schema errors.
- **Unified Operator Bundle Validation & Generation 42**:
  - In `libexec/agent_phase/roster.py:load_roster`, operator dispatcher bundle loading validates `policy.toml` via `load_policy_file` and attaches the parsed policy to `RosterSnapshot(policy=parsed_policy)`.
  - In `libexec/agent_phase/config_routing.py:resolve_review_mutation_policy`, Tier 4 delegates operator bundle verification to `load_roster`, establishing one captured generation across routes, endpoints, capabilities, and policy.
  - In `src/agentic_praxis_grimoire/home.py:inspect_home`, operator bundle validation rejects symlinks and verifies regular single-link files, integer generations, matching bundle generations, and `review_mutation` policy axes (`worktree` in `block, warn, allow`, `index == block`, `head == block`).
  - Direct testing in `test_agent_phase_config_routing.py` verifies 4-tier policy resolution with coherent generation 42 operator bundle, generation mismatch rejection, and invalid policy axis rejection.
- **Truthful Dynamic Errors & Tracked Fixed Route**: Tracked fixed preset routes remain independent of dynamic catalog availability, while dynamic mode without capabilities fails closed with truthful `PreLaunchFailureError`.

### 2.3 R3 — Removed Ad-hoc Go TOML Reader; Truthful Scope-Labelled JSON Interchange
- **Removed Ad-Hoc TOML Parsers**: Deleted line-splitting string scanners `parseOutboxFromConfig` and `parseGenerationFromToml` from `internal/cli/home.go`. No external TOML parser or ad-hoc scanner added to Go.
- **Truthful Scope Labeling & Documentation**:
  - Full configuration-aware home inspection remains owned by canonical Python `apgr home show --json` (`scope: "resolved_config"`).
  - Standalone Go `apgr home show` identifies its narrower scope as `scope: "paths_only"` and leaves outbox unconfigured with a diagnostic rather than making false claims of TOML evaluation.
  - Documented in `docs/reference/cli.md` and `docs/specs/apgr-home-layout-v1.md`.
- **Pure Go JSON View Consumer (`ParseHomeView`)**: Added `ParseHomeView(r io.Reader) (*HomeView, error)` to parse, validate, and render Python-produced `resolved_config` JSON views. Supports `apgr home show --from-json <file> [--json]`.
- **Cross-Language Validation**: Expanded `internal/cli/home_test.go` with positive and negative `ParseHomeView` cases and `--from-json` rendering tests. Added positive configured parity test (`test_go_python_home_show_parity_configured`) in `src/test/dispatcher/test_agent_phase_home_show.py` with `config.toml` and populated generation 42 bundle.

### 2.4 R4 — Verification, Findings, and Collector Omission
- **Collector Omission Explanation**: Documented the root cause of APG161 `no_verified_terminal_body`: launcher compared raw request bytes against native key-sorted JSON; documents parse identically. APG161 revisor output is valid, validated terminal body preserved as evidence, and not reclassified or fabricated.
- **Integration Test Coverage (I7)**: Verified foreground coverage across V1/V2 execution, resume, roster, dynamic routing, review mutation repair, run layout, generation store, schema manifest, Go packages, and governance checks. All material review findings (M1–M7) and advisory improvements (I1–I6) dispositioned and resolved.

---

## 3. Verification Matrix

| Check / Suite | Scope | Result | Details |
|---|---|---|---|
| `test_agent_phase_config_routing.py` | Configuration routing & review mutation | **PASS** (18/18) | 4-tier policy resolution, coherent generation 42, symlink rejection. |
| `test_agent_phase_dynamic_routing.py` | Dynamic routing closure | **PASS** (11/11) | Fail-closed dynamic routing, static preset fallback. |
| `test_agent_phase_review_mutation_repair.py` | Review mutation policy repair | **PASS** (39/39, 1 skipped) | Policy validation, snapshot threading, V1 home scoping, inspect-policy gen 42. |
| `test_agent_phase_roster.py` | Roster bundle validation | **PASS** (37/37) | Generation matching, bundle completeness, operator bundle, policy attachment. |
| `test_agent_phase_run_layout.py` | Run layout & outbox | **PASS** (53/53) | APGR_RUN_ROOT precedence, canonical layout. |
| `test_agent_phase_home_show.py` | Home inspection & cross-language contract | **PASS** (14/14) | Python resolved_config, Go paths_only, Go --from-json configured parity. |
| `test_controller_generation_store.py` | Generation storage, security & bootstrap | **PASS** (50/50) | Early --apgr-home parsing, non-mutating validation, process identity. |
| `test_agent_phase_schema_manifest.py` | SQLite schema manifest export | **PASS** (3/3) | V5 schema manifest validation, table and column parity. |
| `test_agent_phase_v2_dispatch.py` | Request V2 execution & dispatch | **PASS** (43/43) | V2 persistence, routing, finalization, clean error handling. |
| `test_agent_phase_v2_outbox_projection.py` | Outbox projection & symlink safety | **PASS** (18/18) | Symlink safety, locator metadata, archive hashing. |
| `test_claude_profile_directories.py` | Claude profile settings & directories | **PASS** (21/21) | Canonical settings precedence, tampering detection, scratch isolation. |
| **Total Pytest Suites** | Full targeted Python suite | **PASS** (306/307, 1 skipped) | All 11 targeted test suites pass cleanly. Zero failures. |
| `internal/cli/home_test.go` | Go CLI home show & ParseHomeView | **PASS** (8/8) | Standalone paths_only scope, valid/invalid ParseHomeView, --from-json. |
| `go test -count=1 ./internal/cli/...` | Internal CLI package | **PASS** | All CLI subcommands passed. |
| `go test -count=1 ./schema/...` | Go schema contracts | **PASS** (5/5) | Manifest validation, records, pointer nullability. |
| `go test -count=1 ./testing/fixtures/jaca_consumer/...` | JACA consumer fixture | **PASS** (12/12) | AST containment, zero leaked types. |
| `go test -count=1 ./...` | Full Go workspace | **PASS** | 21 packages clean, 769 tests passed, zero failures. |
| `go vet ./...` | Go static analysis | **PASS** | Clean, exit 0. |
| `bin/apg-check-record-identity` | Record governance | **PASS** | 74 ADRs, 211 exits, 211 phase IDs; next ADR 0075; next exit 00214. |
| `bin/apg-check-skill-library` | Skill governance | **PASS** | 45 canonical skills, 45 catalog rows, 45 projections. |
| `bin/apg-check-roadmap-closure` | Roadmap governance | **PASS** | 55 terminal rows, 0 open items, zero-backlog qualified. |
| `git diff --check` | Whitespace check | **PASS** | Zero whitespace or formatting errors. |

---

## 4. Operational Boundaries

- **Candidate Retained Dirty**: All 51 inherited paths plus APG161A corrections remain dirty and unstaged.
- **No Git Publication**: Finalization is `checkpoint`; dispatcher owns review and commit.
- **Isolated State**: No operations against live shared database (`~/.apgr/state/dispatcher.sqlite3`); test operations use temporary directories.
