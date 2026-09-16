# APG147 — v0.12 Agent-Central Dispatcher Parity Migration Exit

Phase ID: `APG147`

## Status

Disposition: **amend**. Exit 00192 is allocated to APG147 without renumbering or substitution.  
Outcome: `V0120_B_AGENT_CENTRAL_DISPATCHER_PARITY_MIGRATED` (single-phase execution runtime prototyped in Agent-Central migrated into APGR with 100% behavioral and evidence parity for `agent-phase-request-v1`; 62 runtime modules and 11 generation/profile helpers migrated into APGR `libexec/agent_phase/` and `libexec/`; 30-route execution matrix locked against golden corpus fixture; 10 native `bin/agent-phase-*` command wrappers installed; dedicated `bin/apg-test-dispatcher` qualification harness created; zero external mutations in Agent-Central or JACA; all APGR governance policies green).

Accounting: Historical v0.11 closure accounting remains terminal at 55/55/0/0. Milestone V0120-B delivers substantive architecture transfer and runtime qualification under ADR 0063.

The [evaluation](../../../../evaluations/apg147-v0120-b-agent-central-dispatcher-parity-migration.md) records the full verification and disposition details for APG147 / V0120-B.

## Exact Candidate and Baseline Provenance

- **Candidate APGR Commit**: `10bf3095bf02ce664f6e2bb54ab60c3fb573eb6f` (APG146 / V0120-A).
- **Candidate APGR Tree**: `936794e203fc07cb0717b7f8fa60ff0ff4a5244a`.
- **Source Agent-Central Baseline**: `56e9bb039536dfc8893e61a431681d6a32167b6f` (immutable commit).
- **JACA Reference Baseline**: `08ca2208805cf446bd15da0a6b4c8c58db737587` (unmodified).

## Final Migration Inventory Counts and Dispositions

- **`libexec/agent_phase/`**: 62 single-phase execution modules (all **MIGRATE**, byte-identical to baseline).
- **`libexec/` Helper Modules**: 11 supporting controller-generation and profile compilation modules (**MIGRATE**).
- **Tracked Configuration**: `common/dispatcher/endpoints.toml` (19 endpoints) and `common/dispatcher/routes.toml` (30 routes) (both **MIGRATE**, byte-identical to baseline).
- **Provider Profiles**: 5 Antigravity profiles in `antigravity/profiles/`, 11 Claude profiles in `claude/profiles/`, 7 Codex profile configs in `codex/profiles/` + `README.md`, `claude/model-catalog-v1.json`, and `codex/config.d/170-subagents.toml` (**MIGRATE**).
- **Prompt Guidance**: `antigravity/GEMINI.md`, `claude/CLAUDE.md`, and `codex/AGENTS.md` (**MIGRATE**, 100% byte-identical to baseline, preserving exact prompt transport SHA-256 digests).
- **CLI Wrappers**: 10 native executable wrappers in `bin/agent-phase-*` (`dispatch`, `resolve`, `finalize`, `archive`, `adopt`, `adopt-entry`, `native-git`, `ownership`, `scan-label`, `scan-summary`) + 3 helper CLIs (`agent-controller-generation`, `antigravity-profile`, `claude-profile`) (**MIGRATE**).
- **Test Suites**: 72 test suites in `src/test/dispatcher/` (65 agent-phase suites + 6 controller-generation suites + 1 parity golden corpus suite) (**MIGRATE** / **NEW**).
- **Baseline Provider Helper Test Suites**: 8 suites (`claude/test/` 4, `antigravity/tests/` 3, `codex/tests/` 1) (**DEFER** to V0120-C/D).

## Dispatcher Normalization Rules (N1–N7)

