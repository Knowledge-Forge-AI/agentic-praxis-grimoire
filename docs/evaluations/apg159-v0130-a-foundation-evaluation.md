# APG159 — v0.13.0 Foundation Architecture and Evaluation Data

## Scope and status

- **Phase ID**: `APG159`
- **Roadmap Milestone**: `V0130-A`
- **Governing Document**: Manager Disposition on APGR v0.13.0 (2026-09-20)
- **Disposition**: **amend** (plan-review and work-review findings incorporated; see `apg159-source-discrepancies-and-findings.md` §3 for the work-review correction trail)
- **Outcome**: `V0130_A_DOCTRINE_ACCEPTED_AND_BASELINE_FROZEN`
- **Hard Authority Boundary**: Pure architecture, documentation, and non-executable fixture data. Zero runtime code, Python/Go packages, lockfiles, CLI entrypoints, skill bodies, or Git commits/pushes.

---

## 1. Truthful Current-State and Multi-Channel v0.12.0 Reconciliation

APG159 replaces the stale proposal premise that "v0.12 is not published" with verified multi-channel registry truth:
- **GitHub Releases**: Observed release ID `392534425`, tag `v0.12.0`, published at 2026-09-20 18:40:56 UTC.
- **PyPI**: Version `0.12.0` uploaded at 2026-09-20 18:56:06 UTC (3 binary wheels + 1 sdist).
- **npm**: Scoped package `@knowledge-forge-ai/apgr@0.12.0` published.
- **Go Module Proxy**: Tagged module `github.com/knowledge-forge-ai/agentic-praxis-grimoire@v0.12.0` available.
- **Homebrew Tap**: Formula `agentic-praxis-grimoire.rb` in `Knowledge-Forge-AI/homebrew-tap` at version `0.12.0`.

### Forward Accounting of Post-G1 Development Commits
Between historical milestone V0120-G1 closure (Exit 00204, Phase APG152C) and the start of V0130-A, seven development commits landed in the private development branch:
- APG153E (Core unit coverage gate closure)
- APG153G (macOS 27 Firefox deferral binding)
- APG153J (Public portability gate closure)
- APG155B (Hosted PR repair qualification)
- APG156A (Candidate qualification regressions repair)
- APG156C (Release-matrix projection-awareness)
- APG158A (Supervisor cleanup repair qualification)

These commits are accounted for forward in `docs/architecture/v0-12-forward-reconciliation.md` without rewriting historical exit records or roadmaps. Exact commit hashes and hosted run IDs are retained in publication-excluded reconciliation evidence to adhere to durable-reference rules; this record does not depend on them. (APG159A corrected three of those identities from native Git objects.)

### Source vs Clone Relationship
- The read-only source development checkout (at APG158A) contains untracked historical v0.8.1 packaging metadata and receipts (`private/releases/v0.8.1/correction1-evidence/`), which remain unadopted.
- The isolated foundation clone on branch `v0.13.0/apg159-foundation` started clean from the same committed APG158A source; exact host paths are retained in the launcher evidence, not here.

### G2 Terminal Gate Evaluation
The G2 terminal reconciliation gate is cleared for documentation milestone V0130-A. It remains an active hard prerequisite before beginning any code milestone (V0130-B through V0130-I).

---

## 2. Amended v0.13 Roadmap

