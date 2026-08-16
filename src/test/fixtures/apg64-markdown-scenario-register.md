# APG63 Markdown Scenario Register

APG64 forward-corrects this immutable APG63 proposal in the APG64 branch. The
register still contains exactly APG63-MD-001 through APG63-MD-036, but every
row now has one consequence-bearing outcome under the corrected closed schema.
Rows 001–034 are candidate-semantic scenarios. Rows 035–036 are review-process
invariants; a future Markdown candidate does not satisfy or explain them.

Each row has exactly fourteen fields: `In`, `Dialect`, `Decision`, `Owner`,
`Selection`, `Response`, `Route`, `Non`, `Structural`, `Semantic`, `Invariant`,
`Forbid`, `Rb`, and `Src`. `Owner` is one exact primary owner. `Selection` is
one of `selected`, `embedded-route`, `route-to-owner`, or `non-trigger`.
`Response` is one warning severity: `proceed-routine`,
`inspect-before-judgment`, `bounded-local-decision`, or `stop-and-escalate`.
`Route` is one exact receiving owner or `not-applicable`. A route never weakens
a simultaneous stop.

## Dialect and syntax — 001–008

### APG63-MD-001 — CommonMark ordinary document

- In: edit a plain .md document containing headings, paragraphs, lists, and links
- Dialect: actual parser/configuration; CommonMark 0.31.2 is the applicable bounded reference
- Decision: decide the document's block and inline Markdown semantics
- Owner: markdown-language-profile
- Selection: selected
- Response: proceed-routine
- Route: not-applicable
- Non: project-policy, parser-tool-owner
- Structural: none
- Semantic: none
- Invariant: apply the evidenced grammar and use CommonMark 0.31.2 only where its rules apply
- Forbid: claim parser- or renderer-specific behavior without evidence
- Rb: not material
- Src: pinned CommonMark object plus parser evidence

### APG63-MD-002 — GFM table under selected extension

- In: add a pipe table where the actual parser/configuration enables table syntax
- Dialect: actual parser/configuration; GFM 0.29 tables are a bounded extension reference
- Decision: decide the table syntax under the enabled extension set
- Owner: markdown-language-profile
- Selection: selected
- Response: proceed-routine
- Route: not-applicable
- Non: parser-tool-owner, project-design
- Structural: none
- Semantic: none
- Invariant: table semantics apply only under the evidenced implementation and option set
- Forbid: treat tables as universal Markdown or assert cross-version composition
- Rb: not material
- Src: pinned GFM object plus parser evidence

### APG63-MD-003 — GFM task list

- In: add task-list items where the actual parser/configuration enables task-list syntax
- Dialect: actual parser/configuration; GFM 0.29 task lists are a bounded extension reference
- Decision: decide task-item syntax without assigning workflow meaning
- Owner: markdown-language-profile
- Selection: selected
- Response: proceed-routine
- Route: not-applicable
- Non: project-policy
- Structural: none
- Semantic: none
- Invariant: separate syntax from project meaning of checked state
- Forbid: infer workflow state from checkbox syntax
- Rb: not material
- Src: pinned GFM object plus parser evidence

### APG63-MD-004 — Extended autolink selected

- In: add a bare URL where the actual parser/configuration explicitly enables extended autolinks
- Dialect: actual parser/configuration; GFM 0.29 autolinks are a bounded extension reference
- Decision: decide whether the evidenced extension recognizes the bare URL
- Owner: markdown-language-profile
- Selection: selected
- Response: proceed-routine
- Route: not-applicable
- Non: parser-tool-owner
- Structural: none
- Semantic: none
- Invariant: distinguish CommonMark angle autolinks from the enabled extended-autolink behavior
- Forbid: promise bare-URL rendering outside the evidenced implementation and option set
- Rb: not material
- Src: pinned specifications plus parser evidence

### APG63-MD-005 — Unsupported repository extension

