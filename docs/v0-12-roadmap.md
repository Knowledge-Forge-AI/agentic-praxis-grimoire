# v0.12 Architecture Transfer and Single-Phase Runtime Roadmap

## Direction and Scheduling Authority

The operator-approved roadmap goal for APGR v0.12 is the transfer, consolidation, and formalization of the lightweight single-phase execution runtime prototyped in Agent-Central into the permanent ownership of APGR.

APGR v0.11.0 publication is terminal, historical, and closed across GitHub Release, Go, PyPI, npm, and Homebrew tap. The [v0.11 closure roadmap](v0-11-roadmap.md) and its [closure ledger](governance/v0-11-closure-ledger.json) are complete and immutable with a 55/55/0/0 closed ledger.

This roadmap (`docs/v0-12-roadmap.md`) establishes the active development line for v0.12.

## Governance Model: Engineering Milestone Progression vs Backlog Closure

A key distinction between v0.11 and v0.12 governs this program:
- **v0.11 was an inherited backlog closure program**: Its primary objective was the terminal accounting and disposition of 55 historical roadmap items, requiring a machine-readable closure ledger (`v0-11-closure-ledger.json`), formal schemas, and mechanical closure checks (`bin/apg-check-roadmap-closure`) enforcing `inherited_roadmap_open_items = 0`.
- **v0.12 is an architecture transfer and feature delivery engineering program**: v0.12 possesses no inherited historical backlog to close. Instead, it is governed by formal Architecture Decision Records (ADRs 0058–0062), discrete staged milestones (V0120-A through V0120-G), bounded execution contracts, provider capability matrices, and rigorous regression test suites (including codified v0.11 hosted repair cases).
- Therefore, v0.12 does NOT instantiate an artificial backlog ledger or clone the v0.11 closure schema. Existing v0.11 closure tooling (`libexec/apg_roadmap_contract.py`) remains dedicated to guarding historical v0.11 terminal accounting and is not coupled to v0.12.

## Substantive Stages

```text
V0120-A: Terminal Reconciliation & Architecture Transfer (Completed — APG146)
   |
   v
V0120-B: Agent-Central Dispatcher Parity Migration (Completed Phase — APG147)
   |
   v
V0120-C: Semantic Roles, Routing Policy Externalization, & SQLite Persistence (Completed — APG148)
   |
   v
V0120-D: Provider Parity Closure & Dynamic Routing Hardening (Completed — APG149)
   |
   v
V0120-E: Go Surfaces & JACA Qualification / Handoff (Completed — APG150)
   |
   v
V0120-E-RECOVERY1-R2: Outbox Projection & Truthful Finalization (Completed — APG150A)
   |
   v
V0120-E-HARDEN1: Provider Failure Feedback & Dynamic Reroute (Completed — APG150B)
   |
   v
V0120-F: Release Hardening, Conditional Nixpkgs, & Integrated Readiness (Completed — APG151)
   |
   v
V0120-F-REPAIR1: V2 Result-Repair Evidence Fail-Closed Hardening (Completed — APG151A)
   |
   v
V0120-G1: Publication Preparation, Live Operator Wiring, & Authority Reconciliation (Completed — APG152)
   |
   v
V0120-G1-REPAIR1: Live Publication Path Reconciliation (Completed — APG152A)
   |
   v
V0120-G2: Public Staging, Hosted Run Execution, Attended Publication, & Terminal Reconciliation (NOT STARTED)
```

### V0120-A — Terminal Reconciliation and Architecture Transfer
- **Phase ID**: `APG146` (Exit 00191)
- **Scope**: Reconcile v0.11.0 terminal publication status across documentation; author foundational architecture decision records (ADRs 0058–0062); establish the v0.12 roadmap; author migration inventories and handoffs for Agent-Central and JACA; codify v0.11 publication repair cases as regression inputs.
- **Exit Criteria**: `V0120_A_ARCHITECTURE_ACCEPTED_AND_HANDOFFS_READY`. Zero code or packaging mutations; pure architecture, documentation, and governance.

