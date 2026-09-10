# v0.10 SVG Language-Profile Contract

Phase: APG122. Status: implementation candidate pending dispatcher review.
Decision: [ADR 0053](../adr/2026/09/0053-v0-10-discovery-capacity-and-svg.md).

## Purpose and ownership

SVG owns practical general web-graphics language and authoring semantics,
including logos, illustrations, diagrams and reusable visual systems. The
profile does not implement a browser platform, accessibility manual, design
system, parser, sanitizer or optimizer. Project-selected supported subsets
remain distinct from SVG language validity.

CSS cascade belongs to `css-language-profile`; ECMAScript evaluation to
`javascript-language-profile`; static typing to `typescript-language-profile`;
JSX syntax to `jsx-language-profile`; component behavior to
`react-component-profile`. HTML parsing and DOM APIs stay with their host
owner. Future accessibility, Playwright and browser-runtime profiles remain
unimplemented; use project-owned evidence for those boundaries now.

## Source basis and rights

Sources inspected on 2026-09-08. These are factual references; all profile
prose and synthetic graphics are independently authored. No upstream artwork,
code, tests or prose is copied. W3C document-use terms and WHATWG attribution
terms govern their documents, not ownership of the standards' concepts.
APGR original artifacts retain the repository license. Source links below
support each clause; draft status is not proof of browser implementation.

