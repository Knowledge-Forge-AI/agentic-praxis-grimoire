# CSS Language Profile

Status: Provisionally integrated with known qualification debt under
[ADR 0044](../adr/2026/08/0044-css-language-profile-candidate-and-target-first-harness.md).
APG76 authored the candidate on the Claude branch. APG77 and APG77A through
APG77C hardened and qualified it; APG77D records explicit human acceptance of
four Medium and one Low qualification limitations and closes the ordinary
integration, release, and rollback gates. ADR 0044 is Accepted with amendment.
The current catalog, projection, provisional maturity row, capability route,
project selection, release owner, and integrated test owner are authoritative.
Stable maturity remains blocked by the accepted Medium qualification debt in
the current known-debt register.
Lifecycle: `provisionally-integrated-with-known-debt`.
Lifecycle ADR: `Accepted with amendment`.

This specification is the normative detail behind
[`skills/css-language-profile/SKILL.md`](../../skills/css-language-profile/SKILL.md).
Stable clause markers (`<!-- APG-CLAUSE: CSS-* -->`) are navigation anchors
for
[the scenario coverage record](css-language-profile-scenario-coverage.md).
They are not an exact-action map: no clause encodes a required action list,
and no scenario carries an expected outcome.

## Scope and ownership

The profile owns exactly one thing: **CSS-specific static semantics and
cascade or value consequences for an established CSS region, under the
question-specific normative authority and the consequence-bearing artifact,
tool, configuration, cascade, document, and environment evidence.**

It does not own all of CSS. Where a decision depends on a document, a
browser, a build, an appearance, or a product policy, the profile routes and
stops rather than deciding.

### Explicit non-owners

HTML and DOM structure; actual selector matching without exact document and
state evidence; accessibility; visual design approval; pixel-level rendering;
browser bugs; browser support policy; cross-browser compatibility decisions;
host component semantics; JavaScript, TypeScript, JSX, and MDX behavior;
runtime user interaction; asset and font correctness; network loading; build
completion; build-time CSS transformation unless that exact role is separately
evidenced; preprocessor and CSS-in-JS semantics; design-token naming policy;
theme product policy; security approval; performance approval; and deployment.

Each simultaneous non-CSS decision routes to its exact owner. Several distinct
obligations never collapse into one generic "other owner."

## Decision axes

### Selection

<!-- APG-CLAUSE: CSS-SELECTION -->
Selection is decision-scoped, never whole-file, and takes exactly one of four
values:

- `selected` — the decision is CSS-owned and this profile answers it;
- `embedded-route` — a bounded CSS region inside a host artifact is analyzed
  while the host owner keeps whole-file control;
- `route-to-owner` — the decision belongs to a named non-CSS owner;
- `non-trigger` — the question is not a CSS decision at all.

Selection follows from the decision as well as the artifact class and
whole-file owner. Authored whole-file CSS admits `selected`; a host-embedded
`<style>` region admits `embedded-route` at most. Exact generated, build-output,
minified, or vendor CSS bytes admit `selected` for a read-only CSS semantic
decision while edit, regeneration, and provenance decisions remain routed.
A source map is metadata rather than CSS semantic input. An unclassified
artifact admits neither `selected` nor `embedded-route` until it is classified.

Selection never implies a response, and a response never implies a selection.
The two vocabularies are disjoint: no selection value is a response value and
no response value is a selection value.

### Response

<!-- APG-CLAUSE: CSS-RESPONSE -->
The response axis has exactly four values and no others:

- `proceed-routine` — the question is established, the inputs are complete,
  and an ordinary answer follows;
- `inspect-before-judgment` — a consequence-bearing input is unread but
  obtainable; read it before concluding;
- `bounded-local-decision` — the answer holds only for the inputs actually
  bound, and the bound scope is stated with the answer;
- `stop-and-escalate` — a required input is missing or contested and no
  sound answer is available.

Use the highest justified response for the one coherent current decision. Do
not split one decision across two responses, and do not average two decisions
into one.

### Routes and obligations

