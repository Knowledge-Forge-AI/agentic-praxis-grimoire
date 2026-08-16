# ADR 0044: CSS Language-Profile Candidate and Target-First Harness

## Status

Accepted with amendment (APG77D). APG76 authored one narrow reusable CSS
language-profile candidate and one APG-owned fourteen-case target-first
fixture. APG77 and APG77A through APG77C preserve the independently reviewed
hardening and qualification history. APG77D exercises accepted ADR 0042 human
authority for exactly four Medium qualification-machinery limitations and one
Low compact-schema redundancy. No Critical or High debt and no semantic,
source-fact, target, ownership, runtime, release, or rollback debt is accepted.

The terminal APG77D integration closes exact current-machine proportionality
accounting and binds lifecycle, release, test, historical exclusion, and
rollback through live repository owners rather than caller-provided literals.
CSS is retained provisionally as
`provisionally-integrated-with-known-debt`. The four accepted Medium items
block stable maturity. Compact v3 remains supporting qualification evidence,
not sufficient product authority.

## Context

ADR 0042 is Accepted: language-profile production recovery proceeds by
candidate authoring separated from independent hardening, with target
usefulness prioritized, a repairable material defect treated as
repair-required rather than automatic rejection, up to three separately
preserved hardening rounds, zero Critical and High required before
integration, explicit human acceptance for Medium or Low debt, and terminal
rejection or removal reserved to human authority. It records CSS as desirable
and sequenced after essential TypeScript. APG74, APG75, and APG75A completed
that sequence for TypeScript.

CSS has prior rejected history. ADR 0035 and ADR 0036 are Rejected. APG61
authored a candidate leaf, a specification, and a sixty-row exact-action
contract map; APG62 froze seven material semantic-navigation defect families,
used its one permitted correction, then found a fresh corrected-state defect
in which the correction required `record-growth-state` for every counted
decision even though six frozen cases deliberately omit it. The one-correction
budget was exhausted and every current CSS surface was removed. That outcome
falsified the old candidate and the old lifecycle. It did not show CSS to be
unfit.

APG76 therefore starts from evidence rather than from those artifacts. The
freshly pinned website target tracks no CSS artifact at all. The freshly
pinned theme target authors twelve stylesheets and four host components with
embedded style regions. Its stylesheets use one cascade layer at the entry
point, custom properties, nesting, media conditions over width and two user
preferences plus one bare print media type, colour mixing and perceptual
colour functions, generated content on pseudo-elements, flow-relative sides
without any writing-mode declaration, and important declarations. Two
constructs appear **only** inside the host style regions and in no stylesheet:
`@supports`, and the target's single `var()` fallback. No authored CSS
anywhere uses `@container`, `@property`, `@scope`, or `currentColor`, and the
target carries no generated, vendor, minified, preprocessor, or source-map
artifact. No target manifest or script names a CSS parser or transformer;
CSS-capable packages resolve only transitively.

That stylesheet-versus-region asymmetry is itself a finding: an inventory that
counts host components without reading their style regions produces false
absence claims, which is why the candidate binds the artifact class before the
conclusion.

## Decision

1. Author one reusable candidate whose owner is CSS-specific static semantics
   and cascade or value consequences for an established authored CSS region,
   under exact project-selected source, parser, configuration, and environment
   evidence.
2. Author exactly three candidate surfaces: the leaf
   `skills/css-language-profile/SKILL.md`, the specification
   `docs/specs/css-language-profile.md`, and the navigation-only coverage
   record `docs/specs/css-language-profile-scenario-coverage.md`.
3. Record explicit non-owners and route each simultaneous non-CSS decision to
   its exact owner; never collapse materially distinct obligations into one
   generic owner.
4. Keep three axes separate and disjoint: selection (`selected`,
   `embedded-route`, `route-to-owner`, `non-trigger`), response
   (`proceed-routine`, `inspect-before-judgment`, `bounded-local-decision`,
   `stop-and-escalate` — exactly four values), and a small ordered set of
   routes or obligations. Routing never lowers the response, and a routed stop
   remains stopped.
5. Require present evidence and required evidence to stay disjoint, and
   require every consequence-bearing tool role — parser, transformer, browser
   — to be bound independently. Package or lockfile presence is availability
   evidence, never invocation evidence.
6. Bind CSS sources by exact module and level, never as one undifferentiated
   authority, and keep normative specification text, repository source,
   explanatory documentation, and compatibility data in separate roles.
7. Keep static semantics, build-time transformation, browser rendering, and
   runtime interaction distinct, and refuse to let any of them stand for
   another.
8. Author exactly twenty-four navigation scenarios `APG76-CSS-001` through
   `APG76-CSS-024`, mapped to globally unique stable clause identifiers. The
   coverage record carries no expected outcome and no exact action.
9. Author one APG-owned fourteen-case target-first fixture at
   `src/test/fixtures/apg76-css-target-first/` with a canonical
   duplicate-refusing manifest, closed state vocabularies, and no target
   source, generated output, lockfile, or source map.
