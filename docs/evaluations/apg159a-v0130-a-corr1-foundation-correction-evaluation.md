# APG159A — v0.13.0 Foundation Correction and Qualification Evaluation Record

- **Phase ID**: `APG159A`
- **Roadmap Milestone**: `V0130-A-CORR1` (bounded correction and qualification of Milestone V0130-A)
- **Governing Authority**: APG159A corrective assignment and governing manager disposition (2026-09-20)
- **Phase Type**: `architecture_docs`
- **Gate Outcome**: `V0130_A_CORR1_FOUNDATION_QUALIFIED`
- **Authority Boundary**: Architecture documentation, non-executable fixture data, and publication-excluded qualification evidence only. No runtime code, Python/Go packages, lockfiles, CLI entrypoints, skill bodies, or Git mutation by agents.

---

## 1. Executive Summary and Corrective Objectives

APG159A is the bounded corrective phase following exact-source review of APG159. APG159 established the v0.13 architectural foundation (ADRs 0069–0074, 15 context evaluation scenarios, specifications, and reconciliation records). The exact-source review identified six finding clusters (F1–F6) requiring evidentiary correction, formula freezing, schema alignment, and reconciliation. A closeout-stage independent review of the APG159A candidate then surfaced further defects inside the correction itself, which this record's final revision resolves.

All six finding clusters are addressed under APG159A:
- **F1 (Skill Costs & Maturity Evidence)**: All ten candidate skills remeasured from canonical source with declared boundaries and digests; APG139 maturity evidence reconciled across all seven categories; debt status corrected.
- **F2 (15-Scenario Corpus & Oracle Freeze)**: Correction revision recorded; formulas, cohorts, p95 method, missing-data rule, and value-source vocabulary frozen; Scenario 01 budget infeasibility resolved; synthetic inputs labelled; Scenario 12 recovery and producer-side-effect variant specified.
- **F3 (Review Mutation Policy)**: Worktree tri-state with block-only index/HEAD; freshness restorable only by an eligible independent review of the exact final candidate.
- **F4 (Home Layout & Configuration)**: Existing `outbox_root` and path contract preserved; unapproved `[provenance]` table removed; ownership boundaries documented.
- **F5 (Provider Qualification & MCP Persistence)**: Six explicit qualification states; MCP lifecycle pinned to the 2025-11-25 revision; run-owned JSONL acquisition events imported by the Python persistence owner.
- **F6 (Reconciliation & Delta Accounting)**: Post-G1 identities rebuilt from native Git objects; registry statuses rebuilt from retained raw readbacks with per-channel observation dates; public documents no longer depend on excluded paths; the 48-path APG159 delta recorded alongside the historical 31-path narrative.

---

## 2. Detailed Disposition of Findings F1–F6

### F1 — Skill Costs & Maturity Evidence

1. **Exact canonical measurements.** Every figure in [the promotion cost ranking](apg159-skill-promotion-cost-ranking.md) was remeasured from the canonical `skills/**/SKILL.md` files: UTF-8 bytes and Unicode characters, POSIX `\n` newlines, frontmatter defined as the opening `---\n` through the closing `\n---\n` inclusive, body defined as everything after that delimiter. Frontmatter bytes plus body bytes equal whole-file bytes for every skill, in bytes and in characters. The ranking document carries a reproducible command covering all ten paths; SHA-256 digests and the command output are retained in publication-excluded evidence.
   - APG159's substitution error is corrected: 3,146 B belongs to `composing-bounded-worker-assignments`; `composing-approved-roadmap-assignments` is 9,182 B whole (8,877 B body, 238 B description).
   - Remeasured whole / body / description bytes for the ten candidates:
     - `go-language-profile`: 16,733 / 16,452 / 233
     - `go-test-profile`: 17,821 / 17,487 / 290
     - `pytest-test-profile`: 17,844 / 17,592 / 204
     - `markdown-language-profile`: 11,566 / 11,339 / 173
     - `sqlite-database-profile`: 17,265 / 16,929 / 284
     - `postgresql-database-profile`: 17,232 / 16,931 / 245
     - `typescript-language-profile`: 11,163 / 10,856 / 251
     - `composing-approved-roadmap-assignments`: 9,182 / 8,877 / 238
     - `converting-bash-scripts-to-python`: 16,669 / 16,452 / 155
     - `css-language-profile`: 13,187 / 12,818 / 320
   - The whole-file values match the generated `skill-metadata.json` source-blob bytes for these paths; the generated metadata was cross-checked against source rather than treated as authoritative.