### V0120-B — Agent-Central Dispatcher Parity Migration
- **Phase ID**: `APG147` (Exit 00192)
- **Scope**: Direct migration of dispatcher runtime subsystems from Agent-Central (`libexec/agent_phase/`, `common/dispatcher/`, provider launchers, and profile templates) into APGR. Establish native execution parity for `agent-phase-request-v1` in APGR.
- **Deliverables**: Native Python dispatcher modules under APGR `libexec/agent_phase/`; route tables and endpoint configurations under `common/dispatcher/`; profile descriptors under `antigravity/`, `claude/`, `codex/`; dedicated dispatcher qualification harness (`bin/apg-test-dispatcher`) and unit/integration tests under `src/test/dispatcher/`; golden parity corpus fixture and verification suite.
- **Exit Criteria**: `V0120_B_AGENT_CENTRAL_DISPATCHER_PARITY_MIGRATED`. `agent-phase-request-v1` requests execute through APGR with 100% parity against Agent-Central baseline `56e9bb039536dfc8893e61a431681d6a32167b6f`. Zero external mutations; all APGR governance policies green.

### V0120-C — Semantic Roles, Routing Policy Externalization, Request V2, SQLite Persistence, and Initial Dynamic Routing
- **Phase ID**: `APG148` (Exit 00193, ADR 0064)
- **Scope**: Implement Request V2 (`agent-phase-request-v2`) with work-only prompt semantics and strict rejection of embedded `execution_mode` or runtime policy. Externalize routing policy to closed TOML configuration (`[dispatcher.routing].execution_mode`) and CLI flags. Implement decoupled semantic role graph (Planner, Plan Reviewer, Plan Review Disposition, Producer, Work Reviewer, Work Review Disposition, Reviser, Closeout Agent) and flexible actor binding per ADR 0059. Implement lightweight non-daemon SQLite persistence at `<APGR_HOME>/state/dispatcher.sqlite3` for structured tracking of phase runs, bindings, resolutions, observations, candidates, findings, and receipts, while preserving run-owned files on disk for large execution artifacts. Implement initial bounded dynamic role routing (`execution_mode = "dynamic"`) with capability-first fail-closed filtering, reviewer independence invariants, pre-launch route persistence, and deterministic selection.
- **Deliverables**: `RequestV2` schema parser; closed TOML dispatcher configuration parser; semantic role engine and decoupled record serializers; SQLite database migration and storage layer; initial bounded dynamic router and `agent-phase-resolved-v7` contract.
- **Exit Criteria**: `V0120_C_SEMANTIC_ROUTING_AND_PERSISTENCE_READY`. Stage transitions, actor bindings, pre-launch route resolutions, and review dispositions recorded in SQLite; dynamic router resolves capability-eligible, independent routes; merged turns serialize decoupled finding and candidate records; clean V1 backward compatibility and schema validation.

### V0120-D — Provider Parity Closure and Dynamic-Routing Hardening
- **Phase ID**: `APG149` (Exit 00194, ADR 0065)
- **Scope**: Normalize provider capabilities across Codex, Claude, and Antigravity per ADR 0061 and ADR 0065. Close asymmetries in profile compilation, activity-pipe monitoring, and silence thresholds. Harden operational observation collection (`probes.py`), telemetry feeds, and cooldown state machines for dynamic routing. Implement full multi-turn Request V2 execution runtime (`v2_turns.py`, `v2_dispatch.py`) with attempt derivation, read-only posture enforcement, unrecorded mutation detection, nonce-fenced candidate/review parsing, and terminal ZIP archiving.
- **Deliverables**: Normalized provider execution adapters; operational observation telemetry monitors; provider conformance verification matrix (`provider-conformance-matrix.json` and `.md`); full V2 multi-turn execution coordinator and receipt archiver.
- **Exit Criteria**: `V0120_D_PROVIDER_PARITY_AND_DYNAMIC_ROUTING_HARDENED`. Full provider conformance matrix verified (22 evaluated rows across 3 providers); normalized timeout and liveness controls across all supported providers; fail-closed behavior on unsupported provider capabilities; multi-turn execution loops with review parsing, disposition transitions, attempt derivation, and tamper detection qualified across comprehensive deterministic tests.

### V0120-E-REPAIR1 — Request V2 Live-Display Contract and Pre-Launch Reconciliation Repair
- **Exit ID**: `Exit 00195` (Narrow post-V0120-D runtime repair / V0120-E bootstrap blocker)
- **Scope**: Repair Request V2 live-display contract mismatch (`Display.stage_started(index, stage, role, endpoint, stage_count=5)`) in `libexec/agent_phase/v2_turns.py`; audit all V2 display integration calls (`stage_started`, `stage_output`, `stage_notice`, `stage_finished`, `stage_failed`); harden pre-launch attempt error boundary so that failed attempts and semantic responsibilities are durably terminalized as `failed_pre_launch` without fabricating execution receipts or exit codes; preserve historical failed run records without mutation; add focused deterministic regression tests.
- **Deliverables**: Hardened `v2_turns.py` and `v2_dispatch.py`; dedicated regression suite `src/test/dispatcher/test_agent_phase_v2_display_repair.py`; zero V0120-E product mutation.
- **Exit Criteria**: `V0120_E_BOOTSTRAP_DISPLAY_REPAIR_COMPLETE`. All 10 contract test cases pass; full V2 and V1 dispatcher regression suites pass.

