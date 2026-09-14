# APG140 compatibility maintenance and rollback

## Ownership and refresh

APGR owns its public package semantics, fixture evidence and this support
inventory. Repo Map owns protocol, canonical graph, storage, publication and
migration implementation. JACA owns adapters, runner registration, scheduling,
authorization, transaction/outbox custody, retries and production adoption.
The matrix records bounded provider evidence; no automatic dependency or
blanket future-version compatibility is created.

| Watched change | Refresh owner | Required scoped action |
| --- | --- | --- |
| Repo Map public-read schema aliases, fields, page bounds, ordering or diagnostics | APGR support maintainer with Repo Map contract maintainer | Observe the new mainline contract; assess affected consumer cases; version or retire the fixture; record accepted and refused versions and update the matrix |
| Coordinator protocol version, generation/identity domain, refusal, cancellation or publication evidence | Repo Map contract maintainer; APGR support maintainer evaluates reusable impact | Separate wire compatibility from generation identity and transaction outcome; add adverse fixtures only for APGR-consumed evidence; leave retries/reconciliation consumer-owned |
| Graph canonical identity, edge direction/metadata, provenance, conflict or materialization semantics | Repo Map graph maintainer; APGR support maintainer | Rebuild independently expected small graphs and inspect empirical evidence; reassess the exact reusable-owner gap, without treating cycles as defects |
| Repository-identity/schema migration, backup compatibility, restore or cutover prerequisites | Repo Map storage maintainer; APGR guidance maintainer | Evaluate the recorded migration condition using the new source scenario; retain explicit local/hosted limits and submit any required leaf for separate admission |
| JACA onboarding role/summary contract or APGR runner receipt semantics | APGR qualification maintainer and JACA CI maintainer | Compare producer fields, exit mapping and freshness semantics; run affected provider tests; JACA separately qualifies registration, candidate custody and supported runner platforms |
| JACA interface-control adapter contract or APGR skills/footprint/schema API and error families | APGR library maintainer and JACA XO maintainer | Bind released version and candidate fixture separately; qualify affected DTO, cancellation, sentinel and unavailable-metric behavior; JACA decides production imports |
| Report envelope/result bytes, digests or JACA artifact transaction semantics | APGR report maintainer and JACA artifact maintainer | Assess report.Result compatibility; qualify changed producer bytes; keep persistence, transaction outcome and retry policy in JACA |

A material change invalidates the affected prior supported-case claim until a
dated impact assessment decides retain, revise or retire against exact source
and fixture bindings. Record an explicit versioned fixture decision even when
no fixture bytes change. An unchanged source observation alone is not a new
runtime qualification. Refresh is maintenance, not automatic reopening of the
inherited release backlog or authority to execute a successor.

Unavailable contract evidence must produce WATCH with no supported cases, or
an explicitly narrower provider handoff. A broken APGR producer contract must
be repaired or reported as blocked; HANDOFF_CLOSED cannot hide it. A newly
demonstrated reusable leaf gap requires separate capacity/admission authority.

## Rollback evidence for RM-S0, RM-S4 and RM-S5

This phase adds support evidence and fixture consumers; it changes no external
runtime or storage state. Rollback is an APGR support-record operation:

- RM-S0: withdraw the affected fixture qualification, restore the prior WATCH
  row with empty supported cases, and retain the observation and fixture as
  superseded evidence. Stop using its positive compatibility claim.
- RM-S4: restore the preceding seam matrix and provider-handoff references as
  one coherent change; keep the ownership split and `adoption_claimed: false`.
  No consumer adapter or database needs reversal because none was changed.
- RM-S5: supersede the refresh decision with a dated narrower support decision;
  retain responsibility for reporting unsupported versions. Do not silently
  promise old compatibility or erase the source/fixture evidence.

Terminal receipts now bind the supplied independent review. Rollback requires
a reviewed ledger disposition preserving those receipts as history; withdrawing
a support claim cannot erase an accepted closure. Preserve APG139's 31 maturity decisions, all twelve
V0110-D/E open rows, DINAS watch, skill corpus, capacity policy and public v0.10
inventory. The entry preservation record supplies exact before-state evidence
for dispatcher closeout; it is not a public runtime dependency.

## Present envelope divergence

JACA's artifact/adapter maintainer owns the current chatgpt-report-record versus
agent-report-record decision before any adoption attempt. Record a dated choice
between JACA-side envelope adaptation and a requested APGR compatibility alias,
with the exact source and fixture version. The APGR report maintainer assesses
any alias request for a reusable provider requirement under separate change
authority. Direct ingestion remains unsupported until that choice is implemented
and qualified by its owner. This open consumer maintenance decision applies now,
even if neither contract changes; it does not reopen the inherited APGR row.
