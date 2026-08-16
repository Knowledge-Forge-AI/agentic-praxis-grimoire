# Language-Profile Iterative Hardening Contract

## Status and authority

This is the normative hardening-round contract accepted by ADR 0042. It
implements the [production recovery charter](../governance/language-profile-production-recovery-charter.md)
without authorizing a profile, integration, target operation, release, or
successor phase.

## Round input

Each round starts from one exact, preserved candidate state and records:

- candidate semantic phase and lifecycle state;
- exact candidate commit or preserved uncommitted snapshot in managed phase
  evidence;
- predecessor and branch parity required by the phase authority;
- exact relevant source, rights, compiler-role, target, and release objects;
- current scenario, fixture, route, ownership, and rollback surfaces; and
- the previous round result and known debt, if any.

A round stops before correction when its input cannot be reproduced, a target
or source object has drifted without disposition, the candidate has been
silently rewritten, or required authority is missing.

## Round procedure

One hardening round is exactly:

1. preserve the exact input candidate and reports;
2. independently reconstruct expected target behavior;
3. collect the complete material finding set for that round;
4. apply at most one coherent correction for that round;
5. preserve the actual correction patch and corrected hashes;
6. obtain fresh corrected-state review;
7. classify remaining defects; and
8. choose the round disposition.

The coherent correction may address one complete, related finding family. It
may not hide unrelated changes, amend the oracle after observing results,
squash away the round boundary, or claim that correction alone proves
acceptance.

## Independent reconstruction and finding ledger

Review reconstructs the expected target behavior without using candidate
wording as its oracle. The round finding ledger contains the complete known
material set before correction. Each finding records evidence, affected
scope, consequence, severity, owner or route, and proposed repair. Critical
and High findings may not be silently waived.

Medium and Low findings remain visible even when they do not block the
correction. A later discovery is not retroactively inserted into the prior
ledger; it is preserved as corrected-state evidence and normally produces
`repair-required`.

Independent lanes establish independent reconstruction; their free-form prose
does not become a product API or routine release owner. Machine checks own
closed vocabularies, identities, exact source bindings, consequence-bearing
routes, stop conditions, lifecycle, and executable product behavior. Human
review owns explanatory prose sufficiency. Exact structured disagreements use
compact explicit adjudication, while equivalent prose requires no item-level
provenance.

Evidence is consequence-bearing and proportionate. Historical phase evidence
remains auditable without remaining current release authority, and a mechanism
materially larger or more complex than the product surface it protects is
narrowed or retired rather than automatically expanded.

## Correction preservation

Before fresh review, preserve:

- the exact correction patch;
- the changed-path set;
- hashes of every corrected semantic artifact;
- applicable parser or fixture result;
- the round's source and target bindings; and
- any deliberately unresolved uncertainty.

The correction record distinguishes candidate bytes, generated or fixture
bytes, target evidence, and managed reports. It does not cite scratch as final
authority.

Current authored evidence, public output, and every newly introduced record
contain no copied target expression. Exact commits, patches, and private
Git-show reports may preserve removed historical bytes as a forensic exception.
The exception neither makes those bytes current evidence nor permits laundering
them into a summary, replacement lane, fixture, test, or new record. Such exact
reports remain private and are never sanitized into a false patch.

## Fresh corrected-state review

Fresh reviewers bind to the preserved corrected hashes and do not author the
corrected state they review. They replay the complete accepted round scope,
including prior findings, near misses, unknown-state controls, owner and route
boundaries, target-facing scenarios, rollback, rights, and source truth.

A fresh material defect after correction does not automatically reject the
candidate. It is classified by consequence and normally produces
`repair-required` for the next separately preserved round.

## Severity and integration effect

Severity is consequence-based:

- **Critical:** data loss, credential exposure, security bypass, unsafe
  irreversible action, use-affecting rights or source-integrity falsehood,
  repository corruption, or deployment-damaging guidance.
