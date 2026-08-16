# Markdown Language-Profile Architecture

- Phase: APG63, terminally reviewed by APG64
- Status: Current accepted architecture input under ADR 0037; no
  candidate-authoring authority
- Decision record: [ADR 0037](../adr/2026/07/0037-markdown-language-profile-architecture-and-lean-validation.md)

## Purpose

This architecture answers whether a reusable `markdown-language-profile` owns
one coherent problem, which dialect is in scope, where Markdown ends and
neighboring owners begin, how Markdown document structure should be governed,
and what lean candidate-independent contract a later authoring phase must
answer to. APG63 authors no skill and integrates nothing; the CSS rejection
recorded by ADR 0036 remains terminal and is not reopened.

## Sources, versions, and rights

- CommonMark 0.31.2 (2024-01-28) is a bounded base reference where the
  actual parser behavior is consistent with that revision. Exact-object and
  release-tag review found no newer CommonMark specification revision.
- GFM 0.29 (2019-04-06) is a separate bounded reference for its five marked
  extensions: tables, task-list items, strikethrough, extended autolinks,
  and disallowed raw HTML. It is based on the CommonMark 0.29-era grammar;
  no primary source establishes normative composition with CommonMark
  0.31.2. The architecture therefore defines no synthetic CM-0.31.2-plus-
  GFM-0.29 dialect.
- Effective behavior comes from the repository's actual renderer or parser,
  exact version, configuration, and enabled extensions. A specification
  reference explains only the facts it actually covers. Implementation-
  specific behavior and divergence route to `parser-tool-owner`.
- Both exact specification documents state CC BY-SA 4.0. Their repositories
  separately apply BSD-2-Clause and MIT terms to identified implementation,
  test, and derived-code regions; those regions are not specification
  authority. No copied or adapted CommonMark, GFM, or target expression was
  identified in APG63 or this correction. This is a bounded factual and
  clean-room conclusion, not a universal legal guarantee.
- Exact commit, tree, document, and license-object identities remain in the
  publication-excluded evidence bundles.

## Target parsers and dogfood

The two pinned targets contain nineteen tracked `.md` or `.markdown` paths:
eighteen regular files and one symlink. They classify as three maintained
documents, one generated changelog, three tool-boilerplate paths, seven
fixtures or demos, three legal or governance documents, one agent
instruction, and one symlink. The historical seven-member set is only a
mixed calibration subset: three maintained documents, one generated file,
one starter-boilerplate README, and two demo stubs. It is not the complete
target Markdown inventory and does not define profile selection.

All nineteen paths were separately assessed for Markdown trigger, ordinary
handwritten growth, useful structural or dialect dogfood, and calibration
exclusion. Excluded instructions, governance, templates, generated history,
and one rich demo still add useful purpose, boundary, duplication, raw-HTML,
heading, and extension evidence. The complete target maximum is eighty-two
physical lines, the ordinary-maintained maximum thirty-four, and the
governance maximum forty-four. These changes increase purpose diversity but
still provide no long-document pressure or numeric threshold authority.

The exact configured target contexts are distinct:

- GitHub-rendered repository documents use GitHub's platform renderer and
  post-processing, not the Astro content pipeline and not the GFM
  specification alone.
- The website lock/configuration selects Astro 7.1.3, Starlight 0.41.4,
  `@astrojs/markdown-satteri` 0.3.4, and Satteri 0.9.5. No
  `markdown.processor` override exists, so the configured `.md` processor is
  Astro 7's Satteri default with its configured feature set.
- The theme resolves Astro 7.1.3, Starlight 0.41.3, and the same Satteri
  pair without a processor override. Its lock importers and tracked
  manifests/workspace disagree on historical package names, so those are
  exact intended/resolved facts, not runtime proof of a reproducible install.

The targets were not installed, built, tested, linted, previewed, or
executed. Parser presence in a lock is not proof that it is the active
processor. Frontmatter, content schemas, directives, asides, heading links,
code transforms, smart punctuation, and platform post-processing remain
implementation- or project-specific facts rather than GFM-0.29 facts.

## Owner

A reusable `markdown-language-profile` owns one coherent problem: selected
Markdown dialect document semantics. Within the selected dialect it owns:

- block and inline structure;
- heading hierarchy as document structure;
- list and blockquote structure;
- link, image, and reference syntax, including reference-definition
  resolution and collision behavior;
