# Markdown Language Profile — Candidate Specification

Lifecycle: `retained-provisional`.
Lifecycle ADR: `Accepted with amendment`.

## Status and branch-only boundary

- Phase: APG65 candidate authoring
- Status: branch-only candidate, Proposed under
  [ADR 0038](../adr/2026/07/0038-markdown-language-profile-candidate.md),
  unintegrated, pending separately authorized APG66 validation
- Governing architecture: [Markdown language-profile architecture](../architecture/markdown-language-profile-architecture.md)
  under [ADR 0037](../adr/2026/07/0037-markdown-language-profile-architecture-and-lean-validation.md)
  (Accepted with amendment)
- Candidate leaf: [skills/markdown-language-profile/SKILL.md](../../skills/markdown-language-profile/SKILL.md)
- Scenario navigation: [scenario-coverage record](markdown-language-profile-scenario-coverage.md)

This specification is design evidence on the Claude authoring branch. It is
not an integrated, provisional, stable, public, active, or released surface,
and no catalog, projection, route, maturity, project, release, test, or
inventory owner references it. This specification would be wrong if a
reviewer applying it to a scenario in the accepted register reached a
different owner, selection, response, or route than the register records, or
if any clause required knowledge that only the private register supplies.

## Purpose

The candidate `markdown-language-profile` owns one coherent problem: selected
Markdown dialect document semantics under the repository's actual parser
context. This document is the complete normative model for that candidate.
The leaf is the operational procedure; this specification carries the
detailed ownership graph, grammar hierarchy, boundary rules, semantic-risk
model, and qualitative structural policy. Stable HTML-comment clause
markers carrying `MARKDOWN-` IDs identify normative clauses; each clause ID
is globally unique across the leaf and this specification.

## Trigger and non-trigger

The trigger and non-trigger clauses live in the candidate leaf
(`MARKDOWN-TRIGGER`, `MARKDOWN-NONTRIGGER`). In summary: the profile
participates only when a material current decision depends on
selected-dialect document semantics, actual-parser discovery consequences,
Markdown semantic risk, or qualitative document-structure judgment for a
`.md` decision. It is a whole-file non-trigger for `.mdx`, frontmatter data
and schema, embedded non-Markdown fence content, HTML semantics, editorial
and content-strategy questions, tool selection, and site-pipeline
configuration.

## Effective grammar hierarchy

<!-- APG-CLAUSE: MARKDOWN-EFFECTIVE-GRAMMAR -->
Effective grammar is established in this exact order of authority:

1. the actual repository renderer or parser, with its exact version,
   configuration, and enabled extensions — this controls observed behavior
   without making the profile the parser owner;
2. CommonMark 0.31.2 (2024-01-28) as a bounded base reference, only for
   behavior to which that revision truthfully applies;
3. GFM 0.29 (2019-04-06) as a bounded reference, only for its five specified
   extension families (tables, task-list items, strikethrough, extended
   autolinks, disallowed raw HTML);
4. implementation-specific behavior — additions, omissions, sanitization,
   typography, directives, frontmatter handling, plugins, and divergences —
   as version-bound input owned by `parser-tool-owner`.

CommonMark 0.31.2 plus GFM 0.29 is never presented as one formally specified
composite dialect; the GFM reference predates the CommonMark base and no
primary source composes them. GitHub platform rendering and an Astro,
Starlight, or Satteri content pipeline are distinct implementation contexts:
the profile never equates them and never promises cross-context
compatibility.

<!-- APG-CLAUSE: MARKDOWN-UNKNOWN-GRAMMAR -->
When the parser or extension set cannot be identified, or a construct falls
outside the evidenced configured grammar and both bounded references, no
extension-dependent claim is made. Parser and configuration discovery — and
any decision to enable another extension — routes to `parser-tool-owner`
with `inspect-before-judgment`; interim claims are restricted to
independently evidenced facts, and the unsupported construct is never
silently interpreted, normalized, or adopted under Markdown authority.

<!-- APG-CLAUSE: MARKDOWN-PARSER-CONFLICT -->
When the actual parser demonstrably interprets a construct differently from
a bounded reference, actual behavior remains effective until the owning tool
decision is made. Whether to change tooling or accept the version-bound
behavior is a `parser-tool-owner` decision reached through
`stop-and-escalate`: dependent work stops, the pre-decision behavior is
recorded when the tooling decision is material, and the parser is never
overridden by a synthetic reference grammar.