<!-- APG-CLAUSE: CSS-ROUTES -->
When several decisions are live at once, emit a small ordered set with one
item per distinct decision, each naming its exact owner: `DOM-owner`,
`host-owner`, `project-configuration`, `project-design-owner`,
`browser-compatibility-owner`, `build-transform-owner`,
`generated-artifact-owner`, `visual-validation-owner`,
`accessibility-owner`, `runtime-owner`, `asset-owner`, `font-owner`,
`network-owner`, `security-owner`, `performance-owner`, or `deployment-owner`.

Routing is orthogonal to severity. Routing a decision away never lowers the
response on the CSS decision that remains, and a routed stop remains stopped
until the receiving owner resolves it. An obligation set that merges two
materially distinct decisions into one item is a defect, not a
simplification.

## Source binding

<!-- APG-CLAUSE: CSS-SOURCE-MODULES -->
CSS is modular and its modules advance independently. Bind the exact module
and level that governs the question, together with its publication status and
date, before asserting a version-dependent result. "CSS says" is not a
binding.

The normative module is selected by the construct and claim. A project usually
selects tools, browser policy, and feature targets; it does not configure a W3C
module as though that module were a compiler flag. Project evidence may select
the implementation question, but it cannot replace the specification authority
that defines the construct. Version-sensitive target behavior requires both
the exact normative source and exact implementation evidence.

Tool role state is decision-scoped. Record parser, transformer, and browser as
`known`, `not-selected`, `not-required`, or `unresolved` for the conclusion at
hand. A documented framework-selected pipeline establishes selection even when
the implementation package is transitive; package presence alone does not.
Selection, configuration, actual invocation, emitted output, and rendering are
five separate facts.

Distinguish four source kinds and never substitute one for another. Normative
specification text is the only source for what a construct means. Repository
source is the mutable editor's draft, possibly ahead of any published
snapshot; cite an exact commit when citing it at all. Browser documentation
explains and never settles a normative question. Compatibility data and
implementation tests bear on support, never on meaning, and belong to the
browser-compatibility owner.

A published status is a fact about the document, not about implementations. A
Candidate Recommendation is not a guarantee of support, and a Working Draft is
not evidence of absence. When a module's exact level cannot be bound and the
result depends on it, the response is `stop-and-escalate`.

## Syntax and selectors

### Grammar validity

<!-- APG-CLAUSE: CSS-SYNTAX -->
CSS parsing is error-tolerant by design, and the unit of recovery matters.
Within a declaration block, a declaration whose value does not match its
property grammar is dropped and the surrounding declarations survive. A
malformed selector invalidates its whole style rule, so the rule's entire
declaration block is discarded. An unrecognized at-rule is consumed and
discarded along with its block.

Therefore a "syntax error" has no single consequence: the exact recovery
boundary — declaration, rule, or at-rule — is part of the answer, and stating
one without the other is incomplete. An unknown property name and an
unsupported value on a known property both drop only their own declaration,
but they are different findings and route differently: the first is usually
an authoring defect, the second is usually a compatibility question.

### Selector list validity

<!-- APG-CLAUSE: CSS-SELECTORS -->
An invalid compound or complex selector normally invalidates the entire
selector list, and with it the whole style rule. Forgiving selector lists are
the deliberate exception: `:is()` and `:where()` accept a forgiving selector
list, so an unrecognized argument is discarded while the remaining arguments
and the enclosing rule survive.

`:not()` and `:has()` are not forgiving. `:has()` takes a relative selector
list, so an invalid argument invalidates the `:has()` and therefore the rule.
`:has()` may not be nested inside `:has()`, and pseudo-elements are not valid
inside `:has()` unless a specification explicitly allows one.

The consequence is asymmetric and must not be generalized: wrapping an
uncertain selector in `:is()` changes both its failure mode and its
specificity, and those are two separate findings.

### Specificity

<!-- APG-CLAUSE: CSS-SPECIFICITY -->
Specificity is the ordered triple (A, B, C): A counts ID selectors, B counts
class selectors, attribute selectors, and pseudo-classes, and C counts type
selectors and pseudo-elements. Triples compare lexicographically; no number
of class selectors reaches one ID selector.

The functional pseudo-classes are the recurring source of error:

- `:is()` takes the specificity of its most specific argument;
- `:not()` takes the specificity of the most specific selector in its
  argument — the negation itself adds nothing, but its argument counts;
- `:has()` likewise takes the specificity of its most specific argument;
- `:where()` contributes zero, and neither it nor any of its arguments
  contribute anything.

`:where()` is therefore a specificity decision, not a formatting choice: it
is how an author makes a declaration easy to override. Treating `:is()` or
`:not()` as specificity-free is a defect; so is treating `:where()` as merely
cosmetic.

Specificity is computed from the selector as written. It never depends on
which elements exist, so it is answerable statically. What the selector
*matches* is not.

## Cascade and inheritance

### Cascade sorting order

<!-- APG-CLAUSE: CSS-CASCADE-ORDER -->
Declarations are sorted by these criteria in descending priority: origin and
importance; encapsulation context; element-attached styles; cascade layers;
specificity; and order of appearance. Each criterion is consulted only when
every earlier one ties.

Within origin and importance, the descending precedence is: transition
declarations; important user-agent declarations; important user declarations;
important author declarations; animation declarations; normal author
declarations; normal user declarations; normal user-agent declarations.

Two consequences follow directly and are commonly missed. First,
`!important` does not simply "win": it moves a declaration into a different
origin band whose internal ordering is reversed relative to the normal band.
Second, specificity is consulted only after origin, context,
element-attached, and layer have tied, so a specificity comparison across
different layers or origins is meaningless.

A conclusion about which declaration wins is sound globally only when every
consequence-bearing declaration is bound. A winner within an explicitly bounded declaration set
is valid when the set is named and the result is not
promoted to a global computed winner. Unknown participating declarations make
the global answer `inspect-before-judgment` or `stop-and-escalate`.

### Cascade layers

<!-- APG-CLAUSE: CSS-LAYERS -->
Declarations not assigned to an explicit layer are placed in an implicit
final layer. Layers are ordered by first appearance of their name.

For normal declarations the declaration in the **last** layer wins, so
unlayered normal declarations beat every explicit layer. For important
declarations the order reverses and the declaration in the **first** layer
wins, so unlayered important declarations are the weakest important
declarations in their origin. This mirrors how importance reverses origin
order, and it is why adding a layer around existing styles can change
outcomes in both directions at once.

Layer order is established by declaration order across the whole stylesheet
graph, including layers named by `@import`. A conclusion about layer
precedence therefore requires the entry-point ordering, not only the file in
which a declaration appears.

### Inheritance and CSS-wide keywords

<!-- APG-CLAUSE: CSS-INHERITANCE -->
Whether a property inherits is a per-property fact defined by its own module;
it is never inferred from a name or from a sibling property. When no
declaration wins for an element, an inherited property takes the parent's
computed value and a non-inherited property takes its initial value.

The CSS-wide keywords are `initial`, `inherit`, `unset`, `revert`, and
`revert-layer`, and they are not interchangeable:

- `initial` sets the property's initial value regardless of inheritance;
- `inherit` sets the parent's computed value regardless of inheritance;
- `unset` acts as `inherit` for inherited properties and `initial` for
  non-inherited ones;
- `revert` rolls back to the value the previous cascade origin would have
  produced;
- `revert-layer` rolls back to the value the previous cascade layer would
  have produced.

`revert` and `revert-layer` are cascade operations, not value keywords: their
result depends on declarations elsewhere and cannot be answered from one
declaration alone.

### Shorthands and longhands

<!-- APG-CLAUSE: CSS-SHORTHANDS -->
A shorthand declaration sets every longhand in its family. Unless the
shorthand's own definition says otherwise, longhands the author did not
mention are assigned their initial values — they are not left untouched. This
is the standard cause of an "unexplained" lost value: an earlier longhand is
silently reset by a later shorthand that appeared to be about something else.

Two qualifications keep the rule from being over-read. Some shorthands define
their own omission behavior or reach reset-only sub-properties, so "initial
value" is the default rather than a universal; and the `all` shorthand, which
resets every property, still excludes the writing-direction properties and
does not touch custom properties.

