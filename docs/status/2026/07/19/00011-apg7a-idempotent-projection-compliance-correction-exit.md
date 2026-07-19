# APG7A Idempotent Projection Compliance Correction Exit

## Phase identity

- **Phase:** APG7A
- **Date:** 2026-07-19
- **Exit sequence:** `00011`
- **Disposition:** Complete — idempotent install and adopt compliance corrected
- **Controlling decision:** ADR 0004, Accepted and unchanged

## External correction disposition

External review accepted APG7 in substance and authorized one narrow forward-
only correction to its install and adopt idempotent compliance checks. Accepted
APG7 substance includes ADR 0004, the command and state architecture, behavior
outside this defect, the original 26-family suite and lifecycle, the prior
review corrections, the projection guide, the human Superpowers rollback
runbook, unchanged skill maturity, unchanged global state, and false
decommission readiness.

APG7A did not authorize or perform another command, state migration, exclusion
redesign, transaction rewrite, external project mutation, dependency, plugin,
registry, daemon, adapter, package manager, skill, promotion, publication,
licensing, or Superpowers decommissioning.

## Reproduced symptom

The defect was reproduced separately for install and adopt in disposable Git
worktrees with temporary `HOME`:

1. manage one exact APG projection;
2. append a later Git-local negation for that exact projection without changing
   the syntactic APG block;
3. confirm normal porcelain status reports the projection as untracked;
4. repeat the original command;
5. observe exit `0` and `already compliant`; and
6. run check and observe exit `1` for non-clean managed status.

The repeated install or adopt command did not mutate the state, exclusion,
tracked tree, link target, or link inode. The failure was an incorrect success
claim, not partial mutation.

## Root cause

Three hypotheses were distinguished. Malformed state or block input was
disproved because both parsed exactly. Link or tracked-path inconsistency was
disproved because the projection remained the exact readable untracked link.
The confirmed cause was premature control flow: the only two `already
compliant` returns occurred after structural validation but before the existing
managed-status query.

The APG block grammar describes owned entries but cannot by itself prove Git's
effective ignore result when a later rule changes that result. Idempotent
success therefore omitted one accepted compliance invariant that check already
enforced.

## Production correction

The existing command helper now contains one shared
`require_idempotent_status_compliance` guard. Immediately before either
idempotent success return, it queries the existing `managed_status` function for
the complete managed set.

When a managed path is visible, install and adopt return operational failure
and direct the operator to restore the exact local ignore behavior and run
check before retrying. The guard does not move the APG block or edit, reorder,
delete, or broaden a later rule.

An audit found exactly two `already compliant` success returns, one for install
and one for adopt. Both are now guarded. No equivalent success omission remains
in the command.

## Behavioral evidence

Two focused behavioral families were added before production correction:

```text
test_27_idempotent_install_refuses_visible_managed_projection
test_28_idempotent_adopt_refuses_visible_managed_projection
```

Both failed against APG7 production for the intended reason: expected safety
exit `1`, actual exit `0`, and `already compliant` output. After the narrow
correction, both pass.

Clean controls for exact repeated install and adopt now also require a passing
check against the same unchanged repository state. The focused corrected set of
tests 04, 06, 27, and 28 passes.

The complete corrected suite result is:

```text
Ran 28 tests
OK
```

The original 26 APG7 families remain present and passing.

## Disposable lifecycle and recovery

The complete install, check, subset uninstall, remaining check, reinstall,
complete uninstall, compatible adopt, adopted check, and adopted uninstall
lifecycle passes with state counts `6/5/6/0/6/0`.

A separate disposable recovery control proves:

- clean idempotent install and adopt succeed and imply passing check;
- semantic re-inclusion makes repeated install and adopt fail;
- check rejects the same visible state;
- failed commands leave state, links, exclusion, tracked content, and unrelated
  sentinels unchanged;
- the later user rule remains byte-identical; and
- restoring the exact earlier exclude bytes restores passing check and
  idempotent success.

No real external repository was used as a mutation target.

## APG skill decisions

- `debugging-systematically` applied to the inconsistent install/check result,
  exact reproduction, competing hypotheses, control-flow localization, root
  cause, and reproduction-specific verification.