## Source and rights basis

Both governing specification documents — the pinned CommonMark 0.31.2
specification and the pinned GFM 0.29 specification — state CC BY-SA 4.0 for
the specification text, with separately identified BSD-2-Clause and MIT
implementation, test, and derived-code regions that are not specification
authority. This candidate is independently written synthesis: it copies or
adapts no CommonMark, GFM, or target expression, quotes no specification
wording, and reproduces no specification example or test case. Exact source
object identities remain in publication-excluded evidence. Reverify before
reuse when either specification revision, either rights file, the rights
policy, the pinned targets' dialect or toolchain evidence, or the accepted
language-profile contract changes.

## Owner and non-owner graph

<!-- APG-CLAUSE: MARKDOWN-OWNER -->
Within the selected dialect the profile owns: block and inline structure;
heading hierarchy as document structure; list and blockquote structure;
link, image, and reference syntax including reference-definition resolution
and collision behavior; code spans and fenced code blocks including the
fence and info-string boundary; escaping and delimiter behavior; the
selected GFM extensions as dialect facts; raw-HTML pass-through recognition
as a boundary fact; recognition of where a parser-established frontmatter
block ends and body parsing begins, as a consumed fact; document
responsibility and structural extraction seams; and Markdown-specific
diagnostics and validation reasoning. Whole-file ownership applies only to
`.md` content under an evidenced parser context.

<!-- APG-CLAUSE: MARKDOWN-NONOWNERS -->
The profile does not own: editorial quality, tone, or voice; content
strategy; factual correctness; product and project policy; HTML meaning; DOM or browser
behavior; accessibility acceptance; frontmatter data language, schema, or
values; embedded code-language semantics; MDX and JSX whole-file semantics;
Astro or Starlight host policy; parser, plugin, or tool selection;
formatter, linter, or link-checker selection; build; preview; or
deployment. Narrowing from evidence: link-destination validity is project-
and tool-owned while syntax, resolution, and collision semantics stay
owned; image asset existence, layout, and policy are project-owned while
image syntax and alternative-text presence stay owned as Markdown facts —
accessibility acceptance never follows from presence; fenced content
belongs to its embedded language while the fence boundary stays owned; and
the profile selects no tool. A clause may explain any of these boundaries
without absorbing the adjacent owner.

## Selection, response, and routing axes

<!-- APG-CLAUSE: MARKDOWN-AXES -->
Every decision keeps three orthogonal axes:

- **Selection** — exactly one of `selected` (Markdown owns the primary
  decision), `embedded-route` (one primary owner remains exact while a
  bounded embedded decision routes onward), `route-to-owner` (another owner
  owns the primary decision), or `non-trigger` (whole-file Markdown
  selection does not apply).
- **Response** — exactly one of the four ordered warning severities:
  `proceed-routine` (`Green — routine`), `inspect-before-judgment`
  (`Yellow — caution`), `bounded-local-decision` (`Orange — warning`), or
  `stop-and-escalate` (`Red — crisis / stop`).
- **Route** — one exact receiving-owner token, or `not-applicable`.

Routing never lowers severity; a routed stop remains stopped until the
receiving owner resolves it. A `non-trigger` is a selection state with a
routine handoff response, not a Green Markdown decision. The receiving-owner
vocabulary is the accepted closed set: `markdown-language-profile`,
`mdx-owner`, `parser-tool-owner`, `project-policy`, `project-design`,
`repository-policy`, `human-instruction`, `host-owner`, `generic-lifecycle`,
and the four conceptual receiving owners `html-owner` (HTML meaning),
`accessibility-owner` (accessibility acceptance),
`embedded-language-owner` (fenced or embedded non-Markdown languages), and
`data-language-owner` (frontmatter data syntax). Conceptual receiving
owners identify competence boundaries; none is asserted to exist as an
integrated skill.

## Block and inline ownership

