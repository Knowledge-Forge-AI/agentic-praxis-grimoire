# v0.13 Dispatcher Consolidation, Review Policy, Hosting Seams, and Adaptive Context Roadmap

- **Status**: Active Program Roadmap
- **Authority**: Delegated program direction to ChatGPT under governing manager disposition (2026-09-20)
- **Foundation Milestone**: `V0130-A` (Phase `APG159`, Exit `00205`); Qualified under `V0130-A-CORR1` (Phase `APG159A`, Exit `00206`)
- **Prior Roadmap**: [v0.12 architecture transfer roadmap](v0-12-roadmap.md)
- **Reconciliation Reference**: [v0.12 forward reconciliation record](architecture/v0-12-forward-reconciliation.md)

---

## 1. Program Direction and Release Purpose

The release purpose of APGR v0.13.0 is **an independently usable APGR dispatcher with proportionate, configurable review behavior, portable hosting interfaces, optional RTK command proxying, and an exercisable, observable context-management pilot with static fallback**. v0.13.0 is an early pilot, not a finished v1.0 system; see §1a for the operative release expectations.

v0.12 transferred the single-phase runtime from Agent-Central into APGR, formalizing dynamic routing, Request V2 multi-turn execution, SQLite persistence, and provider parity closure. v0.13 completes this evolution across five core themes:

1. **Theme 1 — Runtime Doctrine and Decommission Path**: APGR becomes the permanent forward reference single-phase dispatcher. Agent-Central dispatcher retirement is a reversible, owner-executed transition; APGR maintains standalone operational independence with zero mandatory Agent-Central dependencies.
2. **Theme 2 — Review-Stage Mutation Policy**: Establishes a tri-state worktree mutation policy (`block`, `warn`, `allow`) with shipped default `warn`. Index and HEAD mutations remain strictly fail-closed (`block`). Observed worktree edits preserve reviewer findings while recording `subject_drift_observed = true` and `final_candidate_reviewed = false`, with closer-owned path disposition at finalization.
3. **Theme 3 — Operator Home and Portable Hosting Seams**: Adopts `apgr-home-layout-v1` with resolution `--apgr-home` > `APGR_HOME` > `~/.apgr`. APGR never reads `JACA_HOME`. Provides lean, typed Go DTOs and a versioned SQLite schema contract for hosting orchestrators like JACA, while deferring speculative custom Go TOML parsers and mixed-owner databases.
4. **Theme 4 — Optional RTK Integration**: Integrates RTK as optional declared metadata (`required = false` default), absolute executable paths with symlink resolution, conditional provider instruction slices, a read-only doctor, a provisional `rtk-command-proxy` skill within the existing discovery ceiling, and a corrected no-RTK static baseline.
5. **Theme 5 — Adaptive Context Resolution**: Unifies skill catalog sources (`apgr:`, `project:`, `user:`) with deterministic per-binding context plans under explicit byte/character budgets, late acquisition via CLI and a bounded stdio MCP adapter (amending `APGR-D8` while retaining general-suite prohibitions), static fallback, and lightweight local operational observations. Provisional skill promotion is optional incremental maintenance before v1.0, not a per-release quota.

### 1a. Pilot release direction (APG166X, 2026-09-29)

The human maintainer revised the v0.13 priorities: dispatcher reliability and
context management lead the next releases, and the H benchmark result is not
the authority for releasing an early pilot. This supersedes the earlier
*prospective* gates that tied v0.13.0 to a measured H benefit or to five stable
promotions. Historical H records, grants, ledgers and failed attempts are
preserved unchanged.

The operative v0.13.0 release expectations are:

1. supported dispatcher paths (V1 and V2 normal routes) work;
2. user work is preserved, including the real Git index and staged intent;
3. failures are diagnosable from retained run evidence;
4. context management can be exercised on the normal paths, with
   `mode = "adaptive"` available as an explicit, reversible experimental
   opt-in. (Originally: it records prospective plans while launching static
   transport. APG166Z-CONTEXT1 amends this: on the ordinary Claude
   `claude-profile` route the opt-in delivers selected skills with late
   acquisition; other routes keep static transport with a stated reason.);
5. static fallback works and remains the default;
6. the distributed interfaces and packages pass their ordinary applicable
   tests;
7. supported, experimental and deferred status is stated truthfully.

Lightweight local operational observations are collected on normal dispatch
paths (with a documented opt-out) and summarized without rerunning providers;
see [operational observations](guides/operational-observations.md). They inform
later promotion and remediation decisions; they are not a benefit claim or a
maturity score. Quantitative H targets remain optional experiment targets.
There is no default flip based on unmeasured savings and no automatic
promotion.

---

## 2. Governance and Scheduling Authority

- **Execution Lane**: The canonical execution lane is serial. While milestone designs can proceed in parallel, mutating dispatches are strictly serialized into the working tree.
- **Scheduling Boundary**:
  - **Milestone V0130-A (Foundation)** executed in isolation, confined to documentation, specifications, and non-executable evaluation fixtures (APG159 / APG159A).
  - **Milestone V0130-B Local Source-Entry (Manager Disposition M5)**: Settled for local development on the isolated branch via GitHub connector readback of public release commit `919a04f493f79d91315668b5b1b9794e8e35b284` (staging tree `7e40c0f62204d2b9d3f7210812f31229b60988e4`, 13 green jobs, private base `c4ac2a122e9f786fd7208a4619da47ebe468d3e9`), without claiming historical G2 administrative paperwork globally closed. Code dispatches proceed sequentially under manager authorization.
- **Authority Discipline**: APGR phase IDs, ADR identifiers, and exit record numbers are allocated strictly from current repository records per [phase and record identity](phase-and-record-identity.md). ADRs for v0.13 are allocated as ADRs 0069 through 0074.

---

## 3. Milestone Structure and Dependency Graph

```text
V0130-A: Baseline, Doctrine, Architecture & Evaluation Data (APG159 / APG159A)
   |
   +---------------------------------------+
   |                                       |
   v                                       v
V0130-B: Review-Mutation Policy         V0130-C: Operator Home & Hosting Seams
   |                                       |
   +-------------------+-------------------+
                       |
                       v
V0130-D: Optional RTK Integration
   |
   v
V0130-E: Unified Skill Catalog and Sources
   |
   v
V0130-F: Context Planner, Budgets, & Static Fallback
   |
   v
V0130-G: Late Acquisition Channels (CLI & MCP)
   |
   +---------------------------------------+
   |                                       |
   v                                       v
V0130-I: Pilot Release Hardening,       V0130-H: Maturity Tranche & Integrated
         Agent-Central Cutover Gate,             Evaluation (experimental track;
         & Publication                           not a v0.13 publication
                                                 prerequisite)
```

---

## 4. Milestone Definitions and Exit Gates

### V0130-A — Baseline, Doctrine, Architecture, and Evaluation Data
- **Phase ID**: `APG159` (Exit `00205`); Bounded Correction: `APG159A` (`V0130-A-CORR1`, Exit `00206`)
- **Scope**: Reconcile v0.12.0 multi-channel publication reality and post-G1 commits (APG153E–APG158A); author ADRs 0069–0074; specify `apgr-home-layout-v1` and review-mutation seam inventory; establish provider/role qualification plan; measure baseline context delivery; freeze 15 non-executable evaluation scenarios with metric oracles; rank candidate skill promotions across seven evidence categories; disposition discrepancies D1–D12; author unaccepted JACA and Agent-Central handoffs. Under APG159A, re-evaluate canonical skill measurements, freeze mathematical formulas, resolve Scenario 01 budget infeasibility, and qualify foundation evidence.
- **Authority Boundary**: Pure documentation and non-executable fixture data. Zero runtime code, packaging, lockfile, or skill body mutations.
- **Exit Gates**: `V0130_A_DOCTRINE_ACCEPTED_AND_BASELINE_FROZEN`; Correction Gate: `V0130_A_CORR1_FOUNDATION_QUALIFIED`.

### V0130-B — Review-Stage Mutation Policy
- **Phase ID**: `APG160` (Exit `00207`); Bounded Repairs: `APG160A` (Exit `00208`), `APG160B` (Exit `00209`), `APG160C` (Exit `00210`), `APG160D` (`APG160D-LOCAL-FINISH2`, Exit `00211`)
- **Manager Authority Record**: Manager B acceptance recorded under `APG160D-LOCAL-FINISH2` commit `bf6776a4a7bbfb7b66b2d6343ab59f96d6b1d680` (native run interrupted in revise_close; carried qualification: 159 passes, 1 host-snapshot skip, accepted exact-whitespace-readback exit 2 exception).
- **Scope**: Implement shared review drift observer across V1 (`review_binding.verify`) and V2 (`v2_turns.py:472-493`); implement tri-state worktree policy (`warn` shipped default, `block`, `allow`); fail-closed `block` for index and HEAD; distinct `READ_ONLY_STAGE_MUTATED_HEAD` code; `subject_drift_observed = true` and `final_candidate_reviewed = false` tracking; closer-owned path disposition rules; Go evidence DTOs and golden vectors.
- **Exit Gate**: `V0130_B_REVIEW_MUTATION_POLICY_QUALIFIED`.

### V0130-C — Operator Home, Closed Config, and State Seams
- **Phase ID**: `APG161` (Exit `00212`); Bounded Repairs: `APG161A` (`V0130-C-REPAIR1`, Exit `00213`), `APG161B` (`V0130-C-REPAIR2`, Exit `00214`)
- **Scope**: Implement `apgr-home-layout-v1` path resolution (`--apgr-home` > `APGR_HOME` > `~/.apgr`); isolate operator Claude settings (`<APGR_HOME>/claude/settings.json` never written); relocate generation store; enforce fail-closed dynamic routing when `capabilities.toml` is absent; export dispatcher SQLite schema manifest and row DTOs in Go; update consumer fixtures. Document existing `<APGR_HOME>/state/runs` ownership without implicit migration. Under APG161A, correct pre-import home selection, hermetic generation closure, closed config parsing for `dispatcher.review_mutation`, coherent operator generation 42, and pure Go JSON view consumption. Under APG161B, correct effective-home/outbox precedence, legacy generation store directory creation and non-mutating search sequencing, single captured roster bundle threading across policy, routing, and capabilities, and lazy roster loading.
- **Exit Gate**: `V0130_C_HOME_LAYOUT_AND_HOSTING_SEAMS_QUALIFIED`.