- In: interpret definition-list syntax absent from the evidenced parser/configuration
- Dialect: construct is outside the actual configured grammar and both bounded references
- Decision: decide whether the repository enables another parser extension
- Owner: parser-tool-owner
- Selection: route-to-owner
- Response: inspect-before-judgment
- Route: parser-tool-owner
- Non: markdown-language-profile
- Structural: none
- Semantic: extension-unsupported
- Invariant: route the tooling decision without silently adopting syntax
- Forbid: interpret or normalize the unsupported construct under Markdown authority
- Rb: not material
- Src: actual parser/configuration

### APG63-MD-006 — Unknown parser

- In: judge extension-dependent syntax while the repository parser cannot be identified
- Dialect: parser and extension set are unknown; no effective grammar is established
- Decision: identify the parser before dialect-dependent judgment
- Owner: parser-tool-owner
- Selection: route-to-owner
- Response: inspect-before-judgment
- Route: parser-tool-owner
- Non: markdown-language-profile
- Structural: none
- Semantic: dialect-mismatch
- Invariant: restrict interim claims to independently evidenced facts
- Forbid: make extension-dependent claims from a profile default
- Rb: not material
- Src: repository parser evidence required

### APG63-MD-007 — Parser conflicts with reference

- In: the actual parser interprets a construct differently from a bounded specification reference
- Dialect: actual parser/configuration is evidenced and controls effective behavior
- Decision: decide whether to change tooling or accept its version-bound behavior
- Owner: parser-tool-owner
- Selection: route-to-owner
- Response: stop-and-escalate
- Route: parser-tool-owner
- Non: markdown-language-profile
- Structural: none
- Semantic: dialect-mismatch
- Invariant: preserve actual behavior until the owning tool decision is made
- Forbid: override the parser with a synthetic reference grammar
- Rb: record the predecision behavior for a material tooling decision
- Src: actual parser/configuration plus bounded reference

### APG63-MD-008 — Deep delimiter ambiguity

- In: resolve a specifically evidenced deeply nested emphasis and escape sequence
- Dialect: actual parser/configuration; applicable delimiter rules are known
- Decision: resolve the exact delimiter run before editing
- Owner: markdown-language-profile
- Selection: selected
- Response: inspect-before-judgment
- Route: not-applicable
- Non: project-policy
- Structural: none
- Semantic: none
- Invariant: derive the result from evidenced grammar rather than renderer trial
- Forbid: present guessed rendering as specified behavior
- Rb: not material
- Src: actual parser/configuration and applicable reference

## Blocks, links, and fences — 009–016

### APG63-MD-009 — Heading hierarchy

- In: repair a document with one skipped heading level
- Dialect: actual parser/configuration; heading syntax is evidenced
- Decision: decide the proportionate Markdown-structure repair
- Owner: markdown-language-profile
- Selection: selected
- Response: inspect-before-judgment
- Route: not-applicable
- Non: project-design
- Structural: deep-or-inconsistent-heading-hierarchy
- Semantic: none
- Invariant: treat the broken ladder as an owned defect without size escalation
- Forbid: escalate a small hierarchy defect to crisis
- Rb: not material
- Src: actual parser/configuration

### APG63-MD-010 — Reference-link collision

- In: two normalized reference labels resolve to different destinations in one document
- Dialect: actual parser/configuration; applicable reference-resolution rules are evidenced
- Decision: resolve the Markdown collision after project intent is supplied
- Owner: markdown-language-profile
- Selection: embedded-route
- Response: bounded-local-decision
- Route: project-policy
- Non: project-design
- Structural: repeated-definitions
- Semantic: reference-definition-collision
- Invariant: surface precedence and obtain intended destination from the content owner
- Forbid: silently delete or rewrite either definition
- Rb: record both definitions before material repair
- Src: actual parser/configuration and applicable reference

### APG63-MD-011 — Broken destination ownership

- In: a syntactically valid link points to missing or moved content
- Dialect: actual parser/configuration; link syntax is not disputed
- Decision: decide the valid replacement destination
- Owner: project-policy
- Selection: route-to-owner
- Response: inspect-before-judgment
- Route: project-policy
- Non: markdown-language-profile
- Structural: none
- Semantic: link-destination-invalid
- Invariant: keep syntax judgment separate from destination validity
- Forbid: select a link checker or invent a replacement under Markdown authority
- Rb: not material
- Src: project state and link policy