- [W3C SVG 2](https://www.w3.org/TR/SVG2/) remains the Candidate Recommendation
  of 2018-10-04. [SVG 1.1 Second Edition](https://www.w3.org/TR/SVG11/) is the
  historical Recommendation for explicit legacy compatibility decisions.
- [WHATWG HTML SVG integration](https://html.spec.whatwg.org/multipage/embedded-content-other.html#svg-0)
  and [foreign-content parsing](https://html.spec.whatwg.org/multipage/parsing.html#parsing-main-inforeign)
  are living-standard references. Record the target parser and embedding mode.
- [XML 1.0](https://www.w3.org/TR/xml/) and
  [Namespaces in XML](https://www.w3.org/TR/xml-names/) govern standalone XML.
- [CSS Transforms](https://www.w3.org/TR/css-transforms-1/),
  [CSS Masking](https://www.w3.org/TR/css-masking-1/) and
  [Filter Effects](https://www.w3.org/TR/filter-effects-1/) are separate modules;
  their current draft/recommendation-track text does not establish support.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/),
  [WAI image guidance](https://www.w3.org/WAI/tutorials/images/), and
  [complex-image guidance](https://www.w3.org/WAI/tutorials/images/complex/)
  ground the bounded naming and equivalent-information seam.
- [SVG accessibility mappings](https://www.w3.org/TR/svg-aam-1.0/) and
  [Accessible Name 1.2](https://www.w3.org/TR/accname-1.2/) are draft references;
  the latter is a Working Draft dated 2026-08-27, not a Recommendation.
- [W3C document license](https://www.w3.org/copyright/document-license/)
  and [WHATWG copyright](https://whatwg.org/ipr-policy#copyrights) are rights
  references. No copied excerpts require incorporation into the candidate.

Refresh when relevant standards, target browser behavior, embedding modes,
resource policy, accessibility mappings, or a selected optimizer changes;
recheck sources before maturity promotion or release. No mutable URL is an
immutable runtime evidence identity.

## Stable authoring clauses

### SVG-01-DOC-STRUCTURE

For standalone XML, preserve well-formed case-sensitive markup, quoted
attributes and the SVG namespace `http://www.w3.org/2000/svg`. XML declarations
are optional when encoding rules permit; do not impose them on HTML fragments.
Inline HTML SVG enters the SVG namespace through HTML parsing; JSX is another
syntax layer. Prefer SVG2 `href`; retain namespace-bound `xlink:href` only when
an evidenced target needs it. Do not add DTD/entity dependencies casually.
Source: [structure](https://www.w3.org/TR/SVG2/struct.html), XML and HTML above.

### SVG-02-VIEWBOX-SIZING

Distinguish the CSS layout box, SVG viewport, and user coordinates. `viewBox`
is min-x, min-y, width, height; negative dimensions are invalid and zero
suppresses rendering. Positive dimensions are the ordinary visible-artwork
case. `preserveAspectRatio` distinguishes uniform meet/slice alignment from
nonuniform `none`; slice may crop. A viewBox does not by itself establish
responsive CSS sizing, font-relative sizing, clipping or intrinsic dimensions.
Source: [coordinates and sizing](https://www.w3.org/TR/SVG2/coords.html).

### SVG-03-PATHS-GEOMETRY

Check basic-shape dimensions and path command arity, finite numbers, absolute
versus relative coordinates, initial moveto, repeated groups and closepath.
Arc flags and smooth-curve reflection need their specific grammar. Preserve
winding and fill-rule effects; XML parsing does not validate path data. Bound
any local subset parser explicitly and delegate unsupported commands.
Source: [paths](https://www.w3.org/TR/SVG2/paths.html) and
[shapes](https://www.w3.org/TR/SVG2/shapes.html).

### SVG-04-TRANSFORMS-COORDS

Identify the local space and accumulated transform. Matrix multiplication is
order-sensitive: translating then scaling coordinate systems differs from
scaling then translating. Test known points, not just balanced parentheses.
Attribute transforms and CSS transforms have distinct grammar/reference-box
concerns; preserve transform-origin, transform-box and stroke effects.
Source: CSS Transforms and SVG coordinates above.

### SVG-05-PAINT-CURRENTCOLOR

Distinguish fill, stroke, winding, cap/join/dash geometry and group opacity.
`currentColor` uses the element's computed `color`, which can be inherited or
locally overridden. It does not automatically cross an external image
boundary. Presentation attributes participate in the CSS cascade; a CSS
property can override them. Paint order and grouping can alter compositing.
Source: [painting](https://www.w3.org/TR/SVG2/painting.html) and
[rendering model](https://www.w3.org/TR/SVG2/render.html).

### SVG-06-GRADIENTS-PATTERNS

Preserve paint-server IDs and references, stops, spread behavior, units and
transforms. Distinguish objectBoundingBox from userSpaceOnUse; inspect
patternUnits, patternContentUnits and any pattern viewBox independently.
Degenerate bounding boxes require special attention. A matching ID alone does
not prove that the referenced element is a compatible paint server.
Source: [paint servers](https://www.w3.org/TR/SVG2/pservers.html).

### SVG-07-DEFS-SYMBOLS-USE

`g` groups rendered content; defs stores definitions; symbol supplies reusable
content whose viewport can be instantiated by use. Use width/height do not
resize every target kind. Preserve ID uniqueness across combined fragments,
reference targets, shadow-tree/inheritance boundaries and cycle refusal.
Resolve local references before claiming a sprite is usable; external use has
additional host/resource constraints.
Source: [structure and reuse](https://www.w3.org/TR/SVG2/struct.html).

### SVG-08-CLIPPING-MASKING

Clipping controls geometry visibility; masking contributes alpha or luminance.
Do not substitute one for the other. Preserve clipPathUnits, maskUnits,
maskContentUnits, mask-type, region bounds and references. Offscreen extent,
edge antialiasing and compositing still require target rendering evidence.
Source: CSS Masking above.

### SVG-09-TEXT-TYPOGRAPHY

Text/tspan positioning, anchors, baselines, fonts, shaping and language affect
layout. Preserve meaningful text and direction; do not infer glyph metrics
from nominal font size. Text-to-path loses selectability, search and semantic
text unless separately restored, and can incur font/artwork licensing duties.
Source: [text](https://www.w3.org/TR/SVG2/text.html).

### SVG-10-FILTER-EFFECTS

For practical filter authoring, inspect input/result chains, filter/primitive
units, subregions, color interpolation and resource bounds. Blur or shadows
can be clipped by regions and can be costly. An unknown primitive or renderer
must remain unqualified. This is not a complete filter or GPU manual.
Source: Filter Effects above.

### SVG-11-DOM-INTERACTION

Inline SVG and image-embedded SVG have different execution and event contexts.
Recognizing script/event markup does not prove event behavior. Preserve names
and references used by authorized DOM code. Delegate event lifecycle, focus
behavior, animation timing and browser compatibility to project runtime/test
owners; JavaScript syntax alone does not prove DOM behavior.
Source: [interactivity](https://www.w3.org/TR/SVG2/interact.html) and HTML above.

### SVG-12-A11Y-SEMANTICS

Classify meaningful, decorative and interactive graphics by their task use.
For meaningful inline graphics provide an appropriate name, often title and
explicit aria-labelledby; verify referenced IDs and useful text. Description
can use desc/aria-describedby where appropriate. External img alternatives
belong on the embedding image. Complex graphics may need equivalent long-form
information. Decorative graphics should not add redundant names or keyboard
stops. Interactive controls need real roles, keyboard operation and visible
focus; adding tabindex does not supply behavior. ARIA naming markup does not
prove WCAG compliance or an accessibility tree. Contrast duties depend on the
criterion and context, not a universal ratio for every SVG pixel.
Source: WCAG, WAI and SVG accessibility mappings above.

### SVG-13-SECURITY-PROCESSING

State inline, standalone document, image/CSS image, or object/iframe context.
[SVG processing modes](https://www.w3.org/TR/SVG2/conform.html) constrain script,
interaction and external resources differently. Static asset policies can
refuse script, event attributes and external resources without calling all
such SVG universally invalid. Inspect href, paint URLs, styles, fonts, image
resources and foreignObject for the actual trust boundary. No external fetch
is authorized merely by reading a graphic. Lexical patterns are adverse
signals, never a sanitizer or completeness proof.

### SVG-14-SERIALIZATION-OPT

Choose deterministic serialization for the project's actual representation:
stable IDs, escaping, namespaces, numeric precision, ordering and encoding.
Do not reorder rendered children. Comments and whitespace may be significant
to tooling or text; metadata can carry rights. Optimization must preserve
geometry, transform order, CSS/DOM references, accessible meaning and required
metadata. Fewer bytes or repeatable bytes do not prove equivalent rendering.
Use bounded structural negatives and target visual/interaction evidence for
the claim; do not approve an arbitrary optimizer from a fixture comparison.
Source: SVG structure, paths, text and rendering model above; APG evidence policy.

### SVG-15-ROUTING-BOUNDARIES

Select only consequence-bearing SVG decisions. Apply stricter project policy,
classify maintained/generated/legacy/external artifacts, edit generator owners,
and preserve rollback. Use the existing full Green/Yellow/Orange/Red response
labels in the operational leaf. Route adjacent domains explicitly without
implicitly loading profiles. SVG is explicit-only under the existing v1
resolver; language=svg remains an invalid structured request.
Source: APG project ownership and ADR 0053.

## Scenario and proof boundary

The 24-row project-owned scenario register was prepared before leaf authoring.
It covers responsive graphics, sprites, paint/clip/mask composition,
transforms, text/naming, currentColor, adverse resources, malformed inputs,
optimization and owner routing. Parent correction narrows overclaims in the
initial worker draft without changing the 15 clause identities.

Mechanical evidence applies only to the predicates explicitly implemented in
`src/test/support/apg122_svg_contract.py`. Navigation-only rows cannot claim
semantic replay. Unsupported inputs must be explicit; no path subset stands
for the full SVG grammar. The harness provides neither visual pixel
rasterization proof nor accessibility-tree computation proof. Browser and
assistive-technology qualification remain deferred. Source-clause navigation
is independent of semantic fixture assertions and does not replace them.