2. **APG139 maturity reconciliation.** For every candidate: `repeated_positive_use: LIMITED`, `representative_non_triggers: LIMITED`, `current_validation: LIMITED`, `independent_review: PENDING`, `rollback` and `provenance` SUPPORTED. Technology presence (Go code, pytest tests, SQLite storage) is not evidence of effective guidance use. APG159's "high use" and "clean validation" claims are withdrawn.
3. **Debt status.** Nine candidates carry zero open debts. `css-language-profile` carries five active debts (`CSS-QD-001` to `CSS-QD-004` blocking stable promotion; `CSS-QD-005` non-blocking). APG159's `JS-QD-005` attribution is corrected.
4. **Tranche allocation.** Five primary candidates (`go-language-profile`, `go-test-profile`, `pytest-test-profile`, `markdown-language-profile`, `sqlite-database-profile`) and three bounded reserves (`postgresql-database-profile`, `typescript-language-profile`, `composing-approved-roadmap-assignments`) are planning priorities only. `converting-bash-scripts-to-python` is deferred and `css-language-profile` is excluded by blocking debt. No skill is promoted and no criterion is lowered.

### F2 — 15-Scenario Corpus & Oracle Freeze

1. **Correction revision.** Every fixture carries `correction_revision: APG159A-CORR1`, superseding APG159's numerical freeze, which remains in Git history at Exit 00205. This is a pre-implementation correction, not tuning against a held-out set.
2. **Schema and links.** The unresolvable `$schema` reference was removed from the metrics file, which is now a plain instance document; the README's relative ADR link was repaired; the README no longer depends on an excluded evidence path.
3. **Frozen formulas and cohorts.** Initial savings `1 - adaptive_initial / static_initial` with a strictly positive measured denominator, target median ≥ 0.20 over `savings_eligible_cohort` {06, 08, 09, 10, 11, 15}; cumulative growth `adaptive_cumulative / static_cumulative - 1`, target nearest-rank p95 ≤ 0.10 with index ⌈0.95·n⌉ − 1; `savings_eligible_calibration_subset` {01, 02, 04} is development-only; `correctness_failure_only_cohort` {03, 07, 12, 13, 14}; `fallback_cohort` {05, 13}. Missing required measurements fail the gate. Provider-native token overhead is `unavailable`, never zero, and no characters-per-token heuristic is permitted. Enforcement is `planned`.
4. **Value sources.** Every numeric input carries a source tag from the frozen vocabulary `measured | synthetic | estimate | declared | unavailable`. Provider instruction bytes are measured (`codex/AGENTS.md` 7,939 B; `claude/CLAUDE.md` 11,071 B; `antigravity/GEMINI.md` 4,238 B). The uniform `mandatory_doctrine_bytes` value is an explicit planning estimate that V0130-F must replace with a measurement before it feeds any gate.
5. **Scenario 01 feasibility.** The three canonical skills total 39,775 whole-file bytes (38,929 body bytes), so APG159's 25,000 B budget could not hold them. The budget scope is APGR-controlled initial bytes; a 55,000 B budget with a 42,000 B skill-body allocation holds all three complete bodies. The 25,000 B case is retained as a deferred-acquisition alternative. Dependency facts (`go.mod` requiring `github.com/google/go-cmp v0.7.0`) justify the deferred go-cmp skill.
6. **Synthetic inputs (Scenarios 08, 09).** The `project:` source is an embedded synthetic miniature body (690 B whole, 525 B body, digest recorded) explicitly labelled `source_kind: synthetic`; the fixture path does not exist in the repository. These scenarios are flagged `synthetic_inputs: true`, and the default-flip gate must also pass with them excluded. Synthetic bytes never claim canonical corpus savings.
7. **Scenario 04.** The `rtk-command-proxy` skill does not yet exist in the canonical corpus; the fixture marks it planned for V0130-D and its slice bytes as an estimate.
8. **Scenario 12.** A restricted `Work Review` actor (`view_file` only, no Bash) recovers a skill withheld before the failure by native read of a run-owned snapshot that must exist and be readable before launch. A producer-side-effect variant proves no blind replay after mutations. Q1 in the provider plan invokes MCP `skill_acquire` rather than CLI.
9. **Measured canonical bytes** in fixtures were remeasured from source in this closeout: `implementing-with-test-discipline` body is 4,990 B (not 4,960) and `go-cmp-test-profile` is 15,677 B whole (not 14,200). Every canonical skill entry now records `body_sha256` for the exact-body oracle.

### F3 — Review-Stage Mutation Policy, Ownership & Malformed Results