Authored `docs/v0-13-roadmap.md` establishing the amended serial program V0130-A through V0130-I:
- **V0130-A (Foundation)**: Architecture, reconciliation, ADRs 0069–0074, specs, 15 scenarios, metrics, baseline, handoffs. Gate: `V0130_A_DOCTRINE_ACCEPTED_AND_BASELINE_FROZEN`.
- **V0130-B (Review Policy)**: Shipped worktree `warn`, block-only index/HEAD, unified observer, closer disposition. Gate: `V0130_B_REVIEW_MUTATION_POLICY_QUALIFIED`.
- **V0130-C (Operator Home & Seams)**: `apgr-home-layout-v1`, relocatable roots, typed Go DTOs, schema manifest. Gate: `V0130_C_HOME_LAYOUT_AND_HOSTING_SEAMS_QUALIFIED`.
- **V0130-D (Optional RTK)**: Configured executable, provisional skill, conditional slices, read-only doctor, corrected static baseline. Gate: `V0130_D_RTK_INTEGRATION_OPTIONAL_AND_QUALIFIED`.
- **V0130-E (Catalog & Sources)**: Generated descriptors, `apgr:`, `project:`, `user:` sources, collision policy. Gate: `V0130_E_SKILL_CATALOG_AND_SOURCES_QUALIFIED`.
- **V0130-F (Context Planner)**: Per-binding plans, byte budgets, mandatory context preservation, static fallback default. Gate: `V0130_F_CONTEXT_PLANNER_REPRODUCIBLE_WITH_STATIC_FALLBACK`.
- **V0130-G (Late Acquisition & MCP)**: CLI and stdio MCP adapter over native APIs, fence-safe acquisitions, mid-turn recovery without blind replay. Gate: `V0130_G_LATE_ACQUISITION_RECOVERABLE`.
- **V0130-H (Qualification & Promotions)**: 5 qualified skill promotions, integrated paired evaluation over frozen corpus. Gate: `V0130_H_MATURITY_TRANCHE_AND_MEASURED_BENEFIT`.
- **V0130-I (Release Hardening & Cutover)**: Standalone verification without Agent-Central checkout, publication operator, truthful labeling. Gate: `V0130_I_NO_AGENT_CENTRAL_DISPATCHER_DEPENDENCY`.

---

## 3. Cohesive Architecture Decision Records (ADRs 0069–0074)

Six sequential ADRs were allocated and authored in `docs/adr/2026/09/`:
1. **[ADR 0069](../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)**: Program Scope and Forward Dispatcher Reference Doctrine.
2. **[ADR 0070](../adr/2026/09/0070-configurable-review-stage-mutation-policy.md)**: Configurable Review-Stage Mutation Policy.
3. **[ADR 0071](../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md)**: APGR Home Layout, Relocatable Configuration and State, and Portable Hosting Seams.
4. **[ADR 0072](../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md)**: Optional RTK Integration as Declared Metadata and Conditional Instruction Slices.
5. **[ADR 0073](../adr/2026/09/0073-unified-skill-catalog-and-deterministic-resolution.md)**: Unified Skill Catalog, Sources, Namespaces, and Deterministic Resolution.
6. **[ADR 0074](../adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md)**: Context Plan, Byte Budgets, Late Acquisition, and Bounded APGR MCP Adapter.

---

## 4. Technical Specifications and Qualification Framework

1. **[`apgr-home-layout-v1`](../specs/apgr-home-layout-v1.md)**:
   Specifies directory hierarchy, permission boundaries (0700 for state, 0755 for home), `--apgr-home` > `APGR_HOME` > `~/.apgr` precedence, zero `JACA_HOME` coupling, and the migration version allocation rule starting from `SCHEMA_VERSION = 2`.
2. **[`review-mutation-seam-inventory.md`](../specs/review-mutation-seam-inventory.md)**:
   Documents drift seams across V1 (`review_binding.py`) and V2 (`v2_turns.py:472-493`), introduces distinct code `READ_ONLY_STAGE_MUTATED_HEAD`, details closer-owned path disposition rules, and analyzes the semantic interpretation risks of reviewer worktree mutations.
3. **[`provider-role-qualification-plan.md`](../specs/provider-role-qualification-plan.md)**:
   Defines the four capability qualification axes across four evidence tiers, preserves Antigravity usable static mode, and prohibits granting Bash to read-only reviewers.
4. **[`apg159-agent-central-dispatcher-differences.md`](apg159-agent-central-dispatcher-differences.md)**:
   Filename- and byte-level inventory of Agent-Central versus APGR `libexec/agent_phase/`: 16 APGR-only modules, 44 byte-identical shared modules, 18 differing shared modules whose content review is assigned to V0130-I. Both available Agent-Central checkouts sit at the parity baseline `56e9bb0`, so no post-baseline behavior gap was observable on this host. The `V0130_I_NO_AGENT_CENTRAL_DISPATCHER_DEPENDENCY` gate remains unverified and is not claimed by this phase.
