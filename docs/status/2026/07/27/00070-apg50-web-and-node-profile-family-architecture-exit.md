# APG50 Web and Node Profile-Family Architecture Exit

Status: Complete — web and Node profile-family architecture, source
baselines, and authoring slices proposed; Codex peer review pending

Phase ID: `APG50`

Status date: 2026-07-27

## Scope

APG50 verified the exact APG49 baseline (the single-parent mainline
object behind exit 00069 with its complete managed reports; exact
development identities remain publication-excluded), inspected the two Knowledge Forge AI target repositories
read-only at exact commits, established primary-source/version/rights
baselines for all ten Workstream 3 candidates, designed the owner graph
and overlap routing, dispositioned adjacent gaps, defined the structural
warning/crisis calibration method, froze architecture scenarios
APG50-WEB-001 through APG50-WEB-060, proposed bounded authoring slices
and ADR 0031, and created the complete Codex APG51 peer-review handoff.

## Results

- Dispositions: seven architecture-supported (javascript, typescript,
  nodejs-runtime, css, markdown, mdx, astro), one
  architecture-supported-with-target-evidence-gap (jsx), two
  defer-missing-dogfood (react-component, vitest-test).
- Adjacent gaps: HTML and browser/DOM runtime recorded as unowned
  deferred adjacent candidates; accessibility deferred; Starlight
  project-owned with a recorded deferred residual; package managers,
  bundlers, lint/format, deployment, and browser compatibility
  project-owned for v0.5.
- Slices: A (JS/TS/Node), B (CSS/Markdown, parallel), C (MDX + JSX
  conditional on the Codex gap decision), D (Astro); React and Vitest
  excluded pending real target evidence. No slice authorized.

## State

```text
profile leaves:
  0

development:
  28/28/28
  14 stable / 14 provisional

ADR 0031:
  Proposed

target repositories:
  read-only and unexecuted

public/active:
  corrected v0.4.0 unchanged

successor:
  not authorized
```

## Verification

Authoring-safe checks only: exact base and branch identity; target
non-mutation; ledger completeness; bounded 23-file sample; ten owner
cards with dispositions; sixty continuous unique scenario IDs; no
mandatory chain and no Node→TypeScript prerequisite in the graph;
conditional React pairing; no Starlight candidate; gap analysis without
scope expansion; ADR 0031 Proposed with prior ADR statuses unchanged;
unchanged 28/28/28, 14/14, and corrected v0.4.0 claims; clean-room,
privacy, personal-data, public/private surface, Markdown/link,
record-identity, whitespace, staged-diff, and commit-message checks.
No APG executable suite and no target/package/Node/web command ran.

## Boundary

APG50 authored no profile leaf and changed no skill, projection, catalog
row, route, maturity state, test inventory, executable, dependency,
fixture, or release surface. The Go workstream remains closed for v0.5.
`main` did not move. Delivery beyond the attempted bounded branch push
is recorded in the APG50 managed reports. Codex peer review (recommended
APG51) is required before any ADR 0031 decision or authoring slice.
No phase after APG50 is authorized.

## APG51 forward disposition

APG51 later preserved the complete APG50 malformed/revert/formal history,
delivered the exact formal branch, and corrected the design forward once.
Fresh corrected-state rights and corpus defects require ADR 0031 rejection;
all ten candidates are deferred and no authoring slice is eligible. The APG50
historical status above remains unchanged; the
[APG51 exit](../28/00071-apg51-web-and-node-architecture-peer-review-exit.md)
owns the terminal review result and authorizes no successor.