### APG63-MD-012 — Image syntax and accessibility route

- In: add a valid image construct and ask whether its alternative text is accessible
- Dialect: actual parser/configuration; image syntax is evidenced
- Decision: decide Markdown syntax while routing accessibility acceptance
- Owner: markdown-language-profile
- Selection: embedded-route
- Response: proceed-routine
- Route: accessibility-owner
- Non: project-policy, html-owner
- Structural: none
- Semantic: none
- Invariant: own syntax and alt-text presence only
- Forbid: claim accessibility acceptance from presence alone
- Rb: not material
- Src: actual parser/configuration plus accessibility policy

### APG63-MD-013 — Fenced code block

- In: add a closed fenced block containing material from another language
- Dialect: actual parser/configuration; fence and info-string behavior are evidenced
- Decision: decide the fence boundary while routing embedded semantics
- Owner: markdown-language-profile
- Selection: embedded-route
- Response: proceed-routine
- Route: embedded-language-owner
- Non: parser-tool-owner
- Structural: none
- Semantic: none
- Invariant: keep the embedded route non-additive
- Forbid: edit fenced content under Markdown authority
- Rb: not material
- Src: actual parser/configuration

### APG63-MD-014 — Unterminated fence

- In: an opening fence reclassifies the remaining prose as code
- Dialect: actual parser/configuration; fence closure behavior is evidenced
- Decision: restore the smallest valid closing boundary
- Owner: markdown-language-profile
- Selection: selected
- Response: bounded-local-decision
- Route: not-applicable
- Non: none
- Structural: none
- Semantic: accidental-reclassification
- Invariant: surface the reclassification and bound the repair
- Forbid: perform unrelated broad rewrites
- Rb: record the pre-repair region for material edits
- Src: actual parser/configuration

### APG63-MD-015 — Nested containers

- In: inspect a stated deep list and blockquote nest with lazy continuations
- Dialect: actual parser/configuration; container rules are evidenced
- Decision: resolve the exact container structure before reflow
- Owner: markdown-language-profile
- Selection: selected
- Response: inspect-before-judgment
- Route: not-applicable
- Non: project-policy
- Structural: none
- Semantic: none
- Invariant: apply container rules without trial rendering
- Forbid: reflow content without disclosing structural change
- Rb: not material
- Src: actual parser/configuration and applicable reference

### APG63-MD-016 — Inline code delimiters

- In: place backticks inside an inline code span using a longer delimiter run
- Dialect: actual parser/configuration; code-span delimiter behavior is evidenced
- Decision: decide the exact delimiter run
- Owner: markdown-language-profile
- Selection: selected
- Response: proceed-routine
- Route: not-applicable
- Non: none
- Structural: none
- Semantic: none
- Invariant: apply the evidenced backtick-run rule
- Forbid: present HTML-entity workarounds as Markdown semantics
- Rb: not material
- Src: actual parser/configuration

## HTML and frontmatter — 017–022

### APG63-MD-017 — Raw inline HTML

- In: classify an inline HTML element and then assess its HTML meaning
- Dialect: actual parser/configuration; raw-HTML recognition is evidenced
- Decision: decide the Markdown pass-through boundary and route HTML meaning
- Owner: markdown-language-profile
- Selection: embedded-route
- Response: proceed-routine
- Route: html-owner
- Non: accessibility-owner, project-policy
- Structural: none
- Semantic: raw-html-boundary
- Invariant: own recognition only and route element meaning
- Forbid: make HTML or accessibility claims under Markdown authority
- Rb: not material
- Src: actual parser/configuration plus HTML owner

### APG63-MD-018 — Raw HTML policy evasion