1. Worktree policy is configurable as `block`, `warn`, or `allow` (shipped default `warn`); index and HEAD remain block-only across all v0.13 modes with distinct violation codes.
2. A warned or allowed mutation never certifies changed bytes; the original review subject and binding remain immutable; warning observations and raw reviewer output are preserved, including malformed results.
3. `final_candidate_reviewed` is restored only by a later eligible independent review bound to `candidate_tree == terminal_tree`, with eligibility derived from receipts (review role, exact tree, zero drift, verified artifact), never from agent assertion. Earlier warnings do not permanently poison it; without an eligible review it remains false.
4. Closer ownership disposition of surviving reviewer-origin paths is not review and mints no freshness. No new mandatory stage or review loop is introduced.

### F4 — Home Layout, Configuration & Hosting Seams

1. The existing top-level `outbox_root` key and `[dispatcher]` table are preserved; additive v0.13 keys (`[integrations]`, `[skills]`) are documented as approved additions without migrating callers.
2. The unapproved `[provenance]` operator table is removed; provenance is generated evidence.
3. The maintained path contract is preserved: user-home syntax is expanded, absolute results are required, and relative roots are rejected. No cwd-relative `APGR_HOME`.
4. `<APGR_HOME>/state/` is Python-dispatcher owned; sources, projections, transient scratch, generations, and the `user:` skill namespace are distinguished. APGR never reads `JACA_HOME`; no Go TOML parser or shared APGR/JACA database is reintroduced.

### F5 — Provider Qualification & Implementable MCP Persistence

1. Provider capability claims use six explicit states (`inspected`, `documented`, `planned`, `experimental`, `qualified`, `unavailable`) with source evidence. Isolated Claude settings and `--add-dir` are candidate mechanisms, not proven selective discovery. Bash is not granted to review roles to satisfy a CLI test.
2. MCP is pinned to the 2025-11-25 stdio lifecycle: initialize → negotiated version/capabilities → initialized notification → permitted operation → shutdown (stdin close, wait, SIGTERM, SIGKILL); bounded message size, timeouts, cancellation, stderr-only logging, stdout protocol purity. Three tools and two resource templates; no network, subprocesses, credentials, or operator MCP configuration writes.
3. Persistence handoff: the Go adapter appends run-owned JSONL acquisition events with monotonic `event_id` and the materialized content; the existing Python persistence owner validates and imports them at a defined lifecycle seam with `pending`/`imported`/`failed` states, idempotent retry, crash recovery, and raw-artifact retention. `delivered` is recorded only when the actor-accessible channel conveyed the body.
4. Adaptive readiness requires a pre-materialized, role-readable recovery path per provider/role; otherwise static before launch. No producer auto-replay after possible side effects.

### F6 — Forward Reconciliation Evidence and Delta Accounting

1. **Git identities.** All seven post-G1 phase commits (APG153E, APG153G, APG153J, APG155B, APG156A, APG156C, APG158A) were re-read as full native Git objects from the read-only primary checkout and this clone; APG159's three wrong values are superseded. Exact objects live only in the publication-excluded reconciliation evidence record and dispatcher reports, per the repository's identity rules; this public record uses phase and exit identities. The Go module path retains the `Knowledge-Forge-AI` case from `go.mod`.
2. **Registry readbacks (observed 2026-09-20, closeout).** PyPI, npm (main package plus three platform packages), the Go module proxy, and the Homebrew tap formula were read back live; raw bodies and SHA-256 digests are retained in the phase outbox. The Go proxy `.info` origin confirms the tag commit. The GitHub Releases API was unreachable from the sandboxed phase; the release ID and tag were reconfirmed from the release page, while the publish time and draft/prerelease flags rest on the manager's dated API readback. The release tree hash and hosted run ID are `unverified`. Homebrew is a formula readback only; install and audit were not run.
3. **Public/private boundary.** The forward reconciliation record, the ranking document, and the fixture README no longer reference excluded `private/` paths or host filesystem paths. Exact evidence stays in the excluded record and the outbox.
4. **G2 separation.** Public channel visibility, private-source alignment, and G2 terminal closure are recorded as separate facts. The v0.12.0 tag is absent from the primary checkout; source/terminal reconciliation remains explicitly unresolved.
5. **D12 and delta.** D12 documents the verified command syntax `apgr skills verify-corpus --repository <PATH>`. The source-established 48-path APG159 delta (39 additions, 9 modifications) is recorded alongside the preserved 31-path closeout narrative.

---

## 3. Delta and Path Accounting