### V0130-D — Optional RTK Integration
- **Phase ID**: `APG162` (Exit `00215`); Bounded Repairs: `APG162A` (`V0130-D-INTEGRATION1`, Exit `00216`), `APG162B` (`V0130-D-BOUNDARY2`, Exit `00217`), `APG162C` (`V0130-D-CALLPATH1`, Exit `00218`)
- **Current correction**: V0130-D is manager-accepted and closed for local development integration through APG162C-LOCAL-FINALIZE1. Exit 00218 retains its checkpoint history and records the accepted local commitment addendum. No review freshness is upgraded; A1 V2 worker admission, F8 matcher dialect equivalence and F9 diagnostic style remain documented limitations. E does not replay D finalization or tests.
- **Scope**: Implement `[integrations.rtk]` closed configuration (`required = false` default, strict `required = true` deferred); absolute executable validation with symlink resolution; read-only doctor (`apgr integrations rtk doctor`); adopt provisional `rtk-command-proxy` skill within the 11,507-byte discovery ceiling; conditional instruction slices for Codex, Claude, and Antigravity; establish corrected no-RTK static baseline. Under APG162A, correct ordinary path configuration semantics, native generation closure allowlist, Claude and multi-provider transport branch integration, streaming bounded probes with direct child process reaping, isolated hook targeting, and skill provenance. Under APG162B, correct single package version authority (`VERSION` = "0.12.0", `__version__` in `__init__.py`, `version.py` and `VERSION` in `ALLOWLIST`), eliminate sibling guessing in `rtk.py` by passing target project explicitly in adapters, enforce conservative Claude hook uncertainty and double-wrap prevention, surface normal unavailability diagnostics at consumers, ensure serializable fallback `as_dict`, record started timeout probes with bounded output, and narrow process reaping wording.
- **Exit Gate**: `V0130_D_RTK_INTEGRATION_OPTIONAL_AND_QUALIFIED`.

### V0130-E — Unified Skill Catalog and Sources
- **Phase ID**: `APG163` (`V0130-E-CATALOG1`, Exit `00219`). Accepted for local development by the September 23 manager disposition after APG163-LOCAL-AMEND1. The original provider checkpoint remains distinct from the manager-amended candidate; no provider replay or second independent review occurred.
- **Implemented boundary**: Generated descriptors, bounded source capture, qualified explicit resolution and Python-owned override configuration; see [catalog contract](guides/skill-catalog.md). Composition remains informational. No ranking, packing, MCP, promotion or automatic dispatch integration is claimed.
- **Scope**: Implement generated `SkillDescriptor` from frontmatter, ledger, and rules; multi-source catalog supporting `apgr:` (embedded), `project:` (`<project>/.apgr/skills/`), and `user:` (`<APGR_HOME>/skills/`); deterministic collision resolution (`supplement` default, explicit `replace` in config); `apgr skills list --all-sources`.
- **Exit Gate**: `V0130_E_SKILL_CATALOG_AND_SOURCES_QUALIFIED`.

### V0130-F — Context Planner, Budgets, and Static Fallback
- **Phase ID**: `APG164` (`V0130-F-CONTEXT1`, Exit `00220`). Accepted for local integration by the September 23 manager disposition after independent dispatcher work review and revise-close. No push or publication occurred. No second independent review of revise-close amendments. Static remains the shipped context default.
- **Implemented boundary**: Pure Go planner/CLI, Python closed context configuration, V1/V2 per-attempt records, and caller-owned projection seam. No live provider binding is qualified for adaptive reduction; see [context planning](guides/context-planning.md).
- **Scope**: Implement per-binding `ContextPlan` keyed by `(run_id, binding_id, attempt_id)`; byte and character budgeting (tokens unavailable); mandatory repository doctrine preservation; persisted sibling plans (`NN-<stage>.context-plan.json`); static fallback default (`[dispatcher.context] mode = "static"`); provider projection per qualification matrix.
- **Manager Authority Record (M2 & M4)**: On mandatory doctrine overflow, reject adaptive plan and fall back to qualified static transport with doctrine intact (never abort pre-launch or truncate doctrine). Carry forward M4 qualification debts: Scenario 03 packing bounds (31,544 B vs 30,000 B), material applicability across multiple profiles (e.g. Go test needing both language and test profiles), task-result oracles testing intended behavior, and scoped collision-resistant event IDs.
- **Exit Gate**: `V0130_F_CONTEXT_PLANNER_REPRODUCIBLE_WITH_STATIC_FALLBACK`.

### V0130-G — Late Acquisition Channels (CLI & MCP)
- **Phase ID**: `APG165` (`V0130-G-ACQUIRE1`, Exit `00221`). Manager-accepted for local integration before APG166 after supplied dispatcher-owned independent work review and revise-close. No push or publication occurred. Amendments have no second independent review; native provider filesystem permissions and live model behavior remain unqualified. This acceptance establishes neither H benefit nor promotions.
- **Candidate boundary**: Shared native CLI/MCP engine, pinned 2025-11-25 protocol, run-owned snapshots/events, optional artifact indexing and explicit caller-owned native launch seam. Normal provider bindings retain static transport. See [acquisition contract](guides/skill-acquisition.md) for controlled qualification and live-provider limitations.
- **Scope**: Implement shared acquisition engine writing to run-owned store; CLI channel (`apgr skills search` / `acquire`); stdio JSON-RPC 2.0 MCP adapter (`apgr mcp serve`) with 3 tools (`skill_search`, `skill_acquire`, `context_explain`) and 2 resources (`apgr://skills/`, `apgr://context/`); dispatcher-injected MCP configuration for adaptive runs; fence-safe acquisition; mid-turn recovery without blind producer replay.
- **Manager Authority Record (M4)**: Scenario 12 must grant MCP acquisition capability before injected failure and native read after; Delivery and SQLite ingestion are independent facts; non-blocking ingestion failures.
- **Exit Gate**: `V0130_G_LATE_ACQUISITION_RECOVERABLE`.

### V0130-H — Maturity Tranche and Integrated Evaluation
- **Phase ID**: `APG166` (`V0130-H-EVAL1`, Exit `00222`). Revised checkpoint after supplied independent work review, without a second review of documentation amendments. Installed-CLI authority retention is bounded; H0.2 response-write accounting remains partial pending a tested complete-delivery bridge. A sealed provider-free harness and five individual evidence inventories are implemented. All five stable promotions were explicitly declined by review. Zero stable promotions; no measured live paired benefit; required gate remains unsatisfied. See [H evaluation](evaluations/apg166-maturity-and-integrated-evaluation.md). Static remains the default; this candidate does not support a default flip in I.
- **Scope**: Promote five provisional skills individually (`go-language-profile`, `go-test-profile`, `pytest-test-profile`, `markdown-language-profile`, `sqlite-database-profile`); create resolver fixtures per promoted skill; execute paired adaptive vs static evaluation against 15 frozen scenarios; verify $\ge 20\%$ median initial reduction target, $\le 10\%$ p95 cumulative increase target, 100% exact recovery, and zero authority regressions.
- **Pilot status (APG166X)**: V0130-H is an experimental track. Its quantitative targets are optional experiment targets, not v0.13 publication prerequisites; its gate stays false until actually met, and promotions proceed individually as low-priority maintenance.
- **Manager Authority Record (M4)**: Observation-based skill delivery assertions (not static discovery); frozen conformance cases without post-hoc selection; explicit Scenario 15 contingency resolution.
- **Exit Gate**: `V0130_H_MATURITY_TRANCHE_AND_MEASURED_BENEFIT`.

- **APG166 source acceptance**: The manager accepted the blocked APG166 source
  locally on 2026-09-23, at commit `6e46ecb192e8ccb0aea5a6135f5c96e84b5e84f8`
  and tree `a18a93384ee463fc53551ab42af824d14158a33d`. No push or publication
  occurred. Historical dispatcher blockage and the unmet H gate remain intact;
  no promotions, measured benefit, Scenario 15 qualification or I authority follow.
- **APG166A continuation**: `V0130-H-QUAL2`, exit `00223`, is a locally accepted blocked
  infrastructure checkpoint revised after the supplied work review. Prerequisite
  readiness remains blocked on a complete live native recovery observer. It adds
  digest-bearing delivery bridging, process-boundary observations, bounded
  launcher retention, and an instrumented pair-runner interface. The
  [measurement evaluation](evaluations/apg166a-measurement-and-launcher-readiness.md)
  and [pre-live handoff](evaluations/apg166a/handoff.json) distinguish mechanism
  qualification from live H evidence. The manager accepted local commit
  `379f85a47e488fb23a12f12e8250e10c492ebcaf` and tree
  `d5eb6ab3fe6973eefd1c541be3ae28776f2bb294` on 2026-09-23; no push/publication
  occurred. Historical prerequisite blockage is preserved. That acceptance
  grants no H benefit, promotion, Scenario 15 or V0130-I authority.
- **APG166B continuation**: `V0130-H-QUAL3`, exit `00224`, produces a native
  Claude Read observer and one separately labelled non-holdout sentinel probe.
  The [qualification evaluation](evaluations/apg166b-native-read-qualification.md)
  and [handoff](evaluations/apg166b/handoff.json) own current prerequisite
  evidence. Revise-close amends the independently reviewed candidate and keeps
  prerequisites blocked: the wrapper/MCP acquisition seam is incompatible,
  concrete holdout bindings are absent, and repeated-Read CLI semantics remain
  unqualified. No readiness token is established and no second independent
  review covers the amendments. A separately authorized prerequisite continuation
  and manager acceptance are required before any live holdout phase. H main gate remains false, H live pairs and promotions
  remain zero, Scenario 15 remains contingent/unavailable, static remains the
  default, and V0130-I remains unauthorized.

APG166C records manager acceptance of APG166B local source commit
`35da4e52262495ec999e69687c68892a6d42285a` and tree
`7958e83d62159f8c61a01504f5af5046c82ccc25` on 2026-09-23, without
push/publication. The historical blocked result is preserved; no readiness token,
holdout, promotion, Scenario 15 or I authority follows from that acceptance.

- **APG166C continuation**: `V0130-H-QUAL4`, exit `00225`, produces a scoped
  wrapper handoff, observed-shape repeated-Read accounting, five-skill task
  preregistration and explicit fifteen-scenario binding gaps. The corrected
  non-holdout probe succeeds at MCP but native Read is denied by working-directory
  permissions; the authorized rerun budget is exhausted. The full execution
  package, substantive oracles, runtime binding and all-subject dry-run remain
  incomplete. The [evaluation](evaluations/apg166c-pre-live-readiness.md) and
  [handoff](evaluations/apg166c/handoff.json) retain blocked prerequisite readiness
  for dispatcher-owned work review. No readiness token, H pair, promotion,
  Scenario 15 qualification, default change or I authority follows.

APG166D records manager acceptance of APG166C local source commit
`3250c21e9a8dee1752c93338ab4faee1a94c5fba` and tree
`da061dbf152de7562fc789d1038ec8eafc6e4de9` on 2026-09-23, without
push/publication. The historical blocked result remains intact. No readiness,
H gate, live holdout, promotion, Scenario 15 or I authority follows.

- **APG166D continuation**: `V0130-H-QUAL5`, exit `00226`, produces an
  uncommitted prerequisite-repair candidate. Exact recovery-directory custody,
  closed internal argv admission, post-run identity evidence and captured
  repeated-Read authority are under qualification alongside the all-scenario
  execution package and revised promotion attribution. Supplied independent
  review rejected preregistration. Revise-close repairs bounded importer, runtime
  surface and dry-run gates, with no second independent review; substantive
  oracles, runtime bindings and final-source D1 remain incomplete. Prerequisite readiness and H
  remain false; no live holdout, promotion or Scenario 15 qualification follows.
  See the [evaluation](evaluations/apg166d-pre-live-execution-package.md).