- In: content was moved into a raw HTML block specifically to evade document-structure review
- Dialect: actual parser/configuration; HTML block boundaries are evidenced
- Decision: apply the anti-evasion structural response and route permission policy
- Owner: markdown-language-profile
- Selection: embedded-route
- Response: bounded-local-decision
- Route: project-policy
- Non: html-owner, parser-tool-owner
- Structural: policy-evasion
- Semantic: raw-html-boundary
- Invariant: apply structural judgment to the moved responsibility without absorbing HTML semantics
- Forbid: treat raw HTML as a structure-policy escape hatch
- Rb: record the moved responsibility before material repair
- Src: actual parser/configuration plus repository policy

### APG63-MD-019 — Repository-forbidden raw HTML

- In: a repository rule explicitly forbids raw HTML and a change adds it
- Dialect: actual parser/configuration recognizes the construct; repository prohibition controls
- Decision: enforce the explicit repository prohibition
- Owner: repository-policy
- Selection: route-to-owner
- Response: stop-and-escalate
- Route: repository-policy
- Non: markdown-language-profile, html-owner
- Structural: none
- Semantic: raw-html-boundary
- Invariant: stop the prohibited change and preserve the syntax/permission distinction
- Forbid: permit or prohibit HTML under profile authority
- Rb: not material
- Src: repository policy plus parser evidence

### APG63-MD-020 — Valid frontmatter boundary

- In: edit Markdown body text after a valid parser-recognized YAML frontmatter block
- Dialect: actual parser/configuration supplies the exact boundary; body grammar is evidenced
- Decision: decide body Markdown beginning after the closing delimiter
- Owner: markdown-language-profile
- Selection: selected
- Response: proceed-routine
- Route: not-applicable
- Non: parser-tool-owner, data-language-owner, project-policy
- Structural: none
- Semantic: none
- Invariant: consume the valid boundary without owning delimiter or data semantics
- Forbid: choose schema fields, values, routes, or publication dates
- Rb: not material
- Src: actual parser/configuration

### APG63-MD-021 — Unknown frontmatter schema

- In: frontmatter contains fields with no documented project schema
- Dialect: frontmatter is parser-recognized; field authority is unknown
- Decision: identify the governing schema before changing fields
- Owner: project-policy
- Selection: route-to-owner
- Response: inspect-before-judgment
- Route: project-policy
- Non: markdown-language-profile, data-language-owner
- Structural: none
- Semantic: none
- Invariant: route schema judgment while leaving the body independently owned
- Forbid: invent, rename, or normalize schema fields
- Rb: not material
- Src: project schema and parser evidence

### APG63-MD-022 — Frontmatter delimiter corruption

- In: a malformed delimiter makes the configured parser treat frontmatter as body text
- Dialect: actual parser/configuration defines the delimiter and observed reclassification
- Decision: restore the parser-owned delimiter without changing data values
- Owner: parser-tool-owner
- Selection: route-to-owner
- Response: bounded-local-decision
- Route: parser-tool-owner
- Non: markdown-language-profile, data-language-owner, project-policy
- Structural: none
- Semantic: frontmatter-body-corruption
- Invariant: repair only the evidenced boundary form
- Forbid: rewrite frontmatter values as part of delimiter repair
- Rb: record pre-repair bytes for material edits
- Src: actual parser/configuration

## MDX and host boundaries — 023–027

### APG63-MD-023 — Ordinary .md

- In: make a routine edit to a .md file under an evidenced parser/configuration
- Dialect: actual parser/configuration applies to the whole file
- Decision: decide ordinary whole-file Markdown semantics
- Owner: markdown-language-profile
- Selection: selected
- Response: proceed-routine
- Route: not-applicable
- Non: parser-tool-owner
- Structural: none
- Semantic: none
- Invariant: apply whole-file ownership only to the evidenced .md parser context
- Forbid: extend ownership into pipeline configuration
- Rb: not material
- Src: actual parser/configuration

### APG63-MD-024 — Markdown-looking .mdx