- code spans and fenced code blocks, including the fence and info-string
  boundary;
- escaping and delimiter behavior;
- the selected GFM extensions as dialect facts;
- raw-HTML pass-through recognition as a boundary fact;
- recognition of where a frontmatter block ends and body parsing begins,
  as a consumed parser fact (the delimiter rules themselves are
  parser-owned, and frontmatter is not part of the selected dialect);
- document responsibility and extraction seams (structure-first judgment);
- Markdown-specific diagnostics and validation reasoning.

Evidence-driven narrowing applies:

- link-destination validity (whether a URL resolves, link-checker policy)
  is project- and tool-owned; the profile owns syntax, resolution rules,
  and ambiguity or collision semantics only;
- image asset existence, layout, and asset policy are project-owned; the
  profile owns image syntax and the presence of alternative text as a
  Markdown fact, never accessibility acceptance;
- the language inside a code fence is a non-additive embedded route: the
  fence boundary is owned, the fenced content is not;
- the profile selects no formatter, linter, or link checker.

## Non-owners

The following remain explicitly outside Markdown ownership: prose quality
and editorial voice; content strategy; factual correctness of subject
matter; product policy; HTML semantics; HTML accessibility outcomes;
browser runtime; MDX executable semantics; JSX; Astro host semantics;
Starlight conventions; frontmatter schema and approved values; remark and
rehype plugin selection; site pipeline configuration; formatter and linter
selection; link-checker and tool selection; build; preview; deployment.
The profile may explain a pass-through or parsing boundary without taking
ownership of the passed-through language or the project decision.

## Grammar and dialect selection

Markdown is not one universal grammar, and `GFM selected` is not a single
portable boolean. Selection records the actual renderer or parser, its exact
version and configuration, and each materially enabled extension family.

The authority hierarchy is:

1. **Effective grammar:** actual repository renderer/parser plus exact
   configuration. This controls observed behavior but does not make the
   profile the parser owner.
2. **Base reference:** CommonMark 0.31.2 only for behavior to which that
   reference truthfully applies.
3. **Extension reference:** pinned GFM 0.29 only for the five extension facts
   its specification marks. It is not combined normatively with CommonMark
   0.31.2.
4. **Implementation behavior:** parser-specific additions, omissions,
   sanitization, typography, directives, frontmatter handling, plugins, and
   divergences are version-bound inputs owned by `parser-tool-owner`.

GitHub rendering and Astro/Starlight/Satteri rendering are distinct contexts.
A reusable profile never promises compatibility between them. Unsupported
syntax routes to the parser or project owner; a plugin is a consumed project
fact; an unknown parser or extension set requires inspection before any
dialect-dependent claim. MDX remains a separate owner and whole-file
non-trigger. Frontmatter remains a recognized implementation boundary, not
Markdown schema ownership.

## Raw HTML boundary

Markdown owns whether selected Markdown syntax recognizes and passes a
raw-HTML construct through, including the inline-versus-block distinction
and the selected dialect's disallowed-raw-HTML filter as dialect facts.
Markdown does not own HTML semantics, DOM behavior, accessibility
acceptance, or browser rendering policy. Whether a project permits raw HTML
at all is repository or project policy; the profile reports the boundary
and routes to that owner. HTML embedded inside Markdown remains a
pass-through fact; Markdown embedded in another host is an embedded route.
No HTML profile is created inside Markdown.

## Frontmatter boundary

Frontmatter is a boundary, not automatically Markdown grammar. Delimiter
detection is a parser, tool, or project fact. Frontmatter data syntax
belongs to its data-language owner (YAML, TOML, JSON, or tool-specific).
Field schema belongs to the project or tool owner. The document body
belongs to Markdown. The profile may describe where frontmatter ends and
body parsing begins and may detect delimiter corruption as a boundary
fact. It never chooses field values, schemas, routes, publication dates,
or content collections.

## MDX and host boundary

- `.md`: candidate Markdown owner when the selected parser applies.
- `.mdx`: MDX owner for whole-file semantics. Markdown may be an embedded
  semantic route inside MDX; there is no independent Markdown whole-file
  count for `.mdx` files.
- Markdown-looking MDX with no JSX remains MDX-owned, because MDX changes
  base semantics even without JSX.
- MDX expressions, JSX elements, and ESM import/export are MDX and host
  facts, not Markdown constructs.
