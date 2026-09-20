# APG159 — v0.13.0 Foundation Architecture and Evaluation Data Exit

Phase ID: `APG159`
Exit ID: `Exit 00205`
Roadmap Milestone: `V0130-A`
Governing Decisions: [ADR 0069](../../../../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md), [ADR 0070](../../../../adr/2026/09/0070-configurable-review-stage-mutation-policy.md), [ADR 0071](../../../../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md), [ADR 0072](../../../../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md), [ADR 0073](../../../../adr/2026/09/0073-unified-skill-catalog-and-deterministic-resolution.md), [ADR 0074](../../../../adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md)
Exit Target: `V0130_A_DOCTRINE_ACCEPTED_AND_BASELINE_FROZEN`

---

## 1. Status and Disposition

- **Disposition**: **accept**
- **Milestone Outcome**: `V0130_A_DOCTRINE_ACCEPTED_AND_BASELINE_FROZEN`
- **Execution Boundary**: Confined strictly to architecture documentation, specifications, and non-executable evaluation fixtures in an isolated clone (`v0.13.0/apg159-foundation`). Zero runtime code, Python/Go packages, lockfiles, CLI entrypoints, skill bodies, or Git commits/pushes.

---

## 2. Scope Delivery

### 2.1 Current Truth & v0.12 Reconciliation
- Verified multi-channel v0.12.0 publication reality: GitHub Release `392534425` (published 2026-09-20 18:40:56 UTC), PyPI (`0.12.0`), npm (`@knowledge-forge-ai/apgr@0.12.0`), Go module proxy (`v0.12.0`), and Homebrew tap formula (`0.12.0`).
- Accounted forward for seven post-G1 commits (APG153E, APG153G, APG153J, APG155B, APG156A, APG156C, APG158A) in `docs/architecture/v0-12-forward-reconciliation.md` without retroactively rewriting historical exit records.
- Maintained durable semantic references publicly, retaining exact hashes in `private/v0.13.0/v0-12-reconciliation-evidence.json`.
- Excluded unadopted historical v0.8.1 evidence present in the source checkout.
- Evaluated the G2 terminal gate: satisfied for documentation milestone V0130-A, remaining active for code milestones B–I.

### 2.2 Adopted v0.13 Program Roadmap
- Authored `docs/v0-13-roadmap.md` defining milestones V0130-A through V0130-I with explicit owners, dependencies, and stop boundaries.
- Formalized five core themes: T1 (Runtime Doctrine), T2 (Review-Stage Mutation Policy), T3 (Operator Home & Hosting Seams), T4 (Optional RTK Integration), and T5 (Adaptive Context Resolution).

### 2.3 Cohesive ADR Suite (ADRs 0069–0074)
- **ADR 0069**: Program Scope and Forward Dispatcher Reference Doctrine (superseding ADR 0067 §8; reversible owner-executed Agent-Central transition).
- **ADR 0070**: Configurable Review-Stage Mutation Policy (shipped `worktree = "warn"`, block-only index/HEAD, `subject_drift_observed = true`, closer-owned path disposition).
- **ADR 0071**: APGR Home Layout and Portable Hosting Seams (`apgr-home-layout-v1`, `--apgr-home` > `APGR_HOME` > `~/.apgr`, zero `JACA_HOME` coupling, custom Go TOML parser deferred).
- **ADR 0072**: Optional RTK Integration as Declared Metadata and Conditional Instruction Slices (`required = false`, read-only doctor, canonical skill within discovery ceiling, corrected static baseline).
- **ADR 0073**: Unified Skill Catalog, Sources, Namespaces, and Deterministic Resolution (`apgr:`, `project:`, `user:`, generated descriptors, deterministic ordering).
- **ADR 0074**: Context Plan, Byte Budgets, Late Acquisition, and Bounded APGR MCP Adapter (per-binding plans, stdio MCP adapter amending `APGR-D8` while keeping general-suite prohibition, mid-turn recovery without replay).