- In: edit an .mdx file containing no JSX
- Dialect: MDX grammar is selected by the actual pipeline
- Decision: decline whole-file Markdown selection and route to MDX
- Owner: mdx-owner
- Selection: non-trigger
- Response: proceed-routine
- Route: mdx-owner
- Non: markdown-language-profile
- Structural: not-applicable
- Semantic: not-applicable
- Invariant: treat the file as MDX despite Markdown-looking content
- Forbid: make whole-file Markdown claims or counts
- Rb: not material
- Src: actual MDX pipeline; outside pinned Markdown references

### APG63-MD-025 — MDX expression

- In: edit an .mdx file containing an expression
- Dialect: MDX executable grammar is selected
- Decision: decline whole-file Markdown selection and route to MDX
- Owner: mdx-owner
- Selection: non-trigger
- Response: proceed-routine
- Route: mdx-owner
- Non: markdown-language-profile
- Structural: not-applicable
- Semantic: not-applicable
- Invariant: leave expression semantics with MDX and host owners
- Forbid: interpret expression braces as Markdown text
- Rb: not material
- Src: actual MDX pipeline

### APG63-MD-026 — JSX in MDX

- In: edit an .mdx file containing JSX components
- Dialect: MDX plus JSX grammar is selected
- Decision: decline whole-file Markdown selection and route to MDX
- Owner: mdx-owner
- Selection: non-trigger
- Response: proceed-routine
- Route: mdx-owner
- Non: markdown-language-profile, host-owner
- Structural: not-applicable
- Semantic: not-applicable
- Invariant: leave JSX semantics outside Markdown
- Forbid: edit JSX regions under Markdown authority
- Rb: not material
- Src: actual MDX and host pipeline

### APG63-MD-027 — Markdown embedded in a host

- In: review one identified Markdown fragment in a host-owned docstring
- Dialect: host renderer is evidenced and selects the fragment grammar
- Decision: keep whole-file ownership with the host and inspect the embedded route
- Owner: host-owner
- Selection: embedded-route
- Response: inspect-before-judgment
- Route: markdown-language-profile
- Non: project-policy
- Structural: none
- Semantic: none
- Invariant: keep embedded judgment non-additive and limited to the named fragment
- Forbid: make whole-file Markdown structure claims
- Rb: not material
- Src: host renderer evidence

## Structure and document classes — 028–034

### APG63-MD-028 — Long cohesive handwritten changelog

- In: append a dated entry to a stated cohesive, handwritten, single-purpose changelog
- Dialect: actual parser/configuration; no generated owner applies
- Decision: decide the current Markdown growth without using length as severity
- Owner: markdown-language-profile
- Selection: selected
- Response: proceed-routine
- Route: not-applicable
- Non: project-policy
- Structural: none
- Semantic: none
- Invariant: preserve cohesive history and inspect only independently firing signals
- Forbid: demand decomposition from physical length alone
- Rb: not material
- Src: actual parser/configuration plus artifact classification

### APG63-MD-029 — Generated output with hand edit

- In: a generator-owned reference contains a documented hand edit and differs from fresh generator intent
- Dialect: actual parser/configuration applies to output; generator owns content
- Decision: repair the manual/generated ownership conflict through the generator
- Owner: parser-tool-owner
- Selection: route-to-owner
- Response: bounded-local-decision
- Route: parser-tool-owner
- Non: markdown-language-profile
- Structural: manual-generated-content-mixing
- Semantic: generated-source-drift
- Invariant: classify before structural judgment and route repair to the generator
- Forbid: hand-refactor generated output
- Rb: regeneration is the rollback path
- Src: generator and parser evidence

### APG63-MD-030 — Mixed-purpose README

- In: a README currently serves four stated coequal purposes and two divergent audiences
- Dialect: actual parser/configuration applies
- Decision: decide whether the proposed growth requires decomposition
- Owner: markdown-language-profile
- Selection: embedded-route
- Response: bounded-local-decision
- Route: project-design
- Non: project-policy
- Structural: multiple-independent-audiences, multiple-independent-purposes
- Semantic: none
- Invariant: bound the current growth decision and let project design choose the shape
- Forbid: use line count or editorial preference as the classification
- Rb: preserve navigation and record the move map
- Src: actual parser/configuration plus project input