Answering a shorthand question therefore requires the exact longhand family of
that shorthand under the exact module that defines it, and the relative order
of the shorthand and every affected longhand. Membership in that family is a
fact to check, not to infer from a shared name prefix: a property may share a
prefix with a shorthand and still belong to a different family — see the
logical-property rule below. A shorthand that cannot represent a value cannot
set it, which is a separate finding from resetting it.

### Logical and physical properties

<!-- APG-CLAUSE: CSS-LOGICAL -->
A flow-relative property and its physical counterpart form a logical property
group. They are distinct properties with distinct specified values, but the
members of a pair share one computed value, determined by cascading both
declarations together as one — by declaration order, and by the element's own
`writing-mode`, `direction`, and `text-orientation`.

Two errors follow from ignoring that structure. First, a flow-relative
property is **not** a longhand of the physical shorthand whose name it
resembles: a four-directional physical shorthand expands to physical longhands
only, and reaches flow-relative ones solely through an explicit opt-in
keyword. Treating a same-prefixed shorthand as resetting a flow-relative
property is a shorthand-family error, not a cascade result. Second, no
logical/physical interaction is answerable without the element's writing mode,
direction, and text orientation — environment facts this profile does not own.
Where they are unbound the mapping is required evidence and the dependent
claim is `stop-and-escalate`, even when both declarations sit in one file.

## Custom properties and values

### Custom-property definition and substitution

<!-- APG-CLAUSE: CSS-CUSTOM-PROPERTIES -->
Custom properties inherit by default and their values are nearly
unconstrained token sequences. A custom property is validated only where it
is substituted, so an incorrect value produces no error at its definition and
surfaces only at the referencing declaration — often in a different file.

Substitution happens at computed-value time, which means the result depends
on the element: the same `var()` reference on two elements can resolve to
different values through inheritance. A claim about a substituted value is
scoped to the element whose custom-property environment was bound.

### Fallback, cycles, and invalid at computed-value time

<!-- APG-CLAUSE: CSS-SUBSTITUTION -->
`var(--name, fallback)` uses the fallback when the referenced custom property
has the guaranteed-invalid value. Everything after the first comma is the
fallback, including further commas, so a fallback may itself be a
comma-containing value.

An empty custom-property value is valid, not absent: `var()` on it
substitutes nothing, which typically leaves the surrounding declaration
malformed. That is a different failure from an undefined property, and only
the undefined case triggers the fallback.

A declaration is **invalid at computed-value time** when it contains a
`var()` referencing a guaranteed-invalid custom property with no valid
fallback, or when the value is invalid after substitution. The consequence is
not that the declaration is dropped and an earlier declaration wins. Instead
the computed value becomes:

- the guaranteed-invalid value, for a non-registered custom property or a
  registered custom property with universal syntax; or
- otherwise the property's inherited value if it inherits, and its initial
  value if it does not — the behavior of `unset`.

Reading this as ordinary invalid-declaration handling produces the wrong
answer whenever an earlier declaration exists, so it must be stated
explicitly whenever a `var()` result is reported.

A custom property that references itself directly or through a chain of other
custom properties forms a cycle. Every member is invalid at computed-value
time; an unregistered property or a registered property with universal syntax
takes the guaranteed-invalid value, while a typed registered property follows
its registered computation and initial-value rules. Detecting a cycle therefore
requires the whole referencing chain and relevant registration evidence, not
one declaration.

### Values, units, and math functions

<!-- APG-CLAUSE: CSS-VALUES-UNITS -->
A unit is only meaningful against the reference its property defines, and
"font-relative" is not one reference but several. Local font-relative units
(`em` and its family) resolve against the element's own font metrics — for
`em`, its computed `font-size`, except on `font-size` itself where the
parent's is used. Root font-relative units (`rem` and its family) resolve
against the **root element's** font metrics regardless of where they appear,
so the `font-size` exception does not apply to them. Units keyed to other
metrics — x-height, cap-height, advance measure, line-height — resolve against
those metrics, not against `font-size`. Percentages resolve against a
property-specific reference, often a used value static analysis cannot supply,
and viewport-relative units resolve against an environment this profile does
not own.

