# APG139 — Individual Maturity Closure

Phase ID: `APG139`

## Status and authority

Terminal disposition: **amend**.
`V0110_INDIVIDUAL_MATURITY_CLOSURE_QUALIFIED`.
The [campaign](../governance/maturity/apg139/README.md) records 31 individual
PROVISIONAL_MAINTENANCE decisions, zero promotions and zero deprecations.
The dispatcher supplied independent pre-final semantic review; its
[findings and closeout dispositions](../governance/maturity/apg139/independent-review.md)
are bound in every terminal receipt. Closeout authored terminal bindings after
that review under the explicit stage envelope, without another review.
Closure accounting is 55 inherited / 31 terminal / 24 open / zero invalid.

## APG138 manager identity correction

APG138's current status path changes forward from
`docs/status/2026/09/12/00182-apg138-v0-11-foundation-closure-exit.md` to
`docs/status/2026/09/12/00183-apg138-v0-11-foundation-closure-exit.md`.
APG137 already reserved exit 00182 privately. Its reservation and APG138's
historical candidate receipts are preserved. The status index and current
foundation checker binding use 00183. APG138's substantive authority remains
`V0110_FOUNDATION_CLOSURE_LEDGER_QUALIFIED`; public v0.10 is unchanged.
The correction passed 75 governance tests and six subtests, record identity,
and closure accounting before substantive maturity changes.

## Historical proposal and plan-review disposition

The original assignment remains the identity correction and individual
maturity campaign. Proposal amendments address the supplied plan review:

- Missing or limited use evidence is recorded explicitly in each candidate;
  references to these observations do not claim positive use. All seven
  terminal evidence categories remain required.
- Separate `MATURITY:<leaf>` lifecycle records bind the exact controlling debt
  IDs and the missing guidance-use family. Their false state observes an unmet
  maturity-reopening condition. It does not reinterpret UNKNOWN CSS refresh
  states or declare unresolved debt false.
- Byte equality binds the maturity ledger to its maturity reopening condition.
  Debt refresh and repair text stays under the unchanged known-debt authority.
- Pending candidate inventories are a distinct schema from terminal receipts.
  Review fields remain null; terminal accounting is deferred to closeout after
  the dispatcher supplies actual review evidence. A synthetic test fixture can
  exercise 31/24/0 accounting but cannot accept these candidates.
- No deprecation is proposed. Catalog vocabulary and physical leaf ownership
  remain unchanged.
- The complete debt view includes active debts and a separate resolved history;
  JS-QD-001 through JS-QD-004 are resolved history, not active blockers.

The entry product had no cumulative tracked changes. Observed Serena cache
changes were operational metadata, not product changes requiring disposition.

## Preservation and rollback

The inherited population remains 55, including 31 maturity and 24 non-maturity
rows. Canonical, catalog and projection counts remain 45/45/45 and maturity
remains 14 stable / 31 provisional. ADR 0055 retains the 11,507-byte ceiling,
11,142 measured description bytes and zero admissions. No skill description or
procedure is changed. ADR 0054 and `JS_QD_005_REFRESH_NOT_TRIGGERED` remain
controlling. CSS-QD-001 through CSS-QD-004 and JS-QD-005 remain stable blockers;
CSS-QD-005 remains non-blocking active debt.

Rollback restores the APG138 maturity and maintenance schema/records together
with their checker definitions, preserving this campaign as superseded
evidence. Keep the corrected APG138 exit 00183: rollback must not reintroduce
the reserved-identity collision. Any future label rollback must be an explicit
leaf decision preserving prior receipts. This phase changes no consumer or
deployment state and therefore requires no consumer migration.

## Qualification and remaining boundary

The [campaign qualification record](../governance/maturity/apg139/qualification.md)
states checks actually run and their limits. The supplied independent review sampled underlying evidence, inspected every
leaf trigger and both debt-bound leaves, and found no systematic inflation. Reference
existence and distinct actor labels do not authenticate reviewers.

V0110-C/D/E, integrated readiness V0110-F, release work, host activation,
external consumer mutation, new admissions and successor dispatch were not
started. Scoped final verification is provider-local; Git finalization remains
dispatcher-owned.
