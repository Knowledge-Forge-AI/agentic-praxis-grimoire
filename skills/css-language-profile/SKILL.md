---
name: css-language-profile
description: Use when a material decision depends on CSS-specific static semantics — syntax validity, selector specificity, cascade ordering, inheritance, shorthand resets, custom-property substitution, or value consequences — for an established CSS region whose artifact boundary and consequence-bearing evidence are identified.
---

# CSS Language Profile

Normative detail:
[CSS Language Profile](../../docs/specs/css-language-profile.md).
Status: Provisionally integrated with known qualification debt under ADR 0044,
Accepted with amendment in APG77D. APG76 authored the candidate; APG77 through
APG77C hardened and qualified it. Stable maturity remains blocked by the four
accepted Medium items in the current known-debt register.
Lifecycle: `provisionally-integrated-with-known-debt`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

<!-- APG-CLAUSE: CSS-TRIGGER -->
Apply CSS-specific judgment only when a current, consequence-bearing decision
materially depends on CSS syntax, selector semantics, cascade ordering, or
value computation inside an established CSS region. The normative module is
selected by the construct and claim, not by pretending that a project configures
a specification level. Bind only the artifact, tool, environment, and cascade
evidence that the current conclusion actually depends on. Answer the one coherent current
decision at the highest justified `proceed-routine`,
`inspect-before-judgment`, `bounded-local-decision`, or `stop-and-escalate`
response.

Keep three axes separate for every decision: selection (`selected`,
`embedded-route`, `route-to-owner`, or `non-trigger`), response (the four
values above), and a small ordered set of routes or obligations, one per
simultaneous non-CSS decision. Selection is decision-scoped and never
transfers whole-file ownership: a host component's embedded `<style>` region
uses `embedded-route` while the host owner stays controlling. Routing never
lowers the response, and a routed stop stays stopped until its owner resolves
it.

CSS is modular. Bind the exact module and level that governs the question;
never cite "CSS" as one undifferentiated authority, and never assume a
feature is available, selected, or supported because it is specified.

## Do not use

<!-- APG-CLAUSE: CSS-NONTRIGGER -->
Do not use this profile for:

- HTML or DOM structure, actual element matching without exact document and
  state evidence, or any claim about what a selector matches at runtime;
- accessibility, visual design approval, pixel-level rendering, layout
  correctness, or performance and security approval;
- browser bugs, browser support policy, or any cross-browser compatibility
  decision;
- Astro, Starlight, or other host component semantics, and JavaScript,
  TypeScript, JSX, or MDX behavior;
- PostCSS, Vite, Lightning CSS, esbuild, or any other build-time
  transformation unless that exact role is separately evidenced, and never
  for Sass, Less, Stylus, or CSS-in-JS semantics;
- design-token naming policy, theme product policy, asset and font
  correctness, network loading, build completion, or deployment; or
- selecting the CSS source level, parser, transformer, browser targets, or
  project configuration — those are consumed facts owned by the project.

A non-trigger is a routine handoff that names the receiving owner exactly. It
is not a CSS decision, and it never becomes one by being adjacent to CSS.

## Required evidence intake

<!-- APG-CLAUSE: CSS-EVIDENCE -->
Before any CSS-owned conclusion, bind from evidence — and keep present
evidence strictly separate from evidence still required:

- the artifact class (authored whole-file CSS, host-embedded `<style>`
  region, inline style declaration, CSS module, generated CSS, build output,
  vendor CSS, minified CSS, source map, preprocessor source, design-token
  source, documentation sample, fixture, or unknown);
- the whole-file owner and this profile's selection state for the one
  decision at hand;
- the exact CSS source modules and levels that govern the question, each with
  its publication status and date;
- every consequence-bearing tool role independently and per decision — parser, transformer,
  and browser — each as `known`, `not-selected`, `not-required`, or
  `unresolved`, with exact package, exact version, selection source, and
  invocation evidence when `known`. Role state is decision-scoped: evidence
  required only for a routed render claim does not block an independent static
  conclusion. Package or lockfile presence never proves a role runs, a
  configuration option is not an invocation, and one role's evidence never
  satisfies another. A documented framework-selected pipeline is selection
  evidence even when its implementation package is transitive; actual
  invocation and emitted output remain separate facts;
- every cascade input the result depends on under the bound level: origin,
  importance, layer order, specificity, and source order across all
  participating stylesheets;
- the custom-property definitions, environment values, and document state the
  computation reads.

An option or feature name without its exact value is not a fact. When a
required input is missing, name it as required evidence rather than assuming
a default.

## Procedure

1. Classify the artifact, identify the whole-file owner, and set the
   selection state for this one decision.
2. Complete the evidence intake above and list what is present and what is
   still required.
3. Analyze only CSS-owned static semantics for the established region,
   including a read-only CSS semantic decision over exact generated, vendor,
   or minified bytes when provenance and ownership are recorded:
   grammar validity under the selected level, selector-list validity and
   forgiving-selector boundaries, specificity including `:is()`, `:not()`,
   `:has()`, and `:where()`, origin/importance/layer/specificity/source-order
   ordering, inheritance and CSS-wide keywords, shorthand resets of their
   longhands, custom-property inheritance and substitution, `var()` fallback,
   cycles and invalid-at-computed-value-time results, exact units and math
   functions, and target-selected color, condition, nesting, logical-property,
   and pseudo-element consequences.