`calc()`, `min()`, `max()`, and `clamp()` may mix units and resolve at
computed-value time or later. Division by zero is level-dependent and must not
be answered without binding the level: under Values and Units 4 it is not a
parse error — division by zero yields signed infinity and zero over zero
yields NaN, with infinities clamped to the context's range and NaN censored to
zero at the top level — while an earlier level made it invalid at parse time.
Asserting either answer without the bound level is the source-binding defect
this profile forbids.

An expression reduces statically only when every operand's reference is bound.
A percentage, viewport, or root font-relative operand with no reference in
evidence leaves the expression unresolved; name the unresolved reference as
required evidence rather than guessing a viewport, containing block, or root.

### Color

<!-- APG-CLAUSE: CSS-COLOR -->
Color values are answerable statically only within the color module actually
selected. `currentColor` computes to the keyword itself and resolves at
used-value time against the element's own `color`, which is why it survives
inheritance as a keyword and re-resolves on each descendant rather than
freezing to the ancestor's literal. Resolving it therefore needs the cascade
result for `color` on the element carrying the reference, not on the rule
where it is written, and any conclusion about it is a used-value claim bounded
accordingly. Functions such as `color-mix()` and the perceptual color spaces
are defined by specific color-module levels; citing a level that does not
define the function used is a source-binding defect.

Whether a color function is *supported* is a compatibility question owned by
the browser-compatibility owner. This profile answers what a color value
means, and routes whether it renders.

## Conditions, nesting, and pseudo-selectors

### Conditional rules

<!-- APG-CLAUSE: CSS-CONDITIONS -->
A conditional at-rule is a static structure with a runtime-evaluated
condition. The nesting and syntax of the rule are statically answerable; the
truth of the condition usually is not.

A media query evaluates against an environment — viewport dimensions, user
preferences, and device characteristics — that this profile does not own.
Without the exact environment value, the containing declarations' effect is
unknown, and asserting a winner is `stop-and-escalate`.

An unknown media feature name or value does not invalidate the stylesheet and
does not simply evaluate false. It produces the value `unknown`, and a media
query whose value is `unknown` is replaced by `not all`. Two consequences
follow that a plain "evaluates false" reading gets wrong: negating the query
does not flip it true, because the whole query — negation included — has
already been replaced; and recovery is per-query within a comma-separated
list, so sibling queries survive. The practical finding stands either way: an
author's typo degrades silently.

A supports query tests whether the processor **accepts** a declaration inside
a style rule, which is stronger than parsing it. A conforming processor must
not accept a declaration whose property and value it does not implement with a
usable level of support, so a true result is a support claim rather than a
bare parse result. It is still not proof of correct behavior, layout, or
appearance. Evaluating it requires the exact user agent, so without that
evidence the condition's truth is required evidence, not an assumption.

### Nesting

<!-- APG-CLAUSE: CSS-NESTING -->
A nested style rule is resolved against its parent rule's selector list. Where
the nested selector does not contain the nesting selector `&`, one is implied.
Because the parent selector list is treated as a single `:is()`-like unit, a
nested rule's specificity includes the specificity of the *most specific*
selector in the parent list — not the one the author had in mind.

Three consequences matter. First, adding a selector to a parent list can raise
the specificity of every rule nested inside it, at a distance and without any
edit to the nested rule. Second, nesting is a source-level construct: the
resolved selector, not the nested text, is what participates in the cascade,
so a nesting question is answered by resolving the selector first. Third,
order of appearance follows the resolved structure: a nested rule counts as
coming after its parent rule, and declarations written after a nested rule are
themselves treated as a later nested unit rather than reverting to the
parent's position. A source-order tie inside a nested block is therefore not
read off the raw line numbers.

Whether nesting is available at all is a source-level and compatibility
question, and it routes to the project-configuration and
browser-compatibility owners.

### Pseudo-classes and pseudo-elements

<!-- APG-CLAUSE: CSS-PSEUDO -->
A pseudo-class selects on state or structure. Its specificity contribution
and validity are static, but whether it matches depends on the document and,
for interaction states, on runtime. A claim that a state rule applies is a
DOM-owner or runtime-owner claim; a claim about what the rule would compute
if it applied is CSS-owned. Keep them separate and route the first.

