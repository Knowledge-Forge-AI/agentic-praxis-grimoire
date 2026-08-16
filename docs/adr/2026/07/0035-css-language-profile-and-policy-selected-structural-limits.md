# ADR 0035: CSS Language Profile and Policy-Selected Structural Limits

- Status: Rejected
- Date: 2026-07-29
- Proposed in: APG58
- Decided in: APG59
- Relates to: ADR 0012 (Accepted; language-profile contract),
  ADR 0029 (Accepted with amendment; unchanged),
  ADR 0031 (Rejected; unchanged), ADR 0034 (Rejected; unchanged)

## Context

APG58 isolated CSS from the rejected Web/Node family-threshold work and
proposed one candidate under explicit maintainability-policy limits:
`Green < 300`, `Yellow 300–599`, `Orange 600–899`, and `Red >= 900`
nonblank physical lines in ordinary handwritten standalone stylesheets.
Those limits were policy-selected before target placement, not derived from
sampled corpus tails.

APG59 independently verified the exact APG58 object and reports, CSSWG source
and rights evidence, both pinned target trees, all twelve standalone counts,
four embedded contexts, and target-rights boundaries. Failing-first contracts
and initial non-author review reproduced five material defects:

1. no task-baseline, projected, and actual-result classification;
2. no complete-task aggregation boundary against incremental evasion;
3. repository and human authority wording that could reverse accepted local
   instruction precedence;
4. accessibility examples that could invent requirements; and
5. overbroad global custom-property escalation.

One forward correction clarified those behaviors without retuning the numeric
policy. Fresh corrected-state review found the amended policy prose coherent
but found the retained verification and removal contract materially
incomplete: required response outcomes were not executed, several task and
semantic controls were only phrase checks, rejected cleanup was not exercised,
and the documented removal path omitted hard-coded project and release owners
that would leave stale references.

## Decision

Reject the candidate under APG59's one-correction rule. A new material
retention defect after corrected-state review cannot receive a second behavior
correction in the same phase.

The current candidate leaf and specification are removed. APG59 adds no
projection, catalog row, route, maturity row, release row, project-skill owner,
test owner, dependency, public object, active object, or target mutation.
Development remains 28 canonical skills, 28 catalog rows, and 28 relative
projections, with fourteen stable and fourteen provisional rows, twenty-six
general routes, one ChatGPT-local route, and twenty-seven checked route edges.

The 300/600/900 proposal remains rejected decision evidence, not active
guidance. It is not generalized to another profile. ADR 0031 and ADR 0034
remain Rejected, every Web/Node candidate remains deferred, and corrected
public and active v0.4.0 remain unchanged.

## Consequences and re-entry

APG58 and APG59 evidence remains durable. Any future CSS attempt requires
separate maintainer authority and a fresh phase baseline. It must begin from
the complete defect ledger, freeze executable response and cleanup contracts
before candidate behavior, exercise removal against every hard-coded owner,
and receive independent review. APG59 authorizes no re-entry, successor,
readiness, publication, deployment, migration, or target work.