10. Where target evidence does not select a listed feature, keep the scenario
    or case a truthful non-trigger, unknown-state, or route boundary rather
    than inventing target use.
11. Adopt **deferred** as the structural-policy disposition. No numeric
    whole-file band, percentile threshold, or universal stylesheet-size rule
    is authorized; qualitative signals are recorded as review-routing
    observations only.
12. Run no parser or transformer smoke, because no exact current target role
    is selected, and add no dependency to make the fixture look executable.
13. Preserve the rejected CSS history unchanged and integrate nothing in
    APG76.

## Consequences

ADR 0035 and ADR 0036 remain Rejected, and ADR 0031 and ADR 0034 remain
Rejected. The APG61 and APG62 objects, branches, records, and reports remain
preserved and unrewritten; APG76 repairs, revives, and amends none of them.
No rejected candidate file is restored, no sixty-row exact-action map exists,
and no universal record-growth-state obligation is reintroduced under any
name.

The candidate is unintegrated. There is no CSS catalog row, projection,
maturity row, capability route, project selection, release owner, or
maintained test owner. The Claude branch carries a transitional
thirty-one canonical leaves against thirty catalog rows and thirty
projections, and the ordinary library checker reports the expected
uncataloged-candidate diagnostics rather than being weakened to hide them.
Integrated `main` remains thirty canonical skills, thirty catalog rows, and
thirty projections, with fourteen stable and sixteen provisional rows and
twenty-eight general, one ChatGPT-local, and twenty-nine checked routes.
TypeScript and Markdown remain retained provisional; JavaScript remains
absent. Published and active corrected v0.4.0 and both targets are unchanged
and unexecuted.

ADR 0042 governs later review. APG77 may Accept this ADR, Accept it with
amendment, or leave it Proposed under a repair checkpoint. Codex may not
reject it or remove the candidate without human authority. If APG77 cannot
reach zero Critical and High findings within its round budget, the candidate
is preserved and the decision returns to the human product owner.

APG77 preserves the candidate as `repair-required`. Its three immutable rounds
close the candidate's known semantic defects but leave two High proof defects:
full target hash/path-object retention and two separately complete independent
oracle vectors. This is a successful governance checkpoint, not candidate
rejection, removal, integration, or permission to relax the evidence gates.

APG77A preserves its immutable target-identity and independent-vector
correction. Fresh review identifies a wrong target-facing SVG authority,
false-pass H2 qualification, and copied target bytes. No debt is accepted.
The correction does not change candidate semantics, but the zero-High gate is
not met, so ADR 0044 remains Proposed and CSS remains unintegrated pending a
new human decision.

APG77B preserves its immutable H3-H5 correction. The target-facing SVG
authority is semantically coherent, and the current-tree contaminated Lane T
is superseded. Fresh review nevertheless finds four High and two Medium defects
in adjudication semantics, generated-report and escaped-copy boundaries,
immutable diff binding, distinct same-owner-obligation qualification, and
artifact proportionality. No debt is accepted. ADR 0044 remains Proposed and
CSS remains unintegrated pending a new human decision.

APG77C preserves every earlier object and finding. Its correction does not
change CSS candidate semantics or TARGET-007 source authority. The APG77B H1
ledger, Lane N, Lane T2, and resolved provenance remain historical evidence;
the maintained scenario fixture, exact primary sources, compact structured
decisions, focused tests, and human review own the current integration gate.
Fresh APG77C review finds TARGET-007 source-guard circularity, incomplete
disagreement and row-source qualification, conflicting route-stop false passes,
incomplete proportionality accounting, unbound lifecycle proof, and one compact
schema redundancy. No debt is accepted. ADR 0044 remains Proposed, CSS remains
unintegrated, and a new human decision is required.

APG77D exercises that human decision without reopening CSS semantics. The
current known-debt register accepts `CSS-QD-001` through `CSS-QD-005` for
provisional integration only: four Medium qualification limitations block
stable maturity, while the one Low schema redundancy does not block stable
maturity by itself. Compact v3 remains supporting qualification evidence and
is not sufficient source, disagreement, route, lifecycle, release, or rollback
authority. M05 accounting includes every current machine artifact; M06 closes
only through repository-bound checks after integration. The first APG77D
decision commit did not integrate CSS or terminally decide this ADR. The
terminal commit subsequently passes every ordinary integration, regression,
release, public-preservation, and disposable-rollback gate. Current development
is 31/31/31, with fourteen stable and seventeen provisional rows, twenty-nine
general routes, one ChatGPT-local route, and thirty checked edges. TypeScript
and Markdown remain provisional; corrected historical/public/active v0.4.0 and
both read-only targets remain unchanged.

The deferred structural disposition is the reversible part of this decision:
a later authorized phase may revisit it with fresh evidence and human
authority, and until then a structural question is identified and routed
rather than judged.