5. **[`review-mutation-seam-inventory.md` §4.3](../specs/review-mutation-seam-inventory.md)**:
   Bounded read-only sample of retained REVIEWIMMUT1 invalidation evidence (20 files, 1 distinct invalidation event). The invalidated review's response body was not retained, so whether reviewer edits were load-bearing is unanswerable from existing evidence; V0130-B must retain reviewer responses for observed-drift stages.

---

## 5. Context Baseline and 15 Frozen Evaluation Scenarios

1. **Discovery Ceiling Analysis** ([`apg159-context-footprint-baseline.md`](apg159-context-footprint-baseline.md)):
   Current 45 skills consume 11,142 bytes. `rtk-command-proxy` description measures 268 bytes. Projected total: 11,410 bytes, fitting within the 11,507-byte ceiling (97 bytes headroom). Provider instruction files measured as APGR-side file bytes with command provenance (`codex/AGENTS.md` 7,939 B with a 240 B RTK section; `claude/CLAUDE.md` 11,071 B with a 35 B RTK clause and no separable slice; `antigravity/GEMINI.md` 4,238 B with a 1,041 B RTK section). Actually delivered provider bytes and MCP schema overhead are `unavailable`; no token estimates are used.
2. **Evaluation Metrics and Oracles** ([`testing/fixtures/context-eval/context-eval-metrics-and-oracles.json`](../../testing/fixtures/context-eval/context-eval-metrics-and-oracles.json)):
   Freezes targets: $\ge 20\%$ median initial reduction, $\le 10\%$ p95 cumulative growth, 100% exact recovery on mandatory cases, zero authority regressions.
3. **15 Evaluation Scenarios** ([`testing/fixtures/context-eval/`](../../testing/fixtures/context-eval/)):
   - Calibration set: Scenarios 01–05.
   - Acceptance set: Scenarios 06–15 (including Scenario 13: pre-launch no-MCP fallback).
4. **Promotion Candidate Ranking** ([`apg159-skill-promotion-cost-ranking.md`](apg159-skill-promotion-cost-ranking.md)):
   Derived ranking across seven evidence categories establishing primary tranche: `go-language-profile`, `go-test-profile`, `pytest-test-profile`, `markdown-language-profile`, `sqlite-database-profile`.

---

## 6. Discrepancy Dispositions and Handoffs

1. **Discrepancies D1–D12 & Manager Findings** ([`apg159-source-discrepancies-and-findings.md`](apg159-source-discrepancies-and-findings.md)):
   Fully dispositioned with assigned owners and deliverable impact.
2. **Caveman Pattern Evaluation** ([`docs/governance/optional/caveman-pattern-evaluation.md`](../governance/optional/caveman-pattern-evaluation.md)):
   Reaffirms APG141 rejection; excludes upstream BSL-1.1 code; adopts budget-first packing and exact recovery clean-room.
3. **Handoffs Updated and Delivered Unaccepted**:
   - `docs/architecture/v0-12-jaca-disposition-handoff.md` (updated with forward pointer)
   - `docs/architecture/v0-12-agent-central-ownership-transition.md` (updated with forward pointer)
   - `docs/architecture/v0-13-jaca-disposition-handoff.md` (new v0-13 handoff)
   - `docs/architecture/v0-13-agent-central-ownership-transition.md` (new v0-13 handoff)

---

## 7. Verification Results

All read-only validation commands passed cleanly (re-run at closeout after the work-review corrections; see the exit record for the closeout run):
- `bin/apg-check-record-identity --format json`: PASS (74 ADRs, 203 exits, 203 phase IDs; next ADR 0075, next exit 00206).
- `bin/apg-check-skill-library`: PASS (45 canonical skills, 45 catalog rows, 45 projections).
- `bin/apgr skills context-report`: PASS (11,142 description bytes).
- `bin/apg-check-roadmap-closure`: PASS (55/55 historical closed items).
- `git diff --check`: PASS (zero whitespace errors).