APG166E records manager acceptance of local APG166D commit
`e0ffbcfbe6c20b498228b0da11e0e06295c098e0`, tree
`a86b38a44bbcee636c5c2805c9c462cea74177b5`, without push/publication.
APG166D remains historically blocked. No readiness, runtime, D1, H,
promotion, Scenario 15 live qualification or I authority followed.

- **APG166E continuation**: `V0130-H-QUAL6`, exit `00227`, is a provider-free
  execution-package checkpoint rejected by the independent work review.
  Any eventual `V0130_H_PROVIDER_FREE_PACKAGE_READY` token is limited to the
  non-model package and does not authorize D1 or establish live prerequisites.

### V0130-I — Agent-Central Cutover Gate, Release Hardening, and Publication
- **Scope**: Verify standalone operation without Agent-Central checkout; verify the §1a pilot release expectations; run the ordinary applicable test and conformance matrix for the distributed interfaces; keep static as the shipped context default (no default flip without separately qualified evidence) and describe adaptive planning as experimental; state supported, experimental and deferred status truthfully; verify distribution-surface documentation (README, descriptions, referenced docs across PyPI, npm, Go, Homebrew and the first-party Nix flake); add the Nix owners to the `0.13.0` audited release surface and the attended release operator; attended publication with release-ID binding, followed by tag-pinned Nix readback (`bin/apg-qualify-nix readback --tag v0.13.0`), without which the release is not fully published. A met H benefit gate and skill promotions are not prerequisites.
- **Exit Gates**:
  - `V0130_I_NO_AGENT_CENTRAL_DISPATCHER_DEPENDENCY`
  - `V0130_I_PUBLISHED_WITH_TRUTHFUL_STATUS`.

---

## 5. Explicitly Deferred Work

The following items are explicitly out of scope for v0.13.0:

1. **Custom Go TOML Subset Parser (H3)**: Standardizing a handwritten Go TOML grammar is deferred. Hosting consumers remain responsible for their own TOML parsing or pass validated typed JSON/DTO structures.
2. **Shared APGR/JACA Database (H5)**: APGR and JACA maintain independent databases and explicit record exchanges. No mixed-owner tables (`ext_*`), cross-system schema migrations, or shared `database/sql` access layers are introduced.
3. **Full Per-Role Dynamic Instruction Slicing**: Dynamic instruction generation is confined to the minimal supported form (RTK slice and role notices). Full per-dispatch dynamic slicing remains experimental.
4. **Upstream Caveman Runtime Code or Importer**: Caveman concepts (budget-first packing, exact recovery, honest measurement) are adopted clean-room at pattern level. Upstream BSL-1.1 engine code is excluded, and the APG141 importer rejection stands.
5. **Arbitrary Discovery Ceiling Expansion**: The 11,507-byte discovery ceiling remains binding. The `rtk-command-proxy` skill fits within existing headroom.
6. **Strict-Required RTK Policy**: RTK operates strictly as an optional optimization (`required = false`).
7. **External Provider Capability Assumptions**: Dynamic routing and selective projection remain strictly gated on empirical qualification. Unqualified provider configurations fail closed to static mode.
8. **H Benefit Gate and Promotion Quota as Release Prerequisites (APG166X)**: The measured H benefit gate and a fixed number of promotions are not v0.13.0 publication prerequisites. H remains an optional experimental track; live selective projection on normal routes remains unqualified.

## V0130-E verified local acceptance addendum (September 23)

The manager accepted APG163-LOCAL-AMEND1 after verifying the supplied receipt
bundle: 308 manifest payloads, 84 before/after blob occurrences, raw Git objects,
managed report payload, eleven operation command/stream pairs and the exact
manager response. This is supplied receipt verification, not a new inspection
of another workspace. The two-file amendment decodes BuildCatalog's ownership
copy into a fresh zero-valued input and adds four caller-ownership regressions.
Public signatures, selection behavior and equivalent-input identities remain
unchanged. The resulting increment contains 51 paths (18 additions, 33 changes).

The fresh affected Go evidence is 253 passing tests/subtests across four packages,
with no failures or skips and successful vet/whitespace checks. It supersedes the
prior affected 248-case result; counts are not added. Retain the prior 346 Python
passes; Python was not rerun by the amendment and four installed repetitions are
not additional unique cases. The three prior post-test prose changes and absence
of a second independent review remain disclosed. E acceptance grants bounded F
implementation authority, not G/H/I or publication authority.

## V0130-H provider-free amendment checkpoint

APG166E / V0130-H-QUAL6, Exit 00227, produces durable launch guards, bounded
runtime capture and revalidation, retained oracle/importer evidence, immutable
recovery qualification and revised five-skill preregistration. Its
[evaluation](evaluations/apg166e-provider-free-readiness.md) records qualification
and remaining oracle, review-custody and one-arm integration defects. The supplied
independent review requires amendment, rejects the package and rejects every
per-skill preregistration. Revise-close records these unresolved findings without
changing implementation. A separately authorized correction and fresh exact-source
independent review are required; there is no second review in this run.
`V0130_H_PROVIDER_FREE_PACKAGE_READY` remains false. No D1, live H, promotion,
Scenario 15 live qualification, publication or V0130-I authority follows.

### APG166E-CORR1 historical partial correction

APG166F is the correction dispatcher identity for APG166E-CORR1; the formal
product phase remains APG166E / V0130-H-QUAL6 / Exit 00227. Its producer attempted the nine
accepted independent-review corrections and reported a mechanically complete
provider-free candidate: 15 complete scenario records and 25 promotion fixture
pairs, with non-trigger evidence limited to preregistration structure. The fresh
corrected transaction has zero provider sentinels and valid retained readback.
Repository source may seal a mechanical candidate but cannot authenticate its
own independent review or mark the provider-free package accepted. Manager
review is required, and all five preregistrations remain pending independent
review. Revise-close is repository-read-only. That producer state was subsequently reviewed as partial and amended; the
current correction and D1 identities are below. D1, live H, promotions, Scenario 15
live qualification and V0130-I remain unauthorized; static remains default.


### APG166G / APG166E-CORR2 historical provider-free corrections

APG166G owns CORR2 under APG166E / V0130-H-QUAL6 / Exit 00227. APG166F/CORR1
received source amendment and mechanical-package rejection: F1/F2/F3/F5 were
partial while F4/F6/F7/F8/F9 were resolved. CORR2 repairs the remaining visible
API, behavioral contract, neighboring-task correctness and objective review
evidence issues plus four accepted advisories, preserving the resolved findings.
Focused verification and a fresh bounded 15-scenario provider-free transaction
are complete: all records and subject pairs pass, provider calls and sentinels
are zero, runtime before/after and immutable readback are valid, and no H
aggregate is written. Dispatcher-owned exact-source review remains pending. All five skills require fresh
independent dispositions. Source cannot authenticate its own review.

The historical APG166H D1 reservation is superseded by CORR3 below. No new
formal exit is allocated. Package readiness remains false, manager review is
required, promotion acceptance is pending, D1/live prerequisites/H/holdout remain
false, Scenario15-live is contingent, static is default, and V0130-I remains
unauthorized. No publication or successor authority follows this candidate.


### APG166H / APG166E-CORR3 grading custody and transaction neutrality

APG166H owns only F1/F2 and the residual CopyFile/Fetch advisories, retaining
APG166E / V0130-H-QUAL6 / Exit 00227. The APG166G source checkpoint is retained
with F1/F2 partial, F3/F5 resolved and F4/F6/F7/F8/F9 preserved; its mechanical
package was rejected. Prior Go language and Markdown acceptance does not
transfer to the changed source. All five skills need fresh independent review.

The correction preserves candidate configuration and support during authored-
test grading, substitutes explicitly owned implementation files only, commits
SQLite setup before candidate transactions, and removes exception-class bias
from migration recovery. Focused qualification passes (95 contract, 155
preserved-mechanics and eight record tests). The fresh provider-free transaction
completes all 15 records and subject pairs with zero provider tasks/sentinels,
valid runtime before/after and immutable readback, 25 promotion pairs, complete
Scenario12/13/15 mechanics, and no H aggregate. APG166I is reserved for D1 if CORR3 is
accepted and separately authorized. Package readiness remains false; manager
review is required, promotion acceptance pending, and live prerequisites/H/
holdout false. Scenario15-live is contingent, static remains default, and
V0130-I is unauthorized. No new exit or publication authority is created.


### APG166I / APG166E-CORR4 hidden execution attestation

APG166I is the bounded N1/A1/A2/A3 correction under APG166E / V0130-H-QUAL6 /
Exit 00227. APG166H's supplied review requires source amendment while
accepting its mechanical package for manager consideration; pytest is
rejected, the other four skills accepted, F1/F2 and CopyFile/Fetch resolved,
F3–F9 preserved. CORR4 separates exact hidden pytest/Go execution proof from
candidate-authored GOOD/BAD grading, preserves the visible check name and
replaces stale lifecycle attribution with a material open test-design axis.
Focused qualification passes 44 attestation/CORR3, 81 promotion-contract, 174
preserved-mechanics and eight record tests. The fresh provider-free
transaction completes all 15 scenario records and subject pairs, all oracle/
importer and Scenario12/13/15 mechanics, 25 promotion pairs and nine qualified
GOOD hidden-execution attestations. Runtime before/after and immutable
readback are valid, provider tasks/sentinels zero and no H aggregate is
written. All five skills need fresh independent dispositions on the exact
candidate.

Package readiness remains false; manager review is required and promotion
acceptance pending. D1 is reserved for APG166J after separate authorization if
CORR4 is accepted; the historical APG166I reservation is superseded. D1/live
prerequisites/H/holdout remain false, Scenario15-live contingent, static
default and V0130-I unauthorized. No new formal exit or publication authority
follows.

### APG166J / APG166E-CORR5 authored collection and starting evidence

APG166J repairs only A1 and NF1 under APG166E / V0130-H-QUAL6 / Exit 00227.
The supplied APG166I review retains source AMEND and mechanical acceptance for
manager consideration with the NF1 caveat; pytest is rejected, four other skills
accepted, and N1/A2/A3 plus F1-F9 preserved on that historical source.
CORR5 requires actual candidate-configured stable-check GOOD/BAD execution,
captures starting pytest artifacts before disposable-directory cleanup and
recomputes exact retained attestations rather than trusting copied status.
The [current evaluation](evaluations/apg166e-provider-free-readiness.md) records
the focused verification, fresh transaction and deferred limitations.