### APG63-MD-031 — Oversized tutorial section

- In: one tutorial section is stated to be unreviewable as a unit and lookup material is interleaved with ordered steps
- Dialect: actual parser/configuration applies
- Decision: choose a bounded extraction seam for the current growth
- Owner: markdown-language-profile
- Selection: embedded-route
- Response: bounded-local-decision
- Route: project-design
- Non: project-policy
- Structural: oversized-single-section, reference-tutorial-mixing
- Semantic: none
- Invariant: prefer section or series extraction over size-driven whole-file splitting
- Forbid: classify crisis from length alone
- Rb: record the extraction map
- Src: actual parser/configuration plus reviewer evidence

### APG63-MD-032 — Divergent duplicated norms

- In: the same governing requirement exists in two repository documents with contradictory current wording
- Dialect: actual parser/configuration applies; governing content authority is project policy
- Decision: stop dependent work and obtain one authoritative project decision
- Owner: project-policy
- Selection: route-to-owner
- Response: stop-and-escalate
- Route: project-policy
- Non: markdown-language-profile, repository-policy
- Structural: duplicated-normative-truth
- Semantic: normative-contradiction
- Invariant: preserve both statements and resolve authority before harmonization
- Forbid: silently choose or rewrite either statement
- Rb: record both pre-change statements
- Src: project policy and repository evidence

### APG63-MD-033 — Reference-table navigation failure

- In: a large single-purpose table has a named topic unreachable by headings, contents, or links
- Dialect: actual parser/configuration enables table syntax
- Decision: add bounded navigation or choose an extraction seam
- Owner: markdown-language-profile
- Selection: embedded-route
- Response: bounded-local-decision
- Route: project-design
- Non: project-policy
- Structural: navigation-failure
- Semantic: none
- Invariant: use evidenced navigation failure rather than length to select the response
- Forbid: mechanically split the table because it is large
- Rb: not material
- Src: actual parser/configuration plus navigation evidence

### APG63-MD-034 — Short semantic Red document

- In: a small document contains two contradictory governing statements and no stricter repository rule selects one
- Dialect: actual parser/configuration applies; content authority is project policy
- Decision: stop dependent work and obtain the project-policy resolution
- Owner: project-policy
- Selection: route-to-owner
- Response: stop-and-escalate
- Route: project-policy
- Non: markdown-language-profile, repository-policy
- Structural: none
- Semantic: normative-contradiction
- Invariant: keep semantic Red independent of size
- Forbid: proceed on either statement or dismiss the contradiction because the file is small
- Rb: record the contradiction; no content rollback precedes resolution
- Src: project policy and repository evidence

## Review-process invariants — 035–036

### APG63-MD-035 — Candidate rejection preserves history

- In: a future review rejects an authored Markdown candidate
- Dialect: not applicable; this is a review-process invariant
- Decision: remove current candidate surfaces while preserving complete history
- Owner: generic-lifecycle
- Selection: non-trigger
- Response: stop-and-escalate
- Route: generic-lifecycle
- Non: markdown-language-profile
- Structural: not-applicable
- Semantic: not-applicable
- Invariant: keep lifecycle obligations outside candidate semantic prose
- Forbid: map Git, report, catalog, release, or projection operations into the candidate
- Rb: history-preserving removal is the rollback shape
- Src: generic APG lifecycle contracts

### APG63-MD-036 — Corrected evidence survives rejection

- In: a future review corrects once and then rejects the candidate
- Dialect: not applicable; this is a review-process invariant
- Decision: preserve corrected-state evidence before current-surface deletion
- Owner: generic-lifecycle
- Selection: non-trigger
- Response: stop-and-escalate
- Route: generic-lifecycle
- Non: markdown-language-profile
- Structural: not-applicable
- Semantic: false-completion
- Invariant: bind corrected hashes, exact patch, vectors, and reviewers before deletion
- Forbid: delete the only auditable corrected state or rewrite the authoring object
- Rb: preserved evidence is the audit path
- Src: APG64 review-process contract
