# v0.11 Closure Governance

## Ownership and initial state

The [v0.11 roadmap](../v0-11-roadmap.md) owns current inherited scheduling.
Four separate JSON records distinguish release closure, maintenance conditions,
consumer compatibility and leaf maturity. APG138 seeds 55 inherited rows OPEN,
45 maturity rows (14 stable / 31 provisional), nine accepted maintenance
conditions and five unqualified consumer watches. Creating a record is not
closing the linked roadmap item.

| Record | Owner and purpose |
| --- | --- |
| [Closure ledger](v0-11-closure-ledger.json) | Frozen 18 surviving backlog items, RM-S0 through RM-S5 and 31 individual provisional leaves |
| [Maintenance register](maintenance-triggers.json) | Exact accepted conditions, owner, state, consequences, evidence and refresh procedure |
| [Compatibility matrix](external-compatibility.json) | Consumer contract/fixture observations, supported cases, limits and ownership |
| [Maturity ledger](skill-maturity-ledger.json) | Every current canonical leaf, catalog maturity, blocking debts and individual evidence requirements |

The corresponding [schemas](schemas/) are versioned, closed JSON contracts.
`libexec/apg_roadmap_contract.py` owns the independently frozen inheritance
bindings and the narrow schema vocabulary. `libexec/apg_roadmap_closure.py`
validates records and cross-references with standard-library facilities.
It does not implement a general JSON Schema engine. Published schemas are
mechanically compared to the maintained definitions.

## Closure decisions

Ordinary outcomes are `DELIVERED`, `REJECTED`, `CONSUMER_HANDOFF_CLOSED`, and
`MAINTENANCE_TRIGGER`, restricted by each inherited row's route. Maturity
outcomes are `STABLE`, `PROVISIONAL_MAINTENANCE`, and
`DEPRECATED_OR_SUPERSEDED`. Every terminal decision requires a decision record,
qualification references, independent review reference and rationale. The decision
reference must point to a [typed decision receipt](schemas/roadmap-decision.schema.json)
binding the exact item, outcome, closure phase, distinct author/reviewer labels
and outcome-specific evidence categories. Existing arbitrary prose cannot act
as a terminal receipt. These labels do not authenticate actors or prove acceptance.
References must resolve to public repository files; private evidence cannot become a
public prerequisite. Content truth and reviewer independence require actual
review: reference existence does not prove either.

Frozen metadata binds identities, sources, inherited classes, semantic phase
owners, allowed outcomes, prerequisites, triggers and consequences. Changing it
requires a deliberate reviewed contract amendment, not ledger-only editing.
The source consolidation's 18 `HISTORICAL_SUPERSEDED` rows stay excluded.
The 55-item population cannot shrink by deleting a row or expanding exclusions.

Maintenance closure additionally references its exact complete maintenance
record with a false condition. Consumer handoff closure references an explicit
`HANDOFF_CLOSED` ownership decision. A maturity closure must match the named
leaf's individual disposition and its evidence. No existing provider delivery
or historical stable skill automatically closes an inherited row.

## Maintenance and maturity

Refresh conditions and repair conditions remain distinct. The six CSS/JS debt
records copy accepted refresh and repair fields without altering the
[known-debt owner](language-profile-known-debt.json). Pure-Go, migration and
compression conditions retain the accepted APG126 census prerequisites,
with public semantic source references. No condition is broadened to create work.

CSS, pure-Go and migration trigger states are `UNKNOWN` pending their actual
source-bound campaign. Unknown is not false. The measured capacity decision
leaves compression `FALSE`. [ADR 0054](../adr/2026/09/0054-js-qd-005-refresh-trigger-interpretation.md)
controls `JS_QD_005_REFRESH_NOT_TRIGGERED`; its false state rests on that ruling,
not missing report custody. APG138 does not reconstruct APG79B. Future exact
condition changes require current evidence and a deliberate state update.

CSS-QD-001 through CSS-QD-004 and JS-QD-005 block stable maturity; CSS-QD-005
does not. All remain accepted debts. Promotion requires individual evidence
for repeated positive use, representative non-triggers, defect/debt disposition,
rollback, provenance, independent review and current validation. V0110-B owns
that campaign. The initial next-lifecycle fields describe when to gather and
review evidence; they do not invent new accepted repair conditions.