<!-- APG-CLAUSE: MARKDOWN-BLOCK-INLINE -->
Block and inline consequences are derived from the evidenced grammar, never
from trial rendering presented as specified behavior. Paragraphs, lists,
blockquotes, and their nesting — including lazy continuation — are resolved
by the applicable container rules before any reflow, and a reflow that
changes structure is disclosed rather than silent. Emphasis, escaping, and
delimiter runs are resolved exactly from the applicable rules for the
evidenced parser; a guessed rendering is never presented as specified.
Inline code spans use the evidenced backtick-run rule to contain literal
backticks, and an HTML-entity workaround is never presented as Markdown
semantics.

<!-- APG-CLAUSE: MARKDOWN-HEADING-STRUCTURE -->
Heading hierarchy is owned document structure. A skipped or inconsistent
heading level is an owned defect that receives a proportionate repair with
`inspect-before-judgment`: a small hierarchy defect is never escalated to
crisis, and depth alone is not a defect without selected-renderer or
navigation evidence, which stays with its project owner.

<!-- APG-CLAUSE: MARKDOWN-EXTENSION-EVIDENCE -->
Selected-extension syntax is a dialect fact only under evidence that the
actual parser configuration enables it. Table semantics apply only under the
evidenced implementation and option set, and cross-version composition is
never asserted. For an evidenced table, task-list, or extended-autolink
decision, the primary owner is `markdown-language-profile`, selection is
`selected`, response is `proceed-routine`, and route is `not-applicable`.
Task-list item syntax is owned while the project meaning of
a checked state is not; no workflow state is inferred from checkbox syntax.
Extended autolinks are distinguished from base angle-bracket autolinks, and
bare-URL rendering is never promised outside the evidenced implementation
and option set.

## Links, references, and images

<!-- APG-CLAUSE: MARKDOWN-LINK-REFERENCE -->
Link, image, and reference-definition syntax, resolution, and collision
behavior are owned. When two normalized reference labels resolve
differently, the profile surfaces the applicable precedence, records both
definitions before any material repair, and obtains the intended
destination from the content owner as a `bounded-local-decision` routed to
`project-policy`; neither definition is silently deleted or rewritten.
Whether a syntactically valid destination actually resolves is a
`project-policy` decision (`route-to-owner`, `inspect-before-judgment`);
the profile neither selects a link checker nor invents a replacement
destination. Image syntax and the
presence of alternative text are owned Markdown facts; accessibility
acceptance routes to the accessibility owner and is never claimed from
presence alone.

## Fences and embedded languages

<!-- APG-CLAUSE: MARKDOWN-FENCE -->
The profile owns fence opening, closing, and info-string placement. Fenced
content belongs to its embedded language as a non-additive embedded route:
for a closed fence containing another language, the primary owner is
`markdown-language-profile`, selection is `embedded-route`, response is
`proceed-routine`, and route is `embedded-language-owner`, while
`parser-tool-owner` remains a non-owner. The fence boundary decision stays
with Markdown while fenced content is never edited under Markdown authority.
An unterminated fence that
reclassifies following prose as code is an owned boundary defect: the
repair restores the smallest valid closing boundary as a
`bounded-local-decision`, the reclassification is surfaced, the pre-repair
region is recorded for a material edit, and no unrelated broad rewrite
rides along.

## Raw HTML

<!-- APG-CLAUSE: MARKDOWN-RAW-HTML -->
The profile owns whether the selected Markdown syntax recognizes and passes
a raw-HTML construct through, including the inline-versus-block distinction
and the selected dialect's disallowed-raw-HTML filter as dialect facts. It
does not own HTML meaning, sanitization policy, browser behavior, or
accessibility acceptance: element meaning routes to the HTML owner, and no
HTML or accessibility claim is made under Markdown authority. For ordinary
raw-HTML recognition with a simultaneous meaning decision, the primary owner
is `markdown-language-profile`, selection is `embedded-route`, response is
`proceed-routine`, and route is `html-owner`; `accessibility-owner` and
`project-policy` remain non-owners of the syntax decision. When responsibility
is moved into raw HTML specifically to evade document-structure review, the
Markdown primary owner and `embedded-route` selection remain, response is
`bounded-local-decision`, and the exact permission receiver is
`project-policy`; `html-owner` and `parser-tool-owner` remain non-owners.
Whether a
project permits raw HTML at all is repository or project policy: when an
explicit repository rule forbids raw HTML, an addition is stopped
(`stop-and-escalate` routed to `repository-policy`), the
syntax-versus-permission distinction is preserved, and the profile neither
permits nor prohibits HTML under its own authority. No HTML profile grows
inside Markdown.

