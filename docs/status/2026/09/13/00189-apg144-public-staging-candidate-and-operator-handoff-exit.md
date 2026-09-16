# APG144 — Public Staging Candidate and Operator Handoff Exit

Phase ID: `APG144`

## Status

Disposition: **amend**. Exit 00189 is allocated to APG144 without renumbering or substitution.
Historical Outcomes:
- 2026-09-13 STAGING-PREP1/2: Initial handoff claim `V0110_PUBLIC_STAGING_HANDOFF_QUALIFIED` unaccepted for public execution by manager disposition due to unverified staging push and fixture-ref containment boundaries.
- 2026-09-13 STAGING-PREP3: Candidate check under isolated test environment exited 1 during configured-tests (117 failed, 7 errors across browser/runtime suites and scanner suppressions), resulting in closer status `V0110_STAGING_RECONCILIATION_PREPARATION_PARTIAL`.
- 2026-09-13 STAGING-PREP4: Corrective continuation repairing candidate test execution (keyword argument compatibility for `scan_suppressions` test doubles, pinned runtime provisioning via `bootstrap_runtime.py`, bounded output log extension), aligning status documentation, and establishing factual candidate acceptance boundaries. Candidate qualification and per-category verification receipts are recorded in private and external evidence.
Accounting is 55 inherited / 55 terminal / zero OPEN / zero invalid (45 canonical skills: 14 stable / 31 provisional; six active CSS/JS debts; description ceiling 11,507 bytes).

The [evaluation](../../../../evaluations/apg144-public-staging-candidate-and-operator-handoff.md)
records the qualification of the untagged public staging candidate, test boundary containment,
and the attended staging and recovery operator handoffs under the corrective follow-up to APG144 (STAGING-PREP4):
1. Reconciles active repository owners with completed readiness qualification and private publication observations.
2. Contains test transport boundaries so release tests never interact with ambient credentials, real `gh`, or external Git remotes.
3. Builds and checks the untagged public staging candidate commit against accepted public base `250ce73a3dac71a89b8efeee9b8fe6cb0420bf18`.
4. Authors and verifies the hardened attended stage-only operator (`stage_operator.py`) with strict candidate/source projection binding, readback tree assertions, REST pull request validation, and external partial receipts across hermetic test scenarios.
5. Authors and verifies the attended fixture ref recovery tool (`recover_fixture_ref.py`) with guarded `--force-with-lease` deletion executed from the local backup bare repository with tag and submodule suppression to retire the test-fixture staging ref upon separate operator authorization across hermetic test scenarios.
6. Preserves the four-family hosted CI gate and documents observed branch protection state and ruleset requirements in publication-excluded release settings handoff records.

## Preservation and next boundary

All 55 inherited decisions, 45 canonical skills (14 stable / 31 provisional), six active CSS/JS
debts, and the 11,507-byte description ceiling remain intact. External pending state is
preserved: `public_staging: not_started` (incident observed: remote staging branch exists with test-fixture commits and unverified process attribution; attended guarded cleanup tool prepared and verified; public execution pending separate operator authorization), `public_pr_ci: not_run`,
`public_release: not_started`, and branch protection remains unconfigured (observed 2026-09-13).

This dispatch performs no public mutation. The dispatcher owns private Git publication.
Public fixture ref retirement, staging push, PR review, hosted CI execution, squash merge,
tagging, and package release await separate authorization.
