# ADR 0063 — Agent-Central Single-Phase Dispatcher Parity Migration and Normalization

- Status: Accepted (Amended in Part by APG153J)
- Date: 2026-09-16
- Phase: APG147 (Roadmap Stage: V0120-B)

## Context

Under the v0.12 Architecture Transfer roadmap (`docs/v0-12-roadmap.md`), APGR assumes permanent ownership of the lightweight single-phase execution runtime prototyped in Agent-Central. The initial phase of this roadmap, Milestone `V0120-A` (Phase `APG146`), reconciled v0.11 publication, authored foundational ADRs 0058–0062, and established the migration inventory and handoff boundaries.

Milestone `V0120-B` (Phase `APG147`) requires the direct, full-fidelity migration of the single-phase runtime subsystems into APGR with 100% behavioral and evidence parity for `agent-phase-request-v1`. This migration must not mutate Agent-Central or JACA repositories, must respect APGR's strict CI/Python governance gates, and must eliminate prototype host couplings while preserving exact protocol and lifecycle semantics.

## Decision

1. **Direct Parity Migration**:
   - The runtime modules from Agent-Central `libexec/agent_phase/` (62 modules) and supporting generation/profile helpers (11 modules) are migrated directly into APGR `libexec/agent_phase/` and `libexec/`.
   - Dispatcher endpoint and route definitions are ported to `common/dispatcher/endpoints.toml` and `common/dispatcher/routes.toml`.
   - Provider profile definitions and templates are ported to `antigravity/profiles/`, `claude/profiles/`, and `codex/profiles/`.
   - Native APGR CLI launchers are installed under `bin/agent-phase-*` (`bin/agent-phase-dispatch`, `bin/agent-phase-resolve`, `bin/agent-phase-finalize`, `bin/agent-phase-archive`, `bin/agent-phase-adopt`, `bin/agent-phase-adopt-entry`, `bin/agent-phase-native-git`, `bin/agent-phase-ownership`, `bin/agent-phase-scan-label`, `bin/agent-phase-scan-summary`).

2. **Dispatcher Normalization Rules (N1–N7)**:
   - **N1: Prompt Transport Byte Parity & Workstation Path Retention**: Standing instructions (`antigravity/GEMINI.md`, `claude/CLAUDE.md`, `codex/AGENTS.md`) retain 100% byte parity with baseline `56e9bb039536dfc8893e61a431681d6a32167b6f`, ensuring exact SHA-256 digest advertisement in prompt transport envelopes. Personal workstation paths present in baseline Claude profiles and helper fallbacks are preserved for V1 baseline parity; general path sanitization and configurable scratch roots are deferred to V0120-C/D.
   - **N2: Single Source of Truth for Provider Intelligence**: Endpoint routes (`common/dispatcher/routes.toml`) store provider and profile only. Model, reasoning effort, and provider flags remain strictly authored within provider profiles (`claude/profiles/`, `antigravity/profiles/`, `codex/profiles/`) and are dynamically read back into the `intelligence` block of `resolved.json`.
   - **N3: Dispatcher / Worker Decoupling**: Phase execution (`libexec/agent_phase/`) is cleanly decoupled from interactive child worker pools (`libexec/agent_workers/`). Worker subsystem integration tests conditionally import or skip `agent_workers` while phase lifecycle execution remains completely standalone.
   - **N4: Test Layout and Governance Sidecar Lane**: Dispatcher test suites are located under `src/test/dispatcher/` with `fixture-or-test` inventory classification. To maintain APGR's mandatory 80% branch, 80% line, and 85% overall coverage policy on core v0.11 modules (`libexec/apg_*.py`) without diluting coverage metrics, migrated dispatcher sources are governed under a distinct `dispatcher_sources` category in `testing/apg-test-inventory.json`.
   - **N5: Strict No-Growth File-Length Allowances**: Nine oversized migrated runtime modules in `libexec/` and eight oversized test suites in `src/test/dispatcher/` receive explicit, sha256-bound entries in `tools/ci/file_length_policy.json` with an absolute no-growth invariant.
   - **N6: Parity Golden Corpus Enforcement**: The entire 30-route dispatch matrix (3 task kinds $\times$ 10 execution modes), request grammar, lifecycle stage topology, and intelligence readback are locked against a committed golden fixture (`src/test/dispatcher/fixtures/parity_golden_corpus.json`) with baseline provenance binding and continuously validated via `test_agent_phase_parity_corpus.py`.
   - **N7: Fail-Closed Provider and Active Root Boundaries**: Claude provider construction fails closed when operator-supplied `claude/settings.json` is absent, preserving baseline security invariants without copying user credentials. Controller generation bootstrap retains baseline `56e9bb039536dfc8893e61a431681d6a32167b6f` active-root and generation-store paths (`~/.local/state/agent-central/generations`), defaulting to development worktree execution in APGR unless `AGENT_CENTRAL_ACTIVE_ROOT` is explicitly configured.

3. **Reclassification of `scanner.py`**:
   - `libexec/agent_phase/scanner.py` was originally classified as `RETAIN` in preliminary planning. Because the dispatcher invokes scanner checks during pre-execution sanity verification, `scanner.py` is reclassified to `MIGRATE` and admitted into APGR `libexec/agent_phase/scanner.py`.

4. **Dedicated Dispatcher Qualification Harness**:
   - A dedicated runner `bin/apg-test-dispatcher` is established to execute dispatcher unit, integration, and adoption tests in parallel via `pytest-xdist`, ensuring rapid qualification without altering standard APGR `bin/apg-test` invocations.

## Consequences

- APGR possesses full autonomous ownership of the single-phase execution engine.
- Zero mutations were made to external repositories (`agent-central`, `jaca`).
- APGR's existing CI policy gates (`bin/apg-test policy`, `file_length_policy.py`, `python_inventory.py`) remain completely green and satisfied.
- Migrated dispatcher runtime modules and test suites run via dedicated test runner `./bin/apg-test-dispatcher` and are excluded from core `apg-test` coverage gates under the `dispatcher_sources` inventory category; automated CI pipeline execution for the dispatcher test lane is scheduled for integration in V0120-C.
- Subsequent milestone `V0120-C` can cleanly build the decoupled semantic role graph and SQLite state persistence upon this stable, verified parity foundation.

## Forward Amendment: APG153J Release Portability

APG153J closes the path-sanitization and configurable-scratch debt for v0.12.
Claude profiles now declare only `user-home` and `scratch` directory tokens.
The launcher resolves home at runtime and uses `APGR_AGENT_SCRATCH_ROOT` when
configured, otherwise `<APGR_HOME>/scratch` (`~/.apgr/scratch` by default).
Configured directories must already exist; only the bounded default APGR home
and scratch children may be created with restrictive permissions. Directory
validation rejects symlinks, unsafe ownership/modes, and relative paths; shell
expansion is never used. No external controller runtime dependency is introduced.

Standing guidance uses configured scratch and operator-supplied user canon
outside APGR ownership. Pre-release documentation uses repository-relative links
and project identities. APG147 N1 remains historical migration provenance, not
current-release byte identity: APG147 retained workstation paths at its exit.
Prompt envelopes continue advertising the actual standing-instruction bytes and
their SHA-256 digest. Route/model/effort, permission modes, isolated settings, and
the parity corpus's behavioral comparisons remain unchanged.