Focused slices pass 51 changed-boundary, 107 promotion/Go-contract, 166
preserved-mechanics and eight phase-record tests, plus a final cleanup
assertion rerun. These overlapping counts are not added. All guards record zero
sentinels. The fresh final transaction completes 15/15 records, equal initial
pairs and unchanged subject pairs, all scenario oracle/importer exercises,
25 promotion GOOD/BAD pairs and Scenario12/13/15 provider-free mechanics.
All 15 positive starting subjects are rejected for their source-owned outcomes;
all three starting pytest hidden attestations qualify and are recomputed from
retained raw artifacts. All 18 fixture pytest/Go attestations also recompute,
including nine qualifying GOOD hidden runs. Runtime before/after and retained
readback are valid; provider task invocations and durable sentinels are zero.
No H aggregate is written.
All five skills require fresh exact-source independent review. Provider-free
package readiness remains false, manager review is required and promotion
acceptance pending. D1 is reserved for APG166K after CORR5 acceptance and separate
authorization; the historical APG166J reservation is superseded. D1/live
prerequisites/H/holdout remain false, Scenario15-live contingent, static default
and V0130-I unauthorized. No new exit or publication authority follows.

### APG166K empty-tree candidate capture and exact-source carry-forward

APG166J is the accepted provider-free checkpoint on its exact historical tree
`51832efa74e6a50c166dc3e22a12212723a78c44`. APG166K is a generic dispatcher
robustness interlude under continuation `APGR-EMPTY-TREE-CANDIDATE-FIX1`.
Product identity remains APG166E / V0130-H-QUAL6 / Exit 00227; no new formal
exit is allocated.

APG166K repairs candidate capture (`libexec/agent_phase/candidate.py::tree_identity()`)
for repositories whose HEAD is an empty-tree root commit: tracked refresh
`git add -u -- :/` is conditionally executed only when cached paths exist in the
temporary index, preventing pathspec failures and allowing the first untracked
substantive product to reach candidate binding. Dedicated real-Git regressions
cover empty root without product, empty root with first untracked product, real
index absence retention, real index byte immutability, and end-to-end dispatcher
candidate binding.

Because source changed, provider-free acceptance on APG166K is pending exact-source
carry-forward review and manager reacceptance. A fresh mechanical carry-forward
transaction re-verified all 15 provider-free records, 15 equal initial pairs,
15 unchanged subject pairs, 25 promotion pairs, recomputed hidden and starting-subject
attestations, valid runtime before/after, zero sentinels, and zero provider invocations.
All five skills require fresh exact-source dispositions. D1 is reserved for APG166L
if APG166K is accepted; D1, live H, holdout, and V0130-I remain unauthorized,
and static remains default.

### APG166M provider-free D1 seam implementation

APG166L blocked live D1 launch because the D1 seam was not implemented in source.
APG166M implements the missing D1 seam entirely provider-free under continuation `V0130-H-D1-SEAM1`.
Formal product identity remains `APG166E / V0130-H-QUAL6 / Exit 00227`; no new formal exit
is allocated.

APG166M implements:
- Dedicated source-owned D1 owner `testing/h_eval/d1_qualification.py`;
- Source-owned D1 descriptor `testing/h_eval/d1-descriptor.json` binding exactly one route
  (`claude`, `normal-final-review`, `claude-opus-5`, `Work Review`, allowed tools `["Read"]`,
  forbidden tools `["Bash", "Write", "Edit", "Agent"]`, strict-empty MCP `[]`, isolated settings);
- Deterministic non-holdout probe fixture `testing/h_eval/d1_probe_fixture.txt` materialized
  into a run-owned private probe directory (`0o600` permissions);
- External manager authority validation (`APG166D-PROBE-D1`, `max_starts = 1`, `replay_prohibited = true`);
- One-use attempt accounting and replay refusal (`attempt-state.json`);
- Raw evidence custody and readback recomputation with tamper rejection;
- Preserved holdout admission block (`LIVE_ADMISSION_AVAILABLE = False`);
- Zero real provider starts occurred; durable provider-start tripwire active throughout;
- Mechanical validation candidate only (`manager_review_required = true`, `prerequisites_ready = false`).

The live D1 attempt is reserved for APG166N after exact-source manager acceptance.
D1 live, live H, holdout, and V0130-I remain unauthorized, and static remains default.

### APG166N provider-free D1 seam correction (B1–B8)

APG166N corrects blocking findings B1–B8 from the APG166M independent review and manager
disposition entirely provider-free under continuation `V0130-H-D1-SEAM2`. Formal product identity
remains `APG166E / V0130-H-QUAL6 / Exit 00227`; no new formal exit is allocated.

APG166N delivers:
- **B1**: Real source-owned live D1 API (`run_live_d1`) executing the maintained provider runner through an internal transport seam and refusing caller parameter overrides before provider start.
- **B2**: Answer-neutral probe with expected nonce completely removed from prompt bytes; oracle derives expected value strictly from the materialized fixture and enforces valid Read observation.
- **B3**: Explicit schema/provenance separation (`live-provider` vs `instrumented-provider-free`), record digest binding, and refusal of instrumented evidence by `make_d1_readiness_candidate()`.
- **Dynamic model derivation**: Model derived from current source policy (`normal-final-review -> primary -> catalog`), verified against descriptor.
- **Structural non-holdout boundary**: Structural rejection of Scenario 01–15 references, context-eval corpus paths, and traversal.
- **B4**: Manager-bound global one-use custody (`custody_root / "consumed-attempts" / f"{attempt_key}.json"`).
- **B5**: Exact observed Read-only surface (startup tools strictly Read only, structured rejection codes for forbidden tools `Bash`, `Write`, `Edit`, `Agent`, `Glob`, `Grep`, `WebFetch`, `WebSearch`, `NotebookEdit` and non-empty MCP).
- **B6**: Real evidence captures for Git state, isolated settings, runtime manifest, and executables.
- **B7**: Complete readback recomputation and tamper rejection requiring repo root and physical non-symlink `stdout.bin`/`stderr.bin`.
- **B8**: Fresh APG166N 15/15 carry-forward transaction (`qualification/provider-free-transaction-final`, digest `2ff6b621442fb93b56ddbed5e7a71d9f6763bd22dada3678fb1fb0f7b2285c93`), verified across 15 records, 15 initial trees equal, 15 subject pairs unchanged, 25 promotion fixture pairs, all attestations recomputed, zero provider invocations, and zero sentinels.

All 22 dedicated D1 seam tests in `test_h_d1_seam.py` pass; all 143 evaluation suite tests pass.
Real provider starts authorized in APG166N: **ZERO**.
Live D1 remains reserved for APG166P after exact-source manager acceptance. Static remains default;
publication and V0130-I remain unauthorized.

### APG166O D1 seam convergence and final provider-free qualification

APG166O converges the production and provider-free D1 execution paths onto a single private internal attempt owner (`_execute_d1_attempt`) in `testing/h_eval/d1_qualification.py`, resolving all outstanding blocking findings B1–B8 from the APG166N independent review and manager disposition entirely provider-free under continuation `V0130-H-D1-SEAM3`. Formal product identity remains `APG166E / V0130-H-QUAL6 / Exit 00227`; no new formal exit is allocated.

APG166O delivers:
- **B1**: Single internal attempt engine shared by production `run_live_d1` and provider-free `run_instrumented_d1_lifecycle`. Fixes the undefined importer variable (`imp` NameError) and unexecuted branches on the production path. Public `run_live_d1` accepts no kwargs/transport overrides.
- **B2**: Strict native Read observation requirement in `evaluate_d1_response` (missing or None cannot pass). Raw provider stream drives the observer and oracle; recomputed observations are compared against copied summaries and fail on mismatch. Expected nonce marker derived strictly from source fixture / materialized probe receipt.
- **B3**: External live provenance derived from manager authority, custody ledger, and transport receipt (`production-provider` vs `instrumented-provider-free`), not mutable record JSON self-hashes. Reversed forgery test ensures fake JSON converted to live and re-digested strictly fails readback.
- **B4**: Canonical `authority_digest = sha256(canonical authority without authority_digest)`, strict format validation for authority ID and attempt ID, and atomic pre-launch consumed attempt ledger bound to canonical custody root path, authority digest, probe ID, source identity, and attempt ID.
- **B5**: Complete launch contract capture and inspection binding provider `claude`, profile `normal-final-review`, model from source policy, role `Work Review`, startup tools strictly `["Read"]`, MCP strictly empty `[]`, permission `plan`, settings sources, directory grants, and isolated roots.
- **B6**: Real sealed runtime manifest, actual settings sources captured from isolated home (not synthetic dictionaries), and executable evidence inspecting the physical Claude CLI (version 2.1.259) rather than hashing `sys.executable`.
- **B7**: Complete 16-artifact raw custody inventory check, observer inputs serialization without raw binary payloads (`observer-inputs.json`), and replayable native Read and oracle recomputations.
- **Git mutation refusal**: Explicit failure injection refusal ensuring fake provider cannot mutate repository-controlled paths (`REPO_ROOT`).
- **Structural non-holdout boundary**: Full structural rejection of `scenario-01` through `scenario-15`, casing variants, and context-eval corpus directory traversal.
- **B8**: Fresh post-stability 15/15 carry-forward transaction (`qualification/provider-free-transaction-final`, dry-run digest `8686441b3d57c6ebb079da7b2a295d0ba06dd87fe6963e08b0c07c4476632016`, runtime manifest `5865d840a20015278bcd2a98cbb0aa34fbd4c82245fe6ddadc1e92beb58515d5`), verified across 15 records, 15 initial trees equal, 15 subject pairs unchanged, 25 promotion fixture pairs, all attestations recomputed, zero provider invocations, and zero sentinels.

All 32 dedicated D1 seam tests in `test_h_d1_seam.py` pass; all 169 evaluation suite tests pass across 6 focused suites.
Real provider starts authorized in APG166O: **ZERO**. Observed provider invocations: 0. Sentinels: 0.
Live D1 remains reserved for later qualification after exact-source manager acceptance. Static remains default;
publication and V0130-I remain unauthorized.

### APG166P D1 seam final correction (amend / diagnostic carry-forward)

APG166P addressed provider-free transport divergence, Darwin path canonicalization for SQLite writer-wal, and live vs instrumented authority schemas under continuation `V0130-H-D1-SEAM4`. Independent work review resulted in disposition: amend (11 findings sustained), and manager disposition retained its 15/15 evidence as diagnostic only. Formal product identity remains `APG166E / V0130-H-QUAL6 / Exit 00227`; no new formal exit is allocated.