The register begins with existing accepted triggers only. A later
`PROVISIONAL_MAINTENANCE` decision must establish a precise leaf-specific trigger
whose affected skill and exact condition match the leaf, and extend the maintained
trigger contract through its reviewed lifecycle change. APG138 does not pre-author those 31 decisions. The checker deliberately
refuses closure until the corresponding record and evidence exist.

## Compatibility watches

The initial JACA CI, XO and outbox, Repo Map, and DINAS records are `WATCH`.
Existing APGR handoff documents remain source evidence; APG138 observes no new
consumer revision and runs no consumer qualification. Null revisions, contracts,
observation dates and fixture identities mean unavailable evidence, never zero
or compatibility. WATCH entries claim neither supported cases nor adoption.

A future `QUALIFIED` entry requires an observed consumer revision and contract,
observation date, fixture identity, supported cases and qualification references.
A provider-only `HANDOFF_CLOSED` decision can close ownership without claiming
consumer adoption; it still requires explicit evidence and ownership split.
Exact unpublished consumer identities remain in private receipts; public records
use stable source/contract identities with their limits and remain interpretable
without private access. A later fixture must bind its exact receipt before
claiming compatibility. DINAS deployment is consumer-owned and does not gate
v0.11 readiness.

## Maintained checks and transitions

```sh
bin/apg-check-roadmap-closure --json
bin/apg-check-roadmap-closure --json --require-zero
bin/apg-test policy
```

Normal validation permits valid OPEN rows. The explicit zero-backlog mode fails
until all inherited rows have valid terminal dispositions. The result reports
expected/observed totals, terminal/open/invalid/unknown/missing rows, validity
and `zero_backlog_qualified`. `inherited_roadmap_open_items` is a number only
when all four records and sources validate; invalid input returns null and can
never confer zero-backlog authority. A valid foundation has open count 55.

Status transitions do not perform implementation, authorize publication or
prove semantic acceptance. Future phases update their owned rows and evidence,
run focused positive/refusal fixtures, and return for independent review.
V0110-F owns canonical integrated coverage, distribution and zero-backlog proof.

## Semantic adjudication and release obligations

The zero-open result proves accounting completeness under the declared records,
not the truth of their evidence. V0110-C/E and V0110-F must obtain independent
semantic review of every trigger-state transition and each HANDOFF_CLOSED
linkage to inherited items. Review must establish the actual source-bound
condition, the relevance of the consumer ownership decision, and reviewer
independence; existing file paths and distinct actor labels cannot prove these.

Frozen row text retains the inherited source synthesis. Public source references
identify semantic authorities, not guaranteed literal item-ID or text matches;
debt trigger references bridge the APGR backlog IDs to the known-debt IDs.
Later adjudication must explain that correspondence against public authorities
without making private census evidence a prerequisite.

The maturity ledger is a blocking-debt view. Consult the maintenance register
and known-debt owner for all debts, including non-blocking CSS-QD-005. Initial
lifecycle text is a skeleton; each retained-provisional terminal decision must
supply its exact individually reviewed maintenance condition.

APG139's [individual campaign](maturity/apg139/README.md) extends that foundation
with collection-stage inventories and individually bound terminal receipts. `blocking_debts` remains blocking-only;
`debt_authority` identifies the complete known-debt owner, `active_debts` includes
non-blocking entries, and `resolved_debts` separately identifies historical
resolutions. The checker derives both lists from that authority.

The 31 `MATURITY:<leaf>` register entries describe maturity reopening only.
Their `blocks_stable: false` describes the reopening condition, not the leaf;
CSS and JavaScript blocking debts remain independently controlling.
They preserve the original nine refresh records and reference controlling debt
IDs without replacing debt conditions. Their exact payloads are independently
bound by the contract owner. A FALSE observation means the named maturity
evidence or resolution is still missing in the inspected campaign; it does not
mean debt is resolved or its refresh condition is false. A future source or
condition change requires deliberate review and a new binding.

Pending inventories use `apg.maturity-candidate/v1`, with explicit SUPPORTED,
LIMITED, MISSING or PENDING assessments. Missing evidence has an observation,
not invented invocation telemetry. These inventories cannot satisfy the terminal
receipt schema. At closeout, actual review must be bound consistently in the
ledger, terminal receipt and closure row; outcome-specific evidence must match
the named leaf. Historical producer inventories may remain pending as evidence
of their collection stage. The schema extension belongs to unreleased v0.11;
the public v0.10 contract is unchanged.

