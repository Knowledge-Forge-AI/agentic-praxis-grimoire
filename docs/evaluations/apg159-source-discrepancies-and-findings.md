# Evaluation: Source Discrepancies (D1–D12) and Manager-Identified Findings

- **Status**: Authoritative Architectural Audit and Discrepancy Disposition
- **Phase**: APG159 (Milestone V0130-A)
- **Governing Document**: Manager Disposition on APGR v0.13.0 (2026-09-20)

---

## 1. Primary Discrepancies Inventory (D1–D12)

The 12 discrepancies identified during the v0.13 research phase are dispositioned below with assigned ownership, evidentiary basis, and deliverable impact:

| ID | Description & Location | Owner | Authoritative Disposition | Blocks Deliverable? |
|---|---|---|---|---|
| **D1** | **ADR 0061 §4 vs Code Enforcement**<br>ADR says unexpected edits captured as typed evidence; code hard-aborts in V1 (`review_binding.py`) and V2 (`v2_turns.py`). | APGR | Implemented via [ADR 0070](../adr/2026/09/0070-configurable-review-stage-mutation-policy.md) (shipped `worktree = "warn"`). Unified drift observer implemented in V0130-B. | No (Scheduled for B) |
| **D2** | **Reference Doctrine Conflict**<br>ADR 0067 §8 declared Agent-Central not decommissioned; operator directed APGR reference dispatcher. | APGR / Agent-Central | Superseded prospectively via [ADR 0069](../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md). Reversible owner-executed transition. | No (Resolved in A) |
| **D3** | **JACA Artifact-Store Root Mismatch**<br>Spec states configurable root; code derives `<home>/.jaca/artifacts`. | JACA | Documented as external limitation in [v0-13 JACA handoff](../architecture/v0-13-jaca-disposition-handoff.md). APGR maintains its own outbox root. | No |
| **D4** | **JACA Ownership Matrix Alignment**<br>JACA §18.13 restricts APGR to imported primitives; APGR proposal suggested broader execution ownership. | Joint Handoff | APGR proposes Go DTO contracts without claiming execution ownership. Handoff remains delivered/unaccepted. | No (Resolved in A) |
| **D5** | **Dynamic Router Fail-Open Defect**<br>`capabilities.py` returns `{}` when `capabilities.toml` absent, allowing unconstrained dynamic routing. | APGR | Adopted fail-closed rule in [ADR 0071](../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md). When dynamic routing is requested, absent capabilities causes hard error. Implemented in V0130-C. | No (Scheduled for C) |
| **D6** | **`JACA_HOME` Path Coupling**<br>Proposal suggested APGR inspect or derive paths from `JACA_HOME`. | JACA / APGR | Rejected in [ADR 0071](../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md). APGR resolves `--apgr-home` > `APGR_HOME` > `~/.apgr` and never reads `JACA_HOME`. | No (Resolved in A) |
| **D7** | **Conflation of HEAD Drift with Candidate Drift**<br>`review_binding.py` records HEAD drift under candidate drift code. | APGR | Resolved in [ADR 0070](../adr/2026/09/0070-configurable-review-stage-mutation-policy.md) by introducing distinct fail-closed code `READ_ONLY_STAGE_MUTATED_HEAD`. Implemented in V0130-B. | No (Scheduled for B) |
| **D8** | **New Policy Surface Nomenclature**<br>Proposal referred to `policy.toml` as an existing file; it is new surface. | APGR | Formally defined as `agent-phase-policy-v1` in [ADR 0070](../adr/2026/09/0070-configurable-review-stage-mutation-policy.md) with generation sharing. | No (Resolved in A) |
| **D9** | **Missing Codex RTK Symlink**<br>`agent_central_install_links.py` links `claude/RTK.md` but not `codex/RTK.md`. | Agent-Central | Read-only diagnosis; APGR provides conditional instruction slices in prompts and read-only doctor without modifying host symlinks. | No |
| **D10** | **Untracked Post-G1 Commits**<br>APG153E–APG158A exist in Git history without roadmap entries or exit records. | APGR Records | Reconciled forward in [v0-12 forward reconciliation](../architecture/v0-12-forward-reconciliation.md). Historical records preserved. | No (Resolved in A) |
| **D11** | **JACA Stale Specification Note**<br>JACA specs state ADR 0014 contract unimplemented despite XORM implementation. | JACA | Informational external observation; zero impact on APGR. | No |
| **D12** | **Undocumented CLI Subcommand Syntax**<br>`apgr skills verify-corpus` implemented in Go requires `--repository <PATH>` (i.e. `apgr skills verify-corpus --repository <PATH>`), but was omitted from reference documentation and CLI help summaries. | APGR Docs | Documented with exact syntax (`apgr skills verify-corpus --repository <PATH>`) in CLI reference during v0.13 documentation updates. Tested and verified working in milestone V0130-A. | No (Scheduled for v0.13) |

---

## 2. Manager-Identified Findings and Resolutions

In addition to D1–D12, the governing manager disposition identified seven critical findings:

### 1. Stale GitHub Release Premise
- **Finding**: Consolidated proposal asserted v0.12.0 was unpublished.
- **Resolution**: Live public API readback verified GitHub Release `392534425` published on 2026-09-20T18:40:56Z along with PyPI, npm, Go proxy, and Homebrew tap. Reconciled in `docs/architecture/v0-12-forward-reconciliation.md`.

### 2. RTK-Off Static Baseline Delta
- **Finding**: Removing RTK text when disabled alters prompt bytes compared to v0.12 static delivery.
- **Resolution**: Established the corrected no-RTK static baseline in [ADR 0072](../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md) and [footprint baseline](apg159-context-footprint-baseline.md).