APG166P delivers:
- **SQLite writer-wal regression resolution**: Diagnosed and resolved Darwin path canonicalization in `testing/h_eval/promotion_oracles.py` (`work.resolve()` and `real_work.resolve()`), updated preregistration hash (`oracle_source.sha256 = 0b524c740fa3d0628e815617a61d15be813eec455eb3f86e35324ec8c7aa61a0`), and corrected executable resolution in `test_h_promotion_qual6.py`. All 9 tests pass in 149.39s (100%), qualifying all 25 fixture pairs (50 receipts).
- **B1**: Complete elimination of provider-free transport divergence. Production `run_live_d1` and provider-free runs enter the identical `context_adapter.invoke(prep, provider.run, argv, prompt_b, edir, environment=clean_env)` process path with a source-owned fake native `claude` executable placed in `PATH` underneath provider resolution.
- **B6**: Physical Claude CLI (`2.1.259 (Claude Code)`) and Codex CLI (`0.153.3`) inspected directly via bounded `--version` probes without model/task requests. Sealed runtime manifest binds physical executable paths, versions, and non-null digests.
- **B3**: Strict schema-level separation between `LIVE_AUTHORITY_SCHEMA = "apg.d1-live-authority/v1"` and `INSTRUMENTED_AUTHORITY_SCHEMA = "apg.d1-instrumented-authority/v1"`. Live readiness rejects instrumented authority at schema level. Anti-forgery closure: forging fake receipts to live fails readback.
- **B4**: Custody ledger binds authority schema, canonical digest, `launch_contract_digest`, `provider_start_receipt_digest`, and `guard_receipt_digest`.
- **B2/B5/B7**: Retained prompt custody (`prompt.bin`), answer-neutral verification, source-rederived launch contract from repository source owners at readback, recomputed raw Read structures and delivery receipts, and verified isolation roots.
- **Tripwire launch accounting and structural holdouts**: Direct process launch accounting (`guard.account_fake_process`) and expanded holdout regex (`(?i)(?:\b|[a-z0-9_-]*_)scenario[-_\s]*0?([1-9]|1[0-5])(?=[^a-zA-Z0-9]|$)`).
- **B8**: Diagnostic 15/15 transaction on tree into `qualification/provider-free-transaction-final` (dry-run SHA-256 `f6e642f69e8dfe2d44d18c20a659a94db2987ba93e6f34320548cc01a67dfc12`, runtime manifest `5865d840a20015278bcd2a98cbb0aa34fbd4c82245fe6ddadc1e92beb58515d5`). All 15 scenario records complete, 15 initial trees equal, 15 subject pairs unchanged, 25 promotion fixture pairs (50 receipts) passing, 0 provider invocations, and 0 sentinels.

All 32 dedicated D1 seam tests in `test_h_d1_seam.py` pass; all 177 evaluation suite tests pass across 7 focused suites.
Real provider starts authorized in APG166P: **ZERO**. Observed provider invocations: 0. Sentinels: 0.
Actual one-shot live D1 remains reserved for later qualification after exact-source manager acceptance. Static remains default;
publication and V0130-I remain unauthorized.

### APG166Q / APG166Q-R1 D1 seam recovery and qualification

APG166Q was launched to resolve the 11 sustained APG166P findings under continuation `V0130-H-D1-SEAM5`, but the producer was interrupted before completion (~40324s duration, candidate capture retained).
APG166Q-R1 recovers the exact candidate in place under continuation `V0130-H-D1-SEAM5-RECOVERY1` (native phase `APG166QR1`). Formal product identity remains `APG166E / V0130-H-QUAL6 / Exit 00227`; no new formal exit is allocated.

APG166Q-R1 delivers:
- **Process creation observation hook**: Added `PROCESS_CREATION_HOOK` in `libexec/agent_phase/provider.py`, directly observed by `LaunchGuard._on_process_created` at the `subprocess.Popen` boundary. Hook exceptions terminate and reap the spawned child process via `_terminate(process)` and close activity file descriptors without process leaks.
- **B3 live vs instrumented authority separation**: Distinct schemas (`LIVE_AUTHORITY_SCHEMA` vs `INSTRUMENTED_AUTHORITY_SCHEMA`). Live readiness candidate generation structurally rejects instrumented authority, provider-free guard receipts, and fake executables. Anti-forgery closure: forging fake receipts to live fails readback.
- **Closed allowlisted environment**: Built strictly from scratch without ambient environment leakage (`os.environ` secrets excluded).
- **Independently rederived settings and launch contract**: Source owners (`claude_vc_profile`, `provider.build_argv`, `scenario-bindings.json`) rederive settings sources and launch contracts at readback; synthetic caller dictionaries prohibited.
- **Raw stream Read and delivery recomputation**: Complete recomputation of raw native Read structures and delivery entries from raw observer events.
- **Runtime separation**: Distinct production-expected runtime (physical CLI `--version` probe, fallback constants prohibited) and instrumented-executed runtime.
- **Full authority and custody revalidation**: Custody ledger binds provider-start receipt digest and authority; attempt state terminal semantics verified.
- **Disposable Git mutation proof**: Executes against an isolated disposable Git repository and detects mutation failure without touching the APGR repository.
- **Complete negative matrix**: 36+ negative test cases in `test_h_d1_seam.py` covering custody, tamper, leak, and stream failure cases.
- **SQLite writer-wal isolated causal proof**: Demonstrated that Darwin temporary directory path canonicalization (`/var` vs `/private/var`) alone reproduces the failure under uncanonicalized paths and resolves under canonicalized paths with Python executable selection held constant.
- **All 25 promotion fixture pairs**: All 25 GOOD/BAD pairs pass under `test_h_promotion_qual6.py` (9 tests, 50 receipts).
- **B8 fresh exact-source transaction**: Fresh final 15/15 transaction into `qualification/provider-free-transaction-final` postdating all source/test/docs changes, retaining 15 complete scenario records, 15 equal initial trees, 15 unchanged subject pairs, 25 passing promotion pairs, 0 provider invocations, and 0 sentinels.

All 34 dedicated D1 seam tests in `test_h_d1_seam.py` pass; the historical summary reported an unreconciled aggregate of 188 across 7 focused suites.
Real provider starts authorized in APG166Q-R1: **ZERO**. Observed provider invocations: 0. Sentinels: 0.
Actual one-shot live D1 remains reserved for APG166R after exact-source manager acceptance. Static remains default; publication and V0130-I remain unauthorized.

### APG166R D1 seam blockers R1–R4 resolution and qualification

APG166Q-R1 review returned disposition: `amend` sustaining four blockers (R1–R4).
APG166R executes the narrow correction of the recovered APG166Q-R1 checkpoint (retained as historical diagnostic evidence) under continuation `V0130-H-D1-SEAM5-CORR1`. Formal product identity remains `APG166E / V0130-H-QUAL6 / Exit 00227`; no new formal exit is allocated.

APG166R delivers:
- **R1 launch-owner custody authority**: Launch-owner Popen facts (PID, PGID, SID, physical executable/digest, exact argv/digest, actual cwd, executed environment digest, explicit allowlisted env, source identity, timestamp) become authoritative in the custody chain; start receipt is finalized at Popen; attempt ledger transitions from `prelaunch_consumed` to `start_finalized` atomically binding the start receipt digest. Child startup evidence serves strictly as corroboration. Negative tests 9–15 in `test_h_d1_seam.py` verify all negative/tamper paths.
- **R2 standalone SQLite writer-wal causal proof**: Dedicated `qualification/sqlite-writer-wal-causal-proof/` holds Python executable, environment, fixture bytes, and oracle source completely constant, demonstrating Darwin `/var` vs `/private/var` alias observation is the sole differentiating factor (exit 1 vs exit 0). All 25 GOOD/BAD promotion pairs (50 receipts) re-verified passing under `test_h_promotion_qual6.py`.
- **R3 durable test batch receipts and count reconciliation**: Durable batch receipts retained in `qualification/test-batch-receipts/` across all 7 focused evaluation suites (`test_h_d1_seam.py`: 34, `test_h_claude_reads.py`: 80, `test_h_delivery.py`: 20, `test_h_arm_evidence_qual6.py`: 20, `test_h_promotion_qual6.py`: 9, `test_h_provider_free_guard.py`: 8, `test_h_provider_free_readiness.py`: 8), confirming all 179 unique focused cases pass cleanly (exit=0 across all suites). 188 was a historical unreconciled aggregate; its cause was not proven by retained evidence. APG166R1 receipts replace the unsupported double-count explanation.
- **R4 handoff and documentation current-state truth**: Handoff and documentation reconciled to current-state truth; next tranche set to APG166S (workers/config); live D1 reserved for APG166T.
- **B8 fresh exact-source transaction**: Fresh final 15/15 transaction into `qualification/provider-free-transaction-final` (dry-run SHA-256 `990201aae5b3d9cc0a866db16e57510b6981b9bab2c9833c359fc46299d3ab02`, runtime manifest `5865d840a20015278bcd2a98cbb0aa34fbd4c82245fe6ddadc1e92beb58515d5`). All 15 scenario records complete, 15 initial trees equal, 15 subject pairs unchanged, 25 promotion fixture pairs, all attestations recomputed, zero provider invocations, and zero sentinels. Package seal generated in `qualification/provider-free-transaction-final-seal.json` with all mechanical gates passing.

All 34 dedicated D1 seam tests in `test_h_d1_seam.py` pass; all 179 evaluation suite tests pass across 7 focused suites.
Real provider starts authorized in APG166R: **ZERO**. Observed provider invocations: 0. Sentinels: 0.
Workers and home-config subsystem migration are scheduled for APG166S; actual one-shot live D1 remains reserved for APG166T. Static remains default; publication and V0130-I remain unauthorized.


## APG166R1-R1 recovery candidate — interrupted before final B8

Formal identity remains APG166E / V0130-H-QUAL6 / Exit 00227. Recovery
continuation is V0130-H-D1-SEAM5-CORR2-RECOVERY1; native phase is APG166R1R1.
The interrupted APG166R1 partial source change is preserved and completed in
place. Its transport failure established no completed qualification or review.
APG166R's independent review retained R4 as resolved and R1/R2/R3 as partial.

The candidate independently derives launch argv, environment and executable
identities for both authority branches. Actual outer Popen facts are separate
from the native profile child. The child corroborates the native launch owner's
PID and complete source-derived argv; it does not authorize a launch.
Receipt hashes establish local custody consistency and tamper detection, not
cryptographic security against a hostile same-user process.

Portable helpers take the run-owned qualification directory explicitly. The
SQLite comparison retains both vectors, the exact six-path preregistered oracle
identity, fixture bytes and execution outputs. Its conclusion is derived from
those records using an alias and physical path to the same disposable fixture.
This is controlled path-alias reproduction, not a claim about every filesystem.

188 was a historical unreconciled aggregate; current exact-source durable
receipts establish 184 unique focused node IDs. Counts are computed from retained
pytest node outcomes, not fixed acceptance assertions. Runtime, provider cleanup
and receipt-owner tests remain separate from that aggregate. Every rerun retains
an exclusive attempt; reconciliation selects authoritative attempts and lists
superseded attempts. Final qualification must pass on the stabilized candidate
before the final B8 transaction; run-owned receipts and seal carry the results.

Historical B8 transactions remain distinct: APG166Q-R1 and APG166R each retained
15 complete records, 15 equal initial trees, 15 unchanged subject pairs and 25
promotion fixture pairs, with zero provider invocations and zero sentinels.
Those transactions do not qualify this changed candidate. The final APG166R1-R1
B8 requires fresh readback, a package seal and a durable runner receipt.

At that recovery, source acceptance and all five skill dispositions remained
pending the single dispatcher-owned independent work review. No live model/task/provider
session is authorized. APG166S remains the workers/config tranche; APG166T
remains the one-shot live D1 reservation. H stays static by default, its gate
remains false, and V0130-I remains unauthorized.


## APG166R1-R2 recovery candidate — amended after independent review

