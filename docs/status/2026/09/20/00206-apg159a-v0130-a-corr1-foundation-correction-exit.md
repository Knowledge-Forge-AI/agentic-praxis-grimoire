# APG159A — v0.13.0 Foundation Correction and Qualification Exit

Phase ID: `APG159A`
Exit ID: `Exit 00206`
Roadmap Milestone: `V0130-A-CORR1`
Governing Decisions: [ADR 0069](../../../../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md), [ADR 0070](../../../../adr/2026/09/0070-configurable-review-stage-mutation-policy.md), [ADR 0071](../../../../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md), [ADR 0072](../../../../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md), [ADR 0073](../../../../adr/2026/09/0073-unified-skill-catalog-and-deterministic-resolution.md), [ADR 0074](../../../../adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md)
Exit Target: `V0130_A_CORR1_FOUNDATION_QUALIFIED`
Evaluation Record: [APG159A foundation correction evaluation](../../../../evaluations/apg159a-v0130-a-corr1-foundation-correction-evaluation.md)

---

## 1. Status and Disposition

- **Disposition**: **accept** (bounded correction complete; milestone acceptance remains manager-owned)
- **Milestone Outcome**: `V0130_A_CORR1_FOUNDATION_QUALIFIED`
- **Execution Boundary**: Architecture documentation, specifications, non-executable evaluation fixtures, and publication-excluded evidence in the isolated clone on branch `v0.13.0/apg159-foundation`. No runtime code, packages, lockfiles, CLI entrypoints, skill bodies, or agent-performed Git mutation. APG159's finalized commit, review, and repair history are preserved unchanged.

---

## 2. Corrective Scope Delivery (Findings F1–F6)

### 2.1 F1: Skill Costs & Maturity Evidence
- All ten candidate skills remeasured from canonical `skills/**/SKILL.md` source: UTF-8 bytes and Unicode characters, POSIX `\n`, frontmatter `---\n` through `\n---\n` inclusive, body strictly after; frontmatter + body = whole for every skill. Reproducible command over all ten paths in the ranking document; digests and command output in excluded evidence.
- Substitution error corrected: `composing-approved-roadmap-assignments` is 9,182 B whole (8,877 B body, 238 B description); 3,146 B belongs to `composing-bounded-worker-assignments`.
- APG139 maturity reconciled across all seven categories (`repeated_positive_use`, `representative_non_triggers`, `current_validation`: LIMITED; `independent_review`: PENDING; `rollback`, `provenance`: SUPPORTED). "High use" and "clean validation" claims withdrawn.
- Debt inventory corrected: nine candidates carry zero debts; `css-language-profile` carries five active debts (`CSS-QD-001`–`CSS-QD-004` blocking; `CSS-QD-005` non-blocking), not `JS-QD-005`.
- Five primary candidates and three bounded reserves named as planning priorities; no promotion, no lowered criteria.

### 2.2 F2: 15-Scenario Evaluation Corpus & Oracle Freeze
- Correction revision `APG159A-CORR1` recorded in every fixture, superseding APG159's numerical freeze retained in history.
- Metrics file is a plain instance document (invalid `$schema` removed); README ADR link repaired; README no longer depends on an excluded evidence path.
- Frozen: initial savings `1 − adaptive_initial/static_initial` (median ≥ 0.20 over `savings_eligible_cohort` {06, 08, 09, 10, 11, 15}); cumulative growth `adaptive_cumulative/static_cumulative − 1` (nearest-rank p95 ≤ 0.10, index ⌈0.95·n⌉ − 1); `savings_eligible_calibration_subset` {01, 02, 04} development-only; `correctness_failure_only_cohort` {03, 07, 12, 13, 14}; `fallback_cohort` {05, 13}; missing data fails; tokens `unavailable`; enforcement `planned`.
- Value-source vocabulary `measured | synthetic | estimate | declared | unavailable` applied to every numeric fixture input; `mandatory_doctrine_bytes` is an explicit estimate pending V0130-F.
- Scenario 01: three canonical skills total 39,775 B whole (38,929 B body); feasible 55,000 B controlled budget with 42,000 B body allocation; 25,000 B retained as a deferred-acquisition alternative; `go.mod` dependency facts added.
- Scenarios 08/09: synthetic `project:` body embedded and labelled `synthetic` (690 B whole, 525 B body); `synthetic_inputs: true`; gate must also pass with synthetic scenarios excluded.
- Scenario 04: `rtk-command-proxy` marked planned for V0130-D (not in the canonical corpus).
- Scenario 12: restricted reviewer (`view_file` only, no Bash) recovers from a pre-materialized run-owned snapshot; producer-side-effect variant proves no blind replay.
- Canonical byte corrections at closeout: `implementing-with-test-discipline` body 4,990 B; `go-cmp-test-profile` 15,677 B whole; `body_sha256` recorded for every canonical entry.