### V0120-E — Go Surfaces and JACA Qualification / Handoff
- **Phase ID**: `APG150` (Exit 00196, ADR 0066)
- **Scope**: Export reusable public Go domain packages (`phase`, `routing`, `evidence`, `candidate`, `provider`) per ADR 0058, ADR 0066, and JACA handoff specifications. Provide integration fixtures and qualification harness for JACA XO consumption. Enforce zero duplicate Go `ExecutePhase` runtime; APGR Python runtime owns standalone execution while JACA retains XO runtime. Enforce work-only Request V2 contract and eliminate subprocess coupling per JACA §18.12.
- **Deliverables**: Public Go API for single-phase request modeling, pure deterministic routing resolution, candidate identity and artifact manifest validation, review evidence handling, and static provider capability matrix; dual-language golden vector conformance corpus (`testing/fixtures/conformance/`) and generator; AST-based Go API manifest; disposable JACA XO consumer qualification fixture (`testing/fixtures/jaca_consumer`).
- **Exit Criteria**: `V0120_E_GO_SURFACES_AND_JACA_HANDOFF_COMPLETE`. All Go packages pass `go test ./...` and `go vet ./...`; cross-language conformance suite passes; JACA consumer qualification fixture passes in isolated lane; zero JACA dependencies imported into APGR; JACA policy authority preserved intact.

### V0120-E-RECOVERY1-R2 — Request V2 Outbox Projection and Truthful Operational Finalization
- **Phase ID**: `APG150A` (Exit 00197)
- **Scope**: Complete operational recovery of predecessor Request V2 runtime state by implementing the operator outbox projection engine and truthful Git finalization:
  - Implement operator-facing outbox projection engine (`libexec/agent_phase/outbox_projection.py`) projecting navigation symlinks and atomic locator metadata (`agent-phase-dispatch-locator-v1`) into `<outbox_root>/phase-dispatch/<project>/<phase_id>/` without modifying canonical storage under `<APGR_HOME>/state/`.
  - Enforce outbox symlinks as navigation only and refuse their use as resume or continuation authority (`--resume` and `--continue-from` reject symlinks).
  - Implement strict Turn 5 closeout result parsing and truthful Git finalization (`finalize_repository`) across `checkpoint`, `commit-local`, and `publish` policies.
  - Implement atomic two-tier archive digest sealing (asymmetric in-archive null/pending hash vs verified post-sealing SHA-256 locator identity).
  - Support pre-existing entry candidate adoption (`--entry-adoption`) across Request V2 dispatches, rejecting unadopted entry dirt overlaps.
  - Deliver comprehensive qualification test suites: `src/test/dispatcher/test_agent_phase_v2_outbox_projection.py` (11 tests) and `src/test/dispatcher/test_agent_phase_v2_finalization.py` (9 tests).
- **Deliverables**: Hardened `outbox_projection.py`, `v2_dispatch.py`, `v2_turns.py`, `v2_prompts.py`, `cli.py`, and `entry_adoption.py`; dedicated regression test suites; zero daemon or background process introduction; full Go, Python, and JACA XO qualification pass.
- **Exit Criteria**: `V0120_E_RECOVERED_WITH_OUTBOX_AND_TRUTHFUL_FINALIZATION`. Full dispatcher test suite passes (1877 passed); Go test suite passes; record identity, roadmap closure, file length policy, generated drift, and prompt defense gates green.