- A Markdown document renamed to `.mdx` changes owner and can change
  meaning; the rename is a project decision the profile flags, never
  performs.
- Markdown embedded in another host (documentation strings, comments,
  generated fragments) is an embedded route when a host route exists;
  it never produces a whole-file Markdown claim.

## Semantic-risk model

Semantic risk is independent from structural growth. Candidate semantic
signals include: link destination ambiguity; reference-definition
collision; heading hierarchy that changes interpretation or navigation;
fence delimiter failure; accidental code or prose reclassification;
raw-HTML boundary misunderstanding; dialect mismatch; frontmatter and body
boundary corruption; generated and manual source-of-truth conflict; unsafe
broad rewrite; false validation success. Project and content facts remain
outside Markdown.

The profile uses the shared warning contract's `Green — routine`,
`Yellow — caution`, `Orange — warning`, and `Red — crisis / stop` levels
exactly as the accepted language-profile contract defines them: a level
classifies one coherent current decision, and the highest justified level
controls the response. A short document containing contradictory normative
sources can be semantic Red. No semantic issue is forced into a numeric
structural level.

## Structural-policy disposition

APG63 selects disposition C: a qualitative structure-first policy without
numeric whole-file bands.

- One numeric whole-file policy (A) fails its own allowance conditions —
  that lines be a suitable signal across target and source families, that
  ordinary long-form references not be classified as crisis merely for
  being long, that continued mixed-purpose monster growth still be
  caught, and that values be frozen, policy-selected, and never
  percentile-derived. The corpus is purpose-heterogeneous at every scale: any band tight
  enough to catch mixed-purpose monster growth falsely classifies
  legitimate long-form references and changelogs as crisis, and any band
  loose enough to spare them is vacuous. The pinned targets provide zero
  calibration (no document over forty-nine lines), prior review found
  Markdown physical-line metrics unsuitable without separately frozen
  structure, the historically rejected values are forbidden, and
  percentile derivation is forbidden. Any numeric values would be
  invented rather than evidence-supported policy.
- A split numeric policy (B) requires both deterministic pre-size classes
  and independently justified per-class values. Some classes are
  deterministic before size inspection, but no per-class numeric value has
  an evidence base at the pinned targets, and inventing classes to obtain
  preferred thresholds is exactly the failure this phase must avoid. B is
  rejected now; a later evidence-backed revisit would require new
  authority.
- Deferral (D) is unnecessary because C is complete and testable.

Under C, every structural signal states its evidence class. A mechanically
observable predicate can be reproduced from bytes and configuration. Bounded
reviewer judgment requires named evidence and a decision scope. Project input
requires an identified project fact rather than profile inference. Human
judgment is permitted; it is never mislabeled as mechanical determinism.