1. **N1: Prompt Transport Byte Parity & Workstation Path Retention**: Standing instructions (`antigravity/GEMINI.md`, `claude/CLAUDE.md`, `codex/AGENTS.md`) retain 100% byte parity with baseline `56e9bb039536dfc8893e61a431681d6a32167b6f`, ensuring exact SHA-256 digest advertisement in prompt transport envelopes. Personal workstation paths present in baseline Claude profiles and helper fallbacks are preserved for V1 baseline parity; general path sanitization and configurable scratch roots are deferred to V0120-C/D.
2. **N2: Single Source of Truth for Provider Intelligence**: Route tables (`common/dispatcher/routes.toml`) store provider and profile only. Model, reasoning effort, and provider flags remain strictly authored within provider profiles (`claude/profiles/`, `antigravity/profiles/`, `codex/profiles/`) and are dynamically read back into the `intelligence` block of `resolved.json`.
3. **N3: Dispatcher / Worker Decoupling**: Phase execution (`libexec/agent_phase/`) is cleanly decoupled from interactive child worker pools (`libexec/agent_workers/`). Worker subsystem integration tests conditionally import or skip `agent_workers` while phase lifecycle execution remains completely standalone.
4. **N4: Test Layout and Governance Sidecar Lane**: Dispatcher test suites are located under `src/test/dispatcher/` with `fixture-or-test` inventory classification. To maintain APGR's mandatory 80% branch, 80% line, and 85% overall coverage policy on core v0.11 modules (`libexec/apg_*.py`) without diluting coverage metrics, migrated dispatcher sources are governed under a distinct `dispatcher_sources` category in `testing/apg-test-inventory.json`.
5. **N5: Strict No-Growth File-Length Allowances**: Nine oversized migrated runtime modules in `libexec/` and eight oversized test suites in `src/test/dispatcher/` receive explicit, sha256-bound entries in `tools/ci/file_length_policy.json` with an absolute no-growth invariant.
6. **N6: Parity Golden Corpus Enforcement**: The entire 30-route dispatch matrix (3 task kinds × 10 execution modes), request grammar, lifecycle stage topology, and intelligence readback are locked against a committed golden fixture (`src/test/dispatcher/fixtures/parity_golden_corpus.json`) with baseline provenance binding and continuously validated via `test_agent_phase_parity_corpus.py`.
7. **N7: Fail-Closed Provider and Active Root Boundaries**: Claude provider construction fails closed when operator-supplied `claude/settings.json` is absent, preserving baseline security invariants without copying user credentials. Controller generation bootstrap retains baseline `56e9bb039536dfc8893e61a431681d6a32167b6f` active-root and generation-store paths (`~/.local/state/agent-central/generations`), defaulting to development worktree execution in APGR unless `AGENT_CENTRAL_ACTIVE_ROOT` is explicitly configured.

## Provider-Specific Qualification Status

- **Codex**: Verified deterministic 30-route resolution, profile compilation, intelligence readback (`gpt-6-astra`, `medium`), and configuration loading. Live provider canary deferred (provider-free deterministic qualification complete).
- **Claude**: Verified deterministic routing, profile compilation, model catalog lookup (`claude-fable-5-1`, `claude-opus-5`), and live renderer formatting. Operates in fail-closed mode when operator `claude/settings.json` is absent, matching baseline security intent without bundling personal host settings. Live provider canary deferred.
- **Antigravity**: Verified deterministic routing, profile compilation, terminal evidence parsing, and terminal output recovery. Live provider canary deferred.

## Reclassification of `scanner.py`

`libexec/agent_phase/scanner.py` was originally classified as `RETAIN` in preliminary planning. Because the single-phase dispatcher runtime directly imports `scanner.py` (`dispatch.py:41`, `cli.py:38`) for prompt telemetry labeling and scan suppression checks during pre-execution sanity verification, `scanner.py` was reclassified to **MIGRATE** and admitted into APGR `libexec/agent_phase/scanner.py` to preserve 100% execution parity.

## Compatibility Handoff Status

Documented in `docs/architecture/v0-12-agent-central-ownership-transition.md` (status: **Proposed**). The proposed Agent-Central forwarding wrapper `bin/agent-phase-dispatch` includes self-path recursion prevention and candidate search across APGR install paths. Configuration override via `APGR_DISPATCHER_CONFIG` is proposed for V0120-C; in V0120-B, discovery defaults strictly to repository-relative `common/dispatcher/`. Zero mutations were made to Agent-Central.

## Known Gaps Explicitly Deferred

The following items are intentionally deferred and tracked for subsequent phases:
- **V0120-C**: Automated CI pipeline execution for `bin/apg-test-dispatcher` sidecar test lane; configuration root override (`APGR_DISPATCHER_CONFIG`); decoupling controller generation store path and active root detection from Agent-Central locations.
- **V0120-C/D**: Positive worker capability branch and upstream worker pool integration; portable Claude operator settings template; standalone provider helper test suite migration.
- **V0120-E**: Go dispatcher surfaces and JACA integration.

## Next Separately Authorized Phase

The next phase is **V0120-C** (`APG148` — Semantic Roles, Flexible Actor Binding, and SQLite Dispatcher Persistence). No V0120-C work is begun in this dispatch.