### V0120-E-HARDEN1 — Provider Failure Feedback and Dynamic Reroute
- **Phase ID**: `APG150B` (Exit 00198, ADR 0067)
- **Scope**: Provider-feedback and dynamic-reroute hardening milestone. Resolve the post-recovery Codex usage-limit exhaustion dogfood observation by implementing high-confidence provider quota failure classification, sanitized evidence payloads, SQLite persistence schema v2 (`invocation_observation_relations`), and bounded dynamic rerouting ($M=3$) with strict substantive work fence without credential scraping or private provider state access. Decouple generic agent JSON/JSONC syntax parsing from downstream semantic interpretation. Align APGR V2 operator outbox projections with current Agent-Central layout (`<outbox_root>/<project>/<phase-id>/`).
- **Reference Implementation Doctrine**: Agent-Central (`~/projs/agent-central`) remains an active, supported reference implementation and is NOT being decommissioned. APGR now owns and evolves its copy without immediate Agent-Central decommissioning, preserving reference behavior by default with deliberate, documented, and tested improvements.
- **Deliverables**: `failure_classifier.py`, `persistence_feedback.py`, `v2_reroute.py`, updated `v2_turns.py`, `outbox_projection.py`, `feedback_scenarios.py`, and comprehensive qualification test suites.
- **Publication Accounting**: Joint publication across initial partial commit `0670d497` (modifying `docs/status/README.md`) and direct-descendant FINAL2 commit publishing the remaining 28 adopted candidate paths. Local recovery refs are preserved outside main ancestry.
- **Exit Criteria**: `V0120_E_PROVIDER_FEEDBACK_AND_DYNAMIC_REROUTE_HARDENED`. High-confidence classification and sanitization; schema v2 idempotent tracking; bounded reroute on zero-substantive-work failures; terminal failure on substantive work; cross-language golden vector agreement; full dispatcher test suite pass. Milestone V0120-F does not duplicate the Codex provider-result feedback work and remains NOT STARTED.


### V0120-F — Release Hardening, Conditional Nixpkgs, and Integrated Readiness
- **Phase ID**: `APG151` (Exit 00199, ADR 0062)
- **Scope**: Implement operator hardening invariants from ADR 0062: numeric draft release ID binding, strict release authority checking, trusted PyPI publishing alignment, npm distribution state machine, resumable channel execution receipts, and automated Homebrew formula generation. Implement a comprehensive regression test suite covering all 13 hosted CI repair cases (`R1`–`R13`, as `REG-R1`–`REG-R13`) and all 12 v0.11 publication findings (`F1`–`F12`, covered through the independent `REG-P1`–`REG-P13` namespace per the traceability table in `docs/architecture/v0-12-v011-publication-regression-inputs.md` §4). Disposition Nixpkgs based on Knowledge Forge AI organizational precedent (Theme Forge). Wire Request V2 Turn 5 into the mature formatting-only terminal result-repair path (Recovery1) with reference Agent-Central parity, resolving the root cause (`RESULT_MISSING_FENCE`) of historical failed run `apgr-run-v2-implementation_testing-20260918T003756Z-0774ecbe` (preserved as immutable evidence). Zero-debt technical readiness qualification.
- **Deliverables**: Hardened candidate and lineage tooling (`libexec/apg_public_release.py`); resumable Release Operator (`private/releases/v0.12.0/release_operator/`); release operator dry-run qualification suite (`private/releases/v0.12.0/test_release_operator_dry_runs.py`); hosted-CI regression test suite (`private/releases/v0.12.0/test_hosted_ci_regressions.py`); release readiness matrix and mechanical checker (`testing/release/release-readiness-matrix.json`, `testing/release/check_release_matrix.py`, `bin/apg-check-release-matrix`); Nixpkgs conditional evaluation and disposition record (`docs/evaluations/apg151-v0120-f-nixpkgs-conditional-disposition.md`); Request V2 result repair engine (`libexec/agent_phase/v2_repair.py`, `v2_turns.py`, `v2_dispatch.py`) and regression test suite (`src/test/dispatcher/test_agent_phase_v2_result_repair.py`).
- **Exit Criteria**: `V0120_F_RELEASE_HARDENING_AND_INTEGRATED_READINESS_COMPLETE`. Complete technical release readiness verified; all 13 hosted CI regressions (REG-R1..REG-R13) and 13 publication operator invariants (REG-P1..REG-P13) passing 100%; release operator validated against dry-run fixtures; Nixpkgs evaluated and dispositioned as condition-not-met/deferred per TFSB70B precedent; candidate & lineage tooling extended for v0.12.0; Request V2 result repair parity verified. Milestone V0120-G remains NOT STARTED.

