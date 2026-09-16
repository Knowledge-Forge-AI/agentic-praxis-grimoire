# APG142 context-budget compression audit

Closure ID and trigger ID: `APGR-CXT-BUDGET-COMPRESSION`.
Observation date: 2026-09-12. Producer finding: **FALSE**.
Status: terminal MAINTENANCE_TRIGGER after supplied review; refresh finding FALSE.

## Accepted condition and baseline

The exact recurring condition in the [maintenance register](../../maintenance-triggers.json)
is exhaustion of ADR 0053 capacity ceiling (11,507 bytes) or explicit operator
rejection of the reservation model. The separate repair prerequisite is semantic
discovery parity demonstrating no routing-precision loss across benchmark queries.
[ADR 0055](../../../adr/2026/09/0055-v0-11-capacity-and-closure-governance.md)
retains that ceiling and the `v0.10-browser-runtime` mechanical enforcement identity.
Its status still says Proposed for dispatcher pre-final review. This audit does
not promote that status or reopen APG138; the current assignment explicitly
preserves its capacity policy. The fresh observation below supplements that ADR.

## Current observation and sufficiency

The maintained `bin/apgr skills context-report` returned 45 discoverable leaves,
no malformed metadata, **11,142 UTF-8 description bytes** and **11,126 description
characters**. This is 365 bytes below the retained 11,507-byte ceiling.
The maintained `bin/apg-check-skill-library --format json` passed with exactly
45 canonical skills, 45 catalog rows and 45 projections. Catalog maturity remains
14 stable / 31 provisional. `skills/discovery_policy.go`,
`testing/apg-discovery-policy.json`, `libexec/apg_skill_library_check.py`,
canonical leaves and projections are preserved against APG141 entry.
The comparison is current tooling over the current canonical source, not a copy
of ADR measurements. No description compression or leaf admission is proposed.

The operator's present task expressly retains reservation and says that a
zero-backlog target is not rejection of it. No new operator capacity decision is
in this assignment. Thus neither branch of the exact condition is satisfied in
the inspected current policy and source. This conclusion covers this operator
instruction and supported inventory, not hypothetical future capacity demand.

Whole canonical content separately totals 562,538 bytes, 561,448 characters and
9,840 lines. Those totals do not replace the description ceiling measurement.
No selected bundle or materialization was performed in this campaign; ADR 0055's
representative selected-content values remain historical evidence, not fresh
results. Provider prompt overhead, total context and context fit are unavailable;
bytes and characters are not provider tokens.

## Consequences and refresh

Terminal outcome after supplied review: `MAINTENANCE_TRIGGER`. The separate
receipt binds that review; closeout verified the terminal transition. Capacity policy, reservation,
all 45 leaves and maturity remain unchanged; there is no stable-blocking debt on
this trigger and the six profile debts are independently preserved.

Next owner: APGR capacity maintainers and the operator for reservation decisions.
On a description/inventory change, rerun maintained context-report and skill-library
checks against ADR 0055. On ceiling exhaustion or explicit operator rejection,
record TRUE and obtain the required semantic routing-parity qualification before
bounded compression. UNKNOWN remains OPEN if current measurement or operator
intent is unavailable. A changed capacity decision requires its own identifiable
reviewed amendment; this audit grants none.

Terminal decision: [individual receipt](decisions/APGR-CXT-BUDGET-COMPRESSION.json).
Review and post-review amendment boundary: [supplied work review](work-review.md).