V0110-F must register and qualify the foundation checker, contract, schemas,
records, roadmap, ADR and phase records in the new versioned public release
surface, including critical-file membership and test-selection closure.
V0110-G consumes that qualified surface. The frozen v0.10 release inventory
remains historical and is not a valid selection for the added foundation.

## APG140 external support closure

The [APG140 campaign](external/apg140/README.md) records dated source-bound
compatibility and twelve terminal decision receipts bound to supplied independent
review. Actual accounting is 43 terminal / 12 open / zero invalid. The migration
condition is FALSE because no gap was demonstrated by the inspected single-language
scenario, not because all possible migration gaps were disproven; the supplied
review accepts this bounded UNKNOWN-to-FALSE transition. Other maintenance conditions and all
APG139 maturity decisions are unchanged. Repo Map QUALIFIED denotes APGR-local
fixture evidence only; JACA HANDOFF_CLOSED denotes provider ownership closure
with concrete unsupported adoption cases, including legacy envelope differences.
The original APG138 UNKNOWN/WATCH descriptions above remain historical entry
state. Candidate receipt wrappers cannot serve as terminal decision receipts.

## APG141 V0110-D closure

APG141 closes [optional work](../evaluations/apg141-optional-work-closure.md)
after supplied independent review and scoped terminal verification: 55 inherited /
47 terminal / 8 open / zero invalid. Separate decisions deliver bounded hotspot
history v2 and the report-key repair, and reject the Caveman adapter and result-field
restriction. Combined complexity/churn scoring is explicitly abandoned for the
inherited hotspot item. At the historical APG141 exit, V0110-E/F/G and
release remained unstarted.

## APG142 V0110-E terminal closure

APG142 [audits the eight exact maintenance triggers](../evaluations/apg142-exact-trigger-maintenance-closure.md) and strengthens
maintenance receipt reference consistency. Supplied independent review supports
all eight FALSE findings; separate terminal receipts and ledger transitions are
post-review amendments with scoped closeout verification. Actual accounting is
55 inherited / 55 terminal / zero OPEN / zero invalid. Prior outcomes and all
active debt/maturity consequences remain intact. V0110-F must reconcile ADR 0055
status and qualify the new governance/checker/schema/test-selection surfaces.
No independent re-review of amended bytes is claimed. At the historical
APG142 exit, V0110-F/G remained unstarted.

## APG143 current capacity and readiness status

[ADR 0055](../adr/2026/09/0055-v0-11-capacity-and-closure-governance.md) is
Accepted on the manager's 2026-09-12 disposition. Its APG138 proposal and
measurements remain historical. APG143 remeasures 45 discoverable leaves,
11,142 description bytes and 11,126 characters under the unchanged 11,507-byte
ceiling and `v0.10-browser-runtime` enforcement identity. Provider token/context
overhead remains unavailable. Maturity remains 14 stable / 31 provisional.

Current closure accounting is 55 inherited / 55 terminal / zero OPEN / zero
invalid, including all eight maintenance decisions. These counts do not
substitute for semantic readiness review. The [APG143 evaluation](../evaluations/apg143-integrated-readiness-prerequisite.md)
preserves the blocked READINESS1 attempt as historical evidence. READINESS2
implements prospective capture, additive v0.11 public selection, distribution
preparation, and public staging PR CI source. Its terminal candidate remains
unqualified: integration branches are 4,109/5,168, file-length policy remains
unresolved, and static/suppression findings remain unapproved. Source-bound package evidence does not establish
hosted CI, consumer adoption, or release acceptance. Supplied review findings
are dispositioned with terminal corrections and scoped verification; the
dispatcher owns Git finalization.

### READINESS3 continuation

READINESS3 continues APG143 / V0110-F / exit 00188. The manager-authorized
file-length policy and no-growth allowances are implemented, lint is corrected
with exact immutable-fixture classifications, and real suppression/nonsecret
records replace line/count-only observations. Suppression approvals await the
dispatcher pre-final review; local qualification and evidence applicability are
recorded by the current APG143 evaluation and managed records. READINESS1/2
remain historical blocked attempts. No readiness acceptance, V0110-G, public
operation, consumer adoption or host mutation follows automatically.