### 3. Insufficient Go TOML Grammar & Enforcement
- **Finding**: Proposed closed TOML subset omitted booleans and could not enforce lexical constraints after `tomllib`.
- **Resolution**: Custom Go TOML parser deferred (H3 in [ADR 0071](../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md)). Consumers pass typed Go DTOs or validated JSON.

### 4. Mixed-Owner Database State Overreach
- **Finding**: Proposal suggested shared SQLite database with JACA and mixed-owner `ext_*` tables.
- **Resolution**: Deferred in [ADR 0071](../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md). APGR and JACA maintain independent databases and explicit record exchanges.

### 5. Missing Mid-Turn Recovery Semantics
- **Finding**: Mid-turn failure of acquisition channel must not blindly restart or replay producer turns that executed external side effects.
- **Resolution**: Specified in [ADR 0074](../adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md) and Scenario 12: preserve attempt and fall back to local snapshot reads.

### 6. Path-Only Acquisition Risk
- **Finding**: Returning only a file path is insufficient if the actor binding lacks tools to read the filesystem (e.g. read-only reviewer without Bash).
- **Resolution**: Late acquisition via MCP returns the full skill body directly in the tool result payload; CLI channel returns the body to stdout.

### 7. Declared Plans vs Effective Provider Delivery
- **Finding**: Budgeting must distinguish between declared selection plans and bytes actually delivered to provider prompts.
- **Resolution**: Formalized three-tier accounting (planned, materialized, delivered) under `apg.context-footprint/v1`.

---

## 3. Additional Findings from APG159 Work Review (Closeout Corrections)

The APG159 work review (outcome `reviewed_with_findings`, disposition `amend`) surfaced further discrepancies inside the phase's own drafts. Each was corrected in closeout; they are recorded here so the correction trail is visible.

| ID | Finding | Correction | Owner | Remaining gap |
|---|---|---|---|---|
| **W1** | Footprint baseline mixed document classes (root repository `AGENTS.md` for Codex versus projected `claude/CLAUDE.md` for Claude), reported `~` approximations under a "Measured" heading, and asserted RTK slice sizes (1,420 / 850 / 1,210 bytes) that no source file supports. | [Footprint baseline §3](apg159-context-footprint-baseline.md) rewritten: only APGR provider instruction files (`codex/AGENTS.md` 7,939 B, `claude/CLAUDE.md` 11,071 B, `antigravity/GEMINI.md` 4,238 B) with measured RTK text (240 / 35 / 1,041 B), per-figure command provenance, `unavailable` for delivered bytes and MCP overhead, and no "authoritative control baseline" claim. | APGR (V0130-D materializes slices) | Actual provider-delivered bytes unobserved; Claude has no separable RTK slice today. |
| **W2** | Dispatcher-differences report said "17 modules" while listing 16, claimed APGR "encompasses 100%" of Agent-Central logic, and called the V0130-I gate "fully verified" from a filename inventory. | [Report](apg159-agent-central-dispatcher-differences.md) downgraded to a filename- and byte-level inventory (16 APGR-only, 44 identical, 18 differing); gate marked unverified and owned by V0130-I; both available Agent-Central checkouts confirmed at the parity baseline `56e9bb0` with zero post-baseline dispatcher commits. | APGR (V0130-I) / Agent-Central owner | Content review of 18 differing modules pending; a newer Agent-Central revision, if any, is not on this host. |
| **W3** | Required read-only sampling of retained REVIEWIMMUT1 invalidation evidence was not reported. | [Seam inventory §4.3](../specs/review-mutation-seam-inventory.md) records the bounded sample (20 files, 1 distinct invalidation event) and the negative result: the invalidated review's response body was not retained, so the semantic-drift question is unanswerable from existing evidence. | APGR (V0130-B) | V0130-B must retain reviewer responses for observed-drift stages. |
| **W4** | Seam S5 mischaracterized `v2_repair.py:120-145` as a drift validator. | Seam inventory S5 corrected: it is the auxiliary repair working-directory guard (`RESULT_REPAIR_WORKDIR_UNSAFE`), adjacent to but not part of the drift observer set. | APGR | None. |
| **W5** | The prior stage's narrative (not the repository documents) substituted an invented D1–D12 list, pre-assigned phase IDs APG160–APG167, reassigned milestone contents, asserted a 4-characters-per-token estimate, claimed a "standard Go TOML parser", and reported all v0.12 channels "confirmed" without method. | The repository documents were already correct on each point (this file §1; `docs/v0-13-roadmap.md`; `apg159-context-footprint-baseline.md` §1; ADR 0071 §3; `docs/architecture/v0-12-forward-reconciliation.md` §5). The closeout narrative restates them from the documents. | APGR | Phase IDs for B–I remain unallocated until each phase is nominated and checked. |

---

## 4. APG159 Delta Accounting: Source Reality vs Historical Narrative

In the historical APG159 closeout narrative, the author reported a 31-path delta. Authoritative Git inspection of the actual finalized APG159 commit (Exit 00205; exact object retained in dispatcher reports and excluded evidence) establishes a **48-path delta** comprising:
- **39 file additions**: Including ADRs 0069 through 0074, 15 context-eval scenario fixtures, metric/oracle specifications, evaluation reports, and specifications.
- **9 file modifications**: Including `docs/status/README.md`, `docs/v0-13-roadmap.md`, `testing/fixtures/context-eval/README.md`, and supporting documentation.

Both figures are formally recorded here for evidentiary transparency:
- **Historical Narrative Count**: 31 paths reported in the initial closeout summary narrative.
- **Source Git Reality Count**: 48 paths (39 additions, 9 modifications; +2,159 lines, -30 lines) established from the finalized APG159 commit's native Git objects.