## Frontmatter

<!-- APG-CLAUSE: MARKDOWN-FRONTMATTER -->
Frontmatter is a consumed boundary, not Markdown grammar. Delimiter rules
are parser-, tool-, or project-owned; data syntax belongs to its
data-language owner; field schema belongs to the project or tool owner; the
document body belongs to Markdown. The profile consumes a valid
parser-established boundary and begins body judgment after the closing
delimiter without choosing fields, values, routes, publication dates, or
content collections. That valid-boundary body decision has primary owner
`markdown-language-profile`, selection `selected`, response
`proceed-routine`, and route `not-applicable`; `parser-tool-owner`,
`data-language-owner`, and `project-policy` remain non-owners. Fields with no
documented schema route schema
identification to `project-policy` with `inspect-before-judgment` before
any field change; fields are never invented, renamed, or normalized under
Markdown authority. A
malformed delimiter that makes the configured parser reclassify frontmatter
as body text is a parser-owned repair (`route-to-owner` to
`parser-tool-owner`, `bounded-local-decision`): only the evidenced boundary
form is repaired, data values are never rewritten as part of the repair,
and pre-repair bytes are recorded for a material edit.

## MDX and host boundary

<!-- APG-CLAUSE: MARKDOWN-MDX-HOST -->
`.mdx` is a whole-file non-trigger. MDX owns whole-file semantics for
`.mdx` files even when the content contains no expression and no JSX,
because MDX changes base semantics; whole-file Markdown claims and counts
are never made for `.mdx`. The exact whole-file tuple is primary owner
`mdx-owner`, selection `non-trigger`, response `proceed-routine`, and route
`mdx-owner`, with `markdown-language-profile` a non-owner. Expressions, JSX
elements, and ESM
import/export are MDX and host facts; expression braces are never read as
Markdown text and JSX regions are never edited under Markdown authority.
Renaming a document between `.md` and `.mdx` changes owner and can change
meaning; the profile flags the rename and never performs it under its own
authority.

<!-- APG-CLAUSE: MARKDOWN-EMBEDDED-ROUTE -->
Markdown embedded in a host artifact — a documentation string, comment,
generated fragment, or MDX body — is a bounded, non-additive embedded
route. The host retains whole-file ownership; Markdown judgment is limited
to the identified fragment; and no second whole-file classification is
created. Embedded judgment participates only where a host route exists and
the fragment is named, and reviewing a fragment inside a host-owned
artifact begins with `inspect-before-judgment` of that named fragment
before any Markdown conclusion.

## Semantic-risk model

<!-- APG-CLAUSE: MARKDOWN-SEMANTIC-RISK -->
Semantic risk is independent of physical length, and no numeric semantic
score exists. The covered risk classes are: syntax unsupported by the
evidenced grammar; dialect mismatch between contexts or versions;
reference-definition collision; link-destination boundary failures;
accidental reclassification of prose or code; raw-HTML boundary
misreadings; frontmatter-and-body boundary corruption; drift between
generated output and its source of truth; normative contradiction; and
false validation or completion claims. A small document with two
contradictory governing statements — in one file or across files — is a
semantic Red: dependent work stops, both statements are preserved, and one
authoritative resolution is obtained from `project-policy` before
harmonization; the contradiction is never dismissed for size and neither
statement is silently chosen. A long document with no firing structural or
semantic signal remains routine.

## Qualitative structural policy

<!-- APG-CLAUSE: MARKDOWN-STRUCTURAL-POLICY -->
Structural policy is qualitative and structure-first. This profile
contains no numeric whole-file warning band, and none may be introduced
while the accepted disposition stands. Line count may be recorded as
descriptive inspection evidence only: it classifies no document, fires no
signal, selects no response, and authorizes no split. Structural signals
classify the current proposed growth or edit — never a permanent file
score. Co-firing precedence is exact: semantic Red or an explicit policy
stop controls first; otherwise the strongest response severity controls;
routing is simultaneous and never lowers severity; signals at the same
severity never aggregate into a score. A large signal-free document may
proceed only while named maintainers can still review one coherent,
navigable whole-document responsibility; length, heading count, or
preference alone cannot fire the whole-document boundary. Bounded reviewer
judgment in this policy is honest judgment with named evidence — it is
never claimed to be mechanically deterministic.