4. Route every simultaneous adjacent decision as one item in a small ordered
   set while leaving the CSS response unchanged: document shape and matching
   to the DOM owner, host files and extraction to the host owner, source
   level and tool selection to the project-configuration owner, feature
   availability to the browser-compatibility owner, build transformation to
   the build-transform owner, regeneration to the generated-artifact owner,
   appearance to the visual-validation owner, and interaction to the runtime
   owner.
5. Stop rather than infer when an artifact class, source module, tool role,
   cascade input, environment value, or document state is missing.
6. Separate static, transform, render, and runtime results in every report,
   and preserve authored, generated, and vendor provenance.

## Static and rendered boundary

A conclusion drawn from source bytes proves only static CSS semantics for the
inputs actually bound. A parser pass proves only that exact parser's result;
a transform pass proves only that exact transform's output; neither proves
browser support, correct matching, layout, visual acceptance, interaction, or
deployment. A screenshot is one rendered observation under one environment,
not general semantic correctness. Never present any of these as another.

## Cascade completeness

A computed cascade conclusion is only as sound as its inputs. When a
declaration can be reached from more than one stylesheet, layer, or origin,
either bind every participating declaration or record a winner within an
explicitly bounded declaration set. Never promote that bounded result to a
global computed winner when consequence-bearing declarations are unknown;
that is `inspect-before-judgment`, and `stop-and-escalate` when a global result
would otherwise be asserted.

## Provenance

Authored CSS may be edited under this profile once its owner and permission are
bound. A read-only CSS semantic decision over generated, vendor, build-output,
or minified bytes may still be selected when exact bytes and the governing
normative authority are known. That diagnosis does not grant edit permission:
generated and minified CSS are regenerated under an evidenced build-transform
role, vendor CSS remains third-party input, and provenance owners decide every
change. Unknown provenance blocks edits and regeneration claims, not a safely
bounded read-only observation.

An inline style attribute contains CSS declarations at author origin attached
to its element, while the markup owner keeps the file. A recognized SVG
presentation attribute contributes the corresponding CSS property at author
origin with specificity zero and without `!important` declaration grammar,
while the SVG owner keeps the file. Use `embedded-route` for either bounded CSS
decision; do not generalize this rule to arbitrary SVG attributes.

Animation and transition timing or runtime effects route to the runtime and
browser-compatibility owners. This profile may inspect their static grammar,
cascade participation, and referenced keyframes when the governing module is
bound, but it does not claim that motion runs or renders.

## Structural policy

Structural policy for stylesheets is deferred. Line count is descriptive
only, numeric whole-file bands are forbidden, and no stylesheet refactor,
preprocessor conversion, token extraction, or migration is automatic. This
profile may record qualitative signals — cross-file cascade dependency,
layer-order dependency, specificity escalation, custom-property dependency
spread, shorthand overwrite risk, authored/generated boundary confusion, and
host or global-scope leakage — as review-routing observations. Such a signal
routes review to the project-design owner; it never decides failure and never
becomes an obligation to restructure.

## Project-owned parameters

The repository and project own: the CSS source modules and levels in scope;
parser, transformer, and formatter selection and configuration; browser
support policy and compatibility targets; host and build tooling; layer
architecture and naming; design tokens and theme policy; artifact
classification and generated-output paths; structural and migration policy;
accepted exceptions; and any stricter repository policy, which always
controls.

## Stop or escalate

<!-- APG-CLAUSE: CSS-UNKNOWN-STOP -->
Apply these responses exactly:

- missing artifact class or whole-file owner: `inspect-before-judgment`;
- missing exact source module or level for a version-dependent result:
  `stop-and-escalate`;
- unresolved parser, transformer, or browser role where the result depends on
  it: `stop-and-escalate`;
- incomplete cascade inputs: `inspect-before-judgment`, or
  `stop-and-escalate` when a winner would otherwise be asserted;
- unknown environment value, writing mode, root font-size, or document state:
  `stop-and-escalate` for the dependent claim only;
- unknown provenance: stop before any direct edit or regeneration claim;
- static or transform success offered as render or runtime proof:
  `stop-and-escalate`;
- DOM, browser, visual, build, or product-policy question: set selection to
  `route-to-owner` and keep the response at whatever the remaining CSS
  decision justifies — routing is not a response and never replaces one;
- established CSS static question with complete inputs: `proceed-routine`.

## Evidence and completion

Before a material repair, record what rollback needs: the exact prior
declaration or region bytes, the prior cascade inputs the conclusion rested
on, the artifact class and provenance, and the configuration evidence. Report
the selection state, the response, the evidence bindings, each exact route,
and the rollback boundary. Never claim completion while required evidence is
missing, while a routed stop is unresolved, or in terms that let a static
result stand in for a rendered one.

## Common mistakes

- Citing "CSS" as one authority instead of the exact module and level.
- Treating a package in a manifest or lockfile as proof that a parser or
  transformer runs.
- Declaring a cascade winner from one stylesheet when the participating
  declarations are unknown.
- Reading `:where()` as merely cosmetic, or treating `:is()` and `:not()` as
  specificity-free.
- Assuming a shorthand leaves unmentioned longhands untouched.
- Treating an unresolved `var()` as an ordinary invalid declaration.
- Claiming a media, supports, writing-mode, or root-font-size dependent result
  without the exact environment value.
- Taking whole-file ownership of a host component because it contains a
  `<style>` region.
- Hand-editing generated, minified, or vendor CSS, or editing a file whose
  provenance is unknown.
- Presenting a clean parse, a successful transform, or one screenshot as
  proof of correct rendering.
- Making structural, migration, or design-token policy judgments under CSS
  authority.