- **APG159 committed delta** (Exit 00205, parent APG158A): 48 paths, 39 additions and 9 modifications. Exact commit identities are retained in dispatcher Git reports and excluded evidence, not here.
- **APG159A worktree delta** (measured at closeout with `git status --porcelain` before dispatcher staging): 36 paths, 31 modifications and 5 additions:
  - Modified (31): ADRs 0070, 0071, 0074 and the ADR index; `docs/architecture/v0-12-forward-reconciliation.md`; `docs/evaluations/apg159-skill-promotion-cost-ranking.md`; `docs/evaluations/apg159-source-discrepancies-and-findings.md`; `docs/evaluations/apg159-v0130-a-foundation-evaluation.md` (pointer wording only); `docs/specs/apgr-home-layout-v1.md`, `provider-role-qualification-plan.md`, `review-mutation-seam-inventory.md`; `docs/status/README.md`; `docs/v0-13-roadmap.md`; the excluded v0.12 reconciliation evidence record; `testing/fixtures/context-eval/README.md`, `context-eval-metrics-and-oracles.json`, and all 15 scenario fixtures.
  - Added (5): this record; Exit 00206; the excluded skill-cost measurement record, the excluded all-15 consistency record, and the prepared commit message.
  - The dispatcher's staged count is authoritative if it differs.
- **Boundary compliance**: no `.py`, `.go`, `.sh`, or `.mjs` files; no skill bodies, metadata generators, maturity ledger, debt records, lockfiles, package version, release tooling, or dispatcher implementation. Temporary checking scripts and receipts live in the phase outbox.

---

## 4. Verification and Quality Evidence

Scoped, claim-appropriate checks run against the corrected worktree at closeout:
1. `bin/apg-check-record-identity --format json` and `--expect-allocated APG159A`: record identity consistent; Exit 00206 allocated from the actual namespace.
2. `bin/apg-check-skill-library`: PASS (45 canonical skills, 45 catalog rows, 45 projections).
3. `./bin/apgr skills verify-corpus --repository <workspace>`: PASS.
4. `rtk pytest src/test/dispatcher/test_agent_phase_config_routing.py`: 14 passed (the earlier "15 passed" receipt was inaccurate; the file defines 14 tests).
5. `go test ./skills/... ./internal/...`: PASS.
6. JSON parse of all 16 fixture files and the three excluded evidence records: PASS.
7. Source measurement reproduction over the ten ranked skills: all recorded bytes, characters, and digests match; receipt embedded in the measurement record.
8. All-15 fixture consistency: every cohort id is in the frozen vocabulary and listed in the metrics file; every canonical path exists or is explicitly synthetic/planned; every measured byte count and body digest matches source.
9. Public/private boundary scan over `docs/**` and `testing/**` (excluding historical status records): no `private/` dependencies or host paths in APG159/APG159A-owned publishable documents.
10. `bin/apg-check-phase-commit-message --phase APG159A` on the prepared message: PASS.
11. `bin/apg-check-roadmap-closure`: PASS.

Not run: the full pytest and Go matrices for unedited subsystems, live provider transport, and any registry publication action. Inspection and synthetic checks do not establish live provider support.

---

## 5. Program Gate Evaluation

### Gate `V0130_A_CORR1_FOUNDATION_QUALIFIED`
- **Status**: SATISFIED for this bounded correction. All F1–F6 dispositions are backed by reproducible evidence or explicitly recorded limitations. Terminal milestone acceptance remains manager-owned.

### Gate `V0120-G2` (Terminal Reconciliation Prerequisite)
- **Status**: NOT REQUIRED for APG159A (documentation only); UNRESOLVED and BLOCKING for V0130-B onward.
- **Basis**: Public registry visibility is observed and retained; the primary development checkout has no v0.12.0 tag and no G2 exit record; source/terminal alignment is not established. Neither the stale `NOT STARTED` roadmap heading nor a registry version alone settles the gate. Owner: the release authority, before V0130-B.

---

## 6. Material Limitations

1. **GitHub Releases API unobserved by this phase.** Publish time and draft/prerelease flags rest on the manager's dated readback; only the release ID and tag were reconfirmed. Owner: next release-authority verification.
2. **Unverified release identities.** The release tree hash and hosted run ID have no retained raw evidence and are marked `unverified`.
3. **Homebrew** is a formula readback only; install/audit belongs to V0130-I distribution checks.
4. **Mandatory doctrine bytes** are a planning estimate in every scenario until V0130-F defines the measurable slice. The RTK instruction slice and the `rtk-command-proxy` skill do not yet exist in the corpus (V0130-D).
5. **Provider delivery unobserved.** All measurements are APGR-side bytes; delivered provider bytes, tool-schema overhead, and tokens remain `unavailable`.
6. **Agent-Central content review pending** for the differing shared dispatcher modules; owned by V0130-I.