Structural rollback follows the exact changed seam. Moves between documents
preserve navigation and record the move map.
Extracting an oversized tutorial or reference seam records the extraction
map. Adding bounded navigation without moving or extracting content has no
material rollback merely because its response is Orange.

## Fourteen-signal table

<!-- APG-CLAUSE: MARKDOWN-STRUCTURAL-SIGNALS -->
The fourteen accepted signals, each with its evidence class, observable
evidence and decision scope, default response and route, and false-positive
control. For every row the decision scope is the current proposed growth or
edit, and legacy behavior is the same: purpose control 10 of the accepted
architecture's frozen purpose controls applies — smallest-safe change, an
evidenced bounded exception where accepted, and no automatic broad rewrite.

| Signal | Evidence class | Observable evidence and decision scope | Default response and route | False-positive control |
| --- | --- | --- | --- | --- |
| `multiple-independent-audiences` | project input | named reader roles need incompatible navigation or detail for the current growth | `bounded-local-decision`; decomposition shape to `project-design` | naming roles alone does not prove divergence |
| `multiple-independent-purposes` | project input | named coequal installation, tutorial, reference, governance, or history duties govern the current growth | `bounded-local-decision`; shape to `project-design` | subordinate sections serving one purpose do not co-fire |
| `duplicated-normative-truth` | bounded reviewer judgment | two located statements govern the same behavior; divergence is separately evidenced | duplicate: `bounded-local-decision`; contradiction: `stop-and-escalate` to the exact policy owner | non-normative repeated explanation does not count |
| `oversized-single-section` | bounded reviewer judgment | named reviewers cannot review or navigate one section as a unit for its stated purpose | `bounded-local-decision`; extraction seam accepted by `project-design` | physical dominance alone does not fire |
| `deep-or-inconsistent-heading-hierarchy` | mechanically observable plus project input | skipped levels are byte-observable; unsupported depth needs renderer or navigation configuration | `inspect-before-judgment`; project navigation stays non-owner | depth alone is not a defect without selected-renderer evidence |
| `repeated-definitions` | mechanically observable | normalized reference labels or explicitly defined terms duplicate within the selected scope | `inspect-before-judgment`; intended meaning may route to `project-policy` | ordinary repeated words are not definitions |
| `manual-generated-content-mixing` | project input plus mechanically observable edit | generator ownership and a located hand edit or generated fragment are both evidenced | `bounded-local-decision`; repair to `parser-tool-owner` | a generated file without a hand edit is classified, not escalated |
| `navigation-failure` | bounded reviewer judgment | a named topic is unreachable through headings, contents, or links without full-text search | `bounded-local-decision`; navigation or extraction to `project-design` | reader preference without a named failed route does not fire |
| `code-prose-responsibility-mixing` | bounded reviewer judgment | named prose and code owners cannot review the changed document as one responsibility | `bounded-local-decision`; extraction shape to `project-design` | code examples serving the prose remain cohesive |
| `reference-tutorial-mixing` | bounded reviewer judgment | lookup entries interrupt an evidenced ordered learning sequence in the changed scope | `bounded-local-decision`; series or section extraction via `project-design` | a tutorial appendix does not automatically co-fire |
| `history-guidance-mixing` | bounded reviewer judgment | dated history and current governing instructions interleave in the changed scope | `bounded-local-decision`; authoritative content to `project-policy` | labeled non-current historical rationale does not count |
| `unsafe-source-of-truth-duplication` | project input plus bounded reviewer judgment | copied content tied to an identified generated or external authority lacks a tracking owner | governing copy: `stop-and-escalate`; otherwise `bounded-local-decision` to the policy owner | an independently maintained non-normative summary is not presumed unsafe |
| `policy-evasion` | bounded reviewer judgment | change provenance shows responsibility moved into HTML, fences, includes, or generated fragments to avoid review | `bounded-local-decision`; document-structure permission routes to `project-policy`, while moved embedded semantics route to their exact owner | legitimate embedded or generated content does not fire without evasion evidence |
| `whole-document-review-boundary` | bounded reviewer judgment | despite navigation, named maintainers cannot review the proposed change against one coherent whole-document responsibility | `bounded-local-decision`; partition or accepted bounded exception via `project-design` | length, heading count, or reviewer preference alone does not fire |

