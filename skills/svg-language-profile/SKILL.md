---
name: svg-language-profile
description: Use when SVG authoring depends on namespaces, viewBox, paths, transforms, paint, reuse, clipping, masking, text, naming, resources, or serialization; not for general CSS, JSX, React, browser runtime, accessibility audits, or test automation.
---

# SVG Language Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.

## Core principle

Make the graphics-authoring decision against the selected SVG representation,
embedding context and target. SVG is a general vector and mixed-graphics
surface for illustrations, diagrams, branding systems, icons and logos.
Separate language validity, a project's supported subset, deterministic output,
and actual rendering. None proves the others.

Use the highest justified `Green — routine`, `Yellow — caution`,
`Orange — warning`, or `Red — crisis / stop` response for the current decision.
Repository policy and the task's authority control.

## Do not use

Do not select SVG merely because a file contains an icon. Pure CSS cascade
belongs to `css-language-profile`, ECMAScript semantics to
`javascript-language-profile`, static types to `typescript-language-profile`,
JSX syntax to `jsx-language-profile`, and React state/rendering to
`react-component-profile`. Astro and MDX keep their document/framework seams.
HTML parsing, DOM lifecycle, browser compatibility, accessibility audits,
Playwright automation, Vite and package management require their own project
owners. Future profiles for these subjects are not assumed installed.

A non-trigger is a route to its owner, not a Green SVG decision. Broader visual
design, brand strategy and typography selection are product decisions.

## Procedure

1. Identify the task, project rules, target renderer/browser, SVG version or
   supported subset, embedding mode, trust/resource policy and rollback.
2. Classify maintained source, generated output, legacy content, external input
   or embedded fragment. Edit the generator when it owns the artifact; do not
   normalize legacy graphics without a consequence-bearing reason.
3. State the exact SVG decision. Route adjacent language, component, runtime
   and accessibility questions separately without implicitly selecting owners.
4. Inspect the relevant clauses below. Preserve required appearance, references,
   accessible meaning and metadata; classify unsupported features explicitly.
5. Choose proportional evidence: parser/subset checks for structure, known-point
   calculations for geometry, repeated serialization for determinism, and real
   target rendering/interaction evidence when those are the claims.
6. Report the response level, decision, checks, remaining routes and rollback.
   A successful XML parse or byte comparison never closes browser evidence.

### Document and coordinate structure

**SVG-01-DOC-STRUCTURE.** Standalone SVG uses case-sensitive XML and the SVG
namespace `http://www.w3.org/2000/svg`. Preserve quoted attributes, escaping
and namespace bindings. An XML declaration is optional where encoding rules
permit. Inline HTML SVG follows HTML foreign-content parsing; JSX is another
syntax layer and does not use XML attribute spelling universally. Prefer
modern `href`; use namespace-bound `xlink:href` only for an evidenced legacy
target. Avoid introducing DTD/entity dependencies.

**SVG-02-VIEWBOX-SIZING.** Distinguish CSS layout size, SVG viewport and user
coordinates. `viewBox` is min-x, min-y, width, height. Negative dimensions are
invalid; zero dimensions suppress rendering. For visible artwork, use the
intended positive extent. `preserveAspectRatio` meet fits uniformly, slice
fills and can crop, and none stretches nonuniformly. Verify actual CSS sizing,
intrinsic dimensions and overflow; viewBox alone does not prove responsiveness.
Use explicit `1em` sizing when font-relative icons are intended rather than
assuming omitted dimensions imply it.

**SVG-03-PATHS-GEOMETRY.** Check shape dimensions and path data independently
of XML syntax. Preserve initial moveto, command parameter counts, absolute
versus relative coordinates, repeated groups, closepath, arc flags and smooth
control-point reflection. Numeric parsing must reject malformed/nonfinite
values. Winding and fill-rule can change the interior. A bounded path checker
must report unsupported commands instead of declaring the whole path valid.

