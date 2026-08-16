# APG81A Node.js qualification threat model and harness simplification

## Status

The one authorized APG81A correction and its immutable review are complete.
Terminal integration review found one High rollback defect and one Medium
ADR-index lifecycle defect in the proposed integration state, so integration
stopped and those bytes were not retained. ADR 0046 remains Proposed and
`nodejs-runtime-profile` remains
authored, corrected, repair-required, and unintegrated. No finding is accepted
as debt.

## Historical input

APG81's terminal ledger remains valid falsification evidence: three High
families showed that user-immutable flags did not prevent same-UID executable
replacement, deeper path redirection, or path-based setup before the pin; two
Medium families showed outside-parent mutation and partial restoration or
cleanup overclaim. APG81A changes no historical commit or report and does not
reinterpret the writable nested-leaf consequence as a sixth family.

## Corrected qualification boundary

Qualification now has the closed context
`controlled-local-or-ci-qualification`. It accepts only reviewed APG fixtures,
synthetic non-sensitive inputs, and exact maintainer-selected runtime paths.
Target code, user code, untrusted fixtures, credentials, secrets, shell
execution, application dependency installation, and fixture network access are
prohibited. The harness is not a security boundary. Concurrent hostile same-UID
mutation and untrusted execution route to a security, sandbox, CI-isolation, or
operating-system owner; an absent receiver produces `stop-and-escalate`.

The immutable-flag, protected-parent, flag-restoration, and copied-runtime
sealing mechanisms are retired. Each maintained invocation executes the exact
configured direct regular executable and observes path identity, metadata,
digest, public runtime identity, effective arguments, and `NODE_OPTIONS` state
before and after use. Continuous identity is not claimed.

The parent creates one private unique invocation root with exact `tmp`,
`npm-cache`, `pnpm-home`, `work`, and `fs-case` direct children. Ordinary
preflight rejects relative, foreign, escaped, non-private, or pre-existing
symlink paths. The filesystem fixture accepts only the exact `fs-case` child and
uses synthetic filenames and content. Cleanup attempts every owned action,
reports success only after the invocation root is absent, and reports failure
with bounded contract IDs rather than raw paths or streams.

## Preserved product contract

The 30 stable clauses, 24 navigation scenarios, 14 fixture cases, 41
substantive artifacts, two documentation artifacts, exact module mappings,
CommonJS and ESM ownership, two-runtime semantic contrasts, source and rights
identities, target facts, stopped receivers, structural deferral, and
history-preserving rollback remain. The corrected harness is maintained
qualification evidence, not a target-execution or deployment claim.

Focused candidate, fixture, contract, threat-model, runner, privacy, cleanup,
and exact-runtime evidence passes 120 tests. The complete correction-state unit
component passes 3,043 tests at 6,765/7,822 statements and 2,276/2,842 branches.
Fresh precommit and immutable postcommit review of the APG81A correction commit
found zero Critical, High, Medium, or Low findings and zero Node debt. A later
integration candidate passed its
regression, release, and rollback checks, but fresh complete staged review found
one High defect because disposable rollback deleted the Node candidate instead
of preserving it in the resulting state, plus one Medium defect because the ADR
index detached ADR 0045 from its status and listed ADR 0046 twice with
contradictory Accepted and Proposed states. The reviews were discarded after
those findings, integration stopped, and the attempted integration bytes were
removed rather than repaired forward.

## Unchanged boundary

The candidate remains 33 canonical skills / 32 catalog rows / 32 projections.
Development main remains 32/32/32, 14 stable / 18 provisional, and 30 general /
1 ChatGPT-local / 31 checked route edges. Existing CSS and JavaScript debt
remains exactly ten entries; Node debt is zero. Corrected historical, published,
and active v0.4.0 and both read-only targets remain unchanged and unexecuted.
No stable maturity, readiness, publication, deployment, or successor work is
authorized. A new human continuation decision is required.