`duplicated-normative-truth` is intra-repository duplication;
`unsafe-source-of-truth-duplication` is an untracked copy from a generated
or external authority. A stricter co-firing signal controls under the
precedence rule above.

## Generated and embedded content

<!-- APG-CLAUSE: MARKDOWN-GENERATED -->
Generated artifacts are classified before structural judgment, and
classification never suppresses a semantic Red stop. Generator-owned output
is never hand-refactored: a documented hand edit inside generated output
that diverges from generator intent is a manual/generated ownership
conflict repaired through the generator (`route-to-owner` to
`parser-tool-owner`, `bounded-local-decision`), with regeneration as the
rollback path. Asserting the mixing signal requires exact evidence of both
generator ownership and a located manual edit. Moving responsibility into
raw HTML, fences, includes, or generated fragments is policy evasion only
when change provenance evidences an attempt to avoid review; legitimate
embedding never fires the signal by itself.

## Legacy and exceptions

<!-- APG-CLAUSE: MARKDOWN-LEGACY-EXCEPTION -->
A legacy document may receive the smallest safe correction, a bounded
removal or decomposition, or an evidenced bounded exception. Legacy length
does not create a crisis by itself, lower the policy, authorize unrelated
growth, or require a broad rewrite: a long cohesive handwritten document
grows routinely while no independent signal fires, and decomposition is
never demanded from physical length alone. A bounded exception identifies
its real authority, artifact or task scope, reason, validation, rollback,
and non-precedential status, reusing the repository's accepted generic
authority conventions rather than a Markdown-specific hierarchy.

## Project-owned parameters

The repository owns the actual parser and extension set, plugin and
pipeline configuration, frontmatter schema and approved values, raw-HTML
permission policy, asset and link-checking policy, formatter and linter and
tool selection, document taxonomy and navigation conventions, content
strategy, publication and deployment, artifact classifications, accepted
exceptions, and any stricter repository policy, which always controls. The
leaf's `Project-owned parameters` section is the operational statement of
this list.

## Scenario coverage

The accepted APG63 register (as corrected by APG64) controls expected
scenario outcomes for the thirty-four candidate-semantic scenarios
APG63-MD-001 through APG63-MD-034. The
[scenario-coverage record](markdown-language-profile-scenario-coverage.md)
maps every semantic scenario to the stable clause IDs that support it; the
mapping proves navigation, not semantic sufficiency. The two review-process
invariants, APG63-MD-035 and APG63-MD-036, bind the future validation
review and are deliberately not explained or satisfied by this candidate.

## Validation and rollback

Candidate validation evidence is scenario-anchored: for a material
decision, the reported selection, response, route, evidence, and rollback
boundary must be reproducible from the clause set and the evidenced
grammar. Rollback recording is owned by the leaf's `MARKDOWN-VALIDATION`
clause: material repairs record their pre-change state first (colliding
definitions, reclassified regions, frontmatter bytes, contradictory
statements), and regeneration is the rollback path for generator-owned
output. This candidate is independently rollback-safe as an artifact
because no integration owner references it; retention and rejection follow
the accepted lean contract's integration and removal boundary, which this
specification deliberately does not restate.

## Known limitations

- Target dogfood remains thin: no pinned target document exerts
  long-document pressure, so structural policy rests on the accepted
  qualitative disposition rather than target calibration.
- The pinned targets were never installed or executed; parser facts are
  lock- and configuration-evidence, not runtime proof.
- The four conceptual receiving owners name competence boundaries, not
  existing integrated skills.
- Bounded reviewer judgment is honest judgment with named evidence, not
  mechanical determinism; two reviewers replaying a scenario from its
  public facts are the determinism test.
- The GFM reference predates the CommonMark base revision; gaps between
  them are resolved by actual parser evidence, not interpolation.

## APG66 disposition

APG66 independently rebuilt the scenario oracle from accepted APG64, applied
one coherent correction, preserved the exact corrected patch before fresh
review, and replayed all thirty-four semantic scenarios successfully. ADR
0038 is Accepted with amendment and this profile is retained provisionally.
The two review-process invariants remain lifecycle evidence outside this
specification. This disposition grants no stability, readiness, publication,
deployment, APG67, or successor authority.