| Signal token | Evidence class | Observable evidence and decision scope | Default response and route | False-positive control |
| --- | --- | --- | --- | --- |
| `multiple-independent-audiences` | project input | named reader roles require incompatible navigation or detail for the current growth | `bounded-local-decision`; `project-design` chooses decomposition | role labels alone do not prove divergence |
| `multiple-independent-purposes` | project input | named coequal installation, tutorial, reference, governance, or history responsibilities govern the current growth | `bounded-local-decision`; route shape to `project-design` | subordinate sections serving one purpose do not co-fire |
| `duplicated-normative-truth` | bounded reviewer judgment | two located statements govern the same behavior; divergence is separately evidenced | duplicate: `bounded-local-decision`; contradiction: `stop-and-escalate` to the exact policy owner | repeated explanation that is non-normative does not count |
| `oversized-single-section` | bounded reviewer judgment | named reviewers cannot review or navigate one section as a unit for its stated purpose | `bounded-local-decision`; `project-design` accepts an extraction seam | physical dominance alone does not fire |
| `deep-or-inconsistent-heading-hierarchy` | mechanically observable plus project input | skipped levels are byte-observable; unsupported depth requires renderer/navigation configuration | `inspect-before-judgment`; project navigation stays non-owner | depth alone is not a defect without selected-renderer evidence |
| `repeated-definitions` | mechanically observable | normalized reference labels or explicitly defined terms duplicate within the selected scope | `inspect-before-judgment`; intended meaning may route to `project-policy` | ordinary repeated words do not count as definitions |
| `manual-generated-content-mixing` | project input plus mechanically observable edit | generator ownership and a located hand edit or generated fragment are both evidenced | `bounded-local-decision`; route to `parser-tool-owner` | a generated file with no hand edit is classified, not escalated |
| `navigation-failure` | bounded reviewer judgment | a named topic is unreachable through headings, contents, or links without full-text search | `bounded-local-decision`; `project-design` chooses navigation or extraction | reader preference without a named failed route does not fire |
| `code-prose-responsibility-mixing` | bounded reviewer judgment | named prose and code owners cannot review the changed document as one responsibility | `bounded-local-decision`; route the extraction shape to `project-design` | code examples serving the prose remain cohesive |
| `reference-tutorial-mixing` | bounded reviewer judgment | lookup entries interrupt an evidenced ordered learning sequence in the changed scope | `bounded-local-decision`; `project-design` accepts series or section extraction | a tutorial appendix does not automatically co-fire |
| `history-guidance-mixing` | bounded reviewer judgment | dated history and current governing instructions are interleaved in the changed scope | `bounded-local-decision`; authoritative content routes to `project-policy` | historical rationale clearly labeled as non-current does not count |
| `unsafe-source-of-truth-duplication` | project input plus bounded reviewer judgment | copied content is tied to an identified generated or external authority and lacks a tracking owner | governing copy: `stop-and-escalate`; otherwise `bounded-local-decision` to the policy owner | independently maintained non-normative summary is not presumed unsafe |
| `policy-evasion` | bounded reviewer judgment | provenance of the current change shows responsibility moved into HTML, fences, includes, or generated fragments to avoid review | `bounded-local-decision`; route the moved language or policy to its exact owner | legitimate embedded or generated content does not fire without evasion evidence |
| `whole-document-review-boundary` | bounded reviewer judgment | despite navigation, named maintainers cannot review the proposed change against one coherent whole-document responsibility | `bounded-local-decision`; `project-design` chooses partition or an accepted bounded exception | length, heading count, or reviewer preference alone does not fire |

For every signal, the decision scope is the current proposed growth or edit,
not a retrospective file score. Co-firing precedence is exact: semantic Red or
an explicit policy stop controls first; otherwise the highest response
severity controls; routing is simultaneous and never lowers severity. Signals
at the same severity do not aggregate into a score. Legacy documents apply
purpose control 10: smallest-safe change, an evidenced bounded exception, and
no automatic broad rewrite. Those controls apply separately to every row.

Duplicated normative truth is intra-repository duplication; unsafe source-of-
truth duplication is an untracked copy from a generated or external authority.
Line count remains descriptive inspection input only. It can prompt a named
signal review, but cannot fire a signal or select an architecture by itself. A
signal-free large cohesive document may continue only while current evidence
still supports one navigable and reviewable responsibility; the qualitative
whole-document boundary prevents an unreviewable monster from being treated as
permanently routine without inventing numeric bands.

## Purpose controls

Ten purpose controls were frozen (with a recorded SHA-256 in the
publication-excluded bundle) before the structural-policy disposition was
selected, and they constrain its application:

1. a long cohesive changelog is not automatically a crisis;
2. a long generated reference is not ordinary handwritten growth;
3. a short document containing contradictory normative sources can be
   semantic Red;
4. a README serving installation, architecture, API reference, and
   governance may require decomposition well before an arbitrary extreme
   line count;
5. a large single reference table may need navigation rather than file
   split;
6. a large tutorial may need a series or section extraction;
7. a small document with broken heading hierarchy is not automatically
   high-risk, but the defect remains owned;
8. a document must not evade structural policy by moving content into
   HTML, code fences, includes, or generated fragments;
9. editorial preference alone does not become a Markdown stop;
10. existing long documents use smallest-safe and bounded-exception
    behavior where the selected architecture requires it.

Legacy documents and accepted exceptions follow the shared contract's
classification-first and smallest-safe rules; classification never
suppresses a semantic Red stop.

## Selection, response, and routing

The contract separates three orthogonal axes:

- **Selection:** `selected`, `embedded-route`, `route-to-owner`, or
  `non-trigger` says whether and how Markdown judgment participates.
- **Response:** `proceed-routine`, `inspect-before-judgment`,
  `bounded-local-decision`, or `stop-and-escalate` is the warning severity
  for the primary decision.
- **Route:** one exact receiving-owner token or `not-applicable` identifies
  where a simultaneous non-Markdown decision goes.