### V0120-F-REPAIR1 — V2 Result-Repair Evidence Fail-Closed Hardening
- **Phase ID**: `APG151A` (Exit 00200, ADR 0062)
- **Scope**: Narrow post-V0120-F dispatcher-integrity repair resolving manager post-publication review findings on `libexec/agent_phase/v2_repair.py`. Eliminate broad exception swallowing in repair attempt and artifact persistence; enforce exact byte identity across all repair artifacts; delete synthetic repair-completion fallback for runner returning `None` or unsupported shapes; protect semantic attempt lineage and route-attempt numbering contracts by distinguishing auxiliary attempts via `attempt_kind="auxiliary"`; rerun complete dispatcher test suite `bin/apg-test-dispatcher -n auto` to close the post-repair full qualification gap. Agent-Central remains active and supported. Milestone V0120-G remains NOT STARTED.
- **Deliverables**: Hardened V2 result-repair adapter (`libexec/agent_phase/v2_repair.py`); auxiliary attempt accounting and schema migration (`libexec/agent_phase/persistence.py`, `v2_turns.py`); comprehensive deterministic regression test suite (`src/test/dispatcher/test_agent_phase_v2_result_repair.py`); Exit 00200 record (`docs/status/2026/09/17/00200-apg151a-v0120-f-repair1-result-repair-evidence-hardening-exit.md`).
- **Exit Criteria**: `V0120_F_RESULT_REPAIR_EVIDENCE_HARDENED`. All fail-closed persistence paths verified; artifact byte identity verified; runner fallback deleted; lineage protection verified; 15/15 focused result-repair tests passing; full dispatcher regression passing; Milestone V0120-G remains NOT STARTED.

### V0120-G1 — Publication Preparation, Live Operator Wiring, and Authority Reconciliation
- **Phase ID**: `APG152` (Exit 00201, ADR 0068)
- **Scope**: Prepare public release candidate and release operator for v0.12.0. Register deterministic release epoch `1789689600` (`2026-09-18T00:00:00Z`). Reconcile release authority with advanced public `main` (`7c77619cdc54f1f6d87c36eb20a11ea0b30a2441`) via linear ancestor verification (`git merge-base --is-ancestor`) in `apg_public_release.py` and `apg_staging_correction.py`. Remove stale PR association check from `.github/workflows/release.yml` and wire GitHub compare API query asserting `(ahead|identical)` and `behind_by == 0`. Implement and unit-test live channel adapters (`LiveGitHubApi`, `LiveGoProxy`, `LivePyPiApi`, `LiveNpmRegistry`, `LiveTapAdapter`). Build comprehensive immutable operator packet in `private/releases/v0.12.0/packet/`. Maintain ZERO external release mutations (no git push, PR, tag, GitHub Release, PyPI, npm, or Homebrew mutations).
- **Deliverables**: Updated `VERSION` (0.12.0); candidate release notes (`release/v0.12.0-notes.md`); reconciled `apg_public_release.py`, `apg_staging_correction.py`, and `release.yml`; live channel adapters and tests (`test_live_operator_adapters.py`); complete operator packet (`operator-packet.json`, `operator-packet.sha256`, `preflight.py`, `execute.py`, `reconcile_postmerge.py`, `stage_operator.py`, `build_assets.py`, `frozen-input-digests.json`, `evidence-index.json`, `command-receipts.json`, `release-notes.md`, `README.md`); ADR 0068 and Exit 00201 records.
- **Exit Criteria**: `V0120_G1_PUBLICATION_PREPARATION_AND_OPERATOR_WIRING_COMPLETE`. Zero external mutations; all unit, integration, and dry-run test suites passing 100%; preflight passing online and offline. Milestone V0120-G2 remains NOT STARTED.

