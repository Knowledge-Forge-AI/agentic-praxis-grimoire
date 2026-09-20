# APG147 — v0.12 Agent-Central Dispatcher Parity Migration Evaluation

## Scope and status

Phase ID: `APG147`  
Roadmap Stage: `V0120-B`  
Disposition: **amend** (incorporating independent work-review findings F2–F15)  
Outcome: `V0120_B_AGENT_CENTRAL_DISPATCHER_PARITY_MIGRATED`  

Milestone `V0120-B` executes the direct, full-fidelity migration of the single-phase execution runtime prototyped in Agent-Central into permanent ownership in APGR with 100% behavioral and evidence parity for `agent-phase-request-v1`. Zero modifications were made to external repositories (`agent-central`, `jaca`).

## 1. Pinned Baselines Inspected

- **APGR Working Baseline**: `10bf3095bf02ce664f6e2bb54ab60c3fb573eb6f` (APG146 / V0120-A exit).
- **Candidate APGR Tree**: `936794e203fc07cb0717b7f8fa60ff0ff4a5244a`.
- **Agent-Central Pinned Baseline**: `56e9bb039536dfc8893e61a431681d6a32167b6f` (clean, verified unmodified).
- **JACA Baseline**: `08ca2208805cf446bd15da0a6b4c8c58db737587` (clean, verified unmodified).

## 2. Independent Work-Review Finding Disposition (F2–F15)

The terminal disposition amends and resolves all findings raised during the independent work review:
- **F2 (Test Execution & CI Gate Integration)**: Disclosed in ADR 0063 N4; runtime modules and test surface execute via `./bin/apg-test-dispatcher`. Integration of the dispatcher test lane into the automated GitHub Actions CI pipeline is scheduled for V0120-C.
- **F3 (Governed Code Verification)**: Direct Python unit tests for `libexec/apg_test.py` (`src/test/unit/python/agentic-praxis-grimoire/libexec/apg_test.unit.test.py`) verified 166 passed. Full multi-language TypeScript integration testing via `bin/apg-test unit-integration` is delegated to external CI when `APG_TYPESCRIPT_TSC` is absent locally.
- **F4 (Parity Corpus Provenance & Depth)**: Added explicit baseline provenance (`baseline_commit: 56e9bb039536dfc8893e61a431681d6a32167b6f`) to `src/test/dispatcher/fixtures/parity_golden_corpus.json`. Locked concrete model and effort readbacks (`gpt-6-astra`/`medium`, `claude-fable-5-1`/`high`, `claude-opus-5`/`high`, `gemini-3.8-flash-high`) and concrete coded error instances (`ArchiveError`, `FinalizationError`) in `test_agent_phase_parity_corpus.py`.
- **F5 (Worker Capability/Custody Gap)**: Retaining the upstream interactive worker pool facility in Agent-Central is an intentional boundary decision. The fail-safe disabled worker capability path is verified; positive-branch capability and worker custody testing are tracked as deferred gaps for V0120-C/D.
- **F6 (Claude Standalone Fail-Closed)**: Claude provider construction fails closed when operator-supplied `claude/settings.json` is absent, preserving baseline security invariants without copying user-global credentials. Documented in ADR 0063 N7; configurable policy templates deferred to V0120-C/D.
- **F7 (Prompt Guidance Byte Parity)**: Restored `antigravity/GEMINI.md`, `claude/CLAUDE.md`, and `codex/AGENTS.md` to 100% byte parity with baseline `56e9bb039536dfc8893e61a431681d6a32167b6f`, guaranteeing exact advertised prompt transport SHA-256 digests. Personal paths in baseline profiles are retained for V1 parity; portability redesign deferred to V0120-C/D.
- **F8 (`APGR_DISPATCHER_CONFIG` Status)**: Marked as a proposed future extension for V0120-C in `docs/architecture/v0-12-agent-central-ownership-transition.md`. In V0120-B, discovery defaults strictly to repository-relative `common/dispatcher/`.
- **F9 (Recursive Compatibility Wrapper Guard)**: Added self-realpath recursion prevention and candidate search across APGR install paths in the proposed `bin/agent-phase-dispatch` script in `docs/architecture/v0-12-agent-central-ownership-transition.md`.
- **F10 (Exit Token Alignment)**: Reconciled exit token from `V0120_B_DISPATCHER_PARITY_VERIFIED` to `V0120_B_AGENT_CENTRAL_DISPATCHER_PARITY_MIGRATED` across all records, roadmap, and evaluation summaries.
- **F11 (Closeout Content & Launcher Names)**: Corrected launcher list in ADR 0063 (10 wrappers). Added complete test counts, provider qualification statuses, deferred gaps, and next phase identifier.
- **F12 (Helper-Module Test Accounting)**: Recorded 8 baseline provider helper test suites (`claude/test/` 4, `antigravity/tests/` 3, `codex/tests/` 1) in `docs/architecture/v0-12-agent-central-migration-inventory.md` with **DEFER** disposition to V0120-C/D.
- **F13 (Controller Generation Active Root & Store Coupling)**: Documented in ADR 0063 N7; APGR operates in development mode preserving production generation store immutability unless `AGENT_CENTRAL_ACTIVE_ROOT` is configured.
- **F14 (Controller Cutover Directory Assumption)**: Noted pre-existing directory assumption in test environment setup.
- **F15 (Narrative Precision)**: Reconciled exact profile counts (Antigravity 5, Claude 11, Codex 7), 10 CLI wrappers, 72 test suites, and exact test execution figures.

