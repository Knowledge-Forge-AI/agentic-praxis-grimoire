# APG144 — Public Staging Candidate and Operator Handoff

Phase ID: `APG144`

## Status and scope

Disposition: **amend**. APG144 allocates exit 00189 without substitution.
Historical Outcomes:
- 2026-09-13 STAGING-PREP1/2: Initial handoff claim `V0110_PUBLIC_STAGING_HANDOFF_QUALIFIED` unaccepted for public execution by subsequent manager disposition due to unverified staging push and fixture-ref containment boundaries.
- 2026-09-13 STAGING-PREP3: Candidate validation under isolated test environment exited 1 during configured-tests (117 failed, 7 errors across browser/runtime suites and scanner suppressions), resulting in closer status `V0110_STAGING_RECONCILIATION_PREPARATION_PARTIAL`.
- 2026-09-13 STAGING-PREP4: Corrective continuation repairing candidate test execution (keyword argument compatibility for `scan_suppressions` test doubles, pinned runtime provisioning via `bootstrap_runtime.py`, bounded output log extension), aligning status documentation, and establishing factual candidate acceptance boundaries. Candidate qualification and per-category verification receipts are recorded in private and external evidence.
Accounting remains 55 inherited / 55 terminal / zero OPEN / zero invalid (45 canonical skills: 14 stable / 31 provisional; six active CSS/JS debts; description ceiling 11,507 bytes).

APG144 continues the approved v0.11 program as the bounded V0110-G preparation slice
and its corrective follow-up under STAGING-PREP4. The objective is to prepare a disclosure-safe, locally verified
untagged public candidate, isolate the test transport boundary, and author tested, attended
staging, recovery, and PR operations. **This phase performs zero public mutation.**

The entry basis accepts the APG143 manually verified private publication checkpoint
and its reported local readiness results under Manager Decisions A–D. The original
READINESS4 dispatcher attempt remains historically blocked due to a terminal commit-message/protocol
validation failure followed by a recovery digest-binding defect and is preserved without alteration.

## Changes and evidence

1. **State Reconciliation & Documentation Alignment**:
   - `AGENTS.md`, `docs/v0-11-roadmap.md`, and `docs/public-pr-ci.md` are reconciled
     with the completed READINESS4 local readiness qualification and the manual
     private publication observation, while marking READINESS1–3 as historical
     blocked attempts.
   - ADR 0057 is marked `Accepted implementation` with a dated APG144 disposition,
     distinguishing locally implemented and tested tooling contracts from unexercised
     live-host operations.
   - `release/v0.11.0-notes.md` is updated to unreleased staging-candidate status.

2. **Pre-Disclosure Gap Closure**:
   - The public-facing APG143 evaluation and exit 00188 are sanitized by replacing
     private receipt paths and unpublished commit/tree hashes with semantic labels,
     preserving exact metrics, test counts, and coverage.
   - A focused unit regression is added to `apg_public_release.unit.test.py`
     verifying that `validate_markdown_links` rejects public Markdown links pointing
     into `private/` across multiple directory depths. Inline mentions remain
     human/review-enforced.

3. **Untagged Public Candidate Construction**:
   - Built and checked using `bin/apg-public-release` in untagged candidate mode
     against the accepted public base commit `250ce73a3dac71a89b8efeee9b8fe6cb0420bf18`.
   - Single-parent lineage from accepted base, subject `Release v0.11.0`, no release
     tag `v0.11.0`, zero private development history, and exact projection equality.
   - Candidate build and qualification receipts are retained outside tracked source
     under `private/` and external scratch.

4. **Attended Stage-Only Operator & Boundary Containment**:
   - Implemented in publication-excluded release operations staging tooling (`stage_operator.py`).
   - Supports read-only preview/readback mode, non-circular post-checkpoint source readback mode
     (reusing maintained projection filtering), and attended `--execute` mode with strict candidate/source
     projection binding, readback tree assertions, REST pull request validation, and external partial receipts.
   - Fully isolated test environment (scrubbed tokens, test-owned HOME, `GIT_ALLOW_PROTOCOL=file`, `GIT_TERMINAL_PROMPT=0`, fail-closed runner) covering hermetic test scenarios with disposable Git repositories, local bare remotes, and controlled API mocks.

5. **Attended Fixture Ref Recovery Tool**:
   - Implemented in publication-excluded release operations recovery tooling (`recover_fixture_ref.py`).
   - Dedicated, attended single-user tool to inspect and safely retire ONLY the known public test-fixture
     staging ref (`e537cb22b52a1faff745647b85d28202a685b060`) upon separate operator authorization.
   - Enforces exact repository ID (`1306002537`), unchanged accepted base main (`250ce73a`), zero open PRs,
     zero v0.11 tags, exact fixture tip/tree/parent match, pre-deletion local backup verification, and guarded `--force-with-lease` deletion executed from the local backup bare repository with `-c push.followTags=false` and `--no-recurse-submodules`.
   - Covers hermetic test scenarios with disposable bare remotes and controlled API mocks.

6. **Hosted Gate & Settings Handoff**:
   - The candidate preserves the four-family hosted CI gate in `.github/workflows/public-pr.yml`.
   - Publication-excluded release settings handoff documents observed protection
     state (live readback on 2026-09-13: HTTP 404 branch not protected, rulesets empty),
     required rulesets, single-maintainer approval path, the known merge-ref
     identity pre-first-run limitation for `matrix_receipts.py verify`, and the two-step
     attended recovery-then-staging procedure.

## External pending state

External release states remain explicitly pending and outside this dispatch's authority:
- `public_staging`: `not_started` (incident observed: remote staging branch exists with test-fixture commits and unverified process attribution; attended guarded cleanup tool prepared and verified; public execution pending separate operator authorization)
- `public_pr_ci`: `not_run`
- `public_release`: `not_started`
- `branch_protection`: `unconfigured`

## Rollback and boundary

Rollback restores the APG143 checkpoint state. The dispatcher alone owns private
Git commit, push, and publication policy. Stop after APG144; public fixture ref retirement,
public staging push, PR review, hosted CI execution, squash merge, tagging, and package
publication require separate future authorization.
