# APG122 v0.10 Foundation and SVG Vertical Slice

## Scope and status

APG122 implements the v0.10 foundation and first SVG authoring slice. This is
a terminal producer amendment after dispatcher pre-final review. Closeout
verification is recorded below; Git finalization remains dispatcher-owned.

Public v0.9.0 publication remains terminal. The accepted APG121 reconciliation
is preserved; the superseded publication-reconciliation draft is not executed.
Adapter deployment and consumer changes remain separately owned.

## Proposal disposition

Disposition: **amend**. The original task scope is retained. Plan-review
findings change policy storage/parity, clarify explicit-only selection, bind
the exact six candidate names, expand current integration-surface inspection,
and preserve frozen lifecycle vocabulary. No stage deltas were reported.

## Capacity decision

The maintained context report confirmed 39 leaves, 9,504 UTF-8 description
bytes and 9,492 characters. Full skill files occupy 495,319 bytes. These are
different measurement surfaces, and neither is a provider-token estimate.
[ADR 0053](../adr/2026/09/0053-v0-10-discovery-capacity-and-svg.md) records the
three alternatives and bounded v0.10 reservation policy. The original 39 leaf
contents and historical release measurements are preserved. Parent SHA-256
comparison verified all 39 complete files unchanged.

The integrated maintained metadata report measures 40 discoverable leaves,
9,745 description bytes and 9,733 characters, leaving 112 bytes under the
current 9,857-byte ceiling. SVG uses 241 description bytes and a 13,328-byte
complete file, below its 20,480-byte limit. Actual materialization measures
13,569 initial bytes for SVG alone and 47,065 for explicit SVG/CSS/JSX/React
composition (1,077 descriptions plus 45,988 bodies). These values exclude
provider-specific overhead and do not claim token counts.

## Consumer and semantic boundaries

The consumer-needs inspection is read-only and distinguishes implemented
authoring surfaces from proposed future work. Tailwind and shadcn/ui are
manager-directed UI direction rather than proof of current integration.

[The SVG contract](../architecture/v0-10-svg-language-profile.md) owns graphics
language semantics. Its 24-row project-owned fixture harness provides bounded
structural and mathematical evidence for 18 rows; six ownership handoffs are
expressly navigation-only. It does not establish browser pixel or
accessibility-tree qualification. Broader accessibility, Playwright automation and browser
runtime remain future owners. Existing CSS/JS/TS/JSX/React ownership remains.

## Verification

Capacity prerequisite tests passed before SVG admission. Integrated focused
capacity/SVG and adjacent-profile tests, metadata byte parity, exact clause
navigation, materialization and topology checks passed. Go tests and vet/race
for skills and CLI passed; the footprint consumer tests, vet and race passed. The maintained
policy runner passed inventory, skill-library and record-identity checks.

The first combined run exposed current-count fixtures that still expected 39,
historical release fixtures sourcing the expanding development inventory, and
pre-publication wording assertions inconsistent with accepted APG121. Those
fixtures and assertions were corrected; the frozen release-policy implementation
and v0.9 surface remain unchanged. A focused standalone TypeScript check used
the ambient compiler and was rejected; the combined runner uses the existing
qualified compiler binding. No dependency or threshold was changed.

The maintained combined runner passed on the corrected source: 3,485 unit
tests and 622 integration tests passed, with two integration skips. Unit
statements/branches were 9,771/11,378 and 3,457/4,294; integration was
9,771/11,378 and 3,450/4,294. The combined union was 10,293/11,378 statements
and 3,738/4,294 branches. Independent 80% component and 85% combined gates
passed with unchanged thresholds and denominators.

An earlier all-tests-passing run failed integration branch coverage. Useful
remediation added real command/filesystem capacity refusal and recovery cases,
including selector schema, UTF-8 byte limits, baseline preservation, duplicate
and missing identities, and unauthorized admission. The subsequent combined
pass supersedes that coverage failure; exact receipts retain both dispositions.

Work-stage outcome: `V0100_FOUNDATION_SVG_VERTICAL_SLICE_QUALIFIED`.
The prior combined receipt qualifies the work-stage source. Closeout uses
focused verification for the evidence-classification and documentation changes;
it does not claim a new combined-suite or coverage measurement.

## Deferrals and rollback

SVG's initial maturity is provisional. Browser rendering, assistive-technology
behavior, broader consumer dogfood, future leaves and v0.10 public publication
remain unqualified. Removal must reconcile the leaf, projection, catalog,
route, metadata and current inventories while preserving historical records.
No automatic successor is authorized.

## Closeout disposition

Disposition: amend. F1 is accepted: row 024 now reports navigation-only, with
an exact 18 semantic / 6 navigation-only test assertion. No keyboard, focus or
interaction behavior is inferred from a static meaningful-image fixture. F2 is
accepted: all six routing purposes explicitly distinguish requested behavior
from the contextual fixture. F4 is accepted: project-model and language-profile
contract summaries now record APG122 topology and capacity while retaining
historical paragraphs.

F3 is deferred: the safe-resource fixture proves a self-contained boundary,
not a permitted external resource under a trust policy. Filters, browser
interaction and permitted external-resource behavior remain unqualified. F6
requires no change: the future ceiling is a reservation, not additional current
admission authority; disclaimer substring assertions are not semantic proof.

F5 is addressed with a separate terminal source manifest and scoped closeout
receipts. Prior combined/Go results remain work-stage evidence, not a claim
that those commands were rerun on terminal bytes. No substantive review is
requested after the terminal amendment.

Terminal checks: the focused SVG pytest suite passed 29 tests after its
classification test first rejected the old outcome binding. The maintained
`bin/apg-test policy` gate passed inventory, skill-library and record identity.
The maintained context-report function over all canonical leaves confirmed
40 leaves, 9,745 description bytes and 9,733 characters. `git diff --check`
passed and the index remained empty. No combined suite, coverage, Go, browser,
consumer-runtime or external publication check was rerun during closeout.