Routing never substitutes for severity. A stop remains a stop while the
decision routes to its owner; `non-trigger` is a selection state and still has
a routine handoff response. The profile triggers only when Markdown-specific
judgment is material to a current `.md` decision under the actual parser
context. It is a whole-file non-trigger for `.mdx`, frontmatter data and
schema, embedded non-Markdown fence content, HTML semantics, editorial and
content-strategy questions, and site pipeline configuration. Boundary
scenarios may use `embedded-route` without making whole-file ownership
additive.

## Project-owned parameters

Projects own: the actual parser and extension set; plugin configuration;
frontmatter schema and approved values; raw-HTML permission policy; asset
and link-checking policy; formatter, linter, and tool selection; document
taxonomy and navigation conventions; content strategy; publication and
deployment; and any stricter repository policy, which always controls.

## Lean validation model

The candidate-independent contract is a scenario and invariant register,
deliberately not an exact-action map. Thirty-four candidate-semantic scenarios
(APG63-MD-001 through APG63-MD-034) each have one public-safe input, parser and
dialect facts, primary decision, exact primary owner, selection state,
response severity, exact receiving owner, explicit non-owners, closed
structural and semantic signals, required invariant, forbidden outcome,
rollback, and source boundary. APG63-MD-035 and 036 are separately typed
review-process invariants. A future Markdown candidate does not satisfy or
explain them.

Exactness is tiered: ownership-bearing behavior, permission and stop
behavior, and safety and rollback behavior are exact; benign bookkeeping
may be recommended without becoming an automatic semantic defect unless it
changes ownership, permission, stop, privacy, or rollback behavior. An
extra reporting action is material only when it keeps the wrong owner
active, crosses a non-owner boundary, changes permission or stop behavior,
creates false completion, creates a privacy or rights burden, or
contradicts the selected architecture. More documentation is not
automatically a candidate failure.

An omitted structural observation is material only when it changes an exact
owner, selection, response, route, safety, rollback, rights, privacy, or false-
completion consequence. An extra inspect recommendation, route explanation,
or record action is non-material unless it changes one of those consequences.
This preserves tiered exactness without recreating CSS's brittle action map.

Generic candidate lifecycle stays outside Markdown semantic prose. The two
review-process rows bind validation, not a future leaf: the candidate remains
unintegrated until decision; retained-owner closure uses existing integration
contracts; rejection removes current surfaces and preserves history.

## Corrected-state evidence

APG64 and any later validation phase collect the complete initial material
set first and apply at most one coherent semantic correction. Before corrected-
state review, the manager records the exact corrected architecture artifacts,
their hashes, the reproducible full-index correction patch and its digest, and
the scenario vectors; every reviewer binds to those hashes. A genuinely new
material defect after the sole correction requires rejection. Retention binds
hashes to retained bytes; rejection preserves a compact publication-excluded
correction artifact before deletion. The original authoring object is never
rewritten. This is a review-evidence rule, not a candidate-lifecycle clause.

## Authoring eligibility

APG64 terminal result: `authoring-eligible-with-narrowing`. The owner is
coherent only with the actual-parser hierarchy, exact routing axes,
review-process separation, and reproducible qualitative predicates above.
Thin target dogfood prohibits any target-calibrated numeric structure claim.
The smallest later slice remains one Markdown leaf, one candidate
specification, one compact invariant map or scenario link, and one accepted
architecture input; no MDX, HTML, or Starlight skill. APG64's corrected-state
review accepted this architecture with amendment, and no candidate authoring
begins here.

## Rollback

This architecture is independently rollback-safe: rejecting ADR 0037
removes only APG63's architecture, contract, and register surfaces while
preserving APG63 history; no maintained executable, test, catalog,
projection, release, target, public, or active surface depends on it. A
later retained candidate defines its own rollback within the lean
contract's terms.

## Refresh conditions

Reverify before reuse when any of the following changes: the CommonMark
specification revision; the GFM specification revision or its rights file;
the rights policy of either specification source; the dialect or toolchain
evidence in the pinned target repositories; or the accepted language-
profile contract itself.

## Open adjacent gaps

JavaScript and Node target dogfood remains thin; TypeScript remains a
broader multi-class problem; JSX and MDX retain evidence gaps; React and
Vitest remain under ADR 0029 Policy A; Astro retains adjacent browser and
Starlight ambiguity; browser/DOM runtime, generic HTML, and accessibility
remain separate evidence gaps. APG63 decides none of these candidates.