- **High:** common in-scope wrong guidance, false completion, a wrong owner
  dropping a required route, behavior-controlling compiler-role invention or
  omission, common target failure, unknown-as-known behavior, or unavailable
  material rollback.
- **Medium:** bounded edge-case defect, incomplete noncritical route, safe
  known unsupported scenario, secondary coverage gap, or noncritical evidence
  gap.
- **Low:** wording, navigation, metadata, bookkeeping, or nonconsequential
  redundancy.

Critical and High block integration. Medium and Low may remain only through
the known-debt gate and explicit human acceptance.

## Round dispositions

### `ready-for-provisional-integration`

Requires zero Critical and High defects, passing target gates, safe stop or
routing for unknowns, truthful rights and source evidence, available rollback,
and no false completion.

### `accepted-with-known-debt`

Requires zero Critical and High defects and only explicit Medium or Low debt.
Each debt item has an ID, severity, affected scope, consequence, safety basis,
workaround or safe stop, owner, repair and refresh conditions, rollback
relevance, target impact, and human acceptance reference.

### `repair-required`

Preserves the candidate, blocks integration, and identifies the next repair
scope. It is the normal result when a repairable material defect remains.

### `fundamentally-unfit-pending-human-decision`

May be recommended only when no coherent owner exists, the candidate is
unsafe by construction, repair would replace rather than correct it, source or
rights integrity cannot be established, the target cannot exercise it, common
work remains routinely misrouted despite narrowing, or repair cost is
disproportionate to product value. The candidate remains preserved until a
human choice.

## Round budget and human checkpoint

The default budget is up to three rounds. Each round has a separate exact
input, finding ledger, correction patch, corrected hashes, fresh reviewers,
and result. Rounds are not squashed.

After three rounds with Critical or High defects remaining, stop for exactly
one human choice:

```text
continue
narrow scope
defer
declare fundamentally unfit
abandon
```

Continuing, narrowing, declaring unfitness, abandonment, rejection, or debt
acceptance cannot be inferred from Codex review.

## Target-first gate

Round evidence prioritizes target usefulness, safety and truthful uncertainty,
common semantic correctness, owner and route correctness, rollback and debt
transparency, representative breadth, and only then exhaustive theoretical
completeness.

Target-facing validation includes actual target scenarios, APG-owned
representative fixtures, negative and near-miss cases, unknown-state controls,
and rollback controls. Intended-state fixtures label intended product state,
live target state, temporary compatibility, and retirement conditions.

## TypeScript role and uncertainty gate

Every behavior-controlling compiler role records the role, selected package,
exact version, selection source, invocation state, evidence, target or
temporary state, and retirement condition. Package or lockfile presence never
proves execution, and one role never proves another.

Unknown compiler role or consequence-bearing option state stops or routes the
claim. TypeScript 6 compatibility is allowed only for an independently
required, explicit role and must have a retirement condition. Static success
never proves runtime success.

## Integration, debt, and rollback

Provisional integration requires the complete surfaces named by the charter,
zero Critical and High defects, passing target evidence, current release
ownership, and proven rollback. Provisional maturity is not stable maturity.

No Critical or High debt enters integration. Medium or Low debt is explicit,
current, discoverable, and human accepted. A blocked gate preserves the
candidate; it does not authorize rejection or removal.

Before any human-authorized removal, preserve the candidate, final correction
patch, necessary test and target evidence, rejection reason, removal patch,
rollback, and complete history. Do not raw-revert evidence-bearing history.

## Completion evidence

A completed round has:

- an exact input identity;
- a complete finding ledger;
- at most one coherent correction;
- an exact patch and corrected hashes;
- fresh non-author review;
- consequence-based severity for every remaining defect;
- one allowed disposition;
- a current debt record when applicable;
- rollback evidence proportional to any integration; and
- an explicit stop at the authorized phase boundary.

Neither a worker result, passing parser, correction commit, managed report, nor
package resolution alone establishes acceptance.