### 2.3 F3: Review-Stage Mutation Policy, Ownership & Malformed Results
- Worktree tri-state (`block`, `warn`, `allow`; shipped `warn`); index and HEAD block-only in all v0.13 modes.
- Warned/allowed mutation never certifies changed bytes; original subject/binding immutable; raw reviewer output and warning observations preserved, including malformed results.
- `final_candidate_reviewed` restored only by a later eligible independent review bound to the exact final candidate tree, with receipt-derived eligibility; otherwise false.
- Closer disposition is ownership handling, not review; no new mandatory stage.

### 2.4 F4: Home Layout, Configuration & Hosting Seams
- Existing top-level `outbox_root` preserved; v0.12 keys distinguished from additive v0.13 keys (`[integrations]`, `[skills]`); `[provenance]` table removed.
- Path contract preserved (user-home expansion, absolute required, relative rejected); no cwd-relative `APGR_HOME`; no `JACA_HOME`.
- `<APGR_HOME>/state/` Python-dispatcher owned; sources, projections, scratch, generations, and `user:` namespace distinguished; no Go TOML parser; no shared SQLite database.

### 2.5 F5: Provider Qualification & Implementable MCP Persistence
- Six qualification states replace "Supported"; isolated Claude settings and `--add-dir` are candidate mechanisms; Q1 invokes MCP `skill_acquire`; Bash withheld from review roles.
- MCP pinned to the 2025-11-25 stdio lifecycle with bounded messages, timeouts/cancellation, stderr-only logging, and stdin-close/SIGTERM/SIGKILL shutdown.
- Run-owned append-only JSONL acquisition events (monotonic `event_id`) imported by the Python persistence owner at a defined seam; `pending`/`imported`/`failed`; idempotent retry; crash recovery; raw retention; `delivered` only on actor-accessible conveyance.

### 2.6 F6: Forward Reconciliation Evidence and Delta Accounting
- Seven post-G1 phase commits re-read as full native Git objects; APG159's three wrong values superseded. Exact objects retained only in excluded evidence and dispatcher reports.
- Go module path case preserved from `go.mod`.
- Registry statuses rebuilt from live readbacks observed 2026-09-20 with raw bodies and digests retained in the phase outbox: PyPI (four artifacts), npm (main plus three platform packages), Go proxy (origin confirms tag commit), Homebrew formula (install/audit not run). GitHub Releases API unreachable from the sandboxed phase: release ID and tag reconfirmed from the release page; publish time and flags rest on the manager's dated readback; tree hash and hosted run ID `unverified`.
- Publishable documents no longer reference excluded paths or host filesystem paths.
- D12 command syntax verified; 48-path APG159 delta recorded alongside the preserved 31-path narrative.

---

## 3. Verification and Checks

Scoped checks run at closeout on the corrected worktree:
1. `bin/apg-check-record-identity --format json` and `--expect-allocated APG159A`: PASS; Exit 00206 allocated from the actual record namespace.
2. `bin/apg-check-skill-library`: PASS (45 canonical skills, 45 catalog rows, 45 projections).
3. `./bin/apgr skills verify-corpus --repository <workspace>`: PASS.
4. `rtk pytest src/test/dispatcher/test_agent_phase_config_routing.py`: 14 passed (an earlier receipt stating 15 was inaccurate).
5. `go test ./skills/... ./internal/...`: PASS.
6. JSON parse of all fixture and evidence files; source-measurement reproduction over ten skills; all-15 fixture consistency (cohort ids, path existence, bytes, digests): PASS.
7. Public/private boundary scan over `docs/**` and `testing/**` publishable documents owned by APG159/APG159A: PASS.
8. `bin/apg-check-phase-commit-message --phase APG159A`: PASS. `bin/apg-check-roadmap-closure`: PASS.

---

## 4. Not Run and Hard Stop Boundary

- Full pytest and Go matrices for unedited subsystems: not run (documentation-only phase).
- Live provider transport, browser/provider matrix, and registry publication: not run; inspection does not establish live support.
- GitHub Releases API readback: attempted, blocked by the sandbox network policy; recorded as a limitation, not a failure.
- Git staging, commit, push, tag, or branch operations by agents: none (dispatcher-owned commit-local finalization).

---

## 5. Gate Status and Next Authorized Step

- `V0130_A_CORR1_FOUNDATION_QUALIFIED`: satisfied for this bounded correction; terminal milestone acceptance is manager-owned after exact-source review.
- `V0120-G2`: not required for APG159A; unresolved and blocking for V0130-B and later code milestones. Public registry visibility is observed; source/terminal alignment is not established.
- No successor phase is allocated by this exit. Implementation of V0130-B is not authorized by this record.
