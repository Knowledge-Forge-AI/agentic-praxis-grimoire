---
name: markdown-language-profile
description: Use when a material decision depends on the repository's actual Markdown parser or selected-dialect document semantics, or on qualitative Markdown document-structure policy.
---

# Markdown Language Profile

Normative detail: [Markdown Language Profile](../../docs/specs/markdown-language-profile.md).
Lifecycle: `retained-provisional`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

<!-- APG-CLAUSE: MARKDOWN-TRIGGER -->
Apply Markdown-specific judgment only when a current, consequence-bearing
decision materially depends on selected-dialect Markdown document semantics
under the repository's actual parser context. Establish the effective grammar
— the actual renderer or parser, its exact version, configuration, and enabled
extensions — before relying on any dialect-dependent behavior. Use the highest
justified `Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response for the one coherent current decision, exactly
as the accepted language-profile contract defines those levels.

Keep three axes separate for every decision: selection (whether and how
Markdown judgment participates), response (the warning severity), and route
(the one exact receiving owner of any simultaneous non-Markdown decision).
Routing never lowers severity, and a routed stop remains stopped until the
receiving owner resolves it. Structural judgment is qualitative and
decision-scoped: named signals classify the current proposed growth or edit,
never a whole-file score, and no numeric line band exists in this profile.

## Do not use

<!-- APG-CLAUSE: MARKDOWN-NONTRIGGER -->
Do not use this profile for:

- ordinary prose drafting, tone, house style, or editorial preference;
- fact checking or content strategy;
- HTML element semantics, sanitization policy, or accessibility acceptance;
- frontmatter data syntax, schema, field values, routes, or publication
  metadata;
- the semantics of code inside a fence — the embedded language owns fenced
  content;
- whole-file work on `.mdx` files — MDX owns whole-file semantics even when
  the content looks like plain Markdown, and this profile keeps no
  independent whole-file claim there;
- Astro, Starlight, or other site-pipeline configuration;
- selecting a parser, plugin, formatter, linter, or link checker; or
- formatting runs, lint runs, builds, previews, or deployment.

A non-trigger is a routine handoff, not a Green Markdown decision:
whole-file Markdown selection is absent, and any named receiving owner is
identified exactly.

## Procedure

1. Establish task authority, repository instructions, and the exact mutation
   and rollback boundaries before editing.
2. Establish the effective grammar from repository evidence: the actual
   renderer or parser, exact version, configuration, and each materially
   enabled extension family. When that evidence is unknown, make no
   extension-dependent claim and route parser and configuration discovery to
   `parser-tool-owner`.
3. Decide the selection state for the current decision: `selected`,
   `embedded-route`, `route-to-owner`, or `non-trigger`. Whole-file selection
   applies only to `.md` content under an evidenced parser context.
4. Classify the artifact before structural judgment: maintained handwritten
   document, generated output, legacy document, or embedded fragment.
   Classification never suppresses a semantic Red stop.
5. Inspect the Markdown semantics the decision actually touches: block and
   inline structure, heading hierarchy, lists and blockquotes, links, images
   and reference definitions, code spans and fences, escaping and delimiter
   behavior, enabled extension syntax, raw-HTML pass-through, and the
   consumed frontmatter boundary.
6. Apply the qualitative structural signals from the profile specification
   to the current proposed growth or edit only. Record line count as
   descriptive inspection evidence when useful; it fires no signal, selects
   no response, and authorizes no split by itself.
7. Assign the response: proceed for `Green — routine`; gather the named local
   evidence before judgment for `Yellow — caution`; make an explicit bounded
   local decision with rationale and rollback where material for
   `Orange — warning`; stop
   for `Red — crisis / stop`. Semantic Red or an explicit policy stop
   controls first; otherwise the strongest justified response controls;
   co-firing signals never aggregate into a score.
8. Route every simultaneous non-Markdown decision to its one exact owner
   while keeping the Markdown response unchanged: parser and tooling facts to
   `parser-tool-owner`, content and permission policy to `project-policy`,
   document taxonomy and decomposition shape to `project-design`, stricter
   repository rules to `repository-policy`, MDX whole-file work to
   `mdx-owner`, host-owned artifacts to `host-owner`, HTML meaning to the
   HTML owner, accessibility acceptance to the accessibility owner, fenced
   content to the embedded-language owner, and frontmatter data syntax to
   the data-language owner.
9. Preserve stricter repository policy; it always controls. Report the
   selection, response, signals, routes, evidence, and rollback boundary.

### Effective grammar

Use the accepted authority hierarchy exactly. The actual repository renderer
or parser with its exact configuration controls observed behavior. CommonMark
0.31.2 is a bounded base reference only for behavior to which that revision
truthfully applies. GFM 0.29 is a separate bounded reference only for its five
specified extension families — tables, task-list items, strikethrough,
extended autolinks, and disallowed raw HTML — and is never combined with
CommonMark 0.31.2 into one composite dialect. Implementation-specific
behavior, divergence, plugins, and typography are version-bound
`parser-tool-owner` facts. GitHub platform rendering and an Astro, Starlight,
or Satteri pipeline are distinct contexts; never promise compatibility
between them.

### Owner and routes

This profile owns selected-dialect document semantics only: structure,
syntax, resolution and collision rules, the fence and info-string boundary,
the frontmatter boundary as a consumed parser-established fact, raw-HTML
recognition, extraction seams, and Markdown-specific diagnostics. It explains adjacent boundaries without
absorbing the adjacent owner: destination validity, asset policy, fenced
content, HTML meaning, accessibility acceptance, frontmatter data and
schema, MDX whole-file semantics, and every tool selection remain routed.

### Semantic-risk checks

Semantic risk is independent of physical length. Inspect for: syntax the
evidenced grammar does not support; dialect mismatch between contexts;
reference-definition collision; broken or ambiguous link destinations (route
the validity decision); accidental reclassification of prose as code or code
as prose; raw-HTML boundary misreadings; frontmatter delimiter corruption;
divergence between generated output and its source of truth; contradictory
normative statements; and false validation success. A small document
containing contradictory governing statements can be semantic Red; a long
signal-free document can remain routine.

### Qualitative structural checks

The profile specification owns the full fourteen-signal table with each
signal's evidence class, observable evidence, decision scope, default
response, route, false-positive control, and legacy behavior. In this
procedure: fire a signal only from its named observable evidence for the
current change, never from length, heading count, or preference alone; treat
generated artifacts through classification first; give legacy documents the
smallest safe correction or an evidenced bounded exception rather than a
broad rewrite; and treat responsibility moved into HTML, fences, includes,
or generated fragments as policy evasion only when change provenance
evidences an attempt to avoid review.

## Project-owned parameters

The repository owns the actual parser and extension set; plugin and pipeline
configuration; frontmatter schema and approved values; raw-HTML permission
policy; asset and link-checking policy; formatter, linter, and tool
selection; document taxonomy and navigation conventions; content strategy;
publication and deployment; artifact classifications; accepted exceptions;
and any stricter repository policy, which always controls.

## Evidence and completion

<!-- APG-CLAUSE: MARKDOWN-VALIDATION -->
When material, report the selection state, response level, fired structural
and semantic signals, the applied grammar evidence, each exact route, the
repository policy inputs, and the rollback boundary. Before a material
repair, record the pre-change state the rollback needs — for example both
colliding reference definitions, the pre-repair region of a reclassified
document, the pre-repair frontmatter bytes, the responsibility moved into an
evasive embedding, or both contradictory normative statements.
Never report a dialect-dependent conclusion as validated without naming the
parser evidence it rests on, and never claim completion while a routed stop
remains unresolved. `Green — routine` needs applicable project checks;
`Yellow — caution` adds the named local evidence; `Orange — warning` adds
the recorded bounded decision, rationale, focused validation, and rollback
where material;
`Red — crisis / stop` records the stopped action and the condition required
for reconsideration.

## Stop or escalate

<!-- APG-CLAUSE: MARKDOWN-STOP -->
Stop and escalate, keeping the stop in force while the decision routes to
its owner, when:

- the actual parser materially conflicts with a bounded reference and the
  repository must decide whether to change tooling or accept version-bound
  behavior — preserve actual behavior until `parser-tool-owner` decides;
- a change adds raw HTML that an explicit repository rule forbids — the
  prohibition routes to `repository-policy` and is never waived under
  Markdown authority;
- two normative statements governing the same behavior contradict each
  other, in one document or across documents — preserve both statements and
  obtain the `project-policy` resolution before dependent work or
  harmonization;
- copied governing content duplicates a generated or external source of
  truth without a tracking owner; or
- a proposed edit would silently change meaning under the evidenced grammar
  in a way the author did not decide.

Escalate to the named human authority when no closed route resolves the
stop. Contradiction stops are size-independent: never dismiss one because
the document is small.

## Common mistakes

- Treating every `.md` edit as Markdown-profile work.
- Making extension-dependent claims with no parser evidence.
- Treating CommonMark 0.31.2 plus GFM 0.29 as one specified dialect.
- Promising that GitHub rendering matches the site pipeline.
- Counting a `.mdx` file as a Markdown-owned document because it contains
  no JSX.
- Editing fenced content, frontmatter data, or JSX under Markdown authority.
- Using line count, heading count, or editorial preference as a structural
  classification.
- Hand-refactoring generated output instead of routing to its generator.
- Demanding decomposition of a legacy document beyond the smallest safe
  correction without an evidenced signal.
- Letting a route or a non-trigger silently lower a stop.
- Claiming accessibility, HTML, or link-validity outcomes from Markdown
  syntax facts alone.