## 3. Migration and Delivery Inventory

The following assets were transferred and qualified within APGR:
- **`libexec/agent_phase/`**: 62 single-phase execution modules (all byte-identical to baseline).
- **`libexec/`**: 11 helper and bootstrap modules (`agent_source_guidance.py`, `antigravity_profile.py`, `antigravity_terminal_evidence.py`, `claude_live_renderer.py`, `claude_model_catalog.py`, `claude_vc_profile.py`, `controller_generation_bootstrap.py`, `controller_generation.py`, `controller_generation_store.py`, `controller_generation_process.py`, `controller_generation_admin.py`).
- **`common/dispatcher/`**: `endpoints.toml` (19 endpoints), `routes.toml` (30 execution routes), `README.md`.
- **Provider Profiles**: `antigravity/profiles/` (5 files), `claude/profiles/` (11 files), `claude/model-catalog-v1.json`, `codex/profiles/` (7 files + `README.md`), `codex/config.d/170-subagents.toml`.
- **Standing Guidance**: `antigravity/GEMINI.md`, `claude/CLAUDE.md`, `codex/AGENTS.md` (100% byte-identical to baseline).
- **CLI Wrappers**: 10 native executable wrappers in `bin/agent-phase-*` (`dispatch`, `resolve`, `finalize`, `archive`, `adopt`, `adopt-entry`, `native-git`, `ownership`, `scan-label`, `scan-summary`) + 3 helper CLIs (`agent-controller-generation`, `antigravity-profile`, `claude-profile`).
- **Test Suites**: 72 test suites in `src/test/dispatcher/` (65 agent-phase suites + 6 controller-generation suites + 1 parity golden corpus suite).

## 4. Verification Suite Readout

1. **Full Dispatcher Test Sweep**:
   - Command: `./bin/apg-test-dispatcher -n 8`
   - Readout: `1,737 passed, 5 skipped in 9m 10s` (0 failures across all 72 suites; 5 skips across 4 suites due to upstream worker pool retention).
2. **Golden Parity Corpus**:
   - Command: `./bin/apg-test-dispatcher src/test/dispatcher/test_agent_phase_parity_corpus.py`
   - Readout: `6 passed in 0.10s` (30/30 routes, request grammar, lifecycle topologies, concrete model/effort readback, baseline provenance, and coded errors verified).
3. **Core Test Runner Python Unit Tests**:
   - Command: `.venv/bin/python -m pytest src/test/unit/python/agentic-praxis-grimoire/libexec/apg_test.unit.test.py`
   - Readout: `166 passed in 3.02s`
4. **APGR Policy Gate**:
   - Command: `.venv/bin/python bin/apg-test policy`
   - Readout: `PASS policy: inventory, skill-library, record-identity, and roadmap-closure checks passed`
5. **Record Identity**:
   - Readout: `PASS APG record identity: 63 ADRs, 192 exits, 192 phase IDs; next ADR 0064; next exit 00193`
6. **File Length Policy**:
   - Command: `python3 tools/ci/file_length_policy.py --include-untracked`
   - Readout: `file-length: passed with warnings (scanned: 334 Python files, warnings: 103, failures: 0)`
7. **CI Topology, Prompt Defense, and Drift Checks**:
   - `python3 tools/ci/ci_topology.py`: PASS
   - `python3 tools/ci/prompt_defense_check.py`: PASS
   - `python3 tools/ci/check_generated_drift.py`: PASS
8. **External Checkout Verification**:
   - `git -C <jaca>/ci status --porcelain`: 0 lines (clean)
   - `git -C <agent-central> status --porcelain`: 0 lines (clean)

## 5. Provider-Specific Qualification Status

- **Codex**: Verified deterministic 30-route resolution, profile compilation, intelligence readback (`gpt-6-astra`, `medium`), and configuration loading. Live provider canary deferred (provider-free deterministic qualification complete).
- **Claude**: Verified deterministic routing, profile compilation, model catalog lookup (`claude-fable-5-1`, `claude-opus-5`), and live renderer formatting. Operates in fail-closed mode when operator `claude/settings.json` is absent, matching baseline security intent without bundling personal host settings. Live provider canary deferred.
- **Antigravity**: Verified deterministic routing, profile compilation, terminal evidence parsing, and terminal output recovery. Live provider canary deferred.

## 6. Known Gaps Explicitly Deferred

- **V0120-C**: Automated CI pipeline execution for `bin/apg-test-dispatcher` sidecar test lane; configuration root override (`APGR_DISPATCHER_CONFIG`); decoupling controller generation store path and active root detection from Agent-Central locations.
- **V0120-C/D**: Positive worker capability branch and upstream worker pool integration; portable Claude operator settings template; standalone provider helper test suite migration.
- **V0120-E**: Go dispatcher surfaces and JACA integration.

## 7. Next Phase

The next separately authorized phase is **V0120-C** (`APG148` — Semantic Roles, Flexible Actor Binding, and SQLite Dispatcher Persistence). No V0120-C work is begun in this dispatch.