**SVG-04-TRANSFORMS-COORDS.** Track local and accumulated coordinate spaces.
Matrix composition is order-sensitive; use known points to check translation,
scale, rotation and skew. Preserve transform order, origins, reference boxes,
stroke scaling and any vector-effect. CSS transforms and SVG transform
attributes have different syntax/reference concerns; route CSS details.

### Paint and reusable graphics

**SVG-05-PAINT-CURRENTCOLOR.** Distinguish fill from stroke and inspect winding,
cap/join/dash geometry and opacity. Group opacity is not always equivalent to
setting opacity on every child. `currentColor` uses the element's computed
`color`, including local overrides; external image content does not simply
inherit the host page's color. Presentation attributes participate in the CSS
cascade. Preserve painter order and route cascade questions to CSS.

**SVG-06-GRADIENTS-PATTERNS.** Keep paint-server definitions, stable IDs and
references coherent. Inspect stops, spread, transforms and coordinate units;
objectBoundingBox and userSpaceOnUse differ. Pattern tile units, content units
and viewBox interact. Degenerate bounds need special attention. A matching ID
does not prove the target is an appropriate paint server.

**SVG-07-DEFS-SYMBOLS-USE.** `g` groups rendered content, defs stores reusable
definitions, and symbol supplies a reusable viewport when instantiated. Use
width/height affect symbol/svg targets rather than universally resizing any
referenced element. Check duplicate IDs when composing fragments, missing
references, direct/indirect cycles and external-reference constraints. Preserve
use shadow-tree and inheritance boundaries instead of assuming ordinary
selector or DOM access to every instance descendant.

**SVG-08-CLIPPING-MASKING.** Clipping constrains visible geometry; masking
uses alpha or luminance. Preserve clipPathUnits, maskUnits, maskContentUnits,
mask-type, region bounds and compatible references. Replacing a mask with a
clip can change appearance. Edge antialiasing and offscreen compositing need
actual renderer evidence.

### Text, effects and interaction

**SVG-09-TEXT-TYPOGRAPHY.** Text/tspan positioning, anchors, baselines, fonts,
shaping, direction and language affect layout. Do not infer glyph metrics from
font size alone. Converting text to paths loses selectability, search and
semantic text unless separately restored, and may carry font/artwork rights
obligations. Preserve useful text and naming beyond visual glyph outlines.

**SVG-10-FILTER-EFFECTS.** Inspect filter inputs/results, filter and primitive
units, subregions, color interpolation and resource cost. Blur/shadow extents
can be clipped. Unknown primitives or target behavior remain unqualified.
Use this bounded check for practical authoring, not as a GPU/performance guide.

**SVG-11-DOM-INTERACTION.** Establish image versus document embedding before
reasoning about script/events/animation. Preserve identifiers referenced by
explicitly authorized DOM code. Recognition of an event attribute does not
prove event lifecycle or interaction. Delegate timing, focus and browser
compatibility to project runtime/testing owners; JavaScript correctness is
not DOM correctness.

**SVG-12-A11Y-SEMANTICS.** Determine meaningful, decorative or interactive use.
For meaningful inline graphics provide an appropriate name, often title with
explicit aria-labelledby, and verify referenced IDs and useful text. Supply
additional descriptions through desc/aria-describedby where appropriate.
External img alternatives belong on the embedding image; complex graphics may
need equivalent long-form information. Decorative graphics should avoid
redundant announcements and keyboard stops. Interactive content needs real
roles, keyboard operation and visible focus: tabindex alone adds no behavior.
Do not hide focusable controls from assistive technology. Naming markup is not
proof of WCAG compliance or the accessibility tree; contrast depends on the
applicable criterion and context.

### Resources and deterministic authoring

**SVG-13-SECURITY-PROCESSING.** State inline HTML, standalone document,
image/CSS image, or object/iframe context. Processing modes constrain script,
interaction and external resources differently. A static-asset subset may
refuse scripts, handlers and external resources without making them universally
invalid SVG. Inspect hrefs, paint URLs, styles, fonts, images and foreignObject
against actual trust/privacy policy. Reading a graphic does not authorize
fetching linked resources. Pattern matching is an adverse signal, never a
complete sanitizer; unresolved untrusted execution or resource access stops.