- `implementing-with-test-discipline` applied by adding the two behavioral
  tests before production correction and running focused and full gates after
  the smallest code change.
- `reviewing-and-verifying-repository-work` governs the fresh code-and-safety
  review, complete-diff review, and final integrated claim gate.
- `composing-bounded-worker-assignments` applies only to the independently
  authorized read-only reviewer assignments.
- `planning-repository-work` is a material non-trigger because this phase has
  one narrow correction and one integrated gate.
- `designing-significant-changes` is a material non-trigger because ADR 0004,
  state grammar, ownership, and command architecture remain accepted.

Superpowers was not invoked or followed.

## Independent review

The fresh non-author code-and-safety reviewer independently reproduced both
APG7 baseline defects in a disposable archive and proved the two new tests fail
there for the intended exit-`0` reason. The reviewer then ran the focused
controls and complete corrected suite, audited every idempotent success return,
verified no-mutation evidence, and confirmed every preserved contract.

Code-and-safety disposition: `accept`, with no blocker, material, minor,
optional, privacy, or safety finding and no second material defect exposed.

The separate fresh complete-diff reviewer inspected the exact 17-path staged
correction, including production and tests, public and private reconciliation,
privacy boundaries, counters, modes, preserved architecture, and fresh
validation. The disposition was `accept-with-follow-up`, with no substantive
finding. The only follow-up was replacing pending review wording in three
records. After those bounded updates, the same reviewer confirmed that only
record text changed, the implementation and test diff remained identical,
both whitespace checks passed, and the staged patch was commit-ready.

## Unchanged contracts and state

APG7A changes no command or option, state format version, state key or path,
exclusion marker or grammar, canonical source rule, target ownership rule,
locking behavior, transaction ordering, rollback architecture, dependency,
supported portability boundary, or global behavior. The executable wrapper and
core helper remain unchanged. ADR 0004 remains Accepted; no ADR 0005 exists.

All six APG skills remain `provisional`. No comparative, causal, automatic-
selection, stable-maturity, production-ready, publication-ready, or
decommission-ready claim is made.

Superpowers remains globally installed, unchanged, and reference-only for APG.
No user-level Codex or plugin state changed. Decommission readiness remains
false.

## Evidence and validation

The APG7 public evaluation, APG7 exit, projection guide, provenance, roadmap,
bootstrap, and skill index now contain bounded subsequent-correction records.
Publication-excluded evidence preserves exact snapshots, reproduction details,
test results, and reviewer dispositions. Public records are complete without
that private evidence and do not link to it.

The integrated gate covers read-only repository equality; exact changed scope;
file modes; pre-correction failure evidence; focused and complete corrected
tests; clean and non-clean command agreement; no-mutation evidence; disposable
lifecycle and recovery; canonical skill and APG projection integrity; Markdown
structure and local links; public/private and confidentiality boundaries; ADR
and exit counters; global-state sentinels; prohibited-artifact absence; and
both Git whitespace checks.

Report-tool tests are deliberately not run because APG7A changes no report
executable or shared helper. Non-Darwin portability, hostile same-user races,
and abrupt SIGKILL recovery remain outside the focused correction evidence.
Global plugin actions and real external project mutation are deliberately not
run because they are prohibited.

## Limitations

- The correction evidence covers the current macOS environment and disposable
  Git worktrees.
- Git ignore semantics can still be changed by repository owners; the command
  detects non-clean managed paths but does not repair user rules.
- Advisory locking and abrupt-interruption limitations from ADR 0004 remain.
- Projection compliance does not establish Codex invocation, automatic skill
  selection, comparative improvement, or stable maturity.
- Broader repeated real-project evidence remains necessary.

## External review requested

External review is requested to **accept APG7A as Complete — idempotent install
and adopt compliance corrected, preserve ADR 0004 and the accepted APG7
architecture, retain all six skills at `provisional`, preserve Superpowers
coexistence with decommission readiness false, and authorize no successor phase
automatically**.

That disposition does not authorize another command, broader projection repair,
state migration, another real-project mutation, skill promotion, publication,
licensing, Superpowers decommissioning, or a successor phase.