### V0120-G1-REPAIR1 — Live Publication Path Reconciliation
- **Phase ID**: `APG152A` (Exit 00202)
- **Scope**: Narrow post-V0120-G1 publication-path repair before any public v0.12 mutation. Resolve all 19 findings across Scopes A–S: align current-version test assertions to v0.12.0; update public CI and package qualification version gates; reconcile release workflow review verification step to accept approved review or authorized governance waiver in immutable PR/commit record; implement canonical manifest view derivation from flat release deliverables; integrate G2 receipt into execute/runner entrypoints; harden live channel adapters (`LiveGitHubApi` direct REST upload without `gh release upload`, `LiveGoProxy` attended backoff, `LivePyPiApi` bounded workflow observation with conjunctive binding, `LiveNpmRegistry` registry pinning, `LiveTapAdapter` formula stem normalization and fail-closed tools); update Homebrew formula for npm platform tarballs; refactor preflight verifier for offline/preview/live-confirmed modes; enforce clean public checkout and external empty output in asset builder; implement 8 attended G2 commands in `stage_operator.py` with `--force-with-lease` bound to stale staging tip; clarify inter-cycle staging replacement in ADR 0057; establish 18-step G2 campaign test suite; maintain strict ZERO public release mutations.
- **Deliverables**: Hardened `live.py`, `homebrew.py`, `preflight.py`, `build_assets.py`, `stage_operator.py`, `runner.py`, `execute.py`, `authority.py`; updated tests (`test_live_operator_adapters.py`, `test_g2_mocked_campaign.py`); updated operator packet (`operator-packet.json`, `operator-packet.sha256`, `frozen-input-digests.json`, `evidence-index.json`, `README.md`); ADR 0057 amendment; Exit 00202 record (`docs/status/2026/09/18/00202-apg152a-v0120-g1-repair1-live-publication-path-reconciliation-exit.md`).
- **Exit Criteria**: `V0120_G1_REPAIR1_LIVE_PUBLICATION_PATH_RECONCILED`. Zero external mutations; all unit, integration, release dry-run, and mocked campaign test suites passing 100%; preflight passing; file length policy green; Milestone V0120-G2 remains NOT STARTED.

### V0120-G1-REPAIR2 — Real-Schema and Live Fail-Closed Release Path Hardening
- **Phase ID**: `APG152B` (Exit 00203)
- **Scope**: Final private repair of V0120-G1 before any v0.12 public mutation. Resolve manager review advisory findings: fix canonical manifest field contract to consume real `size_bytes` schema (without competing `size` intrusion) from `apg_distribution_candidate` producer; normalize PyPI real response digest (`file["digests"]["sha256"]`); harden `stage_operator.py` with fail-closed authority reads on staging/main drift and malformed PR JSON; enforce idempotent create-or-reuse in `open-pr`; explicitly bind bounded governance waiver markers (`<!-- BEGIN_GOVERNANCE_WAIVER -->` / `<!-- END_GOVERNANCE_WAIVER -->`) in PR verification; bind full hosted workflow run, jobs, artifact IDs, and aggregate matrix qualification evidence into `check-pr` and `g2-staging-receipt.json`; implement attended guarded annotated tag command `stage_operator.py create-tag`; implement stage-aware preflight bindings (validating G2 receipt, peeled tag commit, public main, assets/manifest, GitHub release, PyPI/npm absence); restore proven v0.11 Homebrew package installation contract for npm platform tarballs; enforce external operator state root isolation outside git checkouts; create end-to-end real schema manifest test (`test_real_schema_manifest_e2e.py`); update packet README with complete non-contradictory 18-step G2 runbook; maintain strict ZERO public mutations.
- **Deliverables**: Hardened `stage_operator.py`, `preflight.py`, `execute.py`, `runner.py`, `channels/live.py`, `channels/homebrew.py`, `channels/pypi.py`, `channels/github_release.py`, `channels/npm.py`, `authority.py`; real-schema end-to-end test suite (`test_real_schema_manifest_e2e.py`); updated tests (`test_g2_mocked_campaign.py`, `test_live_operator_adapters.py`); updated operator packet (`operator-packet.json`, `frozen-input-digests.json`, `README.md`); Exit 00203 record (`docs/status/2026/09/18/00203-apg152b-v0120-g1-repair2-real-schema-and-live-fail-closed-exit.md`).
- **Exit Criteria**: `V0120_G1_REAL_SCHEMA_AND_LIVE_FAIL_CLOSED_READY`. Zero external mutations; all unit, integration, release dry-run, real-schema manifest, and mocked campaign test suites passing 100%; release matrix checker clean; file length policy green; Milestone V0120-G2 remains NOT STARTED.

### V0120-G2 — Public Staging, Hosted Run Execution, Attended Publication, and Terminal Reconciliation
- **Scope**: Execute public staging candidate build, public PR creation, hosted CI verification, squash merge to public `main`, postmerge source qualification (`reconcile_postmerge.py`), tagging `v0.12.0`, and multi-channel publication across GitHub Releases, Go, PyPI, npm, and Homebrew (plus Nixpkgs if admitted in V0120-F).
- **Status**: **NOT STARTED**. Strictly reserved for subsequent authorized release execution.
- **Deliverables**: Published v0.12.0 release across all confirmed channels; multi-channel publication receipts; terminal postmerge proof; terminal reconciliation documentation.
- **Exit Criteria**: All published channels verified; public readback matches distribution manifest; terminal exit record published.