Formal identity remains APG166E / V0130-H-QUAL6 / Exit 00227. Recovery
continuation is V0130-H-D1-SEAM5-CORR2-RECOVERY2; native phase is APG166R1R2.
APG166R1-R1 reached passing focused, static and SQLite receipts, then its outer
semantic session hit a usage limit while the final B8 ran in the foreground.
No B8 assertion failed. That partial B8 completed nine scenarios, has no
summary or seal, and is retained only as aborted diagnostic evidence; it is
neither resumed nor promoted.

The native launch owner's environment digest is classified
`diagnostic-non-authoritative` (manager option B). The native Popen mapping
includes host launcher additions, such as shell `PWD`/`SHLVL` and toolchain
shim `SDKROOT`/`CPATH`/`LIBRARY_PATH`/`MANPATH`/`LC_CTYPE`, that readback cannot
derive from source. The field is therefore `diagnostic_environment_digest` with
an explicit classification. Readback rejects an authoritative-looking native
`environment_digest`, a missing or non-diagnostic classification and a
malformed digest, and never uses the value for custody. Authoritative
environment custody remains the outer launch-owner start receipt, whose digest
and allowlist are independently derived for both authority branches.

The SQLite comparison now retains the complete physical fixture inventory
before and after each vector. Its derived conclusion additionally requires no
baseline residue, an identical canonicalized starting state and no
canonicalized residue.

These source changes invalidated reuse of the APG166R1-R1 receipts, and the
focused, separate-regression, static and SQLite receipts were rerun on the
changed exact candidate. The required provider stream/cleanup receipt
(`agent_phase_provider_stream`) failed: 48 collected, 39 passed, 9 failed,
0 errors, exit 1. The nine failures are cleanup and liveness cases whose
process-group cleanup proof calls `/bin/ps`, which the semantic sandbox
denied. The selected reconciliation therefore reported
`all_selected_passed=false`, with `same_candidate=true` and
`required_suite_coverage=true`. The final B8 then ran and was mechanically
green, but it does not qualify the candidate: its prerequisite that every
selected attempt pass first was false. That reconciliation derived 188 unique
focused node IDs. Its relation to the APG166R1-R1 set (184 plus four) was
asserted without a set comparison and is not established.

The dispatcher-owned independent work review returned amend. The failing
provider-stream receipt was blocking (F1), and this section had omitted it
(F2). The review also raised native launch-facts custody, count derivation,
reasonless xfail and host-path portability advisories. Revise-close was
repository-read-only and confirmed F1 from retained evidence.

## APG166R1-R3 source correction — independent source review pending

Formal identity remains APG166E / V0130-H-QUAL6 / Exit 00227. Recovery
continuation is V0130-H-D1-SEAM5-CORR2-RECOVERY3-SOURCE; native phase is
APG166R1R3. This phase corrects source only. Process-group cleanup proof is
unchanged: an unknown or unproven group is not accepted in order to pass a
sandbox that denies `/bin/ps`.

- Native launch facts (`d1.context-launcher-deliveries.json`) are a required
  regular non-symlink artifact. Execution binds their exact bytes and SHA-256
  into a `native_launch_custody` object inside the digest-bound
  `d1-record.json`; a record without that custody cannot qualify. Readback
  reads the file without following links and compares it with the custody
  before trusting `launch_facts`. Absent, symlinked, unreadable or mutated
  facts raise `D1ReadbackError`. The facts are observed once at successful
  native Popen; readback does not re-observe a terminated child's PID,
  process group or session. The native environment digest remains
  diagnostic-non-authoritative (option B).
- `node_set_delta` compares two reconciliations' `unique_nodeids` and returns
  prior and current counts, added, removed and unchanged node IDs, the set and
  count equations, and validity. A prior-to-current count relation, including
  one from 184, is stated only after the host gate supplies both
  reconciliations and the helper validates them.
- The pytest receipt summary treats an xfail marker as present whenever
  `wasxfail` is not `None`, so reasonless xfails and xpasses are no longer
  counted as skips or passes.
- The focused-batch runner exits successfully only when every selected attempt
  passed on one candidate with required suite coverage
  (`covering_qualification`). A partial run cannot claim covering
  qualification.
- The remaining host-path literal in the current readiness history is replaced
  by a placeholder. Portability regression covers the current APG166E
  surfaces and the host-portable qualification helpers.

After these source changes every APG166R1-R2 receipt, reconciliation and B8
is historical for the new candidate. Manager-owned host qualification (all ten
suites in one covering reconciliation, then static and SQLite receipts) and a
fresh final B8 follow in that order and are pending. Neither final
qualification nor APG166S readiness is claimed. A source-accept disposition
from the dispatcher-owned independent review means only readiness for host
qualification. No live model/task/provider session is authorized. APG166S
remains the workers/config tranche; APG166T remains the one-shot live D1
reservation. H stays static by default, its gate remains false, and V0130-I
remains unauthorized.

## APG166S worker/configuration candidate

APG166R1 manager finalization is the accepted entry. Its historical correction
records above are preserved. APG166S implements the separate workers/config
tranche under ADR 0075 (Proposed); it does not reopen R1 findings.

The [APG166S evaluation](evaluations/apg166s-workers-and-canonical-configuration.md)
records proposal amendments, implementation and qualification boundaries. The
candidate is not deployment authority. Four observed worker canaries and D1
source carry-forward require separate disposition. APG166T remains reserved;
no live D1 or H holdout is authorized. H default is static and its gate is false.


### APG166S-R1 bounded repair checkpoint

The manager authorized a new entry-adopted repair of the retained APG166S
candidate: coherent selected model authority, launch-evidence and canary-budget
repairs, and separate current-home provider-free qualification. The predecessor
remains blocked history. The reviewed candidate has terminal corrections and
remains blocked for manager disposition. No APG166T, live D1, H holdout, promotion, V0130-I, deployment or
publication authority follows from it.

APG166S-R1 closeout retains the adopted candidate and amends the reviewed work.
The Git-check exception is restricted to read-only leaves; auth-failure evidence
and inherited-context filtering are corrected. Focused provider-free checks pass.
The producer's one qualifying case remains historical: zero of four cases
qualify the changed terminal runtime. Six attempts remain consumed, both Luna
budgets exhausted. ADR 0075 stays Proposed. This grants no APG166T, live D1,
H promotion or V0130-I authority.

### APG166S-R2 bounded work candidate

R2 continues the retained terminal candidate under the manager reconciliation.
Exact historical Claude session joins support external Luna's missing parent
effort, while native Luna retains its original child-bound observation. Separate
path and fake-provider evidence proposes both Luna cases for carry-forward with
explicit environment limitations; original receipts are unchanged.

Ordinary selected-home routing receives provider-free coverage. V2 parent
selection and captured capability/model authority are corrected, including
authority propagation through the existing retry path. Gemini terminal labels
separate completion-fence delivery from provider interruption. Correlated local
Gemini records exist, but no supported effective model/effort extraction was
identified on the inspected surfaces; both fields remain unknown. No acceptance
attempt was added to the original six-entry budget.