### 2.4 Technical Specifications and Qualification Framework
- `docs/specs/apgr-home-layout-v1.md`: Directory layout, permissions, precedence, migration rules, operator settings isolation.
- `docs/specs/review-mutation-seam-inventory.md`: V1/V2 drift seams, distinct HEAD code `READ_ONLY_STAGE_MUTATED_HEAD`, closer disposition rules, semantic interpretation analysis.
- `docs/specs/provider-role-qualification-plan.md`: Four capability axes across four evidence tiers, preserving Antigravity static fallback.
- `docs/evaluations/apg159-agent-central-dispatcher-differences.md`: Filename- and byte-level inventory (16 APGR-only modules, 44 byte-identical and 18 differing shared modules; both available Agent-Central checkouts at parity baseline `56e9bb0` with zero post-baseline dispatcher commits). Content review of the 18 differing modules and the `V0130_I_NO_AGENT_CENTRAL_DISPATCHER_DEPENDENCY` gate remain pending for V0130-I; this phase does not claim the gate.
- `docs/specs/review-mutation-seam-inventory.md` §4.3: bounded read-only sample of retained REVIEWIMMUT1 invalidation evidence (20 files, 1 distinct event); the invalidated review's response was not retained, so the load-bearing-edit question is open and V0130-B must retain reviewer responses for observed-drift stages.

### 2.5 Baseline Context Accounting & 15 Frozen Evaluation Scenarios
- `docs/evaluations/apg159-context-footprint-baseline.md`: Footprint baseline; discovery ceiling measured at 11,142 bytes + 268 `rtk-command-proxy` = 11,410 bytes <= 11,507 limit (97 bytes headroom). Provider instruction files recorded as APGR-side file bytes with command provenance (Codex 7,939 B / RTK 240 B; Claude 11,071 B / RTK clause 35 B, no separable slice; Antigravity 4,238 B / RTK 1,041 B); delivered provider bytes and MCP overhead are `unavailable`. No control-baseline or delivery claim is made before V0130-D.
- `testing/fixtures/context-eval/context-eval-metrics-and-oracles.json`: Frozen target metrics and quality oracles.
- `testing/fixtures/context-eval/`: 15 non-executable scenario definitions (5 calibration, 10 acceptance including Scenario 13 pre-launch no-MCP fallback).
- `docs/evaluations/apg159-skill-promotion-cost-ranking.md`: Derived ranking across seven evidence categories establishing primary tranche: `go-language-profile`, `go-test-profile`, `pytest-test-profile`, `markdown-language-profile`, `sqlite-database-profile`.

### 2.6 Discrepancies and Handoffs
- Dispositioned D1 through D12 and seven manager findings in `docs/evaluations/apg159-source-discrepancies-and-findings.md`; §3 of that file records the five work-review corrections (W1–W5) applied at closeout.
- Evaluated Caveman patterns in `docs/governance/optional/caveman-pattern-evaluation.md` (clean-room pattern adoption; APG141 rejection stands).
- Updated existing and authored new unaccepted handoffs for JACA and Agent-Central.

---

## 3. Verification and Checks

All required read-only mechanical checks executed and passed, re-run at closeout after the work-review corrections:
1. `bin/apg-check-record-identity --format json`: PASS (74 ADRs, 203 exits, 203 phase IDs; next ADR 0075, next exit 00206).
2. `bin/apg-check-record-identity --expect-allocated APG159`: PASS.
3. `bin/apg-check-skill-library`: PASS (45 canonical skills, 45 catalog rows, 45 projections).
4. `bin/apgr skills context-report`: PASS (11,142 description bytes).
5. `bin/apg-check-roadmap-closure`: PASS (55/55 historical closed rows).
6. `bin/apg-check-phase-commit-message --phase APG159 --message-file private/v0.13.0/apg159-commit-message.txt`: PASS.
7. `git diff --check`: PASS; trailing-whitespace and final-newline scan of every untracked phase file: clean.
8. JSON parse of all 16 `testing/fixtures/context-eval/*.json` files and the private reconciliation evidence: all parse.
9. Private host-path scan of the publishable phase documents: clean after closeout.

---

## 4. Not Run and Hard Stop Boundary

- Full runtime pytest suite, Go compiler tests, and package builds were **not run**: authorized scope is strictly documentation and non-executable fixture data.
- Live provider benchmark sessions were **not run**: benchmark evaluation is scheduled for milestone V0130-H against the frozen scenario corpus.
- Zero git commits, branch creations, tags, or pushes were performed: dispatcher owns local commit finalization.

---

## 5. Next Authorized Phase

Next authorized milestone is **V0130-B** (Review-Stage Mutation Policy), gated on clean G2 terminal reconciliation of the v0.12.0 release.
