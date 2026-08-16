# APG81C Node.js lifecycle, test, and local-scratch closure

## Scope

APG81C is the explicit human continuation after the APG81B repair checkpoint.
It authorizes exactly the three integration-support corrections found there:
coherent candidate-preserving rollback lifecycle, non-self-referential final
staged review, and the xdist timeout-cleanup test's per-invocation assertion.
It also establishes ignored repository-local APG durable scratch after auditing
the shared purge subtree. It does not reopen Node semantics or qualification-
harness behavior and accepts no debt.

## Local durable scratch

Repository-local `.scratch/` is ignored, untracked, machine-local, excluded
from releases and public surfaces, and never qualification/runtime temporary
storage. The shared purge subtree audit found no APG future-needed unique item:
needed state was already durable or reproducible, so no entry was transferred,
moved, or deleted. The detailed local manifest remains ignored and is not a
portable source of truth.

## Integration-support correction

Post-acceptance rollback preserves ADR 0046 as Accepted with amendment,
retains the Node candidate, removes all current Node integration owners, and
uses `accepted-integration-rolled-back` across retained current lifecycle
surfaces. Historical APG80 Proposed provenance remains historical.

Final staged integration review is external evidence bound to one frozen staged
identity. Repository records describe the protocol and target as
`review-target-frozen`; they do not attest to their own final review. Only after
external review returns may the commit message record that result, without a
staged-byte change.

The timeout cleanup integration test now owns one explicit invocation context,
observes that exact invocation root, and requires only that root to be absent
after timeout cleanup. It does not enumerate sibling roots that another xdist
worker may legitimately own. Production cleanup and runtime behavior are
unchanged.

## Immutable review and terminal result

Fresh precommit review of the human-authorized extra correction returned zero
Critical, High, Medium, or Low findings with zero Node debt. Immutable review
then found one new Medium review-sequencing contradiction: two committed
publication-excluded records still described precommit review and correction
commit/report creation as pending, while the commit message and associated
operational report correctly recorded their completion. The implementation and
managed report mechanics otherwise passed review.

APG81C therefore stops before integration at a terminal repair checkpoint. The
support correction is retained, but no Node catalog row, projection, maturity
row, route, project selection, release membership, integration inventory owner,
or ADR acceptance is added. ADR 0046 remains Proposed and Node remains
corrected, repair-required, and unintegrated at 33/32/32. Main remains APG79E
at 32/32/32, 14/18, and 30/1/31. Public and active corrected v0.4.0 and both
targets remain unchanged and unexecuted. No further correction, stable
maturity, publication, deployment, APG82, or successor work is authorized.
