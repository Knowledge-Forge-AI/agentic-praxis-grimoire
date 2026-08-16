# APG76 CSS Language-Profile Candidate Recovery

## Outcome

APG76 verified exact APG75A delivery, preserved the complete rejected CSS
history, freshly selected the CSS source modules the candidate and the current
targets actually depend on, freshly pinned both read-only targets, inventoried
every target CSS-bearing artifact, and authored one fresh reusable CSS
language-profile candidate with one APG-owned fourteen-case target-first
fixture.

[ADR 0044](../adr/2026/08/0044-css-language-profile-candidate-and-target-first-harness.md)
is **Proposed**. Nothing is integrated. APG77 independently reconstructs every
expectation and terminally decides that ADR under
[ADR 0042](../adr/2026/08/0042-language-profile-production-recovery-and-iterative-hardening.md).

## Baseline

APG75A commit, tree, sole parent, path set, numstat, message, and patch were
verified before any CSS byte was written, and its omnibus parsed as exactly
two associated records. Local `main` and remote-tracking `origin/main` are
exact APG75A, and the tracking reflog shows only fast-forward updates. The
APG75A, APG75, and APG74 branches are preserved at their exact commits.

One ordinary record-finalization distinction is recorded rather than treated as
a failure: the private APG75A review file describes the first staged object and
still says fresh corrected-object review is required, while the terminal APG75A
operational record separately reports three fresh non-author reviewers
accepting the corrected staged object with zero Critical, High, Medium, and Low
findings and proving final branch and main equality. The private file is an
intermediate checkpoint; the operational record is terminal execution evidence.
APG76 amends nothing in APG75A and creates no APG75B.

## Rejected CSS history

The APG61 authoring object and the APG62 rejection object were verified as
exact Git objects, including the sixty-row contract map that APG61 authored and
the terminal APG62 tree in which every current CSS surface is absent. APG62's
seven initial material defect families and its fresh corrected-state defect —
a universal `record-growth-state` obligation contradicting six deliberately
exempt frozen cases — are preserved as falsification evidence.

APG76 uses that history as evidence, not as text. No rejected candidate prose
was read into the new candidate, no sixty-row exact-action map exists, no
universal record-growth-state obligation returns under any name, and no numeric
whole-file band appears. ADR 0035 and ADR 0036 remain Rejected.

## Sources and targets

Fourteen CSS modules were selected because an authored fixture construct or an
observed target construct depends on them, each with its publication status and
date read live. Normative specification text, the mutable drafts repository,
explanatory browser documentation, and compatibility data are kept in separate
roles; only the first settles meaning. Rights are the W3C Software and Document
License, and no specification prose, algorithm, table, example, or test was
copied.

The website target tracks no CSS artifact. The theme target authors twelve
stylesheets and four host components with embedded style regions, and its
observed constructs — one entry-point cascade layer, custom properties,
nesting, media conditions over width and user preferences plus one bare print
media type, colour mixing and perceptual colour, generated content on
pseudo-elements, flow-relative sides with no writing-mode declaration, and
important declarations — determined which decision scopes the candidate
carries. Two constructs occur only inside the host style regions and in no
stylesheet: `@supports`, and the target's single `var()` fallback. That
asymmetry is recorded rather than flattened, because an inventory that counts
host components without reading their style regions produces false absence
claims. Constructs no authored CSS uses are recorded as absent rather than
invented.

No target manifest or script selects a CSS parser or transformer, so no parser
smoke was run and no dependency was added to make the fixture look executable.
Both targets were read only as exact Git objects; none was installed, built,
tested, linted, previewed, browsed, or mutated.

## Candidate

The candidate is the leaf `skills/css-language-profile/SKILL.md`, the
specification [`docs/specs/css-language-profile.md`](../specs/css-language-profile.md),
and the navigation-only record
[`docs/specs/css-language-profile-scenario-coverage.md`](../specs/css-language-profile-scenario-coverage.md).

Twenty-four scenarios `APG76-CSS-001` through `APG76-CSS-024` map onto
twenty-six globally unique stable clauses; the two clauses no scenario cites
are operational rather than semantic and are documented as such. Selection and
response vocabularies are disjoint, the response axis has exactly four values,
present and required evidence stay disjoint, and parser, transformer, and
browser roles are bound independently. The structural-policy disposition is
**deferred**: qualitative signals route review and never decide failure.

## Fixture

`src/test/fixtures/apg76-css-target-first/` carries fourteen cases
`APG76-FX-001` through `APG76-FX-014` across nine independently written source
files, a canonical duplicate-refusing manifest, and a README that closes the
state vocabularies. Every manifest path exists, every file is owned by at least
one case, and no case binds a concrete parser, transformer, browser, version,
or invocation to a `not-selected` or `unresolved` role. The fixture commits no
target source, generated output, build output, source map, package manifest, or
lockfile.

## Lifecycle and boundaries

The Claude branch carries the transitional thirty-one canonical leaves against
thirty catalog rows and thirty projections, and the ordinary library checker
reports the expected uncataloged-candidate diagnostics without being weakened.
Integrated `main` remains 30/30/30 with fourteen stable and sixteen provisional
rows and 28/1/29 routes. TypeScript and Markdown remain retained provisional;
CSS and JavaScript integration remain absent. Published and active corrected
v0.4.0 are unchanged.

No CSS integration, maintained hardening test, target command, JavaScript, JSX,
Node, React, MDX, Astro, or Vitest work, readiness, publication, deployment,
stable promotion, APG77, or successor phase began.