A pseudo-element addresses a sub-part of an element rather than a state.
`::before` and `::after` generate a box only when `content` computes to
something other than `none`, so a declaration on them can be entirely inert
for reasons unrelated to the cascade. Pseudo-elements contribute to the C
component of specificity, and constraints on where they may appear —
including inside `:has()` — are selector-level facts, not stylistic
preferences.

## Ownership boundaries

### Host-embedded style regions

<!-- APG-CLAUSE: CSS-HOST-EMBEDDED -->
A `<style>` region inside a host component file is a bounded CSS region under
a host owner. Selection is `embedded-route` at most; the host owner controls
the file, the extraction, and whether the region is scoped or global.

Scoping is a host transformation, not a CSS-level fact. When a host applies
scoping, the selectors that reach the cascade are not the selectors as
written, and their specificity may differ. Any conclusion about how an
embedded region interacts with whole-file stylesheets therefore requires the
host's exact scoping behavior as evidence, and without it the answer is
bounded to the region itself.

An inline style attribute contains CSS declarations at author origin and is
element-attached, after style sheets in the author-origin order. It is owned by
whoever owns the markup; its bounded CSS semantics use `embedded-route` without
transferring whole-file ownership.

A recognized SVG presentation attribute maps to its corresponding CSS property
at author origin with specificity zero. Its value grammar does not admit an
`!important` declaration. The SVG owner retains the file, while a material
bounded CSS semantic decision uses `embedded-route`. Arbitrary SVG attributes
are not thereby CSS.

### Provenance

<!-- APG-CLAUSE: CSS-PROVENANCE -->
Authored, generated, vendor, and minified CSS are distinct artifact classes
with distinct permissions. A read-only CSS semantic decision may inspect exact
bytes from any of those classes. That diagnosis does not grant edit permission:
generated CSS, build output, and minified CSS are regenerated from their
sources under an evidenced build-transform role and are never hand-edited; a
source map is build metadata and never a semantic source of truth. Vendor CSS
is third-party input.

Provenance is established from evidence, not from a filename, a directory
name, or a header comment — those are hints that raise the question. A file
whose provenance is unresolved blocks direct edits and regeneration claims
until an owner resolves it, and any reported consequence for such a file is a
`bounded-local-decision` at best.

### Static, transform, render, and runtime

<!-- APG-CLAUSE: CSS-STATIC-RENDER -->
Four layers stay distinct: static CSS semantics; build-time parsing and
transformation; browser cascade, layout, and paint; and runtime interaction.

A parser pass proves that exact parser's result on those exact bytes. A
transform pass proves that exact transform's output. A computed cascade
conclusion requires every consequence-bearing cascade input. A screenshot is
one rendered observation under one environment and one document state.

None of these proves browser support, correct DOM matching, layout
correctness, visual acceptance, interaction correctness, or deployment. A
report that lets a static or transformed result stand for a rendered one is a
defect regardless of how the result was obtained.

Animation declarations, transitions, keyframes, and vendor-prefixed
declarations remain within the narrow initial owner only for static grammar,
cascade participation, and reference inspection. Animation and transition
timing or runtime effects route to the browser-compatibility and runtime
owners. Prefix support and necessity route to browser compatibility. Source
bytes alone never prove that motion or a prefixed declaration takes effect.

## Structural policy

<!-- APG-CLAUSE: CSS-STRUCTURE-DEFERRED -->
Structural policy for stylesheets is **deferred**. This is a positive
decision, not an omission: no numeric whole-file band, no percentile-derived
threshold, and no universal stylesheet-size rule is authorized, and line
count is descriptive only. No refactor, preprocessor conversion, token
extraction, or migration is automatic.

The profile may record qualitative signals when they are visible in bound
evidence: cross-file cascade dependency, layer-order dependency, specificity
escalation, custom-property dependency spread, shorthand overwrite risk,
authored/generated boundary confusion, and host or global-scope leakage. A
recorded signal routes review to the project-design owner. It never
determines failure by itself, never becomes a required bookkeeping action on
a counted decision, and never accumulates into a growth-state obligation.

APG77 may revisit this disposition with fresh evidence and human authority.
Until then, a structural question is identified and routed, not judged.