**SVG-14-SERIALIZATION-OPT.** Use the project's deterministic encoding,
escaping, namespace, ID, numeric and attribute-order rules. Preserve child paint
order and significant text whitespace. Comments or metadata may be required
by tooling or rights. Optimization must preserve geometry, precision,
transform order, CSS/DOM references and accessible meaning. Do not casually
strip viewBox, names, IDs or groups. Smaller/repeatable bytes do not prove
rendering equivalence; require appropriate negative controls and target
visual/interaction evidence before making that claim.

**SVG-15-ROUTING-BOUNDARIES.** Keep selection, response and route distinct.
Stricter project subsets prevail locally; a subset refusal is not a universal
language error. Existing CSS/JS/TS/JSX/React owners remain independent. Under
APGR v1 resolution select `svg-language-profile` explicitly; `languages:
["svg"]` is an invalid structured request. Compose only independently selected
owners. No future profile or successor task is implicitly authorized.

### Response guide

| Level | SVG signal | Required response |
| --- | --- | --- |
| Green — routine | Local authoring with known subset/context and proportional checks | Proceed under project checks |
| Yellow — caution | Sizing, font, paint units, reference scope or target behavior is uncertain | Inspect the named dependency before claiming correctness |
| Orange — warning | Cross-fragment reuse, text outlining, optimization or resource-policy changes affect several contracts | Record bounded design, adverse controls and rollback |
| Red — crisis / stop | Untrusted execution/fetch, missing ownership, destructive semantic loss or false rendering/accessibility claims remain unresolved | Stop that dependent action and obtain the required owner/evidence |

## Project-owned parameters

The project selects SVG representation and subset, renderer/browser/version,
embedding mode, layout and theme rules, font assets, trusted inputs, resource
policy, generator/optimizer options, precision tolerances, accessibility
requirements, performance limits, test targets, dependencies and rollback.
The APGR skill-file byte ceiling is a context-authoring policy, never a limit
on a user's graphic. Do not invent universal document-size or complexity bands.

## Evidence and completion

Report the artifact class, target/context, SVG decision, response, reference
and geometry checks, serialization evidence, any real rendering/interaction
checks, limitations and unresolved routes. Synthetic structural tests cannot
establish browser pixels, assistive-technology behavior or WCAG compliance.
Keep source inspection, mathematical checks and runtime observations distinct.

The profile is original guidance based on the SVG 2 Candidate Recommendation
of 2018-10-04 and primary XML, HTML, CSS-module and WAI sources inspected
2026-09-08. Source-to-clause provenance and draft-status limitations are in the
[SVG contract](../../docs/specs/svg-language-profile.md).
Refresh when standards, supported targets, resource processing, accessibility
mappings or optimizer behavior changes, and before maturity/release decisions.

Removal reconciles the leaf, catalog, projection, capability route, packaged
metadata, current inventories and candidate tests; preserve ADR, evaluation,
exit and provenance history. Removal does not authorize changing a consumer.

## Stop or escalate

Stop a dependent claim when context/subset/renderer is unknown, references or
path grammar are unresolved, generated output is edited without its owner,
text or naming is lost, untrusted resources can execute/fetch without policy,
or structural evidence is described as rendering/accessibility qualification.
Route broader platform or product decisions to their owners.

## Common mistakes

- Confusing a consumer's restricted subset with all valid SVG.
- Treating viewBox or omitted dimensions as proof of responsive layout.
- Checking XML but not path grammar, references or transform order.
- Assuming currentColor crosses an external image boundary.
- Replacing text, masks or groups without checking semantic loss.
- Calling a lexical scanner a sanitizer or an ID match accessible-name proof.
- Optimizing bytes while changing paint order, precision or accessible meaning.