The [R2 evaluation](evaluations/apg166s-workers-and-canonical-configuration.md#apg166s-r2-bounded-observation-and-route-candidate)
owns findings, verification boundaries and limitations. Bounded closeout amends
the independently reviewed candidate, with Gemini investigation and Claude worker
launcher coverage limitations retained. Overall APG166S acceptance remains open.
ADR 0075 remains Proposed; APG166T, live D1, H promotion and V0130-I remain outside
authority.

### APG166S acceptance and APG166T launch preparation

APG166S is accepted after local R2 finalization, including all four parent/worker
combinations and both Luna carry-forwards. ADR 0075 is Accepted and owns the
settled provider-contract standard: correct selected parameters are trusted;
missing internal provisioning metadata is not a failure or acceptance blocker.
Earlier R1/R2 findings and receipts above remain historical.

APG166T-PREP1 prepares a minimal external handoff for the existing D1 owner,
with a non-consuming check and a separately authorized one-shot execute path.
Preparation grants zero D1 starts; D1 has not been executed by this phase.
Finalized prep commit/tree bindings belong to the later manager authority file;
documentation-only changes do not reopen accepted source qualification.
H remains static by default with its gate false. No holdout, promotion,
V0130-I, installed configuration change, deployment or publication is authorized.

### APG166T failed launch and bounded repair

The separately authorized first D1 launch failed with an explicit authentication
error in its launch context, zero API usage and zero native Read calls. Its
native argv exposed the ordinary five-tool read-only surface instead of D1's
required Read-only selection. Failure capture withheld the completion receipt,
and the original readback remains refused or incomplete. This does not establish
that the operator's normal login expired or that native Read is broken.

APG166T-REPAIR1 is limited to preserving supported authentication context while
isolating task settings, delivering the exact D1 tool selection, and distinguishing
provider failure from capture failure. Qualification uses fake executables only.
The original failed record, receipts and consumption state remain historical;
the attempt is consumed and no missing receipt is synthesized. APG166S and all
four accepted worker combinations remain closed. This repair grants zero live
D1 starts; a later attempt requires a separate manager decision and fresh grant.

The repair candidate uses the operator authentication home and a closed identity
environment rather than an empty production HOME. Supported safe mode suppresses
custom instructions, hooks, skills, plugins and agents; plan permission mode,
Read alone, strict-empty MCP and controlled task/temp directories remain fixed.
Session persistence is disabled. Administrator-managed provider policy still
applies, and provider authentication bookkeeping or internal refresh behavior is
not represented as controlled task output. Unexpected advertised startup
customizations or memory paths fail qualification. Help-gated auth-status
preflight refuses unauthenticated, unsupported or indeterminate status before
consumption; it does not guarantee network or future provider success.

Prospective completion receipts distinguish a fully captured nonzero provider
result from successful inference. Semantic provider errors remain explicit even
when the provider reports a success subtype. Failed readback can inspect retained
failure diagnostics without satisfying strict qualification. Independent pre-final
review returned advisory findings. Closeout separates valid raw-stream receipts
from incomplete runner capture, retaining failed diagnostics without qualification.
The terminal amendment passed focused fake-provider verification; it has not
received another independent review. Historical exact-byte replay remains private,
two nearby failures have unresolved baseline attribution, and readback still
requires the recorded authentication directories to exist.

The repair's non-inference diagnostic observed a selected CLI version different
from the existing D1 version requirement. The requirement is unchanged, and
current selected-runtime compatibility remains refused before consumption.
Fake-provider verification is not live launch readiness. A manager runtime or
version-pin decision must precede any fresh live grant.

### APG166T-COMPAT1 compatibility preparation

The manager-authorized compatibility candidate retains the operator-selected
CLI and updates D1's one exact current pin to its observed stable version
2.1.281. Current fake-provider version and startup records derive from that pin;
historical results and grants retain their original versions. The generic
doctor's HOME-free probe reports a different version from the same physical
executable in the repaired operator context. D1 therefore checks the exact pin
in its closed launch environment while retaining the doctor's compatibility
gate. Authentication, Read-only argv, experiment route and single-use accounting
remain unchanged.

Focused fake-provider tests cover fixed version mismatches, context-dependent
version reports, stable-banner refusal, startup drift and the actual wrapper.
The affected run has 231 passes and four nearby fixture failures caused by a
missing authentication-context artifact; no pristine-entry rerun is claimed.
Startup-version drift fails qualification after consumption, but its retained
failed record currently cannot pass native-read recomputation during readback.
These limits are recorded without expanding this compatibility repair.

The non-consuming agent-context source preflight passes version selection and
refuses at supported auth status as unauthenticated. That does not establish the
operator's host login state; the separate post-dispatch host preflight remains
pending. Preparation is complete after independent work review and terminal amendments,
not live qualification: zero real
D1 starts occurred, D1-01 remains failed and consumed, and a fresh manager grant
is still required. The physical file hash binds the launcher only, not its HOME-resolved
implementation. Closed-context preflight and startup version checks retain a
race if that implementation changes after preflight; the consumed-attempt and
failed-readback limitation above remains explicit. The two earlier nearby failures with unresolved entry attribution,
private replay portability and authentication-directory readback limits remain
separate. No H promotion, successor execution or v0.13 release qualification is
conferred.

### APG166T-D1-02 result and REPAIR2 evaluator correction

D1-02 completed one direct native Read of the correct fixture and returned its
exact nonce. Provider execution succeeded with exit zero, complete capture and
successful failed-result readback. The manager accepts that observed functional
evidence. APG166S and all four worker combinations remain accepted and closed;
REPAIR1's authentication/tool/capture repairs and COMPAT1's version choice remain
settled.

The executed evaluator's historical result remains failed and
unqualified_with_readback. It rejected provider-advertised builtin plugins and
the omission of an optional builtin agent. Its oracle also rejected the sole
fenced JSON response, but that independent failure was missing from the recorded
failure reasons. The historical record, receipts, grants and consumption state
are not rewritten.

REPAIR2 permits structurally consistent builtin-provenance plugin metadata and
subsets of the existing builtin agent inventory. External paths, custom agents
and malformed inventories still fail. These labels are diagnostics, not proof
of total provider-internal isolation or permission to delegate. Read-only tools,
empty MCP, plan mode and safe-mode/session settings remain required. Observed
non-Read calls, nested envelopes or positive subagent spawning/depth fail.
The D1 response interpreter accepts bare JSON or one complete, unambiguous JSON
fence in the final provider result, including surrounding prose. Duplicate keys,
multiple terminal responses and malformed/truncated responses fail; the generic
Work Review importer is unchanged. Failure explanations now include the oracle
and all independently evaluated decision conditions in execution and readback.

The separate source-bound offline replay passes the amended evaluation on the
unchanged retained bytes. It is not a fresh provider run or live qualification
of the changed evaluator. REPAIR2 performs zero real D1 starts; both historical
attempts remain consumed. The earlier 14 nearby failures and the separate
231-pass/four-failure result remain disclosed and unresolved by this repair.
Empty-index capture remains deferred to v0.14.0. This bounded pre-final candidate
confers no release qualification, H promotion, V0130-I authority, deployment or
automatic successor. Agent-Central remains untouched and independent.


### APG166U-REGRESSION1 bounded regression candidate (historical dispatch)

The manager has accepted finalized REPAIR2 and closed D1 native-Read capability
and the separate corrected offline replay. REPAIR2 was finalized at commit
`7a49c604d15d9928539450e2555702e181911b15`, tree
`50c668fbebddf9a4b9d27243c85235b6dc95b6a1`, as recorded in the manager's
finalization disposition. Neither acceptance rewrites
the failed/consumed D1-01 or D1-02 records or claims a fresh live execution of the
corrected evaluator. No D1-03 is required. APG166S and its four combinations remain
closed under the accepted selected-parameters/provider-trust standard.

The regression candidate repairs authentication-context setup, the current Codex
read-only profile, APGR facade collision setup, and disposable execution-package
bindings. Current-source F accounting is separated from its sealed baseline;
APG166S-R2 standing-source changes explain only standing identity, mandatory cost,
payload cost and content identity deltas. A current Go binary reproduces the
frozen accounting when given the original standing inputs. Budgets, mandatory
doctrine, frozen scenarios and oracles are preserved.

Terminal closure remains blocked by the real-stage/fake-child test environment:
process identity observation is denied before supervisor handoff, so no successful
child integration is claimed. The launch diagnostic is retained; its assertions
and production custody requirements remain intact. The adjacent preregistration
fixture now uses the same disposable current-source bindings, preventing stale
route hashes from masking its intended negative checks. This is test scaffolding,
not H rebinding, readiness resealing or experimental qualification.

The H gate remains false, static remains default, and promotions remain zero.
Current route bindings and source/readiness seals need explicit disposition before
any later H evaluation. V0130-I conformance, publication and cutover remain later,
unauthorized gates. Empty-index capture remains deferred to v0.14.0. Independent
pre-final review confirmed the remaining blocker and retained test contracts.
Closeout amends the finalization reference; manager acceptance remains external.
The next action is the unchanged five-module provider-free rerun in an authorized
environment that permits process-identity observation.


### APG166V-H-READY1 current-source preparation

REGRESSION1 is finalized and CLOSED under the manager's accepted HOST2
verification: the unchanged integrated invocation passed all 197 cases, including
all eighteen recorded regressions. The preceding blocked semantic dispatch and
failed HOST1 remain historical; the requested host rerun above has been fulfilled.
The exact finalization identities remain in the manager's retained evidence packet.
Accepted adjacent results are carried separately, not added to the HOST2 count.
APG166S parameter/provisioning acceptance and D1 native Read capability plus the
separate corrected REPAIR2 offline interpretation remain settled. Both original
D1 attempts remain failed and consumed. No D1-03 is required.

READY1 refreshes operative H route-source bindings without changing frozen tasks,
oracles, budgets, skill bodies or stable-maturity criteria. Its carry-forward
representation preserves observation, replay, mechanical checks and external
acceptance as distinct facts. The [preparation record](evaluations/apg166v-h-ready1-preparation.md)
owns this candidate's scope. Dispatcher pre-final review individually accepts all
five preregistrations conditional on host provider-free fixture qualification;
it is not positive guidance use or promotion. Preparation remains blocked: a
manifest-required Scenario 14 subject is ignored and absent from the Git product,
and the single authorized mechanical transaction failed. Manager disposition of
that input and explicit authorization of another transaction are required.

The next decision concerns the concrete non-authorizing H package. Live admission,
a single-invocation promotion runner and an externally accepted ready seal remain
unavailable, and need bounded implementation/review before any source-bound grant.
Scenario 15 remains contingent/unavailable: subset results cannot establish the
full H benefit gate. Zero live H, calibration, D1 or promotion tasks run here.
Static remains the default; the H gate is false and stable promotions are zero.
V0130-I, publication and cutover remain unauthorized. Empty-index capture remains
deferred to v0.14.0; Agent-Central remains independently available.


### APG166V-H-COMPLETE1 granted execution path preparation

COMPLETE1 adopts READY1's preserved candidate and the user-authorized
`claude_only` source correction, then implements the H interfaces READY1 left
absent. The [completion record](evaluations/apg166v-h-complete1.md) owns scope,
evidence separation and limitations. Scenario 14's manifest-required subject is
now in the Git product through an exact-file ignore exception; its bytes and
manifest digest are unchanged. Route-source digests are refreshed for the mode
correction only; H providers, profiles, models and efforts are unchanged.

Live H arms and promotion cases are admitted only by an external manager
decision and grant, consumed once per unit across all grants before any context
or provider work, and retained with readable failures. Assembly aggregates only
granted, retained arms; Scenario 15 stays contingent/unavailable with zero
planned starts and the whole-H benefit gate false. The prospective ceiling of 53
starts (28 scenario arms, 25 promotion cases) is enforced by those owners but is
not a grant. One provider-free host mechanical transaction is authorized after
review; its result is not claimed here. Zero live H, D1, calibration, holdout or
promotion starts ran. Static remains the default; the H gate is false and stable
promotions are zero. V0130-I, publication and cutover remain unauthorized.


### APG166W-H calibration stop, prelaunch repair and recovery boundaries

CALIBRATION1 admitted one pair under the first manager decision and grant and
consumed `scenario-01/static` before the arm's settings/discovery observation
refused, with zero recorded provider invocations. Its ledger, result, terminal
bytes, context plan, integrity record and accounting remain retained and
consumed-incomplete; the exact original failing entry and errno were not
recorded. The adaptive arm did not start and nine calibration units remain
unconsumed. No live calibration task result exists.

APG166W-H-PRELAUNCH1 is manager-accepted and locally finalized. It keeps
stale links in an existing provider skill root observable, adds bounded failure
detail to arm results, and adds a non-consuming prelaunch observation check.
Its accepted diagnosis is a current-layout reproduction, not a retroactive log.

APG166W-H-RECOVERY1 is a reviewed-candidate source preparation of two
prospective manager decisions, pending dispatcher finalization. First, an absent
provider global skill root is observed as absent: only the named root and the
identity metadata of its lexical path components are examined, recorded in an
additive `apg.h-discovery-observation/v2` receipt. No ancestor such as HOME or a
vendor store is inventoried and the prelaunch opt-in is retired; existing roots
keep the v1 receipt. This narrows the observation scope and does not claim an
ancestor was unchanged. Second, an H-only `apg.h-live-grant/v2` may name one
separate manager replacement authorization for a proven pre-provider failure.
The replacement is consumed by an additional record in the same custody root;
the original ledger and result are never modified, a unit is replaceable at most
once, and acceptance with a v2 grant counts only explicitly selected, complete,
current-decision calibration attempts. The historical `scenario-01/static`
failure is only a candidate for a later manager decision. No replacement,
successor grant, live H or D1 start, or mechanical transaction ran here. A later
current-source mechanical/runtime preparation and a preflight of every intended
provider, including Scenario 05, must precede any live grant. Static remains the
default; the H gate is false and stable promotions are zero.

CALIBRATION2 used the single authorized replacement of `scenario-01/static`. Its
runner returned exit 1 with empty stdout and 850 stderr bytes; the arm then
refused because a manifest-bound operator settings file changed during the arm,
and strict readback refused current runtime drift. The original attempt and its
replacement are both consumed, nine units remain unconsumed and no task
measurement exists. The stderr bytes would have been written only after the
refusing check, so they never were; only their digest survives and they are not
recovered. APG166W-H-POSTRUN1 is a reviewed evidence repair: it retains returned
provider streams before independent post-run checks, records provider-return
(including exit code and transport outcome), observation and runtime-close
outcomes together with bounded identity deltas, replaces a failed
post-run runtime record instead of leaving it pre-run valid, and adds an
integrity-checked, non-qualifying diagnostic readback that pair records keep
beside a strict readback refusal. The settings guard, discovery, admission,
consumption and replacement eligibility are unchanged, and no live H or D1 start
ran. The edited H owners change the current source identity that any later live
decision must bind. Static remains the default; the H gate is false and stable
promotions are zero.


### APG166X-PILOT1 operational pilot, observations and empty-index closure

The maintainer's September 29 pilot direction (§1a) is operative for new
ordinary work; the H addenda above remain dated history and their failed,
consumed and blocked records are unchanged. Old H experiment restrictions do
not govern ordinary dispatcher work. No calibration replay, ledger edit, new H
grant or promotion ran.

The empty-index candidate-capture defect is included in and closed for v0.13.0.
This supersedes the earlier "remains deferred to v0.14.0" sentences above, which
are retained as historical wording. The current source already contained the
narrow guarded tracked refresh accepted under APG166K; APG166X reproduced the
failure with the reported earlier implementation, confirmed the current source
and captured generation succeed in the same temporary index, and added the
remaining real-Git regressions (staged deletion of the final tracked file,
staged and intent-to-add content, nested invocation, ignored metadata, tracked
fixtures under ignored directories, literal unusual names, executable mode and
an unborn-HEAD characterization). The candidate-capture implementation is
unchanged.

APG166X adds optional per-attempt dispatch observations on the normal V1 and V2
paths and a provider-free summary, index and feedback command family; see
[operational observations](guides/operational-observations.md). Adaptive context
mode is an explicit experimental opt-in that plans prospectively and launches
static transport; no normal route has a qualified selective projection. Static
remains the default and stable promotions remain zero.

## APG166Z-CONTEXT1 addendum: ordinary context delivery and explanation

This pilot development slice (not an H campaign) implements the next context
increment on canonical development:

- The adaptive opt-in now delivers the planner's selected optional skills to
  the native Claude child on the ordinary `claude-profile` seam, covering the
  five V1 `claude_only` `implementation_testing` stages and Claude bindings in
  V2 through one shared seam. The mandatory prompt stays byte-identical; the
  wrapper composes the run-owned APGR MCP acquisition server beside the worker
  facade, with exact recovery copies for budget-deferred requests. Other
  providers and isolated-settings profiles keep static transport with
  `route_unsupported:<code>`. Static remains the default.
- Planning receives structured facts from project/home configuration,
  dispatch flags (`--context-fact`, `--context-skill`, fresh dispatches only)
  and a small fixed manifest table, with per-kind precedence and visible
  `overridden`/`conflicting`/`unknown` statuses.
- `apgr dispatcher observations explain` shows one run's context decisions,
  byte views and fallbacks without an index; `summarize` adds delivery and
  route-support counts.
- The [observability direction](architecture/v0-13-observability-direction.md)
  is adopted into normal planning (CLI-first; list/live/timeline/dashboard are
  future).

The APG166X sentence above ("Adaptive context mode ... launches static
transport; no normal route has a qualified selective projection") is retained
as history and superseded by this addendum for the Claude route. No live model
benefit, token saving, promotion or H qualification is claimed; a future
ordinary operator dispatch supplies operational feedback.

## APG166ZA-OBSERVABILITY-RUNS1 addendum: run discovery

This ordinary development slice (not an H campaign) adds
`apgr dispatcher observations list`: bounded, file-based discovery of V1
outbox leaves, historical project-level leaves, verified V2 projections and,
with `--v2`, canonical V2 runs. Each row reports recorded runtime state
separately from telemetry coverage, with attempt, context-mode, worker,
build and feedback counts and a path-free `explain --leaf` handoff. It reads
no dispatcher database or optional index and mutates nothing. The shared
readers no longer follow symlinked worker directories or feedback files, and
`explain --v2` now picks the newest canonical run by its timestamp. The same
dispatch was the first operator dispatch opted into adaptive context. Its
retained records are the operational feedback; no benefit, token saving or
promotion is claimed, and static context remains the default.

## APG166ZB-CONTEXT-PROJECTION1 addendum: stage projection of APGR instructions

This ordinary development slice (not an H campaign) makes the adaptive
ordinary Claude route deliver a deterministic, run-owned, stage-scoped
projection of `claude/CLAUDE.md` in place of the whole file. The tracked file
remains the static source; `claude/instruction-fragments-v1.json` classifies
it into an invariant core and role/capability overlays and is carried into
controller generations. The wrapper verifies and claims the projection once
and changes only the standing-instruction text. `apgr dispatcher observations
explain` reports the mode, selection, omitted fragments, labelled byte
boundary, digests and whether the measurement was observed at the launcher.
Fixture measurements are pilot evidence, not live proof, token counts or
context-window savings; static remains the product default and Claude's
native skill discovery is unchanged.

## APG166ZC-NIX-DISTRIBUTION1 addendum: first-party Nix publication target

The manager added first-party Nix as a v0.13.0 publication surface
([ADR 0076](adr/2026/09/0076-first-party-nix-flake-publication-target.md),
Proposed). This slice adds the root `flake.nix`, the locked `flake.lock`,
`nix/` recipes and checks, the `nix/distribution.json` data authority, a
disposable-profile qualification helper and a public PR CI `nix` job. It
packages the full installed runtime: the portable `apgr` plus the existing
dispatcher, runnable in place from the read-only store with
`installed_immutable_runtime` provenance. It is not an upstream nixpkgs
submission, a binary cache or host activation, and it publishes nothing.

Deferred to V0130-I release preparation:

- the `0.13.0` audited surface in the release tool, whose Nix critical files and
  helpers are listed in the release procedure;
- the attended operator's Nix readback channel;
- a release-matrix row. The REG-P set is fixed at thirteen v0.11-sourced
  cases, and a Nix row needs a non-fabricated source.

`aarch64-linux` has evaluation evidence only. Static context remains the
default, and no H or promotion claim follows.

## APG166ZD-V0130I-RELEASE-PREP1 addendum: release hardening and publication preparation

This V0130-I slice prepares v0.13.0 for attended publication. It does not
publish. The editable `VERSION` authority is now `0.13.0`.

- `apg-public-release` has an explicit `0.13.0` audited surface: the v0.12
  surface plus `rtk-command-proxy`, the Nix critical files and helpers, the
  exported dispatcher commands and the Nix unit tests. Its repeated
  per-version code is now table-driven. Digest tests pin every v0.12.0 and
  earlier surface, candidate filter, deselection set and exclusion outcome.
- The hosted release workflow requires 15 checks and 14 receipts, including
  both native Nix cells. The public PR gate validates `--public-version 0.13.0`.
- Installed-mode recognition is bound to a write-protected `/nix/store` object,
  and the recorded digest is verified when a `dispatch`, `finalize` or
  `ownership` run starts. The tag readback resolves once
  and pins the expected revision
  ([ADR 0076](adr/2026/09/0076-first-party-nix-flake-publication-target.md),
  Accepted with amendment).
- The attended operator gains a readback-only Nix channel that runs last.
  Resume verifies every receipt digest. A missing or failed readback leaves the
  release not fully published.

The superseded "Deferred to V0130-I" items in the APG166ZC addendum are now
addressed, except for a release-matrix row, which still has no legitimate
source. Static context remains the default. No H, benefit or promotion claim
follows. The entry baseline's hosted `static-analysis` findings are an open
publication blocker; see the release-preparation handoff.

## APG166ZE / APG166ZF addendum: interrupted-run recovery and provider-launch evidence

APG166ZE made `--resume` recover a result-less run whose dispatcher vanished.
It first proves the recorded controller ended, then settles workers, and it
routes killed-stage residue to manager-only `interrupted_stage_residue`
challenges. The manager retained one release blocker,
`provider_launch_facts_absent`. ZE could exclude a surviving provider only from
the optional adaptive-context `launch_facts`, and on the ordinary routes these
were absent or null.

APG166ZF closes that blocker. Every dispatcher parent-provider attempt now has
one run-owned `<prefix>.provider-launch.json` record (`apgr-provider-launch-v1`).
The provider execution path owns it, not context or observations. A pre-exec
gate records and fsyncs its own pid, process group and process identity. The
parent makes `authorized` durable before the gate is allowed to exec the
provider. A dispatcher lost before that point leaves the provider unexecuted,
and no parent-death signal is involved. New run states carry a
`provider_launch_contract` marker. Interrupted recovery now does three things:

- it requires the evidence and refuses before any write when evidence is
  missing, malformed, cross-bound or live;
- it accepts a started provider only once its exact recorded incarnation has
  provably ended;
- it sends a legacy source with a stage in flight to the manager lane
  (`provider_launch_contract_absent`).

Optional `launch_facts` may still refuse, but never permit.

Stated residuals:

- a nested session that a wrapper or provider starts itself (Antigravity,
  Claude `run_live`) and that outlives a SIGKILLed wrapper is not proven;
- same-uid forgery of the evidence is outside the contract;
- unbound Request V2 spawns are not gated.

ZE's non-blocking limitations remain: second-generation residue may need the
manual lane, some older challenge reasons keep HEAD-boundary skew, large
residue sets cost per-path receipts, and a later mutating stage that rewrites
inherited candidate paths may refuse. Interruption feature work stops here.
The next work is committed-tree v0.13 release requalification and the
public-staging prerequisites.

## APG166ZG addendum: committed-tree release requalification

APG166ZG requalified the committed v0.13.0 candidate without publication. No
branch, tag, release, registry upload or Nix tag readback happened, and the
default Nix profile was not touched.

The committed tree produced an untagged candidate whose files are a
byte-identical subset of the committed tree. Native `aarch64-darwin` Nix
qualification passed, and so did the local package, Go and dispatcher checks.
`x86_64-linux` and `aarch64-linux` were only evaluated and instantiated.
Locally, `check --untagged` passed every stage before the audited pytest
selection. That stage still needs a host with the provisioned public CI
runtime, so it remains owed, together with its candidate-authority receipt.

The slice made bounded repairs:

- ZE added `interrupted_recovery.py` and the worker `settlement.py` without
  registering them in the test inventory. The `policy` suite failed on that,
  and the public-projection `unit-integration` run would fail the same way, so
  both modules are now registered as dispatcher sources.
- The attended release operator now proves resume above the adapter boundary.
  Three crash windows have legal observed transitions: a published GitHub
  release with a `PREPARED` receipt, PyPI files with a `BLOCKED` receipt, and
  an in-flight npm channel. Each state root is also bound to one release
  identity: version, tag, epoch and commit.
- The operator packet gained its missing checksum sidecar, so its documented
  dry-run path runs.
- The release epoch `1790726400` is described as manager-confirmed.

Hosted `static-analysis` remains an open publication blocker. On the exact
public projection the following findings remain:

- file-length: 23 failures;
- ruff: 544 unresolved findings, one of them a ZF instance of an existing
  `E402` pattern;
- pyflakes: failing;
- scanner-suppressions: 52 additions, one from ZE;
- pip-audit: 13 advisories against `pyjwt` 2.13.0, which the pinned `semgrep`
  1.174.0 requires.

Every file-length and ruff finding except that one ZF instance already existed
before ZE. Clearing them needs a remediation campaign or a recorded policy
decision; neither is part of this slice. No H benefit, context-savings, skill
promotion or native `aarch64-linux` runtime claim follows. Static context
remains the default.
